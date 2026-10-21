# Reset-input worst paths per die (ROOT-RST reset_path_audit.py, 2026-10-19 00:46; release-tree cache 1792395941.7228816)

108 of 360 current-die elements have a worst native capture or worst sign-off path that starts at a reset input.  Fix: land the reset at the face in 2 registered stages (ref_tile "reset_landing": {"enable": true} or RTL rst_l0 -> rst_l1 per region), re-route, attach the native_capture receipt (native_pin_audit --view).

## Qwen compute: 2 DEFECT, 8 WATCH
| element | owner | job | TT / FF | finding |
|---|---|---|---|---|
| ot_hdc_sfu_exp_t | Q-DIE11b | qfd_su_sfu_exp-sp1-943c39997 | 47.82 / 21.69 | worst hold FF path starts at rst_n -> rt$_DFF_PN0_ slack -2.9 ps |
| ot_hdc_sfu_rsq_t | Q-DIE11b | qfd_su_sfu_rsq-sp1-943c39997 | 55.5 / 22.16 | worst hold FF path starts at rst_n -> rt$_DFF_PN0_ slack -1.2 ps |

WATCH (reset is the worst path but lands in a synchroniser / relay register with margin): ot_hdc_sfu_rcp_t, qfd_c_xstn, qfd_c_xstnw, qfd_d2d_static, qfd_embedding_word_provider, qfd_rstsync, qfd_sys_face, qfd_ucie_six_five

## Qwen KV/system: 2 DEFECT, 17 WATCH
| element | owner | job | TT / FF | finding |
|---|---|---|---|---|
| qkd_kvs_emb | KV-PLAN4 | qkd_kvs_emb-i2-5561116d2 | 42.46 / 8.54 | native worst capture 465.3 ps at rst_n (FAIL > 190); worst setup TT path starts at rst_n -> u_join.len[6][2]$_DFFE_PN0P_ slack +56.9 ps; worst hold FF path starts at rst_n -> u_join.u_join4.hot[2]$_DFF_PN0_ slack +40.4 ps |
| qkd_kvs_attn | KV-PLAN4 | qkd_kvs_attn-g3-477f1e3ba | 22.81 / 12.1 | native worst capture 383.3 ps at rst_n (FAIL > 190); worst setup TT path starts at rst_n -> u_attn.ctl.g_ld.codec.l_ev$_DFF_PN0_ slack +139.2 ps; worst hold FF path starts at rst_n -> ot_prs_00332_ff slack +20.7 ps |

WATCH (reset is the worst path but lands in a synchroniser / relay register with margin): ot_nhb_zh, ot_qkh_head_score4_native, ot_qkh_head_stk_native, ot_qkh_ktree, ot_qkh_lane8, ot_qkh_recip_leaf, qkd_d2d_cal_seq_pin, qkd_ectl_b_tp8_direct, qkd_embedding_static_return_hop, qkd_embgw_boot, qkd_host_rx_class_admission, qkd_host_rx_pad5, qkd_rst_region, qkd_seq_core_static, qkd_seq_fan, qkd_seq_xs_tp8, qkd_static_ectla_kiss

## S81 (DeepSeek ROM): 2 DEFECT, 32 WATCH
| element | owner | job | TT / FF | finding |
|---|---|---|---|---|
| dsdv_bk_col | S81-DIE6 | s81dvbk_colv-pl1-d863824bf | 10.47 / 24.3 | worst hold FF path starts at rst_n -> g_l[1].u_l slack -20.3 ps |
| ot_s81_kp4_dec | H-D4G | s81lk_kp4_dec-p1-867a65ed7 | 83.61 / 17.36 | native worst capture 337.0 ps at rst_n (FAIL > 190); worst hold FF path starts at rst_n -> u_dly slack -52.3 ps |

WATCH (reset is the worst path but lands in a synchroniser / relay register with margin): dsdv_bk_g, dsdv_bkcol_l, dsdv_bkcol_m, dsdv_bksel_c, dsdv_gunit_l0, dsdv_gunit_l0r, dsdv_gunit_l1c, dsdv_gunit_l3, dsdv_gunit_l4r, dsdv_gunit_l5f, dsdv_mu_land, dsdv_sh_vc, dsdv_svc_sx_hrow, dsfd_node_LLd, dsfd_node_LLfd, dsfd_node_LLfu, dsfd_node_NNfd, dsfd_su_t_rxsb, dsfd_su_t_rxsf, dsfd_su_t_smd, dsfd_su_t_sml, ot_s81_cfg7_seq, ot_s81_cfg7_seq_bf, ot_s81_engram_chunk8, ot_s81_engram_mul4, ot_s81_engram_signed_sqrt, ot_s81_kp4_dsyn, ot_s81_pq_calendar_reader, ot_s81dv_xfin, ot_s81sl_eg, ot_s81sl_vq, ot_s81sl_vsw

