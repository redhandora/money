import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from money.contracts.validate_task1 import validate_contract
from money.review.service import PUBLISH_BLOCK_CODE, ReviewError, ReviewQueueService


ISO_8601_UTC_Z = "%Y-%m-%dT%H:%M:%SZ"
SUPPORTED_PUBLISH_PLATFORMS = ["youtube", "tiktok"]

PUBLISH_RECEIPT_SUCCESS = "success"
PUBLISH_RECEIPT_FAILED_RETRYABLE = "failed_retryable"
PUBLISH_RECEIPT_FAILED_TERMINAL = "failed_terminal"

DEFAULT_PLATFORM_CONTROLS = {
    "youtube": {
        "window_start_hour_utc": 8,
        "window_end_hour_utc": 23,
        "max_publishes_per_hour": 3,
    },
    "tiktok": {
        "window_start_hour_utc": 6,
        "window_end_hour_utc": 22,
        "max_publishes_per_hour": 2,
    },
}


class PublishError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def _stable_id(prefix: str, parts: List[str]) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()
    return "%s-%s" % (prefix, digest[:12])


def _parse_utc_timestamp(raw_timestamp: str) -> datetime:
    value = str(raw_timestamp or "").strip()
    formats = [ISO_8601_UTC_Z, "%Y-%m-%dT%H:%M:%S.%fZ"]
    for timestamp_format in formats:
        try:
            return datetime.strptime(value, timestamp_format)
        except ValueError:
            continue
    raise PublishError(
        code="PUBLISH_TIMESTAMP_INVALID",
        message="timestamp must be UTC ISO-8601 with trailing Z",
    )


def _format_utc_timestamp(value: datetime) -> str:
    return value.strftime(ISO_8601_UTC_Z)


def _normalize_targets(raw_targets: Any) -> List[str]:
    if raw_targets is None:
        return list(SUPPORTED_PUBLISH_PLATFORMS)
    if not isinstance(raw_targets, list) or not raw_targets:
        raise PublishError(
            code="PUBLISH_TARGETS_INVALID",
            message="targets must be a non-empty list",
        )

    deduped = []  # type: List[str]
    seen = set()
    for value in raw_targets:
        normalized = str(value or "").strip().lower()
        if normalized not in SUPPORTED_PUBLISH_PLATFORMS:
            raise PublishError(
                code="PUBLISH_PLATFORM_UNSUPPORTED",
                message="unsupported platform: %s" % normalized,
            )
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def build_publish_request(
    approved_payload: Dict[str, Any],
    *,
    idempotency_key: str,
    scheduled_for: Optional[str] = None,
) -> Dict[str, Any]:
    normalized_key = str(idempotency_key or "").strip()
    if not normalized_key:
        raise PublishError(
            code="PUBLISH_IDEMPOTENCY_KEY_REQUIRED",
            message="idempotency_key is required",
        )

    variant_id = str(approved_payload.get("variant_id", "")).strip()
    if not variant_id:
        raise PublishError(
            code="PUBLISH_VARIANT_REQUIRED",
            message="variant_id is required",
        )

    locale = str(approved_payload.get("locale", "")).strip()
    if not locale:
        raise PublishError(
            code="PUBLISH_LOCALE_REQUIRED",
            message="locale is required",
        )

    localized_script = str(approved_payload.get("localized_script", "")).strip()
    if not localized_script:
        raise PublishError(
            code="PUBLISH_SCRIPT_REQUIRED",
            message="localized_script is required",
        )

    review_status = str(approved_payload.get("review_status", "")).strip().lower()
    if review_status != "approved":
        raise PublishError(
            code=PUBLISH_BLOCK_CODE,
            message="human approval is required before publish",
            http_status=409,
        )

    now_timestamp = _format_utc_timestamp(datetime.utcnow())
    resolved_schedule = str(scheduled_for or approved_payload.get("scheduled_for") or now_timestamp)
    _parse_utc_timestamp(resolved_schedule)

    return {
        "variant_id": variant_id,
        "locale": locale,
        "localized_script": localized_script,
        "review_status": review_status,
        "idempotency_key": normalized_key,
        "scheduled_for": resolved_schedule,
        "targets": _normalize_targets(approved_payload.get("targets")),
    }


