`timescale 1ns/1ps
// SU provider hookup for the SU_PIN_MARGIN CP (2026-10-06). Same finite
// provider datapath as ot_hbm_integrated_su_provider_adapter (exact request
// {we1,byteaddr32,data256,strb32,tag16} and response {tag16,we1,data256}
// pass-through, retained owner frame, executor done/fault/retired to the CP),
// but WITHOUT its own association: the register-to-register CP context
// (ot_hbm_integrated_su_cp_context, SU_PIN_MARGIN=1) already carries the one
// association and publishes exec_owned/new_request_permit/fault from its
// output flops, 3 edges (2 input + 1 output pin stages) behind its inputs.
//
// LIVE_GRANT_GUARD=1 (deployed): a NEW request handshake additionally needs
// the live raw grant on this edge. The pin permit reflects the grant 3 edges
// late, so after a grant drop (revocation, or release before the executor
// stops) it can still read 1 for up to 3 edges; the unregistered path vetoes
// in the same edge. The guard is one AND of a registered permit with the
// grant; it only removes requests issued without the port grant (it never
// adds one). LIVE_GRANT_GUARD=0 is the negative control.
// Accepted response debt is never cancelled (as in the adapter).
module ot_hbm_integrated_su_provider_margin #(
 parameter integer ENABLE=0,LIVE_GRANT_GUARD=1
)(
 input wire raw_grant,
 input wire ext_exec_owned,ext_new_request_permit,ext_fault,
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
  wire permit=ext_new_request_permit&&(LIVE_GRANT_GUARD==0||raw_grant);
  assign exec_owned=ext_exec_owned;assign new_request_permit=permit;assign fault=ext_fault;
  assign provider_req_v=exec_req_v&&permit;
  assign exec_req_r=provider_req_r&&permit;
  assign provider_req=exec_req;
  assign exec_rsp_v=provider_rsp_v;
  assign provider_rsp_r=exec_rsp_r;
  assign exec_rsp=provider_rsp;
  assign owner_frame={held_pos,held_token,held_gen,held_job};
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
