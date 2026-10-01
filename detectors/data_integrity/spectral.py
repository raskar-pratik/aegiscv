"""Class-conditional spectral ranking; an outlier is not proof of poisoning."""
import numpy as np
from core.schemas import Finding


def spectral_signatures(assets, features, min_samples=10, directions=1, threshold=8., percentile_threshold=95., min_energy=.001):
    if len(assets)!=len(features) or not np.isfinite(features).all(): raise ValueError('Invalid spectral feature matrix')
    results=[]; classes=sorted({a['labels'][0] for a in assets if len(a['labels'])==1}); examined=[]; skipped=[]
    for label in classes:
        indices=[i for i,a in enumerate(assets) if a['labels']==[label]]
        if len(indices)<min_samples:
            skipped.append({'class':label,'samples':len(indices),'required':min_samples}); continue
        x=np.asarray(features[indices],dtype=np.float64); x-=x.mean(0)
        _,singular,vh=np.linalg.svd(x,full_matrices=False)
        scores=np.sum((x@vh[:min(directions,len(vh))].T)**2,axis=1)
        median=float(np.median(scores)); mad=float(np.median(np.abs(scores-median)))
        scale=max(1.4826*mad,1e-12)
        robust=(scores-median)/scale
        examined.append({'class':label,'samples':len(indices),'median':median,'mad':mad,'dominant_singular_values':singular[:directions].tolist()})
        for rank,j in enumerate(np.argsort(-scores,kind='stable'),1):
            percentile=float(100*np.count_nonzero(scores<=scores[j])/len(scores))
            if robust[j]<threshold or percentile<percentile_threshold or scores[j]<min_energy: continue
            asset=assets[indices[j]]
            evidence={'class':label,'target_label':label,'spectral_anomaly_score':float(scores[j]),'robust_z':float(robust[j]),'percentile':percentile,'rank':rank,'class_samples':len(indices),'median':median,'mad':mad,'directions':directions,'threshold':threshold,'minimum_projection_energy':min_energy,'contributor':asset['contributor']}
            results.append(Finding('spectral_signature','DATA_INTEGRITY','SUSPECTED_POISONING',asset['asset_id'],min(95,50+float(robust[j])*2),.55,'Class-relative spectral outlier; investigate source and label evidence',evidence,limitations=['Small classes, multimodal legitimate classes and contaminated majorities can invalidate this heuristic.']).to_dict())
    if not results:
        results.append(Finding('spectral_signature','DATA_INTEGRITY','SUSPECTED_POISONING','dataset',0,.5 if examined else 0,'No qualifying spectral outliers' if examined else 'No sufficiently populated singly labeled class',{'examined':examined,'skipped':skipped},status='SUCCESS' if examined else 'UNAVAILABLE').to_dict())
    elif skipped:
        results.append(Finding('spectral_signature','DATA_INTEGRITY','SUSPECTED_POISONING','dataset',0,0,'Some classes were too small for spectral analysis',{'skipped':skipped},status='UNAVAILABLE').to_dict())
    return results
