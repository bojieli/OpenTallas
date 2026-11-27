# COORD snapshot 2026-11-27 10:45 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: f472f2d8d7a6
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
- CLAUDE-RESUME-1127: handoff 102 min old; last post none in recent queue
- EXPLORER-STORE-R1: handoff 597 min old; last post 2026-11-26 22:07 STATE
- HEAD-INT-R2-HOSTW-CAPACITY-1127: handoff 415 min old; last post none in recent queue
- PREPARED-PUBLICATION-PLACE: handoff 692 min old; last post none in recent queue
- PUBLISH-GATE: handoff 597 min old; last post 2026-11-26 23:27 READY
- QC-ALLFIX-COLL: handoff 423 min old; last post none in recent queue
- ROM-WEIGHTS-1119: handoff 597 min old; last post 2026-11-26 23:36 STATE

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 195; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 46 live
- LEC-R3 agent ? last post 2026-11-27 10:44 RESULT
- HEAD-PROBE-R3 agent ? last post 2026-11-27 10:44 DIED
- CLASS-OWNERS-R3 agent ? last post 2026-11-27 10:41 PUSHED
- QC-R3-STA agent ? last post 2026-11-27 10:40 DIED
- S81-INT-R3-SEAM agent ? last post 2026-11-27 10:38 DIED
- QC-R3-TT agent ? last post 2026-11-27 10:38 START
- MERGE-QUEUE agent ? last post 2026-11-27 10:35 MERGED
- s81-int-r3-xr agent ? last post 2026-11-27 10:34 DIED
- S81-INT-R3-BITORDER agent ? last post 2026-11-27 10:31 PROGRESS
- qwen_compute agent ? last post 2026-11-27 10:30 KIT-WAVE
- HOLDGEN-1115 agent ? last post 2026-11-27 10:30 ALERT
- QC-INT-R3 agent ? last post 2026-11-27 10:28 DECISION-NEEDED
- FLEET-OPS-R agent ? last post 2026-11-27 10:26 ALERT
- kv-int-r3 agent ? last post 2026-11-27 10:25 DIED
- KIT-WAVE agent ? last post 2026-11-27 10:24 STATE
- QC-R3-FTC agent ? last post 2026-11-27 10:24 DIED
- NOPROG-FIX-1115 agent ? last post 2026-11-27 10:22 STATE
- KV-INT-R3 agent ? last post 2026-11-27 10:20 LAUNCH
- FLEET-OPS-R5 agent ? last post 2026-11-27 10:19 DIED
- C-FENCE-GEOM-ILLEGAL agent ? last post 2026-11-27 10:18 MEASURED
- CBC-RULES-1119 agent ? last post 2026-11-27 10:17 HOURLY
- QC-R3-SULANE agent ? last post 2026-11-27 10:17 DIED
- C-OVERSIZE agent ? last post 2026-11-27 10:17 PUSHED
- C-TAP-LOAD agent ? last post 2026-11-27 10:17 PUSHED
- SMELL-WATCH agent ? last post 2026-11-27 10:15 RENDER
- P-FLAG-SCHEMA-UNREGISTERED agent ? last post 2026-11-27 10:14 PUSHED
- P-PLAN-AHEAD-OF-RTL agent ? last post 2026-11-27 10:13 PUSHED
- HEAD-INT-R3 agent ? last post 2026-11-27 10:06 DIED
- QC-R3-LEG405 agent ? last post 2026-11-27 10:06 COORDINATION
- QC-R3-TAPS agent ? last post 2026-11-27 10:04 DIED
- S81-INT-R3-VIEWS agent ? last post 2026-11-27 10:04 RESULT
- HOLD-OVERDUE agent ? last post 2026-11-27 10:01 ALERT
- HEAD-PART-R3 agent ? last post 2026-11-27 10:00 DIED
- S81-INT-R3-PROBE agent ? last post 2026-11-27 09:59 SIBLINGS
- HEAD-TILE-R3 agent ? last post 2026-11-27 09:57 START
- FLOW-HEALTH-1 agent ? last post 2026-11-27 09:56 NEEDS-ACTION
- PLAN-CONFIG-DRIFT agent ? last post 2026-11-27 09:55 ALERT
- S81-INT-R3 agent ? last post 2026-11-27 09:52 FORM-A
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
## FAILURES · unsigned cores and types by class (auto, 2026-11-27 10:45 PST)
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
  - type sle_ctl__cla4f6f12f · CANCELLED geom QUEUE-CANCELLED @ 2026-11-23 11:21 (95.4h) · owner QC-PLAN
  - type sle_fw_v2__cl69f5e854 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-23 17:19 (89.4h) · owner QC-PLAN
  - type slw_fw_v1__clf51c11d8__cl592e3d37 · CANCELLED geom GHOST @ 2026-11-24 11:42 (71.1h) · owner unowned
  - type slw_fw_v3 · CANCELLED geom SUPERSEDED @ 2026-11-24 11:50 (70.9h) · owner KIT-WAVE-1
  - type slw_fe_v1__clfe325744__cl08d14f0d · CANCELLED geom SUPERSEDED @ 2026-11-24 20:33 (62.2h) · owner QC-STALE-GEOM
  - type native59 · CANCELLED geom SUPERSEDED @ 2026-11-25 19:34 (39.2h) · owner KIT-WAVE-1
  - type coll_ucie · CANCELLED geom QUEUE-CANCELLED @ 2026-11-26 09:19 (25.4h) · owner KIT-WAVE-1
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 250 commits / missing none
- TOOLS-LAG qwen_kvsys 287 commits / missing none
- TOOLS-LAG s81_head 1 commits / missing none
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 5278 taps in 50 types, 144 over 1650 sinks; insertion max 696 ps (p50 269, p90 284), skew max 176 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 596 taps in 6 types, 17 over 1650 sinks; insertion max 516 ps (p50 258, p90 289), skew max 208 ps; oversized taps: ins max 412 ps, skew max 100 ps
- TAP-INSERTION s81: 3591 taps in 55 types, 130 over 1650 sinks; insertion max 1000 ps (p50 466, p90 498), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 639 taps in 15 types, 9 over 1650 sinks; insertion max 613 ps (p50 458, p90 468), skew max 171 ps; oversized taps: ins max 466 ps, skew max 62 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-27 10:05 | tolera L16.13/112 units0 free419G | key-ca L18.68/112 units5 free587G | dear-c L3.05/128 units0 free375G | loved- L17.94/96 units8 free554G | outgoi L42.03/96 units17 free564G | renewe L1.18/96 units0 free1390G | civil- L15.50/96 units6 free1207G | viable L7.85/96 units0 free2010G | HOST-CAPS ok (9 owned caps); expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (197.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (197.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (197.9 h left); epyc7:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (197.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (197.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (197.9 h left)
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  332G  113G  75% /
    10:45:19 up 34 days,  6:25, 148 users,  load average: 16.25, 15.20, 15.66

## ot-run status
    ot-run status: epyc2 admits 946 GB (avail 987, reserve 0, fresh 0, peak 0) load 3/128 run 0 threads 8/128 root 91% scratch 368 GB
    intel1 admits 781 GB (avail 911, reserve 0, fresh 0, peak 68) load 25/112 run 13 threads 140/112 root 21% scratch 513 GB
    localhost admits 814 GB (avail 943, reserve 0, fresh 0, peak 0) load 16/112 run 0 threads 14/112 root 75% scratch 210 GB
    epyc7 admits 774 GB (avail 896, reserve 0, fresh 0, peak 0) load 35/96 run 14 threads 224/96 root 35% scratch 418 GB
    epyc8 admits 718 GB (avail 849, reserve 0, fresh 0, peak 474.6) load 62/96 waiters 2:24 GB oldest 0.0 h run 22 threads 502/96 root 50% scratch 447 GB
    epyc9 admits 939 GB (avail 987, reserve 0, fresh 0, peak 0) load 2/96 run 0 threads 47/96 root 40% scratch 1383 GB
    epyc10 admits 838 GB (avail 897, reserve 0, fresh 0, peak 0) load 11/96 run 8 threads 178/96 root 48% scratch 1204 GB
    epyc11 admits 917 GB (avail 966, reserve 0, fresh 0, peak 0) load 7/96 run 3 threads 152/96 root 7% scratch 1930 GB
    epyc12 admits 896 GB (avail 945, reserve 0, fresh 0, peak 1362.9) load 13/96 run 7 threads 216/96 root 36% scratch 1039 GB
    next 16-thread 32 GB job -> epyc2

## KIT-WAVE (autopilot log, last 6)
    2026-11-27 10:40:27 PST AUTOPILOT: KIT-WAVE PLAN-ROWS s81_head: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-27 10:40:38 PST AUTOPILOT: KIT-WAVE WAIT-PLAN-VISUAL: missing fresh plan image verdict for qwen_kvsys/kv3_hub_Wi form 538657e322f857559ece90254d3abe79ce95b2a6a08a941b07d8e1e14b2edc1f; request 
    2026-11-27 10:40:57 PST AUTOPILOT: KIT-WAVE RETRY-KEY-LAUNCH qwen_compute/coll_ftc: explicit retry key (fix named or INFRA) in the die config overrides SKIP-SAME-INPUT
    2026-11-27 10:41:01 PST AUTOPILOT: KIT-WAVE RETRY-KEY-LAUNCH qwen_compute/slw_stm_v3: explicit retry key (fix named or INFRA) in the die config overrides SKIP-SAME-INPUT
    2026-11-27 10:43:25 PST AUTOPILOT: KIT-WAVE HOLD-AUDIT HELD-BUT-LAUNCHED=0 HOLD-LEAK=0 TERM-UNREACHABLE=0 TERM-VARIANT=0 HOLD-SUPERSEDED=0 HOLD-ZERO-MATCH=0 PROOF-HELD=0 PILOT-DEADLOCK=0
    2026-11-27 10:43:46 PST AUTOPILOT: UNDER-USE HELD SKIP-HELD 6: s81/serdes__t3 1 [owner S81-SERDES-TAPSKEW, 117.8 h, eta 11-25 00:30, FLAGGED OVERDUE]; s81/serdes__t16 1 [owner S81-SERDES-TAPSKEW, 117.

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-27 10:05 PST DIED [QC-R3-SULANE] ot-run oth-ubuntu-1417586-1795802489 on outgoing-giraffe: rc=1 after 218 s, ended 18:05:04, log /srv/opentallas-scratch2/claude/QC-R3-SULANE/p9row/g3.otrun.log, cmd: --priority die --mem 256 --threads 48 --disk 40 --hosts epyc8 --dir /srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_compute_qc_j | class=NO-PATTERN cause=COMBINE GATE NOT-READY ["row apply rc 1 (scri
- 2026-11-27 10:05 PST PROGRESS [S81-INT-R3-BITORDER C-STATION-BIT-SCRAMBLE -> COORD; cc S81-INT-R3] 89fb176f40f (reporting branch) is already on main (is-ancestor main true). Code done in worktree epyc11:/srv/opentallas-scratch2/claude/S81-INT-R3-BITORDER/wt branch claude/s81-int-r3-bitorder-1127 @73059b534b3 (not on main yet, push waiting on a sparse-cone widen / CLASS-OWNERS-R3 schema overlap): (1) flag plumbing: 
- 2026-11-27 10:06 PST DIED [HEAD-INT-R3] ot-run oth-ubuntu-389384-1795801070 on open-snipe: rc=2 after 1722 s, ended 18:06:29, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/form/w12f_rt4f61.otrun.log, cmd: --priority die --hosts epyc12 --mem 120 --threads 48 --disk 20 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/form -- env RUN=w12f_rt4f61 | class=NO-PATTERN cause=/srv/opentallas-scratch2/claude/HEAD-INT-R3/f
- 2026-11-27 10:06 PST COORDINATION [QC-R3-LEG405 -> QC-R3-SULANE; cc QC-INT-R3] ACK your 10:02: you gate p9 (classes C-LEG405 + P-ROW-POSTTAP-REMAP), I do not gate a second copy. For the two West place-only probes (slw_su_c cl19bb38ef, cl92142dac: the only missing evidence for 0 over-405 first hops on all three siblings, see my correction post: 128-155 p1-bus launch flops are placer-mobile) I need, once g4+ is READY
- 2026-11-27 10:06 PST PUSHED [CLASS-OWNERS-R3 C-FENCE-GEOM-ILLEGAL -> COORD, HEAD-INT-R3, QC-INT-R3, S81-INT-R3, CLASS-TRACK-R2, HEAD-EAST-R4] main efc6b92330fa (R3-FENCE). (1) SAFETY fix live, no flag: every emitted fence/region box snaps OUTWARD onto the site/row grid from the core origin (outward keeps every inside member inside; edges already on grid are byte-identical; edges inside the core never pushed past th
- 2026-11-27 10:07 PST DIED [CLASS-OWNERS-R3] ot-push-main otpush-viable-ram-1852355 on viable-ram: rc=3 after 558 s, ended 18:07:08, log none, cmd: ot-push-main  | class=NO-PATTERN cause=rc 3 after 558 s, no log
- 2026-11-27 10:09 PST DIED [QC-R3-SULANE] ot-run oth-ubuntu-1626383-1795802776 on outgoing-giraffe: rc=1 after 200 s, ended 18:09:32, log /srv/opentallas-scratch2/claude/QC-R3-SULANE/p9row/g4.otrun.log, cmd: --priority die --mem 256 --threads 48 --disk 40 --hosts epyc8 --dir /srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_compute_qc_j | class=NO-PATTERN cause=COMBINE GATE NOT-READY ["row apply rc 1 (scri
- 2026-11-27 10:13 PST PUSHED [P-PLAN-AHEAD-OF-RTL R3-SCHEMA -> COORD, S81-INT-R3, CLASS-TRACK-R2] main a5e96bf75092: report-only PRE advisory ADV-PARAM-NOT-IN-RTL (tools/die_plan/adv_param_not_in_rtl.py, registered in plan_advisory CHECKS, 7 tests). For every partition_types[T].leaf_params key it checks the master declares it (tree RTL module header/body, as-built param_regen.declare, as-built netlist instances); a 
- 2026-11-27 10:14 PST PUSHED [P-FLAG-SCHEMA-UNREGISTERED R3-SCHEMA -> COORD, CLASS-TRACK-R2, S81-INT-R3, HEAD-INT-R3, QC-INT-R3, KV-INT-R3] main a5e96bf75092: tools/die_plan/test_schema_generator_keys.py statically (AST) collects every plan key tools/die_plan reads off raw/plan roots (get/[]/in, aliases, items/values loops) and fails if a closed schema node lacks it; 7 tests incl. negative self-tests (fake top-level
- 2026-11-27 10:15 PST SMELL [SMELL-WATCH -> HEAD-PROBE-R3; cc COORD] 1 kit-class(es): hd_spn_wshim_tx 4_1_cts [CTS] epyc10: post-CTS hold -64 ps (< -50); render epyc10:/srv/opentallas-scratch2/claude/HEAD-INT-R3/cts/hd_spn_wshim_tx/gen/hd_spn_wshim_tx/smell_review/4_1_cts-1127-1015PST (rendering). Early trigger (OWNER 04:1x): start the visual review and the structural root-cause fix now; the kits keep running and ar
- 2026-11-27 10:15 PST RENDER [SMELL-WATCH -> HEAD-PROBE-R3; cc COORD] 1 checkpoint render(s) started: hd_host_n PLACE-GP on epyc11: epyc11:/srv/opentallas-scratch2/claude/HEAD-INT-R3/cts/hd_host_n/gen/hd_host_n/vis_review/place-gp-1127-1015PST (floorplan.png, density.png, SMELL.txt with the GRT per-layer overflow, written when the job ends; render.log there). Launch your own Fable/Opus review (OWNER 04:5x: self-laun
- 2026-11-27 10:16 PST PUSHED [CLASS-OWNERS-R3 C-STATION-OUTSIDE-OUTLINE -> COORD, KV-INT-R3] main f0c79e2abf8d (R3-FENCE). Finding: INOUTLINE (WARN unless OT_PRE_INOUTLINE_BLOCK=1) and FAIL ADV-SITE-OFF-OUTLINE already run whole-plan in plan_gate_pre, but check(types=...) scope_lines drops every line of a type outside the scope, so hroot/hg_v3 outline violations were invisible to a scoped row. Fix, report-only: scop
- 2026-11-27 10:16 PST DONE [S81-INT-R3-BITORDER -> COORD; cc S81-INT-R3] ot-push-main: PUSHED main @673abea96b0 (flag plumbing + warnings + tests; OT_FT_LANE_MONO stays default OFF, flag-off placement byte-identical by golden digest). Rebased clean on top of CLASS-OWNERS-R3 test_schema_generator_keys; my kit_flags.py/test_kit_flag_registry.py covers env + budgets keys of gen_phys. Worktree epyc11:/srv/opentallas-scr
- 2026-11-27 10:17 PST PUSHED [C-OVERSIZE] [CLASS-OWNERS-R3 C-OVERSIZE -> COORD, S81-INT-R3, CLASS-TRACK-R2] main a99f6d58b18 (commit a1de41859b3): ADV-FP-OVERSIZE now reads PRECHECK flop-cache netlist flops (default on, OT_FP_OVERSIZE_NETLIST=0 off), report-only; 3 new tests. Live plans before->after: S81 c085ccb76d2e 4->8 (before kv_leaf t1/t3/t4/t5 false positives; after svc_lo rs t5/t7, rs_w t1 plus svc_hi rs t1/
- 2026-11-27 10:17 PST HOURLY [CBC-RULES-1119 -> COORD; cc S81-DIE-R3, QC-PLAN-R3, KV-D23-COMPOSE, FABLE-FIX-HEAD-MESH-O] CBC-FALLBACK unsigned S81 119 types; CBC-FALLBACK (r713: >= 2 failed design fix rounds -> close-by-construction form; die owner folds tools/die_plan/cbc_pass.py rows into the next event): S81 col_h9_r1: 60 unsigned (col_h9_r1__t1__cl49d7a23e__pv047ea3b3,col_h9_r1__t1__cl49d7a23e__pv0a45e191,col_h9
- 2026-11-27 10:17 PST DIED [QC-R3-SULANE] ot-run oth-ubuntu-1834680-1795803092 on outgoing-giraffe: rc=1 after 344 s, ended 18:17:13, log /srv/opentallas-scratch2/claude/QC-R3-SULANE/p9row/g5.otrun.log, cmd: --priority die --mem 256 --threads 48 --disk 40 --hosts epyc8 --dir /srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_compute_qc_j | class=SETUP cause=COMBINE GATE NOT-READY ["normalize crashed: FileNo
- 2026-11-27 10:17 PST PUSHED [C-TAP-LOAD] [CLASS-OWNERS-R3 C-TAP-LOAD -> COORD, S81-INT-R3, HEAD-INT-R3, QC-INT-R3, KV-INT-R3, CLASS-TRACK-R2] main a99f6d58b18: tap_class_census gate is now the per-type kit cap gen_phys._tap_cap (gen env OT_TAP_MAX_SINKS, else clock.tap_max_sinks, else 1500 density/3000 grid, tap_grid bank_sinks clamp) instead of constant 5000; new UNDER-LOAD floor = tap_post_merge_min_sinks, else t
- 2026-11-27 10:18 PST MEASURED [C-FENCE-GEOM-ILLEGAL] [CLASS-OWNERS-R3 -> COORD, CLASS-TRACK-R2, all INT-R3] FENCE-GEOM advisory (main efc6b92330fa) on the exact LIVE plan JSONs (epyc11 CLASS-OWNERS-R3/ledger/plans): S81 c085ccb76d2e 0 (403 types, no static regions), HEAD 607dd5dd5c82 0 (27), QC 77f2cc98f662 0 (130), KV 5bee15cebae2 0 (93; 1 type with logic_cluster_rects_um, clean). Static plan regions are clean; th
- 2026-11-27 10:18 PST DIED [FLEET-OPS-R5] ot-push-main otpush-tolerant-swine-3017638 on tolerant-swine: rc=4 after 5 s, ended 10:18:43, log none, cmd: ot-push-main  | class=NO-PATTERN cause=rc 4 after 5 s, no log
- 2026-11-27 10:19 PST DIED [FLEET-OPS-R5] ot-push-main otpush-tolerant-swine-3047547 on tolerant-swine: rc=4 after 1 s, ended 10:19:13, log none, cmd: ot-push-main  | class=NO-PATTERN cause=rc 4 after 1 s, no log
- 2026-11-27 10:19 PST RESULT [LEC-R3 -> QC-INT-R3, S81-INT-R3, COORD; cc CLASS-TRACK] (A) QC routed LECs for re-judge, all EQUIVALENT, I1 /srv/opentallas-scratch2/claude/QC-DRT-ECO/lec_r2/: sle_stm_v1 cl27746664 i2 113921/113921 (0 differs, 0 undecided; i2 6_final.v sha prefix 1520479c5535, stm_i2/lec.log); coll_n i3 24049/24049 (da94414db4b5, colln_i3/lec.log); slw_st_b_v1 cl6357f1cc pvffd43fdc i1 239574/239574 (94
- 2026-11-27 10:19 PST DIED [HEAD-PROBE-R3] ot-run oth-ubuntu-3508534-1795803273 on key-cardinal: rc=2 after 319 s, ended 10:19:50, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/cts/hd_st_n3_transit/cts.otrun.log, cmd: --mem 48 --threads 8 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/cts/hd_st_n3_transit/gen --hosts intel1 -- ./run_kit.sh hd_st_n3_tran | class=ROUTE-FAIL cause=FAIL_route make exit 2 (see run_c
- 2026-11-27 10:20 PST LAUNCH [KV-INT-R3 -> COORD] Five goal-cts private probes are live on intel2, each as a systemd unit named runitem-<type>.
- 2026-11-27 10:21 PST DIED [QC-R3-FTC] ot-run oth-ubuntu-1384467-1795802447 on outgoing-giraffe: rc=1 after 1265 s, ended 18:21:49, log /srv/opentallas-scratch2/claude/QC-R3-FTC/g1_ftn.log, cmd: --priority die --hosts epyc8 --no-spill --threads 12 --mem 96 --disk 24 --dir /srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_co | class=NO-PATTERN cause=ROW-GATE NOT-READY lane=QC-R3-FTC die=qwen_compute plan=7c
- 2026-11-27 10:21 PST DIED [QC-R3-FTC] ot-run oth-ubuntu-1434430-1795802510 on outgoing-giraffe: rc=1 after 1206 s, ended 18:21:53, log /srv/opentallas-scratch2/claude/QC-R3-FTC/g3_f012.log, cmd: --priority die --hosts epyc8 --no-spill --threads 12 --mem 96 --disk 24 --dir /srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_co | class=NO-PATTERN cause=ROW-GATE NOT-READY lane=QC-R3-FTC die=qwen_compute plan=0
- 2026-11-27 10:22 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-27 10:22 PST: 37 running jobs, PROGRESSING 36, PLATEAU 1, SLOW 0, NO-PROGRESS 0 (this table is advisory; the separate noprog.timer watchdog (noprog_watchdog.py) DOES ot-heavy-stop NO-PROGRESS jobs, per-host log ~/.local/state/noprog/actions.jsonl); table lanes/NOPROG.tsv
- 2026-11-27 10:24 PST PUSHED [CLASS-OWNERS-R3 C-STREET -> COORD, HEAD-INT-R3, CLASS-TRACK-R2] main ddba1015b8b adv_fp_floorplan: new WARN tag ADV-FP-STREET-BUS (report-only, default on, OT_STREET_BUS=0 off; counted C-STREET tag unchanged). Why HEAD W12f 607dd5dd5c82 read 0: street_worst counts only internal_stations/ft_slots lanes (lep0N 4 lanes, host_w 0, ctl_n coreless) and fails only above 1.0 at 0.6 usable, whil
- 2026-11-27 10:24 PST DIED [QC-R3-FTC] ot-run oth-ubuntu-1384466-1795802447 on outgoing-giraffe: rc=1 after 1424 s, ended 18:24:28, log /srv/opentallas-scratch2/claude/QC-R3-FTC/g2_all.log, cmd: --priority die --hosts epyc8 --no-spill --threads 12 --mem 96 --disk 24 --dir /srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_co | class=NO-PATTERN cause=ROW-GATE NOT-READY lane=QC-R3-FTC die=qwen_compute plan=47
- 2026-11-27 10:24 PST PUSHED [CLASS-OWNERS-R3 C-RELAY-SEAT-KEYMISS -> COORD, all INT-R3, CLASS-TRACK-R2, KV-INT-R3] main ddba1015b8b tools/die_plan/selector_census.py (new, REPORT-ONLY exit 0): matches kit seat (rs_place_all + plan relay_sites), rank (rs_rank_line + relay_rank_sites), Tcl selector lists (set *_cone/_prefix/_pattern/_regex/_unit/_selector), landing band prefixes and plan *pattern/regex keys against t
- 2026-11-27 10:24 PST STATE [KIT-WAVE -> COORD; owner HBM die owner (DIE-HBM-101)] TOOL-SKEW warning (skew does not block launches) on hbm: tree /srv/opentallas-scratch2/claude/kw45/src_hbm_main_d6b0b70323 has 379 gen/bind module(s) that differ from main (0 differ, 0 private, 379 missing; 0 allowlist entries expired). First: tools/die_plan/abstract_cutout.py, tools/die_plan/abstract_detail.py, tools/die_plan/abstrac
- 2026-11-27 10:25 PST DIED [kv-int-r3] ot-run oth-ubuntu-1774648-1795803012 on outgoing-giraffe: rc=1 after 896 s, ended 18:25:04, log /srv/opentallas-scratch2/claude/kv-int-r3/pvreset/pre_2.log, cmd: --priority die --mem 120 --threads 16 --hosts epyc8 --dir /srv/opentallas-scratch2/claude/kv-int-r3/pvreset -- /srv/opentallas-scratch2/clau | class=DESIGN-FAIL cause=WARN ADV-PUB-STALE kv3_pc_v3: published tree 596 re
- 2026-11-27 10:26 PST ALERT [FLEET-OPS-R -> COORD] lane quota: kv-int-r3 on intel1 wrote 52 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-27 10:26 PST ALERT [FLEET-OPS-R -> CLEAN-AGGR; cc COORD] lane quota: kw45 on intel1 wrote 63 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); CLEAN-AGGR prunes superseded event trees and replicas no live or queued row references
- 2026-11-27 10:28 PST DECISION-NEEDED [QC-INT-R3 -> COORD; cc HEAD-INT-R3, S81-INT-R3, CLASS-TRACK-R2; classes C-SPARSE-PARTITION-FILL (= C-SPARSE-OUTLINE / C-FILL-RULE-STRUCTURAL)] I carried out your 09:05 corridor YES, but it does not close the class. QC-R3-FTC measured all six collector instances on 77f2 plus the retained place ODBs. FTc has no unused corridor: pins on all 4 faces, vertical cut 0.882, and only a 
- 2026-11-27 10:30 PST PUSHED [CLASS-OWNERS-R3 P-HOOK-RTL-NET -> COORD, KV-INT-R3, CLASS-TRACK-R2] main 306ca5a7069: tools/die_plan/kit_gen_lint.py hook_status_nets (REPORT-ONLY, rc/verdict unchanged): each placement-hook status net (cland_status in kit landing_placement.tcl) must exist in the kit RTL and not be in a yosys check undriven warning; else gen_lint.json hook_rtl_net list + GEN_LINT WARN line. Tests: test_
- 2026-11-27 10:30 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-103): 14 event(s): sle_hc2__clcc5e3e61 LAUNCHED (kw-qwenco-slehc2clcc5e3e61-1-3948); slw_fw_v2__cl8f84514c LAUNCHED (kw-qwenco-slwfwv2cl8f84514c-1-3999); sle_fe_v3 LAUNCHED (kw-qwenco-slefev3-1-4006); sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9 LAUNCHED (kw-qwenco-slehc2cl9c4c4509clf60c5152pv-1-4022); slw_sc_v1__cl64543eaf__cl5e017c6f LAUNCHED (kw
- 2026-11-27 10:30 PST HOLD-LEAK [-> QC die owner (DIE-QC-103)] qwen_compute/qc-2100-77f2-fw-seats: 1 launched row(s) match a hold record that blocks nothing on this die (stops_off): record qc-2100-77f2-fw-seats key slw_fw_v2__cl8f84514c (launched; hold_items does not carry it); items slw_fw_v2__cl8f84514c. Hold them with dies.qwen_compute.hold_items (kit_wave_edit refuses new records here).
- 2026-11-27 10:30 PST ALERT [HOLDGEN-1115 -> COORD, WAVE-HOLDS-1115] hold audit {'HOLD-LEAK': 2}: HOLD-LEAK qwen_compute/qc-2100-77f2-fw-seats x1: record qc-2100-77f2-fw-seats key slw_fw_v2__cl8f84514c (launched; hold_items does not carry it) items slw_fw_v2__cl8f84514c; HOLD-LEAK qwen_compute/qc-2100-77f2-fw-seats x1: record qc-2100-77f2-fw-seats key slw_fw_v2__cl8537f156 (launched; hold_items does not carry it) it
- 2026-11-27 10:30 PST DIED [S81-INT-R3-SEAM] ot-run oth-ubuntu-3368989-1795804222 on loved-redfish: rc=1 after 29 s, ended 18:30:48, log /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work/base_LLfd.otrun.log, cmd: --mem 24 --threads 4 --disk 5 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work --max-wait 900 -- bash run_measure.sh | class=TOOL-TRACEBACK cause=Error: seam.tcl, 96 port objects 
- 2026-11-27 10:31 PST STATUS [LEC-R3 -> COORD, CLASS-TRACK] 96-kit proof batch input setup fixed: the reset-receipt failure was the rerun mounting the archived kit (no reset receipt or RTL) as /work. New run_prod.sh mounts the located PRODUCER kit (receipt + RTL) as /work and the archived signed gate as /base, current fixed checker (LEC-R2/fix/lec.py sha 411e8b4e), OT_LEC_SUPERSET_VEC=1, after the locator verified p
- 2026-11-27 10:31 PST PROGRESS [S81-INT-R3-BITORDER C-STATION-BIT-SCRAMBLE -> COORD; cc S81-INT-R3] OFF-arm place-only kits running on LIVE c085ccb76d (private-spec goal place, plan visuals GOOD in PLAN-VISUAL-REVIEW.tsv): t4 epyc8 unit s81r3bitorder-t4-off, t1 intel1 s81r3bitorder-t1-off, t3 epyc7 s81r3bitorder-t3-off, leaf t33 epyc7 s81r3bitorder-t33-off-c; ot-run place services kwp-* started 10:20-10:26 PST; spec
- 2026-11-27 10:31 PST DIED [S81-INT-R3-SEAM] ot-run oth-ubuntu-3394540-1795804276 on loved-redfish: rc=1 after 35 s, ended 18:31:49, log /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work/base_LLfd.otrun.log, cmd: --mem 24 --threads 4 --disk 5 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/S81-INT-R3-SEAM/work --max-wait 900 -- bash run_measure.sh | class=NO-PATTERN cause=15# _start in openroad
- 2026-11-27 10:33 PST MEASURED [CLASS-OWNERS-R3 P-PEER-ABI -> COORD, KV-INT-R3, QC-INT-R3, S81-INT-R3, HEAD-INT-R3] Peer ABI census on the four live trees (S81 c085ccb76d2e, HEAD 607dd5dd5c82, QC 77f2cc98f662 bind_1127093611, KV 5bee15cebae2 bind_1126152300), read from bound RTL: 2 pairs, 1 MISMATCH, 1 MATCH. (1) QC-KV:status MISMATCH: QC glue u_d2d_rom = qfd_d2d_static_ovl_sf7_obs1 (status_tx = STATUS-v1) vs KV sys
- 2026-11-27 10:33 PST DIED [CLASS-OWNERS-R3] ot-push-main otpush-viable-ram-2285097 on viable-ram: rc=4 after 148 s, ended 18:33:21, log none, cmd: ot-push-main --dry-run | class=NO-PATTERN cause=rc 4 after 148 s, no log
- 2026-11-27 10:33 PST DIED [s81-int-r3-xr] ot-run oth-ubuntu-953770-1795803408 on open-snipe: rc=1 after 1021 s, ended 18:33:47, log /srv/opentallas-scratch2/claude/s81-int-r3-xr/bind_v5.otrun.log, cmd: --priority die --hosts epyc12 --mem 300 --threads 48 --dir /srv/opentallas-scratch2/claude/s81-int-r3-xr --disk 150 -- bash /srv/opentallas- | class=SETUP cause=FileNotFoundError: [Errno 2] No such file or directory:
- 2026-11-27 10:34 PST DIED [s81-int-r3-xr] ot-run oth-ubuntu-953765-1795803408 on open-snipe: rc=1 after 1037 s, ended 18:34:03, log /srv/opentallas-scratch2/claude/s81-int-r3-xr/g0_v5.otrun.log, cmd: --priority die --hosts epyc12 --mem 120 --threads 16 --dir /srv/opentallas-scratch2/claude/s81-int-r3-xr --disk 20 -- bash /srv/opentallas-s | class=SETUP cause=FileNotFoundError: [Errno 2] No such file or directory: '
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

