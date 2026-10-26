// LEC wrapper (S81-CORE-LAT-R2/LV): ot_v41_chain4 old (*_old, 95107779c) vs new at the parameter sets of its OTHER S81
// users (the BF columns / front: ot_v41_bf16_lanes3 / bf16_lanes2_rne_prepare / bf_lane4 / bf_lane4r_cl / bf_fp4_leaves
// = PD 1, ND 4, NCH NCHB, TW TRW + 1; the q-element set is in lec_top.sv) plus the module defaults.
module lv_c4_top #(parameter integer A_NCH = 8, A_TW = 3, B_NCH = 8, B_TW = 8) (input clk, rst_n,
  input va, vb, vc, input [2:0] sa, sb, input [3:0] sc, input fa, fb, fc, la, lb, lc, input [31:0] ta, tb, tc,
  input tfa, tfb, tfc, input [A_TW-1:0] ga, input [B_TW-1:0] gb, input [7:0] gc,
  output [1:0] ova, ovb, ovc, output [63:0] osa, osb, osc, output [1:0] ofa, ofb, ofc, fta, ftb, ftc,
  output [2*A_TW-1:0] ota, output [2*B_TW-1:0] otb, output [15:0] otc);
 ot_v41_chain4_old #(.PD(1), .ND(4), .NCH(A_NCH), .TW(A_TW)) u_old_a (.clk(clk), .rst_n(rst_n), .v(va), .slot(sa), .first(fa), .last(la), .term(ta), .term_f(tfa), .tag(ga), .ov(ova[0]), .osum(osa[31:0]), .of(ofa[0]), .otag(ota[A_TW-1:0]), .fault(fta[0]));
 ot_v41_chain4     #(.PD(1), .ND(4), .NCH(A_NCH), .TW(A_TW)) u_new_a (.clk(clk), .rst_n(rst_n), .v(va), .slot(sa), .first(fa), .last(la), .term(ta), .term_f(tfa), .tag(ga), .ov(ova[1]), .osum(osa[63:32]), .of(ofa[1]), .otag(ota[2*A_TW-1:A_TW]), .fault(fta[1]));
 ot_v41_chain4_old #(.PD(1), .ND(4), .NCH(B_NCH), .TW(B_TW)) u_old_b (.clk(clk), .rst_n(rst_n), .v(vb), .slot(sb), .first(fb), .last(lb), .term(tb), .term_f(tfb), .tag(gb), .ov(ovb[0]), .osum(osb[31:0]), .of(ofb[0]), .otag(otb[B_TW-1:0]), .fault(ftb[0]));
 ot_v41_chain4     #(.PD(1), .ND(4), .NCH(B_NCH), .TW(B_TW)) u_new_b (.clk(clk), .rst_n(rst_n), .v(vb), .slot(sb), .first(fb), .last(lb), .term(tb), .term_f(tfb), .tag(gb), .ov(ovb[1]), .osum(osb[63:32]), .of(ofb[1]), .otag(otb[2*B_TW-1:B_TW]), .fault(ftb[1]));
 ot_v41_chain4_old u_old_c (.clk(clk), .rst_n(rst_n), .v(vc), .slot(sc), .first(fc), .last(lc), .term(tc), .term_f(tfc), .tag(gc), .ov(ovc[0]), .osum(osc[31:0]), .of(ofc[0]), .otag(otc[7:0]), .fault(ftc[0]));
 ot_v41_chain4     u_new_c (.clk(clk), .rst_n(rst_n), .v(vc), .slot(sc), .first(fc), .last(lc), .term(tc), .term_f(tfc), .tag(gc), .ov(ovc[1]), .osum(osc[63:32]), .of(ofc[1]), .otag(otc[15:8]), .fault(ftc[1]));
endmodule
