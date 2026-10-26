# Pin-register audit: qwen_rom_tp8 (contract v3, c23342b9f)

> **TILE VERDICTS SUPERSEDED (10-13 09:10, el1013-pinreg-audit.log):** `out_over` / `in_over` here judge each side against 0.2 T = 166.7 ps, which is the share the sign-off SDC gives the OUTSIDE, not the tile. The die statement is the pair equation with insertion-compensated clock entry: see `qwen_rom_tp8_compensated.md`, `s81_compensated.md`, `ranked_compensated.md`. The hop tables (> 500 um) and the min-delay / combinational columns stand.

Rule: clock->pin and pin->flop each <= 166.7 ps (0.2 T), hop <= 500 um, L - H >= 100 ps (50 + skew 50).

**PROVISIONAL: 13 of 13 audited views were exported before the export-SDC fix (abc334b14); their boundary numbers may be off by tens of ps**

Cells 44: audited 13 (1004 instances), violating 13 {'out_over': 10, 'in_over': 7, 'min_delay': 5}, not auditable 31 (1065 instances), alias-bound 8.

| # | cell | inst | corner | flags | comb bits | out > B bits | worst out ps (bus) | in > B bits | worst in ps (bus) | L min | H max | L-H | binding |
|---|---|---:|---|---|---:|---:|---|---:|---|---:|---:|---:|---|
| 1 | qkd_ectl | 32 | tt | out_over in_over | 0 | 2276 | 427.2 (req_t) | 455 | 427.3 (exp_done) | 77.0 | -56.1 | 133.1 | ALIAS (same-family master, candidate only) |
| 2 | qfd_io_serdes | 3 | tt | out_over in_over | 0 | 1012 | 408.3 (tx_flit) | 2071 | 346.4 (r_cr) | 60.8 | -100.5 | 161.3 | bind map |
| 3 | qfd_su_cbuf_g | 8 | tt | out_over in_over | 0 | 717 | 221.9 (f_addr) | 502 | 380.7 (grp) | 110.8 | -63.8 | 174.6 | bind map |
| 4 | qkd_kvwq_ctl_bin | 4 | tt | out_over | 0 | 141 | 318.8 (fault) | 0 | 139.5 (kvw_t) | 87.3 | -41.2 | 128.5 | ALIAS (same-family master, candidate only) |
| 5 | qfd_tt_up4 | 1 | tt | out_over in_over | 0 | 298 | 189.9 (tt_ty) | 2 | 311.6 (rst_n) | 106.5 | -31.1 | 137.6 | ALIAS (same-family master, candidate only) |
| 6 | qfd_tt_up4_g | 3 | tt | out_over in_over | 0 | 298 | 189.9 (tt_ty) | 2 | 311.6 (rst_n) | 106.5 | -31.1 | 137.6 | ALIAS (same-family master, candidate only) |
| 7 | qfd_crom_g | 8 | tt | out_over in_over | 0 | 152 | 212.1 (crom_q) | 206 | 242.2 (crom_re) | 95.2 | -105.7 | 200.9 | bind map |
| 8 | qfd_chead_e | 24 | tt | out_over min_delay | 0 | 2 | 180.4 (c_d) | 0 | 101.3 (a_d) | 79.7 | -6.7 | 86.4 | ALIAS (same-family master, candidate only) |
| 9 | qfd_chead_w | 24 | tt | out_over min_delay | 0 | 2 | 180.4 (c_d) | 0 | 101.3 (a_d) | 79.7 | -6.7 | 86.4 | ALIAS (same-family master, candidate only) |
| 10 | qkd_kvwq_leaf_s_w129_m | 128 | tt | out_over in_over | 0 | 49 | 176.8 (w_data) | 1 | 177.1 (dn_bad) | 97.0 | -28.5 | 125.5 | cell / view name |
| 11 | ot_qfd_serdes_112g_x12_phy | 1 | tt | min_delay | 0 | 0 | 117.3 (tx_up) | 0 | 143.5 (tx_v) | 90.5 | 58.6 | 31.9 | cell / view name |
| 12 | qfd_cst_n | 384 | tt | min_delay | 0 | 0 | 151.5 (t_d) | 0 | 95.4 (a_d) | 72.2 | -13.3 | 85.5 | ALIAS (same-family master, candidate only) |
| 13 | qfd_cst_s | 384 | tt | min_delay | 0 | 0 | 151.5 (t_d) | 0 | 95.4 (a_d) | 72.2 | -13.3 | 85.5 | ALIAS (same-family master, candidate only) |

