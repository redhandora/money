from pathlib import Path

from money.localization.pipeline import (
    localize_all_supported_locales,
    localize_and_generate_voiceover,
)


def _base_script() -> dict:
    return {
        "draft_id": "draft-test-1",
        "candidate_id": "trend-test-1",
        "hook": "Three practical ways to improve watch time without hype",
        "body": (
            "Start with one strong hook, keep evidence visible, and avoid "
            "guaranteed claims"
        ),
        "cta": "Save this and test one improvement today",
    }


def test_ja_jp_localization_generates_language_tag_and_voiceover_metadata(
    tmp_path: Path,
) -> None:
    result = localize_and_generate_voiceover(
        script_draft=_base_script(),
        locale="JA-JP",
        similarity_score=0.41,
        declared_categories=["educational_general"],
        asset_root=tmp_path,
    )

    assert result["status"] == "ready_for_review"
    assert result["language_tag"] == "ja-JP"
    assert result["voiceover"] is not None
    assert result["voiceover"]["asset_path"].endswith("draft-test-1-ja-jp.wav")
    assert result["voiceover"]["duration_ms"] > 0
    assert "。" in result["variant"]["localized_script"]


def test_policy_block_is_deterministic_for_en_sea_variant() -> None:
    blocking_script = {
        "draft_id": "draft-block-1",
        "candidate_id": "trend-block-1",
        "hook": "Casino strategy for guaranteed wins",
        "body": "You can beat the house every time with this gambling pattern",
        "cta": "Start now for guaranteed returns",
    }
    result = localize_and_generate_voiceover(
        script_draft=blocking_script,
        locale="EN-SEA",
        similarity_score=0.33,
        declared_categories=["gambling_promotion"],
    )

    assert result["status"] == "blocked_policy"
    assert result["result_code"] == "BLOCKED_POLICY"
    assert result["voiceover"] is None
    assert result["policy"]["policy_code"] == "POLICY_BLOCKED_CATEGORY"
    assert result["policy"]["reason_code"] == "GAMBLING_SOLICITATION"
    assert result["policy"]["block_code"] == (
        "BLOCKED_POLICY::POLICY_BLOCKED_CATEGORY::GAMBLING_SOLICITATION"
    )


def test_all_locales_include_language_tags_and_voiceover_metadata(
    tmp_path: Path,
) -> None:
    outputs = localize_all_supported_locales(
        script_draft=_base_script(),
        similarity_score=0.4,
        declared_categories_by_locale={
            "EN-US": ["educational_general"],
            "EN-SEA": ["educational_general"],
            "JA-JP": ["educational_general"],
        },
        asset_root=tmp_path,
    )

    assert len(outputs) == 3
    by_locale = {item["locale"]: item for item in outputs}
    for locale in ["EN-US", "EN-SEA", "JA-JP"]:
        variant = by_locale[locale]
        assert variant["language_tag"]
        assert variant["voiceover"] is not None
        assert variant["voiceover"]["asset_path"]
        assert variant["voiceover"]["duration_ms"] > 0
