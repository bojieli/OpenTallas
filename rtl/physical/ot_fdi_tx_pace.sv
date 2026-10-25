`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// TOK-QK/C 2026-10-24 (KV boot fix C2): static transmit-slot pacer of a core-clock FDI link adapter whose PHY runs on a
// slower clock.  slot = NUM of every DEN core cycles (Bresenham, evenly spread), NUM/DEN < f_phy / f_core with margin, so
// the adapter never offers more flits than the PHY drains and the PHY-side CDC FIFO (ot_fdi_phy_cdc) cannot fill.  A fixed
// schedule, no ready loop across the die.  The adapter takes `up & slot` on its tx_up pin (the per-cycle transmit
// permission, FDI pl_trdy): a flit (payload and/or piggy-backed credit) leaves only in a slot.
// Default 19/24 = 0.7917 of 1.2 GHz = 0.950 GHz < clk_phy 0.959 GHz (0.92 % margin, >> PLL ppm; link TX rate -0.92 %).
// ---------------------------------------------------------------------------------------------------------------------
module ot_fdi_tx_pace #(
    parameter integer NUM = 19,
    parameter integer DEN = 24
) (
    input  wire clk,
    input  wire rst_n,
    output reg  slot
);
    localparam integer AW = $clog2(DEN + NUM + 1);
    reg [AW-1:0] acc;
    wire [AW-1:0] nx = acc + AW'(NUM);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin acc <= 0; slot <= 1'b0; end
        else if (nx >= AW'(DEN)) begin acc <= nx - AW'(DEN); slot <= 1'b1; end
        else begin acc <= nx; slot <= 1'b0; end
    end
`ifndef SYNTHESIS
    initial if (NUM <= 0 || NUM >= DEN) $fatal(1, "ot_fdi_tx_pace: NUM %0d / DEN %0d must be a proper fraction", NUM, DEN);
`endif
endmodule
