### s81 (physical/die_plan/s81/die_plan.json)

counts {'NEEDS RE-RUN': 37}; NEEDS RE-RUN whose last record already fails the standard on paper: 29; not-closed plan cores (not counted): 0

| module | inst | status | rec SS setup (closure corner: setup) | rec FF hold | rec spread TT/FF | kit in repo | paper |
|---|---|---|---|---|---|---|---|
| dsdv_bk_g | 1 | NEEDS RE-RUN | -295.16 (TT: 17.77) | 6.59 | 67.5/59.6 | yes | FAIL: recorded SS setup -295.16 ps (closed at TT setup +17.77) |
| dsdv_bksel_c | 1 | NEEDS RE-RUN | -302.7 (TT: 54.58) | 8.99 | 51.6/48.5 | yes | FAIL: recorded SS setup -302.70 ps (closed at TT setup +54.58) |
| dsdv_bksel_q | 4 | NEEDS RE-RUN | -309.48 (TT: 37.37) | 5.16 | 65.9/61.2 | yes | FAIL: recorded SS setup -309.48 ps (closed at TT setup +37.37) |
| dsdv_eng_tap | 15 | NEEDS RE-RUN | -187.47 (TT: 38.55) | 22.75 | 24.8/23.3 | NO | FAIL: recorded SS setup -187.47 ps (closed at TT setup +38.55) |
| dsdv_eng_tap_w | 1 | NEEDS RE-RUN | -213.88 (TT: 76.26) | 19.93 | 21.9/21 | NO | FAIL: recorded SS setup -213.88 ps (closed at TT setup +76.26) |
| dsdv_gunit_l0 | 1 | NEEDS RE-RUN | -52.16 (TT: 198.78) | 5.63 | 58.2/55.6 | yes | FAIL: recorded SS setup -52.16 ps (closed at TT setup +198.78) |
| dsdv_gunit_l0r | 1 | NEEDS RE-RUN | -310.65 (TT: 24.55) | 24.06 | 12.5/12.6 | yes | FAIL: recorded SS setup -310.65 ps (closed at TT setup +24.55) |
| dsdv_gunit_l1 | 1 | NEEDS RE-RUN | -263.71 (TT: 59.31) | 2.71 | 76/73.7 | yes | FAIL: recorded SS setup -263.71 ps (closed at TT setup +59.31) |
| dsdv_gunit_l1c | 1 | NEEDS RE-RUN | -371.01 (TT: 0.11) | 16.71 | 36.2/36.3 | yes | FAIL: recorded SS setup -371.01 ps (closed at TT setup +0.11) |
| dsdv_gunit_l2 | 1 | NEEDS RE-RUN | -197.32 (TT: 74.7) | 4.99 | 48.9/47.3 | yes | FAIL: recorded SS setup -197.32 ps (closed at TT setup +74.70) |
| dsdv_gunit_l3 | 1 | NEEDS RE-RUN | -195.47 (TT: 133.72) | 10.01 | 61/58.5 | yes | FAIL: recorded SS setup -195.47 ps (closed at TT setup +133.72) |
| dsdv_gunit_l4 | 1 | NEEDS RE-RUN | -281.11 (TT: 71.87) | 5.94 | 52.8/52 | yes | FAIL: recorded SS setup -281.11 ps (closed at TT setup +71.87) |
| dsdv_gunit_l4r | 1 | NEEDS RE-RUN | -162.6 (TT: 144.14) | 18.96 | 10.6/10.1 | yes | FAIL: recorded SS setup -162.60 ps (closed at TT setup +144.14) |
| dsdv_gunit_l5 | 1 | NEEDS RE-RUN | -2935.05 (TT: 20.6) | 20.07 | 101.9/95.3 | yes | FAIL: recorded TT pin-flop spread 101.9 ps > 80; recorded FF pin-flop spread 95.3 ps > 80; recorded SS setup -2935.05 ps (closed at TT setup +20.60) |
| dsdv_gunit_l5f | 1 | NEEDS RE-RUN | -162.9 (TT: 151.76) | 22.01 | 11.4/11 | yes | FAIL: recorded SS setup -162.90 ps (closed at TT setup +151.76) |
| dsdv_idx_tx_n32 | 1 | NEEDS RE-RUN | - (-: -) | - | -/- | NO | NO RECORD: no closed record in the repo |
| dsfd_bf_front_roots | 228 | NEEDS RE-RUN | -292.83 (TT: 0) | 18.2 | 9.9/8.4 | NO | FAIL: recorded SS setup -292.83 ps (closed at TT setup +0.00) |
| dsfd_cfifo_crs4 | 72 | NEEDS RE-RUN | -150.37 (TT: 40.3) | 11.34 | 61.3/60.6 | yes | FAIL: recorded SS setup -150.37 ps (closed at TT setup +40.30) |
| dsfd_node_LLd | 72 | NEEDS RE-RUN | -242.37 (TT: 95.22) | 23.29 | 12.8/13.1 | yes | FAIL: recorded SS setup -242.37 ps (closed at TT setup +95.22) |
| dsfd_node_LLfd | 504 | NEEDS RE-RUN | -257.04 (TT: 89.29) | 18.49 | 13.1/12.7 | yes | FAIL: recorded SS setup -257.04 ps (closed at TT setup +89.29) |
| dsfd_node_LLfu | 516 | NEEDS RE-RUN | -271.75 (TT: 84.29) | 22.89 | 16.3/17.1 | yes | FAIL: recorded SS setup -271.75 ps (closed at TT setup +84.29) |
| dsfd_node_NNfd | 516 | NEEDS RE-RUN | -249 (TT: 100.18) | 16.83 | 14.2/14.3 | yes | FAIL: recorded SS setup -249.00 ps (closed at TT setup +100.18) |
| dsfd_node_NNfu | 504 | NEEDS RE-RUN | -259.48 (TT: 90.08) | 12.49 | 25.1/24.1 | yes | FAIL: recorded SS setup -259.48 ps (closed at TT setup +90.08) |
| dsfd_qbank_N | 864 | NEEDS RE-RUN | 248.61 (TT: 332.23) | 1.58 | 2.8/3.1 | yes | PASS |
| dsfd_qbank_S | 864 | NEEDS RE-RUN | 69.7 (TT: 214.61) | 21.41 | 12.8/13.1 | yes | PASS |
| dsfd_rstg | 216 | NEEDS RE-RUN | 228.33 (TT: 328.42) | 30.99 | 1.2/1.4 | yes | PASS |
| ot_s81_cfg7_seq | 864 | NEEDS RE-RUN | 119.66 (TT: 321.2) | 25.53 | 12/11.3 | yes | PASS |
| ot_s81_cfg7_seq_bfp | 228 | NEEDS RE-RUN | -24.67 (TT: 244.26) | 23.88 | 14.4/13.5 | yes | FAIL: recorded SS setup -24.67 ps (closed at TT setup +244.26) |
| ot_s81_sstn_base566 | 660 | NEEDS RE-RUN | 232.82 (TT: 329.25) | 24.82 | 14.5/14.5 | yes | PASS |
| ot_s81_sstn_payload536 | 660 | NEEDS RE-RUN | 255.69 (TT: 344.2) | 26.61 | 8.8/9 | yes | PASS |
| ot_s81dv_xfin | 16 | NEEDS RE-RUN | -345.05 (TT: 4.78) | 11.46 | 57.8/56.2 | yes | FAIL: recorded SS setup -345.05 ps (closed at TT setup +4.78) |
| ot_s81sl_capc5r | 16 | NEEDS RE-RUN | 185.74 (TT: 326.69) | 13.38 | 0/0 | yes | PASS |
| ot_s81sl_eg | 16 | NEEDS RE-RUN | -294.79 (TT: 71.85) | 16.24 | 10.1/10.6 | yes | FAIL: recorded SS setup -294.79 ps (closed at TT setup +71.85) |
| ot_s81sl_xrt1 | 15 | NEEDS RE-RUN | -238.75 (TT: 40.44) | 9.45 | 69.1/64.5 | yes | FAIL: recorded SS setup -238.75 ps (closed at TT setup +40.44) |
| ot_s81sl_xrt3 | 1 | NEEDS RE-RUN | -304.84 (TT: 9.5) | 10.86 | 64.1/54.4 | yes | FAIL: recorded SS setup -304.84 ps (closed at TT setup +9.50) |
| ot_v41_bf_col | 456 | NEEDS RE-RUN | -221.99 (TT: 63.59) | 6.24 | 44.4/32.6 | NO | FAIL: recorded SS setup -221.99 ps (closed at TT setup +63.59) |
| ot_v41_rom_elem_q_qxpq_w10 | 864 | NEEDS RE-RUN | -182.29 (TT: 116.28) | 12.25 | 50.2/38.2 | NO | FAIL: recorded SS setup -182.29 ps (closed at TT setup +116.28) |

