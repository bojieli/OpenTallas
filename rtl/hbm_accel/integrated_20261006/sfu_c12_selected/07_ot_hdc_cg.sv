// Integration-only c12 namespace export. Canonical source: rtl/hdc/ot_hdc_cg.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hbm_selected_c12__ot_hdc_cg: integrated clock gate for unit-level clock gating.
//
// Not instantiated by any block.  Gating of the as-built decode-core blocks was
// withdrawn on 2026-09-26 when the core was re-specified top-down; it is to be
// re-applied to the final blocks.  With it the Qwen and V4.1 decode campaigns
// stayed bit-exact and cycle-identical, and the routed V4.1 units closed with
// tools/run_abi3_physical.py --clock-gating except the activation quantiser,
// whose s0 -> s1 max tree missed 0.9 ns by 14-47 ps across two routes (the cause
// was not attributed before the stop; it was NOT the input-register enable).
//
// Function: gclk follows clk while en was high at the clock's last low phase,
// and stays low otherwise, so a gated register sees exactly the rising edges
// at which en was 1 -- the same edges at which an enabled register would load.
// Synthesis maps it onto the platform's latch-based ICG cell; the model below
// is that cell's function (a latch transparent while clk is low, ANDed with
// clk), so simulation clocks the gated registers exactly as the cell will.
// The instance keeps the name u_icg: tools/signoff_analysis.py annotates the
// cell's ENA pin from this module's `en`.  Every user must OR !rst_n into
// `en`: the reset is asynchronous in silicon, but a simulator that starts with
// rst_n already low sees no negedge and applies it only on clock edges, so the
// gated registers must be clocked during reset.
// ---------------------------------------------------------------------------
module ot_hbm_selected_c12__ot_hdc_cg (
    input  wire clk,
    input  wire en /*verilator clock_enable*/,
    output wire gclk
);
`ifdef SYNTHESIS
    ICGx1_ASAP7_75t_R u_icg (.CLK(clk), .ENA(en), .SE(1'b0), .GCLK(gclk));
`else
    reg en_l;
    /* verilator lint_off COMBDLY */
    always_latch if (!clk) en_l = en;   // transparent while clk is low
    /* verilator lint_on COMBDLY */
    assign gclk = clk & en_l;
`endif
endmodule
