import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from money.review.api import ReviewApiApp, invoke_json_request
from money.review.service import ReviewQueueService


ROOT_DIR = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT_DIR / ".sisyphus" / "evidence"
ARTIFACT_DIR = ROOT_DIR / "build" / "task5"


def _fixed_now(value: datetime) -> Callable[[], datetime]:
    return lambda: value


def _reset_file(path: Path) -> None:
    if path.exists():
        path.unlink()


def build_seeded_review_service(
    decision_log_path: Path,
    now_provider: Optional[Callable[[], datetime]] = None,
) -> ReviewQueueService:
    _reset_file(decision_log_path)
    service = ReviewQueueService(
        sla_seconds=24 * 60 * 60,
        now_provider=now_provider,
        decision_log_path=decision_log_path,
    )
    service.enqueue_item(
        variant_id="variant-en-us-001",
        locale="EN-US",
        policy={
            "result_code": "PASS",
            "policy_code": "PASS",
        },
        originality={
            "similarity_score": 0.44,
            "threshold": 0.8,
            "result_code": "PASS",
        },
        cost={
            "estimated_usd": 2.75,
            "currency": "USD",
        },
        queued_at="2026-02-16T00:00:00Z",
    )
    return service


def run_queue_payload_scenario() -> Dict[str, Any]:
    service = build_seeded_review_service(
        decision_log_path=ARTIFACT_DIR / "queue" / "decision_log.jsonl",
        now_provider=_fixed_now(datetime(2026, 2, 16, 1, 0, 0)),
    )
    app = ReviewApiApp(service)

    status_code, payload = invoke_json_request(
        app=app,
        method="GET",
        path="/review/queue",
    )

    item = payload.get("items", [{}])[0] if payload.get("items") else {}
    required_item_fields = ["locale", "policy", "originality", "cost"]
    required_present = {
        field_name: field_name in item for field_name in required_item_fields
    }

    return {
        "scenario": "queue_returns_pending_localized_variants",
        "response": {
            "http_status": status_code,
            "status": payload.get("status"),
            "result_code": payload.get("result_code"),
            "item_count": len(payload.get("items", [])),
        },
        "checks": {
            "has_pending_item": len(payload.get("items", [])) == 1,
            "required_fields_present": required_present,
            "all_required_fields_present": all(required_present.values()),
        },
        "sample_item": item,
    }


def run_decision_immutability_scenario() -> Dict[str, Any]:
    service = build_seeded_review_service(
        decision_log_path=ARTIFACT_DIR / "decision-immutability" / "decision_log.jsonl",
        now_provider=_fixed_now(datetime(2026, 2, 16, 1, 0, 0)),
    )
    app = ReviewApiApp(service)

    first_status, first_payload = invoke_json_request(
        app=app,
        method="POST",
        path="/review/decision",
        payload={
            "variant_id": "variant-en-us-001",
            "decision": "approved",
            "decision_code": "APPROVED_MANUAL_REVIEW",
            "reviewer_id": "validator-reviewer",
            "reviewed_at": "2026-02-16T01:00:00Z",
        },
    )

    second_status, second_payload = invoke_json_request(
        app=app,
        method="POST",
        path="/review/decision",
        payload={
            "variant_id": "variant-en-us-001",
            "decision": "rejected",
            "decision_code": "REJECTED_POLICY",
            "reviewer_id": "validator-reviewer",
            "reviewed_at": "2026-02-16T01:05:00Z",
        },
    )

    list_status, list_payload = invoke_json_request(
        app=app,
        method="GET",
        path="/review/decisions",
    )
    decision_items = list_payload.get("items", [])

    return {
        "scenario": "decision_log_is_immutable",
        "first_response": {
            "http_status": first_status,
            "status": first_payload.get("status"),
            "result_code": first_payload.get("result_code"),
            "decision_id": first_payload.get("decision", {}).get("decision_id"),
        },
        "second_response": {
            "http_status": second_status,
            "status": second_payload.get("status"),
            "result_code": second_payload.get("result_code"),
            "error_code": second_payload.get("error_code"),
        },
        "decision_list": {
            "http_status": list_status,
            "count": len(decision_items),
            "items": decision_items,
        },
        "checks": {
            "first_decision_saved": first_status == 200,
            "second_decision_blocked": second_status == 409,
            "immutable_error_code": second_payload.get("error_code")
            == "REVIEW_DECISION_IMMUTABLE",
            "single_decision_recorded": len(decision_items) == 1,
        },
    }


