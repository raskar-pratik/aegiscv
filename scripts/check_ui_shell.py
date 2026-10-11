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
    return source


def markup_without_presentation(source):
    """Ignore class-only changes and the one explicitly authorized record label."""
    source = re.sub(r'<label for="record-json" class="form-label">Signed inference record JSON</label>', '', source)
    source = re.sub(r' class="[^"]*"', '', source)
    return re.sub(r'>\s+<', '><', source).strip()


def main():
    from app.main import create_app

    result = {'implementation_scope': 'Phases 2.5 and 3: generic presentation and Overview only', 'checks': {}}
    checks = result['checks']
    template = ROOT / 'dashboard/templates/index.html'
    before, after = old(str(template.relative_to(ROOT))), template.read_text()
    old_dom, new_dom = Assets(), Assets()
    old_dom.feed(before)
    new_dom.feed(after)
    assert set(old_dom.ids) <= set(new_dom.ids)
    old_counts, new_counts = Counter(old_dom.ids), Counter(new_dom.ids)
    assert all(new_counts[name] == count for name, count in old_counts.items())
    assert all(count == 1 for name, count in new_counts.items() if name not in old_counts)
    result['preexisting_duplicate_ids'] = {name: count for name, count in old_counts.items() if count > 1}
    assert old_dom.forms == new_dom.forms
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
        if name != 'overview':
            assert markup_without_presentation(content) == markup_without_presentation(new_sections[name]), name
    # Visibility remains application-owned, including the pre-existing .page name.
    for name, classes in re.findall(r'<section id="([^"]+)" class="([^"]+)"', before):
        assert '<section id="' + name + '" class="' + classes + '"' in after
    assert '<label for="record-json" class="form-label">Signed inference record JSON</label>' in after
    warning = 'Composite scores and confidence are heuristic, not calibrated probabilities. Cryptographic failures establish integrity violations; heuristic anomalies require analyst review.'
    assert warning in new_sections['overview']
    assert re.findall(r'data-filter="([^"]+)"', before) == re.findall(r'data-filter="([^"]+)"', after)
    checks['existing_ids_forms_navigation_and_protected_screen_internals'] = 'PASS'
    checks['overview_filters_warning_and_record_label'] = 'PASS'

    for path in ['dashboard/static/app.js', 'dashboard/static/workstation.js', 'dashboard/static/workstation.css']:
        assert restore_legacy_classes((ROOT / path).read_text()) == old(path), path
    checks['application_javascript_and_workstation_css_only_approved_class_renames'] = 'PASS'
    shell = (ROOT / 'dashboard/static/shell.css').read_text()
    assert not re.search(r'#workspace\s+\.(row|card|badge)\b', shell)
    for path in ['dashboard/static/style.css', 'dashboard/static/workstation.css']:
        assert not re.search(r'\.(row|card|badge)(?![\w-])', (ROOT / path).read_text()), path
    checks['legacy_generic_class_collisions_removed'] = 'PASS'
    # All baseline files outside the two approved frontend edits must match.
    allowed = {'dashboard/templates/index.html', 'dashboard/static/style.css', 'dashboard/static/app.js', 'dashboard/static/workstation.css'}
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
