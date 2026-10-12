# AegisCV final security assessment

> **Historical Record Note (2026-10-12):** This document records the security assessment conducted on 2026-09-11 for AegisCV. The project has since been rebranded to Veyra.

**Assessment date:** 2026-09-11  
**Scope:** local AegisCV source tree and the operator-owned loopback service at `http://127.0.0.1:26228`.  
**Authorization:** explicitly authorized by the project owner; non-destructive validation only.

## Method and tooling

- Reviewed the Ponytail and Ponytail Audit skills and applied the YAGNI/minimal-diff ladder to the application, adapters, provenance, reports, and dashboard.
- Reviewed the Strix application-security and web-penetration-testing skills. The `strix` executable is not installed and no cloud execution or network access was attempted. Local static and black-box checks below are the documented fallback.
- Read the request boundary, path confinement, model loading, provenance, ledger, dashboard escaping, and security-header code before testing.
- Ran the existing 50-test unittest suite and the Playwright browser regression with external-request blocking.

## Ponytail review

The codebase already has the smallest safe boundaries for this MVP. `confined()` is shared by all import paths; `ModelAdapter` is the single model-loading boundary; `Ledger` owns signing, sequencing, and replay state. The two dashboard scripts and the CSS overlay look duplicative, but they are intentional compatibility/presentation layers: `app.js` owns existing event wiring and `workstation.js` owns the judge-facing render overrides. Merging them during freeze would increase regression risk. The base render helpers that are overridden remain referenced by the legacy contract and were left unchanged.

**Findings:** no high-confidence dead code or safe security simplification identified.  
**Code removed/simplified:** none. The only change in this assessment is the browser smoke selector updated for the already-shipped “Demonstration Console” label.

## Security test scope and results

| Surface | Checks | Result |
|---|---|---|
| Web/API | loopback health, wrong method, missing token, wrong Origin, malformed JSON, malformed ledger shape | expected 200/400/403/405 responses; no 5xx or stack trace |
| Paths/files | `../` traversal on dataset/model/scan/asset paths, absolute path confinement, extension gate | rejected with 400; resolved paths stay under `local_state/imports` |
| Browser/XSS | Playwright page errors, external request interception, escaped dynamic evidence/report fields | zero browser errors; zero external requests; dynamic values use `esc()` before HTML insertion |
| Headers | CSP, `X-Content-Type-Options` on HTML and API responses | present; report HTML uses a stricter no-script policy |
| Model loading | ONNX CPU-only path, explicit trust acknowledgement, TorchScript identity recheck, PyTorch `weights_only=True`, finite output checks | covered by tests; no network/model download path |
| Crypto/provenance | Ed25519 signatures, hash chain, tamper, checkpoint, nonce/sequence replay and restart persistence | covered by tests and browser flow; tampering/replay rejected |

The malformed JSON response is Flask's generic 400 page, with no application detail or traceback. Unsupported model runtimes fail closed and expose an `UNSUPPORTED`/`UNKNOWN` evidence state rather than inventing a pass.

## Confirmed findings

No exploitable HIGH or CRITICAL finding was confirmed in the authorized scope. No code fix was required.

## False positives / not applicable

- `send_file` is reachable only after `local_path()` confinement and an allow-listed image suffix.
- `torch.jit.load` is not an arbitrary remote loader: model registration requires a local path and explicit operator trust. It remains a trust-boundary risk for untrusted TorchScript files (see residual risks).
- The visible `26228` in localhost URLs and seeded test data is not product UI branding; `rg -n -i "SIH|26228|Smart India Hackathon|hackathon" dashboard` returns zero matches.

## Residual risks and limitations

- The signing private key is locally generated and stored as a raw Ed25519 key under `local_state/provenance/keys`; filesystem access to the host can compromise signing. Protect the state directory and provision an external keystore for production.
- TorchScript/ONNX execution is intentionally operator-trusted local code/data. Use a sandboxed worker and signed model allow-list before processing third-party models in a hostile environment.
- The service is loopback-only and has no production identity/access-control layer. Do not expose it beyond the analyst workstation without deployment hardening.
- A hash chain cannot detect suffix deletion without an independently retained checkpoint; the verifier reports this limitation.
- Strix CLI/cloud execution was unavailable in this air-gapped environment, so this report is not a Strix-generated pentest certificate.

## Offline and frozen-contract verification

All runtime dependencies are local (`numpy`, Pillow, Flask, cryptography; optional model runtimes remain optional). Browser interception recorded zero external requests. Frozen decision-contract artifacts remain unchanged: clean `11.36 / LOW / REVIEW`, malicious contributor `12.5` composite with `100` maximum asset risk and `QUARANTINE`, and the preserved experimental/cryptographic dispositions.

Screenshots from the verified browser run are in [`docs/screenshots`](../screenshots/), including overview, tampered inference, tampered ledger, and demonstration console states.

## Judge-facing security summary

AegisCV runs air-gapped on loopback, confines imported files, verifies SHA-256 identities, signs inference records with Ed25519, rejects nonce/sequence replays, and verifies a tamper-evident ledger. Evidence is explicit when a detector is unavailable. In the final local regression, all 50 tests passed, the browser flow passed with zero external requests, and the frozen decision contract was preserved.
