`timescale 1ns/1ps
// ot_qfd_ucie_x64_phy: licensed link PHY abstract, core-facing top FDI, boundary timing only (ASSUMED registered pins)
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_qfd_ucie_x64_phy (
    output wire lclk,   // QW-GEN5 10-20: the PHY FDI clock output (1.0 GHz), root of the die clk_ucie tree
    input wire clk,
    input wire rst_n,
    output wire tx_up,
    input wire tx_v,
    input wire [1042:0] tx_flit,
    output wire rx_v,
    output wire [1042:0] rx_flit
);
endmodule
