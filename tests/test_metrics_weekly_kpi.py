from money.metrics import (
    MetricsApiApp,
    MetricsError,
    WeeklyRevenueKpiService,
    get_revenue_weekly_metrics,
    invoke_json_request,
)


def _service_with_seed_data() -> WeeklyRevenueKpiService:
    return WeeklyRevenueKpiService(
        events=[
            {
                "event_date": "2026-02-16",
                "locale": "EN-US",
                "platform": "youtube",
                "gross_revenue": 120.0,
                "net_revenue": 96.0,
                "impressions": 50000,
                "approvals": 8,
                "review_total": 10,
                "publish_success": 4,
                "publish_attempts": 5,
            },
            {
                "event_date": "2026-02-13",
                "locale": "EN-US",
                "platform": "youtube",
                "gross_revenue": 80.0,
                "net_revenue": 64.0,
                "impressions": 30000,
                "approvals": 5,
                "review_total": 6,
                "publish_success": 3,
                "publish_attempts": 4,
            },
            {
                "event_date": "2026-02-11",
                "locale": "EN-US",
                "platform": "tiktok",
                "gross_revenue": 45.0,
                "net_revenue": 34.0,
                "impressions": 20000,
                "approvals": 2,
                "review_total": 3,
                "publish_success": 1,
                "publish_attempts": 2,
            },
            {
                "event_date": "2026-02-09",
                "locale": "EN-US",
                "platform": "youtube",
                "gross_revenue": 999.0,
                "net_revenue": 888.0,
                "impressions": 999999,
                "approvals": 90,
                "review_total": 90,
                "publish_success": 90,
                "publish_attempts": 90,
            },
            {
                "event_date": "2026-02-16",
                "locale": "JA-JP",
                "platform": "youtube",
                "gross_revenue": 300.0,
                "net_revenue": 255.0,
                "impressions": 110000,
                "approvals": 11,
                "review_total": 12,
                "publish_success": 5,
                "publish_attempts": 6,
            },
        ]
    )


def test_weekly_kpi_query_returns_numeric_fields_with_fixed_trailing_window() -> None:
    service = _service_with_seed_data()

    payload = get_revenue_weekly_metrics(
        service,
        locale="EN-US",
        platform="youtube",
        as_of_date="2026-02-16",
    )

    assert payload["status"] == "ok"
    assert payload["result_code"] == "PASS"
    assert payload["window_days"] == 7
    assert payload["window_start_date"] == "2026-02-10"
    assert payload["window_end_date"] == "2026-02-16"

    assert isinstance(payload["gross_revenue"], float)
    assert isinstance(payload["net_revenue"], float)
    assert isinstance(payload["rpm_proxy"], float)
    assert isinstance(payload["approval_rate"], float)
    assert isinstance(payload["publish_success_rate"], float)

    assert payload["gross_revenue"] == 200.0
    assert payload["net_revenue"] == 160.0
    assert payload["rpm_proxy"] == 2.0
    assert payload["approval_rate"] == 0.8125
    assert payload["publish_success_rate"] == 0.777778


def test_weekly_kpi_query_enforces_locale_and_platform_filters() -> None:
    service = _service_with_seed_data()

    locale_payload = service.query_weekly_kpis(locale="JA-JP", as_of_date="2026-02-16")
    assert locale_payload["gross_revenue"] == 300.0
    assert locale_payload["net_revenue"] == 255.0

    platform_payload = service.query_weekly_kpis(
        locale="EN-US",
        platform="tiktok",
        as_of_date="2026-02-16",
    )
    assert platform_payload["gross_revenue"] == 45.0
    assert platform_payload["net_revenue"] == 34.0
    assert platform_payload["event_count"] == 1


def test_metrics_validation_rejects_invalid_filters_and_non_weekly_window() -> None:
    service = _service_with_seed_data()
    app = MetricsApiApp(service)

    try:
        service.query_weekly_kpis(locale="FR-FR", as_of_date="2026-02-16")
    except MetricsError as error:
        assert error.code == "METRICS_LOCALE_UNSUPPORTED"
    else:
        raise AssertionError("unsupported locale should raise MetricsError")

    status_code, payload = invoke_json_request(
        app,
        method="GET",
        path="/metrics/revenue-weekly",
        query_string="locale=EN-US&platform=facebook",
    )
    assert status_code == 400
    assert payload["error_code"] == "METRICS_PLATFORM_UNSUPPORTED"

    status_code, payload = invoke_json_request(
        app,
        method="GET",
        path="/metrics/revenue-weekly",
        query_string="locale=EN-US&window_days=30",
    )
    assert status_code == 400
    assert payload["error_code"] == "METRICS_WINDOW_DAYS_FIXED"
