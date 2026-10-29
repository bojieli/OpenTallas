`timescale 1ns/1ps
// HBM3E PHY-only abstract slice PCs 10-21 (row/column/data boundary), boundary timing assumed
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_hbm3e_phy_rc_e8p5_pc10_21 (
    input wire clk,
    input wire rst_n,
    input wire [11:0] row_v,
    input wire [35:0] row_op,
    input wire [59:0] row_bank,
    input wire [227:0] row_row,
    input wire [11:0] col_v,
    input wire [11:0] col_we,
    input wire [59:0] col_bank,
    input wire [59:0] col_col,
    input wire [3071:0] col_data,
    input wire [383:0] col_strb,
    output wire [11:0] dram_rvalid,
    output wire [3071:0] dram_rdata
);
endmodule
