from typing import Dict, Iterable, List, Optional, Set

from money.contracts.validate_task1 import evaluate_policy


KEYWORD_TO_CATEGORY_BY_LOCALE = {
    "EN-US": {
        "guaranteed": "guaranteed_financial_return",
        "cure": "medical_misinformation",
        "illegal": "illegal_activity",
    },
    "EN-SEA": {
        "gambling": "gambling_promotion",
        "casino": "gambling_promotion",
        "crypto guarantee": "crypto_guarantee",
        "cure": "medical_misinformation",
    },
    "JA-JP": {
        "ビフォーアフター": "deceptive_before_after",
        "絶対に治る": "medical_misinformation",
        "違法": "illegal_activity",
    },
}


def _detect_policy_categories(locale: str, localized_script: str) -> List[str]:
    categories = set()  # type: Set[str]
    lowered_script = localized_script.lower()
    locale_rules = KEYWORD_TO_CATEGORY_BY_LOCALE.get(locale, {})
    for phrase, category in locale_rules.items():
        if phrase.lower() in lowered_script:
            categories.add(category)
    return sorted(categories)


def _merge_categories(
    detected: Iterable[str],
    declared: Optional[Iterable[str]],
) -> List[str]:
    merged = set(detected)  # type: Set[str]
    for category in declared or []:
        merged.add(category)
    return sorted(merged)


def evaluate_localized_variant_policy(
    locale: str,
    localized_script: str,
    similarity_score: float,
    declared_categories: Optional[Iterable[str]] = None,
) -> Dict[str, object]:
    detected = _detect_policy_categories(locale, localized_script)
    merged_categories = _merge_categories(detected, declared_categories)
    policy_result = evaluate_policy(
        locale=locale,
        categories=merged_categories,
        similarity_score=similarity_score,
    )

    status = "policy_passed"
    result_code = "PASS"
    block_code = "PASS::PASS::PASS"
    if policy_result["status"] == "blocked":
        status = "blocked_policy"
        result_code = "BLOCKED_POLICY"
        block_code = "BLOCKED_POLICY::{policy_code}::{reason_code}".format(
            policy_code=policy_result["policy_code"],
            reason_code=policy_result["reason_code"],
        )

    return {
        "status": status,
        "result_code": result_code,
        "policy_code": policy_result["policy_code"],
        "reason_code": policy_result["reason_code"],
        "block_code": block_code,
        "categories": merged_categories,
        "similarity_score": policy_result.get("similarity_score", similarity_score),
        "originality_threshold": policy_result.get("originality_threshold"),
    }
