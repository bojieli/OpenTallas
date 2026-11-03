# PRUNE-1102B — successor of PRUNE-1102A (scratch recovery intel2 / epyc2 / intel1)

## Takeover check (2026-11-02 22:26 PST)
- PRUNE-1102A manifests: intel2 47 units + intel1 62 units = all GONE (deleted before 19:5x). intel2 untagged-canary 1653 files done (i2_canary_del_result.tsv).
- NOT yet done at death: (a) intel2 superseded-tag canary DBs i2_oldtag_db.tsv (667 files, 88.46 GB) — still present; (b) intel1 i1_canary_big.tsv (112 files) — still present;
  (c) intel1 wt/codex-s81-1101 (37 GB) left untouched by 1102A (base unknown) — I keep it untouched.

## intel2 manifest A (COORD ruling 11-02 22:2x item 1): superseded flow-tag canary DBs
- Per-file manifest (size, mtime, path): intel2:/srv/opentallas-scratch2/claude/prune-1102a/i2_oldtag_db.tsv (667 *.odb/*.spef/*.def, 88.46 GB, 41 runs: hbm 6, qwen 21, s81 14).
- Reason: generated DBs in canary runs of superseded flow-* tag shas; kept tag shas (newest 2 per die, union) = 0499590af 2b01755d2 99172ad79 9db068b54 9e74a778c . Receipts/logs/reports kept.
- Re-verified 22:3x: run sha in superseded set, not live (/proc cwd/fd/argv), no docker mount, no .keep ancestor, not in PROTECTED-DBS, file mtime >24 h, no ref in coord files modified <24 h.
  Result log: .../prune-1102a/i2_oldtag_del_result_1102b.tsv (p2b_del.py).

## intel2 manifest A result (2026-11-02 22:47 PST)
- DELETED 667/667 files, 88.46 GB (i2_oldtag_del_result_1102b.tsv). intel2 103 -> 185 GB free.

## intel2 manifest B (2026-11-02 22:47 PST): untagged flow-canary runs (PRUNE-1102A class 1, re-evaluated fresh)
- Rule: run sha not on any flow-* tag (154 shas, fresh), newest file >24 h, not live (/proc + docker), no .keep/SIGNED*, not in protect.d/PROTECTED-DBS,
  no ref in refs.tsv outside the run and no run-name mention anywhere in ~/coord lanes/autopilot/RELEASE_TREE/PROTECTED-DBS. Only *.odb/*.spef/*.def/*.gds deleted.
- 462 runs eligible (most already DB-free); 122 files 11.87 GB. Per-file manifest (size, mtime, path): intel2:.../prune-1102a/i2_untag_db_1102b.tsv; per-run verdicts i2_untag_runs_1102b.tsv.

## intel1 manifest C (2026-11-02 22:47 PST): finish PRUNE-1102A i1_canary_big.tsv
- Only *.odb/*.spef/*.def of that list (64 files, 1.78 GB; .v/.csv/.map/.lib kept), untagged sha, >24 h, not live, no .keep. Result intel1:.../prune-1102a/i1_canary_del_result_1102b.tsv.
