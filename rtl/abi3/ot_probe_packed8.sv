`timescale 1ns/1ps
module ot_probe_packed8 (
    input wire clk, input wire rst_n, input wire clear, input wire accept,
    input wire [127:0] a, input wire [31:0] b, input wire [7:0] scale_exp,
    output wire [39:0] result, output wire dropped);
  ot_mac_lane_packed #(.PACK(8), .W_EXP_BITS(2), .W_FRAC_BITS(1)) u (.*);
endmodule
