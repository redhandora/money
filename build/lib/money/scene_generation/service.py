import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from money.script_generation.schemas import PackValidationError, validate_prompt_pack


PHASE1_ALLOWED_ENGINE = "seedance"
DEFAULT_SEEDANCE_PROFILE = "seedance-default-v1"


class SceneGenerationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _stable_hash(parts: List[str]) -> str:
    joined = "|".join(parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:12]


def _write_json(path: Path, payload: Dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_prompt_pack(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_generation_gate(prompt_pack: Dict[str, Any], engine: str) -> None:
    if engine != PHASE1_ALLOWED_ENGINE:
        raise SceneGenerationError(
            code="BLOCKED_ENGINE_POLICY",
            message="phase-1 allows only Seedance scene generation",
        )

    try:
        validate_prompt_pack(prompt_pack)
    except PackValidationError as error:
        raise SceneGenerationError(
            code="BLOCKED_PROMPT_SCHEMA_INVALID",
            message="prompt pack schema invalid at %s (%s)" % (error.field, error.code),
        )

    quality_checks = prompt_pack.get("quality_checks", {})
    if not bool(quality_checks.get("schema_valid", False)):
        raise SceneGenerationError(
            code="BLOCKED_PROMPT_SCHEMA_INVALID",
            message="prompt pack quality_checks.schema_valid must be true",
        )

    if not bool(quality_checks.get("policy_pass", False)):
        raise SceneGenerationError(
            code="BLOCKED_POLICY_NOT_PASSED",
            message="prompt pack quality_checks.policy_pass must be true",
        )


def run_seedance_scene_generation(
    prompt_pack: Dict[str, Any],
    output_dir: Path,
    engine: str = PHASE1_ALLOWED_ENGINE,
    seedance_profile: Optional[str] = None,
) -> Dict[str, Any]:
    _validate_generation_gate(prompt_pack=prompt_pack, engine=engine)

    profile = seedance_profile or str(prompt_pack.get("seedance_profile_id", "")).strip()
    if not profile:
        profile = DEFAULT_SEEDANCE_PROFILE

    scene_assets_dir = output_dir / "scene_assets"
    scene_assets = []  # type: List[Dict[str, Any]]

    for scene_prompt in prompt_pack["scene_prompts"]:
        prompt_id = scene_prompt["prompt_id"]
        scene_fingerprint = _stable_hash(
            [prompt_pack["prompt_pack_id"], prompt_id, profile, scene_prompt["prompt_text"]]
        )
        scene_asset_uri = "seedance://{0}/{1}.mp4".format(
            prompt_pack["prompt_pack_id"],
            scene_fingerprint,
        )
        duration_ms = int(scene_prompt["target_duration_ms"])

        scene_file = scene_assets_dir / (scene_fingerprint + ".json")
        _write_json(
            scene_file,
            {
                "asset_id": scene_fingerprint,
                "engine": PHASE1_ALLOWED_ENGINE,
                "prompt_id": prompt_id,
                "scene_asset_uri": scene_asset_uri,
                "duration_ms": duration_ms,
                "seedance_profile": profile,
                "source_prompt_text": scene_prompt["prompt_text"],
            },
        )

        scene_assets.append(
            {
                "prompt_id": prompt_id,
                "beat_index": scene_prompt["beat_index"],
                "scene_asset_uri": scene_asset_uri,
                "duration_ms": duration_ms,
                "seedance_profile": profile,
                "scene_asset_path": str(scene_file),
            }
        )

    generation_result = {
        "status": "generated",
        "result_code": "PASS",
        "engine": PHASE1_ALLOWED_ENGINE,
        "prompt_pack_id": prompt_pack["prompt_pack_id"],
        "seedance_profile": profile,
        "scene_assets": scene_assets,
    }
    generation_manifest_path = _write_json(
        output_dir / "scene_generation.json",
        generation_result,
    )
    generation_result["scene_generation_path"] = str(generation_manifest_path)
    return generation_result
