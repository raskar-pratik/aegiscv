import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from detectors.data_integrity.features import VisualEncoder
from detectors.data_integrity.encoder import CachedEncoder
from detectors.data_integrity.resnet_encoder import select_encoder,ResNet18Encoder
from detectors.data_integrity.spectral import spectral_signatures


class EncoderSpectralTests(unittest.TestCase):
    def test_fallback_and_cache_invalidation(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); path=root/'x.png'; Image.new('RGB',(32,32),'red').save(path)
            encoder,status=select_encoder(root/'missing.pt')
            self.assertEqual(status['status'],'FALLBACK')
            cache=CachedEncoder(encoder,root/'cache'); first=cache.encode_image(path)
            np.testing.assert_array_equal(first,cache.encode_image(path)); self.assertEqual(cache.hits,1)
            Image.new('RGB',(32,32),'blue').save(path)
            self.assertFalse(np.array_equal(first,cache.encode_image(path))); self.assertEqual(cache.misses,2)
            other=VisualEncoder(); other.encoder_hash='changed-preprocessing'
            cache2=CachedEncoder(other,root/'cache'); cache2.encode_image(path); self.assertEqual(cache2.hits,0)

    def test_local_resnet_determinism_without_network(self):
        import torch
        from torchvision.models import resnet18
        with tempfile.TemporaryDirectory() as t, patch('torch.hub.download_url_to_file',side_effect=AssertionError('Network forbidden')):
            root=Path(t); path=root/'test.png'; Image.new('RGB',(40,50),'green').save(path)
            # Random test weights validate mechanics only; these are NOT pretrained metrics.
            with torch.random.fork_rng():
                torch.manual_seed(5); model=resnet18(weights=None)
            torch.save(model.state_dict(),root/'weights.pt')
            encoder=ResNet18Encoder(root/'weights.pt',batch_size=1)
            first=encoder.encode_image(path); second=encoder.encode_image(path)
            self.assertEqual(first.shape,(512,)); np.testing.assert_array_equal(first,second)
            self.assertAlmostEqual(float(np.linalg.norm(first)),1,places=5)
            self.assertEqual(encoder.capability()['status'],'LOCAL_WEIGHTS_LOADED')
            cache=CachedEncoder(encoder,root/'cache'); cache.encode_image(path)
            prior_hash=encoder.encoder_hash
            state=model.state_dict(); state['conv1.weight']=state['conv1.weight']+.01
            torch.save(state,root/'weights.pt')
            with self.assertRaises(ValueError): cache.encode_image(path)
            replacement=ResNet18Encoder(root/'weights.pt')
            self.assertNotEqual(replacement.encoder_hash,prior_hash)
            new_cache=CachedEncoder(replacement,root/'cache'); new_cache.encode_image(path)
            self.assertEqual(new_cache.hits,0)

    def test_spectral_seeded_subpopulation(self):
        rng=np.random.default_rng(26228); x=rng.normal(0,.03,(100,12)); x[-5:,0]+=3
        assets=[{'asset_id':str(i),'labels':['object'],'contributor':'B' if i>=95 else 'A'} for i in range(100)]
        first=spectral_signatures(assets,x); second=spectral_signatures(assets,x)
        self.assertEqual([f['asset_id'] for f in first],[f['asset_id'] for f in second])
        predicted={f['asset_id'] for f in first if f['risk_score']>20}
        self.assertEqual(predicted,{str(i) for i in range(95,100)})
        self.assertIn('percentile',first[0]['evidence'])
        self.assertEqual(spectral_signatures(assets[:2],x[:2])[0]['status'],'UNAVAILABLE')
