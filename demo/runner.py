"""Executable judge demonstration with measured outcomes and explicit limitations."""
import copy
import json
import time
from pathlib import Path
import numpy as np
from attack_simulator.datasets import generate
from attack_simulator.models import create_models
from adapters.models.runtime import ModelAdapter
from app.services.scanner import scan_dataset
from provenance.inference_record import infer
from provenance.ledger import Ledger,verify_record,verify_ledger
from reports.generator import save


def evaluate(report,truth):
    metrics=[]; universe={a['asset_id'] for a in report['manifest']['assets']}
    for detector in ['exact_duplicate','label_anomaly','ood']:
        actual={a['asset_id'] for a in truth['attacks'] if a['attack']==detector}
        predicted=set()
        for f in report['findings']:
            if f['detector']==detector and f['risk_score']>20:
                predicted.update(f['evidence'].get('members',[f['asset_id']]))
        tp=len(actual&predicted); fp=len(predicted-actual); fn=len(actual-predicted); tn=len(universe-actual-predicted)
        precision=tp/(tp+fp) if tp+fp else 0; recall=tp/(tp+fn) if tp+fn else 0
        metrics.append({'detector':detector,'tp':tp,'fp':fp,'fn':fn,'tn':tn,'precision':precision,'recall':recall,'f1':2*precision*recall/(precision+recall) if precision+recall else 0,'false_positive_rate':fp/(fp+tn) if fp+tn else 0,'scope':'Seeded synthetic fixtures only; duplicate originals count as negatives; trigger images may cause cross-detector positives'})
    return metrics


def run_demo(directory: Path, ledger=None, progress=None):
    start=time.perf_counter(); directory=Path(directory); directory.mkdir(parents=True,exist_ok=False)
    generate(directory/'clean'); truth=generate(directory/'attacked',attack='combined')
    clean_model,bad_model=create_models(directory/'models')
    ledger=ledger or Ledger(directory/'provenance')
    model={'path':str(clean_model),'format':'torchscript','trusted':True,'reconstruct':True,'steps':20}
    clean=scan_dataset(directory/'clean',reference=directory/'clean',model=model,ledger=ledger,progress=progress)
    model.update(path=str(bad_model),expected_hash=clean['model']['metadata']['sha256'],reference_behavior=clean['model']['behavior'])
    attacked=scan_dataset(directory/'attacked',reference=directory/'clean',model=model,ledger=ledger,progress=progress)
    adapter=ModelAdapter(str(clean_model),'torchscript',trusted=True)
    record=infer(adapter,directory/'clean/red/00.png',ledger)
    tampered=copy.deepcopy(record); tampered['payload']['output'][0][0]+=1
    original=ledger.records(); modified=copy.deepcopy(original); modified[0]['payload']['modified']=True
    verification={'valid_inference':verify_record(record,ledger.public),'tampered_inference':verify_record(tampered,ledger.public),'first_acceptance':ledger.accept(record),'replay':ledger.accept(record),'ledger':verify_ledger(original,ledger.public),'tampered_ledger':verify_ledger(modified,ledger.public),'model_substitution':next(f for f in attacked['findings'] if f['detector']=='model_hash'),'metrics':evaluate(attacked,truth),'runtime_seconds':round(time.perf_counter()-start,4),'seed':26228,'limitations':['Synthetic color dataset and deterministic demonstration models, not trained benchmark models.','Reconstruction is measured but is not guaranteed to flag every injected trigger.']}
    from experiments.hardening import backdoor_experiment
    validation=backdoor_experiment(directory/'backdoor_validation')
    compromised=validation['records']['backdoored']; evidence=compromised['reconstruction']['evidence']
    recovered=next((o for o in evidence['outcomes'] if o['target']==evidence['target']),{})
    verification['backdoor_validation']={'measurement':compromised['measurement'],'target':evidence['target'],'recovered_mask_norm':recovered.get('mask_norm'),'recovered_success':recovered.get('success'),'median':evidence['median'],'mad':evidence['mad'],'anomaly_index':evidence['anomaly_index'],'metrics':validation['metrics'],'full_evidence':'backdoor_validation/backdoor_results.json'}
    verification['runtime_seconds']=round(time.perf_counter()-start,4)
    save(clean,directory/'reports'); save(attacked,directory/'reports')
    (directory/'evaluation.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
    return {'clean':clean,'attacked':attacked,'verification':verification}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument('--output',default='demo/results'); args=parser.parse_args()
    result=run_demo(Path(args.output))
    print(json.dumps({'clean':result['clean']['assurance'],'attacked':result['attacked']['assurance'],'verification':{k:v for k,v in result['verification'].items() if k!='model_substitution'}},indent=2))
