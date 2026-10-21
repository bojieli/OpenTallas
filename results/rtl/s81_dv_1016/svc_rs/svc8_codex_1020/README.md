# SVC8 takeover collection, 2026-10-20

Source parent: 1608647da (hgrp8 RTL 91dbe80f8).

- sop2: all eight production ST2 SO and SVCRS verdicts PASS, replayed immutable completed binary; binary SHA256 recorded.
- solp2: all eight release SO+PINREG+landed-parent+hard-group ST2 SO and SVCRS verdicts PASS. This tests the original hard group; hgrp8 replacement lockstep witnesses remain in svc8_1020.
- prod_s2: eight raw production ST2 verdicts PASS (wrapper remains open).
- solp0: ST0 release baseline FAIL, tail PV errors48 while SO passes; cannot certify ST0 mutant pair.
- prod_s0: ST0 engine FAIL PV errors128, first_fault_code00080000, score/selection errors0.
- solpm2: expected FAIL but ST0 baseline also fails; preserved as diagnostic, not qualified causal witness.
- sop0: shell-offset INFRA after executable built; read-only recovery launched separately.
- original native wrapper: missing tools/textbook_lint.py import, erroneously wrapper exit0. Failed log preserved unchanged. Recovery runs map census against existing mapped files then bound/retain without map synthesis.

All original 15 entries in source_identity.sha256 verified on fleet before recovery. Recovery source is separate; original source and map are read-only. No native acceptance or layout claim until retained census PASS.
