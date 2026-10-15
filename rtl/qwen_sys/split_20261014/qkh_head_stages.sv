`timescale 1ns/1ps
// KV/system die v1.4 head stages (kvsys lead r7 2026-10-15 07:02, contract compiler_stages.head_stages):
// ECTL -> head t word (c/row/lt/q_valid/q_beat/q_data) + e word: N = 2 registered stages, one registered copy PER HEAD
// (stage 1 at the ECTL C face replaces the 1-flop -> 8-front-leaf fan-out over ~1 mm; stage 2 mid-way, hops <= ~350 um);
// head score word {sc_d, sc_f, g_f} -> ECTL: M = 1 stage.  Static schedule (owner 10-14): pure pipeline registers, no
// valid/ready/credit; lt rides in the SAME stage as q (no lt/q race).  No reset (a relay flushes while the endpoints are
// held in reset, as qkd_rly_*); the compiler adds +2 to every ECTL->head issue and +1 to the score return (+3/layer).
// ti bit order = die bus ti {c_in[3:0], row_in[1023:0], lt_in[11:0], q_valid_in, q_beat_in[5:0], q_data_in[511:0]}.
module qkh_head_tstage (
  input  wire          ck,
  input  wire [1558:0] ti_a,
  input  wire [15:0]   e_a,
  output reg  [1558:0] ti_b,
  output reg  [15:0]   e_b);
  always @(posedge ck) begin
    ti_b <= ti_a;
    e_b  <= e_a;
  end
endmodule

module qkh_head_sstage (
  input  wire        ck,
  input  wire [33:0] s_a,     // {sc_d[31:0], sc_f, g_f}
  output reg  [33:0] s_b);
  always @(posedge ck) s_b <= s_a;
endmodule

// Bench / composition view: the native r4 head behind 2 t/e stages and 1 score stage, as the die wires it.
// MUT 21: lt rides only ONE stage (lt/q race) -- must fail; MUT 22: score stage missing -- must fail against +3.
module ot_qkh_head_native_r4_staged #(
  parameter integer Q_FP32=1, parameter integer MUT=0
)(input wire [3:0] ck_front,input wire ck_score,ck_kt,
  input wire [15:0] ck_stin,ck_stk,ck_nb1,ck_nb2,ck_lane,input wire ck_t1,ck_t2,ck_s1,
  input wire rst_n,input wire [3:0] c_in,input wire [1023:0] row_in,
  input wire [15:0] e_in,input wire [11:0] lt_in,input wire [1:0] hid,
  input wire q_valid_in,input wire [5:0] q_beat_in,input wire [511:0] q_data_in,
  output wire [31:0] sc_d,output wire sc_f,g_f,output wire [1023:0] nb_d);
  wire [1558:0] ti0 = {c_in,row_in,lt_in,q_valid_in,q_beat_in,q_data_in};
  wire [1558:0] ti1, ti2; wire [15:0] e1, e2;
  qkh_head_tstage u_t1 (.ck(ck_t1),.ti_a(ti0),.e_a(e_in),.ti_b(ti1),.e_b(e1));
  qkh_head_tstage u_t2 (.ck(ck_t2),.ti_a(ti1),.e_a(e1),.ti_b(ti2),.e_b(e2));
  wire [11:0] lt_h = (MUT==21) ? ti1[530:519] : ti2[530:519];
  wire [33:0] s_h, s_o;
  ot_qkh_head_native_r4 #(.Q_FP32(Q_FP32),.MUT(MUT>=20 ? 0 : MUT)) u_head
    (.ck_front(ck_front),.ck_score(ck_score),.ck_kt(ck_kt),.ck_stin(ck_stin),.ck_stk(ck_stk),
     .ck_nb1(ck_nb1),.ck_nb2(ck_nb2),.ck_lane(ck_lane),.rst_n(rst_n),
     .c_in(ti2[1558:1555]),.row_in(ti2[1554:531]),.e_in(e2),.lt_in(lt_h),.hid(hid),
     .q_valid_in(ti2[518]),.q_beat_in(ti2[517:512]),.q_data_in(ti2[511:0]),
     .sc_d(s_h[33:2]),.sc_f(s_h[1]),.g_f(s_h[0]),.nb_d(nb_d));
  qkh_head_sstage u_s1 (.ck(ck_s1),.s_a(s_h),.s_b(s_o));
  assign {sc_d,sc_f,g_f} = (MUT==22) ? s_h : s_o;
endmodule
