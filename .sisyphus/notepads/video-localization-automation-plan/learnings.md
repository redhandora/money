# Learnings

## 2026-02-16 - Task 3 (Toolchain Matrix)

- A neutral intermediate artifact strategy (mezzanine media + timestamped transcript + TMX/SRT/JSON sidecars) is the main control that keeps managed and self-hosted paths interchangeable.
- The most practical non-locking baseline is hybrid-by-stage: managed for ASR/MT/TTS speed, self-hosted for compositing control, with orchestration adapters to preserve portability.
- Failure handling quality is less about tool choice and more about enforcing stage-local fallbacks, queue backpressure, and canary rollback thresholds.

- 2026-02-16: Official-platform wording consistently separates platform-level policy compliance from monetization-program eligibility checks.
- 2026-02-16: Task-1 QA baseline passed with 11 dated citation lines, exceeding the >=6 minimum.
- 2026-02-16: For dual-track scoring, keeping `fit_en` and `fit_zh` as separate explicit columns avoids false aggregation and exposes scheme asymmetry.
- 2026-02-16: Task-2 scoring remains reproducible when assumptions are declared in-file and tied to capability anchors from official provider documentation.

## 2026-02-16 - Task 4 (Risk Gates and Thresholds)

- Numeric threshold governance becomes auditable only when each gate metric has explicit units, windows, and state boundaries.
- Balanced-mode operations are more resilient with lane-scoped HITL holds (`pause_distribution` on affected candidates) instead of full-network freezes for non-hard-stop events.
- Keeping publish and monetization as separate controls allows monetization risk containment without automatically collapsing compliant publish lanes.

## 2026-02-16 - Task 5 (Unit Economics + SLO)

- Balanced-mode economics are more sensitive to monetize eligibility degradation than to moderate processing cost drift; publish/monetize gate separation must remain explicit in KPI math.
- `Track: ZH` shows higher upside per localized minute but a sharper downside curve in the worst case, so stricter quality and strike-budget controls are justified.
- A reusable KPI pattern that includes a `Data source / assumption field` per row keeps scenario outputs reproducible even when upstream draft inputs are missing.

## 2026-02-16 - Task 6 (Final Recommendation + Rollout)

- Final synthesis is most stable when the decision spine is dual-track by design (`Track: EN` throughput + `Track: ZH` monetization-safe quality) instead of forcing a single default posture.
- Rollout safety depends on preserving publish-vs-monetize gate separation at each phase transition, enabling lane-level monetization holds without unnecessary publish collapse.
- Phase advancement quality is improved when entry/exit checks are tied to canonical thresholds (`rights_confidence`, `term_adherence`, `av_sync_ms`, `strike_rate`, `rollback_mttr`) and explicit threshold/action rollback pairs.
- Strike-budget and quality stability are stronger scale-up signals than volume growth because monetize-eligibility degradation drives the sharpest margin downside.
- 2026-02-16: Completion-check consistency holds when plan checkboxes are toggled only after artifact-backed verification (deliverables, source traceability, gate separation, rollback triggers).
