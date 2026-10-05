`timescale 1ns/1ps
// HBM3E PHY + controller abstract for the adopted V4.1 die, controller-side boundary timing only (assumed); functional model: rtl/chip/ot_chip_v41x_hbm3e_phy.sv
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_hbm3e_phy_v41x_aw30 (
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
    input wire w_v,
    output wire w_rdy,
    input wire [23:0] w_addr,
    input wire [5:0] w_len,
    input wire [9:0] w_tag,
    output wire [7:0] w_room,
    output wire [7:0] wr_v,
    input wire [7:0] wr_rdy,
    output wire [79:0] wr_tag,
    output wire [39:0] wr_beat,
    output wire [2047:0] wr_data,
    output wire k_oor,
    output wire w_oor,
    output wire [63:0] refreshes,
    output wire [31:0] w_reads
);
endmodule
