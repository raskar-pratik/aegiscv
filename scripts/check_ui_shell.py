"""Non-browser UI gate. Does not establish visual or network runtime behavior."""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BASELINE = 'e86a86c0968db1afe9de33eb9ad4844d3fdac2af'
APPROVED_OVERVIEW = '32941a00cb4568d22f5854f0f10f4ccb23b0a108'  # Approved content tree; independent of commit transport metadata
APPROVED_INVESTIGATIONS = '4dda0243fb10e3522da0372b60222e66f78d6edb'  # Approved content tree; independent of commit transport metadata
APPROVED_MODEL = 'b7e50bfbd7143684a93a633195261bca148d245d'  # Approved content tree; independent of commit transport metadata


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.assets = []
        self.navigation = {}
        self.forms = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.append(a['id'])
        if tag in {'script', 'img', 'iframe', 'source'} and a.get('src'):
            self.assets.append(a['src'])
        if tag == 'link' and a.get('rel') == 'stylesheet':
            self.assets.append(a['href'])
        if tag == 'button' and 'data-page' in a:
            self.navigation[a['data-page']] = a.get('aria-label')
        if tag in {'input', 'select', 'textarea'}:
            self.forms.append((tag, a.get('name'), a.get('id'), a.get('type')))


def old(path):
    return subprocess.check_output(['git', 'show', BASELINE + ':' + path], cwd=ROOT).decode()


def restore_legacy_classes(source):
    for current, previous in [('aegis-row', 'row'), ('aegis-metric-card', 'card'), ('severity-badge', 'badge')]:
        source = source.replace(current, previous)
    return source.replace("$('overview-coverage').textContent", "$('coverage').textContent")


def markup_without_presentation(source):
    """Ignore class-only changes and the one explicitly authorized record label."""
    source = re.sub(r'<label for="record-json" class="form-label">Signed inference record JSON</label>', '', source)
    source = re.sub(r' class="[^"]*"', '', source)
    return re.sub(r'>\s+<', '><', source).strip()


def protected_phase6(source):
    start = source.index('// Presentation context is separate') if '// Presentation context is separate' in source else source.index('renderProvenance=function')
    source = source[:start] + source[source.index('function renderCoverage', start):]
    start = source.index("for(const [id,path] of [['verify-record'")
    source = source[:start] + source[source.index('renderProvenance(null);show', start):]
    return source


def restore_generation_feedback(source):
    source = source.replace("if(id==='inference-form')renderProvenance(null,null,{phase:'pending',action:'create'});", '')
    source = source.replace("if(id==='inference-form')renderProvenance(null,null,{phase:'error',action:'create',message:'Inference creation or follow-up loading failed. No current verification is established. '+err.message});", '')
    return source


def protected_workstation(source):
    """Exclude the approved investigation and model renderers and their private helpers."""
    start = source.index('function investigationEvidence(') if 'function investigationEvidence(' in source else source.index('function linkedFindings(')
    source = source[:start] + source[source.index('function comparisonRow(', start):]
    start = source.index('renderInvestigation=function(')
    end = source.index(" const fs=(report.findings||[]).filter(f=>f.category==='DISTRIBUTION')", start)
    source = source[:start] + source[end:]
    start = source.index('function renderDataset(')
    source = source[:start] + source[source.index('renderProvenance=function', start):]
    return protected_phase6(source)


class FragmentStructure(HTMLParser):
    """Validate generated disclosure/table fragments without claiming layout validation."""
    def __init__(self):
        super().__init__()
        self.stack = []
        self.ids = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        assert tag not in {'script', 'iframe', 'img'}, tag
        assert 'style' not in a and not any(k.startswith('on') for k in a), a
        if 'id' in a:
            self.ids.append(a['id'])
        parent = self.stack[-1] if self.stack else None
        permitted = {'table': {'caption', 'colgroup', 'thead', 'tbody', 'tfoot'},
                     'thead': {'tr'}, 'tbody': {'tr'}, 'tfoot': {'tr'}, 'tr': {'td', 'th'}}
        if parent in permitted:
            assert tag in permitted[parent], (parent, tag)
        if tag == 'th':
            assert a.get('scope') in {'col', 'row'}, a
        if tag == 'meter':
            assert a.get('aria-label'), a
        if tag == 'summary':
            assert parent == 'details'
        if 'href' in a:
            assert a['href'].startswith('#'), a
        if tag not in {'br', 'hr', 'input', 'wbr'}:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        assert self.stack and self.stack.pop() == tag, tag


