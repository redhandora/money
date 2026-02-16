import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from money.orchestration.service import (
    DeterministicStageHandlerFactory,
    WorkflowOrchestrationService,
)


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


def run_cost_breaker_scenario() -> Dict[str, Any]:
    factory = DeterministicStageHandlerFactory(
        default_stage_costs={
            "trend_ingestion": 0.45,
            "script_generation": 0.8,
            "scene_generation": 1.2,
            "localization": 0.5,
            "review": 0.0,
            "publish": 0.2,
        }
    )
    orchestrator = WorkflowOrchestrationService(
        per_video_budget_cap_usd=2.0,
        daily_spend_cap_usd=30.0,
        max_retries_per_stage=3,
    )
    result = orchestrator.run_workflow(
        workflow_id="task7-cost-breaker-001",
        run_date="2026-02-16",
        stage_handlers=factory.build_handlers(),
    )

    return {
        "scenario": "cost_circuit_breaker_halts_workflow",
        "result": {
            "status": result.get("status"),
            "state": result.get("state"),
            "result_code": result.get("result_code"),
            "reason_code": result.get("reason_code"),
            "state_trace": result.get("state_trace", []),
            "budget_halt_event": result.get("cost_tracking", {}).get("budget_halt_event"),
            "workflow_cost_usd": result.get("cost_tracking", {}).get("workflow_cost_usd"),
            "attempt_count": len(result.get("attempt_trace", [])),
        },
        "checks": {
            "state_is_halted_cost_cap": result.get("state") == "halted_cost_cap",
            "cost_halt_reason_is_per_video": result.get("reason_code")
            == "PER_VIDEO_BUDGET_EXCEEDED",
            "publish_not_attempted": factory.call_count("publish") == 0,
            "review_not_attempted": factory.call_count("review") == 0,
        },
        "attempt_trace": result.get("attempt_trace", []),
    }


def run_retry_ceiling_scenario() -> Dict[str, Any]:
    factory = DeterministicStageHandlerFactory(
        scripted_outcomes={
            "scene_generation": [
                {
                    "status": "retryable_failure",
                    "result_code": "SEEDANCE_TIMEOUT",
                    "reason_code": "SEEDANCE_TIMEOUT",
                    "cost_usd": 0.25,
                },
                {
                    "status": "retryable_failure",
                    "result_code": "SEEDANCE_TIMEOUT",
                    "reason_code": "SEEDANCE_TIMEOUT",
                    "cost_usd": 0.25,
                },
                {
                    "status": "retryable_failure",
                    "result_code": "SEEDANCE_TIMEOUT",
                    "reason_code": "SEEDANCE_TIMEOUT",
                    "cost_usd": 0.25,
                },
                {
                    "status": "retryable_failure",
                    "result_code": "SEEDANCE_TIMEOUT",
                    "reason_code": "SEEDANCE_TIMEOUT",
                    "cost_usd": 0.25,
                },
            ]
        },
        default_stage_costs={
            "trend_ingestion": 0.1,
            "script_generation": 0.2,
            "scene_generation": 0.25,
            "localization": 0.1,
            "review": 0.0,
            "publish": 0.1,
        },
    )
    orchestrator = WorkflowOrchestrationService(
        per_video_budget_cap_usd=15.0,
        daily_spend_cap_usd=100.0,
        max_retries_per_stage=3,
        retry_backoff_base_seconds=2,
    )
    result = orchestrator.run_workflow(
        workflow_id="task7-retry-ceiling-001",
        run_date="2026-02-16",
        stage_handlers=factory.build_handlers(),
    )

    retry_trace = result.get("retry_trace", [])
    scene_profiles = [
        item.get("seedance_profile")
        for item in result.get("seedance_profile_trace", [])
        if item.get("stage") == "scene_generation"
    ]
    backoff_values = [entry.get("backoff_seconds") for entry in retry_trace]

    return {
        "scenario": "retry_ceiling_prevents_runaway",
        "result": {
            "status": result.get("status"),
            "state": result.get("state"),
            "result_code": result.get("result_code"),
            "reason_code": result.get("reason_code"),
            "state_trace": result.get("state_trace", []),
            "retry_count": len(retry_trace),
            "scene_profile_attempts": scene_profiles,
            "backoff_seconds": backoff_values,
        },
        "checks": {
            "state_is_failed_retry_exhausted": result.get("state")
            == "failed_retry_exhausted",
            "retry_ceiling_respected": len(retry_trace) == 3,
            "backoff_is_exponential": backoff_values == [2, 4, 8],
            "profile_fallback_order_is_deterministic": scene_profiles
            == [
                "seedance-quality-v1",
                "seedance-balanced-v1",
                "seedance-speed-v1",
                "seedance-speed-v1",
            ],
            "publish_not_attempted": factory.call_count("publish") == 0,
        },
        "retry_trace": retry_trace,
        "attempt_trace": result.get("attempt_trace", []),
    }


def _run_scenario(scenario: str) -> List[Tuple[str, Dict[str, Any]]]:
    if scenario == "cost-breaker":
        return [("task-7-cost-breaker.json", run_cost_breaker_scenario())]
    if scenario == "retry-ceiling":
        return [("task-7-retry-ceiling.json", run_retry_ceiling_scenario())]
    if scenario == "all":
        return [
            ("task-7-cost-breaker.json", run_cost_breaker_scenario()),
            ("task-7-retry-ceiling.json", run_retry_ceiling_scenario()),
        ]
    raise ValueError("unsupported scenario: %s" % scenario)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "scenario",
        choices=["cost-breaker", "retry-ceiling", "all"],
    )
    args = parser.parse_args()

    for file_name, payload in _run_scenario(args.scenario):
        path = _write_evidence(file_name, payload)
        print(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
