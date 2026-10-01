"""Reproducible stabilization suite; preserves final_validation as the before snapshot."""
import argparse,json,tempfile
from pathlib import Path
import numpy as np
from core.risk import fuse
from core.quality import WEIGHTS,quality
from core.schemas import Finding
from experiments.benchmark import generate
from experiments.stabilization_calibration import run as calibrate_pairs,transform,TRANSFORMS
from detectors.data_integrity.features import dhash,VisualEncoder
from detectors.data_integrity.near_confirmation import profile,representation,compare,confirmed
from detectors.distribution_shift.acquisition import statistics,calibrate
from experiments.final_validation import run as full_suite,save

def heldout_pairs(output):
    p=profile(); thresholds=p['thresholds']
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp); b=generate(root/'data'); assets=b['partitions']['evaluation']['assets']
        paths=[root/'data/evaluation'/a['asset_id'] for a in assets]; reps=[representation(x) for x in paths]; hashes=[dhash(x) for x in paths]; encoder=VisualEncoder(); features=encoder.encode(paths)
        false_pairs=[]; counts={kind:{'tp':0,'fn':0} for kind in TRANSFORMS}
        for i in range(len(paths)):
            for j in range(i+1,len(paths)):
                if (hashes[i]^hashes[j]).bit_count()<=thresholds['hamming'] and 1-features[i]@features[j]<=.08 and confirmed(compare(reps[i],reps[j]),thresholds): false_pairs.append([assets[i]['asset_id'],assets[j]['asset_id']])
        for i,path in enumerate(paths):
            for kind in TRANSFORMS:
                dest=root/'copy.png'; transform(path,dest,kind,991+i)
                match=(hashes[i]^dhash(dest)).bit_count()<=thresholds['hamming'] and 1-features[i]@encoder.encode_image(dest)<=.08 and confirmed(compare(reps[i],representation(dest)),thresholds)
                counts[kind]['tp' if match else 'fn']+=1
        negatives=len(paths)*(len(paths)-1)//2; tp=sum(c['tp'] for c in counts.values()); fn=sum(c['fn'] for c in counts.values())
        result={'profile_hash':p['profile_hash'],'negative_pairs':negatives,'positive_pairs':tp+fn,'fp':len(false_pairs),'tn':negatives-len(false_pairs),'tp':tp,'fn':fn,
            'pair_fpr':len(false_pairs)/negatives,'clean_image_fpr':len({x for pair in false_pairs for x in pair})/len(paths),'recall':tp/(tp+fn),'by_transform':counts,
            'false_pairs':false_pairs,'scope':'Production hash, cosine and pixel confirmation on held-out independent pairs and known transformed copies; cluster membership separately evaluated in full suite'}
        save(output/'heldout_pairs.json',result); return result

def legacy_fuse(findings):
    names=['DATA_INTEGRITY','MODEL_INTEGRITY','INFERENCE_INTEGRITY','DISTRIBUTION']; weights=[1,1.2,1.2,1]
    scores=[max([f['risk_score'] for f in findings if f['status']=='SUCCESS' and f['category']==name] or [0]) for name in names]
    if any(f['status']=='SUCCESS' and f['detector'] in {'model_hash','ledger_verification'} and f['risk_score']==100 for f in findings): return 100.
    active=[(s,w) for s,w in zip(scores,weights) if s>0]; return round(sum(s*w for s,w in active)/sum(w for _,w in active),2) if active else 0.

