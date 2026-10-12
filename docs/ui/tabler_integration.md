# Tabler integration — controlled presentation refinement

> **Historical Record Note (2026-10-12):** This document records the Tabler integration phases completed between 2026-10-07 and 2026-10-11 for AegisCV. The project has since been rebranded to Veyra.

Initial integration date: 2026-10-07. Original Phase 1–2 scope: local dependencies and application shell only.

Final source validation resumed on 2026-10-08 after restoring the temporary Python environment.

Current status (2026-10-11): Phases 3, 3.5, 4 and 5 are implemented and approved. Phase 5 is checkpointed at 78aaf96. The duplicate coverage ID was resolved in Phase 3.5: overview-coverage is the metric and coverage remains the page. Phases 5.5 and 6 are implemented and stopped for review: documentation reconciled, Inference Provenance and Audit Ledger refined. Static validation passed; visual validation remains pending. Visual validation remains PENDING; browser regression NOT RUN. Earlier phase sections below are historical records, not current unresolved work.

## Dependency pin and sources

Tabler Core **1.6.1**, MIT, from https://github.com/tabler/tabler, release tag `@tabler/core@1.6.1`, published 2026-09-28. GitHub's latest-release API and official release page identified this as the stable release on the integration date (not a prerelease).

Compiled assets come from the exact npm archive https://registry.npmjs.org/@tabler/core/-/core-1.6.1.tgz. Only selected members were copied; no package scripts or workspace dependencies were installed. The package's navbar Sass and unminified JavaScript were inspected for structural conventions and bundled dependencies. Layout reference: https://docs.tabler.io/ui/layout/navbars.

Tabler Icons **3.49.0**, MIT, from https://github.com/tabler/tabler-icons, exact archive https://registry.npmjs.org/@tabler/icons/-/icons-3.49.0.tgz. Only the ten outline icons used by navigation are retained.

Both archives were checked against the npm metadata's SHA-512 integrity values. `dashboard/static/vendor/tabler/manifest.json` records archive URLs/integrity, original source-member hashes and final file SHA-256 hashes.

## Vendored inventory

All paths below are relative to `dashboard/static/vendor/tabler/` and served under `/static/vendor/tabler/`.

| Files | Purpose |
| --- | --- |
| `css/tabler.min.css` | Framework shell, vertical navigation, header and collapse primitives |
| `js/tabler.min.js` | Local framework JavaScript for the small-screen navigation collapse; no application data or verification owner |
| `icons/layout-dashboard.svg` | Overview navigation |
| `icons/database.svg` | Data integrity navigation |
| `icons/users.svg` | Contributors navigation |
| `icons/brain.svg` | Model integrity navigation |
| `icons/fingerprint.svg` | Inference navigation |
| `icons/history.svg` | Audit ledger navigation |
| `icons/chart-line.svg` | Distribution navigation |
| `icons/file-report.svg` | Reports navigation |
| `icons/shield-check.svg` | Coverage navigation |
| `icons/player-play.svg` | Demonstration navigation |
| `LICENSE-tabler.txt`, `LICENSE-icons.txt` | Complete upstream MIT notices |
| `LICENSE-bootstrap.txt`, `LICENSE-popper.txt` | Complete MIT notices for Bootstrap 5.3.8 and Popper Core 2.11.8 already included in Tabler's core bundle |
| `manifest.json` | Exact pins, provenance and file-integrity record |

No `dist/libs` bundles, ApexCharts, extra plugin scripts, fonts, icon webfonts, demo pages, or Tabler development infrastructure are imported. Popper is already included in the distributed core JavaScript; no separate optional plugin is added.

Copyright banners remain intact. The only change to upstream CSS/JS is removal of source-map trailers because maps are not shipped. License and documentation URLs in comments, and SVG XML namespace identifiers, are not external asset loads. Full license attribution is indexed in `THIRD_PARTY_NOTICES.md`.

## Offline strategy

All runtime asset references must be same-origin `/static/` paths or embedded data URLs. No CDN, Google Fonts, network icon service, remote CSS or remote JavaScript is used. Font stacks stay `Segoe UI, Arial, sans-serif`; existing technical values retain their monospace styles. Developer-time downloads are not runtime dependencies. Browser interception is still required to establish an observed zero-external-request result.

## Shell integration boundaries

