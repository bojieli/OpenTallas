
## s81  (plan: plan_s10 (intel2 die-s81-10/plan, DIE-S81-15 basis); views: results/core_views_1028/s81 (NEW))

| core module | inst | early taps | max FF ins ps | signed | view (gate pin match) | OWNERS state | owner |
|---|---|---|---|---|---|---|---|
| ot_v41_rom_elem_q_qxpq_w10 | 864 | 864 | 402.1 | no | no | NEEDS-KIT | DRT-TRIAL |
| ot_v41_bf_col | 456 | 456 | 435.2 | no | no | NEEDS-KIT | PG-GRID-AUDIT |
| ot_s81sl_ve_m | 75 | 75 | 252.8 | no | no | FIX | S81-CORES |
| ot_s81sl_vn_a | 75 | 75 | 323.4 | no | no | FIX | S81 |
| ot_s81sl_vn_b | 75 | 75 | 324.3 | no | no | GEOM-REQ | S81-CORES |
| ot_s81sl_vsw | 75 | 75 | 243.2 | no | no | NEEDS-KIT | CORES-KITS-ALL |
| ot_s81dv_xfin | 16 | 16 | 228.4 | no | no | NEEDS-KIT | CORES-KITS-ALL |
| ot_s81sl_capc5r | 16 | 16 | 348.9 | no | no | NEEDS-KIT | S81 |
| ot_s81sl_eg | 16 | 16 | 290.1 | no | no | KIT-PLACED | S81-CORES |
| ot_s81sl_xrt1 | 14 | 14 | 355.5 | no | no | NEEDS-KIT | S81 |
| dsdv_bksel_q | 4 | 4 | 527.5 | no | no | NEEDS-KIT | S81 |
| ot_s81sl_xrt3 | 2 | 2 | 501.4 | no | no | NEEDS-KIT | S81 |
| dsdv_bk_g | 1 | 1 | 269.0 | no | no | KIT-PLACED | S81-CORES |
| dsdv_bksel_c | 1 | 1 | 302.2 | no | no | NEEDS-KIT | CORES-KITS-ALL |
| dsdv_gunit_l0 | 1 | 1 | 235.4 | no | no | FIX | S81-CORES |
| dsdv_gunit_l1 | 1 | 1 | 254.7 | no | no | NEEDS-KIT | S81-CORES |
| dsdv_gunit_l2 | 1 | 1 | 226.9 | no | no | KIT-PLACED | S81-CORES |
| dsdv_gunit_l4 | 1 | 1 | 252.9 | no | no | FIX | CODEX |
| dsdv_gunit_l5 | 1 | 1 | 364.1 | no | no | NEEDS-KIT | S81 |
| dsdv_idx_tx_n32 | 1 | 1 | 665.2 | no | no | KIT-PLACED | S81 |
| ot_rom_4096x72_m8 | 7644 | - | - | no | no | not in OWNERS |  |
| ot_dsrom_su_hcpost_lane_pr | 1200 | - | - | yes | no -- signed, committed view has no LEF/ETM (run data needed) | SIGNED | PATH-S81 |
| ot_s81c_attn_hcore | 1024 | - | - | no | no | FIX | PG-GRID-AUDIT |
| dsfd_qbank_N | 864 | - | - | unversioned | no -- SIGNED-UNVERSIONED retime record only; no view exported (no kit pins/freeze in record dir, UNCHECKED) | SIGNED-UNVERSIONED | S81-CORES |
| dsfd_qbank_S | 864 | - | - | no | no | FIX | CODEX |
| ot_s81_cfg7_seq | 864 | - | - | yes | yes, pins match 864/864 | SIGNED | TOK-ALL |
| ot_s81_sstn_base566 | 660 | - | - | no | no | FIX | CODEX |
| ot_s81_sstn_payload536 | 660 | - | - | yes | yes, pins match 0/660 (pins differ (canonical, no exact MX/MY/R180 image)) | SIGNED | S81-CORES |
| dsfd_node_LLfu | 516 | - | - | yes | yes, pins match 516/516 | SIGNED | S81-CORES |
| dsfd_node_NNfd | 516 | - | - | yes | yes, pins match 516/516 | SIGNED | S81-CORES |
| dsfd_node_LLfd | 504 | - | - | yes | yes, pins match 504/504 | SIGNED | S81-CORES |
| dsfd_node_NNfu | 504 | - | - | yes | yes, pins match 504/504 | SIGNED | S81-CORES |
| dsfd_bf_front_roots | 228 | - | - | no | no | NEEDS-KIT | DRT-TRIAL |
| ot_s81_cfg7_seq_bfp | 228 | - | - | no | no | FIX | S81-CORES |
| dsfd_rstg | 216 | - | - | yes | yes, pins match 0/216 (pins differ (canonical, no exact MX/MY/R180 image)) | SIGNED | S81-CORES |
| ot_sram_1r1w_512x128_m4_r0c0 | 150 | - | - | no | no | not in OWNERS |  |
| dsdv_svc_sx_hrow | 128 | - | - | yes | yes, pins match 128/128 | SIGNED | S81-ECO-1 |
| dsfd_su_t_rxsb | 75 | - | - | yes | no -- signed, committed view has no LEF/ETM (run data needed) | SIGNED | S81-CORES |
| dsfd_su_t_rxsf | 75 | - | - | no | no | FIX | S81-CORES |
| ot_s81sl_ve_s | 75 | - | - | no | no | FIX | S81-CORES |
| ot_s81sl_vq | 75 | - | - | yes | yes, pins match 0/75 (pins content differs) | SIGNED | FLOW-MCMM-GRT |
| ot_s81sl_vs | 75 | - | - | no | no | FIX | S81 |
| dsfd_cfifo_crs4 | 72 | - | - | no | no | NEEDS-KIT | CORES-KITS-ALL |
| dsfd_node_LLd | 72 | - | - | yes | yes, pins match 72/72 | SIGNED | S81-CORES |
| dsdv_eng_rr_e | 1 | - | - | no | no | KIT-PLACED | S81-CORES |
| dsdv_eng_rr_h0 | 1 | - | - | no | no | FIX | S81-CORES |
| dsdv_eng_rr_h1 | 1 | - | - | yes | no -- signed, committed view has no LEF/ETM (run data needed) | SIGNED | S81-CORES |
| dsdv_gunit_l0r | 1 | - | - | no | no | NEEDS-KIT | CODEX |
| dsdv_gunit_l1c | 1 | - | - | no | no | FIX | S81-CORES |
| dsdv_gunit_l3 | 1 | - | - | no | no | NEEDS-KIT | S81-CORES |
| dsdv_gunit_l4r | 1 | - | - | yes | yes, pins match 1/1 | SIGNED | S81-CORES |
| dsdv_gunit_l5f | 1 | - | - | yes | yes, pins match 1/1 | SIGNED | CORES-KITS-ALL |

