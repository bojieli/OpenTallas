`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81hd_elemA_cv - PHYSICAL source of the rebuilt head element A macro (S81-HEAD 10-24, tools/s81_head/hd_elemA_rebuild.py).
// Read ONLY by that kit, together with the CLOSED element RTL ot_dsrom_head_elem @ f11f3cc47 (rtl/v41rom + leaf files,
// pulled by git show); simulation uses ot_s81hd_elem_cv.sv (same module name, lane RTL proven cycle-equal to f11f3cc47
// by tools/s81_head/hd_elem_eq.sh on every common output, with the same output registers).
// Why the wrapper: the fail-closed face guard needs every output to be a flop that drives only its port.  The closed
// RTL's outputs are internal state registers: o_v/o_d/l_v/l_d also feed the A join, best_row feeds the argmax compare,
// done / best_* are enable (hold) flops whose q feeds back into their own D (face_guard 'shared': c2 50 bits, c4 85).
// So every output gets one dedicated register stage, ot_s81hd_oreg (keep_hierarchy), +1 cycle uniformly on all A
// outputs (the bundle reads done / best_* / fault together; o/l are unconnected there).  No other change.
// ---------------------------------------------------------------------------
module ot_s81hd_elemA_cv (
    input  wire clk, input wire rst_n, input wire go, input wire [16:0] row0, input wire [255:0] x,
    input  wire b_v, input wire [31:0] b_d,
    output wire o_v, output wire [31:0] o_d, output wire l_v, output wire [31:0] l_d,
    output wire done, output wire [16:0] best_row, output wire [31:0] best_bits, output wire [31:0] best_key,
    output wire fault
);
    // OWNER RESET RULE 2026-10-24: the delivered reset is a SYNCHRONOUS signal (die relay chain); one local relay flop
    // here, then the element's flops use it with normal timed recovery / removal (c7: rst_n port -> 28.7k async pins was
    // the only TT setup failure, recovery -71 ps).  +1 cycle of reset latency.
    reg rst_q;
    always @(posedge clk) rst_q <= rst_n;
    wire m_ov, m_lv, m_done, m_fault; wire [31:0] m_od, m_ld, m_bits, m_key; wire [16:0] m_row;
    // one dedicated output register stage on EVERY output (+1 cycle, uniform; see the header)
    ot_s81hd_oreg #(.W(1 + 32 + 1 + 32 + 1 + 17 + 32 + 32 + 1)) u_oreg (.clk(clk), .rst_n(rst_q),
        .d({m_ov, m_od, m_lv, m_ld, m_done, m_row, m_bits, m_key, m_fault}),
        .q({o_v, o_d, l_v, l_d, done, best_row, best_bits, best_key, fault}));
    ot_dsrom_head_elem #(.LV(8), .PAD(0), .JOIN(1), .ROWS(32), .CUT(9'h1ff), .SPLIT9(1), .IOREG(1), .SAFE(1)) u_m (
        .clk(clk), .rst_n(rst_q), .go(go), .row0(row0), .x(x), .b_v(b_v), .b_d(b_d), .o_v(m_ov), .o_d(m_od), .l_v(m_lv),
        .l_d(m_ld), .done(m_done), .best_row(m_row), .best_bits(m_bits), .best_key(m_key), .fault(m_fault));
endmodule
