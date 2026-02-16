import argparse
import json
from pathlib import Path
from typing import Any, Dict, Tuple

from money.scene_generation.service import (
    SceneGenerationError,
    load_prompt_pack,
    run_seedance_scene_generation,
)


ROOT_DIR = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT_DIR / ".sisyphus" / "evidence"
PROMPT_PACK_PATH = ROOT_DIR / "build" / "task3" / "baseline" / "prompt_pack.json"
ARTIFACT_DIR = ROOT_DIR / "build" / "task3a"


def _write_evidence(file_name: str, payload: Dict[str, Any]) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EVIDENCE_DIR / file_name
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def _base_prompt_pack() -> Dict[str, Any]:
    return load_prompt_pack(PROMPT_PACK_PATH)


def run_success_scenario() -> Dict[str, Any]:
    prompt_pack = _base_prompt_pack()
    output_dir = ARTIFACT_DIR / "success"
    result = run_seedance_scene_generation(prompt_pack=prompt_pack, output_dir=output_dir)
    return {
        "scenario": "seedance_generation_success",
        "status": result["status"],
        "result_code": result["result_code"],
        "engine": result["engine"],
        "seedance_profile": result["seedance_profile"],
        "scene_count": len(result["scene_assets"]),
        "scene_assets": result["scene_assets"],
        "scene_generation_path": result["scene_generation_path"],
    }


def _capture_block(error: SceneGenerationError) -> Dict[str, Any]:
    return {
        "status": "blocked",
        "result_code": error.code,
        "message": str(error),
    }


def run_block_scenario() -> Dict[str, Any]:
    schema_invalid_prompt_pack = _base_prompt_pack()
    schema_invalid_prompt_pack.pop("scene_prompts")

    policy_blocked_prompt_pack = _base_prompt_pack()
    policy_blocked_prompt_pack["quality_checks"] = dict(policy_blocked_prompt_pack["quality_checks"])
    policy_blocked_prompt_pack["quality_checks"]["policy_pass"] = False

    schema_block = {}
    policy_block = {}

    try:
        run_seedance_scene_generation(
            prompt_pack=schema_invalid_prompt_pack,
            output_dir=ARTIFACT_DIR / "blocked-schema",
        )
    except SceneGenerationError as error:
        schema_block = _capture_block(error)

    try:
        run_seedance_scene_generation(
            prompt_pack=policy_blocked_prompt_pack,
            output_dir=ARTIFACT_DIR / "blocked-policy",
        )
    except SceneGenerationError as error:
        policy_block = _capture_block(error)

    return {
        "scenario": "seedance_generation_blocked",
        "schema_invalid": schema_block,
        "policy_not_passed": policy_block,
    }


def _run_scenario(scenario: str) -> Tuple[str, Dict[str, Any]]:
    if scenario == "seedance-output":
        return ("task-3a-seedance-output.json", run_success_scenario())
    if scenario == "seedance-block":
        return ("task-3a-seedance-block.json", run_block_scenario())
    if scenario == "all":
        raise ValueError("all scenario handled in main")
    raise ValueError("unsupported scenario: %s" % scenario)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=["seedance-output", "seedance-block", "all"])
    args = parser.parse_args()

    if args.scenario == "all":
        output_path = _write_evidence("task-3a-seedance-output.json", run_success_scenario())
        block_path = _write_evidence("task-3a-seedance-block.json", run_block_scenario())
        print(output_path)
        print(block_path)
        return 0

    file_name, payload = _run_scenario(args.scenario)
    path = _write_evidence(file_name, payload)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
