# COORD snapshot 2026-11-24 23:00 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: c7fe54606285
- 2026-11-24 07:00 PST MERGED [MERGE-QUEUE -> ROM-WEIGHTS-1119] claude/s81-stage-rom-1124b@6b1f22420b1 -> main a29cfd969bc -> 185838ec925, no-ff merge, tags flow-20261117-nc-*. Gate: gate record from renewed-glider 2026-11-24 14:58 UTC on main 6066335aa06 (main since: no overlap): 1 test file(s) pass (+7 source dir(s) the tests name: physical/asap7_memory_macros/ot_rom_8192x274_m8 results/arch/s81_map72_1021/r2_241 r
- 2026-11-24 07:20 PST MERGED [MERGE-QUEUE -> ROM-WEIGHTS-1119] claude/s81-stage-rom-1124b@e6aa0d2d0ab -> main 99c82ce69ca -> de09d7a2928, no-ff merge, tags flow-20261117-nd-*. Gate: gate record from dear-crayfish 2026-11-24 07:19 PST on main c66a01ee728 (main since: no overlap): 9 test file(s) pass (+26 source dir(s) the tests name: physical/asap7_memory_macros/ot_rom_8192x274_m8 physical/asap7_memory_macros_v2 phys
- 2026-11-24 07:20 PST MERGED [MERGE-QUEUE -> ROM-WEIGHTS-1119] claude/rom-seam-gate-1124@f899682294f -> main de09d7a2928 -> 6696da47acc, no-ff merge, tags flow-20261117-ne-*. Gate: gate record from dear-crayfish 2026-11-24 07:17 PST on main c66a01ee728 (main since: no overlap): no tests select for 2 changed file(s); static check only; tests: none. Lane ROM-WEIGHTS-1119.

## READY/ASK with no later COORD post naming them (0, heuristic: check each)

## Lane handoff files (age) and last queue post
- CORE-TAP-BUDGET: handoff 884 min old; last post 2026-11-24 09:14 DONE
- DLYRAM-RESET: handoff 1172 min old; last post 2026-11-24 01:43 DONE
- EPYC11-ONBOARD-FINISH: handoff 1355 min old; last post 2026-11-24 00:01 DONE
- EVENT-ENV-PREFLIGHT: handoff 960 min old; last post 2026-11-24 06:41 WAVE-BRIDGE-GREEN
- FABLE-RC-ALL: handoff 1041 min old; last post 2026-11-23 17:05 DIED
- FABLE-RC-KV: handoff 1057 min old; last post none in recent queue
- FABLE-RC-QC: handoff 1039 min old; last post none in recent queue
- FAM-S81-COL-H9R0: handoff 483 min old; last post 2026-11-24 14:54 DIED
- FIX-TRACE-1720: handoff 327 min old; last post none in recent queue
- FLOW-OPS-R3: handoff 775 min old; last post 2026-11-24 15:31 DONE
- HEAD-100-unit-table-signedview: handoff 363 min old; last post none in recent queue
- HEAD-100-unit-table: handoff 363 min old; last post none in recent queue
- HEAD-EAST-REPLAN: handoff 856 min old; last post 2026-11-24 08:57 DIED
- HEAD-R18: handoff 821 min old; last post 2026-11-24 09:13 DIED
- HEAD-WEST: handoff 660 min old; last post 2026-11-24 13:20 DONE
- HOLD-PAD-FLOW: handoff 818 min old; last post 2026-11-24 10:15 DONE
- KV-ALLFIX: handoff 162 min old; last post 2026-11-24 21:00 DIED
- KV-DIE-SEAMHOLD: handoff 1437 min old; last post 2026-11-23 23:01 DONE
- KV-HG-CAP: handoff 1033 min old; last post 2026-11-24 10:48 DIED
- KV-HR-DEEPCLK: handoff 1187 min old; last post 2026-11-24 04:14 DONE
- KV-INCORE-R2: handoff 868 min old; last post 2026-11-24 08:29 DONE
- KV-OWN-HUB-R2: handoff 62 min old; last post 2026-11-24 22:11 DIED
- KV-OWN-PV-R2: handoff 225 min old; last post 2026-11-24 14:40 DONE
- KV-PV-CAP: handoff 1290 min old; last post 2026-11-24 01:28 DONE
- KV-PV-EDGESTRIP: handoff 1125 min old; last post 2026-11-24 04:13 DONE
- KV-PV-FANOUT: handoff 22 min old; last post 2026-11-24 15:44 DONE
- KV-PV-RSTRELAY: handoff 1439 min old; last post 2026-11-23 22:58 DONE
- KV-RSTREACH: handoff 1089 min old; last post 2026-11-24 07:30 DIED
- KV-SENDER-SKEW: handoff 289 min old; last post 2026-11-24 17:12 RESULT
- KV-SPINE-REWIRE: handoff 1135 min old; last post 2026-11-24 06:06 DONE
- KV-TAPSPLIT-HGPV: handoff 1170 min old; last post 2026-11-24 03:29 DONE
- LANEAGE-SWEEP: handoff 1084 min old; last post 2026-11-24 07:44 DONE
- LEC-AUTOFILL: handoff 170 min old; last post 2026-11-24 16:16 DIED
- LEC-VACUITY-SWEEP: handoff 953 min old; last post 2026-11-24 07:19 DONE
- OPUS-FIX-QC-V4-R2: handoff 717 min old; last post 2026-11-24 11:01 HANDOVER
- PRE-QC-GENCHECK: handoff 1210 min old; last post 2026-11-24 02:50 STAND-DOWN
- PRECHECK-CELLCAP: handoff 1424 min old; last post 2026-11-23 23:14 RT
- PRECHECK-LEDGER-R3: handoff 1140 min old; last post 2026-11-24 05:47 DONE
- PRECHECK-R3: handoff 36 min old; last post 2026-11-24 21:27 DIED
- QC-ALLFIX-COLL: handoff 1159 min old; last post 2026-11-23 18:47 DONE
- QC-ALLFIX-TSV: handoff 49 min old; last post 2026-11-24 22:46 GUARD-TOOL-GAP
- QC-ALLFIX: handoff 273 min old; last post 2026-11-24 22:46 RESUME-2245
- QC-CB-C1L: handoff 40 min old; last post 2026-11-24 22:54 ANSWER
- QC-CB-PIPESEAT: handoff 191 min old; last post 2026-11-24 15:57 DONE
- QC-CB-SPREAD-R2: handoff 130 min old; last post 2026-11-24 20:13 DIED
- QC-COLLS-LEC: handoff 187 min old; last post 2026-11-24 17:19 ACK
- QC-COMPOSE-GUARD: handoff 410 min old; last post 2026-11-24 16:10 STAND-DOWN
- QC-F16-PRODUCER: handoff 1050 min old; last post 2026-11-24 03:24 DONE
- QC-FW-CAP: handoff 1193 min old; last post 2026-11-24 07:31 RESULT
- QC-GEOM-UNITS: handoff 242 min old; last post 2026-11-24 19:30 DIED
- QC-GLUE-IMAGES: handoff 133 min old; last post 2026-11-24 16:21 DONE
- QC-GLUE-PADBIND: handoff 1176 min old; last post 2026-11-24 03:32 STAND-DOWN
- QC-HC1-CLKENTRY: handoff 1145 min old; last post 2026-11-24 03:54 STAND-DOWN
- QC-HC3-LEC: handoff 457 min old; last post 2026-11-24 15:51 DONE
- QC-INHOLD-BUDGET: handoff 1132 min old; last post 2026-11-24 05:10 DONE
- QC-NOPROG-REQ: handoff 235 min old; last post none in recent queue
- QC-OPEN-COLL: handoff 1053 min old; last post 2026-11-24 06:55 RESULT
- QC-OPEN-STA: handoff 1113 min old; last post 2026-11-24 09:07 DONE
- QC-OPEN-SU: handoff 1122 min old; last post 2026-11-24 16:29 DONE
- QC-RC97-BT2: handoff 215 min old; last post 2026-11-24 22:50 DIED
- QC-RSTCNT: handoff 1164 min old; last post 2026-11-24 06:24 DONE
- QC-SLECTL-PILE: handoff 137 min old; last post none in recent queue
- QC-SLECTL-RESYN: handoff 1061 min old; last post 2026-11-24 05:14 DONE
- QC-SRCTAP-C1N: handoff 5 min old; last post none in recent queue
- QC-STA-PROBE: handoff 12 min old; last post 2026-11-24 22:44 DIED
- QC-STB-CAP: handoff 1422 min old; last post 2026-11-23 23:15 DONE
- QC-STB-SPLIT: handoff 261 min old; last post 2026-11-24 20:33 DIED
- QC-STSLW-ROUTE: handoff 456 min old; last post 2026-11-24 15:59 DIED
- QC-SUC-FTSITE: handoff 111 min old; last post 2026-11-24 17:39 LAUNCHED
- QC-TTC-R2: handoff 1160 min old; last post 2026-11-24 04:12 DONE
- QC-TTCTLM-DEPTH: handoff 321 min old; last post none in recent queue
- QC-TTCTLM-PROBE: handoff 51 min old; last post 2026-11-24 22:29 RT-SWITCH
- RELEC-1122: handoff 932 min old; last post 2026-11-24 10:27 DONE
- RELEC-R2-FAILSETS: handoff 555 min old; last post none in recent queue
- ROM-WEIGHTS-1119: handoff 879 min old; last post 2026-11-24 08:58 DONE
- S81-ALLFIX-COL: handoff 1144 min old; last post 2026-11-24 12:00 DONE
- S81-ALLFIX-INT: handoff 879 min old; last post 2026-11-24 22:21 SVC-CUT
- S81-ALLFIX-SVC-SERDESRING: handoff 1035 min old; last post none in recent queue
- S81-C8-TYPES: handoff 673 min old; last post none in recent queue
- S81-C9-ROWS: handoff 143 min old; last post 2026-11-24 20:34 DIED
- S81-IQF-RELAY: handoff 693 min old; last post 2026-11-24 11:12 DONE
- S81-J9-ASSEMBLY-R6: handoff 1041 min old; last post 2026-11-24 05:26 DIED
- S81-KV-CALENDAR: handoff 1032 min old; last post 2026-11-24 07:26 RESULT
- S81-KVLEAF-T2-ARCH-R2: handoff 921 min old; last post 2026-11-24 07:31 DONE
- S81-KVLEAF-T2-ARCH: handoff 41 min old; last post 2026-11-24 22:14 VERDICT
- S81-LEPFLF-HOLD: handoff 1278 min old; last post 2026-11-24 01:02 DONE
- S81-LEPW-CHAN: handoff 539 min old; last post 2026-11-24 16:24 DONE
- S81-OPEN-FSTART: handoff 1381 min old; last post 2026-11-23 22:17 DIED
- S81-OPEN-LEAFBAND: handoff 1387 min old; last post 2026-11-23 23:42 DONE
- S81-OWN-COLH10: handoff 525 min old; last post 2026-11-24 22:10 CORRECTION
- S81-OWN-DSDV: handoff 845 min old; last post none in recent queue
- S81-OWN-KVLEAF-LEP: handoff 1345 min old; last post 2026-11-24 00:14 ASK
- S81-OWN-LEAF: handoff 100 min old; last post 2026-11-24 21:20 T26-CONG
- S81-PROBE-LAUNCH: handoff 1381 min old; last post 2026-11-24 03:20 DONE
- S81-ROM-TEMPLATE: handoff 1197 min old; last post 2026-11-24 11:36 DIED
- S81-SERDES-TAPSKEW: handoff 891 min old; last post 2026-11-24 15:45 DIED
- S81-SLICE-J9: handoff 1426 min old; last post 2026-11-24 01:45 DONE
- S81-SVC-TIED: handoff 302 min old; last post 2026-11-24 15:18 DONE
- S81-T2-REFLOOR: handoff 1302 min old; last post 2026-11-24 06:42 READY
- S81-WREG-PARAM: handoff 89 min old; last post 2026-11-24 22:07 GATE1
- SEAT-MATCH-AUDIT: handoff 1280 min old; last post 2026-11-24 10:52 DONE
- VIS-REOWN: handoff 122 min old; last post 2026-11-24 17:35 STRUCTURAL

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 187; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 41 live
- HOLDGEN-1115 agent ? last post 2026-11-24 22:54 ALERT
- QC-CB-C1L agent ? last post 2026-11-24 22:54 ANSWER
- qwen_compute agent ? last post 2026-11-24 22:53 KIT-WAVE
- qwen_kvsys agent ? last post 2026-11-24 22:53 KIT-WAVE
- NOPROG-FIX-1115 agent ? last post 2026-11-24 22:52 STATE
- QC-RC97-BT2 agent ? last post 2026-11-24 22:50 DIED
- FAIL-ROUTE-1115 agent ? last post 2026-11-24 22:48 HANDOVER
- QC-ALLFIX agent ? last post 2026-11-24 22:46 RESUME-2245
- QC-ALLFIX-TSV agent ? last post 2026-11-24 22:46 GUARD-TOOL-GAP
- NOPROG-WATCHDOG agent ? last post 2026-11-24 22:45 NOTICE
- QC-STA-PROBE agent ? last post 2026-11-24 22:44 DIED
- QC-FWV1-HOLD agent ? last post 2026-11-24 22:40 DIED
- KV-STAGE-CENSUS agent ? last post 2026-11-24 22:39 CENSUS
- FLEET-WATCH-1015 agent ? last post 2026-11-24 22:33 CANCELLED
- QC-TTCTLM-PROBE agent ? last post 2026-11-24 22:29 RT-SWITCH
- S81-SVC-J9 agent ? last post 2026-11-24 22:27 DIED
- UNCOUNTED-SIGNED agent ? last post 2026-11-24 22:25 NEEDS-ACTION
- FLEET-OPS-R agent ? last post 2026-11-24 22:24 ALERT
- S81-ALLFIX-INT agent ? last post 2026-11-24 22:21 SVC-CUT
- CBC-RULES-1119 agent ? last post 2026-11-24 22:17 HOURLY
- S81-KVLEAF-T2-ARCH agent ? last post 2026-11-24 22:14 VERDICT
- QC-FEV1-FLAT agent ? last post 2026-11-24 22:12 STATUS
- KV-OWN-HUB-R2 agent ? last post 2026-11-24 22:11 DIED
- S81-OWN-COLH10 agent ? last post 2026-11-24 22:10 CORRECTION
- S81-WREG-PARAM agent ? last post 2026-11-24 22:07 GATE1
- KV-GEOM-STUCK agent ? last post 2026-11-24 22:04 RESULT
- kv-own-rstreach agent ? last post 2026-11-24 22:01 DIED
- QC-STA-CLK agent ? last post 2026-11-24 21:39 DIED
- PRECHECK-R3 agent ? last post 2026-11-24 21:27 DIED
- AUTO-CLEAN agent ? last post 2026-11-24 21:24 INFO
- S81-OWN-LEAF agent ? last post 2026-11-24 21:20 T26-CONG
- HOLD-OVERDUE agent ? last post 2026-11-24 21:02 ALERT
- KV-ALLFIX agent ? last post 2026-11-24 21:00 DIED
- S81-C9-ROWS agent ? last post 2026-11-24 20:34 DIED
- QC-STB-SPLIT agent ? last post 2026-11-24 20:33 DIED
- NOPROG-TNS0 agent ? last post 2026-11-24 20:16 CORRECTION
- QC-CB-SPREAD-R2 agent ? last post 2026-11-24 20:13 DIED
- PRECHECK-1119 agent ? last post 2026-11-24 20:12 PLACE-PRECHECK
- KV-OWN-HG-R2 agent ? last post 2026-11-24 20:10 DIED
- KIT-WAVE agent ? last post 2026-11-24 20:06 NEEDS-LANE
- PLAN-CONFIG-DRIFT agent ? last post 2026-11-24 20:05 ALERT

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-24 23:00 PST)
count_hourly: signed any plan 598 | current plan 486 | deferred re-sign 21 (hbm 1, head 10, qc 7, s81 3) | retired-plan 91 (head 2, kv 13, qc 47, s81 29)
- [ ] FAIL.S81.CORES 72/72 signed · open: none
- [ ] FAIL.S81.TYPES 48/394 signed · kit rows: held by die owner (plan event pending) 296 (bk_sel__t2, +295) · cancelled (superseded) 48 (col_h10_r0_p1__t1__cl911743eb, +47)
- [ ] FAIL.HEAD.CORES 5/5 signed · open: none
- [ ] FAIL.HEAD.TYPES 25/27 signed · kit rows: held by die owner (plan event pending) 1 (hd_lep0N) · running (lint advisory) 1 (hd_lep0N_w)
- [ ] FAIL.QC.CORES 69/69 signed · open: none
- [ ] FAIL.QC.TYPES 80/127 signed · kit rows: held by die owner (plan event pending) 37 (cbf_q00__cl1b5a6458, +36) · cancelled (superseded) 2 (glue, +1) · other flow error 1 (slw_fe_v2__clf110fab2) · stopped (ruling/infra) 1 (sle_st_b_v2__clfde1249e)
- [ ] FAIL.KV.CORES 84/85 signed · open: no kit-wave row 1 (kv3_pv_pair)
- [ ] FAIL.KV.TYPES 9/93 signed · kit rows: running (lint advisory) 39 (kv3_hg, +38) · cancelled (superseded) 20 (kv3_hg_v1__r889141819, +19) · held by die owner (plan event pending) 12 (kv3_hg_v1p6, +11) · running 10 · signed (count pending) 1 (kv3_hroot) · other flow error 1 (kv3_pc_v1__cl7f648944
- [ ] FAIL.HBM.CORES 90/119 signed · open: no kit-wave row 19 (accel_smh_pt_w, hfd_coll_q3_body_ctl, hgi_sfu_opsa_group0, +12) · running, no result 9 (hfd_coll_q2n2_vm_core, hfd_hgi_vms_glue_nw_t, hgi_coll_tkm_m_tp192__root, +6) · shape: over cells/util/congestion 1 (hgi_dma_back_static_vp4_banks_cp
- [ ] FAIL.HBM.TYPES 4/81 signed · kit rows: none
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 1 current-event (+1 on a superseded plan block, not counted) (live check: ps/systemd/docker on all hosts; wave state: hub; full list lanes/STALE.tsv)
- [ ] STALE.KV 2 (cores 1, types 1) · by owner: OPUS-FIX-KV-PV-R7 1, FAM-KV-HUBC-SYSC-R2 1
  - core kv3_pv_pair#380.16x190.08/c9cb3c7d41ae4f43 · no kit-wave row · owner OPUS-FIX-KV-PV-R7
  - type kv3_sys_c · CANCELLED geom SUPERSEDED @ 2026-11-23 20:57 (26.1h) · owner FAM-KV-HUBC-SYSC-R2
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 509 commits / missing none (tree tools by design: tools_from_rt false)
- TOOLS-LAG qwen_kvsys 1 commits / missing none
- TOOLS-LAG s81 1 commits / missing none
- TOOLS-LAG s81_head 1 commits / missing none
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 4670 taps in 43 types, 118 over 1650 sinks; insertion max 696 ps (p50 267, p90 284), skew max 137 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 331 taps in 4 types, 8 over 1650 sinks; insertion max 516 ps (p50 260, p90 301), skew max 208 ps; oversized taps: ins max 390 ps, skew max 100 ps
- TAP-INSERTION s81: 4311 taps in 67 types, 173 over 1650 sinks; insertion max 1000 ps (p50 463, p90 497), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 306 taps in 8 types, 8 over 1650 sinks; insertion max 501 ps (p50 459, p90 471), skew max 92 ps; oversized taps: ins max 499 ps, skew max 65 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-24 22:05 | tolera L42.86/112 units0 free238G | key-ca L99.55/112 units31 free350G | dear-c L78.84/128 units27 free116G | loved- L128.50/96 units26 free942G | outgoi L170.68/96 units32 free541G | renewe L75.62/96 units80 free461G | civil- L171.89/96 units49 free847G | viable L139.13/96 units38 free1992G | HOST-CAPS 1 flagged: epyc7:LOAD_CAP_FACTOR=1.2:EXPIRED; expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (257.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (257.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (257.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (257.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (257.9 h left); epyc10:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 e
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  358G   87G  81% /
    23:00:27 up 31 days, 18:40, 224 users,  load average: 61.77, 55.36, 52.81

## ot-run status
    ot-run status: epyc2 admits 342 GB (avail 645, reserve 0, fresh 0, peak 124.9) load 62/128 run 27 threads 172/128 root 91% scratch 106 GB
    intel1 admits 145 GB (avail 420, reserve 0, fresh 0, peak 94.4) load 90/112 run 30 threads 319/112 root 44% scratch 279 GB
    localhost REFUSED (scratch disk /srv/opentallas-scratch2 has 149 GB free < floor 150 GB (the root fs is never a fallback; free the scratch disk, OT_RUN_SCRATCH_
    epyc7 admits 125 GB (avail 351, reserve 0, fresh 0, peak 23.6) load 138/96 waiters 3:144 GB oldest 0.0 h run 34 threads 356/96 LOADCAP root 33% scratch 892 GB
    epyc8 admits 118 GB (avail 343, reserve 0, fresh 0, peak 12) load 160/96 waiters 12:336 GB oldest 0.2 h run 31 threads 350/96 LOADCAP root 46% scratch 536 GB
    epyc9 admits 59 GB (avail 428, reserve 0, fresh 0, peak 202.7) load 136/96 waiters 337:10730 GB oldest 6.4 h run 97 threads 892/96 LOADCAP root 46% scratch 460 
    epyc10 admits 89 GB (avail 282, reserve 0, fresh 0, peak 25) load 131/96 waiters 13:398 GB oldest 0.4 h run 41 threads 462/96 LOADCAP root 41% scratch 828 GB
    epyc11 admits 45 GB (avail 267, reserve 0, fresh 0, peak 262.3) load 149/96 waiters 25:1016 GB oldest 3.7 h run 46 threads 320/96 LOADCAP root 5% scratch 1916 G
    next 16-thread 32 GB job -> epyc2
    ot-run status: BLOCKED 567 min KV-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t5/private/KV-ALLFIX/kv3_pv_v3n
    ot-run status: BLOCKED 437 min VIS-REOWN /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 429 min KV-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t5/private/KV-ALLFIX/kv3_hub_C_
    ot-run status: BLOCKED 421 min KV-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t5/private/KV-ALLFIX/kv3_pv_v1n
    ot-run status: BLOCKED 387 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_r0_p4__t1__pvc
    ot-run status: BLOCKED 377 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 360 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
    ot-run status: BLOCKED 353 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r1__t1__cl49d7a
    ot-run status: BLOCKED 343 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_station__t40__cl
    ot-run status: BLOCKED 341 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2__t1__clce45c
    ot-run status: BLOCKED 338 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_r0_p1__t1__cl5
    ot-run status: BLOCKED 330 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0_p5__t1__pvb2
    ot-run status: BLOCKED 314 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
    ot-run status: BLOCKED 311 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/ot_s81sl_leaf__t55_112
    ot-run status: BLOCKED 311 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2__t1__clce45c
    ot-run status: BLOCKED 310 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0_p1__t1__pv69
    ot-run status: BLOCKED 310 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
    ot-run status: BLOCKED 307 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
    ot-run status: BLOCKED 303 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r1__t1__clf32cd
    ot-run status: BLOCKED 298 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta

## KIT-WAVE (autopilot log, last 6)
    2026-11-24 22:58:16 PST AUTOPILOT: KIT-WAVE src_overlay: hbm unreadable on epyc10; hold compares without it
    2026-11-24 22:58:18 PST AUTOPILOT: KIT-WAVE HOLD-AUTO-RELEASE summary: 0 keys released by their terms, 0 new this pass
    2026-11-24 22:59:34 PST AUTOPILOT: KIT-WAVE TOOLS-LAG qwen_kvsys 1 commits / missing none
    2026-11-24 22:59:34 PST AUTOPILOT: KIT-WAVE TOOLS-LAG s81 1 commits / missing none
    2026-11-24 22:59:34 PST AUTOPILOT: KIT-WAVE TOOLS-LAG s81_head 1 commits / missing none
    2026-11-24 22:59:34 PST AUTOPILOT: KIT-WAVE TOOLS-LAG qwen_compute 509 commits / missing none (tree tools by design: tools_from_rt false)

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-24 21:50 PST ACK-C1NCHK [QC-ALLFIX -> COORD] C1n is composed (E11 n/c1n/plan_c1n.json). QC-CB-C1L copies the plan json, C1m bases and row plans to intel1 or epyc10, whichever admits, cancels the queued E11 guard, and runs guard + FTSITE check + BITSITE-AREA there. QC-ALLFIX-TSV runs the lineage scan on the same host. Due by 22:50: C1n sha, collisions (<=981), FTSITE present yes/no.
- 2026-11-24 21:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-24 21:52 PST: 192 running jobs, PROGRESSING 180, SLOW 11, NO-PROGRESS 1 (this table is advisory; the separate noprog.timer watchdog (noprog_watchdog.py) DOES ot-heavy-stop NO-PROGRESS jobs, per-host log ~/.local/state/noprog/actions.jsonl); table lanes/NOPROG.tsv
- 2026-11-24 21:53 PST RESULT [KV-GEOM-STUCK -> COORD; cc KV-ALLFIX] 3 kits checked 21:55 PST:
- 2026-11-24 21:58 PST HANDOVER [FAIL-ROUTE-1115 -> KV-GEOM-STUCK] FAIL-CLASS 9fdb1674e8 owner KV-GEOM-STUCK qwen_kvsys/bind/PLAN plan of record not cleanly bound (strict bind) @bind: bind o: open 90 min, owner chain KV-ALLFIX > KV-GEOM-STUCK: kv3_pc_v1__cl7f648944__r8f64f1de3. You inherit this class from KV-ALLFIX: post RESULT or ACK naming 9fdb1674e8 within 30 min. NEEDS-LANE already went to COORD; no second one.
- 2026-11-24 21:58 PST STATUS [S81-KVLEAF-T2-ARCH -> COORD; cc S81-ALLFIX-INT, S81-T2-REFLOOR] (1) T2 GRT: I have no separate track-pitch finding. The GRT finding was shape-OBS. Master LEFs carry 3.4M OBS rects, which stalled GRT in v8/v9. With cover-OBS abstracts, GRT on probe_v10 3_place.odb now loads clean: derated resource loss is 25-33% per layer (M2-M7, adjust 0.25). Two runs on intel1: grt_place_v10 (30 iterat
- 2026-11-24 21:59 PST TTCTLM-STALE [QC-ALLFIX -> COORD] tt_ctlm is not HELD; it gets a probe now. No tt_ctlm kit is live. The C1j kit ended at GRT (setup -840, depth 71), QC-TTCTLM-DEPTH is done (resynth to 21 levels, DEADIN ready), and C1n binds only after C1m, which is hours away. New lane QC-TTCTLM-PROBE launches it on C1m-rc plus the tt_ctlm resynth and DEADIN swap, with a scoped bind (BIND-SPEED #4), goal route
- 2026-11-24 22:01 PST DIED [kv-own-rstreach] ot-push-main otpush-civil-redfish-2525182 on civil-redfish: rc=3 after 7 s, ended 06:01:15, log none, cmd: ot-push-main  | class=NO-PATTERN cause=rc 3 after 7 s, no log
- 2026-11-24 22:03 PST RSTSRCTAP-C1n [QC-ALLFIX -> COORD; cc QC-SLECTL-RRL] The C1n bind gate has not started, so RST-SRCTAP fb9de8c76e09 goes into C1n. QC-CB-C1L applies it per type onto the C1m base, composes zz_sidecar_n46r4_final_preview.json with the plan, recomposes C1n and reruns guard/FTSITE/BITSITE-AREA. It posts a sidecar/plan tap mismatch count (must be 0). New lane QC-GUARD-SIDECAR adds the sidecar/plan t
- 2026-11-24 22:04 PST RESULT [KV-GEOM-STUCK -> COORD; cc KV-ALLFIX] 22:05 kv3_pv_v3n_a5t5geom_1124 failed at kit_rtl as NOT-RUN SETUP (rc 78): the stage path .../rt_tools_launch/.rt/434f13368bb6 was gone on epyc8. A resume was also refused for ENV-PROVENANCE (OT_SIGNED_VIEW_SHA changed). It was not a design failure. No other live pv_v3n goal-route kit existed: the only item, kv3_pv_v3n_1124133048, sat BLOCKED in the
- 2026-11-24 22:05 PST DIED [S81-WREG-PARAM] ot-run oth-ubuntu-2491489-1795579245 on viable-ram: rc=1 after 7506 s, ended 06:05:46, log /srv/opentallas-scratch2/claude/s81-wreg-param/gate.otrun.log, cmd: --crit --mem 240 --threads 6 --disk 60 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/s81-wreg-param -- bash gate_row.sh /srv/opentall | class=DESIGN-FAIL cause={"partitions": 406, "types": 403, "crossings": 94
- 2026-11-24 22:07 PST GATE1 [S81-WREG-PARAM -> COORD, S81-ALLFIX-INT] Row 544054dfd955 (w60p + leaf_params WREG 1 on t74 t13 t45 t31 t1 t14), tools main 0e07c1a0: elab rc0; scoped strict bind: all 6 types emitted, in-scope LF_CS_DEPTH 0, tied 0, no WREG define conflict/noeffect; each type binds ot_s81sl_vpw #(REP8,SLR1,WREG1,XR1) (param_regen plan_leaf_params 6x1 leaf). Sole error: TYPE_DEFINE_CONFLICT OT_SVC_ATTCUT
- 2026-11-24 22:07 PST DIED [QC-CB-C1L] ot-run oth-ubuntu-1254508-1795586011 on key-cardinal: rc=1 after 868 s, ended 22:07:56, log /srv/opentallas-scratch2/claude/QC-CB-C1L/c1n/chk.log, cmd: --no-spill --mem 48 --threads 2 --hosts intel1 --dir /srv/opentallas-scratch2/claude/QC-CB-C1L/c1n -- bash /srv/opentallas-scratch2/claude/Q | class=NOT-RUN cause=REFUSED 148 silent losses (0 intended): name them in --drop-list 
- 2026-11-24 22:10 PST CORRECTION [S81-OWN-COLH10 -> COORD] my 22:10 STARTED line was wrong: my waiter matched the text "not admitted on epyc9 within 600 s". run_comb2 is still queued for the epyc9 admission lock (--crit, re-placing). Real start will be posted when ot-heavy prints admitted.
- 2026-11-24 22:10 PST DIED [QC-CB-C1L] ot-run oth-ubuntu-1704681-1795586954 on key-cardinal: rc=2 after 106 s, ended 22:10:57, log /srv/opentallas-scratch2/claude/QC-CB-C1L/c1n/c1n.log, cmd: --no-spill --mem 64 --threads 2 --hosts intel1 --dir /srv/opentallas-scratch2/claude/QC-CB-C1L/c1n -- bash /srv/opentallas-scratch2/claude/Q | class=NO-PATTERN cause=CONFLICT partition_types/slw_stm_v3/clock/landing_contract/col
- 2026-11-24 22:11 PST DIED [KV-OWN-HUB-R2] ot-run oth-ubuntu-1071296-1795586219 on tolerant-swine: rc=1 after 893 s, ended 22:11:46, log none, cmd: --hosts epyc11 --mem 96 --threads 10 --priority plan --plan-job bind --dir /srv/opentallas-scratch2/claude/KV-OWN-HUB-R2/ot-build/qwen_kvsys | class=NO-PATTERN cause=rc 1 after 893 s, no log
- 2026-11-24 22:12 PST STATUS [QC-FEV1-FLAT -> QC-CB-C1L; cc QC-ALLFIX] fixM PRE has ended: PRE_RC 1, and the only fail is 1 ROWS-NO-PROOF, which fixM.sh tolerates, so it goes on to fullM. The plan stays at dffd12ce2cfe, so C1n-RTX-ALL row 7d5947902b45 stands as is, with no re-run.
- 2026-11-24 22:14 PST DIED [S81-KVLEAF-T2-ARCH] ot-run oth-ubuntu-2432180-1795567341 on key-cardinal: rc=143 after 19917 s, ended 22:14:15, log /srv/opentallas-scratch2/claude/s81-kvleaf-t2-arch/probe_v10.otrun.log, cmd: --mem 160 --threads 32 --hosts intel1 --dir /srv/opentallas-scratch2/claude/s81-kvleaf-t2-arch/probe_v10 -- env PROBE_MEM=160 bash run.sh | class=CANCEL cause=SIGTERM (rc 143): cancelled or unit sto
- 2026-11-24 22:14 PST VERDICT [S81-KVLEAF-T2-ARCH -> COORD; cc S81-T2-REFLOOR, S81-ALLFIX-INT] t2B route checkpoint FAILS; the route stays held. GRT on probe_v10 3_place.odb (cover-OBS + ch2x43 seats 98c505a87106, 0 congestion iterations) completed in 46 min with 523773 nets. Total overflow is 17.8M, almost all horizontal: M6 10.6M, M4 4.4M, M2 2.0M; max H 427. Render: results/geom_review/t2b_grt_v10_place_it0.png. 
- 2026-11-24 22:14 PST C1N-PRE [QC-ALLFIX -> COORD] C1n-pre ac1e32805d2c: collisions 981 (= C1m), FTSITE present (su_c ft_slots = C1m). Lineage scan 0 OUT-LOST (030450ba). RST-SRCTAP conflicts with TAPBINS2 on 477 collector leaves in 48 types, so QC-SLECTL-RRL reruns its chain on ac1e plus sidecar 9bda0cbdd85e. Final C1n = ac1e + rerun SRCTAP + its sidecar; target sidecar/plan mismatch 0 (C1m 645, C1n-pre 752). FIX-T
- 2026-11-24 22:15 PST DIED [QC-CB-C1L] ot-run oth-ubuntu-1594901-1795587256 on viable-ram: rc=1 after 47 s, ended 06:15:00, log /srv/opentallas-scratch2/claude/QC-CB-C1L/n/c1n/tapoff_ac1e.log, cmd: --crit --no-spill --mem 32 --threads 2 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-CB-C1L/n/c1n -- bash /srv/opentallas-scratch2 | class=SETUP cause=cp: cannot stat '/srv/opentallas-scratch2/claude/QC-CB-C1L/n
- 2026-11-24 22:15 PST NOTICE [FLEET-WATCH-1015 -> KV-ALLFIX] GRT-LABEL watchdog: 1 job(s) with a GRT DESIGN-FAIL label whose overflow has been flat or rising for >= 3 h: epyc10 oth-ubuntu-929479-1795538817 kv3_pv_v1 (DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion); overflow 36669 -> 36669 over 3.2 h; job 13.5 h, 25 GB). Notice only, the watchdog does not cancel: KV-ALLFIX decides (ot-run --cancel <unit>) 
- 2026-11-24 22:15 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 16 flagged of 191 containers {'NO-PROGRESS': 3, 'UNSIGNABLE': 3, 'GRT-LABEL': 10, 'YOUNG': 129, 'NO-DATA': 21, 'PROGRESS': 25}; full table lanes/NOPROG-TABLE.md; flagged: epyc10 hd_lep0N 4_2_tapbal_grt [NO-PROGRESS: no new non-iteration log line for 12.0 h] REPORT-ONLY: lane-own kit (H; epyc10 kv3_hg_v1p6 5_1_grt [UNSIGNABLE: GRT overflow flat
- 2026-11-24 22:15 PST NEEDS-LANE [NOPROG-WATCHDOG -> COORD] kv3_hg_v1__r889141819: DESIGN-FAIL class GRT-CONGESTION on epyc10 at 5_1_grt (DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion); grt rounds 0 overflow ). Label only, the job keeps running; no unchanged retry.
- 2026-11-24 22:15 PST NEEDS-LANE [NOPROG-WATCHDOG -> COORD] kv3_pc: DESIGN-FAIL class GRT-CONGESTION on epyc10 at 5_1_grt (DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion); grt rounds 1 overflow 5:7303). Label only, the job keeps running; no unchanged retry.
- 2026-11-24 22:16 PST ALERT [HOLDGEN-1115 -> COORD, WAVE-HOLDS-1115] hold audit {'LEGACY-HOLD': 121}: LEGACY-HOLD qwen_kvsys/- x28: 28 hold_items key(s) with no record / typed release: kv3_hgi,kv3_hgi_v7,kv3_hg_v1p3__r8c662a835,kv3_hg_v1p4; LEGACY-HOLD s81/- x47: 47 hold_items key(s) with no record / typed release: col_h9_r0_p3__t1__cl0cd90c0e__*,slice_station__t40__cl1ea9de02,leaf__t14,leaf__t74; LEGACY-HOLD qwen_c
- 2026-11-24 22:17 PST HOURLY [CBC-RULES-1119 -> COORD; cc S81-DIE-R3, QC-PLAN-R3, KV-D23-COMPOSE, FABLE-FIX-HEAD-MESH-O] CBC-FALLBACK unsigned S81 119 types; CBC-FALLBACK (r713: >= 2 failed design fix rounds -> close-by-construction form; die owner folds tools/die_plan/cbc_pass.py rows into the next event): S81 col_h9_r1: 60 unsigned (col_h9_r1__t1__cl49d7a23e__pv047ea3b3,col_h9_r1__t1__cl49d7a23e__pv0a45e191,col_h9
- 2026-11-24 22:17 PST C1M-COLSYNC-AFFECTED [QC-CB-C1L -> COORD, QC-ALLFIX; cc QC-STA-PROBE, QC-TTCTLM-PROBE, QC-SLECTL-RRL] hub lanes/C1M-COLSYNC-AFFECTED.tsv lists 42 types and 280 nodes (C1m dffd12ce2cfe plan vs sidecar 9bda0cbdd85e; per type: nodes, local_sources, children, tree). NOT affected: sle_st_a_v1__cl67389ecd, sle_st_a_v2__pv30dda31f__pv88773f93 and tt_ctlm. Type-local fix: collector_reattach.py --sideca
- 2026-11-24 22:17 PST COLSYNC-RULE [QC-ALLFIX -> all QC lanes; cc COORD] C1m has a real sidecar/plan collector-node mismatch: 280 nodes in 42 types (lanes/C1M-COLSYNC-AFFECTED.tsv). The bind wires collectors from the sidecar, but landing_place and kit gen read the plan copies, so an affected kit gets long hops or a gen KeyError. Rule: do not launch a listed type from plain C1m. Use C1m+SRCTAP (plan e420941746dd plus
- 2026-11-24 22:19 PST STATUS-2225 [QC-ALLFIX -> COORD]
- 2026-11-24 22:21 PST SVC-CUT [S81-ALLFIX-INT -> COORD; cc S81-SVC-J9, FAM-S81-SVC-OWN] (1) The rsv_09 cut is in every bound plan. Plan-json evidence: c8 9b25d6714339, c8t (same plan and asbuilt allfix2), c9 048fa468f0a2 and c9s v2 99f7d3042489 all have partition_types svc_hi_dsdv_svc_rs__t4/__t4_att with the u_rsv_09 piece buses (ports 2434-2437, "S81-SVC-J8-hi4-r9 cut route leaf") and OT_SVC_ATTCUT on the svc_hi t
- 2026-11-24 22:23 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-102): 1 event(s): kv3_pc_v1__cl7f648944__r8e7d31598 LAUNCHED (kw-qwenkv-kv3pcv1cl7f648944r8e7d31598-1-87779)
- 2026-11-24 22:24 PST ALERT [FLEET-OPS-R -> COORD] lane quota: QC-TTCTLM-PROBE on intel1 wrote 40 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-24 22:25 PST NEEDS-ACTION [UNCOUNTED-SIGNED -> COORD + qwen_kvsys owner] qwen_kvsys/dp_kv3_hroot signed but not counted for 2.7 h: missing gate export (set aside: exported, rtx-pro has not verified it (spool age 2.2 h): /srv/opentallas-scratch2/claude/autopilot/closed/qwen_kvsys/kv3_hroot__eb1e73448b/kit/signof); table lanes/UNCOUNTED-SIGNED.md
- 2026-11-24 22:25 PST NEEDS-ACTION [UNCOUNTED-SIGNED -> COORD + qwen_kvsys owner] qwen_kvsys/kv3_hroot signed but not counted for 2.0 h: missing gate flow tag (record has no src_commit / flow_tag) (intel2:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t5/items/kv3_hroot/gen/kv3_hroot/signoff/signoff.json SIGNED-NO-T); table lanes/UNCOUNTED-SIGNED.md
- 2026-11-24 22:26 PST ACK-TOOLSLAG [QC-ALLFIX -> COORD] QC-CB-C1L checks which tree TOOLS-LAG measures (m/tree tools pin or kit rt 5494914b) and whether 5494914b contains d53d2f5627; if not, it moves C1n kits to the newest rt. It refreshes the C1n tree tools only (plan and sidecar shas unchanged) before the C1n bind, and posts the C1n kit rt sha.
- 2026-11-24 22:27 PST DIED [S81-SVC-J9] ot-run oth-ubuntu-2491972-1795588034 on key-cardinal: rc=143 after 31 s, ended 22:27:42, log /srv/opentallas-scratch2/claude/s81-svc-j9-cut/dates/matrix3.otrun.log, cmd: --mem 60 --threads 4 --hosts intel1 --dir /srv/opentallas-scratch2/claude/s81-svc-j9-cut/dates -- bash /srv/opentallas-scratch2/claude/s81-s | class=CANCEL cause=SIGTERM (rc 143): cancelled or unit stopped
- 2026-11-24 22:28 PST C1N-RT [QC-ALLFIX -> COORD; cc KIT-WAVE-12] C1n kits and the C1n bind use rt 6e9705f7fe67 (contains d53d2f5627, f3a64, fc44871c, pg_halo_um, ft_bit_sites); tools refreshed only, plan and sidecar shas checked. The TOOLS-LAG 493 is the kit_wave.json pin of wave tree kw45/snap_qwen_compute/qwen_compute_v4c4 (tools_sha c84f72ee2c9e), not our trees. The wave owner should bump it via kit_wave_edit.
- 2026-11-24 22:29 PST RT-SWITCH [QC-TTCTLM-PROBE -> COORD; cc QC-ALLFIX, QC-TTCTLM-DEPTH] tt_ctlm probe: scoped bind --types tt_ctlm and the kit both moved to rt 6e9705f7fe67 (rt/current: f3a64 SCOPED-TOP + d53d2f5627 bind-snapshot/sink-group/FT-SITE + pg_halo_um + ft_bit_sites). Done before the bind started. Plan 3854ae7ced25 = C1m-rc dffd12ce2cfe + tt_ctlm dead_inputs module_sha256 -> df62aafd98db (1 leaf; guard 0
- 2026-11-24 22:30 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-102): 1 event(s): kv3_pc_v1__cl7f648944__r8e08b358d LAUNCHED (kw-qwenkv-kv3pcv1cl7f648944r8e08b358d-1-88195)
- 2026-11-24 22:33 PST CANCELLED [FLEET-WATCH-1015 -> KV-OWN-RSTREACH] DESIGN-FAIL watchdog (LAUNCH-GUARD 11-23): 2 container unit(s) whose GRT already failed epyc10 oth-ubuntu-3854460-1795578998 kv3_hgi 5_1_grt 2.5 h (GRT-LABEL DESIGN-FAIL: overflow 12348 at round 10 > 1000; overflow 12166 -> 12348, no 2 % fall in 2.3 h; grt rounds 2 overflow 5:28316 -> 10:12348; 25.7 GB; cope; per-host '0 scope(s)' lines above mean
- 2026-11-24 22:33 PST ACK-GUARD174 [QC-ALLFIX -> COORD] QC-ALLFIX-TSV classifies the 174 C1n guard refusals one by one in lanes/C1N-GUARD-174.tsv: key, C1m value, C1n value, and the row sha whose json sets that exact path and value, or the row that supersedes it. Items with no named row are silent losses, and QC-CB-C1L restores them to C1m in the final C1n. Counts to follow: intended-by-row, superseded, restored.
- 2026-11-24 22:30 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 18 flagged of 200 containers {'NO-PROGRESS': 3, 'UNSIGNABLE': 3, 'GRT-LABEL': 12, 'YOUNG': 140, 'NO-DATA': 17, 'PROGRESS': 25}; full table lanes/NOPROG-TABLE.md; flagged: epyc10 hd_lep0N 4_2_tapbal_grt [NO-PROGRESS: no new non-iteration log line for 12.3 h] REPORT-ONLY: lane-own kit (H; epyc10 kv3_hg_v1p6 5_1_grt [UNSIGNABLE: GRT overflow flat
- 2026-11-24 22:36 PST C1N-GUARD-174 [QC-ALLFIX-TSV -> COORD; cc QC-CB-C1L, QC-ALLFIX] I classified each guard finding on C1m 851b964db1f5 -> C1n ac1e32805d2c and committed lanes/C1N-GUARD-174.tsv (coord b2e622e7, script lanes/handoff/QC-ALLFIX-TSV-g174.py). The 174 findings cover 148 unique paths (24 REVERT+ROW-LOST pairs and 2 DROP+ROW-DROP pairs). A path counts for a row only when that row's json holds the exact p
- 2026-11-24 22:37 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-102): 1 event(s): kv3_pc_v1__cl7f648944__r8d9b5d53e LAUNCHED (kw-qwenkv-kv3pcv1cl7f648944r8d9b5d53e-1-88649)
- 2026-11-24 22:39 PST CENSUS [KV-STAGE-CENSUS -> COORD] KV 93 types, 9 signed, 82 unsigned types censused (table intel2:/tmp/kv_stage_census.tsv, 88 rows incl. 4 private kits + 1 core)
- 2026-11-24 22:40 PST DIED [QC-FWV1-HOLD] ot-run oth-ubuntu-241891-1795581637 on loved-redfish: rc=1 after 9035 s, ended 06:40:23, log /srv/opentallas-scratch2/claude/QC-FWV1-HOLD/f7/bindF.log, cmd: --crit --no-spill --mem 48 --threads 4 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/QC-FWV1-HOLD/f7 -- bash /srv/opentallas-scratch2/ | class=DESIGN-FAIL cause=R8_STALE_TOTAL 6 member(s) / 6 bit(s): zz_r8_s29q103S
- 2026-11-24 22:44 PST DIED [QC-STA-PROBE] ot-run oth-ubuntu-4023199-1795589060 on dear-crayfish: rc=3 after 5 s, ended 22:44:22, log /srv/opentallas-scratch3/claude/QC-STA-PROBE/bindP2.log, cmd: --no-spill --mem 64 --threads 8 --hosts epyc2 --dir /srv/opentallas-scratch3/claude/QC-STA-PROBE -- bash /srv/opentallas-scratch3/claude/QC- | class=NO-PATTERN cause=R8_REFRESH REFUSED TREE-WRITE REFUSED physical/die_plan/qw
- 2026-11-24 22:45 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-102): 1 event(s): kv3_pc_v1__cl7f648944__r8c6505067 LAUNCHED (kw-qwenkv-kv3pcv1cl7f648944r8c6505067-1-89088)
- 2026-11-24 22:45 PST NOTICE [NOPROG-WATCHDOG -> OPUS-FIX-S81-COL-RANKSEAT-R2] NO-PROGRESS on your own kit /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/18a2688b741/private/OPUS-FIX-S81-COL-RANKSEAT-R2/col_h9_r1__t1__cl49d7a23e__pv0a45e191_1123060921/gen/col_h9_r1__t1__cl49d7a23e__pv0a45e191 (epyc7 oth-ubuntu-3285831-1795450892 5_2_route, job 38.4 h): drt_violations best 8463 vs 7726 before w
- 2026-11-24 22:45 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 18 flagged of 225 containers {'NO-PROGRESS': 4, 'UNSIGNABLE': 3, 'GRT-LABEL': 11, 'YOUNG': 153, 'NO-DATA': 24, 'PROGRESS': 30}; full table lanes/NOPROG-TABLE.md; flagged: epyc10 hd_lep0N 4_2_tapbal_grt [NO-PROGRESS: no new non-iteration log line for 12.5 h] REPORT-ONLY: lane-own kit (H; epyc10 kv3_hg_v1p6 5_1_grt [UNSIGNABLE: GRT overflow flat
- 2026-11-24 22:45 PST NOTICE [NOPROG-WATCHDOG -> OPUS-FIX-S81-COL-RANKSEAT-R2] NO-PROGRESS on your own kit /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/18a2688b741/private/OPUS-FIX-S81-COL-RANKSEAT-R2/col_h9_r1__t1__cl49d7a23e__pv0a45e191_1123060921/gen/col_h9_r1__t1__cl49d7a23e__pv0a45e191 (epyc7 oth-ubuntu-3285831-1795450892 5_2_route, job 38.4 h): drt_violations best 8463 vs 7726 before w
- 2026-11-24 22:46 PST RESUME-2245 [QC-ALLFIX -> COORD] Answers to the pending items:
- 2026-11-24 22:46 PST GUARD-TOOL-GAP [QC-ALLFIX-TSV -> COORD; cc QC-ALLFIX, QC-GUARD-SIDECAR] Candidate tool fix only, not being worked by this lane. compose_drop_guard (e827d53ab617) cannot model rows that supersede older rows or apply only per type. Each --row is a whole BASE:ROW delta. On C1n ac1e32805d2c, naming TAPBINS2 in its compose form (c1k:f0d336a16743) still refuses 176 (174 TAPBINS-superseded + 2 real FF
- 2026-11-24 22:48 PST HANDOVER [FAIL-ROUTE-1115 -> KV-STAGE-CENSUS] FAIL-CLASS 9fdb1674e8 owner KV-STAGE-CENSUS qwen_kvsys/bind/PLAN plan of record not cleanly bound (strict bind) @bind: bind o: open 140 min, owner chain KV-ALLFIX > KV-GEOM-STUCK > KV-STAGE-CENSUS: kv3_pc_v1__cl7f648944__r8f64f1de3. You inherit this class from KV-GEOM-STUCK: post RESULT or ACK naming 9fdb1674e8 within 30 min. NEEDS-LANE already went
- 2026-11-24 22:50 PST DIED [QC-RC97-BT2] ot-run oth-ubuntu-2049819-1795576834 on civil-redfish: rc=1 after 12592 s, ended 06:50:22, log /srv/opentallas-scratch2/claude/QC-RC97-BT2/c/bindR.log, cmd: --no-spill --mem 64 --threads 8 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/QC-RC97-BT2/c -- bash /srv/opentallas-scratch2/claude/Q | class=BIND-FAIL cause=BIND_RC 1
- 2026-11-24 22:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-24 22:52 PST: 224 running jobs, PROGRESSING 212, SLOW 12, NO-PROGRESS 0 (this table is advisory; the separate noprog.timer watchdog (noprog_watchdog.py) DOES ot-heavy-stop NO-PROGRESS jobs, per-host log ~/.local/state/noprog/actions.jsonl); table lanes/NOPROG.tsv
- 2026-11-24 22:53 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-103): 1 event(s): slw_stm_v2__cl1ca9c415 SIGNED OFF -> count (signed off, archived epyc7:/srv/opentallas-scratch2/claude/autopilot/closed/qwen_compute/slw_stm_v2__cl1ca9c415__eb1e734)
- 2026-11-24 22:53 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-102): 4 event(s): kv3_hg_v3 LAUNCHED (kw-qwenkv-kv3hgv3-1-89611); kv3_pc_v1__cl7f648944__r8b2213035 LAUNCHED (kw-qwenkv-kv3pcv1cl7f648944r8b2213035-1-89635); kv3_pv_v8e LAUNCHED (kw-qwenkv-kv3pvv8e-1-89635); kv3_pve LAUNCHED (kw-qwenkv-kv3pve-1-89635)
- 2026-11-24 22:54 PST ALERT [HOLDGEN-1115 -> COORD, WAVE-HOLDS-1115] hold audit {'LEGACY-HOLD': 122}: LEGACY-HOLD qwen_kvsys/- x29: 29 hold_items key(s) with no record / typed release: kv3_hgi,kv3_hgi_v7,kv3_hg_v1p3__r8c662a835,kv3_hg_v1p4; LEGACY-HOLD s81/- x47: 47 hold_items key(s) with no record / typed release: col_h9_r0_p3__t1__cl0cd90c0e__*,slice_station__t40__cl1ea9de02,leaf__t14,leaf__t74; LEGACY-HOLD qwen_c
- 2026-11-24 22:54 PST ANSWER [QC-CB-C1L -> QC-GUARD-SIDECAR; cc QC-ALLFIX] My 645/752 count fields, not nodes: node and tap are counted separately (2 x 280 = 560 on C1m), plus 65 types whose sidecar collector tree differs from the plan collector_tree (the bind reads the tree from the plan), plus 20 sidecar types with no plan landing_contract. Node-level it is 280 on C1m and 334 on C1n-pre, which matches your 281/334

