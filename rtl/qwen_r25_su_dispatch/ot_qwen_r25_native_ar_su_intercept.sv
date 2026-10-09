`timescale 1ns/1ps
// Actual AR CP producer bound to the finite native namespace interceptor.
// SU request/completion remain real external endpoints in the CP clock domain.
module ot_qwen_r25_native_ar_su_intercept #(parameter integer ENABLE=0,NCMD=256)(
 input wire clk,rst_n,post_en,external_fault,
 input wire job_v,output wire job_rdy,input wire [31:0] job_id,
 input wire [17:0] job_tok,job_eos,input wire [19:0] job_pos,job_ngen,
 input wire job_eos_en,input wire [20:0] job_maxpos,input wire [3:0] job_generation,
 input wire host_stop,output wire hr_v,input wire hr_rdy,output wire [74:0] hr_d,
 input wire [1:0] cmd_we,input wire [2*$clog2(NCMD)-1:0] cmd_addr,input wire [127:0] cmd_wdata,
 output wire [31:0] sm_launch_v,output wire [63:0] sm_launch_pc,
 output wire [147:0] sm_launch_owner,
 input wire [31:0] sm_done,sm_fault,res_v,input wire [1023:0] res_data,
 output wire native_req_v,input wire native_req_rdy,
 output wire [31:0] native_req_pc,output wire [73:0] native_req_owner,
 input wire native_complete_v,output wire native_complete_rdy,
 input wire [73:0] native_complete_owner,input wire native_fault,
 output wire busy,output wire [2:0] last_status,
 output wire [31:0] st_tokens,st_hq_stall,output wire identity_fault,intercept_fault
);
 wire [31:0] cp_launch_v,cp_done,cp_fault;
 wire [63:0] cp_launch_pc;wire [147:0] cp_launch_owner;
 wire [35:0] launch_token;wire [39:0] launch_pos;
 ot_hbm_native_ar_token_join #(.ENABLE(ENABLE),.QWEN(1),.TW(18),.PW(20),.NCMD(NCMD)) u_cp_join(
  .clk(clk),.rst_n(rst_n),.post_en(post_en),.external_fault(external_fault||intercept_fault),
  .job_v(job_v),.job_rdy(job_rdy),.job_id(job_id),.job_tok(job_tok),.job_eos(job_eos),
  .job_pos(job_pos),.job_ngen(job_ngen),.job_eos_en(job_eos_en),.job_maxpos(job_maxpos),
  .job_generation(job_generation),.host_stop(host_stop),.hr_v(hr_v),.hr_rdy(hr_rdy),.hr_d(hr_d),
  .cmd_we(cmd_we),.cmd_addr(cmd_addr),.cmd_wdata(cmd_wdata),
  .launch_v(cp_launch_v),.launch_pc(cp_launch_pc),.launch_token(launch_token),
  .launch_pos(launch_pos),.launch_owner(cp_launch_owner),
  .sm_done(cp_done),.sm_fault(cp_fault),.res_v(res_v),.res_data(res_data),
  .busy(busy),.last_status(last_status),.st_tokens(st_tokens),.st_hq_stall(st_hq_stall),
  .identity_fault(identity_fault));
 ot_qwen_r25_cp_su_coalesce #(.ENABLE(ENABLE)) u_intercept(
  .clk(clk),.rst_n(rst_n),.cp_launch_v(cp_launch_v),.cp_launch_pc(cp_launch_pc),
  .cp_launch_owner(cp_launch_owner),.sm_launch_v(sm_launch_v),.sm_launch_pc(sm_launch_pc),
  .sm_launch_owner(sm_launch_owner),.sm_done(sm_done),.sm_fault(sm_fault),
  .cp_done(cp_done),.cp_fault(cp_fault),.native_req_v(native_req_v),.native_req_rdy(native_req_rdy),
  .native_req_pc(native_req_pc),.native_req_owner(native_req_owner),
  .native_complete_v(native_complete_v),.native_complete_rdy(native_complete_rdy),
  .native_complete_owner(native_complete_owner),.native_fault(native_fault),.fault(intercept_fault));
endmodule