### qwen_compute (physical/die_plan/qwen_compute/die_plan.json)

counts {'NEEDS RE-RUN': 21}; NEEDS RE-RUN whose last record already fails the standard on paper: 16; not-closed plan cores (not counted): 7

| module | inst | status | rec SS setup (closure corner: setup) | rec FF hold | rec spread TT/FF | kit in repo | paper |
|---|---|---|---|---|---|---|---|
| ot_hdc_sfu_exp_t | 96 | NEEDS RE-RUN | -309.97 (TT: 47.82) | 21.69 | 5.1/4.5 | yes | FAIL: recorded SS setup -309.97 ps (closed at TT setup +47.82) |
| ot_hdc_sfu_rcp_t | 96 | NEEDS RE-RUN | -277.47 (TT: 74.83) | 18.55 | 10.8/10.1 | yes | FAIL: recorded SS setup -277.47 ps (closed at TT setup +74.83) |
| ot_hdc_sfu_rsq_t | 96 | NEEDS RE-RUN | -309.07 (TT: 55.5) | 22.16 | 1.8/2.1 | yes | FAIL: recorded SS setup -309.07 ps (closed at TT setup +55.50) |
| ot_qfd_xs_leaf | 192 | NEEDS RE-RUN | -288.6 (TT: 62.32) | 23.38 | 15.4/15.1 | NO | FAIL: recorded SS setup -288.60 ps (closed at TT setup +62.32) |
| qfd_dv_lane_h_safe2 | 96 | NEEDS RE-RUN | -362.04 (TT: 10.97) | 6.5 | 82.4/77 | yes | FAIL: recorded TT pin-flop spread 82.4 ps > 80; recorded SS setup -362.04 ps (closed at TT setup +10.97) |
| qfd_dv_redstn2_region | 48 | NEEDS RE-RUN | -221.45 (TT: 74.64) | 18.08 | 60.4/58.7 | yes | FAIL: recorded SS setup -221.45 ps (closed at TT setup +74.64) |
| qfd_dv_s5_ctl_repair4_leaf | 12 | NEEDS RE-RUN | -265.74 (TT: 16.56) | 1.18 | 70.8/62.3 | yes | FAIL: recorded SS setup -265.74 ps (closed at TT setup +16.56) |
| qfd_dv_s5_lrly | 96 | NEEDS RE-RUN | 178.48 (TT: 298.94) | 20.52 | 34.5/33.4 | NO | PASS |
| qfd_dv_s5_su8_rst3 | 12 | NEEDS RE-RUN | -205.86 (TT: 121.91) | 7.42 | 33.4/31.8 | yes | FAIL: recorded SS setup -205.86 ps (closed at TT setup +121.91) |
| qfd_dv_s5_xhead3 | 24 | NEEDS RE-RUN | -278.04 (TT: 29.92) | 18.15 | 63.7/61.5 | yes | FAIL: recorded SS setup -278.04 ps (closed at TT setup +29.92) |
| qfd_dv_s8_crh_rp1 | 12 | NEEDS RE-RUN | -17.91 (TT: 166.12) | 19.36 | 30.3/29.7 | yes | FAIL: recorded SS setup -17.91 ps (closed at TT setup +166.12) |
| qfd_dv_s8_station_tail1 | 48 | NEEDS RE-RUN | -263.4 (TT: 62.87) | 16.31 | 84/80.2 | yes | FAIL: recorded TT pin-flop spread 84.0 ps > 80; recorded FF pin-flop spread 80.2 ps > 80; recorded SS setup -263.40 ps (closed at TT setup +62.87) |
| qfd_dv_s8x_btab | 12 | NEEDS RE-RUN | -6.34 (TT: 263.37) | 1.41 | 42.7/42.8 | NO | FAIL: recorded SS setup -6.34 ps (closed at TT setup +263.37) |
| qfd_dv_s8x_crh | 12 | NEEDS RE-RUN | -64.37 (TT: 132.79) | 3.53 | 54.4/51.7 | yes | FAIL: recorded SS setup -64.37 ps (closed at TT setup +132.79) |
| qfd_dv_s8x_prog | 12 | NEEDS RE-RUN | 50.3 (TT: 219.75) | 8.19 | 35/33.4 | NO | PASS |
| qfd_dv_s8x_vmr | 36 | NEEDS RE-RUN | 43.88 (TT: 202.15) | 13.1 | 69/65.3 | NO | PASS |
| qfd_dv_slice_tload | 12 | NEEDS RE-RUN | -230.95 (TT: 19.14) | 14.46 | 38.5/38.4 | NO | FAIL: recorded SS setup -230.95 ps (closed at TT setup +19.14) |
| qfd_dv_stream_tile | 12 | NEEDS RE-RUN | -276.71 (TT: 18.64) | 16.99 | 57.1/55.5 | yes | FAIL: recorded SS setup -276.71 ps (closed at TT setup +18.64) |
| qfd_tile_nk_romleaf_rpf | 720 | NEEDS RE-RUN | - (-: -) | - | -/- | NO | NO RECORD: no closed record in the repo |
| qfd_tile_nl_romleaf_rpf | 48 | NEEDS RE-RUN | - (-: -) | - | -/- | NO | NO RECORD: no closed record in the repo |
| qfd_ucie_six_five | 1 | NEEDS RE-RUN | -176.98 (TT: 27.85) | 20.9 | 31.6/31.5 | yes | FAIL: recorded SS setup -176.98 ps (closed at TT setup +27.85) |

