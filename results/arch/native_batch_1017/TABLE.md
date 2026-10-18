# Lane NATIVE-BATCH, 10-17 17:10 PT: routed native pin audits of closed views

Tool: tools/hier_contract/native_pin_audit.py audit_one @ origin/main 708fc1938 (TT, R = insertion.json boundary mean; launch = O - R <= 220, capture = S + R <= 190; spread = boundary max - min <= 80 ps). Every view taken from its closure job's record commit (git show --name-only of that commit, so cells shared by several kits, e.g. ot_hbm_static_cfg_collar, get the right view). Receipts: branch claude/native-batch-1017, results/arch/native_batch_1017/{native_batch_audit.json (per-pin fail lists, FF launch min / hold need), views.tsv, run_audit.py, audit.txt}. 0 combinational pins on every view. 47 views: 37 BINDABLE, 10 FAIL.

element | view (job / record commit) | launch ps (pin) | capture ps (pin) | spread ps (R) | verdict
---|---|---|---|---|---
KV qkd_astk_er_tap | physical/ref_tile/qkd_astk_er_tap/views/qkd_astk_er_tap (qkd_astk_er_tap-e2-889997e65 / 2d0e4a894) | 190.0 (response_addr[32]) | 157.5 (rst_n) | 27.5 (R 106.9) | BINDABLE
KV qkd_embedding_row_tx | physical/ref_tile/qkd_embedding_row_tx/views/qkd_embedding_row_tx (qkd_embedding_row_tx-r2-b97c79344 / 14f985540) | 113.5 (emb_tx_payload[459]) | 85.6 (word_data[51]) | 70.6 (R 226.0) | BINDABLE
KV qkd_ctrl_pc_sched | physical/ref_tile/qkd_ctrl_pc_sched_s9/views/qkd_ctrl_pc_sched (qkd_ctrl_pc_sched_s9-s9-623df1d3e / 5933cc57f) | 245.8 (e_sec[9]) | 135.1 (pc[3]) | 19.7 (R 179.3) | FAIL launch 10 pins: e_sec[9] 245.8, e_sec[1] 245.1, e_sec[0] 244.0, e_sec[8] 243.1 ...
KV qkd_static_ectla_kiss | physical/ref_tile/qkd_static_ectla_k3/views/qkd_static_ectla_kiss (qkd_static_ectla_k3-r3-828d82516 / d143913c7) | 104.4 (rs_o[489]) | 79.4 (rsp_data[499]) | 36.4 (R 254.2) | BINDABLE
KV qkd_ctrl_pc_cdc_child | physical/ref_tile/qkd_ctrl_pc_cdc_s7c/views/qkd_ctrl_pc_cdc_child (qkd_ctrl_pc_cdc_s7c-s7c-9eb027cde / a86962f8d) | 196.2 (completion_fault) | 154.3 (es[104]) | 33.7 (R 158.2) | BINDABLE
KV qkd_ctrl_pc_obs_child | physical/ref_tile/qkd_ctrl_pc_obs_s7c/views/qkd_ctrl_pc_obs_child (qkd_ctrl_pc_obs_s7c-s7c-41cf54199 / 93a797abe) | 183.3 (native_commit_identity[58]) | 153.5 (context_word[107]) | 33.1 (R 141.0) | BINDABLE
KV qkd_kv_grp_ctl | physical/ref_tile/qkd_kv_grp_ctl/views/qkd_kv_grp_ctl (qkd_kv_grp_ctl-g2-95edd890c / 7feb50b22) | 194.4 (sink_data[19]) | 349.4 (cfg_we[4]) | 38.6 (R 132.8) | FAIL capture 7 pins: cfg_we[4] 349.4, cfg_we[1] 344.4, cfg_we[0] 343.1, cfg_we[2] 338.9, cfg_we[3] 335.6, rst_n 214.9, ctrl_go 192.9
KV ot_qwen_tp8_pv_wide_ctl_t | physical/ref_tile/qkd_pv_ctl_t_d54f58a95/views/ot_qwen_tp8_pv_wide_ctl_t (qkd_pv_ctl_t_d54f58a96-d54f58a96-287098501 / f0be3773d) | 188.9 (req_t[7]) | 135.8 (col_fault[27]) | 9.6 (R 103.7) | BINDABLE
KV qkd_static_kv_return_slots_mc | physical/ref_tile/qkd_static_kv_return_slots_mc_r3/views/qkd_static_kv_return_slots_mc (qkd_static_kv_return_slots_mc_r5-mc5b-ae9c68079 / c49a684a6) | 199.0 (actual_data[85]) | 117.1 (compiled_hbm_put) | 43.5 (R 282.4) | BINDABLE
KV qkd_static_kv_pc_es_merge | physical/ref_tile/qkd_static_kv_pc_es_merge/views/qkd_static_kv_pc_es_merge (qkd_static_kv_pc_es_merge-r1-4751caff6 / 65f28b5c4) | 104.5 (beat_data[27]) | 74.1 (emb_epoch[15]) | 38.6 (R 137.8) | BINDABLE
KV qkd_seq_core_static_p | physical/ref_tile/qkd_seq_core_st_p/views/qkd_seq_core_static_p (qkd_seq_core_st_p-p1-9088bc402 / 7dd3ca122) | 184.6 (tk[43]) | 130.5 (kvn_word_tag[0]) | 10.9 (R 92.3) | BINDABLE
KV qkd_seq_xd_sel | physical/ref_tile/qkd_seq_xd_sel/views/qkd_seq_xd_sel (qkd_seq_xd_sel-x1-ec5a00436 / d62d2752f) | 177.4 (x_d[107]) | 230.8 (q_v) | 5.0 (R 76.7) | FAIL capture 1 pins: q_v 230.8
HBM ot_hbm_host_cp_rx | physical/ref_tile/hdie_host_cprx_r1/views/ot_hbm_host_cp_rx (hdie_host_cprx_r1-r1-1807890a7 / 518a8aea8) | 190.7 (f_flit[31]) | 67.8 (in_v) | 13.5 (R 158.4) | BINDABLE
HBM ot_hbm_static_cfg_collar | physical/ref_tile/hdie_col_su_r1/views/ot_hbm_static_cfg_collar (hdie_col_su_r1-r3-7a1d8a612 / 7d0379818) | 124.0 (prm[63]) | 65.3 (rst_n) | 17.2 (R 98.3) | BINDABLE
HBM ot_hbm_argmax_static_sw_vm_r2 | physical/ref_tile/hbm_argmax_swvm_r2_1017/views/ot_hbm_argmax_static_sw_vm_r2 (hbm_argmax_swvm_r2_1017-r2-e4dc0b651 / 735457a6a) | 222.4 (busy) | 131.4 (mode) | 28.2 (R 166.2) | FAIL launch 1 pins: busy 222.4
HBM ot_hgi_coll_inj_idx_join_rg | physical/ref_tile/hcoll_inj_idx_join_rg_1017/views/ot_hgi_coll_inj_idx_join_rg (hcoll_inj_idx_join_rg_1017-rg1-7a8776ef2 / 102f0715d) | 150.0 (fault) | 124.5 (su_inj_d_r0[417]) | 47.6 (R 244.8) | BINDABLE
HBM ot_hbm_svc_pc_ctrl_leaf_cfg_h9b | physical/ref_tile/hdie_pc_ctrl_cfg_h9c/views/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b (hdie_pc_ctrl_cfg_h9c-h9c-cts-155-1aa2ec44b / 2ab20b600) | 138.1 (kr_data[123]) | 185.3 (dram_rvalid) | 59.8 (R 259.7) | BINDABLE
HBM ot_hbm_status_join_fa | physical/ref_tile/hdie_host_status_fa_r3/views/ot_hbm_status_join_fa (hdie_host_status_fa_r3-r3-b384c6eaf / f1f979aea) | 109.9 (a_cause[3]) | 71.9 (t_fault[102]) | 9.4 (R 104.6) | BINDABLE
HBM lg_pair tap leaf term (HC) | physical/ref_tile/hbm_hc_lg_pair_tap_leaf_term_1017/views/ot_hgi_sfu_lg_pair_tap_leaf_term (hbm_hc_lg_pair_tap_leaf_term_1017-f1-cd78c43fe / 513486259) | 140.9 (fault) | 86.6 (local_read[1]) | 48.5 (R 219.9) | BINDABLE
HBM lg_pair tap leaf (SFU) | physical/ref_tile/hbm_sfu_lg_pair_tap_leaf_1017/views/ot_hgi_sfu_lg_pair_tap_leaf (hbm_sfu_lg_pair_tap_leaf_1017-f1-b593fd3b1 / 9071bc89e) | 179.9 (fault) | 117.6 (local_write[0]) | 53.6 (R 234.6) | BINDABLE
HBM ot_hgi_sfu_store_stripe_leaf_r10 | physical/ref_tile/hbm_sfu_store_stripe_r10_1017/views/ot_hgi_sfu_store_stripe_leaf_r10 (hbm_sfu_store_stripe_r10_1017-r10-947bd4836 / 054f975a6) | 276.8 (out_data[103]) | 72.3 (in_data[60]) | 29.8 (R 256.9) | FAIL launch 73 pins: out_data[103] 276.8, out_data[102] 265.7, out_data[199] 263.4, out_data[179] 250.4 ...
HBM ot_hbm_sm_vm_wr_q_t_lanes | physical/ref_tile/hsm_smvm_wrq_t_r5/views/ot_hbm_sm_vm_wr_q_t_lanes (hsm_smvm_wrq_t_r5-lanes-dc8367e5b / ba3e96512) | 166.2 (wq_s2[280]) | 134.7 (rv_s0) | 55.7 (R 165.0) | BINDABLE
HBM ot_hbm_host_phy_adapt | physical/ref_tile/hdie_host_phy_r1/views/ot_hbm_host_phy_adapt (hdie_host_phy_r1-r1-dcfed59ab / b9b524384) | 255.2 (phy_tx[460]) | 136.6 (phy_rx[451]) | 28.4 (R 121.0) | FAIL launch 12 pins: phy_tx[460] 255.2, phy_tx[475] 235.0, phy_tx[435] 234.9, phy_tx[424] 226.9 ...
HBM ot_hbm_host_landing256 | physical/ref_tile/hdie_host_landing_r1/views/ot_hbm_host_landing256 (hdie_host_landing_r1-r1-dcfed59ab / 84be7ecdb) | 135.8 (out_v) | 101.1 (rst_n) | 21.5 (R 150.4) | BINDABLE
HBM ot_static_cmd_target | physical/ref_tile/hdie_cp_svg_r1/views/ot_static_cmd_target (hdie_cp_svg_r1-r1-dcfed59ab / 7b72d1a45) | 133.7 (configured) | 402.6 (rst_n) | 16.8 (R 104.3) | FAIL capture 1 pins: rst_n 402.6
HBM ot_hbm_static_cfg_collar | physical/ref_tile/hdie_col_sfu_r1/views/ot_hbm_static_cfg_collar (hdie_col_sfu_r1-r1-dcfed59ab / 52e958e94) | 109.6 (prm[184]) | 455.7 (rst_n) | 21.2 (R 97.8) | FAIL capture 1 pins: rst_n 455.7
HBM ot_hbm_static_cfg_collar | physical/ref_tile/hdie_col_idx_r1/views/ot_hbm_static_cfg_collar (hdie_col_idx_r1-r1-dcfed59ab / d9bfc4094) | 136.1 (start_v) | 499.0 (rst_n) | 37.9 (R 175.2) | FAIL capture 1 pins: rst_n 499.0
HBM ot_hgi_dma_back_cp_collar | physical/ref_tile/hv16_dbk_collar/views/ot_hgi_dma_back_cp_collar (hv16_dbk_collar-c1-b51306fbc / bd9ccbe3d) | 127.7 (configured) | 91.4 (cfg_data[162]) | 47.4 (R 217.1) | BINDABLE
HBM ot_hbm_idx_vm_query_static | physical/ref_tile/hidx_op_r4/views/ot_hbm_idx_vm_query_static (hidx_op_r4-r4-d9f104dec / 7dd74122f) | 121.0 (block_data[10]) | 80.1 (vm_rr[222]) | 53.3 (R 216.5) | BINDABLE
HBM ot_hbm_xp_aq_tree13_fmt | physical/ref_tile/hxp_aq13_fmt/views/ot_hbm_xp_aq_tree13_fmt (hxp_aq13_fmt-f1-2680d87a9 / fdcecbe0a) | 137.2 (q[185]) | 272.7 (rst_n) | 28.7 (R 218.4) | FAIL capture 1 pins: rst_n 272.7
S81 dsfd_dvrly_68_NS | physical/ref_tile/s81dv_rly_68_ns/views/dsfd_dvrly_68_NS (s81dv_rly_68_ns-w1-c5a69dc05 / 7c797527a) | 114.4 (o[37]) | 63.4 (i[64]) | 2.1 (R 62.3) | BINDABLE
S81 dsfd_dvrly_68_SN | physical/ref_tile/s81dv_rly_68_sn/views/dsfd_dvrly_68_SN (s81dv_rly_68_sn-w1-c5a69dc05 / 53a9b74ac) | 110.6 (o[44]) | 62.7 (i[33]) | 1.4 (R 63.3) | BINDABLE
S81 dsfd_dvrly_512_EW | physical/ref_tile/s81dv_rly_512_ew/views/dsfd_dvrly_512_EW (s81dv_rly_512_ew-w1-c5a69dc05 / ec3e9287f) | 109.0 (o[20]) | 68.8 (i[217]) | 6.8 (R 82.5) | BINDABLE
S81 dsfd_dvrly_512_WE | physical/ref_tile/s81dv_rly_512_we/views/dsfd_dvrly_512_WE (s81dv_rly_512_we-w1-c5a69dc05 / 06d016112) | 107.2 (o[32]) | 66.9 (i[370]) | 7.4 (R 80.9) | BINDABLE
S81 dsfd_dvrly_562_EW | physical/ref_tile/s81dv_rly_562_ew/views/dsfd_dvrly_562_EW (s81dv_rly_562_ew-w1-c5a69dc05 / 1c9f0935c) | 110.8 (o[80]) | 69.3 (i[162]) | 8.8 (R 84.3) | BINDABLE
S81 dsfd_dvrly_562_WE | physical/ref_tile/s81dv_rly_562_we/views/dsfd_dvrly_562_WE (s81dv_rly_562_we-w1-c5a69dc05 / 9f6f06326) | 107.5 (o[556]) | 68.0 (i[243]) | 8.0 (R 83.2) | BINDABLE
S81 dsfd_dvrly_562_SN | physical/ref_tile/s81dv_rly_562_sn/views/dsfd_dvrly_562_SN (s81dv_rly_562_sn-w2-6e188c155 / 1c78dd47e) | 149.2 (o[351]) | 74.4 (i[136]) | 13.4 (R 90.1) | BINDABLE
S81 dsfd_dvrly_682_EW | physical/ref_tile/s81dv_rly_682_ew/views/dsfd_dvrly_682_EW (s81dv_rly_682_ew-w1-c5a69dc05 / e94448803) | 112.2 (o[628]) | 72.0 (i[489]) | 11.1 (R 89.1) | BINDABLE
S81 dsfd_dvrly_682_WE | physical/ref_tile/s81dv_rly_682_we/views/dsfd_dvrly_682_WE (s81dv_rly_682_we-w1-c5a69dc05 / 369243ad3) | 107.7 (o[676]) | 68.0 (i[174]) | 6.3 (R 87.3) | BINDABLE
S81 dsfd_dvrly_682_NS | physical/ref_tile/s81dv_rly_682_ns/views/dsfd_dvrly_682_NS (s81dv_rly_682_ns-w2-6e188c155 / 10f42ffb9) | 128.8 (o[569]) | 72.5 (i[292]) | 9.2 (R 93.6) | BINDABLE
S81 dsfd_rly_38_WN | physical/ref_tile/s81_rly_38_wn/views/dsfd_rly_38_WN (s81_rly_38_wn-x1-e3cbf17fa / ded1d7032) | 108.4 (o[6]) | 60.0 (i[21]) | 0.8 (R 52.8) | BINDABLE
S81 dsfd_rly_266_EW | physical/ref_tile/s81_rly_266_ew/views/dsfd_rly_266_EW (s81_rly_266_ew-r4n-a2f724583 / 8c337d8b4) | 136.1 (o[16]) | 66.2 (i[13]) | 4.0 (R 79.8) | BINDABLE
S81 dsfd_rly_66_EW | physical/ref_tile/s81_rly_66_ew/views/dsfd_rly_66_EW (s81_rly_66_ew-r4n-32f8e7df7 / 2893828e4) | 108.5 (o[36]) | 63.7 (i[38]) | 1.0 (R 59.4) | BINDABLE
S81 ot_s81_su_smq | physical/ref_tile/s81su_smq/views/ot_s81_su_smq (s81su_smq-s81su_smq-342decba7 / 42a32d3b6) | 106.8 (w_v) | 79.8 (r_p) | 43.4 (R 199.3) | BINDABLE
S81 ot_s81_kp4_enc | physical/ref_tile/s81lk_kp4_enc/views/ot_s81_kp4_enc (s81lk_kp4_enc-k4-10153956e / d65e304f8) | 122.3 (p_d[67]) | 103.5 (tx_d[471]) | 57.2 (R 286.4) | BINDABLE
S81 ot_s81_kp4_dout | physical/ref_tile/s81lk_kp4_dout/views/ot_s81_kp4_dout (s81lk_kp4_dout-t2-cef44c405 / 6577ef93f) | 89.6 (q_d[31]) | 73.5 (d_q[386]) | 45.5 (R 247.4) | BINDABLE
S81 ot_s81dv_xfin | physical/ref_tile/s81dv_xfin/views/ot_s81dv_xfin (s81dv_xfin-x5-06cb91161 / 09cf1dfc4) | 156.6 (fault) | 118.8 (wi_d[23]) | 57.8 (R 274.4) | BINDABLE

