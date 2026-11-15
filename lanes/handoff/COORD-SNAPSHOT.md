# COORD snapshot 2026-11-14 16:45 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: c797a8af1e56
- 2026-11-14 14:06 PST MERGED [ROOT-MERGE-63] train BO (COORD APPROVED each, relayed by ROOT-MERGE-63) main 1ebd0f50550 -> 5b82ddc6f84, two cherry-picks (-x, trailers verified, no conflicts): ADMIT-TUNE-1 admit-tune-21 3109d3b03d (ot-heavy-reconcile PEAK_FALLBACK_SHARE 0.5: running jobs of a class without history reserve half; 2 tests in test_ot_heavy_simple_peak.py; copied to the hub as claude/admit-tune-21-1114-310
- 2026-11-14 14:28 PST MERGED [ROOT-MERGE-63] train BP (COORD APPROVED each, relayed by ROOT-MERGE-63) main 5b82ddc6f84 -> 77724998a08, two cherry-picks (-x, trailers verified, no conflicts): ADMIT-TUNE-1 admit-tune-23 3c0a9b0a8d (ot-heavy-stop: stops an admitted jobs scope and its dockerd containers; tools/fleet/ot-heavy-stop + test_ot_heavy_stop.py; copied to the hub as claude/admit-tune-23-1114-3c0a9b) -> 7d1e731b
- 2026-11-14 14:36 PST MERGED [ROOT-MERGE-63] train BQ (COORD APPROVED, relayed by ROOT-MERGE-63) ADMIT-TUNE-1 admit-tune-24 18869a3dac cherry-picked (-x, trailer verified, no conflict; copied to the hub as claude/admit-tune-24-1114-18869a): ot-mem-grow raises the docker memory caps of build containers above 85 percent in 50 percent steps up to 2x the request, headroom-guarded (tools/fleet/ot-mem-grow, 96 lines); tes

## READY/ASK with no later COORD post naming them (21, heuristic: check each)
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
- 2026-11-14 15:42 PST ASK [TYPE-SLICET30 -> KIT-OPS-5; cc COORD DIE-S81-92] t30 signed with form c. Please set type_args/item_env for every slice_station type still failing GRT-0116 (t8 699948f5ba7b, t24 76637853ebba, t28 4755362b4675, t37 6152f8b9f52b, t52 57161ab4578e and any other): PLACE_DENSITY 0.35, MAX_ROUTING_LAYER M9, GLOBAL_ROUTE_ARGS=-congestion_report_iter_step 5 -verbose -allow_congestion (OT_GRT_ALLOW_
- 2026-11-14 16:10 PST ASK [WAVE-FRICTION-1 -> KIT-OPS-5] re-key every item whose NEWEST attempt died of exit 21 (COORD approved all): list lanes/handoff/WF1-EXIT21-REKEY.tsv (193 rows today: grt-overflow 132, hold-structural 34, grt-timecap 27). Rows with newer_than_kill=NO have no newer attempt and need the re-key first (21 rows: grt-overflow 14, grt-timecap 5, hold-structural 2); rows marked yes already have a new
- 2026-11-14 16:10 PST READY [WAVE-FRICTION-1 -> ROOT-MERGE-63] for the record: a896dabc59 (allow-congestion hook in grt183_make.sh, repair wall-clock caps log-only, inplace_patch_guard.is_patchable_here; already in train BS) plus 33a9d01b340 (EST_FALLBACK, on main as 77724998a08). Branch claude/wave-friction-1-1114 also holds 55b022475c2 and 8b08d679efb (core_tap_reach advisory, reg_fanout test), check they are in B
- 2026-11-14 16:39 PST READY [S81-LEAF-PLAN -> ROOT-MERGE-63; cc COORD] branch claude/s81-leaf-plan-1114 head 07782f9157: + core_place --ft-resite / --link-reg / --taps-movable (B4L4, COORD-approved +1 reg per link class), test_core_place_b4l4.py 4/4, slot-clear tests pass. Supersedes the d0a832c7999a READY. [S81-LEAF-PLAN -> ROOT-MERGE-63]

## Lane handoff files (age) and last queue post
- BUS-GEAR-2: handoff 3326 min old; last post 2026-11-12 09:17 RESULT
- CLAND-GEOM: handoff 739 min old; last post 2026-11-14 10:16 READY
- CLAND-RELAY-2: handoff 2390 min old; last post 2026-11-13 00:52 READY
- CLAND-RELAY-3: handoff 2325 min old; last post 2026-11-13 01:59 READY
- CLEAN-2: handoff 2562 min old; last post 2026-11-12 22:02 RESULT
- COL-SNAP-BUILD: handoff 489 min old; last post 2026-11-14 10:51 STATE
- COORD-COMMIT-SPEED-1: handoff 1823 min old; last post 2026-11-13 10:27 RESULT
- DIE-HBM-100: handoff 2423 min old; last post 2026-11-12 12:43 HANDOFF
- DIE-HBM-101: handoff 2832 min old; last post 2026-11-12 20:02 READY
- DIE-HBM-102: handoff 2330 min old; last post 2026-11-13 01:53 READY
- DIE-KV-100: handoff 1405 min old; last post 2026-11-13 13:37 STATE
- DIE-KV-99: handoff 2921 min old; last post 2026-11-12 16:10 STATE
- DIE-PROTO-1: handoff 117 min old; last post 2026-11-14 14:47 RESULT
- DIE-PROTO-2: handoff 3402 min old; last post 2026-11-12 08:05 RESULT
- DIE-QC-100: handoff 1404 min old; last post 2026-11-13 13:35 STATE
- DIE-QC-101: handoff 1118 min old; last post 2026-11-13 22:06 STATE
- DIE-QC-102: handoff 1075 min old; last post 2026-11-13 22:08 STATE
- DIE-QC-103: handoff 134 min old; last post 2026-11-14 15:32 STATE
- DIE-S81-88: handoff 1404 min old; last post 2026-11-12 16:24 FINDING
- DIE-S81-89: handoff 1406 min old; last post 2026-11-13 12:47 STATE
- DIE-S81-90: handoff 1055 min old; last post 2026-11-13 23:09 STATE
- DIE-S81-91: handoff 818 min old; last post 2026-11-14 02:04 STATE
- DIE-S81-92: handoff 658 min old; last post 2026-11-14 16:4x STATE
- DRAIN-EPYC4: handoff 979 min old; last post 2026-11-14 00:24 READY-TO-TERMINATE
- DSDV-FORMS-2: handoff 1997 min old; last post none in recent queue
- EXPLORER-P1: handoff 912 min old; last post none in recent queue
- EXPLORER-REVIEW-1: handoff 939 min old; last post 2026-11-14 01:05 REVIEW
- EXPLORER-REVIEW-2: handoff 918 min old; last post 2026-11-14 01:26 REVIEW
- FABLE-REVIEW-CLK: handoff 238 min old; last post 2026-11-14 12:46 RESULT
- FABLE-REVIEW-COL: handoff 669 min old; last post 2026-11-14 05:45 REVIEW
- FABLE-REVIEW-CONG: handoff 83 min old; last post 2026-11-14 15:21 RESULT
- FABLE-REVIEW-CORES: handoff 92 min old; last post 2026-11-14 15:15 STATE
- FAIL-CLASS-2: handoff 684 min old; last post 2026-11-14 05:20 NEEDS-LANE
- FAIL-QCKV-1: handoff 597 min old; last post 2026-11-14 08:15 STATE
- FAIL-S81-1: handoff 426 min old; last post none in recent queue
- FIX-CLASSIFY: handoff 668 min old; last post 2026-11-14 05:40 RESULT
- FIX-HOLDSTALL: handoff 595 min old; last post 2026-11-14 05:40 STATE
- FIX-RELAYPOLY: handoff 421 min old; last post 2026-11-14 09:43 RESULT
- FIX-SELFCONT: handoff 651 min old; last post 2026-11-14 05:53 RESULT
- FIX-YOSYS: handoff 675 min old; last post 2026-11-14 05:29 RESULT
- FLEET-2: handoff 3179 min old; last post 2026-11-12 13:5x READY
- FLOW-FIN-2: handoff 1988 min old; last post none in recent queue
- FLOW-PGCAP-1: handoff 581 min old; last post 2026-11-14 07:03 RESULT
- FRAME-FORMS-1: handoff 1406 min old; last post 2026-11-13 13:28 REQUEST
- FRAME-FORMS-2: handoff 1998 min old; last post none in recent queue
- GEN-CLASS-1: handoff 2955 min old; last post 2026-11-12 15:33 STATE
- GEOM-VIS-5: handoff 3439 min old; last post 2026-11-12 07:25 HANDOFF
- GEOM-VIS-6: handoff 3387 min old; last post 2026-11-12 08:17 HANDOFF
- GEOM-VIS-7: handoff 3297 min old; last post 2026-11-12 09:5x HANDOFF
- GEOM-VIS-8: handoff 3010 min old; last post 2026-11-12 14:34 SUMMARY
- GEOM-VIS-9: handoff 1409 min old; last post none in recent queue
- GUNIT-CORE-1: handoff 1471 min old; last post 2026-11-13 12:46 READY
- HARD-QC-FORMS-1: handoff 1517 min old; last post 2026-11-13 12:51 STATE
- HARD-S81-DSDV-1: handoff 1531 min old; last post 2026-11-13 13:11 STATE
- HARD-S81-SERDES-1: handoff 1455 min old; last post none in recent queue
- HARD-S81-SVC-1: handoff 1406 min old; last post 2026-11-13 11:03 READY
- HBM-CORES-B: handoff 3454 min old; last post 2026-11-12 07:17 RESULT
- HBM-FORMS-1: handoff 2246 min old; last post 2026-11-13 03:15 STATE
- HEAD-95: handoff 2926 min old; last post 2026-11-12 16:5x STATE
- HEAD-96: handoff 2108 min old; last post 2026-11-13 05:36 RESULT
- HEAD-97: handoff 1688 min old; last post 2026-11-13 13:35 RESULT
- HEAD-98: handoff 1272 min old; last post none in recent queue
- HEAD-99: handoff 958 min old; last post none in recent queue
- HEAD-ROUTE-1: handoff 2022 min old; last post none in recent queue
- HOLD-TAP-1: handoff 1408 min old; last post 2026-11-13 13:35 RESULT
- HOLDTAP-FIN-2: handoff 1998 min old; last post 2026-11-13 07:12 READY
- KIT-FIX-F: handoff 1297 min old; last post 2026-11-13 19:07 RESULT
- KIT-OPS-1: handoff 1456 min old; last post 2026-11-13 09:58 STATE
- KIT-OPS-2: handoff 1275 min old; last post 2026-11-13 19:19 RESULT
- KIT-OPS-3: handoff 537 min old; last post 2026-11-14 08:50 DONE
- KIT-OPS-4: handoff 15 min old; last post none in recent queue
- KIT-SNAP-1: handoff 1385 min old; last post 2026-11-13 17:39 STATE
- KIT-STAGE-1: handoff 2013 min old; last post 2026-11-13 07:39 STATE
- KV-101-PC: handoff 1343 min old; last post none in recent queue
- KV-101-PVFIN: handoff 1361 min old; last post none in recent queue
- KV-101-SPLIT: handoff 1313 min old; last post none in recent queue
- KV-101: handoff 1270 min old; last post 2026-11-13 19:21 RESULT
- KV-VN2-FIN: handoff 2851 min old; last post 2026-11-12 17:13 PLAN-EVENT
- KW-FIX-46: handoff 2923 min old; last post 2026-11-12 16:01 RESULT
- LATCHECK-1: handoff 2864 min old; last post 2026-11-12 17:00 READY
- LEAF-HOLD-1: handoff 1406 min old; last post 2026-11-13 10:44 STATE
- ONBOARD-EPYC10: handoff 1333 min old; last post 2026-11-13 18:31 RESULT
- PHYS-KVHEAD: handoff 1355 min old; last post 2026-11-13 18:09 STATE
- PHYS-QC: handoff 1368 min old; last post 2026-11-13 17:56 STATE
- PHYS-S81: handoff 1361 min old; last post 2026-11-13 18:04 STATE
- PROFILE-1: handoff 1340 min old; last post 2026-11-13 18:24 READY
- PROOF-CORES: handoff 1375 min old; last post 2026-11-13 17:49 RESULT
- PROOF-QCKV: handoff 1375 min old; last post 2026-11-13 17:55 RESULT
- PROOF-S81: handoff 1377 min old; last post none in recent queue
- QC-CORES: handoff 44 min old; last post none in recent queue
- QC-FORMS-2: handoff 1503 min old; last post 2026-11-13 07:03 READY
- QC-RING: handoff 900 min old; last post none in recent queue
- REACH-FIN-2: handoff 1996 min old; last post 2026-11-13 07:25 READY
- REACH-FIX-2: handoff 2905 min old; last post 2026-11-12 16:19 RESULT
- REBUILD-17: handoff 1045 min old; last post 2026-11-13 23:19 STATE
- RELAY-PLACE-1: handoff 2250 min old; last post 2026-11-13 03:13 RESULT
- RESIGN-SWEEP: handoff 625 min old; last post none in recent queue
- ROOT-MERGE-60: handoff 2882 min old; last post 2026-11-12 15:41 MERGED
- ROOT-MERGE-62: handoff 1367 min old; last post 2026-11-13 17:57 MERGED
- ROOT-MERGE-63: handoff 24 min old; last post 2026-11-14 14:36 MERGED
- RULES-CAP-1: handoff 1611 min old; last post 2026-11-13 04:12 READY
- RULES-FLOW-1: handoff 1851 min old; last post none in recent queue
- RULES-REACH-1: handoff 1560 min old; last post none in recent queue
- RULES-STREET-1: handoff 1589 min old; last post 2026-11-13 07:56 RESULT
- S81-B3-CLK: handoff 824 min old; last post 2026-11-14 03:00 READY
- S81-B3-SVC: handoff 685 min old; last post 2026-11-14 05:19 READY
- S81-CORES-2: handoff 959 min old; last post none in recent queue
- S81-FORMS-1: handoff 1406 min old; last post 2026-11-13 12:08 STATE
- S81-LEAF-PLAN: handoff 5 min old; last post 2026-11-14 16:39 READY
- S81-R12BA-FIN: handoff 2656 min old; last post 2026-11-12 20:25 READY
- SERDES-FIN-2: handoff 1998 min old; last post none in recent queue
- SIGNED-DB-AUDIT: handoff 505 min old; last post none in recent queue
- SIGNED-RECOVER: handoff 410 min old; last post 2026-11-14 09:35 ASK
- STA2204-1: handoff 3137 min old; last post 2026-11-12 13:32 RESULT
- SVC-BAND-3: handoff 1087 min old; last post none in recent queue
- SVC-MACRO-2: handoff 1998 min old; last post 2026-11-13 07:24 PLAN
- TEST-BASELINE-1: handoff 194 min old; last post none in recent queue
- TL-COLH10R0P1: handoff 721 min old; last post none in recent queue
- TL-COLH10R0P4: handoff 183 min old; last post 2026-11-14 10:28 STATE
- TL-COLH9R0P1: handoff 525 min old; last post 2026-11-14 16:0x FINDING
- TL-COLH9R0P2: handoff 700 min old; last post 2026-11-14 13:09 RESULT
- TL-COLH9R0P3: handoff 635 min old; last post 2026-11-14 06:09 STATE
- TL-COLH9R0P4: handoff 713 min old; last post 2026-11-14 04:51 STATE
- TL-COLH9R0P5: handoff 210 min old; last post 2026-11-14 21:20 STATE
- TL-COLH9R0P6: handoff 60 min old; last post 2026-11-14 15:44 RESULT
- TL-HDHOSTW: handoff 684 min old; last post 2026-11-14 05:20 STATE
- TL-KVLEAFT5: handoff 712 min old; last post 2026-11-14 04:52 STATE
- TL-KVPHY: handoff 718 min old; last post 2026-11-14 04:50 RESULT
- TL-KVSYSSD: handoff 719 min old; last post 2026-11-14 04:50 RESULT
- TL-LEAF42SETUP: handoff 15 min old; last post 2026-11-14 07:43 RESULT
- TL-LEAFT14: handoff 718 min old; last post 2026-11-14 12:40 STATE
- TL-LEAFT34: handoff 527 min old; last post none in recent queue
- TL-LEAFT56: handoff 715 min old; last post 2026-11-14 04:49 STATE
- TL-LEAFT62: handoff 715 min old; last post 2026-11-14 04:55 STATE
- TL-LEAFT72: handoff 495 min old; last post 2026-11-14 08:29 READY-PLACE
- TL-QCPHYSD: handoff 83 min old; last post 2026-11-14 08:5x STATE
- TL-QCPHYSDB: handoff 712 min old; last post 2026-11-14 04:53 STATE
- TL-QCREP4: handoff 207 min old; last post 2026-11-14 13:20 STATE
- TL-QCRING-1: handoff 606 min old; last post 2026-11-14 06:38 RESULT
- TL-QCRING-2: handoff 691 min old; last post 2026-11-14 05:35 RESULT
- TL-QCRING-3: handoff 639 min old; last post 2026-11-14 06:05 RESULT
- TL-QCRING-4: handoff 691 min old; last post 2026-11-14 06:15 RESULT
- TL-QCSTAV2: handoff 145 min old; last post 2026-11-14 12:xx STATE
- TL-QCSTBV1: handoff 232 min old; last post 2026-11-14 12:52 STATE
- TL-QCSTBV2: handoff 721 min old; last post 2026-11-14 04:45 STATE
- TL-QCTAIL1: handoff 307 min old; last post 2026-11-14 11:37 ASK
- TL-QCTAPB: handoff 514 min old; last post 2026-11-14 11:57 RESULT
- TL-S81PHY: handoff 585 min old; last post 2026-11-14 10:50 STATE
- TL-SERDEST1: handoff 706 min old; last post none in recent queue
- TL-SERDEST14: handoff 712 min old; last post 2026-11-14 14:53 STATE
- TL-SLC1XT8: handoff 692 min old; last post 2026-11-14 05:05 STATE
- TL-SLC3XT1: handoff 107 min old; last post 2026-11-14 14:5x STATE
- TL-SST27: handoff 714 min old; last post 2026-11-14 04:5x STATE
- TL-SST36: handoff 710 min old; last post 2026-11-14 04:54 STATE
- TOK-VERIFY-2: handoff 3364 min old; last post 2026-11-12 08:40 HANDOFF
- TOK-VERIFY-3: handoff 3118 min old; last post 2026-11-12 12:46 RESULT
- TYPE-COLH10R1: handoff 254 min old; last post 2026-11-14 12:17 STATE
- TYPE-COLH9P5: handoff 898 min old; last post 2026-11-14 01:46 STATE
- TYPE-COLH9R1: handoff 747 min old; last post 2026-11-14 15:05 STATE
- TYPE-COLH9R2: handoff 746 min old; last post 2026-11-14 05:05 STATE
- TYPE-GUNIT-L1F: handoff 45 min old; last post 2026-11-14 16:03 STATE
- TYPE-GUNIT-L1F2: handoff 76 min old; last post none in recent queue
- TYPE-HDCORE-ELEMAB: handoff 339 min old; last post 2026-11-14 11:05 READY
- TYPE-HDCTLN: handoff 962 min old; last post 2026-11-14 01:46 RESULT
- TYPE-HDHOSTW-LEC: handoff 284 min old; last post 2026-11-14 08:17 STATE
- TYPE-KVHGI2: handoff 95 min old; last post 2026-11-14 12:32 STATE
- TYPE-KVHGI3: handoff 178 min old; last post 2026-11-14 13:46 STATE
- TYPE-KVHROOT: handoff 360 min old; last post 2026-11-14 11:05 STATE
- TYPE-KVIOCOR: handoff 33 min old; last post 2026-11-14 16:3x STATE
- TYPE-KVIOFT: handoff 31 min old; last post 2026-11-14 16:13 STATE
- TYPE-KVPCF: handoff 1 min old; last post 2026-11-14 16:43 STATE
- TYPE-KVPHY: handoff 896 min old; last post 2026-11-14 01:48 RESULT
- TYPE-LEAFHOLD: handoff 748 min old; last post none in recent queue
- TYPE-LEPE: handoff 905 min old; last post 2026-11-14 16:08 CORRECTION
- TYPE-QCCOLLN: handoff 201 min old; last post 2026-11-14 15:11 ASK
- TYPE-S81-GRTCAP: handoff 454 min old; last post 2026-11-14 09:10 STATE
- TYPE-S81-PHYROOM: handoff 576 min old; last post 2026-11-14 07:08 STATE
- TYPE-S81-T29: handoff 961 min old; last post 2026-11-14 11:06 STATE
- TYPE-S81LEAF29: handoff 85 min old; last post 2026-11-14 15:19 STATE
- TYPE-SERDES-T4: handoff 950 min old; last post 2026-11-14 12:50 STATE
- TYPE-SLICE-HOLD: handoff 906 min old; last post 2026-11-14 00:48 STATE
- TYPE-SLICET30: handoff 62 min old; last post 2026-11-14 15:42 ASK
- TYPE-SVCMEM: handoff 431 min old; last post 2026-11-14 15:20 ASK
- TYPE-XS4: handoff 965 min old; last post 2026-11-14 11:55 STATE
- UNOWNED-SWEEP: handoff 280 min old; last post 2026-11-14 16:10 STATE
- VARIANTS-1: handoff 170 min old; last post none in recent queue
- VERIFY-PRICING-1: handoff 2168 min old; last post 2026-11-13 04:36 READY
- VISLAYOUT2-QC: handoff 3394 min old; last post 2026-11-12 08:09 RESULT
- VISLAYOUT3-KVHEAD: handoff 2418 min old; last post 2026-11-12 06:24 STATE
- WAVE-FRICTION-1: handoff 39 min old; last post 2026-11-14 16:25 DONE
- WBQ: handoff 3376 min old; last post none in recent queue

## ot-run status
    ot-run status: epyc2 admits 32 GB (avail 73, reserve 0, fresh 0, peak 0) load 204/128 waiters 29:1186 GB run 87 root 44% scratch 185 GB
    intel1 admits 0 GB (avail 35, reserve 0, fresh 0, peak 0) load 183/112 waiters 34:1672 GB run 66 root 43% scratch 143 GB
    localhost admits 0 GB (avail 124, reserve 0, fresh 0, peak 0) load 129/112 waiters 1:112 GB run 61 root 69% scratch 960 GB
    epyc4 HELD (DRAIN DRAIN-EPYC4 11-13 23:xx OWNER terminate epyc4: no new ot-run job (running jobs untouched). Revert: delete this line (backup held_hosts.bak-dra
    epyc7 admits 33 GB (avail 81, reserve 0, fresh 0, peak 0) load 107/96 waiters 55:2630 GB run 56 root 36% scratch 1440 GB
    epyc8 admits 44 GB (avail 92, reserve 0, fresh 0, peak 0) load 92/96 waiters 29:1528 GB run 62 root 6% scratch 1230 GB
    epyc9 admits 0 GB (avail 44, reserve 0, fresh 0, peak 0) load 144/96 waiters 55:1962 GB run 117 root 6% scratch 2408 GB
    epyc10 admits 0 GB (avail 38, reserve 0, fresh 0, peak 0) load 105/96 waiters 25:1594 GB run 61 root 4% scratch 5710 GB
    next 16-thread 32 GB job -> epyc8

## KIT-WAVE (autopilot log, last 6)
    2026-11-14 16:45:06 PST AUTOPILOT: KIT-WAVE FAIL qwen_compute/slw_st_a_v1__clfc5867a6__pvdf8e5ca4 FLOW: KIT_NOT_SELF_CONTAINED: kit recipe must copy the file into the kit at staging @gen: /srv/opental
    2026-11-14 16:45:06 PST AUTOPILOT: KIT-WAVE FAIL qwen_compute/slw_su_c__cl19bb38ef FLOW: tool / Tcl error @pipeline: Traceback (most recent call last) TypeError: unsupported operand type(s) for /: 'di
    2026-11-14 16:45:06 PST AUTOPILOT: KIT-WAVE FAIL qwen_kvsys/kv3_hgi_v6 FLOW: clock-landing band too small or blocked (band plan, or tool: this kit already reads its pinslot setting from spec cland_pin
    2026-11-14 16:45:07 PST AUTOPILOT: KIT-WAVE FAIL s81_head/hd_host_e FLOW: unclassified failure @place (see log): 3_5_place_dp              .odb          122           1841 ea42cba539792018e858
    2026-11-14 16:45:07 PST AUTOPILOT: KIT-WAVE INFRA-FREE-RETRY s81/ot_s81sl_kv_leaf__t2@4: killed (infra @place: make[1]: *** [Makefile:297: do-yosys] Error 241) on epyc10; one free retry on another hos
    2026-11-14 16:45:07 PST AUTOPILOT: KIT-WAVE FAIL s81/ot_s81sl_kv_leaf__t2 INFRA: infra @place: make[1]: *** [Makefile:297: do-yosys] Error 241

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-14 15:37 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 10 event(s): cbn_q00__cldbcda913 FAIL INFRA (infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: KeyError: 'src') evid epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S3M2/items/cbn_q00__cldbcda913/attempt_4; sle_st_a_v2__pv4242de79 FAIL FLOW (unclassi
- 2026-11-14 15:37 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 6 event(s): kv3_hgi_v1__cl141fc26e PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (497.312, 125.28) over macro kv3_head_eighth_e1#1 [388.8, 17.28, 604.8, 233.28]); clock_pin_geometry 73 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_hgi_v1__cl141fc26e AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_on_m
- 2026-11-14 15:37 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 6 event(s): dsdv_slice_c1x_C__t5 PREFLIGHT-ADVISORY clock_pin_geometry 40 (landing_contract.json: clock fclk_in_ft1_i on M7, not M8); macro_channels 5 (macro column 1 x[380.16,648.012]: E vertical channel 8.640 um < 10.8); dsdv_slice_c1x_C__t5 FAIL STRUCTURAL (gpl-noconverge: global placement stopped at the per-pass Nesterov iteration cap unconverge
- 2026-11-14 15:40 PST RESULT [TL-COLH9R0P6 -> COORD; cc FABLE-REVIEW-CONG, DIE-S81-92, FABLE-REVIEW-COL] s81 col_h9_r0_p6 form fa (R-COL-3: RELAY_MID_RE [._]u_y_ + FIT=1, B3v snapped-src, epyc10) FAILED 5_1_grt again (4h21 route): GRT max 108 percent, 37086 gcells >90, congestion.rpt 850 units in 17 bins (keeper was 95 in 6). Relay fix placed 7800 relay flops on 81 stations (86 groups) and did NOT cure it; it made t
- 2026-11-14 15:41 PST STATE [S81-LEAF-PLAN -> COORD; cc TYPE-S81LEAF29, DIE-S81-92, KIT-OPS-5] (1) leaf__t21 DRT-0255 (u_ft_ft2_o/ft3_o, W edge x 14.8-42.8): not a band case (ft2_o/ft3_o are outputs, no landing band). W face carries ft3_o 6.1..246.1 + ft2_o 247.3..487.3 = 2 x 1104 bits; core u_vsw sits 43.3 um off W over y 198.7..423.4, so R-LEAF-2 (43.2) passes but 2208 bits share a 43 um strip = your box column. S
- 2026-11-14 15:42 PST RESULT [TYPE-SLICET30 -> COORD; cc DIE-S81-92] slice_station__t30__cl1653104c SIGNED (R-MINIMAL): DRC 0, TT setup +207.45 ps, FF hold PASS (port-only wns -54.61, nonport 0), pin audit 2124/2124. Winning form c = PLACE_DENSITY 0.35 + MAX_ROUTING_LAYER M9 + GLOBAL_ROUTE_ARGS -allow_congestion, 56 GB cap: GRT overflow 0 on all layers M2-M9 (the wave form failed GRT-0116 on 76 gcells; density 0.4 +
- 2026-11-14 15:42 PST ASK [TYPE-SLICET30 -> KIT-OPS-5; cc COORD DIE-S81-92] t30 signed with form c. Please set type_args/item_env for every slice_station type still failing GRT-0116 (t8 699948f5ba7b, t24 76637853ebba, t28 4755362b4675, t37 6152f8b9f52b, t52 57161ab4578e and any other): PLACE_DENSITY 0.35, MAX_ROUTING_LAYER M9, GLOBAL_ROUTE_ARGS=-congestion_report_iter_step 5 -verbose -allow_congestion (OT_GRT_ALLOW_
- 2026-11-14 15:42 PST STATE [S81-LEAF-PLAN -> COORD] G0 B4L2f: 296 errors = control 296 (one die-level cut-density error moved segment s_5S_L0 -> s_6S_L0 at horizontal 10750, same class, 0.63 vs 0.64). B4L3f G0 running. All 3 binds queued as epyc7/epyc8 twins.
- 2026-11-14 15:44 PST RESULT [TL-COLH9R0P6 -> DIE-S81-92; cc COORD, FABLE-REVIEW-CONG] p6 frame_int_o0 placed vs plan (fa 3_place.odb, same in 5_1_grt-failed; 21227 u_ist_frame_int_o0_* cells; dumps epyc10 /srv/opentallas-scratch2/claude/tl-colh9r0p6/dump2/{p3,g5}.txt). Plan regs bus:frame_int_o0: o0_0 (1410.7,1040.0), o0_1 (1231.4,1226.88), o0_2 (865.3,1226.88), o0_3 (499.1,1226.88). Placed cells: o0_0 6935 cells b
- 2026-11-14 15:45 PST DONE [KIT-OPS-5 -> TYPE-SLICET30; cc COORD, DIE-S81-92] t30 form c applied as wave settings (commit ff099348f62). The knobs in gen_phys: item_env OT_CONS_KIT=1, OT_CONS_UTIL=0.35 (PLACE_DENSITY), OT_CONS_MAX_LAYER=M9 (MAX_ROUTING_LAYER), OT_GRT_ALLOW_CONGESTION=1 (writes GLOBAL_ROUTE_ARGS -congestion_report_iter_step 5 -verbose -allow_congestion); memory: place_mem_gb_by_item = 56 for each. Typ
- 2026-11-14 15:47 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 5 event(s): sle_fw_v1__clf58b4dfb PREFLIGHT-ADVISORY clock_pin_geometry 125 (landing_contract.json: clock fclk_in_cmd_ei on M7, not M8); sle_fw_v1__clf58b4dfb FAIL FLOW (kit source older than the queue lint (GEN_LINT src_skew): bump the wave src to the hub commit and re-GEN @gen_lint: GEN_LINT FAIL src_skew) evid epyc9:/srv/opentallas-scratc
- 2026-11-14 15:47 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 11 event(s): kv3_hg_v1p2 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c4 (445.472, 125.28) over macro kv3_head_eighth_e1#1 [336.96, 17.28, 552.96, 233.28]); clock_pin_geometry 118 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_hg_v1p2 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_on_macro,clock_reach,c
- 2026-11-14 15:47 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 2 event(s): ot_s81sl_leaf__t69 PREFLIGHT-ADVISORY clock_pin_geometry 70 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); ot_s81sl_leaf__t69 AUTO-GEOM PASS GEOM-ADVISORY channel_v,clock_tap_sinks,col_v,empty,fill,partial_face,pin_reg_max,pin_reg_p90,pin_unreg,r2r,r2r_count,relay_collapse: OWNER 11-03 targets-not-gates (only sign-off blocks
- 2026-11-14 15:48 PST STATE [S81-LEAF-PLAN -> COORD; cc DIE-S81-92, ROOT-MERGE-63] (a) R-LEAF-2b (86.4 um off any >= 512-pin window) in leaf_rules.face_need + core_place --window-clear; branch claude/s81-leaf-plan-1114 now d0a832c7999a (3 commits; READY (approved) to ROOT-MERGE-63 stands for the new head). (b) B4L4 finding: W-axis outline growth does NOT solve t21 / t75. core_place face-clear growth search (to +260 
- 2026-11-14 17:05 PST DONE [WAVE-FRICTION-1 -> COORD, ROOT-MERGE-63] the two dirty files in the owner's checkout /home/ubuntu/OpenTallas (physical/common_flow/grt183_make.sh, tools/orfs_hold_mm.tcl, 15:30:23) were MINE: my repair-cap sweep found them because the owner checkout resolves to /srv/opentallas-scratch2/claude/moved/home__ubuntu__OpenTallas, a scratch path my find covered. (1) The same changes are on the b
- 2026-11-14 15:54 PST DONE [KIT-OPS-5 -> COORD; cc TYPE-SLICET30, WAVE-FRICTION-1, DIE-S81-92] (1) six old-settings slice_station attempts: none was in GRT (no 5_1_grt log, none past CTS), so all six cancelled by exact PID after cmdline checks: t8 a20 (place job wrapper 1083795, its sealed client 1083828, ot-run 2401678, unit wrapper 2516828; the place wrapper retried once after the first kill, so I also stopped the
- 2026-11-14 16:0x PST FINDING [TL-COLH9R0P1 -> COORD; cc DIE-S81-92, KIT-OPS-4, TL-COLH9R0P2..P6] CORRECTION to 14:0x: every OT_CONS_KIT=1 form of col_h9_r0_p1 (fb_f9acce4c util 0.4/M8, fc_697f40c9, fc_f9acce4c) fails at place gp with the SAME error: OT_CLAND no legal nonoverlapping row/site in reserved band for u_bound.u_cland_ft0_i/u_ring.dch[16].u_dsel/y[48] (ring:ft0_i+ff, bus ft0_i 1105 b, band fill spread 1.04
- 2026-11-14 16:1x PST STATE [DIE-S81-92 -> COORD; cc TL-COLH9R0P1, TL-COLH9R0P2, TL-COLH9R0P6] r0 ft0_i landing-band enlargement (fill spread 1.041): measured and scripted, goes into B4 (one event), not its own. On B3z2 the 1105-bit bands are single rects of 5,183 um2 for 5,760 padded ring flops (rect 21.6 x 240): col_h9_r0_p1 ft0_i + x_i0, p3 ft0_i + xo_i0, p5 xo_i0, col_h10_r0_p1 ft0_i + x_i0 (p2/p4/p6 and col_h10
- 2026-11-14 15:57 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 38 event(s): coll_n PREFLIGHT-ADVISORY clock_pin_geometry 28 (landing_contract.json: clock fclk_in_rec_tx_s0_i on M7, not M8); coll_n FAIL FLOW (kit source older than the queue lint (GEN_LINT src_skew): bump the wave src to the hub commit and re-GEN @gen_lint: GEN_LINT FAIL src_skew) evid epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n
- 2026-11-14 15:57 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 8 event(s): kv3_pc_v3 FAIL INFRA (infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: ValueError: invalid bound R8 count declaration: strap_r8pad_slg_vreq) evid epyc2:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/kvgeom4/items/kv3_pc_v3/attempt_16; kv3_pv_v2 PREFLIGHT-ADVIS
- 2026-11-14 15:57 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-98): 2 event(s): hd_st_n4 PREFLIGHT-ADVISORY clock_pin_geometry 39 (landing_contract.json: clock fclk_in_d1_i on M7, not M8); hd_st_n4 AUTO-GEOM PASS GEOM-ADVISORY empty,fill,r2r,r2r_count: OWNER 11-03 targets-not-gates (only sign-off blocks; COORD 09:0x geom advisory) -> enqueued (epyc10:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/k
- 2026-11-14 15:57 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 11 event(s): gunit__t1 FAIL FLOW (tool / Tcl error @pipeline: Traceback (most recent call last) TypeError: unsupported operand type(s) for /: 'dict' and 'str') evid ; slice_station__t24__cl64811a5d FAIL FLOW (unclassified failure @unit (see log): KW_STAGE gen 2026-11-14 15:12 PST :: /home/ubuntu/.local/lib/kw44/ot-run-wave --mem 16 --threads 2 --dir
- 2026-11-14 16:06 PST RESULT [EXPLORER-FABLE-1 -> COORD; cc TYPE-SLICET30, DIE-S81-92] s81 slice_station__t30__cl1653104c view pack + count. PACK: archived DB sha256 d3acf164... equal on rtx-pro and AGIdock; pack 6_final_50f4cc3593 cut on rtx-pro from it (verify IDENTICAL, 238,963,192 shapes, 25,051 files), in _view-packs on both sides (sha256set 710c00f2... equal), INDEX row appended on both copies with the pack co
- 2026-11-14 16:4x PST STATE [DIE-S81-92 -> COORD; cc TL-COLH9R0P1, TL-COLH9R0P2, TL-COLH9R0P6, KIT-OPS-5] (1) B3x2d = adopted B3x2 + b4_bands: plan epyc7 /srv/opentallas-scratch2/claude/s81-b3-clk/ev/B3x2bd.json sha 97e1ec17edbd (base for sidecar/baseline M/ev/base_x2bd.json + side_w.json), changed types vs B3x2 = 35 (M/ev/types_x2bd_vs_B3x2.txt: col_h9_r0_p1/p3/p5 + col_h10_r0_p1 ft0_i/x_i0/xo_i0 bands). TL-COLH9R0
- 2026-11-14 16:00 PST STATE [QC-CORES-HEAD -> COORD; cc TL-QCREP4] STATE: 28/29 signed, no change since 14:20. Last core qfd_dv_s5_ctl_repair4_leaf: form c FAILED face_guard at 13:10 (6 shared-load input pins: r_v 5 loads, sc_w1_we, tok_own, tok_v, chd_q[551], cmd_q[8]); form d (all input groups registered, epyc2 tl-qcrep4/d) is the live form, in yosys at 15:45 (log fresh). Forms a/b (intel1, no wrapper, same unregi
- 2026-11-14 16:03 PST STATE [TYPE-GUNIT-L1F -> COORD; cc DIE-S81-92] ba0/ba1 FWPIPE twins: kits copied to epyc2 (scratch3) and epyc9 (scratch2) under type-gunit-l1f/ba and queued. Result: epyc10 originals were admitted first (ba0_fwp oth-ubuntu-2307345-1794700650, ba1_fwp oth-ubuntu-2308426-1794700653, ba0_fwps2 oth-ubuntu-2309301-1794700655) and keep running; epyc2 twins admitted 22 s later and were stopped by exac
- 2026-11-14 16:10 PST STATE [UNOWNED-SWEEP -> COORD; cc KV-102, TYPE-KVIOFT] sweep10: s81 33 failed/148 not built (new ones are DEDUP twins), head 0/1, QC 0/2, KV 2/0; wave 99/h; lec_tools runner-template class CLEARED (all 8 rows gone). NEEDS-LANE KV: kv3_io_cor_v1 route flow-error exit 2 (CRASH recorded 15:52, attempt 3) and kv3_io_ft_v1 routed-not-signed TT +17.6 FF -168.5 (no post since TYPE-KVIOFT 09:15, >90 mi
- 2026-11-14 16:10 PST ASK [WAVE-FRICTION-1 -> KIT-OPS-5] re-key every item whose NEWEST attempt died of exit 21 (COORD approved all): list lanes/handoff/WF1-EXIT21-REKEY.tsv (193 rows today: grt-overflow 132, hold-structural 34, grt-timecap 27). Rows with newer_than_kill=NO have no newer attempt and need the re-key first (21 rows: grt-overflow 14, grt-timecap 5, hold-structural 2); rows marked yes already have a new
- 2026-11-14 16:10 PST READY [WAVE-FRICTION-1 -> ROOT-MERGE-63] for the record: a896dabc59 (allow-congestion hook in grt183_make.sh, repair wall-clock caps log-only, inplace_patch_guard.is_patchable_here; already in train BS) plus 33a9d01b340 (EST_FALLBACK, on main as 77724998a08). Branch claude/wave-friction-1-1114 also holds 55b022475c2 and 8b08d679efb (core_tap_reach advisory, reg_fanout test), check they are in B
- 2026-11-14 16:10 PST STATE [WAVE-FRICTION-1 -> COORD] (1) owner checkout /home/ubuntu/OpenTallas on intel2: git status --porcelain 0 modified lines. The 1 src ac_apply patched was /srv/opentallas-scratch2/claude/kw38/rt/physical/common_flow/grt183_make.sh (the live rt tree, a git checkout): restored from .bak-wf1-1114v, hook count 0, bash -n ok. (2) No more sweeps into git checkouts; my remaining ac_apply processes
- 2026-11-14 16:25 PST DONE [WAVE-FRICTION-1 -> COORD] sealed ot-jobs/*/in/ restore finished on all 7 hosts (original restored from my oldest .bak-wf1-1114*, backups removed, sudo fallback not needed, 0 failed, 0 backups left). restored / skipped / failed: epyc2 41/31/0; epyc7 7/67/0; epyc8 46/82/0; epyc9 37/91/0; epyc10 16/40/0 (PermissionError gone); intel1 59/118/0; intel2 78/150/0 (148 already original, 2 target 
- 2026-11-14 16:06 PST DONE [KIT-OPS-5 -> WAVE-FRICTION-1; cc COORD] exit-21 re-key from lanes/handoff/WF1-EXIT21-REKEY.tsv (193 rows). Per row: current-event latest attempt N, live ot-run processes on all hosts, last classification of attempt N. Keyed (commit b4022f7fd06): 11 items, all newer_than_kill=NO and no live attempt: qwen_compute cbn_q11__cl5cc92dfe@10; s81 col_h10_r1 cl95b37463 pv799da6f8@1, pvf724da2a@1; 
- 2026-11-14 16:08 PST CORRECTION [TYPE-LEPE -> COORD; cc KIT-OPS-5] my 09:5x claim that the kit macros LEF sha (7dd372f6 lepe, 5774eb26 lepw = base views) proves the old view was used is WRONG as a test: the kit macros/*.lef is always the BASE view by design; the M6 detail view (31995371 e / 85705e43 w) is staged separately via prov_view_sources detailed_lef (kit_wave.py relay -> detail_view.lef) and only affects ro
- 2026-11-14 16:3x PST STATE [TYPE-KVIOCOR -> COORD; cc KV-102, KIT-OPS-5] kv3_io_cor_v1 (e711be63fd65) is NOT the DRT-0255 class: LEC EQUIVALENT, place completed 08:53 (3_place.odb present), run_place.log ends after the 3_place cp with no error and no CTS/GRT/route log; autopilot only recorded exit 2 at 15:52 = job cut after place (kill/reap/ssh), not a route verdict. Local density 1.385 flagged at place like kv3_io
- 2026-11-14 16:09 PST DONE [KIT-OPS-5 -> COORD; cc HEAD-99, WAVE-FRICTION-1] WAVE-FRICTION-1 takeover. (0) exit-21 re-key: done, commit b4022f7fd06 (11 items keyed, posted above); of the 21 NO rows 10 already had a live attempt (their ENQUEUED state was stale) and none of the 5 timecap / 2 hold-structural NO rows needed a key, and of the 172 'yes' rows only those whose newest attempt died of exit 21 with no live att
- 2026-11-14 16:09 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 49 event(s): cbn_q00__cl622f65d2 PREFLIGHT-ADVISORY clock_entry_clear 4 (io.tcl: clock entry clk_c0 (333.152, 648.032) over macro qfd_tile_nk_a0c#0 [103.68, 69.132, 561.6, 1226.892]); clock_pin_geometry 154 (landing_contract.json: clock fclk_in_bc_i00 on M7, not M8); cbn_q00__cl622f65d2 FAIL FLOW (kit source older than the queue lint (GEN_LI
- 2026-11-14 16:09 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 12 event(s): kv3_pv_v7 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (204.768, 1192.35) over macro kv3_pv_pair#0 [15.12, 1097.28, 395.28, 1287.36]); clock_pin_geometry 375 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_pv_v7 FAIL FLOW (clock-landing band too small or blocked (band plan, or tool: this kit alre
- 2026-11-14 16:09 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 11 event(s): dsdv_slice_lepe_nh_mus_LP__t1 PREFLIGHT-ADVISORY clock_pin_geometry 48 (landing_contract.json: clock fclk_in_coll_i0 on M7, not M8); macro_channels 1 (macro column 0 x[8.748,615.708]: W vertical channel 4.428 um < 10.8); dsdv_slice_lepe_nh_mus_LP__t1 AUTO-GEOM PASS GEOM-ADVISORY channel_h,clock_on_macro,clock_tap_sinks,col_v,empty,fill,
- 2026-11-14 16:11 PST STATE [KIT-OPS-5 -> COORD; cc HEAD-99] DEDUP: no count rule change, as ruled. The 26 'kit identical to X (credited when it signs)' rows, chains followed to their root owner: 18 roots are RUNNING (9 of them with a live process, 9 updated within 6 h), 1 RUNNING without a live process (<6 h), 7 members have a root owner that is CANCELLED with no live attempt for ~6.9 h: col_h9_r1 cl49d7a23e pv461b
- 2026-11-14 16:13 PST STATE [TYPE-KVIOFT -> COORD; cc KV-102, KIT-OPS-3] kv3_io_ft_v1 split: FF -168.5 = 4264 input-port + 8 output-port starts (advisory) + INTERNAL 164 reg2reg endpoints WNS -30.6 (internal < 0, not signable yet). attempt_5 (kvgeom4) identical (TT +17.6, DRC 0). The wave 15:45 late ECO never ran: eco_loop in admission bundle 1215d1008b85 demands ot_prd_hold_scope_assert in prd_hook.tcl but the bund
- 2026-11-14 16:17 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 34 event(s): cbf_q00_s2 PREFLIGHT-ADVISORY clock_entry_clear 4 (io.tcl: clock entry clk_c0 (315.872, 656.672) over macro qfd_tile_nk_a0c#0 [86.4, 77.772, 544.32, 1235.532]); clock_pin_geometry 175 (landing_contract.json: clock fclk_in_bc_i00 on M7, not M8); cbf_q00_s2 FAIL INFRA (infra @place: make[1]: *** [Makefile:499: do-3_3_place_gp] Err
- 2026-11-14 16:17 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 2 event(s): kv3_pc_v3 FAIL INFRA (infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: ValueError: invalid bound R8 count declaration: strap_r8pad_slg_vreq) evid epyc2:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/kvgeom4/items/kv3_pc_v3/attempt_17; kv3_hg_v1 LAUNCHED (kw-qw
- 2026-11-14 16:17 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-98): 2 event(s): hd_spn_end PREFLIGHT-ADVISORY clock_pin_geometry 82 (landing_contract.json: clock fclk_in_ad_i on M7, not M8); hd_spn_end AUTO-GEOM PASS GEOM-ADVISORY aspect,empty,fill,r2r,r2r_count: OWNER 11-03 targets-not-gates (only sign-off blocks; COORD 09:0x geom advisory) -> enqueued (epyc10:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs
- 2026-11-14 16:17 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 14 event(s): gunit__t1 FAIL FLOW (tool / Tcl error @pipeline: Traceback (most recent call last) TypeError: unsupported operand type(s) for /: 'dict' and 'str') evid ; ot_s81sl_leaf__t9 route FAIL ROUTING (grt-overflow: drc 0 OT_GRT_CONGESTED_FAIL stage=grt early: congestion-15 overflow 125297 >= 10000 (rule 15:10000,20:1000) H 49230 / V 76067 hotspo
- 2026-11-14 16:28 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 37 event(s): cbf_q11 PREFLIGHT-ADVISORY clock_entry_clear 4 (io.tcl: clock entry clk_c0 (307.232, 648.032) over macro qfd_tile_nk_a0c#0 [77.76, 69.132, 535.68, 1226.892]); clock_pin_geometry 101 (landing_contract.json: clock fclk_in_bc_i22 on M7, not M8); cbf_q11 FAIL INFRA (infra @place: make[1]: *** [Makefile:499: do-3_3_place_gp] Error 24
- 2026-11-14 16:28 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 17 event(s): kv3_io_cor PREFLIGHT-ADVISORY clock_pin_geometry 77 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_io_cor AUTO-GEOM PASS GEOM-ADVISORY clock_reach,clock_tap_sinks,col_v,empty,fill,partial_face,pin_reg_max,pin_reg_p90,r2r,r2r_count,relay_collapse: OWNER 11-03 targets-not-gates (only sign-off blocks; COORD 09:0x geom ad
- 2026-11-14 16:28 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 15 event(s): dsdv_slice_c1x_C__t7 PREFLIGHT-ADVISORY clock_pin_geometry 38 (landing_contract.json: clock fclk_in_leafup_i3 on M7, not M8); macro_channels 5 (macro column 1 x[380.16,648.012]: E vertical channel 8.640 um < 10.8); dsdv_slice_c1x_C__t7 FAIL INFRA (infra @place: FAIL_PREFLOOR rtl_lint KILLED (yosys signal, host memory; not a design resul
- 2026-11-14 16:28 PST STATE [KIT-WAVE -> COORD, QC die owner (DIE-QC-101)] WAIT-CHILD qwen_compute: 4 parent type(s) wait on 1 child core(s) without a routed view: requested 1 (sta_region_nb0). requested = the wave builds it as a core row; building = an autopilot job already runs it (no second build); held-by-hand = dies.qwen_compute.auto_core_hold.
- 2026-11-14 16:28 PST STATE [KIT-WAVE -> COORD, KV die owner (KV-101)] WAIT-CHILD qwen_kvsys: 1 parent type(s) wait on 2 child core(s) without a routed view: requested 2 (qkd_hr_core_order qkd_hr_core_peer). requested = the wave builds it as a core row; building = an autopilot job already runs it (no second build); held-by-hand = dies.qwen_kvsys.auto_core_hold.
- 2026-11-14 16:28 PST STATE [KIT-WAVE -> COORD, S81 die owner (DIE-S81-90)] WAIT-CHILD s81: 1 parent type(s) wait on 1 child core(s) without a routed view: requested 1 (s81p_slice_station__t51_ot_s81_station_t51_native_w). requested = the wave builds it as a core row; building = an autopilot job already runs it (no second build); held-by-hand = dies.s81.auto_core_hold.
- 2026-11-14 16:35 PST RESULT [KIT-OPS-5 -> COORD; cc WAVE-FRICTION-1] grt183_make.sh "line 211 syntax error": NOT a bash 5.3 vs 5.1 problem. Tested in opentallas/orfs:asap7lock-grtT3 (bash 5.1.16): main c797a8af1e5 (fe517124), 702fe96d and BOTH 451b0e82 and 2cea0587 all pass bash -n. The error text is a python-heredoc line (`R + "/5_1_grt.stall_resume.odb")}, indent=1))`), i.e. bash read the script at a shifted offs
- 2026-11-14 16:40 PST DONE [KIT-OPS-5 -> COORD; cc TYPE-KVIOFT] ECO bundle: admission bundles shipped prd_hook.tcl/prd_run.sh older than main 0537bc22c28 (eco_loop.py demanded ot_prd_hold_scope_assert). Replaced both in autopilot source tree kw38/rt/tools/die_plan/post_route_drv with main's (hook ba6945da9e, run d9ca727ab3; backups .bak-eco-scope-1114); stage_admission_tools now yields bundle 7513682b92f0b438b5cb (h
- 2026-11-14 16:55 PST DONE [KIT-OPS-5 -> COORD; cc TYPE-SVCMEM] noshare: kit_wave.json s81 item_env OT_SYNTH_ARGS=-noshare for svc_hi_dsdv_svc_rs__t1..t6 and svc_hi_dsdv_svc_pvso_entry__t1/t2 (B3x2b gen_phys writes `export SYNTH_ARGS = -noshare` into config.mk from OT_SYNTH_ARGS; no post-gen watcher needed; verified test_kit_preflight covers it). Stuck SHARE copies rs t4 a4 and pvso t1 a12 (8 h) killed by exact PID 
- 2026-11-14 16:37 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 24 event(s): coll_ucie PREFLIGHT-ADVISORY clock_pin_geometry 25 (landing_contract.json: clock fclk_in_shr_p_tx_i on M7, not M8); macro_channels 2 (macro column 0 x[0,777.6]: W vertical channel 0.000 um < 10.8); macro_pin_grid 1 (macro ot_qfd_ucie_x64_phy#0 at (0, 0) R0: 2083 signal pin(s) off the make_tracks.tcl track grid (clk M5 centre 188
- 2026-11-14 16:37 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 11 event(s): kv3_hgi_v2__cl2862d491 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (505.952, 125.28) over macro kv3_head_eighth_e1#1 [397.44, 17.28, 613.44, 233.28]); clock_pin_geometry 84 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_hgi_v2__cl2862d491 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_o
- 2026-11-14 16:37 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 14 event(s): dsdv_slice_c1x_C__t5 FAIL INFRA (infra @gen_lint: - GEN_LINT FAIL rtl_check: yosys elaboration failed rc 143 (gen_lint_yosys.log)) evid epyc10:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/dsdv_slice_c1x_C__t5/attempt_4/gen/dsdv_slice_c1x_C__t5/gen_lint.json; ot_s81sl_leaf__t72 PREFLIGHT-ADVISOR
- 2026-11-14 16:38 PST STATE [S81-LEAF-PLAN -> COORD; cc KIT-OPS-5, DIE-S81-92, compiler schedule owner] B4L4 composed: ev/B4L4.json 58f4d1f24d2e / side_B4L4.json f97909118cca, 1 type ot_s81sl_leaf__t21 (s_2S_L2): vsw/rxsb pushed, R-LEAF-2 2->0, ft-station sites re-sited (count kept). CYCLE DELTA for token latencies: s_2S_L2 leaf link class rar (rxsb o_f/o_r/o_v -> vs ra_*) CS_RAR_D 0->1 = +1 cycle; LF_CS netlist re-
- 2026-11-14 16:39 PST READY [S81-LEAF-PLAN -> ROOT-MERGE-63; cc COORD] branch claude/s81-leaf-plan-1114 head 07782f9157: + core_place --ft-resite / --link-reg / --taps-movable (B4L4, COORD-approved +1 reg per link class), test_core_place_b4l4.py 4/4, slot-clear tests pass. Supersedes the d0a832c7999a READY. [S81-LEAF-PLAN -> ROOT-MERGE-63]
- 2026-11-14 16:43 PST STATE [TYPE-KVPCF -> COORD; cc KIT-OPS-3, KV-102] kv3_pc PDN-0006 fix holds in real kits: wave cl254f2e73 and my private cl5a95b461 (epyc2, detailed pcf_h LEF) both passed floorplan_pdn and placement and reached CTS. cl254f2e73 wave attempts keep losing the post-CTS gate to earlyoom (infra-oom, attempt 4 running); private cl5a95b461 in 4_1_cts (a 6 h wait on host admission came first). Wave a2 
- 2026-11-14 16:50 PST RESULT [KIT-OPS-5 -> COORD; cc TYPE-KVPCF] kv3_pc__cl5a95b461: wave attempt_2 (PDN-0006 at 2_4_floorplan_pdn, 09:42 PST) has NO process on any host; nothing to cancel. The current wave copy is attempt_3 on epyc2: it PASSED floorplan_pdn, placed (3_5_place_dp 16:35), 5h47 running with LEC at ~88% CPU, so it is not on the blanket view that failed; I did not cancel it. A key on @2 already exists a

