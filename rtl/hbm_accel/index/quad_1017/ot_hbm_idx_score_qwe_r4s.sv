`default_nettype none
// L2H-IDXSCORE 2026-10-19: ONE-ROOT tile tops of the r4 W / E glue (ot_hbm_idx_score_quarter_wo2.sv), for the parallel
// single-root variants: both row clocks are the one tile clock clk, centre-fed at the row seam. r4a/b/c two-root gates:
// row 0 roots 22-56 ps but every row-1 root 88-287 ps (row-1 domain sinks placed across the seam). Same logic and cycles as
// the two-root tiles (the r4 lockstep drives both row clocks from one clock).
module ot_hbm_idx_score_qw_r4s #(parameter integer TP=96,RANK_W=(TP<=1?1:$clog2(TP)))(
 input wire clk,input wire rst_n,input wire half,
 input wire[RANK_W-1:0]rank,input wire[10:0]first_ord,input wire[11:0]nkeys,
 input wire keep_en,input wire[170:0]keep_bitmap,
 input wire ql_v,input wire[7:0]ql_head,input wire[511:0]ql_codes,input wire[31:0]ql_sc,input wire[15:0]ql_w,
 input wire beat_v,input wire[7:0]beat_index,
 input wire[2197:0]key_lines0,input wire[2197:0]key_lines1,
 output wire rst_c0,output wire rst_c1,
 output wire o_qv0,output wire[567:0]o_q0,output wire o_kv0,
 output wire[3:0]o_kkv0,output wire[2175:0]o_key0,output wire[29:0]o_aux0,
 output wire[551:0]o_bus0,
 output wire o_qv1,output wire[567:0]o_q1,output wire o_kv1,
 output wire[3:0]o_kkv1,output wire[2175:0]o_key1,output wire[29:0]o_aux1,
 output wire[551:0]o_bus1
);
 ot_hbm_idx_score_qw_r4 #(.TP(TP)) u(.clk_w0(clk),.clk_w1(clk),.rst_n(rst_n),.half(half),.rank(rank),.first_ord(first_ord),
  .nkeys(nkeys),.keep_en(keep_en),.keep_bitmap(keep_bitmap),.ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),
  .ql_w(ql_w),.beat_v(beat_v),.beat_index(beat_index),.key_lines0(key_lines0),.key_lines1(key_lines1),.rst_c0(rst_c0),
  .rst_c1(rst_c1),.o_qv0(o_qv0),.o_q0(o_q0),.o_kv0(o_kv0),.o_kkv0(o_kkv0),.o_key0(o_key0),.o_aux0(o_aux0),.o_bus0(o_bus0),
  .o_qv1(o_qv1),.o_q1(o_q1),.o_kv1(o_kv1),.o_kkv1(o_kkv1),.o_key1(o_key1),.o_aux1(o_aux1),.o_bus1(o_bus1));
endmodule

module ot_hbm_idx_score_qe_r4s(
 input wire clk,input wire rst_n,
 input wire r0_qv,input wire r0_kv,input wire[29:0]r0_aux,input wire[551:0]r0_bus,
 input wire r1_qv,input wire r1_kv,input wire[29:0]r1_aux,input wire[551:0]r1_bus,
 output wire[153:0]score0,output wire[151:0]score1,output wire fault
);
 ot_hbm_idx_score_qe_r4 u(.clk_e0(clk),.clk_e1(clk),.rst_n(rst_n),.r0_qv(r0_qv),.r0_kv(r0_kv),.r0_aux(r0_aux),.r0_bus(r0_bus),
  .r1_qv(r1_qv),.r1_kv(r1_kv),.r1_aux(r1_aux),.r1_bus(r1_bus),.score0(score0),.score1(score1),.fault(fault));
endmodule
`default_nettype wire
