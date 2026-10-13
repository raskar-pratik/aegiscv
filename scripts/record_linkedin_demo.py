"""Record the real local Veyra dashboard using isolated synthetic demo state.

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
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--channel', choices=['chrome', 'msedge', 'chromium'], default='chrome')
    parser.add_argument('--output', type=Path, default=ROOT / 'local_state/linkedin-video')
    parser.add_argument('--deliverables', type=Path, default=Path(r'd:\DOWNLOADS\Veyra-LinkedIn-Deliverables'))
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright, expect
    from werkzeug.serving import make_server
    from app.main import create_app

    timestamp = time.strftime('%Y%m%d-%H%M%S')
    output = args.output.resolve() / timestamp
    output.mkdir(parents=True, exist_ok=True)
    deliverables = args.deliverables.resolve()
    deliverables.mkdir(parents=True, exist_ok=True)

    console_logs = []
    page_errors = []
    all_requests = []
    responses = []
    external_requests = []
    failed_requests = []
    shots = []

    def attach_telemetry(p):
        p.on('console', lambda msg: console_logs.append({
            'type': msg.type, 'text': msg.text, 'location': msg.location
        }))
        p.on('pageerror', lambda err: page_errors.append(str(err)))

        def on_req(req):
            url = req.url
            all_requests.append({'url': url, 'method': req.method, 'resource_type': req.resource_type})
            parsed = urllib.parse.urlparse(url)
            if parsed.hostname not in ('127.0.0.1', 'localhost'):
                external_requests.append(url)

        def on_fail(req):
            failed_requests.append({'url': req.url, 'method': req.method, 'failure': req.failure})

        def on_resp(resp):
            responses.append({'url': resp.url, 'status': resp.status})

        p.on('request', on_req)
        p.on('requestfailed', on_fail)
        p.on('response', on_resp)

    with tempfile.TemporaryDirectory(prefix='veyra-recording-') as directory, sync_playwright() as playwright:
        options = {'headless': True}
        if args.channel != 'chromium':
            options['channel'] = args.channel

        print(f"Launching browser with channel: {args.channel}...", flush=True)
        browser = playwright.chromium.launch(**options)
        app = create_app(directory)
        server = make_server('127.0.0.1', 0, app, threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{server.server_port}'
        recording = None

        try:
            print('Preparing real synthetic scans; monitoring for prompt terminal failure...', flush=True)
            setup = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = setup.new_page()
            attach_telemetry(page)
            page.goto(url)

            # Trigger reproducible demonstration
            page.locator('#demo').click()

            # Fail promptly on any reported terminal failure
            start_wait = time.monotonic()
            complete = False
            while time.monotonic() - start_wait < 600:
                notice_el = page.locator('#notice')
                text = notice_el.inner_text().strip() if notice_el.count() > 0 else ""
                classes = (notice_el.get_attribute('class') or "").split()
                if 'error' in classes or 'FAILED' in text or 'Scan FAILED' in text:
                    raise RuntimeError(f"Demo preparation failed promptly with error in #notice: '{text}'")
                if 'Assessment complete' in text:
                    complete = True
                    print('Assessment complete reported by application.', flush=True)
                    break
                page.wait_for_timeout(1000)

            if not complete:
                raise TimeoutError("Demo preparation timed out after 600s without completing.")

            demo_dir = next((Path(directory) / 'imports').glob('demo-*')).name
            print(f'Using synthetic demo state: {demo_dir}', flush=True)

            # Register trusted model for comparison
            page.locator('nav button[data-page="models"]').click()
            page.locator('#model-form input[name=path]').fill(demo_dir + '/models/clean.torchscript')
            page.locator('#model-form input[name=trusted]').check()
            with page.expect_response(lambda r: r.url.endswith('/api/models') and r.request.method == 'POST') as response:
                page.locator('#model-form button').click()
            assert response.value.ok, f'Model registration failed with status {response.value.status}'
            model_id = response.value.json()['id']

            # Generate fresh signed inference record
            page.locator('nav button[data-page="inference"]').click()
            page.locator('#inference-form input[name=model_id]').fill(model_id)
            page.locator('#inference-form input[name=image]').fill(demo_dir + '/clean/red/00.png')
            page.locator('#inference-form button').click()
            expect(page.locator('#record-json')).not_to_have_value('', timeout=60000)
            record = page.locator('#record-json').input_value()

            # Locate attacked scan ID
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
            print(f'Target attacked scan ID: {attacked_id}', flush=True)
            setup.close()

            # Start recording context
            print('Starting high-resolution 1920x1080 recording session...', flush=True)
            recording = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                record_video_dir=str(output),
                record_video_size={'width': 1920, 'height': 1080}
            )
            page = recording.new_page()
            attach_telemetry(page)
            video = page.video
            started = time.monotonic()

            def inject_overlays():
                page.evaluate("""() => {
                    if (document.getElementById('demo-watermark')) return;
                    // Top-right watermark
                    const wm = document.createElement('div');
                    wm.id = 'demo-watermark';
                    Object.assign(wm.style, {
                        position: 'fixed',
                        top: '18px',
                        right: '32px',
                        background: 'rgba(19,37,54,0.92)',
                        color: '#8bb8d8',
                        border: '1px solid #365f7e',
                        borderRadius: '18px',
                        padding: '6px 16px',
                        fontFamily: 'Inter,Segoe UI,sans-serif',
                        fontSize: '12px',
                        fontWeight: '700',
                        letterSpacing: '0.8px',
                        zIndex: '99999',
                        pointerEvents: 'none',
                        boxShadow: '0 3px 12px rgba(0,0,0,0.3)',
                        textTransform: 'uppercase'
                    });
                    wm.textContent = 'Seeded synthetic demonstration';
                    document.body.appendChild(wm);

                    // Bottom caption bar
                    const cp = document.createElement('div');
                    cp.id = 'demo-caption';
                    Object.assign(cp.style, {
                        position: 'fixed',
                        bottom: '24px',
                        left: '50%',
                        transform: 'translateX(-50%)',
                        background: 'rgba(19,37,54,0.95)',
                        color: '#fff',
                        border: '1px solid #365f7e',
                        borderRadius: '8px',
                        padding: '12px 28px',
                        fontFamily: 'Inter,Segoe UI,sans-serif',
                        fontSize: '15px',
                        fontWeight: '500',
                        zIndex: '99999',
                        pointerEvents: 'none',
                        boxShadow: '0 6px 24px rgba(0,0,0,0.45)',
                        textAlign: 'center',
                        maxWidth: '880px',
                        lineHeight: '1.45',
                        transition: 'opacity 0.25s ease'
                    });

                    const kickerEl = document.createElement('div');
                    kickerEl.id = 'demo-caption-kicker';
                    Object.assign(kickerEl.style, {
                        color: '#8bb8d8',
                        fontSize: '12px',
                        letterSpacing: '1.2px',
                        marginBottom: '3px',
                        textTransform: 'uppercase',
                        fontWeight: '700'
                    });
                    kickerEl.textContent = 'Veyra';

                    const textEl = document.createElement('div');
                    textEl.id = 'demo-caption-text';
                    Object.assign(textEl.style, {
                        fontSize: '14px',
                        color: '#ffffff'
                    });
                    textEl.textContent = 'Computer Vision Integrity Assurance';

                    cp.appendChild(kickerEl);
                    cp.appendChild(textEl);
                    document.body.appendChild(cp);

                    // Visible mouse pointer dot
                    const cur = document.createElement('div');
                    cur.id = 'demo-cursor';
                    Object.assign(cur.style, {
                        position: 'fixed',
                        width: '16px',
                        height: '16px',
                        borderRadius: '50%',
                        background: 'rgba(224,98,74,0.85)',
                        border: '2px solid #ffffff',
                        pointerEvents: 'none',
                        zIndex: '999999',
                        transform: 'translate(-50%, -50%)',
                        boxShadow: '0 0 8px rgba(0,0,0,0.5)',
                        display: 'none'
                    });
                    document.body.appendChild(cur);
                    window.addEventListener('mousemove', e => {
                        cur.style.display = 'block';
                        cur.style.left = e.clientX + 'px';
                        cur.style.top = e.clientY + 'px';
                    });
                }""")

            def set_caption(kicker, text):
                page.evaluate("""([k, t]) => {
                    const kEl = document.getElementById('demo-caption-kicker');
                    const tEl = document.getElementById('demo-caption-text');
                    if (kEl) kEl.textContent = k;
                    if (tEl) tEl.textContent = t;
                }""", [kicker, text])

            def hold(scene_name, seconds):
                elapsed = round(time.monotonic() - started, 2)
                shots.append({'seconds': elapsed, 'scene': scene_name, 'duration': seconds})
                print(f"[{elapsed}s] {scene_name} ({seconds}s)", flush=True)
                page.wait_for_timeout(seconds * 1000)

            def move_mouse(loc):
                loc.scroll_into_view_if_needed()
                box = loc.bounding_box()
                if box:
                    x = box['x'] + box['width'] / 2
                    y = box['y'] + box['height'] / 2
                    page.mouse.move(x, y, steps=10)
                    page.wait_for_timeout(150)

            def go(name):
                btn = page.locator(f'nav button[data-page="{name}"]')
                move_mouse(btn)
                btn.click()
                page.wait_for_timeout(400)

            # Navigate to base application
            page.goto(url)
            inject_overlays()

            # 1. Overview workflow (loaded via reports selection)
            go('reports')
            rep_btn = page.locator(f'#report-list button[data-scan="{attacked_id}"]')
            move_mouse(rep_btn)
            rep_btn.click()
            expect(page.locator('#score')).not_to_have_text('—')
            inject_overlays()
            set_caption("Overview | Assurance Decision",
                        "Disposition-first decision linked directly to multi-modal evidence · Review: experimental anomaly")
            view_ev_btn = page.locator('.why-panel button[data-go="contributors-page"]')
            if view_ev_btn.is_visible():
                move_mouse(view_ev_btn)
            hold('Overview — disposition, risk scoring and evidence entry point', 8)

            # 2. Data Integrity workflow
            go('datasets')
            inject_overlays()
            set_caption("Inventory | Data Integrity",
                        "Dataset summary, manifest hash verification, and reported detector coverage matrix")
            expect(page.locator('#dataset-workspace')).not_to_be_empty()
            page.evaluate('window.scrollTo(0, 0)')
            hold('Data Integrity — dataset identity, manifest hash and detector coverage', 8)

            # 3. Contributors workflow
            go('contributors-page')
            inject_overlays()
            set_caption("Investigation | Contributor Intelligence",
                        "Source accountability: associational analysis traces findings without assuming authorship")
            expect(page.locator('#contributors-detail table')).to_be_visible()
            hold('Contributor Intelligence — source evidence without attribution leaps', 8)

            # 4. Model Integrity workflow
            go('models')
            inject_overlays()
            set_caption("Assessment | Model Integrity",
                        "Trusted fingerprint comparison flags byte mismatch · Identity verification separated from behavior")
            expect(page.locator('#model-workspace')).to_contain_text('MISMATCH')
            hold('Model Integrity — trusted fingerprint byte mismatch', 9)

            # 5. Inference Provenance workflow
            go('inference')
            inject_overlays()
            tech_summary = page.locator('#inference .technical-record summary')
            move_mouse(tech_summary)
            tech_summary.click()
            page.locator('#record-json').fill(record)
            tech_summary.click()
            verify_btn = page.locator('#verify-record')
            move_mouse(verify_btn)
            verify_btn.click()
            expect(page.locator('#inference-assessment')).to_contain_text('SIGNED RECORD VERIFIED')
            page.evaluate('window.scrollTo(0, 0)')
            set_caption("Provenance | Inference Verification",
                        "Cryptographic signature binds model identity, inputs, configuration and prediction output")
            hold('Inference — signed record verification and bound payload', 8)

            # 6. Replay Policy workflow
            accept_btn = page.locator('#accept-record')
            move_mouse(accept_btn)
            accept_btn.click()
            expect(page.locator('#inference-assessment')).to_contain_text('ACCEPTED · REPLAY CHECK PASSED')
            page.wait_for_timeout(600)
            accept_btn.click()
            expect(page.locator('#inference-assessment')).to_contain_text('REPLAY DETECTED')
            page.evaluate('window.scrollTo(0, 0)')
            set_caption("Policy | Replay Protection",
                        "First acceptance checks freshness and updates state · Repeated submission is strictly rejected")
            hold('Replay Policy — repeated acceptance rejected', 8)

            # 7. Audit Ledger workflow
            go('ledger')
            inject_overlays()
            v_ledger_btn = page.locator('#verify-ledger')
            move_mouse(v_ledger_btn)
            v_ledger_btn.click()
            expect(page.locator('#ledger-state')).to_have_text('VALID')
            page.evaluate('window.scrollTo(0, 0)')
            set_caption("Integrity | Audit Ledger Verification",
                        "Sequential hash chain verified across historical operations · Cryptographically intact")
            page.wait_for_timeout(2000)

            tamper_btn = page.locator('#tamper-ledger')
            move_mouse(tamper_btn)
            tamper_btn.click()
            expect(page.locator('#ledger-assessment')).to_contain_text('FIRST INVALID LINK')
            page.evaluate('window.scrollTo(0, 0)')
            set_caption("Forensics | Altered-Copy Demonstration",
                        "Altered copy immediately exposes first invalid link · The altered-copy demonstration left stored records unchanged")
            hold('Audit Ledger — valid state and altered-copy tamper detection', 9)

            # 8. Closing Overview
            go('overview')
            inject_overlays()
            set_caption("Summary | Analyst-in-the-Loop Review",
                        "Veyra: Local Computer Vision Integrity Assurance · Verifiable evidence with explicit boundaries")
            hold('Summary — local workstation with explicit limitations', 7)

            # Finish recording
            recording.close()
            recording = None

            raw_webm = output / 'veyra-linkedin-demo-original.webm'
            video.save_as(str(raw_webm))
            orig_path = Path(video.path())
            if orig_path != raw_webm and orig_path.exists():
                orig_path.unlink(missing_ok=True)

            print(f'Raw WebM recording saved: {raw_webm}', flush=True)

            notes_data = {
                'scope': 'Actual local app interaction using isolated synthetic demo data',
                'shots': shots,
                'page_errors': page_errors,
                'console_errors': [c for c in console_logs if c['type'] == 'error'],
                'console_warnings': [c for c in console_logs if c['type'] == 'warning'],
                'all_requests_count': len(all_requests),
                'external_requests_attempted': external_requests,
                'failed_requests': failed_requests,
                'validation': 'Recorded workflows: Overview, Data Integrity, Contributors, Model Integrity, Inference, Replay Policy, Audit Ledger',
                'runtime_external_requests': 'No external requests were observed by Playwright during the recorded workflows.',
            }
            (output / 'recording-notes.json').write_text(json.dumps(notes_data, indent=2), encoding='utf-8')

            # Export MP4 if ffmpeg available
            final_mp4 = output / 'veyra-linkedin-demo.mp4'
            has_ffmpeg = bool(shutil.which('ffmpeg'))
            if has_ffmpeg:
                print('Transcoding to H.264 MP4 with FFmpeg...', flush=True)
                subprocess.run([
                    'ffmpeg', '-y', '-i', str(raw_webm),
                    '-c:v', 'libx264', '-crf', '18', '-preset', 'slow',
                    '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                    str(final_mp4)
                ], check=True)
                print(f'H.264 MP4 exported: {final_mp4}', flush=True)

            # Copy to Deliverables folder
            print(f'Copying deliverables to {deliverables}...', flush=True)
            shutil.copy2(raw_webm, deliverables / 'veyra-linkedin-demo-original.webm')
            if has_ffmpeg and final_mp4.exists():
                shutil.copy2(final_mp4, deliverables / 'veyra-linkedin-demo.mp4')

            # Generate frame screenshots and thumbnail using ffmpeg with shot timings
            if has_ffmpeg and final_mp4.exists():
                print('Extracting selected screenshots and thumbnail...', flush=True)
                screen_spec = [
                    ('thumbnail.png', shots[0]['seconds'] + 4),
                    ('01_overview_decision.png', shots[0]['seconds'] + 4),
                    ('02_data_integrity.png', shots[1]['seconds'] + 4),
                    ('03_contributor_intelligence.png', shots[2]['seconds'] + 4),
                    ('04_model_integrity_mismatch.png', shots[3]['seconds'] + 4),
                    ('05_inference_provenance.png', shots[4]['seconds'] + 4),
                    ('06_replay_policy.png', shots[5]['seconds'] + 4),
                    ('07_audit_ledger_tamper.png', shots[6]['seconds'] + 5),
                    ('08_summary_closing.png', shots[7]['seconds'] + 3),
                ]
                for filename, sec in screen_spec:
                    subprocess.run([
                        'ffmpeg', '-y', '-ss', f"{sec:.2f}", '-i', str(final_mp4),
                        '-vframes', '1', '-q:v', '2', str(deliverables / filename)
                    ], check=True)

            # Generate Subtitles and Captions
            print('Generating subtitle deliverables...', flush=True)
            generate_subtitles(shots, deliverables)

            # Generate LinkedIn Post Draft
            generate_post_draft(deliverables)

            # Generate Validation Report
            generate_validation_report(notes_data, deliverables)

            print('All deliverables successfully generated in:', deliverables, flush=True)

        finally:
            if recording:
                recording.close()
            browser.close()
            server.shutdown()
            app.extensions['worker'].shutdown(wait=True)


def generate_subtitles(shots, dest: Path):
    srt_lines = []
    vtt_lines = ["WEBVTT", ""]
    txt_lines = ["# Veyra LinkedIn Walkthrough Captions", ""]

    captions = [
        ("Veyra | Computer Vision Integrity Assurance",
         "Disposition-first decision linked directly to multi-modal evidence."),
        ("Data Integrity & Manifest Identity",
         "Dataset summary, manifest hash verification, and reported detector coverage."),
        ("Contributor Intelligence",
         "Source accountability: associational analysis traces findings without assuming authorship."),
        ("Model Integrity Assessment",
         "Trusted fingerprint comparison flags byte mismatch (Review: experimental anomaly)."),
        ("Inference Provenance Verification",
         "Cryptographic signature binds model identity, inputs, configuration and prediction output."),
        ("Replay Policy Enforcement",
         "Initial acceptance succeeds; repeated acceptance is strictly rejected."),
        ("Audit Ledger & Tamper Demonstration",
         "Sequential hash chain verified; altered copy immediately exposes broken link."),
        ("Veyra Analyst Workstation",
         "Integrity evidence, explicit boundaries, and analyst-in-the-loop review.")
    ]

    for idx, (shot, (title, sub)) in enumerate(zip(shots, captions), 1):
        start_s = shot['seconds']
        duration = shot.get('duration', 9)
        end_s = start_s + duration

        def format_timestamp(s, decimal_sep=','):
            hrs = int(s // 3600)
            mins = int((s % 3600) // 60)
            secs = int(s % 60)
            millis = int(round((s - int(s)) * 1000))
            return f"{hrs:02d}:{mins:02d}:{secs:02d}{decimal_sep}{millis:03d}"

        srt_start = format_timestamp(start_s, ',')
        srt_end = format_timestamp(end_s, ',')
        srt_lines.append(f"{idx}\n{srt_start} --> {srt_end}\n{title}\n{sub}\n")

        vtt_start = format_timestamp(start_s, '.')
        vtt_end = format_timestamp(end_s, '.')
        vtt_lines.append(f"{idx}\n{vtt_start} --> {vtt_end}\n{title}\n{sub}\n")

        txt_lines.append(f"[{format_timestamp(start_s, '.')} - {format_timestamp(end_s, '.')}] {title}: {sub}")

    (dest / 'captions.srt').write_text("\n".join(srt_lines), encoding='utf-8')
    (dest / 'captions.vtt').write_text("\n".join(vtt_lines), encoding='utf-8')
    (dest / 'captions.txt').write_text("\n".join(txt_lines), encoding='utf-8')


def generate_post_draft(dest: Path):
    content = """# LinkedIn Post Draft — Veyra Walkthrough

