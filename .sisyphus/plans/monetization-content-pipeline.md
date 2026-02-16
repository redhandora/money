# Phase-1 Trend-Driven Content Monetization Pipeline

## TL;DR

> **Quick Summary**: Build an internal, low-cost, trend-driven original short-video pipeline that discovers trend signals, generates localized original content, enforces policy + cost guardrails, routes through human approval, and publishes to TikTok + YouTube Shorts.
>
> **Deliverables**:
> - End-to-end pipeline (discover -> script -> localize -> approve -> publish -> track)
> - Test infrastructure + TDD workflow + CI checks
> - Compliance/cost control layer and weekly revenue KPI endpoint
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: Task 0 -> Task 1 -> Task 6 -> Task 7 -> Task 8

---

## Context

### Original Request
Create a method to implement an AI-driven content system that captures trend signals from YouTube/TikTok, generates localized original videos, and auto-publishes for multi-country monetization.

### Interview Summary
**Key Discussions**:
- Source strategy: trend-driven original only (no direct source video reuse).
- Markets: EN-US, EN-SEA, JA-JP.
- Platforms: TikTok + YouTube Shorts.
- Product mode: internal operations tool (not SaaS).
- Throughput target: 3-5 videos/day total.
- Publish mode: human approval required before publish.
- Budget cap: < $300/month.
- Test strategy: setup test infra first, then TDD.

**Research Findings**:
- Repo currently has only `.sisyphus` artifacts; no executable test framework or CI test workflow.

### Metis Review
**Identified Gaps (addressed in this plan)**:
- Added explicit compliance taxonomy and locale policy gate.
- Added hard cost cap and per-job budget circuit breaker.
- Added approval SLA and stale queue handling policy.
- Added retry ceiling + idempotent publish requirements.
- Added edge-case coverage (duplicate trends, partial publish success, provider outage, DST windows).

### Defaults Applied
- Revenue KPI default: optimize for **net revenue** (7-day rolling).
- Approval SLA default: pending item expires after **24 hours**.
- Originality default: block if semantic similarity >= **0.80** to reference corpus.
- Retry default: max **3 retries** per stage with exponential backoff.
- Data retention default: logs/evidence retained for **90 days**.

---

## Work Objectives

### Core Objective
Deliver a production-oriented phase-1 internal system that can safely produce and publish localized original short videos with measurable weekly revenue progress under strict cost and compliance constraints.

### Concrete Deliverables
- Pipeline services + orchestrator + approval API/UI + publisher adapters.
- TDD test suite (unit/integration/e2e) and CI execution.
- Metrics module with weekly revenue KPIs by locale/platform.

### Definition of Done
- [x] One trend signal can flow end-to-end into `published` state only after `approved` event.
- [x] Budget guardrails halt jobs that exceed per-video or daily spend caps.
- [x] Policy gate blocks violating drafts with explicit rejection code.
- [x] Weekly KPI endpoint returns numeric revenue aggregation for EN-US/EN-SEA/JA-JP.

### Must Have
- Human approval gate is mandatory for all publish paths.
- Originality checks to reduce derivative risk before approval queue.
- Locale-aware policy/moderation step before approval and before publish.
- Cost governance: per-job budget, daily cap, retry ceilings.

### Must NOT Have (Guardrails)
- No direct download/reuse/re-upload of source platform videos.
- No autonomous publishing without approval.
- No multi-tenant SaaS scope in phase-1.
- No expansion to extra platforms beyond TikTok + YouTube Shorts.

### Refinement: A-Mode Video Generation Method (Confirmed)

> **A mode policy (hard invariant)**:
> Source YouTube/TikTok videos are used only for trend signals, structure learning, segmentation, and summary extraction.
> Final outputs MUST NOT contain source footage frames/clips.

**Deterministic generation pipeline**:
1. Ingest source metadata + media for analysis workspace only
2. Shot segmentation + topic segmentation (`segments.json`)
3. Transcript + keypoint extraction (`summary_pack.json`)
4. Prompt materialization per scene (`prompt_pack.json`)
5. Scene generation with Seedance adapter (default/exclusive)
6. FFmpeg-first timeline assembly (`render_manifest.json`)
7. Automated QC gates (reuse, subtitle, audio, AV sync, style consistency)

