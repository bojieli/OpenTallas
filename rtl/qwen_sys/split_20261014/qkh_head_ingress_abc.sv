`timescale 1ns/1ps
// Producer-local fixed-latency captures. No valid/ready/credit and no reset.
// Each physical master has its own die-delivered phi-R clock and exact pins.
// Native physical views/homes are REQUIRED before adoption; this is real RTL.
module qkh_head_chunk_stage #(parameter integer W=512)
 (input wire ck,input wire [W-1:0] a,output reg [W-1:0] b);
 always @(posedge ck) b<=a;
endmodule

module qkh_head_ingress_abc #(parameter integer MUT=0)
 (input wire ck_a,ck_b,ck_c,input wire [1558:0] ti_a,input wire [15:0] e_a,
  output wire [1558:0] ti_b,output wire [15:0] e_b);
 wire [534:0] ar;
 wire [534:0] bc;
 wire [534:0] cq;
 // One physical535-bit master reused3times; A23/B7 explicit padding bits are
 // still actual hardened flops. Only those pad outputs are discarded.
 // A: lower512 row bits. B: c4 + upper512 row + lt12. C: epoch16 + q519.
 qkh_head_chunk_stage #(.W(535)) u_a(.ck(ck_a),.a({23'b0,ti_a[1042:531]}),.b(ar));
 qkh_head_chunk_stage #(.W(535)) u_b(.ck(ck_b),.a({7'b0,ti_a[1558:1043],ti_a[530:519]}),.b(bc));
 qkh_head_chunk_stage #(.W(535)) u_c(.ck(ck_c),.a({e_a,ti_a[518:0]}),.b(cq));
 assign ti_b[1558:1555]=bc[527:524];
 assign ti_b[1554:1043]=(MUT==31)?ar[511:0]:bc[523:12];
 assign ti_b[1042:531]=(MUT==31)?bc[523:12]:ar[511:0];
 assign ti_b[530:519]=(MUT==32)?ti_a[530:519]:bc[11:0];
 assign ti_b[518:0]=cq[518:0];
 assign e_b=(MUT==33)?e_a:cq[534:519];
endmodule

// Actual N3 assembly: ABC captures + existingT1/T2 + unchanged rawR4 + S1.
// Compiler issue+3, score+1, total+4/layer; cost is UNMEASURED until fullcomposition.
module ot_qkh_head_native_r4_staged_n3 #(
  parameter integer Q_FP32=1, parameter integer MUT=0
)(input wire [3:0] ck_front,input wire ck_score,ck_kt,
  input wire [15:0] ck_stin,ck_stk,ck_nb1,ck_nb2,ck_lane,input wire ck_t1,ck_t2,ck_s1,ck_a,ck_b,ck_c,
  input wire rst_n,input wire [3:0] c_in,input wire [1023:0] row_in,
  input wire [15:0] e_in,input wire [11:0] lt_in,input wire [1:0] hid,
  input wire q_valid_in,input wire [5:0] q_beat_in,input wire [511:0] q_data_in,
  output wire [31:0] sc_d,output wire sc_f,g_f,output wire [1023:0] nb_d);
  wire [1558:0] ti0 = {c_in,row_in,lt_in,q_valid_in,q_beat_in,q_data_in};
  wire [1558:0] ti0c;
  wire [15:0] e0c;
  qkh_head_ingress_abc #(.MUT(MUT)) u_ingress(.ck_a(ck_a),.ck_b(ck_b),.ck_c(ck_c),
    .ti_a(ti0),.e_a(e_in),.ti_b(ti0c),.e_b(e0c));
  wire [1558:0] ti1, ti2; wire [15:0] e1, e2;
  qkh_head_tstage u_t1 (.ck(ck_t1),.ti_a(ti0c),.e_a(e0c),.ti_b(ti1),.e_b(e1));
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
