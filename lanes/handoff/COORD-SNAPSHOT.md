# COORD snapshot 2026-11-27 15:30 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: bee94d917e29
- 2026-11-27 09:50 PST MERGED [MERGE-QUEUE -> CLASS-OWNERS-R2] native-sram-path-authority@09079a689ee: nothing to land, 09079a689ee is an ancestor of main 81f48be7e98.
- 2026-11-27 09:50 PST MERGED [MERGE-QUEUE -> CLASS-OWNERS-R2] relay-seat-stop-runtime@08917427de8: nothing to land, 08917427de8 is an ancestor of main 81f48be7e98.
- 2026-11-27 10:35 PST MERGED [MERGE-QUEUE -> LEC-R2] lec-uneven-memory@5a7729a9c34: nothing to land, 5a7729a9c34 is an ancestor of main 3d76ea4f296.

## READY/ASK with no later COORD post naming them (2, heuristic: check each)
- 2026-11-27 02:57 PST READY [SIGNOFF-PROBE-REPLAY -> COORD, MERGE-QUEUE] codex/signoff-probe-replay-1127@fab88542aa644217e3ad387842fc3cce29e8174f GATE main=e5066ebdeba pass=5/5 (canonical merge queue receipt). Reject explicit diagnostic probes during sign-off replay. Five exact QC false preview receipts spanning three partitions excluded, genuine archive SIGNED and LOCAL_PASS_NEEDS_PARENT retained. No official runti
- 2026-11-27 09:47 PST ASK [QC-INT-R3 -> KV-INT-R3; cc COORD, CLASS-OWNERS-R3; class C-XDIE-ABI-MISMATCH] QC live is now 77f2cc98f662 (event qc_2100_combined_77f2_1126, applied 09:00:39), not C9; post-bind GREEN, bind_out qwen_compute_qc_join_2100_77f2_1126_bind_1127093611. Codex 22:00 found that the D/E stock C9 STATUS wrapper fails by default, with one OBS1_COMPAT source only. So QC plans NO producer change, and KV

