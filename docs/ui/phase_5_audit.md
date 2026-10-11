# Phase 5 audit — completed before presentation edits

Approved Phase 4 checkpoint: e51c88d. Scope: Model Integrity only, plus optional accurate Data Integrity selection microcopy.

Inspected index.html, app.js, workstation.js, style.css, workstation.css, primitives.css, shell.css, overview.css and investigations.css; model adapter, scanner, API routes, Finding schema, model identity/reconstruction/activation/patch detectors and model/UI/decision tests.

## Preserved contract

- `app.js`: registration and scan form bindings, API serialization, selected report state; unchanged.
- `workstation.js`: renderModel(report), drawArray(id,data,rgb), model inventory in refresh, delegated data-copy/data-go handlers. Only model renderer/preview presentation changes. show/display/refresh and event handlers remain unchanged.
- IDs: models, model-workspace, model-form, model-list, trigger-preview, mask-preview. Form names path/format/trusted and validation remain unchanged. Existing canvas selectors retained even when previews are unavailable.
- Shared hash/status/technical helpers and CSS remain unchanged; new styling scoped to #models.
- Protected renderers: Dataset selection, Contributors, Overview, Distribution, Provenance, Ledger, Coverage, Reports, Demo.

## Actual response and interpretation

- report.model has metadata, behavior, findings; registry ID is not returned. Metadata contains sha256, format, access, runtime_available, reason, architecture, parameter_count, size, version, timestamp. Do not infer registry ID from selected UI state.
- model_hash evidence expected/actual; successful comparison needs both values. No expected hash means NO TRUSTED REFERENCE, never MATCH. Missing check and unavailable execution are distinct; failure reason remains visible.
- behavioral_probe evidence max_absolute_change and observed behavior. Reference outputs/fingerprint are not returned by current scanner. Render that limitation explicitly, actual observed top predictions/output, and backend action/severity without recreating thresholds.
- neural_cleanse evidence outcomes, target, median, mad, anomaly_index, successful_targets, source assumptions and backdoor_assessment; outcome success is held-out recovery, not detector accuracy. Execution SUCCESS can coexist with NO_QUALIFYING_EVIDENCE and ACCEPT. Do not replace either with UNAVAILABLE.
- Backend pattern uses H×W×RGB (`permute(1,2,0)`); mask H×W. Existing drawArray incorrectly assumes channel-first RGB. Correct only canvas mapping, check dimensions/finite values and retain canvas IDs when missing.
- activation_clustering reports cluster sizes, minority fraction, separation, members, examined classes. Metadata parameter_count is a count, not a parameter integrity verdict; no parameter verification detector exists.
- Required access: hash=file bytes; behavioral/patch=prediction runtime; reconstruction=gradients; activations=feature access. Supported capability is separate from actual returned execution status; limited white-box does not guarantee feature availability.
- Existing dataset evidence selects risk>20 then first12, in report order. Keep algorithm; show actual eligible and returned counts.
- Frozen historical backdoor validation remains TP5 FP1 TN2 FN1; no live scan metric injection and no experiment edits.

## Validation plan

50-test suite, source freeze/selector checks, Flask render/local assets, Node syntax and renderer fixtures for reference/mismatch/missing/error/negative/experimental/access states, escaping and RGB/mask pixels. These do not validate visuals, responsive layout, clipboard permissions, or runtime network requests.
