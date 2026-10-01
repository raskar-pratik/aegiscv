# Judge-facing UI freeze

The presentation layer is frozen for the SIH 26228 demo. The Flask API, detector algorithms, thresholds, calibration profiles, attack generator, risk fusion, and disposition policy remain unchanged.

The dashboard is offline-first and uses only local HTML, CSS, and JavaScript. It exposes the final disposition, decision trigger, composite and maximum asset risk, confidence, coverage, evidence details, contributor aggregation, model access status, signed inference provenance, ledger verification, replay protection, and printable reports.

Browser verification covers the reproducible demonstration, model registration, inference signing, valid verification, replay rejection, tampered inference detection, valid ledger verification, altered-copy ledger detection, coverage gaps, and screenshot capture at 1440×1000.

Interpretation remains explicit: heuristic scores are not calibrated probabilities, unavailable white-box checks remain unavailable, and cryptographic failures establish integrity violations.