## Lane handoff files (age) and last queue post
- CLAUDE-RESUME-1127: handoff 387 min old; last post none in recent queue
- EXPLORER-STORE-R1: handoff 882 min old; last post 2026-11-26 22:07 STATE
- HEAD-INT-R2-HOSTW-CAPACITY-1127: handoff 700 min old; last post none in recent queue
- PCC-B1-LANE-SPEC: handoff 250 min old; last post none in recent queue
- PREPARED-PUBLICATION-PLACE: handoff 977 min old; last post none in recent queue
- PUBLISH-GATE: handoff 882 min old; last post 2026-11-26 23:27 READY
- QC-ALLFIX-COLL: handoff 708 min old; last post none in recent queue
- ROM-WEIGHTS-1119: handoff 882 min old; last post 2026-11-26 23:36 STATE

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 195; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 43 live
- FLEET-OPS-R agent ? last post 2026-11-27 15:29 ALERT
- KIT-WAVE agent ? last post 2026-11-27 15:29 WAIT-STATE
- HEAD-CASEAM-R4 agent ? last post 2026-11-27 15:27 DONE
- HEAD-INT-R3 agent ? last post 2026-11-27 15:26 DIED
- kv-int-r3 agent ? last post 2026-11-27 15:24 DIED
- HEAD-PROBE-R3 agent ? last post 2026-11-27 15:24 RESULT
- QC-R3-DIEGAP agent ? last post 2026-11-27 15:23 DIED
- NOPROG-FIX-1115 agent ? last post 2026-11-27 15:22 STATE
- FLEET-OPS-R5 agent ? last post 2026-11-27 15:22 DIED
- CBC-RULES-1119 agent ? last post 2026-11-27 15:17 HOURLY
- HEAD-TILE-R3 agent ? last post 2026-11-27 15:17 DIED
- S81-INT-R3 agent ? last post 2026-11-27 15:11 DIED
- AUTO-CLEAN agent ? last post 2026-11-27 15:09 INFO
- HEAD-EAST-R4 agent ? last post 2026-11-27 15:05 CLASS-REQUEST
- KV-INT-R3 agent ? last post 2026-11-27 15:04 NOTE
- S81-INT-R3-VIEWS agent ? last post 2026-11-27 15:00 RESULT
- LEC-R3 agent ? last post 2026-11-27 14:56 RESULT
- KV-INT-R3/PV-RESET agent ? last post 2026-11-27 14:56 RESULT
- CLASS-TRACK-R3 agent ? last post 2026-11-27 14:54 RESULT
- PLAN-GATE-PRE-1115 agent ? last post 2026-11-27 14:54 NEEDS-ACTION
- MERGE-QUEUE agent ? last post 2026-11-27 14:47 KNOWN-RED
- SMELL-WATCH agent ? last post 2026-11-27 14:45 RENDER
- CLASS-OWNERS-R3 agent ? last post 2026-11-27 14:42 DIED
- FAIL-ROUTE-1115 agent ? last post 2026-11-27 14:38 HANDOVER
- HEAD-PART-R3 agent ? last post 2026-11-27 14:10 DIED
- QC-R3-LEG405 agent ? last post 2026-11-27 14:08 DIED
- KV-INT-R3/COMPOSE agent ? last post 2026-11-27 13:49 RESULT
- KV-INT-R3/AHUB agent ? last post 2026-11-27 13:48 RESULT
- QC-R3-STA agent ? last post 2026-11-27 13:45 ROW-READY
- token-r2 agent ? last post 2026-11-27 13:19 DIED
- s81-int-r3-xr agent ? last post 2026-11-27 13:18 DIED
- S81-INT-R3-WAITER agent ? last post 2026-11-27 13:16 DIED
- S81-INT-R3-BITORDER agent ? last post 2026-11-27 13:12 RESULT
- KV-INT-R3/FIRM agent ? last post 2026-11-27 13:12 RESULT
- KV-INT-R3/GPLTD agent ? last post 2026-11-27 13:10 RESULT
- S81-INT-R3-SEAM agent ? last post 2026-11-27 13:07 RESULT
- qwen_compute agent ? last post 2026-11-27 12:53 KIT-WAVE
- QC-R3-TAPS agent ? last post 2026-11-27 12:51 DIED
- QC-R3-SULANE agent ? last post 2026-11-27 12:51 DIED
- P-GEOM-INHERITED-MASK agent ? last post 2026-11-27 12:51 MEASURED
- KV-INT-R3/HUB agent ? last post 2026-11-27 12:49 RESULT
- S81-INT-R3-T31 agent ? last post 2026-11-27 12:38 C-T31-CS-GLOB
- QC-R3-TT agent ? last post 2026-11-27 12:37 DIED

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-27 15:30 PST)
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
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 1 current-event (+7 on a superseded plan block, not counted) (live check: ps/systemd/docker on all hosts; wave state: hub; full list lanes/STALE.tsv)
- [ ] STALE.QC 7 (cores 0, types 7) · by owner: KIT-WAVE-1 3, QC-PLAN 2, unowned 1, QC-STALE-GEOM 1
  - type sle_ctl__cla4f6f12f · CANCELLED geom QUEUE-CANCELLED @ 2026-11-23 11:21 (100.2h) · owner QC-PLAN
  - type sle_fw_v2__cl69f5e854 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-23 17:19 (94.2h) · owner QC-PLAN
  - type slw_fw_v1__clf51c11d8__cl592e3d37 · CANCELLED geom GHOST @ 2026-11-24 11:42 (75.8h) · owner unowned
  - type slw_fw_v3 · CANCELLED geom SUPERSEDED @ 2026-11-24 11:50 (75.7h) · owner KIT-WAVE-1
  - type slw_fe_v1__clfe325744__cl08d14f0d · CANCELLED geom SUPERSEDED @ 2026-11-24 20:33 (67h) · owner QC-STALE-GEOM
  - type native59 · CANCELLED geom SUPERSEDED @ 2026-11-25 19:34 (43.9h) · owner KIT-WAVE-1
  - type coll_ucie · CANCELLED geom QUEUE-CANCELLED @ 2026-11-26 09:19 (30.2h) · owner KIT-WAVE-1
