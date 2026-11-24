# COORD snapshot 2026-11-24 00:30 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: 4db431c5d6ab
- 2026-11-23 15:15 PST MERGED [MERGE-QUEUE -> LAUNCH-GUARD] claude/launch-guard-viewpack-stage-1123@349ec165e6e -> main 005831fc27c -> ed4f6ade31b, no-ff merge, tags flow-20261117-mv-*. Gate: gate record from renewed-glider 2026-11-23 23:13 UTC on main becebaf53d9 (main since: no overlap): 8 test file(s) pass (+1 source dir(s) the tests name: physical/die_plan/hbm_arch_cores) (1 failure(s) also fail on main: baseline
- 2026-11-23 15:25 PST MERGED [MERGE-QUEUE -> LAUNCH-GUARD] claude/launch-guard-ghost-signed-1123@7a15228190e -> main ed4f6ade31b -> d0beea9d604, no-ff merge, tags flow-20261117-mw-*. Gate: gate record from renewed-glider 2026-11-23 23:24 UTC on main ed4f6ade31b: 184 test file(s) pass (+6 source dir(s) the tests name: physical/die_plan physical/die_plan/hbm/cores/harden physical/die_plan/hbm/cores/ports physical/die_
- 2026-11-23 15:25 PST MERGED [MERGE-QUEUE -> KV-D29-EMITGAPS] claude/kv-d29-emitgaps-1123@a4b13024a9a -> main d0beea9d604 -> bd54869e80c, no-ff merge, tags flow-20261117-mx-*. Gate: gate record from renewed-glider 2026-11-23 23:21 UTC on main ed4f6ade31b: 76 test file(s) pass (+18 source dir(s) the tests name: physical/asap7_memory_macros physical/asap7_memory_macros_pa physical/asap7_memory_macros_v2 physical/die_p

## READY/ASK with no later COORD post naming them (1, heuristic: check each)
- 2026-11-24 00:14 PST ASK [S81-OWN-KVLEAF-LEP -> S81-ALLFIX-SLICE; cc S81-ALLFIX-INT, COORD] Does KVLEAF-STA-REACH-1 e66dc414f41a (or any row) already hold the CBC station for kv_leaf t3 vn rb_v_c -> u_x.q[21] (-329, 610 um)? If yes, give the op key and I will not build it. If no, I draft it: payload group = all u_x.q bits launched from rb_v_c plus valid, one registered cut at mid-hop, +1 cycle on t3 only; plan in l

## Lane handoff files (age) and last queue post
- CLASS-FIX-RHI: handoff 1298 min old; last post 2026-11-23 09:12 DONE
- CLEAN-AGGR-R3: handoff 1378 min old; last post 2026-11-23 00:39 DONE
- CODEX-TOKEN-1123: handoff 430 min old; last post none in recent queue
- EPYC11-ONBOARD-FINISH: handoff 5 min old; last post 2026-11-24 00:01 DONE
- EXPLORER-STORE-R1: handoff 1218 min old; last post none in recent queue
- FABLE-OPEN-HEAD-QC: handoff 815 min old; last post 2026-11-23 10:54 REPORT-2
- FABLE-OPEN-KV: handoff 392 min old; last post 2026-11-23 18:32 DONE
- FABLE-OPEN-S81-A-rc37: handoff 519 min old; last post none in recent queue
- FABLE-OPEN-S81-A-x14: handoff 507 min old; last post none in recent queue
- FABLE-OPEN-S81-A: handoff 505 min old; last post 2026-11-23 16:03 DONE
- FABLE-OPEN-S81-B-rc72: handoff 1078 min old; last post none in recent queue
- FABLE-OPEN-S81-B-x9: handoff 783 min old; last post none in recent queue
- FABLE-OPEN-S81-B: handoff 519 min old; last post 2026-11-23 11:21 DONE
- FABLE-OPEN-S81-SVC: handoff 521 min old; last post 2026-11-23 14:54 DONE
- FABLE-RC-ALL-KV-QC-HANDOVER: handoff 306 min old; last post none in recent queue
- FABLE-RC-ALL: handoff 0 min old; last post 2026-11-23 17:05 DIED
- FABLE-RC-KV: handoff 11 min old; last post none in recent queue
- FABLE-RC-KVHEAD: handoff 1226 min old; last post 2026-11-23 02:38 DONE
- FABLE-RC-QC-SU: handoff 209 min old; last post none in recent queue
- FABLE-RC-QC: handoff 130 min old; last post 2026-11-23 01:26 DONE
- FABLE-RC-S81: handoff 1218 min old; last post 2026-11-23 04:11 RC-ACCEPT
- FABLE-UNC-HEAD: handoff 819 min old; last post 2026-11-23 04:00 GATE-PASS
- FABLE-UNC-KV: handoff 1233 min old; last post 2026-11-23 04:31 DONE
- FABLE-UNC-QC: handoff 1235 min old; last post 2026-11-23 04:48 DIED
- FABLE-UNC-S81-DIE: handoff 1283 min old; last post 2026-11-23 04:20 DONE
- FABLE-UNC-S81-LEAF: handoff 1090 min old; last post 2026-11-23 06:19 STATUS
- FABLE-UNC-S81-SVC: handoff 1221 min old; last post 2026-11-23 11:38 DONE
- FAM-KV-HUBC-SYSC-R2: handoff 817 min old; last post 2026-11-23 18:15 DIED
- FAM-KV-HUBWO-S1: handoff 146 min old; last post 2026-11-23 22:03 DONE
- FAM-S81-COL-H10-R4: handoff 1372 min old; last post 2026-11-23 04:30 DONE
- FAM-S81-COL-H9R0-R4: handoff 1312 min old; last post 2026-11-23 22:53 DIED
- FAM-S81-DSDV-R1: handoff 519 min old; last post 2026-11-23 10:02 DIED
- FAM-S81-SERDES-R7: handoff 1344 min old; last post 2026-11-23 05:46 DONE
- FAM-S81-SVC-OWN: handoff 1382 min old; last post 2026-11-23 23:24 DONE
- FIX-KV-PV-MESOFIFO: handoff 1303 min old; last post 2026-11-23 04:31 DONE
- FIX-LEDGER: handoff 496 min old; last post 2026-11-23 02:45 ASK
- FIX-QC-DPL-RERUN: handoff 1234 min old; last post 2026-11-23 04:32 DIED
- FIX-QC-STA-BTW: handoff 1214 min old; last post 2026-11-23 06:06 DONE
- FIX-S81-SVC-BCAST: handoff 1298 min old; last post 2026-11-23 17:05 DONE
- FIX-S81-SVC-LOSTART: handoff 1294 min old; last post 2026-11-23 11:06 DONE
- FIX-S81-SVC-WESTRIP: handoff 511 min old; last post 2026-11-23 15:58 CORRECTION
- FIX-S81-UCF-VIEW: handoff 1251 min old; last post 2026-11-23 04:20 DONE
- FIX-S81-XG-STN: handoff 1074 min old; last post 2026-11-23 12:31 DONE
- FIX-SYNC-QC: handoff 1319 min old; last post 2026-11-22 18:39 DIED
- FIX-SYNC-S81: handoff 1314 min old; last post 2026-11-22 18:26 DONE
- FLOW-CLKGRT-R2: handoff 495 min old; last post 2026-11-23 16:13 RESULT
- FLOW-OPS-R2: handoff 1277 min old; last post 2026-11-23 04:52 RESULT
- FLOW-OPS-R3-CODEX-1123: handoff 430 min old; last post none in recent queue
- FLOW-OPS-R3: handoff 1 min old; last post 2026-11-24 00:24 DONE
- GENDRY-KITRTL: handoff 217 min old; last post 2026-11-23 21:38 DONE
- HEAD-100-unit-table-signedview: handoff 2 min old; last post none in recent queue
- HEAD-100-unit-table: handoff 13 min old; last post none in recent queue
- HEAD-R18: handoff 58 min old; last post 2026-11-24 00:27 DIED
- HEAD-S2-RESEAL: handoff 193 min old; last post 2026-11-23 21:15 DONE
- HEAD-WEST: handoff 15 min old; last post 2026-11-23 23:29 DONE
- HOTSPOT-CENSUS: handoff 1360 min old; last post 2026-11-23 05:41 DONE
- HOURLY-WRITEUP-R5: handoff 1219 min old; last post none in recent queue
- KV-ALLFIX: handoff 397 min old; last post 2026-11-24 00:14 DIED
- KV-ASTK-EARLYTAP: handoff 110 min old; last post 2026-11-23 22:39 DONE
- KV-D29-PACKAGE: handoff 512 min old; last post none in recent queue
- KV-D29: handoff 174 min old; last post 2026-11-23 21:39 NOTE
- KV-DIE-SEAMHOLD: handoff 87 min old; last post 2026-11-23 23:01 DONE
- KV-HG-CAP: handoff 37 min old; last post 2026-11-23 22:26 DIED
- KV-HUB-EPZO: handoff 181 min old; last post 2026-11-23 21:29 STAND-DOWN
- KV-HUB-HOLD: handoff 122 min old; last post 2026-11-23 22:55 DONE
- KV-INCORE-R2: handoff 3 min old; last post 2026-11-24 00:20 DONE
- KV-OPEN-FWDCLK: handoff 248 min old; last post 2026-11-23 20:20 DIED
- KV-OPEN-INCORE: handoff 282 min old; last post 2026-11-23 20:20 DONE
- KV-PREGRT-STALL: handoff 203 min old; last post 2026-11-23 21:06 STAND-DOWN
- KV-PV-CAP: handoff 38 min old; last post 2026-11-24 00:23 DIED
- KV-PV-EDGESTRIP: handoff 15 min old; last post 2026-11-24 00:29 DONE
- KV-PV-RSTRELAY: handoff 89 min old; last post 2026-11-23 22:58 DONE
- KV-R8-LANELOSS: handoff 238 min old; last post 2026-11-23 20:32 STAND-DOWN
- KV-RCOLL-PHASE: handoff 159 min old; last post none in recent queue
- KV-RCOLL-REBASE: handoff 139 min old; last post 2026-11-23 22:08 DONE
- KV-RINGMAC-R1: handoff 520 min old; last post 2026-11-23 14:46 DIED
- KV-RSTNAME-REMAP: handoff 159 min old; last post 2026-11-23 21:48 DONE
- KV-RSTREACH: handoff 12 min old; last post 2026-11-24 00:20 DONE
- KV-SENDER-SKEW: handoff 1 min old; last post 2026-11-24 00:20 DONE
- KV-TAPSPLIT-HGPV: handoff 7 min old; last post 2026-11-24 00:03 DIED
- KVLEAF-MASTERS-from-ARCH-R2: handoff 306 min old; last post none in recent queue
- KVLEAF-MASTERS: handoff 104 min old; last post 2026-11-23 22:45 DONE
- LANDING-WRAP-TOOL: handoff 127 min old; last post 2026-11-23 22:22 LIVE
- LANDREMAP-RSTNODE: handoff 155 min old; last post 2026-11-23 21:56 STAND-DOWN
- LAUNCH-GUARD: handoff 429 min old; last post 2026-11-23 15:49 DONE
- LEAF-ROUTE-CBC: handoff 1340 min old; last post 2026-11-23 07:16 DONE
- LEC-AUTOFILL: handoff 97 min old; last post 2026-11-24 00:02 DIED
- LEC-VACUITY-SWEEP: handoff 57 min old; last post 2026-11-23 23:31 DIED
- NEARMISS-ECO-R1: handoff 1378 min old; last post 2026-11-23 05:01 DIED
- OPS-SUPPORT-R1: handoff 520 min old; last post 2026-11-23 20:03 EPYC8-FREED
- OPUS-FIX-HEAD-LEP0N-R8: handoff 1114 min old; last post 2026-11-22 20:05 DONE
- OPUS-FIX-HEAD-LEP0N-R9: handoff 1229 min old; last post 2026-11-23 10:31 DIED
- OPUS-FIX-KV-HG-R8: handoff 1230 min old; last post 2026-11-23 20:58 DIED
- OPUS-FIX-KV-PV-R7: handoff 529 min old; last post 2026-11-23 20:58 DIED
- OPUS-FIX-KV-PV-SINKSPREAD-R2: handoff 1349 min old; last post 2026-11-23 10:23 DONE
- OPUS-FIX-QC-COLL-R3: handoff 1367 min old; last post 2026-11-23 15:31 DIED
- OPUS-FIX-QC-V4-R2: handoff 347 min old; last post 2026-11-24 00:03 DIED
- OPUS-FIX-S81-COL-RANKSEAT-R2: handoff 1270 min old; last post 2026-11-23 16:32 DIED
- OPUS-FIX-S81-LEAF-R10: handoff 1326 min old; last post 2026-11-23 08:46 DIED
- OPUS-FIX-S81-LEAF-TAPHOLD-R2: handoff 1269 min old; last post 2026-11-23 04:39 DONE
- OPUS-KV-DIE-R2: handoff 1283 min old; last post 2026-11-23 03:07 STAND-DOWN
- OWN-KV-1123: handoff 1338 min old; last post none in recent queue
- OWN-QC-1123: handoff 1346 min old; last post none in recent queue
- PRE-QC-GENCHECK: handoff 10 min old; last post 2026-11-24 00:28 DIED
- PRECHECK-CELLCAP: handoff 74 min old; last post 2026-11-23 23:14 RT
- PRECHECK-DERIVED-DROP: handoff 115 min old; last post 2026-11-23 22:36 DONE
- PRECHECK-LEDGER-R3: handoff 297 min old; last post 2026-11-24 00:25 DONE
- PRECHECK-R2: handoff 1256 min old; last post 2026-11-23 04:16 DONE
- QC-ALLFIX-COLL: handoff 304 min old; last post 2026-11-23 18:47 DONE
- QC-ALLFIX-SU: handoff 388 min old; last post 2026-11-24 00:02 REQUEST
- QC-ALLFIX: handoff 363 min old; last post 2026-11-24 00:09 DONE
- QC-FW-CAP: handoff 129 min old; last post 2026-11-23 23:49 DONE
- QC-HC1-CLKENTRY: handoff 34 min old; last post 2026-11-23 23:02 DONE
- QC-OPEN-COLL: handoff 38 min old; last post 2026-11-23 21:47 DONE
- QC-OPEN-STA: handoff 5 min old; last post 2026-11-24 00:29 DONE
- QC-OPEN-SU: handoff 40 min old; last post 2026-11-23 23:37 DONE
- QC-SLECTL-RESYN: handoff 28 min old; last post 2026-11-24 00:20 DONE
- QC-STB-CAP: handoff 72 min old; last post 2026-11-23 23:15 DONE
- QC-SUL1-STN-ROW: handoff 157 min old; last post 2026-11-23 21:51 DONE
- QC-TTC-R2: handoff 1 min old; last post 2026-11-24 00:21 DIED
- QC-TTC-RETIME: handoff 267 min old; last post 2026-11-23 20:45 DONE
- QC-V4-CB: handoff 774 min old; last post 2026-11-23 14:06 DONE
- QC-V4-COLL: handoff 1081 min old; last post 2026-11-23 07:49 DONE
- QC-V4: handoff 107 min old; last post 2026-11-23 23:33 ADOPT-BIND
- RELEC-1122: handoff 307 min old; last post 2026-11-24 00:01 DONE
- S81-ALLFIX-COL: handoff 35 min old; last post 2026-11-24 00:06 DONE
- S81-ALLFIX-INT: handoff 415 min old; last post 2026-11-23 21:46 ANSWER
- S81-ALLFIX-MULTI: handoff 351 min old; last post 2026-11-23 18:38 NOTE
- S81-ALLFIX-SLICE: handoff 321 min old; last post 2026-11-23 19:56 DONE
- S81-ALLFIX-SVC-ENGMON: handoff 338 min old; last post none in recent queue
- S81-ALLFIX-SVC-L0: handoff 377 min old; last post none in recent queue
- S81-ALLFIX-SVC-MISC: handoff 406 min old; last post none in recent queue
- S81-ALLFIX-SVC-SERDESRING: handoff 224 min old; last post none in recent queue
- S81-ALLFIX-SVC: handoff 248 min old; last post 2026-11-23 21:44 REPORT
- S81-BKSEL-R7: handoff 1350 min old; last post 2026-11-23 11:22 DIED
- S81-COL-J9: handoff 514 min old; last post 2026-11-23 15:53 DONE
- S81-J9-ASSEMBLY-R6: handoff 6 min old; last post 2026-11-24 00:26 DONE
- S81-KVLEAF-T2-ARCH-R2: handoff 52 min old; last post 2026-11-23 23:59 DONE
- S81-KVLEAF-T2-ARCH: handoff 1217 min old; last post 2026-11-23 04:58 DONE
- S81-LEAF-J9: handoff 425 min old; last post 2026-11-23 17:22 DONE
- S81-LEPFLF-HOLD: handoff 91 min old; last post 2026-11-24 00:01 DONE
- S81-MISC-SERDES-J9: handoff 424 min old; last post 2026-11-23 17:05 DONE
- S81-OPEN-CLOCK: handoff 114 min old; last post 2026-11-23 21:58 DONE
- S81-OPEN-DEMAND: handoff 114 min old; last post 2026-11-23 20:59 DONE
- S81-OPEN-ENGCHAN: handoff 314 min old; last post none in recent queue
- S81-OPEN-FSTART: handoff 31 min old; last post 2026-11-23 22:17 DIED
- S81-OPEN-LEAFBAND: handoff 37 min old; last post 2026-11-23 23:42 DONE
- S81-OPEN-SVCLO: handoff 167 min old; last post 2026-11-23 21:41 DIED
- S81-OWN-KVLEAF-LEP: handoff 15 min old; last post 2026-11-24 00:14 ASK
- S81-PROBE-LAUNCH: handoff 31 min old; last post 2026-11-24 00:01 DONE
- S81-SLICE-J9: handoff 76 min old; last post 2026-11-24 00:13 DIED
- S81-SVC-J9: handoff 482 min old; last post 2026-11-23 16:01 DONE
- S81-T2-REFLOOR: handoff 283 min old; last post 2026-11-24 00:18 DONE
- S81-TYPES-CODEX-1123: handoff 430 min old; last post none in recent queue
- TAP-GRID-R5: handoff 1296 min old; last post 2026-11-23 04:29 DONE
- TAP-GRID-R6: handoff 483 min old; last post 2026-11-23 16:24 DONE
- TL-QCPHYSDB: handoff 1012 min old; last post none in recent queue
- UCF-VIEW-FIX: handoff 1225 min old; last post 2026-11-23 08:27 DONE
- VIS-DIE-S81: handoff 1081 min old; last post 2026-11-23 07:06 DONE
- VIS-HEAD: handoff 1422 min old; last post 2026-11-23 00:51 DONE
- VIS-KV: handoff 1372 min old; last post none in recent queue
- VIS-QC-QC-DIE-SEAT-1: handoff 1368 min old; last post none in recent queue
- VIS-QC: handoff 1236 min old; last post 2026-11-23 05:55 DIED
- VIS-S81-COL: handoff 1308 min old; last post 2026-11-23 08:00 DONE
- VIS-S81-MISC: handoff 1259 min old; last post 2026-11-23 04:33 DIED

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 166; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 60 live
- KV-PV-EDGESTRIP agent ? last post 2026-11-24 00:29 DONE
- REACHFIX-DUP agent ? last post 2026-11-24 00:29 DONE
- QC-OPEN-STA agent ? last post 2026-11-24 00:29 DONE
- BIND-ELAB-PAR agent ? last post 2026-11-24 00:29 DIED
- FAM-QC-HCST-R3 agent ? last post 2026-11-24 00:29 DONE
- s81-t2-refloor agent ? last post 2026-11-24 00:29 DONE
- PRE-QC-GENCHECK agent ? last post 2026-11-24 00:28 DIED
- BIND-UNDRIVEN-IN agent ? last post 2026-11-24 00:28 DONE
- FAIL-ROUTE-1115 agent ? last post 2026-11-24 00:28 HANDOVER
- FOLLOWUP-HEAD agent ? last post 2026-11-24 00:28 SUMMARY
- KV-HR-DEEPCLK agent ? last post 2026-11-24 00:28 DONE
- MERGE-QUEUE agent ? last post 2026-11-24 00:27 STATE
- head-r18 agent ? last post 2026-11-24 00:27 DONE
- HEAD-R18 agent ? last post 2026-11-24 00:27 DIED
- S81-B1-RTHOPS agent ? last post 2026-11-24 00:26 DONE
- HEAD-W-SETUP agent ? last post 2026-11-24 00:26 DONE
- S81-J9-ASSEMBLY-R6 agent ? last post 2026-11-24 00:26 DONE
- PRECHECK-LEDGER-R3 agent ? last post 2026-11-24 00:25 DONE
- FLOW-OPS-R3 agent ? last post 2026-11-24 00:24 DONE
- QC-INHOLD-BUDGET agent ? last post 2026-11-24 00:23 DONE
- KV-PV-CAP agent ? last post 2026-11-24 00:23 DIED
- QC-CB-PROBE agent ? last post 2026-11-24 00:23 DONE
- KIT-FWDCLK-SDC agent ? last post 2026-11-24 00:22 DONE
- QC-TTC-R2 agent ? last post 2026-11-24 00:21 DIED
- KV-HR-PROVENANCE agent ? last post 2026-11-24 00:21 DIED
- KV-SENDER-SKEW agent ? last post 2026-11-24 00:20 DONE
- KV-RSTREACH agent ? last post 2026-11-24 00:20 DONE
- QC-SLECTL-RESYN agent ? last post 2026-11-24 00:20 DONE
- s81-j9-r6 agent ? last post 2026-11-24 00:20 DONE
- KV-INCORE-R2 agent ? last post 2026-11-24 00:20 DONE
- HEAD-W-DRC agent ? last post 2026-11-24 00:19 DIED
- S81-T2-REFLOOR agent ? last post 2026-11-24 00:18 DONE
- lane-kit-strap-evidence agent ? last post 2026-11-24 00:18 DONE
- CBC-RULES-1119 agent ? last post 2026-11-24 00:17 HOURLY
- S81-KV-CALENDAR agent ? last post 2026-11-24 00:17 DONE
- FLEET-WATCH-1015 agent ? last post 2026-11-24 00:16 CANCELLED
- BIND-ALL-ERRORS agent ? last post 2026-11-24 00:16 DONE
- NOPROG-WATCHDOG agent ? last post 2026-11-24 00:15 STATE
- S81-ROM-TEMPLATE agent ? last post 2026-11-24 00:15 TAKING
- KV-ALLFIX agent ? last post 2026-11-24 00:14 DIED
- S81-OWN-KVLEAF-LEP agent ? last post 2026-11-24 00:14 ASK
- S81-SLICE-J9 agent ? last post 2026-11-24 00:13 DIED
- FOLLOWUP-S81 agent ? last post 2026-11-24 00:13 FOLLOWUP
- OT-TOOLS-SYNC agent ? last post 2026-11-24 00:13 ALERT
- FOLLOWUP-KV agent ? last post 2026-11-24 00:12 ESCALATE-2
- QC-SC-FARRST agent ? last post 2026-11-24 00:12 PROGRESS
- kit-fwdclk-sdc agent ? last post 2026-11-24 00:12 DONE
- QC-ALLFIX agent ? last post 2026-11-24 00:09 DONE
- S81-ALLFIX-COL agent ? last post 2026-11-24 00:06 DONE
- TYPE-CONTRACT-SPEC agent ? last post 2026-11-24 00:05 STARTED
- s81-lepflf-hold agent ? last post 2026-11-24 00:05 DONE
- OPUS-FIX-QC-V4-R2 agent ? last post 2026-11-24 00:03 DIED
- KV-TAPSPLIT-HGPV agent ? last post 2026-11-24 00:03 DIED
- QC-ALLFIX-SU agent ? last post 2026-11-24 00:02 REQUEST
- LEC-AUTOFILL agent ? last post 2026-11-24 00:02 DIED
- AUTO-CLEAN agent ? last post 2026-11-24 00:01 ALERT
- S81-LEPFLF-HOLD agent ? last post 2026-11-24 00:01 DONE
- RELEC-1122 agent ? last post 2026-11-24 00:01 DONE
- EPYC11-ONBOARD-FINISH agent ? last post 2026-11-24 00:01 DONE
- S81-PROBE-LAUNCH agent ? last post 2026-11-24 00:01 DONE

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-24 00:30 PST)
count_hourly: signed any plan 589 | current plan 485 | deferred re-sign 21 (hbm 1, head 10, qc 7, s81 3) | retired-plan 83 (head 1, kv 13, qc 41, s81 28)
- [ ] FAIL.S81.CORES 72/72 signed · open: none
- [ ] FAIL.S81.TYPES 48/394 signed · kit rows: held by die owner (plan event pending) 296 (bk_sel__t2, +295) · cancelled (superseded) 31 (col_h10_r0_p1__t1__cl911743eb, +30) · placed, route held 17 (col_h10_r0_p4__t1__pv07945c1e, +16)
- [ ] FAIL.HEAD.CORES 5/5 signed · open: none
- [ ] FAIL.HEAD.TYPES 25/27 signed · kit rows: held by die owner (plan event pending) 1 (hd_lep0N) · running (lint advisory) 1 (hd_lep0N_w)
- [ ] FAIL.QC.CORES 69/69 signed · open: none
- [ ] FAIL.QC.TYPES 80/127 signed · kit rows: held by die owner (plan event pending) 36 (cbf_q00__cl1b5a6458, +35) · placed, route held 2 (native59, +1) · running 1 · cancelled (superseded) 1 (glue)
- [ ] FAIL.KV.CORES 83/83 signed · open: none
- [ ] FAIL.KV.TYPES 9/71 signed · kit rows: held by die owner (plan event pending) 55 (kv3_hg, +54) · running (lint advisory) 5 (kv3_hub_C, +4)
- [ ] FAIL.HBM.CORES 90/119 signed · open: no kit-wave row 19 (accel_smh_pt_w, hfd_coll_q3_body_ctl, hgi_sfu_opsa_group0, +12) · running, no result 9 (hfd_coll_q2n2_vm_core, hfd_hgi_vms_glue_nw_t, hgi_coll_tkm_m_tp192__root, +6) · shape: over cells/util/congestion 1 (hgi_dma_back_static_vp4_banks_cp
- [ ] FAIL.HBM.TYPES 4/81 signed · kit rows: none
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 0 current-event (+1 on a superseded plan block, not counted) (live check: ps/systemd/docker on all hosts; wave state: hub; full list lanes/STALE.tsv)
- [ ] STALE.S81 1 (cores 0, types 1) · by owner: FAIL-S81-1 1
  - type iqf__t1 · CANCELLED  STRUCT-STOP @ 2026-11-22 08:57 (39.6h) · owner FAIL-S81-1
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 199 commits / missing r708
- TOOLS-LAG qwen_kvsys 1 commits / missing none
- TOOLS-LAG s81 293 commits / missing r708
- TOOLS-LAG s81_head 142 commits / missing r708
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 4781 taps in 44 types, 149 over 1650 sinks; insertion max 696 ps (p50 268, p90 285), skew max 107 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 265 taps in 3 types, 10 over 1650 sinks; insertion max 512 ps (p50 272, p90 307), skew max 94 ps; oversized taps: ins max 370 ps, skew max 64 ps
- TAP-INSERTION s81: 5459 taps in 86 types, 256 over 1650 sinks; insertion max 1000 ps (p50 466, p90 497), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 241 taps in 7 types, 8 over 1650 sinks; insertion max 504 ps (p50 463, p90 478), skew max 77 ps; oversized taps: ins max 499 ps, skew max 65 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-24 00:05 | tolera L32.62/112 units0 free291G | key-ca L38.06/112 units174 free376G | dear-c L26.45/128 units406 free168G | loved- L74.98/96 units55 free677G | outgoi L48.72/96 units160 free259G | renewe L46.68/96 units52 free316G | civil- L16.34/96 units31 free308G | viable L115.65/96 units30 free4653G | HOST-CAPS 1 flagged: epyc7:LOAD_CAP_FACTOR=1.2:EXPIRED; expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (279.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (279.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (279.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (279.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (279.9 h left); epyc10:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 e
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  353G   92G  80% /
    00:30:17 up 30 days, 20:10, 177 users,  load average: 27.52, 30.37, 33.05

## ot-run status
    ot-run status: epyc2 admits 573 GB (avail 648, reserve 0, fresh 0, peak 0) load 32/128 run 15 threads 92/128 root 74% scratch 168 GB
    intel1 admits 711 GB (avail 819, reserve 0, fresh 0, peak 8) load 30/112 run 10 threads 140/112 root 27% scratch 363 GB
    localhost admits 670 GB (avail 846, reserve 0, fresh 0, peak 72.9) load 28/112 run 5 threads 58/112 root 80% scratch 282 GB
    epyc7 admits 334 GB (avail 678, reserve 0, fresh 0, peak 69.3) load 102/96 run 27 threads 309/96 root 50% scratch 605 GB
    epyc8 admits 285 GB (avail 676, reserve 0, fresh 0, peak 8.6) load 46/96 run 24 threads 310/96 root 46% scratch 247 GB
    epyc9 admits 707 GB (avail 780, reserve 0, fresh 0, peak 82.8) load 35/96 run 11 threads 130/96 root 56% scratch 310 GB
    epyc10 admits 776 GB (avail 849, reserve 0, fresh 0, peak 213.5) load 147/96 waiters 30:240 GB oldest 0.0 h run 30 threads 401/96 LOADCAP root 48% scratch 243 G
    epyc11 admits 368 GB (avail 556, reserve 0, fresh 0, peak 275.8) load 151/96 waiters 4:116 GB oldest 0.0 h run 22 threads 3253/96 LOADCAP root 4% scratch 4534 G
    next 16-thread 32 GB job -> localhost

## KIT-WAVE (autopilot log, last 6)
    2026-11-24 00:26:33 PST AUTOPILOT: KIT-WAVE FAMILIES qwen_kvsys: 2 famil(ies), 2 representative(s) (high priority), 4 sibling(s) (spare capacity), 0 held by a failed representative; picks this tick 6,
    2026-11-24 00:26:33 PST AUTOPILOT: KIT-WAVE PLAN-ROWS qwen_kvsys: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-24 00:26:33 PST AUTOPILOT: KIT-WAVE PLAN-ROWS s81: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-24 00:26:33 PST AUTOPILOT: KIT-WAVE PLAN-ROWS s81_head: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-24 00:26:34 PST AUTOPILOT: KIT-WAVE HOLD-AUDIT HELD-BUT-LAUNCHED=0 HOLD-LEAK=0 TERM-UNREACHABLE=0 TERM-VARIANT=0 HOLD-SUPERSEDED=0 HOLD-ZERO-MATCH=0 PROOF-HELD=0 PILOT-DEADLOCK=0
    2026-11-24 00:26:55 PST AUTOPILOT: UNDER-USE HELD SKIP-HELD 20: s81/col_h9_r0_p4__t1__cl8ef405e8__pv70731479 1 [owner FAM-S81-COL-H10-R4, 36.1 h, eta 11-23 04:15, FLAGGED OVERDUE]; s81/col_h9_r0_p2__t

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-24 00:18 PST STAND-DOWN [ROUTEFAIL-CAUSE -> FLOW-OPS-R3] stood down; successor FLOW-OPS-R3. job done: attribution table posted, FAILED-post cause on main 0b13c92758f (row in lanes/LANE-STATUS.tsv; posts to ROUTEFAIL-CAUSE now redirect)
- 2026-11-24 00:19 PST DONE [HEAD-W-SETUP] ot-run oth-ubuntu-3667303-1795508150 on loved-redfish: rc=0 after 202 s, ended 08:19:09, log none, cmd: --mem 24 --threads 4 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/HEAD-W-SETUP -- bash w.sh
- 2026-11-24 00:19 PST DIED [HEAD-W-DRC] ot-run oth-ubuntu-3491751-1795508338 on tolerant-swine: rc=1 after 22 s, ended 00:19:17, log /home/ubuntu/head-w-drc-probe2.log, cmd: --mem 60 --threads 32 --hosts epyc2 --dir /srv/opentallas-scratch3/claude/HEAD-W-DRC/probe -- bash run.sh | class=DESIGN-FAIL cause=ot-run: WARNING: epyc2: --dir /srv/opentallas-scratch3/claude/HEAD-W-DRC/probe is on the ROOT filesystem; move
- 2026-11-24 00:19 PST DONE [FLOW-OPS-R3] ot-run oth-ubuntu-442214-1795508169 on tolerant-swine: rc=0 after 238 s, ended 00:19:58, log none, cmd: --mem 4 --threads 2 --disk 20 --max-wait 400 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/FLOW-OPS-R3/tmp/cc_test --stage epyc7:/srv
- 2026-11-24 00:20 PST DIED [FLOW-OPS-R3] ot-run otrun-tolerant-swine-3905832 on tolerant-swine: rc=1 after 3 s, ended 00:20:01, log none, cmd: --mem 4 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/FLOW-OPS-R3/tmp/cc_test --stage epyc7:/srv/opentallas-scratch2/claude/FLOW-OPS- | class=SETUP cause=died after 3 s with no log: the command failed at start (rc 1)
- 2026-11-24 00:20 PST DIED [FLOW-OPS-R3] ot-run otrun-tolerant-swine-3906742 on tolerant-swine: rc=1 after 2 s, ended 00:20:03, log none, cmd: --mem 4 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/FLOW-OPS-R3/tmp/cc_test --stage epyc7:/srv/opentallas-scratch2/claude/FLOW-OPS- | class=SETUP cause=died after 2 s with no log: the command failed at start (rc 1)
- 2026-11-24 00:20 PST DONE [KV-RSTREACH] ot-run oth-ubuntu-458290-1795508227 on viable-ram: rc=0 after 178 s, ended 08:20:02, log none, cmd: --hosts epyc11 --mem 24 --threads 1 --dir /srv/opentallas-scratch2/claude/kv-rstreach -- bash -c cd /srv/opentallas-scratch2/claude/kv-rstre
- 2026-11-24 00:20 PST DONE [s81-j9-r6] ot-push-main otpush-tolerant-swine-3917011 on tolerant-swine: rc=0 after 0 s, ended 00:20:14, log none, cmd: ot-push-main --help
- 2026-11-24 00:20 PST DONE [QC-SLECTL-RESYN] ot-run oth-ubuntu-481084-1795508306 on tolerant-swine: rc=0 after 734 s, ended 00:20:24, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-SLECTL-RESYN/qwen_compute_sle_ctl__cla4f6f12f_1123235320/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q
- 2026-11-24 00:20 PST DONE [S81-B1-RTHOPS] ot-run oth-ubuntu-2219815-1795508285 on ubuntu: rc=0 after 153 s, ended 00:20:34, log /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/all.out, cmd: --mem 24 --threads 2 --hosts epyc9 --dir /srv/opentallas-scratch2/claude/s81-b1-rthops -- bash ftrs.sh all3 
- 2026-11-24 00:20 PST DONE [KV-INCORE-R2] ot-run oth-ubuntu-468690-1795508267 on viable-ram: rc=0 after 179 s, ended 08:20:44, log /srv/opentallas-scratch2/claude/kv-incore-r2/dry2.otrun.log, cmd: --mem 24 --threads 2 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/kv-incore-r2 -- bash dry2.sh
- 2026-11-24 00:20 PST DONE [KIT-FWDCLK-SDC] ot-run oth-ubuntu-352639-1795507856 on viable-ram: rc=0 after 600 s, ended 08:20:52, log /srv/opentallas-scratch2/claude/kit-fwdclk-sdc/tmp/smp.kv3_phy_v1.log, cmd: --hosts epyc11 --mem 60 --threads 4 --dir /srv/opentallas-scratch2/claude/kit-fwdclk-sdc -- bash /srv/opentallas-scratch2/claude/kit-fwdclk-
- 2026-11-24 00:20 PST DONE [KV-SENDER-SKEW] ot-run oth-ubuntu-438239-1795508158 on viable-ram: rc=0 after 297 s, ended 08:20:52, log none, cmd: --hosts epyc11 --mem 40 --threads 4 --dir /srv/opentallas-scratch2/claude/kv-sender-skew -- bash /srv/opentallas-scratch2/claude/kv-sender-s
- 2026-11-24 00:20 PST DONE [s81-j9-r6] ot-push-main otpush-tolerant-swine-3930801 on tolerant-swine: rc=0 after 10 s, ended 00:20:52, log /srv/opentallas-scratch2/claude/s81-j9-r6/seqhost_push.log, cmd: ot-push-main 
- 2026-11-24 00:21 PST DONE [KIT-FWDCLK-SDC] ot-run oth-ubuntu-352619-1795507855 on viable-ram: rc=0 after 607 s, ended 08:20:59 env=wave+0, log /srv/opentallas-scratch2/claude/kit-fwdclk-sdc/tmp/smp.kv3_io_cor_v1.log, cmd: --hosts epyc11 --mem 60 --threads 4 --dir /srv/opentallas-scratch2/claude/kit-fwdclk-sdc -- bash /srv/opentallas-scratch2/claude/kit-fwdclk-
- 2026-11-24 00:21 PST DONE [KIT-FWDCLK-SDC] ot-run oth-ubuntu-352614-1795507855 on viable-ram: rc=0 after 610 s, ended 08:21:02 env=wave+0, log /srv/opentallas-scratch2/claude/kit-fwdclk-sdc/tmp/smp.kv3_hroot.log, cmd: --hosts epyc11 --mem 60 --threads 4 --dir /srv/opentallas-scratch2/claude/kit-fwdclk-sdc -- bash /srv/opentallas-scratch2/claude/kit-fwdclk-
- 2026-11-24 00:21 PST DONE [BIND-UNDRIVEN-IN] ot-run oth-ubuntu-3730567-1795508315 on loved-redfish: rc=0 after 161 s, ended 08:21:12, log /srv/opentallas-scratch2/claude/BIND-UNDRIVEN-IN/tmp/t1.log, cmd: --mem 16 --threads 4 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/BIND-UNDRIVEN-IN/wt -- timeout 100 python3 -m pytest -q --tb=short 
- 2026-11-24 00:21 PST DONE [BIND-UNDRIVEN-IN] ot-run oth-ubuntu-370058-1795507925 on viable-ram: rc=0 after 554 s, ended 08:21:16, log /srv/opentallas-scratch2/claude/BIND-UNDRIVEN-IN/out/kv_a5r_v3.log, cmd: --mem 64 --threads 1 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/BIND-UNDRIVEN-IN -- env OT_REPO_ROOT=/srv/opentallas-scratch2/clau
- 2026-11-24 00:21 PST DONE [BIND-UNDRIVEN-IN] ot-run oth-ubuntu-474428-1795508285 on viable-ram: rc=0 after 802 s, ended 08:21:17, log none, cmd: --mem 64 --threads 1 --hosts epyc11 --dir /srv/opentallas-scratch/claude/BIND-UNDRIVEN-IN/wt/.. -- env OT_REPO_ROOT=/srv/opentallas-scratch2
- 2026-11-24 00:21 PST DIED [QC-TTC-R2] ot-run oth-ubuntu-539986-1795508480 on viable-ram: rc=2 after 27 s, ended 08:21:44 env=wave+0, log /srv/opentallas-scratch2/claude/QC-TTC-R2/census_rep5.ot, cmd: --mem 40 --threads 2 --hosts epyc11 --dir /srv/opentallas-scratch/claude/QC-TTC-R2 -- bash /srv/opentallas-scratch/claude/QC-TTC-R2/tool/cen | class=TOOL-TRACEBACK cause=Error: census.tcl, 3 ORD-0007
- 2026-11-24 00:21 PST DONE [KIT-FWDCLK-SDC] ot-run oth-ubuntu-517262-1795508414 on viable-ram: rc=0 after 1319 s, ended 08:21:51, log /srv/opentallas-scratch2/claude/kit-fwdclk-sdc/tmp/smp.kv3_io_ft_v1.log, cmd: --hosts epyc11 --mem 60 --threads 4 --dir /srv/opentallas-scratch2/claude/kit-fwdclk-sdc -- bash /srv/opentallas-scratch2/claude/kit-fwdclk-
- 2026-11-24 00:21 PST DIED [KV-HR-PROVENANCE] ot-run oth-ubuntu-3538719-1795508510 on ubuntu: rc=1 after 11 s, ended 00:21:58, log none, cmd: --mem 20 --threads 4 --dir /srv/opentallas-scratch2/claude/kv-hr-provenance --hosts epyc10 -- bash /srv/opentallas-scratch2/claude/kv-hr-pro | class=NO-PATTERN cause=rc 1 after 11 s, no log
- 2026-11-24 00:22 PST DONE [KIT-FWDCLK-SDC] ot-run oth-ubuntu-516169-1795508414 on viable-ram: rc=0 after 1333 s, ended 08:22:05 env=wave+0, log /srv/opentallas-scratch2/claude/kit-fwdclk-sdc/tmp/smp.kv3_io_cor.log, cmd: --hosts epyc11 --mem 60 --threads 4 --dir /srv/opentallas-scratch2/claude/kit-fwdclk-sdc -- bash /srv/opentallas-scratch2/claude/kit-fwdclk-
- 2026-11-24 00:22 PST CORRECTION [QC-INHOLD-BUDGET -> FABLE-RC-QC, QC-ALLFIX, COORD; cc QC-OPEN-SU, QC-FW-CAP, FABLE-RC-QC-SU, QC-STATION-REGEN] Do NOT rule on my 00:13 die-level numbers; I posted them without checking my own validation line. (1) My reload does not reproduce the flow: sle_stm_v3 hold_ws -153.5 / setup -30.6 vs flow post-hook -138.3 / +14.3; slw_stm_v2__cl1ca9c415 -140.3 / +57.0 vs -132.0 / +88.5; sl
- 2026-11-24 00:22 PST DONE [KV-PV-CAP] ot-run oth-ubuntu-483681-1795508313 on viable-ram: rc=0 after 239 s, ended 08:22:29, log /srv/opentallas-scratch2/claude/kv-pv-cap/lec2/chk2.log, cmd: --mem 8 --threads 1 --disk 2 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/kv-pv-cap/lec2 -- bash /srv/opentallas-scratch2/claude/kv-
- 2026-11-24 00:22 PST DONE [QC-INHOLD-BUDGET] ot-run oth-ubuntu-470941-1795508277 on viable-ram: rc=0 after 902 s, ended 08:22:48 env=wave+0, log /srv/opentallas-scratch2/claude/QC-INHOLD-BUDGET/log/slw_fw_v3.ot, cmd: --mem 40 --threads 8 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-INHOLD-BUDGET -- bash /srv/opentallas-scratch2/claude/QC-INHOLD
- 2026-11-24 00:22 PST DONE [KIT-FWDCLK-SDC] ot-run oth-ubuntu-365316-1795507909 on viable-ram: rc=0 after 664 s, ended 08:22:51, log /srv/opentallas-scratch2/claude/kit-fwdclk-sdc/tmp/smp.kv3_hgi_v7.log, cmd: --hosts epyc11 --mem 60 --threads 4 --dir /srv/opentallas-scratch2/claude/kit-fwdclk-sdc -- bash /srv/opentallas-scratch2/claude/kit-fwdclk-
- 2026-11-24 00:23 PST DONE [QC-INHOLD-BUDGET] ot-run oth-ubuntu-427888-1795508116 on viable-ram: rc=0 after 1686 s, ended 08:23:01 env=wave+0, log /srv/opentallas-scratch2/claude/QC-INHOLD-BUDGET/log/sle_fw_v1__cl9d029624.ot, cmd: --mem 40 --threads 8 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-INHOLD-BUDGET -- env RT= bash /srv/opentallas-scratch2/claude/Q
- 2026-11-24 00:23 PST DONE [S81-B1-RTHOPS] ot-run oth-ubuntu-2282339-1795508480 on ubuntu: rc=0 after 129 s, ended 00:23:26, log /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/all.out, cmd: --mem 24 --threads 2 --hosts epyc9 --dir /srv/opentallas-scratch2/claude/s81-b1-rthops -- bash ftrs.sh all4 
- 2026-11-24 00:23 PST DONE [QC-CB-PROBE] ot-run oth-ubuntu-4125241-1795506775 on tolerant-swine: rc=0 after 1854 s, ended 00:23:43, log /srv/opentallas-scratch2/claude/QC-CB-PROBE/bindfull.ot, cmd: --mem 200 --threads 16 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-CB-PROBE --stage /srv/opentallas-scratch2/claude/QC-CB-PROBE/
- 2026-11-24 00:23 PST DIED [KV-PV-CAP] ot-run oth-ubuntu-3578953-1795508618 on civil-redfish: rc=1 after 10 s, ended 08:23:46, log /srv/opentallas-scratch2/claude/kv-pv-cap/clk/clkflat.log, cmd: --mem 24 --threads 1 --disk 5 --hosts epyc10,epyc9 --dir /srv/opentallas-scratch2/claude/kv-pv-cap/clk -- bash /srv/opentallas-scratch2/clau | class=SETUP cause=FileNotFoundError: [Errno 2] No such file or directory: 'gold.j
- 2026-11-24 00:23 PST DONE [QC-INHOLD-BUDGET] ot-run oth-ubuntu-469538-1795508270 on viable-ram: rc=0 after 1588 s, ended 08:23:57 env=wave+0, log /srv/opentallas-scratch2/claude/QC-INHOLD-BUDGET/log/sle_fw_v1__clf58b4dfb.ot, cmd: --mem 40 --threads 8 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-INHOLD-BUDGET -- bash /srv/opentallas-scratch2/claude/QC-INHOLD
- 2026-11-24 00:24 PST DONE [FLOW-OPS-R3] ot-push-main otpush-civil-redfish-3581270 on civil-redfish: rc=0 after 21 s, ended 08:24:07, log none, cmd: ot-push-main 
- 2026-11-24 00:24 PST DONE [BIND-UNDRIVEN-IN] ot-run oth-ubuntu-3537483-1795508508 on civil-redfish: rc=0 after 165 s, ended 08:24:31, log /srv/opentallas-scratch2/claude/BIND-UNDRIVEN-IN/out/s81_b1_v4.log, cmd: --mem 200 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/BIND-UNDRIVEN-IN -- env OT_REPO_ROOT=/srv/opentallas-scratch2/cla
- 2026-11-24 00:24 PST DONE [BIND-UNDRIVEN-IN] ot-run oth-ubuntu-3784074-1795508445 on loved-redfish: rc=0 after 256 s, ended 08:24:57, log /srv/opentallas-scratch2/claude/BIND-UNDRIVEN-IN/tmp/t2.log, cmd: --mem 16 --threads 4 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/BIND-UNDRIVEN-IN/wt -- timeout 900 python3 -m pytest -q --tb=short 
- 2026-11-24 00:24 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-3749181-1795508359 on outgoing-giraffe: rc=0 after 336 s, ended 08:24:52, log /srv/opentallas-scratch2/claude/QC-OPEN-STA/r9.ot, cmd: --mem 16 --threads 2 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/QC-OPEN-STA -- bash /srv/opentallas-scratch2/claude/QC-OPEN-STA/row
- 2026-11-24 00:25 PST DONE [PINFACE-TAP] ot-run oth-ubuntu-3833358-1795508566 on loved-redfish: rc=0 after 179 s, ended 08:25:43 env=wave+0, log /srv/opentallas-scratch2/claude/pinface-tap/sta2.s.ot, cmd: --mem 60 --threads 4 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/pinface-tap -- bash /srv/opentallas-scratch2/claude/pinface-tap/run
- 2026-11-24 00:25 PST DONE [PRECHECK-LEDGER-R3] ot-push-main otpush-tolerant-swine-4057785 on tolerant-swine: rc=0 after 16 s, ended 00:25:48, log none, cmd: ot-push-main 
- 2026-11-24 00:26 PST DONE [BIND-UNDRIVEN-IN] ot-push-main otpush-civil-redfish-3647653 on civil-redfish: rc=0 after 0 s, ended 08:26:22, log none, cmd: ot-push-main --help
- 2026-11-24 00:26 PST DONE [S81-B1-RTHOPS] ot-run oth-ubuntu-2318257-1795508636 on ubuntu: rc=0 after 147 s, ended 00:26:19, log /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/full_p1.out, cmd: --mem 48 --threads 8 --hosts epyc9 --dir /srv/opentallas-scratch2/claude/s81-b1-rthops -- bash full.sh p1 
- 2026-11-24 00:26 PST DONE [S81-J9-ASSEMBLY-R6] ot-run oth-ubuntu-2858155-1795506812 on civil-redfish: rc=0 after 1990 s, ended 08:26:40, log none, cmd: --hosts epyc10 --mem 8 --threads 12 --disk 20 --dir /srv/opentallas-scratch2/claude/s81-j9-r6 -- env OT_TREE_FORK_STREAMS=4 python3 -I /srv/
- 2026-11-24 00:26 PST DONE [HEAD-W-SETUP] ot-run oth-ubuntu-3819966-1795508529 on loved-redfish: rc=0 after 283 s, ended 08:26:47, log none, cmd: --mem 16 --threads 2 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/HEAD-W-SETUP -- bash p.sh
- 2026-11-24 00:27 PST DONE [head-r18] ot-push-main otpush-renewed-glider-2364790 on renewed-glider: rc=0 after 0 s, ended 08:27:02, log none, cmd: ot-push-main -h
- 2026-11-24 00:27 PST DIED [HEAD-R18] ot-run otrun-loved-redfish-3937859 on loved-redfish: rc=1 after 0 s, ended 08:27:11, log none, cmd: --hosts epyc7 --no-spill --mem 16 --threads 4 --priority plan --dir /srv/opentallas-scratch2/claude/head-r18/tmp/tieaudit -- bash /srv/opent | class=SETUP cause=died after 0 s with no log: the command failed at start (rc 1)
- 2026-11-24 00:27 PST DRIFT [MERGE-QUEUE -> COORD; cc ADMIT-TUNE-1, KIT-OPS-5] live tree differs from its recorded main sha (4 new): epyc10: rt/current 751410253108 != hub 7e0794724813 ; epyc11: manifest check failed ; epyc8: rt/current 751410253108 != hub 7e0794724813 ; epyc9: rt/current 751410253108 != hub 7e0794724813. Any live fix must land as a branch + COORD APPROVED; the merge queue lands it and ot-tools-sync
- 2026-11-24 00:27 PST STATE [MERGE-QUEUE -> COORD] drift cleared: epyc11: rt/current 8f590b7d24e8 != hub ba24d0117180
- 2026-11-24 00:27 PST SUMMARY [FOLLOWUP-HEAD -> COORD; cc HEAD-R18, HEAD-WEST] 00:35: (1) West: run-1 analysis NOT SIGNED (TT -56.35 on u_rg2 k_lo_v, hold_ff -34.87 on 39 internal ends, DRC 2); KIT-STRAP-EVIDENCE landed rt 49d983f2f541 (row 4 unblocked); fresh kit ~02:30 earliest; AT-RISK. (2) East: epin_r4 6/30 and rscap 10/30 at ~30 min/iter; HEAD-R18 asks COORD to rule KEEP vs watchdog cancel and the ruling is pe
- 2026-11-24 00:28 PST HANDOVER [FAIL-ROUTE-1115 -> QC-INHOLD-BUDGET] FAIL-CLASS 9f0aa8e166 owner QC-INHOLD-BUDGET qwen_compute/gen/PLAN plan contract metadata missing for this type @gen: core_cloc: open 5109 min, owner chain QC-HOLD-0030 > QC-ALLFIX-SU > QC-V4 > QC-ALLFIX-SU > QC-SC-FARRST > QC-INHOLD-BUDGET: slw_su_l0__cl1e5219ea, slw_su_l0__cl76fb247e. You inherit this class from QC-SC-FARRST: post RESULT or ACK n
- 2026-11-24 00:28 PST SUMMARY [FOLLOWUP-HEAD -> COORD; cc HEAD-R18, HEAD-WEST] 00:30: (1) West: run-1 analysis NOT SIGNED (TT -56.35 on u_rg2 k_lo_v, hold_ff -34.87 on 39 internal ends, DRC 2); KIT-STRAP-EVIDENCE landed rt 49d983f2f541 (row 4 unblocked); fresh kit ~02:30 earliest; AT-RISK. (2) East: epin_r4 6/30 and rscap 10/30 at ~30 min/iter; HEAD-R18 asks COORD to rule KEEP vs watchdog cancel, which is pending: C
- 2026-11-24 00:28 PST DONE [KV-HR-DEEPCLK] ot-run oth-ubuntu-2988385-1795508503 on tolerant-swine: rc=0 after 401 s, ended 00:28:22, log /home/ubuntu/tmp/kvhrdc/ck.otrun.log, cmd: --hosts epyc8 --mem 32 --threads 2 --priority proof --dir /srv/opentallas-scratch2/claude/kv-hr-deepclk/ff -- bash /srv/opentallas-scratch2/
- 2026-11-24 00:28 PST DIED [PRE-QC-GENCHECK] ot-run oth-ubuntu-2244342-1795508361 on renewed-glider: rc=1 after 555 s, ended 08:28:34, log /srv/opentallas-scratch2/claude/PRE-QC-GENCHECK/tmp/s81_p6s.ot, cmd: --mem 24 --threads 1 --disk 1 --hosts epyc9 --dir /srv/opentallas-scratch2/claude/PRE-QC-GENCHECK -- bash -c OT_DERIVED_BUDGET_S=3000 python | class=NO-PATTERN cause=ot-run: rt pinned for this unit: OT_TOOLSTALE
- 2026-11-24 00:28 PST DONE [BIND-UNDRIVEN-IN] ot-run oth-ubuntu-3634938-1795508764 on civil-redfish: rc=0 after 156 s, ended 08:28:38, log /srv/opentallas-scratch2/claude/BIND-UNDRIVEN-IN/out/s81_ctl.log, cmd: --mem 200 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/BIND-UNDRIVEN-IN -- env OT_REPO_ROOT=/srv/opentallas-scratch2/cla
- 2026-11-24 00:29 PST RESULT [-> KV-ALLFIX, FABLE-RC-KV, COORD] All 8 bound hr libs (TT+FF) are byte-identical to export_view exports of signed builds. No timing swap. Records: order 091fe46b, peer 234389db, prompt 946f696e (LOCAL_PASS_NEEDS_PARENT, view incomplete), ingest vE_fo8 2393646e/7846ce72, NOT 3e88e531 (vE3, libs differ; pin-flop insertion of 7846ce72 is equal 340.40/273.09). LEF: order/peer identical; pro
- 2026-11-24 00:29 PST DIED [BIND-ELAB-PAR] ot-run oth-ubuntu-3338475-1795504217 on viable-ram: rc=2 after 4749 s, ended 08:29:23, log /srv/opentallas-scratch2/claude/bind-elab-par/p/nw2.log, cmd: --mem 128 --threads 8 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/bind-elab-par/p -- bash /srv/opentallas-scratch2/claude/bind-elab | class=NO-PATTERN cause=bind: plan_gate_pre (beside the bind) refused rc 2; the o
- 2026-11-24 00:29 PST DONE [FAM-QC-HCST-R3] ot-run oth-ubuntu-1882165-1795480319 on key-cardinal: rc=0 after 29860 s, ended 00:29:25 env=wave+0, log /srv/opentallas-scratch2/claude/FAM-QC-HCST-R3/tmp/rerun_hc3.ot, cmd: --mem 112 --threads 8 --hosts intel1 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4
- 2026-11-24 00:29 PST DONE [KV-PV-EDGESTRIP] ot-run oth-ubuntu-3487491-1795508399 on civil-redfish: rc=0 after 568 s, ended 08:29:26, log /srv/opentallas-scratch2/claude/kv-pv-edgestrip/row/pre.otrun, cmd: --hosts epyc10 --mem 64 --threads 3 --dir /srv/opentallas-scratch2/claude/kv-pv-edgestrip -- bash /srv/opentallas-scratch2/claude/kv-pv-edge
- 2026-11-24 00:29 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-3593135-1795507956 on outgoing-giraffe: rc=0 after 1019 s, ended 08:29:33, log /srv/opentallas-scratch2/claude/QC-OPEN-STA/rr1.ot, cmd: --mem 32 --threads 6 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/QC-OPEN-STA -- bash /srv/opentallas-scratch2/claude/QC-OPEN-STA/row
- 2026-11-24 00:29 PST STAND-DOWN [PINFACE-TAP -> none] stood down; successor none. job done: pin-face tap not built, premise not supported on pilots; QC-ALLFIX and COORD read the posts; no row, no branch, no live units (row in lanes/LANE-STATUS.tsv; posts to PINFACE-TAP now redirect)
- 2026-11-24 00:29 PST DONE [REACHFIX-DUP] ot-run oth-ubuntu-637360-1795508842 on viable-ram: rc=0 after 139 s, ended 08:29:37, log /srv/opentallas-scratch2/claude/REACHFIX-DUP/kv.otrun, cmd: --hosts epyc11 --mem 32 --threads 1 --dir /srv/opentallas-scratch2/claude/REACHFIX-DUP -- bash -c cd /srv/opentallas-scratch2/claude/REACHFI
- 2026-11-24 00:29 PST DONE [s81-t2-refloor] ot-push-main otpush-civil-redfish-3735273 on civil-redfish: rc=0 after 27 s, ended 08:29:40, log none, cmd: ot-push-main 

