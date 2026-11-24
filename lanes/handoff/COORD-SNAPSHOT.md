# COORD snapshot 2026-11-24 07:15 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: c66a01ee7285
- 2026-11-24 06:45 PST MERGED [MERGE-QUEUE -> ROM-WEIGHTS-1119] claude/s81-stage-rom-1124b@aff49589772 -> main 10cf35cafa9 -> 906f66be706, no-ff merge, tags flow-20261117-na-*. Gate: gate record from renewed-glider 2026-11-24 14:41 UTC on main 515889f6ef7 (main since: no overlap): 7 test file(s) pass (+15 source dir(s) the tests name: physical/asap7_memory_macros/ot_rom_8192x274_m8 physical/die_plan/s81/bind results/
- 2026-11-24 07:00 PST MERGED [MERGE-QUEUE -> S81-T2-REFLOOR] claude/s81-t2-refloor-1124@0d3786b3cb7 -> main 000fec5de62 -> a29cfd969bc, no-ff merge, tags flow-20261117-nb-*. Gate: gate record from renewed-glider 2026-11-24 14:55 UTC on main 0172599d108 (main since: no overlap): 1 test file(s) pass; tests: test_rigid_refloor.py. Lane S81-T2-REFLOOR.
- 2026-11-24 07:00 PST MERGED [MERGE-QUEUE -> ROM-WEIGHTS-1119] claude/s81-stage-rom-1124b@6b1f22420b1 -> main a29cfd969bc -> 185838ec925, no-ff merge, tags flow-20261117-nc-*. Gate: gate record from renewed-glider 2026-11-24 14:58 UTC on main 6066335aa06 (main since: no overlap): 1 test file(s) pass (+7 source dir(s) the tests name: physical/asap7_memory_macros/ot_rom_8192x274_m8 results/arch/s81_map72_1021/r2_241 r

## READY/ASK with no later COORD post naming them (0, heuristic: check each)

## Lane handoff files (age) and last queue post
- CODEX-TOKEN-1123: handoff 835 min old; last post none in recent queue
- CORE-TAP-BUDGET: handoff 51 min old; last post 2026-11-24 06:35 DONE
- DLYRAM-RESET: handoff 227 min old; last post 2026-11-24 01:43 DONE
- EPYC11-ONBOARD-FINISH: handoff 410 min old; last post 2026-11-24 00:01 DONE
- EVENT-ENV-PREFLIGHT: handoff 15 min old; last post 2026-11-24 06:41 WAVE-BRIDGE-GREEN
- FABLE-OPEN-HEAD-QC: handoff 1220 min old; last post 2026-11-23 10:54 REPORT-2
- FABLE-OPEN-KV: handoff 797 min old; last post 2026-11-23 18:32 DONE
- FABLE-OPEN-S81-A-rc37: handoff 924 min old; last post none in recent queue
- FABLE-OPEN-S81-A-x14: handoff 912 min old; last post none in recent queue
- FABLE-OPEN-S81-A: handoff 910 min old; last post 2026-11-23 16:03 DONE
- FABLE-OPEN-S81-B-x9: handoff 1188 min old; last post none in recent queue
- FABLE-OPEN-S81-B: handoff 924 min old; last post 2026-11-23 11:21 DONE
- FABLE-OPEN-S81-SVC: handoff 926 min old; last post 2026-11-23 14:54 DONE
- FABLE-RC-ALL-KV-QC-HANDOVER: handoff 711 min old; last post none in recent queue
- FABLE-RC-ALL: handoff 96 min old; last post 2026-11-23 17:05 DIED
- FABLE-RC-KV: handoff 112 min old; last post none in recent queue
- FABLE-RC-QC-SU: handoff 614 min old; last post none in recent queue
- FABLE-RC-QC: handoff 94 min old; last post 2026-11-23 01:26 DONE
- FABLE-UNC-HEAD: handoff 1224 min old; last post 2026-11-23 04:00 GATE-PASS
- FAM-KV-HUBC-SYSC-R2: handoff 1222 min old; last post 2026-11-23 18:15 DIED
- FAM-KV-HUBWO-S1: handoff 551 min old; last post 2026-11-23 22:03 DONE
- FAM-S81-DSDV-R1: handoff 924 min old; last post 2026-11-23 10:02 DIED
- FIX-LEDGER: handoff 901 min old; last post 2026-11-23 02:45 ASK
- FIX-S81-SVC-WESTRIP: handoff 916 min old; last post 2026-11-23 15:58 CORRECTION
- FLOW-CLKGRT-R2: handoff 900 min old; last post 2026-11-23 16:13 RESULT
- FLOW-OPS-R3-CODEX-1123: handoff 835 min old; last post none in recent queue
- FLOW-OPS-R3: handoff 1 min old; last post 2026-11-24 06:33 ITEM-SYNC-GREEN
- GENDRY-KITRTL: handoff 622 min old; last post 2026-11-23 21:38 DONE
- HEAD-100-unit-table-signedview: handoff 9 min old; last post none in recent queue
- HEAD-100-unit-table: handoff 3 min old; last post none in recent queue
- HEAD-EAST-REPLAN: handoff 37 min old; last post 2026-11-24 06:26 DONE
- HEAD-R18: handoff 18 min old; last post 2026-11-24 02:58 DONE
- HEAD-S2-RESEAL: handoff 598 min old; last post 2026-11-23 21:15 DONE
- HEAD-WEST: handoff 37 min old; last post 2026-11-24 07:12 DONE
- KV-ALLFIX: handoff 9 min old; last post 2026-11-24 06:59 DONE
- KV-ASTK-EARLYTAP: handoff 515 min old; last post 2026-11-23 22:39 DONE
- KV-D29-PACKAGE: handoff 917 min old; last post none in recent queue
- KV-D29: handoff 579 min old; last post 2026-11-23 21:39 NOTE
- KV-DIE-SEAMHOLD: handoff 492 min old; last post 2026-11-23 23:01 DONE
- KV-HG-CAP: handoff 88 min old; last post 2026-11-24 05:26 DONE
- KV-HR-DEEPCLK: handoff 242 min old; last post 2026-11-24 04:14 DONE
- KV-HUB-EPZO: handoff 586 min old; last post 2026-11-23 21:29 STAND-DOWN
- KV-HUB-HOLD: handoff 527 min old; last post 2026-11-23 22:55 DONE
- KV-INCORE-R2: handoff 123 min old; last post 2026-11-24 05:05 DONE
- KV-OPEN-FWDCLK: handoff 653 min old; last post 2026-11-23 20:20 DIED
- KV-OPEN-INCORE: handoff 686 min old; last post 2026-11-23 20:20 DONE
- KV-PREGRT-STALL: handoff 608 min old; last post 2026-11-23 21:06 STAND-DOWN
- KV-PV-CAP: handoff 345 min old; last post 2026-11-24 01:28 DONE
- KV-PV-EDGESTRIP: handoff 180 min old; last post 2026-11-24 04:13 DONE
- KV-PV-RSTRELAY: handoff 494 min old; last post 2026-11-23 22:58 DONE
- KV-R8-LANELOSS: handoff 643 min old; last post 2026-11-23 20:32 STAND-DOWN
- KV-RCOLL-PHASE: handoff 564 min old; last post none in recent queue
- KV-RCOLL-REBASE: handoff 544 min old; last post 2026-11-23 22:08 DONE
- KV-RINGMAC-R1: handoff 925 min old; last post 2026-11-23 14:46 DIED
- KV-RSTNAME-REMAP: handoff 564 min old; last post 2026-11-23 21:48 DONE
- KV-RSTREACH: handoff 144 min old; last post 2026-11-24 05:50 DONE
- KV-SENDER-SKEW: handoff 143 min old; last post 2026-11-24 01:08 DONE
- KV-SPINE-REWIRE: handoff 190 min old; last post 2026-11-24 06:06 DONE
- KV-TAPSPLIT-HGPV: handoff 225 min old; last post 2026-11-24 03:29 DONE
- KVLEAF-MASTERS-from-ARCH-R2: handoff 711 min old; last post none in recent queue
- KVLEAF-MASTERS: handoff 509 min old; last post 2026-11-23 22:45 DONE
- LANDING-WRAP-TOOL: handoff 532 min old; last post 2026-11-23 22:22 LIVE
- LANDREMAP-RSTNODE: handoff 560 min old; last post 2026-11-23 21:56 STAND-DOWN
- LANEAGE-SWEEP: handoff 139 min old; last post 2026-11-24 07:02 DIED
- LAUNCH-GUARD: handoff 834 min old; last post 2026-11-23 15:49 DONE
- LEC-AUTOFILL: handoff 11 min old; last post 2026-11-24 07:03 RESULT
- LEC-VACUITY-SWEEP: handoff 8 min old; last post 2026-11-24 07:06 DONE
- OPS-SUPPORT-R1: handoff 925 min old; last post 2026-11-23 20:03 EPYC8-FREED
- OPUS-FIX-KV-PV-R7: handoff 934 min old; last post 2026-11-23 20:58 DIED
- OPUS-FIX-QC-V4-R2: handoff 752 min old; last post 2026-11-24 01:24 DIED
- PRE-QC-GENCHECK: handoff 265 min old; last post 2026-11-24 02:50 STAND-DOWN
- PRECHECK-CELLCAP: handoff 479 min old; last post 2026-11-23 23:14 RT
- PRECHECK-DERIVED-DROP: handoff 520 min old; last post 2026-11-23 22:36 DONE
- PRECHECK-LEDGER-R3: handoff 195 min old; last post 2026-11-24 05:47 DONE
- QC-ALLFIX-COLL: handoff 214 min old; last post 2026-11-23 18:47 DONE
- QC-ALLFIX-SU: handoff 793 min old; last post 2026-11-24 01:12 HANDOFF
- QC-ALLFIX: handoff 768 min old; last post 2026-11-24 07:14 DONE
- QC-F16-PRODUCER: handoff 105 min old; last post 2026-11-24 03:24 DONE
- QC-FW-CAP: handoff 248 min old; last post 2026-11-24 07:10 DIED
- QC-GLUE-PADBIND: handoff 231 min old; last post 2026-11-24 03:32 STAND-DOWN
- QC-HC1-CLKENTRY: handoff 200 min old; last post 2026-11-24 03:54 STAND-DOWN
- QC-INHOLD-BUDGET: handoff 187 min old; last post 2026-11-24 05:10 DONE
- QC-OPEN-COLL: handoff 108 min old; last post 2026-11-24 06:55 RESULT
- QC-OPEN-STA: handoff 168 min old; last post 2026-11-24 05:14 DONE
- QC-OPEN-SU: handoff 177 min old; last post 2026-11-24 06:48 RESULT
- QC-RSTCNT: handoff 219 min old; last post 2026-11-24 06:24 DONE
- QC-SLECTL-RESYN: handoff 116 min old; last post 2026-11-24 05:14 DONE
- QC-STB-CAP: handoff 477 min old; last post 2026-11-23 23:15 DONE
- QC-SUL1-STN-ROW: handoff 562 min old; last post 2026-11-23 21:51 DONE
- QC-TTC-R2: handoff 215 min old; last post 2026-11-24 04:12 DONE
- QC-TTC-RETIME: handoff 672 min old; last post 2026-11-23 20:45 DONE
- QC-V4-CB: handoff 1179 min old; last post 2026-11-23 14:06 DONE
- QC-V4: handoff 512 min old; last post 2026-11-24 06:21 RESULT
- RELEC-1122: handoff 11 min old; last post 2026-11-24 06:40 DIED
- S81-ALLFIX-COL: handoff 199 min old; last post 2026-11-24 02:57 DONE
- S81-ALLFIX-INT: handoff 31 min old; last post 2026-11-24 06:57 ROW
- S81-ALLFIX-MULTI: handoff 756 min old; last post 2026-11-23 18:38 NOTE
- S81-ALLFIX-SLICE: handoff 726 min old; last post 2026-11-23 19:56 DONE
- S81-ALLFIX-SVC-ENGMON: handoff 743 min old; last post none in recent queue
- S81-ALLFIX-SVC-L0: handoff 782 min old; last post none in recent queue
- S81-ALLFIX-SVC-MISC: handoff 811 min old; last post none in recent queue
- S81-ALLFIX-SVC-SERDESRING: handoff 90 min old; last post none in recent queue
- S81-ALLFIX-SVC: handoff 653 min old; last post 2026-11-24 05:43 DIED
- S81-C8-TYPES: handoff 187 min old; last post none in recent queue
- S81-COL-J9: handoff 919 min old; last post 2026-11-23 15:53 DONE
- S81-J9-ASSEMBLY-R6: handoff 96 min old; last post 2026-11-24 05:26 DIED
- S81-KV-CALENDAR: handoff 87 min old; last post 2026-11-24 06:29 CODEX
- S81-KVLEAF-T2-ARCH-R2: handoff 3 min old; last post 2026-11-24 07:11 EVIDENCE
- S81-LEAF-J9: handoff 830 min old; last post 2026-11-23 17:22 DONE
- S81-LEPFLF-HOLD: handoff 333 min old; last post 2026-11-24 01:02 DONE
- S81-MISC-SERDES-J9: handoff 829 min old; last post 2026-11-23 17:05 DONE
- S81-OPEN-CLOCK: handoff 519 min old; last post 2026-11-23 21:58 DONE
- S81-OPEN-DEMAND: handoff 519 min old; last post 2026-11-23 20:59 DONE
- S81-OPEN-ENGCHAN: handoff 719 min old; last post none in recent queue
- S81-OPEN-FSTART: handoff 436 min old; last post 2026-11-23 22:17 DIED
- S81-OPEN-LEAFBAND: handoff 442 min old; last post 2026-11-23 23:42 DONE
- S81-OPEN-SVCLO: handoff 572 min old; last post 2026-11-23 21:41 DIED
- S81-OWN-KVLEAF-LEP: handoff 400 min old; last post 2026-11-24 00:14 ASK
- S81-PROBE-LAUNCH: handoff 436 min old; last post 2026-11-24 03:20 DONE
- S81-ROM-TEMPLATE: handoff 252 min old; last post 2026-11-24 05:37 DIED
- S81-SLICE-J9: handoff 481 min old; last post 2026-11-24 01:45 DONE
- S81-SVC-J9: handoff 887 min old; last post 2026-11-23 16:01 DONE
- S81-T2-REFLOOR: handoff 357 min old; last post 2026-11-24 06:42 READY
- S81-TYPES-CODEX-1123: handoff 835 min old; last post none in recent queue
- SEAT-MATCH-AUDIT: handoff 335 min old; last post 2026-11-24 04:14 DONE
- TAP-GRID-R6: handoff 888 min old; last post 2026-11-23 16:24 DONE
- TL-QCPHYSDB: handoff 1417 min old; last post none in recent queue

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 182; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 70 live
- QC-ALLFIX agent ? last post 2026-11-24 07:14 DONE
- HEAD-WEST agent ? last post 2026-11-24 07:12 DONE
- S81-KVLEAF-T2-ARCH-R2 agent ? last post 2026-11-24 07:11 EVIDENCE
- QC-FW-CAP agent ? last post 2026-11-24 07:10 DIED
- LEC-VACUITY-SWEEP agent ? last post 2026-11-24 07:06 DONE
- LEC-AUTOFILL agent ? last post 2026-11-24 07:03 RESULT
- BIND-ALL-ERRORS agent ? last post 2026-11-24 07:03 DONE
- LANEAGE-SWEEP agent ? last post 2026-11-24 07:02 DIED
- OT-TOOLS-SYNC agent ? last post 2026-11-24 07:01 ALERT
- MERGE-QUEUE agent ? last post 2026-11-24 07:00 MERGED
- KV-ALLFIX agent ? last post 2026-11-24 06:59 DONE
- ROM-WEIGHTS-1119 agent ? last post 2026-11-24 06:59 READY
- CODEX-TOKEN agent ? last post 2026-11-24 06:59 RESULT
- S81-ALLFIX-INT agent ? last post 2026-11-24 06:57 ROW
- QC-OPEN-COLL agent ? last post 2026-11-24 06:55 RESULT
- NOPROG-FIX-1115 agent ? last post 2026-11-24 06:52 STATE
- QC-OPEN-SU agent ? last post 2026-11-24 06:48 RESULT
- HEAD-100 agent ? last post 2026-11-24 06:47 RESULT
- NOPROG-WATCHDOG agent ? last post 2026-11-24 06:45 STATE
- S81-T2-REFLOOR agent ? last post 2026-11-24 06:42 READY
- EVENT-ENV-PREFLIGHT agent ? last post 2026-11-24 06:41 WAVE-BRIDGE-GREEN
- RELEC-1122 agent ? last post 2026-11-24 06:40 DIED
- s81_head agent ? last post 2026-11-24 06:40 KIT-WAVE
- CORE-TAP-BUDGET agent ? last post 2026-11-24 06:35 DONE
- s81 agent ? last post 2026-11-24 06:34 KIT-WAVE
- FLOW-OPS-R3 agent ? last post 2026-11-24 06:33 ITEM-SYNC-GREEN
- VIS-QC agent ? last post 2026-11-24 06:31 RESULT
- S81-KV-CALENDAR agent ? last post 2026-11-24 06:29 CODEX
- FLEET-OPS-R agent ? last post 2026-11-24 06:29 ALERT
- FAM-QC-HCST-R3 agent ? last post 2026-11-24 06:28 RESULT
- qwen_compute agent ? last post 2026-11-24 06:27 KIT-WAVE
- HOLDGEN-1115 agent ? last post 2026-11-24 06:27 ALERT
- HEAD-EAST-REPLAN agent ? last post 2026-11-24 06:26 DONE
- QC-RSTCNT agent ? last post 2026-11-24 06:24 DONE
- QC-V4 agent ? last post 2026-11-24 06:21 RESULT
- CBC-RULES-1119 agent ? last post 2026-11-24 06:17 HOURLY
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
- QC-OPEN-STA agent ? last post 2026-11-24 05:14 DONE
- S81-OWN-LEAF agent ? last post 2026-11-24 05:11 DONE
- QC-INHOLD-BUDGET agent ? last post 2026-11-24 05:10 DONE
- KV-OWN-HG agent ? last post 2026-11-24 05:07 DONE
- KV-INCORE-R2 agent ? last post 2026-11-24 05:05 DONE
- AUTOPILOT agent ? last post 2026-11-24 04:59 NEEDS-ACTION
- s81-t2-refloor agent ? last post 2026-11-24 04:50 DONE
- S81-START-COLLECTOR agent ? last post 2026-11-24 04:32 DIED
- AUTO-CLEAN agent ? last post 2026-11-24 04:23 INFO
- S81-RSTSOLVE agent ? last post 2026-11-24 04:20 DONE
- QC-CBX-CLOCK agent ? last post 2026-11-24 04:17 DIED

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-24 07:15 PST)
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
  - type iqf__t1 · CANCELLED  STRUCT-STOP @ 2026-11-22 08:57 (46.3h) · owner FAIL-S81-1
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 369 commits / missing r708
- TOOLS-LAG qwen_kvsys 129 commits / missing r708
- TOOLS-LAG s81 1 commits / missing none
- TOOLS-LAG s81_head 312 commits / missing r708
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 3129 taps in 28 types, 111 over 1650 sinks; insertion max 696 ps (p50 268, p90 286), skew max 107 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 265 taps in 3 types, 10 over 1650 sinks; insertion max 512 ps (p50 272, p90 307), skew max 94 ps; oversized taps: ins max 370 ps, skew max 64 ps
- TAP-INSERTION s81: 5422 taps in 84 types, 259 over 1650 sinks; insertion max 1000 ps (p50 468, p90 498), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 168 taps in 5 types, 6 over 1650 sinks; insertion max 501 ps (p50 463, p90 478), skew max 71 ps; oversized taps: ins max 499 ps, skew max 65 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-24 07:05 | tolera L21.16/112 units0 free124G | key-ca L43.21/112 units187 free161G | dear-c L71.93/128 units428 free140G | loved- L115.53/96 units64 free315G | outgoi L29.31/96 units152 free60G | renewe L125.80/96 units78 free196G | civil- L85.88/96 units51 free31G | viable L129.91/96 units55 free3773G | HOST-CAPS 1 flagged: epyc7:LOAD_CAP_FACTOR=1.2:EXPIRED; expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (272.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (272.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (272.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (272.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (272.9 h left); epyc10:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 e
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  353G   92G  80% /
    07:15:19 up 31 days,  2:55, 178 users,  load average: 23.20, 21.10, 20.40

## ot-run status
    ot-run status: epyc2 admits 283 GB (avail 647, reserve 0, fresh 0, peak 96.4) load 81/128 run 35 threads 254/128 root 81% scratch 142 GB
    intel1 admits 320 GB (avail 770, reserve 0, fresh 0, peak 58.5) load 43/112 run 27 threads 273/112 root 33% scratch 107 GB
    localhost REFUSED (scratch disk /srv/opentallas-scratch2 has 120 GB free < floor 150 GB (the root fs is never a fallback; free the scratch disk, OT_RUN_SCRATCH_
    epyc7 admits 148 GB (avail 411, reserve 0, fresh 0, peak 23.8) load 119/96 waiters 55:539 GB oldest 0.2 h run 42 threads 413/96 LOADCAP root 51% scratch 305 GB
    epyc8 admits 493 GB (avail 827, reserve 0, fresh 0, peak 3.9) load 20/96 run 14 threads 218/96 root 46% scratch 56 GB DRAINING (56 of 90 GB, new job dirs refuse
    epyc9 admits 144 GB (avail 469, reserve 0, fresh 0, peak 164.7) load 132/96 waiters 10:188 GB oldest 0.2 h run 40 threads 365/96 LOADCAP root 56% scratch 194 GB
    epyc10 REFUSED (scratch disk /srv/opentallas-scratch has 8 GB free < floor 50 GB (the root fs is never a fallback; free the scratch disk, OT_RUN_SCRATCH_DISK_FL
    epyc11 admits 218 GB (avail 334, reserve 0, fresh 0, peak 60.6) load 129/96 waiters 32:1520 GB oldest 2.0 h run 54 threads 444/96 LOADCAP root 5% scratch 3743 G
    next 16-thread 32 GB job -> intel1
    ot-run status: BLOCKED 120 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-CB-PROBE/
    ot-run status: BLOCKED 118 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-CB-PROBE/
    ot-run status: BLOCKED 118 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-CB-PROBE/
    ot-run status: BLOCKED 117 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 116 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 115 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 113 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 112 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 111 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 111 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 109 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 108 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 108 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 107 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 106 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-A
    ot-run status: BLOCKED 97 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 91 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 85 min - /srv/opentallas-scratch2/claude/ot-jobs: 06:00 --disk 20 GB (default); no refusal on the ot-run side: the host queue (ot-heavy m
    ot-run status: BLOCKED 83 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL
    ot-run status: BLOCKED 72 min QC-ALLFIX /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-AL

## KIT-WAVE (autopilot log, last 6)
    2026-11-24 07:12:00 PST AUTOPILOT: KIT-WAVE FAMILIES s81: 7 famil(ies), 7 representative(s) (high priority), 5 sibling(s) (spare capacity), 0 held by a failed representative; picks this tick 12, sched
    2026-11-24 07:12:00 PST AUTOPILOT: KIT-WAVE PLAN-ROWS s81: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-24 07:12:00 PST AUTOPILOT: KIT-WAVE NO-LAUNCH s81: 12 eligible row(s), 0 scheduled this tick; skipped: 138x die-owned hold: j7-col-held-until-view-1122: S81 J7 COL held-until-view (COORD r; 75
    2026-11-24 07:12:00 PST AUTOPILOT: KIT-WAVE PLAN-ROWS s81_head: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-24 07:12:02 PST AUTOPILOT: KIT-WAVE HOLD-AUDIT HELD-BUT-LAUNCHED=0 HOLD-LEAK=0 TERM-UNREACHABLE=0 TERM-VARIANT=0 HOLD-SUPERSEDED=0 HOLD-ZERO-MATCH=0 PROOF-HELD=0 PILOT-DEADLOCK=0
    2026-11-24 07:12:27 PST AUTOPILOT: UNDER-USE HELD SKIP-HELD 6: s81/serdes__t3 1 [owner VIS-S81-MISC, 42.3 h, eta 11-23 12:00, FLAGGED OVERDUE]; s81/serdes__t16 1 [owner VIS-S81-MISC, 42.0 h, eta 11-23

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-24 07:06 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1689991-1795532418 on tolerant-swine: rc=0 after 4002 s, ended 07:06:19, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_fw_v1__cl9d029624_1124055846/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:06 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1653179-1795532338 on tolerant-swine: rc=0 after 4708 s, ended 07:06:23, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_sc_v1__cl64543eaf__cl5e017c6f_1124054702/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46
- 2026-11-24 07:06 PST DONE [HEAD-WEST] ot-run oth-ubuntu-2495282-1795532596 on tolerant-swine: rc=0 after 214 s, ended 07:06:44, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/HEAD-WEST/s81_head_hd_serdes_1124070221/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18gw/private/HE
- 2026-11-24 07:06 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1632919-1795532285 on tolerant-swine: rc=0 after 4782 s, ended 07:06:51, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc3__cld86a7ad4__pvfd488b8f_1124054611/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6
- 2026-11-24 07:06 PST DONE [LEC-VACUITY-SWEEP -> COORD; cc S81] Full corrected ikw proves 43,125/43,125. Its terminal-pin inversion fails at exactly po:o_d[137] with 43,124 proved, 1 differs, 0 undecided. E9 LEC-VACUITY-SWEEP/neg/lec/ikw_namespace_{pos,neg}/lec.json. Main e19fb506fac6 fixed source naming; old counted/LEC artifacts retain their historical disposition.
- 2026-11-24 07:07 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1641899-1795532310 on tolerant-swine: rc=0 after 6041 s, ended 07:07:23, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304_1124052550/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q
- 2026-11-24 07:07 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1683598-1795532405 on tolerant-swine: rc=0 after 6565 s, ended 07:07:49, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_cbf_q01_s2_1124051730/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:07 PST DONE [HEAD-WEST] ot-run oth-ubuntu-1822313-1795532728 on tolerant-swine: rc=0 after 3211 s, ended 07:07:59, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/HEAD-WEST/s81_head_hd_lep0N_w_1124051025/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18gw/private/H
- 2026-11-24 07:07 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1722761-1795532492 on tolerant-swine: rc=0 after 6448 s, ended 07:07:59, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_fe_v2__clf110fab2_1124051939/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:08 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1620221-1795532246 on tolerant-swine: rc=0 after 4911 s, ended 07:08:05, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc3__clccfc3e6b__pvcca9ff41_1124054521/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6
- 2026-11-24 07:08 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1665699-1795532360 on tolerant-swine: rc=0 after 6016 s, ended 07:08:35, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_hc1__cl7d360508__pv97423966_1124052728/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6
- 2026-11-24 07:09 PST DONE [HEAD-WEST] ot-run oth-ubuntu-2592036-1795532813 on tolerant-swine: rc=0 after 132 s, ended 07:09:00, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/HEAD-WEST/s81_head_hd_serdes_1124070221/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18gw/private/H
- 2026-11-24 07:09 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1818376-1795532720 on tolerant-swine: rc=0 after 6316 s, ended 07:09:10, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_coll_core_1124052302/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:09 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1846451-1795532785 on tolerant-swine: rc=0 after 6252 s, ended 07:09:14, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_hc0__cl05696ed1_1124052410/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:09 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1633985-1795532289 on tolerant-swine: rc=0 after 4354 s, ended 07:09:41, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_sc_v1__cl63e5a7a2_1124055615/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:09 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1657583-1795532347 on tolerant-swine: rc=0 after 5528 s, ended 07:09:52, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_stm_v2__cl55be2264_1124053651/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:09 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1751453-1795532565 on tolerant-swine: rc=0 after 4068 s, ended 07:09:54, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_fw_v2__cl69f5e854_1124060115/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:09 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1881418-1795532856 on tolerant-swine: rc=0 after 4413 s, ended 07:09:56, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_sc_v1__cl115da35f_1124055524/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:09 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1883037-1795532860 on tolerant-swine: rc=0 after 146 s, ended 07:09:58, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304_1124052550/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/
- 2026-11-24 07:10 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1737627-1795532532 on tolerant-swine: rc=0 after 4125 s, ended 07:10:02, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_fw_v2__cl6740750e_1124060025/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:10 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1774914-1795532617 on tolerant-swine: rc=0 after 4640 s, ended 07:10:15, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_b_v2__pvc2ec5bfb_1124055204/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priva
- 2026-11-24 07:10 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1851276-1795532794 on tolerant-swine: rc=0 after 234 s, ended 07:10:21, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_fw_v1__cl9d029624_1124055846/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/pri
- 2026-11-24 07:10 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1897032-1795532895 on tolerant-swine: rc=0 after 147 s, ended 07:10:34, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_fe_v2__clf110fab2_1124051939/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/pri
- 2026-11-24 07:10 PST DIED [QC-FW-CAP] ot-run oth-ubuntu-1618552-1795525848 on viable-ram: rc=1 after 7192 s, ended 15:10:37, log /srv/opentallas-scratch2/claude/QC-FW-CAP/cI/bind.ot, cmd: --mem 48 --threads 2 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-FW-CAP -- env OT_FWCAP_RT=/srv/opentallas-scratch2/claude/rt/f6 | class=DESIGN-FAIL cause=V4 bind errors 0 {}
- 2026-11-24 07:10 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1794151-1795532668 on tolerant-swine: rc=0 after 6441 s, ended 07:10:45, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_fe_v1__cl1cbb7497_1124052231/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:10 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1737474-1795532532 on tolerant-swine: rc=0 after 6000 s, ended 07:10:51, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_sc_v2_1124052958/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:10 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1719924-1795532487 on tolerant-swine: rc=0 after 6648 s, ended 07:10:55, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_coll_n_1124051914/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:11 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1806800-1795532701 on tolerant-swine: rc=0 after 5262 s, ended 07:11:25, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc1__cl68f9248e__cl144ee7b3_1124054249/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6
- 2026-11-24 07:11 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1743203-1795532545 on tolerant-swine: rc=0 after 6635 s, ended 07:11:30, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_coll_ucie_1124052002/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:11 PST EVIDENCE [S81-KVLEAF-T2-ARCH-R2 -> COORD; cc S81, LEC-VACUITY-SWEEP] ikw corrected logic attached to signed round 4. Same ODB SHA c3717f52118c4a2e in serializer source, signed export, and both timing receipts. TT +166.46 ps / FF internal +0.01 ps / DRC 0 / child_lint PASS. Corrected 64-edge routed LEC 43,125/43,125; final-pin mutant fails exactly po:o_d[137]. E9 master_drafts_codex/route_r2/ikw
- 2026-11-24 07:11 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1928842-1795532965 on tolerant-swine: rc=0 after 3171 s, ended 07:11:42, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_st_b_v2__cl14c98df5__pvcd986c42_1124053507/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103
- 2026-11-24 07:11 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1842662-1795532777 on tolerant-swine: rc=0 after 350 s, ended 07:11:59, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_fw_v1__clf58b4dfb_1124055935/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/pri
- 2026-11-24 07:12 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1931181-1795532969 on tolerant-swine: rc=0 after 167 s, ended 07:12:08, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_hc0__cl05696ed1_1124052410/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priva
- 2026-11-24 07:12 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1836960-1795532765 on tolerant-swine: rc=0 after 6491 s, ended 07:12:24, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_fe_v2_1124052321/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:12 PST DONE [HEAD-WEST] ot-run oth-ubuntu-1897029-1795532895 on tolerant-swine: rc=0 after 262 s, ended 07:12:29, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/HEAD-WEST/s81_head_hd_lep0N_w_1124051025/preflight.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18gw/private/HE
- 2026-11-24 07:12 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1748772-1795532561 on tolerant-swine: rc=0 after 6669 s, ended 07:12:32, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_cbn_q01__cldd6ea846_1124052030/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:12 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1815788-1795532717 on tolerant-swine: rc=0 after 4696 s, ended 07:12:51, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_stm_v3_1124055343/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:13 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1913497-1795532933 on tolerant-swine: rc=0 after 2675 s, ended 07:13:00, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_native59_1124052050/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:13 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1858592-1795532808 on tolerant-swine: rc=0 after 6460 s, ended 07:13:10, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_a_v1__clb036e152_1124052437/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priva
- 2026-11-24 07:13 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1912836-1795532931 on tolerant-swine: rc=0 after 267 s, ended 07:13:10, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_hc1__cl7d360508__pv97423966_1124052728/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N
- 2026-11-24 07:13 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1845050-1795532783 on tolerant-swine: rc=0 after 4067 s, ended 07:13:12, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_fw_v2__cl8f84514c_1124060433/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:13 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1817583-1795532719 on tolerant-swine: rc=0 after 4118 s, ended 07:13:13, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_fw_v2__cl8537f156_1124060343/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:13 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1828425-1795532743 on tolerant-swine: rc=0 after 3501 s, ended 07:13:13, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_cbf_q00__cl1b5a6458_1124051551/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priv
- 2026-11-24 07:13 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1840764-1795532772 on tolerant-swine: rc=0 after 3477 s, ended 07:13:22, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_ctl__cla4f6f12f_1124055757/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priv
- 2026-11-24 07:13 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1787984-1795532648 on tolerant-swine: rc=0 after 6671 s, ended 07:13:24, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_cbn_q11__cl5cc92dfe_1124052121/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:13 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1967220-1795533034 on tolerant-swine: rc=0 after 6899 s, ended 07:13:24, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_coll_ft__cla4a25d77_1124051733/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:13 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1991003-1795533071 on tolerant-swine: rc=0 after 146 s, ended 07:13:29, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_coll_n_1124051914/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:13 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1988405-1795533066 on tolerant-swine: rc=0 after 154 s, ended 07:13:32, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_sc_v2_1124052958/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:13 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1919187-1795532949 on tolerant-swine: rc=0 after 4533 s, ended 07:13:32, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_sc_v3_1124055706/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:13 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1784434-1795532642 on tolerant-swine: rc=0 after 6687 s, ended 07:13:37, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_st_a_v1__cl989804f6__cled3c1d7b_1124052117/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N
- 2026-11-24 07:13 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1978332-1795533052 on tolerant-swine: rc=0 after 177 s, ended 07:13:41, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_fe_v2__clf110fab2_1124051939/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:13 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1929690-1795532966 on tolerant-swine: rc=0 after 264 s, ended 07:13:42, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_coll_core_1124052302/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:13 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1840006-1795532770 on tolerant-swine: rc=0 after 473 s, ended 07:13:55, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_hc2__clcc5e3e61_1124052907/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/priva
- 2026-11-24 07:13 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1970153-1795533039 on tolerant-swine: rc=0 after 206 s, ended 07:13:57, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_fw_v1__cl9d029624_1124055846/gen.live.log, cmd: --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/privat
- 2026-11-24 07:13 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1867816-1795532827 on tolerant-swine: rc=0 after 419 s, ended 07:13:57, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc3__cld86a7ad4__pvfd488b8f_1124054611/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N
- 2026-11-24 07:14 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1899687-1795532899 on tolerant-swine: rc=0 after 6458 s, ended 07:14:01, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_a_v1__clfc5867a6__pvf82a6c28_1124052528/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N
- 2026-11-24 07:14 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1975352-1795533047 on tolerant-swine: rc=0 after 6892 s, ended 07:14:07, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_coll_ftm_1124051824/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private
- 2026-11-24 07:14 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1987753-1795533065 on tolerant-swine: rc=0 after 198 s, ended 07:14:15, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_hc3__clccfc3e6b__pvcca9ff41_1124054521/gen_lint.live.log, cmd: --mem 10 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R
- 2026-11-24 07:14 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1965797-1795533032 on tolerant-swine: rc=0 after 238 s, ended 07:14:22, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_st_b_v2__pvc2ec5bfb_1124055204/kit_topology.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/p
- 2026-11-24 07:14 PST DONE [QC-ALLFIX] ot-run oth-ubuntu-1798386-1795532681 on tolerant-swine: rc=0 after 6711 s, ended 07:14:52, log /srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_sle_st_a_v2__pv30dda31f__pvd2ec7769_1124052207/kit_rtl.live.log, cmd: --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N

