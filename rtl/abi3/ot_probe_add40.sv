`timescale 1ns/1ps
// One 40-bit add between registers -- the carry-save resolve.
module ot_probe_add40 (input wire clk, input wire rst_n,
    input wire [39:0] a, input wire [39:0] b, output reg [39:0] y);
  always @(posedge clk or negedge rst_n)
    if (!rst_n) y <= 40'b0; else y <= a + b;
endmodule
