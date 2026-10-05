`timescale 1ns/1ps
module ot_probe_lane_bf16 (
    input wire clk, input wire rst_n, input wire clear, input wire accept,
    input wire a_sign, input wire [7:0] a_exp, input wire [7:0] a_man, input wire a_zero,
    input wire [15:0] b, input wire [7:0] scale_exp,
    output wire [39:0] result, output wire dropped);
  ot_mac_lane_fmt #(.W_EXP_BITS(8), .W_FRAC_BITS(7)) u (.*);
endmodule
