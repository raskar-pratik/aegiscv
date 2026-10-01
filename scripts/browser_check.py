"""Browser smoke test using preinstalled Playwright and a local Edge executable."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def main():
    output=Path('docs/screenshots'); output.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True,args=['--disable-background-networking'])
        page=browser.new_page(viewport={'width':1440,'height':1000})
        errors=[]; external=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('console',lambda message:errors.append(message.text) if message.type=='error' else None)
        def route(request):
            if not request.request.url.startswith('http://127.0.0.1:26228/'):
                external.append(request.request.url); request.abort()
            else: request.continue_()
        page.route('**/*',route)
        page.goto('http://127.0.0.1:26228/',wait_until='networkidle')
        page.get_by_role('button',name='Run reproducible demonstration').click()
        expect(page.locator('#notice')).to_contain_text('Assessment complete',timeout=60000)
        assert page.locator('#score').inner_text()!='—'
        page.screenshot(path=str(output/'overview.png'),full_page=True)
        page.screenshot(path=str(output/'distribution_shift.png'),full_page=True)
        page.get_by_role('button',name='Data integrity',exact=True).click()
        page.screenshot(path=str(output/'dataset_integrity.png'),full_page=True)
        page.get_by_role('button',name='Demonstration Console',exact=True).click()
        page.screenshot(path=str(output/'demo_mode.png'),full_page=True)
        page.get_by_role('button',name='Overview',exact=True).click()
        page.get_by_role('button',name='Assurance reports',exact=True).click()
        report_buttons=page.locator('#report-list button[data-scan]')
        if report_buttons.count():
            report_buttons.last.click(); page.wait_for_timeout(250)
            page.get_by_role('button',name='Overview',exact=True).click()
        page.screenshot(path=str(output/'malicious_contributor.png'),full_page=True)
        page.get_by_role('button',name='Audit ledger',exact=True).click()
        page.locator('#verify-ledger').click()
        expect(page.locator('#ledger-result')).to_contain_text('VALID')
        page.screenshot(path=str(output/'ledger_valid.png'),full_page=True)
        page.locator('#tamper-ledger').click()
        expect(page.locator('#ledger-result')).to_contain_text('TAMPERED')
        page.screenshot(path=str(output/'ledger_tampered.png'),full_page=True)
        page.get_by_role('button',name='Coverage matrix',exact=True).click()
        assert page.locator('#coverage-list').get_by_text('UNAVAILABLE',exact=True).count()>0
        page.screenshot(path=str(output/'coverage.png'),full_page=True)
        latest=max(Path('local_state/imports').glob('demo-*'),key=lambda d:d.stat().st_mtime).name
        page.get_by_role('button',name='Models',exact=True).click()
        page.locator('#model-form input[name=path]').fill(latest+'/models/clean.torchscript')
        page.locator('#model-form input[name=trusted]').check()
        # refresh() issues a concurrent GET after the form submit; bind this wait to the POST
        # so the smoke test cannot accidentally parse the model-list response as a created model.
        with page.expect_response(lambda candidate: candidate.url.endswith('/api/models') and candidate.request.method=='POST') as response:
            page.locator('#model-form button').click()
        model_id=response.value.json()['id']
        page.get_by_role('button',name='Inference records',exact=True).click()
        page.locator('#inference-form input[name=model_id]').fill(model_id)
        page.locator('#inference-form input[name=image]').fill(latest+'/clean/red/00.png')
        page.locator('#inference-form button').click()
        expect(page.locator('#record-json')).not_to_be_empty()
        page.get_by_role('button',name='Verify record',exact=True).click()
        expect(page.locator('#inference-result')).to_contain_text('VALID')
        page.screenshot(path=str(output/'inference_verified.png'),full_page=True)
        page.get_by_role('button',name='Accept with replay protection').click()
        expect(page.locator('#inference-result')).to_contain_text('persisted')
        page.get_by_role('button',name='Accept with replay protection').click()
        expect(page.locator('#inference-result')).to_contain_text('REPLAY')
        record=json.loads(page.locator('#record-json').input_value())
        record['payload']['output'][0][0]+=1
        page.locator('#inference .technical-record summary').click()
        page.locator('#record-json').fill(json.dumps(record))
        page.get_by_role('button',name='Verify record',exact=True).click()
        expect(page.locator('#inference-result')).to_contain_text('TAMPERED')
        page.screenshot(path=str(output/'inference_tampered.png'),full_page=True)
        page.get_by_role('button',name='Models',exact=True).click()
        page.screenshot(path=str(output/'model_integrity.png'),full_page=True)
        assert not errors,errors
        assert not external,external
        print(json.dumps({'browser_errors':errors,'external_requests':external,'demo':'complete','ledger':'VALID','screenshots':str(output)}))
        browser.close()


if __name__=='__main__': main()
