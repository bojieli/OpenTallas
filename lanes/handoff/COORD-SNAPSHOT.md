# COORD snapshot 2026-11-24 06:15 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: 4d87f4ac76c2
- 2026-11-23 15:15 PST MERGED [MERGE-QUEUE -> LAUNCH-GUARD] claude/launch-guard-viewpack-stage-1123@349ec165e6e -> main 005831fc27c -> ed4f6ade31b, no-ff merge, tags flow-20261117-mv-*. Gate: gate record from renewed-glider 2026-11-23 23:13 UTC on main becebaf53d9 (main since: no overlap): 8 test file(s) pass (+1 source dir(s) the tests name: physical/die_plan/hbm_arch_cores) (1 failure(s) also fail on main: baseline
- 2026-11-23 15:25 PST MERGED [MERGE-QUEUE -> LAUNCH-GUARD] claude/launch-guard-ghost-signed-1123@7a15228190e -> main ed4f6ade31b -> d0beea9d604, no-ff merge, tags flow-20261117-mw-*. Gate: gate record from renewed-glider 2026-11-23 23:24 UTC on main ed4f6ade31b: 184 test file(s) pass (+6 source dir(s) the tests name: physical/die_plan physical/die_plan/hbm/cores/harden physical/die_plan/hbm/cores/ports physical/die_
- 2026-11-23 15:25 PST MERGED [MERGE-QUEUE -> KV-D29-EMITGAPS] claude/kv-d29-emitgaps-1123@a4b13024a9a -> main d0beea9d604 -> bd54869e80c, no-ff merge, tags flow-20261117-mx-*. Gate: gate record from renewed-glider 2026-11-23 23:21 UTC on main ed4f6ade31b: 76 test file(s) pass (+18 source dir(s) the tests name: physical/asap7_memory_macros physical/asap7_memory_macros_pa physical/asap7_memory_macros_v2 physical/die_p

## READY/ASK with no later COORD post naming them (1, heuristic: check each)
- 2026-11-24 03:58 PST ASK [FAM-S81-SVC-OWN -> S81-ALLFIX-INT; cc COORD] Per COORD: how will the c8 kit wave launch the svc types so they COUNT (seal OK)? (a) kit_wave rows on a sealed c8 tree, or (b) ot-tree-fork of it? Please give the tree path and bind dir, and say whether your c8 wave already includes my 7: svc_lo rs t3, svc_hi pvso_entry t1/t2, svc_lo rs_w t1, svc_hi rs t4/t5/t6 (also rs t1,t2,t3, lo t1,t2,t4,t5

## Lane handoff files (age) and last queue post
- CODEX-TOKEN-1123: handoff 775 min old; last post none in recent queue
- CORE-TAP-BUDGET: handoff 149 min old; last post 2026-11-24 05:57 DONE
- DLYRAM-RESET: handoff 167 min old; last post 2026-11-24 01:43 DONE
- EPYC11-ONBOARD-FINISH: handoff 350 min old; last post 2026-11-24 00:01 DONE
- EVENT-ENV-PREFLIGHT: handoff 49 min old; last post 2026-11-24 05:18 DIED
- FABLE-OPEN-HEAD-QC: handoff 1160 min old; last post 2026-11-23 10:54 REPORT-2
- FABLE-OPEN-KV: handoff 737 min old; last post 2026-11-23 18:32 DONE
- FABLE-OPEN-S81-A-rc37: handoff 864 min old; last post none in recent queue
- FABLE-OPEN-S81-A-x14: handoff 852 min old; last post none in recent queue
- FABLE-OPEN-S81-A: handoff 850 min old; last post 2026-11-23 16:03 DONE
- FABLE-OPEN-S81-B-rc72: handoff 1423 min old; last post none in recent queue
- FABLE-OPEN-S81-B-x9: handoff 1128 min old; last post none in recent queue
- FABLE-OPEN-S81-B: handoff 864 min old; last post 2026-11-23 11:21 DONE
- FABLE-OPEN-S81-SVC: handoff 866 min old; last post 2026-11-23 14:54 DONE
- FABLE-RC-ALL-KV-QC-HANDOVER: handoff 651 min old; last post none in recent queue
- FABLE-RC-ALL: handoff 37 min old; last post 2026-11-23 17:05 DIED
- FABLE-RC-KV: handoff 52 min old; last post none in recent queue
- FABLE-RC-QC-SU: handoff 554 min old; last post none in recent queue
- FABLE-RC-QC: handoff 34 min old; last post 2026-11-23 01:26 DONE
- FABLE-UNC-HEAD: handoff 1164 min old; last post 2026-11-23 04:00 GATE-PASS
- FABLE-UNC-S81-LEAF: handoff 1435 min old; last post 2026-11-23 06:19 STATUS
- FAM-KV-HUBC-SYSC-R2: handoff 1162 min old; last post 2026-11-23 18:15 DIED
- FAM-KV-HUBWO-S1: handoff 491 min old; last post 2026-11-23 22:03 DONE
- FAM-S81-DSDV-R1: handoff 864 min old; last post 2026-11-23 10:02 DIED
- FIX-LEDGER: handoff 841 min old; last post 2026-11-23 02:45 ASK
- FIX-S81-SVC-WESTRIP: handoff 856 min old; last post 2026-11-23 15:58 CORRECTION
- FIX-S81-XG-STN: handoff 1419 min old; last post 2026-11-23 12:31 DONE
- FLOW-CLKGRT-R2: handoff 840 min old; last post 2026-11-23 16:13 RESULT
- FLOW-OPS-R3-CODEX-1123: handoff 775 min old; last post none in recent queue
- FLOW-OPS-R3: handoff 74 min old; last post 2026-11-24 05:46 DONE
- GENDRY-KITRTL: handoff 562 min old; last post 2026-11-23 21:38 DONE
- HEAD-100-unit-table-signedview: handoff 10 min old; last post none in recent queue
- HEAD-100-unit-table: handoff 3 min old; last post none in recent queue
- HEAD-EAST-REPLAN: handoff 150 min old; last post 2026-11-24 05:35 DONE
- HEAD-R18: handoff 40 min old; last post 2026-11-24 02:58 DONE
- HEAD-S2-RESEAL: handoff 538 min old; last post 2026-11-23 21:15 DONE
- HEAD-WEST: handoff 360 min old; last post 2026-11-24 06:14 DONE
- KV-ALLFIX: handoff 742 min old; last post 2026-11-24 06:14 DONE
- KV-ASTK-EARLYTAP: handoff 455 min old; last post 2026-11-23 22:39 DONE
- KV-D29-PACKAGE: handoff 857 min old; last post none in recent queue
- KV-D29: handoff 519 min old; last post 2026-11-23 21:39 NOTE
- KV-DIE-SEAMHOLD: handoff 432 min old; last post 2026-11-23 23:01 DONE
- KV-HG-CAP: handoff 28 min old; last post 2026-11-24 05:26 DONE
- KV-HR-DEEPCLK: handoff 182 min old; last post 2026-11-24 04:14 DONE
- KV-HUB-EPZO: handoff 526 min old; last post 2026-11-23 21:29 STAND-DOWN
- KV-HUB-HOLD: handoff 467 min old; last post 2026-11-23 22:55 DONE
- KV-INCORE-R2: handoff 63 min old; last post 2026-11-24 05:05 DONE
- KV-OPEN-FWDCLK: handoff 593 min old; last post 2026-11-23 20:20 DIED
- KV-OPEN-INCORE: handoff 627 min old; last post 2026-11-23 20:20 DONE
- KV-PREGRT-STALL: handoff 548 min old; last post 2026-11-23 21:06 STAND-DOWN
- KV-PV-CAP: handoff 285 min old; last post 2026-11-24 01:28 DONE
- KV-PV-EDGESTRIP: handoff 120 min old; last post 2026-11-24 04:13 DONE
- KV-PV-RSTRELAY: handoff 434 min old; last post 2026-11-23 22:58 DONE
- KV-R8-LANELOSS: handoff 583 min old; last post 2026-11-23 20:32 STAND-DOWN
- KV-RCOLL-PHASE: handoff 504 min old; last post none in recent queue
- KV-RCOLL-REBASE: handoff 484 min old; last post 2026-11-23 22:08 DONE
- KV-RINGMAC-R1: handoff 865 min old; last post 2026-11-23 14:46 DIED
- KV-RSTNAME-REMAP: handoff 504 min old; last post 2026-11-23 21:48 DONE
- KV-RSTREACH: handoff 84 min old; last post 2026-11-24 05:50 DONE
- KV-SENDER-SKEW: handoff 83 min old; last post 2026-11-24 01:08 DONE
- KV-SPINE-REWIRE: handoff 130 min old; last post 2026-11-24 06:06 DONE
- KV-TAPSPLIT-HGPV: handoff 165 min old; last post 2026-11-24 03:29 DONE
- KVLEAF-MASTERS-from-ARCH-R2: handoff 651 min old; last post none in recent queue
- KVLEAF-MASTERS: handoff 449 min old; last post 2026-11-23 22:45 DONE
- LANDING-WRAP-TOOL: handoff 472 min old; last post 2026-11-23 22:22 LIVE
- LANDREMAP-RSTNODE: handoff 500 min old; last post 2026-11-23 21:56 STAND-DOWN
- LANEAGE-SWEEP: handoff 79 min old; last post 2026-11-24 05:28 DIED
- LAUNCH-GUARD: handoff 774 min old; last post 2026-11-23 15:49 DONE
- LEC-AUTOFILL: handoff 442 min old; last post 2026-11-24 03:30 DIED
- LEC-VACUITY-SWEEP: handoff 402 min old; last post 2026-11-23 23:31 DIED
- OPS-SUPPORT-R1: handoff 865 min old; last post 2026-11-23 20:03 EPYC8-FREED
- OPUS-FIX-KV-PV-R7: handoff 874 min old; last post 2026-11-23 20:58 DIED
- OPUS-FIX-QC-V4-R2: handoff 692 min old; last post 2026-11-24 01:24 DIED
- PRE-QC-GENCHECK: handoff 205 min old; last post 2026-11-24 02:50 STAND-DOWN
- PRECHECK-CELLCAP: handoff 419 min old; last post 2026-11-23 23:14 RT
- PRECHECK-DERIVED-DROP: handoff 460 min old; last post 2026-11-23 22:36 DONE
- PRECHECK-LEDGER-R3: handoff 135 min old; last post 2026-11-24 05:47 DONE
- QC-ALLFIX-COLL: handoff 154 min old; last post 2026-11-23 18:47 DONE
- QC-ALLFIX-SU: handoff 733 min old; last post 2026-11-24 01:12 HANDOFF
- QC-ALLFIX: handoff 708 min old; last post 2026-11-24 06:14 DONE
- QC-F16-PRODUCER: handoff 45 min old; last post 2026-11-24 03:24 DONE
- QC-FW-CAP: handoff 188 min old; last post 2026-11-24 03:13 ACK
- QC-GLUE-PADBIND: handoff 171 min old; last post 2026-11-24 03:32 STAND-DOWN
- QC-HC1-CLKENTRY: handoff 140 min old; last post 2026-11-24 03:54 STAND-DOWN
- QC-INHOLD-BUDGET: handoff 127 min old; last post 2026-11-24 05:10 DONE
- QC-OPEN-COLL: handoff 48 min old; last post 2026-11-24 06:06 DONE
- QC-OPEN-STA: handoff 108 min old; last post 2026-11-24 05:14 DONE
- QC-OPEN-SU: handoff 117 min old; last post 2026-11-24 05:55 DONE
- QC-RSTCNT: handoff 159 min old; last post 2026-11-24 06:11 DIED
- QC-SLECTL-RESYN: handoff 56 min old; last post 2026-11-24 05:14 DONE
- QC-STB-CAP: handoff 417 min old; last post 2026-11-23 23:15 DONE
- QC-SUL1-STN-ROW: handoff 502 min old; last post 2026-11-23 21:51 DONE
- QC-TTC-R2: handoff 155 min old; last post 2026-11-24 04:12 DONE
- QC-TTC-RETIME: handoff 612 min old; last post 2026-11-23 20:45 DONE
- QC-V4-CB: handoff 1119 min old; last post 2026-11-23 14:06 DONE
- QC-V4-COLL: handoff 1426 min old; last post 2026-11-23 07:49 DONE
- QC-V4: handoff 452 min old; last post 2026-11-23 23:33 ADOPT-BIND
- RELEC-1122: handoff 332 min old; last post 2026-11-24 03:11 DONE
- S81-ALLFIX-COL: handoff 139 min old; last post 2026-11-24 02:57 DONE
- S81-ALLFIX-INT: handoff 760 min old; last post 2026-11-24 04:15 ANSWERS
- S81-ALLFIX-MULTI: handoff 696 min old; last post 2026-11-23 18:38 NOTE
- S81-ALLFIX-SLICE: handoff 666 min old; last post 2026-11-23 19:56 DONE
- S81-ALLFIX-SVC-ENGMON: handoff 683 min old; last post none in recent queue
- S81-ALLFIX-SVC-L0: handoff 722 min old; last post none in recent queue
- S81-ALLFIX-SVC-MISC: handoff 751 min old; last post none in recent queue
- S81-ALLFIX-SVC-SERDESRING: handoff 30 min old; last post none in recent queue
- S81-ALLFIX-SVC: handoff 593 min old; last post 2026-11-24 05:43 DIED
- S81-C8-TYPES: handoff 127 min old; last post none in recent queue
- S81-COL-J9: handoff 859 min old; last post 2026-11-23 15:53 DONE
- S81-J9-ASSEMBLY-R6: handoff 36 min old; last post 2026-11-24 05:26 DIED
- S81-KV-CALENDAR: handoff 27 min old; last post 2026-11-24 02:38 DONE
- S81-KVLEAF-T2-ARCH-R2: handoff 397 min old; last post 2026-11-24 06:01 DIED
- S81-LEAF-J9: handoff 770 min old; last post 2026-11-23 17:22 DONE
- S81-LEPFLF-HOLD: handoff 273 min old; last post 2026-11-24 01:02 DONE
- S81-MISC-SERDES-J9: handoff 769 min old; last post 2026-11-23 17:05 DONE
- S81-OPEN-CLOCK: handoff 459 min old; last post 2026-11-23 21:58 DONE
- S81-OPEN-DEMAND: handoff 459 min old; last post 2026-11-23 20:59 DONE
- S81-OPEN-ENGCHAN: handoff 659 min old; last post none in recent queue
- S81-OPEN-FSTART: handoff 376 min old; last post 2026-11-23 22:17 DIED
- S81-OPEN-LEAFBAND: handoff 382 min old; last post 2026-11-23 23:42 DONE
- S81-OPEN-SVCLO: handoff 512 min old; last post 2026-11-23 21:41 DIED
- S81-OWN-KVLEAF-LEP: handoff 340 min old; last post 2026-11-24 00:14 ASK
- S81-PROBE-LAUNCH: handoff 376 min old; last post 2026-11-24 03:20 DONE
- S81-ROM-TEMPLATE: handoff 192 min old; last post 2026-11-24 05:37 DIED
- S81-SLICE-J9: handoff 421 min old; last post 2026-11-24 01:45 DONE
- S81-SVC-J9: handoff 827 min old; last post 2026-11-23 16:01 DONE
- S81-T2-REFLOOR: handoff 297 min old; last post 2026-11-24 06:08 DIED
- S81-TYPES-CODEX-1123: handoff 775 min old; last post none in recent queue
- SEAT-MATCH-AUDIT: handoff 275 min old; last post 2026-11-24 04:14 DONE
- TAP-GRID-R6: handoff 829 min old; last post 2026-11-23 16:24 DONE
- TL-QCPHYSDB: handoff 1357 min old; last post none in recent queue
- VIS-DIE-S81: handoff 1426 min old; last post 2026-11-23 07:06 DONE

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 182; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 75 live
- QC-ALLFIX agent ? last post 2026-11-24 06:14 DONE
- KV-ALLFIX agent ? last post 2026-11-24 06:14 DONE
- HEAD-WEST agent ? last post 2026-11-24 06:14 DONE
- QC-RSTCNT agent ? last post 2026-11-24 06:11 DIED
- S81-T2-REFLOOR agent ? last post 2026-11-24 06:08 DIED
- MERGE-QUEUE agent ? last post 2026-11-24 06:07 STATE
- QC-OPEN-COLL agent ? last post 2026-11-24 06:06 DONE
- KV-SPINE-REWIRE agent ? last post 2026-11-24 06:06 DONE
- S81-KVLEAF-T2-ARCH-R2 agent ? last post 2026-11-24 06:01 DIED
- NOPROG-WATCHDOG agent ? last post 2026-11-24 06:00 STATE
- CORE-TAP-BUDGET agent ? last post 2026-11-24 05:57 DONE
- BIND-ALL-ERRORS agent ? last post 2026-11-24 05:56 DONE
- QC-OPEN-SU agent ? last post 2026-11-24 05:55 DONE
- S81-VPW-CONE agent ? last post 2026-11-24 05:55 DIED
- QC-FWDCLK-REPOINT agent ? last post 2026-11-24 05:55 DONE
- s81-serdes-tapskew agent ? last post 2026-11-24 05:53 DONE
- NOPROG-FIX-1115 agent ? last post 2026-11-24 05:52 STATE
- KV-RSTREACH agent ? last post 2026-11-24 05:50 DONE
- KV-PC-TAP agent ? last post 2026-11-24 05:50 DONE
- ROM-WEIGHTS-1119 agent ? last post 2026-11-24 05:48 DONE
- PRECHECK-LEDGER-R3 agent ? last post 2026-11-24 05:47 DONE
- TAPKEY-SITE agent ? last post 2026-11-24 05:47 DONE
- FLOW-OPS-R3 agent ? last post 2026-11-24 05:46 DONE
- FLEET-WATCH-1015 agent ? last post 2026-11-24 05:45 NOTICE
- S81-ALLFIX-SVC agent ? last post 2026-11-24 05:43 DIED
- romw-1119-s81 agent ? last post 2026-11-24 05:42 DONE
- FOLLOWUP-HEAD agent ? last post 2026-11-24 05:36 SUMMARY
- HEAD-EAST-REPLAN agent ? last post 2026-11-24 05:35 DONE
- head-r18 agent ? last post 2026-11-24 05:33 DONE
- FLEET-OPS-R agent ? last post 2026-11-24 05:30 ALERT
- LANEAGE-SWEEP agent ? last post 2026-11-24 05:28 DIED
- S81-J9-ASSEMBLY-R6 agent ? last post 2026-11-24 05:26 DIED
- KV-HG-CAP agent ? last post 2026-11-24 05:26 DONE
- S81-SERDES-TAPSKEW agent ? last post 2026-11-24 05:26 DIED
- QC-CB-PROBE agent ? last post 2026-11-24 05:24 DONE
- FOLLOWUP-S81 agent ? last post 2026-11-24 05:23 FOLLOWUP-S81
- event-env-preflight agent ? last post 2026-11-24 05:22 DONE
- s81-allfix-svc agent ? last post 2026-11-24 05:19 DONE
- EVENT-ENV-PREFLIGHT agent ? last post 2026-11-24 05:18 DIED
- CBC-RULES-1119 agent ? last post 2026-11-24 05:17 HOURLY
- romw-1119 agent ? last post 2026-11-24 05:16 DONE
- lanes agent ? last post 2026-11-24 05:16 DONE
- QC-SLECTL-RESYN agent ? last post 2026-11-24 05:14 DONE
- QC-OPEN-STA agent ? last post 2026-11-24 05:14 DONE
- S81-OWN-LEAF agent ? last post 2026-11-24 05:11 DONE
- QC-INHOLD-BUDGET agent ? last post 2026-11-24 05:10 DONE
- KV-OWN-HG agent ? last post 2026-11-24 05:07 DONE
- KV-INCORE-R2 agent ? last post 2026-11-24 05:05 DONE
- AUTOPILOT agent ? last post 2026-11-24 04:59 NEEDS-ACTION
- s81-t2-refloor agent ? last post 2026-11-24 04:50 DONE
- qwen_compute agent ? last post 2026-11-24 04:44 KIT-WAVE
- s81_head agent ? last post 2026-11-24 04:44 KIT-WAVE
- s81 agent ? last post 2026-11-24 04:44 KIT-WAVE
- S81-START-COLLECTOR agent ? last post 2026-11-24 04:32 DIED
- AUTO-CLEAN agent ? last post 2026-11-24 04:23 INFO
- S81-RSTSOLVE agent ? last post 2026-11-24 04:20 DONE
- QC-CBX-CLOCK agent ? last post 2026-11-24 04:17 DIED
- S81-ALLFIX-INT agent ? last post 2026-11-24 04:15 ANSWERS
- SEAT-MATCH-AUDIT agent ? last post 2026-11-24 04:14 DONE
- KV-PV-EDGESTRIP agent ? last post 2026-11-24 04:13 DONE
- KIT-WAVE agent ? last post 2026-11-24 04:13 NEEDS-LANE
- QC-TTC-R2 agent ? last post 2026-11-24 04:12 DONE
- qc-cbx-clock-lane agent ? last post 2026-11-24 04:09 DONE
- FAM-S81-SVC-OWN agent ? last post 2026-11-24 03:58 ASK
- FOLLOWUP-QC agent ? last post 2026-11-24 03:44 CLOSED
- bind-elab-par agent ? last post 2026-11-24 03:41 DONE
- BIND-ELAB-PAR agent ? last post 2026-11-24 03:38 DONE
- QC-GENDRY-TRIAGE agent ? last post 2026-11-24 03:37 DONE
- LEC-AUTOFILL agent ? last post 2026-11-24 03:30 DIED
- KV-TAPSPLIT-HGPV agent ? last post 2026-11-24 03:29 DONE
- KW-REPICK-PIN agent ? last post 2026-11-24 03:29 DONE
- QC-F16-PRODUCER agent ? last post 2026-11-24 03:24 DONE
- s81-start-collector agent ? last post 2026-11-24 03:21 DONE
- S81-PROBE-LAUNCH agent ? last post 2026-11-24 03:20 DONE
- S81-SLICE-C-OWN agent ? last post 2026-11-24 03:20 DONE

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-24 06:15 PST)
count_hourly: signed any plan 589 | current plan 485 | deferred re-sign 21 (hbm 1, head 10, qc 7, s81 3) | retired-plan 83 (head 1, kv 13, qc 41, s81 28)
- [ ] FAIL.S81.CORES 72/72 signed · open: none
- [ ] FAIL.S81.TYPES 48/394 signed · kit rows: held by die owner (plan event pending) 296 (bk_sel__t2, +295) · cancelled (superseded) 48 (col_h10_r0_p1__t1__cl911743eb, +47)
- [ ] FAIL.HEAD.CORES 5/5 signed · open: none
- [ ] FAIL.HEAD.TYPES 25/27 signed · kit rows: held by die owner (plan event pending) 1 (hd_lep0N) · running (lint advisory) 1 (hd_lep0N_w)
- [ ] FAIL.QC.CORES 69/69 signed · open: none
- [ ] FAIL.QC.TYPES 80/127 signed · kit rows: held by die owner (plan event pending) 36 (cbf_q00__cl1b5a6458, +35) · running 3 · cancelled (superseded) 1 (glue)
- [ ] FAIL.KV.CORES 83/83 signed · open: none
- [ ] FAIL.KV.TYPES 9/71 signed · kit rows: held by die owner (plan event pending) 55 (kv3_hg, +54) · running (lint advisory) 5 (kv3_hub_C, +4)
- [ ] FAIL.HBM.CORES 90/119 signed · open: no kit-wave row 19 (accel_smh_pt_w, hfd_coll_q3_body_ctl, hgi_sfu_opsa_group0, +12) · running, no result 9 (hfd_coll_q2n2_vm_core, hfd_hgi_vms_glue_nw_t, hgi_coll_tkm_m_tp192__root, +6) · shape: over cells/util/congestion 1 (hgi_dma_back_static_vp4_banks_cp
- [ ] FAIL.HBM.TYPES 4/81 signed · kit rows: none
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 0 current-event (+1 on a superseded plan block, not counted) (live check: ps/systemd/docker on all hosts; wave state: hub; full list lanes/STALE.tsv)
- [ ] STALE.S81 1 (cores 0, types 1) · by owner: FAIL-S81-1 1
  - type iqf__t1 · CANCELLED  STRUCT-STOP @ 2026-11-22 08:57 (45.3h) · owner FAIL-S81-1
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 340 commits / missing r708
- TOOLS-LAG qwen_kvsys 100 commits / missing none
- TOOLS-LAG s81 0 commits / missing none
- TOOLS-LAG s81_head 283 commits / missing r708
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 3129 taps in 28 types, 111 over 1650 sinks; insertion max 696 ps (p50 268, p90 286), skew max 107 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 265 taps in 3 types, 10 over 1650 sinks; insertion max 512 ps (p50 272, p90 307), skew max 94 ps; oversized taps: ins max 370 ps, skew max 64 ps
- TAP-INSERTION s81: 5402 taps in 83 types, 259 over 1650 sinks; insertion max 1000 ps (p50 468, p90 498), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 168 taps in 5 types, 6 over 1650 sinks; insertion max 501 ps (p50 463, p90 478), skew max 71 ps; oversized taps: ins max 499 ps, skew max 65 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-24 06:05 | tolera L16.57/112 units0 free127G | key-ca L41.53/112 units181 free136G | dear-c L65.54/128 units421 free104G | loved- L158.85/96 units63 free303G | outgoi L86.91/96 units186 free83G | renewe L45.83/96 units64 free207G | civil- L65.43/96 units54 free218G | viable L76.84/96 units35 free3871G | HOST-CAPS 1 flagged: epyc7:LOAD_CAP_FACTOR=1.2:EXPIRED; expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (273.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (273.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (273.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (273.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (273.9 h left); epyc10:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 ex
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  353G   92G  80% /
    06:15:20 up 31 days,  1:55, 174 users,  load average: 19.78, 18.94, 18.79

## ot-run status
    ot-run status: epyc2 admits 308 GB (avail 696, reserve 0, fresh 0, peak 94.7) load 92/128 run 29 threads 204/128 root 78% scratch 103 GB
    intel1 admits 333 GB (avail 795, reserve 0, fresh 0, peak 52.4) load 41/112 run 20 threads 228/112 root 32% scratch 139 GB
    localhost REFUSED (scratch disk /srv/opentallas-scratch2 has 133 GB free < floor 150 GB (the root fs is never a fallback; free the scratch disk, OT_RUN_SCRATCH_
    epyc7 admits 188 GB (avail 473, reserve 0, fresh 0, peak 27.6) load 131/96 waiters 65:522 GB oldest 0.2 h run 37 threads 415/96 LOADCAP root 51% scratch 305 GB
    epyc8 admits 405 GB (avail 727, reserve 0, fresh 0, peak 4.6) load 75/96 run 44 threads 458/96 root 46% scratch 79 GB DRAINING (79 of 90 GB, new job dirs refuse
    epyc9 admits 331 GB (avail 593, reserve 0, fresh 0, peak 24.9) load 68/96 run 25 threads 262/96 root 54% scratch 265 GB
    epyc10 admits 385 GB (avail 868, reserve 0, fresh 0, peak 74.1) load 51/96 run 25 threads 308/96 root 48% scratch 236 GB
    epyc11 admits 363 GB (avail 494, reserve 0, fresh 0, peak 109.1) load 83/96 waiters 57:2976 GB oldest 1.7 h run 32 threads 5727/96 root 5% scratch 3868 GB
    next 16-thread 32 GB job -> intel1
    ot-run status: BLOCKED 97 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hub_Eo_112404215
    ot-run status: BLOCKED 95 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pc_v1__cl23f6a14
    ot-run status: BLOCKED 90 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hgi_v2__cle00153
    ot-run status: BLOCKED 90 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hg_v1p6_11240419
    ot-run status: BLOCKED 89 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hgi_v5_112404205
    ot-run status: BLOCKED 88 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hg_v3_1124041927
    ot-run status: BLOCKED 86 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pc_v1__cl7f64894
    ot-run status: BLOCKED 83 min KV-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_io_ft_11
    ot-run status: BLOCKED 82 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pc_v1__cl7f64894
    ot-run status: BLOCKED 82 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pc_v1__cl7f64894
    ot-run status: BLOCKED 80 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pc_v1__cl7f64894
    ot-run status: BLOCKED 78 min KV-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_io_ft_v1
    ot-run status: BLOCKED 75 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pv_v4_1124043356
    ot-run status: BLOCKED 75 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pv_1124043038/ge
    ot-run status: BLOCKED 74 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hgi_v4_112404203
    ot-run status: BLOCKED 73 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pv_v4ne_11240435
    ot-run status: BLOCKED 72 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pv_v1e_112404314
    ot-run status: BLOCKED 70 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pv_v6e_112404370
    ot-run status: BLOCKED 70 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pv_v6ne_11240437
    ot-run status: BLOCKED 70 min - /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pv_v7_1124043819

## KIT-WAVE (autopilot log, last 6)
    2026-11-24 06:14:04 PST AUTOPILOT: KIT-WAVE FAMILIES s81: 7 famil(ies), 7 representative(s) (high priority), 5 sibling(s) (spare capacity), 0 held by a failed representative; picks this tick 12, sched
    2026-11-24 06:14:04 PST AUTOPILOT: KIT-WAVE PLAN-ROWS s81: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-24 06:14:04 PST AUTOPILOT: KIT-WAVE NO-LAUNCH s81: 12 eligible row(s), 0 scheduled this tick; skipped: 138x die-owned hold: j7-col-held-until-view-1122: S81 J7 COL held-until-view (COORD r; 75
    2026-11-24 06:14:04 PST AUTOPILOT: KIT-WAVE PLAN-ROWS s81_head: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-24 06:14:05 PST AUTOPILOT: KIT-WAVE HOLD-AUDIT HELD-BUT-LAUNCHED=0 HOLD-LEAK=0 TERM-UNREACHABLE=0 TERM-VARIANT=0 HOLD-SUPERSEDED=0 HOLD-ZERO-MATCH=0 PROOF-HELD=0 PILOT-DEADLOCK=0
    2026-11-24 06:14:30 PST AUTOPILOT: UNDER-USE HELD SKIP-HELD 5: s81/serdes__t3 1 [owner VIS-S81-MISC, 41.3 h, eta 11-23 12:00, FLAGGED OVERDUE]; s81/serdes__t16 1 [owner VIS-S81-MISC, 41.0 h, eta 11-23

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-24 05:45 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-975697-1795526949 on tolerant-swine: rc=0 after 962 s, ended 05:45:09, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_cbn_q11__cl49ae4555_1124052717/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 05:45 PST NOTICE [NOPROG-WATCHDOG -> QC-HC1-CLKENTRY, SEAT-MATCH-AUDIT] NO-PROGRESS on your own kit /srv/opentallas-scratch3/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-HC1-CLKENTRY/sle_ctl__cla4f6f12f_1124064108/gen/sle_ctl__cla4f6f12f (epyc2 oth-ubuntu-4119065-1795510602 pregrt_ff_hold, job 4.8 h): no new repair_TNS row in 2 h; repair_TNS best 0 last 0 r
- 2026-11-24 05:45 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-946728-1795526930 on tolerant-swine: rc=0 after 1012 s, ended 05:45:39, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_cbn_q01__cld9ff4c40_1124052642/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 05:45 PST NOTICE [FLEET-WATCH-1015 -> FAM-KV-HUBC-SYSC-R2] UNSIGNABLE watchdog (owner rule 11-20, >3 h and measured unable to sign): 1 job(s): epyc2 oth-ubuntu-303152-1795486508 kv3_hub_C (tt_setup_repair.log latest setup WNS -1970.01 ps (< -300, gate TT >= -42); job age 11.5 h > 3 h; 8 GB, listed since 05:45). Each is cancelled by ot-run --cancel <unit> 30 min after this post unless FAM-KV-HUBC-SYSC-R2 
- 2026-11-24 05:45 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2044219-1795527773 on tolerant-swine: rc=0 after 188 s, ended 05:45:58, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_b_v1__cl6357f1cc__pv6ace3e48_1124054223/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N4
- 2026-11-24 05:45 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 4 flagged of 138 containers {'UNSIGNABLE': 3, 'NO-PROGRESS': 1, 'YOUNG': 120, 'NO-DATA': 2, 'PROGRESS': 12}; full table lanes/NOPROG-TABLE.md; flagged: epyc2 cbn_q01 tt_setup_repair_grt [UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -743.27 ps (< -300,] UNSIGNABLE (hub: ot-run --ca; epyc2 kv3_hub_C tt_setup_repair [UNSIGNABLE: tt_setup_
- 2026-11-24 05:45 PST NOTICE [NOPROG-WATCHDOG -> QC-HC1-CLKENTRY] NO-PROGRESS on your own kit /srv/opentallas-scratch3/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-HC1-CLKENTRY/sle_ctl__cla4f6f12f_1124064108/gen/sle_ctl__cla4f6f12f (epyc2 oth-ubuntu-4119065-1795510602 pregrt_ff_hold, job 4.8 h): no new repair_TNS row in 2 h; repair_TNS best 0 last 0 rows 1 | before-win
- 2026-11-24 05:46 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2038526-1795527770 on tolerant-swine: rc=0 after 203 s, ended 05:46:10, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc2__cla3497502__cl16607c7a_1124053925/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4
- 2026-11-24 05:46 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2093068-1795527809 on tolerant-swine: rc=0 after 183 s, ended 05:46:30, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_b_v1__cle6023ec2_1124054300/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 05:46 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2081880-1795527801 on tolerant-swine: rc=0 after 192 s, ended 05:46:31, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_cbf_q01_1124052457/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 05:46 PST DONE [FLOW-OPS-R3] ot-push-main otpush-civil-redfish-1551167 on civil-redfish: rc=0 after 279 s, ended 13:46:34, log /srv/opentallas-scratch2/claude/FLOW-OPS-R3/tmp/rtd_push.out, cmd: ot-push-main 
- 2026-11-24 05:47 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2084094-1795527803 on tolerant-swine: rc=0 after 223 s, ended 05:47:03, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc3__clccfc3e6b__pv39aac7a1_1124054001/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4
- 2026-11-24 05:47 PST DONE [PRECHECK-LEDGER-R3] ot-push-main otpush-tolerant-swine-2913846 on tolerant-swine: rc=0 after 19 s, ended 05:47:10, log none, cmd: ot-push-main 
- 2026-11-24 05:47 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2153876-1795527846 on tolerant-swine: rc=0 after 186 s, ended 05:47:10, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_b_v2__pva66d0f22__pvb80e2003_1124054336/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N4
- 2026-11-24 05:47 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2129292-1795527831 on tolerant-swine: rc=0 after 201 s, ended 05:47:10, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_cbf_q11_1124052532/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 05:47 PST DONE [QC-FWDCLK-REPOINT] ot-run oth-ubuntu-1963992-1795527723 on outgoing-giraffe: rc=0 after 309 s, ended 13:47:10, log /srv/opentallas-scratch2/claude/QC-FWDCLK-REPOINT/whatif_dt2out/slw_stm_v2__cl9beb65e6.ot, cmd: --mem 40 --threads 4 --hosts epyc8 --dir /srv/opentallas-scratch2/claude/QC-FWDCLK-REPOINT -- /srv/opentallas-scratch2/claude/QC-FWDCLK-REPO
- 2026-11-24 05:47 PST DONE [TAPKEY-SITE] ot-run oth-ubuntu-485941-1795521341 on loved-redfish: rc=0 after 6700 s, ended 13:47:15, log /srv/opentallas-scratch2/claude/tapkey-site/ref_qc2.otrun.log, cmd: --mem 24 --threads 2 --priority die --hosts epyc7 --dir /srv/opentallas-scratch2/claude/tapkey-site -- bash /srv/opentallas-scratch2/claude/
- 2026-11-24 05:47 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2135727-1795527836 on tolerant-swine: rc=0 after 232 s, ended 05:47:45, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc3__cld86a7ad4__pv6c2c33ed_1124054036/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4
- 2026-11-24 05:48 PST DONE [ROM-WEIGHTS-1119] ot-run oth-ubuntu-522269-1795527934 on renewed-glider: rc=0 after 163 s, ended 13:48:15, log /srv/opentallas-scratch2/claude/romw-1119-s81/logs/rank2_R000_r3.log, cmd: --mem 24 --threads 8 --hosts epyc9 --dir /srv/opentallas-scratch2/claude/romw-1119-s81 -- /srv/opentallas-scratch2/claude/romw-1119-s81/s81/
- 2026-11-24 05:48 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2192435-1795527873 on tolerant-swine: rc=0 after 225 s, ended 05:48:16, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_sc_v1__cl64543eaf__cl4590432d_1124054112/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103
- 2026-11-24 05:48 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2191024-1795527873 on tolerant-swine: rc=0 after 231 s, ended 05:48:21, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_cbx_q10__cl89936551_1124052752/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 05:48 PST DONE [ROM-WEIGHTS-1119] ot-run oth-ubuntu-522645-1795527934 on renewed-glider: rc=0 after 170 s, ended 13:48:22, log /srv/opentallas-scratch2/claude/romw-1119-s81/logs/rank2_R000_r1.log, cmd: --mem 24 --threads 8 --hosts epyc9 --dir /srv/opentallas-scratch2/claude/romw-1119-s81 -- /srv/opentallas-scratch2/claude/romw-1119-s81/s81/
- 2026-11-24 05:48 PST DONE [ROM-WEIGHTS-1119] ot-run oth-ubuntu-522522-1795527934 on renewed-glider: rc=0 after 178 s, ended 13:48:30, log /srv/opentallas-scratch2/claude/romw-1119-s81/logs/rank2_R000_r0.log, cmd: --mem 24 --threads 8 --hosts epyc9 --dir /srv/opentallas-scratch2/claude/romw-1119-s81 -- /srv/opentallas-scratch2/claude/romw-1119-s81/s81/
- 2026-11-24 05:48 PST DONE [ROM-WEIGHTS-1119] ot-run oth-ubuntu-522672-1795527934 on renewed-glider: rc=0 after 180 s, ended 13:48:32, log /srv/opentallas-scratch2/claude/romw-1119-s81/logs/rank2_R000_r2.log, cmd: --mem 24 --threads 8 --hosts epyc9 --dir /srv/opentallas-scratch2/claude/romw-1119-s81 -- /srv/opentallas-scratch2/claude/romw-1119-s81/s81/
- 2026-11-24 05:49 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2235024-1795527903 on tolerant-swine: rc=0 after 239 s, ended 05:49:00, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_sc_v2_1124054148/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 05:49 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2278567-1795527937 on tolerant-swine: rc=0 after 214 s, ended 05:49:09, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_cbx_q10__cl94a12200_h_1124052828/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 05:49 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2300961-1795527955 on tolerant-swine: rc=0 after 204 s, ended 05:49:16, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_cbn_q11__cl49ae4555_1124052717/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 05:49 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2397695-1795528037 on tolerant-swine: rc=0 after 140 s, ended 05:49:35, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_stm_v1__cle34a73c3_1124054412/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priva
- 2026-11-24 05:49 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2403271-1795528042 on tolerant-swine: rc=0 after 137 s, ended 05:49:36, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_stm_v2__cl9beb65e6_1124054447/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priva
- 2026-11-24 05:49 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2326426-1795527979 on tolerant-swine: rc=0 after 210 s, ended 05:49:47, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_cbn_q01__cld9ff4c40_1124052642/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 05:50 PST DONE [KV-PC-TAP] ot-run oth-ubuntu-3509371-1795525293 on ubuntu: rc=0 after 2923 s, ended 05:50:12, log /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/hrprov/g9.out, cmd: --mem 56 --threads 8 --dir /srv/opentallas-scratch2/claude/kv-pc-tap --hosts epyc9 -- bash /srv/opentallas-scratch2/claude/kv-pc-tap/g.sh
- 2026-11-24 05:50 PST DONE [KV-RSTREACH] ot-run oth-ubuntu-3696804-1795522825 on civil-redfish: rc=0 after 5429 s, ended 13:50:52, log /srv/opentallas-scratch2/claude/kv-rstreach/fork_a5t.log, cmd: --hosts epyc10 --mem 8 --threads 4 --disk 100 --dir /srv/opentallas-scratch2/claude/kv-rstreach -- python3 -I /srv/opentallas-scratch2/claud
- 2026-11-24 05:51 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2370975-1795528014 on tolerant-swine: rc=0 after 249 s, ended 05:51:01, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_b_v1__cle6023ec2_1124054300/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 05:51 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2420245-1795528053 on tolerant-swine: rc=0 after 250 s, ended 05:51:41, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_b_v2__pva66d0f22__pvb80e2003_1124054336/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6
- 2026-11-24 05:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-24 05:52 PST: 179 running jobs, PROGRESSING 167, SLOW 12, NO-PROGRESS 0 (advisory, no cancel); table lanes/NOPROG.tsv
- 2026-11-24 05:52 PST DRIFT [MERGE-QUEUE -> COORD; cc ADMIT-TUNE-1, KIT-OPS-5] live tree differs from its recorded main sha (1 new): epyc10: rt/current 655f4cb33f9b != hub 2b5bc1d02707. Any live fix must land as a branch + COORD APPROVED; the merge queue lands it and ot-tools-sync deploys it.
- 2026-11-24 05:52 PST STATE [MERGE-QUEUE -> COORD] drift cleared: epyc10: rt/current a8cfe9274e3c != hub b335c93437b7
- 2026-11-24 05:53 PST DONE [s81-serdes-tapskew] ot-push-main otpush-outgoing-giraffe-2239417 on outgoing-giraffe: rc=0 after 487 s, ended 13:53:14, log none, cmd: ot-push-main 
- 2026-11-24 05:55 PST DONE [QC-FWDCLK-REPOINT] ot-run oth-ubuntu-1806660-1795524142 on loved-redfish: rc=0 after 4378 s, ended 13:55:17, log /srv/opentallas-scratch2/claude/QC-FWDCLK-REPOINT/gate2.ot, cmd: --mem 64 --threads 4 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/QC-FWDCLK-REPOINT -- bash /srv/opentallas-scratch2/claude/QC-FWDCLK
- 2026-11-24 05:55 PST DIED [S81-VPW-CONE] ot-run oth-ubuntu-3947813-1795514473 on renewed-glider: rc=2 after 14047 s, ended 13:55:18, log /srv/opentallas-scratch2/claude/s81-vpw-cone/gate_wreg1.otrun.log, cmd: --mem 96 --threads 16 --hosts epyc9 --disk 40 -- bash /srv/opentallas-scratch2/claude/s81-vpw-cone/run_gate.sh | class=NO-PATTERN cause=ot-run: rt pinned for this unit: OT_TOOLSTALE_RT=/srv/opentallas-scratch2
- 2026-11-24 05:55 PST DONE [QC-OPEN-SU] ot-run oth-ubuntu-4046867-1795526408 on renewed-glider: rc=0 after 2142 s, ended 13:55:48, log /srv/opentallas-scratch2/claude/QC-OPEN-SU/sc3/allfull.ot, cmd: --mem 64 --threads 8 --hosts epyc9 --dir /srv/opentallas-scratch2/claude/QC-OPEN-SU/sc3 -- bash /srv/opentallas-scratch2/claude/QC-OPEN-SU/s
- 2026-11-24 05:56 PST DONE [BIND-ALL-ERRORS] ot-run oth-ubuntu-1231905-1795526979 on civil-redfish: rc=0 after 1611 s, ended 13:56:28, log none, cmd: --mem 16 --threads 1 --hosts epyc10 -- bash /srv/opentallas-scratch2/claude/BIND-ALL-ERRORS/tt4.sh
- 2026-11-24 05:57 PST DONE [CORE-TAP-BUDGET] ot-run oth-ubuntu-1202585-1795526932 on tolerant-swine: rc=0 after 1691 s, ended 05:57:01, log none, cmd: --mem 40 --threads 4 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/CORE-TAP-BUDGET/regen -- bash /srv/opentallas-scratch2/claude/CORE
- 2026-11-24 06:00 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 2 flagged of 149 containers {'UNSIGNABLE': 2, 'YOUNG': 127, 'NO-DATA': 2, 'PROGRESS': 18}; full table lanes/NOPROG-TABLE.md; flagged: epyc2 cbn_q01 tt_setup_repair_grt [UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -743.27 ps (< -300,] UNSIGNABLE (hub: ot-run --ca; epyc8 cbn_q01 tt_setup_repair_grt [UNSIGNABLE: tt_setup_repair_grt.log l
- 2026-11-24 06:00 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-3058699-1795528195 on tolerant-swine: rc=0 after 651 s, ended 06:00:39, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_hgi_1124041954/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_h
- 2026-11-24 06:01 PST DIED [S81-KVLEAF-T2-ARCH-R2] ot-run oth-ubuntu-1425940-1795527416 on civil-redfish: rc=2 after 1477 s, ended 14:01:31, log /srv/opentallas-scratch2/claude/s81-kvleaf-t2-arch/blk97/otrun3.log, cmd: --mem 100 --threads 2 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/s81-kvleaf-t2-arch/blk97 -- env SEQ=16 bash eq3.sh | class=SETUP cause=grep: /srv/opentallas-scratch2/claude/s81-kvleaf-t2-ar
- 2026-11-24 06:04 PST DONE [QC-OPEN-COLL] ot-run oth-ubuntu-1830523-1795528463 on civil-redfish: rc=0 after 1233 s, ended 14:04:49, log /srv/opentallas-scratch2/claude/QC-OPEN-COLL/rowA_lec/lec_posC2.ot, cmd: --mem 48 --threads 8 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/QC-OPEN-COLL/rowA_lec -- bash /srv/opentallas-scratch2/claude/QC-O
- 2026-11-24 06:05 PST DONE [QC-OPEN-COLL] ot-run oth-ubuntu-1829527-1795528462 on civil-redfish: rc=0 after 1255 s, ended 14:05:11, log /srv/opentallas-scratch2/claude/QC-OPEN-COLL/rowA_lec/lec_posC3.ot, cmd: --mem 48 --threads 8 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/QC-OPEN-COLL/rowA_lec -- bash /srv/opentallas-scratch2/claude/QC-O
- 2026-11-24 06:05 PST DONE [QC-OPEN-COLL] ot-run oth-ubuntu-1830828-1795528464 on civil-redfish: rc=0 after 1285 s, ended 14:05:41, log /srv/opentallas-scratch2/claude/QC-OPEN-COLL/rowA_lec/lec_posC1.ot, cmd: --mem 48 --threads 8 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/QC-OPEN-COLL/rowA_lec -- bash /srv/opentallas-scratch2/claude/QC-O
- 2026-11-24 06:05 PST DONE [QC-OPEN-COLL] ot-run oth-ubuntu-1828626-1795528461 on civil-redfish: rc=0 after 1291 s, ended 14:05:47, log /srv/opentallas-scratch2/claude/QC-OPEN-COLL/rowA_lec/lec_negC1.ot, cmd: --mem 48 --threads 8 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/QC-OPEN-COLL/rowA_lec -- bash /srv/opentallas-scratch2/claude/QC-O
- 2026-11-24 06:06 PST DONE [QC-OPEN-COLL] ot-run oth-ubuntu-1829826-1795528462 on civil-redfish: rc=0 after 1312 s, ended 14:06:08, log /srv/opentallas-scratch2/claude/QC-OPEN-COLL/rowA_lec/lec_posC0.ot, cmd: --mem 48 --threads 8 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/QC-OPEN-COLL/rowA_lec -- bash /srv/opentallas-scratch2/claude/QC-O
- 2026-11-24 06:06 PST DONE [KV-SPINE-REWIRE] ot-run oth-ubuntu-1859365-1795526138 on tolerant-swine: rc=0 after 3078 s, ended 06:06:54, log /srv/opentallas-scratch2/claude/kv-spine-rewire/logs/gate_R6.otrun.log, cmd: --hosts intel2 --mem 120 --threads 12 --priority proof --dir /srv/opentallas-scratch2/claude/kv-spine-rewire --stage /srv/opentallas-scratch
- 2026-11-24 06:07 PST STATE [MERGE-QUEUE -> COORD] drift cleared: epyc10: rt/current 655f4cb33f9b != hub 2b5bc1d02707
- 2026-11-24 06:07 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-3263612-1795528606 on tolerant-swine: rc=0 after 661 s, ended 06:07:40, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_hgi_v7_1124042131/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_h
- 2026-11-24 06:08 PST DONE [S81-T2-REFLOOR] ot-run oth-ubuntu-1777517-1795528311 on ubuntu: rc=0 after 984 s, ended 06:08:11, log /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/D3.log, cmd: --mem 64 --threads 8 --disk 20 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/s81-t2-refloor -- bash /srv/opentallas-scratch2/claude/s
- 2026-11-24 06:08 PST DIED [S81-T2-REFLOOR] ot-run oth-ubuntu-2091667-1795529301 on ubuntu: rc=1 after 4 s, ended 06:08:22, log /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/D3sb.log, cmd: --mem 250 --threads 8 --disk 20 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/s81-t2-refloor -- bash /srv/opentallas-scratch2/claude/ | class=SETUP cause=sha256sum: /srv/opentallas
- 2026-11-24 06:11 PST DIED [QC-RSTCNT] ot-run oth-ubuntu-2147490-1795526811 on key-cardinal: rc=1 after 2682 s, ended 06:11:30, log /srv/opentallas-scratch2/claude/QC-RSTCNT/h/trial4.ot, cmd: --mem 64 --threads 4 --hosts intel1 --dir /srv/opentallas-scratch2/claude/QC-RSTCNT/h -- bash /srv/opentallas-scratch2/claude/QC-RSTCNT/tria | class=BIND-FAIL cause=BIND_RC 1
- 2026-11-24 06:14 PST DONE [HEAD-WEST] ot-run oth-ubuntu-270998-1795529209 on tolerant-swine: rc=0 after 3507 s, ended 06:14:04, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/HEAD-WEST/s81_head_hd_lep0N_w_1124051025/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18gw/private/H
- 2026-11-24 06:14 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-3517574-1795529028 on tolerant-swine: rc=0 after 647 s, ended 06:14:29, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_hgi_v2__cl2862d491_1124042014/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_h
- 2026-11-24 06:14 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-336993-1795529351 on tolerant-swine: rc=0 after 3395 s, ended 06:14:44, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_cbf_q00__cl1b5a6458_1124051551/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private

