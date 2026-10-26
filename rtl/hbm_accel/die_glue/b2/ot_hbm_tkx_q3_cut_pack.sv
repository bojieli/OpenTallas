`timescale 1ns/1ps
`default_nettype none
// Logical wires only; no new physical partition, registers, clock or tied pins.
module ot_hbm_tkx_q3_cut_pack(
 input wire[511:0] u_body_g_qout_0_g3_w_o_u_out_u_dst_d,
 input wire[15:0] u_body_g_qout_0_g3_w_o_u_out_u_dst_v,
 input wire[511:0] u_body_g_qout_10_g3_w_o_u_out_u_dst_d,
 input wire[511:0] u_body_g_qout_11_g3_w_o_u_out_u_dst_d,
 input wire[511:0] u_body_g_qout_12_g3_w_o_u_out_u_dst_d,
 input wire[511:0] u_body_g_qout_13_g3_w_o_u_out_u_dst_d,
 input wire[511:0] u_body_g_qout_14_g3_w_o_u_out_u_dst_d,
 input wire[511:0] u_body_g_qout_15_g3_w_o_u_out_u_dst_d,
 input wire[383:0] u_body_g_qout_16_g3_w_o_u_out_u_dst_d,
 input wire[11:0] u_body_g_qout_17_g3_n_o_u_out_u_dst_d,
 input wire[511:0] u_body_g_qout_1_g3_w_o_u_out_u_dst_d,
 input wire[511:0] u_body_g_qout_2_g3_w_o_u_out_u_dst_d,
 input wire[511:0] u_body_g_qout_3_g3_w_o_u_out_u_dst_d,
 input wire[511:0] u_body_g_qout_4_g3_w_o_u_out_u_dst_d,
 input wire[511:0] u_body_g_qout_5_g3_w_o_u_out_u_dst_d,
 input wire[511:0] u_body_g_qout_6_g3_w_o_u_out_u_dst_d,
 input wire[511:0] u_body_g_qout_7_g3_w_o_u_out_u_dst_d,
 input wire[511:0] u_body_g_qout_8_g3_w_o_u_out_u_dst_d,
 input wire[511:0] u_body_g_qout_9_g3_w_o_u_out_u_dst_d,
 input wire[74:0] u_body_u_upipe_SL_7_u_d3,
 input wire[95:0] u_body_u_upipe_SL_8_u_d3,
 input wire[9:0] u_body_u_upipe_SL_9_u_d3,
 output wire[2340:0]raw
);
 assign raw[0+:1]=u_body_u_upipe_SL_7_u_d3[16+:1];
 assign raw[1+:7]=u_body_u_upipe_SL_7_u_d3[68+:7];
 assign raw[8+:9]=u_body_u_upipe_SL_8_u_d3[0+:9];
 assign raw[17+:1]=u_body_u_upipe_SL_9_u_d3[9+:1];
 assign raw[18+:13]=u_body_u_upipe_SL_7_u_d3[42+:13];
 assign raw[31+:12]=u_body_u_upipe_SL_7_u_d3[30+:12];
 assign raw[43+:13]=u_body_u_upipe_SL_7_u_d3[55+:13];
 assign raw[56+:40]=u_body_u_upipe_SL_8_u_d3[25+:40];
 assign raw[96+:16]=u_body_u_upipe_SL_8_u_d3[9+:16];
 assign raw[112+:31]=u_body_u_upipe_SL_8_u_d3[65+:31];
 assign raw[143+:9]=u_body_u_upipe_SL_9_u_d3[0+:9];
 assign raw[152+:32]=u_body_g_qout_0_g3_w_o_u_out_u_dst_d[352+:32];
 assign raw[184+:32]=u_body_g_qout_1_g3_w_o_u_out_u_dst_d[352+:32];
 assign raw[216+:32]=u_body_g_qout_2_g3_w_o_u_out_u_dst_d[352+:32];
 assign raw[248+:32]=u_body_g_qout_3_g3_w_o_u_out_u_dst_d[352+:32];
 assign raw[280+:32]=u_body_g_qout_4_g3_w_o_u_out_u_dst_d[352+:32];
 assign raw[312+:32]=u_body_g_qout_5_g3_w_o_u_out_u_dst_d[352+:32];
 assign raw[344+:32]=u_body_g_qout_6_g3_w_o_u_out_u_dst_d[352+:32];
 assign raw[376+:32]=u_body_g_qout_7_g3_w_o_u_out_u_dst_d[352+:32];
 assign raw[408+:32]=u_body_g_qout_8_g3_w_o_u_out_u_dst_d[352+:32];
 assign raw[440+:32]=u_body_g_qout_9_g3_w_o_u_out_u_dst_d[352+:32];
 assign raw[472+:32]=u_body_g_qout_10_g3_w_o_u_out_u_dst_d[352+:32];
 assign raw[504+:32]=u_body_g_qout_11_g3_w_o_u_out_u_dst_d[352+:32];
 assign raw[536+:32]=u_body_g_qout_12_g3_w_o_u_out_u_dst_d[352+:32];
 assign raw[568+:32]=u_body_g_qout_13_g3_w_o_u_out_u_dst_d[352+:32];
 assign raw[600+:32]=u_body_g_qout_14_g3_w_o_u_out_u_dst_d[352+:32];
 assign raw[632+:32]=u_body_g_qout_15_g3_w_o_u_out_u_dst_d[352+:32];
 assign raw[664+:32]=u_body_g_qout_16_g3_w_o_u_out_u_dst_d[224+:32];
 assign raw[696+:1]=u_body_g_qout_17_g3_n_o_u_out_u_dst_d[7+:1];
 assign raw[697+:32]=u_body_g_qout_0_g3_w_o_u_out_u_dst_d[384+:32];
 assign raw[729+:32]=u_body_g_qout_1_g3_w_o_u_out_u_dst_d[384+:32];
 assign raw[761+:32]=u_body_g_qout_2_g3_w_o_u_out_u_dst_d[384+:32];
 assign raw[793+:32]=u_body_g_qout_3_g3_w_o_u_out_u_dst_d[384+:32];
 assign raw[825+:32]=u_body_g_qout_4_g3_w_o_u_out_u_dst_d[384+:32];
 assign raw[857+:32]=u_body_g_qout_5_g3_w_o_u_out_u_dst_d[384+:32];
 assign raw[889+:32]=u_body_g_qout_6_g3_w_o_u_out_u_dst_d[384+:32];
 assign raw[921+:32]=u_body_g_qout_7_g3_w_o_u_out_u_dst_d[384+:32];
 assign raw[953+:32]=u_body_g_qout_8_g3_w_o_u_out_u_dst_d[384+:32];
 assign raw[985+:32]=u_body_g_qout_9_g3_w_o_u_out_u_dst_d[384+:32];
 assign raw[1017+:32]=u_body_g_qout_10_g3_w_o_u_out_u_dst_d[384+:32];
 assign raw[1049+:32]=u_body_g_qout_11_g3_w_o_u_out_u_dst_d[384+:32];
 assign raw[1081+:32]=u_body_g_qout_12_g3_w_o_u_out_u_dst_d[384+:32];
 assign raw[1113+:32]=u_body_g_qout_13_g3_w_o_u_out_u_dst_d[384+:32];
 assign raw[1145+:32]=u_body_g_qout_14_g3_w_o_u_out_u_dst_d[384+:32];
 assign raw[1177+:32]=u_body_g_qout_15_g3_w_o_u_out_u_dst_d[384+:32];
 assign raw[1209+:32]=u_body_g_qout_16_g3_w_o_u_out_u_dst_d[256+:32];
 assign raw[1241+:1]=u_body_g_qout_17_g3_n_o_u_out_u_dst_d[8+:1];
 assign raw[1242+:32]=u_body_g_qout_0_g3_w_o_u_out_u_dst_d[416+:32];
 assign raw[1274+:32]=u_body_g_qout_1_g3_w_o_u_out_u_dst_d[416+:32];
 assign raw[1306+:32]=u_body_g_qout_2_g3_w_o_u_out_u_dst_d[416+:32];
 assign raw[1338+:32]=u_body_g_qout_3_g3_w_o_u_out_u_dst_d[416+:32];
 assign raw[1370+:32]=u_body_g_qout_4_g3_w_o_u_out_u_dst_d[416+:32];
 assign raw[1402+:32]=u_body_g_qout_5_g3_w_o_u_out_u_dst_d[416+:32];
 assign raw[1434+:32]=u_body_g_qout_6_g3_w_o_u_out_u_dst_d[416+:32];
 assign raw[1466+:32]=u_body_g_qout_7_g3_w_o_u_out_u_dst_d[416+:32];
 assign raw[1498+:32]=u_body_g_qout_8_g3_w_o_u_out_u_dst_d[416+:32];
 assign raw[1530+:32]=u_body_g_qout_9_g3_w_o_u_out_u_dst_d[416+:32];
 assign raw[1562+:32]=u_body_g_qout_10_g3_w_o_u_out_u_dst_d[416+:32];
 assign raw[1594+:32]=u_body_g_qout_11_g3_w_o_u_out_u_dst_d[416+:32];
 assign raw[1626+:32]=u_body_g_qout_12_g3_w_o_u_out_u_dst_d[416+:32];
 assign raw[1658+:32]=u_body_g_qout_13_g3_w_o_u_out_u_dst_d[416+:32];
 assign raw[1690+:32]=u_body_g_qout_14_g3_w_o_u_out_u_dst_d[416+:32];
 assign raw[1722+:32]=u_body_g_qout_15_g3_w_o_u_out_u_dst_d[416+:32];
 assign raw[1754+:32]=u_body_g_qout_16_g3_w_o_u_out_u_dst_d[288+:32];
 assign raw[1786+:1]=u_body_g_qout_17_g3_n_o_u_out_u_dst_d[9+:1];
 assign raw[1787+:32]=u_body_g_qout_0_g3_w_o_u_out_u_dst_d[448+:32];
 assign raw[1819+:32]=u_body_g_qout_1_g3_w_o_u_out_u_dst_d[448+:32];
 assign raw[1851+:32]=u_body_g_qout_2_g3_w_o_u_out_u_dst_d[448+:32];
 assign raw[1883+:32]=u_body_g_qout_3_g3_w_o_u_out_u_dst_d[448+:32];
 assign raw[1915+:32]=u_body_g_qout_4_g3_w_o_u_out_u_dst_d[448+:32];
 assign raw[1947+:32]=u_body_g_qout_5_g3_w_o_u_out_u_dst_d[448+:32];
 assign raw[1979+:32]=u_body_g_qout_6_g3_w_o_u_out_u_dst_d[448+:32];
 assign raw[2011+:32]=u_body_g_qout_7_g3_w_o_u_out_u_dst_d[448+:32];
 assign raw[2043+:32]=u_body_g_qout_8_g3_w_o_u_out_u_dst_d[448+:32];
 assign raw[2075+:32]=u_body_g_qout_9_g3_w_o_u_out_u_dst_d[448+:32];
 assign raw[2107+:32]=u_body_g_qout_10_g3_w_o_u_out_u_dst_d[448+:32];
 assign raw[2139+:32]=u_body_g_qout_11_g3_w_o_u_out_u_dst_d[448+:32];
 assign raw[2171+:32]=u_body_g_qout_12_g3_w_o_u_out_u_dst_d[448+:32];
 assign raw[2203+:32]=u_body_g_qout_13_g3_w_o_u_out_u_dst_d[448+:32];
 assign raw[2235+:32]=u_body_g_qout_14_g3_w_o_u_out_u_dst_d[448+:32];
 assign raw[2267+:32]=u_body_g_qout_15_g3_w_o_u_out_u_dst_d[448+:32];
 assign raw[2299+:32]=u_body_g_qout_16_g3_w_o_u_out_u_dst_d[320+:32];
 assign raw[2331+:1]=u_body_g_qout_17_g3_n_o_u_out_u_dst_d[10+:1];
 assign raw[2332+:4]=u_body_u_upipe_SL_7_u_d3[26+:4];
 assign raw[2336+:4]=u_body_g_qout_0_g3_w_o_u_out_u_dst_v[11+:4];
 assign raw[2340+:1]=u_body_u_upipe_SL_7_u_d3[25+:1];
endmodule
`default_nettype wire
