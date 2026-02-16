import io
import json
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs

from money.metrics.service import MetricsError, WeeklyRevenueKpiService


class MetricsApiApp:
    def __init__(self, metrics_service: WeeklyRevenueKpiService) -> None:
        self._metrics_service = metrics_service

    def __call__(self, environ: Dict[str, Any], start_response: Any) -> Any:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", "/"))

        try:
            if method == "GET" and path == "/metrics/revenue-weekly":
                query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=False)
                locale = _required_query_value(query, "locale")
                platform = _optional_query_value(query, "platform")
                as_of_date = _optional_query_value(query, "as_of_date")
                window_days = _optional_query_value(query, "window_days")

                payload = self._metrics_service.query_weekly_kpis(
                    locale=locale,
                    platform=platform,
                    as_of_date=as_of_date,
                    window_days=_parse_window_days(window_days),
                )
                return self._json_response(start_response, 200, payload)

            return self._json_response(
                start_response,
                404,
                {
                    "status": "not_found",
                    "result_code": "API_ROUTE_NOT_FOUND",
                },
            )
        except MetricsError as error:
            return self._json_response(
                start_response,
                error.http_status,
                {
                    "status": "blocked",
                    "result_code": error.code,
                    "error_code": error.code,
                    "message": str(error),
                },
            )

    def _json_response(
        self,
        start_response: Any,
        status_code: int,
        payload: Dict[str, Any],
    ) -> Any:
        body = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
        status_line = "%d %s" % (status_code, _http_reason_phrase(status_code))
        headers = [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ]
        start_response(status_line, headers)
        return [body]


def _required_query_value(query: Dict[str, Any], key: str) -> str:
    value = _optional_query_value(query, key)
    if value is None:
        raise MetricsError(
            code="METRICS_QUERY_PARAM_REQUIRED",
            message="query parameter is required: %s" % key,
        )
    return value


def _optional_query_value(query: Dict[str, Any], key: str) -> Optional[str]:
    values = query.get(key)
    if not values:
        return None
    first = str(values[0]).strip()
    if not first:
        return None
    return first


def _http_reason_phrase(status_code: int) -> str:
    reasons = {
        200: "OK",
        400: "Bad Request",
        404: "Not Found",
    }
    return reasons.get(status_code, "OK")


def _parse_window_days(raw_value: Optional[str]) -> int:
    if raw_value is None:
        return 7
    try:
        return int(raw_value)
    except ValueError:
        raise MetricsError(
            code="METRICS_WINDOW_DAYS_INVALID",
            message="window_days must be an integer",
        )


def get_revenue_weekly_metrics(
    metrics_service: WeeklyRevenueKpiService,
    *,
    locale: str,
    platform: Optional[str] = None,
    as_of_date: Optional[str] = None,
) -> Dict[str, Any]:
    return metrics_service.query_weekly_kpis(
        locale=locale,
        platform=platform,
        as_of_date=as_of_date,
        window_days=7,
    )


def invoke_json_request(
    app: MetricsApiApp,
    method: str,
    path: str,
    query_string: str = "",
) -> Tuple[int, Dict[str, Any]]:
    captured_status = {"value": "200 OK"}

    def _start_response(status: str, _headers: Any) -> None:
        captured_status["value"] = status

    environ = {
        "REQUEST_METHOD": method.upper(),
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "CONTENT_LENGTH": "0",
        "wsgi.input": io.BytesIO(b""),
    }
    body = b"".join(app(environ, _start_response))
    status_code = int(captured_status["value"].split(" ")[0])
    if not body:
        return status_code, {}
    return status_code, json.loads(body.decode("utf-8"))
