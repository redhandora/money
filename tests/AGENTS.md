# TEST SUITE KNOWLEDGE BASE

## OVERVIEW
Flat pytest suite validating domain behavior across ingestion -> generation -> localization -> review -> publish -> metrics -> orchestration.

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Orchestration semantics | `test_orchestration_workflow.py` | state trace, retry, cost cap, gate enforcement |
| E2E hardening | `test_task9_e2e_hardening.py` | release-gate matrix behavior |
| Generation pipeline | `test_script_generation_pipeline.py` | summary/prompt/originality artifact checks |
| Review gate | `test_review_queue.py` | immutable decisions and SLA expiry |
| Publisher adapters | `test_publisher_service.py` | idempotency and partial failure handling |

## CONVENTIONS
- Tests live in this directory only (`pyproject.toml` `testpaths = ["tests"]`).
- Use domain-specific assertions on `*_code` fields, not generic string matching.
- Prefer deterministic fixtures and `tmp_path` for file assertions.
- Keep test naming domain-oriented (`test_<domain>_<behavior>`).

## ANTI-PATTERNS
- Do not assume nested source-mirroring in test paths; this suite is intentionally flat.
- Do not write new persistent artifacts under repo roots unless evidence capture is intentional.
- Do not assert on unstable ordering/timestamps without normalization.
