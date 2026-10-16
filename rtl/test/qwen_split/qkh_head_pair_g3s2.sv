`timescale 1ns/1ps
// kvsys v1.4.3 G3S2 composition (bench view, KV die lead 2026-10-15): one ECTL head pair exactly as the die wires it.
//   ingress  ECTL t word + e -> G (gather) -> T1 -> T2 -> head      (+3 edges; both heads)
//   score    head {sc_d, sc_f, g_f} -> S1 -> S2 -> ECTL             (+2 edges; both heads)
// The FAR head's T1 and S2 are the NEAR head frame's feed-through leaves (ot_qkh_head_native_r4_ft u_ftg / u_fts).
// MUT 31: far T1 bypassed (far ingress +2), MUT 32: far S2 bypassed, MUT 33: near T2 bypassed -- each must FAIL.
module qkh_head_pair_g3s2 #(parameter integer MUT=0)(
  input wire clk,rst_n,input wire [1:0] hid,hid_f,
  input wire [3:0] c_in,input wire [1023:0] row_in,input wire [11:0] lt_in,input wire q_valid_in,
  input wire [5:0] q_beat_in,input wire [511:0] q_data_in,input wire [15:0] e_in,e_f,
  output wire [31:0] sc_d,output wire sc_f,g_f,output wire [1023:0] nb_d,      // near head (port names = r4's)
  output wire [33:0] s_f,output wire [1023:0] nb_f);                           // far head
  wire [33:0] s_n; wire [1023:0] nb_n; wire [1:0] hid_n=hid; wire [15:0] e_n=e_in;
  assign {sc_d,sc_f,g_f}=s_n; assign nb_d=nb_n;
  wire [1558:0] ti = {c_in,row_in,lt_in,q_valid_in,q_beat_in,q_data_in};
  wire [1558:0] gn,t1n,t2n,gf,t1f,t2f; wire [15:0] egn,e1n,e2n,egf,e1f,e2f;
  qkh_head_gather_stage u_gn (.ck(clk),.ti_a(ti),.e_a(e_n),.ti_b(gn),.e_b(egn));
  qkh_head_gather_stage u_t1n(.ck(clk),.ti_a(gn),.e_a(egn),.ti_b(t1n),.e_b(e1n));
  qkh_head_gather_stage u_t2n(.ck(clk),.ti_a(t1n),.e_a(e1n),.ti_b(t2n),.e_b(e2n));
  qkh_head_gather_stage u_gf (.ck(clk),.ti_a(ti),.e_a(e_f),.ti_b(gf),.e_b(egf));
  wire [1558:0] t1f_n; wire [15:0] e1f_n; wire [33:0] sh_n,sh_f,s1n,s1f,s2f_n;
  qkh_head_gather_stage u_t2f(.ck(clk),.ti_a(MUT==31 ? gf : t1f_n),.e_a(MUT==31 ? egf : e1f_n),.ti_b(t2f),.e_b(e2f));
  wire [1558:0] hn = (MUT==33) ? t1n : t2n; wire [15:0] hen = (MUT==33) ? e1n : e2n;
  ot_qkh_head_native_r4_ft #(.Q_FP32(1)) u_near
    (.ck_front({4{clk}}),.ck_score(clk),.ck_kt(clk),.ck_stin({16{clk}}),.ck_stk({16{clk}}),
     .ck_nb1({16{clk}}),.ck_nb2({16{clk}}),.ck_lane({16{clk}}),.rst_n(rst_n),
     .c_in(hn[1558:1555]),.row_in(hn[1554:531]),.e_in(hen),.lt_in(hn[530:519]),.hid(hid_n),
     .q_valid_in(hn[518]),.q_beat_in(hn[517:512]),.q_data_in(hn[511:0]),
     .sc_d(sh_n[33:2]),.sc_f(sh_n[1]),.g_f(sh_n[0]),.nb_d(nb_n),
     .ck_ft_t(clk),.ck_ft_s(clk),.ft_ti_a(gf),.ft_e_a(egf),.ft_ti_b(t1f_n),.ft_e_b(e1f_n),.ft_s_a(s1f),.ft_s_b(s2f_n));
  ot_qkh_head_native_r4 #(.Q_FP32(1)) u_far
    (.ck_front({4{clk}}),.ck_score(clk),.ck_kt(clk),.ck_stin({16{clk}}),.ck_stk({16{clk}}),
     .ck_nb1({16{clk}}),.ck_nb2({16{clk}}),.ck_lane({16{clk}}),.rst_n(rst_n),
     .c_in(t2f[1558:1555]),.row_in(t2f[1554:531]),.e_in(e2f),.lt_in(t2f[530:519]),.hid(hid_f),
     .q_valid_in(t2f[518]),.q_beat_in(t2f[517:512]),.q_data_in(t2f[511:0]),
     .sc_d(sh_f[33:2]),.sc_f(sh_f[1]),.g_f(sh_f[0]),.nb_d(nb_f));
  wire [33:0] s2n;
  qkh_head_sstage u_s1n(.ck(clk),.s_a(sh_n),.s_b(s1n));
  qkh_head_sstage u_s2n(.ck(clk),.s_a(s1n),.s_b(s2n));
  qkh_head_sstage u_s1f(.ck(clk),.s_a(sh_f),.s_b(s1f));
  assign s_n = s2n;
  assign s_f = (MUT==32) ? s1f : s2f_n;
endmodule
