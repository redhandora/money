from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


ISO_DATE = "%Y-%m-%d"

WORKFLOW_STAGE_ORDER = [
    "trend_ingestion",
    "script_generation",
    "scene_generation",
    "localization",
    "review",
    "publish",
]

WORKFLOW_STAGE_STATES = {
    "trend_ingestion": "trend_ingested",
    "script_generation": "script_generated",
    "scene_generation": "scenes_generated",
    "localization": "localized",
    "review": "approved",
    "publish": "published",
}

TERMINAL_STATE_HALTED_COST_CAP = "halted_cost_cap"
TERMINAL_STATE_FAILED_RETRY_EXHAUSTED = "failed_retry_exhausted"
TERMINAL_STATE_BLOCKED_POLICY = "blocked_policy"
TERMINAL_STATE_BLOCKED_REVIEW_GATE = "blocked_review_gate"
TERMINAL_STATE_FAILED_TERMINAL = "failed_terminal"

DEFAULT_RETRY_CEILING = 3
DEFAULT_RETRY_BACKOFF_BASE_SECONDS = 2

DEFAULT_SEEDANCE_PROFILE_FALLBACK_ORDER = [
    "seedance-quality-v1",
    "seedance-balanced-v1",
    "seedance-speed-v1",
]


class OrchestrationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _round_usd(value: Any) -> float:
    return round(float(value), 4)


def _normalize_run_date(raw_value: str) -> str:
    value = str(raw_value or "").strip()
    try:
        datetime.strptime(value, ISO_DATE)
    except ValueError:
        raise OrchestrationError(
            code="WORKFLOW_RUN_DATE_INVALID",
            message="run_date must use YYYY-MM-DD",
        )
    return value


