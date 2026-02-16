# 最终建议与分阶段发布计划（任务 6）

更新日期：2026-02-16
模式：平衡双轨策略（`Track: EN` + `Track: ZH`）
范围：仅包含研究综合结论与面向运营的发布手册（不含实现/部署任务）。

假设说明：
- 当前工作区中不存在依赖文件 `.sisyphus/drafts/video-localization-research.md`；以下所有结论均明确绑定到任务 1-5 产物。

## 推荐路径

- 决策：采用平衡双轨运营模型，其中 `Track: EN` 优化吞吐，`Track: ZH` 通过更严格的审核闸门优化可安全变现的质量。Source: .sisyphus/research/comparables-scorecard.csv, .sisyphus/research/comparables-analysis.md, .sisyphus/research/unit-economics-and-slo.md.
- 决策：将 Hybrid OTT 作为高变现敏感业务线的默认治理画像，并在以排期为导向的 EN 吞吐场景按上下文使用 FAST/CTV 工厂实践。Source: .sisyphus/research/comparables-scorecard.csv, .sisyphus/research/comparables-analysis.md.
- 决策：在每个阶段切换点将发布与变现保持为相互独立的控制项；在受限业务线上可继续发布，同时变现仍保持审核中。Source: .sisyphus/research/policy-snapshot-2026Q1.md, .sisyphus/research/risk-gates-and-thresholds.md.
- 决策：以混合工具链基线起步（托管 ASR/翻译/TTS + 自托管合成 + 可移植编排适配器），在保留可替换性的同时降低价值落地时间。Source: .sisyphus/research/toolchain-matrix.md, .sisyphus/research/unit-economics-and-slo.md.
- 决策：扩容主要由违规预算稳定性与质量/SLO 达标情况驱动，而非发布总量，因为利润下行主要由变现资格退化引起。Source: .sisyphus/research/unit-economics-and-slo.md, .sisyphus/research/risk-gates-and-thresholds.md.
- 决策：强制使用规范风险状态词汇（`auto-pass`, `HITL-review`, `hard-stop`）和规范键（`rights_confidence`, `term_adherence`, `av_sync_ms`, `strike_rate`, `rollback_mttr`），以实现确定性运行与可审计性。Source: .sisyphus/research/risk-gates-and-thresholds.md.

## 为什么不选其他方案

- 决策：不将 AI-first UGC 作为双轨默认方案，因为其较低的合规风险评分与较弱的 ZH 适配，会在平衡模式约束下增加变现与政策波动。Source: .sisyphus/research/comparables-scorecard.csv, .sisyphus/research/comparables-analysis.md, .sisyphus/research/policy-snapshot-2026Q1.md.
- 决策：不将 FAST/CTV 工厂作为通用默认，因为它在 EN 排期上较强，但在 ZH 敏感术语与高质量治理上并非最优。Source: .sisyphus/research/comparables-scorecard.csv, .sisyphus/research/comparables-analysis.md, .sisyphus/research/unit-economics-and-slo.md.
- 决策：不强制单厂商技术栈，因为锁定与专有元数据会增加恢复风险，并在政策或质量事件中削弱回滚可选性。Source: .sisyphus/research/toolchain-matrix.md, .sisyphus/research/risk-gates-and-thresholds.md.
- 决策：不把跨平台/跨区域政策解读压缩成一个全局规则手册；控制项必须保持业务线范围，并遵循平台特定的违规与执行行为。Source: .sisyphus/research/policy-snapshot-2026Q1.md, .sisyphus/research/risk-gates-and-thresholds.md.

## 发布阶段

### 阶段 1 - 金丝雀

准入条件：
- 候选业务线在发布前抽样中满足 `rights_confidence >=0.985`、`term_adherence >=0.970`、`av_sync_ms <=120`。Source: .sisyphus/research/risk-gates-and-thresholds.md.
- 两条轨道的单位经济基线假设与 SLO 监控均已文档化且可审计。Source: .sisyphus/research/unit-economics-and-slo.md.
- 每个目标平台业务线在首次金丝雀发布前，均已在运营上确认发布与变现的分离闸门。Source: .sisyphus/research/policy-snapshot-2026Q1.md, .sisyphus/research/risk-gates-and-thresholds.md.

