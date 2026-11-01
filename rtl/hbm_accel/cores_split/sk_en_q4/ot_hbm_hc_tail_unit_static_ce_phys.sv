// Selected physical CE tail: identical face-stage mechanism to gated508-edge contract.
// Arithmetic is unchanged; two step0 enable stages plus CAP299 are explicit.
`timescale 1ns/1ps
`default_nettype none
// Exact face_shell.py CELL_SV mechanism: one unreset positive-edge flop on
// every input and output bus except clock/reset, which pass through.
module ot_hbm_ce_face_reg #(parameter W=1)(input clk,input[W-1:0]d,output reg[W-1:0]q);always@(posedge clk)q<=d;endmodule
module ot_hbm_hc_tail_unit_static_ce_phys #(parameter MUT_PRE=0,SMUT=0)(input clk,rst_n,launch,input[767:0]mixes,bases,input[95:0]scales,output result_v,output[767:0]result,output fault);
wire li;wire[767:0]mi,bi;wire[95:0]si;wire rv,ff;wire[767:0]rr;
ot_hbm_ce_face_reg a(clk,launch,li);ot_hbm_ce_face_reg#(768)b(clk,mixes,mi);ot_hbm_ce_face_reg#(768)c(clk,bases,bi);ot_hbm_ce_face_reg#(96)d(clk,scales,si);
wire en,iv,ird,ov,sf;wire[511:0]ie,y;
wire en_o,iv_o,ird_i,ov_i,sf_i;wire[511:0]ie_o,y_i;
ot_hbm_ce_face_reg e(clk,en_o,en);ot_hbm_ce_face_reg f(clk,iv_o,iv);ot_hbm_ce_face_reg#(512)g(clk,ie_o,ie);ot_hbm_ce_face_reg h(clk,ird,ird_i);ot_hbm_ce_face_reg i(clk,ov,ov_i);ot_hbm_ce_face_reg j(clk,sf,sf_i);ot_hbm_ce_face_reg#(512)k(clk,y,y_i);
ot_hbm_hc_tail_rest_core_ce#(.MUT_PRE(MUT_PRE),.CAP(299-((SMUT==1)?7:0)))u(.clk(clk),.rst_n(rst_n),.launch(li),.mixes(mi),.bases(bi),.scales(si),.result_v(rv),.result(rr),.fault(ff),.sk_en_sk(en_o),.sk_in_valid(iv_o),.sk_in_e(ie_o),.sk_in_ready(ird_i),.sk_out_valid(ov_i),.sk_fault(sf_i),.sk_y(y_i));
ot_hbm_ce_face_reg l(clk,rv,result_v);ot_hbm_ce_face_reg#(768)m(clk,rr,result);ot_hbm_ce_face_reg n(clk,ff,fault);
wire lo,pa,pb;wire[511:0]bq;wire bb,ab;
wire en0,lo0,pa0,pb0;wire[511:0]ie0,bq0;wire bb0,ab0;
ot_hbm_ce_face_reg p0(clk,en,en0);ot_hbm_ce_face_reg p1(clk,lo,lo0);ot_hbm_ce_face_reg p2(clk,pa,pa0);ot_hbm_ce_face_reg p3(clk,pb,pb0);ot_hbm_ce_face_reg#(512)p4(clk,ie,ie0);
ot_hdc_sk_step0_en_phys#(.EN_LAND(1),.EN_DELAY(2))s0(.clk(clk),.sk_en_i(en0),.load(lo0),.in_e(ie0),.pa(pa0),.pb(pb0),.b_q(bq0),.bbad_q(bb0),.abad_q(ab0));
ot_hbm_ce_face_reg#(512)p5(clk,bq0,bq);ot_hbm_ce_face_reg p6(clk,bb0,bb);ot_hbm_ce_face_reg p7(clk,ab0,ab);
wire en1,iv1,bb1,ab1;wire[511:0]bq1;wire ird1,lo1,pa1,pb1,ov1,sf1;wire[511:0]y1;
ot_hbm_ce_face_reg q0(clk,en,en1);ot_hbm_ce_face_reg q1(clk,iv,iv1);ot_hbm_ce_face_reg q2(clk,bb,bb1);ot_hbm_ce_face_reg q3(clk,ab,ab1);ot_hbm_ce_face_reg#(512)q4(clk,bq,bq1);
ot_hdc_sk_steady_en#(.EN_LAND(1))ss(.clk(clk),.rst_n(rst_n),.sk_en_i(en1),.in_valid(iv1),.in_ready(ird1),.load(lo1),.pa(pa1),.pb(pb1),.b_q(bq1),.bbad_q(bb1),.abad_q(ab1),.out_valid(ov1),.y(y1),.fault(sf1),.busy());
ot_hbm_ce_face_reg q5(clk,ird1,ird);ot_hbm_ce_face_reg q6(clk,lo1,lo);ot_hbm_ce_face_reg q7(clk,pa1,pa);ot_hbm_ce_face_reg q8(clk,pb1,pb);ot_hbm_ce_face_reg q9(clk,ov1,ov);ot_hbm_ce_face_reg#(512)q10(clk,y1,y);ot_hbm_ce_face_reg q11(clk,sf1,sf);
endmodule

`default_nettype wire
