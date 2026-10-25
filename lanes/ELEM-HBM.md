# ELEM-HBM lane (2026-10-24) — hardened views for HBM B2r2 hard cores
branch claude/elem-hbm-1024 (worktree localhost:~/wt/elem-hbm), scratch localhost:/srv/opentallas-scratch/claude/elem-hbm
Scope (COORD owner correction 2026-10-24 07:43): B2r2 plan (claude/hbm-arch-1024 3277b5e78b) 436 hard cores / 49 types; close through
new kit gates (sdc_lint, face_guard; main 4b7b2b3e64) at TT setup / FF hold, 833 ps, spread <= 80. 10-21 element list dropped.
## current step (2026-10-24 08:02)
- infra committed 0992a92d5d: views_b2r2.py/json, gen_core_kit_hbm.py (sdc_lint gen+pre-synth, face_guard on core pins,
  corners SS/FF/TT + face-flop CK spread, WC flow corner), run_kit_hbm.sh, corners_hbm.tcl, face_guard_core.py.
- dry gen of all 240 views: 123 generate; 117 blocked: split-piece cut->canonical maps (tkm 33, pgslice 31, coll_q2 3,
  hc tail_rest 2, bankq_ft 2, sfu ctl/opstore 2) -> SPLIT sub-agent; no recipe (~35 views) -> RECIPES sub-agent;
  SM halves (256 placed) -> SM sub-agent. Each on its own branch claude/elem-hbm-{split,recipes,sm}-1024.
