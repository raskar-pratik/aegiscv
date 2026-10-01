# Verification performed

2026-09-09, local Windows / Python 3.14 environment.

- `python -m unittest discover -s tests -v`: 13 tests passed. Includes dataset adapters/manifests/path confinement, seeded attacks, near duplicates with different bytes, safe PyTorch loading, ONNX unavailable handling, model identity and behavior, signed inference, modified output, persistent replay, concurrent ledger appends, historical tampering, truncation checkpoint, invalid-ledger report preservation, API security and complete demo.
- `python scripts/browser_check.py`: passed using preinstalled Playwright and Edge. Real demo from UI, report rendering, coverage, live ledger verification, model registration, inference signing, signature verification, second acceptance rejected as replay, manually changed output rejected as tampered. Zero observed page JavaScript/console errors; zero observed external page requests. Browser routing blocked non-loopback page requests.
- `python -m provenance.verifier ...`: exported record and ledger independently verified VALID against exported public key; trusted checkpoint matched the exported ledger.
- Dashboard, ledger, coverage and inference screenshots are in `docs/screenshots/`.

During development, tests found and fixed an OOD threshold mismatch on the synthetic fixture, unclosed SQLite connections on Windows, premature COMPLETE publication, and risk dilution of verified integrity failures. The scan also preserves an assessment if the existing audit chain is invalid, rather than failing while trying to append.

No external benchmark accuracy or production throughput claim. ONNX execution is not verified because its optional runtime is absent. TorchScript runs with Python 3.14 compatibility warnings. Bounded trigger inversion did not flag the injected compromised demo model; byte identity and behavioral comparison detected the change. Default embeddings are handcrafted visual features.

## ML hardening verification

The original 13 tests passed before this phase. The complete expanded suite now passes 25 tests, including the unchanged original tests, local ResNet mechanics without downloads, fallback, actual weight/image/config cache invalidation, spectral mechanics, measured clean accuracy and ASR, recovered triggers, clean-model negative control, annotations, activation access/clustering, shift metrics, correlation links and scanner integration.

The existing Playwright/Edge browser regression also passes: demo, coverage, signed inference, manual output tampering, replay and valid ledger. Zero observed browser errors and zero external page requests. No dashboard assets were redesigned. The controlled experiment suite produced 13 measured comparison rows in `experiments/results/hardening/`; all weak spectral results and false positives remain recorded. See `docs/hardening.md` for the before/after diagnosis and scientific limits.