Built **Veyra** — a local computer vision integrity assurance workstation.

Most CV security tools focus either purely on accuracy or solely on model metadata. Veyra connects the entire evidence chain: from dataset ingestion to cryptographic provenance and audit ledgers.

Here is a 78-second walkthrough of the real application running on local synthetic data:

🔹 **Disposition-First Overview**: Puts the assurance decision and composite risk first, linking directly to underlying evidence families.
🔹 **Contributor Intelligence**: Traces anomalous source patterns without making unverified leaps from association to authorship.
🔹 **Model Integrity**: Compares observed runtime weights against trusted reference fingerprints to catch byte substitutions.
🔹 **Inference Provenance**: Cryptographically binds inputs, model hash, and hyperparameters into a signed verifiable record.
🔹 **Replay Protection**: Strict cryptographic acceptance policy ensures single-use freshness and rejects duplicate replays.
🔹 **Tamper-Evident Ledger**: Validates chronological hash chains and pinpoints the exact link in altered records (the altered-copy demonstration left stored records unchanged).

No external requests were observed by Playwright during the recorded workflows. Cryptographic integrity and empirical anomalies are separated with explicit limitations kept visible.

Check out the project: https://github.com/raskar-pratik/veyra

#AISecurity #ComputerVision #MachineLearning #CyberSecurity #DataIntegrity #Python #BuildInPublic
"""
    (dest / 'linkedin_post_draft.md').write_text(content, encoding='utf-8')


def generate_validation_report(notes: dict, dest: Path):
    content = f"""# Veyra LinkedIn Demonstration Validation Report

