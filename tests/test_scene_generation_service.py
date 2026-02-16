import json
from pathlib import Path
from typing import Any, Dict

import pytest

from money.scene_generation.service import SceneGenerationError, run_seedance_scene_generation


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _prompt_pack_fixture() -> Dict[str, Any]:
    return {
        "schema_version": "2026-02-16",
        "prompt_pack_id": "prompt-pack-scene-001",
        "source_summary_id": "summary-001",
        "candidate_id": "trend-001",
        "locale": "EN-US",
        "seedance_profile_id": "seedance-default-v1",
        "rhythm_fidelity_target": "medium_high",
        "beat_windows": [
            {"beat_index": 1, "start_ms": 0, "end_ms": 1200},
            {"beat_index": 2, "start_ms": 1200, "end_ms": 3000},
            {"beat_index": 3, "start_ms": 3000, "end_ms": 4600},
        ],
        "shot_duration_constraints": {
            "min_ms": 700,
            "max_ms": 1800,
            "max_jump_ratio": 2.5,
            "max_whiplash_per_8s": 2,
        },
        "scene_prompts": [
            {
                "prompt_id": "prompt-1",
                "beat_index": 1,
                "script_role": "hook",
                "prompt_text": "Generate an original hook scene from beat one with transformed visuals and no source shot reuse.",
                "beat_window_ms": {"start_ms": 0, "end_ms": 1200},
                "target_duration_ms": 1200,
                "shot_duration_ms": {"min_ms": 700, "max_ms": 1800},
                "seedance_profile_id": "seedance-default-v1",
            },
            {
                "prompt_id": "prompt-2",
                "beat_index": 2,
                "script_role": "body",
                "prompt_text": "Generate an original body scene from beat two with transformed visuals and no source shot reuse.",
                "beat_window_ms": {"start_ms": 1200, "end_ms": 3000},
                "target_duration_ms": 1800,
                "shot_duration_ms": {"min_ms": 700, "max_ms": 1800},
                "seedance_profile_id": "seedance-default-v1",
            },
            {
                "prompt_id": "prompt-3",
                "beat_index": 3,
                "script_role": "cta",
                "prompt_text": "Generate an original cta scene from beat three with transformed visuals and no source shot reuse.",
                "beat_window_ms": {"start_ms": 3000, "end_ms": 4600},
                "target_duration_ms": 1600,
                "shot_duration_ms": {"min_ms": 700, "max_ms": 1800},
                "seedance_profile_id": "seedance-default-v1",
            },
        ],
        "quality_checks": {
            "schema_valid": True,
            "ambiguity_score": 0.0,
            "ambiguity_threshold": 0.15,
            "policy_violations": [],
            "policy_pass": True,
        },
    }


def test_generation_outputs_required_scene_metadata(tmp_path: Path) -> None:
    result = run_seedance_scene_generation(
        prompt_pack=_prompt_pack_fixture(),
        output_dir=tmp_path,
    )

    assert result["status"] == "generated"
    assert result["result_code"] == "PASS"
    assert result["engine"] == "seedance"
    assert result["seedance_profile"] == "seedance-default-v1"
    assert len(result["scene_assets"]) == 3

    for scene_asset in result["scene_assets"]:
        assert scene_asset["scene_asset_uri"].startswith("seedance://")
        assert scene_asset["duration_ms"] > 0
        assert scene_asset["seedance_profile"] == "seedance-default-v1"
        scene_asset_path = Path(scene_asset["scene_asset_path"])
        assert scene_asset_path.exists()
        persisted = _load_json(scene_asset_path)
        assert persisted["scene_asset_uri"] == scene_asset["scene_asset_uri"]


def test_generation_blocks_schema_invalid_prompt_pack(tmp_path: Path) -> None:
    prompt_pack = _prompt_pack_fixture()
    prompt_pack.pop("scene_prompts")

    with pytest.raises(SceneGenerationError) as error:
        run_seedance_scene_generation(prompt_pack=prompt_pack, output_dir=tmp_path)

    assert error.value.code == "BLOCKED_PROMPT_SCHEMA_INVALID"


def test_generation_blocks_when_policy_gate_not_passed(tmp_path: Path) -> None:
    prompt_pack = _prompt_pack_fixture()
    prompt_pack["quality_checks"]["policy_pass"] = False

    with pytest.raises(SceneGenerationError) as error:
        run_seedance_scene_generation(prompt_pack=prompt_pack, output_dir=tmp_path)

    assert error.value.code == "BLOCKED_POLICY_NOT_PASSED"


def test_generation_enforces_seedance_single_engine_policy(tmp_path: Path) -> None:
    with pytest.raises(SceneGenerationError) as error:
        run_seedance_scene_generation(
            prompt_pack=_prompt_pack_fixture(),
            output_dir=tmp_path,
            engine="other-engine",
        )

    assert error.value.code == "BLOCKED_ENGINE_POLICY"
