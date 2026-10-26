`timescale 1ns/1ps
`default_nettype none
// Two north-half launch collars feed the one root identity collector.  The
// selected launch is captured by its existing face register: no added cycle.
// Simultaneous copies of the same identity coalesce; differing identities fault.
module ot_hbm_router_ids_static_2src #(
 parameter integer XRT=2, GO_DELAY=1, CQ_DELAY=1, MUT=0
)(
 input wire clk,rst_n,
 input wire run_v, input wire[7:0] run_layer,
 input wire run1_v, input wire[7:0] run1_layer,
 input wire topk_go,input wire[155:0]topk_rec,
 input wire[337:0]cq,input wire[1:0]cq_seq,
 output wire ids_v,output wire[7:0]ids_layer,output wire[53:0]ids,
 output wire[15:0]ids_cohort,output wire fault
);
 reg v1_delay;
 reg[7:0] l1_delay;
 always @(posedge clk)begin
  if(!rst_n)v1_delay<=0;else v1_delay<=run1_v;
  l1_delay<=run1_layer;
 end
 wire v1=MUT==3?v1_delay:(run1_v&&(MUT!=1));
 wire[7:0] l1=(MUT==3?l1_delay:run1_layer)+(MUT==2?8'd1:8'd0);
 wire disagree=run_v&&v1&&(run_layer!=l1);
 reg identity_fault;
 always @(posedge clk)begin
  if(!rst_n)identity_fault<=0;
  else if(disagree)identity_fault<=1;
 end
 wire base_fault;
 ot_hbm_router_ids_static #(.XRT(XRT),.GO_DELAY(GO_DELAY),.CQ_DELAY(CQ_DELAY)) u_base(
  .clk(clk),.rst_n(rst_n),.run_v(run_v||v1),.run_layer(run_v?run_layer:l1),
  .topk_go(topk_go),.topk_rec(topk_rec),.cq(cq),.cq_seq(cq_seq),
  .ids_v(ids_v),.ids_layer(ids_layer),.ids(ids),.ids_cohort(ids_cohort),.fault(base_fault));
 assign fault=base_fault||identity_fault;
endmodule
`default_nettype wire
