`timescale 1ns/1ps
`default_nettype none
// Default OFF. Existing protected stage descriptor replaces the caller's
// stand-alone stage_join; do not instantiate both seats for one operation.
// Actual framed SFU64 child; no opcode arithmetic, VM or provider duplication.
// Model before RTL: hbm_integrated_sfu_c12_stage_model.
// clk must be qualified for the actual source and child. No implicit 3:4 CDC.
module ot_hbm_integrated_sfu_c12_stage #(parameter integer ENABLE=0)(
 input wire clk,por_n,warm_req,output wire warm_ack,
 input wire enroll_v,output wire enroll_r,input wire [72:0] enroll_frame,
 input wire [31:0] enroll_pc,enroll_op,input wire [15:0] enroll_source,
 input wire [8:0] enroll_expert,input wire enroll_matrix,
 input wire [11:0] enroll_row,input wire [8:0] enroll_count,
 input wire owner_valid,input wire [72:0] owner_frame,input wire source_permit,
 // Actual source and consumer receipts, never delay/issue-count completion.
 input wire producer_drained,consumer_drained,
 input wire rx_v,output wire rx_r,input wire [1023:0] rx_d,
 input wire [72:0] rx_owner,input wire rx_first,rx_last,
 output wire tx_v,input wire tx_r,output wire [1023:0] tx_d,
 output wire [72:0] tx_owner,output wire [3:0] tx_index,output wire tx_last,
 output wire complete_v,input wire complete_r,input wire [72:0] complete_owner,
 output wire retained,issued,ce,due,fault,output wire [72:0] held_frame,
 output wire [31:0] held_pc,held_op,output wire [15:0] held_source,
 output wire [8:0] held_expert,output wire held_matrix,
 output wire [11:0] held_row,output wire [8:0] held_count
);
 wire stage_start,stage_finish_r,stage_complete,stage_warm,stage_fault;
 wire child_rx_r,child_tx_v,child_finish,child_complete,child_warm,child_fault;
 wire [72:0] child_owner,child_tx_owner;
 wire receiving=stage_start||issued;
 wire frame_live=owner_valid&&owner_frame==held_frame;
 wire tx_match=child_tx_owner==held_frame;
 wire finish_match=child_owner==held_frame;
 wire complete_match=complete_owner==held_frame;
 wire child_finish_r=stage_finish_r&&finish_match;
 // A wrong accepted completion is presented to the child's protected fatal
 // check. The stage descriptor stays retained rather than retiring that owner.
 wire child_complete_r=complete_r&&stage_complete;
 wire stage_complete_r=complete_r&&child_complete&&complete_match;
 assign rx_r=child_rx_r&&receiving;
 assign tx_v=child_tx_v&&tx_match&&!stage_fault;
 assign tx_owner=child_tx_owner;
 assign complete_v=stage_complete&&child_complete&&!stage_fault&&!child_fault;
 assign warm_ack=stage_warm&&child_warm;
 assign fault=stage_fault||child_fault||
   (child_tx_v&&!tx_match)||(child_finish&&!finish_match)||
   (complete_v&&complete_r&&!complete_match);
 ot_hbm_integrated_stage_join #(.ENABLE(ENABLE)) u_stage(
  .clk(clk),.por_n(por_n),.enroll_v(enroll_v),.enroll_r(enroll_r),
  .enroll_frame(enroll_frame),.enroll_pc(enroll_pc),.enroll_op(enroll_op),
  .enroll_source(enroll_source),.enroll_expert(enroll_expert),
  .enroll_matrix(enroll_matrix),.enroll_row(enroll_row),.enroll_count(enroll_count),
  .owner_valid(owner_valid),.owner_frame(owner_frame),.source_permit(source_permit),
  .start_v(stage_start),.start_r(rx_v&&rx_r&&rx_first&&rx_owner==held_frame),
  .finish_v(child_finish&&finish_match),.finish_r(stage_finish_r),
  .producer_drained(producer_drained),.consumer_drained(consumer_drained),
  .complete_v(stage_complete),.complete_r(stage_complete_r),
  .warm_req(warm_req),.warm_ack(stage_warm),.retained(retained),.issued(issued),
  .ce(ce),.due(due),.fault(stage_fault),.held_frame(held_frame),
  .held_pc(held_pc),.held_op(held_op),.held_source(held_source),
  .held_expert(held_expert),.held_matrix(held_matrix),
  .held_row(held_row),.held_count(held_count));
 ot_hbm_sfu_quarter_framed #(.ENABLE(ENABLE)) u_sfu(
  .clk(clk),.por_n(por_n),
  // Live admission can stop after the first beat. Already admitted packet
  // beats and arithmetic/response/finish/completion debt continue through warm.
  .source_permit(receiving&&!stage_fault),.warm_req(warm_req),.warm_ack(child_warm),
  .rx_v(rx_v&&receiving),.rx_r(child_rx_r),.rx_d(rx_d),
  .owner_valid(retained&&frame_live&&rx_owner==held_frame&&!stage_fault),
  .rx_owner(rx_owner),.rx_first(rx_first),.rx_last(rx_last),
  .tx_v(child_tx_v),.tx_r(tx_r&&tx_match&&!stage_fault),.tx_d(tx_d),
  .tx_owner(child_tx_owner),.tx_index(tx_index),.tx_last(tx_last),
  .finish_v(child_finish),.finish_r(child_finish_r),.finish_owner(held_frame),
  .complete_v(child_complete),.complete_r(child_complete_r),
  .complete_owner(complete_owner),.retained_owner(child_owner),.fault(child_fault));
endmodule
`default_nettype wire
