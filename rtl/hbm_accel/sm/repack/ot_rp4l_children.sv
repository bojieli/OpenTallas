// PL-SMT soft children of ot_hbm_smh_rp4_flat (see ot_hbm_smh_rp4_flat.sv)
`timescale 1ns/1ps
`ifndef OT_RP4_RK
`define OT_RP4_RK 2
`endif
// x-store strap: five stages on the leaf's own region (as ot_hbm_smh_rp4_strap, one clock)
module ot_rp4l_strap(input wire clk, input wire [25:0] d, output wire [25:0] q);
 (*keep*)reg[25:0]s0,s1,s2,s3,s4;
 always @(posedge clk)begin s0<=d;s1<=s0;s2<=s1;s3<=s2;s4<=s3;end
 assign q=s4;
endmodule
// row-bundle pin register (as core g_pin[pj].u_r)
module ot_rp4l_pinrow(input wire clk, input wire rst_n, input wire [817:0] d, output wire [817:0] q);
 ot_hbm_accel_smh_bundle_reg #(.W(818), .V(20), .NV(2), .X(7), .RSTK(`OT_RP4_RK)) u_r (.clk(clk), .rst_n(rst_n), .d(d), .q(q));
endmodule
// x-write beat pin register (as core u_pbv + u_pbd)
module ot_rp4l_pinbeat(input wire clk, input wire rst_n, input wire [2068:0] d, output wire [2068:0] q);
 ot_hbm_accel_smh_kreg #(.W(1), .RST(`OT_RP4_RK)) u_pbv (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(d[2068]), .q(q[2068]));
 ot_hbm_accel_smh_kreg #(.W(2068)) u_pbd (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(d[2067:0]), .q(q[2067:0]));
endmodule
// one leaf (x store, block-dot column, BF16 columns, G1 select) on one clock; g = {gv, gf, gy, gt}
module ot_rp4l_leaf(input wire clk, input wire rst_n, input wire [25:0] st, input wire [817:0] rl1,
 input wire [2068:0] bk1, output wire [49:0] g);
 wire gv, gf; wire [31:0] gy; wire [15:0] gt;
 ot_hbm_smh_rp4_leafh u_lh (.clk(clk), .clk_xb(clk), .clk_xf(clk), .clk_hard({5{clk}}), .rst_n(rst_n),
  .xs_a1(st[8:0]), .xs_g1(st[13:9]), .xs_a2(st[20:14]), .xs_g2(st[25:21]), .rl1(rl1), .bk1(bk1), .ohl1(bk1[2060:2048]),
  .gv(gv), .gf(gf), .gy(gy), .gt(gt));
 assign g = {gv, gf, gy, gt};
endmodule
// N-band gather relays: leaf 0's own-row lane (u_grv1/u_grd1 at the leaf, u_grv2/u_grd2 mid-tile) and the two
// pass-through lanes' first two registers (u_v/u_d at the N edge, u_v2/u_d2 mid-tile)
module ot_rp4l_gn(input wire clk, input wire rst_n, input wire [49:0] g0, input wire [99:0] gin,
 output wire [49:0] g0m, output wire [99:0] gpm);
 wire [49:0] g1;
 ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_grv1 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g0[49:48]), .q(g1[49:48]));
 ot_hbm_accel_smh_kreg #(.W(48)) u_grd1 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g0[47:0]), .q(g1[47:0]));
 ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_grv2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1[49:48]), .q(g0m[49:48]));
 ot_hbm_accel_smh_kreg #(.W(48)) u_grd2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1[47:0]), .q(g0m[47:0]));
 genvar k;
 for (k = 0; k < 2; k = k + 1) begin : g_gl
  wire [49:0] gm;
  ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_v (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gin[k*50+48 +: 2]), .q(gm[49:48]));
  ot_hbm_accel_smh_kreg #(.W(48)) u_d (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gin[k*50 +: 48]), .q(gm[47:0]));
  ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_v2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gm[49:48]), .q(gpm[k*50+48 +: 2]));
  ot_hbm_accel_smh_kreg #(.W(48)) u_d2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gm[47:0]), .q(gpm[k*50 +: 48]));
 end
endmodule
// S-band gather: leaf 1's own-row lane (g1, g2 at the leaf), every lane's S-edge output register (u_gov/u_god,
// u_v3/u_d3).  gout lane order as core: leaf j -> gout[(1-j)*50 +: 50], pass lane k -> gout[(2+k)*50 +: 50].
module ot_rp4l_gs(input wire clk, input wire rst_n, input wire [49:0] g1in, input wire [49:0] g0m, input wire [99:0] gpm,
 output wire [199:0] gout);
 wire [49:0] g1, g2;
 ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_grv1 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1in[49:48]), .q(g1[49:48]));
 ot_hbm_accel_smh_kreg #(.W(48)) u_grd1 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1in[47:0]), .q(g1[47:0]));
 ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_grv2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1[49:48]), .q(g2[49:48]));
 ot_hbm_accel_smh_kreg #(.W(48)) u_grd2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1[47:0]), .q(g2[47:0]));
 ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_gov1 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g2[49:48]), .q(gout[48 +: 2]));
 ot_hbm_accel_smh_kreg #(.W(48)) u_god1 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g2[47:0]), .q(gout[0 +: 48]));
 ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_gov0 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g0m[49:48]), .q(gout[98 +: 2]));
 ot_hbm_accel_smh_kreg #(.W(48)) u_god0 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g0m[47:0]), .q(gout[50 +: 48]));
 genvar k;
 for (k = 0; k < 2; k = k + 1) begin : g_gl
  wire [49:0] pass;
`ifdef OT_SMH_G1_CAPTURE
  // Match the added leaf G1 capture edge on both through lanes. All four
  // gout lanes therefore retain one uniform +4 age relative to flat legacy.
  ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_cap_v (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gpm[k*50+48 +: 2]), .q(pass[49:48]));
  ot_hbm_accel_smh_kreg #(.W(48)) u_cap_d (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gpm[k*50 +: 48]), .q(pass[47:0]));
`else
  assign pass = gpm[k*50 +: 50];
`endif
  ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_v3 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(pass[48 +: 2]), .q(gout[(2+k)*50+48 +: 2]));
  ot_hbm_accel_smh_kreg #(.W(48)) u_d3 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(pass[0 +: 48]), .q(gout[(2+k)*50 +: 48]));
 end
endmodule
