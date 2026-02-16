
## 2026-02-16 Task 1 issues

- `lsp_diagnostics` cannot run to completion because `basedpyright-langserver` is not installed in this environment.
- `pytest` command is unavailable in this environment (`command not found`), so pytest-based verification could not be executed.

## 2026-02-16 - Task 0 blockers

- Local interpreter is Python 3.6.8 only; modern `ruff` installation is blocked due build dependency constraints (`maturin>=0.13` unavailable for this runtime).
- Python LSP diagnostics are blocked in this environment because `basedpyright-langserver` is not installed.
- CI is configured on Python 3.11 to enforce `ruff`, `mypy`, and `pytest`; local inability to run `ruff` is environment-specific.

## 2026-02-16 Task 3 issues

- `lsp_diagnostics` remains unavailable for Python files because `basedpyright-langserver` is not installed (`Command not found`).
- `python -m pytest -q` remains unavailable in this environment (`No module named pytest`), so verification used deterministic CLI scenario runs plus `python -m compileall` and `python setup.py build`.

## 2026-02-16 Task 4 issues

- `lsp_diagnostics` remains blocked because `basedpyright-langserver` is not installed, so static diagnostics could not be executed for changed Python files.
- `python -m pytest -q tests/test_localization_pipeline.py` failed because `pytest` is not installed in this environment.
- `python -m mypy src/money/localization tests/test_localization_pipeline.py` failed because `mypy` is not installed in this environment.
- Validation fallback used: deterministic scenario assertions via `python -c`, evidence generation via `python -m money.localization.pipeline all`, and compile/build checks via `python -m compileall src tests` and `python setup.py build`.

## 2026-02-16 Task 2 issues

- `pytest` is still unavailable in this environment (`command not found` and `python -m pytest` reports module missing), so ingestion tests could not be executed locally.
- `lsp_diagnostics` is still unavailable for Python files due missing `basedpyright-langserver`.

## 2026-02-16 Task 2 follow-up issues

- `pytest` and `python -m pytest` remain unavailable; verification used deterministic `PYTHONPATH=src python -c` assertions plus `python -m py_compile`.
- Python LSP diagnostics remain blocked because `basedpyright-langserver` is not installed.

## 2026-02-16 Task 3A issues

- `lsp_diagnostics` could not run on changed Python files because `basedpyright-langserver` is not installed in this environment.
- `pytest` is not installed, so focused test module `tests/test_scene_generation_service.py` could not be executed via `python -m pytest` locally.
- Verification fallback used deterministic evidence run (`PYTHONPATH=src python -m money.scene_generation.validate_task3a all`) and compile/build checks (`python -m compileall src tests`, `python setup.py build`).

## 2026-02-16 Task 5 issues

- `lsp_diagnostics` remains blocked for Python files because `basedpyright-langserver` is not installed in this environment.
- Playwright skill is not usable in this environment (`playwright` MCP reports no discovered capabilities), so browser approve-flow assertions could not be executed.
- Deterministic API fallback was used for review-flow verification via `PYTHONPATH=src python -m money.review.validate_task5 all` plus compile checks.

## 2026-02-16 Task 6 issues

- `lsp_diagnostics` remains unavailable for changed Python files because `basedpyright-langserver` is not installed in this environment.
- `pytest` execution remains unavailable in this runtime, so verification relied on deterministic Task 6 evidence generation plus `python -m compileall src tests`.

## 2026-02-16 Task 7 issues

- `lsp_diagnostics` remains blocked for Task 7 Python changes (`src/money/orchestration/*.py`, `tests/test_orchestration_workflow.py`) because `basedpyright-langserver` is not installed in this environment.
- `python -m pytest -q tests/test_orchestration_workflow.py` could not run because `pytest` is not installed (`No module named pytest`); verification used deterministic Task 7 evidence runner plus `python -m compileall src tests`.

## 2026-02-16 Task 8 issues

- `lsp_diagnostics` remains unavailable for Task 8 Python changes (`src/money/metrics/*.py`, `tests/test_metrics_weekly_kpi.py`) because `basedpyright-langserver` is not installed in this environment.
- `python -m pytest -q tests/test_metrics_weekly_kpi.py` could not run because `pytest` is not installed in this runtime; verification used deterministic Task 8 evidence output plus `python -m compileall src tests`.

## 2026-02-16 Task 9 issues

- Playwright browser automation could not be executed in this runtime because the Playwright MCP reports no discovered capabilities; deterministic API-level E2E validation was used and recorded in `.sisyphus/evidence/task-9-playwright-constraint.json`.
- `lsp_diagnostics` remains unavailable for Task 9 Python changes (`src/money/orchestration/validate_task9.py`, `tests/test_task9_e2e_hardening.py`) because `basedpyright-langserver` is not installed in this environment.
- `pytest` remains unavailable in this runtime, so Task 9 verification relied on deterministic validator execution (`PYTHONPATH=src python -m money.orchestration.validate_task9 all`) plus `PYTHONPATH=src python -m compileall src tests`.