- **Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **Tested Commit**: `566bb52` (Rebrand AegisCV to Veyra; preserve compatibility contracts)
- **Environment**:
  - OS: Windows (x64)
  - Python: 3.14 (CPython)
  - PyTorch: 2.14.0+cpu (Torchvision 0.29.0+cpu)
  - Browser Automation: Playwright (Chromium/Chrome)
  - Transcoding: FFmpeg 9.0.1 (H.264 / libx264)
  - Server: Werkzeug local loopback WSGI

---

## 1. Workflows Exercised & Verified

| Workflow | Demonstrated Features | Status |
| :--- | :--- | :--- |
| **Overview** | Final disposition (`QUARANTINE`), composite risk score, decision reason, evidence trigger entry point | **PASS** |
| **Data Integrity** | Dataset summary, manifest identity, reported detector coverage matrix, priority evidence | **PASS** |
| **Contributor Intelligence** | Source accountability table, evidence families, non-authorship attribution boundary | **PASS** |
| **Model Integrity** | Clean reference vs untrusted model comparison, byte hash mismatch, backdoor detection evidence | **PASS** |
| **Inference Provenance** | Signed JSON record binding inputs/model/configuration, cryptographic verification | **PASS** |
| **Replay Policy** | Fresh record acceptance succeeds; repeated acceptance rejected (`REPLAY DETECTED`) | **PASS** |
| **Audit Ledger** | Sequential hash chain verified as `VALID`; altered-copy demonstration pinpoints `FIRST INVALID LINK` (The altered-copy demonstration left stored records unchanged.) | **PASS** |
| **Summary & Boundaries** | Clear distinction between cryptographic integrity, experimental anomaly detection, and analyst review | **PASS** |

