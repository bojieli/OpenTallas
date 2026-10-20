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
 parameter integer MUT_EARLY_COMPLETE=0,LOCAL32=0
)(
 input wire ck,rst_n,input wire source_fault,
 input wire begin_slot,input wire [58:0] begin_tag,
 input wire request_slot,input wire [58:0] request_tag,input wire [19:0] result_base_word,
 input wire qr_committed,input wire [58:0] qr_tag,
 output reg kernel_request_v,output reg [58:0] kernel_request_tag,
 input wire q_slot,input wire[75:0]q_slot_pub,input wire [4:0] q_slot_beat,
 input wire q_v,input wire [4:0] q_beat,input wire [58:0] q_tag,input wire [511:0] q_data,
 output reg kernel_q_v,output reg [4:0] kernel_q_beat,output reg [58:0] kernel_q_tag,output reg [511:0] kernel_q_data,
 input wire result_slot,input wire[75:0]result_slot_pub,input wire [4:0] result_slot_beat,
 input wire result_v,input wire [4:0] result_beat,input wire [58:0] result_tag,input wire [511:0] result_data,
 output wire[23:0]kernel_request_pub,output wire[24:0]vm_write_pub,
 output reg vm_write_v,output reg [19:0] vm_write_word,output reg [4:0] vm_write_beat,
 output reg [58:0] vm_write_tag,output reg [511:0] vm_write_data,
 input wire vm_commit_v,input wire [4:0] vm_commit_beat,input wire [58:0] vm_commit_tag,
 input wire kernel_done,input wire [58:0] kernel_done_tag,
 input wire complete_slot,output reg completed,output reg active,output reg fault,output wire [94:0] native_ret,
 // R3e (QW-N59-6 10-20) opt-in same-edge publications (LOCAL32; LOCAL32 0 ignores them): begin_pub[k] == begin_slot,
 // request_pub[k] == request_slot, *_beat_pub == the matching beat, on every edge (parent / landing kept copies).
 input wire[12:0]begin_pub,input wire[6:0]request_pub,
 input wire[4:0]q_slot_beat_pub,result_slot_beat_pub,vm_commit_beat_pub,
 // R3g: third copies (== the matching beat): kernel_q_beat capture, vm_write beat / word, result_seen check mux.
 input wire[4:0]q_slot_beat_pub2,result_slot_beat_pub2,vm_commit_beat_pub2,
 // R3i: fourth copies for the upper 16 entries of the 32:1 check muxes (q_seen / result_seen / result_seen / committed).
 input wire[4:0]q_slot_beat_pub3,result_slot_beat_pub3,vm_commit_beat_pub3,vm_commit_beat_pub4
);
 // R3f: groups of <= 16 enable bits (a DFFE enable costs 2 mapped loads per bit).
 wire[12:0]bp=LOCAL32?begin_pub:{13{begin_slot}};
 wire[6:0]rp=LOCAL32?request_pub:{7{request_slot}};
 wire[4:0]qsb_d=LOCAL32?q_slot_beat_pub:q_slot_beat,rsb_d=LOCAL32?result_slot_beat_pub:result_slot_beat,
          vcb_d=LOCAL32?vm_commit_beat_pub:vm_commit_beat,
          qsb2=LOCAL32?q_slot_beat_pub2:q_slot_beat,rsb2=LOCAL32?result_slot_beat_pub2:result_slot_beat,
          vcb2=LOCAL32?vm_commit_beat_pub2:vm_commit_beat,
          qsb3=LOCAL32?q_slot_beat_pub3:q_slot_beat,rsb3=LOCAL32?result_slot_beat_pub3:result_slot_beat,
          vcb3=LOCAL32?vm_commit_beat_pub3:vm_commit_beat,vcb4=LOCAL32?vm_commit_beat_pub4:vm_commit_beat;
 // R3i: X[b] read as b[4] ? X[16 + b'[3:0]] : X[b[3:0]] with b' a second copy of b (== X[b]).
 function automatic rd32(input [31:0] x,input [4:0] lo,input [4:0] hi);
  rd32=lo[4]?x[{1'b1,hi[3:0]}]:x[{1'b0,lo[3:0]}];
 endfunction
 // Result payload holds use independently registered same-edge publications.
 // Every bit is retained on the same inactive edges as the original service.
 wire[19:0]result_word=base+((LOCAL32!=0)?result_slot_beat_pub2:result_slot_beat);   // R3g: == base + result_slot_beat
 generate if(LOCAL32)begin:g_result_payload32
  for(genvar rg=0;rg<64;rg=rg+1)begin:g_data
   always @(posedge ck or negedge rst_n)
    if(!rst_n)vm_write_data[8*rg+:8]<=0;
    else if(result_slot_pub[rg])vm_write_data[8*rg+:8]<=result_data[8*rg+:8];
  end
  for(genvar rg=0;rg<8;rg=rg+1)begin:g_tag
   localparam integer RW=(rg==7)?3:8;
   always @(posedge ck or negedge rst_n)
    if(!rst_n)vm_write_tag[8*rg+:RW]<=0;
    else if(result_slot_pub[64+rg])vm_write_tag[8*rg+:RW]<=result_tag[8*rg+:RW];
  end
  for(genvar rg=0;rg<3;rg=rg+1)begin:g_word
   localparam integer RW=(rg==2)?4:8;
   always @(posedge ck or negedge rst_n)
    if(!rst_n)vm_write_word[8*rg+:RW]<=0;
    else if(result_slot_pub[72+rg])vm_write_word[8*rg+:RW]<=result_word[8*rg+:RW];
  end
  always @(posedge ck or negedge rst_n)
   if(!rst_n)vm_write_beat<=0;
   else if(result_slot_pub[75])vm_write_beat<=rsb2;
 end endgenerate
 // R3c (QW-CB16A0 10-20): Q capture holds use the parent's same-edge kept q_slot publications ([63:0] data bytes,
 // [71:64] tag bytes, [72] beat, [73]/[74] q_seen low/high, [75] count/checks); the kernel-request and VM-write valids
 // publish kept same-D copies (each copy = the original register on every edge).  LOCAL32 0: aliases, no added flops.
 wire kreq_d=request_slot&&!fault&&!source_fault,vmw_d=result_slot&&!fault&&!source_fault;
 generate if(LOCAL32)begin:g_q_payload32
  for(genvar qg=0;qg<64;qg=qg+1)begin:g_data
   always @(posedge ck or negedge rst_n)
    if(!rst_n)kernel_q_data[8*qg+:8]<=0;
    else if(q_slot_pub[qg])kernel_q_data[8*qg+:8]<=q_data[8*qg+:8];
  end
  for(genvar qg=0;qg<8;qg=qg+1)begin:g_tag
   localparam integer RW=(qg==7)?3:8;
   always @(posedge ck or negedge rst_n)
    if(!rst_n)kernel_q_tag[8*qg+:RW]<=0;
    else if(q_slot_pub[64+qg])kernel_q_tag[8*qg+:RW]<=q_tag[8*qg+:RW];
  end
  always @(posedge ck or negedge rst_n)
   if(!rst_n)kernel_q_beat<=0;
   else if(q_slot_pub[72])kernel_q_beat<=qsb2;
  for(genvar c=0;c<24;c=c+1)begin:g_kreq
   (* keep = "true" *) reg q;
   always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=rp[6]&&!fault&&!source_fault;   // R3e: == kreq_d
   assign kernel_request_pub[c]=q;
  end
  for(genvar c=0;c<25;c=c+1)begin:g_vmw
   (* keep = "true" *) reg q;
   always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=vmw_d;
   assign vm_write_pub[c]=q;
  end
 end else begin:g_pub_alias
  assign kernel_request_pub={24{kernel_request_v}};assign vm_write_pub={25{vm_write_v}};
 end endgenerate
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
   kernel_request_v<=0;kernel_request_tag<=0;kernel_q_v<=0;if(LOCAL32==0)begin kernel_q_beat<=0;kernel_q_tag<=0;kernel_q_data<=0;end
   vm_write_v<=0;if(LOCAL32==0)begin vm_write_word<=0;vm_write_beat<=0;vm_write_tag<=0;vm_write_data<=0;end
   completed<=0;active<=0;fault<=0;
  end else begin
   kernel_request_v<=kreq_d;
   kernel_q_v<=q_slot&&!fault&&!source_fault;
   vm_write_v<=vmw_d;
   completed<=0;
   if(source_fault)fault<=1;
   // R3e: the accepted begin / request clears and captures are grouped per kept publication (<= 32 loads each); same
   // statements, same order, same conditions (bp[k] == begin_slot, rp[k] == request_slot).
   if(begin_slot&&(active||!legal_tag))fault<=1;
   if(bp[0]&&!(active||!legal_tag))tag[14:0]<=begin_tag[14:0];
   if(bp[1]&&!(active||!legal_tag))tag[29:15]<=begin_tag[29:15];
   if(bp[2]&&!(active||!legal_tag))tag[44:30]<=begin_tag[44:30];
   if(bp[3]&&!(active||!legal_tag))tag[58:45]<=begin_tag[58:45];
   if(bp[4]&&!(active||!legal_tag))q_seen[15:0]<=0;
   if(bp[5]&&!(active||!legal_tag))q_seen[31:16]<=0;
   if(bp[6]&&!(active||!legal_tag))q_count<=0;
   if(bp[7]&&!(active||!legal_tag))result_seen[15:0]<=0;
   if(bp[8]&&!(active||!legal_tag))result_seen[31:16]<=0;
   if(bp[9]&&!(active||!legal_tag))result_count<=0;
   if(bp[10]&&!(active||!legal_tag))committed[15:0]<=0;
   if(bp[11]&&!(active||!legal_tag))committed[31:16]<=0;
   if(bp[12]&&!(active||!legal_tag))begin commit_count<=0;context_valid<=1;requested<=0;done_seen<=0;end
   if(rp[0])kernel_request_tag[14:0]<=request_tag[14:0];
   if(rp[1])kernel_request_tag[29:15]<=request_tag[29:15];
   if(rp[2])kernel_request_tag[44:30]<=request_tag[44:30];
   if(rp[3])kernel_request_tag[58:45]<=request_tag[58:45];
   if(rp[4])base[9:0]<=result_base_word[9:0];
   if(rp[5])base[19:10]<=result_base_word[19:10];
   if(request_slot)begin
    if(!context_valid||active||requested||request_tag!=tag||!qr_committed||qr_tag!=tag||result_base_word>20'hfffe0)fault<=1;
    requested<=1;active<=1;
   end
   // An unexpected or absent native producer cannot silently change its slot.
   if(q_v!=q_slot)fault<=1;
   if(LOCAL32==0&&q_slot)begin kernel_q_beat<=q_slot_beat;kernel_q_tag<=q_tag;kernel_q_data<=q_data;end
   if(LOCAL32?q_slot_pub[75]:q_slot)begin
    q_count<=q_count+1'b1;
    if(!active||!requested||q_tag!=tag||q_beat!=q_slot_beat||rd32(q_seen,q_slot_beat,qsb3)||q_count!={1'b0,q_slot_beat})fault<=1;
   end
   if((LOCAL32?q_slot_pub[73]:q_slot)&&!qsb_d[4])q_seen[qsb_d]<=1;
   if((LOCAL32?q_slot_pub[74]:q_slot)&&qsb_d[4])q_seen[qsb_d]<=1;
   if(result_v!=result_slot)fault<=1;
   if(result_slot)begin
    if(LOCAL32==0)begin vm_write_word<=base+result_slot_beat;vm_write_beat<=result_slot_beat;
    vm_write_tag<=result_tag;vm_write_data<=result_data;end
    result_count<=result_count+1'b1;
    if(!active||!requested||result_tag!=tag||result_beat!=result_slot_beat||rd32(result_seen,result_slot_beat,rsb3)||result_count!={1'b0,result_slot_beat})fault<=1;
    result_seen[rsb_d]<=1;
   end
   if(vm_commit_v)begin
    if(!active||vm_commit_tag!=tag||!rd32(result_seen,vcb2,vcb3)||rd32(committed,vm_commit_beat,vcb4))fault<=1;
    committed[vcb_d]<=1;commit_count<=commit_count+1'b1;
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
