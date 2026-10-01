"""Execute final regression gates. Requires the existing loopback app to be running."""
import json,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def main():
    from experiments.final_validation import save
    root=Path(__file__).resolve().parents[1]; output=root/'experiments/results/stabilization'; started=time.perf_counter()
    tests=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=root,capture_output=True,text=True,timeout=240)
    (output/'test_output.txt').write_text(tests.stdout+tests.stderr,encoding='utf-8')
    browser=subprocess.run([sys.executable,'scripts/browser_check.py'],cwd=root,capture_output=True,text=True,timeout=180)
    (output/'browser_output.txt').write_text(browser.stdout+browser.stderr,encoding='utf-8')
    browser_result=json.loads(browser.stdout.strip().splitlines()[-1]) if browser.returncode==0 else {'error':browser.stderr,'external_requests':None}
    summary=json.loads((output/'comparison.json').read_text()); pairs=summary['heldout_pairs']
    gates={'clean_not_high_critical':summary['clean']['assurance']['severity'] not in {'HIGH','CRITICAL'},
        'near_false_positives_reduced':pairs['clean_image_fpr']<=.02 and pairs['recall']>=.5,
        'benign_sources_not_universally_flagged':sum(r['risk_score']>20 for r in summary['clean']['contributors'])<len(summary['clean']['contributors']),
        'monotonic_properties':tests.returncode==0 and 'test_monotonic_properties_and_unavailable_separation' in tests.stderr,
        'interpretable_operational_drift':summary['drift']['after'] and summary['drift']['acquisition']['reason']=='OPERATIONAL DISTRIBUTION SHIFT DETECTED',
        'cryptographic_checks':all(summary['cryptographic_checks'].values()),'full_suite':tests.returncode==0,'browser_regression':browser.returncode==0,
        'zero_observed_external_requests':summary['network']['external_attempt_count']==0 and browser_result.get('external_requests')==[]}
    result={'gates':gates,'demo_freeze':'YES' if all(gates.values()) else 'NO','test_exit_code':tests.returncode,'browser_exit_code':browser.returncode,
        'browser':browser_result,'runtime_seconds':time.perf_counter()-started,'observation_scope':'Python socket/DNS guard during full experiment and application-page browser request interception; not OS-wide packet capture'}
    save(output/'freeze_verification.json',result); summary['demo_freeze']=result['demo_freeze']; save(output/'comparison.json',summary)
    with (output/'STABILIZATION_REPORT.md').open('a',encoding='utf-8') as stream:
        stream.write('\n\n## Final freeze verification\n\nDEMO FREEZE: '+result['demo_freeze']+'\n\n'+json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2)); return 0 if all(gates.values()) else 1

if __name__=='__main__': raise SystemExit(main())
