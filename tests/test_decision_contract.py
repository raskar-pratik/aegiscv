import unittest
from core.decision import contract
from core.risk import fuse
from core.schemas import Finding

class DecisionContractTests(unittest.TestCase):
    def finding(self,detector,category,risk,asset='dataset',reason='controlled evidence',status='SUCCESS',evidence=None):
        return Finding(detector,category,detector.upper(),asset,risk,.8,reason,evidence or {},status=status).to_dict()

    def test_contributor_override_preserves_composite(self):
        finding=self.finding('exact_duplicate','DATA_INTEGRITY',55,'sample')
        composite=fuse([finding]); self.assertEqual(composite['risk_score'],12.5)
        row={'contributor':'malicious-contributor','risk_score':100,'evidence_families':{'duplication':55,'representation':25,'trigger_pattern':32},'recommended_action':'QUARANTINE'}
        result=contract([finding],composite,[row])
        self.assertEqual(result['composite_risk'],12.5); self.assertEqual(result['max_asset_risk'],100)
        self.assertEqual(result['highest_risk_asset'],'malicious-contributor'); self.assertEqual(result['final_disposition'],'QUARANTINE')
        self.assertEqual(result['disposition_trigger']['type'],'CONTRIBUTOR_RISK')

    def test_clean_remains_low_review(self):
        finding=self.finding('exact_duplicate','DATA_INTEGRITY',50,'sample')
        result=contract([finding],fuse([finding]),[])
        self.assertEqual(result['composite_severity'],'LOW'); self.assertEqual(result['final_disposition'],'REVIEW')

    def test_crypto_model_and_ledger_override(self):
        model=self.finding('model_hash','MODEL_INTEGRITY',100,'model')
        result=contract([model],fuse([model]),[])
        self.assertEqual(result['final_disposition'],'QUARANTINE'); self.assertEqual(result['disposition_trigger']['type'],'CRYPTOGRAPHIC_INTEGRITY')
        ledger=self.finding('ledger_verification','INFERENCE_INTEGRITY',0,'ledger')
        result=contract([ledger],fuse([ledger]),[],{'status':'TAMPERED','sequence':1})
        self.assertEqual(result['final_disposition'],'QUARANTINE')

    def test_experimental_backdoor_is_review_not_confirmed(self):
        finding=self.finding('neural_cleanse','MODEL_INTEGRITY',85,'model',evidence={'backdoor_assessment':{'verdict':'SUSPICIOUS_EVIDENCE'}})
        result=contract([finding],fuse([finding]),[])
        self.assertEqual(result['final_disposition'],'REVIEW'); self.assertEqual(result['disposition_trigger']['type'],'EXPERIMENTAL_BACKDOOR_EVIDENCE'); self.assertNotIn('CONFIRMED',result['disposition_trigger']['reason'])

    def test_positive_evidence_preserves_composite_and_decisive_disposition(self):
        one=self.finding('exact_duplicate','DATA_INTEGRITY',40,'x'); two=self.finding('trigger_pattern','DATA_INTEGRITY',70,'x')
        self.assertGreaterEqual(fuse([one,two])['risk_score'],fuse([one])['risk_score'])
        contributor={'contributor':'source','risk_score':85,'evidence_families':{'duplication':50,'trigger_pattern':50},'recommended_action':'QUARANTINE'}
        before=contract([one],fuse([one]),[contributor]); after=contract([one,two],fuse([one,two]),[contributor])
        self.assertEqual(before['final_disposition'],'QUARANTINE'); self.assertEqual(after['final_disposition'],'QUARANTINE')
        self.assertGreaterEqual(after['max_asset_risk'],before['max_asset_risk'])

    def test_html_report_exposes_contract_fields(self):
        from reports.generator import render
        finding=self.finding('exact_duplicate','DATA_INTEGRITY',55,'sample')
        report={'scan_id':'test','timestamp':'now','assurance':fuse([finding]),'findings':[finding],**contract([finding],fuse([finding]),[])}
        html=render(report).lower()
        for field in ['decision contract','composite pipeline risk','maximum asset risk','final disposition','highest risk asset']:
            self.assertIn(field,html)

if __name__=='__main__': unittest.main()
