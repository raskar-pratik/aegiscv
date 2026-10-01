"""Explicit cross-layer rules retain every supporting finding link."""
from core.schemas import Finding


def correlate_findings(findings, assets):
    rows=[]; sources={a['asset_id']:a['contributor'] for a in assets}
    positive=[f for f in findings if f['status']=='SUCCESS' and f['risk_score']>20]
    def emit(rule,reason,linked,asset='system',extra=None):
        ids=sorted({f['finding_id'] for f in linked})
        evidence={'rule':rule,'finding_ids':ids,**(extra or {})}
        result=Finding('cross_layer_correlation','CROSS_LAYER','CORRELATED_EVIDENCE',asset,max(f['risk_score'] for f in linked),min(f['confidence'] for f in linked),reason,evidence,asset_type='SYSTEM',limitations=['Correlated signals are not statistically independent; scores are not multiplied.']).to_dict()
        rows.append(dict(result,finding_ids=ids,detectors=sorted({f['detector'] for f in linked}),contributor=asset if asset in set(sources.values()) else None))
    for source in sorted(set(sources.values())-{'unknown'}):
        relevant=[f for f in positive if any(sources.get(a)==source for a in [f['asset_id']]+f['evidence'].get('members',[]))]
        spectral=[f for f in relevant if f['detector']=='spectral_signature']; labels=[f for f in relevant if f['detector']=='label_anomaly']
        if spectral and labels: emit('source_spectral_label','Contributor spectral anomalies and label disagreement increase poisoning concern',spectral+labels,source)
        ood=[f for f in relevant if f['detector']=='ood']; shift=[f for f in positive if f['detector'] in {'embedding_shift','acquisition_shift'}]
        affected={f['asset_id'] for f in ood}; source_count=sum(s==source for s in sources.values())
        concentration=len(affected)/source_count if source_count else 0
        if len(affected)>=2 and concentration>=.2 and shift:
            emit('source_ood_shift','Concentrated OOD and distribution shift are consistent with possible distribution contamination; benign drift remains plausible',ood+shift,source,{'ood_fraction':concentration})
        if len({f['detector'] for f in relevant})>1:
            emit('source_multiple_anomalies','Multiple anomaly types share a contributor; association does not establish intent',relevant,source)
    triggers=[f for f in positive if f['detector']=='trigger_pattern']
    reconstruction=[f for f in positive if f['detector']=='neural_cleanse']
    for data in triggers:
        for model in reconstruction:
            label=data['evidence'].get('target_label'); model_label=model['evidence'].get('target_label')
            if label is not None and model_label is not None and str(label)==str(model_label):
                emit('matched_trigger_target','Dataset trigger pattern and model reconstruction point to the same explicitly mapped target class', [data,model],extra={'target_label':label})
    for model_hash in [f for f in findings if f['detector']=='model_hash' and f['status']=='SUCCESS']:
        behavior=[f for f in positive if f['detector']=='behavioral_probe' and f['asset_id']==model_hash['asset_id']]
        if not behavior: continue
        e=model_hash['evidence']
        if model_hash['risk_score']>20: emit('substitution_hash_behavior','Changed model bytes and changed behavior strongly corroborate substitution or modification',[model_hash]+behavior)
        elif e.get('expected') is not None and e.get('expected')==e.get('actual'):
            emit('unchanged_hash_changed_behavior','Identical model bytes but changed behavior indicate runtime, preprocessing or configuration differences',[model_hash]+behavior)
    return rows


def correlate(findings,assets):
    """Backward-compatible entry point."""
    return correlate_findings(findings,assets)
