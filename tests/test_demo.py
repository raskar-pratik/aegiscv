import tempfile
import unittest
from pathlib import Path
from demo.runner import run_demo


class DemoTests(unittest.TestCase):
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as t:
            result=run_demo(Path(t)/'demo'); v=result['verification']
            self.assertEqual(result['clean']['assurance']['recommended_action'],'ACCEPT')
            self.assertGreater(result['attacked']['assurance']['risk_score'],result['clean']['assurance']['risk_score'])
            self.assertEqual(result['attacked']['contributors'][0]['contributor'],'Contributor-B')
            self.assertEqual(v['valid_inference']['status'],'VALID')
            self.assertEqual(v['tampered_inference']['status'],'TAMPERED')
            self.assertEqual(v['replay']['status'],'REPLAY')
            self.assertEqual(v['tampered_ledger']['sequence'],1)
            self.assertEqual(v['model_substitution']['risk_score'],100)
