# LONG-LEG-CENSUS (2026-11-20 01:56)

> PARTIAL (first commit, 11-20 02:0x PST). Data = fleet scan 11-20 00:3x on 139 newest placed kits (6 gen hosts), done at the old 405 um scan threshold with macro / hard-core ends at the iterm bbox and NO clock-edge data: so (1) legs of 300-405 um are missing, (2) the pin-centroid correction (COORD 11-19) and (3) the half-cycle class h (200 um) are not in these numbers (h = 0 here). Tool on main (tools/die_plan/long_leg_census.py, pin centroid + half-cycle + 300 um + routed slack bins); the rescan with all three is running on all gen hosts (queued behind kit jobs) and replaces this file. Slack bins vs 300 um cap: pending the same scan.
> Rows: lanes/LONG-LEG-CENSUS.tsv = one row per (die, bus class); per-leg rows stay on the hub (~/ll0040/census_run/all.legs.tsv, 755k legs).


Every single-cycle placed leg longer than 300 um (launch -> capture straight Manhattan; register / port / macro ends), newest placed kit per (die, type). Kits scanned OK 139, failed 0. Tool: tools/die_plan/long_leg_census.py. Class a = both ends FIXED (station / relay row, +1 cycle); b = one end fixed (pin or macro-site move, or station); c = both movable (placement / region).

Class h = half-cycle leg (launch or capture on a negedge face, limit 200 um instead of 405); its fixed / movable split is in the leg rows (fcls).

| die | legs (excl. strap/tie) | a | b | c | h (half-cycle) | types hit | worst um | bus classes |
|---|---|---|---|---|---|---|---|---|
| qwen_compute | 59889 | 25390 | 25774 | 8725 | 0 | 40 | 1760 | 301 |
| qwen_kvsys | 126368 | 46842 | 47674 | 31852 | 0 | 11 | 3320 | 585 |
| s81 | 509213 | 85421 | 274161 | 149631 | 0 | 66 | 2437 | 1182 |
| s81_head | 4564 | 992 | 2287 | 1285 | 0 | 4 | 1793 | 88 |

## Legs that changed because macro / hard-core ends now sit at the pin shape (COORD 11-19)

Old measure = macro / core centre. `new` = over 405 um only with the pin location (by class a / b / c); `dropped` = over 405 um at the core centre, not at the pin. Class a / b / c does not depend on length: a leg keeps its class, it enters or leaves the census.

- qwen_compute: none
- qwen_kvsys: none
- s81: none
- s81_head: none

## qwen_compute

| bus class | family | types | legs | worst um | class | station row | owner |
|---|---|---|---|---|---|---|---|
| reader_start_fltv_n_i | coll_core | 1 | 9 | 1760 | b (b9) | yes | QC-PLAN-R3 |
| writer_start_flt_o | coll_core | 1 | 8 | 1727 | b (b8) | yes | QC-PLAN-R3 |
| writer_start_io_collective__out_data | coll_core | 1 | 8 | 1722 | b (b8) | yes | QC-PLAN-R3 |
| g_seg.cnt | cbn_q00 | 7 | 448 | 1714 | c (c448) | no | QC-PLAN-R3 |
| g_seg.run | cbn_q00 | 7 | 112 | 1713 | c (c112) | no | QC-PLAN-R3 |
| fclk_out_io_collective__out_data | coll_core | 1 | 1 | 1705 | a (a1) | no | QC-PLAN-R3 |
| reader_start_flt_n_i | coll_core | 1 | 9 | 1667 | b (b9) | yes | QC-PLAN-R3 |
| writer_start_io_collective__out_err | coll_core | 1 | 1 | 1656 | b (b1) | yes | QC-PLAN-R3 |
| writer_start_io_collective__out_rank | coll_core | 1 | 1 | 1655 | b (b1) | yes | QC-PLAN-R3 |
| writer_start_io_collective__out_valid | coll_core | 1 | 1 | 1652 | b (b1) | yes | QC-PLAN-R3 |
| writer_start_io_collective__out_last | coll_core | 1 | 1 | 1652 | b (b1) | yes | QC-PLAN-R3 |
| fclk_out_io_collective__out_err | coll_core | 1 | 1 | 1651 | a (a1) | no | QC-PLAN-R3 |
| fclk_out_io_collective__out_last | coll_core | 1 | 1 | 1650 | a (a1) | no | QC-PLAN-R3 |
| fclk_out_cland_up | coll_core | 1 | 1 | 1648 | a (a1) | no | QC-PLAN-R3 |
| fclk_out_io_collective__out_valid | coll_core | 1 | 1 | 1646 | a (a1) | no | QC-PLAN-R3 |
| fclk_out_io_collective__out_rank | coll_core | 1 | 1 | 1646 | a (a1) | no | QC-PLAN-R3 |
| reader_start_rec_rx_s0_i | coll_core | 1 | 26 | 1624 | b (b26) | yes | QC-PLAN-R3 |
| reader_start_io_collective__in_data | coll_core | 1 | 19 | 1527 | b (b19) | yes | QC-PLAN-R3 |
| fclk_out_io_collective__fault | coll_core | 1 | 1 | 1474 | a (a1) | no | QC-PLAN-R3 |
| fclk_out_io_collective__cmd_free | coll_core | 1 | 1 | 1473 | a (a1) | no | QC-PLAN-R3 |
| fclk_out_fltv_o | coll_core | 1 | 1 | 1465 | a (a1) | no | QC-PLAN-R3 |
| io_collective__fault | coll_core | 1 | 1 | 1458 | a (a1) | yes | QC-PLAN-R3 |
| fclk_out_flt_o | coll_core | 1 | 1 | 1456 | a (a1) | no | QC-PLAN-R3 |
| reader_start_io_collective__in_tag | coll_core | 1 | 3 | 1455 | b (b3) | yes | QC-PLAN-R3 |
| fltv_o | coll_core | 1 | 58 | 1447 | b (a28b30) | yes | QC-PLAN-R3 |

