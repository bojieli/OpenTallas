# Native pin audit of CLOSED views (TT launch O-R <= 220 ps, capture S+R <= 190 ps)

Source a0f21ea968ec; tool tools/hier_contract/native_pin_audit.py; 928 views found, 925 kept (closed or store), dropped (loop job not CLOSED): {'NEEDS_RTL': 2, 'NEEDS_HUMAN': 1}.

Contracts / censuses for 'used': results/arch/hier_contract_1012/qwen_rom_tp8.json v4; results/arch/hier_contract_1011/qwen_kv.json v5; results/physical/die_real_census/qwen_rom_tp8_v4.json v4; results/arch/hier_contract_1011/s81.json v17; results/physical/die_iter_1012/s81/real_view_census_v16_20261013/ds_rom_s81_layer1_v16.json v16; results/arch/hier_contract_1011/r25gq.json v12; results/physical/die_real_census/hbm_r25gqn_v12.json v12

| design | views | pass | fail | used yes (fail) | cell only (fail) | not used (fail) | launch fail | capture fail | comb | no insertion.json |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen | 241 | 56 | 185 | 7 (3) | 3 (1) | 231 (181) | 114 | 139 | 3 | 106 |
| s81 | 345 | 104 | 241 | 29 (21) | 17 (17) | 299 (203) | 196 | 188 | 1 | 134 |
| hbm | 274 | 103 | 171 | 12 (8) | 11 (8) | 251 (155) | 122 | 133 | 0 | 149 |
| other | 65 | 14 | 51 | 0 (0) | 0 (0) | 65 (51) | 44 | 21 | 8 | 0 |

## qwen

