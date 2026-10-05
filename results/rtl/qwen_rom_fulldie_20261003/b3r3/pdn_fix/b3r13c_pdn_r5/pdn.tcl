# r5 full-die PDN: r4 grids, anchored instance patterns, one macro grid per stripe phase
add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name core -voltage_domains CORE -pins {M9} -starts_with GROUND
add_pdn_stripe -grid core -layer M8 -width .48 -pitch 9.091 -offset 0
add_pdn_stripe -grid core -layer M9 -width .48 -pitch 9.091 -offset 0
add_pdn_connect -grid core -layers {M8 M9}
define_pdn_grid -macro -instances {^phy_EN$ ^phy_ES$} -voltage_domains CORE -name pg_m5_0 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m5_0 -layer M5 -width .504 -pitch 9.091 -offset 6.751
add_pdn_connect -grid pg_m5_0 -layers {M4 M5}
add_pdn_connect -grid pg_m5_0 -layers {M5 M8}
define_pdn_grid -macro -instances {^phy_WN$ ^phy_WS$} -voltage_domains CORE -name pg_m5_1 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m5_1 -layer M5 -width .504 -pitch 9.091 -offset 6.969
add_pdn_connect -grid pg_m5_1 -layers {M4 M5}
add_pdn_connect -grid pg_m5_1 -layers {M5 M8}
define_pdn_grid -macro -instances {^s_0_7$ ^s_10_7$ ^s_11_7$ ^s_12_7$ ^s_13_7$ ^s_14_7$ ^s_15_7$ ^s_16_7$ ^s_17_7$ ^s_18_7$ ^s_19_7$ ^s_1_7$ ^s_20_7$ ^s_21_7$ ^s_22_7$ ^s_23_7$ ^s_24_7$ ^s_25_7$ ^s_26_7$ ^s_27_7$ ^s_28_7$ ^s_29_7$ ^s_2_7$ ^s_30_7$ ^s_31_7$ ^s_32_7$ ^s_33_7$ ^s_34_7$ ^s_35_7$ ^s_36_7$ ^s_37_7$ ^s_38_7$ ^s_39_7$ ^s_3_7$ ^s_40_7$ ^s_41_7$ ^s_42_7$ ^s_43_7$ ^s_44_7$ ^s_45_7$ ^s_46_7$ ^s_47_7$ ^s_48_7$ ^s_49_7$ ^s_4_7$ ^s_50_7$ ^s_51_7$ ^s_52_7$ ^s_53_7$ ^s_54_7$ ^s_55_7$ ^s_56_7$ ^s_57_7$ ^s_58_7$ ^s_59_7$ ^s_5_7$ ^s_60_7$ ^s_61_7$ ^s_62_7$ ^s_63_7$ ^s_6_7$ ^s_7_7$ ^s_8_7$ ^s_9_7$} -voltage_domains CORE -name pg_m8_2 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_2 -layer M8 -width .48 -pitch 9.091 -offset 0.083
add_pdn_connect -grid pg_m8_2 -layers {M7 M8}
add_pdn_connect -grid pg_m8_2 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_11$ ^t_10_11$ ^t_11_11$ ^t_12_11$ ^t_13_11$ ^t_14_11$ ^t_15_11$ ^t_16_11$ ^t_17_11$ ^t_18_11$ ^t_19_11$ ^t_1_11$ ^t_20_11$ ^t_21_11$ ^t_22_11$ ^t_23_11$ ^t_24_11$ ^t_25_11$ ^t_26_11$ ^t_27_11$ ^t_28_11$ ^t_29_11$ ^t_2_11$ ^t_30_11$ ^t_31_11$ ^t_32_11$ ^t_33_11$ ^t_34_11$ ^t_35_11$ ^t_36_11$ ^t_37_11$ ^t_38_11$ ^t_39_11$ ^t_3_11$ ^t_40_11$ ^t_41_11$ ^t_42_11$ ^t_43_11$ ^t_44_11$ ^t_45_11$ ^t_46_11$ ^t_47_11$ ^t_48_11$ ^t_49_11$ ^t_4_11$ ^t_50_11$ ^t_51_11$ ^t_52_11$ ^t_53_11$ ^t_54_11$ ^t_55_11$ ^t_56_11$ ^t_57_11$ ^t_58_11$ ^t_59_11$ ^t_5_11$ ^t_60_11$ ^t_61_11$ ^t_62_11$ ^t_63_11$ ^t_6_11$ ^t_7_11$ ^t_8_11$ ^t_9_11$} -voltage_domains CORE -name pg_m8_3 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_3 -layer M8 -width .48 -pitch 9.091 -offset 0.136
add_pdn_connect -grid pg_m8_3 -layers {M7 M8}
add_pdn_connect -grid pg_m8_3 -layers {M8 M9}
define_pdn_grid -macro -instances {^sp_constants_sequencer$} -voltage_domains CORE -name pg_m8_4 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_4 -layer M8 -width .48 -pitch 9.091 -offset 0.157
add_pdn_connect -grid pg_m8_4 -layers {M7 M8}
add_pdn_connect -grid pg_m8_4 -layers {M8 M9}
define_pdn_grid -macro -instances {^lv_N_3$} -voltage_domains CORE -name pg_m8_5 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_5 -layer M8 -width .48 -pitch 9.091 -offset 0.239
add_pdn_connect -grid pg_m8_5 -layers {M7 M8}
add_pdn_connect -grid pg_m8_5 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_3$ ^s_10_3$ ^s_11_3$ ^s_12_3$ ^s_13_3$ ^s_14_3$ ^s_15_3$ ^s_16_3$ ^s_17_3$ ^s_18_3$ ^s_19_3$ ^s_1_3$ ^s_20_3$ ^s_21_3$ ^s_22_3$ ^s_23_3$ ^s_24_3$ ^s_25_3$ ^s_26_3$ ^s_27_3$ ^s_28_3$ ^s_29_3$ ^s_2_3$ ^s_30_3$ ^s_31_3$ ^s_32_3$ ^s_33_3$ ^s_34_3$ ^s_35_3$ ^s_36_3$ ^s_37_3$ ^s_38_3$ ^s_39_3$ ^s_3_3$ ^s_40_3$ ^s_41_3$ ^s_42_3$ ^s_43_3$ ^s_44_3$ ^s_45_3$ ^s_46_3$ ^s_47_3$ ^s_48_3$ ^s_49_3$ ^s_4_3$ ^s_50_3$ ^s_51_3$ ^s_52_3$ ^s_53_3$ ^s_54_3$ ^s_55_3$ ^s_56_3$ ^s_57_3$ ^s_58_3$ ^s_59_3$ ^s_5_3$ ^s_60_3$ ^s_61_3$ ^s_62_3$ ^s_63_3$ ^s_6_3$ ^s_7_3$ ^s_8_3$ ^s_9_3$} -voltage_domains CORE -name pg_m8_6 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_6 -layer M8 -width .48 -pitch 9.091 -offset 0.314
add_pdn_connect -grid pg_m8_6 -layers {M7 M8}
add_pdn_connect -grid pg_m8_6 -layers {M8 M9}
define_pdn_grid -macro -instances {^lc_SE$ ^lc_SW$ ^lh_SE_1$ ^lh_SE_2$ ^lh_SE_3$ ^lh_SE_4$ ^lh_SE_5$ ^lh_SW_1$ ^lh_SW_2$ ^lh_SW_3$ ^lh_SW_4$ ^lh_SW_5$} -voltage_domains CORE -name pg_m8_7 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_7 -layer M8 -width .48 -pitch 9.091 -offset 0.367
add_pdn_connect -grid pg_m8_7 -layers {M7 M8}
add_pdn_connect -grid pg_m8_7 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_22$ ^s_10_22$ ^s_11_22$ ^s_12_22$ ^s_13_22$ ^s_14_22$ ^s_15_22$ ^s_16_22$ ^s_17_22$ ^s_18_22$ ^s_19_22$ ^s_1_22$ ^s_20_22$ ^s_21_22$ ^s_22_22$ ^s_23_22$ ^s_24_22$ ^s_25_22$ ^s_26_22$ ^s_27_22$ ^s_28_22$ ^s_29_22$ ^s_2_22$ ^s_30_22$ ^s_31_22$ ^s_32_22$ ^s_33_22$ ^s_34_22$ ^s_35_22$ ^s_36_22$ ^s_37_22$ ^s_38_22$ ^s_39_22$ ^s_3_22$ ^s_40_22$ ^s_41_22$ ^s_42_22$ ^s_43_22$ ^s_44_22$ ^s_45_22$ ^s_46_22$ ^s_47_22$ ^s_48_22$ ^s_49_22$ ^s_4_22$ ^s_50_22$ ^s_51_22$ ^s_52_22$ ^s_53_22$ ^s_54_22$ ^s_55_22$ ^s_56_22$ ^s_57_22$ ^s_58_22$ ^s_59_22$ ^s_5_22$ ^s_60_22$ ^s_61_22$ ^s_62_22$ ^s_63_22$ ^s_6_22$ ^s_7_22$ ^s_8_22$ ^s_9_22$} -voltage_domains CORE -name pg_m8_8 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_8 -layer M8 -width .48 -pitch 9.091 -offset 0.605
add_pdn_connect -grid pg_m8_8 -layers {M7 M8}
add_pdn_connect -grid pg_m8_8 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_10$ ^t_10_10$ ^t_11_10$ ^t_12_10$ ^t_13_10$ ^t_14_10$ ^t_15_10$ ^t_16_10$ ^t_17_10$ ^t_18_10$ ^t_19_10$ ^t_1_10$ ^t_20_10$ ^t_21_10$ ^t_22_10$ ^t_23_10$ ^t_24_10$ ^t_25_10$ ^t_26_10$ ^t_27_10$ ^t_28_10$ ^t_29_10$ ^t_2_10$ ^t_30_10$ ^t_31_10$ ^t_32_10$ ^t_33_10$ ^t_34_10$ ^t_35_10$ ^t_36_10$ ^t_37_10$ ^t_38_10$ ^t_39_10$ ^t_3_10$ ^t_40_10$ ^t_41_10$ ^t_42_10$ ^t_43_10$ ^t_44_10$ ^t_45_10$ ^t_46_10$ ^t_47_10$ ^t_48_10$ ^t_49_10$ ^t_4_10$ ^t_50_10$ ^t_51_10$ ^t_52_10$ ^t_53_10$ ^t_54_10$ ^t_55_10$ ^t_56_10$ ^t_57_10$ ^t_58_10$ ^t_59_10$ ^t_5_10$ ^t_60_10$ ^t_61_10$ ^t_62_10$ ^t_63_10$ ^t_6_10$ ^t_7_10$ ^t_8_10$ ^t_9_10$} -voltage_domains CORE -name pg_m8_9 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_9 -layer M8 -width .48 -pitch 9.091 -offset 0.894
add_pdn_connect -grid pg_m8_9 -layers {M7 M8}
add_pdn_connect -grid pg_m8_9 -layers {M8 M9}
define_pdn_grid -macro -instances {^lv_S_1_E$ ^lv_S_1_W$} -voltage_domains CORE -name pg_m8_10 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_10 -layer M8 -width .48 -pitch 9.091 -offset 0.966
add_pdn_connect -grid pg_m8_10 -layers {M7 M8}
add_pdn_connect -grid pg_m8_10 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_2$ ^s_10_2$ ^s_11_2$ ^s_12_2$ ^s_13_2$ ^s_14_2$ ^s_15_2$ ^s_16_2$ ^s_17_2$ ^s_18_2$ ^s_19_2$ ^s_1_2$ ^s_20_2$ ^s_21_2$ ^s_22_2$ ^s_23_2$ ^s_24_2$ ^s_25_2$ ^s_26_2$ ^s_27_2$ ^s_28_2$ ^s_29_2$ ^s_2_2$ ^s_30_2$ ^s_31_2$ ^s_32_2$ ^s_33_2$ ^s_34_2$ ^s_35_2$ ^s_36_2$ ^s_37_2$ ^s_38_2$ ^s_39_2$ ^s_3_2$ ^s_40_2$ ^s_41_2$ ^s_42_2$ ^s_43_2$ ^s_44_2$ ^s_45_2$ ^s_46_2$ ^s_47_2$ ^s_48_2$ ^s_49_2$ ^s_4_2$ ^s_50_2$ ^s_51_2$ ^s_52_2$ ^s_53_2$ ^s_54_2$ ^s_55_2$ ^s_56_2$ ^s_57_2$ ^s_58_2$ ^s_59_2$ ^s_5_2$ ^s_60_2$ ^s_61_2$ ^s_62_2$ ^s_63_2$ ^s_6_2$ ^s_7_2$ ^s_8_2$ ^s_9_2$} -voltage_domains CORE -name pg_m8_11 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_11 -layer M8 -width .48 -pitch 9.091 -offset 1.072
add_pdn_connect -grid pg_m8_11 -layers {M7 M8}
add_pdn_connect -grid pg_m8_11 -layers {M8 M9}
define_pdn_grid -macro -instances {^sp_tree_top$} -voltage_domains CORE -name pg_m8_12 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_12 -layer M8 -width .48 -pitch 9.091 -offset 1.111
add_pdn_connect -grid pg_m8_12 -layers {M7 M8}
add_pdn_connect -grid pg_m8_12 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_6$ ^t_10_6$ ^t_11_6$ ^t_12_6$ ^t_13_6$ ^t_14_6$ ^t_15_6$ ^t_16_6$ ^t_17_6$ ^t_18_6$ ^t_19_6$ ^t_1_6$ ^t_20_6$ ^t_21_6$ ^t_22_6$ ^t_23_6$ ^t_24_6$ ^t_25_6$ ^t_26_6$ ^t_27_6$ ^t_28_6$ ^t_29_6$ ^t_2_6$ ^t_30_6$ ^t_31_6$ ^t_32_6$ ^t_33_6$ ^t_34_6$ ^t_35_6$ ^t_36_6$ ^t_37_6$ ^t_38_6$ ^t_39_6$ ^t_3_6$ ^t_40_6$ ^t_41_6$ ^t_42_6$ ^t_43_6$ ^t_44_6$ ^t_45_6$ ^t_46_6$ ^t_47_6$ ^t_48_6$ ^t_49_6$ ^t_4_6$ ^t_50_6$ ^t_51_6$ ^t_52_6$ ^t_53_6$ ^t_54_6$ ^t_55_6$ ^t_56_6$ ^t_57_6$ ^t_58_6$ ^t_59_6$ ^t_5_6$ ^t_60_6$ ^t_61_6$ ^t_62_6$ ^t_63_6$ ^t_6_6$ ^t_7_6$ ^t_8_6$ ^t_9_6$} -voltage_domains CORE -name pg_m8_13 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_13 -layer M8 -width .48 -pitch 9.091 -offset 1.125
add_pdn_connect -grid pg_m8_13 -layers {M7 M8}
add_pdn_connect -grid pg_m8_13 -layers {M8 M9}
define_pdn_grid -macro -instances {^lfifo_ES$ ^lfifo_WS$} -voltage_domains CORE -name pg_m8_14 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_14 -layer M8 -width .48 -pitch 9.091 -offset 1.174
add_pdn_connect -grid pg_m8_14 -layers {M7 M8}
add_pdn_connect -grid pg_m8_14 -layers {M8 M9}
define_pdn_grid -macro -instances {^sp_vector_memory$} -voltage_domains CORE -name pg_m8_15 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_15 -layer M8 -width .48 -pitch 9.091 -offset 1.323
add_pdn_connect -grid pg_m8_15 -layers {M7 M8}
add_pdn_connect -grid pg_m8_15 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_21$ ^s_10_21$ ^s_11_21$ ^s_12_21$ ^s_13_21$ ^s_14_21$ ^s_15_21$ ^s_16_21$ ^s_17_21$ ^s_18_21$ ^s_19_21$ ^s_1_21$ ^s_20_21$ ^s_21_21$ ^s_22_21$ ^s_23_21$ ^s_24_21$ ^s_25_21$ ^s_26_21$ ^s_27_21$ ^s_28_21$ ^s_29_21$ ^s_2_21$ ^s_30_21$ ^s_31_21$ ^s_32_21$ ^s_33_21$ ^s_34_21$ ^s_35_21$ ^s_36_21$ ^s_37_21$ ^s_38_21$ ^s_39_21$ ^s_3_21$ ^s_40_21$ ^s_41_21$ ^s_42_21$ ^s_43_21$ ^s_44_21$ ^s_45_21$ ^s_46_21$ ^s_47_21$ ^s_48_21$ ^s_49_21$ ^s_4_21$ ^s_50_21$ ^s_51_21$ ^s_52_21$ ^s_53_21$ ^s_54_21$ ^s_55_21$ ^s_56_21$ ^s_57_21$ ^s_58_21$ ^s_59_21$ ^s_5_21$ ^s_60_21$ ^s_61_21$ ^s_62_21$ ^s_63_21$ ^s_6_21$ ^s_7_21$ ^s_8_21$ ^s_9_21$} -voltage_domains CORE -name pg_m8_16 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_16 -layer M8 -width .48 -pitch 9.091 -offset 1.363
add_pdn_connect -grid pg_m8_16 -layers {M7 M8}
add_pdn_connect -grid pg_m8_16 -layers {M8 M9}
define_pdn_grid -macro -instances {^re_EN_1$ ^re_WN_1$} -voltage_domains CORE -name pg_m8_17 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_17 -layer M8 -width .48 -pitch 9.091 -offset 1.446
add_pdn_connect -grid pg_m8_17 -layers {M7 M8}
add_pdn_connect -grid pg_m8_17 -layers {M8 M9}
define_pdn_grid -macro -instances {^re_EN_5$ ^re_WN_5$} -voltage_domains CORE -name pg_m8_18 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_18 -layer M8 -width .48 -pitch 9.091 -offset 1.622
add_pdn_connect -grid pg_m8_18 -layers {M7 M8}
add_pdn_connect -grid pg_m8_18 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_9$ ^t_10_9$ ^t_11_9$ ^t_12_9$ ^t_13_9$ ^t_14_9$ ^t_15_9$ ^t_16_9$ ^t_17_9$ ^t_18_9$ ^t_19_9$ ^t_1_9$ ^t_20_9$ ^t_21_9$ ^t_22_9$ ^t_23_9$ ^t_24_9$ ^t_25_9$ ^t_26_9$ ^t_27_9$ ^t_28_9$ ^t_29_9$ ^t_2_9$ ^t_30_9$ ^t_31_9$ ^t_32_9$ ^t_33_9$ ^t_34_9$ ^t_35_9$ ^t_36_9$ ^t_37_9$ ^t_38_9$ ^t_39_9$ ^t_3_9$ ^t_40_9$ ^t_41_9$ ^t_42_9$ ^t_43_9$ ^t_44_9$ ^t_45_9$ ^t_46_9$ ^t_47_9$ ^t_48_9$ ^t_49_9$ ^t_4_9$ ^t_50_9$ ^t_51_9$ ^t_52_9$ ^t_53_9$ ^t_54_9$ ^t_55_9$ ^t_56_9$ ^t_57_9$ ^t_58_9$ ^t_59_9$ ^t_5_9$ ^t_60_9$ ^t_61_9$ ^t_62_9$ ^t_63_9$ ^t_6_9$ ^t_7_9$ ^t_8_9$ ^t_9_9$} -voltage_domains CORE -name pg_m8_19 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_19 -layer M8 -width .48 -pitch 9.091 -offset 1.652
add_pdn_connect -grid pg_m8_19 -layers {M7 M8}
add_pdn_connect -grid pg_m8_19 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_1$ ^s_10_1$ ^s_11_1$ ^s_12_1$ ^s_13_1$ ^s_14_1$ ^s_15_1$ ^s_16_1$ ^s_17_1$ ^s_18_1$ ^s_19_1$ ^s_1_1$ ^s_20_1$ ^s_21_1$ ^s_22_1$ ^s_23_1$ ^s_24_1$ ^s_25_1$ ^s_26_1$ ^s_27_1$ ^s_28_1$ ^s_29_1$ ^s_2_1$ ^s_30_1$ ^s_31_1$ ^s_32_1$ ^s_33_1$ ^s_34_1$ ^s_35_1$ ^s_36_1$ ^s_37_1$ ^s_38_1$ ^s_39_1$ ^s_3_1$ ^s_40_1$ ^s_41_1$ ^s_42_1$ ^s_43_1$ ^s_44_1$ ^s_45_1$ ^s_46_1$ ^s_47_1$ ^s_48_1$ ^s_49_1$ ^s_4_1$ ^s_50_1$ ^s_51_1$ ^s_52_1$ ^s_53_1$ ^s_54_1$ ^s_55_1$ ^s_56_1$ ^s_57_1$ ^s_58_1$ ^s_59_1$ ^s_5_1$ ^s_60_1$ ^s_61_1$ ^s_62_1$ ^s_63_1$ ^s_6_1$ ^s_7_1$ ^s_8_1$ ^s_9_1$} -voltage_domains CORE -name pg_m8_20 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_20 -layer M8 -width .48 -pitch 9.091 -offset 1.830
add_pdn_connect -grid pg_m8_20 -layers {M7 M8}
add_pdn_connect -grid pg_m8_20 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_5$ ^t_10_5$ ^t_11_5$ ^t_12_5$ ^t_13_5$ ^t_14_5$ ^t_15_5$ ^t_16_5$ ^t_17_5$ ^t_18_5$ ^t_19_5$ ^t_1_5$ ^t_20_5$ ^t_21_5$ ^t_22_5$ ^t_23_5$ ^t_24_5$ ^t_25_5$ ^t_26_5$ ^t_27_5$ ^t_28_5$ ^t_29_5$ ^t_2_5$ ^t_30_5$ ^t_31_5$ ^t_32_5$ ^t_33_5$ ^t_34_5$ ^t_35_5$ ^t_36_5$ ^t_37_5$ ^t_38_5$ ^t_39_5$ ^t_3_5$ ^t_40_5$ ^t_41_5$ ^t_42_5$ ^t_43_5$ ^t_44_5$ ^t_45_5$ ^t_46_5$ ^t_47_5$ ^t_48_5$ ^t_49_5$ ^t_4_5$ ^t_50_5$ ^t_51_5$ ^t_52_5$ ^t_53_5$ ^t_54_5$ ^t_55_5$ ^t_56_5$ ^t_57_5$ ^t_58_5$ ^t_59_5$ ^t_5_5$ ^t_60_5$ ^t_61_5$ ^t_62_5$ ^t_63_5$ ^t_6_5$ ^t_7_5$ ^t_8_5$ ^t_9_5$} -voltage_domains CORE -name pg_m8_21 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_21 -layer M8 -width .48 -pitch 9.091 -offset 1.883
add_pdn_connect -grid pg_m8_21 -layers {M7 M8}
add_pdn_connect -grid pg_m8_21 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_20$ ^s_10_20$ ^s_11_20$ ^s_12_20$ ^s_13_20$ ^s_14_20$ ^s_15_20$ ^s_16_20$ ^s_17_20$ ^s_18_20$ ^s_19_20$ ^s_1_20$ ^s_20_20$ ^s_21_20$ ^s_22_20$ ^s_23_20$ ^s_24_20$ ^s_25_20$ ^s_26_20$ ^s_27_20$ ^s_28_20$ ^s_29_20$ ^s_2_20$ ^s_30_20$ ^s_31_20$ ^s_32_20$ ^s_33_20$ ^s_34_20$ ^s_35_20$ ^s_36_20$ ^s_37_20$ ^s_38_20$ ^s_39_20$ ^s_3_20$ ^s_40_20$ ^s_41_20$ ^s_42_20$ ^s_43_20$ ^s_44_20$ ^s_45_20$ ^s_46_20$ ^s_47_20$ ^s_48_20$ ^s_49_20$ ^s_4_20$ ^s_50_20$ ^s_51_20$ ^s_52_20$ ^s_53_20$ ^s_54_20$ ^s_55_20$ ^s_56_20$ ^s_57_20$ ^s_58_20$ ^s_59_20$ ^s_5_20$ ^s_60_20$ ^s_61_20$ ^s_62_20$ ^s_63_20$ ^s_6_20$ ^s_7_20$ ^s_8_20$ ^s_9_20$} -voltage_domains CORE -name pg_m8_22 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_22 -layer M8 -width .48 -pitch 9.091 -offset 2.121
add_pdn_connect -grid pg_m8_22 -layers {M7 M8}
add_pdn_connect -grid pg_m8_22 -layers {M8 M9}
define_pdn_grid -macro -instances {^io_collective$ ^io_embedding_rom$ ^io_serdes$ ^io_ucie$} -voltage_domains CORE -name pg_m8_23 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_23 -layer M8 -width .48 -pitch 9.091 -offset 2.174
add_pdn_connect -grid pg_m8_23 -layers {M7 M8}
add_pdn_connect -grid pg_m8_23 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_16$ ^s_10_16$ ^s_11_16$ ^s_12_16$ ^s_13_16$ ^s_14_16$ ^s_15_16$ ^s_16_16$ ^s_17_16$ ^s_18_16$ ^s_19_16$ ^s_1_16$ ^s_20_16$ ^s_21_16$ ^s_22_16$ ^s_23_16$ ^s_24_16$ ^s_25_16$ ^s_26_16$ ^s_27_16$ ^s_28_16$ ^s_29_16$ ^s_2_16$ ^s_30_16$ ^s_31_16$ ^s_32_16$ ^s_33_16$ ^s_34_16$ ^s_35_16$ ^s_36_16$ ^s_37_16$ ^s_38_16$ ^s_39_16$ ^s_3_16$ ^s_40_16$ ^s_41_16$ ^s_42_16$ ^s_43_16$ ^s_44_16$ ^s_45_16$ ^s_46_16$ ^s_47_16$ ^s_48_16$ ^s_49_16$ ^s_4_16$ ^s_50_16$ ^s_51_16$ ^s_52_16$ ^s_53_16$ ^s_54_16$ ^s_55_16$ ^s_56_16$ ^s_57_16$ ^s_58_16$ ^s_59_16$ ^s_5_16$ ^s_60_16$ ^s_61_16$ ^s_62_16$ ^s_63_16$ ^s_6_16$ ^s_7_16$ ^s_8_16$ ^s_9_16$} -voltage_domains CORE -name pg_m8_24 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_24 -layer M8 -width .48 -pitch 9.091 -offset 2.352
add_pdn_connect -grid pg_m8_24 -layers {M7 M8}
add_pdn_connect -grid pg_m8_24 -layers {M8 M9}
define_pdn_grid -macro -instances {^re_ES_3$ ^re_WS_3$} -voltage_domains CORE -name pg_m8_25 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_25 -layer M8 -width .48 -pitch 9.091 -offset 2.361
add_pdn_connect -grid pg_m8_25 -layers {M7 M8}
add_pdn_connect -grid pg_m8_25 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_8$ ^t_10_8$ ^t_11_8$ ^t_12_8$ ^t_13_8$ ^t_14_8$ ^t_15_8$ ^t_16_8$ ^t_17_8$ ^t_18_8$ ^t_19_8$ ^t_1_8$ ^t_20_8$ ^t_21_8$ ^t_22_8$ ^t_23_8$ ^t_24_8$ ^t_25_8$ ^t_26_8$ ^t_27_8$ ^t_28_8$ ^t_29_8$ ^t_2_8$ ^t_30_8$ ^t_31_8$ ^t_32_8$ ^t_33_8$ ^t_34_8$ ^t_35_8$ ^t_36_8$ ^t_37_8$ ^t_38_8$ ^t_39_8$ ^t_3_8$ ^t_40_8$ ^t_41_8$ ^t_42_8$ ^t_43_8$ ^t_44_8$ ^t_45_8$ ^t_46_8$ ^t_47_8$ ^t_48_8$ ^t_49_8$ ^t_4_8$ ^t_50_8$ ^t_51_8$ ^t_52_8$ ^t_53_8$ ^t_54_8$ ^t_55_8$ ^t_56_8$ ^t_57_8$ ^t_58_8$ ^t_59_8$ ^t_5_8$ ^t_60_8$ ^t_61_8$ ^t_62_8$ ^t_63_8$ ^t_6_8$ ^t_7_8$ ^t_8_8$ ^t_9_8$} -voltage_domains CORE -name pg_m8_26 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_26 -layer M8 -width .48 -pitch 9.091 -offset 2.410
add_pdn_connect -grid pg_m8_26 -layers {M7 M8}
add_pdn_connect -grid pg_m8_26 -layers {M8 M9}
define_pdn_grid -macro -instances {^sp_port_tiles_5$ ^sp_port_tiles_5_f1$} -voltage_domains CORE -name pg_m8_27 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_27 -layer M8 -width .48 -pitch 9.091 -offset 2.549
add_pdn_connect -grid pg_m8_27 -layers {M7 M8}
add_pdn_connect -grid pg_m8_27 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_0$ ^s_10_0$ ^s_11_0$ ^s_12_0$ ^s_13_0$ ^s_14_0$ ^s_15_0$ ^s_16_0$ ^s_17_0$ ^s_18_0$ ^s_19_0$ ^s_1_0$ ^s_20_0$ ^s_21_0$ ^s_22_0$ ^s_23_0$ ^s_24_0$ ^s_25_0$ ^s_26_0$ ^s_27_0$ ^s_28_0$ ^s_29_0$ ^s_2_0$ ^s_30_0$ ^s_31_0$ ^s_32_0$ ^s_33_0$ ^s_34_0$ ^s_35_0$ ^s_36_0$ ^s_37_0$ ^s_38_0$ ^s_39_0$ ^s_3_0$ ^s_40_0$ ^s_41_0$ ^s_42_0$ ^s_43_0$ ^s_44_0$ ^s_45_0$ ^s_46_0$ ^s_47_0$ ^s_48_0$ ^s_49_0$ ^s_4_0$ ^s_50_0$ ^s_51_0$ ^s_52_0$ ^s_53_0$ ^s_54_0$ ^s_55_0$ ^s_56_0$ ^s_57_0$ ^s_58_0$ ^s_59_0$ ^s_5_0$ ^s_60_0$ ^s_61_0$ ^s_62_0$ ^s_63_0$ ^s_6_0$ ^s_7_0$ ^s_8_0$ ^s_9_0$} -voltage_domains CORE -name pg_m8_28 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_28 -layer M8 -width .48 -pitch 9.091 -offset 2.588
add_pdn_connect -grid pg_m8_28 -layers {M7 M8}
add_pdn_connect -grid pg_m8_28 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_4$ ^t_10_4$ ^t_11_4$ ^t_12_4$ ^t_13_4$ ^t_14_4$ ^t_15_4$ ^t_16_4$ ^t_17_4$ ^t_18_4$ ^t_19_4$ ^t_1_4$ ^t_20_4$ ^t_21_4$ ^t_22_4$ ^t_23_4$ ^t_24_4$ ^t_25_4$ ^t_26_4$ ^t_27_4$ ^t_28_4$ ^t_29_4$ ^t_2_4$ ^t_30_4$ ^t_31_4$ ^t_32_4$ ^t_33_4$ ^t_34_4$ ^t_35_4$ ^t_36_4$ ^t_37_4$ ^t_38_4$ ^t_39_4$ ^t_3_4$ ^t_40_4$ ^t_41_4$ ^t_42_4$ ^t_43_4$ ^t_44_4$ ^t_45_4$ ^t_46_4$ ^t_47_4$ ^t_48_4$ ^t_49_4$ ^t_4_4$ ^t_50_4$ ^t_51_4$ ^t_52_4$ ^t_53_4$ ^t_54_4$ ^t_55_4$ ^t_56_4$ ^t_57_4$ ^t_58_4$ ^t_59_4$ ^t_5_4$ ^t_60_4$ ^t_61_4$ ^t_62_4$ ^t_63_4$ ^t_6_4$ ^t_7_4$ ^t_8_4$ ^t_9_4$} -voltage_domains CORE -name pg_m8_29 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_29 -layer M8 -width .48 -pitch 9.091 -offset 2.641
add_pdn_connect -grid pg_m8_29 -layers {M7 M8}
add_pdn_connect -grid pg_m8_29 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_19$ ^s_10_19$ ^s_11_19$ ^s_12_19$ ^s_13_19$ ^s_14_19$ ^s_15_19$ ^s_16_19$ ^s_17_19$ ^s_18_19$ ^s_19_19$ ^s_1_19$ ^s_20_19$ ^s_21_19$ ^s_22_19$ ^s_23_19$ ^s_24_19$ ^s_25_19$ ^s_26_19$ ^s_27_19$ ^s_28_19$ ^s_29_19$ ^s_2_19$ ^s_30_19$ ^s_31_19$ ^s_32_19$ ^s_33_19$ ^s_34_19$ ^s_35_19$ ^s_36_19$ ^s_37_19$ ^s_38_19$ ^s_39_19$ ^s_3_19$ ^s_40_19$ ^s_41_19$ ^s_42_19$ ^s_43_19$ ^s_44_19$ ^s_45_19$ ^s_46_19$ ^s_47_19$ ^s_48_19$ ^s_49_19$ ^s_4_19$ ^s_50_19$ ^s_51_19$ ^s_52_19$ ^s_53_19$ ^s_54_19$ ^s_55_19$ ^s_56_19$ ^s_57_19$ ^s_58_19$ ^s_59_19$ ^s_5_19$ ^s_60_19$ ^s_61_19$ ^s_62_19$ ^s_63_19$ ^s_6_19$ ^s_7_19$ ^s_8_19$ ^s_9_19$} -voltage_domains CORE -name pg_m8_30 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_30 -layer M8 -width .48 -pitch 9.091 -offset 2.879
add_pdn_connect -grid pg_m8_30 -layers {M7 M8}
add_pdn_connect -grid pg_m8_30 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_23$ ^t_10_23$ ^t_11_23$ ^t_12_23$ ^t_13_23$ ^t_14_23$ ^t_15_23$ ^t_16_23$ ^t_17_23$ ^t_18_23$ ^t_19_23$ ^t_1_23$ ^t_20_23$ ^t_21_23$ ^t_22_23$ ^t_23_23$ ^t_24_23$ ^t_25_23$ ^t_26_23$ ^t_27_23$ ^t_28_23$ ^t_29_23$ ^t_2_23$ ^t_30_23$ ^t_31_23$ ^t_32_23$ ^t_33_23$ ^t_34_23$ ^t_35_23$ ^t_36_23$ ^t_37_23$ ^t_38_23$ ^t_39_23$ ^t_3_23$ ^t_40_23$ ^t_41_23$ ^t_42_23$ ^t_43_23$ ^t_44_23$ ^t_45_23$ ^t_46_23$ ^t_47_23$ ^t_48_23$ ^t_49_23$ ^t_4_23$ ^t_50_23$ ^t_51_23$ ^t_52_23$ ^t_53_23$ ^t_54_23$ ^t_55_23$ ^t_56_23$ ^t_57_23$ ^t_58_23$ ^t_59_23$ ^t_5_23$ ^t_60_23$ ^t_61_23$ ^t_62_23$ ^t_63_23$ ^t_6_23$ ^t_7_23$ ^t_8_23$ ^t_9_23$} -voltage_domains CORE -name pg_m8_31 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_31 -layer M8 -width .48 -pitch 9.091 -offset 2.932
add_pdn_connect -grid pg_m8_31 -layers {M7 M8}
add_pdn_connect -grid pg_m8_31 -layers {M8 M9}
define_pdn_grid -macro -instances {^sp_port_tiles_2$} -voltage_domains CORE -name pg_m8_32 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_32 -layer M8 -width .48 -pitch 9.091 -offset 2.955
add_pdn_connect -grid pg_m8_32 -layers {M7 M8}
add_pdn_connect -grid pg_m8_32 -layers {M8 M9}
define_pdn_grid -macro -instances {^sp_port_tiles_0$ ^sp_port_tiles_0_f1$} -voltage_domains CORE -name pg_m8_33 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_33 -layer M8 -width .48 -pitch 9.091 -offset 3.016
add_pdn_connect -grid pg_m8_33 -layers {M7 M8}
add_pdn_connect -grid pg_m8_33 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_15$ ^s_10_15$ ^s_11_15$ ^s_12_15$ ^s_13_15$ ^s_14_15$ ^s_15_15$ ^s_16_15$ ^s_17_15$ ^s_18_15$ ^s_19_15$ ^s_1_15$ ^s_20_15$ ^s_21_15$ ^s_22_15$ ^s_23_15$ ^s_24_15$ ^s_25_15$ ^s_26_15$ ^s_27_15$ ^s_28_15$ ^s_29_15$ ^s_2_15$ ^s_30_15$ ^s_31_15$ ^s_32_15$ ^s_33_15$ ^s_34_15$ ^s_35_15$ ^s_36_15$ ^s_37_15$ ^s_38_15$ ^s_39_15$ ^s_3_15$ ^s_40_15$ ^s_41_15$ ^s_42_15$ ^s_43_15$ ^s_44_15$ ^s_45_15$ ^s_46_15$ ^s_47_15$ ^s_48_15$ ^s_49_15$ ^s_4_15$ ^s_50_15$ ^s_51_15$ ^s_52_15$ ^s_53_15$ ^s_54_15$ ^s_55_15$ ^s_56_15$ ^s_57_15$ ^s_58_15$ ^s_59_15$ ^s_5_15$ ^s_60_15$ ^s_61_15$ ^s_62_15$ ^s_63_15$ ^s_6_15$ ^s_7_15$ ^s_8_15$ ^s_9_15$} -voltage_domains CORE -name pg_m8_34 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_34 -layer M8 -width .48 -pitch 9.091 -offset 3.110
add_pdn_connect -grid pg_m8_34 -layers {M7 M8}
add_pdn_connect -grid pg_m8_34 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_7$ ^t_10_7$ ^t_11_7$ ^t_12_7$ ^t_13_7$ ^t_14_7$ ^t_15_7$ ^t_16_7$ ^t_17_7$ ^t_18_7$ ^t_19_7$ ^t_1_7$ ^t_20_7$ ^t_21_7$ ^t_22_7$ ^t_23_7$ ^t_24_7$ ^t_25_7$ ^t_26_7$ ^t_27_7$ ^t_28_7$ ^t_29_7$ ^t_2_7$ ^t_30_7$ ^t_31_7$ ^t_32_7$ ^t_33_7$ ^t_34_7$ ^t_35_7$ ^t_36_7$ ^t_37_7$ ^t_38_7$ ^t_39_7$ ^t_3_7$ ^t_40_7$ ^t_41_7$ ^t_42_7$ ^t_43_7$ ^t_44_7$ ^t_45_7$ ^t_46_7$ ^t_47_7$ ^t_48_7$ ^t_49_7$ ^t_4_7$ ^t_50_7$ ^t_51_7$ ^t_52_7$ ^t_53_7$ ^t_54_7$ ^t_55_7$ ^t_56_7$ ^t_57_7$ ^t_58_7$ ^t_59_7$ ^t_5_7$ ^t_60_7$ ^t_61_7$ ^t_62_7$ ^t_63_7$ ^t_6_7$ ^t_7_7$ ^t_8_7$ ^t_9_7$} -voltage_domains CORE -name pg_m8_35 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_35 -layer M8 -width .48 -pitch 9.091 -offset 3.168
add_pdn_connect -grid pg_m8_35 -layers {M7 M8}
add_pdn_connect -grid pg_m8_35 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_3$ ^t_10_3$ ^t_11_3$ ^t_12_3$ ^t_13_3$ ^t_14_3$ ^t_15_3$ ^t_16_3$ ^t_17_3$ ^t_18_3$ ^t_19_3$ ^t_1_3$ ^t_20_3$ ^t_21_3$ ^t_22_3$ ^t_23_3$ ^t_24_3$ ^t_25_3$ ^t_26_3$ ^t_27_3$ ^t_28_3$ ^t_29_3$ ^t_2_3$ ^t_30_3$ ^t_31_3$ ^t_32_3$ ^t_33_3$ ^t_34_3$ ^t_35_3$ ^t_36_3$ ^t_37_3$ ^t_38_3$ ^t_39_3$ ^t_3_3$ ^t_40_3$ ^t_41_3$ ^t_42_3$ ^t_43_3$ ^t_44_3$ ^t_45_3$ ^t_46_3$ ^t_47_3$ ^t_48_3$ ^t_49_3$ ^t_4_3$ ^t_50_3$ ^t_51_3$ ^t_52_3$ ^t_53_3$ ^t_54_3$ ^t_55_3$ ^t_56_3$ ^t_57_3$ ^t_58_3$ ^t_59_3$ ^t_5_3$ ^t_60_3$ ^t_61_3$ ^t_62_3$ ^t_63_3$ ^t_6_3$ ^t_7_3$ ^t_8_3$ ^t_9_3$} -voltage_domains CORE -name pg_m8_36 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_36 -layer M8 -width .48 -pitch 9.091 -offset 3.399
add_pdn_connect -grid pg_m8_36 -layers {M7 M8}
add_pdn_connect -grid pg_m8_36 -layers {M8 M9}
define_pdn_grid -macro -instances {^re_EN_2$ ^re_WN_2$} -voltage_domains CORE -name pg_m8_37 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_37 -layer M8 -width .48 -pitch 9.091 -offset 3.466
add_pdn_connect -grid pg_m8_37 -layers {M7 M8}
add_pdn_connect -grid pg_m8_37 -layers {M8 M9}
define_pdn_grid -macro -instances {^lv_N_2$} -voltage_domains CORE -name pg_m8_38 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_38 -layer M8 -width .48 -pitch 9.091 -offset 3.560
add_pdn_connect -grid pg_m8_38 -layers {M7 M8}
add_pdn_connect -grid pg_m8_38 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_18$ ^s_10_18$ ^s_11_18$ ^s_12_18$ ^s_13_18$ ^s_14_18$ ^s_15_18$ ^s_16_18$ ^s_17_18$ ^s_18_18$ ^s_19_18$ ^s_1_18$ ^s_20_18$ ^s_21_18$ ^s_22_18$ ^s_23_18$ ^s_24_18$ ^s_25_18$ ^s_26_18$ ^s_27_18$ ^s_28_18$ ^s_29_18$ ^s_2_18$ ^s_30_18$ ^s_31_18$ ^s_32_18$ ^s_33_18$ ^s_34_18$ ^s_35_18$ ^s_36_18$ ^s_37_18$ ^s_38_18$ ^s_39_18$ ^s_3_18$ ^s_40_18$ ^s_41_18$ ^s_42_18$ ^s_43_18$ ^s_44_18$ ^s_45_18$ ^s_46_18$ ^s_47_18$ ^s_48_18$ ^s_49_18$ ^s_4_18$ ^s_50_18$ ^s_51_18$ ^s_52_18$ ^s_53_18$ ^s_54_18$ ^s_55_18$ ^s_56_18$ ^s_57_18$ ^s_58_18$ ^s_59_18$ ^s_5_18$ ^s_60_18$ ^s_61_18$ ^s_62_18$ ^s_63_18$ ^s_6_18$ ^s_7_18$ ^s_8_18$ ^s_9_18$} -voltage_domains CORE -name pg_m8_39 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_39 -layer M8 -width .48 -pitch 9.091 -offset 3.637
add_pdn_connect -grid pg_m8_39 -layers {M7 M8}
add_pdn_connect -grid pg_m8_39 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_22$ ^t_10_22$ ^t_11_22$ ^t_12_22$ ^t_13_22$ ^t_14_22$ ^t_15_22$ ^t_16_22$ ^t_17_22$ ^t_18_22$ ^t_19_22$ ^t_1_22$ ^t_20_22$ ^t_21_22$ ^t_22_22$ ^t_23_22$ ^t_24_22$ ^t_25_22$ ^t_26_22$ ^t_27_22$ ^t_28_22$ ^t_29_22$ ^t_2_22$ ^t_30_22$ ^t_31_22$ ^t_32_22$ ^t_33_22$ ^t_34_22$ ^t_35_22$ ^t_36_22$ ^t_37_22$ ^t_38_22$ ^t_39_22$ ^t_3_22$ ^t_40_22$ ^t_41_22$ ^t_42_22$ ^t_43_22$ ^t_44_22$ ^t_45_22$ ^t_46_22$ ^t_47_22$ ^t_48_22$ ^t_49_22$ ^t_4_22$ ^t_50_22$ ^t_51_22$ ^t_52_22$ ^t_53_22$ ^t_54_22$ ^t_55_22$ ^t_56_22$ ^t_57_22$ ^t_58_22$ ^t_59_22$ ^t_5_22$ ^t_60_22$ ^t_61_22$ ^t_62_22$ ^t_63_22$ ^t_6_22$ ^t_7_22$ ^t_8_22$ ^t_9_22$} -voltage_domains CORE -name pg_m8_40 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_40 -layer M8 -width .48 -pitch 9.091 -offset 3.690
add_pdn_connect -grid pg_m8_40 -layers {M7 M8}
add_pdn_connect -grid pg_m8_40 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_14$ ^s_10_14$ ^s_11_14$ ^s_12_14$ ^s_13_14$ ^s_14_14$ ^s_15_14$ ^s_16_14$ ^s_17_14$ ^s_18_14$ ^s_19_14$ ^s_1_14$ ^s_20_14$ ^s_21_14$ ^s_22_14$ ^s_23_14$ ^s_24_14$ ^s_25_14$ ^s_26_14$ ^s_27_14$ ^s_28_14$ ^s_29_14$ ^s_2_14$ ^s_30_14$ ^s_31_14$ ^s_32_14$ ^s_33_14$ ^s_34_14$ ^s_35_14$ ^s_36_14$ ^s_37_14$ ^s_38_14$ ^s_39_14$ ^s_3_14$ ^s_40_14$ ^s_41_14$ ^s_42_14$ ^s_43_14$ ^s_44_14$ ^s_45_14$ ^s_46_14$ ^s_47_14$ ^s_48_14$ ^s_49_14$ ^s_4_14$ ^s_50_14$ ^s_51_14$ ^s_52_14$ ^s_53_14$ ^s_54_14$ ^s_55_14$ ^s_56_14$ ^s_57_14$ ^s_58_14$ ^s_59_14$ ^s_5_14$ ^s_60_14$ ^s_61_14$ ^s_62_14$ ^s_63_14$ ^s_6_14$ ^s_7_14$ ^s_8_14$ ^s_9_14$} -voltage_domains CORE -name pg_m8_41 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_41 -layer M8 -width .48 -pitch 9.091 -offset 3.868
add_pdn_connect -grid pg_m8_41 -layers {M7 M8}
add_pdn_connect -grid pg_m8_41 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_2$ ^t_10_2$ ^t_11_2$ ^t_12_2$ ^t_13_2$ ^t_14_2$ ^t_15_2$ ^t_16_2$ ^t_17_2$ ^t_18_2$ ^t_19_2$ ^t_1_2$ ^t_20_2$ ^t_21_2$ ^t_22_2$ ^t_23_2$ ^t_24_2$ ^t_25_2$ ^t_26_2$ ^t_27_2$ ^t_28_2$ ^t_29_2$ ^t_2_2$ ^t_30_2$ ^t_31_2$ ^t_32_2$ ^t_33_2$ ^t_34_2$ ^t_35_2$ ^t_36_2$ ^t_37_2$ ^t_38_2$ ^t_39_2$ ^t_3_2$ ^t_40_2$ ^t_41_2$ ^t_42_2$ ^t_43_2$ ^t_44_2$ ^t_45_2$ ^t_46_2$ ^t_47_2$ ^t_48_2$ ^t_49_2$ ^t_4_2$ ^t_50_2$ ^t_51_2$ ^t_52_2$ ^t_53_2$ ^t_54_2$ ^t_55_2$ ^t_56_2$ ^t_57_2$ ^t_58_2$ ^t_59_2$ ^t_5_2$ ^t_60_2$ ^t_61_2$ ^t_62_2$ ^t_63_2$ ^t_6_2$ ^t_7_2$ ^t_8_2$ ^t_9_2$} -voltage_domains CORE -name pg_m8_42 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_42 -layer M8 -width .48 -pitch 9.091 -offset 4.157
add_pdn_connect -grid pg_m8_42 -layers {M7 M8}
add_pdn_connect -grid pg_m8_42 -layers {M8 M9}
define_pdn_grid -macro -instances {^ctrl_ES$ ^ctrl_WS$ ^re_ES_0$ ^re_WS_0$} -voltage_domains CORE -name pg_m8_43 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_43 -layer M8 -width .48 -pitch 9.091 -offset 4.205
add_pdn_connect -grid pg_m8_43 -layers {M7 M8}
add_pdn_connect -grid pg_m8_43 -layers {M8 M9}
define_pdn_grid -macro -instances {^lv_S_2_E$ ^lv_S_2_W$} -voltage_domains CORE -name pg_m8_44 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_44 -layer M8 -width .48 -pitch 9.091 -offset 4.287
add_pdn_connect -grid pg_m8_44 -layers {M7 M8}
add_pdn_connect -grid pg_m8_44 -layers {M8 M9}
define_pdn_grid -macro -instances {^re_ES_4$ ^re_WS_4$} -voltage_domains CORE -name pg_m8_45 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_45 -layer M8 -width .48 -pitch 9.091 -offset 4.381
add_pdn_connect -grid pg_m8_45 -layers {M7 M8}
add_pdn_connect -grid pg_m8_45 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_17$ ^s_10_17$ ^s_11_17$ ^s_12_17$ ^s_13_17$ ^s_14_17$ ^s_15_17$ ^s_16_17$ ^s_17_17$ ^s_18_17$ ^s_19_17$ ^s_1_17$ ^s_20_17$ ^s_21_17$ ^s_22_17$ ^s_23_17$ ^s_24_17$ ^s_25_17$ ^s_26_17$ ^s_27_17$ ^s_28_17$ ^s_29_17$ ^s_2_17$ ^s_30_17$ ^s_31_17$ ^s_32_17$ ^s_33_17$ ^s_34_17$ ^s_35_17$ ^s_36_17$ ^s_37_17$ ^s_38_17$ ^s_39_17$ ^s_3_17$ ^s_40_17$ ^s_41_17$ ^s_42_17$ ^s_43_17$ ^s_44_17$ ^s_45_17$ ^s_46_17$ ^s_47_17$ ^s_48_17$ ^s_49_17$ ^s_4_17$ ^s_50_17$ ^s_51_17$ ^s_52_17$ ^s_53_17$ ^s_54_17$ ^s_55_17$ ^s_56_17$ ^s_57_17$ ^s_58_17$ ^s_59_17$ ^s_5_17$ ^s_60_17$ ^s_61_17$ ^s_62_17$ ^s_63_17$ ^s_6_17$ ^s_7_17$ ^s_8_17$ ^s_9_17$} -voltage_domains CORE -name pg_m8_46 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_46 -layer M8 -width .48 -pitch 9.091 -offset 4.395
add_pdn_connect -grid pg_m8_46 -layers {M7 M8}
add_pdn_connect -grid pg_m8_46 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_21$ ^t_10_21$ ^t_11_21$ ^t_12_21$ ^t_13_21$ ^t_14_21$ ^t_15_21$ ^t_16_21$ ^t_17_21$ ^t_18_21$ ^t_19_21$ ^t_1_21$ ^t_20_21$ ^t_21_21$ ^t_22_21$ ^t_23_21$ ^t_24_21$ ^t_25_21$ ^t_26_21$ ^t_27_21$ ^t_28_21$ ^t_29_21$ ^t_2_21$ ^t_30_21$ ^t_31_21$ ^t_32_21$ ^t_33_21$ ^t_34_21$ ^t_35_21$ ^t_36_21$ ^t_37_21$ ^t_38_21$ ^t_39_21$ ^t_3_21$ ^t_40_21$ ^t_41_21$ ^t_42_21$ ^t_43_21$ ^t_44_21$ ^t_45_21$ ^t_46_21$ ^t_47_21$ ^t_48_21$ ^t_49_21$ ^t_4_21$ ^t_50_21$ ^t_51_21$ ^t_52_21$ ^t_53_21$ ^t_54_21$ ^t_55_21$ ^t_56_21$ ^t_57_21$ ^t_58_21$ ^t_59_21$ ^t_5_21$ ^t_60_21$ ^t_61_21$ ^t_62_21$ ^t_63_21$ ^t_6_21$ ^t_7_21$ ^t_8_21$ ^t_9_21$} -voltage_domains CORE -name pg_m8_47 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_47 -layer M8 -width .48 -pitch 9.091 -offset 4.448
add_pdn_connect -grid pg_m8_47 -layers {M7 M8}
add_pdn_connect -grid pg_m8_47 -layers {M8 M9}
define_pdn_grid -macro -instances {^hub_el$} -voltage_domains CORE -name pg_m8_48 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_48 -layer M8 -width .48 -pitch 9.091 -offset 4.576
add_pdn_connect -grid pg_m8_48 -layers {M7 M8}
add_pdn_connect -grid pg_m8_48 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_13$ ^s_10_13$ ^s_11_13$ ^s_12_13$ ^s_13_13$ ^s_14_13$ ^s_15_13$ ^s_16_13$ ^s_17_13$ ^s_18_13$ ^s_19_13$ ^s_1_13$ ^s_20_13$ ^s_21_13$ ^s_22_13$ ^s_23_13$ ^s_24_13$ ^s_25_13$ ^s_26_13$ ^s_27_13$ ^s_28_13$ ^s_29_13$ ^s_2_13$ ^s_30_13$ ^s_31_13$ ^s_32_13$ ^s_33_13$ ^s_34_13$ ^s_35_13$ ^s_36_13$ ^s_37_13$ ^s_38_13$ ^s_39_13$ ^s_3_13$ ^s_40_13$ ^s_41_13$ ^s_42_13$ ^s_43_13$ ^s_44_13$ ^s_45_13$ ^s_46_13$ ^s_47_13$ ^s_48_13$ ^s_49_13$ ^s_4_13$ ^s_50_13$ ^s_51_13$ ^s_52_13$ ^s_53_13$ ^s_54_13$ ^s_55_13$ ^s_56_13$ ^s_57_13$ ^s_58_13$ ^s_59_13$ ^s_5_13$ ^s_60_13$ ^s_61_13$ ^s_62_13$ ^s_63_13$ ^s_6_13$ ^s_7_13$ ^s_8_13$ ^s_9_13$} -voltage_domains CORE -name pg_m8_49 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_49 -layer M8 -width .48 -pitch 9.091 -offset 4.626
add_pdn_connect -grid pg_m8_49 -layers {M7 M8}
add_pdn_connect -grid pg_m8_49 -layers {M8 M9}
define_pdn_grid -macro -instances {^lc_N$ ^lh_NE_1$ ^lh_NE_2$ ^lh_NE_3$ ^lh_NE_4$ ^lh_NE_5$ ^lh_NW_1$ ^lh_NW_2$ ^lh_NW_3$ ^lh_NW_4$ ^lh_NW_5$} -voltage_domains CORE -name pg_m8_50 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_50 -layer M8 -width .48 -pitch 9.091 -offset 4.679
add_pdn_connect -grid pg_m8_50 -layers {M7 M8}
add_pdn_connect -grid pg_m8_50 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_1$ ^t_10_1$ ^t_11_1$ ^t_12_1$ ^t_13_1$ ^t_14_1$ ^t_15_1$ ^t_16_1$ ^t_17_1$ ^t_18_1$ ^t_19_1$ ^t_1_1$ ^t_20_1$ ^t_21_1$ ^t_22_1$ ^t_23_1$ ^t_24_1$ ^t_25_1$ ^t_26_1$ ^t_27_1$ ^t_28_1$ ^t_29_1$ ^t_2_1$ ^t_30_1$ ^t_31_1$ ^t_32_1$ ^t_33_1$ ^t_34_1$ ^t_35_1$ ^t_36_1$ ^t_37_1$ ^t_38_1$ ^t_39_1$ ^t_3_1$ ^t_40_1$ ^t_41_1$ ^t_42_1$ ^t_43_1$ ^t_44_1$ ^t_45_1$ ^t_46_1$ ^t_47_1$ ^t_48_1$ ^t_49_1$ ^t_4_1$ ^t_50_1$ ^t_51_1$ ^t_52_1$ ^t_53_1$ ^t_54_1$ ^t_55_1$ ^t_56_1$ ^t_57_1$ ^t_58_1$ ^t_59_1$ ^t_5_1$ ^t_60_1$ ^t_61_1$ ^t_62_1$ ^t_63_1$ ^t_6_1$ ^t_7_1$ ^t_8_1$ ^t_9_1$} -voltage_domains CORE -name pg_m8_51 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_51 -layer M8 -width .48 -pitch 9.091 -offset 4.915
add_pdn_connect -grid pg_m8_51 -layers {M7 M8}
add_pdn_connect -grid pg_m8_51 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_20$ ^t_10_20$ ^t_11_20$ ^t_12_20$ ^t_13_20$ ^t_14_20$ ^t_15_20$ ^t_16_20$ ^t_17_20$ ^t_18_20$ ^t_19_20$ ^t_1_20$ ^t_20_20$ ^t_21_20$ ^t_22_20$ ^t_23_20$ ^t_24_20$ ^t_25_20$ ^t_26_20$ ^t_27_20$ ^t_28_20$ ^t_29_20$ ^t_2_20$ ^t_30_20$ ^t_31_20$ ^t_32_20$ ^t_33_20$ ^t_34_20$ ^t_35_20$ ^t_36_20$ ^t_37_20$ ^t_38_20$ ^t_39_20$ ^t_3_20$ ^t_40_20$ ^t_41_20$ ^t_42_20$ ^t_43_20$ ^t_44_20$ ^t_45_20$ ^t_46_20$ ^t_47_20$ ^t_48_20$ ^t_49_20$ ^t_4_20$ ^t_50_20$ ^t_51_20$ ^t_52_20$ ^t_53_20$ ^t_54_20$ ^t_55_20$ ^t_56_20$ ^t_57_20$ ^t_58_20$ ^t_59_20$ ^t_5_20$ ^t_60_20$ ^t_61_20$ ^t_62_20$ ^t_63_20$ ^t_6_20$ ^t_7_20$ ^t_8_20$ ^t_9_20$} -voltage_domains CORE -name pg_m8_52 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_52 -layer M8 -width .48 -pitch 9.091 -offset 5.206
add_pdn_connect -grid pg_m8_52 -layers {M7 M8}
add_pdn_connect -grid pg_m8_52 -layers {M8 M9}
define_pdn_grid -macro -instances {^sp_su64_sfu$} -voltage_domains CORE -name pg_m8_53 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_53 -layer M8 -width .48 -pitch 9.091 -offset 5.237
add_pdn_connect -grid pg_m8_53 -layers {M7 M8}
add_pdn_connect -grid pg_m8_53 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_12$ ^s_10_12$ ^s_11_12$ ^s_12_12$ ^s_13_12$ ^s_14_12$ ^s_15_12$ ^s_16_12$ ^s_17_12$ ^s_18_12$ ^s_19_12$ ^s_1_12$ ^s_20_12$ ^s_21_12$ ^s_22_12$ ^s_23_12$ ^s_24_12$ ^s_25_12$ ^s_26_12$ ^s_27_12$ ^s_28_12$ ^s_29_12$ ^s_2_12$ ^s_30_12$ ^s_31_12$ ^s_32_12$ ^s_33_12$ ^s_34_12$ ^s_35_12$ ^s_36_12$ ^s_37_12$ ^s_38_12$ ^s_39_12$ ^s_3_12$ ^s_40_12$ ^s_41_12$ ^s_42_12$ ^s_43_12$ ^s_44_12$ ^s_45_12$ ^s_46_12$ ^s_47_12$ ^s_48_12$ ^s_49_12$ ^s_4_12$ ^s_50_12$ ^s_51_12$ ^s_52_12$ ^s_53_12$ ^s_54_12$ ^s_55_12$ ^s_56_12$ ^s_57_12$ ^s_58_12$ ^s_59_12$ ^s_5_12$ ^s_60_12$ ^s_61_12$ ^s_62_12$ ^s_63_12$ ^s_6_12$ ^s_7_12$ ^s_8_12$ ^s_9_12$} -voltage_domains CORE -name pg_m8_54 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_54 -layer M8 -width .48 -pitch 9.091 -offset 5.384
add_pdn_connect -grid pg_m8_54 -layers {M7 M8}
add_pdn_connect -grid pg_m8_54 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_16$ ^t_10_16$ ^t_11_16$ ^t_12_16$ ^t_13_16$ ^t_14_16$ ^t_15_16$ ^t_16_16$ ^t_17_16$ ^t_18_16$ ^t_19_16$ ^t_1_16$ ^t_20_16$ ^t_21_16$ ^t_22_16$ ^t_23_16$ ^t_24_16$ ^t_25_16$ ^t_26_16$ ^t_27_16$ ^t_28_16$ ^t_29_16$ ^t_2_16$ ^t_30_16$ ^t_31_16$ ^t_32_16$ ^t_33_16$ ^t_34_16$ ^t_35_16$ ^t_36_16$ ^t_37_16$ ^t_38_16$ ^t_39_16$ ^t_3_16$ ^t_40_16$ ^t_41_16$ ^t_42_16$ ^t_43_16$ ^t_44_16$ ^t_45_16$ ^t_46_16$ ^t_47_16$ ^t_48_16$ ^t_49_16$ ^t_4_16$ ^t_50_16$ ^t_51_16$ ^t_52_16$ ^t_53_16$ ^t_54_16$ ^t_55_16$ ^t_56_16$ ^t_57_16$ ^t_58_16$ ^t_59_16$ ^t_5_16$ ^t_60_16$ ^t_61_16$ ^t_62_16$ ^t_63_16$ ^t_6_16$ ^t_7_16$ ^t_8_16$ ^t_9_16$} -voltage_domains CORE -name pg_m8_55 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_55 -layer M8 -width .48 -pitch 9.091 -offset 5.437
add_pdn_connect -grid pg_m8_55 -layers {M7 M8}
add_pdn_connect -grid pg_m8_55 -layers {M8 M9}
define_pdn_grid -macro -instances {^lfifo_EN$ ^lfifo_WN$} -voltage_domains CORE -name pg_m8_56 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_56 -layer M8 -width .48 -pitch 9.091 -offset 5.486
add_pdn_connect -grid pg_m8_56 -layers {M7 M8}
add_pdn_connect -grid pg_m8_56 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_0$ ^t_10_0$ ^t_11_0$ ^t_12_0$ ^t_13_0$ ^t_14_0$ ^t_15_0$ ^t_16_0$ ^t_17_0$ ^t_18_0$ ^t_19_0$ ^t_1_0$ ^t_20_0$ ^t_21_0$ ^t_22_0$ ^t_23_0$ ^t_24_0$ ^t_25_0$ ^t_26_0$ ^t_27_0$ ^t_28_0$ ^t_29_0$ ^t_2_0$ ^t_30_0$ ^t_31_0$ ^t_32_0$ ^t_33_0$ ^t_34_0$ ^t_35_0$ ^t_36_0$ ^t_37_0$ ^t_38_0$ ^t_39_0$ ^t_3_0$ ^t_40_0$ ^t_41_0$ ^t_42_0$ ^t_43_0$ ^t_44_0$ ^t_45_0$ ^t_46_0$ ^t_47_0$ ^t_48_0$ ^t_49_0$ ^t_4_0$ ^t_50_0$ ^t_51_0$ ^t_52_0$ ^t_53_0$ ^t_54_0$ ^t_55_0$ ^t_56_0$ ^t_57_0$ ^t_58_0$ ^t_59_0$ ^t_5_0$ ^t_60_0$ ^t_61_0$ ^t_62_0$ ^t_63_0$ ^t_6_0$ ^t_7_0$ ^t_8_0$ ^t_9_0$} -voltage_domains CORE -name pg_m8_57 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_57 -layer M8 -width .48 -pitch 9.091 -offset 5.673
add_pdn_connect -grid pg_m8_57 -layers {M7 M8}
add_pdn_connect -grid pg_m8_57 -layers {M8 M9}
define_pdn_grid -macro -instances {^h_0$ ^h_1$ ^h_10$ ^h_11$ ^h_12$ ^h_13$ ^h_14$ ^h_15$ ^h_16$ ^h_17$ ^h_18$ ^h_19$ ^h_2$ ^h_20$ ^h_21$ ^h_22$ ^h_23$ ^h_24$ ^h_25$ ^h_26$ ^h_27$ ^h_28$ ^h_29$ ^h_3$ ^h_30$ ^h_31$ ^h_32$ ^h_33$ ^h_34$ ^h_35$ ^h_36$ ^h_37$ ^h_38$ ^h_39$ ^h_4$ ^h_40$ ^h_41$ ^h_42$ ^h_43$ ^h_44$ ^h_45$ ^h_46$ ^h_47$ ^h_48$ ^h_49$ ^h_5$ ^h_50$ ^h_51$ ^h_52$ ^h_53$ ^h_54$ ^h_55$ ^h_56$ ^h_57$ ^h_58$ ^h_59$ ^h_6$ ^h_60$ ^h_61$ ^h_62$ ^h_63$ ^h_7$ ^h_8$ ^h_9$} -voltage_domains CORE -name pg_m8_58 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_58 -layer M8 -width .48 -pitch 9.091 -offset 5.763
add_pdn_connect -grid pg_m8_58 -layers {M7 M8}
add_pdn_connect -grid pg_m8_58 -layers {M8 M9}
define_pdn_grid -macro -instances {^sp_port_tiles_3_f1$} -voltage_domains CORE -name pg_m8_59 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_59 -layer M8 -width .48 -pitch 9.091 -offset 5.812
add_pdn_connect -grid pg_m8_59 -layers {M7 M8}
add_pdn_connect -grid pg_m8_59 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_19$ ^t_10_19$ ^t_11_19$ ^t_12_19$ ^t_13_19$ ^t_14_19$ ^t_15_19$ ^t_16_19$ ^t_17_19$ ^t_18_19$ ^t_19_19$ ^t_1_19$ ^t_20_19$ ^t_21_19$ ^t_22_19$ ^t_23_19$ ^t_24_19$ ^t_25_19$ ^t_26_19$ ^t_27_19$ ^t_28_19$ ^t_29_19$ ^t_2_19$ ^t_30_19$ ^t_31_19$ ^t_32_19$ ^t_33_19$ ^t_34_19$ ^t_35_19$ ^t_36_19$ ^t_37_19$ ^t_38_19$ ^t_39_19$ ^t_3_19$ ^t_40_19$ ^t_41_19$ ^t_42_19$ ^t_43_19$ ^t_44_19$ ^t_45_19$ ^t_46_19$ ^t_47_19$ ^t_48_19$ ^t_49_19$ ^t_4_19$ ^t_50_19$ ^t_51_19$ ^t_52_19$ ^t_53_19$ ^t_54_19$ ^t_55_19$ ^t_56_19$ ^t_57_19$ ^t_58_19$ ^t_59_19$ ^t_5_19$ ^t_60_19$ ^t_61_19$ ^t_62_19$ ^t_63_19$ ^t_6_19$ ^t_7_19$ ^t_8_19$ ^t_9_19$} -voltage_domains CORE -name pg_m8_60 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_60 -layer M8 -width .48 -pitch 9.091 -offset 5.964
add_pdn_connect -grid pg_m8_60 -layers {M7 M8}
add_pdn_connect -grid pg_m8_60 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_11$ ^s_10_11$ ^s_11_11$ ^s_12_11$ ^s_13_11$ ^s_14_11$ ^s_15_11$ ^s_16_11$ ^s_17_11$ ^s_18_11$ ^s_19_11$ ^s_1_11$ ^s_20_11$ ^s_21_11$ ^s_22_11$ ^s_23_11$ ^s_24_11$ ^s_25_11$ ^s_26_11$ ^s_27_11$ ^s_28_11$ ^s_29_11$ ^s_2_11$ ^s_30_11$ ^s_31_11$ ^s_32_11$ ^s_33_11$ ^s_34_11$ ^s_35_11$ ^s_36_11$ ^s_37_11$ ^s_38_11$ ^s_39_11$ ^s_3_11$ ^s_40_11$ ^s_41_11$ ^s_42_11$ ^s_43_11$ ^s_44_11$ ^s_45_11$ ^s_46_11$ ^s_47_11$ ^s_48_11$ ^s_49_11$ ^s_4_11$ ^s_50_11$ ^s_51_11$ ^s_52_11$ ^s_53_11$ ^s_54_11$ ^s_55_11$ ^s_56_11$ ^s_57_11$ ^s_58_11$ ^s_59_11$ ^s_5_11$ ^s_60_11$ ^s_61_11$ ^s_62_11$ ^s_63_11$ ^s_6_11$ ^s_7_11$ ^s_8_11$ ^s_9_11$} -voltage_domains CORE -name pg_m8_61 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_61 -layer M8 -width .48 -pitch 9.091 -offset 6.142
add_pdn_connect -grid pg_m8_61 -layers {M7 M8}
add_pdn_connect -grid pg_m8_61 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_15$ ^t_10_15$ ^t_11_15$ ^t_12_15$ ^t_13_15$ ^t_14_15$ ^t_15_15$ ^t_16_15$ ^t_17_15$ ^t_18_15$ ^t_19_15$ ^t_1_15$ ^t_20_15$ ^t_21_15$ ^t_22_15$ ^t_23_15$ ^t_24_15$ ^t_25_15$ ^t_26_15$ ^t_27_15$ ^t_28_15$ ^t_29_15$ ^t_2_15$ ^t_30_15$ ^t_31_15$ ^t_32_15$ ^t_33_15$ ^t_34_15$ ^t_35_15$ ^t_36_15$ ^t_37_15$ ^t_38_15$ ^t_39_15$ ^t_3_15$ ^t_40_15$ ^t_41_15$ ^t_42_15$ ^t_43_15$ ^t_44_15$ ^t_45_15$ ^t_46_15$ ^t_47_15$ ^t_48_15$ ^t_49_15$ ^t_4_15$ ^t_50_15$ ^t_51_15$ ^t_52_15$ ^t_53_15$ ^t_54_15$ ^t_55_15$ ^t_56_15$ ^t_57_15$ ^t_58_15$ ^t_59_15$ ^t_5_15$ ^t_60_15$ ^t_61_15$ ^t_62_15$ ^t_63_15$ ^t_6_15$ ^t_7_15$ ^t_8_15$ ^t_9_15$} -voltage_domains CORE -name pg_m8_62 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_62 -layer M8 -width .48 -pitch 9.091 -offset 6.195
add_pdn_connect -grid pg_m8_62 -layers {M7 M8}
add_pdn_connect -grid pg_m8_62 -layers {M8 M9}
define_pdn_grid -macro -instances {^re_ES_1$ ^re_WS_1$} -voltage_domains CORE -name pg_m8_63 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_63 -layer M8 -width .48 -pitch 9.091 -offset 6.225
add_pdn_connect -grid pg_m8_63 -layers {M7 M8}
add_pdn_connect -grid pg_m8_63 -layers {M8 M9}
define_pdn_grid -macro -instances {^re_ES_5$ ^re_WS_5$} -voltage_domains CORE -name pg_m8_64 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_64 -layer M8 -width .48 -pitch 9.091 -offset 6.401
add_pdn_connect -grid pg_m8_64 -layers {M7 M8}
add_pdn_connect -grid pg_m8_64 -layers {M8 M9}
define_pdn_grid -macro -instances {^re_EN_3$ ^re_WN_3$} -voltage_domains CORE -name pg_m8_65 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_65 -layer M8 -width .48 -pitch 9.091 -offset 6.673
add_pdn_connect -grid pg_m8_65 -layers {M7 M8}
add_pdn_connect -grid pg_m8_65 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_18$ ^t_10_18$ ^t_11_18$ ^t_12_18$ ^t_13_18$ ^t_14_18$ ^t_15_18$ ^t_16_18$ ^t_17_18$ ^t_18_18$ ^t_19_18$ ^t_1_18$ ^t_20_18$ ^t_21_18$ ^t_22_18$ ^t_23_18$ ^t_24_18$ ^t_25_18$ ^t_26_18$ ^t_27_18$ ^t_28_18$ ^t_29_18$ ^t_2_18$ ^t_30_18$ ^t_31_18$ ^t_32_18$ ^t_33_18$ ^t_34_18$ ^t_35_18$ ^t_36_18$ ^t_37_18$ ^t_38_18$ ^t_39_18$ ^t_3_18$ ^t_40_18$ ^t_41_18$ ^t_42_18$ ^t_43_18$ ^t_44_18$ ^t_45_18$ ^t_46_18$ ^t_47_18$ ^t_48_18$ ^t_49_18$ ^t_4_18$ ^t_50_18$ ^t_51_18$ ^t_52_18$ ^t_53_18$ ^t_54_18$ ^t_55_18$ ^t_56_18$ ^t_57_18$ ^t_58_18$ ^t_59_18$ ^t_5_18$ ^t_60_18$ ^t_61_18$ ^t_62_18$ ^t_63_18$ ^t_6_18$ ^t_7_18$ ^t_8_18$ ^t_9_18$} -voltage_domains CORE -name pg_m8_66 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_66 -layer M8 -width .48 -pitch 9.091 -offset 6.722
add_pdn_connect -grid pg_m8_66 -layers {M7 M8}
add_pdn_connect -grid pg_m8_66 -layers {M8 M9}
define_pdn_grid -macro -instances {^lv_N_1$} -voltage_domains CORE -name pg_m8_67 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_67 -layer M8 -width .48 -pitch 9.091 -offset 6.881
add_pdn_connect -grid pg_m8_67 -layers {M7 M8}
add_pdn_connect -grid pg_m8_67 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_10$ ^s_10_10$ ^s_11_10$ ^s_12_10$ ^s_13_10$ ^s_14_10$ ^s_15_10$ ^s_16_10$ ^s_17_10$ ^s_18_10$ ^s_19_10$ ^s_1_10$ ^s_20_10$ ^s_21_10$ ^s_22_10$ ^s_23_10$ ^s_24_10$ ^s_25_10$ ^s_26_10$ ^s_27_10$ ^s_28_10$ ^s_29_10$ ^s_2_10$ ^s_30_10$ ^s_31_10$ ^s_32_10$ ^s_33_10$ ^s_34_10$ ^s_35_10$ ^s_36_10$ ^s_37_10$ ^s_38_10$ ^s_39_10$ ^s_3_10$ ^s_40_10$ ^s_41_10$ ^s_42_10$ ^s_43_10$ ^s_44_10$ ^s_45_10$ ^s_46_10$ ^s_47_10$ ^s_48_10$ ^s_49_10$ ^s_4_10$ ^s_50_10$ ^s_51_10$ ^s_52_10$ ^s_53_10$ ^s_54_10$ ^s_55_10$ ^s_56_10$ ^s_57_10$ ^s_58_10$ ^s_59_10$ ^s_5_10$ ^s_60_10$ ^s_61_10$ ^s_62_10$ ^s_63_10$ ^s_6_10$ ^s_7_10$ ^s_8_10$ ^s_9_10$} -voltage_domains CORE -name pg_m8_68 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_68 -layer M8 -width .48 -pitch 9.091 -offset 6.900
add_pdn_connect -grid pg_m8_68 -layers {M7 M8}
add_pdn_connect -grid pg_m8_68 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_14$ ^t_10_14$ ^t_11_14$ ^t_12_14$ ^t_13_14$ ^t_14_14$ ^t_15_14$ ^t_16_14$ ^t_17_14$ ^t_18_14$ ^t_19_14$ ^t_1_14$ ^t_20_14$ ^t_21_14$ ^t_22_14$ ^t_23_14$ ^t_24_14$ ^t_25_14$ ^t_26_14$ ^t_27_14$ ^t_28_14$ ^t_29_14$ ^t_2_14$ ^t_30_14$ ^t_31_14$ ^t_32_14$ ^t_33_14$ ^t_34_14$ ^t_35_14$ ^t_36_14$ ^t_37_14$ ^t_38_14$ ^t_39_14$ ^t_3_14$ ^t_40_14$ ^t_41_14$ ^t_42_14$ ^t_43_14$ ^t_44_14$ ^t_45_14$ ^t_46_14$ ^t_47_14$ ^t_48_14$ ^t_49_14$ ^t_4_14$ ^t_50_14$ ^t_51_14$ ^t_52_14$ ^t_53_14$ ^t_54_14$ ^t_55_14$ ^t_56_14$ ^t_57_14$ ^t_58_14$ ^t_59_14$ ^t_5_14$ ^t_60_14$ ^t_61_14$ ^t_62_14$ ^t_63_14$ ^t_6_14$ ^t_7_14$ ^t_8_14$ ^t_9_14$} -voltage_domains CORE -name pg_m8_69 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_69 -layer M8 -width .48 -pitch 9.091 -offset 6.953
add_pdn_connect -grid pg_m8_69 -layers {M7 M8}
add_pdn_connect -grid pg_m8_69 -layers {M8 M9}
define_pdn_grid -macro -instances {^sp_port_tiles_2_f1$} -voltage_domains CORE -name pg_m8_70 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_70 -layer M8 -width .48 -pitch 9.091 -offset 6.966
add_pdn_connect -grid pg_m8_70 -layers {M7 M8}
add_pdn_connect -grid pg_m8_70 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_6$ ^s_10_6$ ^s_11_6$ ^s_12_6$ ^s_13_6$ ^s_14_6$ ^s_15_6$ ^s_16_6$ ^s_17_6$ ^s_18_6$ ^s_19_6$ ^s_1_6$ ^s_20_6$ ^s_21_6$ ^s_22_6$ ^s_23_6$ ^s_24_6$ ^s_25_6$ ^s_26_6$ ^s_27_6$ ^s_28_6$ ^s_29_6$ ^s_2_6$ ^s_30_6$ ^s_31_6$ ^s_32_6$ ^s_33_6$ ^s_34_6$ ^s_35_6$ ^s_36_6$ ^s_37_6$ ^s_38_6$ ^s_39_6$ ^s_3_6$ ^s_40_6$ ^s_41_6$ ^s_42_6$ ^s_43_6$ ^s_44_6$ ^s_45_6$ ^s_46_6$ ^s_47_6$ ^s_48_6$ ^s_49_6$ ^s_4_6$ ^s_50_6$ ^s_51_6$ ^s_52_6$ ^s_53_6$ ^s_54_6$ ^s_55_6$ ^s_56_6$ ^s_57_6$ ^s_58_6$ ^s_59_6$ ^s_5_6$ ^s_60_6$ ^s_61_6$ ^s_62_6$ ^s_63_6$ ^s_6_6$ ^s_7_6$ ^s_8_6$ ^s_9_6$} -voltage_domains CORE -name pg_m8_71 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_71 -layer M8 -width .48 -pitch 9.091 -offset 7.131
add_pdn_connect -grid pg_m8_71 -layers {M7 M8}
add_pdn_connect -grid pg_m8_71 -layers {M8 M9}
define_pdn_grid -macro -instances {^sp_port_tiles_1$ ^sp_port_tiles_1_f1$} -voltage_domains CORE -name pg_m8_72 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_72 -layer M8 -width .48 -pitch 9.091 -offset 7.176
add_pdn_connect -grid pg_m8_72 -layers {M7 M8}
add_pdn_connect -grid pg_m8_72 -layers {M8 M9}
define_pdn_grid -macro -instances {^sp_port_tiles_4$ ^sp_port_tiles_4_f1$ ^t_0_17$ ^t_10_17$ ^t_11_17$ ^t_12_17$ ^t_13_17$ ^t_14_17$ ^t_15_17$ ^t_16_17$ ^t_17_17$ ^t_18_17$ ^t_19_17$ ^t_1_17$ ^t_20_17$ ^t_21_17$ ^t_22_17$ ^t_23_17$ ^t_24_17$ ^t_25_17$ ^t_26_17$ ^t_27_17$ ^t_28_17$ ^t_29_17$ ^t_2_17$ ^t_30_17$ ^t_31_17$ ^t_32_17$ ^t_33_17$ ^t_34_17$ ^t_35_17$ ^t_36_17$ ^t_37_17$ ^t_38_17$ ^t_39_17$ ^t_3_17$ ^t_40_17$ ^t_41_17$ ^t_42_17$ ^t_43_17$ ^t_44_17$ ^t_45_17$ ^t_46_17$ ^t_47_17$ ^t_48_17$ ^t_49_17$ ^t_4_17$ ^t_50_17$ ^t_51_17$ ^t_52_17$ ^t_53_17$ ^t_54_17$ ^t_55_17$ ^t_56_17$ ^t_57_17$ ^t_58_17$ ^t_59_17$ ^t_5_17$ ^t_60_17$ ^t_61_17$ ^t_62_17$ ^t_63_17$ ^t_6_17$ ^t_7_17$ ^t_8_17$ ^t_9_17$} -voltage_domains CORE -name pg_m8_73 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_73 -layer M8 -width .48 -pitch 9.091 -offset 7.480
add_pdn_connect -grid pg_m8_73 -layers {M7 M8}
add_pdn_connect -grid pg_m8_73 -layers {M8 M9}
define_pdn_grid -macro -instances {^sp_port_tiles_3$} -voltage_domains CORE -name pg_m8_74 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_74 -layer M8 -width .48 -pitch 9.091 -offset 7.571
add_pdn_connect -grid pg_m8_74 -layers {M7 M8}
add_pdn_connect -grid pg_m8_74 -layers {M8 M9}
define_pdn_grid -macro -instances {^lv_S_3_E$ ^lv_S_3_W$} -voltage_domains CORE -name pg_m8_75 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_75 -layer M8 -width .48 -pitch 9.091 -offset 7.608
add_pdn_connect -grid pg_m8_75 -layers {M7 M8}
add_pdn_connect -grid pg_m8_75 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_9$ ^s_10_9$ ^s_11_9$ ^s_12_9$ ^s_13_9$ ^s_14_9$ ^s_15_9$ ^s_16_9$ ^s_17_9$ ^s_18_9$ ^s_19_9$ ^s_1_9$ ^s_20_9$ ^s_21_9$ ^s_22_9$ ^s_23_9$ ^s_24_9$ ^s_25_9$ ^s_26_9$ ^s_27_9$ ^s_28_9$ ^s_29_9$ ^s_2_9$ ^s_30_9$ ^s_31_9$ ^s_32_9$ ^s_33_9$ ^s_34_9$ ^s_35_9$ ^s_36_9$ ^s_37_9$ ^s_38_9$ ^s_39_9$ ^s_3_9$ ^s_40_9$ ^s_41_9$ ^s_42_9$ ^s_43_9$ ^s_44_9$ ^s_45_9$ ^s_46_9$ ^s_47_9$ ^s_48_9$ ^s_49_9$ ^s_4_9$ ^s_50_9$ ^s_51_9$ ^s_52_9$ ^s_53_9$ ^s_54_9$ ^s_55_9$ ^s_56_9$ ^s_57_9$ ^s_58_9$ ^s_59_9$ ^s_5_9$ ^s_60_9$ ^s_61_9$ ^s_62_9$ ^s_63_9$ ^s_6_9$ ^s_7_9$ ^s_8_9$ ^s_9_9$} -voltage_domains CORE -name pg_m8_76 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_76 -layer M8 -width .48 -pitch 9.091 -offset 7.658
add_pdn_connect -grid pg_m8_76 -layers {M7 M8}
add_pdn_connect -grid pg_m8_76 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_13$ ^t_10_13$ ^t_11_13$ ^t_12_13$ ^t_13_13$ ^t_14_13$ ^t_15_13$ ^t_16_13$ ^t_17_13$ ^t_18_13$ ^t_19_13$ ^t_1_13$ ^t_20_13$ ^t_21_13$ ^t_22_13$ ^t_23_13$ ^t_24_13$ ^t_25_13$ ^t_26_13$ ^t_27_13$ ^t_28_13$ ^t_29_13$ ^t_2_13$ ^t_30_13$ ^t_31_13$ ^t_32_13$ ^t_33_13$ ^t_34_13$ ^t_35_13$ ^t_36_13$ ^t_37_13$ ^t_38_13$ ^t_39_13$ ^t_3_13$ ^t_40_13$ ^t_41_13$ ^t_42_13$ ^t_43_13$ ^t_44_13$ ^t_45_13$ ^t_46_13$ ^t_47_13$ ^t_48_13$ ^t_49_13$ ^t_4_13$ ^t_50_13$ ^t_51_13$ ^t_52_13$ ^t_53_13$ ^t_54_13$ ^t_55_13$ ^t_56_13$ ^t_57_13$ ^t_58_13$ ^t_59_13$ ^t_5_13$ ^t_60_13$ ^t_61_13$ ^t_62_13$ ^t_63_13$ ^t_6_13$ ^t_7_13$ ^t_8_13$ ^t_9_13$} -voltage_domains CORE -name pg_m8_77 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_77 -layer M8 -width .48 -pitch 9.091 -offset 7.711
add_pdn_connect -grid pg_m8_77 -layers {M7 M8}
add_pdn_connect -grid pg_m8_77 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_5$ ^s_10_5$ ^s_11_5$ ^s_12_5$ ^s_13_5$ ^s_14_5$ ^s_15_5$ ^s_16_5$ ^s_17_5$ ^s_18_5$ ^s_19_5$ ^s_1_5$ ^s_20_5$ ^s_21_5$ ^s_22_5$ ^s_23_5$ ^s_24_5$ ^s_25_5$ ^s_26_5$ ^s_27_5$ ^s_28_5$ ^s_29_5$ ^s_2_5$ ^s_30_5$ ^s_31_5$ ^s_32_5$ ^s_33_5$ ^s_34_5$ ^s_35_5$ ^s_36_5$ ^s_37_5$ ^s_38_5$ ^s_39_5$ ^s_3_5$ ^s_40_5$ ^s_41_5$ ^s_42_5$ ^s_43_5$ ^s_44_5$ ^s_45_5$ ^s_46_5$ ^s_47_5$ ^s_48_5$ ^s_49_5$ ^s_4_5$ ^s_50_5$ ^s_51_5$ ^s_52_5$ ^s_53_5$ ^s_54_5$ ^s_55_5$ ^s_56_5$ ^s_57_5$ ^s_58_5$ ^s_59_5$ ^s_5_5$ ^s_60_5$ ^s_61_5$ ^s_62_5$ ^s_63_5$ ^s_6_5$ ^s_7_5$ ^s_8_5$ ^s_9_5$} -voltage_domains CORE -name pg_m8_78 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_78 -layer M8 -width .48 -pitch 9.091 -offset 7.889
add_pdn_connect -grid pg_m8_78 -layers {M7 M8}
add_pdn_connect -grid pg_m8_78 -layers {M8 M9}
define_pdn_grid -macro -instances {^re_ES_2$ ^re_WS_2$} -voltage_domains CORE -name pg_m8_79 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_79 -layer M8 -width .48 -pitch 9.091 -offset 8.245
add_pdn_connect -grid pg_m8_79 -layers {M7 M8}
add_pdn_connect -grid pg_m8_79 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_8$ ^s_10_8$ ^s_11_8$ ^s_12_8$ ^s_13_8$ ^s_14_8$ ^s_15_8$ ^s_16_8$ ^s_17_8$ ^s_18_8$ ^s_19_8$ ^s_1_8$ ^s_20_8$ ^s_21_8$ ^s_22_8$ ^s_23_8$ ^s_24_8$ ^s_25_8$ ^s_26_8$ ^s_27_8$ ^s_28_8$ ^s_29_8$ ^s_2_8$ ^s_30_8$ ^s_31_8$ ^s_32_8$ ^s_33_8$ ^s_34_8$ ^s_35_8$ ^s_36_8$ ^s_37_8$ ^s_38_8$ ^s_39_8$ ^s_3_8$ ^s_40_8$ ^s_41_8$ ^s_42_8$ ^s_43_8$ ^s_44_8$ ^s_45_8$ ^s_46_8$ ^s_47_8$ ^s_48_8$ ^s_49_8$ ^s_4_8$ ^s_50_8$ ^s_51_8$ ^s_52_8$ ^s_53_8$ ^s_54_8$ ^s_55_8$ ^s_56_8$ ^s_57_8$ ^s_58_8$ ^s_59_8$ ^s_5_8$ ^s_60_8$ ^s_61_8$ ^s_62_8$ ^s_63_8$ ^s_6_8$ ^s_7_8$ ^s_8_8$ ^s_9_8$} -voltage_domains CORE -name pg_m8_80 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_80 -layer M8 -width .48 -pitch 9.091 -offset 8.416
add_pdn_connect -grid pg_m8_80 -layers {M7 M8}
add_pdn_connect -grid pg_m8_80 -layers {M8 M9}
define_pdn_grid -macro -instances {^t_0_12$ ^t_10_12$ ^t_11_12$ ^t_12_12$ ^t_13_12$ ^t_14_12$ ^t_15_12$ ^t_16_12$ ^t_17_12$ ^t_18_12$ ^t_19_12$ ^t_1_12$ ^t_20_12$ ^t_21_12$ ^t_22_12$ ^t_23_12$ ^t_24_12$ ^t_25_12$ ^t_26_12$ ^t_27_12$ ^t_28_12$ ^t_29_12$ ^t_2_12$ ^t_30_12$ ^t_31_12$ ^t_32_12$ ^t_33_12$ ^t_34_12$ ^t_35_12$ ^t_36_12$ ^t_37_12$ ^t_38_12$ ^t_39_12$ ^t_3_12$ ^t_40_12$ ^t_41_12$ ^t_42_12$ ^t_43_12$ ^t_44_12$ ^t_45_12$ ^t_46_12$ ^t_47_12$ ^t_48_12$ ^t_49_12$ ^t_4_12$ ^t_50_12$ ^t_51_12$ ^t_52_12$ ^t_53_12$ ^t_54_12$ ^t_55_12$ ^t_56_12$ ^t_57_12$ ^t_58_12$ ^t_59_12$ ^t_5_12$ ^t_60_12$ ^t_61_12$ ^t_62_12$ ^t_63_12$ ^t_6_12$ ^t_7_12$ ^t_8_12$ ^t_9_12$} -voltage_domains CORE -name pg_m8_81 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_81 -layer M8 -width .48 -pitch 9.091 -offset 8.469
add_pdn_connect -grid pg_m8_81 -layers {M7 M8}
add_pdn_connect -grid pg_m8_81 -layers {M8 M9}
define_pdn_grid -macro -instances {^ctrl_EN$ ^ctrl_WN$ ^re_EN_0$ ^re_WN_0$} -voltage_domains CORE -name pg_m8_82 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_82 -layer M8 -width .48 -pitch 9.091 -offset 8.517
add_pdn_connect -grid pg_m8_82 -layers {M7 M8}
add_pdn_connect -grid pg_m8_82 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_4$ ^s_10_4$ ^s_11_4$ ^s_12_4$ ^s_13_4$ ^s_14_4$ ^s_15_4$ ^s_16_4$ ^s_17_4$ ^s_18_4$ ^s_19_4$ ^s_1_4$ ^s_20_4$ ^s_21_4$ ^s_22_4$ ^s_23_4$ ^s_24_4$ ^s_25_4$ ^s_26_4$ ^s_27_4$ ^s_28_4$ ^s_29_4$ ^s_2_4$ ^s_30_4$ ^s_31_4$ ^s_32_4$ ^s_33_4$ ^s_34_4$ ^s_35_4$ ^s_36_4$ ^s_37_4$ ^s_38_4$ ^s_39_4$ ^s_3_4$ ^s_40_4$ ^s_41_4$ ^s_42_4$ ^s_43_4$ ^s_44_4$ ^s_45_4$ ^s_46_4$ ^s_47_4$ ^s_48_4$ ^s_49_4$ ^s_4_4$ ^s_50_4$ ^s_51_4$ ^s_52_4$ ^s_53_4$ ^s_54_4$ ^s_55_4$ ^s_56_4$ ^s_57_4$ ^s_58_4$ ^s_59_4$ ^s_5_4$ ^s_60_4$ ^s_61_4$ ^s_62_4$ ^s_63_4$ ^s_6_4$ ^s_7_4$ ^s_8_4$ ^s_9_4$} -voltage_domains CORE -name pg_m8_83 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_83 -layer M8 -width .48 -pitch 9.091 -offset 8.647
add_pdn_connect -grid pg_m8_83 -layers {M7 M8}
add_pdn_connect -grid pg_m8_83 -layers {M8 M9}
define_pdn_grid -macro -instances {^re_EN_4$ ^re_WN_4$} -voltage_domains CORE -name pg_m8_84 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_84 -layer M8 -width .48 -pitch 9.091 -offset 8.693
add_pdn_connect -grid pg_m8_84 -layers {M7 M8}
add_pdn_connect -grid pg_m8_84 -layers {M8 M9}
define_pdn_grid -macro -instances {^s_0_23$ ^s_10_23$ ^s_11_23$ ^s_12_23$ ^s_13_23$ ^s_14_23$ ^s_15_23$ ^s_16_23$ ^s_17_23$ ^s_18_23$ ^s_19_23$ ^s_1_23$ ^s_20_23$ ^s_21_23$ ^s_22_23$ ^s_23_23$ ^s_24_23$ ^s_25_23$ ^s_26_23$ ^s_27_23$ ^s_28_23$ ^s_29_23$ ^s_2_23$ ^s_30_23$ ^s_31_23$ ^s_32_23$ ^s_33_23$ ^s_34_23$ ^s_35_23$ ^s_36_23$ ^s_37_23$ ^s_38_23$ ^s_39_23$ ^s_3_23$ ^s_40_23$ ^s_41_23$ ^s_42_23$ ^s_43_23$ ^s_44_23$ ^s_45_23$ ^s_46_23$ ^s_47_23$ ^s_48_23$ ^s_49_23$ ^s_4_23$ ^s_50_23$ ^s_51_23$ ^s_52_23$ ^s_53_23$ ^s_54_23$ ^s_55_23$ ^s_56_23$ ^s_57_23$ ^s_58_23$ ^s_59_23$ ^s_5_23$ ^s_60_23$ ^s_61_23$ ^s_62_23$ ^s_63_23$ ^s_6_23$ ^s_7_23$ ^s_8_23$ ^s_9_23$} -voltage_domains CORE -name pg_m8_85 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_m8_85 -layer M8 -width .48 -pitch 9.091 -offset 8.938
add_pdn_connect -grid pg_m8_85 -layers {M7 M8}
add_pdn_connect -grid pg_m8_85 -layers {M8 M9}
