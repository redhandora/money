import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from money.contracts.validate_task1 import validate_contract
from money.script_generation.originality import (
    compute_similarity_score,
    persist_originality_score,
)
from money.script_generation.schemas import (
    PackValidationError,
    validate_prompt_pack,
    validate_summary_pack,
)


ROOT_DIR = Path(__file__).resolve().parents[3]
POLICY_PATH = ROOT_DIR / "docs" / "policy" / "locale_compliance_policy.json"


class ScriptGenerationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _stable_id(prefix: str, parts: Sequence[str]) -> str:
    seed = "|".join(parts)
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    return "%s-%s" % (prefix, digest[:12])


def _segment_role(index: int, total: int) -> str:
    if index == 0:
        return "hook"
    if index == total - 1:
        return "cta"
    return "body"


def _normalize_segments(segmented_source_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_segments = segmented_source_analysis.get("segments")
    if not isinstance(raw_segments, list) or len(raw_segments) < 3:
        raise ScriptGenerationError(
            code="SEGMENTS_MIN_ITEMS",
            message="segmented_source_analysis.segments must have at least three entries",
        )

    normalized: List[Dict[str, Any]] = []
    for index, raw_segment in enumerate(raw_segments):
        segment_id = str(raw_segment.get("segment_id", "")).strip()
        summary = str(raw_segment.get("summary", "")).strip()
        if not segment_id:
            raise ScriptGenerationError(
                code="SEGMENTS_REQUIRED_FIELD",
                message="segment_id is required at index %d" % index,
            )
        if len(summary) < 5:
            raise ScriptGenerationError(
                code="SEGMENTS_SUMMARY_TOO_SHORT",
                message="summary must have at least five characters at index %d" % index,
            )

        try:
            start_ms = int(raw_segment.get("start_ms"))
            end_ms = int(raw_segment.get("end_ms"))
        except (TypeError, ValueError):
            raise ScriptGenerationError(
                code="SEGMENTS_TIME_TYPE_MISMATCH",
                message="start_ms and end_ms must be integers",
            )

        if start_ms < 0 or end_ms <= start_ms:
            raise ScriptGenerationError(
                code="SEGMENTS_TIME_RANGE_INVALID",
                message="end_ms must be greater than start_ms",
            )

        normalized.append(
            {
                "segment_id": segment_id,
                "summary": summary,
                "start_ms": start_ms,
                "end_ms": end_ms,
            }
        )

    return normalized


def _build_factual_quality(
    source_facts: Sequence[str],
    segments: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    joined_segment_text = " ".join(segment["summary"].lower() for segment in segments)
    checked_facts = [fact.strip() for fact in source_facts if fact and fact.strip()]

    if not checked_facts:
        factual_precision = 1.0
    else:
        matched_count = 0
        for fact in checked_facts:
            if fact.lower() in joined_segment_text:
                matched_count += 1
        factual_precision = round(float(matched_count) / float(len(checked_facts)), 4)

    hallucination_rate = round(max(0.0, 1.0 - factual_precision), 4)
    precision_threshold = 0.95
    hallucination_threshold = 0.02
    passes = (
        factual_precision >= precision_threshold
        and hallucination_rate <= hallucination_threshold
    )

    return {
        "factual_precision": factual_precision,
        "hallucination_rate": hallucination_rate,
        "precision_threshold": precision_threshold,
        "hallucination_threshold": hallucination_threshold,
        "passes": passes,
    }


def _max_duration_jump_ratio(beat_map: Sequence[Dict[str, Any]]) -> float:
    durations = [beat["duration_ms"] for beat in beat_map]
    if len(durations) < 2:
        return 1.0

    max_ratio = 1.0
    for index in range(1, len(durations)):
        left = durations[index - 1]
        right = durations[index]
        low = min(left, right)
        high = max(left, right)
        if low <= 0:
            continue
        ratio = float(high) / float(low)
        if ratio > max_ratio:
            max_ratio = ratio

    return round(max_ratio, 4)


def build_summary_pack(
    trend_candidate: Dict[str, Any],
    segmented_source_analysis: Dict[str, Any],
    locale: str,
) -> Dict[str, Any]:
    candidate_id = str(trend_candidate.get("candidate_id", "")).strip()
    topic = str(trend_candidate.get("topic", "")).strip()
    source_analysis_id = str(segmented_source_analysis.get("analysis_id", "")).strip()

    if not candidate_id:
        raise ScriptGenerationError(
            code="TREND_REQUIRED_FIELD",
            message="trend_candidate.candidate_id is required",
        )
    if len(topic) < 3:
        raise ScriptGenerationError(
            code="TREND_TOPIC_INVALID",
            message="trend_candidate.topic must have at least three characters",
        )
    if not source_analysis_id:
        raise ScriptGenerationError(
            code="ANALYSIS_REQUIRED_FIELD",
            message="segmented_source_analysis.analysis_id is required",
        )

    source_facts = segmented_source_analysis.get("source_facts", [])
    if not isinstance(source_facts, list):
        raise ScriptGenerationError(
            code="ANALYSIS_SOURCE_FACTS_TYPE",
            message="segmented_source_analysis.source_facts must be an array",
        )

    segments = _normalize_segments(segmented_source_analysis)
    keypoints: List[Dict[str, Any]] = []
    beat_map: List[Dict[str, Any]] = []

    for index, segment in enumerate(segments):
        role = _segment_role(index=index, total=len(segments))
        order = index + 1
        duration_ms = segment["end_ms"] - segment["start_ms"]

        keypoints.append(
            {
                "order": order,
                "role": role,
                "text": segment["summary"],
                "source_segment_id": segment["segment_id"],
            }
        )
        beat_map.append(
            {
                "beat_index": order,
                "segment_id": segment["segment_id"],
                "start_ms": segment["start_ms"],
                "end_ms": segment["end_ms"],
                "duration_ms": duration_ms,
            }
        )

    pacing_map = {
        "total_duration_ms": sum(beat["duration_ms"] for beat in beat_map),
        "max_duration_jump_ratio": _max_duration_jump_ratio(beat_map),
    }

    summary_pack = {
        "schema_version": "2026-02-16",
        "summary_id": _stable_id("summary", [candidate_id, locale, source_analysis_id]),
        "source_analysis_id": source_analysis_id,
        "candidate_id": candidate_id,
        "locale": locale,
        "topic": topic,
        "analysis_only": True,
        "factual_quality": _build_factual_quality(source_facts, segments),
        "keypoints": keypoints,
        "beat_map": beat_map,
        "pacing_map": pacing_map,
    }

    validate_summary_pack(summary_pack)
    if not summary_pack["factual_quality"]["passes"]:
        raise ScriptGenerationError(
            code="SUMMARY_FACTUAL_QUALITY_BLOCKED",
            message="summary pack factual checks did not pass",
        )

    return summary_pack


def _compute_ambiguity_score(scene_prompts: Sequence[Dict[str, Any]]) -> float:
    ambiguous_tokens = set(["thing", "things", "stuff", "maybe", "somehow", "etc"])

    token_count = 0
    ambiguous_count = 0
    for scene_prompt in scene_prompts:
        words = scene_prompt["prompt_text"].lower().split()
        for raw_word in words:
            cleaned_word = raw_word.strip(".,:;!?()[]{}\"")
            if not cleaned_word:
                continue
            token_count += 1
            if cleaned_word in ambiguous_tokens:
                ambiguous_count += 1

    if token_count == 0:
        return 1.0
    return round(float(ambiguous_count) / float(token_count), 4)


def _detect_policy_violations(scene_prompts: Sequence[Dict[str, Any]]) -> List[str]:
    policy_phrases = [
        "guaranteed profit",
        "risk free return",
        "medical cure",
        "illegal trick",
        "bet now",
    ]
    joined_text = " ".join(scene["prompt_text"].lower() for scene in scene_prompts)

    violations: List[str] = []
    for phrase in policy_phrases:
        if phrase in joined_text:
            violations.append(phrase)
    return violations


def build_prompt_pack(summary_pack: Dict[str, Any]) -> Dict[str, Any]:
    shot_duration_constraints = {
        "min_ms": 700,
        "max_ms": 1800,
        "max_jump_ratio": 2.5,
        "max_whiplash_per_8s": 2,
    }

    beat_windows = []
    scene_prompts = []
    for keypoint, beat in zip(summary_pack["keypoints"], summary_pack["beat_map"]):
        beat_window = {
            "beat_index": beat["beat_index"],
            "start_ms": beat["start_ms"],
            "end_ms": beat["end_ms"],
        }
        beat_windows.append(beat_window)

        prompt_text = (
            "Generate an original {role} scene for topic '{topic}' using this beat: "
            "{detail}. Keep visuals transformed and avoid source shot reuse."
        ).format(
            role=keypoint["role"],
            topic=summary_pack["topic"],
            detail=keypoint["text"],
        )

        scene_prompts.append(
            {
                "prompt_id": _stable_id(
                    "prompt",
                    [summary_pack["summary_id"], str(beat["beat_index"])],
                ),
                "beat_index": beat["beat_index"],
                "script_role": keypoint["role"],
                "prompt_text": prompt_text,
                "beat_window_ms": {
                    "start_ms": beat["start_ms"],
                    "end_ms": beat["end_ms"],
                },
                "target_duration_ms": beat["duration_ms"],
                "shot_duration_ms": {
                    "min_ms": shot_duration_constraints["min_ms"],
                    "max_ms": shot_duration_constraints["max_ms"],
                },
                "seedance_profile_id": "seedance-default-v1",
            }
        )

    ambiguity_threshold = 0.15
    ambiguity_score = _compute_ambiguity_score(scene_prompts)
    policy_violations = _detect_policy_violations(scene_prompts)
    policy_pass = len(policy_violations) == 0

    prompt_pack = {
        "schema_version": "2026-02-16",
        "prompt_pack_id": _stable_id(
            "prompt-pack",
            [summary_pack["summary_id"], summary_pack["locale"]],
        ),
        "source_summary_id": summary_pack["summary_id"],
        "candidate_id": summary_pack["candidate_id"],
        "locale": summary_pack["locale"],
        "seedance_profile_id": "seedance-default-v1",
        "rhythm_fidelity_target": "medium_high",
        "beat_windows": beat_windows,
        "shot_duration_constraints": shot_duration_constraints,
        "scene_prompts": scene_prompts,
        "quality_checks": {
            "schema_valid": True,
            "ambiguity_score": ambiguity_score,
            "ambiguity_threshold": ambiguity_threshold,
            "policy_violations": policy_violations,
            "policy_pass": policy_pass,
        },
    }

    validate_prompt_pack(prompt_pack)
    if ambiguity_score > ambiguity_threshold:
        raise ScriptGenerationError(
            code="PROMPT_PACK_AMBIGUITY_BLOCKED",
            message="prompt pack ambiguity score exceeded threshold",
        )
    if not policy_pass:
        raise ScriptGenerationError(
            code="PROMPT_PACK_POLICY_BLOCKED",
            message="prompt pack policy check failed",
        )

    return prompt_pack


def _build_script_sections(summary_pack: Dict[str, Any]) -> Dict[str, str]:
    hook_keypoint = summary_pack["keypoints"][0]["text"]
    cta_keypoint = summary_pack["keypoints"][-1]["text"]
    body_keypoints = [
        keypoint["text"] for keypoint in summary_pack["keypoints"][1:-1]
    ]
    if not body_keypoints:
        body_keypoints = [summary_pack["keypoints"][0]["text"]]

    hook = "Stop scrolling: %s" % hook_keypoint
    body = (
        "Build the body around '%s' with these transformed beats: %s"
        % (summary_pack["topic"], " | ".join(body_keypoints))
    )
    cta = "Save this flow and run your next test now: %s" % cta_keypoint

    return {
        "hook": hook,
        "body": body,
        "cta": cta,
    }


def merge_script_text(script_draft: Dict[str, Any]) -> str:
    return "%s %s %s" % (
        script_draft["hook"],
        script_draft["body"],
        script_draft["cta"],
    )


def _load_originality_threshold(locale: str) -> float:
    policy = _load_json(POLICY_PATH)
    locale_rules = policy.get("locale_rules", {})
    if locale not in locale_rules:
        raise ScriptGenerationError(
            code="POLICY_LOCALE_UNSUPPORTED",
            message="locale not found in policy: %s" % locale,
        )
    return float(locale_rules[locale]["originality_threshold"])


def _default_reference_corpus(segmented_source_analysis: Dict[str, Any]) -> List[str]:
    references = []
    for segment in segmented_source_analysis.get("segments", []):
        summary = str(segment.get("summary", "")).strip()
        if summary:
            references.append(summary)
    for fact in segmented_source_analysis.get("source_facts", []):
        fact_text = str(fact).strip()
        if fact_text:
            references.append(fact_text)
    return references


def run_script_generation_pipeline(
    trend_candidate: Dict[str, Any],
    segmented_source_analysis: Dict[str, Any],
    locale: str,
    output_dir: Path,
    reference_corpus: Optional[Sequence[str]] = None,
    originality_threshold: Optional[float] = None,
) -> Dict[str, Any]:
    if originality_threshold is None:
        originality_threshold = _load_originality_threshold(locale)

    summary_pack = build_summary_pack(
        trend_candidate=trend_candidate,
        segmented_source_analysis=segmented_source_analysis,
        locale=locale,
    )
    prompt_pack = build_prompt_pack(summary_pack)

    summary_path = _write_json(output_dir / "summary_pack.json", summary_pack)
    prompt_path = _write_json(output_dir / "prompt_pack.json", prompt_pack)

    sections = _build_script_sections(summary_pack)
    draft_id = _stable_id("draft", [summary_pack["candidate_id"], locale, summary_pack["topic"]])

    if reference_corpus is None:
        reference_corpus = _default_reference_corpus(segmented_source_analysis)

    script_text = "%s %s %s" % (sections["hook"], sections["body"], sections["cta"])
    similarity_score = compute_similarity_score(script_text, reference_corpus)
    originality_record = persist_originality_score(
        output_dir=output_dir / "originality",
        draft_id=draft_id,
        candidate_id=summary_pack["candidate_id"],
        locale=locale,
        similarity_score=similarity_score,
        originality_threshold=originality_threshold,
        reference_count=len(reference_corpus),
    )

    result_code = (
        "BLOCKED_ORIGINALITY"
        if similarity_score >= originality_threshold
        else "PASS"
    )
    script_draft = {
        "draft_id": draft_id,
        "candidate_id": summary_pack["candidate_id"],
        "locale": locale,
        "hook": sections["hook"],
        "body": sections["body"],
        "cta": sections["cta"],
        "originality_threshold": originality_threshold,
        "similarity_score": similarity_score,
        "similarity_trace_id": originality_record["similarity_trace_id"],
        "result_code": result_code,
    }

    validate_contract(entity_name="script_draft", payload=script_draft)
    script_draft_path = _write_json(output_dir / "script_draft.json", script_draft)

    response = {
        "status": "ready_for_review" if result_code == "PASS" else "rejected_originality",
        "result_code": result_code,
        "approval_queue_state": "queued" if result_code == "PASS" else "not_enqueued",
        "script_draft": script_draft,
        "summary_pack_path": str(summary_path),
        "prompt_pack_path": str(prompt_path),
        "script_draft_path": str(script_draft_path),
        "originality_record_path": originality_record["path"],
    }
    if result_code != "PASS":
        response["rejection"] = {
            "state": "rejected_originality",
            "code": "BLOCKED_ORIGINALITY",
        }

    return response


def validate_pack_schemas(summary_pack: Dict[str, Any], prompt_pack: Dict[str, Any]) -> None:
    try:
        validate_summary_pack(summary_pack)
        validate_prompt_pack(prompt_pack)
    except PackValidationError:
        raise