### qwen_kvsys (physical/die_plan/qwen_kvsys/die_plan.json)

counts {'NEEDS RE-RUN': 20}; NEEDS RE-RUN whose last record already fails the standard on paper: 9; not-closed plan cores (not counted): 30

| module | inst | status | rec SS setup (closure corner: setup) | rec FF hold | rec spread TT/FF | kit in repo | paper |
|---|---|---|---|---|---|---|---|
| ot_qkh_head_score4_native | 128 | NEEDS RE-RUN | 211.89 (TT: 316.98) | 25.72 | 2.8/2.2 | yes | PASS |
| ot_qkh_head_stin_native | 2048 | NEEDS RE-RUN | 253.02 (TT: 342.95) | 20.38 | 10/10.4 | yes | PASS |
| ot_qkh_head_stk_native | 2048 | NEEDS RE-RUN | 250.52 (TT: 340.98) | 28.23 | 1.9/1.8 | yes | PASS |
| ot_qkh_ktree_lk | 128 | NEEDS RE-RUN | -88.42 (TT: 198.95) | 23.07 | 17.5/17.4 | yes | FAIL: recorded SS setup -88.42 ps (closed at TT setup +198.95) |
| ot_qwen_tp8_pv_join_t | 64 | NEEDS RE-RUN | -271.12 (TT: 80.23) | 23.23 | 50.2/49.8 | yes | FAIL: recorded SS setup -271.12 ps (closed at TT setup +80.23) |
| ot_qwen_tp8_pv_slice_t | 512 | NEEDS RE-RUN | -273.24 (TT: 46.74) | 16.06 | 31.9/31.5 | yes | FAIL: recorded SS setup -273.24 ps (closed at TT setup +46.74) |
| qkd_astk_fault_join | 9 | NEEDS RE-RUN | 392.5 (TT: 431.16) | 27.12 | 0/0 | yes | PASS |
| qkd_ctrl_kc | 4 | NEEDS RE-RUN | 19.05 (TT: 92.08) | 25.46 | 3.2/3.3 | yes | PASS |
| qkd_embgw | 1 | NEEDS RE-RUN | -353.25 (TT: 29.09) | 6.37 | 42.3/40 | yes | FAIL: recorded SS setup -353.25 ps (closed at TT setup +29.09) |
| qkd_hp_or2 | 87 | NEEDS RE-RUN | 307.59 (TT: 379.81) | 66.33 | 0/0 | yes | PASS |
| qkd_kvs_ctl | 1 | NEEDS RE-RUN | -295.24 (TT: 24.38) | 8.88 | 121.8/109.3 | yes | FAIL: recorded TT pin-flop spread 121.8 ps > 80; recorded FF pin-flop spread 109.3 ps > 80; recorded SS setup -295.24 ps (closed at TT setup +24.38) |
| qkd_kvs_emb | 1 | NEEDS RE-RUN | -369.4 (TT: 27.3) | 13.35 | 149.9/66.7 | yes | FAIL: recorded TT pin-flop spread 149.9 ps > 80; recorded SS setup -369.40 ps (closed at TT setup +27.30) |
| qkd_kvs_hroot | 4 | NEEDS RE-RUN | -219.78 (TT: 40.47) | 16.77 | 42.5/42 | yes | FAIL: recorded SS setup -219.78 ps (closed at TT setup +40.47) |
| qkd_pv_rs_hd_f | 2 | NEEDS RE-RUN | 228.38 (TT: 326.13) | 21.55 | 35.5/34.2 | yes | PASS |
| qkd_rlyi_258s | 128 | NEEDS RE-RUN | 108.93 (TT: 334.8) | 27.45 | 5.6/5.7 | yes | PASS |
| qkd_seq_core_static_s | 1 | NEEDS RE-RUN | -99.68 (TT: 189.52) | 21.81 | 16.9/17.6 | yes | FAIL: recorded SS setup -99.68 ps (closed at TT setup +189.52) |
| qkd_seq_fan_s | 4 | NEEDS RE-RUN | 235.62 (TT: 326.77) | 18.06 | 14.4/14.2 | yes | PASS |
| qkd_seq_xs_s | 4 | NEEDS RE-RUN | -103.57 (TT: 155.4) | 19.39 | 16.1/15.9 | yes | FAIL: recorded SS setup -103.57 ps (closed at TT setup +155.40) |
| qkh_head_gather_stage | 64 | NEEDS RE-RUN | 269.98 (TT: 354.91) | 11.02 | 42.9/42.4 | yes | PASS |
| qkh_head_sstage | 64 | NEEDS RE-RUN | 211.84 (TT: 317.75) | 11.84 | 0.6/0.6 | yes | PASS |