**Stage contracts (required artifacts)**:
- `artifacts/segments.json`
- `artifacts/summary_pack.json`
- `artifacts/prompt_pack.json`
- `artifacts/render_manifest.json`
- `artifacts/qc_*.json`

**Seedance role (confirmed)**:
- Default and exclusive video generation engine in Phase-1
- No alternate video generation model/provider in this phase
- Invocation policy: Seedance generates all AI shot segments used in final composition

**Rhythm transfer policy (confirmed)**:
- Fidelity target: **medium-high rhythm fidelity**
- Preserve: beat points, information density, hook/payoff/CTA arc
- Reconstruct: visuals, wording, shot grammar (no one-to-one cloning)

**Dual-gate QC contract (both required)**:
- **Fidelity Gate** (must pass):
  - Beat alignment within +/-200ms for >= 80% key beats
  - P95 beat error <= 350ms
  - Segment duration drift <= +/-12%
  - Intensity/pacing arc correlation >= 0.75
- **Transformation Gate** (must pass):
  - Sequence similarity <= 0.93
  - Max consecutive matched shot-grammar class < 3
  - Lexical re-expression >= 40% token change in hook/CTA phrasing
  - Source motif reuse flags == 0

**Narrative pacing coherence thresholds**:
- Hook appears <= 1.5s
- Payoff occurs in 70%-90% timeline window
- CTA occurs in last 15%-25%
- Tempo whiplash (>2.5x shot-length jump) <= 2 per 8s window

**QC thresholds (fail-fast gates)**:
- Source-reuse guard: exact frame matches `== 0`, near-match ratio `<= 0.005`
- Segmentation quality: shot-boundary F1 `>= 0.85`, topic-boundary F1 `>= 0.80`
- Summary quality: factual precision `>= 0.95`, hallucination rate `<= 0.02`
- Prompt quality: schema valid `true`, ambiguity score `<= 0.15`, policy violations `== 0`
- Subtitle quality: timing offset P95 `<= 120ms`, max chars/sec `<= 20`
- Audio quality: integrated LUFS `[-17, -15]`, true peak `<= -1.0 dBTP`
- AV/style quality: AV sync offset P95 `<= 45ms`, style drift score `<= 0.18`

**Scope locks for this refinement**:
- Include: segmentation -> summary -> prompt -> generation -> assembly quality loop
- Exclude: source-clip remix mode (B mode), additional distribution channels, editor-suite expansion
- Exclude: multi-model video generation routing (single-engine Seedance only)

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> All acceptance criteria below are agent-executable. Human approval is represented as an API event emitted by automated test scenarios (not manual clicking).

### Test Decision
- **Infrastructure exists**: NO
- **Automated tests**: TDD
- **Framework**: `pytest` + `playwright` + `ruff` + `mypy`

### If TDD Enabled

Each implementation task follows RED-GREEN-REFACTOR:
1. RED: write failing test.
2. GREEN: implement minimum passing logic.
3. REFACTOR: improve internals while preserving passing tests.

**Test Setup Task**: included as Task 0.

### Agent-Executed QA Scenarios

All tasks include concrete scenarios with tool, preconditions, exact steps, expected results, failure indicators, and evidence paths.

---

## Execution Strategy

### Parallel Execution Waves

Wave 1 (Start Immediately):
- Task 0: Test/CI bootstrap
- Task 1: Contracts + compliance taxonomy

Wave 2 (After Wave 1):
- Task 2: Trend ingestion service
- Task 3: Script generation + originality gate
- Task 3A: Seedance scene generation service (default/exclusive)
- Task 4: Localization + voiceover pipeline

Wave 3 (After Wave 2):
- Task 5: Review API + review UI
- Task 6: Publisher adapters + scheduling/rate-limit layer
- Task 7: Orchestrator + cost control + retries

Wave 4 (After Wave 3):
- Task 8: Metrics + weekly revenue KPI endpoint
- Task 9: End-to-end test matrix + hardening

