`timescale 1ns/1ps
// Normative unit9 SELECT=3 retains the shipped DS router mechanism/cycles.
// TOPK=2 is separately bound to the generic TOPK adapter; never aliases SELECT.
// Command record precedes its score stream. Default DS path is independent of
// generic enable. Dispatcher/VM descriptors are owned by the command processor.
module ot_hgi_idx_ds_dispatch #(
 parameter integer N=384,P=16,K=6,IW=9,
 parameter bit MUTANT_DROP_LAST=0
)(
 input wire clk,rst_n,cmd_valid,
 input wire [3:0]cmd_unit,input wire [5:0]cmd_op,
 output wire cmd_ready,output reg error,
 input wire ds_in_valid,input wire [P*32-1:0]ds_in_vals,input wire ds_in_last,
 output wire ds_in_ready,output wire ds_out_valid,output wire [K*IW-1:0]ds_out_ids,
 output wire done
);
 reg active,reject_done;
 assign cmd_ready=!active;
 assign ds_in_ready=active;
 assign done=ds_out_valid||reject_done;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;error<=0;reject_done<=0;end
  else begin
   reject_done<=0;
   if(cmd_valid&&cmd_ready)begin
    if(cmd_unit==9&&cmd_op==3)begin active<=1;error<=0;end
    else begin error<=1;reject_done<=1;end
   end
   if(ds_out_valid)active<=0;
  end
 end
 ot_gpu_router_topk #(.N(N),.P(P),.K(K),.IW(IW)) ds(
 .clk(clk),.rst_n(rst_n),.in_valid(ds_in_valid&&active),.in_vals(ds_in_vals),
 .in_last(ds_in_last&&!MUTANT_DROP_LAST),.out_valid(ds_out_valid),.out_ids(ds_out_ids));
endmodule
