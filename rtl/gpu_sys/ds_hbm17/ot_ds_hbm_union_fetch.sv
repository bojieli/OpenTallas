`timescale 1ns/1ps
// Actual union -> descriptor -> finite HBM staging -> retained line replay.
// No backing payload dictionary or synthetic request/return/consumer ACK.
// The caller supplies source-selected SM offsets/counts and actual column
// context ready; column-context MMA/epilogue remains a separate connection.
module ot_ds_hbm_union_fetch #(
 parameter integer ENABLE=0,NSM=2,NPC=2,PM=8,IW=9,AW=32,
 parameter integer LENW=5,TAGW=16,BEATW=5,
 parameter integer DEPTH=16,MAX_OUT=8,RUN=4,DQ=2,LAND=4
)(
 input wire clk,rst_n,
 input wire [AW-3:0] cfg_base,input wire [15:0] cfg_exp_lines,
 input wire [NSM*16-1:0] cfg_off,cfg_lines,
 input wire u_v,output wire u_ready,input wire [IW-1:0] u_id,
 input wire [PM-1:0] u_mask,input wire u_last,
 output wire req_v,input wire req_rdy,output wire [AW-1:0] req_addr,
 output wire [LENW-1:0] req_len,output wire [TAGW-1:0] req_tag,
 input wire [NPC-1:0] rsp_v,output wire [NPC-1:0] rsp_rdy,
 input wire [NPC*TAGW-1:0] rsp_tag,input wire [NPC*BEATW-1:0] rsp_beat,
 input wire [NPC*256-1:0] rsp_data,
 output wire [NSM-1:0] out_valid,input wire [NSM-1:0] out_ready,
 output wire [NSM*1024-1:0] out_data,
 output wire [NSM*$clog2(PM)-1:0] out_col,
 output wire [NSM*16-1:0] out_line,output wire [IW-1:0] out_expert,
 output wire expert_done,pass_done,fault
);
generate if(ENABLE==0) begin:g_off
 assign u_ready=0;assign req_v=0;assign req_addr=0;assign req_len=0;assign req_tag=0;assign rsp_rdy=0;
 assign out_valid=0;assign out_data=0;assign out_col=0;assign out_line=0;assign out_expert=0;
 assign expert_done=0;assign pass_done=0;assign fault=0;
end else begin:g_on
 wire e_valid,e_ready,fetch_idle;
 wire [IW-1:0] e_id;
 wire [NSM-1:0] landed_v,landed_ready;
 wire [NSM*1024-1:0] landed_data;
 ot_gpu_expert_fetch #(.NSM(NSM),.NPC(NPC),.DEPTH(DEPTH),.MAX_OUT(MAX_OUT),
 .RUN(RUN),.DQ(DQ),.LAND(LAND),.AW(AW),.LENW(LENW),.TAGW(TAGW),.BEATW(BEATW),.IW(IW)) u_fetch(
 .clk(clk),.rst_n(rst_n),.cfg_base(cfg_base),.cfg_exp_lines(cfg_exp_lines),
 .cfg_off(cfg_off),.cfg_lines(cfg_lines),.e_valid(e_valid),.e_ready(e_ready),.e_id(e_id),
 .req_v(req_v),.req_rdy(req_rdy),.req_addr(req_addr),.req_len(req_len),.req_tag(req_tag),
 .rsp_v(rsp_v),.rsp_rdy(rsp_rdy),.rsp_tag(rsp_tag),.rsp_beat(rsp_beat),.rsp_data(rsp_data),
 .s_valid(landed_v),.s_ready(landed_ready),.s_data(landed_data),.idle(fetch_idle));
 ot_ds_hbm_union_replay #(.ENABLE(1),.NSM(NSM),.PM(PM),.IW(IW)) u_replay(
 .clk(clk),.rst_n(rst_n),.u_v(u_v),.u_ready(u_ready),.u_id(u_id),.u_mask(u_mask),.u_last(u_last),
 .cfg_lines(cfg_lines),.e_valid(e_valid),.e_ready(e_ready),.e_id(e_id),.fetch_idle(fetch_idle),
 .in_valid(landed_v),.in_ready(landed_ready),.in_data(landed_data),
 .out_valid(out_valid),.out_ready(out_ready),.out_data(out_data),.out_col(out_col),.out_line(out_line),
 .out_expert(out_expert),.expert_done(expert_done),.pass_done(pass_done),.fault(fault));
end endgenerate
endmodule
