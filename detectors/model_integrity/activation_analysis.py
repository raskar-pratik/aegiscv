"""Deterministic PCA/two-means representation clustering; no sklearn dependency."""
import numpy as np
from core.schemas import Finding


def cluster_representations(assets,features,min_samples=12,min_fraction=.05,max_fraction=.3,separation_threshold=4.):
    results=[]; examined=0
    for label in sorted({a['labels'][0] for a in assets if len(a['labels'])==1}):
        ids=[i for i,a in enumerate(assets) if a['labels']==[label]]
        if len(ids)<min_samples: continue
        examined+=1; x=np.asarray(features[ids],dtype=np.float64); x-=x.mean(0)
        _,_,vh=np.linalg.svd(x,full_matrices=False); z=x@vh[:min(5,len(vh))].T
        first=int(np.argmax(np.sum(z*z,axis=1))); second=int(np.argmax(np.sum((z-z[first])**2,axis=1)))
        centers=z[[first,second]].copy(); assignment=np.zeros(len(z),dtype=int)
        for _ in range(50):
            new=np.argmin(((z[:,None]-centers[None])**2).sum(2),axis=1)
            if len(np.unique(new))<2: break
            updated=np.array([z[new==i].mean(0) for i in range(2)])
            if np.array_equal(new,assignment): centers=updated; assignment=new; break
            centers=updated; assignment=new
        counts=np.bincount(assignment,minlength=2); minority=int(counts.argmin()); fraction=float(counts[minority]/len(z))
        residual=np.linalg.norm(z-centers[assignment],axis=1)
        separation=float(np.linalg.norm(centers[0]-centers[1])/max(float(np.sqrt(np.mean(residual**2))),1e-8))
        if min_fraction<=fraction<=max_fraction and separation>=separation_threshold:
            members=[assets[ids[i]]['asset_id'] for i in np.flatnonzero(assignment==minority)]
            results.append(Finding('activation_clustering','MODEL_INTEGRITY','REPRESENTATION_ANOMALY',members[0],70,.55,'Separated minority representation cluster within declared class',{'class':label,'members':members,'cluster_sizes':counts.tolist(),'minority_fraction':fraction,'separation_ratio':separation,'threshold':separation_threshold,'method':'PCA up to five dimensions; deterministic farthest-point two-means'},limitations=['Minority clusters can be legitimate subclasses; clustering alone cannot identify clean versus poisoned samples.']).to_dict())
    return results or [Finding('activation_clustering','MODEL_INTEGRITY','REPRESENTATION_ANOMALY','dataset',0,.45 if examined else 0,'No qualifying minority activation clusters' if examined else 'No sufficiently populated class for activation clustering',{'examined_classes':examined},status='SUCCESS' if examined else 'UNAVAILABLE').to_dict()]


def analyze_activations(adapter,x,assets):
    try: return cluster_representations(assets,adapter.get_features(x))
    except Exception as exc:
        return [Finding('activation_clustering','MODEL_INTEGRITY','REPRESENTATION_ANOMALY',adapter.identity,0,0,str(exc),{},status='UNAVAILABLE',asset_type='MODEL').to_dict()]
