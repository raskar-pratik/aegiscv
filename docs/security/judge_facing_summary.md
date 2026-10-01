# Judge-facing security summary

AegisCV is an air-gapped, loopback-only integrity workstation. It confines imported paths, fingerprints models and assets with SHA-256, signs inference provenance with Ed25519, blocks replayed records, and verifies a hash-chain ledger. Detector gaps remain visible as `UNKNOWN`/`UNAVAILABLE`; they are never presented as passes.

The final local regression passed all 50 tests and the browser demonstration with zero external requests. Frozen decision values remain intact, including clean `11.36 / LOW / REVIEW` and malicious-contributor `12.5` composite with `100` maximum asset risk and `QUARANTINE`.
