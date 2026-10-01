"""Bounded research trigger inversion for compatible local classification models."""
import numpy as np
from core.schemas import Finding


def reconstruct(adapter, probes, steps=120, lambda_l1=.05, seed=26228,
                learning_rate=.15, success_threshold=.9, restarts=2, anomaly_threshold=2., labels=None):
    if not adapter.supports_gradients():
        return Finding('neural_cleanse','MODEL_INTEGRITY','BACKDOOR',adapter.identity,0,0,'White-box backdoor reconstruction unavailable because model gradients are inaccessible',{},status='UNAVAILABLE',asset_type='MODEL').to_dict()
    import torch
    x=torch.tensor(probes,dtype=torch.float32)
    outcomes=[]
    try:
        if steps<1 or restarts not in {1,2} or learning_rate<=0 or lambda_l1<=0: raise ValueError('Invalid inversion settings')
        if x.ndim!=4 or not torch.isfinite(x).all() or x.min()<0 or x.max()>1:
            raise ValueError('Reconstruction requires finite NCHW RGB inputs in [0,1]; wrap normalization inside model')
        with torch.no_grad(): output=adapter.runtime(x)
        if output.ndim!=2 or not 2<=output.shape[1]<=20: raise ValueError('Research inversion supports 2..20 classification classes')
        source=output.argmax(1) if labels is None else torch.as_tensor(labels,dtype=torch.long)
        if source.shape!=(len(x),): raise ValueError('Source labels must align with probes')
        rng=np.random.default_rng(seed)
        for target in range(output.shape[1]):
            indices=np.flatnonzero((source!=target).numpy()); rng.shuffle(indices)
            if len(indices)<2:
                outcomes.append({'target':target,'status':'UNAVAILABLE','reason':'Fewer than two non-target clean sources'}); continue
            cut=max(1,int(len(indices)*.7)); train=x[indices[:cut]]; validation=x[indices[cut:]]
            targets=torch.full((len(train),),target,dtype=torch.long)
            best=None; attempts=[]
            for restart in range(restarts):
                # Dense bright initialization crosses dead threshold branches; sparse neutral explores ordinary paths.
                mask=torch.full((1,1,*x.shape[-2:]),3. if restart else -2.,requires_grad=True)
                pattern=torch.full((1,*x.shape[1:]),4. if restart else 0.,requires_grad=True)
                optimizer=torch.optim.Adam([mask,pattern],lr=learning_rate); cost=lambda_l1
                for step in range(steps):
                    m,p=mask.sigmoid(),pattern.sigmoid()
                    logits=adapter.runtime((1-m)*train+m*p)
                    success=float((logits.argmax(1)==target).float().mean())
                    norm=float(m.detach().sum())
                    if success>=success_threshold and (best is None or norm<best['mask_norm']):
                        best={'mask_norm':norm,'m':m.detach().clone(),'p':p.detach().clone(),'train_success':success,'restart':restart,'step':step}
                    loss=torch.nn.functional.cross_entropy(logits,targets)+cost*m.mean()
                    gradients=torch.autograd.grad(loss,[mask,pattern])
                    optimizer.zero_grad(); mask.grad,pattern.grad=gradients; optimizer.step()
                    if (step+1)%10==0:
                        cost=min(100.,cost*1.8) if success>=success_threshold else max(lambda_l1/10,cost/1.5)
                attempts.append({'initialization':'dense_bright' if restart else 'sparse_neutral','final_cost':cost})
            if best is None:
                outcomes.append({'target':target,'status':'FAILED','reason':'No feasible trigger reached training success threshold','attempts':attempts}); continue
            m,p=best.pop('m'),best.pop('p')
            with torch.no_grad(): success=float((adapter.runtime((1-m)*validation+m*p).argmax(1)==target).float().mean())
            outcomes.append(dict(best,target=target,status='SUCCESS' if success>=success_threshold else 'FAILED',success=success,validation_samples=len(validation),training_samples=len(train),mask=m[0,0].tolist(),pattern=p[0].permute(1,2,0).tolist(),attempts=attempts))
        valid=[o for o in outcomes if o['status']=='SUCCESS']; median=mad=index=None; chosen=None; suspicious=False
        if len(valid)>=3:
            norms=np.array([o['mask_norm'] for o in valid]); median=float(np.median(norms)); mad=float(np.median(np.abs(norms-median)))
            candidate=min(valid,key=lambda o:o['mask_norm']); chosen=candidate['target']
            if mad>1e-6:
                index=float((median-candidate['mask_norm'])/(1.4826*mad))
                suspicious=index>anomaly_threshold
        evidence={'outcomes':outcomes,'anomaly_index':index,'target':chosen,'median':median,'mad':mad,'steps':steps,'lambda_l1':lambda_l1,'learning_rate':learning_rate,'restarts':restarts,'success_threshold':success_threshold,'anomaly_threshold':anomaly_threshold,'source_count':len(x),'source_labels':'supplied' if labels is not None else 'model predictions','successful_targets':len(valid),'preprocessing':'Model must consume [0,1] tensors or include normalization internally'}
        # A short/unsuccessful search is explicitly recorded, never counted as a small trigger.
        return Finding('neural_cleanse','MODEL_INTEGRITY','BACKDOOR',adapter.identity,85 if suspicious else 0,.55 if suspicious else .25,'Backdoor-like trigger reconstruction anomaly' if suspicious else 'No qualifying reconstruction anomaly; inspect feasibility and search limitations',evidence,asset_type='MODEL',limitations=['Finite optimization can miss thresholded, distributed or unseen triggers.','MAD needs successful comparison targets and is unstable for few classes.','Held-out recovery success is measured; it does not establish real-world backdoor detection accuracy.']).to_dict()
    except Exception as exc:
        return Finding('neural_cleanse','MODEL_INTEGRITY','BACKDOOR',adapter.identity,0,0,str(exc),{},status='FAILED',asset_type='MODEL').to_dict()