def run_sla_expiry_scenario() -> Dict[str, Any]:
    service = build_seeded_review_service(
        decision_log_path=ARTIFACT_DIR / "sla-expiry" / "decision_log.jsonl",
        now_provider=_fixed_now(datetime(2026, 2, 17, 0, 0, 0)),
    )
    app = ReviewApiApp(service)

    queue_status, queue_payload = invoke_json_request(
        app=app,
        method="GET",
        path="/review/queue",
    )
    publish_status, publish_payload = invoke_json_request(
        app=app,
        method="POST",
        path="/publish",
        payload={
            "variant_id": "variant-en-us-001",
        },
    )
    decision_status, decision_payload = invoke_json_request(
        app=app,
        method="POST",
        path="/review/decision",
        payload={
            "variant_id": "variant-en-us-001",
            "decision": "approved",
            "decision_code": "APPROVED_MANUAL_REVIEW",
            "reviewer_id": "validator-reviewer",
        },
    )
    decisions_status, decisions_payload = invoke_json_request(
        app=app,
        method="GET",
        path="/review/decisions",
    )

    decision_items = decisions_payload.get("items", [])
    expired_entry = decision_items[0] if decision_items else {}

    return {
        "scenario": "sla_expiry_prevents_publish",
        "queue_response": {
            "http_status": queue_status,
            "pending_count": len(queue_payload.get("items", [])),
        },
        "publish_response": {
            "http_status": publish_status,
            "error_code": publish_payload.get("error_code"),
            "result_code": publish_payload.get("result_code"),
        },
        "decision_attempt_response": {
            "http_status": decision_status,
            "error_code": decision_payload.get("error_code"),
            "result_code": decision_payload.get("result_code"),
        },
        "decision_log_response": {
            "http_status": decisions_status,
            "count": len(decision_items),
            "entry": expired_entry,
        },
        "checks": {
            "item_removed_from_pending_queue": len(queue_payload.get("items", [])) == 0,
            "publish_blocked_with_human_gate_code": publish_payload.get("error_code")
            == "HUMAN_APPROVAL_REQUIRED",
            "decision_attempt_blocked_after_expiry": decision_payload.get("error_code")
            == "REVIEW_ITEM_EXPIRED",
            "expiry_decision_recorded": expired_entry.get("decision") == "expired"
            and expired_entry.get("decision_code") == "EXPIRED_SLA",
        },
    }


def run_human_gate_scenario() -> Dict[str, Any]:
    service = build_seeded_review_service(
        decision_log_path=ARTIFACT_DIR / "human-gate" / "decision_log.jsonl",
        now_provider=_fixed_now(datetime(2026, 2, 16, 1, 0, 0)),
    )
    app = ReviewApiApp(service)

    status_code, payload = invoke_json_request(
        app=app,
        method="POST",
        path="/publish",
        payload={
            "variant_id": "variant-en-us-001",
        },
    )
    return {
        "scenario": "publish_without_approval_is_blocked",
        "request": {
            "path": "/publish",
            "variant_id": "variant-en-us-001",
        },
        "response": {
            "http_status": status_code,
            "error_code": payload.get("error_code"),
            "result_code": payload.get("result_code"),
            "message": payload.get("message"),
        },
    }


def _write_evidence(file_name: str, payload: Dict[str, Any]) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EVIDENCE_DIR / file_name
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def _run_scenario(scenario: str) -> List[Tuple[str, Dict[str, Any]]]:
    if scenario == "queue":
        return [("task-5-review-queue.json", run_queue_payload_scenario())]
    if scenario == "decision-immutability":
        return [
            (
                "task-5-decision-immutability.json",
                run_decision_immutability_scenario(),
            )
        ]
    if scenario == "sla-expiry":
        return [("task-5-sla-expiry-block.json", run_sla_expiry_scenario())]
    if scenario == "human-gate":
        return [("task-5-human-gate.json", run_human_gate_scenario())]
    if scenario == "all":
        return [
            ("task-5-review-queue.json", run_queue_payload_scenario()),
            (
                "task-5-decision-immutability.json",
                run_decision_immutability_scenario(),
            ),
            ("task-5-sla-expiry-block.json", run_sla_expiry_scenario()),
            ("task-5-human-gate.json", run_human_gate_scenario()),
        ]
    raise ValueError("unsupported scenario: %s" % scenario)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "scenario",
        choices=[
            "queue",
            "decision-immutability",
            "sla-expiry",
            "human-gate",
            "all",
        ],
    )
    args = parser.parse_args()

    for file_name, payload in _run_scenario(args.scenario):
        path = _write_evidence(file_name, payload)
        print(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