| view | cell | closed by | worst launch ps (pin) | worst capture ps (pin) | comb | R src | pass | used |
|---|---|---|---:|---:|---:|---|---|---|
| physical/ref_tile/qkd_cdc_wleaf_ref/views/qkd_cdc_wleaf | qkd_cdc_wleaf | loop | 382.8 (l_data[150]) | 453.7 (h_hand) | 0 | ins | FAIL | yes |
| physical/ref_tile/qkd_kvwq_leaf_s_w129_m/views/qkd_kvwq_leaf_s_w129_m | qkd_kvwq_leaf_s_w129_m | loop | 231.1 (w[55]) | 365.5 (lane[0]) | 0 | ins | FAIL | yes |
| physical/ref_tile/qkd_kvwq_ctl_bin/views/qkd_kvwq_ctl_bin | qkd_kvwq_ctl_bin | loop | 230.1 (durable[22]) | 392.1 (rst_n) | 0 | ins | FAIL | yes |
| physical/ref_tile/qkd_embgw/views/qkd_embgw | qkd_embgw | loop | 312.0 (t_eq[473]) | 178.8 (emr_WN[482]) | 0 | ins | FAIL | cell |
| physical/qwen_die_masters/views/qfd_emb_pcport_kvw_a | qfd_emb_pcport | loop | 528.0 (wd[96]) | 559.6 (w_d[163]) | 288 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_emb_pcport | qfd_emb_pcport | loop | 526.8 (wd[30]) | 503.7 (w_d[10]) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_emb_pcport_kvw | qfd_emb_pcport | loop | 523.3 (wd[23]) | 515.7 (w_d[166]) | 288 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_emb_pc_00 | qfd_emb_pc_00 | loop | 509.4 (wd[243]) | 601.3 (r_d[0]) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qkd_ectl_b | qkd_ectl_b | loop | 417.9 (req_t[2]) | 436.6 (exp_done[8]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_io_serdes_rxd512 | qfd_io_serdes_rxd512 | loop | 415.6 (tx_flit[804]) | 339.1 (r_cr) | 0 | lib est | FAIL | no |
| physical/ref_tile/qkd_ectl_c/views/qkd_ectl_c | qkd_ectl_c | loop | 410.3 (x_o[12]) | 333.4 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/qkd_ctrl_pc/views/qkd_ctrl_pc | qkd_ctrl_pc | loop | 402.4 (po[33]) | 163.0 (es[251]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_d2d_rom_b | qfd_d2d_rom_b | loop | 399.4 (fault_cause[5]) | 451.9 (rx_flit[436]) | 0 | lib est | FAIL | no |
| physical/ref_tile/qkd_host_prompt_capture_bal/views/qkd_host_prompt_capture_pins | qkd_host_prompt_capture_pins | loop | 397.3 (q[11]) | 255.6 (rst_n) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_dspark_s7_control | qfd_dspark_s7_control | loop | 388.6 (cmd_token[6]) | 656.9 (done_id[49]) | 1 | lib est | FAIL | no |
| physical/ref_tile/qkd_ectl_a/views/qkd_ectl_a | qkd_ectl_a | loop | 388.6 (rvm_o) | 384.7 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_emb_pcport_m5/views/ot_qfd_emb_pcport | ot_qfd_emb_pcport | loop | 387.1 (wd[23]) | 478.6 (w_d[45]) | 0 | ins | FAIL | no |
| physical/ref_tile/qkd_ectl_b/views/qkd_ectl_b | qkd_ectl_b | loop | 384.4 (x_o[5]) | 381.4 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/qkd_astk_ex/views/qkd_astk_ex | qkd_astk_ex | loop | 371.6 (uo[78]) | 176.1 (pi[16]) | 0 | ins | FAIL | no |
| physical/ref_tile/qkd_ke_rq_ref/views/ot_qkvd_ke_rq | ot_qkvd_ke_rq | loop | 367.6 (rqv) | 257.2 (rx_flit[547]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_tt_ctlm_head/views/qfd_tt_ctlm_head | qfd_tt_ctlm_head | loop | 356.6 (cmd[112]) | 287.4 (ret[75]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_vm_bank_t/views/ot_qfd_vm_bank_t | ot_qfd_vm_bank_t | loop | 351.0 (q[286]) | 284.1 (wd[491]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_sysctl_stn_pb2_cl | qfd_sysctl_stn_pb2_cl | loop | 345.5 (fault_src[17]) | 514.4 (por_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/qdq_wr_pay_ref/views/ot_hgi_qdq_wr_pay | ot_hgi_qdq_wr_pay | loop | 343.2 (wwq[441]) | 187.3 (y[481]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_su_cbuf_native_l0/views/qfd_su_cbuf_native_l0 | qfd_su_cbuf_native_l0 | loop | 342.6 (f_addr[8]) | 277.9 (f_q[75]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_dspark_argmax_gather | qfd_dspark_argmax_gather | loop | 340.3 (o_id[10]) | 580.2 (i_id[170]) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_io_emb_root | qfd_io_emb_root | loop | 339.7 (eq_data[439]) | 447.4 (r_v[5]) | 0 | lib est | FAIL | no |
| physical/ref_tile/qkd_land_grp/views/qkd_land_grp | qkd_land_grp | loop | 339.4 (rs[878]) | 173.5 (kn[1027]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_sp_constants_sequencer_sys | qfd_sp_constants_sequencer_sys | loop | 337.2 (me_clk_en[0]) | 184.1 (vm_rq[509]) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_slab_pg_col/views/ot_qwen_slab_pg_col | ot_qwen_slab_pg_col | loop | 329.9 (m5[121]) | 196.7 (cid[0]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qkd_kvwq_ctl_bin_a | qkd_kvwq_ctl_bin_a | loop | 326.1 (fault) | 149.9 (kvw_d[37]) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/ot_nhb_pbst | ot_nhb_pbst | loop | 323.2 (sr[192]) | 202.1 (pdata[105]) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_res_slot_rs/views/ot_qfd_res_slot_tile | ot_qfd_res_slot_tile | loop | 321.8 (rqf_ptr[4]) | 369.0 (rst_n) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qkd_kvwq_ctl_bin_h | qkd_kvwq_ctl_bin_h | loop | 318.8 (fault) | 139.5 (kvw_t[3]) | 0 | lib est | FAIL | no |
| physical/ref_tile/qkd_astk_ctl/views/qkd_astk_ctl | qkd_astk_ctl | loop | 316.7 (lt[6]) | 175.5 (aq[251]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_q5_landing_ecc | qfd_q5_landing_ecc | loop | 312.4 (o_data[232]) | 690.7 (i_code[57]) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_link_adp128_p12_txcap/views/qfd_link_adp128_p12_txcap | qfd_link_adp128_p12_txcap | loop | 307.4 (tx_flit[21]) | 167.2 (c_d[84]) | 0 | ins | FAIL | no |
| physical/variant_fill/qfd_link_rx128_rxp-1d3c576bbtc-f5-lvt/views/qfd_link_rx128 | qfd_link_rx128 | loop | 307.0 (i_cr) | 237.3 (i_v) | 0 | lib est | FAIL | no |
| physical/ref_tile/qkd_sbufp_ref/views/ot_qkvd_sbufp | ot_qkvd_sbufp | loop | 306.5 (dout[261]) | 358.7 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/qkd_land_emb/views/qkd_land_emb | qkd_land_emb | loop | 304.2 (dno[114]) | 168.3 (upi[248]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_link_adp128/views/qfd_link_adp128 | qfd_link_adp128 | loop | 304.0 (tx_flit[94]) | 211.4 (r_cr) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_slab_pg_core/views/ot_qwen_slab_pg_core | ot_qwen_slab_pg_core | loop | 303.2 (core_rs0) | 176.0 (col_m5[730]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_vm_su_t/views/ot_qfd_vm_su_t | ot_qfd_vm_su_t | loop | 293.5 (q[456]) | 260.9 (swd[221]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_su_cbuf_native_l0_sp/views/qfd_su_cbuf_native_l0 | qfd_su_cbuf_native_l0 | loop | 288.5 (fault_code[0]) | 179.1 (f_q[174]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_su_lane_h/views/ot_hdc_vstream_lane_h | ot_hdc_vstream_lane_h | loop | 287.1 (va_addr[0]) | 192.0 (sy_rsq_y[28]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qkd_kvwq_ctl_a | qkd_kvwq_ctl_a | loop | 284.2 (fault) | 150.1 (kvw_d[14]) | 0 | lib est | FAIL | no |
| physical/ref_tile/qkd_seq_core/views/qkd_seq_core | qkd_seq_core | loop | 283.8 (t_pw[64]) | 168.7 (r_sd[53]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_lst_c_split | qfd_lst_c_split | loop | 280.6 (w_o[518]) | 176.7 (w_i[410]) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_su_cbuf_native_l0_p13_l12_h2/views/qfd_su_cbuf_native_l0_p13_l12_h2 | qfd_su_cbuf_native_l0_p13_l12_h2 | loop | 279.1 (f_addr[41]) | 307.3 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/qdq_core_fin_ref/views/ot_hgi_qdq_core | ot_hgi_qdq_core | loop | 277.2 (rg_req) | 458.6 (i_fin) | 0 | ins | FAIL | no |
| physical/ref_tile/qdq_asm_ref/views/ot_hgi_qdq_asm | ot_hgi_qdq_asm | loop | 274.0 (m_v) | 177.1 (hq_p1[251]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_lst_c | qfd_lst_c | loop | 272.8 (a_o[261]) | 234.0 (a_i[722]) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_vm_xcol_t/views/ot_qfd_vm_xcol_t | ot_qfd_vm_xcol_t | loop | 271.5 (q_lo[266]) | 348.5 (c_d[4]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_res_slot_ru/views/ot_qfd_res_slot_tile | ot_qfd_res_slot_tile | loop | 268.0 (od[150]) | 237.0 (rst_n) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/hard/ot_qwen_tile_lsl | ot_qwen_tile_lsl | store | 266.2 (lfault[4]) | 175.5 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_vm_xfifo32_codex/views/ot_qfd_vm_xfifo32_t | ot_qfd_vm_xfifo32_t | loop | 266.0 (xo[560]) | 411.1 (rtg[1]) | 0 | ins | FAIL | no |
| physical/ref_tile/qkd_seq_xs/views/qkd_seq_xs | qkd_seq_xs | loop | 255.1 (q_w[58]) | 161.6 (x_d[27]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_crom_gs_a | qfd_crom_gs_a | loop | 253.9 (crom_q[287]) | 207.5 (crom_re[1]) | 0 | lib est | FAIL | no |
| physical/ref_tile/qkh_head_hs_ref/views/ot_qwen_nearhbm_head_hs | ot_qwen_nearhbm_head_hs | loop | 251.7 (nb_d[1009]) | 391.0 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_su_cbuf_g_m5/views/ot_qfd_su_cbuf_g | ot_qfd_su_cbuf_g | loop | 251.5 (f_addr[19]) | 206.5 (f_q[409]) | 0 | ins | FAIL | no |
| physical/ref_tile/qkd_ke_tf_ref/views/ot_qkvd_ke_tf | ot_qkvd_ke_tf | loop | 251.4 (tx_flit[121]) | 161.4 (tw[369]) | 0 | ins | FAIL | no |
| physical/ref_tile/qdq_lq_ref/views/ot_hgi_qdq_lq | ot_hgi_qdq_lq | loop | 250.1 (hq[411]) | 171.7 (wrr[315]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_crom_g_m5/views/ot_qfd_crom_gr | ot_qfd_crom_gr | loop | 248.1 (crom_q[52]) | 182.4 (crom_addr[97]) | 0 | ins | FAIL | no |
| physical/ref_tile/qkd_astk_pv/views/qkd_astk_pv | qkd_astk_pv | loop | 247.8 (co[5]) | 263.6 (ui[82]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_cdc_eco_h1 | qfd_cdc | loop | 246.4 (l_data[194]) | 568.0 (h_hand) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_res_slot | qfd_res_slot | loop | 246.3 (rqf_ptr[4]) | 243.5 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_embed_code_bank_parent | qfd_embed_code_bank_parent | loop | 246.0 (o_data[27]) | 340.9 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_emb_pcport_kvw2_a | qfd_emb_pcport | loop | 244.8 (wd[83]) | 526.5 (col_sr) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_res_slot_rj/views/ot_qfd_res_slot_tile | ot_qfd_res_slot_tile | loop | 243.7 (rqf_ptr[2]) | 325.1 (rd[28]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/ot_qkvd_sbuf | ot_qkvd_sbuf | loop | 243.6 (dout[198]) | 532.0 (pop) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_bl_lane_ce/views/qfd_bl_lane | qfd_bl_lane | loop | 243.3 (pw[6]) | 303.6 (rst_n) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_emb_00 | qfd_ctrl_emb_00 | loop | 242.9 (col_col[0]) | 171.4 (s_v) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_res_slot_rh/views/ot_qfd_res_slot_tile | ot_qfd_res_slot_tile | loop | 242.8 (rqf_ptr[0]) | 342.0 (rst_n) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_link_rx128 | qfd_link_rx128 | loop | 240.9 (i_cr) | 320.8 (i_d[454]) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_link_adp128_p12/views/qfd_link_adp128_p12 | qfd_link_adp128_p12 | loop | 240.9 (tx_flit[27]) | 164.8 (c_d[48]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_su_cbuf_native_l0_p13_l12_r2/views/qfd_su_cbuf_native_l0_p13_l12_r2 | qfd_su_cbuf_native_l0_p13_l12_r2 | loop | 239.6 (f_addr[19]) | 185.5 (f_fault) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_protected_oreg_00 | qfd_ctrl_protected_oreg_00 | loop | 239.2 (row_row[18]) | 355.0 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/qkd_land_pc/views/qkd_land_pc | qkd_land_pc | loop | 238.9 (es[9]) | 166.8 (er[198]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_su_cbuf_native_l0_reqepoch/views/qfd_su_cbuf_native_l0_reqepoch | qfd_su_cbuf_native_l0_reqepoch | loop | 238.7 (f_addr[23]) | 182.9 (crom_stage[3]) | 0 | ins | FAIL | no |
| physical/ref_tile/qdq_fr_one_s2_ref/views/ot_hgi_qdq_fr_one_s2 | ot_hgi_qdq_fr_one_s2 | loop | 238.5 (s2[246]) | 178.4 (rec[669]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_protected_00 | qfd_ctrl_protected_00 | loop | 236.8 (row_row[18]) | 356.4 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_su_vred_region8/views/ot_hdc_vreduce_region8 | ot_hdc_vreduce_region8 | loop | 236.4 (v_out) | 237.5 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/qdq_fr_one_payload_ref/views/ot_hgi_qdq_fr_one_payload | ot_hgi_qdq_fr_one_payload | loop | 236.0 (payload[139]) | 164.7 (rec[177]) | 0 | ins | FAIL | no |
| physical/ref_tile/qkd_astk_zn/views/qkd_astk_zn | qkd_astk_zn | loop | 235.0 (zo[20]) | 161.7 (zi[3]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_embed_code_bank_retained | qfd_embed_code_bank_retained | loop | 234.8 (o_data[78]) | 253.4 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/qdq_core_ref/views/ot_hgi_qdq_core | ot_hgi_qdq_core | loop | 234.8 (o_act) | 164.2 (i_s3[11]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_res_slot_ri/views/ot_qfd_res_slot_tile | ot_qfd_res_slot_tile | loop | 234.7 (rqf_ptr[0]) | 359.1 (slot_id[1]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_vm_xqface_t/views/ot_qfd_vm_xqface_t | ot_qfd_vm_xqface_t | loop | 233.9 (q[773]) | 145.0 (me_e) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_06 | qfd_ctrl_pc_06 | loop | 233.7 (row_op[1]) | 310.5 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/ot_qwen_tile_node/views/ot_qwen_tile_node | ot_qwen_tile_node | loop | 233.3 (t_out[229]) | 170.7 (t_d[185]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_kv_merge_skid8 | qfd_kv_merge_skid8 | loop | 233.2 (kvw_mask[249]) | 451.0 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/qkh_lane8_ref_c/views/ot_qkh_lane8 | ot_qkh_lane8 | loop | 233.1 (kp[9]) | 172.2 (row_in[20]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_cst | qfd_cst | loop | 233.0 (t_d[68]) | 154.9 (a_d[49]) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_vm_xcol_roots/views/ot_qfd_vm_xcol_roots | ot_qfd_vm_xcol_roots | loop | 232.6 (q[126]) | 263.7 (me_e) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_lst_v | qfd_lst_v | loop | 229.3 (b_o[521]) | 178.5 (b_i[663]) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_vm_xplane_t/views/ot_qfd_vm_xplane_t | ot_qfd_vm_xplane_t | loop | 229.2 (q[108]) | 255.8 (me_e) | 0 | ins | FAIL | no |
| physical/ref_tile/qdq_fr_retire_ref/views/ot_hgi_qdq_fr_retire | ot_hgi_qdq_fr_retire | loop | 229.0 (s3[113]) | 483.1 (fast_v) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_kvc_decode_pc | qfd_kvc_decode_pc | loop | 228.6 (o_data[186]) | 315.9 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/qkd_seq_fan/views/qkd_seq_fan | qkd_seq_fan | loop | 228.0 (aq[4]) | 165.4 (kw[61]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_vm_xrelay_w/views/ot_qfd_vm_xrelay_t | ot_qfd_vm_xrelay_t | loop | 227.4 (q[163]) | 133.4 (d[412]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_vm_xrelay_w/views/ot_qfd_vm_xrelay_w | ot_qfd_vm_xrelay_w | loop | 227.4 (q[163]) | 133.4 (d[412]) | 0 | ins | FAIL | no |
| physical/ref_tile/qdq_fr_ref/views/ot_hgi_qdq_fr | ot_hgi_qdq_fr | loop | 226.9 (s3[150]) | 165.1 (rec[496]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_xf_ch546/views/qfd_xf_ch | qfd_xf_ch | loop | 226.1 (w_fault) | 160.1 (i_d[335]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_tt_up4_tp8/views/ot_qfd_band_upper | ot_qfd_band_upper | loop | 225.2 (tt_ty[283]) | 324.1 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/qkd_ke_ro_ref/views/ot_qkvd_ke_ro | ot_qkvd_ke_ro | loop | 224.8 (r_d[505]) | 168.3 (r_cr) | 0 | ins | FAIL | no |
| physical/ref_tile/qkd_host_ctl/views/qkd_host_ctl | qkd_host_ctl | loop | 224.2 (hc[60]) | 310.6 (rst_n) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_res_ctl | qfd_res_ctl | loop | 224.0 (fault) | 245.4 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/qdq_fr_one_payload_face_ref/views/ot_hgi_qdq_fr_one_payload_face | ot_hgi_qdq_fr_one_payload_face | loop | 223.5 (payload[111]) | 171.7 (rec[199]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_io_host_qm/views | qfd_io_host_qm | store | 222.8 (o_d[255]) | 377.7 (h_d[457]) | 0 | ins | FAIL | no |
| physical/ref_tile/qkd_fbuf8_ref/views/ot_qkvd_fbuf8 | ot_qkvd_fbuf8 | loop | 222.8 (dout[471]) | 379.1 (pop) | 0 | ins | FAIL | no |
| physical/ref_tile/qkd_ke_ti_ref/views/ot_qkvd_ke_ti | ot_qkvd_ke_ti | loop | 222.5 (ce_d[212]) | 165.2 (tcr_i) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_vm_xrelay_t/views/ot_qfd_vm_xrelay_t | ot_qfd_vm_xrelay_t | loop | 222.2 (q[127]) | 130.1 (d[279]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_lst_h | qfd_lst_h | loop | 222.1 (b_o[327]) | 168.4 (b_i[152]) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_su_cbuf_g_b | qfd_su_cbuf_g_b | loop | 221.9 (f_addr[70]) | 380.7 (grp[2]) | 0 | lib est | FAIL | no |
| physical/qwen_hub_pg_candidates/qfd_hub_ps-dde873a8e-tc-bal32/views/qfd_hub | qfd_hub | loop | 219.2 (ar_d[301]) | 321.2 (l3_i[222]) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_05 | qfd_ctrl_pc_05 | loop | 217.7 (row_op[1]) | 328.5 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_24 | qfd_ctrl_pc_24 | loop | 217.1 (col_col[0]) | 342.4 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_emb_pcport_kvw2 | qfd_emb_pcport | loop | 217.0 (em_d[184]) | 512.4 (col_sr) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_lst_v_m5/views/ot_qwen_die_link_stn | ot_qwen_die_link_stn | loop | 216.7 (b_o[730]) | 267.8 (b_i[895]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_02 | qfd_ctrl_pc_02 | loop | 215.2 (row_op[1]) | 347.3 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_embed_ingress_scale_padded | qfd_embed_ingress_scale_padded | loop | 215.1 (address_n[9]) | 229.4 (credit) | 0 | lib est | FAIL | no |
| physical/ref_tile/ot_qkvd_fbuf8_m5/views/ot_qkvd_fbuf8 | ot_qkvd_fbuf8 | loop | 215.0 (dout[385]) | 290.5 (pop) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_31 | qfd_ctrl_pc_31 | loop | 214.5 (row_op[2]) | 320.3 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_ctrl_pc_19_m5/views/ot_qwen_ctrl_pc_head | ot_qwen_ctrl_pc_head | loop | 214.3 (col_we) | 365.3 (rst_n) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_03 | qfd_ctrl_pc_03 | loop | 214.2 (row_op[2]) | 359.7 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_io_emb_tap | qfd_io_emb_tap | loop | 213.5 (p_data[53]) | 325.3 (d_tap[0]) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_04 | qfd_ctrl_pc_04 | loop | 213.2 (row_op[1]) | 364.0 (rst_n) | 0 | lib est | FAIL | no |
| physical/multivt/qfd_ctrl_pc_01-74d839a79-tt-lvt/views/qfd_ctrl_pc_01 | qfd_ctrl_pc_01 | loop | 212.2 (col_bank[0]) | 358.3 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/qend_pack_k_rt_a/views/hfd_qsel_pack_k | hfd_qsel_pack_k | loop | 211.9 (o_line[551]) | 447.7 (i_sel[9]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_22 | qfd_ctrl_pc_22 | loop | 211.7 (row_op[2]) | 330.7 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_su_kv624 | qfd_su_kv624 | loop | 211.3 (o_mask[21]) | 433.0 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_20 | qfd_ctrl_pc_20 | loop | 210.5 (col_v) | 325.5 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_embed_ingress_code_padded | qfd_embed_ingress_code_padded | loop | 210.5 (address_q[7]) | 228.3 (credit) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_su_vred_tail64/views/ot_hdc_vreduce_tail64 | ot_hdc_vreduce_tail64 | loop | 209.4 (o_we) | 225.5 (rst_n) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_09 | qfd_ctrl_pc_09 | loop | 209.2 (row_op[1]) | 341.6 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_18 | qfd_ctrl_pc_18 | loop | 208.1 (row_op[2]) | 336.6 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_crom_g_a | qfd_crom_g_a | loop | 207.5 (crom_q[41]) | 246.8 (crom_re[5]) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_30 | qfd_ctrl_pc_30 | loop | 207.5 (row_row[3]) | 330.5 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_13 | qfd_ctrl_pc_13 | loop | 206.1 (row_row[3]) | 341.8 (rst_n) | 0 | lib est | FAIL | no |
| physical/multivt/qfd_ctrl_pc_16-74d839a79-tt-lvt/views/qfd_ctrl_pc_16 | qfd_ctrl_pc_16 | loop | 206.0 (col_we) | 343.9 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_08 | qfd_ctrl_pc_08 | loop | 204.8 (col_v) | 335.2 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_16 | qfd_ctrl_pc_16 | loop | 204.3 (col_we) | 333.7 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_21 | qfd_ctrl_pc_21 | loop | 204.2 (row_op[1]) | 340.0 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_12 | qfd_ctrl_pc_12 | loop | 203.9 (row_row[5]) | 335.0 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_11 | qfd_ctrl_pc_11 | loop | 203.0 (row_op[1]) | 335.1 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_25 | qfd_ctrl_pc_25 | loop | 201.6 (row_op[1]) | 346.2 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_kvc_decode_map_pc_m5/views/ot_qwen_kvc_decode_map_pc | ot_qwen_kvc_decode_map_pc | loop | 201.6 (o_sel0[0]) | 354.2 (rst_n) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_07 | qfd_ctrl_pc_07 | loop | 201.3 (row_op[2]) | 343.6 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_23 | qfd_ctrl_pc_23 | loop | 200.4 (col_v) | 332.7 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_embed_ingress_code_numeric | qfd_embed_ingress_code_numeric | loop | 200.1 (credit_q) | 228.3 (credit) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_19 | qfd_ctrl_pc_19 | loop | 199.4 (row_op[2]) | 342.4 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_00 | qfd_ctrl_pc_00 | loop | 199.3 (row_bank[0]) | 321.3 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_ready_00 | qfd_ctrl_ready_00 | loop | 199.3 (row_bank[0]) | 321.3 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_kvc_decode_pc_m5/views/ot_qwen_kvc_decode_pc | ot_qwen_kvc_decode_pc | loop | 198.6 (fault) | 416.0 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_ctrl_pc_11_m5/views/ot_qwen_ctrl_pc | ot_qwen_ctrl_pc | loop | 198.3 (row_bank[0]) | 344.7 (rst_n) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_10 | qfd_ctrl_pc_10 | loop | 198.0 (row_op[2]) | 326.9 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_17 | qfd_ctrl_pc_17 | loop | 197.5 (row_op[2]) | 349.2 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_embed_ingress_scale_numeric | qfd_embed_ingress_scale_numeric | loop | 197.2 (credit_n) | 229.7 (valid) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_su_cbuf_g_a | qfd_su_cbuf_g_a | loop | 197.1 (f_stage[0]) | 422.7 (grp[1]) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_26 | qfd_ctrl_pc_26 | loop | 195.8 (col_we) | 331.2 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_ctrl_pc_00_m5/views/ot_qwen_ctrl_pc | ot_qwen_ctrl_pc | loop | 195.2 (col_we) | 348.7 (rst_n) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_14 | qfd_ctrl_pc_14 | loop | 195.0 (col_bank[2]) | 336.1 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_27 | qfd_ctrl_pc_27 | loop | 195.0 (row_op[1]) | 345.4 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_kvc_decode_map_pc | qfd_kvc_decode_map_pc | loop | 193.5 (o_data[115]) | 346.7 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/ot_qkvd_fbuf8 | ot_qkvd_fbuf8 | loop | 193.0 (dout[90]) | 307.1 (pop) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_15 | qfd_ctrl_pc_15 | loop | 192.4 (row_op[2]) | 351.4 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qkd_kvwq_leaf_b | qkd_kvwq_leaf_b | loop | 192.3 (n_d[126]) | 190.8 (dn_bad) | 0 | lib est | FAIL | no |
| physical/multivt/qfd_kvc_decode_map_pc-970663df7-tt-lvt/views/qfd_kvc_decode_map_pc | qfd_kvc_decode_map_pc | loop | 192.1 (o_sel1[0]) | 337.3 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_shift_00 | qfd_ctrl_shift_00 | loop | 192.1 (row_op[1]) | 351.2 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_ctrl_pc_31_m5/views/ot_qwen_ctrl_pc_head | ot_qwen_ctrl_pc_head | loop | 190.9 (row_row[8]) | 346.6 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/qkd_fbuf8p_ref/views/ot_qkvd_fbuf8p | ot_qkvd_fbuf8p | loop | 189.2 (dout[449]) | 199.6 (pop) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_29 | qfd_ctrl_pc_29 | loop | 188.5 (row_op[1]) | 353.4 (rst_n) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_28 | qfd_ctrl_pc_28 | loop | 186.6 (col_v) | 347.7 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/qend_pack_k_rt_b/views/hfd_qsel_pack_k | hfd_qsel_pack_k | loop | 184.3 (o_line[528]) | 408.8 (i_sel[3]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_ctrl_pc_16_m5/views/ot_qwen_ctrl_pc | ot_qwen_ctrl_pc | loop | 183.7 (row_row[16]) | 357.7 (rst_n) | 0 | ins | FAIL | no |
| physical/qwen_die_masters/views/qfd_ctrl_pc_01 | qfd_ctrl_pc_01 | loop | 182.0 (row_op[2]) | 344.2 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_q5_landing_ecc_p2/views/ot_qfd_kv_landing_ecc | ot_qfd_kv_landing_ecc | loop | 172.7 (o_v) | 202.7 (h_rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_ctrl_ready_00_m5/views/ot_qwen_ctrl_pc_head | ot_qwen_ctrl_pc_head | loop | 169.7 (row_op[2]) | 331.1 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/qkh_recip_ref/views/ot_qkh_recip_leaf | ot_qkh_recip_leaf | loop | 169.0 (y[24]) | 233.9 (rst_n) | 0 | ins | FAIL | no |
| physical/qwen_embedding_parent/bindings/code/qfd_embed_ingress_code | qfd_embed_ingress_code | loop | 160.7 (valid_q) | 227.8 (credit) | 0 | lib est | FAIL | no |
| physical/qwen_embedding_parent/bindings/scale/qfd_embed_ingress_scale | qfd_embed_ingress_scale | loop | 159.6 (valid_q) | 228.6 (credit) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qkd_kvwq_leaf_s | qkd_kvwq_leaf_s | loop | 158.2 (w_data[137]) | 231.1 (dn_v) | 0 | lib est | FAIL | no |
| physical/qwen_die_masters/views/qfd_embed_scale_bank_parent | qfd_embed_scale_bank_parent | loop | 154.1 (i_cr) | 345.0 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/qfd_io_emb_tap_m5/views/ot_qfd_emb_tap | ot_qfd_emb_tap | loop | 148.7 (p_data[337]) | 294.2 (d_tap[8]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_vm_xfifo8_codex/views/ot_qfd_vm_xfifo8_t | ot_qfd_vm_xfifo8_t | loop | 146.8 (xo[7]) | 254.4 (rtg[0]) | 0 | ins | FAIL | no |
| physical/ref_tile/qfd_cst_n/views/qfd_cst_n | qfd_cst_n | loop | 197.2 (a_d[193]) | 162.5 (b_d[446]) | 0 | ins | PASS | yes |
| physical/ref_tile/qfd_chead_e/views/qfd_chead_e | qfd_chead_e | loop | 192.3 (e_d[334]) | 186.6 (w_d[276]) | 0 | ins | PASS | yes |
| physical/ref_tile/qfd_chead_w/views/qfd_chead_w | qfd_chead_w | loop | 191.0 (w_d[410]) | 184.9 (e_d[325]) | 0 | ins | PASS | yes |
| physical/ref_tile/qfd_cst_s/views/qfd_cst_s | qfd_cst_s | loop | 189.7 (tap_d[8]) | 161.0 (a_d[475]) | 0 | ins | PASS | yes |
| physical/qwen_die_masters/views/qkd_kvwq_leaf_s_w129_m | qkd_kvwq_leaf_s_w129_m | loop | 176.8 (w_data[87]) | 177.1 (dn_bad) | 0 | lib est | PASS | cell |
| physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy | ot_qkvd_ucie_x64_phy | store | 117.3 (tx_up) | 143.5 (tx_v) | 0 | lib est | PASS | cell |
| physical/ref_tile/qfd_vm_rr2_t/views/ot_qfd_vm_rr2_t | ot_qfd_vm_rr2_t | loop | 219.4 (ro[284]) | 170.6 (t1a[494]) | 0 | ins | PASS | no |
| physical/ref_tile/qfd_su_sfu_exp/views/ot_hdc_sfu_exp_t | ot_hdc_sfu_exp_t | loop | 218.1 (y[26]) | 162.4 (x[3]) | 0 | ins | PASS | no |
| physical/ref_tile/qfd_vm_rr4_t/views/ot_qfd_vm_rr4_t | ot_qfd_vm_rr4_t | loop | 217.4 (t1[264]) | 184.7 (bx[1760]) | 0 | ins | PASS | no |
| physical/ref_tile/qfd_su_sfu_rsq/views/ot_hdc_sfu_rsq_t | ot_hdc_sfu_rsq_t | loop | 216.6 (y[16]) | 159.7 (x[27]) | 0 | ins | PASS | no |
| physical/ref_tile/qfd_vm_xpad2_t/views/ot_qfd_vm_xpad2_t | ot_qfd_vm_xpad2_t | loop | 215.9 (q[295]) | 118.1 (me_e) | 0 | ins | PASS | no |
| physical/ref_tile/qkd_rstseq/views/qkd_rstseq | qkd_rstseq | loop | 214.3 (rst_st[2]) | 153.2 (boot_done[3]) | 0 | ins | PASS | no |
| physical/ref_tile/qdq_fr_capture_retire_ref/views/ot_hgi_qdq_fr_capture_retire | ot_hgi_qdq_fr_capture_retire | loop | 213.4 (overflow) | 176.8 (fast_payload[79]) | 0 | ins | PASS | no |
| physical/ref_tile/qfd_su_sfu_rcp/views/ot_hdc_sfu_rcp_t | ot_hdc_sfu_rcp_t | loop | 212.3 (y[14]) | 163.6 (x[14]) | 0 | ins | PASS | no |
| physical/ref_tile/ot_qwen_tile_rpair/views/ot_qwen_tile_rpair | ot_qwen_tile_rpair | loop | 210.4 (r_q[299]) | 110.8 (ad_d[0]) | 0 | ins | PASS | no |
| physical/ref_tile/qkd_ke_tm_ref/views/ot_qkvd_ke_tm | ot_qkvd_ke_tm | loop | 209.1 (tw[374]) | 186.9 (h1[123]) | 0 | ins | PASS | no |
| physical/ref_tile/qfd_vm_bctl_t/views/ot_qfd_vm_bctl_t | ot_qfd_vm_bctl_t | loop | 208.7 (rtg) | 150.0 (wl[3]) | 0 | ins | PASS | no |
| physical/ref_tile/qkd_ke_ctl_ref/views/ot_qkvd_ke_ctl | ot_qkvd_ke_ctl | loop | 208.4 (rqq_o[0]) | 153.8 (crq[2]) | 0 | ins | PASS | no |
| physical/qwen_die_masters/views/qkd_kvwq_grp_a | qkd_kvwq_grp_a | loop | 205.1 (w_data[1959]) | 163.9 (w_room[1]) | 0 | lib est | PASS | no |
| physical/ref_tile/qkd_ke_wf_ref/views/ot_qkvd_ke_wf | ot_qkvd_ke_wf | loop | 203.8 (fault_cause[2]) | 148.8 (flt_i[5]) | 0 | ins | PASS | no |
| physical/ref_tile/qfd_vm_sctl_t/views/ot_qfd_vm_sctl_t | ot_qfd_vm_sctl_t | loop | 203.4 (svc) | 148.9 (swl[5]) | 0 | ins | PASS | no |
| physical/ref_tile/qkd_ctrl_kc/views/qkd_ctrl_kc | qkd_ctrl_kc | loop | 199.8 (ko[19]) | 155.0 (kc[13]) | 0 | ins | PASS | no |
| physical/ref_tile/qfd_vm_fan_lc/views/ot_qfd_vm_fan_t | ot_qfd_vm_fan_t | loop | 199.1 (q[20]) | 142.3 (me_e) | 0 | ins | PASS | no |
| physical/qwen_die_masters/views/qfd_tt_up4_b | qfd_tt_up4_b | loop | 198.6 (tt_ty[143]) | 163.1 (lf[0]) | 0 | lib est | PASS | no |
| physical/ref_tile/qfd_vm_fan_pc/views/ot_qfd_vm_fan_t | ot_qfd_vm_fan_t | loop | 198.4 (q[10]) | 140.9 (me_e) | 0 | ins | PASS | no |
| physical/ref_tile/qdq_wr_fin_ref/views/ot_hgi_qdq_wr_fin | ot_hgi_qdq_wr_fin | loop | 196.2 (o_bad) | 167.0 (wwq_done[6]) | 0 | ins | PASS | no |
| physical/ref_tile/qfd_cbuf_ready_join8/views/qfd_cbuf_ready_join8 | qfd_cbuf_ready_join8 | loop | 194.7 (cb_st_rdy) | 158.1 (st_rdy_stage[2]) | 0 | ins | PASS | no |
| physical/ref_tile/qfd_vm_fan_me/views/ot_qfd_vm_fan_t | ot_qfd_vm_fan_t | loop | 186.4 (q[0]) | 143.9 (d[0]) | 0 | ins | PASS | no |
| physical/qwen_die_masters/views/ot_nhb_pvlg | ot_nhb_pvlg | loop | 184.5 (pf[1]) | 150.4 (rz[29]) | 0 | lib est | PASS | no |
| physical/qwen_die_masters/views/qkd_kvwq_grp_b | qkd_kvwq_grp_b | loop | 183.2 (w_data[456]) | 188.7 (f_d[29]) | 0 | lib est | PASS | no |
| physical/ref_tile/qfd_chead_m5/views/ot_qwen_die_station | ot_qwen_die_station | loop | 177.0 (c_d[180]) | 133.9 (a_d[326]) | 0 | ins | PASS | no |
| physical/ref_tile/qfd_tree_delay2_t/views/ot_qwen_tree_delay2_t | ot_qwen_tree_delay2_t | loop | 170.5 (q[230]) | 106.0 (d[76]) | 0 | ins | PASS | no |
| physical/qwen_die_masters/views/qkd_kvwq_leaf_s_w129 | qkd_kvwq_leaf_s_w129 | loop | 169.1 (n_d[199]) | 173.4 (dn_bad) | 0 | lib est | PASS | no |
| physical/ref_tile/ot_qkh_lane8_m5/views/ot_qkh_lane8 | ot_qkh_lane8 | loop | 168.5 (kp[31]) | 140.8 (rst_n) | 0 | ins | PASS | no |
| physical/ref_tile/qkh_lane8_ref_b/views/ot_qkh_lane8 | ot_qkh_lane8 | loop | 168.5 (kp[31]) | 140.8 (rst_n) | 0 | ins | PASS | no |
| physical/variant_fill/qfd_cdc1024_a-1a9caff1a-tc/views/qfd_link_rx128 | qfd_link_rx128 | loop | 168.4 (o_d[729]) | 116.5 (i_d[954]) | 0 | lib est | PASS | no |
| physical/ref_tile/qfd_tree_delay8_t/views/ot_qwen_tree_delay8_t | ot_qwen_tree_delay8_t | loop | 168.0 (q[465]) | 106.0 (d[161]) | 0 | ins | PASS | no |
| physical/ref_tile/qfd_tree_delay3_t/views/ot_qwen_tree_delay3_t | ot_qwen_tree_delay3_t | loop | 166.9 (q[208]) | 106.0 (d[114]) | 0 | ins | PASS | no |
| physical/ref_tile/ot_qkh_ktree_m5/views/ot_qkh_ktree | ot_qkh_ktree | loop | 165.8 (g_f) | 161.9 (rst_n) | 0 | ins | PASS | no |
| physical/ref_tile/qkh_ktree_ref/views/ot_qkh_ktree | ot_qkh_ktree | loop | 165.8 (g_f) | 161.9 (rst_n) | 0 | ins | PASS | no |
| physical/ref_tile/qfd_tree_delay16_t/views/ot_qwen_tree_delay16_t | ot_qwen_tree_delay16_t | loop | 164.7 (q[476]) | 118.4 (d[68]) | 0 | ins | PASS | no |
| physical/qwen_die_masters/views/qkd_kvwq_leaf_a | qkd_kvwq_leaf_a | loop | 164.1 (w_data[77]) | 189.7 (dn_bad) | 0 | lib est | PASS | no |
| physical/ref_tile/qfd_tree_delay4_t/views/ot_qwen_tree_delay4_t | ot_qwen_tree_delay4_t | loop | 163.0 (q[10]) | 104.6 (d[442]) | 0 | ins | PASS | no |
| physical/qwen_die_masters/views/qfd_embed_ingress_code | qfd_embed_ingress_code | loop | 160.9 (valid_q) | 127.7 (credit) | 0 | lib est | PASS | no |
| physical/qwen_die_masters/hard/ot_coll_fold_slice | ot_coll_fold_slice | store | 160.0 (sum[22]) | 65.9 (src[334]) | 0 | lib est | PASS | no |
| physical/qwen_die_masters/views/qfd_embed_ingress_scale | qfd_embed_ingress_scale | loop | 158.4 (valid_q) | 130.7 (valid) | 0 | lib est | PASS | no |
| physical/ref_tile/qfd_tree_delay1_t/views/ot_qwen_tree_delay1_t | ot_qwen_tree_delay1_t | loop | 153.7 (q[183]) | 109.2 (d[399]) | 0 | ins | PASS | no |
| physical/ref_tile/qfd_vm_su1024_codex/views/ot_qfd_vm_su1024_t | ot_qfd_vm_su1024_t | loop | 151.7 (so[392]) | 135.0 (rtg) | 0 | ins | PASS | no |
| physical/ref_tile/qfd_tree_delay1/views/ot_qwen_tree_delay | ot_qwen_tree_delay | loop | 151.3 (q[49]) | 111.1 (d[352]) | 0 | ins | PASS | no |
| physical/ref_tile/qfd_cst_m5/views/ot_qwen_die_station | ot_qwen_die_station | loop | 148.9 (t_d[380]) | 125.2 (a_d[231]) | 0 | ins | PASS | no |
| physical/ref_tile/qfd_embed_ingress_code_m5/views/ot_qwen_embedding_ingress_island | ot_qwen_embedding_ingress_island | loop | 147.1 (valid_q) | 134.0 (credit) | 0 | ins | PASS | no |
| physical/qwen_die_masters/views/ot_nhb_zh | ot_nhb_zh | loop | 146.2 (root[29]) | 169.1 (zs_we[10]) | 0 | lib est | PASS | no |
| physical/ref_tile/qfd_slab_pg_lanes/views/ot_qwen_slab_pg_lanes | ot_qwen_slab_pg_lanes | loop | 146.2 (y[98]) | 155.4 (l_ws[1]) | 0 | ins | PASS | no |
| physical/ref_tile/qfd_embed_ingress_scale_m5/views/ot_qwen_embedding_ingress_island | ot_qwen_embedding_ingress_island | loop | 143.9 (credit_n) | 134.0 (credit) | 0 | ins | PASS | no |
| physical/qkd_astk_strip/macros/ot_sram_1r1w_256x128_m1_r2c2 | ot_sram_1r1w_256x128_m1_r2c2 | store | None (None) | 107.0 (w_ce_in) | 0 | lib est | PASS | no |
| physical/qkd_astk_strip/macros/ot_sram_1r1w_64x128_m1_r2c2 | ot_sram_1r1w_64x128_m1_r2c2 | store | None (None) | 107.0 (w_ce_in) | 0 | lib est | PASS | no |

## s81

| view | cell | closed by | worst launch ps (pin) | worst capture ps (pin) | comb | R src | pass | used |
|---|---|---|---:|---:|---:|---|---|---|
| physical/ref_tile/dscoll_ces0_sp/views/dsfd_coll_ces0 | dsfd_coll_ces0 | loop | 526.6 (cr_o[5]) | 262.6 (rs) | 0 | ins | FAIL | yes |
| physical/ref_tile/dscoll_cesn_sp/views/dsfd_coll_cesn | dsfd_coll_cesn | loop | 493.0 (cr_o[5]) | 250.8 (rs) | 0 | ins | FAIL | yes |
| physical/ref_tile/dscoll_lane_w_cxea/views/dsfd_coll_lane_w | dsfd_coll_lane_w | loop | 439.8 (flt[2]) | 494.0 (lo_v[0]) | 0 | ins | FAIL | yes |
| physical/ref_tile/s81hc_crrfw_ref/views/ot_s81_hc_crootr_f | ot_s81_hc_crootr_f | loop | 429.2 (ch_fd[1109]) | 497.0 (p_y[1213]) | 0 | ins | FAIL | yes |
| physical/ref_tile/hrow5_cbw_cx/views/dsfd_mtp_hrow_cbw | dsfd_mtp_hrow_cbw | loop | 422.8 (t_w[54]) | 440.4 (f_w[75]) | 0 | ins | FAIL | yes |
| physical/ref_tile/s81hc_crrre_ref/views/ot_s81_hc_crootr_r | ot_s81_hc_crootr_r | loop | 414.7 (t_pk[19]) | 397.4 (ch_rd[323]) | 0 | ins | FAIL | yes |
| physical/ref_tile/p2h_head_ref/views/ot_p2h_head | ot_p2h_head | loop | 413.1 (t_out[46]) | 289.2 (f_s[102]) | 0 | ins | FAIL | yes |
| physical/ref_tile/s81su_qbe_sp8_ref/views/dsfd_su_t_qbe | dsfd_su_t_qbe | loop | 406.4 (nx_o_q[44]) | 375.6 (cfg_b[2]) | 0 | ins | FAIL | yes |
| physical/ref_tile/hrow5_cbe_cx/views/dsfd_mtp_hrow_cbe | dsfd_mtp_hrow_cbe | loop | 399.0 (t_w[844]) | 505.9 (f_w[327]) | 0 | ins | FAIL | yes |
| physical/ref_tile/dsfd_coll_ct_rt/views/dsfd_coll_ct | dsfd_coll_ct | loop | 367.6 (elo_d[68]) | 515.9 (eli_d[514]) | 0 | ins | FAIL | yes |
| physical/ref_tile/s81su_qbt_ref/views/dsfd_su_t_qbt | dsfd_su_t_qbt | loop | 358.8 (e_dl[3773]) | 415.9 (dn_st) | 0 | ins | FAIL | yes |
| physical/ref_tile/s81su_ctl_ref/views/dsfd_su_t_ctl | dsfd_su_t_ctl | loop | 354.3 (rst_o) | 179.8 (up_rjid[3]) | 0 | ins | FAIL | yes |
| physical/ref_tile/dscoll_ces0_cxsp/views/dsfd_coll_ces0 | dsfd_coll_ces0 | loop | 317.9 (tx_d[9]) | 450.2 (qp[3]) | 0 | ins | FAIL | yes |
| physical/ref_tile/hrow5_hub/views/dsfd_mtp_hrow_hub | dsfd_mtp_hrow_hub | loop | 316.0 (t_rc1[3]) | 357.3 (f_pr1[693]) | 0 | ins | FAIL | yes |
| physical/ref_tile/s81su_kvq_ref/views/dsfd_su_t_kvq | dsfd_su_t_kvq | loop | 304.9 (o_d[150]) | 360.7 (i_y[770]) | 0 | ins | FAIL | yes |
| physical/ref_tile/s81hc_crrte_ref/views/ot_s81_hc_crootr_t | ot_s81_hc_crootr_t | loop | 293.3 (s_ex[349]) | 406.6 (s_fd[1114]) | 0 | ins | FAIL | yes |
| physical/ref_tile/s81su_swe_gfix_ref/views/dsfd_su_t_swe | dsfd_su_t_swe | loop | 270.8 (c_od[33]) | 223.2 (c_id[69]) | 0 | ins | FAIL | yes |
| physical/ref_tile/dsfd_su_t_pin_rt/views/dsfd_su_t_pin | dsfd_su_t_pin | loop | 267.1 (c_rf[117]) | 244.9 (up_a[34]) | 0 | ins | FAIL | yes |
| physical/ref_tile/s81hc_crrww_ref/views/ot_s81_hc_crootr_w | ot_s81_hc_crootr_w | loop | 250.6 (p_w[23]) | 276.4 (s_w[1818]) | 0 | ins | FAIL | yes |
| physical/s81_die_views/q_elem_qs5f_efs | ot_v41_rom_elem_q_qxpq_w10 | store | 212.4 (bank_free) | 239.2 (rst_n) | 0 | ins | FAIL | yes |
| physical/s81_ph_views/vm_master/views/dsfd_vm_be_sl | dsfd_vm_be_sl | loop | 186.9 (bl_d[638]) | 246.0 (o_v[5]) | 0 | lib est | FAIL | yes |
| physical/ref_tile/s81hc_cpin_ref/views/ot_s81_hc_cpin | ot_s81_hc_cpin | loop | 427.9 (yacc_w) | 469.6 (y_s[2464]) | 0 | ins | FAIL | cell |
| physical/ref_tile/s81hc_crrfe_ref/views/ot_s81_hc_crootr_f | ot_s81_hc_crootr_f | loop | 392.6 (ch_fd[1100]) | 499.3 (p_y[1056]) | 0 | ins | FAIL | cell |
| physical/ref_tile/s81hc_crywe_ref/views/ot_s81_hc_crooty_w | ot_s81_hc_crooty_w | loop | 386.0 (wq_d[1154]) | 372.9 (p_w[1629]) | 0 | ins | FAIL | cell |
| physical/ref_tile/s81hc_cryww_ref/views/ot_s81_hc_crooty_w | ot_s81_hc_crooty_w | loop | 379.1 (wq_d[1899]) | 331.1 (p_w[268]) | 0 | ins | FAIL | cell |
| physical/ref_tile/s81hc_crrrw_ref/views/ot_s81_hc_crootr_r | ot_s81_hc_crootr_r | loop | 365.6 (t_pk[283]) | 393.3 (ch_rd[329]) | 0 | ins | FAIL | cell |
| physical/ref_tile/s81su_qbe_spx_ref/views/dsfd_su_t_qbe | dsfd_su_t_qbe | loop | 360.2 (nx_o_q[45]) | 388.4 (cfg_b[1]) | 0 | ins | FAIL | cell |
| physical/s81_ph_views/closed/dsfd_coll_lane_w | dsfd_coll_lane_w | loop | 347.5 (li_d[107]) | 371.8 (li_r[0]) | 0 | lib est | FAIL | cell |
| physical/ref_tile/dsfd_coll_cbr_m5/views/dsfd_coll_cbr | dsfd_coll_cbr | loop | 322.2 (n_li_d[157]) | 225.8 (x_li_d[211]) | 0 | ins | FAIL | cell |
| physical/ref_tile/s81su_swe_spx_ref/views/dsfd_su_t_swe | dsfd_su_t_swe | loop | 271.4 (c_od[9]) | 229.0 (c_id[52]) | 0 | ins | FAIL | cell |
| physical/ref_tile/s81su_swe_sp8_ref/views/dsfd_su_t_swe | dsfd_su_t_swe | loop | 266.4 (c_od[26]) | 294.2 (c_id[91]) | 0 | ins | FAIL | cell |
| physical/ref_tile/s81hc_crrwe_ref/views/ot_s81_hc_crootr_w | ot_s81_hc_crootr_w | loop | 259.6 (p_w[51]) | 278.4 (s_w[1827]) | 0 | ins | FAIL | cell |
| physical/ref_tile/dsfd_coll_cbq0_m5/views/dsfd_coll_cbq0 | dsfd_coll_cbq0 | loop | 247.6 (t_vm[7]) | 218.6 (bw_v) | 0 | ins | FAIL | cell |
| physical/ref_tile/s81su_pinns_ref/views/dsfd_su_t_pin | dsfd_su_t_pin | loop | 240.2 (wq_mask[4]) | 188.9 (up_m[8]) | 0 | ins | FAIL | cell |
| physical/ref_tile/s81hc_crrtw_ref/views/ot_s81_hc_crootr_t | ot_s81_hc_crootr_t | loop | 223.2 (s_ex[307]) | 415.5 (s_fd[1074]) | 0 | ins | FAIL | cell |
| physical/variant_fill/dsfd_coll_ct-fe-34c4ded32-rsl-tc-cl/dsfd_coll_ct | dsfd_coll_ct | loop | 194.5 (lo7_r[0]) | 233.5 (lo3_d[29]) | 0 | lib est | FAIL | cell |
| physical/hbm_export_revisions_1013/dsfd_coll_ct-fe-6d1a3decb-kpslvt-tc-cl/dsfd_coll_ct | dsfd_coll_ct | loop | 146.9 (lo3_r[0]) | 197.6 (lo3_d[64]) | 0 | lib est | FAIL | cell |
| physical/variant_fill/dsfd_coll_ct-fe-6d1a3decb-kpslvt-tc-cl/dsfd_coll_ct | dsfd_coll_ct | loop | 146.9 (lo3_r[0]) | 197.6 (lo3_d[64]) | 0 | lib est | FAIL | cell |
| physical/dsrom_fh_safe/closed/ep_r4 | ot_hdc_v41_fh_ep_view | loop | 610.6 (request_checked_v) | 264.4 (head_addr[15]) | 0 | lib est | FAIL | no |
| physical/s81_engc_tiles/results/el1011-engc-pbb-a-109a69d35-tc-cl/views/ot_engc_t_pbb | ot_engc_t_pbb | loop | 502.8 (x_do[266]) | 482.6 (x_d[14]) | 0 | lib est | FAIL | no |
| physical/s81_engc_tiles/results/el1011-engc-pbb-b-109a69d35-tc-cl/views/ot_engc_t_pbb | ot_engc_t_pbb | loop | 502.8 (x_do[266]) | 482.6 (x_d[14]) | 0 | lib est | FAIL | no |
| physical/s81_engc_tiles/views/ot_engc_t_pbb | ot_engc_t_pbb | loop | 502.8 (x_do[266]) | 482.6 (x_d[14]) | 0 | lib est | FAIL | no |
| physical/s81_engc_tiles/results/el1013-engc-pbb-rv-22566e03c-tc-cl/views/ot_engc_t_pbb | ot_engc_t_pbb | loop | 463.9 (r_d[120]) | 479.5 (x_d[5]) | 0 | lib est | FAIL | no |
| physical/s81_die_views/views/m221pq/dsfd_m2l_vr_68x11__hr_E3 | dsfd_m2l_vr_68x11__hr_E3 | loop | 461.1 (o[760]) | 429.4 (di0[1]) | 0 | ins | FAIL | no |
| physical/s81_pq_hier/results/el1011-pqc-srom-b-cc60cd537-tc-cl/views/ot_pqc_t_srom | ot_pqc_t_srom | loop | 458.7 (q[26]) | 468.7 (wa[7]) | 0 | lib est | FAIL | no |
| physical/s81_pq_hier/results/el1011-pqc-srom-c-648e3800a-tc-cl/views/ot_pqc_t_srom | ot_pqc_t_srom | loop | 447.1 (q[35]) | 447.0 (wa[0]) | 0 | lib est | FAIL | no |
| physical/s81_pq_hier/views/ot_pqc_t_srom | ot_pqc_t_srom | loop | 447.1 (q[35]) | 447.0 (wa[0]) | 0 | lib est | FAIL | no |
| physical/variant_fill/s81-hend-m221pq-hr-W4-a1f23fa0b-mm-vf-hm25/dsfd_m2l_vr_68x11__hr_W4 | dsfd_m2l_vr_68x11__hr_W4 | loop | 440.5 (o[760]) | 432.6 (di5[0]) | 0 | ins | FAIL | no |
| physical/ref_tile/dscoll_cesc0/views/dsfd_coll_cesc0 | dsfd_coll_cesc0 | loop | 431.5 (ln_d[189]) | 189.6 (ln_y[93]) | 0 | ins | FAIL | no |
| physical/ref_tile/dscoll_cescn/views/dsfd_coll_cescn | dsfd_coll_cescn | loop | 416.0 (ln_d[408]) | 196.4 (ln_y[121]) | 0 | ins | FAIL | no |
| physical/mtp_link_rtt/view_f9r10_d23_dd7ddda95/view | ot_dsrom_mtp_lrx_rtt | loop | 409.8 (c_data[269]) | 245.7 (c_ready) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81hc_ccfh2_ref/views/ot_s81_hc_ccf | ot_s81_hc_ccf | loop | 408.2 (ch_rst) | 544.3 (fv_i[2]) | 0 | ins | FAIL | no |
| physical/dsrom_fh_safe/closed/ep_r6_routed_boundary | ot_hdc_v41_fh_ep_view | store | 405.4 (guard_busy) | 440.2 (head_we[0]) | 0 | lib est | FAIL | no |
| physical/s81_pq_hier/results/el1011-pqc-prom-b-cc60cd537-tc-cl/views/ot_pqc_t_prom | ot_pqc_t_prom | loop | 405.1 (q[21]) | 455.1 (wa[2]) | 0 | lib est | FAIL | no |
| physical/s81_ph_views/closed/dsfd_wfc_vmx_prd_default | dsfd_wfc_vmx | store | 392.8 (t_swd[435]) | 225.8 (f_srq[512]) | 0 | ins | FAIL | no |
| physical/variant_fill/s81-hend-m221pq-hr-W1-a1f23fa0b-mm-vf-hm25/dsfd_m2l_vr_68x11__hr_W1 | dsfd_m2l_vr_68x11__hr_W1 | loop | 388.5 (o[760]) | 435.5 (di9[0]) | 0 | ins | FAIL | no |
| physical/variant_fill/s81-hend-m221pq-hr-W2-a1f23fa0b-mm-vf-hm25/dsfd_m2l_vr_68x11__hr_W2 | dsfd_m2l_vr_68x11__hr_W2 | loop | 388.5 (o[760]) | 435.5 (di9[0]) | 0 | ins | FAIL | no |
| physical/variant_fill/s81-hend-m221pq-hr-W3-a1f23fa0b-mm-vf-hm25/dsfd_m2l_vr_68x11__hr_W3 | dsfd_m2l_vr_68x11__hr_W3 | loop | 387.6 (o[760]) | 366.6 (di9[0]) | 0 | ins | FAIL | no |
| physical/s81_pq_hier/results/el1011-pqc-prom-c-648e3800a-tc-cl/views/ot_pqc_t_prom | ot_pqc_t_prom | loop | 383.0 (q[31]) | 439.9 (we) | 0 | lib est | FAIL | no |
| physical/variant_fill/s81-hend-m221pq-hr-E4-a1f23fa0b-mm-vf-hm25/dsfd_m2l_vr_68x11__hr_E4 | dsfd_m2l_vr_68x11__hr_E4 | loop | 380.3 (o[760]) | 485.1 (di9[1]) | 0 | ins | FAIL | no |
| physical/s81_pq_hier/results/el1011-pqc-prom-a-cc60cd537-tc-cl/views/ot_pqc_t_prom | ot_pqc_t_prom | loop | 377.8 (q[53]) | 418.4 (wa[3]) | 0 | lib est | FAIL | no |
| physical/s81_pq_hier/results/el1011-pqc-prom-pka-5e6ab1fda-tc-cl/views/ot_pqc_t_prom | ot_pqc_t_prom | loop | 377.8 (q[53]) | 418.4 (wa[3]) | 0 | lib est | FAIL | no |
| physical/s81_pq_hier/views/ot_pqc_t_prom | ot_pqc_t_prom | loop | 377.8 (q[53]) | 418.4 (wa[3]) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81su_qnq_spx_ref/views/dsfd_su_t_qnq | dsfd_su_t_qnq | loop | 376.6 (nx_o_q[176]) | 298.3 (nx_i_q[121]) | 0 | ins | FAIL | no |
| physical/s81_die_views/views/m221pq/dsfd_m2l_vr_68x10__hr_W5 | dsfd_m2l_vr_68x10__hr_W5 | loop | 368.1 (o[414]) | 393.6 (di3[1]) | 0 | ins | FAIL | no |
| physical/s81_ph_views/closed/dsfd_vm_wfc_ep_rd2 | dsfd_vm_wfc_ep | loop | 362.5 (t_srq[645]) | 321.8 (m1_od[434]) | 0 | lib est | FAIL | no |
| physical/ref_tile/dscoll_cescn_ln_c16/views/dsfd_coll_cescn | dsfd_coll_cescn | loop | 358.5 (cr_o[2]) | 184.8 (pt_d[620]) | 0 | ins | FAIL | no |
| physical/ref_tile/dsfd_vm_fcn_m5_sumpipe/views/dsfd_vm_fcn | dsfd_vm_fcn | loop | 357.1 (t_rdy[0]) | 290.3 (c_wr[0]) | 0 | ins | FAIL | no |
| physical/dsrom_fh_safe/closed/ctl_oreg2 | ot_hdc_v41_fh_ctl | loop | 355.3 (fault) | 197.5 (wr_addr[88]) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81su_qnq_sp8_ref/views/dsfd_su_t_qnq | dsfd_su_t_qnq | loop | 343.3 (nx_o_q[79]) | 282.0 (nx_i_q[162]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81pq_ctl_native/views/ot_s81_pq_ctl_fixed_native | ot_s81_pq_ctl_fixed_native | loop | 341.0 (q_consume) | 300.6 (ga_i[88]) | 18 | ins | FAIL | no |
| physical/dsrom_fh_safe/closed/elemA | ot_dsrom_head_elem | loop | 336.5 (best_key[12]) | 185.5 (x[158]) | 0 | lib est | FAIL | no |
| physical/s81_pq_hier/views/ot_pqc_t_ctl16 | ot_pqc_t_ctl16 | loop | 333.1 (aq_vin) | 199.0 (ga_i[5]) | 0 | lib est | FAIL | no |
| physical/ref_tile/dsfd_vm_fcn_m5_cmdpipe/views/dsfd_vm_fcn | dsfd_vm_fcn | loop | 333.0 (t_rdy[3]) | 296.5 (c_wr[0]) | 0 | ins | FAIL | no |
| physical/s81_pq_tiles/results/el1011-pqc-aq12t-b-cc60cd537-tc-cl/views/ot_dsrom_aq12t | ot_dsrom_aq12t | loop | 330.4 (q[243]) | 181.6 (x[44]) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81pq_aq_mem_native/views/ot_s81_pq_aq_mem_native | ot_s81_pq_aq_mem_native | loop | 330.3 (r_wp[0]) | 170.7 (x[134]) | 0 | ins | FAIL | no |
| physical/s81_pq_hier/results/el1011-pqc-ctl-a-cc60cd537-tc-cl/views/ot_pqc_t_ctl16 | ot_pqc_t_ctl16 | loop | 328.1 (aq_vin) | 202.2 (ga_i[25]) | 0 | lib est | FAIL | no |
| physical/s81_die_views/bf_compact199/ot_s81_bf_front | ot_s81_bf_front | loop | 327.4 (c1_issue) | 188.2 (xb_d[880]) | 0 | lib est | FAIL | no |
| physical/s81_die_views/meso/view_d4/record/view | ot_meso_fifo | loop | 322.5 (r_v) | 93.0 (w_d[395]) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81pq_root_ref/views/ot_s81_pq_ret_root_cam_p | ot_s81_pq_ret_root_cam_p | loop | 314.9 (r_row[2]) | 192.6 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/s81pq_ix_ba_native/views/ot_s81_pq_ix_ba_native | ot_s81_pq_ix_ba_native | loop | 313.2 (ba_hi[331]) | 234.9 (xw[464]) | 0 | ins | FAIL | no |
| physical/s81_ph_views/closed/dsfd_colt_lane | dsfd_colt_lane | loop | 309.2 (t_w[247]) | 303.7 (c_in[398]) | 0 | lib est | FAIL | no |
| physical/s81_engc_tiles/results/el1011-engc-win-pke-a804fc09b-tc-cl/views/ot_engc_t_win | ot_engc_t_win | loop | 307.8 (t_ag[256]) | 240.8 (lk_stb) | 0 | lib est | FAIL | no |
| physical/s81_engc_tiles/results/el1011-engc-win-a-109a69d35-tc-cl/views/ot_engc_t_win | ot_engc_t_win | loop | 307.7 (t_ag[256]) | 241.9 (lk_stb) | 0 | lib est | FAIL | no |
| physical/s81_engc_tiles/results/el1011-engc-win-b-109a69d35-tc-cl/views/ot_engc_t_win | ot_engc_t_win | loop | 307.7 (t_ag[256]) | 241.9 (lk_stb) | 0 | lib est | FAIL | no |
| physical/s81_engc_tiles/views/ot_engc_t_win | ot_engc_t_win | loop | 307.7 (t_ag[256]) | 241.9 (lk_stb) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81hc_cseqh2_ref/views/ot_s81_hc_cseq | ot_s81_hc_cseq | loop | 305.3 (w_fd[74]) | 167.1 (n_yacc) | 0 | ins | FAIL | no |
| physical/dsrom_fh_safe/closed/elemB | ot_dsrom_head_elem | loop | 300.5 (o_d[5]) | 163.3 (x[125]) | 0 | lib est | FAIL | no |
| physical/s81_die_views/views/dsfd_cfifo | dsfd_cfifo | loop | 298.0 (xb[117]) | 223.5 (xd[507]) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81hc_ctfn_ref/views/ot_s81_hc_ctfn | ot_s81_hc_ctfn | loop | 296.0 (fvm[2]) | 378.2 (fv_in[2]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81hc_ccr_ref/views/ot_s81_hc_ccr | ot_s81_hc_ccr | loop | 295.8 (crd_o[587]) | 234.2 (ch_rd[1974]) | 0 | ins | FAIL | no |
| physical/ref_tile/dsfd_wfc_lnk_e/views/dsfd_wfc_lnk | dsfd_wfc_lnk | loop | 293.8 (t_dw[32]) | 298.6 (f_lor[0]) | 0 | ins | FAIL | no |
| physical/s81_pq_tiles/results/el1011-pqc-aq12t-pka-5e6ab1fda-tc-cl/views/ot_dsrom_aq12t | ot_dsrom_aq12t | loop | 291.8 (q[187]) | 202.0 (x[703]) | 0 | lib est | FAIL | no |
| physical/s81_ph_views/closed/dsfd_svcio_q | dsfd_svcio_q | loop | 291.0 (q_q[1941]) | 122.1 (q[332]) | 0 | lib est | FAIL | no |
| physical/ref_tile/dsfd_m2l_raw_512x1__hl_w1_negcap/views/dsfd_m2l_raw_512x1__hl_W1 | dsfd_m2l_raw_512x1__hl_W1 | loop | 290.5 (o[404]) | 219.2 (di0[242]) | 0 | ins | FAIL | no |
| physical/ref_tile/dscoll_cesc0_ln/views/dsfd_coll_cesc0 | dsfd_coll_cesc0 | loop | 290.3 (cr_o[4]) | 188.6 (pt_d[768]) | 0 | ins | FAIL | no |
| physical/ref_tile/dsfd_m2l_raw_512x1__hl_e0_negcap/views/dsfd_m2l_raw_512x1__hl_E0 | dsfd_m2l_raw_512x1__hl_E0 | loop | 288.3 (o[285]) | 199.2 (di0[245]) | 0 | ins | FAIL | no |
| physical/s81_pq_hier/views/ot_dsrom_aq12t | ot_dsrom_aq12t | loop | 285.6 (q[187]) | 191.7 (x[1002]) | 0 | lib est | FAIL | no |
| physical/ref_tile/dsfd_hrow_r2079_m5/views/dsfd_hrow_r2079 | dsfd_hrow_r2079 | loop | 283.5 (o[1623]) | 185.6 (i[908]) | 0 | ins | FAIL | no |
| physical/ref_tile/dsfd_m2l_raw_512x1__hl_e2_negcap/views/dsfd_m2l_raw_512x1__hl_E2 | dsfd_m2l_raw_512x1__hl_E2 | loop | 282.9 (o[397]) | 201.6 (di0[437]) | 0 | ins | FAIL | no |
| physical/s81_ph_views/closed/dsfd_svcio_ad | dsfd_svcio_ad | loop | 282.7 (a0_r[0]) | 237.9 (a1_d[5]) | 0 | lib est | FAIL | no |
| physical/s81_ph_views/closed/dsfd_ctrl_pc | dsfd_ctrl_pc | loop | 282.5 (k_tag[4]) | 402.9 (k_rdy[0]) | 0 | lib est | FAIL | no |
| physical/s81_pq_tiles/results/el1011-pqc-aq12t-a-cc60cd537-tc-cl/views/ot_dsrom_aq12t | ot_dsrom_aq12t | loop | 282.3 (q[187]) | 201.0 (x[275]) | 0 | lib est | FAIL | no |
| physical/s81_ph_views/closed/ot_s81ph_root_tile | ot_s81ph_root_tile | loop | 281.3 (co[43]) | 241.5 (lt_ei[40]) | 0 | lib est | FAIL | no |
| physical/ref_tile/dsfd_capt_x8_dual/views/dsfd_capt_x8_dual | dsfd_capt_x8_dual | loop | 278.6 (t_st[23]) | 158.2 (f_w[367]) | 0 | ins | FAIL | no |
| physical/s81_die_views/views/m221pq/dsfd_m2l_raw_512x1__hl_E2 | dsfd_m2l_raw_512x1__hl_E2 | loop | 278.5 (o[513]) | 138.2 (di0[19]) | 0 | ins | FAIL | no |
| physical/s81_ph_views/closed/dsfd_wfc_crp_hm10 | dsfd_wfc_crp | loop | 274.0 (t_kswa[0]) | 310.9 (f_kswv[0]) | 0 | lib est | FAIL | no |
| physical/ref_tile/dsfd_hrow_r1025_m5/views/dsfd_hrow_r1025 | dsfd_hrow_r1025 | loop | 273.5 (o[77]) | 178.3 (i[385]) | 0 | ins | FAIL | no |
| physical/s81_engc_tiles/results/el1011-engc-io-pka-e432393fb-tc-cl/views/ot_engc_t_io | ot_engc_t_io | loop | 273.4 (r2_a[0]) | 251.7 (rst) | 0 | lib est | FAIL | no |
| physical/s81_engc_tiles/results/el1013-engc-io-rv-22566e03c-tc-cl/views/ot_engc_t_io | ot_engc_t_io | loop | 273.4 (r2_a[0]) | 251.7 (rst) | 0 | lib est | FAIL | no |
| physical/s81_die_views/views/m221pq/dsfd_m2l_vr_512x1__hqe_SW | dsfd_m2l_vr_512x1__hqe_SW | loop | 271.7 (o[0]) | 436.6 (di0[0]) | 0 | ins | FAIL | no |
| physical/s81_ph_views/closed/dsfd_wfc_crp_hm25 | dsfd_wfc_crp | loop | 270.9 (t_kswa[0]) | 310.8 (f_kswv[0]) | 0 | lib est | FAIL | no |
| physical/s81_die_views/views/m221pq/dsfd_m2l_vr_512x1__hco_SW | dsfd_m2l_vr_512x1__hco_SW | loop | 270.8 (o[0]) | 384.1 (di0[1]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81pq_ix_rb_native/views/ot_s81_pq_ix_rb_native | ot_s81_pq_ix_rb_native | loop | 270.5 (bank_fault[0]) | 358.6 (par) | 0 | ins | FAIL | no |
| physical/s81_die_views/views/m221pq/dsfd_m2l_raw_512x1__hl_W1 | dsfd_m2l_raw_512x1__hl_W1 | loop | 268.3 (o[513]) | 120.8 (di0[438]) | 0 | ins | FAIL | no |
| physical/s81_engc_tiles/results/el1011-engc-io-a-109a69d35-tc-cl/views/ot_engc_t_io | ot_engc_t_io | loop | 264.6 (jn_o[13]) | 277.8 (rst) | 0 | lib est | FAIL | no |
| physical/s81_engc_tiles/results/el1011-engc-io-b-109a69d35-tc-cl/views/ot_engc_t_io | ot_engc_t_io | loop | 264.6 (jn_o[13]) | 277.8 (rst) | 0 | lib est | FAIL | no |
| physical/s81_engc_tiles/views/ot_engc_t_io | ot_engc_t_io | loop | 264.6 (jn_o[13]) | 277.8 (rst) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81hc_ccrh2_ref/views/ot_s81_hc_ccr | ot_s81_hc_ccr | loop | 264.1 (crd_o[484]) | 191.6 (ch_rd[583]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81hc_cseq_ref/views/ot_s81_hc_cseq | ot_s81_hc_cseq | loop | 263.7 (w_fd[959]) | 162.5 (x_wdone) | 0 | ins | FAIL | no |
| physical/s81_die_views/views_colck/dsfd_cfifo | dsfd_cfifo | loop | 263.3 (xb[123]) | 205.7 (xd[364]) | 0 | ins | FAIL | no |
| physical/s81_die_views/views/m221pq/dsfd_l2r_vr_512x1__hq_SW | dsfd_l2r_vr_512x1__hq_SW | loop | 261.3 (od[471]) | 119.9 (i[14]) | 0 | ins | FAIL | no |
| physical/ref_tile/dsfd_vm_fld_m5/views/dsfd_vm_fld | dsfd_vm_fld | loop | 260.5 (s_o[574]) | 177.6 (ret[3787]) | 0 | ins | FAIL | no |
| physical/ref_tile/dsfd_vm_flt_m5/views/dsfd_vm_flt | dsfd_vm_flt | loop | 259.8 (ret[71]) | 263.6 (arm_base[5]) | 0 | ins | FAIL | no |
| physical/s81_ph_views/closed/dsfd_svch_pcs | dsfd_svch_pcs | loop | 259.4 (ar_d[140]) | 207.9 (gq_d[29]) | 0 | lib est | FAIL | no |
| physical/s81_ph_views/vm_master/views/dsfd_vm_clt | dsfd_vm_clt | loop | 259.1 (flt[0]) | 128.6 (f_c[552]) | 0 | lib est | FAIL | no |
| physical/variant_fill/s81ph-dsfd_colt_lane-ring-e96dd1e56-tc-hm10-g12/dsfd_colt_lane | dsfd_colt_lane | loop | 258.8 (t_w[214]) | 117.3 (c_in[511]) | 0 | lib est | FAIL | no |
| physical/s81_pq_root_cam_p/view_pq-rc2-a0-h212-hm10/view | ot_s81_pq_ret_root_cam_p | loop | 258.5 (r_row[1]) | 89.0 (i_v) | 0 | lib est | FAIL | no |
| physical/s81_die_views/meso/view_d8g1/view | ot_meso_fifo | loop | 257.7 (r_v) | 80.1 (w_d[196]) | 0 | lib est | FAIL | no |
| physical/ref_tile/dsfd_vm_fld_m5_parallel/views/dsfd_vm_fld | dsfd_vm_fld | loop | 256.1 (s_o[574]) | 175.4 (ret[3144]) | 0 | ins | FAIL | no |
| physical/s81_die_views/views/m221pq/dsfd_m2l_raw_512x1__hl_E0 | dsfd_m2l_raw_512x1__hl_E0 | loop | 255.4 (o[0]) | 109.1 (di0[123]) | 0 | ins | FAIL | no |
| physical/s81_pq_root_cam_p/view_pq-rc2-a7-h212-hm10/view | ot_s81_pq_ret_root_cam_p | loop | 255.0 (r_row[8]) | 95.8 (i_t[17]) | 0 | lib est | FAIL | no |
| physical/s81_ph_views/closed/dsfd_mtp_seed_launch | dsfd_mtp_seed_launch | loop | 253.8 (t_x[499]) | 168.8 (f_x[1]) | 0 | lib est | FAIL | no |
| physical/variant_fill/s81b-selt_c-mrg-mm2-9ac26e269-tt-f5-lvt-hm0/dsfd_selt_c | dsfd_selt_c | loop | 253.6 (t_c[197]) | 182.8 (f_s[844]) | 0 | lib est | FAIL | no |
| physical/s81_ph_views/closed/dsfd_p2_lnk | dsfd_p2_lnk | loop | 252.0 (c_in_d[399]) | 232.3 (c_in_r[0]) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81_markov_ctl_native/views/ot_s81_markov_ctl_native | ot_s81_markov_ctl_native | loop | 251.8 (head[31]) | 284.6 (in_valid) | 0 | ins | FAIL | no |
| physical/s81_engc_tiles/results/el1011-engc-ws-a-109a69d35-tc-cl/views/ot_engc_t_ws | ot_engc_t_ws | loop | 251.1 (b1_d[8]) | 242.0 (f_hr[44]) | 0 | lib est | FAIL | no |
| physical/s81_engc_tiles/results/el1011-engc-ws-b-109a69d35-tc-cl/views/ot_engc_t_ws | ot_engc_t_ws | loop | 251.1 (b1_d[8]) | 242.0 (f_hr[44]) | 0 | lib est | FAIL | no |
| physical/s81_engc_tiles/views/ot_engc_t_ws | ot_engc_t_ws | loop | 251.1 (b1_d[8]) | 242.0 (f_hr[44]) | 0 | lib est | FAIL | no |
| physical/s81_engc_tiles/results/el1011-engc-pbc-a-109a69d35-tc-cl/views/ot_engc_t_pbc | ot_engc_t_pbc | loop | 250.7 (x_a[7]) | 275.0 (x_d[56]) | 0 | lib est | FAIL | no |
| physical/s81_die_views/views/m221pq/dsfd_l2r_vr_564x1__hx_E | dsfd_l2r_vr_564x1__hx_E | loop | 249.9 (od[65]) | 122.5 (i[523]) | 0 | ins | FAIL | no |
| physical/s81_die_views/swiglu/view_esum_25/view | ot_dsrom_su_swiglu_lane | loop | 248.7 (a[13]) | 898.6 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/dsfd_vm_fld_m5_ranks/views/dsfd_vm_fld | dsfd_vm_fld | loop | 247.8 (s_o[664]) | 175.5 (ret[3378]) | 0 | ins | FAIL | no |
| physical/s81_ph_views/closed/dsfd_capt_x | dsfd_capt_x | loop | 247.8 (t_vm[1391]) | 148.1 (f_w[111]) | 0 | lib est | FAIL | no |
| physical/s81_engc_tiles/results/el1013-engc-pbc-rv-22566e03c-tc-cl/views/ot_engc_t_pbc | ot_engc_t_pbc | loop | 246.5 (x_a[7]) | 273.8 (x_d[56]) | 0 | lib est | FAIL | no |
| physical/s81_ph_views/closed/ot_p2h_arith | ot_p2h_arith | loop | 245.0 (t_ab[797]) | 252.4 (f_or) | 0 | lib est | FAIL | no |
| physical/s81_engc_tiles/results/el1011-engc-ws-pk-5f1603a05-tc-cl/views/ot_engc_t_ws | ot_engc_t_ws | loop | 244.4 (b1_d[14]) | 258.1 (f_hr[15]) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81pq_qb_head_native/views/ot_s81_pq_qb_head_native | ot_s81_pq_qb_head_native | loop | 244.1 (i0[2]) | 219.8 (rd_data[240]) | 0 | ins | FAIL | no |
| physical/s81_die_views/views/m221pq/dsfd_m2l_vr_512x1__hix_SW | dsfd_m2l_vr_512x1__hix_SW | loop | 242.3 (o[132]) | 396.6 (di0[0]) | 0 | ins | FAIL | no |
| physical/s81_engc_tiles/results/el1011-engc-ws-pke-a804fc09b-tc-cl/views/ot_engc_t_ws | ot_engc_t_ws | loop | 242.3 (b1_d[0]) | 243.6 (f_hr[119]) | 0 | lib est | FAIL | no |
| physical/s81_ph_views/closed/dsfd_coll_p2_lane_pa | dsfd_coll_p2_lane_pa | loop | 242.0 (lo_d[2]) | 228.8 (r_r[0]) | 0 | lib est | FAIL | no |
| physical/s81_engc_tiles/results/el1011-engc-pbc-b-109a69d35-tc-cl/views/ot_engc_t_pbc | ot_engc_t_pbc | loop | 240.8 (x_a[7]) | 266.8 (x_d[56]) | 0 | lib est | FAIL | no |
| physical/s81_engc_tiles/views/ot_engc_t_pbc | ot_engc_t_pbc | loop | 240.8 (x_a[7]) | 266.8 (x_d[56]) | 0 | lib est | FAIL | no |
| physical/ref_tile/dsfd_vm_fsr_m5_pm/views/dsfd_vm_fsr | dsfd_vm_fsr | loop | 237.1 (o_d[14]) | 171.6 (i_d[3011]) | 0 | ins | FAIL | no |
| physical/s81_ph_views/closed/dsfd_vm_wfc_ep | dsfd_vm_wfc_ep | loop | 236.4 (t_srq[512]) | 242.8 (m_od[510]) | 0 | lib est | FAIL | no |
| physical/s81_pq_hier/results/el1011-pqc-qb-b-cc60cd537-tc-cl/views/ot_pqc_t_qb | ot_pqc_t_qb | loop | 235.6 (hq1[74]) | 261.9 (hw_sv[0]) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81pq_aq_math_native/views/ot_s81_pq_aq_math_native | ot_s81_pq_aq_math_native | loop | 234.8 (y[46]) | 382.0 (s15_e[2]) | 0 | ins | FAIL | no |
| physical/s81_ph_views/closed/dsfd_coll_mtp_lane | dsfd_coll_mtp_lane | loop | 234.1 (lo_d[448]) | 224.9 (f_lflt[1]) | 0 | lib est | FAIL | no |
| physical/ref_tile/ot_dsrom_aq12t_m5/views/ot_dsrom_aq12t | ot_dsrom_aq12t | loop | 232.7 (q[122]) | 259.4 (x[223]) | 0 | ins | FAIL | no |
| physical/ref_tile/dsfd_vm_fcc_m5/views/dsfd_vm_fcc | dsfd_vm_fcc | loop | 230.7 (s_o[695]) | 169.8 (vwd[24]) | 0 | ins | FAIL | no |
| physical/ref_tile/dscoll_cespn/views/dsfd_coll_cespn | dsfd_coll_cespn | loop | 229.4 (o_d[599]) | 168.7 (i_d[583]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81hc_ctfs_ref/views/ot_s81_hc_ctfs | ot_s81_hc_ctfs | loop | 229.2 (rst_out) | 216.4 (fdm[2494]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_rly_266_sn/views/dsfd_rly_266_SN | dsfd_rly_266_SN | loop | 228.9 (o[27]) | 204.7 (rs) | 0 | ins | FAIL | no |
| physical/s81_ph_views/closed/dsfd_capt_g2 | dsfd_capt_g2 | loop | 228.6 (t_w[281]) | 114.4 (f_row[771]) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81hc_ctnl_l2_ref/views/ot_s81_hc_ctnl_l2 | ot_s81_hc_ctnl_l2 | loop | 228.5 (sq_out[24]) | 178.0 (wb_d[51]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_svciojob_ref/views/dsfd_svcio_job | dsfd_svcio_job | loop | 227.9 (jd[0]) | 183.5 (j[21]) | 0 | ins | FAIL | no |
| physical/s81_ph_views/closed/dsfd_coll_p2_ep | dsfd_coll_p2_ep | loop | 227.8 (c_od[27]) | 245.5 (c_or[0]) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81pq_bc3_ns/views/ot_s81_pq_bc_slice3 | ot_s81_pq_bc_slice3 | loop | 227.5 (q[208]) | 157.2 (d[225]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_markov_chunk7_native/views/ot_s81_markov_chunk7_native | ot_s81_markov_chunk7_native | loop | 227.4 (y[3]) | 278.0 (p[19]) | 0 | ins | FAIL | no |
| physical/s81_ph_views/closed/dsfd_wfc_lnk_b | dsfd_wfc_lnk | loop | 227.3 (t_dw[505]) | 246.9 (f_lor[0]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_rly_283_sn/views/dsfd_rly_283_SN | dsfd_rly_283_SN | loop | 226.9 (o[175]) | 199.5 (rs) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_markov_chunk6_native/views/ot_s81_markov_chunk6_native | ot_s81_markov_chunk6_native | loop | 226.5 (y[12]) | 367.1 (sum[27]) | 0 | ins | FAIL | no |
| physical/s81_die_views/swiglu/view_esum_10/view | ot_dsrom_su_swiglu_lane | loop | 226.5 (a[6]) | 896.3 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81pq_bc1_ns/views/ot_s81_pq_bc_slice1 | ot_s81_pq_bc_slice1 | loop | 226.3 (q[235]) | 157.7 (d[93]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_markov_chunk4_native/views/ot_s81_markov_chunk4_native | ot_s81_markov_chunk4_native | loop | 225.4 (y[13]) | 327.8 (sum[26]) | 0 | ins | FAIL | no |
| physical/ref_tile/dscoll_cesp0/views/dsfd_coll_cesp0 | dsfd_coll_cesp0 | loop | 225.3 (o_d[519]) | 163.8 (i_d[10]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_markov_chunk5_native/views/ot_s81_markov_chunk5_native | ot_s81_markov_chunk5_native | loop | 225.3 (vout) | 355.6 (sum[13]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81pq_bc0_ns/views/ot_s81_pq_bc_slice0 | ot_s81_pq_bc_slice0 | loop | 224.9 (q[285]) | 159.7 (d[141]) | 0 | ins | FAIL | no |
| physical/ref_tile/dsfd_vm_fcc_m5_pipe/views/dsfd_vm_fcc | dsfd_vm_fcc | loop | 224.5 (s_o[231]) | 166.7 (vwd[362]) | 0 | ins | FAIL | no |
| physical/s81_pq_hier/results/el1011-pqc-qb-pka-5e6ab1fda-tc-cl/views/ot_pqc_t_qb | ot_pqc_t_qb | loop | 224.4 (hq1[166]) | 225.4 (aqi_d[0]) | 0 | lib est | FAIL | no |
| physical/dsrom_s81_ctx/q_z20c_h20/views/ot_v41_rom_elem_q_qx_w10 | ot_v41_rom_elem_q_qx_w10 | store | 224.3 (perr[0]) | 529.6 (cfg_a[4]) | 0 | lib est | FAIL | no |
| physical/dsrom_s81_ctx/q_z20c_h400/views/ot_v41_rom_elem_q_qx_w10 | ot_v41_rom_elem_q_qx_w10 | store | 224.3 (perr[0]) | 529.6 (cfg_a[4]) | 0 | lib est | FAIL | no |
| physical/dsrom_s81_frame/r9_f19224/views/ot_v41_rom_elem_q_qx_w10 | ot_v41_rom_elem_q_qx_w10 | store | 224.3 (perr[0]) | 529.6 (cfg_a[4]) | 0 | lib est | FAIL | no |
| physical/dsrom_s81_frame/r9m215_f19224/views/ot_v41_rom_elem_q_qx_w10 | ot_v41_rom_elem_q_qx_w10 | store | 224.3 (perr[0]) | 529.6 (cfg_a[4]) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81pq_bc2_ns/views/ot_s81_pq_bc_slice2 | ot_s81_pq_bc_slice2 | loop | 224.3 (q[273]) | 157.2 (d[234]) | 0 | ins | FAIL | no |
| physical/ref_tile/dscoll_ceso/views/dsfd_coll_ceso | dsfd_coll_ceso | loop | 224.1 (bw_d[185]) | 167.9 (i_d[76]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81hc_ctnl_l3_ref/views/ot_s81_hc_ctnl_l3 | ot_s81_hc_ctnl_l3 | loop | 224.1 (acc_out[14]) | 196.6 (fdx[45]) | 0 | ins | FAIL | no |
| physical/s81_pq_hier/results/el1011-pqc-qb-pke-a804fc09b-tc-cl/views/ot_pqc_t_qb | ot_pqc_t_qb | loop | 224.0 (hq1[166]) | 225.4 (aqi_d[0]) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81_markov_chunk1_native/views/ot_s81_markov_chunk1_native | ot_s81_markov_chunk1_native | loop | 223.7 (bad) | 375.6 (sum[30]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_markov_chunk3_native/views/ot_s81_markov_chunk3_native | ot_s81_markov_chunk3_native | loop | 223.7 (y[3]) | 329.1 (sum[26]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_rly_63_wn/views/dsfd_rly_63_WN | dsfd_rly_63_WN | loop | 223.7 (o[1]) | 185.1 (rs) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_rly_283_we/views/dsfd_rly_283_WE | dsfd_rly_283_WE | loop | 222.7 (o[254]) | 235.9 (rs) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_rly_266_we/views/dsfd_rly_266_WE | dsfd_rly_266_WE | loop | 222.2 (o[232]) | 234.1 (rs) | 0 | ins | FAIL | no |
| physical/ref_tile/dsfd_ctrl_pc_m5/views/dsfd_ctrl_pc | dsfd_ctrl_pc | loop | 221.9 (r_data[132]) | 108.2 (rq[331]) | 0 | ins | FAIL | no |
| physical/s81_ph_views/closed/dsfd_capt_ctl | dsfd_capt_ctl | loop | 221.5 (t_k[722]) | 108.9 (f_ctl[53]) | 0 | lib est | FAIL | no |
| physical/s81_ph_views/closed/dsfd_svcio_job | dsfd_svcio_job | loop | 221.1 (jd[0]) | 168.9 (j[7]) | 0 | lib est | FAIL | no |
| physical/s81_ph_views/closed/dsfd_engram_lkp | dsfd_engram_lkp | loop | 220.8 (fault) | 366.7 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/dscoll_cesx/views/dsfd_coll_cesx | dsfd_coll_cesx | loop | 220.6 (o_d[108]) | 158.9 (i_d[313]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_rly_63_ws/views/dsfd_rly_63_WS | dsfd_rly_63_WS | loop | 220.6 (o[29]) | 104.3 (rs) | 0 | ins | FAIL | no |
| physical/dsrom_fh_safe/closed/glue | ot_dsrom_head_bundle_glue | loop | 220.3 (xsb[163]) | 251.1 (a_row_flat[60]) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81_rly_54_we/views/dsfd_rly_54_WE | dsfd_rly_54_WE | loop | 220.3 (o[12]) | 145.0 (i[34]) | 0 | ins | FAIL | no |
| physical/s81_pq_hier/results/el1011-pqc-qb-a-cc60cd537-tc-cl/views/ot_pqc_t_qb | ot_pqc_t_qb | loop | 219.7 (hq0[208]) | 225.3 (aqi_d[0]) | 0 | lib est | FAIL | no |
| physical/s81_pq_hier/views/ot_pqc_t_qb | ot_pqc_t_qb | loop | 219.7 (hq0[208]) | 225.3 (aqi_d[0]) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81_markov_pair_native/views/ot_s81_markov_pair_native | ot_s81_markov_pair_native | loop | 219.0 (y[21]) | 398.9 (b[27]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_rly_63_we/views/dsfd_rly_63_WE | dsfd_rly_63_WE | loop | 216.9 (o[14]) | 198.9 (rs) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_markov_chunk0_native/views/ot_s81_markov_chunk0_native | ot_s81_markov_chunk0_native | loop | 216.8 (y[12]) | 395.9 (p[28]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_markov_fold_native/views/ot_s81_markov_fold_native | ot_s81_markov_fold_native | loop | 215.0 (y[6]) | 391.8 (x[20]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81pq_aq_common_native/views/ot_s81_pq_aq_common_native | ot_s81_pq_aq_common_native | loop | 214.8 (s15_e[2]) | 256.4 (s0_x[736]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_markov_chunk2_native/views/ot_s81_markov_chunk2_native | ot_s81_markov_chunk2_native | loop | 214.4 (y[22]) | 289.1 (sum[30]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_rly_63_se/views/dsfd_rly_63_SE | dsfd_rly_63_SE | loop | 214.1 (o[25]) | 217.0 (rs) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_markov_join_native/views/ot_s81_markov_join_native | ot_s81_markov_join_native | loop | 213.4 (y[21]) | 391.1 (head[26]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81_markov_mul_native/views/ot_s81_markov_mul_native | ot_s81_markov_mul_native | loop | 210.7 (y[12]) | 438.1 (b[11]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81su_smt_hb1_ref/views/dsfd_su_t_smt | dsfd_su_t_smt | loop | 207.0 (o_d[668]) | 266.3 (dn_p[2555]) | 0 | ins | FAIL | no |
| physical/ref_tile/pqc_aq12t_rt/views/ot_dsrom_aq12t | ot_dsrom_aq12t | loop | 206.4 (q[118]) | 252.6 (x[223]) | 0 | ins | FAIL | no |
| physical/ref_tile/dsfd_capt_cd/views/dsfd_capt_cd | dsfd_capt_cd | loop | 203.9 (t_cd[7]) | 207.7 (f_st[2]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81hc_caq_ref/views/ot_s81_hc_caq | ot_s81_hc_caq | loop | 203.4 (wd[108]) | 253.6 (odd) | 0 | ins | FAIL | no |
| physical/ref_tile/s81su_smt_hb2_ref/views/dsfd_su_t_smt | dsfd_su_t_smt | loop | 201.6 (o_d[783]) | 318.7 (dn_p[2558]) | 0 | ins | FAIL | no |
| physical/hbm_export_revisions_1013/mtp-rtt512-f9r10-d23p1-09dc8fad4-hm10/ot_dsrom_mtp_lrx_rtt | ot_dsrom_mtp_lrx_rtt | loop | 200.1 (l_ready) | 336.8 (c_ready) | 0 | lib est | FAIL | no |
| physical/mtp_link_rtt/view_f9r10_d23p1_09dc8fad4/view | ot_dsrom_mtp_lrx_rtt | loop | 200.1 (l_ready) | 336.8 (c_ready) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81su_qne_ref/views/dsfd_su_t_qne | dsfd_su_t_qne | loop | 191.3 (y[221]) | 234.9 (i_x[218]) | 0 | ins | FAIL | no |
| physical/s81_ph_views/closed/ot_dsrom_wfc_tokpipe_stg | ot_dsrom_wfc_tokpipe_stg | store | 180.5 (core_user[7]) | 209.6 (vm_rq[412]) | 0 | ins | FAIL | no |
| physical/s81_die_views/views/m221pq/dsfd_r2l_vr_1024x1__ha_SW | dsfd_r2l_vr_1024x1__ha_SW | loop | 178.0 (o[326]) | 398.0 (di0[0]) | 0 | ins | FAIL | no |
| physical/s81_ph_views/closed/dsfd_svc_stn | dsfd_svc_stn | loop | 174.1 (od_ed[509]) | 225.2 (od_er[0]) | 0 | lib est | FAIL | no |
| physical/variant_fill/window-column128-halfwrite-distributed-6bb5fd3da-vf-lvt/view/view | ot_dsrom_window_column_halfwrite_distributed | loop | 174.1 (read_data[29]) | 399.4 (read_addr[2]) | 0 | lib est | FAIL | no |
| physical/s81_die_views/bf_compact199/ot_v41_bf_col | ot_v41_bf_col | loop | 170.0 (pnseg[2]) | 279.8 (i2x_q1[39]) | 0 | lib est | FAIL | no |
| physical/s81_die_views/views/m221pq/dsfd_r2l_vr_512x1__hsel | dsfd_r2l_vr_512x1__hsel | loop | 169.4 (o[102]) | 384.2 (di0[0]) | 0 | ins | FAIL | no |
| physical/s81_pq_hier/results/el1011-pqc-ix-a-cc60cd537-tc-cl/views/ot_pqc_t_ix | ot_pqc_t_ix | loop | 168.0 (bt_d[61]) | 333.7 (par) | 0 | lib est | FAIL | no |
| physical/s81_die_views/views/m221pq/dsfd_r2l_vr_512x1__hcol | dsfd_r2l_vr_512x1__hcol | loop | 167.6 (o[504]) | 358.0 (di0[0]) | 0 | ins | FAIL | no |
| physical/dsrom_window_columns/m6/ot_dsrom_window_column_128/view | ot_dsrom_window_column_128 | loop | 163.3 (read_data[41]) | 384.9 (read_v) | 0 | lib est | FAIL | no |
| physical/ref_tile/dsfd_vm_fcw_m5/views/dsfd_vm_fcw | dsfd_vm_fcw | loop | 161.3 (t_ks[6]) | 239.4 (rni) | 0 | ins | FAIL | no |
| physical/ref_tile/s81hc_ctfx_ref/views/ot_s81_hc_ctfx | ot_s81_hc_ctfx | loop | 160.7 (fdx[180]) | 248.4 (rst_in) | 0 | ins | FAIL | no |
| physical/s81_pq_hier/results/el1011-pqc-ix-c-648e3800a-tc-cl/views/ot_pqc_t_ix | ot_pqc_t_ix | loop | 159.9 (bt_d[59]) | 340.7 (par) | 0 | lib est | FAIL | no |
| physical/s81_pq_hier/views/ot_pqc_t_ix | ot_pqc_t_ix | loop | 159.9 (bt_d[59]) | 340.7 (par) | 0 | lib est | FAIL | no |
| physical/s81_ph_views/closed/dsfd_svcio_od | dsfd_svcio_od | loop | 154.1 (od_r[1]) | 281.6 (od_v[2]) | 0 | lib est | FAIL | no |
| physical/s81_ph_views/closed/dsfd_engram_sink | dsfd_engram_sink | loop | 141.8 (wr_en) | 409.6 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81hc_cntree_ref/views/ot_s81_hc_cntree | ot_s81_hc_cntree | loop | 140.0 (ss[24]) | 221.5 (c_ex[443]) | 0 | ins | FAIL | no |
| physical/ref_tile/s81hc_cntreeh2_ref/views/ot_s81_hc_cntree | ot_s81_hc_cntree | loop | 140.0 (ss[24]) | 221.5 (c_ex[443]) | 0 | ins | FAIL | no |
| physical/s81_ph_views/closed/dsfd_mtp_hrow_bank | dsfd_mtp_hrow_bank | loop | 123.8 (t_d[883]) | 234.4 (f_w[509]) | 0 | lib est | FAIL | no |
| physical/dsrom_fh_quad/lane_tc_lvt/6ce4b64fd/view | ot_hdc_v41_fh_sram_lane_hardened | loop | 116.2 (rd_valid) | 243.1 (bank_id[4]) | 0 | lib est | FAIL | no |
| physical/s81_ph_views/closed/dsfd_dw_ep_c | dsfd_dw_ep_c | loop | 97.2 (c_done[4]) | 250.8 (vh[0]) | 0 | lib est | FAIL | no |
| physical/s81_ph_views/closed/dsfd_dw_ep_s | dsfd_dw_ep_s | loop | 88.6 (c_done[4]) | 234.3 (vh[0]) | 0 | lib est | FAIL | no |
| physical/ref_tile/s81su_kvt_ref/views/dsfd_su_t_kvt | dsfd_su_t_kvt | loop | 219.2 (e_d[1622]) | 169.4 (dn_d[1215]) | 0 | ins | PASS | yes |
| physical/ref_tile/s81hc_cryys_ref/views/ot_s81_hc_cryys | ot_s81_hc_cryys | loop | 197.3 (p_y[162]) | 165.6 (y_s[235]) | 0 | ins | PASS | yes |
| physical/ref_tile/s81su_kvr_ref/views/dsfd_su_t_kvr | dsfd_su_t_kvr | loop | 183.1 (o_f) | 124.2 (i_eps[15]) | 0 | ins | PASS | yes |
| physical/s81_ph_views/closed/ot_p2h_fadd16 | ot_p2h_fadd16 | loop | 161.8 (t_y[476]) | 118.8 (f_ab[480]) | 0 | ins | PASS | yes |
| physical/ref_tile/s81su_kvp_ref/views/dsfd_su_t_kvp | dsfd_su_t_kvp | loop | 157.1 (y[155]) | 125.4 (i_x[60]) | 0 | ins | PASS | yes |
| physical/ref_tile/hrow5_ing/views/dsfd_mtp_hrow_ing | dsfd_mtp_hrow_ing | loop | 155.7 (t_wc[1032]) | 119.5 (f_hp[61]) | 0 | ins | PASS | yes |
| physical/ref_tile/s81su_kve_ref/views/dsfd_su_t_kve | dsfd_su_t_kve | loop | 155.5 (y[19]) | 128.0 (i_x[2]) | 0 | ins | PASS | yes |
| physical/s81_ph_views/closed/ot_p2h_xport | ot_p2h_xport | loop | 125.3 (t_inr[1]) | 122.6 (f_in[1208]) | 0 | ins | PASS | yes |
| physical/ref_tile/s81_rly_68_ew/views/dsfd_rly_68_EW | dsfd_rly_68_EW | loop | 219.8 (o[28]) | 160.6 (rs) | 0 | ins | PASS | no |
| physical/ref_tile/dscoll_cesl/views/dsfd_coll_cesl | dsfd_coll_cesl | loop | 219.7 (o_y[22]) | 164.2 (i_d[42]) | 0 | ins | PASS | no |
| physical/ref_tile/s81_rly_63_ns/views/dsfd_rly_63_NS | dsfd_rly_63_NS | loop | 219.0 (o[18]) | 100.0 (rs) | 0 | ins | PASS | no |
| physical/ref_tile/s81_rly_66_sn/views/dsfd_rly_66_SN | dsfd_rly_66_SN | loop | 218.9 (o[5]) | 106.4 (rs) | 0 | ins | PASS | no |
| physical/ref_tile/s81_rly_63_es/views/dsfd_rly_63_ES | dsfd_rly_63_ES | loop | 218.5 (o[53]) | 148.4 (rs) | 0 | ins | PASS | no |
| physical/ref_tile/s81_rly_54_ew/views/dsfd_rly_54_EW | dsfd_rly_54_EW | loop | 218.4 (o[36]) | 165.9 (rs) | 0 | ins | PASS | no |
| physical/ref_tile/s81hc_crxh2_ref/views/ot_s81_hc_crx | ot_s81_hc_crx | loop | 217.7 (o_rd[64]) | 133.3 (e_rv[3]) | 0 | ins | PASS | no |
| physical/ref_tile/s81_rly_66_ns/views/dsfd_rly_66_NS | dsfd_rly_66_NS | loop | 217.4 (o[65]) | 106.1 (rs) | 0 | ins | PASS | no |
| physical/ref_tile/s81su_qnr_ref/views/dsfd_su_t_qnr | dsfd_su_t_qnr | loop | 217.4 (o_f) | 116.5 (i_eps[10]) | 0 | ins | PASS | no |
| physical/ref_tile/s81hc_crx_ref/views/ot_s81_hc_crx | ot_s81_hc_crx | loop | 216.9 (o_rd[1]) | 127.7 (e_rd[62]) | 0 | ins | PASS | no |
| physical/ref_tile/s81_rly_63_ne/views/dsfd_rly_63_NE | dsfd_rly_63_NE | loop | 214.4 (o[22]) | 102.1 (rs) | 0 | ins | PASS | no |
| physical/ref_tile/dsfd_be_r55_m5/views/dsfd_be_r55 | dsfd_be_r55 | loop | 214.3 (o[37]) | 150.3 (i[21]) | 0 | ins | PASS | no |
| physical/ref_tile/s81su_sml_u65_ref/views/dsfd_su_t_sml | dsfd_su_t_sml | loop | 214.2 (o_e[7]) | 171.8 (i_sink[14]) | 0 | ins | PASS | no |
| physical/s81_ph_views/closed/dsfd_colt_mrg | dsfd_colt_mrg | loop | 213.3 (vd[475]) | 131.4 (f_w[1651]) | 0 | lib est | PASS | no |
| physical/ref_tile/dsfd_hrow_r23_m5/views/dsfd_hrow_r23 | dsfd_hrow_r23 | loop | 213.2 (o[0]) | 146.2 (i[19]) | 0 | ins | PASS | no |
| physical/ref_tile/s81su_qnt_cb32_ref/views/dsfd_su_t_qnt | dsfd_su_t_qnt | loop | 212.2 (e_eps[10]) | 138.6 (dn_v[2]) | 0 | ins | PASS | no |
| physical/ref_tile/s81hc_pad_f5r1_ref/views/ot_s81_hc_pad_f5r1 | ot_s81_hc_pad_f5r1 | loop | 211.4 (r_o[687]) | 148.7 (r_i[455]) | 0 | ins | PASS | no |
| physical/ref_tile/dsfd_hrow_r15_m5/views/dsfd_hrow_r15 | dsfd_hrow_r15 | loop | 209.9 (o[8]) | 145.7 (i[2]) | 0 | ins | PASS | no |
| physical/ref_tile/s81_rly_15_sn/views/dsfd_rly_15_SN | dsfd_rly_15_SN | loop | 209.5 (o[4]) | 105.1 (rs) | 0 | ins | PASS | no |
| physical/ref_tile/s81_rly_15_en/views/dsfd_rly_15_EN | dsfd_rly_15_EN | loop | 207.3 (o[9]) | 94.3 (i[10]) | 0 | ins | PASS | no |
| physical/ref_tile/s81pq_fault_native/views/ot_s81_pq_fault_pin | ot_s81_pq_fault_pin | loop | 206.9 (fault) | 149.0 (faults[11]) | 0 | ins | PASS | no |
| physical/s81_ph_views/closed/dsfd_wfc_tok_hard | dsfd_wfc_tok_hard | loop | 205.2 (t_ft[0]) | 174.6 (f_pr[28]) | 0 | lib est | PASS | no |
| physical/ref_tile/s81su_smd_u65_ref/views/dsfd_su_t_smd | dsfd_su_t_smd | loop | 203.7 (o_o[24]) | 170.2 (i_csd[50]) | 0 | ins | PASS | no |
| physical/ref_tile/s81su_qbtl_ref/views/dsfd_su_t_qbtl | dsfd_su_t_qbtl | loop | 202.3 (e_t[11]) | 171.6 (dn_dl[1070]) | 0 | ins | PASS | no |
| physical/ref_tile/s81su_swth_ref/views/dsfd_su_t_swth | dsfd_su_t_swth | loop | 202.2 (e_dh[1142]) | 169.8 (dn_dh[2339]) | 0 | ins | PASS | no |
| physical/ref_tile/dsfd_vm_fxs_m5/views/dsfd_vm_fxs | dsfd_vm_fxs | loop | 200.8 (s_o[245]) | 184.5 (w_v[0]) | 0 | ins | PASS | no |
| physical/ref_tile/s81su_swtl_ref/views/dsfd_su_t_swtl | dsfd_su_t_swtl | loop | 200.1 (e_dl[621]) | 169.7 (dn_dl[2796]) | 0 | ins | PASS | no |
| physical/ref_tile/dsfd_die_r1_m5/views/dsfd_die_r1 | dsfd_die_r1 | loop | 197.8 (o) | 144.1 (i) | 0 | ins | PASS | no |
| physical/ref_tile/s81_rly_2_ew/views/dsfd_rly_2_EW | dsfd_rly_2_EW | loop | 197.1 (o[0]) | 79.7 (i[0]) | 0 | ins | PASS | no |
| physical/ref_tile/s81_rly_2_nw/views/dsfd_rly_2_NW | dsfd_rly_2_NW | loop | 197.0 (o[0]) | 78.6 (i[1]) | 0 | ins | PASS | no |
| physical/ref_tile/s81_rly_2_es/views/dsfd_rly_2_ES | dsfd_rly_2_ES | loop | 196.2 (o[1]) | 79.5 (i[1]) | 0 | ins | PASS | no |
| physical/ref_tile/s81_rly_2_sn/views/dsfd_rly_2_SN | dsfd_rly_2_SN | loop | 196.2 (o[1]) | 78.4 (i[1]) | 0 | ins | PASS | no |
| physical/ref_tile/s81_rly_2_ws/views/dsfd_rly_2_WS | dsfd_rly_2_WS | loop | 195.2 (o[1]) | 78.2 (i[1]) | 0 | ins | PASS | no |
| physical/ref_tile/s81_rly_2_ns/views/dsfd_rly_2_NS | dsfd_rly_2_NS | loop | 195.1 (o[1]) | 78.8 (i[1]) | 0 | ins | PASS | no |
| physical/ref_tile/s81hc_ctrn_ref/views/ot_s81_hc_ctrn | ot_s81_hc_ctrn | loop | 194.8 (rd_out[785]) | 175.0 (rdm[256]) | 0 | ins | PASS | no |
| physical/ref_tile/s81su_smc_ref/views/dsfd_su_t_smc | dsfd_su_t_smc | loop | 194.4 (o_l) | 173.9 (i_e[97]) | 0 | ins | PASS | no |
| physical/ref_tile/s81_rly_2_we/views/dsfd_rly_2_WE | dsfd_rly_2_WE | loop | 194.3 (o[1]) | 79.1 (i[1]) | 0 | ins | PASS | no |
| physical/ref_tile/dsfd_be_f16_m5/views/dsfd_be_f16 | dsfd_be_f16 | loop | 194.0 (o[7]) | 127.8 (rn) | 0 | ins | PASS | no |
| physical/ref_tile/s81_rly_1_ew/views/dsfd_rly_1_EW | dsfd_rly_1_EW | loop | 193.9 (o) | 80.0 (i) | 0 | ins | PASS | no |
| physical/ref_tile/s81_rly_2_ne/views/dsfd_rly_2_NE | dsfd_rly_2_NE | loop | 193.7 (o[1]) | 78.4 (i[0]) | 0 | ins | PASS | no |
| physical/ref_tile/s81_rly_1_we/views/dsfd_rly_1_WE | dsfd_rly_1_WE | loop | 192.1 (o) | 79.8 (i) | 0 | ins | PASS | no |
| physical/ref_tile/dsfd_die_rstsync_m5/views/dsfd_die_rstsync | dsfd_die_rstsync | loop | 191.9 (rn) | 104.7 (rst) | 0 | ins | PASS | no |
| physical/ref_tile/s81hc_ctnl_l1_ref/views/ot_s81_hc_ctnl_l1 | ot_s81_hc_ctnl_l1 | loop | 191.3 (sq_out[13]) | 155.0 (acc_in[27]) | 0 | ins | PASS | no |
| physical/s81_die_views/views/m221pq/dsfd_l2r_vr_564x1__hx_W | dsfd_l2r_vr_564x1__hx_W | loop | 188.5 (od[429]) | 142.2 (i[174]) | 0 | ins | PASS | no |
| physical/s81_ph_views/closed/dsfd_mtp_seq_rtt_61b4bc729 | dsfd_mtp_seq_rtt | loop | 185.5 (t_td[36]) | 116.5 (f_rv[0]) | 0 | lib est | PASS | no |
| physical/s81_ph_views/closed/dsfd_mtp_seq_rtt_c | dsfd_mtp_seq_rtt | loop | 183.2 (t_rg[0]) | 120.2 (f_rv[0]) | 0 | lib est | PASS | no |
| physical/s81_ph_views/closed/dsfd_mtp_seq_rtt_d | dsfd_mtp_seq_rtt | loop | 183.2 (t_rg[0]) | 120.2 (f_rv[0]) | 0 | lib est | PASS | no |
| physical/s81_ph_views/closed/dsfd_svcio_x | dsfd_svcio_x | loop | 179.9 (xd[185]) | 120.1 (x_d[198]) | 0 | lib est | PASS | no |
| physical/s81_ph_views/closed/dsfd_host_sd | dsfd_host_sd | loop | 175.1 (host_ack_n[2]) | 165.8 (o_d[74]) | 0 | lib est | PASS | no |
| physical/s81_ph_views/closed/dsfd_svch_rly | dsfd_svch_rly | loop | 171.7 (o_d[4198]) | 169.8 (i_d[3375]) | 0 | lib est | PASS | no |
| physical/s81_ph_views/closed/dsfd_vm_mtp_ep | dsfd_vm_mtp_ep | loop | 170.6 (c_hv[0]) | 188.6 (c_hr[0]) | 0 | lib est | PASS | no |
| physical/s81_pq_hier/results/el1011-pqc-ret-c-648e3800a-tc-cl/views/ot_pqc_t_ret | ot_pqc_t_ret | loop | 168.1 (w_addr[96]) | 103.5 (r_fp32[25]) | 0 | lib est | PASS | no |
| physical/s81_pq_hier/views/ot_pqc_t_ret | ot_pqc_t_ret | loop | 168.1 (w_addr[96]) | 103.5 (r_fp32[25]) | 0 | lib est | PASS | no |
| physical/ref_tile/s81hc_cpad_ref/views/ot_s81_hc_cpad | ot_s81_hc_cpad | loop | 167.0 (crd_o[797]) | 126.6 (fv_i[4]) | 0 | ins | PASS | no |
| physical/s81_pq_hier/results/el1011-pqc-ret-d-648e3800a-tc-cl/views/ot_pqc_t_ret | ot_pqc_t_ret | loop | 166.6 (w_data[124]) | 105.9 (r_bf16[6]) | 0 | lib est | PASS | no |
| physical/ref_tile/s81hc_ctnl_l0_ref/views/ot_s81_hc_ctnl_l0 | ot_s81_hc_ctnl_l0 | loop | 165.2 (hrq[109]) | 125.9 (wb_d[34]) | 0 | ins | PASS | no |
| physical/hbm_export_revisions_1013/mtp-mtp_seq-c-c67a71fe5-tc/dsfd_mtp_seq | dsfd_mtp_seq | loop | 163.3 (t_rg[0]) | 69.9 (f_rv[0]) | 0 | lib est | PASS | no |
| physical/s81_ph_views/closed/dsfd_mtp_seq_c | dsfd_mtp_seq | loop | 163.3 (t_rg[0]) | 69.9 (f_rv[0]) | 0 | lib est | PASS | no |
| physical/s81_ph_views/closed/dsfd_svc_pc | dsfd_svc_pc | loop | 162.2 (qr_data[168]) | 75.3 (qrq[322]) | 0 | lib est | PASS | no |
| physical/ref_tile/s81hc_pad_r6_ref/views/ot_s81_hc_pad_r6 | ot_s81_hc_pad_r6 | loop | 161.6 (d_o[801]) | 114.1 (d_i[1767]) | 0 | ins | PASS | no |
| physical/s81_ph_views/closed/dsfd_mtp_seq_b | dsfd_mtp_seq | loop | 161.3 (t_rg[0]) | 71.9 (f_rv[0]) | 0 | lib est | PASS | no |
| physical/ref_tile/dsfd_vm_fsr/views/dsfd_vm_fsr | dsfd_vm_fsr | loop | 157.7 (o_we[0]) | 169.9 (i_d[970]) | 0 | ins | PASS | no |
| physical/s81_pq_hier/results/el1011-pqc-bc-e-73f4017b5-tc-cl/views/ot_pqc_t_bc | ot_pqc_t_bc | loop | 157.6 (q[277]) | 111.4 (d[885]) | 0 | lib est | PASS | no |
| physical/s81_pq_hier/views/ot_pqc_t_bc | ot_pqc_t_bc | loop | 157.6 (q[277]) | 111.4 (d[885]) | 0 | lib est | PASS | no |
| physical/ref_tile/s81hc_ctpl_ref/views/ot_s81_hc_ctpl | ot_s81_hc_ctpl | loop | 156.9 (hov) | 137.1 (fdx[37]) | 0 | ins | PASS | no |
| physical/s81_pq_hier/results/el1011-pqc-bc-pka-5e6ab1fda-tc-cl/views/ot_pqc_t_bc | ot_pqc_t_bc | loop | 156.9 (q[277]) | 111.4 (d[885]) | 0 | lib est | PASS | no |
| physical/ref_tile/s81hc_pad_f8_ref/views/ot_s81_hc_pad_f8 | ot_s81_hc_pad_f8 | loop | 155.3 (d_o[385]) | 125.6 (v_i[6]) | 0 | ins | PASS | no |
| physical/ref_tile/s81hc_pad_r5_ref/views/ot_s81_hc_pad_r5 | ot_s81_hc_pad_r5 | loop | 153.7 (d_o[254]) | 114.0 (d_i[1650]) | 0 | ins | PASS | no |
| physical/ref_tile/dsfd_vm_fxr_m5/views/dsfd_vm_fxr | dsfd_vm_fxr | loop | 153.3 (o[158]) | 168.4 (i[15]) | 0 | ins | PASS | no |
| physical/ref_tile/s81_svcjoin_ref/views/dsfd_svc_join | dsfd_svc_join | loop | 150.3 (j_cmd[21]) | 142.9 (rst) | 0 | ins | PASS | no |
| physical/ref_tile/dsfd_vm_frr_m5/views/dsfd_vm_frr | dsfd_vm_frr | loop | 150.1 (o[200]) | 161.8 (i[402]) | 0 | ins | PASS | no |
| physical/ref_tile/s81hc_pad_meta2_ref/views/ot_s81_hc_pad_meta2 | ot_s81_hc_pad_meta2 | loop | 149.2 (e_o[323]) | 110.0 (e_i[14]) | 0 | ins | PASS | no |
| physical/ref_tile/dsfd_vm_frm_m5/views/dsfd_vm_frm | dsfd_vm_frm | loop | 149.1 (a_o[11]) | 165.3 (r_i[213]) | 0 | ins | PASS | no |
| physical/s81_pq_hier/results/el1011-pqc-xin-b-73f4017b5-tc-cl/views/ot_pqc_t_xin | ot_pqc_t_xin | loop | 148.8 (q[841]) | 97.5 (d[894]) | 0 | lib est | PASS | no |
| physical/ref_tile/dsfd_vm_fxb_m5/views/dsfd_vm_fxb | dsfd_vm_fxb | loop | 147.9 (o[191]) | 164.9 (i[139]) | 0 | ins | PASS | no |
| physical/ref_tile/s81su_smd_ref/views/dsfd_su_t_smd | dsfd_su_t_smd | loop | 147.6 (o_f) | 131.4 (i_pv) | 0 | ins | PASS | no |
| physical/ref_tile/dsfd_vm_fxa_m5/views/dsfd_vm_fxa | dsfd_vm_fxa | loop | 147.3 (o[221]) | 161.8 (i[115]) | 0 | ins | PASS | no |
| physical/s81_pq_hier/results/el1011-pqc-xin-a-73f4017b5-tc-cl/views/ot_pqc_t_xin | ot_pqc_t_xin | loop | 145.7 (q[20]) | 95.4 (d[743]) | 0 | lib est | PASS | no |
| physical/s81_pq_hier/views/ot_pqc_t_xin | ot_pqc_t_xin | loop | 145.7 (q[20]) | 95.4 (d[743]) | 0 | lib est | PASS | no |
| physical/ref_tile/s81su_smr_ref/views/dsfd_su_t_smr | dsfd_su_t_smr | loop | 145.5 (o_nmb[1]) | 122.6 (i_vv) | 0 | ins | PASS | no |
| physical/ref_tile/s81su_sml_ref/views/dsfd_su_t_sml | dsfd_su_t_sml | loop | 144.8 (o_e[0]) | 116.4 (i_mv) | 0 | ins | PASS | no |
| physical/ref_tile/s81su_qnh_ref/views/dsfd_su_t_qnh | dsfd_su_t_qnh | loop | 144.0 (s_d[17]) | 117.2 (p_d[274]) | 0 | ins | PASS | no |
| physical/s81_ph_views/closed/dsfd_coll_p2_lane_ba | dsfd_coll_p2_lane_ba | loop | 143.8 (t_flt[0]) | 151.3 (f_lflt[2]) | 0 | lib est | PASS | no |
| physical/s81_ph_views/closed/dsfd_vm_p2_ep | dsfd_vm_p2_ep | loop | 133.8 (c_l0r[0]) | 95.8 (c_l0d[118]) | 0 | lib est | PASS | no |
| physical/s81_ph_views/closed/dsfd_cap_mtp_ep | dsfd_cap_mtp_ep | loop | 133.6 (c_rr[0]) | 97.5 (c_rd[96]) | 0 | lib est | PASS | no |
| physical/s81_ph_views/closed/dsfd_svc_join | dsfd_svc_join | loop | 125.8 (c_done[0]) | 182.0 (rst[0]) | 0 | ins | PASS | no |
| physical/s81_ph_views/closed/dsfd_coll_ck | dsfd_coll_ck | loop | 114.2 (rst_serial[0]) | None (None) | 0 | lib est | PASS | no |
| physical/s81_die_views/views/dsfd_stnh_566x1 | dsfd_stnh_566x1 | loop | 112.5 (do0[482]) | 43.8 (di0[104]) | 0 | ins | PASS | no |
| physical/s81_die_views/views/dsfd_stnh_512x1 | dsfd_stnh_512x1 | loop | 110.6 (do0[305]) | 44.0 (di0[170]) | 0 | ins | PASS | no |
| physical/s81_die_views/views/dsfd_stnh_514x1 | dsfd_stnh_514x1 | loop | 109.2 (do0[75]) | 42.3 (di0[83]) | 0 | ins | PASS | no |
| physical/s81_die_views/views/dsfd_stnv_512x1 | dsfd_stnv_512x1 | loop | 108.2 (do0[226]) | 41.9 (di0[239]) | 0 | ins | PASS | no |
| physical/s81_die_views/views/dsfd_stnv_514x1 | dsfd_stnv_514x1 | loop | 108.2 (do0[414]) | 40.4 (di0[192]) | 0 | ins | PASS | no |
| physical/s81_ph_views/closed/dsfd_ctrl_ctr | dsfd_ctrl_ctr | loop | 99.8 (st[1]) | 62.6 (co_e[0]) | 0 | lib est | PASS | no |
| physical/s81_die_views/hbglue_tc/6ce4b64fd/view | ot_s81_head_delay8x32 | loop | 88.5 (q[25]) | 26.2 (d[24]) | 0 | lib est | PASS | no |
| physical/s81_ph_views/macros/ot_s81_pll_bb | ot_s81_pll_bb | store | None (None) | None (None) | 0 | lib est | PASS | no |
| physical/s81_ph_views/mtp/macros/ot_sram_1r1w_512x64_m4_r2c2 | ot_sram_1r1w_512x64_m4_r2c2 | store | None (None) | 107.0 (w_ce_in) | 0 | lib est | PASS | no |

## hbm

| view | cell | closed by | worst launch ps (pin) | worst capture ps (pin) | comb | R src | pass | used |
|---|---|---|---:|---:|---:|---|---|---|
| physical/ref_tile/hgi_dma_back_b2_ref/views/ot_hgi_dma_back | ot_hgi_dma_back | loop | 381.6 (wd[1948]) | 332.9 (vr2r[512]) | 0 | ins | FAIL | yes |
| physical/ref_tile/hgi_seq_fe/views/ot_hgi_seq_fe | ot_hgi_seq_fe | loop | 358.1 (fe_s1_n[11]) | 311.8 (f_req_rdy) | 0 | ins | FAIL | yes |
| physical/ref_tile/hgi_seq_be/views/ot_hgi_seq_be | ot_hgi_seq_be | loop | 337.4 (be_jl_entry[0]) | 255.1 (db_loff[10]) | 0 | ins | FAIL | yes |
| physical/ref_tile/coll_tkm_tile_cx/views/ot_hgi_coll_tkm_tile | ot_hgi_coll_tkm_tile | loop | 324.5 (up_out[55]) | 416.5 (ins_b[26]) | 0 | ins | FAIL | yes |
| physical/ref_tile/hcoll_port_cx/views/ot_hcoll_port | ot_hcoll_port | loop | 319.0 (rb_d[518]) | 464.6 (rst_n) | 0 | ins | FAIL | yes |
| physical/ref_tile/hgi_sv_lane2_pf/views/ot_hgi_sv_lane2 | ot_hgi_sv_lane2 | loop | 293.6 (lsw_d[431]) | 472.7 (rst_n) | 0 | ins | FAIL | yes |
| physical/ref_tile/sfu_lane_ring3_rt/views/ot_su12_sfu | ot_su12_sfu | loop | 242.2 (kv_waddr[23]) | 417.6 (rst_n) | 0 | ins | FAIL | yes |
| physical/hbm_accel_die_views/mtp_hgi | hgi_mtp_native | store | 184.8 (t_cmdproc[43]) | 210.1 (f_cmdproc[82]) | 0 | lib est | FAIL | yes |
| physical/ref_tile/hgi_sv_lane2/views/ot_hgi_sv_lane2 | ot_hgi_sv_lane2 | loop | 344.1 (wwq[230]) | 451.8 (rst_n) | 0 | ins | FAIL | cell |
| physical/hbm_accel_die_views/svc/split/hfd_svc_SE_s8 | hfd_svc_SE_s8 | store | 343.1 (wo[206]) | 100.7 (wi[31]) | 0 | lib est | FAIL | cell |
| physical/hbm_accel_die_views/svc/split/hfd_svc_SE_s6 | hfd_svc_SE_s6 | store | 339.3 (phy[1588]) | 140.5 (wi[52]) | 0 | lib est | FAIL | cell |
| physical/hbm_accel_die_views/svc/split/hfd_svc_SE_s7 | hfd_svc_SE_s7 | store | 280.1 (phy[966]) | 112.0 (wi[59]) | 0 | lib est | FAIL | cell |
| physical/ref_tile/hbm_native_mtp_pinaccess_m5_1014/views/hgi_mtp_native | hgi_mtp_native | loop | 266.1 (t_cmdproc[43]) | 345.5 (f_cmdproc[139]) | 0 | ins | FAIL | cell |
| physical/ref_tile/idx_hslice_rt_a/views/ot_hdc_v41x_idx_hslice | ot_hdc_v41x_idx_hslice | loop | 263.9 (ko_key[543]) | 215.7 (first) | 0 | ins | FAIL | cell |
| physical/hbm_accel_die_views/svc/split/hfd_svc_SW_s4 | hfd_svc_SW_s4 | store | 260.9 (wo[0]) | 159.1 (wi[26]) | 0 | lib est | FAIL | cell |
| physical/ref_tile/ot_hdc_v41x_idx_hslice_m5/views/ot_hdc_v41x_idx_hslice | ot_hdc_v41x_idx_hslice | loop | 216.2 (ko_key[483]) | 205.3 (cs_in[30]) | 0 | ins | FAIL | cell |
| physical/hbm_attn_tile_r/quad_b_tc/079f5ee02_pk/view | ot_attn_tile_m6h1q | loop | 489.6 (oy[6]) | 795.2 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/smh_fcis_ref_p45/views/ot_hbm_accel_smh_fc_is | ot_hbm_accel_smh_fc_is | loop | 471.1 (lt1[134]) | 370.8 (k0_mv[28]) | 0 | ins | FAIL | no |
| physical/hbm_accel_die_views/hgi_vm/results/hgi_vm_bta-a7bf28890-tc-cl/view | ot_hgi_vm_btile | loop | 444.2 (u_d[20]) | 386.9 (rst_n) | 0 | lib est | FAIL | no |
| physical/hbm_export_revisions_1013/hgi_vm_bta2-74fdec20c-tc-cl/ot_hgi_vm_btile | ot_hgi_vm_btile | loop | 444.2 (u_d[20]) | 386.9 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/hbm_retry545_ref/views/ot_hbm_link_retry_pipeline | ot_hbm_link_retry_pipeline | loop | 409.2 (in_ready) | 428.0 (in_valid) | 0 | ins | FAIL | no |
| physical/ref_tile/smn_fcxr_ref_fa/views/ot_hbm_accel_smh_fc_xr | ot_hbm_accel_smh_fc_xr | loop | 409.1 (xo[1366]) | 186.9 (xi[902]) | 0 | ins | FAIL | no |
| physical/ref_tile/qw_ovr_ref/views/ot_hgi_qw_ovr | ot_hgi_qw_ovr | loop | 402.9 (row_rst_n) | 182.3 (d_vo) | 0 | ins | FAIL | no |
| physical/hbm_export_revisions_1013/hgi_quant_c360-dedb8a397-tc-cl/ot_hgi_quant_decode | ot_hgi_quant_decode | loop | 395.2 (y[166]) | 361.1 (generic_enable) | 0 | lib est | FAIL | no |
| physical/hgi_quant_generic_20261009/results/hgi_quant_c360/view | ot_hgi_quant_decode | loop | 395.2 (y[166]) | 361.1 (generic_enable) | 0 | lib est | FAIL | no |
| physical/hbm_accel_die_views/stations/hfd_mcast_r5/route_cl | hfd_mcast_r5 | store | 381.0 (t0[606]) | 199.0 (a[1120]) | 0 | lib est | FAIL | no |
| physical/hbm_export_revisions_1013/hgi-coll-tkm-tile-d-7258eeb45-tc-cl/hgi_coll_tkm_tile | hgi_coll_tkm_tile | loop | 379.6 (up_out[276]) | 437.9 (ins_b[141]) | 0 | lib est | FAIL | no |
| physical/ref_tile/hbm_native_no3_observation_hub_m5_1014/views/ot_hbm_native_no3_hub_observe_1014 | ot_hbm_native_no3_hub_observe_1014 | loop | 379.6 (sl3_rst_e) | 424.8 (sl4_q[49]) | 0 | ins | FAIL | no |
| physical/hbm_attn_tile_r/quad_b_tc/6ce4b64fd/view | ot_attn_tile_m6h1q | loop | 375.2 (oy[82]) | 934.4 (rst_n) | 0 | lib est | FAIL | no |
| physical/hbm_attn_tile_r/quad_b_tc/c891a57cf_cg_hm10/view | ot_attn_tile_m6h1q | loop | 375.2 (oy[82]) | 934.4 (rst_n) | 0 | lib est | FAIL | no |
| physical/hbm_export_revisions_1013/hgi_quant_c360p-12c0bd9da-tc-cl/ot_hgi_quant_decode | ot_hgi_quant_decode | loop | 373.1 (y[415]) | 339.8 (header[122]) | 0 | lib est | FAIL | no |
| physical/hgi_quant_generic_20261009/results/hgi_quant_c360p/view | ot_hgi_quant_decode | loop | 373.1 (y[415]) | 339.8 (header[122]) | 0 | lib est | FAIL | no |
| physical/ref_tile/hgi_b2_rqu/views/ot_hgi_b2_rqu | ot_hgi_b2_rqu | loop | 368.2 (rec_b[509]) | 264.4 (rst_n) | 0 | ins | FAIL | no |
| physical/hbm_export_revisions_1013/hgi-coll-tkm-tile-c-7258eeb45-tc-cl/hgi_coll_tkm_tile | hgi_coll_tkm_tile | loop | 359.9 (up_out[264]) | 440.7 (ins_b[68]) | 0 | lib est | FAIL | no |
| physical/hbm_accel_die_views/stations/hfd_mcast_r7/route_cl | hfd_mcast_r7 | store | 359.5 (t0[596]) | 69.9 (a[126]) | 0 | lib est | FAIL | no |
| physical/ref_tile/dma_core_issue_prefix_m5_window_ref/views/ot_hgi_dma_kvw_core_issue_prefix | ot_hgi_dma_kvw_core_issue_prefix | loop | 356.7 (kq[79]) | 460.8 (kw_rdy[2]) | 0 | ins | FAIL | no |
| physical/hbm_accel_smh_views/hier/3c93227a7_cal_h3_ptw_pf/ot_hbm_accel_smh_pt_w | ot_hbm_accel_smh_pt_w | store | 342.3 (rpm[896]) | 264.3 (bin[2015]) | 0 | lib est | FAIL | no |
| physical/hbm_attn_tile_r/quad_b_tc/04424cd9f_pka/view | ot_attn_tile_m6h1q | loop | 337.4 (oy[6]) | 942.9 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/hgi_ix2_qa/views/ot_hgi_idx_ix2_qa | ot_hgi_idx_ix2_qa | loop | 330.5 (qb[667]) | 396.1 (a_v[6]) | 0 | ins | FAIL | no |
| physical/ref_tile/smpub_vmmerge/views/ot_hgi_sm_pub_vmmerge | ot_hgi_sm_pub_vmmerge | loop | 328.4 (vmq[57]) | 327.4 (rn) | 0 | ins | FAIL | no |
| physical/hbm_export_revisions_1013/hgi_idx_t4_join-fe-f7cabb9b7-b-tc-cl/hfd_idx_t4_join | hfd_idx_t4_join | loop | 326.9 (fault) | 256.9 (taps[0]) | 0 | lib est | FAIL | no |
| physical/ref_tile/hgi_dfe12edge_lane/views/ot_hgi_dma_front_lane12 | ot_hgi_dma_front_lane12 | loop | 323.4 (beat_valid) | 167.4 (dd[252]) | 0 | ins | FAIL | no |
| physical/ref_tile/smh_pt_w_ref_p45h/views/ot_hbm_accel_smh_pt_w | ot_hbm_accel_smh_pt_w | loop | 322.1 (bk1_n[2068]) | 451.2 (bin[1975]) | 0 | ins | FAIL | no |
| physical/ref_tile/hgi_dfe2_lane/views/ot_hgi_dma_front_lane2 | ot_hgi_dma_front_lane2 | loop | 318.1 (beat_valid) | 176.7 (dd[150]) | 0 | ins | FAIL | no |
| physical/hbm_accel_die_views/b2_dma_kface_ref/face9-COMMIT/ot_hgi_b2_dma_kface | ot_hgi_b2_dma_kface | loop | 309.8 (response[207]) | 317.8 (k_req_rdy) | 0 | ins | FAIL | no |
| physical/ref_tile/hbm_norm_gtile8_ref/views/ot_hbm_norm_gtile8 | ot_hbm_norm_gtile8 | loop | 308.1 (y_o[150]) | 302.8 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/hgi_idx_tk2/views/ot_hgi_idx_tk2 | ot_hgi_idx_tk2 | loop | 304.3 (vmq[321]) | 168.5 (vmr[248]) | 0 | ins | FAIL | no |
| physical/hbm_w2_rb_station_20261006/views_hier/2cf685462_hub_no3a/ot_hbm_w2_stn_hub_no3 | ot_hbm_w2_stn_hub_no3 | loop | 302.9 (sl0_go_repair) | 342.1 (sl4_q[32]) | 0 | lib est | FAIL | no |
| physical/ref_tile/smn_front_n_ref/views/ot_hbm_accel_smh_front_n | ot_hbm_accel_smh_front_n | loop | 300.2 (rout_r0[477]) | 346.4 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/b2_dma_rq_q5_ref/views/ot_hgi_b2_dma_rq | ot_hgi_b2_dma_rq | loop | 298.3 (il_vmq[6]) | 355.3 (pin_m_rdy) | 0 | ins | FAIL | no |
| physical/ref_tile/lkep_rp_ref/views/ot_lkep_rp | ot_lkep_rp | loop | 290.7 (st_rep[1]) | 254.2 (rx_v) | 0 | ins | FAIL | no |
| physical/ref_tile/lkep_tx_shared_ref/views/ot_lkep_tx_shared | ot_lkep_tx_shared | loop | 290.1 (b_v) | 433.7 (th_vt[0]) | 0 | ins | FAIL | no |
| physical/hbm_export_revisions_1013/smn_front_s_ref-r1-0720be650/ot_hbm_accel_smh_front_s | ot_hbm_accel_smh_front_s | loop | 290.0 (rout_l3[574]) | 307.7 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/smn_front_s_ref/views/ot_hbm_accel_smh_front_s | ot_hbm_accel_smh_front_s | loop | 290.0 (rout_l3[574]) | 270.1 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/smpub_vmcore/views/ot_hgi_sm_pub_vmcore | ot_hgi_sm_pub_vmcore | loop | 289.9 (n_p[139]) | 308.8 (rn) | 0 | ins | FAIL | no |
| physical/ref_tile/hgi_topk_lane_rt_b/views/ot_hgi_topk_lane_tile | ot_hgi_topk_lane_tile | loop | 287.8 (t_k[2]) | 199.1 (mcr) | 0 | ins | FAIL | no |
| physical/ref_tile/vm_cp_rb2_cx/views/vm_cp_rb2 | vm_cp_rb2 | loop | 273.9 (rd[198]) | 125.5 (wi[1352]) | 0 | ins | FAIL | no |
| physical/hbm_accel_die_views/stations/hfd_meso_r35/route_cl | hfd_meso_r35 | store | 273.3 (b[277]) | 57.1 (a[219]) | 0 | lib est | FAIL | no |
| physical/ref_tile/hgi_ix2_wp/views/ot_hgi_idx_ix2_wp | ot_hgi_idx_ix2_wp | loop | 271.7 (wg_req) | 168.8 (t_r[5]) | 0 | ins | FAIL | no |
| physical/ref_tile/hgi_topk_lane_rt_e/views/ot_hgi_topk_lane_tile | ot_hgi_topk_lane_tile | loop | 270.5 (root[19]) | 230.6 (pd[34]) | 0 | ins | FAIL | no |
| physical/hbm_accel_smh_views/fc_hier/7377947fa_fc_bc/ot_hbm_accel_smh_fc_bc | ot_hbm_accel_smh_fc_bc | loop | 269.6 (k0_mv[12]) | 352.7 (k1_sr[27]) | 0 | lib est | FAIL | no |
| physical/hbm_accel_die_views/b2_dma_land_dp_edge_ref/dp-edge-COMMIT/ot_hgi_b2_dma_land_dp | ot_hgi_b2_dma_land_dp | loop | 269.3 (decoded[114]) | 166.1 (source_format[6]) | 0 | ins | FAIL | no |
| physical/ref_tile/smh_xs_ref_p50/views/ot_hbm_accel_smh_xs | ot_hbm_accel_smh_xs | loop | 269.0 (o_ix[309]) | 356.3 (bk1[1105]) | 0 | ins | FAIL | no |
| physical/ref_tile/hgi_topk_lane_rt_a/views/ot_hgi_topk_lane_tile | ot_hgi_topk_lane_tile | loop | 268.5 (t_k[1]) | 199.8 (ph[0]) | 0 | ins | FAIL | no |
| physical/hbm_accel_die_views/index/native/results/hgi-idx-hslice-a-a791d4196-tc-cl/views/ot_hdc_v41x_idx_chunk_el | ot_hdc_v41x_idx_chunk_el | loop | 267.8 (ko_key[408]) | 206.9 (hid[5]) | 0 | lib est | FAIL | no |
| physical/ref_tile/qw_ovg_ref/views/ot_hgi_qw_ovg | ot_hgi_qw_ovg | loop | 265.9 (x_v) | 219.3 (c_gh[11]) | 0 | ins | FAIL | no |
| physical/ref_tile/smh_fcxl_ref_p40/views/ot_hbm_accel_smh_fc_xl | ot_hbm_accel_smh_fc_xl | loop | 265.5 (xw_w[1517]) | 274.4 (fx_b[817]) | 0 | ins | FAIL | no |
| physical/ref_tile/smh_fcxl_ref_p45/views/ot_hbm_accel_smh_fc_xl | ot_hbm_accel_smh_fc_xl | loop | 265.5 (xw_w[1227]) | 278.6 (fx_b[544]) | 0 | ins | FAIL | no |
| physical/hbm_accel_die_views/b2_dma_groupface_ref/face10-COMMIT/ot_hgi_b2_dma_groupface | ot_hgi_b2_dma_groupface | loop | 263.1 (vr2q[495]) | 154.8 (request[398]) | 0 | ins | FAIL | no |
| physical/ref_tile/hgi_dfe6b_ctrl/views/ot_hgi_dma_front_ctrl6b | ot_hgi_dma_front_ctrl6b | loop | 257.5 (issue_v[0]) | 281.9 (id_v) | 0 | ins | FAIL | no |
| physical/hbm_accel_smh_views/fc_hier/27742d3f8_fc_b/ot_hbm_accel_smh_fc_b | ot_hbm_accel_smh_fc_b | store | 257.3 (bout[1705]) | 241.2 (xi[1899]) | 0 | lib est | FAIL | no |
| physical/ref_tile/qw_dbq_ref/views/ot_hgi_qw_dbq | ot_hgi_qw_dbq | loop | 255.1 (byo[149]) | 108.1 (xb[658]) | 0 | ins | FAIL | no |
| physical/hbm_generic_views/g12_120 | hgi_att_rows_g12_120 | loop | 254.5 (c_id_r) | 308.5 (row_r) | 0 | lib est | FAIL | no |
| physical/ref_tile/smh_xs_ref_p45m/views/ot_hbm_accel_smh_xs | ot_hbm_accel_smh_xs | loop | 254.5 (o_ix[417]) | 254.9 (rl1[734]) | 0 | ins | FAIL | no |
| physical/hbm_accel_smh_views/fc_hier/27742d3f8_fc_xl/ot_hbm_accel_smh_fc_xl | ot_hbm_accel_smh_fc_xl | store | 251.7 (fo_row0[769]) | 351.6 (fx_b[93]) | 0 | lib est | FAIL | no |
| physical/hbm_accel_die_views/stations/hfd_meso_r37/route_cl | hfd_meso_r37 | store | 247.8 (b[245]) | 75.9 (a[157]) | 0 | lib est | FAIL | no |
| physical/ref_tile/smh_own_local_icg_eg_ref/views/ot_smh_own_local_icg_eg | ot_smh_own_local_icg_eg | loop | 247.7 (cut_8870) | 190.4 (cut_8382) | 0 | lib est | FAIL | no |
| physical/hbm_export_revisions_1013/hfd_hc_hub-cons1011-5f27090d5-tc-pd40-hm0-cl/hfd_hc_hub | hfd_hc_hub | loop | 247.2 (hb0[93]) | 222.0 (hq0[159]) | 0 | lib est | FAIL | no |
| physical/ref_tile/hattn_lo_root/views/ot_attn_lo_root | ot_attn_lo_root | loop | 245.8 (root_q[1086]) | 423.1 (ri_s[1475]) | 0 | ins | FAIL | no |
| physical/hbm_accel_die_views/stations/hfd_meso_r1 | hfd_meso_r1 | store | 245.4 (b[780]) | 168.1 (a[1064]) | 0 | lib est | FAIL | no |
| physical/hbm_export_revisions_1013/hbm_retry545_nakh64m6a-c87c01b44-tc-rvt-hm10-cl/ot_hbm_link_retry_pipeline | ot_hbm_link_retry_pipeline | loop | 245.3 (tx_data[426]) | 508.6 (tx_ready) | 0 | lib est | FAIL | no |
| physical/ref_tile/hbm_tkm_native_output_ref2240/views/ot_hfd_tkm_native_output_leaf | ot_hfd_tkm_native_output_leaf | loop | 244.1 (pack_empty) | 168.2 (native_control[5]) | 0 | ins | FAIL | no |
| physical/hbm_accel_die_views/su/lane_pk2/ot_su12_light | ot_su12_light | loop | 243.4 (vm_waddr[4]) | None (None) | 0 | lib est | FAIL | no |
| physical/hbm_export_revisions_1013/hbm_su_lane_pk2-0be5f1bec-tc-cl/ot_su12_light | ot_su12_light | loop | 243.4 (vm_waddr[4]) | None (None) | 0 | lib est | FAIL | no |
| physical/ref_tile/qw_dxl_ref/views/ot_hgi_qw_dxl | ot_hgi_qw_dxl | loop | 241.6 (xs[784]) | 220.2 (x[910]) | 0 | ins | FAIL | no |
| physical/ref_tile/b2_dma_serial_q5_ref/views/ot_hgi_b2_dma_serial | ot_hgi_b2_dma_serial | loop | 241.5 (vmq[323]) | 469.8 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/smh_xs_ref_p45/views/ot_hbm_accel_smh_xs | ot_hbm_accel_smh_xs | loop | 241.5 (o_itag_e[9]) | 280.4 (bk1[1494]) | 0 | ins | FAIL | no |
| physical/ref_tile/sfu_lane_map_ref/views/ot_hgi_sfu_lane_map | ot_hgi_sfu_lane_map | loop | 240.1 (o_pass[111]) | 182.3 (i_pass[441]) | 0 | ins | FAIL | no |
| physical/ref_tile/hbm_gorder_mt_ref/views/ot_hbm_index_global_order_mt | ot_hbm_index_global_order_mt | loop | 237.9 (read_ordinal[3]) | 403.9 (por_n) | 0 | ins | FAIL | no |
| physical/ref_tile/hgi_smmv_eng_rt/views/ot_hgi_smmv | ot_hgi_smmv | loop | 237.2 (dbg_iss_seq[1]) | 243.2 (rec_v) | 0 | ins | FAIL | no |
| physical/ref_tile/hgi_xp_sps/views/ot_hgi_xp_sps | ot_hgi_xp_sps | loop | 234.2 (o_data[404]) | 171.1 (i_data[1012]) | 0 | ins | FAIL | no |
| physical/ref_tile/hgi_topk_heap_rt_b/views/ot_hgi_topk_heap_tile | ot_hgi_topk_heap_tile | loop | 233.9 (root_key[45]) | 194.1 (k[5]) | 0 | ins | FAIL | no |
| physical/hbm_accel_die_views/router | hfd_router | store | 232.0 (eSE[45]) | 162.0 (f_vm[19]) | 0 | lib est | FAIL | no |
| physical/ref_tile/smpub_vmport/views/ot_hgi_sm_pub_vmport | ot_hgi_sm_pub_vmport | loop | 231.5 (vmq[40]) | 230.8 (n_v) | 0 | ins | FAIL | no |
| physical/hbm_accel_die_views/stations/hfd_gath_r25/route_cl | hfd_gath_r25 | store | 230.8 (b[71]) | 139.0 (a2[1063]) | 0 | lib est | FAIL | no |
| physical/hbm_generic_views/g12_140 | hgi_att_rows_g12_140 | loop | 230.8 (cmd_r) | 317.3 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/smpub_smrg_l3/views/ot_hgi_sm_pub_smrg_l3 | ot_hgi_sm_pub_smrg_l3 | loop | 230.7 (o_d[16]) | 257.9 (i_v[1]) | 0 | ins | FAIL | no |
| physical/hbm_accel_die_views/b2_dma_groupface_regkq_ref/regkq-look-COMMIT/ot_hgi_b2_dma_groupface | ot_hgi_b2_dma_groupface | loop | 230.4 (vr2q[29]) | 176.8 (kv_request[487]) | 0 | ins | FAIL | no |
| physical/ref_tile/hgi_ix2_kc/views/ot_hgi_idx_ix2_kc | ot_hgi_idx_ix2_kc | loop | 230.0 (kin[222]) | 171.9 (wp_idle) | 0 | ins | FAIL | no |
| physical/ref_tile/hgi_ix2_kp/views/ot_hgi_idx_ix2_kp | ot_hgi_idx_ix2_kp | loop | 229.0 (c_cr[3]) | 169.9 (c_h[5]) | 0 | ins | FAIL | no |
| physical/ref_tile/hgi_ix2_pk/views/ot_hgi_idx_ix2_pk | ot_hgi_idx_ix2_pk | loop | 229.0 (t_r[61]) | 166.4 (co[39]) | 0 | ins | FAIL | no |
| physical/ref_tile/qw_ovrow_ref/views/ot_hgi_qw_ovrow | ot_hgi_qw_ovrow | loop | 228.8 (o_y[56]) | 242.4 (i_sec[2]) | 0 | ins | FAIL | no |
| physical/ref_tile/hgi_xp_rd_ln/views/ot_hgi_xp_rd_ln | ot_hgi_xp_rd_ln | loop | 228.3 (wrq[29]) | 169.1 (wrr[249]) | 0 | ins | FAIL | no |
| physical/ref_tile/smpub_cmd_quiet/views/ot_hgi_sm_pub_cmd_quiet | ot_hgi_sm_pub_cmd_quiet | loop | 228.2 (cfd[16]) | 210.4 (ft_l[0]) | 0 | ins | FAIL | no |
| physical/ref_tile/hgi_b2_disp/views/ot_hgi_b2_disp | ot_hgi_b2_disp | loop | 226.5 (cb[1020]) | 456.4 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/smpub_smrg_l2/views/ot_hgi_sm_pub_smrg_l2 | ot_hgi_sm_pub_smrg_l2 | loop | 226.0 (o_d[19]) | 246.4 (i_v[0]) | 0 | ins | FAIL | no |
| physical/ref_tile/qw_ovmeta_ref/views/ot_hgi_qw_ovmeta | ot_hgi_qw_ovmeta | loop | 225.9 (o_slot[23]) | 233.3 (i_sec[11]) | 0 | ins | FAIL | no |
| physical/ref_tile/smpub_cmd/views/ot_hgi_sm_pub_cmd | ot_hgi_sm_pub_cmd | loop | 225.9 (pub_fault) | 209.6 (agg_r) | 0 | ins | FAIL | no |
| physical/ref_tile/smpub_cmd_relay/views/ot_hgi_sm_pub_cmd_relay | ot_hgi_sm_pub_cmd_relay | loop | 225.5 (o_data[27]) | 151.2 (i_data[50]) | 0 | ins | FAIL | no |
| physical/hbm_accel_die_views/b2_dma_groupface_owned_ref/owned-wface-COMMIT/ot_hgi_b2_dma_groupface_owned | ot_hgi_b2_dma_groupface_owned | loop | 224.2 (vr2q[512]) | 168.5 (kv_owned) | 0 | ins | FAIL | no |
| physical/ref_tile/hgi_pub_slice_rt/views/ot_hgi_sm_pub_slice | ot_hgi_sm_pub_slice | loop | 224.1 (s_fault) | 498.3 (sid[1]) | 0 | ins | FAIL | no |
| physical/ref_tile/lkep_ti_ref/views/ot_lkep_ti | ot_lkep_ti | loop | 223.9 (m_in_d[523]) | 271.6 (session[3]) | 0 | ins | FAIL | no |
| physical/ref_tile/dma_hold_a_m5_window_ref/views/ot_hgi_dma_kvw_hold | ot_hgi_dma_kvw_hold | loop | 223.5 (d1[182]) | 170.1 (rsp[1323]) | 0 | ins | FAIL | no |
| physical/ref_tile/ctlw_lane2_ref/views/ot_hgi_su_ctlw_lane2 | ot_hgi_su_ctlw_lane2 | loop | 223.4 (lb_o[35]) | 148.9 (d_hi_i[17]) | 0 | ins | FAIL | no |
| physical/ref_tile/hbm_native_fence_bank128_m5_1014/views/ot_hbm_native_fence_bank128 | ot_hbm_native_fence_bank128 | loop | 223.4 (slots[191]) | 160.8 (din[53]) | 0 | ins | FAIL | no |
| physical/ref_tile/hgi_b2_swap_disp_ref/views/ot_hgi_b2_swap_disp_t | ot_hgi_b2_swap_disp_t | loop | 223.0 (dn0[79]) | 247.0 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/qw_rq_ref/views/ot_hgi_qw_rq | ot_hgi_qw_rq | loop | 222.9 (wrq[62]) | 121.4 (wrr[715]) | 0 | ins | FAIL | no |
| physical/ref_tile/hattn_ks_entry/views/ot_attn_ks_entry | ot_attn_ks_entry | loop | 222.8 (ks_r[991]) | 230.3 (ks[919]) | 0 | ins | FAIL | no |
| physical/ref_tile/smh_own_eg_ref/views/ot_smh_own_eg | ot_smh_own_eg | loop | 222.8 (cut_8870) | 240.0 (cut_8382) | 0 | ins | FAIL | no |
| physical/ref_tile/dma_hold_b_m5_window_ref/views/ot_hgi_dma_kvw_hold | ot_hgi_dma_kvw_hold | loop | 222.1 (d0[165]) | 179.1 (rsp[2162]) | 0 | ins | FAIL | no |
| physical/ref_tile/smpub_stream_edge/views/ot_hgi_sm_pub_stream_edge | ot_hgi_sm_pub_stream_edge | loop | 222.0 (o_data[38]) | 225.9 (i_v) | 0 | ins | FAIL | no |
| physical/ref_tile/hgi_ix2_lane/views/ot_hgi_idx_ix2_lane | ot_hgi_idx_ix2_lane | loop | 221.7 (ab_d[158]) | 167.9 (wrr[14]) | 0 | ins | FAIL | no |
| physical/ref_tile/smpub_smrg_l1/views/ot_hgi_sm_pub_smrg_l1 | ot_hgi_sm_pub_smrg_l1 | loop | 221.7 (o_d[25]) | 240.8 (rn) | 0 | ins | FAIL | no |
| physical/hbm_link_retry_pipeline_20261009/view_wpin_hm10 | ot_hbm_link_retry_pipeline | loop | 221.2 (tx_data[261]) | 477.4 (tx_ready) | 0 | lib est | FAIL | no |
| physical/ref_tile/lkep_face_ref/views/hfd_lk_ep_face | hfd_lk_ep_face | loop | 218.3 (core_session[21]) | 204.7 (f_lk_rx[559]) | 0 | ins | FAIL | no |
| physical/ref_tile/smpub_egress/views/ot_hgi_sm_pub_egress | ot_hgi_sm_pub_egress | loop | 215.7 (relay_v) | 220.3 (i_v) | 0 | ins | FAIL | no |
| physical/hbm_accel_die_views/index_q/split/hfd_index_q_b4 | hfd_index_q_b4 | store | 215.2 (a3o[439]) | 198.7 (a3i[224]) | 0 | lib est | FAIL | no |
| physical/hbm_export_revisions_1013/hgi-idx-hslice-a-121c75340-tc-cl/ot_hdc_v41x_idx_chunk_el | ot_hdc_v41x_idx_chunk_el | loop | 208.6 (qo_codes[352]) | 210.6 (hid[6]) | 0 | lib est | FAIL | no |
| physical/ref_tile/lkep_status_shared_ref/views/ot_lkep_status_shared | ot_lkep_status_shared | loop | 207.4 (st_replays[23]) | 407.7 (rp_flat[70]) | 0 | ins | FAIL | no |
| physical/hbm_export_revisions_1013/smn_be_eg_ref-r2-b9a29ac93/ot_hbm_accel_smh_be_eg | ot_hbm_accel_smh_be_eg | loop | 205.5 (cgo) | 505.8 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/smn_be_eg_ref/views/ot_hbm_accel_smh_be_eg | ot_hbm_accel_smh_be_eg | loop | 205.5 (cgo) | 479.6 (rst_n) | 0 | ins | FAIL | no |
| physical/hbm_accel_die_views/argmax_hgi | ot_hgi_argmax18_m | store | 202.6 (out_range_fault) | 398.5 (in_bias[21]) | 0 | lib est | FAIL | no |
| physical/hbm_export_revisions_1013/mtprb-hist-ring-p-190e09324-tc/ot_mtp_hist_ring_p | ot_mtp_hist_ring_p | loop | 202.2 (rd_ready) | 323.5 (rst_n) | 0 | lib est | FAIL | no |
| physical/mtp_rollback/views/ot_mtp_hist_ring_p | ot_mtp_hist_ring_p | loop | 202.2 (rd_ready) | 323.5 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/lkep_rx_shared_ref/views/ot_lkep_rx_shared | ot_lkep_rx_shared | loop | 196.3 (r_flit[6]) | 434.4 (oh_vt[1]) | 0 | ins | FAIL | no |
| physical/hbm_accel_die_views/mtp | hfd_mtp | store | 194.4 (p_addr[0]) | 237.1 (cmd_ready) | 0 | lib est | FAIL | no |
| physical/hbm_accel_die_views/mtp_hfd | hfd_mtp_x_stop | store | 194.4 (p_addr[0]) | 237.1 (cmd_ready) | 0 | lib est | FAIL | no |
| physical/hbm_export_revisions_1013/hgi-idx-topk-tile-b-3c5540533-tc-cl/hgi_idx_topk_w8 | hgi_idx_topk_w8 | loop | 193.9 (ext_d[19]) | 256.3 (op_x[0]) | 0 | lib est | FAIL | no |
| physical/hbm_w2_rb_station_20261006/views_hier/7377496ab_slice8_no3_preclose/ot_hbm_w2_stn_slice8 | ot_hbm_w2_stn_slice8 | store | 193.5 (grc_o[2]) | 201.9 (ph4[1]) | 0 | lib est | FAIL | no |
| physical/hbm_norm_split_20261008/views/ot_hbm_norm_grp8 | ot_hbm_norm_grp8 | loop | 192.8 (y[210]) | 225.7 (pre[28]) | 0 | lib est | FAIL | no |
| physical/hgi_sm_pub_views/hier/0317261a2_slice_m6-pd50-cal/ot_hgi_sm_pub_slice | ot_hgi_sm_pub_slice | store | 192.7 (w_v) | 592.6 (sid[2]) | 0 | lib est | FAIL | no |
| physical/hbm_w2_rb_station_20261006/views_hier/7377496ab_slice8_no3/ot_hbm_w2_stn_slice8 | ot_hbm_w2_stn_slice8 | store | 191.5 (grc_o[2]) | 201.7 (ph4[1]) | 0 | lib est | FAIL | no |
| physical/hbm_export_revisions_1013/hgi_qw_dec_s260-ac62227e1-tc-cl/ot_hgi_qw_dec | ot_hgi_qw_dec | loop | 191.2 (y[317]) | 199.0 (rst_n) | 0 | lib est | FAIL | no |
| physical/hgi_quant_wide_views/ac62227e1_dec_s260/ot_hgi_qw_dec | ot_hgi_qw_dec | loop | 191.2 (y[317]) | 199.0 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/hc_lanes_ref/views/ot_hdc_v41x_hcp_lanes | ot_hdc_v41x_hcp_lanes | loop | 190.5 (y[25]) | 209.0 (rst_n) | 0 | ins | FAIL | no |
| physical/hbm_w2_rb_station_20261006/views_hier/c9db5e45bp7pa_slice8_no3/ot_hbm_w2_stn_slice8 | ot_hbm_w2_stn_slice8 | store | 189.7 (grc_o[2]) | 200.4 (ph4[1]) | 0 | lib est | FAIL | no |
| physical/ref_tile/hgi_coll_park_fault_ref/views/ot_hgi_coll_park_fault | ot_hgi_coll_park_fault | loop | 188.6 (ovf) | 201.0 (bank_ovf[1]) | 0 | ins | FAIL | no |
| physical/hbm_w2_rb_station_20261006/views_hier/6fc328026p7_slice8_no3/ot_hbm_w2_stn_slice8 | ot_hbm_w2_stn_slice8 | store | 187.3 (grc_o[2]) | 200.9 (ph4[1]) | 0 | lib est | FAIL | no |
| physical/ref_tile/stn_slice5_no3_rt/views/ot_hbm_w2_stn_slice5 | ot_hbm_w2_stn_slice5 | loop | 183.5 (q[214]) | 236.5 (rst_p) | 0 | ins | FAIL | no |
| physical/hbm_w2_rb_station_20261006/views_hier/7377496ab_slice8_no2/ot_hbm_w2_stn_slice8 | ot_hbm_w2_stn_slice8 | store | 180.7 (grc_o[5]) | 192.3 (ph4[2]) | 0 | lib est | FAIL | no |
| physical/hbm_w2_rb_station_20261006/views_hier/6fc328026p7_slice8_no2/ot_hbm_w2_stn_slice8 | ot_hbm_w2_stn_slice8 | store | 177.1 (grc_o[5]) | 192.4 (ph4[2]) | 0 | lib est | FAIL | no |
| physical/hbm_accel_smh_views/fc_hier/297893a19_fc_is/ot_hbm_accel_smh_fc_is | ot_hbm_accel_smh_fc_is | loop | 176.1 (k1_sr[22]) | 372.7 (k0_mv[15]) | 0 | lib est | FAIL | no |
| physical/hbm_export_revisions_1013/hgi-idx-topk-tile-a-3c5540533-tc-cl/hgi_idx_topk_w8 | hgi_idx_topk_w8 | loop | 175.1 (ext_d[43]) | 232.8 (clr_go) | 0 | lib est | FAIL | no |
| physical/hbm_w2_rb_station_20261006/views_hier/c9db5e45bp7pa_slice8_no2/ot_hbm_w2_stn_slice8 | ot_hbm_w2_stn_slice8 | store | 173.5 (grc_o[5]) | 193.4 (ph4[2]) | 0 | lib est | FAIL | no |
| physical/ref_tile/smn_be_wg_ref/views/ot_hbm_accel_smh_be_wg | ot_hbm_accel_smh_be_wg | loop | 165.4 (qout[44]) | 454.5 (rst_n) | 0 | ins | FAIL | no |
| physical/hbm_export_revisions_1013/hgi-idx-topk-tile-b-f87bdf90d-tc-cl/hgi_idx_topk_w8 | hgi_idx_topk_w8 | loop | 163.7 (ext_d[41]) | 216.8 (k[10]) | 0 | lib est | FAIL | no |
| physical/ref_tile/stn_slice8_no3_rt/views/ot_hbm_w2_stn_slice8 | ot_hbm_w2_stn_slice8 | loop | 157.9 (dout[375]) | 241.2 (ph4[0]) | 0 | ins | FAIL | no |
| physical/hbm_export_revisions_1013/hgi-idx-topk-tile-a-f87bdf90d-tc-cl/hgi_idx_topk_w8 | hgi_idx_topk_w8 | loop | 155.0 (root_key[13]) | 203.6 (k[9]) | 0 | lib est | FAIL | no |
| physical/ref_tile/hattn_hi_merge/views/ot_attn_hi_merge | ot_attn_hi_merge | loop | 149.8 (o[154]) | 342.7 (gov[6]) | 0 | ins | FAIL | no |
| physical/hgi_idx_topk_w8h/views/ot_hgi_topk_heap_tile | ot_hgi_topk_heap_tile | store | 149.5 (root_key[13]) | 209.2 (k[9]) | 0 | lib est | FAIL | no |
| physical/hbm_accel_sm_views/ot_hbm_accel_tc16 | ot_hbm_accel_tc16 | store | 128.6 (fault) | 2984.5 (rst_n) | 0 | lib est | FAIL | no |
| physical/hbm_attn_tile_r/bank_v12/ew544_rec/view | ot_attn_bank_ew544 | loop | 107.8 (q[94]) | 210.5 (d[14]) | 0 | lib est | FAIL | no |
| physical/hbm_attn_tile_r/bank_v11/sn544_recb/view | ot_attn_bank_sn544 | loop | 107.7 (q[22]) | 209.7 (d[429]) | 0 | lib est | FAIL | no |
| physical/hbm_attn_tile_r/bank_v12/sn544_rec/view | ot_attn_bank_sn544 | loop | 107.7 (q[22]) | 209.6 (d[429]) | 0 | lib est | FAIL | no |
| physical/hbm_export_revisions_1013/hbm_attn_bank_ew544-m5pdn-905d2ec04-tc-iotime-h1-cl/ot_attn_bank_ew544 | ot_attn_bank_ew544 | loop | 107.3 (q[523]) | 200.6 (d[15]) | 0 | lib est | FAIL | no |
| physical/hbm_export_revisions_1013/hbm_attn_bank_ew544-cl11a-04424cd9f-tc-iotime-h1-cl/ot_attn_bank_ew544 | ot_attn_bank_ew544 | loop | 106.3 (q[44]) | 244.4 (d[486]) | 0 | lib est | FAIL | no |
| physical/hbm_export_revisions_1013/hbm_attn_bank_sn544-midpdn-15bed538d-tc-iotime-h1-cl/ot_attn_bank_sn544 | ot_attn_bank_sn544 | loop | 105.5 (q[423]) | 205.2 (d[206]) | 0 | lib est | FAIL | no |
| physical/hbm_export_revisions_1013/hbm_attn_bank_sn544-m5pdn-905d2ec04-tc-iotime-h1-cl/ot_attn_bank_sn544 | ot_attn_bank_sn544 | loop | 105.2 (q[423]) | 204.8 (d[206]) | 0 | lib est | FAIL | no |
| physical/hbm_attn_tile_r/bank_v11/ew544_reca/view | ot_attn_bank_ew544 | loop | 97.3 (q[44]) | 244.4 (d[486]) | 0 | lib est | FAIL | no |
| physical/hbm_attn_tile_r/bank_v7/ot_attn_bank_sn544 | ot_attn_bank_sn544 | store | 96.7 (q[423]) | 205.2 (d[206]) | 0 | lib est | FAIL | no |
| physical/hbm_accel_sm_views/ot_hbm_accel_bd_col | ot_hbm_accel_bd_col | store | 95.3 (fault) | 1189.8 (rst_n) | 0 | lib est | FAIL | no |
| physical/ref_tile/hgi_seq_au/views/ot_hgi_seq_au | ot_hgi_seq_au | loop | 213.4 (au_tbl_ok) | 169.7 (fe_s1_n[10]) | 0 | ins | PASS | yes |
| physical/hbm_accel_die_views/hcp/tile_xl/view_hm10-pd55/view | hfd_hc_tile_xl | loop | 202.6 (bc_out[33]) | -16.4 (acc_in[234]) | 0 | lib est | PASS | yes |
| physical/hgi_idx_chunk_h/views/ot_hdc_v41x_idx_hslice | ot_hdc_v41x_idx_hslice | store | 176.2 (ko_key[541]) | 135.0 (hid[2]) | 0 | lib est | PASS | yes |
| physical/hbm_accel_die_views/phy_bb/ot_hbm_host_phy | ot_hbm_host_phy | store | None (None) | None (None) | 0 | lib est | PASS | yes |
| physical/hbm_accel_die_views/sfu/lane/ot_su12_sfu | ot_su12_sfu | store | 217.6 (vm_waddr[20]) | None (None) | 0 | lib est | PASS | cell |
| physical/ref_tile/idx_hslice_rt_b/views/ot_hdc_v41x_idx_hslice | ot_hdc_v41x_idx_hslice | loop | 213.8 (ko_key[404]) | 185.3 (ql_v) | 0 | ins | PASS | cell |
| physical/hbm_accel_die_views/sfu/lane/ot_su12_sfu_ring3_aa5dd28d5 | ot_su12_sfu | store | 184.3 (coll) | None (None) | 0 | lib est | PASS | cell |
| physical/hbm_accel_die_views/b2_dma_vmface_ref/face9-COMMIT/ot_hgi_b2_dma_vmface | ot_hgi_b2_dma_vmface | loop | 218.8 (mover_response[197]) | 180.2 (vmr[248]) | 0 | ins | PASS | no |
| physical/ref_tile/lkep_ts_ref/views/ot_lkep_ts | ot_lkep_ts | loop | 218.1 (tx_d[515]) | 163.0 (m_tx_d[233]) | 0 | ins | PASS | no |
| physical/hbm_w2_rb_station_20261006/views_hier/6fc328026p7_slice5_no2/ot_hbm_w2_stn_slice5 | ot_hbm_w2_stn_slice5 | store | 217.7 (q[250]) | 155.6 (ph4[3]) | 0 | lib est | PASS | no |
| physical/ref_tile/hbm_coll_face512_ref/views/ot_hbm_coll_face_pipe512 | ot_hbm_coll_face_pipe512 | loop | 217.1 (q[413]) | 162.3 (d[420]) | 0 | ins | PASS | no |
| physical/hbm_w2_rb_station_20261006/views_hier/c9db5e45bp7pa_slice5_no2/ot_hbm_w2_stn_slice5 | ot_hbm_w2_stn_slice5 | store | 216.4 (q[250]) | 155.9 (ph4[3]) | 0 | lib est | PASS | no |
| physical/ref_tile/hbm_native_fence_bank32_m5_1014/views/ot_hbm_native_fence_bank32 | ot_hbm_native_fence_bank32 | loop | 215.4 (slots[49]) | 143.7 (din[31]) | 0 | ins | PASS | no |
| physical/hbm_export_revisions_1013/hgi_qw_wq_w38-ac62227e1-tc-cl/ot_hgi_qw_wq | ot_hgi_qw_wq | loop | 211.9 (wwq[199]) | 148.4 (c_slot[14]) | 0 | lib est | PASS | no |
| physical/hgi_quant_wide_views/ac62227e1_wq_w38/ot_hgi_qw_wq | ot_hgi_qw_wq | loop | 211.9 (wwq[199]) | 148.4 (c_slot[14]) | 0 | lib est | PASS | no |
| physical/ref_tile/smpub_credit/views/ot_hgi_sm_pub_credit4 | ot_hgi_sm_pub_credit4 | loop | 210.5 (o_cr[3]) | 144.9 (i_cr[2]) | 0 | ins | PASS | no |
| physical/hbm_w2_rb_station_20261006/views_hier/7377496ab_slice5_no2/ot_hbm_w2_stn_slice5 | ot_hbm_w2_stn_slice5 | store | 210.4 (q[24]) | 155.0 (ph4[3]) | 0 | lib est | PASS | no |
| physical/ref_tile/hbm_native_fence_bank9_m5_1014/views/ot_hbm_native_fence_bank9 | ot_hbm_native_fence_bank9 | loop | 210.1 (slots[7]) | 141.7 (rst_n) | 0 | ins | PASS | no |
| physical/hbm_export_revisions_1013/hgi_qw_rq_w85-ac62227e1-tc-cl/ot_hgi_qw_rq | ot_hgi_qw_rq | loop | 208.6 (gq[499]) | 126.9 (wrr[1027]) | 0 | lib est | PASS | no |
| physical/hgi_quant_wide_views/ac62227e1_rq_w85/ot_hgi_qw_rq | ot_hgi_qw_rq | loop | 208.6 (gq[499]) | 126.9 (wrr[1027]) | 0 | lib est | PASS | no |
| physical/ref_tile/hbm_native_fence_bank18_m5_1014/views/ot_hbm_native_fence_bank18 | ot_hbm_native_fence_bank18 | loop | 208.6 (slots[25]) | 144.9 (rst_n) | 0 | ins | PASS | no |
| physical/hbm_export_revisions_1013/hgi_qw_dec_s260-2b1df5142-tc-cl/ot_hgi_qw_dec | ot_hgi_qw_dec | loop | 206.5 (y[255]) | 188.8 (rst_n) | 0 | lib est | PASS | no |
| physical/hgi_quant_wide_views/2b1df5142_dec_s260/ot_hgi_qw_dec | ot_hgi_qw_dec | loop | 206.5 (y[255]) | 188.8 (rst_n) | 0 | lib est | PASS | no |
| physical/ref_tile/sfu_chain_rta/views/ot_hdc_v41x_sfu_chain | ot_hdc_v41x_sfu_chain | loop | 204.5 (y_exp[23]) | 135.9 (r[17]) | 0 | ins | PASS | no |
| physical/ref_tile/hbm_native_fence_bank8_m5_1014/views/ot_hbm_native_fence_bank8 | ot_hbm_native_fence_bank8 | loop | 203.3 (slots[4]) | 139.4 (rst_n) | 0 | ins | PASS | no |
| physical/ref_tile/smpub_return_d1/views/ot_hgi_sm_pub_return_d1 | ot_hgi_sm_pub_return_d1 | loop | 202.0 (o_done) | 145.0 (i_fault) | 0 | ins | PASS | no |
| physical/ref_tile/hbm_native_fence_bank1_m5_1014/views/ot_hbm_native_fence_bank1 | ot_hbm_native_fence_bank1 | loop | 201.5 (slots[1]) | 139.2 (rst_n) | 0 | ins | PASS | no |
| physical/ref_tile/hbm_coll_reduce_lane_ref2240/views/ot_hcoll_reduce_lane8 | ot_hcoll_reduce_lane8 | loop | 200.9 (reply[6]) | 161.0 (operands[41]) | 0 | ins | PASS | no |
| physical/hbm_accel_die_views/su/tile_xl/view_fe_hm0-pd45/view | hfd_su_tile_xl | loop | 200.0 (bc_out[1311]) | -11.0 (acc_in[406]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/su/tile_xl/view_fe_hm10-pd55/view | hfd_su_tile_xl | loop | 196.5 (bc_out[1322]) | 8.4 (acc_in[203]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_gath_r10 | hfd_gath_r10 | store | 196.3 (b[1586]) | 150.5 (a[130]) | 0 | lib est | PASS | no |
| physical/hbm_accel_smh_views/hier/3c93227a7_calhb45_h3_tcl/ot_hbm_accel_smh_tcl | ot_hbm_accel_smh_tcl | store | 196.1 (lfault) | 66.6 (i_v) | 0 | lib est | PASS | no |
| physical/ref_tile/smpub_return_d3/views/ot_hgi_sm_pub_return_d3 | ot_hgi_sm_pub_return_d3 | loop | 194.7 (o_done) | 144.2 (i_fault) | 0 | ins | PASS | no |
| physical/ref_tile/smpub_return_d4/views/ot_hgi_sm_pub_return_d4 | ot_hgi_sm_pub_return_d4 | loop | 194.1 (o_fault) | 144.3 (i_fault) | 0 | ins | PASS | no |
| physical/ref_tile/smpub_return_d2/views/ot_hgi_sm_pub_return_d2 | ot_hgi_sm_pub_return_d2 | loop | 193.7 (o_fault) | 143.9 (i_fault) | 0 | ins | PASS | no |
| physical/hbm_w2_rb_station_20261006/views_hier/7377496ab_slice5_no3/ot_hbm_w2_stn_slice5 | ot_hbm_w2_stn_slice5 | store | 192.8 (q[253]) | 169.6 (ph4[2]) | 0 | lib est | PASS | no |
| physical/ref_tile/smpub_reset/views/ot_hgi_sm_pub_reset | ot_hgi_sm_pub_reset | loop | 192.5 (rn) | 101.3 (rst_n_in) | 0 | ins | PASS | no |
| physical/ref_tile/smpub_reset_hop/views/ot_hgi_sm_pub_reset_hop | ot_hgi_sm_pub_reset_hop | loop | 189.6 (o_rn) | 100.1 (i_rn) | 0 | ins | PASS | no |
| physical/hbm_w2_rb_station_20261006/views_hier/6fc328026p7_slice5_no3/ot_hbm_w2_stn_slice5 | ot_hbm_w2_stn_slice5 | store | 187.9 (q[272]) | 169.2 (ph4[2]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_gath_r8 | hfd_gath_r8 | store | 187.6 (b[13]) | 150.8 (t0[66]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r3 | hfd_stn_r3 | store | 187.3 (b[40]) | 39.8 (a[21]) | 0 | lib est | PASS | no |
| physical/ref_tile/b2_dma_kvw_hold_closed_a/views | ot_hgi_dma_kvw_hold | store | 184.7 (d0[10]) | 183.1 (rsp[784]) | 0 | ins | PASS | no |
| physical/ref_tile/sfu_chain_rtb/views/ot_hdc_v41x_sfu_chain | ot_hdc_v41x_sfu_chain | loop | 179.7 (y_exp[29]) | 130.5 (r[24]) | 0 | ins | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r39/route_cl | hfd_stn_r39 | store | 177.6 (b[324]) | 64.6 (a[1683]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/index/native/results/hgi-idx-hslice-b-a791d4196-tc-cl/views/ot_hdc_v41x_idx_chunk_el | ot_hdc_v41x_idx_chunk_el | loop | 176.2 (ko_key[541]) | 135.0 (hid[2]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/cmdproc/view_s | hfd_cmdproc_s | store | 170.6 (xt[1]) | 76.3 (xb[12]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r16 | hfd_stn_r16 | store | 169.8 (b[27]) | 62.0 (a[115]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r33/route_cl | hfd_stn_r33 | store | 169.6 (b[138]) | 172.6 (a[229]) | 0 | lib est | PASS | no |
| physical/hbm_accel_smh_views/hier/3c93227a7_calhb45_h3_tct/ot_hbm_accel_smh_tct | ot_hbm_accel_smh_tct | store | 165.7 (fault) | 69.7 (sum_i[220]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r38/route_cl | hfd_stn_r38 | store | 165.5 (b[334]) | 118.8 (a[110]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_cdist_r14 | hfd_cdist_r14 | store | 164.7 (t3[77]) | 103.1 (a[418]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r34/route_cl | hfd_stn_r34 | store | 164.1 (b[103]) | 73.7 (a[295]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r26 | hfd_stn_r26 | store | 163.9 (b[2158]) | 56.9 (a[955]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r22 | hfd_stn_r22 | store | 163.5 (b[432]) | 62.3 (a[292]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_cdist_r15 | hfd_cdist_r15 | store | 162.7 (t3[76]) | 37.6 (a[244]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r19/route_cl | hfd_stn_r19 | store | 161.3 (b[159]) | 64.6 (a[871]) | 0 | lib est | PASS | no |
| physical/ref_tile/smh_pt_e_ref_p40s/views/ot_hbm_accel_smh_pt_e | ot_hbm_accel_smh_pt_e | loop | 159.7 (bout[1610]) | 146.0 (bm[925]) | 0 | ins | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r30 | hfd_stn_r30 | store | 159.2 (b[253]) | 64.0 (a[181]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r13 | hfd_stn_r13 | store | 159.0 (b[327]) | 65.7 (a[360]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r18 | hfd_stn_r18 | store | 158.8 (b[594]) | 57.6 (a[204]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r21 | hfd_stn_r21 | store | 158.6 (b[45]) | 61.6 (a[437]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_meso_r28 | hfd_meso_r28 | store | 158.2 (b[429]) | 84.7 (a[55]) | 0 | lib est | PASS | no |
| physical/ref_tile/qw_daq_ref/views/ot_hgi_qw_daq | ot_hgi_qw_daq | loop | 157.8 (y[231]) | 140.2 (xa[95]) | 0 | ins | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r31 | hfd_stn_r31 | store | 157.6 (b[159]) | 73.6 (a[5]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r4 | hfd_stn_r4 | store | 156.2 (b[1968]) | 55.6 (a[373]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_meso_r32 | hfd_meso_r32 | store | 154.1 (b[175]) | 164.4 (a[73]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r12 | hfd_stn_r12 | store | 154.1 (b[246]) | 58.7 (a[273]) | 0 | lib est | PASS | no |
| physical/ref_tile/smh_tcl_ref_p45/views/ot_hbm_accel_smh_tcl | ot_hbm_accel_smh_tcl | loop | 153.5 (sum_o[168]) | 117.0 (i_x[62]) | 0 | ins | PASS | no |
| physical/ref_tile/smh_tct_ref_p45/views/ot_hbm_accel_smh_tct | ot_hbm_accel_smh_tct | loop | 152.1 (y[4]) | 117.3 (sum_i[78]) | 0 | ins | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r17 | hfd_stn_r17 | store | 151.3 (b[112]) | 103.3 (a[9]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r27 | hfd_stn_r27 | store | 151.1 (b[189]) | 59.8 (a[417]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r29 | hfd_stn_r29 | store | 150.5 (b[388]) | 65.4 (a[293]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r20 | hfd_stn_r20 | store | 150.2 (b[751]) | 61.1 (a[190]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r11 | hfd_stn_r11 | store | 148.8 (b[1699]) | 60.9 (a[206]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r23 | hfd_stn_r23 | store | 148.8 (b[419]) | 72.3 (a[223]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r36/route_cl | hfd_stn_r36 | store | 148.4 (b[143]) | 70.5 (a[110]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/barrier | hfd_barrier | store | 145.2 (t_cmdproc[9]) | 175.5 (rst[0]) | 0 | lib est | PASS | no |
| physical/ref_tile/qw_wq_ref/views/ot_hgi_qw_wq | ot_hgi_qw_wq | loop | 145.1 (wwq[61]) | 114.6 (c_v[3]) | 0 | ins | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_gath_r9/route_cl | hfd_gath_r9 | store | 144.2 (b[736]) | 83.6 (a[30]) | 0 | lib est | PASS | no |
| physical/ref_tile/smh_bdc_ref_p50/views/ot_hbm_accel_smh_bdc | ot_hbm_accel_smh_bdc | loop | 144.2 (otag[2]) | 129.5 (i_v) | 0 | ins | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_gath_r24 | hfd_gath_r24 | store | 142.3 (b[590]) | 96.8 (t0[203]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r0 | hfd_stn_r0 | store | 135.3 (b[1038]) | 59.1 (a[1015]) | 0 | lib est | PASS | no |
| physical/hbm_accel_smh_views/fc_hier/27742d3f8_fc_t/ot_hbm_accel_smh_fc_t | ot_hbm_accel_smh_fc_t | store | 129.3 (r0a[816]) | 102.0 (li[482]) | 0 | lib est | PASS | no |
| physical/ref_tile/b2_dma_kvw_hold_closed_b/views | ot_hgi_dma_kvw_hold | store | 129.1 (d1[3]) | 118.7 (rsp[3862]) | 0 | ins | PASS | no |
| physical/hbm_accel_smh_views/hier/3c93227a7_cal_h3_bdc3/ot_hbm_accel_smh_bdc | ot_hbm_accel_smh_bdc | store | 119.2 (y[19]) | 65.0 (i_v) | 0 | lib est | PASS | no |
| physical/hbm_accel_smh_views/hier/3c93227a7_calhb45_h3_pte_pf/ot_hbm_accel_smh_pt_e | ot_hbm_accel_smh_pt_e | store | 112.4 (rout[0]) | 150.6 (rpm[1393]) | 0 | lib est | PASS | no |
| physical/hbm_accel_smh_views/hier/790e9cdd1_bdc_pd45_hm000/ot_hbm_accel_smh_bdc | ot_hbm_accel_smh_bdc | store | 107.5 (otag[3]) | 107.8 (i_x[100]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/stations/hfd_stn_r2 | hfd_stn_r2 | store | 107.1 (b[41]) | 156.3 (a[29]) | 0 | lib est | PASS | no |
| physical/hbm_export_revisions_1013/hbm_attn_bank_sn136-midpdn-15bed538d-tc-iotime-h1-cl/ot_attn_bank_sn136 | ot_attn_bank_sn136 | loop | 106.2 (q[124]) | 170.8 (d[78]) | 0 | lib est | PASS | no |
| physical/hbm_export_revisions_1013/hbm_attn_bank_sn136-cl12-6ee746757-tc-iotime-h1-cl/ot_attn_bank_sn136 | ot_attn_bank_sn136 | loop | 105.9 (q[124]) | 167.9 (d[39]) | 0 | lib est | PASS | no |
| physical/hbm_export_revisions_1013/hbm_attn_bank_sn136-cl11b-ac0cd0588-tc-iotime-h1-cl/ot_attn_bank_sn136 | ot_attn_bank_sn136 | loop | 105.5 (q[124]) | 167.7 (d[24]) | 0 | lib est | PASS | no |
| physical/hbm_export_revisions_1013/hbm_attn_bank_sn136-m5pdn-905d2ec04-tc-iotime-h1-cl/ot_attn_bank_sn136 | ot_attn_bank_sn136 | loop | 105.4 (q[124]) | 170.3 (d[78]) | 0 | lib est | PASS | no |
| physical/hbm_export_revisions_1013/hbm_attn_bank_ew136-m5pdn-905d2ec04-tc-iotime-h1-cl/ot_attn_bank_ew136 | ot_attn_bank_ew136 | loop | 104.7 (q[115]) | 169.0 (d[88]) | 0 | lib est | PASS | no |
| physical/hbm_accel_smh_views/fc_hier/27742d3f8_fc_xr/ot_hbm_accel_smh_fc_xr | ot_hbm_accel_smh_fc_xr | store | 104.0 (lo[100]) | 119.5 (li[329]) | 0 | lib est | PASS | no |
| physical/hbm_accel_smh_views/hier/6f7adfcbc_tcc_pd50_hm000_hb45/ot_hbm_accel_smh_tcc | ot_hbm_accel_smh_tcc | store | 100.9 (y[9]) | 108.2 (i_x[129]) | 0 | lib est | PASS | no |
| physical/hbm_attn_tile_r/bank/ot_attn_bank_ew136 | ot_attn_bank_ew136 | loop | 98.1 (q[103]) | None (None) | 0 | lib est | PASS | no |
| physical/hbm_attn_tile_r/bank/ot_attn_bank_sn136 | ot_attn_bank_sn136 | loop | 97.8 (q[0]) | None (None) | 0 | lib est | PASS | no |
| physical/hbm_attn_tile_r/bank_v7/ot_attn_bank_sn136 | ot_attn_bank_sn136 | store | 97.3 (q[124]) | 170.8 (d[78]) | 0 | lib est | PASS | no |
| physical/hbm_attn_tile_r/bank_v12/sn136_rec/view | ot_attn_bank_sn136 | loop | 96.9 (q[124]) | 167.9 (d[39]) | 0 | lib est | PASS | no |
| physical/hbm_attn_tile_r/bank_v11/sn136_recb/view | ot_attn_bank_sn136 | loop | 96.6 (q[124]) | 167.7 (d[24]) | 0 | lib est | PASS | no |
| physical/hbm_accel_die_views/cmdproc/view_n | hfd_cmdproc_n | store | 72.7 (cNW[653]) | 84.4 (rst[0]) | 0 | lib est | PASS | no |
| physical/asap7_v41x_karb_pc_budget/ot_chip_v41x_hbm_karb_pc_local | ot_chip_v41x_hbm_karb_pc_local | store | None (None) | None (None) | 0 | lib est | PASS | no |
| physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2 | ot_sram_1r1w_512x256_m1_r2c2 | store | None (None) | 107.0 (w_ce_in) | 0 | lib est | PASS | no |

## other

| view | cell | closed by | worst launch ps (pin) | worst capture ps (pin) | comb | R src | pass | used |
|---|---|---|---:|---:|---:|---|---|---|
| physical/ref_tile/ot_pqc_t_srom_m5/views/ot_pqc_t_srom | ot_pqc_t_srom | loop | 458.8 (q[20]) | 465.2 (wa[6]) | 0 | ins | FAIL | no |
| physical/ref_tile/vms_hub/views/ot_vms_hub | ot_vms_hub | loop | 412.7 (cci[259]) | 480.5 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/ot_pqc_t_prom_m5/views/ot_pqc_t_prom | ot_pqc_t_prom | loop | 389.6 (q[5]) | 429.2 (wa[0]) | 0 | ins | FAIL | no |
| physical/ref_tile/vms_bank/views/ot_vms_bank | ot_vms_bank | loop | 385.2 (eg[107]) | 327.6 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/vm_cp_root_cx/views/vm_cp_root | vm_cp_root | loop | 356.3 (cmd0[3]) | 189.0 (rd3[250]) | 0 | ins | FAIL | no |
| physical/ref_tile/vm_cp_slice2/views/vm_cp_slice2 | vm_cp_slice2 | loop | 336.6 (rd[126]) | 168.9 (rst) | 0 | ins | FAIL | no |
| physical/ref_tile/coll_tp8_col_cx/views/ot_coll_tp8_col_tile | ot_coll_tp8_col_tile | loop | 333.1 (lq_hd[0]) | 453.5 (c_pop[5]) | 0 | ins | FAIL | no |
| physical/ref_tile/hbfd_rly_1136_ns/views/hbfd_rly_1136_NS | hbfd_rly_1136_NS | loop | 325.7 (o[1122]) | 164.3 (i[408]) | 0 | ins | FAIL | no |
| physical/ref_tile/hbfd_rly_1136_sn/views/hbfd_rly_1136_SN | hbfd_rly_1136_SN | loop | 322.7 (o[936]) | 165.7 (i[708]) | 0 | ins | FAIL | no |
| physical/ref_tile/ot_pqc_t_ctl16_m5/views/ot_pqc_t_ctl16 | ot_pqc_t_ctl16 | loop | 319.0 (aq_vin) | 208.8 (rom_pq0[63]) | 0 | ins | FAIL | no |
| physical/ref_tile/vms_rstop/views/ot_vms_rstop | ot_vms_rstop | loop | 294.1 (rce[6]) | 314.5 (l_in[2222]) | 0 | ins | FAIL | no |
| physical/ref_tile/hbfd_rly_624_sn/views/hbfd_rly_624_SN | hbfd_rly_624_SN | loop | 288.2 (o[618]) | 161.5 (i[83]) | 0 | ins | FAIL | no |
| physical/ref_tile/hbfd_rly_624_ns/views/hbfd_rly_624_NS | hbfd_rly_624_NS | loop | 288.1 (o[533]) | 164.8 (i[539]) | 0 | ins | FAIL | no |
| physical/ref_tile/coll_col_tile_rt/views/ot_coll_col_tile | ot_coll_col_tile | loop | 280.8 (tx[33]) | 221.1 (c_l1[51]) | 0 | ins | FAIL | no |
| physical/ref_tile/vm_cp_rt2_cx2/views/vm_cp_rt2 | vm_cp_rt2 | loop | 273.2 (cfg[0]) | 130.3 (wi[333]) | 0 | ins | FAIL | no |
| physical/ref_tile/vms_relay_ring/views/ot_vms_relay | ot_vms_relay | loop | 257.9 (f_out[1438]) | 135.8 (f_in[1926]) | 0 | ins | FAIL | no |
| physical/ref_tile/vm_cp_re_cx/views/vm_cp_re | vm_cp_re | loop | 251.0 (rdo[78]) | 176.0 (tap[335]) | 0 | ins | FAIL | no |
| physical/ref_tile/vms_relay_star/views/ot_vms_relay | ot_vms_relay | loop | 248.3 (f_out[1445]) | 131.8 (f_in[1619]) | 0 | ins | FAIL | no |
| physical/ref_tile/ot_pqc_t_qb_m5/views/ot_pqc_t_qb | ot_pqc_t_qb | loop | 240.1 (hq0[138]) | 255.4 (aq_q[231]) | 0 | ins | FAIL | no |
| physical/ref_tile/vms_star/views/ot_vms_star | ot_vms_star | loop | 239.8 (kq[839]) | 219.9 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/vm_cp_fw0_cx/views/vm_cp_fw0 | vm_cp_fw0 | loop | 238.9 (ph[1982]) | 148.3 (f_su_SW[2005]) | 2 | ins | FAIL | no |
| physical/ref_tile/ot_pqc_t_bc_m5/views/ot_pqc_t_bc | ot_pqc_t_bc | loop | 236.1 (q[0]) | 162.2 (d[465]) | 0 | ins | FAIL | no |
| physical/ref_tile/vm_cp_fe0_cx/views/vm_cp_fe0 | vm_cp_fe0 | loop | 235.9 (qSE[565]) | 214.9 (f_su_SE[2045]) | 2 | ins | FAIL | no |
| physical/ref_tile/vm_cp_fw2_cx/views/vm_cp_fw2 | vm_cp_fw2 | loop | 235.9 (xNW[1086]) | 200.8 (tap[26]) | 5 | ins | FAIL | no |
| physical/ref_tile/hbfd_rly_1136_we/views/hbfd_rly_1136_WE | hbfd_rly_1136_WE | loop | 235.7 (o[1135]) | 112.2 (i[620]) | 0 | ins | FAIL | no |
| physical/ref_tile/vm_cp_fe2_cx/views/vm_cp_fe2 | vm_cp_fe2 | loop | 234.9 (xNE[1037]) | 158.6 (ph[2019]) | 5 | ins | FAIL | no |
| physical/ref_tile/hbfd_rly_624_ew/views/hbfd_rly_624_EW | hbfd_rly_624_EW | loop | 229.7 (o[472]) | 113.5 (i[618]) | 0 | ins | FAIL | no |
| physical/ref_tile/hbfd_rly_1136_ew/views/hbfd_rly_1136_EW | hbfd_rly_1136_EW | loop | 228.5 (o[1126]) | 112.8 (i[1128]) | 0 | ins | FAIL | no |
| physical/ref_tile/hbfd_rly_304_ns/views/hbfd_rly_304_NS | hbfd_rly_304_NS | loop | 228.1 (o[4]) | 160.0 (i[201]) | 0 | ins | FAIL | no |
| physical/ref_tile/vm_cp_slice3_cx/views/vm_cp_slice3 | vm_cp_slice3 | loop | 228.0 (rd[135]) | 175.1 (wd[405]) | 0 | ins | FAIL | no |
| physical/ref_tile/vm_cp_rb_cx2/views/vm_cp_rb | vm_cp_rb | loop | 227.6 (eo[648]) | 122.4 (wi[58]) | 0 | ins | FAIL | no |
| physical/ref_tile/hbfd_rly_304_ew/views/hbfd_rly_304_EW | hbfd_rly_304_EW | loop | 227.5 (o[174]) | 105.8 (i[274]) | 0 | ins | FAIL | no |
| physical/ref_tile/hbfd_rly_624_we/views/hbfd_rly_624_WE | hbfd_rly_624_WE | loop | 226.8 (o[582]) | 109.4 (i[472]) | 0 | ins | FAIL | no |
| physical/ref_tile/vm_cp_rwt_cx/views/vm_cp_rwt | vm_cp_rwt | loop | 226.5 (sw[36]) | 192.7 (tap[265]) | 0 | ins | FAIL | no |
| physical/ref_tile/vm_cp_fe1_cx/views/vm_cp_fe1 | vm_cp_fe1 | loop | 226.4 (t_su_SE[274]) | 193.5 (tap[862]) | 5 | ins | FAIL | no |
| physical/ref_tile/hbfd_rly_304_sn/views/hbfd_rly_304_SN | hbfd_rly_304_SN | loop | 225.7 (o[236]) | 161.0 (i[96]) | 0 | ins | FAIL | no |
| physical/ref_tile/vm_cp_fw1_cx/views/vm_cp_fw1 | vm_cp_fw1 | loop | 224.9 (t_su_SW[167]) | 140.6 (ph[921]) | 5 | ins | FAIL | no |
| physical/ref_tile/vm_cp_fe3_cx/views/vm_cp_fe3 | vm_cp_fe3 | loop | 224.8 (ph[977]) | 121.3 (f_su_NE[738]) | 2 | ins | FAIL | no |
| physical/ref_tile/vm_cp_fw3_cx/views/vm_cp_fw3 | vm_cp_fw3 | loop | 224.6 (qNW[516]) | 119.0 (f_su_NW[1114]) | 2 | ins | FAIL | no |
| physical/ref_tile/hbfd_rly_304_we/views/hbfd_rly_304_WE | hbfd_rly_304_WE | loop | 223.8 (o[103]) | 102.6 (i[75]) | 0 | ins | FAIL | no |
| physical/ref_tile/hbfd_rly_136_ew/views/hbfd_rly_136_EW | hbfd_rly_136_EW | loop | 223.5 (o[85]) | 163.5 (i[62]) | 0 | ins | FAIL | no |
| physical/ref_tile/hbfd_rly_136_we/views/hbfd_rly_136_WE | hbfd_rly_136_WE | loop | 221.6 (o[16]) | 164.5 (i[77]) | 0 | ins | FAIL | no |
| physical/ref_tile/vm_cp_rt_cx2/views/vm_cp_rt | vm_cp_rt | loop | 220.6 (eo[179]) | 126.1 (wi[1247]) | 0 | ins | FAIL | no |
| physical/ref_tile/vm_cp_rwa_cx2/views/vm_cp_rwa | vm_cp_rwa | loop | 220.1 (o[1842]) | 127.6 (i[104]) | 0 | ins | FAIL | no |
| physical/ref_tile/hbfd_rly_136_sn/views/hbfd_rly_136_SN | hbfd_rly_136_SN | loop | 219.2 (o[55]) | 224.4 (rs) | 0 | ins | FAIL | no |
| physical/ref_tile/hbfd_rly_136_ns/views/hbfd_rly_136_NS | hbfd_rly_136_NS | loop | 218.9 (o[112]) | 195.9 (rs) | 0 | ins | FAIL | no |
| physical/ref_tile/vms_rcl/views/ot_vms_rcl | ot_vms_rcl | loop | 212.9 (ri1[231]) | 267.4 (rst_n) | 0 | ins | FAIL | no |
| physical/ref_tile/nhb_pbst_ref/views/ot_nhb_pbst | ot_nhb_pbst | loop | 212.1 (sr[413]) | 267.7 (pdata[392]) | 0 | ins | FAIL | no |
| physical/ref_tile/ot_pqc_t_ret_m5/views/ot_pqc_t_ret | ot_pqc_t_ret | loop | 202.3 (w_data[209]) | 194.8 (mdr[210]) | 0 | ins | FAIL | no |
| physical/ref_tile/ot_nhb_pbst_m5/views/ot_nhb_pbst | ot_nhb_pbst | loop | 198.8 (sr[179]) | 275.9 (pdata[371]) | 0 | ins | FAIL | no |
| physical/ref_tile/pqc_ix_rt/views/ot_pqc_t_ix | ot_pqc_t_ix | loop | 153.5 (bt_d[221]) | 360.4 (par) | 0 | ins | FAIL | no |
| physical/ref_tile/hbfd_rly_48_ns/views/hbfd_rly_48_NS | hbfd_rly_48_NS | loop | 217.2 (o[10]) | 152.0 (i[11]) | 0 | ins | PASS | no |
| physical/ref_tile/hbfd_rly_48_ew/views/hbfd_rly_48_EW | hbfd_rly_48_EW | loop | 216.0 (o[38]) | 151.4 (i[23]) | 0 | ins | PASS | no |
| physical/ref_tile/hbfd_rly_48_sn/views/hbfd_rly_48_SN | hbfd_rly_48_SN | loop | 215.5 (o[22]) | 148.8 (i[27]) | 0 | ins | PASS | no |
| physical/ref_tile/hbfd_rly_48_we/views/hbfd_rly_48_WE | hbfd_rly_48_WE | loop | 215.3 (o[23]) | 148.1 (i[35]) | 0 | ins | PASS | no |
| physical/ref_tile/hbfd_rly_8_ew/views/hbfd_rly_8_EW | hbfd_rly_8_EW | loop | 206.5 (o[2]) | 148.5 (i[2]) | 0 | ins | PASS | no |
| physical/ref_tile/hbfd_rly_8_sn/views/hbfd_rly_8_SN | hbfd_rly_8_SN | loop | 205.6 (o[6]) | 147.1 (i[5]) | 0 | ins | PASS | no |
| physical/ref_tile/hbfd_rly_8_ns/views/hbfd_rly_8_NS | hbfd_rly_8_NS | loop | 203.9 (o[0]) | 148.0 (i[2]) | 0 | ins | PASS | no |
| physical/ref_tile/hbfd_rly_8_we/views/hbfd_rly_8_WE | hbfd_rly_8_WE | loop | 203.8 (o[4]) | 145.8 (i[2]) | 0 | ins | PASS | no |
| physical/ref_tile/vm_cp_rwb_cx2/views/vm_cp_rwb | vm_cp_rwb | loop | 197.7 (o[57]) | 93.5 (i[23]) | 0 | ins | PASS | no |
| physical/ref_tile/coll_fold_slice_rt/views/ot_coll_fold_slice | ot_coll_fold_slice | loop | 152.9 (v_out) | 116.6 (src[240]) | 0 | ins | PASS | no |
| physical/ref_tile/nhb_pvlg_ref/views/ot_nhb_pvlg | ot_nhb_pvlg | loop | 152.9 (pf[2]) | 115.5 (rz[0]) | 0 | ins | PASS | no |
| physical/ref_tile/ot_pqc_t_xin_m5/views/ot_pqc_t_xin | ot_pqc_t_xin | loop | 152.7 (q[140]) | 124.0 (d[882]) | 0 | ins | PASS | no |
| physical/ref_tile/nhb_zh_ref/views/ot_nhb_zh | ot_nhb_zh | loop | 148.7 (root[40]) | 164.2 (zs_we[78]) | 0 | ins | PASS | no |
| physical/ref_tile/ot_nhb_zh_m5/views/ot_nhb_zh | ot_nhb_zh | loop | 145.1 (root[56]) | 170.6 (zs_we[80]) | 0 | ins | PASS | no |

## Re-route candidates (fail AND bound by the die)

| design | cell | view | launch | capture | spread | fix |
|---|---|---|---:|---:|---:|---|
| qwen | qkd_cdc_wleaf | physical/ref_tile/qkd_cdc_wleaf_ref/views/qkd_cdc_wleaf | 382.8 | 453.7 | 47.4 | 515 outputs over 220 (worst l_data[150] 382.8): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 2 inputs over 190 (worst h_hand 453.7): single capture flop at each input pin, HB2 pad |
| qwen | qkd_kvwq_leaf_s_w129_m | physical/ref_tile/qkd_kvwq_leaf_s_w129_m/views/qkd_kvwq_leaf_s_w129_m | 231.1 | 365.5 | 27.9 | 48 outputs over 220 (worst w[55] 231.1): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 5 inputs over 190 (worst lane[0] 365.5): single capture flop at each input pin, HB2 pad |
| qwen | qkd_kvwq_ctl_bin | physical/ref_tile/qkd_kvwq_ctl_bin/views/qkd_kvwq_ctl_bin | 230.1 | 392.1 | 35.5 | 12 outputs over 220 (worst durable[22] 230.1): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 1 inputs over 190 (worst rst_n 392.1): the reset input needs its own capture flop at the pin (local reset release) |
| s81 | dsfd_coll_ces0 | physical/ref_tile/dscoll_ces0_sp/views/dsfd_coll_ces0 | 526.6 | 262.6 | 250.8 | 751 outputs over 220 (worst cr_o[5] 526.6): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 2 inputs over 190 (worst rs 262.6): the reset input needs its own capture flop at the pin (local reset release); boundary clock spread 250.8 ps > 80: balance the boundary registers / split the root |
| s81 | dsfd_coll_cesn | physical/ref_tile/dscoll_cesn_sp/views/dsfd_coll_cesn | 493.0 | 250.8 | 188.0 | 700 outputs over 220 (worst cr_o[5] 493.0): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 2 inputs over 190 (worst rs 250.8): the reset input needs its own capture flop at the pin (local reset release); boundary clock spread 188.0 ps > 80: balance the boundary registers / split the root |
| s81 | dsfd_coll_lane_w | physical/ref_tile/dscoll_lane_w_cxea/views/dsfd_coll_lane_w | 439.8 | 494.0 | 114.6 | 240 outputs over 220 (worst flt[2] 439.8): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 741 inputs over 190 (worst lo_v[0] 494.0): single capture flop at each input pin, HB2 pad; boundary clock spread 114.6 ps > 80: balance the boundary registers / split the root |
| s81 | ot_s81_hc_crootr_f | physical/ref_tile/s81hc_crrfw_ref/views/ot_s81_hc_crootr_f | 429.2 | 497.0 | 71.2 | 2281 outputs over 220 (worst ch_fd[1109] 429.2): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 2838 inputs over 190 (worst p_y[1213] 497.0): single capture flop at each input pin, HB2 pad |
| s81 | dsfd_mtp_hrow_cbw | physical/ref_tile/hrow5_cbw_cx/views/dsfd_mtp_hrow_cbw | 422.8 | 440.4 | 89.2 | 991 outputs over 220 (worst t_w[54] 422.8): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 962 inputs over 190 (worst f_w[75] 440.4): single capture flop at each input pin, HB2 pad; boundary clock spread 89.2 ps > 80: balance the boundary registers / split the root |
| s81 | ot_s81_hc_crootr_r | physical/ref_tile/s81hc_crrre_ref/views/ot_s81_hc_crootr_r | 414.7 | 397.4 | 95.4 | 706 outputs over 220 (worst t_pk[19] 414.7): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 1911 inputs over 190 (worst ch_rd[323] 397.4): single capture flop at each input pin, HB2 pad; boundary clock spread 95.4 ps > 80: balance the boundary registers / split the root |
| s81 | ot_p2h_head | physical/ref_tile/p2h_head_ref/views/ot_p2h_head | 413.1 | 289.2 | 181.4 | 331 outputs over 220 (worst t_out[46] 413.1): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 529 inputs over 190 (worst f_s[102] 289.2): single capture flop at each input pin, HB2 pad; boundary clock spread 181.4 ps > 80: balance the boundary registers / split the root |
| s81 | dsfd_su_t_qbe | physical/ref_tile/s81su_qbe_sp8_ref/views/dsfd_su_t_qbe | 406.4 | 375.6 | 82.4 | 183 outputs over 220 (worst nx_o_q[44] 406.4): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 180 inputs over 190 (worst cfg_b[2] 375.6): single capture flop at each input pin, HB2 pad; boundary clock spread 82.4 ps > 80: balance the boundary registers / split the root |
| s81 | dsfd_mtp_hrow_cbe | physical/ref_tile/hrow5_cbe_cx/views/dsfd_mtp_hrow_cbe | 399.0 | 505.9 | 98.5 | 971 outputs over 220 (worst t_w[844] 399.0): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 870 inputs over 190 (worst f_w[327] 505.9): single capture flop at each input pin, HB2 pad; boundary clock spread 98.5 ps > 80: balance the boundary registers / split the root |
| s81 | dsfd_coll_ct | physical/ref_tile/dsfd_coll_ct_rt/views/dsfd_coll_ct | 367.6 | 515.9 | 88.6 | 751 outputs over 220 (worst elo_d[68] 367.6): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 1094 inputs over 190 (worst eli_d[514] 515.9): single capture flop at each input pin, HB2 pad; boundary clock spread 88.6 ps > 80: balance the boundary registers / split the root |
| s81 | dsfd_su_t_qbt | physical/ref_tile/s81su_qbt_ref/views/dsfd_su_t_qbt | 358.8 | 415.9 | 102.2 | 4658 outputs over 220 (worst e_dl[3773] 358.8): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 4541 inputs over 190 (worst dn_st 415.9): single capture flop at each input pin, HB2 pad; boundary clock spread 102.2 ps > 80: balance the boundary registers / split the root |
| s81 | dsfd_su_t_ctl | physical/ref_tile/s81su_ctl_ref/views/dsfd_su_t_ctl | 354.3 | 179.8 | 43.6 | 13 outputs over 220 (worst rst_o 354.3): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f) |
| s81 | dsfd_coll_ces0 | physical/ref_tile/dscoll_ces0_cxsp/views/dsfd_coll_ces0 | 317.9 | 450.2 | 90.6 | 49 outputs over 220 (worst tx_d[9] 317.9): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 39 inputs over 190 (worst qp[3] 450.2): single capture flop at each input pin, HB2 pad; boundary clock spread 90.6 ps > 80: balance the boundary registers / split the root |
| s81 | dsfd_mtp_hrow_hub | physical/ref_tile/hrow5_hub/views/dsfd_mtp_hrow_hub | 316.0 | 357.3 | 45.0 | 202 outputs over 220 (worst t_rc1[3] 316.0): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 2436 inputs over 190 (worst f_pr1[693] 357.3): single capture flop at each input pin, HB2 pad |
| s81 | dsfd_su_t_kvq | physical/ref_tile/s81su_kvq_ref/views/dsfd_su_t_kvq | 304.9 | 360.7 | 60.2 | 117 outputs over 220 (worst o_d[150] 304.9): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 1100 inputs over 190 (worst i_y[770] 360.7): single capture flop at each input pin, HB2 pad |
| s81 | ot_s81_hc_crootr_t | physical/ref_tile/s81hc_crrte_ref/views/ot_s81_hc_crootr_t | 293.3 | 406.6 | 51.4 | 108 outputs over 220 (worst s_ex[349] 293.3): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 1306 inputs over 190 (worst s_fd[1114] 406.6): single capture flop at each input pin, HB2 pad |
| s81 | dsfd_su_t_swe | physical/ref_tile/s81su_swe_gfix_ref/views/dsfd_su_t_swe | 270.8 | 223.2 | 26.0 | 20 outputs over 220 (worst c_od[33] 270.8): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 30 inputs over 190 (worst c_id[69] 223.2): single capture flop at each input pin, HB2 pad |
| s81 | dsfd_su_t_pin | physical/ref_tile/dsfd_su_t_pin_rt/views/dsfd_su_t_pin | 267.1 | 244.9 | 83.4 | 541 outputs over 220 (worst c_rf[117] 267.1): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 179 inputs over 190 (worst up_a[34] 244.9): single capture flop at each input pin, HB2 pad; boundary clock spread 83.4 ps > 80: balance the boundary registers / split the root |
| s81 | ot_s81_hc_crootr_w | physical/ref_tile/s81hc_crrww_ref/views/ot_s81_hc_crootr_w | 250.6 | 276.4 | 45.4 | 81 outputs over 220 (worst p_w[23] 250.6): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 1213 inputs over 190 (worst s_w[1818] 276.4): single capture flop at each input pin, HB2 pad |
| s81 | ot_v41_rom_elem_q_qxpq_w10 | physical/s81_die_views/q_elem_qs5f_efs | 212.4 | 239.2 | 50.2 | 1 inputs over 190 (worst rst_n 239.2): the reset input needs its own capture flop at the pin (local reset release) |
| s81 | dsfd_vm_be_sl | physical/s81_ph_views/vm_master/views/dsfd_vm_be_sl | 186.9 | 246.0 | 43.5 | 10 inputs over 190 (worst o_v[5] 246.0): single capture flop at each input pin, HB2 pad |
| hbm | ot_hgi_dma_back | physical/ref_tile/hgi_dma_back_b2_ref/views/ot_hgi_dma_back | 381.6 | 332.9 | 186.3 | 432 outputs over 220 (worst wd[1948] 381.6): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 1084 inputs over 190 (worst vr2r[512] 332.9): single capture flop at each input pin, HB2 pad; boundary clock spread 186.3 ps > 80: balance the boundary registers / split the root |
| hbm | ot_hgi_seq_fe | physical/ref_tile/hgi_seq_fe/views/ot_hgi_seq_fe | 358.1 | 311.8 | 49.2 | 308 outputs over 220 (worst fe_s1_n[11] 358.1): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 2 inputs over 190 (worst f_req_rdy 311.8): single capture flop at each input pin, HB2 pad |
| hbm | ot_hgi_seq_be | physical/ref_tile/hgi_seq_be/views/ot_hgi_seq_be | 337.4 | 255.1 | 27.0 | 1538 outputs over 220 (worst be_jl_entry[0] 337.4): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 17 inputs over 190 (worst db_loff[10] 255.1): single capture flop at each input pin, HB2 pad |
| hbm | ot_hgi_coll_tkm_tile | physical/ref_tile/coll_tkm_tile_cx/views/ot_hgi_coll_tkm_tile | 324.5 | 416.5 | 37.9 | 177 outputs over 220 (worst up_out[55] 324.5): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 378 inputs over 190 (worst ins_b[26] 416.5): single capture flop at each input pin, HB2 pad |
| hbm | ot_hcoll_port | physical/ref_tile/hcoll_port_cx/views/ot_hcoll_port | 319.0 | 464.6 | 76.8 | 116 outputs over 220 (worst rb_d[518] 319.0): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 663 inputs over 190 (worst rst_n 464.6): the reset input needs its own capture flop at the pin (local reset release) |
| hbm | ot_hgi_sv_lane2 | physical/ref_tile/hgi_sv_lane2_pf/views/ot_hgi_sv_lane2 | 293.6 | 472.7 | 25.8 | 457 outputs over 220 (worst lsw_d[431] 293.6): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 1 inputs over 190 (worst rst_n 472.7): the reset input needs its own capture flop at the pin (local reset release) |
| hbm | ot_su12_sfu | physical/ref_tile/sfu_lane_ring3_rt/views/ot_su12_sfu | 242.2 | 417.6 | 23.4 | 7 outputs over 220 (worst kv_waddr[23] 242.2): one dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f); 2 inputs over 190 (worst rst_n 417.6): the reset input needs its own capture flop at the pin (local reset release) |
| hbm | hgi_mtp_native | physical/hbm_accel_die_views/mtp_hgi | 184.8 | 210.1 | 38.7 | 4 inputs over 190 (worst f_cmdproc[82] 210.1): single capture flop at each input pin, HB2 pad |