class WorkflowOrchestrationService:
    def __init__(
        self,
        *,
        per_video_budget_cap_usd: float,
        daily_spend_cap_usd: float,
        max_retries_per_stage: int = DEFAULT_RETRY_CEILING,
        retry_backoff_base_seconds: int = DEFAULT_RETRY_BACKOFF_BASE_SECONDS,
        seedance_profile_fallback_order: Optional[List[str]] = None,
    ) -> None:
        if _round_usd(per_video_budget_cap_usd) <= 0:
            raise OrchestrationError(
                code="WORKFLOW_PER_VIDEO_BUDGET_INVALID",
                message="per_video_budget_cap_usd must be greater than zero",
            )
        if _round_usd(daily_spend_cap_usd) <= 0:
            raise OrchestrationError(
                code="WORKFLOW_DAILY_SPEND_CAP_INVALID",
                message="daily_spend_cap_usd must be greater than zero",
            )
        if int(max_retries_per_stage) < 0:
            raise OrchestrationError(
                code="WORKFLOW_RETRY_CEILING_INVALID",
                message="max_retries_per_stage must be zero or greater",
            )
        if int(retry_backoff_base_seconds) <= 0:
            raise OrchestrationError(
                code="WORKFLOW_BACKOFF_BASE_INVALID",
                message="retry_backoff_base_seconds must be greater than zero",
            )

        fallback_order = list(
            seedance_profile_fallback_order or DEFAULT_SEEDANCE_PROFILE_FALLBACK_ORDER
        )
        normalized_order = [str(profile).strip() for profile in fallback_order if str(profile).strip()]
        if not normalized_order:
            raise OrchestrationError(
                code="WORKFLOW_SEEDANCE_PROFILE_ORDER_INVALID",
                message="seedance profile fallback order requires at least one profile",
            )

        self._per_video_budget_cap_usd = _round_usd(per_video_budget_cap_usd)
        self._daily_spend_cap_usd = _round_usd(daily_spend_cap_usd)
        self._max_retries_per_stage = int(max_retries_per_stage)
        self._retry_backoff_base_seconds = int(retry_backoff_base_seconds)
        self._seedance_profile_fallback_order = normalized_order
        self._daily_spend_by_date = {}  # type: Dict[str, float]

    def set_daily_spend(self, *, run_date: str, spend_usd: float) -> None:
        normalized_date = _normalize_run_date(run_date)
        self._daily_spend_by_date[normalized_date] = _round_usd(spend_usd)

    def get_daily_spend(self, *, run_date: str) -> float:
        normalized_date = _normalize_run_date(run_date)
        return _round_usd(self._daily_spend_by_date.get(normalized_date, 0.0))

    def run_workflow(
        self,
        *,
        workflow_id: str,
        run_date: str,
        stage_handlers: Dict[str, Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized_workflow_id = str(workflow_id or "").strip()
        if not normalized_workflow_id:
            raise OrchestrationError(
                code="WORKFLOW_ID_REQUIRED",
                message="workflow_id is required",
            )

        normalized_date = _normalize_run_date(run_date)
        self._assert_required_handlers(stage_handlers)

        workflow_context = dict(context or {})
        workflow_context["workflow_id"] = normalized_workflow_id
        workflow_context["run_date"] = normalized_date

        state_trace = ["created"]
        attempt_trace = []  # type: List[Dict[str, Any]]
        retry_trace = []  # type: List[Dict[str, Any]]
        stage_results = {}  # type: Dict[str, Dict[str, Any]]
        seedance_profile_trace = []  # type: List[Dict[str, Any]]

        current_state = "created"
        workflow_cost_usd = 0.0
        daily_spend_before_usd = self.get_daily_spend(run_date=normalized_date)

        for stage in WORKFLOW_STAGE_ORDER:
            if self.get_daily_spend(run_date=normalized_date) >= self._daily_spend_cap_usd:
                budget_halt_event = {
                    "stage": stage,
                    "reason_code": "DAILY_SPEND_CAP_REACHED",
                    "workflow_cost_usd": _round_usd(workflow_cost_usd),
                    "daily_spend_usd": self.get_daily_spend(run_date=normalized_date),
                }
                return self._terminal_response(
                    workflow_id=normalized_workflow_id,
                    state=TERMINAL_STATE_HALTED_COST_CAP,
                    status="halted",
                    result_code="HALTED_COST_CAP",
                    reason_code="DAILY_SPEND_CAP_REACHED",
                    current_state=current_state,
                    state_trace=state_trace,
                    stage_results=stage_results,
                    attempt_trace=attempt_trace,
                    retry_trace=retry_trace,
                    seedance_profile_trace=seedance_profile_trace,
                    run_date=normalized_date,
                    daily_spend_before_usd=daily_spend_before_usd,
                    workflow_cost_usd=workflow_cost_usd,
                    budget_halt_event=budget_halt_event,
                )

            retry_count = 0
            stage_cost_usd = 0.0

            while True:
                attempt_number = retry_count + 1
                seedance_profile = None
                if stage == "scene_generation":
                    seedance_profile = self._seedance_profile_for_retry(retry_count)
                    seedance_profile_trace.append(
                        {
                            "stage": stage,
                            "attempt_number": attempt_number,
                            "seedance_profile": seedance_profile,
                        }
                    )

                attempt_metadata = {
                    "workflow_id": normalized_workflow_id,
                    "stage": stage,
                    "attempt_number": attempt_number,
                    "retry_count": retry_count,
                    "max_retries": self._max_retries_per_stage,
                    "run_date": normalized_date,
                    "seedance_profile": seedance_profile,
                }

                call_context = dict(workflow_context)
                call_context["state"] = current_state
                call_context["workflow_cost_usd"] = _round_usd(workflow_cost_usd)
                call_context["daily_spend_usd"] = self.get_daily_spend(run_date=normalized_date)
                call_context["stage_results"] = dict(stage_results)

                raw_result = stage_handlers[stage](call_context, attempt_metadata)
                normalized_result = self._normalize_stage_result(
                    stage=stage,
                    raw_result=raw_result,
                    seedance_profile=seedance_profile,
                )

                stage_cost_usd = _round_usd(stage_cost_usd + normalized_result["cost_usd"])
                workflow_cost_usd = _round_usd(workflow_cost_usd + normalized_result["cost_usd"])

                daily_spend_after_attempt = _round_usd(
                    self.get_daily_spend(run_date=normalized_date) + normalized_result["cost_usd"]
                )
                self._daily_spend_by_date[normalized_date] = daily_spend_after_attempt

                attempt_event = {
                    "stage": stage,
                    "attempt_number": attempt_number,
                    "status": normalized_result["status"],
                    "result_code": normalized_result["result_code"],
                    "reason_code": normalized_result["reason_code"],
                    "cost_usd": normalized_result["cost_usd"],
                    "workflow_cost_usd": _round_usd(workflow_cost_usd),
                    "daily_spend_usd": daily_spend_after_attempt,
                    "seedance_profile": seedance_profile,
                }
                attempt_trace.append(attempt_event)

                budget_halt_event = self._build_budget_halt_event(
                    stage=stage,
                    attempt_number=attempt_number,
                    workflow_cost_usd=workflow_cost_usd,
                    daily_spend_usd=daily_spend_after_attempt,
                )
                if budget_halt_event is not None:
                    stage_results[stage] = {
                        "status": "halted_cost_cap",
                        "result_code": "HALTED_COST_CAP",
                        "reason_code": budget_halt_event["reason_code"],
                        "attempt_count": attempt_number,
                        "stage_cost_usd": stage_cost_usd,
                    }
                    return self._terminal_response(
                        workflow_id=normalized_workflow_id,
                        state=TERMINAL_STATE_HALTED_COST_CAP,
                        status="halted",
                        result_code="HALTED_COST_CAP",
                        reason_code=budget_halt_event["reason_code"],
                        current_state=current_state,
                        state_trace=state_trace,
                        stage_results=stage_results,
                        attempt_trace=attempt_trace,
                        retry_trace=retry_trace,
                        seedance_profile_trace=seedance_profile_trace,
                        run_date=normalized_date,
                        daily_spend_before_usd=daily_spend_before_usd,
                        workflow_cost_usd=workflow_cost_usd,
                        budget_halt_event=budget_halt_event,
                    )

                if normalized_result["status"] == "success":
                    stage_results[stage] = {
                        "status": "success",
                        "result_code": normalized_result["result_code"],
                        "reason_code": normalized_result["reason_code"],
                        "attempt_count": attempt_number,
                        "stage_cost_usd": stage_cost_usd,
                        "seedance_profile": seedance_profile,
                    }
                    current_state = WORKFLOW_STAGE_STATES[stage]
                    state_trace.append(current_state)
                    workflow_context[stage] = dict(normalized_result)
                    break

                if normalized_result["status"] == "blocked_policy":
                    stage_results[stage] = {
                        "status": "blocked_policy",
                        "result_code": normalized_result["result_code"],
                        "reason_code": normalized_result["reason_code"],
                        "attempt_count": attempt_number,
                        "stage_cost_usd": stage_cost_usd,
                    }
                    return self._terminal_response(
                        workflow_id=normalized_workflow_id,
                        state=TERMINAL_STATE_BLOCKED_POLICY,
                        status="blocked",
                        result_code=normalized_result["result_code"],
                        reason_code=normalized_result["reason_code"],
                        current_state=current_state,
                        state_trace=state_trace,
                        stage_results=stage_results,
                        attempt_trace=attempt_trace,
                        retry_trace=retry_trace,
                        seedance_profile_trace=seedance_profile_trace,
                        run_date=normalized_date,
                        daily_spend_before_usd=daily_spend_before_usd,
                        workflow_cost_usd=workflow_cost_usd,
                        budget_halt_event=None,
                    )

                if normalized_result["status"] == "blocked_review":
                    stage_results[stage] = {
                        "status": "blocked_review",
                        "result_code": normalized_result["result_code"],
                        "reason_code": normalized_result["reason_code"],
                        "attempt_count": attempt_number,
                        "stage_cost_usd": stage_cost_usd,
                    }
                    return self._terminal_response(
                        workflow_id=normalized_workflow_id,
                        state=TERMINAL_STATE_BLOCKED_REVIEW_GATE,
                        status="blocked",
                        result_code=normalized_result["result_code"],
                        reason_code=normalized_result["reason_code"],
                        current_state=current_state,
                        state_trace=state_trace,
                        stage_results=stage_results,
                        attempt_trace=attempt_trace,
                        retry_trace=retry_trace,
                        seedance_profile_trace=seedance_profile_trace,
                        run_date=normalized_date,
                        daily_spend_before_usd=daily_spend_before_usd,
                        workflow_cost_usd=workflow_cost_usd,
                        budget_halt_event=None,
                    )

                if normalized_result["status"] == "terminal_failure":
                    stage_results[stage] = {
                        "status": "failed_terminal",
                        "result_code": normalized_result["result_code"],
                        "reason_code": normalized_result["reason_code"],
                        "attempt_count": attempt_number,
                        "stage_cost_usd": stage_cost_usd,
                    }
                    return self._terminal_response(
                        workflow_id=normalized_workflow_id,
                        state=TERMINAL_STATE_FAILED_TERMINAL,
                        status="failed",
                        result_code=normalized_result["result_code"],
                        reason_code=normalized_result["reason_code"],
                        current_state=current_state,
                        state_trace=state_trace,
                        stage_results=stage_results,
                        attempt_trace=attempt_trace,
                        retry_trace=retry_trace,
                        seedance_profile_trace=seedance_profile_trace,
                        run_date=normalized_date,
                        daily_spend_before_usd=daily_spend_before_usd,
                        workflow_cost_usd=workflow_cost_usd,
                        budget_halt_event=None,
                    )

                if retry_count >= self._max_retries_per_stage:
                    stage_results[stage] = {
                        "status": "failed_retry_exhausted",
                        "result_code": "FAILED_RETRY_EXHAUSTED",
                        "reason_code": "RETRY_CEILING_REACHED",
                        "attempt_count": attempt_number,
                        "stage_cost_usd": stage_cost_usd,
                    }
                    return self._terminal_response(
                        workflow_id=normalized_workflow_id,
                        state=TERMINAL_STATE_FAILED_RETRY_EXHAUSTED,
                        status="failed",
                        result_code="FAILED_RETRY_EXHAUSTED",
                        reason_code="RETRY_CEILING_REACHED",
                        current_state=current_state,
                        state_trace=state_trace,
                        stage_results=stage_results,
                        attempt_trace=attempt_trace,
                        retry_trace=retry_trace,
                        seedance_profile_trace=seedance_profile_trace,
                        run_date=normalized_date,
                        daily_spend_before_usd=daily_spend_before_usd,
                        workflow_cost_usd=workflow_cost_usd,
                        budget_halt_event=None,
                    )

                retry_count += 1
                retry_event = {
                    "stage": stage,
                    "retry_index": retry_count,
                    "reason_code": normalized_result["reason_code"],
                    "result_code": normalized_result["result_code"],
                    "backoff_seconds": self._retry_backoff_base_seconds * (2 ** (retry_count - 1)),
                    "seedance_profile": seedance_profile,
                }
                retry_trace.append(retry_event)

        return {
            "workflow_id": normalized_workflow_id,
            "status": "completed",
            "state": "published",
            "result_code": "PASS",
            "reason_code": "PASS",
            "stage_order": list(WORKFLOW_STAGE_ORDER),
            "state_trace": state_trace,
            "stage_results": stage_results,
            "attempt_trace": attempt_trace,
            "retry_trace": retry_trace,
            "seedance_profile_trace": seedance_profile_trace,
            "cost_tracking": {
                "run_date": normalized_date,
                "per_video_budget_cap_usd": self._per_video_budget_cap_usd,
                "daily_spend_cap_usd": self._daily_spend_cap_usd,
                "workflow_cost_usd": _round_usd(workflow_cost_usd),
                "daily_spend_before_usd": daily_spend_before_usd,
                "daily_spend_after_usd": self.get_daily_spend(run_date=normalized_date),
                "budget_halt_event": None,
            },
        }

    def _terminal_response(
        self,
        *,
        workflow_id: str,
        state: str,
        status: str,
        result_code: str,
        reason_code: str,
        current_state: str,
        state_trace: List[str],
        stage_results: Dict[str, Dict[str, Any]],
        attempt_trace: List[Dict[str, Any]],
        retry_trace: List[Dict[str, Any]],
        seedance_profile_trace: List[Dict[str, Any]],
        run_date: str,
        daily_spend_before_usd: float,
        workflow_cost_usd: float,
        budget_halt_event: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        state_trace_with_terminal = list(state_trace)
        if state_trace_with_terminal[-1] != state:
            state_trace_with_terminal.append(state)
        return {
            "workflow_id": workflow_id,
            "status": status,
            "state": state,
            "result_code": result_code,
            "reason_code": reason_code,
            "blocked_from_state": current_state,
            "stage_order": list(WORKFLOW_STAGE_ORDER),
            "state_trace": state_trace_with_terminal,
            "stage_results": stage_results,
            "attempt_trace": attempt_trace,
            "retry_trace": retry_trace,
            "seedance_profile_trace": seedance_profile_trace,
            "cost_tracking": {
                "run_date": run_date,
                "per_video_budget_cap_usd": self._per_video_budget_cap_usd,
                "daily_spend_cap_usd": self._daily_spend_cap_usd,
                "workflow_cost_usd": _round_usd(workflow_cost_usd),
                "daily_spend_before_usd": daily_spend_before_usd,
                "daily_spend_after_usd": self.get_daily_spend(run_date=run_date),
                "budget_halt_event": budget_halt_event,
            },
        }

    def _assert_required_handlers(
        self,
        stage_handlers: Dict[str, Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]],
    ) -> None:
        missing = []  # type: List[str]
        for stage in WORKFLOW_STAGE_ORDER:
            if stage not in stage_handlers:
                missing.append(stage)
        if missing:
            raise OrchestrationError(
                code="WORKFLOW_STAGE_HANDLER_MISSING",
                message="missing stage handlers: %s" % ", ".join(missing),
            )

    def _build_budget_halt_event(
        self,
        *,
        stage: str,
        attempt_number: int,
        workflow_cost_usd: float,
        daily_spend_usd: float,
    ) -> Optional[Dict[str, Any]]:
        if workflow_cost_usd > self._per_video_budget_cap_usd:
            return {
                "stage": stage,
                "attempt_number": attempt_number,
                "reason_code": "PER_VIDEO_BUDGET_EXCEEDED",
                "workflow_cost_usd": _round_usd(workflow_cost_usd),
                "per_video_budget_cap_usd": self._per_video_budget_cap_usd,
                "daily_spend_usd": _round_usd(daily_spend_usd),
                "daily_spend_cap_usd": self._daily_spend_cap_usd,
            }
        if daily_spend_usd > self._daily_spend_cap_usd:
            return {
                "stage": stage,
                "attempt_number": attempt_number,
                "reason_code": "DAILY_SPEND_CAP_EXCEEDED",
                "workflow_cost_usd": _round_usd(workflow_cost_usd),
                "per_video_budget_cap_usd": self._per_video_budget_cap_usd,
                "daily_spend_usd": _round_usd(daily_spend_usd),
                "daily_spend_cap_usd": self._daily_spend_cap_usd,
            }
        return None

    def _seedance_profile_for_retry(self, retry_count: int) -> str:
        bounded_index = retry_count
        if bounded_index >= len(self._seedance_profile_fallback_order):
            bounded_index = len(self._seedance_profile_fallback_order) - 1
        return self._seedance_profile_fallback_order[bounded_index]

    def _normalize_stage_result(
        self,
        *,
        stage: str,
        raw_result: Dict[str, Any],
        seedance_profile: Optional[str],
    ) -> Dict[str, Any]:
        if not isinstance(raw_result, dict):
            raise OrchestrationError(
                code="WORKFLOW_STAGE_RESULT_INVALID",
                message="stage %s must return a dict result" % stage,
            )

        status_aliases = {
            "ok": "success",
            "pass": "success",
            "generated": "success",
            "ready_for_review": "success",
            "approved": "success",
            "published": "success",
            "retryable": "retryable_failure",
            "retryable_error": "retryable_failure",
            "failed_retryable": "retryable_failure",
            "failed_retryable_stage": "retryable_failure",
            "failed_terminal": "terminal_failure",
            "error": "terminal_failure",
            "blocked_policy": "blocked_policy",
            "blocked_review": "blocked_review",
            "pending_review": "blocked_review",
            "human_approval_required": "blocked_review",
        }

        raw_status = str(raw_result.get("status", "success") or "success").strip().lower()
        status = status_aliases.get(raw_status, raw_status)
        if status not in [
            "success",
            "retryable_failure",
            "terminal_failure",
            "blocked_policy",
            "blocked_review",
        ]:
            status = "terminal_failure"

        result_code = str(raw_result.get("result_code", "PASS") or "PASS").strip()
        reason_code = str(raw_result.get("reason_code", result_code) or result_code).strip()

        cost_usd = _round_usd(raw_result.get("cost_usd", 0.0))
        if cost_usd < 0:
            raise OrchestrationError(
                code="WORKFLOW_STAGE_COST_INVALID",
                message="stage %s cost_usd cannot be negative" % stage,
            )

        if stage == "localization":
            policy_result_code = str(raw_result.get("policy_result_code", "PASS") or "PASS").strip()
            if policy_result_code != "PASS":
                status = "blocked_policy"
                result_code = "BLOCKED_POLICY_GATE"
                reason_code = str(
                    raw_result.get("policy_reason_code", policy_result_code) or policy_result_code
                ).strip()

        if stage == "review":
            review_status = str(raw_result.get("review_status", "approved") or "approved").strip().lower()
            if review_status != "approved":
                status = "blocked_review"
                result_code = "HUMAN_APPROVAL_REQUIRED"
                reason_code = str(raw_result.get("reason_code", "HUMAN_APPROVAL_REQUIRED")).strip()

        return {
            "status": status,
            "result_code": result_code,
            "reason_code": reason_code,
            "cost_usd": cost_usd,
            "seedance_profile": seedance_profile,
            "raw": dict(raw_result),
        }


class DeterministicStageHandlerFactory:
    def __init__(
        self,
        *,
        scripted_outcomes: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        default_stage_costs: Optional[Dict[str, float]] = None,
    ) -> None:
        self._scripted_outcomes = {}  # type: Dict[str, List[Dict[str, Any]]]
        for stage in WORKFLOW_STAGE_ORDER:
            self._scripted_outcomes[stage] = [
                dict(entry) for entry in (scripted_outcomes or {}).get(stage, [])
            ]

        defaults = {
            "trend_ingestion": 0.25,
            "script_generation": 0.8,
            "scene_generation": 1.6,
            "localization": 0.55,
            "review": 0.0,
            "publish": 0.2,
        }
        if default_stage_costs:
            for stage, value in default_stage_costs.items():
                defaults[stage] = _round_usd(value)

        self._default_stage_costs = defaults
        self._calls_by_stage = {}  # type: Dict[str, int]

    def build_handlers(self) -> Dict[str, Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]]:
        handlers = {}  # type: Dict[str, Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]]

        for stage in WORKFLOW_STAGE_ORDER:
            handlers[stage] = self._build_handler(stage)
        return handlers

    def call_count(self, stage: str) -> int:
        return int(self._calls_by_stage.get(stage, 0))

    def _build_handler(self, stage: str) -> Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]:
        def _handler(_context: Dict[str, Any], attempt_metadata: Dict[str, Any]) -> Dict[str, Any]:
            index = self._calls_by_stage.get(stage, 0)
            self._calls_by_stage[stage] = index + 1

            scripted = self._scripted_outcomes.get(stage, [])
            if index < len(scripted):
                response = dict(scripted[index])
            else:
                response = {
                    "status": "success",
                    "result_code": "PASS",
                    "reason_code": "PASS",
                }

            if "cost_usd" not in response:
                response["cost_usd"] = self._default_stage_costs.get(stage, 0.0)

            if stage == "scene_generation":
                response.setdefault(
                    "seedance_profile_used",
                    attempt_metadata.get("seedance_profile"),
                )
            if stage == "localization":
                response.setdefault("policy_result_code", "PASS")
            if stage == "review":
                response.setdefault("review_status", "approved")

            return response

        return _handler