### hbm (physical/die_plan/hbm/die_plan.json)

counts {'NEEDS RE-RUN': 55}; NEEDS RE-RUN whose last record already fails the standard on paper: 32; not-closed plan cores (not counted): 189

| module | inst | status | rec SS setup (closure corner: setup) | rec FF hold | rec spread TT/FF | kit in repo | paper |
|---|---|---|---|---|---|---|---|
| hfd_ep_static | 6 | NEEDS RE-RUN | -14.52 (TT: 217.23) | 8 | 53.4/49.3 | yes | FAIL: recorded SS setup -14.52 ps (closed at TT setup +217.23) |
| hfd_hgi_vm_calendar_f20 | 4 | NEEDS RE-RUN | -373.14 (TT: 25.04) | 12.63 | 25.3/21.8 | yes | FAIL: recorded SS setup -373.14 ps (closed at TT setup +25.04) |
| hfd_vms_bank_native_q0_faces | 32 | NEEDS RE-RUN | -266.26 (TT: 17.45) | 8.62 | 0.1/0 | yes | FAIL: recorded SS setup -266.26 ps (closed at TT setup +17.45) |
| hfd_vms_wq2_merge | 32 | NEEDS RE-RUN | 249.78 (TT: 335.22) | 21.14 | 19.5/20.4 | yes | PASS |
| ot_hbm_argmax_static_sw_vm_r2 | 1 | NEEDS RE-RUN | -261.08 (TT: 84.29) | 16.79 | 25.5/23.3 | yes | FAIL: recorded SS setup -261.08 ps (closed at TT setup +84.29) |
| ot_hbm_fault_leaf | 24 | NEEDS RE-RUN | 390.14 (TT: 434.46) | 29.75 | 0.8/0.5 | yes | PASS |
| ot_hbm_fault_leaf_n8_s0 | 4 | NEEDS RE-RUN | 387.26 (TT: 432.71) | 30.46 | 0.3/0.3 | yes | PASS |
| ot_hbm_host_cfg_leaf_nw | 4 | NEEDS RE-RUN | 317.73 (TT: 417.66) | 20.52 | 10.1/10.7 | yes | PASS |
| ot_hbm_host_cp_rxs | 1 | NEEDS RE-RUN | -379.24 (TT: 2.05) | 18.8 | 54/50.8 | yes | FAIL: recorded SS setup -379.24 ps (closed at TT setup +2.05) |
| ot_hbm_idx_qctl_static | 4 | NEEDS RE-RUN | 46.41 (TT: 227.91) | 22.75 | 14.8/14.7 | NO | PASS |
| ot_hbm_idx_query_static | 4 | NEEDS RE-RUN | -382.5 (TT: 12) | 14.52 | 79.6/75.3 | yes | FAIL: recorded SS setup -382.50 ps (closed at TT setup +12.00) |
| ot_hbm_idx_rootctl_static_am | 1 | NEEDS RE-RUN | -275.36 (TT: 23.17) | 20.15 | 76.3/63.7 | yes | FAIL: recorded SS setup -275.36 ps (closed at TT setup +23.17) |
| ot_hbm_idx_vm_query_static_n12 | 4 | NEEDS RE-RUN | -336.2 (TT: 23.35) | 13.64 | 49.4/45.7 | yes | FAIL: recorded SS setup -336.20 ps (closed at TT setup +23.35) |
| ot_hbm_idx_xq_node_static | 3 | NEEDS RE-RUN | 253.9 (TT: 362.14) | 9.92 | 31.3/30.1 | yes | PASS |
| ot_hbm_pc_refresh_cfg | 4 | NEEDS RE-RUN | -97.62 (TT: 125.96) | 24.03 | 6.1/6.4 | yes | FAIL: recorded SS setup -97.62 ps (closed at TT setup +125.96) |
| ot_hbm_sm_vm_wr_q_t_lanes4 | 4 | NEEDS RE-RUN | -202.86 (TT: 92.94) | 26.15 | 28.1/26.6 | yes | FAIL: recorded SS setup -202.86 ps (closed at TT setup +92.94) |
| ot_hbm_static_cfg_collar | 5 | NEEDS RE-RUN | -303.09 (TT: 50.96) | 22.05 | 22.6/22.4 | yes | FAIL: recorded SS setup -303.09 ps (closed at TT setup +50.96) |
| ot_hbm_static_cfg_collar_idx256r | 1 | NEEDS RE-RUN | -297.99 (TT: 40.72) | 27.12 | 36.2/33.3 | NO | FAIL: recorded SS setup -297.99 ps (closed at TT setup +40.72) |
| ot_hbm_status_join_fa | 1 | NEEDS RE-RUN | 289.75 (TT: 409.15) | 28.92 | 9.4/6.6 | yes | PASS |
| ot_hbm_su_bridge_release_s | 4 | NEEDS RE-RUN | -44.75 (TT: 7.34) | 30.52 | 11.9/7.6 | yes | FAIL: recorded SS setup -44.75 ps (closed at TT setup +7.34) |
| ot_hbm_su_programme_root_h5 | 1 | NEEDS RE-RUN | 276.16 (TT: 346.8) | 21.53 | 13.1/13.4 | yes | PASS |
| ot_hbm_su_static_cxport_dl_q | 16 | NEEDS RE-RUN | -41.45 (TT: 88.64) | 29.09 | 56.7/54.7 | yes | FAIL: recorded SS setup -41.45 ps (closed at TT setup +88.64) |
| ot_hbm_su_static_cxport_dl_s | 16 | NEEDS RE-RUN | 3.2 (TT: 204.45) | 29.5 | 17.1/16.9 | yes | PASS |
| ot_hbm_su_static_cxport_ij_q | 4 | NEEDS RE-RUN | -92.39 (TT: 67.13) | 26.92 | 39.6/37.4 | NO | FAIL: recorded SS setup -92.39 ps (closed at TT setup +67.13) |
| ot_hbm_su_static_cxport_ij_s | 4 | NEEDS RE-RUN | -158.57 (TT: 88.31) | 15.51 | 64.6/60.8 | yes | FAIL: recorded SS setup -158.57 ps (closed at TT setup +88.31) |
| ot_hbm_su_static_cxport_rc_q | 4 | NEEDS RE-RUN | -157.02 (TT: 28.42) | 27.54 | 26.3/23.9 | yes | FAIL: recorded SS setup -157.02 ps (closed at TT setup +28.42) |
| ot_hbm_su_static_cxport_rc_s | 4 | NEEDS RE-RUN | -237.63 (TT: 9.9) | 27.04 | 43.5/41.4 | yes | FAIL: recorded SS setup -237.63 ps (closed at TT setup +9.90) |
| ot_hbm_su_static_qcore_r13 | 4 | NEEDS RE-RUN | -291.7 (TT: 4.27) | 10.87 | 52.6/49.9 | yes | FAIL: recorded SS setup -291.70 ps (closed at TT setup +4.27) |
| ot_hbm_su_static_sfustore_hw | 4 | NEEDS RE-RUN | -80.61 (TT: 175.55) | 23.13 | 71.7/64.4 | yes | FAIL: recorded SS setup -80.61 ps (closed at TT setup +175.55) |
| ot_hbm_su_stree_leaf | 4 | NEEDS RE-RUN | 328.42 (TT: 391.8) | 27.45 | 7.3/7.3 | yes | PASS |
| ot_hbm_su_stree_root | 1 | NEEDS RE-RUN | 379.45 (TT: 426.1) | 19.37 | 12.5/13.4 | yes | PASS |
| ot_hbm_svc_pc_ctrl_leaf_cfg_h9b | 64 | NEEDS RE-RUN | -294.93 (TT: 29.75) | 13.65 | 117.5/117.7 | yes | FAIL: recorded TT pin-flop spread 117.5 ps > 80; recorded FF pin-flop spread 117.7 ps > 80; recorded SS setup -294.93 ps (closed at TT setup +29.75) |
| ot_hbm_svc_stack_fault | 4 | NEEDS RE-RUN | 256.22 (TT: 346.67) | 7.33 | 2.4/2.2 | yes | PASS |
| ot_hbm_svc_vmdel_lane_n | 32 | NEEDS RE-RUN | -229.87 (TT: 85.47) | 3.23 | 68.2/61.5 | yes | FAIL: recorded SS setup -229.87 ps (closed at TT setup +85.47) |
| ot_hbm_svc_wbw_copy | 4 | NEEDS RE-RUN | 378.02 (TT: 425.86) | 28.95 | 4.9/4.2 | yes | PASS |
| ot_hbm_xp_aq_tree13_fmt | 8 | NEEDS RE-RUN | -282.54 (TT: 65.07) | 15.27 | 17.7/16.9 | yes | FAIL: recorded SS setup -282.54 ps (closed at TT setup +65.07) |
| ot_hgi_coll_gq_land | 4 | NEEDS RE-RUN | -337.75 (TT: 11.98) | 16.83 | 69.9/66.1 | yes | FAIL: recorded SS setup -337.75 ps (closed at TT setup +11.98) |
| ot_hgi_coll_inj_copy | 4 | NEEDS RE-RUN | 196.28 (TT: 306.68) | 28.65 | 3/2.6 | yes | PASS |
| ot_hgi_coll_inj_idx_join_rg | 4 | NEEDS RE-RUN | -150.72 (TT: 134.13) | 5.27 | 47.6/43.9 | yes | FAIL: recorded SS setup -150.72 ps (closed at TT setup +134.13) |
| ot_hgi_coll_kq_share2_leaf | 16 | NEEDS RE-RUN | 52.19 (TT: 253.01) | 18.21 | 44.5/42.9 | yes | PASS |
| ot_hgi_coll_ring_b_stop | 4 | NEEDS RE-RUN | -39.78 (TT: 210.92) | 8.29 | 58.8/57.2 | yes | FAIL: recorded SS setup -39.78 ps (closed at TT setup +210.92) |
| ot_hgi_qdq_lg_port_group_r2 | 16 | NEEDS RE-RUN | 240.08 (TT: 329.97) | 19.9 | 17.4/17.5 | yes | PASS |
| ot_hgi_qdq_transport_ctl_r4 | 4 | NEEDS RE-RUN | 58.32 (TT: 269.77) | 12.01 | 28.6/22.8 | yes | PASS |
| ot_hgi_qdq_transport_rslice | 16 | NEEDS RE-RUN | 54.89 (TT: 287.66) | 6.28 | 84.7/80.8 | yes | FAIL: recorded TT pin-flop spread 84.7 ps > 80; recorded FF pin-flop spread 80.8 ps > 80 |
| ot_hgi_qdq_transport_wslice | 16 | NEEDS RE-RUN | 196.37 (TT: 314.49) | 23.98 | 37.4/37.1 | yes | PASS |
| ot_hgi_qw_dec | 4 | NEEDS RE-RUN | -305.88 (TT: 50.84) | 18.4 | -/- | NO | FAIL: recorded SS setup -305.88 ps (closed at TT setup +50.84); no recorded pin-flop spread (insertion.json missing) |
| ot_hgi_sfu_lg_pair_tap_leaf | 16 | NEEDS RE-RUN | 121.58 (TT: 306.16) | 5.09 | 53.6/51 | yes | PASS |
| ot_hgi_sfu_lg_pair_tap_leaf_term | 16 | NEEDS RE-RUN | 306.56 (TT: 378.05) | 8.54 | 48.5/46.1 | yes | PASS |
| ot_hgi_sm_xload_cl2_bdring | 8 | NEEDS RE-RUN | -242.93 (TT: 48.29) | 22.86 | 25.4/24.2 | yes | FAIL: recorded SS setup -242.93 ps (closed at TT setup +48.29) |
| ot_hgi_sm_xload_cl2_bfqg | 32 | NEEDS RE-RUN | -176.82 (TT: 115.25) | 11.69 | -/- | yes | FAIL: recorded SS setup -176.82 ps (closed at TT setup +115.25); no recorded pin-flop spread (insertion.json missing) |
| ot_hgi_sm_xload_cl2_ctlx | 4 | NEEDS RE-RUN | -317.43 (TT: 8.26) | 5.9 | 79.8/74.6 | yes | FAIL: recorded SS setup -317.43 ps (closed at TT setup +8.26) |
| ot_hgi_sm_xload_xq_pegress | 8 | NEEDS RE-RUN | -203.74 (TT: 82.21) | 12.05 | 32.9/31.4 | yes | FAIL: recorded SS setup -203.74 ps (closed at TT setup +82.21) |
| ot_pdie_ucie_col | 1 | NEEDS RE-RUN | 49.67 (TT: 229.17) | 10.65 | 14.4/13.7 | yes | PASS |
| ot_static_run_target | 16 | NEEDS RE-RUN | 3.46 (TT: 262.51) | 27.37 | 15/15.5 | NO | PASS |
| ot_vms_status4_static | 1 | NEEDS RE-RUN | 131.02 (TT: 344.22) | 29.09 | 2.6/2.7 | yes | PASS |

