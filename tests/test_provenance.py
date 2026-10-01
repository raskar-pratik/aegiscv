import copy
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from provenance.ledger import Ledger, verify_record, verify_ledger
from provenance.hashing import digest


class ProvenanceTests(unittest.TestCase):
    def test_tamper_replay_checkpoint_and_restart(self):
        with tempfile.TemporaryDirectory() as t:
            ledger=Ledger(t); a=ledger.append('test',{'value':1},nonce='fixed')
            self.assertEqual(verify_record(a,ledger.public)['status'],'VALID')
            self.assertEqual(ledger.accept(a)['status'],'VALID')
            self.assertEqual(Ledger(t).accept(a)['status'],'REPLAY')
            with self.assertRaises(ValueError): ledger.append('test',{},nonce='fixed')
            b=ledger.append('test',{'value':2}); records=ledger.records(); checkpoint=verify_ledger(records,ledger.public)
            self.assertEqual(checkpoint['status'],'VALID')
            changed=copy.deepcopy(records); changed[0]['payload']['value']=9
            self.assertEqual(verify_ledger(changed,ledger.public)['sequence'],1)
            self.assertEqual(verify_ledger(records[:1],ledger.public,checkpoint)['status'],'TAMPERED')
            a['payload']['value']=3; a['record_hash']=digest({k:v for k,v in a.items() if k not in {'record_hash','signature'}})
            self.assertEqual(verify_record(a,ledger.public)['status'],'SIGNATURE_INVALID')

    def test_concurrent_append(self):
        with tempfile.TemporaryDirectory() as t:
            ledger=Ledger(t)
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(lambda i:ledger.append('test',{'i':i}),range(12)))
            result=verify_ledger(ledger.records(),ledger.public)
            self.assertEqual(result['status'],'VALID'); self.assertEqual(result['count'],12)
