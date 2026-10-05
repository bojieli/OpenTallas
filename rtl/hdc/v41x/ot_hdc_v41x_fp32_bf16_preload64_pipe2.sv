`timescale 1ns/1ps
// Two-stage 64-lane converter for a registered four-bank VM neighbour.
// Stage 1 decides RNE increment from the low FP32 half. Stage 2 increments,
// saturates and canonicalizes +0. It has two-cycle fill, one beat/cycle issue.
module ot_hdc_v41x_fp32_bf16_preload64_pipe2 #(
    parameter integer EW=13,
    parameter integer PW=2
) (
    input wire clk,
    input wire rst_n,
    input wire in_v,
    input wire [PW-1:0] in_p,
    input wire [EW-1:0] in_e,
    input wire [2047:0] in_d,
    output reg out_v,
    output reg [PW-1:0] out_p,
    output reg [EW-1:0] out_e,
    output reg [1023:0] out_d,
    output reg out_fault,
    output reg out_saturated
);
    reg v1;
    reg [PW-1:0] p1;
    reg [EW-1:0] e1;
    reg [1023:0] hi1;
    reg [63:0] inc1, nonfinite1;
    wire [15:0] value2 [0:63];
    wire [63:0] sat2;
    genvar i;
    generate for (i=0;i<64;i=i+1) begin : g_cv
        wire [15:0] hi=hi1[i*16 +:16];
        wire [15:0] rounded=hi+{15'b0,inc1[i]};
        assign sat2[i]=!nonfinite1[i] && rounded[14:7]==8'hff;
        wire [15:0] candidate=sat2[i] ? {hi[15],8'hfe,7'h7f} : rounded;
        assign value2[i]=nonfinite1[i] ? 16'b0 :
                         ((candidate[14:0]==0) ? 16'b0 : candidate);
    end endgenerate
    integer j;
    always @(posedge clk) begin
        if (!rst_n) begin
            v1<=0; p1<='0; e1<='0; hi1<='0; inc1<='0; nonfinite1<='0;
            out_v<=0; out_p<='0; out_e<='0; out_d<='0;
            out_fault<=0; out_saturated<=0;
        end else begin
            v1<=in_v; p1<=in_p; e1<=in_e;
            for (j=0;j<64;j=j+1) begin
                hi1[j*16 +:16]<=in_d[j*32+16 +:16];
                inc1[j]<=(in_d[j*32 +:16]>16'h8000) ||
                         ((in_d[j*32 +:16]==16'h8000) && in_d[j*32+16]);
                nonfinite1[j]<=in_d[j*32+23 +:8]==8'hff;
                out_d[j*16 +:16]<=value2[j];
            end
            out_v<=v1; out_p<=p1; out_e<=e1;
            out_fault<=v1 && (|nonfinite1);
            out_saturated<=v1 && (|sat2);
        end
    end
endmodule
