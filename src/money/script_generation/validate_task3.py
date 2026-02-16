import argparse
import json
from pathlib import Path
from typing import Any, Dict, Tuple

from money.script_generation.pipeline import merge_script_text, run_script_generation_pipeline


ROOT_DIR = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT_DIR / ".sisyphus" / "evidence"
ARTIFACT_DIR = ROOT_DIR / "build" / "task3"


def _sample_trend_candidate() -> Dict[str, Any]:
    return {
        "candidate_id": "trend-derivative-001",
        "source_platform": "youtube",
        "external_id": "yt-998877",
        "topic": "budget meal prep sequence",
        "signal_score": 0.91,
        "captured_at": "2026-02-16T00:00:00Z",
    }


def _sample_segmented_analysis() -> Dict[str, Any]:
    return {
        "analysis_id": "analysis-segments-001",
        "source_facts": [
            "audit one pantry category first",
            "batch prep two protein options",
            "end with a one-click shopping reminder",
        ],
        "segments": [
            {
                "segment_id": "seg-1",
                "start_ms": 0,
                "end_ms": 1300,
                "summary": "audit one pantry category first and show the price delta",
            },
            {
                "segment_id": "seg-2",
                "start_ms": 1300,
                "end_ms": 3100,
                "summary": "batch prep two protein options to cut weekday spend drift",
            },
            {
                "segment_id": "seg-3",
                "start_ms": 3100,
                "end_ms": 4700,
                "summary": "end with a one-click shopping reminder and weekly reset",
            },
        ],
    }


def _write_evidence(file_name: str, payload: Dict[str, Any]) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EVIDENCE_DIR / file_name
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def run_low_originality_scenario() -> Dict[str, Any]:
    trend_candidate = _sample_trend_candidate()
    segmented_source_analysis = _sample_segmented_analysis()

    baseline_result = run_script_generation_pipeline(
        trend_candidate=trend_candidate,
        segmented_source_analysis=segmented_source_analysis,
        locale="EN-US",
        output_dir=ARTIFACT_DIR / "baseline",
    )

    blocked_result = run_script_generation_pipeline(
        trend_candidate=trend_candidate,
        segmented_source_analysis=segmented_source_analysis,
        locale="EN-US",
        output_dir=ARTIFACT_DIR / "blocked",
        reference_corpus=[merge_script_text(baseline_result["script_draft"])],
    )

    return {
        "scenario": "low_originality_draft_rejected",
        "status": blocked_result["status"],
        "result_code": blocked_result["result_code"],
        "queue_state": blocked_result["approval_queue_state"],
        "rejection": blocked_result.get("rejection", {}),
        "script_draft": {
            "draft_id": blocked_result["script_draft"]["draft_id"],
            "similarity_score": blocked_result["script_draft"]["similarity_score"],
            "originality_threshold": blocked_result["script_draft"][
                "originality_threshold"
            ],
            "similarity_trace_id": blocked_result["script_draft"][
                "similarity_trace_id"
            ],
        },
        "artifacts": {
            "summary_pack": blocked_result["summary_pack_path"],
            "prompt_pack": blocked_result["prompt_pack_path"],
            "script_draft": blocked_result["script_draft_path"],
            "originality_record": blocked_result["originality_record_path"],
        },
    }


def _run_scenario(scenario: str) -> Tuple[str, Dict[str, Any]]:
    if scenario == "low-originality":
        return ("task-3-originality-block.json", run_low_originality_scenario())
    if scenario == "all":
        return ("task-3-originality-block.json", run_low_originality_scenario())
    raise ValueError("unsupported scenario: %s" % scenario)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=["low-originality", "all"])
    args = parser.parse_args()

    file_name, payload = _run_scenario(args.scenario)
    path = _write_evidence(file_name, payload)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
