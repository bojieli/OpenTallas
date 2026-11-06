`timescale 1ns/1ps
// Same two occupied entries and edge schedule as the RF1 ring skid. push is
// already admitted by the caller using the pre-edge n!=2 test (no full-pop
// lookahead). pop is an accepted head. Payloads deliberately have no reset.
module ot_svgr_rf1_skid_head #(parameter integer W=285, parameter integer MUT=0)(
 input wire clk,rst_n,push,pop,input wire [W-1:0] in_data,input wire in_ok,
 output wire [W-1:0] head_data,output wire head_ok,output reg [1:0] n
);
 reg [W-1:0] head,tail;
 reg hok,tok;
 assign head_data=head;
 assign head_ok=hok;
 always @(posedge clk) begin
  if(pop && n==2 && MUT!=1) head<=tail;
  if(push && MUT!=2) begin
   if(n==0 || (n==1 && pop) || (MUT==3 && n==1)) head<=in_data;
   else tail<=in_data;
  end
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n)begin n<=0;hok<=0;tok<=0;end
  else begin
   n<=n+2'(push)-2'(pop);
   if(pop && n==2 && MUT!=1)hok<=tok;
   if(push && MUT!=2)begin
    if(n==0 || (n==1 && pop) || (MUT==3 && n==1))hok<=in_ok;
    else tok<=in_ok;
   end
  end
 end
endmodule
