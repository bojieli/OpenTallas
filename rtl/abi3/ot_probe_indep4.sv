`timescale 1ns/1ps
module ot_probe_indep4 (
    input wire clk, input wire rst_n, input wire clear,
    input wire [3:0] v, input wire [63:0] a, input wire [63:0] b,
    input wire [31:0] se, output wire [159:0] r, output wire [3:0] rv);
  genvar i;
  generate for (i=0;i<4;i=i+1) begin : c
    ot_mac_bf16_csa_pipe u (.clk(clk), .rst_n(rst_n), .clear(clear),
      .valid_in(v[i]), .a(a[16*i +: 16]), .b(b[16*i +: 16]),
      .scale_exp(se[8*i +: 8]), .result(r[40*i +: 40]), .acc_valid(rv[i]));
  end endgenerate
endmodule
