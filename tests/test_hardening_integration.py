import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from attack_simulator.datasets import generate
from app.services.scanner import scan_dataset
from core.config import Config


class HardeningIntegrationTests(unittest.TestCase):
    def test_fallback_report_and_repeat_cache(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); generate(root/'clean')
            with patch('socket.create_connection',side_effect=AssertionError('Network forbidden')):
                first=scan_dataset(root/'clean',reference=root/'clean',config=Config(encoder_weights=str(root/'absent.pt')),cache_dir=root/'cache')
                second=scan_dataset(root/'clean',reference=root/'clean',cache_dir=root/'cache')
            self.assertEqual(first['encoder_capability']['status'],'FALLBACK')
            self.assertGreater(second['encoder_capability']['cache']['hits'],0)
            self.assertEqual(first['manifest']['manifest_hash'],second['manifest']['manifest_hash'])
            self.assertTrue(any(f['detector']=='spectral_signature' for f in first['findings']))
            self.assertIn('metrics',next(f for f in first['findings'] if f['detector']=='embedding_shift')['evidence'])
