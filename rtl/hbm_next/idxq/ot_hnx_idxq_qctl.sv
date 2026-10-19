`default_nettype none
// HBM-NEXT-UNITS IDXQ 2026-10-19: IDXN QUADRANT CONTROL (die slot idx_ctl<q>, one per quadrant). Fork of the d4g
// ot_hbm_idx_qctl_static with the d4g issuer replaced by the IDXN N-row issuer ot_hnx_idxn_calendar (K pipelined row
// streams over one frame, per-class routing, collision = fault). Same programme / start / n_rows / pitch broadcast as
// the root copy (ot_hnx_idxq_rootctl), so the 5 calendars issue in lockstep. This copy decodes the quadrant classes:
//   OPR (operand reader), QEM (query head emit), KEY (all rows: scorer beat; row 0 also = the HBM key-line service
//   request key_slot), PRE (replay-buffer read one edge ahead), row_start (query unit seen-clear per row).
// The selector / link classes are decoded by the root copy only (its collision checks run here too: same programme).
// PINS: programme bus, start, length, n_rows, pitch, nkeys, slot land in pin flops (+1 edge); every output leaves a
// flop (+1 edge): the timeline is +2 edges after the host start, as the d4g quadrant copy. frame_start (record start:
// operand row bases, key buffer clear) = start + 2; row_start = start + 2 (row 0) or the launch edge + 1 (rows >= 1).
// RESET: rst_n drives only ot_rst_relay; calendar/control flops reset, pin flops unreset. STATIC: no ready/credit.
// CW=2 (HBM-NEXT-UNITS IDXQ 2026-10-19, default; CW=1 = bypass form, gate 4 cross-clock -15.7 ps): compact windows (shared head rows 0-1 + 3-row ring, no bypass); CW=1 was one shared head row + a 2-row
// ring per stream: 4,352 instead of 9,216 window flops; same instruction on every edge, tb_hnx_idxn_cw + the quad lockstep);
// gate hnx_idxq_qctl 04:2x failed the clock rule at 9,290 sinks (pin-flop spread 104 ps > 80 TT).
module ot_hnx_idxq_qctl #(parameter integer K=8,S=4,CW=2)(
 input wire clk_program,clk_program_mem,input wire rst_n,
 input wire slot,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,input wire[4:0]n_rows,input wire[11:0]row_pitch,input wire[13:0]nkeys,
 output reg weight_slot,query_slot,output reg[6:0]query_index,
 output reg query_emit,output reg[4:0]query_emit_head,
 output reg key_slot,                                   // row 0 key beat = HBM key-line service request
 output reg key_v,output reg[7:0]key_index,output reg[4:0]key_row,
 output reg pre_v,output reg[7:0]pre_index,
 output reg[11:0]nq,output reg frame_start,row_start,
 input wire vf,qf,scf,kbf,
 output reg fault
);
 wire rst_c;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk_program),.rst_n_in(rst_n),.rst_n(rst_c));
 (* keep *) reg pw_r,st_r,sl_r;(* keep *) reg[7:0]pa_r;(* keep *) reg[255:0]pd_r;(* keep *) reg[11:0]ln_r,pi_r;
 (* keep *) reg[4:0]nr_r;(* keep *) reg[13:0]nk_r;
 (* keep *) reg vf_r,qf_r,sf_r,kf_r;
 always @(posedge clk_program)begin
  pw_r<=program_we;pa_r<=program_addr;pd_r<=program_data;st_r<=start;ln_r<=length;nr_r<=n_rows;pi_r<=row_pitch;
  nk_r<=nkeys;sl_r<=slot;vf_r<=vf;qf_r<=qf;sf_r<=scf;kf_r<=kbf;
 end
 wire calendar_fault,done_u,rs,ow,oq,qe,kv,pv,lc,lf,le;wire[6:0]oi;wire[4:0]qh,kr,lr,er;wire[7:0]ki,pi;wire[3:0]eg;
 wire[4*S-1:0]sop;wire[2*S-1:0]sps;wire[8*S-1:0]sad;
 ot_hnx_idxn_calendar #(.K(K),.S(S),.CW(CW)) calendar(.clk(clk_program),.clk_mem(clk_program_mem),.rst_n(rst_c),
  .program_we(pw_r),.program_addr(pa_r),.program_data(pd_r),.start(st_r),.length(ln_r),.n_rows(nr_r),.pitch(pi_r),
  .row_start(rs),.opr_weight(ow),.opr_query(oq),.opr_index(oi),.qem_v(qe),.qem_head(qh),
  .key_v(kv),.key_index(ki),.key_row(kr),.pre_v(pv),.pre_index(pi),.sel_op(sop),.sel_pass(sps),.sel_addr(sad),
  .lin_clear(lc),.lin_flush(lf),.lin_row(lr),.lout_emit(le),.lout_group(eg),.lout_row(er),.done(done_u),.fault(calendar_fault));
 wire[13:0]base=sl_r?14'd2736:14'd0;
 always @(posedge clk_program or negedge rst_c)
  if(!rst_c)begin weight_slot<=0;query_slot<=0;query_emit<=0;key_slot<=0;key_v<=0;pre_v<=0;frame_start<=0;row_start<=0;fault<=0;end
  else begin
   weight_slot<=ow;query_slot<=oq;query_emit<=qe;key_v<=kv;key_slot<=kv&&kr==5'd0;pre_v<=pv;
   frame_start<=st_r;row_start<=rs;
   if(calendar_fault||vf_r||qf_r||sf_r||kf_r)fault<=1;
  end
 always @(posedge clk_program)begin
  query_index<=oi;query_emit_head<=qh;key_index<=ki;key_row<=kr;pre_index<=pi;
  nq<=(nk_r<=base)?12'd0:((nk_r-base>=14'd2736)?12'd2736:12'(nk_r-base));
 end
endmodule
`default_nettype wire