def main():
    from app.main import create_app

    result = {'implementation_scope': 'Phases 5.5 / 6: documentation, Inference Provenance and Audit Ledger only', 'checks': {}}
    checks = result['checks']
    template = ROOT / 'dashboard/templates/index.html'
    before, after = old(str(template.relative_to(ROOT))), template.read_text()
    old_dom, new_dom = Assets(), Assets()
    old_dom.feed(before)
    new_dom.feed(after)
    assert set(old_dom.ids) <= set(new_dom.ids)
    old_counts, new_counts = Counter(old_dom.ids), Counter(new_dom.ids)
    assert all(new_counts[name] == (1 if name == 'coverage' else count) for name, count in old_counts.items())
    assert all(count == 1 for name, count in new_counts.items() if name not in old_counts)
    assert len(new_dom.ids) == len(set(new_dom.ids))
    assert new_counts['overview-coverage'] == 1
    result['duplicate_ids'] = []
    assert sorted(old_dom.forms, key=str) == sorted(new_dom.forms, key=str)
    # Existing accessible aliases remain stable. Data integrity receives an
    # explicit alias preserving the prior case-sensitive browser-test name.
    for page, alias in old_dom.navigation.items():
        if alias:
            assert new_dom.navigation[page] == alias
    assert set(old_dom.navigation) == set(new_dom.navigation)
    sections = lambda text: dict(re.findall(r'<section id="([^"]+)"[^>]*>(.*?)</section>', text, re.S))
    old_sections, new_sections = sections(before), sections(after)
    assert old_sections.keys() == new_sections.keys()
    for name, content in old_sections.items():
        if name not in {'overview', 'datasets', 'contributors-page', 'models', 'inference', 'ledger'}:
            assert markup_without_presentation(content) == markup_without_presentation(new_sections[name]), name
    approved_html = subprocess.check_output(['git', 'show', APPROVED_OVERVIEW + ':dashboard/templates/index.html'], cwd=ROOT).decode()
    approved_sections = sections(approved_html)
    assert new_sections['overview'] == approved_sections['overview'].replace('id="coverage"', 'id="overview-coverage"')
    # Visibility remains application-owned, including the pre-existing .page name.
    for name, classes in re.findall(r'<section id="([^"]+)" class="([^"]+)"', before):
        assert '<section id="' + name + '" class="' + classes + '"' in after
    assert '<label for="record-json" class="form-label">Signed inference record JSON</label>' in after
    warning = 'Composite scores and confidence are heuristic, not calibrated probabilities. Cryptographic failures establish integrity violations; heuristic anomalies require analyst review.'
    assert warning in new_sections['overview']
    assert re.findall(r'data-filter="([^"]+)"', before) == re.findall(r'data-filter="([^"]+)"', after)
    checks['existing_ids_forms_navigation_and_protected_screen_internals'] = 'PASS'
    checks['overview_filters_warning_and_record_label'] = 'PASS'

    for path in ['dashboard/static/app.js', 'dashboard/static/workstation.css']:
        assert restore_legacy_classes(restore_generation_feedback((ROOT / path).read_text())) == old(path), path
    workstation = (ROOT / 'dashboard/static/workstation.js').read_text()
    assert protected_workstation(workstation) == protected_workstation(old('dashboard/static/workstation.js'))
    for path in ['dashboard/static/overview.css', 'dashboard/static/primitives.css', 'dashboard/static/shell.css']:
        approved = subprocess.check_output(['git', 'show', APPROVED_OVERVIEW + ':' + path], cwd=ROOT)
        assert (ROOT / path).read_bytes() == approved, path
    approved_workstation = subprocess.check_output(['git', 'show', APPROVED_MODEL + ':dashboard/static/workstation.js'], cwd=ROOT).decode()
    assert protected_phase6(workstation) == protected_phase6(approved_workstation), 'Protected renderer changed'
    approved_template = subprocess.check_output(['git', 'show', APPROVED_MODEL + ':dashboard/templates/index.html'], cwd=ROOT).decode()
    for name, content in sections(approved_template).items():
        if name not in {'inference', 'ledger'}:
            assert new_sections[name] == content, name
    for path in ['dashboard/static/investigations.css', 'dashboard/static/model-integrity.css']:
        assert (ROOT / path).read_bytes() == subprocess.check_output(['git', 'show', APPROVED_MODEL + ':' + path], cwd=ROOT)
    assert restore_generation_feedback((ROOT / 'dashboard/static/app.js').read_text()) == subprocess.check_output(['git', 'show', APPROVED_MODEL + ':dashboard/static/app.js'], cwd=ROOT).decode()
    # All form markup is preserved exactly, regardless of the surrounding layout order.
    forms = lambda source: sorted(re.findall(r'<form\b.*?</form>', source, re.S))
    assert forms(after) == forms(approved_template)
    for selector in ['trigger-preview', 'mask-preview']:
        assert 'id="' + selector + '"' in workstation
    checks['phases_3_to_5_frozen_and_form_contract_preserved'] = 'PASS'
    checks['approved_overview_generic_styles_and_protected_renderers_unchanged'] = 'PASS'
    shell = (ROOT / 'dashboard/static/shell.css').read_text()
    assert not re.search(r'#workspace\s+\.(row|card|badge)\b', shell)
    for path in ['dashboard/static/style.css', 'dashboard/static/workstation.css']:
        assert not re.search(r'\.(row|card|badge)(?![\w-])', (ROOT / path).read_text()), path
    checks['legacy_generic_class_collisions_removed'] = 'PASS'
    # All baseline files outside the two approved frontend edits must match.
    allowed = {'dashboard/templates/index.html', 'dashboard/static/style.css', 'dashboard/static/app.js', 'dashboard/static/workstation.css', 'dashboard/static/workstation.js', 'tests/test_ui_contract.py'}
    tracked = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASELINE], cwd=ROOT).decode().splitlines()
    for path in tracked:
        if path not in allowed:
            expected = subprocess.check_output(['git', 'show', BASELINE + ':' + path], cwd=ROOT)
            assert (ROOT / path).read_bytes() == expected, path
    checks['frozen_baseline_files_unchanged'] = 'PASS'

    vendor = ROOT / 'dashboard/static/vendor/tabler'
    manifest = json.loads((vendor / 'manifest.json').read_text())
    for name, entry in manifest['files'].items():
        assert hashlib.sha256((vendor / name).read_bytes()).hexdigest() == entry['sha256'], name
    checks['vendor_file_integrity'] = 'PASS'

    with tempfile.TemporaryDirectory() as directory:
        app = create_app(directory, testing=True)
        client = app.test_client()
        response = client.get('/')
        assert response.status_code == 200
        assert response.headers['Content-Security-Policy'] == "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'"
        rendered = response.get_data(as_text=True)
        dom = Assets()
        dom.feed(rendered)
        assert len(dom.ids) == len(set(dom.ids)), 'Rendered duplicate IDs'
        assert 'aegis-token' in rendered
        for path in dom.assets:
            assert path.startswith('/static/'), path
            assert client.get(path).status_code == 200, path
        assert client.get('/api/health').json['status'] == 'ok'
        checks['flask_render_csp_and_local_asset_routes'] = 'PASS'
        checks['local_assets_served'] = len(dom.assets)

    styles = list((ROOT / 'dashboard/static').rglob('*.css'))
    for path in styles:
        css = re.sub(r'/\*[\s\S]*?\*/', '', path.read_text())
        assert not re.search(r'@import\b', css), path
        for url in re.findall(r'url\((.*?)\)', css, re.S):
            url = url.strip(' \t\n\'"')
            assert url.startswith(('data:', '/static/', '#')), (path, url)
    assert not re.search(r'(?<![-\w.#])svg\s*\{', (ROOT / 'dashboard/static/style.css').read_text())
    vendor_js = (vendor / 'js/tabler.min.js').read_text()
    for api in ['fetch(', 'XMLHttpRequest', 'WebSocket', 'sendBeacon', 'sourceMappingURL']:
        assert api not in vendor_js, api
    checks['external_asset_static_check'] = 'PASS'
    checks['plot_svg_scoped'] = 'PASS'
    executed = json.loads(subprocess.check_output(['node', 'scripts/check_investigation_ui.js'], cwd=ROOT))
    model_executed = json.loads(subprocess.check_output(['node', 'scripts/check_model_ui.js'], cwd=ROOT))
    checks['model_renderer_semantics_and_preview_pixels'] = model_executed['status']
    executed['fragments'].update(model_executed['fragments'])
    from ui_verification_fixtures import fixtures
    verification = json.loads(subprocess.check_output(['node', 'scripts/check_verification_ui.js'], input=json.dumps(fixtures()).encode(), cwd=ROOT))
    checks['inference_ledger_renderer_and_action_contract'] = verification['status']
    executed['fragments'].update(verification['fragments'])
    for name, fragment in executed['fragments'].items():
        parsed = FragmentStructure()
        parsed.feed(fragment)
        assert not parsed.stack, (name, parsed.stack)
        assert len(parsed.ids) == len(set(parsed.ids)), name
    checks['executed_renderer_selection_order_values_missing_data_and_escaping'] = executed['status']
    checks['generated_html_structure_meter_labels_no_inline_styles_or_duplicate_ids'] = 'PASS'
    # Report all requested search terms, including harmless license/namespace
    # occurrences, instead of incorrectly treating a raw URL match as a load.
    terms = ['http://', 'https://', 'cdn', 'jsdelivr', 'unpkg', 'fonts.googleapis', 'fonts.gstatic']
    result['source_term_occurrences'] = {}
    for path in sorted((ROOT / 'dashboard').rglob('*')):
        if path.suffix in {'.html', '.css', '.js', '.svg'}:
            text = path.read_text().lower()
            hits = {term: text.count(term) for term in terms if term in text}
            if hits:
                result['source_term_occurrences'][str(path.relative_to(ROOT))] = hits
    result.update(visual_validation='PENDING — NO BROWSER AVAILABLE', browser_regression='NOT RUN',
                  screenshots='NOT AVAILABLE', responsive_behavior='NOT VERIFIED',
                  runtime_external_requests='NOT MEASURED', tabler_ui_freeze='NO')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
