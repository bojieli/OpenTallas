`timescale 1ps/1fs
`default_nettype none
// Dedicated index_path SOURCE_VM_ENABLE=1 -> VM publication parent.
// source_cp_frame is the actual held protected CP tuple, not live permission.
// It stays retained until the caller and provider debts drain. Both sides use
// the same real clk_sm. No formatter85/599 conversion, storage or CDC.
// Model: hbm_vm_publication_parent_model().native_index_binding.
module ot_hbm_native_index_frame_binding #(parameter integer ENABLE=0)(
 input wire [72:0] source_cp_frame,parent_held_frame,
 input wire vm_read_v,output wire vm_read_r,
 input wire [31:0] vm_read_addr,vm_read_job,
 input wire [3:0] vm_read_gen,input wire [19:0] vm_read_pos,
 input wire [6:0] vm_read_rank,input wire [7:0] vm_read_tag,
 input wire [5:0] vm_read_words,
 output wire vm_rsp_v,input wire vm_rsp_r,
 output wire [1023:0] vm_rsp_data,output wire [7:0] vm_rsp_tag,
 output wire [31:0] vm_rsp_job,output wire [3:0] vm_rsp_gen,
 output wire [19:0] vm_rsp_pos,output wire [6:0] vm_rsp_rank,
 output wire index_read_v,input wire index_read_r,
 output wire [31:0] index_read_addr,output wire [72:0] index_read_frame,
 output wire [6:0] index_read_rank,output wire [7:0] index_read_tag,
 output wire [5:0] index_read_words,
 input wire index_rsp_v,output wire index_rsp_r,
 input wire [1023:0] index_rsp_data,input wire [7:0] index_rsp_tag,
 input wire [72:0] index_rsp_frame,input wire [6:0] index_rsp_rank,
 output wire binding_fault
);
 wire request_match=source_cp_frame==parent_held_frame&&
   vm_read_job==source_cp_frame[31:0]&&vm_read_gen==source_cp_frame[35:32]&&
   vm_read_pos==source_cp_frame[72:53];
 wire response_match=index_rsp_frame==source_cp_frame&&source_cp_frame==parent_held_frame;
 assign binding_fault=ENABLE&&((vm_read_v&&!request_match)||(index_rsp_v&&!response_match));
 assign index_read_v=ENABLE&&vm_read_v&&request_match;
 assign vm_read_r=ENABLE&&index_read_r&&request_match;
 assign index_read_addr=ENABLE?vm_read_addr:0;
 assign index_read_frame=ENABLE?source_cp_frame:0;
 assign index_read_rank=ENABLE?vm_read_rank:0;
 assign index_read_tag=ENABLE?vm_read_tag:0;
 assign index_read_words=ENABLE?vm_read_words:0;
 // Debt is gated only by retained identity, never live grant/warm admission.
 // A wrong full frame refuses acknowledgment and reports the actual fault.
 assign vm_rsp_v=ENABLE&&index_rsp_v&&response_match;
 assign index_rsp_r=ENABLE&&vm_rsp_r&&response_match;
 assign vm_rsp_data=ENABLE?index_rsp_data:0;
 assign vm_rsp_tag=ENABLE?index_rsp_tag:0;
 assign vm_rsp_job=ENABLE?index_rsp_frame[31:0]:0;
 assign vm_rsp_gen=ENABLE?index_rsp_frame[35:32]:0;
 assign vm_rsp_pos=ENABLE?index_rsp_frame[72:53]:0;
 assign vm_rsp_rank=ENABLE?index_rsp_rank:0;
endmodule
`default_nettype wire
