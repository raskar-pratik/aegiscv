"""Reference/current distribution comparison, without attributing intent."""
import numpy as np
from collections import Counter
from core.schemas import Finding


def compare(reference, current, reference_labels=None, current_labels=None,
            reference_confidence=None, current_confidence=None, thresholds=None, max_samples=512):
    if reference is None or len(reference)<2 or len(current)<2:
        return Finding('embedding_shift','DISTRIBUTION','DISTRIBUTION_SHIFT','dataset',0,0,'Requires two or more reference and current images',{},status='UNAVAILABLE',asset_type='DATASET').to_dict()
    limits={'centroid_l2':.1,'covariance_frobenius':.02,'mmd_squared':.05,'class_frequency_tv':.1,'confidence_mean_delta':.1}
    if thresholds: limits.update(thresholds)
    if any(v<=0 for v in limits.values()): raise ValueError('Shift thresholds must be positive')
    a=np.asarray(reference,dtype=np.float64); b=np.asarray(current,dtype=np.float64)
    if a.ndim!=2 or b.ndim!=2 or a.shape[1]!=b.shape[1] or not np.isfinite(a).all() or not np.isfinite(b).all():
        return Finding('embedding_shift','DISTRIBUTION','DISTRIBUTION_SHIFT','dataset',0,0,'Incompatible or nonfinite embedding matrices',{},status='FAILED').to_dict()
    metrics={'centroid_l2':float(np.linalg.norm(a.mean(0)-b.mean(0))),
             'covariance_frobenius':float(np.linalg.norm(np.atleast_2d(np.cov(a,rowvar=False))-np.atleast_2d(np.cov(b,rowvar=False)),ord='fro'))}
    # Deterministically bound quadratic kernel memory without changing full-data moments.
    ar=a[np.linspace(0,len(a)-1,min(max_samples,len(a)),dtype=int)]
    br=b[np.linspace(0,len(b)-1,min(max_samples,len(b)),dtype=int)]
    def squared(x,y): return np.maximum((x*x).sum(1)[:,None]+(y*y).sum(1)[None]-2*x@y.T,0)
    reference_dist=squared(ar,ar); nonzero=reference_dist[reference_dist>1e-12]
    bandwidth=float(np.median(nonzero)) if len(nonzero) else 1.
    kernel=lambda x,y:np.exp(-squared(x,y)/(2*bandwidth))
    metrics['mmd_squared']=max(0.,float(kernel(ar,ar).mean()+kernel(br,br).mean()-2*kernel(ar,br).mean()))
    unavailable=[]; details={}
    if reference_labels is not None and current_labels is not None:
        counts_a=Counter(l for labs in reference_labels for l in labs); counts_b=Counter(l for labs in current_labels for l in labs)
        if sum(counts_a.values()) and sum(counts_b.values()):
            names=set(counts_a)|set(counts_b)
            metrics['class_frequency_tv']=.5*sum(abs(counts_a[c]/sum(counts_a.values())-counts_b[c]/sum(counts_b.values())) for c in names)
            details['class_counts']={'reference':dict(counts_a),'current':dict(counts_b)}
        else: unavailable.append('class_frequency_tv: no labeled samples')
    else: unavailable.append('class_frequency_tv: labels unavailable')
    if reference_confidence is not None and current_confidence is not None:
        ca=np.asarray(reference_confidence); cb=np.asarray(current_confidence)
        if len(ca) and len(cb) and np.isfinite(ca).all() and np.isfinite(cb).all():
            metrics['confidence_mean_delta']=float(abs(ca.mean()-cb.mean()))
            details['confidence_means']={'reference':float(ca.mean()),'current':float(cb.mean())}
        else: unavailable.append('confidence_mean_delta: invalid confidence values')
    else: unavailable.append('confidence_mean_delta: compatible model predictions unavailable')
    triggered=[name for name,value in metrics.items() if value>limits[name]]
    normalized={name:value/limits[name] for name,value in metrics.items()}
    score=min(100,50*max(normalized.values())) if triggered else 0
    evidence={'metrics':{name:{'value':value,'threshold':limits[name],'threshold_ratio':normalized[name],'triggered':name in triggered} for name,value in metrics.items()},'triggered_metrics':triggered,'unavailable_metrics':unavailable,'reference_count':len(a),'current_count':len(b),'mmd_kernel':'RBF, biased nonnegative empirical MMD squared','mmd_bandwidth_squared':bandwidth,'kernel_sample_counts':[len(ar),len(br)],'normalization':'Each value divided by its own configured domain threshold. Risk uses the maximum ratio, not a sum; zero if none trigger.',**details}
    return Finding('embedding_shift','DISTRIBUTION','DISTRIBUTION_SHIFT','dataset',round(score,2),round(.65*len(metrics)/len(limits),3),'Shift thresholds triggered: '+', '.join(triggered) if triggered else 'No configured distribution-shift thresholds triggered',evidence,asset_type='DATASET',limitations=['Threshold ratios are heuristic, not p-values; calibrate on held-out domain data.','Class mix, camera changes and malicious injection can produce the same metrics.']).to_dict()