### s81_head (physical/die_plan/s81_head/die_plan.json)

counts {'NEEDS RE-RUN': 3}; NEEDS RE-RUN whose last record already fails the standard on paper: 1; not-closed plan cores (not counted): 1

| module | inst | status | rec SS setup (closure corner: setup) | rec FF hold | rec spread TT/FF | kit in repo | paper |
|---|---|---|---|---|---|---|---|
| ot_dsrom_head_elem | 1320 | NEEDS RE-RUN | 133.67 (-: 133.67) | 10.81 | -/- | NO | INCOMPLETE: no recorded pin-flop spread (insertion.json missing) |
| ot_s81hd_spo | 6 | NEEDS RE-RUN | -70.45 (TT: 19.69) | 40.87 | 78/72.9 | yes | FAIL: recorded SS setup -70.45 ps (closed at TT setup +19.69) |
| ot_s81hd_spr | 6 | NEEDS RE-RUN | 223.93 (TT: 373.03) | 32.35 | 48.3/44.9 | yes | PASS |

### hbm_b2r2 (origin/claude/hbm-arch-1024@3277b5e78b:physical/die_plan/hbm_arch/B2r2/die_plan.json)

counts {'NEEDS RE-RUN': 51}; NEEDS RE-RUN whose last record already fails the standard on paper: 31; not-closed plan cores (not counted): 192

