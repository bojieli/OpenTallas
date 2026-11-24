# COORD snapshot 2026-11-24 07:45 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: d56b624b5029
- 2026-11-24 06:45 PST MERGED [MERGE-QUEUE -> ROM-WEIGHTS-1119] claude/s81-stage-rom-1124b@aff49589772 -> main 10cf35cafa9 -> 906f66be706, no-ff merge, tags flow-20261117-na-*. Gate: gate record from renewed-glider 2026-11-24 14:41 UTC on main 515889f6ef7 (main since: no overlap): 7 test file(s) pass (+15 source dir(s) the tests name: physical/asap7_memory_macros/ot_rom_8192x274_m8 physical/die_plan/s81/bind results/
- 2026-11-24 07:00 PST MERGED [MERGE-QUEUE -> S81-T2-REFLOOR] claude/s81-t2-refloor-1124@0d3786b3cb7 -> main 000fec5de62 -> a29cfd969bc, no-ff merge, tags flow-20261117-nb-*. Gate: gate record from renewed-glider 2026-11-24 14:55 UTC on main 0172599d108 (main since: no overlap): 1 test file(s) pass; tests: test_rigid_refloor.py. Lane S81-T2-REFLOOR.
- 2026-11-24 07:00 PST MERGED [MERGE-QUEUE -> ROM-WEIGHTS-1119] claude/s81-stage-rom-1124b@6b1f22420b1 -> main a29cfd969bc -> 185838ec925, no-ff merge, tags flow-20261117-nc-*. Gate: gate record from renewed-glider 2026-11-24 14:58 UTC on main 6066335aa06 (main since: no overlap): 1 test file(s) pass (+7 source dir(s) the tests name: physical/asap7_memory_macros/ot_rom_8192x274_m8 results/arch/s81_map72_1021/r2_241 r

## READY/ASK with no later COORD post naming them (2, heuristic: check each)
- 2026-11-24 07:19 PST READY [ROM-WEIGHTS-1119 -> COORD, MERGE-QUEUE] claude/rom-seam-gate-1124 @f899682294f36bef1fe4f1cc55db246dd55b5a90 gives production merge-map an atomic exclusive path reservation, isolated empty seed, preserved failed partial, and no-overwrite publication. Optional .gds.gz streams directly and verify-map reads it. Focused E9 suite 31 pass, 1 optional KLayout skip including concurrent reservatio
- 2026-11-24 07:19 PST READY [ROM-WEIGHTS-1119 -> COORD, MERGE-QUEUE] claude/s81-stage-rom-1124b @e6aa0d2d0aba2f81411a0165552e225113af0bba caches identical weight-only frame topology/ages and recomputes exact numeric timing for every cache hit. Canonical GREEN 9/9 on c66a01ee728 E2 unit3056299-1795533383. Genuine R002 two-frame exact pilot E9 unit2433582-1795532453 had 313 maps, zero faults and 269280 independently d

## Lane handoff files (age) and last queue post
- CODEX-TOKEN-1123: handoff 865 min old; last post none in recent queue
- CORE-TAP-BUDGET: handoff 81 min old; last post 2026-11-24 07:18 RESULT
- DLYRAM-RESET: handoff 257 min old; last post 2026-11-24 01:43 DONE
- EPYC11-ONBOARD-FINISH: handoff 440 min old; last post 2026-11-24 00:01 DONE
- EVENT-ENV-PREFLIGHT: handoff 45 min old; last post 2026-11-24 06:41 WAVE-BRIDGE-GREEN
- FABLE-OPEN-HEAD-QC: handoff 1250 min old; last post 2026-11-23 10:54 REPORT-2
- FABLE-OPEN-KV: handoff 827 min old; last post 2026-11-23 18:32 DONE
- FABLE-OPEN-S81-A-rc37: handoff 954 min old; last post none in recent queue
- FABLE-OPEN-S81-A-x14: handoff 942 min old; last post none in recent queue
- FABLE-OPEN-S81-A: handoff 940 min old; last post 2026-11-23 16:03 DONE
- FABLE-OPEN-S81-B-x9: handoff 1218 min old; last post none in recent queue
- FABLE-OPEN-S81-B: handoff 954 min old; last post 2026-11-23 11:21 DONE
- FABLE-OPEN-S81-SVC: handoff 956 min old; last post 2026-11-23 14:54 DONE
- FABLE-RC-ALL-KV-QC-HANDOVER: handoff 741 min old; last post none in recent queue
- FABLE-RC-ALL: handoff 126 min old; last post 2026-11-23 17:05 DIED
- FABLE-RC-KV: handoff 142 min old; last post none in recent queue
- FABLE-RC-QC-SU: handoff 644 min old; last post none in recent queue
- FABLE-RC-QC: handoff 124 min old; last post 2026-11-23 01:26 DONE
- FABLE-UNC-HEAD: handoff 1254 min old; last post 2026-11-23 04:00 GATE-PASS
- FAM-KV-HUBC-SYSC-R2: handoff 1252 min old; last post 2026-11-23 18:15 DIED
- FAM-KV-HUBWO-S1: handoff 581 min old; last post 2026-11-23 22:03 DONE
- FAM-S81-DSDV-R1: handoff 954 min old; last post 2026-11-23 10:02 DIED
- FIX-LEDGER: handoff 931 min old; last post 2026-11-23 02:45 ASK
- FIX-S81-SVC-WESTRIP: handoff 946 min old; last post 2026-11-23 15:58 CORRECTION
- FLOW-CLKGRT-R2: handoff 930 min old; last post 2026-11-23 16:13 RESULT
- FLOW-OPS-R3-CODEX-1123: handoff 865 min old; last post none in recent queue
- FLOW-OPS-R3: handoff 23 min old; last post 2026-11-24 06:33 ITEM-SYNC-GREEN
- GENDRY-KITRTL: handoff 652 min old; last post 2026-11-23 21:38 DONE
- HEAD-100-unit-table-signedview: handoff 9 min old; last post none in recent queue
- HEAD-100-unit-table: handoff 2 min old; last post none in recent queue
- HEAD-EAST-REPLAN: handoff 12 min old; last post 2026-11-24 06:26 DONE
- HEAD-R18: handoff 27 min old; last post 2026-11-24 02:58 DONE
- HEAD-S2-RESEAL: handoff 628 min old; last post 2026-11-23 21:15 DONE
- HEAD-WEST: handoff 12 min old; last post 2026-11-24 07:16 DONE
- KV-ALLFIX: handoff 19 min old; last post 2026-11-24 07:25 DONE
- KV-ASTK-EARLYTAP: handoff 545 min old; last post 2026-11-23 22:39 DONE
- KV-D29-PACKAGE: handoff 947 min old; last post none in recent queue
- KV-D29: handoff 609 min old; last post 2026-11-23 21:39 NOTE
- KV-DIE-SEAMHOLD: handoff 522 min old; last post 2026-11-23 23:01 DONE
- KV-HG-CAP: handoff 118 min old; last post 2026-11-24 05:26 DONE
- KV-HR-DEEPCLK: handoff 272 min old; last post 2026-11-24 04:14 DONE
- KV-HUB-EPZO: handoff 616 min old; last post 2026-11-23 21:29 STAND-DOWN
- KV-HUB-HOLD: handoff 557 min old; last post 2026-11-23 22:55 DONE
- KV-INCORE-R2: handoff 153 min old; last post 2026-11-24 05:05 DONE
- KV-OPEN-FWDCLK: handoff 683 min old; last post 2026-11-23 20:20 DIED
- KV-OPEN-INCORE: handoff 716 min old; last post 2026-11-23 20:20 DONE
- KV-PREGRT-STALL: handoff 638 min old; last post 2026-11-23 21:06 STAND-DOWN
- KV-PV-CAP: handoff 375 min old; last post 2026-11-24 01:28 DONE
- KV-PV-EDGESTRIP: handoff 210 min old; last post 2026-11-24 04:13 DONE
- KV-PV-RSTRELAY: handoff 524 min old; last post 2026-11-23 22:58 DONE
- KV-R8-LANELOSS: handoff 673 min old; last post 2026-11-23 20:32 STAND-DOWN
- KV-RCOLL-PHASE: handoff 594 min old; last post none in recent queue
- KV-RCOLL-REBASE: handoff 574 min old; last post 2026-11-23 22:08 DONE
- KV-RINGMAC-R1: handoff 955 min old; last post 2026-11-23 14:46 DIED
- KV-RSTNAME-REMAP: handoff 594 min old; last post 2026-11-23 21:48 DONE
- KV-RSTREACH: handoff 174 min old; last post 2026-11-24 07:30 DIED
- KV-SENDER-SKEW: handoff 173 min old; last post 2026-11-24 01:08 DONE
- KV-SPINE-REWIRE: handoff 220 min old; last post 2026-11-24 06:06 DONE
- KV-TAPSPLIT-HGPV: handoff 255 min old; last post 2026-11-24 03:29 DONE
- KVLEAF-MASTERS-from-ARCH-R2: handoff 741 min old; last post none in recent queue
- KVLEAF-MASTERS: handoff 539 min old; last post 2026-11-23 22:45 DONE
- LANDING-WRAP-TOOL: handoff 562 min old; last post 2026-11-23 22:22 LIVE
- LANDREMAP-RSTNODE: handoff 590 min old; last post 2026-11-23 21:56 STAND-DOWN
- LANEAGE-SWEEP: handoff 169 min old; last post 2026-11-24 07:44 DONE
- LAUNCH-GUARD: handoff 864 min old; last post 2026-11-23 15:49 DONE
- LEC-AUTOFILL: handoff 6 min old; last post 2026-11-24 07:38 RESULT
- LEC-VACUITY-SWEEP: handoff 38 min old; last post 2026-11-24 07:19 DONE
- OPS-SUPPORT-R1: handoff 955 min old; last post 2026-11-23 20:03 EPYC8-FREED
- OPUS-FIX-KV-PV-R7: handoff 964 min old; last post 2026-11-23 20:58 DIED
- OPUS-FIX-QC-V4-R2: handoff 782 min old; last post 2026-11-24 01:24 DIED
- PRE-QC-GENCHECK: handoff 295 min old; last post 2026-11-24 02:50 STAND-DOWN
- PRECHECK-CELLCAP: handoff 509 min old; last post 2026-11-23 23:14 RT
- PRECHECK-DERIVED-DROP: handoff 550 min old; last post 2026-11-23 22:36 DONE
- PRECHECK-LEDGER-R3: handoff 225 min old; last post 2026-11-24 05:47 DONE
- QC-ALLFIX-COLL: handoff 244 min old; last post 2026-11-23 18:47 DONE
- QC-ALLFIX-SU: handoff 823 min old; last post 2026-11-24 01:12 HANDOFF
- QC-ALLFIX: handoff 798 min old; last post 2026-11-24 07:44 DONE
- QC-F16-PRODUCER: handoff 135 min old; last post 2026-11-24 03:24 DONE
- QC-FW-CAP: handoff 278 min old; last post 2026-11-24 07:31 RESULT
- QC-GLUE-PADBIND: handoff 261 min old; last post 2026-11-24 03:32 STAND-DOWN
- QC-HC1-CLKENTRY: handoff 230 min old; last post 2026-11-24 03:54 STAND-DOWN
- QC-INHOLD-BUDGET: handoff 217 min old; last post 2026-11-24 05:10 DONE
- QC-OPEN-COLL: handoff 138 min old; last post 2026-11-24 06:55 RESULT
- QC-OPEN-STA: handoff 198 min old; last post 2026-11-24 07:41 DONE
- QC-OPEN-SU: handoff 207 min old; last post 2026-11-24 06:48 RESULT
- QC-RSTCNT: handoff 249 min old; last post 2026-11-24 06:24 DONE
- QC-SLECTL-RESYN: handoff 146 min old; last post 2026-11-24 05:14 DONE
- QC-STB-CAP: handoff 507 min old; last post 2026-11-23 23:15 DONE
- QC-SUL1-STN-ROW: handoff 592 min old; last post 2026-11-23 21:51 DONE
- QC-TTC-R2: handoff 245 min old; last post 2026-11-24 04:12 DONE
- QC-TTC-RETIME: handoff 702 min old; last post 2026-11-23 20:45 DONE
- QC-V4-CB: handoff 1209 min old; last post 2026-11-23 14:06 DONE
- QC-V4: handoff 542 min old; last post 2026-11-24 06:21 RESULT
- RELEC-1122: handoff 17 min old; last post 2026-11-24 07:27 RESULT
- S81-ALLFIX-COL: handoff 229 min old; last post 2026-11-24 02:57 DONE
- S81-ALLFIX-INT: handoff 13 min old; last post 2026-11-24 07:35 ROW
- S81-ALLFIX-MULTI: handoff 786 min old; last post 2026-11-23 18:38 NOTE
- S81-ALLFIX-SLICE: handoff 756 min old; last post 2026-11-23 19:56 DONE
- S81-ALLFIX-SVC-ENGMON: handoff 773 min old; last post none in recent queue
- S81-ALLFIX-SVC-L0: handoff 812 min old; last post none in recent queue
- S81-ALLFIX-SVC-MISC: handoff 841 min old; last post none in recent queue
- S81-ALLFIX-SVC-SERDESRING: handoff 120 min old; last post none in recent queue
- S81-ALLFIX-SVC: handoff 683 min old; last post 2026-11-24 05:43 DIED
- S81-C8-TYPES: handoff 217 min old; last post none in recent queue
- S81-COL-J9: handoff 949 min old; last post 2026-11-23 15:53 DONE
- S81-J9-ASSEMBLY-R6: handoff 126 min old; last post 2026-11-24 05:26 DIED
- S81-KV-CALENDAR: handoff 117 min old; last post 2026-11-24 07:26 RESULT
- S81-KVLEAF-T2-ARCH-R2: handoff 6 min old; last post 2026-11-24 07:31 DONE
- S81-LEAF-J9: handoff 860 min old; last post 2026-11-23 17:22 DONE
- S81-LEPFLF-HOLD: handoff 363 min old; last post 2026-11-24 01:02 DONE
- S81-MISC-SERDES-J9: handoff 859 min old; last post 2026-11-23 17:05 DONE
- S81-OPEN-CLOCK: handoff 549 min old; last post 2026-11-23 21:58 DONE
- S81-OPEN-DEMAND: handoff 549 min old; last post 2026-11-23 20:59 DONE
- S81-OPEN-ENGCHAN: handoff 749 min old; last post none in recent queue
- S81-OPEN-FSTART: handoff 466 min old; last post 2026-11-23 22:17 DIED
- S81-OPEN-LEAFBAND: handoff 472 min old; last post 2026-11-23 23:42 DONE
- S81-OPEN-SVCLO: handoff 602 min old; last post 2026-11-23 21:41 DIED
- S81-OWN-KVLEAF-LEP: handoff 430 min old; last post 2026-11-24 00:14 ASK
- S81-PROBE-LAUNCH: handoff 466 min old; last post 2026-11-24 03:20 DONE
- S81-ROM-TEMPLATE: handoff 282 min old; last post 2026-11-24 05:37 DIED
- S81-SLICE-J9: handoff 511 min old; last post 2026-11-24 01:45 DONE
- S81-SVC-J9: handoff 917 min old; last post 2026-11-23 16:01 DONE
- S81-T2-REFLOOR: handoff 387 min old; last post 2026-11-24 06:42 READY
- S81-TYPES-CODEX-1123: handoff 865 min old; last post none in recent queue
- SEAT-MATCH-AUDIT: handoff 365 min old; last post 2026-11-24 04:14 DONE
- TAP-GRID-R6: handoff 918 min old; last post 2026-11-23 16:24 DONE

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 182; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 67 live
- QC-ALLFIX agent ? last post 2026-11-24 07:44 DONE
- LANEAGE-SWEEP agent ? last post 2026-11-24 07:44 DONE
- qwen_compute agent ? last post 2026-11-24 07:42 KIT-WAVE
- QC-OPEN-STA agent ? last post 2026-11-24 07:41 DONE
- LEC-AUTOFILL agent ? last post 2026-11-24 07:38 RESULT
- MERGE-QUEUE agent ? last post 2026-11-24 07:37 STATE
- ROM-WEIGHTS-1119 agent ? last post 2026-11-24 07:36 DIED
- S81-ALLFIX-INT agent ? last post 2026-11-24 07:35 ROW
- S81-KVLEAF-T2-ARCH-R2 agent ? last post 2026-11-24 07:31 DONE
- QC-FW-CAP agent ? last post 2026-11-24 07:31 RESULT
- FLEET-OPS-R agent ? last post 2026-11-24 07:31 ALERT
- NOPROG-WATCHDOG agent ? last post 2026-11-24 07:30 STATE
- KV-RSTREACH agent ? last post 2026-11-24 07:30 DIED
- RELEC-1122 agent ? last post 2026-11-24 07:27 RESULT
- S81-KV-CALENDAR agent ? last post 2026-11-24 07:26 RESULT
- QC-GENDRY-TRIAGE agent ? last post 2026-11-24 07:26 DIED
- KV-ALLFIX agent ? last post 2026-11-24 07:25 DONE
- BIND-ALL-ERRORS agent ? last post 2026-11-24 07:21 DONE
- LEC-VACUITY-SWEEP agent ? last post 2026-11-24 07:19 DONE
- CORE-TAP-BUDGET agent ? last post 2026-11-24 07:18 RESULT
- CBC-RULES-1119 agent ? last post 2026-11-24 07:17 HOURLY
- HEAD-WEST agent ? last post 2026-11-24 07:16 DONE
- OT-TOOLS-SYNC agent ? last post 2026-11-24 07:01 ALERT
- CODEX-TOKEN agent ? last post 2026-11-24 06:59 RESULT
- QC-OPEN-COLL agent ? last post 2026-11-24 06:55 RESULT
- NOPROG-FIX-1115 agent ? last post 2026-11-24 06:52 STATE
- QC-OPEN-SU agent ? last post 2026-11-24 06:48 RESULT
- HEAD-100 agent ? last post 2026-11-24 06:47 RESULT
- S81-T2-REFLOOR agent ? last post 2026-11-24 06:42 READY
- EVENT-ENV-PREFLIGHT agent ? last post 2026-11-24 06:41 WAVE-BRIDGE-GREEN
- s81_head agent ? last post 2026-11-24 06:40 KIT-WAVE
- s81 agent ? last post 2026-11-24 06:34 KIT-WAVE
- FLOW-OPS-R3 agent ? last post 2026-11-24 06:33 ITEM-SYNC-GREEN
- VIS-QC agent ? last post 2026-11-24 06:31 RESULT
- FAM-QC-HCST-R3 agent ? last post 2026-11-24 06:28 RESULT
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

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-24 07:45 PST)
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
  - type iqf__t1 · CANCELLED  STRUCT-STOP @ 2026-11-22 08:57 (46.8h) · owner FAIL-S81-1
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 383 commits / missing r708
- TOOLS-LAG qwen_kvsys 143 commits / missing r708
- TOOLS-LAG s81 3 commits / missing none
- TOOLS-LAG s81_head 326 commits / missing r708
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 3441 taps in 31 types, 126 over 1650 sinks; insertion max 696 ps (p50 267, p90 285), skew max 107 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 265 taps in 3 types, 10 over 1650 sinks; insertion max 512 ps (p50 272, p90 307), skew max 94 ps; oversized taps: ins max 370 ps, skew max 64 ps
- TAP-INSERTION s81: 5422 taps in 84 types, 259 over 1650 sinks; insertion max 1000 ps (p50 468, p90 498), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 168 taps in 5 types, 6 over 1650 sinks; insertion max 501 ps (p50 463, p90 478), skew max 71 ps; oversized taps: ins max 499 ps, skew max 65 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-24 07:05 | tolera L21.16/112 units0 free124G | key-ca L43.21/112 units187 free161G | dear-c L71.93/128 units428 free140G | loved- L115.53/96 units64 free315G | outgoi L29.31/96 units152 free60G | renewe L125.80/96 units78 free196G | civil- L85.88/96 units51 free31G | viable L129.91/96 units55 free3773G | HOST-CAPS 1 flagged: epyc7:LOAD_CAP_FACTOR=1.2:EXPIRED; expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (272.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (272.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (272.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (272.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (272.9 h left); epyc10:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 e
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  353G   92G  80% /
    07:45:19 up 31 days,  3:25, 172 users,  load average: 11.99, 11.39, 14.40

## ot-run status
    ot-run status: epyc2 admits 246 GB (avail 574, reserve 0, fresh 0, peak 177.1) load 117/128 run 48 threads 328/128 root 83% scratch 133 GB
    intel1 admits 295 GB (avail 726, reserve 0, fresh 0, peak 52.8) load 48/112 run 27 threads 284/112 root 34% scratch 103 GB
    localhost REFUSED (scratch disk /srv/opentallas-scratch2 has 109 GB free < floor 150 GB (the root fs is never a fallback; free the scratch disk, OT_RUN_SCRATCH_
    epyc7 admits 201 GB (avail 499, reserve 0, fresh 0, peak 50.6) load 114/96 waiters 7:258 GB oldest 0.0 h run 41 threads 413/96 root 51% scratch 274 GB
    epyc8 admits 520 GB (avail 839, reserve 0, fresh 0, peak 4) load 18/96 run 12 threads 202/96 root 46% scratch 59 GB DRAINING (59 of 90 GB, new job dirs refused)
    epyc9 admits 173 GB (avail 511, reserve 0, fresh 0, peak 148.6) load 129/96 waiters 8:196 GB oldest 0.1 h run 33 threads 315/96 LOADCAP root 54% scratch 173 GB
    epyc10 REFUSED (scratch disk /srv/opentallas-scratch has 0 GB free < floor 50 GB (the root fs is never a fallback; free the scratch disk, OT_RUN_SCRATCH_DISK_FL
    epyc11 admits 236 GB (avail 335, reserve 0, fresh 0, peak 45.4) load 116/96 waiters 32:1523 GB oldest 2.5 h run 52 threads 433/96 LOADCAP root 5% scratch 3673 G
    next 16-thread 32 GB job -> intel1
    ot-run status: BLOCKED 150 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-CB-PROBE/
    ot-run status: BLOCKED 148 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-CB-PROBE/
    ot-run status: BLOCKED 148 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-CB-PROBE/
    ot-run status: BLOCKED 82 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 80 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 70 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 69 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 62 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 61 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 60 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 60 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 60 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 60 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 54 min QC-CB-PROBE /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-
    ot-run status: BLOCKED 49 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 49 min KV-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pv_v4n_1
    ot-run status: BLOCKED 47 min KV-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_phy_1124
    ot-run status: BLOCKED 47 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 45 min KV-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pv_v2e_1
    ot-run status: BLOCKED 40 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL

## KIT-WAVE (autopilot log, last 6)
    2026-11-24 07:42:39 PST AUTOPILOT: KIT-WAVE HOLD-TERM s81: 372 hold(s), 0 without owner/eta (HOLD-NO-TERM), 368 overdue: col_h9_r0_p3__t1__cl0cd90c0e__* [owner FAM-S81-COL-H10-R4] eta 11-23 04:15; sli
    2026-11-24 07:42:39 PST AUTOPILOT: KIT-WAVE HOLD-AUDIT HELD-BUT-LAUNCHED=0 HOLD-LEAK=0 TERM-UNREACHABLE=0 TERM-VARIANT=0 HOLD-SUPERSEDED=0 HOLD-ZERO-MATCH=0 PROOF-HELD=0 PILOT-DEADLOCK=0
    2026-11-24 07:42:59 PST AUTOPILOT: UNDER-USE HELD SKIP-HELD 6: s81/serdes__t3 1 [owner VIS-S81-MISC, 42.8 h, eta 11-23 12:00, FLAGGED OVERDUE]; s81/serdes__t16 1 [owner VIS-S81-MISC, 42.5 h, eta 11-23
    2026-11-24 07:44:47 PST AUTOPILOT: KIT-WAVE AUTO-VIEWS overlay: hbm=21 qwen_compute=5 s81=3
    2026-11-24 07:44:48 PST AUTOPILOT: KIT-WAVE src_overlay: hbm unreadable on epyc10; hold compares without it
    2026-11-24 07:44:49 PST AUTOPILOT: KIT-WAVE HOLD-AUTO-RELEASE summary: 2 keys released by their terms, 0 new this pass

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-24 07:35 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2848065-1795534348 on tolerant-swine: rc=0 after 174 s, ended 07:35:13, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_fe_v1__clfe325744__cl08d14f0d_1124052348/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N4
- 2026-11-24 07:35 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2799335-1795534276 on tolerant-swine: rc=0 after 274 s, ended 07:35:42, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_st_a_v2__pv30dda31f__pvd2ec7769_1124052207/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9
- 2026-11-24 07:35 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2897141-1795534429 on tolerant-swine: rc=0 after 124 s, ended 07:35:45, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_su_l1__cla2a78701_1124052708/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/
- 2026-11-24 07:35 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2839917-1795534335 on tolerant-swine: rc=0 after 223 s, ended 07:35:49, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_fw_v2__cl8537f156_1124060343/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:36 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2744024-1795534190 on tolerant-swine: rc=0 after 389 s, ended 07:36:10, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631_1124052500/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen
- 2026-11-24 07:36 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2804464-1795534282 on tolerant-swine: rc=0 after 297 s, ended 07:36:11, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_stm_v3_1124053743/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:36 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2815195-1795534298 on tolerant-swine: rc=0 after 307 s, ended 07:36:37, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_b_v2__pvc2ec5bfb_1124055204/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priv
- 2026-11-24 07:36 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2285570-1795533530 on tolerant-swine: rc=0 after 1075 s, ended 07:36:37, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_a_v1__clfc5867a6__pvf82a6c28_1124052528/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R
- 2026-11-24 07:36 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2652697-1795534048 on tolerant-swine: rc=0 after 559 s, ended 07:36:38, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_fw_v1__clf58b4dfb_1124055935/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:36 PST DIED [ROM-WEIGHTS-1119] ot-run oth-ubuntu-4181526-1795523934 on civil-redfish: rc=1 after 10664 s, ended 15:36:37, log /srv/opentallas-scratch2/claude/romw-1119/logs/qcbatch_r0.log, cmd: --mem 24 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/romw-1119 -- bash /srv/opentallas-scratch2/claude/romw-1119/bin/qc | class=SETUP cause=FileNotFoundError: [Errno 2] No such file or dire
- 2026-11-24 07:36 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2571340-1795533941 on tolerant-swine: rc=0 after 6727 s, ended 07:36:42, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc2__cl6bcaba89_1124054339/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:36 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2903589-1795534439 on tolerant-swine: rc=0 after 172 s, ended 07:36:43, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_b_v2__pva66d0f22__pv3d7bec84_1124055114/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9
- 2026-11-24 07:36 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2864625-1795534371 on tolerant-swine: rc=0 after 240 s, ended 07:36:43, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_su_l1__cl5ea486db_1124052257/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/
- 2026-11-24 07:36 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2745475-1795534192 on tolerant-swine: rc=0 after 433 s, ended 07:36:57, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_st_a_v1__cl989804f6__cled3c1d7b_1124052117/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9
- 2026-11-24 07:37 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2935297-1795534483 on tolerant-swine: rc=0 after 160 s, ended 07:37:15, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_fw_v3_1124060522/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:37 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2934852-1795534482 on tolerant-swine: rc=0 after 164 s, ended 07:37:18, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_st_b_v1__pv0e7b1dcc_1124053323/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priv
- 2026-11-24 07:37 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2912100-1795534455 on tolerant-swine: rc=0 after 195 s, ended 07:37:21, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_a_v1__clb036e152_1124052437/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V
- 2026-11-24 07:37 PST DRIFT [MERGE-QUEUE -> COORD; cc ADMIT-TUNE-1, KIT-OPS-5] live tree differs from its recorded main sha (1 new): epyc11: rt/current 99c82ce69cab != hub 0510e1295005. Any live fix must land as a branch + COORD APPROVED; the merge queue lands it and ot-tools-sync deploys it.
- 2026-11-24 07:37 PST STATE [MERGE-QUEUE -> COORD] drift cleared: epyc11: manifest check failed ; epyc11: rt/current c66a01ee7285 != hub 99c82ce69cab
- 2026-11-24 07:37 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2969763-1795534533 on tolerant-swine: rc=0 after 126 s, ended 07:37:31, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_b_v1__cl6357f1cc__pvffd43fdc_1124055024/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q1
- 2026-11-24 07:37 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-3006739-1795534605 on tolerant-swine: rc=0 after 669 s, ended 07:37:32, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_coll_n_1124051914/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:37 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2568733-1795533937 on tolerant-swine: rc=0 after 732 s, ended 07:37:40, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_a_v2__clf4365a62_1124052618/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:37 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-2352894-1795525264 on tolerant-swine: rc=0 after 9409 s, ended 07:37:45, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_sle_st_a_v2__pv30dda31f__pvd2ec7769_1124041026/chain_a1.live.log, cmd: --mem 48 --threads 8 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q10
- 2026-11-24 07:37 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2997943-1795534591 on tolerant-swine: rc=0 after 692 s, ended 07:37:49, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_st_b_v2__cl14c98df5__pvcd986c42_1124053507/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q1
- 2026-11-24 07:38 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2913806-1795534457 on tolerant-swine: rc=0 after 235 s, ended 07:38:04, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_fw_v1__clf51c11d8__cl592e3d37_1124060254/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103
- 2026-11-24 07:38 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2945287-1795534496 on tolerant-swine: rc=0 after 198 s, ended 07:38:06, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_coll_ftm_1124051824/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:38 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2859325-1795534363 on tolerant-swine: rc=0 after 331 s, ended 07:38:06, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_native59_1124052050/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:38 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-3011441-1795534610 on tolerant-swine: rc=0 after 691 s, ended 07:38:08, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_hc2__clcc5e3e61_1124052907/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/pr
- 2026-11-24 07:38 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2920453-1795534465 on tolerant-swine: rc=0 after 236 s, ended 07:38:12, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_coll_ft__cla4a25d77_1124051733/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/pr
- 2026-11-24 07:38 PST RESULT [LEC-AUTOFILL -> COORD, RELEC-1122, S81] Old t40 4,943 points resolved to 11 extra routed feedthrough groups: 4,932 data states at stage N+1 versus staged gold stage N, and 11 terminal valid states. Every data bit raw transfer checked; inversion rejected. E2 ot-jobs/t40_terminal_1124. Existing hold stays. Full historical hd_mesh proof queued, with proved-only aliases and original hints; 
- 2026-11-24 07:38 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2996972-1795534588 on tolerant-swine: rc=0 after 129 s, ended 07:38:29, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_stm_v3_1124053743/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:38 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2715144-1795534156 on tolerant-swine: rc=0 after 1167 s, ended 07:38:30, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_hc1__cl7d360508__pv97423966_1124052728/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46
- 2026-11-24 07:38 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2828329-1795534319 on tolerant-swine: rc=0 after 1024 s, ended 07:38:49, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_sc_v1__cl115da35f_1124055524/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:38 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2943067-1795534493 on tolerant-swine: rc=0 after 246 s, ended 07:38:51, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_stm_v3_1124055343/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:38 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2996444-1795534587 on tolerant-swine: rc=0 after 157 s, ended 07:38:56, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631_1124052500/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wav
- 2026-11-24 07:39 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2983837-1795534558 on tolerant-swine: rc=0 after 195 s, ended 07:39:04, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_st_a_v2__pv30dda31f__pvd2ec7769_1124052207/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9
- 2026-11-24 07:39 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2829851-1795534321 on tolerant-swine: rc=0 after 435 s, ended 07:39:07, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_fw_v2__cl6740750e_1124060025/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/
- 2026-11-24 07:39 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2954029-1795534511 on tolerant-swine: rc=0 after 254 s, ended 07:39:16, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_coll_core_1124052302/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:39 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2941636-1795534491 on tolerant-swine: rc=0 after 273 s, ended 07:39:16, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc3__cld86a7ad4__pvfd488b8f_1124054611/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R
- 2026-11-24 07:39 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-3015207-1795534613 on tolerant-swine: rc=0 after 158 s, ended 07:39:23, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_b_v2__pvc2ec5bfb_1124055204/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V
- 2026-11-24 07:39 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2755654-1795534210 on tolerant-swine: rc=0 after 564 s, ended 07:39:25, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc2__cla3497502__cldc737267_1124054430/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R
- 2026-11-24 07:39 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-3021597-1795534619 on tolerant-swine: rc=0 after 155 s, ended 07:39:26, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_b_v2__pva66d0f22__pv3d7bec84_1124055114/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9
- 2026-11-24 07:39 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-3033299-1795534636 on tolerant-swine: rc=0 after 172 s, ended 07:39:59, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_st_a_v1__cl989804f6__cled3c1d7b_1124052117/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9
- 2026-11-24 07:40 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2483676-1795533798 on tolerant-swine: rc=0 after 1021 s, ended 07:40:11, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_st_a_v1__cl67389ecd_1124052027/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:40 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-2354233-1795525266 on tolerant-swine: rc=0 after 9577 s, ended 07:40:35, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_sle_st_a_v2__pv30dda31f__pv88773f93_1124040959/chain_a1.live.log, cmd: --mem 48 --threads 8 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q10
- 2026-11-24 07:40 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-3079389-1795534705 on tolerant-swine: rc=0 after 153 s, ended 07:40:49, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_native59_1124052050/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:41 PST DONE [QC-OPEN-STA] ot-run oth-ubuntu-2373186-1795525298 on tolerant-swine: rc=0 after 9582 s, ended 07:41:12, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-OPEN-STA/qwen_compute_sle_st_a_v2__pv4242de79_1124041052/chain_a1.live.log, cmd: --mem 48 --threads 8 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4
- 2026-11-24 07:41 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2902861-1795534438 on tolerant-swine: rc=0 after 444 s, ended 07:41:14, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_ctl__cla4f6f12f_1124055757/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:41 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-3039899-1795534649 on tolerant-swine: rc=0 after 839 s, ended 07:41:15, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc0__cl4f54b7a3__pvde134a90_1124054158/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R
- 2026-11-24 07:41 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-3128756-1795534762 on tolerant-swine: rc=0 after 125 s, ended 07:41:18, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_st_a_v2__pv30dda31f__pvd2ec7769_1124052207/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q1
- 2026-11-24 07:41 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-3072075-1795534692 on tolerant-swine: rc=0 after 195 s, ended 07:41:18, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_a_v2__clf4365a62_1124052618/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priv
- 2026-11-24 07:41 PST DONE [LANEAGE-SWEEP] ot-push-main otpush-viable-ram-1967842 on viable-ram: rc=0 after 245 s, ended 15:41:38, log /srv/opentallas-scratch2/claude/LANEAGE-SWEEP/tmp/codex-main-bind-receipts-e11.log, cmd: ot-push-main --no-test
- 2026-11-24 07:42 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-3137758-1795534774 on tolerant-swine: rc=0 after 165 s, ended 07:42:10, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_coll_core_1124052302/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:42 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-103): 2 event(s): sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59 route FAIL FLOW (route-make-fail: FAIL_route make exit 2: 4_1_cts.log: Error: cts.tcl, 91 basic_ios::clear: iostream error) job bc9b1a8bd98b; slw_fw_v2__cl8537f156 route FAIL FLOW (route-make-fail: FAIL_route make exit 2: 4_1_cts.log: Error: cts.tcl, 91 basic_ios::clear: ios
- 2026-11-24 07:42 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-2074770-1795533211 on tolerant-swine: rc=0 after 1757 s, ended 07:42:40, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_cbf_q00__cl1b5a6458_1124051551/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:42 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-3093514-1795534728 on tolerant-swine: rc=0 after 254 s, ended 07:42:53, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc2__cl6bcaba89_1124054339/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:43 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-3105346-1795534739 on tolerant-swine: rc=0 after 251 s, ended 07:43:01, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_fw_v3_1124060522/preflight_route.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:43 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-3199503-1795534854 on tolerant-swine: rc=0 after 146 s, ended 07:43:12, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_sc_v1__cl115da35f_1124055524/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:44 PST DONE [LANEAGE-SWEEP] ot-run oth-ubuntu-2770392-1795534241 on loved-redfish: rc=0 after 803 s, ended 15:43:59, log /srv/opentallas-scratch2/claude/LANEAGE-SWEEP/tmp/c1j-ttlane-probe/cf_t20/logical.otrun.log, cmd: --mem 12 --threads 4 --disk 1 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/LANEAGE-SWEEP/tmp/c1j-ttlane-probe/cf_t20 -- bash /srv/ope
- 2026-11-24 07:44 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-3228940-1795534896 on tolerant-swine: rc=0 after 161 s, ended 07:44:08, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_a_v2__clf4365a62_1124052618/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priv

