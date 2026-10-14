# Pin-register audit: ds_rom_s81_layer1 (contract v14, 0f63a4d25)

> **TILE VERDICTS SUPERSEDED (10-13 09:10, el1013-pinreg-audit.log):** `out_over` / `in_over` here judge each side against 0.2 T = 166.7 ps, which is the share the sign-off SDC gives the OUTSIDE, not the tile. The die statement is the pair equation with insertion-compensated clock entry: see `qwen_rom_tp8_compensated.md`, `s81_compensated.md`, `ranked_compensated.md`. The hop tables (> 500 um) and the min-delay / combinational columns stand.

Rule: clock->pin and pin->flop each <= 166.7 ps (0.2 T), hop <= 500 um, L - H >= 100 ps (50 + skew 50).

**PROVISIONAL: 33 of 47 audited views carry no corrected-export record (reexport_1013 / verdict check) after the export-SDC fix (abc334b14); their boundary numbers may be off by tens of ps**

Cells 72: audited 47 (1736 instances), violating 45 {'out_over': 39, 'in_over': 33, 'min_delay': 21}, not auditable 25 (122 instances), alias-bound 0.

| # | cell | inst | corner | flags | comb bits | out > B bits | worst out ps (bus) | in > B bits | worst in ps (bus) | L min | H max | L-H | binding |
|---|---|---:|---|---|---:|---:|---|---:|---|---:|---:|---:|---|
| 1 | dsfd_m2l_vr_68x11__hr_E3 | 1 | ss | out_over in_over min_delay | 0 | 758 | 693.5 (o) | 124 | 618.9 (di0) | 76.5 | -20.6 | 97.1 | census (closed timing, generated_placeholder) |
| 2 | dsfd_m2l_vr_68x11__hr_W4 | 1 | ss | out_over in_over min_delay | 0 | 755 | 649.3 (o) | 74 | 595.8 (di6) | 77.5 | -10.2 | 87.7 | census (closed timing, generated_placeholder) |
| 3 | dsfd_m2l_vr_68x11__hr_E4 | 1 | ss | out_over in_over min_delay | 0 | 756 | 569.3 (o) | 53 | 638.2 (di9) | 74.2 | -11.9 | 86.1 | census (closed timing, generated_placeholder) |
| 4 | ot_s81_hc_crooty | 2 | ss | out_over in_over min_delay | 0 | 4694 | 596.9 (wq_d) | 381 | 400.9 (p_w) | 59.7 | -20.5 | 80.2 | cell / view name |
| 5 | dsfd_m2l_vr_68x11__hr_W1 | 1 | ss | out_over in_over min_delay | 0 | 761 | 561.5 (o) | 178 | 596.7 (di6) | 77.3 | -19.0 | 96.3 | census (closed timing, generated_placeholder) |
| 6 | dsfd_m2l_vr_68x11__hr_W2 | 1 | ss | out_over in_over min_delay | 0 | 761 | 561.5 (o) | 178 | 596.7 (di6) | 77.3 | -19.0 | 96.3 | census (closed timing, generated_placeholder) |
| 7 | dsfd_m2l_vr_68x11__hr_W3 | 1 | ss | out_over in_over min_delay | 0 | 753 | 564.7 (o) | 172 | 533.9 (di9) | 68.9 | -19.2 | 88.1 | census (closed timing, generated_placeholder) |
| 8 | dsfd_m2l_vr_512x1__hco_SW | 1 | ss | out_over in_over min_delay | 0 | 511 | 415.6 (o) | 7 | 550.6 (di0) | 75.2 | -22.5 | 97.7 | census (closed timing, generated_placeholder) |
| 9 | dsfd_m2l_vr_68x10__hr_W5 | 1 | ss | out_over in_over min_delay | 0 | 666 | 545.2 (o) | 51 | 520.2 (di3) | 72.5 | -13.0 | 85.5 | census (closed timing, generated_placeholder) |
| 10 | dsfd_coll_ct | 1 | tt | out_over in_over | 0 | 1503 | 351.4 (elo_d) | 2217 | 532.1 (eli_d) | 79.6 | -84.6 | 164.2 | cell / view name (1 of 3 views) |
| 11 | dsfd_su_t_ctl | 1 | tt | out_over in_over min_delay | 0 | 7 | 247.0 (dn_kind) | 463 | 519.1 (p_rf) | 64.5 | -12.3 | 76.8 | cell / view name (1 of 2 views) |
| 12 | ot_s81_hc_crootr_f | 2 | tt | out_over in_over | 0 | 2784 | 383.6 (ch_fd) | 3530 | 508.3 (p_y) | 85.3 | -74.1 | 159.4 | contract kit s81hc_crrfe_ref |
| 13 | ot_mtp_p2_prefix_path | 1 | ss | out_over in_over | 0 | 601 | 351.3 (out_data) | 1314 | 504.9 (in_v) | 112.8 | -61.7 | 174.5 | cell / view name (1 of 2 views) |
| 14 | dsfd_coll_lane_w | 8 | tt | out_over in_over | 0 | 928 | 447.1 (flt) | 967 | 486.8 (lo_v) | 97.4 | -70.0 | 167.4 | cell / view name (1 of 2 views) |
| 15 | ot_s81_hc_cpin | 1 | tt | out_over in_over | 0 | 3721 | 427.1 (yacc_w) | 3649 | 470.4 (y_s) | 154.2 | -12.1 | 166.3 | cell / view name (1 of 2 views) |
| 16 | dsfd_m2l_vr_512x1__hqe_SW | 1 | tt | out_over in_over | 0 | 26 | 273.5 (o) | 2 | 433.5 (di0) | 82.2 | -22.6 | 104.8 | census (closed timing, generated_placeholder) |
| 17 | dsfd_r2l_vr_512x1__hsel | 1 | tt | out_over in_over | 0 | 514 | 432.1 (o) | 2 | 294.5 (di0) | 78.4 | -33.7 | 112.1 | census (closed timing, generated_placeholder) |
| 18 | dsfd_l2r_vr_564x1__hx_W | 1 | tt | out_over in_over | 0 | 568 | 429.0 (st) | 1 | 372.7 (i) | 76.7 | -49.9 | 126.6 | census (closed timing, generated_placeholder) |
| 19 | dsfd_r2l_vr_512x1__hcol | 1 | tt | out_over in_over | 0 | 514 | 416.3 (o) | 2 | 298.8 (di0) | 79.8 | -30.9 | 110.7 | census (closed timing, generated_placeholder) |
| 20 | ot_s81_hc_crootr_r | 2 | tt | out_over in_over | 0 | 1949 | 397.1 (t_pk) | 2164 | 415.0 (ch_rd) | 56.6 | -91.1 | 147.7 | contract kit s81hc_crrre_ref |
| 21 | dsfd_l2r_vr_512x1__hq_SW | 1 | ss | out_over in_over | 0 | 516 | 401.7 (od) | 10 | 174.4 (i) | 83.6 | -31.5 | 115.1 | census (closed timing, generated_placeholder) |
| 22 | ot_s81_hc_crootr_t | 2 | tt | out_over in_over | 0 | 1495 | 304.3 (s_ex) | 1426 | 395.6 (s_fd) | 109.3 | -67.5 | 176.8 | contract kit s81hc_crrte_ref |
| 23 | dsfd_r2l_vr_1024x1__ha_SW | 1 | tt | out_over in_over min_delay | 0 | 6 | 182.1 (o) | 2 | 394.0 (di0) | 75.5 | -21.2 | 96.7 | census (closed timing, generated_placeholder) |
| 24 | dsfd_m2l_vr_512x1__hix_SW | 1 | tt | out_over in_over | 0 | 57 | 246.0 (o) | 2 | 390.9 (di0) | 83.1 | -24.6 | 107.7 | census (closed timing, generated_placeholder) |
| 25 | ot_s81_hc_crooty_w | 2 | tt | out_over in_over | 0 | 2172 | 376.4 (wq_d) | 2173 | 382.5 (p_w) | 136.1 | -113.8 | 249.9 | cell / view name (1 of 2 views) |
| 26 | dsfd_su_t_pin | 4 | tt | out_over in_over | 0 | 4105 | 376.5 (dn_d) | 3832 | 348.3 (up_d) | 102.0 | -62.1 | 164.1 | cell / view name (1 of 3 views) |
| 27 | ot_p2h_head | 1 | tt | out_over in_over | 0 | 380 | 366.1 (t_out) | 1336 | 336.2 (f_s) | 20.6 | -102.5 | 123.1 | cell / view name |
| 28 | dsfd_coll_cbr | 2 | tt | out_over in_over | 0 | 708 | 322.2 (n_li_d) | 175 | 225.8 (x_li_d) | 88.8 | -44.2 | 133.0 | cell / view name (1 of 3 views) |
| 29 | dsfd_m2l_raw_512x1__hl_E2 | 1 | tt | out_over | 0 | 87 | 282.4 (o) | 0 | 138.5 (di0) | 76.6 | -23.4 | 100.0 | census (closed timing, generated_placeholder) |
| 30 | dsfd_m2l_raw_512x1__hl_W1 | 1 | tt | out_over min_delay | 0 | 91 | 272.5 (o) | 0 | 118.6 (di0) | 79.3 | -19.8 | 99.1 | census (closed timing, generated_placeholder) |
| 31 | ot_s81_hc_crootr_w | 2 | tt | out_over in_over | 0 | 890 | 255.2 (p_w) | 1813 | 271.8 (s_w) | 78.5 | -75.3 | 153.8 | cell / view name |
| 32 | dsfd_svc_join | 1 | ss | out_over in_over | 0 | 42 | 199.6 (c_done) | 26 | 261.6 (rst) | 68.8 | -51.2 | 120.0 | census (closed timing, generated_placeholder) |
| 33 | dsfd_m2l_raw_512x1__hl_E0 | 1 | tt | out_over min_delay | 0 | 22 | 260.9 (o) | 0 | 105.1 (di0) | 82.7 | -13.2 | 95.9 | census (closed timing, generated_placeholder) |
| 34 | ot_p2h_fadd16 | 1 | ss | out_over | 0 | 283 | 256.5 (t_y) | 0 | 164.4 (f_ab) | 58.1 | - | - | cell / view name |
| 35 | dsfd_l2r_vr_564x1__hx_E | 1 | tt | out_over | 0 | 566 | 254.5 (od) | 0 | 120.9 (i) | 81.7 | -34.4 | 116.1 | census (closed timing, generated_placeholder) |
| 36 | dsfd_coll_cbq0 | 1 | tt | out_over in_over | 0 | 52 | 247.6 (t_vm) | 346 | 218.6 (bw_v) | 93.5 | -89.7 | 183.2 | cell / view name (1 of 3 views) |
| 37 | dsfd_cfifo | 128 | tt | out_over in_over min_delay | 0 | 515 | 246.7 (xb) | 1 | 201.9 (xd) | 70.4 | -24.7 | 95.1 | census (closed timing, generated_placeholder) |
| 38 | dsfd_vm_be_sl | 4 | tt | out_over in_over | 0 | 5 | 186.9 (bl_d) | 25 | 246.0 (o_v) | 64.9 | -47.9 | 112.8 | cell / view name (1 of 6 views) |
| 39 | dsfd_coll_cbq | 4 | ss | out_over min_delay | 0 | 1 | 245.1 (flt_o) | 0 | 163.6 (bw_d) | 72.6 | -25.4 | 98.0 | cell / view name (1 of 3 views) |
| 40 | dsfd_stnv_512x1 | 383 | tt | min_delay | 0 | 0 | 115.4 (do0) | 0 | 28.1 (di0) | 53.4 | 12.1 | 41.3 | census (closed timing, generated_placeholder) |
| 41 | dsfd_stnh_566x1 | 391 | tt | min_delay | 0 | 0 | 117.0 (do0) | 0 | 31.4 (di0) | 55.2 | 12.0 | 43.2 | census (closed timing, generated_placeholder) |
| 42 | dsfd_stnh_512x1 | 598 | tt | min_delay | 0 | 0 | 116.9 (do0) | 0 | 28.1 (di0) | 55.4 | 11.4 | 44.0 | census (closed timing, generated_placeholder) |
| 43 | dsfd_stnh_514x1 | 43 | tt | min_delay | 0 | 0 | 115.5 (do0) | 0 | 29.0 (di0) | 55.0 | 10.1 | 44.9 | census (closed timing, generated_placeholder) |
| 44 | dsfd_stnv_514x1 | 129 | tt | min_delay | 0 | 0 | 117.2 (do0) | 0 | 28.9 (di0) | 55.9 | 10.3 | 45.6 | census (closed timing, generated_placeholder) |
| 45 | dsfd_coll_cbf | 1 | tt | min_delay | 0 | 0 | 114.2 (fvm_u) | 0 | 125.3 (f_vm) | 58.5 | -36.4 | 94.9 | cell / view name |

