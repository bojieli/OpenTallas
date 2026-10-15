`timescale 1ns/1ps
// Compute-die names of the adopted band result serializer (Q-ATTN r3 decision 2026-10-15, main 00b0a6886:
// Codex fixed train24 banks qfd_res_train_static, join961t).  Replaces the legacy qfd_sp_res_ser die master whose
// i port has a different bit order from qfd_port_tiles_b.rq (die contracts c8..c17 were functionally wrong).
// One die name per band (BAND sets the fixed emission calendar).  Pure wrapper: the 24 bank clock entries are scalar
// die ports ck_bank0..23 (one per-child clock entry each, as the slab masters' ck_col*), everything else is the
// source port 1:1.  train_start / train_count / capture_stride / payload_write are compiler-calendar inputs from the
// TT ME-issue calendar (producer open: Q-FUNC); never tied in the die.

module qfd_sp_res_train_0 (
 input wire ck,rst_n,
 input wire ck_bank0,ck_bank1,ck_bank2,ck_bank3,ck_bank4,ck_bank5,ck_bank6,ck_bank7,ck_bank8,ck_bank9,ck_bank10,ck_bank11,ck_bank12,ck_bank13,ck_bank14,ck_bank15,ck_bank16,ck_bank17,ck_bank18,ck_bank19,ck_bank20,ck_bank21,ck_bank22,ck_bank23,
 input wire train_start,input wire[3:0]train_count,input wire[31:0]capture_stride,input wire payload_write,
 input wire[4424:0]rq,output wire[550:0]rb,output wire fault);
 qfd_res_train_static #(.BAND(0),.NB(3),.D(2),.MAX_TRAIN(8)) u (
  .ck(ck),.rst_n(rst_n),.ck_bank({ck_bank23,ck_bank22,ck_bank21,ck_bank20,ck_bank19,ck_bank18,ck_bank17,ck_bank16,ck_bank15,ck_bank14,ck_bank13,ck_bank12,ck_bank11,ck_bank10,ck_bank9,ck_bank8,ck_bank7,ck_bank6,ck_bank5,ck_bank4,ck_bank3,ck_bank2,ck_bank1,ck_bank0}),
  .train_start(train_start),.train_count(train_count),.capture_stride(capture_stride),.payload_write(payload_write),
  .rq(rq),.rb(rb),.fault(fault));
endmodule

module qfd_sp_res_train_1 (
 input wire ck,rst_n,
 input wire ck_bank0,ck_bank1,ck_bank2,ck_bank3,ck_bank4,ck_bank5,ck_bank6,ck_bank7,ck_bank8,ck_bank9,ck_bank10,ck_bank11,ck_bank12,ck_bank13,ck_bank14,ck_bank15,ck_bank16,ck_bank17,ck_bank18,ck_bank19,ck_bank20,ck_bank21,ck_bank22,ck_bank23,
 input wire train_start,input wire[3:0]train_count,input wire[31:0]capture_stride,input wire payload_write,
 input wire[4424:0]rq,output wire[550:0]rb,output wire fault);
 qfd_res_train_static #(.BAND(1),.NB(3),.D(2),.MAX_TRAIN(8)) u (
  .ck(ck),.rst_n(rst_n),.ck_bank({ck_bank23,ck_bank22,ck_bank21,ck_bank20,ck_bank19,ck_bank18,ck_bank17,ck_bank16,ck_bank15,ck_bank14,ck_bank13,ck_bank12,ck_bank11,ck_bank10,ck_bank9,ck_bank8,ck_bank7,ck_bank6,ck_bank5,ck_bank4,ck_bank3,ck_bank2,ck_bank1,ck_bank0}),
  .train_start(train_start),.train_count(train_count),.capture_stride(capture_stride),.payload_write(payload_write),
  .rq(rq),.rb(rb),.fault(fault));
endmodule

module qfd_sp_res_train_2 (
 input wire ck,rst_n,
 input wire ck_bank0,ck_bank1,ck_bank2,ck_bank3,ck_bank4,ck_bank5,ck_bank6,ck_bank7,ck_bank8,ck_bank9,ck_bank10,ck_bank11,ck_bank12,ck_bank13,ck_bank14,ck_bank15,ck_bank16,ck_bank17,ck_bank18,ck_bank19,ck_bank20,ck_bank21,ck_bank22,ck_bank23,
 input wire train_start,input wire[3:0]train_count,input wire[31:0]capture_stride,input wire payload_write,
 input wire[4424:0]rq,output wire[550:0]rb,output wire fault);
 qfd_res_train_static #(.BAND(2),.NB(3),.D(2),.MAX_TRAIN(8)) u (
  .ck(ck),.rst_n(rst_n),.ck_bank({ck_bank23,ck_bank22,ck_bank21,ck_bank20,ck_bank19,ck_bank18,ck_bank17,ck_bank16,ck_bank15,ck_bank14,ck_bank13,ck_bank12,ck_bank11,ck_bank10,ck_bank9,ck_bank8,ck_bank7,ck_bank6,ck_bank5,ck_bank4,ck_bank3,ck_bank2,ck_bank1,ck_bank0}),
  .train_start(train_start),.train_count(train_count),.capture_stride(capture_stride),.payload_write(payload_write),
  .rq(rq),.rb(rb),.fault(fault));
endmodule
