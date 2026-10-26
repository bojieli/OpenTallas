`timescale 1ns/1ps
`default_nettype none
// Actual COMPACT1 target48 producer. Installation evidence observes the real
// downstream programme write port, never the upstream host's promise.
module ot_hbm_host_qdq_installed_target #(parameter integer MUT=0)(
 input wire clk,rst_n,cfg_v,input wire[7:0]cfg_target,input wire[11:0]cfg_addr,
 input wire[255:0]cfg_data,input wire desc_v,input wire[11:0]desc_base,
 input wire[12:0]desc_limit,input wire[15:0]desc_loops,input wire launch_v,
 output wire block_ready,active,done,configured,fault,
 output wire[47:0]command,output wire command_v,output wire[31:0]ordinal);
 wire actual_we,pfault,rfault,ready;
 wire[9:0]actual_addr;reg bad_loop;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)bad_loop<=0;
  else if(desc_v&&cfg_target==48&&desc_loops!=1)bad_loop<=1;
 assign block_ready=ready&&!bad_loop&&!pfault;
 // An invalid external launch is a fault; it cannot start uninstalled SRAM.
 wire accepted_launch=launch_v&&block_ready;
 ot_hgi_qdq_native_program_leaf #(.COMPACT(1)) u_program(
 .clk(clk),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(accepted_launch),
 .command(command),.command_v(command_v),.ordinal(ordinal),.active(active),.done(done),.configured(configured),.fault(pfault),
 .installed_cfg_we(actual_we),.installed_cfg_addr(actual_addr));
 ot_hbm_program_block_ready #(.TARGET(48),.PCW(10),.MUT(MUT)) u_ready(
 .clk(clk),.rst_n(rst_n),.cfg_we(actual_we),.cfg_addr(actual_addr),.desc_v(desc_v),.desc_target(cfg_target),
 .desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.program_active(active),.launch_v(launch_v),
 .block_ready(ready),.fault(rfault));
 assign fault=pfault|rfault|bad_loop;
endmodule
`default_nettype wire
