from pathlib import Path
from typing import Dict, Optional


ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_ASSET_ROOT = ROOT_DIR / "build" / "voiceovers"

VOICE_PROFILE_BY_LOCALE = {
    "EN-US": "alloy-us-narration-v1",
    "EN-SEA": "marina-sea-conversational-v1",
    "JA-JP": "haruka-jp-neutral-v1",
}

CHARS_PER_SECOND_BY_LOCALE = {
    "EN-US": 15.0,
    "EN-SEA": 14.0,
    "JA-JP": 9.5,
}


def _to_repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def _estimate_duration_ms(locale: str, localized_script: str) -> int:
    normalized = "".join(localized_script.split())
    char_count = len(normalized)
    chars_per_second = CHARS_PER_SECOND_BY_LOCALE[locale]
    estimated = int(round((char_count / chars_per_second) * 1000.0))
    return max(900, estimated)


def generate_voiceover_asset(
    variant_id: str,
    locale: str,
    language_tag: str,
    localized_script: str,
    asset_root: Optional[Path] = None,
) -> Dict[str, object]:
    if locale not in VOICE_PROFILE_BY_LOCALE:
        raise ValueError("unsupported locale for TTS: {}".format(locale))

    root = asset_root if asset_root is not None else DEFAULT_ASSET_ROOT
    locale_dir = root / locale.lower()
    locale_dir.mkdir(parents=True, exist_ok=True)

    asset_path = locale_dir / "{}.wav".format(variant_id)
    duration_ms = _estimate_duration_ms(locale, localized_script)
    asset_path.write_text(
        (
            "SIMULATED_TTS_ASSET\n"
            "locale={}\n"
            "language_tag={}\n"
            "duration_ms={}\n"
            "script={}\n"
        ).format(
            locale,
            language_tag,
            duration_ms,
            localized_script,
        ),
        encoding="utf-8",
    )

    return {
        "provider": "seedance-tts-sim",
        "voice_profile": VOICE_PROFILE_BY_LOCALE[locale],
        "language_tag": language_tag,
        "asset_path": _to_repo_relative(asset_path),
        "duration_ms": duration_ms,
    }
