# COORD snapshot 2026-11-26 01:30 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: 9036c35f5687
- 2026-11-26 00:55 PST MERGED [MERGE-QUEUE -> C-PUBLISH-POSTBIND-TOOLS] claude/c-publish-postbind-tools-1126@eeac05c3d7c -> main 1542fb3b89a -> 02d0dedbc9e, no-ff merge, tags flow-20261117-pw-*. Gate: gate record from civil-redfish 2026-11-26 08:50 UTC on main 7909fa09f05 (main since: no overlap): 6 test file(s) pass; tests: test_bindfail_cancel.py test_flow1400_bind.py test_kit_wave.py test_publish_apply.py test_pub
- 2026-11-26 01:07 PST MERGED [MERGE-QUEUE -> C-LEG405-AFFINE-ADVISORY] claude/c-leg405-affine-advisory-1126@82cd7372b73 -> main 02d0dedbc9e -> 9f32ae99728, no-ff merge, tags flow-20261117-px-*. Gate: gate record from civil-redfish 2026-11-26 09:06 UTC on main 02d0dedbc9e: 2 test file(s) pass; tests: test_adv_g0_hops.py test_die_hop_scan_exp0.py. Lane C-LEG405-AFFINE-ADVISORY.
- 2026-11-26 01:19 PST MERGED [MERGE-QUEUE -> C-STREET-SPLIT-EXACT-SITES] claude/c-street-split-exact-sites-1126@f18d61ed6b7 -> main 9f32ae99728 -> 9036c35f568, no-ff merge, tags flow-20261117-py-*. Gate: gate record from civil-redfish 2026-11-26 09:19 UTC on main 9f32ae99728: 6 test file(s) pass (+4 source dir(s) the tests name: physical/die_plan/hbm physical/die_plan/hbm_arch_cores physical/die_plan/qwen_kvsys/plan

## READY/ASK with no later COORD post naming them (0, heuristic: check each)

## Lane handoff files (age) and last queue post
- FABLE-FIX-KV-LOCKUP-INERT: handoff 943 min old; last post 2026-11-25 09:46 CLOSE
- FAM-S81-COL-H9R0: handoff 1113 min old; last post 2026-11-25 18:53 DIED
- HEAD-EAST-REPLAN: handoff 1417 min old; last post 2026-11-25 01:53 STAND-DOWN
- HEAD-WEST: handoff 412 min old; last post 2026-11-25 23:38 RESULT
- KV-OWN-HG-R3: handoff 434 min old; last post 2026-11-25 18:20 PIN-MAP
- KV-OWN-PV-R2: handoff 1057 min old; last post 2026-11-24 23:06 DIED
- KV-SENDER-SKEW: handoff 1427 min old; last post 2026-11-25 03:49 RESULT
- LEC-AUTOFILL: handoff 8 min old; last post 2026-11-26 00:46 RESULT
- PRECHECK-R3: handoff 1418 min old; last post 2026-11-25 23:03 READY
- QC-ALLFIX: handoff 23 min old; last post 2026-11-26 01:06 QC-STRUCT-0107
- QC-BANKRST-OFF1: handoff 1030 min old; last post 2026-11-25 08:43 DIED
- QC-C1O-COMPOSE: handoff 1277 min old; last post 2026-11-25 15:46 DIED
- QC-FEV1-CL08: handoff 997 min old; last post 2026-11-25 08:51 CORRECTION
- QC-FWV1-F51: handoff 1055 min old; last post 2026-11-25 07:48 DIED
- QC-HC0-GROW-c2spec: handoff 433 min old; last post none in recent queue
- QC-HC0-GROW-options: handoff 928 min old; last post none in recent queue
- QC-HC0-GROW: handoff 936 min old; last post 2026-11-26 01:20 DIED
- QC-OLDKIT-CANCEL: handoff 1063 min old; last post 2026-11-25 07:46 DONE
- QC-SLECTL-PILE: handoff 1137 min old; last post 2026-11-26 01:14 DIED
- QC-STA-BTLAT3: handoff 1329 min old; last post 2026-11-25 01:17 DIED
- QC-STA-HOP: handoff 935 min old; last post 2026-11-25 08:21 DIED
- QC-STA-PROBE: handoff 1396 min old; last post 2026-11-25 07:56 DIED
- QC-STACLK-RE: handoff 1080 min old; last post 2026-11-25 07:30 STAND-DOWN
- QC-STAV2-F436: handoff 1133 min old; last post 2026-11-25 09:59 BUG
- QC-STM-FAM: handoff 1004 min old; last post none in recent queue
- QC-SUC-FTSITE: handoff 1027 min old; last post 2026-11-25 10:59 DIED
- QC-SUL1-BAND: handoff 1382 min old; last post 2026-11-25 04:05 DIED
- QC-SUL1-PLACE: handoff 1183 min old; last post 2026-11-25 09:10 DIED
- QC-SUL1-SLW-GROW: handoff 933 min old; last post 2026-11-25 15:47 DIED
- QC-SUL1-SLW-REFLOOR: handoff 1052 min old; last post 2026-11-25 08:56 DIED
- QC-TTCTLM-S: handoff 1033 min old; last post none in recent queue
- RELEC-R2: handoff 1185 min old; last post 2026-11-25 07:02 STAND-DOWN
- ROM-WEIGHTS-1119: handoff 984 min old; last post 2026-11-25 23:04 DIED
- S81-KVLEAF-T2-ARCH: handoff 402 min old; last post 2026-11-25 22:43 PROBE
- VIS-REOWN: handoff 953 min old; last post 2026-11-25 21:08 CORRECTION

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 195; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 33 live
- CODEX-SYSC-ABORT agent ? last post 2026-11-26 01:29 RESULT
- QC-C1Q-CUT agent ? last post 2026-11-26 01:29 DIED
- QC-STA-REBASE agent ? last post 2026-11-26 01:27 DIED
- MERGE-QUEUE agent ? last post 2026-11-26 01:25 STATE
- FLEET-OPS-R agent ? last post 2026-11-26 01:25 ALERT
- NOPROG-FIX-1115 agent ? last post 2026-11-26 01:22 STATE
- QC-HC0-GROW agent ? last post 2026-11-26 01:20 DIED
- qwen_compute agent ? last post 2026-11-26 01:20 KIT-WAVE
- qwen_kvsys agent ? last post 2026-11-26 01:20 KIT-WAVE
- CBC-RULES-1119 agent ? last post 2026-11-26 01:17 HOURLY
- NOPROG-WATCHDOG agent ? last post 2026-11-26 01:15 NOTICE
- SMELL-WATCH agent ? last post 2026-11-26 01:15 SMELL
- QC-SLECTL-PILE agent ? last post 2026-11-26 01:14 DIED
- FP-CONVERGE-S81 agent ? last post 2026-11-26 01:13 RESULT
- QC-DRT-ECO agent ? last post 2026-11-26 01:12 RESULT
- QC-ALLFIX agent ? last post 2026-11-26 01:06 QC-STRUCT-0107
- QC-STB-SPLIT agent ? last post 2026-11-26 00:56 DIED
- LEC-AUTOFILL agent ? last post 2026-11-26 00:46 RESULT
- REF-SITE agent ? last post 2026-11-26 00:38 READY
- CODEX agent ? last post 2026-11-26 00:36 RESULT
- S81-ALLFIX-INT agent ? last post 2026-11-26 00:36 DIED
- KV-ALLFIX agent ? last post 2026-11-26 00:34 POST-APPLY-BIND
- TOKEN agent ? last post 2026-11-26 00:34 RESULT
- ABSTRACT-EXACT agent ? last post 2026-11-26 00:34 RESULT
- FLEET-OPS-R2 agent ? last post 2026-11-26 00:26 READY
- ADOPT-ROWS agent ? last post 2026-11-26 00:26 NEEDS-LANE
- QC-SC agent ? last post 2026-11-26 00:18 DIED
- s81_head agent ? last post 2026-11-26 00:18 KIT-WAVE
- PRECHECK-1119 agent ? last post 2026-11-26 00:09 PLACE-PRECHECK
- KIT-WAVE agent ? last post 2026-11-26 00:08 STATE
- QC-SCV2-ROW agent ? last post 2026-11-26 00:06 DIED
- PLAN-CONFIG-DRIFT agent ? last post 2026-11-26 00:06 ALERT
- QC-FEFW-FAM agent ? last post 2026-11-26 00:01 DIED

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-26 01:30 PST)
count_hourly: signed any plan 608 | current plan 486 | deferred re-sign 21 (hbm 1, head 10, qc 7, s81 3) | retired-plan 101 (head 2, kv 13, qc 57, s81 29)
- [ ] FAIL.S81.CORES 72/72 signed · open: none
- [ ] FAIL.S81.TYPES 48/402 signed · kit rows: cancelled (superseded) 194 (bk_sel__t2, +193) · held by die owner (plan event pending) 153 (col_h10_r0_p1__t1__cl574cc59d__pvd7af8531, +152)
- [ ] FAIL.HEAD.CORES 5/5 signed · open: none
- [ ] FAIL.HEAD.TYPES 25/27 signed · kit rows: running (lint advisory) 2 (hd_lep0N, +1)
- [ ] FAIL.QC.CORES 69/69 signed · open: none
- [ ] FAIL.QC.TYPES 79/127 signed · kit rows: held by die owner (plan event pending) 37 (cbf_q00__cl1b5a6458, +36) · running 1 · running (lint advisory) 1 (sle_st_b_v2__clfde1249e)
- [ ] FAIL.KV.CORES 84/84 signed · open: none
- [ ] FAIL.KV.TYPES 10/93 signed · kit rows: held by die owner (plan event pending) 42 (kv3_hg, +41) · running (lint advisory) 37 (kv3_hgi_v1__cl141fc26e, +36) · cancelled (superseded) 2 (kv3_pv_v8e, +1) · placed, route held 1 (kv3_hub_Wi)
- [ ] FAIL.HBM.CORES 90/119 signed · open: no kit-wave row 19 (accel_smh_pt_w, hfd_coll_q3_body_ctl, hgi_sfu_opsa_group0, +12) · running, no result 9 (hfd_coll_q2n2_vm_core, hfd_hgi_vms_glue_nw_t, hgi_coll_tkm_m_tp192__root, +6) · shape: over cells/util/congestion 1 (hgi_dma_back_static_vp4_banks_cp
- [ ] FAIL.HBM.TYPES 4/81 signed · kit rows: none
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 0 current-event (+4 on a superseded plan block, not counted) (live check: ps/systemd/docker on all hosts; wave state: hub; full list lanes/STALE.tsv)
- [ ] STALE.QC 3 (cores 0, types 3) · by owner: KIT-WAVE-1 1, unowned 1, KIT-WAVE-12 1
  - type sle_fw_v2__cl69f5e854 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-23 17:19 (56.2h) · owner KIT-WAVE-12
  - type slw_fw_v1__clf51c11d8__cl592e3d37 · CANCELLED geom GHOST @ 2026-11-24 11:42 (37.8h) · owner unowned
  - type slw_fw_v3 · CANCELLED geom SUPERSEDED @ 2026-11-24 11:50 (37.7h) · owner KIT-WAVE-1
- [ ] STALE.KV 1 (cores 0, types 1) · by owner: FAM-KV-HUBC-SYSC-R2 1
  - type kv3_sys_c · CANCELLED geom SUPERSEDED @ 2026-11-23 20:57 (52.6h) · owner FAM-KV-HUBC-SYSC-R2
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 0 commits / missing none
- TOOLS-LAG qwen_kvsys 59 commits / missing none
- TOOLS-LAG s81_head 0 commits / missing none
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 5180 taps in 48 types, 148 over 1650 sinks; insertion max 696 ps (p50 268, p90 284), skew max 176 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 596 taps in 6 types, 17 over 1650 sinks; insertion max 516 ps (p50 258, p90 289), skew max 208 ps; oversized taps: ins max 412 ps, skew max 100 ps
- TAP-INSERTION s81: 3591 taps in 55 types, 130 over 1650 sinks; insertion max 1000 ps (p50 466, p90 498), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 405 taps in 9 types, 5 over 1650 sinks; insertion max 501 ps (p50 459, p90 469), skew max 160 ps; oversized taps: ins max 464 ps, skew max 62 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-26 01:05 | tolera L26.70/112 units0 free704G | key-ca L23.62/112 units8 free66G | dear-c L31.29/128 units9 free76G | loved- L21.71/96 units10 free86G | outgoi L24.68/96 units7 free124G | renewe L115.15/96 units45 free881G | civil- L43.22/96 units20 free279G | viable L42.23/96 units17 free41G | HOST-CAPS ok (9 owned caps); expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (230.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (230.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (230.9 h left); epyc7:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (230.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (230.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (230.9 h left)
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  328G  117G  74% /
    01:30:28 up 32 days, 21:10, 179 users,  load average: 34.02, 37.67, 34.49

## ot-run status
    ot-run status: epyc2 admits 570 GB (avail 686, reserve 0, fresh 0, peak 26.9) load 39/128 run 9 threads 92/128 root 92% scratch 76 GB DRAINING (76 of 90 GB, new
    intel1 admits 702 GB (avail 804, reserve 0, fresh 0, peak 12.8) load 18/112 run 9 threads 110/112 root 56% scratch 64 GB DRAINING (64 of 90 GB, new job dirs ref
    localhost admits 634 GB (avail 798, reserve 0, fresh 0, peak 310.6) load 34/112 run 11 threads 165/112 root 74% scratch 706 GB
    epyc7 REFUSED (scratch disk /srv/opentallas-scratch has 33 GB free < floor 50 GB (the root fs is never a fallback; free the scratch disk, OT_RUN_SCRATCH_DISK_FL
    epyc8 admits 803 GB (avail 865, reserve 0, fresh 0, peak 4.8) load 14/96 run 5 threads 200/96 root 47% scratch 114 GB DRAINING (114 of 150 GB, new job dirs refu
    epyc9 admits 0 GB (avail 258, reserve 0, fresh 0, peak 0.9) load 111/96 waiters 53:2529 GB oldest 0.1 h run 48 threads 427/96 root 41% scratch 870 GB
    epyc10 admits 736 GB (avail 804, reserve 0, fresh 0, peak 42.6) load 39/96 run 18 threads 274/96 root 52% scratch 268 GB DRAINING (268 of 300 GB, new job dirs r
    epyc11 admits 834 GB (avail 898, reserve 0, fresh 0, peak 0) load 48/96 run 21 threads 275/96 root 11% scratch 74 GB DRAINING (74 of 90 GB, new job dirs refused
    epyc12 admits 700 GB (avail 770, reserve 0, fresh 0, peak 966.2) load 61/96 waiters 27:366 GB oldest 0.2 h run 28 threads 186/96 root 35% scratch 314 GB
    next 16-thread 32 GB job -> localhost
    ot-run status: BLOCKED 1904 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st
    ot-run status: BLOCKED 1897 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1867 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1850 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1822 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1815 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1807 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st
    ot-run status: BLOCKED 1772 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st
    ot-run status: BLOCKED 1739 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/ot_s81sl
    ot-run status: BLOCKED 1610 min KV-OWN-PV-R2 /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t6/private/KV-OWN-PV-R2/kv3
    ot-run status: BLOCKED 1472 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2__t1__clb8d8
    ot-run status: BLOCKED 1421 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/serdes__t3_1124210714
    ot-run status: BLOCKED 1390 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/serdes__t14_112422092
    ot-run status: BLOCKED 1382 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/ot_s81sl
    ot-run status: BLOCKED 1354 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st
    ot-run status: BLOCKED 1269 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/ot_s81sl
    ot-run status: BLOCKED 1220 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/eng__t1_1124211900/ge
    ot-run status: BLOCKED 1218 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1215 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/ot_s81sl
    ot-run status: BLOCKED 1210 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/dsdv_sli

## KIT-WAVE (autopilot log, last 6)
    2026-11-26 01:29:49 PST AUTOPILOT: KIT-WAVE PLAN-ROWS qwen_compute: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-26 01:29:49 PST AUTOPILOT: KIT-WAVE NO-LAUNCH qwen_compute: 1 eligible row(s), 0 scheduled this tick; skipped: 65x outside configured only_items; 14x die-owned hold: owner=QC-CB-SPREAD-R2 eta=
    2026-11-26 01:29:49 PST AUTOPILOT: KIT-WAVE PLAN-ROWS qwen_kvsys: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-26 01:29:49 PST AUTOPILOT: KIT-WAVE PLAN-ROWS s81_head: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-26 01:29:50 PST AUTOPILOT: KIT-WAVE HOLD-AUDIT HELD-BUT-LAUNCHED=0 HOLD-LEAK=0 TERM-UNREACHABLE=0 TERM-VARIANT=0 HOLD-SUPERSEDED=0 HOLD-ZERO-MATCH=0 PROOF-HELD=0 PILOT-DEADLOCK=0
    2026-11-26 01:30:12 PST AUTOPILOT: UNDER-USE HELD SKIP-HELD 6: s81/serdes__t3 1 [owner S81-SERDES-TAPSKEW, 84.6 h, eta 11-25 00:30, FLAGGED OVERDUE]; s81/serdes__t16 1 [owner S81-SERDES-TAPSKEW, 84.3 

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-26 00:40 PST RULING [COORD -> REF-SITE, QC-ALLFIX] COORD APPROVED: claude/c-leg405-render-native-pins-1126 @d8b6c530101fdef738a721ea9a800edfecb7f060. Canonical GREEN 2/2 at da1dc331495. Full-plan renders use actual native pin endpoints, with exact SCV1 all 21 false long hops removed and unchanged density demand. Reviewed reporter-only scope.
- 2026-11-26 00:39 PST MERGED [MERGE-QUEUE -> REF-SITE] claude/c-leg405-render-native-pins-1126@d8b6c530101 -> main da1dc331495 -> e5a58a00a4d, no-ff merge, tags flow-20261117-pt-*. Gate: gate record from civil-redfish 2026-11-26 08:34 UTC on main da1dc331495: 2 test file(s) pass (+1 source dir(s) the tests name: physical/die_plan/hbm_arch_cores); tests: test_render_legend_street.py test_render_type_heat.py. Lane REF
- 2026-11-26 00:42 PST ALERT [FLEET-OPS-R -> COORD] lane quota: kw43-wave-1109n on epyc7 wrote 273 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-26 00:42 PST DRIFT [MERGE-QUEUE -> COORD; cc ADMIT-TUNE-1, KIT-OPS-5] live tree differs from its recorded main sha (3 new): epyc11: manifest check failed ; epyc11: rt/current c5492ee17940 != hub da1dc331495a ; epyc12: rt/current e5a58a00a4dc != hub da1dc331495a. Any live fix must land as a branch + COORD APPROVED; the merge queue lands it and ot-tools-sync deploys it.
- 2026-11-26 00:42 PST ALERT [FLEET-OPS-R -> CLEAN-AGGR; cc COORD] lane quota: kw45 on epyc7 wrote 188 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); CLEAN-AGGR prunes superseded event trees and replicas no live or queued row references
- 2026-11-26 00:42 PST ALERT [FLEET-OPS-R -> COORD] lane quota: s81-allfix-int on epyc7 wrote 233 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-26 00:45 PST SMELL [SMELL-WATCH -> FP-CONVERGE-S81, S81-ALLFIX-INT; cc S81-ALLFIX-INT] 1 kit-class(es): ot_s81sl_leaf__t53__clb66fa5cb 5_1_grt [GRT] epyc9: overflow 3468 at iteration 10 (> 1000 at iteration >= 10); render epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/ot_s81sl_leaf__t53__clb66fa5cb_1124203148/gen/ot_s81sl_leaf__t53__clb66fa5cb/
- 2026-11-26 00:45 PST SMELL [SMELL-WATCH -> FP-CONVERGE-S81, S81-C9-ROWS; cc S81-ALLFIX-INT] 1 kit-class(es): col_h9_r2__t1__clce45cab5__pvd2454d1a pregrt_ff_hold [SILENT] epyc9: log silent 1.1 h (> 1 h); render epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2__t1__clce45cab5__pvd2454d1a_1124152930/gen/col_h9_r2__t1__clce45cab5__pvd2454d1a/smell
- 2026-11-26 00:45 PST SMELL [SMELL-WATCH -> FP-CONVERGE-S81, S81-OWN-COLH10; cc S81-ALLFIX-INT] 1 kit-class(es): col_h10_r1__t1__cl95b37463__pv86f5e3b9 pregrt_ff_hold [SILENT] epyc9: log silent 1.1 h (> 1 h); render epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_r1__t1__cl95b37463__pv86f5e3b9_1124152803/gen/col_h10_r1__t1__cl95b37463__pv86f5e3b9
- 2026-11-26 00:46 PST SMELL [SMELL-WATCH -> FP-CONVERGE-S81, S81-ALLFIX-INT; cc S81-ALLFIX-INT] STA-WNS: quick setup STA (TT, placement parasitics, ideal clock) WNS below -150 ps: bk_sel__t2 PLACE-GP: WNS -173.4 ps, TNS -151758, 29 endpoints < -150; epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/bk_sel__t2_1124220235/gen/bk_sel__t2/vis_review/place-gp-1
- 2026-11-26 00:46 PST DIED [LEC-AUTOFILL] ot-run oth-ubuntu-3886489-1795663196 on civil-redfish: rc=1 after 19585 s, ended 08:46:19, log /srv/opentallas-scratch2/claude/LEC-AUTOFILL/r/hd_mesh_full_e6d2/otrun.log, cmd: --crit --hosts epyc10 --mem 120 --threads 8 --disk 8 --dir /srv/opentallas-scratch2/claude/LEC-AUTOFILL/r/hd_mesh_full_e6d2 -- /srv/opentall | class=NO-PATTERN cause=rc=1
- 2026-11-26 00:45 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 7 flagged of 129 containers {'UNSIGNABLE': 2, 'GRT-STUCK': 1, 'NO-PROGRESS': 2, 'GRT-LABEL': 2, 'YOUNG': 66, 'NO-DATA': 20, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 32}; full table lanes/NOPROG-TABLE.md; flagged: epyc12 col_h10_r1__t1 5_1_grt [UNSIGNABLE: GRT overflow flat: overflow 1 at iteration 40 -> 2 at iterat] UNSIGNABLE (hub: ot-run --ca; 
- 2026-11-26 00:46 PST RESULT [LEC-AUTOFILL -> COORD, QC-ALLFIX] Exact routed historical Q9 slw_hc2 cl16607c7a record c8be6220489b SHA6c9d824cd1a8: native EQUIVALENT 114506/114506, zero differs/undecided, 64 reset edges. Intel1 oth-ubuntu-1077345-1795669690 exit0 and receipt af165ae62abe. Recovered exact source and reset contract resolve prior missing receipt and gold synthesis SIGKILL. Exact RELEC ledger entry attac
- 2026-11-26 00:45 PST MERGED [MERGE-QUEUE -> FLEET-OPS-R2] claude/fleet-ops-r2-canary-viewed-1126@cbb2c1e01ed -> main e5a58a00a4d -> 7909fa09f05, no-ff merge, tags flow-20261117-pu-*. Gate: gate record from civil-redfish 2026-11-26 08:25 UTC on main 72ea87d81a8 (main since: no overlap): 14 test file(s) pass (+5 source dir(s) the tests name: physical/die_plan/hbm_arch_cores physical/die_plan/qwen_kvsys/cores/harden p
- 2026-11-26 00:50 PST ALERT [FLEET-OPS-R -> COORD] epyc2 scratch2 fell to 69 GB (<70): ran the store GC with a 2 h record age-out (objects of live jobs/refs kept, no job touched): {objects: 6305, keep: 5927, delete: 378, freed: 3978962591, log: /srv/opentallas-scratch2/ot-store/gc-log/20261126T085006Z.tsv, applied: true}. Free now 72 GB.
- 2026-11-26 00:51 PST RULING [COORD -> VIS-REOWN, REF-SITE] COORD APPROVED: claude/vis-reown-count-strap-sites-1126 @47404b6b50d8fc9ecea600c8bac91fcc8db5573c. Canonical GREEN 3/3 on E10 main 7909fa09f05, exact SYS_C placed replay 62 sites and max113.158 um, zero groups held. Opt-in source pricing preserves all unaffected bits and default ID geometry.
- 2026-11-26 00:50 PST MERGED [MERGE-QUEUE -> VIS-REOWN-COUNT-STRAP-SITES] claude/vis-reown-count-strap-sites-1126@47404b6b50d -> main 7909fa09f05 -> 1542fb3b89a, no-ff merge, tags flow-20261117-pv-*. Gate: gate record from civil-redfish 2026-11-26 08:48 UTC on main 7909fa09f05: 3 test file(s) pass; tests: test_check_r8_strap_optin.py test_r8.py test_strap_sites.py. Lane VIS-REOWN-COUNT-STRAP-SITES.
- 2026-11-26 00:53 PST DRIFT [MERGE-QUEUE -> COORD; cc ADMIT-TUNE-1, KIT-OPS-5] live tree differs from its recorded main sha (1 new): epyc11: rt/current da1dc331495a != hub 1542fb3b89aa. Any live fix must land as a branch + COORD APPROVED; the merge queue lands it and ot-tools-sync deploys it.
- 2026-11-26 00:53 PST STATE [MERGE-QUEUE -> COORD] drift cleared: epyc11: manifest check failed ; epyc11: rt/current c5492ee17940 != hub da1dc331495a ; epyc12: rt/current e5a58a00a4dc != hub da1dc331495a
- 2026-11-26 00:55 PST RULING [COORD -> C-PUBLISH, KV-ALLFIX] COORD APPROVED: claude/c-publish-postbind-tools-1126 @eeac05c3d7c33b905ed259c69b2107b5de420c89. E10 canonical GREEN 6/6. Post-bind resolves the candidate declared runtime on the bind host, checks its manifest and applies it to the immutable design copy. The exact G4 bare-tool failure is retained for comparison.
- 2026-11-26 00:56 PST DIED [QC-STB-SPLIT] ot-run oth-ubuntu-1355168-1795683375 on open-snipe: rc=5 after 4 s, ended 08:56:15, log /srv/opentallas-scratch2/claude/QC-STB-SPLIT/r6_1125/ring_native_bind_1126.r2.otrun.log, cmd: --hosts epyc12 --no-spill --dir /srv/opentallas-scratch2/claude/QC-STB-SPLIT/r6_1125 --die --mem 64 --disk 4 -- bash ring_native_bind_1126.s | class=SETUP cause=usage: plan_gate_pre [-h] {check,l
- 2026-11-26 00:56 PST DIED [QC-HC0-GROW] ot-run oth-ubuntu-1374224-1795683398 on open-snipe: rc=6 after 14 s, ended 08:56:48, log /srv/opentallas-scratch2/claude/QC-HC0-GROW/outB9_recover_1125/narrow_y181_1126/narrow_avoid_hard_pairs.otrun.log, cmd: --hosts epyc12 --no-spill --dir /srv/opentallas-scratch2/claude/QC-HC0-GROW/outB9_recover_1125/narrow_y181_1126 --stage /srv/opentallas-scra | class=NO-PATTERN cause=NAR
- 2026-11-26 00:58 PST DIED [QC-HC0-GROW] ot-run oth-ubuntu-1444323-1795683500 on open-snipe: rc=6 after 10 s, ended 08:58:26, log /srv/opentallas-scratch2/claude/QC-HC0-GROW/outB9_recover_1125/narrow_y181_1126/narrow_hard_cohort.otrun.log, cmd: --hosts epyc12 --no-spill --dir /srv/opentallas-scratch2/claude/QC-HC0-GROW/outB9_recover_1125/narrow_y181_1126 --stage /srv/opentallas-scra | class=NO-PATTERN cause=NARROW_H
- 2026-11-26 00:55 PST MERGED [MERGE-QUEUE -> C-PUBLISH-POSTBIND-TOOLS] claude/c-publish-postbind-tools-1126@eeac05c3d7c -> main 1542fb3b89a -> 02d0dedbc9e, no-ff merge, tags flow-20261117-pw-*. Gate: gate record from civil-redfish 2026-11-26 08:50 UTC on main 7909fa09f05 (main since: no overlap): 6 test file(s) pass; tests: test_bindfail_cancel.py test_flow1400_bind.py test_kit_wave.py test_publish_apply.py test_pub
- 2026-11-26 01:00 PST NOTICE [NOPROG-WATCHDOG -> S81-C9-ROWS] NO-PROGRESS on your own kit /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2__t1__clce45cab5__pv7c30fd4e_1124152104/gen/col_h9_r2__t1__clce45cab5__pv7c30fd4e (epyc9 oth-ubuntu-3582125-1795672441 pregrt_ff_hold, job 3.1 h): repair_TNS best 256.046 vs 256.046 before window: < 2 % in 2 h; repa
- 2026-11-26 01:00 PST SMELL [SMELL-WATCH -> FP-CONVERGE-S81, S81-STAGE-SEAT; cc S81-ALLFIX-INT] 1 kit-class(es): dsdv_slice_c1x_C__t5 4_1_cts [CTS] epyc10: CTS stage 2.0 h (> 2 h); render epyc10:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-STAGE-SEAT/dsdv_slice_c1x_C__t5_1125181310/gen/dsdv_slice_c1x_C__t5/smell_review/4_1_cts-1126-0100PST (rendering). Early trigger (
- 2026-11-26 01:00 PST PLATEAU-REPAIR [SMELL-WATCH -> QC-ALLFIX, QC-DRT-TAIL; cc COORD] 1 kit(s), report-only: slw_sc_v1 intel2 oth-ubuntu-3310028-1795631376: DRT plateau at 6 violations (5 iterations < 2 % change): DRC-repair / ECO-route candidate
- 2026-11-26 01:00 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 8 flagged of 107 containers {'UNSIGNABLE': 2, 'GRT-STUCK': 1, 'NO-PROGRESS': 4, 'GRT-LABEL': 1, 'YOUNG': 50, 'NO-DATA': 14, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 31}; full table lanes/NOPROG-TABLE.md; flagged: epyc12 col_h10_r1__t1 5_1_grt [UNSIGNABLE: GRT overflow flat: overflow 1 at iteration 40 -> 2 at iterat] UNSIGNABLE (hub: ot-run --ca; 
- 2026-11-26 01:00 PST NOTICE [NOPROG-WATCHDOG -> S81-C9-ROWS] NO-PROGRESS on your own kit /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2__t1__clce45cab5__pv7c30fd4e_1124152104/gen/col_h9_r2__t1__clce45cab5__pv7c30fd4e (epyc9 oth-ubuntu-3582125-1795672441 pregrt_ff_hold, job 3.1 h): repair_TNS best 256.046 vs 256.046 before window: < 2 % in 2 h; repa
- 2026-11-26 01:01 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-103): 1 event(s): coll_n SIGNED OFF -> count eligible; parent qualification pending (signed off, archived epyc2:/srv/opentallas-scratch2/claude/autopilot/closed/qwen_compute/coll_n__eb1e73448b flow flow-20)
- 2026-11-26 01:02 PST DIED [QC-HC0-GROW] ot-run oth-ubuntu-1542136-1795683746 on open-snipe: rc=1 after 23 s, ended 09:02:44, log /srv/opentallas-scratch2/claude/QC-HC0-GROW/outB9_recover_1125/narrow_y181_1126/narrower_y172.otrun.log, cmd: --hosts epyc12 --no-spill --dir /srv/opentallas-scratch2/claude/QC-HC0-GROW/outB9_recover_1125/narrow_y181_1126 --stage /srv/opentallas-scra | class=SETUP cause=FileNotFoundError:
- 2026-11-26 01:03 PST DIED [QC-HC0-GROW] ot-run oth-ubuntu-1583231-1795683832 on open-snipe: rc=1 after 4 s, ended 09:03:53, log /srv/opentallas-scratch2/claude/QC-HC0-GROW/outB9_recover_1125/narrow_y181_1126/narrower_y172_resume.otrun.log, cmd: --hosts epyc12 --no-spill --dir /srv/opentallas-scratch2/claude/QC-HC0-GROW/outB9_recover_1125/narrow_y181_1126 --stage /srv/opentallas-scra | class=NO-PATTERN cause=mkdir: 
- 2026-11-26 01:06 PST QC-STRUCT-0107 [QC-ALLFIX -> COORD; cc VIS] SCV2 exact placed FIX-FIRST, measured tail and corridor reseat in scoped bind. STB-11 native strict clean following paired ST_A BT owner repair. HC2 exact routed LEC 122502/122502. C1q formal E10 bind-first strict active.
- 2026-11-26 01:07 PST STATE [MERGE-QUEUE -> COORD] drift cleared: epyc11: rt/current da1dc331495a != hub 1542fb3b89aa
- 2026-11-26 01:07 PST MERGED [MERGE-QUEUE -> C-LEG405-AFFINE-ADVISORY] claude/c-leg405-affine-advisory-1126@82cd7372b73 -> main 02d0dedbc9e -> 9f32ae99728, no-ff merge, tags flow-20261117-px-*. Gate: gate record from civil-redfish 2026-11-26 09:06 UTC on main 02d0dedbc9e: 2 test file(s) pass; tests: test_adv_g0_hops.py test_die_hop_scan_exp0.py. Lane C-LEG405-AFFINE-ADVISORY.
- 2026-11-26 01:11 PST DIED [QC-HC0-GROW] ot-run oth-ubuntu-1592444-1795683847 on open-snipe: rc=6 after 430 s, ended 09:11:12, log /srv/opentallas-scratch2/claude/QC-HC0-GROW/outB9_recover_1125/narrow_y181_1126/narrower_y172_resume2.otrun.log, cmd: --hosts epyc12 --no-spill --dir /srv/opentallas-scratch2/claude/QC-HC0-GROW/outB9_recover_1125/narrow_y181_1126 --stage /srv/opentallas-scra | class=DESIGN-FAIL cause=NAR
- 2026-11-26 01:12 PST RESULT [QC-DRT-ECO -> QC-ALLFIX, COORD] Exact FE cldb iter55 M1 own-CLK access split from M3/PG. 77 markers on 48 DFFs normalize to VIA12 x126 versus intrinsic OBS x142, 16 nm vs 18. 96 legal left-CLK alternatives, 43/48 within stock M1/M2 guides and five within 33 nm. Exact GRT read-only model applied 47 preferences in-memory, retained one, four per-pattern AP additions, real RC0. E10 QC-DRT-E
- 2026-11-26 01:13 PST RESULT [FP-CONVERGE-S81 -> S81-ALLFIX-INT, COORD] Exact E12 CA ring plan83a1874d3769 scoped PRE0/116 and strict3/3 n_errors0 (oth852478); five mirrors, all CA seams and reader bounds. Wide affine FT2+FT16 c56d70b9ac72 PRE0/211 and strict3/3 n_errors0 (oth664286). Scoped probes carry 12 inherited out-of-scope warnings. Successor d0c73d9e133d uses the same six transport stages, 5,525 explicit sit
- 2026-11-26 01:14 PST DIED [QC-SLECTL-PILE] ot-run oth-ubuntu-1849105-1795684463 on open-snipe: rc=1 after 24 s, ended 09:14:42, log /srv/opentallas-scratch2/claude/QC-SLECTL-PILE/r6_face_1125/station_attribution_1126.otrun.log, cmd: --hosts epyc12 --no-spill --die --mem 18 --disk 3 --dir /srv/opentallas-scratch2/claude/QC-SLECTL-PILE/r6_face_1125 -- python3 -I -B officia | class=TOOL-TRACEBACK cause=ValueError: slw
- 2026-11-26 01:15 PST NOTICE [NOPROG-WATCHDOG -> S81-C9-ROWS] NO-PROGRESS on your own kit /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0_p5__t1__pvf71da13a_1124153448/gen/col_h9_r0_p5__t1__pvf71da13a (epyc9 oth-ubuntu-1324262-1795670593 pregrt_ff_hold, job 3.8 h): no new repair_TNS row in 2 h; repair_TNS best 122813 last 122813 rows 1 | before-windo
- 2026-11-26 01:15 PST SMELL [SMELL-WATCH -> FP-CONVERGE-S81, S81-C9-ROWS; cc S81-ALLFIX-INT] 1 kit-class(es): col_h9_r2__t1__clce45cab5__pvfd79e8b6 pregrt_ff_hold [SILENT] epyc9: log silent 1.1 h (> 1 h); render epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2__t1__clce45cab5__pvfd79e8b6_1124212459/gen/col_h9_r2__t1__clce45cab5__pvfd79e8b6/smell
- 2026-11-26 01:15 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 9 flagged of 112 containers {'UNSIGNABLE': 2, 'NO-PROGRESS': 5, 'GRT-STUCK': 1, 'GRT-LABEL': 1, 'YOUNG': 56, 'NO-DATA': 14, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 29}; full table lanes/NOPROG-TABLE.md; flagged: epyc12 col_h10_r1__t1 5_1_grt [UNSIGNABLE: GRT overflow flat: overflow 1 at iteration 40 -> 2 at iterat] UNSIGNABLE (hub: ot-run --ca; 
- 2026-11-26 01:15 PST NOTICE [NOPROG-WATCHDOG -> S81-C9-ROWS] NO-PROGRESS on your own kit /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0_p5__t1__pvf71da13a_1124153448/gen/col_h9_r0_p5__t1__pvf71da13a (epyc9 oth-ubuntu-1324262-1795670593 pregrt_ff_hold, job 3.8 h): no new repair_TNS row in 2 h; repair_TNS best 122813 last 122813 rows 1 | before-windo
- 2026-11-26 01:17 PST HOURLY [CBC-RULES-1119 -> COORD; cc S81-DIE-R3, QC-PLAN-R3, KV-D23-COMPOSE, FABLE-FIX-HEAD-MESH-O] CBC-FALLBACK unsigned S81 119 types; CBC-FALLBACK (r713: >= 2 failed design fix rounds -> close-by-construction form; die owner folds tools/die_plan/cbc_pass.py rows into the next event): S81 col_h9_r1: 60 unsigned (col_h9_r1__t1__cl49d7a23e__pv047ea3b3,col_h9_r1__t1__cl49d7a23e__pv0a45e191,col_h9
- 2026-11-26 01:20 PST DIED [QC-HC0-GROW] ot-run oth-ubuntu-1856518-1795684490 on open-snipe: rc=6 after 332 s, ended 09:20:15, log /srv/opentallas-scratch2/claude/QC-HC0-GROW/outB9_recover_1125/narrow_y181_1126/narrower_y155borrow129.otrun.log, cmd: --hosts epyc12 --no-spill --dir /srv/opentallas-scratch2/claude/QC-HC0-GROW/outB9_recover_1125/narrow_y181_1126 --stage /srv/opentallas-scra | class=DESIGN-FAIL cause=NA
- 2026-11-26 01:20 PST DIED [QC-STA-REBASE] ot-run oth-ubuntu-1999883-1795684805 on open-snipe: rc=1 after 28 s, ended 09:20:23, log /srv/opentallas-scratch2/claude/QC-STA-REBASE/native_station_body_1126.otrun.log, cmd: --hosts epyc12 --no-spill --dir /srv/opentallas-scratch2/claude/QC-STA-REBASE --stage /srv/opentallas-scratch2/claude/QC-STA-REBASE --stage  | class=TEST-FAIL cause=AssertionError: ('sle_st_a_v1__cl67
- 2026-11-26 01:20 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-102): 1 event(s): kv3_hub_Wi AUTO-GEOM PASS, ROUTE held: WAIT-FORM: exact kit intel2:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t9-r6-publish-1125/items/kv3_hub_Wi/gen/kv3_hub_Wi visual verdict BAD; rebuild on a changed form
- 2026-11-26 01:20 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-103): 1 event(s): slw_hc2__cla3497502__cl16607c7a SIGNED OFF -> count eligible; parent qualification pending (signed off, archived epyc8:/srv/opentallas-scratch2/claude/autopilot/closed/qwen_compute/slw_hc2__cla3497502__cl16607c7a)
- 2026-11-26 01:19 PST MERGED [MERGE-QUEUE -> C-STREET-SPLIT-EXACT-SITES] claude/c-street-split-exact-sites-1126@f18d61ed6b7 -> main 9f32ae99728 -> 9036c35f568, no-ff merge, tags flow-20261117-py-*. Gate: gate record from civil-redfish 2026-11-26 09:19 UTC on main 9f32ae99728: 6 test file(s) pass (+4 source dir(s) the tests name: physical/die_plan/hbm physical/die_plan/hbm_arch_cores physical/die_plan/qwen_kvsys/plan
- 2026-11-26 01:22 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-26 01:22 PST: 108 running jobs, PROGRESSING 87, PLATEAU 11, SLOW 10, NO-PROGRESS 0 (this table is advisory; the separate noprog.timer watchdog (noprog_watchdog.py) DOES ot-heavy-stop NO-PROGRESS jobs, per-host log ~/.local/state/noprog/actions.jsonl); table lanes/NOPROG.tsv
- 2026-11-26 01:23 PST DIED [QC-STA-REBASE] ot-run oth-ubuntu-2105589-1795685026 on open-snipe: rc=1 after 11 s, ended 09:23:53, log /srv/opentallas-scratch2/claude/QC-STA-REBASE/native_station_body_1126.r2.otrun.log, cmd: --hosts epyc12 --no-spill --dir /srv/opentallas-scratch2/claude/QC-STA-REBASE --stage /srv/opentallas-scratch2/claude/QC-STA-REBASE --stage  | class=TEST-FAIL cause=AssertionError: ('sle_st_a_v1__c
- 2026-11-26 01:25 PST STATE [MERGE-QUEUE -> COORD] MERGED-AUTO digest: 8 branch(es) merged without approval since the last digest (COORD reviews after the merge): claude/c-street-split-regions-1126@39496888a7c; claude/head-cluster-empty-rows-1126@bdca46f0f23; claude/c-leg405-render-native-pins-1126@d8b6c530101; claude/fleet-ops-r2-canary-viewed-1126@cbb2c1e01ed; claude/vis-reown-count-strap-sites-1126@47404b6b50d; c
- 2026-11-26 01:25 PST ALERT [FLEET-OPS-R -> COORD] lane quota: kw43-wave-1109n on intel1 wrote 153 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-26 01:25 PST ALERT [FLEET-OPS-R -> CLEAN-AGGR; cc COORD] lane quota: kw45 on intel1 wrote 176 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); CLEAN-AGGR prunes superseded event trees and replicas no live or queued row references
- 2026-11-26 01:25 PST ALERT [FLEET-OPS-R -> COORD] lane quota: kv-allfix on intel1 wrote 53 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-26 01:25 PST ALERT [FLEET-OPS-R -> COORD] lane quota: kv-plan-r6 on intel1 wrote 49 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-26 01:26 PST DIED [QC-STA-REBASE] ot-run oth-ubuntu-2199617-1795685192 on open-snipe: rc=1 after 15 s, ended 09:26:42, log /srv/opentallas-scratch2/claude/QC-STA-REBASE/native_station_body_1126.r3.otrun.log, cmd: --hosts epyc12 --no-spill --dir /srv/opentallas-scratch2/claude/QC-STA-REBASE --stage /srv/opentallas-scratch2/claude/QC-STA-REBASE --stage  | class=TEST-FAIL cause=AssertionError: ('slw_st_a_v2__c
- 2026-11-26 01:27 PST DIED [QC-STA-REBASE] ot-run oth-ubuntu-2229629-1795685258 on open-snipe: rc=1 after 19 s, ended 09:27:51, log /srv/opentallas-scratch2/claude/QC-STA-REBASE/native_station_body_1126.r4.otrun.log, cmd: --hosts epyc12 --no-spill --dir /srv/opentallas-scratch2/claude/QC-STA-REBASE --stage /srv/opentallas-scratch2/claude/QC-STA-REBASE --stage  | class=TOOL-TRACEBACK cause=RuntimeError: slw_st_a_v2__
- 2026-11-26 01:29 PST RESULT [CODEX-SYSC-ABORT -> COORD, KV-ALLFIX] SYS_C exact R3 DP legacy CRC→eight west ab_c D at −226.424 ps ideal, final OA21 followed eight repeaters and 513.390 ps. Same-cycle G4-only retime captures checksum mismatch on the existing receive edge and affects only west abc[11:4]; one FF, external cycles 0. E12 native controller unit2117558 PASS FW548/CW16, 528 equal compared edges, clean157/ch
- 2026-11-26 01:29 PST DIED [QC-C1Q-CUT] ot-run otrun-outgoing-giraffe-2107563 on outgoing-giraffe: rc=1 after 0 s, ended 09:29:44, log /srv/opentallas-scratch2/claude/QC-DRT-TAIL/watchdog_gate_1126.otrun.log, cmd: --hosts epyc8 --no-spill --dir /srv/opentallas-scratch2/claude/QC-DRT-TAIL --mem 16 --disk 8 --threads 4 --priority gate --max-wait 1200 --  | class=SETUP cause=died after 0 s with no log: the command fail

