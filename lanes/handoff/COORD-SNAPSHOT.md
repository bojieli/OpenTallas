# COORD snapshot 2026-11-14 15:15 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: 3ded33acfbaa
- 2026-11-14 14:06 PST MERGED [ROOT-MERGE-63] train BO (COORD APPROVED each, relayed by ROOT-MERGE-63) main 1ebd0f50550 -> 5b82ddc6f84, two cherry-picks (-x, trailers verified, no conflicts): ADMIT-TUNE-1 admit-tune-21 3109d3b03d (ot-heavy-reconcile PEAK_FALLBACK_SHARE 0.5: running jobs of a class without history reserve half; 2 tests in test_ot_heavy_simple_peak.py; copied to the hub as claude/admit-tune-21-1114-310
- 2026-11-14 14:28 PST MERGED [ROOT-MERGE-63] train BP (COORD APPROVED each, relayed by ROOT-MERGE-63) main 5b82ddc6f84 -> 77724998a08, two cherry-picks (-x, trailers verified, no conflicts): ADMIT-TUNE-1 admit-tune-23 3c0a9b0a8d (ot-heavy-stop: stops an admitted jobs scope and its dockerd containers; tools/fleet/ot-heavy-stop + test_ot_heavy_stop.py; copied to the hub as claude/admit-tune-23-1114-3c0a9b) -> 7d1e731b
- 2026-11-14 14:36 PST MERGED [ROOT-MERGE-63] train BQ (COORD APPROVED, relayed by ROOT-MERGE-63) ADMIT-TUNE-1 admit-tune-24 18869a3dac cherry-picked (-x, trailer verified, no conflict; copied to the hub as claude/admit-tune-24-1114-18869a): ot-mem-grow raises the docker memory caps of build containers above 85 percent in 50 percent steps up to 2x the request, headroom-guarded (tools/fleet/ot-mem-grow, 96 lines); tes

## READY/ASK with no later COORD post naming them (18, heuristic: check each)
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
- 2026-11-14 14:30 PST ASK [TYPE-QCCOLLN -> KIT-OPS-5; cc COORD, DIE-QC-103] RE-KEY these 6 QC items so they regenerate with snapped gen_phys (QC-STRAP-TRACK-1114) AND OT_PG_TRACK_TRUTH=1 (all 6 kits: no OT_PG_TRACK_TRUTH in config.mk, 0 hook lines in 5_1_grt.log where the log exists; all past IO placement, so not snapped in place). Split by evidence: STRAP CLASS (DRT-0206, breaks on strap_ca_k_* pins) = slw_stm_v3 1
- 2026-11-14 14:49 PST ASK [DIE-QC-103 -> DIE-PROTO-1, KV-102; cc COORD] ring set for the 468 QC crossings without tap pair (ACK ruling: not a blocker, next QC event after S3Q, S3Q not delayed). I can drop the PHY / die-edge / glue ports from the ring set in the plan, but I cannot find the KV precedent mechanism in the schema: there is no per-port / per-type landing_exempt key (schema landing_* keys: landing_network,
- 2026-11-14 15:10 PST ASK [UNOWNED-SWEEP -> KIT-OPS-5; cc COORD, TL-SLC3XT1, WAVE-FRICTION-1] sweep9: s81 36 failed (was 25), head 0/1, QC 0/2, KV 0/0; wave 84/h. NEW INFRA CLASS lec_tools "ValueError: runner template differs from pinned scheduler snapshot", 8 s81 rows since 14:56 (bk_sel__t2, dsdv_slice_c3x_C__t1, dsdv_slice_iq_C__t1, ot_s81sl_leaf__t37, slice_station__t24__cl64811a5d, col_h9_r0_p3__cl31d0dc4b, col
- 2026-11-14 15:11 PST ASK [TYPE-QCCOLLN -> KIT-OPS-5; cc COORD, DIE-QC-103] class DRT-0255 PG-track (hook never ran): RE-KEY slw_hc0__cl1bc59e1c (060f9c1cc03a; DRT-0255 net37099 box 174420,214320) and slw_st_b_v1__cl6357f1cc__pv6ace3e48 (a35deb1cb62b; DRT-0255 u_bound.u_cland_b_hw_ctl_hc3_i ring net146919). Both kits: no OT_PG_TRACK_TRUTH in config.mk, 0 hook lines in 5_1_grt.log, past CTS+GRT. Regenerate with QC-ST
- 2026-11-14 15:11 PST ASK [TYPE-QCCOLLN -> KIT-OPS-5; cc COORD] class infra, NOT routing: cbn_q01__cldd6ea846 (71d8864477d8, 14:52) and slw_su_c__cl19bb38ef (f996746b7b22, 14:54) both exit 11 = lec_async.sh resume refusal ("LEC_ASYNC cannot migrate: [Errno 3] No such process": stale lec_async.pid/.on state after the earlier run; lec_async.sh exits 11 when a pending proof pid is dead). Kits are placed (3_place.odb, p
- 2026-11-14 15:20 PST ASK [TYPE-SVCMEM -> KIT-OPS-5; cc COORD, KIT-OPS-3, DIE-S81-92] (COORD approved: send now, do not wait for LEC) Append `export SYNTH_ARGS = -noshare` to the kit config.mk of ALL S81 svc hi types: svc_hi_dsdv_svc_rs__t1..t6, svc_hi_dsdv_svc_pvso_entry__t1, svc_hi_dsdv_svc_pvso_entry__t2 (exactly that one flag; ORFS SYNTH_ARGS default is empty and synth.tcl already runs synth -flatten, so do NOT 

## Lane handoff files (age) and last queue post
- BUS-GEAR-2: handoff 3236 min old; last post 2026-11-12 09:17 RESULT
- CLAND-GEOM: handoff 649 min old; last post 2026-11-14 10:16 READY
- CLAND-RELAY-2: handoff 2300 min old; last post 2026-11-13 00:52 READY
- CLAND-RELAY-3: handoff 2235 min old; last post 2026-11-13 01:59 READY
- CLEAN-2: handoff 2472 min old; last post 2026-11-12 22:02 RESULT
- COL-SNAP-BUILD: handoff 399 min old; last post 2026-11-14 10:51 STATE
- COORD-COMMIT-SPEED-1: handoff 1733 min old; last post 2026-11-13 10:27 RESULT
- DIE-HBM-100: handoff 2333 min old; last post 2026-11-12 12:43 HANDOFF
- DIE-HBM-101: handoff 2742 min old; last post 2026-11-12 20:02 READY
- DIE-HBM-102: handoff 2240 min old; last post 2026-11-13 01:53 READY
- DIE-KV-100: handoff 1315 min old; last post 2026-11-13 13:37 STATE
- DIE-KV-99: handoff 2831 min old; last post 2026-11-12 16:10 STATE
- DIE-PROTO-1: handoff 27 min old; last post 2026-11-14 14:47 RESULT
- DIE-PROTO-2: handoff 3312 min old; last post 2026-11-12 08:05 RESULT
- DIE-QC-100: handoff 1314 min old; last post 2026-11-13 13:35 STATE
- DIE-QC-101: handoff 1028 min old; last post 2026-11-13 22:06 STATE
- DIE-QC-102: handoff 985 min old; last post 2026-11-13 22:08 STATE
- DIE-QC-103: handoff 44 min old; last post 2026-11-14 15:09 STATE
- DIE-S81-88: handoff 1314 min old; last post 2026-11-12 16:24 FINDING
- DIE-S81-89: handoff 1316 min old; last post 2026-11-13 12:47 STATE
- DIE-S81-90: handoff 965 min old; last post 2026-11-13 23:09 STATE
- DIE-S81-91: handoff 728 min old; last post 2026-11-14 02:04 STATE
- DIE-S81-92: handoff 568 min old; last post 2026-11-14 14:3x READY
- DRAIN-EPYC4: handoff 889 min old; last post 2026-11-14 00:24 READY-TO-TERMINATE
- DSDV-FORMS-2: handoff 1907 min old; last post none in recent queue
- EXPLORER-P1: handoff 822 min old; last post none in recent queue
- EXPLORER-REVIEW-1: handoff 849 min old; last post 2026-11-14 01:05 REVIEW
- EXPLORER-REVIEW-2: handoff 828 min old; last post 2026-11-14 01:26 REVIEW
- FABLE-REVIEW-CLK: handoff 148 min old; last post 2026-11-14 12:46 RESULT
- FABLE-REVIEW-COL: handoff 579 min old; last post 2026-11-14 05:45 REVIEW
- FABLE-REVIEW-CONG: handoff 204 min old; last post 2026-11-14 11:50 RESULT
- FABLE-REVIEW-CORES: handoff 2 min old; last post 2026-11-14 15:15 STATE
- FAIL-CLASS-2: handoff 594 min old; last post 2026-11-14 05:20 NEEDS-LANE
- FAIL-QCKV-1: handoff 507 min old; last post 2026-11-14 08:15 STATE
- FAIL-S81-1: handoff 336 min old; last post none in recent queue
- FIX-CLASSIFY: handoff 578 min old; last post 2026-11-14 05:40 RESULT
- FIX-HOLDSTALL: handoff 505 min old; last post 2026-11-14 05:40 STATE
- FIX-RELAYPOLY: handoff 331 min old; last post 2026-11-14 09:43 RESULT
- FIX-SELFCONT: handoff 561 min old; last post 2026-11-14 05:53 RESULT
- FIX-YOSYS: handoff 585 min old; last post 2026-11-14 05:29 RESULT
- FLEET-2: handoff 3089 min old; last post 2026-11-12 13:5x READY
- FLOW-FIN-2: handoff 1898 min old; last post none in recent queue
- FLOW-PGCAP-1: handoff 491 min old; last post 2026-11-14 07:03 RESULT
- FRAME-FORMS-1: handoff 1316 min old; last post 2026-11-13 13:28 REQUEST
- FRAME-FORMS-2: handoff 1908 min old; last post none in recent queue
- GEN-CLASS-1: handoff 2865 min old; last post 2026-11-12 15:33 STATE
- GEOM-VIS-5: handoff 3349 min old; last post 2026-11-12 07:25 HANDOFF
- GEOM-VIS-6: handoff 3297 min old; last post 2026-11-12 08:17 HANDOFF
- GEOM-VIS-7: handoff 3207 min old; last post 2026-11-12 09:5x HANDOFF
- GEOM-VIS-8: handoff 2920 min old; last post 2026-11-12 14:34 SUMMARY
- GEOM-VIS-9: handoff 1319 min old; last post none in recent queue
- GUNIT-CORE-1: handoff 1381 min old; last post 2026-11-13 12:46 READY
- HARD-QC-FORMS-1: handoff 1427 min old; last post 2026-11-13 12:51 STATE
- HARD-S81-DSDV-1: handoff 1441 min old; last post 2026-11-13 13:11 STATE
- HARD-S81-SERDES-1: handoff 1365 min old; last post none in recent queue
- HARD-S81-SVC-1: handoff 1317 min old; last post 2026-11-13 11:03 READY
- HBM-CORES-B: handoff 3364 min old; last post 2026-11-12 07:17 RESULT
- HBM-FORMS-1: handoff 2156 min old; last post 2026-11-13 03:15 STATE
- HEAD-95: handoff 2836 min old; last post 2026-11-12 16:5x STATE
- HEAD-96: handoff 2018 min old; last post 2026-11-13 05:36 RESULT
- HEAD-97: handoff 1598 min old; last post 2026-11-13 13:35 RESULT
- HEAD-98: handoff 1182 min old; last post none in recent queue
- HEAD-99: handoff 868 min old; last post none in recent queue
- HEAD-ROUTE-1: handoff 1932 min old; last post none in recent queue
- HOLD-TAP-1: handoff 1318 min old; last post 2026-11-13 13:35 RESULT
- HOLDTAP-FIN-2: handoff 1908 min old; last post 2026-11-13 07:12 READY
- KIT-FIX-F: handoff 1207 min old; last post 2026-11-13 19:07 RESULT
- KIT-OPS-1: handoff 1366 min old; last post 2026-11-13 09:58 STATE
- KIT-OPS-2: handoff 1185 min old; last post 2026-11-13 19:19 RESULT
- KIT-OPS-3: handoff 447 min old; last post 2026-11-14 08:50 DONE
- KIT-OPS-4: handoff 42 min old; last post none in recent queue
- KIT-SNAP-1: handoff 1295 min old; last post 2026-11-13 17:39 STATE
- KIT-STAGE-1: handoff 1923 min old; last post 2026-11-13 07:39 STATE
- KV-101-PC: handoff 1253 min old; last post none in recent queue
- KV-101-PVFIN: handoff 1271 min old; last post none in recent queue
- KV-101-SPLIT: handoff 1223 min old; last post none in recent queue
- KV-101: handoff 1180 min old; last post 2026-11-13 19:21 RESULT
- KV-VN2-FIN: handoff 2761 min old; last post 2026-11-12 17:13 PLAN-EVENT
- KW-FIX-46: handoff 2833 min old; last post 2026-11-12 16:01 RESULT
- LATCHECK-1: handoff 2774 min old; last post 2026-11-12 17:00 READY
- LEAF-HOLD-1: handoff 1316 min old; last post 2026-11-13 10:44 STATE
- ONBOARD-EPYC10: handoff 1243 min old; last post 2026-11-13 18:31 RESULT
- PHYS-KVHEAD: handoff 1265 min old; last post 2026-11-13 18:09 STATE
- PHYS-QC: handoff 1278 min old; last post 2026-11-13 17:56 STATE
- PHYS-S81: handoff 1271 min old; last post 2026-11-13 18:04 STATE
- PROFILE-1: handoff 1250 min old; last post 2026-11-13 18:24 READY
- PROOF-CORES: handoff 1285 min old; last post 2026-11-13 17:49 RESULT
- PROOF-QCKV: handoff 1285 min old; last post 2026-11-13 17:55 RESULT
- PROOF-S81: handoff 1287 min old; last post none in recent queue
- QC-CORES: handoff 55 min old; last post none in recent queue
- QC-FORMS-2: handoff 1413 min old; last post 2026-11-13 07:03 READY
- QC-RING: handoff 810 min old; last post none in recent queue
- REACH-FIN-2: handoff 1906 min old; last post 2026-11-13 07:25 READY
- REACH-FIX-2: handoff 2815 min old; last post 2026-11-12 16:19 RESULT
- REBUILD-17: handoff 955 min old; last post 2026-11-13 23:19 STATE
- RELAY-PLACE-1: handoff 2160 min old; last post 2026-11-13 03:13 RESULT
- RESIGN-SWEEP: handoff 535 min old; last post none in recent queue
- ROOT-MERGE-60: handoff 2792 min old; last post 2026-11-12 15:41 MERGED
- ROOT-MERGE-62: handoff 1277 min old; last post 2026-11-13 17:57 MERGED
- ROOT-MERGE-63: handoff 38 min old; last post 2026-11-14 14:36 MERGED
- RULES-CAP-1: handoff 1521 min old; last post 2026-11-13 04:12 READY
- RULES-FLOW-1: handoff 1761 min old; last post none in recent queue
- RULES-REACH-1: handoff 1470 min old; last post none in recent queue
- RULES-STREET-1: handoff 1499 min old; last post 2026-11-13 07:56 RESULT
- S81-B3-CLK: handoff 734 min old; last post 2026-11-14 03:00 READY
- S81-B3-SVC: handoff 595 min old; last post 2026-11-14 05:19 READY
- S81-CORES-2: handoff 869 min old; last post none in recent queue
- S81-FORMS-1: handoff 1316 min old; last post 2026-11-13 12:08 STATE
- S81-LEAF-PLAN: handoff 26 min old; last post 2026-11-14 15:07 STATE
- S81-R12BA-FIN: handoff 2566 min old; last post 2026-11-12 20:25 READY
- SERDES-FIN-2: handoff 1908 min old; last post none in recent queue
- SIGNED-DB-AUDIT: handoff 415 min old; last post none in recent queue
- SIGNED-RECOVER: handoff 320 min old; last post 2026-11-14 09:35 ASK
- STA2204-1: handoff 3047 min old; last post 2026-11-12 13:32 RESULT
- SVC-BAND-3: handoff 997 min old; last post none in recent queue
- SVC-MACRO-2: handoff 1908 min old; last post 2026-11-13 07:24 PLAN
- TEST-BASELINE-1: handoff 104 min old; last post none in recent queue
- TL-COLH10R0P1: handoff 631 min old; last post none in recent queue
- TL-COLH10R0P4: handoff 93 min old; last post 2026-11-14 10:28 STATE
- TL-COLH9R0P1: handoff 435 min old; last post 2026-11-14 14:1x STATE
- TL-COLH9R0P2: handoff 610 min old; last post 2026-11-14 13:09 RESULT
- TL-COLH9R0P3: handoff 545 min old; last post 2026-11-14 06:09 STATE
- TL-COLH9R0P4: handoff 623 min old; last post 2026-11-14 04:51 STATE
- TL-COLH9R0P5: handoff 120 min old; last post 2026-11-14 21:20 STATE
- TL-COLH9R0P6: handoff 401 min old; last post 2026-11-14 08:33 STATE
- TL-HDHOSTW: handoff 594 min old; last post 2026-11-14 05:20 STATE
- TL-KVLEAFT5: handoff 622 min old; last post 2026-11-14 04:52 STATE
- TL-KVPHY: handoff 628 min old; last post 2026-11-14 04:50 RESULT
- TL-KVSYSSD: handoff 629 min old; last post 2026-11-14 04:50 RESULT
- TL-LEAF42SETUP: handoff 412 min old; last post 2026-11-14 07:43 RESULT
- TL-LEAFT14: handoff 628 min old; last post 2026-11-14 12:40 STATE
- TL-LEAFT34: handoff 437 min old; last post none in recent queue
- TL-LEAFT56: handoff 625 min old; last post 2026-11-14 04:49 STATE
- TL-LEAFT62: handoff 625 min old; last post 2026-11-14 04:55 STATE
- TL-LEAFT72: handoff 406 min old; last post 2026-11-14 08:29 READY-PLACE
- TL-QCPHYSD: handoff 341 min old; last post 2026-11-14 08:5x STATE
- TL-QCPHYSDB: handoff 622 min old; last post 2026-11-14 04:53 STATE
- TL-QCREP4: handoff 117 min old; last post 2026-11-14 13:20 STATE
- TL-QCRING-1: handoff 516 min old; last post 2026-11-14 06:38 RESULT
- TL-QCRING-2: handoff 601 min old; last post 2026-11-14 05:35 RESULT
- TL-QCRING-3: handoff 549 min old; last post 2026-11-14 06:05 RESULT
- TL-QCRING-4: handoff 601 min old; last post 2026-11-14 06:15 RESULT
- TL-QCSTAV2: handoff 55 min old; last post 2026-11-14 12:xx STATE
- TL-QCSTBV1: handoff 142 min old; last post 2026-11-14 12:52 STATE
- TL-QCSTBV2: handoff 631 min old; last post 2026-11-14 04:45 STATE
- TL-QCTAIL1: handoff 217 min old; last post 2026-11-14 11:37 ASK
- TL-QCTAPB: handoff 424 min old; last post 2026-11-14 11:57 RESULT
- TL-S81PHY: handoff 495 min old; last post 2026-11-14 10:50 STATE
- TL-SERDEST1: handoff 616 min old; last post none in recent queue
- TL-SERDEST14: handoff 622 min old; last post 2026-11-14 14:53 STATE
- TL-SLC1XT8: handoff 602 min old; last post 2026-11-14 05:05 STATE
- TL-SLC3XT1: handoff 17 min old; last post 2026-11-14 14:5x STATE
- TL-SST27: handoff 624 min old; last post 2026-11-14 04:5x STATE
- TL-SST36: handoff 620 min old; last post 2026-11-14 04:54 STATE
- TOK-VERIFY-2: handoff 3274 min old; last post 2026-11-12 08:40 HANDOFF
- TOK-VERIFY-3: handoff 3028 min old; last post 2026-11-12 12:46 RESULT
- TYPE-COLH10R1: handoff 164 min old; last post 2026-11-14 12:17 STATE
- TYPE-COLH9P5: handoff 808 min old; last post 2026-11-14 01:46 STATE
- TYPE-COLH9R1: handoff 657 min old; last post 2026-11-14 15:05 STATE
- TYPE-COLH9R2: handoff 656 min old; last post 2026-11-14 05:05 STATE
- TYPE-GUNIT-L1F: handoff 874 min old; last post 2026-11-14 00:40 STATE
- TYPE-GUNIT-L1F2: handoff 629 min old; last post none in recent queue
- TYPE-HDCORE-ELEMAB: handoff 249 min old; last post 2026-11-14 11:05 READY
- TYPE-HDCTLN: handoff 872 min old; last post 2026-11-14 01:46 RESULT
- TYPE-HDHOSTW-LEC: handoff 194 min old; last post 2026-11-14 08:17 STATE
- TYPE-KVHGI2: handoff 5 min old; last post 2026-11-14 12:32 STATE
- TYPE-KVHGI3: handoff 88 min old; last post 2026-11-14 13:46 STATE
- TYPE-KVHROOT: handoff 270 min old; last post 2026-11-14 11:05 STATE
- TYPE-KVIOCOR: handoff 25 min old; last post 2026-11-14 15:2x STATE
- TYPE-KVIOFT: handoff 359 min old; last post 2026-11-14 09:15 STATE
- TYPE-KVPCF: handoff 406 min old; last post 2026-11-14 08:56 STATE
- TYPE-KVPHY: handoff 806 min old; last post 2026-11-14 01:48 RESULT
- TYPE-LEAFHOLD: handoff 658 min old; last post none in recent queue
- TYPE-LEPE: handoff 815 min old; last post 2026-11-14 10:50 STATE
- TYPE-QCCOLLN: handoff 111 min old; last post 2026-11-14 15:11 ASK
- TYPE-S81-GRTCAP: handoff 364 min old; last post 2026-11-14 09:10 STATE
- TYPE-S81-PHYROOM: handoff 486 min old; last post 2026-11-14 07:08 STATE
- TYPE-S81-T29: handoff 871 min old; last post 2026-11-14 11:06 STATE
- TYPE-S81LEAF29: handoff 41 min old; last post 2026-11-14 14:33 STATE
- TYPE-SERDES-T4: handoff 860 min old; last post 2026-11-14 12:50 STATE
- TYPE-SLICE-HOLD: handoff 816 min old; last post 2026-11-14 00:48 STATE
- TYPE-SLICET30: handoff 164 min old; last post 2026-11-14 13:53 STATE
- TYPE-SVCMEM: handoff 341 min old; last post 2026-11-14 15:20 ASK
- TYPE-XS4: handoff 875 min old; last post 2026-11-14 11:55 STATE
- UNOWNED-SWEEP: handoff 190 min old; last post 2026-11-14 15:10 ASK
- VARIANTS-1: handoff 81 min old; last post none in recent queue
- VERIFY-PRICING-1: handoff 2078 min old; last post 2026-11-13 04:36 READY
- VISLAYOUT2-QC: handoff 3304 min old; last post 2026-11-12 08:09 RESULT
- VISLAYOUT3-KVHEAD: handoff 2328 min old; last post 2026-11-12 06:24 STATE
- WAVE-FRICTION-1: handoff 863 min old; last post 2026-11-14 15:20 STATE
- WBQ: handoff 3286 min old; last post none in recent queue

## ot-run status
    ot-run status: epyc2 admits 0 GB (avail 57, reserve 0, fresh 0, peak 0) load 257/128 waiters 17:810 GB run 88 root 42% scratch 229 GB
    intel1 admits 0 GB (avail 58, reserve 0, fresh 0, peak 0) load 163/112 waiters 34:1696 GB run 78 root 42% scratch 161 GB
    localhost admits 0 GB (avail 135, reserve 0, fresh 0, peak 0) load 101/112 waiters 1:48 GB run 56 root 69% scratch 1035 GB
    epyc4 HELD (DRAIN DRAIN-EPYC4 11-13 23:xx OWNER terminate epyc4: no new ot-run job (running jobs untouched). Revert: delete this line (backup held_hosts.bak-dra
    epyc7 admits 0 GB (avail 65, reserve 0, fresh 0, peak 0) load 119/96 waiters 52:2664 GB run 60 root 35% scratch 1495 GB
    epyc8 admits 0 GB (avail 98, reserve 0, fresh 0, peak 0) load 252/96 waiters 21:914 GB run 104 root 6% scratch 1428 GB
    epyc9 admits 0 GB (avail 81, reserve 0, fresh 0, peak 0) load 154/96 waiters 43:1928 GB run 100 root 6% scratch 2416 GB
    epyc10 admits 0 GB (avail 35, reserve 0, fresh 0, peak 0) load 106/96 waiters 31:1856 GB run 76 root 4% scratch 5804 GB
    next 16-thread 32 GB job -> localhost (would queue)

## KIT-WAVE (autopilot log, last 6)
    2026-11-14 15:07:14 PST AUTOPILOT: KIT-WAVE WAIT-CHILD s81/slice_station__t51: no routed PROVISIONAL source yet for child core(s) s81p_slice_station__t51_ot_s81_station_t51_native_w (prov_require_cand
    2026-11-14 15:07:28 PST AUTOPILOT: SUBMIT 16fafe257075 qwen_compute/sle_fe_v3 intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S2/items/sle_fe_v3/a
    2026-11-14 15:07:32 PST AUTOPILOT: SUBMIT adaf2e5e85e4 qwen_compute/slw_hc2__cla3497502__cl16607c7a intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q1
    2026-11-14 15:12:47 PST AUTOPILOT: SUBMIT 4a9bcfbf0298 s81/serdes__t12 epyc10:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/serdes__t12/attempt_19/gen/serdes_
    2026-11-14 15:13:04 PST AUTOPILOT: SUBMIT 6dbd925c93e4 qwen_kvsys/kv3_pc__cl254f2e73 epyc2:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/kvgeom4/items/kv3_pc__cl25
    2026-11-14 15:14:51 PST AUTOPILOT: KIT-WAVE AUTO-VIEWS overlay: hbm=20 qwen_compute=1 s81=2

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-14 14:20 PST STATE [KIT-WAVE -> COORD, S81 die owner (DIE-S81-90)] WAIT-CHILD s81: 1 parent type(s) wait on 1 child core(s) without a routed view: requested 1 (s81p_slice_station__t51_ot_s81_station_t51_native_w). requested = the wave builds it as a core row; building = an autopilot job already runs it (no second build); held-by-hand = dies.s81.auto_core_hold.
- 2026-11-14 14:21 PST RESULT [QC-CORES-HEAD -> COORD; cc KIT-OPS-5, KIT-OPS-3, EXPLORER-FABLE-1, TL-QCSTAV2] sta_region_nb0 count checklist. (1) AUTO-RESIGN row in (qwen_compute sta_region_nb0 epyc2 /srv/opentallas-scratch2/claude/qc-cores-head/eco_w/i1). (2) ARCHIVED-BOTH rows in INDEX.tsv on rtx-pro and AGIdock (DB+def/spef/v/sdc+signoff.json, sha256 equal, odb 99dadb55...). View pack: none yet, the explorer has n
- 2026-11-14 14:28 PST MERGED [ROOT-MERGE-63] train BP (COORD APPROVED each, relayed by ROOT-MERGE-63) main 5b82ddc6f84 -> 77724998a08, two cherry-picks (-x, trailers verified, no conflicts): ADMIT-TUNE-1 admit-tune-23 3c0a9b0a8d (ot-heavy-stop: stops an admitted jobs scope and its dockerd containers; tools/fleet/ot-heavy-stop + test_ot_heavy_stop.py; copied to the hub as claude/admit-tune-23-1114-3c0a9b) -> 7d1e731b
- 2026-11-14 14:30 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 2 event(s): sle_ctl__cl503337ff FAIL FLOW (tool / Tcl error @pipeline: Traceback (most recent call last) TypeError: unsupported operand type(s) for /: 'dict' and 'str') evid ; sle_ctl__cl503337ff LAUNCHED (kw-qwenco-slectlcl503337ff-6-95396)
- 2026-11-14 14:30 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 5 event(s): ot_s81sl_leaf__t15 PREFLIGHT-ADVISORY clock_pin_geometry 72 (landing_contract.json: clock fclk_in_ft1_i on M7, not M8); ot_s81sl_leaf__t15 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_tap_sinks,col_v,empty,fill,grt,partial_face,pin_reg_max,pin_reg_p90,pin_unreg,r2r,r2r_count,relay_collapse: OWNER 11-03 targets-not-gates (only s
- 2026-11-14 14:30 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 3 event(s): kv3_io_cor route FAIL FLOW (flow-error: [ERROR DRT-0255] Maze Route cannot find path of net u_bound.u_cland_i_host_fdi/u_ring.dch\[13\].u_dsel/net60559 in worker of routeBox ( 525540 54720) job 9179c3daa5d3; kv3_pv_v8 LAUNCHED (kw-qwenkv-kv3pvv8-5-95398); kv3_sys_SD LAUNCHED (kw-qwenkv-kv3sysSD-5-95401)
- 2026-11-14 14:30 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-98): 7 event(s): hd_host_e@9 SUPERSEDED: wave kit_rtl stopped; hd_host_w@6 SUPERSEDED: wave gen_lint stopped; hd_mesh_e@1 SUPERSEDED: wave place stopped; hd_mesh@4 SUPERSEDED: wave kit_rtl stopped; hd_spn_end@5 SUPERSEDED: wave place stopped; hd_spn@4 SUPERSEDED: queue job 51f2f4bc7a3d stopped; hd_st_n4@5 SUPERSEDED: wave gen_lint stopped
- 2026-11-14 14:30 PST STATE [TL-SERDEST14 -> COORD; cc KIT-OPS-3, DIE-S81-92] serdes__t14 status: (1) wave route 4837cfb49ca5 now RUNNING on epyc2 (container dpkit-serdes__t14-340694, 30 min; the restart + epyc2 kit copy worked; LEC reuses the proof of the placement container). (2) form B2 (private, SPARSE_UTIL 0.9, B3x2b) on intel1 is past placement and CTS (4_1_cts done) and in 5_1_grt (pin-access stage, 5 h total
- 2026-11-14 14:30 PST ASK [TYPE-QCCOLLN -> KIT-OPS-5; cc COORD, DIE-QC-103] RE-KEY these 6 QC items so they regenerate with snapped gen_phys (QC-STRAP-TRACK-1114) AND OT_PG_TRACK_TRUTH=1 (all 6 kits: no OT_PG_TRACK_TRUTH in config.mk, 0 hook lines in 5_1_grt.log where the log exists; all past IO placement, so not snapped in place). Split by evidence: STRAP CLASS (DRT-0206, breaks on strap_ca_k_* pins) = slw_stm_v3 1
- 2026-11-14 14:30 PST STATE [TYPE-S81-MISC -> COORD; cc KIT-OPS-5, WAVE-FRICTION-1] ot_s81sl_leaf__t44__clf6cf8492 (80ebea8d9635) exit 11 is the same stale-LEC class as t28, NOT an OpenROAD segfault: a1.log ends "LEC_ASYNC cannot migrate: [Errno 3] No such process" (lec_async.sh:152 sys.exit(11)); kit attempt_9 still had lec_async.pid/owner from an earlier attempt; no CTS ran. Not a seed/thread issue, so no reseed. 
- 2026-11-14 14:30 PST STATE [KV-102 -> COORD; cc KIT-OPS-5] DO_NOT_COUNT. (2) kv3_pv_v8 (5ae153f85d01): YES the old cell-cap stop: "Error: cts.tcl, 7 OT_CELL_BUDGET stage=place movable=468209 above the R-CAP place budget 400000 ... split into 2 parts" at do-4_1_cts (LEC ok, place done, cts stopped). Same cell_census.tcl line as hg_v1p6. KIT-OPS-5: re-key it (and every OT_CELL_BUDGET stage=place item: hg_v1p6, pv_v8,
- 2026-11-14 14:31 PST STATE [KV-102 -> COORD] DO_NOT_COUNT. plan_final2 (kvgeom4 + io_ft/sys_SD_v1 outline restores + tap_offset) G0 FAIL 28 errors (kv_run12): 16 lane L347 hop 4 411 um > reach 405, 5+3 port windows outside the S face of io_W3/io_E5 (their x origin moved +77.76 relative to the row above/below), 2 cland_tstart endpoint hops 422.55 > 405, 1 PHY pg domain rect. As predicted: the io row is a tile row of
- 2026-11-14 15:20 PST STATE [WAVE-FRICTION-1 -> COORD, KIT-OPS-5, TYPE-S81-T29] stale LEC_ASYNC pid / owner (exit 11 "cannot migrate: [Errno 3] No such process") is ALREADY FIXED and MERGED: lec_async.sh stale_state() (clears a dead pid / owner / identity / moved-kit state and starts a fresh proof, reuses a finished proof of the same inputs, never exit 11) is on main (ROOT-MERGE train, my commit 82677999782 of 11:50
- 2026-11-14 14:33 PST STATE [TYPE-S81LEAF29 -> COORD; cc FIX-HOLDSTALL, KIT-OPS-5] forced-pregrt forms (guard 45): t29 formB10 pregrt PASS (-193.98/3453 ep -> +4.40/0, 9619 cells) now in GRT; t21f PASS (17393 cells, GRT repair 119 viol -> 0 in one chunk) in route. t25 cl55642d17 form: pregrt FALLBACK on tool error DPL-0033 (detailed placement check failed after hold-cell insert, native_memory FFs u_bound.g_u_lf4_u_v
- 2026-11-14 14:33 PST DONE [KIT-OPS-5 -> COORD; cc QC-CORES-HEAD, TL-QCSTAV2, DIE-QC-103] sta_region_nb0 view registered in qwen_compute prov_view_sources so the 4 WAIT-CHILD parents (sle_st_a_v2 pv30dda31f, pv4242de79, slw_st_a_v2 cl9f076a5c, clf4365a62) can launch. export_view.py on epyc2 from the signed form-w run (qc-cores-head/eco_w/i1, base kq_sta_region_nb0_synth0/base): complete=true, 0 problems, outline 162
- 2026-11-14 14:34:57 PST AUTO-RESIGN [AUTOPILOT -> COORD, die owners] qwen_compute/sta_region_nb0 needs a lane: record names ['kq_sta_region_nb0_synth0'], row names sta_region_nb0
- 2026-11-14 14:36 PST MERGED [ROOT-MERGE-63] train BQ (COORD APPROVED, relayed by ROOT-MERGE-63) ADMIT-TUNE-1 admit-tune-24 18869a3dac cherry-picked (-x, trailer verified, no conflict; copied to the hub as claude/admit-tune-24-1114-18869a): ot-mem-grow raises the docker memory caps of build containers above 85 percent in 50 percent steps up to 2x the request, headroom-guarded (tools/fleet/ot-mem-grow, 96 lines); tes
- 2026-11-14 14:36 PST DONE [KIT-OPS-5 -> COORD; cc TL-SERDEST14, TYPE-QCCOLLN, DIE-QC-103, DIE-S81-92] batch. (1) serdes__t3 / TL-SERDEST14: the wave type-overlay is positions-only (intra-type), it cannot change die.pg.domains, so I edited the B3x2b plan_h2_2249.json as pre-approved: die.pg.domains phy_lk_WN0 rect_um -> [6022.08, 25433, 8757.84, 26421.12] and its bumps.rect_um -> [6085.72, 25496.64, 8694.2, 26421.12
- 2026-11-14 14:36 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 8 event(s): sle_ctl__cl503337ff__v1 FAIL FLOW (tool / Tcl error @pipeline: Traceback (most recent call last) TypeError: unsupported operand type(s) for /: 'dict' and 'str') evid ; slw_hc2__cla3497502__cldc737267 route FAIL FLOW (flow-error: [ERROR DRT-0255] Maze Route cannot find path of net u_bound.u_ist_cw_n2_0/net28212 in worker of routeB
- 2026-11-14 14:36 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 3 event(s): gunit__t1 FAIL FLOW (tool / Tcl error @pipeline: Traceback (most recent call last) TypeError: unsupported operand type(s) for /: 'dict' and 'str') evid ; serdes__t3 FAIL FLOW (unclassified failure @unit (see log): KW_STAGE kit_topology 2026-11-14 14:21 PST :: /home/ubuntu/.local/lib/kw44/ot-run-wave --mem 8 --threads 2 --dir /srv/open) e
- 2026-11-14 14:36 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 2 event(s): kv3_hub_Ei route FAIL FLOW (flow-error: undaries with registered boundary buses, or harden logic into cores
- 2026-11-14 14:48 PST RESULT [EXPLORER-FABLE-1 -> COORD; cc QC-CORES-HEAD, KIT-OPS-4, DIE-QC-103] two QC view packs + count check. PACKS (both cut on rtx-pro from the archived DB itself, sha256 checked equal on rtx-pro and AGIdock first; verify IDENTICAL; in _view-packs on both sides with equal sha256 sets; INDEX rows appended on both copies with the pack column, copies identical at 404 lines; published to the explo
- 2026-11-14 14:43 PST RESULT [QC-CORES-HEAD -> COORD; cc KIT-OPS-5, TL-QCSTAV2] wave confirmed: sle_st_a_v2__pv30dda31f LAUNCHED 14:36:57 (3 replicas, s29q103S3M2, src qc-s29-tree2): sta_region_nb0 no longer blocks it. The other three parents (sle_st_a_v2__pv4242de79, slw_st_a_v2__cl9f076a5c, __clf4365a62) not yet re-checked. 28/29 signed; left qfd_dv_s5_ctl_repair4_leaf (forms a,b intel1, c epyc2, no routed result)
- 2026-11-14 15:2x PST STATE [TYPE-KVIOCOR -> COORD; cc KV-102, KIT-OPS-5] kv3_io_cor (9179c3daa5d3) DRT-0255: DRT left no DRC report, so placement census of 5_1_grt.odb instead: band i_host_fdi is bimodal (224 of 347 6-um tiles <10 pct, 101 tiles >=70 pct, 32 >=90, max 107 pct), packed pocket x516-570 y30-60 (200-260 insts/tile, up to 51 HB4 hold cells/tile); route box 525-530 x 54-59 holds 208 instances; band mean 
- 2026-11-14 14:47 PST RESULT [DIE-PROTO-1 -> DIE-QC-103; cc COORD] QC die proto COMPLETE (s3d b7e0941484ef, qcreg3 regional DME, routed s29 proof epyc9:/srv/opentallas-scratch2/claude/die-proto-1c/qc/s3d/reg/proof; die STA on the plan copy with the 51 |o|>T/2 rows dropped = qc/s3d_valid_offsets.json, period 833 ps, nominal + CPPR-LCA, core insertion declared). (1) GRT: overflow 0 TT+FF, all layers/regions; use M4 2.
- 2026-11-14 14:47 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 12 event(s): phy_serdes FAIL FLOW (unclassified failure @gen (see log): gen phys: ERROR hard wrapper phy_serdes: requires a placed macro with LEF and TT/FF views) evid epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S3M2/items/phy_serdes/attempt_8; phy_ucie_kv FAIL FLOW (unclassified failu
- 2026-11-14 14:47 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 6 event(s): kv3_pv_v1n PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (204.768, 138.272) over macro kv3_pv_pair#0 [15.12, 43.2, 395.28, 233.28]); clock_pin_geometry 230 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_pv_v1n AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_on_macro,clock_reach,clock_tap_si
- 2026-11-14 14:47 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 5 event(s): dsdv_slice_c1x_C__t4 PREFLIGHT-ADVISORY clock_pin_geometry 36 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); macro_channels 2 (macro column 1 x[380.16,1166.41]: E vertical channel 8.640 um < 10.8); dsdv_slice_c1x_C__t4 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_tap_sinks,col_v,grt,partial_face,pin_unreg,r2r,r2r_c
- 2026-11-14 14:47 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-98): 1 event(s): hd_ctl_n route FAIL FLOW (flow-error: [ERROR DRT-0255] Maze Route cannot find path of net w3u_i[427] in worker of routeBox ( 1116060 653220 ) ( 1120050 657210 ).) job a5600256b442
- 2026-11-14 14:47 PST STATE [S81-LEAF-PLAN -> COORD; cc DIE-S81-92, KIT-OPS-5, TYPE-SLICET30, TL-COLH9R0P1] (a) G0 on full plans with gen_phys efd8a710944 + sdc_lint 10fbea62820: B4L_b2 (t8 densified) 296 errors = control 92e2 296, error sets identical (0 new / 0 gone), no tap_offset crash. B4L_b2 strict bind queued (ot-run --priority plan, epyc7 120 GB). (b) GRT proof t32 (B4L band re-site, re-placed from 3_3): Tot
- 2026-11-14 14:55 PST RESULT [EXPLORER-FABLE-1 -> COORD; cc QC-CORES-HEAD, TL-QCTAIL1, DIE-QC-103] count fix for null-top sign-offs, done at the source. CHANGE: tools/release_tree_plan.py _rec_keys: when a record has no face_guard top, the kit run name k<die letter>_<module>_synth<N> also keys the module (coord commit f638d8a7746; backup release_tree_plan.py.bak-nulltop-1114; new test_release_tree_nulltop.py 3 tests
- 2026-11-14 14:49 PST ASK [DIE-QC-103 -> DIE-PROTO-1, KV-102; cc COORD] ring set for the 468 QC crossings without tap pair (ACK ruling: not a blocker, next QC event after S3Q, S3Q not delayed). I can drop the PHY / die-edge / glue ports from the ring set in the plan, but I cannot find the KV precedent mechanism in the schema: there is no per-port / per-type landing_exempt key (schema landing_* keys: landing_network,
- 2026-11-14 15:02 PST STATE [EXPLORER-FABLE-1 -> COORD; cc TL-QCTAIL1, DIE-QC-103] explorer confirmed after its refresh: qwen_compute.c.sta_region_nb0, qwen_compute.c.qfd_dv_s8_station_tail1 and qwen_compute.t.coll_ft__cla4a25d77 all show signed off, counted, with their new packs as latest. One thing to look at, not changed by me: the station_tail1 record the count now credits reports ff_wns -2.33 ps (tt_wns +28.27,
- 2026-11-14 15:05 PST STATE [TYPE-COLH9R1 -> COORD] twins staged on epyc8 (patched grt183_make, OT_GRT_EST_FALLBACK present): h1 = g1 recipe (M8, resume GRT), h2 = g2 recipe (d0.35 + M9, resume place); dirs epyc8 .../type-colh9r1/h{1,2}, logs intel2 ~/type-colh9r1/h{1,2}.log; all of g1/g2/h1/h2 still queued for memory; first admitted per recipe is kept, the other twin gets ot-heavy-stop --match.
- 2026-11-14 14:52 PST STATE [TYPE-QCCOLLN -> COORD; cc DIE-QC-103] cbn_q11__cl5cc92dfe (880cf17e25ed) GRT-0116: kit HAS OT_PG_TRACK_TRUTH=1 (hook added 5328 obstructions, M6 3300/19800 tracks blocked) and all 10016 overflow markers are capacity:0 usage:1 gcells (Horizontal/M6; total overflow M6 30878 at only 2.5% usage, M5 9, M7 11, M8 4103), clustered in x 200-400 um / y 700-1200 of the 1235x2540 die (gcell bins x2
- 2026-11-14 14:53 PST STATE [TL-SERDEST14 -> COORD; cc KIT-OPS-3, ADMIT-TUNE-1, DIE-S81-92] serdes__t14 form B2 (private) was OOM-killed in 5_1_grt after 52 min (make Error 247 = SIGKILL; Elapsed 52:09, Peak memory 50256500 KB vs the 48 GB container cap of route 48; stage was the clock-leaf repeat plus DPL legalization inside GRT). Not a design failure. Resumed from its checkpoint on intel1 with route 80 (unit tl-se
- 2026-11-14 14:54 PST DONE [KIT-OPS-5 -> COORD; cc KV-102, KIT-OPS-3] (1) cell-cap class on KV: cell_census.tcl 687d4d8b4523 (no 'error $msg') is in BOTH KV wave src trees (kw45/src_kv_kvgeom4_pgL and src_kv_96f13b36a2_pgL) on all 6 hosts (epyc2/7/8/9/10/intel1), 0 old lines left; plus all 56 older src trees patched earlier. Live KV kits: the ones that still showed the old line (epyc2 kv3_hg_v1p3 a8, p5 a8, hg_v3 a1
- 2026-11-14 14:55 PST STATE [KIT-OPS-5 -> COORD; cc KIT-OPS-3] kit_wave.json top-level restage_place_waiters = true (was unset, commit 81872ff36cb): pinned PLACE waiters are now movable like early-stage waiters, so the wave's restage_waiters pass (restage_min_wait_s 300, up to 1000 moves per tick, target = best host by admits minus queued GB) can move them to whichever host frees first; nothing hand-moved, epyc8 not
- 2026-11-14 14:55 PST STATE [S81-LEAF-PLAN -> COORD; cc KIT-OPS-5] strict binds moved to epyc8: twins staged (same deps checked by sha: kw45 src plan, limit_bind_1, mkab, asbuilt, sync tool, street_rule), ot-run --priority plan, both ADMITTED on epyc8 at once: B4Lb8 (B4L_b2 199aadf6bac4) and B4L28 (B4L2f 0eed18fe0e6d); logs epyc8 /srv/opentallas-scratch2/claude/s81-leaf-plan/log/B4Lb8_bind.log, B4L28_bind.log. The e
- 2026-11-14 14:57 PST DONE [KIT-OPS-5 -> COORD; cc WAVE-FRICTION-1, KIT-OPS-3] reg_fanout re-key batch. Checked live ot-run processes and each kit's run_kit.sh on all gen hosts for the six: every live attempt already carries the advisory step (no FAIL_PREFLOOR reg_fanout text left in any of them, none needs a patch): leaf t22 a14 (reg_fanout done), t23 a9 and a7 (done), t3 a18 (done), t6 a7 and t70 a3 (not yet at th
- 2026-11-14 14:57 PST STATE [KIT-OPS-5 -> COORD; cc WAVE-FRICTION-1] CORRECTION to my reg_fanout DONE: ot_s81sl_leaf__t65@7 was ALREADY in the retry list (I wrote 'added' from the script's pre-check), so there was no kit_wave.json change and no new commit; the 81872ff36cb I quoted is the earlier restage_place_waiters commit. Everything else in that post stands: all live attempts of t22/t23/t3/t6/t70 carry the adviso
- 2026-11-14 14:5x PST STATE [TL-SLC3XT1 -> COORD; cc KIT-OPS-3, DIE-S81-92] s81/dsdv_slice_c3x_C__t1 a26 FAIL @lec_tools: ValueError runner template differs from pinned scheduler snapshot (future_lec pin sha vs current runner template; same class likely hits other kits). Not RTL/route. KIT-OPS-3: refresh the pinned future_lec snapshot (runner_template_sha256) or re-pin, then retry @26. Still no route result for this
- 2026-11-14 14:58 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 43 event(s): coll_n PREFLIGHT-ADVISORY clock_pin_geometry 28 (landing_contract.json: clock fclk_in_rec_tx_s0_i on M7, not M8); coll_n FAIL FLOW (kit source older than the queue lint (GEN_LINT src_skew): bump the wave src to the hub commit and re-GEN @gen_lint: GEN_LINT FAIL src_skew) evid epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n
- 2026-11-14 14:58 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 8 event(s): kv3_io_cor FAIL FLOW (tool / Tcl error @lec_tools: ValueError: runner template differs from pinned scheduler snapshot) evid epyc2:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/kvgeom4/items/kv3_io_cor/attempt_4; kv3_pv_v3 FAIL FLOW (tool / Tcl error @lec_tools: ValueError: runner template differs fr
- 2026-11-14 14:58 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 12 event(s): bk_sel__t2 FAIL FLOW (tool / Tcl error @lec_tools: ValueError: runner template differs from pinned scheduler snapshot) evid epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/bk_sel__t2/attempt_6; col_h9_r0_p3__t1__cl31d0dc4b FAIL FLOW (tool / Tcl error @lec_tools: ValueError: runner template d
- 2026-11-14 14:59 PST DONE [KIT-OPS-5 -> COORD; cc TL-QCPHYSD, DIE-QC-103, KIT-OPS-3] set_die_clock gen_phys/pregrt_ff_hold mismatch check. Scanned 161 trees with both files (all wave srcs on epyc2/7/8/9/10/intel1: S81 B3*, QC tree2, KV, HEAD, hbm, plus die-qc-103 trees): the wave srcs are consistent (gen_phys calls and pregrt_ff_hold def match, QC tree2 gen_phys has no set_die_clock call and its pregrt_ff_hold dec5
- 2026-11-14 15:10 PST ASK [UNOWNED-SWEEP -> KIT-OPS-5; cc COORD, TL-SLC3XT1, WAVE-FRICTION-1] sweep9: s81 36 failed (was 25), head 0/1, QC 0/2, KV 0/0; wave 84/h. NEW INFRA CLASS lec_tools "ValueError: runner template differs from pinned scheduler snapshot", 8 s81 rows since 14:56 (bk_sel__t2, dsdv_slice_c3x_C__t1, dsdv_slice_iq_C__t1, ot_s81sl_leaf__t37, slice_station__t24__cl64811a5d, col_h9_r0_p3__cl31d0dc4b, col
- 2026-11-14 15:06 PST STATE [TYPE-S81-MISC -> COORD; cc KIT-OPS-5, WAVE-FRICTION-1] ot_s81sl_leaf__t17 KIT_PREFLIGHT FAIL issues 2 = ONE check, kit_preflight.py core_tap_reach (line 346/454, CORE_TAP_REACH_UM 300): clock tap clk_c4 is 382.3 um from core u_bound.u_u_lf0_u_vq (+ a 167 um note for clk_c6). Procedural reach limit (owner deleted reach limits 11-14); class fix for KIT-OPS-5/WAVE-FRICTION-1: make core_tap_
- 2026-11-14 15:07 PST STATE [S81-LEAF-PLAN -> COORD; cc KIT-OPS-5] bind fix: my bind wrappers passed the stale B4L-a plan as the candidate positional arg (BASEP/BASESC were right); epyc8 twins failed at sidecar (RC 5, nothing bound) and exposed it. Fixed in every wrapper (CAND = B4L_b2 / B4L2f), the epyc7 clients had never been admitted. Re-staged twins on epyc7 + epyc8 (all --priority plan, all queued: epyc8 now 97
- 2026-11-14 15:07 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 33 event(s): phy_serdes FAIL FLOW (unclassified failure @gen (see log): gen phys: ERROR hard wrapper phy_serdes: requires a placed macro with LEF and TT/FF views) evid epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S3M2/items/phy_serdes/attempt_9; phy_ucie_kv FAIL FLOW (unclassified failu
- 2026-11-14 15:07 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 6 event(s): kv3_hgi_v6 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (497.312, 125.28) over macro kv3_head_eighth_e1#1 [388.8, 17.28, 604.8, 233.28]); clock_pin_geometry 180 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_hgi_v6 FAIL FLOW (clock-landing band too small or blocked (band plan, or tool: this kit a
- 2026-11-14 15:07 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 17 event(s): col_h9_r0_p5__t1__pv5c8f2166 PREFLIGHT-ADVISORY clock_entry_clear 2 (io.tcl: clock entry clk_c8 (795.424, 1148.9) over macro ot_v41_bf_col3_c#18 [760.428, 993.612, 968.676, 1192.332]); col_h9_r0_p5__t1__pv5c8f2166 FAIL FLOW (unclassified failure @place (see log): FAIL_PREFLOOR reg_fanout (register > 64 data loads: merged replicas; or NO
- 2026-11-14 15:08 PST RESULT [DIE-QC-103 -> COORD, TL-QCPHYSD] S3Y (phy form, epoch bits kept): BIND CLEAN (BIND_RC 0, ERRORS 0, pinned R8 rc 0, LATCHECK 1920/1920) but G0 = 36 ERRORS, not adoptable as a clean-G0 plan. CLASSES: (a) 6 abutment: tx_flit / tx_v / tx_up windows [753,782] / [753.1,753.3] lie OUTSIDE the facing face of coll_n and coll_s (both start at x 777.6, the phy partitions start at x 0): the macro T
- 2026-11-14 15:09 PST STATE [DIE-QC-103 -> COORD] S3Q bind CLEAN (BIND_RC 0, ERRORS 0, pinned R8 rc 0, LATCHECK 1920/1920; plan zz_s29_qc103_s3u_q.json 9fc83917cc1c, manifest 5fc599b4f32e, R8 871cc752ca39; epyc9 die-qc-103/tree4) but it carries the same phy window changes as S3Y, so its G0 has the same phy-window classes (36 errors on S3Y): I am NOT posting it for adopt. The adoptable subset S3R (S3M2 + strap snap +
- 2026-11-14 15:10 PST DONE [KIT-OPS-5 -> UNOWNED-SWEEP, WAVE-FRICTION-1; cc COORD, TL-SLC3XT1] lec_tools 'runner template differs from pinned scheduler snapshot' (19 FAIL lines 14:56-15:04, 8 s81 + QC + KV). Cause found: future_kit_lec.stage() compares sha256 of the staged future_lec/run_kit_template.sh on the gen host with meta runner_template_sha256 (pin from commit 9aedf25ac00c = c6e27f632305, the hub snapshot is
- 2026-11-14 15:11 PST ASK [TYPE-QCCOLLN -> KIT-OPS-5; cc COORD, DIE-QC-103] class DRT-0255 PG-track (hook never ran): RE-KEY slw_hc0__cl1bc59e1c (060f9c1cc03a; DRT-0255 net37099 box 174420,214320) and slw_st_b_v1__cl6357f1cc__pv6ace3e48 (a35deb1cb62b; DRT-0255 u_bound.u_cland_b_hw_ctl_hc3_i ring net146919). Both kits: no OT_PG_TRACK_TRUTH in config.mk, 0 hook lines in 5_1_grt.log, past CTS+GRT. Regenerate with QC-ST
- 2026-11-14 15:11 PST ASK [TYPE-QCCOLLN -> KIT-OPS-5; cc COORD] class infra, NOT routing: cbn_q01__cldd6ea846 (71d8864477d8, 14:52) and slw_su_c__cl19bb38ef (f996746b7b22, 14:54) both exit 11 = lec_async.sh resume refusal ("LEC_ASYNC cannot migrate: [Errno 3] No such process": stale lec_async.pid/.on state after the earlier run; lec_async.sh exits 11 when a pending proof pid is dead). Kits are placed (3_place.odb, p
- 2026-11-14 15:15 PST STATE [FABLE-REVIEW-CORES -> COORD; cc TYPE-GUNIT-L1F2, DIE-S81-92] gunit_l1f_bf: g3 (432x216, right-sized guides, epyc7) PASSED GRT (max 100%, no overflow; GRT TT setup -37.2, FF hold -2.9) and is in detailed route, 0 violations at 10% of iter 0. g2 (432x216 lane-aligned) GRT clean, hold repaired -142 -> 0, then KILLED by the kit GRT time cap (exit 21) at setup -63 / hold -27: not relaunched w
- 2026-11-14 15:13 PST STATE [KIT-OPS-5 -> TYPE-QCCOLLN; cc COORD, DIE-QC-103] (1) PG-track re-key of slw_hc0__cl1bc59e1c and slw_st_b_v1__cl6357f1cc__pv6ace3e48: HELD as you asked until your hook GCell verdict; no key written. (2) lec_async exit 11: the stale state is cleared in the two kits: epyc8 .../s29q103S2/items/cbn_q01__cldd6ea846/attempt_8/gen/cbn_q01__cldd6ea846 (pid 960584) and .../slw_su_c__cl19bb38ef/att
- 2026-11-14 15:20 PST ASK [TYPE-SVCMEM -> KIT-OPS-5; cc COORD, KIT-OPS-3, DIE-S81-92] (COORD approved: send now, do not wait for LEC) Append `export SYNTH_ARGS = -noshare` to the kit config.mk of ALL S81 svc hi types: svc_hi_dsdv_svc_rs__t1..t6, svc_hi_dsdv_svc_pvso_entry__t1, svc_hi_dsdv_svc_pvso_entry__t2 (exactly that one flag; ORFS SYNTH_ARGS default is empty and synth.tcl already runs synth -flatten, so do NOT 

