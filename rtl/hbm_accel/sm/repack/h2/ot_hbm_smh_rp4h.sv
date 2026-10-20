// L2H-SM9 (LEAD2-HBM, 10-19; RELEASE_TREE H.STA.BLK.9): the HBM SM tile rp4 as TWO HARDENED HALVES.
//
// Why (safe-design review of smh_tile_rp4lp, owner checklist 10-19): the landed one-tile parent was 457.92 x 1598.4
// (aspect 3.49), 13/18 child macros off the 43.2 um lattice, and its 2,069-b n->s landing read mux hung on one read
// counter (u_lpl_0_r rc[1] 8,284 loads, rc[0] 4,145; ring write enables 4,140) -- gate 1 GRT overflow 51,363, gate 2
// CTS rc 2.  Structural successor: the two lp regions become two hardened tiles that abut in the SM frame slot:
//   ot_hbm_smh_rp4h_n = leaf 0 + row 0 (row_w / row_e) + the whole bin beat path (pin flops, beat_t, pte beat, land_n)
//                       + the N gather relays (lp region n), one clock root;
//   ot_hbm_smh_rp4h_s = leaf 1 + row 1 + land_s + the S gather outputs (lp region s), one clock root.
// The n->s crossing is a plain registered tile-to-tile link (out pin register on n's S face, in pin register on s's N
// face, < 50 um apart), judged at die level per linked child-flop pair (neighbour-matched boundary, owner 10-17 clock
// rule) instead of a 4-slot landing: no ring bank, no read mux, no read counter -> no high-fanout select at all.
// LATENCY IS IDENTICAL TO THE PRICED LANDED PARENT (results/arch/landed_parent_1018/pl_smt/ot_hbm_smh_rp4_flat_lp_record
// .json): every n->s lane keeps +3 edges --
//   bin_l -> bk1_s    : n relays u_xb1 / u_xb2 (keep every hop < 405 um from the W-face pin flops) + n out u_xbo + the s
//                       landing register u_lands (= s's N-face input pin register; replaces land_s.d -> land_s.q)
//   g0m / gpm -> gs   : n out u_xgo / u_xpo + s in u_xgi / u_xpi + s relay u_xg2 / u_xp2 (mid of s, toward the S face)
// and the leaf-1 alignment pads (rl1_s, st_s: 3 stages) and reset depths are the lp ones (n children 3, s row/pin
// children 3, land_s / leaf 1 / gs 6), so ot_hbm_smh_rp4h2 == ot_hbm_smh_rp4_flat_lp cycle for cycle and the compiler
// record (gout +3 on all 4 lanes, all other ports 0) is unchanged.
// The two hard 216 x 43.2 landing children (ot_smh_tr_group_land: ONE register stage, valid bit reset) become SOFT kept
// registers (u_landn / u_lands, same edge, same valid-bit clear): the placer spreads them under the x store's 300-um bk1
// face, so the 818-b rl1 bus from row_w no longer has to cross a hard macro to reach the x store (the gate-1 M6 overflow
// at the W macro column) and the macro stack fits the 43.2 lattice in <= 2:1 halves.
// Reset: rst_n lands in 2 kept registers at the face (reset_landing), then one kept copy per consumer (<= ~10 loads
// each); the s half's land_s / leaf 1 / gs copies carry the lp +3.
// MUT (bench only, 0 in every kit): 1 = bin crossing one stage short (n relay u_xb2 bypassed), 2 = gpm crossing one stage
// short (s relay bypassed), 3 = leaf-1 rl1 pad one stage short (4 = s landing reset copy one short: not observable, reset only
// clears valids, as lp MUT4; not benched).
`timescale 1ns/1ps

// reset landing: two kept stages at the face, then NC kept copies (one per consumer) -> depth 3
module ot_rp4h_rst #(parameter integer NC = 8) (input wire clk, input wire rst_n, output wire [NC-1:0] r);
    (* keep *) reg l0, l1;
    (* keep *) reg [NC-1:0] c;
    always @(posedge clk) begin l0 <= rst_n; l1 <= l0; c <= {NC{l1}}; end
    assign r = c;
endmodule

// kept delay of N stages on one reset copy (lp t(child) pads)
module ot_rp4h_rpad #(parameter integer N = 3) (input wire clk, input wire d, output wire q);
    (* keep *) reg [N-1:0] p;
    always @(posedge clk) p <= {p[N-2:0], d};
    assign q = p[N-1];
endmodule

// crossing register: valid bits (positions VLO.., NV wide groups given by mask) sync-cleared, data plain
module ot_rp4h_xreg #(parameter integer W = 8, parameter [W-1:0] VMASK = 0) (
    input wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q);
    (* keep *) reg [W-1:0] r;
    integer i;
    always @(posedge clk)
        for (i = 0; i < W; i = i + 1)
            if (VMASK[i] && !rst_n) r[i] <= 1'b0; else r[i] <= d[i];
    assign q = r;
endmodule

module ot_hbm_smh_rp4h_n #(parameter integer MUT = 0) (
    input wire clk, input wire rst_n,
    input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
    input wire [817:0] rin_n, input wire [2068:0] bin, input wire [99:0] gin,
    output wire [817:0] rout_n, output wire [2068:0] bout,
    output wire [2068:0] xo_b, output wire [49:0] xo_g0, output wire [99:0] xo_gp
);
    wire [10:0] r;
    ot_rp4h_rst #(.NC(11)) u_rst (.clk(clk), .rst_n(rst_n), .r(r));
    wire [25:0] st_n;
    wire [817:0] rl_n, rl1_n, rpm_n;
    wire [2068:0] bin_l, bm, bk1_n, xb1, xb2;
    wire [49:0] g0, g0m;
    wire [99:0] gpm;
    ot_rp4l_strap u_sr_n (.clk(clk), .d({xs_g2, xs_a2, xs_g1, xs_a1}), .q(st_n));
    ot_rp4l_pinrow u_pr_n (.clk(clk), .rst_n(r[0]), .d(rin_n), .q(rl_n));
    ot_rp4l_pinbeat u_pb (.clk(clk), .rst_n(r[1]), .d(bin), .q(bin_l));
    ot_smh_tr_group_row_w u_row0 (.clk(clk), .rst_a(r[2]), .d(rl_n), .first(rl1_n), .last(rpm_n));
    ot_smh_tr_group_beat_e u_beat_t (.clk(clk), .rst_a(r[3]), .d(bin_l), .last(bm));
    ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_landn (.clk(clk), .rst_n(r[4]), .d(bin_l), .q(bk1_n));
    ot_smh_tr_group_row_e u_rowe0 (.clk(clk), .rst_a(r[5]), .d(rpm_n), .last(rout_n));
    ot_smh_tr_group_beat_e u_beate (.clk(clk), .rst_a(r[6]), .d(bm), .last(bout));
    ot_rp4l_leaf u_lf0 (.clk(clk), .rst_n(r[7]), .st(st_n), .rl1(rl1_n), .bk1(bk1_n), .g(g0));
    ot_rp4l_gn u_gn (.clk(clk), .rst_n(r[8]), .g0(g0), .gin(gin), .g0m(g0m), .gpm(gpm));
    // n -> s crossing (lp +3 split: bin 3 here + the s landing register; gather 1 here + 2 in s)
    ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_xb1 (.clk(clk), .rst_n(r[9]), .d(bin_l), .q(xb1));
    generate if (MUT == 1) begin : g_m1
        assign xb2 = xb1;
    end else begin : g_xb2
        ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_xb2 (.clk(clk), .rst_n(r[9]), .d(xb1), .q(xb2));
    end endgenerate
    ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_xbo (.clk(clk), .rst_n(r[9]), .d(xb2), .q(xo_b));
    ot_rp4h_xreg #(.W(50), .VMASK({2'b11, 48'b0})) u_xgo (.clk(clk), .rst_n(r[10]), .d(g0m), .q(xo_g0));
    ot_rp4h_xreg #(.W(100), .VMASK({2'b11, 48'b0, 2'b11, 48'b0})) u_xpo (.clk(clk), .rst_n(r[10]), .d(gpm), .q(xo_gp));
endmodule

module ot_hbm_smh_rp4h_s #(parameter integer MUT = 0) (
    input wire clk, input wire rst_n,
    input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2,
    input wire [817:0] rin_s, output wire [817:0] rout_s,
    input wire [2068:0] xi_b, input wire [49:0] xi_g0, input wire [99:0] xi_gp,
    output wire [199:0] gout
);
    wire [7:0] r;
    ot_rp4h_rst #(.NC(8)) u_rst (.clk(clk), .rst_n(rst_n), .r(r));
    // lp t(child) = 3 for land_s, leaf 1, gs
    wire r_land, r_lf1, r_gs;
    ot_rp4h_rpad #(.N((MUT == 4) ? 2 : 3)) u_rp_land (.clk(clk), .d(r[3]), .q(r_land));
    ot_rp4h_rpad #(.N(3)) u_rp_lf1 (.clk(clk), .d(r[4]), .q(r_lf1));
    ot_rp4h_rpad #(.N(3)) u_rp_gs (.clk(clk), .d(r[5]), .q(r_gs));
    wire [25:0] st_s, st_s_p;
    wire [817:0] rl_s, rl1_s, rl1_s_p, rpm_s;
    wire [2068:0] bk1_s;
    wire [49:0] g1, xg, g0m;
    wire [99:0] xp, gpm;
    // in pin registers (N face) and s relays
    ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_lands (.clk(clk), .rst_n(r_land), .d(xi_b), .q(bk1_s));
    ot_rp4h_xreg #(.W(50), .VMASK({2'b11, 48'b0})) u_xgi (.clk(clk), .rst_n(r[6]), .d(xi_g0), .q(xg));
    ot_rp4h_xreg #(.W(50), .VMASK({2'b11, 48'b0})) u_xg2 (.clk(clk), .rst_n(r[6]), .d(xg), .q(g0m));
    ot_rp4h_xreg #(.W(100), .VMASK({2'b11, 48'b0, 2'b11, 48'b0})) u_xpi (.clk(clk), .rst_n(r[7]), .d(xi_gp), .q(xp));
    wire [99:0] xp2;
    ot_rp4h_xreg #(.W(100), .VMASK({2'b11, 48'b0, 2'b11, 48'b0})) u_xp2 (.clk(clk), .rst_n(r[7]), .d(xp), .q(xp2));
    assign gpm = (MUT == 2) ? xp : xp2;
    ot_rp4l_strap u_sr_s (.clk(clk), .d({xss_g2, xss_a2, xss_g1, xss_a1}), .q(st_s));
    ot_rp4l_pinrow u_pr_s (.clk(clk), .rst_n(r[0]), .d(rin_s), .q(rl_s));
    ot_smh_tr_group_row_w u_row1 (.clk(clk), .rst_a(r[1]), .d(rl_s), .first(rl1_s), .last(rpm_s));
    ot_smh_tr_group_row_e u_rowe1 (.clk(clk), .rst_a(r[2]), .d(rpm_s), .last(rout_s));
    // leaf-1 alignment pads (lp u_lpp_0 / u_lpp_1: +3)
    ot_pl_pad #(.W(818), .N((MUT == 3) ? 2 : 3)) u_pp_rl1 (.ck(clk), .d(rl1_s), .q(rl1_s_p));
    ot_pl_pad #(.W(26), .N(3)) u_pp_st (.ck(clk), .d(st_s), .q(st_s_p));
    ot_rp4l_leaf u_lf1 (.clk(clk), .rst_n(r_lf1), .st(st_s_p), .rl1(rl1_s_p), .bk1(bk1_s), .g(g1));
    ot_rp4l_gs u_gs (.clk(clk), .rst_n(r_gs), .g1in(g1), .g0m(g0m), .gpm(gpm), .gout(gout));
endmodule

// the SM frame slot: both halves abutted (die binder form; also the bench DUT). Port names = ot_hbm_smh_rp4_flat_lp.
module ot_hbm_smh_rp4h2 #(parameter integer MUT = 0) (
    input wire rst_n,
    input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
    input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2,
    input wire [817:0] rin_n, input wire [817:0] rin_s, input wire [2068:0] bin,
    output wire [817:0] rout_n, output wire [817:0] rout_s, output wire [2068:0] bout,
    input wire [99:0] gin, output wire [199:0] gout,
    input wire ck_n, input wire ck_s
);
    wire [2068:0] x_b; wire [49:0] x_g0; wire [99:0] x_gp;
    ot_hbm_smh_rp4h_n #(.MUT(MUT)) u_n (.clk(ck_n), .rst_n(rst_n), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2),
        .rin_n(rin_n), .bin(bin), .gin(gin), .rout_n(rout_n), .bout(bout), .xo_b(x_b), .xo_g0(x_g0), .xo_gp(x_gp));
    ot_hbm_smh_rp4h_s #(.MUT(MUT)) u_s (.clk(ck_s), .rst_n(rst_n), .xss_a1(xss_a1), .xss_g1(xss_g1), .xss_a2(xss_a2), .xss_g2(xss_g2),
        .rin_s(rin_s), .rout_s(rout_s), .xi_b(x_b), .xi_g0(x_g0), .xi_gp(x_gp), .gout(gout));
endmodule
