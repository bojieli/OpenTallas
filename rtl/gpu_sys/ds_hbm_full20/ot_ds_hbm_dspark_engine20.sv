`timescale 1ns/1ps
// Actual shared-edge DSpark command engine: ordered sequencer -> CP17 -> SM17
// -> inherited real memory/collective RTL -> actual completion join.
// Controller command inputs come from ot_dshbm_dspark_ctl on clk_sm.
// No 16-bit host-ring transport, numeric callback or fake engine_done.
module ot_ds_hbm_dspark_engine20 #(
 parameter integer ENABLE=0,CONTEXT_POSITIONS=1048576,ND=2,NSM=2,NLANES=128,IMW=14,CB=8,
 parameter integer NS=2,NPC=2,MEM_WORDS=2097152,USE_W2=0
)(
 input wire por_n,clk_host,clk_sm,clk_mem,clk_link,
 input wire cmd_v,output wire cmd_ready,input wire [3:0] cmd_op,
 input wire [7:0] cmd_idx,input wire [3:0] cmd_ncol,
 input wire [31:0] cmd_pos,input wire [16:0] cmd_tok1,
 input wire [31:0] cmd_job,input wire [3:0] cmd_generation,
 input wire [8*17-1:0] cmd_toks,
 input wire [11*32-1:0] entry_pc,input wire [16:0] noise_token,
 output wire eng_done,am_v,output wire [16:0] am_idx,
 input wire [ND*NSM-1:0] im_we,
 input wire [IMW-1:0] im_addr,input wire [63:0] im_data,
 output wire rst_sm_n,output wire fault
);
 wire [ND-1:0] cw,dv,dr,cv,cr;
 wire [ND*CB-1:0] ca;wire [ND*64-1:0] cd;
 wire [ND*17-1:0] dt;wire [ND*20-1:0] dp;wire [ND*32-1:0] dj;wire [ND*4-1:0] dg;
 wire [ND*109-1:0] cp;
 wire seq_fault,cluster_fault;
 ot_ds_hbm_ordered_bridge20 #(.ENABLE(ENABLE),.CONTEXT_POSITIONS(CONTEXT_POSITIONS),.ND(ND),.NSM(NSM),.CB(CB)) u_seq(
 .clk(clk_sm),.rst_n(rst_sm_n),.cmd_v(cmd_v),.cmd_ready(cmd_ready),.cmd_op(cmd_op),
 .cmd_idx(cmd_idx),.cmd_ncol(cmd_ncol),.cmd_pos(cmd_pos),.cmd_job(cmd_job),.cmd_generation(cmd_generation),.cmd_tok1(cmd_tok1),.cmd_toks(cmd_toks),
 .entry_pc(entry_pc),.noise_token(noise_token),.eng_done(eng_done),.am_v(am_v),.am_idx(am_idx),.fault(seq_fault),
 .cp_cmd_we(cw),.cp_cmd_addr(ca),.cp_cmd_data(cd),.db_v(dv),.db_rdy(dr),.db_token(dt),.db_pos(dp),.db_job(dj),.db_generation(dg),
 .cpl_v(cv),.cpl_rdy(cr),.cpl_data(cp));
 ot_ds_hbm_cluster20 #(.ENABLE(ENABLE),.CONTEXT_POSITIONS(CONTEXT_POSITIONS),.ND(ND),.NSM(NSM),.NL(NLANES),.IMW(IMW),.CB(CB),
 .NS(NS),.NPC(NPC),.MEM_WORDS(MEM_WORDS),.USE_W2(USE_W2)) u_cluster(
 .por_n(por_n),.clk_host(clk_host),.clk_sm(clk_sm),.clk_mem(clk_mem),.clk_link(clk_link),
 .cmd_we(cw),.cmd_addr(ca),.cmd_wdata(cd),.db_v(dv),.db_rdy(dr),.db_token(dt),.db_pos(dp),.db_job(dj),.db_generation(dg),
 .cpl_v(cv),.cpl_rdy(cr),.cpl_data(cp),.im_we(im_we),.im_addr(im_addr),.im_data(im_data),
 .rst_sm_n(rst_sm_n),.sys_fault(cluster_fault));
 assign fault=seq_fault | cluster_fault;
endmodule
