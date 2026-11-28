# COORD snapshot 2026-11-27 16:15 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: ae795468725e
- 2026-11-27 09:50 PST MERGED [MERGE-QUEUE -> CLASS-OWNERS-R2] native-sram-path-authority@09079a689ee: nothing to land, 09079a689ee is an ancestor of main 81f48be7e98.
- 2026-11-27 09:50 PST MERGED [MERGE-QUEUE -> CLASS-OWNERS-R2] relay-seat-stop-runtime@08917427de8: nothing to land, 08917427de8 is an ancestor of main 81f48be7e98.
- 2026-11-27 10:35 PST MERGED [MERGE-QUEUE -> LEC-R2] lec-uneven-memory@5a7729a9c34: nothing to land, 5a7729a9c34 is an ancestor of main 3d76ea4f296.

## READY/ASK with no later COORD post naming them (1, heuristic: check each)
- 2026-11-27 09:47 PST ASK [QC-INT-R3 -> KV-INT-R3; cc COORD, CLASS-OWNERS-R3; class C-XDIE-ABI-MISMATCH] QC live is now 77f2cc98f662 (event qc_2100_combined_77f2_1126, applied 09:00:39), not C9; post-bind GREEN, bind_out qwen_compute_qc_join_2100_77f2_1126_bind_1127093611. Codex 22:00 found that the D/E stock C9 STATUS wrapper fails by default, with one OBS1_COMPAT source only. So QC plans NO producer change, and KV

## Lane handoff files (age) and last queue post
- CLAUDE-RESUME-1127: handoff 432 min old; last post none in recent queue
- EXPLORER-STORE-R1: handoff 927 min old; last post 2026-11-26 22:07 STATE
- HEAD-INT-R2-HOSTW-CAPACITY-1127: handoff 745 min old; last post none in recent queue
- LIMIT-OUTAGE: handoff 0 min old; last post none in recent queue
- PCC-B1-LANE-SPEC: handoff 295 min old; last post none in recent queue
- PREPARED-PUBLICATION-PLACE: handoff 1022 min old; last post none in recent queue
- PUBLISH-GATE: handoff 927 min old; last post 2026-11-26 23:27 READY
- QC-ALLFIX-COLL: handoff 753 min old; last post none in recent queue
- ROM-WEIGHTS-1119: handoff 927 min old; last post 2026-11-26 23:36 STATE

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 195; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 36 live
- HEAD-PROBE-R3 agent ? last post 2026-11-27 16:11 RESULT
- KIT-WAVE agent ? last post 2026-11-27 16:04 WAIT-STATE
- SMELL-WATCH agent ? last post 2026-11-27 15:45 RENDER
- PROGRESS-WATCH agent ? last post 2026-11-27 15:36 ALERT
- QC-R3-SULANE agent ? last post 2026-11-27 15:35 DIED
- mq1 agent ? last post 2026-11-27 15:32 DIED
- NOPROG-WATCHDOG agent ? last post 2026-11-27 15:30 STATE
- FLEET-OPS-R agent ? last post 2026-11-27 15:29 ALERT
- HEAD-CASEAM-R4 agent ? last post 2026-11-27 15:27 DONE
- HEAD-INT-R3 agent ? last post 2026-11-27 15:26 DIED
- kv-int-r3 agent ? last post 2026-11-27 15:24 DIED
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

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-27 16:15 PST)
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
  - type sle_ctl__cla4f6f12f · CANCELLED geom QUEUE-CANCELLED @ 2026-11-23 11:21 (100.9h) · owner QC-PLAN
  - type sle_fw_v2__cl69f5e854 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-23 17:19 (94.9h) · owner QC-PLAN
  - type slw_fw_v1__clf51c11d8__cl592e3d37 · CANCELLED geom GHOST @ 2026-11-24 11:42 (76.6h) · owner unowned
  - type slw_fw_v3 · CANCELLED geom SUPERSEDED @ 2026-11-24 11:50 (76.4h) · owner KIT-WAVE-1
  - type slw_fe_v1__clfe325744__cl08d14f0d · CANCELLED geom SUPERSEDED @ 2026-11-24 20:33 (67.7h) · owner QC-STALE-GEOM
  - type native59 · CANCELLED geom SUPERSEDED @ 2026-11-25 19:34 (44.7h) · owner KIT-WAVE-1
  - type coll_ucie · CANCELLED geom QUEUE-CANCELLED @ 2026-11-26 09:19 (30.9h) · owner KIT-WAVE-1