- pilots on localhost (/srv/opentallas-scratch/claude/elem-hbm/kits/*): argmax, gq_land, gq_issue, bankq0 lanes0_2,
  idx score r0c0_k0h0, sfu lane0.
- split proposal posted to lanes/HBM-ARCH.md (2026-10-24 07:43); inventory: 819 placed, 210 modules, 240 distinct pin-table views.
- building on claude/core-hbm-1023 harden tooling (gen_core_kit.py, split RTL tops, recipes).
## results
## OWNER?
- face_guard on HARD-CORE pins: legacy d4g cores are NOT registered on every pin (pilot synth: argmax 372/1118 bits OK:
  feedthrough 360, dropped 256, shared 112; gq_land 3794/3879: vm_kq feedthrough 50, ld_desc dropped 12). face_guard was
  written for planned partition face registers; KVG3-CORES runs it report-only on cores. Making it gating for cores
  means pin registers in ~every core RTL = +1..2 cycles per core crossing to report to the model (AGENTS.md). Until
  ruled: recorded per view as a separate FAIL column; timing verdicts (TT setup / FF hold / spread) reported as is.

## SIGNOFF re-signoff list (2026-10-24 08:04 PDT, main 4ab1ec1399, results/signoff_1024/) — SUPERSEDED by the SIGNOFF list below (rec SS there was the TT slack)
Recipe: tools/die_plan/signoff.py (TT setup / FF hold with std boundary-hold overlay / TT report, DRV, unconstrained, pin-flop spread <= 80 TT+FF, sdc_lint, face_guard, DRC/antenna). Routed DBs of every closed block were on the wiped old fleet -> NEEDS RE-RUN; re-close from the kit and run `signoff.py run --run-dir <run> --out <dir>` before calling it closed.

### hbm: 55 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 55
- last record already FAILS the standard (re-close, not just re-STA): ot_hbm_svc_pc_ctrl_leaf_cfg_h9b (recorded TT pin-flop spread 117.5 ps > 80, recorded FF pin-flop spread 117.7 ps > 80); ot_hgi_qdq_transport_rslice (recorded TT pin-flop spread 84.7 ps > 80, recorded FF pin-flop spread 80.8 ps > 80)
- NO kit in repo (5): ot_hbm_idx_qctl_static, ot_hbm_static_cfg_collar_idx256r, ot_hbm_su_static_cxport_ij_q, ot_hgi_qw_dec, ot_static_run_target
- NEEDS RE-RUN (module x instances, rec SS/FF ps, rec spread TT/FF): hfd_ep_static x6 (217.23/8.0, 53.4/49.3); hfd_hgi_vm_calendar_f20 x4 (25.04/12.63, 25.3/21.8); hfd_vms_bank_native_q0_faces x32 (17.45/8.62, 0.1/0.0); hfd_vms_wq2_merge x32 (335.22/21.14, 19.5/20.4); ot_hbm_argmax_static_sw_vm_r2 x1 (84.29/16.79, 25.5/23.3); ot_hbm_fault_leaf x24 (434.46/29.75, 0.8/0.5); ot_hbm_fault_leaf_n8_s0 x4 (432.71/30.46, 0.3/0.3); ot_hbm_host_cfg_leaf_nw x4 (417.66/20.52, 10.1/10.7); ot_hbm_host_cp_rxs x1 (2.05/18.8, 54.0/50.8); ot_hbm_idx_qctl_static x4 (227.91/22.75, 14.8/14.7); ot_hbm_idx_query_static x4 (12.0/14.52, 79.6/75.3); ot_hbm_idx_rootctl_static_am x1 (23.17/20.15, 76.3/63.7); ot_hbm_idx_vm_query_static_n12 x4 (23.35/13.64, 49.4/45.7); ot_hbm_idx_xq_node_static x3 (362.14/9.92, 31.3/30.1); ot_hbm_pc_refresh_cfg x4 (125.96/24.03, 6.1/6.4); ot_hbm_sm_vm_wr_q_t_lanes4 x4 (92.94/26.15, 28.1/26.6); ot_hbm_static_cfg_collar x5 (50.96/22.05, 22.6/22.4); ot_hbm_static_cfg_collar_idx256r x1 (40.72/27.12, 36.2/33.3); ot_hbm_status_join_fa x1 (409.15/28.92, 9.4/6.6); ot_hbm_su_bridge_release_s x4 (7.34/30.52, 11.9/7.6); ot_hbm_su_programme_root_h5 x1 (346.8/21.53, 13.1/13.4); ot_hbm_su_static_cxport_dl_q x16 (88.64/29.09, 56.7/54.7); ot_hbm_su_static_cxport_dl_s x16 (204.45/29.5, 17.1/16.9); ot_hbm_su_static_cxport_ij_q x4 (67.13/26.92, 39.6/37.4); ot_hbm_su_static_cxport_ij_s x4 (88.31/15.51, 64.6/60.8); ot_hbm_su_static_cxport_rc_q x4 (28.42/27.54, 26.3/23.9); ot_hbm_su_static_cxport_rc_s x4 (9.9/27.04, 43.5/41.4); ot_hbm_su_static_qcore_r13 x4 (4.27/10.87, 52.6/49.9); ot_hbm_su_static_sfustore_hw x4 (175.55/23.13, 71.7/64.4); ot_hbm_su_stree_leaf x4 (391.8/27.45, 7.3/7.3); ot_hbm_su_stree_root x1 (426.1/19.37, 12.5/13.4); ot_hbm_svc_pc_ctrl_leaf_cfg_h9b x64 (29.75/13.65, 117.5/117.7); ot_hbm_svc_stack_fault x4 (346.67/7.33, 2.4/2.2); ot_hbm_svc_vmdel_lane_n x32 (85.47/3.23, 68.2/61.5); ot_hbm_svc_wbw_copy x4 (425.86/28.95, 4.9/4.2); ot_hbm_xp_aq_tree13_fmt x8 (65.07/15.27, 17.7/16.9); ot_hgi_coll_gq_land x4 (11.98/16.83, 69.9/66.1); ot_hgi_coll_inj_copy x4 (306.68/28.65, 3.0/2.6); ot_hgi_coll_inj_idx_join_rg x4 (134.13/5.27, 47.6/43.9); ot_hgi_coll_kq_share2_leaf x16 (253.01/18.21, 44.5/42.9); ot_hgi_coll_ring_b_stop x4 (210.92/8.29, 58.8/57.2); ot_hgi_qdq_lg_port_group_r2 x16 (329.97/19.9, 17.4/17.5); ot_hgi_qdq_transport_ctl_r4 x4 (269.77/12.01, 28.6/22.8); ot_hgi_qdq_transport_rslice x16 (287.66/6.28, 84.7/80.8); ot_hgi_qdq_transport_wslice x16 (314.49/23.98, 37.4/37.1); ot_hgi_qw_dec x4 (50.84/18.4, None/None); ot_hgi_sfu_lg_pair_tap_leaf x16 (306.16/5.09, 53.6/51.0); ot_hgi_sfu_lg_pair_tap_leaf_term x16 (378.05/8.54, 48.5/46.1); ot_hgi_sm_xload_cl2_bdring x8 (48.29/22.86, 25.4/24.2); ot_hgi_sm_xload_cl2_bfqg x32 (115.25/11.69, None/None); ot_hgi_sm_xload_cl2_ctlx x4 (8.26/5.9, 79.8/74.6); ot_hgi_sm_xload_xq_pegress x8 (82.21/12.05, 32.9/31.4); ot_pdie_ucie_col x1 (229.17/10.65, 14.4/13.7); ot_static_run_target x16 (262.51/27.37, 15.0/15.5); ot_vms_status4_static x1 (344.22/29.09, 2.6/2.7)

### hbm_b2r2: 51 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 51
- last record already FAILS the standard (re-close, not just re-STA): ot_hbm_svc_pc_ctrl_leaf_cfg_h9b (recorded TT pin-flop spread 117.5 ps > 80, recorded FF pin-flop spread 117.7 ps > 80); ot_hgi_qdq_transport_rslice (recorded TT pin-flop spread 84.7 ps > 80, recorded FF pin-flop spread 80.8 ps > 80)
- NO kit in repo (5): ot_hbm_idx_qctl_static, ot_hbm_static_cfg_collar_idx256r, ot_hbm_su_static_cxport_ij_q, ot_hgi_qw_dec, ot_static_run_target
- NEEDS RE-RUN (module x instances, rec SS/FF ps, rec spread TT/FF): hfd_ep_static x6 (217.23/8.0, 53.4/49.3); hfd_hgi_vm_calendar_f20 x2 (25.04/12.63, 25.3/21.8); hfd_vms_bank_native_q0_faces x16 (17.45/8.62, 0.1/0.0); hfd_vms_wq2_merge x16 (335.22/21.14, 19.5/20.4); ot_hbm_argmax_static_sw_vm_r2 x1 (84.29/16.79, 25.5/23.3); ot_hbm_fault_leaf_n8_s0 x2 (432.71/30.46, 0.3/0.3); ot_hbm_host_cfg_leaf_nw x2 (417.66/20.52, 10.1/10.7); ot_hbm_host_cp_rxs x1 (2.05/18.8, 54.0/50.8); ot_hbm_idx_qctl_static x2 (227.91/22.75, 14.8/14.7); ot_hbm_idx_query_static x2 (12.0/14.52, 79.6/75.3); ot_hbm_idx_rootctl_static_am x1 (23.17/20.15, 76.3/63.7); ot_hbm_idx_vm_query_static_n12 x2 (23.35/13.64, 49.4/45.7); ot_hbm_pc_refresh_cfg x2 (125.96/24.03, 6.1/6.4); ot_hbm_sm_vm_wr_q_t_lanes4 x2 (92.94/26.15, 28.1/26.6); ot_hbm_static_cfg_collar_idx256r x1 (40.72/27.12, 36.2/33.3); ot_hbm_status_join_fa x1 (409.15/28.92, 9.4/6.6); ot_hbm_su_bridge_release_s x2 (7.34/30.52, 11.9/7.6); ot_hbm_su_programme_root_h5 x1 (346.8/21.53, 13.1/13.4); ot_hbm_su_static_cxport_dl_q x8 (88.64/29.09, 56.7/54.7); ot_hbm_su_static_cxport_ij_q x2 (67.13/26.92, 39.6/37.4); ot_hbm_su_static_cxport_rc_q x2 (28.42/27.54, 26.3/23.9); ot_hbm_su_static_cxport_rc_s x2 (9.9/27.04, 43.5/41.4); ot_hbm_su_static_qcore_r13 x2 (4.27/10.87, 52.6/49.9); ot_hbm_su_static_sfustore_hw x2 (175.55/23.13, 71.7/64.4); ot_hbm_su_stree_leaf x2 (391.8/27.45, 7.3/7.3); ot_hbm_su_stree_root x1 (426.1/19.37, 12.5/13.4); ot_hbm_svc_pc_ctrl_leaf_cfg_h9b x32 (29.75/13.65, 117.5/117.7); ot_hbm_svc_stack_fault x2 (346.67/7.33, 2.4/2.2); ot_hbm_svc_vmdel_lane_n x16 (85.47/3.23, 68.2/61.5); ot_hbm_svc_wbw_copy x2 (425.86/28.95, 4.9/4.2); ot_hbm_xp_aq_tree13_fmt x4 (65.07/15.27, 17.7/16.9); ot_hgi_coll_gq_land x2 (11.98/16.83, 69.9/66.1); ot_hgi_coll_inj_copy x2 (306.68/28.65, 3.0/2.6); ot_hgi_coll_inj_idx_join_rg x2 (134.13/5.27, 47.6/43.9); ot_hgi_coll_kq_share2_leaf x8 (253.01/18.21, 44.5/42.9); ot_hgi_coll_ring_b_stop x2 (210.92/8.29, 58.8/57.2); ot_hgi_qdq_lg_port_group_r2 x8 (329.97/19.9, 17.4/17.5); ot_hgi_qdq_nw_program_leaf x2 (42.22/12.45, 42.3/26.6); ot_hgi_qdq_transport_ctl_r4 x2 (269.77/12.01, 28.6/22.8); ot_hgi_qdq_transport_rslice x8 (287.66/6.28, 84.7/80.8); ot_hgi_qdq_transport_wslice x8 (314.49/23.98, 37.4/37.1); ot_hgi_qw_dec x2 (50.84/18.4, None/None); ot_hgi_sfu_lg_pair_tap_leaf x8 (306.16/5.09, 53.6/51.0); ot_hgi_sfu_lg_pair_tap_leaf_term x8 (378.05/8.54, 48.5/46.1); ot_hgi_sm_xload_cl2_bdring x4 (48.29/22.86, 25.4/24.2); ot_hgi_sm_xload_cl2_bfqg x16 (115.25/11.69, None/None); ot_hgi_sm_xload_cl2_ctlx x2 (8.26/5.9, 79.8/74.6); ot_hgi_sm_xload_xq_pegress x4 (82.21/12.05, 32.9/31.4); ot_pdie_ucie_col x1 (229.17/10.65, 14.4/13.7); ot_static_run_target x8 (262.51/27.37, 15.0/15.5); ot_vms_status4_static x1 (344.22/29.09, 2.6/2.7)
- note: P7 + B2r2 re-pin the closed cores onto plan tracks -> they need a re-harden regardless of DB.

## [SUPERSEDED: SS-based, owner 10-24 rule is TT setup / FF hold] SIGNOFF re-signoff list v2 (2026-10-24 08:06 PDT, main 0f5176689d, results/signoff_1024/README.md + per_die.md)
Recipe tools/die_plan/signoff.py: SS setup, FF hold (std overlay: out min 0 / in min -40), TT report, DRV, unconstrained, pin-flop spread <= 80 TT+FF, sdc_lint, face_guard, DRC/antenna. Every closed block's routed DB was on the wiped old fleet -> NEEDS RE-RUN. NOTE: closure_loop verdicts were accepted at TT setup; 'rec SS' below is the SS-library slack (metrics.ss_sensitivity_ps). Paper FAIL = re-close needed (not just re-STA). After re-close: `signoff.py run --run-dir <ORFS run> --out <dir>` must say SIGNED.

### hbm: 55 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 55 (paper FAIL 32, paper PASS 23)
- hfd_ep_static x6: NEEDS RE-RUN | rec SS -14.52 (TT 217.23) FF 8 spread TT/FF 53.4/49.3 | kit repo | paper FAIL
- hfd_hgi_vm_calendar_f20 x4: NEEDS RE-RUN | rec SS -373.14 (TT 25.04) FF 12.63 spread TT/FF 25.3/21.8 | kit repo | paper FAIL
- hfd_vms_bank_native_q0_faces x32: NEEDS RE-RUN | rec SS -266.26 (TT 17.45) FF 8.62 spread TT/FF 0.1/0 | kit repo | paper FAIL
- hfd_vms_wq2_merge x32: NEEDS RE-RUN | rec SS 249.78 (TT 335.22) FF 21.14 spread TT/FF 19.5/20.4 | kit repo | paper PASS
- ot_hbm_argmax_static_sw_vm_r2 x1: NEEDS RE-RUN | rec SS -261.08 (TT 84.29) FF 16.79 spread TT/FF 25.5/23.3 | kit repo | paper FAIL
- ot_hbm_fault_leaf x24: NEEDS RE-RUN | rec SS 390.14 (TT 434.46) FF 29.75 spread TT/FF 0.8/0.5 | kit repo | paper PASS
- ot_hbm_fault_leaf_n8_s0 x4: NEEDS RE-RUN | rec SS 387.26 (TT 432.71) FF 30.46 spread TT/FF 0.3/0.3 | kit repo | paper PASS
- ot_hbm_host_cfg_leaf_nw x4: NEEDS RE-RUN | rec SS 317.73 (TT 417.66) FF 20.52 spread TT/FF 10.1/10.7 | kit repo | paper PASS
- ot_hbm_host_cp_rxs x1: NEEDS RE-RUN | rec SS -379.24 (TT 2.05) FF 18.8 spread TT/FF 54/50.8 | kit repo | paper FAIL
- ot_hbm_idx_qctl_static x4: NEEDS RE-RUN | rec SS 46.41 (TT 227.91) FF 22.75 spread TT/FF 14.8/14.7 | kit NOT IN REPO | paper PASS
- ot_hbm_idx_query_static x4: NEEDS RE-RUN | rec SS -382.5 (TT 12) FF 14.52 spread TT/FF 79.6/75.3 | kit repo | paper FAIL
- ot_hbm_idx_rootctl_static_am x1: NEEDS RE-RUN | rec SS -275.36 (TT 23.17) FF 20.15 spread TT/FF 76.3/63.7 | kit repo | paper FAIL
- ot_hbm_idx_vm_query_static_n12 x4: NEEDS RE-RUN | rec SS -336.2 (TT 23.35) FF 13.64 spread TT/FF 49.4/45.7 | kit repo | paper FAIL
- ot_hbm_idx_xq_node_static x3: NEEDS RE-RUN | rec SS 253.9 (TT 362.14) FF 9.92 spread TT/FF 31.3/30.1 | kit repo | paper PASS
- ot_hbm_pc_refresh_cfg x4: NEEDS RE-RUN | rec SS -97.62 (TT 125.96) FF 24.03 spread TT/FF 6.1/6.4 | kit repo | paper FAIL
- ot_hbm_sm_vm_wr_q_t_lanes4 x4: NEEDS RE-RUN | rec SS -202.86 (TT 92.94) FF 26.15 spread TT/FF 28.1/26.6 | kit repo | paper FAIL
- ot_hbm_static_cfg_collar x5: NEEDS RE-RUN | rec SS -303.09 (TT 50.96) FF 22.05 spread TT/FF 22.6/22.4 | kit repo | paper FAIL
- ot_hbm_static_cfg_collar_idx256r x1: NEEDS RE-RUN | rec SS -297.99 (TT 40.72) FF 27.12 spread TT/FF 36.2/33.3 | kit NOT IN REPO | paper FAIL
- ot_hbm_status_join_fa x1: NEEDS RE-RUN | rec SS 289.75 (TT 409.15) FF 28.92 spread TT/FF 9.4/6.6 | kit repo | paper PASS
- ot_hbm_su_bridge_release_s x4: NEEDS RE-RUN | rec SS -44.75 (TT 7.34) FF 30.52 spread TT/FF 11.9/7.6 | kit repo | paper FAIL
- ot_hbm_su_programme_root_h5 x1: NEEDS RE-RUN | rec SS 276.16 (TT 346.8) FF 21.53 spread TT/FF 13.1/13.4 | kit repo | paper PASS
- ot_hbm_su_static_cxport_dl_q x16: NEEDS RE-RUN | rec SS -41.45 (TT 88.64) FF 29.09 spread TT/FF 56.7/54.7 | kit repo | paper FAIL
- ot_hbm_su_static_cxport_dl_s x16: NEEDS RE-RUN | rec SS 3.2 (TT 204.45) FF 29.5 spread TT/FF 17.1/16.9 | kit repo | paper PASS
- ot_hbm_su_static_cxport_ij_q x4: NEEDS RE-RUN | rec SS -92.39 (TT 67.13) FF 26.92 spread TT/FF 39.6/37.4 | kit NOT IN REPO | paper FAIL
- ot_hbm_su_static_cxport_ij_s x4: NEEDS RE-RUN | rec SS -158.57 (TT 88.31) FF 15.51 spread TT/FF 64.6/60.8 | kit repo | paper FAIL
- ot_hbm_su_static_cxport_rc_q x4: NEEDS RE-RUN | rec SS -157.02 (TT 28.42) FF 27.54 spread TT/FF 26.3/23.9 | kit repo | paper FAIL
- ot_hbm_su_static_cxport_rc_s x4: NEEDS RE-RUN | rec SS -237.63 (TT 9.9) FF 27.04 spread TT/FF 43.5/41.4 | kit repo | paper FAIL
- ot_hbm_su_static_qcore_r13 x4: NEEDS RE-RUN | rec SS -291.7 (TT 4.27) FF 10.87 spread TT/FF 52.6/49.9 | kit repo | paper FAIL
- ot_hbm_su_static_sfustore_hw x4: NEEDS RE-RUN | rec SS -80.61 (TT 175.55) FF 23.13 spread TT/FF 71.7/64.4 | kit repo | paper FAIL
- ot_hbm_su_stree_leaf x4: NEEDS RE-RUN | rec SS 328.42 (TT 391.8) FF 27.45 spread TT/FF 7.3/7.3 | kit repo | paper PASS
- ot_hbm_su_stree_root x1: NEEDS RE-RUN | rec SS 379.45 (TT 426.1) FF 19.37 spread TT/FF 12.5/13.4 | kit repo | paper PASS
- ot_hbm_svc_pc_ctrl_leaf_cfg_h9b x64: NEEDS RE-RUN | rec SS -294.93 (TT 29.75) FF 13.65 spread TT/FF 117.5/117.7 | kit repo | paper FAIL
- ot_hbm_svc_stack_fault x4: NEEDS RE-RUN | rec SS 256.22 (TT 346.67) FF 7.33 spread TT/FF 2.4/2.2 | kit repo | paper PASS
- ot_hbm_svc_vmdel_lane_n x32: NEEDS RE-RUN | rec SS -229.87 (TT 85.47) FF 3.23 spread TT/FF 68.2/61.5 | kit repo | paper FAIL
- ot_hbm_svc_wbw_copy x4: NEEDS RE-RUN | rec SS 378.02 (TT 425.86) FF 28.95 spread TT/FF 4.9/4.2 | kit repo | paper PASS
- ot_hbm_xp_aq_tree13_fmt x8: NEEDS RE-RUN | rec SS -282.54 (TT 65.07) FF 15.27 spread TT/FF 17.7/16.9 | kit repo | paper FAIL
- ot_hgi_coll_gq_land x4: NEEDS RE-RUN | rec SS -337.75 (TT 11.98) FF 16.83 spread TT/FF 69.9/66.1 | kit repo | paper FAIL
- ot_hgi_coll_inj_copy x4: NEEDS RE-RUN | rec SS 196.28 (TT 306.68) FF 28.65 spread TT/FF 3/2.6 | kit repo | paper PASS
- ot_hgi_coll_inj_idx_join_rg x4: NEEDS RE-RUN | rec SS -150.72 (TT 134.13) FF 5.27 spread TT/FF 47.6/43.9 | kit repo | paper FAIL
- ot_hgi_coll_kq_share2_leaf x16: NEEDS RE-RUN | rec SS 52.19 (TT 253.01) FF 18.21 spread TT/FF 44.5/42.9 | kit repo | paper PASS
- ot_hgi_coll_ring_b_stop x4: NEEDS RE-RUN | rec SS -39.78 (TT 210.92) FF 8.29 spread TT/FF 58.8/57.2 | kit repo | paper FAIL
- ot_hgi_qdq_lg_port_group_r2 x16: NEEDS RE-RUN | rec SS 240.08 (TT 329.97) FF 19.9 spread TT/FF 17.4/17.5 | kit repo | paper PASS
- ot_hgi_qdq_transport_ctl_r4 x4: NEEDS RE-RUN | rec SS 58.32 (TT 269.77) FF 12.01 spread TT/FF 28.6/22.8 | kit repo | paper PASS
- ot_hgi_qdq_transport_rslice x16: NEEDS RE-RUN | rec SS 54.89 (TT 287.66) FF 6.28 spread TT/FF 84.7/80.8 | kit repo | paper FAIL
- ot_hgi_qdq_transport_wslice x16: NEEDS RE-RUN | rec SS 196.37 (TT 314.49) FF 23.98 spread TT/FF 37.4/37.1 | kit repo | paper PASS
- ot_hgi_qw_dec x4: NEEDS RE-RUN | rec SS -305.88 (TT 50.84) FF 18.4 spread TT/FF -/- | kit NOT IN REPO | paper FAIL
- ot_hgi_sfu_lg_pair_tap_leaf x16: NEEDS RE-RUN | rec SS 121.58 (TT 306.16) FF 5.09 spread TT/FF 53.6/51 | kit repo | paper PASS
- ot_hgi_sfu_lg_pair_tap_leaf_term x16: NEEDS RE-RUN | rec SS 306.56 (TT 378.05) FF 8.54 spread TT/FF 48.5/46.1 | kit repo | paper PASS
- ot_hgi_sm_xload_cl2_bdring x8: NEEDS RE-RUN | rec SS -242.93 (TT 48.29) FF 22.86 spread TT/FF 25.4/24.2 | kit repo | paper FAIL
- ot_hgi_sm_xload_cl2_bfqg x32: NEEDS RE-RUN | rec SS -176.82 (TT 115.25) FF 11.69 spread TT/FF -/- | kit repo | paper FAIL
- ot_hgi_sm_xload_cl2_ctlx x4: NEEDS RE-RUN | rec SS -317.43 (TT 8.26) FF 5.9 spread TT/FF 79.8/74.6 | kit repo | paper FAIL
- ot_hgi_sm_xload_xq_pegress x8: NEEDS RE-RUN | rec SS -203.74 (TT 82.21) FF 12.05 spread TT/FF 32.9/31.4 | kit repo | paper FAIL
- ot_pdie_ucie_col x1: NEEDS RE-RUN | rec SS 49.67 (TT 229.17) FF 10.65 spread TT/FF 14.4/13.7 | kit repo | paper PASS
- ot_static_run_target x16: NEEDS RE-RUN | rec SS 3.46 (TT 262.51) FF 27.37 spread TT/FF 15/15.5 | kit NOT IN REPO | paper PASS
- ot_vms_status4_static x1: NEEDS RE-RUN | rec SS 131.02 (TT 344.22) FF 29.09 spread TT/FF 2.6/2.7 | kit repo | paper PASS

### hbm_b2r2: 51 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 51 (paper FAIL 31, paper PASS 20)
- hfd_ep_static x6: NEEDS RE-RUN | rec SS -14.52 (TT 217.23) FF 8 spread TT/FF 53.4/49.3 | kit repo | paper FAIL
- hfd_hgi_vm_calendar_f20 x2: NEEDS RE-RUN | rec SS -373.14 (TT 25.04) FF 12.63 spread TT/FF 25.3/21.8 | kit repo | paper FAIL
- hfd_vms_bank_native_q0_faces x16: NEEDS RE-RUN | rec SS -266.26 (TT 17.45) FF 8.62 spread TT/FF 0.1/0 | kit repo | paper FAIL
- hfd_vms_wq2_merge x16: NEEDS RE-RUN | rec SS 249.78 (TT 335.22) FF 21.14 spread TT/FF 19.5/20.4 | kit repo | paper PASS
- ot_hbm_argmax_static_sw_vm_r2 x1: NEEDS RE-RUN | rec SS -261.08 (TT 84.29) FF 16.79 spread TT/FF 25.5/23.3 | kit repo | paper FAIL
- ot_hbm_fault_leaf_n8_s0 x2: NEEDS RE-RUN | rec SS 387.26 (TT 432.71) FF 30.46 spread TT/FF 0.3/0.3 | kit repo | paper PASS
- ot_hbm_host_cfg_leaf_nw x2: NEEDS RE-RUN | rec SS 317.73 (TT 417.66) FF 20.52 spread TT/FF 10.1/10.7 | kit repo | paper PASS
- ot_hbm_host_cp_rxs x1: NEEDS RE-RUN | rec SS -379.24 (TT 2.05) FF 18.8 spread TT/FF 54/50.8 | kit repo | paper FAIL
- ot_hbm_idx_qctl_static x2: NEEDS RE-RUN | rec SS 46.41 (TT 227.91) FF 22.75 spread TT/FF 14.8/14.7 | kit NOT IN REPO | paper PASS
- ot_hbm_idx_query_static x2: NEEDS RE-RUN | rec SS -382.5 (TT 12) FF 14.52 spread TT/FF 79.6/75.3 | kit repo | paper FAIL
- ot_hbm_idx_rootctl_static_am x1: NEEDS RE-RUN | rec SS -275.36 (TT 23.17) FF 20.15 spread TT/FF 76.3/63.7 | kit repo | paper FAIL
- ot_hbm_idx_vm_query_static_n12 x2: NEEDS RE-RUN | rec SS -336.2 (TT 23.35) FF 13.64 spread TT/FF 49.4/45.7 | kit repo | paper FAIL
- ot_hbm_pc_refresh_cfg x2: NEEDS RE-RUN | rec SS -97.62 (TT 125.96) FF 24.03 spread TT/FF 6.1/6.4 | kit repo | paper FAIL
- ot_hbm_sm_vm_wr_q_t_lanes4 x2: NEEDS RE-RUN | rec SS -202.86 (TT 92.94) FF 26.15 spread TT/FF 28.1/26.6 | kit repo | paper FAIL
- ot_hbm_static_cfg_collar_idx256r x1: NEEDS RE-RUN | rec SS -297.99 (TT 40.72) FF 27.12 spread TT/FF 36.2/33.3 | kit NOT IN REPO | paper FAIL
- ot_hbm_status_join_fa x1: NEEDS RE-RUN | rec SS 289.75 (TT 409.15) FF 28.92 spread TT/FF 9.4/6.6 | kit repo | paper PASS
- ot_hbm_su_bridge_release_s x2: NEEDS RE-RUN | rec SS -44.75 (TT 7.34) FF 30.52 spread TT/FF 11.9/7.6 | kit repo | paper FAIL
- ot_hbm_su_programme_root_h5 x1: NEEDS RE-RUN | rec SS 276.16 (TT 346.8) FF 21.53 spread TT/FF 13.1/13.4 | kit repo | paper PASS
- ot_hbm_su_static_cxport_dl_q x8: NEEDS RE-RUN | rec SS -41.45 (TT 88.64) FF 29.09 spread TT/FF 56.7/54.7 | kit repo | paper FAIL
- ot_hbm_su_static_cxport_ij_q x2: NEEDS RE-RUN | rec SS -92.39 (TT 67.13) FF 26.92 spread TT/FF 39.6/37.4 | kit NOT IN REPO | paper FAIL
- ot_hbm_su_static_cxport_rc_q x2: NEEDS RE-RUN | rec SS -157.02 (TT 28.42) FF 27.54 spread TT/FF 26.3/23.9 | kit repo | paper FAIL
- ot_hbm_su_static_cxport_rc_s x2: NEEDS RE-RUN | rec SS -237.63 (TT 9.9) FF 27.04 spread TT/FF 43.5/41.4 | kit repo | paper FAIL
- ot_hbm_su_static_qcore_r13 x2: NEEDS RE-RUN | rec SS -291.7 (TT 4.27) FF 10.87 spread TT/FF 52.6/49.9 | kit repo | paper FAIL
- ot_hbm_su_static_sfustore_hw x2: NEEDS RE-RUN | rec SS -80.61 (TT 175.55) FF 23.13 spread TT/FF 71.7/64.4 | kit repo | paper FAIL
- ot_hbm_su_stree_leaf x2: NEEDS RE-RUN | rec SS 328.42 (TT 391.8) FF 27.45 spread TT/FF 7.3/7.3 | kit repo | paper PASS
- ot_hbm_su_stree_root x1: NEEDS RE-RUN | rec SS 379.45 (TT 426.1) FF 19.37 spread TT/FF 12.5/13.4 | kit repo | paper PASS
- ot_hbm_svc_pc_ctrl_leaf_cfg_h9b x32: NEEDS RE-RUN | rec SS -294.93 (TT 29.75) FF 13.65 spread TT/FF 117.5/117.7 | kit repo | paper FAIL
- ot_hbm_svc_stack_fault x2: NEEDS RE-RUN | rec SS 256.22 (TT 346.67) FF 7.33 spread TT/FF 2.4/2.2 | kit repo | paper PASS
- ot_hbm_svc_vmdel_lane_n x16: NEEDS RE-RUN | rec SS -229.87 (TT 85.47) FF 3.23 spread TT/FF 68.2/61.5 | kit repo | paper FAIL
- ot_hbm_svc_wbw_copy x2: NEEDS RE-RUN | rec SS 378.02 (TT 425.86) FF 28.95 spread TT/FF 4.9/4.2 | kit repo | paper PASS
- ot_hbm_xp_aq_tree13_fmt x4: NEEDS RE-RUN | rec SS -282.54 (TT 65.07) FF 15.27 spread TT/FF 17.7/16.9 | kit repo | paper FAIL
- ot_hgi_coll_gq_land x2: NEEDS RE-RUN | rec SS -337.75 (TT 11.98) FF 16.83 spread TT/FF 69.9/66.1 | kit repo | paper FAIL
- ot_hgi_coll_inj_copy x2: NEEDS RE-RUN | rec SS 196.28 (TT 306.68) FF 28.65 spread TT/FF 3/2.6 | kit repo | paper PASS
- ot_hgi_coll_inj_idx_join_rg x2: NEEDS RE-RUN | rec SS -150.72 (TT 134.13) FF 5.27 spread TT/FF 47.6/43.9 | kit repo | paper FAIL
- ot_hgi_coll_kq_share2_leaf x8: NEEDS RE-RUN | rec SS 52.19 (TT 253.01) FF 18.21 spread TT/FF 44.5/42.9 | kit repo | paper PASS
- ot_hgi_coll_ring_b_stop x2: NEEDS RE-RUN | rec SS -39.78 (TT 210.92) FF 8.29 spread TT/FF 58.8/57.2 | kit repo | paper FAIL
- ot_hgi_qdq_lg_port_group_r2 x8: NEEDS RE-RUN | rec SS 240.08 (TT 329.97) FF 19.9 spread TT/FF 17.4/17.5 | kit repo | paper PASS
- ot_hgi_qdq_nw_program_leaf x2: NEEDS RE-RUN | rec SS -265.85 (TT 42.22) FF 12.45 spread TT/FF 42.3/26.6 | kit repo | paper FAIL
- ot_hgi_qdq_transport_ctl_r4 x2: NEEDS RE-RUN | rec SS 58.32 (TT 269.77) FF 12.01 spread TT/FF 28.6/22.8 | kit repo | paper PASS
- ot_hgi_qdq_transport_rslice x8: NEEDS RE-RUN | rec SS 54.89 (TT 287.66) FF 6.28 spread TT/FF 84.7/80.8 | kit repo | paper FAIL
- ot_hgi_qdq_transport_wslice x8: NEEDS RE-RUN | rec SS 196.37 (TT 314.49) FF 23.98 spread TT/FF 37.4/37.1 | kit repo | paper PASS
- ot_hgi_qw_dec x2: NEEDS RE-RUN | rec SS -305.88 (TT 50.84) FF 18.4 spread TT/FF -/- | kit NOT IN REPO | paper FAIL
- ot_hgi_sfu_lg_pair_tap_leaf x8: NEEDS RE-RUN | rec SS 121.58 (TT 306.16) FF 5.09 spread TT/FF 53.6/51 | kit repo | paper PASS
- ot_hgi_sfu_lg_pair_tap_leaf_term x8: NEEDS RE-RUN | rec SS 306.56 (TT 378.05) FF 8.54 spread TT/FF 48.5/46.1 | kit repo | paper PASS
- ot_hgi_sm_xload_cl2_bdring x4: NEEDS RE-RUN | rec SS -242.93 (TT 48.29) FF 22.86 spread TT/FF 25.4/24.2 | kit repo | paper FAIL
- ot_hgi_sm_xload_cl2_bfqg x16: NEEDS RE-RUN | rec SS -176.82 (TT 115.25) FF 11.69 spread TT/FF -/- | kit repo | paper FAIL
- ot_hgi_sm_xload_cl2_ctlx x2: NEEDS RE-RUN | rec SS -317.43 (TT 8.26) FF 5.9 spread TT/FF 79.8/74.6 | kit repo | paper FAIL
- ot_hgi_sm_xload_xq_pegress x4: NEEDS RE-RUN | rec SS -203.74 (TT 82.21) FF 12.05 spread TT/FF 32.9/31.4 | kit repo | paper FAIL
- ot_pdie_ucie_col x1: NEEDS RE-RUN | rec SS 49.67 (TT 229.17) FF 10.65 spread TT/FF 14.4/13.7 | kit repo | paper PASS
- ot_static_run_target x8: NEEDS RE-RUN | rec SS 3.46 (TT 262.51) FF 27.37 spread TT/FF 15/15.5 | kit NOT IN REPO | paper PASS
- ot_vms_status4_static x1: NEEDS RE-RUN | rec SS 131.02 (TT 344.22) FF 29.09 spread TT/FF 2.6/2.7 | kit repo | paper PASS
- P7 + B2r2 re-pin the closed cores onto plan tracks -> re-harden needed regardless of DB.

## SM sub-lane
- 2026-10-24 08:09 SM: diag: hnx-sm4p half kits = 'cluster' (18/16 hard children: xs3n FAIL spread 154/134, bdc/tct/tcl SS setup -47.5/-17.9/-29.7 ps, tr_group WARN) -> not closed -> FLAT kits (sm/gen_sm_kit.py, RTL git-show @4d6f5439dc). B2r2 pins = kit pins +0.012 track snap only (names equal: n 6506, s 4537).
- 2026-10-24 08:09 SM: P&R launched (ot-run, run_kit_hbm.sh finish 128G/32thr): n-f epyc2:/srv/opentallas-scratch/claude/elem-hbm/kits_sm/hnx_rp3lp3h_n_1938f3904f84-f; n-h (SYNTH_HIERARCHICAL=1) epyc3:.../kits_sm/hnx_rp3lp3h_n_1938f3904f84-h; s-f, s-h intel1:.../kits_sm/hnx_rp3lp3h_s_33365650555c-{f,h}; local ot-run pids 1216656..1216659 (logs localhost:/srv/opentallas-scratch/claude/elem-hbm/runs_sm). Halves lockstep+MUT1-4 bench running epyc3 (pid 1168440).

## 2026-10-24 08:18 PDT — review before route (owner 08:05) + TT sign-off (AGENTS.md c7ce2ed69a)
- Cancelled my 6 SS-corner unreviewed pilots (argmax, gq_land, gq_issue, bankq0 l0_2, idx r0c0_k0h0, sfu lane0): NOT RUN.
  (Also stopped SM sub-agent's epyc2 hnx_n container by prefix match — told the sub-agent.)
- Kits regenerated at CORNER TC: /srv/opentallas-scratch/claude/elem-hbm/kits_tt (133 views, all gen rc 0).
- Plan-stage review of all 240 views: renders in /srv/opentallas-scratch/claude/elem-hbm/review/<view>/ (plan.png,
  context.png, stats.json); I read the family montages (review/montage_{plan,context}.png) + gq_issue, argmax, sfu lane0,
  idx_vm_query. Core pins OK in every view (<= 0.254 pins/track); plan-level face-orientation / long-wire / unchecked
  findings posted to HBM-ARCH.md. Records: results/geom_review/<module>__<kit>_plan__<hash12>.json, verdict PASS-COND
  (place only) for the 133 kits.
- Now: place stage of 133 kits (TT) via ot-run on localhost,epyc2,epyc3; then placed review (fill, macros, density,
  face-flop distance) -> route -> tools/die_plan/signoff.py --corners tt,ff.

## SIGNOFF re-signoff list v3 — TT RULE (2026-10-24 08:22 PDT, main f942bf2f72; supersedes v1/v2 above)
Rule (owner 2026-10-24, AGENTS.md): setup TT / hold FF (std boundary-hold overlay: out min 0, in min -40), 60/25 ps, pin-flop spread <= 80 TT+FF, DRV at TT+FF; SS information only. All routed DBs of closed blocks were on the wiped old fleet -> NEEDS RE-RUN. 'rec TT' = closure_loop metrics.ss_ps (historical key; now published as tt_setup_ps). Paper FAIL = needs re-close; paper PASS still needs re-run + signoff.py (records predate the hold standard / sdc_lint / face_guard). New gen_phys kits run signoff.py automatically at the end of run_kit.sh (KIT/signoff/signoff.json).

### hbm: 55 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 55 (paper FAIL 2, PASS 51, no/incomplete record 2)
- hfd_ep_static x6: NEEDS RE-RUN | rec TT 217.23 FF 8 spread TT/FF 53.4/49.3 | kit repo | paper PASS
- hfd_hgi_vm_calendar_f20 x4: NEEDS RE-RUN | rec TT 25.04 FF 12.63 spread TT/FF 25.3/21.8 | kit repo | paper PASS
- hfd_vms_bank_native_q0_faces x32: NEEDS RE-RUN | rec TT 17.45 FF 8.62 spread TT/FF 0.1/0 | kit repo | paper PASS
- hfd_vms_wq2_merge x32: NEEDS RE-RUN | rec TT 335.22 FF 21.14 spread TT/FF 19.5/20.4 | kit repo | paper PASS
- ot_hbm_argmax_static_sw_vm_r2 x1: NEEDS RE-RUN | rec TT 84.29 FF 16.79 spread TT/FF 25.5/23.3 | kit repo | paper PASS
- ot_hbm_fault_leaf x24: NEEDS RE-RUN | rec TT 434.46 FF 29.75 spread TT/FF 0.8/0.5 | kit repo | paper PASS
- ot_hbm_fault_leaf_n8_s0 x4: NEEDS RE-RUN | rec TT 432.71 FF 30.46 spread TT/FF 0.3/0.3 | kit repo | paper PASS
- ot_hbm_host_cfg_leaf_nw x4: NEEDS RE-RUN | rec TT 417.66 FF 20.52 spread TT/FF 10.1/10.7 | kit repo | paper PASS
- ot_hbm_host_cp_rxs x1: NEEDS RE-RUN | rec TT 2.05 FF 18.8 spread TT/FF 54/50.8 | kit repo | paper PASS
- ot_hbm_idx_qctl_static x4: NEEDS RE-RUN | rec TT 227.91 FF 22.75 spread TT/FF 14.8/14.7 | kit NOT IN REPO | paper PASS
- ot_hbm_idx_query_static x4: NEEDS RE-RUN | rec TT 12 FF 14.52 spread TT/FF 79.6/75.3 | kit repo | paper PASS
- ot_hbm_idx_rootctl_static_am x1: NEEDS RE-RUN | rec TT 23.17 FF 20.15 spread TT/FF 76.3/63.7 | kit repo | paper PASS
- ot_hbm_idx_vm_query_static_n12 x4: NEEDS RE-RUN | rec TT 23.35 FF 13.64 spread TT/FF 49.4/45.7 | kit repo | paper PASS
- ot_hbm_idx_xq_node_static x3: NEEDS RE-RUN | rec TT 362.14 FF 9.92 spread TT/FF 31.3/30.1 | kit repo | paper PASS
- ot_hbm_pc_refresh_cfg x4: NEEDS RE-RUN | rec TT 125.96 FF 24.03 spread TT/FF 6.1/6.4 | kit repo | paper PASS
- ot_hbm_sm_vm_wr_q_t_lanes4 x4: NEEDS RE-RUN | rec TT 92.94 FF 26.15 spread TT/FF 28.1/26.6 | kit repo | paper PASS
- ot_hbm_static_cfg_collar x5: NEEDS RE-RUN | rec TT 50.96 FF 22.05 spread TT/FF 22.6/22.4 | kit repo | paper PASS
- ot_hbm_static_cfg_collar_idx256r x1: NEEDS RE-RUN | rec TT 40.72 FF 27.12 spread TT/FF 36.2/33.3 | kit NOT IN REPO | paper PASS
- ot_hbm_status_join_fa x1: NEEDS RE-RUN | rec TT 409.15 FF 28.92 spread TT/FF 9.4/6.6 | kit repo | paper PASS
- ot_hbm_su_bridge_release_s x4: NEEDS RE-RUN | rec TT 7.34 FF 30.52 spread TT/FF 11.9/7.6 | kit repo | paper PASS
- ot_hbm_su_programme_root_h5 x1: NEEDS RE-RUN | rec TT 346.8 FF 21.53 spread TT/FF 13.1/13.4 | kit repo | paper PASS
- ot_hbm_su_static_cxport_dl_q x16: NEEDS RE-RUN | rec TT 88.64 FF 29.09 spread TT/FF 56.7/54.7 | kit repo | paper PASS
- ot_hbm_su_static_cxport_dl_s x16: NEEDS RE-RUN | rec TT 204.45 FF 29.5 spread TT/FF 17.1/16.9 | kit repo | paper PASS
- ot_hbm_su_static_cxport_ij_q x4: NEEDS RE-RUN | rec TT 67.13 FF 26.92 spread TT/FF 39.6/37.4 | kit NOT IN REPO | paper PASS
- ot_hbm_su_static_cxport_ij_s x4: NEEDS RE-RUN | rec TT 88.31 FF 15.51 spread TT/FF 64.6/60.8 | kit repo | paper PASS
- ot_hbm_su_static_cxport_rc_q x4: NEEDS RE-RUN | rec TT 28.42 FF 27.54 spread TT/FF 26.3/23.9 | kit repo | paper PASS
- ot_hbm_su_static_cxport_rc_s x4: NEEDS RE-RUN | rec TT 9.9 FF 27.04 spread TT/FF 43.5/41.4 | kit repo | paper PASS
- ot_hbm_su_static_qcore_r13 x4: NEEDS RE-RUN | rec TT 4.27 FF 10.87 spread TT/FF 52.6/49.9 | kit repo | paper PASS
- ot_hbm_su_static_sfustore_hw x4: NEEDS RE-RUN | rec TT 175.55 FF 23.13 spread TT/FF 71.7/64.4 | kit repo | paper PASS
- ot_hbm_su_stree_leaf x4: NEEDS RE-RUN | rec TT 391.8 FF 27.45 spread TT/FF 7.3/7.3 | kit repo | paper PASS
- ot_hbm_su_stree_root x1: NEEDS RE-RUN | rec TT 426.1 FF 19.37 spread TT/FF 12.5/13.4 | kit repo | paper PASS
- ot_hbm_svc_pc_ctrl_leaf_cfg_h9b x64: NEEDS RE-RUN | rec TT 29.75 FF 13.65 spread TT/FF 117.5/117.7 | kit repo | paper FAIL (recorded TT pin-flop spread 117.5 ps > 80; recorded FF pin-flop spread 117.7 ps > 80)
- ot_hbm_svc_stack_fault x4: NEEDS RE-RUN | rec TT 346.67 FF 7.33 spread TT/FF 2.4/2.2 | kit repo | paper PASS
- ot_hbm_svc_vmdel_lane_n x32: NEEDS RE-RUN | rec TT 85.47 FF 3.23 spread TT/FF 68.2/61.5 | kit repo | paper PASS
- ot_hbm_svc_wbw_copy x4: NEEDS RE-RUN | rec TT 425.86 FF 28.95 spread TT/FF 4.9/4.2 | kit repo | paper PASS
- ot_hbm_xp_aq_tree13_fmt x8: NEEDS RE-RUN | rec TT 65.07 FF 15.27 spread TT/FF 17.7/16.9 | kit repo | paper PASS
- ot_hgi_coll_gq_land x4: NEEDS RE-RUN | rec TT 11.98 FF 16.83 spread TT/FF 69.9/66.1 | kit repo | paper PASS
- ot_hgi_coll_inj_copy x4: NEEDS RE-RUN | rec TT 306.68 FF 28.65 spread TT/FF 3/2.6 | kit repo | paper PASS
- ot_hgi_coll_inj_idx_join_rg x4: NEEDS RE-RUN | rec TT 134.13 FF 5.27 spread TT/FF 47.6/43.9 | kit repo | paper PASS
- ot_hgi_coll_kq_share2_leaf x16: NEEDS RE-RUN | rec TT 253.01 FF 18.21 spread TT/FF 44.5/42.9 | kit repo | paper PASS
- ot_hgi_coll_ring_b_stop x4: NEEDS RE-RUN | rec TT 210.92 FF 8.29 spread TT/FF 58.8/57.2 | kit repo | paper PASS
- ot_hgi_qdq_lg_port_group_r2 x16: NEEDS RE-RUN | rec TT 329.97 FF 19.9 spread TT/FF 17.4/17.5 | kit repo | paper PASS
- ot_hgi_qdq_transport_ctl_r4 x4: NEEDS RE-RUN | rec TT 269.77 FF 12.01 spread TT/FF 28.6/22.8 | kit repo | paper PASS
- ot_hgi_qdq_transport_rslice x16: NEEDS RE-RUN | rec TT 287.66 FF 6.28 spread TT/FF 84.7/80.8 | kit repo | paper FAIL (recorded TT pin-flop spread 84.7 ps > 80; recorded FF pin-flop spread 80.8 ps > 80)
- ot_hgi_qdq_transport_wslice x16: NEEDS RE-RUN | rec TT 314.49 FF 23.98 spread TT/FF 37.4/37.1 | kit repo | paper PASS
- ot_hgi_qw_dec x4: NEEDS RE-RUN | rec TT 50.84 FF 18.4 spread TT/FF -/- | kit NOT IN REPO | paper INCOMPLETE (no recorded pin-flop spread (insertion.json missing))
- ot_hgi_sfu_lg_pair_tap_leaf x16: NEEDS RE-RUN | rec TT 306.16 FF 5.09 spread TT/FF 53.6/51 | kit repo | paper PASS
- ot_hgi_sfu_lg_pair_tap_leaf_term x16: NEEDS RE-RUN | rec TT 378.05 FF 8.54 spread TT/FF 48.5/46.1 | kit repo | paper PASS
- ot_hgi_sm_xload_cl2_bdring x8: NEEDS RE-RUN | rec TT 48.29 FF 22.86 spread TT/FF 25.4/24.2 | kit repo | paper PASS
- ot_hgi_sm_xload_cl2_bfqg x32: NEEDS RE-RUN | rec TT 115.25 FF 11.69 spread TT/FF -/- | kit repo | paper INCOMPLETE (no recorded pin-flop spread (insertion.json missing))
- ot_hgi_sm_xload_cl2_ctlx x4: NEEDS RE-RUN | rec TT 8.26 FF 5.9 spread TT/FF 79.8/74.6 | kit repo | paper PASS
- ot_hgi_sm_xload_xq_pegress x8: NEEDS RE-RUN | rec TT 82.21 FF 12.05 spread TT/FF 32.9/31.4 | kit repo | paper PASS
- ot_pdie_ucie_col x1: NEEDS RE-RUN | rec TT 229.17 FF 10.65 spread TT/FF 14.4/13.7 | kit repo | paper PASS
- ot_static_run_target x16: NEEDS RE-RUN | rec TT 262.51 FF 27.37 spread TT/FF 15/15.5 | kit NOT IN REPO | paper PASS
- ot_vms_status4_static x1: NEEDS RE-RUN | rec TT 344.22 FF 29.09 spread TT/FF 2.6/2.7 | kit repo | paper PASS

### hbm_b2r2: 51 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 51 (paper FAIL 2, PASS 47, no/incomplete record 2)
- hfd_ep_static x6: NEEDS RE-RUN | rec TT 217.23 FF 8 spread TT/FF 53.4/49.3 | kit repo | paper PASS
- hfd_hgi_vm_calendar_f20 x2: NEEDS RE-RUN | rec TT 25.04 FF 12.63 spread TT/FF 25.3/21.8 | kit repo | paper PASS
- hfd_vms_bank_native_q0_faces x16: NEEDS RE-RUN | rec TT 17.45 FF 8.62 spread TT/FF 0.1/0 | kit repo | paper PASS
- hfd_vms_wq2_merge x16: NEEDS RE-RUN | rec TT 335.22 FF 21.14 spread TT/FF 19.5/20.4 | kit repo | paper PASS
- ot_hbm_argmax_static_sw_vm_r2 x1: NEEDS RE-RUN | rec TT 84.29 FF 16.79 spread TT/FF 25.5/23.3 | kit repo | paper PASS
- ot_hbm_fault_leaf_n8_s0 x2: NEEDS RE-RUN | rec TT 432.71 FF 30.46 spread TT/FF 0.3/0.3 | kit repo | paper PASS
- ot_hbm_host_cfg_leaf_nw x2: NEEDS RE-RUN | rec TT 417.66 FF 20.52 spread TT/FF 10.1/10.7 | kit repo | paper PASS
- ot_hbm_host_cp_rxs x1: NEEDS RE-RUN | rec TT 2.05 FF 18.8 spread TT/FF 54/50.8 | kit repo | paper PASS
- ot_hbm_idx_qctl_static x2: NEEDS RE-RUN | rec TT 227.91 FF 22.75 spread TT/FF 14.8/14.7 | kit NOT IN REPO | paper PASS
- ot_hbm_idx_query_static x2: NEEDS RE-RUN | rec TT 12 FF 14.52 spread TT/FF 79.6/75.3 | kit repo | paper PASS
- ot_hbm_idx_rootctl_static_am x1: NEEDS RE-RUN | rec TT 23.17 FF 20.15 spread TT/FF 76.3/63.7 | kit repo | paper PASS
- ot_hbm_idx_vm_query_static_n12 x2: NEEDS RE-RUN | rec TT 23.35 FF 13.64 spread TT/FF 49.4/45.7 | kit repo | paper PASS
- ot_hbm_pc_refresh_cfg x2: NEEDS RE-RUN | rec TT 125.96 FF 24.03 spread TT/FF 6.1/6.4 | kit repo | paper PASS
- ot_hbm_sm_vm_wr_q_t_lanes4 x2: NEEDS RE-RUN | rec TT 92.94 FF 26.15 spread TT/FF 28.1/26.6 | kit repo | paper PASS
- ot_hbm_static_cfg_collar_idx256r x1: NEEDS RE-RUN | rec TT 40.72 FF 27.12 spread TT/FF 36.2/33.3 | kit NOT IN REPO | paper PASS
- ot_hbm_status_join_fa x1: NEEDS RE-RUN | rec TT 409.15 FF 28.92 spread TT/FF 9.4/6.6 | kit repo | paper PASS
- ot_hbm_su_bridge_release_s x2: NEEDS RE-RUN | rec TT 7.34 FF 30.52 spread TT/FF 11.9/7.6 | kit repo | paper PASS
- ot_hbm_su_programme_root_h5 x1: NEEDS RE-RUN | rec TT 346.8 FF 21.53 spread TT/FF 13.1/13.4 | kit repo | paper PASS
- ot_hbm_su_static_cxport_dl_q x8: NEEDS RE-RUN | rec TT 88.64 FF 29.09 spread TT/FF 56.7/54.7 | kit repo | paper PASS
- ot_hbm_su_static_cxport_ij_q x2: NEEDS RE-RUN | rec TT 67.13 FF 26.92 spread TT/FF 39.6/37.4 | kit NOT IN REPO | paper PASS
- ot_hbm_su_static_cxport_rc_q x2: NEEDS RE-RUN | rec TT 28.42 FF 27.54 spread TT/FF 26.3/23.9 | kit repo | paper PASS
- ot_hbm_su_static_cxport_rc_s x2: NEEDS RE-RUN | rec TT 9.9 FF 27.04 spread TT/FF 43.5/41.4 | kit repo | paper PASS
- ot_hbm_su_static_qcore_r13 x2: NEEDS RE-RUN | rec TT 4.27 FF 10.87 spread TT/FF 52.6/49.9 | kit repo | paper PASS
- ot_hbm_su_static_sfustore_hw x2: NEEDS RE-RUN | rec TT 175.55 FF 23.13 spread TT/FF 71.7/64.4 | kit repo | paper PASS
- ot_hbm_su_stree_leaf x2: NEEDS RE-RUN | rec TT 391.8 FF 27.45 spread TT/FF 7.3/7.3 | kit repo | paper PASS
- ot_hbm_su_stree_root x1: NEEDS RE-RUN | rec TT 426.1 FF 19.37 spread TT/FF 12.5/13.4 | kit repo | paper PASS
- ot_hbm_svc_pc_ctrl_leaf_cfg_h9b x32: NEEDS RE-RUN | rec TT 29.75 FF 13.65 spread TT/FF 117.5/117.7 | kit repo | paper FAIL (recorded TT pin-flop spread 117.5 ps > 80; recorded FF pin-flop spread 117.7 ps > 80)
- ot_hbm_svc_stack_fault x2: NEEDS RE-RUN | rec TT 346.67 FF 7.33 spread TT/FF 2.4/2.2 | kit repo | paper PASS
- ot_hbm_svc_vmdel_lane_n x16: NEEDS RE-RUN | rec TT 85.47 FF 3.23 spread TT/FF 68.2/61.5 | kit repo | paper PASS
- ot_hbm_svc_wbw_copy x2: NEEDS RE-RUN | rec TT 425.86 FF 28.95 spread TT/FF 4.9/4.2 | kit repo | paper PASS
- ot_hbm_xp_aq_tree13_fmt x4: NEEDS RE-RUN | rec TT 65.07 FF 15.27 spread TT/FF 17.7/16.9 | kit repo | paper PASS
- ot_hgi_coll_gq_land x2: NEEDS RE-RUN | rec TT 11.98 FF 16.83 spread TT/FF 69.9/66.1 | kit repo | paper PASS
- ot_hgi_coll_inj_copy x2: NEEDS RE-RUN | rec TT 306.68 FF 28.65 spread TT/FF 3/2.6 | kit repo | paper PASS
- ot_hgi_coll_inj_idx_join_rg x2: NEEDS RE-RUN | rec TT 134.13 FF 5.27 spread TT/FF 47.6/43.9 | kit repo | paper PASS
- ot_hgi_coll_kq_share2_leaf x8: NEEDS RE-RUN | rec TT 253.01 FF 18.21 spread TT/FF 44.5/42.9 | kit repo | paper PASS
- ot_hgi_coll_ring_b_stop x2: NEEDS RE-RUN | rec TT 210.92 FF 8.29 spread TT/FF 58.8/57.2 | kit repo | paper PASS
- ot_hgi_qdq_lg_port_group_r2 x8: NEEDS RE-RUN | rec TT 329.97 FF 19.9 spread TT/FF 17.4/17.5 | kit repo | paper PASS
- ot_hgi_qdq_nw_program_leaf x2: NEEDS RE-RUN | rec TT 42.22 FF 12.45 spread TT/FF 42.3/26.6 | kit repo | paper PASS
- ot_hgi_qdq_transport_ctl_r4 x2: NEEDS RE-RUN | rec TT 269.77 FF 12.01 spread TT/FF 28.6/22.8 | kit repo | paper PASS
- ot_hgi_qdq_transport_rslice x8: NEEDS RE-RUN | rec TT 287.66 FF 6.28 spread TT/FF 84.7/80.8 | kit repo | paper FAIL (recorded TT pin-flop spread 84.7 ps > 80; recorded FF pin-flop spread 80.8 ps > 80)
- ot_hgi_qdq_transport_wslice x8: NEEDS RE-RUN | rec TT 314.49 FF 23.98 spread TT/FF 37.4/37.1 | kit repo | paper PASS
- ot_hgi_qw_dec x2: NEEDS RE-RUN | rec TT 50.84 FF 18.4 spread TT/FF -/- | kit NOT IN REPO | paper INCOMPLETE (no recorded pin-flop spread (insertion.json missing))
- ot_hgi_sfu_lg_pair_tap_leaf x8: NEEDS RE-RUN | rec TT 306.16 FF 5.09 spread TT/FF 53.6/51 | kit repo | paper PASS
- ot_hgi_sfu_lg_pair_tap_leaf_term x8: NEEDS RE-RUN | rec TT 378.05 FF 8.54 spread TT/FF 48.5/46.1 | kit repo | paper PASS
- ot_hgi_sm_xload_cl2_bdring x4: NEEDS RE-RUN | rec TT 48.29 FF 22.86 spread TT/FF 25.4/24.2 | kit repo | paper PASS
- ot_hgi_sm_xload_cl2_bfqg x16: NEEDS RE-RUN | rec TT 115.25 FF 11.69 spread TT/FF -/- | kit repo | paper INCOMPLETE (no recorded pin-flop spread (insertion.json missing))
- ot_hgi_sm_xload_cl2_ctlx x2: NEEDS RE-RUN | rec TT 8.26 FF 5.9 spread TT/FF 79.8/74.6 | kit repo | paper PASS
- ot_hgi_sm_xload_xq_pegress x4: NEEDS RE-RUN | rec TT 82.21 FF 12.05 spread TT/FF 32.9/31.4 | kit repo | paper PASS
- ot_pdie_ucie_col x1: NEEDS RE-RUN | rec TT 229.17 FF 10.65 spread TT/FF 14.4/13.7 | kit repo | paper PASS
- ot_static_run_target x8: NEEDS RE-RUN | rec TT 262.51 FF 27.37 spread TT/FF 15/15.5 | kit NOT IN REPO | paper PASS
- ot_vms_status4_static x1: NEEDS RE-RUN | rec TT 344.22 FF 29.09 spread TT/FF 2.6/2.7 | kit repo | paper PASS
- P7 + B2r2 re-pin the closed cores onto plan tracks -> re-harden needed regardless of DB.
- 2026-10-24 08:22 SM: owner orders applied (TT setup + FF hold sign-off; review before route). epyc2 n-f WC run was killed (ELEM-HBM prefix cancel, exit 137); n-h epyc3, s-f/s-h intel1 WC runs kept as PATHFINDING. Plan-stage reviews PASS-COND: results/geom_review/hnx_rp3lp3h_{n,s}__*-t_plan__*.json (pics review/hnx_rp3lp3h_{n,s}_*/plan.png, context.png). TC kits launched: n-t epyc2:/srv/opentallas-scratch/claude/elem-hbm/kits_sm/hnx_rp3lp3h_n_1938f3904f84-t (hash 65cbb15398c1884e), s-t epyc3:.../kits_sm/hnx_rp3lp3h_s_33365650555c-t (d70b9ba3b263ade2). Branch claude/elem-hbm-sm-1024.

