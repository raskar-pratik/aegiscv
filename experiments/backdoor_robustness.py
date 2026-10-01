"""Fixed-parameter inversion on seeded, locally trained patch-poisoned controls."""
import time
from pathlib import Path
import numpy as np
from PIL import Image
from attack_simulator.backdoor_validation import samples
from adapters.models.runtime import ModelAdapter
from detectors.model_integrity.neural_cleanse import reconstruct
from detectors.model_integrity.patch_probe import probe_patches
from detectors.model_integrity.decision import assess
from experiments.hardening import backdoor_experiment
from experiments.validation_metrics import evaluate
from provenance.hashing import digest


def patch(x,size,corner):
    x=x.copy(); ys=slice(0,size) if corner.startswith('top') else slice(-size,None)
    xs=slice(0,size) if corner.endswith('left') else slice(-size,None)
    x[:,:,ys,xs]=1.; return x


def factory():
    import torch
    class SmallModel(torch.nn.Module):
        def __init__(self):
            super().__init__(); self.head=torch.nn.Sequential(torch.nn.Linear(15,48),torch.nn.ReLU(),torch.nn.Linear(48,6))
        def get_features(self,x):
            return torch.cat([x.mean((2,3)),x[:,:,:4,:4].mean((2,3)),x[:,:,:4,-4:].mean((2,3)),
                              x[:,:,-4:,:4].mean((2,3)),x[:,:,-4:,-4:].mean((2,3))],1)
        def forward(self,x): return self.head(self.get_features(x))
    return SmallModel()


def train(directory,seed,rate,target,size,corner):
    import torch
    torch.manual_seed(seed); model=factory(); x,y=samples(seed,per_class=100)
    eligible=np.flatnonzero(y!=target); selected=np.random.default_rng(seed).permutation(eligible)[:round(rate*len(y))]
    x[selected]=patch(x[selected],size,corner); y[selected]=target
    optimizer=torch.optim.Adam(model.parameters(),lr=.025)
    features=model.get_features(torch.tensor(x)).detach(); labels=torch.tensor(y)
    for _ in range(350):
        optimizer.zero_grad(); loss=torch.nn.functional.cross_entropy(model.head(features),labels); loss.backward(); optimizer.step()
    path=directory/'model.pt'; directory.mkdir(parents=True,exist_ok=True); torch.save(model.state_dict(),path)
    return ModelAdapter(str(path),'pytorch',factory=factory),{'training_samples':len(y),'poisoned_samples':len(selected),
             'poison_rate':rate,'training_data_hash':digest({'x':x.tolist(),'y':y.tolist()}),'epochs':350,'optimizer':'Adam lr=0.025'}


def run(output):
    import torch
    output=Path(output); output.mkdir(parents=True,exist_ok=True); torch.set_num_threads(1)
    baseline=backdoor_experiment(output/'preserved_baseline')
    cases=[('calibration',11,.10,2,4,'bottom_right'),('calibration',11,0.,2,4,'bottom_right')]
    cases += [('evaluation',7,r,0,4,'top_left') for r in [.01,.05,.10,.20]]
    cases += [('evaluation',19,.10,3,3,'top_right'),('evaluation',41,.10,5,2,'bottom_left')]
    cases += [('evaluation',seed,0.,target,size,corner) for seed,target,size,corner in [(7,0,4,'top_left'),(19,3,3,'top_right'),(41,5,2,'bottom_left')]]
    settings={'steps':140,'seed':26228,'success_threshold':.9,'anomaly_threshold':2.,'restarts':2}
    records=[]
    for split,seed,rate,target,size,corner in cases:
        name=f'{split}-{seed}-{rate:g}-{corner}-{size}-{target}'; start=time.perf_counter()
        adapter,training=train(output/name,seed,rate,target,size,corner)
        # Different seed and distribution draw from model training; no poisoned inversion probes.
        x,y=samples(seed+100000,per_class=6); clean=adapter.predict(x).argmax(1)
        eligible=y!=target; triggered=adapter.predict(patch(x[eligible],size,corner)).argmax(1)
        result=reconstruct(adapter,x,labels=y,**settings); e=result['evidence']
        patch_result=probe_patches(adapter,x); decision=assess(result,patch_result)
        for outcome in e.get('outcomes',[]):
            if 'mask' in outcome:
                Image.fromarray(np.uint8(np.clip(outcome['mask'],0,1)*255)).save(output/name/f"target-{outcome['target']}-mask.png")
                Image.fromarray(np.uint8(np.clip(outcome['pattern'],0,1)*255)).save(output/name/f"target-{outcome['target']}-pattern.png")
        recovered=next((o for o in e.get('outcomes',[]) if o['target']==e.get('target')), {})
        row={'name':name,'split':split,'seed':seed,'target':target,'trigger_size':size,'trigger_location':corner,
             'model_hash':adapter.identity,'training':training,'clean_correct':int((clean==y).sum()),'clean_samples':len(y),
             'clean_accuracy':float((clean==y).mean()),'attack_successes':int((triggered==target).sum()),'attack_samples':len(triggered),
             'attack_success_rate':float((triggered==target).mean()),'recovered_target':e.get('target'),
             'recovered_trigger_success':recovered.get('success'),'mask_norm':recovered.get('mask_norm'),
             'median':e.get('median'),'mad':e.get('mad'),'anomaly_index':e.get('anomaly_index'),
             'detected':result['risk_score']>20,'finding':result,'patch_probe':patch_result,'backdoor_assessment':decision,'runtime_seconds':time.perf_counter()-start}
        records.append(row); print('Backdoor case completed: '+name,flush=True)
    held=[r for r in records if r['split']=='evaluation']
    return {'preserved_baseline':baseline,'settings':settings,'settings_status':'UNCALIBRATED_HEURISTIC; fixed before all cases; calibration cases are diagnostic only',
            'records':records,'metrics':evaluate('neural_cleanse','held-out trained models',[r['name'] for r in held],
            [r['name'] for r in held if r['training']['poison_rate']>0],[r['name'] for r in held if r['detected']],
            sum(r['runtime_seconds'] for r in held),scores={r['name']:r['anomaly_index'] for r in held} if all(r['anomaly_index'] is not None for r in held) else None,unit='model'),
            'limitations':['Tiny synthetic six-class models, not independently sourced natural-image models.',
            'Positive ground truth is training poisoning; low ASR models may not have acquired the intended backdoor.',
            'Model seeds are independent, but trigger settings are partially confounded with seed.',
            'Calibration cases did not select inversion hyperparameters; those remain heuristic.']}
