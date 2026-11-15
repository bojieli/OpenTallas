# PLACED-SCAN-1115 (11-15 10:1x PST): placed dumps that need stations

Tool: `tools/autopilot/placed_scan.py GEOM.TSV --kit KIT` (branch claude/placed-scan-1115). Zero-logic links (flop/macro/pin -> buffers only -> flop/macro/pin) on the post-place `geom.tsv`, grouped by (source group -> end group). **NEED-STATION** = group has bits over 580 um (what one 833 ps cycle carries, 1.24 ps/um); REACH = only over the 405 um plan reach. `plan_row` = internal_stations row of the kit plan on that bus (`none` = no station row on the matched group). Advisory early-fail diagnostic, not a sign-off gate. Scan time 2-5 s per dump.

MEASURED on place outputs on the fleet (kit geom dirs, 11-14/15). Full lists: `<host>:/srv/opentallas-scratch2/claude/placed-scan-1115/runs/<type>_attempt_N/placed_scan.tsv` (epyc2/7/8/9/10).

## Summary per type (latest attempt with a geom.tsv)

| family | type | attempt | groups need station | bits >580 um | bits >405 um | owner |
|---|---|---|---|---|---|---|
| KV hg | kv3_hg | 16 | 86 | 6563 | 8943 | KV-102 |
| KV hg | kv3_hg_v1 | 6 | 270 | 8327 | 11606 | KV-102 |
| KV hg | kv3_hg_v1p2 | 5 | 130 | 8195 | 11684 | KV-102 |
| KV hg | kv3_hg_v1p3 | 11 | 262 | 8026 | 11875 | KV-102 |
| KV hg | kv3_hg_v1p4 | 12 | 129 | 8017 | 11836 | KV-102 |
| KV hgi | kv3_hgi_v1__cl141fc26e | 11 | 27 | 2781 | 5050 | KV-102 |
| KV hgi | kv3_hgi_v2__cl2862d491 | 13 | 26 | 3005 | 5338 | KV-102 |
| KV hgi | kv3_hgi_v2__cle0015330 | 9 | 26 | 3012 | 5335 | KV-102 |
| KV hgi | kv3_hgi_v3 | 8 | 25 | 3649 | 6528 | KV-102 |
| KV pv | kv3_pv | 4 | 5264 | 7072 | 16922 | KV-PVGEN, KV-102 |
| KV pv | kv3_pv_v1n | 7 | 4703 | 12223 | 23131 | KV-PVGEN, KV-102 |
| KV pv | kv3_pv_v8 | 7 | 5566 | 8641 | 18302 | KV-PVGEN, KV-102 |
| QC fw | sle_fw_v3 | 3 | 5 | 44 | 1643 | QC-FWST, DIE-QC-103 |
| QC st_b | sle_st_b_v1__pv0e7b1dcc | 3 | 12 | 614 | 1202 | QC-FWST, DIE-QC-103 |
| QC st_b | sle_st_b_v1__pvc5a85fd4__pv38472fb8 | 6 | 9 | 628 | 1254 | QC-FWST, DIE-QC-103 |
| QC st_b | sle_st_b_v2__cl14c98df5__pv41c959f3 | 8 | 10 | 457 | 1096 | QC-FWST, DIE-QC-103 |
| QC st_b | sle_st_b_v2__cl14c98df5__pvcd986c42 | 6 | 10 | 507 | 1123 | QC-FWST, DIE-QC-103 |
| QC st_b | slw_st_b_v1__cl6357f1cc__pvffd43fdc | 3 | 13 | 677 | 1279 | QC-FWST, DIE-QC-103 |
| QC st_b | slw_st_b_v2__pvc2ec5bfb | 7 | 9 | 488 | 1130 | QC-FWST, DIE-QC-103 |
| QC su_c | sle_su_c | 8 | 377 | 3133 | 6215 | QC-FWST (rows), DIE-QC-103 (bind) |
| QC su_c | slw_su_c__cl19bb38ef | 6 | 509 | 4496 | 7416 | QC-FWST (rows), DIE-QC-103 (bind) |
| QC su_c | slw_su_c__cl92142dac | 3 | 491 | 4526 | 7601 | QC-FWST (rows), DIE-QC-103 (bind) |

