`timescale 1ns/1ps
// One 8-bit add between registers: a realistic floor for any datapath stage.
module ot_probe_add8 (input wire clk, input wire rst_n,
    input wire [7:0] a, input wire [7:0] b, output reg [8:0] y);
  always @(posedge clk or negedge rst_n)
    if (!rst_n) y <= 9'b0; else y <= {1'b0,a} + {1'b0,b};
endmodule
