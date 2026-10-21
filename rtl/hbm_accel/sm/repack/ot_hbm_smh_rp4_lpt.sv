`timescale 1ns/1ps
// PL-SMT (PARENTS-LANDED 10-18): kit top of the LANDED HBM SM tile rp4 (2 clock regions).  Wires only: the generated
// ot_hbm_smh_rp4_flat_lp (tools/landed_parent/lp.py, spec results/arch/landed_parent_1018/pl_smt/rp4_lp_spec.json) with
// ot_hbm_smh_rp4_one's data port names restored (rin / rout are split per region inside), so the die binds the same data
// ports.  Clock: ONE port per region, ck_n (N region: leaf 0, row 0, bin beat path) and ck_s (S region: leaf 1, row 1,
// land_s, gout); the old single `clk` is gone.  Latency vs ot_hbm_smh_rp4_one: gout +3 edges, reset release +3 - 5
// (lp reset runs depth 3 replace the 5-stage u_rt tree), every other port 0 (record ot_hbm_smh_rp4_flat_lp_record.json).
module ot_hbm_smh_rp4_lpt (input wire ck_n, input wire ck_s, input wire rst_n,
 input wire[8:0]xs_a1,input wire[4:0]xs_g1,input wire[6:0]xs_a2,input wire[4:0]xs_g2,
 input wire[8:0]xss_a1,input wire[4:0]xss_g1,input wire[6:0]xss_a2,input wire[4:0]xss_g2,
 input wire[1635:0]rin,input wire[2068:0]bin,output wire[1635:0]rout,output wire[2068:0]bout,
 input wire[99:0]gin,output wire[199:0]gout);
 ot_hbm_smh_rp4_flat_lp u (.ck_n(ck_n), .ck_s(ck_s), .rst_n(rst_n), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2),
  .xss_a1(xss_a1), .xss_g1(xss_g1), .xss_a2(xss_a2), .xss_g2(xss_g2), .rin_n(rin[817:0]), .rin_s(rin[1635:818]), .bin(bin),
  .rout_n(rout[817:0]), .rout_s(rout[1635:818]), .bout(bout), .gin(gin), .gout(gout));
endmodule
