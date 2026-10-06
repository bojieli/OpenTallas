`timescale 1ns/1ps
// Minimum head physical boundary: copies of the real native fast-domain
// capture registers in ot_dsrom_protected_vm (554d7b0c9/16aa68768).
// These represent existing parent registers, not extra production stages.
// Backend SRAM readback/transport and publication remain actual parent inputs.
// Conditional child proof only; do not substitute this for the parent VM.
(* keep_hierarchy *)
module ot_hdc_v41_fh_vm_endpoint_ctx # (parameter integer ENABLE=0, CHECK_PIPE=0, MARGIN=0)(
 input wire fast_clk,cold_n,
 input wire request_accept,request_warm,checked_reply_capture,published_reply_v,
 input wire [31:0] native_ordinal,
 input wire [46:0] request_owner,
 input wire [7:0] request_id,
 input wire [3:0] head_we,
 input wire [95:0] head_addr,
 input wire [63:0] head_mask,
 input wire [2047:0] head_data,
 input wire [ot_dsrom_vm_pkg::REP_BITS-1:0] checked_reply,
 output wire bounds_fault, endpoint_fault,
 output wire [ot_dsrom_vm_pkg::REQ_BITS-1:0] captured_request,captured_request_check,
 output wire [ot_dsrom_vm_pkg::REP_BITS-1:0] captured_reply,captured_reply_check,
 output wire request_checked_v,reply_checked_v,guard_busy,
 output wire head_ack_v,
 output wire [7:0] head_ack_id,
 output wire [23:0] head_ack_word,
 output wire [15:0] head_ack_mask
);
 import ot_dsrom_vm_pkg::*;
 generate if(ENABLE && CHECK_PIPE) begin : g_distributed_check
  ot_hdc_v41_fh_checked_permission #(.MARGIN(MARGIN)) u_guard(.cold_n_in(cold_n),.*);
 end else if(ENABLE) begin : g_native_endpoints
  assign request_checked_v=request_accept&&!endpoint_fault;
  assign reply_checked_v=published_reply_v&&!endpoint_fault;
  assign guard_busy=0;
  wire [1:0] read_enable=0;
  wire [29:0] read_addr=0;
  wire [4:0] write_enable={head_we,1'b0};
  wire [2559:0] write_data={head_data,512'b0};
  wire [79:0] write_mask={head_mask,16'b0};
  wire [74:0] write_addr;
  wire [3:0] bad_address;
  for(genvar g=0;g<4;g=g+1) begin : g_word
   assign write_addr[(g+1)*15+:15]=head_addr[g*24+:15];
   assign bad_address[g]=head_we[g]&&(|head_addr[g*24+15+:9]);
  end
  assign write_addr[14:0]=0;
  assign bounds_fault=|bad_address;
  request_t accepted_input;
  wire [31:0] serial=native_ordinal;
  // Native normalization, expressed with vector temporaries because the
  // small Icarus gate does not support struct-member part-select assignments.
  // Packed member order is the unchanged native request_t declaration.
  reg [29:0] clean_ra;
  reg [74:0] clean_wa;
  reg [79:0] clean_wm;
  reg [2559:0] clean_wd;
  always @*begin
   clean_ra=0;clean_wa=0;clean_wm=0;clean_wd=0;
   for(integer r=0;r<2;r=r+1)if(read_enable[r])clean_ra[r*15+:15]=read_addr[r*15+:15];
   for(integer w=0;w<5;w=w+1)if(write_enable[w])begin
    clean_wa[w*15+:15]=write_addr[w*15+:15];clean_wm[w*16+:16]=write_mask[w*16+:16];
    for(integer l=0;l<16;l=l+1)if(write_mask[w*16+l])clean_wd[w*512+l*32+:32]=write_data[w*512+l*32+:32];
   end
   accepted_input={serial,request_owner,read_enable,clean_ra,write_enable,clean_wa,clean_wd,clean_wm};
  end
  (* keep=1,dont_touch=1 *) request_t source_packet,source_check;
  (* keep=1,dont_touch=1 *) reply_t held_reply,held_check;
  reg warm,warm_check,ack_sent,ack_sent_check,poison,poison_check;
  reg [7:0] head_id,head_id_check;
  wire matching_reply=source_packet.owner==held_reply.owner&&source_packet.ordinal==held_reply.ordinal&&
      source_packet.we==held_reply.visible&&source_packet.wa==held_reply.wa&&source_packet.wm==held_reply.wm;
  wire bad=source_packet!=~source_check||held_reply!=~held_check||warm!=~warm_check||
      ack_sent!=~ack_sent_check||poison!=~poison_check||head_id!=~head_id_check;
  assign endpoint_fault=poison||bad||bounds_fault;
  always @(posedge fast_clk) begin
   if(!cold_n) begin
    source_packet<=0;source_check<={REQ_BITS{1'b1}};
    held_reply<=0;held_check<={REP_BITS{1'b1}};
    head_id<=0;head_id_check<=8'hff;
    warm<=0;warm_check<=1;ack_sent<=0;ack_sent_check<=1;poison<=0;poison_check<=1;
   end else begin
    if(request_accept&&!endpoint_fault) begin
     source_packet<=accepted_input;source_check<=~accepted_input;
     head_id<=request_id;head_id_check<=~request_id;
     warm<=request_warm;warm_check<=~request_warm;ack_sent<=0;ack_sent_check<=1;
    end
    if(head_ack_v)begin ack_sent<=1;ack_sent_check<=0;end
    if(bad||bounds_fault||(published_reply_v&&!matching_reply))begin poison<=1;poison_check<=0;end
    // This enable is the native matching protected-reply capture, not C8.
    if(checked_reply_capture) begin held_reply<=checked_reply;held_check<=~checked_reply;end
   end
  end
  assign captured_request=source_packet;assign captured_request_check=source_check;
  assign captured_reply=held_reply;assign captured_reply_check=held_check;
  // Native publication has already checked full owner+ordinal/enable/address/
  // mask and protected readback. The head debt owner independently matches
  // these ID/word/mask fields against its retained warm transaction.
  assign head_ack_v=published_reply_v&&held_reply.visible[1]&&warm&&!ack_sent&&matching_reply&&!endpoint_fault;
  assign head_ack_id=head_id;
  assign head_ack_word={9'b0,held_reply.wa[15+:15]};
  assign head_ack_mask=held_reply.wm[16+:16];
 end else begin : g_off
  assign request_checked_v=0;assign reply_checked_v=0;assign guard_busy=0;
  assign bounds_fault=0;assign endpoint_fault=0;assign captured_request=0;assign captured_request_check=0;
  assign captured_reply=0;assign captured_reply_check=0;assign head_ack_v=0;
  assign head_ack_id=0;assign head_ack_word=0;assign head_ack_mask=0;
 end endgenerate
endmodule
