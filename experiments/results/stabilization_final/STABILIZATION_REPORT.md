# Reliability stabilization and demo freeze

## Quantitative root causes

See pair_diagnosis.json: dHash and color gates lose image-specific texture; connected components imply unsupported transitive links. Pair truth is now separate from image/cluster membership truth. Calibration uses 19,900 independent negatives and 1,200 transformed-copy positives, with no held-out features used for selection.

## Before versus after

|Metric|Before|After|
|---|---|---|
|Near clean image FPR|0.67|0.0|
|Near precision|0.42857142857142855|1.0|
|Near recall|1.0|1.0|
|Near F1|0.6|1.0|
|Clean contributors falsely flagged|5|0|
|Clean risk|80.0|11.36|
|Malicious contributor case risk|95.0|12.5|
|Backdoor fixture risk|85.0|13.09|
|OOD case risk|97.5|34.09|

## Held-out transformed copies

{"resize": {"tp": 300, "fn": 0}, "jpeg": {"tp": 300, "fn": 0}, "brightness": {"tp": 300, "fn": 0}, "crop_pad": {"tp": 300, "fn": 0}, "noise": {"tp": 300, "fn": 0}, "reencode": {"tp": 300, "fn": 0}}

Pair FPR 0.0; image FPR 0.0; copy recall 1.0. No thresholds were changed after this evaluation.

## Risk policy and contributor reliability

Fixed-denominator weighted sum of reliability-adjusted category maxima (weights 1,1.2,1.2,1 by default; denominator 4.4). Verified model/ledger violations force risk 100. Unavailable checks only change confidence/coverage. Experimental evidence remains visible and may require REVIEW.
Quality multipliers: {"VERIFIED_MECHANICAL": 1.0, "CALIBRATED": 1.0, "HEURISTIC": 0.6, "VALIDATED_EXPERIMENTAL": 0.35, "EXPERIMENTAL": 0.2, "UNAVAILABLE": 0.0}. Multipliers are conservative policy choices, not empirical probabilities. Contributor scores group related representation and duplication evidence, use affected fraction, confidence and quality, and preserve every finding. A fixed denominator changes the numerical scale relative to the prior active-category mean.

## Clean control

Risk 11.36, LOW, REVIEW. Positive findings remain visible in comparison.json; residual OOD false alarms are not hidden.

## Operational drift

{
  "profile_hash": "e0676f7f9fc2994d8de77d17b60f4b9bbd634fc2104755abb3b19fb153da12f1",
  "mean_luminance_delta": -0.1624565882850797,
  "luminance_calibration_sd_units": 19.6194164494155,
  "luminance_shift_direction": "darker",
  "median_sharpness_relative_change": -0.9345516572757676,
  "luminance_threshold": 0.03409164598268991,
  "sharpness_relative_threshold": 0.2,
  "reference_means": [
    0.458820864250153,
    0.04694238804308202,
    0.014307659094183633,
    0.4589831495098039,
    0.45876313572303906,
    0.4589148475796567
  ],
  "current_means": [
    0.29636427596507325,
    0.025418499295312254,
    0.0009393861094435728,
    0.2963043172998375,
    0.29637502553104655,
    0.2964343469158504
  ],
  "features": [
    "luminance",
    "luminance_std",
    "laplacian_energy",
    "red_mean",
    "green_mean",
    "blue_mean"
  ],
  "intent": "Not determined; acquisition change alone is not attack evidence"
}

Acquisition changes are described as OPERATIONAL DISTRIBUTION SHIFT DETECTED, with no attribution of malicious intent. Embedding thresholds were not lowered. Correlation requires separate suspicious evidence.

## Backdoor limitations

