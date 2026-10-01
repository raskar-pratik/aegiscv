"""Offline reproducible hardening measurements; missing metrics remain null."""
import argparse
import csv
import json
import tempfile
import time
from pathlib import Path
import numpy as np
from PIL import Image
from adapters.datasets.ingestion import ingest
from attack_simulator.datasets import generate
from attack_simulator.annotations import generate_annotations
from attack_simulator.backdoor_validation import create_adapter,samples,measure
from core.config import Config
from detectors.data_integrity.resnet_encoder import select_encoder
from detectors.data_integrity.engine import duplicates,labels,ood
from detectors.data_integrity.spectral import spectral_signatures
from detectors.data_integrity.trigger_pattern import detect_patterns
from detectors.data_integrity.annotations import annotation_integrity
from detectors.model_integrity.neural_cleanse import reconstruct
from detectors.model_integrity.patch_probe import probe_patches
from detectors.model_integrity.activation_analysis import cluster_representations
from detectors.distribution_shift.embedding_shift import compare
from provenance.hashing import digest


def metrics(detector,attack,universe,actual,predicted,runtime,unit='image'):
    universe=set(universe); actual=set(actual); predicted=set(predicted)&universe
    tp=len(actual&predicted); fp=len(predicted-actual); tn=len(universe-actual-predicted); fn=len(actual-predicted)
    precision=tp/(tp+fp) if tp+fp else None; recall=tp/(tp+fn) if tp+fn else None
    f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None
    return {'detector':detector,'attack':attack,'unit':unit,'clean_samples':len(universe-actual),'attack_samples':len(actual),'tp':tp,'fp':fp,'tn':tn,'fn':fn,'precision':precision,'recall':recall,'f1':f1,'fpr':fp/(fp+tn) if fp+tn else None,'runtime_seconds':runtime}


def flagged(findings):
    result=set()
    for finding in findings:
        if finding['status']=='SUCCESS' and finding['risk_score']>20:
            result.update(finding['evidence'].get('members',[finding['asset_id']]))
    return result


def backdoor_experiment(output: Path,seed=26228,steps=140):
    output.mkdir(parents=True,exist_ok=True); x,y=samples(seed,per_class=6)
    records={}; predictions={}; runtimes={}
    for kind,backdoor in [('clean',False),('backdoored',True)]:
        adapter=create_adapter(output/kind,backdoor); measurement=measure(adapter,x,y)
        start=time.perf_counter(); result=reconstruct(adapter,x,labels=y,steps=steps,seed=seed)
        elapsed=time.perf_counter()-start; patch_start=time.perf_counter(); patch=probe_patches(adapter,x,patch_size=4)
        records[kind]={'model_hash':adapter.identity,'measurement':measurement,'reconstruction':result,'patch_probe':patch,'runtime_seconds':elapsed}
        predictions[kind]=result['risk_score']>20; runtimes[kind]=elapsed
        records[kind]['patch_runtime_seconds']=time.perf_counter()-patch_start
        for outcome in result['evidence'].get('outcomes',[]):
            if 'mask' not in outcome: continue
            mask=np.asarray(outcome['mask']); pattern=np.asarray(outcome['pattern'])
            Image.fromarray(np.uint8(np.clip(mask,0,1)*255)).save(output/kind/f'target-{outcome["target"]}-mask.png')
            Image.fromarray(np.uint8(np.clip(pattern,0,1)*255)).save(output/kind/f'target-{outcome["target"]}-pattern.png')
    rows=[metrics('neural_cleanse','Differentiable patch backdoor',['clean','backdoored'],['backdoored'],[k for k,v in predictions.items() if v],sum(runtimes.values()),'model'),
          metrics('patch_probe','Differentiable patch backdoor',['clean','backdoored'],['backdoored'],[k for k,v in records.items() if v['patch_probe']['risk_score']>20],sum(v['patch_runtime_seconds'] for v in records.values()),'model')]
    artifact={'seed':seed,'steps':steps,'records':records,'metrics':rows,'limitations':['One controlled model mechanism and six synthetic classes; not a benchmark of general backdoor detection.','Clean accuracy uses synthetic ground-truth classes. ASR excludes samples already in attacker target class.']}
    (output/'backdoor_results.json').write_text(json.dumps(artifact,indent=2,allow_nan=False),encoding='utf-8')
    return artifact


