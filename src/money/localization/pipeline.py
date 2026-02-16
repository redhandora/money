import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .policy_gate import evaluate_localized_variant_policy
from .transcreation import SUPPORTED_LOCALES, transcreate_script
from .voiceover import generate_voiceover_asset


ROOT_DIR = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT_DIR / ".sisyphus" / "evidence"


def _safe_policy_categories(categories: object) -> List[str]:
    if isinstance(categories, list):
        normalized = []  # type: List[str]
        for category in categories:
            if isinstance(category, str) and category:
                normalized.append(category)
        if normalized:
            return normalized
    return ["safe_general"]


def localize_and_generate_voiceover(
    script_draft: Dict[str, str],
    locale: str,
    similarity_score: float,
    declared_categories: Optional[Iterable[str]] = None,
    asset_root: Optional[Path] = None,
) -> Dict[str, object]:
    transcreated = transcreate_script(script_draft=script_draft, locale=locale)
    policy = evaluate_localized_variant_policy(
        locale=locale,
        localized_script=transcreated["localized_script"],
        similarity_score=similarity_score,
        declared_categories=declared_categories,
    )

    draft_id = script_draft["draft_id"]
    variant_id = "{}-{}".format(draft_id, locale.lower())
    variant = {
        "variant_id": variant_id,
        "draft_id": draft_id,
        "locale": locale,
        "localized_script": transcreated["localized_script"],
        "voice_style": transcreated["voice_style"],
        "policy_categories": _safe_policy_categories(policy["categories"]),
        "policy_result_code": policy["result_code"],
    }

    response = {
        "status": "blocked_policy",
        "result_code": "BLOCKED_POLICY",
        "locale": locale,
        "language_tag": transcreated["language_tag"],
        "transcreation_notes": transcreated["transcreation_notes"],
        "variant": variant,
        "voiceover": None,
        "policy": policy,
    }

    if policy["status"] != "blocked_policy":
        response["status"] = "ready_for_review"
        response["result_code"] = "PASS"
        response["voiceover"] = generate_voiceover_asset(
            variant_id=variant_id,
            locale=locale,
            language_tag=transcreated["language_tag"],
            localized_script=transcreated["localized_script"],
            asset_root=asset_root,
        )

    return response


def localize_all_supported_locales(
    script_draft: Dict[str, str],
    similarity_score: float,
    declared_categories_by_locale: Optional[Dict[str, List[str]]] = None,
    asset_root: Optional[Path] = None,
) -> List[Dict[str, object]]:
    categories_by_locale = declared_categories_by_locale or {}
    outputs = []  # type: List[Dict[str, object]]
    for locale in SUPPORTED_LOCALES:
        outputs.append(
            localize_and_generate_voiceover(
                script_draft=script_draft,
                locale=locale,
                similarity_score=similarity_score,
                declared_categories=categories_by_locale.get(locale, []),
                asset_root=asset_root,
            )
        )
    return outputs


def _base_script_payload() -> Dict[str, str]:
    return {
        "draft_id": "draft-004",
        "candidate_id": "trend-004",
        "hook": "Three mistakes creators make when trying to grow revenue fast",
        "body": (
            "Use a repeatable workflow, measure retention by segment, and avoid "
            "guaranteed wealth promises"
        ),
        "cta": "Save this checklist and test one change today",
    }


def run_ja_output_scenario() -> Dict[str, object]:
    payload = _base_script_payload()
    return {
        "scenario": "ja_jp_localization_voiceover",
        "input": {
            "locale": "JA-JP",
            "similarity_score": 0.44,
            "declared_categories": ["educational_general"],
        },
        "result": localize_and_generate_voiceover(
            script_draft=payload,
            locale="JA-JP",
            similarity_score=0.44,
            declared_categories=["educational_general"],
        ),
    }


def run_policy_block_scenario() -> Dict[str, object]:
    payload = {
        "draft_id": "draft-004-block",
        "candidate_id": "trend-004",
        "hook": "Crypto guaranteed win formula for this weekend",
        "body": "Use this gambling system and you will always beat the casino",
        "cta": "Start now and lock guaranteed returns",
    }
    return {
        "scenario": "en_sea_localization_policy_block",
        "input": {
            "locale": "EN-SEA",
            "similarity_score": 0.35,
            "declared_categories": ["gambling_promotion"],
        },
        "result": localize_and_generate_voiceover(
            script_draft=payload,
            locale="EN-SEA",
            similarity_score=0.35,
            declared_categories=["gambling_promotion"],
        ),
    }


def _write_evidence(file_name: str, payload: Dict[str, object]) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    target = EVIDENCE_DIR / file_name
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=["ja-output", "policy-block", "all"])
    args = parser.parse_args()

    if args.scenario in {"ja-output", "all"}:
        output = run_ja_output_scenario()
        print(_write_evidence("task-4-ja-output.json", output))

    if args.scenario in {"policy-block", "all"}:
        output = run_policy_block_scenario()
        print(_write_evidence("task-4-policy-block.json", output))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