## HBM: 3 DEFECT, 43 WATCH
| element | owner | job | TT / FF | finding |
|---|---|---|---|---|
| ot_hgi_sm_xload_cl2_ctlx | H-D4G | hgi_sm_xl2_ctlx-q1-7af6f4406 | 8.26 / 5.9 | native worst capture 455.7 ps at rst_n (FAIL > 190); worst setup TT path starts at rst_n -> u_w.u_iss.lbase[6]$_DFF_PN0_ slack +100.8 ps; worst hold FF path starts at rst_n -> u_w.u_iss.dv$_DFF_PN0_ slack +35.4 ps |
| ot_s81_kp4_dec | H-D4G | s81lk_kp4_dec-p1-867a65ed7 | 83.61 / 17.36 | native worst capture 337.0 ps at rst_n (FAIL > 190); worst hold FF path starts at rst_n -> u_dly slack -52.3 ps |
| ot_hbm_idx_vm_share2_leaf_r | H-D4G | hidx_share2r_leaf_1018-r3-16615707a | 302.58 / 19.31 | native worst capture 280.1 ps at rst_n (FAIL > 190); worst setup TT path starts at rst_n -> rst_q$_DFF_PN0_ slack +438.9 ps |

WATCH (reset is the worst path but lands in a synchroniser / relay register with margin): hfd_ckgen_rel, hfd_ckgen_rel4, hfd_ep_static, hfd_hgi_vm_calendar, hfd_vms_bank_native_q0_faces, ot_hbm_fault_leaf, ot_hbm_fault_leaf_n8_s0, ot_hbm_host_cfg_leaf2, ot_hbm_host_cfg_leaf_ne2, ot_hbm_host_cfg_leaf_nw, ot_hbm_host_cfg_leaf_se2, ot_hbm_host_cfg_leaf_sw, ot_hbm_host_cp_rxs, ot_hbm_host_landing256, ot_hbm_host_static_ingress, ot_hbm_idx_qctl_static, ot_hbm_idx_vm_query_static_n12, ot_hbm_idx_xq_node_static, ot_hbm_sm_vm_wr_q_t_lanes4, ot_hbm_status_join, ot_hbm_status_join_fa, ot_hbm_su_bridge_release_s, ot_hbm_su_programme_pghead, ot_hbm_su_programme_root_h5, ot_hbm_su_static_sfustore_hw, ot_hbm_su_stree_leaf, ot_hbm_su_stree_root, ot_hbm_svc_pc_ctrl_leaf_cfg_h9b, ot_hbm_svc_sm_xcal, ot_hbm_svc_stack_fault, ot_hbm_svc_wbw_copy, ot_hgi_coll_gq_land, ot_hgi_coll_inj_copy, ot_hgi_coll_inj_idx_join_rg, ot_hgi_coll_kq_share2_leaf, ot_hgi_coll_qslots_capture_pin_v2, ot_hgi_coll_ring_ag_ctl, ot_hgi_coll_ring_b_stop, ot_hgi_dma_back_landing_bank, ot_hgi_dma_back_static_vp4_banks_cp, ot_hgi_qw_daq, ot_hgi_sm_xload_cl2_bfqg, ot_vms_status4_static

