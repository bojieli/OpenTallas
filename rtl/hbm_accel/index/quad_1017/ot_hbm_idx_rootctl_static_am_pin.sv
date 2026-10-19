`default_nettype none
// d4g die master for the ARGMAX-merge IDX root on pin-registered VM banks (VEH-TOPKFIX2 2026-10-19): the d4g die binds
// hfd_vms_bank_native_q0_faces in all 32 VM banks (literal input pin flop: bank answer and hub echo +1 edge), but
// ot_hbm_idx_rootctl_static_am r3 was timed on the 7-edge non-face VM model. This master =
// ot_hbm_idx_rootctl_static_am #(.VM_RT(1), .CR_RT(1)): TOPK capture n+10 (RT_EXTRA 2), ACK 14, share owner tap own[8];
// INDEX and ARGMAX responses +1 (operand reader capture n+13, argmax r2 VMX 6). Ports identical (drop-in rebind of
// hb_idx__ctl). Die relay / landing stages on the rq4/rr4 or cq/cr lanes add to VM_RT / CR_RT (then a new master).
module ot_hbm_idx_rootctl_static_am_pin(

 input wire clk,input wire rst_n,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,
 output wire[3:0]sel_op,output wire[1:0]sel_pass,output wire[7:0]sel_addr,
 output wire link_flush,link_emit,output wire[3:0]link_group,output wire link_clear,
 input wire[3:0]selected_v,output wire ingest_v,
 input wire[3:0]tree_ev,                 // ev of the 4 quadrant lists at the tree root (quadrant 0 = list 0)
 input wire[3:0]qfault,input wire sf,lf,
 output wire done,output wire fault,
 // TOPK
 input wire topk_go,input wire[3:0]topk_k,input wire topk_order,input wire[19:0]topk_n,topk_m,
 input wire topk_a_mirror,input wire[17:0]topk_a_base,topk_a_str,input wire topk_o_mirror,input wire[17:0]topk_o_base,topk_o_str,
 input wire topk_has_r,input wire[17:0]topk_r_base,topk_r_str,
 output wire[337:0]cq,output wire[1:0]cq_seq,input wire[273:0]cr,
 output wire topk_busy,topk_done,topk_fault,
 // VM read group 4 share (index face = quadrant 0's operand reader)
 input wire[135:0]index_rq,output wire[2055:0]index_rr,
 input wire[135:0]argmax_rq,output wire[263:0]argmax_m,
 output wire[135:0]vm_rq,input wire[2055:0]vm_rr,
 output wire share_fault
);
 ot_hbm_idx_rootctl_static_am #(.VM_RT(1), .CR_RT(1)) u(
  .clk(clk),
  .rst_n(rst_n),
  .program_we(program_we),
  .program_addr(program_addr),
  .program_data(program_data),
  .start(start),
  .length(length),
  .sel_op(sel_op),
  .sel_pass(sel_pass),
  .sel_addr(sel_addr),
  .link_flush(link_flush),
  .link_emit(link_emit),
  .link_group(link_group),
  .link_clear(link_clear),
  .selected_v(selected_v),
  .ingest_v(ingest_v),
  .tree_ev(tree_ev),
  .qfault(qfault),
  .sf(sf),
  .lf(lf),
  .done(done),
  .fault(fault),
  .topk_go(topk_go),
  .topk_k(topk_k),
  .topk_order(topk_order),
  .topk_n(topk_n),
  .topk_m(topk_m),
  .topk_a_mirror(topk_a_mirror),
  .topk_a_base(topk_a_base),
  .topk_a_str(topk_a_str),
  .topk_o_mirror(topk_o_mirror),
  .topk_o_base(topk_o_base),
  .topk_o_str(topk_o_str),
  .topk_has_r(topk_has_r),
  .topk_r_base(topk_r_base),
  .topk_r_str(topk_r_str),
  .cq(cq),
  .cq_seq(cq_seq),
  .cr(cr),
  .topk_busy(topk_busy),
  .topk_done(topk_done),
  .topk_fault(topk_fault),
  .index_rq(index_rq),
  .index_rr(index_rr),
  .argmax_rq(argmax_rq),
  .argmax_m(argmax_m),
  .vm_rq(vm_rq),
  .vm_rr(vm_rr),
  .share_fault(share_fault));
endmodule
`default_nettype wire
