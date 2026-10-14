`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Functional (simulation-only) models of the S81 die's link PHY hard macros (s81-functional-token 2026-10-14, die item
// F10).  The die netlist instantiates ot_pdie_serdes (x6) and ot_pdie_ucie (x2) as pin-only black boxes {clk, tx[511:0],
// rx[511:0]} (physical/asap7_v41x_pdie_macros_v2/*_bb.v): the DIGITAL link layer (framing, CRC, credits, go-back-N,
// gearbox) is real RTL inside the collective slab (ot_s81ph_link_ep / ot_s81ph_link_gbx / ot_dsrom_link_chan); only the
// analog PHY is modelled here, as a fixed-latency lane: what enters tx on this die leaves rx of the PEER die LAT clk
// edges later.  The black box has no off-die (bump) port, so the model exposes the line as pd_o / pd_i ports that a
// multi-die testbench connects die to die (`define OT_PDIE_FM_PADS); without it, rx is driven from a hierarchical peer
// set by the testbench (pd_i tied 0 = an unconnected link: rx idle).
// Same module names as the black boxes: compile this file INSTEAD of the _bb.v for a functional die run.
// ---------------------------------------------------------------------------------------------------------------------
module ot_pdie_fm_lane #(parameter integer W = 512, parameter integer LAT = 8) (
    input  wire         clk,
    input  wire [W-1:0] tx,
    output wire [W-1:0] rx,
    output wire [W-1:0] pd_o,
    input  wire [W-1:0] pd_i
);
    reg [W-1:0] q [0:LAT-1];
    integer i;
    always @(posedge clk) begin
        q[0] <= pd_i;
        for (i = 1; i < LAT; i = i + 1) q[i] <= q[i - 1];
    end
    assign rx = q[LAT - 1];
    assign pd_o = tx;
endmodule

module ot_pdie_serdes (
    input  wire         clk,
    input  wire [511:0] tx,
    output wire [511:0] rx
`ifdef OT_PDIE_FM_PADS
  , output wire [511:0] pd_o,
    input  wire [511:0] pd_i
`endif
);
`ifndef OT_PDIE_FM_PADS
    wire [511:0] pd_o, pd_i;
    assign pd_i = 512'd0;
`endif
    ot_pdie_fm_lane #(.W(512), .LAT(`ifdef OT_PDIE_SERDES_LAT `OT_PDIE_SERDES_LAT `else 24 `endif)) u (
        .clk(clk), .tx(tx), .rx(rx), .pd_o(pd_o), .pd_i(pd_i));
endmodule

module ot_pdie_ucie (
    input  wire         clk,
    input  wire [511:0] tx,
    output wire [511:0] rx
`ifdef OT_PDIE_FM_PADS
  , output wire [511:0] pd_o,
    input  wire [511:0] pd_i
`endif
);
`ifndef OT_PDIE_FM_PADS
    wire [511:0] pd_o, pd_i;
    assign pd_i = 512'd0;
`endif
    ot_pdie_fm_lane #(.W(512), .LAT(`ifdef OT_PDIE_UCIE_LAT `OT_PDIE_UCIE_LAT `else 8 `endif)) u (
        .clk(clk), .tx(tx), .rx(rx), .pd_o(pd_o), .pd_i(pd_i));
endmodule
