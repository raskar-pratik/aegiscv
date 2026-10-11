# Tabler integration — phases 1 and 2

Integration date: 2026-10-07. Scope: local dependencies and application shell only.

Final source validation resumed on 2026-10-08 after restoring the temporary Python environment.

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

## Validation status

Known baseline limitation: `coverage` is already duplicated between the overview metric and the Coverage page. The shell does not add or remove either occurrence because these IDs and page internals are explicitly frozen for this phase. The source contract checks preserve the baseline ID counts and prohibit new duplicates; they do not certify the baseline HTML as free of duplicate IDs. Resolving the existing collision requires a separately scoped coordinated selector change.

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
