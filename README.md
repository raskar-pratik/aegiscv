# Veyra

Computer Vision Integrity Assurance — an offline AI-security analyst workstation.

> **Rebranding note:** Veyra was previously named AegisCV. Historical audit records, frozen experiment results, benchmark identifiers, and environment variable names (e.g. `AEGISCV_STATE`, `AEGISCV_ENCODER`) retain the original naming for compatibility and traceability.

A local analyst application for inspecting image datasets, model identities, inference lineage and audit history. It produces evidence, heuristic risk, confidence, severity, recommended action and explicit coverage gaps. No cloud APIs, downloaded weights, CDN assets or runtime network services are used.

## Install dependencies

For an internet-connected development machine, install dependencies before running:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-models.txt
```

For an air-gapped machine, use the offline installation instructions below. The application does not fetch models at runtime.

## Start here

From this directory, with the installed Python environment:

```powershell
python run.py
```

Open http://127.0.0.1:26228 and click **Run reproducible demonstration**. The demo creates its own synthetic clean/attacked images and local TorchScript models, executes real scans, signs an inference, and verifies tampered copies and replay attempts. Reports persist across restarts.

```powershell
python -m unittest discover -s tests -v
python -m demo.runner --output demo/results-new
```

The standalone demo output directory must be new. Seeded image bytes and model behavior are reproducible; UUIDs, signing keys, timestamps and TorchScript container bytes can differ between executions.

## Implemented MVP

- Folder/classification, COCO and YOLO ingestion; validated image/annotation handling; SHA-256 manifest including annotations and contributor metadata.
- Exact duplicate groups and dHash candidates with calibrated pixel/texture confirmation and explicit confirmed edges.
- Embedding neighbor label disagreement; OOD relative to a supplied reference; contributor risk and evidence correlation.
- PyTorch safe state dictionaries with local architecture factories, TorchScript runtime and optional ONNX Runtime adapter. Access-aware unavailable states.
- Model byte fingerprint, fixed behavioral probe battery, substitution comparison and bounded classification trigger inversion with MAD statistics.
- Inference execution binding input, model, preprocessing, configuration and output hashes; Ed25519 signatures.
- Transactional SQLite hash-chain ledger; persistent nonce/sequence/freshness replay checks; independent verification and trusted checkpoint support.
- Distribution feature comparison, heuristic risk fusion, local background scans, dashboard, JSON and printable HTML reports.
- Seeded attack simulator and executable synthetic precision/recall/F1/false-positive measurements.

## Offline installation

Core dependencies are listed in `requirements.txt`; optional model runtimes are in `requirements-models.txt`. Prepare wheels matching the target Python version and OS on your provisioning machine, transfer them through your approved process, and install without accessing a package index:

```powershell
python -m pip install --no-index --find-links X:\wheelhouse -r requirements.txt
python -m pip install --no-index --find-links X:\wheelhouse -r requirements-models.txt
```

Alternatively use `scripts/setup_offline.ps1 -Wheelhouse X:\wheelhouse`. Nothing in this repository fetches a model or package automatically. The current environment has NumPy, Pillow, Flask, cryptography and CPU PyTorch; ONNX Runtime is absent. Python 3.14 emits TorchScript compatibility warnings despite passing exercised tests; use a supported, validated Python/PyTorch combination for deployment.

## Own datasets and models

Place inputs inside `local_state/imports/` and enter relative paths in **New scan**. Set `AEGISCV_STATE` to select a different local state directory before starting. The browser API confines all input paths to its `imports/` subtree. There is no archive extraction or file-upload endpoint.

- Folder: `dataset/class_name/image.png`; root images can be unlabeled.
- COCO: `dataset/annotations.json` and referenced images within the same dataset directory.
- YOLO: `dataset/images/...` plus matching `dataset/labels/...txt`, or sibling image/text files. Class IDs are preserved.
- Contributors: optional `contributors.json` mapping relative image paths to contributor/source names.
- Reference: a separate trusted clean dataset in the same annotation format.
- Models: register in **Models**, explicitly acknowledge trust for executable local artifacts, then paste the returned model ID into the scan/inference form. The default probe/input convention is RGB, 32×32, NCHW, float32 scaled by 1/255. Other conventions require an adapter integration; incompatible outputs become visible failed findings.

The Python API accepts `LocalModelEncoder` for supplied feature models and a `factory` for safe PyTorch state dictionaries. See `docs/architecture.md`.

## Scientific and operational limits

An optional ResNet18 penultimate encoder loads an operator-supplied local state dictionary only. Configure `Config(encoder_weights='local-resnet18.pt')` in Python or `config.encoder_weights` as an import-relative path in the scan API. No weights are bundled or downloaded. Without usable weights the handcrafted encoder remains available, and `encoder_capability` explicitly reports FALLBACK. Embeddings are cached by image SHA-256 plus encoder weights/preprocessing/configuration identity. Semantic performance gains remain unmeasured until a trusted pretrained checkpoint and representative evaluation data are supplied. The OOD default of 0.20 remains an uncalibrated visual-feature heuristic.

COCO/YOLO annotation checks now cover geometry, duplicate/conflicting annotations, box counts, class frequencies and contributor evidence. Semantic label anomaly analysis remains whole-image and singly labeled. Spectral signatures and optional penultimate activation clustering provide additional heuristic evidence. Spectral recall on the current handcrafted image fixtures is limited: 33% for label flips and 25% for triggers in the recorded experiment.

Trigger inversion now uses multiple initializations, adaptive mask regularization, non-target sources and held-out reconstruction success. The new six-class validation fixture demonstrates a real backdoor with measured clean accuracy/ASR and recovered mask/pattern evidence. This does **not** establish general backdoor detection reliability. The original thresholded three-class model remains a limited-search case; complementary corner-patch behavioral evidence and byte/probe identities remain available. See `docs/hardening.md` for the diagnosis, measured results and limitations.

## ML security hardening experiments

```powershell
python -m experiments.hardening
# Optional: repeat with your own locally provisioned pretrained checkpoint
python -m experiments.hardening --weights local-resnet18.pt --output experiments/results/semantic-evaluation
```

Results are written as JSON, CSV and Markdown under `experiments/results/hardening/`. Undefined metrics remain null/N/A. Recovered masks, patterns, model artifacts and measured clean accuracy/ASR are under `backdoor_validation/`. The existing one-click demo also executes this validation fixture and includes its measured summary in the audit/demo results.

Distribution reports now expose centroid displacement, covariance difference, RBF MMD, class-frequency TV and optional prediction-confidence change. Each metric has its own threshold and lists whether it triggered. Correlation rules retain underlying finding IDs; matching dataset/model targets requires an explicit `class_names` mapping. Optional activation analysis is enabled with `activation_analysis: true` on model scans; inaccessible penultimate features are reported as UNAVAILABLE.

A risk score is not an attack probability. Synthetic experiment metrics are not benchmark/generalization claims. `ACCEPT` means the executed checks found no configured issue; it does not establish absence of unknown attacks. Missing tests lower confidence and require review.

The server is a loopback-only hackathon application, not a multi-user production service. Local signing-key access is a trust boundary; signatures cannot protect against an attacker controlling the signer and its keys. Independent public-key pinning and ledger checkpoints are required for meaningful external verification and truncation detection.

## Benchmarking and scientific validation

Run `python -m experiments.final_validation` using the installed offline dependencies. This produces `experiments/results/final_validation/VALIDATION_REPORT.md`, detector-specific JSON/CSV metrics, split/asset hashes, frozen calibration, attack configurations, failure examples, model robustness evidence, and runtime/environment records. The procedural ten-class benchmark has 200 training, 200 reference, 200 calibration and 300 held-out images. Only label disagreement and OOD thresholds are calibrated for this generated benchmark; application defaults remain unchanged. Use `core.thresholds.apply_profile` to validate an encoder-bound profile before explicitly applying it.

The original six-class backdoor experiment is preserved. Additional locally trained tiny models exercise 1/5/10/20% poisoned training, multiple seeds, targets and patch geometries with fixed inversion settings. Results can include missed attacks and clean-model false positives; no overall “Veyra accuracy” is reported.

For a trusted local semantic checkpoint, follow `docs/checkpoint_provisioning.md`. `AEGISCV_ENCODER`, `AEGISCV_ENCODER_WEIGHTS` and optional `AEGISCV_ENCODER_SHA256` configure offline loading. The semantic ablation requires a checksum pin and records operator-supplied provenance limitations. No model or dataset is downloaded.

## Reliability stabilization

Run `python -m experiments.stabilization` for calibration-only duplicate diagnosis, frozen acquisition statistics, the complete regression matrix, and held-out transformed-copy measurements. Results are under `experiments/results/stabilization`; the prior `final_validation` results remain the before snapshot. The source of current detector and risk policy is `docs/detectors.md`. The dashboard and architecture are unchanged.

With the local dashboard running, `python scripts/verify_freeze.py` executes all tests and the browser regression, checks the measured freeze criteria, and writes an explicit YES/NO freeze record. No download is performed when an optional runtime is absent. Scores use a new fixed denominator and are not directly comparable as attack probabilities. Retained failures include backdoor misses/false positives and ambiguous contributor attribution for duplicate originals.

## Judge-facing decision contract

The scanner preserves composite pipeline risk and adds a separate decision contract: maximum asset risk, highest-risk asset and reason, confidence/coverage, final disposition and a structured disposition trigger. This prevents a low diluted composite score from masking a decisive contributor or cryptographic violation. See `docs/decision_policy.md` and `docs/assurance_schema.md`. Existing dashboard visuals and detector metrics are unchanged.

## Architecture and project structure

`app/` contains REST routes, background orchestration and SQLite persistence. `adapters/` contains dataset/model integration. `detectors/` contains independent data, model and drift modules. `core/` defines configuration, findings, risk and coverage. `provenance/` handles signatures, records and verification. `dashboard/` provides local HTML/CSS/JS. `reports/`, `attack_simulator/`, `demo/`, `tests/`, `scripts/`, and `docs/` contain the supporting workflow.

Documentation: `docs/architecture.md`, `docs/detectors.md`, `docs/security.md`, `docs/attack_coverage.md`, `docs/demo.md`, `docs/api.md`, `docs/audit.md`.
