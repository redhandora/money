# Final Recommendation and Phased Rollout (Task 6)

Updated: 2026-02-16
Mode: Balanced dual-track strategy (`Track: EN` + `Track: ZH`)
Scope: Research synthesis and operator-ready rollout playbook only (no implementation/deployment tasks).

Assumption note:
- The dependency `.sisyphus/drafts/video-localization-research.md` is not available in this workspace; all conclusions below are explicitly tied to Task 1-5 artifacts.

## Recommended Path

- Decision: Adopt a balanced dual-track operating model where `Track: EN` optimizes throughput and `Track: ZH` optimizes monetization-safe quality with tighter review gates. Source: .sisyphus/research/comparables-scorecard.csv, .sisyphus/research/comparables-analysis.md, .sisyphus/research/unit-economics-and-slo.md.
- Decision: Use Hybrid OTT as the default governance profile for high-monetization-sensitivity lanes, with context-specific use of FAST/CTV factory practices for schedule-driven EN throughput. Source: .sisyphus/research/comparables-scorecard.csv, .sisyphus/research/comparables-analysis.md.
- Decision: Keep publish and monetize as independent controls at every phase transition; publishing may continue in constrained lanes while monetization remains held under review. Source: .sisyphus/research/policy-snapshot-2026Q1.md, .sisyphus/research/risk-gates-and-thresholds.md.
- Decision: Start with a hybrid toolchain baseline (managed ASR/translation/TTS + self-hosted compositing + portable orchestration adapters) to reduce time-to-value while preserving swapability. Source: .sisyphus/research/toolchain-matrix.md, .sisyphus/research/unit-economics-and-slo.md.
- Decision: Gate scale-up primarily on strike-budget stability and quality/SLO adherence, not gross publish volume, because margin downside is driven by monetization-eligibility degradation. Source: .sisyphus/research/unit-economics-and-slo.md, .sisyphus/research/risk-gates-and-thresholds.md.
- Decision: Enforce the canonical risk-state vocabulary (`auto-pass`, `HITL-review`, `hard-stop`) and canonical keys (`rights_confidence`, `term_adherence`, `av_sync_ms`, `strike_rate`, `rollback_mttr`) for deterministic operations and auditability. Source: .sisyphus/research/risk-gates-and-thresholds.md.

## Why Not the Alternatives

- Decision: Do not choose AI-first UGC as the default across both tracks because its lower compliance-risk score and weaker ZH fit increase monetization and policy volatility under balanced-mode constraints. Source: .sisyphus/research/comparables-scorecard.csv, .sisyphus/research/comparables-analysis.md, .sisyphus/research/policy-snapshot-2026Q1.md.
- Decision: Do not choose FAST/CTV factory as the universal default because it is strong for EN scheduling but not the strongest for ZH-sensitive terminology and premium-quality governance. Source: .sisyphus/research/comparables-scorecard.csv, .sisyphus/research/comparables-analysis.md, .sisyphus/research/unit-economics-and-slo.md.
- Decision: Do not force a single-vendor stack because lock-in and proprietary metadata increase recovery risk and weaken rollback optionality during policy or quality incidents. Source: .sisyphus/research/toolchain-matrix.md, .sisyphus/research/risk-gates-and-thresholds.md.
- Decision: Do not collapse policy interpretation across platforms/regions into one global rulebook; controls must remain lane-scoped with platform-specific strike and enforcement behavior. Source: .sisyphus/research/policy-snapshot-2026Q1.md, .sisyphus/research/risk-gates-and-thresholds.md.

## Rollout Phases

### Phase 1 - Canary

