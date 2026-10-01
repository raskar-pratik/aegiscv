"""Offline calibration, held-out measurements, and reproducible evidence artifacts."""
import argparse
import csv
import json
import os
import platform
import shutil
import socket
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
import numpy as np
from adapters.datasets.ingestion import ingest
from attack_simulator.annotations import generate_annotations
from core.config import Config
from core.thresholds import freeze,apply_profile,registry
from core.risk import fuse
from core.schemas import Finding
from core.correlation import correlate_findings
from detectors.data_integrity.features import VisualEncoder
from detectors.data_integrity.resnet_encoder import select_encoder
from detectors.data_integrity.engine import duplicates,labels,ood,contributors
from detectors.data_integrity.spectral import spectral_signatures
from detectors.data_integrity.trigger_pattern import detect_patterns
from detectors.data_integrity.annotations import annotation_integrity
from detectors.distribution_shift.embedding_shift import compare
from detectors.distribution_shift.acquisition import compare_acquisition
from experiments.benchmark import generate,attack
from experiments.validation_metrics import evaluate
from experiments.hardening import flagged
from experiments.backdoor_robustness import run as backdoors
from provenance.hashing import digest


def save(path,value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')


def calibrate(root,encoder,benchmark,output):
    ref=benchmark['partitions']['reference']['assets']; cal=benchmark['partitions']['calibration']['assets']
    reference=encoder.encode([root/'reference'/a['asset_id'] for a in ref])
    features=encoder.encode([root/'calibration'/a['asset_id'] for a in cal])
    distances=np.clip(1-features@reference.T,0,2).min(1)
    threshold=max(1e-6,float(np.quantile(distances,.99,method='higher')))
    truth=attack(root/'calibration',root/'calibration-flips','label_flip',.1,benchmark['seed'])
    altered=ingest(root/'calibration-flips')['assets']; altered_features=encoder.encode([root/'calibration-flips'/a['asset_id'] for a in altered])
    candidates=[]
    for value in [.6,.75,.9,1.]:
        config=Config(label_disagreement=value)
        clean_pred=flagged(labels(cal,features,config)); pred=flagged(labels(altered,altered_features,config))
        m=evaluate('label_anomaly','calibration',[a['asset_id'] for a in altered],truth['truth']['label_anomaly'],pred)
        candidates.append({'threshold':value,'clean_fpr':len(clean_pred&{a['asset_id'] for a in cal})/len(cal),'poisoned_f1':m['f1'] or 0.})
    eligible=[r for r in candidates if r['clean_fpr']<=.05]
    winner=max(eligible,key=lambda r:(r['poisoned_f1'],r['threshold'])) if eligible else None
    values={'ood_distance':threshold}
    if winner: values['label_disagreement']=winner['threshold']
    profile=freeze(values,[a['asset_id'] for a in cal],[a['asset_id'] for a in benchmark['partitions']['evaluation']['assets']],encoder.encoder_hash,
        {'ood':'99th percentile (higher) of clean calibration nearest-reference distances; empirical, no population FPR guarantee',
         'label':'Maximum F1 on 10% calibration label flips subject to clean calibration FPR <= 5%; ties choose stricter threshold',
         'candidates':candidates,'no_eligible_label_candidate':winner is None,'calibration_attack_hash':truth['attack_hash'],
         'calibration_manifest_hash':benchmark['partitions']['calibration']['manifest_hash'],
         'reference_manifest_hash':benchmark['partitions']['reference']['manifest_hash']})
    thresholds=registry(apply_profile(profile,encoder.encoder_hash))
    for key in values: thresholds[key]['status']='CALIBRATED_ON_GENERATED_CALIBRATION_ONLY'
    save(output/'calibration.json',profile); save(output/'threshold_registry.json',thresholds)
    return apply_profile(profile,encoder.encoder_hash),reference,profile


def detectors(root,encoder,reference,config):
    times={}; start=time.perf_counter(); manifest=ingest(root); times['hashing_and_ingestion']=time.perf_counter()-start
    assets=manifest['assets']; start=time.perf_counter(); features=encoder.encode([root/a['asset_id'] for a in assets]); times['feature_extraction']=time.perf_counter()-start
    start=time.perf_counter(); pair=duplicates(assets,root,features,config); pair_time=time.perf_counter()-start
    results={name:([f for f in pair if f['detector']==name],pair_time/2) for name in ['exact_duplicate','near_duplicate']}
    calls={'label_anomaly':lambda:labels(assets,features,config),'ood':lambda:ood(assets,features,config,reference),
           'spectral_signature':lambda:spectral_signatures(assets,features,min_samples=config.spectral_min_samples,threshold=config.spectral_threshold),
           'trigger_pattern':lambda:detect_patterns(assets,root)}
    for name,fn in calls.items():
        start=time.perf_counter(); findings=fn(); results[name]=(findings,time.perf_counter()-start)
    times['data_detectors']=sum(t for _,t in results.values())
    return manifest,features,results,times


def example(output,root,scenario,name,category,ids,findings,assets,truth):
    if not ids: return {'status':'NOT_OBSERVED'}
    asset_id=sorted(ids)[0]; a=next(a for a in assets if a['asset_id']==asset_id)
    linked=[f for f in findings if asset_id==f['asset_id'] or asset_id in f['evidence'].get('members',[])]
    relative=f'examples/{scenario}-{name}-{category}.png'; dest=output/relative; dest.parent.mkdir(exist_ok=True)
    shutil.copyfile(root/asset_id,dest)
    interpretations={'exact_duplicate':'Exact byte equality is deterministic; group truth includes original members.',
        'near_duplicate':'dHash and cosine thresholds can merge independently generated similar textures; pixel perturbations may cross hash boundaries.',
        'label_anomaly':'Neighbor agreement assumes appearance follows class and local neighborhoods have mostly correct labels.',
        'ood':'Reference distances distinguish appearance; nuisance variation and reference coverage control the decision.',
        'spectral_signature':'Minority poison must form a sufficiently energetic class-conditional spectral outlier; contamination may blend into variance.',
        'trigger_pattern':'Only constant high-contrast corners with enough support and label association are covered.',
        'annotation_integrity':'Geometry checks detect malformed boxes; folder classification has no object annotations.'}
    return {'status':'OBSERVED','scenario':scenario,'asset':a,'image':relative,'findings':linked,
            'attack':truth,'interpretation':interpretations.get(name),'interpretation_status':'Mechanistic explanation, not a proven causal attribution',
            'negative_evidence':None if linked else 'No finding exceeded the fixed review threshold for this asset.'}


def matrix(root,benchmark,encoder,output):
    output.mkdir(parents=True,exist_ok=True); config,reference,profile=calibrate(root,encoder,benchmark,output)
    scenarios=[('clean',0.)]+[(k,r) for k in ['label_flip','trigger'] for r in [.01,.05,.1,.2]]
    scenarios += [('exact_duplicate',.2),('near_duplicate',.2)]+[('ood',r) for r in [.05,.15,.3]]+[('contributor',.2),('benign_shift',1.)]
    rows=[]; attacks=[]; failures={}; runtime=[]; risk=[]; cross={}
    refassets=benchmark['partitions']['reference']['assets']
    for kind,rate in scenarios:
        start=time.perf_counter(); name=f'{kind}-{rate:g}'; path=root/name
        truth=attack(root/'evaluation',path,kind,rate,benchmark['seed']); manifest,features,results,times=detectors(path,encoder,reference,config)
        assets=manifest['assets']; universe={a['asset_id'] for a in assets}; allfindings=[]
        for detector,(findings,elapsed) in results.items():
            if detector in {'label_anomaly','ood'}:
                from core.quality import annotate
                for finding in findings:
                    finding['calibration_profile_hash']=profile['profile_hash']; annotate(finding)
            actual=set(truth['truth'].get(detector,[])); predicted=flagged(findings)&universe; scores=None
            if detector=='ood': scores=dict(zip([a['asset_id'] for a in assets],np.clip(1-features@reference.T,0,2).min(1).astype(float).tolist()))
            if detector=='label_anomaly':
                scores={}
                for i,a in enumerate(assets):
                    candidates=[j for j,b in enumerate(assets) if j!=i and b['sha256']!=a['sha256']]
                    near=sorted(candidates,key=lambda j:float(1-features[i]@features[j]))[:config.neighbors]
                    scores[a['asset_id']]=sum(assets[j]['labels']!=a['labels'] for j in near)/len(near) if near else 0.
            row=evaluate(detector,name,universe,actual,predicted,elapsed,scores); row['encoder']=encoder.encoder_id; rows.append(row)
            for category,ids in [('TP',actual&predicted),('FP',predicted-actual),('FN',actual-predicted)]:
                key=detector+':'+category
                if key not in failures or failures[key]['status']=='NOT_OBSERVED': failures[key]=example(output,path,name,detector,category,ids,findings,assets,truth)
            allfindings.extend(findings)
        start_shift=time.perf_counter(); shift=compare(reference,features,[a['labels'] for a in refassets],[a['labels'] for a in assets])
        times['distribution_shift']=time.perf_counter()-start_shift
        shift_actual={name} if kind in {'benign_shift','ood'} else set()
        shift_row=evaluate('embedding_shift',name,[name],shift_actual,[name] if shift['risk_score']>20 else [],times['distribution_shift'],unit='dataset')
        shift_row['encoder']=encoder.encoder_id; rows.append(shift_row)
        acquisition=compare_acquisition([root/'reference'/a['asset_id'] for a in refassets],[path/a['asset_id'] for a in assets])
        allfindings.extend([shift,acquisition]); source_start=time.perf_counter(); sources=contributors(assets,allfindings)
        times['contributor_aggregation']=time.perf_counter()-source_start
        contributor_truth={'malicious-contributor'} if kind in {'contributor','label_flip','trigger','ood'} else set()
        source_row=evaluate('contributor_aggregation',name,[r['contributor'] for r in sources],contributor_truth,[r['contributor'] for r in sources if r['risk_score']>20],times['contributor_aggregation'],unit='contributor')
        source_row['encoder']=encoder.encoder_id; rows.append(source_row)
        source_pred={r['contributor'] for r in sources if r['risk_score']>20}
        for category,ids in [('TP',contributor_truth&source_pred),('FP',source_pred-contributor_truth),('FN',contributor_truth-source_pred)]:
            key='contributor_aggregation:'+category
            if key not in failures or failures[key]['status']=='NOT_OBSERVED':
                selected=sorted(ids)[0] if ids else None
                failures[key]={'status':'OBSERVED' if ids else 'NOT_OBSERVED','scenario':name,'contributor':selected,
                    'evidence':[r for r in sources if r['contributor']==selected],
                    'findings':[f for f in allfindings if any(a['contributor']==selected and (a['asset_id']==f['asset_id'] or a['asset_id'] in f['evidence'].get('members',[])) for a in assets)] if ids else [],
                    'interpretation':'Contributor mean risk inherits upstream false positives and may dilute sparse true anomalies; source attribution does not establish malicious intent.'}
        combined=fuse(allfindings,config); risk.append({'attack':kind,'rate':rate,**combined})
        correlations=correlate_findings(allfindings,assets)
        for category,observed in [('TP',bool(shift_actual) and shift['risk_score']>20),('FP',not shift_actual and shift['risk_score']>20),('FN',bool(shift_actual) and shift['risk_score']<=20)]:
            key='embedding_shift:'+category
            if key not in failures or failures[key]['status']=='NOT_OBSERVED':
                failures[key]={'status':'OBSERVED' if observed else 'NOT_OBSERVED','scenario':name,'finding':shift if observed else None,
                    'interpretation':'L2-normalized appearance features suppress global brightness changes. Shift thresholds may miss benign operational changes; changed labels or poison can also shift a distribution.'}
        if kind in {'benign_shift','ood','contributor'}: cross[name]={'assurance':combined,'contributors':sources,'shift':shift,'acquisition_shift':acquisition,'correlations':correlations}
        times.update(scenario=name,image_count=len(assets),dataset_bytes=sum(a['size'] for a in assets),total_scan_seconds=time.perf_counter()-start,
                     timing_scope='Includes attack copy/generation, metric and representative evidence work; model integrity separately timed')
        runtime.append(times); attacks.append({**truth,'manifest_hash':manifest['manifest_hash'],'sample_count':len(assets),
             'class_distribution':{label:sum(a['labels']==[label] for a in assets) for label in sorted({a['labels'][0] for a in assets})}})
        save(output/f'evidence-{name}.json',{'manifest':manifest,'findings':allfindings,'contributors':sources,'correlations':correlations,'assurance':combined})
        print('Dataset case completed: '+name,flush=True)
    return {'rows':rows,'attacks':attacks,'failures':failures,'runtime':runtime,'risk':risk,'cross':cross,'profile_hash':profile['profile_hash']}


def fusion_validation(risks):
    series=[]
    clean=next(r['risk_score'] for r in risks if r['attack']=='clean')
    for attack in ['label_flip','trigger','ood']:
        points=[{'rate':0,'risk':clean}]+[{'rate':r['rate'],'risk':r['risk_score']} for r in risks if r['attack']==attack]
        series.append({'attack':attack,'points':points,'nondecreasing':all(a['risk']<=b['risk'] for a,b in zip(points,points[1:])),
                       'strictly_increasing':all(a['risk']<b['risk'] for a,b in zip(points,points[1:]))})
    make=lambda category,score:Finding('controlled_'+category,category,'SYNTHETIC_CHECK','system',score,.5,'Fusion mechanics probe',{}).to_dict()
    strong=[make('DATA_INTEGRITY',90)]; extra=strong+[make('DISTRIBUTION',30)]
    weak=fuse([make(c,30) for c in ['DATA_INTEGRITY','MODEL_INTEGRITY','INFERENCE_INTEGRITY','DISTRIBUTION']])
    return {'contamination_series':series,'weak_anomalies':weak,'weak_anomalies_critical':weak['severity']=='CRITICAL',
            'new_category_counterexample':{'before':fuse(strong),'after':fuse(extra),'monotonic':fuse(extra)['risk_score']>=fuse(strong)['risk_score']},
            'interpretation':fuse(strong)['method']+' Contamination rates can change the underlying evidence; coordinate-wise monotonicity is tested separately from contamination-series ordering.'}


def validate_result(summary,rows):
    for key in ['dataset','encoder','calibration_profile_hash','judge_metrics','limitations','cross_layer']: 
        if key not in summary: raise ValueError('Missing result field '+key)
    if len(summary['judge_metrics'])>5: raise ValueError('Too many judge metrics')
    for row in rows:
        if sum(row[k] for k in ['tp','fp','tn','fn'])!=row['clean_samples']+row['attack_samples']: raise ValueError('Invalid confusion counts')
        for key in ['precision','recall','f1','fpr','roc_auc','pr_auc']:
            if row.get(key) is not None and not 0<=row[key]<=1: raise ValueError('Invalid metric '+key)


def run(output,seed=26228):
    import torch
    from demo.runner import run_demo
    output=Path(output); output.mkdir(parents=True,exist_ok=True); started=time.perf_counter(); torch.set_num_threads(1)
    network_attempts=[]
    def blocked(*args,**kwargs):
        network_attempts.append(str(args[1:])); raise RuntimeError('Benchmark prohibits network access')
    environment={'os':platform.platform(),'cpu':platform.processor(),'logical_cpus':os.cpu_count(),'python':platform.python_version(),
                 'numpy':np.__version__,'torch':torch.__version__,'cuda_available':torch.cuda.is_available(),'torch_threads':torch.get_num_threads(),
                 'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,'seed':seed}
    scratch=Path(__file__).resolve().parents[3]/'work'; scratch.mkdir(exist_ok=True)
    with patch.object(socket.socket,'connect',blocked),patch.object(socket.socket,'connect_ex',blocked),patch('socket.getaddrinfo',blocked), tempfile.TemporaryDirectory(dir=scratch,prefix='validation-') as temp:
        root=Path(temp); benchmark=generate(root/'benchmark',seed); save(output/'dataset_manifest.json',benchmark)
        encoder=VisualEncoder(); selected,capability=select_encoder()
        result=matrix(root/'benchmark',benchmark,encoder,output)
        semantic=None
        # A checksum pin records operator trust intent; compatibility alone does not prove pretraining.
        if capability['status']=='LOCAL_WEIGHTS_LOADED' and capability.get('checksum_pinned'):
            semantic_root=root/'semantic'
            for split in benchmark['partitions']: shutil.copytree(root/'benchmark'/split,semantic_root/split)
            semantic=matrix(semantic_root,benchmark,selected,output/'semantic')
            save(output/'semantic'/'detector_metrics.json',semantic['rows'])
        model_start=time.perf_counter(); backdoor=backdoors(output/'models'); model_seconds=time.perf_counter()-model_start
        print('Running end-to-end provenance controls',flush=True)
        demo=run_demo(root/'demo'); v=demo['verification']
        # Public evidence is retained; private signing keys and scratch databases are not exported.
        save(output/'end_to_end_evidence.json',demo)
        annotations=[]
        for format in ['coco','yolo']:
            for malformed in [False,True]:
                path=root/(format+str(malformed)); truth=generate_annotations(path,format,malformed,seed)
                manifest=ingest(path,format); start=time.perf_counter(); findings=annotation_integrity(manifest)
                row=evaluate('annotation_integrity',format+('-malformed' if malformed else '-clean'),[a['asset_id'] for a in manifest['assets']],truth if malformed else [],flagged(findings),time.perf_counter()-start)
                row['encoder']='not applicable'; annotations.append(row)
                save(output/(row['attack']+'.json'),{'manifest':manifest,'findings':findings,'ground_truth':truth})
                for category,ids in [('TP',set(truth)&flagged(findings) if malformed else set()),('FP',flagged(findings)-set(truth)),('FN',set(truth)-flagged(findings) if malformed else set())]:
                    key='annotation_integrity:'+category
                    if key not in result['failures'] or result['failures'][key]['status']=='NOT_OBSERVED': result['failures'][key]=example(output,path,row['attack'],'annotation_integrity',category,ids&{a['asset_id'] for a in manifest['assets']},findings,manifest['assets'],{'format':format,'malformed':malformed})
        # Dedicated malicious-source mix, preserving three distinct attack mechanisms in one dataset.
        mix1=root/'mixed-label'; mix2=root/'mixed-trigger'; mix3=root/'mixed-final'
        attack(root/'benchmark'/'evaluation',mix1,'contributor',.1,seed)
        attack(mix1,mix2,'trigger',.1,seed+1); duplicate_truth=attack(mix2,mix3,'exact_duplicate',.1,seed+2)
        mixed_attribution=json.loads((mix3/'contributors.json').read_text())
        for change in duplicate_truth['changes']: mixed_attribution[change['result']]='malicious-contributor'
        save(mix3/'contributors.json',mixed_attribution)
        mixed_manifest,mixed_features,mixed_results,_=detectors(mix3,encoder,encoder.encode([root/'benchmark'/'reference'/a['asset_id'] for a in benchmark['partitions']['reference']['assets']]),apply_profile(json.loads((output/'calibration.json').read_text()),encoder.encoder_hash))
        mixed_findings=[f for fs,_ in mixed_results.values() for f in fs]; mixed_sources=contributors(mixed_manifest['assets'],mixed_findings)
        save(output/'malicious_contributor.json',{'manifest':mixed_manifest,'findings':mixed_findings,'contributors':mixed_sources})
    for category in ['TP','FP','FN']:
        candidates=[r for r in backdoor['records'] if r['split']=='evaluation' and
            ((category=='TP' and r['training']['poison_rate']>0 and r['detected']) or
             (category=='FP' and r['training']['poison_rate']==0 and r['detected']) or
             (category=='FN' and r['training']['poison_rate']>0 and not r['detected']))]
        result['failures']['neural_cleanse:'+category]={'status':'OBSERVED' if candidates else 'NOT_OBSERVED','example':candidates[0] if candidates else None,
            'interpretation':'Small reconstructed masks need not uniquely identify poisoned models. Optimization and the relative median/MAD test can miss a high-ASR backdoor or flag a clean classifier.'}
    held_metrics=result['rows']+annotations+[backdoor['metrics']]
    clean_assurance=demo['clean']['assurance']; model_hash=v['model_substitution']
    cross={'A':{'description':'Trusted original control','assurance':clean_assurance,'inference':v['valid_inference'],'ledger':v['ledger'],
                'expectation_met':clean_assurance['recommended_action']=='ACCEPT' and v['valid_inference']['status']=='VALID' and v['ledger']['status']=='VALID'},
           'B':{'description':'Combined malicious-source label flips, trigger patches and duplicate flood','contributors':mixed_sources,
                'expectation_met':any(r['contributor']=='malicious-contributor' and r['risk_score']>20 for r in mixed_sources),'evidence':'malicious_contributor.json'},
           'C':{'description':'Preserved controlled backdoor','metrics':backdoor['preserved_baseline']['metrics'],
                'expectation_met':backdoor['preserved_baseline']['records']['backdoored']['reconstruction']['risk_score']>20},
           'D':{'description':'Substitution','hash':model_hash,'behavior':[f for f in demo['attacked']['findings'] if f['detector']=='behavioral_probe'],
                'expectation_met':model_hash['risk_score']==100 and any(f['risk_score']>20 for f in demo['attacked']['findings'] if f['detector']=='behavioral_probe')},
           'E':{'description':'Prediction modified after signing','verification':v['tampered_inference'],'expectation_met':v['tampered_inference']['status']=='TAMPERED'},
           'F':{'description':'Replay signed record','verification':v['replay'],'first_acceptance':v['first_acceptance'],'expectation_met':v['replay']['status']=='REPLAY' and v['first_acceptance']['status']=='VALID'},
           'G':{'description':'Historical entry modified','verification':v['tampered_ledger'],'expectation_met':v['tampered_ledger']['status']=='TAMPERED' and v['tampered_ledger'].get('sequence')==1},
           'H':{'description':'Benign blur/dimming: distribution evidence does not determine intent',**result['cross']['benign_shift-1']},
           'I':{'description':'30% unrelated-image contamination',**result['cross']['ood-0.3']}}
    cross['H']['expectation_met']=cross['H']['shift']['risk_score']>20 or cross['H']['acquisition_shift']['risk_score']>20
    cross['I']['expectation_met']=cross['I']['shift']['risk_score']>20 and any(r['evidence']['rule']=='source_ood_shift' for r in cross['I']['correlations'])
    ablation=[]
    for name in ['label_anomaly','ood','near_duplicate','spectral_signature','embedding_shift']:
        for row in [r for r in result['rows'] if r['detector']==name]:
            other=next((r for r in semantic['rows'] if r['detector']==name and r['attack']==row['attack']),None) if semantic else None
            metric='f1' if row['attack_samples'] else 'fpr'; a=row[metric]; b=other[metric] if other else None
            ablation.append({'detector':name,'scenario':row['attack'],'metric':metric,'handcrafted':a,'semantic':b,'difference':b-a if a is not None and b is not None else None,
                             'status':'MEASURED' if other else 'UNAVAILABLE: trusted checksum-pinned pretrained checkpoint not supplied'})
    duplicate=next(r for r in held_metrics if r['detector']=='exact_duplicate' and r['attack']=='exact_duplicate-0.2')
    outlier=next(r for r in held_metrics if r['detector']=='ood' and r['attack']=='ood-0.3')
    bm=backdoor['metrics']
    judge=[{'metric':'Signed inference tamper rejection','value':int(cross['E']['expectation_met']),'denominator':1,'scope':'One controlled alteration'},
           {'metric':'Replay rejection','value':int(cross['F']['expectation_met']),'denominator':1,'scope':'One repeated signed record'},
           {'metric':'Exact duplicate F1','value':duplicate['f1'],'scope':'60 injected copies; original group members included in duplicate truth'},
           {'metric':'OOD F1','value':outlier['f1'],'scope':'90 generated noise replacements / 300 evaluation images'},
           {'metric':'Backdoor detector recall','value':bm['recall'],'denominator':bm['attack_samples'],'scope':'Held-out tiny locally trained poisoned models; inspect ASR and false positives separately'}]
    limitations=['All data are generated color/texture controls, not natural-image or operational validation.',
        'Semantic encoder comparison unavailable unless a trusted local checksum-pinned checkpoint is provided.',
        'Calibration is specific to this generated benchmark; two thresholds calibrated, the rest explicitly heuristic.',
        'Scenarios reuse the same held-out base images; metric rows are correlated and must not be pooled as independent samples.',
        'Near-duplicate truth uses known injected families, not human perceptual adjudication; natural similarities may be counted as false positives.',
        'OOD injection replaces selected images to preserve a 300-image rate denominator.',
        'A detector-specific FP may be a legitimate response to another injected attack; truth is mechanism-specific.',
        'Runtime network guard covers Python socket connection and DNS attempts, not native-library system calls; browser observation is a separate artifact.',
        'Risk score is a fixed-policy heuristic, not an attack probability; see fusion mechanics results and stabilization property tests.']
    summary={'dataset':{k:v for k,v in benchmark.items() if k!='partitions'},'partition_counts':{k:v['count'] for k,v in benchmark['partitions'].items()},
             'encoder':{'used':encoder.capability(),'semantic_candidate':capability},'calibration_profile_hash':result['profile_hash'],
             'judge_metrics':judge,'cross_layer':cross,'limitations':limitations,'ablation':ablation,'fusion':fusion_validation(result['risk']),
             'network':{'attempted_python_socket_requests':network_attempts,'external_attempt_count':len(network_attempts)},
             'schema_version':1,'seed':seed,'metric_rows':len(held_metrics)}
    validate_result(summary,held_metrics)
    report_start=time.perf_counter()
    for filename,value in [('summary.json',summary),('detector_metrics.json',held_metrics),('attack_matrix.json',{'dataset_cases':result['attacks'],'cross_layer_cases':cross}),
                           ('backdoor_results.json',backdoor),('failures.json',result['failures']),('environment.json',environment),('ablation.json',ablation)]: save(output/filename,value)
    columns=['detector','attack','unit','clean_samples','attack_samples','tp','fp','tn','fn','precision','recall','f1','fpr','roc_auc','pr_auc','runtime_seconds']
    with (output/'summary.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns,extrasaction='ignore'); writer.writeheader(); writer.writerows(held_metrics)
    runtime={'dataset_scans':result['runtime'],'model_integrity_seconds':model_seconds,'report_generation_seconds':time.perf_counter()-report_start,
             'total_experiment_seconds':time.perf_counter()-started,'environment':'environment.json','notes':'Wall-clock on this machine only. Model robustness timing includes local training, accuracy/ASR evaluation and inversion. Combined duplicate-call time is split evenly between exact and near metric rows, not independently profiled. Report timing covers JSON/CSV serialization; Markdown rendering is excluded.'}
    save(output/'runtime.json',runtime); report(output,summary,held_metrics,backdoor,runtime)
    print(json.dumps({'output':str(output),'judge_metrics':judge,'runtime':runtime['total_experiment_seconds']},indent=2),flush=True)
    return summary


def report(output,summary,rows,backdoor,runtime):
    fmt=lambda x:'N/A' if x is None else f'{x:.4f}' if isinstance(x,float) else str(x)
    lines=['# AegisCV scientific validation','', '## Executive summary','',
           'These are measured synthetic-control results, not a general accuracy claim. Existing architecture and dashboard are preserved. Poor results and unavailable semantic measurements remain visible.',
           '', '## Experimental setup and datasets','',f"Seed {summary['seed']}; AegisCV Procedural-10 v1, RGB 32×32. Partitions: {summary['partition_counts']}. Independently seeded image generation and content/identity disjointness checks precede calibration. Full asset hashes and class counts: dataset_manifest.json.",
           '', '## Calibration','', 'OOD uses the higher 99th percentile of 200 clean calibration distances to 200 reference images. Label disagreement uses a predeclared four-value grid on 10% calibration flips, constrained by clean FPR ≤5%. Frozen profile and its hash are saved before any evaluation case. No held-out threshold optimization. All remaining important thresholds are marked UNCALIBRATED_HEURISTIC in threshold_registry.json.',
           '', '## Models','', 'Handcrafted normalized 198-dimensional appearance features are used for image measurements. A trusted pretrained ResNet18 checkpoint was not supplied for this run unless semantic rows explicitly say MEASURED. The preserved analytic six-class baseline is separate from newly trained 15-input/48-hidden/6-output MLP models. Each training case uses 600 images, Adam for 350 full-batch steps. Different seeds define independent draws; cases sharing a seed are paired controls and reuse base images. Poison rates are fractions of training samples relabeled to the target after inserting a white patch. Evaluation uses 36 fresh images per seed and excludes true-target images from ASR.',
           '', '## Attack generation and metrics','', 'Nested seeded source selections implement label flips and trigger poisoning at 1/5/10/20%, duplicate injection at 20%, OOD replacement at 5/15/30%, contributor poisoning, and deterministic benign blur/dimming. Full changes and manifest identities are in attack_matrix.json. Duplicate truth includes originals plus injected copies; contributor metrics use contributor units. Annotation tests separately exercise COCO and YOLO malformed geometry. Scores above 20 count as findings. Undefined denominators are null. ROC AUC is pairwise and tie-aware; PR AUC is average precision. Image-level continuous scores are available for label disagreement and OOD. Model-level AUC uses the reconstruction anomaly index when every evaluated model has a valid index. Other AUCs are not invented.',
           '', '## Detector results','', '|Detector|Scenario|TP|FP|TN|FN|Precision|Recall|F1|FPR|ROC AUC|PR AUC|','|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows: lines.append('|'+ '|'.join(fmt(r.get(k)) for k in ['detector','attack','tp','fp','tn','fn','precision','recall','f1','fpr','roc_auc','pr_auc'])+'|')
    lines+=['','## Backdoor results','','Fixed inversion settings apply to calibration and held-out models alike. Calibration models are diagnostic; the index threshold remains heuristic. Positive truth below means poisoned training, not guaranteed successful backdoor acquisition. See per-model ASR before interpreting a miss. The original analytic baseline and masks are retained under models/preserved_baseline.','',
            '|Split / model|CA|ASR|Recovered target|Recovered success|Mask norm|Median|MAD|Index|Detected|','|---|---|---|---|---|---|---|---|---|---|']
    for r in backdoor['records']: lines.append('|'+ '|'.join(fmt(r.get(k)) for k in ['name','clean_accuracy','attack_success_rate','recovered_target','recovered_trigger_success','mask_norm','median','mad','anomaly_index','detected'])+'|')
    lines+=['','## False positives and false negatives','','failures.json retains representative TP/FP/FN images and supporting detector evidence for each observed category. NOT_OBSERVED means absent in these cases, not impossible. Similar generated images can violate near-duplicate ground-truth assumptions. Spectral detection assumes a separable minority; simple flips may not meet that assumption. Patch detection is limited to supported, constant high-contrast corners. Model inversion can fail even when a backdoor has high ASR. Cross-detector responses to other attack mechanisms are counted against mechanism-specific truth, not silently credited.','',
            '## Ablation results','','|Detector|Scenario|Metric|Handcrafted|Semantic|Difference|','|---|---|---|---|---|---|']
    for r in summary['ablation']: lines.append('|'+ '|'.join(fmt(r[k]) for k in ['detector','scenario','metric','handcrafted','semantic','difference'])+'|')
    lines+=['','No semantic improvement is claimed when the checkpoint is unavailable. See docs/checkpoint_provisioning.md for offline pinning and compatibility validation.','',
            '## Risk and cross-layer scenarios','',summary['fusion']['interpretation'],'',
            '|Case|Expectation met|','|---|---|']
    for name,case in summary['cross_layer'].items(): lines.append(f"|{name}: {case['description']}|{case['expectation_met']}|")
    clean_rows={r['detector']:r for r in rows if r['attack']=='clean-0'}
    lines += ['',f"The new benchmark clean baseline has risk {summary['fusion']['contamination_series'][0]['points'][0]['risk']}; near-duplicate detection flags {clean_rows['near_duplicate']['fp']}/300 independently generated images and contributor aggregation flags {clean_rows['contributor_aggregation']['fp']}/5 benign contributors. The original trusted demo control still ACCEPTs; it is a different, easier fixture. Do not present that control as proof that the new clean benchmark passes.",
              '',f"Held-out backdoor confusion counts: {backdoor['metrics']['tp']} TP, {backdoor['metrics']['fp']} FP, {backdoor['metrics']['tn']} TN, {backdoor['metrics']['fn']} FN. At least one high-ASR poisoned model can be missed; the clean-model false-positive denominator is only three models.",
              '', 'Embedding-only drift remains largely insensitive to blur/dimming. The separate acquisition-statistics finding records the new operational check. Existing embedding thresholds were not lowered. See the fusion mechanics JSON for actual before/after evidence-addition risk; poisoning-rate order can still differ when the underlying evidence changes.']
    lines+=['', 'Full underlying findings, source attribution, signatures and verification reasons are retained in end_to_end_evidence.json, malicious_contributor.json and evidence-*.json. Failed expectations are measurements, not overwritten outcomes. Benign drift findings describe changed distributions without proving malicious intent.',
            '', '## Runtime and environment','',f"Total experiment wall time: {runtime['total_experiment_seconds']:.3f}s; model robustness: {runtime['model_integrity_seconds']:.3f}s. Per-scan ingestion/hashing, features, detectors, shift and dataset bytes are in runtime.json. Actual CPU/OS/library versions are in environment.json. No hardware-generalization claim.",
            '', '## Judge-facing metrics','']
    for m in summary['judge_metrics']: lines.append(f"- {m['metric']}: {fmt(m['value'])}"+(f" / {m['denominator']}" if m['metric'].endswith('rejection') else '')+f". Scope: {m['scope']}.")
    lines+=['','## Limitations','']+['- '+s for s in summary['limitations']]+['','## Reproduction commands','','From the repository root, with existing local dependencies:','', '```powershell','python -m unittest discover -s tests -v','python -m experiments.final_validation --output experiments/results/final_validation','python scripts/validate_checkpoint.py --help','```','', 'No packages, images or checkpoints are downloaded. Preserve the existing results by choosing a different output directory for comparison runs. Seeds reproduce image content and attack selections; timing, UUID finding IDs and signed record timestamps vary. PyTorch determinism is scoped to this CPU/software environment. Browser regression details are recorded separately in verification.json after the local UI test.']
    (output/'VALIDATION_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,default=Path('experiments/results/final_validation')); parser.add_argument('--seed',type=int,default=26228)
    args=parser.parse_args(); run(args.output,args.seed)
