from datetime import datetime

from money.publishing import (
    PublishError,
    PublisherService,
    TikTokPublisherAdapter,
    YouTubeShortsAdapter,
)
from money.review.service import PUBLISH_BLOCK_CODE, ReviewQueueService


def _build_review_service(variant_id: str, decision: str) -> ReviewQueueService:
    service = ReviewQueueService(sla_seconds=24 * 60 * 60)
    service.enqueue_item(
        variant_id=variant_id,
        locale="EN-US",
        policy={
            "result_code": "PASS",
            "policy_code": "PASS",
        },
        originality={
            "similarity_score": 0.21,
            "threshold": 0.8,
            "result_code": "PASS",
        },
        cost={
            "estimated_usd": 2.91,
            "currency": "USD",
        },
        queued_at="2026-02-16T09:00:00Z",
    )
    service.record_decision(
        variant_id=variant_id,
        decision=decision,
        decision_code="APPROVED_MANUAL_REVIEW"
        if decision == "approved"
        else "REJECTED_POLICY",
        reviewer_id="task6-test-reviewer",
        reviewed_at="2026-02-16T09:10:00Z",
    )
    return service


def _approved_payload(variant_id: str) -> dict:
    return {
        "variant_id": variant_id,
        "locale": "EN-US",
        "localized_script": "A quick framework for investing your first 100 dollars.",
        "review_status": "approved",
        "targets": ["youtube", "tiktok"],
        "scheduled_for": "2026-02-16T12:00:00Z",
    }


def test_publish_idempotency_key_prevents_duplicate_posts() -> None:
    youtube_adapter = YouTubeShortsAdapter()
    tiktok_adapter = TikTokPublisherAdapter()
    service = PublisherService(
        review_service=_build_review_service("variant-publish-idempotent", decision="approved"),
        now_provider=lambda: datetime(2026, 2, 16, 12, 1, 0),
        adapters={
            "youtube": youtube_adapter,
            "tiktok": tiktok_adapter,
        },
    )

    first = service.publish(
        approved_payload=_approved_payload("variant-publish-idempotent"),
        idempotency_key="task6-idempotent-key-001",
    )
    second = service.publish(
        approved_payload=_approved_payload("variant-publish-idempotent"),
        idempotency_key="task6-idempotent-key-001",
    )

    assert first["status"] == "published"
    assert first["result_code"] == "PASS"
    assert first == second
    assert len(service.list_receipts()) == 2
    assert youtube_adapter.publish_call_count == 1
    assert tiktok_adapter.publish_call_count == 1


def test_partial_failure_returns_retryable_receipt_for_only_failing_platform() -> None:
    service = PublisherService(
        review_service=_build_review_service("variant-publish-partial", decision="approved"),
        now_provider=lambda: datetime(2026, 2, 16, 12, 1, 0),
        adapters={
            "youtube": YouTubeShortsAdapter(),
            "tiktok": TikTokPublisherAdapter(retryable_failure_keys=["task6-partial-key-001"]),
        },
    )

    response = service.publish(
        approved_payload=_approved_payload("variant-publish-partial"),
        idempotency_key="task6-partial-key-001",
    )

    by_platform = {
        receipt["platform"]: receipt
        for receipt in response["platform_receipts"]
    }
    assert response["status"] == "publish_partial_retryable"
    assert response["result_code"] == "PUBLISH_PARTIAL_RETRYABLE"
    assert by_platform["youtube"]["publish_status"] == "success"
    assert by_platform["tiktok"]["publish_status"] == "failed_retryable"
    assert len(service.list_receipts()) == 2


def test_publish_requires_human_approval_gate() -> None:
    service = PublisherService(
        review_service=_build_review_service("variant-publish-blocked", decision="rejected"),
        now_provider=lambda: datetime(2026, 2, 16, 12, 1, 0),
    )

    try:
        service.publish(
            approved_payload=_approved_payload("variant-publish-blocked"),
            idempotency_key="task6-blocked-key-001",
        )
    except PublishError as error:
        assert error.code == PUBLISH_BLOCK_CODE
    else:
        raise AssertionError("publish should fail when review decision is not approved")