- [ ] STALE.KV 1 (cores 0, types 1) · by owner: FAM-KV-HUBC-SYSC-R2 1
  - type kv3_sys_c · CANCELLED geom SUPERSEDED @ 2026-11-23 20:57 (91.3h) · owner FAM-KV-HUBC-SYSC-R2
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 357 commits / missing none
- TOOLS-LAG qwen_kvsys 394 commits / missing none
- TOOLS-LAG s81_head 0 commits / missing none
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 5049 taps in 48 types, 136 over 1650 sinks; insertion max 696 ps (p50 269, p90 284), skew max 176 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 596 taps in 6 types, 17 over 1650 sinks; insertion max 516 ps (p50 258, p90 289), skew max 208 ps; oversized taps: ins max 412 ps, skew max 100 ps
- TAP-INSERTION s81: 3591 taps in 55 types, 130 over 1650 sinks; insertion max 1000 ps (p50 466, p90 498), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 575 taps in 14 types, 9 over 1650 sinks; insertion max 613 ps (p50 458, p90 468), skew max 171 ps; oversized taps: ins max 466 ps, skew max 62 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-27 16:05 | tolera L7.51/112 units0 free825G | key-ca L79.52/112 units6 free274G | dear-c L2.56/128 units0 free347G | loved- L10.04/96 units4 free326G | outgoi L19.08/96 units5 free248G | renewe L2.17/96 units0 free1361G | civil- L3.19/96 units0 free1204G | viable L6.39/96 units2 free1606G | HOST-CAPS ok (9 owned caps); expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (191.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (191.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (191.9 h left); epyc7:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (191.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (191.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (191.9 h left); e
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  336G  109G  76% /
    16:15:17 up 34 days, 11:55, 148 users,  load average: 7.53, 8.70, 9.18

## ot-run status
    ot-run status: epyc2 admits 946 GB (avail 987, reserve 0, fresh 0, peak 0) load 2/128 run 0 threads 8/128 root 91% scratch 346 GB
    intel1 admits 771 GB (avail 924, reserve 0, fresh 0, peak 359) load 18/112 run 5 threads 192/112 root 21% scratch 273 GB
    localhost admits 826 GB (avail 955, reserve 0, fresh 0, peak 0) load 8/112 run 0 threads 14/112 root 76% scratch 823 GB
    epyc7 admits 909 GB (avail 960, reserve 0, fresh 0, peak 0) load 7/96 run 3 threads 140/96 root 35% scratch 325 GB
    epyc8 admits 874 GB (avail 924, reserve 0, fresh 0, peak 175.1) load 25/96 run 4 threads 342/96 root 51% scratch 222 GB
    epyc9 admits 939 GB (avail 988, reserve 0, fresh 0, peak 0) load 1/96 run 0 threads 47/96 root 40% scratch 1360 GB
    epyc10 admits 937 GB (avail 985, reserve 0, fresh 0, peak 0) load 2/96 run 0 threads 138/96 root 54% scratch 1205 GB
    epyc11 admits 927 GB (avail 975, reserve 0, fresh 0, peak 0) load 5/96 run 3 threads 150/96 root 7% scratch 1611 GB
    epyc12 admits 902 GB (avail 951, reserve 0, fresh 0, peak 514) load 24/96 run 6 threads 402/96 root 37% scratch 801 GB
    next 16-thread 32 GB job -> epyc2

## KIT-WAVE (autopilot log, last 6)
    2026-11-27 16:15:08 PST AUTOPILOT: KIT-WAVE TOOLS-LAG qwen_kvsys 394 commits / missing none
    2026-11-27 16:15:08 PST AUTOPILOT: KIT-WAVE TOOLS-LAG s81_head 0 commits / missing none
    2026-11-27 16:15:08 PST AUTOPILOT: KIT-WAVE TOOLS-LAG qwen_compute 357 commits / missing none
    2026-11-27 16:15:08 PST AUTOPILOT: KIT-WAVE KPG-PILOT qwen_kvsys/kv3_hub_Wi: known-problem pilot (recorded) SMELL:CTS,SMELL:STA-WNS,SMELL:STA-WNS [+4 identical line(s) in the last hour]
    2026-11-27 16:15:08 PST AUTOPILOT: KIT-WAVE KPG-PILOT s81_head/hd_mesh: known-problem pilot (recorded) SMELL:CTS,SMELL:SILENT [+4 identical line(s) in the last hour]
    2026-11-27 16:15:08 PST AUTOPILOT: KIT-WAVE KPG-PILOT s81/slice_station__t17: known-problem pilot (recorded) VIS:S81-SETUP-AT-CTS [+4 identical line(s) in the last hour]

## Last 60 queue posts (cut to 420 chars; full text in the queue)
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
- 2026-11-27 15:30 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 1 flagged of 24 containers {'NO-PROGRESS': 1, 'NO-DATA': 6, 'YOUNG': 17}; full table lanes/NOPROG-TABLE.md; flagged: epyc8 slw_fe_v1 5_2_route [NO-PROGRESS: drt_violations best 7 vs 7 before window: < 2 % in 6 h] REPORT-ONLY: lane-own kit (Q
- 2026-11-27 15:31 PST STATUS [HEAD-PROBE-R3] the stopped relay run-item is hd_st_m and it is a NORMAL COMPLETION, not a failure: result.json stage cts verdict PASS (run-item exited, no OOM, no stage failure; epyc11 systemd unit gone). Kit private/HEAD-PROBE-R3/hd_st_m_1127231819 on epyc11. Findings: config.mk carries export OT_RESET_AFFINITY_MAX_DRIVER_UM = 165 and export OT_RESET_RELAY = 1 (the gen_knobs export pat
- 2026-11-27 15:32 PST DIED [mq1] ot-push-main otpush-tolerant-swine-1963211 on tolerant-swine: rc=2 after 0 s, ended 15:32:13, log none, cmd: ot-push-main  | class=SETUP cause=died after 0 s with no log: the command failed at start (rc 2)
- 2026-11-27 15:32 PST DIED [mq1] ot-push-main otpush-tolerant-swine-1963722 on tolerant-swine: rc=3 after 0 s, ended 15:32:14, log none, cmd: ot-push-main  | class=NO-PATTERN cause=rc 3 after 0 s, no log
- 2026-11-27 15:32 PST DIED [mq1] ot-push-main otpush-tolerant-swine-1963496 on tolerant-swine: rc=4 after 0 s, ended 15:32:14, log none, cmd: ot-push-main  | class=NO-PATTERN cause=rc 4 after 0 s, no log
- 2026-11-27 15:32 PST DIED [mq1] ot-push-main otpush-tolerant-swine-1964250 on tolerant-swine: rc=4 after 0 s, ended 15:32:15, log none, cmd: ot-push-main  | class=NO-PATTERN cause=rc 4 after 0 s, no log
- 2026-11-27 15:32 PST DIED [mq1] ot-push-main otpush-tolerant-swine-1969508 on tolerant-swine: rc=4 after 0 s, ended 15:32:23, log none, cmd: ot-push-main  | class=NO-PATTERN cause=rc 4 after 0 s, no log
- 2026-11-27 15:33 PST DIED [QC-R3-SULANE] ot-run oth-ubuntu-3442011-1795822347 on key-cardinal: rc=1 after 55 s, ended 15:33:19, log /srv/opentallas-scratch2/claude/QC-R3-SULANE/p9row/g12.otrun.log, cmd: --priority die --mem 256 --threads 48 --disk 40 --hosts intel1 --dir /srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_compute_qc_ | class=STATE-NOT-DEATH cause=ROW-GATE NOT-READY lane=QC-R3-SULANE die=qwe
- 2026-11-27 15:33 PST RECONCILE [HEAD-PROBE-R3] hd_st_m: the class metric and the relay hook measure DIFFERENT things; the relay cannot see the class legs. Class metric (HEAD-PART-R3 census.tcl / ot_reset_reach::census 405, run by me on MY probe odbs, epyc11 relay_probe/proof): cumulative placed path root flop u_rst_in/q or u_run_in/q -> INV/BUF relay chain -> endpoint D, Manhattan between instance centres, summed o
- 2026-11-27 15:35 PST DIED [QC-R3-SULANE] ot-run oth-ubuntu-3606046-1795822455 on key-cardinal: rc=1 after 56 s, ended 15:35:07, log /srv/opentallas-scratch2/claude/QC-R3-SULANE/p9row/g13.otrun.log, cmd: --priority die --mem 256 --threads 48 --disk 40 --hosts intel1 --dir /srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_compute_qc_ | class=STATE-NOT-DEATH cause=ROW-GATE NOT-READY lane=QC-R3-SULANE die=qwe
- 2026-11-27 15:36 PST ALERT [PROGRESS-WATCH -> COORD] TICK-DEAD: no autopilot TICK-TIMES line since 15:12:42 (24 min; no launch or classify meanwhile) running tick started 15:32:17, last mark 'after admit_new'. Look: systemctl --user status autopilot.service; autopilot/tick_stack.log
- 2026-11-27 15:36 PST TABLE [HEAD-PROBE-R3] C-RST-RELAY-REACH class table started: epyc12 rows_2100/RST-RELAY-REACH/CLASS_TABLE.md. 3 of 10 probes finished at CTS (hd_st_m, hd_spn_eshim_tx, hd_turn_b), class metric on 4_cts, setup slack on the worst path, worst pin slew on the path vs 320: hd_st_m 429.084 um, +483.5 ps, 228.1 ps; hd_spn_eshim_tx 478.980 um, +463.5 ps, 213.4 ps; hd_turn_b 581.472 um (root u_rrl_8/q -
- 2026-11-27 15:37 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/sle_hc1__cl22c1ff36__pve230954c: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 2d5e95a50498a8f8256f553d92c1556d3851d9c1bc32047d2329bb3c70107db0 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_sle_hc1__cl22c1ff36__pve230954c_bfe4f950fe8d0/a1/plan_visual_request.json) (a GOOD verdict on the exact plan for
- 2026-11-27 15:37 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/sle_hc1__cl22c1ff36__pve289215f: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 2d5e95a50498a8f8256f553d92c1556d3851d9c1bc32047d2329bb3c70107db0 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_sle_hc1__cl22c1ff36__pve289215f_b2fa25e8ae39a/a1/plan_visual_request.json) (a GOOD verdict on the exact plan for
- 2026-11-27 15:37 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/sle_hc1__cl7d360508__pv77c16c8a: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 2d5e95a50498a8f8256f553d92c1556d3851d9c1bc32047d2329bb3c70107db0 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_sle_hc1__cl7d360508__pv77c16c8a_be3bc1aae41e9/a1/plan_visual_request.json) (a GOOD verdict on the exact plan for
- 2026-11-27 15:38 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_su_l0__cl1a1c1f8f: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 8a1d76b8ad14ef5149870c7a441a4f0174e222d5f42774294d2dd00cbb19a9df (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_su_l0__cl1a1c1f8f_b0b66acf34119/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane QC
- 2026-11-27 15:38 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/sle_st_b_v2__cl14c98df5__pv41c959f3: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 821f10a969b1a5d33dab99482b9cbd67c33aa40bffa6fbaa39de5e61cb6aaafd (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_sle_st_b_v2__cl14c98df5__pv41c959f3_b1e719d698820/a1/plan_visual_request.json) (a GOOD verdict on the exact 
- 2026-11-27 15:38 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_st_b_v2__pva66d0f22__pv3d7bec84: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 821f10a969b1a5d33dab99482b9cbd67c33aa40bffa6fbaa39de5e61cb6aaafd (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_st_b_v2__pva66d0f22__pv3d7bec84_b7899d0fbb284/a1/plan_visual_request.json) (a GOOD verdict on the exact 
- 2026-11-27 15:38 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_st_b_v2__pva66d0f22__pvb80e2003: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 821f10a969b1a5d33dab99482b9cbd67c33aa40bffa6fbaa39de5e61cb6aaafd (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_st_b_v2__pva66d0f22__pvb80e2003_b99f15af471a5/a1/plan_visual_request.json) (a GOOD verdict on the exact 
- 2026-11-27 15:39 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_stm_v1__cle34a73c3: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form fa8820ad5c6c42b09b3fae57021a057805492c32c29129bb7802bd758e4fabe2 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_stm_v1__cle34a73c3_b7a7fcce20240/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane 
- 2026-11-27 15:39 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_stm_v2__cl1ca9c415: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form ef269736cc0e42e03b54d1a7d55370271a7631abe55707f31013a82033403054 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_stm_v2__cl1ca9c415_bccca328bf449/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane 
- 2026-11-27 15:39 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_stm_v2__cl9beb65e6: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form c5d87b644fcfc7424f86280618c7f8fc1d3a25efe745a70c6cde5b18336805ff (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_stm_v2__cl9beb65e6_b4b00ede7d9d0/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane 
- 2026-11-27 15:45 PST RENDER [SMELL-WATCH -> HEAD-INT-R3, HEAD-PROBE-R3; cc HEAD-INT-R3] 1 checkpoint render(s) started: nervous_keller PLACE-GP on epyc11: epyc11:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/private/HEAD-PROBE-R3/hd_st_n3_transit_1127231718/gen/hd_st_n3_transit/vis_review/place-gp-1127-1545PST (floorplan.png, density.png, SMELL.txt wit
- 2026-11-27 15:47 PST TABLE [HEAD-PROBE-R3] C-RST-RELAY-REACH class table now 7 of 10 (rows_2100/RST-RELAY-REACH/CLASS_TABLE.md): worst class path um / setup slack ps / worst path slew ps: hd_st_m 429.1/+483.5/228; hd_spn_eshim_tx 479.0/+463.5/213; hd_turn_b 581.5/+298.8/222; hd_st_n3_turn 621.5/+324.0/236 (5 hops); hd_st_n3_transit 511.4/+358.9/220; hd_st_str 498.9/+383.8/211; hd_ctl_n 428.7/+396.7/145. All single-
- 2026-11-27 15:48 PST RESULT [HEAD-PROBE-R3] hd_spn_wshim_rx START hops CTS skew (for HEAD-PART-R3's +1 reader START cycle row; CTS-only in place on PART's attempt dir intel1 .../private/HEAD-PART-R3/hd_spn_wshim_rx_1127151501, reused 3_place d34a2dec0b36, ot-run oth-ubuntu-200914-1795822981): origin u_cland_origin/s2 -> stage0 u_cland_reader_start_link_i_0/q: setup +626.7 ps, hold +43.3 ps; stage0 -> stage1 copies 
- 2026-11-27 15:49 PST TABLE [HEAD-PROBE-R3] C-RST-RELAY-REACH class table 9 of 10 (hd_mesh pending). New rows: hd_st_k5 537.3 um (6 hops) / +359.6 ps / 170.6 ps; hd_st_n4 606.2 um (5 hops) / +338.1 ps / 232.4 ps. All 9: slack >= +298.8 ps, slew <= 236 ps vs 320, CTS slew violations 0. RELAY inserted on 2 types so far: hd_ctl_n 3 relays, hd_st_k5 1 relay (leaf leg 176.0 -> 88.0 + 88.0 um, recovery +663.6 ps, removal 
- 2026-11-27 16:03 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_hc1__cl3449ea95: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 2e091e8b96c1cf14e6efab68a86484ffb1682b3a3bad5349c561f4309056fb3e (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_hc1__cl3449ea95_b38842f11711f/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane QC-INT
- 2026-11-27 16:03 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_hc1__cl68f9248e__cl144ee7b3: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form a0511907c91b981c550ae300068e038b27a7a25b44dccd902d4d3ff8a179f6d0 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_hc1__cl68f9248e__cl144ee7b3_b1db3fbb0d2df/a1/plan_visual_request.json) (a GOOD verdict on the exact plan for
- 2026-11-27 16:04 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_hc1__cl68f9248e__cle683a076: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 0e7dce7f66389b4b6c3e1085fa5a1b7851f5adc3bcd8b9ec121387bec54e3553 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_hc1__cl68f9248e__cle683a076_b37c4ec754732/a1/plan_visual_request.json) (a GOOD verdict on the exact plan for
- 2026-11-27 16:11 PST RESULT [HEAD-PROBE-R3] relay before/after (hd_ctl_n, 3 relays; baseline CTS-only run of the same type, rt d9b7ec5dc7f8, knobs unset; same placement legs, check_placement 0 both): recovery slack ps (before -> after) u_ft_w3u_s2 558.2 -> 549.8 (-8.4), u_ft_w3d_s4 637.6 -> 612.4 (-25.2), u_ft_lw_ft_s2 688.8 -> 615.6 (-73.2); removal slack 178.5 -> 184.4 (+5.9), 120.0 -> 136.8 (+16.8), 66.8 -> 123.

