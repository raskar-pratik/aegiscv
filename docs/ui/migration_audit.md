# AegisCV presentation migration audit

Date: 2026-10-07

Status at original audit: preparation complete; Tabler integration had not started. Browser baseline remained blocked. This document preserves the pre-migration source audit, not a visual validation report.

Update 2026-10-08: the user subsequently authorized implementation without the browser baseline. Phases 1 and 2 are now implemented; see `tabler_integration.md` and `phase_1_2_validation.json` for current status. Visual validation is still pending.

## Checkpoint and baseline

- Branch: `ui/tabler-refinement`.
- Starting commit: `e86a86c0968db1afe9de33eb9ad4844d3fdac2af`.
- Initial tracked and untracked changes: none.
- Application code remains unchanged.
- Initial dependency-incomplete run: 48 test entries, 10 errors.
- After Flask and CPU PyTorch installation: 50 tests, two errors for missing torchvision.
- After torchvision installation: **50 tests passed in 30.896 seconds**.
- Command: `python -m unittest discover -s tests -v`.
- Environment prepared outside the repository: Python 3.12, Flask 3.1.3, torch 2.14.1+cpu, torchvision 0.29.1+cpu, Playwright 1.58.0. The recorded frozen environment uses different Python, NumPy, and torch versions; passing unit tests does not independently reproduce every benchmark metric.
- Browser regression: did not reach the application. The existing script requires Edge, which is absent. Edge installation failed with a setgroups permission error. Chromium and headless-shell downloads returned invalid archives.
- Cloud browser: initial application connection refused; selecting the resulting tab was blocked by browser policy. No workaround attempted.
- Baseline screenshots: not captured. External request count: not measured, not zero.
- The four requested design skills were absent from the available skill catalog. No skill-based critique is claimed.

## Ownership and migration map

| File | Current responsibility | Migration boundary |
| --- | --- | --- |
| `dashboard/templates/index.html` | Shell, navigation, page sections, forms, output containers, script order | Add structural classes incrementally; retain IDs, form names, accessible names and script order |
| `dashboard/static/app.js` | API wrapper, escaping, form submission, polling, filters, base display functions and events | Preserve API paths, payloads, POST token and error behavior; retain until proven unused |
| `dashboard/static/workstation.js` | Effective navigation, report rendering, forensic views, verification UI and several replacement handlers | Style render templates without changing evidence interpretation or verification logic |
| `dashboard/static/style.css` | Global reset, controls, base cards, tables, print rules and legacy layout | Scope conflicting selectors after screenshot baseline; do not delete wholesale |
| `dashboard/static/workstation.css` | Final product tokens, custom investigation components, responsive overrides | Retain product identity; consolidate only after each migration gate passes |
| `scripts/browser_check.py` | Demo, navigation, report loading, ledger, inference, replay, screenshots, external-request interception | Preserve exercised workflows; adapt browser runtime only when available |
| `tests/test_ui_contract.py` | Required labels/IDs, static external-asset check, report fields | Preserve contract; expand checks for new vendor assets without weakening existing assertions |

### Load order and events

The template loads `app.js` before `workstation.js`, both deferred. The latter replaces `show`, `display`, `renderInvestigation`, `renderProvenance`, `renderLedger`, and `refresh`. Its `display` first calls the saved base `display`; the base renderer therefore remains active even when parts of its output are replaced.

`app.js` binds navigation, forms, filters and the two demo buttons. `workstation.js` adds history navigation, delegated `data-go` and `data-copy` actions, contributor disclosure links, and replacement verification/ledger handlers. Do not introduce a second navigation or verification owner through Tabler JavaScript.

### Stable selectors

- Navigation: `.page`, `.hidden`, `nav button[data-page]`, `[data-go]`, `aria-current`, and existing section IDs.
- Overview: `score`, `disposition`, `decision-trigger`, `composite-risk`, `max-asset-risk`, `asset-emphasis`, `highest-severity`, `confidence`, `coverage`, `why-title`, `why-body`.
- Findings: `filter`, `.filter-btn[data-filter]`, `finding-summary`, `findings`.
- Forms: `scan-form`, `dataset-form`, `model-form`, `inference-form`; retain every existing input `name`, including checkbox names.
- Evidence: `contributors-detail`, `[data-source]`, `[data-copy]`, `dataset-workspace`, `model-workspace`, `trigger-preview`, `mask-preview`, `scatter`.
- Verification: `record-json`, `verify-record`, `accept-record`, `inference-result`, `inference-assessment`, `provenance-chain`.
- Ledger: `verify-ledger`, `tamper-ledger`, `ledger-state`, `ledger-count`, `ledger-chain`, `ledger-result`, `ledger-assessment`.
- Reports/demo: `report-list button[data-scan]`, `coverage-list`, `demo`, `demo-secondary`, `notice`, `scenario-console`.

Browser accessible names include `Models`, `Inference records`, `Audit ledger`, `Assurance reports`, `Coverage matrix`, `Demonstration Console`, `Run reproducible demonstration`, `Verify record`, and `Accept with replay protection`. Visible wording can differ from these labels. Any approved label change needs a corresponding presentation-selector update, never a backend change.

