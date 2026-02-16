
## 2026-02-16 Task 1 learnings

- Added machine-validated contract catalog at `src/money/contracts/pipeline_contracts.schema.json` with six required entities.
- Standardized explicit `result_code` and `violation_code` enums to avoid free-text policy outcomes.
- Encoded locale-aware compliance policy in `docs/policy/locale_compliance_policy.json` for EN-US, EN-SEA, and JA-JP.
- Added deterministic validation entrypoint `python -m money.contracts.validate_task1` that writes reproducible evidence files.
- Included explicit `originality_threshold` and `similarity_score` fields in `script_draft` schema and policy evaluation path.

## 2026-02-16 - Task 0 bootstrap

- Created Python bootstrap baseline with `pyproject.toml` tool config for `pytest`, `ruff`, and `mypy`.
- Added minimal package/test scaffold: `src/money/__init__.py` and `tests/test_bootstrap.py`.
- Added CI workflow at `.github/workflows/python-ci.yml` with explicit lint/type/test gates:
  - `ruff check .`
  - `mypy .`
  - `pytest -q`
- Verified local baseline checks in this environment:
  - `pytest -q`: passed (`1 passed`)
  - `mypy .`: passed (no issues found)
- Added `setup.py` for compatibility with local legacy Python packaging behavior.

## 2026-02-16 Task 3 learnings

- Implemented deterministic script generation pipeline in `src/money/script_generation/pipeline.py` that materializes `summary_pack.json`, `prompt_pack.json`, and `script_draft.json` from segmented analysis input.
- Added machine-validated pack schemas plus validator in `src/money/script_generation/schemas.py` to enforce required keys, typing, value ranges, and no additional properties.
- Added originality scoring and persistence in `src/money/script_generation/originality.py`, including explicit `BLOCKED_ORIGINALITY` handling and traceable `similarity_trace_id`.
- Added CLI evidence runner `python -m money.script_generation.validate_task3 low-originality` to generate `.sisyphus/evidence/task-3-originality-block.json` deterministically.
- Prompt pack now carries `rhythm_fidelity_target=medium_high`, explicit `beat_windows`, and `shot_duration_constraints` so downstream Seedance generation can consume scene prompts directly.

## 2026-02-16 Task 4 learnings

- Added transcreation-first localization pipeline under `src/money/localization/` with locale-explicit behavior for `EN-US`, `EN-SEA`, and `JA-JP`.
- Added deterministic post-localization policy gate in `src/money/localization/policy_gate.py` with stable block code format `BLOCKED_POLICY::<policy_code>::<reason_code>`.
- Added locale-specific simulated TTS asset generation in `src/money/localization/voiceover.py` with deterministic `asset_path`, `language_tag`, and `duration_ms` metadata.
- Added orchestration and evidence generator in `src/money/localization/pipeline.py` that writes `.sisyphus/evidence/task-4-ja-output.json` and `.sisyphus/evidence/task-4-policy-block.json`.
- Added focused tests in `tests/test_localization_pipeline.py` for JA-JP output metadata, deterministic policy blocking, and all-locale metadata coverage.

## 2026-02-16 Task 2 learnings

- Added `TrendIngestionService` in `src/money/ingestion/trend_ingestion.py` with deterministic idempotency keyed by `(source_platform, external_id)` and stable `candidate_id` derivation.
- Enforced metadata-only ingestion by rejecting source-media reuse fields (`source_media_url`, `media_blob`, etc.) with explicit `SOURCE_MEDIA_REUSE_FORBIDDEN` errors.
- Implemented explicit monetization-proxy ranking heuristic: `0.55*signal + 0.25*engagement_velocity + 0.15*advertiser_fit + 0.05*region_match`.
- Implemented analysis-only isolation in manifest generation; `analysis_only=true` candidates are blocked with `ANALYSIS_ONLY_BLOCKED_FROM_PUBLISH_MANIFEST`.
- Added source-analysis artifact fields (`beat_map_artifact`, `pacing_map_artifact`) on normalized candidates for downstream rhythm transfer steps.

## 2026-02-16 Task 2 follow-up learnings

- Added explicit rate-limit/backoff enforcement to `TrendIngestionService` via configurable `max_new_candidates` and `backoff_base_seconds`, with deterministic `RATE_LIMIT_BACKOFF_REQUIRED` behavior.
- Revalidated Task 2 acceptance using deterministic Python assertions (without pytest) and refreshed `.sisyphus/evidence/task-2-idempotent.json` with per-criterion check flags.

## 2026-02-16 Task 3A learnings

- Added deterministic Seedance-only scene generation service at `src/money/scene_generation/service.py` that consumes Task 3 `prompt_pack.json` and emits `scene_generation.json` plus per-scene asset metadata files.
- Enforced generation preflight gates with explicit block codes: `BLOCKED_PROMPT_SCHEMA_INVALID`, `BLOCKED_POLICY_NOT_PASSED`, and `BLOCKED_ENGINE_POLICY` for non-Seedance engine requests.
- Standardized scene output metadata per prompt with required assembly fields: `scene_asset_uri`, `duration_ms`, and `seedance_profile` plus prompt traceability (`prompt_id`, `beat_index`).
- Added focused tests in `tests/test_scene_generation_service.py` for pass path, schema-invalid block, policy-not-passed block, and single-engine policy enforcement.
- Added deterministic evidence runner `python -m money.scene_generation.validate_task3a all` to produce `.sisyphus/evidence/task-3a-seedance-output.json` and `.sisyphus/evidence/task-3a-seedance-block.json`.

