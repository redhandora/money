# ORCHESTRATION KNOWLEDGE BASE

## OVERVIEW
This directory owns stage sequencing, retry/backoff, cost caps, and integrated task-9 validation.

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Stage machine | `service.py` | `WORKFLOW_STAGE_ORDER`, state transitions, terminal responses |
| Retry and cost governance | `service.py` | retry ceiling, backoff trace, budget halt events |
| End-to-end matrix | `validate_task9.py` | route matrix, edge cases, release gate payloads |
| Task-7 focused checks | `validate_task7.py` | bounded retry and cost breaker scenario outputs |

## CONVENTIONS
- Preserve stage order semantics; downstream tests assert exact `state_trace` sequence.
- Keep per-stage handlers contract-compatible (`status`, `result_code`, costs, optional reason codes).
- Any new terminal state must include deterministic response payload and tests.
- Backoff values and retry traces must remain numeric and reproducible.

## ANTI-PATTERNS
- Do not fold policy-blocked and review-blocked outcomes into one generic failure state.
- Do not silently continue after budget-cap violations.
- Do not mutate daily spend accounting outside service methods.
- Do not add non-deterministic timestamps/IDs where tests expect stable output.
