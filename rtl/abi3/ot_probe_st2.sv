`timescale 1ns/1ps
// the align barrel shift alone: 16-bit product into a 40-bit window, shift <=16
module ot_probe_st2 (input wire clk, input wire rst_n,
    input wire [15:0] prod, input wire [9:0] rel, input wire sign,
    output reg [39:0] term);
  wire in_win = (rel[9]==1'b0) && (rel <= 10'd16);
  wire [4:0] sh = in_win ? rel[4:0] : 5'd0;
  wire [39:0] mag = in_win ? ({24'b0, prod} << sh) : 40'b0;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) term <= 40'b0; else term <= sign ? ~mag : mag;
endmodule
