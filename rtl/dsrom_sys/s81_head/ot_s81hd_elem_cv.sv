`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81hd_elemA_cv / ot_s81hd_elemB_cv (S81-HEAD 10-24): SIMULATION models of the CLOSED head element views as the
// hard macros of the head tile kit (ot_s81hd_bundle CV = 1).  The views are physical/dsrom_fh_safe/closed/elemA
// (dshead-elemA-ss-f11f3cc47) and elemB (dshead-elemB-ss-a318fdf47): ot_dsrom_head_elem at IOREG 1 SAFE 1 CUT 0x1ff
// SPLIT9 1 with A = LV 8 PAD 0 JOIN 1 ROWS 32, B = LV 6 PAD 2 JOIN 0 ROWS 128; their LEF / liberty carry the cell names
// ot_s81hd_elem{A,B}_cv (physical/die_plan/s81_head/cores/views, renamed copies, tools/s81_head/hd_cv_views.py).
// The model is ot_s81hd_elem at that point, which tools/s81_head/hd_elem_eq.sh proves cycle-equal to the closed RTL
// (ot_dsrom_head_elem @ f11f3cc47) on every common output.  Ports = the view pins (no head_* outputs).
// Synthesis reads ot_s81hd_elem_cv_bb.v (black boxes) instead of this file.
// elemA REBUILD (S81-HEAD 10-24): the closed elemA view's clk pin is unreachable (24-nm sliver, source ODB lost), so
// elemA is re-implemented (tools/s81_head/hd_elemA_rebuild.py) from the closed RTL under ot_s81hd_elemA_rb.sv, which adds
// one dedicated output register (ot_s81hd_oreg) on EVERY output for the face guard: +1 cycle, uniform on all A
// outputs.  This model carries the same register stage (reads ot_s81hd_oreg.sv).
// ---------------------------------------------------------------------------
module ot_s81hd_elemA_cv #(parameter INSTANCE = "") (
    input  wire clk, input wire rst_n, input wire go, input wire [16:0] row0, input wire [255:0] x,
    input  wire b_v, input wire [31:0] b_d,
    output wire o_v, output wire [31:0] o_d, output wire l_v, output wire [31:0] l_d,
    output wire done, output wire [16:0] best_row, output wire [31:0] best_bits, output wire [31:0] best_key,
    output wire fault
);
    wire nc_hv; wire [31:0] nc_hd; wire [16:0] nc_hr;
    wire m_ov, m_lv, m_done, m_fault; wire [31:0] m_od, m_ld, m_bits, m_key; wire [16:0] m_row;
    // one dedicated output register stage on EVERY output (+1 cycle, uniform; see the header)
    ot_s81hd_oreg #(.W(1 + 32 + 1 + 32 + 1 + 17 + 32 + 32 + 1)) u_oreg (.clk(clk), .rst_n(rst_n),
        .d({m_ov, m_od, m_lv, m_ld, m_done, m_row, m_bits, m_key, m_fault}),
        .q({o_v, o_d, l_v, l_d, done, best_row, best_bits, best_key, fault}));
    ot_s81hd_elem #(.LV(8), .PAD(0), .JOIN(1), .ROWS(32), .CUT(9'h1ff), .SPLIT9(1), .INSTANCE(INSTANCE), .IOREG(1),
                    .SAFE(1)) u_m (
        .clk(clk), .rst_n(rst_n), .go(go), .row0(row0), .x(x), .b_v(b_v), .b_d(b_d), .o_v(m_ov), .o_d(m_od), .l_v(m_lv),
        .l_d(m_ld), .head_v(nc_hv), .head_d(nc_hd), .head_row(nc_hr),
        .done(m_done), .best_row(m_row), .best_bits(m_bits), .best_key(m_key), .fault(m_fault));
endmodule

module ot_s81hd_elemB_cv #(parameter INSTANCE = "") (
    input  wire clk, input wire rst_n, input wire go, input wire [16:0] row0, input wire [255:0] x,
    input  wire b_v, input wire [31:0] b_d,
    output wire o_v, output wire [31:0] o_d, output wire l_v, output wire [31:0] l_d,
    output wire done, output wire [16:0] best_row, output wire [31:0] best_bits, output wire [31:0] best_key,
    output wire fault
);
    wire nc_hv; wire [31:0] nc_hd; wire [16:0] nc_hr;
    ot_s81hd_elem #(.LV(6), .PAD(2), .JOIN(0), .ROWS(128), .CUT(9'h1ff), .SPLIT9(1), .INSTANCE(INSTANCE), .IOREG(1),
                    .SAFE(1)) u_m (
        .clk(clk), .rst_n(rst_n), .go(go), .row0(row0), .x(x), .b_v(b_v), .b_d(b_d), .o_v(o_v), .o_d(o_d), .l_v(l_v),
        .l_d(l_d), .head_v(nc_hv), .head_d(nc_hd), .head_row(nc_hr), .done(done), .best_row(best_row),
        .best_bits(best_bits), .best_key(best_key), .fault(fault));
endmodule
