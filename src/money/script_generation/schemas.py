from typing import Any, Dict


SUMMARY_PACK_SCHEMA = {
    "type": "object",
    "required": [
        "schema_version",
        "summary_id",
        "source_analysis_id",
        "candidate_id",
        "locale",
        "topic",
        "analysis_only",
        "factual_quality",
        "keypoints",
        "beat_map",
        "pacing_map",
    ],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "string", "minLength": 1},
        "summary_id": {"type": "string", "minLength": 1},
        "source_analysis_id": {"type": "string", "minLength": 1},
        "candidate_id": {"type": "string", "minLength": 1},
        "locale": {"type": "string", "enum": ["EN-US", "EN-SEA", "JA-JP"]},
        "topic": {"type": "string", "minLength": 3},
        "analysis_only": {"type": "boolean", "enum": [True]},
        "factual_quality": {
            "type": "object",
            "required": [
                "factual_precision",
                "hallucination_rate",
                "precision_threshold",
                "hallucination_threshold",
                "passes",
            ],
            "additionalProperties": False,
            "properties": {
                "factual_precision": {"type": "number", "minimum": 0, "maximum": 1},
                "hallucination_rate": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                },
                "precision_threshold": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                },
                "hallucination_threshold": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                },
                "passes": {"type": "boolean"},
            },
        },
        "keypoints": {
            "type": "array",
            "minItems": 3,
            "items": {
                "type": "object",
                "required": ["order", "role", "text", "source_segment_id"],
                "additionalProperties": False,
                "properties": {
                    "order": {"type": "integer", "minimum": 1},
                    "role": {"type": "string", "enum": ["hook", "body", "cta"]},
                    "text": {"type": "string", "minLength": 5},
                    "source_segment_id": {"type": "string", "minLength": 1},
                },
            },
        },
        "beat_map": {
            "type": "array",
            "minItems": 3,
            "items": {
                "type": "object",
                "required": [
                    "beat_index",
                    "segment_id",
                    "start_ms",
                    "end_ms",
                    "duration_ms",
                ],
                "additionalProperties": False,
                "properties": {
                    "beat_index": {"type": "integer", "minimum": 1},
                    "segment_id": {"type": "string", "minLength": 1},
                    "start_ms": {"type": "integer", "minimum": 0},
                    "end_ms": {"type": "integer", "minimum": 1},
                    "duration_ms": {"type": "integer", "minimum": 1},
                },
            },
        },
        "pacing_map": {
            "type": "object",
            "required": ["total_duration_ms", "max_duration_jump_ratio"],
            "additionalProperties": False,
            "properties": {
                "total_duration_ms": {"type": "integer", "minimum": 1},
                "max_duration_jump_ratio": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 10,
                },
            },
        },
    },
}


PROMPT_PACK_SCHEMA = {
    "type": "object",
    "required": [
        "schema_version",
        "prompt_pack_id",
        "source_summary_id",
        "candidate_id",
        "locale",
        "seedance_profile_id",
        "rhythm_fidelity_target",
        "beat_windows",
        "shot_duration_constraints",
        "scene_prompts",
        "quality_checks",
    ],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "string", "minLength": 1},
        "prompt_pack_id": {"type": "string", "minLength": 1},
        "source_summary_id": {"type": "string", "minLength": 1},
        "candidate_id": {"type": "string", "minLength": 1},
        "locale": {"type": "string", "enum": ["EN-US", "EN-SEA", "JA-JP"]},
        "seedance_profile_id": {"type": "string", "minLength": 1},
        "rhythm_fidelity_target": {"type": "string", "enum": ["medium_high"]},
        "beat_windows": {
            "type": "array",
            "minItems": 3,
            "items": {
                "type": "object",
                "required": ["beat_index", "start_ms", "end_ms"],
                "additionalProperties": False,
                "properties": {
                    "beat_index": {"type": "integer", "minimum": 1},
                    "start_ms": {"type": "integer", "minimum": 0},
                    "end_ms": {"type": "integer", "minimum": 1},
                },
            },
        },
        "shot_duration_constraints": {
            "type": "object",
            "required": ["min_ms", "max_ms", "max_jump_ratio", "max_whiplash_per_8s"],
            "additionalProperties": False,
            "properties": {
                "min_ms": {"type": "integer", "minimum": 1},
                "max_ms": {"type": "integer", "minimum": 1},
                "max_jump_ratio": {"type": "number", "minimum": 1, "maximum": 10},
                "max_whiplash_per_8s": {"type": "integer", "minimum": 0, "maximum": 8},
            },
        },
        "scene_prompts": {
            "type": "array",
            "minItems": 3,
            "items": {
                "type": "object",
                "required": [
                    "prompt_id",
                    "beat_index",
                    "script_role",
                    "prompt_text",
                    "beat_window_ms",
                    "target_duration_ms",
                    "shot_duration_ms",
                    "seedance_profile_id",
                ],
                "additionalProperties": False,
                "properties": {
                    "prompt_id": {"type": "string", "minLength": 1},
                    "beat_index": {"type": "integer", "minimum": 1},
                    "script_role": {
                        "type": "string",
                        "enum": ["hook", "body", "cta"],
                    },
                    "prompt_text": {"type": "string", "minLength": 20},
                    "beat_window_ms": {
                        "type": "object",
                        "required": ["start_ms", "end_ms"],
                        "additionalProperties": False,
                        "properties": {
                            "start_ms": {"type": "integer", "minimum": 0},
                            "end_ms": {"type": "integer", "minimum": 1},
                        },
                    },
                    "target_duration_ms": {"type": "integer", "minimum": 1},
                    "shot_duration_ms": {
                        "type": "object",
                        "required": ["min_ms", "max_ms"],
                        "additionalProperties": False,
                        "properties": {
                            "min_ms": {"type": "integer", "minimum": 1},
                            "max_ms": {"type": "integer", "minimum": 1},
                        },
                    },
                    "seedance_profile_id": {"type": "string", "minLength": 1},
                },
            },
        },
        "quality_checks": {
            "type": "object",
            "required": [
                "schema_valid",
                "ambiguity_score",
                "ambiguity_threshold",
                "policy_violations",
                "policy_pass",
            ],
            "additionalProperties": False,
            "properties": {
                "schema_valid": {"type": "boolean"},
                "ambiguity_score": {"type": "number", "minimum": 0, "maximum": 1},
                "ambiguity_threshold": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                },
                "policy_violations": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "policy_pass": {"type": "boolean"},
            },
        },
    },
}


