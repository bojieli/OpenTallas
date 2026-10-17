`timescale 1ns/1ps
`default_nettype none
// IDX control tile (H-NETLIST/IDXP 2026-10-16, die slot idx_ctl, H-DIE grant 6413258a6): everything of the SW IDX
// client (hb_idx = ot_hbm_idx_client_static_sw) that is NOT one of its hardened children, gathered so the die can
// bind hb_idx as a SOFT hierarchy (children = die-level instances hb_idx__*). Contents, verbatim from the source RTL:
//   ot_hbm_idx_calendar_static calendar      (ot_hbm_idx_scheduled_static.sv:23)  programme SRAM issuer
//   ot_hbm_idx_topk_static topk              (ot_hbm_idx_client_static.sv:44)
//   ot_hbm_idx_vm_share_static share         (ot_hbm_idx_client_static.sv:48)
//   scheduled glue: key_slot/key_index, slot gating, sel_op mux, fault OR  (ot_hbm_idx_scheduled_static.sv:25-35)
//   parent glue: per-scorer nkeys split, ingest_v = &selected_v, calendar_fault register, fault OR
//                                            (ot_hbm_idx_parent_static.sv:33,55,58-63)
// No new logic, latency or flow control: the equivalence of ot_hbm_idx_client_static_soft against
// ot_hbm_idx_client_static_sw (children cut) is proven in results/arch/hbm_idx_soft_parent_1016.
module ot_hbm_idx_ctl_static #(parameter integer N_Q=4)(   // N_Q: scorer slots (A2P half die 2; see ot_hbm_idx_parent_static)
 input wire clk_program,clk_program_mem,clk_sel,clk_topk,input wire[3:0]clk_pair,input wire rst_n,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,
 input wire[13:0]nkeys,
 // to the children (instruction fields of the issued calendar word, gated as in the scheduled parent)
 output wire weight_slot,query_slot,output wire[6:0]query_index,
 output wire query_emit,output wire[4:0]query_emit_head,
 output wire key_slot,output wire[7:0]key_index,
 output wire[3:0]sel_op,output wire[1:0]sel_pass,output wire[7:0]sel_addr,
 output wire link_flush,link_emit,output wire[3:0]link_group,
 output wire[12*N_Q-1:0]nq,
 input wire[3:0]selected_v,output wire ingest_v,
 input wire score0_ev,
 input wire vf,qf,input wire[N_Q-1:0]scf,input wire sf,lf,
 output wire done,fault,
 // TOPK
 input wire topk_go,input wire[3:0]topk_k,input wire topk_order,input wire[19:0]topk_n,topk_m,
 input wire topk_a_mirror,input wire[17:0]topk_a_base,topk_a_str,input wire topk_o_mirror,input wire[17:0]topk_o_base,topk_o_str,
 input wire topk_has_r,input wire[17:0]topk_r_base,topk_r_str,
 output wire[337:0]cq,output wire[1:0]cq_seq,input wire[273:0]cr,
 output wire topk_busy,topk_done,topk_fault,
 // VM read group 4 share
 input wire[135:0]index_rq,output wire[2055:0]index_rr,
 input wire[135:0]argmax_rq,output wire[2055:0]argmax_rr,
 output wire[135:0]vm_rq,input wire[2055:0]vm_rr,
 output wire share_fault
);
 localparam [1:0] SID = 2'd0;
 wire issue_v,calendar_fault;wire[31:0]ins;
 ot_hbm_idx_calendar_static calendar(.clk(clk_program),.clk_mem(clk_program_mem),.rst_n(rst_n),
 .program_we(program_we),.program_addr(program_addr),.program_data(program_data),.start(start),.length(length),
 .issue_v(issue_v),.instruction(ins),.done(done),.fault(calendar_fault));
 assign key_slot=issue_v&&ins[28];assign key_index=ins[27:20];
 assign weight_slot=issue_v&&ins[31];assign query_slot=issue_v&&ins[30];assign query_index=ins[26:20];
 assign query_emit=issue_v&&ins[29];assign query_emit_head=ins[24:20];
 assign sel_op=issue_v?ins[19:16]:4'd0;assign sel_pass=ins[15:14];assign sel_addr=ins[13:6];
 assign link_flush=issue_v&&ins[5];assign link_emit=issue_v&&ins[4];assign link_group=ins[3:0];
 for(genvar q=0;q<N_Q;q=q+1)begin:gscore
  assign nq[q*12+:12]=(nkeys<=q*2736)?12'd0:((nkeys-q*2736>=2736)?12'd2736:12'(nkeys-q*2736));
 end
 assign ingest_v=&selected_v;
 reg parent_calendar_fault;
 always @(posedge clk_sel or negedge rst_n)begin
  if(!rst_n)parent_calendar_fault<=0;
  else if(sel_op==2&&score0_ev!=1'b1)parent_calendar_fault<=1;
 end
 wire parent_fault=vf|qf|(|scf)|sf|lf|parent_calendar_fault;
 assign fault=calendar_fault|parent_fault;
 wire[135:0]topk_rq;wire[2055:0]topk_rr;
 ot_hbm_idx_topk_static topk(.clk(clk_topk),.rst_n(rst_n),.sid(SID),.go(topk_go),.k(topk_k),.order(topk_order),
  .n(topk_n),.m(topk_m),.a_mirror(topk_a_mirror),.a_base(topk_a_base),.a_str(topk_a_str),.o_mirror(topk_o_mirror),
  .o_base(topk_o_base),.o_str(topk_o_str),.has_r(topk_has_r),.r_base(topk_r_base),.r_str(topk_r_str),
  .vm_rq(topk_rq),.vm_rr(topk_rr),.cq(cq),.cq_seq(cq_seq),.cr(cr),.busy(topk_busy),.done(topk_done),.fault(topk_fault));
 ot_hbm_idx_vm_share_static share(.clk_pair(clk_pair),.rst_n(rst_n),.index_rq(index_rq),.topk_rq(topk_rq),.argmax_rq(argmax_rq),
  .vm_rq(vm_rq),.vm_rr(vm_rr),.index_rr(index_rr),.topk_rr(topk_rr),.argmax_rr(argmax_rr),.fault(share_fault));
endmodule
`default_nettype wire
