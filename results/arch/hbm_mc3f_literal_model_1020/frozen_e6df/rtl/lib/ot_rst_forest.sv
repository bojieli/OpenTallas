`timescale 1ns/1ps
// Registered reset FOREST: every reset net drives <= ~32 loads (HBM-MC3 2026-10-19, SAFE-DESIGN checklist items 2 + 3).
//
// Why: ot_rst_relay clears all REGIONS relay flops asynchronously from its input and feeds them from ONE synchroniser
// flop, so on hdie_pc_ctrl_bw_face_p540 (94 regions) the reset landing flop drove 96 async clears over 413 um, the
// synchroniser drove 94 D pins, and every region copy drove 50..237 reset pins (native census bw_p540_v6: 202 drivers
// > 32 endpoints, ~190 of them reset).
//
// Structure (all plain same-clock D flops, KEPT; the input is already a registered face landing stage):
//   rst_n_in -> s0 (1 flop) -> l1_q[FIRST] (s0 drives FIRST D pins) -> l2_q[LEAVES] (every l2 D pin from l1_q[0] in
//   RTL) = rst_n.
// The l1_q and l2_q copies are logically identical registers, so they form two copy FAMILIES for the synthesis pass
// physical/common_flow/ot_rst_copies.tcl (spec "reset_relay_split", re "(^|\.)u_rst\.(l1_q|l2_q)$"): after flatten it
// proves the copies identical and re-points (a) the LEAVES l2 D pins over the FIRST l1 copies (<= ceil(LEAVES/FIRST)
// each) and (b) every reset load of the block over the LEAVES l2 copies, sorted by hierarchical name, so each leaf
// serves one name-local group (a bank, a metadata slice, a ring slice) and placement puts it there.  Re-pointing a load
// between identical registers cannot change the function; RTL simulation of this module is the post-pass function.
//
// Timing contract: release reaches rst_n 3 rising edges after rst_n_in rises (s0, l1, l2) -- the same 3 edges as
// ot_rst_relay #(SYNC_STAGES 2, TREE_STAGES 1), so a top that swaps the relay for the forest keeps its composed reset
// release fixed point.  Assertion is also 3 edges (synchronous; the clock runs during reset, as for every face landing).
module ot_rst_forest #(
    parameter integer LEAVES = 192,
    parameter integer FIRST  = 8
) (
    input  wire              clk,
    input  wire              rst_n_in,
    output wire [LEAVES-1:0] rst_n
);
    (* keep = "true", dont_touch = "true" *) reg s0;
    (* keep = "true", dont_touch = "true" *) reg [FIRST-1:0]  l1_q;
    (* keep = "true", dont_touch = "true" *) reg [LEAVES-1:0] l2_q;
    always @(posedge clk) begin
        s0   <= rst_n_in;
        l1_q <= {FIRST{s0}};
        l2_q <= {LEAVES{l1_q[0]}};
    end
    assign rst_n = l2_q;
`ifndef SYNTHESIS
    initial begin
        if (FIRST < 1 || FIRST > 32) $error("ot_rst_forest: FIRST must be 1..32 (s0 drives FIRST loads)");
        if (LEAVES < FIRST || (LEAVES + FIRST - 1) / FIRST > 32)
            $error("ot_rst_forest: LEAVES/FIRST must be <= 32 (each l1 copy drives that many l2 D pins)");
    end
`endif
endmodule