Export-SDC: 14 audited cells on corrected views, 33 still pre-fix: physical/redesign_ds/routes/dsfd_coll_cbf-cbh-c2e836720-tc-cl-p2/dsfd_coll_cbf, physical/redesign_ds/routes/dsfd_coll_cbq-cbh-390208180-tc-cl-p4/dsfd_coll_cbq, physical/s81_die_views/views/dsfd_stnh_512x1, physical/s81_die_views/views/dsfd_stnh_514x1, physical/s81_die_views/views/dsfd_stnh_566x1, physical/s81_die_views/views/dsfd_stnv_512x1, physical/s81_die_views/views/dsfd_stnv_514x1, physical/s81_die_views/views/m221pq/dsfd_l2r_vr_512x1__hq_SW, physical/s81_die_views/views/m221pq/dsfd_l2r_vr_564x1__hx_E, physical/s81_die_views/views/m221pq/dsfd_l2r_vr_564x1__hx_W, physical/s81_die_views/views/m221pq/dsfd_m2l_raw_512x1__hl_E0, physical/s81_die_views/views/m221pq/dsfd_m2l_raw_512x1__hl_E2, physical/s81_die_views/views/m221pq/dsfd_m2l_raw_512x1__hl_W1, physical/s81_die_views/views/m221pq/dsfd_m2l_vr_512x1__hco_SW, physical/s81_die_views/views/m221pq/dsfd_m2l_vr_512x1__hix_SW, physical/s81_die_views/views/m221pq/dsfd_m2l_vr_512x1__hqe_SW, physical/s81_die_views/views/m221pq/dsfd_m2l_vr_68x10__hr_W5, physical/s81_die_views/views/m221pq/dsfd_m2l_vr_68x11__hr_E3, physical/s81_die_views/views/m221pq/dsfd_r2l_vr_1024x1__ha_SW, physical/s81_die_views/views/m221pq/dsfd_r2l_vr_512x1__hcol, physical/s81_die_views/views/m221pq/dsfd_r2l_vr_512x1__hsel, physical/s81_die_views/views_colck/dsfd_cfifo, physical/s81_ph_views/assembled/dsfd_ctrl, physical/s81_ph_views/closed/dsfd_svc_join, physical/s81_ph_views/closed/ot_p2h_fadd16, physical/s81_ph_views/hc_hier/routes/s81hc-crooth-673aa90b0-tc-yw-pd40/ot_s81_hc_crooty, physical/s81_ph_views/vm_master/views/dsfd_vm_be_sl, physical/variant_fill/s81-hend-m221pq-hr-E4-a1f23fa0b-mm-vf-hm25/dsfd_m2l_vr_68x11__hr_E4, physical/variant_fill/s81-hend-m221pq-hr-W1-a1f23fa0b-mm-vf-hm25/dsfd_m2l_vr_68x11__hr_W1, physical/variant_fill/s81-hend-m221pq-hr-W2-a1f23fa0b-mm-vf-hm25/dsfd_m2l_vr_68x11__hr_W2, physical/variant_fill/s81-hend-m221pq-hr-W3-a1f23fa0b-mm-vf-hm25/dsfd_m2l_vr_68x11__hr_W3, physical/variant_fill/s81-hend-m221pq-hr-W4-a1f23fa0b-mm-vf-hm25/dsfd_m2l_vr_68x11__hr_W4, results/rtl/mtp_p2_rootpipe_20261010/routes/mtp-p2-path-rb4v-a978bdba9-tc-hm20.

Not auditable (no closed view): dsfd_sp_su_c x1, dsfd_su_t_qn0 x1, dsfd_su_t_qn1 x1, dsfd_su_t_kv0 x1, dsfd_su_t_kv1 x1, dsfd_su_t_qb x4, dsfd_su_t_sw x8, ot_s81_su_sm x8, dsfd_sp_hc_c x1, dsfd_sp_hc_t x1, ot_s81_hc_crooty_y x2, ot_s81_hc_crootr x2, ot_s81_hc_comb x1, ot_s81_hc_cth x64, dsfd_sp_collective_c x1, dsfd_sp_vm x1, dsfd_sp_capture_c x1, dsfd_sp_gather_c x1, dsfd_wfc_stg x1, ot_v41_rom_elem_q_* x1, dsfd_bf x1, dsfd_sp_pq / pqc tiles x1, dsfd_mtp_hrow banks x1, engram_c tiles x1, dsfd_vm_bgq28 x16

## Hops: no die case given (contract carries placement but no nets)
