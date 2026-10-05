`timescale 1ns/1ps
module ot_probe_tile4 (
    input wire clk, input wire rst_n, input wire clear, input wire valid_in,
    input wire [15:0] act, input wire [16*4-1:0] wgt, input wire [7:0] scale_exp,
    output wire [40*4-1:0] result, output wire [4-1:0] dropped_mask,
    output wire result_valid);
  ot_mac_tile #(.LANES(4)) u (.*);
endmodule
