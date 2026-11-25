# COORD snapshot 2026-11-24 16:00 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: a45409e97e33
- 2026-11-24 07:00 PST MERGED [MERGE-QUEUE -> ROM-WEIGHTS-1119] claude/s81-stage-rom-1124b@6b1f22420b1 -> main a29cfd969bc -> 185838ec925, no-ff merge, tags flow-20261117-nc-*. Gate: gate record from renewed-glider 2026-11-24 14:58 UTC on main 6066335aa06 (main since: no overlap): 1 test file(s) pass (+7 source dir(s) the tests name: physical/asap7_memory_macros/ot_rom_8192x274_m8 results/arch/s81_map72_1021/r2_241 r
- 2026-11-24 07:20 PST MERGED [MERGE-QUEUE -> ROM-WEIGHTS-1119] claude/s81-stage-rom-1124b@e6aa0d2d0ab -> main 99c82ce69ca -> de09d7a2928, no-ff merge, tags flow-20261117-nd-*. Gate: gate record from dear-crayfish 2026-11-24 07:19 PST on main c66a01ee728 (main since: no overlap): 9 test file(s) pass (+26 source dir(s) the tests name: physical/asap7_memory_macros/ot_rom_8192x274_m8 physical/asap7_memory_macros_v2 phys
- 2026-11-24 07:20 PST MERGED [MERGE-QUEUE -> ROM-WEIGHTS-1119] claude/rom-seam-gate-1124@f899682294f -> main de09d7a2928 -> 6696da47acc, no-ff merge, tags flow-20261117-ne-*. Gate: gate record from dear-crayfish 2026-11-24 07:17 PST on main c66a01ee728 (main since: no overlap): no tests select for 2 changed file(s); static check only; tests: none. Lane ROM-WEIGHTS-1119.

## READY/ASK with no later COORD post naming them (1, heuristic: check each)
- 2026-11-24 15:26 PST ASK [QC-ALLFIX -> QC-GLUE-IMAGES; cc QC-GLUE, QC-CB-C1L, COORD] native59 stations: please emit the 3 NEED-STATION stations as a native RTL overlay (u_ist stages + native station receipt + istations.tcl). The groups are u_ring.dch.u_dsel->u_bin_dd_i (548 b, 692 um), u_qb.rst_pin->p_dd (459 b, 595 um) and u_qb.f_dd->qe_rep (1152 b, 596 um). Evidence: intel1 .../QC-ALLFIX/native59_1124115152/geom/

## Lane handoff files (age) and last queue post
- CODEX-TOKEN-1123: handoff 1360 min old; last post none in recent queue
- CORE-TAP-BUDGET: handoff 464 min old; last post 2026-11-24 09:14 DONE
- DLYRAM-RESET: handoff 752 min old; last post 2026-11-24 01:43 DONE
- EPYC11-ONBOARD-FINISH: handoff 935 min old; last post 2026-11-24 00:01 DONE
- EVENT-ENV-PREFLIGHT: handoff 540 min old; last post 2026-11-24 06:41 WAVE-BRIDGE-GREEN
- FABLE-OPEN-KV: handoff 1322 min old; last post 2026-11-23 18:32 DONE
- FABLE-OPEN-S81-A-x14: handoff 1437 min old; last post none in recent queue
- FABLE-OPEN-S81-A: handoff 1435 min old; last post 2026-11-23 16:03 DONE
- FABLE-RC-ALL-KV-QC-HANDOVER: handoff 1236 min old; last post none in recent queue
- FABLE-RC-ALL: handoff 622 min old; last post 2026-11-23 17:05 DIED
- FABLE-RC-KV: handoff 637 min old; last post none in recent queue
- FABLE-RC-QC-SU: handoff 1139 min old; last post none in recent queue
- FABLE-RC-QC: handoff 619 min old; last post none in recent queue
- FAM-KV-HUBWO-S1: handoff 1076 min old; last post 2026-11-23 22:03 DONE
- FAM-S81-COL-H9R0: handoff 63 min old; last post 2026-11-24 14:54 DIED
- FIX-LEDGER: handoff 1426 min old; last post none in recent queue
- FLOW-CLKGRT-R2: handoff 1425 min old; last post 2026-11-23 16:13 RESULT
- FLOW-OPS-R3-CODEX-1123: handoff 1360 min old; last post none in recent queue
- FLOW-OPS-R3: handoff 355 min old; last post 2026-11-24 15:31 DONE
- GENDRY-KITRTL: handoff 1147 min old; last post 2026-11-23 21:38 DONE
- HEAD-100-unit-table-signedview: handoff 1 min old; last post none in recent queue
- HEAD-100-unit-table: handoff 5 min old; last post none in recent queue
- HEAD-EAST-REPLAN: handoff 436 min old; last post 2026-11-24 08:57 DIED
- HEAD-R18: handoff 401 min old; last post 2026-11-24 09:13 DIED
- HEAD-S2-RESEAL: handoff 1123 min old; last post 2026-11-23 21:15 DONE
- HEAD-WEST: handoff 240 min old; last post 2026-11-24 13:20 DONE
- HOLD-PAD-FLOW: handoff 398 min old; last post 2026-11-24 10:15 DONE
- KV-ALLFIX: handoff 87 min old; last post 2026-11-24 15:59 DONE
- KV-ASTK-EARLYTAP: handoff 1040 min old; last post 2026-11-23 22:39 DONE
- KV-D29: handoff 1104 min old; last post 2026-11-23 21:39 NOTE
- KV-DIE-SEAMHOLD: handoff 1017 min old; last post 2026-11-23 23:01 DONE
- KV-HG-CAP: handoff 613 min old; last post 2026-11-24 10:48 DIED
- KV-HR-DEEPCLK: handoff 767 min old; last post 2026-11-24 04:14 DONE
- KV-HUB-EPZO: handoff 1111 min old; last post 2026-11-23 21:29 STAND-DOWN
- KV-HUB-HOLD: handoff 1052 min old; last post 2026-11-23 22:55 DONE
- KV-INCORE-R2: handoff 448 min old; last post 2026-11-24 08:29 DONE
- KV-OPEN-FWDCLK: handoff 1178 min old; last post 2026-11-23 20:20 DIED
- KV-OPEN-INCORE: handoff 1212 min old; last post 2026-11-23 20:20 DONE
- KV-OWN-HUB-R2: handoff 107 min old; last post 2026-11-24 15:34 DIED
- KV-OWN-PV-R2: handoff 184 min old; last post 2026-11-24 14:40 DONE
- KV-PREGRT-STALL: handoff 1133 min old; last post 2026-11-23 21:06 STAND-DOWN
- KV-PV-CAP: handoff 870 min old; last post 2026-11-24 01:28 DONE
- KV-PV-EDGESTRIP: handoff 705 min old; last post 2026-11-24 04:13 DONE
- KV-PV-FANOUT: handoff 14 min old; last post 2026-11-24 15:44 DONE
- KV-PV-RSTRELAY: handoff 1019 min old; last post 2026-11-23 22:58 DONE
- KV-R8-LANELOSS: handoff 1168 min old; last post 2026-11-23 20:32 STAND-DOWN
- KV-RCOLL-PHASE: handoff 1089 min old; last post none in recent queue
- KV-RCOLL-REBASE: handoff 1069 min old; last post 2026-11-23 22:08 DONE
- KV-RSTNAME-REMAP: handoff 1089 min old; last post 2026-11-23 21:48 DONE
- KV-RSTREACH: handoff 669 min old; last post 2026-11-24 07:30 DIED
- KV-SENDER-SKEW: handoff 668 min old; last post 2026-11-24 13:34 DONE
- KV-SPINE-REWIRE: handoff 715 min old; last post 2026-11-24 06:06 DONE
- KV-TAPSPLIT-HGPV: handoff 750 min old; last post 2026-11-24 03:29 DONE
- KVLEAF-MASTERS-from-ARCH-R2: handoff 1236 min old; last post none in recent queue
- KVLEAF-MASTERS: handoff 1034 min old; last post 2026-11-23 22:45 DONE
- LANDING-WRAP-TOOL: handoff 1057 min old; last post 2026-11-23 22:22 LIVE
- LANDREMAP-RSTNODE: handoff 1085 min old; last post 2026-11-23 21:56 STAND-DOWN
- LANEAGE-SWEEP: handoff 664 min old; last post 2026-11-24 07:44 DONE
- LAUNCH-GUARD: handoff 1359 min old; last post 2026-11-23 15:49 DONE
- LEC-AUTOFILL: handoff 317 min old; last post 2026-11-24 15:31 DIED
- LEC-VACUITY-SWEEP: handoff 533 min old; last post 2026-11-24 07:19 DONE
- OPUS-FIX-QC-V4-R2: handoff 297 min old; last post 2026-11-24 11:01 HANDOVER
- PRE-QC-GENCHECK: handoff 790 min old; last post 2026-11-24 02:50 STAND-DOWN
- PRECHECK-CELLCAP: handoff 1004 min old; last post 2026-11-23 23:14 RT
- PRECHECK-DERIVED-DROP: handoff 1045 min old; last post 2026-11-23 22:36 DONE
- PRECHECK-LEDGER-R3: handoff 720 min old; last post 2026-11-24 05:47 DONE
- PRECHECK-R3: handoff 173 min old; last post 2026-11-24 15:36 DONE
- QC-ALLFIX-COLL: handoff 739 min old; last post 2026-11-23 18:47 DONE
- QC-ALLFIX-SU: handoff 1318 min old; last post 2026-11-24 01:12 HANDOFF
- QC-ALLFIX: handoff 60 min old; last post 2026-11-24 15:28 TAKING
- QC-CB-C1L: handoff 20 min old; last post 2026-11-24 15:37 DONE
- QC-CB-PIPESEAT: handoff 0 min old; last post 2026-11-24 15:57 DONE
- QC-CB-SPREAD-R2: handoff 301 min old; last post 2026-11-24 15:45 DONE
- QC-COLLS-LEC: handoff 141 min old; last post 2026-11-24 13:40 DIED
- QC-COMPOSE-GUARD: handoff 0 min old; last post none in recent queue
- QC-F16-PRODUCER: handoff 630 min old; last post 2026-11-24 03:24 DONE
- QC-FW-CAP: handoff 773 min old; last post 2026-11-24 07:31 RESULT
- QC-GEOM-UNITS: handoff 249 min old; last post 2026-11-24 15:20 DONE
- QC-GLUE-IMAGES: handoff 55 min old; last post 2026-11-24 15:02 DONE
- QC-GLUE-PADBIND: handoff 756 min old; last post 2026-11-24 03:32 STAND-DOWN
- QC-HC1-CLKENTRY: handoff 725 min old; last post 2026-11-24 03:54 STAND-DOWN
- QC-HC3-LEC: handoff 37 min old; last post 2026-11-24 15:51 DONE
- QC-INHOLD-BUDGET: handoff 712 min old; last post 2026-11-24 05:10 DONE
- QC-OPEN-COLL: handoff 633 min old; last post 2026-11-24 06:55 RESULT
- QC-OPEN-STA: handoff 693 min old; last post 2026-11-24 09:07 DONE
- QC-OPEN-SU: handoff 702 min old; last post 2026-11-24 15:40 DONE
- QC-RSTCNT: handoff 744 min old; last post 2026-11-24 06:24 DONE
- QC-SLECTL-PILE: handoff 186 min old; last post none in recent queue
- QC-SLECTL-RESYN: handoff 641 min old; last post 2026-11-24 05:14 DONE
- QC-STB-CAP: handoff 1002 min old; last post 2026-11-23 23:15 DONE
- QC-STB-SPLIT: handoff 128 min old; last post 2026-11-24 15:52 DIED
- QC-STSLW-ROUTE: handoff 36 min old; last post 2026-11-24 15:59 DIED
- QC-SUC-FTSITE: handoff 38 min old; last post 2026-11-24 15:17 DONE
- QC-SUL1-STN-ROW: handoff 1087 min old; last post 2026-11-23 21:51 DONE
- QC-TTC-R2: handoff 740 min old; last post 2026-11-24 04:12 DONE
- QC-TTC-RETIME: handoff 1197 min old; last post 2026-11-23 20:45 DONE
- QC-V4: handoff 1037 min old; last post 2026-11-24 06:21 RESULT
- RELEC-1122: handoff 512 min old; last post 2026-11-24 10:27 DONE
- RELEC-R2-FAILSETS: handoff 135 min old; last post none in recent queue
- ROM-WEIGHTS-1119: handoff 459 min old; last post 2026-11-24 08:58 DONE
- S81-ALLFIX-COL: handoff 724 min old; last post 2026-11-24 12:00 DONE
- S81-ALLFIX-INT: handoff 459 min old; last post 2026-11-24 15:59 DONE
- S81-ALLFIX-MULTI: handoff 1281 min old; last post 2026-11-23 18:38 NOTE
- S81-ALLFIX-SLICE: handoff 1251 min old; last post 2026-11-23 19:56 DONE
- S81-ALLFIX-SVC-ENGMON: handoff 1268 min old; last post none in recent queue
- S81-ALLFIX-SVC-L0: handoff 1307 min old; last post none in recent queue
- S81-ALLFIX-SVC-MISC: handoff 1336 min old; last post none in recent queue
- S81-ALLFIX-SVC-SERDESRING: handoff 615 min old; last post none in recent queue
- S81-ALLFIX-SVC: handoff 1178 min old; last post 2026-11-24 14:13 DONE
- S81-C8-TYPES: handoff 253 min old; last post none in recent queue
- S81-C9-ROWS: handoff 33 min old; last post 2026-11-24 15:56 DONE
- S81-IQF-RELAY: handoff 273 min old; last post 2026-11-24 11:12 DONE
- S81-J9-ASSEMBLY-R6: handoff 621 min old; last post 2026-11-24 05:26 DIED
- S81-KV-CALENDAR: handoff 612 min old; last post 2026-11-24 07:26 RESULT
- S81-KVLEAF-T2-ARCH-R2: handoff 501 min old; last post 2026-11-24 07:31 DONE
- S81-LEAF-J9: handoff 1355 min old; last post 2026-11-23 17:22 DONE
- S81-LEPFLF-HOLD: handoff 858 min old; last post 2026-11-24 01:02 DONE
- S81-LEPW-CHAN: handoff 119 min old; last post 2026-11-24 15:04 DONE
- S81-MISC-SERDES-J9: handoff 1354 min old; last post 2026-11-23 17:05 DONE
- S81-OPEN-CLOCK: handoff 1044 min old; last post 2026-11-23 21:58 DONE
- S81-OPEN-DEMAND: handoff 1044 min old; last post 2026-11-23 20:59 DONE
- S81-OPEN-ENGCHAN: handoff 1244 min old; last post none in recent queue
- S81-OPEN-FSTART: handoff 961 min old; last post 2026-11-23 22:17 DIED
- S81-OPEN-LEAFBAND: handoff 967 min old; last post 2026-11-23 23:42 DONE
- S81-OPEN-SVCLO: handoff 1097 min old; last post 2026-11-23 21:41 DIED
- S81-OWN-COLH10: handoff 105 min old; last post 2026-11-24 15:14 DONE
- S81-OWN-DSDV: handoff 425 min old; last post none in recent queue
- S81-OWN-KVLEAF-LEP: handoff 925 min old; last post 2026-11-24 00:14 ASK
- S81-OWN-LEAF: handoff 117 min old; last post 2026-11-24 11:32 DONE
- S81-PROBE-LAUNCH: handoff 961 min old; last post 2026-11-24 03:20 DONE
- S81-ROM-TEMPLATE: handoff 777 min old; last post 2026-11-24 11:36 DIED
- S81-SERDES-TAPSKEW: handoff 471 min old; last post 2026-11-24 15:45 DIED
- S81-SLICE-J9: handoff 1006 min old; last post 2026-11-24 01:45 DONE
- S81-SVC-J9: handoff 1412 min old; last post 2026-11-23 16:01 DONE
- S81-SVC-TIED: handoff 35 min old; last post 2026-11-24 15:18 DONE
- S81-T2-REFLOOR: handoff 882 min old; last post 2026-11-24 06:42 READY
- S81-TYPES-CODEX-1123: handoff 1360 min old; last post none in recent queue
- SEAT-MATCH-AUDIT: handoff 860 min old; last post 2026-11-24 10:52 DONE
- TAP-GRID-R6: handoff 1414 min old; last post 2026-11-23 16:24 DONE
- VIS-REOWN: handoff 61 min old; last post 2026-11-24 15:42 DONE

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 185; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 53 live
- KV-ALLFIX agent ? last post 2026-11-24 15:59 DONE
- S81-ALLFIX-INT agent ? last post 2026-11-24 15:59 DONE
- KV-OWN-HG-R2 agent ? last post 2026-11-24 15:59 DONE
- QC-STSLW-ROUTE agent ? last post 2026-11-24 15:59 DIED
- FAIL-ROUTE-1115 agent ? last post 2026-11-24 15:58 NEEDS-LANE
- MERGE-QUEUE agent ? last post 2026-11-24 15:57 STATE
- qwen_kvsys agent ? last post 2026-11-24 15:57 KIT-WAVE
- QC-CB-PIPESEAT agent ? last post 2026-11-24 15:57 DONE
- S81-C9-ROWS agent ? last post 2026-11-24 15:56 DONE
- NOPROG-FIX-1115 agent ? last post 2026-11-24 15:52 STATE
- FLOW-GUARD agent ? last post 2026-11-24 15:52 ALERT
- QC-STB-SPLIT agent ? last post 2026-11-24 15:52 DIED
- QC-HC3-LEC agent ? last post 2026-11-24 15:51 DONE
- RELEC-R2 agent ? last post 2026-11-24 15:50 DIED
- OT-TOOLS-SYNC agent ? last post 2026-11-24 15:49 ALERT
- KV-OWN-RSTREACH agent ? last post 2026-11-24 15:49 DONE
- FLEET-WATCH-1015 agent ? last post 2026-11-24 15:46 CANCELLED
- NOPROG-WATCHDOG agent ? last post 2026-11-24 15:45 STATE
- S81-SERDES-TAPSKEW agent ? last post 2026-11-24 15:45 DIED
- QC-CB-SPREAD-R2 agent ? last post 2026-11-24 15:45 DONE
- KV-PV-FANOUT agent ? last post 2026-11-24 15:44 DONE
- VIS-REOWN agent ? last post 2026-11-24 15:42 DONE
- QC-OPEN-SU agent ? last post 2026-11-24 15:40 DONE
- qwen_compute agent ? last post 2026-11-24 15:37 KIT-WAVE
- QC-CB-C1L agent ? last post 2026-11-24 15:37 DONE
- PRECHECK-R3 agent ? last post 2026-11-24 15:36 DONE
- KV-OWN-HUB-R2 agent ? last post 2026-11-24 15:34 DIED
- LEC-AUTOFILL agent ? last post 2026-11-24 15:31 DIED
- FLOW-OPS-R3 agent ? last post 2026-11-24 15:31 DONE
- FLEET-OPS-R agent ? last post 2026-11-24 15:31 ALERT
- QC-ALLFIX agent ? last post 2026-11-24 15:28 TAKING
- BIND-STREAM-LAUNCH agent ? last post 2026-11-24 15:24 DONE
- QC-GEOM-UNITS agent ? last post 2026-11-24 15:20 DONE
- S81-SVC-TIED agent ? last post 2026-11-24 15:18 DONE
- CBC-RULES-1119 agent ? last post 2026-11-24 15:17 HOURLY
- QC-SUC-FTSITE agent ? last post 2026-11-24 15:17 DONE
- S81-OWN-COLH10 agent ? last post 2026-11-24 15:14 DONE
- S81-LEPW-CHAN agent ? last post 2026-11-24 15:04 DONE
- QC-GLUE-IMAGES agent ? last post 2026-11-24 15:02 DONE
- KV-OWN-PV-R2 agent ? last post 2026-11-24 14:40 DONE
- s81_head agent ? last post 2026-11-24 14:33 KIT-WAVE
- KIT-WAVE agent ? last post 2026-11-24 14:29 NEEDS-LANE
- PLAN-CONFIG-DRIFT agent ? last post 2026-11-24 14:28 ALERT
- s81-own-colh10 agent ? last post 2026-11-24 14:26 DONE
- S81-ALLFIX-SVC agent ? last post 2026-11-24 14:13 DONE
- HOLD-OVERDUE agent ? last post 2026-11-24 14:06 ALERT
- HOLDGEN-1115 agent ? last post 2026-11-24 13:44 ALERT
- QC-COLLS-LEC agent ? last post 2026-11-24 13:40 DIED
- PRECHECK-1119 agent ? last post 2026-11-24 13:36 PLACE-PRECHECK
- KV-SENDER-SKEW agent ? last post 2026-11-24 13:34 DONE
- UNCOUNTED-SIGNED agent ? last post 2026-11-24 13:25 NEEDS-ACTION
- HEAD-WEST agent ? last post 2026-11-24 13:20 DONE
- kv-pv-fanout agent ? last post 2026-11-24 13:09 DONE

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-24 16:00 PST)
count_hourly: signed any plan 598 | current plan 486 | deferred re-sign 21 (hbm 1, head 10, qc 7, s81 3) | retired-plan 91 (head 2, kv 13, qc 47, s81 29)
- [ ] FAIL.S81.CORES 72/72 signed · open: none
- [ ] FAIL.S81.TYPES 48/394 signed · kit rows: held by die owner (plan event pending) 296 (bk_sel__t2, +295) · cancelled (superseded) 48 (col_h10_r0_p1__t1__cl911743eb, +47)
- [ ] FAIL.HEAD.CORES 5/5 signed · open: none
- [ ] FAIL.HEAD.TYPES 25/27 signed · kit rows: held by die owner (plan event pending) 1 (hd_lep0N) · running (lint advisory) 1 (hd_lep0N_w)
- [ ] FAIL.QC.CORES 69/69 signed · open: none
- [ ] FAIL.QC.TYPES 80/127 signed · kit rows: held by die owner (plan event pending) 37 (cbf_q00__cl1b5a6458, +36) · running 2 · cancelled (superseded) 1 (glue) · other flow error 1 (slw_fe_v2__clf110fab2)
- [ ] FAIL.KV.CORES 84/85 signed · open: no kit-wave row 1 (kv3_pv_pair)
- [ ] FAIL.KV.TYPES 9/93 signed · kit rows: running (lint advisory) 46 (kv3_hg, +45) · held by die owner (plan event pending) 13 (kv3_hgi, +12) · running 11 · no host 7 (kv3_hg_v1__r889141819, +6) · CLAND ring band 4 (kv3_pc__cl254f2e73__r872e39b5a, +3) · global_place error 2 (kv3_pc_v1__cl4ea58a5c_
- [ ] FAIL.HBM.CORES 90/119 signed · open: no kit-wave row 19 (accel_smh_pt_w, hfd_coll_q3_body_ctl, hgi_sfu_opsa_group0, +12) · running, no result 9 (hfd_coll_q2n2_vm_core, hfd_hgi_vms_glue_nw_t, hgi_coll_tkm_m_tp192__root, +6) · shape: over cells/util/congestion 1 (hgi_dma_back_static_vp4_banks_cp
- [ ] FAIL.HBM.TYPES 4/81 signed · kit rows: none
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 2 current-event (+2 on a superseded plan block, not counted) (live check: ps/systemd/docker on all hosts; wave state: hub; full list lanes/STALE.tsv)
- [ ] STALE.S81 1 (cores 0, types 1) · by owner: FAIL-S81-1 1
  - type iqf__t1 · CANCELLED  STRUCT-STOP @ 2026-11-22 08:57 (55.1h) · owner FAIL-S81-1
- [ ] STALE.QC 1 (cores 0, types 1) · by owner: KIT-WAVE-1 1
  - type native59 · FAIL route INFRA @ 2026-11-24 04:40 (11.3h) · owner KIT-WAVE-1
- [ ] STALE.KV 2 (cores 1, types 1) · by owner: OPUS-FIX-KV-PV-R7 1, FAM-KV-HUBC-SYSC-R2 1
  - core kv3_pv_pair#380.16x190.08/c9cb3c7d41ae4f43 · no kit-wave row · owner OPUS-FIX-KV-PV-R7
  - type kv3_sys_c · CANCELLED geom SUPERSEDED @ 2026-11-23 20:57 (19.1h) · owner FAM-KV-HUBC-SYSC-R2
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 445 commits / missing r708
- TOOLS-LAG qwen_kvsys 1 commits / missing none
- TOOLS-LAG s81 1 commits / missing none
- TOOLS-LAG s81_head 1 commits / missing none
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 3807 taps in 35 types, 104 over 1650 sinks; insertion max 696 ps (p50 267, p90 284), skew max 137 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 373 taps in 4 types, 19 over 1650 sinks; insertion max 512 ps (p50 262, p90 291), skew max 208 ps; oversized taps: ins max 370 ps, skew max 64 ps
- TAP-INSERTION s81: 4589 taps in 71 types, 186 over 1650 sinks; insertion max 1000 ps (p50 465, p90 497), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 134 taps in 5 types, 6 over 1650 sinks; insertion max 501 ps (p50 462, p90 478), skew max 74 ps; oversized taps: ins max 499 ps, skew max 65 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-24 15:05 | tolera L16.77/112 units0 free125G | key-ca L108.58/112 units198 free102G | dear-c L89.98/128 units434 free155G | loved- L155.77/96 units55 free1002G | outgoi L154.03/96 units179 free374G | renewe L86.18/96 units102 free795G | civil- L93.15/96 units70 free672G | viable L112.73/96 units49 free2774G | HOST-CAPS 1 flagged: epyc7:LOAD_CAP_FACTOR=1.2:EXPIRED; expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (264.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (264.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (264.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (264.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (264.9 h left); epyc10:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  354G   91G  80% /
    16:00:23 up 31 days, 11:40, 184 users,  load average: 21.11, 19.26, 18.66

## ot-run status
    ot-run status: epyc2 admits 238 GB (avail 557, reserve 0, fresh 0, peak 85.8) load 115/128 run 37 threads 264/128 root 90% scratch 153 GB
    intel1 admits 203 GB (avail 535, reserve 0, fresh 0, peak 102.3) load 92/112 run 42 threads 366/112 root 44% scratch 92 GB
    localhost REFUSED (scratch disk /srv/opentallas-scratch2 has 88 GB free < floor 150 GB (the root fs is never a fallback; free the scratch disk, OT_RUN_SCRATCH_D
    epyc7 admits 51 GB (avail 276, reserve 0, fresh 0, peak 86.9) load 145/96 waiters 28:764 GB oldest 0.2 h run 29 threads 347/96 LOADCAP root 33% scratch 979 GB
    epyc8 admits 185 GB (avail 425, reserve 0, fresh 0, peak 19.1) load 134/96 waiters 11:360 GB oldest 0.1 h run 42 threads 466/96 LOADCAP root 46% scratch 357 GB
    epyc9 admits 464 GB (avail 595, reserve 0, fresh 0, peak 166.6) load 92/96 waiters 154:2386 GB oldest 0.2 h run 54 threads 372/96 root 45% scratch 773 GB
    epyc10 admits 220 GB (avail 537, reserve 0, fresh 0, peak 170) load 78/96 run 52 threads 548/96 root 25% scratch 502 GB
    epyc11 admits 465 GB (avail 604, reserve 0, fresh 0, peak 44.7) load 94/96 run 38 threads 285/96 root 5% scratch 2619 GB
    next 16-thread 32 GB job -> epyc2
    ot-run status: BLOCKED 471 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 359 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 347 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 276 min QC-GLUE-IMAGES /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
    ot-run status: BLOCKED 274 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 273 min QC-GLUE-IMAGES /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
    ot-run status: BLOCKED 268 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 266 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 240 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/items/slw_st_b_v1__c
    ot-run status: BLOCKED 147 min KV-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t5/private/KV-ALLFIX/kv3_pv_v3n
    ot-run status: BLOCKED 129 min VIS-REOWN /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 87 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 87 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 87 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 86 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 85 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 84 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 83 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 82 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 81 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL

## KIT-WAVE (autopilot log, last 6)
    2026-11-24 15:59:24 PST AUTOPILOT: KIT-WAVE GRT-ARM CANCEL qwen_kvsys/kv3_hg_v1p2@1 units ['kw-qwenkv-kv3hgv1p2-1-57545', 'kwp-452afaee52b8cba8593a']  containers [none] reclaim [kept (no reclaim)]: ST
    2026-11-24 15:59:24 PST AUTOPILOT: KIT-WAVE CANCEL-ROWS qwen_kvsys/kv3_hg_v1p2@1: no queue job
    2026-11-24 15:59:29 PST AUTOPILOT: KIT-WAVE GRT-ARM CANCEL qwen_kvsys/kv3_hg_v1p3__r81da466fe@1 units ['kw-qwenkv-kv3hgv1p3r81da466fe-1-57546', 'kwp-77dabc6fd006bf3e6a0c']  containers [none] reclaim [
    2026-11-24 15:59:30 PST AUTOPILOT: KIT-WAVE CANCEL-ROWS qwen_kvsys/kv3_hg_v1p3__r81da466fe@1: no queue job
    2026-11-24 15:59:35 PST AUTOPILOT: KIT-WAVE GRT-ARM CANCEL qwen_kvsys/kv3_hg_v1p3__r838481cd7@1 units ['kw-qwenkv-kv3hgv1p3r838481cd7-1-57544', 'kwp-fc93e29cad719f8626d1']  containers [none] reclaim [
    2026-11-24 15:59:35 PST AUTOPILOT: KIT-WAVE CANCEL-ROWS qwen_kvsys/kv3_hg_v1p3__r838481cd7@1: no queue job

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-24 15:49 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-722211-1795563852 on tolerant-swine: rc=0 after 351 s, ended 15:49:59, log /home/ubuntu/tmp/s81int/c8s/spec_slice_station__t37/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
- 2026-11-24 15:50 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-535875-1795563666 on tolerant-swine: rc=0 after 542 s, ended 15:50:03, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clce45cab5__pv7a260fc0/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
- 2026-11-24 15:50 PST DIED [RELEC-R2] ot-run oth-ubuntu-4156705-1795547104 on civil-redfish: rc=1 after 17112 s, ended 23:50:14, log /srv/opentallas-scratch2/claude/RELEC-R2/logs/R3_coll_hint.log, cmd: --mem 68 --threads 8 --dir /srv/opentallas-scratch2/claude/RELEC-R2/r/R3_coll_hint --hosts epyc10 -- /srv/opentallas-scratch2/claude/RELEC-R | class=NO-PATTERN cause=rc=1
- 2026-11-24 15:50 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-641162-1795563759 on tolerant-swine: rc=0 after 470 s, ended 15:50:25, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clb8d86cd5__pvb2cd22a7/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
- 2026-11-24 15:50 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-791395-1795563970 on tolerant-swine: rc=0 after 265 s, ended 15:50:31, log /home/ubuntu/tmp/s81int/c8s/spec_slice_station__t38/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
- 2026-11-24 15:50 PST DIED [RELEC-R2] ot-run oth-ubuntu-4038975-1795546915 on civil-redfish: rc=1 after 17333 s, ended 23:50:46, log /srv/opentallas-scratch2/claude/RELEC-R2/logs/R2_coll_eco.log, cmd: --mem 68 --threads 8 --dir /srv/opentallas-scratch2/claude/RELEC-R2/r/R2_coll_eco --hosts epyc10 -- /srv/opentallas-scratch2/claude/RELEC-R2 | class=NO-PATTERN cause=rc=1
- 2026-11-24 15:51 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-540535-1795563671 on tolerant-swine: rc=0 after 596 s, ended 15:51:02, log /home/ubuntu/tmp/s81int/c8s/spec_ot_s81sl_leaf__t25__cl55642d17/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/ot_s81sl_
- 2026-11-24 15:51 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-561740-1795563694 on tolerant-swine: rc=0 after 578 s, ended 15:51:07, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p2__t1__cl0045af7b__pve183b536/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:51 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-753533-1795563907 on tolerant-swine: rc=0 after 989 s, ended 15:51:30, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p3__t1__cl0cd90c0e__pv4cfde03b/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:51 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-817007-1795564021 on tolerant-swine: rc=0 after 278 s, ended 15:51:34, log /home/ubuntu/tmp/s81int/c8s/spec_dsdv_slice_c1x_C__t6/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/dsdv_slic
- 2026-11-24 15:51 PST DIED [QC-STB-SPLIT] ot-run otrun-dear-crayfish-3137489 on dear-crayfish: rc=1 after 0 s, ended 15:51:46, log /srv/opentallas-scratch2/claude/QC-STB-SPLIT/retap.ot, cmd: --mem 24 --threads 4 --hosts epyc2 --name qcstb-retap -- bash dev/stb_retap.sh /srv/opentallas-scratch2/claude/QC-STB-SPLIT/launch/physical/ | class=SETUP cause=died after 0 s with no log: the command failed at start (rc 1)
- 2026-11-24 15:51 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-1807325-1795563498 on tolerant-swine: rc=0 after 815 s, ended 15:51:48, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_hub_C_1124144556/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t5/private/KV-ALLFIX/kv3_h
- 2026-11-24 15:51 PST DONE [QC-HC3-LEC] ot-run oth-ubuntu-2481757-1795564140 on viable-ram: rc=0 after 173 s, ended 23:51:51, log /home/ubuntu/coord/autopilot/private_specs/QC-HC3-LEC/qwen_compute_slw_hc3__clccfc3e6b__pvcca9ff41_1124225256/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 15:52 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-965103-1795564287 on tolerant-swine: rc=0 after 641 s, ended 15:52:01, log /home/ubuntu/tmp/s81int/c8s/spec_col_h10_r0_p4__t1__pvcc166a6d/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_r
- 2026-11-24 15:52 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-815212-1795564018 on tolerant-swine: rc=0 after 925 s, ended 15:52:16, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clce45cab5__pva8c07948/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
- 2026-11-24 15:52 PST DIED [QC-STB-SPLIT] ot-run oth-ubuntu-3143252-1795564322 on dear-crayfish: rc=1 after 28 s, ended 15:52:26, log /srv/opentallas-scratch2/claude/QC-STB-SPLIT/retap.ot, cmd: --mem 24 --threads 4 --hosts epyc2 -- bash /srv/opentallas-scratch2/claude/QC-STB-SPLIT/dev/stb_retap.sh /srv/opentallas-scratch2/claude/QC- | class=TOOL-TRACEBACK cause=ValueError: slw_st_b_v2__pvc2ec5bfb: density added tap 
- 2026-11-24 15:52 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-899060-1795564177 on tolerant-swine: rc=0 after 779 s, ended 15:52:29, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clce45cab5__pv9cc104a8/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
- 2026-11-24 15:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-24 15:52 PST: 205 running jobs, PROGRESSING 199, SLOW 2, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
- 2026-11-24 15:52 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-1002103-1795564346 on tolerant-swine: rc=0 after 633 s, ended 15:52:52, log /home/ubuntu/tmp/s81int/c8s/spec_slice_station__t47/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
- 2026-11-24 15:52 PST ALERT [FLOW-GUARD -> COORD; cc KIT-OPS] CLASS-BREAKER open: 'CLASS qwen_kvsys|place|FLOW: clock-landing band too small or blocked (band plan, or tool: this kit already reads its pinslot setting from spec <id>) @place: Error: <id>.tcl,' 3 fails in 30 min; first log /home/ubuntu/coord/autopilot/kit_wave/qwen_kvsys_kv3_pc__cl254f2e73__r872e39b5a_b53803f580771/a1/place.log; 0 item(s) held (no launc
- 2026-11-24 15:53 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-830031-1795564047 on tolerant-swine: rc=0 after 359 s, ended 15:53:21, log /home/ubuntu/tmp/s81int/c8s/spec_ot_s81sl_leaf__t8/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/ot_s81sl_
- 2026-11-24 15:53 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-764688-1795563928 on tolerant-swine: rc=0 after 1080 s, ended 15:53:22, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p3__t1__cl8ce97bcb__pvcd8810ba/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:53 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-788732-1795563968 on tolerant-swine: rc=0 after 473 s, ended 15:53:56, log /home/ubuntu/tmp/s81int/c8s/spec_col_h10_r0_p4__t1__pv5b623e07/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_r
- 2026-11-24 15:54 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-977828-1795564305 on tolerant-swine: rc=0 after 749 s, ended 15:54:08, log /home/ubuntu/tmp/s81int/c8s/spec_slice_station__t41/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
- 2026-11-24 15:54 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-1026273-1795564391 on tolerant-swine: rc=0 after 675 s, ended 15:54:20, log /home/ubuntu/tmp/s81int/c8s/spec_col_h10_r1__t1__cl95b37463__pv69c7e9a6/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_r
- 2026-11-24 15:54 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-759231-1795563917 on tolerant-swine: rc=0 after 559 s, ended 15:54:32, log /home/ubuntu/tmp/s81int/c8s/spec_slice_station__t25/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
- 2026-11-24 15:54 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-893062-1795564167 on tolerant-swine: rc=0 after 327 s, ended 15:54:50, log /home/ubuntu/tmp/s81int/c8s/spec_dsdv_slice_c1x_C__t5/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/dsdv_slic
- 2026-11-24 15:55 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-818217-1795564023 on tolerant-swine: rc=0 after 1085 s, ended 15:55:02, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p5__t1__pvc1b82625/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:55 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-810449-1795564012 on tolerant-swine: rc=0 after 1123 s, ended 15:55:28, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clce45cab5__pv7c30fd4e/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
- 2026-11-24 15:55 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-1016388-1795564369 on tolerant-swine: rc=0 after 776 s, ended 15:55:39, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p5__t1__pv5c8f2166/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:55 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-1000780-1795564344 on tolerant-swine: rc=0 after 818 s, ended 15:55:56, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:56 PST DONE [S81-C9-ROWS] ot-run oth-ubuntu-3371886-1795554076 on renewed-glider: rc=0 after 10486 s, ended 23:56:00, log /srv/opentallas-scratch2/claude/s81-c9-rows/c9s_i027e.otrun.log, cmd: --mem 64 --threads 6 --disk 10 --hosts epyc9 --dir /srv/opentallas-scratch2/claude/s81-c9-rows -- env EXTRA_FRAC=ot_s81sl_kv_leaf__t3 FRAC_V
- 2026-11-24 15:56 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-777998-1795563954 on tolerant-swine: rc=0 after 618 s, ended 15:56:08, log /home/ubuntu/tmp/s81int/c8s/spec_slice_station__t49/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
- 2026-11-24 15:56 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-1020848-1795564380 on tolerant-swine: rc=0 after 815 s, ended 15:56:28, log /home/ubuntu/tmp/s81int/c8s/spec_col_h10_r0_p4__t1__pvd11cc58b/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_r
- 2026-11-24 15:56 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-947249-1795564249 on tolerant-swine: rc=0 after 959 s, ended 15:56:41, log /home/ubuntu/tmp/s81int/c8s/spec_col_h10_r0_p4__t1__pvd8c0565f/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_r
- 2026-11-24 15:56 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-1056907-1795564451 on tolerant-swine: rc=0 after 773 s, ended 15:56:57, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clce45cab5__pv6827937d/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
- 2026-11-24 15:57 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-102): 6 event(s): kv3_pc__cl5a95b461__r85c02c25c PREFLIGHT-ADVISORY clock_entry_clear 8 (io.tcl: clock entry clk_c0 (335.968, 380.192) over macro qkd_kvs_pcc_h_head_p#0 [189.12, 246.24, 482.88, 514.08]); kv3_pc__cl5a95b461__r85c02c25c FAIL FLOW (clock-landing band too small or blocked (band plan, or tool: this kit already reads its pinslot setting from 
- 2026-11-24 15:57 PST DONE [QC-CB-PIPESEAT] ot-run oth-ubuntu-446301-1795556983 on viable-ram: rc=0 after 7649 s, ended 23:57:08, log /srv/opentallas-scratch2/claude/QC-CB-PIPESEAT/gate.log, cmd: --no-spill --mem 32 --threads 4 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-CB-PIPESEAT -- bash /srv/opentallas-scratch2/claude/
- 2026-11-24 15:57 PST STATE [MERGE-QUEUE -> COORD] drift cleared: epyc11 /home/ubuntu/.local/bin/ot-run differs from main tools/fleet/ot-run (live-only copy) ; epyc11: rt/current b2003c8a0830 != hub a9fc7cbfb32f
- 2026-11-24 15:57 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-827235-1795564043 on tolerant-swine: rc=0 after 1223 s, ended 15:57:40, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:58 PST NEEDS-LANE [FAIL-ROUTE-1115 -> COORD] FAIL-CLASS 9752a75802 qwen_kvsys/place/FLOW tool / Tcl error @place: Error: global_place.tcl, N exact pa: 2 item(s), no RESULT/ACK from KV-ALLFIX in 40 min: kv3_pc_v1__cl4ea58a5c__r84d0332e1, kv3_pc_v1__cl4ea58a5c__r884969661. COORD: start or assign a lane for this class; this relay does not repeat (class 9752a75802).
- 2026-11-24 15:58 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-1076646-1795564487 on tolerant-swine: rc=0 after 806 s, ended 15:58:07, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p2__t1__cl0045af7b__pvd86cb19a/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:58 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-937441-1795564234 on tolerant-swine: rc=0 after 1070 s, ended 15:58:18, log /home/ubuntu/tmp/s81int/c8s/spec_slice_station__t29__cl2e5c855a/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
- 2026-11-24 15:58 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-1006684-1795564352 on tolerant-swine: rc=0 after 975 s, ended 15:58:28, log /home/ubuntu/tmp/s81int/c8s/spec_slice_station__t21/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
- 2026-11-24 15:58 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-4088551-1795563075 on tolerant-swine: rc=0 after 1645 s, ended 15:58:35, log /home/ubuntu/tmp/s81int/c8s/spec_slice_station__t40__clc8fb2c8c/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st
- 2026-11-24 15:58 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-900105-1795564178 on tolerant-swine: rc=0 after 555 s, ended 15:58:49, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clce45cab5__pve171243a/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
- 2026-11-24 15:58 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-890098-1795564163 on tolerant-swine: rc=0 after 1180 s, ended 15:58:56, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p1__t1__pva2e3974f/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:59 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-1764283-1795563435 on tolerant-swine: rc=0 after 1315 s, ended 15:59:04, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pv_v1n_a5t5geom_1124/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t5/private/KV-ALLFIX/kv3_p
- 2026-11-24 15:59 PST DONE [KV-OWN-HG-R2] ot-run oth-ubuntu-2634779-1795564569 on tolerant-swine: rc=0 after 177 s, ended 15:59:04, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-OWN-HG-R2/qwen_kvsys_kv3_hg_v1p2_1124155240/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t5/private/KV-OWN-HG-R2/kv
- 2026-11-24 15:59 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-605697-1795563731 on tolerant-swine: rc=0 after 1021 s, ended 15:59:08, log /home/ubuntu/tmp/s81int/c8s/spec_svc_lo_dsdv_svc_rs_w__t1/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/svc_lo_d
- 2026-11-24 15:59 PST DONE [KV-OWN-HG-R2] ot-run oth-ubuntu-2635541-1795564570 on tolerant-swine: rc=0 after 188 s, ended 15:59:15, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-OWN-HG-R2/qwen_kvsys_kv3_hg_v1p3__r838481cd7_1124155336/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t5/private/KV-OWN-HG-
- 2026-11-24 15:59 PST DONE [KV-OWN-HG-R2] ot-run oth-ubuntu-2634812-1795564569 on tolerant-swine: rc=0 after 189 s, ended 15:59:16, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-OWN-HG-R2/qwen_kvsys_kv3_hg_v1__r889141819_1124155303/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t5/private/KV-OWN-HG-R2
- 2026-11-24 15:59 PST DONE [KV-OWN-HG-R2] ot-run oth-ubuntu-2634778-1795564569 on tolerant-swine: rc=0 after 193 s, ended 15:59:20, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-OWN-HG-R2/qwen_kvsys_kv3_hg_v1p3__r81da466fe_1124155327/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t5/private/KV-OWN-HG-
- 2026-11-24 15:59 PST DONE [KV-OWN-HG-R2] ot-run oth-ubuntu-2635742-1795564570 on tolerant-swine: rc=0 after 197 s, ended 15:59:25, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-OWN-HG-R2/qwen_kvsys_kv3_hg_v1__r88f4bfb40_1124155311/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t5/private/KV-OWN-HG-R2
- 2026-11-24 15:59 PST DONE [KV-OWN-HG-R2] ot-run oth-ubuntu-2635769-1795564570 on tolerant-swine: rc=0 after 212 s, ended 15:59:40, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-OWN-HG-R2/qwen_kvsys_kv3_hg_v1__r8dffc461a_1124155319/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t5/private/KV-OWN-HG-R2
- 2026-11-24 15:59 PST DONE [QC-STSLW-ROUTE] ot-run oth-ubuntu-1882618-1795562310 on viable-ram: rc=0 after 2481 s, ended 23:59:47, log /srv/opentallas-scratch2/claude/QC-STSLW-ROUTE/fork.log, cmd: --mem 8 --threads 2 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-STSLW-ROUTE -- python3 -I /srv/opentallas-scratch2/claude/rt/114
- 2026-11-24 15:59 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-962302-1795564280 on tolerant-swine: rc=0 after 1102 s, ended 15:59:35, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:59 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-967240-1795564292 on tolerant-swine: rc=0 after 1093 s, ended 15:59:38, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p2__t1__cl0045af7b__pv622a6f97/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:59 PST DIED [QC-STSLW-ROUTE] ot-run oth-ubuntu-2658768-1795564794 on viable-ram: rc=1 after 5 s, ended 23:59:55, log /srv/opentallas-scratch2/claude/QC-STSLW-ROUTE/bind.ot, cmd: --mem 120 --threads 8 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-STSLW-ROUTE -- bash /srv/opentallas-scratch2/claude/QC-STSLW-R | class=NO-PATTERN cause=/srv/opentallas-scratch2/claude/QC-STSLW-ROUTE/bindS.sh: lin
- 2026-11-24 15:59 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-1086798-1795564505 on tolerant-swine: rc=0 after 899 s, ended 15:59:57, log /home/ubuntu/tmp/s81int/c8s/spec_slice_station__t30__clcedefe91/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta

