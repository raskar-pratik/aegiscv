"""Regression coverage for model identity, inference type and report integrity."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

from adapters.datasets.ingestion import ingest
from app.main import create_app
from app.services.scanner import scan_dataset
from provenance.inference_record import infer
from provenance.ledger import verify_ledger
from reports.generator import render


class ReviewFixTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app=create_app(self.temp.name,testing=True)
        self.addCleanup(self.app.extensions['worker'].shutdown,wait=True)
        self.client=self.app.test_client()
        self.headers={'X-Aegis-Token':self.app.config['TOKEN']}
        self.root=Path(self.temp.name)/'imports'
        self.data=self.root/'data'; self.data.mkdir()
        for i in range(3): Image.new('RGB',(32,32),(i*70,50,40)).save(self.data/f'{i}.png')
        self.model=self.root/'model.bin'; self.model.write_bytes(b'original')
        response=self.post('/models',{'path':'model.bin','format':'unsupported'})
        self.assertEqual(response.status_code,201)
        self.registered=response.json

    def post(self,path,data):
        return self.client.post('/api'+path,json=data,headers=self.headers)

    def scan(self,**extra):
        response=self.post('/scans',{'path':'data','model_id':self.registered['id'],**extra})
        self.assertEqual(response.status_code,202,response.json)
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            row=self.client.get('/api/scans/'+response.json['id']).json
            if row['status'] in {'COMPLETE','FAILED'}: break
            time.sleep(.02)
        self.assertEqual(row['status'],'COMPLETE',row)
        return row['data']

    def test_blank_optional_digest_does_not_quarantine(self):
        report=self.scan(expected_hash='  ')
        finding=next(f for f in report['findings'] if f['detector']=='model_hash')
        self.assertEqual(finding['risk_score'],0)
        self.assertIsNone(finding['evidence']['expected'])
        self.assertNotEqual(report['final_disposition'],'QUARANTINE')

    def test_invalid_digest_rejected_before_queueing(self):
        for value in ['wrong','g'*64,23]:
            response=self.post('/scans',{'path':'data','model_id':self.registered['id'],'expected_hash':value})
            self.assertEqual(response.status_code,400,response.json)
        self.assertEqual(self.client.get('/api/scans').json,[])

    def test_registered_substitution_overrides_missing_or_matching_reference(self):
        self.model.write_bytes(b'replaced')
        from adapters.datasets.ingestion import digest_file
        for extra in [{},{'expected_hash':digest_file(self.model).upper()}]:
            report=self.scan(**extra)
            finding=next(f for f in report['findings'] if f['detector']=='model_hash')
            self.assertEqual(finding['risk_score'],100)
            self.assertEqual(finding['evidence']['registered'],self.registered['sha256'])
            self.assertEqual(report['final_disposition'],'QUARANTINE')

    def test_unchanged_model_with_wrong_trusted_digest_is_quarantined(self):
        report=self.scan(expected_hash='0'*64)
        self.assertEqual(report['final_disposition'],'QUARANTINE')

    def test_inference_endpoints_reject_scan_without_consuming_replay_state(self):
        ledger=self.app.extensions['ledger']
        record=ledger.append('scan',{'scan_id':'example'})
        for endpoint in ['/inference/verify','/inference/accept']:
            response=self.post(endpoint,{'record':record,'bindings':{'input_hash':'wrong'}})
            self.assertEqual(response.status_code,400,response.json)
        self.assertEqual(verify_ledger(ledger.records(),ledger.public)['status'],'VALID')
        self.assertEqual(ledger.accept(record)['status'],'VALID')

    def test_inference_verification_bindings_and_replay_still_work(self):
        class Adapter:
            identity='a'*64
            def predict(self,x): return np.array([[.2,.8]],dtype=np.float32)
        record=infer(Adapter(),self.data/'0.png',self.app.extensions['ledger'])
        self.assertEqual(self.post('/inference/verify',{'record':record}).json['status'],'VALID')
        self.assertEqual(self.post('/inference/verify',{'record':record,'bindings':{'input_hash':'wrong'}}).json['status'],'TAMPERED')
        self.assertEqual(self.post('/inference/accept',{'record':record}).json['status'],'VALID')
        self.assertEqual(self.post('/inference/accept',{'record':record}).json['status'],'REPLAY')

    def test_coco_canonical_paths_preserve_annotations_and_reject_aliases(self):
        document={'images':[{'id':1,'file_name':'./0.png'}],
                  'categories':[{'id':1,'name':'cat'}],
                  'annotations':[{'id':1,'image_id':1,'category_id':1,'bbox':[1,1,10,10]}]}
        path=self.data/'annotations.json'; path.write_text(json.dumps(document))
        asset=ingest(self.data,'coco')['assets'][0]
        self.assertEqual(asset['asset_id'],'0.png')
        self.assertEqual(asset['labels'],['cat'])
        self.assertEqual(asset['boxes'],[[1,1,10,10]])
        self.assertEqual(len(asset['object_annotations']),1)
        document['images'].append({'id':2,'file_name':'0.png'})
        path.write_text(json.dumps(document))
        with self.assertRaisesRegex(ValueError,'Duplicate COCO image paths'): ingest(self.data,'coco')
        document['images']=[{'id':1,'file_name':'../outside.png'}]
        path.write_text(json.dumps(document))
        with self.assertRaisesRegex(ValueError,'escapes dataset root'): ingest(self.data,'coco')

    def test_audit_write_failure_updates_displayed_coverage_and_confidence(self):
        ledger=self.app.extensions['ledger']
        original=scan_dataset(self.data,ledger=ledger)
        with patch.object(ledger,'append',side_effect=OSError('disk full')):
            report=scan_dataset(self.data,ledger=ledger)
        self.assertEqual(report['audit_append']['status'],'FAILED')
        self.assertLess(report['coverage'],original['coverage'])
        self.assertLess(report['confidence'],original['confidence'])
        self.assertEqual(report['coverage'],report['assurance']['coverage_fraction'])
        self.assertEqual(report['confidence'],report['assurance']['confidence'])
        self.assertIn(f"{report['coverage']*100:.0f}%",render(report))
