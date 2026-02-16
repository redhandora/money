import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Set


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> Set[str]:
    tokens = TOKEN_PATTERN.findall(text.lower())
    return set(token for token in tokens if len(token) >= 3)


def _jaccard_similarity(left: Set[str], right: Set[str]) -> float:
    union = left.union(right)
    if not union:
        return 0.0
    return float(len(left.intersection(right))) / float(len(union))


def compute_similarity_score(script_text: str, reference_texts: Iterable[str]) -> float:
    script_tokens = _tokenize(script_text)
    best_similarity = 0.0

    for reference_text in reference_texts:
        similarity = _jaccard_similarity(script_tokens, _tokenize(reference_text))
        if similarity > best_similarity:
            best_similarity = similarity

    return round(best_similarity, 4)


def compute_originality_score(similarity_score: float) -> float:
    return round(max(0.0, 1.0 - similarity_score), 4)


def build_similarity_trace_id(candidate_id: str, locale: str, similarity_score: float) -> str:
    fingerprint_source = "%s|%s|%.4f" % (candidate_id, locale, similarity_score)
    digest = hashlib.sha1(fingerprint_source.encode("utf-8")).hexdigest()
    return "trace-%s" % digest[:12]


def persist_originality_score(
    output_dir: Path,
    draft_id: str,
    candidate_id: str,
    locale: str,
    similarity_score: float,
    originality_threshold: float,
    reference_count: int,
) -> Dict[str, Any]:
    similarity_trace_id = build_similarity_trace_id(
        candidate_id=candidate_id,
        locale=locale,
        similarity_score=similarity_score,
    )
    originality_score = compute_originality_score(similarity_score)

    payload = {
        "draft_id": draft_id,
        "candidate_id": candidate_id,
        "locale": locale,
        "similarity_trace_id": similarity_trace_id,
        "similarity_score": similarity_score,
        "originality_score": originality_score,
        "originality_threshold": originality_threshold,
        "reference_count": reference_count,
        "result_code": "BLOCKED_ORIGINALITY"
        if similarity_score >= originality_threshold
        else "PASS",
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / ("%s.json" % draft_id)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    payload["path"] = str(output_path)
    return payload
