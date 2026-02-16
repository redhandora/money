from money.orchestration import (
    DeterministicStageHandlerFactory,
    WorkflowOrchestrationService,
)


def _orchestrator(
    *,
    per_video_budget_cap_usd: float = 20.0,
    daily_spend_cap_usd: float = 100.0,
    max_retries_per_stage: int = 3,
    retry_backoff_base_seconds: int = 2,
) -> WorkflowOrchestrationService:
    return WorkflowOrchestrationService(
        per_video_budget_cap_usd=per_video_budget_cap_usd,
        daily_spend_cap_usd=daily_spend_cap_usd,
        max_retries_per_stage=max_retries_per_stage,
        retry_backoff_base_seconds=retry_backoff_base_seconds,
    )


def test_state_machine_enforces_required_sequence_to_publish() -> None:
    factory = DeterministicStageHandlerFactory()
    service = _orchestrator()

    result = service.run_workflow(
        workflow_id="workflow-sequence-001",
        run_date="2026-02-16",
        stage_handlers=factory.build_handlers(),
    )

    assert result["status"] == "completed"
    assert result["state"] == "published"
    assert result["result_code"] == "PASS"
    assert result["state_trace"] == [
        "created",
        "trend_ingested",
        "script_generated",
        "scenes_generated",
        "localized",
        "approved",
        "published",
    ]


def test_policy_gate_blocks_and_prevents_review_or_publish_bypass() -> None:
    factory = DeterministicStageHandlerFactory(
        scripted_outcomes={
            "localization": [
                {
                    "status": "success",
                    "result_code": "PASS",
                    "policy_result_code": "BLOCKED_POLICY",
                    "policy_reason_code": "POLICY_BLOCKED_CATEGORY",
                    "cost_usd": 0.3,
                }
            ]
        }
    )
    service = _orchestrator()

    result = service.run_workflow(
        workflow_id="workflow-policy-gate-001",
        run_date="2026-02-16",
        stage_handlers=factory.build_handlers(),
    )

    assert result["state"] == "blocked_policy"
    assert result["result_code"] == "BLOCKED_POLICY_GATE"
    assert result["reason_code"] == "POLICY_BLOCKED_CATEGORY"
    assert factory.call_count("review") == 0
    assert factory.call_count("publish") == 0


def test_review_gate_blocks_publish_when_not_approved() -> None:
    factory = DeterministicStageHandlerFactory(
        scripted_outcomes={
            "review": [
                {
                    "status": "success",
                    "result_code": "PASS",
                    "review_status": "pending",
                    "reason_code": "HUMAN_APPROVAL_REQUIRED",
                    "cost_usd": 0.0,
                }
            ]
        }
    )
    service = _orchestrator()

    result = service.run_workflow(
        workflow_id="workflow-review-gate-001",
        run_date="2026-02-16",
        stage_handlers=factory.build_handlers(),
    )

    assert result["state"] == "blocked_review_gate"
    assert result["result_code"] == "HUMAN_APPROVAL_REQUIRED"
    assert factory.call_count("publish") == 0


def test_budget_exceed_event_sets_halted_cost_cap_state() -> None:
    factory = DeterministicStageHandlerFactory(
        default_stage_costs={
            "trend_ingestion": 0.7,
            "script_generation": 0.9,
            "scene_generation": 1.1,
            "localization": 0.4,
            "review": 0.0,
            "publish": 0.2,
        }
    )
    service = _orchestrator(per_video_budget_cap_usd=2.0, daily_spend_cap_usd=50.0)

    result = service.run_workflow(
        workflow_id="workflow-cost-cap-001",
        run_date="2026-02-16",
        stage_handlers=factory.build_handlers(),
    )

    budget_halt_event = result["cost_tracking"]["budget_halt_event"]
    assert result["state"] == "halted_cost_cap"
    assert result["result_code"] == "HALTED_COST_CAP"
    assert result["reason_code"] == "PER_VIDEO_BUDGET_EXCEEDED"
    assert budget_halt_event["reason_code"] == "PER_VIDEO_BUDGET_EXCEEDED"
    assert factory.call_count("localization") == 0
    assert factory.call_count("publish") == 0


