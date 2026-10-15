`timescale 1ns/1ps
`default_nettype none
// Source-only local credit terminator candidate. Not a closed hard view.
// Fixed native flit encoding; no destination interpretation or arithmetic.
// Payload chunks are separate hardening units; no reset on payload.
module ot_vms_elastic_chunk #(parameter integer W=276,D=6,B=$clog2(D))(
 input wire clk, input wire [W-1:0] din,
 input wire put, input wire putvc, input wire [B-1:0] wp,
 input wire take, input wire takevc, input wire [B-1:0] rp,
 output reg [W-1:0] dout);
 reg [W-1:0] pin_d;
 reg [W-1:0] mem [0:1][0:D-1];
 always @(posedge clk) begin
  pin_d<=din;
  if(put) mem[putvc][wp]<=pin_d;
  if(take) dout<=mem[takevc][rp];
 end
endmodule
module ot_vms_elastic #(parameter integer D=6, MUT=0)(
 input wire [9:0] clk,input wire rst_n,
 input wire [2223:0] f_in,output wire [2223:0] f_out,
 input wire [1:0] cr_in,output reg [1:0] cr_out);
 localparam integer B=$clog2(D);
 reg pin_v,pin_vc,out_v; reg [1:0] pin_cr;
 reg [B-1:0] head[0:1],tail[0:1];
 reg [B:0] count[0:1],credit[0:1];
 wire available0=(count[0]!=0 && credit[0]!=0);
 wire available1=(count[1]!=0 && credit[1]!=0);
 wire take=available0 || available1;
 wire vc=available1;
 wire [B-1:0] readp=head[vc],writep=tail[pin_vc];
 assign f_out[2223]=out_v;
 for(genvar c=0;c<9;c=c+1) begin:g_chunk
  localparam integer LO=c*276, W=(c==8)?15:276;
  ot_vms_elastic_chunk #(.W(W),.D(D)) u(.clk(clk[c+1]),.din(f_in[LO+:W]),
   .put(pin_v),.putvc(pin_vc),.wp(writep),.take(take),.takevc(vc),.rp(readp),.dout(f_out[LO+:W]));
 end
 always @(posedge clk[0] or negedge rst_n) begin
  if(!rst_n) begin
   pin_v<=0;pin_vc<=0;out_v<=0;pin_cr<=0;cr_out<=0;
   for(integer v=0;v<2;v=v+1) begin head[v]<=0;tail[v]<=0;count[v]<=0;credit[v]<=D;end
  end else begin
   pin_v<=f_in[2223];pin_vc<=f_in[2222];pin_cr<=cr_in;out_v<=take;
   cr_out<=take ? (MUT==2 ? (vc ? 2'b01:2'b10) : (vc ? 2'b10:2'b01)) : 2'b00;
   for(integer v=0;v<2;v=v+1) begin
    count[v]<=count[v]+(pin_v && pin_vc==v)-(take && vc==v);
    credit[v]<=credit[v]+pin_cr[v]-(take && vc==v);
    if(pin_v && pin_vc==v) tail[v]<=(tail[v]==D-1)?0:tail[v]+1'b1;
    if(take && vc==v) head[v]<=(head[v]==D-1)?0:head[v]+1'b1;
   end
  end
 end
endmodule
`default_nettype wire