## CSS integration risks

| Existing rule | Risk | Planned treatment |
| --- | --- | --- |
| `.row` | Shared generic name with framework grid conventions | Rename custom action-row usage or scope it before adopting framework rows |
| `.card, article` | Applies padding, border and margins to all articles | Separate generic cards from custom decision/forensic components |
| `.badge`, `.page`, `.table`-related element rules | Potential framework overlap | Compare the pinned vendor stylesheet before assigning framework classes |
| `svg { width:100%; min-height:190px; ... }` | Local navigation SVG icons would inherit chart dimensions | Scope plot styling to `#scatter`; define icon dimensions separately |
| Global `button`, `label`, `input`, `details`, `summary` | Can override framework controls and disclosures | Introduce component classes gradually; retain native details where suitable |
| Duplicate `:root` tokens and responsive rules | Earlier definitions are overridden by workstation styles | Extract one final token layer once regression proves equivalence |
| `.chain-node` border `!important` and `.hidden` | Specificity conflict potential | Preserve visibility contract; resolve custom chain structure without adding blanket overrides |
| Base `@media print` | Later workstation colors/layout may affect printed dashboard | Inspect print output separately; do not change report generator semantics |

Stylesheet target order: vendored Tabler, retained base CSS, product tokens, final workstation overrides. No Tabler version or asset is selected or vendored yet.

## Custom components to preserve

| Screen | Existing implementation | Refinement target after baseline |
| --- | --- | --- |
| Overview | Decision hero, maximum asset risk, reason, policy evidence path | Preserve decision hierarchy; keep title, reason, metrics and rationale entry visible at 1366×768 |
| Contributors | Numeric table, evidence-family meters, linked findings and disclosures | Framework table spacing; retain attribution caution and actual report values |
| Data integrity | Dataset metrics, detector strip, selected suspicious evidence | Clear priority and accessible evidence disclosure without changing selection rules |
| Model integrity | Hash comparison, behavioral fingerprint, recovered pattern/mask canvases | Forensic grouping and readable metrics; preserve experimental limitations |
| Inference | Seven-stage custom chain and backend verification result | Text plus semantic status; never infer verification from signature presence |
| Ledger | Sequence list, first-invalid banner, collapsed hashes | Preserve first-invalid emphasis and altered-copy behavior |
| Distribution | Backend feature means and meters, intent warning | Improve comparison alignment; no decorative or fabricated data |
| Coverage | Backend support, method and derived reliability labels | Readable table; do not silently redefine reliability mappings |
| Demonstration | One suite, scenario observations and inspect links | One primary suite action; no independent fabricated scenario runs |
| Reports | Existing assessment links and printable report links | Presentation only; preserve generation and export behavior |

## Accessibility and security observations

Existing strengths: skip link, visible keyboard focus, aria-current navigation, live notices, native disclosures, nested form labels, disabled submit states, reduced-motion rules, explicit verification text and numeric alignment.

Items requiring browser validation: projector contrast, small inherited metadata styles, focus after page changes, narrow-screen overflow, tables and disclosures with keyboard input, and long hashes/reasons. `record-json` currently has a placeholder but no explicit associated label; address its accessible name during the forms phase. Do not represent these as verified failures without browser inspection.

The API wrapper escapes generated text through `esc`, sends `X-Aegis-Token`, and uses same-origin paths. The server enforces loopback clients, trusted hosts, Origin checking, CSP and import confinement. Those controls are frozen. Dynamic vendor templates must preserve escaping. No tooltips or HTML-enabled widgets should weaken CSP or insert raw report strings.

## Ordered execution gates

1. Obtain a permitted browser runtime that can reach the unchanged application. Run the baseline script, intercept external requests and capture screenshots. Stop on an actual baseline failure.
2. Inspect the official Tabler repository and current stable release. Pin an exact version, inspect license and assets, vendor only required local CSS/JS/icons, and record checksums/source/version in `tabler_integration.md` and notices. This step is pending, not completed.
3. Run regression after vendoring; migrate shell/navigation/header and capture review cycle 1.
4. Migrate generic primitives, then Overview and contributor/data screens; perform review cycle 2.
5. Refine model, inference (verified/tampered), ledger (valid/tampered), distribution and coverage; perform review cycle 3.
6. Refine demonstration console and reports, then remove only proven-unused presentation code. Perform whole-product review cycle 4.
7. Validate 1366×768, 1440×1000, 1920×1080 and narrow layouts; rerun full suite, demo, browser/offline, security and decision-contract checks.
8. Independently check frozen numerical values from their controlled fixtures; distinguish historical JSON results from newly measured results. Do not force live composite risk to 12.5.

Required screenshots belong in `docs/screenshots/tabler_refinement/`: overview, data_integrity, contributors, model_integrity, inference_verified, inference_tampered, ledger_valid, ledger_tampered, distribution, coverage, demonstration_console, overview_1366x768 and overview_1920x1080 (PNG).

## Completion boundary

TABLER UI FREEZE: NO.

Only audit documentation is complete. No Tabler integration, visual review, new screenshots, browser pass, zero-external-request result, or independently rerun benchmark metrics are claimed. The user's baseline-browser requirement remains in force.
