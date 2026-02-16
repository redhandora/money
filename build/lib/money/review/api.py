import io
import json
from wsgiref.simple_server import WSGIServer, make_server

from typing import Any, Dict, Optional, Tuple

from money.review.service import PUBLISH_BLOCK_CODE, ReviewError, ReviewQueueService


REVIEW_PAGE_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Human Review Queue</title>
    <style>
      :root {
        --paper: #f7efe1;
        --paper-deep: #eadfcd;
        --ink: #111313;
        --ink-soft: #3f4444;
        --accent: #d04f2d;
        --accent-soft: #f4b08f;
        --olive: #616f3a;
        --line: rgba(17, 19, 19, 0.18);
        --card: rgba(247, 239, 225, 0.86);
        --ok: #2f6b37;
        --warn: #9a5d13;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        min-height: 100vh;
        background:
          radial-gradient(circle at 12% 14%, rgba(208, 79, 45, 0.23), transparent 40%),
          radial-gradient(circle at 92% 6%, rgba(97, 111, 58, 0.21), transparent 34%),
          linear-gradient(165deg, var(--paper) 0%, var(--paper-deep) 100%);
        color: var(--ink);
        font-family: "Courier New", "Nimbus Mono PS", monospace;
        padding: 24px;
      }

      .grain::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        opacity: 0.06;
        background-image: radial-gradient(rgba(0, 0, 0, 0.8) 0.4px, transparent 0.4px);
        background-size: 3px 3px;
      }

      .panel {
        width: min(1100px, 100%);
        margin: 0 auto;
        border: 1px solid var(--line);
        border-radius: 20px;
        background: var(--card);
        backdrop-filter: blur(3px);
        box-shadow: 0 18px 48px rgba(17, 19, 19, 0.12);
        overflow: hidden;
      }

      .header {
        padding: 24px;
        border-bottom: 1px solid var(--line);
        display: grid;
        gap: 14px;
      }

      .eyebrow {
        text-transform: uppercase;
        letter-spacing: 0.15em;
        font-size: 11px;
        color: var(--ink-soft);
      }

      h1 {
        margin: 0;
        font-size: clamp(26px, 4.8vw, 44px);
        line-height: 1;
        font-family: "Palatino Linotype", "Book Antiqua", serif;
      }

      .meta {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }

      .badge {
        border: 1px solid var(--line);
        border-radius: 999px;
        padding: 6px 12px;
        font-size: 12px;
        background: rgba(255, 255, 255, 0.35);
      }

      .table-wrap {
        overflow-x: auto;
      }

      table {
        width: 100%;
        border-collapse: collapse;
      }

      th,
      td {
        text-align: left;
        padding: 14px 18px;
        border-bottom: 1px solid var(--line);
        font-size: 13px;
        vertical-align: top;
      }

      thead th {
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 11px;
        color: var(--ink-soft);
      }

      .stack {
        display: grid;
        gap: 2px;
      }

      .muted {
        color: var(--ink-soft);
      }

      .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      button {
        border: 1px solid var(--ink);
        border-radius: 999px;
        padding: 7px 13px;
        background: transparent;
        color: var(--ink);
        cursor: pointer;
        font: inherit;
        transition: transform 120ms ease, background 120ms ease;
      }

      select {
        border: 1px solid var(--line);
        border-radius: 999px;
        padding: 7px 10px;
        background: rgba(255, 255, 255, 0.4);
        color: var(--ink);
        font: inherit;
      }

      button:hover {
        transform: translateY(-1px);
      }

      button[data-kind="approve"] {
        border-color: var(--ok);
        color: var(--ok);
      }

      button[data-kind="approve"]:hover {
        background: rgba(47, 107, 55, 0.12);
      }

      button[data-kind="reject"] {
        border-color: var(--warn);
        color: var(--warn);
      }

      button[data-kind="reject"]:hover {
        background: rgba(154, 93, 19, 0.13);
      }

      .toast {
        position: fixed;
        right: 20px;
        bottom: 20px;
        border-radius: 12px;
        border: 1px solid var(--line);
        background: rgba(17, 19, 19, 0.92);
        color: #fef4e4;
        padding: 10px 12px;
        font-size: 13px;
        transform: translateY(18px);
        opacity: 0;
        transition: transform 220ms ease, opacity 220ms ease;
        pointer-events: none;
      }

      .toast.show {
        opacity: 1;
        transform: translateY(0);
      }

      .empty {
        padding: 20px;
        color: var(--ink-soft);
      }

      @media (max-width: 760px) {
        body {
          padding: 14px;
        }

        th,
        td {
          padding: 10px 11px;
          font-size: 12px;
        }
      }
    </style>
  </head>
  <body class="grain">
    <main class="panel">
      <section class="header">
        <div class="eyebrow">Manual Gate / Phase-1</div>
        <h1>Review Queue</h1>
        <div class="meta">
          <div class="badge">All publish paths require approval</div>
          <div class="badge" data-testid="pending-count">Pending: 0</div>
          <div class="badge" data-testid="sla-hours">SLA: 24h</div>
        </div>
      </section>
      <section class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Variant</th>
              <th>Locale</th>
              <th>Policy</th>
              <th>Originality</th>
              <th>Cost</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody data-testid="queue-body"></tbody>
        </table>
      </section>
    </main>
    <aside id="toast" class="toast" role="status" aria-live="polite"></aside>

    <script>
      const queueBody = document.querySelector('[data-testid="queue-body"]');
      const pendingCount = document.querySelector('[data-testid="pending-count"]');
      const slaHours = document.querySelector('[data-testid="sla-hours"]');
      const toast = document.getElementById('toast');

      function showToast(text) {
        toast.textContent = text;
        toast.classList.add('show');
        window.setTimeout(() => toast.classList.remove('show'), 1400);
      }

      function formatCost(cost) {
        const value = Number(cost.estimated_usd || 0).toFixed(2);
        return '$' + value + ' ' + (cost.currency || 'USD');
      }

      function renderRows(items) {
        queueBody.innerHTML = '';
        pendingCount.textContent = 'Pending: ' + items.length;
        if (!items.length) {
          const row = document.createElement('tr');
          row.innerHTML = '<td class="empty" colspan="7">Queue is clear. No pending approvals.</td>';
          queueBody.appendChild(row);
          return;
        }

        items.forEach((item) => {
          const row = document.createElement('tr');
          row.innerHTML = [
            '<td><div class="stack"><strong>' + item.variant_id + '</strong><span class="muted">' + item.review_item_id + '</span></div></td>',
            '<td>' + item.locale + '</td>',
            '<td><div class="stack"><span>' + item.policy.result_code + '</span><span class="muted">' + item.policy.policy_code + '</span></div></td>',
            '<td><div class="stack"><span>score: ' + Number(item.originality.similarity_score).toFixed(2) + '</span><span class="muted">threshold: ' + Number(item.originality.threshold).toFixed(2) + '</span></div></td>',
            '<td>' + formatCost(item.cost) + '</td>',
            '<td>' + item.status + '</td>',
            '<td class="actions"></td>'
          ].join('');

          const actionsCell = row.querySelector('.actions');

          const rejectReasonSelect = document.createElement('select');
          rejectReasonSelect.dataset.testid = 'reject-reason';

          const rejectPolicyOption = document.createElement('option');
          rejectPolicyOption.value = 'REJECTED_POLICY';
          rejectPolicyOption.textContent = 'reason: policy';

          const rejectOriginalityOption = document.createElement('option');
          rejectOriginalityOption.value = 'REJECTED_ORIGINALITY';
          rejectOriginalityOption.textContent = 'reason: originality';

          rejectReasonSelect.appendChild(rejectPolicyOption);
          rejectReasonSelect.appendChild(rejectOriginalityOption);

          const approveButton = document.createElement('button');
          approveButton.dataset.testid = 'approve';
          approveButton.dataset.kind = 'approve';
          approveButton.textContent = 'Approve';
          approveButton.addEventListener('click', () => {
            submitDecision(item.variant_id, 'approved', 'APPROVED_MANUAL_REVIEW');
          });

          const rejectButton = document.createElement('button');
          rejectButton.dataset.testid = 'reject';
          rejectButton.dataset.kind = 'reject';
          rejectButton.textContent = 'Reject';
          rejectButton.addEventListener('click', () => {
            submitDecision(item.variant_id, 'rejected', rejectReasonSelect.value);
          });

          actionsCell.appendChild(rejectReasonSelect);
          actionsCell.appendChild(approveButton);
          actionsCell.appendChild(rejectButton);
          queueBody.appendChild(row);
        });
      }

      async function fetchQueue() {
        const response = await fetch('/review/queue');
        const payload = await response.json();
        const hours = Number(payload.sla_seconds || 0) / 3600;
        slaHours.textContent = 'SLA: ' + hours + 'h';
        renderRows(payload.items || []);
      }

      async function submitDecision(variantId, decision, decisionCode) {
        const response = await fetch('/review/decision', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            variant_id: variantId,
            decision: decision,
            decision_code: decisionCode,
            reviewer_id: 'review-ui',
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          showToast(payload.error_code || 'Decision failed');
          return;
        }
        showToast(payload.message || 'Decision saved');
        await fetchQueue();
      }

      fetchQueue();
    </script>
  </body>
