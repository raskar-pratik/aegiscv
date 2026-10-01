# Judge-facing decision contract freeze

The assurance report exposes two different concepts. `composite_risk` is the fixed-denominator cross-domain heuristic aggregate and is explicitly not an attack probability. `max_asset_risk` is the highest applicable sample, contributor, model, inference, ledger, or distribution risk. `confidence` and `coverage` describe how much of the configured assessment completed; unavailable checks do not reduce composite risk.

`final_disposition` is selected by a conservative policy layered over the unchanged composite formula:

1. Verified signature, model identity, inference, or ledger integrity failure produces `QUARANTINE`.
2. A contributor with risk at least 80 and at least two independent evidence families produces `QUARANTINE`.
3. Strong experimental backdoor-like evidence produces `REVIEW`; it never claims cryptographic confirmation.
4. Moderate calibrated anomalies produce `REVIEW`.
5. Otherwise the composite action is retained (`ACCEPT`, `REVIEW`, or `QUARANTINE`).

Reports also expose `composite_severity`, `highest_severity`, `highest_risk_asset`, `highest_risk_asset_type`, `highest_risk_reason`, and `disposition_trigger`. The trigger records why the final disposition was selected. It is evidence metadata, not a proof of attacker intent.

The malicious-contributor control intentionally demonstrates the distinction: composite risk can remain 12.5 while maximum contributor risk is 100 and final disposition is `QUARANTINE`. A clean control remains LOW/REVIEW because its residual calibrated OOD findings are not special-cased away.
