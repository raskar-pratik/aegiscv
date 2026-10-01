"""Complementary black-box patch response; no gradient or suspected target required."""
import numpy as np
from core.schemas import Finding


def probe_patches(adapter,x,patch_size=None):
    if patch_size is None:
        sizes=sorted({max(1,min(x.shape[-2:])//8),max(1,min(x.shape[-2:])//6)})
        candidates=[probe_patches(adapter,x,size) for size in sizes]
        chosen=max(candidates,key=lambda f:f['risk_score'])
        chosen['evidence']['patch_sizes']=sizes
        chosen['evidence']['tested_responses']=[r for c in candidates for r in c['evidence'].get('tested_responses',[])]
        return chosen
    try:
        if adapter.runtime is None: raise ValueError('Model execution unavailable')
        logits=adapter.predict(x)
        if logits.ndim!=2: raise ValueError('Patch probe requires classification logits')
        baseline=logits.argmax(1); size=patch_size
        results=[]
        for corner in ['top_left','top_right','bottom_left','bottom_right']:
            for value in [0.,1.]:
                changed=x.copy(); ys=slice(0,size) if corner.startswith('top') else slice(-size,None)
                xs=slice(0,size) if corner.endswith('left') else slice(-size,None)
                changed[:,:,ys,xs]=value
                predictions=adapter.predict(changed).argmax(1)
                for target in range(logits.shape[1]):
                    eligible=baseline!=target; n=int(eligible.sum())
                    if not n: continue
                    success=float(np.mean(predictions[eligible]==target))
                    results.append({'corner':corner,'value':value,'target':target,'success':success,'eligible_samples':n,'patch_size':size,'area_fraction':size*size/(x.shape[-2]*x.shape[-1])})
        best=max(results,key=lambda r:r['success']) if results else None
        suspicious=best is not None and best['success']>=.9 and best['eligible_samples']>=6
        return Finding('patch_probe','MODEL_INTEGRITY','BACKDOOR',adapter.identity,80 if suspicious else 0,.65,'Small patch drives non-target inputs to a common target' if suspicious else 'No qualifying concentrated response to tested patches',{'best_response':best,'tested_responses':results,'target':best['target'] if best else None},asset_type='MODEL',limitations=['Limited corner/color battery; legitimate patch sensitivity may look similar.','Prediction-based source selection is not clean ground truth.']).to_dict()
    except Exception as exc:
        return Finding('patch_probe','MODEL_INTEGRITY','BACKDOOR',adapter.identity,0,0,str(exc),{},status='UNAVAILABLE',asset_type='MODEL').to_dict()
