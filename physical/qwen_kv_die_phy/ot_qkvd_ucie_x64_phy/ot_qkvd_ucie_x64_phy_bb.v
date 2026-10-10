`timescale 1ns/1ps
// ot_qkvd_ucie_x64_phy: licensed UCIe PHY + D2D adapter abstract, FDI boundary timing only (ASSUMED registered pins)
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_qkvd_ucie_x64_phy (
    input wire clk,
    input wire rst_n,
    output wire tx_up,
    input wire tx_v,
    input wire [547:0] tx_flit,
    output wire rx_v,
    output wire [547:0] rx_flit
);
endmodule
