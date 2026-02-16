from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

from money.localization import SUPPORTED_LOCALES
from money.publishing import SUPPORTED_PUBLISH_PLATFORMS


ISO_DATE = "%Y-%m-%d"
WEEKLY_WINDOW_DAYS = 7


class MetricsError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def _normalize_locale(raw_locale: str, supported_locales: Sequence[str]) -> str:
    value = str(raw_locale or "").strip().upper()
    if value not in supported_locales:
        raise MetricsError(
            code="METRICS_LOCALE_UNSUPPORTED",
            message="unsupported locale: %s" % value,
        )
    return value


def _normalize_platform(raw_platform: str, supported_platforms: Sequence[str]) -> str:
    value = str(raw_platform or "").strip().lower()
    if value not in supported_platforms:
        raise MetricsError(
            code="METRICS_PLATFORM_UNSUPPORTED",
            message="unsupported platform: %s" % value,
        )
    return value


def _parse_iso_date(raw_value: str) -> date:
    value = str(raw_value or "").strip()
    try:
        return datetime.strptime(value, ISO_DATE).date()
    except ValueError:
        raise MetricsError(
            code="METRICS_DATE_INVALID",
            message="date must use YYYY-MM-DD",
        )


def _round_metric(value: float) -> float:
    return round(float(value), 6)


class WeeklyRevenueKpiService:
    def __init__(
        self,
        events: Optional[List[Dict[str, Any]]] = None,
        supported_locales: Optional[Sequence[str]] = None,
        supported_platforms: Optional[Sequence[str]] = None,
    ) -> None:
        self._supported_locales = list(supported_locales or SUPPORTED_LOCALES)
        self._supported_platforms = list(supported_platforms or SUPPORTED_PUBLISH_PLATFORMS)
        self._events = []  # type: List[Dict[str, Any]]

        for entry in events or []:
            self.add_event(
                event_date=str(entry.get("event_date", "")),
                locale=str(entry.get("locale", "")),
                platform=str(entry.get("platform", "")),
                gross_revenue=float(entry.get("gross_revenue", 0.0)),
                net_revenue=float(entry.get("net_revenue", 0.0)),
                impressions=int(entry.get("impressions", 0)),
                approvals=int(entry.get("approvals", 0)),
                review_total=int(entry.get("review_total", 0)),
                publish_success=int(entry.get("publish_success", 0)),
                publish_attempts=int(entry.get("publish_attempts", 0)),
            )

    def add_event(
        self,
        *,
        event_date: str,
        locale: str,
        platform: str,
        gross_revenue: float,
        net_revenue: float,
        impressions: int,
        approvals: int,
        review_total: int,
        publish_success: int,
        publish_attempts: int,
    ) -> Dict[str, Any]:
        normalized_locale = _normalize_locale(locale, self._supported_locales)
        normalized_platform = _normalize_platform(platform, self._supported_platforms)
        resolved_date = _parse_iso_date(event_date)

        gross = _round_metric(gross_revenue)
        net = _round_metric(net_revenue)
        if gross < 0 or net < 0:
            raise MetricsError(
                code="METRICS_REVENUE_NEGATIVE",
                message="gross_revenue and net_revenue must be non-negative",
            )

        event = {
            "event_date": resolved_date.strftime(ISO_DATE),
            "locale": normalized_locale,
            "platform": normalized_platform,
            "gross_revenue": gross,
            "net_revenue": net,
            "impressions": self._bounded_int(impressions, "impressions"),
            "approvals": self._bounded_int(approvals, "approvals"),
            "review_total": self._bounded_int(review_total, "review_total"),
            "publish_success": self._bounded_int(publish_success, "publish_success"),
            "publish_attempts": self._bounded_int(publish_attempts, "publish_attempts"),
        }
        self._events.append(event)
        return dict(event)

    def query_weekly_kpis(
        self,
        *,
        locale: str,
        platform: Optional[str] = None,
        as_of_date: Optional[str] = None,
        window_days: int = WEEKLY_WINDOW_DAYS,
    ) -> Dict[str, Any]:
        if int(window_days) != WEEKLY_WINDOW_DAYS:
            raise MetricsError(
                code="METRICS_WINDOW_DAYS_FIXED",
                message="window_days must be exactly 7",
            )

        normalized_locale = _normalize_locale(locale, self._supported_locales)
        normalized_platform = None  # type: Optional[str]
        if platform is not None and str(platform).strip():
            normalized_platform = _normalize_platform(platform, self._supported_platforms)

        end_date = _parse_iso_date(as_of_date) if as_of_date else datetime.utcnow().date()
        start_date = end_date - timedelta(days=WEEKLY_WINDOW_DAYS - 1)

        matched = []  # type: List[Dict[str, Any]]
        for item in self._events:
            item_date = _parse_iso_date(item["event_date"])
            if item_date < start_date or item_date > end_date:
                continue
            if item["locale"] != normalized_locale:
                continue
            if normalized_platform is not None and item["platform"] != normalized_platform:
                continue
            matched.append(item)

        gross_revenue = _round_metric(sum(float(item["gross_revenue"]) for item in matched))
        net_revenue = _round_metric(sum(float(item["net_revenue"]) for item in matched))
        impressions = sum(int(item["impressions"]) for item in matched)
        approvals = sum(int(item["approvals"]) for item in matched)
        review_total = sum(int(item["review_total"]) for item in matched)
        publish_success = sum(int(item["publish_success"]) for item in matched)
        publish_attempts = sum(int(item["publish_attempts"]) for item in matched)

        rpm_proxy = 0.0
        if impressions > 0:
            rpm_proxy = _round_metric((net_revenue / float(impressions)) * 1000.0)

        approval_rate = 0.0
        if review_total > 0:
            approval_rate = _round_metric(float(approvals) / float(review_total))

        publish_success_rate = 0.0
        if publish_attempts > 0:
            publish_success_rate = _round_metric(float(publish_success) / float(publish_attempts))

        return {
            "status": "ok",
            "result_code": "PASS",
            "window_days": WEEKLY_WINDOW_DAYS,
            "window_start_date": start_date.strftime(ISO_DATE),
            "window_end_date": end_date.strftime(ISO_DATE),
            "locale": normalized_locale,
            "platform": normalized_platform,
            "gross_revenue": gross_revenue,
            "net_revenue": net_revenue,
            "rpm_proxy": rpm_proxy,
            "approval_rate": approval_rate,
            "publish_success_rate": publish_success_rate,
            "event_count": len(matched),
        }

    @staticmethod
    def _bounded_int(raw_value: int, field_name: str) -> int:
        value = int(raw_value)
        if value < 0:
            raise MetricsError(
                code="METRICS_COUNT_INVALID",
                message="%s must be non-negative" % field_name,
            )
        return value
