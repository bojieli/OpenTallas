`timescale 1ps/1fs
// Actual native AR token runtime around two real 16-SM CP halves.
// Default off. MTP commit join and physical budget are separately outstanding.
module ot_hbm_native_ar_token_join #(
 parameter integer ENABLE=0,QWEN=0,TW=QWEN?18:17,PW=20,NCMD=256
)(
 input wire clk,rst_n,post_en,external_fault,
 input wire job_v,output wire job_rdy,input wire [31:0] job_id,
 input wire [TW-1:0] job_tok,job_eos,input wire [PW-1:0] job_pos,job_ngen,
 input wire job_eos_en,input wire [PW:0] job_maxpos,input wire [3:0] job_generation,
 input wire host_stop,
 output wire hr_v,input wire hr_rdy,output wire [TW+PW+36:0] hr_d,
 input wire [1:0] cmd_we,input wire [2*$clog2(NCMD)-1:0] cmd_addr,
 input wire [127:0] cmd_wdata,
 output wire [31:0] launch_v,output wire [63:0] launch_pc,
 output wire [2*TW-1:0] launch_token,output wire [2*PW-1:0] launch_pos,
 output wire [2*(TW+PW+36)-1:0] launch_owner,
 input wire [31:0] sm_done,sm_fault,res_v,input wire [1023:0] res_data,
 output wire busy,output wire [2:0] last_status,
 output wire [31:0] st_tokens,st_hq_stall,output wire identity_fault
);
 wire db_v,db_rdy,cpl_rdy;wire [TW-1:0] db_token;
 wire [PW-1:0] db_pos;wire [31:0] db_job;
 wire [1:0] cp_db_rdy,cp_cpl_v;wire [2*TW-1:0] cp_token;
 wire [7:0] cp_status;wire [63:0] cp_job;wire [7:0] cp_gen;
 wire [2*PW-1:0] cp_pos;
 reg [3:0] generation;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) generation<=0;
  else if(ENABLE && job_v && job_rdy) generation<=job_generation;
 wire both= &cp_cpl_v;
 assign identity_fault=both && (cp_job[31:0]!=db_job || cp_job[63:32]!=db_job ||
  cp_gen[3:0]!=generation || cp_gen[7:4]!=generation ||
  cp_pos[PW-1:0]!=db_pos || cp_pos[2*PW-1:PW]!=db_pos ||
  cp_token[TW-1:0]!=cp_token[2*TW-1:TW]);
 wire [3:0] status=identity_fault?4'd3:(cp_status[3:0]!=0?cp_status[3:0]:cp_status[7:4]);
 wire jr;
 assign job_rdy=ENABLE && jr && !external_fault;
 assign db_rdy=&cp_db_rdy;
 ot_hbm_token_loop #(.TW(TW),.PW(PW),.EXTERNAL_FAULT_EN(1)) u_loop(
  .clk(clk),.rst_n(rst_n),.post_en(post_en),.external_fault(external_fault),
  .job_v(ENABLE && job_v && !external_fault),.job_rdy(jr),.job_id(job_id),.job_tok(job_tok),.job_pos(job_pos),
  .job_ngen(job_ngen),.job_eos(job_eos),.job_eos_en(job_eos_en),.job_maxpos(job_maxpos),.job_mtp(1'b0),
  .host_stop(host_stop),.hr_v(hr_v),.hr_rdy(hr_rdy),.hr_d(hr_d),
  .db_v(db_v),.db_rdy(db_rdy),.db_token(db_token),.db_pos(db_pos),.db_job(db_job),
  .cpl_v(both),.cpl_rdy(cpl_rdy),.cpl_token(status==0?cp_token[TW-1:0]:{TW{1'b0}}),.cpl_status(status),
  .mtp_v(1'b0),.mtp_n(3'b0),.mtp_tok({6*TW{1'b0}}),
  .busy(busy),.last_status(last_status),.st_tokens(st_tokens),.st_hq_stall(st_hq_stall));
 generate for(genvar k=0;k<2;k=k+1) begin:g_half
  // Actual producer identity: job32, generation4, TOKEN17/18, position20.
  assign launch_owner[k*(TW+PW+36)+:(TW+PW+36)] = {launch_pos[k*PW+:PW],launch_token[k*TW+:TW],cp_gen[k*4+:4],cp_job[k*32+:32]};
  if(QWEN) begin:g_qwen
   ot_qwen_r25_cmdproc18 #(.ENABLE(ENABLE),.NSM(16),.NCMD(NCMD),.TW(TW),.PW(PW)) u_cp(
    .clk(clk),.rst_n(rst_n && !external_fault),.cmd_we(cmd_we[k] && !busy),
    .cmd_addr(cmd_addr[k*$clog2(NCMD)+:$clog2(NCMD)]),.cmd_wdata(cmd_wdata[k*64+:64]),
    .db_v(db_v && db_rdy),.db_rdy(cp_db_rdy[k]),.db_token(db_token),.db_pos(db_pos),
    .db_job(db_job),.db_generation(generation),.cpl_position(cp_pos[k*PW+:PW]),
    .cpl_job(cp_job[k*32+:32]),.cpl_generation(cp_gen[k*4+:4]),
    .launch_v(launch_v[k*16+:16]),.launch_pc(launch_pc[k*32+:32]),
    .launch_token(launch_token[k*TW+:TW]),.launch_pos(launch_pos[k*PW+:PW]),
    .sm_done(sm_done[k*16+:16]),.sm_fault(sm_fault[k*16+:16]),
    .res_v(res_v[k*16+:16]),.res_data(res_data[k*512+:512]),
    .cpl_v(cp_cpl_v[k]),.cpl_rdy(cpl_rdy && both),.cpl_token(cp_token[k*TW+:TW]),
    .cpl_status(cp_status[k*4+:4]),.cpl_cycles(),.st_kernels(),.st_busy());
  end else begin:g_ds
   ot_ds_hbm_cmdproc20 #(.ENABLE(ENABLE),.NSM(16),.NCMD(NCMD),.TW(TW),.PW(PW)) u_cp(
    .clk(clk),.rst_n(rst_n && !external_fault),.cmd_we(cmd_we[k] && !busy),
    .cmd_addr(cmd_addr[k*$clog2(NCMD)+:$clog2(NCMD)]),.cmd_wdata(cmd_wdata[k*64+:64]),
    .db_v(db_v && db_rdy),.db_rdy(cp_db_rdy[k]),.db_token(db_token),.db_pos(db_pos),
    .db_job(db_job),.db_generation(generation),.cpl_position(cp_pos[k*PW+:PW]),
    .cpl_job(cp_job[k*32+:32]),.cpl_generation(cp_gen[k*4+:4]),
    .launch_v(launch_v[k*16+:16]),.launch_pc(launch_pc[k*32+:32]),
    .launch_token(launch_token[k*TW+:TW]),.launch_pos(launch_pos[k*PW+:PW]),
    .sm_done(sm_done[k*16+:16]),.sm_fault(sm_fault[k*16+:16]),
    .res_v(res_v[k*16+:16]),.res_data(res_data[k*512+:512]),
    .cpl_v(cp_cpl_v[k]),.cpl_rdy(cpl_rdy && both),.cpl_token(cp_token[k*TW+:TW]),
    .cpl_status(cp_status[k*4+:4]),.cpl_cycles(),.st_kernels(),.st_busy());
  end
 end endgenerate
endmodule
