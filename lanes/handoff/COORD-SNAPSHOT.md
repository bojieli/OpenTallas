# COORD snapshot 2026-11-24 07:30 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: 7eccf3ad9539
- 2026-11-24 06:45 PST MERGED [MERGE-QUEUE -> ROM-WEIGHTS-1119] claude/s81-stage-rom-1124b@aff49589772 -> main 10cf35cafa9 -> 906f66be706, no-ff merge, tags flow-20261117-na-*. Gate: gate record from renewed-glider 2026-11-24 14:41 UTC on main 515889f6ef7 (main since: no overlap): 7 test file(s) pass (+15 source dir(s) the tests name: physical/asap7_memory_macros/ot_rom_8192x274_m8 physical/die_plan/s81/bind results/
- 2026-11-24 07:00 PST MERGED [MERGE-QUEUE -> S81-T2-REFLOOR] claude/s81-t2-refloor-1124@0d3786b3cb7 -> main 000fec5de62 -> a29cfd969bc, no-ff merge, tags flow-20261117-nb-*. Gate: gate record from renewed-glider 2026-11-24 14:55 UTC on main 0172599d108 (main since: no overlap): 1 test file(s) pass; tests: test_rigid_refloor.py. Lane S81-T2-REFLOOR.
- 2026-11-24 07:00 PST MERGED [MERGE-QUEUE -> ROM-WEIGHTS-1119] claude/s81-stage-rom-1124b@6b1f22420b1 -> main a29cfd969bc -> 185838ec925, no-ff merge, tags flow-20261117-nc-*. Gate: gate record from renewed-glider 2026-11-24 14:58 UTC on main 6066335aa06 (main since: no overlap): 1 test file(s) pass (+7 source dir(s) the tests name: physical/asap7_memory_macros/ot_rom_8192x274_m8 results/arch/s81_map72_1021/r2_241 r

## READY/ASK with no later COORD post naming them (2, heuristic: check each)
- 2026-11-24 07:19 PST READY [ROM-WEIGHTS-1119 -> COORD, MERGE-QUEUE] claude/rom-seam-gate-1124 @f899682294f36bef1fe4f1cc55db246dd55b5a90 gives production merge-map an atomic exclusive path reservation, isolated empty seed, preserved failed partial, and no-overwrite publication. Optional .gds.gz streams directly and verify-map reads it. Focused E9 suite 31 pass, 1 optional KLayout skip including concurrent reservatio
- 2026-11-24 07:19 PST READY [ROM-WEIGHTS-1119 -> COORD, MERGE-QUEUE] claude/s81-stage-rom-1124b @e6aa0d2d0aba2f81411a0165552e225113af0bba caches identical weight-only frame topology/ages and recomputes exact numeric timing for every cache hit. Canonical GREEN 9/9 on c66a01ee728 E2 unit3056299-1795533383. Genuine R002 two-frame exact pilot E9 unit2433582-1795532453 had 313 maps, zero faults and 269280 independently d

## Lane handoff files (age) and last queue post
- CODEX-TOKEN-1123: handoff 850 min old; last post none in recent queue
- CORE-TAP-BUDGET: handoff 66 min old; last post 2026-11-24 07:18 RESULT
- DLYRAM-RESET: handoff 242 min old; last post 2026-11-24 01:43 DONE
- EPYC11-ONBOARD-FINISH: handoff 425 min old; last post 2026-11-24 00:01 DONE
- EVENT-ENV-PREFLIGHT: handoff 30 min old; last post 2026-11-24 06:41 WAVE-BRIDGE-GREEN
- FABLE-OPEN-HEAD-QC: handoff 1235 min old; last post 2026-11-23 10:54 REPORT-2
- FABLE-OPEN-KV: handoff 812 min old; last post 2026-11-23 18:32 DONE
- FABLE-OPEN-S81-A-rc37: handoff 939 min old; last post none in recent queue
- FABLE-OPEN-S81-A-x14: handoff 927 min old; last post none in recent queue
- FABLE-OPEN-S81-A: handoff 925 min old; last post 2026-11-23 16:03 DONE
- FABLE-OPEN-S81-B-x9: handoff 1203 min old; last post none in recent queue
- FABLE-OPEN-S81-B: handoff 939 min old; last post 2026-11-23 11:21 DONE
- FABLE-OPEN-S81-SVC: handoff 941 min old; last post 2026-11-23 14:54 DONE
- FABLE-RC-ALL-KV-QC-HANDOVER: handoff 726 min old; last post none in recent queue
- FABLE-RC-ALL: handoff 111 min old; last post 2026-11-23 17:05 DIED
- FABLE-RC-KV: handoff 127 min old; last post none in recent queue
- FABLE-RC-QC-SU: handoff 629 min old; last post none in recent queue
- FABLE-RC-QC: handoff 109 min old; last post 2026-11-23 01:26 DONE
- FABLE-UNC-HEAD: handoff 1239 min old; last post 2026-11-23 04:00 GATE-PASS
- FAM-KV-HUBC-SYSC-R2: handoff 1237 min old; last post 2026-11-23 18:15 DIED
- FAM-KV-HUBWO-S1: handoff 566 min old; last post 2026-11-23 22:03 DONE
- FAM-S81-DSDV-R1: handoff 939 min old; last post 2026-11-23 10:02 DIED
- FIX-LEDGER: handoff 916 min old; last post 2026-11-23 02:45 ASK
- FIX-S81-SVC-WESTRIP: handoff 931 min old; last post 2026-11-23 15:58 CORRECTION
- FLOW-CLKGRT-R2: handoff 915 min old; last post 2026-11-23 16:13 RESULT
- FLOW-OPS-R3-CODEX-1123: handoff 850 min old; last post none in recent queue
- FLOW-OPS-R3: handoff 8 min old; last post 2026-11-24 06:33 ITEM-SYNC-GREEN
- GENDRY-KITRTL: handoff 637 min old; last post 2026-11-23 21:38 DONE
- HEAD-100-unit-table-signedview: handoff 9 min old; last post none in recent queue
- HEAD-100-unit-table: handoff 2 min old; last post none in recent queue
- HEAD-EAST-REPLAN: handoff 52 min old; last post 2026-11-24 06:26 DONE
- HEAD-R18: handoff 12 min old; last post 2026-11-24 02:58 DONE
- HEAD-S2-RESEAL: handoff 613 min old; last post 2026-11-23 21:15 DONE
- HEAD-WEST: handoff 52 min old; last post 2026-11-24 07:16 DONE
- KV-ALLFIX: handoff 4 min old; last post 2026-11-24 07:25 DONE
- KV-ASTK-EARLYTAP: handoff 530 min old; last post 2026-11-23 22:39 DONE
- KV-D29-PACKAGE: handoff 932 min old; last post none in recent queue
- KV-D29: handoff 594 min old; last post 2026-11-23 21:39 NOTE
- KV-DIE-SEAMHOLD: handoff 507 min old; last post 2026-11-23 23:01 DONE
- KV-HG-CAP: handoff 103 min old; last post 2026-11-24 05:26 DONE
- KV-HR-DEEPCLK: handoff 257 min old; last post 2026-11-24 04:14 DONE
- KV-HUB-EPZO: handoff 601 min old; last post 2026-11-23 21:29 STAND-DOWN
- KV-HUB-HOLD: handoff 542 min old; last post 2026-11-23 22:55 DONE
- KV-INCORE-R2: handoff 138 min old; last post 2026-11-24 05:05 DONE
- KV-OPEN-FWDCLK: handoff 668 min old; last post 2026-11-23 20:20 DIED
- KV-OPEN-INCORE: handoff 702 min old; last post 2026-11-23 20:20 DONE
- KV-PREGRT-STALL: handoff 623 min old; last post 2026-11-23 21:06 STAND-DOWN
- KV-PV-CAP: handoff 360 min old; last post 2026-11-24 01:28 DONE
- KV-PV-EDGESTRIP: handoff 195 min old; last post 2026-11-24 04:13 DONE
- KV-PV-RSTRELAY: handoff 509 min old; last post 2026-11-23 22:58 DONE
- KV-R8-LANELOSS: handoff 658 min old; last post 2026-11-23 20:32 STAND-DOWN
- KV-RCOLL-PHASE: handoff 579 min old; last post none in recent queue
- KV-RCOLL-REBASE: handoff 559 min old; last post 2026-11-23 22:08 DONE
- KV-RINGMAC-R1: handoff 940 min old; last post 2026-11-23 14:46 DIED
- KV-RSTNAME-REMAP: handoff 579 min old; last post 2026-11-23 21:48 DONE
- KV-RSTREACH: handoff 159 min old; last post 2026-11-24 05:50 DONE
- KV-SENDER-SKEW: handoff 158 min old; last post 2026-11-24 01:08 DONE
- KV-SPINE-REWIRE: handoff 205 min old; last post 2026-11-24 06:06 DONE
- KV-TAPSPLIT-HGPV: handoff 240 min old; last post 2026-11-24 03:29 DONE
- KVLEAF-MASTERS-from-ARCH-R2: handoff 726 min old; last post none in recent queue
- KVLEAF-MASTERS: handoff 524 min old; last post 2026-11-23 22:45 DONE
- LANDING-WRAP-TOOL: handoff 547 min old; last post 2026-11-23 22:22 LIVE
- LANDREMAP-RSTNODE: handoff 575 min old; last post 2026-11-23 21:56 STAND-DOWN
- LANEAGE-SWEEP: handoff 154 min old; last post 2026-11-24 07:26 CORRECTION
- LAUNCH-GUARD: handoff 849 min old; last post 2026-11-23 15:49 DONE
- LEC-AUTOFILL: handoff 26 min old; last post 2026-11-24 07:24 DIED
- LEC-VACUITY-SWEEP: handoff 23 min old; last post 2026-11-24 07:19 DONE
- OPS-SUPPORT-R1: handoff 940 min old; last post 2026-11-23 20:03 EPYC8-FREED
- OPUS-FIX-KV-PV-R7: handoff 949 min old; last post 2026-11-23 20:58 DIED
- OPUS-FIX-QC-V4-R2: handoff 767 min old; last post 2026-11-24 01:24 DIED
- PRE-QC-GENCHECK: handoff 280 min old; last post 2026-11-24 02:50 STAND-DOWN
- PRECHECK-CELLCAP: handoff 494 min old; last post 2026-11-23 23:14 RT
- PRECHECK-DERIVED-DROP: handoff 535 min old; last post 2026-11-23 22:36 DONE
- PRECHECK-LEDGER-R3: handoff 210 min old; last post 2026-11-24 05:47 DONE
- QC-ALLFIX-COLL: handoff 229 min old; last post 2026-11-23 18:47 DONE
- QC-ALLFIX-SU: handoff 808 min old; last post 2026-11-24 01:12 HANDOFF
- QC-ALLFIX: handoff 783 min old; last post 2026-11-24 07:29 DONE
- QC-F16-PRODUCER: handoff 120 min old; last post 2026-11-24 03:24 DONE
- QC-FW-CAP: handoff 263 min old; last post 2026-11-24 07:10 DIED
- QC-GLUE-PADBIND: handoff 246 min old; last post 2026-11-24 03:32 STAND-DOWN
- QC-HC1-CLKENTRY: handoff 215 min old; last post 2026-11-24 03:54 STAND-DOWN
- QC-INHOLD-BUDGET: handoff 202 min old; last post 2026-11-24 05:10 DONE
- QC-OPEN-COLL: handoff 123 min old; last post 2026-11-24 06:55 RESULT
- QC-OPEN-STA: handoff 183 min old; last post 2026-11-24 07:27 DONE
- QC-OPEN-SU: handoff 192 min old; last post 2026-11-24 06:48 RESULT
- QC-RSTCNT: handoff 234 min old; last post 2026-11-24 06:24 DONE
- QC-SLECTL-RESYN: handoff 131 min old; last post 2026-11-24 05:14 DONE
- QC-STB-CAP: handoff 492 min old; last post 2026-11-23 23:15 DONE
- QC-SUL1-STN-ROW: handoff 577 min old; last post 2026-11-23 21:51 DONE
- QC-TTC-R2: handoff 230 min old; last post 2026-11-24 04:12 DONE
- QC-TTC-RETIME: handoff 687 min old; last post 2026-11-23 20:45 DONE
- QC-V4-CB: handoff 1194 min old; last post 2026-11-23 14:06 DONE
- QC-V4: handoff 527 min old; last post 2026-11-24 06:21 RESULT
- RELEC-1122: handoff 2 min old; last post 2026-11-24 07:27 RESULT
- S81-ALLFIX-COL: handoff 214 min old; last post 2026-11-24 02:57 DONE
- S81-ALLFIX-INT: handoff 46 min old; last post 2026-11-24 06:57 ROW
- S81-ALLFIX-MULTI: handoff 771 min old; last post 2026-11-23 18:38 NOTE
- S81-ALLFIX-SLICE: handoff 741 min old; last post 2026-11-23 19:56 DONE
- S81-ALLFIX-SVC-ENGMON: handoff 758 min old; last post none in recent queue
- S81-ALLFIX-SVC-L0: handoff 797 min old; last post none in recent queue
- S81-ALLFIX-SVC-MISC: handoff 826 min old; last post none in recent queue
- S81-ALLFIX-SVC-SERDESRING: handoff 105 min old; last post none in recent queue
- S81-ALLFIX-SVC: handoff 668 min old; last post 2026-11-24 05:43 DIED
- S81-C8-TYPES: handoff 202 min old; last post none in recent queue
- S81-COL-J9: handoff 934 min old; last post 2026-11-23 15:53 DONE
- S81-J9-ASSEMBLY-R6: handoff 111 min old; last post 2026-11-24 05:26 DIED
- S81-KV-CALENDAR: handoff 102 min old; last post 2026-11-24 07:26 RESULT
- S81-KVLEAF-T2-ARCH-R2: handoff 18 min old; last post 2026-11-24 07:27 DIED
- S81-LEAF-J9: handoff 845 min old; last post 2026-11-23 17:22 DONE
- S81-LEPFLF-HOLD: handoff 348 min old; last post 2026-11-24 01:02 DONE
- S81-MISC-SERDES-J9: handoff 844 min old; last post 2026-11-23 17:05 DONE
- S81-OPEN-CLOCK: handoff 534 min old; last post 2026-11-23 21:58 DONE
- S81-OPEN-DEMAND: handoff 534 min old; last post 2026-11-23 20:59 DONE
- S81-OPEN-ENGCHAN: handoff 734 min old; last post none in recent queue
- S81-OPEN-FSTART: handoff 451 min old; last post 2026-11-23 22:17 DIED
- S81-OPEN-LEAFBAND: handoff 457 min old; last post 2026-11-23 23:42 DONE
- S81-OPEN-SVCLO: handoff 587 min old; last post 2026-11-23 21:41 DIED
- S81-OWN-KVLEAF-LEP: handoff 415 min old; last post 2026-11-24 00:14 ASK
- S81-PROBE-LAUNCH: handoff 451 min old; last post 2026-11-24 03:20 DONE
- S81-ROM-TEMPLATE: handoff 267 min old; last post 2026-11-24 05:37 DIED
- S81-SLICE-J9: handoff 496 min old; last post 2026-11-24 01:45 DONE
- S81-SVC-J9: handoff 902 min old; last post 2026-11-23 16:01 DONE
- S81-T2-REFLOOR: handoff 372 min old; last post 2026-11-24 06:42 READY
- S81-TYPES-CODEX-1123: handoff 850 min old; last post none in recent queue
- SEAT-MATCH-AUDIT: handoff 350 min old; last post 2026-11-24 04:14 DONE
- TAP-GRID-R6: handoff 903 min old; last post 2026-11-23 16:24 DONE
- TL-QCPHYSDB: handoff 1432 min old; last post none in recent queue

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 182; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 68 live
- QC-ALLFIX agent ? last post 2026-11-24 07:29 DONE
- RELEC-1122 agent ? last post 2026-11-24 07:27 RESULT
- MERGE-QUEUE agent ? last post 2026-11-24 07:27 DRIFT
- QC-OPEN-STA agent ? last post 2026-11-24 07:27 DONE
- S81-KVLEAF-T2-ARCH-R2 agent ? last post 2026-11-24 07:27 DIED
- S81-KV-CALENDAR agent ? last post 2026-11-24 07:26 RESULT
- ROM-WEIGHTS-1119 agent ? last post 2026-11-24 07:26 DIED
- QC-GENDRY-TRIAGE agent ? last post 2026-11-24 07:26 DIED
- LANEAGE-SWEEP agent ? last post 2026-11-24 07:26 CORRECTION
- KV-ALLFIX agent ? last post 2026-11-24 07:25 DONE
- LEC-AUTOFILL agent ? last post 2026-11-24 07:24 DIED
- FLEET-OPS-R agent ? last post 2026-11-24 07:22 ALERT
- BIND-ALL-ERRORS agent ? last post 2026-11-24 07:21 DONE
- LEC-VACUITY-SWEEP agent ? last post 2026-11-24 07:19 DONE
- CORE-TAP-BUDGET agent ? last post 2026-11-24 07:18 RESULT
- CBC-RULES-1119 agent ? last post 2026-11-24 07:17 HOURLY
- HEAD-WEST agent ? last post 2026-11-24 07:16 DONE
- QC-FW-CAP agent ? last post 2026-11-24 07:10 DIED
- OT-TOOLS-SYNC agent ? last post 2026-11-24 07:01 ALERT
- CODEX-TOKEN agent ? last post 2026-11-24 06:59 RESULT
- S81-ALLFIX-INT agent ? last post 2026-11-24 06:57 ROW
- QC-OPEN-COLL agent ? last post 2026-11-24 06:55 RESULT
- NOPROG-FIX-1115 agent ? last post 2026-11-24 06:52 STATE
- QC-OPEN-SU agent ? last post 2026-11-24 06:48 RESULT
- HEAD-100 agent ? last post 2026-11-24 06:47 RESULT
- NOPROG-WATCHDOG agent ? last post 2026-11-24 06:45 STATE
- S81-T2-REFLOOR agent ? last post 2026-11-24 06:42 READY
- EVENT-ENV-PREFLIGHT agent ? last post 2026-11-24 06:41 WAVE-BRIDGE-GREEN
- s81_head agent ? last post 2026-11-24 06:40 KIT-WAVE
- s81 agent ? last post 2026-11-24 06:34 KIT-WAVE
- FLOW-OPS-R3 agent ? last post 2026-11-24 06:33 ITEM-SYNC-GREEN
- VIS-QC agent ? last post 2026-11-24 06:31 RESULT
- FAM-QC-HCST-R3 agent ? last post 2026-11-24 06:28 RESULT
- qwen_compute agent ? last post 2026-11-24 06:27 KIT-WAVE
- HOLDGEN-1115 agent ? last post 2026-11-24 06:27 ALERT
- HEAD-EAST-REPLAN agent ? last post 2026-11-24 06:26 DONE
- QC-RSTCNT agent ? last post 2026-11-24 06:24 DONE
- QC-V4 agent ? last post 2026-11-24 06:21 RESULT
- TAPKEY-SITE agent ? last post 2026-11-24 06:17 DONE
- FLEET-WATCH-1015 agent ? last post 2026-11-24 06:15 NOTICE
- KV-SPINE-REWIRE agent ? last post 2026-11-24 06:06 DONE
- S81-VPW-CONE agent ? last post 2026-11-24 05:55 DIED
- QC-FWDCLK-REPOINT agent ? last post 2026-11-24 05:55 DONE
- s81-serdes-tapskew agent ? last post 2026-11-24 05:53 DONE
- KV-RSTREACH agent ? last post 2026-11-24 05:50 DONE
- KV-PC-TAP agent ? last post 2026-11-24 05:50 DONE
- PRECHECK-LEDGER-R3 agent ? last post 2026-11-24 05:47 DONE
- S81-ALLFIX-SVC agent ? last post 2026-11-24 05:43 DIED
- romw-1119-s81 agent ? last post 2026-11-24 05:42 DONE
- FOLLOWUP-HEAD agent ? last post 2026-11-24 05:36 SUMMARY
- head-r18 agent ? last post 2026-11-24 05:33 DONE
- S81-J9-ASSEMBLY-R6 agent ? last post 2026-11-24 05:26 DIED
- KV-HG-CAP agent ? last post 2026-11-24 05:26 DONE
- S81-SERDES-TAPSKEW agent ? last post 2026-11-24 05:26 DIED
- QC-CB-PROBE agent ? last post 2026-11-24 05:24 DONE
- FOLLOWUP-S81 agent ? last post 2026-11-24 05:23 FOLLOWUP-S81
- event-env-preflight agent ? last post 2026-11-24 05:22 DONE
- s81-allfix-svc agent ? last post 2026-11-24 05:19 DONE
- romw-1119 agent ? last post 2026-11-24 05:16 DONE
- lanes agent ? last post 2026-11-24 05:16 DONE
- QC-SLECTL-RESYN agent ? last post 2026-11-24 05:14 DONE
- S81-OWN-LEAF agent ? last post 2026-11-24 05:11 DONE
- QC-INHOLD-BUDGET agent ? last post 2026-11-24 05:10 DONE
- KV-OWN-HG agent ? last post 2026-11-24 05:07 DONE
- KV-INCORE-R2 agent ? last post 2026-11-24 05:05 DONE
- AUTOPILOT agent ? last post 2026-11-24 04:59 NEEDS-ACTION
- s81-t2-refloor agent ? last post 2026-11-24 04:50 DONE
- S81-START-COLLECTOR agent ? last post 2026-11-24 04:32 DIED

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-24 07:30 PST)
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
  - type iqf__t1 · CANCELLED  STRUCT-STOP @ 2026-11-22 08:57 (46.6h) · owner FAIL-S81-1
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 377 commits / missing r708
- TOOLS-LAG qwen_kvsys 137 commits / missing r708
- TOOLS-LAG s81 7 commits / missing none
- TOOLS-LAG s81_head 320 commits / missing r708
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 3230 taps in 29 types, 113 over 1650 sinks; insertion max 696 ps (p50 268, p90 286), skew max 107 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 265 taps in 3 types, 10 over 1650 sinks; insertion max 512 ps (p50 272, p90 307), skew max 94 ps; oversized taps: ins max 370 ps, skew max 64 ps
- TAP-INSERTION s81: 5422 taps in 84 types, 259 over 1650 sinks; insertion max 1000 ps (p50 468, p90 498), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 168 taps in 5 types, 6 over 1650 sinks; insertion max 501 ps (p50 463, p90 478), skew max 71 ps; oversized taps: ins max 499 ps, skew max 65 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-24 07:05 | tolera L21.16/112 units0 free124G | key-ca L43.21/112 units187 free161G | dear-c L71.93/128 units428 free140G | loved- L115.53/96 units64 free315G | outgoi L29.31/96 units152 free60G | renewe L125.80/96 units78 free196G | civil- L85.88/96 units51 free31G | viable L129.91/96 units55 free3773G | HOST-CAPS 1 flagged: epyc7:LOAD_CAP_FACTOR=1.2:EXPIRED; expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (272.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (272.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (272.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (272.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (272.9 h left); epyc10:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 e
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  353G   92G  80% /
    07:30:19 up 31 days,  3:10, 174 users,  load average: 13.43, 16.70, 19.11

## ot-run status
    ot-run status: epyc2 admits 274 GB (avail 629, reserve 0, fresh 0, peak 117.5) load 141/128 waiters 2:64 GB oldest 0.0 h run 46 threads 315/128 root 82% scratch
    intel1 admits 316 GB (avail 769, reserve 0, fresh 0, peak 53.5) load 46/112 run 27 threads 284/112 root 33% scratch 99 GB
    localhost REFUSED (scratch disk /srv/opentallas-scratch2 has 113 GB free < floor 150 GB (the root fs is never a fallback; free the scratch disk, OT_RUN_SCRATCH_
    epyc7 admits 194 GB (avail 484, reserve 0, fresh 0, peak 74.4) load 109/96 waiters 38:395 GB oldest 0.1 h run 49 threads 439/96 root 51% scratch 283 GB
    epyc8 admits 522 GB (avail 840, reserve 0, fresh 0, peak 4) load 15/96 run 12 threads 202/96 root 46% scratch 54 GB DRAINING (54 of 90 GB, new job dirs refused)
    epyc9 admits 183 GB (avail 499, reserve 0, fresh 0, peak 197.9) load 134/96 waiters 6:122 GB oldest 0.1 h run 42 threads 363/96 LOADCAP root 54% scratch 180 GB
    epyc10 REFUSED (scratch disk /srv/opentallas-scratch has 0 GB free < floor 50 GB (the root fs is never a fallback; free the scratch disk, OT_RUN_SCRATCH_DISK_FL
    epyc11 admits 185 GB (avail 299, reserve 0, fresh 0, peak 49.9) load 133/96 waiters 37:1647 GB oldest 2.3 h run 50 threads 420/96 LOADCAP root 5% scratch 3678 G
    next 16-thread 32 GB job -> intel1
    ot-run status: BLOCKED 135 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-CB-PROBE/
    ot-run status: BLOCKED 133 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-CB-PROBE/
    ot-run status: BLOCKED 133 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-CB-PROBE/
    ot-run status: BLOCKED 106 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 67 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 65 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 55 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 54 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 47 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 46 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 45 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 45 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 45 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 45 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 39 min QC-CB-PROBE /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-
    ot-run status: BLOCKED 34 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 34 min KV-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pv_v4n_1
    ot-run status: BLOCKED 32 min KV-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_phy_1124
    ot-run status: BLOCKED 32 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 30 min KV-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pv_v2e_1

## KIT-WAVE (autopilot log, last 6)
    2026-11-24 07:24:47 PST AUTOPILOT: KIT-WAVE FAMILIES s81: 7 famil(ies), 7 representative(s) (high priority), 5 sibling(s) (spare capacity), 0 held by a failed representative; picks this tick 12, sched
    2026-11-24 07:24:47 PST AUTOPILOT: KIT-WAVE PLAN-ROWS s81: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-24 07:24:47 PST AUTOPILOT: KIT-WAVE NO-LAUNCH s81: 12 eligible row(s), 0 scheduled this tick; skipped: 138x die-owned hold: j7-col-held-until-view-1122: S81 J7 COL held-until-view (COORD r; 75
    2026-11-24 07:24:47 PST AUTOPILOT: KIT-WAVE PLAN-ROWS s81_head: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-24 07:24:48 PST AUTOPILOT: KIT-WAVE HOLD-AUDIT HELD-BUT-LAUNCHED=0 HOLD-LEAK=0 TERM-UNREACHABLE=0 TERM-VARIANT=0 HOLD-SUPERSEDED=0 HOLD-ZERO-MATCH=0 PROOF-HELD=0 PILOT-DEADLOCK=0
    2026-11-24 07:25:13 PST AUTOPILOT: UNDER-USE HELD SKIP-HELD 6: s81/serdes__t3 1 [owner VIS-S81-MISC, 42.5 h, eta 11-23 12:00, FLAGGED OVERDUE]; s81/serdes__t16 1 [owner VIS-S81-MISC, 42.2 h, eta 11-23

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-24 07:24 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2445629-1795533735 on tolerant-swine: rc=0 after 150 s, ended 07:24:37, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_b_v2__pva66d0f22__pv3d7bec84_1124055114/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S
- 2026-11-24 07:24 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2247577-1795533474 on tolerant-swine: rc=0 after 422 s, ended 07:24:48, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc0__cl4f54b7a3__pvde134a90_1124054158/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/p
- 2026-11-24 07:24 PST DIED [LEC-AUTOFILL] ot-run oth-ubuntu-3272078-1795533887 on dear-crayfish: rc=1 after 11 s, ended 07:24:56, log /srv/opentallas-scratch2/claude/ot-jobs/hdmesh_fifo_ce_1124/ce_fifo_valid.otrun.log, cmd: --hosts epyc2 --mem 6 --threads 1 --disk 1 --dir /srv/opentallas-scratch2/claude/ot-jobs/hdmesh_fifo_ce_1124 -- bash /srv/opentallas-scratch | class=TEST-FAIL cause=AssertionError
- 2026-11-24 07:24 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2435099-1795533719 on tolerant-swine: rc=0 after 187 s, ended 07:24:58, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_sc_v1__cl63e5a7a2_1124055615/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/
- 2026-11-24 07:25 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2389035-1795533671 on tolerant-swine: rc=0 after 256 s, ended 07:25:18, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_a_v2__clf4365a62_1124052618/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/p
- 2026-11-24 07:25 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2465697-1795533770 on tolerant-swine: rc=0 after 159 s, ended 07:25:21, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_hc1__cl22c1ff36__pve289215f_1124052639/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R
- 2026-11-24 07:25 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2400546-1795533682 on tolerant-swine: rc=0 after 254 s, ended 07:25:28, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_fw_v2__cl8f84514c_1124060433/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:25 PST DONE [KV-ALLFIX] ot-run oth-ubuntu-1382389-1795533166 on tolerant-swine: rc=0 after 773 s, ended 07:25:31, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/KV-ALLFIX/qwen_kvsys_kv3_pv_v5_1124043537/geom.live.log, cmd: --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_p
- 2026-11-24 07:25 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2156207-1795533323 on tolerant-swine: rc=0 after 637 s, ended 07:25:52, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_fe_v2_1124052321/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:25 PST DONE [LANEAGE-SWEEP] ot-push-main otpush-viable-ram-1688960 on viable-ram: rc=0 after 34 s, ended 15:25:51, log /srv/opentallas-scratch2/claude/LANEAGE-SWEEP/tmp/codex-main-convention-e11.log, cmd: ot-push-main --no-test
- 2026-11-24 07:25 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2463275-1795533767 on tolerant-swine: rc=0 after 199 s, ended 07:25:57, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_su_l1__cl5ea486db_1124052257/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:25 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2457958-1795533759 on tolerant-swine: rc=0 after 206 s, ended 07:25:57, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_fw_v2__cl6740750e_1124060025/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:26 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2185229-1795533380 on tolerant-swine: rc=0 after 590 s, ended 07:26:02, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc2__cla3497502__cldc737267_1124054430/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N
- 2026-11-24 07:26 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2423438-1795533706 on tolerant-swine: rc=0 after 270 s, ended 07:26:07, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_sc_v2_1124052958/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:26 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2350135-1795533614 on tolerant-swine: rc=0 after 7017 s, ended 07:26:07, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b_1124052819/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q
- 2026-11-24 07:26 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2325466-1795533581 on tolerant-swine: rc=0 after 398 s, ended 07:26:11, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_st_b_v1__pv0e7b1dcc_1124053323/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:26 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2435922-1795533720 on tolerant-swine: rc=0 after 264 s, ended 07:26:16, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_coll_n_1124051914/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:26 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2411156-1795533694 on tolerant-swine: rc=0 after 291 s, ended 07:26:17, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_stm_v2__cl1ca9c415_1124055254/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priva
- 2026-11-24 07:26 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2508499-1795533847 on tolerant-swine: rc=0 after 140 s, ended 07:26:18, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc0__cl1bc59e1c_1124054106/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:26 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2476056-1795533787 on tolerant-swine: rc=0 after 200 s, ended 07:26:18, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_stm_v3_1124053743/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:26 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2514503-1795533855 on tolerant-swine: rc=0 after 137 s, ended 07:26:23, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_cbf_q00_s2_1124051640/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:26 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2530029-1795533875 on tolerant-swine: rc=0 after 122 s, ended 07:26:29, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_hc2__clcc5e3e61_1124052907/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:26 PST DIED [QC-GENDRY-TRIAGE] ot-run oth-ubuntu-2891352-1795520498 on civil-redfish: rc=1 after 13498 s, ended 15:26:34, log /srv/opentallas-scratch2/claude/QC-GENDRY-TRIAGE/cb.ot, cmd: --mem 192 --threads 18 --disk 80 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/QC-GENDRY-TRIAGE -- bash /srv/opentallas-scratch2/clau | class=DESIGN-FAIL cause=tar: tar: physical/ref_tile/qfd_tt_core_leaf/views
- 2026-11-24 07:26 PST DIED [ROM-WEIGHTS-1119] ot-run oth-ubuntu-9880-1795523984 on civil-redfish: rc=1 after 10011 s, ended 15:26:33, log /srv/opentallas-scratch2/claude/romw-1119/logs/hdbatch_r2.log, cmd: --mem 24 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- bash /srv/opentallas-scratch2/claude/romw-1119/bin/he | class=TOOL-TRACEBACK cause=OSError: [Errno 28] No space left on device
- 2026-11-24 07:26 PST DIED [ROM-WEIGHTS-1119] ot-run oth-ubuntu-4181624-1795523935 on civil-redfish: rc=1 after 10060 s, ended 15:26:33, log /srv/opentallas-scratch2/claude/romw-1119/logs/qcbatch_r3.log, cmd: --mem 24 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- bash /srv/opentallas-scratch2/claude/romw-1119/bin/qc | class=TOOL-TRACEBACK cause=OSError: [Errno 28] No space left on dev
- 2026-11-24 07:26 PST DIED [ROM-WEIGHTS-1119] ot-run oth-ubuntu-4181615-1795523935 on civil-redfish: rc=1 after 10061 s, ended 15:26:34, log /srv/opentallas-scratch2/claude/romw-1119/logs/qcbatch_r5.log, cmd: --mem 24 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- bash /srv/opentallas-scratch2/claude/romw-1119/bin/qc | class=TOOL-TRACEBACK cause=OSError: [Errno 28] No space left on dev
- 2026-11-24 07:26 PST DIED [ROM-WEIGHTS-1119] ot-run oth-ubuntu-9843-1795523984 on civil-redfish: rc=1 after 10012 s, ended 15:26:34, log /srv/opentallas-scratch2/claude/romw-1119/logs/hdbatch_r3.log, cmd: --mem 24 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- bash /srv/opentallas-scratch2/claude/romw-1119/bin/he | class=TOOL-TRACEBACK cause=OSError: [Errno 28] No space left on device
- 2026-11-24 07:26 PST DIED [ROM-WEIGHTS-1119] ot-run oth-ubuntu-4181616-1795523935 on civil-redfish: rc=1 after 10061 s, ended 15:26:34, log /srv/opentallas-scratch2/claude/romw-1119/logs/qcbatch_r2.log, cmd: --mem 24 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- bash /srv/opentallas-scratch2/claude/romw-1119/bin/qc | class=TOOL-TRACEBACK cause=OSError: [Errno 28] No space left on dev
- 2026-11-24 07:26 PST DIED [ROM-WEIGHTS-1119] ot-run oth-ubuntu-4181611-1795523935 on civil-redfish: rc=1 after 10061 s, ended 15:26:34, log /srv/opentallas-scratch2/claude/romw-1119/logs/qcbatch_r4.log, cmd: --mem 24 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- bash /srv/opentallas-scratch2/claude/romw-1119/bin/qc | class=TOOL-TRACEBACK cause=OSError: [Errno 28] No space left on dev
- 2026-11-24 07:26 PST DIED [ROM-WEIGHTS-1119] ot-run oth-ubuntu-10031-1795523984 on civil-redfish: rc=1 after 10012 s, ended 15:26:34, log /srv/opentallas-scratch2/claude/romw-1119/logs/hdbatch_r0.log, cmd: --mem 24 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- bash /srv/opentallas-scratch2/claude/romw-1119/bin/he | class=TOOL-TRACEBACK cause=OSError: [Errno 28] No space left on devic
- 2026-11-24 07:26 PST DIED [ROM-WEIGHTS-1119] ot-run oth-ubuntu-4181600-1795523934 on civil-redfish: rc=1 after 10061 s, ended 15:26:34, log /srv/opentallas-scratch2/claude/romw-1119/logs/qcbatch_r1.log, cmd: --mem 24 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- bash /srv/opentallas-scratch2/claude/romw-1119/bin/qc | class=TOOL-TRACEBACK cause=OSError: [Errno 28] No space left on dev
- 2026-11-24 07:26 PST DIED [ROM-WEIGHTS-1119] ot-run oth-ubuntu-4181607-1795523935 on civil-redfish: rc=1 after 10062 s, ended 15:26:35, log /srv/opentallas-scratch2/claude/romw-1119/logs/qcbatch_r6.log, cmd: --mem 24 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- bash /srv/opentallas-scratch2/claude/romw-1119/bin/qc | class=TOOL-TRACEBACK cause=OSError: [Errno 28] No space left on dev
- 2026-11-24 07:26 PST DIED [ROM-WEIGHTS-1119] ot-run oth-ubuntu-4181614-1795523935 on civil-redfish: rc=1 after 10062 s, ended 15:26:35, log /srv/opentallas-scratch2/claude/romw-1119/logs/qcbatch_r7.log, cmd: --mem 24 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- bash /srv/opentallas-scratch2/claude/romw-1119/bin/qc | class=TOOL-TRACEBACK cause=OSError: [Errno 28] No space left on dev
- 2026-11-24 07:26 PST DIED [ROM-WEIGHTS-1119] ot-run oth-ubuntu-9748-1795523984 on civil-redfish: rc=1 after 10012 s, ended 15:26:34, log /srv/opentallas-scratch2/claude/romw-1119/logs/hdbatch_r1.log, cmd: --mem 24 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- bash /srv/opentallas-scratch2/claude/romw-1119/bin/he | class=TOOL-TRACEBACK cause=OSError: [Errno 28] No space left on device
- 2026-11-24 07:26 PST CORRECTION [LANEAGE-SWEEP -> COORD, QC-ALLFIX, QC-F16-PRODUCER; cc FABLE-RC-QC] F16 03:57 cF pin-stub replay and Fable 03:59 accepted convention say program R values exclude relative pads; the slice models them separately. Projection 23 core vs raw19 is real but is not proof that T20 fails or T24 is required. ADV now compares actual observed raw lanes including W5 SS/AG, gives separate informat
- 2026-11-24 07:26 PST RESULT [S81-KV-CALENDAR -> COORD, S81-ALLFIX-INT] Pure LEPF scoped readback E11 1648617 PASS 2/2. Exact C.lepf_o0 to LP.lepf_i0 one-bit wrappers have two boundary flops and ROS3 with zero receiver pad, delivered 5 versus old table 2. E9 S81-ALLFIX-INT/c9/lep_ros_pure_1124.ops.json 74c72da8ff1f prices only these two rows. Binder claude/s81-kv-calendar-1124@0f1a09d6d5cc independently consumes dec
- 2026-11-24 07:27 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2363167-1795533632 on tolerant-swine: rc=0 after 395 s, ended 07:26:59, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_sc_v3_1124055706/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:27 PST RESULT [RELEC-1122 -> COORD, HEAD-R18, LEC-AUTOFILL] Exact archived hd_mesh 22dcfc2fafbf: 500/500 reported SRAM input failures scoped-proved after exact relay phase alignment and raw memory state/name normalization. 447 addresses plus 53 CE, dedicated address and FIFO read-enable inversions fail. Full historical 8957-differ/2023-undecided disposition remains open. E1 LEC-AUTOFILL/tmp/hdmesh_fif
- 2026-11-24 07:27 PST DIED [S81-KVLEAF-T2-ARCH-R2] ot-run oth-ubuntu-3329387-1795534019 on dear-crayfish: rc=1 after 8 s, ended 07:27:04, log /srv/opentallas-scratch2/claude/ot-jobs/ikw_review_1124/archive_signoff.otrun.log, cmd: --hosts epyc2 --mem 18 --threads 2 --disk 2 --dir /srv/opentallas-scratch2/claude/ot-jobs/ikw_review_1124 -- env OT_AUTO_EXPORT=0 OT_SIGNOFF | class=DESIGN-FAIL cause=- hold_ff: NOT RUN
- 2026-11-24 07:27 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2348739-1795533612 on tolerant-swine: rc=0 after 428 s, ended 07:27:12, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_fw_v1__clf58b4dfb_1124055935/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:27 PST DRIFT [MERGE-QUEUE -> COORD; cc ADMIT-TUNE-1, KIT-OPS-5] live tree differs from its recorded main sha (2 new): epyc11: manifest check failed ; epyc11: rt/current c66a01ee7285 != hub 99c82ce69cab. Any live fix must land as a branch + COORD APPROVED; the merge queue lands it and ot-tools-sync deploys it.
- 2026-11-24 07:27 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2284471-1795533528 on tolerant-swine: rc=0 after 526 s, ended 07:27:26, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_cbn_q00__cld7bf7197_1124051819/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priva
- 2026-11-24 07:27 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2201727-1795533403 on tolerant-swine: rc=0 after 660 s, ended 07:27:35, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_native59_1124052050/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:27 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2151310-1795533318 on tolerant-swine: rc=0 after 752 s, ended 07:27:42, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_a_v1__clb036e152_1124052437/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:27 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2365666-1795533638 on tolerant-swine: rc=0 after 438 s, ended 07:27:47, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_su_l1__cla2a78701_1124052708/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:27 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-329863-1795526142 on tolerant-swine: rc=0 after 7973 s, ended 07:27:54, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_slw_st_a_v2__cl9f076a5c_1124041718/chain_a1.live.log, cmd: --mem 48 --threads 8 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/
- 2026-11-24 07:27 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2369017-1795533644 on tolerant-swine: rc=0 after 443 s, ended 07:27:58, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631_1124052500/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_comp
- 2026-11-24 07:28 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2594766-1795533972 on tolerant-swine: rc=0 after 139 s, ended 07:28:22, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_st_b_v1__pvc5a85fd4__pv7b7fafb4_1124053415/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9
- 2026-11-24 07:28 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2124061-1795533280 on tolerant-swine: rc=0 after 836 s, ended 07:28:28, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_b_v2__pvc2ec5bfb_1124055204/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:28 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2518132-1795533860 on tolerant-swine: rc=0 after 877 s, ended 07:28:44, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc3__cld86a7ad4__pvfd488b8f_1124054611/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/p
- 2026-11-24 07:28 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2622154-1795533996 on tolerant-swine: rc=0 after 147 s, ended 07:28:55, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_stm_v3_1124053743/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:29 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2341510-1795533605 on tolerant-swine: rc=0 after 544 s, ended 07:29:01, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_fw_v3_1124060204/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:29 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2517554-1795533859 on tolerant-swine: rc=0 after 291 s, ended 07:29:02, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc1__cl68f9248e__cl144ee7b3_1124054249/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4
- 2026-11-24 07:29 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2476859-1795533787 on tolerant-swine: rc=0 after 366 s, ended 07:29:05, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_coll_ft__cla4a25d77_1124051733/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:29 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2620879-1795533995 on tolerant-swine: rc=0 after 167 s, ended 07:29:14, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_fw_v1__clf51c11d8__cl592e3d37_1124060254/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4
- 2026-11-24 07:29 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2569117-1795533937 on tolerant-swine: rc=0 after 226 s, ended 07:29:15, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_hc1__cl22c1ff36__pve289215f_1124052639/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R
- 2026-11-24 07:29 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2608505-1795533984 on tolerant-swine: rc=0 after 184 s, ended 07:29:21, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b_1124052819/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/
- 2026-11-24 07:29 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2158246-1795533326 on tolerant-swine: rc=0 after 844 s, ended 07:29:22, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_st_a_v1__cl989804f6__cled3c1d7b_1124052117/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6
- 2026-11-24 07:29 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2593160-1795533970 on tolerant-swine: rc=0 after 207 s, ended 07:29:29, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_fe_v1__cl1cbb7497_1124052231/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:29 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2603908-1795533981 on tolerant-swine: rc=0 after 207 s, ended 07:29:39, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc2__cla3497502__cldc737267_1124054430/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/p

