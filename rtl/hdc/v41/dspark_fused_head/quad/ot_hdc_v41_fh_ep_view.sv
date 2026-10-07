`timescale 1ns/1ps
// Hardened view wrapper of the checked endpoint (ot_hdc_v41_fh_vm_endpoint_ctx ENABLE CHECK_PIPE MARGIN FPIPE=2): the
// clock port is named clk for the physical flow. No logic.
module ot_hdc_v41_fh_ep_view (
 input wire clk,cold_n,
 input wire request_accept,request_warm,checked_reply_capture,published_reply_v,
 input wire [31:0] native_ordinal,
 input wire [46:0] request_owner,
 input wire [7:0] request_id,
 input wire [3:0] head_we,
 input wire [95:0] head_addr,
 input wire [63:0] head_mask,
 input wire [2047:0] head_data,
 input wire [ot_dsrom_vm_pkg::REP_BITS-1:0] checked_reply,
 output wire endpoint_fault,
 output wire [ot_dsrom_vm_pkg::REQ_BITS-1:0] captured_request,
 output wire [ot_dsrom_vm_pkg::REP_BITS-1:0] captured_reply,
 output wire request_checked_v,reply_checked_v,guard_busy,
 output wire head_ack_v,
 output wire [7:0] head_ack_id,
 output wire [23:0] head_ack_word,
 output wire [15:0] head_ack_mask
);
 wire bf;
 wire [ot_dsrom_vm_pkg::REQ_BITS-1:0] c1;
 wire [ot_dsrom_vm_pkg::REP_BITS-1:0] c2;
 ot_hdc_v41_fh_vm_endpoint_ctx #(.ENABLE(1),.CHECK_PIPE(1),.MARGIN(1),.FPIPE(2)) u_ep (
  .fast_clk(clk),.cold_n(cold_n),.request_accept(request_accept),.request_warm(request_warm),
  .checked_reply_capture(checked_reply_capture),.published_reply_v(published_reply_v),
  .native_ordinal(native_ordinal),.request_owner(request_owner),.request_id(request_id),
  .head_we(head_we),.head_addr(head_addr),.head_mask(head_mask),.head_data(head_data),.checked_reply(checked_reply),
  .bounds_fault(bf),.endpoint_fault(endpoint_fault),.captured_request(captured_request),.captured_request_check(c1),
  .captured_reply(captured_reply),.captured_reply_check(c2),.request_checked_v(request_checked_v),
  .reply_checked_v(reply_checked_v),.guard_busy(guard_busy),.head_ack_v(head_ack_v),.head_ack_id(head_ack_id),
  .head_ack_word(head_ack_word),.head_ack_mask(head_ack_mask));
endmodule
