"""Offline orchestration; detector failures become visible findings."""
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import numpy as np
from adapters.datasets.ingestion import ingest
from adapters.models.runtime import ModelAdapter
from core.config import Config
from core.schemas import Finding
from core.risk import fuse
from core.correlation import correlate
from core.coverage import COVERAGE
from core import VERSION
from detectors.data_integrity.features import VisualEncoder
from detectors.data_integrity.encoder import CachedEncoder,FeatureEncoder
from detectors.data_integrity.resnet_encoder import select_encoder
from detectors.data_integrity.spectral import spectral_signatures
from detectors.data_integrity.annotations import annotation_integrity
from detectors.data_integrity.trigger_pattern import detect_patterns
from detectors.data_integrity.engine import duplicates, labels, ood, contributors
from detectors.distribution_shift.embedding_shift import compare
from detectors.model_integrity.fingerprint import inspect_model
from detectors.model_integrity.neural_cleanse import reconstruct
from detectors.model_integrity.patch_probe import probe_patches
from detectors.model_integrity.activation_analysis import analyze_activations
from adapters.models.preprocessing import image_batch,confidences
from provenance.ledger import verify_ledger
from core.decision import contract
from detectors.distribution_shift.acquisition import compare_acquisition
from detectors.model_integrity.decision import assess

log = logging.getLogger(__name__)


