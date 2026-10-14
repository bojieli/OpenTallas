`timescale 1ns/1ps
// Shared issue and weight bus for five speculative slots. Each group carries
// five MAC-only ot_hdc_lane_copy instances. In a core integration slot 0 may
// reuse the base matvec lanes and slots 1..4 are the four additions. The caller owns
// the common weight fetch, K-split reduction, post-sum scale and result tags.
// This module is the copy-lane structure priced by the O4 ledger; it does not
// replicate matrix issue control or ROM ports.
module ot_hdc_qwen_m5_mac_array #(
    parameter integer G = 4, W = 16, IL = 8
) (
    input  wire clk, rst_n, v, first, last_k,
    input  wire [G*W*32-1:0] weight_fp32,
    input  wire [5*G*32-1:0] activation_fp32,
    output wire [5*G*W*32-1:0] partial_sum,
    output wire sum_valid,
    output wire fault
);
    wire [12:0] last_pipe;
    ot_hdc_vline #(.D(12)) u_last_tag (
        .clk(clk), .rst_n(rst_n), .v(v && last_k), .vd(last_pipe));
    assign sum_valid = last_pipe[12];
    wire [5*G-1:0] fault_w;
    genvar s, g;
    generate for (s = 0; s < 5; s = s + 1) begin : g_slot
        for (g = 0; g < G; g = g + 1) begin : g_group
            ot_hdc_lane_copy #(.W(W), .IL(IL)) u_mac (
                .clk(clk), .rst_n(rst_n), .v(v), .first(first),
                .w(weight_fp32[g*W*32 +: W*32]),
                .x(activation_fp32[(s*G+g)*32 +: 32]),
                .sum_q(partial_sum[(s*G+g)*W*32 +: W*32]),
                .fault(fault_w[s*G+g])
            );
        end
    end endgenerate
    assign fault = |fault_w;
endmodule
