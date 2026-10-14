`timescale 1ns/1ps
// Typed all-group cache identity. A stage0 start needs the requested RoPE position,
// including on prefetched/same-position hits; no assumed ready-low transition.
module ot_qfd_stage_gate_native_epoch #(parameter integer SW_=6,NW=18,NG=8,MUT=0)(
 input wire clk,rst_n,h_start,input wire[SW_-1:0]stage,input wire[NW-1:0]token,pos,
 input wire[NG-1:0]st_rdy,input wire[NG*SW_-1:0]st_rdy_stage,input wire[NG*NW-1:0]st_rdy_tpos,
 output wire go,output reg[NW-1:0]go_token,go_pos,output reg[SW_-1:0]cur_stage,output wire tok_start);
 reg pend;wire[NG-1:0]qualified;genvar g;
 generate for(g=0;g<NG;g=g+1)begin:g_identity
  assign qualified[g]=st_rdy[g]&&(st_rdy_stage[g*SW_+:SW_]==cur_stage)&&
   ((MUT==2)||(cur_stage!=0)||(st_rdy_tpos[g*NW+:NW]==go_pos));
 end endgenerate
 assign go=pend&&!h_start&&((MUT==1)||(&qualified));
 assign tok_start=h_start&&(stage==0);
 always @(posedge clk or negedge rst_n)if(!rst_n)begin pend<=0;cur_stage<=0;go_token<=0;go_pos<=0;end
 else if(h_start)begin pend<=1;cur_stage<=stage;go_token<=token;go_pos<=pos;end
 else if(go)pend<=0;
endmodule
