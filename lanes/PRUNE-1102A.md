# PRUNE-1102A — scratch2 recovery intel2 / epyc2 / intel1

Lane brief (COORD 11-02): intel2 scratch2 96%, epyc2 93%, intel1 92%; target <=85% (done at <=88%).

## Method (2026-11-02 18:35 PST)
- Reference scan per host (receipts on each host under /srv/opentallas-scratch2/claude/prune-1102a/): every absolute
  /srv/opentallas-scratch2 path in *.f/*.mk/*.json/*.tcl/*.sh/*.py/*.yaml/*.cfg (<5 MB) on that scratch, plus
  ~/coord lanes/*.md, autopilot/*.tsv/json, RELEASE_TREE*, COORD-REVIEW-QUEUE, PROTECTED-DBS, Codex checkpoint
  20261102_0158, and the central repo (git grep HEAD). Live = /proc cwd/fd/argv on all hosts + localhost argv + docker mounts.
- A unit is eligible only if: no .keep in it or any ancestor; not in PROTECTED-DBS; no ref from outside the unit;
  not live; nothing modified <24 h; name not tok-*/kv-fn-*/codex-ds-*/veh*/signed*/closed/autopilot; canary runs on a
  flow-* tagged sha excluded (150 tag shas). Codex-preserved dirs (geometry_disk.md: flow hold, signed/provenance) excluded.
- Deletion class 1: generated *.odb/*.spef/*.def/*.gds/*.vcd/*.fst only (receipts, logs, reports, netlists kept) in
  eligible flow-canary runs. Per-file manifest: <host>:.../prune-1102a/<host>_del_*.tsv.
- Move class (epyc2): idle (>24 h), not live, no .keep, referenced dirs -> rsync -aHAX to epyc2 root scratch
  /home/ubuntu/scratch-root/claude/<same name>, verify bytes+file count, then replace with a symlink (paths keep working).
- wt-reaper (infra, every 30 min, --apply) already handles clean pushed worktrees; this lane does not touch worktrees it keeps.

## epyc2 manifest (planned 2026-11-02 18:35 PST)
### delete (generated DBs in eligible, untagged canary runs; 10.5 GB, 82 files)
| unit | GB | files | newest |
|---|---|---|---|
| flow-canary/runs/hbm_02a91da3c_1031_123734_109363 | 1.63 | 14 files | newest 2026-10-31 13:29 |
| flow-canary/runs/hbm_b3b607bc5_1031_152307_558537 | 1.63 | 14 files | newest 2026-10-31 16:27 |
| flow-canary/runs/qwen_kvsys_core_c96881d10_1031_145215_554131 | 3.21 | 25 files | newest 2026-10-31 17:43 |
| flow-canary/runs/s81_e5fff58bf_1101_002246_525551 | 3.60 | 15 files | newest 2026-11-01 01:50 |
| flow-canary/runs/s81_head_cl_abeaacad4_1101_010746_110045 | 0.44 | 14 files | newest 2026-11-01 01:19 |

### move to /home/ubuntu/scratch-root/claude + symlink
| dir | GB | newest file |
|---|---|---|
82 epyc2_del_canary.tsv
10.5081
| die-s81-46 | 8.44 | 2026-11-01 01:59 |
| die-kv-50 | 8.44 | 2026-11-01 04:25 |
| head-serdes-1 | 7.34 | 2026-10-31 15:09 |
| die-s81-45 | 3.74 | 2026-10-31 21:52 |
| codex-hbm-multitap-1101 | 3.73 | 2026-11-01 08:23 |
| codex-hbm-bind-restore-1101 | 3.88 | 2026-11-01 14:52 |
| codex-qc-cores-0815 | 2.28 | 2026-10-31 02:16 |
| die-kv-51 | 1.62 | 2026-11-01 04:25 |
| dh53-hostlec | 1.86 | 2026-11-01 08:12 |
| codex-head-serdes-repair-1101 | 4.54 | 2026-11-01 08:41 |
| codex-kv-hg-ex-recovery-1101 | 3.19 | 2026-11-01 09:49 |
| codex-qca0 | 2.93 | 2026-11-01 09:35 |
| codex-qc-slw-count-1101 | 1.65 | 2026-11-01 13:00 |

## Results
