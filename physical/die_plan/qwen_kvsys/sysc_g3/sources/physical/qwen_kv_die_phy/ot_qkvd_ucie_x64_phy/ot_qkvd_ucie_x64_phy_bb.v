`timescale 1ns/1ps
// ot_qkvd_ucie_x64_phy: licensed UCIe PHY abstract, FDI boundary timing only (ASSUMED registered pins)
// Blackbox view for synthesis and place-and-route (the hard macro).
// Line-side ports are the offshore bump interface already exported by the die plan;
// they match the functional ot_qkvd_ucie_x64_phy in rtl/qwen_split/qfd_link_slots.sv.
(* blackbox *)
module ot_qkvd_ucie_x64_phy (
    input wire clk,
    input wire rst_n,
    output wire tx_up,
    input wire tx_v,
    input wire [582:0] tx_flit,
    output wire rx_v,
    output wire [582:0] rx_flit,
    output wire link_v,
    output wire [582:0] link_flit,
    input wire far_v,
    input wire [582:0] far_flit
);
endmodule
