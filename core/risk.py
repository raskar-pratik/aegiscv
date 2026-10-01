"""Transparent heuristic fusion with coverage-aware confidence."""
from core.config import Config
from core.schemas import severity
from core.quality import quality


def fuse(findings: list[dict], config: Config | None = None) -> dict:
    config = config or Config()
    valid = [f for f in findings if f['status'] == 'SUCCESS']
    categories = {c: max((f['risk_score']*quality(f)['risk_weight'] for f in valid if f['category'] == c), default=0) for c in ['DATA_INTEGRITY','MODEL_INTEGRITY','INFERENCE_INTEGRITY','DISTRIBUTION']}
    score = round(sum(s*w for s,w in zip(categories.values(),config.risk_weights))/sum(config.risk_weights),2)
    if any(f['detector'] in {'model_hash','ledger_verification'} and f['risk_score']==100 for f in valid):
        score=100
    detector_names={f['detector'] for f in findings}
    successful={name for name in detector_names if all(f['status']=='SUCCESS' for f in findings if f['detector']==name)}
    coverage = len(successful)/len(detector_names) if detector_names else 0
    detector_confidence=[min(f['confidence'] for f in valid if f['detector']==name) for name in successful]
    confidence = round(coverage * (sum(detector_confidence)/len(detector_confidence) if detector_confidence else 0), 3)
    review_evidence=any(f['risk_score']>20 and (f.get('recommended_action')=='REVIEW' or quality(f)['status'] in {'EXPERIMENTAL','VALIDATED_EXPERIMENTAL'}) for f in valid)
    action = 'QUARANTINE' if score > config.quarantine_threshold else 'REVIEW' if score > config.review_threshold or coverage < 1 or review_evidence else 'ACCEPT'
    return {'risk_score':score,'assurance_score':100-score,'severity':severity(score),'recommended_action':action,'confidence':confidence,'coverage_fraction':coverage,'category_risk':categories,'category_weights':dict(zip(categories,config.risk_weights)),'score_type':'heuristic composite; not a calibrated probability','method':'Fixed-denominator weighted sum of reliability-adjusted category maxima (weights 1,1.2,1.2,1 by default; denominator 4.4). Verified model/ledger violations force risk 100. Unavailable checks only change confidence/coverage. Experimental evidence remains visible and may require REVIEW.'}
