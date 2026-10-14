`timescale 1ns/1ps
`default_nettype none
// Eight LOCAL-OFFSET write lanes, explicit native {v, sec16, data256, mask8}.
// Same retained aperture/ownership obligation as xread. wq_cr is NOT visibility:
// wq_done marks local SRAM commitment; mirror publication also needs ring drain.
module ot_hbm_b2_xwrite_aperture #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire permit,input wire [1:0] sid,input wire mirror,
 input wire [8*280-1:0] old_q,output wire [7:0] old_cr,old_done,
 output wire [8*281-1:0] wq,input wire [7:0] wq_cr,wq_done,
 output reg fault
);
 wire [7:0] bad,valid;
 for(genvar b=0;b<8;b=b+1)begin:lane
  wire [279:0] q=old_q[b*280+:280];
  assign valid[b]=q[279];
  assign bad[b]=q[279]&&(q[278:277]!=0||(mirror&&q[276]));
  assign wq[b*281+:281]={q[279]&&permit&&!fault&&!(|bad),mirror,mirror?2'b00:(MUT==1?sid^2'b01:sid),q[276:264],q[263:0]};
 end
 assign old_cr=wq_cr;assign old_done=wq_done;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)fault<=0;
  else if((|bad)||(!permit&&|valid))fault<=1;
endmodule
`default_nettype wire
