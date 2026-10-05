`timescale 1ns/1ps
// stage 2 as it ACTUALLY is in the assembled MAC: exponent subtract, window
// compare, barrel shift, sign XOR -- all between two registers.
module ot_probe_st2b (input wire clk, input wire rst_n,
    input wire [15:0] prod, input wire [9:0] s1_exp, input wire [7:0] scale_exp,
    input wire sign, output reg [39:0] term);
  wire [9:0] rel = s1_exp - {2'b0, scale_exp};
  wire in_win = (rel[9]==1'b0) && (rel <= 10'd16);
  wire [4:0] sh = in_win ? rel[4:0] : 5'd0;
  wire [39:0] mag = in_win ? ({24'b0, prod} << sh) : 40'b0;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) term <= 40'b0; else term <= sign ? ~mag : mag;
endmodule
