# Local API

All endpoints start with `/api`. POST requires JSON and `X-Aegis-Token` from the dashboard's `aegis-token` meta tag. Run from the same loopback origin. File paths are relative to the runtime `imports/` directory.

| Endpoint | Input / result |
|---|---|
| GET /health | Offline status |
| POST /datasets | `{path,format}`; validated manifest and ID |
| GET /datasets, /datasets/{id} | Registered datasets |
| POST /models | `{path,format,trusted}`; fingerprint/access and ID |
| GET /models, /models/{id} | Registered models |
| POST /scans | `{path,format,reference,model_id,expected_hash,reconstruct,config}`; queued job ID |
| GET /scans, /scans/{id} | Status and persisted assessment |
| GET /findings, /findings/{id} | Evidence findings |
| GET /reports/{job_id} | Report JSON; `?format=html` for printable HTML |
| POST /inference | `{model_id,image}`; executes and signs local inference |
| POST /inference/verify | `{record,bindings?}`; signature/content check; optional trusted hash bindings |
| POST /inference/accept | `{record}`; persistent freshness/replay acceptance |
| GET /ledger | Records and local public key |
| POST /ledger/verify | `{records?,checkpoint?}`; verify provided copy or live ledger |
| GET /coverage | Capability declarations |
| POST /demo | `{}`; queues reproducible demonstration |
| GET /demo/results | Latest actual verification and synthetic metrics |

Report `scan_id` identifies the signed assessment; the API job ID identifies its orchestration entry. They are separate identifiers. Artifacts on disk use the assessment ID.

Independent verification: export a record/ledger JSON and pin the public key through a trusted channel, then run `python -m provenance.verifier artifact.json --public-key trusted_public_key.txt` (add `--ledger` and optional `--checkpoint checkpoint.json`). This validates integrity, not consumer freshness; use the persistent acceptance API for replay prevention.

Hardening scan options: `config.encoder_weights` is resolved inside imports; `config.encoder_batch_size` controls local ResNet batches. Missing/incompatible weights cause an explicit handcrafted FALLBACK, not a download. `config.spectral_*`, `config.shift_*` and `config.annotation_*` configure detector thresholds. `activation_analysis: true` enables optional contributed-model penultimate clustering. `reference_behavior` accepts a trusted behavioral baseline; `class_names` maps output indices to dataset labels for target correlation. Do not supply an untrusted baseline as a trust anchor. Confidence/inversion/activation input processing retains the existing RGB 32×32 convention and a 96-image bound.
