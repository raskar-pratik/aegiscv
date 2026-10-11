# Phase 6 audit — before implementation (2026-10-11)

Approved Phase 5 checkpoint: 78aaf96. Documentation reconciliation completed before application edits. Reviewed template, both JS owners, all existing app stylesheets, provenance/ledger.py, provenance/inference_record.py, API routes and API/provenance tests.

## Ownership and stable selectors

- app.js owns fetch with local POST token, form serialization and generation callback. workstation.js overrides renderProvenance/renderLedger and verify/accept/ledger click handlers. No third renderer owner.
- IDs preserved: inference, inference-workspace, inference-form, inference-list, record-json, verify-record, accept-record, inference-result, inference-assessment, provenance-chain; ledger, verify-ledger, tamper-ledger, ledger-state, ledger-count, ledger-chain, ledger-list, ledger-result, ledger-assessment, demo-results.
- Inference form names model_id/image, required labels, submission endpoint and action order unchanged. Shared copy handler uses exact data-copy. Navigation/show/display remain frozen.
- Existing generation: POST /inference, populate record-json, render unverified record, refresh inventories. Verification POST /inference/verify {record}; acceptance POST /inference/accept {record}. Acceptance is never automatic.
- Ledger action: GET /ledger, deep-copy; demo changes only records[max(0,length-3)].record_hash to 'altered'; POST /ledger/verify with copied ledger for demo or {} for ordinary verification. No stored ledger mutation.

## Actual schema and semantics

Signed record: record_id, kind, payload, timestamp, nonce, sequence_number, previous_record_hash, record_hash, signature. Inference payload: input_hash, model_hash, preprocessing and preprocessing_hash, config and config_hash, output and output_hash. No model registry ID/input path, per-stage verifier result, observed/expected failure pair or backend REJECT field is returned.

verify_record returns VALID with reason, TAMPERED with actual mismatch reason, or SIGNATURE_INVALID with reason. SIGNATURE_INVALID also covers malformed metadata/structure and exceptions; it must not automatically be labeled intentional tampering. Missing JSON/request/runtime failures are client execution states, not cryptographic backend outcomes. The verifier stops at first failure; no later stage gets independent verification claims.

accept first runs verify_record. Then REPLAY can mean freshness window, stale/repeated sequence or repeated nonce/ID/sequence. Therefore REPLAY from acceptance implies preceding signature/content checks passed but policy rejected acceptance. VALID from verify does not mean accepted. VALID from accept means replay state persisted. UI action context must distinguish them without changing backend states.

GET /ledger returns records and public_key. verify_ledger returns VALID/count/head/limitation, or TAMPERED/SEQUENCE_ERROR/SIGNATURE_INVALID with optional sequence/reason. sequence is the 1-based verifier traversal position, not necessarily the untrusted stored sequence_number. A checkpoint mismatch can report len(records)+1, with no extant invalid row. Earlier traversal entries passed checks before an ordinary first failure; successors are not trusted, not independently tampered. Empty chain VALID is supported. Suffix deletion requires independently retained checkpoint evidence.

## Existing presentation risks to fix

- All non-VALID inference responses are currently called TAMPERING DETECTED; replay gets an ad-hoc override. Failures are wrongly assigned to OUTPUT/SIGNATURE based on stage index.
- Request/JSON errors leave a prior verified banner visible. Pending only disables the clicked control. In-flight responses can become stale after edits.
- Ledger treats any failure as tampering and labels later entries CHAIN INVALID without explaining trust boundary. It uses stored sequence to infer row position and retains check state when refresh fetches a different ledger, including after an altered-copy demo.
- Record content/hashes are not visible in the provenance stages; ledger copy/full details are limited.

## Allowed presentation changes

Keep exact API paths/payloads and demo mutation. Introduce separate UI pending/error context, invalidate stale displayed verification on edits/new snapshots, and guard asynchronous presentation updates. No new signing, replay, checkpoint or ledger feature. No frontend cryptographic checks. Keep history on execution errors. Scoped inference-ledger.css, native details, exact-value copy controls, live assessments. Shared rendering/other screens remain unchanged except narrowly scoped generation feedback in the existing form owner.

## Validation

After Inference and after Ledger: full 50-test suite. Final source freeze, selector/duplicate-ID/Flask/offline checks, JS syntax and renderer fixtures. Actual responses will be generated using the unchanged backend in a temporary ledger; separate UI pending/error contexts tested as presentation states. Include action payloads, altered-copy isolation, stale-response/edit handling, replay, signature/structure ambiguity, checkpoint failure and escaping. Browser/layout/network behavior remains unverified.