## qwen_kvsys

| bus class | family | types | legs | worst um | class | station row | owner |
|---|---|---|---|---|---|---|---|
| origin | kv3_pv_v8 | 2 | 7 | 3320 | a (a7) | yes | FABLE-FIX-KV-PV-2140 |
| fstart_o_vport_W_N_vo_d | kv3_pv_v8 | 1 | 1 | 3185 | a (a1) | yes | FABLE-FIX-KV-PV-2140 |
| tstart_o | kv3_pv_v8 | 1 | 1 | 2994 | a (a1) | yes | FABLE-FIX-KV-PV-2140 |
| raw_reset_o | kv3_pv_v8 | 1 | 1 | 2992 | a (a1) | yes | FABLE-FIX-KV-PV-2140 |
| o_pvw__u_sN_j_y_valid_d | kv3_pv_v1n | 2 | 6 | 2935 | a (a6) | yes | FABLE-FIX-KV-PV-2140 |
| fstart_ft3_o | kv3_pv_v8 | 1 | 1 | 2925 | a (a1) | yes | FABLE-FIX-KV-PV-2140 |
| fstart_ft4_o | kv3_pv_v8 | 1 | 1 | 2922 | a (a1) | yes | FABLE-FIX-KV-PV-2140 |
| o_ectl_Q_N_eN | kv3_hg_v1p6 | 1 | 32 | 2521 | a (a32) | yes | FABLE-FIX-KV-HG-0000 |
| i_pvw__u_ctl_cmd | kv3_pv_v8 | 2 | 954 | 2436 | a (a517b437) | yes | FABLE-FIX-KV-PV-2140 |
| o_pvw__u_sN_j_fault_d | kv3_pv_v1n | 2 | 6 | 2311 | a (a6) | yes | FABLE-FIX-KV-PV-2140 |
| fstart_o_fch_pv_V_N_q | kv3_pv_v8 | 1 | 1 | 2164 | a (a1) | yes | FABLE-FIX-KV-PV-2140 |
| fstart_o_pvw__u_sN_j_fault_d | kv3_pv_v8 | 1 | 3 | 2156 | a (a3) | yes | FABLE-FIX-KV-PV-2140 |
| fstart_o_pvw__u_sN_j_y_valid_d | kv3_pv_v8 | 1 | 3 | 2155 | a (a3) | yes | FABLE-FIX-KV-PV-2140 |
| fstart_o_pvw__u_sN_j_y_valid | kv3_pv_v8 | 1 | 1 | 2151 | a (a1) | yes | FABLE-FIX-KV-PV-2140 |
| fstart_o_pvw__u_sN_j_fault | kv3_pv_v8 | 1 | 1 | 2149 | a (a1) | yes | FABLE-FIX-KV-PV-2140 |
| u_ist_o_vport_E_N_f_d | kv3_pv_v1n | 1 | 1 | 1995 | b (b1) | yes | FABLE-FIX-KV-PV-2140 |
| g_selcp.u_cp | kv3_pv_v1n | 1 | 64 | 1955 | c (c64) | no | FABLE-FIX-KV-PV-2140 |
| i_ectl_Q_N_kf | kv3_pc_v1 | 3 | 7 | 1908 | a (a4b3) | yes | KV-D23-COMPOSE |
| u_ist_o_vport_E_N_f | kv3_pv_v1n | 1 | 1 | 1822 | b (b1) | yes | FABLE-FIX-KV-PV-2140 |
| i_head_Q_N_N__u_fts_s_b | kv3_hg_v1p6 | 1 | 70 | 1794 | a (a69b1) | yes | FABLE-FIX-KV-HG-0000 |
| i_astk_E__u_strip_g_er_chain_u_er_g_owner_N__u_owner_response_data | kv3_pv_v8 | 2 | 447 | 1792 | a (a369b78) | yes | FABLE-FIX-KV-PV-2140 |
| i_hst_Q_N_N_sN_s_b | kv3_hg_v1p6 | 1 | 70 | 1779 | a (a69b1) | yes | FABLE-FIX-KV-HG-0000 |
| o_pvw__u_sN_j_y_valid | kv3_pv_v1n | 2 | 2 | 1759 | a (a2) | yes | FABLE-FIX-KV-PV-2140 |
| i_host_hbm_rst_n | kv3_pc_v3 | 3 | 33 | 1756 | b (a4b29) | yes | KV-D23-COMPOSE |
| i_vport_E_N_vo_d | kv3_pv_v1n | 2 | 692 | 1754 | a (a687b5) | yes | FABLE-FIX-KV-PV-2140 |

