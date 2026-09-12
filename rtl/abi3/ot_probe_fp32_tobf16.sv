`timescale 1ns/1ps
module ot_probe_fp32_tobf16 (
    input wire clk, input wire rst_n,
    input wire [31:0] a,
    output reg [18:0] y
);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) y <= 19'b0;
        else y <= ot_fp32_rne_pkg::fp32_to_bf16_rne(a);
endmodule
