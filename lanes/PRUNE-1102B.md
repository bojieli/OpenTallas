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

## epyc2 manifest D (2026-11-02 23:00 PST): MOVE (not delete) idle dirs to epyc2 root scratch + symlink (PRUNE-1102A move class)
- Rule: no .keep anywhere inside/above, newest file >24 h, not in PROTECTED-DBS/protect.d, not live (act.py rechecks /proc+docker before and after copy), rsync -aH, verify bytes+file count, rename+symlink, old copy removed. Root keeps >=500 GB free (2.4 TB free now).
| MB | newest | path -> /home/ubuntu/scratch-root/claude/<name> |
|---|---|---|
| 18103 | 2026-11-01 01:47 | /srv/opentallas-scratch2/claude/hbm-cores-kits-36 |
| 8978 | 2026-11-01 21:14 | /srv/opentallas-scratch2/claude/kt1-lec |
| 6568 | 2026-10-31 21:00 | /srv/opentallas-scratch2/claude/s81ck11cap |
| 5212 | 2026-11-01 18:54 | /srv/opentallas-scratch2/claude/kv60-ahpc |
| 5564 | 2026-11-01 00:44 | /srv/opentallas-scratch2/claude/hbm-cores-kits-37 |
| 5716 | 2026-10-31 15:33 | /srv/opentallas-scratch2/claude/hbm-cores-kits-26 |
| 4757 | 2026-10-30 02:00 | /srv/opentallas-scratch2/claude/kits10-1029 |

## epyc2 manifest D result (2026-11-02 23:12 PST)
- MOVED 6/7 (52.54 GB) to /home/ubuntu/scratch-root/claude with symlinks, verified; kits10-1029 skipped (live). epyc2 scratch2 104 -> 153 GB free (82%); root 2147 GB free.

## intel2 manifest E (2026-11-02 23:12 PST): DIE-HEAD-55 RELEASE 22:53 (die-head-48 .keep dir; owner-released paths only)
- 37 dirs + their .p1/.p2.log (96 entries, 89.15 GB): rtlgen_l48a, rtlgen_l48b_hd_st_{k5,n4}, rtlgen_l48r, rtlgen_l48g_hd_st_{turn,k5,n4}, rtlgen_l48w_hd_st_{turn,k5,n4}, rtlgen_l48c_hd_* (21), dh51spn, prd51, kits_l47{t,u,v}, tile51.
  Per-entry manifest (bytes, mtime, path): intel2:.../prune-1102a/i2_head_rel_1102b.tsv. Checked: newest file >24 h, not in protect.d/PROTECTED-DBS, not live.
- HELD BACK (not deleted, need DIE-HEAD-55 confirm): dh52spn (11.5 GB; prd53/hd_spn_end_D + dh53/v1/spn_{band,end} preflight.json name dh52spn/kits_spn2band/... as kit source) and tile52 (3.3 GB; codex-head-tilea-1131/kit/preflight.json names tile52/l48y/gen/hd_tile).

## intel2 manifest F (2026-11-02 23:12 PST): DIE-HBM-59 RELEASE 22:44
- hbm-cores-kits-40/wt (47.37 GB, worktree claude/hbm-cores-kits-40-hb4-1101@b26a827db, clean, only __pycache__ ignored) and wt_tm (32.59 GB, detached e5b857a7e, clean). Removed via git worktree remove --force from the central repo (registered worktrees wt3/wt_tm). Kept: tailmax, wt_d44q, nk, hold, hfdep, tnode, lecc, resign.

## manifest E/F results (2026-11-02 23:18 PST)
- E: removed 96/96 entries, 89.15 GB (i2_head_rel_1102b_result.tsv). F: git worktree remove --force wt + wt_tm (79.95 GB). intel2 -> 264 GB free.

## intel2 manifest G (2026-11-02 23:18 PST): FLOW-23 RELEASE 23:10
- flow-21/kcc/base/tree/physical (31.41 GB, newest 2026-11-01 14:43) and flow-21/kcc/tip/tree/physical (31.41 GB); plain repo copies, no PROTECTED path inside (results/ kept). Manifest intel2:.../prune-1102a/i2_flow21_rel_1102b.tsv.
