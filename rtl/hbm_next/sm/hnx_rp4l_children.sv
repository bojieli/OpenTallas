// HBM-NEXT-SM4 (10-19): COPY of claude/pl-smt-1018 2444d768c rtl/hbm_accel/sm/repack/ot_rp4l_children.sv (soft children of the rp4
// landed tile), modules renamed ot_rp4l_* -> hnx_rp4l_*; ot_rp4l_leaf is replaced by the P-lane leaf hnx_rp4lp4_lf (hnx_rp4lp4.sv).
// PL-SMT soft children of ot_hbm_smh_rp4_flat (see ot_hbm_smh_rp4_flat.sv)
`timescale 1ns/1ps
`ifndef OT_RP4_RK
`define OT_RP4_RK 2
`endif
// x-store strap: five stages on the leaf's own region (as ot_hbm_smh_rp4_strap, one clock)
module hnx_rp4l_strap(input wire clk, input wire [25:0] d, output wire [25:0] q);
 (*keep*)reg[25:0]s0,s1,s2,s3,s4;
 always @(posedge clk)begin s0<=d;s1<=s0;s2<=s1;s3<=s2;s4<=s3;end
 assign q=s4;
endmodule
// row-bundle pin register (as core g_pin[pj].u_r)
module hnx_rp4l_pinrow(input wire clk, input wire rst_n, input wire [817:0] d, output wire [817:0] q);
 hnx_rp4l_bundle_reg #(.W(818), .V(20), .NV(2), .X(7), .RSTK(`OT_RP4_RK)) u_r (.clk(clk), .rst_n(rst_n), .d(d), .q(q));
endmodule
// x-write beat pin register (as core u_pbv + u_pbd)
module hnx_rp4l_pinbeat(input wire clk, input wire rst_n, input wire [2068:0] d, output wire [2068:0] q);
 hnx_rp4l_kreg #(.W(1), .RST(`OT_RP4_RK)) u_pbv (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(d[2068]), .q(q[2068]));
 hnx_rp4l_kreg #(.W(2068)) u_pbd (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(d[2067:0]), .q(q[2067:0]));
endmodule
// N-band gather relays: leaf 0's own-row lane (u_grv1/u_grd1 at the leaf, u_grv2/u_grd2 mid-tile) and the two
// pass-through lanes' first two registers (u_v/u_d at the N edge, u_v2/u_d2 mid-tile)
// NREL (P3-SM 10-19, safe-design item 2 reach <= 405 um): extra relay stages on the N-edge -> mid hop of every pass lane
// (g_gl[k].g_rl[r]) and on leaf 0's leaf -> mid hop (g_ro[r]); +NREL edges on those lanes (compiler record).  0 = SM4 / rp4lp.
module hnx_rp4l_gn #(parameter integer NREL = 0) (input wire clk, input wire rst_n, input wire [49:0] g0, input wire [99:0] gin,
 output wire [49:0] g0m, output wire [99:0] gpm);
 wire [49:0] g1;
 wire [(NREL+1)*50-1:0] g1c;
 hnx_rp4l_kreg #(.W(2), .RST(`OT_RP4_RK)) u_grv1 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g0[49:48]), .q(g1[49:48]));
 hnx_rp4l_kreg #(.W(48)) u_grd1 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g0[47:0]), .q(g1[47:0]));
 assign g1c[49:0] = g1;
 genvar r;
 for (r = 0; r < NREL; r = r + 1) begin : g_ro
  hnx_rp4l_kreg #(.W(2), .RST(`OT_RP4_RK)) u_rv (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1c[r*50+48 +: 2]), .q(g1c[(r+1)*50+48 +: 2]));
  hnx_rp4l_kreg #(.W(48)) u_rd (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1c[r*50 +: 48]), .q(g1c[(r+1)*50 +: 48]));
 end
 hnx_rp4l_kreg #(.W(2), .RST(`OT_RP4_RK)) u_grv2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1c[NREL*50+48 +: 2]), .q(g0m[49:48]));
 hnx_rp4l_kreg #(.W(48)) u_grd2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1c[NREL*50 +: 48]), .q(g0m[47:0]));
 genvar k;
 for (k = 0; k < 2; k = k + 1) begin : g_gl
  wire [49:0] gm;
  wire [(NREL+1)*50-1:0] gc;
  hnx_rp4l_kreg #(.W(2), .RST(`OT_RP4_RK)) u_v (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gin[k*50+48 +: 2]), .q(gm[49:48]));
  hnx_rp4l_kreg #(.W(48)) u_d (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gin[k*50 +: 48]), .q(gm[47:0]));
  assign gc[49:0] = gm;
  for (r = 0; r < NREL; r = r + 1) begin : g_rl
   hnx_rp4l_kreg #(.W(2), .RST(`OT_RP4_RK)) u_rv (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gc[r*50+48 +: 2]), .q(gc[(r+1)*50+48 +: 2]));
   hnx_rp4l_kreg #(.W(48)) u_rd (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gc[r*50 +: 48]), .q(gc[(r+1)*50 +: 48]));
  end
  hnx_rp4l_kreg #(.W(2), .RST(`OT_RP4_RK)) u_v2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gc[NREL*50+48 +: 2]), .q(gpm[k*50+48 +: 2]));
  hnx_rp4l_kreg #(.W(48)) u_d2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gc[NREL*50 +: 48]), .q(gpm[k*50 +: 48]));
 end
