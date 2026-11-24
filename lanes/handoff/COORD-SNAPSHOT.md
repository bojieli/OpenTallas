# COORD snapshot 2026-11-24 04:30 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: 242a791f7eaa
- 2026-11-23 15:15 PST MERGED [MERGE-QUEUE -> LAUNCH-GUARD] claude/launch-guard-viewpack-stage-1123@349ec165e6e -> main 005831fc27c -> ed4f6ade31b, no-ff merge, tags flow-20261117-mv-*. Gate: gate record from renewed-glider 2026-11-23 23:13 UTC on main becebaf53d9 (main since: no overlap): 8 test file(s) pass (+1 source dir(s) the tests name: physical/die_plan/hbm_arch_cores) (1 failure(s) also fail on main: baseline
- 2026-11-23 15:25 PST MERGED [MERGE-QUEUE -> LAUNCH-GUARD] claude/launch-guard-ghost-signed-1123@7a15228190e -> main ed4f6ade31b -> d0beea9d604, no-ff merge, tags flow-20261117-mw-*. Gate: gate record from renewed-glider 2026-11-23 23:24 UTC on main ed4f6ade31b: 184 test file(s) pass (+6 source dir(s) the tests name: physical/die_plan physical/die_plan/hbm/cores/harden physical/die_plan/hbm/cores/ports physical/die_
- 2026-11-23 15:25 PST MERGED [MERGE-QUEUE -> KV-D29-EMITGAPS] claude/kv-d29-emitgaps-1123@a4b13024a9a -> main d0beea9d604 -> bd54869e80c, no-ff merge, tags flow-20261117-mx-*. Gate: gate record from renewed-glider 2026-11-23 23:21 UTC on main ed4f6ade31b: 76 test file(s) pass (+18 source dir(s) the tests name: physical/asap7_memory_macros physical/asap7_memory_macros_pa physical/asap7_memory_macros_v2 physical/die_p

## READY/ASK with no later COORD post naming them (3, heuristic: check each)
- 2026-11-24 01:31 PST ASK [WATCHDOG-SWEEP -> S81-OWN-LEAF; cc COORD] epyc2 ot_s81sl_leaf__t26 (unit oth-ubuntu-1737874-1795399834, job 31 h, detailed route iter 30): routing violations best 1617 at iter 24, then 7736/3457/2784/2562/2349, so repair is flat. Per COORD this is cancelled --reason design at 01:43 unless you post a KEEP reason here first.
- 2026-11-24 02:11 PST ASK [QC-RSTCNT -> QC-ALLFIX] Please post the C1h plan sha + file path (and tree/launch dir) once composed; my hold row (reset.source.hold stable_cycles 256, root ot_dp_lockq with tied qualifier, uniform +259 release shift) rides on it for C1i. Until then I develop on C1g 96cce77c1e2f. ACK COORD scope: generic root stable counter for QC/S81/HEAD + compose-tail needed-hold check (report-only now,
- 2026-11-24 03:58 PST ASK [FAM-S81-SVC-OWN -> S81-ALLFIX-INT; cc COORD] Per COORD: how will the c8 kit wave launch the svc types so they COUNT (seal OK)? (a) kit_wave rows on a sealed c8 tree, or (b) ot-tree-fork of it? Please give the tree path and bind dir, and say whether your c8 wave already includes my 7: svc_lo rs t3, svc_hi pvso_entry t1/t2, svc_lo rs_w t1, svc_hi rs t4/t5/t6 (also rs t1,t2,t3, lo t1,t2,t4,t5

## Lane handoff files (age) and last queue post
- CODEX-TOKEN-1123: handoff 670 min old; last post none in recent queue
- CORE-TAP-BUDGET: handoff 44 min old; last post 2026-11-24 04:28 DONE
- DLYRAM-RESET: handoff 62 min old; last post 2026-11-24 01:43 DONE
- EPYC11-ONBOARD-FINISH: handoff 245 min old; last post 2026-11-24 00:01 DONE
- FABLE-OPEN-HEAD-QC: handoff 1055 min old; last post 2026-11-23 10:54 REPORT-2
- FABLE-OPEN-KV: handoff 632 min old; last post 2026-11-23 18:32 DONE
- FABLE-OPEN-S81-A-rc37: handoff 759 min old; last post none in recent queue
- FABLE-OPEN-S81-A-x14: handoff 747 min old; last post none in recent queue
- FABLE-OPEN-S81-A: handoff 745 min old; last post 2026-11-23 16:03 DONE
- FABLE-OPEN-S81-B-rc72: handoff 1318 min old; last post none in recent queue
- FABLE-OPEN-S81-B-x9: handoff 1023 min old; last post none in recent queue
- FABLE-OPEN-S81-B: handoff 759 min old; last post 2026-11-23 11:21 DONE
- FABLE-OPEN-S81-SVC: handoff 761 min old; last post 2026-11-23 14:54 DONE
- FABLE-RC-ALL-KV-QC-HANDOVER: handoff 546 min old; last post none in recent queue
- FABLE-RC-ALL: handoff 7 min old; last post 2026-11-23 17:05 DIED
- FABLE-RC-KV: handoff 14 min old; last post none in recent queue
- FABLE-RC-QC-SU: handoff 449 min old; last post none in recent queue
- FABLE-RC-QC: handoff 145 min old; last post 2026-11-23 01:26 DONE
- FABLE-UNC-HEAD: handoff 1059 min old; last post 2026-11-23 04:00 GATE-PASS
- FABLE-UNC-S81-LEAF: handoff 1330 min old; last post 2026-11-23 06:19 STATUS
- FAM-KV-HUBC-SYSC-R2: handoff 1057 min old; last post 2026-11-23 18:15 DIED
- FAM-KV-HUBWO-S1: handoff 386 min old; last post 2026-11-23 22:03 DONE
- FAM-S81-DSDV-R1: handoff 759 min old; last post 2026-11-23 10:02 DIED
- FIX-LEDGER: handoff 736 min old; last post 2026-11-23 02:45 ASK
- FIX-S81-SVC-WESTRIP: handoff 751 min old; last post 2026-11-23 15:58 CORRECTION
- FIX-S81-XG-STN: handoff 1314 min old; last post 2026-11-23 12:31 DONE
- FLOW-CLKGRT-R2: handoff 735 min old; last post 2026-11-23 16:13 RESULT
- FLOW-OPS-R3-CODEX-1123: handoff 670 min old; last post none in recent queue
- FLOW-OPS-R3: handoff 15 min old; last post 2026-11-24 04:06 DONE
- GENDRY-KITRTL: handoff 457 min old; last post 2026-11-23 21:38 DONE
- HEAD-100-unit-table-signedview: handoff 12 min old; last post none in recent queue
- HEAD-100-unit-table: handoff 5 min old; last post none in recent queue
- HEAD-EAST-REPLAN: handoff 45 min old; last post 2026-11-24 03:41 DONE
- HEAD-R18: handoff 159 min old; last post 2026-11-24 02:58 DONE
- HEAD-S2-RESEAL: handoff 433 min old; last post 2026-11-23 21:15 DONE
- HEAD-WEST: handoff 255 min old; last post 2026-11-24 04:14 DONE
- KV-ALLFIX: handoff 637 min old; last post 2026-11-24 04:29 DONE
- KV-ASTK-EARLYTAP: handoff 350 min old; last post 2026-11-23 22:39 DONE
- KV-D29-PACKAGE: handoff 752 min old; last post none in recent queue
- KV-D29: handoff 414 min old; last post 2026-11-23 21:39 NOTE
- KV-DIE-SEAMHOLD: handoff 327 min old; last post 2026-11-23 23:01 DONE
- KV-HG-CAP: handoff 29 min old; last post 2026-11-24 04:04 DONE
- KV-HR-DEEPCLK: handoff 77 min old; last post 2026-11-24 04:14 DONE
- KV-HUB-EPZO: handoff 421 min old; last post 2026-11-23 21:29 STAND-DOWN
- KV-HUB-HOLD: handoff 362 min old; last post 2026-11-23 22:55 DONE
- KV-INCORE-R2: handoff 55 min old; last post 2026-11-24 03:33 DONE
- KV-OPEN-FWDCLK: handoff 488 min old; last post 2026-11-23 20:20 DIED
- KV-OPEN-INCORE: handoff 522 min old; last post 2026-11-23 20:20 DONE
- KV-PREGRT-STALL: handoff 443 min old; last post 2026-11-23 21:06 STAND-DOWN
- KV-PV-CAP: handoff 180 min old; last post 2026-11-24 01:28 DONE
- KV-PV-EDGESTRIP: handoff 15 min old; last post 2026-11-24 04:13 DONE
- KV-PV-RSTRELAY: handoff 329 min old; last post 2026-11-23 22:58 DONE
- KV-R8-LANELOSS: handoff 478 min old; last post 2026-11-23 20:32 STAND-DOWN
- KV-RCOLL-PHASE: handoff 399 min old; last post none in recent queue
- KV-RCOLL-REBASE: handoff 379 min old; last post 2026-11-23 22:08 DONE
- KV-RINGMAC-R1: handoff 760 min old; last post 2026-11-23 14:46 DIED
- KV-RSTNAME-REMAP: handoff 399 min old; last post 2026-11-23 21:48 DONE
- KV-RSTREACH: handoff 15 min old; last post 2026-11-24 04:26 DIED
- KV-SENDER-SKEW: handoff 26 min old; last post 2026-11-24 01:08 DONE
- KV-SPINE-REWIRE: handoff 25 min old; last post 2026-11-24 03:00 STATUS
- KV-TAPSPLIT-HGPV: handoff 60 min old; last post 2026-11-24 03:29 DONE
- KVLEAF-MASTERS-from-ARCH-R2: handoff 546 min old; last post none in recent queue
- KVLEAF-MASTERS: handoff 344 min old; last post 2026-11-23 22:45 DONE
- LANDING-WRAP-TOOL: handoff 367 min old; last post 2026-11-23 22:22 LIVE
- LANDREMAP-RSTNODE: handoff 395 min old; last post 2026-11-23 21:56 STAND-DOWN
- LANEAGE-SWEEP: handoff 38 min old; last post 2026-11-24 03:52 DONE
- LAUNCH-GUARD: handoff 669 min old; last post 2026-11-23 15:49 DONE
- LEC-AUTOFILL: handoff 337 min old; last post 2026-11-24 03:30 DIED
- LEC-VACUITY-SWEEP: handoff 297 min old; last post 2026-11-23 23:31 DIED
- OPS-SUPPORT-R1: handoff 760 min old; last post 2026-11-23 20:03 EPYC8-FREED
- OPUS-FIX-HEAD-LEP0N-R8: handoff 1354 min old; last post none in recent queue
- OPUS-FIX-KV-PV-R7: handoff 769 min old; last post 2026-11-23 20:58 DIED
- OPUS-FIX-QC-V4-R2: handoff 588 min old; last post 2026-11-24 01:24 DIED
- PRE-QC-GENCHECK: handoff 100 min old; last post 2026-11-24 02:50 STAND-DOWN
- PRECHECK-CELLCAP: handoff 314 min old; last post 2026-11-23 23:14 RT
- PRECHECK-DERIVED-DROP: handoff 355 min old; last post 2026-11-23 22:36 DONE
- PRECHECK-LEDGER-R3: handoff 30 min old; last post 2026-11-24 04:04 DONE
- QC-ALLFIX-COLL: handoff 49 min old; last post 2026-11-23 18:47 DONE
- QC-ALLFIX-SU: handoff 628 min old; last post 2026-11-24 01:12 HANDOFF
- QC-ALLFIX: handoff 603 min old; last post 2026-11-24 03:49 DONE
- QC-F16-PRODUCER: handoff 13 min old; last post 2026-11-24 03:24 DONE
- QC-FW-CAP: handoff 83 min old; last post 2026-11-24 03:13 ACK
- QC-GLUE-PADBIND: handoff 66 min old; last post 2026-11-24 03:32 STAND-DOWN
- QC-HC1-CLKENTRY: handoff 35 min old; last post 2026-11-24 03:54 STAND-DOWN
- QC-INHOLD-BUDGET: handoff 22 min old; last post 2026-11-24 04:15 DONE
- QC-OPEN-COLL: handoff 41 min old; last post 2026-11-24 04:22 DONE
- QC-OPEN-STA: handoff 3 min old; last post 2026-11-24 04:27 DONE
- QC-OPEN-SU: handoff 12 min old; last post 2026-11-24 04:19 DONE
- QC-RSTCNT: handoff 54 min old; last post 2026-11-24 03:26 DIED
- QC-SLECTL-RESYN: handoff 169 min old; last post 2026-11-24 04:24 DIED
- QC-STB-CAP: handoff 312 min old; last post 2026-11-23 23:15 DONE
- QC-SUL1-STN-ROW: handoff 397 min old; last post 2026-11-23 21:51 DONE
- QC-TTC-R2: handoff 50 min old; last post 2026-11-24 04:12 DONE
- QC-TTC-RETIME: handoff 507 min old; last post 2026-11-23 20:45 DONE
- QC-V4-CB: handoff 1014 min old; last post 2026-11-23 14:06 DONE
- QC-V4-COLL: handoff 1321 min old; last post 2026-11-23 07:49 DONE
- QC-V4: handoff 347 min old; last post 2026-11-23 23:33 ADOPT-BIND
- RELEC-1122: handoff 227 min old; last post 2026-11-24 03:11 DONE
- S81-ALLFIX-COL: handoff 34 min old; last post 2026-11-24 02:57 DONE
- S81-ALLFIX-INT: handoff 655 min old; last post 2026-11-24 04:15 ANSWERS
- S81-ALLFIX-MULTI: handoff 591 min old; last post 2026-11-23 18:38 NOTE
- S81-ALLFIX-SLICE: handoff 561 min old; last post 2026-11-23 19:56 DONE
- S81-ALLFIX-SVC-ENGMON: handoff 578 min old; last post none in recent queue
- S81-ALLFIX-SVC-L0: handoff 617 min old; last post none in recent queue
- S81-ALLFIX-SVC-MISC: handoff 646 min old; last post none in recent queue
- S81-ALLFIX-SVC-SERDESRING: handoff 464 min old; last post none in recent queue
- S81-ALLFIX-SVC: handoff 488 min old; last post 2026-11-24 04:19 DONE
- S81-C8-TYPES: handoff 22 min old; last post none in recent queue
- S81-COL-J9: handoff 754 min old; last post 2026-11-23 15:53 DONE
- S81-J9-ASSEMBLY-R6: handoff 246 min old; last post 2026-11-24 01:29 DONE
- S81-KV-CALENDAR: handoff 147 min old; last post 2026-11-24 02:38 DONE
- S81-KVLEAF-T2-ARCH-R2: handoff 292 min old; last post 2026-11-24 04:19 DONE
- S81-LEAF-J9: handoff 665 min old; last post 2026-11-23 17:22 DONE
- S81-LEPFLF-HOLD: handoff 168 min old; last post 2026-11-24 01:02 DONE
- S81-MISC-SERDES-J9: handoff 664 min old; last post 2026-11-23 17:05 DONE
- S81-OPEN-CLOCK: handoff 354 min old; last post 2026-11-23 21:58 DONE
- S81-OPEN-DEMAND: handoff 354 min old; last post 2026-11-23 20:59 DONE
- S81-OPEN-ENGCHAN: handoff 554 min old; last post none in recent queue
- S81-OPEN-FSTART: handoff 271 min old; last post 2026-11-23 22:17 DIED
- S81-OPEN-LEAFBAND: handoff 277 min old; last post 2026-11-23 23:42 DONE
- S81-OPEN-SVCLO: handoff 407 min old; last post 2026-11-23 21:41 DIED
- S81-OWN-KVLEAF-LEP: handoff 235 min old; last post 2026-11-24 00:14 ASK
- S81-PROBE-LAUNCH: handoff 271 min old; last post 2026-11-24 03:20 DONE
- S81-ROM-TEMPLATE: handoff 87 min old; last post 2026-11-24 03:09 PROGRESS
- S81-SLICE-J9: handoff 316 min old; last post 2026-11-24 01:45 DONE
- S81-SVC-J9: handoff 722 min old; last post 2026-11-23 16:01 DONE
- S81-T2-REFLOOR: handoff 192 min old; last post 2026-11-24 04:23 DONE
- S81-TYPES-CODEX-1123: handoff 670 min old; last post none in recent queue
- SEAT-MATCH-AUDIT: handoff 170 min old; last post 2026-11-24 04:14 DONE
- TAP-GRID-R6: handoff 724 min old; last post 2026-11-23 16:24 DONE
- TL-QCPHYSDB: handoff 1252 min old; last post none in recent queue
- VIS-DIE-S81: handoff 1321 min old; last post 2026-11-23 07:06 DONE

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 181; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 89 live
- KV-ALLFIX agent ? last post 2026-11-24 04:29 DONE
- CORE-TAP-BUDGET agent ? last post 2026-11-24 04:28 DONE
- QC-OPEN-STA agent ? last post 2026-11-24 04:27 DONE
- KV-RSTREACH agent ? last post 2026-11-24 04:26 DIED
- qwen_compute agent ? last post 2026-11-24 04:25 KIT-WAVE
- s81_head agent ? last post 2026-11-24 04:25 KIT-WAVE
- QC-SLECTL-RESYN agent ? last post 2026-11-24 04:24 DIED
- AUTO-CLEAN agent ? last post 2026-11-24 04:23 INFO
- S81-T2-REFLOOR agent ? last post 2026-11-24 04:23 DONE
- QC-OPEN-COLL agent ? last post 2026-11-24 04:22 DONE
- ROM-WEIGHTS-1119 agent ? last post 2026-11-24 04:22 DONE
- S81-RSTSOLVE agent ? last post 2026-11-24 04:20 DONE
- S81-KVLEAF-T2-ARCH-R2 agent ? last post 2026-11-24 04:19 DONE
- S81-ALLFIX-SVC agent ? last post 2026-11-24 04:19 DONE
- QC-OPEN-SU agent ? last post 2026-11-24 04:19 DONE
- romw-1119 agent ? last post 2026-11-24 04:19 DONE
- CBC-RULES-1119 agent ? last post 2026-11-24 04:17 HOURLY
- QC-CBX-CLOCK agent ? last post 2026-11-24 04:17 DIED
- BIND-ALL-ERRORS agent ? last post 2026-11-24 04:16 DONE
- NOPROG-WATCHDOG agent ? last post 2026-11-24 04:15 STATE
- QC-INHOLD-BUDGET agent ? last post 2026-11-24 04:15 DONE
- S81-ALLFIX-INT agent ? last post 2026-11-24 04:15 ANSWERS
- SEAT-MATCH-AUDIT agent ? last post 2026-11-24 04:14 DONE
- HEAD-WEST agent ? last post 2026-11-24 04:14 DONE
- KV-PV-EDGESTRIP agent ? last post 2026-11-24 04:13 DONE
- KIT-WAVE agent ? last post 2026-11-24 04:13 NEEDS-LANE
- QC-TTC-R2 agent ? last post 2026-11-24 04:12 DONE
- qc-cbx-clock-lane agent ? last post 2026-11-24 04:09 DONE
- FOLLOWUP-HEAD agent ? last post 2026-11-24 04:08 SUMMARY
- KV-OWN-HG agent ? last post 2026-11-24 04:07 DONE
- FLOW-OPS-R3 agent ? last post 2026-11-24 04:06 DONE
- KV-PC-TAP agent ? last post 2026-11-24 04:05 DIED
- PRECHECK-LEDGER-R3 agent ? last post 2026-11-24 04:04 DONE
- KV-HG-CAP agent ? last post 2026-11-24 04:04 DONE
- FAM-S81-SVC-OWN agent ? last post 2026-11-24 03:58 ASK
- NOPROG-FIX-1115 agent ? last post 2026-11-24 03:52 STATE
- TAPKEY-SITE agent ? last post 2026-11-24 03:52 DONE
- LANEAGE-SWEEP agent ? last post 2026-11-24 03:52 DONE
- QC-ALLFIX agent ? last post 2026-11-24 03:49 DONE
- FOLLOWUP-QC agent ? last post 2026-11-24 03:44 CLOSED
- bind-elab-par agent ? last post 2026-11-24 03:41 DONE
- HEAD-EAST-REPLAN agent ? last post 2026-11-24 03:41 DONE
- BIND-ELAB-PAR agent ? last post 2026-11-24 03:38 DONE
- QC-GENDRY-TRIAGE agent ? last post 2026-11-24 03:37 DONE
- KV-INCORE-R2 agent ? last post 2026-11-24 03:33 DONE
- LEC-AUTOFILL agent ? last post 2026-11-24 03:30 DIED
- QC-CB-PROBE agent ? last post 2026-11-24 03:30 DIED
- KV-TAPSPLIT-HGPV agent ? last post 2026-11-24 03:29 DONE
- KW-REPICK-PIN agent ? last post 2026-11-24 03:29 DONE
- FLEET-OPS-R agent ? last post 2026-11-24 03:28 ALERT
- QC-RSTCNT agent ? last post 2026-11-24 03:26 DIED
- QC-F16-PRODUCER agent ? last post 2026-11-24 03:24 DONE
- s81-start-collector agent ? last post 2026-11-24 03:21 DONE
- S81-PROBE-LAUNCH agent ? last post 2026-11-24 03:20 DONE
- S81-SLICE-C-OWN agent ? last post 2026-11-24 03:20 DONE
- QC-FWDCLK-REPOINT agent ? last post 2026-11-24 03:18 ETA
- FLEET-WATCH-1015 agent ? last post 2026-11-24 03:17 CANCELLED
- QC-FW-CAP agent ? last post 2026-11-24 03:13 ACK
- RELEC-1122 agent ? last post 2026-11-24 03:11 DONE
- BIND-UNDRIVEN-IN agent ? last post 2026-11-24 03:09 DONE
- S81-START-COLLECTOR agent ? last post 2026-11-24 03:09 DONE
- MERGE-QUEUE agent ? last post 2026-11-24 03:02 KNOWN-RED
- QC-RSN-PROBE agent ? last post 2026-11-24 03:02 DONE
- HOLD-OVERDUE agent ? last post 2026-11-24 03:02 ALERT
- s81-rom-template agent ? last post 2026-11-24 03:01 DONE
- KV-SPINE-REWIRE agent ? last post 2026-11-24 03:00 STATUS
- HEAD-R18 agent ? last post 2026-11-24 02:58 DONE
- S81-ALLFIX-COL agent ? last post 2026-11-24 02:57 DONE
- QC-DEADIN-ROW agent ? last post 2026-11-24 02:56 DONE
- romw-1119-band agent ? last post 2026-11-24 02:48 DONE
- S81-OWN-LEAF agent ? last post 2026-11-24 02:47 DONE
- kv-pv-cap agent ? last post 2026-11-24 02:45 DONE
- S81-KV-CALENDAR agent ? last post 2026-11-24 02:38 DONE
- ROMW-LOSS-1124 agent ? last post 2026-11-24 02:37 RESULT
- romw-loss-1124 agent ? last post 2026-11-24 02:37 DONE
- KV-OWN-PV agent ? last post 2026-11-24 02:34 DONE
- S81-OWN-SLICE agent ? last post 2026-11-24 02:32 DONE
- head-west agent ? last post 2026-11-24 02:28 DONE
- QC-RESETPUB-SC agent ? last post 2026-11-24 02:24 DONE
- S81-OWN-MISC agent ? last post 2026-11-24 02:14 DONE
- QC-CB-SPREAD agent ? last post 2026-11-24 02:10 RENDER
- QC-DEPTH5 agent ? last post 2026-11-24 02:07 DIED
- qc-hold-0030 agent ? last post 2026-11-24 02:05 DONE
- S81-VPW-CONE agent ? last post 2026-11-24 02:00 DONE
- s81-rstsolve agent ? last post 2026-11-24 01:57 DONE
- s81-b1-rthops agent ? last post 2026-11-24 01:52 DONE
- NEARMISS-ECO-R1 agent ? last post 2026-11-24 01:46 DIED
- S81-SLICE-J9 agent ? last post 2026-11-24 01:45 DONE
- DLYRAM-RESET agent ? last post 2026-11-24 01:43 DONE

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-24 04:30 PST)
count_hourly: signed any plan 589 | current plan 485 | deferred re-sign 21 (hbm 1, head 10, qc 7, s81 3) | retired-plan 83 (head 1, kv 13, qc 41, s81 28)
- [ ] FAIL.S81.CORES 72/72 signed · open: none
- [ ] FAIL.S81.TYPES 48/394 signed · kit rows: held by die owner (plan event pending) 296 (bk_sel__t2, +295) · cancelled (superseded) 31 (col_h10_r0_p1__t1__cl911743eb, +30) · placed, route held 17 (col_h10_r0_p4__t1__pv07945c1e, +16)
- [ ] FAIL.HEAD.CORES 5/5 signed · open: none
- [ ] FAIL.HEAD.TYPES 25/27 signed · kit rows: held by die owner (plan event pending) 1 (hd_lep0N) · running (lint advisory) 1 (hd_lep0N_w)
- [ ] FAIL.QC.CORES 69/69 signed · open: none
- [ ] FAIL.QC.TYPES 80/127 signed · kit rows: held by die owner (plan event pending) 36 (cbf_q00__cl1b5a6458, +35) · running 2 · cancelled (superseded) 1 (glue) · placed, route held 1 (native59)
- [ ] FAIL.KV.CORES 83/83 signed · open: none
- [ ] FAIL.KV.TYPES 9/71 signed · kit rows: held by die owner (plan event pending) 55 (kv3_hg, +54) · running (lint advisory) 5 (kv3_hub_C, +4)
- [ ] FAIL.HBM.CORES 90/119 signed · open: no kit-wave row 19 (accel_smh_pt_w, hfd_coll_q3_body_ctl, hgi_sfu_opsa_group0, +12) · running, no result 9 (hfd_coll_q2n2_vm_core, hfd_hgi_vms_glue_nw_t, hgi_coll_tkm_m_tp192__root, +6) · shape: over cells/util/congestion 1 (hgi_dma_back_static_vp4_banks_cp
- [ ] FAIL.HBM.TYPES 4/81 signed · kit rows: none
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 0 current-event (+3 on a superseded plan block, not counted) (live check: ps/systemd/docker on all hosts; wave state: hub; full list lanes/STALE.tsv)
- [ ] STALE.S81 1 (cores 0, types 1) · by owner: FAIL-S81-1 1
  - type iqf__t1 · CANCELLED  STRUCT-STOP @ 2026-11-22 08:57 (43.6h) · owner FAIL-S81-1
- [ ] STALE.QC 1 (cores 0, types 1) · by owner: FAM-QC-FEFW-R3 1
  - type slw_fe_v2__clf110fab2 · CANCELLED geom SUPERSEDED @ 2026-11-23 15:40 (12.8h) · owner FAM-QC-FEFW-R3
- [ ] STALE.KV 1 (cores 0, types 1) · by owner: FAM-KV-HUBC-SYSC-R2 1
  - type kv3_sys_c · CANCELLED geom SUPERSEDED @ 2026-11-23 20:57 (7.6h) · owner FAM-KV-HUBC-SYSC-R2
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 317 commits / missing r708
- TOOLS-LAG qwen_kvsys 77 commits / missing none
- TOOLS-LAG s81 0 commits / missing none
- TOOLS-LAG s81_head 260 commits / missing r708
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 4781 taps in 44 types, 149 over 1650 sinks; insertion max 696 ps (p50 268, p90 285), skew max 107 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 265 taps in 3 types, 10 over 1650 sinks; insertion max 512 ps (p50 272, p90 307), skew max 94 ps; oversized taps: ins max 370 ps, skew max 64 ps
- TAP-INSERTION s81: 5542 taps in 87 types, 259 over 1650 sinks; insertion max 1000 ps (p50 466, p90 497), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 241 taps in 7 types, 8 over 1650 sinks; insertion max 504 ps (p50 463, p90 478), skew max 77 ps; oversized taps: ins max 499 ps, skew max 65 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-24 04:05 | tolera L32.88/112 units0 free161G | key-ca L19.27/112 units169 free226G | dear-c L18.93/128 units405 free106G | loved- L71.34/96 units61 free264G | outgoi L18.57/96 units148 free355G | renewe L50.52/96 units56 free637G | civil- L59.74/96 units30 free830G | viable L53.33/96 units24 free3999G | HOST-CAPS 1 flagged: epyc7:LOAD_CAP_FACTOR=1.2:EXPIRED; expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (275.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (275.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (275.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (275.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (275.9 h left); epyc10:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 ex
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  353G   92G  80% /
    04:30:29 up 31 days, 10 min, 176 users,  load average: 47.04, 39.56, 35.98

## ot-run status
    ot-run status: epyc2 admits 744 GB (avail 881, reserve 0, fresh 0, peak 8.1) load 16/128 run 14 threads 84/128 root 76% scratch 93 GB
    intel1 admits 763 GB (avail 838, reserve 0, fresh 0, peak 0) load 16/112 run 8 threads 128/112 root 30% scratch 226 GB
    localhost admits 665 GB (avail 843, reserve 0, fresh 0, peak 148.9) load 46/112 run 6 threads 70/112 root 80% scratch 163 GB
    epyc7 admits 311 GB (avail 543, reserve 0, fresh 0, peak 18.6) load 85/96 run 34 threads 351/96 root 51% scratch 251 GB
    epyc8 admits 600 GB (avail 828, reserve 0, fresh 0, peak 0) load 17/96 run 11 threads 198/96 root 46% scratch 352 GB
    epyc9 admits 650 GB (avail 753, reserve 0, fresh 0, peak 32.8) load 49/96 run 15 threads 155/96 root 53% scratch 458 GB
    epyc10 admits 842 GB (avail 901, reserve 0, fresh 0, peak 50) load 57/96 run 11 threads 277/96 root 48% scratch 690 GB
    epyc11 admits 343 GB (avail 430, reserve 0, fresh 0, peak 153.7) load 70/96 waiters 9:200 GB oldest 0.0 h run 38 threads 4730/96 root 5% scratch 3989 GB
    next 16-thread 32 GB job -> epyc2

## KIT-WAVE (autopilot log, last 6)
    2026-11-24 04:25:49 PST AUTOPILOT: KIT-WAVE HOLD-AUDIT HELD-BUT-LAUNCHED=0 HOLD-LEAK=0 TERM-UNREACHABLE=0 TERM-VARIANT=0 HOLD-SUPERSEDED=0 HOLD-ZERO-MATCH=0 PROOF-HELD=0 PILOT-DEADLOCK=0
    2026-11-24 04:26:17 PST AUTOPILOT: SUBMIT 2b18902a5bc7 qwen_compute/sle_st_b_v2__clfde1249e epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46
    2026-11-24 04:26:23 PST AUTOPILOT: UNDER-USE HELD SKIP-HELD 20: s81/col_h9_r0_p4__t1__cl8ef405e8__pv70731479 1 [owner FAM-S81-COL-H10-R4, 40.1 h, eta 11-23 04:15, FLAGGED OVERDUE]; s81/col_h9_r0_p2__t
    2026-11-24 04:29:24 PST AUTOPILOT: KIT-WAVE AUTO-VIEWS overlay: hbm=21 qwen_compute=5 s81=3
    2026-11-24 04:29:25 PST AUTOPILOT: KIT-WAVE src_overlay: hbm unreadable on epyc10; hold compares without it
    2026-11-24 04:29:37 PST AUTOPILOT: KIT-WAVE HOLD-AUTO-RELEASE summary: 2 keys released by their terms, 0 new this pass

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-24 04:18 PST DONE [QC-OPEN-SU] ot-run oth-ubuntu-1898216-1795520276 on renewed-glider: rc=0 after 2418 s, ended 12:18:12, log /srv/opentallas-scratch2/claude/QC-OPEN-SU/sc3/sc3full.ot, cmd: --mem 64 --threads 4 --hosts epyc9 --dir /srv/opentallas-scratch2/claude/QC-OPEN-SU/sc3 -- bash /srv/opentallas-scratch2/claude/QC-OPEN-SU/s
- 2026-11-24 04:18 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-939366-1795522400 on tolerant-swine: rc=0 after 320 s, ended 04:18:32, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_slw_st_a_v1__clb036e152_1124041222/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/pri
- 2026-11-24 04:18 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-937074-1795522395 on tolerant-swine: rc=0 after 328 s, ended 04:18:35, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_sle_st_a_v1__cl67389ecd_1124041216/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/pri
- 2026-11-24 04:18 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-949840-1795522425 on tolerant-swine: rc=0 after 300 s, ended 04:18:37, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_slw_st_a_v1__clfc5867a6__pvdf8e5ca4_1124041251/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q
- 2026-11-24 04:18 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-961311-1795522452 on tolerant-swine: rc=0 after 293 s, ended 04:18:58, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_slw_st_a_v1__clfc5867a6__pvf82a6c28_1124041317/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q
- 2026-11-24 04:18 PST DIED [ROM-WEIGHTS-1119] ot-run oth-ubuntu-3653972-1795522717 on civil-redfish: rc=1 after 22 s, ended 12:18:57, log /srv/opentallas-scratch2/claude/romw-1119/logs/qcverify_ctrl.log, cmd: --mem 8 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- /srv/opentallas-scratch2/claude/romw-1119/venv/bin/pyt | class=VERDICT-FAIL cause={"rank": 0, "verdict": "FAIL", "codes_chec
- 2026-11-24 04:19 PST DONE [QC-OPEN-SU] ot-run oth-ubuntu-1045560-1795522625 on loved-redfish: rc=0 after 120 s, ended 12:19:01 env=wave+2, log /srv/opentallas-scratch2/claude/QC-OPEN-SU/sta/run_sle_sc_v1__cl115da35f_4_cts_ff.ot, cmd: --mem 40 --threads 4 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/QC-OPEN-SU/sta -- bash /srv/opentallas-scratch2/claude/QC-OPEN-SU/s
- 2026-11-24 04:19 PST DONE [QC-OPEN-SU] ot-run oth-ubuntu-1045580-1795522625 on loved-redfish: rc=0 after 122 s, ended 12:19:03 env=wave+2, log /srv/opentallas-scratch2/claude/QC-OPEN-SU/sta/run_sle_sc_v1__cl115da35f_4_cts_tt.ot, cmd: --mem 40 --threads 4 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/QC-OPEN-SU/sta -- bash /srv/opentallas-scratch2/claude/QC-OPEN-SU/s
- 2026-11-24 04:19 PST DONE [S81-KVLEAF-T2-ARCH-R2] ot-run oth-ubuntu-3550410-1795522477 on civil-redfish: rc=0 after 271 s, ended 12:19:06, log /srv/opentallas-scratch2/claude/s81-kvleaf-t2-arch/blkproof/otrun.log, cmd: --mem 100 --threads 2 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/s81-kvleaf-t2-arch/blkproof -- bash run.sh
- 2026-11-24 04:19 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-955310-1795522439 on tolerant-swine: rc=0 after 317 s, ended 04:19:08, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_sle_st_a_v1__cl989804f6__cl18eece69_1124041303/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q
- 2026-11-24 04:19 PST DONE [romw-1119] ot-push-main otpush-civil-redfish-3662849 on civil-redfish: rc=0 after 21 s, ended 12:19:18, log none, cmd: ot-push-main 
- 2026-11-24 04:19 PST DONE [S81-ALLFIX-SVC] ot-run oth-ubuntu-3288937-1795522374 on dear-crayfish: rc=0 after 403 s, ended 04:19:35, log /home/ubuntu/coord/autopilot/private_specs/S81-ALLFIX-SVC/s81_serdes__t2_1124024359/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-SVC/serdes__
- 2026-11-24 04:20 PST DONE [S81-RSTSOLVE] ot-run oth-ubuntu-467379-1795521290 on loved-redfish: rc=0 after 1543 s, ended 12:20:30, log /srv/opentallas-scratch2/claude/s81-rstsolve/names_qc.otrun.log, cmd: --mem 40 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/s81-rstsolve -- bash -c cd /srv/opentallas-scratch2/claude/QC-ALLFIX/cH/tree &&
- 2026-11-24 04:22 PST DONE [QC-OPEN-COLL] ot-run oth-ubuntu-2428865-1795519500 on dear-crayfish: rc=0 after 3422 s, ended 04:22:00, log /srv/opentallas-scratch3/claude/QC-OPEN-COLL/cG/bindG.ot, cmd: --mem 64 --threads 8 --hosts epyc2 --dir /srv/opentallas-scratch3/claude/QC-OPEN-COLL -- bash /srv/opentallas-scratch3/claude/QC-OPEN-COLL/h
- 2026-11-24 04:22 PST DONE [ROM-WEIGHTS-1119] ot-run oth-ubuntu-3627683-1795522644 on civil-redfish: rc=0 after 278 s, ended 12:22:01, log /srv/opentallas-scratch2/claude/romw-1119/logs/qcverify_r6.log, cmd: --mem 12 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- /srv/opentallas-scratch2/claude/romw-1119/venv/bin/py
- 2026-11-24 04:22 PST DONE [ROM-WEIGHTS-1119] ot-run oth-ubuntu-3627691-1795522644 on civil-redfish: rc=0 after 279 s, ended 12:22:02, log /srv/opentallas-scratch2/claude/romw-1119/logs/qcverify_r4.log, cmd: --mem 12 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- /srv/opentallas-scratch2/claude/romw-1119/venv/bin/py
- 2026-11-24 04:22 PST DONE [ROM-WEIGHTS-1119] ot-run oth-ubuntu-3627694-1795522644 on civil-redfish: rc=0 after 279 s, ended 12:22:02, log /srv/opentallas-scratch2/claude/romw-1119/logs/qcverify_r7.log, cmd: --mem 12 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- /srv/opentallas-scratch2/claude/romw-1119/venv/bin/py
- 2026-11-24 04:22 PST DONE [ROM-WEIGHTS-1119] ot-run oth-ubuntu-3627682-1795522644 on civil-redfish: rc=0 after 285 s, ended 12:22:08, log /srv/opentallas-scratch2/claude/romw-1119/logs/qcverify_r5.log, cmd: --mem 12 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- /srv/opentallas-scratch2/claude/romw-1119/venv/bin/py
- 2026-11-24 04:22 PST DONE [ROM-WEIGHTS-1119] ot-run oth-ubuntu-3627674-1795522644 on civil-redfish: rc=0 after 293 s, ended 12:22:16, log /srv/opentallas-scratch2/claude/romw-1119/logs/qcverify_r2.log, cmd: --mem 12 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- /srv/opentallas-scratch2/claude/romw-1119/venv/bin/py
- 2026-11-24 04:22 PST DONE [ROM-WEIGHTS-1119] ot-run oth-ubuntu-3627672-1795522644 on civil-redfish: rc=0 after 297 s, ended 12:22:20, log /srv/opentallas-scratch2/claude/romw-1119/logs/qcverify_r3.log, cmd: --mem 12 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- /srv/opentallas-scratch2/claude/romw-1119/venv/bin/py
- 2026-11-24 04:22 PST DONE [ROM-WEIGHTS-1119] ot-run oth-ubuntu-3627695-1795522644 on civil-redfish: rc=0 after 305 s, ended 12:22:28, log /srv/opentallas-scratch2/claude/romw-1119/logs/qcverify_r1.log, cmd: --mem 12 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- /srv/opentallas-scratch2/claude/romw-1119/venv/bin/py
- 2026-11-24 04:22 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-1057213-1795522648 on tolerant-swine: rc=0 after 314 s, ended 04:22:35, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_sle_st_a_v1__cl989804f6__cled3c1d7b_1124041629/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4
- 2026-11-24 04:22 PST DONE [ROM-WEIGHTS-1119] ot-run oth-ubuntu-3627381-1795522644 on civil-redfish: rc=0 after 306 s, ended 12:22:29, log /srv/opentallas-scratch2/claude/romw-1119/logs/qcverify_r0.log, cmd: --mem 12 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- /srv/opentallas-scratch2/claude/romw-1119/venv/bin/py
- 2026-11-24 04:22 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-1078249-1795522699 on tolerant-swine: rc=0 after 273 s, ended 04:22:44, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_slw_st_a_v2__cl9f076a5c_1124041718/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/pr
- 2026-11-24 04:23 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-1107619-1795522747 on tolerant-swine: rc=0 after 275 s, ended 04:23:34, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_slw_st_a_v2__clf4365a62_1124041807/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/pr
- 2026-11-24 04:23 PST DONE [S81-T2-REFLOOR] ot-run oth-ubuntu-2114641-1795517515 on ubuntu: rc=0 after 5517 s, ended 04:23:48, log /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/D2bsb.log, cmd: --mem 250 --threads 8 --disk 20 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/s81-t2-refloor -- bash /srv/opentallas-scratch2/claude/
- 2026-11-24 04:23 PST INFO [AUTO-CLEAN -> COORD] 4-hourly cleanup report: intel1 freed 4 GB, top writers 4 h: QC-RSTCNT 59 GB, kv-own-pv 46 GB, kw43-wave-1109n 16 GB, ot-jobs 15 GB, QC-TTC-R2 14 GB | epyc2 freed 7 GB, top writers 4 h: SEAT-MATCH-AUDIT 59 GB, ot-jobs 22 GB, warm 6 GB, s81-rom-template 1 GB, auto-resign 0 GB | epyc7 freed 304 GB, top writers 4 h: QC-ALLFIX 62 GB, QC-F16-PRODUCER 62 GB, QC-DEADIN-ROW 5
- 2026-11-24 04:24 PST DIED [KV-RSTREACH] ot-run oth-ubuntu-3791393-1795523055 on civil-redfish: rc=1 after 4 s, ended 12:24:17, log none, cmd: --hosts epyc10 --mem 8 --threads 1 --dir /srv/opentallas-scratch2/claude/kv-rstreach/a5t -- python3 -I -B /srv/opentallas-scratch2/claude/kv | class=SETUP cause=died after 4 s with no log: the command failed at start (rc 1)
- 2026-11-24 04:24 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-1040770-1795522620 on tolerant-swine: rc=0 after 470 s, ended 04:24:42, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_sle_st_a_v2__pv30dda31f__pv88773f93_1124040959/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N
- 2026-11-24 04:24 PST DIED [QC-SLECTL-RESYN] ot-run oth-ubuntu-3509079-1795523076 on dear-crayfish: rc=5 after 8 s, ended 04:24:42, log /srv/opentallas-scratch2/claude/QC-SLECTL-RESYN/hs/fork.log, cmd: --mem 8 --threads 8 --hosts epyc2 --dir /srv/opentallas-scratch2/claude/QC-SLECTL-RESYN/hs -- python3 -I /srv/opentallas-scratch2/claude/rt/ | class=NO-PATTERN cause=TREE-FORK REFUSED: plain copy of 57.3 GB needs 107.
- 2026-11-24 04:24 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-1059985-1795522656 on tolerant-swine: rc=0 after 445 s, ended 04:24:54, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_sle_st_a_v2__pv30dda31f__pvd2ec7769_1124041026/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N
- 2026-11-24 04:25 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-1067294-1795522672 on tolerant-swine: rc=0 after 467 s, ended 04:25:32, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_sle_st_a_v2__pv4242de79_1124041052/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priva
- 2026-11-24 04:25 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-100): 1 event(s): hd_spn AUTO-GEOM PASS, ROUTE held: WAIT-VISUAL: view the placement and record a GEOM VERDICT with kit=epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f/items/hd_spn/gen/hd_spn
- 2026-11-24 04:25 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-103): 1 event(s): sle_st_b_v2__clfde1249e AUTO-GEOM PASS GEOM-ADVISORY aspect,channel_h,channel_v,clock_tap_empty,clock_tap_sinks,col_v,empty,fill,pin_reg_max,pin_reg_p90,r2r,r2r_count,relay_collapse: OWNER 11-03 targets-not-gates (only sign-off blocks; COORD 09:0x geom advisory) -> enqueued (epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/r
- 2026-11-24 04:26 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-3989507-1795522957 on tolerant-swine: rc=0 after 212 s, ended 04:26:02, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_hg_v1p6_1124041921/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hg
- 2026-11-24 04:26 PST DIED [KV-RSTREACH] ot-run oth-ubuntu-3844249-1795523186 on civil-redfish: rc=1 after 6 s, ended 12:26:30, log none, cmd: --hosts epyc10 --mem 8 --threads 1 --dir /srv/opentallas-scratch2/claude/kv-rstreach/a5t/launch_ro -- python3 -I -B /srv/opentallas-scratch2 | class=SETUP cause=died after 6 s with no log: the command failed at start (rc 1)
- 2026-11-24 04:26 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-4042615-1795523070 on tolerant-swine: rc=0 after 143 s, ended 04:26:47, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_hgi_v2__cl2862d491_1124042014/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hg
- 2026-11-24 04:27 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-4084359-1795523112 on tolerant-swine: rc=0 after 128 s, ended 04:27:14, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_hgi_v4_1124042053/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hg
- 2026-11-24 04:27 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-1088387-1795522716 on tolerant-swine: rc=0 after 526 s, ended 04:27:14, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_sle_st_a_v1__cl989804f6__cl18eece69_1124041150/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N
- 2026-11-24 04:27 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-4084354-1795523112 on tolerant-swine: rc=0 after 138 s, ended 04:27:24, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_hgi_v7_1124042131/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hg
- 2026-11-24 04:27 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-1083987-1795522707 on tolerant-swine: rc=0 after 547 s, ended 04:27:26, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_sle_st_a_v1__cl67389ecd_1124041121/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priva
- 2026-11-24 04:27 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-1117605-1795522766 on tolerant-swine: rc=0 after 496 s, ended 04:27:34, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_slw_st_a_v1__clfc5867a6__pvdf8e5ca4_1124041251/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N
- 2026-11-24 04:27 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-4080175-1795523109 on tolerant-swine: rc=0 after 154 s, ended 04:27:37, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_hgi_v5_1124042111/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hg
- 2026-11-24 04:27 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-1114517-1795522759 on tolerant-swine: rc=0 after 505 s, ended 04:27:37, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_slw_st_a_v1__clb036e152_1124041222/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priva
- 2026-11-24 04:27 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-4072979-1795523103 on tolerant-swine: rc=0 after 169 s, ended 04:27:46, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pc_v1__cl4ea58a5c__r828e1c2a5_1124042412/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLF
- 2026-11-24 04:27 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-4053923-1795523083 on tolerant-swine: rc=0 after 192 s, ended 04:27:48, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pc_v1__cl23f6a148_1124042356/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pc
- 2026-11-24 04:27 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-4090023-1795523118 on tolerant-swine: rc=0 after 158 s, ended 04:27:49, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_hub_Eo_1124042212/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hu
- 2026-11-24 04:27 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-4095760-1795523123 on tolerant-swine: rc=0 after 161 s, ended 04:27:57, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pc_v1__cl4ea58a5c__r877307f5d_1124042448/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLF
- 2026-11-24 04:27 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-1124141-1795522786 on tolerant-swine: rc=0 after 499 s, ended 04:27:57, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_slw_st_a_v1__clfc5867a6__pvf82a6c28_1124041317/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N
- 2026-11-24 04:28 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-4113092-1795523152 on tolerant-swine: rc=0 after 138 s, ended 04:28:04, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_hgi_v8_1124042150/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hg
- 2026-11-24 04:28 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-4095919-1795523123 on tolerant-swine: rc=0 after 171 s, ended 04:28:08, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pc_v1__cl4ea58a5c__r84d0332e1_1124042429/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLF
- 2026-11-24 04:28 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-4080817-1795523110 on tolerant-swine: rc=0 after 192 s, ended 04:28:15, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_hg_v3_1124041937/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hg
- 2026-11-24 04:28 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-4109060-1795523145 on tolerant-swine: rc=0 after 168 s, ended 04:28:27, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pc_v1__cl4ea58a5c__r884969661_1124042508/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLF
- 2026-11-24 04:28 PST DONE [CORE-TAP-BUDGET] ot-run oth-ubuntu-3670754-1795522752 on tolerant-swine: rc=0 after 568 s, ended 04:28:38, log none, cmd: --mem 60 --threads 5 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/CORE-TAP-BUDGET/parent -- bash -c cd /srv/opentallas-scratch2/clau
- 2026-11-24 04:28 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-4120386-1795523163 on tolerant-swine: rc=0 after 167 s, ended 04:28:44, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pc_v1__cl4ea58a5c__r8afe1e027_1124042528/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLF
- 2026-11-24 04:28 PST DONE [CORE-TAP-BUDGET] ot-run oth-ubuntu-3446035-1795522183 on tolerant-swine: rc=0 after 1151 s, ended 04:28:53, log none, cmd: --mem 80 --threads 12 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/CORE-TAP-BUDGET/regen -- bash /srv/opentallas-scratch2/claude/COR
- 2026-11-24 04:28 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-4108178-1795523144 on tolerant-swine: rc=0 after 201 s, ended 04:28:59, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_hgi_1124041954/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_h
- 2026-11-24 04:29 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-4134891-1795523185 on tolerant-swine: rc=0 after 166 s, ended 04:29:04, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pc_v1__cl4ea58a5c__r8c9cba7ae_1124042549/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLF
- 2026-11-24 04:29 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-4149671-1795523205 on tolerant-swine: rc=0 after 160 s, ended 04:29:18, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pc_v1__cl4ea58a5c__r8ef700d7c_1124042607/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLF
- 2026-11-24 04:29 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-4162260-1795523224 on tolerant-swine: rc=0 after 174 s, ended 04:29:51, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pc_v1__cl7f648944__r817e6c402_1124042628/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLF

