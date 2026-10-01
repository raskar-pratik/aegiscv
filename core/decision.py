"""Judge-facing decision contract layered over unchanged composite risk."""
from core.quality import quality
from core.schemas import severity


def contract(findings, composite, contributors=None, ledger_verification=None):
    contributors=contributors or []
    ledger_verification=ledger_verification or {}
    candidates=[]
    for finding in findings:
        if finding.get('status')=='SUCCESS' and finding.get('risk_score',0)>0:
            asset_type=finding.get('asset_type','IMAGE')
            if finding.get('detector') in {'model_hash','behavioral_probe','neural_cleanse','patch_probe','activation_clustering'}: asset_type='MODEL'
            elif finding.get('detector') in {'ledger_verification','signature_verification'}: asset_type='LEDGER'
            elif finding.get('category')=='DISTRIBUTION': asset_type='DATASET'
            candidates.append((float(finding['risk_score']),finding.get('asset_id','dataset'),'FINDING',asset_type,finding.get('reason',''),finding))
    for row in contributors:
        if row.get('risk_score',0)>0:
            candidates.append((float(row['risk_score']),row.get('contributor','unknown'),'CONTRIBUTOR','CONTRIBUTOR','Contributor-level evidence aggregation',row))
    highest=max(candidates,key=lambda item:item[0]) if candidates else (0,'dataset','DATASET','DATASET','No positive risk evidence',None)
    max_risk=round(highest[0],2)
    highest_severity=severity(max_risk)
    trigger={'type':'NONE','asset':highest[1],'risk':max_risk,'evidence_families':[],'reason':'No decisive evidence override'}
    disposition=composite.get('recommended_action','REVIEW')

    crypto=[f for f in findings if f.get('status')=='SUCCESS' and f.get('detector') in {'model_hash','signature_verification'} and f.get('risk_score')>=100]
    ledger_bad=ledger_verification.get('status') in {'TAMPERED','SIGNATURE_INVALID','SEQUENCE_ERROR','FAILED'}
    ledger_findings=[f for f in findings if f.get('detector')=='ledger_verification' and f.get('risk_score',0)>=100]
    substitution=[f for f in findings if f.get('status')=='SUCCESS' and f.get('detector')=='model_hash' and f.get('risk_score',0)>=100]
    decisive=max(crypto+ledger_findings+substitution,key=lambda f:f.get('risk_score',0),default=None)
    if decisive is not None or ledger_bad:
        disposition='QUARANTINE'
        trigger={'type':'CRYPTOGRAPHIC_INTEGRITY','asset':decisive.get('asset_id','ledger') if decisive else 'ledger','risk':100,
                 'evidence_families':['cryptographic_integrity'],'reason':'Verified model, signature or ledger integrity failure'}
    else:
        source=max(contributors,key=lambda row:row.get('risk_score',0),default=None)
        families=sorted((source or {}).get('evidence_families',{}))
        if source and source.get('risk_score',0)>=80 and len(families)>=2:
            disposition='QUARANTINE'
            trigger={'type':'CONTRIBUTOR_RISK','asset':source.get('contributor'),'risk':round(source['risk_score'],2),'evidence_families':families,
                     'reason':'Critical contributor evidence spans multiple detector families'}
        else:
            strong=[]; moderate=[]
            backdoor_evidence=[]
            for finding in findings:
                if finding.get('status')!='SUCCESS': continue
                evidence=finding.get('evidence',{}); assessment=evidence.get('backdoor_assessment',{})
                if assessment.get('verdict')=='STRONG_BACKDOOR_LIKE_EVIDENCE': strong.append(finding)
                if finding.get('detector') in {'neural_cleanse','patch_probe'} and finding.get('risk_score',0)>20: backdoor_evidence.append(finding)
                if finding.get('risk_score',0)>=40 and quality(finding).get('status')=='CALIBRATED': moderate.append(finding)
            if strong:
                disposition='REVIEW'; chosen=strong[0]
                trigger={'type':'EXPERIMENTAL_BACKDOOR_EVIDENCE','asset':chosen.get('asset_id'),'risk':chosen.get('risk_score',0),
                         'evidence_families':['reconstruction','behavioral_patch'],'reason':'Independent experimental evidence requires analyst review; not cryptographic confirmation'}
            elif backdoor_evidence:
                disposition='REVIEW'; chosen=backdoor_evidence[0]
                trigger={'type':'EXPERIMENTAL_BACKDOOR_EVIDENCE','asset':chosen.get('asset_id'),'risk':chosen.get('risk_score',0),
                         'evidence_families':['reconstruction' if chosen.get('detector')=='neural_cleanse' else 'behavioral_patch'],
                         'reason':'Suspicious experimental backdoor evidence requires analyst review; not cryptographic confirmation'}
            elif moderate:
                disposition='REVIEW'; chosen=moderate[0]
                trigger={'type':'CALIBRATED_ANOMALY','asset':chosen.get('asset_id'),'risk':chosen.get('risk_score',0),
                         'evidence_families':[quality(chosen).get('evidence_family','representation')],'reason':'Moderate calibrated anomaly requires review'}
    return {'composite_risk':composite.get('risk_score',0),'composite_severity':composite.get('severity',severity(composite.get('risk_score',0))),
            'max_asset_risk':max_risk,'highest_severity':highest_severity,'highest_risk_asset':highest[1],
            'highest_risk_asset_type':highest[3],'highest_risk_reason':highest[4],'final_disposition':disposition,
            'disposition_trigger':trigger,'confidence':composite.get('confidence',0),'coverage':composite.get('coverage_fraction',0),
            'composite_score_type':'Heuristic cross-domain aggregate; not an attack probability.',
            'policy':'Cryptographic failures and multi-family critical contributor evidence override composite action; experimental backdoor evidence remains REVIEW unless an independent integrity rule applies.'}
