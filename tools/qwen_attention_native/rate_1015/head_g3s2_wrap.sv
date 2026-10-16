`timescale 1ns/1ps
// KV/system die v1.4.3 G3S2 head as the die wires it, for the attention-stack composition bench: the native r4 head
// (protected library ot_qkh_head_native_r4_8) behind 3 ingress register stages (G, T1, T2 = qkh_head_gather_stage /
// qkh_head_tstage on the full t word + e) and 2 score return stages (S1, S2 = qkh_head_sstage). Common-phase clock.
module qattn_head_g3s2 (
 input wire [3:0] ck_front,input wire ck_score,ck_kt,input wire [15:0] ck_stin,ck_stk,ck_nb1,ck_nb2,ck_lane,
 input wire rst_n,input wire [3:0] c_in,input wire [1023:0] row_in,input wire [15:0] e_in,input wire [11:0] lt_in,
 input wire [1:0] hid,input wire q_valid_in,input wire [5:0] q_beat_in,input wire [511:0] q_data_in,
 output wire [31:0] sc_d,output wire sc_f,g_f,output wire [1023:0] nb_d);
 wire [1558:0] t0={c_in,row_in,lt_in,q_valid_in,q_beat_in,q_data_in},t1,t2,t3;wire [15:0] e1,e2,e3;
 qkh_head_gather_stage u_g(.ck(ck_kt),.ti_a(t0),.e_a(e_in),.ti_b(t1),.e_b(e1));
 qkh_head_tstage u_t1(.ck(ck_kt),.ti_a(t1),.e_a(e1),.ti_b(t2),.e_b(e2));
 qkh_head_tstage u_t2(.ck(ck_kt),.ti_a(t2),.e_a(e2),.ti_b(t3),.e_b(e3));
 wire [31:0] hs;wire hf,hg;
 ot_qkh_head_native_r4_8 u_r4(.ck_front(ck_front),.ck_score(ck_score),.ck_kt(ck_kt),.ck_stin(ck_stin),.ck_stk(ck_stk),
  .ck_nb1(ck_nb1),.ck_nb2(ck_nb2),.ck_lane(ck_lane),.rst_n(rst_n),.c_in(t3[1558:1555]),.row_in(t3[1554:531]),.e_in(e3),
  .lt_in(t3[530:519]),.hid(hid),.q_valid_in(t3[518]),.q_beat_in(t3[517:512]),.q_data_in(t3[511:0]),
  .sc_d(hs),.sc_f(hf),.g_f(hg),.nb_d(nb_d));
 wire [33:0] s1;
 qkh_head_sstage u_s1(.ck(ck_score),.s_a({hs,hf,hg}),.s_b(s1));
 qkh_head_sstage u_s2(.ck(ck_score),.s_a(s1),.s_b({sc_d,sc_f,g_f}));
endmodule
