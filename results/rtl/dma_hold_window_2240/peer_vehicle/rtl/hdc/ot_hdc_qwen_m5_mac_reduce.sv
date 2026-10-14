`timescale 1ns/1ps
// O4 five-slot arithmetic datapath behind one matrix issue/ROM controller.
// The controller supplies the decoded shared BF16 weight word and one operand
// per slot/group, with first/last K tags. Five MAC streams enter five parallel
// split trees and post-sum BF16 row-scale multipliers. Five reduction paths
// are required to retire short-K results at the modeled weight-sweep rate.
module ot_hdc_qwen_m5_mac_reduce #(
    parameter integer G = 4, W = 16, IL = 8
) (
    input  wire clk, rst_n, valid, first, last_k,
    input  wire [$clog2(G):0] split_log2,
    input  wire [G*W*32-1:0] weight_fp32,
    input  wire [5*G*32-1:0] activation_fp32,
    input  wire [G*W*16-1:0] row_scale_bf16,
    output wire out_valid,
    output wire [5*G*W*32-1:0] result,
    output wire fault
);
    wire [5*G*W*32-1:0] partial;
    wire partial_valid, mac_fault, reduce_fault;
    ot_hdc_qwen_m5_mac_array #(.G(G), .W(W), .IL(IL)) u_mac (
        .clk(clk), .rst_n(rst_n), .v(valid), .first(first), .last_k(last_k),
        .weight_fp32(weight_fp32), .activation_fp32(activation_fp32),
        .partial_sum(partial), .sum_valid(partial_valid), .fault(mac_fault));
    ot_hdc_qwen_m5_reduce_scale #(.G(G), .W(W)) u_reduce (
        .clk(clk), .rst_n(rst_n), .valid(partial_valid), .split_log2(split_log2),
        .partial_sum(partial), .row_scale_bf16(row_scale_bf16),
        .out_valid(out_valid), .result(result), .fault(reduce_fault));
    assign fault = mac_fault || reduce_fault;
endmodule
