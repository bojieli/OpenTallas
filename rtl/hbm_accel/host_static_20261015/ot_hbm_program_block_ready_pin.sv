`timescale 1ns/1ps
`default_nettype none
// Physical local readiness child. Actual downstream programme writes land at
// unconditional pin DFFs, then feed the original finite loaded-row validator.
// Ready/fault outputs are pin DFFs. Added1 input+1 status edge is initialization
// latency only; neither can stretch or schedule a running programme.
module ot_hbm_program_block_ready_pin #(parameter integer PCW=10,MUT=0,parameter[7:0]TARGET=48)(
 input wire clk,rst_n,cfg_we,input wire[PCW-1:0]cfg_addr,
 input wire desc_v,input wire[7:0]desc_target,input wire[11:0]desc_base,
 input wire[12:0]desc_limit,input wire[15:0]desc_loops,
 input wire program_active,launch_v,output reg block_ready,output reg fault);
 reg rm,rl,live;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin rm<=0;rl<=0;end else begin rm<=1;rl<=rm;end
 reg cw,dv,pa,lv;reg[PCW-1:0]ca;reg[7:0]dt;reg[11:0]db;reg[12:0]dl;reg[15:0]loops;
 always @(posedge clk)begin
  cw<=cfg_we;ca<=cfg_addr;dv<=desc_v;dt<=desc_target;db<=desc_base;dl<=desc_limit;loops<=desc_loops;
  pa<=program_active;lv<=launch_v;
 end
 wire ready_core,fault_core;
 ot_hbm_program_block_ready #(.PCW(PCW),.MUT(MUT),.TARGET(TARGET)) u_ready(
 .clk(clk),.rst_n(rl),.cfg_we(cw&&live),.cfg_addr(ca),.desc_v(dv&&live),.desc_target(dt),
 .desc_base(db),.desc_limit(dl),.desc_loops(loops),.program_active(pa),.launch_v(lv&&live),
 .block_ready(ready_core),.fault(fault_core));
 always @(posedge clk or negedge rl)
 if(!rl)begin live<=0;block_ready<=0;fault<=0;end
 else begin live<=1;block_ready<=live&&ready_core;fault<=live&&fault_core;end
endmodule
`default_nettype wire
