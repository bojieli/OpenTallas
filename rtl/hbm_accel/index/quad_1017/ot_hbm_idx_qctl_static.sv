`default_nettype none
// HBM d4g plan (b) IDX QUADRANT CONTROL (lane HBM-B-RTL2, 2026-10-17; die slot idx_ctl<q>, one per quadrant).
// The quadrant-local copy of the parts of ot_hbm_idx_ctl_static that feed the quadrant's own operand reader
// (ot_hbm_idx_vm_query_static), query unit (ot_hbm_idx_query_static) and quarter scorer: the programme SRAM issuer
// (ot_hbm_idx_calendar_static, same programme as the root copy: the host broadcasts the programme rows and the start
// to the 5 calendars with equal fixed latency), the scheduled-glue fields weight/query/emit/key beat, the per-stack
// key count split nq(slot) and the quadrant fault OR. The selector/link fields are decoded by the root copy only.
// PINS: programme bus, start and nkeys land in pin flops (+1 edge); every output leaves a flop (+1 edge): the
// whole IDX timeline is +2 edges after the host start (identical for root and quadrants, so the compiled
// programme is unchanged). frame_start (query clear) = start + 2, aligned with the calendar issue as before.
// RESET: rst_n drives only ot_rst_relay (release +3 edges); calendar/control flops reset, pin flops unreset.
// STATIC: no ready/credit; slot is a die strap (stack index of this quadrant's KV ordinals).
module ot_hbm_idx_qctl_static(
 input wire clk_program,clk_program_mem,input wire rst_n,
 input wire slot,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,input wire[13:0]nkeys,
 output reg weight_slot,query_slot,output reg[6:0]query_index,
 output reg query_emit,output reg[4:0]query_emit_head,
 output reg key_slot,output reg[7:0]key_index,
 output reg[11:0]nq,output reg frame_start,
 input wire vf,qf,scf,
 output reg fault
);
 wire rst_c;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk_program),.rst_n_in(rst_n),.rst_n(rst_c));
 (* keep *) reg pw_r,st_r,sl_r;(* keep *) reg[7:0]pa_r;(* keep *) reg[255:0]pd_r;(* keep *) reg[11:0]ln_r;(* keep *) reg[13:0]nk_r;
 (* keep *) reg vf_r,qf_r,sf_r;
 always @(posedge clk_program)begin
  pw_r<=program_we;pa_r<=program_addr;pd_r<=program_data;st_r<=start;ln_r<=length;nk_r<=nkeys;sl_r<=slot;
  vf_r<=vf;qf_r<=qf;sf_r<=scf;
 end
 wire issue_v,calendar_fault,done_u;wire[31:0]ins;
 ot_hbm_idx_calendar_static calendar(.clk(clk_program),.clk_mem(clk_program_mem),.rst_n(rst_c),
 .program_we(pw_r),.program_addr(pa_r),.program_data(pd_r),.start(st_r),.length(ln_r),
 .issue_v(issue_v),.instruction(ins),.done(done_u),.fault(calendar_fault));
 wire[13:0]base=sl_r?14'd2736:14'd0;
 always @(posedge clk_program or negedge rst_c)
  if(!rst_c)begin weight_slot<=0;query_slot<=0;query_emit<=0;key_slot<=0;frame_start<=0;fault<=0;end
  else begin
   weight_slot<=issue_v&&ins[31];query_slot<=issue_v&&ins[30];query_emit<=issue_v&&ins[29];key_slot<=issue_v&&ins[28];
   frame_start<=st_r;
   if(calendar_fault||vf_r||qf_r||sf_r)fault<=1;
  end
 always @(posedge clk_program)begin
  query_index<=ins[26:20];query_emit_head<=ins[24:20];key_index<=ins[27:20];
  nq<=(nk_r<=base)?12'd0:((nk_r-base>=14'd2736)?12'd2736:12'(nk_r-base));
 end
endmodule
`default_nettype wire
