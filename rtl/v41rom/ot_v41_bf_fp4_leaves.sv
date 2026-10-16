`timescale 1ns/1ps
// Actual FP4/FP8 term and serial chunk chain; no arithmetic or latency changes.
module ot_v41_bf_fp4_chain #(parameter integer NCH=16,TG=7,TW=$clog2(NCH)+TG+6,
 parameter[8:0] CUT=9'b1_0111_1011)(
 input wire fclk,rst_pin,ze_d,v,fp4,input wire[255:0] xq,wq,
 input wire[9:0] xe,we,input wire[TW-1:0] tag,
 output wire cv,output wire[31:0] cs,output wire cf,output wire[TG:0] ct,output wire fault);
 localparam integer HW=$clog2(NCH);
 wire clk,rst_n,term_v,term_f;wire[31:0] term;wire[TW-1:0] term_tag;
 ot_v41_tile_clk u_tc(.fclk(fclk),.rst_pin(rst_pin),.ze_d(ze_d),.gclk(clk),.rst_n(rst_n));
 ot_v41_bterm4_w10 #(.TW(TW),.P1S(1),.CSAM(10),.P2S(1),.NS(1)) u_term
 (.clk(clk),.rst_n(rst_n),.v(v),.fp4(fp4),.xq(xq),.xe(xe),.wq(wq),.we(we),.tag(tag),
 .ov(term_v),.y(term),.f(term_f),.otag(term_tag));
 ot_v41_chain4 #(.PD(1),.ND(4),.NCH(NCH),.TW(TG+1),.CUT(CUT)) u_chain
 (.clk(clk),.rst_n(rst_n),.v(term_v),.slot(term_tag[TW-1 -:HW]),.first(term_tag[5]),.last(term_tag[4]),
 .term(term),.term_f(term_f),.tag({term_tag[TW-HW-1 -:TG],term_tag[3]}),
 .ov(cv),.osum(cs),.of(cf),.otag(ct),.fault(fault));
endmodule

module ot_v41_bf_fp4_pair_leaf #(parameter integer NCH=16,TG=7,TW=$clog2(NCH)+TG+6,
 parameter[8:0] CUT=9'b1_0111_1011,
 parameter integer LAT=1+CUT[0]+CUT[1]+CUT[2]+CUT[3]+CUT[4]+CUT[5]+CUT[6]+CUT[7]+CUT[8])(
 input wire fclk,rst_pin,ze_d,v,fp4,input wire[255:0] xq,wq,
 input wire[9:0] xe,we,input wire[TW-1:0] tag,
 input wire other_v,input wire[31:0] other_sum,input wire other_f,input wire[TG:0] other_tag,
 output wire q_v,output wire[31:0] q_val,output wire q_err,output wire[TG:0] q_tag,output wire fault);
 wire cv,cf;wire[31:0] cs;wire[TG:0] ct;
 ot_v41_bf_fp4_chain #(.NCH(NCH),.TG(TG),.TW(TW),.CUT(CUT)) u_chain
 (.fclk(fclk),.rst_pin(rst_pin),.ze_d(ze_d),.v(v),.fp4(fp4),.xq(xq),.wq(wq),.xe(xe),.we(we),.tag(tag),
 .cv(cv),.cs(cs),.cf(cf),.ct(ct),.fault(fault));
 wire clk,rst_n;
 ot_v41_tile_clk u_tc(.fclk(fclk),.rst_pin(rst_pin),.ze_d(ze_d),.gclk(clk),.rst_n(rst_n));
 wire both=cv&&other_v;wire any_v=cv||other_v;
 wire[TG:0] chosen_tag=cv?ct:other_tag;wire[31:0] one=cv?cs:other_sum;wire one_f=cv?cf:other_f;
 wire[31:0] sum,pass;wire[1:0] err;wire vo;wire[TG+2:0] tp;
 ot_v41_fadd #(.CUT(CUT)) u_pair(.clk(clk),.rst_n(rst_n),.valid_in(both),.a(cs),.b(other_sum),.y(sum),.err(err),.valid_out(vo));
 ot_hdc_delay #(.W(32),.D(LAT)) u_pass(.clk(clk),.rst_n(rst_n),.d(one),.q(pass));
 ot_hdc_delay #(.W(TG+3),.D(LAT)) u_tag(.clk(clk),.rst_n(rst_n),.d({chosen_tag,both,both?(cf|other_f):one_f}),.q(tp));
 reg[LAT-1:0] vp;
 always @(posedge clk or negedge rst_n)if(!rst_n)vp<='0;else vp<={vp[LAT-2:0],any_v};
 assign q_v=vp[LAT-1];assign q_val=tp[1]?sum:pass;assign q_err=tp[0]|(tp[1]&&err!=2'd0);assign q_tag=tp[TG+2:2];
endmodule
