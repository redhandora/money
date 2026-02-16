import re
from typing import Dict


SUPPORTED_LOCALES = ("EN-US", "EN-SEA", "JA-JP")

LANGUAGE_TAG_BY_LOCALE = {
    "EN-US": "en-US",
    "EN-SEA": "en-SG",
    "JA-JP": "ja-JP",
}

VOICE_STYLE_BY_LOCALE = {
    "EN-US": "energetic",
    "EN-SEA": "conversational",
    "JA-JP": "neutral",
}


def _normalize_line(text: str) -> str:
    return " ".join(text.strip().split())


def _keyword_rewrite(text: str, replacements: Dict[str, str]) -> str:
    rewritten = text
    for source, target in replacements.items():
        rewritten = re.sub(
            r"\b{}\b".format(re.escape(source)),
            target,
            rewritten,
            flags=re.IGNORECASE,
        )
    return rewritten


def _transcreate_en_us(hook: str, body: str, cta: str) -> Dict[str, str]:
    hook_line = "Quick reality check: {}".format(hook.rstrip(".?!"))
    body_line = "{} Keep it practical, measurable, and hype-free.".format(
        body.rstrip(".?!")
    )
    cta_line = "Next action: {}.".format(cta.rstrip(".?!"))
    script = "{}\n{}\n{}".format(hook_line, body_line, cta_line)
    return {
        "localized_script": script,
        "transcreation_notes": (
            "US social-short cadence with direct hook and measurable CTA."
        ),
    }


def _transcreate_en_sea(hook: str, body: str, cta: str) -> Dict[str, str]:
    replacements = {
        "guaranteed": "steady",
        "profit": "upside",
        "daily": "day-to-day",
    }
    localized_hook = _keyword_rewrite(hook, replacements).rstrip(".?!")
    localized_body = _keyword_rewrite(body, replacements).rstrip(".?!")
    localized_cta = _keyword_rewrite(cta, replacements).rstrip(".?!")
    script = "{}\n{}\n{}".format(
        "SEA creator note: {}".format(localized_hook),
        "{} Focus on low-risk steps that fit mobile-first viewers.".format(
            localized_body
        ),
        "Try this in your next posting cycle: {}.".format(localized_cta),
    )
    return {
        "localized_script": script,
        "transcreation_notes": (
            "Southeast Asia transcreation with practical, low-risk framing."
        ),
    }


def _transcreate_ja(hook: str, body: str, cta: str) -> Dict[str, str]:
    replacements = {
        "guaranteed": "確実",
        "profit": "利益",
        "growth": "成長",
        "quick": "短時間",
        "daily": "毎日",
        "tips": "コツ",
        "risk": "リスク",
        "money": "お金",
    }
    ja_hook = _keyword_rewrite(hook, replacements).rstrip(".?!")
    ja_body = _keyword_rewrite(body, replacements).rstrip(".?!")
    ja_cta = _keyword_rewrite(cta, replacements).rstrip(".?!")
    script = "{}\n{}\n{}".format(
        "冒頭で要点を共有します: {}。".format(ja_hook),
        "{}。誇張表現を避け、再現できる手順に整えます。".format(ja_body),
        "次の一歩: {}。".format(ja_cta),
    )
    return {
        "localized_script": script,
        "transcreation_notes": (
            "Japanese adaptation rewrites cadence and claim strength for "
            "policy-safe tone."
        ),
    }


def transcreate_script(script_draft: Dict[str, str], locale: str) -> Dict[str, str]:
    if locale not in SUPPORTED_LOCALES:
        raise ValueError("unsupported locale: {}".format(locale))

    hook = _normalize_line(script_draft.get("hook", ""))
    body = _normalize_line(script_draft.get("body", ""))
    cta = _normalize_line(script_draft.get("cta", ""))

    if not hook or not body or not cta:
        raise ValueError("script draft must include non-empty hook/body/cta")

    if locale == "EN-US":
        transcreated = _transcreate_en_us(hook, body, cta)
    elif locale == "EN-SEA":
        transcreated = _transcreate_en_sea(hook, body, cta)
    else:
        transcreated = _transcreate_ja(hook, body, cta)

    return {
        "locale": locale,
        "language_tag": LANGUAGE_TAG_BY_LOCALE[locale],
        "voice_style": VOICE_STYLE_BY_LOCALE[locale],
        "localized_script": transcreated["localized_script"],
        "transcreation_notes": transcreated["transcreation_notes"],
    }
