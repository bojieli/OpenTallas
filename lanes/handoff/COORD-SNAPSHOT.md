# COORD snapshot 2026-11-27 13:15 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: 2645bd5c4a8f
- 2026-11-27 09:50 PST MERGED [MERGE-QUEUE -> CLASS-OWNERS-R2] native-sram-path-authority@09079a689ee: nothing to land, 09079a689ee is an ancestor of main 81f48be7e98.
- 2026-11-27 09:50 PST MERGED [MERGE-QUEUE -> CLASS-OWNERS-R2] relay-seat-stop-runtime@08917427de8: nothing to land, 08917427de8 is an ancestor of main 81f48be7e98.
- 2026-11-27 10:35 PST MERGED [MERGE-QUEUE -> LEC-R2] lec-uneven-memory@5a7729a9c34: nothing to land, 5a7729a9c34 is an ancestor of main 3d76ea4f296.

## READY/ASK with no later COORD post naming them (5, heuristic: check each)
- 2026-11-27 00:25 PST READY [S81-GUNIT-RRL -> S81-INT-R2, COORD; cc OWNERS-SWEEP] Existing gunit__t1 owner S81-ALLFIX-INT remains valid on c085ccb76d2e. Old superseded cancellation is historical. Private c085 exact L1F physical-reset carry plan36bf82f075fd/asbuilt65947432d60d stock scoped strict PASS E7 oth-ubuntu-469544-1795767029 exit0 errors0 final native one type, saved ELAB and PRE. E7 cut2100/gunit-c085-owners
- 2026-11-27 01:21 PST READY [S81-GUNIT-RRL -> S81-INT-R2, COORD; cc TOKEN-DS] Exact private GUNIT 9a46c73ea6cb from 36bf82f075fd native PRE pass and strict one-type final errors0. Saved ELAB reused. Unit1578768 outer diagnostic rc1 came from unaccounted expected lane-age comment, corrected byte-readback on original output passed. Wrapper69ec884f3949 W266 LPAD D1->2. Scoped stock LAT actual 70->71 solely unit__seqhos
- 2026-11-27 01:29 PST ASK [S81-GUNIT-RRL -> S81-REGDROP, S81-INT-R2, COORD] One current GUNIT early place-only source/PVR request prepared at E12 s81-allfix-int/gunit-l5f-parent-phase-1127/gunit_l5f_source_pvr_launch_request.json. Stay held pending exact eligible child view, exact parent source seal/recipe and independent review. Existing L5f fceef46a7a78 local source is read-only and never duplicated. On historical
- 2026-11-27 02:57 PST READY [SIGNOFF-PROBE-REPLAY -> COORD, MERGE-QUEUE] codex/signoff-probe-replay-1127@fab88542aa644217e3ad387842fc3cce29e8174f GATE main=e5066ebdeba pass=5/5 (canonical merge queue receipt). Reject explicit diagnostic probes during sign-off replay. Five exact QC false preview receipts spanning three partitions excluded, genuine archive SIGNED and LOCAL_PASS_NEEDS_PARENT retained. No official runti
- 2026-11-27 09:47 PST ASK [QC-INT-R3 -> KV-INT-R3; cc COORD, CLASS-OWNERS-R3; class C-XDIE-ABI-MISMATCH] QC live is now 77f2cc98f662 (event qc_2100_combined_77f2_1126, applied 09:00:39), not C9; post-bind GREEN, bind_out qwen_compute_qc_join_2100_77f2_1126_bind_1127093611. Codex 22:00 found that the D/E stock C9 STATUS wrapper fails by default, with one OBS1_COMPAT source only. So QC plans NO producer change, and KV

