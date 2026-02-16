import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from money.contracts.validate_task1 import validate_contract


DEFAULT_REVIEW_SLA_SECONDS = 24 * 60 * 60
ISO_8601_UTC_Z = "%Y-%m-%dT%H:%M:%SZ"
PUBLISH_BLOCK_CODE = "HUMAN_APPROVAL_REQUIRED"


class ReviewError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def _parse_utc_timestamp(raw_timestamp: str) -> datetime:
    value = str(raw_timestamp or "").strip()
    formats = [ISO_8601_UTC_Z, "%Y-%m-%dT%H:%M:%S.%fZ"]
    for timestamp_format in formats:
        try:
            return datetime.strptime(value, timestamp_format)
        except ValueError:
            continue
    raise ReviewError(
        code="REVIEW_TIMESTAMP_INVALID",
        message="timestamp must be UTC ISO-8601 with trailing Z",
    )


def _format_utc_timestamp(value: datetime) -> str:
    return value.strftime(ISO_8601_UTC_Z)


def _stable_id(prefix: str, parts: List[str]) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()
    return "%s-%s" % (prefix, digest[:12])


class ReviewQueueService:
    def __init__(
        self,
        sla_seconds: int = DEFAULT_REVIEW_SLA_SECONDS,
        now_provider: Optional[Callable[[], datetime]] = None,
        decision_log_path: Optional[Path] = None,
    ) -> None:
        if int(sla_seconds) <= 0:
            raise ReviewError(
                code="REVIEW_SLA_INVALID",
                message="sla_seconds must be greater than zero",
            )

        self._sla_seconds = int(sla_seconds)
        self._now_provider = now_provider
        self._decision_log_path = decision_log_path
        self._queue_by_variant = {}  # type: Dict[str, Dict[str, Any]]
        self._decision_log = []  # type: List[Dict[str, Any]]

    def enqueue_item(
        self,
        *,
        variant_id: str,
        locale: str,
        policy: Dict[str, Any],
        originality: Dict[str, Any],
        cost: Dict[str, Any],
        queued_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_variant_id = str(variant_id or "").strip()
        if not normalized_variant_id:
            raise ReviewError(
                code="REVIEW_VARIANT_REQUIRED",
                message="variant_id is required",
            )
        if normalized_variant_id in self._queue_by_variant:
            raise ReviewError(
                code="REVIEW_VARIANT_ALREADY_QUEUED",
                message="variant is already queued",
            )

        queued_at_timestamp = queued_at or _format_utc_timestamp(self._now())
        queued_datetime = _parse_utc_timestamp(queued_at_timestamp)
        expires_at = _format_utc_timestamp(
            queued_datetime + timedelta(seconds=self._sla_seconds)
        )
        review_item = {
            "review_item_id": _stable_id("review", [normalized_variant_id, queued_at_timestamp]),
            "variant_id": normalized_variant_id,
            "locale": str(locale),
            "policy": {
                "result_code": str(policy.get("result_code", "PASS")),
                "policy_code": str(policy.get("policy_code", "PASS")),
            },
            "originality": {
                "similarity_score": round(float(originality.get("similarity_score", 0.0)), 4),
                "threshold": round(float(originality.get("threshold", 1.0)), 4),
                "result_code": str(originality.get("result_code", "PASS")),
            },
            "cost": {
                "estimated_usd": round(float(cost.get("estimated_usd", 0.0)), 4),
                "currency": str(cost.get("currency", "USD")),
            },
            "status": "pending",
            "publish_eligible": False,
            "queued_at": queued_at_timestamp,
            "expires_at": expires_at,
            "updated_at": queued_at_timestamp,
            "decision_id": None,
        }
        self._queue_by_variant[normalized_variant_id] = review_item
        return self._snapshot_item(review_item)

    def enqueue_from_localization_result(
        self,
        *,
        script_draft: Dict[str, Any],
        localized_output: Dict[str, Any],
        estimated_cost_usd: float,
        queued_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        variant = localized_output.get("variant")
        policy = localized_output.get("policy")
        if not isinstance(variant, dict):
            raise ReviewError(
                code="REVIEW_VARIANT_PAYLOAD_INVALID",
                message="localized_output.variant is required",
            )
        if not isinstance(policy, dict):
            raise ReviewError(
                code="REVIEW_POLICY_PAYLOAD_INVALID",
                message="localized_output.policy is required",
            )

        return self.enqueue_item(
            variant_id=str(variant.get("variant_id", "")),
            locale=str(variant.get("locale", "")),
            policy={
                "result_code": policy.get("result_code", "PASS"),
                "policy_code": policy.get("policy_code", "PASS"),
            },
            originality={
                "similarity_score": script_draft.get("similarity_score", 0.0),
                "threshold": script_draft.get("originality_threshold", 1.0),
                "result_code": script_draft.get("result_code", "PASS"),
            },
            cost={
                "estimated_usd": estimated_cost_usd,
                "currency": "USD",
            },
            queued_at=queued_at,
        )

    def list_pending_queue(self, now_timestamp: Optional[str] = None) -> Dict[str, Any]:
        self._expire_items(now_timestamp=now_timestamp)
        pending_items = []  # type: List[Dict[str, Any]]
        for variant_id in sorted(self._queue_by_variant.keys()):
            item = self._queue_by_variant[variant_id]
            if item["status"] == "pending":
                pending_items.append(self._snapshot_item(item))
        return {
            "status": "ok",
            "result_code": "PASS",
            "sla_seconds": self._sla_seconds,
            "items": pending_items,
        }

    def get_item(self, variant_id: str, now_timestamp: Optional[str] = None) -> Dict[str, Any]:
        self._expire_items(now_timestamp=now_timestamp)
        item = self._queue_by_variant.get(variant_id)
        if item is None:
            raise ReviewError(
                code="REVIEW_ITEM_NOT_FOUND",
                message="review item was not found",
                http_status=404,
            )
        return self._snapshot_item(item)

    def record_decision(
        self,
        *,
        variant_id: str,
        decision: str,
        reviewer_id: str,
        reviewed_at: Optional[str] = None,
        decision_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_variant_id = str(variant_id or "").strip()
        if normalized_variant_id not in self._queue_by_variant:
            raise ReviewError(
                code="REVIEW_ITEM_NOT_FOUND",
                message="review item was not found",
                http_status=404,
            )

        review_timestamp = reviewed_at or _format_utc_timestamp(self._now())
        self._expire_items(now_timestamp=review_timestamp)
        item = self._queue_by_variant[normalized_variant_id]

        if item["status"] == "expired":
            raise ReviewError(
                code="REVIEW_ITEM_EXPIRED",
                message="review item expired and cannot be decided",
                http_status=409,
            )
        if item["status"] != "pending":
            raise ReviewError(
                code="REVIEW_DECISION_IMMUTABLE",
                message="review decision is immutable once recorded",
                http_status=409,
            )

        normalized_decision = str(decision or "").strip().lower()
        normalized_reviewer = str(reviewer_id or "").strip()
        if not normalized_reviewer:
            raise ReviewError(
                code="REVIEW_REVIEWER_REQUIRED",
                message="reviewer_id is required",
            )

        if normalized_decision not in ["approved", "rejected"]:
            raise ReviewError(
                code="REVIEW_DECISION_INVALID",
                message="decision must be approved or rejected",
            )

        if normalized_decision == "approved":
            resolved_decision_code = "APPROVED_MANUAL_REVIEW"
        else:
            resolved_decision_code = str(decision_code or "").strip() or "REJECTED_POLICY"
            if resolved_decision_code not in ["REJECTED_POLICY", "REJECTED_ORIGINALITY"]:
                raise ReviewError(
                    code="REVIEW_DECISION_CODE_INVALID",
                    message="rejected decisions must use REJECTED_POLICY or REJECTED_ORIGINALITY",
                )

        decision_entry = self._append_decision(
            variant_id=normalized_variant_id,
            decision=normalized_decision,
            decision_code=resolved_decision_code,
            reviewer_id=normalized_reviewer,
            reviewed_at=review_timestamp,
        )

        item["status"] = normalized_decision
        item["publish_eligible"] = normalized_decision == "approved"
        item["updated_at"] = review_timestamp
        item["decision_id"] = decision_entry["decision_id"]

        return {
            "status": "decision_saved",
            "result_code": "PASS",
            "message": "Decision saved",
            "item": self._snapshot_item(item),
            "decision": decision_entry,
        }

    def list_decisions(self) -> List[Dict[str, Any]]:
        return [dict(entry) for entry in self._decision_log]

    def check_publish_eligibility(
        self,
        variant_id: str,
        now_timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._expire_items(now_timestamp=now_timestamp)
        item = self._queue_by_variant.get(variant_id)
        if item is None:
            raise ReviewError(
                code="REVIEW_ITEM_NOT_FOUND",
                message="review item was not found",
                http_status=404,
            )

        if item["status"] != "approved":
            raise ReviewError(
                code=PUBLISH_BLOCK_CODE,
                message="human approval is required before publish",
                http_status=409,
            )

        return {
            "status": "publish_eligible",
            "result_code": "PASS",
            "variant_id": variant_id,
            "review_status": item["status"],
        }

    def _snapshot_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "review_item_id": item["review_item_id"],
            "variant_id": item["variant_id"],
            "locale": item["locale"],
            "policy": dict(item["policy"]),
            "originality": dict(item["originality"]),
            "cost": dict(item["cost"]),
            "status": item["status"],
            "publish_eligible": item["publish_eligible"],
            "queued_at": item["queued_at"],
            "expires_at": item["expires_at"],
            "updated_at": item["updated_at"],
            "decision_id": item["decision_id"],
        }

    def _append_decision(
        self,
        *,
        variant_id: str,
        decision: str,
        decision_code: str,
        reviewer_id: str,
        reviewed_at: str,
    ) -> Dict[str, Any]:
        decision_entry = {
            "decision_id": _stable_id(
                "decision",
                [variant_id, decision, decision_code, reviewer_id, reviewed_at],
            ),
            "variant_id": variant_id,
            "decision": decision,
            "decision_code": decision_code,
            "reviewer_id": reviewer_id,
            "reviewed_at": reviewed_at,
        }
        validate_contract(entity_name="approval_decision", payload=decision_entry)
        self._decision_log.append(dict(decision_entry))
        if self._decision_log_path is not None:
            self._decision_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._decision_log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(decision_entry, sort_keys=True) + "\n")
        return decision_entry

    def _expire_items(self, now_timestamp: Optional[str] = None) -> None:
        if now_timestamp is None:
            now_dt = self._now()
            now_value = _format_utc_timestamp(now_dt)
        else:
            now_value = str(now_timestamp)
            now_dt = _parse_utc_timestamp(now_value)

        for variant_id in sorted(self._queue_by_variant.keys()):
            item = self._queue_by_variant[variant_id]
            if item["status"] != "pending":
                continue
            expiry_dt = _parse_utc_timestamp(item["expires_at"])
            if now_dt < expiry_dt:
                continue

            item["status"] = "expired"
            item["publish_eligible"] = False
            item["updated_at"] = now_value
            expiry_decision = self._append_decision(
                variant_id=item["variant_id"],
                decision="expired",
                decision_code="EXPIRED_SLA",
                reviewer_id="system-sla-guard",
                reviewed_at=now_value,
            )
            item["decision_id"] = expiry_decision["decision_id"]

    def _now(self) -> datetime:
        if self._now_provider is None:
            return datetime.utcnow()
        return self._now_provider()
