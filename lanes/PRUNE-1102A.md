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

## intel2 manifest (URGENT, 2026-11-02 19:02 PST) — delete whole eligible units (all rules above; additionally no .git/PROVENANCE.json/*signoff*.json/SIGNED*/.keep inside, >=0.2 GB)
| GB | newest | path |
|---|---|---|
| 0.77 | 2026-11-01 11:48 | /srv/opentallas-scratch2/claude/codex-caprt-1101/A40R20 |
| 1.60 | 2026-11-01 08:17 | /srv/opentallas-scratch2/claude/codex-head-spn-g5-1101/band32_proposal |
| 3.16 | 2026-11-01 07:41 | /srv/opentallas-scratch2/claude/codex-head-spn-g5-1101/kit |
| 0.42 | 2026-11-01 14:07 | /srv/opentallas-scratch2/claude/codex-qc-q4-official64-1131/out |
| 0.50 | 2026-11-01 11:33 | /srv/opentallas-scratch2/claude/codex-qc-q4-spill64/out |
| 0.50 | 2026-11-01 15:46 | /srv/opentallas-scratch2/claude/codex-qc-su/l1_snapshot_diag1131 |
| 0.28 | 2026-11-01 06:48 | /srv/opentallas-scratch2/claude/codex-s81-cohort-1101/peco |
| 0.44 | 2026-11-01 15:45 | /srv/opentallas-scratch2/claude/codex-s81-l4fanout-1535 |
| 0.79 | 2026-11-01 15:45 | /srv/opentallas-scratch2/claude/codex-s81-t41-ownership-r3-1546 |
| 0.40 | 2026-10-31 22:25 | /srv/opentallas-scratch2/claude/dh50-hostlec/lec_C |
| 0.24 | 2026-10-28 14:08 | /srv/opentallas-scratch2/claude/die-hbm-10/c23r_s |
| 0.42 | 2026-10-29 14:48 | /srv/opentallas-scratch2/claude/die-head-31/ctl_canary |
| 2.29 | 2026-10-29 17:47 | /srv/opentallas-scratch2/claude/die-head-33/rekit |
| 0.38 | 2026-10-31 09:50 | /srv/opentallas-scratch2/claude/die-qc-52/gen54v1 |
| 0.38 | 2026-10-31 09:42 | /srv/opentallas-scratch2/claude/die-qc-52/gen54v2 |
| 0.38 | 2026-10-31 16:32 | /srv/opentallas-scratch2/claude/die-qc-52/gen55b |
| 0.38 | 2026-10-31 17:52 | /srv/opentallas-scratch2/claude/die-qc-52/gen55c |
| 1.70 | 2026-10-31 12:12 | /srv/opentallas-scratch2/claude/die-qc-52/r54v1 |
| 1.70 | 2026-10-31 12:12 | /srv/opentallas-scratch2/claude/die-qc-52/r54v2 |
| 1.81 | 2026-10-31 19:51 | /srv/opentallas-scratch2/claude/die-qc-52/r55a |
| 1.71 | 2026-10-31 17:49 | /srv/opentallas-scratch2/claude/die-qc-52/r55b |
| 1.70 | 2026-10-31 18:47 | /srv/opentallas-scratch2/claude/die-qc-52/r55c |
| 0.70 | 2026-10-31 20:16 | /srv/opentallas-scratch2/claude/die-qc-57d/e3_nk |
| 0.68 | 2026-10-31 20:16 | /srv/opentallas-scratch2/claude/die-qc-57d/e3_nl |
| 0.70 | 2026-10-31 20:45 | /srv/opentallas-scratch2/claude/die-qc-57d/e6_nk |
| 0.64 | 2026-10-31 19:50 | /srv/opentallas-scratch2/claude/die-qc-57d/probe_nk |
| 0.63 | 2026-10-31 19:50 | /srv/opentallas-scratch2/claude/die-qc-57d/probe_nl |
| 0.40 | 2026-10-31 23:28 | /srv/opentallas-scratch2/claude/die-qc-58/gapsA2 |
| 0.28 | 2026-11-01 01:42 | /srv/opentallas-scratch2/claude/die-qc-58b/lec |
| 0.20 | 2026-10-31 23:03 | /srv/opentallas-scratch2/claude/die-qc-58l/lec_r8_diag |
| 0.27 | 2026-10-31 23:45 | /srv/opentallas-scratch2/claude/die-qc-58l/lec_rstc |
| 0.40 | 2026-11-01 08:20 | /srv/opentallas-scratch2/claude/die-qc-59c/main |
| 0.35 | 2026-11-01 13:26 | /srv/opentallas-scratch2/claude/die-qc-59e2/new |
| 0.93 | 2026-10-28 13:54 | /srv/opentallas-scratch2/claude/die-qc18-1028/nl |
| 1.37 | 2026-10-29 11:09 | /srv/opentallas-scratch2/claude/die-qc34/gridvias |
| 0.51 | 2026-10-28 08:46 | /srv/opentallas-scratch2/claude/die-s81-12/kit |
| 0.54 | 2026-10-27 21:18 | /srv/opentallas-scratch2/claude/die-s81-2/kit |
| 0.21 | 2026-10-24 08:14 | /srv/opentallas-scratch2/claude/geom-review/GR-QK |
| 0.21 | 2026-10-24 20:45 | /srv/opentallas-scratch2/claude/geom-review/tiles |
| 0.38 | 2026-10-31 21:44 | /srv/opentallas-scratch2/claude/hbm-cores-kits-38/opa_probe |
| 0.22 | 2026-10-27 04:15 | /srv/opentallas-scratch2/claude/infra-head4-1027/pylib |
| 1.82 | 2026-10-29 22:40 | /srv/opentallas-scratch2/claude/kf4/iqf |
| 0.23 | 2026-10-26 02:05 | /srv/opentallas-scratch2/claude/path-hbm/clk_0126 |
| 5.98 | 2026-10-30 17:47 | /srv/opentallas-scratch2/claude/qc-kits-aa/ck |
| 0.91 | 2026-10-27 16:43 | /srv/opentallas-scratch2/claude/qk-cores-6/ingest |
| 0.74 | 2026-10-29 19:17 | /srv/opentallas-scratch2/claude/s81-kits-a/plan2 |
| 10.95 | 2026-10-31 12:45 | /srv/opentallas-scratch2/claude/s81ck10/probe_l3 |