退出条件（进入阶段 2）：
- 金丝雀业务线至少连续 14 天满足 `rollout_gate=auto-pass`，且不存在超过 SLA 且未解决的 `HITL-review` 工单。Source: .sisyphus/research/risk-gates-and-thresholds.md.
- 金丝雀业务线 `strike_rate <0.20%`，且政策违规预算保持在 SLO 目标区间。Source: .sisyphus/research/risk-gates-and-thresholds.md, .sisyphus/research/unit-economics-and-slo.md.
- EN 与 ZH 两条轨道的 P95 发布时延和质量评分均维持在各自目标范围内。Source: .sisyphus/research/unit-economics-and-slo.md.

停止/回滚触发阈值与动作：
- 触发条件：`rights_confidence <0.960` OR `term_adherence <0.940` OR `av_sync_ms >220`；动作：对受影响业务线立即执行 `pause_distribution`，并在任何新发布前 `rollback` 到最近一次已知良好画像。Source: .sisyphus/research/risk-gates-and-thresholds.md.
- 触发条件：业务线近 30 天窗口内 `strike_rate >=0.50%`；动作：强制 `monetization_eligibility=hard-stop`，执行业务线回滚，并在连续 14 天 `<0.20%` 前保持变现暂停。Source: .sisyphus/research/risk-gates-and-thresholds.md.
- 触发条件：`hard-stop` 事件后 `rollback_mttr >60 min`；动作：冻结阶段推进，并持续进行恢复演练，直到连续两次演练结果恢复 `rollback_mttr <=30 min`。Source: .sisyphus/research/risk-gates-and-thresholds.md.

### 阶段 2 - 有限扩展

准入条件：
- 阶段 1 退出条件已满足，且两条轨道均有证据文档。Source: .sisyphus/research/risk-gates-and-thresholds.md, .sisyphus/research/unit-economics-and-slo.md.
- 已证明收入关键阶段具备业务线级回退就绪能力（至少 1 条预热备用路径），并保留中立中间产物。Source: .sisyphus/research/toolchain-matrix.md.
- 在术语/文化敏感风险仍较高的场景下，ZH 业务线保持比 EN 更严格的 HITL 姿态。Source: .sisyphus/research/comparables-analysis.md, .sisyphus/research/unit-economics-and-slo.md.

退出条件（进入阶段 3）：
- 活跃业务线连续 30 天无 `hard-stop` 事件，且 `strike_rate <0.20%`。Source: .sisyphus/research/risk-gates-and-thresholds.md.
- 经济性维持在基线可行区间，且在连续两次周评中没有任一轨道落入最差情景轨迹。Source: .sisyphus/research/unit-economics-and-slo.md.
- 每个关键阶段族（localize、compositing、distribution）至少成功完成 1 次受控回退演练。Source: .sisyphus/research/toolchain-matrix.md.

停止/回滚触发阈值与动作：
- 触发条件：任一关键指标进入 `hard-stop` 区间（`rights_confidence`, `term_adherence`, `av_sync_ms`, `strike_rate`, `rollback_mttr`）；动作：将受影响业务线回退到阶段 1 体量，并立即执行业务线回滚。Source: .sisyphus/research/risk-gates-and-thresholds.md.
- 触发条件：SLO 违约（发布时延、质量、MTTR 或违规预算）持续 >3 天；动作：暂停进一步扩展，在失败业务线上强制仅 HITL 发布，并回滚最近一次流程/画像变更。Source: .sisyphus/research/unit-economics-and-slo.md, .sisyphus/research/risk-gates-and-thresholds.md.
- 触发条件：回退业务线无法在 MTTR 预算内恢复发布连续性；动作：停止扩容，仅将新输入路由到已验证业务线，并在恢复有限扩展增长前完成事件 RCA。Source: .sisyphus/research/toolchain-matrix.md, .sisyphus/research/unit-economics-and-slo.md.

