"""Cryptographic and behavioral identity with explicit access reporting."""
from datetime import datetime, timezone
import numpy as np
from core import VERSION
from core.schemas import Finding
from provenance.hashing import digest


def inspect_model(adapter, expected=None, probes=None, reference=None, registered=None):
    metadata={'sha256':adapter.identity,'size':adapter.path.stat().st_size,'format':adapter.format,'access':adapter.access,'scanner_version':VERSION,'timestamp':datetime.now(timezone.utc).isoformat(),'runtime_available':adapter.runtime is not None,'reason':adapter.reason,'architecture':str(type(adapter.runtime).__name__) if adapter.runtime else None,'parameter_count':sum(p.numel() for p in adapter.get_parameters()) if adapter.supports_gradients() else None}
    if isinstance(expected,str): expected=expected.strip().lower() or None
    substituted=registered is not None and registered!=adapter.identity
    changed=substituted or (expected is not None and expected!=adapter.identity)
    if substituted: reason='Registered model was substituted'
    elif changed: reason='Model differs from trusted digest'
    else:
        reason='Model bytes fingerprinted'+('; registered digest matches' if registered is not None else '')
        reason+='; no trusted baseline supplied' if expected is None else '; trusted digest matches'
    findings=[Finding('model_hash','MODEL_INTEGRITY','MODEL_SUBSTITUTION',adapter.identity,100 if changed else 0,1,reason,{'expected':expected,'registered':registered,'actual':adapter.identity},asset_type='MODEL').to_dict()]
    behavior=None
    if adapter.runtime is not None and probes is not None:
        try:
            output=adapter.predict(probes)
            if output.ndim!=2: raise ValueError('Behavioral summary requires N x classes output')
            exp=np.exp(output-output.max(axis=1,keepdims=True)); probabilities=exp/exp.sum(axis=1,keepdims=True)
            behavior={'probe_hash':digest(probes.tolist()),'output':output.tolist(),'top_prediction':output.argmax(axis=1).tolist(),'softmax_confidence':probabilities.max(axis=1).tolist(),'interpretation':'Softmax over supplied outputs; meaningful as probabilities only if outputs are logits','fingerprint':digest({'probe':digest(probes.tolist()),'output':output.tolist()})}
            distance=None
            if reference:
                if reference['probe_hash']!=behavior['probe_hash']: raise ValueError('Reference probe battery differs')
                old=np.array(reference['output'])
                if old.shape!=output.shape: raise ValueError('Reference output shape differs')
                distance=float(np.max(np.abs(old-output)))
            findings.append(Finding('behavioral_probe','MODEL_INTEGRITY','BEHAVIOR_CHANGE',adapter.identity,90 if distance is not None and distance>1e-5 else 0,.8,'Fixed local probe battery executed',{'max_absolute_change':distance,'behavior':behavior},asset_type='MODEL',limitations=['Finite probes cannot establish absence of a backdoor.']).to_dict())
        except Exception as exc:
            findings.append(Finding('behavioral_probe','MODEL_INTEGRITY','BEHAVIOR_CHANGE',adapter.identity,0,0,str(exc),{},status='FAILED',asset_type='MODEL').to_dict())
    else:
        findings.append(Finding('behavioral_probe','MODEL_INTEGRITY','BEHAVIOR_CHANGE',adapter.identity,0,0,adapter.reason or 'No probe battery supplied',{},status='UNAVAILABLE',asset_type='MODEL').to_dict())
    return {'metadata':metadata,'behavior':behavior,'findings':findings}
