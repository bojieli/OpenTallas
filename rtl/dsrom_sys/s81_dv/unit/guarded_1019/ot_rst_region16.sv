// PRIVATE OPT-IN GRAPH: never selected by public main defaults.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-GUNIT whole model (2026-10-19): ot_gunit_guarded_1019_ot_rst_region16 -- regional reset ownership with 16 kept region roots.
// The raw rst_n port drives ONLY the two synchronizer flops (2 raw async-clear contacts; ot_rst_relay #(4) had 6).
// Each region root q[k] is asynchronously cleared from sync_q[0] (assertion: raw -> sync_q[0] clear->Q -> q[k] clear)
// and takes D = sync_q[1], so release is the 3rd rising clk edge after the port deasserts -- the same release edge as
// ot_rst_relay #(SYNC_STAGES 2, TREE_STAGES 1).  Every consumer resets from one region root; the owner keeps each root
// at <= 24 async-clear pins.  Assertion now traverses a real flop clear->Q arc: minimum pulse width, recovery/removal
// of sync_q[0] -> q[k] and assertion propagation are physical checks (STA recovery/removal), not RTL claims.
// Fixed width (no parameters) so the module name survives synthesis unchanged; region roots are kept registers.
// ---------------------------------------------------------------------------------------------------------------------
(* keep_hierarchy = 1 *) module ot_gunit_guarded_1019_ot_rst_region16 (
    input  wire        clk,
    input  wire        rst_n_in,
    output wire [15:0] rst_n
);
    (* async_reg = "true" *) reg [1:0] sync_q;
    always @(posedge clk or negedge rst_n_in)
        if (!rst_n_in) sync_q <= 2'b00;
        else           sync_q <= {sync_q[0], 1'b1};
    genvar k;
    generate for (k = 0; k < 16; k = k + 1) begin : g_region
        (* keep = "true", dont_touch = "true" *) reg q;
        always @(posedge clk or negedge sync_q[0])
            if (!sync_q[0]) q <= 1'b0;
            else            q <= sync_q[1];
        assign rst_n[k] = q;
    end endgenerate
endmodule
