# POLICY CONTRACT KNOWLEDGE BASE

## OVERVIEW
`locale_compliance_policy.json` is the authoritative locale policy + originality threshold contract consumed by runtime gates.

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Canonical policy schema | `locale_compliance_policy.json` | supported locales, result/violation codes, per-locale blocks |
| Runtime usage in script generation | `../../src/money/script_generation/pipeline.py` | originality threshold loading |
| Runtime usage in localization gate | `../../src/money/localization/policy_gate.py` | category-based allow/block mapping |

## CONVENTIONS
- Maintain stable code vocab: `result_codes`, `violation_codes`, `reason_codes`.
- Update `policy_version` when semantic rule changes are introduced.
- Keep locale keys and reason mappings explicit and complete.

## ANTI-PATTERNS
- Do not add locale-specific free-text behavior without machine-readable codes.
- Do not remove a reason code referenced by runtime services/tests without coordinated updates.
- Do not store environment-specific values in this policy contract.
