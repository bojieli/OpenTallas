`timescale 1ns/1ps
// One real pre-producer arm transaction. The compiler supplies the operand
// descriptor before presenting its producer instruction. The instruction
// stays held by allow=0 until the registered descriptor has crossed the
// assigned relay latency plus the tap's three-edge arm/write separation.
// This module does not derive an arm from consumer go or infer VM residency.
module ot_qfd_xpf_release_guard #(
 parameter integer ARM_TO_WRITE_EDGES=3, MUT_EARLY=0,
 parameter integer CW=(ARM_TO_WRITE_EDGES<2)?1:$clog2(ARM_TO_WRITE_EDGES+1)
)(
 input wire clk,rst_n,
 input wire arm_v,input wire [71:0] arm_descriptor,
 input wire [11:0] arm_pc,input wire [1:0] arm_unit,
 output wire arm_ready,
 input wire producer_v,input wire [11:0] producer_pc,input wire [1:0] producer_unit,
 input wire producer_requires_arm,
 input wire producer_issue,
 output wire producer_allow,output reg [71:0] xpf,output reg released,
 output reg fault
);
 reg active;reg [CW-1:0] delay_count;reg [11:0] pc;reg [1:0] unit_r;
 assign arm_ready=!active&&!fault;
 wire match=active&&producer_v&&producer_pc==pc&&producer_unit==unit_r;
 assign producer_allow=!fault&&((!active&&!arm_v&&!producer_requires_arm)||(match&&(delay_count==0)));
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;delay_count<=0;pc<=0;unit_r<=0;xpf<=0;released<=0;fault<=0;end
  else begin
   xpf[0]<=0;released<=0;
   if(arm_v&&arm_ready)begin
    if(!arm_descriptor[0]||arm_unit==0)fault<=1;
    else begin
     active<=1;pc<=arm_pc;unit_r<=arm_unit;xpf<=arm_descriptor;
     delay_count<=(MUT_EARLY!=0)?0:ARM_TO_WRITE_EDGES;
    end
   end
   if(active&&delay_count!=0)delay_count<=delay_count-1'b1;
   if(producer_issue)begin
    if(!producer_allow||(arm_v&&arm_ready))fault<=1;
    else if(active)begin active<=0;released<=1;end
   end
   if(fault)xpf[0]<=0;
  end
 end
endmodule