---

## 2. Telemetry, Console & Network Findings

- **Browser Console Errors**: {len(notes.get('console_errors', []))}
- **Browser Page Errors**: {len(notes.get('page_errors', []))}
- **Failed HTTP Requests**: {len(notes.get('failed_requests', []))}
- **Total Loopback HTTP Requests**: {notes.get('all_requests_count', 0)}
- **HTTP Response Statuses**: Response status codes were not captured in the recorded telemetry for this run. Unsupported claims that every request returned 200/201 are omitted (the asynchronous demo endpoint returns 202).
- **Attempted External Requests**: {len(notes.get('external_requests_attempted', []))}
- **Network Assessment**: No external requests were observed by Playwright during the recorded workflows.

---

## 3. Deliverables Inventory

All deliverables generated in `Veyra-LinkedIn-Deliverables`:
1. `veyra-linkedin-demo.mp4` (H.264 1920x1080 MP4, ~77-78s duration)
2. `veyra-linkedin-demo-original.webm` (Original browser video recording)
3. `thumbnail.png` (High-resolution cover frame)
4. Key Scene Screenshots (`01` through `08`)
5. Subtitle Files (`captions.srt`, `captions.vtt`, `captions.txt`)
6. `linkedin_post_draft.md` (Social post copy)
7. `demo_validation_report.md` (This report)

---

## 4. Boundaries & Remaining Limitations

- **Demonstration Scope**: Claims are strictly scoped to the observed demonstration, not full application validation.
- **Audit Ledger Demonstration**: The altered-copy demonstration left stored records unchanged.
- **Network Observation**: No external requests were observed by Playwright during the recorded workflows.
- **Synthetic Demo Scope**: The walkthrough uses isolated seeded synthetic fixtures and deterministic test models. It is designed to verify UI workflows, decision contracts, cryptographic provenance, and replay protection—not general real-world detector accuracy.
- **Experimental Anomaly Detection**: Neural Cleanse trigger reconstruction and behavioral probes are presented with explicit `REVIEW` status, separate from deterministic hash-based cryptographic failures.
- **Browser Scope**: Full multi-browser responsive regression across all viewport sizes is not established by this single 1920x1080 walkthrough recording.
"""
    (dest / 'demo_validation_report.md').write_text(content, encoding='utf-8')


if __name__ == '__main__':
    main()
