"""Record the real local dashboard using isolated synthetic demo state.

Optional recording dependency: pip install playwright
Use --channel chrome for installed Google Chrome, or --channel msedge for Edge.
No browser/package/model download is performed by this script.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--channel', choices=['chrome', 'msedge', 'chromium'], default='chrome')
    parser.add_argument('--output', type=Path, default=ROOT / 'local_state/linkedin-video')
    args = parser.parse_args()
    from playwright.sync_api import sync_playwright, expect
    from werkzeug.serving import make_server
    from app.main import create_app

    output = args.output.resolve() / time.strftime('%Y%m%d-%H%M%S')
    output.mkdir(parents=True, exist_ok=False)
    errors, shots = [], []
    with tempfile.TemporaryDirectory(prefix='aegiscv-recording-') as directory, sync_playwright() as playwright:
        options = {'headless': True}
        if args.channel != 'chromium':
            options['channel'] = args.channel
        # Fail before starting the demo if the selected browser cannot launch.
        browser = playwright.chromium.launch(**options)
        app = create_app(directory)
        server = make_server('127.0.0.1', 0, app, threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{server.server_port}'
        recording = None
        try:
            print('Preparing real synthetic scans; this may take several minutes.', flush=True)
            setup = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = setup.new_page()
            page.goto(url)
            page.locator('#demo').click()
            expect(page.locator('#notice')).to_contain_text('Assessment complete', timeout=600000)
            # Use actual generated data and a fresh inference record, not prewritten results.
            demo_dir = next((Path(directory) / 'imports').glob('demo-*')).name
            page.locator('nav button[data-page="models"]').click()
            page.locator('#model-form input[name=path]').fill(demo_dir + '/models/clean.torchscript')
            page.locator('#model-form input[name=trusted]').check()
            with page.expect_response(lambda r: r.url.endswith('/api/models') and r.request.method == 'POST') as response:
                page.locator('#model-form button').click()
            assert response.value.ok, 'Model registration failed'
            model_id = response.value.json()['id']
            page.locator('nav button[data-page="inference"]').click()
            page.locator('#inference-form input[name=model_id]').fill(model_id)
            page.locator('#inference-form input[name=image]').fill(demo_dir + '/clean/red/00.png')
            page.locator('#inference-form button').click()
            expect(page.locator('#record-json')).not_to_have_value('', timeout=60000)
            record = page.locator('#record-json').input_value()
            await_scans = page.request.get(url + '/api/scans').json()
            attacked_id = None
            for scan in await_scans:
                if scan['status'] == 'COMPLETE':
                    report = page.request.get(url + '/api/scans/' + scan['id']).json()['data']
                    if (report.get('model') or {}).get('metadata', {}).get('sha256') and any(
                        f.get('detector') == 'model_hash' and f.get('risk_score') == 100
                        for f in report.get('findings', [])
                    ):
                        attacked_id = scan['id']
                        break
            assert attacked_id, 'Expected seeded substitution report was not returned'
            setup.close()

            recording = browser.new_context(viewport={'width': 1920, 'height': 1080},
                                            record_video_dir=str(output),
                                            record_video_size={'width': 1920, 'height': 1080})
            page = recording.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            video = page.video
            started = time.monotonic()

            def hold(title, seconds):
                shots.append({'seconds': round(time.monotonic() - started, 2), 'scene': title})
                print(title, flush=True)
                page.wait_for_timeout(seconds * 1000)

            def go(name):
                page.locator(f'nav button[data-page="{name}"]').click()
                page.wait_for_timeout(500)

            page.goto(url)
            go('reports')
            page.locator(f'#report-list button[data-scan="{attacked_id}"]').click()
            expect(page.locator('#score')).not_to_have_text('—')
            hold('Overview — actual seeded demonstration assessment', 9)
            go('contributors-page')
            expect(page.locator('#contributors-detail table')).to_be_visible()
            hold('Contributor evidence — association does not establish authorship', 8)
            go('models')
            expect(page.locator('#model-workspace')).to_contain_text('MISMATCH')
            hold('Model Integrity — trusted-reference byte mismatch', 9)
            go('inference')
            page.locator('#inference .technical-record summary').click()
            page.locator('#record-json').fill(record)
            page.locator('#inference .technical-record summary').click()
            page.locator('#verify-record').click()
            expect(page.locator('#inference-assessment')).to_contain_text('SIGNED RECORD VERIFIED')
            page.evaluate('window.scrollTo(0, 0)')
            hold('Inference — signature and content verification', 9)
            page.locator('#accept-record').click()
            expect(page.locator('#inference-assessment')).to_contain_text('ACCEPTED · REPLAY CHECK PASSED')
            page.locator('#accept-record').click()
            expect(page.locator('#inference-assessment')).to_contain_text('REPLAY DETECTED')
            page.evaluate('window.scrollTo(0, 0)')
            hold('Replay policy — repeated acceptance rejected', 8)
            go('ledger')
            page.locator('#verify-ledger').click()
            expect(page.locator('#ledger-state')).to_have_text('VALID')
            page.evaluate('window.scrollTo(0, 0)')
            hold('Audit ledger — actual chain verification', 8)
            page.locator('#tamper-ledger').click()
            expect(page.locator('#ledger-assessment')).to_contain_text('FIRST INVALID LINK')
            page.evaluate('window.scrollTo(0, 0)')
            hold('Altered-copy demonstration — stored ledger remains unchanged', 10)
            go('overview')
            hold('AegisCV — synthetic demonstration, not general detector accuracy', 6)
            recording.close()
            recording = None
            raw = output / 'aegiscv-demo.webm'
            video.save_as(str(raw))
            original = Path(video.path())
            if original != raw:
                original.unlink(missing_ok=True)
            (output / 'recording-notes.json').write_text(json.dumps({
                'scope': 'Actual local app interaction using isolated synthetic demo data',
                'shots': shots, 'page_errors': errors,
                'validation': 'Recorded workflow only; not full responsive/browser regression',
                'runtime_external_requests': 'NOT MEASURED',
            }, indent=2), encoding='utf-8')
            if errors:
                raise RuntimeError(f'Browser errors occurred; inspect recording-notes.json before sharing: {errors}')
            if shutil.which('ffmpeg'):
                mp4 = output / 'aegiscv-demo.mp4'
                subprocess.run(['ffmpeg', '-y', '-i', str(raw), '-c:v', 'libx264', '-crf', '20',
                                '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(mp4)], check=True)
                print(f'Video saved: {mp4}')
            else:
                print(f'Video saved: {raw}\nConvert to MP4 in your video editor before posting.')
        finally:
            if recording:
                recording.close()
            browser.close()
            server.shutdown()
            app.extensions['worker'].shutdown(wait=True)


if __name__ == '__main__':
    main()