Tabler supplies vertical navbar, navigation link/icon/title, page-wrapper/container, header and collapse patterns. Product palette, compact spacing and existing navigation grouping remain AegisCV-specific. The sidebar toggle controls navigation only and lives outside `nav`, so existing `nav button` handlers continue to select pages only.

The template keeps every existing section, form and output container. Existing `app.js` and `workstation.js` remain the sole owners of data fetching, navigation selection, history, verification and evidence rendering. No tab plugin is attached to existing page buttons. No backend, API, experiment, report, detector or cryptographic code is changed.

Overview internals, contributor tables, dataset/model investigations, provenance/ledger chains, distribution, coverage and the demonstration console are outside this phase. No feature controls, theme switcher, avatar, notification or search UI is added.

## CSS strategy

Load order: vendor CSS, existing base CSS, existing workstation CSS, final shell stylesheet. Product variables and framework token mappings live in the shell stylesheet; existing product overrides remain available.

The legacy plot rule is scoped from global `svg` to `#scatter` before adding icons. Shell icons have explicit dimensions and empty alternative text beside visible labels. The shell stylesheet includes a limited compatibility boundary for shared `.row`, `.card`, `.badge` and `.page` names. Global control/disclosure rules stay in place; shell controls get scoped selectors. `.hidden` remains the existing visibility contract. Custom `.chain-node` rules are untouched. This is source-level conflict handling, not a claim of pixel equivalence.

## Accessibility and responsive intent

Preserve skip navigation, keyboard-focus outlines, visible link labels, `aria-current`, live service health, nested form labels, reduced motion and native evidence disclosures. The navigation collapse uses Tabler's supplied control and `aria-expanded`/`aria-controls`. Its visible text and accessible name describe navigation; icons are decorative.

Desktop uses a compact fixed navy rail. Below 720px the rail becomes a top navigation region with a collapsible menu; no navigation labels are abbreviated. Narrow investigation layouts remain owned by existing workstation styles. Real keyboard, contrast, viewport and overflow checks are pending.

## Upgrade procedure

1. Read official stable release notes and choose an exact version; never use `latest` or the development branch.
2. Download exact release/npm archives to a temporary directory and verify registry integrity. Inspect changed upstream CSS, JS and license notices.
3. Copy only the inventory above; retain copyright banners and remove only unshipped source-map trailers. Check core bundles for newly included dependencies or runtime network references.
4. Update the manifest's versions, source URLs, upstream/file SHA-256 hashes, full licenses and notices. Keep icon versions independently pinned.
5. Review shell compatibility selectors against the new vendor CSS. Preserve all application IDs, form names, accessible navigation names and script ordering.
6. Run the full suite, shell contract checks, Flask rendering/local asset checks and static external-reference scan.
7. When a browser is available, run the real browser regression, block external requests, capture baseline/after screenshots and validate requested viewport sizes. Do not mark the UI frozen from source checks alone.

## Historical Phase 1–2 validation status

Historical baseline limitation (resolved in Phase 3.5): `coverage` is already duplicated between the overview metric and the Coverage page. The shell does not add or remove either occurrence because these IDs and page internals are explicitly frozen for this phase. The source contract checks preserve the baseline ID counts and prohibit new duplicates; they do not certify the baseline HTML as free of duplicate IDs. Resolving the existing collision requires a separately scoped coordinated selector change.

Implementation and visual validation are separate. The user explicitly waived the pre-implementation browser baseline for this environment, not browser validation itself. Final phase results are recorded in `phase_1_2_validation.json` after execution.

- Visual validation: **PENDING — NO BROWSER AVAILABLE**.
- Browser regression: **NOT RUN** for this implementation.
- Screenshots: **NOT AVAILABLE**.
- Responsive behavior: implemented by CSS; **not browser-verified**.
- Runtime external requests: **not measured**.
- Tabler UI freeze: **NO**.


## Phase completion record

Phases 1 and 2 are implemented; work stops here for shell review.

- Phase 1 full suite: 50/50 passed before shell migration (2026-10-07).
- Phase 2 full suite: 50/50 passed in 10.636 seconds (2026-10-08), including existing UI-contract tests.
- `python scripts/check_ui_shell.py`: PASS for selector/form preservation, byte-identical screen internals, frozen files, unchanged application JS/workstation CSS, vendor hashes, Flask rendering/CSP, all 17 local asset routes, and external-asset static scan.
- `node --check dashboard/static/vendor/tabler/js/tabler.min.js`: PASS.
- `git diff --check`: PASS.
- Optional PostCSS syntax parsing was unavailable because PostCSS is not installed; no parser-based CSS validation is claimed.
- Static source hits for HTTP(S) are limited to copyright/license documentation, Popper error-message documentation, and SVG namespace identifiers. No CDN, jsDelivr, unpkg or Google Fonts reference was found in runtime source. This does not replace browser request interception.