## Recent views (closed in the last 3 days) outside the release-tree die rows with a reset capture FAIL (33; die by cell family)
| die | cell | owner | job | capture |
|---|---|---|---|---|
| qwen_compute | qfd_sysctl_stn_pb2_cl | Claude:drive-0158 | qfd_sysctl_stn_pb2_cl-d4760be45-tc-hm10-b-cl | 514.4 ps at por_n |
| qwen_compute | qfd_d2d_static | Claude:Q-DVM+LINK | qfd_d2d_static_r5-r5-99ecb9ed4 | 491.3 ps at rst_n |
| qwen_compute | qfd_d2d_static | Claude:Q-DVM+LINK | qfd_d2d_static_r1-r4-f779ceecf | 468.8 ps at rst_n |
| s81 | dsfd_engram_lkp_static14 | Claude:S-ENGRAM+NORM | s81engm_lkp_static14-st10-ckrd-428af274c | 465.6 ps at rst_n |
| qwen_kvsys | qkd_hr_core_guard | Claude:KV-HOSTCL | qkd_hr_core_guard-r2-342580b92 | 463.0 ps at host_rst_n |
| hbm | ot_hbm_static_cfg_collar | Claude:HBMA-HOST | hdie_col_sfu_r1-r1-dcfed59ab | 455.7 ps at rst_n |
| hbm | ot_hgi_coll_argmax_m_tp192 | Claude H-NETLIST/COLL 1815 | hcoll_v7_arg_tp192-d4f-0377e2057 | 448.7 ps at rst_n |
| qwen_kvsys | qkd_host_pc_slice_die | Claude:ELEM-CENSUS kit helper | qkd_hslice-ec1-75cbc9b99 | 435.7 ps at host_rst_n |
| hbm | ot_hbm_su_programme_pgcol_s | Claude:HBM-SU | hbm_su_pgcol_s_r5-r5-9e33ce295 | 414.2 ps at rst_n |
| hbm | ot_hbm_idx_tail_native | Codex:H-NETLIST | hidx_tail_native_0854-tail0854-11e1a1c51 | 402.8 ps at rst_n |
| hbm | ot_hbm_host_packet_static | Claude:HBMA-HOST | hdie_host_packet_r1-r1-dcfed59ab | 392.0 ps at rst_n |
| qwen_kvsys | qkd_hr_core_order | Claude:KV-HOSTCL | qkd_hr_core_order-r3-aea9dd896 | 386.9 ps at host_rst_n |
| qwen_compute | qfd_ctrl_pc_03 | Claude:qwen-blocks | qfd_ctrl_ready_hbm_03-216a06602mm-tt | 359.7 ps at rst_n |
| qwen_compute | qfd_ctrl_pc_01 | Claude:multivt | qfd_ctrl_pc_01-74d839a79-tt-lvt | 358.3 ps at rst_n |
| qwen_compute | qfd_ctrl_protected_oreg_00 | Claude:qwen-blocks | qfd_ctrl_protected_oreg_00-591f6a683mm-tt | 355.0 ps at rst_n |
| qwen_compute | qfd_kvc_decode_map_pc | Claude:multivt | qfd_kvc_decode_map_pc-970663df7-tt-lvt | 337.3 ps at rst_n |
| qwen_compute | qfd_ctrl_pc_11 | Claude:qwen-blocks | qfd_ctrl_ready_hbm_11-3d5ad2a4ftt | 335.1 ps at rst_n |
| qwen_compute | qfd_ctrl_pc_12 | Claude:qwen-blocks | qfd_ctrl_ready_hbm_12-3d5ad2a4ftt | 335.0 ps at rst_n |
| qwen_compute | qfd_ctrl_pc_10 | Claude:qwen-blocks | qfd_ctrl_ready_hbm_10-3d5ad2a4ftt | 326.9 ps at rst_n |
| qwen_compute | qfd_ctrl_ready_00 | Codex:qwen-control | qfd_ctrl_ready_00-8be556c2e-tt | 321.3 ps at rst_n |
| qwen_compute | qfd_kvc_decode_pc | Codex:qwen-kvctrl | qfd_kvc_decode_pc-d85c4b6ce-mmq-tt | 315.9 ps at rst_n |
| qwen_kvsys | qkd_hr_core_tx | Claude:KV-HOSTCL | qkd_hr_core_tx-r2-c372bf6fe | 298.4 ps at host_rst_n |
| qwen_kvsys | qkd_astk_rly_296 | Claude:HKV-ASTK | qkd_astk_rly_296-r1-849bb441e | 277.4 ps at rst_n |
| hbm | ot_hbm_svc_vmdel_lane | Claude:H-NETLIST/kits | hv15_vmdel_lane-hv15-20b84db92 | 274.2 ps at rst_n |
| qwen_kvsys | qkd_hr_core_queue | Claude:KV-HROOT | qkd_hr_core_queue-r4-24f17c338 | 274.0 ps at host_rst_n |
| qwen_kvsys | qkd_host_rx_class_admission | Claude:KV-HOSTCL-A8 | qkd_hr_core_rx-b1-161e15878 | 256.6 ps at rst_n |
| qwen_compute | qfd_ucie_six_five | Claude:Q-DVM+LINK | qfd_ucie_gearbox_r10-r13-428ab16dd | 255.0 ps at rst_n |
| hbm | ot_hbm_svc_sm_xcal | Codex:H-XC-physical-1016 | hbm_xcal216_r1-r1-a380caec1 | 254.0 ps at rst_n |
| qwen_compute | qfd_embed_code_bank_retained | Codex:embedding-scale | qfd_embed_code_bank_retained-24bd6a53b-tt | 253.4 ps at rst_n |
| qwen_compute | qfd_res_ctl | Codex:res-ser-tiles | qfd_res_ctl-f46a68c8a-tc-hm0 | 245.4 ps at rst_n |
| hbm | ot_hgi_hc_residual_half_static | Claude:H-NETLIST/kits (for HC owner) | hbm_hc_residual_half_static-native1-36070f827 | 243.8 ps at rst_n |
| qwen_kvsys | qkd_pv16_vport | Claude:Q-ATTN-RATE | qkd_pv16_vport_r1-r1-643237e29 | 203.2 ps at rst_n |
| hbm | ot_hgi_xp_aq_bypass13 | Claude:HBM-COLLQ | hgi_xp_aq_bypass13_1018-p1-75cdef3c4 | 198.4 ps at rst_n |

