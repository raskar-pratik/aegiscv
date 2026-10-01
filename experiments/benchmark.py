"""Deterministic generated ten-class benchmark; no downloaded or pretrained data."""
import colorsys
import json
import shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from adapters.datasets.ingestion import ingest
from provenance.hashing import digest

SPLITS={'train':20,'reference':20,'calibration':20,'evaluation':30}


def generate(root,seed=26228,counts=None):
    root=Path(root); partitions={}
    for index,(split,count) in enumerate((counts or SPLITS).items()):
        rng=np.random.default_rng(np.random.SeedSequence([seed,index])); sources={}
        for label in range(10):
            color=np.array(colorsys.hsv_to_rgb(label/10,.72,.72))*255
            for i in range(count):
                y,x=np.mgrid[:32,:32]
                texture=14*np.sin((x*(label%3+1)+y*(label//3+1))/5+rng.uniform(0,6.28))
                pixels=np.clip(color+texture[...,None]+rng.normal(0,9,(32,32,3)),0,255).astype('uint8')
                relative=f'class-{label:02d}/{split}-{i:04d}.png'; path=root/split/relative
                path.parent.mkdir(parents=True,exist_ok=True); Image.fromarray(pixels).save(path)
                sources[relative]=f'contributor-{i%5}'
        (root/split/'contributors.json').write_text(json.dumps(sources,sort_keys=True))
        manifest=ingest(root/split)
        partitions[split]={'count':len(manifest['assets']),'class_distribution':{f'class-{i:02d}':count for i in range(10)},
                           'assets':manifest['assets'],'manifest_hash':digest(manifest)}
    validate_splits(partitions)
    return {'name':'AegisCV Procedural-10 v1','kind':'generated RGB color/texture images; not natural imagery',
            'seed':seed,'image_shape':[32,32,3],'partitions':partitions,
            'training_use':'Reserved, not used: image encoder is fixed; model controls are analytic.'}


def validate_splits(partitions):
    hashes=set(); identities=set()
    for split,part in partitions.items():
        current={a['sha256'] for a in part['assets']}
        ids={a['asset_id'] for a in part['assets']}
        if hashes&current or identities&ids: raise ValueError('Split leakage: duplicate content or identity')
        hashes.update(current); identities.update(ids)


def attack(source,destination,kind='clean',rate=0.,seed=26228):
    """Rates are selected source-image fractions. Duplicate truth includes original group members."""
    source=Path(source); destination=Path(destination)
    shutil.copytree(source,destination)
    assets=ingest(destination)['assets']; rng=np.random.default_rng(seed)
    selected=[assets[int(i)] for i in rng.permutation(len(assets))[:round(rate*len(assets))]]
    truth={k:[] for k in ['exact_duplicate','near_duplicate','label_anomaly','ood','spectral_signature','trigger_pattern']}
    sources=json.loads((destination/'contributors.json').read_text()); changes=[]
    for i,a in enumerate(selected):
        old=a['asset_id']; path=destination/old; new=old
        if kind in {'label_flip','trigger','contributor'}:
            target=(int(a['labels'][0].split('-')[1])+1)%10 if kind=='label_flip' else 0
            if target==int(a['labels'][0].split('-')[1]): target=1
            # Contributor poisoning uses flipped labels; trigger is always associated with class 0.
            if kind=='trigger': target=0
            new=f'class-{target:02d}/poison-{i:04d}.png'; output=destination/new; output.parent.mkdir(exist_ok=True)
            with Image.open(path) as image: pixels=np.array(image.convert('RGB'))
            if kind=='trigger': pixels[-5:,-5:]=255; truth['trigger_pattern'].append(new)
            Image.fromarray(pixels).save(output); path.unlink(); sources.pop(old)
            if a['labels']!=[f'class-{target:02d}']: truth['label_anomaly'].append(new)
            truth['spectral_signature'].append(new)
        elif kind in {'exact_duplicate','near_duplicate'}:
            new=str(Path(old).parent/f'injected-{i:04d}.png').replace('\\','/')
            if kind=='exact_duplicate': shutil.copyfile(path,destination/new)
            else:
                with Image.open(path) as image: pixels=np.asarray(image.convert('RGB')).copy()
                pixels[16,16,0]^=1; Image.fromarray(pixels).save(destination/new)
            truth[kind].extend([old,new])
        elif kind=='ood':
            pixels=rng.integers(0,256,(32,32,3),dtype='uint8'); Image.fromarray(pixels).save(path); truth['ood'].append(old)
        elif kind=='benign_shift':
            with Image.open(path) as image:
                image=image.filter(ImageFilter.GaussianBlur(.6)); pixels=np.clip(np.asarray(image)*.65,0,255).astype('uint8')
            Image.fromarray(pixels).save(path)
        sources[new]='malicious-contributor' if kind in {'contributor','trigger','ood','label_flip'} else a['contributor']
        changes.append({'original':old,'result':new,'original_sha256':a['sha256']})
    (destination/'contributors.json').write_text(json.dumps(sources,sort_keys=True))
    result={'kind':kind,'rate':rate,'rate_denominator':'original source images','selected_count':len(selected),
            'source_count':len(assets),'seed':seed,'truth':{k:sorted(set(v)) for k,v in truth.items()},'changes':changes}
    result['attack_hash']=digest(result)
    return result