## Worst groups per type (top 4 by bits over 580 um; internal glue groups included)

**kv3_hg** a16
- `u_cland_i_slg_Q_N_krsp/u_ring.dch.u_dsel/y` -> `u_bin_i_slg_Q_N_krsp`: 1062 bits, 1023 over 580, max 1386 um (~1719 ps), 23 bufs, plan_row none
- `u_hst0_t2.u_reg.ti_b` -> `u_head1_e0`: 791 bits, 535 over 580, max 1248 um (~1547 ps), 14 bufs, plan_row none
- `u_hst0_t2.u_reg.ti_b` -> `u_head0_e0`: 791 bits, 535 over 580, max 1198 um (~1486 ps), 17 bufs, plan_row none
- `u_hst0_t2.u_reg.ti_b` -> `u_head0_e2`: 791 bits, 531 over 580, max 879 um (~1090 ps), 17 bufs, plan_row none
**kv3_hg_v1** a6
- `u_cland_i_slg_Q_N_krsp/u_ring.dch.u_dsel/y` -> `u_bin_i_slg_Q_N_krsp`: 1062 bits, 1024 over 580, max 1396 um (~1731 ps), 20 bufs, plan_row none
- `u_hst0_t2.u_reg.ti_b` -> `u_head1_e0`: 791 bits, 535 over 580, max 1250 um (~1550 ps), 15 bufs, plan_row none
- `u_hst0_t2.u_reg.ti_b` -> `u_head0_e0`: 791 bits, 535 over 580, max 1200 um (~1488 ps), 17 bufs, plan_row none
- `u_hst0_t2.u_reg.ti_b` -> `u_head0_e2`: 791 bits, 531 over 580, max 880 um (~1091 ps), 17 bufs, plan_row none
**kv3_hg_v1p2** a5
- `u_cland_i_slg_Q_N_krsp/u_ring.dch.u_dsel/y` -> `u_bin_i_slg_Q_N_krsp`: 1062 bits, 1024 over 580, max 1453 um (~1802 ps), 22 bufs, plan_row none
- `u_hst0_t2.u_reg.ti_b` -> `u_head1_e0`: 791 bits, 535 over 580, max 1249 um (~1549 ps), 19 bufs, plan_row none
- `u_hst0_t2.u_reg.ti_b` -> `u_head0_e0`: 791 bits, 535 over 580, max 1203 um (~1492 ps), 21 bufs, plan_row none
- `u_hst0_t2.u_reg.ti_b` -> `u_head0_e2`: 791 bits, 531 over 580, max 884 um (~1096 ps), 17 bufs, plan_row none
**kv3_hg_v1p3** a11
- `u_cland_i_slg_Q_N_krsp/u_ring.dch.u_dsel/y` -> `u_bin_i_slg_Q_N_krsp`: 1062 bits, 1024 over 580, max 1412 um (~1751 ps), 19 bufs, plan_row none
- `u_hst0_t2.u_reg.ti_b` -> `u_head1_e0`: 791 bits, 535 over 580, max 1251 um (~1551 ps), 19 bufs, plan_row none
- `u_hst0_t2.u_reg.ti_b` -> `u_head0_e0`: 791 bits, 535 over 580, max 1195 um (~1482 ps), 21 bufs, plan_row none
- `u_hst0_t2.u_reg.ti_b` -> `u_head0_e2`: 791 bits, 531 over 580, max 875 um (~1086 ps), 17 bufs, plan_row none
**kv3_hg_v1p4** a12
- `u_cland_i_slg_Q_N_krsp/u_ring.dch.u_dsel/y` -> `u_bin_i_slg_Q_N_krsp`: 1062 bits, 1024 over 580, max 1414 um (~1753 ps), 20 bufs, plan_row none
- `u_hst0_t2.u_reg.ti_b` -> `u_head1_e0`: 791 bits, 535 over 580, max 1252 um (~1553 ps), 19 bufs, plan_row none
- `u_hst0_t2.u_reg.ti_b` -> `u_head0_e0`: 791 bits, 535 over 580, max 1201 um (~1489 ps), 21 bufs, plan_row none
- `u_hst0_t2.u_reg.ti_b` -> `u_head0_e2`: 791 bits, 531 over 580, max 881 um (~1092 ps), 17 bufs, plan_row none
**kv3_hgi_v1__cl141fc26e** a11
- `u_hst2_t2.u_reg.ti_b` -> `u_head3_e2`: 791 bits, 598 over 580, max 1123 um (~1393 ps), 20 bufs, plan_row none
- `u_hst2_t2.u_reg.ti_b` -> `u_head3_e0`: 791 bits, 536 over 580, max 1443 um (~1789 ps), 20 bufs, plan_row none
- `u_hst2_t2.u_reg.ti_b` -> `u_head2_e0`: 791 bits, 531 over 580, max 856 um (~1061 ps), 13 bufs, plan_row none
- `u_cland_i_ectl_Q_N_tN/u_ring.dch.u_dsel/y` -> `u_bin_i_ectl_Q_N_tN`: 1559 bits, 243 over 580, max 879 um (~1089 ps), 9 bufs, plan_row none
**kv3_hgi_v2__cl2862d491** a13
- `u_hst2_t2.u_reg.ti_b` -> `u_head3_e2`: 791 bits, 577 over 580, max 1065 um (~1320 ps), 18 bufs, plan_row none
- `u_hst2_t2.u_reg.ti_b` -> `u_head3_e0`: 791 bits, 536 over 580, max 1384 um (~1716 ps), 18 bufs, plan_row none
- `u_hst2_t2.u_reg.ti_b` -> `u_head2_e0`: 791 bits, 531 over 580, max 872 um (~1082 ps), 14 bufs, plan_row none
- `u_cland_i_ectl_Q_N_tN/u_ring.dch.u_dsel/y` -> `u_bin_i_ectl_Q_N_tN`: 1559 bits, 418 over 580, max 1007 um (~1249 ps), 10 bufs, plan_row none
**kv3_hgi_v2__cle0015330** a9
- `u_hst2_t2.u_reg.ti_b` -> `u_head3_e2`: 791 bits, 579 over 580, max 1064 um (~1320 ps), 18 bufs, plan_row none
- `u_hst2_t2.u_reg.ti_b` -> `u_head3_e0`: 791 bits, 539 over 580, max 1384 um (~1716 ps), 18 bufs, plan_row none
- `u_hst2_t2.u_reg.ti_b` -> `u_head2_e0`: 791 bits, 531 over 580, max 883 um (~1094 ps), 14 bufs, plan_row none
- `u_cland_i_ectl_Q_N_tN/u_ring.dch.u_dsel/y` -> `u_bin_i_ectl_Q_N_tN`: 1559 bits, 419 over 580, max 1017 um (~1261 ps), 10 bufs, plan_row none
**kv3_hgi_v3** a8
- `u_hst2_t2.u_reg.ti_b` -> `u_head3_e2`: 791 bits, 791 over 580, max 1106 um (~1371 ps), 19 bufs, plan_row none
- `u_hst2_t2.u_reg.ti_b` -> `u_head3_e4`: 791 bits, 564 over 580, max 719 um (~892 ps), 13 bufs, plan_row none
- `u_hst2_t2.u_reg.ti_b` -> `u_head3_e0`: 791 bits, 545 over 580, max 1384 um (~1717 ps), 19 bufs, plan_row none
- `u_hst2_t2.u_reg.ti_b` -> `u_head2_e0`: 791 bits, 531 over 580, max 767 um (~951 ps), 9 bufs, plan_row none
**kv3_pv** a4
- `u_pv_u_T1Q0_3_r0.b` -> `u_bout_o_pvw__u_TNQN_N_rN_b_d2`: 257 bits, 256 over 580, max 1160 um (~1438 ps), 14 bufs, plan_row none
- `u_pv_u_T1Q1_3_r0.b` -> `u_bout_o_pvw__u_TNQN_N_rN_b_d3`: 256 bits, 256 over 580, max 1108 um (~1374 ps), 13 bufs, plan_row none
- `u_pv_u_T0Q1_3_r0.b` -> `u_bout_o_pvw__u_TNQN_N_rN_b_d1`: 256 bits, 256 over 580, max 904 um (~1121 ps), 10 bufs, plan_row none
- `u_pv_u_T0Q0_3_r0.b` -> `u_bout_o_pvw__u_TNQN_N_rN_b`: 257 bits, 256 over 580, max 876 um (~1086 ps), 10 bufs, plan_row none
**kv3_pv_v1n** a7
- `u_cland_i_slg_E_N_rsp_d1/u_ring.dch.u_dsel/y` -> `u_bin_i_slg_E_N_rsp_d1`: 1056 bits, 771 over 580, max 1205 um (~1494 ps), 13 bufs, plan_row none
- `u_bin_i_slg_W_N_rsp` -> `u_vport_W.d`: 1024 bits, 539 over 580, max 1331 um (~1650 ps), 22 bufs, plan_row none
- `u_cland_i_slg_W_N_rsp_d1/u_ring.dch.u_dsel/y` -> `u_bin_i_slg_W_N_rsp_d1`: 1056 bits, 534 over 580, max 1009 um (~1251 ps), 12 bufs, plan_row none
- `u_bin_i_slg_W_N_rsp_d1` -> `u_vport_W.d`: 1024 bits, 523 over 580, max 1461 um (~1811 ps), 21 bufs, plan_row none
**kv3_pv_v8** a7
- `u_cland_ft0_i/u_ring.dch.u_dsel/y` -> `u_ft_ft0_o_0`: 1056 bits, 1056 over 580, max 1110 um (~1377 ps), 17 bufs, plan_row none
- `u_pv_u_T1Q0_3_r0.b` -> `u_bout_o_pvw__u_TNQN_N_rN_b_d2`: 257 bits, 256 over 580, max 1154 um (~1431 ps), 14 bufs, plan_row none
- `u_pv_u_T1Q1_3_r0.b` -> `u_bout_o_pvw__u_TNQN_N_rN_b_d3`: 256 bits, 256 over 580, max 1102 um (~1366 ps), 13 bufs, plan_row none
- `u_pv_u_T0Q1_3_r0.b` -> `u_bout_o_pvw__u_TNQN_N_rN_b_d1`: 256 bits, 256 over 580, max 897 um (~1112 ps), 9 bufs, plan_row none
**sle_fw_v3** a3
- `PIN:x_sc_i` -> `u_bin_x_sc_i`: 48 bits, 40 over 580, max 584 um (~724 ps), 3 bufs, plan_row none
- `u_ist_arv_eo_0` -> `u_ist_arv_eo_1`: 1 bits, 1 over 580, max 905 um (~1122 ps), 7 bufs, plan_row 2/368um
- `u_ist_arl_eo_0` -> `u_ist_arl_eo_1`: 1 bits, 1 over 580, max 876 um (~1086 ps), 6 bufs, plan_row 2/366um
- `u_ist_arm_eo_0` -> `u_ist_arm_eo_1`: 1 bits, 1 over 580, max 873 um (~1082 ps), 9 bufs, plan_row 2/366um
**sle_st_b_v1__pv0e7b1dcc** a3
- `u_bin_x_hc1_i` -> `u_u_r5.g_pin.r`: 128 bits, 105 over 580, max 895 um (~1110 ps), 8 bufs, plan_row none
- `u_bin_x_hc1_i` -> `u_u_r4.g_pin.r`: 132 bits, 93 over 580, max 898 um (~1114 ps), 13 bufs, plan_row none
- `u_cland_x_fw_i/u_ring.dch.u_dsel/y` -> `u_bin_x_fw_i`: 258 bits, 78 over 580, max 759 um (~941 ps), 5 bufs, plan_row none
- `u_cland_x_hc1_i/u_ring.dch.u_dsel/y` -> `u_bin_x_hc1_i`: 516 bits, 77 over 580, max 709 um (~879 ps), 4 bufs, plan_row none
**sle_st_b_v1__pvc5a85fd4__pv38472fb8** a6
- `u_cland_x_fw_i/u_ring.dch.u_dsel/y` -> `u_bin_x_fw_i`: 258 bits, 129 over 580, max 789 um (~979 ps), 8 bufs, plan_row none
- `u_bin_x_hc1_i` -> `u_u_r5.g_pin.r`: 128 bits, 120 over 580, max 887 um (~1100 ps), 10 bufs, plan_row none
- `u_bin_x_hc1_i` -> `u_u_r4.g_pin.r`: 132 bits, 101 over 580, max 854 um (~1059 ps), 12 bufs, plan_row none
- `u_cland_x_hc1_i/u_ring.dch.u_dsel/y` -> `u_bin_x_hc1_i`: 516 bits, 98 over 580, max 688 um (~853 ps), 7 bufs, plan_row none
**sle_st_b_v2__cl14c98df5__pv41c959f3** a8
- `u_bin_x_hc1_i` -> `u_u_r5.g_pin.r`: 128 bits, 116 over 580, max 887 um (~1100 ps), 10 bufs, plan_row none
- `u_cland_x_hc1_i/u_ring.dch.u_dsel/y` -> `u_bin_x_hc1_i`: 516 bits, 104 over 580, max 682 um (~846 ps), 7 bufs, plan_row none
- `u_bin_x_hc1_i` -> `u_u_r4.g_pin.r`: 132 bits, 87 over 580, max 859 um (~1065 ps), 13 bufs, plan_row none
- `u_u_r7.g_nb.u_nbo_pad.q` -> `u_bout_x_fe_o`: 64 bits, 64 over 580, max 825 um (~1022 ps), 8 bufs, plan_row none
**sle_st_b_v2__cl14c98df5__pvcd986c42** a6
- `u_bin_x_hc1_i` -> `u_u_r5.g_pin.r`: 128 bits, 109 over 580, max 862 um (~1069 ps), 9 bufs, plan_row none
- `u_cland_x_hc1_i/u_ring.dch.u_dsel/y` -> `u_bin_x_hc1_i`: 516 bits, 102 over 580, max 641 um (~795 ps), 6 bufs, plan_row none
- `u_bin_x_hc1_i` -> `u_u_r4.g_pin.r`: 132 bits, 94 over 580, max 964 um (~1196 ps), 13 bufs, plan_row none
- `u_u_r7.g_nb.u_nbo_pad.q` -> `u_bout_x_fe_o`: 64 bits, 64 over 580, max 830 um (~1029 ps), 8 bufs, plan_row none
**slw_st_b_v1__cl6357f1cc__pvffd43fdc** a3
- `u_bin_x_hc1_i` -> `u_u_r5.g_pin.r`: 128 bits, 126 over 580, max 822 um (~1019 ps), 9 bufs, plan_row none
- `u_bin_x_hc1_i` -> `u_u_r4.g_pin.r`: 132 bits, 95 over 580, max 844 um (~1047 ps), 13 bufs, plan_row none
- `u_cland_x_hc1_i/u_ring.dch.u_dsel/y` -> `u_bin_x_hc1_i`: 516 bits, 94 over 580, max 631 um (~782 ps), 4 bufs, plan_row none
- `u_cland_x_fw_i/u_ring.dch.u_dsel/y` -> `u_bin_x_fw_i`: 258 bits, 85 over 580, max 770 um (~955 ps), 5 bufs, plan_row none
**slw_st_b_v2__pvc2ec5bfb** a7
- `u_bin_x_hc1_i` -> `u_u_r5.g_pin.r`: 128 bits, 107 over 580, max 785 um (~974 ps), 8 bufs, plan_row none
- `u_bin_x_hc1_i` -> `u_u_r4.g_pin.r`: 132 bits, 97 over 580, max 743 um (~921 ps), 11 bufs, plan_row none
- `u_cland_x_hc1_i/u_ring.dch.u_dsel/y` -> `u_bin_x_hc1_i`: 516 bits, 92 over 580, max 634 um (~786 ps), 6 bufs, plan_row none
- `u_u_r7.g_nb.u_nbo_pad.g_line.r` -> `u_u_r7.g_nb.u_nbo_pad.q`: 64 bits, 64 over 580, max 972 um (~1205 ps), 11 bufs, plan_row none
**sle_su_c** a8
- `u_u_suvm_u_su8` -> `u_bout_x_su_l0_o`: 510 bits, 510 over 580, max 907 um (~1125 ps), 14 bufs, plan_row none
- `u_bin_x_ctl_p2_i` -> `u_u_suvm_u_vm8q_u_twb.q`: 551 bits, 474 over 580, max 1121 um (~1390 ps), 13 bufs, plan_row none
- `u_bin_x_ctl_p1_i` -> `u_u_suvm_u_vm8q_u_twb.q`: 483 bits, 391 over 580, max 1104 um (~1369 ps), 11 bufs, plan_row none
- `u_u_suvm_u_vm8q_u_twb.q` -> `u_u_suvm_u_vm8q_u_pg`: 923 bits, 238 over 580, max 695 um (~862 ps), 11 bufs, plan_row none
**slw_su_c__cl19bb38ef** a6
- `u_u_suvm_u_su8` -> `u_bout_x_su_l0_o`: 510 bits, 510 over 580, max 945 um (~1172 ps), 10 bufs, plan_row none
- `u_cland_x_ctl_p1_i/u_ring.dch.u_dsel/y` -> `u_bin_x_ctl_p1_i`: 552 bits, 483 over 580, max 1411 um (~1750 ps), 15 bufs, plan_row none
- `u_u_suvm_u_vm8q_u_twb.q` -> `u_u_suvm_u_vm8q_u_bt`: 1034 bits, 482 over 580, max 804 um (~997 ps), 11 bufs, plan_row none
- `u_cland_x_ctl_p2_i/u_ring.dch.u_dsel/y` -> `u_bin_x_ctl_p2_i`: 551 bits, 468 over 580, max 1777 um (~2204 ps), 18 bufs, plan_row none
**slw_su_c__cl92142dac** a3
- `u_u_suvm_u_vm8q_u_twb.q` -> `u_u_suvm_u_vm8q_u_bt`: 1034 bits, 515 over 580, max 813 um (~1008 ps), 11 bufs, plan_row none
- `u_u_suvm_u_su8` -> `u_bout_x_su_l0_o`: 510 bits, 510 over 580, max 945 um (~1172 ps), 10 bufs, plan_row none
- `u_cland_x_ctl_p1_i/u_ring.dch.u_dsel/y` -> `u_bin_x_ctl_p1_i`: 552 bits, 494 over 580, max 1464 um (~1815 ps), 16 bufs, plan_row none
- `u_cland_x_ctl_p2_i/u_ring.dch.u_dsel/y` -> `u_bin_x_ctl_p2_i`: 551 bits, 481 over 580, max 1494 um (~1853 ps), 15 bufs, plan_row none

## Reading, per owner
- QC-FWST / DIE-QC-103: su_c (3 types) all have 377-509 groups with bits over 580 um and no station row on the matched group; sle_su_c a6 still has no row on `x_su_l0_o` / `x_ctl_p*_i` / the twb->bt chain (the x_su_l1_o station row is not enough, as PD-QC-SUC-0800 s0.4). 4 st_b types: 9-13 groups each (457-677 bits), no row. sle_fw_v3 a3: 5 groups (44 bits >580, 1,643 >405).
- KV-102: hg v1/v1p2/v1p3/v1p4: 129-270 groups, 8,0xx bits >580; kv3_hg a16 86 groups; hgi v1/v2/v3: 25-27 groups, 2.8-3.6k bits; none has a plan row on the flagged groups (krsp, head hst0 ti_b, q0-q3 ectl columns).
- KV-PVGEN: pv (kv3_pv, v1n, v8) 4.7-5.6k groups each, 7.0-12.2k bits >580; a per-bit family, so group the listing by prefix before writing rows.
- Not scanned (no geom.tsv on the fleet yet): kv3_pv_v2/v5n/v7/v12/v4, kv3_hgi_v5/v7/v8, hg_v1p5/p6, slw_su_c a4 running; the wave step will scan them at geom.