Critical Path: 0 -> 1 -> 6 -> 7 -> 8
Parallel Speedup: ~35-45% vs sequential

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|---|---|---|---|
| 0 | None | 2,3,4,9 | 1 |
| 1 | None | 3,4,5,7 | 0 |
| 2 | 0,1 | 7,9 | 3,4 |
| 3 | 0,1 | 5,7,9 | 2,4 |
| 3A | 0,1,3 | 7,9 | 2,4 |
| 4 | 0,1 | 5,7,9 | 2,3 |
| 5 | 1,3,4 | 7,9 | 6 |
| 6 | 1,2 | 7,8,9 | 5 |
| 7 | 1,2,3,3A,4,5,6 | 8,9 | None |
| 8 | 6,7 | 9 | None |
| 9 | 0..8,3A | None | None |

---

## TODOs

- [x] 0. Bootstrap repository, test framework, and CI

  **What to do**:
  - Initialize Python service workspace, dependency management, lint/type/test config.
  - Add `pytest` baseline + sample passing test.
  - Add CI workflow to run lint/type/test on push.

  **Must NOT do**:
  - Do not introduce optional framework sprawl.
  - Do not skip failing-fast CI setup.

  **Recommended Agent Profile**:
  - **Category**: `quick` (bootstrap + tooling setup)
  - **Skills**: `git-master` (clean commit boundaries), `playwright` (future E2E tooling alignment)
  - **Skills Evaluated but Omitted**: `frontend-ui-ux` (not required for infra bootstrap)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: 2,3,4,9
  - **Blocked By**: None

  **References**:
  - `.sisyphus/plans/video-localization-automation-plan.md` - plan structure conventions for this workspace.
  - `https://docs.pytest.org/en/stable/getting-started.html` - canonical test runner setup.
  - `https://playwright.dev/python/docs/intro` - browser E2E test runner integration.
  - `https://docs.github.com/actions` - CI workflow baseline.

  **Acceptance Criteria**:
  - [ ] `pytest -q` runs and returns at least one passing test.
  - [ ] CI workflow file exists and includes lint + type + test steps.
  - [ ] `ruff check .` and `mypy .` commands run in CI pipeline.

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: Local test bootstrap success
    Tool: Bash
    Preconditions: Dependencies installed in virtual environment
    Steps:
      1. Run: pytest -q
      2. Assert: output contains "1 passed"
      3. Run: ruff check .
      4. Assert: exit code is 0
    Expected Result: Test/lint baseline is operational
    Failure Indicators: missing test discovery, non-zero exit
    Evidence: .sisyphus/evidence/task-0-bootstrap.txt

  Scenario: CI workflow static validation
    Tool: Bash
    Preconditions: Workflow file committed in repository
    Steps:
      1. Parse workflow YAML and verify jobs include lint/type/test
      2. Assert: all three command steps present
    Expected Result: CI enforces quality gates
    Failure Indicators: any gate missing
    Evidence: .sisyphus/evidence/task-0-ci-check.txt
  ```

- [x] 1. Define data contracts and compliance taxonomy

  **What to do**:
  - Define schemas: `trend_candidate`, `script_draft`, `localized_variant`, `approval_decision`, `publish_receipt`, `revenue_event`.
  - Define locale policy rules and blocked categories.
  - Define originality threshold and violation codes.

  **Must NOT do**:
  - Do not leave policy outcomes as free-text only.
  - Do not skip locale-specific rule fields.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `git-master`, `playwright`
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: 3,4,5,7
  - **Blocked By**: None

  **References**:
  - `https://developers.google.com/youtube/v3` - YouTube integration field constraints.
  - `https://developers.tiktok.com/` - TikTok platform API and policy context.
  - `.sisyphus/evidence/task-1-policy-snapshot-check.txt` - existing policy evidence artifact style.

  **Acceptance Criteria**:
  - [ ] Contract files include all six core entities with validation constraints.
  - [ ] Policy rule set includes locale code and blocked reason enums.
  - [ ] Originality checker schema includes threshold and traceable similarity score.

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: Contract validation rejects malformed payload
    Tool: Bash
    Preconditions: Contract validation CLI/entrypoint available
    Steps:
      1. Submit invalid trend_candidate payload missing required topic field
      2. Assert: validation error code CONTRACT_REQUIRED_FIELD
    Expected Result: Invalid payload rejected deterministically
    Failure Indicators: payload accepted or vague error
    Evidence: .sisyphus/evidence/task-1-contract-invalid.json

  Scenario: Locale policy block for JA-JP prohibited class
    Tool: Bash
    Preconditions: Policy evaluator endpoint available
    Steps:
      1. Submit JA-JP sample content with prohibited claim category
      2. Assert: result.status = blocked
      3. Assert: result.policy_code present
    Expected Result: Block with explicit policy code
    Failure Indicators: pass-through without reason
    Evidence: .sisyphus/evidence/task-1-policy-block.json
  ```

- [x] 2. Build trend signal ingestion module

  **What to do**:
  - Ingest trend metadata (not source media) from target platforms.
  - Deduplicate trends and rank candidates by monetization potential proxy.
  - Persist normalized candidates for downstream generation.
  - Add analysis-only ingest path for segmentation and summary extraction, separated from publish assets.

  **Must NOT do**:
  - No source media download/reuse pipeline.
  - No unbounded polling without quota controls.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `git-master`
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`, `playwright`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with 3,4)
  - **Blocks**: 6,7,9
  - **Blocked By**: 0,1

  **References**:
  - `https://developers.google.com/youtube/v3/docs/search/list` - trend-relevant search metadata.
  - `https://developers.tiktok.com/doc/overview` - TikTok API constraints and access model.

  **Acceptance Criteria**:
  - [ ] Ingestion job stores normalized trend candidates with source metadata.
  - [ ] Duplicate trend IDs are ignored idempotently.
  - [ ] Rate-limit config is enforced with backoff.
  - [ ] Analysis workspace assets are tagged `analysis_only=true` and blocked from final publish manifests.
  - [ ] Source-analysis outputs include beat map and pacing map artifacts for downstream transfer.

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: Duplicate trend ingestion is idempotent
    Tool: Bash
    Preconditions: Ingestion endpoint and test datastore available
    Steps:
      1. POST same trend payload twice
      2. Query trend_candidate store by external_id
      3. Assert: exactly one record exists
    Expected Result: No duplicate rows
    Failure Indicators: count > 1
    Evidence: .sisyphus/evidence/task-2-idempotent.json
  ```

- [x] 3. Build original script generation + originality gate

  **What to do**:
  - Generate original scripts from trend signals.
  - Run similarity/originality scoring before approval queue.
  - Reject drafts below originality threshold.
  - Generate `summary_pack.json` and `prompt_pack.json` from segmented source analysis with schema validation.

  **Must NOT do**:
  - No direct transcript paraphrase fallback.
  - No silent bypass of originality checks.

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
  - **Skills**: `git-master`
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: 5,7,9
  - **Blocked By**: 0,1

  **References**:
  - `https://platform.openai.com/docs/guides/text-generation` - prompt/output design for script generation.
  - `https://www.sbert.net/` - semantic similarity scoring approaches.

  **Acceptance Criteria**:
  - [ ] Script draft generated with required hook/body/CTA fields.
  - [ ] Originality score calculated and persisted.
  - [ ] Low-originality drafts are blocked with explicit code.
  - [ ] `summary_pack.json` passes factual quality checks.
  - [ ] `prompt_pack.json` passes schema + ambiguity + policy checks.
  - [ ] Prompt pack includes explicit beat windows and shot-duration constraints for medium-high rhythm fidelity.

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: Low-originality draft is rejected
    Tool: Bash
    Preconditions: Similarity service seeded with reference corpus
    Steps:
      1. Submit trend producing intentionally derivative prompt
      2. Assert: originality_score < threshold
      3. Assert: state = rejected_originality
    Expected Result: Draft does not enter approval queue
    Failure Indicators: derivative draft reaches review queue
    Evidence: .sisyphus/evidence/task-3-originality-block.json
  ```

- [x] 3A. Build Seedance scene generation service (default/exclusive)

  **What to do**:
  - Implement Seedance generation adapter that consumes `prompt_pack.json` scene prompts.
  - Persist generated scene assets and metadata for FFmpeg assembly (`scene_asset_uri`, `duration_ms`, `seedance_profile`).
  - Enforce single-engine policy: all AI-generated scene assets come from Seedance in Phase-1.

  **Must NOT do**:
  - Do not add alternate video generation providers in this phase.
  - Do not bypass prompt schema or policy gate requirements before generation.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `git-master`
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`, `playwright`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: 7,9
  - **Blocked By**: 0,1,3

  **References**:
  - `https://jimeng.jianying.com/` - Seedance/Jimeng capability context and generation modes.
  - `https://ffmpeg.org/documentation.html` - downstream assembly metadata requirements.

  **Acceptance Criteria**:
  - [ ] Scene generation job accepts validated prompt pack and returns standardized scene asset metadata.
  - [ ] Generated scenes are traceable to prompt IDs and Seedance profile IDs.
  - [ ] Generation output is rejected if prompt schema is invalid or policy gate is not passed.

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: Seedance generation produces scene assets with metadata
    Tool: Bash
    Preconditions: Valid prompt_pack.json available
    Steps:
      1. Trigger scene generation with a valid prompt pack
      2. Assert: output includes scene_asset_uri and duration_ms per scene
      3. Assert: seedance_profile is present in metadata
    Expected Result: Scene assets are ready for FFmpeg assembly
    Failure Indicators: missing asset URIs or metadata fields
    Evidence: .sisyphus/evidence/task-3a-seedance-output.json

  Scenario: Invalid prompt pack is blocked pre-generation
    Tool: Bash
    Preconditions: Invalid prompt_pack.json fixture available
    Steps:
      1. Trigger generation with invalid prompt pack
      2. Assert: validation error returned
      3. Assert: no scene asset created
    Expected Result: Invalid prompt input is rejected deterministically
    Failure Indicators: generation proceeds despite invalid schema
    Evidence: .sisyphus/evidence/task-3a-seedance-block.json
  ```

- [x] 4. Build localization and voiceover generation module

  **What to do**:
  - Transcreate scripts for EN-US, EN-SEA, JA-JP.
  - Generate locale-specific TTS voiceover assets.
  - Validate locale policy compliance post-localization.

  **Must NOT do**:
  - No direct machine translation without style constraints.
  - No publish-ready state without post-localization policy pass.

  **Recommended Agent Profile**:
  - **Category**: `artistry`
  - **Skills**: `git-master`, `playwright`
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: 5,7,9
  - **Blocked By**: 0,1

  **References**:
  - `https://cloud.google.com/text-to-speech/docs` - TTS generation and voice controls.
  - `https://learn.microsoft.com/azure/ai-services/speech-service/` - alternative TTS provider behavior.

  **Acceptance Criteria**:
  - [ ] Three localized variants generated per approved script input.
  - [ ] Voiceover file path and duration metadata stored per locale.
  - [ ] Locale policy check runs after localization and can block variant.

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: JA-JP localization passes and produces audio
    Tool: Bash
    Preconditions: TTS credentials configured for test provider
    Steps:
      1. Submit approved script for JA-JP localization
      2. Assert: localized text exists and language tag is ja-JP
      3. Assert: audio file generated and duration > 0
    Expected Result: Localized artifact ready for review
    Failure Indicators: missing voice file or wrong locale tag
    Evidence: .sisyphus/evidence/task-4-ja-output.json

  Scenario: Locale policy blocks violating localized variant
    Tool: Bash
    Preconditions: Policy block sample text available
    Steps:
      1. Submit known violating localized text for EN-SEA
      2. Assert: status = blocked_policy
      3. Assert: policy_code not null
    Expected Result: Variant blocked before review queue
    Failure Indicators: violating variant enters queue
    Evidence: .sisyphus/evidence/task-4-policy-block.json
  ```

- [x] 5. Build review API and review queue UI

  **What to do**:
  - Create queue API for pending localized variants.
  - Create minimal review UI for approve/reject with reasons.
  - Enforce approval SLA and stale-item policy.

  **Must NOT do**:
  - Do not allow publish endpoints to bypass review decision state.
  - Do not omit decision audit fields.

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: `frontend-ui-ux`, `playwright`
  - **Skills Evaluated but Omitted**: `git-master`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with 6)
  - **Blocks**: 7,9
  - **Blocked By**: 1,3,4

  **References**:
  - `https://playwright.dev/docs/test-assertions` - deterministic UI assertions.
  - `.sisyphus/evidence/task-1-stale-test.md` - evidence storage convention for stale handling artifacts.

  **Acceptance Criteria**:
  - [x] `GET /review/queue` returns pending items with locale, policy, originality, cost fields.
  - [x] `POST /review/decision` writes immutable decision log.
  - [x] Items exceeding SLA transition to `expired` and cannot be published.

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: Approve flow unlocks publish eligibility
    Tool: Playwright
    Preconditions: Review UI running; one pending item seeded
    Steps:
      1. Navigate to /review
      2. Wait for table row with status "pending"
      3. Click row action button data-testid="approve"
      4. Assert toast contains "Decision saved"
      5. Call API and assert item state = approved
      6. Screenshot: .sisyphus/evidence/task-5-approve-ui.png
    Expected Result: Item becomes publish-eligible
    Failure Indicators: state not updated or missing audit record
    Evidence: .sisyphus/evidence/task-5-approve-ui.png

  Scenario: Publish blocked when approval missing
    Tool: Bash
    Preconditions: Variant exists in pending state
    Steps:
      1. Call publish endpoint directly with pending item ID
      2. Assert: HTTP 409
      3. Assert: error code HUMAN_APPROVAL_REQUIRED
    Expected Result: Hard gate enforced
    Failure Indicators: publish allowed without approval
    Evidence: .sisyphus/evidence/task-5-human-gate.json
  ```

- [x] 6. Build publisher adapters (TikTok + YouTube Shorts)

  **What to do**:
  - Implement publish request builders and adapter interfaces.
  - Add per-platform scheduling windows and rate-limit controls.
  - Persist publish receipt with platform IDs and statuses.

  **Must NOT do**:
  - Do not implement best-effort silent failures.
  - Do not skip idempotency keys for publish calls.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `git-master`
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: 7,8,9
  - **Blocked By**: 1,2

  **References**:
  - `https://developers.google.com/youtube/v3/docs/videos/insert` - upload flow and required fields.
  - `https://developers.tiktok.com/doc/content-posting-api-overview` - TikTok posting capability and constraints.

  **Acceptance Criteria**:
  - [x] Publish adapter accepts approved payload and returns standardized receipt.
  - [x] Repeated publish call with same idempotency key does not create duplicate posts.
  - [x] Partial publish failure captured per platform with retry state.

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: Idempotent publish request
    Tool: Bash
    Preconditions: Mock publish providers running
    Steps:
      1. Submit approved variant publish request with idempotency_key K1
      2. Repeat same request with K1
      3. Assert: only one receipt in datastore for each platform
    Expected Result: Duplicate publish prevented
    Failure Indicators: >1 receipt created per platform
    Evidence: .sisyphus/evidence/task-6-idempotency.json

  Scenario: Partial platform failure is isolated
    Tool: Bash
    Preconditions: TikTok mock forced failure, YouTube mock success
    Steps:
      1. Trigger publish for both platforms
      2. Assert: YouTube status = success
      3. Assert: TikTok status = failed_retryable
    Expected Result: One success does not get rolled back
    Failure Indicators: both marked failed or both retried incorrectly
    Evidence: .sisyphus/evidence/task-6-partial-failure.json
  ```

- [x] 7. Implement orchestration workflow with cost + retry governance

  **What to do**:
  - Orchestrate full state machine from trend to publish.
  - Enforce per-video budget cap, daily spend cap, and retry ceilings.
  - Add Seedance profile fallback order (quality/speed tiers within Seedance) with deterministic stop conditions.

  **Must NOT do**:
  - Do not allow infinite retries.
  - Do not allow state transitions that bypass policy/review gates.

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
  - **Skills**: `git-master`
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`, `playwright`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 3)
  - **Blocks**: 8,9
  - **Blocked By**: 1,2,3,4,5,6

  **References**:
  - `https://temporal.io/` - durable workflow patterns and retry semantics.
  - `https://docs.n8n.io/` - alternative workflow orchestration if low-code route is retained.

  **Acceptance Criteria**:
  - [x] State machine enforces required sequence and gate checks.
  - [x] Budget exceed event sets state `halted_cost_cap`.
  - [x] Retry policy is bounded and logged with reason codes.

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: Cost circuit breaker halts job
    Tool: Bash
    Preconditions: Per-video budget set to low threshold for test
    Steps:
      1. Trigger generation with expensive model route
      2. Assert: accumulated_cost exceeds cap
      3. Assert: workflow state transitions to halted_cost_cap
    Expected Result: Job halts and no publish attempt occurs
    Failure Indicators: pipeline continues after cap exceed
    Evidence: .sisyphus/evidence/task-7-cost-breaker.json

  Scenario: Retry ceiling prevents runaway
    Tool: Bash
    Preconditions: Simulated provider timeout configured
    Steps:
      1. Trigger stage with known timeout
      2. Assert: retries stop at configured max
      3. Assert: terminal state = failed_retry_exhausted
    Expected Result: Bounded failure behavior
    Failure Indicators: retries continue past ceiling
    Evidence: .sisyphus/evidence/task-7-retry-ceiling.json
  ```

- [x] 8. Implement metrics and weekly revenue KPI service

  **What to do**:
  - Define KPI schema (`gross_revenue`, `net_revenue`, `rpm_proxy`, `approval_rate`, `publish_success_rate`).
  - Aggregate 7-day windows by locale/platform.
  - Expose query API for dashboard and optimization loops.

  **Must NOT do**:
  - Do not mix gross and net revenue fields.
  - Do not return unbounded historical queries by default.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `git-master`
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4
  - **Blocks**: 9
  - **Blocked By**: 6,7

  **References**:
  - `https://www.youtube.com/creators/how-things-work/content-analytics/` - YouTube analytics concepts for KPI mapping.
  - `https://business.tiktok.com/` - TikTok business analytics context.

  **Acceptance Criteria**:
  - [x] `GET /metrics/revenue-weekly?locale=en-US` returns numeric KPI fields.
  - [x] Aggregation window is exactly trailing 7 days.
  - [x] Locale/platform filters are validated and enforced.

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: Weekly KPI endpoint returns valid schema
    Tool: Bash
    Preconditions: Seeded revenue_event records for 7+ days
    Steps:
      1. Call endpoint for locale=en-US
      2. Assert: fields gross_revenue/net_revenue/rpm_proxy are numeric
      3. Assert: window_days == 7
    Expected Result: KPI payload is queryable for optimization
    Failure Indicators: missing fields or wrong window
    Evidence: .sisyphus/evidence/task-8-kpi-schema.json
  ```

- [x] 9. Execute full E2E matrix and release hardening

  **What to do**:
  - Run full matrix across locales and platform routes with mock/live-safe modes.
  - Validate edge cases: duplicate trends, stale approvals, partial publish success, provider outage, DST sloting.
  - Gate release on all critical checks.

  **Must NOT do**:
  - Do not ship with unresolved critical policy/cost/review gate failures.
  - Do not skip negative scenarios.

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `playwright`, `git-master`
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 final
  - **Blocks**: None
  - **Blocked By**: 0..8

  **References**:
  - `https://playwright.dev/docs/test-parallel` - parallel E2E execution model.
  - `.sisyphus/evidence/task-1-policy-snapshot-check.txt` - evidence naming/retention style.

  **Acceptance Criteria**:
  - [x] End-to-end happy path passes for all three locales.
  - [x] Human gate enforced in all publish paths (no bypass).
  - [x] Cost and policy negative tests pass.
  - [x] Evidence files captured under `.sisyphus/evidence/task-9-*`.
  - [x] A-mode reuse guard passes: exact source-frame matches = 0.
  - [x] Subtitle/audio/AV/style QC thresholds pass from `qc_*.json` artifacts.
  - [x] Fidelity Gate and Transformation Gate both pass from machine-readable QC reports.

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: Full happy path from trend to published receipt
    Tool: Bash
    Preconditions: Test environment running with mock platform adapters
    Steps:
      1. Ingest trend candidate
      2. Generate script + localization variants
      3. Emit approval event via API
      4. Trigger publish
      5. Assert: publish_receipt exists for selected platform(s)
    Expected Result: End-to-end flow succeeds after approval
    Failure Indicators: state stuck or publish without approval
    Evidence: .sisyphus/evidence/task-9-happy-path.json

  Scenario: Approval timeout expires item
    Tool: Bash
    Preconditions: SLA timeout shortened in test config
    Steps:
      1. Create pending review item
      2. Wait past SLA
      3. Assert: state = expired
      4. Attempt publish and assert HTTP 409
    Expected Result: stale item cannot be published
    Failure Indicators: expired item publish succeeds
    Evidence: .sisyphus/evidence/task-9-expiry.json
  ```

---

## Commit Strategy

| After Task | Message | Verification |
|---|---|---|
| 0-1 | `chore(bootstrap): initialize test and contract baseline` | pytest + lint + type |
| 2-4 | `feat(pipeline): add ingestion generation localization modules` | module tests |
| 5-7 | `feat(workflow): add review gate publishers and orchestration controls` | integration tests |
| 8-9 | `feat(metrics): add KPI service and e2e hardening` | e2e matrix |

---

## Success Criteria

### Verification Commands
```bash
pytest -q
ruff check .
mypy .
pytest tests/e2e/test_pipeline_happy_path.py -q
pytest tests/e2e/test_human_gate_required.py -q
pytest tests/e2e/test_cost_circuit_breaker.py -q
pytest tests/e2e/test_locale_policy_block_ja_jp.py -q
```

### Final Checklist
- [x] All Must Have controls are present.
- [x] All Must NOT Have constraints are respected.
- [x] Approval gate, policy gate, and cost gate are all enforceable by tests.
- [x] Weekly revenue KPI endpoint is available and validated.
- [x] Evidence artifacts captured for happy path and negative paths.

---

## Appendix A - Reorganized Chinese TODO (Execution View)

> This appendix is a Chinese execution view of the same plan scope, with Seedance made explicit as an independent task. It does not replace the canonical acceptance criteria above.

### 阶段 0：基础设施
- [x] T0 初始化仓库与工程基线（Python、pytest、ruff、mypy、CI）
- [x] T1 定义核心数据契约与合规分类（6类实体、违规码、locale规则）

### 阶段 1：内容理解与生成核心
- [x] T2 趋势信号采集与标准化（含 `analysis_only` 资产隔离）
- [x] T3 内容理解管线（分段、摘要、Prompt 产物）
- [x] T4 Seedance 生成服务（默认且唯一引擎，输出镜头资产与元数据）

### 阶段 2：本地化与发布门禁
- [x] T5 本地化与配音（EN-US / EN-SEA / JA-JP）+ 本地化后合规校验
- [x] T6 审核 API + 审核队列 UI（审批通过才允许发布）
- [x] T7 发布适配层（TikTok + YouTube Shorts，幂等与部分失败处理）

### 阶段 3：编排治理与商业闭环
- [x] T8 工作流编排与治理（状态机、成本熔断、重试上限、Seedance 档位回退）
- [x] T9 收益指标服务（7日滚动 KPI，按市场/平台聚合）

### 阶段 4：最终验收
- [x] T10 全链路 E2E 与硬化（Happy Path + 负向场景 + 证据归档）
- [x] 双闸门必须同时通过：
  - [x] Fidelity Gate（节奏保真）
  - [x] Transformation Gate（转化距离与防过度相似）

### 对应关系（便于对照原任务编号）
- [x] 原 Task 0-1 对应 T0-T1
- [x] 原 Task 2 对应 T2
- [x] 原 Task 3 + 新 Task 3A 对应 T3-T4（显式 Seedance）
- [x] 原 Task 4-6 对应 T5-T7
- [x] 原 Task 7-9 对应 T8-T10
