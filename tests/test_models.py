import tempfile
import unittest
from pathlib import Path
import numpy as np
from adapters.models.runtime import ModelAdapter
from attack_simulator.models import create_models
from detectors.model_integrity.fingerprint import inspect_model
from detectors.model_integrity.neural_cleanse import reconstruct
from provenance.inference_record import infer
from provenance.ledger import Ledger, verify_record
from PIL import Image


class ModelTests(unittest.TestCase):
    def test_identity_behavior_and_inference(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); a,b=create_models(root/'models')
            first=ModelAdapter(str(a),'torchscript',trusted=True); second=ModelAdapter(str(b),'torchscript',trusted=True)
            probes=np.ones((2,3,32,32),dtype=np.float32)
            original=inspect_model(first,probes=probes)
            changed=inspect_model(second,expected=first.identity,probes=probes,reference=original['behavior'])
            self.assertEqual(changed['findings'][0]['risk_score'],100)
            self.assertGreater(changed['findings'][1]['risk_score'],0)
            image=root/'image.png'; Image.new('RGB',(32,32),'red').save(image)
            ledger=Ledger(root/'state'); record=infer(first,image,ledger)
            self.assertEqual(verify_record(record,ledger.public)['status'],'VALID')
            self.assertEqual(verify_record(record,ledger.public,{'model_hash':'wrong'})['status'],'TAMPERED')
            record['payload']['output'][0][0]+=1
            self.assertEqual(verify_record(record,ledger.public)['status'],'TAMPERED')
            denied=ModelAdapter(str(a),'torchscript')
            self.assertIsNone(denied.runtime)
            self.assertEqual(reconstruct(denied,probes)['status'],'UNAVAILABLE')
            self.assertEqual(reconstruct(first,probes,steps=2)['status'],'SUCCESS')
