`timescale 1ns/1ps
`default_nettype none
// Static die relay between an SFU LG pair leaf and the SFU core (H-SU 2026-10-15): R register stages in
// each direction on the leaf's 1,112-bit port, placed by the die tools at <= 480 um reach. R is a compile
// constant shared with the core (LG_PATH = 1 + R); no flow control. Valid bits reset, data not.
module ot_hgi_sfu_lg_relay #(parameter integer R=0)(
 input wire clk,rst_n,
 input wire [33:0] c_rq,
 input wire [561:0] c_wq,
 output wire [513:0] c_rr,
 output wire [1:0] c_w_done,
 output wire [33:0] l_rq,
 output wire [561:0] l_wq,
 input wire [513:0] l_rr,
 input wire [1:0] l_w_done
);
 for(genvar b=0;b<2;b=b+1)begin:g_bank
  ot_hdc_delay #(.W(1),.D(R),.RESET(1)) u_rqv(.clk(clk),.rst_n(rst_n),.d(c_rq[17*b+16]),.q(l_rq[17*b+16]));
  ot_hdc_delay #(.W(16),.D(R)) u_rqd(.clk(clk),.rst_n(rst_n),.d(c_rq[17*b+:16]),.q(l_rq[17*b+:16]));
  ot_hdc_delay #(.W(1),.D(R),.RESET(1)) u_wqv(.clk(clk),.rst_n(rst_n),.d(c_wq[281*b+280]),.q(l_wq[281*b+280]));
  ot_hdc_delay #(.W(280),.D(R)) u_wqd(.clk(clk),.rst_n(rst_n),.d(c_wq[281*b+:280]),.q(l_wq[281*b+:280]));
  ot_hdc_delay #(.W(1),.D(R),.RESET(1)) u_rrv(.clk(clk),.rst_n(rst_n),.d(l_rr[257*b+256]),.q(c_rr[257*b+256]));
  ot_hdc_delay #(.W(256),.D(R)) u_rrd(.clk(clk),.rst_n(rst_n),.d(l_rr[257*b+:256]),.q(c_rr[257*b+:256]));
 end
 ot_hdc_delay #(.W(2),.D(R),.RESET(1)) u_done(.clk(clk),.rst_n(rst_n),.d(l_w_done),.q(c_w_done));
endmodule
`default_nettype wire
