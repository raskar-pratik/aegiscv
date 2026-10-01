# AegisCV publication copy

## GitHub description

Offline computer-vision integrity assurance: dataset anomaly detection, contributor investigation, model fingerprinting, signed inference provenance, replay protection, and a tamper-evident audit ledger.

Suggested repository name: `aegiscv`

Suggested topics: `computer-vision`, `ai-security`, `data-integrity`, `model-security`, `digital-signatures`, `provenance`, `python`, `flask`.

## LinkedIn launch post

Introducing AegisCV — Computer Vision Integrity Assurance.

Can we trust the data, model, and evidence behind a computer-vision result?

AegisCV is a local analyst workstation that brings those checks into one investigation workflow:

- Dataset manifests, exact and near-duplicate detection, label anomalies, and out-of-distribution signals.
- Contributor investigations that correlate independent evidence families.
- Model identity and behavioral fingerprints, plus experimental backdoor investigation.
- Ed25519-signed inference provenance, nonce and sequence replay protection, and a tamper-evident audit ledger.
- Operational distribution-shift analysis and explicit evidence-coverage reporting.

One useful design lesson: an aggregate score should not hide a critical local finding. In the controlled malicious-contributor case, maximum asset risk reaches 100 and the disposition is QUARANTINE even though composite pipeline risk is 12.5.

The last recorded regression passed 50 tests. Browser verification recorded zero page errors and zero external requests. Runtime processing stays local.

The limits matter too: validation uses controlled synthetic fixtures, risk scores are not attack probabilities, and backdoor findings remain experimental evidence for analyst review.

I would welcome feedback on the investigation workflow and how to evaluate it against broader datasets and model families.

Repository: https://github.com/raskar-pratik/aegiscv

#ComputerVision #AISecurity #CyberSecurity #Python #MachineLearning

## LinkedIn Projects entry

Name: AegisCV — Computer Vision Integrity Assurance

Description: Built an offline analyst workstation for investigating dataset integrity, contributor risk, model identity, inference provenance, and audit history. Implemented SHA-256 manifests, anomaly detection, behavioral fingerprints, Ed25519 signing, replay protection, and a tamper-evident SQLite ledger. Includes a reproducible attack simulator, evidence-based decisions, and explicit limitations for experimental ML checks.

Skills: Python, Flask, Computer Vision, Machine Learning, Application Security, Cryptography, SQLite.

Project URL: https://github.com/raskar-pratik/aegiscv

## Publication boundaries

- Exclude local_state, work, caches, virtual environments, private signing keys, databases, raw recordings, and generated experiment model/checkpoint directories.
- Include source, tests, dependency lists, setup instructions, and reviewed documentation.
- Preserve measured results with their controlled-fixture scope. Do not claim military certification, production deployment, or general detection accuracy.
- Review screenshots before publishing: older final_ui captures contain superseded branding and local identifiers.
- Review the generated documentation before promoting it as final: the earlier DOCX, PDF, and Markdown contain different amounts of content and DOCX pagination was not visually verified.
- Choose a license explicitly before presenting the project as licensed open source.
