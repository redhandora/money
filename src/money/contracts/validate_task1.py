import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT_DIR / "src" / "money" / "contracts" / "pipeline_contracts.schema.json"
POLICY_PATH = ROOT_DIR / "docs" / "policy" / "locale_compliance_policy.json"
EVIDENCE_DIR = ROOT_DIR / ".sisyphus" / "evidence"


class ContractValidationError(Exception):
    def __init__(self, code: str, field: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.field = field


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def validate_contract(entity_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    schema = _load_json(SCHEMA_PATH)
    entity_schema = schema["$defs"][entity_name]

    required = entity_schema.get("required", [])
    for field in required:
        if field not in payload:
            raise ContractValidationError(
                code="CONTRACT_REQUIRED_FIELD",
                field=field,
                message=f"missing required field: {field}",
            )

    if entity_schema.get("additionalProperties") is False:
        allowed_fields = set(entity_schema.get("properties", {}).keys())
        extra_fields = sorted(set(payload.keys()) - allowed_fields)
        if extra_fields:
            raise ContractValidationError(
                code="CONTRACT_ADDITIONAL_PROPERTY",
                field=extra_fields[0],
                message=f"additional property is not allowed: {extra_fields[0]}",
            )

    for field, field_schema in entity_schema.get("properties", {}).items():
        if field not in payload:
            continue
        value = payload[field]

        if "$ref" in field_schema:
            ref_name = field_schema["$ref"].split("/")[-1]
            ref_schema = schema["$defs"][ref_name]
            if "enum" in ref_schema and value not in ref_schema["enum"]:
                raise ContractValidationError(
                    code="CONTRACT_ENUM_VIOLATION",
                    field=field,
                    message=f"enum violation at {field}: {value}",
                )
            continue

        field_type = field_schema.get("type")
        if field_type and not _check_type(value, field_type):
            raise ContractValidationError(
                code="CONTRACT_TYPE_MISMATCH",
                field=field,
                message=f"type mismatch at {field}: expected {field_type}",
            )

        if "enum" in field_schema and value not in field_schema["enum"]:
            raise ContractValidationError(
                code="CONTRACT_ENUM_VIOLATION",
                field=field,
                message=f"enum violation at {field}: {value}",
            )

        if field_type in {"number", "integer"}:
            minimum = field_schema.get("minimum")
            maximum = field_schema.get("maximum")
            if minimum is not None and value < minimum:
                raise ContractValidationError(
                    code="CONTRACT_TYPE_MISMATCH",
                    field=field,
                    message=f"value below minimum at {field}: {value}",
                )
            if maximum is not None and value > maximum:
                raise ContractValidationError(
                    code="CONTRACT_TYPE_MISMATCH",
                    field=field,
                    message=f"value above maximum at {field}: {value}",
                )

        if field_type == "array" and "items" in field_schema:
            item_type = field_schema["items"].get("type")
            if item_type:
                for idx, item in enumerate(value):
                    if not _check_type(item, item_type):
                        raise ContractValidationError(
                            code="CONTRACT_TYPE_MISMATCH",
                            field=f"{field}[{idx}]",
                            message=f"array item type mismatch at {field}[{idx}]",
                        )

    return {
        "status": "accepted",
        "result_code": "PASS",
        "entity": entity_name,
    }


def evaluate_policy(locale: str, categories: List[str], similarity_score: float) -> Dict[str, Any]:
    policy = _load_json(POLICY_PATH)
    locale_rules = policy["locale_rules"]

    if locale not in locale_rules:
        return {
            "status": "blocked",
            "result_code": "BLOCK",
            "policy_code": "POLICY_LOCALE_UNSUPPORTED",
            "reason_code": "POLICY_LOCALE_UNSUPPORTED",
        }

    rules = locale_rules[locale]
    blocked_categories = set(rules["blocked_categories"])
    category_reason_code = rules["category_reason_code"]

    for category in categories:
        if category in blocked_categories:
            return {
                "status": "blocked",
                "result_code": "BLOCK",
                "policy_code": "POLICY_BLOCKED_CATEGORY",
                "reason_code": category_reason_code[category],
                "blocked_category": category,
            }

    threshold = float(rules["originality_threshold"])
    if similarity_score >= threshold:
        return {
            "status": "blocked",
            "result_code": "BLOCK",
            "policy_code": "POLICY_SIMILARITY_THRESHOLD_EXCEEDED",
            "reason_code": "RISKY_FINANCIAL_PROMISE",
            "similarity_score": similarity_score,
            "originality_threshold": threshold,
        }

    return {
        "status": "allowed",
        "result_code": "ALLOW",
        "policy_code": "PASS",
        "reason_code": "PASS",
        "similarity_score": similarity_score,
        "originality_threshold": threshold,
    }


def run_contract_invalid_scenario() -> Dict[str, Any]:
    invalid_payload = {
        "candidate_id": "trend-001",
        "source_platform": "youtube",
        "external_id": "abc123",
        "signal_score": 0.66,
        "captured_at": "2026-02-16T00:00:00Z",
    }

    try:
        validate_contract("trend_candidate", invalid_payload)
    except ContractValidationError as exc:
        return {
            "scenario": "contract_invalid",
            "entity": "trend_candidate",
            "status": "rejected",
            "result_code": "BLOCKED_CONTRACT",
            "error_code": exc.code,
            "error_field": exc.field,
        }

    return {
        "scenario": "contract_invalid",
        "entity": "trend_candidate",
        "status": "accepted_unexpectedly",
        "result_code": "FAIL",
        "error_code": "NONE",
    }


def run_policy_block_scenario() -> Dict[str, Any]:
    return {
        "scenario": "policy_block_ja_jp",
        "locale": "JA-JP",
        "input": {
            "categories": ["deceptive_before_after"],
            "similarity_score": 0.72,
        },
        "result": evaluate_policy(
            locale="JA-JP",
            categories=["deceptive_before_after"],
            similarity_score=0.72,
        ),
    }


def _write_evidence(file_name: str, payload: Dict[str, Any]) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    output = EVIDENCE_DIR / file_name
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "scenario",
        choices=["contract-invalid", "policy-block", "all"],
    )
    args = parser.parse_args()

    if args.scenario in {"contract-invalid", "all"}:
        contract_result = run_contract_invalid_scenario()
        path = _write_evidence("task-1-contract-invalid.json", contract_result)
        print(path)

    if args.scenario in {"policy-block", "all"}:
        policy_result = run_policy_block_scenario()
        path = _write_evidence("task-1-policy-block.json", policy_result)
        print(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
