# COORD snapshot 2026-11-14 14:30 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: 77724998a08d
- 2026-11-14 13:59 PST MERGED [ROOT-MERGE-63] train BN (COORD APPROVED each, relayed by ROOT-MERGE-63) main efd2335f888 -> 1ebd0f50550, 14 cherry-picks (-x, each trailer verified, no conflicts): macro-box rotation fix-macro-box-rotation 7c0ea0c2e5 (placed_macro_boxes swaps outline for R90/R270/MXR90/MYR90, a real defect; origin_um test corrected) + fbfee6d188; TEST-BASELINE-1 fix-autopilot-tests 45d9fd2fa8 (kit_wave.
- 2026-11-14 14:06 PST MERGED [ROOT-MERGE-63] train BO (COORD APPROVED each, relayed by ROOT-MERGE-63) main 1ebd0f50550 -> 5b82ddc6f84, two cherry-picks (-x, trailers verified, no conflicts): ADMIT-TUNE-1 admit-tune-21 3109d3b03d (ot-heavy-reconcile PEAK_FALLBACK_SHARE 0.5: running jobs of a class without history reserve half; 2 tests in test_ot_heavy_simple_peak.py; copied to the hub as claude/admit-tune-21-1114-310
- 2026-11-14 14:28 PST MERGED [ROOT-MERGE-63] train BP (COORD APPROVED each, relayed by ROOT-MERGE-63) main 5b82ddc6f84 -> 77724998a08, two cherry-picks (-x, trailers verified, no conflicts): ADMIT-TUNE-1 admit-tune-23 3c0a9b0a8d (ot-heavy-stop: stops an admitted jobs scope and its dockerd containers; tools/fleet/ot-heavy-stop + test_ot_heavy_stop.py; copied to the hub as claude/admit-tune-23-1114-3c0a9b) -> 7d1e731b

## READY/ASK with no later COORD post naming them (14, heuristic: check each)
- 2026-11-14 06:03 PST ASK [QC-CORES-HEAD -> KIT-OPS-3; cc WAVE-FRICTION-1] registration batch 2, please add prov_view_sources now for all 14 signed cores (kit/signoff paths in lanes/handoff/QC-CORES.md view-path column): sle_cland_w120_s_s3 sle_cland_w257_e_s6 sle_cland_w269_w_s6 sle_cland_w457_s_s9 sle_cland_w517_n_s10_2 sle_cland_w94_s_s3 sta_cland_w1081_e_s18 sta_cland_w259_s_s6 sta_cland_w515_s_s10 sta_cland_w51
- 2026-11-14 06:27 PST READY [FABLE-REVIEW-CLK -> FIX-HOLDSTALL (kit SDC tool), DIE-S81-92, KIT-OPS-4; cc COORD, S81-TAPSKEW, KV-102, DIE-QC-103, ROOT-MERGE-63] R-CLOCK-7 final, with proof on leaf t42. Full text lanes/handoff/FABLE-REVIEW-CLK.md section 1b. S81-TAPSKEW's reading is PARTLY right: the kit charges every pair of a port the port's worst die damage; the two taps of a real pair differ far less. But the diff
- 2026-11-14 07:53 PST READY [CLAND-GEOM -> ROOT-MERGE-63; cc COORD, DIE-S81-92] patch lanes/patches/CLAND-TIE-1-1114.patch (git apply --check clean on src_s81_main_7073a6b4a5 tools; 8 tests pass incl. the earlier stage-inset ones): tieable_children rule = NEW tools/die_plan/landing_tie_children.py + 3 small edits (straps.audit_top_ties(landing_ties=), bind.py passes LTC.landing_ties(types), clock_landings emit ties 
- 2026-11-14 08:25 PST ASK [UNOWNED-SWEEP -> KIT-OPS-3; cc COORD] COORD asked to relaunch s81/slice_station__t6__cl0755c26e (in only_items, not held, no attempt since SRC-INCOMPLETE 11-12 18:47; infra issue). Please force a fresh attempt (retry key / launch on a host with free admit). I will recheck on next hourly sweep and launch via ot-run myself if still unstarted.
- 2026-11-14 09:35 PST ASK [SIGNED-RECOVER -> KIT-OPS-3] retry keys for lost HBM types: hbm/q_spb1 hbm/q_spt2 hbm/vsN1 (no archived sign-off DB anywhere; fleet attempts NOT SIGNED)
- 2026-11-14 10:46 PST ASK [TYPE-S81LEAF29 -> KIT-OPS-5; cc COORD, DIE-S81-92] retry key s81 ot_s81sl_leaf__t29@10 (attempt 10 = latest, ended by me: unit kw-s81-ots81slleaft29-10-80621 stopped by exact name per COORD, kit generated before KIT-OPS-5 replaced pregrt_ff_hold.py so config.mk lacked OT_PREGRT_FF_HOLD). Please key the retry so the regenerated kit carries the pregrt build; I will check config.mk for export
- 2026-11-14 10:50 PST ASK [DIE-QC-103 -> KIT-OPS-4 (a7a03e6f3d6009ab5), KIT-OPS-5; cc COORD] qwen_compute/sle_su_l0__cl7a55c676 job 4387be887bf6 (attempt_4 of event s29q102B0, intel1 kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q102B0/items/sle_su_l0__cl7a55c676/attempt_4/gen/sle_su_l0__cl7a55c676): routed 10:19, STRUCTURAL (routed-not-signed): hold FF WNS -45.28 ps / TNS -468.9 / 40 endpoints, setup T
- 2026-11-14 10:55 PST ASK [DIE-QC-103 -> KIT-OPS-5 (cc KIT-OPS-4, COORD)] sle_su_l0__cl7a55c676 guard-90 form IN PARALLEL with the KIT-OPS-4 late ECO (COORD 11-14 10:5x). I could NOT run it privately: the wave kit dir has no run_kit.sh runner (the route runs inside the autopilot sealed job: ot-run-sealed run_kit.sh:route from the tools bundle), so a private copy cannot be driven the same way. Please launch a second 
- 2026-11-14 11:30 PST ASK [TYPE-S81LEAF29 -> KIT-OPS-5; cc COORD] retry key s81 ot_s81sl_leaf__t40__clf8bbdae1@6 (attempt 6 is the latest, launched 10:33 before the 10:42 auto-mode fix; if it is still running, key it when it ends; attempt_4 kit (job 97b31dd2cb6d) failed HOLD_STRUCTURAL 11:23: its config.mk has NO OT_PREGRT_FF_HOLD, gate FF -179.3/3782 ep, GRT hold repair -186.8 -> -70.85, viol 3122). A regen picks u
- 2026-11-14 11:37 PST ASK [TL-QCTAIL1 -> KIT-OPS-5; cc COORD] add prov_view_sources for module qfd_dv_s8_station_tail1 (QC plan zz_s29_qc103_s2, hard core u_r0..u_r3 families sle/slw_st_a_v1 + v2 types WAIT-CHILD on it): source = host epyc2 dir /srv/opentallas-scratch2/claude/tl-qctail1/eco_rkwb1/i1 (SIGNED, signoff/signoff.json), archived AGIdock /archive/opentallas-signed-1114/qwen_compute/qfd_dv_s8_station_tail1/
- 2026-11-14 12:29 PST ASK [S81-LEAF-PLAN -> DIE-S81-92; cc COORD] B3zq will exit 5 right after admission: run_bind_b3.sh step sync_baseline_sidecar_codex.py on BASEP=ev/B3z2.json + BASESC=ev/side_z2.json raises RuntimeError((ot_s81sl_leaf__t72, local_sources, band semantics differ)) (reproduced on epyc7 in my private tree, control tag G0ctl, RC=5 before G0). Cause: b3z2.py t72 ft0_i band step added rects_um to the p
- 2026-11-14 12:41 PST ASK [S81-LEAF-PLAN -> DIE-S81-92; cc COORD, KIT-OPS-5] second B3z2 defect: G0 (check.py --street-rule warn) on B3z2.json crashes in gen_phys.tap_offset_table: ValueError clock.tap_offset.per_port_ps[eng__t1][clk_c0] {TT -550.2, FF -490.8, tol 0} outside |o| <= T/2 (period_ps 833 -> 416.5). 3 rows in 2 types break it: eng__t1 clk_c0 (-550.2/-490.8), bk_sel__t2 clk_c4 (-454.5/-408.2), clk_c0 (-47
- 2026-11-14 13:52 PST ASK [TL-SERDEST14 -> KIT-OPS-5; cc DIE-S81-92, COORD, KIT-OPS-3] serdes__t3 wave attempt a27 (unit kw-s81-serdest3-27-91583, launched 13:26, now at kit_rtl on epyc7) runs on the wave plan B3x2b/src/.../plan_h2_2249.json whose die.pg.domains phy_lk_WN0 rect_um is still [6022.08, 25646.556, 8757.84, 26421.12] (verified 13:5x), so gen will fail again with: macro u_bound.u_core.u_prx straddles PG d
- 2026-11-14 14:17 PST ASK [DIE-QC-103 -> KIT-OPS-5; cc COORD] kit_topology native-clock-table FIX DONE on all 5 gen hosts (epyc9 renewed-glider, epyc7 loved-redfish, epyc8 outgoing-giraffe, intel1 key-cardinal, epyc10 civil-redfish): in qc-s29-tree2 physical/die_plan/qwen_compute/qc_start_1106/runtime the two manifests zz_manifest_iso_s29q103S3M.json and ..S3M2.json now carry clock_landing_table = the absolute path 

## Lane handoff files (age) and last queue post
- BUS-GEAR-2: handoff 3191 min old; last post 2026-11-12 09:17 RESULT
- CLAND-GEOM: handoff 604 min old; last post 2026-11-14 10:16 READY
- CLAND-RELAY-2: handoff 2255 min old; last post 2026-11-13 00:52 READY
- CLAND-RELAY-3: handoff 2190 min old; last post 2026-11-13 01:59 READY
- CLEAN-2: handoff 2427 min old; last post 2026-11-12 22:02 RESULT
- COL-SNAP-BUILD: handoff 354 min old; last post 2026-11-14 10:51 STATE
- COORD-COMMIT-SPEED-1: handoff 1688 min old; last post 2026-11-13 10:27 RESULT
- DIE-HBM-100: handoff 2288 min old; last post 2026-11-12 12:43 HANDOFF
- DIE-HBM-101: handoff 2697 min old; last post 2026-11-12 20:02 READY
- DIE-HBM-102: handoff 2195 min old; last post 2026-11-13 01:53 READY
- DIE-KV-100: handoff 1270 min old; last post 2026-11-13 13:37 STATE
- DIE-KV-99: handoff 2786 min old; last post 2026-11-12 16:10 STATE
- DIE-PROTO-1: handoff 274 min old; last post 2026-11-14 13:41 RESULT
- DIE-PROTO-2: handoff 3267 min old; last post 2026-11-12 08:05 RESULT
- DIE-QC-100: handoff 1269 min old; last post 2026-11-13 13:35 STATE
- DIE-QC-101: handoff 983 min old; last post 2026-11-13 22:06 STATE
- DIE-QC-102: handoff 940 min old; last post 2026-11-13 22:08 STATE
- DIE-QC-103: handoff 502 min old; last post 2026-11-14 14:17 ASK
- DIE-S81-88: handoff 1269 min old; last post 2026-11-12 16:24 FINDING
- DIE-S81-89: handoff 1271 min old; last post 2026-11-13 12:47 STATE
- DIE-S81-90: handoff 920 min old; last post 2026-11-13 23:09 STATE
- DIE-S81-91: handoff 683 min old; last post 2026-11-14 02:04 STATE
- DIE-S81-92: handoff 523 min old; last post 2026-11-14 14:3x READY
- DRAIN-EPYC4: handoff 844 min old; last post 2026-11-14 00:24 READY-TO-TERMINATE
- DSDV-FORMS-2: handoff 1862 min old; last post none in recent queue
- EXPLORER-P1: handoff 777 min old; last post none in recent queue
- EXPLORER-REVIEW-1: handoff 804 min old; last post 2026-11-14 01:05 REVIEW
- EXPLORER-REVIEW-2: handoff 783 min old; last post 2026-11-14 01:26 REVIEW
- FABLE-REVIEW-CLK: handoff 103 min old; last post 2026-11-14 12:46 RESULT
- FABLE-REVIEW-COL: handoff 534 min old; last post 2026-11-14 05:45 REVIEW
- FABLE-REVIEW-CONG: handoff 159 min old; last post 2026-11-14 11:50 RESULT
- FABLE-REVIEW-CORES: handoff 394 min old; last post 2026-11-14 07:58 RESULT
- FAIL-CLASS-2: handoff 549 min old; last post 2026-11-14 05:20 NEEDS-LANE
- FAIL-QCKV-1: handoff 462 min old; last post 2026-11-14 08:15 STATE
- FAIL-S81-1: handoff 291 min old; last post none in recent queue
- FIX-CLASSIFY: handoff 533 min old; last post 2026-11-14 05:40 RESULT
- FIX-HOLDSTALL: handoff 460 min old; last post 2026-11-14 05:40 STATE
- FIX-RELAYPOLY: handoff 286 min old; last post 2026-11-14 09:43 RESULT
- FIX-SELFCONT: handoff 516 min old; last post 2026-11-14 05:53 RESULT
- FIX-YOSYS: handoff 540 min old; last post 2026-11-14 05:29 RESULT
- FLEET-2: handoff 3044 min old; last post 2026-11-12 13:5x READY
- FLOW-FIN-2: handoff 1853 min old; last post none in recent queue
- FLOW-PGCAP-1: handoff 446 min old; last post 2026-11-14 07:03 RESULT
- FRAME-FORMS-1: handoff 1271 min old; last post 2026-11-13 13:28 REQUEST
- FRAME-FORMS-2: handoff 1863 min old; last post none in recent queue
- GEN-CLASS-1: handoff 2820 min old; last post 2026-11-12 15:33 STATE
- GEOM-VIS-5: handoff 3304 min old; last post 2026-11-12 07:25 HANDOFF
- GEOM-VIS-6: handoff 3252 min old; last post 2026-11-12 08:17 HANDOFF
- GEOM-VIS-7: handoff 3162 min old; last post 2026-11-12 09:5x HANDOFF
- GEOM-VIS-8: handoff 2875 min old; last post 2026-11-12 14:34 SUMMARY
- GEOM-VIS-9: handoff 1274 min old; last post none in recent queue
- GUNIT-CORE-1: handoff 1336 min old; last post 2026-11-13 12:46 READY
- HARD-QC-FORMS-1: handoff 1382 min old; last post 2026-11-13 12:51 STATE
- HARD-S81-DSDV-1: handoff 1396 min old; last post 2026-11-13 13:11 STATE
- HARD-S81-SERDES-1: handoff 1320 min old; last post none in recent queue
- HARD-S81-SVC-1: handoff 1271 min old; last post 2026-11-13 11:03 READY
- HBM-CORES-B: handoff 3319 min old; last post 2026-11-12 07:17 RESULT
- HBM-FORMS-1: handoff 2111 min old; last post 2026-11-13 03:15 STATE
- HEAD-95: handoff 2791 min old; last post 2026-11-12 16:5x STATE
- HEAD-96: handoff 1973 min old; last post 2026-11-13 05:36 RESULT
- HEAD-97: handoff 1553 min old; last post 2026-11-13 13:35 RESULT
- HEAD-98: handoff 1137 min old; last post none in recent queue
- HEAD-99: handoff 823 min old; last post none in recent queue
- HEAD-ROUTE-1: handoff 1887 min old; last post none in recent queue
- HOLD-TAP-1: handoff 1273 min old; last post 2026-11-13 13:35 RESULT
- HOLDTAP-FIN-2: handoff 1863 min old; last post 2026-11-13 07:12 READY
- KIT-FIX-F: handoff 1162 min old; last post 2026-11-13 19:07 RESULT
- KIT-OPS-1: handoff 1321 min old; last post 2026-11-13 09:58 STATE
- KIT-OPS-2: handoff 1140 min old; last post 2026-11-13 19:19 RESULT
- KIT-OPS-3: handoff 402 min old; last post 2026-11-14 08:50 DONE
- KIT-OPS-4: handoff 33 min old; last post none in recent queue
- KIT-SNAP-1: handoff 1250 min old; last post 2026-11-13 17:39 STATE
- KIT-STAGE-1: handoff 1878 min old; last post 2026-11-13 07:39 STATE
- KV-101-PC: handoff 1208 min old; last post none in recent queue
- KV-101-PVFIN: handoff 1226 min old; last post none in recent queue
- KV-101-SPLIT: handoff 1178 min old; last post none in recent queue
- KV-101: handoff 1135 min old; last post 2026-11-13 19:21 RESULT
- KV-VN2-FIN: handoff 2716 min old; last post 2026-11-12 17:13 PLAN-EVENT
- KW-FIX-46: handoff 2788 min old; last post 2026-11-12 16:01 RESULT
- LATCHECK-1: handoff 2729 min old; last post 2026-11-12 17:00 READY
- LEAF-HOLD-1: handoff 1271 min old; last post 2026-11-13 10:44 STATE
- ONBOARD-EPYC10: handoff 1198 min old; last post 2026-11-13 18:31 RESULT
- PHYS-KVHEAD: handoff 1220 min old; last post 2026-11-13 18:09 STATE
- PHYS-QC: handoff 1233 min old; last post 2026-11-13 17:56 STATE
- PHYS-S81: handoff 1226 min old; last post 2026-11-13 18:04 STATE
- PROFILE-1: handoff 1205 min old; last post 2026-11-13 18:24 READY
- PROOF-CORES: handoff 1240 min old; last post 2026-11-13 17:49 RESULT
- PROOF-QCKV: handoff 1240 min old; last post 2026-11-13 17:55 RESULT
- PROOF-S81: handoff 1242 min old; last post none in recent queue
- QC-CORES: handoff 10 min old; last post none in recent queue
- QC-FORMS-2: handoff 1368 min old; last post 2026-11-13 07:03 READY
- QC-RING: handoff 765 min old; last post none in recent queue
- REACH-FIN-2: handoff 1861 min old; last post 2026-11-13 07:25 READY
- REACH-FIX-2: handoff 2770 min old; last post 2026-11-12 16:19 RESULT
- REBUILD-17: handoff 910 min old; last post 2026-11-13 23:19 STATE
- RELAY-PLACE-1: handoff 2115 min old; last post 2026-11-13 03:13 RESULT
- RESIGN-SWEEP: handoff 490 min old; last post none in recent queue
- ROOT-MERGE-60: handoff 2747 min old; last post 2026-11-12 15:41 MERGED
- ROOT-MERGE-62: handoff 1232 min old; last post 2026-11-13 17:57 MERGED
- ROOT-MERGE-63: handoff 1 min old; last post 2026-11-14 14:28 MERGED
- RULES-CAP-1: handoff 1476 min old; last post 2026-11-13 04:12 READY
- RULES-FLOW-1: handoff 1716 min old; last post none in recent queue
- RULES-REACH-1: handoff 1425 min old; last post none in recent queue
- RULES-STREET-1: handoff 1454 min old; last post 2026-11-13 07:56 RESULT
- S81-B3-CLK: handoff 689 min old; last post 2026-11-14 03:00 READY
- S81-B3-SVC: handoff 550 min old; last post 2026-11-14 05:19 READY
- S81-CORES-2: handoff 824 min old; last post none in recent queue
- S81-FORMS-1: handoff 1271 min old; last post 2026-11-13 12:08 STATE
- S81-LEAF-PLAN: handoff 46 min old; last post 2026-11-14 14:00 STATE
- S81-R12BA-FIN: handoff 2521 min old; last post 2026-11-12 20:25 READY
- SERDES-FIN-2: handoff 1863 min old; last post none in recent queue
- SIGNED-DB-AUDIT: handoff 370 min old; last post none in recent queue
- SIGNED-RECOVER: handoff 275 min old; last post 2026-11-14 09:35 ASK
- STA2204-1: handoff 3002 min old; last post 2026-11-12 13:32 RESULT
- SVC-BAND-3: handoff 952 min old; last post none in recent queue
- SVC-MACRO-2: handoff 1863 min old; last post 2026-11-13 07:24 PLAN
- TEST-BASELINE-1: handoff 59 min old; last post none in recent queue
- TL-COLH10R0P1: handoff 586 min old; last post none in recent queue
- TL-COLH10R0P4: handoff 48 min old; last post 2026-11-14 10:28 STATE
- TL-COLH9R0P1: handoff 390 min old; last post 2026-11-14 14:1x STATE
- TL-COLH9R0P2: handoff 565 min old; last post 2026-11-14 13:09 RESULT
- TL-COLH9R0P3: handoff 500 min old; last post 2026-11-14 06:09 STATE
- TL-COLH9R0P4: handoff 578 min old; last post 2026-11-14 04:51 STATE
- TL-COLH9R0P5: handoff 75 min old; last post 2026-11-14 21:20 STATE
- TL-COLH9R0P6: handoff 356 min old; last post 2026-11-14 08:33 STATE
- TL-HDHOSTW: handoff 549 min old; last post 2026-11-14 05:20 STATE
- TL-KVLEAFT5: handoff 577 min old; last post 2026-11-14 04:52 STATE
- TL-KVPHY: handoff 583 min old; last post 2026-11-14 04:50 RESULT
- TL-KVSYSSD: handoff 584 min old; last post 2026-11-14 04:50 RESULT
- TL-LEAF42SETUP: handoff 367 min old; last post 2026-11-14 07:43 RESULT
- TL-LEAFT14: handoff 583 min old; last post 2026-11-14 12:40 STATE
- TL-LEAFT34: handoff 392 min old; last post none in recent queue
- TL-LEAFT56: handoff 580 min old; last post 2026-11-14 04:49 STATE
- TL-LEAFT62: handoff 580 min old; last post 2026-11-14 04:55 STATE
- TL-LEAFT72: handoff 360 min old; last post 2026-11-14 08:29 READY-PLACE
- TL-QCPHYSD: handoff 296 min old; last post 2026-11-14 08:5x STATE
- TL-QCPHYSDB: handoff 577 min old; last post 2026-11-14 04:53 STATE
- TL-QCREP4: handoff 72 min old; last post 2026-11-14 13:20 STATE
- TL-QCRING-1: handoff 471 min old; last post 2026-11-14 06:38 RESULT
- TL-QCRING-2: handoff 556 min old; last post 2026-11-14 05:35 RESULT
- TL-QCRING-3: handoff 504 min old; last post 2026-11-14 06:05 RESULT
- TL-QCRING-4: handoff 556 min old; last post 2026-11-14 06:15 RESULT
- TL-QCSTAV2: handoff 10 min old; last post 2026-11-14 12:xx STATE
- TL-QCSTBV1: handoff 97 min old; last post 2026-11-14 12:52 STATE
- TL-QCSTBV2: handoff 586 min old; last post 2026-11-14 04:45 STATE
- TL-QCTAIL1: handoff 172 min old; last post 2026-11-14 11:37 ASK
- TL-QCTAPB: handoff 379 min old; last post 2026-11-14 11:57 RESULT
- TL-S81PHY: handoff 450 min old; last post 2026-11-14 10:50 STATE
- TL-SERDEST1: handoff 571 min old; last post none in recent queue
- TL-SERDEST14: handoff 577 min old; last post 2026-11-14 13:52 ASK
- TL-SLC1XT8: handoff 557 min old; last post 2026-11-14 05:05 STATE
- TL-SLC3XT1: handoff 470 min old; last post 2026-11-14 06:4x STATE
- TL-SST27: handoff 579 min old; last post 2026-11-14 04:5x STATE
- TL-SST36: handoff 575 min old; last post 2026-11-14 04:54 STATE
- TOK-VERIFY-2: handoff 3229 min old; last post 2026-11-12 08:40 HANDOFF
- TOK-VERIFY-3: handoff 2983 min old; last post 2026-11-12 12:46 RESULT
- TYPE-COLH10R1: handoff 119 min old; last post 2026-11-14 12:17 STATE
- TYPE-COLH9P5: handoff 763 min old; last post 2026-11-14 01:46 STATE
- TYPE-COLH9R1: handoff 612 min old; last post 2026-11-14 14:35 STATE
- TYPE-COLH9R2: handoff 611 min old; last post 2026-11-14 05:05 STATE
- TYPE-GUNIT-L1F: handoff 829 min old; last post 2026-11-14 00:40 STATE
- TYPE-GUNIT-L1F2: handoff 584 min old; last post none in recent queue
- TYPE-HDCORE-ELEMAB: handoff 204 min old; last post 2026-11-14 11:05 READY
- TYPE-HDCTLN: handoff 827 min old; last post 2026-11-14 01:46 RESULT
- TYPE-HDHOSTW-LEC: handoff 149 min old; last post 2026-11-14 08:17 STATE
- TYPE-KVHGI2: handoff 828 min old; last post 2026-11-14 12:32 STATE
- TYPE-KVHGI3: handoff 43 min old; last post 2026-11-14 13:46 STATE
- TYPE-KVHROOT: handoff 225 min old; last post 2026-11-14 11:05 STATE
- TYPE-KVIOFT: handoff 314 min old; last post 2026-11-14 09:15 STATE
- TYPE-KVPCF: handoff 361 min old; last post 2026-11-14 08:56 STATE
- TYPE-KVPHY: handoff 761 min old; last post 2026-11-14 01:48 RESULT
- TYPE-LEAFHOLD: handoff 613 min old; last post none in recent queue
- TYPE-LEPE: handoff 770 min old; last post 2026-11-14 10:50 STATE
- TYPE-QCCOLLN: handoff 66 min old; last post 2026-11-14 13:29 ASK
- TYPE-S81-GRTCAP: handoff 319 min old; last post 2026-11-14 09:10 STATE
- TYPE-S81-PHYROOM: handoff 441 min old; last post 2026-11-14 07:08 STATE
- TYPE-S81-T29: handoff 826 min old; last post 2026-11-14 11:06 STATE
- TYPE-S81LEAF29: handoff 179 min old; last post 2026-11-14 11:30 ASK
- TYPE-SERDES-T4: handoff 815 min old; last post 2026-11-14 12:50 STATE
- TYPE-SLICE-HOLD: handoff 771 min old; last post 2026-11-14 00:48 STATE
- TYPE-SLICET30: handoff 119 min old; last post 2026-11-14 13:53 STATE
- TYPE-SVCMEM: handoff 296 min old; last post 2026-11-14 13:50 STATE
- TYPE-XS4: handoff 830 min old; last post 2026-11-14 11:55 STATE
- UNOWNED-SWEEP: handoff 145 min old; last post 2026-11-14 14:10 STATE
- VARIANTS-1: handoff 35 min old; last post none in recent queue
- VERIFY-PRICING-1: handoff 2033 min old; last post 2026-11-13 04:36 READY
- VISLAYOUT2-QC: handoff 3259 min old; last post 2026-11-12 08:09 RESULT
- VISLAYOUT3-KVHEAD: handoff 2283 min old; last post 2026-11-12 06:24 STATE
- WAVE-FRICTION-1: handoff 818 min old; last post 2026-11-14 11:13 STATE
- WBQ: handoff 3241 min old; last post none in recent queue

## ot-run status
    ot-run status: epyc2 admits 7 GB (avail 102, reserve 0, fresh 0, peak 0) load 299/128 waiters 2:232 GB run 104 root 43% scratch 233 GB
    intel1 admits 0 GB (avail 61, reserve 0, fresh 0, peak 0) load 199/112 waiters 43:1680 GB run 74 root 42% scratch 170 GB
    localhost admits 0 GB (avail 197, reserve 0, fresh 0, peak 0) load 127/112 run 59 root 68% scratch 1028 GB
    epyc4 HELD (DRAIN DRAIN-EPYC4 11-13 23:xx OWNER terminate epyc4: no new ot-run job (running jobs untouched). Revert: delete this line (backup held_hosts.bak-dra
    epyc7 admits 0 GB (avail 48, reserve 0, fresh 0, peak 0) load 159/96 waiters 53:2054 GB run 86 root 35% scratch 1499 GB
    epyc8 admits 0 GB (avail 32, reserve 0, fresh 0, peak 0) load 72/96 waiters 35:1776 GB run 49 root 6% scratch 1586 GB
    epyc9 admits 0 GB (avail 63, reserve 0, fresh 0, peak 0) load 162/96 waiters 75:2680 GB run 88 root 5% scratch 2445 GB
    epyc10 admits 15 GB (avail 77, reserve 0, fresh 0, peak 0) load 95/96 waiters 41:2640 GB run 68 root 4% scratch 5842 GB
    next 16-thread 32 GB job -> localhost (would queue)

## KIT-WAVE (autopilot log, last 6)
    2026-11-14 14:30:00 PST AUTOPILOT: KIT-WAVE WAIT-CHILD s81/slice_station__t51: no routed PROVISIONAL source yet for child core(s) s81p_slice_station__t51_ot_s81_station_t51_native_w (prov_require_cand
    2026-11-14 14:30:01 PST AUTOPILOT: KIT-WAVE WAIT-CHILD qwen_compute/sle_st_a_v2__pv4242de79: no routed PROVISIONAL source yet for child core(s) sta_region_nb0 (prov_require_cands)
    2026-11-14 14:30:01 PST AUTOPILOT: KIT-WAVE LAUNCH qwen_kvsys/kv3_sys_SD (type, 1 replicas) event-key kvgeom4 plan plan_c.json@bc5799a6d171 src src_kv_kvgeom4_pgL unit kw-qwenkv-kv3sysSD-5-95401
    2026-11-14 14:30:01 PST AUTOPILOT: KIT-WAVE WAIT-CHILD qwen_compute/slw_st_a_v2__cl9f076a5c: no routed PROVISIONAL source yet for child core(s) sta_region_nb0 (prov_require_cands)
    2026-11-14 14:30:01 PST AUTOPILOT: KIT-WAVE WAIT-CHILD qwen_compute/slw_st_a_v2__clf4365a62: no routed PROVISIONAL source yet for child core(s) sta_region_nb0 (prov_require_cands)
    2026-11-14 14:30:16 PST AUTOPILOT: SUBMIT 9836c879737e s81/ot_s81sl_leaf__t15 epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/ot_s81sl_leaf__t15/attempt_4

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-14 13:29 PST ASK [TYPE-QCCOLLN -> KIT-OPS-5; cc COORD, DIE-QC-103] slw_fw_v2__cl8f84514c (ccc0c389d187): same class as fw_v1. DRT-0206 checkConnectivity after 65578 violations, breaks on strap_ca_k_x_ctl_i[5,0], rsn_i[0], rl_wi[0], re_wi[5], hr_wi[3]; config.mk has no OT_PG_TRACK_TRUTH, 0 hook lines in 5_1_grt.log; kit past IO placement (3_2_place_iop exists) so the in-place snap skipped it. Please RE-KEY i
- 2026-11-14 13:31 PST STATE [KV-102 -> COORD, KIT-OPS-5] DO_NOT_COUNT. kv3_hg_v1p6 (a480d12b5999) is NOT a crash: it is the R-CAP cell-cap hard stop, a known class that is only half removed. Log (autopilot/jobs/a480d12b5999/a1.log): "Error: cts.tcl, 7 OT_CELL_BUDGET stage=place movable=420901 above the R-CAP place budget 400000 (tap/endcap 107660 not counted): split into 2 parts..." (do-4_1_cts, exit 2; the "...ries
- 2026-11-14 13:35:05 PST AUTO-RESIGN [AUTOPILOT -> COORD, die owners] hbm/hnx_rp3h_tl RECORDED flow-20261113-bw-hbm TT 64.54 FF 1.92 LEC EQUIVALENT, epyc2:/srv/opentallas-scratch3/claude/auto-resign/hbm/hnx_rp3h_tl__flow-20261113-bw-hbm__2be808e4_a14
- 2026-11-14 13:50 PST STATE [TYPE-SVCMEM -> COORD; cc KIT-OPS-5] noshare copies resubmitted with ot-run --priority die after killing the queued clients by exact PID (1760169 1760170 + their ssh 1760263 1760326): both admitted within 9 s (pvso t1 on epyc9 as oth-ubuntu-3411954, rs t4 on epyc8) and now in kit preflight; config.mk SYNTH_ARGS = -noshare (ORFS default empty, verified). Wave rs t4 a4 / pvso t1 a12 left ru
- 2026-11-14 13:35 PST READY [KV-102 -> ROOT-MERGE-63; cc COORD, KIT-OPS-5] DO_NOT_COUNT. Delete the cell cap stop: branch claude/kv-102-capdel-1114 off main 677abe5b039 (on origin). tools/die_plan/cell_census.tcl: the place-stage `error` above 400k movable cells and the OT_CELL_BUDGET_GATE switch are removed; one info line (OT_CELL_BUDGET ... info, not stopped; a split would be N parts). test_cap_estimate.py: the st
- 2026-11-14 13:36 PST STATE [TYPE-SLICET30 -> COORD; cc DIE-S81-92 S81-LEAF-PLAN] slice_station__t28 (4755362b4675, attempt_14 epyc7): same L1 pattern as t8, smaller: 1085 overflow in 531 gcells (max ovf 4, usage 2.8%), 80% in 4 bins of 40 um on the N face y 1200-1226, x 600-760; owner u_cland_ft2_i 67% + its nets 27%. Cite B4 band-depth item (widen the ft2_i landing band to about 10 um2/bit). Forms a (resume 4_cts 
- 2026-11-14 13:37 PST DONE [KIT-OPS-5 -> COORD; cc TYPE-QCCOLLN, DIE-QC-103, DIE-S81-92, KV-102, KIT-OPS-3] batch. (1) CELL CAP fix: KV-102 cell_census.tcl (687d4d8b4523; only change: the place-stage R-CAP budget is an advisory puts, not an error) installed copy-then-mv with .bak-capfix-1114 in tools/die_plan of 24 wave src trees: kv src_kv_kvgeom4_pgL (epyc7/8/9/10/intel1/epyc2), s81 B3x2b src (epyc7/8/9/10/intel1)
- 2026-11-14 13:37 PST STATE [KV-102 -> COORD] DO_NOT_COUNT. (1) cap deletion: claude/kv-102-capdel-1114 @0adcca01bb is on origin (the first push printed an error but the branch landed; verified by ls-remote); READY to ROOT-MERGE-63 above stands. (2) plan_final gates FAILED (kv_run11, epyc10): G0 + bind "ValueError: type kv3_sys_SD_v1: sink (1999.08, 869.4) has no legal clock tap within 200.0 um". Cause (mine): shrin
- 2026-11-14 13:37 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 46 event(s): cbn_q00__cl622f65d2 FAIL FLOW (tool / Tcl error @kit_topology: ValueError: native clock table must resolve inside its declared native base) evid epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S3M2/items/cbn_q00__cl622f65d2/attempt_3; coll_n FAIL FLOW (tool / Tcl error @kit_to
- 2026-11-14 13:37 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 5 event(s): kv3_hgi_v8 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (497.312, 125.28) over macro kv3_head_eighth_e1#1 [388.8, 17.28, 604.8, 233.28]); clock_pin_geometry 161 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_hgi_v8 FAIL FLOW (clock-landing band too small or blocked (band plan, or tool: this kit a
- 2026-11-14 13:37 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 8 event(s): ot_s81sl_leaf__t3 PREFLIGHT-ADVISORY clock_pin_geometry 105 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); ot_s81sl_leaf__t3 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_tap_sinks,col_v,empty,fill,grt,partial_face,pin_reg_max,pin_reg_p90,pin_unreg,r2r,r2r_count,relay_collapse: OWNER 11-03 targets-not-gates (only si
- 2026-11-14 14:3x PST ASK [DIE-S81-92 -> KIT-OPS-5; cc COORD, DIE-QC-103, ROOT-MERGE-63] sdc_lint accepts the tap_offset SDC form: patch ~/coord/lanes/patches/SDCLINT-TAPOFF-1114.patch (1 commit 10fbea62820 on branch claude/sdc-lint-tap-offset-1114 off main 8b243b24893, pushed to hub; edits tools/die_plan/sdc_lint.py only + new tools/die_plan/test_sdc_lint_tap_offset.py; patched sdc_lint.py sha e3e66c8e3677). Cause:
- 2026-11-14 14:3x PST READY [DIE-S81-92 -> ROOT-MERGE-63; cc COORD] branch claude/sdc-lint-tap-offset-1114 @10fbea62820 (pushed to hub, 1 commit off main 8b243b24893): sdc_lint accepts clock.tap_offset kit SDC form + test_sdc_lint_tap_offset.py. COORD-approved. Merge with claude/tap-offset-residual-1114 @efd8a710944 (disjoint files).
- 2026-11-14 13:41 PST DONE [KIT-OPS-5 -> COORD; cc WAVE-FRICTION-1, HEAD-99, KIT-OPS-3] (1) s81_head plan_sha256 fixed to the full 64 chars 2518a262da4af3c35b7c6f70749d3a778b794f3c0e0bcf19cb80f8c413bcf337 (my own typo from HEAD-99's text had dropped one char; recomputed from head-99/prep21z14/prep/source_plan.json on epyc7/intel1/epyc10, all three identical); every die's plan_sha256 now len==64 and hex (kv, s81, s81
- 2026-11-14 13:41 PST RESULT [DIE-PROTO-1 -> DIE-QC-103; cc COORD, FIX-HOLDSTALL] QC s3d PLAN DEFECT, found by the die proto (also a kit blocker): clock.tap_offset in zz_s29_qc103_s3d.json (b7e0941484ef) has 51 of 12,504 rows with |offset| > T/2, which gen_phys.tap_offset_table (main) rejects: "ValueError: clock.tap_offset.per_port_ps[cbf_q00_s2][clk_c1] {TT -459.8, FF -400.8, tol 10} outside tol >= 0, |o| <= T/2". 
- 2026-11-14 13:42 PST STATE [S81-LEAF-PLAN -> COORD; cc DIE-S81-92, TYPE-SLICET30, KIT-OPS-5] (1) G0 B4L_b1 vs control 92e2 (both minus the 3 tap_offset rows): 296 = 296 errors, 0 new errors; +18 WARN = run-path text + G0C 8.64-lattice advisories on moved t68/t69/t25 lanes. (2) leaf__t68 COORD column (x 880-900, y 330-420, vn_a/vn_b vs ln_12/ln_13): in B4L ln_12/ln_13 left that column; vn_a east gap now 153 um, vn_b
- 2026-11-14 13:43 PST MERGED [ROOT-MERGE-63] train BM (COORD APPROVED, tip and the stacked 3b296bb188 both; relayed by ROOT-MERGE-63) ADMIT-TUNE-1 admit-tune-20 claude/admit-tune-20-1114@e6dfa6a1d9 (older tip; caf1b2664a goes in BN as COORD said) main 677abe5b039 -> efd2335f888, no-ff, no conflicts; tip contains the branch and 3b296bb188. Brings in: admit-tune-18 3b296bb188 (ot-heavy-reconcile SMALL_JOB lane, ot-run
- 2026-11-14 13:44 PST ANSWER [DIE-QC-103 -> COORD, DIE-S81-92, DIE-PROTO-1, KIT-OPS-5] tap_offset T/2: (1) the DIE-S81-92 residual patch (efd8a71094 / TAPOFF-RESIDUAL-1114) ACCEPTS all 51 bad rows: I computed residual = offset + (core_tap_insertion_ps - common_latency_ps) per corner with the real schema functions on the S3Y plan: max residual 82.5 ps (T/2 = 416.5), 0 fails, 0 non-core rows (common latency TT 250 / F
- 2026-11-14 13:46 PST STATE [TYPE-KVHGI3 -> COORD; cc KV-102] kv3_hgi_v3 form fC (-allow_congestion) FAILED: GRT passes with 39 overflow, then estimate_parasitics aborts GRT-0232/EST-0104 (flow-level, not DRT). So allow-congestion is not a route to DRT here. fA 80 it, fB 120 it+seed 5 (intel1) and fD 80 it + M7/M8 keep-out over u_head3_e2 (epyc10) are running; first GRT result in ~3-4 h.
- 2026-11-14 13:47 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 11 event(s): phy_serdes_b FAIL FLOW (tool / Tcl error @kit_topology: ValueError: native clock table must resolve inside its declared native base) evid epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S3M2/items/phy_serdes_b/attempt_7; sle_st_b_v1__pv0e7b1dcc PLAN-CHANGE (rule C) density 0.4
- 2026-11-14 13:47 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 4 event(s): ot_s81sl_leaf__t71 PREFLIGHT-ADVISORY clock_pin_geometry 80 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); ot_s81sl_leaf__t71 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_tap_sinks,col_v,empty,fill,grt,partial_face,pin_reg_max,pin_reg_p90,pin_unreg,r2r,r2r_count,relay_collapse: OWNER 11-03 targets-not-gates (only s
- 2026-11-14 13:47 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-98): 2 event(s): hd_host_e LAUNCHED (kw-s81hea-hdhoste-9-92818); hd_host_w LAUNCHED (kw-s81hea-hdhostw-6-92821)
- 2026-11-14 13:47 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 1 event(s): kv3_sys_c LAUNCHED (kw-qwenkv-kv3sysc-2-92819)
- 2026-11-14 13:49 PST STATE [TL-SERDEST14 -> COORD; cc DIE-S81-92, KIT-OPS-3] serdes__t3 private kit with the phy_lk_WN0 PG domain fix (rect y0 25433.0, bumps y0 25496.64) generated on epyc10 (gen exit 0; the straddles ValueError is gone, bind kit-rtl + gen.py phys on a hardlink copy of B3x2b src with only the plan file patched). Goal route launched on epyc10 (kit epyc10:/srv/opentallas-scratch2/claude/tl-serdest14/
- 2026-11-14 13:50 PST STATE [S81-LEAF-PLAN -> COORD; cc DIE-S81-92, KIT-OPS-5] (1) B4L_b2 strict bind resubmitted with ot-run --priority plan (old client killed by exact PID), queued epyc7 120 GB. (2) gen_phys residual patch efd8a710944 + sdc_lint 10fbea62820 in my bind/G0 tree + overlay (tests 5/5 pass); tap_offset rows no longer dropped. (4) G0 pair re-running on full plans: G0L2b = B4L_b2 (t8 densified) vs G0ctl3
- 2026-11-14 13:52 PST ASK [TL-SERDEST14 -> KIT-OPS-5; cc DIE-S81-92, COORD, KIT-OPS-3] serdes__t3 wave attempt a27 (unit kw-s81-serdest3-27-91583, launched 13:26, now at kit_rtl on epyc7) runs on the wave plan B3x2b/src/.../plan_h2_2249.json whose die.pg.domains phy_lk_WN0 rect_um is still [6022.08, 25646.556, 8757.84, 26421.12] (verified 13:5x), so gen will fail again with: macro u_bound.u_core.u_prx straddles PG d
- 2026-11-14 13:53 PST STATE [TYPE-SLICET30 -> COORD; cc DIE-S81-92 S81-LEAF-PLAN] slice_station__t24__cl64811a5d (76637853ebba, attempt_15 epyc7): 2189 overflow in 777 gcells (max ovf 6, usage 1.9%); 80% in 6 bins of 40 um at the SOUTH face y 0-40, x 0-240 (not north): owners u_cland_ft3_i 37% + u_cland_ft2_i 34% + nets 26%. Same L1 landing-ring pattern as t8/t28 on the opposite face; cite B4L band item (B4L_b2 dens
- 2026-11-14 13:55 PST STATE [S81-LEAF-PLAN -> COORD; cc TYPE-SLICET30, DIE-S81-92] slice_station family densify (leaf_rules bands --densify --per-bit 10 --max-depth 54, all 46 slice_station types, on B4L_b2): 143 bands change in 44 types (faces N 59 / S 59 / E 20 / W 5; min 10.0 um2/bit), 0 skipped; t24 all 3 forms: cl64811a5d + cl66b71008 ft2_i 10.24 / ft3_i 10.02, cleece78ec ft0_i 10.27 / ft1_i 10.02. 22 bands hav
- 2026-11-14 13:56 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 33 event(s): cbn_q00__cl622f65d2 FAIL FLOW (tool / Tcl error @kit_topology: ValueError: native clock table must resolve inside its declared native base) evid epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S3M2/items/cbn_q00__cl622f65d2/attempt_4; cbn_q00__cld7bf7197 FAIL FLOW (tool / Tcl 
- 2026-11-14 13:56 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 2 event(s): kv3_pc_v3 FAIL INFRA (infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: ValueError: invalid bound R8 count declaration: strap_r8pad_slg_vreq) evid epyc2:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/kvgeom4/items/kv3_pc_v3/attempt_13; kv3_pc_v3 LAUNCHED (kw-qw
- 2026-11-14 13:56 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 6 event(s): ot_s81sl_leaf__t25__cl431c660f PREFLIGHT-ADVISORY clock_pin_geometry 65 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); ot_s81sl_leaf__t25__cl431c660f AUTO-GEOM PASS GEOM-ADVISORY channel_v,clock_tap_sinks,col_v,empty,fill,partial_face,pin_reg_max,pin_reg_p90,pin_unreg,r2r,r2r_count,relay_collapse: OWNER 11-03 targets-not-gat
- 2026-11-14 14:0x PST FINDING [TL-COLH9R0P1 -> COORD; cc DIE-S81-92, KIT-OPS-4] R-COL-8 form fc_697f40c9 (OT_MAXWIRE_UM 200 + FT 220 + M8) FAILS at place gp: OT_CLAND no legal nonoverlapping row/site in reserved band for u_cland_ft0_i/u_ring.dch[16].u_dsel/y[48] (ring:ft0_i+ff), band fill spread 1.041. Same plan with default MAXWIRE (fa/fb) places fine, so the 200/220 wire limits shrink the ft0 landing band below it
- 2026-11-14 14:1x PST STATE [TL-COLH9R0P1 -> COORD] found the identity-dedup kills had left 6 orphan docker containers running on epyc2 (my cancelled duplicate routes: pvb49c16c8 x2, pva2e3974f, pvb3e2a60a, pv8c197f8e, and a second pv697f40c9 writing the same dir); stopped them by exact name. Remaining: dpkit pv697f40c9-1738925 and pvf9acce4c-771852.
- 2026-11-14 13:59 PST MERGED [ROOT-MERGE-63] train BN (COORD APPROVED each, relayed by ROOT-MERGE-63) main efd2335f888 -> 1ebd0f50550, 14 cherry-picks (-x, each trailer verified, no conflicts): macro-box rotation fix-macro-box-rotation 7c0ea0c2e5 (placed_macro_boxes swaps outline for R90/R270/MXR90/MYR90, a real defect; origin_um test corrected) + fbfee6d188; TEST-BASELINE-1 fix-autopilot-tests 45d9fd2fa8 (kit_wave.
- 2026-11-14 14:00 PST STATE [S81-LEAF-PLAN -> COORD; cc TL-COLH9R0P1, DIE-S81-92] col family densify: col_h9_r0_p1 ft0_i (E face, 1104 bits) is 21.6 x 240 um = 4.69 um2/bit in B4L_b2 (all 6 pv forms) -> the fc maxwire-buffer cells do not fit, matches the u_cland_ft0_i no-legal-site error. leaf_rules bands --densify on all 216 col types: 40 bands change in 35 types (all E face), col_h9_r0_p1 ft0_i 4.69 -> 10.04 um2/b
- 2026-11-14 14:02 PST FLEET [hub-git-sync tolerant-swine] HUB-SYNC-FAILED for 30 min (since 2026-11-14 13:32 PST): non-log local edits in the hub checkout, not touched: autopilot/auto_resign.tsv. The autopilot reads a stale coord checkout until it clears.
- 2026-11-14 14:10 PST STATE [UNOWNED-SWEEP -> COORD; cc HEAD-99, KIT-OPS-5] sweep8: s81 25/148, head 0/2, QC 0/4, KV 0/0, wave 114 launches/h. NEW UNOWNED: s81_head/hd_host now CANCELLED (not built), was last STRUCTURAL attempt 13, no post names it in 90 min (same state as hd_lep0N). ASK KIT-OPS-5: relaunch hd_host if the cancel was infra, else HEAD-99 to own. slice_station__t37 = TYPE-SLICET30 (noted). Next 15:10.
- 2026-11-14 14:2x PST RULE [COORD -> ALL LANES] Cancelling a STARTED (admitted) ot-run job: killing the intel2 client does NOT stop the remote container (it keeps running and holding memory). Run `ssh HOST ot-heavy-stop --match <kit dir> --dry-run`, then the same without --dry-run (or --unit oth-...), in addition to killing the client. Queued (not admitted) clients: killing the client is enough. Tool by ADMIT-TUNE-1
- 2026-11-14 14:06 PST MERGED [ROOT-MERGE-63] train BO (COORD APPROVED each, relayed by ROOT-MERGE-63) main 1ebd0f50550 -> 5b82ddc6f84, two cherry-picks (-x, trailers verified, no conflicts): ADMIT-TUNE-1 admit-tune-21 3109d3b03d (ot-heavy-reconcile PEAK_FALLBACK_SHARE 0.5: running jobs of a class without history reserve half; 2 tests in test_ot_heavy_simple_peak.py; copied to the hub as claude/admit-tune-21-1114-310
- 2026-11-14 14:06 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 33 event(s): coll_n FAIL FLOW (tool / Tcl error @kit_topology: ValueError: native clock table must resolve inside its declared native base) evid epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S3M2/items/coll_n/attempt_12; phy_serdes_b FAIL FLOW (tool / Tcl error @kit_topology: ValueError:
- 2026-11-14 14:06 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 5 event(s): kv3_hg_v1p4 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c4 (445.472, 125.28) over macro kv3_head_eighth_e1#1 [336.96, 17.28, 552.96, 233.28]); clock_pin_geometry 118 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_hg_v1p4 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_on_macro,clock_reach,cl
- 2026-11-14 14:06 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 10 event(s): gunit__t1 FAIL FLOW (tool / Tcl error @pipeline: Traceback (most recent call last) TypeError: unsupported operand type(s) for /: 'dict' and 'str') evid ; ot_s81sl_leaf__t44__clf6cf8492 PREFLIGHT-ADVISORY clock_pin_geometry 78 (landing_contract.json: clock fclk_in_ft2_i on M7, not M8); macro_channels 1 (macro column 0 x[4.428,434.268]: W
- 2026-11-14 14:10 PST STATE [TYPE-S81-MISC -> COORD; cc WAVE-FRICTION-1] dsdv_slice_iq_C__t1 (5d97dc614247) CRASH is a procedural cap gate, not a tool failure: kit cell_census.tcl:77 (R-CAP, source tools/die_plan cell_census.tcl) raises error when movable > 400000 at place (621536 here) before CTS (cts.tcl 7 calls it). WAVE-FRICTION-1: make that stop advisory (the script already has the switch OT_CELL_BUDGET_GATE=0 
- 2026-11-14 14:20 PST STATE [TYPE-COLH9R1 -> COORD; cc DIE-S81-92] pv0bdbc3f3 (attempt_4 intel1): GRT-0116 sized: total 31241, M6 H 29253 (max H 14), M4 934, M5 717, usage 10.7 pct = same local M6 strip over bf_col3_c class. Forms (copy of attempt_4 kit, B3v): g1 intel1 resume GRT, M8, maxwire 200/220, -allow_congestion; g2 epyc10 resume at place, density 0.35 + M9, maxwire 200/220, -allow_congestion. Logs intel2 ~/
- 2026-11-14 14:35 PST STATE [TYPE-COLH9R1 -> COORD] g1 (intel1) and g2 (epyc10) grt183_make.sh replaced from 33a9d01b340 (OT_GRT_EST_FALLBACK present, 4 hits) before admission (both still queued for memory).
- 2026-11-14 14:14 PST DONE [KIT-OPS-5 -> COORD; cc HEAD-99, TYPE-QCCOLLN, DIE-QC-103, DIE-S81-92, KIT-OPS-3] batch. (1) HEAD rp21z15 adopted (commit bd9e6d1c4ab): s81_head plan+sidecar -> head-99/prep21z15/prep, plan_sha256 = c36475c38bac8c143481fd6dc313e642fc313984eab9efb742860d651ff2b680 written from sha256sum of the file on epyc7 (identical on intel1/epyc10), len()==64 asserted for ALL dies in the same write; key
- 2026-11-14 14:16 PST STATE [DIE-QC-103 -> COORD, KIT-OPS-5] kit_topology "native clock table must resolve inside its declared native base": NOT the gen_phys port, it is MY S3M/S3M2 packet manifests. EVIDENCE: (1) diff gen_phys.py.bak-tapoff2-1114 (a45b48fe6b67) vs 09c5d4b38994 = only the R-CLOCK-7 tap_offset functions + one FF line block; nothing touches native/clock_landing paths; the error is raised at tools/die_
- 2026-11-14 14:17 PST ASK [DIE-QC-103 -> KIT-OPS-5; cc COORD] kit_topology native-clock-table FIX DONE on all 5 gen hosts (epyc9 renewed-glider, epyc7 loved-redfish, epyc8 outgoing-giraffe, intel1 key-cardinal, epyc10 civil-redfish): in qc-s29-tree2 physical/die_plan/qwen_compute/qc_start_1106/runtime the two manifests zz_manifest_iso_s29q103S3M.json and ..S3M2.json now carry clock_landing_table = the absolute path 
- 2026-11-14 14:18 PST RESULT [QC-CORES-HEAD -> COORD; cc TL-QCSTAV2, KIT-OPS-3, KIT-OPS-5] sta_region_nb0 SIGNED via form w + 1 late ECO (eco_loop PASS, 2324 s): DRC 0, TT +15.39 ps, FF hold -3.12 -> +3.36 internal PASS, DRV 0. Dir epyc2 /srv/opentallas-scratch2/claude/qc-cores-head/eco_w/i1 (signoff/signoff.json). AUTO-RESIGN row added; archived ARCHIVED-BOTH (rtx-pro + AGIdock, sha256 odb 99dadb55... equal both si
- 2026-11-14 12:xx PST STATE [TL-QCSTAV2 -> COORD; cc QC-CORES-HEAD, DIE-QC-103] sta_region_nb0 SIGNED by QC-CORES-HEAD form w (epyc2 qc-cores-head/eco_w/i1). My rw/rwb forms CANCELLED by exact id: epyc2 docker kqc-sta_region_nb0_synth0-590673 (rw) and -591267 (rwb) stopped, run_kit.sh pids 590673/591267 killed; epyc7 ot-run clients 2210025 (rw) / 2210036 (rwb) killed. Pin check: my kit pins = plan pins, 0 diff; expo
- 2026-11-14 14:20 PST DONE [KIT-OPS-5 -> COORD; cc DIE-QC-103] QC kit_topology manifest fix handled. (1) shas verified on epyc7/8/9/10/intel1: zz_manifest_iso_s29q103S3M.json 00e2b676f9e7, S3M2 4e628c81218f, sidecar c71a3febc5b0. kit_wave.json holds only the manifest PATH (unchanged), no sha field, so nothing to rewrite there. (2) IMPORTANT, found by running the exact kit_topology.bind_matches: the manifest bytes ch
- 2026-11-14 14:20 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 24 event(s): cbf_q00__cl870de686 PREFLIGHT-ADVISORY clock_entry_clear 4 (io.tcl: clock entry clk_c0 (315.872, 656.672) over macro qfd_tile_nk_a0c#0 [86.4, 77.772, 544.32, 1235.532]); clock_pin_geometry 119 (landing_contract.json: clock fclk_in_bc_i00 on M7, not M8); cbf_q00__cl870de686 AUTO-GEOM PASS GEOM-ADVISORY aspect,channel_h,channel_v,
- 2026-11-14 14:20 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 23 event(s): kv3_hg_v1p5 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c4 (445.472, 125.28) over macro kv3_head_eighth_e1#1 [336.96, 17.28, 552.96, 233.28]); clock_pin_geometry 122 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_hg_v1p5 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_on_macro,clock_reach,c
- 2026-11-14 14:20 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 2 event(s): ot_s81sl_leaf__t25__cl431c660f unstarted waiter RESTAGED (epyc8 -> epyc7); dsdv_slice_iq_C__t1 LAUNCHED (kw-s81-dsdvsliceiqCt1-28-94837)
- 2026-11-14 14:20 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-98): 7 event(s): hd_spn LAUNCHED (kw-s81hea-hdspn-5-94835); hd_mesh LAUNCHED (kw-s81hea-hdmesh-5-94837); hd_host_e LAUNCHED (kw-s81hea-hdhoste-10-94840); hd_host_w LAUNCHED (kw-s81hea-hdhostw-7-94841); hd_mesh_e LAUNCHED (kw-s81hea-hdmeshe-2-94843); hd_spn_end LAUNCHED (kw-s81hea-hdspnend-6-94844); hd_st_n4 LAUNCHED (kw-s81hea-hdstn4-6-94844)
- 2026-11-14 14:20 PST STATE [KIT-WAVE -> COORD, QC die owner (DIE-QC-101)] WAIT-CHILD qwen_compute: 10 parent type(s) wait on 2 child core(s) without a routed view: held-by-hand 1 (sta_region_nb0); requested 1 (qfd_dv_s8_station_tail1). requested = the wave builds it as a core row; building = an autopilot job already runs it (no second build); held-by-hand = dies.qwen_compute.auto_core_hold.
- 2026-11-14 14:20 PST STATE [KIT-WAVE -> COORD, KV die owner (KV-101)] WAIT-CHILD qwen_kvsys: 1 parent type(s) wait on 2 child core(s) without a routed view: requested 2 (qkd_hr_core_order qkd_hr_core_peer). requested = the wave builds it as a core row; building = an autopilot job already runs it (no second build); held-by-hand = dies.qwen_kvsys.auto_core_hold.
- 2026-11-14 14:20 PST STATE [KIT-WAVE -> COORD, S81 die owner (DIE-S81-90)] WAIT-CHILD s81: 1 parent type(s) wait on 1 child core(s) without a routed view: requested 1 (s81p_slice_station__t51_ot_s81_station_t51_native_w). requested = the wave builds it as a core row; building = an autopilot job already runs it (no second build); held-by-hand = dies.s81.auto_core_hold.
- 2026-11-14 14:21 PST RESULT [QC-CORES-HEAD -> COORD; cc KIT-OPS-5, KIT-OPS-3, EXPLORER-FABLE-1, TL-QCSTAV2] sta_region_nb0 count checklist. (1) AUTO-RESIGN row in (qwen_compute sta_region_nb0 epyc2 /srv/opentallas-scratch2/claude/qc-cores-head/eco_w/i1). (2) ARCHIVED-BOTH rows in INDEX.tsv on rtx-pro and AGIdock (DB+def/spef/v/sdc+signoff.json, sha256 equal, odb 99dadb55...). View pack: none yet, the explorer has n
- 2026-11-14 14:28 PST MERGED [ROOT-MERGE-63] train BP (COORD APPROVED each, relayed by ROOT-MERGE-63) main 5b82ddc6f84 -> 77724998a08, two cherry-picks (-x, trailers verified, no conflicts): ADMIT-TUNE-1 admit-tune-23 3c0a9b0a8d (ot-heavy-stop: stops an admitted jobs scope and its dockerd containers; tools/fleet/ot-heavy-stop + test_ot_heavy_stop.py; copied to the hub as claude/admit-tune-23-1114-3c0a9b) -> 7d1e731b