def build_platform_publish_request(
    publish_request: Dict[str, Any],
    platform: str,
) -> Dict[str, Any]:
    normalized_platform = str(platform or "").strip().lower()
    if normalized_platform not in SUPPORTED_PUBLISH_PLATFORMS:
        raise PublishError(
            code="PUBLISH_PLATFORM_UNSUPPORTED",
            message="unsupported platform: %s" % normalized_platform,
        )

    base_parts = [
        publish_request["variant_id"],
        normalized_platform,
        publish_request["idempotency_key"],
    ]
    return {
        "platform": normalized_platform,
        "variant_id": publish_request["variant_id"],
        "locale": publish_request["locale"],
        "localized_script": publish_request["localized_script"],
        "scheduled_for": publish_request["scheduled_for"],
        "idempotency_key": publish_request["idempotency_key"],
        "platform_submission_id": _stable_id("submission", base_parts),
    }


class PublisherAdapter:
    platform = ""

    def publish(self, request: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class DeterministicPublisherAdapter(PublisherAdapter):
    def __init__(
        self,
        platform: str,
        retryable_failure_keys: Optional[List[str]] = None,
        terminal_failure_keys: Optional[List[str]] = None,
    ) -> None:
        self.platform = platform
        self._retryable_failure_keys = set(retryable_failure_keys or [])
        self._terminal_failure_keys = set(terminal_failure_keys or [])
        self.publish_call_count = 0

    def publish(self, request: Dict[str, Any]) -> Dict[str, Any]:
        self.publish_call_count += 1
        key = str(request.get("idempotency_key", ""))
        if key in self._retryable_failure_keys:
            raise PublishError(
                code="PUBLISH_PLATFORM_RETRYABLE_FAILURE",
                message="retryable upstream failure from %s" % self.platform,
                http_status=503,
            )
        if key in self._terminal_failure_keys:
            raise PublishError(
                code="PUBLISH_PLATFORM_TERMINAL_FAILURE",
                message="terminal upstream failure from %s" % self.platform,
                http_status=422,
            )

        platform_post_id = _stable_id(
            "%s-post" % self.platform,
            [
                str(request.get("variant_id", "")),
                key,
                str(request.get("platform_submission_id", "")),
            ],
        )
        return {
            "status": "published",
            "platform_post_id": platform_post_id,
        }


class YouTubeShortsAdapter(DeterministicPublisherAdapter):
    def __init__(
        self,
        retryable_failure_keys: Optional[List[str]] = None,
        terminal_failure_keys: Optional[List[str]] = None,
    ) -> None:
        DeterministicPublisherAdapter.__init__(
            self,
            platform="youtube",
            retryable_failure_keys=retryable_failure_keys,
            terminal_failure_keys=terminal_failure_keys,
        )


class TikTokPublisherAdapter(DeterministicPublisherAdapter):
    def __init__(
        self,
        retryable_failure_keys: Optional[List[str]] = None,
        terminal_failure_keys: Optional[List[str]] = None,
    ) -> None:
        DeterministicPublisherAdapter.__init__(
            self,
            platform="tiktok",
            retryable_failure_keys=retryable_failure_keys,
            terminal_failure_keys=terminal_failure_keys,
        )


class PublisherService:
    def __init__(
        self,
        review_service: Optional[ReviewQueueService] = None,
        adapters: Optional[Dict[str, PublisherAdapter]] = None,
        platform_controls: Optional[Dict[str, Dict[str, int]]] = None,
        now_provider: Optional[Callable[[], datetime]] = None,
        receipt_log_path: Optional[Path] = None,
    ) -> None:
        self._review_service = review_service
        self._adapters = adapters or {
            "youtube": YouTubeShortsAdapter(),
            "tiktok": TikTokPublisherAdapter(),
        }
        self._platform_controls = platform_controls or dict(DEFAULT_PLATFORM_CONTROLS)
        self._now_provider = now_provider
        self._receipt_log_path = receipt_log_path

        self._receipts = []  # type: List[Dict[str, Any]]
        self._receipts_by_idempotency = {}  # type: Dict[str, Dict[str, Any]]
        self._publish_attempts_by_platform = {}  # type: Dict[str, List[str]]

    def publish(
        self,
        *,
        approved_payload: Dict[str, Any],
        idempotency_key: str,
        scheduled_for: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_key = str(idempotency_key or "").strip()
        if normalized_key in self._receipts_by_idempotency:
            return self._clone_response(self._receipts_by_idempotency[normalized_key])

        publish_request = build_publish_request(
            approved_payload,
            idempotency_key=normalized_key,
            scheduled_for=scheduled_for,
        )
        self._check_human_gate(publish_request)

        scheduled_dt = _parse_utc_timestamp(publish_request["scheduled_for"])
        published_at = _format_utc_timestamp(self._now())

        platform_receipts = []  # type: List[Dict[str, Any]]
        has_retryable_failure = False
        has_terminal_failure = False

        for platform in publish_request["targets"]:
            self._assert_schedule_window(platform=platform, scheduled_dt=scheduled_dt)
            self._enforce_rate_limit(platform=platform, scheduled_dt=scheduled_dt)
            platform_request = build_platform_publish_request(publish_request, platform)
            platform_receipt = self._publish_to_platform(
                platform_request=platform_request,
                published_at=published_at,
            )
            platform_receipts.append(platform_receipt)

            if platform_receipt["publish_status"] == PUBLISH_RECEIPT_FAILED_RETRYABLE:
                has_retryable_failure = True
            if platform_receipt["publish_status"] == PUBLISH_RECEIPT_FAILED_TERMINAL:
                has_terminal_failure = True

        overall_status = "published"
        result_code = "PASS"
        if has_terminal_failure:
            overall_status = "publish_failed_terminal"
            result_code = "PUBLISH_FAILED_TERMINAL"
        elif has_retryable_failure:
            overall_status = "publish_partial_retryable"
            result_code = "PUBLISH_PARTIAL_RETRYABLE"

        response = {
            "status": overall_status,
            "result_code": result_code,
            "variant_id": publish_request["variant_id"],
            "idempotency_key": normalized_key,
            "scheduled_for": publish_request["scheduled_for"],
            "platform_receipts": platform_receipts,
        }
        self._receipts_by_idempotency[normalized_key] = self._clone_response(response)
        return self._clone_response(response)

    def list_receipts(self) -> List[Dict[str, Any]]:
        return [dict(receipt) for receipt in self._receipts]

    def _check_human_gate(self, publish_request: Dict[str, Any]) -> None:
        if self._review_service is None:
            return
        try:
            self._review_service.check_publish_eligibility(
                variant_id=publish_request["variant_id"],
                now_timestamp=publish_request["scheduled_for"],
            )
        except ReviewError as error:
            raise PublishError(
                code=error.code,
                message=str(error),
                http_status=error.http_status,
            )

    def _assert_schedule_window(self, platform: str, scheduled_dt: datetime) -> None:
        controls = self._platform_controls.get(platform)
        if controls is None:
            raise PublishError(
                code="PUBLISH_PLATFORM_CONTROL_MISSING",
                message="missing platform controls for %s" % platform,
            )

        start_hour = int(controls.get("window_start_hour_utc", -1))
        end_hour = int(controls.get("window_end_hour_utc", -1))
        if start_hour < 0 or start_hour > 23 or end_hour < 1 or end_hour > 24:
            raise PublishError(
                code="PUBLISH_WINDOW_CONFIG_INVALID",
                message="window hours must be in UTC hour range",
            )
        if start_hour >= end_hour:
            raise PublishError(
                code="PUBLISH_WINDOW_CONFIG_INVALID",
                message="window_start_hour_utc must be less than window_end_hour_utc",
            )

        if scheduled_dt.hour < start_hour or scheduled_dt.hour >= end_hour:
            raise PublishError(
                code="PUBLISH_WINDOW_CLOSED",
                message="%s publish window is closed for scheduled timestamp" % platform,
                http_status=409,
            )

    def _enforce_rate_limit(self, platform: str, scheduled_dt: datetime) -> None:
        controls = self._platform_controls[platform]
        max_per_hour = int(controls.get("max_publishes_per_hour", 0))
        if max_per_hour <= 0:
            raise PublishError(
                code="PUBLISH_RATE_LIMIT_CONFIG_INVALID",
                message="max_publishes_per_hour must be greater than zero",
            )

        hour_bucket = "%s-%02d" % (scheduled_dt.strftime("%Y%m%d"), scheduled_dt.hour)
        bucket_key = "%s:%s" % (platform, hour_bucket)
        attempts = self._publish_attempts_by_platform.setdefault(bucket_key, [])
        if len(attempts) >= max_per_hour:
            raise PublishError(
                code="PUBLISH_RATE_LIMIT_BACKOFF_REQUIRED",
                message="rate limit exceeded for %s in %s" % (platform, hour_bucket),
                http_status=429,
            )
        attempts.append(bucket_key)

    def _publish_to_platform(
        self,
        *,
        platform_request: Dict[str, Any],
        published_at: str,
    ) -> Dict[str, Any]:
        platform = platform_request["platform"]
        adapter = self._adapters.get(platform)
        if adapter is None:
            raise PublishError(
                code="PUBLISH_ADAPTER_NOT_CONFIGURED",
                message="adapter not configured for %s" % platform,
            )

        status = PUBLISH_RECEIPT_SUCCESS
        platform_post_id = ""
        try:
            response = adapter.publish(platform_request)
            platform_post_id = str(response.get("platform_post_id", "")).strip()
            if not platform_post_id:
                raise PublishError(
                    code="PUBLISH_PLATFORM_RESPONSE_INVALID",
                    message="platform response must include platform_post_id",
                )
        except PublishError as error:
            if error.code in [
                "PUBLISH_PLATFORM_RETRYABLE_FAILURE",
                "PUBLISH_RATE_LIMIT_BACKOFF_REQUIRED",
            ]:
                status = PUBLISH_RECEIPT_FAILED_RETRYABLE
            else:
                status = PUBLISH_RECEIPT_FAILED_TERMINAL
            platform_post_id = _stable_id(
                "%s-receipt" % platform,
                [
                    platform_request["variant_id"],
                    platform_request["idempotency_key"],
                    status,
                ],
            )

        receipt = {
            "receipt_id": _stable_id(
                "receipt",
                [
                    platform_request["variant_id"],
                    platform,
                    platform_request["idempotency_key"],
                ],
            ),
            "variant_id": platform_request["variant_id"],
            "platform": platform,
            "publish_status": status,
            "platform_post_id": platform_post_id,
            "idempotency_key": platform_request["idempotency_key"],
            "published_at": published_at,
        }
        validate_contract(entity_name="publish_receipt", payload=receipt)
        self._receipts.append(dict(receipt))
        if self._receipt_log_path is not None:
            self._receipt_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._receipt_log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(receipt, sort_keys=True) + "\n")
        return dict(receipt)

    def _clone_response(self, value: Dict[str, Any]) -> Dict[str, Any]:
        return json.loads(json.dumps(value, sort_keys=True))

    def _now(self) -> datetime:
        if self._now_provider is None:
            return datetime.utcnow()
        return self._now_provider()
