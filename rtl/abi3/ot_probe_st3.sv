`timescale 1ns/1ps
// the carry-save recurring stage alone
module ot_probe_st3 (input wire clk, input wire rst_n,
    input wire [39:0] term, input wire v,
    output reg [39:0] s, output reg [39:0] c);
  wire [39:0] ns = s ^ c ^ term;
  wire [39:0] nc = ((s & c) | (s & term) | (c & term)) << 1;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin s<=40'b0; c<=40'b0; end
    else if (v) begin s<=ns; c<=nc; end
endmodule
