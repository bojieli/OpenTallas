`timescale 1ns/1ps
`default_nettype none
// HBM-SVGREL8 2026-10-20: the 2-entry registered pin skid of ot_hbm_svc_pin_skid2_h9 (same handshake: in_r = !tail
// valid, out_v = head valid, registered both ways, no combinational in -> out path) with 32-bit regions instead of 64
// (each region's KEPT head/tail valid copy and its push / pop controls drive <= 32 data flops), the tail register
// loading whenever it is empty (it is only read while its valid is set), and asynchronous reset from a synchronised leaf.
// Round 3 (HBM-SVGREL8): RW = region width (default 32); the per-region push / pop / head-load / tail-select controls are
// KEPT wires, so synthesis cannot fold out_r / in_v into every data bit's mux (census: 328-load out_r nets at RW 32).
module ot_hbm_svc_pin_skid2_r32 #(parameter integer WIDTH=1,parameter integer RW=32)(
 input wire clk,rst_n,input wire in_v,output wire in_r,
 input wire [WIDTH-1:0]in_data,output wire out_v,input wire out_r,
 output wire [WIDTH-1:0]out_data
);
 localparam integer N=(WIDTH+RW-1)/RW;
 (* keep="true",dont_touch="true" *) reg [N-1:0] hv,tv;
 assign in_r=!tv[0]; assign out_v=hv[0];
 for(genvar s=0;s<N;s=s+1)begin:g_slice
   localparam integer B=(WIDTH-s*RW<RW)?WIDTH-s*RW:RW;
   reg[B-1:0] h,t;
   (* keep="true" *) wire push=in_v&&!tv[s];
   (* keep="true" *) wire pop=hv[s]&&out_r;
   (* keep="true" *) wire hload=push&&(!hv[s]||pop);
   (* keep="true" *) wire hfromt=!hload&&pop&&tv[s];
   (* keep="true" *) wire tload=!tv[s];
   assign out_data[s*RW+:B]=h;
   always @(posedge clk or negedge rst_n)begin
     if(!rst_n)begin hv[s]<=0;tv[s]<=0;end
     else case({push,pop})
       2'b10:if(!hv[s])hv[s]<=1;else tv[s]<=1;
       2'b01:begin hv[s]<=tv[s];tv[s]<=0;end
       2'b11:begin hv[s]<=1;tv[s]<=0;end
       default:;
     endcase
   end
   always @(posedge clk)begin
     if(hload)h<=in_data[s*RW+:B];
     else if(hfromt)h<=t;
     if(tload)t<=in_data[s*RW+:B];
   end
 end
endmodule
`default_nettype wire
