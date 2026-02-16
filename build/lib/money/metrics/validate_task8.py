import json
from pathlib import Path
from typing import Any, Dict

from money.metrics.api import get_revenue_weekly_metrics
from money.metrics.service import WeeklyRevenueKpiService


ROOT_DIR = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT_DIR / ".sisyphus" / "evidence"


def _write_evidence(file_name: str, payload: Dict[str, Any]) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EVIDENCE_DIR / file_name
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def run_task8_validation() -> Dict[str, Any]:
    service = WeeklyRevenueKpiService(
        events=[
            {
                "event_date": "2026-02-16",
                "locale": "EN-US",
                "platform": "youtube",
                "gross_revenue": 240.0,
                "net_revenue": 198.0,
                "impressions": 120000,
                "approvals": 18,
                "review_total": 20,
                "publish_success": 9,
                "publish_attempts": 10,
            },
            {
                "event_date": "2026-02-12",
                "locale": "EN-US",
                "platform": "youtube",
                "gross_revenue": 100.0,
                "net_revenue": 79.0,
                "impressions": 60000,
                "approvals": 6,
                "review_total": 8,
                "publish_success": 4,
                "publish_attempts": 5,
            },
            {
                "event_date": "2026-02-09",
                "locale": "EN-US",
                "platform": "youtube",
                "gross_revenue": 999.0,
                "net_revenue": 888.0,
                "impressions": 999999,
                "approvals": 100,
                "review_total": 100,
                "publish_success": 100,
                "publish_attempts": 100,
            },
        ]
    )

    payload = get_revenue_weekly_metrics(
        service,
        locale="EN-US",
        platform="youtube",
        as_of_date="2026-02-16",
    )

    kpi_fields = [
        "gross_revenue",
        "net_revenue",
        "rpm_proxy",
        "approval_rate",
        "publish_success_rate",
    ]
    checks = {
        "kpi_fields_are_numeric": all(
            isinstance(payload.get(field), (int, float)) for field in kpi_fields
        ),
        "window_days_is_fixed_to_7": payload.get("window_days") == 7,
        "window_bounds_are_trailing_7_days": payload.get("window_start_date") == "2026-02-10"
        and payload.get("window_end_date") == "2026-02-16",
        "gross_and_net_are_distinct": payload.get("gross_revenue") != payload.get("net_revenue"),
    }

    return {
        "task": "task-8-weekly-revenue-kpi",
        "query": {
            "locale": "EN-US",
            "platform": "youtube",
            "as_of_date": "2026-02-16",
        },
        "result": payload,
        "checks": checks,
    }


def main() -> int:
    payload = run_task8_validation()
    evidence_path = _write_evidence("task-8-kpi-schema.json", payload)
    print(evidence_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
