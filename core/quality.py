"""Conservative evidence policy; weights are design choices, not fitted probabilities."""
WEIGHTS={'VERIFIED_MECHANICAL':1.,'CALIBRATED':1.,'HEURISTIC':.6,'VALIDATED_EXPERIMENTAL':.35,'EXPERIMENTAL':.2,'UNAVAILABLE':0.}

def quality(finding):
    name=finding['detector']; state='HEURISTIC'; reason='Uncalibrated heuristic; requires analyst interpretation'; fpr=None
    if finding['status']!='SUCCESS': state='UNAVAILABLE'
    elif name in {'exact_duplicate','model_hash','ledger_verification','signature_verification'}: state='VERIFIED_MECHANICAL'; reason='Deterministic byte/signature/chain verification, within its stated trust boundary'
    elif name=='near_duplicate':
        from detectors.data_integrity.near_confirmation import profile
        try:
            p=profile(); state='CALIBRATED' if p['qualified'] else 'EXPERIMENTAL'; fpr=p.get('image_fpr'); reason=p.get('scope','No qualifying frozen profile')
            import json
            from pathlib import Path
            gate_path=Path(__file__).parent/'calibration/quality_gate.json'
            if gate_path.exists():
                gate=json.loads(gate_path.read_text())
                if gate['profile_hash']==p['profile_hash'] and not gate['eligible']:
                    state='EXPERIMENTAL'; fpr=gate['heldout_image_fpr']; reason='Measured held-out false-positive gate failed; escalation disabled'
        except Exception: state='EXPERIMENTAL'; reason='Calibration profile unavailable or invalid'
    elif name=='acquisition_shift': state='CALIBRATED' if finding['evidence'].get('profile_hash') else 'EXPERIMENTAL'; reason='Reference/calibration acquisition controls only'
    elif name in {'label_anomaly','ood'} and finding.get('calibration_profile_hash'): state='CALIBRATED'; reason='Explicit frozen encoder-bound calibration profile'
    elif name=='neural_cleanse': state='VALIDATED_EXPERIMENTAL'; reason='Prior held-out models: TP5 FP1 TN2 FN1; single inversion anomaly is not a backdoor verdict'; fpr=1/3
    elif name in {'spectral_signature','activation_clustering'}: state='EXPERIMENTAL'; reason='Limited synthetic sensitivity; no validated deployment operating point'
    weight=WEIGHTS[state]
    if name=='near_duplicate' and state=='EXPERIMENTAL': weight=0.
    family='representation' if name in {'label_anomaly','ood','spectral_signature','activation_clustering'} else 'duplication' if name in {'exact_duplicate','near_duplicate'} else name
    return {'status':state,'risk_weight':weight,'measured_fpr':fpr,'reason':reason,'evidence_family':family,'weight_type':'Fixed conservative policy, not learned reliability probability'}

def annotate(finding):
    finding['quality']=quality(finding)
    if finding['risk_score']>20 and (finding['quality']['status'] in {'EXPERIMENTAL','VALIDATED_EXPERIMENTAL'} or finding['detector']=='acquisition_shift'):
        finding['recommended_action']='REVIEW'
    return finding