## FAIL causes (one line each; nothing fixed)

- qkd_ctrl_pc_sched_s9 (qkd_ctrl_pc_sched, qkd_ctrl_pc_sched_s9-s9-623df1d3e): e_sec/e_row outputs are the s9 post-edge 2:1 mux of the es0/es1 registers, selected by the kvc_q copy (17 selects): register->mux->pin, +1 mux over the probe's 221.4 after routing. Fix class (coordinator 15:45): +1-cycle ECC child / output register after the select.
- qkd_kv_grp_ctl (qkd_kv_grp_ctl, qkd_kv_grp_ctl-g2-95edd890c): wires-only wrapper (0 added edges): cfg_we[i] goes straight from the pin into the boot_cdc FIFO wr_valid gate (cfg_we & !sealed & !fault -> write pointer + 64-b data enables), rst_n (214.9) and ctrl_go (192.9) also unregistered; the inputs need pin flops / a reset relay.
- qkd_seq_xd_sel (qkd_seq_xd_sel, qkd_seq_xd_sel-x1-ec5a00436): q_v is the select of the 128-b x_d <= q_v ? q_d : k_d mux, taken straight from the pin: one pin fans out to 128 mux selects ahead of the flops (no q_v pin flop or replicated select).
- hbm_argmax_swvm_r2_1017 (ot_hbm_argmax_static_sw_vm_r2, hbm_argmax_swvm_r2_1017-r2-e4dc0b651): busy is the FSM state flop itself (it gates go_p, s_beat, flt internally), so the pin is driven off a loaded internal net: 2.4 ps over; needs a dedicated busy pin-register copy.
- hbm_sfu_store_stripe_r10_1017 (ot_hgi_sfu_store_stripe_leaf_r10, hbm_sfu_store_stripe_r10_1017-r10-947bd4836): out_data = data_q, the keep/dont_touch 256-b register that also drives the SRAM wd_in, so it sits beside the macro, far from the chain-out face (73 pins 220-277): the chain forward needs its own register at the out face.
- hdie_host_phy_r1 (ot_hbm_host_phy_adapt, hdie_host_phy_r1-r1-dcfed59ab): phy_tx is a pin register, but the tile is pin-bound (2,052 pins; the old 41.04 slot was 20.8 pins/um): 12 phy_tx flops placed too far from their dense face pins (wire launch 224-255); needs the face lengthened or the slot widened.
- hdie_cp_svg_r1 (ot_static_cmd_target, hdie_cp_svg_r1-r1-dcfed59ab): raw rst_n from the pin fans out to every flop (no reset pin register / local reset sync); capture 402.6. col_su r3's clk_in reset sync (65.3 here) is the proven shape.
- hdie_col_sfu_r1 (ot_hbm_static_cfg_collar, hdie_col_sfu_r1-r1-dcfed59ab): raw rst_n fans out to every collar flop (no local reset sync); capture 455.7. col_su r3's reset sync (65.3) fixes this.
- hdie_col_idx_r1 (ot_hbm_static_cfg_collar, hdie_col_idx_r1-r1-dcfed59ab): raw rst_n fans out to every collar flop (no local reset sync); capture 499.0. col_su r3's reset sync (65.3) fixes this.
- hxp_aq13_fmt (ot_hbm_xp_aq_tree13_fmt, hxp_aq13_fmt-f1-2680d87a9): raw rst_n fans out to the whole tree13 body (no reset relay/sync at the pin); capture 272.7.

## Notes
- sched_s9: the predicted e_sec launch risk (probe 221.4) materialised at 245.8 on 10 pins (e_sec[0..10]); capture is clean now (135.1; p_kv_v fixed). Not bindable.
- argmax_swvm r2: only 2.4 ps over on one pin (busy); still FAIL by the rule.
- col_su r3 PASSES (L124.0/C65.3/sp17.2): its reset sync is the fix for col_sfu/col_idx/cp_svg (all from the same dcfed59ab HBMA-HOST batch).
- pv_ctl_t age96 (d54f58a96) record writes into physical/ref_tile/qkd_pv_ctl_t_d54f58a95/views (its auto-merge CONFLICTED, so main still has the a95 view there); mc5b record writes into physical/ref_tile/qkd_static_kv_return_slots_mc_r3/views. kv_pc_es_merge and smvm_wrq_t r5 records also had AUTO-MERGE CONFLICTs: the audited bytes are the record commits, not necessarily main.
- KV qkd_ctrl_pc_cdc_s7c launch 196.2 (completion_fault) and HBM hdie_host_cprx 190.7, astk_er_tap 190.0: PASS but within 30 ps of the launch budget.

