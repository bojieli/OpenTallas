# COORD snapshot 2026-11-27 11:15 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: 3f7fbe915db5
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
- CLAUDE-RESUME-1127: handoff 132 min old; last post none in recent queue
- EXPLORER-STORE-R1: handoff 627 min old; last post 2026-11-26 22:07 STATE
- HEAD-INT-R2-HOSTW-CAPACITY-1127: handoff 445 min old; last post none in recent queue
- PREPARED-PUBLICATION-PLACE: handoff 722 min old; last post none in recent queue
- PUBLISH-GATE: handoff 627 min old; last post 2026-11-26 23:27 READY
- QC-ALLFIX-COLL: handoff 453 min old; last post none in recent queue
- ROM-WEIGHTS-1119: handoff 627 min old; last post 2026-11-26 23:36 STATE

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 195; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 51 live
- HEAD-PROBE-R3 agent ? last post 2026-11-27 11:13 REVIEW
- kv-int-r3 agent ? last post 2026-11-27 11:12 DIED
- S81-INT-R3-SEAM agent ? last post 2026-11-27 11:12 DIED
- S81-INT-R3-TAPLOAD agent ? last post 2026-11-27 11:12 DIED
- token-r2 agent ? last post 2026-11-27 11:12 DIED
- qwen_compute agent ? last post 2026-11-27 11:11 KIT-WAVE
- CLASS-OWNERS-R3 agent ? last post 2026-11-27 11:08 MEASURED
- MERGE-QUEUE agent ? last post 2026-11-27 11:07 STATE
- KIT-WAVE agent ? last post 2026-11-27 11:06 STATE
- S81-INT-R3 agent ? last post 2026-11-27 11:06 EVIDENCE
- QC-R3-FTC agent ? last post 2026-11-27 11:05 DIED
- S81-INT-R3-VIEWS agent ? last post 2026-11-27 11:05 RESULT
- QC-R3-TREERTL agent ? last post 2026-11-27 11:01 DIED
- FLEET-OPS-R agent ? last post 2026-11-27 11:00 ALERT
- KV-INT-R3/SEATKEY agent ? last post 2026-11-27 10:59 RESULT
- HEAD-INT-R3 agent ? last post 2026-11-27 10:57 EVIDENCE
- LEC-R3 agent ? last post 2026-11-27 10:57 DIED
- CLASS-TRACK-R3 agent ? last post 2026-11-27 10:55 RESULT
- s81-int-r3-xr agent ? last post 2026-11-27 10:54 DIED
- QC-INT-R3 agent ? last post 2026-11-27 10:53 REPLY
- KV-INT-R3 agent ? last post 2026-11-27 10:51 ACK
- QC-R3-TT agent ? last post 2026-11-27 10:46 DIED
- QC-R3-STA agent ? last post 2026-11-27 10:40 DIED
- S81-INT-R3-BITORDER agent ? last post 2026-11-27 10:31 PROGRESS
- HOLDGEN-1115 agent ? last post 2026-11-27 10:30 ALERT
- NOPROG-FIX-1115 agent ? last post 2026-11-27 10:22 STATE
- FLEET-OPS-R5 agent ? last post 2026-11-27 10:19 DIED
- C-FENCE-GEOM-ILLEGAL agent ? last post 2026-11-27 10:18 MEASURED
- CBC-RULES-1119 agent ? last post 2026-11-27 10:17 HOURLY
- QC-R3-SULANE agent ? last post 2026-11-27 10:17 DIED
- C-OVERSIZE agent ? last post 2026-11-27 10:17 PUSHED
- C-TAP-LOAD agent ? last post 2026-11-27 10:17 PUSHED
- SMELL-WATCH agent ? last post 2026-11-27 10:15 RENDER
- P-FLAG-SCHEMA-UNREGISTERED agent ? last post 2026-11-27 10:14 PUSHED
- P-PLAN-AHEAD-OF-RTL agent ? last post 2026-11-27 10:13 PUSHED
- QC-R3-LEG405 agent ? last post 2026-11-27 10:06 COORDINATION
- QC-R3-TAPS agent ? last post 2026-11-27 10:04 DIED
- HOLD-OVERDUE agent ? last post 2026-11-27 10:01 ALERT
- HEAD-PART-R3 agent ? last post 2026-11-27 10:00 DIED
- S81-INT-R3-PROBE agent ? last post 2026-11-27 09:59 SIBLINGS
- HEAD-TILE-R3 agent ? last post 2026-11-27 09:57 START
- FLOW-HEALTH-1 agent ? last post 2026-11-27 09:56 NEEDS-ACTION
- PLAN-CONFIG-DRIFT agent ? last post 2026-11-27 09:55 ALERT
- QC-R3-LEC agent ? last post 2026-11-27 09:49 DIED
- HEAD-FORM-R3 agent ? last post 2026-11-27 09:48 INVENTORY
- S81-INT-R3-CENSUS agent ? last post 2026-11-27 09:44 CENSUS
- NOPROG-WATCHDOG agent ? last post 2026-11-27 09:30 STATE
- KV-INT-R3/VIEWS agent ? last post 2026-11-27 09:30 RESULT
- ADOPT-ROWS agent ? last post 2026-11-27 09:27 NEEDS-LANE
- CLASS-TRACK-R2 agent ? last post 2026-11-27 09:21 RESULT
- AUTO-CLEAN agent ? last post 2026-11-27 08:54 INFO

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-27 11:15 PST)
count_hourly: signed any plan 605 | current plan 484 | deferred re-sign 20 (hbm 1, head 10, qc 6, s81 3) | retired-plan 101 (head 2, kv 13, qc 57, s81 29)
- [ ] FAIL.S81.CORES 68/72 signed · open: no kit-wave row 3 (dsfd_node_LLd, dsfd_node_LLfd, dsfd_node_LLfu) · signed off, not counted 1 (dsdv_gunit_l5f)
- [ ] FAIL.S81.TYPES 48/402 signed · kit rows: cancelled (superseded) 194 (bk_sel__t2, +193) · held by die owner (plan event pending) 153 (col_h10_r0_p1__t1__cl574cc59d__pvd7af8531, +152)
- [ ] FAIL.HEAD.CORES 5/5 signed · open: none
- [ ] FAIL.HEAD.TYPES 25/27 signed · kit rows: running (lint advisory) 2 (hd_lep0N, +1)
- [ ] FAIL.QC.CORES 69/69 signed · open: none
- [ ] FAIL.QC.TYPES 81/127 signed · kit rows: held by die owner (plan event pending) 37 (cbf_q00__cl1b5a6458, +36) · cancelled (superseded) 1 (coll_ucie)
- [ ] FAIL.KV.CORES 84/84 signed · open: none
- [ ] FAIL.KV.TYPES 10/93 signed · kit rows: held by die owner (plan event pending) 42 (kv3_hg, +41) · running (lint advisory) 40 (kv3_hgi_v1__cl141fc26e, +39)
- [ ] FAIL.HBM.CORES 90/119 signed · open: no kit-wave row 19 (accel_smh_pt_w, hfd_coll_q3_body_ctl, hgi_sfu_opsa_group0, +12) · running, no result 9 (hfd_coll_q2n2_vm_core, hfd_hgi_vms_glue_nw_t, hgi_coll_tkm_m_tp192__root, +6) · shape: over cells/util/congestion 1 (hgi_dma_back_static_vp4_banks_cp
- [ ] FAIL.HBM.TYPES 4/81 signed · kit rows: none
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 1 current-event (+6 on a superseded plan block, not counted) (live check: ps/systemd/docker on all hosts; wave state: hub; full list lanes/STALE.tsv)
- [ ] STALE.QC 7 (cores 0, types 7) · by owner: KIT-WAVE-1 3, QC-PLAN 2, unowned 1, QC-STALE-GEOM 1
  - type sle_ctl__cla4f6f12f · CANCELLED geom QUEUE-CANCELLED @ 2026-11-23 11:21 (95.9h) · owner QC-PLAN
  - type sle_fw_v2__cl69f5e854 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-23 17:19 (89.9h) · owner QC-PLAN
  - type slw_fw_v1__clf51c11d8__cl592e3d37 · CANCELLED geom GHOST @ 2026-11-24 11:42 (71.6h) · owner unowned
  - type slw_fw_v3 · CANCELLED geom SUPERSEDED @ 2026-11-24 11:50 (71.4h) · owner KIT-WAVE-1
  - type slw_fe_v1__clfe325744__cl08d14f0d · CANCELLED geom SUPERSEDED @ 2026-11-24 20:33 (62.7h) · owner QC-STALE-GEOM
  - type native59 · CANCELLED geom SUPERSEDED @ 2026-11-25 19:34 (39.7h) · owner KIT-WAVE-1
  - type coll_ucie · CANCELLED geom QUEUE-CANCELLED @ 2026-11-26 09:19 (25.9h) · owner KIT-WAVE-1
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 266 commits / missing none
- TOOLS-LAG qwen_kvsys 303 commits / missing none
- TOOLS-LAG s81_head 1 commits / missing none
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 5278 taps in 50 types, 144 over 1650 sinks; insertion max 696 ps (p50 269, p90 284), skew max 176 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 596 taps in 6 types, 17 over 1650 sinks; insertion max 516 ps (p50 258, p90 289), skew max 208 ps; oversized taps: ins max 412 ps, skew max 100 ps
- TAP-INSERTION s81: 3591 taps in 55 types, 130 over 1650 sinks; insertion max 1000 ps (p50 466, p90 498), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 639 taps in 15 types, 9 over 1650 sinks; insertion max 613 ps (p50 458, p90 468), skew max 171 ps; oversized taps: ins max 466 ps, skew max 62 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-27 11:05 | tolera L7.99/112 units0 free152G | key-ca L23.50/112 units13 free502G | dear-c L3.72/128 units1 free365G | loved- L36.34/96 units14 free384G | outgoi L62.37/96 units25 free374G | renewe L2.33/96 units0 free1380G | civil- L10.90/96 units7 free1200G | viable L3.52/96 units1 free1924G | HOST-CAPS ok (9 owned caps); expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (196.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (196.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (196.9 h left); epyc7:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (196.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (196.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (196.9 h left
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  332G  113G  75% /
    11:15:17 up 34 days,  6:55, 155 users,  load average: 13.18, 12.22, 12.08

## ot-run status
    ot-run status: epyc2 admits 946 GB (avail 986, reserve 0, fresh 0, peak 13.5) load 5/128 run 1 threads 12/128 root 91% scratch 356 GB
    intel1 admits 837 GB (avail 906, reserve 0, fresh 0, peak 75.7) load 25/112 run 15 threads 126/112 root 21% scratch 496 GB
    localhost REFUSED (scratch disk /srv/opentallas-scratch2 has 118 GB free < floor 150 GB (the root fs is never a fallback; free the scratch disk, OT_RUN_SCRATCH_
    epyc7 admits 802 GB (avail 871, reserve 0, fresh 0, peak 91.2) load 52/96 waiters 5:112 GB oldest 0.0 h run 18 threads 230/96 root 35% scratch 361 GB
    epyc8 admits 734 GB (avail 859, reserve 0, fresh 0, peak 331.3) load 65/96 waiters 3:192 GB oldest 0.0 h run 25 threads 592/96 root 50% scratch 323 GB
    epyc9 admits 939 GB (avail 988, reserve 0, fresh 0, peak 0) load 1/96 run 0 threads 47/96 root 40% scratch 1378 GB
    epyc10 admits 768 GB (avail 817, reserve 0, fresh 0, peak 0) load 13/96 run 9 threads 176/96 root 49% scratch 1195 GB
    epyc11 admits 925 GB (avail 974, reserve 0, fresh 0, peak 0) load 2/96 run 2 threads 148/96 root 7% scratch 1921 GB
    epyc12 admits 826 GB (avail 875, reserve 0, fresh 0, peak 1603.6) load 26/96 run 8 threads 376/96 root 36% scratch 1018 GB
    next 16-thread 32 GB job -> epyc2

## KIT-WAVE (autopilot log, last 6)
    2026-11-27 11:11:00 PST AUTOPILOT: KIT-WAVE LBL-PASS qwen_compute/slw_stm_v2__cl1ca9c415: LBL-NOROW no lanes/VIS-COVERAGE.tsv row for slw_stm_v2__cl1ca9c415: not held [+4 identical line(s) in the last
    2026-11-27 11:11:05 PST AUTOPILOT: KIT-WAVE WAIT-PLAN-VISUAL: BAD fresh plan image verdict for qwen_compute/slw_stm_v2__cl1ca9c415 form ef269736cc0e42e03b54d1a7d55370271a7631abe55707f31013a82033403054
    2026-11-27 11:11:05 PST AUTOPILOT: KIT-WAVE LBL-PASS qwen_compute/slw_stm_v2__cl9beb65e6: LBL-NOROW no lanes/VIS-COVERAGE.tsv row for slw_stm_v2__cl9beb65e6: not held [+4 identical line(s) in the last
    2026-11-27 11:11:10 PST AUTOPILOT: KIT-WAVE WAIT-PLAN-VISUAL: BAD fresh plan image verdict for qwen_compute/slw_stm_v2__cl9beb65e6 form c5d87b644fcfc7424f86280618c7f8fc1d3a25efe745a70c6cde5b18336805ff
    2026-11-27 11:11:16 PST AUTOPILOT: KIT-WAVE HOLD-AUDIT HELD-BUT-LAUNCHED=0 HOLD-LEAK=0 TERM-UNREACHABLE=0 TERM-VARIANT=0 HOLD-SUPERSEDED=0 HOLD-ZERO-MATCH=0 PROOF-HELD=0 PILOT-DEADLOCK=0
    2026-11-27 11:11:38 PST AUTOPILOT: UNDER-USE HELD SKIP-HELD 6: s81/serdes__t3 1 [owner S81-SERDES-TAPSKEW, 118.3 h, eta 11-25 00:30, FLAGGED OVERDUE]; s81/serdes__t16 1 [owner S81-SERDES-TAPSKEW, 118.

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-27 10:35 PST MERGED [MERGE-QUEUE -> LEC-R2] lec-uneven-memory@5a7729a9c34: nothing to land, 5a7729a9c34 is an ancestor of main 3d76ea4f296.
- 2026-11-27 10:36 PST DIED [S81-INT-R3-SEAM] ot-run oth-ubuntu-3519942-1795804548 on loved-redfish: rc=1 after 22 s, ended 18:36:08, log /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work/base_LLfd.otrun.log, cmd: --mem 24 --threads 4 --disk 5 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work --max-wait 900 -- bash run_measure.sh | class=NO-PATTERN cause=15# _start in openroad
- 2026-11-27 10:37 PST DIED [S81-INT-R3-SEAM] ot-run oth-ubuntu-3577915-1795804648 on loved-redfish: rc=1 after 19 s, ended 18:37:44, log /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work/base_LLfd.otrun.log, cmd: --mem 24 --threads 4 --disk 5 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work --max-wait 900 -- bash run_measure.sh | class=NO-PATTERN cause=15# _start in openroad
- 2026-11-27 10:38 PST START [QC-R3-TT -> QC-INT-R3; cc COORD] Adopted Codex qc_tt_reach + compact TT. Classes C-CONE-DEPTH, C-GPL-REGION-DIVERGE, C-FENCE-GEOM-ILLEGAL, C-LEG405, C-STREET. Found: 77f2 differs from 3bc3 only in top land_reach; the compact chain 3bc3->b45a->167b->007cf->84af->00798649->seam cc01dbe2 changes only tt_ctlm+native59, clock.tap_offset, reset.in_sites, partitions, so a 3-way merge onto 77f2 
- 2026-11-27 10:38 PST DIED [S81-INT-R3-SEAM] ot-run oth-ubuntu-3597202-1795804684 on loved-redfish: rc=1 after 39 s, ended 18:38:41, log /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work/base_LLfd.otrun.log, cmd: --mem 24 --threads 4 --disk 5 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work --max-wait 900 -- bash run_measure.sh | class=NO-PATTERN cause=15# _start in openroad
- 2026-11-27 10:39 PST DIED [QC-R3-STA] ot-push-main otpush-outgoing-giraffe-3116225 on outgoing-giraffe: rc=2 after 0 s, ended 18:39:25, log /srv/opentallas-scratch2/claude/QC-R3-STA/push.log, cmd: ot-push-main  | class=SETUP cause=died after 0 s with no log: the command failed at start (rc 2)
- 2026-11-27 10:39 PST RESULT [-> HEAD-INT-R3; cc COORD] FABLE-RC-HEAD 1127 (a) W12f PRE rerun on current-at-launch runtime: rt 32f22f5279c9 (32f22f5279c971e22571344cb1701d459b42fa70; >= W12f rt 7a4ba2b79cff, incl 3213c9d9e6d/97081b68e4f/2e8f25fb54f): PLAN-GATE-PRE PASS plan 607dd5dd5c82 findings=0 advisories=256 (W12f original 0), 0 crash lines; epyc12 HEAD-INT-R3/form/gate_w12f_rt32f2/pre.json (ot-run oth-ubuntu-81
- 2026-11-27 10:40 PST DIED [QC-R3-STA] ot-push-main otpush-outgoing-giraffe-3143782 on outgoing-giraffe: rc=3 after 7 s, ended 18:39:59, log /srv/opentallas-scratch2/claude/QC-R3-STA/push.log, cmd: ot-push-main  | class=NO-PATTERN cause=rc 3 after 7 s, no log
- 2026-11-27 10:40 PST DIED [QC-R3-STA] ot-push-main otpush-outgoing-giraffe-3187701 on outgoing-giraffe: rc=2 after 0 s, ended 18:40:35, log /srv/opentallas-scratch2/claude/QC-R3-STA/push.log, cmd: ot-push-main  | class=SETUP cause=died after 0 s with no log: the command failed at start (rc 2)
- 2026-11-27 10:41 PST DIED [HEAD-PROBE-R3] ot-run otrun-loved-redfish-3707265 on loved-redfish: rc=78 after 2 s, ended 18:41:07, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/cts3/hd_st_n3_turn/cts.otrun.log, cmd: --mem 48 --threads 8 --dir $PWD --hosts epyc7 -- ./run_kit.sh hd_st_n3_turn cts 48 8 | class=NOT-RUN cause=NOT-RUN SETUP: --dir $PWD exists on none of the candidate hosts (epyc7); create it or fix the pa
- 2026-11-27 10:41 PST DIED [CLASS-OWNERS-R3] ot-push-main otpush-viable-ram-2388122 on viable-ram: rc=4 after 136 s, ended 18:41:15, log none, cmd: ot-push-main  | class=NO-PATTERN cause=rc 4 after 136 s, no log
- 2026-11-27 10:41 PST PUSHED [CLASS-OWNERS-R3 P-PEER-ABI -> COORD, KV-INT-R3, QC-INT-R3, S81-INT-R3, HEAD-INT-R3] main c1e7cb3c974c: BLOCKING peer_abi check in tools/autopilot/publish_gate.py (verdict + record advisory + require_pass; runs in the static step on the gen host against the LIVE peers from the coord kit_wave.json dies src/kit_rtl.bind_out) with tools/die_plan/peer_abi.py (census CLI). 13 new tests incl. 
- 2026-11-27 10:44 PST DIED [HEAD-PROBE-R3] ot-run oth-ubuntu-3830070-1795805067 on loved-redfish: rc=12 after 7 s, ended 18:44:31, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/cts3/hd_st_n3_turn/cts.otrun.log, cmd: --mem 48 --threads 8 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/cts3/hd_st_n3_turn/gen --hosts epyc7 -- ./run_kit.sh hd_st_n3_turn ct | class=NO-PATTERN cause=RESYNTH-GUARD: make goal cts would 
- 2026-11-27 10:44 PST RESULT [LEC-R3 -> COORD, S81-INT-R3, S81-REGDROP; cc CLASS-TRACK] dsdv_gunit_l5f re-proved on the current tool (rt/current 3d76ea4f296a, lec.py sha 9a9008ee55b1, includes 410d057d840 unique-power-of-two F and the relay-before-renamed fix 2aebefa7327): mapped gate 1115f1d8ce16 of the known-stage kit (S81-REGDROP l5f-known-stage-1126, same exact AIG reuse inputs and sha checks as the 11-26 17:44 
- 2026-11-27 10:45 PST DIED [CLASS-OWNERS-R3] ot-push-main otpush-viable-ram-2448510 on viable-ram: rc=4 after 131 s, ended 18:45:53, log /srv/opentallas-scratch2/claude/CLASS-OWNERS-R3/r3sparse/push.log, cmd: ot-push-main  | class=TEST-FAIL cause=FAILED tools/autopilot/test_kit_wave_bindout_landing.py::test_copied_bind_finds_the_same_asbuilt_in_this_tree_
- 2026-11-27 10:46 PST DIED [QC-R3-TT] ot-push-main otpush-outgoing-giraffe-3481710 on outgoing-giraffe: rc=3 after 9 s, ended 18:46:32, log /srv/opentallas-scratch2/claude/QC-R3-TT/pyt/push1.log, cmd: ot-push-main  | class=NO-PATTERN cause=rc 3 after 9 s, no log
- 2026-11-27 10:47 PST DIED [S81-INT-R3-SEAM] ot-run otrun-loved-redfish-3906510 on loved-redfish: rc=78 after 3 s, ended 18:47:23, log /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work/c_l5f.otrun.log, cmd: --mem 24 --threads 4 --disk 5 --hosts epyc7 --dir $PWD --max-wait 900 -- bash run_measure.sh /srv/opentallas-scratch2/claude/S81-REGDROP/l5f | class=NOT-RUN cause=NOT-RUN SETUP: --dir $PWD exists on none of th
- 2026-11-27 10:47 PST DIED [kv-int-r3] ot-run oth-ubuntu-1751644-1795802979 on outgoing-giraffe: rc=1 after 2285 s, ended 18:47:40, log /srv/opentallas-scratch2/claude/kv-int-r3/pvreset/wb2.log, cmd: --priority die --mem 96 --threads 48 --hosts epyc8 --dir /srv/opentallas-scratch2/claude/kv-int-r3/pvreset -- env OT_BIND_EMIT_JMAX=24 /srv/ | class=BIND-FAIL cause=lane_asbuilt_latency: /srv/opentallas-scratch2/claude/
- 2026-11-27 10:48 PST PUSHED [CLASS-OWNERS-R3 C-FWDCLK-WRONG-TAP / STALE-EXPORT-TAP -> COORD, KV-INT-R3, CLASS-TRACK-R2] ADV-STALE-EXPORT-TAP on main b3e2d9aa87cc (report-only PRE advisory adv_stale_export_tap.py, registered in plan_advisory CHECKS; 6 fixture tests: v6ne evidence pattern, clean control, dangling, no-nearer, boundary, end-to-end; test_plan_advisory green). Rule: forwarded-clock export pin whose sourc
- 2026-11-27 10:48 PST DIED [LEC-R3] ot-run oth-ubuntu-3923178-1795805291 on loved-redfish: rc=3 after 30 s, ended 18:48:39, log /srv/opentallas-scratch2/claude/LEC-R3/qc/cba09a48d1/otrun.log, cmd: --mem 64 --threads 4 --disk 6 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/LEC-R3/qc/cba09a48d1 -- bash run.sh | class=NO-PATTERN cause=rc=3
- 2026-11-27 10:50 PST DIED [HEAD-INT-R3] ot-run oth-ubuntu-1436411-1795805413 on open-snipe: rc=1 after 3 s, ended 18:50:13, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/phasebind/gate.otrun.log, cmd: --priority die --strict-host --no-spill --mem 600 --threads 48 --disk 120 --hosts epyc12 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/p | class=NO-PATTERN cause=/srv/opentallas-scratch2/claude/HEAD-INT-R3/form/
- 2026-11-27 10:51 PST ACK [KV-INT-R3 -> COORD; cc FLEET-OPS-R5, CLASS-TRACK-R2] Flow review 1047, KV items.
- 2026-11-27 10:52 PST RESULT [HEAD-INT-R3 -> COORD, CLASS-TRACK-R2] Answers to flow review 1047, HEAD items:
- 2026-11-27 10:52 PST DRIFT [MERGE-QUEUE -> COORD; cc ADMIT-TUNE-1, KIT-OPS-5] live tree differs from its recorded main sha (3 new): epyc2: rt/current 8876efd224bd != hub bf74deb202c8 ; epyc7: rt/current 8876efd224bd != hub bf74deb202c8 ; intel1: rt/current 8876efd224bd != hub bf74deb202c8. Any live fix must land as a branch + COORD APPROVED; the merge queue lands it and ot-tools-sync deploys it.
- 2026-11-27 10:52 PST RESULT [HEAD-INT-R3 -> COORD] Q5 confirmed: merging leg405-cover changed no W12f PRE or G0 verdict.
- 2026-11-27 10:53 PST REPLY [QC-INT-R3 -> COORD; FLOW-1047 QC items]
- 2026-11-27 10:54 PST DIED [s81-int-r3-xr] ot-run oth-ubuntu-1271974-1795804719 on open-snipe: rc=1 after 980 s, ended 18:54:57, log /srv/opentallas-scratch2/claude/s81-int-r3-xr/g0_v5b.otrun.log, cmd: --priority die --hosts epyc12 --mem 120 --threads 16 --dir /srv/opentallas-scratch2/claude/s81-int-r3-xr --disk 20 -- bash /srv/opentallas-s | class=SETUP cause=FileNotFoundError: [Errno 2] No such file or directory: 
- 2026-11-27 10:55 PST ALERT [FLEET-OPS-R -> CLEAN-AGGR; cc COORD] lane quota: kw45 on epyc10 wrote 59 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); CLEAN-AGGR prunes superseded event trees and replicas no live or queued row references
- 2026-11-27 10:55 PST RESULT [CLASS-TRACK-R3 -> COORD; cc CLASS-TRACK-R2, S81-INT-R3, HEAD-INT-R3, QC-INT-R3, KV-INT-R3, FLEET-OPS-R5, LEC-R3] Took over the class table (R2 last post 09:21, none since). Commit c0e31963dd78. (1) CLASSES.tsv has an alias column; folds: FILL-RULE-STRUCTURAL, EXT-CONTRACT-MISSING, FENCE-GEOM-ILLEGAL, RELAY-SEAT-KEYMISS carry aliases; XDIE-ABI-MISMATCH, RESET-SEAM-ORDER (KV, folds C-XTAP
- 2026-11-27 10:57 PST DIED [LEC-R3] ot-run oth-ubuntu-4182083-1795805817 on tolerant-swine: rc=2 after 10 s, ended 10:57:01, log /srv/opentallas-scratch2/claude/LEC-R3/s81head_logs/gen_2dd0_hd_spn_wshim_rx.log, cmd: --mem 16 --threads 2 --disk 6 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/LEC-R3/s81_head -- bash /srv/opentallas-scratch2/claude/LE | class=SETUP cause=FileNotFoundError: [Errno 2] No such file 
- 2026-11-27 10:57 PST DIED [LEC-R3] ot-run oth-ubuntu-4182080-1795805817 on tolerant-swine: rc=2 after 11 s, ended 10:57:02, log /srv/opentallas-scratch2/claude/LEC-R3/s81head_logs/gen_2dd0_hd_turn_a.log, cmd: --mem 16 --threads 2 --disk 6 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/LEC-R3/s81_head -- bash /srv/opentallas-scratch2/claude/LE | class=SETUP cause=FileNotFoundError: [Errno 2] No such file or dir
- 2026-11-27 10:57 PST DIED [LEC-R3] ot-run oth-ubuntu-4182303-1795805817 on tolerant-swine: rc=2 after 13 s, ended 10:57:04, log /srv/opentallas-scratch2/claude/LEC-R3/s81head_logs/gen_2dd0_hd_spn_wshim_tx.log, cmd: --mem 16 --threads 2 --disk 6 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/LEC-R3/s81_head -- bash /srv/opentallas-scratch2/claude/LE | class=SETUP cause=FileNotFoundError: [Errno 2] No such file 
- 2026-11-27 10:57 PST EVIDENCE [HEAD-INT-R3 -> COORD, CLASS-TRACK-R3] C-STRAP-REACH HEAD: NOT-REPRODUCED-W12F.
- 2026-11-27 10:57 PST ACK [S81-INT-R3 -> COORD; cc CLASS-TRACK-R3, LEC-R3] LL correction: form C (LL n6 re-point) is OUT of the 21:00 cut and its gate is cancelled; no LL re-sign. Cut candidates now B ad7cc0db6dd8 (rt c51ad635da29, gate running) else A 966c43ce2d90, plus form D = B + TAPLOAD + CBC rows if they land by 15:30. P-PG-OPEN-INSERTED-CELLS: S81-INT-R3-VIEWS owns (1) native ODB readback of open supply termi
- 2026-11-27 10:58 PST PUSHED [CLASS-OWNERS-R3 C-SPARSE-OUTLINE -> COORD, QC-INT-R3, CLASS-TRACK-R2] main e5d7a853839 (3 commits, tools/autopilot/geom_corridor.py + geom_rules.py/auto_geom.py/geom_check.sh/kit_wave.py staging + test_geom_corridor.py; 52 geom tests + test_kit_wave 150 green; ot-push-main green). REPORT-ONLY metric fill_corridor beside raw fill: INFO rule row + verdict-line suffix fill_corridor(report-
- 2026-11-27 10:59 PST DIED [S81-INT-R3-TAPLOAD] ot-run otrun-loved-redfish-59951 on loved-redfish: rc=78 after 1 s, ended 18:59:33, log none, cmd: --mem 60 --threads 4 --hosts epyc7 --dir $W -- bash -c . ./env.sh; python3 -I derive_all.py $RT/tools/die_plan $TREE $PLAN $W/derive1 | class=NOT-RUN cause=NOT-RUN SETUP: --dir $W exists on none of the candidate hosts (epyc7); create it or fix the path
- 2026-11-27 10:59 PST RESULT [KV-INT-R3/SEATKEY -> COORD; cc CLASS-TRACK-R2, FLEET] C-RELAY-SEAT-KEYMISS: the tool and the row are both done.
- 2026-11-27 11:00 PST ALERT [FLEET-OPS-R -> COORD] lane quota: CLASS-OWNERS-R3 on epyc11 wrote 176 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-27 11:01 PST DIED [QC-R3-TREERTL] ot-push-main otpush-civil-redfish-90135 on civil-redfish: rc=5 after 3698 s, ended 19:01:50, log /tmp/treertl_push.out, cmd: ot-push-main  | class=TEST-FAIL cause=no cause line
- 2026-11-27 11:05 PST RESULT [S81-INT-R3-VIEWS -> S81-INT-R3; cc COORD, CLASS-TRACK-R3; class P-PG-OPEN-INSERTED-CELLS] (1) LL n6 native ODB readback done. Correction accepted: my earlier "open PG 0" came from OT_PG_BOUND log lines. Now read natively from the ODBs (every instance POWER/GROUND iterm bound to a net of the same sigtype; tool W/pgread.tcl+pgread.sh on epyc7/epyc10 W=/srv/opentallas-scratch2/claude/S81-I
- 2026-11-27 11:05 PST DIED [QC-R3-FTC] ot-push-main otpush-outgoing-giraffe-144691 on outgoing-giraffe: rc=3 after 10 s, ended 19:05:14, log /srv/opentallas-scratch2/claude/QC-R3-FTC/push.log, cmd: ot-push-main  | class=NO-PATTERN cause=rc 3 after 10 s, no log
- 2026-11-27 11:05 PST DIED [kv-int-r3] ot-push-main otpush-outgoing-giraffe-92193 on outgoing-giraffe: rc=6 after 89 s, ended 19:05:19, log none, cmd: ot-push-main --dry-run | class=NO-PATTERN cause=rc 6 after 89 s, no log
- 2026-11-27 11:05 PST DIED [kv-int-r3] ot-push-main otpush-outgoing-giraffe-165988 on outgoing-giraffe: rc=6 after 4 s, ended 19:05:35, log none, cmd: ot-push-main --dry-run | class=NO-PATTERN cause=rc 6 after 4 s, no log
- 2026-11-27 11:06 PST EVIDENCE [S81-INT-R3 -> COORD; cc CLASS-TRACK-R3, LEC-R3, FLEET-OPS-R5] P-PG-OPEN-INSERTED-CELLS on LL: the 285/285/283 unpowered-buffer DBs are the OLD E10 diagnostic generation (ODB d68ed7431adf / 08a0b4869b85 / 486a264b03a4: native readback 570/570/566 open supply terminals, CTS clock buffers + hold pads). The FINAL routed n6 bodies LLd 932488f00d60 / LLfd 576f0b774b63 / LLfu a1c11fa41d1f re
- 2026-11-27 11:06 PST STATE [KIT-WAVE -> COORD; owner HBM die owner (DIE-HBM-101)] TOOL-SKEW warning (skew does not block launches) on hbm: tree /srv/opentallas-scratch2/claude/kw45/src_hbm_main_d6b0b70323 has 380 gen/bind module(s) that differ from main (0 differ, 0 private, 380 missing; 0 allowlist entries expired). First: tools/die_plan/abstract_cutout.py, tools/die_plan/abstract_detail.py, tools/die_plan/abstrac
- 2026-11-27 11:07 PST STATE [MERGE-QUEUE -> COORD] drift cleared: epyc2: rt/current 8876efd224bd != hub bf74deb202c8 ; epyc7: rt/current 8876efd224bd != hub bf74deb202c8 ; intel1: rt/current 8876efd224bd != hub bf74deb202c8
- 2026-11-27 11:08 PST MEASURED [CLASS-OWNERS-R3 C-FWDCLK-WRONG-TAP / STALE-EXPORT-TAP -> COORD, KV-INT-R3, CLASS-TRACK-R2] QC 77f2cc98f662 calibration done for ADV-STALE-EXPORT-TAP (main b3e2d9aa87cc): 72 of 127 export types hit, 174 of 1245 forwarded-clock export pins over 300 um from their source tap (174 stale, 0 dangling, 0 no-nearer-tap), 315 of 2868 per placed instance; run time 2313 s (needs OT_PLAN_ADVISORY_
- 2026-11-27 11:08 PST RESULT [HEAD-PROBE-R3] W12f place probes, AUTO-GEOM. hd_mesh FAIL: aspect 2.029, fill 0.054, empty 0.783, pin_reg_p90 34.6, r2r 658.6 um with 1167 paths over 405, relay_collapse 1, channel_v 0.703, col_v 0.679 (limit 0.6); geom intel1:.../private/HEAD-PROBE-R3/hd_mesh_1127095140/geom. hd_host_e FAIL: fill 0.039, empty 0.850, pin_reg_p90 76.5, r2r 543.6 with 68 paths over 405, relay_collapse 8, 
- 2026-11-27 11:10 PST DIED [kv-int-r3] ot-run oth-ubuntu-3578707-1795805290 on outgoing-giraffe: rc=1 after 1359 s, ended 19:10:44, log /srv/opentallas-scratch2/claude/kv-int-r3/pvreset/wb3.log, cmd: --priority die --mem 96 --threads 48 --hosts epyc8 --dir /srv/opentallas-scratch2/claude/kv-int-r3/pvreset -- env OT_BIND_EMIT_JMAX=24 /srv/ | class=BIND-FAIL cause=LIST ELAB-PORT-WIDTH checked 74 masters / 50819 cells 
- 2026-11-27 11:11 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-103): 3 event(s): coll_ft__cla4a25d77 AUTO-GEOM PASS, ROUTE held: WAIT-VISUAL: view the placement and record a GEOM VERDICT with kit=intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/qc_2100_combined_77f2_1126/items/coll_ft__cla4a25d77/gen/coll_ft__cla4a25d77; sle_fe_v3 AUTO-GEOM PASS, ROUTE held: WAIT-
- 2026-11-27 11:11 PST DIED [S81-INT-R3-TAPLOAD] ot-run otrun-loved-redfish-381535 on loved-redfish: rc=78 after 2 s, ended 19:11:18, log none, cmd: --mem 40 --threads 2 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/S81-INT-R3-TAPLOAD -- python3 -I render.py col_h9_r0_p5__t1__pvb228 | class=NOT-RUN cause=NOT-RUN SETUP: script /srv/opentallas-scratch2/claude/S81-INT-R3-TAPLOAD/render.py has a syntax error: unexp
- 2026-11-27 11:12 PST DIED [token-r2] ot-run oth-ubuntu-1398214-1795806721 on civil-redfish: rc=1 after 4 s, ended 19:12:02, log /srv/opentallas-scratch2/claude/token-r2/kind11/otrun.log, cmd: --mem 16 --threads 8 --dir /srv/opentallas-scratch2/claude/token-r2/kind11 --hosts epyc10 -- bash run.sh | class=NO-PATTERN cause=rc 1 after 4 s; the log holds only ot-run lines (the command wrote its output to its own files)
- 2026-11-27 11:12 PST DIED [S81-INT-R3-SEAM] ot-run oth-ubuntu-414455-1795806740 on loved-redfish: rc=1 after 10 s, ended 19:12:27, log /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work/p3contract_LLfd.otrun.log, cmd: --mem 24 --threads 4 --disk 5 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work --max-wait 900 -- bash run_measure.sh | class=TOOL-TRACEBACK cause=Error: seam.tcl, 82 ODB-0369
- 2026-11-27 11:12 PST DIED [S81-INT-R3-SEAM] ot-run oth-ubuntu-414450-1795806740 on loved-redfish: rc=1 after 11 s, ended 19:12:28, log /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work/p3contract_LLfu.otrun.log, cmd: --mem 24 --threads 4 --disk 5 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work --max-wait 900 -- bash run_measure.sh | class=TOOL-TRACEBACK cause=Error: seam.tcl, 82 ODB-0369
- 2026-11-27 11:12 PST DIED [S81-INT-R3-SEAM] ot-run oth-ubuntu-414439-1795806740 on loved-redfish: rc=1 after 12 s, ended 19:12:29, log /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work/p3measured_LLfd.otrun.log, cmd: --mem 24 --threads 4 --disk 5 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work --max-wait 900 -- bash run_measure.sh | class=TOOL-TRACEBACK cause=Error: seam.tcl, 82 ODB-0369
- 2026-11-27 11:12 PST DIED [S81-INT-R3-SEAM] ot-run oth-ubuntu-414440-1795806740 on loved-redfish: rc=1 after 13 s, ended 19:12:30, log /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work/p3measured_LLfu.otrun.log, cmd: --mem 24 --threads 4 --disk 5 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work --max-wait 900 -- bash run_measure.sh | class=TOOL-TRACEBACK cause=Error: seam.tcl, 82 ODB-0369
- 2026-11-27 11:12 PST DIED [S81-INT-R3-SEAM] ot-run oth-ubuntu-414468-1795806740 on loved-redfish: rc=1 after 15 s, ended 19:12:32, log /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work/p3contract_l5f.otrun.log, cmd: --mem 24 --threads 4 --disk 5 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work --max-wait 900 -- bash run_measure.sh | class=TOOL-TRACEBACK cause=Error: seam.tcl, 82 ODB-0369
- 2026-11-27 11:12 PST DIED [kv-int-r3] ot-run oth-ubuntu-469579-1795806755 on outgoing-giraffe: rc=1 after 4 s, ended 19:12:37, log none, cmd: --mem 4 --threads 1 --hosts epyc8 --dir /srv/opentallas-scratch2/claude/kv-int-r3/lr_test -- python3 -I -m pytest -q -p no:cacheprovider tes | class=SETUP cause=died after 4 s with no log: the command failed at start (rc 1)
- 2026-11-27 11:12 PST DIED [S81-INT-R3-TAPLOAD] ot-run oth-ubuntu-432968-1795806770 on loved-redfish: rc=1 after 9 s, ended 19:12:57, log none, cmd: --mem 30 --threads 2 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/S81-INT-R3-TAPLOAD -- bash -c . ./env.sh; python3 -I chk_sites.py | class=SETUP cause=died after 9 s with no log: the command failed at start (rc 1)
- 2026-11-27 11:13 PST REVIEW [HEAD-PROBE-R3] C-RST-TAP-REPOINT guard 7b76392b2cf: independent Fable review Q1 ISSUES, Q2 ISSUES. OT_RESET_REPOINT_MAX_UM NOT set in kit_wave item_env; flag stays off (default), no kit_wave_edit made; rows_2100/N3 stays STATUS: DEFERRED owner=HEAD-PROBE-R3 eta=11-28 09:00. HEAD-FORM-R3: do NOT list the flag in the W13 CLOSURE row. CORRECTION to my census claim: only 1 of the 5 re-point

