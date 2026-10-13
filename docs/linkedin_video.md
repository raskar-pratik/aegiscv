# Record a real Veyra LinkedIn walkthrough

Status: recording helper prepared and syntax-checked; NOT browser-run in the authoring environment. No video has been produced here. Existing browser/visual-validation limitations remain unchanged.

## Windows setup

Use the `ui/tabler-refinement` branch and the project's installed virtual environment (Python 3.12 recommended). If the project is not installed yet, follow README.md to install requirements.txt and requirements-models.txt first.

```powershell
python -m pip install playwright
python scripts/record_linkedin_demo.py --channel chrome
```

Chrome must already be installed. Use `--channel msedge` for installed Microsoft Edge instead. The recorder does not download a browser, model, or dataset. No separate `python run.py` command is needed: it starts a loopback server with a temporary state directory and removes that demo state on exit. Your normal application state is not used.

The preparation stage runs the real seeded demonstration, which can take several minutes. Recording then uses real UI interactions to show Overview, Contributors, model hash mismatch, signed inference verification, replay rejection, valid ledger and an altered-copy failure. It records roughly 80–100 seconds, depending on local response times. Do not label this as general detector accuracy or production validation.

Output: `local_state/linkedin-video/<timestamp>/aegiscv-demo.webm`, plus recording-notes.json. If FFmpeg is on PATH, an H.264 MP4 is also created automatically. Otherwise import the WebM into your video editor and export MP4. Review the entire clip before posting; the notes report browser JavaScript errors, not complete visual or network regression results.

## Suggested edit

- Add a 2-second opening title: **Veyra | Computer Vision Integrity Assurance**.
- Keep a visible label: **Seeded synthetic demonstration**.
- Cut preparation/loading and long scroll transitions.
- End with: **Integrity evidence, explicit limitations, analyst review.**
- Target about 90 seconds with readable captions. No music is required.

## Voiceover

“Veyra is a local workstation for investigating computer-vision pipeline integrity. This walkthrough uses seeded synthetic data.

The overview puts the assurance decision first, then links it to the underlying evidence. Contributor investigations help trace suspicious findings without treating association as proof of authorship.

Model Integrity compares the observed model with a trusted fingerprint. Here, the returned byte hashes differ.

For inference, the signed record binds the input, model, preprocessing, configuration and output. Verification checks the protected record; it does not prove the prediction is correct or the model is benign.

Acceptance separately enforces replay policy. Trying to accept this record again is rejected.

The audit ledger verifies signed history. The altered-copy demonstration exposes the first invalid link and explains why later links cannot be trusted. Stored ledger records are unchanged.

Veyra combines integrity evidence with explicit limits—not a claim that every attack can be detected.”

## Suggested LinkedIn post

Built Veyra, a local computer-vision integrity assurance workstation.

This demo walks through contributor evidence, trusted model fingerprint comparison, signed inference verification, replay protection and audit-ledger checks.

The walkthrough uses seeded synthetic data. Cryptographic integrity checks and experimental anomaly evidence are presented separately, with limitations kept visible.

Repository: https://github.com/raskar-pratik/veyra

#AISecurity #ComputerVision #Python #CyberSecurity #BuildInPublic
