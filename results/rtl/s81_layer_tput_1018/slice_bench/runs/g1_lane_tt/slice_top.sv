`timescale 1ns/1ps
// slice_top: cut by tools/s81_dv/dv_slice_cut.py from die.v (dv_die); 249 instances, 83 ports -- instance lines verbatim from the die netlist
module slice_top (
  i__ck_cl2S,
  i__ck_cl3S,
  i__ck_cl4S,
  i__ck_south2,
  i__ck_south3,
  i__ck_south4,
  i__ck_south5,
  o__land_fault,
  o__rs_25_13_1,
  o__rs_25_3_1,
  o__rs_26_0,
  o__rs_26_12,
  o__rs_26_18,
  o__rs_26_18_1,
  o__rs_26_18_3,
  o__rs_26_6_2,
  o__rs_27_19_3,
  o__rs_28_19_1,
  o__rs_29_10_2,
  o__rs_29_19_2,
  o__rs_29_3,
  o__rs_29_3_2,
  o__rs_29_3_3,
  o__rs_29_4_1,
  o__rs_29_4_2,
  o__rs_29_5_2,
  o__rs_29_6_2,
  o__rs_30_19_2,
  o__rs_31_10_2,
  o__rs_31_19_2,
  o__rs_31_7,
  o__rs_32_18_3,
  o__rs_32_3_2,
  o__rs_32_7,
  o__rs_33_10_3,
  o__rs_33_11_3,
  o__rs_33_12,
  o__rs_33_18,
  o__rs_33_19_2,
  o__rs_33_6_1,
  o__rs_33_7_3,
  o__rs_34_10,
  o__rs_34_13_2,
  o__rs_36_19_3,
  o__rs_37_19_2,
  o__rs_38_19_2,
  o__rs_39_0_2,
  o__rs_39_19_2,
  o__rs_40_19_2,
  o__rs_41_19_2,
  o__rs_42_19_2,
  o__rs_43_11_1,
  o__rs_43_18_3,
  o__rs_43_19_2,
  o__rs_43_4,
  o__rs_43_5,
  o__rs_43_6,
  o__rs_43_7,
  o__rs_44_4_1,
  o__rs_45_13_1,
  o__rs_45_4_1,
  o__rs_46_10_1,
  o__rs_46_12_3,
  o__rs_49_3,
  o__rs_50_0,
  o__rs_50_10_1,
  o__rs_50_3_1,
  o__rs_50_7_2,
  o__rsg_rs_25_13_1_cl2S_0,
  o__rsg_rs_25_13_1_cl2S_2,
  o__rsg_rs_34_13_2_cl3S_0,
  o__rsl_hrq_03_3,
  o__rsl_jw_W_l1_31,
  o__rsl_xrE_2S_l0_2,
  i__rst_n,
  i__u_s_3S_ck_line,
  i__u_s_4S_ck_line,
  o__w_r_f_3L01_lnd,
  i__w_r_f_3L01_src,
  o__w_xrW_2S_l3_lnd,
  i__w_xrW_2S_l3_src,
  o__w_xrW_3S_l0_lnd,
  i__w_xrW_3S_l0_src
);
  input wire i__ck_cl2S;
  input wire i__ck_cl3S;
  input wire i__ck_cl4S;
  input wire i__ck_south2;
  input wire i__ck_south3;
  input wire i__ck_south4;
  input wire i__ck_south5;
  output wire [223:0] o__land_fault;
  output wire o__rs_25_13_1;
  output wire o__rs_25_3_1;
  output wire o__rs_26_0;
  output wire o__rs_26_12;
  output wire o__rs_26_18;
  output wire o__rs_26_18_1;
  output wire o__rs_26_18_3;
  output wire o__rs_26_6_2;
  output wire o__rs_27_19_3;
  output wire o__rs_28_19_1;
  output wire o__rs_29_10_2;
  output wire o__rs_29_19_2;
  output wire o__rs_29_3;
  output wire o__rs_29_3_2;
  output wire o__rs_29_3_3;
  output wire o__rs_29_4_1;
  output wire o__rs_29_4_2;
  output wire o__rs_29_5_2;
  output wire o__rs_29_6_2;
  output wire o__rs_30_19_2;
  output wire o__rs_31_10_2;
  output wire o__rs_31_19_2;
  output wire o__rs_31_7;
  output wire o__rs_32_18_3;
  output wire o__rs_32_3_2;
  output wire o__rs_32_7;
  output wire o__rs_33_10_3;
  output wire o__rs_33_11_3;
  output wire o__rs_33_12;
  output wire o__rs_33_18;
  output wire o__rs_33_19_2;
  output wire o__rs_33_6_1;
  output wire o__rs_33_7_3;
  output wire o__rs_34_10;
  output wire o__rs_34_13_2;
  output wire o__rs_36_19_3;
  output wire o__rs_37_19_2;
  output wire o__rs_38_19_2;
  output wire o__rs_39_0_2;
  output wire o__rs_39_19_2;
  output wire o__rs_40_19_2;
  output wire o__rs_41_19_2;
  output wire o__rs_42_19_2;
  output wire o__rs_43_11_1;
  output wire o__rs_43_18_3;
  output wire o__rs_43_19_2;
  output wire o__rs_43_4;
  output wire o__rs_43_5;
  output wire o__rs_43_6;
  output wire o__rs_43_7;
  output wire o__rs_44_4_1;
  output wire o__rs_45_13_1;
  output wire o__rs_45_4_1;
  output wire o__rs_46_10_1;
  output wire o__rs_46_12_3;
  output wire o__rs_49_3;
  output wire o__rs_50_0;
  output wire o__rs_50_10_1;
  output wire o__rs_50_3_1;
  output wire o__rs_50_7_2;
  output wire o__rsg_rs_25_13_1_cl2S_0;
  output wire o__rsg_rs_25_13_1_cl2S_2;
  output wire o__rsg_rs_34_13_2_cl3S_0;
  output wire o__rsl_hrq_03_3;
  output wire o__rsl_jw_W_l1_31;
  output wire o__rsl_xrE_2S_l0_2;
  input wire i__rst_n;
  input wire [15:0] i__u_s_3S_ck_line;
  input wire [15:0] i__u_s_4S_ck_line;
  output wire [69:0] o__w_r_f_3L01_lnd;
  input wire [69:0] i__w_r_f_3L01_src;
  output wire [275:0] o__w_xrW_2S_l3_lnd;
  input wire [275:0] i__w_xrW_2S_l3_src;
  output wire [275:0] o__w_xrW_3S_l0_lnd;
  input wire [275:0] i__w_xrW_3S_l0_src;
  wire ck_cl2S;
  assign ck_cl2S = i__ck_cl2S;
  wire ck_cl3S;
  assign ck_cl3S = i__ck_cl3S;
  wire ck_cl4S;
  assign ck_cl4S = i__ck_cl4S;
  wire ck_south2;
  assign ck_south2 = i__ck_south2;
  wire ck_south3;
  assign ck_south3 = i__ck_south3;
  wire ck_south4;
  assign ck_south4 = i__ck_south4;
  wire ck_south5;
  assign ck_south5 = i__ck_south5;
  wire [223:0] land_fault;
  assign o__land_fault = land_fault;
  wire [1:0] nr_f_3L01_fck;
  wire [7:0] nxrW_2S_l3_fck;
  wire [7:0] nxrW_3S_l0_fck;
  wire [275:0] r_xrW_2S_l3_0;
  wire [275:0] r_xrW_2S_l3_1;
  wire [275:0] r_xrW_2S_l3_2;
  wire [275:0] r_xrW_2S_l3_3;
  wire [275:0] r_xrW_2S_l3_4;
  wire [275:0] r_xrW_2S_l3_5;
  wire [275:0] r_xrW_3S_l0_0;
  wire [275:0] r_xrW_3S_l0_1;
  wire [275:0] r_xrW_3S_l0_2;
  wire [275:0] r_xrW_3S_l0_3;
  wire [275:0] r_xrW_3S_l0_4;
  wire [275:0] r_xrW_3S_l0_5;
  wire rs_25_10_1;
  wire rs_25_11_1;
  wire rs_25_12_1;
  wire rs_25_13_1;
  assign o__rs_25_13_1 = rs_25_13_1;
  wire rs_25_3_1;
  assign o__rs_25_3_1 = rs_25_3_1;
  wire rs_25_4_1;
  wire rs_25_5_1;
  wire rs_25_6_1;
  wire rs_25_7_1;
  wire rs_25_8_1;
  wire rs_25_9_1;
  wire rs_26_0;
  assign o__rs_26_0 = rs_26_0;
  wire rs_26_1;
  wire rs_26_10;
  wire rs_26_10_2;
  wire rs_26_11;
  wire rs_26_11_1;
  wire rs_26_11_2;
  wire rs_26_12;
  assign o__rs_26_12 = rs_26_12;
  wire rs_26_12_2;
  wire rs_26_13;
  wire rs_26_13_2;
  wire rs_26_14;
  wire rs_26_14_2;
  wire rs_26_15;
  wire rs_26_15_2;
  wire rs_26_16;
  wire rs_26_16_2;
  wire rs_26_17;
  wire rs_26_17_2;
  wire rs_26_18;
  assign o__rs_26_18 = rs_26_18;
  wire rs_26_18_1;
  assign o__rs_26_18_1 = rs_26_18_1;
  wire rs_26_18_3;
  assign o__rs_26_18_3 = rs_26_18_3;
  wire rs_26_19_2;
  wire rs_26_2;
  wire rs_26_3;
  wire rs_26_3_1;
  wire rs_26_3_3;
  wire rs_26_4;
  wire rs_26_4_1;
  wire rs_26_4_2;
  wire rs_26_5;
  wire rs_26_5_2;
  wire rs_26_6;
  wire rs_26_6_2;
  assign o__rs_26_6_2 = rs_26_6_2;
  wire rs_26_7_2;
  wire rs_26_7_3;
  wire rs_26_8;
  wire rs_26_8_1;
  wire rs_26_9;
  wire rs_26_9_1;
  wire rs_27_0;
  wire rs_27_19_2;
  wire rs_27_19_3;
  assign o__rs_27_19_3 = rs_27_19_3;
  wire rs_27_3_1;
  wire rs_28_0;
  wire rs_28_19_1;
  assign o__rs_28_19_1 = rs_28_19_1;
  wire rs_28_19_2;
  wire rs_28_3_1;
  wire rs_29_0;
  wire rs_29_0_1;
  wire rs_29_0_2;
  wire rs_29_1;
  wire rs_29_10_2;
  assign o__rs_29_10_2 = rs_29_10_2;
  wire rs_29_19_1;
  wire rs_29_19_2;
  assign o__rs_29_19_2 = rs_29_19_2;
  wire rs_29_1_2;
  wire rs_29_2;
  wire rs_29_2_2;
  wire rs_29_3;
  assign o__rs_29_3 = rs_29_3;
  wire rs_29_3_1;
  wire rs_29_3_2;
  assign o__rs_29_3_2 = rs_29_3_2;
  wire rs_29_3_3;
  assign o__rs_29_3_3 = rs_29_3_3;
  wire rs_29_4;
  wire rs_29_4_1;
  assign o__rs_29_4_1 = rs_29_4_1;
  wire rs_29_4_2;
  assign o__rs_29_4_2 = rs_29_4_2;
  wire rs_29_5;
  wire rs_29_5_2;
  assign o__rs_29_5_2 = rs_29_5_2;
  wire rs_29_6;
  wire rs_29_6_2;
  assign o__rs_29_6_2 = rs_29_6_2;
  wire rs_29_7;
  wire rs_29_7_3;
  wire rs_29_8_2;
  wire rs_29_9_2;
  wire rs_30_0;
  wire rs_30_10_1;
  wire rs_30_10_2;
  wire rs_30_19_2;
  assign o__rs_30_19_2 = rs_30_19_2;
  wire rs_30_3_2;
  wire rs_30_7;
  wire rs_31_0;
  wire rs_31_10_2;
  assign o__rs_31_10_2 = rs_31_10_2;
  wire rs_31_19_2;
  assign o__rs_31_19_2 = rs_31_19_2;
  wire rs_31_3_2;
  wire rs_31_7;
  assign o__rs_31_7 = rs_31_7;
  wire rs_32_0;
  wire rs_32_18_3;
  assign o__rs_32_18_3 = rs_32_18_3;
  wire rs_32_19;
  wire rs_32_19_2;
  wire rs_32_3_2;
  assign o__rs_32_3_2 = rs_32_3_2;
  wire rs_32_7;
  assign o__rs_32_7 = rs_32_7;
  wire rs_32_8_1;
  wire rs_33_0;
  wire rs_33_10;
  wire rs_33_10_1;
  wire rs_33_10_3;
  assign o__rs_33_10_3 = rs_33_10_3;
  wire rs_33_11;
  wire rs_33_11_2;
  wire rs_33_11_3;
  assign o__rs_33_11_3 = rs_33_11_3;
  wire rs_33_12;
  assign o__rs_33_12 = rs_33_12;
  wire rs_33_12_2;
  wire rs_33_13_2;
  wire rs_33_14_2;
  wire rs_33_15_2;
  wire rs_33_16_2;
  wire rs_33_17_2;
  wire rs_33_18;
  assign o__rs_33_18 = rs_33_18;
  wire rs_33_19_2;
  assign o__rs_33_19_2 = rs_33_19_2;
  wire rs_33_6_1;
  assign o__rs_33_6_1 = rs_33_6_1;
  wire rs_33_7_3;
  assign o__rs_33_7_3 = rs_33_7_3;
  wire rs_33_8;
  wire rs_33_8_1;
  wire rs_33_8_2;
  wire rs_33_9;
  wire rs_33_9_2;
  wire rs_34_0;
  wire rs_34_10;
  assign o__rs_34_10 = rs_34_10;
  wire rs_34_13_2;
  assign o__rs_34_13_2 = rs_34_13_2;
  wire rs_35_0;
  wire rs_36_0;
  wire rs_36_19_3;
  assign o__rs_36_19_3 = rs_36_19_3;
  wire rs_37_0;
  wire rs_37_19_2;
  assign o__rs_37_19_2 = rs_37_19_2;
  wire rs_38_0;
  wire rs_38_19_2;
  assign o__rs_38_19_2 = rs_38_19_2;
  wire rs_39_0;
  wire rs_39_0_2;
  assign o__rs_39_0_2 = rs_39_0_2;
  wire rs_39_19_2;
  assign o__rs_39_19_2 = rs_39_19_2;
  wire rs_40_0;
  wire rs_40_19_2;
  assign o__rs_40_19_2 = rs_40_19_2;
  wire rs_41_0;
  wire rs_41_19_2;
  assign o__rs_41_19_2 = rs_41_19_2;
  wire rs_42_0;
  wire rs_42_19_2;
  assign o__rs_42_19_2 = rs_42_19_2;
  wire rs_43_0;
  wire rs_43_10;
  wire rs_43_11;
  wire rs_43_11_1;
  assign o__rs_43_11_1 = rs_43_11_1;
  wire rs_43_12;
  wire rs_43_13;
  wire rs_43_14;
  wire rs_43_15;
  wire rs_43_16;
  wire rs_43_17;
  wire rs_43_18_3;
  assign o__rs_43_18_3 = rs_43_18_3;
  wire rs_43_19_2;
  assign o__rs_43_19_2 = rs_43_19_2;
  wire rs_43_4;
  assign o__rs_43_4 = rs_43_4;
  wire rs_43_5;
  assign o__rs_43_5 = rs_43_5;
  wire rs_43_6;
  assign o__rs_43_6 = rs_43_6;
  wire rs_43_7;
  assign o__rs_43_7 = rs_43_7;
  wire rs_43_8;
  wire rs_43_9;
  wire rs_44_0;
  wire rs_44_4_1;
  assign o__rs_44_4_1 = rs_44_4_1;
  wire rs_45_0;
  wire rs_45_13_1;
  assign o__rs_45_13_1 = rs_45_13_1;
  wire rs_45_4_1;
  assign o__rs_45_4_1 = rs_45_4_1;
  wire rs_46_0;
  wire rs_46_10_1;
  assign o__rs_46_10_1 = rs_46_10_1;
  wire rs_46_11_3;
  wire rs_46_12_3;
  assign o__rs_46_12_3 = rs_46_12_3;
  wire rs_46_4_3;
  wire rs_47_0;
  wire rs_47_10;
  wire rs_47_4_2;
  wire rs_48_0;
  wire rs_48_10;
  wire rs_48_4_1;
  wire rs_49_0;
  wire rs_49_10;
  wire rs_49_3;
  assign o__rs_49_3 = rs_49_3;
  wire rs_49_4_1;
  wire rs_50_0;
  assign o__rs_50_0 = rs_50_0;
  wire rs_50_0_1;
  wire rs_50_10_1;
  assign o__rs_50_10_1 = rs_50_10_1;
  wire rs_50_10_2;
  wire rs_50_1_1;
  wire rs_50_2_1;
  wire rs_50_3_1;
  assign o__rs_50_3_1 = rs_50_3_1;
  wire rs_50_3_3;
  wire rs_50_4;
  wire rs_50_5;
  wire rs_50_6;
  wire rs_50_7_2;
  assign o__rs_50_7_2 = rs_50_7_2;
  wire rs_50_8_1;
  wire rs_50_9_1;
  wire rsg_rs_25_13_1_cl2S_0;
  assign o__rsg_rs_25_13_1_cl2S_0 = rsg_rs_25_13_1_cl2S_0;
  wire rsg_rs_25_13_1_cl2S_1;
  wire rsg_rs_25_13_1_cl2S_2;
  assign o__rsg_rs_25_13_1_cl2S_2 = rsg_rs_25_13_1_cl2S_2;
  wire rsg_rs_31_10_2_cl3S_0;
  wire rsg_rs_31_10_2_cl3S_1;
  wire rsg_rs_31_10_2_cl3S_2;
  wire rsg_rs_31_10_2_cl3S_3;
  wire rsg_rs_31_10_2_cl3S_4;
  wire rsg_rs_34_13_2_cl3S_0;
  assign o__rsg_rs_34_13_2_cl3S_0 = rsg_rs_34_13_2_cl3S_0;
  wire rsl_hrq_03_2;
  wire rsl_hrq_03_3;
  assign o__rsl_hrq_03_3 = rsl_hrq_03_3;
  wire rsl_jd_W_1;
  wire rsl_jd_W_10;
  wire rsl_jd_W_11;
  wire rsl_jd_W_12;
  wire rsl_jd_W_2;
  wire rsl_jd_W_3;
  wire rsl_jd_W_4;
  wire rsl_jd_W_5;
  wire rsl_jd_W_6;
  wire rsl_jd_W_7;
  wire rsl_jd_W_8;
  wire rsl_jd_W_9;
  wire rsl_jw_W_l1_31;
  assign o__rsl_jw_W_l1_31 = rsl_jw_W_l1_31;
  wire rsl_jw_W_l1_32;
  wire rsl_pv_E_1;
  wire rsl_q_W_l0_1;
  wire rsl_xrE_2S_l0_0;
  wire rsl_xrE_2S_l0_1;
  wire rsl_xrE_2S_l0_2;
  assign o__rsl_xrE_2S_l0_2 = rsl_xrE_2S_l0_2;
  wire rst_n;
  assign rst_n = i__rst_n;
  wire rst_sync0;
  wire rst_sync1;
  wire [15:0] u_s_3S_ck_line;
  assign u_s_3S_ck_line[15:15] = i__u_s_3S_ck_line[15:15];
  wire [15:0] u_s_4S_ck_line;
  assign u_s_4S_ck_line[12:12] = i__u_s_4S_ck_line[12:12];
  wire [69:0] w_r_f_3L01_dst;
  wire [69:0] w_r_f_3L01_lnd;
  assign o__w_r_f_3L01_lnd = w_r_f_3L01_lnd;
  wire [69:0] w_r_f_3L01_src;
  assign w_r_f_3L01_src[69:0] = i__w_r_f_3L01_src[69:0];
  wire [275:0] w_xrW_2S_l3_dst;
  wire [275:0] w_xrW_2S_l3_lnd;
  assign o__w_xrW_2S_l3_lnd = w_xrW_2S_l3_lnd;
  wire [275:0] w_xrW_2S_l3_src;
  assign w_xrW_2S_l3_src[275:0] = i__w_xrW_2S_l3_src[275:0];
  wire [275:0] w_xrW_3S_l0_dst;
  wire [275:0] w_xrW_3S_l0_lnd;
  assign o__w_xrW_3S_l0_lnd = w_xrW_3S_l0_lnd;
  wire [275:0] w_xrW_3S_l0_src;
  assign w_xrW_3S_l0_src[275:0] = i__w_xrW_3S_l0_src[275:0];
  wire ld_r_f_3L01__ckf_d; wire [69:0] ld_r_f_3L01__i_d;   // lane flight 1 cycles (tt: S1 -159.1 ps, E 2, D 4)
  dv_flight_sim #(.W(70), .F(1)) ld_r_f_3L01__flight (.ck_in(nr_f_3L01_fck[1]), .rs(rs_34_13_2), .i_in(w_r_f_3L01_dst), .ck_out(ld_r_f_3L01__ckf_d), .i_out(ld_r_f_3L01__i_d));
  wire ld_xrW_2S_l3__ckf_d; wire [275:0] ld_xrW_2S_l3__i_d;   // lane flight 4 cycles (tt: S1 -2579.2 ps, E 5, D 4)
  dv_flight_sim #(.W(276), .F(4)) ld_xrW_2S_l3__flight (.ck_in(nxrW_2S_l3_fck[7]), .rs(rsg_rs_25_13_1_cl2S_2), .i_in(w_xrW_2S_l3_dst), .ck_out(ld_xrW_2S_l3__ckf_d), .i_out(ld_xrW_2S_l3__i_d));
  wire ld_xrW_3S_l0__ckf_d; wire [275:0] ld_xrW_3S_l0__i_d;   // lane flight 4 cycles (tt: S1 -2557.8 ps, E 5, D 4)
  dv_flight_sim #(.W(276), .F(4)) ld_xrW_3S_l0__flight (.ck_in(nxrW_3S_l0_fck[7]), .rs(rsg_rs_34_13_2_cl3S_0), .i_in(w_xrW_3S_l0_dst), .ck_out(ld_xrW_3S_l0__ckf_d), .i_out(ld_xrW_3S_l0__i_d));
  dsfd_rly_1_WN st_rsg_rs_25_13_1_cl2S_0 (.ck(ck_cl2S), .rs(rs_25_13_1), .i(rs_25_13_1), .o(rsg_rs_25_13_1_cl2S_0));
  dsfd_rly_1_WN st_rsg_rs_25_13_1_cl2S_1 (.ck(ck_cl2S), .rs(rsg_rs_25_13_1_cl2S_0), .i(rsg_rs_25_13_1_cl2S_0), .o(rsg_rs_25_13_1_cl2S_1));
  dsfd_rly_1_WN st_rsg_rs_25_13_1_cl2S_2 (.ck(ck_cl2S), .rs(rsg_rs_25_13_1_cl2S_1), .i(rsg_rs_25_13_1_cl2S_1), .o(rsg_rs_25_13_1_cl2S_2));
  dsfd_dvland_276 ld_xrW_2S_l3 (.ck_f(ld_xrW_2S_l3__ckf_d), .i(ld_xrW_2S_l3__i_d), .ck(ck_cl2S), .rs(rsg_rs_25_13_1_cl2S_2), .k(3'd5), .o(w_xrW_2S_l3_lnd), .fault(land_fault[40]));
  dsfd_rly_1_WN st_rsg_rs_34_13_2_cl3S_0 (.ck(ck_cl3S), .rs(rs_34_13_2), .i(rs_34_13_2), .o(rsg_rs_34_13_2_cl3S_0));
  dsfd_dvland_276 ld_xrW_3S_l0 (.ck_f(ld_xrW_3S_l0__ckf_d), .i(ld_xrW_3S_l0__i_d), .ck(ck_cl3S), .rs(rsg_rs_34_13_2_cl3S_0), .k(3'd5), .o(w_xrW_3S_l0_lnd), .fault(land_fault[66]));
  dsfd_rly_1_WN st_rsg_rs_31_10_2_cl3S_0 (.ck(ck_cl3S), .rs(rs_31_10_2), .i(rs_31_10_2), .o(rsg_rs_31_10_2_cl3S_0));
  dsfd_rly_1_WN st_rsg_rs_31_10_2_cl3S_1 (.ck(ck_cl3S), .rs(rsg_rs_31_10_2_cl3S_0), .i(rsg_rs_31_10_2_cl3S_0), .o(rsg_rs_31_10_2_cl3S_1));
  dsfd_rly_1_WN st_rsg_rs_31_10_2_cl3S_2 (.ck(ck_cl3S), .rs(rsg_rs_31_10_2_cl3S_1), .i(rsg_rs_31_10_2_cl3S_1), .o(rsg_rs_31_10_2_cl3S_2));
  dsfd_rly_1_WN st_rsg_rs_31_10_2_cl3S_3 (.ck(ck_cl3S), .rs(rsg_rs_31_10_2_cl3S_2), .i(rsg_rs_31_10_2_cl3S_2), .o(rsg_rs_31_10_2_cl3S_3));
  dsfd_rly_1_WN st_rsg_rs_31_10_2_cl3S_4 (.ck(ck_cl3S), .rs(rsg_rs_31_10_2_cl3S_3), .i(rsg_rs_31_10_2_cl3S_3), .o(rsg_rs_31_10_2_cl3S_4));
  dsfd_dvland_70 ld_r_f_3L01 (.ck_f(ld_r_f_3L01__ckf_d), .i(ld_r_f_3L01__i_d), .ck(ck_cl3S), .rs(rs_34_13_2), .k(3'd2), .o(w_r_f_3L01_lnd), .fault(land_fault[71]));
  ICGx4_ASAP7_75t_R fwd_xrW_2S_l3 (.CLK(u_s_3S_ck_line[15]), .ENA(rs_34_13_2), .SE(1'b0), .GCLK(nxrW_2S_l3_fck[0]));
  dsfd_dvrlyh_276_EW st_xrW_2S_l3_0 (.i(w_xrW_2S_l3_src), .o(r_xrW_2S_l3_0), .ck(nxrW_2S_l3_fck[0]), .ck_o(nxrW_2S_l3_fck[1]), .rs(rs_32_19));
  dsfd_dvrlyh_276_EW st_xrW_2S_l3_1 (.i(r_xrW_2S_l3_0), .o(r_xrW_2S_l3_1), .ck(nxrW_2S_l3_fck[1]), .ck_o(nxrW_2S_l3_fck[2]), .rs(rs_31_19_2));
  dsfd_dvrlyh_276_EW st_xrW_2S_l3_2 (.i(r_xrW_2S_l3_1), .o(r_xrW_2S_l3_2), .ck(nxrW_2S_l3_fck[2]), .ck_o(nxrW_2S_l3_fck[3]), .rs(rs_30_19_2));
  dsfd_dvrlyh_276_EW st_xrW_2S_l3_3 (.i(r_xrW_2S_l3_2), .o(r_xrW_2S_l3_3), .ck(nxrW_2S_l3_fck[3]), .ck_o(nxrW_2S_l3_fck[4]), .rs(rs_29_19_2));
  dsfd_dvrlyh_276_EW st_xrW_2S_l3_4 (.i(r_xrW_2S_l3_3), .o(r_xrW_2S_l3_4), .ck(nxrW_2S_l3_fck[4]), .ck_o(nxrW_2S_l3_fck[5]), .rs(rs_29_19_1));
  dsfd_dvrlyh_276_EW st_xrW_2S_l3_5 (.i(r_xrW_2S_l3_4), .o(r_xrW_2S_l3_5), .ck(nxrW_2S_l3_fck[5]), .ck_o(nxrW_2S_l3_fck[6]), .rs(rs_28_19_1));
  dsfd_dvrlyh_276_EW st_xrW_2S_l3_6 (.i(r_xrW_2S_l3_5), .o(w_xrW_2S_l3_dst), .ck(nxrW_2S_l3_fck[6]), .ck_o(nxrW_2S_l3_fck[7]), .rs(rs_27_19_3));
  ICGx4_ASAP7_75t_R fwd_xrW_3S_l0 (.CLK(u_s_4S_ck_line[12]), .ENA(rs_45_13_1), .SE(1'b0), .GCLK(nxrW_3S_l0_fck[0]));
  dsfd_dvrlyh_276_EW st_xrW_3S_l0_0 (.i(w_xrW_3S_l0_src), .o(r_xrW_3S_l0_0), .ck(nxrW_3S_l0_fck[0]), .ck_o(nxrW_3S_l0_fck[1]), .rs(rs_42_19_2));
  dsfd_dvrlyh_276_EW st_xrW_3S_l0_1 (.i(r_xrW_3S_l0_0), .o(r_xrW_3S_l0_1), .ck(nxrW_3S_l0_fck[1]), .ck_o(nxrW_3S_l0_fck[2]), .rs(rs_41_19_2));
  dsfd_dvrlyh_276_EW st_xrW_3S_l0_2 (.i(r_xrW_3S_l0_1), .o(r_xrW_3S_l0_2), .ck(nxrW_3S_l0_fck[2]), .ck_o(nxrW_3S_l0_fck[3]), .rs(rs_40_19_2));
  dsfd_dvrlyh_276_EW st_xrW_3S_l0_3 (.i(r_xrW_3S_l0_2), .o(r_xrW_3S_l0_3), .ck(nxrW_3S_l0_fck[3]), .ck_o(nxrW_3S_l0_fck[4]), .rs(rs_39_19_2));
  dsfd_dvrlyh_276_EW st_xrW_3S_l0_4 (.i(r_xrW_3S_l0_3), .o(r_xrW_3S_l0_4), .ck(nxrW_3S_l0_fck[4]), .ck_o(nxrW_3S_l0_fck[5]), .rs(rs_38_19_2));
  dsfd_dvrlyh_276_EW st_xrW_3S_l0_5 (.i(r_xrW_3S_l0_4), .o(r_xrW_3S_l0_5), .ck(nxrW_3S_l0_fck[5]), .ck_o(nxrW_3S_l0_fck[6]), .rs(rs_37_19_2));
  dsfd_dvrlyh_276_EW st_xrW_3S_l0_6 (.i(r_xrW_3S_l0_5), .o(w_xrW_3S_l0_dst), .ck(nxrW_3S_l0_fck[6]), .ck_o(nxrW_3S_l0_fck[7]), .rs(rs_36_19_3));
  ICGx4_ASAP7_75t_R fwd_r_f_3L01 (.CLK(ck_cl3S), .ENA(rsg_rs_31_10_2_cl3S_4), .SE(1'b0), .GCLK(nr_f_3L01_fck[0]));
  dsfd_dvrlyh_70_SN st_r_f_3L01_0 (.i(w_r_f_3L01_src), .o(w_r_f_3L01_dst), .ck(nr_f_3L01_fck[0]), .ck_o(nr_f_3L01_fck[1]), .rs(rs_33_12));
  dsfd_rly_1_WN rst_root0 (.ck(ck_south4), .rs(rst_n), .i(rst_n), .o(rst_sync0));
  dsfd_rly_1_WN rst_root1 (.ck(ck_south4), .rs(rst_sync0), .i(rst_sync0), .o(rst_sync1));
  dsfd_rly_1_WN st_rs_39_0_2 (.ck(ck_south4), .rs(rst_sync1), .i(rst_sync1), .o(rs_39_0_2));
  dsfd_rly_1_WN st_rs_39_0 (.ck(ck_south4), .rs(rs_39_0_2), .i(rs_39_0_2), .o(rs_39_0));
  dsfd_rly_1_WN st_rs_40_0 (.ck(ck_south4), .rs(rs_39_0_2), .i(rs_39_0_2), .o(rs_40_0));
  dsfd_rly_1_WN st_rs_38_0 (.ck(ck_south4), .rs(rs_39_0), .i(rs_39_0), .o(rs_38_0));
  dsfd_rly_1_WN st_rs_41_0 (.ck(ck_south4), .rs(rs_40_0), .i(rs_40_0), .o(rs_41_0));
  dsfd_rly_1_WN st_rs_37_0 (.ck(ck_south3), .rs(rs_38_0), .i(rs_38_0), .o(rs_37_0));
  dsfd_rly_1_WN st_rs_42_0 (.ck(ck_south4), .rs(rs_41_0), .i(rs_41_0), .o(rs_42_0));
  dsfd_rly_1_WN st_rs_36_0 (.ck(ck_south3), .rs(rs_37_0), .i(rs_37_0), .o(rs_36_0));
  dsfd_rly_1_WN st_rs_43_0 (.ck(ck_south4), .rs(rs_42_0), .i(rs_42_0), .o(rs_43_0));
  dsfd_rly_1_WN st_rs_35_0 (.ck(ck_south3), .rs(rs_36_0), .i(rs_36_0), .o(rs_35_0));
  dsfd_rly_1_WN st_rs_44_0 (.ck(ck_south4), .rs(rs_43_0), .i(rs_43_0), .o(rs_44_0));
  dsfd_rly_1_WN st_rs_34_0 (.ck(ck_south3), .rs(rs_35_0), .i(rs_35_0), .o(rs_34_0));
  dsfd_rly_1_WN st_rs_45_0 (.ck(ck_south4), .rs(rs_44_0), .i(rs_44_0), .o(rs_45_0));
  dsfd_rly_1_WN st_rs_33_0 (.ck(ck_south3), .rs(rs_34_0), .i(rs_34_0), .o(rs_33_0));
  dsfd_rly_1_WN st_rs_46_0 (.ck(ck_south4), .rs(rs_45_0), .i(rs_45_0), .o(rs_46_0));
  dsfd_rly_1_WN st_rs_32_0 (.ck(ck_south3), .rs(rs_33_0), .i(rs_33_0), .o(rs_32_0));
  dsfd_rly_1_WN st_rs_47_0 (.ck(ck_south4), .rs(rs_46_0), .i(rs_46_0), .o(rs_47_0));
  dsfd_rly_1_WN st_rs_31_0 (.ck(ck_south3), .rs(rs_32_0), .i(rs_32_0), .o(rs_31_0));
  dsfd_rly_1_WN st_rs_48_0 (.ck(ck_south4), .rs(rs_47_0), .i(rs_47_0), .o(rs_48_0));
  dsfd_rly_1_WN st_rs_30_0 (.ck(ck_south3), .rs(rs_31_0), .i(rs_31_0), .o(rs_30_0));
  dsfd_rly_1_WN st_rs_49_0 (.ck(ck_south5), .rs(rs_48_0), .i(rs_48_0), .o(rs_49_0));
  dsfd_rly_1_WN st_rs_29_0_1 (.ck(ck_south3), .rs(rs_30_0), .i(rs_30_0), .o(rs_29_0_1));
  dsfd_rly_1_WN st_rs_50_0_1 (.ck(ck_south5), .rs(rs_49_0), .i(rs_49_0), .o(rs_50_0_1));
  dsfd_rly_1_WN st_rs_29_0 (.ck(ck_south3), .rs(rs_29_0_1), .i(rs_29_0_1), .o(rs_29_0));
  dsfd_rly_1_WN st_rs_50_0 (.ck(ck_south5), .rs(rs_50_0_1), .i(rs_50_0_1), .o(rs_50_0));
  dsfd_rly_1_WN st_rs_28_0 (.ck(ck_south3), .rs(rs_29_0), .i(rs_29_0), .o(rs_28_0));
  dsfd_rly_1_WN st_rs_29_0_2 (.ck(ck_south3), .rs(rs_29_0), .i(rs_29_0), .o(rs_29_0_2));
  dsfd_rly_1_WN st_rs_29_1 (.ck(ck_south3), .rs(rs_29_0), .i(rs_29_0), .o(rs_29_1));
  dsfd_rly_1_WN st_rs_50_1_1 (.ck(ck_south5), .rs(rs_50_0), .i(rs_50_0), .o(rs_50_1_1));
  dsfd_rly_1_WN st_rs_27_0 (.ck(ck_south3), .rs(rs_28_0), .i(rs_28_0), .o(rs_27_0));
  dsfd_rly_1_WN st_rs_29_1_2 (.ck(ck_south3), .rs(rs_29_0_2), .i(rs_29_0_2), .o(rs_29_1_2));
  dsfd_rly_1_WN st_rs_29_2 (.ck(ck_south3), .rs(rs_29_1), .i(rs_29_1), .o(rs_29_2));
  dsfd_rly_1_WN st_rs_50_2_1 (.ck(ck_south5), .rs(rs_50_1_1), .i(rs_50_1_1), .o(rs_50_2_1));
  dsfd_rly_1_WN st_rs_26_0 (.ck(ck_south3), .rs(rs_27_0), .i(rs_27_0), .o(rs_26_0));
  dsfd_rly_1_WN st_rs_29_2_2 (.ck(ck_south3), .rs(rs_29_1_2), .i(rs_29_1_2), .o(rs_29_2_2));
  dsfd_rly_1_WN st_rs_29_3_1 (.ck(ck_south3), .rs(rs_29_2), .i(rs_29_2), .o(rs_29_3_1));
  dsfd_rly_1_WN st_rs_50_3_3 (.ck(ck_south5), .rs(rs_50_2_1), .i(rs_50_2_1), .o(rs_50_3_3));
  dsfd_rly_1_WN st_rs_26_1 (.ck(ck_south3), .rs(rs_26_0), .i(rs_26_0), .o(rs_26_1));
  dsfd_rly_1_WN st_rs_29_3 (.ck(ck_south3), .rs(rs_29_2_2), .i(rs_29_2_2), .o(rs_29_3));
  dsfd_rly_1_WN st_rs_29_3_2 (.ck(ck_south3), .rs(rs_29_2_2), .i(rs_29_2_2), .o(rs_29_3_2));
  dsfd_rly_1_WN st_rs_29_3_3 (.ck(ck_south3), .rs(rs_29_3_1), .i(rs_29_3_1), .o(rs_29_3_3));
  dsfd_rly_1_WN st_rs_29_4_1 (.ck(ck_south3), .rs(rs_29_3_1), .i(rs_29_3_1), .o(rs_29_4_1));
  dsfd_rly_1_WN st_rs_50_3_1 (.ck(ck_south5), .rs(rs_50_3_3), .i(rs_50_3_3), .o(rs_50_3_1));
  dsfd_rly_1_WN st_rs_26_2 (.ck(ck_south3), .rs(rs_26_1), .i(rs_26_1), .o(rs_26_2));
  dsfd_rly_1_WN st_rs_28_3_1 (.ck(ck_south3), .rs(rs_29_3_2), .i(rs_29_3_2), .o(rs_28_3_1));
  dsfd_rly_1_WN st_rs_29_4 (.ck(ck_south3), .rs(rs_29_3), .i(rs_29_3), .o(rs_29_4));
  dsfd_rly_1_WN st_rs_29_4_2 (.ck(ck_south3), .rs(rs_29_4_1), .i(rs_29_4_1), .o(rs_29_4_2));
  dsfd_rly_1_WN st_rs_30_3_2 (.ck(ck_south3), .rs(rs_29_3_3), .i(rs_29_3_3), .o(rs_30_3_2));
  dsfd_rly_1_WN st_rs_49_3 (.ck(ck_south5), .rs(rs_50_3_1), .i(rs_50_3_1), .o(rs_49_3));
  dsfd_rly_1_WN st_rs_50_4 (.ck(ck_south5), .rs(rs_50_3_1), .i(rs_50_3_1), .o(rs_50_4));
  dsfd_rly_1_WN st_rs_26_3 (.ck(ck_south3), .rs(rs_26_2), .i(rs_26_2), .o(rs_26_3));
  dsfd_rly_1_WN st_rs_27_3_1 (.ck(ck_south3), .rs(rs_28_3_1), .i(rs_28_3_1), .o(rs_27_3_1));
  dsfd_rly_1_WN st_rs_29_5 (.ck(ck_south2), .rs(rs_29_4), .i(rs_29_4), .o(rs_29_5));
  dsfd_rly_1_WN st_rs_29_5_2 (.ck(ck_south2), .rs(rs_29_4_2), .i(rs_29_4_2), .o(rs_29_5_2));
  dsfd_rly_1_WN st_rs_31_3_2 (.ck(ck_south3), .rs(rs_30_3_2), .i(rs_30_3_2), .o(rs_31_3_2));
  dsfd_rly_1_WN st_rs_49_4_1 (.ck(ck_south4), .rs(rs_49_3), .i(rs_49_3), .o(rs_49_4_1));
  dsfd_rly_1_WN st_rs_50_5 (.ck(ck_south5), .rs(rs_50_4), .i(rs_50_4), .o(rs_50_5));
  dsfd_rly_1_WN st_rs_26_3_1 (.ck(ck_south3), .rs(rs_27_3_1), .i(rs_27_3_1), .o(rs_26_3_1));
  dsfd_rly_1_WN st_rs_26_3_3 (.ck(ck_south2), .rs(rs_27_3_1), .i(rs_27_3_1), .o(rs_26_3_3));
  dsfd_rly_1_WN st_rs_26_4_1 (.ck(ck_south2), .rs(rs_26_3), .i(rs_26_3), .o(rs_26_4_1));
  dsfd_rly_1_WN st_rs_29_6 (.ck(ck_south2), .rs(rs_29_5), .i(rs_29_5), .o(rs_29_6));
  dsfd_rly_1_WN st_rs_29_6_2 (.ck(ck_south2), .rs(rs_29_5_2), .i(rs_29_5_2), .o(rs_29_6_2));
  dsfd_rly_1_WN st_rs_32_3_2 (.ck(ck_south3), .rs(rs_31_3_2), .i(rs_31_3_2), .o(rs_32_3_2));
  dsfd_rly_1_WN st_rs_48_4_1 (.ck(ck_south4), .rs(rs_49_4_1), .i(rs_49_4_1), .o(rs_48_4_1));
  dsfd_rly_1_WN st_rs_50_6 (.ck(ck_south5), .rs(rs_50_5), .i(rs_50_5), .o(rs_50_6));
  dsfd_rly_1_WN st_rs_25_3_1 (.ck(ck_south3), .rs(rs_26_3_1), .i(rs_26_3_1), .o(rs_25_3_1));
  dsfd_rly_1_WN st_rs_26_4 (.ck(ck_south2), .rs(rs_26_3_3), .i(rs_26_3_3), .o(rs_26_4));
  dsfd_rly_1_WN st_rs_26_4_2 (.ck(ck_south2), .rs(rs_26_4_1), .i(rs_26_4_1), .o(rs_26_4_2));
  dsfd_rly_1_WN st_rs_29_7 (.ck(ck_south2), .rs(rs_29_6), .i(rs_29_6), .o(rs_29_7));
  dsfd_rly_1_WN st_rs_29_7_3 (.ck(ck_south2), .rs(rs_29_6_2), .i(rs_29_6_2), .o(rs_29_7_3));
  dsfd_rly_1_WN st_rs_47_4_2 (.ck(ck_south4), .rs(rs_48_4_1), .i(rs_48_4_1), .o(rs_47_4_2));
  dsfd_rly_1_WN st_rs_50_7_2 (.ck(ck_south4), .rs(rs_50_6), .i(rs_50_6), .o(rs_50_7_2));
  dsfd_rly_1_WN st_rsl_hrq_03_3 (.ck(ck_south3), .rs(rs_32_3_2), .i(rs_32_3_2), .o(rsl_hrq_03_3));
  dsfd_rly_1_WN st_rs_25_4_1 (.ck(ck_south2), .rs(rs_25_3_1), .i(rs_25_3_1), .o(rs_25_4_1));
  dsfd_rly_1_WN st_rs_26_5 (.ck(ck_south2), .rs(rs_26_4), .i(rs_26_4), .o(rs_26_5));
  dsfd_rly_1_WN st_rs_26_5_2 (.ck(ck_south2), .rs(rs_26_4_2), .i(rs_26_4_2), .o(rs_26_5_2));
  dsfd_rly_1_WN st_rs_29_8_2 (.ck(ck_south2), .rs(rs_29_7_3), .i(rs_29_7_3), .o(rs_29_8_2));
  dsfd_rly_1_WN st_rs_30_7 (.ck(ck_south3), .rs(rs_29_7), .i(rs_29_7), .o(rs_30_7));
  dsfd_rly_1_WN st_rs_46_4_3 (.ck(ck_south4), .rs(rs_47_4_2), .i(rs_47_4_2), .o(rs_46_4_3));
  dsfd_rly_1_WN st_rs_50_8_1 (.ck(ck_south5), .rs(rs_50_7_2), .i(rs_50_7_2), .o(rs_50_8_1));
  dsfd_rly_1_WN st_rsl_hrq_03_2 (.ck(ck_south3), .rs(rsl_hrq_03_3), .i(rsl_hrq_03_3), .o(rsl_hrq_03_2));
  dsfd_rly_1_WN st_rs_25_5_1 (.ck(ck_south2), .rs(rs_25_4_1), .i(rs_25_4_1), .o(rs_25_5_1));
  dsfd_rly_1_WN st_rs_26_6 (.ck(ck_south2), .rs(rs_26_5), .i(rs_26_5), .o(rs_26_6));
  dsfd_rly_1_WN st_rs_26_6_2 (.ck(ck_south2), .rs(rs_26_5_2), .i(rs_26_5_2), .o(rs_26_6_2));
  dsfd_rly_1_WN st_rs_29_9_2 (.ck(ck_south2), .rs(rs_29_8_2), .i(rs_29_8_2), .o(rs_29_9_2));
  dsfd_rly_1_WN st_rs_31_7 (.ck(ck_south3), .rs(rs_30_7), .i(rs_30_7), .o(rs_31_7));
  dsfd_rly_1_WN st_rs_33_6_1 (.ck(ck_south3), .rs(rsl_hrq_03_2), .i(rsl_hrq_03_2), .o(rs_33_6_1));
  dsfd_rly_1_WN st_rs_45_4_1 (.ck(ck_south4), .rs(rs_46_4_3), .i(rs_46_4_3), .o(rs_45_4_1));
  dsfd_rly_1_WN st_rs_50_9_1 (.ck(ck_south5), .rs(rs_50_8_1), .i(rs_50_8_1), .o(rs_50_9_1));
  dsfd_rly_1_WN st_rs_25_6_1 (.ck(ck_south2), .rs(rs_25_5_1), .i(rs_25_5_1), .o(rs_25_6_1));
  dsfd_rly_1_WN st_rs_26_7_2 (.ck(ck_south2), .rs(rs_26_6), .i(rs_26_6), .o(rs_26_7_2));
  dsfd_rly_1_WN st_rs_26_7_3 (.ck(ck_south2), .rs(rs_26_6_2), .i(rs_26_6_2), .o(rs_26_7_3));
  dsfd_rly_1_WN st_rs_29_10_2 (.ck(ck_south2), .rs(rs_29_9_2), .i(rs_29_9_2), .o(rs_29_10_2));
  dsfd_rly_1_WN st_rs_32_7 (.ck(ck_south3), .rs(rs_31_7), .i(rs_31_7), .o(rs_32_7));
  dsfd_rly_1_WN st_rs_33_7_3 (.ck(ck_south3), .rs(rs_33_6_1), .i(rs_33_6_1), .o(rs_33_7_3));
  dsfd_rly_1_WN st_rs_44_4_1 (.ck(ck_south4), .rs(rs_45_4_1), .i(rs_45_4_1), .o(rs_44_4_1));
  dsfd_rly_1_WN st_rs_50_10_2 (.ck(ck_south5), .rs(rs_50_9_1), .i(rs_50_9_1), .o(rs_50_10_2));
  dsfd_rly_1_WN st_rs_25_7_1 (.ck(ck_cl2S), .rs(rs_25_6_1), .i(rs_25_6_1), .o(rs_25_7_1));
  dsfd_rly_1_WN st_rs_26_8 (.ck(ck_south2), .rs(rs_26_7_3), .i(rs_26_7_3), .o(rs_26_8));
  dsfd_rly_1_WN st_rs_26_8_1 (.ck(ck_south2), .rs(rs_26_7_2), .i(rs_26_7_2), .o(rs_26_8_1));
  dsfd_rly_1_WN st_rs_30_10_1 (.ck(ck_south3), .rs(rs_29_10_2), .i(rs_29_10_2), .o(rs_30_10_1));
  dsfd_rly_1_WN st_rs_32_8_1 (.ck(ck_south3), .rs(rs_32_7), .i(rs_32_7), .o(rs_32_8_1));
  dsfd_rly_1_WN st_rs_33_8_1 (.ck(ck_south3), .rs(rs_33_7_3), .i(rs_33_7_3), .o(rs_33_8_1));
  dsfd_rly_1_WN st_rs_43_4 (.ck(ck_south4), .rs(rs_44_4_1), .i(rs_44_4_1), .o(rs_43_4));
  dsfd_rly_1_WN st_rs_50_10_1 (.ck(ck_south5), .rs(rs_50_10_2), .i(rs_50_10_2), .o(rs_50_10_1));
  dsfd_rly_1_WN st_rs_25_8_1 (.ck(ck_south2), .rs(rs_25_7_1), .i(rs_25_7_1), .o(rs_25_8_1));
  dsfd_rly_1_WN st_rs_26_9 (.ck(ck_south2), .rs(rs_26_8), .i(rs_26_8), .o(rs_26_9));
  dsfd_rly_1_WN st_rs_26_9_1 (.ck(ck_south2), .rs(rs_26_8_1), .i(rs_26_8_1), .o(rs_26_9_1));
  dsfd_rly_1_WN st_rs_30_10_2 (.ck(ck_south3), .rs(rs_30_10_1), .i(rs_30_10_1), .o(rs_30_10_2));
  dsfd_rly_1_WN st_rs_33_8 (.ck(ck_south3), .rs(rs_32_8_1), .i(rs_32_8_1), .o(rs_33_8));
  dsfd_rly_1_WN st_rs_33_8_2 (.ck(ck_south3), .rs(rs_33_8_1), .i(rs_33_8_1), .o(rs_33_8_2));
  dsfd_rly_1_WN st_rs_43_5 (.ck(ck_south4), .rs(rs_43_4), .i(rs_43_4), .o(rs_43_5));
  dsfd_rly_1_WN st_rs_49_10 (.ck(ck_south4), .rs(rs_50_10_1), .i(rs_50_10_1), .o(rs_49_10));
  dsfd_rly_1_WN st_rs_25_9_1 (.ck(ck_south2), .rs(rs_25_8_1), .i(rs_25_8_1), .o(rs_25_9_1));
  dsfd_rly_1_WN st_rs_26_10 (.ck(ck_south2), .rs(rs_26_9), .i(rs_26_9), .o(rs_26_10));
  dsfd_rly_1_WN st_rs_26_10_2 (.ck(ck_south2), .rs(rs_26_9_1), .i(rs_26_9_1), .o(rs_26_10_2));
  dsfd_rly_1_WN st_rs_31_10_2 (.ck(ck_south3), .rs(rs_30_10_2), .i(rs_30_10_2), .o(rs_31_10_2));
  dsfd_rly_1_WN st_rs_33_9 (.ck(ck_south3), .rs(rs_33_8), .i(rs_33_8), .o(rs_33_9));
  dsfd_rly_1_WN st_rs_33_9_2 (.ck(ck_south3), .rs(rs_33_8_2), .i(rs_33_8_2), .o(rs_33_9_2));
  dsfd_rly_1_WN st_rs_43_6 (.ck(ck_south4), .rs(rs_43_5), .i(rs_43_5), .o(rs_43_6));
  dsfd_rly_1_WN st_rs_48_10 (.ck(ck_south4), .rs(rs_49_10), .i(rs_49_10), .o(rs_48_10));
  dsfd_rly_1_WN st_rs_25_10_1 (.ck(ck_south2), .rs(rs_25_9_1), .i(rs_25_9_1), .o(rs_25_10_1));
  dsfd_rly_1_WN st_rs_26_11 (.ck(ck_south2), .rs(rs_26_10), .i(rs_26_10), .o(rs_26_11));
  dsfd_rly_1_WN st_rs_26_11_1 (.ck(ck_south2), .rs(rs_26_10_2), .i(rs_26_10_2), .o(rs_26_11_1));
  dsfd_rly_1_WN st_rs_33_10 (.ck(ck_south3), .rs(rs_33_9), .i(rs_33_9), .o(rs_33_10));
  dsfd_rly_1_WN st_rs_33_10_3 (.ck(ck_south3), .rs(rs_33_9_2), .i(rs_33_9_2), .o(rs_33_10_3));
  dsfd_rly_1_WN st_rs_43_7 (.ck(ck_south4), .rs(rs_43_6), .i(rs_43_6), .o(rs_43_7));
  dsfd_rly_1_WN st_rs_47_10 (.ck(ck_south4), .rs(rs_48_10), .i(rs_48_10), .o(rs_47_10));
  dsfd_rly_1_WN st_rs_25_11_1 (.ck(ck_south2), .rs(rs_25_10_1), .i(rs_25_10_1), .o(rs_25_11_1));
  dsfd_rly_1_WN st_rs_26_11_2 (.ck(ck_south2), .rs(rs_26_11_1), .i(rs_26_11_1), .o(rs_26_11_2));
  dsfd_rly_1_WN st_rs_26_12 (.ck(ck_cl2S), .rs(rs_26_11), .i(rs_26_11), .o(rs_26_12));
  dsfd_rly_1_WN st_rs_33_10_1 (.ck(ck_south3), .rs(rs_33_10), .i(rs_33_10), .o(rs_33_10_1));
  dsfd_rly_1_WN st_rs_33_11 (.ck(ck_south3), .rs(rs_33_10_3), .i(rs_33_10_3), .o(rs_33_11));
  dsfd_rly_1_WN st_rs_43_8 (.ck(ck_south4), .rs(rs_43_7), .i(rs_43_7), .o(rs_43_8));
  dsfd_rly_1_WN st_rs_46_10_1 (.ck(ck_south4), .rs(rs_47_10), .i(rs_47_10), .o(rs_46_10_1));
  dsfd_rly_1_WN st_rs_25_12_1 (.ck(ck_cl2S), .rs(rs_25_11_1), .i(rs_25_11_1), .o(rs_25_12_1));
  dsfd_rly_1_WN st_rs_26_12_2 (.ck(ck_cl2S), .rs(rs_26_11_2), .i(rs_26_11_2), .o(rs_26_12_2));
  dsfd_rly_1_WN st_rs_26_13 (.ck(ck_cl2S), .rs(rs_26_12), .i(rs_26_12), .o(rs_26_13));
  dsfd_rly_1_WN st_rs_33_11_2 (.ck(ck_south3), .rs(rs_33_10_1), .i(rs_33_10_1), .o(rs_33_11_2));
  dsfd_rly_1_WN st_rs_33_11_3 (.ck(ck_south3), .rs(rs_33_10_1), .i(rs_33_10_1), .o(rs_33_11_3));
  dsfd_rly_1_WN st_rs_33_12 (.ck(ck_cl3S), .rs(rs_33_11), .i(rs_33_11), .o(rs_33_12));
  dsfd_rly_1_WN st_rs_34_10 (.ck(ck_south3), .rs(rs_33_10_1), .i(rs_33_10_1), .o(rs_34_10));
  dsfd_rly_1_WN st_rs_43_9 (.ck(ck_south4), .rs(rs_43_8), .i(rs_43_8), .o(rs_43_9));
  dsfd_rly_1_WN st_rs_46_11_3 (.ck(ck_south4), .rs(rs_46_10_1), .i(rs_46_10_1), .o(rs_46_11_3));
  dsfd_rly_1_WN st_rs_25_13_1 (.ck(ck_cl2S), .rs(rs_25_12_1), .i(rs_25_12_1), .o(rs_25_13_1));
  dsfd_rly_1_WN st_rs_26_13_2 (.ck(ck_cl2S), .rs(rs_26_12_2), .i(rs_26_12_2), .o(rs_26_13_2));
  dsfd_rly_1_WN st_rs_26_14 (.ck(ck_cl2S), .rs(rs_26_13), .i(rs_26_13), .o(rs_26_14));
  dsfd_rly_1_WN st_rs_33_12_2 (.ck(ck_cl3S), .rs(rs_33_11_2), .i(rs_33_11_2), .o(rs_33_12_2));
  dsfd_rly_1_WN st_rs_43_10 (.ck(ck_south4), .rs(rs_43_9), .i(rs_43_9), .o(rs_43_10));
  dsfd_rly_1_WN st_rs_46_12_3 (.ck(ck_south4), .rs(rs_46_11_3), .i(rs_46_11_3), .o(rs_46_12_3));
  dsfd_rly_1_WN st_rsl_jw_W_l1_32 (.ck(ck_south3), .rs(rs_33_11_3), .i(rs_33_11_3), .o(rsl_jw_W_l1_32));
  dsfd_rly_1_WN st_rsl_q_W_l0_1 (.ck(ck_south3), .rs(rs_34_10), .i(rs_34_10), .o(rsl_q_W_l0_1));
  dsfd_rly_1_WN st_rs_26_14_2 (.ck(ck_cl2S), .rs(rs_26_13_2), .i(rs_26_13_2), .o(rs_26_14_2));
  dsfd_rly_1_WN st_rs_26_15 (.ck(ck_cl2S), .rs(rs_26_14), .i(rs_26_14), .o(rs_26_15));
  dsfd_rly_1_WN st_rs_33_13_2 (.ck(ck_cl3S), .rs(rs_33_12_2), .i(rs_33_12_2), .o(rs_33_13_2));
  dsfd_rly_1_WN st_rs_43_11_1 (.ck(ck_south4), .rs(rs_43_10), .i(rs_43_10), .o(rs_43_11_1));
  dsfd_rly_1_WN st_rsl_jd_W_1 (.ck(ck_south3), .rs(rsl_q_W_l0_1), .i(rsl_q_W_l0_1), .o(rsl_jd_W_1));
  dsfd_rly_1_WN st_rsl_jw_W_l1_31 (.ck(ck_south3), .rs(rsl_jw_W_l1_32), .i(rsl_jw_W_l1_32), .o(rsl_jw_W_l1_31));
  dsfd_rly_1_WN st_rsl_pv_E_1 (.ck(ck_south4), .rs(rs_46_12_3), .i(rs_46_12_3), .o(rsl_pv_E_1));
  dsfd_rly_1_WN st_rs_26_15_2 (.ck(ck_cl2S), .rs(rs_26_14_2), .i(rs_26_14_2), .o(rs_26_15_2));
  dsfd_rly_1_WN st_rs_26_16 (.ck(ck_cl2S), .rs(rs_26_15), .i(rs_26_15), .o(rs_26_16));
  dsfd_rly_1_WN st_rs_33_14_2 (.ck(ck_cl3S), .rs(rs_33_13_2), .i(rs_33_13_2), .o(rs_33_14_2));
  dsfd_rly_1_WN st_rs_34_13_2 (.ck(ck_south3), .rs(rsl_jw_W_l1_31), .i(rsl_jw_W_l1_31), .o(rs_34_13_2));
  dsfd_rly_1_WN st_rs_43_11 (.ck(ck_south4), .rs(rs_43_11_1), .i(rs_43_11_1), .o(rs_43_11));
  dsfd_rly_1_WN st_rs_45_13_1 (.ck(ck_south4), .rs(rsl_pv_E_1), .i(rsl_pv_E_1), .o(rs_45_13_1));
  dsfd_rly_1_WN st_rsl_jd_W_2 (.ck(ck_south3), .rs(rsl_jd_W_1), .i(rsl_jd_W_1), .o(rsl_jd_W_2));
  dsfd_rly_1_WN st_rs_26_16_2 (.ck(ck_cl2S), .rs(rs_26_15_2), .i(rs_26_15_2), .o(rs_26_16_2));
  dsfd_rly_1_WN st_rs_26_17 (.ck(ck_cl2S), .rs(rs_26_16), .i(rs_26_16), .o(rs_26_17));
  dsfd_rly_1_WN st_rs_33_15_2 (.ck(ck_cl3S), .rs(rs_33_14_2), .i(rs_33_14_2), .o(rs_33_15_2));
  dsfd_rly_1_WN st_rs_43_12 (.ck(ck_cl4S), .rs(rs_43_11), .i(rs_43_11), .o(rs_43_12));
  dsfd_rly_1_WN st_rsl_jd_W_3 (.ck(ck_cl3S), .rs(rsl_jd_W_2), .i(rsl_jd_W_2), .o(rsl_jd_W_3));
  dsfd_rly_1_WN st_rs_26_17_2 (.ck(ck_cl2S), .rs(rs_26_16_2), .i(rs_26_16_2), .o(rs_26_17_2));
  dsfd_rly_1_WN st_rs_26_18_1 (.ck(ck_cl2S), .rs(rs_26_17), .i(rs_26_17), .o(rs_26_18_1));
  dsfd_rly_1_WN st_rs_33_16_2 (.ck(ck_cl3S), .rs(rs_33_15_2), .i(rs_33_15_2), .o(rs_33_16_2));
  dsfd_rly_1_WN st_rs_43_13 (.ck(ck_cl4S), .rs(rs_43_12), .i(rs_43_12), .o(rs_43_13));
  dsfd_rly_1_WN st_rsl_jd_W_4 (.ck(ck_cl3S), .rs(rsl_jd_W_3), .i(rsl_jd_W_3), .o(rsl_jd_W_4));
  dsfd_rly_1_WN st_rs_26_18 (.ck(ck_cl2S), .rs(rs_26_17_2), .i(rs_26_17_2), .o(rs_26_18));
  dsfd_rly_1_WN st_rs_26_18_3 (.ck(ck_cl2S), .rs(rs_26_18_1), .i(rs_26_18_1), .o(rs_26_18_3));
  dsfd_rly_1_WN st_rs_33_17_2 (.ck(ck_cl3S), .rs(rs_33_16_2), .i(rs_33_16_2), .o(rs_33_17_2));
  dsfd_rly_1_WN st_rs_43_14 (.ck(ck_cl4S), .rs(rs_43_13), .i(rs_43_13), .o(rs_43_14));
  dsfd_rly_1_WN st_rsl_jd_W_5 (.ck(ck_cl3S), .rs(rsl_jd_W_4), .i(rsl_jd_W_4), .o(rsl_jd_W_5));
  dsfd_rly_1_WN st_rs_26_19_2 (.ck(ck_cl2S), .rs(rs_26_18_3), .i(rs_26_18_3), .o(rs_26_19_2));
  dsfd_rly_1_WN st_rs_27_19_3 (.ck(ck_cl2S), .rs(rs_26_18_3), .i(rs_26_18_3), .o(rs_27_19_3));
  dsfd_rly_1_WN st_rs_33_18 (.ck(ck_cl3S), .rs(rs_33_17_2), .i(rs_33_17_2), .o(rs_33_18));
  dsfd_rly_1_WN st_rs_43_15 (.ck(ck_cl4S), .rs(rs_43_14), .i(rs_43_14), .o(rs_43_15));
  dsfd_rly_1_WN st_rsl_jd_W_6 (.ck(ck_cl3S), .rs(rsl_jd_W_5), .i(rsl_jd_W_5), .o(rsl_jd_W_6));
  dsfd_rly_1_WN st_rsl_xrE_2S_l0_0 (.ck(ck_cl2S), .rs(rs_26_18), .i(rs_26_18), .o(rsl_xrE_2S_l0_0));
  dsfd_rly_1_WN st_rs_27_19_2 (.ck(ck_cl2S), .rs(rs_26_19_2), .i(rs_26_19_2), .o(rs_27_19_2));
  dsfd_rly_1_WN st_rs_32_18_3 (.ck(ck_cl3S), .rs(rs_33_18), .i(rs_33_18), .o(rs_32_18_3));
  dsfd_rly_1_WN st_rs_33_19_2 (.ck(ck_cl3S), .rs(rs_33_18), .i(rs_33_18), .o(rs_33_19_2));
  dsfd_rly_1_WN st_rs_43_16 (.ck(ck_cl4S), .rs(rs_43_15), .i(rs_43_15), .o(rs_43_16));
  dsfd_rly_1_WN st_rsl_jd_W_7 (.ck(ck_cl3S), .rs(rsl_jd_W_6), .i(rsl_jd_W_6), .o(rsl_jd_W_7));
  dsfd_rly_1_WN st_rsl_xrE_2S_l0_1 (.ck(ck_cl2S), .rs(rsl_xrE_2S_l0_0), .i(rsl_xrE_2S_l0_0), .o(rsl_xrE_2S_l0_1));
  dsfd_rly_1_WN st_rs_28_19_1 (.ck(ck_cl2S), .rs(rsl_xrE_2S_l0_1), .i(rsl_xrE_2S_l0_1), .o(rs_28_19_1));
  dsfd_rly_1_WN st_rs_28_19_2 (.ck(ck_cl2S), .rs(rs_27_19_2), .i(rs_27_19_2), .o(rs_28_19_2));
  dsfd_rly_1_WN st_rs_32_19 (.ck(ck_cl3S), .rs(rs_32_18_3), .i(rs_32_18_3), .o(rs_32_19));
  dsfd_rly_1_WN st_rs_32_19_2 (.ck(ck_cl3S), .rs(rs_33_19_2), .i(rs_33_19_2), .o(rs_32_19_2));
  dsfd_rly_1_WN st_rs_43_17 (.ck(ck_cl4S), .rs(rs_43_16), .i(rs_43_16), .o(rs_43_17));
  dsfd_rly_1_WN st_rsl_jd_W_8 (.ck(ck_cl3S), .rs(rsl_jd_W_7), .i(rsl_jd_W_7), .o(rsl_jd_W_8));
  dsfd_rly_1_WN st_rsl_xrE_2S_l0_2 (.ck(ck_cl2S), .rs(rsl_xrE_2S_l0_1), .i(rsl_xrE_2S_l0_1), .o(rsl_xrE_2S_l0_2));
  dsfd_rly_1_WN st_rs_29_19_1 (.ck(ck_cl2S), .rs(rsl_xrE_2S_l0_2), .i(rsl_xrE_2S_l0_2), .o(rs_29_19_1));
  dsfd_rly_1_WN st_rs_29_19_2 (.ck(ck_cl2S), .rs(rs_28_19_2), .i(rs_28_19_2), .o(rs_29_19_2));
  dsfd_rly_1_WN st_rs_31_19_2 (.ck(ck_cl3S), .rs(rs_32_19_2), .i(rs_32_19_2), .o(rs_31_19_2));
  dsfd_rly_1_WN st_rs_43_18_3 (.ck(ck_cl4S), .rs(rs_43_17), .i(rs_43_17), .o(rs_43_18_3));
  dsfd_rly_1_WN st_rsl_jd_W_9 (.ck(ck_cl3S), .rs(rsl_jd_W_8), .i(rsl_jd_W_8), .o(rsl_jd_W_9));
  dsfd_rly_1_WN st_rs_30_19_2 (.ck(ck_cl3S), .rs(rs_31_19_2), .i(rs_31_19_2), .o(rs_30_19_2));
  dsfd_rly_1_WN st_rs_36_19_3 (.ck(ck_cl3S), .rs(rsl_jd_W_9), .i(rsl_jd_W_9), .o(rs_36_19_3));
  dsfd_rly_1_WN st_rs_43_19_2 (.ck(ck_cl4S), .rs(rs_43_18_3), .i(rs_43_18_3), .o(rs_43_19_2));
  dsfd_rly_1_WN st_rsl_jd_W_10 (.ck(ck_cl3S), .rs(rsl_jd_W_9), .i(rsl_jd_W_9), .o(rsl_jd_W_10));
  dsfd_rly_1_WN st_rs_37_19_2 (.ck(ck_cl3S), .rs(rsl_jd_W_10), .i(rsl_jd_W_10), .o(rs_37_19_2));
  dsfd_rly_1_WN st_rs_42_19_2 (.ck(ck_cl4S), .rs(rs_43_19_2), .i(rs_43_19_2), .o(rs_42_19_2));
  dsfd_rly_1_WN st_rsl_jd_W_11 (.ck(ck_cl3S), .rs(rsl_jd_W_10), .i(rsl_jd_W_10), .o(rsl_jd_W_11));
  dsfd_rly_1_WN st_rs_38_19_2 (.ck(ck_cl3S), .rs(rsl_jd_W_11), .i(rsl_jd_W_11), .o(rs_38_19_2));
  dsfd_rly_1_WN st_rs_41_19_2 (.ck(ck_cl4S), .rs(rs_42_19_2), .i(rs_42_19_2), .o(rs_41_19_2));
  dsfd_rly_1_WN st_rsl_jd_W_12 (.ck(ck_cl3S), .rs(rsl_jd_W_11), .i(rsl_jd_W_11), .o(rsl_jd_W_12));
  dsfd_rly_1_WN st_rs_39_19_2 (.ck(ck_cl3S), .rs(rsl_jd_W_12), .i(rsl_jd_W_12), .o(rs_39_19_2));
  dsfd_rly_1_WN st_rs_40_19_2 (.ck(ck_cl4S), .rs(rs_41_19_2), .i(rs_41_19_2), .o(rs_40_19_2));
endmodule

// dv_flight_sim (S81-LBGAP/G1, bench side): F whole periods of lane flight between the last relay station and its
// landing.  The word is delayed F edges of the lane clock and the lane clock reaches the landing F edges late: its first
// edge carries the word of hop-0 gate edge G, as the silicon ck_f edge 0 does (LANDING-CONTRACT L3).
module dv_flight_sim #(parameter integer W = 1, parameter integer F = 0) (
    input  wire ck_in, input wire rs, input wire [W-1:0] i_in, output wire ck_out, output wire [W-1:0] i_out);
    generate if (F == 0) begin : g0
        assign ck_out = ck_in; assign i_out = i_in;
    end else begin : gf
        reg [W-1:0] d [0:F-1];
        reg [31:0] n = 0;
        reg en_l = 1'b0;
        integer k;
        always @(posedge ck_in) begin
            d[0] <= i_in;
            for (k = 1; k < F; k = k + 1) d[k] <= d[k - 1];
        end
        // the flight count starts with the lane clock's first real edge: the time-0 settle of an idle-high (inverted,
        // half-cycle) lane clock is not an edge (rs kept on the port for the record; the wire delay ignores it)
        always @(posedge ck_in)
            if ($time > 0 && n < F) n <= n + 1;
        /* verilator lint_off COMBDLY */
        always_latch if (!ck_in) en_l = (n >= F);
        /* verilator lint_on COMBDLY */
        assign ck_out = ck_in & en_l;
        assign i_out = d[F - 1];
    end endgenerate
endmodule