## qwen_compute  (plan: qc_k2b_phase12 (DIE-QC-16 t11i basis); views: results/core_views_1028/qwen_compute (NEW))

| core module | inst | early taps | max FF ins ps | signed | view (gate pin match) | OWNERS state | owner |
|---|---|---|---|---|---|---|---|
| qfd_dv_s8x_vmr | 36 | 36 | 202.5 | unversioned | yes, pins match 36/36 | SIGNED-UNVERSIONED | CORES-KITS-ALL |
| qfd_dv_s5_su8_rst3 | 12 | 12 | 202.5 | yes | no -- OWNERS SIGNED but DEMOTED 10-27 (routed LEC KEEP FAIL, retired record); closed run has no pins/freeze -> no view | SIGNED | CODEX |
| qfd_dv_s8_crh_rp1 | 12 | 12 | 202.5 | yes | yes, pins match 12/12 | SIGNED | QC-PLAN |
| qfd_dv_s8x_btab | 12 | 12 | 295.2 | no | no | FIX | QC-CORES-4 |
| qfd_dv_s8x_crh | 12 | 12 | 240.6 | yes | yes, pins match 12/12 | SIGNED | QC-PLAN |
| qfd_dv_s8x_prog | 12 | 12 | 363.3 | yes | yes, pins match 12/12 | SIGNED | QC-CORES-CODEX |
| qfd_tile_nk_a0c | 720 | - | - | no | no | FIX | QC-SLICECLK |
| qfd_qc_su_lane_w | 96 | - | - | no | no | not in OWNERS |  |
| qfd_tile_nl_a0c | 48 | - | - | no | no | KIT-PLACED | QC-PLAN |