## s81

| bus class | family | types | legs | worst um | class | station row | owner |
|---|---|---|---|---|---|---|---|
| fstart_ft6_o | ot_s81sl_leaf | 2 | 2 | 2437 | b (b2) | yes | FABLE-FIX-S81-LEAF-2140 |
| fstart_ft7_o | ot_s81sl_leaf | 2 | 2 | 2198 | b (b2) | yes | FABLE-FIX-S81-LEAF-2140 |
| u_r.g_d | dsdv_slice_c1x_C | 13 | 12650 | 1951 | c (c12650) | no | FABLE-FIX-S81-SLICEC-0045 |
| fstart_ft8_o | ot_s81sl_leaf | 2 | 2 | 1923 | b (b2) | yes | FABLE-FIX-S81-LEAF-2140 |
| u_r.roe_d | dsdv_slice_c1x_C | 11 | 7405 | 1922 | c (c7405) | no | FABLE-FIX-S81-SLICEC-0045 |
| u_u_s_1N_u_lp_u_xf_g_cp_u_e | dsdv_slice_c1x_C | 1 | 1376 | 1818 | b (b1376) | no | FABLE-FIX-S81-SLICEC-0045 |
| u_s.xw_d | dsdv_slice_c1x_C | 8 | 1277 | 1805 | c (c1277) | no | FABLE-FIX-S81-SLICEC-0045 |
| u_r.dl_w | dsdv_slice_iq_C | 7 | 712 | 1794 | c (c712) | no | S81-SVC-DSDV-0005 |
| u_r.dl_e | dsdv_slice_iq_C | 10 | 2235 | 1787 | c (c2235) | no | S81-SVC-DSDV-0005 |
| u_r.nxw_d | dsdv_slice_c1x_C | 6 | 647 | 1785 | c (c647) | no | FABLE-FIX-S81-SLICEC-0045 |
| u_r.dl_ev | dsdv_slice_c1x_C | 11 | 17 | 1744 | c (c17) | no | FABLE-FIX-S81-SLICEC-0045 |
| u_r.nxe_d | dsdv_slice_c1x_C | 9 | 859 | 1724 | c (c859) | no | FABLE-FIX-S81-SLICEC-0045 |
| u_r.dl_wv | dsdv_slice_c1x_C | 5 | 8 | 1707 | c (c8) | no | FABLE-FIX-S81-SLICEC-0045 |
| u_u_s_6S_u_lp_u_eg_u_gg | dsdv_slice_c1x_C | 1 | 33 | 1679 | a (a32b1) | no | FABLE-FIX-S81-SLICEC-0045 |
| u_u_s_2N_u_lp_u_xf_g_cp_u_e | dsdv_slice_c1x_C | 1 | 1344 | 1657 | b (b1344) | no | FABLE-FIX-S81-SLICEC-0045 |
| u_u_s_6S_u_lp_u_eg_u_nk | dsdv_slice_c1x_C | 1 | 33 | 1642 | a (a32b1) | no | FABLE-FIX-S81-SLICEC-0045 |
| u_r.vo_d | dsdv_slice_c1x_C | 11 | 1957 | 1641 | c (c1957) | no | FABLE-FIX-S81-SLICEC-0045 |
| u_u_s_5S_u_lp_u_xf_g_cp_u_e | dsdv_slice_c1x_C | 1 | 1342 | 1639 | b (b1342) | no | FABLE-FIX-S81-SLICEC-0045 |
| u_u_s_3N_u_slice_u_xf_g_cp_u_e | dsdv_slice_kv512_C | 1 | 1684 | 1638 | b (b1684) | no | S81-SVC-DSDV-0005 |
| g_u_s_2N_u_lp_u_xf_src_H_q | dsdv_slice_c1x_C | 1 | 245 | 1599 | c (b2c243) | no | FABLE-FIX-S81-SLICEC-0045 |
| g_u_s_7S_u_sl_u_xf_driver_rb_v_q | dsdv_slice_lepe_nh_mus_C | 1 | 1 | 1585 | c (c1) | no | S81-SVC-DSDV-0005 |
| g_u_s_1S_u_lp_u_xf_driver_rb_v_q | dsdv_slice_c1x_C | 1 | 1 | 1582 | c (c1) | no | FABLE-FIX-S81-SLICEC-0045 |
| u_u_land.ri | dsdv_slice_lepw_mu_LP | 2 | 21 | 1580 | c (c21) | no | S81-SVC-DSDV-0005 |
| g_u_s_1N_u_lp_u_xf_driver_rb_v_q | dsdv_slice_c1x_C | 1 | 1 | 1580 | c (c1) | no | FABLE-FIX-S81-SLICEC-0045 |
| u_u_s_6S_u_lp_u_xr | dsdv_slice_c1x_C | 1 | 440 | 1580 | b (a35b405) | no | FABLE-FIX-S81-SLICEC-0045 |

