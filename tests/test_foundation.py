import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from adapters.datasets.ingestion import ingest, confined
from core.config import Config
from core.schemas import Finding
from core.risk import fuse
from app.main import create_app


class FoundationTests(unittest.TestCase):
    def test_folder_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'cat').mkdir()
            Image.new('RGB',(16,16),'red').save(root/'cat/a.png')
            a = ingest(root); b = ingest(root)
            self.assertEqual(a['manifest_hash'],b['manifest_hash'])
            self.assertEqual(a['assets'][0]['labels'],['cat'])
            Image.new('RGB',(16,16),'blue').save(root/'cat/a.png')
            self.assertNotEqual(a['manifest_hash'],ingest(root)['manifest_hash'])
            with self.assertRaises(ValueError): confined(root,'../escape')

    def test_annotation_adapters(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); Image.new('RGB',(16,16)).save(root/'a.png')
            (root/'annotations.json').write_text(json.dumps({'images':[{'id':1,'file_name':'a.png'}],'categories':[{'id':0,'name':'car'}],'annotations':[{'image_id':1,'category_id':0,'bbox':[1,1,3,3]}]}))
            self.assertEqual(ingest(root,'coco')['assets'][0]['labels'],['car'])
            (root/'a.txt').write_text('0 0.5 0.5 0.2 0.2')
            self.assertEqual(ingest(root,'yolo')['assets'][0]['labels'],['0'])

    def test_validation_and_coverage(self):
        with self.assertRaises(ValueError): Config(neighbors=0)
        f=Finding('x','MODEL_INTEGRITY','BACKDOOR','m',0,0,'No gradients',{},status='UNAVAILABLE').to_dict()
        self.assertEqual(fuse([f])['recommended_action'],'REVIEW')
        self.assertEqual(fuse([f])['confidence'],0)
        self.assertEqual(create_app().test_client().get('/api/health').status_code,200)