## hbm  (plan: origin/main hbm_arch/B2n; views: none)

| core module | inst | early taps | max FF ins ps | signed | view (gate pin match) | OWNERS state | owner |
|---|---|---|---|---|---|---|---|
| ot_hgi_sm_xload_cl2_bfqg | 16 | 320 | 311.9 | no | no | not in OWNERS |  |
| hnx_rp3lp3h_n | 128 | 128 | 202.5 | no | no | NEEDS-KIT | HBM-CORES-REBAL |
| hnx_rp3lp3h_s | 128 | 128 | 202.5 | no | no | NEEDS-KIT | HBM-CORES |
| hfd_vms_bank_native_q0_faces | 16 | 80 | 354.0 | no | no | not in OWNERS |  |
| ot_hbm_svc_pc_ctrl_leaf_cfg_h9b | 32 | 30 | 238.9 | no | no | not in OWNERS |  |
| ot_hgi_sm_xload_xq_pegress | 4 | 20 | 362.9 | no | no | not in OWNERS |  |
| ot_hbm_svc_vm_kshare_splitstrap | 8 | 16 | 439.8 | no | no | not in OWNERS |  |
| ot_hbm_su_static_pgslice_lg__side_rest | 4 | 12 | 417.1 | no | no | GEOM-REQ | DIE-HBM |
| ot_hbm_su_static_pgslice_lg__side_softplus | 4 | 12 | 463.3 | no | no | GEOM-REQ | DIE-HBM |
| ot_hbm_sm_vm_wr_q_t_lanes4 | 2 | 12 | 288.4 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_svc_sm_xcal_rel_t | 8 | 8 | 426.9 | no | no | not in OWNERS |  |
| ot_hbm_hc_bankq_static__lanes3_5 | 8 | 6 | 292.4 | no | no | not in OWNERS |  |
| hfd_ep_static | 6 | 5 | 467.4 | no | no | not in OWNERS |  |
| ot_pdie_serdes | 5 | 5 | 507.9 | no | no | NEEDS-KIT | LAND-HEAD |
| ot_hbm_hc_bankq_static__lanes0_2 | 8 | 4 | 292.4 | no | no | not in OWNERS |  |
| ot_hbm_su_static_pgslice_lg__lane_exp0 | 4 | 4 | 454.4 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_su_static_pgslice_lg__lane_exp1 | 4 | 4 | 486.8 | no | no | not in OWNERS |  |
| ot_hbm_su_static_pgslice_lg__lane_exp10 | 4 | 4 | 478.7 | no | no | not in OWNERS |  |
| ot_hbm_su_static_pgslice_lg__lane_exp11 | 4 | 4 | 486.0 | no | no | not in OWNERS |  |
| ot_hbm_su_static_pgslice_lg__lane_exp12 | 4 | 4 | 461.7 | no | no | not in OWNERS |  |
| ot_hbm_su_static_pgslice_lg__lane_exp13 | 4 | 4 | 466.6 | no | no | not in OWNERS |  |
| ot_hbm_su_static_pgslice_lg__lane_exp14 | 4 | 4 | 464.9 | no | no | not in OWNERS |  |
| ot_hbm_su_static_pgslice_lg__lane_exp2 | 4 | 4 | 474.7 | no | no | not in OWNERS |  |
| ot_hbm_su_static_pgslice_lg__lane_exp3 | 4 | 4 | 472.2 | no | no | not in OWNERS |  |
| ot_hbm_su_static_pgslice_lg__lane_exp4 | 4 | 4 | 465.8 | no | no | not in OWNERS |  |
| ot_hbm_su_static_pgslice_lg__lane_exp5 | 4 | 4 | 482.8 | no | no | not in OWNERS |  |
| ot_hbm_su_static_pgslice_lg__lane_exp6 | 4 | 4 | 473.9 | no | no | not in OWNERS |  |
| ot_hbm_su_static_pgslice_lg__lane_exp7 | 4 | 4 | 485.2 | no | no | not in OWNERS |  |
| ot_hbm_su_static_pgslice_lg__lane_exp8 | 4 | 4 | 451.2 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_su_static_pgslice_lg__lane_exp9 | 4 | 4 | 448.7 | no | no | not in OWNERS |  |
| ot_hbm_su_static_pgslice_lg__lane_exp_l | 4 | 4 | 452.8 | no | no | not in OWNERS |  |
| ot_hgi_sm_xload_cl2_bdring | 4 | 4 | 233.3 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c0_k0h0 | 2 | 4 | 208.2 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_idx_score_quarter_static__r0c0_k0h1 | 2 | 4 | 206.6 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_idx_score_quarter_static__r0c0_k1h0 | 2 | 4 | 208.2 | no | no | GEOM-REQ | HBM-CORES |
| ot_hbm_idx_score_quarter_static__r0c0_k1h1 | 2 | 4 | 208.2 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c0_k2h0 | 2 | 4 | 206.6 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c0_k2h1 | 2 | 4 | 207.4 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_idx_score_quarter_static__r0c0_k3h0 | 2 | 4 | 209.0 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c0_k3h1 | 2 | 4 | 207.4 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_idx_score_quarter_static__r0c1_k0h0 | 2 | 4 | 209.0 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c1_k0h1 | 2 | 4 | 208.2 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c1_k1h0 | 2 | 4 | 207.4 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c1_k1h1 | 2 | 4 | 208.2 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c1_k2h0 | 2 | 4 | 207.4 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_idx_score_quarter_static__r0c1_k2h1 | 2 | 4 | 207.4 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_idx_score_quarter_static__r0c1_k3h0 | 2 | 4 | 207.4 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_idx_score_quarter_static__r0c1_k3h1 | 2 | 4 | 208.2 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c2_k0h1 | 2 | 4 | 209.8 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c2_k1h0 | 2 | 4 | 207.4 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c2_k1h1 | 2 | 4 | 208.2 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c2_k2h0 | 2 | 4 | 207.4 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c2_k2h1 | 2 | 4 | 208.2 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c2_k3h0 | 2 | 4 | 207.4 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c2_k3h1 | 2 | 4 | 206.6 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c3_k0h0 | 2 | 4 | 206.6 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c3_k0h1 | 2 | 4 | 208.2 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c3_k1h0 | 2 | 4 | 209.0 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c3_k1h1 | 2 | 4 | 208.2 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c3_k2h0 | 2 | 4 | 206.6 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c3_k3h0 | 2 | 4 | 208.2 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r0c3_k3h1 | 2 | 4 | 207.4 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_idx_score_quarter_static__r1c0_k0h0 | 2 | 4 | 207.4 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_idx_score_quarter_static__r1c0_k1h0 | 2 | 4 | 208.2 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c0_k1h1 | 2 | 4 | 206.6 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c0_k2h0 | 2 | 4 | 207.4 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c0_k2h1 | 2 | 4 | 209.0 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c0_k3h0 | 2 | 4 | 207.4 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c0_k3h1 | 2 | 4 | 207.4 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c1_k0h0 | 2 | 4 | 206.6 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_idx_score_quarter_static__r1c1_k0h1 | 2 | 4 | 207.4 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c1_k1h0 | 2 | 4 | 207.4 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c1_k1h1 | 2 | 4 | 206.6 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c1_k2h0 | 2 | 4 | 209.0 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c1_k2h1 | 2 | 4 | 207.4 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c1_k3h0 | 2 | 4 | 208.2 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c1_k3h1 | 2 | 4 | 208.2 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_idx_score_quarter_static__r1c2_k0h1 | 2 | 4 | 208.2 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c2_k1h1 | 2 | 4 | 209.0 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c2_k2h0 | 2 | 4 | 209.8 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c2_k2h1 | 2 | 4 | 208.2 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c2_k3h0 | 2 | 4 | 207.4 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c2_k3h1 | 2 | 4 | 208.2 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c3_k0h0 | 2 | 4 | 208.2 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c3_k0h1 | 2 | 4 | 208.2 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c3_k1h0 | 2 | 4 | 206.6 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c3_k1h1 | 2 | 4 | 209.0 | no | no | not in OWNERS |  |
| ot_hbm_idx_score_quarter_static__r1c3_k2h0 | 2 | 4 | 209.0 | no | no | not in OWNERS |  |
| ot_hgi_coll_inj_idx_join_rg | 2 | 4 | 337.8 | no | no | GEOM-REQ | HBM-CORES |
| ot_hgi_sfu_core_split3__lane0 | 2 | 4 | 410.7 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hgi_sfu_core_split3__lane1 | 2 | 4 | 396.1 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hgi_sfu_core_split3__lane10 | 2 | 4 | 390.4 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hgi_sfu_core_split3__lane11 | 2 | 4 | 390.4 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hgi_sfu_core_split3__lane12 | 2 | 4 | 359.6 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hgi_sfu_core_split3__lane13 | 2 | 4 | 364.5 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hgi_sfu_core_split3__lane14 | 2 | 4 | 413.9 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hgi_sfu_core_split3__lane15 | 2 | 4 | 383.1 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hgi_sfu_core_split3__lane2 | 2 | 4 | 396.1 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hgi_sfu_core_split3__lane3 | 2 | 4 | 413.1 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hgi_sfu_core_split3__lane4 | 2 | 4 | 364.5 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hgi_sfu_core_split3__lane5 | 2 | 4 | 408.2 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hgi_sfu_core_split3__lane6 | 2 | 4 | 396.1 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hgi_sfu_core_split3__lane7 | 2 | 4 | 396.1 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hgi_sfu_core_split3__lane8 | 2 | 4 | 406.6 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hgi_sfu_core_split3__lane9 | 2 | 4 | 365.3 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hgi_sm_xload_cl2_ctlx | 2 | 4 | 409.1 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_hc_bankq0_static__lanes0_2 | 2 | 2 | 288.4 | no | no | RETIRED | HBM-CORES |
| ot_hbm_hc_bankq0_static__lanes3_5 | 2 | 2 | 286.7 | no | no | RETIRED | HBM-CORES |
| ot_hbm_hc_bankq0_static__lanes6_7_bank | 2 | 2 | 652.9 | no | no | RETIRED | HBM-CORES |
| ot_hbm_hc_bankq_term_static__lanes3_5 | 2 | 2 | 292.4 | no | no | not in OWNERS |  |
| ot_hbm_idx_query_static | 2 | 2 | 222.8 | no | no | GEOM-REQ | HBM-CORE-LAT |
| ot_hbm_idx_score_quarter_static__tail0 | 2 | 2 | 207.4 | no | no | GEOM-REQ | HBM-CORES |
| ot_hbm_idx_score_quarter_static__tail1 | 2 | 2 | 208.2 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_idx_vm_query_static_n12 | 2 | 2 | 209.8 | no | no | KIT-PLACED | HBM-CORES |
| ot_hbm_su_static_cxport_ij_q | 2 | 2 | 362.1 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_su_static_qcore_r13 | 2 | 2 | 351.5 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_su_static_sfustore_hw | 2 | 2 | 445.5 | no | no | FIX | HBM-CORES |
| ot_hgi_coll_gq_issue | 2 | 2 | 277.8 | no | no | NEEDS-KIT | DIE-HBM |
| ot_hgi_coll_gq_land | 2 | 2 | 265.7 | no | no | FIX | HBM-CORES |
| ot_hgi_qw_dec | 2 | 2 | 298.1 | no | no | NEEDS-KIT | DIE-HBM |
| ot_hgi_sfu_programme_store_r10 | 2 | 2 | 931.5 | no | no | NEEDS-KIT | HBM-CORES |
| ot_hbm_hc_root_static__hcp_sys1 | 1 | 1 | 203.3 | no | no | KIT-PLACED | HBM-CORES |
| ot_hbm_static_cfg_collar_idx256r | 1 | - | - | unversioned | no -- SIGNED-UNVERSIONED; not in the B2n plan | SIGNED-UNVERSIONED | HBM-CORES |

