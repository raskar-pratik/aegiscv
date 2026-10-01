"""Bounded pairwise MVP detectors with explicit negative and unavailable results."""
from collections import defaultdict
import numpy as np
from core.schemas import Finding
from core.config import Config
from detectors.data_integrity.features import dhash
from detectors.data_integrity.near_confirmation import representation,compare,profile,confirmed


def finding(detector, asset, score, reason, evidence, confidence=.65, status='SUCCESS', attack=None):
    return Finding(detector,'DATA_INTEGRITY',attack or detector.upper(),asset,score,confidence,reason,evidence,status=status).to_dict()


def duplicates(assets, root, features, config):
    groups=defaultdict(list)
    for a in assets: groups[a['sha256']].append(a['asset_id'])
    results=[finding('exact_duplicate',ids[0],min(95,35+10*len(ids)),'Identical asset bytes',{'members':ids,'sha256':sha},1) for sha,ids in groups.items() if len(ids)>1]
    hashes=[dhash(root/a['asset_id']) for a in assets]
    calibration=profile(); limits=calibration['thresholds']; pixels=[representation(root/a['asset_id']) for a in assets]; edges=[]
    parents=list(range(len(assets)))
    def find(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]]; i=parents[i]
        return i
    for i in range(len(assets)):
        distances=1-features[i+1:]@features[i]
        for off,d in enumerate(distances):
            j=i+1+off
            if assets[i]['sha256'] != assets[j]['sha256'] and (hashes[i]^hashes[j]).bit_count() <= min(config.near_hamming,limits['hamming']) and d <= config.near_color_distance:
                confirmation=compare(pixels[i],pixels[j])
                if confirmed(confirmation,limits):
                    parents[find(j)]=find(i)
                    edges.append({'members':[assets[i]['asset_id'],assets[j]['asset_id']],'hamming':(hashes[i]^hashes[j]).bit_count(),**confirmation})
    near=defaultdict(list)
    for i,a in enumerate(assets): near[find(i)].append(a['asset_id'])
    results += [finding('near_duplicate',ids[0],min(85,30+5*len(ids)),'Connected component of visually confirmed copy pairs; no all-pairs equivalence claim',{'members':ids,'confirmed_pairs':[e for e in edges if e['members'][0] in ids],'thresholds':limits,'calibration_profile_hash':calibration['profile_hash'],'transitive_pairs_verified':False},.65) for ids in near.values() if len(ids)>1]
    for detector in ['exact_duplicate','near_duplicate']:
        if not any(f['detector']==detector for f in results):
            results.append(finding(detector,'dataset',0,'No matching pairs at configured threshold',{'sample_count':len(assets)},1 if detector=='exact_duplicate' else .65))
    return results


def labels(assets, features, config):
    eligible=[i for i,a in enumerate(assets) if len(a['labels'])==1]
    if len(eligible)<3:
        return [finding('label_anomaly','dataset',0,'Requires at least three singly labeled images; object-level analysis is unavailable',{},0,'UNAVAILABLE')]
    results=[]
    for i in eligible:
        candidates=[j for j in eligible if j!=i and assets[j]['sha256']!=assets[i]['sha256']]
        if not candidates: continue
        order=sorted(candidates,key=lambda j:float(1-features[i]@features[j]))[:config.neighbors]
        disagreement=sum(assets[j]['labels']!=assets[i]['labels'] for j in order)/len(order)
        if disagreement>=config.label_disagreement:
            results.append(finding('label_anomaly',assets[i]['asset_id'],round(disagreement*90,2),'Declared label disagrees with nearest visual neighbors',{'neighbors':[assets[j]['asset_id'] for j in order],'disagreement':disagreement,'label':assets[i]['labels']},.6))
    return results or [finding('label_anomaly','dataset',0,'No label disagreement above threshold',{'eligible_samples':len(eligible)},.6)]


def ood(assets, features, config, reference=None):
    results=[]
    if reference is None:
        return [finding('ood','dataset',0,'Trusted reference embeddings are required for OOD assessment',{},0,'UNAVAILABLE')]
    for i,a in enumerate(assets):
        distance=float(np.clip(np.min(1-reference@features[i]),0,2))
        if distance>config.ood_distance:
            results.append(finding('ood',a['asset_id'],min(100,50+distance*50),'Image lies outside supplied reference neighborhood',{'nearest_reference_cosine_distance':distance,'threshold':config.ood_distance},.65))
    return results or [finding('ood','dataset',0,'All samples fall within configured reference neighborhood',{'reference_count':len(reference)},.65)]


def contributors(assets, findings):
    from core.quality import quality
    groups=defaultdict(list)
    for a in assets: groups[a['contributor']].append(a['asset_id'])
    rows=[]
    for source,ids in groups.items():
        affected={}; families={}; evidence=[]
        for f in findings:
            if f['status']!='SUCCESS' or f['risk_score']<=20: continue
            members=set(f['evidence'].get('members',[])+[f['asset_id']]) & set(ids)
            if not members: continue
            q=quality(f); family=q['evidence_family']
            bucket=families.setdefault(f['detector'],{'family':family,'members':set(),'severity':0.,'confidence':0.,'weight':0.})
            bucket['members'].update(members); bucket['severity']=max(bucket['severity'],f['risk_score']); bucket['confidence']=max(bucket['confidence'],f['confidence']); bucket['weight']=max(bucket['weight'],q['risk_weight'])
            affected.update({a:True for a in members}); evidence.append({'finding_id':f['finding_id'],'detector':f['detector'],'quality':q,'affected_samples':len(members)})
        components={}
        for b in families.values():
            value=round(b['severity']*b['weight']*(.5+.5*b['confidence'])*min(1,len(b['members'])/len(ids)/.2),2)
            components[b['family']]=max(components.get(b['family'],0),value)
        score=min(100,round(sum(components.values()),2))
        rows.append({'contributor':source,'samples':len(ids),'affected_samples':len(affected),'affected_fraction':len(affected)/len(ids),'risk_score':score,
                     'evidence_families':components,'evidence':evidence,'recommended_action':'REVIEW' if evidence and score<=20 else 'QUARANTINE' if score>80 else 'REVIEW' if score>20 else 'ACCEPT',
                     'score_type':'Sum of distinct-family severity × reliability × confidence factor × concentration (saturates at 20%); representation and duplicate signals each share a family'})
    return sorted(rows,key=lambda r:-r['risk_score'])