## GEOM-REVIEW note (2026-10-24 08:55 PDT)
Die-level review of B2r2 (results/geom_review/hbm_plan__hbm_b2r2__c1bc2d0f7ada.json): q_sm*, q_hub and root partition G3 are BLOCKED pending re-floorplan (HBM-ARCH lane file). Core hardening of SM halves / hub cores may continue (outline/pins may change if HBM-ARCH re-pins the hub). Tile review of your running core kits in progress (GR-HBM).
- 2026-10-24 09:15 GEOM-REVIEW tile (GR-HBM; records on claude/geom-review-1024 results/geom_review/, images localhost:/srv/opentallas-scratch/claude/geom-review/tiles/GR-HBM/):
  - bankq0 lanes0_2 = FAIL: pin plan twisted against its partners (see HBM-ARCH note). Fill is 25.7%, 120k cells vs 289k planned because the wrapper ties s_i[767:0]=0 and fst=1: confirm against the parent or the core is not the die function.
  - gq_land = FAIL: 79% empty, pin-limited outline; 612 vm_kq_lo pins on S while the partners are N; ld_* pins face qw_dec.
  - gq_issue = FAIL (plan).
  STOP submitting these three, and any q_hub core, until HBM-ARCH re-floorplans and re-pins the hub (q_hub FAIL).
  - argmax_r2 = PASS-COND: W pin column 5.8/um, 83 bins > 0.8 density; 672 unregistered pins (face_guard 372/1117), pin->reg max 42.7 um; SS -394 ps is RTL depth (~30 levels).
  - SM halves: kit pins == B2r2 pins (n 6,506 / s 4,537, 0.000 um). PASS-COND at kit level; n-f OOM at 128 GB in yosys.

