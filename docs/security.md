# Security boundaries

No cloud APIs, external frontend assets, model downloads or runtime package installation. Server binds to loopback. Browser mutation requests require a random per-process token and same-origin checks; trusted Host validation mitigates DNS rebinding. JSON body size is limited. Input paths are resolved and confined to `imports/`, including symlink resolution. No archive extraction or arbitrary file-write API exists. HTML evidence is escaped and the dashboard uses a restrictive CSP.

Executable models must be explicitly trusted locally. TorchScript/ONNX runtimes are native-code trust boundaries; no claim of safe sandbox execution. PyTorch uses `weights_only=True`, never unsafe pickle fallback. Large or adversarial model artifacts still require OS isolation/resource controls in a hardened deployment.

Private Ed25519 keys are generated under the local runtime state, excluded from source control, and created with mode 0600 where supported. Windows operators must restrict the state directory ACL to the intended account; POSIX mode bits do not substitute for Windows ACLs. Do not ship the local runtime signing key as a reusable identity.

Canonical JSON rejects nonfinite numbers. The signature binds the entire record envelope, payload, record ID, timestamp, nonce, sequence and prior hash. Inference payload binds the exact raw input bytes, model bytes, preprocessing, configuration and output. Verification requires an independently trusted public key; accepting the key from an untrusted record is unsafe.

Offline signature validation is distinct from freshness acceptance. `/inference/accept` persists nonce, record ID and monotonic sequence state, with a five-minute freshness window and 30-second future-clock allowance. Sequence gaps are allowed by the consumer; repeated or older sequences are rejected. Full-ledger verification separately requires contiguous sequence numbers.

An attacker rewriting history without the key breaks verification. An attacker holding the key can forge future entries; OS compromise is outside this MVP trust boundary. A valid ledger suffix can be removed undetectably without an independent checkpoint. Retain `{count,head}` from a trusted verification result outside the ledger and provide it to the verifier.

The SQLite ledger is application-append-only and tamper-evident, not hardware immutable. Local scans and reports are bound by a signed report hash in the audit entry. Full-file loss, disk rollback, malicious signing processes and multi-user authentication need additional operational controls.
