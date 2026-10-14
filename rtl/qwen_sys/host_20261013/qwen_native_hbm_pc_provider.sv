`timescale 1ns/1ps
// Functional integration top: one genuine pseudo-channel controller plus its
// existing ordered static arbitration. Historical CLOSED modules are unchanged.
module qwen_native_hbm_pc_provider (
 input wire ck, rst_n, pll_hbm, hrst,
 input wire [4:0] pc,
 input wire [287:0] host_es, land_es,
 output wire host_cr, host_ack,
 output wire [260:0] land_er,
 output wire [327:0] po, input wire [288:0] pi,
 input wire [318:0] ci, output wire [293:0] co,
 input wire [32:0] ki, output wire [32:0] ko,
 input wire fi, output wire fo,
 output wire static_fault, completion_fault,
 output wire completion_v, completion_we
);
 wire [287:0] ctrl_es;
 wire [260:0] ctrl_er;
 qkd_host_static_pc u_static (
  .ck(ck), .rst_n(rst_n), .land_es(land_es), .land_er(land_er),
  .host_es(host_es), .host_cr(host_cr), .host_ack(host_ack),
  .ctrl_es(ctrl_es), .ctrl_er(ctrl_er),
  .completion_v(completion_v), .completion_we(completion_we),
  .fault(static_fault));
 qkd_ctrl_pc_host u_ctrl (
  .pll_hbm(pll_hbm), .hrst(hrst), .ck(ck), .rsi(rst_n), .pc(pc),
  .ci(ci), .co(co), .es(ctrl_es), .er(ctrl_er), .po(po), .pi(pi),
  .ki(ki), .ko(ko), .fi(fi), .fo(fo),
  .completion_v(completion_v), .completion_we(completion_we),
  .completion_fault(completion_fault));
endmodule
