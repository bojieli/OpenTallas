# COORD snapshot 2026-11-24 15:45 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: a45409e97e33
- 2026-11-24 07:00 PST MERGED [MERGE-QUEUE -> ROM-WEIGHTS-1119] claude/s81-stage-rom-1124b@6b1f22420b1 -> main a29cfd969bc -> 185838ec925, no-ff merge, tags flow-20261117-nc-*. Gate: gate record from renewed-glider 2026-11-24 14:58 UTC on main 6066335aa06 (main since: no overlap): 1 test file(s) pass (+7 source dir(s) the tests name: physical/asap7_memory_macros/ot_rom_8192x274_m8 results/arch/s81_map72_1021/r2_241 r
- 2026-11-24 07:20 PST MERGED [MERGE-QUEUE -> ROM-WEIGHTS-1119] claude/s81-stage-rom-1124b@e6aa0d2d0ab -> main 99c82ce69ca -> de09d7a2928, no-ff merge, tags flow-20261117-nd-*. Gate: gate record from dear-crayfish 2026-11-24 07:19 PST on main c66a01ee728 (main since: no overlap): 9 test file(s) pass (+26 source dir(s) the tests name: physical/asap7_memory_macros/ot_rom_8192x274_m8 physical/asap7_memory_macros_v2 phys
- 2026-11-24 07:20 PST MERGED [MERGE-QUEUE -> ROM-WEIGHTS-1119] claude/rom-seam-gate-1124@f899682294f -> main de09d7a2928 -> 6696da47acc, no-ff merge, tags flow-20261117-ne-*. Gate: gate record from dear-crayfish 2026-11-24 07:17 PST on main c66a01ee728 (main since: no overlap): no tests select for 2 changed file(s); static check only; tests: none. Lane ROM-WEIGHTS-1119.

## READY/ASK with no later COORD post naming them (1, heuristic: check each)
- 2026-11-24 15:26 PST ASK [QC-ALLFIX -> QC-GLUE-IMAGES; cc QC-GLUE, QC-CB-C1L, COORD] native59 stations: please emit the 3 NEED-STATION stations as a native RTL overlay (u_ist stages + native station receipt + istations.tcl). The groups are u_ring.dch.u_dsel->u_bin_dd_i (548 b, 692 um), u_qb.rst_pin->p_dd (459 b, 595 um) and u_qb.f_dd->qe_rep (1152 b, 596 um). Evidence: intel1 .../QC-ALLFIX/native59_1124115152/geom/

## Lane handoff files (age) and last queue post
- CODEX-TOKEN-1123: handoff 1345 min old; last post none in recent queue
- CORE-TAP-BUDGET: handoff 449 min old; last post 2026-11-24 09:14 DONE
- DLYRAM-RESET: handoff 737 min old; last post 2026-11-24 01:43 DONE
- EPYC11-ONBOARD-FINISH: handoff 920 min old; last post 2026-11-24 00:01 DONE
- EVENT-ENV-PREFLIGHT: handoff 525 min old; last post 2026-11-24 06:41 WAVE-BRIDGE-GREEN
- FABLE-OPEN-KV: handoff 1307 min old; last post 2026-11-23 18:32 DONE
- FABLE-OPEN-S81-A-rc37: handoff 1434 min old; last post none in recent queue
- FABLE-OPEN-S81-A-x14: handoff 1422 min old; last post none in recent queue
- FABLE-OPEN-S81-A: handoff 1420 min old; last post 2026-11-23 16:03 DONE
- FABLE-OPEN-S81-B: handoff 1434 min old; last post 2026-11-23 11:21 DONE
- FABLE-OPEN-S81-SVC: handoff 1436 min old; last post 2026-11-23 14:54 DONE
- FABLE-RC-ALL-KV-QC-HANDOVER: handoff 1221 min old; last post none in recent queue
- FABLE-RC-ALL: handoff 606 min old; last post 2026-11-23 17:05 DIED
- FABLE-RC-KV: handoff 622 min old; last post none in recent queue
- FABLE-RC-QC-SU: handoff 1124 min old; last post none in recent queue
- FABLE-RC-QC: handoff 604 min old; last post none in recent queue
- FAM-KV-HUBWO-S1: handoff 1061 min old; last post 2026-11-23 22:03 DONE
- FAM-S81-COL-H9R0: handoff 48 min old; last post 2026-11-24 14:54 DIED
- FAM-S81-DSDV-R1: handoff 1434 min old; last post 2026-11-23 10:02 DIED
- FIX-LEDGER: handoff 1411 min old; last post none in recent queue
- FIX-S81-SVC-WESTRIP: handoff 1426 min old; last post 2026-11-23 15:58 CORRECTION
- FLOW-CLKGRT-R2: handoff 1410 min old; last post 2026-11-23 16:13 RESULT
- FLOW-OPS-R3-CODEX-1123: handoff 1345 min old; last post none in recent queue
- FLOW-OPS-R3: handoff 340 min old; last post 2026-11-24 15:31 DONE
- GENDRY-KITRTL: handoff 1132 min old; last post 2026-11-23 21:38 DONE
- HEAD-100-unit-table-signedview: handoff 1 min old; last post none in recent queue
- HEAD-100-unit-table: handoff 6 min old; last post none in recent queue
- HEAD-EAST-REPLAN: handoff 421 min old; last post 2026-11-24 08:57 DIED
- HEAD-R18: handoff 386 min old; last post 2026-11-24 09:13 DIED
- HEAD-S2-RESEAL: handoff 1108 min old; last post 2026-11-23 21:15 DONE
- HEAD-WEST: handoff 225 min old; last post 2026-11-24 13:20 DONE
- HOLD-PAD-FLOW: handoff 383 min old; last post 2026-11-24 10:15 DONE
- KV-ALLFIX: handoff 72 min old; last post 2026-11-24 14:27 DONE
- KV-ASTK-EARLYTAP: handoff 1025 min old; last post 2026-11-23 22:39 DONE
- KV-D29-PACKAGE: handoff 1427 min old; last post none in recent queue
- KV-D29: handoff 1089 min old; last post 2026-11-23 21:39 NOTE
- KV-DIE-SEAMHOLD: handoff 1002 min old; last post 2026-11-23 23:01 DONE
- KV-HG-CAP: handoff 598 min old; last post 2026-11-24 10:48 DIED
- KV-HR-DEEPCLK: handoff 752 min old; last post 2026-11-24 04:14 DONE
- KV-HUB-EPZO: handoff 1096 min old; last post 2026-11-23 21:29 STAND-DOWN
- KV-HUB-HOLD: handoff 1037 min old; last post 2026-11-23 22:55 DONE
- KV-INCORE-R2: handoff 433 min old; last post 2026-11-24 08:29 DONE
- KV-OPEN-FWDCLK: handoff 1163 min old; last post 2026-11-23 20:20 DIED
- KV-OPEN-INCORE: handoff 1197 min old; last post 2026-11-23 20:20 DONE
- KV-OWN-HUB-R2: handoff 92 min old; last post 2026-11-24 15:34 DIED
- KV-OWN-PV-R2: handoff 169 min old; last post 2026-11-24 14:40 DONE
- KV-PREGRT-STALL: handoff 1118 min old; last post 2026-11-23 21:06 STAND-DOWN
- KV-PV-CAP: handoff 855 min old; last post 2026-11-24 01:28 DONE
- KV-PV-EDGESTRIP: handoff 690 min old; last post 2026-11-24 04:13 DONE
- KV-PV-FANOUT: handoff 50 min old; last post 2026-11-24 15:44 DONE
- KV-PV-RSTRELAY: handoff 1004 min old; last post 2026-11-23 22:58 DONE
- KV-R8-LANELOSS: handoff 1153 min old; last post 2026-11-23 20:32 STAND-DOWN
- KV-RCOLL-PHASE: handoff 1074 min old; last post none in recent queue
- KV-RCOLL-REBASE: handoff 1054 min old; last post 2026-11-23 22:08 DONE
- KV-RINGMAC-R1: handoff 1435 min old; last post 2026-11-23 14:46 DIED
- KV-RSTNAME-REMAP: handoff 1074 min old; last post 2026-11-23 21:48 DONE
- KV-RSTREACH: handoff 654 min old; last post 2026-11-24 07:30 DIED
- KV-SENDER-SKEW: handoff 653 min old; last post 2026-11-24 13:34 DONE
- KV-SPINE-REWIRE: handoff 700 min old; last post 2026-11-24 06:06 DONE
- KV-TAPSPLIT-HGPV: handoff 735 min old; last post 2026-11-24 03:29 DONE
- KVLEAF-MASTERS-from-ARCH-R2: handoff 1221 min old; last post none in recent queue
- KVLEAF-MASTERS: handoff 1019 min old; last post 2026-11-23 22:45 DONE
- LANDING-WRAP-TOOL: handoff 1042 min old; last post 2026-11-23 22:22 LIVE
- LANDREMAP-RSTNODE: handoff 1070 min old; last post 2026-11-23 21:56 STAND-DOWN
- LANEAGE-SWEEP: handoff 649 min old; last post 2026-11-24 07:44 DONE
- LAUNCH-GUARD: handoff 1344 min old; last post 2026-11-23 15:49 DONE
- LEC-AUTOFILL: handoff 302 min old; last post 2026-11-24 15:31 DIED
- LEC-VACUITY-SWEEP: handoff 518 min old; last post 2026-11-24 07:19 DONE
- OPS-SUPPORT-R1: handoff 1435 min old; last post 2026-11-23 20:03 EPYC8-FREED
- OPUS-FIX-QC-V4-R2: handoff 282 min old; last post 2026-11-24 11:01 HANDOVER
- PRE-QC-GENCHECK: handoff 775 min old; last post 2026-11-24 02:50 STAND-DOWN
- PRECHECK-CELLCAP: handoff 989 min old; last post 2026-11-23 23:14 RT
- PRECHECK-DERIVED-DROP: handoff 1030 min old; last post 2026-11-23 22:36 DONE
- PRECHECK-LEDGER-R3: handoff 705 min old; last post 2026-11-24 05:47 DONE
- PRECHECK-R3: handoff 158 min old; last post 2026-11-24 15:36 DONE
- QC-ALLFIX-COLL: handoff 724 min old; last post 2026-11-23 18:47 DONE
- QC-ALLFIX-SU: handoff 1303 min old; last post 2026-11-24 01:12 HANDOFF
- QC-ALLFIX: handoff 45 min old; last post 2026-11-24 15:28 TAKING
- QC-CB-C1L: handoff 5 min old; last post 2026-11-24 15:37 DONE
- QC-CB-PIPESEAT: handoff 114 min old; last post 2026-11-24 13:49 DONE
- QC-CB-SPREAD-R2: handoff 286 min old; last post 2026-11-24 13:37 DIED
- QC-COLLS-LEC: handoff 126 min old; last post 2026-11-24 13:40 DIED
- QC-F16-PRODUCER: handoff 615 min old; last post 2026-11-24 03:24 DONE
- QC-FW-CAP: handoff 758 min old; last post 2026-11-24 07:31 RESULT
- QC-GEOM-UNITS: handoff 234 min old; last post 2026-11-24 15:20 DONE
- QC-GLUE-IMAGES: handoff 40 min old; last post 2026-11-24 15:02 DONE
- QC-GLUE-PADBIND: handoff 741 min old; last post 2026-11-24 03:32 STAND-DOWN
- QC-HC1-CLKENTRY: handoff 710 min old; last post 2026-11-24 03:54 STAND-DOWN
- QC-HC3-LEC: handoff 22 min old; last post 2026-11-24 15:05 DONE
- QC-INHOLD-BUDGET: handoff 697 min old; last post 2026-11-24 05:10 DONE
- QC-OPEN-COLL: handoff 618 min old; last post 2026-11-24 06:55 RESULT
- QC-OPEN-STA: handoff 678 min old; last post 2026-11-24 09:07 DONE
- QC-OPEN-SU: handoff 687 min old; last post 2026-11-24 15:40 DONE
- QC-RSTCNT: handoff 729 min old; last post 2026-11-24 06:24 DONE
- QC-SLECTL-PILE: handoff 171 min old; last post none in recent queue
- QC-SLECTL-RESYN: handoff 626 min old; last post 2026-11-24 05:14 DONE
- QC-STB-CAP: handoff 987 min old; last post 2026-11-23 23:15 DONE
- QC-STB-SPLIT: handoff 113 min old; last post 2026-11-24 14:20 DONE
- QC-STSLW-ROUTE: handoff 21 min old; last post 2026-11-24 15:16 CLASS-CAUSE
- QC-SUC-FTSITE: handoff 23 min old; last post 2026-11-24 15:17 DONE
- QC-SUL1-STN-ROW: handoff 1072 min old; last post 2026-11-23 21:51 DONE
- QC-TTC-R2: handoff 725 min old; last post 2026-11-24 04:12 DONE
- QC-TTC-RETIME: handoff 1182 min old; last post 2026-11-23 20:45 DONE
- QC-V4: handoff 1022 min old; last post 2026-11-24 06:21 RESULT
- RELEC-1122: handoff 497 min old; last post 2026-11-24 10:27 DONE
- RELEC-R2-FAILSETS: handoff 120 min old; last post none in recent queue
- ROM-WEIGHTS-1119: handoff 444 min old; last post 2026-11-24 08:58 DONE
- S81-ALLFIX-COL: handoff 709 min old; last post 2026-11-24 12:00 DONE
- S81-ALLFIX-INT: handoff 444 min old; last post 2026-11-24 15:44 DONE
- S81-ALLFIX-MULTI: handoff 1266 min old; last post 2026-11-23 18:38 NOTE
- S81-ALLFIX-SLICE: handoff 1236 min old; last post 2026-11-23 19:56 DONE
- S81-ALLFIX-SVC-ENGMON: handoff 1253 min old; last post none in recent queue
- S81-ALLFIX-SVC-L0: handoff 1292 min old; last post none in recent queue
- S81-ALLFIX-SVC-MISC: handoff 1321 min old; last post none in recent queue
- S81-ALLFIX-SVC-SERDESRING: handoff 600 min old; last post none in recent queue
- S81-ALLFIX-SVC: handoff 1163 min old; last post 2026-11-24 14:13 DONE
- S81-C8-TYPES: handoff 238 min old; last post none in recent queue
- S81-C9-ROWS: handoff 18 min old; last post 2026-11-24 15:20 DONE
- S81-COL-J9: handoff 1429 min old; last post 2026-11-23 15:53 DONE
- S81-IQF-RELAY: handoff 258 min old; last post 2026-11-24 11:12 DONE
- S81-J9-ASSEMBLY-R6: handoff 606 min old; last post 2026-11-24 05:26 DIED
- S81-KV-CALENDAR: handoff 597 min old; last post 2026-11-24 07:26 RESULT
- S81-KVLEAF-T2-ARCH-R2: handoff 486 min old; last post 2026-11-24 07:31 DONE
- S81-LEAF-J9: handoff 1340 min old; last post 2026-11-23 17:22 DONE
- S81-LEPFLF-HOLD: handoff 843 min old; last post 2026-11-24 01:02 DONE
- S81-LEPW-CHAN: handoff 104 min old; last post 2026-11-24 15:04 DONE
- S81-MISC-SERDES-J9: handoff 1339 min old; last post 2026-11-23 17:05 DONE
- S81-OPEN-CLOCK: handoff 1029 min old; last post 2026-11-23 21:58 DONE
- S81-OPEN-DEMAND: handoff 1029 min old; last post 2026-11-23 20:59 DONE
- S81-OPEN-ENGCHAN: handoff 1229 min old; last post none in recent queue
- S81-OPEN-FSTART: handoff 946 min old; last post 2026-11-23 22:17 DIED
- S81-OPEN-LEAFBAND: handoff 952 min old; last post 2026-11-23 23:42 DONE
- S81-OPEN-SVCLO: handoff 1082 min old; last post 2026-11-23 21:41 DIED
- S81-OWN-COLH10: handoff 90 min old; last post 2026-11-24 15:14 DONE
- S81-OWN-DSDV: handoff 410 min old; last post none in recent queue
- S81-OWN-KVLEAF-LEP: handoff 910 min old; last post 2026-11-24 00:14 ASK
- S81-OWN-LEAF: handoff 102 min old; last post 2026-11-24 11:32 DONE
- S81-PROBE-LAUNCH: handoff 946 min old; last post 2026-11-24 03:20 DONE
- S81-ROM-TEMPLATE: handoff 762 min old; last post 2026-11-24 11:36 DIED
- S81-SERDES-TAPSKEW: handoff 456 min old; last post 2026-11-24 12:06 DIED
- S81-SLICE-J9: handoff 991 min old; last post 2026-11-24 01:45 DONE
- S81-SVC-J9: handoff 1397 min old; last post 2026-11-23 16:01 DONE
- S81-SVC-TIED: handoff 20 min old; last post 2026-11-24 15:18 DONE
- S81-T2-REFLOOR: handoff 867 min old; last post 2026-11-24 06:42 READY
- S81-TYPES-CODEX-1123: handoff 1345 min old; last post none in recent queue
- SEAT-MATCH-AUDIT: handoff 845 min old; last post 2026-11-24 10:52 DONE
- TAP-GRID-R6: handoff 1398 min old; last post 2026-11-23 16:24 DONE
- VIS-REOWN: handoff 46 min old; last post 2026-11-24 15:42 DONE

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 185; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 53 live
- S81-ALLFIX-INT agent ? last post 2026-11-24 15:44 DONE
- KV-PV-FANOUT agent ? last post 2026-11-24 15:44 DONE
- MERGE-QUEUE agent ? last post 2026-11-24 15:42 STATE
- VIS-REOWN agent ? last post 2026-11-24 15:42 DONE
- QC-OPEN-SU agent ? last post 2026-11-24 15:40 DONE
- qwen_compute agent ? last post 2026-11-24 15:37 KIT-WAVE
- QC-CB-C1L agent ? last post 2026-11-24 15:37 DONE
- PRECHECK-R3 agent ? last post 2026-11-24 15:36 DONE
- RELEC-R2 agent ? last post 2026-11-24 15:36 DIED
- KV-OWN-HUB-R2 agent ? last post 2026-11-24 15:34 DIED
- LEC-AUTOFILL agent ? last post 2026-11-24 15:31 DIED
- FLOW-OPS-R3 agent ? last post 2026-11-24 15:31 DONE
- FLEET-OPS-R agent ? last post 2026-11-24 15:31 ALERT
- NOPROG-WATCHDOG agent ? last post 2026-11-24 15:30 NEEDS-LANE
- QC-ALLFIX agent ? last post 2026-11-24 15:28 TAKING
- BIND-STREAM-LAUNCH agent ? last post 2026-11-24 15:24 DONE
- QC-GEOM-UNITS agent ? last post 2026-11-24 15:20 DONE
- S81-C9-ROWS agent ? last post 2026-11-24 15:20 DONE
- FAIL-ROUTE-1115 agent ? last post 2026-11-24 15:18 NEEDS-ACTION
- S81-SVC-TIED agent ? last post 2026-11-24 15:18 DONE
- CBC-RULES-1119 agent ? last post 2026-11-24 15:17 HOURLY
- QC-SUC-FTSITE agent ? last post 2026-11-24 15:17 DONE
- FLEET-WATCH-1015 agent ? last post 2026-11-24 15:16 CANCELLED
- QC-STSLW-ROUTE agent ? last post 2026-11-24 15:16 CLASS-CAUSE
- S81-OWN-COLH10 agent ? last post 2026-11-24 15:14 DONE
- qwen_kvsys agent ? last post 2026-11-24 15:11 KIT-WAVE
- QC-HC3-LEC agent ? last post 2026-11-24 15:05 DONE
- S81-LEPW-CHAN agent ? last post 2026-11-24 15:04 DONE
- QC-GLUE-IMAGES agent ? last post 2026-11-24 15:02 DONE
- NOPROG-FIX-1115 agent ? last post 2026-11-24 14:52 STATE
- KV-OWN-HG-R2 agent ? last post 2026-11-24 14:48 DONE
- OT-TOOLS-SYNC agent ? last post 2026-11-24 14:41 ALERT
- KV-OWN-PV-R2 agent ? last post 2026-11-24 14:40 DONE
- KV-OWN-RSTREACH agent ? last post 2026-11-24 14:39 DONE
- s81_head agent ? last post 2026-11-24 14:33 KIT-WAVE
- KIT-WAVE agent ? last post 2026-11-24 14:29 NEEDS-LANE
- FLOW-GUARD agent ? last post 2026-11-24 14:29 ALERT
- PLAN-CONFIG-DRIFT agent ? last post 2026-11-24 14:28 ALERT
- KV-ALLFIX agent ? last post 2026-11-24 14:27 DONE
- s81-own-colh10 agent ? last post 2026-11-24 14:26 DONE
- QC-STB-SPLIT agent ? last post 2026-11-24 14:20 DONE
- S81-ALLFIX-SVC agent ? last post 2026-11-24 14:13 DONE
- HOLD-OVERDUE agent ? last post 2026-11-24 14:06 ALERT
- QC-CB-PIPESEAT agent ? last post 2026-11-24 13:49 DONE
- HOLDGEN-1115 agent ? last post 2026-11-24 13:44 ALERT
- QC-COLLS-LEC agent ? last post 2026-11-24 13:40 DIED
- QC-CB-SPREAD-R2 agent ? last post 2026-11-24 13:37 DIED
- PRECHECK-1119 agent ? last post 2026-11-24 13:36 PLACE-PRECHECK
- KV-SENDER-SKEW agent ? last post 2026-11-24 13:34 DONE
- UNCOUNTED-SIGNED agent ? last post 2026-11-24 13:25 NEEDS-ACTION
- HEAD-WEST agent ? last post 2026-11-24 13:20 DONE
- kv-pv-fanout agent ? last post 2026-11-24 13:09 DONE
- REPEAT-STOP agent ? last post 2026-11-24 12:50 NEEDS-ACTION

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-24 15:45 PST)
count_hourly: signed any plan 598 | current plan 486 | deferred re-sign 21 (hbm 1, head 10, qc 7, s81 3) | retired-plan 91 (head 2, kv 13, qc 47, s81 29)
- [ ] FAIL.S81.CORES 72/72 signed · open: none
- [ ] FAIL.S81.TYPES 48/394 signed · kit rows: held by die owner (plan event pending) 296 (bk_sel__t2, +295) · cancelled (superseded) 48 (col_h10_r0_p1__t1__cl911743eb, +47)
- [ ] FAIL.HEAD.CORES 5/5 signed · open: none
- [ ] FAIL.HEAD.TYPES 25/27 signed · kit rows: held by die owner (plan event pending) 1 (hd_lep0N) · running (lint advisory) 1 (hd_lep0N_w)
- [ ] FAIL.QC.CORES 69/69 signed · open: none
- [ ] FAIL.QC.TYPES 80/127 signed · kit rows: held by die owner (plan event pending) 37 (cbf_q00__cl1b5a6458, +36) · running 2 · cancelled (superseded) 1 (glue) · other flow error 1 (slw_fe_v2__clf110fab2)
- [ ] FAIL.KV.CORES 84/85 signed · open: no kit-wave row 1 (kv3_pv_pair)
- [ ] FAIL.KV.TYPES 9/93 signed · kit rows: running (lint advisory) 46 (kv3_hg, +45) · running 21 · held by die owner (plan event pending) 13 (kv3_hgi, +12) · CLAND ring band 2 (kv3_pc__cl254f2e73__r872e39b5a, +1) · global_place error 1 (kv3_pc_v1__cl4ea58a5c__r884969661)
- [ ] FAIL.HBM.CORES 90/119 signed · open: no kit-wave row 19 (accel_smh_pt_w, hfd_coll_q3_body_ctl, hgi_sfu_opsa_group0, +12) · running, no result 9 (hfd_coll_q2n2_vm_core, hfd_hgi_vms_glue_nw_t, hgi_coll_tkm_m_tp192__root, +6) · shape: over cells/util/congestion 1 (hgi_dma_back_static_vp4_banks_cp
- [ ] FAIL.HBM.TYPES 4/81 signed · kit rows: none
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 2 current-event (+2 on a superseded plan block, not counted) (live check: ps/systemd/docker on all hosts; wave state: hub; full list lanes/STALE.tsv)
- [ ] STALE.S81 1 (cores 0, types 1) · by owner: FAIL-S81-1 1
  - type iqf__t1 · CANCELLED  STRUCT-STOP @ 2026-11-22 08:57 (54.8h) · owner FAIL-S81-1
- [ ] STALE.QC 1 (cores 0, types 1) · by owner: KIT-WAVE-1 1
  - type native59 · FAIL route INFRA @ 2026-11-24 04:40 (11.1h) · owner KIT-WAVE-1
- [ ] STALE.KV 2 (cores 1, types 1) · by owner: OPUS-FIX-KV-PV-R7 1, FAM-KV-HUBC-SYSC-R2 1
  - core kv3_pv_pair#380.16x190.08/c9cb3c7d41ae4f43 · no kit-wave row · owner OPUS-FIX-KV-PV-R7
  - type kv3_sys_c · CANCELLED geom SUPERSEDED @ 2026-11-23 20:57 (18.8h) · owner FAM-KV-HUBC-SYSC-R2
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
    15:45:21 up 31 days, 11:25, 183 users,  load average: 16.07, 17.93, 18.60

## ot-run status
    ot-run status: epyc2 admits 238 GB (avail 558, reserve 0, fresh 0, peak 64.4) load 76/128 run 36 threads 256/128 root 89% scratch 104 GB
    intel1 admits 179 GB (avail 488, reserve 0, fresh 0, peak 118.7) load 92/112 run 45 threads 368/112 root 44% scratch 100 GB
    localhost REFUSED (scratch disk /srv/opentallas-scratch2 has 92 GB free < floor 150 GB (the root fs is never a fallback; free the scratch disk, OT_RUN_SCRATCH_D
    epyc7 admits 33 GB (avail 251, reserve 0, fresh 0, peak 31.8) load 127/96 waiters 29:600 GB oldest 0.2 h run 27 threads 341/96 LOADCAP root 33% scratch 985 GB
    epyc8 admits 185 GB (avail 428, reserve 0, fresh 0, peak 23.6) load 121/96 waiters 9:344 GB oldest 0.2 h run 44 threads 472/96 LOADCAP root 46% scratch 359 GB
    epyc9 admits 450 GB (avail 588, reserve 0, fresh 0, peak 181.5) load 107/96 waiters 152:2080 GB oldest 0.2 h run 59 threads 392/96 root 45% scratch 776 GB
    epyc10 admits 207 GB (avail 512, reserve 0, fresh 0, peak 158) load 97/96 run 45 threads 533/96 root 25% scratch 573 GB
    epyc11 admits 400 GB (avail 564, reserve 0, fresh 0, peak 49.4) load 104/96 run 44 threads 310/96 root 5% scratch 2665 GB
    next 16-thread 32 GB job -> epyc2
    ot-run status: BLOCKED 456 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 344 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 332 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 332 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 261 min QC-GLUE-IMAGES /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
    ot-run status: BLOCKED 259 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 258 min QC-GLUE-IMAGES /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
    ot-run status: BLOCKED 253 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 251 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 225 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/items/slw_st_b_v1__c
    ot-run status: BLOCKED 132 min KV-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t5/private/KV-ALLFIX/kv3_pv_v3n
    ot-run status: BLOCKED 114 min VIS-REOWN /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 72 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 72 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 72 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 71 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 70 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 69 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 68 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 67 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL

## KIT-WAVE (autopilot log, last 6)
    2026-11-24 15:42:08 PST AUTOPILOT: KIT-WAVE src_overlay: hbm unreadable on epyc10; hold compares without it
    2026-11-24 15:42:10 PST AUTOPILOT: KIT-WAVE HOLD-AUTO-RELEASE summary: 0 keys released by their terms, 0 new this pass
    2026-11-24 15:43:37 PST AUTOPILOT: KIT-WAVE TOOLS-LAG qwen_kvsys 1 commits / missing none
    2026-11-24 15:43:37 PST AUTOPILOT: KIT-WAVE TOOLS-LAG s81 1 commits / missing none
    2026-11-24 15:43:37 PST AUTOPILOT: KIT-WAVE TOOLS-LAG s81_head 1 commits / missing none
    2026-11-24 15:43:37 PST AUTOPILOT: KIT-WAVE TOOLS-LAG qwen_compute 445 commits / missing r708

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-24 15:37 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-168049-1795563312 on tolerant-swine: rc=0 after 148 s, ended 15:37:35, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:37 PST DONE [QC-CB-C1L] ot-run oth-ubuntu-1291386-1795561324 on civil-redfish: rc=0 after 2143 s, ended 23:37:44, log /srv/opentallas-scratch2/claude/QC-CB-C1L/fork.log, cmd: --mem 8 --threads 2 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/QC-CB-C1L -- python3 -I /srv/opentallas-scratch2/claude/rt/current/
- 2026-11-24 15:37 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-3963320-1795562979 on tolerant-swine: rc=0 after 494 s, ended 15:37:49, log /home/ubuntu/tmp/s81int/c8s/spec_slice_station__t44/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
- 2026-11-24 15:37 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-4119039-1795563100 on tolerant-swine: rc=0 after 982 s, ended 15:37:55, log /home/ubuntu/tmp/s81int/c8s/spec_col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_r
- 2026-11-24 15:38 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-157323-1795563301 on tolerant-swine: rc=0 after 183 s, ended 15:38:00, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p5__t1__pvbca8d846/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:38 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-4168792-1795563144 on tolerant-swine: rc=0 after 349 s, ended 15:38:09, log /home/ubuntu/tmp/s81int/c8s/spec_slice_station__t30__cl1653104c/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
- 2026-11-24 15:38 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-4118249-1795563100 on tolerant-swine: rc=0 after 999 s, ended 15:38:12, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:38 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-134578-1795563283 on tolerant-swine: rc=0 after 239 s, ended 15:38:38, log /home/ubuntu/tmp/s81int/c8s/spec_ot_s81sl_leaf__t23/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/ot_s81sl
- 2026-11-24 15:38 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-4057150-1795563047 on tolerant-swine: rc=0 after 476 s, ended 15:38:39, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clb8d86cd5__pv8d57997d/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
- 2026-11-24 15:38 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-3926309-1795562949 on tolerant-swine: rc=0 after 577 s, ended 15:38:39, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clce45cab5__pvb11188eb/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:38 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-4058621-1795563049 on tolerant-swine: rc=0 after 486 s, ended 15:38:49, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clce45cab5__pvcd1d9f5f/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:38 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-4002463-1795563011 on tolerant-swine: rc=0 after 524 s, ended 15:38:50, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p5__t1__pv8995e794/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:38 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-4002427-1795563011 on tolerant-swine: rc=0 after 525 s, ended 15:38:51, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p3__t1__cl0cd90c0e__pv13474472/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:38 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-40529-1795563196 on tolerant-swine: rc=0 after 341 s, ended 15:38:52, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clce45cab5__pve0486b40/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:38 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-108068-1795563258 on tolerant-swine: rc=0 after 281 s, ended 15:38:54, log /home/ubuntu/tmp/s81int/c8s/spec_col_h10_r0_p4__t1__pv07945c1e/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_
- 2026-11-24 15:39 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-101306-1795563254 on tolerant-swine: rc=0 after 292 s, ended 15:39:02, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clce45cab5__pv843b0fff/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:39 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-171781-1795563316 on tolerant-swine: rc=0 after 242 s, ended 15:39:13, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p1__t1__pva2e3974f/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:39 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-269688-1795563412 on tolerant-swine: rc=0 after 146 s, ended 15:39:13, log /home/ubuntu/tmp/s81int/c8s/spec_slice_station__t52/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st
- 2026-11-24 15:39 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-254423-1795563405 on tolerant-swine: rc=0 after 165 s, ended 15:39:26, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clce45cab5__pv9cc104a8/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:39 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-3949187-1795562966 on tolerant-swine: rc=0 after 607 s, ended 15:39:27, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clb8d86cd5__pv982ec12c/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:39 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-109944-1795563260 on tolerant-swine: rc=0 after 317 s, ended 15:39:32, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p3__t1__cl31d0dc4b/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:39 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-203488-1795563352 on tolerant-swine: rc=0 after 235 s, ended 15:39:42, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__cl87f3ff59/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
- 2026-11-24 15:39 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-273968-1795563414 on tolerant-swine: rc=0 after 173 s, ended 15:39:43, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:39 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-4130984-1795563112 on tolerant-swine: rc=0 after 481 s, ended 15:39:48, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:39 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-309358-1795563445 on tolerant-swine: rc=0 after 148 s, ended 15:39:49, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r1__t1__clf32cde8d__pv63f488e9/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r1
- 2026-11-24 15:39 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-204573-1795563352 on tolerant-swine: rc=0 after 246 s, ended 15:39:54, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p5__t1__pv35382794/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:39 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-215294-1795563361 on tolerant-swine: rc=0 after 240 s, ended 15:39:55, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p4__t1__cl8ef405e8__pv91095415/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:40 PST DONE [QC-OPEN-SU] ot-run oth-ubuntu-823871-1795528731 on tolerant-swine: rc=0 after 34888 s, ended 15:40:14, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-SU/qwen_compute_qfd_qc_su_lane_w_l5_1124051223/chain_a1.live.log, cmd: --mem 64 --threads 8 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priva
- 2026-11-24 15:40 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-4022318-1795563024 on tolerant-swine: rc=0 after 603 s, ended 15:40:23, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clce45cab5__pv9a22736e/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
- 2026-11-24 15:40 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-4160710-1795563138 on tolerant-swine: rc=0 after 496 s, ended 15:40:30, log /home/ubuntu/tmp/s81int/c8s/spec_slice_station__t43/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
- 2026-11-24 15:40 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-3882678-1795562905 on tolerant-swine: rc=0 after 738 s, ended 15:40:38, log /home/ubuntu/tmp/s81int/c8s/spec_col_h10_r0_p4__t1__pvd8c0565f/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_
- 2026-11-24 15:40 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-282217-1795563420 on tolerant-swine: rc=0 after 223 s, ended 15:40:39, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p4__t1__cl8ef405e8__pv70731479/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:40 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-261617-1795563409 on tolerant-swine: rc=0 after 248 s, ended 15:40:52, log /home/ubuntu/tmp/s81int/c8s/spec_serdes__t4/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/serdes__
- 2026-11-24 15:40 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-4110382-1795563093 on tolerant-swine: rc=0 after 1171 s, ended 15:40:57, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clce45cab5__pv7a260fc0/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:41 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-293562-1795563427 on tolerant-swine: rc=0 after 239 s, ended 15:41:02, log /home/ubuntu/tmp/s81int/c8s/spec_ot_s81sl_leaf__t25__cl55642d17/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/ot_s81sl
- 2026-11-24 15:41 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-271655-1795563413 on tolerant-swine: rc=0 after 261 s, ended 15:41:09, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:41 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-271774-1795563413 on tolerant-swine: rc=0 after 269 s, ended 15:41:17, log /home/ubuntu/tmp/s81int/c8s/spec_col_h10_r0_p4__t1__pvcc166a6d/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_
- 2026-11-24 15:41 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-108292-1795563258 on tolerant-swine: rc=0 after 429 s, ended 15:41:23, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p2__t1__cl9f71e63d__pv2744f675/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:41 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-4075200-1795563063 on tolerant-swine: rc=0 after 626 s, ended 15:41:24, log /home/ubuntu/tmp/s81int/c8s/spec_col_h10_r2__t1__cl1f5d6c2a__pvec003743/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_
- 2026-11-24 15:41 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-4170541-1795563145 on tolerant-swine: rc=0 after 1146 s, ended 15:41:25, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p2__t1__cl0045af7b__pve183b536/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:42 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-337694-1795563476 on tolerant-swine: rc=0 after 262 s, ended 15:42:13, log /home/ubuntu/tmp/s81int/c8s/spec_ot_s81sl_leaf__t27/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/ot_s81sl
- 2026-11-24 15:42 PST DONE [VIS-REOWN] ot-run oth-ubuntu-1552061-1795563141 on tolerant-swine: rc=0 after 1211 s, ended 15:42:17, log /srv/opentallas-scratch2/claude/vis-reown/census/qwen_compute__sle_stm_v1__clbe630b9c__qwen_compute_sle_stm_v1__clbe630b9c_1124052610.log, cmd: --mem 24 --threads 4 --hosts epyc8 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9
- 2026-11-24 15:42 PST DRIFT [MERGE-QUEUE -> COORD; cc ADMIT-TUNE-1, KIT-OPS-5] live tree differs from its recorded main sha (2 new): epyc11 /home/ubuntu/.local/bin/ot-run differs from main tools/fleet/ot-run (live-only copy) ; epyc11: rt/current b2003c8a0830 != hub a9fc7cbfb32f. Any live fix must land as a branch + COORD APPROVED; the merge queue lands it and ot-tools-sync deploys it.
- 2026-11-24 15:42 PST STATE [MERGE-QUEUE -> COORD] drift cleared: epyc11: rt/current 2f70048f0596 != hub b2003c8a0830
- 2026-11-24 15:42 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-455077-1795563596 on tolerant-swine: rc=0 after 185 s, ended 15:42:57, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:42 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-433405-1795563575 on tolerant-swine: rc=0 after 207 s, ended 15:42:58, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clb8d86cd5__pv982ec12c/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
- 2026-11-24 15:43 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-283330-1795563420 on tolerant-swine: rc=0 after 366 s, ended 15:43:02, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p1__t1__pv8c197f8e/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:43 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-399091-1795563539 on tolerant-swine: rc=0 after 251 s, ended 15:43:06, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clce45cab5__pve0486b40/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
- 2026-11-24 15:43 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-288475-1795563424 on tolerant-swine: rc=0 after 372 s, ended 15:43:12, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p3__t1__cl0cd90c0e__pv8d734760/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:43 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-446112-1795563588 on tolerant-swine: rc=0 after 214 s, ended 15:43:17, log /home/ubuntu/tmp/s81int/c8s/spec_slice_station__t51/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
- 2026-11-24 15:43 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-304567-1795563439 on tolerant-swine: rc=0 after 373 s, ended 15:43:28, log /home/ubuntu/tmp/s81int/c8s/spec_serdes__t13/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/serdes__
- 2026-11-24 15:43 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-532380-1795563660 on tolerant-swine: rc=0 after 177 s, ended 15:43:52, log /home/ubuntu/tmp/s81int/c8s/spec_serdes__t4/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/serdes__t
- 2026-11-24 15:43 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-559359-1795563692 on tolerant-swine: rc=0 after 152 s, ended 15:43:59, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p2__t1__cl9f71e63d__pv2744f675/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
- 2026-11-24 15:44 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-409961-1795563549 on tolerant-swine: rc=0 after 295 s, ended 15:44:00, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clce45cab5__pv843b0fff/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
- 2026-11-24 15:44 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-514800-1795563649 on tolerant-swine: rc=0 after 196 s, ended 15:44:00, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clce45cab5__pv6827937d/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:44 PST DONE [KV-PV-FANOUT] ot-run oth-ubuntu-1366083-1795561485 on civil-redfish: rc=0 after 2360 s, ended 23:44:02, log /srv/opentallas-scratch2/claude/kv-pv-fanout/jobG.otrun.log, cmd: --mem 64 --threads 8 --disk 20 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/kv-pv-fanout -- env SRC=/srv/opentallas-scratch2/claude/
- 2026-11-24 15:44 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-317770-1795563451 on tolerant-swine: rc=0 after 405 s, ended 15:44:12, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r2__t1__clce45cab5__pva119e808/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:44 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-54649-1795563208 on tolerant-swine: rc=0 after 1266 s, ended 15:44:26, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r1__t1__clf32cde8d__pv48cfde67/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:44 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-575253-1795563702 on tolerant-swine: rc=0 after 180 s, ended 15:44:37, log /home/ubuntu/tmp/s81int/c8s/spec_col_h9_r0_p2__t1__cl0045af7b__pvd86cb19a/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r
- 2026-11-24 15:44 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-443894-1795563585 on tolerant-swine: rc=0 after 314 s, ended 15:44:54, log /home/ubuntu/tmp/s81int/c8s/spec_slice_station__t30__clcedefe91/kit_rtl.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_st

