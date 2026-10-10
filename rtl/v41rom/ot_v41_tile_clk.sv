`timescale 1ns/1ps
// ot_v41_tile_clk (bf-arch 2026-10-09): one clock-gated tile ("island") of an element built on ot_v41_rom_elem_qx_w10 QZE.
// It holds a LOCAL copy of the element's registered gate enable (ze, a kreg loaded with the same next-state ze_d, same
// asynchronous reset to 1 from the reset pin) driving a LOCAL integrated clock gate, and a LOCAL copy of the element's
// reset synchroniser (asynchronous assert from the reset pin, synchronous release, as g_mz.u_rs).  Every copy is the same
// register function of the same inputs as the element's own ze / reset synchroniser, so the tile clock has exactly the
// element clock's edges and the tile reset releases on exactly the element reset's edge: a tile is a clock / reset
// NETWORK change only (exact by construction).  Physically the enable register sits beside its gate and both sit low
// in the clock tree (the gate drives one small tile instead of the whole element), so the enable path is short and the
// gate's clock pin is late (the root-level gate of the single-gate element gave the enable only ~250 ps: the gate CLK at
// ~250 ps against an enable launched from a ~775 ps leaf), and the reset recovery path is local to the tile.
module ot_v41_tile_clk (
    input  wire fclk,       // free-running element clock
    input  wire rst_pin,    // the element's reset pin (asynchronous, active low)
    input  wire ze_d,       // the element's registered-gate-enable next state (ot_v41_rom_elem_qx_w10 QZE ze_d)
    output wire gclk,       // tile gated clock (= the element's gclk, edge for edge)
    output wire rst_n       // tile reset (= the element's reset synchroniser output, edge for edge)
);
    wire ze_q;
    ot_v41_kreg #(.W(1), .AR(1), .RV(1'b1)) u_ze (.clk(fclk), .arst_n(rst_pin), .d(ze_d), .q(ze_q));
    ot_hdc_cg u_cg (.clk(fclk), .en(ze_q), .gclk(gclk));
    ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_rs (.clk(fclk), .arst_n(rst_pin), .d(1'b1), .q(rst_n));
endmodule
