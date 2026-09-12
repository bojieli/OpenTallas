`timescale 1ns/1ps
module ot_probe_bf16_add_pipe (
    input wire clk, input wire rst_n, input wire iv,
    input wire [15:0] l, input wire [15:0] r,
    output wire ov, output wire [15:0] q, output wire sat, output wire [1:0] err);
  ot_bf16_add_pipe u (.clk(clk), .rst_n(rst_n), .in_valid(iv),
    .left_code(l), .right_code(r), .out_valid(ov),
    .result_code(q), .result_saturated(sat), .result_error(err));
endmodule