Before: TP 5, FP 1, TN 2, FN 1. After: TP 5, FP 1, TN 2, FN 1.
[
  {
    "model": "evaluation-7-0.1-top_left-4-0",
    "clean_accuracy": 1.0,
    "ASR": 1.0,
    "anomaly_index": 1.2596615953029688,
    "raw_detected": false,
    "assessment": {
      "verdict": "NO_QUALIFYING_EVIDENCE",
      "reconstruction_anomaly": false,
      "held_out_recovery": true,
      "matching_behavioral_confirmation": false,
      "recommended_action": "ACCEPT",
      "limitations": "Not a confirmed-backdoor verdict. Negative evidence does not prove absence; patch and reconstruction probes are complementary but not statistically independent."
    },
    "diagnosis": "High-ASR backdoor lacks a sufficiently exceptional recovered mask; optimization/MAD comparison is a sensitivity limitation."
  },
  {
    "model": "evaluation-19-0-top_right-3-3",
    "clean_accuracy": 1.0,
    "ASR": 0.0,
    "anomaly_index": 2.363509923091567,
    "raw_detected": true,
    "assessment": {
      "verdict": "SUSPICIOUS_EVIDENCE",
      "reconstruction_anomaly": true,
      "held_out_recovery": true,
      "matching_behavioral_confirmation": false,
      "recommended_action": "REVIEW",
      "limitations": "Not a confirmed-backdoor verdict. Negative evidence does not prove absence; patch and reconstruction probes are complementary but not statistically independent."
    },
    "diagnosis": "Relative small-mask outlier on a clean classifier does not establish poisoning."
  }
]

No inversion threshold was tuned to either failure. Reconstruction evidence, held-out recovery and matching behavioral patch confirmation are reported separately. None is labeled a confirmed backdoor.

## Reproduce

```powershell
python -m experiments.stabilization
python -m unittest discover -s tests -v
python run.py
# Separate terminal, local Edge/Playwright already installed:
python scripts/browser_check.py
```

The original final_validation artifacts are retained. Full after results are under full_suite/. Freeze remains pending until final test/browser verification is appended.

## Remaining limitations

- Generated-domain calibration is not a natural-image operating guarantee.
- The same held-out benchmark was used across phases; report this as regression validation, not a fresh external generalization estimate.
- Raw backdoor false positives and false negatives remain; strong evidence is still an analyst REVIEW.
- Fixed-denominator risk intentionally changes score scale; no attack-probability interpretation.
- Pair recall does not imply that all transitive cluster pairs were confirmed.

## Final freeze verification

DEMO FREEZE: YES

{
  "gates": {
    "clean_not_high_critical": true,
    "near_false_positives_reduced": true,
    "benign_sources_not_universally_flagged": true,
    "monotonic_properties": true,
    "interpretable_operational_drift": true,
    "cryptographic_checks": true,
    "full_suite": true,
    "browser_regression": true,
    "zero_observed_external_requests": true
  },
  "demo_freeze": "YES",
  "test_exit_code": 0,
  "browser_exit_code": 0,
  "browser": {
    "browser_errors": [],
    "external_requests": [],
    "demo": "complete",
    "ledger": "VALID",
    "screenshots": "docs\\screenshots"
  },
  "runtime_seconds": 31.035399000000325,
  "observation_scope": "Python socket/DNS guard during full experiment and application-page browser request interception; not OS-wide packet capture"
}


## Final artifact set

This directory was assembled after the complete stabilization rerun and final freeze verification. It does not overwrite `final_validation/` or the prior `stabilization/` history. Required machine-readable artifacts are listed in `summary.json`, and exact before/after rows are in `before_after.csv`.

DEMO FREEZE: YES. All nine freeze gates passed. Full test execution passed 41 tests (25 previous plus 16 stabilization/validation tests); no tests were skipped. Browser regression had zero page errors and zero external requests.


## Decision contract freeze

The scanner and HTML generator now expose composite pipeline risk separately from maximum asset risk and final disposition. The contract examples in decision_contract.json show clean control, malicious contributor, verified substitution, and experimental backdoor semantics. Composite values and detector metrics remain unchanged; decisive evidence is handled only by the disposition policy.


## Decision contract verification

The final scanner smoke test confirms JSON and HTML expose the contract fields. Malicious contributor evidence produces a QUARANTINE disposition despite a low composite score; clean OOD evidence remains LOW/REVIEW; verified model substitution produces QUARANTINE; experimental backdoor-only evidence produces REVIEW with an explicit non-confirmatory trigger. The browser smoke test now binds to the model-registration POST response, avoiding a GET/POST race.
