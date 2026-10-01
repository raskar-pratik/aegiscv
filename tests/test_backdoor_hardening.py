import tempfile
import unittest
from pathlib import Path
import numpy as np
from attack_simulator.backdoor_validation import create_adapter,samples,measure
from detectors.model_integrity.neural_cleanse import reconstruct
from detectors.model_integrity.patch_probe import probe_patches


class BackdoorHardeningTests(unittest.TestCase):
    def test_measured_backdoor_and_reconstruction(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); adapter=create_adapter(root); x,y=samples(per_class=6)
            metrics=measure(adapter,x,y)
            self.assertEqual(metrics['clean_accuracy'],1)
            self.assertEqual(metrics['attack_success_rate'],1)
            self.assertEqual(metrics['attack_samples'],30)
            result=reconstruct(adapter,x,labels=y,steps=140)
            self.assertEqual(result['status'],'SUCCESS')
            candidates=[o for o in result['evidence']['outcomes'] if o['target']==2]
            self.assertEqual(candidates[0]['status'],'SUCCESS')
            self.assertGreaterEqual(candidates[0]['success'],.9)
            self.assertIn('mask',candidates[0]); self.assertIn('pattern',candidates[0])
            self.assertEqual(result['evidence']['target'],2)
            self.assertGreater(result['evidence']['anomaly_index'],2)
            self.assertGreater(result['risk_score'],20)
            clean=create_adapter(root,False)
            self.assertLess(reconstruct(clean,x,labels=y,steps=140)['risk_score'],20)
            self.assertLess(probe_patches(clean,x,patch_size=4)['risk_score'],20)
            self.assertGreater(probe_patches(adapter,x,patch_size=4)['risk_score'],20)

    def test_no_non_target_sources_not_invented(self):
        with tempfile.TemporaryDirectory() as t:
            adapter=create_adapter(Path(t)); x,y=samples(per_class=1)
            result=reconstruct(adapter,x[:1],steps=2)
            self.assertIsNone(result['evidence']['anomaly_index'])
            self.assertEqual(result['risk_score'],0)