### 阶段 3 - 全量扩展

准入条件：
- 已满足阶段 2 退出条件，包括 30 天无 hard-stop 窗口和稳定的违规率表现。Source: .sisyphus/research/risk-gates-and-thresholds.md.
- 两条轨道持续满足 SLO 目标，并按平台业务线记录独立的发布与变现闸门结果。Source: .sisyphus/research/policy-snapshot-2026Q1.md, .sisyphus/research/unit-economics-and-slo.md.
- 已确认可持续应对政策漂移的治理就绪性（业务线范围控制，无全局化政策假设）。Source: .sisyphus/research/policy-snapshot-2026Q1.md, .sisyphus/research/risk-gates-and-thresholds.md.

退出条件（稳态持续）：
- 季度评审确认双轨适配仍然成立（`fit_en` 与 `fit_zh` 假设仍与观察到的表现一致）。Source: .sisyphus/research/comparables-scorecard.csv, .sisyphus/research/unit-economics-and-slo.md.
- 在滚动 90 天评审中，不存在未解决的政策关键事件，且无违规 hard-stop 阈值突破。Source: .sisyphus/research/policy-snapshot-2026Q1.md, .sisyphus/research/risk-gates-and-thresholds.md.
- 两条轨道在无紧急控制的情况下，贡献利润率与质量保持在批准运营区间内。Source: .sisyphus/research/unit-economics-and-slo.md.

停止/回滚触发阈值与动作：
- 触发条件：`strike_rate >=0.50%` OR 满足政策违规预算 hard-stop 条件；动作：立即关闭受影响业务线变现，回滚到最近已知良好发布画像，并将受影响业务线降级至阶段 1 金丝雀，直到证明连续 14 天恢复。Source: .sisyphus/research/risk-gates-and-thresholds.md, .sisyphus/research/unit-economics-and-slo.md.
- 触发条件：线上事件 `rollback_mttr >60 min` OR 连续 2 个周窗口重复 SLO 违约；动作：停止净新增扩展，将活跃范围收缩至稳定子集，并在恢复扩展前执行完整事件修复周期。Source: .sisyphus/research/risk-gates-and-thresholds.md, .sisyphus/research/unit-economics-and-slo.md.
- 触发条件：政策漂移在任一主要平台业务线引入未解决的变现歧义；动作：暂停受影响业务线变现，若发布闸门仍合规则仅继续发布，并在获取更新政策证据前回滚变现设置。Source: .sisyphus/research/policy-snapshot-2026Q1.md, .sisyphus/research/risk-gates-and-thresholds.md.

## 回滚触发器

| 阶段 | 触发阈值 | 立即动作 | 恢复条件 |
|---|---|---|---|
| 金丝雀 | `rights_confidence <0.960` OR `term_adherence <0.940` OR `av_sync_ms >220` | 在受影响业务线上执行 `pause_distribution` + 回滚到最近已知良好画像 | 连续两次 QA 样本合规，且 HITL 队列完成审核签核 |
| 金丝雀 | `strike_rate >=0.50%`（近 30 天，业务线范围） | 强制 `monetization_eligibility=hard-stop`，暂停业务线分发，回滚画像 | 连续 14 天 `strike_rate <0.20%` + 明确批准 |
| 有限扩展 | 任一规范键进入 `hard-stop` 区间 OR SLO 违约持续 >3 天 | 冻结扩展，将受影响业务线回退到金丝雀体量，回滚最近发布/流程变更 | 连续 7 天稳定窗口，所有键均在 `auto-pass`，且无未解决高严重度事件 |
| 全量扩展 | 违规预算 hard-stop OR `rollback_mttr >60 min` OR 影响变现决策的未解决政策漂移 | 停止净新增扩展，关闭受影响业务线变现，收缩到已验证稳定子集，并执行回滚 | 连续 14 天稳定窗口，回退演练成功，且更新后的政策证据确认业务线合规 |

可追溯性说明：
- 以上每个关键决策都已链接到 `.sisyphus/research/` 下的任务 1-5 产物，支持确定性审计检查。
