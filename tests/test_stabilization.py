import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from core.schemas import Finding
from core.risk import fuse
from detectors.data_integrity.engine import contributors
from detectors.data_integrity.near_confirmation import profile

class StabilizationTests(unittest.TestCase):
    def test_monotonic_properties_and_unavailable_separation(self):
        rng=np.random.default_rng(91); categories=['DATA_INTEGRITY','MODEL_INTEGRITY','INFERENCE_INTEGRITY','DISTRIBUTION']
        for _ in range(500):
            rows=[Finding('signal_'+str(i),c,'TEST','same-context',float(rng.uniform(0,100)),.5,'test',{}).to_dict() for i,c in enumerate(categories)]
            before=fuse(rows); changed=copy.deepcopy(rows); i=int(rng.integers(4)); changed[i]['risk_score']=float(rng.uniform(changed[i]['risk_score'],100))
            self.assertGreaterEqual(fuse(changed)['risk_score'],before['risk_score'])
            extra=Finding('extra',categories[i],'TEST','same-context',float(rng.uniform(0,100)),.1,'test',{}).to_dict()
            self.assertGreaterEqual(fuse(rows+[extra])['risk_score'],before['risk_score'])
            unavailable=Finding('missing',categories[i],'TEST','same-context',0,0,'test',{},status='UNAVAILABLE').to_dict()
            after=fuse(rows+[unavailable]); self.assertEqual(after['risk_score'],before['risk_score']); self.assertLess(after['confidence'],before['confidence'])
            self.assertTrue(0<=after['risk_score']<=100)

    def test_calibrated_pairs_and_clean_sources(self):
        p=profile(); self.assertTrue(p['qualified']); self.assertLessEqual(p['image_fpr'],.02)
        self.assertTrue(all('calibration' in value for value in p['calibration_ids']))
        assets=[{'asset_id':str(i),'contributor':str(i%5)} for i in range(100)]
        noisy=[Finding('spectral_signature','DATA_INTEGRITY','TEST',str(i),90,.5,'test',{}).to_dict() for i in range(100)]
        self.assertFalse(any(r['risk_score']>20 for r in contributors(assets,noisy)))
        mixed=[Finding(name,'DATA_INTEGRITY','TEST','0',90,.8,'test',{'members':[str(i) for i in range(0,100,5)]}).to_dict() for name in ['label_anomaly','trigger_pattern','spectral_signature']]
        rows=contributors(assets,mixed); self.assertGreater(rows[0]['risk_score'],60); self.assertEqual(rows[0]['contributor'],'0')

    def test_reliability_does_not_mix_unrelated_severity_and_weight(self):
        assets=[{'asset_id':str(i),'contributor':'a'} for i in range(100)]
        noisy=Finding('spectral_signature','DATA_INTEGRITY','TEST','0',100,.9,'noise',{'members':[str(i) for i in range(100)]}).to_dict()
        rare=Finding('ood','DATA_INTEGRITY','TEST','0',30,.5,'rare',{}).to_dict()
        self.assertLessEqual(contributors(assets,[noisy,rare])[0]['risk_score'],20)

    def test_backdoor_single_evidence_is_review(self):
        from detectors.model_integrity.decision import assess
        reconstruction=Finding('neural_cleanse','MODEL_INTEGRITY','BACKDOOR','m',85,.55,'anomaly',{'target':2,'outcomes':[{'target':2,'status':'SUCCESS','success':1.}]}).to_dict()
        patch_result=Finding('patch_probe','MODEL_INTEGRITY','BACKDOOR','m',0,.65,'none',{}).to_dict()
        result=assess(reconstruction,patch_result); self.assertEqual(result['recommended_action'],'REVIEW'); self.assertEqual(result['verdict'],'SUSPICIOUS_EVIDENCE')
        self.assertEqual(reconstruction['recommended_action'],'REVIEW')

    def test_detector_exceptions_remain_visible(self):
        from attack_simulator.datasets import generate
        from app.services.scanner import scan_dataset
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); generate(root/'clean')
            for target in ['duplicates','labels','ood','spectral_signatures','detect_patterns','annotation_integrity','compare','compare_acquisition']:
                with self.subTest(target=target),patch('app.services.scanner.'+target,side_effect=RuntimeError('injected module failure')):
                    result=scan_dataset(root/'clean',reference=root/'clean',cache_dir=root/'cache')
                    self.assertTrue(any(f['status']=='FAILED' and 'injected module failure' in f['reason'] for f in result['findings']))
                    self.assertLess(result['assurance']['coverage_fraction'],1)
                    self.assertEqual(result['assurance']['recommended_action'],'REVIEW')

    def test_encoder_failure_falls_back_visibly(self):
        from attack_simulator.datasets import generate
        from app.services.scanner import scan_dataset
        from detectors.data_integrity.features import VisualEncoder
        class Broken(VisualEncoder):
            def encode_batch(self,paths): raise RuntimeError('encoder failure')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); generate(root/'clean')
            result=scan_dataset(root/'clean',reference=root/'clean',encoder=Broken(),cache_dir=root/'cache')
            self.assertEqual(result['encoder_capability']['status'],'FALLBACK')
            self.assertTrue(any(f['detector']=='feature_encoder' and f['status']=='FAILED' for f in result['findings']))

    def test_ledger_failure_is_not_fabricated_tampering(self):
        from attack_simulator.datasets import generate
        from app.services.scanner import scan_dataset
        from provenance.ledger import Ledger
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); generate(root/'clean'); ledger=Ledger(root/'ledger')
            with patch.object(ledger,'records',side_effect=RuntimeError('ledger read unavailable')):
                result=scan_dataset(root/'clean',reference=root/'clean',ledger=ledger)
                self.assertEqual(result['ledger_verification']['status'],'FAILED'); self.assertLess(result['assurance']['risk_score'],100)
            with patch.object(ledger,'append',side_effect=RuntimeError('ledger write unavailable')):
                result=scan_dataset(root/'clean',reference=root/'clean',ledger=ledger)
                self.assertEqual(result['audit_append']['status'],'FAILED'); self.assertLess(result['assurance']['coverage_fraction'],1)

    def test_acquisition_drift_and_clean_controls(self):
        from experiments.benchmark import generate,attack
        from detectors.distribution_shift.acquisition import compare_acquisition
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); b=generate(root/'data',26228,{'train':2,'reference':20,'calibration':20,'evaluation':30})
            reference=list((root/'data/reference').rglob('*.png')); current=list((root/'data/evaluation').rglob('*.png'))
            self.assertEqual(compare_acquisition(reference,current)['risk_score'],0)
            attack(root/'data/evaluation',root/'drift','benign_shift',1.)
            finding=compare_acquisition(reference,list((root/'drift').rglob('*.png')))
            self.assertGreater(finding['risk_score'],20); self.assertEqual(finding['reason'],'OPERATIONAL DISTRIBUTION SHIFT DETECTED')
            self.assertEqual(finding['recommended_action'],'REVIEW')

    def test_clusters_preserve_only_confirmed_edges(self):
        from PIL import Image
        from adapters.datasets.ingestion import ingest
        from detectors.data_integrity.engine import duplicates
        from core.config import Config
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for i in range(3): Image.new('RGB',(32,32),(20+i,20,20)).save(root/f'{i}.png')
            assets=ingest(root)['assets']; yes={'pixel_rmse':0.,'residual_correlation':1.}; no={'pixel_rmse':1.,'residual_correlation':0.}
            with patch('detectors.data_integrity.engine.dhash',return_value=0),patch('detectors.data_integrity.engine.compare',side_effect=[yes,no,yes]):
                findings=duplicates(assets,root,np.ones((3,1)),Config())
            cluster=next(f for f in findings if f['detector']=='near_duplicate' and f['risk_score']>0)
            self.assertEqual(len(cluster['evidence']['members']),3); self.assertEqual(len(cluster['evidence']['confirmed_pairs']),2)
            self.assertFalse(cluster['evidence']['transitive_pairs_verified'])

if __name__=='__main__': unittest.main()
