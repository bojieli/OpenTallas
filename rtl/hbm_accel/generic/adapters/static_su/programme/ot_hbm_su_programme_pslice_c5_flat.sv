`timescale 1ns/1ps
// PL-PSLICE (PARENTS-LANDED 10-18): ot_hbm_su_programme_pslice_c5 written out as the WIRES-ONLY flat parent that
// tools/landed_parent/lp.py lands (the generate loop expanded at the default DICT_CAP {1,1,1,1,1,2,13,9,10,3}, MUT 0):
// columns 1,2,3 = the L leaf master ot_hbm_su_programme_pgcol_l, the other seven = ot_hbm_su_programme_pgcol_s, head =
// ot_hbm_su_programme_pghead with the hardened head view's parameters (NC 10, OREG/FREG/HRLY/DLAT 1, CLAT 2).  Same ports
// and same cycle behaviour as ot_hbm_su_programme_pslice_c5 (bench tb_pslice_c5_flat_eq).  Per-column status nets so
// every net has one driver region.
// 10-18 PL-PSLICE (PL-KIT form): the 2,422-bit command bus is split per clock region so every output port has ONE
// driver region: command_l = {cm3, cm2, cm1} (L row), command_t = {cm9[117:0], cm8, cm7, cm6, cm5} (top S row),
// command_b = {cm4, cm0} (bottom S pair).  The generate form's bus is
//   command == {command_t, command_b[511:256], command_l, command_b[255:0]}
// (the parent die / pslice_q wrapper concatenates; tb_hbm_su_programme_pslice_c5_flat_eq compares exactly that).
module ot_hbm_su_programme_pslice_c5_flat (
    input logic clk, rst_n,
    input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
    input logic start, input logic [15:0] length,
    output logic busy, valid, done, fault, output logic [15:0] edge_index,
    output logic [767:0] command_l, output logic [1141:0] command_t, output logic [511:0] command_b);
    wire [9:0] we;  wire any;  wire [4:0] bank;  wire [6:0] row;  wire [255:0] data;
    wire bs0, vl0, dn0, ft0;  wire [15:0] ei0;  wire [255:0] cm0;
    wire bs1, vl1, dn1, ft1;  wire [15:0] ei1;  wire [255:0] cm1;
    wire bs2, vl2, dn2, ft2;  wire [15:0] ei2;  wire [255:0] cm2;
    wire bs3, vl3, dn3, ft3;  wire [15:0] ei3;  wire [255:0] cm3;
    wire bs4, vl4, dn4, ft4;  wire [15:0] ei4;  wire [255:0] cm4;
    wire bs5, vl5, dn5, ft5;  wire [15:0] ei5;  wire [255:0] cm5;
    wire bs6, vl6, dn6, ft6;  wire [15:0] ei6;  wire [255:0] cm6;
    wire bs7, vl7, dn7, ft7;  wire [15:0] ei7;  wire [255:0] cm7;
    wire bs8, vl8, dn8, ft8;  wire [15:0] ei8;  wire [255:0] cm8;
    wire bs9, vl9, dn9, ft9;  wire [15:0] ei9;  wire [255:0] cm9;
    ot_hbm_su_programme_pgcol_s u_c0 (.clk(clk), .rst_n(rst_n), .cfg_we(we[0]), .cfg_any(any), .cfg_bank(bank), .cfg_row(row), .cfg_data(data),
        .start(start), .length(length), .busy(bs0), .valid(vl0), .done(dn0), .fault(ft0), .edge_index(ei0), .command(cm0));
    ot_hbm_su_programme_pgcol_l u_c1 (.clk(clk), .rst_n(rst_n), .cfg_we(we[1]), .cfg_any(any), .cfg_bank(bank), .cfg_row(row), .cfg_data(data),
        .start(start), .length(length), .busy(bs1), .valid(vl1), .done(dn1), .fault(ft1), .edge_index(ei1), .command(cm1));
    ot_hbm_su_programme_pgcol_l u_c2 (.clk(clk), .rst_n(rst_n), .cfg_we(we[2]), .cfg_any(any), .cfg_bank(bank), .cfg_row(row), .cfg_data(data),
        .start(start), .length(length), .busy(bs2), .valid(vl2), .done(dn2), .fault(ft2), .edge_index(ei2), .command(cm2));
    ot_hbm_su_programme_pgcol_l u_c3 (.clk(clk), .rst_n(rst_n), .cfg_we(we[3]), .cfg_any(any), .cfg_bank(bank), .cfg_row(row), .cfg_data(data),
        .start(start), .length(length), .busy(bs3), .valid(vl3), .done(dn3), .fault(ft3), .edge_index(ei3), .command(cm3));
    ot_hbm_su_programme_pgcol_s u_c4 (.clk(clk), .rst_n(rst_n), .cfg_we(we[4]), .cfg_any(any), .cfg_bank(bank), .cfg_row(row), .cfg_data(data),
        .start(start), .length(length), .busy(bs4), .valid(vl4), .done(dn4), .fault(ft4), .edge_index(ei4), .command(cm4));
    ot_hbm_su_programme_pgcol_s u_c5 (.clk(clk), .rst_n(rst_n), .cfg_we(we[5]), .cfg_any(any), .cfg_bank(bank), .cfg_row(row), .cfg_data(data),
        .start(start), .length(length), .busy(bs5), .valid(vl5), .done(dn5), .fault(ft5), .edge_index(ei5), .command(cm5));
    ot_hbm_su_programme_pgcol_s u_c6 (.clk(clk), .rst_n(rst_n), .cfg_we(we[6]), .cfg_any(any), .cfg_bank(bank), .cfg_row(row), .cfg_data(data),
        .start(start), .length(length), .busy(bs6), .valid(vl6), .done(dn6), .fault(ft6), .edge_index(ei6), .command(cm6));
    ot_hbm_su_programme_pgcol_s u_c7 (.clk(clk), .rst_n(rst_n), .cfg_we(we[7]), .cfg_any(any), .cfg_bank(bank), .cfg_row(row), .cfg_data(data),
        .start(start), .length(length), .busy(bs7), .valid(vl7), .done(dn7), .fault(ft7), .edge_index(ei7), .command(cm7));
    ot_hbm_su_programme_pgcol_s u_c8 (.clk(clk), .rst_n(rst_n), .cfg_we(we[8]), .cfg_any(any), .cfg_bank(bank), .cfg_row(row), .cfg_data(data),
        .start(start), .length(length), .busy(bs8), .valid(vl8), .done(dn8), .fault(ft8), .edge_index(ei8), .command(cm8));
    ot_hbm_su_programme_pgcol_s u_c9 (.clk(clk), .rst_n(rst_n), .cfg_we(we[9]), .cfg_any(any), .cfg_bank(bank), .cfg_row(row), .cfg_data(data),
        .start(start), .length(length), .busy(bs9), .valid(vl9), .done(dn9), .fault(ft9), .edge_index(ei9), .command(cm9));
    ot_hbm_su_programme_pghead u_h (.clk(clk), .rst_n(rst_n),
        .cfg_we(cfg_we), .cfg_bank(cfg_bank), .cfg_row(cfg_row), .cfg_data(cfg_data),
        .l_fault({ft9, ft8, ft7, ft6, ft5, ft4, ft3, ft2, ft1, ft0}),
        .l_valid({vl9, vl8, vl7, vl6, vl5, vl4, vl3, vl2, vl1, vl0}),
        .o_we(we), .o_any(any), .o_bank(bank), .o_row(row), .o_data(data), .fault(fault));
    assign busy = bs0;  assign valid = vl0;  assign done = dn0;  assign edge_index = ei0;
    assign command_l = {cm3, cm2, cm1};
    assign command_t = {cm9[117:0], cm8, cm7, cm6, cm5};
    assign command_b = {cm4, cm0};
endmodule
