`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81hd_elemB_cv - PHYSICAL source of the rebuilt head element B macro (S81-HEAD 10-24, tools/s81_head/hd_elemA_rebuild.py).
// Read ONLY by that kit, together with the CLOSED element RTL ot_dsrom_head_elem @ f11f3cc47 (rtl/v41rom + leaf files,
// pulled by git show); simulation uses ot_s81hd_elem_cv.sv (same module name, lane RTL proven cycle-equal to f11f3cc47
// by tools/s81_head/hd_elem_eq.sh on every common output, with the same output registers).
// Why the wrapper: as ot_s81hd_elemA_rb.sv (fail-closed face guard: every output a dedicated flop driving only its
// port).  B (LV 6 PAD 2 JOIN 0 ROWS 128) is the bundle's root1024 element: its o_v / o_d (the padded root stream) feed
// the four A elements' b_v / b_d; one ot_s81hd_oreg stage on EVERY output = +1 cycle on that stream (the A join FIFO
// absorbs it; tile bench).  The rest of B's outputs are unconnected in the bundle.
// JOIN 0 leaves row0 / b_v / b_d unused inside the element (the bundle ties them 0); their pin registers were
// removed (face_guard 'dropped', 50 bits), so they get a kept face register u_bin_jn (q unused; face_keep.tcl keeps
// u_bin_* through ORFS eliminate_dead_logic).
// ---------------------------------------------------------------------------
module ot_s81hd_elemB_cv (
    input  wire clk, input wire rst_n, input wire go, input wire [16:0] row0, input wire [255:0] x,
    input  wire b_v, input wire [31:0] b_d,
    output wire o_v, output wire [31:0] o_d, output wire l_v, output wire [31:0] l_d,
    output wire done, output wire [16:0] best_row, output wire [31:0] best_bits, output wire [31:0] best_key,
    output wire fault
);
    wire m_ov, m_lv, m_done, m_fault; wire [31:0] m_od, m_ld, m_bits, m_key; wire [16:0] m_row;
    // one dedicated output register stage on EVERY output (+1 cycle, uniform; see the header)
    ot_s81hd_oreg #(.W(1 + 32 + 1 + 32 + 1 + 17 + 32 + 32 + 1)) u_oreg (.clk(clk), .rst_n(rst_n),
        .d({m_ov, m_od, m_lv, m_ld, m_done, m_row, m_bits, m_key, m_fault}),
        .q({o_v, o_d, l_v, l_d, done, best_row, best_bits, best_key, fault}));
    ot_s81hd_oreg #(.W(17 + 1 + 32)) u_bin_jn (.clk(clk), .rst_n(rst_n), .d({row0, b_v, b_d}), .q());
    ot_dsrom_head_elem #(.LV(6), .PAD(2), .JOIN(0), .ROWS(128), .CUT(9'h1ff), .SPLIT9(1), .IOREG(1), .SAFE(1)) u_m (
        .clk(clk), .rst_n(rst_n), .go(go), .row0(row0), .x(x), .b_v(b_v), .b_d(b_d), .o_v(m_ov), .o_d(m_od), .l_v(m_lv),
        .l_d(m_ld), .done(m_done), .best_row(m_row), .best_bits(m_bits), .best_key(m_key), .fault(m_fault));
endmodule
