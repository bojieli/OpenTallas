`default_nettype none
// HBM-IDXSQ8 2026-10-20: the W glue one-root top at the die's TP = 192 (rank 8 b), non-parameterised so the landed-parent
// generator (tools/landed_parent/lp.py) and the hard-child flow see fixed port widths. Same logic as ot_hbm_idx_score_qw_r4s.
module ot_hbm_idx_score_qw_tp192(
 input wire clk,input wire rst_n,input wire half,
 input wire[7:0]rank,input wire[10:0]first_ord,input wire[11:0]nkeys,
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
 ot_hbm_idx_score_qw_r4s #(.TP(192)) u(.clk(clk),.rst_n(rst_n),.half(half),.rank(rank),.first_ord(first_ord),
  .nkeys(nkeys),.keep_en(keep_en),.keep_bitmap(keep_bitmap),.ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),
  .ql_w(ql_w),.beat_v(beat_v),.beat_index(beat_index),.key_lines0(key_lines0),.key_lines1(key_lines1),.rst_c0(rst_c0),
  .rst_c1(rst_c1),.o_qv0(o_qv0),.o_q0(o_q0),.o_kv0(o_kv0),.o_kkv0(o_kkv0),.o_key0(o_key0),.o_aux0(o_aux0),.o_bus0(o_bus0),
  .o_qv1(o_qv1),.o_q1(o_q1),.o_kv1(o_kv1),.o_kkv1(o_kkv1),.o_key1(o_key1),.o_aux1(o_aux1),.o_bus1(o_bus1));
endmodule
`default_nettype wire
