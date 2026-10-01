"""Explicit confusion counts and tie-aware ranking metrics without optional dependencies."""
import numpy as np
from experiments.hardening import metrics


def evaluate(detector,scenario,universe,actual,predicted,runtime=0.,scores=None,unit='image'):
    if not set(actual)<=set(universe): raise ValueError('Ground truth outside evaluation universe')
    row=metrics(detector,scenario,universe,actual,predicted,runtime,unit)
    row.update(roc_auc=None,pr_auc=None,auc_reason='No continuous per-unit score supplied')
    if scores is not None:
        if set(scores)!=set(universe): raise ValueError('Scores must cover every evaluation unit')
        positive=np.asarray([scores[x] for x in universe if x in set(actual)],dtype=float)
        negative=np.asarray([scores[x] for x in universe if x not in set(actual)],dtype=float)
        if not all(np.isfinite(v) for v in scores.values()): raise ValueError('Nonfinite scores')
        if len(positive) and len(negative):
            row['roc_auc']=float(((positive[:,None]>negative).sum()+.5*(positive[:,None]==negative).sum())/(len(positive)*len(negative)))
            # Step-integrated precision-recall (average precision), grouping tied scores.
            previous=0.; ap=0.
            for threshold in sorted(set(scores.values()),reverse=True):
                tp=int((positive>=threshold).sum()); fp=int((negative>=threshold).sum()); recall=tp/len(positive)
                ap+=(recall-previous)*tp/(tp+fp); previous=recall
            row.update(pr_auc=ap,auc_reason='PR AUC is average precision with tied scores grouped')
        else: row['auc_reason']='Requires both positive and negative evaluation units'
    return row
