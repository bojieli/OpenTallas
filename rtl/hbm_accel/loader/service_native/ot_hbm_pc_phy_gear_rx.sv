`timescale 1ns/1ps
`default_nettype none
// BUS-GEAR-1 (2026-11-12): PHY-side receiver of one pseudo-channel's command bundle when the PC leaf runs WGB=2
// (ot_hbm_svc_pc_ctrl_leaf_cfg_h9b__fcore).  In: the 40 command bits (row 28 + col 12) and the 144-b write beat
// (col_data[127:0] = beat[127:0], col_strb[15:0] = beat[143:128]); col_we is the first-beat flag.  Out: the original
// bundle, every bit one edge later than the PC's pins (relative DRAM command timing unchanged), with the re-assembled
// 256-b col_data / 32-b col_strb valid on the col_we edge (zero on other edges; the PHY samples them only with col_we).
module ot_hbm_pc_phy_gear_rx (
    input  wire clk, rst_n,
    input  wire i_row_v, input wire [2:0] i_row_op, input wire [4:0] i_row_bank, input wire [18:0] i_row_row,
    input  wire i_col_v, i_col_we, input wire [4:0] i_col_bank, i_col_col,
    input  wire [127:0] i_col_data, input wire [15:0] i_col_strb,
    output wire row_v, output wire [2:0] row_op, output wire [4:0] row_bank, output wire [18:0] row_row,
    output wire col_v, col_we, output wire [4:0] col_bank, col_col,
    output wire [255:0] col_data, output wire [31:0] col_strb
);
    wire [39:0] s_o;
    wire [287:0] w_o;
    /* verilator lint_off PINCONNECTEMPTY */   // v_o: the PHY samples col_data / col_strb with col_we (= v_o)
    ot_bus_gear_rx #(.W(288), .BEATS(2), .SW(40)) u_rx (.clk(clk), .rst_n(rst_n), .b_i({i_col_strb, i_col_data}),
        .f_i(i_col_we), .s_i({i_row_v, i_row_op, i_row_bank, i_row_row, i_col_v, i_col_we, i_col_bank, i_col_col}),
        .v_o(), .d_o(w_o), .s_o(s_o));
    /* verilator lint_on PINCONNECTEMPTY */
    assign {row_v, row_op, row_bank, row_row, col_v, col_we, col_bank, col_col} = s_o;
    assign col_data = w_o[255:0];
    assign col_strb = w_o[287:256];
endmodule
`default_nettype wire

`default_nettype none
// NPC copies of ot_hbm_pc_phy_gear_rx in the packing of the PHY slice macros (ot_hbm3e_phy_rc_*: PC k owns
// row_v[k], row_op[3k+:3], row_bank[5k+:5], row_row[19k+:19], col_v[k], col_we[k], col_bank[5k+:5], col_col[5k+:5],
// col_data[256k+:256], col_strb[32k+:32]).  Placed in the PHY_N* / PHY_NC partition between the L8 / L9 landing and
// the slice macro: i_* = the narrow pins from the WGB=2 PC leaves, outputs drive the macro unchanged.
module ot_hbm_pc_phy_gear_rx_x #(
    parameter integer NPC = 10
) (
    input  wire clk, rst_n,
    input  wire [NPC-1:0] i_row_v, input wire [3*NPC-1:0] i_row_op, input wire [5*NPC-1:0] i_row_bank,
    input  wire [19*NPC-1:0] i_row_row, input wire [NPC-1:0] i_col_v, i_col_we,
    input  wire [5*NPC-1:0] i_col_bank, i_col_col, input wire [128*NPC-1:0] i_col_data, input wire [16*NPC-1:0] i_col_strb,
    output wire [NPC-1:0] row_v, output wire [3*NPC-1:0] row_op, output wire [5*NPC-1:0] row_bank,
    output wire [19*NPC-1:0] row_row, output wire [NPC-1:0] col_v, col_we,
    output wire [5*NPC-1:0] col_bank, col_col, output wire [256*NPC-1:0] col_data, output wire [32*NPC-1:0] col_strb
);
    genvar k;
    generate for (k = 0; k < NPC; k = k + 1) begin : g_pc
        ot_hbm_pc_phy_gear_rx u (.clk(clk), .rst_n(rst_n),
            .i_row_v(i_row_v[k]), .i_row_op(i_row_op[3*k+:3]), .i_row_bank(i_row_bank[5*k+:5]), .i_row_row(i_row_row[19*k+:19]),
            .i_col_v(i_col_v[k]), .i_col_we(i_col_we[k]), .i_col_bank(i_col_bank[5*k+:5]), .i_col_col(i_col_col[5*k+:5]),
            .i_col_data(i_col_data[128*k+:128]), .i_col_strb(i_col_strb[16*k+:16]),
            .row_v(row_v[k]), .row_op(row_op[3*k+:3]), .row_bank(row_bank[5*k+:5]), .row_row(row_row[19*k+:19]),
            .col_v(col_v[k]), .col_we(col_we[k]), .col_bank(col_bank[5*k+:5]), .col_col(col_col[5*k+:5]),
            .col_data(col_data[256*k+:256]), .col_strb(col_strb[32*k+:32]));
    end endgenerate
endmodule
`default_nettype wire
