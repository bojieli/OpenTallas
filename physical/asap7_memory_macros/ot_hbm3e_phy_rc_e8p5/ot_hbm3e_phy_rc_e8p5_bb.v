`timescale 1ns/1ps
// HBM3E PHY-only abstract (row/column/data boundary of the real controller), boundary timing assumed; functional model: rtl/hbm_accel/loader/service_native/tb_hbm_svc_command_dram_pipeline_fixture.sv
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_hbm3e_phy_rc_e8p5 (
    input wire clk,
    input wire rst_n,
    input wire [31:0] row_v,
    input wire [95:0] row_op,
    input wire [159:0] row_bank,
    input wire [607:0] row_row,
    input wire [31:0] col_v,
    input wire [31:0] col_we,
    input wire [159:0] col_bank,
    input wire [159:0] col_col,
    input wire [8191:0] col_data,
    input wire [1023:0] col_strb,
    output wire [31:0] dram_rvalid,
    output wire [8191:0] dram_rdata
);
endmodule
