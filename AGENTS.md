# PROJECT KNOWLEDGE BASE

**Generated:** 2026-02-16T10:13:21Z
**Commit:** UNBORN (no `HEAD` commit yet)
**Branch:** master

## OVERVIEW
Internal Python workspace for phase-1 trend-driven monetization pipeline.
Core stack: setuptools `src/` layout, pytest, mypy, ruff, GitHub Actions.

## STRUCTURE
```text
money/
|- src/money/            # main business logic by domain module
|- tests/                # flat pytest suite (domain-mapped names)
|- docs/policy/          # locale policy contract JSON
|- .github/workflows/    # CI gates
|- .sisyphus/            # planning/research/evidence workspace
`- build/                # generated artifacts and package mirror
```

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Package config | `pyproject.toml` | canonical tool + packaging config |
| CI contract | `.github/workflows/python-ci.yml` | install + lint + type + test order |
| Workflow state machine | `src/money/orchestration/service.py` | stage order, retries, budget gates |
| End-to-end scenario matrix | `src/money/orchestration/validate_task9.py` | integrated gate coverage |
| Script and prompt packs | `src/money/script_generation/pipeline.py` | summary/prompt/originality gates |
| Review HTTP interface | `src/money/review/api.py` | WSGI app + embedded review UI |
| Locale policy data | `docs/policy/locale_compliance_policy.json` | blocked categories, thresholds |
| Tests | `tests/test_*.py` | flat layout, one file per domain area |

## CODE MAP
| Symbol | Type | Location | Role |
|---|---|---|---|
| `WorkflowOrchestrationService` | class | `src/money/orchestration/service.py` | stage execution, retry/budget governance |
| `run_task9_validation` | function | `src/money/orchestration/validate_task9.py` | full matrix + release gate checks |
| `run_script_generation_pipeline` | function | `src/money/script_generation/pipeline.py` | build script/summary/prompt outputs |
| `ReviewApiApp` | class | `src/money/review/api.py` | queue HTTP handling + JSON responses |
| `TrendIngestionService` | class | `src/money/ingestion/trend_ingestion.py` | trend candidate ingestion and ranking |
| `WeeklyRevenueKpiService` | class | `src/money/metrics/service.py` | trailing-window KPI aggregation |

## CONVENTIONS
- Source of truth code in `src/`; tests in `tests/` only (`pyproject.toml` `testpaths`).
- CLI-style validators follow `validate_task*.py` naming with `main()` + `if __name__ == "__main__":`.
- Runtime policy and threshold behavior often encoded as explicit `*_code` strings; keep stable.
- CI enforces sequence: `ruff check .` -> `mypy .` -> `pytest -q`.
- Tooling baseline is old/pinned (py36-era targets) while CI runs Python 3.11; avoid accidental modern-only syntax.

## ANTI-PATTERNS (THIS PROJECT)
- Do not treat `build/lib/` as editable source; it mirrors `src/money/`.
- Do not put operational guidance under `.sisyphus/evidence/` or `build/task*`; those are generated outputs.
- Do not merge publish and monetize gates into one implicit decision.
- Do not bypass review approval before publish paths.
- Do not ingest or reuse source media blobs/URLs in trend ingestion payload metadata.

## UNIQUE STYLES
- Functional domain partitioning: `contracts`, `ingestion`, `script_generation`, `scene_generation`, `localization`, `review`, `publishing`, `orchestration`, `metrics`.
- Heavy deterministic evidence production under `.sisyphus/evidence` from validator scripts.
- Flat test tree mirrors domain names, not source directory nesting.

## COMMANDS
```bash
python -m pip install --upgrade pip
python -m pip install ".[dev]"
ruff check .
mypy .
pytest -q
```

## NOTES
- `ast-grep` unavailable in this environment (GLIBC mismatch); rely on `grep` + `read`.
- Python LSP unavailable (`basedpyright` missing); symbol maps here are grep-derived.
- Repository currently has no valid `HEAD` commit; avoid commit-hash-dependent automation.