## s81_head

| bus class | family | types | legs | worst um | class | station row | owner |
|---|---|---|---|---|---|---|---|
| fclk_out_coll_o | hd_lep0N | 1 | 3 | 1793 | a (a3) | no | HEAD-CROSSING-1119 |
| u_st.q | hd_lep0N | 1 | 100 | 1311 | c (b1c99) | no | HEAD-CROSSING-1119 |
| g_c.qc | hd_lep0N | 1 | 15 | 1238 | c (c15) | no | HEAD-CROSSING-1119 |
| fclk_out_fault_o | hd_lep0N | 1 | 1 | 1054 | a (a1) | no | HEAD-CROSSING-1119 |
| fclk_out_lw_o | hd_lep0N | 1 | 1 | 1039 | a (a1) | no | HEAD-CROSSING-1119 |
| fclk_out_ctrl_o | hd_lep0N | 1 | 1 | 983 | a (a1) | no | HEAD-CROSSING-1119 |
| g_local.local_r | hd_lep0N | 2 | 65 | 932 | c (c65) | no | HEAD-CROSSING-1119 |
| coll_i | hd_lep0N | 1 | 698 | 861 | a (a509b189) | yes | HEAD-CROSSING-1119 |
| fault_o | hd_lep0N | 1 | 1 | 845 | b (b1) | yes | HEAD-CROSSING-1119 |
| g_address.credit_pin_r | hd_lep0N | 1 | 14 | 735 | c (c14) | no | HEAD-CROSSING-1119 |
| origin | hd_ctl | 1 | 4 | 721 | b (b4) | yes | HEAD-CROSSING-1119 |
| g_address.wp_r | hd_lep0N | 1 | 171 | 716 | c (c171) | no | HEAD-CROSSING-1119 |
| g_slice.valid_r | hd_lep0N | 1 | 76 | 706 | c (c76) | no | HEAD-CROSSING-1119 |
| g_address.count_r | hd_lep0N | 1 | 186 | 702 | c (c186) | no | HEAD-CROSSING-1119 |
| g_pp.u_pair | hd_lep0N | 1 | 27 | 684 | b (b27) | no | HEAD-CROSSING-1119 |
| u_logic.u_xb | hd_ctl | 1 | 627 | 677 | b (b627) | no | HEAD-CROSSING-1119 |
| unit_i | hd_lep0N | 1 | 45 | 640 | b (b45) | yes | HEAD-CROSSING-1119 |
| lepf_i | hd_lep0N | 1 | 1 | 639 | b (b1) | yes | HEAD-CROSSING-1119 |
| coll_o | hd_lep0N | 1 | 596 | 630 | a (a434b162) | yes | HEAD-CROSSING-1119 |
| coll_ob | hd_mesh | 1 | 458 | 626 | b (b458) | yes | HEAD-CROSSING-1119 |
| ctrl_o | hd_lep0N | 1 | 32 | 602 | b (b32) | yes | HEAD-CROSSING-1119 |
| g_group.group_r | hd_lep0N | 1 | 7 | 598 | c (c7) | no | HEAD-CROSSING-1119 |
| agg | hd_ctl | 3 | 6 | 592 | a (a6) | yes | HEAD-CROSSING-1119 |
| g_registered_select.tm_r | hd_lep0N | 1 | 3 | 586 | c (c3) | no | HEAD-CROSSING-1119 |
| g_s.u_st | hd_lep0N | 1 | 57 | 579 | c (c57) | no | HEAD-CROSSING-1119 |
