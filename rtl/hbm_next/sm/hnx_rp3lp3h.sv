// HNX-SM4/SM4P (10-20, SAFE-DESIGN item 6: hnx_rp3lp3x is 630.72 x 2203.2 = 3.49:1): the SM P = 3 tile as TWO HARDENED
// HALVES, each <= 2:1 with ONE clock root, registered pins and the 2-stage reset landing (kit reset_landing):
//   hnx_rp3lp3h_n  (ck_n)  = lp region n of hnx_rp3lp3x_flat_lp: leaf 0, row 0, the bin beat path (pinbeat, beat_t,
//                            beat_e, land_n), N gather relays + the RING (writer) of the n->s gather landing.
//   hnx_rp3lp3h_s  (ck_s)  = lp region s: leaf 1, row 1, land_s fed by its OWN bin pin capture (the die fans the bin
//                            landing out to both halves on the same edge), the READ side of the gather landing, S gather.
// SEAM (N half S face <-> S half N face, abutted): only the gather landing crosses, 150 b (pass lanes gpm 100 b + leaf-0
// lane g0m 50 b) as ring banks 4 x 150 + 4 slot-valid bits (ot_pl_land_w in N beside the source, ot_pl_land_r in S beside
// the reader: LANDING-CONTRACT L1-L7, D 4, E = K = 2, +3 edges, fixed latency, no ready / credit / backpressure; ring
// slot epochs are simulation-only ports).  The flat lp's 2,069-b bin_l landing (4 dual-clock 16x546 SRAMs) and the
// rl1_s / st_s alignment pads (7 x 32x128 SRAMs + 26-b ring) are GONE: land_s now runs at t = 0 like the flat parent,
// and only the leaf-1 gather word g1 (50 b) is aligned by 3 edges (addressed flop ring, 150 b).
// COMPILER (static calendar, vs hnx_rp3lp3x_flat): every child t = 0 except u_gs t = 3; outputs rout_n / rout_s / bout
// +0, gout +3; reset release +2 (regional runs) -- IDENTICAL to the hnx_rp3lp3x_flat_lp record (no new cycle).
// DIE obligations: (1) bin delivered to BOTH halves on the same edge; (2) rst_n to both halves on the same edge (equal
// reset-run depth); (3) ck_n / ck_s are the slot's two regional roots (as for the flat lp tile); (4) the seam bank paths
// N.ring -> S.read are landed multicycles (-setup 2 -hold 3), constrained in the die / column STA.
// MUT (bench only; 0 in every kit): 1 = read K = 1 (one early), 2 = read K = 3 (one late), 3 = g1 pad one short,
//                                  4 = S bin capture bypassed (land_s one edge early)
`timescale 1ns/1ps

module hnx_rp3lp3h_n (
 input wire ck_n, input wire rst_n,
 input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
 input wire [817:0] rin_n, input wire [2068:0] bin, input wire [99:0] gin,
 output wire [817:0] rout_n, output wire [2068:0] bout,
 output wire [599:0] sb_bank, output wire [3:0] sb_vld
`ifndef SYNTHESIS
 , output wire [11:0] sb_epo
`endif
);
 wire [25:0] st_n;
 wire [817:0] rl_n, rl1_n, rpm_n;
 wire [2068:0] bin_l, bm, bk1_n;
 wire [49:0] g0, g0m;
 wire [99:0] gpm;
 wire [11:0] epo_w;
 // regional reset run, depth 2 (= lp region n: u_lpr_root, u_lpr_n)
 wire lpr_root; ot_pl_pad #(.W(1), .N(1)) u_lpr_root (.ck(ck_n), .d(rst_n), .q(lpr_root));
 wire lpr_n;    ot_pl_pad #(.W(1), .N(1)) u_lpr_n (.ck(ck_n), .d(lpr_root), .q(lpr_n));
 hnx_rp4l_strap u_sr_n (.clk(ck_n), .d({xs_g2, xs_a2, xs_g1, xs_a1}), .q(st_n));
 hnx_rp4l_pinrow u_pr_n (.clk(ck_n), .rst_n(lpr_n), .d(rin_n), .q(rl_n));
 hnx_rp4l_pinbeat u_pb (.clk(ck_n), .rst_n(lpr_n), .d(bin), .q(bin_l));
 ot_smh_tr_group_row_w u_row0 (.clk(ck_n), .rst_a(lpr_n), .d(rl_n), .first(rl1_n), .last(rpm_n));
 ot_smh_tr_group_beat_e u_beat_t (.clk(ck_n), .rst_a(lpr_n), .d(bin_l), .last(bm));
 ot_smh_tr_group_land u_land_n (.clk(ck_n), .rst_a(lpr_n), .d(bin_l), .q(bk1_n));
 ot_smh_tr_group_row_e u_rowe0 (.clk(ck_n), .rst_a(lpr_n), .d(rpm_n), .last(rout_n));
 ot_smh_tr_group_beat_e u_beate (.clk(ck_n), .rst_a(lpr_n), .d(bm), .last(bout));
 hnx_rp4lp4_lfx #(.P(3)) u_lf0 (.clk(ck_n), .rst_n(lpr_n), .st(st_n), .rl1(rl1_n), .bk1(bk1_n), .g(g0));
 hnx_rp4l_gn #(.NREL(2)) u_gn (.clk(ck_n), .rst_n(lpr_n), .g0(g0), .gin(gin), .g0m(g0m), .gpm(gpm));
 // seam landing RING (source side, beside the gather mid stage): banks + slot valids drive the S-face pins directly
 ot_pl_land_w #(.W(150), .D(4)) u_sb_w (.ck(ck_n), .rsi(lpr_n), .i({gpm, g0m}), .bank(sb_bank), .epo(epo_w), .vld(sb_vld));
`ifndef SYNTHESIS
 assign sb_epo = epo_w;