## CODEX notes
- 2026-10-24 08:54 PDT CODEX took over: collect TT placements and fix generation failures on codex/elem-hbm-1024. 18 placed collected (11 epyc2, 7 epyc3); 8 explicit failures: pgslice side_rest/side_softplus + HC tail0/tail1 sk_steady omit 4096-bit memory synthesis permission; three xcal views fail macro clustering (MPL-0003/0045), opstore_b fails macro packing MPL-0065. Diagnosis/fix active; q_hub/bankq/gq holds retained.
- 2026-10-24 09:10 PDT CODEX: xcal r2 explicit four-SRAM placement PASS 3/3; placed PNGs inspected (kit_xcal_r2/*.png): 4.32um channels, >7um outer bands, fill of free28-29%, zero bins>0.8, pin-reg p90 7.0/15.4/22.2um. SUCCESSOR PASS-COND for route; previous halo-only r1 rejected (0.024um macro gap despite placement success). Generator supports recipe macro_placement + halo. Commits47266eedd1 then77f5bd3dad on codex/elem-hbm-1024.
- CORRECTION memory diagnosis: ORFS error prints limit, not actual table size. r1 at4096 FAIL four kits; actual Yosys inventory largest HC tails33280bit, pgslice sides15616bit fixed tables. r2 uses measured bounds, running localhost:/srv/opentallas-scratch/claude/codex-hbm/kit_memory_r2 (ot-run32? actual16GB/8threads; run_place.log), sessions kept. No table truncation/mock.
- opstore_b FAIL physically impossible at original388.8x345.6um:48 SRAMs x172.824x41.064um=340646um2 >134369um2 outline. HBM-ARCH successor grows to760.32x691.2um (four columns/twelve rows +8.64um channels), pending global plan gate.

- 2026-10-24 10:20 PDT CODEX: All four measured-cap memory r2 kits reached placement (tail33280bit, pgslice15616bit); oldregexSDC preserved so no signoff claim. xcal r4 canonicalSDC+tap_balance failed3/3 RSZ0060; propagated clock RC422–662ps, structural. Physical buffer relocation diagnostic improved238–364ps but spread126FAIL;13repeaters worsened265–428REJECTED. NativeMM coregen b6e8083af8 now tc/bc with requiredTT+FFmacro libs and activeclock measurement. SMhalf n/s12SRAM correctedkits both alive intel1 scratch2 sm_r1, YosysSHARE, no restart. bankq0 fixedzero/fst specialization confirmedagainstparent f3cf7a2f16; pin hold remains.

- 2026-10-24 11:00 PDT CODEX: NativeMM macro plumbing fixed with LIB_FILES=TC_LIB_FILES plus scopedTT/FF; xcalstillCTSFAIL2206holdendpoints2755bufcap. Originalwave96placements, ninthfailuretopkOOM33.5GB/32GBcap ->128GBsynthretryintel2. New bankq0/gq_issue/gq_land B2lpinplans reviewed, placementonly jobsintel2scratch2/revised_held alladmitted; opstore B2j48x256x256SRAM explicitgrid runninglocalhost; SMhalvesintel1actual12SRAMkits progressingGPL. LatestELEM243e68c9fe includesmainclockfix.

## RESUMED 2026-10-24 12:23 PDT (Claude, after 08:50-12:04 usage limit)
- Adopted codex/elem-hbm-1024 @e463622e33 into claude/elem-hbm-1024 (it was built on my branch; + main 24b2da3433) -> ba987f77a3.
- Adopted live jobs (no duplicates): SM halves n/s -tc intel1 scratch2 sm_r1 (place); opstore_b B2j b2j-r2 localhost (GPL oscillating)
  + bin256 epyc3; topk 128 GB synth retry intel2 (in yosys EXTRACT_FA since 11:45); revised_held bankq0/gq_issue/gq_land -b2l
  placements intel2 (3_5 DP done). GQ land exact0 CTS RSZ0060 FAIL stays on record.
- PLAN MOVED: B2l (main 858a6f2b1f) re-pinned almost every core: views_b2l.json 281 views, only 10 (module,pins) identical to
  B2r2 -> all B2r2 placements (my 08:20 wave, Codex's 96) are pathfinding only; re-harden against B2l.
- B2l kits: /srv/opentallas-scratch/claude/elem-hbm/kits_b2l, 169/281 generate (TC). Remaining: split pieces MAP_AMBIGUOUS
  (pgslice 53, tkm 33, +11) -> sub-lane SPLIT2; bankq lanes6_7_bank (8) + vmdel PORT_MISMATCH (5) -> sub-lane RECIPES2; SM halves
  = Codex kits (live).
- Pruned localhost: removed 3 sub-agent worktrees (129 GB; WIP pushed to claude/elem-hbm-{split,recipes}-1024) + old SS kits.
  Root 83% -> 68%. New big runs go to intel1/intel2/epyc3.

## SPLIT2
- 2026-10-24 12:30 SPLIT2 start: wt /srv/opentallas-scratch/claude/elem-hbm/wt-split2 (claude/elem-hbm-split2-1024). Scope 97 MAP_AMBIGUOUS views / 69 modules (tkm 33, pgslice 33 mod/53 views, bankq_ft 2/4, hc tail_rest 2, sfu ctl+opstore_a, coll_q2 3). Reusing parked split/ tools.

## RECIPES2
- 2026-10-24 12:48 PDT RECIPES2 (wt /srv/opentallas-scratch/claude/elem-hbm/wt-recipes2, scratch localhost:/srv/opentallas-scratch/claude/elem-hbm/recipes2): bankq lanes6_7_bank remainder cores extracted from the as-built scoped masters (rtl/hbm_accel/die_glue/scoped_d4g/hcb{,ft,t,0}.sv @d34578d6f, die_r18h5 params CPI1/CPO1, DRLY2/CPO1): port check vs B2l pins EXACT for all 4 (bankq 3894/5970, ft 1368/3444, term 3894/5941 incl. 3 unread d_xa[9:7] retained, bankq0 3894/6483). Lockstep-free formal equiv (remainder + 2 CORE-HBM lanes3 pieces vs master, leaves/SRAMs everted) running localhost. vmdel: plan pins = NPC 4 (default-param elaboration in p4_ports.json) but as-built NPC 2 (die_r18h5 32x NPC 2, ref tile hv18_vmdel_lane2, plan core_conns 2 vmks sources) -> BLOCKED on HBM-ARCH re-pin (OWNER?/HBM-ARCH).
- SPLIT2 13:10 tool split/sw2.py (member/rest/manual kinds, yosys equiv -seq4 + bit-swap mutant). PASS+mutant caught so far: tkm tiles (24/32 done), coll reduce, coll ring_ag. Finding: coll body canonical core AND B2l plan pins were cut from VM_RT=0 master (a_u_control) while die_r18h5 binds VM_RT=81 -> body verified vs VM_RT=0 master (family coll0); flag to parent.
- 2026-10-24 RECIPES2 DONE branch claude/elem-hbm-recipes2-1024 @c010445fb8 (not merged). bankq lanes6_7_bank x4 (bankq/ft/term/bankq0): remainder cores built from the as-built scoped masters @d34578d6f, port check vs B2l EXACT, yosys formal equiv (core + 2 lanes3 pieces vs master) PASS 30010/24870/29733/34079 cells, mutant control caught (bankq, bankq0). 8 kits in kits_b2l. vmdel BLOCKED: B2l pins = NPC4 default, die as built = NPC2 -> HBM-ARCH must re-pin (929 pins). 14 reuse recipes / 25 views spot-check PASS (vm_query NOTE: B2l uses NW VM_RT_EXTRA 173, as-built others 171). Generator fixes: reset-named outputs not given input delay; signed top port -> __core + wrapper (aq_tree13 STA-0171); idx_query SYNTH_MEMORY_MAX_BITS 7168 (measured). Record: physical/die_plan/hbm_arch_cores/results/recipes_b2l.json
- 2026-10-24 13:27 B2l: RECIPES2 merged (c010445fb8 -> ece4a167ff): bankq lanes6_7_bank x4 types equivalence PASS (mutant caught bankq/bankq0),
  idx_query mem cap 7168 measured, aq_tree13 signed-port wrapper; vmdel BLOCKED (plan NPC=4 vs die NPC=2 -> HBM-ARCH).
  180 B2l kits generate; plan-stage records for all; place running on localhost/epyc3/intel1. Macro kits (47) now fence RTL-MP
  out of the pin bands (placed review found idx_qctl SRAM on its 313-pin face) and were re-placed.
- GQ land CTS RSZ0060 root cause: ORFS runs CTS hold repair BEFORE the POST_CTS tap_balance, on a tree of 284-384 ps vs the
  250+-40 IO reference -> 9577 hold buffers. Variants (SKIP_CTS_REPAIR_TIMING + repair after GRT; CTS clustering/buffer
  distance/buffer list) under /srv/opentallas-scratch/claude/elem-hbm/gq_cts; best insertion 306 ps -> core clock contract
  question posted to HBM-ARCH (early core taps).
- SPLIT2 13:45 member-kind wrappers all PASS (yosys equiv -seq4, 0 unproven) + bit-swap mutant caught: tkm tiles 32/32, pgslice pv0 21/21, pv8 9/9 (master QID2 G2: pv8 = all-plain slice; lane_id straps match split_tops), bankq 2/2, coll reduce+ring_ag. Fixed a vacuity bug on the way ($paramod members were not everted -> member inputs unchecked; all reruns post-fix). Kits generated rc=0 for 91 views in kits_b2l. Rest/manual (tkm root, coll body@VM_RT0, sfu ctl/opstore_a, hc tail rest) miters running.
- 2026-10-24 14:00 OWNER? (core clock contract, HBM B2l): hard-core kits must put internal flops at 250 +- 40 ps from the core clock pin
  (IO SDC vclk 250, tap_balance can only lengthen). Measured: gq_land best 306 ps mean (6 CTS variants), Codex xcal 422-662.
  With insertion > 290 the input hold (-100..-156 ps on ~1700 face-flop inputs) and output setup cannot be met without
  thousands of hold buffers (RSZ0060 / hours of repair). Options: (a) plan early core taps (clock pin fed I-250 early, as
  KV/CP2 do) per core from measured I; (b) shrink cores / fewer perimeter sinks. Asked HBM-ARCH; measuring I on every placed
  B2l kit now (CTS-only probes, /srv/opentallas-scratch/claude/elem-hbm/cts_probe2.txt).
- placed-stage findings so far: idx_score_quarter r1c3_k3h1 (64-view family) fill 85% of free, 185/304 bins > 0.8 -> outline too
  small for 23.9k flops (measured request to HBM-ARCH pending a CTS/GRT probe); idx_qctl SRAM on the pin face (fixed by fence,
  re-placed); dma_back vp4_banks_cp 10 SRAMs, pin->reg p90 53 um (re-placed with fence).
- 2026-10-24 14:29 GQ land CTS retry verdict FAIL (not closed): variant skip_h0 (CTS repair after tap balance, hold margin 0) reached GRT and hit RSZ0060 again (9577 hold buffers, 1687 input hold endpoints at -68..-156 ps); c1-c5 CTS variants gave insertion 306-320 ps mean, 345-371 max, all > 290 -> structural core clock contract issue (OWNER? above), not a tool setting. Runs /srv/opentallas-scratch/claude/elem-hbm/runs/gq_land_c9df5f7e46f9-cts_* (localhost/epyc3).
- 2026-10-24 18:49 RESUMED after the session limit.
  - 89 B2l kits are routing: CTS-probe mean insertion <= 290.
  - The kits were regenerated with SKIP_CTS_REPAIR_TIMING and hold_cap.tcl. hold_cap raises repair_timing -max_buffer_percent to 100 (RSZ-0060 had hit at the 20% default). It changes no constraint, margin or corner. The scoping bug is fixed (9bd0d7c0f8).
  - Plan/placed records were rewritten for the new kit hashes.
  - auto_resume.sh retries a failed route up to 2 times.
  - 26 kits are recorded as placed FAIL on the core clock contract (insertion 328-1150 ps): OWNER?/HBM-ARCH.
  - The OWNER DECISIONS (pipelined reset; margins INFO) need no kit change: the core SDC already times rst inputs with recovery/removal against vclk.
- GQ land CTS retry FAIL kept on record (RSZ0060, insertion > 290). It needs the core clock contract decision.
- SPLIT2 PARKED 2026-10-24 (coordinator move). Branch claude/elem-hbm-split2-1024 @d2d3dc361d (pushed; wt /srv/opentallas-scratch/claude/elem-hbm/wt-split2).
  RESULTS (physical/die_plan/hbm_arch_cores/results/split_wrappers_b2l.json, committed @a02e858e91): 65/70 modules PASS = yosys equiv -seq4 0 unproven + bit-swap mutant caught:
  tkm tiles 32, pgslice pv0 21 (lane_exp0-14, lane_exp_l, lanes_plain*, pretree), pv8 9 (lanes0_3..28_31, pretree; master QID2 G2), bankq_ft lanes0_2/lanes3_5, coll reduce/ring_ag.
  Kits gen rc=0 for all 91 views of those modules: /srv/opentallas-scratch/claude/elem-hbm/kits_b2l (gen_rc.txt). READY TO REGENERATE = those 91 views.
  NOT DONE (unverified wrappers parked in split/wip_unverified/, NOT in wrappers/): tkm root, coll body, sfu ctl, sfu opstore_a, hc tail0_rest/tail1_rest.
  LIVE JOBS (localhost, mine, left running; logs under /srv/opentallas-scratch/claude/elem-hbm/split2/work/): pids 2319737 tkm root (tkm/root_0.log), 2319738 coll0 body (coll0/run_0.log), 2319739/40 sfu ctl/opstore_a (sfu/run_0,1.log), 2319741/42 hc tail0/1 (hcroot/run_0,1.log). Each writes wrappers/<m>.sv (untracked) + work/<fam>/reports/<m>.json.
  FINDINGS: coll body canonical + B2l pins were cut from the VM_RT=0 master but die_r18h5 binds VM_RT=81 (flag to HBM-ARCH). No port-set mismatches between pins tables. Fixed vacuity bug ($paramod members not everted); all PASS are post-fix.
  NEXT: when jobs finish, `python3 split/collect_results.py --gen <kits_b2l>/gen_rc.txt`; for PASS modules run split2/genkits.sh <regex>, commit wrappers/<m>.sv + map.json by path. Open issues: rest kind uses an unobservable-unproven rule (unread dead bits, e.g. sfu io_r[470]) - review; hc tail induction (1300 unproven pre region-merge fix) may need deeper -seq or lockstep sim.

## PARKED 2026-10-24 19:00 PDT (ELEM-HBM main)
- Branches:
  - claude/elem-hbm-1024 @9bd0d7c0f8 (pushed, worktree ~/wt/elem-hbm clean).
  - SPLIT2 claude/elem-hbm-split2-1024 @d2d3dc361d (see its park report above). It has 65/70 split modules proven exact; their 91 views generate rc=0 and are not launched yet.
  - Not merged to main yet: no core has SIGNED.
- Live jobs (all mine, running, left alone):
  - B2l core routes, 89 kits, in /srv/opentallas-scratch/claude/elem-hbm/runs/<kit> on localhost, epyc3 and intel1. Containers are hbmcore-<kit>_*.
  - Kit list: /srv/opentallas-scratch/claude/elem-hbm/route_all.txt. Status snapshot: route_status_parked.txt (route_status.sh LIST re-reads it).
  - At park: 70 in GRT, 10 at generate_abstract (finish, signoff next), 1 in DRT.
  - auto_resume.sh is stopped (pid 853443 killed). Its retries are logged in auto_resume.log.
  - SPLIT2 equivalence jobs: localhost pids 2319737-2319742.
- Failures on record (not closed):
  - RSZ-0060 hold-buffer cap. Several first-batch runs started before hold_cap.tcl, and some failed again after resume.
    - Next: check that OT_HOLD_CAP appears in their 5_1_grt.log.
    - If it is there and the cap is still hit, the input-hold demand itself is the problem. That belongs to the same core clock contract question: IO vclk 250 vs measured insertion.
  - GRT-0116/0183 congestion: svc_pc_ctrl_leaf_cfg_h9b (31be7c, 3b586c, a4d8b0, 3ffaa4, 9467d1) and sm_xload cl2 bdring/bfqg.
    - These cores are pin- or macro-dense. Next: try a lower PLACE_DENSITY or a higher layer, or ask HBM-ARCH for a bigger outline.
  - 6_report "LEF Cell ot_sram_* has no matching GDS/OAS": macro GDS is missing in kits with SRAMs (vm_calendar, idx_query, svc_pc_ctrl_leaf 3f2f98/cfc804/684f40).
    - Next: add the macro GDS (ADDITIONAL_GDS) in gen_core_kit_hbm.py, or check whether signoff.py accepts it without GDS.
  - Placed-stage FAIL: 26 kits on the core clock contract (insertion 328-1150 ps). Lists: route_hold.txt and route_hold3.txt.
  - GQ land CTS retry: FAIL.
- Next steps:
  1. Collect the finish runs: physical/die_plan/hbm_arch_cores/collect.py, then record verdicts.
  2. Fix the GDS and congestion items, then re-launch.
  3. Integrate SPLIT2: merge its branch, run plan_records, then place the 91 views.
  4. CTS-probe the 9 unmeasured sfu split3 lanes (cts_probe_result3.txt).
- OWNER? (open):
  - Core clock contract: early core taps for cores whose insertion is over 290 ps (posted to HBM-ARCH 13:27 and 14:11).
  - vmdel re-pin to NPC=2.
  - VM_RT_EXTRA 173 vs 171.
  - coll body pins were cut from the VM_RT=0 master, but the die binds VM_RT=81 (SPLIT2 finding).

## HBM-ELEM (sub-agent of lane HBM) 2026-10-24 19:51 PDT
- 2026-10-24 19:51 PDT HBM-ELEM: took over the parked ELEM-HBM jobs (epyc1 worktree ~/wt/elem-hbm, branch claude/elem-hbm-1024, merged origin/main -> 60311a3cd5).
  COLLECT 89 routing kits: 13 routed -> signoff (corners step had a make-print parse bug that skipped signoff on every finished kit; fixed, run_kit_hbm.sh GOAL=post): 13/13 NOT SIGNED (all face_guard FAIL [OWNER? open]; argmax_r2 is the only one clean on TT setup/FF hold/DRV/DRC; others TT setup -14..-144, FF hold -7..-56, DRV slew). 8 GRT congestion FAIL (svc_pc_ctrl x5, bdring 2f4c, bfqg x2). 57 hold-repair non-convergent FAIL (56 idx_score_quarter + vm_query n12: WNS/TNS flat > 3000 iterations on one endpoint; killed). 8 contract-hold FAIL killed (faces x5, pegress x2, ctlx). 3 still in GRT (bdring 709a, bfqg 1b2f/a386). Record results/b2l_route_verdicts_1024.json @ca77d6ada3. Failed run data deleted (73 run/results).
  CORE CLOCK CONTRACT: results/core_insertion_b2l.json @0e65b11fce (281 views: 136 MEASURED, I = max flop-port mean, early_tap = I-250: 130 > 0, 59 > 40 ps; all 16 sfu lanes measured; 130 not measured = 91 SPLIT2 never placed + 39 no CTS). Generator: vclk / tap target / signoff target = I (0e65b11fce), GDS_ALLOW_EMPTY for abstract SRAMs, hold repair iteration cap 4000.
  GEOM placed2 records: 25 PASS-COND (relaunch under contract), 74 FAIL (18 low-fill pin/macro-limited outlines, 56 idx_score_quarter overfull 86%) -> plan requests to lane HBM.

## PARKED 2026-10-24 20:20 PDT (HBM-ELEM)
- Branches: claude/elem-hbm-1024 @77ad44e788 (pushed; worktree epyc1:~/wt/elem-hbm was pruned by the cleanup agent after the push - re-create from the branch; kits are self-contained so live jobs are unaffected; = origin/main 60311a3cd5 + SPLIT2 merged). claude/elem-hbm-split2-1024 @337f5e8619 (opstore_a wrapper committed). Not merged to main: no core SIGNED.
- Key commits: core_insertion_b2l.json + contract generator 0e65b11fce; verdicts ca77d6ada3/77ad44e788; placed2 geom records c6d07a7a0e (GEOM-REVIEW PASS-COND 19:57); split plan records d906f39227 (GEOM-REVIEW PASS-COND place+CTS 20:06).
- RESULTS (89 route kits, results/b2l_route_verdicts_1024.json): 13 routed NOT SIGNED (signoff run via new GOAL=post; all face_guard FAIL; argmax_r2 clean on TT 25.8 / FF 14.2 / DRV / DRC; others TT -14..-144, FF -7..-56, DRV slew; idx_query + sm_vm_wr_q spread > 80 = INFO under decision 5), 11 GRT congestion FAIL, 57 hold-repair non-convergent FAIL (killed), 8 contract-hold FAIL (killed); + 26 placed contract FAIL. Failed run data deleted.
- LIVE JOBS (ot-run, containers hbmcore-<kit>_*, dirs <host>:/srv/opentallas-scratch/claude/elem-hbm/runs/<kit>, launch.log): 26 finish runs under the contract (sfu lanes 14/15/2/4/5/6/9, hc_bankq0 l0_2/l3_5, hc_bankq l0_2/l3_5, gq_issue, qcore_r13, xcal x4, svc_pc 95777e + 31be7c/3b586c/3ffaa4/9467d1/a4d8b0 [RLA 0.10], bdring 2f4ce4/709af9 [RLA 0.10], vm_query n12); 91 SPLIT2 place+CTS probes (GOAL=cts, kits_b2l/<k>.cts.out). Older: idx_selector a074 (epyc3, yosys EXTRACT_FA since 14:17), idx_selector 64b1 (epyc3 GPL), opstore_b b2j-r2 (epyc1, Codex) - untouched. SPLIT2 equivalence pids 2319737/38/39/41/42 (epyc1) still running; tail0_rest latest miter 1300 unproven (FAIL so far).
- NEXT: (1) when the 26 finish: python3 collect.py on epyc1 (signoff runs automatically now), record; CTS/route pictures for GEOM-REVIEW. (2) when the 91 CTS probes finish: bash cts_gather.sh > cts_gather.txt; regenerate core_insertion_b2l.json (/tmp-free copy of mkins.py logic is in the commit message basis; re-run with the new log lines) and commit. (3) SPLIT2: after the pids exit, python3 split/collect_results.py --gen kits_b2l/gen_rc.txt in wt-split2; commit only PASS+mutant-caught wrappers by path. (4) 13 NOT SIGNED: setup/DRV fixes need RTL/placement analysis (hcp_sys1 -89, idx_query -144, svc_pc -21..-82).
- PLAN REQUESTS (lane HBM, B2m): early core taps from results/core_insertion_b2l.json (early_tap_ps); shrink/reshape 18 low-fill outlines (ep_static, vms_bank_native_q0_faces, hc_bankq0 lanes6_7_bank, sfustore_hw, kshare_splitstrap, gq_land, inj_idx_join_rg, programme_store_r10 [I 1150 ps], bfqg, ctlx, xq_pegress) + hc_bankq0/qcore_r13 empty corners; grow idx_score_quarter (~1.45x area, 86% fill); vmdel NPC=2 re-pin; VM_RT_EXTRA 173 vs 171; coll body VM_RT 0 vs 81; split items from GEOM-REVIEW 20:06 (pgslice clk/rst core-to-core, bankq_ft lanes3_5@20947a re-pin + stations, tkm tile order/stations).
- OWNER?: face_guard on hard-core pins (blocks every SIGNED); signoff.py on main still gates pin-flop spread (decision 5 says INFO).

## CODEX notes 2026-10-24 21:10 PDT — PARKED for Claude reset
CODEX took over collection + measured-memory fix on codex/elem-hbm-push-1024, epyc1:/srv/opentallas-scratch2/claude/wt/codex-elem-hbm-push (HEAD 77ad44e788, verified matches lane origin). No new fleet jobs launched; all inherited jobs preserved. Collected 117 recent jobs: 30 pgslice exp-lane synth FAIL (Yosys actual descriptor table 256x61=15616 bits; default inference guard4096), 4 GRT-0116 FAIL (xcal9ee64d/afccc1/f9e949 and svc_pc95777e), 22 CTS completed, rest progressing. Completed tkm insertion ~441ps, pgslice pretree595-599ps; update insertion contracts next. Collection JSON saved epyc1:/srv/opentallas-scratch2/claude/codex-hbm-core-memory/collection_1024.json. Memory guard fix source saved gen_core_kit_hbm.memory15616.py alongside; local helper /srv/opentallas-scratch2/claude/codex_hbm_memory_fix.py. Pilot generation NOT RUN: initial worktree checkout still in progress (git reset child2318653), tools/die_plan/sdc_lint.py not yet installed; wait for that checkout before retrying. Do not rerun helper as-is (its first replacement has already applied); resume its generation part. No arithmetic/latency change. Review PNGs for exp0 visually inspected, low pin density <=1.9/um, channelled surrounding plan; other29 require contact-sheet view before launch. No route approval granted. New OWNER? none; face_guard technical repairs remain open, argmax zero-cycle output clone is best next clean-timing candidate.

## HBM-CORES (sub-agent of lane HBM) 2026-10-24 21:50 PDT
- 2026-10-24 21:50 PDT HBM-CORES: branch claude/hbm-cores-1024 @146bce40d6 (= claude/elem-hbm-1024 + split2 @337f5e8619 + fixes), worktree epyc1:/srv/opentallas-scratch2/claude/wt/hbm-cores.
- HOLD ROOT CAUSE (16 of the 26 finish runs were stuck in GRT hold repair, the same as the 57 earlier non-convergent FAILs): the kit HOLD_SLACK_MARGIN=30 flow margin. FF probe on sfu lane14 4_cts: 1467 endpoints below 0 but 37822 below 30, mostly flop->flop paths in the 0..5 ps band. Repair ran ~20 it/min with a 4000-iteration cap, so it could never finish. Fix dd78a34eef: generator default margin 0. The gate is unchanged (FF hold with 25 ps SDC uncertainty).
- RELAUNCHED from CTS with margin 0 (kits regenerated, resumed through ot-run in the same run dir): sfu lanes 14/15/2/4/5/6/9, hc_bankq0 l0_2/l3_5, hc_bankq l0_2/l3_5, gq_issue, qcore_r13, vm_query n12. Also svc_pc 95777e with RLA 0.10 (GRT-0116 with 189 overflow; its 5 siblings passed GRT with RLA 0.10).
- KEPT: svc_pc 31be7c/3b586c/3ffaa4/9467d1/a4d8b0 (DRT/report), bdring 709af9 (hold converged) and 2f4ce4.
- FAIL, plan request: xcal_rel_t x4 GRT-0116 with heavy congestion (M2/M3 60-68% use, 74k overflow, M5 max, 210x210 um). It needs a bigger outline (~1.3x) or M6 signal grant, not a knob.
- MEMORY GUARD: Codex's measured 15616-bit patch was committed (ea66e18d2f). The 30 pgslice exp lanes were regenerated and their plan renders viewed (contact sheet epyc1:/srv/opentallas-scratch/claude/elem-hbm/hbmcores_mem30_plan.png): identical ~440x460 outlines, N/S pins at <=2 pins/um, well under budget. Place+CTS probes (GOAL=cts) are launched via ot-run.
- SPLIT2 CTS probes so far: tkm tiles I 438-445 ps; pgslice pretree 595-599; bankq_ft 326-362; lanes_plain4_7/8_11 clk_bank 475-597. lanes_plain12_15@871944 FAIL PDN-0179 (channel repair).
- HAZARD fixed: stale run dirs of the same kit name on 2 hosts let ot-run --dir run 5 jobs on old 14:xx data (killed at once). 77 stale duplicate run dirs deleted; resume.sh no longer passes --hosts.
- 2026-10-24 22:08 PDT HBM-CORES findings:
  - COLLECT: collect.py gives 0 SIGNED / 15 NOT SIGNED (results/b2l_verdicts.json @34f09bd789). New since the last record: svc_pc 31be7c (TT -155.6, FF -34.1, DRV slew 231, spread 125) and 9467d1 (TT -42.9, FF -25.6).
    - svc_pc root cause: 63% utilization in 155x155 um with an SRAM and 1229 pins on 2 faces. GRT passes only with RLA 0.10. The routed paths show 125-140 ps slews (detours) and 8-level AND5/OR4 control logic (controller.on.open -> c_oh).
    - PLAN REQUEST: grow the svc_pc_ctrl_leaf_cfg_h9b outline to <= 50% utilization (~1.3x area), or pipeline the controller in RTL. All 7 routed svc_pc kits fail TT setup (-21..-156).
  - FACE_GUARD (OWNER?): 348 of 370 synthesized core kits fail it. Only 22 pass, e.g. bankq_ft and bankq0 lanes0_2, which come from the registered as-built scoped masters.
    - Classes across kits: shared 338, dropped 216, unregistered 129, feedthrough 120, merged 8.
    - Cause is in the RTL, not the tool. The cores are as-built die logic cut at module ports, and those ports are not one flop per pin. Examples:
      - sfu lane i_pass feeds a 3-entry delay ring (3 enabled loads).
      - argmax vm_rq[134:0] is 8 copies of one 16-bit register (feedthrough).
      - argmax cr[255:x] and sfu ld_terms are unread input bits (dropped).
      - argmax imm_a and sfu i_emit feed OR2/AND2 directly (unregistered).
    - The fix needs a decision:
      - (a) a pin-register stage in every core wrapper (keep cells, +1 cycle per core crossing, static schedule recompile: HBM-ARCH); or
      - (b) the plan drops unread input pins and duplicate output copies (as decision 8 did for S81 constant outputs), and the rule for hard-core pins that are timed by the 20%-T IO budget becomes INFO.
    - Until then no core except bankq_ft/bankq0-type can SIGN.
  - SIGNOFF (CLOCK/SIGNOFF own signoff.py; not edited):
    - (1) The 'clock' check still gates pin-flop spread > 80 (signoff.py:645, BLOCKING), against decision 5. It blocks idx_query, sm_vm_wr_q, svc_pc 31be7c.
    - (2) The FF corner reuses the TT IO vclk latency (the SDC value I).
      - Measured on sfu lane14 4_cts: core tree mean 511 ps at TT, 419 ps at FF (ratio 0.82). The partition side scales the same way, so FF output hold is pessimistic by ~0.18*I (lane14 outputs -66 ps, an artifact) and FF input hold is optimistic by the same amount.
      - svc_pc 9467d1 FF hold -25.6 is input k_tag[6] -> kp_tag[6] with vclk 270 at FF; it is worse with an honest FF vclk.
      - Proposal for SIGNOFF: the FF corner uses vclk = I x (core FF mean / core TT mean), measured on the routed tree.
  - RESET (decision 2): ot_rst_relay with a core-local 2-flop sync_q synchroniser sits inside 31 core kits: svc_pc x10, bankq lanes6_7_bank x12, bfqg x4, sfu ctl, qw_dec, dma_back cp, tkm root, gq_land. Decision 2 allows ONE root synchroniser per region -> RTL item for HBM-ARCH/RESET.
  - CLOCK INSERTION (core_insertion_b2l.json @8ddbfc18f3, +53 probes): pgslice lanes0_3..28_31 I = 869-941 ps; 3400-sink clk_lane ports are fed from the face across 760x726 um (tree max 1161 ps > T).
    - PLAN REQUEST: in-core clock taps (decision 5b: density taps from the M8/M9 spine, ~1000-1500 sinks/tap) for pgslice lanes. Edge clock pins cannot meet the contract.
    - Also measured: lanes_plain 589-628, pretree 595-599, tkm tiles 438-445, coll_q2 259/312.
  - xcal_rel_t: 83% utilization (33.9k um2 in 210x211 um) -> GRT-0116. PLAN REQUEST: ~250x250 um (+45% area) for <= 55%.
  - ROUTE REQUEST sent to GEOM-REVIEW: bankq_ft lanes0_2 x2 + lanes3_5@1d3df8. face_guard PASS, kits regenerated under the contract, waiting for PASS.

## PARKED 2026-10-24 22:16 PDT (HBM-CORES)
- Branch: claude/hbm-cores-1024 @1d69cf3da1 (pushed). Worktree: epyc1:/srv/opentallas-scratch2/claude/wt/hbm-cores. Not merged: 0 SIGNED.
- Commits:
  - ea66e18d2f: memory guard 15616.
  - dd78a34eef: HOLD_SLACK_MARGIN 0.
  - 146bce40d6: resume.sh without --hosts.
  - 34f09bd789: verdicts.
  - 8ddbfc18f3: insertion table (+189 rows).
  - 1d69cf3da1: bankq_ft review records.
- LIVE JOBS. All are ot-run units, containers hbmcore-<kit>_-<pid>, run dirs <host>:/srv/opentallas-scratch/claude/elem-hbm/runs/<kit>. Lists are in epyc1:/srv/opentallas-scratch/claude/elem-hbm/.
  - (a) 14 finish runs restarted with margin 0 (hbmcores_restart14k.txt): sfu lanes 14/2/4/6 + bankq0 l0_2 + bankq x2 + qcore_r13 + vm_query on epyc1; lane15/lane5 + bankq0 l3_5 on intel1; lane9 + gq_issue on intel2. They re-run from synth because config.mk changed.
    - vm_query is in GRT hold repair: 4806 endpoints at margin 0 (was 21017 at 30), WNS -62 -> -57 after 70 iterations, converging.
  - (b) Other finish runs: svc_pc 95777e (RLA 0.10, GRT) and svc_pc 3b586c/3ffaa4/a4d8b0 (DRT) on epyc1/intel1. bdring 709af9 (epyc1) and 2f4ce4 (intel2): hold converged, GRT/route.
  - (c) CTS probes (GOAL=cts): 30 pgslice exp lanes (hbmcores_mem30.txt, 2 done), exp7_059f relaunched, 7 pgslice lanes*.
- NEXT:
  - 1. When the runs finish, run collect.py in the worktree and commit results/b2l_verdicts.json.
  - 2. After the CTS probes: run cts_gather.sh > hbmcores_cts_gather.txt, then update_insertion.py, then commit.
  - 3. On GEOM PASS for bankq_ft x3: launch.sh kits_b2l/<k> 32 8 finish (kits are already regenerated). These are the best SIGN candidates (face_guard PASS).
  - 4. SIGN is blocked for every other family by face_guard (OWNER? below).
- OWNER? / requests:
  - face_guard on hard-core pins: (a) wrapper pin registers (+1 cycle per crossing, HBM-ARCH schedule) or (b) plan drops unread/duplicate pins and the rule is INFO for IO-budget-timed core pins.
  - signoff.py: spread still gates (decision 5), and the FF corner uses the TT vclk latency. Both are for SIGNOFF/CLOCK.
  - Core-local reset synchronisers (ot_rst_relay) in 31 kits break decision 2.
  - PLAN: grow svc_pc (~1.3x), xcal_rel_t (~1.45x), idx_score_quarter (~1.45x, earlier). In-core clock taps for pgslice lanes (I 870-940). Earlier list from 20:20 still open.
  - lanes_plain12_15@871944: PDN-0179 (M2 VSS channel 4.6 um at y=396 between macros) -> macro halo/channel fix in the generator.
2026-10-24 23:11 PDT COORD (owner): fleet has ~1.5 TB admittable -- launch known fixes and alternative variants IN PARALLEL now (first to sign wins, delete losers at once); do not serialize fixes behind running attempts. Routes still need GEOM PASS and must not start on types the dec. 17 re-plan changes.

## HBM-CORES2 (sub-agent of lane HBM) 2026-10-24 23:23 PDT
- 2026-10-24 23:23 PDT HBM-CORES2: branch claude/hbm-cores-1024 @9e9e8feb8b (merged main c5834d0306; kits now ship main signoff.py + pair_skew.tcl = pair-skew gate, spread INFO; generator copies pair_skew.tcl). New signoff.py pushed into all 266 kits_b2l + run dirs on 5 hosts. Probe argmax_r2: TT 25.76 / FF 14.18 / pair skew TT/FF 31.9/29.5 / DRC 0 -> NOT SIGNED only on face_guard (timing-clean). Pair-skew re-signoff of the 14 other routed kits running (hc2_reso_<host>.log on epyc1/epyc3/intel1).
- LAUNCHED bankq_ft x3 finish (GEOM PASS 22:13) + PLACE_DENSITY 0.42 variants (_pd42), 6 ot-run units (epyc1 hc2_jobs.log).
- 30 pgslice exp lanes: CTS done, I 552-601 (core_insertion updated, 226 rows), kits regenerated under contract; author placed review PASS-COND; ROUTE request posted to GEOM-REVIEW (cond (1) clock source open).
- 2026-10-24 23:29 PDT HBM-CORES2: pair-skew re-signoff (main signoff.py) of routed kits so far, all NOT SIGNED: idx_score_quarter tail0 TT +34.3 / FF -6.7, tail1 TT +35.5 / FF -9.9, xp_aq_tree13_fmt 55d2 TT +18.7 / FF -16.4, a798 TT -14.4 / FF -10.2 (pair skew 23-47 PASS, DRC 0, all face_guard FAIL). Worst FF hold path on aq_tree13 = OUTPUT port y[256] vs vclk 250 ps ideal latency at FF while the core tree at FF is ~163 ps -> the known FF-IO-latency artefact (SIGNOFF item), not a design miss. idx_query (TT -143.9, pair skew 123) and svc_pc 31be7c (TT -155.6, pair skew 183) fail for real (plan: grow outline). argmax_r2 = timing-clean (face_guard only).
- LAUNCHED 19 variants/finishes (list in HBM-ARCH.md "## HBM-CORES2 launches"): bankq_ft x3 + _pd42, xcal x4 _m6, _cr (CTS hold repair + tight CTS clusters) for sfu lanes x7, qcore_r13, gq_issue. Cause behind _cr: the sfu hold probe shows intra-tree related-pair hold skew of -100 ps (u_pass ring m[0] -> qr); GRT repair fixes ~2 endpoints/iteration.

## PARKED 2026-10-24 23:42 PDT (HBM-CORES2)
- Branch claude/hbm-cores-1024 @0d4432fa9a (pushed). Worktree epyc1:/srv/opentallas-scratch2/claude/wt/hbm-cores. Merged main c5834d0306. Kits ship main signoff.py (pair-skew gate, spread INFO) + pair_skew.tcl. Both files were pushed into all kits_b2l and run dirs, so in-flight finishes sign off with the new gate. Not merged to main: 0 SIGNED.
- RESULTS (results/b2l_verdicts.json): 0 SIGNED, 15 NOT SIGNED, all face_guard FAIL.
  - TIMING-CLEAN (only face_guard fails): argmax_r2 (TT +25.8, FF +14.2, pair skew 31.9/29.5, DRC 0).
  - Near-clean, only FF hold misses: idx_score_quarter tail0 (TT +34.3, FF -6.7) and tail1 (TT +35.5, FF -9.9); xp_aq_tree13_fmt 55d2 (TT +18.7, FF -16.4). Their worst FF hold path is an OUTPUT port vs vclk at the TT latency, while the core tree at FF is ~0.65-0.8x. This is the SIGNOFF FF-IO-latency item.
  - Real misses:
    - idx_query: TT -143.9, pair skew 123.
    - svc_pc: 31be7c TT -155.6 (pair skew 183); 3f2f98 -47.3; 9467d1 -42.9; 684f/cfc8 similar.
    - hcp_sys1: TT -88.6.
    - vm_calendar: TT -30.7.
    - sm_vm_wr_q: TT -29.7, pair skew 89.7.
    - aq_tree13 a798: TT -14.4.
- GEOM: pgslice_lg lane_exp x30 FAIL 23:29 (13-15% fill, macros scattered, cond (1) clocks). Plan request is posted to HBM-ARCH: height ~205 um, family MACRO_PLACEMENT, clk/rst source. The run data was deleted; I 552-601 is kept in core_insertion_b2l.json; kits are regenerated under the contract and wait for the new outline.
- LIVE JOBS (ot-run; list in HBM-ARCH.md "## HBM-CORES2 launches"; log epyc1:/srv/opentallas-scratch/claude/elem-hbm/hc2_jobs.log; run dirs <host>:/srv/opentallas-scratch/claude/elem-hbm/runs/<kit>):
  - bankq_ft x3 (epyc1 x2, intel1) + _pd42 x3 (epyc3, intel2 x2): synth/floorplan.
  - xcal_rel_t x4 _m6 (intel2 x2, epyc3 x2): GRT passes at M6 (was GRT-0116 at M5). Hold repair now WNS -95..-166. These bind only with an M6 grant (OWNER?/HBM-ARCH) or the 1.45x outline.
  - _cr variants (CTS hold repair + CTS cluster 20/25), all in synth: sfu lanes 14/15/2/4/5/6/9, qcore_r13, gq_issue (intel2/epyc3).
  - Inherited base runs, carried to signoff:
    - GRT hold repair, converging slowly: bankq0 l0_2/l3_5, bankq l0_2/l3_5, sfu x7, qcore_r13, gq_issue. qcore WNS is stuck at -117 on e_f[69].
    - Route: vm_query n12, svc_pc 95777e/3b586c/3ffaa4/a4d8b0, bdring 2f4ce4.
- NEXT:
  1. When runs finish, run python3 collect.py in the worktree and commit. Delete the losing variant of each pair as soon as one signs or both fail.
  2. Once HBM-ARCH lands the outlines, regenerate and run place+CTS for the exp lanes and the 8 low-fill types, then GEOM review.
- OWNER?:
  - face_guard on hard-core pins blocks every SIGN except bankq_ft-type.
  - FF corner IO vclk latency (SIGNOFF).
  - M6 signal grant for xcal_rel_t.
2026-10-25 00:32 PDT COORD (sign-rate push, all die lanes): (1) DEFAULT CLOSING RECIPE for every new kit = the KV-proven m8 ECO (post-route repair setup+hold at TT and FF, fanout cap 24, then slew) + in-flow HOLD_SLACK_MARGIN 40 + output-face-flop hold targeting; (2) run face_guard (raw netlist) + SELRANGE + LEC right after synth and STOP before floorplan on any FAIL -- never discover a pin/RTL problem after a 10-h route; (3) every kit launches 2 recipe variants in parallel (memory-only admission), first SIGNED wins, losers deleted at once; (4) kits must stay <= ~250k cells where the plan allows (runtime + closure), hard cap 400k; (5) harvest finished runs every hour (signoff.py + record) -- a finished-but-uncollected run counts as a stall.

## HBM-CORES3 (sub-agent of lane HBM) 2026-10-25 00:35 PDT
- 2026-10-25 00:35 PDT HBM-CORES3: branch claude/hbm-cores-1024 @6bc0063c4e (pushed); worktree epyc1:/srv/opentallas-scratch2/claude/wt/hbm-cores. Imported B2n plan (claude/hbm-b2n-1024@871717c83) -> views_b2n.json: 280 views, 117 new (outline/pins changed): 30 exp-lane views (32 inst, 440.64x207.36), svc_pc x10 (177.984^2), xcal x4 (250.56^2), idx_score_quarter x70 (218.592x187.488), ep_static x2, bankq0 lanes6_7_bank, sfustore, gq_land, inj, programme_store.
- Generator: new --macro-placement/--macro-inst-fmt (exp lanes: B2n_inputs/exp_lane.json, 6 x ot_sram_1r1w_128x256_m1_r2c2 place_macro -exact at the family origins; instances u_core.u_bank.u_data.g_read[k].u_m). 117/117 kits generated (epyc1:/srv/opentallas-scratch/claude/elem-hbm/kits_b2n).
- LAUNCHED place+CTS (GOAL=cts, pre-review allowed) for all 117 via ot-run (log epyc1:.../elem-hbm/hc3_jobs.log). Route waits for GEOM PASS.
- Plan renders: epyc1:/srv/opentallas-scratch/claude/elem-hbm/review_b2n/<view>/{plan,context}.png, sheet .../hc3_b2n_plan_sheet.png. Seen: all faces <= 6 pins/um budget; exp lanes E 4.2 / W 2.6 pins/um; 5 reshaped cores have faces AT the 6 pins/um budget (bankq0 l67 N/S/E/W, sfustore E, gq_land N/S/W, inj E/W, ep_static@936 S) -> pin-access risk, watch at placement.
- COLLECT (results/b2l_verdicts.json): 0 SIGNED, 16 NOT SIGNED. New: vm_query n12 TT -3.2 / FF -38.8 (2625 ep) / slew 1975 viol, face_guard PASS; worst FF hold = output port vs vclk 259 ps at FF while core tree ~177 ps (FF-IO-latency artefact, SIGNOFF), real internal -11.8 (tags shift reg). cfg_collar_idx256r TT +33.4 / FF +8.6, fails only drv (1 slew) + face_guard.
- xcal_rel_t _m6 x4 DELETED (2 DPL-0033 FAIL, 2 superseded by the 250.56^2 outline now in place+CTS).