Reproduce from the repository root with the configured Python environment:

```sh
python -m unittest discover -s tests -v
python scripts/check_ui_shell.py
node --check dashboard/static/vendor/tabler/js/tabler.min.js
```

The shell check compares against the recorded baseline Git commit, so it requires that commit to remain available locally. It intentionally reports the pre-existing duplicate `coverage` ID rather than silently changing a frozen selector.


## Phase 2.5 — legacy class compatibility cleanup (2026-10-08)

The approved phases 1/2 state was checkpointed as Git commit `cc7bada` before this work. No vendor asset changed.

All existing unqualified `row`, `card` and `badge` uses in the six audited frontend files were AegisCV legacy presentation, not intentional Tabler components. The JavaScript-generated occurrences included temporary base-renderer output that is subsequently replaced by workstation rendering; these were retained and renamed, not deleted.

| Legacy class | Replacement | Locations and intent |
| --- | --- | --- |
| `.row` | `.aegis-row` | Template action groups, source summaries and base report rows in app.js; matching base/workstation CSS selectors. Existing `.action-row` is preserved. |
| `.card` | `.aegis-metric-card` | Base app.js domain metrics and their base/print CSS. Effective workstation `.domain` investigation entries remain custom. |
| `.badge` | `.severity-badge` | app.js finding severity tags and their CSS. Status text/severity values are unchanged. |

Removed all broad `#workspace .row`, `.row > *`, `.card` and `.badge` compatibility overrides from shell.css. Tabler's actual grid, card and badge classes are now available without those overrides. The `.page` compatibility rule remains because it belongs to the application's frozen navigation visibility contract. `.hidden`, IDs, handlers and all business logic are unchanged.

Phase 2.5 gate: 50/50 unit/integration tests passed in 10.776 seconds; shell source contract, vendor JS syntax and diff whitespace checks passed. Records: `phase_2_5_tests.txt` and `phase_2_5_validation.json`.

## Phase 3 — generic presentation primitives

New local stylesheet `dashboard/static/primitives.css` follows shell.css. Static workspace buttons adopt Tabler `.btn`, `.btn-primary`, `.btn-outline-secondary` and `.btn-sm` classes with Aegis steel/navy and white-outline treatment. The main Overview investigation path is primary; secondary actions and findings filters remain restrained. No destructive action is invented.

The four existing forms use `.form-control`, `.form-select`, `.form-check-input` and compact `.aegis-form` spacing. Every existing input name, label, required attribute, submit handler and payload remains intact. The record JSON textarea now has an explicit visible associated label, `Signed inference record JSON`, using `for="record-json"`; no existing ID changed.

Native details/summary elements remain native. Registration disclosures, technical disclosures, copy buttons and notices receive shared presentation rules only. Tables receive consistent header contrast, cell spacing and hover/focus treatment; existing numeric cells keep explicit `.numeric` alignment and tabular figures. No table data, filtering, sorting, or reliability logic changes.

Semantic tags remain Aegis-specific `.status-tag` and `.severity-badge`, with visible text. Severity LOW/MODERATE/HIGH/CRITICAL/UNAVAILABLE/FAILED labels are retained. FAILED severity tags use the red failure palette; UNAVAILABLE uses neutral slate. Existing verification labels and status interpretation are not renamed or reclassified. Tabler `.badge` is left available, not used to replace forensic semantics.

## Phase 3B — Overview only

New local stylesheet `dashboard/static/overview.css` scopes its rules to `#overview`.

- Custom decision hero retains the actual report disposition, triggering asset, decision reason and metrics. The triggering asset now precedes the reason; maximum asset risk is emphasized over composite risk and confidence/coverage. No values are hardcoded.
- Rationale panel keeps the existing dynamically rendered asset, affected count, evidence-family count and policy reason. The actual evidence-family path remains below it. `View evidence` is the primary investigation action.
- Domain entries remain custom `.domain` buttons showing the existing domain, risk, findings, completed checks and investigation route, with compact typography.
- Contributor and PCA summary surroundings use actual Tabler `.card`, `.card-header` and `.card-body` primitives. Their underlying rendering and data remain unchanged; there is no new chart library, axis or legend.
- Findings retain their existing order, filtering and disclosure behavior. Buttons, count chips and severity tags receive consistent spacing and readability.
- The complete interpretation boundary warning is preserved verbatim.
- Desktop proportions target the requested 1366×768 above-fold decision content. Media rules stack the hero and rationale at narrower widths. This is responsive intent, not visual confirmation.

