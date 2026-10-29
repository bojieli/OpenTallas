`timescale 1ns/1ps
`default_nettype none
// No inferrednewmath: nativeHCOL atfixedHALF, samecurrentMUT/DELIVERED_RESET.
module ot_hbm_idx_score_hcol_h0 #(parameter integer MUT=0,DELIVERED_RESET=1)(
 input wire [1:0] clk_pair,
 input wire rst_col,
 input wire qv_b,
 input wire [567:0] q_b,
 input wire [543:0] key,
 input wire [31:0] hid4,
 output wire [31:0] cs_out,
 output wire cf_out,
 output wire [1:0] prdy
);
 ot_hidx_score_hcol #(.HALF(0),.MUT(MUT),.DELIVERED_RESET(DELIVERED_RESET)) u_native (
.clk_pair(clk_pair),
.rst_col(rst_col),
.qv_b(qv_b),
.q_b(q_b),
.key(key),
.hid4(hid4),
.cs_in(32'd0),
.cf_in(1'b0),
.cs_out(cs_out),
.cf_out(cf_out),
.prdy(prdy)
 );
endmodule
module ot_hbm_idx_score_hcol_h1 #(parameter integer MUT=0,DELIVERED_RESET=1)(
 input wire [1:0] clk_pair,
 input wire rst_col,
 input wire qv_b,
 input wire [567:0] q_b,
 input wire [543:0] key,
 input wire [31:0] hid4,
 input wire [31:0] cs_in,
 input wire cf_in,
 output wire [31:0] cs_out,
 output wire cf_out,
 output wire [1:0] prdy
);
 ot_hidx_score_hcol #(.HALF(1),.MUT(MUT),.DELIVERED_RESET(DELIVERED_RESET)) u_native (
.clk_pair(clk_pair),
.rst_col(rst_col),
.qv_b(qv_b),
.q_b(q_b),
.key(key),
.hid4(hid4),
.cs_in(cs_in),
.cf_in(cf_in),
.cs_out(cs_out),
.cf_out(cf_out),
.prdy(prdy)
 );
endmodule
`default_nettype wire
