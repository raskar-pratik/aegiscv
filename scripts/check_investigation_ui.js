'use strict';
// Execute existing renderers with element stubs. This is not a browser/layout test.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert/strict');
const root = path.resolve(__dirname, '..');
const elements = new Map();
const element = id => {
  if (!elements.has(id)) elements.set(id, {innerHTML: '', textContent: '', addEventListener() {}});
  return elements.get(id);
};
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
const context = vm.createContext({
  $: element, esc: escape, display() {}, show() {}, renderInvestigation() {},
  renderProvenance() {}, renderLedger() {}, refresh() {},
  document: {addEventListener() {}, querySelectorAll() { return []; }},
  window: {addEventListener() {}},
});
const source = fs.readFileSync(path.join(root, 'dashboard/static/workstation.js'), 'utf8');
vm.runInContext(source.slice(0, source.indexOf('renderProvenance(null);show(')), context);
const untrusted = '<img src=x onerror="alert(1)">';
const findings = Array.from({length: 15}, (_, i) => ({
  finding_id: 'finding-' + i, asset_id: 'asset_' + String(i).padStart(2, '0'),
  detector: i % 2 ? 'near_duplicate' : 'exact_duplicate', category: 'DATA_INTEGRITY',
  severity: i % 2 ? 'HIGH' : 'MODERATE', risk_score: 21 + i, confidence: .96,
  reason: i === 0 ? untrusted : 'Reported evidence ' + i,
  status: 'SUCCESS', quality: {status: 'CALIBRATED'}, recommended_action: 'REVIEW',
  evidence: {detail: untrusted}, limitations: [untrusted],
}));
const report = {
  manifest: {format: 'folder', manifest_hash: 'a'.repeat(64), assets: findings.map(f => ({asset_id: f.asset_id, labels: ['class-a'], contributor: untrusted}))},
  contributors: [
    {contributor: 'benign-source', samples: 4, affected_samples: 0, risk_score: 0, evidence_families: {}, recommended_action: 'ACCEPT', evidence: []},
    {contributor: '<evil"&>', samples: 3, affected_samples: 1, risk_score: 3, evidence_families: {'<family&>': 12}, evidence: []},
    {contributor: 'malicious-contributor', samples: 57, affected_samples: 57, risk_score: 100, evidence_families: {duplication: 100, representation: 82, trigger_pattern: 94}, recommended_action: 'QUARANTINE', evidence: [{finding_id: 'finding-0'}, {finding_id: 'finding-1'}]},
  ],
  findings: [...findings, {...findings[0], asset_id: 'excluded-low', risk_score: 20}, {...findings[0], asset_id: 'excluded-model', category: 'MODEL_INTEGRITY'}],
};
const originalReport = JSON.stringify(report);
context.renderDataset(report);
const dataset = element('dataset-workspace').innerHTML;
for (let i = 0; i < 15; i++) {
  const name = 'asset_' + String(i).padStart(2, '0');
  assert.equal(dataset.includes(name), i < 12, 'Existing risk selection/cap changed: ' + name);
  if (i > 0 && i < 12) assert(dataset.indexOf('asset_' + String(i - 1).padStart(2, '0')) < dataset.indexOf(name));
}
assert(!dataset.includes('excluded-low') && !dataset.includes('excluded-model'));
assert(dataset.includes(escape(untrusted)) && !dataset.includes(untrusted));
assert(dataset.includes('96%') && dataset.includes('CALIBRATED'));
assert(!dataset.includes('VERIFIED SAFE'));
const missing = vm.runInContext('investigationEvidence({asset_id:"missing",severity:"LOW",evidence:{}})', context);
assert(missing.includes('Unavailable') && missing.includes('Not supplied'));
assert(!missing.includes('NaN') && !missing.includes('undefined'));
context.renderDataset({manifest: {assets: []}, findings: []});
assert(element('dataset-workspace').innerHTML.includes('does not establish absence of risk'));
const fragments = {dataset, missing};
if (!process.argv.includes('--data-only')) {
  context.renderInvestigation(report);
  const contributors = element('contributors-detail').innerHTML;
  assert(contributors.indexOf('malicious-contributor') < contributors.indexOf('benign-source'));
  assert(contributors.includes('57 / 57') && contributors.includes('100') && contributors.includes('QUARANTINE'));
  assert(!contributors.includes('100%'));
  assert(contributors.includes('ACCEPT'));
  assert(contributors.includes(escape('<evil"&>')) && !contributors.includes('<evil"&>'));
  assert(contributors.includes('Unknown')); // no action supplied: do not invent REVIEW/ACCEPT
  assert(contributors.includes('value="82"') && contributors.includes('value="94"'));
  assert(contributors.includes('Assets associated with duplicate clusters do not establish who created the duplicate.'));
  assert(contributors.includes('investigation-evidence') && !contributors.includes(untrusted));
  assert(contributors.includes(escape(untrusted)));
  assert(contributors.includes('scope="col"') && contributors.includes('aria-label='));
  context.renderInvestigation({contributors: [], findings: []});
  assert(element('contributors-detail').innerHTML.includes('No contributor evidence'));
  fragments.contributors = contributors;
  fragments.empty_contributors = element('contributors-detail').innerHTML;
}
assert.equal(JSON.stringify(report), originalReport, 'Rendering must not mutate report data');
// JSON can be fed to the Python HTML structure check; nothing here is a screenshot.
console.log(JSON.stringify({status: 'PASS', scope: 'renderer execution with element stubs; not browser validation', fragments}));
