import tempfile
import unittest
from pathlib import Path
from core.config import Config
from adapters.datasets.ingestion import ingest
from detectors.data_integrity.features import VisualEncoder
from detectors.data_integrity.engine import duplicates, labels, ood, contributors
from attack_simulator.datasets import generate


class DataTests(unittest.TestCase):
    def test_seeded_attacks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); clean=root/'clean'; bad=root/'bad'
            generate(clean); generate(bad,attack='combined')
            encoder=VisualEncoder(); cfg=Config(near_hamming=0,near_color_distance=.001)
            ca=ingest(clean)['assets']; ba=ingest(bad)['assets']
            cf=encoder.encode([clean/a['asset_id'] for a in ca]); bf=encoder.encode([bad/a['asset_id'] for a in ba])
            self.assertFalse(any(f['risk_score'] for f in labels(ca,cf,cfg)))
            results=duplicates(ba,bad,bf,cfg)+labels(ba,bf,cfg)+ood(ba,bf,cfg,cf)
            self.assertTrue(any(f['detector']=='exact_duplicate' and f['risk_score']>0 for f in results))
            self.assertTrue(any('flipped' in f['asset_id'] for f in results))
            self.assertTrue(any(f['detector']=='ood' and f['risk_score']>0 for f in results))
            self.assertEqual(contributors(ba,results)[0]['contributor'],'Contributor-B')
            self.assertEqual(ood(ba,bf,cfg)[0]['status'],'UNAVAILABLE')
