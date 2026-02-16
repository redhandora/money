import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from money.review.api import REVIEW_PAGE_HTML, ReviewApiApp, invoke_json_request
from money.review.service import PUBLISH_BLOCK_CODE, ReviewQueueService


def _enqueue_review_item(service: ReviewQueueService, variant_id: str) -> Dict[str, Any]:
    return service.enqueue_item(
        variant_id=variant_id,
        locale="EN-US",
        policy={
            "result_code": "PASS",
            "policy_code": "PASS",
        },
        originality={
            "similarity_score": 0.33,
            "threshold": 0.8,
            "result_code": "PASS",
        },
        cost={
            "estimated_usd": 2.45,
            "currency": "USD",
        },
        queued_at="2026-02-16T00:00:00Z",
    )


def _read_jsonl(path: Path) -> Any:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def test_review_queue_api_returns_required_pending_fields() -> None:
    service = ReviewQueueService()
    queued = _enqueue_review_item(service, variant_id="variant-en-us-queue-001")
    app = ReviewApiApp(service)

    status_code, payload = invoke_json_request(app, "GET", "/review/queue")

    assert status_code == 200
    assert payload["status"] == "ok"
    assert payload["result_code"] == "PASS"
    assert payload["items"]
    item = payload["items"][0]
    assert item["variant_id"] == queued["variant_id"]
    assert item["locale"] == "EN-US"
    assert item["status"] == "pending"
    assert "policy" in item
    assert "originality" in item
    assert "cost" in item
    assert item["policy"]["policy_code"] == "PASS"
    assert item["originality"]["result_code"] == "PASS"
    assert item["cost"]["currency"] == "USD"


def test_review_ui_exposes_reject_reason_control() -> None:
    assert 'data-testid="queue-body"' in REVIEW_PAGE_HTML
    assert "rejectReasonSelect.dataset.testid = 'reject-reason'" in REVIEW_PAGE_HTML
    assert "REJECTED_POLICY" in REVIEW_PAGE_HTML
    assert "REJECTED_ORIGINALITY" in REVIEW_PAGE_HTML


def test_review_decision_persists_to_immutable_log(tmp_path: Path) -> None:
    decision_log_path = tmp_path / "decision_log.jsonl"
    service = ReviewQueueService(decision_log_path=decision_log_path)
    _enqueue_review_item(service, variant_id="variant-en-us-decision-001")
    app = ReviewApiApp(service)

    first_status, first_payload = invoke_json_request(
        app,
        "POST",
        "/review/decision",
        {
            "variant_id": "variant-en-us-decision-001",
            "decision": "approved",
            "decision_code": "APPROVED_MANUAL_REVIEW",
            "reviewer_id": "qa-reviewer",
            "reviewed_at": "2026-02-16T01:00:00Z",
        },
    )

    assert first_status == 200
    assert first_payload["status"] == "decision_saved"
    assert first_payload["decision"]["decision"] == "approved"

    lines_after_first_decision = _read_jsonl(decision_log_path)
    assert len(lines_after_first_decision) == 1
    assert lines_after_first_decision[0]["decision"] == "approved"

    second_status, second_payload = invoke_json_request(
        app,
        "POST",
        "/review/decision",
        {
            "variant_id": "variant-en-us-decision-001",
            "decision": "rejected",
            "decision_code": "REJECTED_POLICY",
            "reviewer_id": "qa-reviewer",
            "reviewed_at": "2026-02-16T01:05:00Z",
        },
    )

    assert second_status == 409
    assert second_payload["error_code"] == "REVIEW_DECISION_IMMUTABLE"

    lines_after_second_decision = _read_jsonl(decision_log_path)
    assert lines_after_second_decision == lines_after_first_decision


def test_publish_path_blocks_pending_and_rejected_with_human_gate_code() -> None:
    service = ReviewQueueService()
    _enqueue_review_item(service, variant_id="variant-en-us-block-001")
    app = ReviewApiApp(service)

    pending_status, pending_payload = invoke_json_request(
        app,
        "POST",
        "/publish",
        {"variant_id": "variant-en-us-block-001"},
    )

    assert pending_status == 409
    assert pending_payload["error_code"] == PUBLISH_BLOCK_CODE

    decision_status, _decision_payload = invoke_json_request(
        app,
        "POST",
        "/review/decision",
        {
            "variant_id": "variant-en-us-block-001",
            "decision": "rejected",
            "decision_code": "REJECTED_POLICY",
            "reviewer_id": "qa-reviewer",
        },
    )
    assert decision_status == 200

    rejected_status, rejected_payload = invoke_json_request(
        app,
        "POST",
        "/publish",
        {"variant_id": "variant-en-us-block-001"},
    )

    assert rejected_status == 409
    assert rejected_payload["error_code"] == PUBLISH_BLOCK_CODE


def test_sla_expired_item_is_removed_from_queue_and_cannot_publish(tmp_path: Path) -> None:
    decision_log_path = tmp_path / "decision_log.jsonl"
    service = ReviewQueueService(
        decision_log_path=decision_log_path,
        now_provider=lambda: datetime(2026, 2, 17, 0, 0, 0),
    )
    _enqueue_review_item(service, variant_id="variant-en-us-expired-001")
    app = ReviewApiApp(service)

    queue_status, queue_payload = invoke_json_request(app, "GET", "/review/queue")
    assert queue_status == 200
    assert queue_payload["items"] == []

    publish_status, publish_payload = invoke_json_request(
        app,
        "POST",
        "/publish",
        {"variant_id": "variant-en-us-expired-001"},
    )
    assert publish_status == 409
    assert publish_payload["error_code"] == PUBLISH_BLOCK_CODE

    review_status, review_payload = invoke_json_request(
        app,
        "POST",
        "/review/decision",
        {
            "variant_id": "variant-en-us-expired-001",
            "decision": "approved",
            "decision_code": "APPROVED_MANUAL_REVIEW",
            "reviewer_id": "qa-reviewer",
        },
    )
    assert review_status == 409
    assert review_payload["error_code"] == "REVIEW_ITEM_EXPIRED"

    item = service.get_item("variant-en-us-expired-001")
    assert item["status"] == "expired"

    decision_rows = _read_jsonl(decision_log_path)
    assert len(decision_rows) == 1
    assert decision_rows[0]["decision"] == "expired"
    assert decision_rows[0]["decision_code"] == "EXPIRED_SLA"
