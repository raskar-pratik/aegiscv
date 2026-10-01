"""Central threshold inventory and frozen, scoped calibration profiles."""
from dataclasses import fields
from core.config import Config
from provenance.hashing import digest


EXTRA={'neural_cleanse.anomaly_threshold':2.,'neural_cleanse.success_threshold':.9,
       'neural_cleanse.learning_rate':.15,'neural_cleanse.lambda_l1':.05,'neural_cleanse.steps':120,
       'trigger_pattern.min_support':3,'trigger_pattern.min_association':.8,
       'patch_probe.success':.9,'patch_probe.min_sources':6,
       'activation.separation':4.,'activation.minority_fraction_min':.05,'activation.minority_fraction_max':.3,
       'finding.review_threshold':20,'finding.quarantine_threshold':80,
       'trigger_pattern.max_patch_std':.03,'trigger_pattern.min_contrast':.5,'annotation.dominant_frequency':.9,
       'activation.min_samples':12,'neural_cleanse.restarts':2,'neural_cleanse.validation_fraction':.3,
       'correlation.min_ood_count':2,'correlation.min_source_ood_fraction':.2}


def registry(config=None):
    values=(config or Config()).to_dict()
    names=[name for name in values if name.startswith(('near_','label_','ood_','spectral_','shift_','annotation_')) or name in {'neighbors','risk_weights','review_threshold','quarantine_threshold'}]
    result={name:{'value':value,'status':'UNCALIBRATED_HEURISTIC'} for name,value in {**{n:values[n] for n in names},**EXTRA}.items()}
    from detectors.data_integrity.near_confirmation import profile
    from detectors.distribution_shift.acquisition import PROFILE
    from core.quality import WEIGHTS
    import json
    try:
        p=profile()
        for name,value in p['thresholds'].items(): result['near_confirmation.'+name]={'value':value,'status':'CALIBRATED' if p['qualified'] else 'EXPERIMENTAL','profile_hash':p['profile_hash'],'scope':p.get('scope')}
    except Exception as exc: result['near_confirmation']={'status':'UNAVAILABLE','reason':str(exc)}
    if PROFILE.exists():
        p=json.loads(PROFILE.read_text())
        for name in ['luminance_threshold','sharpness_relative_threshold']: result['acquisition.'+name]={'value':p[name],'status':'CALIBRATED','scope':p['scope'],'profile_hash':p['profile_hash']}
    result['quality_weights']={'value':WEIGHTS,'status':'FIXED_POLICY_NOT_FITTED'}
    return result


def freeze(values,calibration_ids,evaluation_ids,encoder_hash,method):
    if set(calibration_ids)&set(evaluation_ids): raise ValueError('Calibration/evaluation overlap')
    if not calibration_ids: raise ValueError('Calibration sample IDs required')
    if not set(values)<={f.name for f in fields(Config)}: raise ValueError('Unknown configuration threshold')
    Config(**values)
    profile={'values':values,'calibration_ids':sorted(calibration_ids),'reserved_evaluation_ids':sorted(evaluation_ids),
             'encoder_hash':encoder_hash,'method':method,'scope':'Generated benchmark only; not a probability calibration'}
    profile['profile_hash']=digest(profile)
    return profile


def apply_profile(profile,encoder_hash):
    payload={k:v for k,v in profile.items() if k!='profile_hash'}
    if digest(payload)!=profile['profile_hash']: raise ValueError('Calibration profile was altered')
    if encoder_hash!=profile['encoder_hash']: raise ValueError('Calibration encoder mismatch')
    if set(profile['calibration_ids'])&set(profile['reserved_evaluation_ids']): raise ValueError('Partition leakage')
    return Config(**profile['values'])
