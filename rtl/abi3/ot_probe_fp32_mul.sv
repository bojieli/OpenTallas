`timescale 1ns/1ps
module ot_probe_fp32_mul (
    input wire clk, input wire rst_n,
    input wire [31:0] a, input wire [31:0] b,
    output reg [33:0] y
);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) y <= 34'b0;
        else y <= ot_fp32_rne_pkg::fp32_mul_rne(a, b);
endmodule