def scan_dataset(root, format='folder', config=None, reference=None, model=None, ledger=None, progress=None, encoder=None, cache_dir=None):
    config=config or Config(); root=Path(root).resolve(); findings=[]; timings={}
    if encoder is None:
        encoder,encoder_status=select_encoder(config.encoder_weights,config.encoder_batch_size)
    else:
        encoder_status=encoder.capability() if isinstance(encoder,FeatureEncoder) else {'status':'CUSTOM','encoder_id':encoder.name,'semantic':'operator-defined'}
    if isinstance(encoder,FeatureEncoder):
        cache_dir=Path(cache_dir) if cache_dir else (ledger.directory.parent if ledger else Path(__file__).resolve().parents[2]/'local_state')/'embedding_cache'
        encoder=CachedEncoder(encoder,cache_dir)
    def stage(name):
        log.info('Scan stage %s',name)
        if progress: progress(name)
    stage('HASHING'); manifest=ingest(root,format,config)
    if not manifest['assets']: raise ValueError('No valid images remain after validation')
    stage('EXTRACTING_FEATURES')
    assets=manifest['assets']
    try: features=encoder.encode([root/a['asset_id'] for a in assets])
    except Exception as exc:
        findings.append(Finding('feature_encoder','DATA_INTEGRITY','ENCODER_FAILURE','dataset',0,0,str(exc),{},status='FAILED').to_dict())
        encoder=VisualEncoder(); encoder_status=dict(encoder.capability(),status='FALLBACK',reason='Configured encoder failed; using local handcrafted features')
        features=encoder.encode([root/a['asset_id'] for a in assets])
    ref_features=None; reference_hash=None
    if reference:
        try:
            ref_root=Path(reference); ref=ingest(ref_root,format,config)
            if not ref['assets']: raise ValueError('Reference contains no valid images')
            reference_hash=ref['manifest_hash']; ref_features=encoder.encode([ref_root/a['asset_id'] for a in ref['assets']])
        except Exception as exc:
            findings.append(Finding('reference_ingestion','DATA_INTEGRITY','REFERENCE_FAILURE','dataset',0,0,str(exc),{},status='FAILED').to_dict())
            reference=None; reference_hash=None; ref_features=None
    stage('SCANNING_DATA')
    for name,fn in [('duplicates',lambda:duplicates(assets,root,features,config)),('label_anomaly',lambda:labels(assets,features,config)),('ood',lambda:ood(assets,features,config,ref_features)),('spectral_signature',lambda:spectral_signatures(assets,features,config.spectral_min_samples,config.spectral_directions,config.spectral_threshold,config.spectral_percentile,config.spectral_min_energy)),('trigger_pattern',lambda:detect_patterns(assets,root)),('annotation_integrity',lambda:annotation_integrity(manifest,config.annotation_min_area,config.annotation_max_area,config.annotation_max_boxes))]:
        start=time.perf_counter()
        try: findings.extend(fn())
        except Exception as exc:
            log.exception('Detector %s failed',name)
            findings.append(Finding(name,'DATA_INTEGRITY',name.upper(),'dataset',0,0,str(exc),{},status='FAILED').to_dict())
        finally: timings[name]=time.perf_counter()-start
    for error in manifest['errors']:
        findings.append(Finding('ingestion','DATA_INTEGRITY','MALFORMED_ASSET',error['asset_id'],70,1,error['error'],{}).to_dict())
    model_result=None; ref_confidence=current_confidence=None
    stage('SCANNING_MODEL')
    if model:
        try:
            adapter=ModelAdapter(model['path'],model.get('format','torchscript'),trusted=model.get('trusted',False))
            probes=np.random.default_rng(config.seed).random((6,3,32,32),dtype=np.float32)
            probes[0]=1; probes[1]=0
            model_result=inspect_model(adapter,expected=model.get('expected_hash'),probes=probes,reference=model.get('reference_behavior'))
            findings.extend(model_result['findings'])
            if reference and adapter.runtime is not None:
                try:
                    current_confidence=confidences(adapter,image_batch(root,assets))
                    ref_confidence=confidences(adapter,image_batch(Path(reference),ref['assets']))
                except Exception as exc:
                    findings.append(Finding('prediction_confidence','DISTRIBUTION','CONFIDENCE_SHIFT',adapter.identity,0,0,str(exc),{},status='UNAVAILABLE',asset_type='MODEL').to_dict())
            if model.get('reconstruct'):
                source_assets=ref['assets'] if reference else assets
                source_root=Path(reference) if reference else root
                clean_probes=image_batch(source_root,source_assets)
                start=time.perf_counter()
                finding=reconstruct(adapter,clean_probes,steps=model.get('steps',120),seed=config.seed)
                timings['neural_cleanse']=time.perf_counter()-start
                finding['evidence']['source_assumption']='Trusted reference' if reference else 'Scanned data may be contaminated; supply a clean reference'
                target=finding['evidence'].get('target'); class_names=model.get('class_names')
                if target is not None and isinstance(class_names,list) and target<len(class_names):
                    finding['evidence']['target_label']=str(class_names[target])
                    finding['evidence']['class_mapping_source']='Operator-supplied model class_names'
                findings.append(finding)
                patch=probe_patches(adapter,clean_probes); findings.append(patch)
                finding['evidence']['backdoor_assessment']=assess(finding,patch)
                finding['recommended_action']=finding['evidence']['backdoor_assessment']['recommended_action']
            else:
                findings.append(Finding('neural_cleanse','MODEL_INTEGRITY','BACKDOOR',adapter.identity,0,0,'Optional research reconstruction not requested',{},status='UNAVAILABLE',asset_type='MODEL').to_dict())
            if model.get('activation_analysis'):
                findings.extend(analyze_activations(adapter,image_batch(root,assets),assets[:96]))
        except Exception as exc:
            findings.append(Finding('model_scan','MODEL_INTEGRITY','MODEL_INTEGRITY','model',0,0,str(exc),{},status='FAILED',asset_type='MODEL').to_dict())
    else:
        findings.append(Finding('model_scan','MODEL_INTEGRITY','MODEL_INTEGRITY','model',0,0,'No model supplied; model behavior unassessed',{},status='UNAVAILABLE',asset_type='MODEL').to_dict())
    stage('ASSESSING_SHIFT')
    thresholds={'centroid_l2':config.shift_centroid_threshold,'covariance_frobenius':config.shift_covariance_threshold,'mmd_squared':config.shift_mmd_threshold,'class_frequency_tv':config.shift_class_threshold,'confidence_mean_delta':config.shift_confidence_threshold}
    start=time.perf_counter()
    try: findings.append(compare(ref_features,features,[a['labels'] for a in ref['assets']] if reference else None,[a['labels'] for a in assets],ref_confidence,current_confidence,thresholds))
    except Exception as exc: findings.append(Finding('embedding_shift','DISTRIBUTION','SHIFT','dataset',0,0,str(exc),{},status='FAILED').to_dict())
    timings['embedding_shift']=time.perf_counter()-start
    start=time.perf_counter()
    try: findings.append(compare_acquisition([Path(reference)/a['asset_id'] for a in ref['assets']] if reference else None,[root/a['asset_id'] for a in assets]))
    except Exception as exc: findings.append(Finding('acquisition_shift','DISTRIBUTION','OPERATIONAL_SHIFT','dataset',0,0,str(exc),{},status='FAILED').to_dict())
    timings['acquisition_shift']=time.perf_counter()-start
    try: ledger_check=verify_ledger(ledger.records(),ledger.public) if ledger else {'status':'UNAVAILABLE'}
    except Exception as exc: ledger_check={'status':'FAILED','reason':str(exc)}
    violation=ledger_check['status'] in {'TAMPERED','SIGNATURE_INVALID','SEQUENCE_ERROR'}
    findings.append(Finding('ledger_verification','INFERENCE_INTEGRITY','AUDIT_TAMPERING','ledger',100 if violation else 0,1 if ledger else 0,'Local audit verification result' if ledger else 'No ledger provided',ledger_check,status='FAILED' if ledger_check['status']=='FAILED' else 'SUCCESS' if ledger else 'UNAVAILABLE',asset_type='LEDGER').to_dict())
    stage('GENERATING_REPORT')
    if ingest(root,format,config)['manifest_hash']!=manifest['manifest_hash']:
        raise ValueError('Dataset changed during scan; retry with immutable input assets')
    if reference and ingest(Path(reference),format,config)['manifest_hash']!=reference_hash:
        raise ValueError('Reference changed during scan; retry with immutable reference assets')
    centered=features-features.mean(0)
    try: _,_,vh=np.linalg.svd(centered,full_matrices=False)
    except Exception as exc:
        vh=np.zeros((2,features.shape[1])); findings.append(Finding('projection','DATA_INTEGRITY','VISUALIZATION','dataset',0,0,str(exc),{},status='FAILED').to_dict())
    composite=fuse(findings,config); contributor_rows=contributors(assets,findings); decision=contract(findings,composite,contributor_rows,ledger_check)
    report={'scan_id':str(uuid4()),'timestamp':datetime.now(timezone.utc).isoformat(),'scanner_version':VERSION,'config':config.to_dict(),'manifest':manifest,'reference_manifest_hash':reference_hash,'encoder':encoder.name,'findings':findings,'assurance':composite,'contributors':contributor_rows,'correlations':correlate(findings,assets),'model':model_result,'ledger_verification':ledger_check,'coverage':COVERAGE,'projection':(centered@vh[:2].T).tolist(),'limitations':encoder.limitations+['Scores and confidence are heuristic, not calibrated probabilities.','Negative findings do not prove absence of attacks.','Object annotations are preserved; label-neighbor analysis uses singly labeled whole images.','No external benchmark metrics are claimed.'],**decision}
    report['encoder_capability']=dict(encoder_status,cache={'hits':encoder.hits,'misses':encoder.misses} if isinstance(encoder,CachedEncoder) else None)
    report['detector_runtime_seconds']=timings
    if ledger and ledger_check['status']=='VALID':
        from provenance.hashing import digest
        try: report['audit_entry']=ledger.append('scan',{'scan_id':report['scan_id'],'report_hash':digest(report),'manifest_hash':manifest['manifest_hash']})
        except Exception as exc:
            report['audit_append']={'status':'FAILED','reason':str(exc)}
            findings.append(Finding('audit_append','INFERENCE_INTEGRITY','AUDIT_WRITE','ledger',0,0,str(exc),{},status='FAILED',asset_type='LEDGER').to_dict())
            report['assurance']=fuse(findings,config)
    elif ledger:
        report['audit_append']={'status':'FAILED','reason':'Invalid historical chain; report preserved without appending to compromised ledger'}
    return report
