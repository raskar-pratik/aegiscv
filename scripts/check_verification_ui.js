'use strict';
// Real backend responses arrive on stdin. UI errors/pending are separate presentation context.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const fixture=JSON.parse(fs.readFileSync(0,'utf8')),elements=new Map(),fragments={};
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const element=id=>{if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',value:'',disabled:false,attrs:{},handlers:{},setAttribute(k,v){this.attrs[k]=v;},addEventListener(k,f){this.handlers[k]=f;},querySelector(){return element(id+'-submit');},querySelectorAll(){return[];}});return elements.get(id);};
let apiHandler=async()=>{throw Error('Unexpected API call');};
const context=vm.createContext({$:element,esc,ledgerCache:null,display(){},show(){},renderInvestigation(){},renderProvenance(){},renderLedger(){},refresh(){},notice(){},api:(...args)=>apiHandler(...args),document:{addEventListener(){},querySelectorAll(){return[];}},window:{addEventListener(){}}});
const source=fs.readFileSync('dashboard/static/workstation.js','utf8');
vm.runInContext(source.slice(0,source.indexOf('renderProvenance(null);show(')),context);
const combined=()=>['inference-assessment','inference-workspace','provenance-chain'].map(id=>element(id).innerHTML).join('');
function inference(name,record,check=null,ui={}){const original=JSON.stringify(record);context.renderProvenance(record,check,ui);assert.equal(JSON.stringify(record),original);const html=combined();assert(!html.includes('undefined'));fragments[name]=html;return html;}
function ledger(name,data,check=null,ui={}){const original=JSON.stringify(data);context.renderLedger(data,check,ui);assert.equal(JSON.stringify(data),original);const html=element('ledger-assessment').innerHTML+element('ledger-chain').innerHTML;assert(!html.includes('undefined'));fragments[name]=html;return html;}
let html=inference('inference_unchecked',fixture.record);assert(html.includes('NOT CHECKED'));assert(!html.includes('SIGNED RECORD VERIFIED'));assert(html.includes('PRESENT · NOT VERIFIED'));
html=inference('inference_valid',fixture.record,fixture.valid,{action:'verify'});assert(html.includes('SIGNED RECORD VERIFIED'));assert(html.includes('Replay policy NOT CHECKED'));assert(html.includes('BOUND BY VERIFIED RECORD'));assert(html.includes('Copy input identity'));assert(html.includes('0.1'));assert(!html.includes('>ACCEPTED'));
assert(element('inference-boundary').textContent.includes('does not prove the model is benign'));
html=inference('inference_modified',fixture.modified_record,fixture.modified,{action:'verify'});assert(html.includes('INTEGRITY FAILED')&&html.includes('Record hash mismatch'));assert(!html.includes('Output hash mismatch'));assert(!html.includes('BOUND BY VERIFIED RECORD'));
html=inference('inference_signature',fixture.signature_record,fixture.signature_invalid,{action:'verify'});assert(html.includes('RECORD VERIFICATION FAILED'));assert(html.includes('invalid signatures and invalid record structures'));assert(!html.includes('TAMPERING DETECTED'));
html=inference('inference_replay',fixture.record,fixture.replay,{action:'accept'});assert(html.includes('REPLAY DETECTED'));assert(html.includes('Signature/content checks passed before replay policy rejected acceptance.'));assert(!html.includes('ACCEPTED ·'));
html=inference('inference_accepted',fixture.record,fixture.accepted,{action:'accept'});assert(html.includes('ACCEPTED · REPLAY CHECK PASSED'));
html=inference('inference_missing',{},fixture.missing,{action:'verify'});assert(html.includes('NOT AVAILABLE'));assert(!html.includes('TAMPERING DETECTED'));
html=inference('inference_error',fixture.record,null,{phase:'error',message:'Request failed'});assert(html.includes('VERIFICATION ERROR'));assert(!html.includes('SIGNED RECORD VERIFIED'));
const hostile='<img src=x onerror="bad()">';const evil=JSON.parse(JSON.stringify(fixture.record));evil.record_id=hostile;evil.payload.input_hash=hostile;evil.payload.output=[[hostile]];
html=inference('inference_escaped',evil,{...fixture.signature_invalid,reason:hostile});assert(html.includes(esc(hostile))&&!html.includes(hostile));
html=ledger('ledger_empty',{records:[]},fixture.empty);assert(html.includes('CHAIN VERIFIED'));assert(html.includes('No records in this history'));
html=ledger('ledger_valid',fixture.ledger,fixture.valid_chain);assert(html.includes('CHAIN VERIFIED'));assert(html.includes('Copy Record hash'));assert(element('ledger-boundary').textContent.includes('independently preserved checkpoint'));
html=ledger('ledger_broken',fixture.broken,fixture.broken_check,{altered:true});assert(html.includes('FIRST INVALID LINK'));assert(html.includes('CHAIN NOT TRUSTED'));assert(html.includes('PASSED BEFORE FAILURE'));assert(html.includes('not independently classified as tampered'));assert(html.includes('stored records were not modified'));
html=ledger('ledger_sequence',fixture.wrong_sequence,fixture.sequence_check);assert(html.includes('#99'));assert(html.includes('Position 2'));assert(html.includes('FIRST INVALID LINK'));
html=ledger('ledger_checkpoint',fixture.shortened,fixture.checkpoint_check);assert(html.includes('VERIFICATION BOUNDARY FAILURE'));assert(html.includes('No displayed record exists'));
html=ledger('ledger_error',fixture.ledger,null,{phase:'error',message:'Storage request failed'});assert(html.includes('VERIFICATION ERROR'));assert(!html.includes('>VERIFIED<'));
html=ledger('ledger_missing',{records:[{}]});assert(html.includes('NOT AVAILABLE'));assert(html.includes('Timestamp not available'));
html=ledger('ledger_escaped',{records:[{sequence_number:hostile,kind:hostile,record_hash:hostile}]});assert(html.includes(esc(hostile))&&!html.includes(hostile));
context.renderLedger(fixture.ledger,fixture.valid_chain,{});context.renderLedger(fixture.shortened,fixture.valid_chain);assert(element('ledger-state').textContent==='NOT CHECKED');
context.renderLedger(fixture.shortened,fixture.valid_chain,{});assert(element('ledger-state').textContent==='VERIFICATION ERROR');
async function main(){
 // Action contracts: no auto-accept, exact payloads, pending, editing and execution errors.
 element('record-json').value=JSON.stringify(fixture.record);let calls=[];
 apiHandler=async(path,data)=>{calls.push({path,data});return fixture.valid;};
 await element('verify-record').onclick();assert.equal(element('copy-record-json').attrs['data-copy'],element('record-json').value);assert.equal(calls.length,1);assert.equal(calls[0].path,'/inference/verify');assert.deepEqual(JSON.parse(JSON.stringify(calls[0].data)),{record:fixture.record});
 apiHandler=async(path,data)=>{assert.equal(path,'/inference/accept');assert.deepEqual(JSON.parse(JSON.stringify(data)),{record:fixture.record});return fixture.replay;};
 await element('accept-record').onclick();assert(element('inference-assessment').innerHTML.includes('REPLAY DETECTED'));
 let resolve;apiHandler=()=>new Promise(r=>{resolve=r;});const pending=element('verify-record').onclick();assert(element('verify-record').disabled&&element('accept-record').disabled);assert(element('inference-assessment').innerHTML.includes('VERIFICATION PENDING'));
 element('record-json').value='{}';element('record-json').handlers.input();resolve(fixture.valid);await pending;assert(!element('inference-assessment').innerHTML.includes('SIGNED RECORD VERIFIED'));assert(!element('verify-record').disabled);
 element('record-json').value='invalid JSON';calls=[];apiHandler=async(...args)=>{calls.push(args);return fixture.valid;};await element('verify-record').onclick();assert.equal(calls.length,0);assert(element('inference-assessment').innerHTML.includes('VERIFICATION ERROR'));
 element('record-json').value=JSON.stringify(fixture.record);apiHandler=async()=>{throw Error('Request failed');};await element('verify-record').onclick();assert(element('inference-assessment').innerHTML.includes('VERIFICATION ERROR'));assert(!element('verify-record').disabled);
 // Existing altered-copy index and value; source records must be unchanged.
 const original=JSON.stringify(fixture.ledger);let sent;
 apiHandler=async(path,data)=>{if(path==='/ledger')return fixture.ledger;assert.equal(path,'/ledger/verify');sent=data;return fixture.broken_check;};
 await element('tamper-ledger').onclick();assert.equal(JSON.stringify(fixture.ledger),original);
 const changed=sent.records.map((r,i)=>r.record_hash!==fixture.ledger.records[i].record_hash?i:null).filter(i=>i!==null);assert.deepEqual(Array.from(changed),[Math.max(0,sent.records.length-3)]);assert.equal(sent.records[changed[0]].record_hash,'altered');
 apiHandler=async(path,data)=>{if(path==='/ledger')return fixture.ledger;assert.equal(path,'/ledger/verify');assert.equal(JSON.stringify(data),'{}');return fixture.valid_chain;};await element('verify-ledger').onclick();assert.equal(element('ledger-state').textContent,'VALID');
 const history=element('ledger-list').textContent;apiHandler=async()=>{throw Error('Storage error');};await element('verify-ledger').onclick();assert.equal(element('ledger-list').textContent,history);assert.equal(element('ledger-state').textContent,'VERIFICATION ERROR');assert(!element('verify-ledger').disabled);
 apiHandler=()=>new Promise(r=>{resolve=r;});const ledgerPending=element('verify-ledger').onclick();assert(element('tamper-ledger').disabled);assert.equal(element('ledger-state').textContent,'VERIFICATION PENDING');context.renderLedger(fixture.ledger,null);assert(element('tamper-ledger').disabled);assert.equal(element('ledger-state').textContent,'VERIFICATION PENDING');await element('tamper-ledger').onclick();resolve(fixture.ledger);apiHandler=async()=>fixture.valid_chain;await ledgerPending;
 // Generation feedback stays in app.js's existing form owner, with unchanged payload.
 const app=fs.readFileSync('dashboard/static/app.js','utf8');
 context.FormData=class{*[Symbol.iterator](){yield['model_id','registered'];yield['image','local.png'];}};
 vm.runInContext(app.slice(app.indexOf('function bindForm('),app.indexOf("bindForm('scan-form'")),context);
 context.bindForm('inference-form','/inference',async record=>context.renderProvenance(record));
 apiHandler=async(path,data)=>{assert.equal(path,'/inference');assert.equal(JSON.stringify(data),JSON.stringify({model_id:'registered',image:'local.png'}));throw Error('Execution failed');};
 await element('inference-form').onsubmit({preventDefault(){},target:element('inference-form')});assert(element('inference-assessment').innerHTML.includes('VERIFICATION ERROR'));
 console.log(JSON.stringify({status:'PASS',scope:'Actual backend fixtures, DOM/canvas-free stubs, API action contracts; no browser validation',fragments}));
}
main().catch(error=>{console.error(error);process.exit(1);});
