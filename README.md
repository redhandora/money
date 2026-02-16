# money

Phase-1 trend-driven content monetization pipeline.

## Overview

`money` is an internal Python workspace for generating and publishing original
short-video content through a gated workflow:

1. ingest trend signals
2. generate scripts and prompt packs
3. generate scenes
4. localize and apply policy checks
5. require human approval
6. publish to target platforms
7. aggregate weekly revenue KPIs

The repository favors deterministic outputs, explicit reason/result codes, and
artifact-based evidence for validation scenarios.

## Project Layout

```text
money/
|- src/money/            # core domain logic
|- tests/                # pytest suite (flat, domain-mapped)
|- docs/policy/          # locale policy contract JSON
|- .github/workflows/    # CI workflow
|- .sisyphus/            # planning/research/evidence workspace
`- build/                # generated artifacts and mirrored outputs
```

## Requirements

- Python 3.11 for CI/runtime checks
- package metadata remains compatible with Python >=3.6 settings in tooling

## Setup

```bash
python -m pip install --upgrade pip
python -m pip install ".[dev]"
```

## Development Commands

```bash
ruff check .
mypy .
pytest -q
```

CI runs the same quality gate order:

1. `ruff check .`
2. `mypy .`
3. `pytest -q`

## Key Modules

- `src/money/orchestration/service.py`: workflow state machine, retries, budget
  gates, terminal states
- `src/money/orchestration/validate_task9.py`: integrated end-to-end validation
  matrix and release gate checks
- `src/money/script_generation/pipeline.py`: summary/prompt pack generation and
  originality/policy gate logic
- `src/money/review/api.py`: WSGI review API and embedded queue UI
- `src/money/metrics/service.py`: weekly revenue KPI aggregation

## How The Project Works

### 1) End-to-end state machine

The runtime flow is coordinated by `WorkflowOrchestrationService` in
`src/money/orchestration/service.py`.

Nominal stage order:

1. `trend_ingestion`
2. `script_generation`
3. `scene_generation`
4. `localization`
5. `review`
6. `publish`

Expected happy-path state trace:

`created -> trend_ingested -> script_generated -> scenes_generated -> localized -> approved -> published`

If any gate fails, orchestration returns a terminal blocked/failed state with
machine-readable `result_code` and `reason_code`.

### 2) Stage responsibilities

- `ingestion` (`src/money/ingestion/trend_ingestion.py`)
  - de-duplicates by `(source_platform, external_id)`
  - computes monetization score from weighted signals
  - blocks source-media reuse metadata (`SOURCE_MEDIA_REUSE_FORBIDDEN`)

- `script_generation` (`src/money/script_generation/pipeline.py`)
  - builds `summary_pack` from segmented analysis
  - builds `prompt_pack` with beat windows and scene prompts
  - generates `script_draft` and checks originality threshold by locale policy

- `scene_generation` (`src/money/scene_generation/service.py`)
  - validates prompt pack and creates scene manifests/assets metadata

- `localization` (`src/money/localization/pipeline.py`)
  - transcreation + voiceover preparation
  - applies locale policy gate from `docs/policy/locale_compliance_policy.json`

- `review` (`src/money/review/service.py`, `src/money/review/api.py`)
  - enforces human-approval gate and queue semantics

- `publishing` (`src/money/publishing/service.py`)
  - validates publish payloads and adapter behavior
  - maintains idempotent receipt behavior

- `metrics` (`src/money/metrics/service.py`)
  - computes trailing-window KPI summaries from publish/revenue events

### 3) What goes in / what comes out

Typical inputs:

- trend candidate payloads (`candidate_id`, source info, topic, signal)
- segmented analysis (`segments`, `source_facts`)
- locale and policy rules

Typical outputs:

- `summary_pack.json`
- `prompt_pack.json`
- `script_draft.json`
- originality records and evidence artifacts under `build/` and `.sisyphus/evidence/`

### 4) Gates and hard stops

Pipeline is intentionally gate-driven:

- policy block -> cannot proceed to publish
- review not approved -> publish blocked
- budget cap exceeded -> workflow halted
- retry ceiling reached -> terminal failure with retry trace
- originality threshold exceeded -> draft rejected

These are verified by test suites and scenario validators (especially task7/task9
validation scripts).

### 5) How to run it in practice

Run quality checks first:

```bash
ruff check .
mypy .
pytest -q
```

Run integrated orchestration validation matrix:

```bash
PYTHONPATH=src python src/money/orchestration/validate_task9.py all
```

Run script-generation scenario validation:

```bash
PYTHONPATH=src python src/money/script_generation/validate_task3.py all
```

Run localization scenario validation:

```bash
PYTHONPATH=src python src/money/localization/pipeline.py all
```

### 6) Where to inspect behavior quickly

- Stage transition logic: `src/money/orchestration/service.py`
- End-to-end scenario matrix: `src/money/orchestration/validate_task9.py`
- Prompt generation behavior: `src/money/script_generation/pipeline.py`
- Locale compliance contract: `docs/policy/locale_compliance_policy.json`
- Human-review API: `src/money/review/api.py`

## Conventions

- Source-of-truth code lives in `src/`; tests live in `tests/`
- Validator scripts use `validate_task*.py` naming and CLI-style `main()` entry
- Structured machine-readable codes (`result_code`, `reason_code`, `error_code`)
  are part of the contract
- `build/lib/` is generated mirror output and must not be treated as editable
  source

## Notes

- `ast-grep` may be unavailable in constrained environments
- Python LSP (`basedpyright`) is optional and may not be installed by default
