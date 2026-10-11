# GitHub publication record

Published through the authorized GitHub connector because shell Git has no credentials. Each staged content tree was verified to match its local Git tree exactly. GitHub commit metadata differs, so commit IDs differ. Historical logs retain their original local checkpoint IDs. The static checker now pins the same approved content trees, which remain reachable in the published history; no application or backend change was made for publication.

| Local checkpoint | GitHub commit | Verified tree |
| --- | --- | --- |
| cc7bada8f55068d78a4bbc34d69a69efe16f2a5e | 3ee8e4367622eedc7b065d8cb5f3c689c570d820 | ac6caf7e392419d4d889be9fc6c32614b858c1e3 |
| 20ee6ad7ff85e9a8b98b909010ca70791ac9b4d5 | 9cc0b6d4eb9c8698b8ba22f1ac759c0b1299c18f | 32941a00cb4568d22f5854f0f10f4ccb23b0a108 |
| e51c88d22c8aa5e14ce85326589d46ed0cc497a1 | 625a704702eda2588e2a513463b3a1ed63189a81 | 4dda0243fb10e3522da0372b60222e66f78d6edb |
| 78aaf9647921e6d2f3b610d14a7b6e005a4f5095 | 807e3746829224afe7137464b7dc7e1328d6e22a | b7e50bfbd7143684a93a633195261bca148d245d |
| 581cef0e4a998db0a2322656c39b6fbadf3461d6 | 25cca5f18370b92915c25b18e57ffd3e07bed942 | 1e9b17aa71377e01417f774599595a66c54975af |

50/50 baseline tests passed at Phase 6. Static checks pass with portable tree references. Visual validation remains PENDING, browser regression NOT RUN, runtime external requests NOT MEASURED. Branch: ui/tabler-refinement. Main is unchanged.

