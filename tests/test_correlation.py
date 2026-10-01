import unittest
from core.schemas import Finding
from core.correlation import correlate_findings


class CorrelationTests(unittest.TestCase):
    def test_explicit_rules_and_links(self):
        def f(det,asset='x',e=None,score=80):
            return Finding(det,'DATA_INTEGRITY','TEST',asset,score,.7,'Evidence',e or {}).to_dict()
        assets=[{'asset_id':x,'contributor':'B'} for x in ['x','y','z']]
        findings=[f('spectral_signature'),f('label_anomaly'),f('ood','x'),f('ood','y'),f('embedding_shift','dataset'),f('trigger_pattern',e={'target_label':'cat'}),f('neural_cleanse','m',{'target_label':'cat'}),f('model_hash','m',{'actual':'a','expected':'b'}),f('behavioral_probe','m')]
        result=correlate_findings(findings,assets); rules={r['evidence']['rule'] for r in result}
        for rule in ['source_spectral_label','source_ood_shift','matched_trigger_target','substitution_hash_behavior']: self.assertIn(rule,rules)
        ids={r['finding_id'] for r in findings}
        self.assertTrue(all(set(r['finding_ids'])<=ids for r in result))
        stable=f('model_hash','m',{'actual':'a','expected':'a'},0)
        self.assertIn('unchanged_hash_changed_behavior',{r['evidence']['rule'] for r in correlate_findings([stable,f('behavioral_probe','m')],assets)})
        self.assertFalse(correlate_findings([f('trigger_pattern',e={'target_label':'cat'}),f('neural_cleanse','m',{'target':2})],[]))