</html>
"""


class ReviewApiApp:
    def __init__(self, review_service: ReviewQueueService) -> None:
        self._review_service = review_service

    def __call__(self, environ: Dict[str, Any], start_response: Any) -> Any:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", "/"))

        try:
            if method == "GET" and path == "/review":
                return self._html_response(start_response, REVIEW_PAGE_HTML)

            if method == "GET" and path == "/review/queue":
                payload = self._review_service.list_pending_queue()
                return self._json_response(start_response, 200, payload)

            if method == "GET" and path == "/review/decisions":
                payload = {
                    "status": "ok",
                    "result_code": "PASS",
                    "items": self._review_service.list_decisions(),
                }
                return self._json_response(start_response, 200, payload)

            if method == "POST" and path == "/review/decision":
                body = self._read_json_body(environ)
                result = self._review_service.record_decision(
                    variant_id=str(body.get("variant_id", "")),
                    decision=str(body.get("decision", "")),
                    reviewer_id=str(body.get("reviewer_id", "")),
                    reviewed_at=body.get("reviewed_at"),
                    decision_code=body.get("decision_code"),
                )
                return self._json_response(start_response, 200, result)

            if method == "POST" and path == "/publish":
                body = self._read_json_body(environ)
                check = self._review_service.check_publish_eligibility(
                    variant_id=str(body.get("variant_id", "")),
                    now_timestamp=body.get("checked_at"),
                )
                response_payload = {
                    "status": "accepted_for_publish",
                    "result_code": check["result_code"],
                    "variant_id": check["variant_id"],
                }
                return self._json_response(start_response, 202, response_payload)

            return self._json_response(
                start_response,
                404,
                {
                    "status": "not_found",
                    "result_code": "API_ROUTE_NOT_FOUND",
                },
            )
        except ReviewError as error:
            payload = {
                "status": "blocked",
                "result_code": error.code,
                "error_code": error.code,
                "message": str(error),
            }
            return self._json_response(start_response, error.http_status, payload)

    def _read_json_body(self, environ: Dict[str, Any]) -> Dict[str, Any]:
        content_length = str(environ.get("CONTENT_LENGTH", "0")).strip()
        try:
            length = int(content_length)
        except ValueError:
            length = 0

        body_bytes = environ["wsgi.input"].read(max(0, length))
        if not body_bytes:
            return {}
        return json.loads(body_bytes.decode("utf-8"))

    def _html_response(self, start_response: Any, html_body: str) -> Any:
        body = html_body.encode("utf-8")
        status_line = "200 OK"
        headers = [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ]
        start_response(status_line, headers)
        return [body]

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


def _http_reason_phrase(status_code: int) -> str:
    reasons = {
        200: "OK",
        202: "Accepted",
        400: "Bad Request",
        404: "Not Found",
        409: "Conflict",
    }
    return reasons.get(status_code, "OK")


def serve_review_api(
    app: ReviewApiApp,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> WSGIServer:
    return make_server(host, port, app)


def invoke_json_request(
    app: ReviewApiApp,
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Tuple[int, Dict[str, Any]]:
    request_payload = payload or {}
    raw_bytes = json.dumps(request_payload).encode("utf-8")

    captured_status = {"value": "200 OK"}

    def _start_response(status: str, _headers: Any) -> None:
        captured_status["value"] = status

    environ = {
        "REQUEST_METHOD": method.upper(),
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(raw_bytes) if method.upper() == "POST" else 0),
        "wsgi.input": io.BytesIO(raw_bytes if method.upper() == "POST" else b""),
    }
    body = b"".join(app(environ, _start_response))
    status_code = int(captured_status["value"].split(" ")[0])
    if not body:
        return status_code, {}
    return status_code, json.loads(body.decode("utf-8"))


def build_demo_review_app(review_service: ReviewQueueService) -> ReviewApiApp:
    return ReviewApiApp(review_service=review_service)


def is_human_gate_response(status_code: int, payload: Dict[str, Any]) -> bool:
    return status_code == 409 and payload.get("error_code") == PUBLISH_BLOCK_CODE