No Contributors, Data Integrity, Model Integrity, Inference, Ledger, Distribution, Coverage or Demonstration investigation internals were redesigned. Outside Overview, changes are limited to approved shared primitive classes/treatment, legacy class renames and the explicit record label. `workstation.js` is byte-identical to the original baseline. `app.js` differs only in the approved class names, so display, navigation, verification, polling and data behavior are unchanged.

## Historical Phase 3 validation and stop point

Phases 2.5 / 3 Overview: **IMPLEMENTATION COMPLETE — STOPPED FOR REVIEW**.

- Full suite: **50/50 PASS**, 11.130 seconds.
- Source contract: **PASS** for IDs and their original counts, form names/attributes, navigation targets, page visibility classes, non-Overview structure/text, unchanged JavaScript behavior, frozen files, vendor integrity and static asset locality.
- Flask render, unchanged CSP and all **19** referenced local assets: **PASS**.
- `node --check` for app.js and workstation.js: **PASS**. Vendored JS syntax passed the Phase 2.5 gate and was not changed.
- `git diff --check`: **PASS**.
- No new remote fonts, icons, CSS, JS, CDNs or chart libraries. Raw HTTP(S) matches remain license/documentation strings and SVG namespaces only.
- Validation records: `phase_3_tests.txt` and `phase_3_validation.json`.

The source checker was updated to permit only authorized presentation changes: normalized legacy class names in JavaScript; class-only changes and the explicit record label in protected sections; and Overview markup refinement. It still verifies original IDs, input names, navigation, visibility classes, warning text and filters, and checks every original non-frontend file against the frozen commit. It does not substitute these checks for a browser.

Known issues remain: the pre-existing duplicate `coverage` ID is intentionally untouched; generic vendor resets and responsive layouts require browser review; keyboard/mobile-menu operation, contrast, overflow and above-fold composition have not been visually validated.

VISUAL VALIDATION: **PENDING — NO BROWSER AVAILABLE**.
RESPONSIVE VALIDATION: **PENDING — NO BROWSER AVAILABLE**.
BROWSER REGRESSION: **NOT RUN**.
SCREENSHOTS: **NOT AVAILABLE**.
RUNTIME EXTERNAL REQUESTS: **NOT MEASURED**.
TABLER UI FREEZE: **NO**.


## Phase 3.5 — coordinated coverage ID correction (2026-10-08)

Approved Phase 3 was checkpointed as commit `20ee6ad` before this work. Repository search found one metric writer in app.js and the two template IDs. Only the Overview metric changed to `overview-coverage`, with its corresponding textContent writer updated. The Coverage section remains `id="coverage"`; its `data-page="coverage"` navigation and `coverage-list` output remain unchanged. No backend or JSON field was renamed.

The existing UI-contract test now renders Flask HTML and rejects every duplicate ID, confirms both intended coverage IDs and the navigation target, and checks that the metric writer uses the new ID. The source checker now requires zero duplicates in rendered/template HTML instead of tolerating the former collision. The 50-test count is preserved by strengthening the existing test.

Phase 3.5: 50/50 tests passed; selector/duplicate-ID checks, JS syntax and diff checks passed. Logs: `phase_3_5_tests.txt`, `phase_3_5_validation.json`.

## Phase 4 — Data Integrity

The existing `renderDataset()` owner now presents one compact dataset summary followed by reported detector findings and a high-priority evidence list. Format, image count, classes, contributor count and manifest identity come from the selected report. The manifest uses the existing shortened hash/copy control plus a collapsed full-identity disclosure.

The detector strip shows counts and only actual returned execution/reliability states. It never treats an absent or zero finding count as verified safety. A note makes that distinction explicit.

The exact evidence selection remains `fs.filter(f => Number(f.risk_score) > 20).slice(0, 12)`, in report order. No severity sort or alternative filtering was introduced. Severity tags convey review priority; the display limit is now explicit. Compact native disclosures expose detector, asset, reason, source, risk, confidence, reported reliability and recommended action, with actual evidence and limitations below. Missing values are identified as unavailable/not supplied rather than fabricated. No image thumbnails or chart library are introduced.

