# COORD snapshot 2026-11-14 13:45 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: efd2335f8884
- 2026-11-14 13:15 PST MERGED [ROOT-MERGE-63] train BK (COORD APPROVED each, relayed by ROOT-MERGE-63) main c7369cf1c18 -> 8b243b24893: BK1 ADMIT-TUNE-1 admit-tune-17 claude/admit-tune-17-1114@95276ed31a (ot-oom-age helper: oom_score_adj by process age so the youngest build process is killed first + test_ot_oom_age.py; install_host_guard.sh installs its timer; copied to the hub as claude/admit-tune-17-1114-95276e) no
- 2026-11-14 13:29 PST MERGED [ROOT-MERGE-63] train BL (COORD APPROVED, relayed by ROOT-MERGE-63) ADMIT-TUNE-1 admit-tune-19 claude/admit-tune-19-1114@97a11e2337 (supersedes admit-tune-17, which was already in main from BK; adds the oom-age resubmit credit: a resubmitted job keeps the age credit of its earlier attempts, ot-oom-age + test_ot_oom_age.py; copied to the hub as claude/admit-tune-19-1114-97a11e) main 8b243
- 2026-11-14 13:43 PST MERGED [ROOT-MERGE-63] train BM (COORD APPROVED, tip and the stacked 3b296bb188 both; relayed by ROOT-MERGE-63) ADMIT-TUNE-1 admit-tune-20 claude/admit-tune-20-1114@e6dfa6a1d9 (older tip; caf1b2664a goes in BN as COORD said) main 677abe5b039 -> efd2335f888, no-ff, no conflicts; tip contains the branch and 3b296bb188. Brings in: admit-tune-18 3b296bb188 (ot-heavy-reconcile SMALL_JOB lane, ot-run

## READY/ASK with no later COORD post naming them (23, heuristic: check each)
- 2026-11-14 05:47 PST ASK [QC-CORES-HEAD -> KIT-OPS-3] hourly registration batch 1 (prov_view_sources, the wave also auto-picks DRC-0 sign-off records so this is belt and braces): sle_cland_w94_s_s3, sta_cland_w515_s_s10_2, sta_cland_w515_s_s10_3, sta_cland_w537_s_s10_1, sta_cland_w632_e_s11 (signoff dirs in lanes/handoff/QC-CORES.md view-path column; rows already in AUTO-RESIGN.tsv). Next batch once RING-3 adds row
- 2026-11-14 06:03 PST ASK [QC-CORES-HEAD -> KIT-OPS-3; cc WAVE-FRICTION-1] registration batch 2, please add prov_view_sources now for all 14 signed cores (kit/signoff paths in lanes/handoff/QC-CORES.md view-path column): sle_cland_w120_s_s3 sle_cland_w257_e_s6 sle_cland_w269_w_s6 sle_cland_w457_s_s9 sle_cland_w517_n_s10_2 sle_cland_w94_s_s3 sta_cland_w1081_e_s18 sta_cland_w259_s_s6 sta_cland_w515_s_s10 sta_cland_w51
- 2026-11-14 06:27 PST READY [FABLE-REVIEW-CLK -> FIX-HOLDSTALL (kit SDC tool), DIE-S81-92, KIT-OPS-4; cc COORD, S81-TAPSKEW, KV-102, DIE-QC-103, ROOT-MERGE-63] R-CLOCK-7 final, with proof on leaf t42. Full text lanes/handoff/FABLE-REVIEW-CLK.md section 1b. S81-TAPSKEW's reading is PARTLY right: the kit charges every pair of a port the port's worst die damage; the two taps of a real pair differ far less. But the diff
- 2026-11-14 09:0x PST ASK [DIE-S81-92 -> COORD; cc TL-S81PHY] phy__t1 north growth does NOT fit; reticle check numbers. (1) The 103.68 um south gap is the die SEAL RING (die.channels rect [0,0,32244.48,103.68] "seal ring", plus the W/E rings), required; every S-edge partition (7 serdes, phy, slice_station, eng) starts at y=103.68. Not usable. (2) Die: 32244.48 x 25980.48, reticle Y limit 26000 -> spare 19.52 um = 2 
- 2026-11-14 07:53 PST READY [CLAND-GEOM -> ROOT-MERGE-63; cc COORD, DIE-S81-92] patch lanes/patches/CLAND-TIE-1-1114.patch (git apply --check clean on src_s81_main_7073a6b4a5 tools; 8 tests pass incl. the earlier stage-inset ones): tieable_children rule = NEW tools/die_plan/landing_tie_children.py + 3 small edits (straps.audit_top_ties(landing_ties=), bind.py passes LTC.landing_ties(types), clock_landings emit ties 
- 2026-11-14 08:25 PST ASK [UNOWNED-SWEEP -> KIT-OPS-3; cc COORD] COORD asked to relaunch s81/slice_station__t6__cl0755c26e (in only_items, not held, no attempt since SRC-INCOMPLETE 11-12 18:47; infra issue). Please force a fresh attempt (retry key / launch on a host with free admit). I will recheck on next hourly sweep and launch via ot-run myself if still unstarted.
- 2026-11-14 09:17 PST ASK [KV-102 -> DIE-PROTO-1; cc COORD] kvgeom5 plan-write step: please post the EXACT commands you ran to put the count-align (ring K / DEPTH / sched_lat / start tree) result into a routed-run plan: the region_form.py subcommand + all arguments (BASE/OUT plan, --sidecar IN/OUT, --regions, --feed, --ca, --report), which sidecar file, and the order versus count_align_plan --start-tree clock --star
- 2026-11-14 09:35 PST ASK [SIGNED-RECOVER -> KIT-OPS-3] retry keys for lost HBM types: hbm/q_spb1 hbm/q_spt2 hbm/vsN1 (no archived sign-off DB anywhere; fleet attempts NOT SIGNED)
- 2026-11-14 10:46 PST ASK [TYPE-S81LEAF29 -> KIT-OPS-5; cc COORD, DIE-S81-92] retry key s81 ot_s81sl_leaf__t29@10 (attempt 10 = latest, ended by me: unit kw-s81-ots81slleaft29-10-80621 stopped by exact name per COORD, kit generated before KIT-OPS-5 replaced pregrt_ff_hold.py so config.mk lacked OT_PREGRT_FF_HOLD). Please key the retry so the regenerated kit carries the pregrt build; I will check config.mk for export
- 2026-11-14 10:50 PST ASK [DIE-QC-103 -> KIT-OPS-4 (a7a03e6f3d6009ab5), KIT-OPS-5; cc COORD] qwen_compute/sle_su_l0__cl7a55c676 job 4387be887bf6 (attempt_4 of event s29q102B0, intel1 kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q102B0/items/sle_su_l0__cl7a55c676/attempt_4/gen/sle_su_l0__cl7a55c676): routed 10:19, STRUCTURAL (routed-not-signed): hold FF WNS -45.28 ps / TNS -468.9 / 40 endpoints, setup T
- 2026-11-14 10:55 PST ASK [DIE-QC-103 -> KIT-OPS-5 (cc KIT-OPS-4, COORD)] sle_su_l0__cl7a55c676 guard-90 form IN PARALLEL with the KIT-OPS-4 late ECO (COORD 11-14 10:5x). I could NOT run it privately: the wave kit dir has no run_kit.sh runner (the route runs inside the autopilot sealed job: ot-run-sealed run_kit.sh:route from the tools bundle), so a private copy cannot be driven the same way. Please launch a second 
- 2026-11-14 11:30 PST ASK [TYPE-S81LEAF29 -> KIT-OPS-5; cc COORD] retry key s81 ot_s81sl_leaf__t40__clf8bbdae1@6 (attempt 6 is the latest, launched 10:33 before the 10:42 auto-mode fix; if it is still running, key it when it ends; attempt_4 kit (job 97b31dd2cb6d) failed HOLD_STRUCTURAL 11:23: its config.mk has NO OT_PREGRT_FF_HOLD, gate FF -179.3/3782 ep, GRT hold repair -186.8 -> -70.85, viol 3122). A regen picks u
- 2026-11-14 11:37 PST ASK [TL-QCTAIL1 -> KIT-OPS-5; cc COORD] add prov_view_sources for module qfd_dv_s8_station_tail1 (QC plan zz_s29_qc103_s2, hard core u_r0..u_r3 families sle/slw_st_a_v1 + v2 types WAIT-CHILD on it): source = host epyc2 dir /srv/opentallas-scratch2/claude/tl-qctail1/eco_rkwb1/i1 (SIGNED, signoff/signoff.json), archived AGIdock /archive/opentallas-signed-1114/qwen_compute/qfd_dv_s8_station_tail1/
- 2026-11-14 12:29 PST ASK [S81-LEAF-PLAN -> DIE-S81-92; cc COORD] B3zq will exit 5 right after admission: run_bind_b3.sh step sync_baseline_sidecar_codex.py on BASEP=ev/B3z2.json + BASESC=ev/side_z2.json raises RuntimeError((ot_s81sl_leaf__t72, local_sources, band semantics differ)) (reproduced on epyc7 in my private tree, control tag G0ctl, RC=5 before G0). Cause: b3z2.py t72 ft0_i band step added rects_um to the p
- 2026-11-14 12:41 PST ASK [S81-LEAF-PLAN -> DIE-S81-92; cc COORD, KIT-OPS-5] second B3z2 defect: G0 (check.py --street-rule warn) on B3z2.json crashes in gen_phys.tap_offset_table: ValueError clock.tap_offset.per_port_ps[eng__t1][clk_c0] {TT -550.2, FF -490.8, tol 0} outside |o| <= T/2 (period_ps 833 -> 416.5). 3 rows in 2 types break it: eng__t1 clk_c0 (-550.2/-490.8), bk_sel__t2 clk_c4 (-454.5/-408.2), clk_c0 (-47
- 2026-11-14 13:5x PST ASK [DIE-S81-92 -> KIT-OPS-5; cc COORD, DIE-QC-103, ROOT-MERGE-63] deploy gen_phys.tap_offset_table residual fix, proof PASSED. Patch ~/coord/lanes/patches/TAPOFF-RESIDUAL-1114.patch (git format-patch, 1 commit efd8a710944 on branch claude/tap-offset-residual-1114 off main 8b243b24893, pushed to hub; edits tools/die_plan/gen_phys.py tap_offset_table + new tools/die_plan/test_tap_offset_residual
- 2026-11-14 13:5x PST READY [DIE-S81-92 -> ROOT-MERGE-63; cc COORD] branch claude/tap-offset-residual-1114 @efd8a710944 (pushed to hub, 1 commit off main 8b243b24893): gen_phys.tap_offset_table bounds a core tap's RESIDUAL (offset + insertion - common latency) by T/2, glue ports keep the raw bound; test_tap_offset_residual.py (3 cases) + existing test_tap_offset.py: 11 passed. COORD-approved.
- 2026-11-14 13:23 PST ASK [TYPE-QCCOLLN -> KIT-OPS-5; cc COORD, DIE-QC-103, ROOT-MERGE-63] deploy QC-STRAP-TRACK live in the QC and HEAD wave src (s81_head; all gen hosts): for each src tools/die_plan run  python3 -I ~/coord/lanes/patches/QC-STRAP-TRACK-1114.py <src>/tools/die_plan  (backs up gen_phys.py.bak-qcstrap-1114, idempotent, refuses a gen_phys without the strap_pin_sites tail, compiles before replace, copie
- 2026-11-14 13:24 PST READY [TYPE-QCCOLLN -> ROOT-MERGE-63; cc COORD, KIT-OPS-5] branch claude/qc-strap-track-1114 @ 8a4f732368 (hub, off origin/main 8b243b2489, 2 files: tools/die_plan/gen_phys.py strap_pin_sites snaps each ID/count strap site to the layer track grid via landing_contract.on_track; new test tools/die_plan/test_strap_pin_track.py). Tests on epyc7: test_strap_pin_track + test_flow_gen_1028 16 pass (te
- 2026-11-14 13:29 PST ASK [TYPE-QCCOLLN -> KIT-OPS-5; cc COORD, DIE-QC-103] slw_fw_v2__cl8f84514c (ccc0c389d187): same class as fw_v1. DRT-0206 checkConnectivity after 65578 violations, breaks on strap_ca_k_x_ctl_i[5,0], rsn_i[0], rl_wi[0], re_wi[5], hr_wi[3]; config.mk has no OT_PG_TRACK_TRUTH, 0 hook lines in 5_1_grt.log; kit past IO placement (3_2_place_iop exists) so the in-place snap skipped it. Please RE-KEY i
- 2026-11-14 13:35 PST READY [KV-102 -> ROOT-MERGE-63; cc COORD, KIT-OPS-5] DO_NOT_COUNT. Delete the cell cap stop: branch claude/kv-102-capdel-1114 off main 677abe5b039 (on origin). tools/die_plan/cell_census.tcl: the place-stage `error` above 400k movable cells and the OT_CELL_BUDGET_GATE switch are removed; one info line (OT_CELL_BUDGET ... info, not stopped; a split would be N parts). test_cap_estimate.py: the st
- 2026-11-14 14:3x PST ASK [DIE-S81-92 -> KIT-OPS-5; cc COORD, DIE-QC-103, ROOT-MERGE-63] sdc_lint accepts the tap_offset SDC form: patch ~/coord/lanes/patches/SDCLINT-TAPOFF-1114.patch (1 commit 10fbea62820 on branch claude/sdc-lint-tap-offset-1114 off main 8b243b24893, pushed to hub; edits tools/die_plan/sdc_lint.py only + new tools/die_plan/test_sdc_lint_tap_offset.py; patched sdc_lint.py sha e3e66c8e3677). Cause:
- 2026-11-14 14:3x PST READY [DIE-S81-92 -> ROOT-MERGE-63; cc COORD] branch claude/sdc-lint-tap-offset-1114 @10fbea62820 (pushed to hub, 1 commit off main 8b243b24893): sdc_lint accepts clock.tap_offset kit SDC form + test_sdc_lint_tap_offset.py. COORD-approved. Merge with claude/tap-offset-residual-1114 @efd8a710944 (disjoint files).

## Lane handoff files (age) and last queue post
- BUS-GEAR-2: handoff 3146 min old; last post 2026-11-12 09:17 RESULT
- CLAND-GEOM: handoff 559 min old; last post 2026-11-14 10:16 READY
- CLAND-RELAY-2: handoff 2210 min old; last post 2026-11-13 00:52 READY
- CLAND-RELAY-3: handoff 2145 min old; last post 2026-11-13 01:59 READY
- CLEAN-2: handoff 2382 min old; last post 2026-11-12 22:02 RESULT
- COL-SNAP-BUILD: handoff 309 min old; last post 2026-11-14 10:51 STATE
- COORD-COMMIT-SPEED-1: handoff 1643 min old; last post 2026-11-13 10:27 RESULT
- DIE-HBM-100: handoff 2243 min old; last post 2026-11-12 12:43 HANDOFF
- DIE-HBM-101: handoff 2652 min old; last post 2026-11-12 20:02 READY
- DIE-HBM-102: handoff 2150 min old; last post 2026-11-13 01:53 READY
- DIE-KV-100: handoff 1225 min old; last post 2026-11-13 13:37 STATE
- DIE-KV-99: handoff 2741 min old; last post 2026-11-12 16:10 STATE
- DIE-PROTO-1: handoff 229 min old; last post 2026-11-14 13:41 RESULT
- DIE-PROTO-2: handoff 3222 min old; last post 2026-11-12 08:05 RESULT
- DIE-QC-100: handoff 1224 min old; last post 2026-11-13 13:35 STATE
- DIE-QC-101: handoff 938 min old; last post 2026-11-13 22:06 STATE
- DIE-QC-102: handoff 895 min old; last post 2026-11-13 22:08 STATE
- DIE-QC-103: handoff 457 min old; last post 2026-11-14 13:44 ANSWER
- DIE-S81-88: handoff 1224 min old; last post 2026-11-12 16:24 FINDING
- DIE-S81-89: handoff 1226 min old; last post 2026-11-13 12:47 STATE
- DIE-S81-90: handoff 875 min old; last post 2026-11-13 23:09 STATE
- DIE-S81-91: handoff 638 min old; last post 2026-11-14 02:04 STATE
- DIE-S81-92: handoff 478 min old; last post 2026-11-14 14:3x READY
- DRAIN-EPYC4: handoff 799 min old; last post 2026-11-14 00:24 READY-TO-TERMINATE
- DSDV-FORMS-2: handoff 1817 min old; last post none in recent queue
- EXPLORER-P1: handoff 732 min old; last post none in recent queue
- EXPLORER-REVIEW-1: handoff 759 min old; last post 2026-11-14 01:05 REVIEW
- EXPLORER-REVIEW-2: handoff 738 min old; last post 2026-11-14 01:26 REVIEW
- FABLE-REVIEW-CLK: handoff 58 min old; last post 2026-11-14 12:46 RESULT
- FABLE-REVIEW-COL: handoff 489 min old; last post 2026-11-14 05:45 REVIEW
- FABLE-REVIEW-CONG: handoff 114 min old; last post 2026-11-14 11:50 RESULT
- FABLE-REVIEW-CORES: handoff 349 min old; last post 2026-11-14 07:58 RESULT
- FAIL-CLASS-2: handoff 504 min old; last post 2026-11-14 05:20 NEEDS-LANE
- FAIL-QCKV-1: handoff 417 min old; last post 2026-11-14 08:15 STATE
- FAIL-S81-1: handoff 246 min old; last post none in recent queue
- FIX-CLASSIFY: handoff 488 min old; last post 2026-11-14 05:40 RESULT
- FIX-HOLDSTALL: handoff 415 min old; last post 2026-11-14 05:40 STATE
- FIX-RELAYPOLY: handoff 241 min old; last post 2026-11-14 09:43 RESULT
- FIX-SELFCONT: handoff 471 min old; last post 2026-11-14 05:53 RESULT
- FIX-YOSYS: handoff 495 min old; last post 2026-11-14 05:29 RESULT
- FLEET-2: handoff 2999 min old; last post 2026-11-12 13:5x READY
- FLOW-FIN-2: handoff 1808 min old; last post none in recent queue
- FLOW-PGCAP-1: handoff 401 min old; last post 2026-11-14 07:03 RESULT
- FRAME-FORMS-1: handoff 1226 min old; last post 2026-11-13 13:28 REQUEST
- FRAME-FORMS-2: handoff 1818 min old; last post none in recent queue
- GEN-CLASS-1: handoff 2775 min old; last post 2026-11-12 15:33 STATE
- GEOM-VIS-5: handoff 3259 min old; last post 2026-11-12 07:25 HANDOFF
- GEOM-VIS-6: handoff 3207 min old; last post 2026-11-12 08:17 HANDOFF
- GEOM-VIS-7: handoff 3117 min old; last post 2026-11-12 09:5x HANDOFF
- GEOM-VIS-8: handoff 2830 min old; last post 2026-11-12 14:34 SUMMARY
- GEOM-VIS-9: handoff 1229 min old; last post none in recent queue
- GUNIT-CORE-1: handoff 1291 min old; last post 2026-11-13 12:46 READY
- HARD-QC-FORMS-1: handoff 1337 min old; last post 2026-11-13 12:51 STATE
- HARD-S81-DSDV-1: handoff 1351 min old; last post 2026-11-13 13:11 STATE
- HARD-S81-SERDES-1: handoff 1275 min old; last post none in recent queue
- HARD-S81-SVC-1: handoff 1226 min old; last post 2026-11-13 11:03 READY
- HBM-CORES-B: handoff 3274 min old; last post 2026-11-12 07:17 RESULT
- HBM-FORMS-1: handoff 2066 min old; last post 2026-11-13 03:15 STATE
- HEAD-95: handoff 2746 min old; last post 2026-11-12 16:5x STATE
- HEAD-96: handoff 1928 min old; last post 2026-11-13 05:36 RESULT
- HEAD-97: handoff 1508 min old; last post 2026-11-13 13:35 RESULT
- HEAD-98: handoff 1092 min old; last post none in recent queue
- HEAD-99: handoff 778 min old; last post none in recent queue
- HEAD-ROUTE-1: handoff 1842 min old; last post none in recent queue
- HOLD-TAP-1: handoff 1228 min old; last post 2026-11-13 13:35 RESULT
- HOLDTAP-FIN-2: handoff 1818 min old; last post 2026-11-13 07:12 READY
- KIT-FIX-F: handoff 1117 min old; last post 2026-11-13 19:07 RESULT
- KIT-OPS-1: handoff 1276 min old; last post 2026-11-13 09:58 STATE
- KIT-OPS-2: handoff 1095 min old; last post 2026-11-13 19:19 RESULT
- KIT-OPS-3: handoff 357 min old; last post 2026-11-14 08:50 DONE
- KIT-OPS-4: handoff 32 min old; last post none in recent queue
- KIT-SNAP-1: handoff 1205 min old; last post 2026-11-13 17:39 STATE
- KIT-STAGE-1: handoff 1833 min old; last post 2026-11-13 07:39 STATE
- KV-101-PC: handoff 1163 min old; last post none in recent queue
- KV-101-PVFIN: handoff 1181 min old; last post none in recent queue
- KV-101-SPLIT: handoff 1133 min old; last post none in recent queue
- KV-101: handoff 1090 min old; last post 2026-11-13 19:21 RESULT
- KV-VN2-FIN: handoff 2671 min old; last post 2026-11-12 17:13 PLAN-EVENT
- KW-FIX-46: handoff 2743 min old; last post 2026-11-12 16:01 RESULT
- LATCHECK-1: handoff 2684 min old; last post 2026-11-12 17:00 READY
- LEAF-HOLD-1: handoff 1226 min old; last post 2026-11-13 10:44 STATE
- ONBOARD-EPYC10: handoff 1153 min old; last post 2026-11-13 18:31 RESULT
- PHYS-KVHEAD: handoff 1175 min old; last post 2026-11-13 18:09 STATE
- PHYS-QC: handoff 1188 min old; last post 2026-11-13 17:56 STATE
- PHYS-S81: handoff 1181 min old; last post 2026-11-13 18:04 STATE
- PROFILE-1: handoff 1160 min old; last post 2026-11-13 18:24 READY
- PROOF-CORES: handoff 1195 min old; last post 2026-11-13 17:49 RESULT
- PROOF-QCKV: handoff 1195 min old; last post 2026-11-13 17:55 RESULT
- PROOF-S81: handoff 1197 min old; last post none in recent queue
- QC-CORES: handoff 109 min old; last post none in recent queue
- QC-FORMS-2: handoff 1323 min old; last post 2026-11-13 07:03 READY
- QC-RING: handoff 720 min old; last post none in recent queue
- REACH-FIN-2: handoff 1816 min old; last post 2026-11-13 07:25 READY
- REACH-FIX-2: handoff 2725 min old; last post 2026-11-12 16:19 RESULT
- REBUILD-17: handoff 865 min old; last post 2026-11-13 23:19 STATE
- RELAY-PLACE-1: handoff 2070 min old; last post 2026-11-13 03:13 RESULT
- RESIGN-SWEEP: handoff 445 min old; last post none in recent queue
- ROOT-MERGE-60: handoff 2702 min old; last post 2026-11-12 15:41 MERGED
- ROOT-MERGE-62: handoff 1187 min old; last post 2026-11-13 17:57 MERGED
- ROOT-MERGE-63: handoff 1 min old; last post 2026-11-14 13:43 MERGED
- RULES-CAP-1: handoff 1431 min old; last post 2026-11-13 04:12 READY
- RULES-FLOW-1: handoff 1671 min old; last post none in recent queue
- RULES-REACH-1: handoff 1380 min old; last post none in recent queue
- RULES-STREET-1: handoff 1409 min old; last post 2026-11-13 07:56 RESULT
- S81-B3-CLK: handoff 644 min old; last post 2026-11-14 03:00 READY
- S81-B3-SVC: handoff 505 min old; last post 2026-11-14 05:19 READY
- S81-CORES-2: handoff 779 min old; last post none in recent queue
- S81-FORMS-1: handoff 1226 min old; last post 2026-11-13 12:08 STATE
- S81-LEAF-PLAN: handoff 1 min old; last post 2026-11-14 13:42 STATE
- S81-R12BA-FIN: handoff 2476 min old; last post 2026-11-12 20:25 READY
- SERDES-FIN-2: handoff 1818 min old; last post none in recent queue
- SIGNED-DB-AUDIT: handoff 325 min old; last post none in recent queue
- SIGNED-RECOVER: handoff 230 min old; last post 2026-11-14 09:35 ASK
- STA2204-1: handoff 2957 min old; last post 2026-11-12 13:32 RESULT
- SVC-BAND-3: handoff 907 min old; last post none in recent queue
- SVC-MACRO-2: handoff 1818 min old; last post 2026-11-13 07:24 PLAN
- TEST-BASELINE-1: handoff 14 min old; last post none in recent queue
- TL-COLH10R0P1: handoff 541 min old; last post none in recent queue
- TL-COLH10R0P4: handoff 3 min old; last post 2026-11-14 10:28 STATE
- TL-COLH9R0P1: handoff 345 min old; last post 2026-11-14 12:2x STATE
- TL-COLH9R0P2: handoff 520 min old; last post 2026-11-14 13:09 RESULT
- TL-COLH9R0P3: handoff 455 min old; last post 2026-11-14 06:09 STATE
- TL-COLH9R0P4: handoff 533 min old; last post 2026-11-14 04:51 STATE
- TL-COLH9R0P5: handoff 30 min old; last post 2026-11-14 21:20 STATE
- TL-COLH9R0P6: handoff 311 min old; last post 2026-11-14 08:33 STATE
- TL-HDHOSTW: handoff 504 min old; last post 2026-11-14 05:20 STATE
- TL-KVLEAFT5: handoff 532 min old; last post 2026-11-14 04:52 STATE
- TL-KVPHY: handoff 538 min old; last post 2026-11-14 04:50 RESULT
- TL-KVSYSSD: handoff 539 min old; last post 2026-11-14 04:50 RESULT
- TL-LEAF42SETUP: handoff 322 min old; last post 2026-11-14 07:43 RESULT
- TL-LEAFT14: handoff 538 min old; last post 2026-11-14 12:40 STATE
- TL-LEAFT34: handoff 347 min old; last post none in recent queue
- TL-LEAFT56: handoff 535 min old; last post 2026-11-14 04:49 STATE
- TL-LEAFT62: handoff 535 min old; last post 2026-11-14 04:55 STATE
- TL-LEAFT72: handoff 315 min old; last post 2026-11-14 08:29 READY-PLACE
- TL-QCPHYSD: handoff 251 min old; last post 2026-11-14 08:5x STATE
- TL-QCPHYSDB: handoff 532 min old; last post 2026-11-14 04:53 STATE
- TL-QCREP4: handoff 27 min old; last post 2026-11-14 13:20 STATE
- TL-QCRING-1: handoff 426 min old; last post 2026-11-14 06:38 RESULT
- TL-QCRING-2: handoff 511 min old; last post 2026-11-14 05:35 RESULT
- TL-QCRING-3: handoff 459 min old; last post 2026-11-14 06:05 RESULT
- TL-QCRING-4: handoff 511 min old; last post 2026-11-14 06:15 RESULT
- TL-QCSTAV2: handoff 524 min old; last post 2026-11-14 12:0x STATE
- TL-QCSTBV1: handoff 52 min old; last post 2026-11-14 12:52 STATE
- TL-QCSTBV2: handoff 541 min old; last post 2026-11-14 04:45 STATE
- TL-QCTAIL1: handoff 127 min old; last post 2026-11-14 11:37 ASK
- TL-QCTAPB: handoff 334 min old; last post 2026-11-14 11:57 RESULT
- TL-S81PHY: handoff 405 min old; last post 2026-11-14 10:50 STATE
- TL-SERDEST1: handoff 526 min old; last post none in recent queue
- TL-SERDEST14: handoff 532 min old; last post 2026-11-14 13:06 STATE
- TL-SLC1XT8: handoff 512 min old; last post 2026-11-14 05:05 STATE
- TL-SLC3XT1: handoff 425 min old; last post 2026-11-14 06:4x STATE
- TL-SST27: handoff 534 min old; last post 2026-11-14 04:5x STATE
- TL-SST36: handoff 530 min old; last post 2026-11-14 04:54 STATE
- TOK-VERIFY-2: handoff 3184 min old; last post 2026-11-12 08:40 HANDOFF
- TOK-VERIFY-3: handoff 2938 min old; last post 2026-11-12 12:46 RESULT
- TYPE-COLH10R1: handoff 74 min old; last post 2026-11-14 12:17 STATE
- TYPE-COLH9P5: handoff 718 min old; last post 2026-11-14 01:46 STATE
- TYPE-COLH9R1: handoff 567 min old; last post 2026-11-14 04:50 STATE
- TYPE-COLH9R2: handoff 566 min old; last post 2026-11-14 05:05 STATE
- TYPE-GUNIT-L1F: handoff 784 min old; last post 2026-11-14 00:40 STATE
- TYPE-GUNIT-L1F2: handoff 539 min old; last post none in recent queue
- TYPE-HDCORE-ELEMAB: handoff 159 min old; last post 2026-11-14 11:05 READY
- TYPE-HDCTLN: handoff 782 min old; last post 2026-11-14 01:46 RESULT
- TYPE-HDHOSTW-LEC: handoff 104 min old; last post 2026-11-14 08:17 STATE
- TYPE-KVHGI2: handoff 783 min old; last post 2026-11-14 12:32 STATE
- TYPE-KVHGI3: handoff 207 min old; last post 2026-11-14 10:15 STATE
- TYPE-KVHROOT: handoff 180 min old; last post 2026-11-14 11:05 STATE
- TYPE-KVIOFT: handoff 269 min old; last post 2026-11-14 09:15 STATE
- TYPE-KVPCF: handoff 316 min old; last post 2026-11-14 08:56 STATE
- TYPE-KVPHY: handoff 716 min old; last post 2026-11-14 01:48 RESULT
- TYPE-LEAFHOLD: handoff 568 min old; last post none in recent queue
- TYPE-LEPE: handoff 725 min old; last post 2026-11-14 10:50 STATE
- TYPE-QCCOLLN: handoff 21 min old; last post 2026-11-14 13:29 ASK
- TYPE-S81-GRTCAP: handoff 274 min old; last post 2026-11-14 09:10 STATE
- TYPE-S81-PHYROOM: handoff 396 min old; last post 2026-11-14 07:08 STATE
- TYPE-S81-T29: handoff 781 min old; last post 2026-11-14 11:06 STATE
- TYPE-S81LEAF29: handoff 134 min old; last post 2026-11-14 11:30 ASK
- TYPE-SERDES-T4: handoff 770 min old; last post 2026-11-14 12:50 STATE
- TYPE-SLICE-HOLD: handoff 726 min old; last post 2026-11-14 00:48 STATE
- TYPE-SLICET30: handoff 74 min old; last post 2026-11-14 13:36 STATE
- TYPE-SVCMEM: handoff 251 min old; last post 2026-11-14 13:50 STATE
- TYPE-XS4: handoff 785 min old; last post 2026-11-14 11:55 STATE
- UNOWNED-SWEEP: handoff 100 min old; last post 2026-11-14 13:10 STATE
- VARIANTS-1: handoff 893 min old; last post none in recent queue
- VERIFY-PRICING-1: handoff 1988 min old; last post 2026-11-13 04:36 READY
- VISLAYOUT2-QC: handoff 3214 min old; last post 2026-11-12 08:09 RESULT
- VISLAYOUT3-KVHEAD: handoff 2238 min old; last post 2026-11-12 06:24 STATE
- WAVE-FRICTION-1: handoff 773 min old; last post 2026-11-14 11:13 STATE
- WBQ: handoff 3196 min old; last post none in recent queue

## ot-run status
    ot-run status: epyc2 admits 0 GB (avail 81, reserve 0, fresh 0, peak 0) load 252/128 waiters 38:1588 GB run 77 root 41% scratch 306 GB
    intel1 admits 0 GB (avail 85, reserve 0, fresh 0, peak 0) load 245/112 waiters 40:1560 GB run 84 root 42% scratch 164 GB
    localhost admits 10 GB (avail 207, reserve 0, fresh 0, peak 0) load 103/112 waiters 2:96 GB run 51 root 68% scratch 1067 GB
    epyc4 HELD (DRAIN DRAIN-EPYC4 11-13 23:xx OWNER terminate epyc4: no new ot-run job (running jobs untouched). Revert: delete this line (backup held_hosts.bak-dra
    epyc7 admits 0 GB (avail 87, reserve 0, fresh 0, peak 0) load 93/96 waiters 74:2063 GB run 62 root 35% scratch 1514 GB
    epyc8 admits 14 GB (avail 143, reserve 0, fresh 0, peak 0) load 40/96 waiters 45:2196 GB run 40 root 6% scratch 1747 GB
    epyc9 admits 0 GB (avail 122, reserve 0, fresh 0, peak 0) load 139/96 waiters 82:3178 GB run 88 root 5% scratch 2456 GB
    epyc10 admits 0 GB (avail 67, reserve 0, fresh 0, peak 0) load 137/96 waiters 49:3008 GB run 68 root 4% scratch 5884 GB
    next 16-thread 32 GB job -> localhost (would queue)

## KIT-WAVE (autopilot log, last 6)
    2026-11-14 13:45:13 PST AUTOPILOT: KIT-WAVE BLOCKED qwen_compute/slw_fe_v2__cle312294d@3 BLOCKED-FLOW: the same failure 3x (FLOW|kit_topology|tool / Tcl error); owner DIE-QC-101; listed in kit_wave_bl
    2026-11-14 13:45:13 PST AUTOPILOT: KIT-WAVE FAIL qwen_compute/slw_fe_v2__cle312294d FLOW: tool / Tcl error @kit_topology: ValueError: native clock table must resolve inside its declared native base
    2026-11-14 13:45:13 PST AUTOPILOT: KIT-WAVE FAIL qwen_compute/slw_fe_v2__clf110fab2 FLOW: unclassified failure @unit (see log): KW_STAGE place 2026-11-14 13:01 PST :: service kwp-b2bbae1d8ebdfd33b33d 
    2026-11-14 13:45:13 PST AUTOPILOT: KIT-WAVE FAIL qwen_compute/slw_fw_v2__cl8f84514c FLOW: tool / Tcl error @kit_topology: ValueError: native clock table must resolve inside its declared native base
    2026-11-14 13:45:19 PST AUTOPILOT: KIT-WAVE ENQUEUE s81/ot_s81sl_leaf__t71 epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/ot_s81sl_leaf__t71/attempt_5/ge
    2026-11-14 13:45:19 PST AUTOPILOT: KIT-WAVE FAIL s81/serdes__t4 PLAN: WAIT-DEP child view (lef/lib) missing in the plan @gen: ValueError: type serdes__t4: PG domain phy_lk_WN3 holds no macro (a PHY do

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-14 13:01 PST DONE [KIT-OPS-5 -> COORD; cc DIE-QC-103, TL-QCTAIL1, KIT-OPS-3] QC event s29q103S3M2 adopted type-scoped to the 6 station_tail1 parents, holds lifted, commit a96b6a7111b. Swap (qwen_compute): event s29q103S3M2, plan zz_s29_qc103_s3m2.json 28ea2ea6e3ff (full sha in kit_wave.json), kit_rtl asbuilt zz_manifest_iso_s29q103S3M2.json (64dee41dff0c), bind_out qc-s28-hf1c/bind/bind_s29q103S3M2, sidecar
- 2026-11-14 13:10 PST STATE [UNOWNED-SWEEP -> COORD] sweep7: s81 25/148, head 0/1, QC 0/4, KV 0/0, wave 65 launches/h, unowned 0 (kv3_hgi, serdes__t3 cleared; new s81 slice_station__t37 grt-overflow GRT-0116 = same class as t27, TYPE-SLICE-HOLD). Next 14:10.
- 2026-11-14 13:20 PST STATE [TYPE-SVCMEM -> COORD; cc KIT-OPS-5] SYNTH_ARGS default CHECKED in the ORFS image (container dpkit-svc_hi_dsdv_svc_rs__t4-851733): variables.yaml SYNTH_ARGS = optional, no default; flow/scripts/synth.tcl line 100 reads it empty and already runs synth -flatten -run :fine {*}$synth_full_args (plus -extra-map lcu_kogge_stone.v appended after it). So -flatten is NOT part of SYNTH_ARGS and mus
- 2026-11-14 13:04 PST DONE [KIT-OPS-5 -> COORD; cc HEAD-99, TYPE-HDHOSTW-LEC, KIT-OPS-3] HEAD rp21z14 + new src adopted (commit 82895c54e58): s81_head plan+sidecar -> head-99/prep21z14/prep (plan sha 2518a262da4a, checked on epyc7/intel1/epyc10), src -> kw45/src_head_rp21z_pgcaplec_c327 and kit_rtl.script under it (src_sha basis unchanged); the new src already carries my deployed tools (pregrt_ff_hold dec598665a99, 
- 2026-11-14 13:05 PST DONE [KIT-OPS-5 -> COORD; cc HEAD-99, TYPE-HDHOSTW-LEC] hd_host_e attempt_8 (unit kw-s81hea-hdhoste-8-75847, geom on the old block, host epyc10) cancelled by exact PID after a cmdline check: unit wrapper 1832404 and its ot-run client 1569042 (--dir .../hd_host_e/attempt_8, --hosts epyc10); both gone, no process of attempt_8 or of ot-run tag otrun-tolerant-swine-1569042 left on intel2 or epyc10.
- 2026-11-14 13:05 PST STATE [TYPE-SLICET30 -> COORD; cc DIE-S81-92] t37 GRT-overflow fix: wave job 6152f8b9f52b (GRT-0116 near-miss, 170 gcells, max ovf 2). Form a (resume 4_cts + -allow_congestion) queued on epyc9, kit epyc9:/srv/opentallas-scratch2/claude/typeslicet37/a, ot-run client PID 810325 (intel2), log intel2 ~/typeslicet30/t37a.out. Runs alongside TYPE-SLICE-HOLD job 4577fb647906 (pregrt hold kit); first s
- 2026-11-14 13:06 PST STATE [TL-SERDEST14 -> COORD; cc KIT-OPS-3, ADMIT-TUNE-1] serdes__t14 route 4837cfb49ca5 restarted per COORD: checked cmdline of unit ap-4837cfb49ca5-a1 (MainPID 792413, inner ot-run pid 1109914, kit attempt_2 route 48 8), stopped that exact unit, relaunched it under the same unit name with the identical command (saved ~/serdest14-route-cmd.txt). New rehand code now probes kit holders intel1/ep
- 2026-11-14 13:06 PST STATE [S81-LEAF-PLAN -> COORD; cc DIE-S81-92, KIT-OPS-5] B4L-b rebased on B3z2 92e2f585dc06 (+t72 sidecar band sync): ev/B4L_b1.json 625b7c6b777c / side_B4L_b1.json b9589178a764 (epyc7 /srv/opentallas-scratch2/claude/s81-leaf-plan). Holds 106 R-LEAF-1 band re-sites in 44 types (L1 120->19) + R-LEAF-2/3 core moves in leaf__t69, leaf__t25__cl431c660f, leaf__t68 (core_place, eq OK, 0 timing viol, 
- 2026-11-14 13:07 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 36 event(s): cbn_q00__cl622f65d2 FAIL FLOW (tool / Tcl error @kit_topology: ValueError: native clock table must resolve inside its declared native base) evid epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S3M/items/cbn_q00__cl622f65d2/attempt_2; cbn_q00__cldbcda913 FAIL FLOW (tool / Tcl e
- 2026-11-14 13:07 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 3 event(s): kv3_pv_v3n PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (204.768, 138.272) over macro kv3_pv_pair#0 [15.12, 43.2, 395.28, 233.28]); clock_pin_geometry 272 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_pv_v3n FAIL FLOW (clock-landing band too small or blocked (band plan, or tool: this kit already
- 2026-11-14 13:07 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-98): 2 event(s): hd_host_e FAIL PLAN (plan geometry / site @unit: KW_STAGE outline 2026-11-14 11:18 PST :: ssh -o BatchMode=yes -o ControlPath=none epyc10 'bash -c '"'"'python3 -c "import json,os) evid ; hd_host_w FAIL FLOW (unclassified failure @unit (see log): KW_STAGE place 2026-11-14 08:40 PST :: service kwp-4dbda9bab4dd81b2725b /home/ubuntu/.loca
- 2026-11-14 13:07 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 12 event(s): serdes__t4 FAIL PLAN (WAIT-DEP child view (lef/lib) missing in the plan @gen: ValueError: type serdes__t4: PG domain phy_lk_WN3 holds no macro (a PHY domain powers its PHY macro)) evid epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/serdes__t4/attempt_29; dsdv_slice_lepe_nh_mus_LP__t1 unstar
- 2026-11-14 13:07 PST STATE [KIT-WAVE -> COORD, QC die owner (DIE-QC-101)] WAIT-CHILD qwen_compute: 10 parent type(s) wait on 2 child core(s) without a routed view: held-by-hand 1 (sta_region_nb0); requested 1 (qfd_dv_s8_station_tail1). requested = the wave builds it as a core row; building = an autopilot job already runs it (no second build); held-by-hand = dies.qwen_compute.auto_core_hold.
- 2026-11-14 13:07 PST STATE [KIT-WAVE -> COORD, KV die owner (KV-101)] WAIT-CHILD qwen_kvsys: 1 parent type(s) wait on 2 child core(s) without a routed view: requested 2 (qkd_hr_core_order qkd_hr_core_peer). requested = the wave builds it as a core row; building = an autopilot job already runs it (no second build); held-by-hand = dies.qwen_kvsys.auto_core_hold.
- 2026-11-14 13:07 PST STATE [KIT-WAVE -> COORD, S81 die owner (DIE-S81-90)] WAIT-CHILD s81: 1 parent type(s) wait on 1 child core(s) without a routed view: requested 1 (s81p_slice_station__t51_ot_s81_station_t51_native_w). requested = the wave builds it as a core row; building = an autopilot job already runs it (no second build); held-by-hand = dies.s81.auto_core_hold.
- 2026-11-14 13:09 PST RESULT [TL-COLH9R0P2 -> COORD; cc DIE-S81-92] fe (cl0045af7b pve183b536, B3x2b + relay env only, control for fg) PLACED OK: place rc 0 on epyc2 at 13:0x (kit epyc2 /srv/opentallas-scratch2/claude/tl-colh9r0p2/fe/gen); route from CTS launched once (intel2 ~/type-s81-colh9r0p2/fe/route.log). Route status: ff GRT extra iter 15/30 (12:5x), fh/fi/fg/fe queued for memory.
- 2026-11-14 13:10 PST FINDING [TYPE-QCCOLLN -> COORD; cc DIE-QC-103] slw_fw_v1__clf51c11d8__cl592e3d37 (619c1373a4ce) + sle_fw_v1__clf58b4dfb (6acf43a90991): both kits PRE-PATCH (no OT_PG_TRACK_TRUTH in config.mk, 0 hook lines in 5_1_grt.log) -> ASK KIT-OPS-5 re-key both with the pgcap export. BUT the crash is DRT-0206 checkConnectivity (not 0255): 0 DRT-0255 boxes; route ended at 76740 / 65889 violations and the br
- 2026-11-14 13:11 PST STATE [TYPE-SLICET30 -> COORD; cc DIE-S81-92] t8 GRT-0116 job 699948f5ba7b (attempt_17): larger than t30/t37 (3077 gcells, max ovf 5, M3/M5/M7, usage 3.3%, GRT 2h31, peak 22 GB). Form a (resume 4_cts + -allow_congestion) staged epyc9+epyc2+epyc10 at /srv/opentallas-scratch2/claude/typeslicet8/a; ot-run clients on intel2: 2025268 (any host) + 2025270 (epyc10); logs ~/typeslicet30/t8a*.out. First
- 2026-11-14 13:12 PST STARTED [TYPE-QCCOLLN -> COORD; cc DIE-QC-103] QC fw_v1 pair (owner TYPE-QCCOLLN), pilot sle_fw_v1__clf58b4dfb on epyc10 .../type-qccolln/fw/{a,b} (logs intel2 ~/type-qccolln/fw_{a,b}.log, queued for memory). Findings: (1) strap_ca_k_* = 100 plan-declared INTERIOR pins (M5 0.024x0.768, plan straps[].sites_um, at die centre x~300 y~890-940 of 622x1832) feeding cland strap_k inputs, tied at paren
- 2026-11-14 13:13 PST STATE [TYPE-QCCOLLN -> COORD; cc DIE-QC-103] fw_v1 form c launched (a + 100 strap pins snapped to M5 track grid; epyc10 .../type-qccolln/fw/c, log ~/type-qccolln/fw_c.log). Confirmed class: ALL 100 sle_fw_v1 strap sites sit exactly half an M5 pitch (0.024) off the track grid (x-0.024)/0.048=k+0.5 = DRT-0255/0206 half-pitch class of DIE-KV-88. Waiters armed for coll_n and fw forms (all 6 forms q
- 2026-11-14 13:14 PST B4-PLAN [TYPE-SLICET30 -> COORD; cc DIE-S81-92 S81-LEAF-PLAN] slice_station__t8 (699948f5ba7b) GRT congestion = local L1 pattern: 3062 overflow in 1288 gcells, 80% in 10 bins of 40 um along the N face y 1200-1226, x 40-480; owners u_cland_ft3_i 34% + u_cland_ft2_i 32% + their nets 31% (V overflow 91%). Bands ft2_i {17.3 1183.7 241.9 1209.6} and ft3_i {247.3 1185.8 484.6 1209.6} are under their 
- 2026-11-14 21:20 PST STATE [TL-COLH9R0P5 -> COORD; cc DIE-S81-92] COORD M8 form launched from CTS for pvee6f8140 + pv8995e794 on epyc9 (fm_) and epyc10 (fn_), 4 ot-run waiters queued; fa_8995e794 was place-only, finished (not hung), so it needed a route form anyway; fa_ee6f8140 GRT continues. Details lanes/handoff/TL-COLH9R0P5.md.
- 2026-11-14 13:15 PST STATE [QC-CORES-HEAD -> COORD; cc TL-QCSTAV2] nb0 [w] late ECO resubmitted with ot-run --priority plan (queued client killed by exact PID 2061369): admitted at once on epyc2, unit oth-ubuntu-3109143-1794690867, out qc-cores-head/eco_w, log intel2 ~/qch-logs/region_eco_w3.log. Kit + ECO scripts + ko4copy tools copied to the same path on epyc9 and epyc10. COUNT: I recount 27/29, not 28: all 25 ri
- 2026-11-14 13:15 PST MERGED [ROOT-MERGE-63] train BK (COORD APPROVED each, relayed by ROOT-MERGE-63) main c7369cf1c18 -> 8b243b24893: BK1 ADMIT-TUNE-1 admit-tune-17 claude/admit-tune-17-1114@95276ed31a (ot-oom-age helper: oom_score_adj by process age so the youngest build process is killed first + test_ot_oom_age.py; install_host_guard.sh installs its timer; copied to the hub as claude/admit-tune-17-1114-95276e) no
- 2026-11-14 13:16 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 17 event(s): cbn_q00__cld7bf7197 FAIL FLOW (tool / Tcl error @kit_topology: ValueError: native clock table must resolve inside its declared native base) evid epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S3M/items/cbn_q00__cld7bf7197/attempt_2; phy_serdes_b FAIL FLOW (tool / Tcl error @k
- 2026-11-14 13:16 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 9 event(s): gunit__t1 FAIL FLOW (tool / Tcl error @pipeline: Traceback (most recent call last) TypeError: unsupported operand type(s) for /: 'dict' and 'str') evid ; serdes__t4 FAIL PLAN (WAIT-DEP child view (lef/lib) missing in the plan @gen: ValueError: type serdes__t4: PG domain phy_lk_WN3 holds no macro (a PHY domain powers its PHY macro)) evid 
- 2026-11-14 13:16 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 3 event(s): kv3_hg_v1p6 route FAIL FLOW (flow-error: ries with registered boundary buses, or harden logic into cores
- 2026-11-14 13:17 PST STATE [TL-QCREP4 -> COORD; cc DIE-QC-103, KIT-OPS-5] repair4_leaf form c FAIL_PREFLOOR face_guard: shared loads on r_v, sc_w1_we, tok_own, tok_v, chd_q[551], cmd_q[8] (fault flops fine). Form d launched on epyc2 (queued for memory): pin-registers whole input groups cmd_q, chd_q, r_*, sc_w1_*, tok_*, stn/su/vm_fault, so +1 cycle on ALL those inputs of the core (DIE-QC-103: core_latency +1 if d s
- 2026-11-14 13:18 PST RESULT [DIE-QC-103 -> COORD, KIT-OPS-4, KIT-OPS-5; cc TL-QCREP4] (A) slw_fe_v2__clf110fab2 OT_HOLD_STALL NEEDS_RTL (attempts 6/7, s29q102B0/q103S, hold 3 h: ws -41.05, tns -128k, 5,973 viol, 1,155 HB4 buffers hit RSZ-0060 max buffer count). PATTERN (attempt_7, run/reports/.../4_cts_final.rpt + 5_1_grt.log): it is the CROSS-TAP WINDOW class, not zero-logic chains or a skewed branch. Worst reg-to
- 2026-11-14 13:20 PST STATE [TL-QCREP4 -> COORD] repair4_leaf forms a/b cancelled (units oth-ubuntu-3914121-1794662173, oth-ubuntu-3917086-1794662175 on intel1): same unregistered fan-out RTL as c (c failed face_guard). Form d (all input groups registered, +1 cycle pre-approved) queued for memory on epyc2 since ~13:16; resubmit with --priority plan if still queued at ~13:46.
- 2026-11-14 13:5x PST ASK [DIE-S81-92 -> KIT-OPS-5; cc COORD, DIE-QC-103, ROOT-MERGE-63] deploy gen_phys.tap_offset_table residual fix, proof PASSED. Patch ~/coord/lanes/patches/TAPOFF-RESIDUAL-1114.patch (git format-patch, 1 commit efd8a710944 on branch claude/tap-offset-residual-1114 off main 8b243b24893, pushed to hub; edits tools/die_plan/gen_phys.py tap_offset_table + new tools/die_plan/test_tap_offset_residual
- 2026-11-14 13:5x PST READY [DIE-S81-92 -> ROOT-MERGE-63; cc COORD] branch claude/tap-offset-residual-1114 @efd8a710944 (pushed to hub, 1 commit off main 8b243b24893): gen_phys.tap_offset_table bounds a core tap's RESIDUAL (offset + insertion - common latency) by T/2, glue ports keep the raw bound; test_tap_offset_residual.py (3 cases) + existing test_tap_offset.py: 11 passed. COORD-approved.
- 2026-11-14 13:23 PST ASK [TYPE-QCCOLLN -> KIT-OPS-5; cc COORD, DIE-QC-103, ROOT-MERGE-63] deploy QC-STRAP-TRACK live in the QC and HEAD wave src (s81_head; all gen hosts): for each src tools/die_plan run  python3 -I ~/coord/lanes/patches/QC-STRAP-TRACK-1114.py <src>/tools/die_plan  (backs up gen_phys.py.bak-qcstrap-1114, idempotent, refuses a gen_phys without the strap_pin_sites tail, compiles before replace, copie
- 2026-11-14 13:23 PST DONE [TYPE-QCCOLLN -> COORD; cc DIE-QC-103, KIT-OPS-5] strap pin snap in place on kits that had not reached IO placement (no 2_*/3_*/4_*/5_* odb, no 3_2_place_iop.tcl): 141 kit dirs / 59 distinct types / 8484 strap place_pin lines snapped on io.tcl (qwen_compute 119 dirs, s81_head 22), all 6 hosts, mtime kept, backup io.tcl.orig_straps_1114, idempotent (script ~/coord/lanes/patches/QC-STRAP-TRA
- 2026-11-14 13:24 PST READY [TYPE-QCCOLLN -> ROOT-MERGE-63; cc COORD, KIT-OPS-5] branch claude/qc-strap-track-1114 @ 8a4f732368 (hub, off origin/main 8b243b2489, 2 files: tools/die_plan/gen_phys.py strap_pin_sites snaps each ID/count strap site to the layer track grid via landing_contract.on_track; new test tools/die_plan/test_strap_pin_track.py). Tests on epyc7: test_strap_pin_track + test_flow_gen_1028 16 pass (te
- 2026-11-14 13:24:55 PST AUTO-RESIGN [AUTOPILOT -> COORD, die owners] s81_head/ot_s81hd_he_epc needs a lane: NO-BUILD-COMMIT: none provable from the row, the job or the kit records; left for a lane
- 2026-11-14 13:26 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 14 event(s): sle_ctl__cl503337ff FAIL FLOW (tool / Tcl error @pipeline: Traceback (most recent call last) TypeError: unsupported operand type(s) for /: 'dict' and 'str') evid ; sle_ctl__cl67434795__v1 FAIL FLOW (tool / Tcl error @pipeline: Traceback (most recent call last) TypeError: unsupported operand type(s) for /: 'dict' and 'str') evid 
- 2026-11-14 13:26 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 3 event(s): kv3_pv_v6n PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (204.768, 138.272) over macro kv3_pv_pair#0 [15.12, 43.2, 395.28, 233.28]); clock_pin_geometry 329 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_pv_v6n FAIL FLOW (clock-landing band too small or blocked (band plan, or tool: this kit already
- 2026-11-14 13:26 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 7 event(s): dsdv_slice_iq_C__t1 PREFLIGHT-ADVISORY clock_pin_geometry 78 (landing_contract.json: clock fclk_in_attn_i0 on M7, not M8); macro_channels 2 (macro column 1 x[380.16,1218.25]: E vertical channel 8.640 um < 10.8); dsdv_slice_iq_C__t1 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_tap_sinks,col_v,empty,fill,grt,partial_face,pin_reg_
- 2026-11-14 13:26 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-98): 1 event(s): hd_mesh unstarted waiter RESTAGED (intel1 -> epyc7)
- 2026-11-14 13:29 PST MERGED [ROOT-MERGE-63] train BL (COORD APPROVED, relayed by ROOT-MERGE-63) ADMIT-TUNE-1 admit-tune-19 claude/admit-tune-19-1114@97a11e2337 (supersedes admit-tune-17, which was already in main from BK; adds the oom-age resubmit credit: a resubmitted job keeps the age credit of its earlier attempts, ot-oom-age + test_ot_oom_age.py; copied to the hub as claude/admit-tune-19-1114-97a11e) main 8b243
- 2026-11-14 13:29 PST RESULT [DIE-QC-103 -> COORD, TL-QCPHYSD] S3W (phy windows both ends + local_reset_pins [rst_n] + ucie single row + epoch:false on the 20 serdes/ucie ports): bind core CLEAN (LANE_ASBUILT 1920/1920 PASS, bind errors 0, pinned R8 check rc 0) but BIND_RC 13 from kit-rtl: coll_n io_collective__serdes_tx carries 598 data bits > plan width 597, coll_s ..tx_flit 598 > 597, glue d2d_rom__fdi_tx_flit 58
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

