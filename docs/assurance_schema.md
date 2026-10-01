# Assurance report contract

Every scan JSON report contains the legacy `assurance` object plus these judge-facing fields:

| Field | Meaning |
|---|---|
| `composite_risk` | Fixed-denominator heuristic cross-domain risk; not an attack probability |
| `composite_severity` | Severity band derived from `composite_risk` |
| `max_asset_risk` | Maximum applicable sample/contributor/model/inference/ledger/distribution risk |
| `highest_severity` | Severity band for `max_asset_risk` |
| `highest_risk_asset` | Asset, contributor, model identity, or ledger selected as maximum |
| `highest_risk_asset_type` | `IMAGE`, `CONTRIBUTOR`, `MODEL`, `LEDGER`, `DATASET`, or `FINDING` |
| `highest_risk_reason` | Evidence reason associated with the maximum |
| `final_disposition` | Conservative policy result: `ACCEPT`, `REVIEW`, or `QUARANTINE` |
| `disposition_trigger` | Structured policy rule, asset, risk and evidence families |
| `confidence` | Coverage-adjusted detector confidence, not probability of safety |
| `coverage` | Fraction of detector families that completed successfully |

HTML reports render the same decision contract before the detailed findings. The original `assurance.risk_score` and `assurance.recommended_action` remain available for backward compatibility.