Not auditable (no closed view): ot_hbm3e_phy x4, qfd_clkrx x1, qfd_io_collective x1, qfd_io_ucie x1, qfd_io_xfifo x1, qfd_port_tiles_0 x1, qfd_port_tiles_0_f1 x1, qfd_port_tiles_1 x1, qfd_port_tiles_1_f1 x1, qfd_port_tiles_2 x1, qfd_port_tiles_2_f1 x1, qfd_seq_su x1, qfd_sp_band_lanes x3, qfd_sp_res_ser x3, qfd_sp_su64_sfu x1, qfd_sp_vector_memory x1, qfd_tile_nk x768, qfd_tt_ctlm x1, qkd_ahub x1, qkd_astk x2, qkd_astk_n x2, qkd_cdc_wleaf x128, qkd_ctrl x2, qkd_ctrl_n x2, qkd_embgw x1, qkd_host x1, qkd_land x2, qkd_land_n x2, qkd_pll x1, qkd_rhead x128, qkd_seq x1

## Hops over 500 um: 278 (55363 bits; 265 data, 13 unrelayed reset nets), max 31115.7 um

Source: case tp8b case regenerated from main (tools/qwen_rom_fulldie_b3r2.py pdn --recipe tp8b --pdn-rev r5) c23342b9f --recipe tp8b --pdn-rev r5; 12180 instances, 14995 data hops; contract slots placed as the contract 2069 / 2069.

