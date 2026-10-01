# Coverage

The dashboard's coverage matrix is sourced from `core/coverage.py`; individual reports also contain executed statuses.

Implemented deterministic integrity checks: exact-byte duplication, trusted model digest mismatch, inference content/signature alteration, replay acceptance, historical hash-chain alteration and checkpoint-based truncation checks.

Heuristic/partial checks: near duplicates, label anomalies, reference OOD, contributor attribution, behavioral changes and distribution shift. A model can change benignly; a behavior change does not prove malicious intent.

Research: bounded classification trigger reconstruction with gradients. Current demo reconstruction may miss the compromised model. No detection accuracy claim is made. Black-box runtimes report reconstruction UNAVAILABLE and continue behavioral/identity tests.

Added in hardening: local ResNet18 features with explicit fallback/cache, spectral anomaly ranking, repeated corner-pattern evidence, optional penultimate PCA/two-means clustering, COCO/YOLO annotation integrity, five distribution metrics and linked cross-layer rules. The new controlled validation model is detected by reconstruction and patch response; the original limited-search case is not presented as solved universally.

Still outside coverage: general backdoor detection guarantees, semantic object-level poisoning, broad trigger-family coverage and reliable attribution of environmental versus malicious drift. A pretrained semantic checkpoint is not bundled. Spectral recall on handcrafted image fixtures is only 25–33%; consult the measured comparison rather than treating feature availability as detection quality.