`endif
endmodule

module hnx_rp3lp3h_s #(parameter integer MUT = 0) (
 input wire ck_s, input wire rst_n,
 input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2,
 input wire [817:0] rin_s, input wire [2068:0] bin,
 input wire [599:0] sb_bank, input wire [3:0] sb_vld,
`ifndef SYNTHESIS
 input wire [11:0] sb_epo,
`endif
 output wire [817:0] rout_s, output wire [199:0] gout
);
 wire [25:0] st_s;
 wire [817:0] rl_s, rl1_s, rpm_s;
 wire [2068:0] bin_s, bin_c, bk1_s;
 wire [49:0] g1, g1p;
 wire [149:0] sb_o;
 wire [11:0] epo_r;
`ifndef SYNTHESIS
 assign epo_r = sb_epo;
`else
 assign epo_r = 12'd0;          // slot epochs are assertion-only (ot_pl_land_r reads them only outside SYNTHESIS)
`endif
 // regional reset run, depth 2 (= lp region s), + t(u_gs) = 3
 wire lpr_root; ot_pl_pad #(.W(1), .N(1)) u_lpr_root (.ck(ck_s), .d(rst_n), .q(lpr_root));
 wire lpr_s;    ot_pl_pad #(.W(1), .N(1)) u_lpr_s (.ck(ck_s), .d(lpr_root), .q(lpr_s));
 wire lpr_c_u_gs; ot_pl_pad #(.W(1), .N(3)) u_lprc_u_gs (.ck(ck_s), .d(lpr_s), .q(lpr_c_u_gs));
 hnx_rp4l_strap u_sr_s (.clk(ck_s), .d({xss_g2, xss_a2, xss_g1, xss_a1}), .q(st_s));
 hnx_rp4l_pinrow u_pr_s (.clk(ck_s), .rst_n(lpr_s), .d(rin_s), .q(rl_s));
 // the S half's OWN bin pin capture (as u_pb in N): land_s sees bin at the same edge as the flat parent's bin_l
 hnx_rp4l_pinbeat u_pbs (.clk(ck_s), .rst_n(lpr_s), .d(bin), .q(bin_c));
 assign bin_s = (MUT == 4) ? bin : bin_c;
 ot_smh_tr_group_row_w u_row1 (.clk(ck_s), .rst_a(lpr_s), .d(rl_s), .first(rl1_s), .last(rpm_s));
 ot_smh_tr_group_land u_land_s (.clk(ck_s), .rst_a(lpr_s), .d(bin_s), .q(bk1_s));
 ot_smh_tr_group_row_e u_rowe1 (.clk(ck_s), .rst_a(lpr_s), .d(rpm_s), .last(rout_s));
 hnx_rp4lp4_lfx #(.P(3)) u_lf1 (.clk(ck_s), .rst_n(lpr_s), .st(st_s), .rl1(rl1_s), .bk1(bk1_s), .g(g1));
 // seam landing READ (destination side, beside the gather read stage): +3 edges (E + 1)
 ot_pl_land_r #(.W(150), .D(4), .K((MUT == 1) ? 1 : (MUT == 2) ? 3 : 2)) u_sb_r (.ck(ck_s), .rsi(lpr_s), .bank(sb_bank), .epo(epo_r),
  .vld(sb_vld), .o(sb_o));
 // leaf-1 gather word aligned to t(u_gs) = 3: addressed flop ring (150 b < 2 kb, no shift chain)
 hnx_pl_pad_ring #(.W(50), .N((MUT == 3) ? 2 : 3)) u_lpp_g1 (.ck(ck_s), .rst_n(lpr_s), .d(g1), .q(g1p));
 hnx_rp4l_gs #(.NREL(2)) u_gs (.clk(ck_s), .rst_n(lpr_c_u_gs), .g1in(g1p), .g0m(sb_o[49:0]), .gpm(sb_o[149:50]), .gout(gout));
endmodule

// Composition of the two halves in the DIE slot (bench / die-integration reference; wires only): N above S, abutted;
// bin fanned to both halves (die obligation 1), one rst_n (obligation 2).  Same ports as hnx_rp3lp3x_flat_lp.
module hnx_rp3lp3x_halves #(parameter integer MUT = 0) (
 input wire rst_n, input wire ck_n, input wire ck_s,
 input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
 input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2,
 input wire [817:0] rin_n, input wire [817:0] rin_s, input wire [2068:0] bin,
 output wire [817:0] rout_n, output wire [817:0] rout_s, output wire [2068:0] bout,
 input wire [99:0] gin, output wire [199:0] gout
);
 wire [599:0] sb_bank;
 wire [3:0] sb_vld;
`ifndef SYNTHESIS
 wire [11:0] sb_epo;
`endif
 hnx_rp3lp3h_n u_hn (.ck_n(ck_n), .rst_n(rst_n), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2),
  .rin_n(rin_n), .bin(bin), .gin(gin), .rout_n(rout_n), .bout(bout), .sb_bank(sb_bank), .sb_vld(sb_vld)
`ifndef SYNTHESIS
  , .sb_epo(sb_epo)
`endif
 );
 hnx_rp3lp3h_s #(.MUT(MUT)) u_hs (.ck_s(ck_s), .rst_n(rst_n), .xss_a1(xss_a1), .xss_g1(xss_g1), .xss_a2(xss_a2), .xss_g2(xss_g2),
  .rin_s(rin_s), .bin(bin), .sb_bank(sb_bank), .sb_vld(sb_vld),
`ifndef SYNTHESIS
  .sb_epo(sb_epo),
`endif
  .rout_s(rout_s), .gout(gout));
endmodule
