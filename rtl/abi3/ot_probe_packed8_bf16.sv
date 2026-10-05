`timescale 1ns/1ps
// As ot_probe_packed4_bf16, at PACK=8: eight BF16 multipliers on one accumulator.
module ot_probe_packed8_bf16 (
    input wire clk, input wire rst_n, input wire clear, input wire accept,
    input wire [127:0] a, input wire [127:0] b, input wire [7:0] scale_exp,
    output wire [39:0] result, output wire dropped);
  ot_mac_lane_packed #(.PACK(8), .W_EXP_BITS(8), .W_FRAC_BITS(7)) u (.*);
endmodule