class PackValidationError(Exception):
    def __init__(self, code: str, field: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.field = field


def _check_type(value: Any, schema_type: str) -> bool:
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "object":
        return isinstance(value, dict)
    return False


def _validate_schema_node(value: Any, schema: Dict[str, Any], field_path: str) -> None:
    schema_type = schema.get("type")
    if schema_type is not None and not _check_type(value, schema_type):
        raise PackValidationError(
            code="PACK_TYPE_MISMATCH",
            field=field_path,
            message="type mismatch at %s" % field_path,
        )

    enum_values = schema.get("enum")
    if enum_values is not None and value not in enum_values:
        raise PackValidationError(
            code="PACK_ENUM_VIOLATION",
            field=field_path,
            message="enum violation at %s" % field_path,
        )

    if schema_type == "string":
        min_length = schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            raise PackValidationError(
                code="PACK_VALUE_RANGE",
                field=field_path,
                message="string too short at %s" % field_path,
            )

    if schema_type in {"number", "integer"}:
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and value < minimum:
            raise PackValidationError(
                code="PACK_VALUE_RANGE",
                field=field_path,
                message="value below minimum at %s" % field_path,
            )
        if maximum is not None and value > maximum:
            raise PackValidationError(
                code="PACK_VALUE_RANGE",
                field=field_path,
                message="value above maximum at %s" % field_path,
            )

    if schema_type == "array":
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            raise PackValidationError(
                code="PACK_VALUE_RANGE",
                field=field_path,
                message="array too short at %s" % field_path,
            )
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                _validate_schema_node(
                    item,
                    item_schema,
                    "%s[%d]" % (field_path, index),
                )

    if schema_type == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for required_field in required:
            if required_field not in value:
                raise PackValidationError(
                    code="PACK_REQUIRED_FIELD",
                    field="%s.%s" % (field_path, required_field),
                    message="missing required field %s.%s"
                    % (field_path, required_field),
                )

        if schema.get("additionalProperties") is False:
            extra_fields = sorted(set(value.keys()) - set(properties.keys()))
            if extra_fields:
                raise PackValidationError(
                    code="PACK_ADDITIONAL_PROPERTY",
                    field="%s.%s" % (field_path, extra_fields[0]),
                    message="additional property is not allowed at %s.%s"
                    % (field_path, extra_fields[0]),
                )

        for property_name, property_schema in properties.items():
            if property_name in value:
                _validate_schema_node(
                    value[property_name],
                    property_schema,
                    "%s.%s" % (field_path, property_name),
                )


def validate_summary_pack(payload: Dict[str, Any]) -> Dict[str, str]:
    _validate_schema_node(payload, SUMMARY_PACK_SCHEMA, "summary_pack")
    return {
        "status": "accepted",
        "result_code": "PASS",
        "entity": "summary_pack",
    }


def validate_prompt_pack(payload: Dict[str, Any]) -> Dict[str, str]:
    _validate_schema_node(payload, PROMPT_PACK_SCHEMA, "prompt_pack")
    return {
        "status": "accepted",
        "result_code": "PASS",
        "entity": "prompt_pack",
    }