Entry criteria:
- `rights_confidence >=0.985`, `term_adherence >=0.970`, and `av_sync_ms <=120` in pre-release sampling for candidate lanes. Source: .sisyphus/research/risk-gates-and-thresholds.md.
- Unit-economics base-case assumptions and SLO instrumentation for both tracks are documented and auditable. Source: .sisyphus/research/unit-economics-and-slo.md.
- Publish-vs-monetize split gate is operationally acknowledged for each target platform lane before first canary publish. Source: .sisyphus/research/policy-snapshot-2026Q1.md, .sisyphus/research/risk-gates-and-thresholds.md.

Exit criteria (advance to Phase 2):
- Minimum 14 consecutive days with `rollout_gate=auto-pass` for canary lanes and no unresolved `HITL-review` tickets older than SLA. Source: .sisyphus/research/risk-gates-and-thresholds.md.
- `strike_rate <0.20%` on canary lanes, and policy strike budget remains within SLO target band. Source: .sisyphus/research/risk-gates-and-thresholds.md, .sisyphus/research/unit-economics-and-slo.md.
- P95 time-to-publish and quality score remain inside track targets for both EN and ZH. Source: .sisyphus/research/unit-economics-and-slo.md.

Stop/rollback trigger thresholds with actions:
- Trigger: `rights_confidence <0.960` OR `term_adherence <0.940` OR `av_sync_ms >220`; Action: immediate `pause_distribution` on affected lane and `rollback` to last known-good profile before any new publish. Source: .sisyphus/research/risk-gates-and-thresholds.md.
- Trigger: `strike_rate >=0.50%` in trailing 30-day lane window; Action: force `monetization_eligibility=hard-stop`, execute lane rollback, and hold monetization resume until `<0.20%` for 14 consecutive days. Source: .sisyphus/research/risk-gates-and-thresholds.md.
- Trigger: `rollback_mttr >60 min` after hard-stop event; Action: freeze phase advancement and run recovery drills until two consecutive drill outcomes restore `rollback_mttr <=30 min`. Source: .sisyphus/research/risk-gates-and-thresholds.md.

### Phase 2 - Limited Scale

Entry criteria:
- Phase 1 exit criteria met and documented with evidence for both tracks. Source: .sisyphus/research/risk-gates-and-thresholds.md, .sisyphus/research/unit-economics-and-slo.md.
- Demonstrated lane-level fallback readiness for revenue-critical stages (at least one warm standby path) with neutral intermediate artifacts preserved. Source: .sisyphus/research/toolchain-matrix.md.
- ZH lanes retain tighter HITL posture than EN lanes where terminology/cultural sensitivity risk remains elevated. Source: .sisyphus/research/comparables-analysis.md, .sisyphus/research/unit-economics-and-slo.md.

Exit criteria (advance to Phase 3):
- 30 consecutive days with no `hard-stop` events and with `strike_rate <0.20%` across active lanes. Source: .sisyphus/research/risk-gates-and-thresholds.md.
- Economics remain within base-case viability bands and no track falls into worst-case trajectory for two consecutive weekly reviews. Source: .sisyphus/research/unit-economics-and-slo.md.
- At least one controlled fallback exercise completed successfully per critical stage family (localize, compositing, distribution). Source: .sisyphus/research/toolchain-matrix.md.

Stop/rollback trigger thresholds with actions:
- Trigger: any key enters `hard-stop` band (`rights_confidence`, `term_adherence`, `av_sync_ms`, `strike_rate`, `rollback_mttr`); Action: revert affected lanes to Phase 1 volume and execute lane rollback immediately. Source: .sisyphus/research/risk-gates-and-thresholds.md.
- Trigger: SLO breach persistence (time-to-publish, quality, MTTR, or strike budget) for >3 consecutive days; Action: suspend further expansion, enforce HITL-only release on failing lane, and rollback latest process/profile change. Source: .sisyphus/research/unit-economics-and-slo.md, .sisyphus/research/risk-gates-and-thresholds.md.
- Trigger: fallback lane cannot recover publish continuity within MTTR budget; Action: stop scale-up, route new intake to proven lanes only, and run incident RCAs before resuming limited-scale growth. Source: .sisyphus/research/toolchain-matrix.md, .sisyphus/research/unit-economics-and-slo.md.

