`timescale 1ns/1ps
// KV-BIND8 2026-10-20 (bench only): stands in for ot_qwen_tp8_pv_wide_ctl_t inside the trunked pair qkd_pvw_die_t so
// tb_qkd_pvw_die_t exercises the pair END FLOOR control ot_qwen_tp8_pv_wide_ctl_tbf with its boot age pinned to the
// static FIRST_INPUT_AGE (ctl_tb == ctl_t #(.FIRST_INPUT_AGE(a)) when cfg_fia = a: rtl/test/kv_bootage_1019/tb_kvba_pvctl.sv).
// `OT_END_FLOOR (default 1) selects the floor; 0 = the shipping control (negative control: pair skew returns).
// KV-FLOOR2 10-20: `OT_CTL_MUT (bench mutant witness, default = the frame's MUT) overrides the control MUT.
`ifndef OT_CTL_MUT
`define OT_CTL_MUT MUT
`endif
`ifndef OT_END_FLOOR
`define OT_END_FLOOR 1
`endif
module ot_qwen_tp8_pv_wide_ctl_t #(parameter integer FIRST_INPUT_AGE=96,parameter integer RESET_PIN=0,parameter integer MUT=0,
 parameter integer TRUNK_D=0,parameter integer FLAG_D=0)(
 input wire clk,rst_n,input wire pair_id,
 input wire start,input wire[13:0] context_len,input wire[15:0] epoch,
 input wire[7:0] in_valid,input wire[111:0] in_t,input wire[127:0] in_epoch,
 output wire[7:0] req_valid,output wire[111:0] req_t,
 output wire[59:0] cmd,input wire[31:0] col_valid,input wire[31:0] col_fault,
 output wire[15:0] out_epoch,output wire fault,output wire busy,output wire[15:0] out_age);
 ot_qwen_tp8_pv_wide_ctl_tbf #(.FIRST_INPUT_AGE(127),.END_FLOOR(`OT_END_FLOOR),.RESET_PIN(RESET_PIN),.MUT(`OT_CTL_MUT),.TRUNK_D(TRUNK_D),
  .FLAG_D(FLAG_D)) u(.clk(clk),.rst_n(rst_n),.cfg_fia(8'(FIRST_INPUT_AGE)),.pair_id(pair_id),.start(start),
  .context_len(context_len),.epoch(epoch),.in_valid(in_valid),.in_t(in_t),.in_epoch(in_epoch),.req_valid(req_valid),
  .req_t(req_t),.cmd(cmd),.col_valid(col_valid),.col_fault(col_fault),.out_epoch(out_epoch),.fault(fault),.busy(busy),
  .out_age(out_age));
endmodule
