"""Calibration-only pair diagnosis and predeclared threshold search."""
import io,json,tempfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageEnhance,ImageOps
from experiments.benchmark import generate
from detectors.data_integrity.features import VisualEncoder,dhash
from detectors.data_integrity.near_confirmation import representation,compare,PROFILE
from provenance.hashing import digest

TRANSFORMS=['resize','jpeg','brightness','crop_pad','noise','reencode']
def transform(source,dest,kind,seed):
    rng=np.random.default_rng(seed)
    with Image.open(source) as im:
        im=im.convert('RGB')
        if kind=='resize': im=im.resize((30,30)).resize((32,32))
        if kind=='jpeg':
            stream=io.BytesIO(); im.save(stream,format='JPEG',quality=90); stream.seek(0); im=Image.open(stream).convert('RGB')
        if kind=='brightness': im=ImageEnhance.Brightness(im).enhance(1.03)
        if kind=='crop_pad': im=ImageOps.expand(im.crop((1,1,31,31)),border=1,fill=tuple(np.asarray(im).mean((0,1)).astype(int)))
        if kind=='noise': im=Image.fromarray(np.clip(np.asarray(im,dtype=float)+rng.normal(0,1,(32,32,3)),0,255).astype('uint8'))
        im.save(dest)

def run(output):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp); benchmark=generate(root/'data'); assets=benchmark['partitions']['calibration']['assets']
        paths=[root/'data/calibration'/a['asset_id'] for a in assets]; reps=[representation(p) for p in paths]; hashes=[dhash(p) for p in paths]; embeddings=VisualEncoder().encode(paths)
        rows=[]
        for i in range(len(paths)):
            for j in range(i+1,len(paths)):
                rows.append(dict(compare(reps[i],reps[j]),hamming=(hashes[i]^hashes[j]).bit_count(),cosine_distance=float(1-embeddings[i]@embeddings[j]),positive=False,i=i,j=j,transform='independent'))
        for i,path in enumerate(paths):
            for kind in TRANSFORMS:
                dest=root/'transformed.png'; transform(path,dest,kind,26228+i)
                rows.append(dict(compare(reps[i],representation(dest)),hamming=(hashes[i]^dhash(dest)).bit_count(),cosine_distance=float(1-embeddings[i]@VisualEncoder().encode_image(dest)),positive=True,i=i,j=i,transform=kind))
        candidates=[]; neg=[r for r in rows if not r['positive']]; pos=[r for r in rows if r['positive']]
        for h in [4,8,16,32]:
            for rmse in [.01,.02,.03,.05,.08]:
                for corr in [.2,.4,.6,.8,.95]:
                    choose=lambda r:r['hamming']<=h and r['pixel_rmse']<=rmse and r['residual_correlation']>=corr
                    bad=[r for r in neg if choose(r)]; affected={v for r in bad for v in [r['i'],r['j']]}
                    candidates.append({'thresholds':{'hamming':h,'rmse':rmse,'correlation':corr},'pair_fpr':len(bad)/len(neg),'image_fpr':len(affected)/len(paths),'recall':sum(choose(r) for r in pos)/len(pos)})
        eligible=[c for c in candidates if c['pair_fpr']<=.02 and c['image_fpr']<=.02]
        winner=max(eligible,key=lambda c:(c['recall'],-c['image_fpr'],-c['thresholds']['hamming'])) if eligible else min(candidates,key=lambda c:(c['image_fpr'],-c['recall']))
        value={**winner,'qualified':winner['recall']>=.5 and winner['image_fpr']<=.02 and winner['pair_fpr']<=.02,'scope':'Procedural-10 calibration pairs only; not natural-image validation',
               'calibration_manifest_hash':benchmark['partitions']['calibration']['manifest_hash'],'calibration_ids':[a['asset_id'] for a in assets],
               'negative_pairs':len(neg),'positive_pairs':len(pos),'selection':'Max recall subject to pair and image FPR <= .02; no evaluation features used',
               'seed':26228,'transformations':TRANSFORMS}
        value['profile_hash']=digest(value); PROFILE.parent.mkdir(exist_ok=True); PROFILE.write_text(json.dumps(value,indent=2))
        legacy=[r for r in neg if r['hamming']<=4 and r['cosine_distance']<=.08]
        parent=list(range(len(paths)))
        def find(i):
            while parent[i]!=i: i=parent[i]
            return i
        for r in legacy: parent[find(r['j'])]=find(r['i'])
        connected=sum(find(r['i'])==find(r['j']) for r in neg)
        distribution={}
        for feature in ['hamming','cosine_distance','pixel_rmse','histogram_intersection','ssim_approx','residual_correlation']:
            distribution[feature]={kind:np.quantile([r[feature] for r in group],[0,.01,.5,.99,1]).tolist() for kind,group in [('negative',neg),('positive',pos)]}
        diagnosis={'image_shape':[32,32,3],'negative_pairs':len(neg),'legacy_false_edges':len(legacy),'legacy_affected_images':len({v for r in legacy for v in [r['i'],r['j']]}),
            'transitive_connected_pairs':connected,'unsupported_transitive_pairs':connected-len(legacy),'feature_quantiles_0_1_50_99_100':distribution,
            'root_causes':['8x8 dHash loses image-specific high-frequency noise; same-class procedural textures collide.','198-dimensional normalized color features primarily gate class/color, not copy identity.','Connected components imply unverified transitive pair relationships. Image membership and pair truth must be evaluated separately.'],
            'selected':value,'candidate_grid':candidates}
        points=[]
        for feature,threshold,higher in [('hamming',4,False),('hamming',8,False),('cosine_distance',.08,False),('pixel_rmse',.05,False),('histogram_intersection',.95,True),('ssim_approx',.95,True),('residual_correlation',.2,True)]:
            selected=lambda r:r[feature]>=threshold if higher else r[feature]<=threshold
            bad=[r for r in neg if selected(r)]
            points.append({'feature':feature,'threshold':threshold,'comparison':'>=' if higher else '<=','recall':sum(selected(r) for r in pos)/len(pos),'pair_fpr':len(bad)/len(neg),'image_fpr':len({i for r in bad for i in [r['i'],r['j']]})/len(paths)})
        diagnosis['individual_feature_operating_points']=points
        (output/'pair_diagnosis.json').write_text(json.dumps(diagnosis,indent=2)); (output/'calibration_pairs.json').write_text(json.dumps(rows))
        print(json.dumps({k:v for k,v in diagnosis.items() if k not in {'candidate_grid','feature_quantiles_0_1_50_99_100'}},indent=2))
    return value

if __name__=='__main__': run(Path('experiments/results/stabilization'))
