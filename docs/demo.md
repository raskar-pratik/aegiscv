# Demonstration

1. Run `python run.py` and open the loopback dashboard.
2. Click **Run reproducible demonstration**. Wait for the completed assessment.
3. Open **Assurance reports** and choose the clean result: executed checks yield ACCEPT on the seeded fixture.
4. Choose the attacked result: Contributor-B is highest risk; expand duplicate, label and OOD findings. Model identity and probe outputs differ from the baseline. This produces QUARANTINE.
5. In **Audit ledger**, verify the live chain. It remains VALID.
6. Read **Reproducible attack results**: signed original VALID; modified output TAMPERED; second acceptance REPLAY; modified historical copy fails at sequence 1.
7. Open **Coverage matrix** to explain unavailable/research capabilities.
8. Export JSON or printable HTML from **Assurance reports**.

Synthetic images represent noisy RGB classes with seed 26228. Injected cases: three label flips, six duplicate copies, four OOD images, and four corner-patched images. Models are deterministic color classifiers; the compromised version adds a corner-trigger response. These are executable fixtures, not trained benchmarks.

The suite computes confusion counts and precision/recall/F1/FPR for duplicate, label and OOD signals. Original duplicate-group members count as false positives under the injection-only ground truth, deliberately exposing the attribution limitation. Ground truth is used only by evaluation, not by detectors.

Standalone: `python -m demo.runner --output demo/results-new`. This writes datasets, models, both reports and `evaluation.json`. The output directory must not exist. Browser checks: with the server running and local Playwright/Edge installed, `python scripts/browser_check.py`.

Hardening adds a separate six-class, differentiable patch-backdoor fixture to the existing demo. Read `backdoor_validation` in the measured demo results for clean accuracy, ASR, recovered target/mask norm/success, median/MAD and anomaly index. Full per-target masks/patterns and results are saved in the demo directory's `backdoor_validation/`. The fixture's clean labels are known; ASR excludes already-target-class samples. It is a detector-validation fixture, not a trained CV benchmark.

## Presenting the scientific validation

Keep the live demonstration above, then open `experiments/results/final_validation/VALIDATION_REPORT.md`. Clearly separate the original easy trusted fixture from the new 300-image held-out benchmark. Show deterministic signature tampering, replay and model identity checks first. Present exact-duplicate and OOD measurements with their synthetic-data scope and denominators.

Show the backdoor robustness confusion counts alongside clean accuracy and ASR; do not present the original successful reconstruction as universal reliability. The generated benchmark exposes near-duplicate false positives, benign contributors inheriting those false alarms, a missed brightness/blur shift, and non-monotone fusion. Keep those limitations visible. Semantic ablation remains unavailable until a trusted local checkpoint is provisioned. No dashboard redesign or fabricated aggregate accuracy is needed.
