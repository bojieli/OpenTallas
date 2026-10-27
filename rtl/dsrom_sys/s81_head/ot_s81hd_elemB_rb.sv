`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81hd_elemB_cv - PHYSICAL source of the rebuilt head element B macro (S81-HEAD 10-24, tools/s81_head/hd_elemA_rebuild.py).
// Read ONLY by that kit, together with the CLOSED element RTL ot_dsrom_head_elem @ f11f3cc47 (rtl/v41rom + leaf files,
// pulled by git show); simulation uses ot_s81hd_elem_cv.sv (same module name, lane RTL proven cycle-equal to f11f3cc47
// by tools/s81_head/hd_elem_eq.sh on every common output, with the same output registers).
// Why the wrapper: as ot_s81hd_elemA_rb.sv (fail-closed face guard: every output a dedicated flop driving only its
// port).  B (LV 6 PAD 2 JOIN 0 ROWS 128) is the bundle's root1024 element: its o_v / o_d (the padded root stream) feed
// the four A elements' b_v / b_d; one ot_s81hd_oreg stage on EVERY output = +1 cycle on that stream (the A join FIFO
// absorbs it; tile bench).
// HEAD-CORE-LAT-R6 10-26 (RULING HEAD-CORE-LAT-R5 (2), no silent dangling): B's l_v / l_d / done / best_row /
// best_bits / best_key were unconnected in the bundle (proven unused: nc_* wires with no load) -> REMOVED from this
// macro; their element cones are dead and synthesis drops them.  The old kept face register u_bin_jn (50 flops, q unused)
// is deleted.
// HEAD-CORE-R14 10-27 (COORD RULING HEAD-CORE-R13 ASK2 (a)): the PROVEN-DEAD inputs row0[16:0] / b_v / b_d[31:0] (JOIN 0
// never reads them; flattened yosys no-fanout proof results/head_core_lat_r6_1026/elemB/dead_inputs.json) are REMOVED
// from the macro (50 ports; the parent ties go too).  The element's row0/b_v/b_d inputs are constant 0 inside the
// wrapper, i.e. the value the parent tied before: LEC vs the r11 RTL / its proven netlist (head_core_r14 README).
// Synthesis source: the kit's 12.2a1 pushdown patch (patch_synth.tcl on 1_synth.odb) replaces clk by the ft_* island
// ports after synthesis; the kit LEC gold wrapper carries those ft_* ports (clk = ft_mstrap_i).
// ---------------------------------------------------------------------------
module ot_s81hd_elemB_cv (
    input  wire clk, input wire rst_n, input wire go, input wire [255:0] x,
    output wire o_v, output wire [31:0] o_d,
    output wire fault
);
    // OWNER RESET RULE 2026-10-24: the delivered reset is a SYNCHRONOUS signal (die relay chain); one local relay flop
    // here, then the element's flops use it with normal timed recovery / removal (c7: rst_n port -> 28.7k async pins was
    // the only TT setup failure, recovery -71 ps).  +1 cycle of reset latency.
    reg rst_q;
    always @(posedge clk) rst_q <= rst_n;
    wire m_ov, m_fault; wire [31:0] m_od;
    wire nc_lv, nc_done; wire [31:0] nc_ld, nc_bits, nc_key; wire [16:0] nc_row;   // dead element cones (removed ports)
    // one dedicated output register stage on EVERY output (+1 cycle, uniform; see the header)
    ot_s81hd_oreg #(.W(1 + 32 + 1)) u_oreg (.clk(clk), .rst_n(rst_q),
        .d({m_ov, m_od, m_fault}), .q({o_v, o_d, fault}));
    ot_dsrom_head_elem #(.LV(6), .PAD(2), .JOIN(0), .ROWS(128), .CUT(9'h1ff), .SPLIT9(1), .IOREG(1), .SAFE(1)) u_m (
        .clk(clk), .rst_n(rst_q), .go(go), .row0(17'd0), .x(x), .b_v(1'b0), .b_d(32'd0), .o_v(m_ov), .o_d(m_od), .l_v(nc_lv),
        .l_d(nc_ld), .done(nc_done), .best_row(nc_row), .best_bits(nc_bits), .best_key(nc_key), .fault(m_fault));
endmodule
