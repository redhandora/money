# Decisions

## 2026-02-16 - Task 3 (Toolchain Matrix)

- Decision: produce a 7-stage matrix with explicit managed-service and self-hosted alternatives per stage; avoid any single-vendor recommendation.
- Decision: include a dedicated decision-rule section with practical triggers for managed vs self-hosted selection and hybrid rollout defaults.
- Decision: include explicit cost assumption/basis notes and official public reference links for all cost-directional statements.
- Decision: include a failure-mode section with 10 concrete items, covering required risks (rate limits, lock-in, latency, quality drift) and mitigations.

- 2026-02-16: Use a 1-5 favorable-score scale across all scorecard columns, with `compliance_risk=5` meaning lowest risk exposure.
- 2026-02-16: Keep three schemes exactly as plan-defined (AI-first UGC, Hybrid OTT, FAST/CTV factory) and decide winners by operating context, not one aggregate metric.
- 2026-02-16: For Task 1 evidence, use only first-party policy domains (Google/YouTube Help, TikTok official policy/legal pages, Meta official transparency/business policy pages).
- 2026-02-16: Enforce freshness SLA in artifact text as "<=30 days at execution" and verify with dated citation-line audit.
- 2026-02-16: Synced plan checklist state for verified Wave 1 completion (tasks 1-3 marked complete).

## 2026-02-16 - Task 4 (Risk Gates and Thresholds)

- Decision: lock canonical Task-4 schema keys to `rights_confidence`, `term_adherence`, `av_sync_ms`, `strike_rate`, `rollback_mttr` for deterministic QA checks.
- Decision: lock escalation states to `auto-pass`, `HITL-review`, `hard-stop` and map `hard-stop` to mandatory `pause_distribution` plus `rollback`.
- Decision: enforce separate control paths for `publish_eligibility` and `monetization_eligibility`; monetization failure cannot collapse this split into one merged gate.
- Decision: set strike hard-stop at `strike_rate >=0.50%` (trailing 30-day lane window) and require recovery `<0.20%` for 14 consecutive days before resume.

## 2026-02-16 - Task 5 (Unit Economics + SLO)

- Decision: model all economics as six rows (3 scenarios x 2 tracks) using exact labels `Best Case`, `Base Case`, `Worst Case`, `Track: EN`, and `Track: ZH`.
- Decision: include explicit formula definitions and publish/monetize split rates so downstream task-6 synthesis can trace margin changes to gate performance.
- Decision: enforce SLO table columns with numeric target plus explicit `On breach action` for all required metrics (time-to-publish, quality score, incident MTTR, policy strike budget).
- 2026-02-16: Synced plan checklist state for verified Wave 2 completion (tasks 4-5 marked complete).

## 2026-02-16 - Task 6 (Final Recommendation + Rollout)

- Decision: publish `.sisyphus/research/final-recommendation-and-rollout.md` with mandatory sections exactly named `Recommended Path`, `Why Not the Alternatives`, `Rollout Phases`, and `Rollback Triggers`.
- Decision: keep recommendation as balanced dual-track (EN + ZH) and avoid a universal one-scheme winner; use context-specific profile selection under a shared gate framework.
- Decision: lock rollout shape to three phases (canary -> limited scale -> full scale) with explicit entry criteria, exit criteria, and stop/rollback threshold-action pairs in each phase.
- Decision: preserve strict source traceability by attaching at least one `Source: .sisyphus/research/...` reference to every major decision bullet.
- Decision: enforce deterministic QA evidence outputs in `.sisyphus/evidence/task-6-traceability.txt` and `.sisyphus/evidence/task-6-rollback-audit.txt`.
- 2026-02-16: Synced final plan checklist state (task 6 marked complete; overall tasks 1-6 now checked).
