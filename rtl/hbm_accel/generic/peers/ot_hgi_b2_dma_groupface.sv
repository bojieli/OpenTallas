`timescale 1ns/1ps
`default_nettype none
// Real separate hard-face root combines two independently registered source seams.
// Capture on the original group_q edge; the distinct core clears invalid sector FFs.
module ot_hgi_b2_dma_groupface #(parameter integer MUT_SEAM=0)(
 input wire clk,rst_n,input wire [512:0] request,input wire [511:0] kv_request,output reg [512:0] vr2q
);
 wire [512:0] group_next={request[512],request[511:0]|kv_request} ^ ((MUT_SEAM==3 && |kv_request)?513'd1:513'd0);
 reg [1:0] reset_release;
 always @(posedge clk or negedge rst_n)
   if(!rst_n)reset_release<=0;else reset_release<={reset_release[0],1'b1};
 wire rn=reset_release[1];
 always @(posedge clk or negedge rn) begin
   if(!rn)begin vr2q[512]<=0;for(integer lane=0;lane<32;lane=lane+1)vr2q[lane*16+15]<=0;end
   else begin vr2q[512]<=group_next[512];for(integer lane=0;lane<32;lane=lane+1)vr2q[lane*16+15]<=group_next[lane*16+15];end
 end
 always @(posedge clk)for(integer lane=0;lane<32;lane=lane+1)vr2q[lane*16 +:15]<=group_next[lane*16 +:15];
endmodule
`default_nettype wire
