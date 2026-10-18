// PL-SMT (PARENTS-LANDED, 10-18): the HBM SM tile rp4 (ot_hbm_smh_rp4_one) re-expressed as a WIRES-ONLY flat parent so
// tools/landed_parent/lp.py can build it as LANDED REGIONS (landed-regions-standard-1018).  Same hard children, same
// soft registers, same cycle counts as ot_hbm_smh_rp4_one; only the grouping changes:
//   * every soft register group (pin registers, x-store straps, leaf glue, gather relays) is a single-clock soft child;
//   * the 7-copy registered reset tree u_rt (uniform depth 5) is gone: lp.py's regional reset runs replace it, so
//     ot_hbm_smh_rp4_flat == ot_hbm_smh_rp4_one with its reset delayed 5 edges less (wrapper ot_hbm_smh_rp4_flat_one
//     restores the one-port interface and the 5-stage reset for the SM-level PQ bench);
//   * the row ports are split by region (rin_n = rin[817:0] pins y 1055-1282, rin_s = rin[1635:818] pins y 250-476,
//     rout likewise) because a port must belong to one region; ot_hbm_smh_rp4_lpt restores the original port names.
// Region plan (PL-SMT spec): N = leaf 0 + row 0 + the whole bin beat path (bin pins y 476-1055, beat_t, pte beat, land_n);
// S = leaf 1 + row 1 + land_s + the S-edge gather outputs.  Crossings: bin_l -> land_s (2,069 b), leaf-0 gather (50 b),
// pass-through gather (100 b).
`timescale 1ns/1ps
// THE FLAT PARENT (wires only: lp.py input)
module ot_hbm_smh_rp4_flat (input wire clk, input wire rst_n,
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
 ot_rp4l_strap u_sr_n (.clk(clk), .d({xs_g2, xs_a2, xs_g1, xs_a1}), .q(st_n));
 ot_rp4l_strap u_sr_s (.clk(clk), .d({xss_g2, xss_a2, xss_g1, xss_a1}), .q(st_s));
 ot_rp4l_pinrow u_pr_n (.clk(clk), .rst_n(rst_n), .d(rin_n), .q(rl_n));
 ot_rp4l_pinrow u_pr_s (.clk(clk), .rst_n(rst_n), .d(rin_s), .q(rl_s));
 ot_rp4l_pinbeat u_pb (.clk(clk), .rst_n(rst_n), .d(bin), .q(bin_l));
 ot_smh_tr_group_row_w u_row0 (.clk(clk), .rst_a(rst_n), .d(rl_n), .first(rl1_n), .last(rpm_n));
 ot_smh_tr_group_row_w u_row1 (.clk(clk), .rst_a(rst_n), .d(rl_s), .first(rl1_s), .last(rpm_s));
 ot_smh_tr_group_beat_e u_beat_t (.clk(clk), .rst_a(rst_n), .d(bin_l), .last(bm));
 ot_smh_tr_group_land u_land_n (.clk(clk), .rst_a(rst_n), .d(bin_l), .q(bk1_n));
 ot_smh_tr_group_land u_land_s (.clk(clk), .rst_a(rst_n), .d(bin_l), .q(bk1_s));
 ot_smh_tr_group_row_e u_rowe0 (.clk(clk), .rst_a(rst_n), .d(rpm_n), .last(rout_n));
 ot_smh_tr_group_row_e u_rowe1 (.clk(clk), .rst_a(rst_n), .d(rpm_s), .last(rout_s));
 ot_smh_tr_group_beat_e u_beate (.clk(clk), .rst_a(rst_n), .d(bm), .last(bout));
 ot_rp4l_leaf u_lf0 (.clk(clk), .rst_n(rst_n), .st(st_n), .rl1(rl1_n), .bk1(bk1_n), .g(g0));
 ot_rp4l_leaf u_lf1 (.clk(clk), .rst_n(rst_n), .st(st_s), .rl1(rl1_s), .bk1(bk1_s), .g(g1));
 ot_rp4l_gn u_gn (.clk(clk), .rst_n(rst_n), .g0(g0), .gin(gin), .g0m(g0m), .gpm(gpm));
 ot_rp4l_gs u_gs (.clk(clk), .rst_n(rst_n), .g1in(g1), .g0m(g0m), .gpm(gpm), .gout(gout));
endmodule
// Equivalence wrapper: the flat parent with ot_hbm_smh_rp4_one's ports and its 5-stage registered reset (u_rt depth),
// for the SM-level PQ bench (tools/hbm_sm_repack_1015/local_clock_lockstep.py --flat).
module ot_hbm_smh_rp4_flat_one #(parameter integer MUT_CLKDROP=0)(input wire clk,input wire rst_n,
 input wire[8:0]xs_a1,input wire[4:0]xs_g1,input wire[6:0]xs_a2,input wire[4:0]xs_g2,
 input wire[8:0]xss_a1,input wire[4:0]xss_g1,input wire[6:0]xss_a2,input wire[4:0]xss_g2,
 input wire[1635:0]rin,input wire[2068:0]bin,output wire[1635:0]rout,output wire[2068:0]bout,
 input wire[99:0]gin,output wire[199:0]gout);
 (*keep*)reg[4:0]rd;
 always @(posedge clk) rd<={rd[3:0],rst_n};
 ot_hbm_smh_rp4_flat u (.clk(clk), .rst_n(rd[4]), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2),
  .xss_a1(xss_a1), .xss_g1(xss_g1), .xss_a2(xss_a2), .xss_g2(xss_g2), .rin_n(rin[817:0]), .rin_s(rin[1635:818]), .bin(bin),
  .rout_n(rout[817:0]), .rout_s(rout[1635:818]), .bout(bout), .gin(gin), .gout(gout));
endmodule
// Functional proof wrapper (same ports as ot_hbm_smh_rp4_one_gated): the SM-level PQ bench runs the flat parent through
// tools/hbm_sm_repack_1015/local_clock_lockstep.py --flat (MUT_CLKDROP is accepted for interface parity and unused: the
// flat parent has one clock port; the landed parent's mutants are in the lp.py lockstep bench).
module ot_hbm_smh_rp4_flat_gated #(parameter integer MUT_CLKDROP=0)(
 input wire clk,rst_n,cgi,output wire cgo,input wire[17:0]xs_a1,input wire[9:0]xs_g1,
 input wire[13:0]xs_a2,input wire[9:0]xs_g2,input wire[1635:0]rin,input wire[2068:0]bin,
 output wire[1635:0]rout,output wire[2068:0]bout,input wire[99:0]gin,output wire[199:0]gout);
 wire gclk;
 ot_hbm_smh_rp4_one_dist u_clk(.clk_raw(clk),.rst_n(rst_n),.cgi(cgi),.cgo(cgo),.gclk(gclk));
 ot_hbm_smh_rp4_flat_one u_tile(.clk(gclk),.rst_n(rst_n),
  .xs_a1(xs_a1[8:0]),.xs_g1(xs_g1[4:0]),.xs_a2(xs_a2[6:0]),.xs_g2(xs_g2[4:0]),
  .xss_a1(xs_a1[17:9]),.xss_g1(xs_g1[9:5]),.xss_a2(xs_a2[13:7]),.xss_g2(xs_g2[9:5]),
  .rin(rin),.bin(bin),.rout(rout),.bout(bout),.gin(gin),.gout(gout));
endmodule
