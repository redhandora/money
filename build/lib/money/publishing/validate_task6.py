import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from money.publishing.service import PublisherService, TikTokPublisherAdapter, YouTubeShortsAdapter
from money.review.service import ReviewQueueService


ROOT_DIR = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT_DIR / ".sisyphus" / "evidence"
ARTIFACT_DIR = ROOT_DIR / "build" / "task6"


def _write_evidence(file_name: str, payload: Dict[str, Any]) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EVIDENCE_DIR / file_name
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def _build_approved_review_service(variant_id: str) -> ReviewQueueService:
    service = ReviewQueueService(sla_seconds=24 * 60 * 60)
    service.enqueue_item(
        variant_id=variant_id,
        locale="EN-US",
        policy={
            "result_code": "PASS",
            "policy_code": "PASS",
        },
        originality={
            "similarity_score": 0.27,
            "threshold": 0.8,
            "result_code": "PASS",
        },
        cost={
            "estimated_usd": 3.12,
            "currency": "USD",
        },
        queued_at="2026-02-16T09:00:00Z",
    )
    service.record_decision(
        variant_id=variant_id,
        decision="approved",
        decision_code="APPROVED_MANUAL_REVIEW",
        reviewer_id="task6-validator",
        reviewed_at="2026-02-16T09:01:00Z",
    )
    return service


def _approved_payload(variant_id: str) -> Dict[str, Any]:
    return {
        "variant_id": variant_id,
        "locale": "EN-US",
        "localized_script": "Three-budget-rules that stop impulse spending this week.",
        "review_status": "approved",
        "targets": ["youtube", "tiktok"],
        "scheduled_for": "2026-02-16T12:00:00Z",
    }


def run_idempotency_scenario() -> Dict[str, Any]:
    review_service = _build_approved_review_service("variant-task6-idempotency")
    service = PublisherService(
        review_service=review_service,
        now_provider=lambda: datetime(2026, 2, 16, 12, 1, 0),
        receipt_log_path=ARTIFACT_DIR / "idempotency" / "publish_receipts.jsonl",
    )

    first = service.publish(
        approved_payload=_approved_payload("variant-task6-idempotency"),
        idempotency_key="publish-task6-idempotent-001",
    )
    second = service.publish(
        approved_payload=_approved_payload("variant-task6-idempotency"),
        idempotency_key="publish-task6-idempotent-001",
    )

    first_receipts = first.get("platform_receipts", [])
    second_receipts = second.get("platform_receipts", [])
    persisted_receipts = service.list_receipts()

    return {
        "scenario": "publish_is_idempotent_by_idempotency_key",
        "first_response": first,
        "second_response": second,
        "checks": {
            "same_response_on_repeat": first == second,
            "single_platform_receipt_set_persisted": len(persisted_receipts) == 2,
            "receipt_count_stable": len(first_receipts) == len(second_receipts) == 2,
            "platform_post_ids_stable": [
                item["platform_post_id"] for item in first_receipts
            ]
            == [item["platform_post_id"] for item in second_receipts],
        },
    }


def run_partial_failure_scenario() -> Dict[str, Any]:
    review_service = _build_approved_review_service("variant-task6-partial")
    service = PublisherService(
        review_service=review_service,
        now_provider=lambda: datetime(2026, 2, 16, 12, 2, 0),
        receipt_log_path=ARTIFACT_DIR / "partial-failure" / "publish_receipts.jsonl",
        adapters={
            "youtube": YouTubeShortsAdapter(),
            "tiktok": TikTokPublisherAdapter(
                retryable_failure_keys=["publish-task6-partial-001"],
            ),
        },
    )

    response = service.publish(
        approved_payload=_approved_payload("variant-task6-partial"),
        idempotency_key="publish-task6-partial-001",
    )
    receipts = response.get("platform_receipts", [])
    by_platform = {
        item["platform"]: item
        for item in receipts
    }

    return {
        "scenario": "partial_failure_is_isolated_per_platform",
        "response": response,
        "checks": {
            "overall_marked_retryable": response.get("result_code") == "PUBLISH_PARTIAL_RETRYABLE",
            "youtube_success": by_platform.get("youtube", {}).get("publish_status") == "success",
            "tiktok_retryable_failure": by_platform.get("tiktok", {}).get("publish_status")
            == "failed_retryable",
            "both_platform_receipts_persisted": len(service.list_receipts()) == 2,
        },
        "platform_receipts": receipts,
    }


def _run_scenario(scenario: str) -> List[Tuple[str, Dict[str, Any]]]:
    if scenario == "idempotency":
        return [("task-6-idempotency.json", run_idempotency_scenario())]
    if scenario == "partial-failure":
        return [("task-6-partial-failure.json", run_partial_failure_scenario())]
    if scenario == "all":
        return [
            ("task-6-idempotency.json", run_idempotency_scenario()),
            ("task-6-partial-failure.json", run_partial_failure_scenario()),
        ]
    raise ValueError("unsupported scenario: %s" % scenario)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "scenario",
        choices=["idempotency", "partial-failure", "all"],
    )
    args = parser.parse_args()

    for file_name, payload in _run_scenario(args.scenario):
        path = _write_evidence(file_name, payload)
        print(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
