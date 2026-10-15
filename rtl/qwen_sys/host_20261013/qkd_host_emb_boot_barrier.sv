`timescale 1ns/1ps
// A real chain retirement marker alone does not certify the embedding image.
// Hold it until the gateway receives and verifies all four STATUS checksums.
module qkd_host_emb_boot_barrier #(parameter integer MUT=0)(
 input wire ck,rst_n,input wire in_v,input wire[65:0]in_d,output reg in_cr,
 input wire[12:0]est,output reg out_v,output reg[65:0]out_d,
 input wire out_cr,output reg fault);
 reg pending,delivered;reg[65:0]word;reg iv_q,cr_q;reg[12:0]est_q;
 always @(posedge ck)word<=in_v?in_d:word;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin pending<=0;delivered<=0;iv_q<=0;cr_q<=0;est_q<=0;in_cr<=0;out_v<=0;out_d<=0;fault<=0;end
  else begin
   iv_q<=in_v;cr_q<=out_cr;est_q<=est;in_cr<=0;out_v<=0;
   if(est_q[1])fault<=1;
   if(iv_q)begin if(pending||delivered)fault<=1;else pending<=1;end
   if(pending&&((est_q[0]&&!est_q[1])||MUT==1)&&!fault)begin out_d<=word;out_v<=1;pending<=0;delivered<=1;end
   if(cr_q)begin if(!delivered)fault<=1;else begin delivered<=0;in_cr<=1;end end
  end
 end
endmodule
