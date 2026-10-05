`timescale 1ns/1ps
// Caller-side finite W2 mapper. No column/issue RTL is instantiated or changed.
// Composite issue shape: rows=4, groups=2, c=8, FP4. Keep virtual row and
// row-mod-8 slot in the existing column tag; restore local identity at output.
// ISSUE descriptor = the currently issuing pair; RESULT descriptor = oldest
// outstanding pair at the *pin* rv event. They MUST NOT share a mutable head.
// Caller holds each descriptor until all four actual pin results have arrived.
// xb delta is compiler-provided and verified, never an allocator or guessed row.
// Feed issue_xa_out into the caller's existing s1 x-address capture; no new edge.
module ot_hbm_accel_w2_tag16_map #(
    parameter integer ENABLE = 0,
    parameter integer RW = 12
) (
    input wire issue_v,
    input wire issue_row_ok,
    input wire [RW:0] issue_virtual_row,
    input wire [6:0] issue_xa_absolute,
    input wire issue_pair_bound,
    input wire [6:0] issue_xb_a,
    input wire [6:0] issue_xb_b,
    input wire [6:0] issue_delta_x,
    output wire [6:0] issue_xa_out,
    output wire issue_fault,
    input wire rsp_v,
    input wire [RW-1:0] rsp_virtual_row,
    input wire result_pair_bound,
    input wire [31:0] result_op_a,
    input wire [31:0] result_op_b,
    output wire out_v,
    output wire [RW-1:0] out_local_row,
    output wire [31:0] out_operation,
    output wire out_segment,
    output wire out_a_last,
    output wire out_pair_last,
    output wire result_fault
);
    generate if (ENABLE == 0) begin : g_off
        assign issue_xa_out = issue_xa_absolute;
        assign issue_fault = 1'b0;
        assign out_v = rsp_v;
        assign out_local_row = rsp_virtual_row;
        assign out_operation = result_op_a;
        assign out_segment = 1'b0;
        assign out_a_last = 1'b0;
        assign out_pair_last = 1'b0;
        assign result_fault = 1'b0;
    end else begin : g_w2
        wire issue_b = issue_virtual_row >= 2;
        wire [6:0] expected_delta = issue_xb_b - issue_xb_a;
        wire issue_bound = issue_pair_bound && issue_virtual_row < 4 &&
                           issue_delta_x == expected_delta;
        wire [6:0] translated = issue_xa_absolute + issue_delta_x;
        assign issue_xa_out = issue_b ? translated : issue_xa_absolute;
        assign issue_fault = issue_v && issue_row_ok && !issue_bound;
        wire result_bound = result_pair_bound && rsp_virtual_row < 4;
        wire segment_b = rsp_virtual_row >= 2;
        assign result_fault = rsp_v && !result_bound;
        assign out_v = rsp_v && result_bound;
        assign out_local_row = segment_b ? rsp_virtual_row - 2 : rsp_virtual_row;
        assign out_operation = segment_b ? result_op_b : result_op_a;
        assign out_segment = segment_b;
        assign out_a_last = out_v && rsp_virtual_row == 1;
        assign out_pair_last = out_v && rsp_virtual_row == 3;
    end endgenerate
endmodule
