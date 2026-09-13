`timescale 1ns/1ps
module ot_probe_mac_fp32_pipe (
    input wire clk, input wire rst_n, input wire iv,
    input wire [15:0] a, input wire [15:0] b, input wire [31:0] c,
    output wire [31:0] y, output wire [1:0] err, output wire ov);
  ot_mac_bf16_fp32_pipe u (.clk(clk), .rst_n(rst_n), .valid_in(iv),
                           .a(a), .b(b), .c(c), .y(y), .err(err), .valid_out(ov));
endmodule
