import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image, PngImagePlugin
from adapters.datasets.ingestion import ingest
from adapters.models.runtime import ModelAdapter
from detectors.data_integrity.features import VisualEncoder
from detectors.data_integrity.engine import duplicates
from core.config import Config
from core.schemas import Finding
from core.risk import fuse


class RegressionTests(unittest.TestCase):
    def test_near_duplicate_different_bytes(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); image=Image.fromarray(np.random.default_rng(1).integers(0,255,(32,32,3),dtype='uint8'))
            image.save(root/'a.png'); metadata=PngImagePlugin.PngInfo(); metadata.add_text('source','re-encoded'); image.save(root/'b.png',pnginfo=metadata)
            a=ingest(root)['assets']; f=VisualEncoder().encode([root/x['asset_id'] for x in a])
            results=duplicates(a,root,f,Config())
            self.assertTrue(any(r['detector']=='near_duplicate' and r['risk_score']>0 for r in results))
            self.assertFalse(any(r['detector']=='exact_duplicate' and r['risk_score']>0 for r in results))

    def test_safe_pytorch_and_missing_onnx(self):
        import torch
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'model.pt'; model=torch.nn.Linear(3,2); torch.save(model.state_dict(),path)
            adapter=ModelAdapter(str(path),'pytorch',factory=lambda:torch.nn.Linear(3,2))
            self.assertEqual(adapter.access,'FULL_WHITE_BOX')
            self.assertEqual(adapter.predict(np.ones((1,3),dtype=np.float32)).shape,(1,2))
            self.assertEqual(ModelAdapter(str(path),'pytorch').access,'LIMITED_WHITE_BOX')
            adapter=ModelAdapter(str(path),'onnx',trusted=True)
            self.assertIsNone(adapter.runtime); self.assertTrue(adapter.reason)

    def test_verified_violation_cannot_be_diluted(self):
        rows=[Finding('model_hash','MODEL_INTEGRITY','MODEL_SUBSTITUTION','m',100,1,'Mismatch',{}).to_dict(),Finding('ood','DATA_INTEGRITY','OOD','x',25,.5,'Anomaly',{}).to_dict()]
        self.assertEqual(fuse(rows)['recommended_action'],'QUARANTINE')

    def test_invalid_ledger_still_produces_report(self):
        from provenance.ledger import Ledger,verify_ledger
        from attack_simulator.datasets import generate
        from app.services.scanner import scan_dataset
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); generate(root/'clean'); ledger=Ledger(root/'state'); ledger.append('test',{})
            with ledger.connect() as db: db.execute("UPDATE entries SET record=?", ('{"nonce":"n","record_id":"r","sequence_number":1}',))
            report=scan_dataset(root/'clean',reference=root/'clean',ledger=ledger)
            self.assertEqual(report['assurance']['recommended_action'],'QUARANTINE')
            self.assertEqual(report['audit_append']['status'],'FAILED')
            self.assertEqual(verify_ledger([{'nonce':[]}],ledger.public)['status'],'TAMPERED')
