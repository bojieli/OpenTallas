`timescale 1ns/1ps
`default_nettype none
// Real separate hard-face root after the registered MV group request source.
// All32 lane payloads and the credit-request level cross together, one edge later.
module ot_hgi_b2_dma_groupface(
 input wire clk,rst_n,input wire [512:0] request,output reg [512:0] vr2q
);
 reg [1:0] reset_release;
 always @(posedge clk or negedge rst_n)
   if(!rst_n)reset_release<=0;else reset_release<={reset_release[0],1'b1};
 wire rn=reset_release[1];
 always @(posedge clk or negedge rn) begin
   if(!rn)begin vr2q[512]<=0;for(integer lane=0;lane<32;lane=lane+1)vr2q[lane*16+15]<=0;end
   else begin vr2q[512]<=request[512];for(integer lane=0;lane<32;lane=lane+1)vr2q[lane*16+15]<=request[lane*16+15];end
 end
 always @(posedge clk)for(integer lane=0;lane<32;lane=lane+1)vr2q[lane*16 +:15]<=request[lane*16 +:15];
endmodule
`default_nettype wire
