`timescale 1ns/1ps
// Q-VMWB 2026-10-15: compute-die names of the parallel-band successor serializer qfd_res_train_par (supersedes
// qfd_sp_res_train_<b> / qfd_res_train_static for join961w).  Same pins plus slot_count[3:0]; the three bands land in the
// same cycles on rb0..rb2 (VM PAR_RB=1).  The train command (train_start/count/stride/payload/slot_count) comes from the
// on-die issuer qfd_res_train_issue (TT rom_cmd fields + c1 result tag), one bundle fanned out to the three bands.
// Reset (Q-ELEM-CMP 2026-10-16, die master hardening): rst_n is captured by ONE station flop at the pin (asynchronous
// assert, release on the next ck edge) that drives the body's clear tree (~119k async FF), so the raw reset pin loads one
// flop (native capture <= 190 ps).  Cold init only: the band leaves reset one edge later and is idle until its first
// train_start, which the static schedule issues long after the release.  Bench-only body mutant: +define+OT_QFD_RTP_MUT=<n>.
`ifdef OT_QFD_RTP_MUT
`define OT_QFD_RTP_MUTV `OT_QFD_RTP_MUT
`else
`define OT_QFD_RTP_MUTV 0
`endif

module qfd_sp_res_train_par_0 (
 input wire ck,rst_n,
 input wire ck_bank0,ck_bank1,ck_bank2,ck_bank3,ck_bank4,ck_bank5,ck_bank6,ck_bank7,ck_bank8,ck_bank9,ck_bank10,ck_bank11,ck_bank12,ck_bank13,ck_bank14,ck_bank15,ck_bank16,ck_bank17,ck_bank18,ck_bank19,ck_bank20,ck_bank21,ck_bank22,ck_bank23,
 input wire train_start,input wire[3:0]train_count,input wire[31:0]capture_stride,input wire payload_write,input wire[3:0]slot_count,
 input wire[4424:0]rq,output wire[550:0]rb,output wire fault);
 reg rs_q;
 always @(posedge ck or negedge rst_n) if(!rst_n) rs_q<=1'b0; else rs_q<=1'b1;
 qfd_res_train_par #(.BAND(0),.NB(3),.D(2),.MAX_TRAIN(8),.MUT(`OT_QFD_RTP_MUTV)) u (
  .ck(ck),.rst_n(rs_q),.ck_bank({ck_bank23,ck_bank22,ck_bank21,ck_bank20,ck_bank19,ck_bank18,ck_bank17,ck_bank16,ck_bank15,ck_bank14,ck_bank13,ck_bank12,ck_bank11,ck_bank10,ck_bank9,ck_bank8,ck_bank7,ck_bank6,ck_bank5,ck_bank4,ck_bank3,ck_bank2,ck_bank1,ck_bank0}),
  .train_start(train_start),.train_count(train_count),.capture_stride(capture_stride),.payload_write(payload_write),.slot_count(slot_count),
  .rq(rq),.rb(rb),.fault(fault));
endmodule

module qfd_sp_res_train_par_1 (
 input wire ck,rst_n,
 input wire ck_bank0,ck_bank1,ck_bank2,ck_bank3,ck_bank4,ck_bank5,ck_bank6,ck_bank7,ck_bank8,ck_bank9,ck_bank10,ck_bank11,ck_bank12,ck_bank13,ck_bank14,ck_bank15,ck_bank16,ck_bank17,ck_bank18,ck_bank19,ck_bank20,ck_bank21,ck_bank22,ck_bank23,
 input wire train_start,input wire[3:0]train_count,input wire[31:0]capture_stride,input wire payload_write,input wire[3:0]slot_count,
 input wire[4424:0]rq,output wire[550:0]rb,output wire fault);
 reg rs_q;
 always @(posedge ck or negedge rst_n) if(!rst_n) rs_q<=1'b0; else rs_q<=1'b1;
 qfd_res_train_par #(.BAND(1),.NB(3),.D(2),.MAX_TRAIN(8),.MUT(`OT_QFD_RTP_MUTV)) u (
  .ck(ck),.rst_n(rs_q),.ck_bank({ck_bank23,ck_bank22,ck_bank21,ck_bank20,ck_bank19,ck_bank18,ck_bank17,ck_bank16,ck_bank15,ck_bank14,ck_bank13,ck_bank12,ck_bank11,ck_bank10,ck_bank9,ck_bank8,ck_bank7,ck_bank6,ck_bank5,ck_bank4,ck_bank3,ck_bank2,ck_bank1,ck_bank0}),
  .train_start(train_start),.train_count(train_count),.capture_stride(capture_stride),.payload_write(payload_write),.slot_count(slot_count),
  .rq(rq),.rb(rb),.fault(fault));
endmodule

module qfd_sp_res_train_par_2 (
 input wire ck,rst_n,
 input wire ck_bank0,ck_bank1,ck_bank2,ck_bank3,ck_bank4,ck_bank5,ck_bank6,ck_bank7,ck_bank8,ck_bank9,ck_bank10,ck_bank11,ck_bank12,ck_bank13,ck_bank14,ck_bank15,ck_bank16,ck_bank17,ck_bank18,ck_bank19,ck_bank20,ck_bank21,ck_bank22,ck_bank23,
 input wire train_start,input wire[3:0]train_count,input wire[31:0]capture_stride,input wire payload_write,input wire[3:0]slot_count,
 input wire[4424:0]rq,output wire[550:0]rb,output wire fault);
 reg rs_q;
 always @(posedge ck or negedge rst_n) if(!rst_n) rs_q<=1'b0; else rs_q<=1'b1;
 qfd_res_train_par #(.BAND(2),.NB(3),.D(2),.MAX_TRAIN(8),.MUT(`OT_QFD_RTP_MUTV)) u (
  .ck(ck),.rst_n(rs_q),.ck_bank({ck_bank23,ck_bank22,ck_bank21,ck_bank20,ck_bank19,ck_bank18,ck_bank17,ck_bank16,ck_bank15,ck_bank14,ck_bank13,ck_bank12,ck_bank11,ck_bank10,ck_bank9,ck_bank8,ck_bank7,ck_bank6,ck_bank5,ck_bank4,ck_bank3,ck_bank2,ck_bank1,ck_bank0}),
  .train_start(train_start),.train_count(train_count),.capture_stride(capture_stride),.payload_write(payload_write),.slot_count(slot_count),
  .rq(rq),.rb(rb),.fault(fault));
endmodule
