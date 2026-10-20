`default_nettype none
// ---------------------------------------------------------------------------
// IDX OPERAND READER, UNIFORM n+12 MASTER (HBM-IDXAM3 2026-10-18, coordinator decision 0hk).
// One die master for all four quadrant operand readers hb_idx__op_{SW,SE,NW,NE}. Identical to the pin-registered
// shell ot_hbm_idx_vm_query_static (one kept flop on every data input and output; clk/rst_n pass through; the
// unchanged arithmetic/control is ot_hbm_idx_vm_query_static_core) except that the core's VM face captures at
// n+12 (VM_RT_EXTRA=4) instead of n+10: the round trip carries the two pin flops of this shell (vm_rq out,
// vm_rr in) plus TWO fixed edges outside the tile, which are
//   SW: the registered share ot_hbm_idx_vm_share_static_amr (index_rq pin flop +1, vm_rr leaf pin flop +1), and
//   SE/NW/NE: two relay stages on the die (one on vm_rq, one on vm_rr; H-D4G-GEN2).
// Every other port keeps the +1/+1 edge of the n+10 shell. Data flops are reset-free (as the n+10 shell).
module ot_hbm_idx_vm_query_static_n12(
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
 ot_hbm_idx_vm_query_static_core #(.VM_RT_EXTRA(4)) core(.clk(clk),.rst_n(rst_n),.sid(sid_r),.weight_slot(ws_r),.query_slot(qs_r),
  .query_index(qi_r),.weight_sector(wsec_r),.query_sector(qsec_r),.vm_rq(c_rq),.vm_rr(rr_r),
  .block_v(c_bv),.block_head(c_bh),.block_number(c_bn),.block_data(c_bd),.head_weight(c_hw),.fault(c_fault));
endmodule
`default_nettype wire
