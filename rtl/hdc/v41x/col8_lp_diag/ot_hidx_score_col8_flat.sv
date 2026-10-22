`timescale 1ns/1ps
`default_nettype none
// DIAGNOSTIC-ONLY (START-NONFAIL/HBM-PAR1/SQ 10-21): wires-only flat form of ot_hidx_score_col8 (rtl/hdc/v41x/ot_hbm_idx_score_col8.sv)
// for tools/landed_parent/lp.py.  Identical pair wiring (query N broadcast, key S broadcast, head ids, W->E running-sum
// chain r0 -> r1 -> r2 -> r3); the col8 two-flop face synchroniser is NOT here: lp.py lands rst_n per region instead
// (each pair8 keeps its own 2-stage pair-local synchroniser).  Geometry / pin / clock-entry evidence for the col8 parent
// on the CLOSED interim pair8 views; never bindable, never a schedule reference.
module ot_hidx_score_col8_flat(input wire clk,rst_n,qv_b,input wire [567:0] q_b,
 input wire [543:0] key,input wire [63:0] hid,output wire [31:0] cs_out,
 output wire cf_out,output wire prdy0,prdy1,prdy2,prdy3);  // col8 prdy[3:0] split per pair (lp: one driver region per port)
 wire [31:0] cs1,cs2,cs3; wire cf1,cf2,cf3;
 ot_hidx_score_pair8_r0 u_pair0(.clk(clk),.rst_n(rst_n),.qv_b(qv_b),.q_b(q_b),.key(key),
  .hid(hid[0+:16]),.cs_out(cs1),.cf_out(cf1),.prdy(prdy0));
 ot_hidx_score_pair8_r1 u_pair1(.clk(clk),.rst_n(rst_n),.qv_b(qv_b),.q_b(q_b),.key(key),
  .hid(hid[16+:16]),.cs_in(cs1),.cf_in(cf1),.cs_out(cs2),.cf_out(cf2),.prdy(prdy1));
 ot_hidx_score_pair8_r2 u_pair2(.clk(clk),.rst_n(rst_n),.qv_b(qv_b),.q_b(q_b),.key(key),
  .hid(hid[32+:16]),.cs_in(cs2),.cf_in(cf2),.cs_out(cs3),.cf_out(cf3),.prdy(prdy2));
 ot_hidx_score_pair8_r3 u_pair3(.clk(clk),.rst_n(rst_n),.qv_b(qv_b),.q_b(q_b),.key(key),
  .hid(hid[48+:16]),.cs_in(cs3),.cf_in(cf3),.cs_out(cs_out),.cf_out(cf_out),.prdy(prdy3));
endmodule
`default_nettype wire