## Lane handoff files (age) and last queue post
- CLAUDE-RESUME-1127: handoff 252 min old; last post none in recent queue
- EXPLORER-STORE-R1: handoff 747 min old; last post 2026-11-26 22:07 STATE
- HEAD-INT-R2-HOSTW-CAPACITY-1127: handoff 565 min old; last post none in recent queue
- PCC-B1-LANE-SPEC: handoff 115 min old; last post none in recent queue
- PREPARED-PUBLICATION-PLACE: handoff 842 min old; last post none in recent queue
- PUBLISH-GATE: handoff 747 min old; last post 2026-11-26 23:27 READY
- QC-ALLFIX-COLL: handoff 573 min old; last post none in recent queue
- ROM-WEIGHTS-1119: handoff 747 min old; last post 2026-11-26 23:36 STATE

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 195; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 56 live
- MERGE-QUEUE agent ? last post 2026-11-27 13:14 KNOWN-RED
- HEAD-INT-R3 agent ? last post 2026-11-27 13:14 DIED
- CLASS-OWNERS-R3 agent ? last post 2026-11-27 13:14 MEASURED
- S81-INT-R3-WAITER agent ? last post 2026-11-27 13:14 DIED
- QC-R3-STA agent ? last post 2026-11-27 13:13 REQUEST
- S81-INT-R3-BITORDER agent ? last post 2026-11-27 13:12 RESULT
- KV-INT-R3/FIRM agent ? last post 2026-11-27 13:12 RESULT
- KV-INT-R3/GPLTD agent ? last post 2026-11-27 13:10 RESULT
- KV-INT-R3 agent ? last post 2026-11-27 13:09 NOTE
- kv-int-r3 agent ? last post 2026-11-27 13:08 DIED
- HEAD-PROBE-R3 agent ? last post 2026-11-27 13:08 REVIEW
- QC-R3-LEG405 agent ? last post 2026-11-27 13:07 DIED
- S81-INT-R3-SEAM agent ? last post 2026-11-27 13:07 RESULT
- HEAD-EAST-R4 agent ? last post 2026-11-27 13:07 LANDED
- KIT-WAVE agent ? last post 2026-11-27 13:01 STATE
- SMELL-WATCH agent ? last post 2026-11-27 13:00 SMELL
- CLASS-TRACK-R3 agent ? last post 2026-11-27 12:59 RESULT
- FLEET-OPS-R5 agent ? last post 2026-11-27 12:55 DIED
- qwen_compute agent ? last post 2026-11-27 12:53 KIT-WAVE
- LEC-R3 agent ? last post 2026-11-27 12:51 DIED
- QC-R3-TAPS agent ? last post 2026-11-27 12:51 DIED
- QC-R3-SULANE agent ? last post 2026-11-27 12:51 DIED
- P-GEOM-INHERITED-MASK agent ? last post 2026-11-27 12:51 MEASURED
- KV-INT-R3/HUB agent ? last post 2026-11-27 12:49 RESULT
- QC-R3-DIEGAP agent ? last post 2026-11-27 12:48 START
- S81-INT-R3 agent ? last post 2026-11-27 12:41 FORM-RECOMPOSE
- S81-INT-R3-T31 agent ? last post 2026-11-27 12:38 C-T31-CS-GLOB
- QC-R3-TT agent ? last post 2026-11-27 12:37 DIED
- s81-int-r3-xr agent ? last post 2026-11-27 12:35 DIED
- NOPROG-FIX-1115 agent ? last post 2026-11-27 12:22 STATE
- mq1 agent ? last post 2026-11-27 12:21 DIED
- KV-INT-R3/PINENTRY agent ? last post 2026-11-27 12:19 RESULT
- CBC-RULES-1119 agent ? last post 2026-11-27 12:17 HOURLY
- NOPROG-WATCHDOG agent ? last post 2026-11-27 12:00 STATE
- KV-INT-R3/COMPOSE agent ? last post 2026-11-27 11:52 RESULT
- QC-R3-COLLS agent ? last post 2026-11-27 11:49 DIED
- PLAN-GATE-PRE-1115 agent ? last post 2026-11-27 11:44 NEEDS-ACTION
- KV-INT-R3/PROBEREV agent ? last post 2026-11-27 11:33 RESULT
- QC-R3-VISUAL agent ? last post 2026-11-27 11:32 DIED
- KV-INT-R3/LANDREACH agent ? last post 2026-11-27 11:31 RESULT
- FLEET-OPS-R agent ? last post 2026-11-27 11:26 ALERT
- TOKEN-R2 agent ? last post 2026-11-27 11:26 DIED
- QC-R3-TREERTL agent ? last post 2026-11-27 11:25 DIED
- OT-TOOLS-SYNC agent ? last post 2026-11-27 11:23 ALERT
- S81-INT-R3-PARAM agent ? last post 2026-11-27 11:22 DIED
- HEAD-TILE-R3 agent ? last post 2026-11-27 11:19 DIED
- S81-INT-R3-TAPLOAD agent ? last post 2026-11-27 11:12 DIED
- token-r2 agent ? last post 2026-11-27 11:12 DIED
- QC-R3-FTC agent ? last post 2026-11-27 11:05 DIED
- S81-INT-R3-VIEWS agent ? last post 2026-11-27 11:05 RESULT
- KV-INT-R3/SEATKEY agent ? last post 2026-11-27 10:59 RESULT
- QC-INT-R3 agent ? last post 2026-11-27 10:53 REPLY
- HOLDGEN-1115 agent ? last post 2026-11-27 10:30 ALERT
- C-FENCE-GEOM-ILLEGAL agent ? last post 2026-11-27 10:18 MEASURED
- C-OVERSIZE agent ? last post 2026-11-27 10:17 PUSHED
- C-TAP-LOAD agent ? last post 2026-11-27 10:17 PUSHED

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-27 13:15 PST)
count_hourly: signed any plan 608 | current plan 487 | deferred re-sign 20 (hbm 1, head 10, qc 6, s81 3) | retired-plan 101 (head 2, kv 13, qc 57, s81 29)
- [ ] FAIL.S81.CORES 71/72 signed · open: signed off, not counted 1 (dsdv_gunit_l5f)
- [ ] FAIL.S81.TYPES 48/402 signed · kit rows: cancelled (superseded) 194 (bk_sel__t2, +193) · held by die owner (plan event pending) 153 (col_h10_r0_p1__t1__cl574cc59d__pvd7af8531, +152)
- [ ] FAIL.HEAD.CORES 5/5 signed · open: none
- [ ] FAIL.HEAD.TYPES 25/27 signed · kit rows: running (lint advisory) 2 (hd_lep0N, +1)
- [ ] FAIL.QC.CORES 69/69 signed · open: none
- [ ] FAIL.QC.TYPES 81/127 signed · kit rows: held by die owner (plan event pending) 37 (cbf_q00__cl1b5a6458, +36) · cancelled (superseded) 1 (coll_ucie)
- [ ] FAIL.KV.CORES 84/84 signed · open: none
- [ ] FAIL.KV.TYPES 10/93 signed · kit rows: held by die owner (plan event pending) 42 (kv3_hg, +41) · running (lint advisory) 40 (kv3_hgi_v1__cl141fc26e, +39)
- [ ] FAIL.HBM.CORES 90/119 signed · open: no kit-wave row 19 (accel_smh_pt_w, hfd_coll_q3_body_ctl, hgi_sfu_opsa_group0, +12) · running, no result 9 (hfd_coll_q2n2_vm_core, hfd_hgi_vms_glue_nw_t, hgi_coll_tkm_m_tp192__root, +6) · shape: over cells/util/congestion 1 (hgi_dma_back_static_vp4_banks_cp
- [ ] FAIL.HBM.TYPES 4/81 signed · kit rows: none
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 1 current-event (+5 on a superseded plan block, not counted) (live check: ps/systemd/docker on all hosts; wave state: hub; full list lanes/STALE.tsv)
- [ ] STALE.QC 5 (cores 0, types 5) · by owner: QC-PLAN 2, KIT-WAVE-1 1, unowned 1, QC-STALE-GEOM 1
  - type sle_ctl__cla4f6f12f · CANCELLED geom QUEUE-CANCELLED @ 2026-11-23 11:21 (97.9h) · owner QC-PLAN
  - type sle_fw_v2__cl69f5e854 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-23 17:19 (91.9h) · owner QC-PLAN
  - type slw_fw_v1__clf51c11d8__cl592e3d37 · CANCELLED geom GHOST @ 2026-11-24 11:42 (73.6h) · owner unowned
  - type slw_fe_v1__clfe325744__cl08d14f0d · CANCELLED geom SUPERSEDED @ 2026-11-24 20:33 (64.7h) · owner QC-STALE-GEOM
  - type coll_ucie · CANCELLED geom QUEUE-CANCELLED @ 2026-11-26 09:19 (27.9h) · owner KIT-WAVE-1
- [ ] STALE.KV 1 (cores 0, types 1) · by owner: FAM-KV-HUBC-SYSC-R2 1
  - type kv3_sys_c · CANCELLED geom SUPERSEDED @ 2026-11-23 20:57 (88.3h) · owner FAM-KV-HUBC-SYSC-R2
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 295 commits / missing none
- TOOLS-LAG qwen_kvsys 332 commits / missing none
- TOOLS-LAG s81_head 0 commits / missing none
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 5274 taps in 50 types, 142 over 1650 sinks; insertion max 696 ps (p50 269, p90 284), skew max 176 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 596 taps in 6 types, 17 over 1650 sinks; insertion max 516 ps (p50 258, p90 289), skew max 208 ps; oversized taps: ins max 412 ps, skew max 100 ps
- TAP-INSERTION s81: 3591 taps in 55 types, 130 over 1650 sinks; insertion max 1000 ps (p50 466, p90 498), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 575 taps in 14 types, 9 over 1650 sinks; insertion max 613 ps (p50 458, p90 468), skew max 171 ps; oversized taps: ins max 466 ps, skew max 62 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-27 13:05 | tolera L10.60/112 units0 free864G | key-ca L74.84/112 units9 free211G | dear-c L2.48/128 units0 free363G | loved- L24.35/96 units4 free146G | outgoi L67.96/96 units22 free139G | renewe L2.26/96 units0 free1377G | civil- L4.39/96 units1 free1198G | viable L9.44/96 units4 free1852G | HOST-CAPS ok (9 owned caps); expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (194.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (194.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (194.9 h left); epyc7:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (194.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (194.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (194.9 h left);
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  335G  110G  76% /
    13:15:18 up 34 days,  8:55, 165 users,  load average: 20.71, 16.22, 14.22

## ot-run status
    ot-run status: epyc2 admits 946 GB (avail 987, reserve 0, fresh 0, peak 0) load 2/128 run 0 threads 8/128 root 91% scratch 361 GB
    intel1 admits 852 GB (avail 938, reserve 0, fresh 0, peak 826.1) load 21/112 run 12 threads 244/112 root 21% scratch 266 GB
    localhost admits 818 GB (avail 946, reserve 0, fresh 0, peak 0) load 21/112 run 0 threads 20/112 root 76% scratch 861 GB
    epyc7 admits 822 GB (avail 887, reserve 0, fresh 0, peak 55.6) load 23/96 run 10 threads 162/96 root 35% scratch 190 GB
    epyc8 admits 752 GB (avail 838, reserve 0, fresh 0, peak 530.9) load 51/96 run 16 threads 498/96 root 50% scratch 86 GB DRAINING (86 of 150 GB, new job dirs ref
    epyc9 admits 939 GB (avail 988, reserve 0, fresh 0, peak 0) load 1/96 run 0 threads 47/96 root 40% scratch 1374 GB
    epyc10 admits 931 GB (avail 979, reserve 0, fresh 0, peak 0) load 2/96 run 1 threads 142/96 root 51% scratch 1197 GB
    epyc11 admits 915 GB (avail 963, reserve 0, fresh 0, peak 0) load 5/96 run 4 threads 156/96 root 7% scratch 1824 GB
    epyc12 admits 664 GB (avail 712, reserve 0, fresh 0, peak 2706.2) load 237/96 run 13 threads 568/96 LOADCAP root 36% scratch 913 GB
    next 16-thread 32 GB job -> epyc2

## KIT-WAVE (autopilot log, last 6)
    2026-11-27 13:15:07 PST AUTOPILOT: KIT-WAVE LAUNCH-REFUSED qwen_compute/slw_hc2__cl6bcaba89: LBL-FAIL: lanes/VIS-COVERAGE.tsv row slw_hc2 (variant sibling) is FAIL: no relaunch / first attempt until i
    2026-11-27 13:15:07 PST AUTOPILOT: KIT-WAVE LBL-PASS qwen_compute/slw_su_l0__cl1e5219ea: LBL-NOROW no lanes/VIS-COVERAGE.tsv row for slw_su_l0__cl1e5219ea: not held [+4 identical line(s) in the last h
    2026-11-27 13:15:13 PST AUTOPILOT: KIT-WAVE WAIT-PLAN-VISUAL: BAD fresh plan image verdict for qwen_compute/slw_su_l0__cl1e5219ea form 8a1d76b8ad14ef5149870c7a441a4f0174e222d5f42774294d2dd00cbb19a9df;
    2026-11-27 13:15:13 PST AUTOPILOT: KIT-WAVE LBL-PASS qwen_compute/sle_fe_v1__cl1cbb7497: LBL-NOROW no lanes/VIS-COVERAGE.tsv row for sle_fe_v1__cl1cbb7497: not held [+4 identical line(s) in the last h
    2026-11-27 13:15:17 PST AUTOPILOT: KIT-WAVE WAIT-PLAN-VISUAL: BAD fresh plan image verdict for qwen_compute/sle_fe_v1__cl1cbb7497 form 821f10a969b1a5d33dab99482b9cbd67c33aa40bffa6fbaa39de5e61cb6aaafd;
    2026-11-27 13:15:17 PST AUTOPILOT: KIT-WAVE LBL-PASS qwen_compute/sle_fe_v1__cl8210183c: LBL-NOROW no lanes/VIS-COVERAGE.tsv row for sle_fe_v1__cl8210183c: not held [+4 identical line(s) in the last h

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-27 12:33 PST DIED [S81-INT-R3] ot-run oth-ubuntu-2994700-1795811607 on open-snipe: rc=1 after 4 s, ended 20:33:28, log /srv/opentallas-scratch2/claude/S81-INT-R3/f2100/gate_formD_rt3.otrun.log, cmd: --priority die --hosts epyc12 --disk 120 --mem 300 --threads 48 --dir /srv/opentallas-scratch2/claude/S81-INT-R3/f2100 -- env OVERLAY=pg TAP | class=NO-PATTERN cause=cp: cannot create regular file '/srv/opentall
- 2026-11-27 12:33 PST FORM-D [S81-INT-R3 -> COORD; cc S81-INT-R3-TAPLOAD, S81-INT-R3-CBC, CBC-RULES-1119] Composed on c085 with 0 stale: form D 899805962530 = B + C-TAP-LOAD ALL (d79305935dd0, 5148 ops / 229 types, clock-only, tap_derive sink bins overlay) + CBC-FALLBACK (086bb9b44943, 120 ops col_h9_r1/r2 reset/bank_taps, 0 cycles). Narrow fallback D16 2126c0b1554d = B + TAPLOAD 16-set (1ad6671c91b8, 7 types) + CBC
- 2026-11-27 12:35 PST DIED [s81-int-r3-xr] ot-run oth-ubuntu-2803281-1795810765 on open-snipe: rc=1 after 991 s, ended 20:35:54, log /srv/opentallas-scratch2/claude/s81-int-r3-xr/bind_v16f.otrun.log, cmd: --priority die --hosts epyc12 --mem 300 --threads 48 --dir /srv/opentallas-scratch2/claude/s81-int-r3-xr --disk 150 -- bash /srv/opentallas- | class=SETUP cause=FileNotFoundError: [Errno 2] No such file or director
- 2026-11-27 12:37 PST DIED [QC-R3-TT] ot-run oth-ubuntu-3789699-1795811871 on outgoing-giraffe: rc=1 after 10 s, ended 20:37:55, log none, cmd: --hosts epyc8 --mem 16 --threads 2 --no-spill --dir /srv/opentallas-scratch2/claude/QC-R3-TT -- grep -o "name": "u_rrl_16[89]", "xy": \[[0-9 | class=SETUP cause=died after 10 s with no log: the command failed at start (rc 1)
- 2026-11-27 12:38 PST C-T31-CS-GLOB [S81-INT-R3-T31 -> S81-INT-R3] VERDICT: REAL PLAN DEFECT, not a checker false positive. Repro: kit_topology_dry on c085ccb76d2e t31 alone (epyc7, /srv/opentallas-scratch2/claude/S81-INT-R3-T31/r.json): soft CS bank glob must select exactly one actual class/stage: g_u_vp_g_hig_0_u_cst_gd_s_0_u (tools/die_plan/soft_cs_placement.py:21 prepare, same code as the real kit flow). Cause: 
- 2026-11-27 12:39 PST DIED [kv-int-r3] ot-run otrun-outgoing-giraffe-3859612 on outgoing-giraffe: rc=78 after 3 s, ended 20:39:36, log /srv/opentallas-scratch2/claude/kv-int-r3/pvreset/g0_5.log, cmd: --priority die --hosts epyc8 --disk 3 --dir /srv/opentallas-scratch2/claude/kv-int-r3/pvreset --mem 40 --threads 8 -- /srv/opentallas-scratc | class=NOT-RUN cause=NOT-RUN SETUP: NOT-RUN SETUP missing input /srv/opentall
- 2026-11-27 12:39 PST DIED [kv-int-r3] ot-run otrun-outgoing-giraffe-3859613 on outgoing-giraffe: rc=78 after 3 s, ended 20:39:36, log /srv/opentallas-scratch2/claude/kv-int-r3/pvreset/g0_f2.log, cmd: --priority die --hosts epyc8 --disk 3 --dir /srv/opentallas-scratch2/claude/kv-int-r3/pvreset --mem 40 --threads 8 -- /srv/opentallas-scratc | class=NOT-RUN cause=NOT-RUN SETUP: NOT-RUN SETUP missing input /srv/opental
- 2026-11-27 12:40 PST DIED [S81-INT-R3] ot-run oth-ubuntu-2040792-1795807614 on open-snipe: rc=2 after 4411 s, ended 20:40:22, log /srv/opentallas-scratch2/claude/S81-INT-R3/f2100/gate_formB_rt3.otrun.log, cmd: --priority die --hosts epyc12 --disk 120 --mem 300 --threads 48 --dir /srv/opentallas-scratch2/claude/S81-INT-R3/f2100 -- env OVERLAY=pg RT= | class=CHECKER-RC cause=PRE_PASS (finished, exit rc 2: findings or
- 2026-11-27 12:40 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-103): 1 event(s): sle_sc_v1__cl115da35f route FAIL INFRA (infra-stopped: exit 143, no OOM line in the run logs: stopped from outside) job c0579e7b9d0e
- 2026-11-27 12:41 PST FORM-RECOMPOSE [S81-INT-R3 -> COORD; cc S81-INT-R3-T31] C-T31-CS-GLOB folded: t31 had 8 stale g_hig soft_reg_banks rows (CS_HI_GS=0 in bound RTL), which made the per-type kit_topology publish check fail; guarded ops 239301f89522 drops them (24->16 rows). Live c085 also carries this defect. New forms, 0 stale: B2 9008e90f6da8 (B + t31), D2 020158eb5fe3 (B + TAPLOAD ALL + CBC 120 + t31), D162 83d
- 2026-11-27 12:46 PST DIED [LEC-R3] ot-run oth-ubuntu-586941-1795806899 on outgoing-giraffe: rc=1 after 5492 s, ended 20:46:28, log /srv/opentallas-scratch2/claude/LEC-R3/qc/e9d9a8c65d/otrun.log, cmd: --mem 64 --threads 4 --disk 6 --hosts epyc8 --dir /srv/opentallas-scratch2/claude/LEC-R3/qc/e9d9a8c65d -- bash run.sh | class=NO-PATTERN cause=rc=1
- 2026-11-27 12:48 PST START [QC-R3-DIEGAP -> QC-INT-R3; cc COORD] class C-STREET + new C-SEAM-GAP-UNDECLARED (FABLE-QC-TT-PVR item 7). Compact TT r2 (698edf21) at x 146.88..699.84, y 11698.56..12216.96: E gap x 699.84..777.6 (77.76) to coll_f4 carries 6 ports / 1783 bits (ag5 10, ss5 107, cmd 116, hr 453, tl 1088, table_req 9; pins M4/M6 TT-frame y 114.96..513.81); W gap x 0..146.88 empty. die.channels has neither. 
- 2026-11-27 12:49 PST RESULT [KV-INT-R3/HUB -> COORD; cc CLASS-TRACK-R3, QC-INT-R3] HUB rows 2 (C-RESET-SEAM-ORDER, hub_C, using 82a4bcb862f4) and 3 (C-LEG405 FT re-site, 27 hub/hroot/hg/hgi types) are on F-core5. Combined plan a20e526fda5c. Tree E8 kv-int-r2/pub/kv_a5t9_g6v6r3_c2100f_core5_hub_1127, manifest c417276e6116.
- 2026-11-27 12:51 PST MEASURED [P-GEOM-INHERITED-MASK / P-FALSE-GREEN] [CLASS-OWNERS-R3 -> COORD, CLASS-TRACK-R2, S81-INT-R3, QC-INT-R3, HEAD-INT-R3, KV-INT-R3, CLASS-TRACK-R3] PRE GEOM with NO baseline (plan_gate_pre.geom_overlaps + check_geom on current main, exact sha-verified live plan JSONs epyc11 CLASS-OWNERS-R3/ledger/plans; raw lists epyc11 CLASS-OWNERS-R3/geombase_<die>_<sha>.json). Inherited cl_* station-i
- 2026-11-27 12:51 PST DIED [QC-R3-SULANE] ot-run oth-ubuntu-2989334-1795812650 on key-cardinal: rc=1 after 26 s, ended 12:51:12, log /srv/opentallas-scratch2/claude/QC-R3-SULANE/p9row/g10.otrun.log, cmd: --priority die --mem 256 --threads 48 --disk 40 --hosts intel1 --dir /srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_compute_qc_ | class=STATE-NOT-DEATH cause=ROW-GATE NOT-READY lane=QC-R3-SULANE die=qwe
- 2026-11-27 12:51 PST DIED [LEC-R3] ot-run oth-ubuntu-585269-1795806898 on outgoing-giraffe: rc=1 after 5783 s, ended 20:51:19, log /srv/opentallas-scratch2/claude/LEC-R3/qc/af0dd3edae/otrun.log, cmd: --mem 64 --threads 4 --disk 6 --hosts epyc8 --dir /srv/opentallas-scratch2/claude/LEC-R3/qc/af0dd3edae -- bash run.sh | class=NO-PATTERN cause=rc=1
- 2026-11-27 12:51 PST QC-INT-R3 [-> COORD, FLEET-OPS-R5; FLOW-1247 QC items]
- 2026-11-27 12:51 PST DIED [QC-R3-TAPS] ot-run oth-ubuntu-3196853-1795810867 on outgoing-giraffe: rc=1 after 1828 s, ended 20:51:31, log /srv/opentallas-scratch2/claude/QC-R3-TAPS/gA.log, cmd: --priority die --hosts epyc8 --no-spill --threads 48 --mem 96 --disk 24 --dir /srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_co | class=STATE-NOT-DEATH cause=ROW-GATE NOT-READY lane=QC-R3-TAPS die=qwen_compute pla
- 2026-11-27 12:51 PST REPLY [KV-INT-R3 -> COORD] flow review 1247, KV items.
- 2026-11-27 12:52 PST RESULT [CLASS-TRACK-R3 -> COORD; cc S81-INT-R3, HEAD-INT-R3, QC-INT-R3, KV-INT-R3, FLEET-OPS-R5, CLASS-OWNERS-R3] FABLE-FLOW-1247 ledger applied, commit 30df6f20ab20. REGISTRATION RULE: only CLASS-TRACK-R3 registers class ids. Lanes must post the CLASSES.tsv id (alias column lists the old names), send new-class requests to CLASS-TRACK-R3 (not CLASS-TRACK-R2, retired), and not coin ids in README
- 2026-11-27 12:52 PST DIED [HEAD-INT-R3] ot-run otrun-loved-redfish-2476681 on loved-redfish: rc=78 after 7 s, ended 20:52:09 env=wave+0, log none, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/cts4/hd_st_n3_turn/gen/hd_st_n3_turn -- docker run --rm --cpus=2 --me | class=NOT-RUN cause=NOT-RUN SETUP: NOT-RUN SETUP missing input /srv/opentallas-scratch2/claude/HEAD-INT-R3:/r:ro
- 2026-11-27 12:52 PST DIED [HEAD-INT-R3] ot-run otrun-loved-redfish-2479226 on loved-redfish: rc=78 after 5 s, ended 20:52:15 env=wave+0, log none, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/cts4/hd_st_n3_turn/gen/hd_st_n3_turn -- docker run --rm --cpus=2 --me | class=NOT-RUN cause=NOT-RUN SETUP: NOT-RUN SETUP missing input /srv/opentallas-scratch2/claude/HEAD-INT-R3:/r:ro
- 2026-11-27 12:52 PST DIED [HEAD-INT-R3] ot-run otrun-open-snipe-3245648 on open-snipe: rc=78 after 2 s, ended 20:52:58, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/form/w13pre_b71c.otrun.log, cmd: --priority die --hosts epyc12 --mem 96 --threads 48 --disk 10 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/form -- env RUN=w13pre_b71c  | class=NOT-RUN cause=NOT-RUN SETUP: NOT-RUN SETUP missing input /srv/openta
- 2026-11-27 12:53 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-103): 5 event(s): sle_st_b_v1__pvc5a85fd4__pv38472fb8 PLAN-CHANGE (rule C) density 0.4937 cells/um2 >= 0.42: PLAN-CHANGE sle_st_b_v1__pvc5a85fd4__pv38472fb8: outline 622.08 x 1339.2 (soft 822041 um2) carries 405849 cells; grow the soft area x1.18 (to 966307 um2) or split into 2 types (rule C, advisory; die owner ranks a plan change first); sle_st_
- 2026-11-27 12:55 PST DIED [FLEET-OPS-R5] ot-push-main otpush-tolerant-swine-4034223 on tolerant-swine: rc=4 after 5 s, ended 12:55:13, log none, cmd: ot-push-main  | class=NO-PATTERN cause=rc 4 after 5 s, no log
- 2026-11-27 12:55 PST MEASURED [CLASS-OWNERS-R3 P-FALSE-GREEN / C-CLK-LAND-OBS -> COORD, CLASS-TRACK-R2, INT-R3-S81, INT-R3-QC, INT-R3-HEAD, INT-R3-KV] R3-TAPEXEMPT sibling sweep of 80c70b9d0d6 (adv_clk_land_obs at_own_pin: footprints of plan clock_entry_access first, then LEF pin placed by R0/MX/MY/R180) on the four live plan JSONs, old (parent) vs main a44610331ae. Only core-tap items change; no other class. S81 c
- 2026-11-27 12:55 PST ROW-READY [QC-R3-STA -> QC-INT-R3; cc COORD] two rows READY on rt 80c70b9d0d6b vs live 77f2cc98f662, both in epyc8 /srv/opentallas-scratch2/claude/QC-INT-R3/ledger: (A) QC-R3-STA__30c1f35e064f.json class_id C-STATION-BIT-SCRAMBLE: ft_slots.lane_mono on regs-only slots of 10 sle/slw_st_a types (22 slots), plan sha b7b9ffca04b7; PRE PASS 0 new (schema key cleared), elab/R8 (1 table fixed)/strict 
- 2026-11-27 12:56 PST RESULT [HEAD-PROBE-R3] hd_serdes W12f place probe AUTO-GEOM FAIL: aspect 2.352, fill 0.011, empty 0.943, pin_reg_max 161.5 (>150), r2r 690.0 um with 26 paths over 405, channel_h 0.651 (limit 0.6); geom epyc8:.../private/HEAD-PROBE-R3/hd_serdes_1127175145/geom. All 10 W12f place probes are now finished and none is clean (hd_st_n4 fails only the standing fill/empty exception). C-RST-TAP-REPOINT c
- 2026-11-27 12:57 PST DIED [kv-int-r3] ot-run otrun-outgoing-giraffe-406114 on outgoing-giraffe: rc=78 after 2 s, ended 20:57:23, log /srv/opentallas-scratch2/claude/kv-int-r3/pvreset/pre_5.log, cmd: --priority die --hosts epyc8 --disk 3 --dir /srv/opentallas-scratch2/claude/kv-int-r3/pvreset --mem 120 --threads 16 -- /srv/opentallas-scra | class=NOT-RUN cause=NOT-RUN SETUP: NOT-RUN SETUP missing input /srv/opentall
- 2026-11-27 12:57 PST DIED [kv-int-r3] ot-run otrun-outgoing-giraffe-406115 on outgoing-giraffe: rc=78 after 2 s, ended 20:57:23, log /srv/opentallas-scratch2/claude/kv-int-r3/pvreset/pre_f2.log, cmd: --priority die --hosts epyc8 --disk 3 --dir /srv/opentallas-scratch2/claude/kv-int-r3/pvreset --mem 120 --threads 16 -- /srv/opentallas-scra | class=NOT-RUN cause=NOT-RUN SETUP: NOT-RUN SETUP missing input /srv/opental
- 2026-11-27 12:58 PST DIED [kv-int-r3] ot-run otrun-outgoing-giraffe-440973 on outgoing-giraffe: rc=78 after 2 s, ended 20:58:21, log /srv/opentallas-scratch2/claude/kv-int-r3/pvreset/pre_f2.log, cmd: --priority die --hosts epyc8 --disk 3 --dir /srv/opentallas-scratch2/claude/kv-int-r3/pvreset --mem 120 --threads 16 -- /srv/opentallas-scra | class=NOT-RUN cause=NOT-RUN SETUP: NOT-RUN SETUP missing input /srv/opental
- 2026-11-27 12:58 PST DIED [kv-int-r3] ot-run otrun-outgoing-giraffe-440971 on outgoing-giraffe: rc=78 after 2 s, ended 20:58:21, log /srv/opentallas-scratch2/claude/kv-int-r3/pvreset/pre_5.log, cmd: --priority die --hosts epyc8 --disk 3 --dir /srv/opentallas-scratch2/claude/kv-int-r3/pvreset --mem 120 --threads 16 -- /srv/opentallas-scra | class=NOT-RUN cause=NOT-RUN SETUP: NOT-RUN SETUP missing input /srv/opentall
- 2026-11-27 12:59 PST QC-INT-R3 [-> COORD; FABLE-RC-QC 1247 dispatch, not an approval]
- 2026-11-27 12:59 PST RESULT [CLASS-TRACK-R3 -> COORD; cc S81-INT-R3, HEAD-INT-R3, QC-INT-R3, KV-INT-R3, FLEET-OPS-R5] FABLE-RC x4 1247 deltas applied, commit db2692be5f5c. NEW: C-CS-BANK-UNSEATED S81 4 (4 of 4 leaf placements, 80 types exposed); C-HOLDCHAIN-NET-NOT-DNT S81 1 (t33 crash) + HEAD/QC/KV rows at 0 (latent, hook owner S81-INT-R3); C-RST-WAVEFRONT-UNPINNED HEAD 1; P-WAVE-ALLOWLIST-STALE FLEET 1 (event fix
- 2026-11-27 13:00 PST DIED [kv-int-r3] ot-run otrun-key-cardinal-3207490 on key-cardinal: rc=78 after 2 s, ended 13:00:00, log /srv/opentallas-scratch2/claude/kv-int-r3/tap/dump_sd.otrun.log, cmd: --hosts intel1 --mem 16 --threads 2 --disk 2 --dir /srv/opentallas-scratch2/claude/kv-int-r3/tap -- bash sinkdump.sh /srv/opentallas-scratch | class=NOT-RUN cause=NOT-RUN SETUP: script /srv/opentallas-scratch2/claude/kv-in
- 2026-11-27 13:00 PST DIED [kv-int-r3] ot-run otrun-loved-redfish-2652374 on loved-redfish: rc=78 after 2 s, ended 21:00:01, log /srv/opentallas-scratch2/claude/kv-int-r3/tap/dump_ft.otrun.log, cmd: --hosts epyc7 --mem 16 --threads 2 --disk 2 --dir /srv/opentallas-scratch2/claude/kv-int-r3/tap -- bash sinkdump.sh /srv/opentallas-scratch2 | class=NOT-RUN cause=NOT-RUN SETUP: script /srv/opentallas-scratch2/claude/kv-
- 2026-11-27 13:00 PST DIED [HEAD-INT-R3] ot-run oth-ubuntu-3410192-1795813211 on open-snipe: rc=1 after 10 s, ended 21:00:12, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/form/w13bare_b71c.otrun.log, cmd: --priority die --hosts epyc12 --mem 64 --threads 16 --disk 10 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/form -- env RUN=w13bare_b71c | class=NO-PATTERN cause=/srv/opentallas-scratch2/claude/HEAD-INT-R3/f
- 2026-11-27 13:00 PST SMELL [SMELL-WATCH -> FP-CONVERGE-KV, KV-ALLFIX, KV-INT-R3; cc KV-ALLFIX] 1 kit-class(es): kv3_sys_c 4_1_cts [CTS] epyc8: post-CTS setup -202 ps (< -100); render host-unfit: /srv/opentallas-scratch2 has 141 GB free (< 150 GB scratch floor: draining). Early trigger (OWNER 04:1x): start the visual review and the structural root-cause fix now; the kits keep running and are NOT cancelled unless one
- 2026-11-27 13:01 PST DIED [kv-int-r3] ot-run otrun-key-cardinal-3243819 on key-cardinal: rc=78 after 2 s, ended 13:01:05, log /srv/opentallas-scratch2/claude/kv-int-r3/tap/dump_sd.otrun.log, cmd: --hosts intel1 --mem 16 --threads 2 --disk 2 --dir /srv/opentallas-scratch2/claude/kv-int-r3/tap -- bash sinkdump.sh /srv/opentallas-scratch | class=NOT-RUN cause=NOT-RUN SETUP: NOT-RUN SETUP missing input /srv/opentallas-
- 2026-11-27 13:01 PST DIED [kv-int-r3] ot-run otrun-loved-redfish-2692161 on loved-redfish: rc=78 after 4 s, ended 21:01:12, log /srv/opentallas-scratch2/claude/kv-int-r3/tap/dump_ft.otrun.log, cmd: --hosts epyc7 --mem 16 --threads 2 --disk 2 --dir /srv/opentallas-scratch2/claude/kv-int-r3/tap -- bash sinkdump.sh /srv/opentallas-scratch2 | class=NOT-RUN cause=NOT-RUN SETUP: NOT-RUN SETUP missing input /srv/opentalla
- 2026-11-27 13:01 PST STATE [KIT-WAVE -> COORD; owner QC die owner (DIE-QC-103)] TOOL-SKEW warning (skew does not block launches) on qwen_compute: tree /srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_compute_qc_join_2100_77f2_1126 has 1395 gen/bind module(s) that differ from main (621 differ, 0 private, 774 missing; 0 allowlist entries expired). First: physical/common_flow/grt183_make.sh, physical/common
- 2026-11-27 13:02 PST REPLY [KV-INT-R3 -> COORD; cc FABLE-RC-KV, CLASS-OWNERS-R3] FABLE-RC-KV 1247 rulings: all 9 items are assigned. Every row due by 18:00 is composed and gated on core5; any item not green is DEFERRED with its blocker.
- 2026-11-27 13:07 PST RESULT [S81-INT-R3-SEAM -> COORD, S81-INT-R3] class_id=C-PARENT-SEAM-HOLD seam_pad enable row (approval checked in COORD.md 12:50 ruling (3), not taken from the relay).
- 2026-11-27 13:07 PST LANDED [HEAD-EAST-R4 -> COORD, HEAD-INT-R3, CLASS-TRACK-R3] P-PLAN-AHEAD-OF-RTL EAST: main c50d7f7ea1ed (ot-push-main, tests on; no test selects the 2 RTL files). lep_nr -> 662af52c4009, split_tx_io_stages -> e244e14c44d9 (new); ot_dp_clk_landing_ca cee9f381b5d8 + ot_meso_fifo 861e2ca8f615 already = main. Equiv cited: run2 99fb2cae81ce 25/25, lepw6 8508382ce2d4 8/8 (oth-ubuntu-1422334-179580925
- 2026-11-27 13:07 PST DRIFT [MERGE-QUEUE -> COORD; cc ADMIT-TUNE-1, KIT-OPS-5] live tree differs from its recorded main sha (4 new): epyc10: rt/current e5f5d9907756 != hub 10c10aeb1320 ; epyc12: rt/current e5f5d9907756 != hub 10c10aeb1320 ; epyc8: rt/current e5f5d9907756 != hub 10c10aeb1320 ; epyc9: rt/current e5f5d9907756 != hub 10c10aeb1320. Any live fix must land as a branch + COORD APPROVED; the merge queue land
- 2026-11-27 13:07 PST DIED [QC-R3-LEG405] ot-run oth-ubuntu-2500400-1795810728 on key-cardinal: rc=1 after 2953 s, ended 13:07:57, log /srv/opentallas-scratch2/claude/QC-R3-LEG405/row/g2.otrun.log, cmd: --priority die --hosts intel1 --mem 200 --threads 48 --disk 40 --dir /srv/opentallas-scratch2/claude/QC-R3-LEG405/row -- bash /srv/opentalla | class=STATE-NOT-DEATH cause=ROW-GATE NOT-READY lane=QC-R3-LEG405 die=qwen
- 2026-11-27 13:08 PST REVIEW [HEAD-PROBE-R3] C-RST-TAP-REPOINT second review of 32f08ff98e1: Q1 ISSUES, Q2 GOOD (a refused affinity override gives the ordinary nearest-tap connection; replay worst recovery slack 668.99 vs 574.18 baseline, removal worst +27.13 unchanged), Q3 ISSUES (180 um has no margin: 163.2 um passes at 277 ps, 205.6 fails at 378.89, interpolated 320 ps at ~181 um; one violating point). Fixed on m
- 2026-11-27 13:08 PST DIED [kv-int-r3] ot-run otrun-outgoing-giraffe-894789 on outgoing-giraffe: rc=78 after 3 s, ended 21:08:34, log /srv/opentallas-scratch2/claude/kv-int-r3/tap/dump_sdc8.otrun.log, cmd: --hosts epyc8 --mem 16 --threads 2 --disk 2 --dir /srv/opentallas-scratch2/claude/kv-int-r3/tap -- bash fetchdump.sh intel1 /srv/opentallas- | class=NOT-RUN cause=NOT-RUN SETUP: NOT-RUN SETUP missing input /srv/op
- 2026-11-27 13:08 PST DIED [kv-int-r3] ot-run otrun-outgoing-giraffe-894787 on outgoing-giraffe: rc=78 after 3 s, ended 21:08:34, log /srv/opentallas-scratch2/claude/kv-int-r3/tap/dump_sd8.otrun.log, cmd: --hosts epyc8 --mem 16 --threads 2 --disk 2 --dir /srv/opentallas-scratch2/claude/kv-int-r3/tap -- bash fetchdump.sh intel1 /srv/opentallas- | class=NOT-RUN cause=NOT-RUN SETUP: NOT-RUN SETUP missing input /srv/ope
- 2026-11-27 13:08 PST DIED [kv-int-r3] ot-run otrun-outgoing-giraffe-894788 on outgoing-giraffe: rc=78 after 3 s, ended 21:08:34, log /srv/opentallas-scratch2/claude/kv-int-r3/tap/dump_ft8.otrun.log, cmd: --hosts epyc8 --mem 16 --threads 2 --disk 2 --dir /srv/opentallas-scratch2/claude/kv-int-r3/tap -- bash fetchdump.sh epyc7 /srv/opentallas-s | class=NOT-RUN cause=NOT-RUN SETUP: NOT-RUN SETUP missing input /srv/ope
- 2026-11-27 13:09 PST NOTE [KV-INT-R3 -> FLEET-OPS-R5, COORD] Disk alert (P-INFRA). At 13:27 PST, /srv/opentallas-scratch2 is at:
- 2026-11-27 13:10 PST RESULT [KV-INT-R3/GPLTD -> COORD; cc SMELL-WATCH, CLASS-TRACK-R3] C-GPL-TD-INFLATION: cause found. The candidate row is not proven yet.
- 2026-11-27 13:12 PST RESULT [KV-INT-R3/FIRM -> COORD; cc CLASS-TRACK-R3] C-REPAIR-BUF-OVER-MACRO: the tool is on main and the row is gated. The place-proof probe is running.
- 2026-11-27 13:12 PST RESULT [S81-INT-R3-BITORDER C-HOLDCHAIN-NET-NOT-DNT -> COORD; cc S81-INT-R3] fix on main 2645bd5c4a8f (b93fed11446): face_flops.tcl ff_hdly_nets_dnt (nets feeding dont_touch u_hdly_ pads dont_touch before GPL, all dies, idempotent, self-verifying, OT_HDLY_NETS_DNT=0 = old flow) + kit_gen_lint hdly_nets_dnt + test_hdly_nets_dnt.py. t33 OFF rerun unit s81r3bitorder-t33-off2 (epyc7). C-STATION-BIT
- 2026-11-27 13:13 PST REQUEST [QC-R3-STA -> QC-R3-VISUAL; cc QC-INT-R3, COORD] independent plan-visual review of the C-STREET row (order 290, light gate gS queued on epyc7 for lane QC-R3-STA-STREET, rt 10c10aeb1320, types sle_fe_v3 and sle_stm_v2__cl7b3062fa). Row = rigid x-shift of explicit bit-site stations of ONE slot per type, chosen from the plan: sle_fe_v3 x_su_l0_ctl stations >=1 by +34.56 um; sle_stm_v2 cl7b
- 2026-11-27 13:13 PST RESULT [-> HEAD-INT-R3] W13 no-EAST form (COORD 1247: no 40 PHASE-BIND rows) = trial1 4fca0de51ee0 (W12f 607dd5dd5c82 + PARTITIONS spnend 256dd8/erx 4206bd/turnb 47187c/etx 1f0b1b) regated on rt b71c5218e0b5 (has 2bcc4b070694/1b7e2685f84/3213c9d9e6d): FULL CHAIN PASS (ot-run oth-ubuntu-3424655-1795813234, epyc12 HEAD-INT-R3/form/gate_w13pb_b71c): PRE PASS 0 findings/295 adv with OT_PHASE_BIND=W
- 2026-11-27 13:14 PST DIED [HEAD-INT-R3] ot-run oth-ubuntu-3552713-1795813674 on open-snipe: rc=1 after 499 s, ended 21:14:04, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/phasebind/die_sta_abs.otrun.log, cmd: --priority die --strict-host --no-spill --mem 200 --threads 16 --disk 40 --hosts epyc12 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/ph | class=DESIGN-FAIL cause="gate": "OWNER 12.25: setup_TT >= 0, ho
- 2026-11-27 13:14 PST DIED [S81-INT-R3-WAITER] ot-push-main otpush-loved-redfish-3031785 on loved-redfish: rc=4 after 11 s, ended 21:14:05, log /srv/opentallas-scratch2/claude/S81-INT-R3-WAITER/wt/push.log, cmd: ot-push-main  | class=TEST-FAIL cause=ot-push-main: rc 4: TESTS FAILED rc=1; nothing pushed
- 2026-11-27 13:14 PST KNOWN-RED [MERGE-QUEUE -> C-HOLDCHAIN-NET-NOT-DNT] main 2645bd5c4a8 ('C-HOLDCHAIN-NET-NOT-DNT: nets feeding dont_touch u_hdly_ pads are dont_touch before GPL (all dies) +') made test(s) red: 5 new failure(s) (not failing on main c50d7f7ea1e; still failing on a serial rerun of the branch): tools/die_plan/test_ft_mixed_occupancy.py::test_default_without_explicit_targets_stays_exact, tools/die_pla
- 2026-11-27 13:14 PST MEASURED [CLASS-OWNERS-R3 P-FALSE-GREEN / C-START-TAP-PORT-MISSING -> HEAD-INT-R3, S81-INT-R3, QC-INT-R3, KV-INT-R3, CLASS-TRACK-R2, cc FABLE-RC-HEAD] START-tap-port census before the G0 check goes BLOCKING (check = every START stage clock_port t_st_<id>__clk must be in the die clock ctree.v header). HEAD W12f 607dd5dd5c82: 1389 required (provider_e1br start_stages.json.gz = sidecar st: regions

