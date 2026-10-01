# ML security hardening

The existing application architecture, dashboard assets, provenance engine and original tests were preserved. The baseline 13 tests passed before modifications. This phase adds detector implementations through the existing adapters/orchestration.

## Inversion diagnosis

The original sparse mask started at sigmoid(-2) = 0.1192, with pattern intensity 0.5. The demonstration model's backdoor branch used `relu(corner_mean - 0.9)`. Below that threshold its gradient is zero. Starting with a mostly unchanged source therefore provided no local gradient toward the small true trigger. The original 20-step run found large ordinary class-changing masks instead: norms 576.01, 588.39 and 551.07, all with 100% probe target success, and anomaly index 1.359. Random probes included already-target samples and unrealistic white/black inputs; unsuccessful target reconstructions were also eligible for the old MAD comparison.

Changes: sparse-neutral and dense-bright restarts; clean reference source images; non-target source selection; adaptive L1 cost; smallest feasible training mask retained; separate validation success; only successful reconstructions enter robust comparison. Null MAD/anomaly values are preserved when evidence is insufficient. The default model input contract remains RGB [0,1]; normalization must be internal to the model for inversion.

The new fixture has six color prototypes and a differentiable corner trigger that causes target class 2. It is deliberately suitable for validating reconstruction, not evidence of broad robustness. On the recorded seed-26228 experiment: 36/36 clean classifications correct; 30/30 non-target triggered samples reach class 2; held-out recovered-trigger success is 100%; recovered mask norm is 13.72, median 110.11, MAD 2.89, anomaly index 22.47. The paired clean model is not flagged. Full floating-point evidence and PNG masks/patterns are in `experiments/results/hardening/backdoor_validation/`.

The original thresholded three-class model remains a bounded-search limitation; the original fixture is retained. Complementary patch behavior, byte identity and behavioral fingerprints remain distinct signals. No result is forced positive merely because a fixture is labeled compromised.

## Before versus after coverage

| Area | Before | After |
|---|---|---|
| Features | Handcrafted; generic local extension | Explicit ResNet18 local-only loader, common interface, capability/fallback and SHA/config cache |
| Spectral poisoning | Absent | Per-class dominant projections, robust ranks, percentile/source evidence |
| Inversion | Single sparse start, fixed cost, random probes | Two starts, adaptive cost, non-target clean sources, held-out recovery and feasibility-aware MAD |
| Behavioral backdoor evidence | Fixed general probes | Additional independent corner/color/size battery |
| Activations | Unavailable | Optional penultimate PCA/two-means, with graceful access failure |
| Object annotations | Basic validation; invalid COCO box could stop ingestion | Retained annotation evidence, geometry/duplicates/conflicts/frequency/source checks |
| Shift | Mean/variance differences | Centroid, covariance, MMD, class mix and optional confidence, explicit triggering metrics |
| Correlation | Generic shared contributor | Explicit spectral/label, OOD/shift, mapped target and hash/behavior rules, retained links |

## Evaluation and limitations

Run `python -m experiments.hardening`. The JSON, CSV and Markdown comparison include detector, attack, unit, benign/attack sample counts, TP/FP/TN/FN, precision, recall, F1, FPR and measured runtime. Undefined values are null/N/A. Image IDs are namespaced by clean/attacked corpus. Model- and dataset-level rows use different units explicitly; their tiny denominators must not be confused with image-level benchmark performance.

The image suite used the handcrafted FALLBACK because no pretrained weights were supplied. ResNet mechanics were tested with seeded random local weights, with download functions blocked; this does not measure pretrained quality. Spectral image recall is 33% for label flips and 25% for triggers. The controlled vector suite also exposed one spectral false positive among 195 benign representations. These failures remain in the results. The default 95th-percentile rule is conservative and limits recall for larger poison fractions. The configurable projection-energy floor avoids nearly constant-class noise amplification but can miss subtle poison.

Annotation class imbalance and minority activation clusters can be legitimate. MMD uses a bounded deterministic sample and a reference-derived bandwidth; thresholds are heuristic, not calibrated significance tests. Confidence drift uses the existing bounded sample and assumes classifier logits. Matching targets across dataset/model evidence requires operator-supplied class names. Correlated findings are not treated as statistically independent probabilities.

Embedding-cache checksums detect accidental corruption, not a malicious local operator able to rewrite both cache values and checksums. Protect local state and trusted weights with OS permissions. No network services, model downloads, CDN assets or cloud APIs were added. Optional ONNX execution remains unverified in this environment because ONNX Runtime is absent.

## Files created

- `detectors/data_integrity/encoder.py`, `resnet_encoder.py`, `spectral.py`, `annotations.py`, `trigger_pattern.py`
- `detectors/model_integrity/activation_analysis.py`, `patch_probe.py`
- `adapters/models/preprocessing.py`
- `attack_simulator/backdoor_validation.py`, `annotations.py`
- `experiments/hardening.py` and generated `experiments/results/hardening/` artifacts
- `tests/test_encoders_spectral.py`, `test_backdoor_hardening.py`, `test_annotations_activation_shift.py`, `test_correlation.py`, `test_hardening_integration.py`
- `docs/hardening.md`

## Files modified

- `detectors/data_integrity/features.py`
- `detectors/model_integrity/neural_cleanse.py`
- `detectors/distribution_shift/embedding_shift.py`
- `adapters/datasets/ingestion.py`, `adapters/models/runtime.py`
- `core/config.py`, `core/correlation.py`, `core/coverage.py`
- `app/services/scanner.py`, `app/api/routes.py`
- `reports/generator.py`, `demo/runner.py`, `requirements-models.txt`
- `README.md`, `docs/architecture.md`, `docs/api.md`, `docs/attack_coverage.md`, `docs/detectors.md`, `docs/demo.md`
- `docs/verification.md`; generated browser regression screenshots under `docs/screenshots/`

Next highest-value work: provision a trusted pretrained feature checkpoint and representative held-out clean/attacked CV dataset, then calibrate thresholds and compare semantic versus handcrafted detectors across multiple seeds and attack mechanisms. More synthetic feature availability is not a substitute for that evaluation.
