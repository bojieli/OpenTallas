`default_nettype none
// Actual VM operand path. Weights and FP32 queries are read from mapped SRAM;
// there is no externally supplied internal quantisation/arithmetic result.
module ot_hbm_idx_vm_query_static_core #(parameter integer VM_RT_EXTRA=0)(
 input wire clk,rst_n,input wire[1:0]sid,
 input wire weight_slot,query_slot,input wire[6:0]query_index,
 input wire[15:0]weight_sector,query_sector,
 output wire[135:0]vm_rq,input wire[2055:0]vm_rr,
 output reg block_v,output reg[4:0]block_head,output reg[1:0]block_number,
 output reg[1023:0]block_data,output reg[15:0]head_weight,
 output wire fault
);
 reg[135:0]slots;
 reg[127:0]tags;
 wire[2055:0]rr;wire[127:0]rtag;wire face_fault;
 reg[511:0]weights;reg[1:0]weight_seen;reg bad;
 reg[15:0]sector;
 integer lane;
 always @*begin
  slots=0;tags=0;sector=0;lane=0;
  if(weight_slot)begin
   for(integer s=0;s<2;s=s+1)begin
    sector=weight_sector+16'(s);lane=int'(sector[2:0]);
    slots[lane*17+:17]={1'b1,sector};tags[lane*16+:16]=16'h8000|16'(s);
   end
  end
  if(query_slot)begin
   for(integer s=0;s<4;s=s+1)begin
    sector=query_sector+16'(int'(query_index)*4+s);lane=int'(sector[2:0]);
    slots[lane*17+:17]={1'b1,sector};tags[lane*16+:16]={1'b0,6'd0,2'(s),query_index};
   end
  end
 end
 ot_hbm_idx_vm_static #(.RT_EXTRA(VM_RT_EXTRA)) face(.clk(clk),.rst_n(rst_n),.sid(sid),.read_slot(slots),.read_tag(tags),.vm_rq(vm_rq),.vm_rr(vm_rr),.result(rr),.result_tag(rtag),.fault(face_fault));
 assign fault=bad||face_fault;
 reg[3:0]parts;
 reg[1023:0]assembled;
 reg[6:0]qid;
 integer pi;
 always @*begin
  parts=0;assembled=0;qid=0;pi=0;
  for(integer b=0;b<8;b=b+1)if(rr[b*257+256]&&!rtag[b*16+15])begin
   pi=int'(rtag[b*16+7+:2]);parts[pi]=1;assembled[pi*256+:256]=rr[b*257+:256];qid=rtag[b*16+:7];
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin weights<=0;weight_seen<=0;bad<=0;block_v<=0;block_head<=0;block_number<=0;block_data<=0;head_weight<=0;end
  else begin
   block_v<=|parts;
   if(weight_slot&&query_slot)bad<=1;
   if(weight_slot&&weight_sector[2:0]!=0)bad<=1;
   if(query_slot&&query_sector[1:0]!=0)bad<=1;
   for(integer b=0;b<8;b=b+1)if(rr[b*257+256])begin
    if(rtag[b*16+15])begin
     weights[int'(rtag[b*16])*256+:256]<=rr[b*257+:256];weight_seen[int'(rtag[b*16])]<=1;
    end else if(rtag[b*16+:7]!=qid)bad<=1;
   end
   if(|parts)begin
    if(parts!=4'hf||weight_seen!=2'b11)bad<=1;
    block_head<=qid[6:2];block_number<=qid[1:0];block_data<=assembled;head_weight<=weights[qid[6:2]*16+:16];
   end
  end
 end
endmodule
`default_nettype wire
`default_nettype none
// ---------------------------------------------------------------------------
// PIN-REGISTERED TILE (OWNER RULE 19:50 PT 10-15, H-NETLIST/idxreg 2026-10-16): the die
// master ot_hbm_idx_vm_query_static is this shell. Every data input and every output passes ONE kept
// flop at the pin (clocks and rst_n pass through); the unchanged arithmetic/control is
// ot_hbm_idx_vm_query_static_core. Latency: +1 edge on every input, +1 edge on every output; the IDX
// calendar compiler (tools/hbm_idx_static_calendar.py, PIN table) schedules them.
// Pin flops have no reset (as physical/common_flow/ot_pin_regs.tcl); the core is reset.
// The VM round trip crosses the vm_rq output and vm_rr input pin flops: the core's face
// captures at n+10 (VM_RT_EXTRA=2) instead of n+8.
module ot_hbm_idx_vm_query_static(
 input wire clk,rst_n,input wire[1:0]sid,
 input wire weight_slot,query_slot,input wire[6:0]query_index,
 input wire[15:0]weight_sector,query_sector,
 output reg[135:0]vm_rq,input wire[2055:0]vm_rr,
 output reg block_v,output reg[4:0]block_head,output reg[1:0]block_number,
 output reg[1023:0]block_data,output reg[15:0]head_weight,
 output reg fault
);
 (* keep *) reg[1:0]sid_r;(* keep *) reg ws_r,qs_r;(* keep *) reg[6:0]qi_r;(* keep *) reg[15:0]wsec_r,qsec_r;(* keep *) reg[2055:0]rr_r;
 wire[135:0]c_rq;wire c_bv,c_fault;wire[4:0]c_bh;wire[1:0]c_bn;wire[1023:0]c_bd;wire[15:0]c_hw;
 always @(posedge clk)begin
  sid_r<=sid;ws_r<=weight_slot;qs_r<=query_slot;qi_r<=query_index;wsec_r<=weight_sector;qsec_r<=query_sector;rr_r<=vm_rr;
  vm_rq<=c_rq;block_v<=c_bv;block_head<=c_bh;block_number<=c_bn;block_data<=c_bd;head_weight<=c_hw;fault<=c_fault;
 end
 ot_hbm_idx_vm_query_static_core #(.VM_RT_EXTRA(2)) core(.clk(clk),.rst_n(rst_n),.sid(sid_r),.weight_slot(ws_r),.query_slot(qs_r),
  .query_index(qi_r),.weight_sector(wsec_r),.query_sector(qsec_r),.vm_rq(c_rq),.vm_rr(rr_r),
  .block_v(c_bv),.block_head(c_bh),.block_number(c_bn),.block_data(c_bd),.head_weight(c_hw),.fault(c_fault));
endmodule
`default_nettype wire
