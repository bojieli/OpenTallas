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
// r3 PIN-REGISTERED BOUNDARY -- SUPERSEDES the share / INDEX / TOPK / ingest_v / fault statements above (lane HBM-IDXAM2 10-18; r2 hidx_rootctl_am_1018-r2-0385e1977 EARLY_FAIL_SETUP -577.7 ps,
// 3,621 endpoints at CTS: 2,194 port-to-port combinational endpoints -- index_rq/argmax_rq -> vm_rq, vm_rr -> index_rr,
// sf/lf -> fault, selected_v -> ingest_v -- each holding in-max 518.7 + out-max 518.7 of 773 ps under the consistent
// link split, plus TOPK cq/busy leaving engine flops ~235 um from their face (-231/-245), vm_rr -> TOPK capture /
// share steering (-85/-246/-240) and topk_go -> 200 descriptor enables (-139)). No port reaches a port any more:
//   * share = ot_hbm_idx_vm_share_static_amr: index_rq / argmax_rq pin registers here, vm_rr pin registers in the leaves,
//     owner tap own[7], ARGMAX 2-stage OR tree (argmax port-to-port edges UNCHANGED: +1 request, +1 vm_rr, tree 2 = 4);
//   * TOPK: command inputs pin-registered (+1), engine RT_EXTRA 1 (capture n+9, +1 per row), cq/cq_seq/busy/done/fault
//     leave pin registers (+1; engine ACK 12 -> 13 for the cq register);
//   * ingest_v is PREDICTED from the root's own sel_op stream: the selector raises selected_v[q] <= (op == 6) for all four
//     quadrants on a fixed schedule (shell pin flop, core rv/rop, selected_v, shell out flop = SEL_LAT 4 edges after
//     sel_op leaves this tile), so ingest_v = (sel_op of SEL_LAT edges ago == 6) from a register, timing identical to the
//     old &selected_v; selected_v is now only CHECKED (any lane != ingest_v -> sticky fault). SEL_LAT must equal the die's
//     sel_op -> selected_v round trip (relay hops added there add to it);
//   * fault and share_fault leave pin registers (+1).
// Latency ledger (compiler, results/arch/hbm_d4g_price_1017/latency_ledger.json row HBM-IDXAM2): INDEX requests +1 and
// responses +1 (SW operand reader capture n+12: VM_RT_EXTRA 4), ARGMAX +0, TOPK go +1 / row +1 / writes +1 / done +1,
// fault +1, share_fault +1, ingest_v +0, sel/link/done +0.
// AMMUT (bench only): 1..4 forwarded to the share ARGMAX tree (see ot_hbm_idx_vm_share_static_amr.sv); 5 TOPK engine
// RT_EXTRA 0 (capture one edge early against the registered vm_rr); 6 ingest_v predicted one edge early; 7 share leaf
// owner tap own[6] (INDEX/TOPK/ARGMAX steering one edge short).
// VM_RT / CR_RT (VEH-TOPKFIX2 2026-10-19, defect veh_cuts_1019/topk_finding.json): the d4g die binds
// hfd_vms_bank_native_q0_faces in all 32 VM banks (literal input pin flop on rq/rslot/wq/wslot/pq: +1 edge on every bank
// answer and on the hub echo) and may add relay / landing stages on the rq4/rr4 (VM_RT) and cq/cr (CR_RT) lanes. This r3
// was timed on the 7-edge non-face VM model (bench RD 7, ACKD 11). VM_RT = fixed extra VM round-trip edges outside the
// tile: TOPK RT_EXTRA 1+VM_RT, share owner tap own[7+VM_RT]; INDEX / ARGMAX responses leave VM_RT edges later (operand
// reader VM_RT_EXTRA 4+VM_RT, argmax r2 VMX 5+VM_RT). CR_RT = fixed extra hub echo edges: TOPK ACK 13+CR_RT. Die master
// for the faces banks with no relay on those lanes: ot_hbm_idx_rootctl_static_am_pin (VM_RT 1, CR_RT 1). Default 0 = r3.
module ot_hbm_idx_rootctl_static_am #(parameter integer AMMUT = 0, parameter integer SEL_LAT = 4,
 parameter integer VM_RT = 0, parameter integer CR_RT = 0)(
 input wire clk,input wire rst_n,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,
 output reg[3:0]sel_op,output reg[1:0]sel_pass,output reg[7:0]sel_addr,
 output reg link_flush,link_emit,output reg[3:0]link_group,output reg link_clear,
 input wire[3:0]selected_v,output reg ingest_v,
 input wire[3:0]tree_ev,                 // ev of the 4 quadrant lists at the tree root (quadrant 0 = list 0)
 input wire[3:0]qfault,input wire sf,lf,
 output reg done,output reg fault,
 // TOPK
 input wire topk_go,input wire[3:0]topk_k,input wire topk_order,input wire[19:0]topk_n,topk_m,
 input wire topk_a_mirror,input wire[17:0]topk_a_base,topk_a_str,input wire topk_o_mirror,input wire[17:0]topk_o_base,topk_o_str,
 input wire topk_has_r,input wire[17:0]topk_r_base,topk_r_str,
 output reg[337:0]cq,output reg[1:0]cq_seq,input wire[273:0]cr,
 output reg topk_busy,topk_done,topk_fault,
 // VM read group 4 share (index face = quadrant 0's operand reader)
 input wire[135:0]index_rq,output wire[2055:0]index_rr,
 input wire[135:0]argmax_rq,output wire[263:0]argmax_m,
 output wire[135:0]vm_rq,input wire[2055:0]vm_rr,
 output reg share_fault
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
 // ingest_v: predicted from the sel_op stream (selected_v = {4{op == 6}} SEL_LAT edges after sel_op); selected_v checked
 localparam integer SL = (AMMUT == 6) ? SEL_LAT - 1 : SEL_LAT;
 reg [3:0] so_d [0:SL-2];
 reg ingest_fault;
 always @(posedge clk or negedge rst_c[0])
  if(!rst_c[0])begin ingest_v<=0;ingest_fault<=0;for(integer d=0;d<SL-1;d=d+1)so_d[d]<=0;end
  else begin
   so_d[0]<=sel_op;for(integer d=1;d<SL-1;d=d+1)so_d[d]<=so_d[d-1];
   ingest_v<=so_d[SL-2]==4'd6;
   if(selected_v!={4{ingest_v}})ingest_fault<=1;
  end
 reg parent_calendar_fault,agree_fault;
 always @(posedge clk or negedge rst_c[0])begin
  if(!rst_c[0])begin parent_calendar_fault<=0;agree_fault<=0;fault<=0;end
  else begin
   if(sel_op==2&&tree_ev[0]!=1'b1)parent_calendar_fault<=1;
   if(tree_ev!={4{tree_ev[0]}})agree_fault<=1;
   fault<=calendar_fault|(|qf_r)|sf|lf|parent_calendar_fault|agree_fault|ingest_fault;   // fault pin register (+1)
  end
 end
 // TOPK command pin registers (+1 on the TOPK timeline; no reset: data pin flops, go is reset)
 (* keep *) reg tk_go_r;(* keep *) reg[3:0]tk_k_r;(* keep *) reg tk_ord_r,tk_am_r,tk_om_r,tk_hr_r;
 (* keep *) reg[19:0]tk_n_r,tk_m_r;(* keep *) reg[17:0]tk_ab_r,tk_as_r,tk_ob_r,tk_os_r,tk_rb_r,tk_rs_r;
 always @(posedge clk or negedge rst_c[1]) if(!rst_c[1]) tk_go_r<=0; else tk_go_r<=topk_go;
 always @(posedge clk)begin
  tk_k_r<=topk_k;tk_ord_r<=topk_order;tk_n_r<=topk_n;tk_m_r<=topk_m;tk_am_r<=topk_a_mirror;tk_ab_r<=topk_a_base;
  tk_as_r<=topk_a_str;tk_om_r<=topk_o_mirror;tk_ob_r<=topk_o_base;tk_os_r<=topk_o_str;tk_hr_r<=topk_has_r;
  tk_rb_r<=topk_r_base;tk_rs_r<=topk_r_str;
 end
 wire[135:0]topk_rq;wire[2055:0]topk_rr;wire[337:0]tk_cq;wire[1:0]tk_cqs;wire tk_busy,tk_done,tk_fault;
 ot_hbm_idx_topk_static #(.ACK(13 + CR_RT),.RT_EXTRA(((AMMUT == 5) ? 0 : 1) + VM_RT)) topk(.clk(clk),.rst_n(rst_c[1]),.sid(SID),.go(tk_go_r),
  .k(tk_k_r),.order(tk_ord_r),.n(tk_n_r),.m(tk_m_r),.a_mirror(tk_am_r),.a_base(tk_ab_r),.a_str(tk_as_r),.o_mirror(tk_om_r),
  .o_base(tk_ob_r),.o_str(tk_os_r),.has_r(tk_hr_r),.r_base(tk_rb_r),.r_str(tk_rs_r),
  .vm_rq(topk_rq),.vm_rr(topk_rr),.cq(tk_cq),.cq_seq(tk_cqs),.cr(cr),.busy(tk_busy),.done(tk_done),.fault(tk_fault));
 // TOPK output pin registers (+1): the hub sees cq one edge later, so the engine's cr check runs at ACK 13
 always @(posedge clk or negedge rst_c[1])
  if(!rst_c[1])begin cq[337]<=0;topk_busy<=0;topk_done<=0;topk_fault<=0;end
  else begin cq[337]<=tk_cq[337];topk_busy<=tk_busy;topk_done<=tk_done;topk_fault<=tk_fault;end
 always @(posedge clk)begin cq[336:0]<=tk_cq[336:0];cq_seq<=tk_cqs;end
 // share: INDEX / ARGMAX request pin registers here, vm_rr pin registers in the leaves
 (* keep *) reg[135:0]irq_r,arq_r;
 always @(posedge clk)begin irq_r<=index_rq;arq_r<=argmax_rq;end
 wire share_f;
 ot_hbm_idx_vm_share_static_amr #(.MUT((AMMUT == 7) ? 1 : 0),.AMMUT((AMMUT >= 1 && AMMUT <= 4) ? AMMUT : 0),.VM_RT(VM_RT)) share(.clk(clk),
  .rst_n(rst_c[2]),.index_rq(irq_r),.topk_rq(topk_rq),.argmax_rq(arq_r),.vm_rq(vm_rq),.vm_rr(vm_rr),.index_rr(index_rr),
  .topk_rr(topk_rr),.argmax_m(argmax_m),.fault(share_f));
 always @(posedge clk or negedge rst_c[2]) if(!rst_c[2]) share_fault<=0; else share_fault<=share_f;
endmodule
`default_nettype wire