def test_daily_spend_cap_is_enforced() -> None:
    factory = DeterministicStageHandlerFactory(
        default_stage_costs={
            "trend_ingestion": 0.3,
            "script_generation": 0.2,
            "scene_generation": 0.2,
            "localization": 0.2,
            "review": 0.0,
            "publish": 0.2,
        }
    )
    service = _orchestrator(per_video_budget_cap_usd=20.0, daily_spend_cap_usd=5.0)
    service.set_daily_spend(run_date="2026-02-16", spend_usd=4.8)

    result = service.run_workflow(
        workflow_id="workflow-daily-cap-001",
        run_date="2026-02-16",
        stage_handlers=factory.build_handlers(),
    )

    assert result["state"] == "halted_cost_cap"
    assert result["reason_code"] == "DAILY_SPEND_CAP_EXCEEDED"
    assert factory.call_count("trend_ingestion") == 1
    assert factory.call_count("script_generation") == 0


def test_retry_policy_is_bounded_with_reason_codes_and_backoff_trace() -> None:
    factory = DeterministicStageHandlerFactory(
        scripted_outcomes={
            "scene_generation": [
                {
                    "status": "retryable_failure",
                    "result_code": "SEEDANCE_TIMEOUT",
                    "reason_code": "SEEDANCE_TIMEOUT",
                    "cost_usd": 0.2,
                },
                {
                    "status": "retryable_failure",
                    "result_code": "SEEDANCE_TIMEOUT",
                    "reason_code": "SEEDANCE_TIMEOUT",
                    "cost_usd": 0.2,
                },
                {
                    "status": "retryable_failure",
                    "result_code": "SEEDANCE_TIMEOUT",
                    "reason_code": "SEEDANCE_TIMEOUT",
                    "cost_usd": 0.2,
                },
                {
                    "status": "retryable_failure",
                    "result_code": "SEEDANCE_TIMEOUT",
                    "reason_code": "SEEDANCE_TIMEOUT",
                    "cost_usd": 0.2,
                },
            ]
        }
    )
    service = _orchestrator(max_retries_per_stage=3, retry_backoff_base_seconds=2)

    result = service.run_workflow(
        workflow_id="workflow-retry-ceiling-001",
        run_date="2026-02-16",
        stage_handlers=factory.build_handlers(),
    )

    assert result["state"] == "failed_retry_exhausted"
    assert result["result_code"] == "FAILED_RETRY_EXHAUSTED"
    assert result["reason_code"] == "RETRY_CEILING_REACHED"

    retry_trace = result["retry_trace"]
    assert len(retry_trace) == 3
    assert [entry["backoff_seconds"] for entry in retry_trace] == [2, 4, 8]
    assert [entry["reason_code"] for entry in retry_trace] == [
        "SEEDANCE_TIMEOUT",
        "SEEDANCE_TIMEOUT",
        "SEEDANCE_TIMEOUT",
    ]


def test_seedance_profile_fallback_uses_deterministic_order_and_stops_on_success() -> None:
    factory = DeterministicStageHandlerFactory(
        scripted_outcomes={
            "scene_generation": [
                {
                    "status": "retryable_failure",
                    "result_code": "SEEDANCE_TIMEOUT",
                    "reason_code": "SEEDANCE_TIMEOUT",
                    "cost_usd": 0.2,
                },
                {
                    "status": "success",
                    "result_code": "PASS",
                    "reason_code": "PASS",
                    "cost_usd": 0.2,
                },
            ]
        }
    )
    service = _orchestrator()

    result = service.run_workflow(
        workflow_id="workflow-seedance-fallback-001",
        run_date="2026-02-16",
        stage_handlers=factory.build_handlers(),
    )

    scene_profiles = [
        item["seedance_profile"]
        for item in result["seedance_profile_trace"]
        if item["stage"] == "scene_generation"
    ]
    assert result["state"] == "published"
    assert scene_profiles == [
        "seedance-quality-v1",
        "seedance-balanced-v1",
    ]
    assert factory.call_count("scene_generation") == 2
