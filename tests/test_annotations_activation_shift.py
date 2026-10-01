import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from adapters.datasets.ingestion import ingest
from detectors.data_integrity.annotations import annotation_integrity
from detectors.model_integrity.activation_analysis import cluster_representations,analyze_activations
from detectors.distribution_shift.embedding_shift import compare
from attack_simulator.backdoor_validation import create_adapter,samples


class AnnotationActivationShiftTests(unittest.TestCase):
    def test_coco_geometry_and_sources(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); Image.new('RGB',(100,100)).save(root/'a.png')
            boxes=[[90,90,20,20],[2,2,-3,4],[1,1,0,3],[0,0,100,100],[1,1,5,5],[1,1,5,5],[1,1,5,5]]
            data={'images':[{'id':1,'file_name':'a.png'}],'categories':[{'id':0,'name':'cat'},{'id':1,'name':'dog'}],'annotations':[{'id':i,'image_id':1,'category_id':1 if i==6 else 0,'bbox':b} for i,b in enumerate(boxes)]}
            (root/'annotations.json').write_text(json.dumps(data)); (root/'contributors.json').write_text('{"a.png":"B"}')
            manifest=ingest(root,'coco'); self.assertEqual(len(manifest['assets']),1)
            findings=annotation_integrity(manifest); reasons=' '.join(f['reason'] for f in findings)
            for expected in ['outside image','Negative','Zero-area','Extreme','Duplicate','Conflicting','Contributor']: self.assertIn(expected,reasons)
            self.assertTrue(all('annotation_id' in f['evidence'] for f in findings if f['detector']=='annotation_integrity'))

    def test_yolo_boundary_and_malformed_retention(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); Image.new('RGB',(100,100)).save(root/'a.png')
            (root/'a.txt').write_text('0 .95 .5 .2 .4\n0 .5 .5 -.2 .4\n0 .5 .5 0 .2\n0 nan .5 .2 .2')
            manifest=ingest(root,'yolo'); self.assertEqual(len(manifest['assets']),1)
            reasons=' '.join(f['reason'] for f in annotation_integrity(manifest))
            for expected in ['outside image','Negative','Zero-area','Nonfinite']: self.assertIn(expected,reasons)

    def test_annotation_population_statistics(self):
        objects=[{'annotation_id':str(i),'file':'annotations.json','label':'common' if i<29 else 'rare','bbox':[1,1,5,5],'encoding':'coco_xywh','issues':[]} for i in range(30)]
        manifest={'format':'coco','assets':[{'asset_id':'a','width':100,'height':100,'contributor':'B','object_annotations':objects}]}
        findings=annotation_integrity(manifest,max_boxes=10)
        reasons=' '.join(f['reason'] for f in findings)
        self.assertIn('boxes per image',reasons); self.assertIn('class frequency',reasons); self.assertIn('Contributor',reasons)

    def test_activation_clusters_and_access(self):
        rng=np.random.default_rng(3); x=rng.normal(0,.02,(60,8)); x[-6:,0]+=3
        assets=[{'asset_id':str(i),'labels':['class']} for i in range(len(x))]
        result=cluster_representations(assets,x)
        self.assertEqual(set(result[0]['evidence']['members']),{str(i) for i in range(54,60)})
        with tempfile.TemporaryDirectory() as t:
            adapter=create_adapter(Path(t)); images,y=samples(per_class=12)
            self.assertEqual(adapter.get_features(images).shape,(72,6))
            adapter.runtime=None
            self.assertEqual(analyze_activations(adapter,images,assets)[0]['status'],'UNAVAILABLE')

    def test_shift_metrics_and_missing_signals(self):
        rng=np.random.default_rng(26228); a=rng.normal(0,.05,(50,12)); b=a+1
        clean=compare(a,a,reference_labels=[['a']]*50,current_labels=[['a']]*50,reference_confidence=np.ones(50)*.9,current_confidence=np.ones(50)*.9)
        self.assertEqual(clean['risk_score'],0)
        shifted=compare(a,b,reference_labels=[['a']]*50,current_labels=[['b']]*50,reference_confidence=np.ones(50)*.9,current_confidence=np.ones(50)*.5)
        names=shifted['evidence']['triggered_metrics']
        for name in ['centroid_l2','mmd_squared','class_frequency_tv','confidence_mean_delta']: self.assertIn(name,names)
        self.assertTrue(compare(a,b)['evidence']['unavailable_metrics'])
