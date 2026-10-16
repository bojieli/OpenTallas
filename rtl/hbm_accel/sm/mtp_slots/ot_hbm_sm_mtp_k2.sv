`timescale 1ns/1ps
// Diagnostic native P6/K2 compute vehicle, not yet bound into the production SM.
// Two actual production block-dot sets share one weight word; each set owns
// 3 query positions x 8 interleaved output rows = 24 accumulator contexts.
// All issue cycles are assigned by the compiler/test programme. No handshake.
module ot_hbm_sm_mtp_k2 #(parameter integer MUT_SLOT_ALIAS=0)(
 input wire clk,rst_n,iv,first,last,fp4,
 input wire [15:0] tag0,tag1,
 input wire [531:0] weight,x0,x1,
 output wire [1:0] ov,fault,
 output wire [63:0] result,
 output wire [31:0] otag
);
 wire [531:0] x1_native = MUT_SLOT_ALIAS ? x0 : x1;
 ot_hbm_accel_smh_bdc #(.IL(24)) u_set0(.clk(clk),.rst_a(rst_n),.i_v(iv),.i_first(first),.i_last(last),
  .i_fp4(fp4),.i_tag(tag0),.i_w(weight),.i_x(x0),.ov(ov[0]),.y(result[31:0]),.otag(otag[15:0]),.fault(fault[0]));
 ot_hbm_accel_smh_bdc #(.IL(24)) u_set1(.clk(clk),.rst_a(rst_n),.i_v(iv),.i_first(first),.i_last(last),
  .i_fp4(fp4),.i_tag(tag1),.i_w(weight),.i_x(x1_native),.ov(ov[1]),.y(result[63:32]),.otag(otag[31:16]),.fault(fault[1]));
endmodule
