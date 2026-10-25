`timescale 1ns/1ps
`default_nettype none
// L12/L13 coherent TKM return. DATA_STAGES are physical data-lane edges;
// any difference to CTL_STAGES is explicit data padding, not an SDC waiver.
// Only control flops reset; data is consumed solely under returned w_v.
module ot_hbm_tkm_return #(
 parameter integer CTL_STAGES=2,DATA_STAGES=2,MUT=0
)(input wire clk,rst_n,input wire in_v,in_busy,in_done,in_fault,
 input wire[39:0]in_addr,input wire[15:0]in_mask,input wire[511:0]in_data,
 output wire out_v,out_busy,out_done,out_fault,output wire[39:0]out_addr,
 output wire[15:0]out_mask,output wire[511:0]out_data);
 initial if(DATA_STAGES<1||CTL_STAGES<DATA_STAGES)$fatal(1,"TKM return needs nonnegative explicit data pad");
 reg[3:0]c[0:CTL_STAGES-1];reg[567:0]d[0:CTL_STAGES-1];
 always@(posedge clk)begin
  if(!rst_n)begin for(integer j=0;j<CTL_STAGES;j=j+1)c[j]<=0;end
  else begin c[0]<={in_busy,in_v,in_done,in_fault};for(integer j=1;j<CTL_STAGES;j=j+1)c[j]<=c[j-1];end
  d[0]<={in_addr,in_mask,in_data};for(integer j=1;j<CTL_STAGES;j=j+1)d[j]<=d[j-1];
 end
 assign {out_v,out_done,out_fault}=c[CTL_STAGES-1][2:0];
 assign out_busy=c[(MUT==1&&CTL_STAGES>1)?CTL_STAGES-2:CTL_STAGES-1][3];
 assign {out_addr,out_mask,out_data}=d[(MUT==2&&CTL_STAGES>1)?CTL_STAGES-2:CTL_STAGES-1];
endmodule
`default_nettype wire
