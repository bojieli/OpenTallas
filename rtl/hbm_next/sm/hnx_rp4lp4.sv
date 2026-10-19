// HBM-NEXT-SM4 (lane HBM-NEXT-SM4, 10-19): the SM P = 4 matrix tile hnx_rp4lp4 for the NEXT-release HBM die (not a release
// gate).  Forked by COPY from the d4g landed SM tile rp4lp (claude/pl-smt-1018 2444d768c, ot_hbm_smh_rp4_flat): same tile
// pins and bit counts, same transport hard children (row_w / row_e / beat_e / land), same two leaves; each leaf now holds
// P accumulator LANES, each lane one unmodified copy of the closed d4g leaf (x store smh_xs + block-dot column smh_bdc +
// BF16 column tcl x2 + tct, hnx_rp4_leafh = ot_hbm_smh_rp4_leafh renamed), so every lane keeps the golden reduction order
// bit for bit (no new leaf variant: P is a parameter of the leaf).
//
// Mechanisms (static schedule only: no ready / credit / backpressure; a schedule collision is a FAULT, never a stall):
//  * weight / row broadcast: the leaf's row bundle rl1 (818 b: control, 788-b weight word, x read address) reaches the
//    P lanes through ONE kept register copy per lane, placed beside that lane's x store (registered per-lane fan-out,
//    +1 cycle on every lane alike; D1 synth: an unbuffered P >= 4 broadcast is a 4.3 ns net);
//  * x-slot stores: lane p has its own x store (smh_xs).  The x-write beat bk1 (2,069 b, unchanged pins) reaches lane p
//    through its own kept register copy (+1 cycle); its valid is gated by the leaf's x TARGET mask.  Lane addressing
//    without new pins: a LANE-SELECT beat = a valid x-write beat whose 13-bit beat one-hot is ZERO (never produced by
//    the d4g front: every real beat has exactly one beat bit; the x store writes nothing for it) loads
//      data[P-1:0]    -> x target mask (which lanes the following x-write beats land in; >1 bit = broadcast x),
//      data[8+P-1:8]  -> active-lane mask (which lanes publish results).
//    Reset: target = active = lane 0, so a P = 1 programme (no select beats) runs exactly as the d4g tile (+2 cycles).
//    The select beat travels the beat relay chain like any beat (bout), so every tile of the column takes it.
//  * slot-major publish with a fixed lane slot: lane p's leaf result word {gv, gf, gy, gt} is delayed p x LSKEW cycles
//    (LSKEW = IL = 8 = one interleave burst) and the lanes are merged onto the leaf's ONE 50-b gather lane (pins
//    unchanged).  The lane of a published word is therefore fixed by its cycle (lane tag = slot offset / LSKEW, a
//    compiler-known constant: result of lane p, row r at t_r + 2 + p*LSKEW); a word published by two lanes in the same
//    cycle is a schedule COLLISION: published with gf = 1 (fault).  The compiler keeps a row chunk >= P*IL cycles apart
//    (K >= 4 beats per interleaved row chunk at P = 4), which the production shape satisfies.
//
// Latency (compiler record, vs rp4lp): rin/bin -> lane operands +1 (fan-out copies); lane result -> gather +1 (merge
// register) + p*LSKEW for lane p.  Every other port offset as rp4lp.
`timescale 1ns/1ps

// ---------------------------------------------------------------------------------------------------------------------
// THE FLAT PARENT (wires only: lp.py input) -- ot_hbm_smh_rp4_flat with the leaves replaced by P-lane leaves.
// Ports, port widths and transport children unchanged (rin_n = rin[817:0], rin_s = rin[1635:818], rout likewise).
module hnx_rp4lp4_flat (input wire clk, input wire rst_n,
 input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
 input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2,
 input wire [817:0] rin_n, input wire [817:0] rin_s, input wire [2068:0] bin,
 output wire [817:0] rout_n, output wire [817:0] rout_s, output wire [2068:0] bout,
 input wire [99:0] gin, output wire [199:0] gout);
 wire [25:0] st_n, st_s;
 wire [817:0] rl_n, rl_s, rl1_n, rl1_s, rpm_n, rpm_s;
 wire [2068:0] bin_l, bm, bk1_n, bk1_s;
 wire [49:0] g0, g1, g0m;
 wire [99:0] gpm;
 hnx_rp4l_strap u_sr_n (.clk(clk), .d({xs_g2, xs_a2, xs_g1, xs_a1}), .q(st_n));
 hnx_rp4l_strap u_sr_s (.clk(clk), .d({xss_g2, xss_a2, xss_g1, xss_a1}), .q(st_s));
 hnx_rp4l_pinrow u_pr_n (.clk(clk), .rst_n(rst_n), .d(rin_n), .q(rl_n));
 hnx_rp4l_pinrow u_pr_s (.clk(clk), .rst_n(rst_n), .d(rin_s), .q(rl_s));
 hnx_rp4l_pinbeat u_pb (.clk(clk), .rst_n(rst_n), .d(bin), .q(bin_l));
 ot_smh_tr_group_row_w u_row0 (.clk(clk), .rst_a(rst_n), .d(rl_n), .first(rl1_n), .last(rpm_n));
 ot_smh_tr_group_row_w u_row1 (.clk(clk), .rst_a(rst_n), .d(rl_s), .first(rl1_s), .last(rpm_s));
 ot_smh_tr_group_beat_e u_beat_t (.clk(clk), .rst_a(rst_n), .d(bin_l), .last(bm));
 ot_smh_tr_group_land u_land_n (.clk(clk), .rst_a(rst_n), .d(bin_l), .q(bk1_n));
 ot_smh_tr_group_land u_land_s (.clk(clk), .rst_a(rst_n), .d(bin_l), .q(bk1_s));
 ot_smh_tr_group_row_e u_rowe0 (.clk(clk), .rst_a(rst_n), .d(rpm_n), .last(rout_n));
 ot_smh_tr_group_row_e u_rowe1 (.clk(clk), .rst_a(rst_n), .d(rpm_s), .last(rout_s));
 ot_smh_tr_group_beat_e u_beate (.clk(clk), .rst_a(rst_n), .d(bm), .last(bout));
 hnx_rp4lp4_lf u_lf0 (.clk(clk), .rst_n(rst_n), .st(st_n), .rl1(rl1_n), .bk1(bk1_n), .g(g0));
 hnx_rp4lp4_lf u_lf1 (.clk(clk), .rst_n(rst_n), .st(st_s), .rl1(rl1_s), .bk1(bk1_s), .g(g1));
 hnx_rp4l_gn u_gn (.clk(clk), .rst_n(rst_n), .g0(g0), .gin(gin), .g0m(g0m), .gpm(gpm));
 hnx_rp4l_gs u_gs (.clk(clk), .rst_n(rst_n), .g1in(g1), .g0m(g0m), .gpm(gpm), .gout(gout));
endmodule

// LEVER (a) (PROG 10-19, adopted base): the same flat parent with the SHARED-x-store leaves hnx_rp4lp4_lfx (one hnx_xs4
// per leaf instead of P separate closed x stores).  Ports, transport children, regions and cycle timing as hnx_rp4lp4_flat.
module hnx_rp4lp4x_flat (input wire clk, input wire rst_n,
 input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
 input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2,
 input wire [817:0] rin_n, input wire [817:0] rin_s, input wire [2068:0] bin,
 output wire [817:0] rout_n, output wire [817:0] rout_s, output wire [2068:0] bout,
 input wire [99:0] gin, output wire [199:0] gout);
 wire [25:0] st_n, st_s;
 wire [817:0] rl_n, rl_s, rl1_n, rl1_s, rpm_n, rpm_s;
 wire [2068:0] bin_l, bm, bk1_n, bk1_s;
 wire [49:0] g0, g1, g0m;
 wire [99:0] gpm;
 hnx_rp4l_strap u_sr_n (.clk(clk), .d({xs_g2, xs_a2, xs_g1, xs_a1}), .q(st_n));
 hnx_rp4l_strap u_sr_s (.clk(clk), .d({xss_g2, xss_a2, xss_g1, xss_a1}), .q(st_s));
 hnx_rp4l_pinrow u_pr_n (.clk(clk), .rst_n(rst_n), .d(rin_n), .q(rl_n));
 hnx_rp4l_pinrow u_pr_s (.clk(clk), .rst_n(rst_n), .d(rin_s), .q(rl_s));
 hnx_rp4l_pinbeat u_pb (.clk(clk), .rst_n(rst_n), .d(bin), .q(bin_l));
 ot_smh_tr_group_row_w u_row0 (.clk(clk), .rst_a(rst_n), .d(rl_n), .first(rl1_n), .last(rpm_n));
 ot_smh_tr_group_row_w u_row1 (.clk(clk), .rst_a(rst_n), .d(rl_s), .first(rl1_s), .last(rpm_s));
 ot_smh_tr_group_beat_e u_beat_t (.clk(clk), .rst_a(rst_n), .d(bin_l), .last(bm));
 ot_smh_tr_group_land u_land_n (.clk(clk), .rst_a(rst_n), .d(bin_l), .q(bk1_n));
 ot_smh_tr_group_land u_land_s (.clk(clk), .rst_a(rst_n), .d(bin_l), .q(bk1_s));
 ot_smh_tr_group_row_e u_rowe0 (.clk(clk), .rst_a(rst_n), .d(rpm_n), .last(rout_n));
 ot_smh_tr_group_row_e u_rowe1 (.clk(clk), .rst_a(rst_n), .d(rpm_s), .last(rout_s));
 ot_smh_tr_group_beat_e u_beate (.clk(clk), .rst_a(rst_n), .d(bm), .last(bout));
 hnx_rp4lp4_lfx u_lf0 (.clk(clk), .rst_n(rst_n), .st(st_n), .rl1(rl1_n), .bk1(bk1_n), .g(g0));
 hnx_rp4lp4_lfx u_lf1 (.clk(clk), .rst_n(rst_n), .st(st_s), .rl1(rl1_s), .bk1(bk1_s), .g(g1));
 hnx_rp4l_gn u_gn (.clk(clk), .rst_n(rst_n), .g0(g0), .gin(gin), .g0m(g0m), .gpm(gpm));
 hnx_rp4l_gs u_gs (.clk(clk), .rst_n(rst_n), .g1in(g1), .g0m(g0m), .gpm(gpm), .gout(gout));
endmodule