| module | inst | status | rec SS setup (closure corner: setup) | rec FF hold | rec spread TT/FF | kit in repo | paper |
|---|---|---|---|---|---|---|---|
| hfd_ep_static | 6 | NEEDS RE-RUN | -14.52 (TT: 217.23) | 8 | 53.4/49.3 | yes | FAIL: recorded SS setup -14.52 ps (closed at TT setup +217.23) |
| hfd_hgi_vm_calendar_f20 | 2 | NEEDS RE-RUN | -373.14 (TT: 25.04) | 12.63 | 25.3/21.8 | yes | FAIL: recorded SS setup -373.14 ps (closed at TT setup +25.04) |
| hfd_vms_bank_native_q0_faces | 16 | NEEDS RE-RUN | -266.26 (TT: 17.45) | 8.62 | 0.1/0 | yes | FAIL: recorded SS setup -266.26 ps (closed at TT setup +17.45) |
| hfd_vms_wq2_merge | 16 | NEEDS RE-RUN | 249.78 (TT: 335.22) | 21.14 | 19.5/20.4 | yes | PASS |
| ot_hbm_argmax_static_sw_vm_r2 | 1 | NEEDS RE-RUN | -261.08 (TT: 84.29) | 16.79 | 25.5/23.3 | yes | FAIL: recorded SS setup -261.08 ps (closed at TT setup +84.29) |
| ot_hbm_fault_leaf_n8_s0 | 2 | NEEDS RE-RUN | 387.26 (TT: 432.71) | 30.46 | 0.3/0.3 | yes | PASS |
| ot_hbm_host_cfg_leaf_nw | 2 | NEEDS RE-RUN | 317.73 (TT: 417.66) | 20.52 | 10.1/10.7 | yes | PASS |
| ot_hbm_host_cp_rxs | 1 | NEEDS RE-RUN | -379.24 (TT: 2.05) | 18.8 | 54/50.8 | yes | FAIL: recorded SS setup -379.24 ps (closed at TT setup +2.05) |
| ot_hbm_idx_qctl_static | 2 | NEEDS RE-RUN | 46.41 (TT: 227.91) | 22.75 | 14.8/14.7 | NO | PASS |
| ot_hbm_idx_query_static | 2 | NEEDS RE-RUN | -382.5 (TT: 12) | 14.52 | 79.6/75.3 | yes | FAIL: recorded SS setup -382.50 ps (closed at TT setup +12.00) |
| ot_hbm_idx_rootctl_static_am | 1 | NEEDS RE-RUN | -275.36 (TT: 23.17) | 20.15 | 76.3/63.7 | yes | FAIL: recorded SS setup -275.36 ps (closed at TT setup +23.17) |
| ot_hbm_idx_vm_query_static_n12 | 2 | NEEDS RE-RUN | -336.2 (TT: 23.35) | 13.64 | 49.4/45.7 | yes | FAIL: recorded SS setup -336.20 ps (closed at TT setup +23.35) |
| ot_hbm_pc_refresh_cfg | 2 | NEEDS RE-RUN | -97.62 (TT: 125.96) | 24.03 | 6.1/6.4 | yes | FAIL: recorded SS setup -97.62 ps (closed at TT setup +125.96) |
| ot_hbm_sm_vm_wr_q_t_lanes4 | 2 | NEEDS RE-RUN | -202.86 (TT: 92.94) | 26.15 | 28.1/26.6 | yes | FAIL: recorded SS setup -202.86 ps (closed at TT setup +92.94) |
| ot_hbm_static_cfg_collar_idx256r | 1 | NEEDS RE-RUN | -297.99 (TT: 40.72) | 27.12 | 36.2/33.3 | NO | FAIL: recorded SS setup -297.99 ps (closed at TT setup +40.72) |
| ot_hbm_status_join_fa | 1 | NEEDS RE-RUN | 289.75 (TT: 409.15) | 28.92 | 9.4/6.6 | yes | PASS |
| ot_hbm_su_bridge_release_s | 2 | NEEDS RE-RUN | -44.75 (TT: 7.34) | 30.52 | 11.9/7.6 | yes | FAIL: recorded SS setup -44.75 ps (closed at TT setup +7.34) |
| ot_hbm_su_programme_root_h5 | 1 | NEEDS RE-RUN | 276.16 (TT: 346.8) | 21.53 | 13.1/13.4 | yes | PASS |
| ot_hbm_su_static_cxport_dl_q | 8 | NEEDS RE-RUN | -41.45 (TT: 88.64) | 29.09 | 56.7/54.7 | yes | FAIL: recorded SS setup -41.45 ps (closed at TT setup +88.64) |
| ot_hbm_su_static_cxport_ij_q | 2 | NEEDS RE-RUN | -92.39 (TT: 67.13) | 26.92 | 39.6/37.4 | NO | FAIL: recorded SS setup -92.39 ps (closed at TT setup +67.13) |
| ot_hbm_su_static_cxport_rc_q | 2 | NEEDS RE-RUN | -157.02 (TT: 28.42) | 27.54 | 26.3/23.9 | yes | FAIL: recorded SS setup -157.02 ps (closed at TT setup +28.42) |
| ot_hbm_su_static_cxport_rc_s | 2 | NEEDS RE-RUN | -237.63 (TT: 9.9) | 27.04 | 43.5/41.4 | yes | FAIL: recorded SS setup -237.63 ps (closed at TT setup +9.90) |
| ot_hbm_su_static_qcore_r13 | 2 | NEEDS RE-RUN | -291.7 (TT: 4.27) | 10.87 | 52.6/49.9 | yes | FAIL: recorded SS setup -291.70 ps (closed at TT setup +4.27) |
| ot_hbm_su_static_sfustore_hw | 2 | NEEDS RE-RUN | -80.61 (TT: 175.55) | 23.13 | 71.7/64.4 | yes | FAIL: recorded SS setup -80.61 ps (closed at TT setup +175.55) |
| ot_hbm_su_stree_leaf | 2 | NEEDS RE-RUN | 328.42 (TT: 391.8) | 27.45 | 7.3/7.3 | yes | PASS |
| ot_hbm_su_stree_root | 1 | NEEDS RE-RUN | 379.45 (TT: 426.1) | 19.37 | 12.5/13.4 | yes | PASS |
| ot_hbm_svc_pc_ctrl_leaf_cfg_h9b | 32 | NEEDS RE-RUN | -294.93 (TT: 29.75) | 13.65 | 117.5/117.7 | yes | FAIL: recorded TT pin-flop spread 117.5 ps > 80; recorded FF pin-flop spread 117.7 ps > 80; recorded SS setup -294.93 ps (closed at TT setup +29.75) |
| ot_hbm_svc_stack_fault | 2 | NEEDS RE-RUN | 256.22 (TT: 346.67) | 7.33 | 2.4/2.2 | yes | PASS |
| ot_hbm_svc_vmdel_lane_n | 16 | NEEDS RE-RUN | -229.87 (TT: 85.47) | 3.23 | 68.2/61.5 | yes | FAIL: recorded SS setup -229.87 ps (closed at TT setup +85.47) |
| ot_hbm_svc_wbw_copy | 2 | NEEDS RE-RUN | 378.02 (TT: 425.86) | 28.95 | 4.9/4.2 | yes | PASS |
| ot_hbm_xp_aq_tree13_fmt | 4 | NEEDS RE-RUN | -282.54 (TT: 65.07) | 15.27 | 17.7/16.9 | yes | FAIL: recorded SS setup -282.54 ps (closed at TT setup +65.07) |
| ot_hgi_coll_gq_land | 2 | NEEDS RE-RUN | -337.75 (TT: 11.98) | 16.83 | 69.9/66.1 | yes | FAIL: recorded SS setup -337.75 ps (closed at TT setup +11.98) |
| ot_hgi_coll_inj_copy | 2 | NEEDS RE-RUN | 196.28 (TT: 306.68) | 28.65 | 3/2.6 | yes | PASS |
| ot_hgi_coll_inj_idx_join_rg | 2 | NEEDS RE-RUN | -150.72 (TT: 134.13) | 5.27 | 47.6/43.9 | yes | FAIL: recorded SS setup -150.72 ps (closed at TT setup +134.13) |
| ot_hgi_coll_kq_share2_leaf | 8 | NEEDS RE-RUN | 52.19 (TT: 253.01) | 18.21 | 44.5/42.9 | yes | PASS |
| ot_hgi_coll_ring_b_stop | 2 | NEEDS RE-RUN | -39.78 (TT: 210.92) | 8.29 | 58.8/57.2 | yes | FAIL: recorded SS setup -39.78 ps (closed at TT setup +210.92) |
| ot_hgi_qdq_lg_port_group_r2 | 8 | NEEDS RE-RUN | 240.08 (TT: 329.97) | 19.9 | 17.4/17.5 | yes | PASS |
| ot_hgi_qdq_nw_program_leaf | 2 | NEEDS RE-RUN | -265.85 (TT: 42.22) | 12.45 | 42.3/26.6 | yes | FAIL: recorded SS setup -265.85 ps (closed at TT setup +42.22) |
| ot_hgi_qdq_transport_ctl_r4 | 2 | NEEDS RE-RUN | 58.32 (TT: 269.77) | 12.01 | 28.6/22.8 | yes | PASS |
| ot_hgi_qdq_transport_rslice | 8 | NEEDS RE-RUN | 54.89 (TT: 287.66) | 6.28 | 84.7/80.8 | yes | FAIL: recorded TT pin-flop spread 84.7 ps > 80; recorded FF pin-flop spread 80.8 ps > 80 |
| ot_hgi_qdq_transport_wslice | 8 | NEEDS RE-RUN | 196.37 (TT: 314.49) | 23.98 | 37.4/37.1 | yes | PASS |
| ot_hgi_qw_dec | 2 | NEEDS RE-RUN | -305.88 (TT: 50.84) | 18.4 | -/- | NO | FAIL: recorded SS setup -305.88 ps (closed at TT setup +50.84); no recorded pin-flop spread (insertion.json missing) |
| ot_hgi_sfu_lg_pair_tap_leaf | 8 | NEEDS RE-RUN | 121.58 (TT: 306.16) | 5.09 | 53.6/51 | yes | PASS |
| ot_hgi_sfu_lg_pair_tap_leaf_term | 8 | NEEDS RE-RUN | 306.56 (TT: 378.05) | 8.54 | 48.5/46.1 | yes | PASS |
| ot_hgi_sm_xload_cl2_bdring | 4 | NEEDS RE-RUN | -242.93 (TT: 48.29) | 22.86 | 25.4/24.2 | yes | FAIL: recorded SS setup -242.93 ps (closed at TT setup +48.29) |
| ot_hgi_sm_xload_cl2_bfqg | 16 | NEEDS RE-RUN | -176.82 (TT: 115.25) | 11.69 | -/- | yes | FAIL: recorded SS setup -176.82 ps (closed at TT setup +115.25); no recorded pin-flop spread (insertion.json missing) |
| ot_hgi_sm_xload_cl2_ctlx | 2 | NEEDS RE-RUN | -317.43 (TT: 8.26) | 5.9 | 79.8/74.6 | yes | FAIL: recorded SS setup -317.43 ps (closed at TT setup +8.26) |
| ot_hgi_sm_xload_xq_pegress | 4 | NEEDS RE-RUN | -203.74 (TT: 82.21) | 12.05 | 32.9/31.4 | yes | FAIL: recorded SS setup -203.74 ps (closed at TT setup +82.21) |
| ot_pdie_ucie_col | 1 | NEEDS RE-RUN | 49.67 (TT: 229.17) | 10.65 | 14.4/13.7 | yes | PASS |
| ot_static_run_target | 8 | NEEDS RE-RUN | 3.46 (TT: 262.51) | 27.37 | 15/15.5 | NO | PASS |
| ot_vms_status4_static | 1 | NEEDS RE-RUN | 131.02 (TT: 344.22) | 29.09 | 2.6/2.7 | yes | PASS |
