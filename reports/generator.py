"""Portable JSON and escaped, printable HTML assurance report."""
import html
import json
from pathlib import Path


def render(report):
    escape=lambda v:html.escape(str(v))
    a=report['assurance']; sections=[]
    for key in ['encoder_capability','detector_runtime_seconds','manifest','model','ledger_verification','contributors','correlations','coverage','limitations']:
        if key not in report: continue
        sections.append(f'<h2>{escape(key.replace("_"," ").title())}</h2><pre>{escape(json.dumps(report[key],indent=2))}</pre>')
    findings=''.join(f'<article><h3>{escape(f["severity"])} · {escape(f["detector"])}</h3><p>{escape(f["asset_id"])} — {escape(f["reason"])}</p><p>Confidence {f["confidence"]} · {escape(f["recommended_action"])} · {escape(f["status"])}</p><pre>{escape(json.dumps(f["evidence"],indent=2))}</pre></article>' for f in report['findings'])
    contract=f'<h2>Decision contract</h2><p>Composite pipeline risk {escape(str(report.get("composite_risk",a.get("risk_score"))))} · maximum asset risk {escape(str(report.get("max_asset_risk",0)))} · final disposition <strong>{escape(str(report.get("final_disposition",a.get("recommended_action"))))}</strong></p><p>Highest risk asset: {escape(str(report.get("highest_risk_asset","dataset")))} ({escape(str(report.get("highest_risk_asset_type","DATASET")))}); severity {escape(str(report.get("highest_severity","LOW")))}</p><pre>{escape(json.dumps(report.get("disposition_trigger",{}),indent=2))}</pre>'
    disposition=report.get('final_disposition',a.get('recommended_action','REVIEW'))
    composite=report.get('composite_risk',a.get('risk_score',0)); max_asset=report.get('max_asset_risk',0)
    confidence=report.get('confidence',a.get('confidence',0)); coverage=report.get('coverage',a.get('coverage_fraction',0))
    trigger=report.get('disposition_trigger',{})
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Veyra Assurance Report</title><style>
body{{font:14px/1.55 Inter,Segoe UI,Arial,sans-serif;color:#1e344b;background:#f4f6f4;margin:0;padding:34px;max-width:1180px}}header,section,article{{background:#fff;border:1px solid #d8e0e6;border-radius:6px;padding:22px;margin:0 0 18px}}header{{border-top:6px solid #10263e}}h1{{font-size:32px;margin:0 0 5px;color:#10263e}}h2{{font-size:18px;color:#10263e;margin-top:0}}.meta{{color:#64788a;font-size:12px}}.decision{{display:grid;grid-template-columns:1.2fr 2fr;gap:18px;align-items:stretch}}.disposition{{background:#10263e;color:#fff;padding:22px;border-radius:5px}}.disposition strong{{display:block;font-size:36px;letter-spacing:1px;margin:8px 0;text-transform:uppercase}}.metrics{{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:#d8e0e6}}.metric{{background:#f8faf9;padding:15px}}.metric b{{display:block;font-size:21px;color:#1e344b}}.metric span{{font-size:10px;letter-spacing:1px;color:#60768a}}.trigger{{background:#e9eff1;padding:13px;border-left:3px solid #66849a;color:#4c6478}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf1f3;padding:14px;max-height:520px;overflow:auto}}article{{break-inside:avoid;border-radius:4px;padding:16px;margin:11px 0}}.finding-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}@media(max-width:700px){{body{{padding:15px}}.decision,.finding-grid{{grid-template-columns:1fr}}}}@media print{{body{{background:#fff;padding:0}}header,section,article{{box-shadow:none}}.decision{{break-inside:avoid}}}}
</style><header><h1>Veyra — Assurance Report</h1><p class="meta">{escape(report["scan_id"])} · {escape(report["timestamp"])} · local-only evidence packet</p></header><section class="decision"><div class="disposition"><span>FINAL DISPOSITION</span><strong>{escape(str(disposition))}</strong><span>{escape(str(report.get('highest_risk_reason','Decision contract loaded')))}</span></div><div class="metrics"><div class="metric"><span>COMPOSITE PIPELINE RISK</span><b>{escape(str(composite))} / 100</b></div><div class="metric"><span>MAXIMUM ASSET RISK</span><b>{escape(str(max_asset))} / 100</b></div><div class="metric"><span>CONFIDENCE</span><b>{float(confidence)*100:.1f}%</b></div><div class="metric"><span>COVERAGE</span><b>{float(coverage)*100:.0f}%</b></div></div></section><section><h2>Decision contract</h2><p>Highest risk asset: <strong>{escape(str(report.get("highest_risk_asset","dataset")))}</strong> ({escape(str(report.get("highest_risk_asset_type","DATASET")))}); severity {escape(str(report.get("highest_severity","LOW")))}</p><p class="trigger"><b>Trigger:</b> {escape(str(trigger.get('type','NONE')))} · {escape(str(trigger.get('asset','dataset')))} · risk {escape(str(trigger.get('risk',0)))} · {escape(str(trigger.get('reason','No decisive evidence override')))}</p><p>{escape(str(report.get('composite_score_type',a.get('score_type','Heuristic aggregate'))))}</p></section><section><h2>Evidence and recommended actions</h2><div class="finding-grid">{findings}</div></section>{"".join(sections)}</html>'''


def save(report, directory: Path):
    directory.mkdir(parents=True,exist_ok=True); base=directory/report['scan_id']
    base.with_suffix('.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    base.with_suffix('.html').write_text(render(report),encoding='utf-8')