| class | hops | bits | max um | masters |
|---|---:|---:|---:|---|
| n_rst_core_WS | 1 | 1 | 31115.7 | qkd_astk, qkd_ctrl, qkd_ectl, qkd_kvwq_ctl_bin, qkd_kvwq_leaf_s_w129_m, qkd_land |
| n_rst_core_WN | 1 | 1 | 28720.3 | qkd_astk_n, qkd_ctrl_n, qkd_ectl, qkd_kvwq_ctl_bin, qkd_kvwq_leaf_s_w129_m, qkd_land_n |
| n_rst_core_ES | 1 | 1 | 26938.4 | qkd_astk, qkd_ctrl, qkd_ectl, qkd_kvwq_ctl_bin, qkd_kvwq_leaf_s_w129_m, qkd_land |
| n_rst_core_EN | 1 | 1 | 24546.2 | qkd_astk_n, qkd_ctrl_n, qkd_ectl, qkd_kvwq_ctl_bin, qkd_kvwq_leaf_s_w129_m, qkd_land_n |
| n_rst_core_c | 1 | 1 | 20629.2 | ot_qfd_serdes_112g_x12_phy, qkd_ahub, qkd_embgw, qkd_host, qkd_pll, qkd_seq |
| n_rst_kv_WN | 1 | 1 | 12364.5 | qkd_cdc_wleaf, qkd_land_n |
| n_rst_kv_WS | 1 | 1 | 12364.5 | qkd_cdc_wleaf, qkd_land |
| n_rst_kv_EN | 1 | 1 | 12364.4 | qkd_cdc_wleaf, qkd_land_n |
| n_rst_kv_ES | 1 | 1 | 12364.4 | qkd_cdc_wleaf, qkd_land |
| n_rst_hbm_WN | 1 | 1 | 12064.3 | ot_hbm3e_phy, qkd_cdc_wleaf, qkd_ctrl_n |
| n_rst_hbm_WS | 1 | 1 | 12064.3 | ot_hbm3e_phy, qkd_cdc_wleaf, qkd_ctrl |
| n_rst_hbm_EN | 1 | 1 | 12064.1 | ot_hbm3e_phy, qkd_cdc_wleaf, qkd_ctrl_n |
| n_rst_hbm_ES | 1 | 1 | 12064.1 | ot_hbm3e_phy, qkd_cdc_wleaf, qkd_ctrl |
| n_am_WN__r# | 5 | 180 | 2382.3 | qfd_rly_36_ES_53x30, qfd_rly_36_EW_53x30, qfd_rly_36_WS_53x30 |
| n_ap_WS__r# | 6 | 3378 | 1980.5 | qfd_rly_563_EN_53x60, qfd_rly_563_SE_53x60, qfd_rly_563_SN_53x60, qfd_rly_563_SW_53x60, qfd_rly_563_WN_53x60, qfd_rly_563_WS_53x60 |
| n_af_EN__r# | 3 | 3 | 1973.6 | qfd_rly_1_ES_53x30, qfd_rly_1_EW_53x30, qfd_rly_1_NE_53x30, qfd_rly_1_NW_53x30, qfd_rly_1_WS_53x30 |
| n_aq_WS__r# | 2 | 1080 | 1812.5 | qfd_rly_540_NS_53x60, qfd_rly_540_NW_53x60, qfd_rly_540_WS_53x60 |
| n_aq_EN__r# | 6 | 3240 | 1779.6 | qfd_rly_540_EN_53x60, qfd_rly_540_SE_53x60, qfd_rly_540_SN_53x60, qfd_rly_540_SW_53x60, qfd_rly_540_WN_53x60 |
| n_am_WS__r# | 6 | 216 | 1728.2 | qfd_rly_36_EN_53x30, qfd_rly_36_SE_53x30, qfd_rly_36_SN_53x30, qfd_rly_36_SW_53x30 |
| n_af_WS__r# | 4 | 4 | 1687.2 | qfd_rly_1_NE_53x30, qfd_rly_1_NS_53x30, qfd_rly_1_SN_53x30, qfd_rly_1_WE_53x30, qfd_rly_1_WN_53x30, qfd_rly_1_WS_53x30 |
| n_ap_WN__r# | 13 | 7319 | 1609.0 | qfd_rly_563_EN_53x60, qfd_rly_563_SE_53x60, qfd_rly_563_SN_53x60, qfd_rly_563_SW_53x60, qfd_rly_563_WE_53x60, qfd_rly_563_WN_53x60 |
| n_mf_EN__r# | 1 | 1 | 1586.9 | qfd_rly_1_ES_53x30, qfd_rly_1_WN_53x30 |
| n_am_EN__r# | 4 | 144 | 1583.5 | qfd_rly_36_ES_53x30, qfd_rly_36_NE_53x30, qfd_rly_36_NS_53x30, qfd_rly_36_WE_53x30, qfd_rly_36_WS_53x30 |
| n_af_ES__r# | 2 | 2 | 1574.9 | qfd_rly_1_NS_53x30, qfd_rly_1_WS_53x30 |
| n_emr_ES__r# | 3 | 1590 | 1439.0 | qfd_rly_530_ES_53x60, qfd_rly_530_EW_53x60, qfd_rly_530_NE_53x60, qfd_rly_530_NS_53x60, qfd_rly_530_SN_53x60, qfd_rly_530_SW_53x60 |
| n_kc_WN__r# | 2 | 66 | 1028.4 | qfd_rly_33_EW_53x30, qfd_rly_33_SE_53x30, qfd_rly_33_SN_53x30, qfd_rly_33_WN_53x30 |
| n_kc_EN__r# | 1 | 33 | 1028.4 | qfd_rly_33_SN_53x30, qfd_rly_33_SW_53x30 |
| n_mf_WS__r# | 3 | 3 | 1012.8 | qfd_rly_1_ES_53x30, qfd_rly_1_SE_53x30, qfd_rly_1_WE_53x30, qfd_rly_1_WN_53x30 |
| n_emr_EN__r# | 3 | 1590 | 990.0 | qfd_rly_530_EW_53x60, qfd_rly_530_NS_53x60, qfd_rly_530_SE_53x60, qfd_rly_530_WS_53x60 |
| n_emr_WN__r# | 5 | 2650 | 943.7 | qfd_rly_530_EN_53x60, qfd_rly_530_SE_53x60, qfd_rly_530_WE_53x60, qfd_rly_530_WN_53x60 |
| n_ing_WS__r# | 1 | 530 | 881.3 | qfd_rly_530_EW_53x60, qfd_rly_530_WN_53x60 |
| n_bword_#__r# | 2 | 1024 | 848.9 | qfd_port_tiles_1_f1, qfd_rly_512_EW_53x30, qfd_rly_512_NW_53x30, qfd_rly_512_SW_53x30 |
| n_emf_WS__r# | 2 | 1060 | 846.7 | qfd_rly_530_EW_53x60, qfd_rly_530_WN_53x60 |
| n_ap_EN__r# | 6 | 3378 | 796.8 | qfd_rly_563_EN_53x60, qfd_rly_563_ES_53x60, qfd_rly_563_EW_53x60, qfd_rly_563_NW_53x60, qfd_rly_563_SE_53x60, qfd_rly_563_SN_53x60 |
| n_emf_EN__r# | 2 | 1060 | 788.2 | qfd_rly_530_EN_53x60, qfd_rly_530_NE_53x60, qfd_rly_530_SN_53x60, qfd_rly_530_WE_53x60 |
| n_gq__r# | 1 | 530 | 753.2 | qfd_rly_530_ES_53x60, qfd_rly_530_SW_53x60 |
| n_gq | 1 | 530 | 746.9 | qfd_rly_530_SW_53x60, qkd_seq |
| n_krs_WS_#__r# | 6 | 6150 | 703.5 | qkd_rly_1025 |
| n_krs_WN_#__r# | 6 | 6150 | 703.5 | qkd_rly_1025 |
| n_krq_ES_#__r# | 4 | 64 | 703.5 | qkd_land, qkd_rly_16 |
