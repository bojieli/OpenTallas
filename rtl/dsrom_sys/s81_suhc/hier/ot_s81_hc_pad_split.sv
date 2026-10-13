`timescale 1ns/1ps
// Closed standalone relay leaves. Centre wrapper assembly remains on the physical candidate branch.

module ot_s81_hc_pad_f8 #(parameter integer FW=1128,VW=7,DEPTH=8)(
 input wire sk,srs,input wire[VW-1:0]v_i,input wire[FW-1:0]d_i,
 output wire[VW-1:0]v_o,output wire[FW-1:0]d_o);
 reg[1:0] rr;always @(posedge sk)rr<={rr[0],srs};
 ot_hdc_delay #(.W(VW),.D(DEPTH),.RESET(1)) u_v(.clk(sk),.rst_n(rr[1]),.d(v_i),.q(v_o));
 ot_hdc_delay #(.W(FW),.D(DEPTH)) u_d(.clk(sk),.rst_n(rr[1]),.d(d_i),.q(d_o));
endmodule

module ot_s81_hc_pad_meta2 #(parameter integer VW=8,EW=512,DEPTH=2)(
 input wire sk,srs,input wire[VW-1:0]v_i,input wire[7:0]p_i,input wire[EW-1:0]e_i,
 output wire[VW-1:0]v_o,output wire[7:0]p_o,output wire[EW-1:0]e_o);
 reg[1:0] rr;always @(posedge sk)rr<={rr[0],srs};
 ot_hdc_delay #(.W(VW),.D(DEPTH),.RESET(1))u_v(.clk(sk),.rst_n(rr[1]),.d(v_i),.q(v_o));
 ot_hdc_delay #(.W(8+EW),.D(DEPTH))u_d(.clk(sk),.rst_n(rr[1]),.d({e_i,p_i}),.q({e_o,p_o}));
endmodule
