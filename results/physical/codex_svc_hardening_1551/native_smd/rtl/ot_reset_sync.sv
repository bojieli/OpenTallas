`timescale 1ns/1ps
// Asynchronous-assert, synchronous-deassert reset conditioner.  ASYNC_STAGES
// includes the output stage and must be at least two for a CDC/RDC boundary.
module ot_reset_sync #(
    parameter integer ASYNC_STAGES = 2,
    parameter integer OUTPUT_COPIES = 1,
    // TREE 1 (S81-SHLK12 2026-10-20, default 0 = unchanged): with OUTPUT_COPIES > 1 the first stage is itself
    // ceil(OUTPUT_COPIES / 16) kept copies (D = 1), so after the synthesis copy pass no flop of the synchroniser drives
    // more than 16 loads.  Same release edge (still ASYNC_STAGES = 2 edges).
    parameter integer TREE = 0
) (
    input  wire clk,
    input  wire async_rst_n,
    output wire sync_rst_n
);
    (* async_reg = "true" *) reg [ASYNC_STAGES-1:0] reset_pipe;

    always @(posedge clk or negedge async_rst_n) begin
        if (!async_rst_n)
            reset_pipe <= {ASYNC_STAGES{1'b0}};
        else
            reset_pipe <= {reset_pipe[ASYNC_STAGES-2:0],1'b1};
    end

    generate if (OUTPUT_COPIES > 1 && TREE != 0 && ASYNC_STAGES == 2) begin : g_tree
        localparam integer L1 = (OUTPUT_COPIES + 15) / 16;
        (* keep = "true", async_reg = "true" *) reg [L1-1:0] reset_l1__ot_rlv;
        (* keep = "true" *) reg [OUTPUT_COPIES-1:0] reset_regions__ot_rlv;
        always @(posedge clk or negedge async_rst_n)
            if (!async_rst_n) reset_l1__ot_rlv <= '0;
            else reset_l1__ot_rlv <= {L1{1'b1}};
        // every output copy takes the first-stage copy 0 in RTL: both families are identical registers, and the
        // synthesis copy pass (physical/common_flow/ot_rst_copies.tcl) spreads the output copies over the first-stage
        // copies and the reset loads over the output copies (<= OT_RST_COPIES_MAX each)
        always @(posedge clk or negedge async_rst_n)
            if (!async_rst_n) reset_regions__ot_rlv <= '0;
            else reset_regions__ot_rlv <= {OUTPUT_COPIES{reset_l1__ot_rlv[0]}};
        assign sync_rst_n = reset_regions__ot_rlv[0];
    end else if (OUTPUT_COPIES > 1) begin : g_regions
        // Same release edge as reset_pipe's last stage. The canonicalizer
        // proves identical D/clock/reset and partitions reset loads <=256.
        (* keep = "true" *) reg [OUTPUT_COPIES-1:0] reset_regions__ot_rlv;
        always @(posedge clk or negedge async_rst_n)
            if (!async_rst_n) reset_regions__ot_rlv <= '0;
            else reset_regions__ot_rlv <= {OUTPUT_COPIES{reset_pipe[ASYNC_STAGES-2]}};
        assign sync_rst_n = reset_regions__ot_rlv[0];
    end else begin : g_original
        assign sync_rst_n = reset_pipe[ASYNC_STAGES-1];
    end endgenerate

`ifndef SYNTHESIS
    initial begin
        if (ASYNC_STAGES < 2)
            $error("ot_reset_sync requires at least two stages");
    end
`endif
endmodule
