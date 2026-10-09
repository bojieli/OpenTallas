`timescale 1ns/1ps
`default_nettype none
// Fresh physical master. Original AR south source is instantiated unchanged.
// Native MTP full-list backend is independent of legacy single-token doorbell.
// Default-off until real providers, operation translator and physical context qualify.
module hfd_cmdproc_s_mtp_native_mx1 #(parameter integer ENABLE_MTP=0)(
 inout wire [826:0] cSE,cSW,
 input wire [0:0] ck,rst,
 input wire [340:0] f_loader,input wire [63:0] f_router,
 output wire [63:0] t_su_SE,t_su_SW,
 input wire [15:0] xb,output wire [146:0] xl,output wire [15:0] xt,
 input wire [516:0] f_mtp,output wire [196:0] t_mtp,
 input wire [215:0] f_host,output wire [4:0] t_host,
 input wire [178:0] f_provider,
 output wire [37:0] t_emit,output wire [42:0] t_provider,
 input wire [1:0] f_emit_host,output wire [99:0] t_emit_host,
 output wire [0:0] t_abort,
 output wire [0:0] t_drained,
 input wire [17:0] f_am,
 input wire [72:0] f_backend,output wire [270:0] t_backend
);
 assign t_emit=ENABLE_MTP?f_mtp[43+:38]:38'b0;
 assign t_provider=ENABLE_MTP?f_mtp[0+:43]:43'b0;
 wire guard_rdy,queue_rdy,queue_ready,queue_fault,guard_fault;
 wire guard_drained,queue_drained;
 // f_backend[71] is actual backend drained_ready AND SM/service quiescence.
 // Native S_DONE holds done until the coordinated drained reset.
 wire [178:0] provider_owned={f_provider[178:140],queue_ready,f_provider[138:0]};
 wire admit=guard_rdy&&queue_rdy&&f_backend[0]&&f_backend[71]&&!f_mtp[43]&&!f_mtp[81]&&!f_mtp[82];
 assign t_host[0]=admit&&!rst[0];
 assign t_drained[0]=guard_drained&&queue_drained&&f_backend[71]&&f_mtp[81]&&!f_mtp[43]&&!f_mtp[82]&&!rst[0];
 assign t_host[4]=guard_fault||queue_fault;
 assign t_abort[0]=guard_fault||queue_fault;
 ot_hbm_native_mtp_emit_queue_mx1 #(.ENABLE(ENABLE_MTP),.DEPTH(8)) emit_queue(
  .clk(ck[0]),.rst_n(~rst[0]),.external_fault(f_backend[72]||guard_fault),
  .job_v(f_host[0]&&admit),.job_rdy(queue_rdy),.job_id(f_host[1+:32]),
  .job_generation(f_host[33+:4]),
  .emit(f_mtp[43+:38]),.native_done(f_mtp[81]),.native_status(f_mtp[514+:3]),
  .emit_ready(queue_ready),.host_v(t_emit_host[0]),.host_ready(f_emit_host[0]),
  .host_data(t_emit_host[1+:73]),.host_done_v(t_emit_host[74]),.host_done_ready(f_emit_host[1]),
  .host_status(t_emit_host[75+:3]),.accepted_count(t_emit_host[78+:21]),.drained_ready(queue_drained),.fault(queue_fault));
 assign t_emit_host[99]=queue_fault;
 hfd_cmdproc_s ar(.cSE(cSE),.cSW(cSW),.ck(ck),.rst(rst),
  .f_loader(f_loader),.f_router(f_router),.t_su_SE(t_su_SE),.t_su_SW(t_su_SW),
  .xb(xb),.xl(xl),.xt(xt));
 ot_hbm_native_mtp_transaction_cp_join_mx1 #(.ENABLE(ENABLE_MTP),.SEQ_W(32)) mtp_owner(
  .clk(ck[0]),.rst_n(~rst[0]),.external_fault(f_backend[72]||queue_fault),.backend_quiescent(f_backend[71]),
  .job_v(f_host[0]&&admit),.job_rdy(guard_rdy),.job_id(f_host[1+:32]),
  .job_generation(f_host[33+:4]),.job_config(f_host[37+:179]),
  .provider_controls(provider_owned),.f_mtp(f_mtp),.t_mtp(t_mtp),
  .eng_cmd_v(t_backend[0]),.eng_cmd_rdy(f_backend[0]),.eng_cmd(t_backend[1+:201]),
  .eng_job(t_backend[202+:32]),.eng_generation(t_backend[234+:4]),
  .eng_sequence(t_backend[238+:32]),
  .cp_am_v(f_am[0]),.cp_am_idx(f_am[1+:17]),
  .eng_cpl_v(f_backend[1]),.eng_cpl_rdy(t_backend[270]),.eng_cpl_job(f_backend[2+:32]),
  .eng_cpl_generation(f_backend[34+:4]),.eng_cpl_sequence(f_backend[38+:32]),
  .eng_cpl_fault(f_backend[70]),
  .drained_ready(guard_drained),.active(t_host[1]),.inflight(t_host[2]),.identity_fault(t_host[3]),.fault(guard_fault));
endmodule
`default_nettype wire
