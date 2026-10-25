# KIT-CENSUS -- why partition/core kits sign so slowly (generated 2026-10-25 00:43 PDT, KIT-CENSUS lane)

Read-only census. Two independent sources:
- **FS**: every ORFS run dir on epyc1/epyc2/epyc3/intel1/intel2 (/srv/opentallas-scratch*/claude/**, ~/wt, /tmp) with a stage
  log newer than 2026-10-22, collected by script (stage logs, Elapsed lines, kit run_<GOAL>.log, signoff/face_guard/sdc_lint
  json, live containers). Git-checkout copies of committed logs, copied corpora (kv/kvbind, qc/a0v8place, tok-ds/verify_*,
  cp1r10-base, routes/lbl) and spill duplicates removed -> **1059 runs, 1709 run-hours** (container wall-hours; jobs use 8-16
  cpus). All surviving runs start 10-24 00:00 or later: 10-22/23 run dirs were deleted (failed-job rule) or wiped with the
  old fleet. Per-run table: lanes/KIT-CENSUS-runs.tsv.
- **LANES**: 730 attempts recorded in lanes/*.md, HANDOFF.md and results/** on origin/main since 10-22, incl. deleted
  failures (sub-agent extraction, lanes/.kit-census-lanes.tsv). Covers 10-22/23 but wall times are mostly missing.

## 1. Headline

- Fleet ran **1059 kit/P&R runs in ~25 h** for **21 SIGNED runs** (FS; 18 s81, 3 qwen_kvsys) = 2% yield, **40 of 1709
  run-hours** went into runs that signed. LANES records 58 SIGNED since 10-22 (s81 31, qwen_compute 9, s81_head 7, kv 5,
  hbm 3, vehicle 3). **HBM: 427 runs, 136 kit types, 0 signed, 758 run-h.**
- A signing run is fast: **median wall 1.76 h (s81), 1.35 h (kv)**, GRT median 10 min, DRT 14 min. Slowness is not the tool
  runtime of good kits; it is (a) kits that were unsignable before P&R started, (b) unbounded GRT hold-repair loops that
  burn 3-12 h before someone kills them, (c) failures found at signoff that were visible at synth/CTS.
- **Attempts per signed kit: median 4** (FS, 21 kit types; slice stations 4-5, hrow 9; machine-h to sign 1-14 h; first run
  to signature span 1.3-12 h). Every LANES signature was the first *recorded* attempt of that view, but the FS shows the
  re-kits before it.
- **face_guard FAIL is cross-cutting: 418 of 1059 runs (763 run-h, 45% of all run-hours) ran with a failing face_guard**
  (HBM 331/427: run_kit_hbm.sh records the FAIL and continues by design). 132 of them were routed to GRT or beyond. None
  of these can ever sign. Fail kinds (runs): shared 126, dropped 108, feedthrough 35, unregistered 27.

## 2. Ranked causes (FS, failed/aborted sign-off attempts; probes that stopped at their GOAL excluded)

| # | cause | runs | wasted run-h | median time-to-fail h | detected at | earliest possible | dies |
|---|---|---|---|---|---|---|---|
| 1 | killed in GRT (FF-hold repair loop, superseded) | 91 | 299 | 4.71 | grt | cts (FF hold count after CTS) / plan (ft-chain hold) | hbm:59 s81:19 s81_head:7 qwen_kvsys:6 |
| 2 | runaway-stage (log grows, >6 h one stage: GRT FF-hold repair) | 13 | 158 | 11.75 | grt, place | cts / plan; watchdog for the rest | s81:10 hbm:3 |
| 3 | clock skew/spread > 80 ps | 30 | 116 | 3.09 | signoff | cts | s81:23 qwen_compute:5 s81_head:1 qwen_kvsys:1 |
| 4 | killed/superseded mid-stage | 106 | 86 | 0.21 | place, synth | - | s81:64 hbm:29 s81_head:5 qwen_kvsys:4 |
| 5 | routed, signoff not run/recorded | 33 | 78 | 2.22 | final | - | s81:21 s81_head:6 hbm:3 qwen_kvsys:3 |
| 6 | legacy ref_tile flow (unsignable, 9.13) | 48 | 76 | 0.71 | final | kit choice | qwen_kvsys:19 qwen_compute:10 s81:10 part-cap-study:5 |
| 7 | congestion / GRT overflow | 18 | 66 | 2.96 | grt | place (RUDY) / G2 probe | hbm:8 qwen_kvsys:8 qwen_compute:2 |
| 8 | rtl-boundary (face_guard) routed anyway | 37 | 61 | 1.60 | signoff | synth | qwen_kvsys:21 hbm:10 s81:5 s81_head:1 |
| 9 | FF hold (faces/ft chains) | 26 | 60 | 1.45 | signoff | grt (FF STA) / plan IO budget | s81:18 qwen_compute:5 qwen_kvsys:3 |
| 10 | TT setup | 23 | 57 | 1.56 | signoff | place/grt (G2 STA) | s81:19 qwen_kvsys:4 |
| 11 | tool/kit-script bug (missing file/LEF/GDS, bad kit) | 21 | 26 | 0.39 | synth, place | kit generation (static check) | hbm:8 s81:6 qwen_kvsys:6 part-cap-study:1 |
| 12 | rtl fanout > 64 routed anyway | 7 | 24 | 2.02 | signoff | synth | qwen_kvsys:6 hbm:1 |
| 13 | CTS failure (max buffer count) | 14 | 17 | 0.72 | cts | plan/synth (fanout, tap plan) | qwen_kvsys:6 hbm:5 s81:3 |
| 14 | placement divergence | 2 | 14 | 7.13 | place | floorplan (density) | hbm:1 qwen_kvsys:1 |
| 15 | DRV slew/cap | 4 | 11 | 2.19 | signoff | grt | s81:4 |
| 16 | plan geometry (macro/outline/pins/util) | 16 | 6 | 0.21 | floorplan, place | G0 plan check | hbm:11 s81:4 qwen_kvsys:1 |
| 17 | tool error other | 9 | 4 | 0.23 | synth, place | synth | hbm:4 s81:3 qwen_kvsys:2 |
| 18 | rtl-boundary (face_guard) | 39 | 3 | 0.01 | synth (after yosys) | RTL lint / port-bind (pre-synth) | s81:26 qwen_kvsys:11 qwen_compute:2 |
| 19 | infra (killed / OOM) | 8 | 3 | 0.32 | grt, synth | - | s81:6 hbm:2 |
| 20 | stalled (no log >2 h) | 3 | 2 | 0.66 | grt, synth | watchdog (now) | s81_head:2 s81:1 |
| 21 | rtl: memory not a macro (>SYNTH_MEMORY_MAX_BITS) | 8 | 0 | 0.06 | synth | RTL lint (2.7) | hbm:6 s81:2 |

Notes: rows 1-2 are one mechanism. 84 of the 104 killed/runaway GRT runs were inside `repair_timing` hold repair (last
log line = repair table with a DFF endpoint), median last WNS -31.8 ps, 94% worse than -20 ps; it inserts 2 buffers per
iteration (t27: 4694 hold endpoints, iteration 2960 after 11 h, WNS stuck at -58 ps on `u_ft_ft4_s0/q[27]`). The violators
are feedthrough-station flop chains (u_ft_ft*_s0) -- back-to-back ft registers whose FF hold is known from the plan.
Clock row: 25 of 30 are pin-flop *spread* > 80 ps, which BRIEFING #5 / ruling 9.2 made INFO; signoff.py still fails it
(only 1 run failed on spread alone: s81 slice_station__t11 kitsBmw, 86.5 ps -- would sign under the ruled gate).

### LANES view (730 attempts, incl. 10-22/23 and deleted failures)

| cause | attempts | detected at (top) | could be detected at (top) | dies |
|---|---|---|---|---|
| ff-hold-faces | 116 | grt 67, signoff 47 | **cts 110** | hbm 70, s81 21, kv 18 |
| plan-geometry (hop, stations in macros, pins, fill) | 67 | place 28, cts 16, floorplan 10 | **plan/G0 50** | s81 40, kv 12, hbm 11 |
| rtl-boundary (face_guard shared/unregistered/const) | 60 | synth 41, signoff 17 | synth 34, **plan/G0 25** | s81 32, kv 16 |
| tool/script bug | 59 | synth 15, signoff 15, place 13 | synth 34 | s81 26, kv 14, hbm 10 |
| CTS failure | 58 | cts 52 | **plan/G0 33**, cts 24 | hbm 32, kv 17 |
| TT setup | 56 | signoff 40, eco 10 | grt 16, plan/G0 15 | kv 23, s81 20, hbm 10 |
| killed/superseded | 55 | - | - | s81 27, kv 15 |
| sdc-lint | 30 | **signoff 29** | **synth 28** | kv 14, qc 13 |
| congestion/GRT overflow | 23 | grt 23 | place 18 | hbm 13, kv 7 |
| infra (OOM, host, ot-run) | 21 | synth/route | - | s81 11 |
| stalled | 21 | place 10, grt 8 | cts/place | s81 16 |
| DRT pin access/DRC | 7 | drt | - | |
| cell cap > 400k | 3 | synth | plan/G0C | |

Both sources agree: the top three are **FF hold at faces / ft chains**, **RTL boundary (face_guard)** and **plan geometry +
CTS failures that a plan check could catch**; each is detected 1-3 stages (and 1-12 h) later than it could be.

## 3. Per die (FS)

| die | runs | sign-off attempts | probes | running | SIGNED runs | kit types tried | types SIGNED | run-h total | median wall of a SIGNED run h |
|---|---|---|---|---|---|---|---|---|---|
| s81 | 396 | 262 | 128 | 6 | 18 | 98 | 18 | 597 | 1.755 |
| s81_head | 35 | 22 | 10 | 3 | 0 | 11 | 0 | 26 | - |
| qwen_compute | 43 | 24 | 2 | 17 | 0 | 35 | 0 | 33 | - |
| qwen_kvsys | 123 | 105 | 12 | 6 | 3 | 57 | 3 | 198 | 1.35 |
| hbm | 427 | 150 | 216 | 61 | 0 | 136 | 0 | 758 | - |
| fp32-study | 17 | 0 | 17 | 0 | 0 | 0 | 0 | 10 | - |
| part-cap-study | 13 | 10 | 0 | 3 | 0 | 10 | 0 | 85 | - |
| other | 4 | 4 | 0 | 0 | 0 | 4 | 0 | 1 | - |
| lec-test | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | - |

Signed kits (FS) and attempts to sign: s81 slice_station__t12/t15/t16/t17/t20/t21 (4-5 each, kitsB epyc1, ~7 h span),
t5 (4, intel1, 13.6 machine-h), dsdv_svc_sx_hrow_c (9), ot_s81sl_vq_lfp (4 of 7), ot_dsrom_su_hcpost_lane_pr_c (3),
legacy-r2..r6 dsfd_node_* / gunit_l4r/l5f / cfg7_seq (1-2); kv3_head_eighth_e1/e5/e7 ECO m8 (3-5).
Most-tried never-signed types: hbm svc_sm_xcal_rel_t 14, hbm svc_pc_ctrl_leaf_cfg_h9b 11 (21 run-h), kv3_hub_Ei 9 (21 h),
s81 slice_station__t7 9, kv3_io_ft_v1 7 (15 h), s81 col_h10_r0_p1__t1 7, slice_station__t11/t3/t29/t18 5-6 each (19-25 h).

## 4. Stage times (FS, minutes)

| stage | SIGNED runs median / max min | all runs that ran the stage: median / p90 min | n |
|---|---|---|---|
| synth | 0 / 4 | 1 / 16 | 1029 |
| floorplan | 1 / 5 | 3 / 17 | 849 |
| place | 5 / 24 | 16 / 48 | 827 |
| cts | 1 / 6 | 4 / 16 | 536 |
| grt | 10 / 298 | 32 / 213 | 435 |
| drt | 14 / 86 | 33 / 118 | 270 |
| final | 4 / 9 | 6 / 13 | 240 |

GRT is the only stage whose tail explodes (p90 213 min vs 10 min median for signed runs): FF-hold repair inside 5_1_grt.

## 5. Live at census time (stall_watch first run 00:37 PDT, see ~/coord/STALLS.txt)

217 running jobs; 4 STALLED (epyc2 s81-head elemA_rb_c9 3h05 and elemB_rb_c6 2h36 idle in 5_1_grt; epyc3 trial-qk
qc_cap_4b445d_ir_t4 IR 2h22; intel2 kv-cores eco kv3_head_eighth_e0/m8 1h32 in GRT) and 13 RUNAWAY (10 s81 elem-s81-st405
kitsB slice stations t3/t4/t8/t9/t10/t22/t25/t27/t29/t32 in GRT hold repair 10.4-11.2 h each, 2 hbm proto-cores GRT 10.4 h,
1 hbm idx_selector place 6.5 h). Owners: ELEM-S81, S81-HEAD, KVG3-CORES, TRIAL-QK, PROTO, ELEM-HBM -- nothing was killed.

## 6. Five changes that would most raise signatures/day

1. **Bound and replace GRT hold repair.** Cap `repair_timing -hold` (time limit ~45 min / max buffer %), and fix ft-chain
   FF hold structurally in the kit: deterministic delay cells / min-wire on back-to-back ft station flops (rule 5.8) generated
   from the plan, and report FF hold count+TNS right after CTS; fail fast if > ~500 endpoints or WNS < -20 ps. Recovers
   ~457 run-h/day of killed+runaway GRT (rows 1-2) and the 116 lane hold failures.
2. **Make face_guard (and sdc_lint, SELRANGE, port-bind) fail-closed before floorplan everywhere**, incl. run_kit_hbm.sh
   (today "verdict recorded, flow continues"), and add a pre-synth RTL boundary lint (every planned pin registered, no shared
   or constant pins). 418 runs / 763 run-h ran with a failing face_guard; sdc-lint was found at signoff 29 times.
3. **A static kit/plan check before submission (seconds, no ot-run)**: G0C + files/LEF/GDS present, macro list vs
   ADDITIONAL_LEFS, memories > SYNTH_MEMORY_MAX_BITS have macros, utilisation/outline sane, CTS tap plan sized (max buffer
   count), pins exist. Catches plan-geometry (67 + 16), tool/kit bugs (59 + 21), CTS RSZ-0060 (14) and SYNTH_MEMORY (8).
4. **Kill-switch for stalls/runaways + gate on the ruled clock check.** stall_watch now reports at 90 min; lanes should act
   on STALLS.txt each drive (and ot-run could add a per-stage wall budget). Switch signoff.py to related-pair skew + CPPR
   (ruling 9.2): spread-only failures are not failures.
5. **G2 prototype before route, with congestion/setup/hold readout, then route only kits that pass** (METHODOLOGY 7.6):
   setup failures (23 FS, 56 LANES) and GRT overflow (18/23) are visible at place/GRT in minutes but were found at
   signoff after a full route (median 1.5-3 h each). Pair with "fix the first failing gate structurally, then re-run" instead
   of parallel re-kits that all hit the same wall (median 4 attempts per signed kit; slice stations re-kitted 4-9 times).

## 7. Method / caveats
- wall_h = first stage start (log mtime - Elapsed) to last log mtime; stage minutes = sum of ORFS Elapsed (tmp logs: mtime - previous stage end).
- "killed in GRT" = run whose 5_1_grt.tmp.log stopped without a container (killed/superseded); 84/104 were in hold repair.
- Signoff "first failing gate" in flow order: face_guard > fanout > clock > hold_ff > setup_tt > drv.
- Scripts: rtx-pro ~/coord-scratch/kitcensus/{collect.py,collect2.py,analyse.py,classify.py,final.py}.

## 8. LANES addendum (weighted by n_attempts: 1166 attempts)
Outcomes: 24 SIGNED (19 real die kits), 535 FAIL, 328 killed/superseded, 124 running, 126 unknown (HBM probe waves), 29 stalled.
Causes (attempts / kit-h): tool-script-bug 167/152, ff-hold-faces 128/197, killed-superseded 115/98, plan-geometry 100/166,
rtl-boundary 73/105, infra 66/6, cts 64/59, tt-setup 62/116, sdc-lint 30/7, congestion 26/57, stalled 25.
205 of 535 FAILs were found at CTS or later although knowable at place or earlier; 208 were knowable at plan/G0.
Attempts to sign (lanes): vq_lfp 9 (~4.5 h), hrow 12 (~13 h), stations t5..t21 4 waves (~12 h from first wave),
kv head_eighth e1 8 / e5,e7 7 (~13-15 h, signed via m8 ECO). HBM: ~600 core attempts, 15 reached signoff, all 15 face_guard FAIL.
Why the GRT hold loops never converge (key evidence):
- ELEM-HBM.md:410 -- kit HOLD_SLACK_MARGIN=30: "1467 endpoints below 0 but 37822 below 30 ... ~20 it/min with a 4000-iteration
  cap, so it could never finish" (a flat repair margin far above the real violators = flow bug, not physics).
- S81.md:327 -- stations "t3/t4/t25/t32 ~7-8 h more, t27 ~11 h, t9 ~20 h, then DRT ~2 h"; GEOM-REVIEW.md:140 head c9/c6
  "blanket margin-45 repair over ~24k internal endpoints (stuck >3 h)".
- ELEM-HBM.md:421 "348 of 370 synthesized core kits fail [face_guard] ... cause is in the RTL"; ELEM-QK.md:237 "32/33 re-runs
  ALL NOT SIGNED ... sdc_lint 32, face_guard 26, FF hold 13".
- KVG3-CORES.md:42 / ELEM-HBM.md:392 -- make-print parse bug ("NAME:" not "NAME=") skipped signoff on finished kits.
- >= 6 mid-flight rule changes in 17 h (TT/FF, sdc_lint/face_guard, ft share 0.16, pair-skew gate, reset, DEC12) each forced re-kits;
  usage-limit gaps (08:50-12:04, 14:30-18:49 10-24) left finished runs uncollected.
Implication for change 1: set the hold repair margin to the sign-off hold margin (5 ps) + ft-chain delay cells, and stop at CTS
when endpoints-under-margin >> real violators.

## CODEX notes 2026-10-25 02:43 PDT
Historical census DONE; operational recipe findings retained (hold margin0..5; early preflight stop; postCTS trueFF structural stop). CLOCK/CP1 implementing common runner stop gates; no duplicate census.

## CODEX PARKED 2026-10-25 03:35 PDT
Claude reset order: safe park, no new jobs. Sources/jobs/results/failures/OWNER? recorded under Handoff to Claude 2026-10-25 03:35 PDT — GEOM/PROTO/toolchain in CODEX-LOG.md. Prototype strict SU channel job live; point SU done/uncollected. No main merges by this agent.
