`timescale 1ns/1ps
// Enclosing full-width owner/descriptor join for Franklin's existing live GU
// producer and consumer. No arithmetic, payload storage, grant or capture helper.
// The BF16 payload remains the original producer -> existing consumer wire.
module ot_hbm_integrated_gu_descriptor_join #(parameter integer ENABLE=0)(
 input wire clk,por_n,enroll_v,output wire enroll_r,
 input wire [72:0] enroll_frame,input wire [31:0] enroll_conversion_pc,enroll_op,
 input wire [15:0] enroll_source,input wire [8:0] enroll_expert,
 input wire enroll_matrix,input wire [11:0] enroll_row,input wire [8:0] enroll_count,
 input wire owner_valid,input wire [72:0] owner_frame,input wire real_source_permit,
 input wire native_quiet,producer_retained,producer_ce,producer_due,producer_fault,producer_terminal,
 input wire producer_v,input wire [72:0] producer_frame,input wire [31:0] producer_op,
 input wire [15:0] producer_source,input wire [8:0] producer_expert,
 input wire producer_matrix,input wire [11:0] producer_row,
 input wire [8:0] producer_count,input wire [7:0] producer_lane_first,
 output wire consumer_v,input wire consumer_accept,consumer_drained,
 output wire producer_accept,output wire native_launch,
 output wire [16:0] native_token,output wire [19:0] native_position,
 output wire [72:0] held_frame,output wire [31:0] held_conversion_pc,held_op,
 output wire [15:0] held_source,output wire [8:0] held_expert,
 output wire held_matrix,output wire [11:0] held_row,output wire [8:0] held_count,
 output wire complete_v,input wire complete_r,
 input wire warm_req,output wire warm_ack,retained,ce,due,fault
);
 wire start_v,issued,finish_r;
 wire native_drained=native_quiet&&!producer_retained&&!producer_ce&&!producer_due;
 wire tuple_match=producer_frame==held_frame&&producer_op==held_op&&
   producer_source==held_source&&producer_expert==held_expert&&
   producer_matrix==held_matrix&&producer_row==held_row&&
   producer_count==held_count&&producer_lane_first==0;
 // Identity veto must not feed back through issued -> fault -> owner_valid.
 // During enclosing CE the genuine producer keeps valid asserted; acceptance
 // pauses through consumer_v, without declaring that held payload foreign.
 wire bad_export=producer_v&&!tuple_match;
 wire qualified_owner=owner_valid&&!producer_fault&&!producer_due&&!bad_export;
 wire start_ready=native_drained;
 assign native_launch=start_v&&start_ready;
 assign native_token=held_frame[52:36];assign native_position=held_frame[72:53];
 assign consumer_v=producer_v&&issued&&tuple_match&&qualified_owner&&!ce&&!due&&!fault;
 assign producer_accept=consumer_v&&consumer_accept;
 ot_hbm_integrated_stage_join #(.ENABLE(ENABLE)) seat(
  .clk(clk),.por_n(por_n),.enroll_v(enroll_v),.enroll_r(enroll_r),
  .enroll_frame(enroll_frame),.enroll_pc(enroll_conversion_pc),.enroll_op(enroll_op),
  .enroll_source(enroll_source),.enroll_expert(enroll_expert),.enroll_matrix(enroll_matrix),
  .enroll_row(enroll_row),.enroll_count(enroll_count),
  .owner_valid(qualified_owner),.owner_frame(owner_frame),.source_permit(real_source_permit),
  .start_v(start_v),.start_r(start_ready),
  .finish_v(producer_terminal&&native_drained&&consumer_drained),.finish_r(finish_r),
  .producer_drained(native_drained),.consumer_drained(consumer_drained),
  .complete_v(complete_v),.complete_r(complete_r),.warm_req(warm_req),.warm_ack(warm_ack),
  .retained(retained),.issued(issued),.ce(ce),.due(due),.fault(fault),
  .held_frame(held_frame),.held_pc(held_conversion_pc),.held_op(held_op),
  .held_source(held_source),.held_expert(held_expert),.held_matrix(held_matrix),
  .held_row(held_row),.held_count(held_count));
endmodule