The existing registration disclosure remains after investigation evidence and uses a quieter surface. Its open/close behavior is unchanged; navigation still owns that behavior.

## Phase 4 — Contributors

The table remains the investigation index, using Tabler `.table`, `.table-vcenter` and `.table-responsive` patterns. Columns remain Source, Samples, Affected, Evidence families, Risk /100 and Action. Numeric fields remain right-aligned with tabular figures; names and labels are left-aligned. Risk is displayed out of 100, never as a percentage. Actions come from the existing report; absent actions retain an unknown label rather than an invented recommendation. ACCEPT receives verified-green treatment only when the backend actually returns ACCEPT; QUARANTINE and REVIEW keep red/amber labels.

Descending risk sorting, source-link targets, linked-finding selection/order and the first-open disclosure behavior are preserved. Source links open the existing native source investigation. Evidence composition uses the existing meters and actual values, now with accessible names. Associated findings use the same compact evidence component as Data Integrity. The exact attribution warning remains: “Assets associated with duplicate clusters do not establish who created the duplicate.” A short version is also visible above the table.

## Shared component, scope and accessibility

`investigationEvidence()` is a presentation helper within workstation.js, called only by the existing dataset/source renderers. It does not become a new rendering/navigation owner. `findingCard()` remains unchanged for the protected Model and Distribution views. No API, risk, decision, evidence-content or report-data mutation occurs.

New stylesheet: `dashboard/static/investigations.css`, loaded last after vendor, base, workstation, shell, primitives and Overview styles. Its rules are scoped to `#datasets` and `#contributors-page`. The approved generic/Overview styles are byte-identical to their approved checkpoint.

New component classes include `dataset-summary`, `manifest-identity`, `detector-entry`, `investigation-heading`, `investigation-evidence-list`, `investigation-evidence`, `evidence-heading`, `evidence-asset`, `evidence-reason`, `evidence-facts`, `evidence-detail`, `contributor-table-wrap`, `source-composition` and `source-findings`. Existing `.source-investigation`, `.evidence-bar`, `.numeric`, severity/status classes and navigation IDs remain in use.

Tabler supplies the dataset summary panel, table structure and responsive overflow pattern. Aegis retains its severity/action semantics, score meaning, attribution warning, detector evidence and native progressive disclosure. No new library or vendored asset is added.

Accessibility additions: column and row-header scope, a descriptive table caption, a keyboard-focusable labelled scroll region, named meters with visible values, and explicit evidence text. Existing form labels, copy names, focus outlines and native summary markers remain. Dynamic text and attribute values remain escaped. No inline style or event handler attributes are introduced in generated fragments.

Legacy CSS removed: none in this phase. Existing base/fallback presentation definitions are retained; the new screen-specific stylesheet provides scoped treatment. No unrelated CSS cleanup was performed.

## Phase 4 source review and validation

- After Data Integrity: **50/50 PASS**, 12.891 seconds.
- After Contributors: **50/50 PASS**, 10.441 seconds.
- Final full suite: **50/50 PASS**, 11.644 seconds.
- Final selector/source contract: **PASS**. Overview is unchanged except the authorized metric ID. Protected Model, Inference, Ledger, Distribution, Coverage, Reports, Demo and navigation/rendering code remain unchanged.
- Flask HTML and all **20** local asset paths: **PASS**; CSP unchanged.
- Rendered template duplicate IDs: **0**. Generated fixture fragments also contain no duplicate IDs.
- Static offline scan, app.js/workstation.js syntax and `git diff --check`: **PASS**.
- `scripts/check_investigation_ui.js` executes the existing renderers with element stubs, checking unchanged risk selection/cap/order, contributor sorting, actual fixture values, linked findings, missing data, escaping and absence of report mutation. This is not browser execution.
- The Python source checker parses those generated fragments to reject unbalanced/invalid table markup, missing header scope/meter labels, inline styles/event attributes, injected active markup and duplicate IDs.
- Frozen backend files modified: **NONE**.

Records: `phase_4_data_tests.txt`, `phase_4_contributors_tests.txt`, `phase_4_final_tests.txt` and `phase_4_validation.json`.

Known limitations: the existing Data Integrity view still displays at most 12 findings above risk 20 and is not a complete findings list; missing reliability/source fields are explicitly labelled; actual narrow-screen overflow, density, focus behavior and meter rendering require a browser. The previous duplicate coverage ID is resolved.