## 2026-02-16 Task 5 learnings

- Extended review queue coverage with `tests/test_review_queue.py` to validate required `locale/policy/originality/cost` queue payload fields, immutable decisions, and SLA expiry publish blocking.
- Updated `src/money/review/api.py` review UI to include explicit reject-reason selection (`REJECTED_POLICY` or `REJECTED_ORIGINALITY`) while keeping approve/reject actions minimal.
- Expanded deterministic validator `python -m money.review.validate_task5 all` to emit scenario evidence for queue payload checks, decision immutability, SLA expiry transition, and pending publish gate enforcement.

## 2026-02-16 Task 6 learnings

- Added publisher orchestration module at `src/money/publishing/service.py` with reusable request builders (`build_publish_request`, `build_platform_publish_request`) and explicit adapter interface coverage for YouTube Shorts and TikTok.
- Enforced approved-state publish gating by combining payload-level `review_status=approved` checks with optional `ReviewQueueService.check_publish_eligibility` integration that preserves `HUMAN_APPROVAL_REQUIRED` semantics.
- Added per-platform schedule and quota controls (`window_start_hour_utc`, `window_end_hour_utc`, `max_publishes_per_hour`) with explicit block/error codes instead of silent fallback behavior.
- Standardized per-platform publish receipts validated against Task 1 contracts (`publish_receipt`) with deterministic `receipt_id`, `platform_post_id`, and retryable/terminal status persistence.
- Added deterministic evidence runner `PYTHONPATH=src python -m money.publishing.validate_task6 all` to emit `.sisyphus/evidence/task-6-idempotency.json` and `.sisyphus/evidence/task-6-partial-failure.json`.

## 2026-02-16 Task 7 learnings

- Added Task 7 orchestration module at `src/money/orchestration/service.py` with fixed state progression (`trend_ingested -> script_generated -> scenes_generated -> localized -> approved -> published`) and explicit terminal states for `halted_cost_cap`, `failed_retry_exhausted`, policy blocks, and review-gate blocks.
- Enforced cost governance with deterministic budget halt events and reason codes (`PER_VIDEO_BUDGET_EXCEEDED`, `DAILY_SPEND_CAP_EXCEEDED`, `DAILY_SPEND_CAP_REACHED`) while preserving cumulative workflow/daily spend traces.
- Implemented bounded retry governance with default `max_retries_per_stage=3`, exponential backoff metadata (`2,4,8` base-2 sequence), and terminal `FAILED_RETRY_EXHAUSTED` behavior.
- Added deterministic Seedance fallback sequencing within single-engine policy (`seedance-quality-v1 -> seedance-balanced-v1 -> seedance-speed-v1`) with profile trace capture and deterministic stop on success or retry ceiling.
- Added focused Task 7 coverage in `tests/test_orchestration_workflow.py` and deterministic evidence CLI `PYTHONPATH=src python -m money.orchestration.validate_task7 all` producing `task-7-cost-breaker.json` and `task-7-retry-ceiling.json`.

## 2026-02-16 Task 8 learnings

- Added weekly KPI aggregation service at `src/money/metrics/service.py` with explicit schema fields (`gross_revenue`, `net_revenue`, `rpm_proxy`, `approval_rate`, `publish_success_rate`) and fixed trailing 7-day window enforcement.
- Added metrics API surface at `src/money/metrics/api.py` with `GET /metrics/revenue-weekly` compatible query handling (`locale`, optional `platform`, optional `as_of_date`) and deterministic `window_days/window_start_date/window_end_date` metadata.
- Enforced locale/platform validation using shared pipeline constraints (`SUPPORTED_LOCALES`, `SUPPORTED_PUBLISH_PLATFORMS`) so dashboard and optimization loops cannot query unsupported filters.
- Added focused Task 8 tests in `tests/test_metrics_weekly_kpi.py` for numeric KPI typing, exact trailing-7-day filtering, locale/platform filter enforcement, and validation errors.
- Added deterministic evidence runner `PYTHONPATH=src python -m money.metrics.validate_task8` to produce `.sisyphus/evidence/task-8-kpi-schema.json`.

## 2026-02-16 Task 9 learnings

- Added deterministic Task 9 validator at `src/money/orchestration/validate_task9.py` that executes a full E2E matrix across `mock` and `live-safe` modes for all locale/platform routes (`EN-US`, `EN-SEA`, `JA-JP` x `youtube`, `tiktok`).
- Implemented end-to-end happy path coverage for each route: trend candidate -> script generation -> Seedance scene generation -> localization -> human review approval -> publish receipt.
- Added explicit hardening scenarios for duplicate trend idempotency, stale approval blocking, partial publish success, bounded provider outage retries, deterministic DST UTC slotting, and cost/policy negative gates.
- Added machine-readable QC artifacts for A-mode reuse guard (`exact_source_frame_matches=0`), subtitle/audio/AV/style thresholds, Fidelity Gate, and Transformation Gate under `.sisyphus/evidence/task-9-*.json`.
- Added release gate artifact `task-9-release-gate.json` that blocks release unless matrix, edge-case, QC, fidelity, transformation, and human-approval checks all pass.
- Added focused regression coverage in `tests/test_task9_e2e_hardening.py` validating full matrix completion and release-critical gate pass conditions.
