// HBM-NEXT-P3-SM (10-19, OWNER decision 0le: next-release HBM die = P = 3 + SHARED 3-lane x store, "P3+(a)"): the SM matrix
// tile hnx_rp3lp3x.  Same ports, pin widths, transport hard children and landed regions as hnx_rp4lp4x (rtl/hbm_next/sm/
// hnx_rp4lp4.sv, PROG lever (a)); the P-generic leaf hnx_rp4lp4_lfx runs at P = 3 (no logic fork): per leaf ONE hnx_xs3
// (hnx_xs4's generator at P = 3, 3 lane SRAM sets, face split N block-dot / W lanes 0-1 / E lane 2), per lane the d4g
// block-dot column + BF16 column (CLOSED views) and the slot-major publish (lane p at +p*LSKEW, LSKEW = IL = 8, ring-buffer
// delays).  P = 3 protocol (compiler): lane-select beat data[2:0] = x target mask, data[10:8] = active-lane mask; a row
// chunk must be >= P*IL = 24 cycles apart (K >= 3 beats per interleaved chunk; production K >= 4), else gf = collision.
// REACH (safe-design item 2, tile ~2.2 mm tall in the DIE SM slot): NREL = 2 extra gather relays per half (N edge -> mid,
// mid -> S edge, leaf 0 -> mid) so no gather hop exceeds ~365 um.  Compiler latency vs hnx_rp4lp4x: gout pass lanes
// (gin -> gout) +4 edges, leaf-0 lane +4, leaf-1 lane +0; every other port offset as hnx_rp4lp4x (lp record).
`timescale 1ns/1ps

module hnx_rp3lp3x_flat (input wire clk, input wire rst_n,
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
 hnx_rp4lp4_lfx #(.P(3)) u_lf0 (.clk(clk), .rst_n(rst_n), .st(st_n), .rl1(rl1_n), .bk1(bk1_n), .g(g0));
 hnx_rp4lp4_lfx #(.P(3)) u_lf1 (.clk(clk), .rst_n(rst_n), .st(st_s), .rl1(rl1_s), .bk1(bk1_s), .g(g1));
 hnx_rp4l_gn #(.NREL(2)) u_gn (.clk(clk), .rst_n(rst_n), .g0(g0), .gin(gin), .g0m(g0m), .gpm(gpm));
 hnx_rp4l_gs #(.NREL(2)) u_gs (.clk(clk), .rst_n(rst_n), .g1in(g1), .g0m(g0m), .gpm(gpm), .gout(gout));
endmodule
