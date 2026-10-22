`timescale 1ns/1ps
// Compute-local identity/commit root for the actual statically scheduled
// remote KV attention service. Every launch/consume/completion cycle comes
// from the compiler. Missing resource/data is a fault, never a deferred issue.
// Local CMD does not wait for a KV-commit response. The actual remote
// controller/landing checks TAG59/generation/mask/address/ticket visibility at
// compiled read slots and returns real fault/status before completion. The
// selected compiler must account for that return deadline; no fake ACK exists.
// This module contains no arithmetic and cannot fabricate Q or result words.
// TAG59={epoch16,stage6,token18,position13,segment6}; stages1..36.
module qfd_native59_static_service #(
 parameter integer MUT_EARLY_COMPLETE=0
)(
 input wire ck,rst_n,input wire source_fault,
 input wire begin_slot,input wire [58:0] begin_tag,
 input wire request_slot,input wire [58:0] request_tag,input wire [19:0] result_base_word,
 input wire qr_committed,input wire [58:0] qr_tag,
 output reg kernel_request_v,output reg [58:0] kernel_request_tag,
 input wire q_slot,input wire [4:0] q_slot_beat,
 input wire q_v,input wire [4:0] q_beat,input wire [58:0] q_tag,input wire [511:0] q_data,
 output reg kernel_q_v,output reg [4:0] kernel_q_beat,output reg [58:0] kernel_q_tag,output reg [511:0] kernel_q_data,
 input wire result_slot,input wire [4:0] result_slot_beat,
 input wire result_v,input wire [4:0] result_beat,input wire [58:0] result_tag,input wire [511:0] result_data,
 output reg vm_write_v,output reg [19:0] vm_write_word,output reg [4:0] vm_write_beat,
 output reg [58:0] vm_write_tag,output reg [511:0] vm_write_data,
 input wire vm_commit_v,input wire [4:0] vm_commit_beat,input wire [58:0] vm_commit_tag,
 input wire kernel_done,input wire [58:0] kernel_done_tag,
 input wire complete_slot,output reg completed,output reg active,output reg fault,output wire [94:0] native_ret
);
 reg [58:0] tag;
 reg [19:0] base;
 reg requested,done_seen,context_valid;reg [5:0] q_count,result_count,commit_count;
 reg [31:0] q_seen,result_seen,committed;
 wire legal_tag=begin_tag[42:37]>=1&&begin_tag[42:37]<=36&&begin_tag[36:19]<151936&&begin_tag[5:0]==0;
 // NativePC11 guard proves argmax and weight-ROM accesses inactive. Status
 // reports actual single-operation availability even after completion, when
 // the head still selects this face before the next ordinary-ROM command.
 assign native_ret={fault,{10'd0,commit_count},76'd0,(!active&&!fault),(!active&&!fault)};
 wire complete_ok=requested&&done_seen&&(&q_seen)&&(&result_seen)&&(&committed);
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin
   tag<=0;base<=0;context_valid<=0;commit_count<=0;requested<=0;done_seen<=0;q_seen<=0;result_seen<=0;committed<=0;q_count<=0;result_count<=0;
   kernel_request_v<=0;kernel_request_tag<=0;kernel_q_v<=0;kernel_q_beat<=0;kernel_q_tag<=0;kernel_q_data<=0;
   vm_write_v<=0;vm_write_word<=0;vm_write_beat<=0;vm_write_tag<=0;vm_write_data<=0;
   completed<=0;active<=0;fault<=0;
  end else begin
   kernel_request_v<=request_slot&&!fault&&!source_fault;
   kernel_q_v<=q_slot&&!fault&&!source_fault;
   vm_write_v<=result_slot&&!fault&&!source_fault;
   completed<=0;
   if(source_fault)fault<=1;
   if(begin_slot)begin
    if(active||!legal_tag)fault<=1;
    else begin context_valid<=1;commit_count<=0;tag<=begin_tag;requested<=0;done_seen<=0;q_seen<=0;result_seen<=0;committed<=0;q_count<=0;result_count<=0;end
   end
   if(request_slot)begin
    kernel_request_tag<=request_tag;base<=result_base_word;
    if(!context_valid||active||requested||request_tag!=tag||!qr_committed||qr_tag!=tag||result_base_word>20'hfffe0)fault<=1;
    requested<=1;active<=1;
   end
   // An unexpected or absent native producer cannot silently change its slot.
   if(q_v!=q_slot)fault<=1;
   if(q_slot)begin
    kernel_q_beat<=q_slot_beat;kernel_q_tag<=q_tag;kernel_q_data<=q_data;q_count<=q_count+1'b1;
    if(!active||!requested||q_tag!=tag||q_beat!=q_slot_beat||q_seen[q_slot_beat]||q_count!={1'b0,q_slot_beat})fault<=1;
    q_seen[q_slot_beat]<=1;
   end
   if(result_v!=result_slot)fault<=1;
   if(result_slot)begin
    vm_write_word<=base+result_slot_beat;vm_write_beat<=result_slot_beat;
    vm_write_tag<=result_tag;vm_write_data<=result_data;result_count<=result_count+1'b1;
    if(!active||!requested||result_tag!=tag||result_beat!=result_slot_beat||result_seen[result_slot_beat]||result_count!={1'b0,result_slot_beat})fault<=1;
    result_seen[result_slot_beat]<=1;
   end
   if(vm_commit_v)begin
    if(!active||vm_commit_tag!=tag||!result_seen[vm_commit_beat]||committed[vm_commit_beat])fault<=1;
    committed[vm_commit_beat]<=1;commit_count<=commit_count+1'b1;
   end
   if(kernel_done)begin
    if(!active||kernel_done_tag!=tag||done_seen)fault<=1;
    done_seen<=1;
   end
   if(complete_slot)begin
    if(!active||(!complete_ok&&MUT_EARLY_COMPLETE==0))fault<=1;
    else if(!fault&&!source_fault)begin completed<=1;active<=0;end
   end
  end
 end
endmodule
