# Unit Economics + SLO Model (Balanced Mode)

Updated: 2026-02-16
Mode: Balanced risk posture (moderate HITL + phased canary)
Scope: Dual-track localization economics and operating SLOs for `Track: EN` and `Track: ZH`

## Traceability and modeling basis

- Source: `.sisyphus/research/comparables-scorecard.csv` (relative quality/risk/speed/cost positioning by scheme, including `fit_en` and `fit_zh`).
- Source: `.sisyphus/research/toolchain-matrix.md` (stage-level cost drivers, latency, incident MTTR framing, fallback strategy).
- Source: `.sisyphus/research/policy-snapshot-2026Q1.md` (publish vs monetize gate split and policy-risk assumptions).
- Limitation: `.sisyphus/drafts/video-localization-research.md` is not present in workspace; assumptions are explicit and reproducible below.

## Modeling formula (reproducible)

- `localized_minutes = input_minutes * publish_success_rate`
- `monetized_minutes = localized_minutes * monetize_eligibility_rate`
- `monthly_revenue = monetized_minutes * realized_revenue_per_localized_minute_usd`
- `monthly_processing_cost = localized_minutes * processing_cost_per_localized_minute_usd`
- `contribution_margin_pct = (monthly_revenue - monthly_processing_cost) / monthly_revenue`

## KPI and cost-driver assumptions (with source tags)

| KPI / cost driver | `Track: EN` assumption | `Track: ZH` assumption | Data source / assumption field |
|---|---:|---:|---|
| Input minutes per month (Base Case) | 12,000 | 8,000 | Source: `.sisyphus/research/comparables-scorecard.csv` speed/cost ranking and balanced dual-track mix assumption. |
| Publish success rate (Base Case) | 95% | 92% | Source: `.sisyphus/research/policy-snapshot-2026Q1.md` publish gate strictness + balanced HITL review assumption. |
| Monetize eligibility rate (Base Case) | 78% | 70% | Source: `.sisyphus/research/policy-snapshot-2026Q1.md` monetize gate independence and stricter policy sensitivity for ZH. |
| Realized revenue per localized minute (Base Case, USD) | 0.42 | 0.55 | Source: internal planning assumption calibrated to dual-track monetization mix; ZH premium-content skew assumption. |
| Processing cost per localized minute (Base Case, USD) | 0.13 | 0.19 | Source: `.sisyphus/research/toolchain-matrix.md` stage drivers (ASR/MT/TTS/compositing/orchestration) with higher ZH review load assumption. |
| Incident rate pressure on throughput | Lower relative pressure | Higher relative pressure | Source: `.sisyphus/research/toolchain-matrix.md` failure modes (latency spikes, quality drift) and scorecard `fit_zh` sensitivity. |

## Scenario economics (Best/Base/Worst)

| Scenario | Track | Input minutes/month | Publish success rate | Monetize eligibility rate | Realized revenue per localized minute (USD) | Processing cost per localized minute (USD) | Localized minutes/month | Monetized minutes/month | Monthly revenue (USD) | Monthly processing cost (USD) | Contribution margin |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Best Case | Track: EN | 14,000 | 97% | 84% | 0.46 | 0.11 | 13,580 | 11,407.2 | 5,247.31 | 1,493.80 | 71.5% |
| Base Case | Track: EN | 12,000 | 95% | 78% | 0.42 | 0.13 | 11,400 | 8,892.0 | 3,734.64 | 1,482.00 | 60.3% |
| Worst Case | Track: EN | 10,000 | 90% | 68% | 0.36 | 0.17 | 9,000 | 6,120.0 | 2,203.20 | 1,530.00 | 30.6% |
| Best Case | Track: ZH | 9,000 | 95% | 79% | 0.61 | 0.16 | 8,550 | 6,754.5 | 4,120.24 | 1,368.00 | 66.8% |
| Base Case | Track: ZH | 8,000 | 92% | 70% | 0.55 | 0.19 | 7,360 | 5,152.0 | 2,833.60 | 1,398.40 | 50.6% |
| Worst Case | Track: ZH | 7,000 | 86% | 58% | 0.46 | 0.25 | 6,020 | 3,491.6 | 1,606.14 | 1,505.00 | 6.3% |

## SLO model (Balanced Mode)

| SLO metric | Numeric target | Measurement window | Data source / assumption field | On breach action |
|---|---|---|---|---|
| Time-to-publish | P95 <= 6h (`Track: EN`), P95 <= 8h (`Track: ZH`) | Rolling 7 days | Source: `.sisyphus/research/toolchain-matrix.md` latency/fallback guidance; assumption: balanced mode keeps moderate HITL overhead. | Trigger degraded-mode routing to fallback provider, reduce new intake by 20%, and open incident with `sev-2` until 3 consecutive days back within target. |
| Quality score | Weighted localization QA >= 92/100 (`Track: EN`), >= 94/100 (`Track: ZH`) | Per release batch, reviewed daily | Source: `.sisyphus/research/comparables-scorecard.csv` quality/fit gradients; assumption: ZH requires tighter terminology and cultural context control. | Auto-route failing titles to HITL queue, freeze model/voice version changes, and run terminology rollback before next publish window. |
| Incident MTTR | <= 45 minutes for pipeline incidents that block publish | Rolling 30 days | Source: `.sisyphus/research/toolchain-matrix.md` failure-mode section (orchestrator/rate-limit/latency incidents) and mitigation cadence assumption. | Escalate to incident commander, fail over orchestrator namespace if >45 min elapsed, and pause non-critical batch jobs until MTTR recovers for 2 weeks. |
| Policy strike budget | <= 1 policy strike per 10,000 published videos (rolling 90 days); hard stop at >=2 strikes per 10,000 | Rolling 90 days | Source: `.sisyphus/research/policy-snapshot-2026Q1.md` publish-vs-monetize split and policy enforcement assumptions. | Immediately pause affected platform distribution lane, force monetization gate to manual review, and require root-cause fix + canary pass before resume. |

## Sensitivity notes for downstream synthesis

- `Track: ZH` has stronger upside per localized minute but materially higher downside if quality/policy thresholds are missed; this justifies stricter SLO targets and faster breach escalation.
- The largest downside driver in both tracks is monetize eligibility degradation (not pure processing cost inflation), consistent with publish/monetize gate separation.
- Worst-case `Track: ZH` approaches near-break-even contribution margin, so task-6 rollout should use tighter canary volume caps for ZH until strike-budget stability is confirmed.
