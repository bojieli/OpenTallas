`default_nettype none
// HBM-NEXT-UNITS IDXQ 2026-10-19: IDXN ROOT CONTROL (die slot idx_ctl, beside the selectors and the link). Fork of the
// d4g ot_hbm_idx_rootctl_static with the d4g issuer replaced by the IDXN N-row issuer ot_hnx_idxn_calendar (the root
// copy of the 5 lockstep calendars). It decodes the root classes:
//   SEL (one class per time-shared selector: row r -> selector r mod S), LIN (link row clear / flush + row),
//   LOUT (link emit + group + row), done; link_clear (record start) = start + 2.
// Checks (fault): a selector ingest (op 2) when the tree root carries no valid score line, the 4 quarters out of
// lockstep at the tree root, the quadrant faults, the selector and link faults, the calendar (class collisions,
// query-reload hazard, launch onto a busy stream). TOPK engine and the SW read-group share: verbatim d4g.
// PINS: programme bus, start, length, n_rows, pitch and the quadrant faults land in pin flops; the decoded fields and
// done leave flops (+2 edges from the host start, as the quadrant copies). RESET: rst_n drives only ot_rst_relay.
// STATIC: no ready/credit. CW=1 (default): compact calendar stream windows, as ot_hnx_idxq_qctl.
module ot_hnx_idxq_rootctl #(parameter integer K=8,S=4,CW=1)(
 input wire clk_program,clk_program_mem,clk_sel,clk_topk,input wire[3:0]clk_pair,input wire rst_n,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,input wire[4:0]n_rows,input wire[11:0]row_pitch,
 output reg[4*S-1:0]sel_op,output reg[2*S-1:0]sel_pass,output reg[8*S-1:0]sel_addr,
 output reg lin_clear,lin_flush,output reg[4:0]lin_row,output reg lout_emit,output reg[3:0]lout_group,output reg[4:0]lout_row,
 output reg link_clear,
 input wire[3:0]tree_ev,                 // ev of the 4 quadrant lists at the tree root (quadrant 0 = list 0)
 input wire[3:0]qfault,input wire[S-1:0]sf,input wire lf,
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
 (* keep *) reg pw_r,st_r;(* keep *) reg[7:0]pa_r;(* keep *) reg[255:0]pd_r;(* keep *) reg[11:0]ln_r,pi_r;(* keep *) reg[4:0]nr_r;
 (* keep *) reg[3:0]qf_r;
 always @(posedge clk_program)begin
  pw_r<=program_we;pa_r<=program_addr;pd_r<=program_data;st_r<=start;ln_r<=length;nr_r<=n_rows;pi_r<=row_pitch;qf_r<=qfault;
 end
 wire calendar_fault,done_u,rs,ow,oq,qe,kv,pv,lc,lf_u,le;wire[6:0]oi;wire[4:0]qh,kr,lr,er;wire[7:0]ki,pi;wire[3:0]eg;
 wire[4*S-1:0]sop;wire[2*S-1:0]sps;wire[8*S-1:0]sad;
 ot_hnx_idxn_calendar #(.K(K),.S(S),.CW(CW)) calendar(.clk(clk_program),.clk_mem(clk_program_mem),.rst_n(rst_c),
  .program_we(pw_r),.program_addr(pa_r),.program_data(pd_r),.start(st_r),.length(ln_r),.n_rows(nr_r),.pitch(pi_r),
  .row_start(rs),.opr_weight(ow),.opr_query(oq),.opr_index(oi),.qem_v(qe),.qem_head(qh),
  .key_v(kv),.key_index(ki),.key_row(kr),.pre_v(pv),.pre_index(pi),.sel_op(sop),.sel_pass(sps),.sel_addr(sad),
  .lin_clear(lc),.lin_flush(lf_u),.lin_row(lr),.lout_emit(le),.lout_group(eg),.lout_row(er),.done(done_u),.fault(calendar_fault));
 always @(posedge clk_program or negedge rst_c)
  if(!rst_c)begin sel_op<=0;lin_clear<=0;lin_flush<=0;lout_emit<=0;link_clear<=0;done<=0;end
  else begin sel_op<=sop;lin_clear<=lc;lin_flush<=lf_u;lout_emit<=le;link_clear<=st_r;done<=done_u;end
 always @(posedge clk_program)begin sel_pass<=sps;sel_addr<=sad;lin_row<=lr;lout_group<=eg;lout_row<=er;end
 reg parent_calendar_fault,agree_fault;
 always @(posedge clk_sel or negedge rst_c)begin
  if(!rst_c)begin parent_calendar_fault<=0;agree_fault<=0;end
  else begin
   for(integer s=0;s<S;s=s+1)if(sel_op[s*4+:4]==4'd2&&tree_ev[0]!=1'b1)parent_calendar_fault<=1;
   if(tree_ev!={4{tree_ev[0]}})agree_fault<=1;          // the 4 quarters score in lockstep
  end
 end
 assign fault=calendar_fault|(|qf_r)|(|sf)|lf|parent_calendar_fault|agree_fault;
 wire[135:0]topk_rq;wire[2055:0]topk_rr;
 ot_hbm_idx_topk_static topk(.clk(clk_topk),.rst_n(rst_n),.sid(SID),.go(topk_go),.k(topk_k),.order(topk_order),
  .n(topk_n),.m(topk_m),.a_mirror(topk_a_mirror),.a_base(topk_a_base),.a_str(topk_a_str),.o_mirror(topk_o_mirror),
  .o_base(topk_o_base),.o_str(topk_o_str),.has_r(topk_has_r),.r_base(topk_r_base),.r_str(topk_r_str),
  .vm_rq(topk_rq),.vm_rr(topk_rr),.cq(cq),.cq_seq(cq_seq),.cr(cr),.busy(topk_busy),.done(topk_done),.fault(topk_fault));
 ot_hbm_idx_vm_share_static share(.clk_pair(clk_pair),.rst_n(rst_n),.index_rq(index_rq),.topk_rq(topk_rq),.argmax_rq(argmax_rq),
  .vm_rq(vm_rq),.vm_rr(vm_rr),.index_rr(index_rr),.topk_rr(topk_rr),.argmax_rr(argmax_rr),.fault(share_fault));
endmodule
`default_nettype wire