### Phase 3 - Full Scale

Entry criteria:
- Phase 2 exit criteria met, including 30-day hard-stop-free window and stable strike-rate performance. Source: .sisyphus/research/risk-gates-and-thresholds.md.
- Both tracks sustain SLO targets with independent publish and monetization gate outcomes documented per platform lane. Source: .sisyphus/research/policy-snapshot-2026Q1.md, .sisyphus/research/unit-economics-and-slo.md.
- Governance readiness confirmed for ongoing policy drift response (lane-scoped controls, no globalized policy assumptions). Source: .sisyphus/research/policy-snapshot-2026Q1.md, .sisyphus/research/risk-gates-and-thresholds.md.

Exit criteria (steady-state continuation):
- Quarterly review confirms dual-track fit remains valid (`fit_en` and `fit_zh` assumptions still aligned with observed performance). Source: .sisyphus/research/comparables-scorecard.csv, .sisyphus/research/unit-economics-and-slo.md.
- No unresolved policy-critical incidents and no breach of strike hard-stop threshold in rolling 90-day review. Source: .sisyphus/research/policy-snapshot-2026Q1.md, .sisyphus/research/risk-gates-and-thresholds.md.
- Contribution margin and quality remain within approved operating bands for both tracks without emergency controls. Source: .sisyphus/research/unit-economics-and-slo.md.

Stop/rollback trigger thresholds with actions:
- Trigger: `strike_rate >=0.50%` OR policy strike budget hard-stop condition met; Action: immediate monetization disable on affected lanes, rollback to last known-good release profile, and demote affected lanes to Phase 1 canary until 14-day recovery is proven. Source: .sisyphus/research/risk-gates-and-thresholds.md, .sisyphus/research/unit-economics-and-slo.md.
- Trigger: `rollback_mttr >60 min` on live incidents OR repeated SLO breach in 2 consecutive weekly windows; Action: halt net-new scale, shrink active footprint to stable subset, and execute full incident remediation cycle before expansion resume. Source: .sisyphus/research/risk-gates-and-thresholds.md, .sisyphus/research/unit-economics-and-slo.md.
- Trigger: policy drift introduces unresolved monetization ambiguity in any major platform lane; Action: hold monetization on impacted lane, continue publish only if publish gate remains compliant, and rollback monetization settings until updated policy evidence is captured. Source: .sisyphus/research/policy-snapshot-2026Q1.md, .sisyphus/research/risk-gates-and-thresholds.md.

## Rollback Triggers

| Phase | Trigger threshold | Immediate action | Resume condition |
|---|---|---|---|
| Canary | `rights_confidence <0.960` OR `term_adherence <0.940` OR `av_sync_ms >220` | `pause_distribution` on affected lane + rollback to last known-good profile | Two consecutive compliant QA samples and reviewer sign-off in HITL queue |
| Canary | `strike_rate >=0.50%` (trailing 30 days, lane-scoped) | Force `monetization_eligibility=hard-stop`, pause lane distribution, rollback profile | `strike_rate <0.20%` for 14 consecutive days + explicit approval |
| Limited scale | Any canonical key in `hard-stop` band OR SLO breach persistence >3 days | Freeze expansion, revert affected lanes to canary volume, rollback latest release/process change | 7-day stable window with all keys in `auto-pass` and no unresolved high-severity incidents |
| Full scale | Strike budget hard-stop OR `rollback_mttr >60 min` OR unresolved policy drift affecting monetization decisions | Halt net-new scale, disable monetization on impacted lanes, reduce to proven subset, execute rollback | 14-day stability window, successful fallback drill, and refreshed policy evidence confirms lane compliance |

Traceability note:
- Every major decision above is source-linked to Task 1-5 artifacts under `.sisyphus/research/` for deterministic audit checks.
