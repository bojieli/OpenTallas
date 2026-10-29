`default_nettype none
// Explicit actual-source bridge. Default mode preserves the selected legacy
// calendar/ports/dates for N1. Native IDXN mode requires a matching root
// calendar source event; it never reinterprets the legacy 32b programme.
// VM_RT is the declared reader capture contract, not a clock-tree estimate.
module ot_hbm_idx_qctl_static_r2048 #(
 parameter integer NATIVE_IDXN=0, ROOT_NATIVE_PROFILE=0,
 parameter integer VM_RT=173, PREFILLED_KEYS=0,
 parameter integer K=8,S=4,CW=2,DELIVERED_RESET=0
)(
 input wire clk_program,clk_program_mem,rst_n,slot,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,input wire[13:0]nkeys,
 input wire[4:0]n_rows,input wire[11:0]row_pitch,
 output wire weight_slot,query_slot,output wire[6:0]query_index,
 output wire query_emit,output wire[4:0]query_emit_head,
 output wire key_slot,key_v,output wire[7:0]key_index,output wire[4:0]key_row,
 output wire pre_v,output wire[7:0]pre_index,
 output wire key_replay,
 output wire[11:0]nq,output wire frame_start,row_start,
 input wire vf,qf,scf,kbf,output wire fault
);
 wire bad_shape=(n_rows==5'd0)||(n_rows>5'(K))||(n_rows>5'd1&&row_pitch==12'd0);
 wire reject_start=bad_shape||((NATIVE_IDXN==0)?n_rows!=5'd1:ROOT_NATIVE_PROFILE==0);
 wire accepted_start=start&&!reject_start;
 wire child_fault;
 // Configuration faults are presented in the same full input START slot;
 // the existing root/collar fault path owns latching. No new reset leaf.
 assign fault=child_fault||(start&&reject_start);
 generate if(NATIVE_IDXN==0)begin:g_legacy
  wire ks,fs;
  ot_hbm_idx_qctl_static legacy(
   .clk_program(clk_program),.clk_program_mem(clk_program_mem),.rst_n(rst_n),.slot(slot),
   .program_we(program_we),.program_addr(program_addr),.program_data(program_data),
   .start(accepted_start),.length(length),.nkeys(nkeys),
   .weight_slot(weight_slot),.query_slot(query_slot),.query_index(query_index),
   .query_emit(query_emit),.query_emit_head(query_emit_head),.key_slot(ks),.key_index(key_index),
   .nq(nq),.frame_start(fs),.vf(vf),.qf(qf),.scf(scf||kbf),.fault(child_fault));
  assign key_slot=ks;assign key_v=ks;assign key_row=5'd0;
  assign pre_v=1'b0;assign pre_index=8'd0;assign key_replay=1'b0;
  assign frame_start=fs;assign row_start=fs;
 end else begin:g_native
  wire ks,kv;wire[4:0]kr;
  ot_hnx_idxq_qctl #(.K(K),.S(S),.CW(CW),.DELIVERED_RESET(DELIVERED_RESET),.ROW_CLEAR_DELAY(VM_RT-2),.PRE_ROW0(PREFILLED_KEYS)) native_ctl(
   .clk_program(clk_program),.clk_program_mem(clk_program_mem),.rst_n(rst_n),.slot(slot),
   .program_we(program_we),.program_addr(program_addr),.program_data(program_data),
   .start(accepted_start),.length(length),.nkeys(nkeys),.n_rows(n_rows),.row_pitch(row_pitch),
   .weight_slot(weight_slot),.query_slot(query_slot),.query_index(query_index),
   .query_emit(query_emit),.query_emit_head(query_emit_head),.key_slot(ks),
   .key_v(kv),.key_index(key_index),.key_row(kr),.pre_v(pre_v),.pre_index(pre_index),
   .nq(nq),.frame_start(frame_start),.row_start(row_start),
   .vf(vf),.qf(qf),.scf(scf),.kbf(kbf),.fault(child_fault));
  assign key_slot=(PREFILLED_KEYS!=0)?1'b0:ks;
  assign key_v=kv;assign key_row=kr;
  assign key_replay=kv&&((PREFILLED_KEYS!=0)||(kr!=0));
 end endgenerate
endmodule
`default_nettype wire
