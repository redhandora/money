# PACKAGE KNOWLEDGE BASE

## OVERVIEW
`src/money` is the authoritative business-logic package for phase-1 pipeline behavior.

## STRUCTURE
```text
src/money/
|- contracts/         # schema + policy validation contracts
|- ingestion/         # trend candidate intake + ranking
|- script_generation/ # summary/prompt/script/originality pipeline
|- scene_generation/  # Seedance scene metadata generation
|- localization/      # transcreation, voiceover, policy gate
|- review/            # queue service + WSGI review API/UI
|- publishing/        # adapters, idempotency, publish receipts
|- orchestration/     # state machine, retries, budgets, task9 matrix
`- metrics/           # revenue KPI service + API
```

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Cross-stage flow | `orchestration/service.py` | canonical stage order and terminal states |
| Full scenario coverage | `orchestration/validate_task9.py` | matrix + edge-case + release-gate output |
| Prompt/schema behavior | `script_generation/pipeline.py` + `script_generation/schemas.py` | validation and threshold gates |
| Policy contract | `../docs/policy/locale_compliance_policy.json` | locale blocks + originality thresholds |
| Human gate behavior | `review/service.py` + `review/api.py` | approval lifecycle and API responses |

## CONVENTIONS
- Public error paths use explicit machine-readable codes (`result_code`, `reason_code`, `error_code`).
- Validator scripts are executable CLIs (`validate_task*.py`) that emit evidence files.
- Prefer deterministic IDs/hashes and sorted JSON output for reproducibility.
- Keep stage output schemas explicit; downstream modules assume stable keys.

## ANTI-PATTERNS
- Never import from `build/lib/money`; always import from `src/money` package.
- Do not co-locate new generated artifacts inside package directories.
- Do not introduce hidden gate bypass flags across review/publish/policy boundaries.
- Do not replace structured error codes with free-text-only signaling.
