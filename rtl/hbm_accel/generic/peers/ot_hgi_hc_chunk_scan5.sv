`timescale 1ns/1ps
`default_nettype none
// One quarter's five block stores. Pin-capture every local packet, then publish
// the selected registered scan word with its global block/group association.
module ot_hgi_hc_chunk_scan5(
 input wire clk,rst_n,clr,input wire[4:0]in_v,
 input wire[5*256-1:0]in_data,input wire[6:0]in_meta,
 output reg out_v,output reg[255:0]out_data,output reg[6:0]out_meta,
 output reg fault
);
 wire[0:0]rn;ot_rst_relay #(.REGIONS(1))u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rn));
 reg[4:0]vq;reg[1279:0]dq;reg[6:0]mq;reg clear_q;
 always @(posedge clk)begin dq<=in_data;mq<=in_meta;end
 always @(posedge clk or negedge rn[0])begin
  if(!rn[0])begin vq<=0;clear_q<=1;end
  else begin vq<=in_v;clear_q<=clr;end
 end
 reg[255:0]selected;
 always @*begin selected=0;for(integer k=0;k<5;k++)selected=selected|(dq[k*256+:256]&{256{vq[k]}});end
 always @(posedge clk)begin out_data<=selected;out_meta<=mq;end
 always @(posedge clk or negedge rn[0])begin
  if(!rn[0])begin out_v<=0;fault<=0;end
  else begin out_v<=(|vq)&&!clear_q;if(clear_q)fault<=0;else if((vq&(vq-1'b1))!=0)fault<=1;end
 end
endmodule
`default_nettype wire
