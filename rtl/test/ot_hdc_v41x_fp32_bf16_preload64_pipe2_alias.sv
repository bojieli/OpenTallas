`timescale 1ns/1ps
// Bench-only pin-compatible alias.  The physical pipeline is the pipe2 module;
// this keeps the checkpoint ME harness source unchanged for an isolated swap.
module ot_hdc_v41x_fp32_bf16_preload64 #(
    parameter integer EW=13,
    parameter integer PW=2
) (
    input wire clk,rst_n,in_v,
    input wire [PW-1:0] in_p,
    input wire [EW-1:0] in_e,
    input wire [2047:0] in_d,
    output wire out_v,
    output wire [PW-1:0] out_p,
    output wire [EW-1:0] out_e,
    output wire [1023:0] out_d,
    output wire out_fault,out_saturated
);
    ot_hdc_v41x_fp32_bf16_preload64_pipe2 #(.EW(EW),.PW(PW)) u_pipe (.*);
endmodule
