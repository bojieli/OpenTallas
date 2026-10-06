`timescale 1ns/1ps
// One complete 16-key quarter at the real production scorer port. This is a
// wiring join to the unchanged W11 engine, not a score/calendar stand-in.
// Query codes/scales/weights must come from the actual producer. Its clock is
// literal clk, shared with the gather; no QX gated-clock relation is invented.
// Caller retains gather fault/debt and handles sc_fault/protocol_fault closed.
// Causal masking stays in the existing golden mdrop AFTER native scoring.
// Model: dsrom_reindex_parent_model.native_quarter_join_model(), prebuild.
module ot_dsrom_reindex_native_quarter #(parameter bit ENABLE=0) (
    input wire clk, rst_n,
    input wire ql_v,
    output wire ql_ready,
    input wire [7:0] ql_head,
    input wire [511:0] ql_codes,
    input wire [31:0] ql_sc,
    input wire [15:0] ql_w,
    input wire ks_valid,
    output wire ks_ready,
    input wire ks_last,
    input wire [15:0] ks_lv, ks_ref,
    input wire [8703:0] ks_key,
    input wire [319:0] ks_idx,
    output wire sc_valid,
    input wire sc_ready,
    output wire sc_last,
    output wire [3:0] sc_last_slices,
    output wire [15:0] sc_lv, sc_fault,
    output wire [255:0] sc_val,
    output wire [319:0] sc_idx,
    output wire protocol_fault
);
    generate if (!ENABLE) begin : disabled
        assign ql_ready=0;
        assign ks_ready=0;
        assign sc_valid=0;
        assign sc_last_slices=0;
        assign sc_lv=0;
        assign sc_fault=0;
        assign sc_val=0;
        assign sc_idx=0;
        assign protocol_fault=0;
    end else begin : enabled
        // The gather's lanes are consecutive within each group of four.
        // Keep every full global ID; do not regenerate a quarter-local ID.
        ot_hdc_v41x_idx_array_l #(
            .NS(4),.NK(4),.NB(4),.IH(32),.IW(20),.MD(64),
            .FPL(7),.FML(5),.QL(5)
        ) u_score (
            .clk(clk),.rst_n(rst_n),
            .ql_v(ql_v),.ql_ready(ql_ready),.ql_head(ql_head),
            .ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),
            .i_valid(ks_valid),.i_ready(ks_ready),
            .i_last({4{ks_last}}),.i_kv(ks_lv),.i_ref(ks_ref),
            .i_keep(ks_lv),.i_index(ks_idx),.i_key(ks_key),
            .o_valid(sc_valid),.o_ready(sc_ready),.o_last(sc_last_slices),
            .o_kv(sc_lv),.o_fault(sc_fault),.o_score(sc_val),.o_index(sc_idx),
            .protocol_fault(protocol_fault)
        );
    end endgenerate
    assign sc_last=sc_last_slices[0];
endmodule
