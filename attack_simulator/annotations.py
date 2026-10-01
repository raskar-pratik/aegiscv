"""Deterministic object annotation corruption fixtures in both supported formats."""
import json
from pathlib import Path
import numpy as np
from PIL import Image


def generate_annotations(destination: Path,format='coco',poisoned=False,seed=26228):
    if format not in {'coco','yolo'}: raise ValueError('Expected COCO or YOLO')
    destination.mkdir(parents=True,exist_ok=False); rng=np.random.default_rng(seed); images=[]; annotations=[]; truth=[]
    for i in range(12):
        name=f'{i:02}.png'; Image.fromarray(rng.integers(0,255,(64,64,3),dtype=np.uint8)).save(destination/name)
        bad=poisoned and i>=9
        images.append({'id':i,'file_name':name}); annotations.append({'id':i,'image_id':i,'category_id':i%2,'bbox':[60 if bad else 10,10,16,16]})
        if format=='yolo': (destination/f'{i:02}.txt').write_text(f'{i%2} {1.0625 if bad else .28125} .28125 .25 .25')
        if bad: truth.append(name)
    if format=='coco': (destination/'annotations.json').write_text(json.dumps({'images':images,'annotations':annotations,'categories':[{'id':0,'name':'object-a'},{'id':1,'name':'object-b'}]}))
    return truth