def summarize(output):
    before=Path('experiments/results/final_validation'); after=output/'full_suite'
    read=lambda root,name:json.loads((root/name).read_text())
    bm=read(before,'detector_metrics.json'); am=read(after,'detector_metrics.json'); old=read(before,'summary.json'); new=read(after,'summary.json')
    metric=lambda rows,detector,scenario:next(r for r in rows if r['detector']==detector and r['attack']==scenario)
    comparisons=[]
    for title,detector,scenario,key in [('Near clean image FPR','near_duplicate','clean-0','fpr'),('Near precision','near_duplicate','near_duplicate-0.2','precision'),('Near recall','near_duplicate','near_duplicate-0.2','recall'),('Near F1','near_duplicate','near_duplicate-0.2','f1'),('Clean contributors falsely flagged','contributor_aggregation','clean-0','fp')]:
        comparisons.append({'metric':title,'before':metric(bm,detector,scenario)[key],'after':metric(am,detector,scenario)[key]})
    clean=read(after,'evidence-clean-0.json'); malicious=read(after,'malicious_contributor.json'); old_malicious=read(before,'malicious_contributor.json')
    # Re-evaluate action/quality policy from retained raw findings; detector scores are never rewritten.
    clean_risk=fuse(clean['findings']); malicious_risk=fuse(malicious['findings'])
    backs=read(after,'backdoor_results.json'); prior_backs=read(before,'backdoor_results.json')
    baseline=backs['preserved_baseline']['records']['backdoored']; old_baseline=prior_backs['preserved_baseline']['records']['backdoored']
    risk_rows=[('Clean risk',legacy_fuse(read(before,'evidence-clean-0.json')['findings']),clean_risk['risk_score']),
        ('Malicious contributor case risk',legacy_fuse(old_malicious['findings']),malicious_risk['risk_score']),
        ('Backdoor fixture risk',legacy_fuse([old_baseline['reconstruction'],old_baseline['patch_probe']]),fuse([baseline['reconstruction'],baseline['patch_probe']])['risk_score']),
        ('OOD case risk',old['cross_layer']['I']['assurance']['risk_score'],new['cross_layer']['I']['assurance']['risk_score'])]
    comparisons.extend({'metric':name,'before':a,'after':b} for name,a,b in risk_rows)
    pairs=heldout_pairs(output)
    save(Path('core/calibration/quality_gate.json'),{'profile_hash':pairs['profile_hash'],'eligible':pairs['clean_image_fpr']<=.02 and metric(am,'near_duplicate','clean-0')['fpr']<=.02,
        'heldout_image_fpr':pairs['clean_image_fpr'],'injected_scenario_f1':metric(am,'near_duplicate','near_duplicate-0.2')['f1'],'policy':'Validation gates escalation only; thresholds are not retuned'})
    backdoor_cases=[r for r in backs['records'] if r['split']=='evaluation' and ((r['training']['poison_rate']==0 and r['detected']) or (r['training']['poison_rate']>0 and not r['detected']))]
    decisions=[{'model':r['name'],'clean_accuracy':r['clean_accuracy'],'ASR':r['attack_success_rate'],'anomaly_index':r['anomaly_index'],'raw_detected':r['detected'],'assessment':r['backdoor_assessment'],
        'diagnosis':'Relative small-mask outlier on a clean classifier does not establish poisoning.' if r['training']['poison_rate']==0 else 'High-ASR backdoor lacks a sufficiently exceptional recovered mask; optimization/MAD comparison is a sensitivity limitation.'} for r in backdoor_cases]
    result={'before_source':str(before),'after_source':str(after),'comparison':comparisons,'clean':{'assurance':clean_risk,'contributors':clean['contributors'],'positive_findings':[f for f in clean['findings'] if f['risk_score']>20]},
        'malicious_contributor':{'assurance':malicious_risk,'contributors':malicious['contributors']},'heldout_pairs':pairs,
        'drift':{'before':old['cross_layer']['H']['expectation_met'],'after':new['cross_layer']['H']['expectation_met'],'acquisition':new['cross_layer']['H']['acquisition_shift'],'OOD_shift':new['cross_layer']['I']['expectation_met']},
        'backdoor':{'before':prior_backs['metrics'],'after':backs['metrics'],'failure_analysis':decisions},'monotonicity':new['fusion'],
        'quality_weights':WEIGHTS,'network':new['network'],'cryptographic_checks':{k:new['cross_layer'][k]['expectation_met'] for k in ['D','E','F','G']},
        'demo_freeze':'PENDING_TEST_AND_BROWSER_VERIFICATION','limitations':['Generated-domain calibration is not a natural-image operating guarantee.','The same held-out benchmark was used across phases; report this as regression validation, not a fresh external generalization estimate.','Raw backdoor false positives and false negatives remain; strong evidence is still an analyst REVIEW.','Fixed-denominator risk intentionally changes score scale; no attack-probability interpretation.','Pair recall does not imply that all transitive cluster pairs were confirmed.']}
    save(output/'comparison.json',result)
    lines=['# Reliability stabilization and demo freeze','', '## Quantitative root causes','', 'See pair_diagnosis.json: dHash and color gates lose image-specific texture; connected components imply unsupported transitive links. Pair truth is now separate from image/cluster membership truth. Calibration uses 19,900 independent negatives and 1,200 transformed-copy positives, with no held-out features used for selection.','',
           '## Before versus after','', '|Metric|Before|After|','|---|---|---|']
    lines += [f"|{r['metric']}|{r['before']}|{r['after']}|" for r in comparisons]
    lines += ['', '## Held-out transformed copies','',json.dumps(pairs['by_transform']),f"\nPair FPR {pairs['pair_fpr']}; image FPR {pairs['clean_image_fpr']}; copy recall {pairs['recall']}. No thresholds were changed after this evaluation.",
        '', '## Risk policy and contributor reliability','',clean_risk['method'], 'Quality multipliers: '+json.dumps(WEIGHTS)+'. Multipliers are conservative policy choices, not empirical probabilities. Contributor scores group related representation and duplication evidence, use affected fraction, confidence and quality, and preserve every finding. A fixed denominator changes the numerical scale relative to the prior active-category mean.',
        '', '## Clean control','',f"Risk {clean_risk['risk_score']}, {clean_risk['severity']}, {clean_risk['recommended_action']}. Positive findings remain visible in comparison.json; residual OOD false alarms are not hidden.",
        '', '## Operational drift','',json.dumps(result['drift']['acquisition']['evidence'],indent=2),
        '', 'Acquisition changes are described as OPERATIONAL DISTRIBUTION SHIFT DETECTED, with no attribution of malicious intent. Embedding thresholds were not lowered. Correlation requires separate suspicious evidence.',
        '', '## Backdoor limitations','',f"Before: TP {prior_backs['metrics']['tp']}, FP {prior_backs['metrics']['fp']}, TN {prior_backs['metrics']['tn']}, FN {prior_backs['metrics']['fn']}. After: TP {backs['metrics']['tp']}, FP {backs['metrics']['fp']}, TN {backs['metrics']['tn']}, FN {backs['metrics']['fn']}.",json.dumps(decisions,indent=2),
        '', 'No inversion threshold was tuned to either failure. Reconstruction evidence, held-out recovery and matching behavioral patch confirmation are reported separately. None is labeled a confirmed backdoor.',
        '', '## Reproduce','', '```powershell','python -m experiments.stabilization','python -m unittest discover -s tests -v','python run.py','# Separate terminal, local Edge/Playwright already installed:','python scripts/browser_check.py','```',
        '', 'The original final_validation artifacts are retained. Full after results are under full_suite/. Freeze remains pending until final test/browser verification is appended.','', '## Remaining limitations','']+['- '+s for s in result['limitations']]
    (output/'STABILIZATION_REPORT.md').write_text('\n'.join(lines),encoding='utf-8'); return result

def run(output,summarize_only=False):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    if not summarize_only:
        calibrate_pairs(output)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); b=generate(root); a=b['partitions']['reference']; c=b['partitions']['calibration']
            calibrate(statistics([root/'reference'/x['asset_id'] for x in a['assets']]),statistics([root/'calibration'/x['asset_id'] for x in c['assets']]),a['manifest_hash'],c['manifest_hash'])
        full_suite(output/'full_suite')
    return summarize(output)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,default=Path('experiments/results/stabilization')); parser.add_argument('--summarize-only',action='store_true'); args=parser.parse_args(); run(args.output,args.summarize_only)