HBM early-tapped modules by OWNERS state: {'not in OWNERS': 69, 'NEEDS-KIT': 40, 'GEOM-REQ': 6, 'RETIRED': 3, 'KIT-PLACED': 2, 'FIX': 2}; non-early modules omitted (87).

## qwen_kvsys  (plan: origin/main die_plan.json; views: physical/ref_tile/kv3_head_eighth_e{1,5}/views (existing))

| core module | inst | early taps | max FF ins ps | signed | view (gate pin match) | OWNERS state | owner |
|---|---|---|---|---|---|---|---|
| kv3_head_eighth_e1 | 256 | - | - | yes | yes, pins match 0/256 (pins content differs) | SIGNED | KV-CORES |
| kv3_head_eighth_e5 | 256 | - | - | yes | yes, pins match 0/256 (pins content differs) | SIGNED | KV-CORES |
| kv3_head_eighth_e6 | 256 | - | - | no | no | ROUTING | KV-CORES |
| kv3_pv_pair | 256 | - | - | no | no | FIX | KV-CORES |
| kv3_head_eighth_e0 | 128 | - | - | no | no | ROUTING | KV-CORES |
| kv3_head_eighth_e2 | 128 | - | - | no | no | ROUTING | KV-CORES |
| qkd_kvs_pc | 124 | - | - | no | no | KIT-PLACED | KV-CORES |
| ot_qwen_tp8_pv_join_t | 64 | - | - | no | no | REVIEW | KV-CORES |
| qkd_ectlk_q0 | 32 | - | - | no | no | FIX | KV-CORES |
| qkd_ectlk_q1 | 32 | - | - | no | no | GEOM-REQ | KV-CORES |
| qkd_ectlk_q2 | 32 | - | - | no | no | NEEDS-KIT | KV-CORES |
| qkd_ectlk_q3 | 32 | - | - | no | no | GEOM-REQ | KV-CORES |
| qkd_hr_phy_adp | 8 | - | - | no | no | NEEDS-KIT | KV-CORES |
| kv3_astk | 4 | - | - | no | no | KIT-PLACED | KV-CORES |
| qkd_kvs_pc_h_head_p | 4 | - | - | no | no | GEOM-REQ | KV-KITS-7 |
| qkd_ahub | 1 | - | - | no | no | KIT-PLACED | CLOCK-KV |
| qkd_hr_cdc_ch | 1 | - | - | no | no | NEEDS-KIT | KV-CORES |
| qkd_hr_cdc_ci | 1 | - | - | no | no | NEEDS-KIT | KV-CORES |
| qkd_hr_cdc_hi | 1 | - | - | no | no | NEEDS-KIT | KV-CORES |
| qkd_hr_cdc_pc | 1 | - | - | no | no | NEEDS-KIT | KV-CORES |
| qkd_hr_core_guard | 1 | - | - | no | no | NEEDS-KIT | KV-CORES |
| qkd_hr_core_order | 1 | - | - | no | no | NEEDS-KIT | KV-CORES |
| qkd_hr_core_peer | 1 | - | - | no | no | NEEDS-KIT | KV-CORES |
| qkd_hr_core_prompt | 1 | - | - | no | no | NEEDS-KIT | KV-CORES |
| qkd_hr_core_queue | 1 | - | - | no | no | NEEDS-KIT | KV-CORES |
| qkd_hr_core_rx | 1 | - | - | no | no | NEEDS-KIT | KV-CORES |
| qkd_hr_core_tx | 1 | - | - | no | no | NEEDS-KIT | KV-CORES |
| qkd_hr_host_qm | 1 | - | - | no | no | FIX | KV-CORES |
| qkd_hr_ingest_eng | 1 | - | - | no | no | NEEDS-KIT | KV-CORES |
| qkd_hr_phy_pad | 1 | - | - | no | no | ROUTING | KV-CORES |
| qkd_kvs_ctl | 1 | - | - | no | no | NEEDS-KIT | CORES-KITS-ALL |

## s81_head  (plan: origin/main die_plan.json; views: results/die_head_1027/views (existing))

| core module | inst | early taps | max FF ins ps | signed | view (gate pin match) | OWNERS state | owner |
|---|---|---|---|---|---|---|---|
| ot_s81hd_elemA_cv | 1056 | - | - | yes | yes, pins match 1056/1056 | SIGNED | LAND-HEAD |
| ot_s81hd_elemB_cv | 264 | - | - | yes | yes, pins match 264/264 | SIGNED | S81-HEAD |
| ot_s81hd_lep_pair | 4 | - | - | no | no | NEEDS-KIT | LAND-HEAD |
