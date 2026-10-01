"""Seeded synthetic fixtures; no benchmark or real-world performance claims."""
import json
import shutil
from pathlib import Path
import numpy as np
from PIL import Image


def generate(destination: Path, seed: int = 26228, attack: str = 'clean') -> dict:
    if destination.exists(): raise ValueError('Simulator destination must be new')
    if attack not in {'clean','label_flip','duplicate_flood','ood','trigger','combined'}:
        raise ValueError('Unknown attack scenario')
    rng=np.random.default_rng(seed); destination.mkdir(parents=True)
    metadata,truth={},[]
    for cls,color in [('red',(210,35,35)),('green',(35,210,35)),('blue',(35,35,210))]:
        (destination/cls).mkdir()
        for i in range(12):
            a=np.clip(np.array(color)+rng.normal(0,20,(32,32,3)),0,255).astype('uint8')
            name=f'{cls}/{i:02}.png'; Image.fromarray(a).save(destination/name); metadata[name]='Contributor-A'
    if attack in {'label_flip','combined'}:
        for i in range(3):
            src=f'red/{i:02}.png'; dst=f'blue/flipped-{i}.png'
            (destination/src).rename(destination/dst); metadata.pop(src); metadata[dst]='Contributor-B'; truth.append({'asset_id':dst,'attack':'label_anomaly'})
    if attack in {'duplicate_flood','combined'}:
        for i in range(6):
            dst=f'green/duplicate-{i}.png'; shutil.copyfile(destination/'green/00.png',destination/dst)
            metadata[dst]='Contributor-B'; truth.append({'asset_id':dst,'attack':'exact_duplicate'})
    if attack in {'ood','combined'}:
        for i in range(4):
            dst=f'red/ood-{i}.png'; Image.fromarray(rng.integers(120,255,(32,32,3),dtype='uint8')).save(destination/dst)
            metadata[dst]='Contributor-B'; truth.append({'asset_id':dst,'attack':'ood'})
    if attack in {'trigger','combined'}:
        for i in range(4):
            dst=f'blue/trigger-{i}.png'
            with Image.open(destination/f'green/{i:02}.png') as image:
                a=np.array(image); a[-5:,-5:]=255; Image.fromarray(a).save(destination/dst)
            metadata[dst]='Contributor-B'; truth.append({'asset_id':dst,'attack':'trigger'})
    (destination/'contributors.json').write_text(json.dumps(metadata,indent=2))
    ground_truth={'seed':seed,'scenario':attack,'attacks':truth,'synthetic':True}
    (destination/'ground_truth.json').write_text(json.dumps(ground_truth,indent=2))
    return ground_truth
