// LEC wrapper (S81-CORE-LAT-R2/LV): old (*_old, 95107779c) and new q element side by side at the S81 die parameters
// (canonical core spec physical/die_plan/s81/cores/legacy/specs/ot_v41_rom_elem_q_qxpq_w10/spec.json: RSTP 1, CPR 0).
module lv_top (
  input clk, rst_n, cfg_v, go, xs_v, input [4:0] cfg_a, input [47:0] cfg_d, input [1:0] go_tag,
  input [7:0] xs_p, input [2:0] xs_b, xs_pos, input [1:0] xs_sv, input [255:0] xs_q0, xs_q1, input [9:0] xs_e0, xs_e1,
  output [1:0] av, bv, ae, be, output [63:0] ad, bd, output [31:0] ar, br, output [9:0] asg, bsg, an, bn,
  output [5:0] ap, bp, output ab, bb, af, bf, awk, bwk, abf, bbf, ash, bsh);
`define QP .MTP(1), .EARLY(1), .NB(2), .FAST(1), .PP(1), .QTIMING_FIX(1), .QPIPE(1), .QP_XS(1), .QP_CAP(0), .QP_P1(1), .QP_CSAM(10), .QZ(1), .QZ_NS(8), .QZ_NE(4), .QY(1), .QX(10), .PQ(1), .QW(0), .QM(5), .QS(5), .RSTP(1), .CPR(0)
 ot_v41_rom_elem_q_qxpq_w10_old #(`QP, .INSTANCE("r")) u_old (
  .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go), .go_tag(go_tag),
  .walking(awk), .bank_free(abf), .sh_free(ash),
  .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1), .xs_e1(xs_e1),
  .xs_pos(xs_pos), .pv(av), .pval(ad), .prow(ar), .pseg(asg), .pnseg(an), .perr(ae), .ppos(ap), .busy(ab), .fault(af));
 ot_v41_rom_elem_q_qxpq_w10 #(`QP, .INSTANCE("r")) u_new (
  .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go), .go_tag(go_tag),
  .walking(bwk), .bank_free(bbf), .sh_free(bsh),
  .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1), .xs_e1(xs_e1),
  .xs_pos(xs_pos), .pv(bv), .pval(bd), .prow(br), .pseg(bsg), .pnseg(bn), .perr(be), .ppos(bp), .busy(bb), .fault(bf));
endmodule