IMPLEMENTATION: **PHASES 3.5 / 4 COMPLETE — STOPPED FOR REVIEW**.

VISUAL VALIDATION: **PENDING — NO BROWSER AVAILABLE**.

RESPONSIVE VALIDATION: **PENDING — NO BROWSER AVAILABLE**.

BROWSER REGRESSION: **NOT RUN**.

SCREENSHOTS: **NOT AVAILABLE**.

RUNTIME EXTERNAL REQUESTS: **NOT MEASURED**.

TABLER UI FREEZE: **NO**.


## Approved Phase 5 Model Integrity (2026-10-11)

Implementation complete; STOP for review. Tabler Core remains locally pinned at 1.6.1. No backend, API, detector, threshold, calibration, risk fusion, policy, cryptography, model loading, dependency or experiment change.

### Audit and ownership

See `phase_5_audit.md` for the audit completed before presentation edits. `app.js` remains byte-identical to approved Phase 4: model registration, form serialization, scan submission and report selection keep their existing ownership. `workstation.js` owns renderModel and canvas presentation. show, display, refresh and delegated navigation/copy handlers are unchanged. Model form names, validation, IDs and event bindings are unchanged.

### Model Integrity design

The identity summary gives the actual architecture, format, SHA-256, access and returned-check execution counts. A registry model ID is not included in scan reports; the UI says so rather than guessing from an inventory match. Registration remains below the investigation, in a compact native disclosure; existing opening behavior is preserved.

Six numbered sections distinguish cryptographic identity, behavioral fingerprint, backdoor investigation, activation/parameter evidence, coverage/limitations and technical records. Tabler card/header/body and table structures provide layout; Aegis text-bearing semantic tags remain independent. The main evidence column occupies two thirds and the secondary coverage/technical column one third at desktop widths. The layout stacks below 1100px. Responsive intent includes 1366×768, 1440×1000 and 1920×1080; no viewport has been visually verified.

Cryptographic MATCH/MISMATCH requires a successful check and both expected/actual hashes. Missing expected identity is NO TRUSTED REFERENCE; absent check NOT CHECKED; incomplete or unsuccessful comparison UNAVAILABLE with actual execution status/reason displayed separately. A trusted mismatch uses the red integrity-violation treatment. Full values remain in native disclosures and shortened hashes have context-specific copy names.

Behavior uses actual observed fingerprint, probe hash, predictions and optional probe-output table. The backend returns maximum absolute difference, but not reference outputs/fingerprint; the comparison explains that limit. Backend severity/action remain the assessment outcome; no frontend threshold or invented confidence. Raw outputs are not labeled as calibrated probabilities.

Backdoor execution and evidence verdict are separate. SUCCESS + NO_QUALIFYING_EVIDENCE remains a successful negative result; it does not become UNAVAILABLE. The backend recommended action remains visible, including ACCEPT for a qualifying negative execution. Experimental evidence handling is labeled REVIEW and the exact warning is visible: “Reconstruction anomalies may indicate suspicious model behavior but do not cryptographically confirm a backdoor.” The frozen historical TP=5, FP=1, TN=2, FN=1 is checked and untouched, never injected into live scan metrics.

Recovered target, norm, median, MAD, anomaly index and held-out recovery come only from reported values. The existing preview reader assumed channel-first patterns; backend patterns are height × width × RGB. The presentation reader now maps that actual layout; masks remain height × width. No synthetic images are generated. Missing, malformed or nonfinite arrays show PREVIEW UNAVAILABLE while retaining hidden canvas IDs. Accessible descriptions distinguish reconstruction imagery from observed attack images. Held-out recovery is explicitly not detector accuracy.

Activation measurements show actual available class/count/separation/cluster data, with members in a disclosure. Parameter count is explicitly not a parameter-integrity verdict. Access requirements and execution outcomes are separate; black-box access never establishes completed gradient or activation checks. Missing results stay NOT CHECKED and runtime/feature limitations remain visible.

### Presentation classes and accessibility

New stylesheet `model-integrity.css`, scoped exclusively to #models. Classes include model-assessment-summary, model-investigation-layout, model-primary, model-secondary, model-panel, model-comparison, model-status-pair, model-facts, model-reliability, model-reconstruction, model-check and preview-unavailable. Existing global/shared styles remain frozen.

