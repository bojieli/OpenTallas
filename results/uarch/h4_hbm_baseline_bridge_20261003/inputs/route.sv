`timescale 1ps/1fs
// Real held register and finite delay counter; no packet callback from a bound.
// This single-owned lane deliberately backpressures while38FASTedges in flight.
// Measured throughput cannot be transferred to the inherited weight transport.
module ot_hbm_r14_route #(parameter integer WIDTH=471,EDGES=38)(
 input wire clk,rst_n,iv,output wire ir,input wire [WIDTH-1:0] id,
 output wire ov,input wire ore,output wire [WIDTH-1:0] od);
 reg [WIDTH-1:0] packet;reg live;reg [5:0] left;
 assign ir=!live;assign ov=live&&left==0;assign od=packet;
 always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin packet<=0;live<=0;left<=0;end
   else begin
     if(iv&&ir)begin packet<=id;live<=1;left<=6'(EDGES);end
     if(live&&left!=0)left<=left-1'b1;
     if(ov&&ore)live<=0;
   end
 end
endmodule