def run(output: Path,weights=None,seed=26228):
    output.mkdir(parents=True,exist_ok=True); rows=[]; details={}; config=Config(seed=seed)
    encoder,capability=select_encoder(weights)
    scratch=Path(__file__).resolve().parents[3]/'work'; scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch,prefix='hardening-') as temp:
        root=Path(temp); generate(root/'clean',seed)
        clean=ingest(root/'clean')['assets']; cf=encoder.encode([root/'clean'/a['asset_id'] for a in clean])
        for scenario in ['label_flip','duplicate_flood','ood','trigger']:
            truth=generate(root/scenario,seed,scenario); assets=ingest(root/scenario)['assets']
            features=encoder.encode([root/scenario/a['asset_id'] for a in assets])
            analyses=[]
            if scenario=='label_flip': analyses.append(('label_anomaly',lambda a,x,p:labels(a,x,config)))
            if scenario=='duplicate_flood': analyses.append(('exact_duplicate',lambda a,x,p:[f for f in duplicates(a,p,x,config) if f['detector']=='exact_duplicate']))
            if scenario=='ood': analyses.append(('ood',lambda a,x,p:ood(a,x,config,cf)))
            if scenario=='trigger': analyses.append(('trigger_pattern',lambda a,x,p:detect_patterns(a,p)))
            if scenario in {'label_flip','trigger'}: analyses.append(('spectral_signature',lambda a,x,p:spectral_signatures(a,x)))
            actual={'attacked/'+a['asset_id'] for a in truth['attacks']}
            universe={'clean/'+a['asset_id'] for a in clean}|{'attacked/'+a['asset_id'] for a in assets}
            for name,fn in analyses:
                start=time.perf_counter(); normal=fn(clean,cf,root/'clean'); altered=fn(assets,features,root/scenario)
                duration=time.perf_counter()-start
                predicted={'clean/'+p for p in flagged(normal)}|{'attacked/'+p for p in flagged(altered)}
                rows.append(metrics(name,scenario,universe,actual,predicted,duration))
                details[name+':'+scenario]={'clean_findings':normal,'attack_findings':altered}
        rng=np.random.default_rng(seed); baseline=rng.normal(0,.03,(100,12)); contaminated=baseline.copy(); contaminated[-5:,0]+=3
        assets=[{'asset_id':str(i),'labels':['class'],'contributor':'B' if i>=95 else 'A'} for i in range(100)]
        for name,fn in [('spectral_signature',spectral_signatures),('activation_clustering',cluster_representations)]:
            start=time.perf_counter(); findings=fn(assets,contaminated); clean_findings=fn(assets,baseline)
            universe={'clean/'+str(i) for i in range(100)}|{'attacked/'+str(i) for i in range(100)}
            predicted={'clean/'+p for p in flagged(clean_findings)}|{'attacked/'+p for p in flagged(findings)}
            rows.append(metrics(name,'Controlled vector subpopulation',universe,{'attacked/'+str(i) for i in range(95,100)},predicted,time.perf_counter()-start,'representation'))
        start=time.perf_counter(); normal=compare(baseline,baseline); shifted=compare(baseline,baseline+1)
        rows.append(metrics('embedding_shift','Global embedding shift',['clean','shifted'],['shifted'],[k for k,f in [('clean',normal),('shifted',shifted)] if f['risk_score']>20],time.perf_counter()-start,'dataset'))
        for format in ['coco','yolo']:
            generate_annotations(root/(format+'-clean'),format,False,seed)
            truth=generate_annotations(root/(format+'-bad'),format,True,seed)
            clean_manifest=ingest(root/(format+'-clean'),format); bad_manifest=ingest(root/(format+'-bad'),format)
            start=time.perf_counter(); normal=annotation_integrity(clean_manifest); altered=annotation_integrity(bad_manifest)
            predicted={'clean/'+p for p in flagged(normal)}|{'attacked/'+p for p in flagged(altered)}
            universe={'clean/'+a['asset_id'] for a in clean_manifest['assets']}|{'attacked/'+a['asset_id'] for a in bad_manifest['assets']}
            rows.append(metrics('annotation_integrity',format+' out-of-bounds boxes',universe,{'attacked/'+p for p in truth},predicted,time.perf_counter()-start))
    backdoor=backdoor_experiment(output/'backdoor_validation',seed)
    rows.extend(backdoor['metrics'])
    artifact={'seed':seed,'encoder':capability,'config':config.to_dict(),'rows':rows,'details':details,'backdoor_results':'backdoor_validation/backdoor_results.json','limitations':['All measurements use synthetic controlled data, not external validation.','Pretrained semantic performance is unmeasured when local weights are absent.','Original duplicate-group members count as negatives under injection-only ground truth.','Runtime measures detector calls including clean and attacked cases; embedding extraction is excluded from tabulated detector runtime.','Vector-subpopulation results are mechanics checks, separate from image-poisoning performance.']}
    artifact['experiment_hash']=digest(artifact)
    (output/'comparison.json').write_text(json.dumps(artifact,indent=2,allow_nan=False),encoding='utf-8')
    with (output/'comparison.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    columns=list(rows[0]); lines=['# Measured hardening experiments','',f'Seed: {seed}. Encoder: {capability["encoder_id"]} ({capability["status"]}).','', '| '+' | '.join(columns)+' |','| '+' | '.join(['---']*len(columns))+' |']
    for row in rows: lines.append('| '+' | '.join('N/A' if row[k] is None else f'{row[k]:.4f}' if isinstance(row[k],float) else str(row[k]) for k in columns)+' |')
    lines+=['']+artifact['limitations']; (output/'comparison.md').write_text('\n'.join(lines),encoding='utf-8')
    return artifact


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,default=Path('experiments/results/hardening')); parser.add_argument('--weights',type=Path); parser.add_argument('--seed',type=int,default=26228)
    args=parser.parse_args(); result=run(args.output,args.weights,args.seed)
    print(json.dumps({'encoder':result['encoder'],'rows':result['rows']},indent=2))
