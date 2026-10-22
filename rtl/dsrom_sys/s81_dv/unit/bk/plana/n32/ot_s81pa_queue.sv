`timescale 1ns/1ps
// Opt-in control DM4 storage. Pure pointer replacement of the original shift
// queue; q is the logical head AFTER each edge. Caller supplies pop=take, so
// empty arrivals cannot be consumed until the following edge, exactly as before.
(* keep_hierarchy="yes" *)
module ot_s81pa_queue #(parameter integer W=358, NS=(W+15)/16, MUT=0)(
 input wire clk,input wire[NS-1:0]rst_n,
 input wire push,pop,input wire[W-1:0]data,
 output wire[W-1:0]head,output reg[2:0]count);
 reg[1:0]rp,wp;
 wire[1:0]next_head=(MUT==3)?rp:(pop?(rp+2'd1):rp);
 always @(posedge clk or negedge rst_n[0])
  if(!rst_n[0]) begin rp<=0;wp<=0;count<=0;end
  else begin
   if(pop)rp<=rp+2'd1;
   if(push)wp<=wp+2'd1;
   count<=count+3'(push)-3'(pop);
  end
 ot_sram_showahead_1r1w #(.W(W),.AW(2),.WREG(1),.MUT(MUT))u_mem(
  .clk(clk),.rst_n(rst_n),.we(push),.wa(wp),.wd(data),.ra(next_head),.q(head));
endmodule
