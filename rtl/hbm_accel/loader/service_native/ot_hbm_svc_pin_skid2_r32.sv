`timescale 1ns/1ps
`default_nettype none
// HBM-SVGREL8 2026-10-20: the 2-entry registered pin skid of ot_hbm_svc_pin_skid2_h9 (same handshake: in_r = !tail
// valid, out_v = head valid, registered both ways, no combinational in -> out path) with 32-bit regions instead of 64
// (each region's KEPT head/tail valid copy and its push / pop controls drive <= 32 data flops), the tail register
// loading whenever it is empty (it is only read while its valid is set), and asynchronous reset from a synchronised leaf.
module ot_hbm_svc_pin_skid2_r32 #(parameter integer WIDTH=1)(
 input wire clk,rst_n,input wire in_v,output wire in_r,
 input wire [WIDTH-1:0]in_data,output wire out_v,input wire out_r,
 output wire [WIDTH-1:0]out_data
);
 localparam integer N=(WIDTH+31)/32;
 (* keep="true",dont_touch="true" *) reg [N-1:0] hv,tv;
 assign in_r=!tv[0]; assign out_v=hv[0];
 for(genvar s=0;s<N;s=s+1)begin:g_slice
   localparam integer B=(WIDTH-s*32<32)?WIDTH-s*32:32;
   reg[B-1:0] h,t;
   wire push=in_v&&!tv[s],pop=hv[s]&&out_r;
   assign out_data[s*32+:B]=h;
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
     if(push && (!hv[s] || pop))h<=in_data[s*32+:B];
     else if(pop && tv[s])h<=t;
     if(!tv[s])t<=in_data[s*32+:B];
   end
 end
endmodule
`default_nettype wire
