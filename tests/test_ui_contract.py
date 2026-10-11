import unittest
import re
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DashboardContractTests(unittest.TestCase):
    def test_judge_facing_ids_and_labels_exist(self):
        html = (ROOT / 'dashboard' / 'templates' / 'index.html').read_text(encoding='utf-8')
        for value in ['id="score"', 'decision-trigger', 'why-title', 'contributors', 'findings', 'provenance-chain', 'ledger-state', 'coverage-list', 'Run reproducible demonstration', 'Verify altered copy']:
            self.assertIn(value, html)
        from app.main import create_app
        with tempfile.TemporaryDirectory() as directory:
            rendered = create_app(directory, testing=True).test_client().get('/').get_data(as_text=True)
        ids = re.findall(r'\bid="([^"]+)"', rendered)
        self.assertEqual(len(ids), len(set(ids)), 'Rendered HTML contains duplicate IDs')
        self.assertIn('<b id="overview-coverage">', rendered)
        self.assertIn('<section id="coverage"', rendered)
        self.assertIn('data-page="coverage"', rendered)
        self.assertIn('id="coverage-list"', rendered)
        js = (ROOT / 'dashboard/static/app.js').read_text(encoding='utf-8')
        self.assertIn("$('overview-coverage').textContent", js)
        self.assertNotIn("$('coverage').textContent", js)

    def test_dashboard_has_no_external_assets(self):
        for name in ['index.html', 'app.js', 'style.css']:
            text = (ROOT / 'dashboard' / ('templates' if name == 'index.html' else 'static') / name).read_text(encoding='utf-8').lower()
            self.assertNotIn('http://', text)
            self.assertNotIn('https://', text)

    def test_report_contract_fields_are_rendered(self):
        text = (ROOT / 'reports' / 'generator.py').read_text(encoding='utf-8').lower()
        for value in ['final disposition', 'composite pipeline risk', 'maximum asset risk', 'confidence', 'coverage', 'decision contract']:
            self.assertIn(value, text)


if __name__ == '__main__':
    unittest.main()
