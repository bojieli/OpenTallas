`timescale 1ns/1ps
// Each 64-bit region owns its registered valid/select state. Data flops
// have no reset; valid bits synchronously mask uninitialized words.
module ot_hbm_svc_pin_skid2_h9 #(parameter integer WIDTH=1)(
 input wire clk,rst_n,input wire in_v,output wire in_r,
 input wire [WIDTH-1:0]in_data,output wire out_v,input wire out_r,
 output wire [WIDTH-1:0]out_data
);
 localparam N=(WIDTH+63)/64;
 (* keep="true",dont_touch="true" *) reg [N-1:0] hv,tv;
 assign in_r=!tv[0]; assign out_v=hv[0];
 for(genvar s=0;s<N;s=s+1)begin:g_slice
   localparam B=(WIDTH-s*64<64)?WIDTH-s*64:64;
   reg[B-1:0] h,t;
   wire push=in_v&&!tv[s],pop=hv[s]&&out_r;
   assign out_data[s*64+:B]=h;
   always @(posedge clk)begin
     if(!rst_n)begin hv[s]<=0;tv[s]<=0;end
     else case({push,pop})
       2'b10:if(!hv[s])hv[s]<=1;else tv[s]<=1;
       2'b01:begin hv[s]<=tv[s];tv[s]<=0;end
       2'b11:begin hv[s]<=1;tv[s]<=0;end
       default:;
     endcase
   end
   always @(posedge clk)begin
     if(push && (!hv[s] || pop))h<=in_data[s*64+:B];
     else if(pop && tv[s])h<=t;
     if(push && hv[s] && !pop)t<=in_data[s*64+:B];
   end
 end
endmodule
