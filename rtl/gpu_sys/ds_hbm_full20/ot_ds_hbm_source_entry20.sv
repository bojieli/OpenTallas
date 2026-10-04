`timescale 1ns/1ps
// Actual source admission before ANY narrowing: raw token32 and position32.
// A DS1M caller cannot silently alias position1048576 to position0. Fault is
// retained; neither a launch nor a fabricated completion is issued on refusal.
module ot_ds_hbm_source_entry20 #(
 parameter integer ENABLE=0,CONTEXT_POSITIONS=1048576,ND=2,NSM=2,
 parameter integer NL=128,IMW=14,CB=8,NS=2,NPC=2,MEM_WORDS=2097152,USE_W2=0
)(
 input wire por_n,clk_host,clk_sm,clk_mem,clk_link,
 input wire [ND-1:0] cmd_we,input wire [ND*CB-1:0] cmd_addr,
 input wire [ND*64-1:0] cmd_wdata,
 input wire [ND-1:0] db_v,output wire [ND-1:0] db_rdy,
 input wire [ND*32-1:0] db_token,db_pos,db_job,
 input wire [ND*4-1:0] db_generation,
 output wire [ND-1:0] cpl_v,input wire [ND-1:0] cpl_rdy,
 output wire [ND*109-1:0] cpl_data,
 input wire [ND*NSM-1:0] im_we,input wire [IMW-1:0] im_addr,
 input wire [63:0] im_data,output wire rst_sm_n,output wire fault
);
 wire [ND-1:0] admitted_v,inner_ready,valid_tuple;
 wire [ND*17-1:0] tokens;
 wire [ND*20-1:0] positions;
 wire cluster_fault;
 reg source_fault;
 for(genvar d=0;d<ND;d=d+1) begin:g_source
  assign valid_tuple[d]=(db_token[d*32+:32]<131072) && (db_pos[d*32+:32]<CONTEXT_POSITIONS);
  assign tokens[d*17+:17]=db_token[d*32+:17];
  assign positions[d*20+:20]=db_pos[d*32+:20];
  assign admitted_v[d]=ENABLE && db_v[d] && valid_tuple[d] && !source_fault;
  assign db_rdy[d]=ENABLE && inner_ready[d] && valid_tuple[d] && !source_fault;
 end
 initial if(ENABLE && CONTEXT_POSITIONS!=1048576) $fatal(1,"exact DS1M source bound");
 always @(posedge clk_sm or negedge rst_sm_n) begin
  if(!rst_sm_n) source_fault<=0;
  else if(ENABLE && |(db_v & ~valid_tuple)) source_fault<=1;
 end
 ot_ds_hbm_cluster20 #(.ENABLE(ENABLE),.CONTEXT_POSITIONS(CONTEXT_POSITIONS),.ND(ND),.NSM(NSM),
 .NL(NL),.IMW(IMW),.CB(CB),.NS(NS),.NPC(NPC),.MEM_WORDS(MEM_WORDS),.USE_W2(USE_W2)) u_cluster(
 .por_n(por_n),.clk_host(clk_host),.clk_sm(clk_sm),.clk_mem(clk_mem),.clk_link(clk_link),
 .cmd_we(cmd_we),.cmd_addr(cmd_addr),.cmd_wdata(cmd_wdata),
 .db_v(admitted_v),.db_rdy(inner_ready),.db_token(tokens),.db_pos(positions),
 .db_job(db_job),.db_generation(db_generation),.cpl_v(cpl_v),.cpl_rdy(cpl_rdy),.cpl_data(cpl_data),
 .im_we(im_we),.im_addr(im_addr),.im_data(im_data),.rst_sm_n(rst_sm_n),.sys_fault(cluster_fault));
 assign fault=cluster_fault | (ENABLE && source_fault);
endmodule
