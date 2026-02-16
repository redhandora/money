import json
from pathlib import Path
from typing import Any, Dict

import pytest

from money.script_generation.pipeline import merge_script_text, run_script_generation_pipeline
from money.script_generation.schemas import PackValidationError, validate_prompt_pack


def _trend_candidate() -> Dict[str, Any]:
    return {
        "candidate_id": "trend-001",
        "source_platform": "youtube",
        "external_id": "yt-123",
        "topic": "weekly grocery budgeting",
        "signal_score": 0.88,
        "captured_at": "2026-02-16T00:00:00Z",
    }


def _segmented_source_analysis() -> Dict[str, Any]:
    return {
        "analysis_id": "analysis-001",
        "source_facts": [
            "audit one pantry category first",
            "set a fixed cap for weekday meals",
            "close with a weekly reset checklist",
        ],
        "segments": [
            {
                "segment_id": "seg-1",
                "start_ms": 0,
                "end_ms": 1400,
                "summary": "audit one pantry category first and reveal hidden spend",
            },
            {
                "segment_id": "seg-2",
                "start_ms": 1400,
                "end_ms": 3200,
                "summary": "set a fixed cap for weekday meals and track drift nightly",
            },
            {
                "segment_id": "seg-3",
                "start_ms": 3200,
                "end_ms": 5000,
                "summary": "close with a weekly reset checklist and next-action reminder",
            },
        ],
    }


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_pipeline_generates_required_script_fields_and_artifacts(tmp_path: Path) -> None:
    result = run_script_generation_pipeline(
        trend_candidate=_trend_candidate(),
        segmented_source_analysis=_segmented_source_analysis(),
        locale="EN-US",
        output_dir=tmp_path,
    )

    script_draft = result["script_draft"]
    assert result["result_code"] == "PASS"
    assert script_draft["hook"]
    assert script_draft["body"]
    assert script_draft["cta"]

    summary_pack = _load_json(tmp_path / "summary_pack.json")
    prompt_pack = _load_json(tmp_path / "prompt_pack.json")
    assert summary_pack["factual_quality"]["passes"] is True
    assert prompt_pack["quality_checks"]["schema_valid"] is True
    assert prompt_pack["quality_checks"]["policy_pass"] is True


def test_originality_score_is_persisted(tmp_path: Path) -> None:
    result = run_script_generation_pipeline(
        trend_candidate=_trend_candidate(),
        segmented_source_analysis=_segmented_source_analysis(),
        locale="EN-US",
        output_dir=tmp_path,
    )

    originality_record_path = Path(result["originality_record_path"])
    originality_record = _load_json(originality_record_path)
    assert originality_record["draft_id"] == result["script_draft"]["draft_id"]
    assert "originality_score" in originality_record
    assert originality_record["similarity_trace_id"] == result["script_draft"][
        "similarity_trace_id"
    ]


def test_low_originality_draft_is_rejected_with_explicit_code(tmp_path: Path) -> None:
    baseline_result = run_script_generation_pipeline(
        trend_candidate=_trend_candidate(),
        segmented_source_analysis=_segmented_source_analysis(),
        locale="EN-US",
        output_dir=tmp_path / "baseline",
    )

    blocked_result = run_script_generation_pipeline(
        trend_candidate=_trend_candidate(),
        segmented_source_analysis=_segmented_source_analysis(),
        locale="EN-US",
        output_dir=tmp_path / "blocked",
        reference_corpus=[merge_script_text(baseline_result["script_draft"])],
    )

    assert blocked_result["status"] == "rejected_originality"
    assert blocked_result["result_code"] == "BLOCKED_ORIGINALITY"
    assert blocked_result["approval_queue_state"] == "not_enqueued"
    assert blocked_result["rejection"]["code"] == "BLOCKED_ORIGINALITY"


def test_prompt_pack_contains_beat_windows_and_shot_constraints(tmp_path: Path) -> None:
    run_script_generation_pipeline(
        trend_candidate=_trend_candidate(),
        segmented_source_analysis=_segmented_source_analysis(),
        locale="EN-US",
        output_dir=tmp_path,
    )

    prompt_pack = _load_json(tmp_path / "prompt_pack.json")
    assert prompt_pack["rhythm_fidelity_target"] == "medium_high"
    assert len(prompt_pack["beat_windows"]) >= 3
    assert prompt_pack["shot_duration_constraints"]["min_ms"] == 700
    assert prompt_pack["shot_duration_constraints"]["max_ms"] == 1800
    assert prompt_pack["shot_duration_constraints"]["max_jump_ratio"] == 2.5

    for scene_prompt in prompt_pack["scene_prompts"]:
        assert "beat_window_ms" in scene_prompt
        assert "shot_duration_ms" in scene_prompt
        assert scene_prompt["beat_window_ms"]["end_ms"] > scene_prompt["beat_window_ms"][
            "start_ms"
        ]


def test_prompt_pack_schema_validation_rejects_missing_beat_windows(
    tmp_path: Path,
) -> None:
    run_script_generation_pipeline(
        trend_candidate=_trend_candidate(),
        segmented_source_analysis=_segmented_source_analysis(),
        locale="EN-US",
        output_dir=tmp_path,
    )
    prompt_pack = _load_json(tmp_path / "prompt_pack.json")
    prompt_pack.pop("beat_windows")

    with pytest.raises(PackValidationError) as error:
        validate_prompt_pack(prompt_pack)

    assert error.value.code == "PACK_REQUIRED_FIELD"
    assert error.value.field == "prompt_pack.beat_windows"


def test_pipeline_outputs_are_deterministic_for_same_input(tmp_path: Path) -> None:
    first_output_dir = tmp_path / "first"
    second_output_dir = tmp_path / "second"

    run_script_generation_pipeline(
        trend_candidate=_trend_candidate(),
        segmented_source_analysis=_segmented_source_analysis(),
        locale="EN-US",
        output_dir=first_output_dir,
    )
    run_script_generation_pipeline(
        trend_candidate=_trend_candidate(),
        segmented_source_analysis=_segmented_source_analysis(),
        locale="EN-US",
        output_dir=second_output_dir,
    )

    first_summary_pack = _load_json(first_output_dir / "summary_pack.json")
    second_summary_pack = _load_json(second_output_dir / "summary_pack.json")
    first_prompt_pack = _load_json(first_output_dir / "prompt_pack.json")
    second_prompt_pack = _load_json(second_output_dir / "prompt_pack.json")
    first_script_draft = _load_json(first_output_dir / "script_draft.json")
    second_script_draft = _load_json(second_output_dir / "script_draft.json")

    assert first_summary_pack == second_summary_pack
    assert first_prompt_pack == second_prompt_pack
    assert first_script_draft == second_script_draft
