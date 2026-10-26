`timescale 1ns/1ps
module ot_qwen_rst_rep #(
    parameter integer PAD = 0,
    parameter integer MUT = 0
) (
    input  wire clk,
    input  wire d,
    output wire q0,
    output wire q1
);
    reg [PAD:0] s;                               // s[0] = input flop, s[PAD:1] = pad flops
    (* keep = "true", dont_touch = "true" *) reg r0;
    (* keep = "true", dont_touch = "true" *) reg r1;
    integer i;
    always @(posedge clk) begin
        s[0] <= d;
        for (i = 1; i <= PAD; i = i + 1) s[i] <= s[i - 1];
        r0 <= s[PAD];
        r1 <= (MUT == 1) ? ((PAD == 0) ? d : s[PAD - 1]) : s[PAD];
    end
    assign q0 = r0;
    assign q1 = r1;
endmodule
