# SCRIPT GENERATION KNOWLEDGE BASE

## OVERVIEW
This directory materializes summary/prompt/script packs and applies originality + policy gates.

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Main pipeline | `pipeline.py` | normalization, pack construction, persistence, gating |
| Originality math | `originality.py` | similarity scoring and trace IDs |
| Pack schemas | `schemas.py` | strict field/type validation and errors |
| Scenario validator | `validate_task3.py` | evidence-producing scenarios for gate behavior |

## CONVENTIONS
- Input segment lists must satisfy minimum-length and timing invariants before pack generation.
- Summary/prompt pack validation failures should raise explicit typed errors.
- Keep prompt output deterministic (stable IDs, predictable ordering, stable JSON formatting).
- Threshold-driven checks (factual quality, ambiguity, policy violations) are first-class contract behavior.

## ANTI-PATTERNS
- Do not bypass schema validation when writing summary/prompt artifacts.
- Do not lower originality/policy thresholds implicitly per callsite.
- Do not write artifacts outside expected artifact/evidence roots.
- Do not couple prompt generation to platform-specific publishing concerns.