Preserved native disclosures, keyboard navigation, visible focus, form labels, live regions and reduced-motion behavior. Copy controls name the specific fingerprint. Canvas role/description/fallback text and a keyboard-focusable output table region provide text context. All dynamic backend strings are escaped. No added animation, chart library or external asset.

### Earlier phase status and Data Integrity boundary

Phase 3.5 renamed only the Overview metric to overview-coverage; coverage navigation/page/output remain intact and duplicate IDs remain zero. Phase 4 Data Integrity and Contributors are approved. Their renderers/styles remain frozen except authorized selection microcopy: “shown / eligible / returned,” calculated from existing report findings. Selection is still risk >20, first12, report order; no sorting or selection changes. It is explicitly a subset.

### Regression and known limits

- Full baseline: **50 / 50 PASS**, 10.946 seconds (`phase_5_tests.txt`).
- `check_ui_shell.py`: PASS, including frozen backend/experiment bytes, prior-screen markup/renderer boundaries, selectors/forms, template and generated-fragment duplicate IDs, vendored integrity, Flask/CSP/local routes and static offline checks.
- Existing `check_investigation_ui.js`: PASS; dataset cap/order and Contributors preserved.
- New `check_model_ui.js`: PASS; trusted/missing/failed identity, negative vs unavailable backdoor evidence, black-box limits, missing model, actual values, escaping, immutability, malformed arrays and exact RGB/mask pixel mapping. Also executes against frozen reconstruction records and checks TP5/FP1/TN2/FN1.
- app.js/workstation.js Node syntax and git diff --check: PASS.
- 21 local assets served; no new runtime external asset references. Existing vendor URL text is license/documentation/SVG namespace content.

**VISUAL VALIDATION: PENDING — NO BROWSER AVAILABLE.** Responsive visual validation PENDING. Browser regression NOT RUN. Screenshots NOT AVAILABLE. Runtime external request count NOT MEASURED. Canvas checks use stubs and do not establish actual browser rendering; clipboard permission behavior and viewport layout remain unverified. No changes to Inference, Ledger, Distribution, Coverage, Reports or Demo. TABLER UI FREEZE: NO.


## Phase 5.5 — documentation reconciliation (2026-10-11)

Inspected the current working document and Git history: cc7bada (Phases 1–2), 20ee6ad (Phase 3), e51c88d (Phases 3.5/4), 78aaf96 (Phase 5). The current repository already recorded Phases 3–5 and the duplicate-ID fix; older review copies and ambiguous “current” headings could suggest otherwise. Historical headers are now explicit and a current implementation summary appears at the top. Earlier test logs and measured results are preserved unchanged. No visual verification is claimed.


## Current implementation — Phase 6 (2026-10-11)

**Implementation complete; stopped after Inference Provenance and Audit Ledger. Static validation passed. Visual validation pending.** No Distribution, Coverage, Reports, Demonstration Console or final UI freeze work is included.

### Rendering ownership and scope

`phase_6_audit.md` records the DOM/schema audit completed before application edits. `app.js` retains fetch, token handling, form serialization, generation callbacks and API ownership. Its only change is narrowly scoped pending/error presentation feedback for inference creation inside the existing form handler. `workstation.js` retains provenance/ledger rendering and verification actions. No third rendering owner. All form markup, names, required fields, action IDs and endpoints are preserved. show, display, refresh, Model Integrity, Data Integrity, Contributors and other screen renderers remain byte-identical to approved Phase 5 outside the authorized verification regions.

### Inference Provenance

The current assessment precedes signed record identity and a compact seven-stage chain: input, preprocessing, model, configuration, output, signature, record verification. Record ID, kind, sequence, timestamp, record hash and nonce use actual record fields. Available payload hashes and technical values remain accessible through exact-value copy controls and native disclosures. Raw record JSON remains labeled and can be copied unchanged.

Present values are not treated as verified. A successful overall record check labels payload identities “BOUND BY VERIFIED RECORD”; the signature stage says “SIGNATURE CHECK PASSED.” This does not imply independent verification of each stage or external artifact identity. The visible interpretation boundary states that a valid signature does not establish a benign model, attack-free input, correct output, trustworthy dataset or safe prediction.

Backend TAMPERED displays its actual first-failure reason. SIGNATURE_INVALID is described as signature or record-structure failure, never automatically intentional tampering. The backend does not return expected/observed failure pairs or a REJECT field, so none is fabricated. Pending/request/JSON errors are separate frontend presentation context, not invented backend states. Editing a record invalidates displayed verification and stale in-flight responses are ignored.

