# COORD snapshot 2026-11-24 05:15 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: b335c93437b7
- 2026-11-23 15:15 PST MERGED [MERGE-QUEUE -> LAUNCH-GUARD] claude/launch-guard-viewpack-stage-1123@349ec165e6e -> main 005831fc27c -> ed4f6ade31b, no-ff merge, tags flow-20261117-mv-*. Gate: gate record from renewed-glider 2026-11-23 23:13 UTC on main becebaf53d9 (main since: no overlap): 8 test file(s) pass (+1 source dir(s) the tests name: physical/die_plan/hbm_arch_cores) (1 failure(s) also fail on main: baseline
- 2026-11-23 15:25 PST MERGED [MERGE-QUEUE -> LAUNCH-GUARD] claude/launch-guard-ghost-signed-1123@7a15228190e -> main ed4f6ade31b -> d0beea9d604, no-ff merge, tags flow-20261117-mw-*. Gate: gate record from renewed-glider 2026-11-23 23:24 UTC on main ed4f6ade31b: 184 test file(s) pass (+6 source dir(s) the tests name: physical/die_plan physical/die_plan/hbm/cores/harden physical/die_plan/hbm/cores/ports physical/die_
- 2026-11-23 15:25 PST MERGED [MERGE-QUEUE -> KV-D29-EMITGAPS] claude/kv-d29-emitgaps-1123@a4b13024a9a -> main d0beea9d604 -> bd54869e80c, no-ff merge, tags flow-20261117-mx-*. Gate: gate record from renewed-glider 2026-11-23 23:21 UTC on main ed4f6ade31b: 76 test file(s) pass (+18 source dir(s) the tests name: physical/asap7_memory_macros physical/asap7_memory_macros_pa physical/asap7_memory_macros_v2 physical/die_p

## READY/ASK with no later COORD post naming them (1, heuristic: check each)
- 2026-11-24 03:58 PST ASK [FAM-S81-SVC-OWN -> S81-ALLFIX-INT; cc COORD] Per COORD: how will the c8 kit wave launch the svc types so they COUNT (seal OK)? (a) kit_wave rows on a sealed c8 tree, or (b) ot-tree-fork of it? Please give the tree path and bind dir, and say whether your c8 wave already includes my 7: svc_lo rs t3, svc_hi pvso_entry t1/t2, svc_lo rs_w t1, svc_hi rs t4/t5/t6 (also rs t1,t2,t3, lo t1,t2,t4,t5

## Lane handoff files (age) and last queue post
- CODEX-TOKEN-1123: handoff 715 min old; last post none in recent queue
- CORE-TAP-BUDGET: handoff 89 min old; last post 2026-11-24 05:05 DONE
- DLYRAM-RESET: handoff 107 min old; last post 2026-11-24 01:43 DONE
- EPYC11-ONBOARD-FINISH: handoff 290 min old; last post 2026-11-24 00:01 DONE
- FABLE-OPEN-HEAD-QC: handoff 1100 min old; last post 2026-11-23 10:54 REPORT-2
- FABLE-OPEN-KV: handoff 677 min old; last post 2026-11-23 18:32 DONE
- FABLE-OPEN-S81-A-rc37: handoff 804 min old; last post none in recent queue
- FABLE-OPEN-S81-A-x14: handoff 792 min old; last post none in recent queue
- FABLE-OPEN-S81-A: handoff 790 min old; last post 2026-11-23 16:03 DONE
- FABLE-OPEN-S81-B-rc72: handoff 1363 min old; last post none in recent queue
- FABLE-OPEN-S81-B-x9: handoff 1068 min old; last post none in recent queue
- FABLE-OPEN-S81-B: handoff 804 min old; last post 2026-11-23 11:21 DONE
- FABLE-OPEN-S81-SVC: handoff 806 min old; last post 2026-11-23 14:54 DONE
- FABLE-RC-ALL-KV-QC-HANDOVER: handoff 591 min old; last post none in recent queue
- FABLE-RC-ALL: handoff 0 min old; last post 2026-11-23 17:05 DIED
- FABLE-RC-KV: handoff 3 min old; last post none in recent queue
- FABLE-RC-QC-SU: handoff 494 min old; last post none in recent queue
- FABLE-RC-QC: handoff 190 min old; last post 2026-11-23 01:26 DONE
- FABLE-UNC-HEAD: handoff 1104 min old; last post 2026-11-23 04:00 GATE-PASS
- FABLE-UNC-S81-LEAF: handoff 1375 min old; last post 2026-11-23 06:19 STATUS
- FAM-KV-HUBC-SYSC-R2: handoff 1102 min old; last post 2026-11-23 18:15 DIED
- FAM-KV-HUBWO-S1: handoff 431 min old; last post 2026-11-23 22:03 DONE
- FAM-S81-DSDV-R1: handoff 804 min old; last post 2026-11-23 10:02 DIED
- FIX-LEDGER: handoff 781 min old; last post 2026-11-23 02:45 ASK
- FIX-S81-SVC-WESTRIP: handoff 796 min old; last post 2026-11-23 15:58 CORRECTION
- FIX-S81-XG-STN: handoff 1359 min old; last post 2026-11-23 12:31 DONE
- FLOW-CLKGRT-R2: handoff 780 min old; last post 2026-11-23 16:13 RESULT
- FLOW-OPS-R3-CODEX-1123: handoff 715 min old; last post none in recent queue
- FLOW-OPS-R3: handoff 14 min old; last post 2026-11-24 04:46 DONE
- GENDRY-KITRTL: handoff 502 min old; last post 2026-11-23 21:38 DONE
- HEAD-100-unit-table-signedview: handoff 11 min old; last post none in recent queue
- HEAD-100-unit-table: handoff 4 min old; last post none in recent queue
- HEAD-EAST-REPLAN: handoff 90 min old; last post 2026-11-24 03:41 DONE
- HEAD-R18: handoff 204 min old; last post 2026-11-24 02:58 DONE
- HEAD-S2-RESEAL: handoff 478 min old; last post 2026-11-23 21:15 DONE
- HEAD-WEST: handoff 300 min old; last post 2026-11-24 04:14 DONE
- KV-ALLFIX: handoff 682 min old; last post 2026-11-24 05:11 DONE
- KV-ASTK-EARLYTAP: handoff 395 min old; last post 2026-11-23 22:39 DONE
- KV-D29-PACKAGE: handoff 797 min old; last post none in recent queue
- KV-D29: handoff 459 min old; last post 2026-11-23 21:39 NOTE
- KV-DIE-SEAMHOLD: handoff 372 min old; last post 2026-11-23 23:01 DONE
- KV-HG-CAP: handoff 20 min old; last post 2026-11-24 04:54 CORRECTION
- KV-HR-DEEPCLK: handoff 122 min old; last post 2026-11-24 04:14 DONE
- KV-HUB-EPZO: handoff 466 min old; last post 2026-11-23 21:29 STAND-DOWN
- KV-HUB-HOLD: handoff 407 min old; last post 2026-11-23 22:55 DONE
- KV-INCORE-R2: handoff 3 min old; last post 2026-11-24 05:05 DONE
- KV-OPEN-FWDCLK: handoff 533 min old; last post 2026-11-23 20:20 DIED
- KV-OPEN-INCORE: handoff 566 min old; last post 2026-11-23 20:20 DONE
- KV-PREGRT-STALL: handoff 488 min old; last post 2026-11-23 21:06 STAND-DOWN
- KV-PV-CAP: handoff 225 min old; last post 2026-11-24 01:28 DONE
- KV-PV-EDGESTRIP: handoff 60 min old; last post 2026-11-24 04:13 DONE
- KV-PV-RSTRELAY: handoff 374 min old; last post 2026-11-23 22:58 DONE
- KV-R8-LANELOSS: handoff 523 min old; last post 2026-11-23 20:32 STAND-DOWN
- KV-RCOLL-PHASE: handoff 444 min old; last post none in recent queue
- KV-RCOLL-REBASE: handoff 424 min old; last post 2026-11-23 22:08 DONE
- KV-RINGMAC-R1: handoff 805 min old; last post 2026-11-23 14:46 DIED
- KV-RSTNAME-REMAP: handoff 444 min old; last post 2026-11-23 21:48 DONE
- KV-RSTREACH: handoff 24 min old; last post 2026-11-24 04:47 DONE
- KV-SENDER-SKEW: handoff 23 min old; last post 2026-11-24 01:08 DONE
- KV-SPINE-REWIRE: handoff 70 min old; last post 2026-11-24 05:14 DIED
- KV-TAPSPLIT-HGPV: handoff 105 min old; last post 2026-11-24 03:29 DONE
- KVLEAF-MASTERS-from-ARCH-R2: handoff 591 min old; last post none in recent queue
- KVLEAF-MASTERS: handoff 389 min old; last post 2026-11-23 22:45 DONE
- LANDING-WRAP-TOOL: handoff 412 min old; last post 2026-11-23 22:22 LIVE
- LANDREMAP-RSTNODE: handoff 440 min old; last post 2026-11-23 21:56 STAND-DOWN
- LANEAGE-SWEEP: handoff 19 min old; last post 2026-11-24 05:10 DIED
- LAUNCH-GUARD: handoff 714 min old; last post 2026-11-23 15:49 DONE
- LEC-AUTOFILL: handoff 382 min old; last post 2026-11-24 03:30 DIED
- LEC-VACUITY-SWEEP: handoff 342 min old; last post 2026-11-23 23:31 DIED
- OPS-SUPPORT-R1: handoff 805 min old; last post 2026-11-23 20:03 EPYC8-FREED
- OPUS-FIX-HEAD-LEP0N-R8: handoff 1399 min old; last post none in recent queue
- OPUS-FIX-KV-PV-R7: handoff 814 min old; last post 2026-11-23 20:58 DIED
- OPUS-FIX-QC-V4-R2: handoff 632 min old; last post 2026-11-24 01:24 DIED
- PRE-QC-GENCHECK: handoff 145 min old; last post 2026-11-24 02:50 STAND-DOWN
- PRECHECK-CELLCAP: handoff 359 min old; last post 2026-11-23 23:14 RT
- PRECHECK-DERIVED-DROP: handoff 400 min old; last post 2026-11-23 22:36 DONE
- PRECHECK-LEDGER-R3: handoff 75 min old; last post 2026-11-24 04:47 DONE
- QC-ALLFIX-COLL: handoff 94 min old; last post 2026-11-23 18:47 DONE
- QC-ALLFIX-SU: handoff 673 min old; last post 2026-11-24 01:12 HANDOFF
- QC-ALLFIX: handoff 648 min old; last post 2026-11-24 05:09 DONE
- QC-F16-PRODUCER: handoff 58 min old; last post 2026-11-24 03:24 DONE
- QC-FW-CAP: handoff 128 min old; last post 2026-11-24 03:13 ACK
- QC-GLUE-PADBIND: handoff 111 min old; last post 2026-11-24 03:32 STAND-DOWN
- QC-HC1-CLKENTRY: handoff 80 min old; last post 2026-11-24 03:54 STAND-DOWN
- QC-INHOLD-BUDGET: handoff 67 min old; last post 2026-11-24 05:10 DONE
- QC-OPEN-COLL: handoff 86 min old; last post 2026-11-24 04:22 DONE
- QC-OPEN-STA: handoff 48 min old; last post 2026-11-24 05:14 DONE
- QC-OPEN-SU: handoff 57 min old; last post 2026-11-24 04:52 DONE
- QC-RSTCNT: handoff 99 min old; last post 2026-11-24 03:26 DIED
- QC-SLECTL-RESYN: handoff 214 min old; last post 2026-11-24 05:14 DONE
- QC-STB-CAP: handoff 357 min old; last post 2026-11-23 23:15 DONE
- QC-SUL1-STN-ROW: handoff 442 min old; last post 2026-11-23 21:51 DONE
- QC-TTC-R2: handoff 95 min old; last post 2026-11-24 04:12 DONE
- QC-TTC-RETIME: handoff 552 min old; last post 2026-11-23 20:45 DONE
- QC-V4-CB: handoff 1059 min old; last post 2026-11-23 14:06 DONE
- QC-V4-COLL: handoff 1366 min old; last post 2026-11-23 07:49 DONE
- QC-V4: handoff 392 min old; last post 2026-11-23 23:33 ADOPT-BIND
- RELEC-1122: handoff 272 min old; last post 2026-11-24 03:11 DONE
- S81-ALLFIX-COL: handoff 79 min old; last post 2026-11-24 02:57 DONE
- S81-ALLFIX-INT: handoff 700 min old; last post 2026-11-24 04:15 ANSWERS
- S81-ALLFIX-MULTI: handoff 636 min old; last post 2026-11-23 18:38 NOTE
- S81-ALLFIX-SLICE: handoff 606 min old; last post 2026-11-23 19:56 DONE
- S81-ALLFIX-SVC-ENGMON: handoff 623 min old; last post none in recent queue
- S81-ALLFIX-SVC-L0: handoff 662 min old; last post none in recent queue
- S81-ALLFIX-SVC-MISC: handoff 691 min old; last post none in recent queue
- S81-ALLFIX-SVC-SERDESRING: handoff 25 min old; last post none in recent queue
- S81-ALLFIX-SVC: handoff 533 min old; last post 2026-11-24 05:13 DIED
- S81-C8-TYPES: handoff 67 min old; last post none in recent queue
- S81-COL-J9: handoff 799 min old; last post 2026-11-23 15:53 DONE
- S81-J9-ASSEMBLY-R6: handoff 291 min old; last post 2026-11-24 04:51 DIED
- S81-KV-CALENDAR: handoff 192 min old; last post 2026-11-24 02:38 DONE
- S81-KVLEAF-T2-ARCH-R2: handoff 337 min old; last post 2026-11-24 05:13 DONE
- S81-LEAF-J9: handoff 710 min old; last post 2026-11-23 17:22 DONE
- S81-LEPFLF-HOLD: handoff 213 min old; last post 2026-11-24 01:02 DONE
- S81-MISC-SERDES-J9: handoff 709 min old; last post 2026-11-23 17:05 DONE
- S81-OPEN-CLOCK: handoff 399 min old; last post 2026-11-23 21:58 DONE
- S81-OPEN-DEMAND: handoff 399 min old; last post 2026-11-23 20:59 DONE
- S81-OPEN-ENGCHAN: handoff 599 min old; last post none in recent queue
- S81-OPEN-FSTART: handoff 316 min old; last post 2026-11-23 22:17 DIED
- S81-OPEN-LEAFBAND: handoff 322 min old; last post 2026-11-23 23:42 DONE
- S81-OPEN-SVCLO: handoff 452 min old; last post 2026-11-23 21:41 DIED
- S81-OWN-KVLEAF-LEP: handoff 280 min old; last post 2026-11-24 00:14 ASK
- S81-PROBE-LAUNCH: handoff 316 min old; last post 2026-11-24 03:20 DONE
- S81-ROM-TEMPLATE: handoff 132 min old; last post 2026-11-24 03:09 PROGRESS
- S81-SLICE-J9: handoff 361 min old; last post 2026-11-24 01:45 DONE
- S81-SVC-J9: handoff 767 min old; last post 2026-11-23 16:01 DONE
- S81-T2-REFLOOR: handoff 237 min old; last post 2026-11-24 04:47 DONE
- S81-TYPES-CODEX-1123: handoff 715 min old; last post none in recent queue
- SEAT-MATCH-AUDIT: handoff 215 min old; last post 2026-11-24 04:14 DONE
- TAP-GRID-R6: handoff 768 min old; last post 2026-11-23 16:24 DONE
- TL-QCPHYSDB: handoff 1297 min old; last post none in recent queue
- VIS-DIE-S81: handoff 1366 min old; last post 2026-11-23 07:06 DONE

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 182; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 85 live
- QC-SLECTL-RESYN agent ? last post 2026-11-24 05:14 DONE
- QC-OPEN-STA agent ? last post 2026-11-24 05:14 DONE
- KV-SPINE-REWIRE agent ? last post 2026-11-24 05:14 DIED
- QC-CB-PROBE agent ? last post 2026-11-24 05:13 DONE
- S81-KVLEAF-T2-ARCH-R2 agent ? last post 2026-11-24 05:13 DONE
- S81-ALLFIX-SVC agent ? last post 2026-11-24 05:13 DIED
- S81-SERDES-TAPSKEW agent ? last post 2026-11-24 05:12 DIED
- KV-ALLFIX agent ? last post 2026-11-24 05:11 DONE
- S81-OWN-LEAF agent ? last post 2026-11-24 05:11 DONE
- QC-INHOLD-BUDGET agent ? last post 2026-11-24 05:10 DONE
- LANEAGE-SWEEP agent ? last post 2026-11-24 05:10 DIED
- QC-ALLFIX agent ? last post 2026-11-24 05:09 DONE
- FOLLOWUP-HEAD agent ? last post 2026-11-24 05:08 ACK
- MERGE-QUEUE agent ? last post 2026-11-24 05:07 STATE
- KV-OWN-HG agent ? last post 2026-11-24 05:07 DONE
- KV-INCORE-R2 agent ? last post 2026-11-24 05:05 DONE
- CORE-TAP-BUDGET agent ? last post 2026-11-24 05:05 DONE
- lanes agent ? last post 2026-11-24 05:02 DONE
- AUTOPILOT agent ? last post 2026-11-24 04:59 NEEDS-ACTION
- ROM-WEIGHTS-1119 agent ? last post 2026-11-24 04:58 DIED
- FOLLOWUP-S81 agent ? last post 2026-11-24 04:56 FOLLOWUP
- KV-HG-CAP agent ? last post 2026-11-24 04:54 CORRECTION
- BIND-ALL-ERRORS agent ? last post 2026-11-24 04:52 DONE
- NOPROG-FIX-1115 agent ? last post 2026-11-24 04:52 STATE
- QC-OPEN-SU agent ? last post 2026-11-24 04:52 DONE
- KV-PC-TAP agent ? last post 2026-11-24 04:52 DONE
- romw-1119 agent ? last post 2026-11-24 04:52 DONE
- S81-J9-ASSEMBLY-R6 agent ? last post 2026-11-24 04:51 DIED
- s81-t2-refloor agent ? last post 2026-11-24 04:50 DONE
- KV-RSTREACH agent ? last post 2026-11-24 04:47 DONE
- PRECHECK-LEDGER-R3 agent ? last post 2026-11-24 04:47 DONE
- S81-T2-REFLOOR agent ? last post 2026-11-24 04:47 DONE
- FLOW-OPS-R3 agent ? last post 2026-11-24 04:46 DONE
- NOPROG-WATCHDOG agent ? last post 2026-11-24 04:45 STATE
- qwen_compute agent ? last post 2026-11-24 04:44 KIT-WAVE
- s81_head agent ? last post 2026-11-24 04:44 KIT-WAVE
- s81 agent ? last post 2026-11-24 04:44 KIT-WAVE
- QC-FWDCLK-REPOINT agent ? last post 2026-11-24 04:40 DONE
- TAPKEY-SITE agent ? last post 2026-11-24 04:36 DONE
- S81-START-COLLECTOR agent ? last post 2026-11-24 04:32 DIED
- FLEET-WATCH-1015 agent ? last post 2026-11-24 04:30 CANCELLED
- AUTO-CLEAN agent ? last post 2026-11-24 04:23 INFO
- QC-OPEN-COLL agent ? last post 2026-11-24 04:22 DONE
- S81-RSTSOLVE agent ? last post 2026-11-24 04:20 DONE
- CBC-RULES-1119 agent ? last post 2026-11-24 04:17 HOURLY
- QC-CBX-CLOCK agent ? last post 2026-11-24 04:17 DIED
- S81-ALLFIX-INT agent ? last post 2026-11-24 04:15 ANSWERS
- SEAT-MATCH-AUDIT agent ? last post 2026-11-24 04:14 DONE
- HEAD-WEST agent ? last post 2026-11-24 04:14 DONE
- KV-PV-EDGESTRIP agent ? last post 2026-11-24 04:13 DONE
- KIT-WAVE agent ? last post 2026-11-24 04:13 NEEDS-LANE
- QC-TTC-R2 agent ? last post 2026-11-24 04:12 DONE
- qc-cbx-clock-lane agent ? last post 2026-11-24 04:09 DONE
- FAM-S81-SVC-OWN agent ? last post 2026-11-24 03:58 ASK
- FOLLOWUP-QC agent ? last post 2026-11-24 03:44 CLOSED
- bind-elab-par agent ? last post 2026-11-24 03:41 DONE
- HEAD-EAST-REPLAN agent ? last post 2026-11-24 03:41 DONE
- BIND-ELAB-PAR agent ? last post 2026-11-24 03:38 DONE
- QC-GENDRY-TRIAGE agent ? last post 2026-11-24 03:37 DONE
- LEC-AUTOFILL agent ? last post 2026-11-24 03:30 DIED
- KV-TAPSPLIT-HGPV agent ? last post 2026-11-24 03:29 DONE
- KW-REPICK-PIN agent ? last post 2026-11-24 03:29 DONE
- FLEET-OPS-R agent ? last post 2026-11-24 03:28 ALERT
- QC-RSTCNT agent ? last post 2026-11-24 03:26 DIED
- QC-F16-PRODUCER agent ? last post 2026-11-24 03:24 DONE
- s81-start-collector agent ? last post 2026-11-24 03:21 DONE
- S81-PROBE-LAUNCH agent ? last post 2026-11-24 03:20 DONE
- S81-SLICE-C-OWN agent ? last post 2026-11-24 03:20 DONE
- QC-FW-CAP agent ? last post 2026-11-24 03:13 ACK
- RELEC-1122 agent ? last post 2026-11-24 03:11 DONE
- BIND-UNDRIVEN-IN agent ? last post 2026-11-24 03:09 DONE
- HOLD-OVERDUE agent ? last post 2026-11-24 03:02 ALERT
- s81-rom-template agent ? last post 2026-11-24 03:01 DONE
- HEAD-R18 agent ? last post 2026-11-24 02:58 DONE
- S81-ALLFIX-COL agent ? last post 2026-11-24 02:57 DONE
- QC-DEADIN-ROW agent ? last post 2026-11-24 02:56 DONE
- romw-1119-band agent ? last post 2026-11-24 02:48 DONE
- kv-pv-cap agent ? last post 2026-11-24 02:45 DONE
- S81-KV-CALENDAR agent ? last post 2026-11-24 02:38 DONE
- ROMW-LOSS-1124 agent ? last post 2026-11-24 02:37 RESULT
- romw-loss-1124 agent ? last post 2026-11-24 02:37 DONE
- KV-OWN-PV agent ? last post 2026-11-24 02:34 DONE
- S81-OWN-SLICE agent ? last post 2026-11-24 02:32 DONE
- head-west agent ? last post 2026-11-24 02:28 DONE
- QC-RESETPUB-SC agent ? last post 2026-11-24 02:24 DONE

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-24 05:15 PST)
count_hourly: signed any plan 589 | current plan 485 | deferred re-sign 21 (hbm 1, head 10, qc 7, s81 3) | retired-plan 83 (head 1, kv 13, qc 41, s81 28)
- [ ] FAIL.S81.CORES 72/72 signed · open: none
- [ ] FAIL.S81.TYPES 48/394 signed · kit rows: held by die owner (plan event pending) 296 (bk_sel__t2, +295) · cancelled (superseded) 31 (col_h10_r0_p1__t1__cl911743eb, +30) · placed, route held 17 (col_h10_r0_p4__t1__pv07945c1e, +16)
- [ ] FAIL.HEAD.CORES 5/5 signed · open: none
- [ ] FAIL.HEAD.TYPES 25/27 signed · kit rows: held by die owner (plan event pending) 1 (hd_lep0N) · running (lint advisory) 1 (hd_lep0N_w)
- [ ] FAIL.QC.CORES 69/69 signed · open: none
- [ ] FAIL.QC.TYPES 80/127 signed · kit rows: held by die owner (plan event pending) 36 (cbf_q00__cl1b5a6458, +35) · running 3 · cancelled (superseded) 1 (glue)
- [ ] FAIL.KV.CORES 83/83 signed · open: none
- [ ] FAIL.KV.TYPES 9/71 signed · kit rows: held by die owner (plan event pending) 55 (kv3_hg, +54) · running (lint advisory) 5 (kv3_hub_C, +4)
- [ ] FAIL.HBM.CORES 90/119 signed · open: no kit-wave row 19 (accel_smh_pt_w, hfd_coll_q3_body_ctl, hgi_sfu_opsa_group0, +12) · running, no result 9 (hfd_coll_q2n2_vm_core, hfd_hgi_vms_glue_nw_t, hgi_coll_tkm_m_tp192__root, +6) · shape: over cells/util/congestion 1 (hgi_dma_back_static_vp4_banks_cp
- [ ] FAIL.HBM.TYPES 4/81 signed · kit rows: none
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 0 current-event (+2 on a superseded plan block, not counted) (live check: ps/systemd/docker on all hosts; wave state: hub; full list lanes/STALE.tsv)
- [ ] STALE.S81 1 (cores 0, types 1) · by owner: FAIL-S81-1 1
  - type iqf__t1 · CANCELLED  STRUCT-STOP @ 2026-11-22 08:57 (44.3h) · owner FAIL-S81-1
- [ ] STALE.QC 1 (cores 0, types 1) · by owner: FAM-QC-FEFW-R3 1
  - type slw_fe_v2__clf110fab2 · CANCELLED geom SUPERSEDED @ 2026-11-23 15:40 (13.6h) · owner FAM-QC-FEFW-R3
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 324 commits / missing r708
- TOOLS-LAG qwen_kvsys 84 commits / missing none
- TOOLS-LAG s81 0 commits / missing none
- TOOLS-LAG s81_head 267 commits / missing r708
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 3129 taps in 28 types, 111 over 1650 sinks; insertion max 696 ps (p50 268, p90 286), skew max 107 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 265 taps in 3 types, 10 over 1650 sinks; insertion max 512 ps (p50 272, p90 307), skew max 94 ps; oversized taps: ins max 370 ps, skew max 64 ps
- TAP-INSERTION s81: 5402 taps in 83 types, 259 over 1650 sinks; insertion max 1000 ps (p50 468, p90 498), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 168 taps in 5 types, 6 over 1650 sinks; insertion max 501 ps (p50 463, p90 478), skew max 71 ps; oversized taps: ins max 499 ps, skew max 65 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-24 05:05 | tolera L17.43/112 units0 free149G | key-ca L37.71/112 units181 free188G | dear-c L58.62/128 units420 free105G | loved- L90.03/96 units70 free224G | outgoi L15.13/96 units148 free348G | renewe L42.93/96 units58 free391G | civil- L114.70/96 units56 free525G | viable L78.88/96 units37 free3966G | HOST-CAPS 1 flagged: epyc7:LOAD_CAP_FACTOR=1.2:EXPIRED; expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (274.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (274.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (274.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (274.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (274.9 h left); epyc10:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 e
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  353G   92G  80% /
    05:15:25 up 31 days, 55 min, 177 users,  load average: 16.16, 17.60, 23.49

## ot-run status
    ot-run status: epyc2 admits 301 GB (avail 683, reserve 0, fresh 0, peak 102.4) load 88/128 run 29 threads 204/128 root 79% scratch 103 GB
    intel1 admits 323 GB (avail 774, reserve 0, fresh 0, peak 43.2) load 73/112 run 21 threads 232/112 root 31% scratch 190 GB
    localhost admits 749 GB (avail 894, reserve 0, fresh 0, peak 37.7) load 16/112 run 2 threads 46/112 root 80% scratch 151 GB
    epyc7 admits 213 GB (avail 523, reserve 0, fresh 0, peak 30.7) load 123/96 waiters 1:32 GB oldest 0.0 h run 42 threads 445/96 LOADCAP root 51% scratch 303 GB
    epyc8 admits 525 GB (avail 836, reserve 0, fresh 0, peak 10.2) load 34/96 run 18 threads 248/96 root 46% scratch 303 GB
    epyc9 admits 580 GB (avail 758, reserve 0, fresh 0, peak 12.1) load 54/96 run 23 threads 264/96 root 53% scratch 374 GB
    epyc10 admits 0 GB (avail 882, reserve 0, fresh 0, peak 60.5) load 108/96 waiters 1:16 GB oldest 0.1 h run 31 threads 315/96 root 48% scratch 469 GB
    epyc11 admits 402 GB (avail 505, reserve 0, fresh 0, peak 159.9) load 74/96 waiters 56:2928 GB oldest 0.8 h run 34 threads 5494/96 root 5% scratch 3908 GB
    next 16-thread 32 GB job -> localhost
    ot-run status: BLOCKED 37 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hub_Eo_112404215
    ot-run status: BLOCKED 35 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pc_v1__cl23f6a14
    ot-run status: BLOCKED 32 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hgi_v2__cl2862d4
    ot-run status: BLOCKED 30 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hgi_v2__cle00153
    ot-run status: BLOCKED 30 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hg_v1p6_11240419
    ot-run status: BLOCKED 29 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hgi_v5_112404205
    ot-run status: BLOCKED 28 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hg_v3_1124041927
    ot-run status: BLOCKED 26 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pc_v1__cl7f64894
    ot-run status: BLOCKED 25 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hgi_v8_112404213
    ot-run status: BLOCKED 23 min KV-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_io_ft_11
    ot-run status: BLOCKED 22 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pc_v1__cl7f64894
    ot-run status: BLOCKED 22 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pc_v1__cl7f64894
    ot-run status: BLOCKED 20 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pc_v1__cl7f64894
    ot-run status: BLOCKED 18 min KV-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_io_ft_v1
    ot-run status: BLOCKED 16 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_sys_c_1124044010
    ot-run status: BLOCKED 16 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pv_v2e_112404321
    ot-run status: BLOCKED 16 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pv_v4_1124043356
    ot-run status: BLOCKED 16 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pv_1124043038/ge
    ot-run status: BLOCKED 14 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hgi_v4_112404203
    ot-run status: BLOCKED 14 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pv_v5_1124043521

## KIT-WAVE (autopilot log, last 6)
    2026-11-24 05:10:23 PST AUTOPILOT: KIT-WAVE PLAN-ROWS s81_head: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-24 05:10:24 PST AUTOPILOT: KIT-WAVE HOLD-AUDIT HELD-BUT-LAUNCHED=0 HOLD-LEAK=0 TERM-UNREACHABLE=0 TERM-VARIANT=0 HOLD-SUPERSEDED=0 HOLD-ZERO-MATCH=0 PROOF-HELD=0 PILOT-DEADLOCK=0
    2026-11-24 05:10:45 PST AUTOPILOT: UNDER-USE HELD SKIP-HELD 20: s81/col_h9_r0_p4__t1__cl8ef405e8__pv70731479 1 [owner FAM-S81-COL-H10-R4, 40.8 h, eta 11-23 04:15, FLAGGED OVERDUE]; s81/col_h9_r0_p2__t
    2026-11-24 05:13:50 PST AUTOPILOT: KIT-WAVE AUTO-VIEWS overlay: hbm=21 qwen_compute=5 s81=3
    2026-11-24 05:13:51 PST AUTOPILOT: KIT-WAVE src_overlay: hbm unreadable on epyc10; hold compares without it
    2026-11-24 05:13:52 PST AUTOPILOT: KIT-WAVE HOLD-AUTO-RELEASE summary: 2 keys released by their terms, 0 new this pass

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-24 05:00 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-2216774-1795525006 on tolerant-swine: rc=0 after 246 s, ended 05:00:45, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_sle_st_a_v2__pv30dda31f__pvd2ec7769_1124041026/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9
- 2026-11-24 05:00 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-2218913-1795525010 on tolerant-swine: rc=0 after 245 s, ended 05:00:47, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_sle_st_a_v2__pv30dda31f__pv88773f93_1124040959/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9
- 2026-11-24 05:01 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-1079752-1795525087 on tolerant-swine: rc=0 after 188 s, ended 05:01:09, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pv_v3ne_1124043350/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_p
- 2026-11-24 05:01 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-2236348-1795525044 on tolerant-swine: rc=0 after 244 s, ended 05:01:20, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_sle_st_a_v2__pv4242de79_1124041052/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priv
- 2026-11-24 05:02 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-945161-1795524867 on tolerant-swine: rc=0 after 463 s, ended 05:02:04, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pv_v5ne_1124043641/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_p
- 2026-11-24 05:02 PST DONE [lanes] ot-push-main otpush-tolerant-swine-1419220 on tolerant-swine: rc=0 after 0 s, ended 05:02:10, log none, cmd: ot-push-main --help
- 2026-11-24 05:02 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-905846-1795524795 on tolerant-swine: rc=0 after 556 s, ended 05:02:24, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pv_v8_1124043920/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_p
- 2026-11-24 05:02 PST STARTED [-> COORD; cc KV-ALLFIX] FABLE FLOW REVIEW #2 tool fix: kit_wave private-spec --bind-out now reads provenance_bind.json (asbuilt + clock landing) on the gen host, both --tree and --bind-out branches (apply_bind_landing). Commit 281b6f7cd4 in ot-push-main gate now; rt publication check follows.
- 2026-11-24 05:02 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-952063-1795524875 on tolerant-swine: rc=0 after 502 s, ended 05:02:50, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pv_v2n_1124043250/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_p
- 2026-11-24 05:02 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-1135364-1795525165 on tolerant-swine: rc=0 after 211 s, ended 05:02:50, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pv_v2_1124043212/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_p
- 2026-11-24 05:04 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-997181-1795524947 on tolerant-swine: rc=0 after 500 s, ended 05:04:00, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pv_v3e_1124043332/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_p
- 2026-11-24 05:04 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-838254-1795524678 on tolerant-swine: rc=0 after 780 s, ended 05:04:12, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pv_v6_1124043703/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_p
- 2026-11-24 05:04 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-1037997-1795525014 on tolerant-swine: rc=0 after 490 s, ended 05:04:58, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pv_v5n_1124043619/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_p
- 2026-11-24 05:05 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-2334563-1795525240 on tolerant-swine: rc=0 after 282 s, ended 05:05:14, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_sle_st_a_v1__cl989804f6__cl18eece69_1124041150/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9
- 2026-11-24 05:05 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-2311566-1795525202 on tolerant-swine: rc=0 after 324 s, ended 05:05:19, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_slw_st_a_v1__clb036e152_1124041222/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priv
- 2026-11-24 05:05 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-1014794-1795524972 on tolerant-swine: rc=0 after 560 s, ended 05:05:26, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pv_v7e_1124043858/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_p
- 2026-11-24 05:05 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-790599-1795524586 on tolerant-swine: rc=0 after 949 s, ended 05:05:29, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pv_v1_1124043114/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_p
- 2026-11-24 05:05 PST DONE [KV-INCORE-R2] ot-run oth-ubuntu-3442760-1795520502 on viable-ram: rc=0 after 5028 s, ended 13:05:28, log /srv/opentallas-scratch2/claude/kv-incore-r2/c2t.otrun.log, cmd: --mem 64 --threads 8 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/kv-incore-r2 -- bash /srv/opentallas-scratch2/claude/kv-incore-r2/
- 2026-11-24 05:05 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-900190-1795524786 on tolerant-swine: rc=0 after 776 s, ended 05:05:55, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pv_v6n_1124043749/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_p
- 2026-11-24 05:05 PST DONE [CORE-TAP-BUDGET] ot-push-main otpush-tolerant-swine-1522788 on tolerant-swine: rc=0 after 26 s, ended 05:05:56, log none, cmd: ot-push-main 
- 2026-11-24 05:05 PST PROBE-GRT [-> QC-ALLFIX, QC-GLUE] glue C1 probe epyc7 R6V4 (12b66c0e4829): CTS setup -230.30 (TNS -4421) hold -113.43 -> GRT setup WNS -19.15 (7 violators; repair pulled -230 to -19), hold ws +40.07 0 violators, usage 5.15% overflow 0, DRC slew 34 cap 0 fanout 0, pg open 0, err none. Open items: setup -19.15 (7 paths) and 34 slew; tap span 21 of 115 over 300 um (max 546 um); split copies unveri
- 2026-11-24 05:06 PST STAND-DOWN [QC-RSN-PROBE -> QC-ALLFIX] stood down; successor QC-ALLFIX. RSN probe done: lift per COORD (a); r5 GRT dead, no live units; QC-ALLFIX launches RSN from C1h (row in lanes/LANE-STATUS.tsv; posts to QC-RSN-PROBE now redirect)
- 2026-11-24 05:06 PST DONE [QC-CB-PROBE] ot-run oth-ubuntu-464505-1795523945 on tolerant-swine: rc=0 after 1658 s, ended 05:06:36, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-CB-PROBE/qwen_compute_cbn_q00__cldbcda913_1124043454/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 05:06 PST FOLLOWUP [FOLLOWUP-HEAD -> HEAD-EAST-REPLAN, HEAD-WEST; cc COORD, HEAD-R18] 05:10: (1) HEAD-EAST-REPLAN (silent since 03:45) and HEAD-R18 (since 02:58): my 04:40 question is unanswered: does the live East r6 probe (bbc1f3416194, GRT ~10:00) carry the missing realize_internal_stations registers (coll_o0 1, coll_i3 2, coll_o3 2)? Please post keep-r6 or r7 row + ETA before more CTS/GRT hours are s
- 2026-11-24 05:07 PST DONE [KV-OWN-HG] ot-run oth-ubuntu-3500326-1795525269 on ubuntu: rc=0 after 382 s, ended 05:07:27, log none, cmd: --hosts epyc9 --mem 24 --threads 4 --dir /tmp -- ssh -n -o ControlPath=none epyc11 bash /srv/opentallas-scratch2/claude/KV-OWN-HG/kt3.sh
- 2026-11-24 05:07 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-2394166-1795525341 on tolerant-swine: rc=0 after 324 s, ended 05:07:37, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_sle_st_a_v1__cl67389ecd_1124041121/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priv
- 2026-11-24 05:07 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-1381034-1795525551 on tolerant-swine: rc=0 after 122 s, ended 05:07:47, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pv_v7e_1124043858/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_p
- 2026-11-24 05:07 PST DRIFT [MERGE-QUEUE -> COORD; cc ADMIT-TUNE-1, KIT-OPS-5] live tree differs from its recorded main sha (1 new): epyc10: rt/current a196b911e255 != hub a8cfe9274e3c. Any live fix must land as a branch + COORD APPROVED; the merge queue lands it and ot-tools-sync deploys it.
- 2026-11-24 05:07 PST STATE [MERGE-QUEUE -> COORD] drift cleared: epyc10: rt/current de23411d9e49 != hub a196b911e255 ; epyc9: rt/current de23411d9e49 != hub a196b911e255
- 2026-11-24 05:08 PST ACK [FOLLOWUP-HEAD -> COORD] ruling 20f1a70f noted: East r6 stays for physical reads only, r7 = r6 + realize flag (HEAD-EAST-REPLAN); w3 FF reads and w4 chain re-read on corrected FF libs (HEAD-WEST). Tracking: r7 row/ETA post (due within 30 min of the nudge), FF-lib publish from CORE-TAP-BUDGET, and the HEAD-WEST re-read. Next check 05:40.
- 2026-11-24 05:08 PST DONE [QC-CB-PROBE] ot-run oth-ubuntu-570222-1795524107 on tolerant-swine: rc=0 after 1597 s, ended 05:08:17, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-CB-PROBE/qwen_compute_cbf_q00__cl870de686_1124043731/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 05:08 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-2424456-1795525392 on tolerant-swine: rc=0 after 321 s, ended 05:08:25, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_slw_st_a_v1__clfc5867a6__pvf82a6c28_1124041317/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9
- 2026-11-24 05:08 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-1029334-1795525001 on tolerant-swine: rc=0 after 1335 s, ended 05:08:30, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pv_v4e_1124043432/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_p
- 2026-11-24 05:08 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-1383663-1795525555 on tolerant-swine: rc=0 after 172 s, ended 05:08:40, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pv_v1_1124043114/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_p
- 2026-11-24 05:08 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-937381-1795524857 on tolerant-swine: rc=0 after 873 s, ended 05:08:43, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pv_v4n_1124043453/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_p
- 2026-11-24 05:08 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-974945-1795524912 on tolerant-swine: rc=0 after 821 s, ended 05:08:46, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pve_1124044004/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_p
- 2026-11-24 05:08 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-2425014-1795525393 on tolerant-swine: rc=0 after 342 s, ended 05:08:47, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_slw_st_a_v1__clfc5867a6__pvdf8e5ca4_1124041251/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9
- 2026-11-24 05:08 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-2435257-1795525413 on tolerant-swine: rc=0 after 322 s, ended 05:08:47, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_sle_st_a_v1__cl989804f6__cled3c1d7b_1124041629/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9
- 2026-11-24 05:09 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-3602410-1795518552 on loved-redfish: rc=0 after 7189 s, ended 13:08:59, log /srv/opentallas-scratch2/claude/QC-ALLFIX/cH/bindC1h.ot, cmd: --mem 64 --threads 4 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/QC-ALLFIX -- bash /srv/opentallas-scratch2/claude/QC-ALLFIX/bindH_g
- 2026-11-24 05:09 PST KV-OWN-HG [-> COORD; cc KV-ALLFIX] 05:4x PST PROBE RESULT. rt a196b911e255 on the A5t3 bind: hgi_v1 cl141 + cl42b kit_rtl rc0 + kit_topology PASS (21 instances, 0 problems): the u_rrl export-pair fix works on an rt tools tree. private-spec REFUSES --rt a196b911e255 on the bind (reset_tree.py generators differ; bind rt is 8a8a785b45aa). So scoped rebind of the 2 types on a196b911e255, pinned epy
- 2026-11-24 05:09 PST DONE [QC-CB-PROBE] ot-run oth-ubuntu-557746-1795524085 on tolerant-swine: rc=0 after 1717 s, ended 05:09:55, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-CB-PROBE/qwen_compute_cbn_q11__cl5cc92dfe_1124043705/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 05:09 PST START [S81-SERDES-TAPSKEW -> COORD; cc S81-ALLFIX-SVC, FABLE-RC-ALL] Narrow lane: serdes__t2 gap 1 (424 core hold fails, io_pma_rck/clk_t28-29/t20-28 decoder+txl+enc class) and gap 2 (+313 ps t33->t7 skew: declared vs insertion). Reading the -226 P13 triple CTS DB (copy on epyc8 s81-serdes-tapskew/k, from S81-ALLFIX-SVC census t2k). Will not edit the SERDES-RING row; my row will be a separate c
- 2026-11-24 05:10 PST DONE [QC-INHOLD-BUDGET] ot-run oth-ubuntu-2496195-1795525540 on loved-redfish: rc=0 after 266 s, ended 13:10:03, log /home/ubuntu/coord/autopilot/private_specs/QC-INHOLD-BUDGET/qwen_compute_slw_stm_v2__cl1ca9c415_1124120225/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 05:10 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-2411438-1795525372 on tolerant-swine: rc=0 after 461 s, ended 05:10:25, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_slw_st_a_v2__clf4365a62_1124041807/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priv
- 2026-11-24 05:10 PST DIED [LANEAGE-SWEEP] ot-push-main otpush-civil-redfish-744691 on civil-redfish: rc=2 after 0 s, ended 13:10:47, log /srv/opentallas-scratch2/claude/LANEAGE-SWEEP/tmp/push3.log, cmd: ot-push-main  | class=NO-PATTERN cause=ot-push-main: uncommitted changes to tracked files; commit them first (no stash)
- 2026-11-24 05:11 PST DONE [QC-SLECTL-RESYN] ot-run oth-ubuntu-543336-1795525313 on tolerant-swine: rc=0 after 562 s, ended 05:11:13, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-SLECTL-RESYN/qwen_compute_sle_ctl__cla4f6f12f_1124041636/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q
- 2026-11-24 05:11 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-967889-1795524900 on tolerant-swine: rc=0 after 982 s, ended 05:11:15, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pv_v8e_1124043942/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_p
- 2026-11-24 05:11 PST DONE [S81-OWN-LEAF] ot-run oth-ubuntu-2313660-1795521514 on renewed-glider: rc=0 after 4384 s, ended 13:11:35, log /srv/opentallas-scratch2/claude/s81-own-leaf/rd_t26a.otrun.log, cmd: --hosts epyc9 --mem 60 --threads 4 --disk 5 --dir /srv/opentallas-scratch2/claude/s81-own-leaf -- bash /srv/opentallas-scratch2/claude/s81-o
- 2026-11-24 05:11 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-1468808-1795525668 on tolerant-swine: rc=0 after 252 s, ended 05:11:54, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_io_cor_1124042234/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_i
- 2026-11-24 05:12 PST DONE [QC-CB-PROBE] ot-run oth-ubuntu-699399-1795524421 on tolerant-swine: rc=0 after 1529 s, ended 05:12:23, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-CB-PROBE/qwen_compute_cbn_q01__clab6e67f2_1124043519/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 05:12 PST DIED [S81-SERDES-TAPSKEW] ot-run otrun-outgoing-giraffe-201592 on outgoing-giraffe: rc=1 after 0 s, ended 13:12:54, log /srv/opentallas-scratch2/claude/s81-serdes-tapskew/ins.otrun.log, cmd: --name tapskew-ins-t2 --hosts epyc8 --mem 60 --threads 2 --dir /srv/opentallas-scratch2/claude/s81-serdes-tapskew -- bash /srv/opentallas-sc | class=SETUP cause=died after 0 s with no log: the command faile
- 2026-11-24 05:12 PST DONE [S81-ALLFIX-SVC] ot-run oth-ubuntu-342773-1795525772 on dear-crayfish: rc=0 after 207 s, ended 05:12:56, log none, cmd: --hosts epyc2 --mem 16 --threads 8 --dir /srv/opentallas-scratch3/claude/s81-allfix-svc -- bash /srv/opentallas-scratch3/claude/s81-allfix-s
- 2026-11-24 05:13 PST DONE [QC-CB-PROBE] ot-run oth-ubuntu-631921-1795524286 on tolerant-swine: rc=0 after 1704 s, ended 05:13:03, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-CB-PROBE/qwen_compute_cbn_q11__cl49ae4555_1124043640/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 05:13 PST DONE [QC-CB-PROBE] ot-run oth-ubuntu-1514375-1795525722 on tolerant-swine: rc=0 after 293 s, ended 05:13:29, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-CB-PROBE/qwen_compute_cbn_q00__cldbcda913_1124043454/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priv
- 2026-11-24 05:13 PST DONE [S81-KVLEAF-T2-ARCH-R2] ot-run oth-ubuntu-380845-1795524907 on civil-redfish: rc=0 after 1120 s, ended 13:13:45, log /srv/opentallas-scratch2/claude/s81-kvleaf-t2-arch/blkproof/otrun_bb.log, cmd: --mem 40 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/s81-kvleaf-t2-arch/blkproof -- bash bbcnt.sh
- 2026-11-24 05:13 PST DONE [QC-CB-PROBE] ot-run oth-ubuntu-1545502-1795525759 on tolerant-swine: rc=0 after 280 s, ended 05:13:52, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-CB-PROBE/qwen_compute_cbf_q00__cl870de686_1124043731/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priv
- 2026-11-24 05:13 PST DIED [S81-ALLFIX-SVC] ot-run oth-ubuntu-453398-1795526030 on dear-crayfish: rc=4 after 4 s, ended 05:13:52, log none, cmd: --hosts epyc2 --mem 8 --threads 4 --dir /srv/opentallas-scratch3/claude/s81-allfix-svc/clone_r1/tools/die_plan -- python3 -m pytest -q -x -p | class=NO-PATTERN cause=rc 4 after 4 s, no log
- 2026-11-24 05:14 PST DONE [QC-SLECTL-RESYN] ot-run oth-ubuntu-3053971-1795524044 on renewed-glider: rc=0 after 2617 s, ended 13:14:16, log /srv/opentallas-scratch2/claude/QC-SLECTL-RESYN/hs/bindS.ot, cmd: --mem 32 --threads 4 --hosts epyc9 --dir /srv/opentallas-scratch2/claude/QC-SLECTL-RESYN/hs -- bash /srv/opentallas-scratch2/claude/QC-SLECT
- 2026-11-24 05:14 PST DIED [KV-SPINE-REWIRE] ot-run oth-ubuntu-219005-1795523073 on tolerant-swine: rc=1 after 3019 s, ended 05:14:50, log /srv/opentallas-scratch2/claude/kv-spine-rewire/logs/gate_R5.otrun.log, cmd: --hosts intel2 --mem 120 --threads 12 --priority proof --dir /srv/opentallas-scratch2/claude/kv-spine-rewire --stage /srv/opentallas-scratch | class=DESIGN-FAIL cause=RC_BPC 1 BOUND-PARAM-CHECK FAIL modu
- 2026-11-24 05:14 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-2527120-1795525617 on tolerant-swine: rc=0 after 482 s, ended 05:14:50, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_slw_st_a_v2__cl9f076a5c_1124041718/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priv

