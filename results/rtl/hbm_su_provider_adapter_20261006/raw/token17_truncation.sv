`timescale 1ns/1ps
// Extract selected parent's one association and finite provider hookup.
// Replace its association instance; never instantiate both. CP owns retained
// identity, grant/release ACK, warm drainage and response tag/class checks.
module ot_hbm_integrated_su_provider_adapter #(
 parameter integer ENABLE=0,FAST_OWNER_FRONTIER=0
)(
 input wire clk_sm,por_n,
 input wire raw_grant,qualified_owned,
 input wire [11:0] qualified_owned_terms,
 output wire exec_owned,new_request_permit,fault,
 input wire exec_req_v,output wire exec_req_r,input wire [336:0] exec_req,
 output wire provider_req_v,input wire provider_req_r,output wire [336:0] provider_req,
 input wire provider_rsp_v,output wire provider_rsp_r,input wire [272:0] provider_rsp,
 output wire exec_rsp_v,input wire exec_rsp_r,output wire [272:0] exec_rsp,
 input wire [31:0] held_job,input wire [3:0] held_gen,
 input wire [16:0] held_token,input wire [19:0] held_pos,
 output wire [72:0] owner_frame,
 input wire [31:0] held_selected_pc,output wire [31:0] selected_pc,
 input wire exec_done,exec_fault,input wire [3:0] retired_original_ops,
 output wire caller_exec_done,caller_exec_fault,output wire [3:0] caller_retired_original_ops
);
 generate if(ENABLE!=0)begin:g_enabled
  ot_hbm_integrated_su_cp_association #(.ENABLE(1),.FAST_OWNER_FRONTIER(FAST_OWNER_FRONTIER)) association(
   .clk(clk_sm),.por_n(por_n),.raw_grant(raw_grant),.qualified_owned(qualified_owned),
   .qualified_owned_terms(qualified_owned_terms),.exec_owned(exec_owned),
   .new_request_permit(new_request_permit),.fault(fault));
  // Exactly {we1,byteaddr32,data256,strb32,tag16}; only NEW handshakes use veto.
  assign provider_req_v=exec_req_v&&new_request_permit;
  assign exec_req_r=provider_req_r&&new_request_permit;
  assign provider_req=exec_req;
  // Exactly {tag16,we1,data256}. No live owner/warm/permission cancellation
  // of already accepted response debt. Executor validates tag and class.
  assign exec_rsp_v=provider_rsp_v;
  assign provider_rsp_r=exec_rsp_r;
  assign exec_rsp=provider_rsp;
  assign owner_frame={held_pos,1'b0,held_token[15:0],held_gen,held_job};
  assign selected_pc=held_selected_pc;
  assign caller_exec_done=exec_done;
  assign caller_exec_fault=exec_fault;
  assign caller_retired_original_ops=retired_original_ops;
 end else begin:g_disabled
  assign exec_owned=0;assign new_request_permit=0;assign fault=0;
  assign provider_req_v=0;assign exec_req_r=0;assign provider_req=0;
  assign exec_rsp_v=0;assign provider_rsp_r=0;assign exec_rsp=0;
  assign owner_frame=0;assign selected_pc=0;
  assign caller_exec_done=0;assign caller_exec_fault=0;assign caller_retired_original_ops=0;
 end endgenerate
endmodule
