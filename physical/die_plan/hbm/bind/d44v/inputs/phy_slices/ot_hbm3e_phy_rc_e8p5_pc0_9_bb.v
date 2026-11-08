`timescale 1ns/1ps
// HBM3E PHY-only abstract slice PCs 0-9 (row/column/data boundary), boundary timing assumed
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_hbm3e_phy_rc_e8p5_pc0_9 (
    input wire clk,
    input wire rst_n,
    input wire [9:0] row_v,
    input wire [29:0] row_op,
    input wire [49:0] row_bank,
    input wire [189:0] row_row,
    input wire [9:0] col_v,
    input wire [9:0] col_we,
    input wire [49:0] col_bank,
    input wire [49:0] col_col,
    input wire [2559:0] col_data,
    input wire [319:0] col_strb,
    output wire [9:0] dram_rvalid,
    output wire [2559:0] dram_rdata
);
endmodule
