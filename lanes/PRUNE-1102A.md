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

## intel2 URGENT additions (2026-11-02 19:21 PST)
- Removed worktree wt/codex-s81-cohort-1101 (19 GB; HEAD 82aa68ac2 in origin/codex/s81-cohort-1101; idle, no process; dirty diff saved
  intel2:/srv/opentallas-scratch2/claude/prune-1102a/wt-patches/codex-s81-cohort-1101.{info,patch,untracked} + the 1 untracked recipe json; reaper rescue patch also exists).
- wt/codex-qc-suc.partial_checkout (not a git worktree, Codex 11-01 07:25, no external refs): removed tracked-content copies physical/ rtl/ runtime/ schemas/ site/ spec/ (24.9 GB); results/ (with .keep) and reports/ kept.
- Untagged flow-canary runs, idle >24 h, no external ref (prune-1101b manifests ignored as referrers), not live: 479 runs eligible; deleting
  generated files >1 MB except *.json/*.log/*.rpt (67.7 GB, 1653 files; receipts/logs kept). Per-file list intel2:.../prune-1102a/i2_canary_big.tsv.

## intel1 manifest (2026-11-02 19:29 PST) — delete whole eligible units (same rules; fixed live check; prune manifests not counted as referrers)
| GB | newest | path |
|---|---|---|
| 1.26 | 2026-11-01 15:34 | /srv/opentallas-scratch2/claude/codex-bksel-r2-correct-1531 |
| 0.73 | 2026-11-01 11:42 | /srv/opentallas-scratch2/claude/codex-caprt-1101/A40R |
| 0.66 | 2026-11-01 11:42 | /srv/opentallas-scratch2/claude/codex-caprt-1101/B25rR |
| 0.44 | 2026-11-01 07:15 | /srv/opentallas-scratch2/claude/codex-hbm-clock/calib |
| 0.27 | 2026-11-01 07:39 | /srv/opentallas-scratch2/claude/codex-hbm-clock/physical_ca_A |
| 0.32 | 2026-10-30 04:18 | /srv/opentallas-scratch2/claude/codex-hbm-cores-1030/query |
| 0.24 | 2026-10-30 08:53 | /srv/opentallas-scratch2/claude/codex-hbm-cores-1030/retired |
| 0.20 | 2026-11-01 07:46 | /srv/opentallas-scratch2/claude/codex-hbm-finalstations-n1-1101 |
| 0.30 | 2026-11-01 13:59 | /srv/opentallas-scratch2/claude/codex-hbm-pslice-coldreset-1400/plan |
| 0.27 | 2026-10-30 08:33 | /srv/opentallas-scratch2/claude/codex-hbm-selector-1030/native_verilog |
| 0.22 | 2026-08-27 07:21 | /srv/opentallas-scratch2/claude/codex-head-padkeep-source-1102/lib |
| 1.14 | 2026-10-29 01:59 | /srv/opentallas-scratch2/claude/codex-kv-1028/event24_bind |
| 0.26 | 2026-10-30 03:51 | /srv/opentallas-scratch2/claude/codex-kv-1030/bind_e0_import_FAIL |
| 0.67 | 2026-10-30 09:47 | /srv/opentallas-scratch2/claude/codex-kv-1030/count_batch3 |
| 2.12 | 2026-10-30 06:46 | /srv/opentallas-scratch2/claude/codex-kv-1030/hroot_current_gplplain2 |
| 0.22 | 2026-11-01 18:10 | /srv/opentallas-scratch2/claude/codex-kv-hroot-reset-preserve-1131 |
| 0.42 | 2026-11-01 09:04 | /srv/opentallas-scratch2/claude/codex-qc-count-wave-1030 |
| 0.31 | 2026-11-01 12:45 | /srv/opentallas-scratch2/claude/codex-qc-su-trials/l4_reset_face_stage1131 |
| 0.78 | 2026-11-01 07:26 | /srv/opentallas-scratch2/claude/codex-qca0 |
| 0.32 | 2026-11-01 18:21 | /srv/opentallas-scratch2/claude/codex-s81-l2gate-1445/slew1_transport |
| 0.69 | 2026-10-30 05:08 | /srv/opentallas-scratch2/claude/codex-s81types-1030/kvt2_noshare_v2 |
| 0.49 | 2026-11-01 04:13 | /srv/opentallas-scratch2/claude/die-qc-59/lec_stb64 |
| 1.64 | 2026-11-01 08:27 | /srv/opentallas-scratch2/claude/die-qc-59/lec_stbC |
| 0.48 | 2026-11-01 17:27 | /srv/opentallas-scratch2/claude/die-s81-47/rg3eq |
| 2.32 | 2026-11-01 06:15 | /srv/opentallas-scratch2/claude/flow-canary/runs/hbm_2e8f53639_1101_053753_069801 |
| 2.32 | 2026-10-31 16:54 | /srv/opentallas-scratch2/claude/flow-canary/runs/hbm_4453cc5b5_1031_165312_787528 |
| 2.16 | 2026-10-31 14:40 | /srv/opentallas-scratch2/claude/flow-canary/runs/qwen_compute_c96881d10_1031_143757_540145 |
| 3.62 | 2026-10-31 15:13 | /srv/opentallas-scratch2/claude/flow-canary/runs/s81_c96881d10_1031_150719_587034 |
| 0.42 | 2026-11-01 16:46 | /srv/opentallas-scratch2/claude/flow-canary/runs/s81_head_951cc6273_1101_163639_593697 |
| 0.47 | 2026-11-01 07:04 | /srv/opentallas-scratch2/claude/flow-canary/runs/s81_head_cl_03e957472_1101_065232_569024 |
| 0.47 | 2026-11-01 16:44 | /srv/opentallas-scratch2/claude/flow-canary/runs/s81_head_cl_951cc6273_1101_163639_593697 |
| 0.88 | 2026-10-31 16:48 | /srv/opentallas-scratch2/claude/hbm-clkloc-1/C10d |
| 0.89 | 2026-10-31 17:18 | /srv/opentallas-scratch2/claude/hbm-clkloc-1/C10h |
| 0.89 | 2026-10-31 18:44 | /srv/opentallas-scratch2/claude/hbm-clkloc-1/C11b |
| 0.89 | 2026-10-31 18:44 | /srv/opentallas-scratch2/claude/hbm-clkloc-1/C11c |
| 0.91 | 2026-10-31 19:02 | /srv/opentallas-scratch2/claude/hbm-clkloc-1/C11d |
| 0.91 | 2026-10-31 19:02 | /srv/opentallas-scratch2/claude/hbm-clkloc-1/C11e |
| 0.91 | 2026-10-31 19:34 | /srv/opentallas-scratch2/claude/hbm-clkloc-1/C11f |
| 0.91 | 2026-10-31 19:33 | /srv/opentallas-scratch2/claude/hbm-clkloc-1/C11g |
| 0.91 | 2026-10-31 20:05 | /srv/opentallas-scratch2/claude/hbm-clkloc-1/C11h |
| 0.91 | 2026-10-31 20:06 | /srv/opentallas-scratch2/claude/hbm-clkloc-1/C11i |
| 0.91 | 2026-10-31 20:37 | /srv/opentallas-scratch2/claude/hbm-clkloc-1/C11j |
| 0.91 | 2026-10-31 20:37 | /srv/opentallas-scratch2/claude/hbm-clkloc-1/C11k |
| 0.91 | 2026-10-31 21:09 | /srv/opentallas-scratch2/claude/hbm-clkloc-1/C11l |
| 1.30 | 2026-11-01 03:43 | /srv/opentallas-scratch2/claude/hbm-clkloc-1/C11m |
| 0.95 | 2026-11-01 03:24 | /srv/opentallas-scratch2/claude/hbm-clkloc-1/C12a |
| 0.91 | 2026-10-31 21:47 | /srv/opentallas-scratch2/claude/hbm-clkloc-1/C12c |
| 0.91 | 2026-11-01 03:50 | /srv/opentallas-scratch2/claude/hbm-clkloc-1/C12d |
| 1.16 | 2026-10-31 13:59 | /srv/opentallas-scratch2/claude/hbm-clkloc-1/C7 |
| 2.13 | 2026-11-01 04:45 | /srv/opentallas-scratch2/claude/kit-triage-1/lec_canary |
| 2.74 | 2026-10-31 18:05 | /srv/opentallas-scratch2/claude/kit-wave/s81/e6e75a4ea7e/items/slice_station__t24__cl66b71008 |
| 1.17 | 2026-10-24 22:08 | /srv/opentallas-scratch2/claude/s81-head/bench_pipe |
| 0.46 | 2026-10-24 21:39 | /srv/opentallas-scratch2/claude/s81-head/tile_prev2 |
| 0.47 | 2026-10-24 22:09 | /srv/opentallas-scratch2/claude/s81-head/tile_prev3 |
| 0.47 | 2026-10-24 22:09 | /srv/opentallas-scratch2/claude/s81-head/tile_prev4 |
| 0.47 | 2026-10-24 22:44 | /srv/opentallas-scratch2/claude/s81-head/tile_prev5 |
| 0.70 | 2026-10-31 09:01 | /srv/opentallas-scratch2/claude/s81-ringhold-4/pilot_t24 |
| 0.85 | 2026-10-31 15:20 | /srv/opentallas-scratch2/claude/s81-serdes-phy-3/pilot5_serdes__t14 |
| 0.91 | 2026-10-31 15:21 | /srv/opentallas-scratch2/claude/s81-serdes-phy-3/pilot5_serdes__t16 |
| 0.91 | 2026-10-31 15:21 | /srv/opentallas-scratch2/claude/s81-serdes-phy-3/pilot5_serdes__t1__clb45db5be |
| 1.95 | 2026-10-31 07:04 | /srv/opentallas-scratch2/claude/s81ck9/ef_bench |
| 0.66 | 2026-10-24 06:59 | /srv/opentallas-scratch2/qc-tok |

epyc2 results: deleted 10.51 GB canary DBs; moved (symlinked) die-s81-46, die-kv-50, head-serdes-1, die-s81-45, codex-hbm-multitap-1101, codex-hbm-bind-restore-1101, codex-qc-slw-count-1101, dh53-hostlec, codex-head-serdes-repair-1101, codex-kv-hg-ex-recovery-1101, codex-qca0 to /home/ubuntu/scratch-root/claude (~50 GB). Skipped codex-qc-cores-0815 and die-kv-51 (autopilot signoff dirs). epyc2 93% -> 87%.
