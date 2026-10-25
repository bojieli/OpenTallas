`timescale 1ns/1ps
`default_nettype none
// chain-terminal plain ring bank (ring position 7; LH-UNREAD F-T 2026-10-19, die master of hcb_<q>7): ot_hbm_hc_bankq_static
// without the forward-descriptor ports and their CPO face registers (bank 7 has no next bank; its sum_out / f_out go to
// bank 0's chain-exit relay).  Every retained output is cycle-exact with ot_hbm_hc_bankq_static #(CPI, CPO, W).  Canonical
// form of the scoped die copy rtl/hbm_accel/die_glue/scoped_d4g/hcbt.sv (claude/hbm-unread-term-1019 4418ce6ff), with W.
// MUT (bench): 1 = weight slice rotate (bank stage), 3 = f_out inverted at the face.  A die file list that uses this file
// must not also carry the scoped hcbt.sv (same module name).
module ot_hbm_hc_bankq_term_static #(parameter integer MUT = 0, parameter integer CPI = 0, parameter integer CPO = 0,
    parameter integer W = 64, parameter integer NVW = (W == 128) ? 8 : 7, parameter integer JW = (W == 128) ? 2 : 1)(
    input  wire          clk, rst_n,
    input  wire          d_v, d_ss, input wire [NVW-1:0] d_nv, input wire [9:0] d_wa, d_xa,
    input  wire [W*32-1:0] sum_in, output wire [W*32-1:0] sum_out,
    input  wire          f_in, output wire f_out,
    input  wire          xb_v, input wire [1:0] xb_beat, input wire [255:0] xb_d,
    input  wire          wv, xv, input wire [JW-1:0] j, input wire [9:0] wa,
    output wire          wfault
);
    wire t_v, t_ss; wire [NVW-1:0] t_nv; wire [9:0] t_wa, t_xa;   // stage forward descriptor: no load in the terminal tile
    ot_hbm_hc_bankq_core #(.MUT(MUT), .CPI(CPI), .CPO(CPO), .W(W), .TERM(1)) u_c (.clk(clk), .rst_n(rst_n), .first(1'b0),
        .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa), .o_v(t_v), .o_ss(t_ss), .o_nv(t_nv),
        .o_wa(t_wa), .o_xa(t_xa), .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out),
        .xb_v(xb_v), .xb_beat(xb_beat), .xb_d(xb_d), .wv(wv), .xv(xv), .j(j), .wa(wa), .wfault(wfault));
endmodule
`default_nettype wire
