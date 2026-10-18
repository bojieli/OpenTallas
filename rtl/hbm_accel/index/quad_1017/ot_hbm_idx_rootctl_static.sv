`default_nettype none
// HBM d4g plan (b) IDX ROOT CONTROL (lane HBM-B-RTL2, 2026-10-17; die slot idx_ctl, beside idx_sel / idx_link).
// Successor of ot_hbm_idx_ctl_static for the per-quadrant IDX: the root calendar copy decodes only the selector and
// link fields (the operand/query/key-beat fields are decoded by the 4 quadrant copies ot_hbm_idx_qctl_static), plus
// ingest_v, the selector calendar check, the IDX fault OR, the static TOPK engine and the SW read-group share (index
// face of quadrant 0, TOPK, ARGMAX), all verbatim from ot_hbm_idx_ctl_static.
// The selector reads the 4 quadrant score lists through the registered tree (ot_hbm_idx_xq_node_static x3); the
// compiler shifts selector/link fields by the tree (hbm_idx_static_calendar.py --score-chain, see lanes/HBM-B-RTL2.md).
// PINS: programme bus, start and the quadrant faults land in pin flops; the decoded fields and done leave flops
// (+2 edges from the host start, as the quadrant copies). TOPK/share keep their own (unchanged) pin structure.
// RESET: rst_n drives only ot_rst_relay. STATIC: no ready/credit.
// ELEM-GAPS/HBMB 10-18 (native pass): ONE clock root clk_program for every flop, the calendar SRAM, TOPK and the 4 share
// leaves (the die drives all 8 clock ports from the same stream root; clk_program_mem/clk_sel/clk_topk/clk_pair kept as
// ports, unloaded); TOPK and the share take the relayed reset rst_c (release +3 edges, as the calendar) instead of the raw
// pin; sf/lf land in pin flops and fault leaves a flop: fault (sticky status only) is now 2 edges after a qfault/sf/lf
// pin event (was 1 / 0 / 0) and 1 edge after an internal fault flop (was 0). Remaining zero-latency pin-to-pin paths (by design, unchanged): ingest_v=&selected_v
// and the SW read-group share (index/topk/argmax rq -> vm_rq, vm_rr -> *_rr).
module ot_hbm_idx_rootctl_static(
 input wire clk_program,clk_program_mem,clk_sel,clk_topk,input wire[3:0]clk_pair,input wire rst_n,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,
 output reg[3:0]sel_op,output reg[1:0]sel_pass,output reg[7:0]sel_addr,
 output reg link_flush,link_emit,output reg[3:0]link_group,output reg link_clear,
 input wire[3:0]selected_v,output wire ingest_v,
 input wire[3:0]tree_ev,                 // ev of the 4 quadrant lists at the tree root (quadrant 0 = list 0)
 input wire[3:0]qfault,input wire sf,lf,
 output reg done,output wire fault,
 // TOPK
 input wire topk_go,input wire[3:0]topk_k,input wire topk_order,input wire[19:0]topk_n,topk_m,
 input wire topk_a_mirror,input wire[17:0]topk_a_base,topk_a_str,input wire topk_o_mirror,input wire[17:0]topk_o_base,topk_o_str,
 input wire topk_has_r,input wire[17:0]topk_r_base,topk_r_str,
 output wire[337:0]cq,output wire[1:0]cq_seq,input wire[273:0]cr,
 output wire topk_busy,topk_done,topk_fault,
 // VM read group 4 share (index face = quadrant 0's operand reader)
 input wire[135:0]index_rq,output wire[2055:0]index_rr,
 input wire[135:0]argmax_rq,output wire[2055:0]argmax_rr,
 output wire[135:0]vm_rq,input wire[2055:0]vm_rr,
 output wire share_fault
);
 localparam [1:0] SID = 2'd0;
 wire rst_c;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk_program),.rst_n_in(rst_n),.rst_n(rst_c));
 (* keep *) reg pw_r,st_r;(* keep *) reg[7:0]pa_r;(* keep *) reg[255:0]pd_r;(* keep *) reg[11:0]ln_r;
 (* keep *) reg[3:0]qf_r;(* keep *) reg sf_r,lf_r;
 always @(posedge clk_program)begin pw_r<=program_we;pa_r<=program_addr;pd_r<=program_data;st_r<=start;ln_r<=length;qf_r<=qfault;sf_r<=sf;lf_r<=lf;end
 wire issue_v,calendar_fault,done_u;wire[31:0]ins;
 ot_hbm_idx_calendar_static calendar(.clk(clk_program),.clk_mem(clk_program),.rst_n(rst_c),
 .program_we(pw_r),.program_addr(pa_r),.program_data(pd_r),.start(st_r),.length(ln_r),
 .issue_v(issue_v),.instruction(ins),.done(done_u),.fault(calendar_fault));
 always @(posedge clk_program or negedge rst_c)
  if(!rst_c)begin sel_op<=0;link_flush<=0;link_emit<=0;link_clear<=0;done<=0;end
  else begin
   sel_op<=issue_v?ins[19:16]:4'd0;link_flush<=issue_v&&ins[5];link_emit<=issue_v&&ins[4];link_clear<=st_r;done<=done_u;
  end
 always @(posedge clk_program)begin sel_pass<=ins[15:14];sel_addr<=ins[13:6];link_group<=ins[3:0];end
 assign ingest_v=&selected_v;
 reg parent_calendar_fault,agree_fault;
 always @(posedge clk_program or negedge rst_c)begin
  if(!rst_c)begin parent_calendar_fault<=0;agree_fault<=0;end
  else begin
   if(sel_op==2&&tree_ev[0]!=1'b1)parent_calendar_fault<=1;
   if(tree_ev!={4{tree_ev[0]}})agree_fault<=1;          // the 4 quarters score in lockstep (was ev agreement per stack)
  end
 end
 reg fault_r;assign fault=fault_r;
 always @(posedge clk_program or negedge rst_c)
  if(!rst_c)fault_r<=0;
  else if(calendar_fault|(|qf_r)|sf_r|lf_r|parent_calendar_fault|agree_fault)fault_r<=1;
 wire[135:0]topk_rq;wire[2055:0]topk_rr;
 ot_hbm_idx_topk_static topk(.clk(clk_program),.rst_n(rst_c),.sid(SID),.go(topk_go),.k(topk_k),.order(topk_order),
  .n(topk_n),.m(topk_m),.a_mirror(topk_a_mirror),.a_base(topk_a_base),.a_str(topk_a_str),.o_mirror(topk_o_mirror),
  .o_base(topk_o_base),.o_str(topk_o_str),.has_r(topk_has_r),.r_base(topk_r_base),.r_str(topk_r_str),
  .vm_rq(topk_rq),.vm_rr(topk_rr),.cq(cq),.cq_seq(cq_seq),.cr(cr),.busy(topk_busy),.done(topk_done),.fault(topk_fault));
 ot_hbm_idx_vm_share_static share(.clk_pair({4{clk_program}}),.rst_n(rst_c),.index_rq(index_rq),.topk_rq(topk_rq),.argmax_rq(argmax_rq),
  .vm_rq(vm_rq),.vm_rr(vm_rr),.index_rr(index_rr),.topk_rr(topk_rr),.argmax_rr(argmax_rr),.fault(share_fault));
endmodule
`default_nettype wire
