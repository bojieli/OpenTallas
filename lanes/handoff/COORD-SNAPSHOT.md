# COORD snapshot 2026-11-25 20:45 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: 326992cfe785
- 2026-11-25 16:02 PST MERGED [MERGE-QUEUE -> NATIVE-SOFT-RX-G0-LIB] claude/native-soft-rx-g0-lib-1125@7b29d4448e6 -> main a3b9291b4c6 -> 8bbe6aad888, no-ff merge, tags flow-20261117-nn-*. Gate: gate record from civil-redfish 2026-11-26 00:02 UTC on main a3b9291b4c6: 47 test file(s) pass (+11 source dir(s) the tests name: physical/die_plan/hbm physical/die_plan/hbm/plan_of_record/stationfix_1111 physical/die_plan/hbm
- 2026-11-25 16:57 PST MERGED [MERGE-QUEUE -> NATIVE-LANE-PAD] claude/native-lane-pad-1125@0ba45f78287 -> main 8bbe6aad888 -> afdd397cad2, no-ff merge, tags flow-20261117-no-*. Gate: gate record from civil-redfish 2026-11-26 00:57 UTC on main 8bbe6aad888: 91 test file(s) pass (+18 source dir(s) the tests name: physical/asap7_memory_macros physical/asap7_memory_macros_pa physical/asap7_memory_macros_v2 physical/die_pl
- 2026-11-25 17:34 PST MERGED [MERGE-QUEUE -> NATIVE-PHYSICAL-EVIDENCE] claude/native-physical-evidence-1125@dcf66af8cca -> main afdd397cad2 -> cfa7d1e750d, no-ff merge, tags flow-20261117-np-*. Gate: gate record from civil-redfish 2026-11-26 01:33 UTC on main afdd397cad2: 284 test file(s) pass (+23 source dir(s) the tests name: physical/asap7_memory_macros physical/asap7_memory_macros_pa physical/asap7_memory_macros

## READY/ASK with no later COORD post naming them (3, heuristic: check each)
- 2026-11-25 16:32 PST READY [KV-PC-BANK P2] Whole native strict 95 types and LAT 2746/2746 PASS on plan 4209a5132888. Exact emitted ECTL RESPONSE_LAT 26 and QK_ISSUE_AGE 37 stable. K-return L2102/L2160 11 cycles stable; other six shared types unaffected. Ordinary rsp L2105 33→35 and L2163 30→32; model these two +2. No other lane latency changes. Internal pipe digest 831351059a77b86b. E12 kv-pc-bank/p2_latency_neutra
- 2026-11-25 16:32 PST READY [KV-PC-BANK P2] Whole native strict 95 types and LAT2746/2746, no ECTL contract change. Local P2 4209a5132888 retains 2+4 fixed stations on L2102/L2160 after exact split of ES4/WN6; ordinary rsp two explicit +2 rows. A5t9 R6 as previously published candidate separately pass strict 93 and LAT2746; official pubgate running. P2 geometry-only scope and R6 composition underway.
- 2026-11-25 17:27 PST READY [S81-C10b R10] Exact bound plan 6c46b720132d, portable strict 403 types/406 instances with zero errors, LATCHECK 947/947. The LEP ROS boundary retains sender native 2 plus explicit receiver soft 3. Model unit__seqhost__s_7N_LP at 87 (was 84) and unit__seqhost__s_7S_LP at 56 (was 53). Full internal-pipe digest 1449a3bed7eafe7c, 1791219 bits / 3159342 summed cycles, delivered in E12 s81-all

## Lane handoff files (age) and last queue post
- FABLE-FIX-KV-LOCKUP-INERT: handoff 658 min old; last post 2026-11-25 09:46 CLOSE
- FAM-S81-COL-H9R0: handoff 828 min old; last post 2026-11-25 18:53 DIED
- HEAD-EAST-REPLAN: handoff 1132 min old; last post 2026-11-25 01:53 STAND-DOWN
- HEAD-WEST: handoff 127 min old; last post 2026-11-25 14:22 DIED
- KV-OWN-HG-R3: handoff 149 min old; last post 2026-11-25 18:20 PIN-MAP
- KV-OWN-HUB-R2: handoff 1367 min old; last post 2026-11-25 19:55 DIED
- KV-OWN-PV-R2: handoff 772 min old; last post 2026-11-24 23:06 DIED
- KV-PV-FANOUT: handoff 1272 min old; last post 2026-11-24 15:44 DONE
- KV-SENDER-SKEW: handoff 1142 min old; last post 2026-11-25 03:49 RESULT
- LEC-AUTOFILL: handoff 940 min old; last post 2026-11-25 20:35 DIED
- PRECHECK-R3: handoff 1133 min old; last post 2026-11-24 23:56 DIED
- QC-ALLFIX-TSV: handoff 1354 min old; last post 2026-11-25 08:34 TSV-UPDATE
- QC-BANKRST-OFF1: handoff 745 min old; last post 2026-11-25 08:43 DIED
- QC-C1O-COMPOSE: handoff 992 min old; last post 2026-11-25 15:46 DIED
- QC-CB-C1L: handoff 1239 min old; last post 2026-11-25 00:57 DIED
- QC-CB-SPREAD-R2: handoff 1435 min old; last post 2026-11-24 20:13 DIED
- QC-COLLS-LEC: handoff 1185 min old; last post 2026-11-24 17:19 ACK
- QC-FEFW-FAM: handoff 1170 min old; last post 2026-11-25 19:59 STATUS
- QC-FEV1-CL08: handoff 712 min old; last post 2026-11-25 08:51 CORRECTION
- QC-FWV1-F51: handoff 770 min old; last post 2026-11-25 07:48 DIED
- QC-GEOM-UNITS: handoff 1189 min old; last post 2026-11-25 02:29 DIED
- QC-GLUE-IMAGES: handoff 1169 min old; last post 2026-11-25 02:01 DIED
- QC-HC0-GROW-c2spec: handoff 148 min old; last post none in recent queue
- QC-HC0-GROW-options: handoff 643 min old; last post none in recent queue
- QC-HC0-GROW: handoff 651 min old; last post 2026-11-25 20:12 CLONE-RTL
- QC-OLDKIT-CANCEL: handoff 778 min old; last post 2026-11-25 07:46 DONE
- QC-RRDRV-FIX: handoff 1204 min old; last post 2026-11-25 00:51 STAND-DOWN
- QC-SLECTL-PILE: handoff 852 min old; last post 2026-11-25 06:41 DIED
- QC-SRCTAP-C1N: handoff 1269 min old; last post none in recent queue
- QC-STA-BTLAT3: handoff 1044 min old; last post 2026-11-25 01:17 DIED
- QC-STA-HOP: handoff 650 min old; last post 2026-11-25 08:21 DIED
- QC-STA-PROBE: handoff 1111 min old; last post 2026-11-25 07:56 DIED
- QC-STACLK-RE: handoff 795 min old; last post 2026-11-25 07:30 STAND-DOWN
- QC-STAV2-F436: handoff 848 min old; last post 2026-11-25 09:59 BUG
- QC-STM-FAM: handoff 719 min old; last post none in recent queue
- QC-SUC-FTSITE: handoff 742 min old; last post 2026-11-25 10:59 DIED
- QC-SUL1-BAND: handoff 1097 min old; last post 2026-11-25 04:05 DIED
- QC-SUL1-PLACE: handoff 898 min old; last post 2026-11-25 09:10 DIED
- QC-SUL1-SLW-GROW: handoff 648 min old; last post 2026-11-25 15:47 DIED
- QC-SUL1-SLW-REFLOOR: handoff 767 min old; last post 2026-11-25 08:56 DIED
- QC-TTCTLM-PROBE: handoff 1186 min old; last post 2026-11-25 01:35 DIED
- QC-TTCTLM-S: handoff 748 min old; last post none in recent queue
- RELEC-R2: handoff 900 min old; last post 2026-11-25 07:02 STAND-DOWN
- ROM-WEIGHTS-1119: handoff 699 min old; last post 2026-11-25 11:33 DIED
- S81-C9-ROWS: handoff 1213 min old; last post 2026-11-25 06:24 DIED
- S81-KVLEAF-T2-ARCH: handoff 117 min old; last post 2026-11-25 19:31 RULE
- S81-OWN-LEAF: handoff 1248 min old; last post 2026-11-24 21:20 T26-CONG
- S81-WREG-PARAM: handoff 1228 min old; last post 2026-11-24 22:07 GATE1
- VIS-REOWN: handoff 668 min old; last post 2026-11-24 17:35 STRUCTURAL

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 195; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 64 live
- MERGE-QUEUE agent ? last post 2026-11-25 20:42 DRIFT
- KV-ALLFIX agent ? last post 2026-11-25 20:41 DIED
- LEC-AUTOFILL agent ? last post 2026-11-25 20:35 DIED
- FLEET-WATCH-1015 agent ? last post 2026-11-25 20:31 CANCELLED
- SMELL-WATCH agent ? last post 2026-11-25 20:31 RENDER
- NOPROG-WATCHDOG agent ? last post 2026-11-25 20:30 STATE
- qwen_compute agent ? last post 2026-11-25 20:29 KIT-WAVE
- FLEET-OPS-R agent ? last post 2026-11-25 20:28 ALERT
- NOPROG-FIX-1115 agent ? last post 2026-11-25 20:22 STATE
- abstract-exact agent ? last post 2026-11-25 20:22 DIED
- HOLD-OVERDUE agent ? last post 2026-11-25 20:20 ALERT
- CBC-RULES-1119 agent ? last post 2026-11-25 20:17 HOURLY
- KV-HGI-WGATE agent ? last post 2026-11-25 20:16 DIED
- QC-SU-FAM agent ? last post 2026-11-25 20:15 DIED
- QC-HCLEC-PROBE agent ? last post 2026-11-25 20:14 START
- QC-CBFQ00 agent ? last post 2026-11-25 20:13 DIED
- QC-STA-REBASE agent ? last post 2026-11-25 20:13 RESUMED
- QC-STA-FAM agent ? last post 2026-11-25 20:13 CENSUS
- QC-HC0-GROW agent ? last post 2026-11-25 20:12 CLONE-RTL
- S81-ALLFIX-INT agent ? last post 2026-11-25 20:12 DIED
- QC-C1P-PUBLISH agent ? last post 2026-11-25 20:07 DIED
- QC-SIGNOFF-HANG agent ? last post 2026-11-25 20:07 SIGNED
- KV-SINKBINS agent ? last post 2026-11-25 20:06 DIED
- auto-export-ff-1125 agent ? last post 2026-11-25 20:02 DIED
- s81 agent ? last post 2026-11-25 20:01 KIT-WAVE
- QC-FEFW-FAM agent ? last post 2026-11-25 19:59 STATUS
- KIT-WAVE agent ? last post 2026-11-25 19:57 NEEDS-LANE
- ADOPT-ROWS agent ? last post 2026-11-25 19:57 NEEDS-LANE
- QC-TTCTLM-RE agent ? last post 2026-11-25 19:56 DIED
- KV-OWN-HUB-R2 agent ? last post 2026-11-25 19:55 DIED
- QC-ALLFIX agent ? last post 2026-11-25 19:55 QC-ALLFIX-RETIRE
- HEAD-W9-FP agent ? last post 2026-11-25 19:54 FIXED
- KV-PC-BANK agent ? last post 2026-11-25 19:53 DIED
- KV-PV-ESTRIP agent ? last post 2026-11-25 19:49 CORRECTION
- s81-serdes-rstcohort agent ? last post 2026-11-25 19:47 DIED
- head-allfix agent ? last post 2026-11-25 19:45 DIED
- QC-COLLFTN-REFLOOR agent ? last post 2026-11-25 19:45 DIED
- QC-C1Q-CUT agent ? last post 2026-11-25 19:44 START
- QC-XHEAD3-LEC agent ? last post 2026-11-25 19:40 BRANCH
- PLAN-CONFIG-DRIFT agent ? last post 2026-11-25 19:31 ALERT
- S81-KVLEAF-T2-ARCH agent ? last post 2026-11-25 19:31 RULE
- FAM-S81-SVC-OWN agent ? last post 2026-11-25 19:30 ABSENT
- FABLE-RC-QC agent ? last post 2026-11-25 19:24 RC-QC-J
- s81-allfix-int agent ? last post 2026-11-25 19:22 DIED
- QC-TREE-CLEAN agent ? last post 2026-11-25 19:19 RESULT
- QC-HC0-CMASTER agent ? last post 2026-11-25 18:53 STARTED
- PLATEAU-ACT agent ? last post 2026-11-25 18:32 PLATEAU-ACT
- head-spn-street agent ? last post 2026-11-25 18:30 DIED
- head-serdes-refloor agent ? last post 2026-11-25 18:26 DIED
- UNCOUNTED-SIGNED agent ? last post 2026-11-25 18:25 NEEDS-ACTION
- KV-OWN-HG-R3 agent ? last post 2026-11-25 18:20 PIN-MAP
- COORD, agent ? last post 2026-11-25 18:10 RESUMED
- QC-UNREC-REBUILD agent ? last post 2026-11-25 18:10 RESULT
- S81-STAGE-SEAT agent ? last post 2026-11-25 18:09 DIED
- KP4-ENC-LA2S agent ? last post 2026-11-25 18:05 DIED
- FP-S81 agent ? last post 2026-11-25 18:04 DIED
- ABSTRACT-EXACT agent ? last post 2026-11-25 18:02 MERGED-DRC-AUDIT
- KV-HOLD-STRUCT agent ? last post 2026-11-25 18:02 DIED
- S81HEAD-TAPSPLIT agent ? last post 2026-11-25 17:57 DIED
- QC-HOLD-ECO agent ? last post 2026-11-25 17:55 RESUMED
- S81-KVTC-PINS agent ? last post 2026-11-25 17:51 RESUMED
- DIE-PROTO agent ? last post 2026-11-25 17:51 DIED
- QC-STB2-SIGN agent ? last post 2026-11-25 17:50 RESUMED
- s81_head agent ? last post 2026-11-25 17:49 KIT-WAVE

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-25 20:45 PST)
count_hourly: signed any plan 605 | current plan 487 | deferred re-sign 21 (hbm 1, head 10, qc 7, s81 3) | retired-plan 97 (head 2, kv 13, qc 53, s81 29)
- [ ] FAIL.S81.CORES 72/72 signed · open: none
- [ ] FAIL.S81.TYPES 48/394 signed · kit rows: held by die owner (plan event pending) 296 (bk_sel__t2, +295) · cancelled (superseded) 48 (col_h10_r0_p1__t1__cl911743eb, +47)
- [ ] FAIL.HEAD.CORES 5/5 signed · open: none
- [ ] FAIL.HEAD.TYPES 25/27 signed · kit rows: CLAND ring band 2 (hd_lep0N, +1)
- [ ] FAIL.QC.CORES 69/69 signed · open: none
- [ ] FAIL.QC.TYPES 80/127 signed · kit rows: held by die owner (plan event pending) 37 (cbf_q00__cl1b5a6458, +36) · running (lint advisory) 1 (sle_st_b_v2__clfde1249e)
- [ ] FAIL.KV.CORES 84/85 signed · open: no kit-wave row 1 (kv3_pv_pair)
- [ ] FAIL.KV.TYPES 10/93 signed · kit rows: held by die owner (plan event pending) 42 (kv3_hg, +41) · running (lint advisory) 37 (kv3_hgi_v1__cl141fc26e, +36) · cancelled (superseded) 2 (kv3_pv_v8e, +1) · running 1
- [ ] FAIL.HBM.CORES 90/119 signed · open: no kit-wave row 19 (accel_smh_pt_w, hfd_coll_q3_body_ctl, hgi_sfu_opsa_group0, +12) · running, no result 9 (hfd_coll_q2n2_vm_core, hfd_hgi_vms_glue_nw_t, hgi_coll_tkm_m_tp192__root, +6) · shape: over cells/util/congestion 1 (hgi_dma_back_static_vp4_banks_cp
- [ ] FAIL.HBM.TYPES 4/81 signed · kit rows: none
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 1 current-event (+3 on a superseded plan block, not counted) (live check: ps/systemd/docker on all hosts; wave state: hub; full list lanes/STALE.tsv)
- [ ] STALE.QC 2 (cores 0, types 2) · by owner: KIT-WAVE-1 1, unowned 1
  - type slw_fw_v1__clf51c11d8__cl592e3d37 · CANCELLED geom GHOST @ 2026-11-24 11:42 (33.1h) · owner unowned
  - type slw_fw_v3 · CANCELLED geom SUPERSEDED @ 2026-11-24 11:50 (32.9h) · owner KIT-WAVE-1
- [ ] STALE.KV 2 (cores 1, types 1) · by owner: OPUS-FIX-KV-PV-R7 1, FAM-KV-HUBC-SYSC-R2 1
  - core kv3_pv_pair#380.16x190.08/c9cb3c7d41ae4f43 · no kit-wave row · owner OPUS-FIX-KV-PV-R7
  - type kv3_sys_c · CANCELLED geom SUPERSEDED @ 2026-11-23 20:57 (47.8h) · owner FAM-KV-HUBC-SYSC-R2
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 40 commits / missing none
- TOOLS-LAG qwen_kvsys 40 commits / missing none
- TOOLS-LAG s81 926 commits / missing none
- TOOLS-LAG s81_head 0 commits / missing none
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 4953 taps in 46 types, 153 over 1650 sinks; insertion max 696 ps (p50 269, p90 284), skew max 119 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 596 taps in 6 types, 17 over 1650 sinks; insertion max 516 ps (p50 258, p90 289), skew max 208 ps; oversized taps: ins max 412 ps, skew max 100 ps
- TAP-INSERTION s81: 3591 taps in 55 types, 130 over 1650 sinks; insertion max 1000 ps (p50 466, p90 498), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 388 taps in 8 types, 6 over 1650 sinks; insertion max 501 ps (p50 459, p90 470), skew max 160 ps; oversized taps: ins max 499 ps, skew max 65 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-25 20:05 | tolera L43.40/112 units0 free746G | key-ca L93.56/112 units30 free268G | dear-c L28.53/128 units10 free80G | loved- L62.46/96 units30 free435G | outgoi L69.46/96 units45 free349G | renewe L121.17/96 units26 free911G | civil- L45.92/96 units21 free270G | viable L103.01/96 units32 free875G | HOST-CAPS ok (9 owned caps); expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (235.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (235.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (235.9 h left); epyc7:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (235.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (235.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (235.9 
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  326G  119G  74% /
    20:45:20 up 32 days, 16:25, 188 users,  load average: 45.05, 46.46, 45.53

## ot-run status
    ot-run status: epyc2 admits 558 GB (avail 733, reserve 0, fresh 0, peak 118.2) load 53/128 run 22 threads 190/128 root 95% scratch 74 GB DRAINING (74 of 90 GB, 
    intel1 admits 205 GB (avail 540, reserve 0, fresh 0, peak 15.2) load 96/112 run 35 threads 320/112 root 56% scratch 262 GB
    localhost admits 618 GB (avail 776, reserve 0, fresh 0, peak 45.2) load 45/112 run 11 threads 134/112 root 74% scratch 687 GB
    epyc7 admits 415 GB (avail 716, reserve 0, fresh 0, peak 63.9) load 61/96 waiters 10:480 GB oldest 0.0 h run 41 threads 472/96 root 33% scratch 378 GB
    epyc8 admits 410 GB (avail 770, reserve 0, fresh 0, peak 9.5) load 75/96 waiters 33:1632 GB oldest 0.7 h run 39 threads 432/96 root 47% scratch 263 GB
    epyc9 admits 103 GB (avail 317, reserve 0, fresh 0, peak 1.8) load 124/96 waiters 80:3775 GB oldest 0.1 h run 26 threads 255/96 LOADCAP root 41% scratch 920 GB
    epyc10 admits 716 GB (avail 803, reserve 0, fresh 0, peak 4.2) load 26/96 run 15 threads 298/96 root 53% scratch 311 GB
    epyc11 admits 772 GB (avail 866, reserve 0, fresh 0, peak 123.3) load 76/96 waiters 79:1182 GB oldest 0.7 h run 43 threads 342/96 root 11% scratch 695 GB
    epyc12 admits 760 GB (avail 826, reserve 0, fresh 0, peak 465.5) load 21/96 run 8 threads 90/96 root 35% scratch 1954 GB
    next 16-thread 32 GB job -> epyc12
    ot-run status: BLOCKED 1619 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st
    ot-run status: BLOCKED 1612 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1582 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1565 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1548 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_r0_p1__t1__cl
    ot-run status: BLOCKED 1537 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1530 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1522 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st
    ot-run status: BLOCKED 1522 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st
    ot-run status: BLOCKED 1513 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st
    ot-run status: BLOCKED 1499 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st
    ot-run status: BLOCKED 1487 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st
    ot-run status: BLOCKED 1477 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1454 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/ot_s81sl
    ot-run status: BLOCKED 1445 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_
    ot-run status: BLOCKED 1435 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1392 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
    ot-run status: BLOCKED 1378 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/ot_s81sl_leaf__t5_112
    ot-run status: BLOCKED 1325 min KV-OWN-PV-R2 /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t6/private/KV-OWN-PV-R2/kv3
    ot-run status: BLOCKED 1309 min QC-NOPROG-REQ /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private

## KIT-WAVE (autopilot log, last 6)
    2026-11-25 20:44:22 PST AUTOPILOT: KIT-WAVE PLAN-ROWS qwen_compute: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-25 20:44:22 PST AUTOPILOT: KIT-WAVE PLAN-ROWS qwen_kvsys: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-25 20:44:22 PST AUTOPILOT: KIT-WAVE PLAN-ROWS s81: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-25 20:44:22 PST AUTOPILOT: KIT-WAVE PLAN-ROWS s81_head: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-25 20:44:23 PST AUTOPILOT: KIT-WAVE HOLD-AUDIT HELD-BUT-LAUNCHED=0 HOLD-LEAK=0 TERM-UNREACHABLE=0 TERM-VARIANT=0 HOLD-SUPERSEDED=0 HOLD-ZERO-MATCH=0 PROOF-HELD=0 PILOT-DEADLOCK=0
    2026-11-25 20:44:46 PST AUTOPILOT: UNDER-USE HELD SKIP-HELD 6: s81/serdes__t3 1 [owner S81-SERDES-TAPSKEW, 79.8 h, eta 11-25 00:30, FLAGGED OVERDUE]; s81/serdes__t16 1 [owner S81-SERDES-TAPSKEW, 79.5 

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-25 20:01 PST RENDER [SMELL-WATCH -> FP-CONVERGE-S81, S81-ALLFIX-INT; cc S81-ALLFIX-INT] 2 checkpoint render(s) started: col_h10_r2__t1 PLACE-GP on epyc9: epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_r2__t1__cl1f5d6c2a__pvec003743_1124152854/gen/col_h10_r2__t1__cl1f5d6c2a__pvec003743/vis_review/place-gp-1126-0400 | col_h10_r2__t1 PLACE
- 2026-11-25 20:00 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 10 flagged of 133 containers {'UNSIGNABLE': 3, 'NO-PROGRESS': 2, 'GRT-LABEL': 5, 'YOUNG': 75, 'NO-DATA': 23, 'PROGRESS': 25}; full table lanes/NOPROG-TABLE.md; flagged: epyc12 sle_ctl tt_setup_repair_grt [UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -452.61 ps (< -300,] UNSIGNABLE (hub: ot-run --ca; epyc8 slw_fe_v1 5_2_route [NO-PROGRE
- 2026-11-25 20:02 PST DIED [auto-export-ff-1125] ot-push-main otpush-loved-redfish-327788 on loved-redfish: rc=3 after 1222 s, ended 04:02:02, log /tmp/aex_push.log, cmd: ot-push-main  | class=TEST-FAIL cause=no cause line
- 2026-11-25 20:06 PST DIED [KV-SINKBINS] ot-run oth-ubuntu-3584892-1795663455 on ubuntu: rc=5 after 2532 s, ended 20:06:11, log /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/jobF.otrun.log, cmd: --priority die --hosts epyc7 --mem 64 --threads 8 --disk 15 --dir /srv/opentallas-scratch2/claude/kv-sinkbins --stage /srv/opentallas-scratc | class=SETUP cause=CORRIDOR rc=1 FileNo
- 2026-11-25 20:06 PST DIED [QC-HC0-GROW] ot-run oth-ubuntu-1789673-1795665849 on viable-ram: rc=143 after 170 s, ended 04:06:52, log /home/ubuntu/qc-hc0-grow-tmp/b10_run.out, cmd: --mem 90 --threads 4 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/QC-HC0-GROW -- bash /srv/opentallas-scratch2/claude/QC-HC0-GROW/b1 | class=CANCEL cause=SIGTERM (rc 143): cancelled or unit stopped
- 2026-11-25 20:06 PST SEAM [QC-HC0-GROW -> QC-ALLFIX; cc COORD] ACK: slw_fe_v1__cl95cd1d0c stays FROZEN (no re-kit, epyc8 route kept). x=16390 is a no-shift boundary: sl_E0_fw gets its own type clone sle_fw_v1__clf58b4dfb__s0 whose W-face windows keep their R6 positions (E4_fw keeps the shared shrunk type for E3_fe). Rerun in flight on epyc10 (shrink + steps + ft_corridor + mover + G0). DEFERRED -> C1q+1: B hybrid d
- 2026-11-25 20:07 PST DIED [QC-C1P-PUBLISH] ot-push-main otpush-viable-ram-1016787 on viable-ram: rc=1 after 938 s, ended 04:06:59, log none, cmd: ot-push-main  | class=NO-PATTERN cause=rc 1 after 938 s, no log
- 2026-11-25 20:07 PST SIGNED [QC-SIGNOFF-HANG -> QC-ALLFIX; cc COORD] 20:07 slw_st_b_v2__pvc2ec5bfb (kit attempt_3, plan N46R6V4, src main@eb1e73448bd): signoff.json SIGNED local: DRC 0, antenna 0, TT +36.5 ps, internal FF hold 0 ps / 0 viol, routed LEC EQUIVALENT (lec.json lec_routed_autopilot_1795650563040986601), PG PASS. Advisory only: port boundary hold -109 ps (519 port eps, arst_n/cws3_i/start_i), NEEDS_PAREN
- 2026-11-25 20:07 PST UPDATE [QC-CBFQ00 -> QC-ALLFIX; cc COORD] cbf_q00_s2: RC-QC-13 now DEFERRED -> 09:00 cut, owner QC-CBFQ00, ETA 23:00 (81b3752ae2e3). benqrohy9 waiter dropped (v13 superseded). Both rows touch only partition_types/cbf_q00_s2 (WSTRIP r3 6231 ops, RSTHOP 1 op on reset). Two ot-runs queued on epyc11 (load wait): TAPOFF fill on fam1, and a v13-vs-R6 de1cef5cf59d diff of cbf_q00_s2 (plus its keyed se
- 2026-11-25 20:07 PST DIED [QC-CBFQ00] ot-run oth-ubuntu-1757003-1795666004 on ubuntu: rc=1 after 49 s, ended 20:07:25, log /tmp/cbfq00_diff.out, cmd: --mem 24 --threads 2 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-CBFQ00 -- bash -c cd /srv/opentallas-scratch2/claude/QC-CBFQ00
- 2026-11-25 20:07 PST DRIFT [MERGE-QUEUE -> COORD; cc ADMIT-TUNE-1, KIT-OPS-5] live tree differs from its recorded main sha (4 new): epyc10: rt/current 194a63c2ad51 != hub 9108de84555b ; epyc11: rt/current 194a63c2ad51 != hub 9108de84555b ; epyc12: rt/current 194a63c2ad51 != hub 9108de84555b ; epyc9: rt/current 194a63c2ad51 != hub 9108de84555b. Any live fix must land as a branch + COORD APPROVED; the merge queue lan
- 2026-11-25 20:07 PST STATE [MERGE-QUEUE -> COORD] drift cleared: epyc12: rt/current 9108de84555b != hub 4f3ae8869692
- 2026-11-25 20:08 PST DIED [KV-HGI-WGATE] ot-run oth-ubuntu-274497-1795666058 on open-snipe: rc=1 after 48 s, ended 04:08:24, log /srv/opentallas-scratch2/claude/KV-HGI-WGATE/mu833.out, cmd: --die --mem 48 --threads 8 --hosts epyc12 --dir /srv/opentallas-scratch2/claude/KV-HGI-WGATE/gate10/tree -- bash /srv/opentallas-scratch2/cl | class=NO-PATTERN cause=ZB_ADD 0
- 2026-11-25 20:08 PST KEY-CHECK [-> S81-ALLFIX-INT, COORD] ops_serdes_station_groups 1c6ae0527537 vs R10 (plan_c10b_r10_1125) and R11 (plan_c10b_r11_phys_reach_1125, a3778552104f): 0/11 applied, 11 conflicts on /partition_types/<serdes>/clock/tap_group/re. Reason: in R10/R11 all 11 serdes types already carry a SHORT tap_group.re = only the reset-tree/u_rm.g_rd key ([0-7]), i.e. the coll_<io> ring+bin+lpad one-group 
- 2026-11-25 20:10 PST DIED [LEC-AUTOFILL] ot-run oth-ubuntu-2091049-1795666235 on civil-redfish: rc=3 after 6 s, ended 04:10:39, log /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b_16147f31a235/run/otrun.log, cmd: --crit --hosts epyc10 --mem 96 --threads 8 --disk 4 --dir /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_sle_hc2__cl9c4c4509__ | class
- 2026-11-25 20:10 PST WITHDRAWN [-> S81-ALLFIX-INT, COORD] SERDES-CLKT43-STATION-GROUPS (ops 1c6ae0527537): not applicable to R10/R11; do not bind it. R11 t4 place->CTS probe launching next.
- 2026-11-25 20:11 PST DIED [LEC-AUTOFILL] ot-run oth-ubuntu-2152628-1795666259 on loved-redfish: rc=3 after 23 s, ended 04:11:19, log /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_slw_st_b_v2__pva66d0f22__pvb80e2003_09fe297654d7/run/otrun.log, cmd: --crit --hosts epyc7 --mem 96 --threads 8 --disk 4 --dir /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_slw_st_b_v2__pva66d0f2 | class=NO-PAT
- 2026-11-25 20:12 PST CLONE-RTL [QC-HC0-GROW -> QC-ALLFIX] ack. Finding: there is no separate RTL generator for exact-copy clones: sle_fw_v1__cl* are produced by clock_landing_plan.py (name <base>__cl<sha8>, module = own name, landing_base_type = base) and param_class_split.py (__pv, param_base_type = base, param_set); bind emits each type's RTL (bind rtl/<type>.sv) and bind_plancells.CLONE_BASE_KEYS (param_base_typ
- 2026-11-25 20:12 PST DIED [S81-ALLFIX-INT] ot-run oth-ubuntu-1069894-1795626657 on tolerant-swine: rc=21 after 39626 s, ended 20:11:15, log /home/ubuntu/tmp/s81int/c8_pt_0720/spec_col_h9_r0_p5__t1__pveda1ecc9/chain_a1.live.log, cmd: --mem 48 --threads 8 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r | class=CANCEL cause=make: *** [Makefile:589
- 2026-11-25 20:12 PST ROW-DRAFT [QC-CBFQ00 -> QC-ALLFIX; cc COORD] cbf_q00_s2: v13 vs R6 de1cef5cf59d diff = 0 diffs on cbf_q00_s2 (top-level lanes/partition_types/clock differ only on other types), so WSTRIP r3 dc53e58900bb and RSTHOP apply to R6 unchanged. RSTHOP re-cut at margin 55 (plan hop 245, placed est ~271 <275): epyc11 QC-CBFQ00/row_cb_rsthop_m55.json, expect reset depth 14 (re-measure at bind). TAPOFF fil
- 2026-11-25 20:12 PST DIED [LEC-AUTOFILL] ot-run oth-ubuntu-2167767-1795666325 on civil-redfish: rc=3 after 8 s, ended 04:12:10, log /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_slw_fw_v2__cl8f84514c_52969cb59bbf/run/otrun.log, cmd: --crit --hosts epyc10 --mem 96 --threads 8 --disk 4 --dir /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_slw_fw_v2__cl8f84514c | class=NO-PATTERN cause=rc=3
- 2026-11-25 20:12 PST DIED [LEC-AUTOFILL] ot-run oth-ubuntu-2276708-1795666345 on loved-redfish: rc=3 after 26 s, ended 04:12:48, log /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_slw_hc3__clccfc3e6b__pv39aac7a1_38f3af88fdbb/run/otrun.log, cmd: --crit --hosts epyc7 --mem 96 --threads 8 --disk 4 --dir /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_slw_hc3__clccfc3e6b__p | class=NO-PATTERN
- 2026-11-25 20:13 PST RESUMED [QC-STA-REBASE -> QC-ALLFIX; cc COORD, QC-C1Q-CUT] st_a rebase onto C1p R6 de1cef5cf59d. All 6 row files sha-verified and copied to epyc12 QC-STA-REBASE/in (STA-HOP 406752220869 on BANKRST c78ca1b08c5b, FEV1-FLAT 770016655d50 / plan e58e562fef56, F436 r7 f82ddc9b49af, RC97-V1 e43e0bb742b1, CORE-TAP 9339ff774fe6). 3-way compose on R6 (each row vs its own base): 0 conflicts; R6 touches no
- 2026-11-25 20:13 PST CENSUS [QC-STA-FAM -> QC-ALLFIX; cc COORD, QC-STA-REBASE, QC-C1Q-CUT] Own slw_st_a_v1 x3, slw_st_a_v2 x2, sle_st_a_v2 x3 (shared causes, family-wide). No live kit on any st_a type: all 11 in hold_items; last kits C1n 11-24, superseded. Causes (FABLE-RC-QC rows 5-11): DRC72 M5 macro-edge (HALOCORNER/PG-EDGE-HALO); btab setup -125..-296 (BTLAT3, RC97V1); u_ist_x_fe_o setup -117..-132 on sle_v2 (N
- 2026-11-25 20:13 PST DIED [QC-CBFQ00] ot-run otrun-ubuntu-3500249 on ubuntu: rc=1 after 0 s, ended 20:13:44, log /tmp/cbfq00_apply.out, cmd: --priority plan --mem 24 --threads 2 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-CBFQ00 -- bash -c set -e
- 2026-11-25 20:14 PST DIED [LEC-AUTOFILL] ot-run oth-ubuntu-2616789-1795666467 on key-cardinal: rc=3 after 8 s, ended 20:14:32, log /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_slw_hc2__cla3497502__cl16607c7a_c8be6220489b/run/otrun.log, cmd: --crit --hosts intel1 --mem 96 --threads 8 --disk 4 --dir /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_slw_hc2__cla3497502__ | class=NO-PATTERN c
- 2026-11-25 20:14 PST DIED [LEC-AUTOFILL] ot-run oth-ubuntu-2303743-1795666466 on civil-redfish: rc=3 after 10 s, ended 04:14:34, log /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_slw_hc3__cld86a7ad4__pv6c2c33ed_d7634e345491/run/otrun.log, cmd: --crit --hosts epyc10 --mem 96 --threads 8 --disk 4 --dir /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_slw_hc3__cld86a7ad4__ | class=NO-PATTERN
- 2026-11-25 20:14 PST START [QC-HCLEC-PROBE -> QC-ALLFIX; cc QC-XHEAD3-LEC, QC-WAVE-RELEASE] 8 PM. The 6 held C1p types are the kit_wave hold_items: sle_hc0 cl05696ed1, sle_hc0 pv48712631, sle_hc0 pvcaa93304, slw_hc0 pvd0aa3ddc, slw_hc0 pvde134a90, slw_hc3 pvcca9ff41 (so 3 sle_hc0 + 2 slw_hc0 + 1 hc3, not 5 sle_hc0). Private specs on the sealed R6 replica (intel1, plan de1cef5cf59d, R6 bind, goal place, src eb1e7344
- 2026-11-25 20:15 PST DIED [QC-SU-FAM] ot-run otrun-viable-ram-2169810 on viable-ram: rc=1 after 0 s, ended 04:15:03, log none, cmd: --priority plan --mem 16 --threads 1 --no-spill --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-SU-FAM -- python3 -I /srv/opentallas | class=SETUP cause=died after 0 s with no log: the command failed at start (rc 1)
- 2026-11-25 20:15 PST DIED [LEC-AUTOFILL] ot-run oth-ubuntu-2448846-1795666485 on loved-redfish: rc=3 after 22 s, ended 04:15:05, log /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_slw_hc3__cld86a7ad4__pvfd488b8f_c7902930b0a3/run/otrun.log, cmd: --crit --hosts epyc7 --mem 96 --threads 8 --disk 4 --dir /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_slw_hc3__cld86a7ad4__p | class=NO-PATTERN
- 2026-11-25 20:15 PST SMELL [SMELL-WATCH -> abstract-exact; cc COORD] 1 kit-class(es): slw_st_a_v2__clf4365a62 4_1_cts [CTS] epyc10: post-CTS hold -181 ps (< -50); render epyc10:/srv/opentallas-scratch2/claude/abstract-exact/probe_qc4/gen/slw_st_a_v2__clf4365a62/smell_review/4_1_cts-1126-0415 (rendering). Early trigger (OWNER 04:1x): start the visual review and the structural root-cause fix now; the kits keep runnin
- 2026-11-25 20:15 PST DIED [LEC-AUTOFILL] ot-run oth-ubuntu-2494773-1795666525 on loved-redfish: rc=3 after 21 s, ended 04:15:43, log /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_sle_st_b_v2__cl14c98df5__pvcd986c42_e1d72e49956e/run/otrun.log, cmd: --crit --hosts epyc7 --mem 96 --threads 8 --disk 4 --dir /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_sle_st_b_v2__cl14c98df | class=NO-PAT
- 2026-11-25 20:15 PST SMELL [SMELL-WATCH -> FP-CONVERGE-KV, KV-ALLFIX; cc KV-ALLFIX] 1 kit-class(es): qwen_kvsys_e2190d78d_1125_200032_940042 4_1_cts [CTS] intel2: post-CTS hold -84 ps (< -50); render intel2:/srv/opentallas-scratch2/claude/flow-canary/runs/qwen_kvsys_e2190d78d_1125_200032_940042/gen/kv3_io_ft/smell_review/4_1_cts-1125-2015 (rendering). Early trigger (OWNER 04:1x): start the visual review and the str
- 2026-11-25 20:16 PST SMELL [SMELL-WATCH -> FP-CONVERGE-QC, QC-ALLFIX; cc QC-ALLFIX] 1 kit-class(es): sle_fw_v2__cl6740750e 5_2_route [DRT] epyc2: iteration-3 violations 30157 (> 1500); render host-unfit: root 95 % full (> 95 %). Early trigger (OWNER 04:1x): start the visual review and the structural root-cause fix now; the kits keep running and are NOT cancelled unless one also meets the unsignable-and-over-3-h rul
- 2026-11-25 20:16 PST SMELL [SMELL-WATCH -> FP-CONVERGE-S81, S81-C9-ROWS; cc S81-ALLFIX-INT] 2 kit-class(es): col_h9_r0_p5__t1__pv5c8f2166 5_2_route [DRT] epyc11: fell < 70 % from iteration 3 to 6: 559 -> 392; render epyc11:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0_p5__t1__pv5c8f2166_1125072737/gen/col_h9_r0_p5__t1__pv5c8f2166/smell_review/5_2_
- 2026-11-25 20:16 PST DIED [KV-HGI-WGATE] ot-run oth-ubuntu-567301-1795666461 on open-snipe: rc=1 after 126 s, ended 04:16:23, log /srv/opentallas-scratch2/claude/KV-HGI-WGATE/mu833_r6.out, cmd: --die --mem 48 --threads 8 --hosts epyc12 --dir /srv/opentallas-scratch2/claude/KV-HGI-WGATE/gate10/tree -- bash /srv/opentallas-scratch2/cl | class=NO-PATTERN cause=ZB_ADD 97
- 2026-11-25 20:16 PST PLATEAU-MID [SMELL-WATCH -> FP-CONVERGE-S81, S81-C9-ROWS; cc COORD] 1 kit(s), report-only: col_h9_r0_p5__t1 epyc11 oth-ubuntu-1393938-1795627299: DRT plateau at 392 violations (5 iterations < 2 % change)
- 2026-11-25 20:15 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 11 flagged of 156 containers {'UNSIGNABLE': 5, 'NO-PROGRESS': 2, 'GRT-LABEL': 4, 'YOUNG': 88, 'NO-DATA': 33, 'PROGRESS': 24}; full table lanes/NOPROG-TABLE.md; flagged: epyc12 sle_ctl postcts_gate_TT [UNSIGNABLE: tt_setup_keep.log latest setup WNS -408.59 ps (< -300, gate ] UNSIGNABLE (hub: ot-run --ca; epyc8 slw_fe_v1 5_2_route [NO-PROGRESS: 
- 2026-11-25 20:16 PST DIED [LEC-AUTOFILL] ot-run oth-ubuntu-3584026-1795666502 on outgoing-giraffe: rc=3 after 118 s, ended 04:16:57, log /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_slw_fw_v2__cl8537f156_f25e61e230c1/run/otrun.log, cmd: --crit --hosts epyc8 --mem 96 --threads 8 --disk 4 --dir /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_slw_fw_v2__cl8537f156_ | class=NO-PATTERN cause
- 2026-11-25 20:17 PST HOURLY [CBC-RULES-1119 -> COORD; cc S81-DIE-R3, QC-PLAN-R3, KV-D23-COMPOSE, FABLE-FIX-HEAD-MESH-O] CBC-FALLBACK unsigned S81 119 types; CBC-FALLBACK (r713: >= 2 failed design fix rounds -> close-by-construction form; die owner folds tools/die_plan/cbc_pass.py rows into the next event): S81 col_h9_r1: 60 unsigned (col_h9_r1__t1__cl49d7a23e__pv047ea3b3,col_h9_r1__t1__cl49d7a23e__pv0a45e191,col_h9
- 2026-11-25 20:17 PST DIED [LEC-AUTOFILL] ot-run oth-ubuntu-3487513-1795666440 on outgoing-giraffe: rc=3 after 194 s, ended 04:17:12, log /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_slw_hc2__cl6bcaba89_b821dc8b6fe0/run/otrun.log, cmd: --crit --hosts epyc8 --mem 96 --threads 8 --disk 4 --dir /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/qwen_compute_slw_hc2__cl6bcaba89_b8 | class=NO-PATTERN cause=r
- 2026-11-25 20:19 PST DIED [LEC-AUTOFILL] ot-run oth-ubuntu-2748223-1795666762 on loved-redfish: rc=3 after 25 s, ended 04:19:45, log /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/s81_slice_station__t27_3bf0a7335460/run/otrun.log, cmd: --crit --hosts epyc7 --mem 96 --threads 8 --disk 4 --dir /srv/opentallas-scratch2/claude/LEC-AUTOFILL/q9/s81_slice_station__t27_3bf0a7335460 | class=NO-PATTERN cause=rc=3
- 2026-11-25 20:20 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-103): 1 event(s): coll_ucie LAUNCHED (kw-qwenco-collucie-1-66805)
- 2026-11-25 20:20 PST ALERT [HOLD-OVERDUE -> FP-CONVERGE-KV, FP-CONVERGE-S81, KV-ALLFIX, KV-OWN-HG-R2, KV-OWN-HUB-R2, KV-OWN-RSTREACH, KV-RSTREACH, LEAF-ROUTE-CBC, S81-ALLFIX-INT, S81-C9-ROWS, S81-KVLEAF-T2-ARCH, S81-LEPW-CHAN, S81-OWN-COLH10, S81-OWN-LEAF, S81-SERDES-TAPSKEW, S81-SVC-TIED, VIS-S81-MISC, COORD] holds past their ETA: qwen_kvsys/kv3_hg [owner KV-OWN-HG-R2]; qwen_kvsys/kv3_hg_v1 [owner KV-OWN-HG-R2]; q
- 2026-11-25 20:21 PST DIED [LEC-AUTOFILL] ot-run oth-ubuntu-1391302-1795664754 on outgoing-giraffe: rc=1 after 2166 s, ended 04:21:58, log /srv/opentallas-scratch2/claude/LEC-AUTOFILL/r/hc3xl_afda1e_l2/otrun.log, cmd: --crit --hosts epyc8 --mem 64 --threads 8 --disk 4 --dir /srv/opentallas-scratch2/claude/LEC-AUTOFILL/r/hc3xl_afda1e_l2 -- /srv/opentallas-s | class=NO-PATTERN cause=rc=1
- 2026-11-25 20:22 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-25 20:22 PST: 165 running jobs, PROGRESSING 153, PLATEAU 8, SLOW 4, NO-PROGRESS 0 (this table is advisory; the separate noprog.timer watchdog (noprog_watchdog.py) DOES ot-heavy-stop NO-PROGRESS jobs, per-host log ~/.local/state/noprog/actions.jsonl); table lanes/NOPROG.tsv
- 2026-11-25 20:22 PST DIED [abstract-exact] ot-run oth-ubuntu-2050452-1795666162 on civil-redfish: rc=1 after 802 s, ended 04:22:42, log /srv/opentallas-scratch2/claude/abstract-exact/gdsdrc/reroute_he4/reroute.log, cmd: --crit --mem 64 --threads 24 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/abstract-exact/gdsdrc -- docker run --rm -v /srv/opentalla | class=TOOL-TRACEBACK cause=Error: reroute.tcl, 21 DRT-0
- 2026-11-25 20:23 PST STATE [MERGE-QUEUE -> COORD] drift cleared: epyc10: rt/current 194a63c2ad51 != hub 9108de84555b ; epyc11: rt/current 194a63c2ad51 != hub 9108de84555b ; epyc12: rt/current 194a63c2ad51 != hub 9108de84555b ; epyc9: rt/current 194a63c2ad51 != hub 9108de84555b
- 2026-11-25 20:26 PST DIED [LEC-AUTOFILL] ot-run oth-ubuntu-1391551-1795664754 on outgoing-giraffe: rc=1 after 2434 s, ended 04:26:25, log /srv/opentallas-scratch2/claude/LEC-AUTOFILL/r/hc3xl_d5fde_l2/otrun.log, cmd: --crit --hosts epyc8 --mem 64 --threads 8 --disk 4 --dir /srv/opentallas-scratch2/claude/LEC-AUTOFILL/r/hc3xl_d5fde_l2 -- /srv/opentallas-sc | class=NO-PATTERN cause=rc=1
- 2026-11-25 20:27 PST ALERT [FLEET-OPS-R -> COORD] lane quota: kv-own-hub-r2 on intel1 wrote 53 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-25 20:27 PST ALERT [FLEET-OPS-R -> COORD] lane quota: kv-pv-estrip on intel1 wrote 53 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-25 20:28 PST ALERT [FLEET-OPS-R -> CLEAN-AGGR; cc COORD] lane quota: kw45 on intel1 wrote 68 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); CLEAN-AGGR prunes superseded event trees and replicas no live or queued row references
- 2026-11-25 20:29 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-103): 1 event(s): coll_n LAUNCHED (kw-qwenco-colln-1-67373)
- 2026-11-25 20:31 PST CANCELLED [FLEET-WATCH-1015 -> QC-SLECTL-PILE] UNSIGNABLE watchdog cancelled 1 job(s) (>3 h, measured unable to sign; ot-run --cancel --reason design): epyc12 oth-ubuntu-218974-1795636608 sle_ctl (tt_setup_keep.log latest setup WNS -408.59 ps (< -300, gate TT >= -42); job age 8.5 h > 3 h; NOTICE to QC-SLECTL-PILE 20; he job's scope; per-host '0 scope(s)' lines above mean nothing was left to sto
- 2026-11-25 20:31 PST RENDER [SMELL-WATCH -> FP-CONVERGE-QC, QC-GLUE-IMAGES; cc QC-ALLFIX] 1 checkpoint render(s) started: native59 GRT on epyc12: epyc12:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-GLUE-IMAGES/native59_1125013719/gen/native59/vis_review/grt-1126-0430 (floorplan.png, density.png, SMELL.txt with the GRT per-layer overflow, writt
- 2026-11-25 20:31 PST RENDER [SMELL-WATCH -> FP-CONVERGE-S81, S81-ALLFIX-INT; cc S81-ALLFIX-INT] 1 checkpoint render(s) started: col_h10_r2__t1 GRT on epyc9: epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_r2__t1__cl1f5d6c2a__pvec003743_1124152854/gen/col_h10_r2__t1__cl1f5d6c2a__pvec003743/vis_review/grt-1126-0430 (floorplan.png, density.png, SME
- 2026-11-25 20:30 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 12 flagged of 175 containers {'UNSIGNABLE': 5, 'NO-PROGRESS': 3, 'GRT-LABEL': 4, 'YOUNG': 102, 'NO-DATA': 34, 'KEEP': 1, 'PROGRESS': 26}; full table lanes/NOPROG-TABLE.md; flagged: epyc12 sle_ctl postcts_gate_FF [UNSIGNABLE: tt_setup_keep.log latest setup WNS -408.59 ps (< -300, gate ] UNSIGNABLE (hub: ot-run --ca; epyc8 slw_fe_v1 5_2_route [N
- 2026-11-25 20:35 PST DIED [LEC-AUTOFILL] ot-run oth-ubuntu-1391743-1795664754 on outgoing-giraffe: rc=1 after 2959 s, ended 04:35:11, log /srv/opentallas-scratch2/claude/LEC-AUTOFILL/r/hc3xl_d5fde_l5/otrun.log, cmd: --crit --hosts epyc8 --mem 64 --threads 8 --disk 4 --dir /srv/opentallas-scratch2/claude/LEC-AUTOFILL/r/hc3xl_d5fde_l5 -- /srv/opentallas-sc | class=NO-PATTERN cause=rc=1
- 2026-11-25 20:41 PST DIED [KV-ALLFIX] ot-run oth-ubuntu-573497-1795666470 on tolerant-swine: rc=1 after 1614 s, ended 20:41:20, log /home/ubuntu/tmp/kvallfix/r8_cut2100_1125/prep.otrun.log, cmd: --mem 96 --threads 10 --hosts epyc12 --priority die --dir /srv/opentallas-scratch2/claude/kv-allfix/a5t9/r8_cut2100_1125 -- bash /srv/openta | class=CHECKER-RC cause=KV_R8_PRE_WHOLE rc=0 PLAN-GATE-PRE PASS tree=/srv/opental
- 2026-11-25 20:42 PST DRIFT [MERGE-QUEUE -> COORD; cc ADMIT-TUNE-1, KIT-OPS-5] live tree differs from its recorded main sha (1 new): epyc11: manifest check failed. Any live fix must land as a branch + COORD APPROVED; the merge queue lands it and ot-tools-sync deploys it.

