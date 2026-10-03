`timescale 1ns/1ps
module ot_ds_hbm_simulator20 #(
 parameter integer ENABLE=0, TW=17, PW=20, CONTEXT_POSITIONS=1048576, ND=2, NSM=2, NL=128, IMW=14,
 parameter integer CB=8, NS=2, NPC=2, MEM_WORDS=2097152,
 parameter integer SW_PIPE=8, USE_W2=0, HAS_DIV=1, HAS_BD=1
)(
 input wire por_n, clk_host, clk_sm, clk_mem, clk_link,
 input wire [ND-1:0] cmd_we,
 input wire [ND*CB-1:0] cmd_addr,
 input wire [ND*64-1:0] cmd_wdata,
 input wire [ND-1:0] db_v, output wire [ND-1:0] db_rdy,
 input wire [ND*TW-1:0] db_token,
 input wire [ND*PW-1:0] db_pos,
 input wire [ND*32-1:0] db_job,
 input wire [ND*4-1:0] db_generation,
 output wire [ND-1:0] cpl_v, input wire [ND-1:0] cpl_rdy,
 output wire [ND*(TW+PW+72)-1:0] cpl_data,
 input wire [ND*NSM-1:0] im_we,
 input wire [IMW-1:0] im_addr, input wire [63:0] im_data,
 output wire rst_sm_n, output wire sys_fault,
 output wire [ND*NSM*32-1:0] debug_pc,debug_instructions,debug_stall_mem,
 output wire [ND*NSM-1:0] debug_busy
);
// Simulation-only port wrapper; no new execution or storage hardware.
 ot_ds_hbm_cluster20 #(.ENABLE(ENABLE),.TW(TW),.PW(PW),.CONTEXT_POSITIONS(CONTEXT_POSITIONS),
 .ND(ND),.NSM(NSM),.NL(NL),.IMW(IMW),.CB(CB),.NS(NS),.NPC(NPC),
 .MEM_WORDS(MEM_WORDS),.SW_PIPE(SW_PIPE),.USE_W2(USE_W2),.HAS_DIV(HAS_DIV),.HAS_BD(HAS_BD)) u_cluster(.*);
 generate if(ENABLE) begin:g_debug
 for(genvar d=0;d<ND;d=d+1) begin:g_die
 for(genvar s=0;s<NSM;s=s+1) begin:g_sm
 assign debug_pc[(d*NSM+s)*32+:32]=32'(u_cluster.g_on.g_die[d].g_sm[s].u_sm.g_on.pc);
 assign debug_instructions[(d*NSM+s)*32+:32]=u_cluster.g_on.g_die[d].g_sm[s].st_instr;
 assign debug_stall_mem[(d*NSM+s)*32+:32]=u_cluster.g_on.g_die[d].g_sm[s].st_stall_mem;
 assign debug_busy[d*NSM+s]=u_cluster.g_on.g_die[d].busy[s];
 end end
 end else begin:g_no_debug
 assign debug_pc=0;assign debug_instructions=0;assign debug_stall_mem=0;assign debug_busy=0;
 end endgenerate
endmodule
