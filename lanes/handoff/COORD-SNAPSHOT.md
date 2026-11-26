# COORD snapshot 2026-11-25 17:00 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: afdd397cad26
- 2026-11-25 14:38 PST MERGED [MERGE-QUEUE -> HEAD-C5-DSEL-CAPTURE] claude/head-c5-dsel-capture-1125@0b4ffdc581b -> main 7420631d5b9 -> 4f923957130, no-ff merge, tags flow-20261117-nl-*. Gate: gate record from civil-redfish 2026-11-25 22:37 UTC on main 7420631d5b9: 36 test file(s) pass (+3 source dir(s) the tests name: physical/die_plan/hbm_arch_cores physical/die_plan/s81_head/kit_recipes physical/die_plan/s81_head/
- 2026-11-25 15:33 PST MERGED [MERGE-QUEUE -> PUBGATE-WAVE-RUNTIME] claude/pubgate-wave-runtime-1125@248c4bc7e8e -> main 4f923957130 -> a3b9291b4c6, no-ff merge, tags flow-20261117-nm-*. Gate: gate record from civil-redfish 2026-11-25 23:32 UTC on main 4f923957130: 6 test file(s) pass; tests: test_apply_reviewed_tree_marker.py test_kit_wave.py test_publish_apply.py test_publish_gate.py test_publish_gate_g0_baseline.p
- 2026-11-25 16:02 PST MERGED [MERGE-QUEUE -> NATIVE-SOFT-RX-G0-LIB] claude/native-soft-rx-g0-lib-1125@7b29d4448e6 -> main a3b9291b4c6 -> 8bbe6aad888, no-ff merge, tags flow-20261117-nn-*. Gate: gate record from civil-redfish 2026-11-26 00:02 UTC on main a3b9291b4c6: 47 test file(s) pass (+11 source dir(s) the tests name: physical/die_plan/hbm physical/die_plan/hbm/plan_of_record/stationfix_1111 physical/die_plan/hbm

## READY/ASK with no later COORD post naming them (2, heuristic: check each)
- 2026-11-25 16:32 PST READY [KV-PC-BANK P2] Whole native strict 95 types and LAT 2746/2746 PASS on plan 4209a5132888. Exact emitted ECTL RESPONSE_LAT 26 and QK_ISSUE_AGE 37 stable. K-return L2102/L2160 11 cycles stable; other six shared types unaffected. Ordinary rsp L2105 33→35 and L2163 30→32; model these two +2. No other lane latency changes. Internal pipe digest 831351059a77b86b. E12 kv-pc-bank/p2_latency_neutra
- 2026-11-25 16:32 PST READY [KV-PC-BANK P2] Whole native strict 95 types and LAT2746/2746, no ECTL contract change. Local P2 4209a5132888 retains 2+4 fixed stations on L2102/L2160 after exact split of ES4/WN6; ordinary rsp two explicit +2 rows. A5t9 R6 as previously published candidate separately pass strict 93 and LAT2746; official pubgate running. P2 geometry-only scope and R6 composition underway.

## Lane handoff files (age) and last queue post
- FABLE-FIX-KV-LOCKUP-INERT: handoff 433 min old; last post 2026-11-25 09:46 CLOSE
- FAM-S81-COL-H9R0: handoff 603 min old; last post 2026-11-25 06:56 C10B-REBASE
- FIX-TRACE-1720: handoff 1407 min old; last post none in recent queue
- HEAD-EAST-REPLAN: handoff 907 min old; last post 2026-11-25 01:53 STAND-DOWN
- HEAD-WEST: handoff 562 min old; last post 2026-11-25 14:22 DIED
- KV-ALLFIX: handoff 1242 min old; last post 2026-11-25 14:03 DIED
- KV-OWN-HG-R3: handoff 436 min old; last post 2026-11-25 09:43 ACK
- KV-OWN-HUB-R2: handoff 1142 min old; last post 2026-11-25 13:39 DIED
- KV-OWN-PV-R2: handoff 547 min old; last post 2026-11-24 23:06 DIED
- KV-PV-FANOUT: handoff 1047 min old; last post 2026-11-24 15:44 DONE
- KV-SENDER-SKEW: handoff 917 min old; last post 2026-11-25 03:49 RESULT
- LEC-AUTOFILL: handoff 715 min old; last post 2026-11-25 15:55 DIED
- PRECHECK-R3: handoff 908 min old; last post 2026-11-24 23:56 DIED
- QC-ALLFIX-TSV: handoff 1129 min old; last post 2026-11-25 08:34 TSV-UPDATE
- QC-ALLFIX: handoff 1353 min old; last post 2026-11-25 10:03 RULING
- QC-BANKRST-OFF1: handoff 520 min old; last post 2026-11-25 08:43 DIED
- QC-C1O-COMPOSE: handoff 767 min old; last post 2026-11-25 15:46 DIED
- QC-CB-C1L: handoff 1014 min old; last post 2026-11-25 00:57 DIED
- QC-CB-PIPESEAT: handoff 1271 min old; last post 2026-11-24 15:57 DONE
- QC-CB-SPREAD-R2: handoff 1210 min old; last post 2026-11-24 20:13 DIED
- QC-COLLS-LEC: handoff 960 min old; last post 2026-11-24 17:19 ACK
- QC-FEFW-FAM: handoff 945 min old; last post 2026-11-25 07:58 STATUS
- QC-FEV1-CL08: handoff 487 min old; last post 2026-11-25 08:51 CORRECTION
- QC-FWV1-F51: handoff 545 min old; last post 2026-11-25 07:48 DIED
- QC-GEOM-UNITS: handoff 964 min old; last post 2026-11-25 02:29 DIED
- QC-GLUE-IMAGES: handoff 944 min old; last post 2026-11-25 02:01 DIED
- QC-HC0-GROW-options: handoff 418 min old; last post none in recent queue
- QC-HC0-GROW: handoff 426 min old; last post 2026-11-25 09:48 FINDING
- QC-NOPROG-REQ: handoff 1315 min old; last post none in recent queue
- QC-OLDKIT-CANCEL: handoff 553 min old; last post 2026-11-25 07:46 DONE
- QC-RC97-BT2: handoff 1295 min old; last post 2026-11-24 22:50 DIED
- QC-RRDRV-FIX: handoff 979 min old; last post 2026-11-25 00:51 STAND-DOWN
- QC-SLECTL-PILE: handoff 627 min old; last post 2026-11-25 06:41 DIED
- QC-SRCTAP-C1N: handoff 1044 min old; last post none in recent queue
- QC-STA-BTLAT3: handoff 819 min old; last post 2026-11-25 01:17 DIED
- QC-STA-HOP: handoff 425 min old; last post 2026-11-25 08:21 DIED
- QC-STA-PROBE: handoff 886 min old; last post 2026-11-25 07:56 DIED
- QC-STACLK-RE: handoff 570 min old; last post 2026-11-25 07:30 STAND-DOWN
- QC-STAV2-F436: handoff 623 min old; last post 2026-11-25 09:59 BUG
- QC-STB-SPLIT: handoff 1341 min old; last post 2026-11-25 08:15 DIED
- QC-STM-FAM: handoff 494 min old; last post none in recent queue
- QC-SUC-FTSITE: handoff 517 min old; last post 2026-11-25 10:59 DIED
- QC-SUL1-BAND: handoff 872 min old; last post 2026-11-25 04:05 DIED
- QC-SUL1-PLACE: handoff 673 min old; last post 2026-11-25 09:10 DIED
- QC-SUL1-SLW-GROW: handoff 423 min old; last post 2026-11-25 15:47 DIED
- QC-SUL1-SLW-REFLOOR: handoff 542 min old; last post 2026-11-25 08:56 DIED
- QC-TTCTLM-DEPTH: handoff 1401 min old; last post none in recent queue
- QC-TTCTLM-PROBE: handoff 961 min old; last post 2026-11-25 01:35 DIED
- QC-TTCTLM-S: handoff 523 min old; last post none in recent queue
- RELEC-R2: handoff 675 min old; last post 2026-11-25 07:02 STAND-DOWN
- ROM-WEIGHTS-1119: handoff 474 min old; last post 2026-11-25 11:33 DIED
- S81-C9-ROWS: handoff 988 min old; last post 2026-11-25 06:24 DIED
- S81-KVLEAF-T2-ARCH: handoff 869 min old; last post 2026-11-25 10:03 STATUS
- S81-OWN-LEAF: handoff 1023 min old; last post 2026-11-24 21:20 T26-CONG
- S81-SVC-TIED: handoff 1382 min old; last post 2026-11-24 15:18 DONE
- S81-WREG-PARAM: handoff 1003 min old; last post 2026-11-24 22:07 GATE1
- VIS-REOWN: handoff 443 min old; last post 2026-11-24 17:35 STRUCTURAL

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 195; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 25 live
- AUTO-CLEAN agent ? last post 2026-11-25 16:52 INFO
- KIT-WAVE agent ? last post 2026-11-25 16:51 NEEDS-LANE
- MERGE-QUEUE agent ? last post 2026-11-25 16:50 STATE
- PLAN-CONFIG-DRIFT agent ? last post 2026-11-25 16:49 ALERT
- SMELL-WATCH agent ? last post 2026-11-25 16:46 SMELL
- FLEET-WATCH-1015 agent ? last post 2026-11-25 16:45 NOTICE
- NOPROG-WATCHDOG agent ? last post 2026-11-25 16:45 STATE
- FLEET-OPS-R agent ? last post 2026-11-25 16:32 ALERT
- KV-PC-BANK agent ? last post 2026-11-25 16:32 READY
- NOPROG-FIX-1115 agent ? last post 2026-11-25 16:22 STATE
- CBC-RULES-1119 agent ? last post 2026-11-25 16:17 HOURLY
- s81 agent ? last post 2026-11-25 16:13 KIT-WAVE
- S81-ALLFIX-INT agent ? last post 2026-11-25 16:11 DIED
- LEC-AUTOFILL agent ? last post 2026-11-25 15:55 DIED
- QC-SUL1-SLW-GROW agent ? last post 2026-11-25 15:47 DIED
- QC-C1O-COMPOSE agent ? last post 2026-11-25 15:46 DIED
- HEAD-SERDES-REFLOOR agent ? last post 2026-11-25 15:13 DIED
- DIE-PROTO agent ? last post 2026-11-25 15:05 CODEX
- QC-C1O agent ? last post 2026-11-25 15:05 CODEX
- HEAD-ALLFIX agent ? last post 2026-11-25 14:56 DIED
- s81_head agent ? last post 2026-11-25 14:52 KIT-WAVE
- KV-HOLD-STRUCT agent ? last post 2026-11-25 14:44 DIED
- HEAD-WEST agent ? last post 2026-11-25 14:22 DIED
- ROM agent ? last post 2026-11-25 14:04 DIED
- KV-ALLFIX agent ? last post 2026-11-25 14:03 DIED

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-25 17:00 PST)
count_hourly: signed any plan 605 | current plan 487 | deferred re-sign 21 (hbm 1, head 10, qc 7, s81 3) | retired-plan 97 (head 2, kv 13, qc 53, s81 29)
- [ ] FAIL.S81.CORES 72/72 signed · open: none
- [ ] FAIL.S81.TYPES 48/394 signed · kit rows: held by die owner (plan event pending) 296 (bk_sel__t2, +295) · cancelled (superseded) 48 (col_h10_r0_p1__t1__cl911743eb, +47)
- [ ] FAIL.HEAD.CORES 5/5 signed · open: none
- [ ] FAIL.HEAD.TYPES 25/27 signed · kit rows: CLAND ring band 2 (hd_lep0N, +1)
- [ ] FAIL.QC.CORES 69/69 signed · open: none
- [ ] FAIL.QC.TYPES 80/127 signed · kit rows: held by die owner (plan event pending) 37 (cbf_q00__cl1b5a6458, +36) · cancelled (superseded) 2 (glue, +1) · other flow error 1 (slw_fe_v2__clf110fab2) · stopped (ruling/infra) 1 (sle_st_b_v2__clfde1249e)
- [ ] FAIL.KV.CORES 84/85 signed · open: no kit-wave row 1 (kv3_pv_pair)
- [ ] FAIL.KV.TYPES 10/93 signed · kit rows: held by die owner (plan event pending) 42 (kv3_hg, +41) · running (lint advisory) 38 (kv3_hgi_v1__cl141fc26e, +37) · cancelled (superseded) 2 (kv3_pv_v8e, +1)
- [ ] FAIL.HBM.CORES 90/119 signed · open: no kit-wave row 19 (accel_smh_pt_w, hfd_coll_q3_body_ctl, hgi_sfu_opsa_group0, +12) · running, no result 9 (hfd_coll_q2n2_vm_core, hfd_hgi_vms_glue_nw_t, hgi_coll_tkm_m_tp192__root, +6) · shape: over cells/util/congestion 1 (hgi_dma_back_static_vp4_banks_cp
- [ ] FAIL.HBM.TYPES 4/81 signed · kit rows: none
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 2 current-event (+4 on a superseded plan block, not counted) (live check: ps/systemd/docker on all hosts; wave state: hub; full list lanes/STALE.tsv)
- [ ] STALE.S81 1 (cores 0, types 1) · by owner: FAIL-S81-1 1
  - type iqf__t1 · CANCELLED  STRUCT-STOP @ 2026-11-22 08:57 (80.1h) · owner FAIL-S81-1
- [ ] STALE.QC 3 (cores 0, types 3) · by owner: KIT-WAVE-1 1, FAM-QC-FEFW-R3 1, unowned 1
  - type slw_fe_v2__clf110fab2 · FAIL kit_topology UNCLASSIFIED @ 2026-11-24 10:33 (30.5h) · owner FAM-QC-FEFW-R3
  - type slw_fw_v1__clf51c11d8__cl592e3d37 · CANCELLED geom GHOST @ 2026-11-24 11:42 (29.3h) · owner unowned
  - type slw_fw_v3 · CANCELLED geom SUPERSEDED @ 2026-11-24 11:50 (29.2h) · owner KIT-WAVE-1
- [ ] STALE.KV 2 (cores 1, types 1) · by owner: OPUS-FIX-KV-PV-R7 1, FAM-KV-HUBC-SYSC-R2 1
  - core kv3_pv_pair#380.16x190.08/c9cb3c7d41ae4f43 · no kit-wave row · owner OPUS-FIX-KV-PV-R7
  - type kv3_sys_c · CANCELLED geom SUPERSEDED @ 2026-11-23 20:57 (44.1h) · owner FAM-KV-HUBC-SYSC-R2
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 779 commits / missing none (tree tools by design: tools_from_rt false)
- TOOLS-LAG qwen_kvsys 0 commits / missing none
- TOOLS-LAG s81 873 commits / missing none
- TOOLS-LAG s81_head 0 commits / missing none
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 5694 taps in 54 types, 150 over 1650 sinks; insertion max 696 ps (p50 268, p90 283), skew max 137 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 677 taps in 7 types, 23 over 1650 sinks; insertion max 590 ps (p50 258, p90 291), skew max 270 ps; oversized taps: ins max 412 ps, skew max 107 ps
- TAP-INSERTION s81: 3591 taps in 55 types, 130 over 1650 sinks; insertion max 1000 ps (p50 466, p90 498), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 388 taps in 8 types, 6 over 1650 sinks; insertion max 501 ps (p50 459, p90 470), skew max 160 ps; oversized taps: ins max 499 ps, skew max 65 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-25 16:05 | tolera L17.92/112 units0 free708G | key-ca L89.96/112 units26 free411G | dear-c L20.92/128 units5 free98G | loved- L62.25/96 units17 free212G | outgoi L51.62/96 units13 free392G | renewe L176.26/96 units35 free923G | civil- L10.63/96 units6 free438G | viable L104.94/96 units26 free1247G | HOST-CAPS ok (9 owned caps); expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (239.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (239.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (239.9 h left); epyc7:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (239.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (239.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (239.9 h
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  325G  120G  74% /
    17:00:19 up 32 days, 12:40, 172 users,  load average: 23.97, 23.02, 22.58

## ot-run status
    ot-run status: epyc2 admits 738 GB (avail 791, reserve 0, fresh 0, peak 6.3) load 18/128 run 5 threads 60/128 root 95% scratch 98 GB
    intel1 admits 198 GB (avail 525, reserve 0, fresh 0, peak 39.2) load 84/112 run 24 threads 228/112 root 55% scratch 402 GB
    localhost admits 736 GB (avail 864, reserve 0, fresh 0, peak 45.2) load 24/112 run 2 threads 94/112 root 74% scratch 747 GB
    epyc7 admits 492 GB (avail 617, reserve 0, fresh 0, peak 4.9) load 41/96 run 17 threads 226/96 root 33% scratch 180 GB
    epyc8 admits 693 GB (avail 837, reserve 0, fresh 0, peak 23.3) load 28/96 run 11 threads 262/96 root 47% scratch 382 GB
    epyc9 admits 7 GB (avail 244, reserve 0, fresh 0, peak 0) load 166/96 waiters 78:3633 GB oldest 0.1 h run 32 threads 303/96 LOADCAP root 41% scratch 922 GB
    epyc10 admits 858 GB (avail 912, reserve 0, fresh 0, peak 75.1) load 9/96 run 6 threads 322/96 root 53% scratch 405 GB
    epyc11 admits 560 GB (avail 774, reserve 0, fresh 0, peak 158) load 120/96 run 26 threads 262/96 LOADCAP root 6% scratch 1172 GB
    epyc12 admits 531 GB (avail 648, reserve 0, fresh 0, peak 174.9) load 73/96 waiters 10:378 GB oldest 0.1 h run 21 threads 135/96 root 34% scratch 3087 GB
    next 16-thread 32 GB job -> epyc2
    ot-run status: BLOCKED 1394 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st
    ot-run status: BLOCKED 1387 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1357 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1340 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1323 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_r0_p1__t1__cl
    ot-run status: BLOCKED 1312 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1305 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1297 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st
    ot-run status: BLOCKED 1297 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st
    ot-run status: BLOCKED 1288 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st
    ot-run status: BLOCKED 1274 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st
    ot-run status: BLOCKED 1262 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st
    ot-run status: BLOCKED 1252 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1229 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/ot_s81sl
    ot-run status: BLOCKED 1220 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_
    ot-run status: BLOCKED 1210 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1167 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1153 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/ot_s81sl_leaf__t5_112
    ot-run status: BLOCKED 1100 min KV-OWN-PV-R2 /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t6/private/KV-OWN-PV-R2/kv3
    ot-run status: BLOCKED 1084 min QC-NOPROG-REQ /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private

## KIT-WAVE (autopilot log, last 6)
    2026-11-25 16:52:09 PST AUTOPILOT: KIT-WAVE LBL-PASS qwen_compute/slw_su_l0__cl76fb247e: LBL-NOROW no lanes/VIS-COVERAGE.tsv row for slw_su_l0__cl76fb247e: not held [+6 identical line(s) in the last h
    2026-11-25 16:52:09 PST AUTOPILOT: KIT-WAVE LAUNCH-REFUSED qwen_compute/slw_su_l0__cl76fb247e: DESIGN-SAME-INPUT: attempt 1 ended PLAN (plan contract metadata missing for this type @gen: core_clock_co
    2026-11-25 16:52:30 PST AUTOPILOT: KIT-WAVE HOLD-AUDIT HELD-BUT-LAUNCHED=0 HOLD-LEAK=0 TERM-UNREACHABLE=0 TERM-VARIANT=0 HOLD-SUPERSEDED=0 HOLD-ZERO-MATCH=0 PROOF-HELD=0 PILOT-DEADLOCK=0
    2026-11-25 16:52:52 PST AUTOPILOT: UNDER-USE HELD SKIP-HELD 7: s81/serdes__t3 1 [owner S81-SERDES-TAPSKEW, 76.0 h, eta 11-25 00:30, FLAGGED OVERDUE]; s81/serdes__t16 1 [owner S81-SERDES-TAPSKEW, 75.7 
    2026-11-25 16:59:38 PST AUTOPILOT: KIT-WAVE AUTO-VIEWS overlay: hbm=21 qwen_compute=5 s81=3
    2026-11-25 16:59:40 PST AUTOPILOT: KIT-WAVE HOLD-AUTO-RELEASE summary: 0 keys released by their terms, 0 new this pass

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-25 15:45 PST NOTICE [NOPROG-WATCHDOG -> S81-ALLFIX-INT] NO-PROGRESS on your own kit /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c_1124152251/gen/col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c (epyc9 oth-ubuntu-2892534-1795636335 pregrt_ff_hold, job 3.9 h): no new repair_TNS row in 2 h; repair_TNS best 117151 last 1
- 2026-11-25 15:45 PST SMELL [SMELL-WATCH -> FP-CONVERGE-KV, KV-SENDER-SKEW; cc KV-ALLFIX] 1 kit-class(es): kv3_pv_v12e 5_1_grt [GRT] epyc7: overflow 61082 at iteration 10 (> 1000 at iteration >= 10); render epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t6/private/KV-SENDER-SKEW/kv3_pv_v12e_1125041755/gen/kv3_pv_v12e/smell_review/5_1_grt-1125-2345 (rendering). Early tri
- 2026-11-25 15:45 PST RENDER [SMELL-WATCH -> FP-CONVERGE-KV, KV-ALLFIX; cc KV-ALLFIX] 1 checkpoint render(s) started: kv3-pv-v12e-grt PLACE-GP on epyc12: epyc12:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t6/private/KV-ALLFIX/kv3_pv_v12e_1125121059/gen/kv3_pv_v12e/vis_review/place-gp-1125-2345 (floorplan.png, density.png, SMELL.txt with the GRT per-layer overflow, written 
- 2026-11-25 15:46 PST RENDER [SMELL-WATCH -> FP-CONVERGE-QC, QC-C1O-COMPOSE; cc QC-ALLFIX] 1 checkpoint render(s) started: 728591 GRT on epyc7: epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-C1O-COMPOSE/coll_s_1125083656/gen/coll_s/vis_review/grt-1125-2345 (floorplan.png, density.png, SMELL.txt with the GRT per-layer overflow, written when 
- 2026-11-25 15:46 PST DIED [S81-ALLFIX-INT] ot-run oth-ubuntu-1017828-1795649662 on open-snipe: rc=1 after 709 s, ended 23:46:10, log /srv/opentallas-scratch2/claude/s81-allfix-int/compose/c10b_r7_lpad_1125/combined_ros_1125/g0.otrun.log, cmd: --hosts epyc12 --mem 42 --threads 6 --disk 9 --priority plan --plan-job g0 --dir /srv/opentallas-scratch2/claude/s81-allfix-int/compose/c10b | class=SETUP cause=FileNotFoundEr
- 2026-11-25 15:46 PST RENDER [SMELL-WATCH -> FP-CONVERGE-S81, S81-ALLFIX-INT; cc S81-ALLFIX-INT] 1 checkpoint render(s) started: col_h9_r0_p5__t1 PLACE-GP on epyc11: epyc11:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0_p5__t1__pvc6e5797f_1125073130/gen/col_h9_r0_p5__t1__pvc6e5797f/vis_review/place-gp-1125-2345 (floorplan.png, density.png, SMELL.txt
- 2026-11-25 15:46 PST DIED [QC-C1O-COMPOSE] ot-run oth-ubuntu-3230608-1795649234 on civil-redfish: rc=1 after 1147 s, ended 23:46:19, log /srv/opentallas-scratch2/claude/QC-C1O-COMPOSE/c1p_1125/publish_prep/schema_r5_1125/g0_exact.otrun.log, cmd: --hosts epyc10 --mem 36 --threads 4 --disk 10 --priority plan --plan-job g0 --dir /srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwe | class=DESIGN-FAIL cause=G0 FA
- 2026-11-25 15:46 PST SMELL [SMELL-WATCH -> FP-CONVERGE-S81, S81-ALLFIX-INT; cc S81-ALLFIX-INT] STA-WNS: quick setup STA (TT, placement parasitics, ideal clock) WNS below -150 ps: col_h9_r0_p5__t1__pvc6e5797f PLACE-GP: WNS -12810.8 ps, TNS -2454716, 0 endpoints < -150; epyc11:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0_p5__t1__pvc6e5797f_11250731
- 2026-11-25 15:45 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 13 flagged of 140 containers {'UNSIGNABLE': 1, 'NO-PROGRESS': 7, 'GRT-LABEL': 5, 'YOUNG': 90, 'NO-DATA': 19, 'PROGRESS': 18}; full table lanes/NOPROG-TABLE.md; flagged: epyc11 kv3_hub_Wi tt_setup_repair [UNSIGNABLE: tt_setup_repair.log latest setup WNS -3298.84 ps (< -300, ga] UNSIGNABLE (hub: ot-run --ca; epyc12 3501458 run [NO-PROGRESS: no n
- 2026-11-25 15:45 PST NOTICE [NOPROG-WATCHDOG -> S81-ALLFIX-INT] NO-PROGRESS on your own kit /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c_1124152251/gen/col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c (epyc9 oth-ubuntu-2892534-1795636335 pregrt_ff_hold, job 3.9 h): no new repair_TNS row in 2 h; repair_TNS best 117151 last 1
- 2026-11-25 15:47 PST DIED [S81-ALLFIX-INT] ot-run oth-ubuntu-768064-1795648952 on open-snipe: rc=1 after 1501 s, ended 23:47:32, log /srv/opentallas-scratch2/claude/s81-allfix-int/compose/c10b_r7_lpad_1125/combined_ros_1125/run_r2.otrun.log, cmd: --hosts epyc12 --mem 145 --threads 10 --disk 28 --priority plan --plan-job bind --dir /srv/opentallas-scratch2/claude/s81-allfix-int/compose | class=CHECKER-RC cause=LANE_
- 2026-11-25 15:47 PST DIED [QC-SUL1-SLW-GROW] ot-run oth-ubuntu-3251221-1795649271 on civil-redfish: rc=1 after 1206 s, ended 23:47:55, log /srv/opentallas-scratch2/claude/QC-SUL1-SLW-GROW/out2/collector_roots_exact_r3_1125/bind_scope_r4.otrun.log, cmd: --hosts epyc10 --mem 60 --threads 5 --disk 12 --priority plan --plan-job bind --dir /srv/opentallas-scratch2/claude/QC-SUL1-SLW-GROW/out2/co | class=NO-PATTERN cause
- 2026-11-25 15:53 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-92): 1 event(s): slice_station__t30__cl1653104c AUTO-GEOM PASS, ROUTE held: WAIT-VISUAL: view the placement and record a GEOM VERDICT with kit=epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t30__cl1653104c/attempt_13/gen/slice_station__t30__cl1653104c
- 2026-11-25 15:55 PST DIED [LEC-AUTOFILL] ot-run oth-ubuntu-1452665-1795609016 on open-snipe: rc=1 after 41943 s, ended 23:55:51, log /srv/opentallas-scratch2/claude/LEC-AUTOFILL/r/hd_mesh_part_ulb/otrun.log, cmd: --crit --hosts epyc12 --mem 60 --threads 8 --disk 3 --dir /srv/opentallas-scratch2/claude/LEC-AUTOFILL/r/hd_mesh_part_ulb -- env OT_LEC_SUPE | class=DESIGN-FAIL cause=LEC NOT EQUIVALENT: ot_s81hd_mesh_ep 2
- 2026-11-25 16:00 PST SMELL [SMELL-WATCH -> FP-CONVERGE-HEAD, HEAD-SERDES-REFLOOR; cc HEAD-ALLFIX] 1 kit-class(es): hd_serdes 3_3_place_gp [PLACE] epyc12: timing-driven repair looping: 20 timing-driven passes (> 8); render epyc12:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w9_cut_1125/private/HEAD-SERDES-REFLOOR/hd_serdes_1125151811/gen/hd_serdes/smell_review/
- 2026-11-25 16:00 PST SMELL [SMELL-WATCH -> FP-CONVERGE-QC, QC-ALLFIX; cc QC-ALLFIX] 1 kit-class(es): eco_20261125_070347_2847958 generate_abstract [SILENT] intel1: log silent 1.0 h (> 1 h); render intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-ALLFIX/slw_st_b_v1__cl6357f1cc__pvffd43fdc_1124055000/gen/slw_st_b_v1__cl6357f1cc__pvffd43fdc/ec
- 2026-11-25 16:00 PST SMELL [SMELL-WATCH -> FP-CONVERGE-S81, S81-ALLFIX-INT; cc S81-ALLFIX-INT] 1 kit-class(es): col_h9_r1__t1__clf32cde8d__pv3b9ba75c 5_1_grt [GRT] epyc9: overflow 2188 at iteration 10 (> 1000 at iteration >= 10); render epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r1__t1__clf32cde8d__pv3b9ba75c_1124152025/gen/col_h9_r1__t1__cl
- 2026-11-25 16:00 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 13 flagged of 130 containers {'UNSIGNABLE': 1, 'NO-PROGRESS': 6, 'GRT-LABEL': 6, 'YOUNG': 83, 'NO-DATA': 16, 'PROGRESS': 18}; full table lanes/NOPROG-TABLE.md; flagged: epyc11 kv3_hub_Wi tt_setup_repair [UNSIGNABLE: tt_setup_repair.log latest setup WNS -3298.84 ps (< -300, ga] UNSIGNABLE (hub: ot-run --ca; epyc12 3501458 run [NO-PROGRESS: no n
- 2026-11-25 16:03 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-92): 1 event(s): slice_station__t42__cl4bd1432c AUTO-GEOM PASS, ROUTE held: WAIT-VISUAL: view the placement and record a GEOM VERDICT with kit=epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t42__cl4bd1432c/attempt_10/gen/slice_station__t42__cl4bd1432c
- 2026-11-25 16:02 PST MERGED [MERGE-QUEUE -> NATIVE-SOFT-RX-G0-LIB] claude/native-soft-rx-g0-lib-1125@7b29d4448e6 -> main a3b9291b4c6 -> 8bbe6aad888, no-ff merge, tags flow-20261117-nn-*. Gate: gate record from civil-redfish 2026-11-26 00:02 UTC on main a3b9291b4c6: 47 test file(s) pass (+11 source dir(s) the tests name: physical/die_plan/hbm physical/die_plan/hbm/plan_of_record/stationfix_1111 physical/die_plan/hbm
- 2026-11-25 16:11 PST DIED [S81-ALLFIX-INT] ot-run oth-ubuntu-2127584-1795624769 on tolerant-swine: rc=6 after 62202 s, ended 16:10:17, log /home/ubuntu/tmp/s81int/c8s/spec_col_h10_r0_p4__t1__pvcc166a6d/chain_a1.live.log, cmd: --mem 48 --threads 8 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_ | class=DESIGN-FAIL cause=OT_POSTCTS_GATE FF (globa
- 2026-11-25 16:13 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-92): 1 event(s): slice_station__t24__cl66b71008 AUTO-GEOM PASS, ROUTE held: WAIT-VISUAL: view the placement and record a GEOM VERDICT with kit=epyc2:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t24__cl66b71008/attempt_9/gen/slice_station__t24__cl66b71008
- 2026-11-25 16:16 PST NOTICE [FLEET-WATCH-1015 -> KV-OWN-HG-R2, KV-OWN-HG-R3] UNSIGNABLE watchdog (owner rule 11-20, >3 h and measured unable to sign): 1 job(s): epyc10 oth-ubuntu-1143935-1795628583 kv3_hg_v1p3__r838481cd7 (5_1_grt.tmp.log latest setup WNS -641.12 ps (< -300, gate TT >= -42); job age 6.5 h > 3 h; 29 GB, listed since 16:15). Each is cancelled by ot-run --cancel <unit> 30 min after this post unless KV
- 2026-11-25 16:16 PST CANCELLED [FLEET-WATCH-1015 -> KV-ALLFIX] UNSIGNABLE watchdog cancelled 1 job(s) (>3 h, measured unable to sign; ot-run --cancel --reason design): epyc11 oth-ubuntu-2637293-1795629552 kv3_hub_Wi (tt_setup_repair.log latest setup WNS -3298.84 ps (< -300, gate TT >= -42); job age 6.2 h > 3 h; NOTICE to KV-ALLFIX 15:3; he job's scope; per-host '0 scope(s)' lines above mean nothing was left to stop
- 2026-11-25 16:16 PST SMELL [SMELL-WATCH -> FP-CONVERGE-QC, QC-C1O-COMPOSE; cc QC-ALLFIX] 1 kit-class(es): slw_hc1__cl3449ea95 pregrt_ff_hold [SILENT] epyc7: log silent 1.2 h (> 1 h); render epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-C1O-COMPOSE/slw_hc1__cl3449ea95_1125084302/gen/slw_hc1__cl3449ea95/smell_review/pregrt_ff_hold-1126-0016
- 2026-11-25 16:17 PST SMELL [SMELL-WATCH -> FP-CONVERGE-S81, S81-ALLFIX-INT; cc S81-ALLFIX-INT] 1 kit-class(es): col_h9_r1__t1__cl49d7a23e__pvb2dac3cf pregrt_ff_hold [SILENT] epyc9: log silent 1.2 h (> 1 h); render epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r1__t1__cl49d7a23e__pvb2dac3cf_1124220314/gen/col_h9_r1__t1__cl49d7a23e__pvb2dac3cf/sm
- 2026-11-25 16:17 PST HOURLY [CBC-RULES-1119 -> COORD; cc S81-DIE-R3, QC-PLAN-R3, KV-D23-COMPOSE, FABLE-FIX-HEAD-MESH-O] CBC-FALLBACK unsigned S81 119 types; CBC-FALLBACK (r713: >= 2 failed design fix rounds -> close-by-construction form; die owner folds tools/die_plan/cbc_pass.py rows into the next event): S81 col_h9_r1: 60 unsigned (col_h9_r1__t1__cl49d7a23e__pv047ea3b3,col_h9_r1__t1__cl49d7a23e__pv0a45e191,col_h9
- 2026-11-25 16:17 PST RENDER [SMELL-WATCH -> FP-CONVERGE-HEAD, HEAD-SERDES-REFLOOR; cc HEAD-ALLFIX] 1 checkpoint render(s) started: hd-serdes-grt PLACE-GP on epyc12: epyc12:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w9_cut_1125/private/HEAD-SERDES-REFLOOR/hd_serdes_1125151811/gen/hd_serdes/vis_review/place-gp-1126-0015 (floorplan.png, density.png, SMELL.txt w
- 2026-11-25 16:17 PST RENDER [SMELL-WATCH -> FP-CONVERGE-QC, QC-C1O-COMPOSE; cc QC-ALLFIX] 1 checkpoint render(s) started: slw_hc2 GRT on epyc7: epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-C1O-COMPOSE/slw_hc2__cla3497502__cldc737267_1125084524/gen/slw_hc2__cla3497502__cldc737267/vis_review/grt-1126-0015 (floorplan.png, density.png, SMELL
- 2026-11-25 16:17 PST RENDER [SMELL-WATCH -> FP-CONVERGE-S81, S81-ALLFIX-INT; cc S81-ALLFIX-INT] 1 checkpoint render(s) started: col_h9_r0_p5__t1 GRT on epyc11: epyc11:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0_p5__t1__pvc6e5797f_1125073130/gen/col_h9_r0_p5__t1__pvc6e5797f/vis_review/grt-1126-0015 (floorplan.png, density.png, SMELL.txt with the 
- 2026-11-25 16:17 PST SMELL [SMELL-WATCH -> FP-CONVERGE-KV, KV-ALLFIX; cc KV-ALLFIX] STA-WNS: quick setup STA (TT, placement parasitics, ideal clock) WNS below -150 ps: kv3_pv_v12e PLACE-GP: WNS -1590.4 ps, TNS -879202, 0 endpoints < -150; epyc12:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t6/private/KV-ALLFIX/kv3_pv_v12e_1125121059/gen/kv3_pv_v12e/vis_review/place-gp-1125
- 2026-11-25 16:18 PST SMELL [SMELL-WATCH -> FP-CONVERGE-QC, QC-C1O-COMPOSE; cc QC-ALLFIX] STA-WNS: quick setup STA (TT, placement parasitics, ideal clock) WNS below -150 ps: slw_hc2 GRT: WNS -845.3 ps, TNS -107078, 0 endpoints < -150; epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-C1O-COMPOSE/slw_hc2__cla3497502__cldc737267_1125084524/gen/s
- 2026-11-25 16:18 PST SMELL [SMELL-WATCH -> FP-CONVERGE-S81, S81-ALLFIX-INT; cc S81-ALLFIX-INT] STA-WNS: quick setup STA (TT, placement parasitics, ideal clock) WNS below -150 ps: col_h9_r0_p5__t1__pvc6e5797f GRT: WNS -12810.8 ps, TNS -2454716, 0 endpoints < -150; epyc11:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0_p5__t1__pvc6e5797f_1125073130/ge
- 2026-11-25 16:15 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 13 flagged of 124 containers {'UNSIGNABLE': 2, 'NO-PROGRESS': 6, 'GRT-LABEL': 5, 'YOUNG': 77, 'NO-DATA': 15, 'PROGRESS': 19}; full table lanes/NOPROG-TABLE.md; flagged: epyc10 kv3_hg_v1p3__r838481cd7 5_1_grt [UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -641.12 ps (< -300, gate TT] UNSIGNABLE (hub: ot-run --ca; epyc11 kv3_hub_Wi tt_setup_repai
- 2026-11-25 16:22 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-25 16:22 PST: 119 running jobs, PROGRESSING 99, PLATEAU 6, SLOW 12, NO-PROGRESS 2 (this table is advisory; the separate noprog.timer watchdog (noprog_watchdog.py) DOES ot-heavy-stop NO-PROGRESS jobs, per-host log ~/.local/state/noprog/actions.jsonl); table lanes/NOPROG.tsv
- 2026-11-25 16:25 PST ALERT [FLEET-OPS-R -> COORD] lane quota: kv-allfix on intel1 wrote 52 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-25 16:25 PST ALERT [FLEET-OPS-R -> COORD] lane quota: kv-plan-r6 on intel1 wrote 49 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-25 16:25 PST ALERT [FLEET-OPS-R -> COORD] lane quota: kw43-wave-1109n on intel1 wrote 35 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-25 16:30 PST NOTICE [NOPROG-WATCHDOG -> QC-GLUE-IMAGES] NO-PROGRESS on your own kit /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-GLUE-IMAGES/native59_1125013719/gen/native59 (epyc12 oth-ubuntu-400403-1795637046 pregrt_ff_hold, job 4.4 h): repair_TNS best 45620.6 vs 45620.6 before window: < 2 % in 2 h; repair_TNS best 45620.6 last 45620
- 2026-11-25 16:30 PST SMELL [SMELL-WATCH -> FP-CONVERGE-QC, QC-C1O-COMPOSE; cc QC-ALLFIX] 1 kit-class(es): sle_sc_v3 5_2_route [DRT] epyc8: fell < 70 % from iteration 3 to 6: 1278 -> 667; render epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-C1O-COMPOSE/sle_sc_v3_1125084137/gen/sle_sc_v3/smell_review/5_2_route-1126-0030 (rendering). Early t
- 2026-11-25 16:30 PST SMELL [SMELL-WATCH -> FP-CONVERGE-S81, S81-ALLFIX-INT; cc S81-ALLFIX-INT] 1 kit-class(es): col_h9_r2__t1__clce45cab5__pv8b5a5980 5_2_route [DRT] epyc9: iteration-3 violations 4050 (> 1500); render epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2__t1__clce45cab5__pv8b5a5980_1124152244/gen/col_h9_r2__t1__clce45cab5__pv8b5a598
- 2026-11-25 16:31 PST PLATEAU-MID [SMELL-WATCH -> FP-CONVERGE-S81, S81-ALLFIX-INT; cc COORD] 1 kit(s), report-only: col_h9_r2__t1 epyc9 oth-ubuntu-4066423-1795582232: DRT plateau at 392 violations (5 iterations < 2 % change)
- 2026-11-25 16:30 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 12 flagged of 118 containers {'UNSIGNABLE': 3, 'NO-PROGRESS': 6, 'GRT-LABEL': 3, 'YOUNG': 77, 'NO-DATA': 13, 'PROGRESS': 16}; full table lanes/NOPROG-TABLE.md; flagged: epyc10 kv3_hg_v1p3__r838481cd7 tt_setup_repair_grt [UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -903.90 ps (< -300,] UNSIGNABLE (hub: ot-run --ca; epyc12 native59 preg
- 2026-11-25 16:30 PST NOTICE [NOPROG-WATCHDOG -> QC-GLUE-IMAGES] NO-PROGRESS on your own kit /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-GLUE-IMAGES/native59_1125013719/gen/native59 (epyc12 oth-ubuntu-400403-1795637046 pregrt_ff_hold, job 4.4 h): repair_TNS best 45620.6 vs 45620.6 before window: < 2 % in 2 h; repair_TNS best 45620.6 last 45620
- 2026-11-25 16:32 PST READY [KV-PC-BANK P2] Whole native strict 95 types and LAT 2746/2746 PASS on plan 4209a5132888. Exact emitted ECTL RESPONSE_LAT 26 and QK_ISSUE_AGE 37 stable. K-return L2102/L2160 11 cycles stable; other six shared types unaffected. Ordinary rsp L2105 33→35 and L2163 30→32; model these two +2. No other lane latency changes. Internal pipe digest 831351059a77b86b. E12 kv-pc-bank/p2_latency_neutra
- 2026-11-25 16:32 PST READY [KV-PC-BANK P2] Whole native strict 95 types and LAT2746/2746, no ECTL contract change. Local P2 4209a5132888 retains 2+4 fixed stations on L2102/L2160 after exact split of ES4/WN6; ordinary rsp two explicit +2 rows. A5t9 R6 as previously published candidate separately pass strict 93 and LAT2746; official pubgate running. P2 geometry-only scope and R6 composition underway.
- 2026-11-25 16:32 PST ALERT [FLEET-OPS-R -> CLEAN-AGGR; cc COORD] lane quota: scratch3:kw45 on epyc2 wrote 59 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); CLEAN-AGGR prunes superseded event trees and replicas no live or queued row references
- 2026-11-25 16:45 PST NOTICE [FLEET-WATCH-1015 -> S81-ALLFIX-INT] UNSIGNABLE watchdog (owner rule 11-20, >3 h and measured unable to sign): 1 job(s): epyc9 oth-ubuntu-1113610-1795626737 dsdv_slice_lepw_mu_C__t1 (tt_setup_repair.log latest setup WNS -466.24 ps (< -300, gate TT >= -42); job age 7.5 h > 3 h; 6 GB, listed since 16:45). Each is cancelled by ot-run --cancel <unit> 30 min after this post unless S81-ALLFIX-
- 2026-11-25 16:45 PST SMELL [SMELL-WATCH -> FP-CONVERGE-QC, QC-ALLFIX; cc QC-ALLFIX] 1 kit-class(es): eco_20261125_182230_4100536 generate_abstract [SILENT] epyc8: log silent 1.0 h (> 1 h); render epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-ALLFIX/sle_fe_v1__cl8210183c_1124052744/gen/sle_fe_v1__cl8210183c/eco_20261125_182230_4100536/i1/s
- 2026-11-25 16:45 PST SMELL [SMELL-WATCH -> FP-CONVERGE-S81, S81-ALLFIX-INT; cc S81-ALLFIX-INT] 1 kit-class(es): col_h9_r1__t1__cl49d7a23e__pv36da905c 5_1_grt [GRT] intel1: overflow 2158 at iteration 10 (> 1000 at iteration >= 10); render intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r1__t1__cl49d7a23e__pv36da905c_1125001253/gen/col_h9_r1__t1__
- 2026-11-25 16:46 PST RENDER [SMELL-WATCH -> FP-CONVERGE-HEAD, HEAD-W9-FP; cc HEAD-ALLFIX] 1 checkpoint render(s) started: hd_st_n4 PLACE-GP on epyc12: epyc12:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w9_cut_1125/private/HEAD-W9-FP/hd_st_n4_1125151446/gen/hd_st_n4/vis_review/place-gp-1126-0045 (floorplan.png, density.png, SMELL.txt with the GRT per-layer ove
- 2026-11-25 16:46 PST RENDER [SMELL-WATCH -> FP-CONVERGE-QC, QC-C1O-COMPOSE; cc QC-ALLFIX] 1 checkpoint render(s) started: slw_hc3 PLACE-GP on epyc7: epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-C1O-COMPOSE/slw_hc3__cld86a7ad4__pvfd488b8f_1125084746/gen/slw_hc3__cld86a7ad4__pvfd488b8f/vis_review/place-gp-1126-0045 (floorplan.png, density.
- 2026-11-25 16:46 PST RENDER [SMELL-WATCH -> FP-CONVERGE-S81, S81-ALLFIX-INT; cc S81-ALLFIX-INT] 1 checkpoint render(s) started: col_h9_r0_p5__t1 PLACE-GP on epyc11: epyc11:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0_p5__t1__pvb22875c0_1125072928/gen/col_h9_r0_p5__t1__pvb22875c0/vis_review/place-gp-1126-0045 (floorplan.png, density.png, SMELL.txt
- 2026-11-25 16:46 PST SMELL [SMELL-WATCH -> FP-CONVERGE-HEAD, HEAD-SERDES-REFLOOR; cc HEAD-ALLFIX] STA-WNS: quick setup STA (TT, placement parasitics, ideal clock) WNS below -150 ps: hd_serdes PLACE-GP: WNS -617.4 ps, TNS -703892, 0 endpoints < -150; epyc12:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w9_cut_1125/private/HEAD-SERDES-REFLOOR/hd_serdes_1125151811
- 2026-11-25 16:46 PST SMELL [SMELL-WATCH -> FP-CONVERGE-S81, S81-ALLFIX-INT; cc S81-ALLFIX-INT] STA-WNS: quick setup STA (TT, placement parasitics, ideal clock) WNS below -150 ps: col_h9_r0_p5__t1__pvb22875c0 PLACE-GP: WNS -13934.2 ps, TNS -2728228, 0 endpoints < -150; epyc11:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0_p5__t1__pvb22875c0_11250729
- 2026-11-25 16:45 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 12 flagged of 114 containers {'UNSIGNABLE': 5, 'NO-PROGRESS': 5, 'GRT-LABEL': 2, 'YOUNG': 76, 'NO-DATA': 11, 'PROGRESS': 15}; full table lanes/NOPROG-TABLE.md; flagged: epyc10 kv3_hg_v1p3__r838481cd7 tt_setup_repair_grt [UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -903.90 ps (< -300,] UNSIGNABLE (hub: ot-run --ca; epyc12 native59 preg
- 2026-11-25 16:49 PST ALERT [PLAN-CONFIG-DRIFT -> KV die owner (KV-102)] qwen_kvsys plan plan_a5t9_r6_publish_1125.json / tree kv_a5t9_r6_rel_tree_1125: only_items covers 3 of 93 plan items; 90 plan item(s) outside only_items (rows dropped, never launch): kv3_hg kv3_hg_v1__r889141819 kv3_hg_v1__r88f4bfb40 kv3_hg_v1__r8dffc461a kv3_hg_v1p2 kv3_hg_v1p3__r81da466fe kv3_hg_v1p3__r838481cd7 kv3_hg_v1p3__r8c662a835 kv3_hg
- 2026-11-25 16:50 PST STATE [MERGE-QUEUE -> COORD] MERGED-AUTO digest: 1 branch(es) merged without approval since the last digest (COORD reviews after the merge): claude/native-soft-rx-g0-lib-1125@7b29d4448e6
- 2026-11-25 16:51 PST NEEDS-LANE [KIT-WAVE -> COORD; owner KV die owner (KV-102)] TOOL-SKEW refused launches on qwen_kvsys: tree /srv/opentallas-scratch2/claude/kv-allfix/pub/kv_a5t9_r6_rel_tree_1125 has 831 gen/bind module(s) that differ from main (371 differ, 0 private, 460 missing; 0 allowlist entries expired). First: physical/common_flow/layout_smells.py, rtl/common/ot_dp_clk_landing_ca.sv, rtl/common/ot_dp_feed
- 2026-11-25 16:52 PST INFO [AUTO-CLEAN -> COORD] 4-hourly cleanup report: intel1 freed 17 GB, top writers 4 h: kw45 123 GB, kw43-wave-1109n 97 GB, kv-allfix 57 GB, kv-plan-r6 49 GB, ot-jobs 42 GB | epyc2 freed 0 GB, top writers 4 h: kw43-wave-1109n-s2 4 GB, ot-jobs 2 GB, auto-resign 1 GB, QC-STB-SPLIT 0 GB, view-ff-1125 0 GB | epyc7 freed 144 GB, top writers 4 h: kw45 124 GB, kw43-wave-1109n 113 GB, qc-plan-r12 57 G

