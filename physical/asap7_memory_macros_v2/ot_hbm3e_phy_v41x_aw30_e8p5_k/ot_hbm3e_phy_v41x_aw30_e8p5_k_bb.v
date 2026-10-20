`timescale 1ns/1ps
// HBM3E PHY + controller abstract (v2, legal pins/PDN) for the adopted V4.1 die, controller-side boundary timing only (assumed); functional model: rtl/chip/ot_chip_v41x_hbm3e_phy.sv
// S81 K-only variant (tools/s81_dv/phy_k_variant.py: no W port, no model counters).
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_hbm3e_phy_v41x_aw30_e8p5_k (
    input wire clk,
    input wire rst_n,
    input wire [31:0] k_v,
    output wire [31:0] k_rdy,
    input wire [959:0] k_addr,
    input wire [127:0] k_len,
    input wire [543:0] k_tag,
    input wire [31:0] k_we,
    input wire [8191:0] k_wdata,
    input wire [1023:0] k_wstrb,
    output wire [31:0] k_wr_done,
    output wire [31:0] kr_v,
    input wire [31:0] kr_rdy,
    output wire [543:0] kr_tag,
    output wire [127:0] kr_beat,
    output wire [8191:0] kr_data,
    output wire k_oor
);
endmodule