Verification and acceptance remain separate requests. VALID from verification is not acceptance. VALID from acceptance shows replay-check success and persisted replay state. REPLAY from the acceptance endpoint is shown separately: the unchanged backend first verifies signature/content, then rejects on replay policy. No automatic acceptance is introduced.

### Audit Ledger

The primary assessment exposes actual verifier status, reason and first reported traversal position. Stored sequence values are shown separately because untrusted sequence metadata can differ from the verifier's 1-based position. Earlier entries are “PASSED BEFORE FAILURE”; the first reported entry is “FIRST INVALID LINK”; later entries are “CHAIN NOT TRUSTED,” with an explicit warning that they are not independently classified as tampered. A checkpoint failure beyond the returned history is a boundary failure, without an invented row.

Dense rows show actual sequence, kind, timestamp, record hash and previous hash, with full record disclosures. The existing recent/failure-centered window is retained and explicitly labeled as a subset; full returned history remains available. Empty returned history is distinct from unavailable history. A fetched-history change invalidates prior verification; a successful result whose count/head differs from the displayed history is not presented as verification of that snapshot. This is a presentation consistency check, not frontend cryptography.

The altered-copy workflow still changes only `records[max(0, length-3)].record_hash` to `altered` in a deep copy, and submits the same existing endpoint/payload. It does not change stored data. Pending ledger actions cannot overlap, and refresh preserves pending controls. Execution errors retain history and remove stale verification. Suffix-deletion/checkpoint limitations remain visible; no external anchoring or full completeness is claimed.

### Tabler, custom components and accessibility

Local Tabler 1.6.1 supplies card/header/body structure and existing button/form primitives. AegisCV owns chain states, forensic identity rows, failure emphasis, replay distinction and palette. `inference-ledger.css` is scoped to #inference/#ledger; shared styles are unchanged. New classes include forensic-panel, forensic-value, record-identity-grid, forensic-section-heading, forensic-boundary, stage-state, ledger-summary, ledger-position, ledger-hashes and chain-untrusted.

Preserved keyboard interaction, native disclosures, focus outlines, labels, reduced-motion rules and escaped values. Assessment regions are live and atomic, with aria-busy during actions. Copy controls have descriptive names and retain exact values. Layout targets 1366×768, 1440×1000 and 1920×1080; narrow layouts stack identity grids and stages, with wrapped hashes. No visual/responsive verification is claimed.

### Regression evidence

- After Inference: 50/50 PASS, 11.189 seconds (`phase_6_inference_tests.txt`).
- After Ledger: 50/50 PASS, 11.013 seconds (`phase_6_ledger_tests.txt`).
- Final full test gate: see `phase_6_final_tests.txt` and `phase_6_validation.json`.
- `check_ui_shell.py` passes original frozen-file comparisons, prior-screen preservation, unchanged form contracts, IDs, CSP, local routes and vendor integrity.
- New `ui_verification_fixtures.py` generates actual responses using the unchanged backend in temporary storage; it does not modify backend source or production data.
- `check_verification_ui.js` covers unchecked/valid/modified/invalid-signature/replay/missing/error states; empty/valid/broken/sequence/checkpoint ledgers; escaping; exact payloads; no automatic acceptance; altered-copy isolation; stale-response suppression; history retention; pending actions and generation feedback. Existing investigation/model renderer checks also pass.
- 22 local assets served; no new external runtime references. Template, Flask HTML and generated fragments have no duplicate IDs. Node syntax and git diff --check pass.

### Known unverified behavior and boundaries

**VISUAL VALIDATION: PENDING. RESPONSIVE VALIDATION: PENDING. BROWSER REGRESSION: NOT RUN. SCREENSHOTS: NOT AVAILABLE. RUNTIME EXTERNAL REQUESTS: NOT MEASURED.** Actual viewport density, native disclosure appearance, clipboard permission behavior and focus rendering require a browser.

The API provides an overall result, not per-field verification responses. SIGNATURE_INVALID conflates signature and structure errors. Ordinary ledger verification still uses the existing separate fetch and POST `{}` requests; the UI checks returned count/head for successful results, but this is not a new atomic snapshot protocol. No backend protocol, verification, signing, hashing, binding, replay, checkpoint, storage, security, ML or policy behavior changed. **TABLER UI FREEZE: NO.**
