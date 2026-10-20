// Opt-in SAFE variant: same H9b skid edges, eight-bit kept select regions.
`timescale 1ns/1ps
// Each eight-bit region owns its registered valid/select state. Data flops
// have no reset; valid bits synchronously mask uninitialized words.
// ARST=1 (HBM-MC3 10-19, default 0 = unchanged): hv/tv clear asynchronously (one counted reset endpoint per flop).
module ot_hbm_svc_pin_skid2_bw_safe #(parameter integer WIDTH=1,REGIONAL=0,ARST=0)(
 input wire clk,rst_n,input wire in_v,output wire in_r,
 input wire [WIDTH-1:0]in_data,output wire out_v,input wire [(WIDTH+15)/16-1:0]out_r_regions,
 output wire [WIDTH-1:0]out_data,
 input wire [(WIDTH+15)/16-1:0]in_v_regions,
 output wire [(WIDTH+15)/16-1:0]out_v_regions
);
 localparam N=(WIDTH+7)/8;
 (* keep="true",dont_touch="true" *) reg [N-1:0] hv,tv;
 assign in_r=!tv[0]; assign out_v=hv[0];
 for(genvar s=0;s<N;s=s+1)begin:g_slice
   localparam B=(WIDTH-s*8<8)?WIDTH-s*8:8;
   reg[B-1:0] h,t;
   wire push=((REGIONAL!=0)?in_v_regions[s/2]:in_v)&&!tv[s],pop=hv[s]&&out_r_regions[s/2];
   assign out_data[s*8+:B]=h;
   if(s%2==0)assign out_v_regions[s/2]=hv[s];
   reg hv_n,tv_n;
   always @*begin
     hv_n=hv[s];tv_n=tv[s];
     case({push,pop})
       2'b10:if(!hv[s])hv_n=1;else tv_n=1;
       2'b01:begin hv_n=tv[s];tv_n=0;end
       2'b11:begin hv_n=1;tv_n=0;end
       default:;
     endcase
   end
   if(ARST!=0)begin:g_a
     always @(posedge clk or negedge rst_n)
       if(!rst_n)begin hv[s]<=0;tv[s]<=0;end else begin hv[s]<=hv_n;tv[s]<=tv_n;end
   end else begin:g_s
     always @(posedge clk)
       if(!rst_n)begin hv[s]<=0;tv[s]<=0;end else begin hv[s]<=hv_n;tv[s]<=tv_n;end
   end
   always @(posedge clk)begin
     if(push && (!hv[s] || pop))h<=in_data[s*8+:B];
     else if(pop && tv[s])h<=t;
     if(push && hv[s] && !pop)t<=in_data[s*8+:B];
   end
 end
endmodule