endmodule
// S-band gather: leaf 1's own-row lane (g1, g2 at the leaf), every lane's S-edge output register (u_gov/u_god,
// u_v3/u_d3).  gout lane order as core: leaf j -> gout[(1-j)*50 +: 50], pass lane k -> gout[(2+k)*50 +: 50].
// NREL (P3-SM 10-19, reach <= 405 um): extra relay stages on the mid -> S-edge hop of every pass lane (g_gl[k].g_rl[r]) and of
// leaf 0's lane (g_ro[r]); leaf 1's own lane is inside the S half already (unchanged).  0 = SM4 / rp4lp.
module hnx_rp4l_gs #(parameter integer NREL = 0) (input wire clk, input wire rst_n, input wire [49:0] g1in, input wire [49:0] g0m,
 input wire [99:0] gpm, output wire [199:0] gout);
 wire [49:0] g1, g2;
 wire [(NREL+1)*50-1:0] g0c;
 hnx_rp4l_kreg #(.W(2), .RST(`OT_RP4_RK)) u_grv1 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1in[49:48]), .q(g1[49:48]));
 hnx_rp4l_kreg #(.W(48)) u_grd1 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1in[47:0]), .q(g1[47:0]));
 hnx_rp4l_kreg #(.W(2), .RST(`OT_RP4_RK)) u_grv2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1[49:48]), .q(g2[49:48]));
 hnx_rp4l_kreg #(.W(48)) u_grd2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1[47:0]), .q(g2[47:0]));
 hnx_rp4l_kreg #(.W(2), .RST(`OT_RP4_RK)) u_gov1 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g2[49:48]), .q(gout[48 +: 2]));
 hnx_rp4l_kreg #(.W(48)) u_god1 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g2[47:0]), .q(gout[0 +: 48]));
 assign g0c[49:0] = g0m;
 genvar r;
 for (r = 0; r < NREL; r = r + 1) begin : g_ro
  hnx_rp4l_kreg #(.W(2), .RST(`OT_RP4_RK)) u_rv (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g0c[r*50+48 +: 2]), .q(g0c[(r+1)*50+48 +: 2]));
  hnx_rp4l_kreg #(.W(48)) u_rd (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g0c[r*50 +: 48]), .q(g0c[(r+1)*50 +: 48]));
 end
 hnx_rp4l_kreg #(.W(2), .RST(`OT_RP4_RK)) u_gov0 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g0c[NREL*50+48 +: 2]), .q(gout[98 +: 2]));
 hnx_rp4l_kreg #(.W(48)) u_god0 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g0c[NREL*50 +: 48]), .q(gout[50 +: 48]));
 genvar k;
 for (k = 0; k < 2; k = k + 1) begin : g_gl
  wire [(NREL+1)*50-1:0] gc;
  assign gc[49:0] = gpm[k*50 +: 50];
  for (r = 0; r < NREL; r = r + 1) begin : g_rl
   hnx_rp4l_kreg #(.W(2), .RST(`OT_RP4_RK)) u_rv (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gc[r*50+48 +: 2]), .q(gc[(r+1)*50+48 +: 2]));
   hnx_rp4l_kreg #(.W(48)) u_rd (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gc[r*50 +: 48]), .q(gc[(r+1)*50 +: 48]));
  end
  hnx_rp4l_kreg #(.W(2), .RST(`OT_RP4_RK)) u_v3 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gc[NREL*50+48 +: 2]), .q(gout[(2+k)*50+48 +: 2]));
  hnx_rp4l_kreg #(.W(48)) u_d3 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gc[NREL*50 +: 48]), .q(gout[(2+k)*50 +: 48]));
 end
