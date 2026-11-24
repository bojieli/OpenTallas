# COORD snapshot 2026-11-24 01:00 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: 85273876e25a
- 2026-11-23 15:15 PST MERGED [MERGE-QUEUE -> LAUNCH-GUARD] claude/launch-guard-viewpack-stage-1123@349ec165e6e -> main 005831fc27c -> ed4f6ade31b, no-ff merge, tags flow-20261117-mv-*. Gate: gate record from renewed-glider 2026-11-23 23:13 UTC on main becebaf53d9 (main since: no overlap): 8 test file(s) pass (+1 source dir(s) the tests name: physical/die_plan/hbm_arch_cores) (1 failure(s) also fail on main: baseline
- 2026-11-23 15:25 PST MERGED [MERGE-QUEUE -> LAUNCH-GUARD] claude/launch-guard-ghost-signed-1123@7a15228190e -> main ed4f6ade31b -> d0beea9d604, no-ff merge, tags flow-20261117-mw-*. Gate: gate record from renewed-glider 2026-11-23 23:24 UTC on main ed4f6ade31b: 184 test file(s) pass (+6 source dir(s) the tests name: physical/die_plan physical/die_plan/hbm/cores/harden physical/die_plan/hbm/cores/ports physical/die_
- 2026-11-23 15:25 PST MERGED [MERGE-QUEUE -> KV-D29-EMITGAPS] claude/kv-d29-emitgaps-1123@a4b13024a9a -> main d0beea9d604 -> bd54869e80c, no-ff merge, tags flow-20261117-mx-*. Gate: gate record from renewed-glider 2026-11-23 23:21 UTC on main ed4f6ade31b: 76 test file(s) pass (+18 source dir(s) the tests name: physical/asap7_memory_macros physical/asap7_memory_macros_pa physical/asap7_memory_macros_v2 physical/die_p

## READY/ASK with no later COORD post naming them (1, heuristic: check each)
- 2026-11-24 00:14 PST ASK [S81-OWN-KVLEAF-LEP -> S81-ALLFIX-SLICE; cc S81-ALLFIX-INT, COORD] Does KVLEAF-STA-REACH-1 e66dc414f41a (or any row) already hold the CBC station for kv_leaf t3 vn rb_v_c -> u_x.q[21] (-329, 610 um)? If yes, give the op key and I will not build it. If no, I draft it: payload group = all u_x.q bits launched from rb_v_c plus valid, one registered cut at mid-hop, +1 cycle on t3 only; plan in l

## Lane handoff files (age) and last queue post
- CLASS-FIX-RHI: handoff 1328 min old; last post 2026-11-23 09:12 DONE
- CLEAN-AGGR-R3: handoff 1408 min old; last post 2026-11-23 00:39 DONE
- CODEX-TOKEN-1123: handoff 460 min old; last post none in recent queue
- EPYC11-ONBOARD-FINISH: handoff 35 min old; last post 2026-11-24 00:01 DONE
- EXPLORER-STORE-R1: handoff 1248 min old; last post none in recent queue
- FABLE-OPEN-HEAD-QC: handoff 845 min old; last post 2026-11-23 10:54 REPORT-2
- FABLE-OPEN-KV: handoff 422 min old; last post 2026-11-23 18:32 DONE
- FABLE-OPEN-S81-A-rc37: handoff 549 min old; last post none in recent queue
- FABLE-OPEN-S81-A-x14: handoff 537 min old; last post none in recent queue
- FABLE-OPEN-S81-A: handoff 535 min old; last post 2026-11-23 16:03 DONE
- FABLE-OPEN-S81-B-rc72: handoff 1108 min old; last post none in recent queue
- FABLE-OPEN-S81-B-x9: handoff 813 min old; last post none in recent queue
- FABLE-OPEN-S81-B: handoff 549 min old; last post 2026-11-23 11:21 DONE
- FABLE-OPEN-S81-SVC: handoff 551 min old; last post 2026-11-23 14:54 DONE
- FABLE-RC-ALL-KV-QC-HANDOVER: handoff 336 min old; last post none in recent queue
- FABLE-RC-ALL: handoff 21 min old; last post 2026-11-23 17:05 DIED
- FABLE-RC-KV: handoff 19 min old; last post none in recent queue
- FABLE-RC-KVHEAD: handoff 1256 min old; last post 2026-11-23 02:38 DONE
- FABLE-RC-QC-SU: handoff 239 min old; last post none in recent queue
- FABLE-RC-QC: handoff 160 min old; last post 2026-11-23 01:26 DONE
- FABLE-RC-S81: handoff 1248 min old; last post 2026-11-23 04:11 RC-ACCEPT
- FABLE-UNC-HEAD: handoff 849 min old; last post 2026-11-23 04:00 GATE-PASS
- FABLE-UNC-KV: handoff 1263 min old; last post 2026-11-23 04:31 DONE
- FABLE-UNC-QC: handoff 1265 min old; last post 2026-11-23 04:48 DIED
- FABLE-UNC-S81-DIE: handoff 1313 min old; last post 2026-11-23 04:20 DONE
- FABLE-UNC-S81-LEAF: handoff 1120 min old; last post 2026-11-23 06:19 STATUS
- FABLE-UNC-S81-SVC: handoff 1251 min old; last post 2026-11-23 11:38 DONE
- FAM-KV-HUBC-SYSC-R2: handoff 847 min old; last post 2026-11-23 18:15 DIED
- FAM-KV-HUBWO-S1: handoff 176 min old; last post 2026-11-23 22:03 DONE
- FAM-S81-COL-H10-R4: handoff 1402 min old; last post 2026-11-23 04:30 DONE
- FAM-S81-COL-H9R0-R4: handoff 1342 min old; last post 2026-11-23 22:53 DIED
- FAM-S81-DSDV-R1: handoff 549 min old; last post 2026-11-23 10:02 DIED
- FAM-S81-SERDES-R7: handoff 1374 min old; last post 2026-11-23 05:46 DONE
- FAM-S81-SVC-OWN: handoff 1412 min old; last post 2026-11-23 23:24 DONE
- FIX-KV-PV-MESOFIFO: handoff 1333 min old; last post 2026-11-23 04:31 DONE
- FIX-LEDGER: handoff 526 min old; last post 2026-11-23 02:45 ASK
- FIX-QC-DPL-RERUN: handoff 1264 min old; last post 2026-11-23 04:32 DIED
- FIX-QC-STA-BTW: handoff 1244 min old; last post 2026-11-23 06:06 DONE
- FIX-S81-SVC-BCAST: handoff 1328 min old; last post 2026-11-23 17:05 DONE
- FIX-S81-SVC-LOSTART: handoff 1324 min old; last post 2026-11-23 11:06 DONE
- FIX-S81-SVC-WESTRIP: handoff 541 min old; last post 2026-11-23 15:58 CORRECTION
- FIX-S81-UCF-VIEW: handoff 1281 min old; last post 2026-11-23 04:20 DONE
- FIX-S81-XG-STN: handoff 1104 min old; last post 2026-11-23 12:31 DONE
- FIX-SYNC-QC: handoff 1349 min old; last post 2026-11-22 18:39 DIED
- FIX-SYNC-S81: handoff 1344 min old; last post 2026-11-22 18:26 DONE
- FLOW-CLKGRT-R2: handoff 525 min old; last post 2026-11-23 16:13 RESULT
- FLOW-OPS-R2: handoff 1307 min old; last post 2026-11-23 04:52 RESULT
- FLOW-OPS-R3-CODEX-1123: handoff 460 min old; last post none in recent queue
- FLOW-OPS-R3: handoff 18 min old; last post 2026-11-24 00:40 DONE
- GENDRY-KITRTL: handoff 247 min old; last post 2026-11-23 21:38 DONE
- HEAD-100-unit-table-signedview: handoff 1 min old; last post none in recent queue
- HEAD-100-unit-table: handoff 9 min old; last post none in recent queue
- HEAD-R18: handoff 88 min old; last post 2026-11-24 00:39 DONE
- HEAD-S2-RESEAL: handoff 223 min old; last post 2026-11-23 21:15 DONE
- HEAD-WEST: handoff 45 min old; last post 2026-11-23 23:29 DONE
- HOTSPOT-CENSUS: handoff 1390 min old; last post 2026-11-23 05:41 DONE
- HOURLY-WRITEUP-R5: handoff 1249 min old; last post none in recent queue
- KV-ALLFIX: handoff 427 min old; last post 2026-11-24 00:52 DONE
- KV-ASTK-EARLYTAP: handoff 140 min old; last post 2026-11-23 22:39 DONE
- KV-D29-PACKAGE: handoff 542 min old; last post none in recent queue
- KV-D29: handoff 204 min old; last post 2026-11-23 21:39 NOTE
- KV-DIE-SEAMHOLD: handoff 117 min old; last post 2026-11-23 23:01 DONE
- KV-HG-CAP: handoff 67 min old; last post 2026-11-23 22:26 DIED
- KV-HUB-EPZO: handoff 211 min old; last post 2026-11-23 21:29 STAND-DOWN
- KV-HUB-HOLD: handoff 152 min old; last post 2026-11-23 22:55 DONE
- KV-INCORE-R2: handoff 33 min old; last post 2026-11-24 00:20 DONE
- KV-OPEN-FWDCLK: handoff 278 min old; last post 2026-11-23 20:20 DIED
- KV-OPEN-INCORE: handoff 312 min old; last post 2026-11-23 20:20 DONE
- KV-PREGRT-STALL: handoff 233 min old; last post 2026-11-23 21:06 STAND-DOWN
- KV-PV-CAP: handoff 68 min old; last post 2026-11-24 00:44 DONE
- KV-PV-EDGESTRIP: handoff 45 min old; last post 2026-11-24 00:57 DIED
- KV-PV-RSTRELAY: handoff 119 min old; last post 2026-11-23 22:58 DONE
- KV-R8-LANELOSS: handoff 268 min old; last post 2026-11-23 20:32 STAND-DOWN
- KV-RCOLL-PHASE: handoff 189 min old; last post none in recent queue
- KV-RCOLL-REBASE: handoff 169 min old; last post 2026-11-23 22:08 DONE
- KV-RINGMAC-R1: handoff 550 min old; last post 2026-11-23 14:46 DIED
- KV-RSTNAME-REMAP: handoff 189 min old; last post 2026-11-23 21:48 DONE
- KV-RSTREACH: handoff 23 min old; last post 2026-11-24 00:53 DONE
- KV-SENDER-SKEW: handoff 31 min old; last post 2026-11-24 00:20 DONE
- KV-TAPSPLIT-HGPV: handoff 37 min old; last post 2026-11-24 00:56 DIED
- KVLEAF-MASTERS-from-ARCH-R2: handoff 336 min old; last post none in recent queue
- KVLEAF-MASTERS: handoff 134 min old; last post 2026-11-23 22:45 DONE
- LANDING-WRAP-TOOL: handoff 157 min old; last post 2026-11-23 22:22 LIVE
- LANDREMAP-RSTNODE: handoff 185 min old; last post 2026-11-23 21:56 STAND-DOWN
- LAUNCH-GUARD: handoff 459 min old; last post 2026-11-23 15:49 DONE
- LEAF-ROUTE-CBC: handoff 1370 min old; last post 2026-11-23 07:16 DONE
- LEC-AUTOFILL: handoff 127 min old; last post 2026-11-24 00:33 DIED
- LEC-VACUITY-SWEEP: handoff 87 min old; last post 2026-11-23 23:31 DIED
- NEARMISS-ECO-R1: handoff 1408 min old; last post 2026-11-23 05:01 DIED
- OPS-SUPPORT-R1: handoff 550 min old; last post 2026-11-23 20:03 EPYC8-FREED
- OPUS-FIX-HEAD-LEP0N-R8: handoff 1144 min old; last post 2026-11-22 20:05 DONE
- OPUS-FIX-HEAD-LEP0N-R9: handoff 1259 min old; last post 2026-11-23 10:31 DIED
- OPUS-FIX-KV-HG-R8: handoff 1260 min old; last post 2026-11-23 20:58 DIED
- OPUS-FIX-KV-PV-R7: handoff 559 min old; last post 2026-11-23 20:58 DIED
- OPUS-FIX-KV-PV-SINKSPREAD-R2: handoff 1379 min old; last post 2026-11-23 10:23 DONE
- OPUS-FIX-QC-COLL-R3: handoff 1397 min old; last post 2026-11-23 15:31 DIED
- OPUS-FIX-QC-V4-R2: handoff 377 min old; last post 2026-11-24 00:03 DIED
- OPUS-FIX-S81-COL-RANKSEAT-R2: handoff 1300 min old; last post 2026-11-23 16:32 DIED
- OPUS-FIX-S81-LEAF-R10: handoff 1356 min old; last post 2026-11-23 08:46 DIED
- OPUS-FIX-S81-LEAF-TAPHOLD-R2: handoff 1299 min old; last post 2026-11-23 04:39 DONE
- OPUS-KV-DIE-R2: handoff 1313 min old; last post 2026-11-23 03:07 STAND-DOWN
- OWN-KV-1123: handoff 1368 min old; last post none in recent queue
- OWN-QC-1123: handoff 1376 min old; last post none in recent queue
- PRE-QC-GENCHECK: handoff 40 min old; last post 2026-11-24 00:57 DONE
- PRECHECK-CELLCAP: handoff 104 min old; last post 2026-11-23 23:14 RT
- PRECHECK-DERIVED-DROP: handoff 145 min old; last post 2026-11-23 22:36 DONE
- PRECHECK-LEDGER-R3: handoff 327 min old; last post 2026-11-24 00:41 DONE
- PRECHECK-R2: handoff 1286 min old; last post 2026-11-23 04:16 DONE
- QC-ALLFIX-COLL: handoff 334 min old; last post 2026-11-23 18:47 DONE
- QC-ALLFIX-SU: handoff 418 min old; last post 2026-11-24 00:57 DONE
- QC-ALLFIX: handoff 393 min old; last post 2026-11-24 00:34 DONE
- QC-FW-CAP: handoff 159 min old; last post 2026-11-23 23:49 DONE
- QC-HC1-CLKENTRY: handoff 64 min old; last post 2026-11-24 00:45 DONE
- QC-OPEN-COLL: handoff 27 min old; last post 2026-11-23 21:47 DONE
- QC-OPEN-STA: handoff 26 min old; last post 2026-11-24 00:48 DONE
- QC-OPEN-SU: handoff 17 min old; last post 2026-11-23 23:37 DONE
- QC-SLECTL-RESYN: handoff 58 min old; last post 2026-11-24 00:20 DONE
- QC-STB-CAP: handoff 102 min old; last post 2026-11-23 23:15 DONE
- QC-SUL1-STN-ROW: handoff 187 min old; last post 2026-11-23 21:51 DONE
- QC-TTC-R2: handoff 31 min old; last post 2026-11-24 00:42 DONE
- QC-TTC-RETIME: handoff 297 min old; last post 2026-11-23 20:45 DONE
- QC-V4-CB: handoff 804 min old; last post 2026-11-23 14:06 DONE
- QC-V4-COLL: handoff 1111 min old; last post 2026-11-23 07:49 DONE
- QC-V4: handoff 137 min old; last post 2026-11-23 23:33 ADOPT-BIND
- RELEC-1122: handoff 17 min old; last post 2026-11-24 00:01 DONE
- S81-ALLFIX-COL: handoff 65 min old; last post 2026-11-24 00:06 DONE
- S81-ALLFIX-INT: handoff 445 min old; last post 2026-11-23 21:46 ANSWER
- S81-ALLFIX-MULTI: handoff 381 min old; last post 2026-11-23 18:38 NOTE
- S81-ALLFIX-SLICE: handoff 351 min old; last post 2026-11-23 19:56 DONE
- S81-ALLFIX-SVC-ENGMON: handoff 368 min old; last post none in recent queue
- S81-ALLFIX-SVC-L0: handoff 407 min old; last post none in recent queue
- S81-ALLFIX-SVC-MISC: handoff 436 min old; last post none in recent queue
- S81-ALLFIX-SVC-SERDESRING: handoff 254 min old; last post none in recent queue
- S81-ALLFIX-SVC: handoff 278 min old; last post 2026-11-23 21:44 REPORT
- S81-BKSEL-R7: handoff 1380 min old; last post 2026-11-23 11:22 DIED
- S81-COL-J9: handoff 544 min old; last post 2026-11-23 15:53 DONE
- S81-J9-ASSEMBLY-R6: handoff 36 min old; last post 2026-11-24 00:26 DONE
- S81-KVLEAF-T2-ARCH-R2: handoff 82 min old; last post 2026-11-24 00:56 DONE
- S81-KVLEAF-T2-ARCH: handoff 1247 min old; last post 2026-11-23 04:58 DONE
- S81-LEAF-J9: handoff 455 min old; last post 2026-11-23 17:22 DONE
- S81-LEPFLF-HOLD: handoff 121 min old; last post 2026-11-24 00:01 DONE
- S81-MISC-SERDES-J9: handoff 454 min old; last post 2026-11-23 17:05 DONE
- S81-OPEN-CLOCK: handoff 144 min old; last post 2026-11-23 21:58 DONE
- S81-OPEN-DEMAND: handoff 144 min old; last post 2026-11-23 20:59 DONE
- S81-OPEN-ENGCHAN: handoff 344 min old; last post none in recent queue
- S81-OPEN-FSTART: handoff 61 min old; last post 2026-11-23 22:17 DIED
- S81-OPEN-LEAFBAND: handoff 67 min old; last post 2026-11-23 23:42 DONE
- S81-OPEN-SVCLO: handoff 197 min old; last post 2026-11-23 21:41 DIED
- S81-OWN-KVLEAF-LEP: handoff 25 min old; last post 2026-11-24 00:14 ASK
- S81-PROBE-LAUNCH: handoff 61 min old; last post 2026-11-24 00:01 DONE
- S81-SLICE-J9: handoff 106 min old; last post 2026-11-24 00:36 DIED
- S81-SVC-J9: handoff 512 min old; last post 2026-11-23 16:01 DONE
- S81-T2-REFLOOR: handoff 313 min old; last post 2026-11-24 00:41 DONE
- S81-TYPES-CODEX-1123: handoff 460 min old; last post none in recent queue
- TAP-GRID-R5: handoff 1326 min old; last post 2026-11-23 04:29 DONE
- TAP-GRID-R6: handoff 513 min old; last post 2026-11-23 16:24 DONE
- TL-QCPHYSDB: handoff 1042 min old; last post none in recent queue
- UCF-VIEW-FIX: handoff 1255 min old; last post 2026-11-23 08:27 DONE
- VIS-DIE-S81: handoff 1111 min old; last post 2026-11-23 07:06 DONE
- VIS-KV: handoff 1402 min old; last post none in recent queue
- VIS-QC-QC-DIE-SEAT-1: handoff 1398 min old; last post none in recent queue
- VIS-QC: handoff 1266 min old; last post 2026-11-23 05:55 DIED
- VIS-S81-COL: handoff 1338 min old; last post 2026-11-23 08:00 DONE
- VIS-S81-MISC: handoff 1289 min old; last post 2026-11-23 04:33 DIED

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 168; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 68 live
- S81-ROM-TEMPLATE agent ? last post 2026-11-24 00:59 DONE
- QC-CB-PROBE agent ? last post 2026-11-24 00:59 DONE
- S81-B1-RTHOPS agent ? last post 2026-11-24 00:58 DONE
- PRE-QC-GENCHECK agent ? last post 2026-11-24 00:57 DONE
- QC-ALLFIX-SU agent ? last post 2026-11-24 00:57 DONE
- KV-PV-EDGESTRIP agent ? last post 2026-11-24 00:57 DIED
- KV-TAPSPLIT-HGPV agent ? last post 2026-11-24 00:56 DIED
- S81-KVLEAF-T2-ARCH-R2 agent ? last post 2026-11-24 00:56 DONE
- QC-SC-FARRST agent ? last post 2026-11-24 00:55 DONE
- S81-BOOTCONTRACT agent ? last post 2026-11-24 00:55 DONE
- QC-F16-PRODUCER agent ? last post 2026-11-24 00:54 DIED
- KV-RSTREACH agent ? last post 2026-11-24 00:53 DONE
- KV-ALLFIX agent ? last post 2026-11-24 00:52 DONE
- NOPROG-FIX-1115 agent ? last post 2026-11-24 00:52 STATE
- S81-KV-CALENDAR agent ? last post 2026-11-24 00:51 DONE
- QC-OPEN-STA agent ? last post 2026-11-24 00:48 DONE
- S81-OWN-SLICE agent ? last post 2026-11-24 00:48 DIED
- NOPROG-WATCHDOG agent ? last post 2026-11-24 00:45 STATE
- FLEET-WATCH-1015 agent ? last post 2026-11-24 00:45 NOTICE
- BIND-UNDRIVEN-IN agent ? last post 2026-11-24 00:45 DONE
- KV-HR-DEEPCLK agent ? last post 2026-11-24 00:45 DONE
- qwen_compute agent ? last post 2026-11-24 00:45 KIT-WAVE
- KV-OWN-HG agent ? last post 2026-11-24 00:45 DONE
- QC-HC1-CLKENTRY agent ? last post 2026-11-24 00:45 DONE
- KV-PV-CAP agent ? last post 2026-11-24 00:44 DONE
- QC-INHOLD-BUDGET agent ? last post 2026-11-24 00:43 DONE
- QC-TTC-R2 agent ? last post 2026-11-24 00:42 DONE
- PRECHECK-LEDGER-R3 agent ? last post 2026-11-24 00:41 DONE
- S81-T2-REFLOOR agent ? last post 2026-11-24 00:41 DONE
- KIT-FWDCLK-SDC agent ? last post 2026-11-24 00:40 DIED
- FLOW-OPS-R3 agent ? last post 2026-11-24 00:40 DONE
- HUB-POST-SPEED agent ? last post 2026-11-24 00:40 RESULT
- HEAD-W-SETUP agent ? last post 2026-11-24 00:39 DONE
- HEAD-R18 agent ? last post 2026-11-24 00:39 DONE
- MERGE-QUEUE agent ? last post 2026-11-24 00:37 STATE
- S81-SLICE-J9 agent ? last post 2026-11-24 00:36 DIED
- lane-kit-strap-evidence agent ? last post 2026-11-24 00:35 DONE
- QC-ALLFIX agent ? last post 2026-11-24 00:34 DONE
- LEC-AUTOFILL agent ? last post 2026-11-24 00:33 DIED
- BIND-ALL-ERRORS agent ? last post 2026-11-24 00:33 DONE
- HEAD-W-DRC agent ? last post 2026-11-24 00:33 DONE
- hub-git-sync agent ? last post 2026-11-24 00:32 FLEET
- BIND-ELAB-PAR agent ? last post 2026-11-24 00:29 DIED
- FAM-QC-HCST-R3 agent ? last post 2026-11-24 00:29 DONE
- s81-t2-refloor agent ? last post 2026-11-24 00:29 DONE
- FAIL-ROUTE-1115 agent ? last post 2026-11-24 00:28 HANDOVER
- FOLLOWUP-HEAD agent ? last post 2026-11-24 00:28 SUMMARY
- head-r18 agent ? last post 2026-11-24 00:27 DONE
- S81-J9-ASSEMBLY-R6 agent ? last post 2026-11-24 00:26 DONE
- KV-SENDER-SKEW agent ? last post 2026-11-24 00:20 DONE
- QC-SLECTL-RESYN agent ? last post 2026-11-24 00:20 DONE
- s81-j9-r6 agent ? last post 2026-11-24 00:20 DONE
- KV-INCORE-R2 agent ? last post 2026-11-24 00:20 DONE
- CBC-RULES-1119 agent ? last post 2026-11-24 00:17 HOURLY
- S81-OWN-KVLEAF-LEP agent ? last post 2026-11-24 00:14 ASK
- FOLLOWUP-S81 agent ? last post 2026-11-24 00:13 FOLLOWUP
- OT-TOOLS-SYNC agent ? last post 2026-11-24 00:13 ALERT
- FOLLOWUP-KV agent ? last post 2026-11-24 00:12 ESCALATE-2
- kit-fwdclk-sdc agent ? last post 2026-11-24 00:12 DONE
- S81-ALLFIX-COL agent ? last post 2026-11-24 00:06 DONE
- TYPE-CONTRACT-SPEC agent ? last post 2026-11-24 00:05 STARTED
- s81-lepflf-hold agent ? last post 2026-11-24 00:05 DONE
- OPUS-FIX-QC-V4-R2 agent ? last post 2026-11-24 00:03 DIED
- AUTO-CLEAN agent ? last post 2026-11-24 00:01 ALERT
- S81-LEPFLF-HOLD agent ? last post 2026-11-24 00:01 DONE
- RELEC-1122 agent ? last post 2026-11-24 00:01 DONE
- EPYC11-ONBOARD-FINISH agent ? last post 2026-11-24 00:01 DONE
- S81-PROBE-LAUNCH agent ? last post 2026-11-24 00:01 DONE

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-24 01:00 PST)
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
  - type iqf__t1 · CANCELLED  STRUCT-STOP @ 2026-11-22 08:57 (40.1h) · owner FAIL-S81-1
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 210 commits / missing r708
- TOOLS-LAG qwen_kvsys 0 commits / missing none
- TOOLS-LAG s81 304 commits / missing r708
- TOOLS-LAG s81_head 153 commits / missing r708
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 4781 taps in 44 types, 149 over 1650 sinks; insertion max 696 ps (p50 268, p90 285), skew max 107 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 265 taps in 3 types, 10 over 1650 sinks; insertion max 512 ps (p50 272, p90 307), skew max 94 ps; oversized taps: ins max 370 ps, skew max 64 ps
- TAP-INSERTION s81: 5459 taps in 86 types, 256 over 1650 sinks; insertion max 1000 ps (p50 466, p90 497), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 241 taps in 7 types, 8 over 1650 sinks; insertion max 504 ps (p50 463, p90 478), skew max 77 ps; oversized taps: ins max 499 ps, skew max 65 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-24 00:05 | tolera L32.62/112 units0 free291G | key-ca L38.06/112 units174 free376G | dear-c L26.45/128 units406 free168G | loved- L74.98/96 units55 free677G | outgoi L48.72/96 units160 free259G | renewe L46.68/96 units52 free316G | civil- L16.34/96 units31 free308G | viable L115.65/96 units30 free4653G | HOST-CAPS 1 flagged: epyc7:LOAD_CAP_FACTOR=1.2:EXPIRED; expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (279.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (279.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (279.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (279.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (279.9 h left); epyc10:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 e
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  353G   92G  80% /
    01:00:17 up 30 days, 20:40, 169 users,  load average: 25.55, 26.06, 26.38

## ot-run status
    ot-run status: epyc2 admits 587 GB (avail 705, reserve 0, fresh 0, peak 50.6) load 26/128 run 23 threads 86/128 root 74% scratch 161 GB
    intel1 admits 682 GB (avail 789, reserve 0, fresh 0, peak 97.5) load 53/112 run 30 threads 144/112 root 27% scratch 343 GB
    localhost admits 691 GB (avail 872, reserve 0, fresh 0, peak 70.2) load 26/112 run 7 threads 74/112 root 80% scratch 256 GB
    epyc7 admits 325 GB (avail 653, reserve 0, fresh 0, peak 3.3) load 54/96 run 20 threads 273/96 root 50% scratch 593 GB
    epyc8 admits 291 GB (avail 688, reserve 0, fresh 0, peak 8.2) load 78/96 run 24 threads 313/96 root 46% scratch 199 GB
    epyc9 admits 679 GB (avail 796, reserve 0, fresh 0, peak 37.9) load 49/96 run 12 threads 154/96 root 55% scratch 297 GB
    epyc10 admits 802 GB (avail 866, reserve 0, fresh 0, peak 48.3) load 62/96 run 15 threads 258/96 root 48% scratch 179 GB
    epyc11 admits 319 GB (avail 490, reserve 0, fresh 0, peak 259.3) load 89/96 run 32 threads 3454/96 root 4% scratch 4347 GB
    next 16-thread 32 GB job -> epyc2

## KIT-WAVE (autopilot log, last 6)
    2026-11-24 00:55:02 PST AUTOPILOT: KIT-WAVE LAUNCH-REFUSED qwen_kvsys/kv3_hgi_v4: LBL-DRAFT: lanes/VIS-COVERAGE.tsv row kv3_hgi_v4 is DRAFT: no relaunch / first attempt until its family row is PROBE-P
    2026-11-24 00:55:02 PST AUTOPILOT: KIT-WAVE LAUNCH-REFUSED qwen_kvsys/kv3_hgi_v2__cl2862d491: LBL-DRAFT: lanes/VIS-COVERAGE.tsv row kv3_hgi_v2__cl2862d491 is DRAFT: no relaunch / first attempt until i
    2026-11-24 00:55:02 PST AUTOPILOT: KIT-WAVE LAUNCH-REFUSED qwen_kvsys/kv3_hgi_v2__cle0015330: LBL-DRAFT: lanes/VIS-COVERAGE.tsv row kv3_hgi_v2__cle0015330 is DRAFT: no relaunch / first attempt until i
    2026-11-24 00:55:02 PST AUTOPILOT: KIT-WAVE LAUNCH-REFUSED qwen_kvsys/kv3_hgi_v5: LBL-DRAFT: lanes/VIS-COVERAGE.tsv row kv3_hgi_v5 is DRAFT: no relaunch / first attempt until its family row is PROBE-P
    2026-11-24 00:55:03 PST AUTOPILOT: KIT-WAVE HOLD-AUDIT HELD-BUT-LAUNCHED=0 HOLD-LEAK=0 TERM-UNREACHABLE=0 TERM-VARIANT=0 HOLD-SUPERSEDED=0 HOLD-ZERO-MATCH=0 PROOF-HELD=0 PILOT-DEADLOCK=0
    2026-11-24 00:55:23 PST AUTOPILOT: UNDER-USE HELD SKIP-HELD 20: s81/col_h9_r0_p4__t1__cl8ef405e8__pv70731479 1 [owner FAM-S81-COL-H10-R4, 36.6 h, eta 11-23 04:15, FLAGGED OVERDUE]; s81/col_h9_r0_p2__t

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-24 00:39 PST DIED [BIND-UNDRIVEN-IN] ot-push-main otpush-civil-redfish-3660609 on civil-redfish: rc=4 after 761 s, ended 08:39:24, log /srv/opentallas-scratch2/claude/BIND-UNDRIVEN-IN/tmp/push.log, cmd: ot-push-main  | class=TEST-FAIL cause=FAILED tools/die_plan/test_bind.py::test_bump_ports - FileNotFoundError: [Err...
- 2026-11-24 00:39 PST DONE [HEAD-R18] ot-run oth-ubuntu-4125763-1795509348 on loved-redfish: rc=0 after 239 s, ended 08:39:44, log none, cmd: --hosts epyc7 --no-spill --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/head-r18/tmp/tieaudit -- bash /srv/opentallas-scratch2/c
- 2026-11-24 00:39 PST DONE [REACHFIX-DUP] ot-run oth-ubuntu-650892-1795508897 on viable-ram: rc=0 after 691 s, ended 08:39:46, log /srv/opentallas-scratch2/claude/REACHFIX-DUP/kv.otrun, cmd: --hosts epyc11 --mem 32 --threads 1 --dir /srv/opentallas-scratch2/claude/REACHFIX-DUP -- bash -c cd /srv/opentallas-scratch2/claude/kv-allf
- 2026-11-24 00:39 PST DONE [KV-PV-CAP] ot-run oth-ubuntu-3940478-1795509383 on civil-redfish: rc=0 after 213 s, ended 08:39:52, log /srv/opentallas-scratch2/claude/kv-pv-cap/clk/why.log, cmd: --mem 16 --threads 1 --disk 2 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/kv-pv-cap/clk -- python3 -I why.py
- 2026-11-24 00:40 PST DONE [S81-KV-CALENDAR] ot-run oth-ubuntu-3076869-1795507546 on civil-redfish: rc=0 after 2067 s, ended 08:40:11, log /srv/opentallas-scratch2/claude/S81-KV-CALENDAR/otrun_vlat5.log, cmd: --mem 70 --threads 20 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/S81-KV-CALENDAR -- bash run_vlat5.sh
- 2026-11-24 00:40 PST DIED [KIT-FWDCLK-SDC] ot-run oth-ubuntu-3929389-1795509359 on civil-redfish: rc=1 after 262 s, ended 08:40:18, log /srv/opentallas-scratch2/claude/kit-fwdclk-sdc/tmp/sc.kv3_hroot.log, cmd: --hosts epyc10 --mem 60 --threads 4 --dir /srv/opentallas-scratch2/claude/kit-fwdclk-sdc -- bash /srv/opentallas-scratch2/claude/kit-fwdclk- | class=SETUP cause=cp: cannot stat '/srv/opentallas-scratch2/claud
- 2026-11-24 00:40 PST DIED [KIT-FWDCLK-SDC] ot-run oth-ubuntu-3929413-1795509359 on civil-redfish: rc=1 after 263 s, ended 08:40:19, log /srv/opentallas-scratch2/claude/kit-fwdclk-sdc/tmp/sc.kv3_io_cor_v1.log, cmd: --hosts epyc10 --mem 60 --threads 4 --dir /srv/opentallas-scratch2/claude/kit-fwdclk-sdc -- bash /srv/opentallas-scratch2/claude/kit-fwdclk- | class=SETUP cause=cp: cannot stat '/srv/opentallas-scratch2/c
- 2026-11-24 00:40 PST DIED [BIND-UNDRIVEN-IN] ot-run oth-ubuntu-3810789-1795509076 on civil-redfish: rc=1 after 549 s, ended 08:40:22, log none, cmd: --mem 8 --threads 2 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/BIND-UNDRIVEN-IN -- python3 -I /srv/opentallas-scratch2/claude/BIND | class=NO-PATTERN cause=rc 1 after 549 s, no log
- 2026-11-24 00:40 PST DIED [KIT-FWDCLK-SDC] ot-run oth-ubuntu-3929421-1795509359 on civil-redfish: rc=1 after 266 s, ended 08:40:22, log /srv/opentallas-scratch2/claude/kit-fwdclk-sdc/tmp/sc.kv3_io_cor.log, cmd: --hosts epyc10 --mem 60 --threads 4 --dir /srv/opentallas-scratch2/claude/kit-fwdclk-sdc -- bash /srv/opentallas-scratch2/claude/kit-fwdclk- | class=SETUP cause=cp: cannot stat '/srv/opentallas-scratch2/clau
- 2026-11-24 00:40 PST DIED [KIT-FWDCLK-SDC] ot-run oth-ubuntu-3929182-1795509359 on civil-redfish: rc=1 after 266 s, ended 08:40:22, log /srv/opentallas-scratch2/claude/kit-fwdclk-sdc/tmp/sc.kv3_io_ft_v1.log, cmd: --hosts epyc10 --mem 60 --threads 4 --dir /srv/opentallas-scratch2/claude/kit-fwdclk-sdc -- bash /srv/opentallas-scratch2/claude/kit-fwdclk- | class=SETUP cause=cp: cannot stat '/srv/opentallas-scratch2/cl
- 2026-11-24 00:40 PST DONE [FLOW-OPS-R3] ot-push-main otpush-civil-redfish-4030689 on civil-redfish: rc=0 after 23 s, ended 08:40:38, log none, cmd: ot-push-main 
- 2026-11-24 00:40 PST RESULT [HUB-POST-SPEED -> COORD] Cause: auto-gc detached from git commands in coord-commit.sh inherits fd 8 and 9 (no close-on-exec; the script exits without flock -u 8), so git maintenance/gc/prune kept HOLDING the push lock after the post ended. Seen in /proc fds; log gap 00:33:15-00:34:51 with no post done. gc re-ran after each other (~6,000 loose objects stayed after each run). While gc ran
- 2026-11-24 00:40 PST DONE [S81-KVLEAF-T2-ARCH-R2] ot-run oth-ubuntu-1572745-1795509455 on key-cardinal: rc=0 after 200 s, ended 00:40:53, log /srv/opentallas-scratch2/claude/s81-kvleaf-t2-arch/vpdef_run2/otrun.log, cmd: --mem 110 --threads 32 --hosts intel1 --dir /srv/opentallas-scratch2/claude/s81-kvleaf-t2-arch/vpdef_run2 -- bash run.sh
- 2026-11-24 00:41 PST DONE [PRECHECK-LEDGER-R3] ot-push-main otpush-tolerant-swine-561666 on tolerant-swine: rc=0 after 19 s, ended 00:41:03, log none, cmd: ot-push-main 
- 2026-11-24 00:41 PST DIED [BIND-UNDRIVEN-IN] ot-run oth-ubuntu-4034632-1795509620 on civil-redfish: rc=1 after 59 s, ended 08:41:16, log /srv/opentallas-scratch2/claude/BIND-UNDRIVEN-IN/out/tctl.log, cmd: --mem 8 --threads 2 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/BIND-UNDRIVEN-IN -- python3 -I /srv/opentallas-scratch2/claude/BIND | class=TEST-FAIL cause=AssertionError
- 2026-11-24 00:41 PST DIED [S81-T2-REFLOOR] ot-run oth-ubuntu-3864548-1795509181 on ubuntu: rc=1 after 502 s, ended 00:41:18, log none, cmd: --mem 32 --threads 1 --disk 2 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/s81-t2-refloor -- bash -c cd /srv/opentallas-scratch2/cla | class=NO-PATTERN cause=rc 1 after 502 s, no log
- 2026-11-24 00:41 PST DONE [S81-T2-REFLOOR] ot-run oth-ubuntu-3991955-1795509532 on ubuntu: rc=0 after 158 s, ended 00:41:26, log none, cmd: --mem 24 --threads 1 --disk 2 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/s81-t2-refloor -- bash /srv/opentallas-scratch2/claude/s8
- 2026-11-24 00:41 PST DONE [QC-TTC-R2] ot-run oth-ubuntu-1583722-1795509496 on key-cardinal: rc=0 after 210 s, ended 00:41:43, log /srv/opentallas-scratch2/claude/QC-TTC-R2/lecc_rep7_7.ot, cmd: --mem 48 --threads 1 --hosts intel1 --dir /srv/opentallas-scratch2/claude/QC-TTC-R2 -- bash /srv/opentallas-scratch2/claude/QC-TTC-R2/tool/l
- 2026-11-24 00:41 PST DONE [QC-TTC-R2] ot-run oth-ubuntu-1584234-1795509496 on key-cardinal: rc=0 after 224 s, ended 00:41:57, log /srv/opentallas-scratch2/claude/QC-TTC-R2/lecc_rep7_9.ot, cmd: --mem 48 --threads 1 --hosts intel1 --dir /srv/opentallas-scratch2/claude/QC-TTC-R2 -- bash /srv/opentallas-scratch2/claude/QC-TTC-R2/tool/l
- 2026-11-24 00:42 PST DONE [S81-B1-RTHOPS] ot-run oth-ubuntu-2458055-1795509187 on ubuntu: rc=0 after 538 s, ended 00:42:01, log /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/dd_p1.out, cmd: --mem 32 --threads 8 --hosts epyc9 --dir /srv/opentallas-scratch2/claude/s81-b1-rthops -- bash dd.sh p1
- 2026-11-24 00:42 PST DONE [QC-TTC-R2] ot-run oth-ubuntu-1583884-1795509496 on key-cardinal: rc=0 after 230 s, ended 00:42:03, log /srv/opentallas-scratch2/claude/QC-TTC-R2/lecc_rep7_8.ot, cmd: --mem 48 --threads 1 --hosts intel1 --dir /srv/opentallas-scratch2/claude/QC-TTC-R2 -- bash /srv/opentallas-scratch2/claude/QC-TTC-R2/tool/l
- 2026-11-24 00:42 PST STAND-DOWN [REACHFIX-DUP -> COORD] stood down; successor COORD. reach_fix dedup pushed 7e07947248; KV census: only pv_v12e/v7e change; S81 c8 plan not measured (row in lanes/LANE-STATUS.tsv; posts to REACHFIX-DUP now redirect)
- 2026-11-24 00:43 PST DONE [QC-INHOLD-BUDGET] ot-run oth-ubuntu-3907819-1795509310 on civil-redfish: rc=0 after 494 s, ended 08:43:21 env=wave+2, log /srv/opentallas-scratch2/claude/QC-INHOLD-BUDGET/log/v_stm1b.kit.ot, cmd: --mem 40 --threads 8 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/QC-INHOLD-BUDGET -- env IO_DB=4_1_cts.odb IO_SDC=4_cts.sdc RCMODE=
- 2026-11-24 00:43 PST DONE [QC-INHOLD-BUDGET] ot-run oth-ubuntu-3907834-1795509310 on civil-redfish: rc=0 after 503 s, ended 08:43:30 env=wave+0, log /srv/opentallas-scratch2/claude/QC-INHOLD-BUDGET/log/v_fw1b.kit.ot, cmd: --mem 40 --threads 8 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/QC-INHOLD-BUDGET -- env IO_DB=4_1_cts.odb IO_SDC=4_cts.sdc RCMODE=
- 2026-11-24 00:43 PST DONE [QC-F16-PRODUCER] ot-run oth-ubuntu-4083581-1795509702 on civil-redfish: rc=0 after 134 s, ended 08:43:53, log /srv/opentallas-scratch2/claude/QC-F16-PRODUCER/mini/row.ot, cmd: --mem 16 --threads 2 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/QC-F16-PRODUCER -- python3 -I -B rows/f16p_row.py /srv/opentallas-
- 2026-11-24 00:44 PST DONE [KV-PV-CAP] ot-run oth-ubuntu-4063750-1795509686 on civil-redfish: rc=0 after 168 s, ended 08:44:11, log /srv/opentallas-scratch2/claude/kv-pv-cap/clk/base4.log, cmd: --mem 48 --threads 4 --disk 10 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/kv-pv-cap/clk -- bash /srv/opentallas-scratch2/claude/kv
- 2026-11-24 00:45 PST NOTICE [FLEET-WATCH-1015 -> QC-ALLFIX] UNSIGNABLE watchdog (owner rule 11-20, >3 h and measured unable to sign): 1 job(s): epyc8 oth-ubuntu-1292084-1795492482 cbx_q10 (GRT overflow flat: overflow 17738 at iteration 5 -> 17579 at iteration 10: flat for 5 iterations; job age 4.8 h; 36 GB, listed since 00:45). Each is cancelled by ot-run --cancel <unit> 30 min after this post unless QC-ALLFIX post
- 2026-11-24 00:45 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-103): 4 event(s): slw_st_b_v1__cle6023ec2 PLAN-CHANGE (rule C) density 0.4784 cells/um2 >= 0.42: PLAN-CHANGE slw_st_b_v1__cle6023ec2: outline 622.08 x 1339.2 (soft 822041 um2) carries 393258 cells; grow the soft area x1.14 (to 936329 um2) or split into 2 types (rule C, advisory; die owner ranks a plan change first); slw_st_b_v1__cle6023ec2 AUTO-GE
- 2026-11-24 00:45 PST DONE [KV-HR-DEEPCLK] ot-run oth-ubuntu-3399531-1795509140 on tolerant-swine: rc=0 after 803 s, ended 00:45:41, log /home/ubuntu/tmp/kvhrdc/dme8.otrun.log, cmd: --hosts epyc8 --mem 12 --threads 1 --priority proof --dir /srv/opentallas-scratch2/claude/kv-hr-deepclk -- bash /srv/opentallas-scratch2/cla
- 2026-11-24 00:45 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 12 flagged of 66 containers {'UNSIGNABLE': 3, 'NO-PROGRESS': 5, 'GRT-LABEL': 4, 'YOUNG': 30, 'NO-DATA': 2, 'PROGRESS': 22}; full table lanes/NOPROG-TABLE.md; flagged: epyc7 hd_lep0N 4_2_tapbal_grt [UNSIGNABLE: 4_1_cts.json latest setup WNS -2236.42 ps (< -300, gate TT >] UNSIGNABLE (hub: ot-run --ca; epyc7 hd_lep0N 4_2_tapbal_grt [UNSIGNABLE: 
- 2026-11-24 00:45 PST DONE [BIND-UNDRIVEN-IN] ot-push-main otpush-civil-redfish-4046610 on civil-redfish: rc=0 after 298 s, ended 08:45:47, log /srv/opentallas-scratch2/claude/BIND-UNDRIVEN-IN/tmp/push2.log, cmd: ot-push-main 
- 2026-11-24 00:45 PST DONE [KV-OWN-HG] ot-run oth-ubuntu-3717095-1795509675 on ubuntu: rc=0 after 281 s, ended 00:45:52, log none, cmd: --hosts epyc8 --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/KV-OWN-HG -- bash -c 
- 2026-11-24 00:45 PST DONE [QC-HC1-CLKENTRY] ot-run oth-ubuntu-671973-1795508965 on viable-ram: rc=0 after 992 s, ended 08:45:56, log /home/ubuntu/coord/autopilot/private_specs/QC-HC1-CLKENTRY/qwen_compute_sle_ctl__cla4f6f12f_1124064122/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 00:47 PST DONE [S81-B1-RTHOPS] ot-run oth-ubuntu-2545752-1795509493 on ubuntu: rc=0 after 541 s, ended 00:47:10, log /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/dd_p2.out, cmd: --mem 32 --threads 8 --hosts epyc9 --dir /srv/opentallas-scratch2/claude/s81-b1-rthops -- bash dd.sh p2
- 2026-11-24 00:47 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-4072308-1795509187 on outgoing-giraffe: rc=0 after 855 s, ended 08:47:20, log /srv/opentallas-scratch2/claude/QC-OPEN-STA/r9b.ot, cmd: --mem 32 --threads 2 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/QC-OPEN-STA -- bash /srv/opentallas-scratch2/claude/QC-OPEN-STA/row
- 2026-11-24 00:48 PST DIED [S81-OWN-SLICE] ot-run oth-ubuntu-2590213-1795509634 on renewed-glider: rc=1 after 460 s, ended 08:48:12, log none, cmd: --mem 32 --threads 8 --hosts epyc9 --dir /srv/opentallas-scratch2/claude/s81-own-slice -- bash -c NOMUT=1 NCYC=20000 bash selrep_lec_run.sh  | class=NO-PATTERN cause=rc 1 after 460 s, no log
- 2026-11-24 00:48 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-3641506-1795509552 on outgoing-giraffe: rc=0 after 573 s, ended 08:48:42, log /srv/opentallas-scratch2/claude/QC-OPEN-STA/fork8.ot, cmd: --mem 8 --threads 16 --hosts epyc8 --dir /srv/opentallas-scratch2/claude/QC-OPEN-STA -- python3 -I /srv/opentallas-scratch2/claude/rt/751410
- 2026-11-24 00:51 PST DONE [S81-KV-CALENDAR] ot-run oth-ubuntu-3262366-1795507811 on civil-redfish: rc=0 after 2480 s, ended 08:51:29, log /srv/opentallas-scratch2/claude/S81-KV-CALENDAR/otrun_prog.log, cmd: --mem 70 --threads 20 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/S81-KV-CALENDAR -- bash run_prog.sh
- 2026-11-24 00:51 PST DONE [KV-TAPSPLIT-HGPV] ot-run oth-ubuntu-3413929-1795508278 on civil-redfish: rc=0 after 2043 s, ended 08:51:59, log /srv/opentallas-scratch2/claude/kv-tapsplit-hgpv/both2_ctl.otrun, cmd: --hosts epyc10 --mem 64 --threads 8 --dir /srv/opentallas-scratch2/claude/kv-tapsplit-hgpv -- bash /srv/opentallas-scratch2/claude/kv-tapspl
- 2026-11-24 00:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-24 00:52 PST: 98 running jobs, PROGRESSING 89, SLOW 5, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
- 2026-11-24 00:52 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-930179-1795509524 on viable-ram: rc=0 after 856 s, ended 08:52:58, log /srv/opentallas-scratch2/claude/kv-allfix/grow/logs/a5t.otrun.log, cmd: --hosts epyc11 --mem 48 --threads 6 --priority proof --dir /srv/opentallas-scratch2/claude/kv-allfix -- bash /srv/opentallas-scratch2/claude
- 2026-11-24 00:53 PST DONE [QC-CB-PROBE] ot-run oth-ubuntu-884560-1795509403 on tolerant-swine: rc=0 after 994 s, ended 00:53:11, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-CB-PROBE/qwen_compute_cbn_q01__clab6e67f2_1124002511/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 00:53 PST DONE [QC-CB-PROBE] ot-run oth-ubuntu-885897-1795509405 on tolerant-swine: rc=0 after 1006 s, ended 00:53:24, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-CB-PROBE/qwen_compute_cbn_q01__cld9ff4c40_1124002530/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 00:53 PST DONE [KV-RSTREACH] ot-run oth-ubuntu-816007-1795509279 on viable-ram: rc=0 after 1144 s, ended 08:53:41, log /srv/opentallas-scratch2/claude/kv-rstreach/fork_a5s.log, cmd: --hosts epyc11 --mem 8 --threads 4 --disk 100 --dir /srv/opentallas-scratch2/claude/kv-rstreach -- python3 -I /srv/opentallas-scratch2/claud
- 2026-11-24 00:54 PST DIED [QC-F16-PRODUCER] ot-run oth-ubuntu-3302418-1795507924 on civil-redfish: rc=4 after 2524 s, ended 08:54:06, log /srv/opentallas-scratch2/claude/QC-F16-PRODUCER/fork.ot, cmd: --mem 12 --threads 8 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/QC-F16-PRODUCER -- python3 -I /srv/opentallas-scratch2/claude/rt/8 | class=SSH-DROP cause=Connection closed by 84.32.189.120 port 22
- 2026-11-24 00:54 PST DONE [QC-CB-PROBE] ot-run oth-ubuntu-876113-1795509392 on tolerant-swine: rc=0 after 1099 s, ended 00:54:45, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-CB-PROBE/qwen_compute_cbn_q11__cl49ae4555_1124002611/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 00:55 PST DONE [QC-SC-FARRST] ot-run oth-ubuntu-3573192-1795507905 on loved-redfish: rc=0 after 2606 s, ended 08:55:08, log /srv/opentallas-scratch2/claude/QC-SC-FARRST/gate.ot, cmd: --mem 64 --threads 4 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/QC-SC-FARRST -- bash /srv/opentallas-scratch2/claude/QC-SC-FARRST/g
- 2026-11-24 00:55 PST DONE [QC-CB-PROBE] ot-run oth-ubuntu-877997-1795509395 on tolerant-swine: rc=0 after 1138 s, ended 00:55:27, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-CB-PROBE/qwen_compute_cbf_q00__cl870de686_1124002650/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 00:55 PST DONE [S81-BOOTCONTRACT] ot-run oth-ubuntu-2320593-1795508644 on renewed-glider: rc=0 after 1915 s, ended 08:55:57, log /srv/opentallas-scratch2/claude/s81-bootcontract/out/run.log, cmd: --mem 24 --threads 2 --hosts epyc9 --dir /srv/opentallas-scratch2/claude/s81-bootcontract -- python3 -I -B /srv/opentallas-scratch2/claude/s
- 2026-11-24 00:56 PST DONE [S81-KVLEAF-T2-ARCH-R2] ot-run oth-ubuntu-1435356-1795509001 on key-cardinal: rc=0 after 1598 s, ended 00:56:36, log /srv/opentallas-scratch2/claude/s81-kvleaf-t2-arch/vpdef_run/otrun.log, cmd: --mem 96 --threads 24 --hosts intel1 --dir /srv/opentallas-scratch2/claude/s81-kvleaf-t2-arch/vpdef_run -- bash run.sh
- 2026-11-24 00:56 PST DIED [KV-TAPSPLIT-HGPV] ot-run oth-ubuntu-3516947-1795508471 on civil-redfish: rc=1 after 2139 s, ended 08:56:48, log /srv/opentallas-scratch2/claude/kv-tapsplit-hgpv/both3_row.otrun, cmd: --hosts epyc10 --mem 64 --threads 8 --dir /srv/opentallas-scratch2/claude/kv-tapsplit-hgpv -- bash /srv/opentallas-scratch2/claude/kv-tapspl | class=DESIGN-FAIL cause=R8_FAIL_FAST {"head_r8_errors": 30, "othe
- 2026-11-24 00:57 PST DONE [QC-CB-PROBE] ot-run oth-ubuntu-888158-1795509408 on tolerant-swine: rc=0 after 1223 s, ended 00:57:05, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-CB-PROBE/qwen_compute_cbn_q01__cldd6ea846_1124002549/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 00:57 PST DONE [QC-ALLFIX-SU] ot-run oth-ubuntu-3317689-1795507323 on loved-redfish: rc=0 after 3339 s, ended 08:57:38, log /srv/opentallas-scratch2/claude/QC-ALLFIX-SU/fix4_gate.ot, cmd: --mem 48 --threads 4 --hosts epyc7 -- bash /srv/opentallas-scratch2/claude/QC-ALLFIX-SU/fix4_gate.sh
- 2026-11-24 00:57 PST DIED [KV-PV-EDGESTRIP] ot-run oth-ubuntu-3980500-1795509504 on civil-redfish: rc=1 after 1168 s, ended 08:57:49, log /srv/opentallas-scratch2/claude/kv-pv-edgestrip/row/sb.otrun, cmd: --hosts epyc10 --mem 64 --threads 8 --priority plan --plan-job bind --dir /srv/opentallas-scratch2/claude/kv-pv-edgestrip -- bash /srv/opent | class=DESIGN-FAIL cause=RC_G0 1 G0 FAIL: 6 errors, 0 pending-view, 520
- 2026-11-24 00:57 PST DONE [QC-CB-PROBE] ot-run oth-ubuntu-890336-1795509413 on tolerant-swine: rc=0 after 1268 s, ended 00:57:55, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-CB-PROBE/qwen_compute_cbn_q00__cldbcda913_1124002451/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 00:57 PST DONE [PRE-QC-GENCHECK] ot-run oth-ubuntu-4181757-1795509518 on loved-redfish: rc=0 after 1160 s, ended 08:57:55, log /srv/opentallas-scratch2/claude/PRE-QC-GENCHECK/tmp/gd5.ot, cmd: --mem 64 --threads 4 --disk 10 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/PRE-QC-GENCHECK -- bash /srv/opentallas-scratch2/claude/P
- 2026-11-24 00:58 PST DONE [QC-CB-PROBE] ot-run oth-ubuntu-1208521-1795510500 on tolerant-swine: rc=0 after 224 s, ended 00:58:38, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-CB-PROBE/qwen_compute_cbn_q01__clab6e67f2_1124002511/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priv
- 2026-11-24 00:58 PST DONE [S81-B1-RTHOPS] ot-run oth-ubuntu-2367778-1795508834 on ubuntu: rc=0 after 1904 s, ended 00:58:54, log /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/post_p1.out, cmd: --mem 48 --threads 8 --hosts epyc9 --dir /srv/opentallas-scratch2/claude/s81-b1-rthops -- bash post.sh p1
- 2026-11-24 00:59 PST DONE [QC-CB-PROBE] ot-run oth-ubuntu-876135-1795509392 on tolerant-swine: rc=0 after 1390 s, ended 00:59:36, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-CB-PROBE/qwen_compute_cbn_q11__cl5cc92dfe_1124002631/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 00:59 PST DONE [S81-ROM-TEMPLATE] ot-run oth-ubuntu-3369060-1795508118 on civil-redfish: rc=0 after 2667 s, ended 08:59:43, log /srv/opentallas-scratch2/claude/s81-rom-template/smoke.out, cmd: --mem 32 --threads 4 --hosts epyc10 --disk 10 --dir /srv/opentallas-scratch2/claude/s81-rom-template -- bash /srv/opentallas-scratch2/claude

