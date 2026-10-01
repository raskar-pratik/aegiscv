import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from experiments.benchmark import generate,attack,validate_splits
from experiments.validation_metrics import evaluate
from experiments.final_validation import validate_result
from core.thresholds import freeze,apply_profile
from adapters.datasets.ingestion import ingest,digest_file
from detectors.data_integrity.resnet_encoder import select_encoder
from scripts.validate_checkpoint import validate


class FinalValidationTests(unittest.TestCase):
    def test_split_and_attack_reproducibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); counts={'train':2,'reference':2,'calibration':2,'evaluation':3}
            a=generate(root/'a',123,counts); b=generate(root/'b',123,counts)
            self.assertEqual(a,b)
            first=attack(root/'a'/'evaluation',root/'one','trigger',.2,4)
            second=attack(root/'b'/'evaluation',root/'two','trigger',.2,4)
            self.assertEqual(first,second); self.assertEqual(ingest(root/'one'),ingest(root/'two'))
            self.assertEqual(first['selected_count'],6)
            bad=copy.deepcopy(a['partitions']); bad['evaluation']['assets'][0]=bad['train']['assets'][0]
            with self.assertRaises(ValueError): validate_splits(bad)

    def test_threshold_partition_and_identity_enforcement(self):
        with self.assertRaises(ValueError): freeze({},['shared'],['shared'],'encoder',{})
        profile=freeze({'ood_distance':.12},['cal'],['held'],'encoder',{})
        self.assertEqual(apply_profile(profile,'encoder').ood_distance,.12)
        with self.assertRaises(ValueError): apply_profile(profile,'different')
        profile['values']['ood_distance']=.2
        with self.assertRaises(ValueError): apply_profile(profile,'encoder')

    def test_metrics_and_tied_ranking(self):
        row=evaluate('test','test',['a','b','c','d'],['a','b'],['a','c'],scores={'a':.5,'b':.5,'c':.5,'d':.5})
        self.assertEqual([row[k] for k in ['tp','fp','tn','fn']],[1,1,1,1])
        for key in ['precision','recall','f1','fpr','roc_auc','pr_auc']: self.assertEqual(row[key],.5)
        with self.assertRaises(ValueError): evaluate('x','x',['a'],['missing'],[])
        row=evaluate('x','clean',['a'],[],[])
        self.assertIsNone(row['recall']); self.assertIsNone(row['roc_auc'])

    def test_result_schema_rejects_inconsistent_counts(self):
        summary={k:{} for k in ['dataset','encoder','calibration_profile_hash','limitations','cross_layer']}; summary['judge_metrics']=[]
        row=evaluate('x','x',['a'],['a'],['a']); validate_result(summary,[row])
        row['fn']=1
        with self.assertRaises(ValueError): validate_result(summary,[row])

    def test_checkpoint_hash_and_offline_failure(self):
        with tempfile.TemporaryDirectory() as tmp,patch('socket.socket.connect',side_effect=AssertionError('Network forbidden')):
            path=Path(tmp)/'weights.pt'; path.write_bytes(b'incompatible checkpoint')
            self.assertEqual(validate(path,'0'*64)['status'],'CHECKSUM_MISMATCH')
            result=validate(path); self.assertEqual(result['sha256'],digest_file(path)); self.assertEqual(result['status'],'INCOMPATIBLE')
            with patch.dict('os.environ',{'AEGISCV_ENCODER':'resnet18','AEGISCV_ENCODER_WEIGHTS':str(path),'AEGISCV_ENCODER_SHA256':'0'*64}):
                _,capability=select_encoder(); self.assertEqual(capability['status'],'FALLBACK')
                self.assertIn('pinned SHA-256',capability['reason'])

    def test_calibration_excludes_evaluation_features(self):
        from experiments.final_validation import calibrate
        from detectors.data_integrity.features import VisualEncoder
        class RecordingEncoder(VisualEncoder):
            paths=[]
            def encode_batch(self,paths):
                self.paths.extend(str(p) for p in paths); return super().encode_batch(paths)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); benchmark=generate(root/'data',1,{'train':2,'reference':3,'calibration':3,'evaluation':3})
            output=root/'output'; output.mkdir(); encoder=RecordingEncoder()
            config,_,profile=calibrate(root/'data',encoder,benchmark,output)
            self.assertFalse(any('evaluation' in p for p in encoder.paths))
            self.assertTrue(set(profile['calibration_ids']).isdisjoint(profile['reserved_evaluation_ids']))

    def test_pinned_local_checkpoint_loads_with_socket_blocked(self):
        import torch
        from torchvision.models import resnet18
        with tempfile.TemporaryDirectory() as tmp,patch('socket.socket.connect',side_effect=AssertionError('Network forbidden')),patch('torch.hub.download_url_to_file',side_effect=AssertionError('Download forbidden')):
            path=Path(tmp)/'random-test-only.pt'
            with torch.random.fork_rng():
                torch.manual_seed(123); torch.save(resnet18(weights=None).state_dict(),path)
            sha=digest_file(path)
            with patch.dict('os.environ',{'AEGISCV_ENCODER':'resnet18','AEGISCV_ENCODER_WEIGHTS':str(path),'AEGISCV_ENCODER_SHA256':sha}):
                _,capability=select_encoder()
                self.assertEqual(capability['weights_sha256'],sha)
                self.assertTrue(capability['checksum_pinned']); self.assertEqual(capability['status'],'LOCAL_WEIGHTS_LOADED')
                self.assertEqual(capability['encoder_version'],'1')


if __name__=='__main__': unittest.main()