endmodule

// COPIES (renamed hnx_rp4l_*) of the RP4f register primitives of claude/pl-smt-1018 rtl/hbm_accel/sm/ot_hbm_accel_smh.sv
// (hsm-rp4-0030: kreg RST = 2 synchronous clear, bundle_reg RSTK); main's ot_hbm_accel_smh.sv has no RST = 2 form.
module hnx_rp4l_kreg #(
    parameter integer W = 1,
    parameter integer RST = 0,
    parameter integer EN = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         en,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    // RST = 1: asynchronous clear; RST = 2: SYNCHRONOUS clear from a registered regional reset tree (RP4f, owner
    // 2026-10-16: regional sync reset trees, no async fan-out / removal checks across roots)
    generate if (RST == 2) begin : g_s
        always @(posedge clk)
            if (!rst_n) q <= {W{1'b0}};
            else if (EN == 0 || en) q <= d;
    end else if (RST != 0) begin : g_r
        always @(posedge clk or negedge rst_n)
            if (!rst_n) q <= {W{1'b0}};
            else if (EN == 0 || en) q <= d;
    end else begin : g_n
        always @(posedge clk) if (EN == 0 || en) q <= d;
    end endgenerate
endmodule
module hnx_rp4l_kregk #(
    parameter integer W = 1,
    parameter integer RST = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    (* keep *) reg [W-1:0] r;
    generate if (RST == 2) begin : g_s
        always @(posedge clk) if (!rst_n) r <= {W{1'b0}}; else r <= d;
    end else if (RST != 0) begin : g_r
        always @(posedge clk or negedge rst_n) if (!rst_n) r <= {W{1'b0}}; else r <= d;
    end else begin : g_n
        always @(posedge clk) r <= d;
    end endgenerate
    assign q = r;
endmodule
module hnx_rp4l_bundle_reg #(
    parameter integer W = 8,
    parameter integer V = 4,        // bits below the NV top valids that are data (c's non-valid part, w ...)
    parameter integer NV = 2,
    parameter integer X = 7,        // x_ce sits at bit X (above the X-bit x address)
    parameter integer K = 0,        // 1: kept flops (a deliberate duplicate of another bundle register)
    parameter integer RSTK = 1      // reset kind of the valid / x_ce flops: 1 async clear, 2 synchronous clear (RP4f)
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate if (K != 0) begin : g_k
        hnx_rp4l_kregk #(.W(NV), .RST(RSTK)) u_v (.clk(clk), .rst_n(rst_n), .d(d[W-1 -: NV]), .q(q[W-1 -: NV]));
        hnx_rp4l_kregk #(.W(W-NV-X-1)) u_d (.clk(clk), .rst_n(rst_n), .d(d[W-NV-1:X+1]), .q(q[W-NV-1:X+1]));
        hnx_rp4l_kregk #(.W(1), .RST(RSTK)) u_x (.clk(clk), .rst_n(rst_n), .d(d[X]), .q(q[X]));
        hnx_rp4l_kregk #(.W(X)) u_a (.clk(clk), .rst_n(rst_n), .d(d[X-1:0]), .q(q[X-1:0]));
    end else begin : g_p
    hnx_rp4l_kreg #(.W(NV), .RST(RSTK)) u_v (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(d[W-1 -: NV]),
        .q(q[W-1 -: NV]));
    hnx_rp4l_kreg #(.W(W-NV-X-1)) u_d (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(d[W-NV-1:X+1]),
        .q(q[W-NV-1:X+1]));
    hnx_rp4l_kreg #(.W(1), .RST(RSTK)) u_x (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(d[X]), .q(q[X]));
    hnx_rp4l_kreg #(.W(X)) u_a (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(d[X-1:0]), .q(q[X-1:0]));
    end endgenerate
endmodule
