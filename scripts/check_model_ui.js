'use strict';
// Source-level renderer checks with canvas stubs; no browser or visual validation.
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const elements = new Map(), fragments = {};
const element = id => {
  if (!elements.has(id)) elements.set(id, {innerHTML:'', hidden:false, addEventListener(){}, getContext(){return {
    createImageData:(w,h)=>({data:new Uint8ClampedArray(w*h*4)}),
    putImageData:im=>{element(id).pixels=Array.from(im.data);},
  };}});
  return elements.get(id);
};
const esc = value => String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const context=vm.createContext({$:element,esc,display(){},show(){},renderInvestigation(){},renderProvenance(){},renderLedger(){},refresh(){},document:{addEventListener(){},querySelectorAll(){return[];}},window:{addEventListener(){}}});
const source=fs.readFileSync('dashboard/static/workstation.js','utf8');
vm.runInContext(source.slice(0,source.indexOf('renderProvenance(null);show(')),context);
const finding=(detector,extra={})=>({detector,category:'MODEL_INTEGRITY',status:'SUCCESS',severity:'LOW',risk_score:0,reason:'Backend reason',recommended_action:'ACCEPT',evidence:{},limitations:[],...extra});
const base=()=>({model:{metadata:{sha256:'b'.repeat(64),format:'torchscript',access:'LIMITED_WHITE_BOX',runtime_available:true,parameter_count:15},behavior:{fingerprint:'c'.repeat(64),probe_hash:'d'.repeat(64),top_prediction:[2,0],output:[[0,1,2],[2,0,1]]}},findings:[finding('model_hash',{evidence:{expected:'a'.repeat(64),actual:'b'.repeat(64)},recommended_action:'QUARANTINE',severity:'CRITICAL'}),finding('behavioral_probe',{evidence:{max_absolute_change:0.125},recommended_action:'REVIEW'}),finding('neural_cleanse',{evidence:{target:0,median:4,mad:1,anomaly_index:3,outcomes:[{target:0,mask_norm:1,success:0.95,mask:[[0,1],[.5,.25]],pattern:[[[1,0,0],[0,1,0]],[[0,0,1],[.5,.25,0]]]}],backdoor_assessment:{verdict:'STRONG_BACKDOOR_LIKE_EVIDENCE',recommended_action:'REVIEW'}},recommended_action:'REVIEW'})]});
function render(name,report){const frozen=JSON.stringify(report);context.renderModel(report);assert.equal(JSON.stringify(report),frozen);const html=element('model-workspace').innerHTML;assert(!html.includes('NaN')&&!html.includes('undefined'));fragments[name]=html;return html;}
let report=base(), html=render('model_mismatch',report);
assert(html.includes('status-danger">MISMATCH'));
assert(html.includes('NO ASSESSMENT RETURNED')===false);
assert(html.includes('EXPERIMENTAL BACKDOOR-LIKE EVIDENCE'));
assert(html.includes('Reconstruction anomalies may indicate suspicious model behavior but do not cryptographically confirm a backdoor.'));
assert(html.includes('95%') && html.includes('0.125'));
assert(html.includes('Copy Reference fingerprint') && html.includes('aria-describedby="trigger-preview-description"'));
assert.deepEqual(element('trigger-preview').pixels,[255,0,0,255,0,255,0,255,0,0,255,255,128,64,0,255]);
assert.deepEqual(element('mask-preview').pixels,[0,0,0,255,255,255,255,255,128,128,128,255,64,64,64,255]);
assert.equal(element('trigger-preview').width,2);assert.equal(element('trigger-preview').height,2);
report.findings[0].evidence.expected='b'.repeat(64);html=render('model_match',report);assert(html.includes('status-success">MATCH'));
report.findings[0].evidence.expected=null;html=render('model_no_reference',report);assert(html.includes('NO TRUSTED REFERENCE')&&!html.includes('>MATCH<'));
report.findings[0].status='FAILED';html=render('model_failed',report);assert(!html.includes('>MATCH<')&&!html.includes('>MISMATCH<'));
report=base();report.findings[2].evidence={backdoor_assessment:{verdict:'NO_QUALIFYING_EVIDENCE',recommended_action:'ACCEPT'}};report.findings[2].recommended_action='ACCEPT';
html=render('model_negative',report);assert(html.includes('NO QUALIFYING EVIDENCE'));assert(html.includes('Backend recommended action: <b>ACCEPT'));
assert(html.includes('DETECTOR EXECUTION STATUS</h3><span class="status-tag status-info">SUCCESS'));
assert(html.includes('BACKDOOR EVIDENCE STATUS</h3><span class="status-tag status-neutral">NO QUALIFYING EVIDENCE'));
assert.equal(element('mask-preview').hidden,true);assert.equal(element('mask-preview-unavailable').hidden,false);
report=base();report.model.metadata.access='BLACK_BOX';report.findings[2].status='UNAVAILABLE';report.findings[2].evidence={};report.findings[2].reason='Gradients inaccessible';
html=render('model_black_box',report);assert(html.includes('Gradients inaccessible'));assert(html.includes('White-box capability is not established'));assert(html.includes('2 / 3 returned checks completed'));
report=base();report.model.metadata.runtime_available=false;report.model.metadata.reason='Architecture factory required';report.findings=[];report.model.behavior=null;
html=render('model_missing',report);assert(html.includes('NOT CHECKED'));assert(html.includes('Architecture factory required'));assert(html.includes('Observed predictions unavailable'));
render('model_absent',{model:null,findings:[finding('model_scan',{status:'FAILED',reason:'Inspection failed'})]});assert(fragments.model_absent.includes('Inspection failed'));
report=base();report.findings.push(finding('activation_clustering',{evidence:{examined_classes:2,cluster_sizes:[18,2],minority_fraction:0.1,separation_ratio:4.5}}));
const attack='<img src=x onerror="alert(1)">';report.model.metadata.architecture=attack;report.model.metadata.sha256=attack;report.findings[2].evidence.target_label=attack;report.findings[0].reason=attack;report.findings[2].limitations=[attack];
html=render('model_escaping',report);assert(html.includes(esc(attack))&&!html.includes(attack));assert(html.includes('18 / 2'));
// Malformed/absent arrays must not leave a blank canvas presented as evidence.
for(const data of [null,[],[[NaN]],[[[1,0]]],[[[1,0,0]],[]]]){context.drawArray('trigger-preview',data,true);assert.equal(element('trigger-preview').hidden,true);}
context.drawArray('mask-preview',[[0,.5,1]],false);assert.equal(element('mask-preview').width,3);assert.equal(element('mask-preview').height,1);
assert(!source.includes('TP = 5')); // historical metrics never become scan evidence
// Preserve the frozen validation record and exercise real returned reconstruction arrays.
const frozenResults=JSON.parse(fs.readFileSync('experiments/results/stabilization_final/backdoor_results.json','utf8'));
assert.deepEqual(['tp','fp','tn','fn'].map(k=>frozenResults.metrics[k]),[5,1,2,1]);
for(const record of frozenResults.records){
  const report={model:{metadata:{sha256:record.model_hash}},findings:[record.finding,record.patch_probe].filter(Boolean)};
  const before=JSON.stringify(report);context.renderModel(report);assert.equal(JSON.stringify(report),before);
  const ev=record.finding.evidence||{}, outcome=(ev.outcomes||[]).find(o=>o.target===ev.target);
  if(outcome?.pattern){
    assert.equal(element('trigger-preview').hidden,false);
    assert.equal(element('trigger-preview').width,outcome.pattern[0].length);
    assert.equal(element('trigger-preview').height,outcome.pattern.length);
    assert.equal(element('trigger-preview').pixels[0],Math.round(255*Math.max(0,Math.min(1,outcome.pattern[0][0][0]))));
  }
}
console.log(JSON.stringify({status:'PASS',scope:'Model renderer and canvas stub checks; not browser validation',fragments}));
