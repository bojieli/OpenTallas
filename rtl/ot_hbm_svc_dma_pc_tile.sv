`timescale 1ns/1ps
// Native burst metadata resides beside each PC. Sixteen independent leases
// hide read startup; echoed native tag is mandatory. Returns may reorder.
module ot_hbm_svc_dma_pc_tile #(
 parameter integer DEPTH=16
)(
 input wire clk,rst,
 output wire capacity,input wire rq_v,output wire rq_rdy,input wire[16:0] rq_tag,input wire[3:0] rq_len,
 input wire phy_ready,output wire phy_v,
 input wire rs_v,output wire rs_rdy,input wire[16:0] rs_tag,input wire[3:0] rs_beat,
 output wire out_v,output wire[2:0] out_slot,output wire[7:0] out_idx
);
 reg valid[0:DEPTH-1];reg[16:0] tags[0:DEPTH-1];reg[3:0] lengths[0:DEPTH-1];
 reg[3:0] beats_seen[0:DEPTH-1];
 integer i,free_slot,match_slot;
 always @*begin
   free_slot=-1;match_slot=-1;
   for(i=0;i<DEPTH;i=i+1)begin
     if(!valid[i] && free_slot<0)free_slot=i;
     if(valid[i] && tags[i]==rs_tag)match_slot=i;
   end
 end
 assign capacity=free_slot>=0;
 assign rq_rdy=free_slot>=0 && phy_ready;
 assign phy_v=rq_v && free_slot>=0;
 assign rs_rdy=match_slot>=0;
 assign out_v=rs_v && rs_rdy;
 assign out_slot=rs_tag[10:8];assign out_idx=rs_tag[7:0]+rs_beat;
 integer k;
 always @(posedge clk)begin
   if(rst)for(k=0;k<DEPTH;k=k+1)begin valid[k]<=0;tags[k]<=0;lengths[k]<=0;beats_seen[k]<=0;end
   else begin
     if(rq_v && rq_rdy)begin valid[free_slot]<=1;tags[free_slot]<=rq_tag;lengths[free_slot]<=rq_len;beats_seen[free_slot]<=0;end
     if(out_v)begin
       beats_seen[match_slot]<=beats_seen[match_slot]|(4'b0001<<rs_beat);
       if((beats_seen[match_slot]|(4'b0001<<rs_beat))==((4'b0001<<lengths[match_slot])-1'b1))valid[match_slot]<=0;
     end
`ifndef SYNTHESIS
     if(rs_v && !rs_rdy)$fatal(1,"DMA native unknown/retired tag");
     if(out_v && (rs_beat>=lengths[match_slot] || beats_seen[match_slot][rs_beat]))$fatal(1,"DMA native duplicate/out-of-bounds beat");
`endif
   end
 end
endmodule
