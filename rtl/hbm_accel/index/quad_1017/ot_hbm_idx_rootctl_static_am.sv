`default_nettype none
// HBM d4g IDX ROOT CONTROL, ARGMAX-merge successor (lane HBM-IDXAM 2026-10-18; die slot idx_ctl, coordinator 0gl (3)).
// = ot_hbm_idx_rootctl_static (HBM-B-RTL2) with ONE change on the ARGMAX face: the SW read-group share is
// ot_hbm_idx_vm_share_static_am, so argmax_m is ONE 264-bit word {lane valid8, data256} (was argmax_rr 8 x 257 = 2,056 b)
// for the argmax successor ot_hbm_argmax_static_sw_vm_r2 (closed hbm_argmax_swvm_r2_1017-r3). The 8:1 sector select is
// done in the four bank-pair leaves (data of a lane ORs in only with its owner-steered valid) and the lanes are merged on
// an equal-latency register chain pair 0 -> 3: every lane reaches argmax_m exactly 4 edges after the leaves' n+7 steer
// (argmax VMX = 4 + the r2 vm_rr pin register = 5; compiler ledger row HBM-IDXAM). INDEX / TOPK faces, the calendar,
// the selector/link fields, ingest_v and every fault are verbatim rootctl (bench run_idx_rootctl_am.sh: every other
// output identical every edge vs ot_hbm_idx_rootctl_static).
// TILE CLOCK: one clock pin clk drives the programme, programme SRAM, selector check, TOPK and the four pair leaves (the
// tile is 300 x 260 um: one local tree; the die's eight IDX ctl clock nets were the same stream clock). RESET: rst_n
// drives only ot_rst_relay (3 regions: calendar/ctl, TOPK, share); the share's async clear now releases 3 edges after the
// port like the calendar's (transaction-level: no client counts from reset). STATIC: no ready/credit, no backpressure.
// AMMUT: bench mutants forwarded to the share merge chain (see ot_hbm_idx_vm_share_static_am.sv).
module ot_hbm_idx_rootctl_static_am #(parameter integer AMMUT = 0)(
 input wire clk,input wire rst_n,
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
 input wire[135:0]argmax_rq,output wire[263:0]argmax_m,
 output wire[135:0]vm_rq,input wire[2055:0]vm_rr,
 output wire share_fault
);
 localparam [1:0] SID = 2'd0;
 wire [2:0] rst_c;
 ot_rst_relay #(.REGIONS(3),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rst_c));
 (* keep *) reg pw_r,st_r;(* keep *) reg[7:0]pa_r;(* keep *) reg[255:0]pd_r;(* keep *) reg[11:0]ln_r;
 (* keep *) reg[3:0]qf_r;
 always @(posedge clk)begin pw_r<=program_we;pa_r<=program_addr;pd_r<=program_data;st_r<=start;ln_r<=length;qf_r<=qfault;end
 wire issue_v,calendar_fault,done_u;wire[31:0]ins;
 ot_hbm_idx_calendar_static calendar(.clk(clk),.clk_mem(clk),.rst_n(rst_c[0]),
 .program_we(pw_r),.program_addr(pa_r),.program_data(pd_r),.start(st_r),.length(ln_r),
 .issue_v(issue_v),.instruction(ins),.done(done_u),.fault(calendar_fault));
 always @(posedge clk or negedge rst_c[0])
  if(!rst_c[0])begin sel_op<=0;link_flush<=0;link_emit<=0;link_clear<=0;done<=0;end
  else begin
   sel_op<=issue_v?ins[19:16]:4'd0;link_flush<=issue_v&&ins[5];link_emit<=issue_v&&ins[4];link_clear<=st_r;done<=done_u;
  end
 always @(posedge clk)begin sel_pass<=ins[15:14];sel_addr<=ins[13:6];link_group<=ins[3:0];end
 assign ingest_v=&selected_v;
 reg parent_calendar_fault,agree_fault;
 always @(posedge clk or negedge rst_c[0])begin
  if(!rst_c[0])begin parent_calendar_fault<=0;agree_fault<=0;end
  else begin
   if(sel_op==2&&tree_ev[0]!=1'b1)parent_calendar_fault<=1;
   if(tree_ev!={4{tree_ev[0]}})agree_fault<=1;
  end
 end
 assign fault=calendar_fault|(|qf_r)|sf|lf|parent_calendar_fault|agree_fault;
 wire[135:0]topk_rq;wire[2055:0]topk_rr;
 ot_hbm_idx_topk_static topk(.clk(clk),.rst_n(rst_c[1]),.sid(SID),.go(topk_go),.k(topk_k),.order(topk_order),
  .n(topk_n),.m(topk_m),.a_mirror(topk_a_mirror),.a_base(topk_a_base),.a_str(topk_a_str),.o_mirror(topk_o_mirror),
  .o_base(topk_o_base),.o_str(topk_o_str),.has_r(topk_has_r),.r_base(topk_r_base),.r_str(topk_r_str),
  .vm_rq(topk_rq),.vm_rr(topk_rr),.cq(cq),.cq_seq(cq_seq),.cr(cr),.busy(topk_busy),.done(topk_done),.fault(topk_fault));
 ot_hbm_idx_vm_share_static_am #(.AMMUT(AMMUT)) share(.clk_pair({4{clk}}),.rst_n(rst_c[2]),.index_rq(index_rq),.topk_rq(topk_rq),
  .argmax_rq(argmax_rq),.vm_rq(vm_rq),.vm_rr(vm_rr),.index_rr(index_rr),.topk_rr(topk_rr),.argmax_m(argmax_m),.fault(share_fault));
endmodule
`default_nettype wire