- [ ] STALE.KV 1 (cores 0, types 1) · by owner: FAM-KV-HUBC-SYSC-R2 1
  - type kv3_sys_c · CANCELLED geom SUPERSEDED @ 2026-11-23 20:57 (90.6h) · owner FAM-KV-HUBC-SYSC-R2
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 348 commits / missing none
- TOOLS-LAG qwen_kvsys 385 commits / missing none
- TOOLS-LAG s81_head 1 commits / missing none
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 5049 taps in 48 types, 136 over 1650 sinks; insertion max 696 ps (p50 269, p90 284), skew max 176 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 596 taps in 6 types, 17 over 1650 sinks; insertion max 516 ps (p50 258, p90 289), skew max 208 ps; oversized taps: ins max 412 ps, skew max 100 ps
- TAP-INSERTION s81: 3591 taps in 55 types, 130 over 1650 sinks; insertion max 1000 ps (p50 466, p90 498), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 575 taps in 14 types, 9 over 1650 sinks; insertion max 613 ps (p50 458, p90 468), skew max 171 ps; oversized taps: ins max 466 ps, skew max 62 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-27 15:05 | tolera L12.69/112 units0 free833G | key-ca L17.21/112 units6 free287G | dear-c L2.88/128 units0 free351G | loved- L9.91/96 units2 free263G | outgoi L16.54/96 units5 free372G | renewe L1.32/96 units0 free1364G | civil- L4.61/96 units1 free1202G | viable L7.03/96 units3 free1629G | HOST-CAPS ok (9 owned caps); expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (192.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (192.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (192.9 h left); epyc7:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (192.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (192.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (192.9 h left); e
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  336G  109G  76% /
    15:30:18 up 34 days, 11:10, 150 users,  load average: 9.51, 10.13, 12.06

## ot-run status
    ot-run status: epyc2 admits 946 GB (avail 986, reserve 0, fresh 0, peak 0) load 3/128 run 0 threads 8/128 root 91% scratch 346 GB
    intel1 admits 786 GB (avail 962, reserve 0, fresh 0, peak 60.1) load 17/112 run 5 threads 112/112 root 21% scratch 278 GB
    localhost admits 825 GB (avail 953, reserve 0, fresh 0, peak 0) load 10/112 run 0 threads 14/112 root 76% scratch 823 GB
    epyc7 admits 888 GB (avail 941, reserve 0, fresh 0, peak 0) load 5/96 run 2 threads 124/96 root 35% scratch 330 GB
    epyc8 admits 873 GB (avail 922, reserve 0, fresh 0, peak 154.9) load 11/96 run 4 threads 342/96 root 51% scratch 293 GB
    epyc9 admits 939 GB (avail 987, reserve 0, fresh 0, peak 0) load 1/96 run 0 threads 47/96 root 40% scratch 1359 GB
    epyc10 admits 931 GB (avail 979, reserve 0, fresh 0, peak 0) load 2/96 run 1 threads 142/96 root 54% scratch 1201 GB
    epyc11 admits 899 GB (avail 958, reserve 0, fresh 0, peak 0) load 23/96 run 15 threads 248/96 root 7% scratch 1612 GB
    epyc12 admits 875 GB (avail 923, reserve 0, fresh 0, peak 869.2) load 71/96 run 15 threads 560/96 root 37% scratch 845 GB
    next 16-thread 32 GB job -> epyc2

## KIT-WAVE (autopilot log, last 6)
    2026-11-27 15:28:46 PST AUTOPILOT: KIT-WAVE LAUNCH-REFUSED qwen_compute/slw_hc2__cla3497502__cldc737267: LBL-FAIL: lanes/VIS-COVERAGE.tsv row slw_hc2 (variant sibling) is FAIL: no relaunch / first att
    2026-11-27 15:28:46 PST AUTOPILOT: KIT-WAVE LBL-PASS qwen_compute/coll_ft__cl78c7b300: LBL-NOROW no lanes/VIS-COVERAGE.tsv row for coll_ft__cl78c7b300: not held [+4 identical line(s) in the last hour]
    2026-11-27 15:29:07 PST AUTOPILOT: KIT-WAVE WAIT-PLAN-VISUAL: BAD fresh plan image verdict for qwen_compute/coll_ft__cl78c7b300 form 9f92ee087cce9ae628b169cefa2b017b0cc2a7ceb3b2b5cc7d66bf4bfbb10de9; r
    2026-11-27 15:29:30 PST AUTOPILOT: KIT-WAVE LBL-PASS qwen_compute/slw_st_b_v2__pvc2ec5bfb: LBL-NOROW no lanes/VIS-COVERAGE.tsv row for slw_st_b_v2__pvc2ec5bfb: not held [+4 identical line(s) in the la
    2026-11-27 15:29:46 PST AUTOPILOT: KIT-WAVE WAIT-PLAN-VISUAL: BAD fresh plan image verdict for qwen_compute/slw_st_b_v2__pvc2ec5bfb form 821f10a969b1a5d33dab99482b9cbd67c33aa40bffa6fbaa39de5e61cb6aaaf
    2026-11-27 15:29:46 PST AUTOPILOT: KIT-WAVE LBL-PASS qwen_compute/sle_stm_v2__cl55be2264: LBL-NOROW no lanes/VIS-COVERAGE.tsv row for sle_stm_v2__cl55be2264: not held [+4 identical line(s) in the last

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-27 15:18 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-PLAN-VISUAL s81_head/hd_turn_b: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form fa61effff19647ecc25f0b94eb0c2b27eb73db710cec12c9c5acdea20ad45300 (request /srv/opentallas-scratch2/claude/HEAD-INT-R3/relay_probe/spec_hd_turn_b/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-PLAN-
- 2026-11-27 15:18 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-VISUAL qwen_compute/sle_st_b_v1__pvc5a85fd4__pv7b7fafb4: missing lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT verdict line for qwen_compute/sle_st_b_v1__pvc5a85fd4__pv7b7fafb4; reviewer lane QC-INT-R3 (fallback INT-R3); reason: WAIT-VISUAL: view the placement and record a GEOM VERDICT with kit=intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/
- 2026-11-27 15:18 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-VISUAL qwen_compute/sle_stm_v2__cl7b3062fa: missing lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT verdict line for qwen_compute/sle_stm_v2__cl7b3062fa; reviewer lane QC-INT-R3 (fallback INT-R3); reason: WAIT-VISUAL: view the placement and record a GEOM VERDICT with kit=epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_
- 2026-11-27 15:18 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-VISUAL qwen_compute/slw_fw_v2__cl8537f156: missing lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT verdict line for qwen_compute/slw_fw_v2__cl8537f156; reviewer lane QC-INT-R3 (fallback INT-R3); reason: WAIT-VISUAL: view the placement and record a GEOM VERDICT with kit=intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_c
- 2026-11-27 15:19 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-PLAN-VISUAL s81_head/hd_mesh: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form fa61effff19647ecc25f0b94eb0c2b27eb73db710cec12c9c5acdea20ad45300 (request /srv/opentallas-scratch2/claude/HEAD-INT-R3/relay_probe/spec_hd_mesh/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-PLAN-VISU
- 2026-11-27 15:19 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-VISUAL qwen_compute/slw_fw_v2__cl8f84514c: missing lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT verdict line for qwen_compute/slw_fw_v2__cl8f84514c; reviewer lane QC-INT-R3 (fallback INT-R3); reason: WAIT-VISUAL: view the placement and record a GEOM VERDICT with kit=intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_c
- 2026-11-27 15:19 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-VISUAL qwen_compute/slw_hc3__clccfc3e6b__pv39aac7a1: missing lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT verdict line for qwen_compute/slw_hc3__clccfc3e6b__pv39aac7a1; reviewer lane QC-INT-R3 (fallback INT-R3); reason: WAIT-VISUAL: view the placement and record a GEOM VERDICT with kit=epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_comp
- 2026-11-27 15:19 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-VISUAL qwen_compute/slw_sc_v1__cl64543eaf__cl5e017c6f: missing lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT verdict line for qwen_compute/slw_sc_v1__cl64543eaf__cl5e017c6f; reviewer lane QC-INT-R3 (fallback INT-R3); reason: WAIT-VISUAL: view the placement and record a GEOM VERDICT with kit=intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen
- 2026-11-27 15:19 PST DIED [kv-int-r3] ot-push-main otpush-outgoing-giraffe-1272498 on outgoing-giraffe: rc=3 after 5 s, ended 23:19:26, log /srv/opentallas-scratch2/claude/kv-int-r3/pvreset/lane/push.log, cmd: ot-push-main  | class=PUSH-CONFLICT cause=ot-push-main: rc 3: REBASE CONFLICT on main 0e0590e94f1 in:
- 2026-11-27 15:19 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-PLAN-VISUAL s81_head/hd_st_n4: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form bcfc180a7af985145d0c23de0f75f59f143d109c8bc3c3e59b50f20c9df46fa6 (request /srv/opentallas-scratch2/claude/HEAD-INT-R3/relay_probe/spec_hd_st_n4/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-PLAN-VI
- 2026-11-27 15:19 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-VISUAL qwen_compute/slw_st_b_v1__cl6357f1cc__pv6ace3e48: missing lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT verdict line for qwen_compute/slw_st_b_v1__cl6357f1cc__pv6ace3e48; reviewer lane QC-INT-R3 (fallback INT-R3); reason: WAIT-VISUAL: view the placement and record a GEOM VERDICT with kit=epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/q
- 2026-11-27 15:19 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-FORM s81_head/hd_ctl_e: missing a changed form fingerprint for s81_head/hd_ctl_e, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel2:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/items
- 2026-11-27 15:20 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-FORM s81_head/hd_ctl_n: missing a changed form fingerprint for s81_head/hd_ctl_n, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/items
- 2026-11-27 15:20 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-FORM s81_head/hd_host_n: missing a changed form fingerprint for s81_head/hd_host_n, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel2:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/ite
- 2026-11-27 15:20 PST DONE [HEAD-CASEAM-R4] C-TAP-REACH tool tap_cohort_assign pushed to main c493a87422f4 (ot-push-main; 5 independent Fable review rounds, rounds 1-4 FAILED earlier versions and every finding was fixed, round 5 PASS; 11 tests incl. main() exit-code/refusal tests and 17 mutants; default off, standalone, no flow calls it). Model results on W12f placed sinks (rows_2100/TAP-REACH/README.md, tapreach/tc
- 2026-11-27 15:20 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-FORM s81_head/hd_spn_eshim_rx: missing a changed form fingerprint for s81_head/hd_spn_eshim_rx, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18
- 2026-11-27 15:20 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-FORM s81_head/hd_spn_eshim_tx: missing a changed form fingerprint for s81_head/hd_spn_eshim_tx, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18
- 2026-11-27 15:20 PST DIED [QC-R3-DIEGAP] ot-run oth-ubuntu-1054624-1795819590 on key-cardinal: rc=1 after 2055 s, ended 15:20:41, log /srv/opentallas-scratch2/claude/QC-R3-DIEGAP/gate_g4.out, cmd: --priority die --hosts intel1 --mem 168 --disk 25 --dir /srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_compute_qc_join_2100_77f | class=STATE-NOT-DEATH cause=ROW-GATE NOT-READY lane=QC-R3-DIEGAP die=qwen_comp
- 2026-11-27 15:20 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-FORM s81_head/hd_spn_wshim_tx: missing a changed form fingerprint for s81_head/hd_spn_wshim_tx, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel2:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18
- 2026-11-27 15:20 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-FORM s81_head/hd_st_k5: missing a changed form fingerprint for s81_head/hd_st_k5, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/items/
- 2026-11-27 15:21 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-FORM s81_head/hd_st_m: missing a changed form fingerprint for s81_head/hd_st_m, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel2:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/items/h
- 2026-11-27 15:21 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-FORM s81_head/hd_st_n3_transit: missing a changed form fingerprint for s81_head/hd_st_n3_transit, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r
- 2026-11-27 15:21 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-FORM s81_head/hd_st_n3_turn: missing a changed form fingerprint for s81_head/hd_st_n3_turn, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1
- 2026-11-27 15:21 PST DIED [kv-int-r3] ot-push-main otpush-outgoing-giraffe-1346339 on outgoing-giraffe: rc=4 after 8 s, ended 23:21:38, log /srv/opentallas-scratch2/claude/kv-int-r3/pvreset/lane/push.log, cmd: ot-push-main  | class=TEST-FAIL cause=ot-push-main: rc 4: TESTS FAILED rc=1; nothing pushed
- 2026-11-27 15:21 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-FORM s81_head/hd_st_str: missing a changed form fingerprint for s81_head/hd_st_str, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/item
- 2026-11-27 15:21 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-FORM s81_head/hd_st_turn: missing a changed form fingerprint for s81_head/hd_st_turn, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/it
- 2026-11-27 15:22 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-FORM s81_head/hd_turn_a: missing a changed form fingerprint for s81_head/hd_turn_a, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/ite
- 2026-11-27 15:22 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-27 15:22 PST: 17 running jobs, PROGRESSING 16, PLATEAU 0, SLOW 0, NO-PROGRESS 1 (this table is advisory; the separate noprog.timer watchdog (noprog_watchdog.py) DOES ot-heavy-stop NO-PROGRESS jobs, per-host log ~/.local/state/noprog/actions.jsonl); table lanes/NOPROG.tsv
- 2026-11-27 15:22 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-FORM s81_head/hd_turn_b: missing a changed form fingerprint for s81_head/hd_turn_b, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel2:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/ite
- 2026-11-27 15:22 PST DIED [FLEET-OPS-R5] ot-push-main otpush-tolerant-swine-1412031 on tolerant-swine: rc=4 after 696 s, ended 15:22:46, log /tmp/r5kw4.out, cmd: ot-push-main  | class=TEST-FAIL cause=ot-push-main: rc 4: TESTS FAILED rc=1; nothing pushed
- 2026-11-27 15:23 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_hc3__cld86a7ad4__pvfd488b8f: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 2d5e95a50498a8f8256f553d92c1556d3851d9c1bc32047d2329bb3c70107db0 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_hc3__cld86a7ad4__pvfd488b8f_b1b55749a3d22/a1/plan_visual_request.json) (a GOOD verdict on the exact plan for
- 2026-11-27 15:23 PST DIED [QC-R3-DIEGAP] ot-run otrun-key-cardinal-2659016 on key-cardinal: rc=78 after 3 s, ended 15:23:50, log /srv/opentallas-scratch2/claude/QC-R3-DIEGAP/pre_g4.out, cmd: --hosts intel1 --mem 64 --threads 16 --disk 10 --dir /srv/opentallas-scratch2/claude/QC-R3-DIEGAP/gate_g4/launch -- env OT_SEAL_GATE=report  | class=NOT-RUN cause=NOT-RUN SETUP: NOT-RUN SETUP missing input /srv/opentallas-scrat
- 2026-11-27 15:24 PST WAIT-STATE [KIT-WAVE -> KV-INT-R3] WAIT-PLAN-VISUAL qwen_kvsys/kv3_hub_Wi: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 538657e322f857559ece90254d3abe79ce95b2a6a08a941b07d8e1e14b2edc1f (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_kvsys_kv3_hub_Wi_b4dab1acb06a2/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane KV-INT-R3 (fallback INT-R3);
- 2026-11-27 15:24 PST RESULT [HEAD-PROBE-R3] serdes4stock5 PASS, SERDES-PB ROW-READY (conditional, NEXT form; COORD keeps serdes DEFERRED for 21:00). Stock chain on committed tools (main 180574c46c04 guard, pinned rt b71c5218e0b5, phase-bind env), W12f+serdes4 digest 25448e0100ac: all 10 stages PASS: PRE PASS, bind, cohort, LATCHECK 334/334, native_release via the guard (CHANGED_BINDING_COVERED 4 paths, WF_PLAN_RELE
- 2026-11-27 15:24 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_su_l0__cl76fb247e: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form e36bc4ced77e32c750f8c71beaae13fecebac14c32aa425a3e728a985510d3be (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_su_l0__cl76fb247e_b56c46f392aad/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane QC
- 2026-11-27 15:24 PST DIED [kv-int-r3] ot-run otrun-outgoing-giraffe-1463601 on outgoing-giraffe: rc=78 after 3 s, ended 23:24:40, log /srv/opentallas-scratch2/claude/kv-int-r3/firm/gate4.otrun.log, cmd: --priority die --mem 96 --threads 8 --hosts epyc12,epyc11 --dir /srv/opentallas-scratch2/claude/kv-int-r3/firm -- bash gate4.sh | class=NOT-RUN cause=NOT-RUN SETUP: script /srv/opentallas-scratch2/claude/kv-int-r3/f
- 2026-11-27 15:24 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/sle_fe_v2: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 821f10a969b1a5d33dab99482b9cbd67c33aa40bffa6fbaa39de5e61cb6aaafd (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_sle_fe_v2_bb97aa62b624c/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane QC-INT-R3 (fallback INT-R3
- 2026-11-27 15:25 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/sle_fw_v2__cl6740750e: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form d49f45465119c4ebc8f4bceaa58b0f709d180a19d443254a8b1d477e76e6367c (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_sle_fw_v2__cl6740750e_b0c5e6100fe86/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane QC
- 2026-11-27 15:25 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/coll_ftc: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 821f10a969b1a5d33dab99482b9cbd67c33aa40bffa6fbaa39de5e61cb6aaafd (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_coll_ftc_ba26f1871f3f0/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane QC-INT-R3 (fallback INT-R3);
- 2026-11-27 15:25 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_stm_v3: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form ef269736cc0e42e03b54d1a7d55370271a7631abe55707f31013a82033403054 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_stm_v3_bf9d1bef2d4d4/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane QC-INT-R3 (fallback INT-
- 2026-11-27 15:25 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_hc3__cld86a7ad4__pv6c2c33ed: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 2d5e95a50498a8f8256f553d92c1556d3851d9c1bc32047d2329bb3c70107db0 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_hc3__cld86a7ad4__pv6c2c33ed_b3be2ed32bfd6/a1/plan_visual_request.json) (a GOOD verdict on the exact plan for
- 2026-11-27 15:26 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/sle_su_l0__cl086d85ba: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 84593337d8c3241f4ea0acccf2400689aed667d5d3e717c341f0f40b335f40ae (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_sle_su_l0__cl086d85ba_bd7efeb841747/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane QC
- 2026-11-27 15:26 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_su_l0__cl1e5219ea: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 8a1d76b8ad14ef5149870c7a441a4f0174e222d5f42774294d2dd00cbb19a9df (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_su_l0__cl1e5219ea_bca4e690ba4cf/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane QC
- 2026-11-27 15:26 PST DIED [HEAD-INT-R3] ot-run oth-ubuntu-1985375-1795822002 on open-snipe: rc=3 after 5 s, ended 23:26:43, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/rows_2100/SIBLINGS-1247/hd_st_n3_transit/work/ot-run2.log, cmd: --priority die --hosts epyc12 --mem 80 --threads 48 --disk 30 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/rows_2100/SIBLINGS-1247/hd_s | class=NO-PATTERN cause=REFUSE_EXISTS
- 2026-11-27 15:26 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/sle_fe_v1__cl1cbb7497: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 821f10a969b1a5d33dab99482b9cbd67c33aa40bffa6fbaa39de5e61cb6aaafd (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_sle_fe_v1__cl1cbb7497_ba941daa1c1dc/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane QC
- 2026-11-27 15:27 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/sle_fe_v1__cl8210183c: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 821f10a969b1a5d33dab99482b9cbd67c33aa40bffa6fbaa39de5e61cb6aaafd (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_sle_fe_v1__cl8210183c_b8c70bd6e251b/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane QC
- 2026-11-27 15:27 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_sc_v1__cl63e5a7a2: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 821f10a969b1a5d33dab99482b9cbd67c33aa40bffa6fbaa39de5e61cb6aaafd (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_sc_v1__cl63e5a7a2_b0bec21de3f4d/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane QC
- 2026-11-27 15:27 PST DONE [HEAD-CASEAM-R4] tap_cohort_assign follow-up pushed to main 92a1ff96b37e (Fable PASS after 1 FAIL round): --split-oversize default OFF with per-cohort cut-pair report (PROXY adjacent pairs on different taps; real related pairs UNMEASURED) and the plan-side alternative recorded; numeric tap tie order fixes the equidistant-renumber assert. Why explicit types did not converge: hd_ctl_n / hd_s
- 2026-11-27 15:27 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_sc_v1__cl64543eaf__cl4590432d: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form ec04e1fa02957f80a3730f4ce7ec1f69ceaf2b2cb6d94c099ad05c83e1e04950 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_sc_v1__cl64543eaf__cl4590432d_bc7eb7bfcef28/a1/plan_visual_request.json) (a GOOD verdict on the exact plan
- 2026-11-27 15:28 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_sc_v2: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 77ae5ab78a0ab98c8cc48afc11c944631484b598f3fd5e43b4dd96c1a7ede5e9 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_sc_v2_bddbefcca98b3/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane QC-INT-R3 (fallback INT-R3
- 2026-11-27 15:28 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/sle_hc1__cl7d360508__pv97423966: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 2d5e95a50498a8f8256f553d92c1556d3851d9c1bc32047d2329bb3c70107db0 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_sle_hc1__cl7d360508__pv97423966_b555da616ac70/a1/plan_visual_request.json) (a GOOD verdict on the exact plan for
- 2026-11-27 15:28 PST ALERT [FLEET-OPS-R -> COORD] lane quota: HEAD-INT-R3 on intel1 wrote 172 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-27 15:28 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/sle_su_l0__cl7a55c676: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form e36bc4ced77e32c750f8c71beaae13fecebac14c32aa425a3e728a985510d3be (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_sle_su_l0__cl7a55c676_bf16039c8a4d4/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane QC
- 2026-11-27 15:28 PST ALERT [FLEET-OPS-R -> COORD] lane quota: kv-allfix on intel1 wrote 52 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-27 15:28 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/coll_ft__cl78c7b300: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 9f92ee087cce9ae628b169cefa2b017b0cc2a7ceb3b2b5cc7d66bf4bfbb10de9 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_coll_ft__cl78c7b300_b70249fddf5bb/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane QC-INT
- 2026-11-27 15:28 PST ALERT [FLEET-OPS-R -> COORD] lane quota: kv-int-r2 on intel1 wrote 53 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-27 15:29 PST ALERT [FLEET-OPS-R -> COORD] lane quota: s81-allfix-int on intel1 wrote 76 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-27 15:29 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/sle_st_b_v2__cl14c98df5__pvcd986c42: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 1df1f5065095c1e939d2171d39f71044bad2c29eb0764a574e202385f5cb84b8 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_sle_st_b_v2__cl14c98df5__pvcd986c42_bae78acc948ea/a1/plan_visual_request.json) (a GOOD verdict on the exact 
- 2026-11-27 15:29 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_st_b_v2__pvc2ec5bfb: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 821f10a969b1a5d33dab99482b9cbd67c33aa40bffa6fbaa39de5e61cb6aaafd (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_st_b_v2__pvc2ec5bfb_bcf29eb67ffc0/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lan
- 2026-11-27 15:29 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/sle_stm_v2__cl55be2264: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 2854e2f72b378cccba366f3043aa4c2ddee3d883783178154856c4dab0b068cd (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_sle_stm_v2__cl55be2264_bb545549c2c88/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane 

