`timescale 1ns/1ps
// Source-faithful CP child cut of g_die[d].u_su_cp/u_su_association.
// Shared grant/response owner and executor remain parent-facing boundaries.
// No added registers, independent authority, or delay of live-owner veto.
//
// SU_PIN_MARGIN (default off; margin-first rule 2026-10-06): register-to-register
// block boundary. Every input is captured at its pin and once more (2 edges);
// every output leaves from a flop at its pin (1 edge). The core is the
// canonical CP + association with PIN_MARGIN restructuring, cycle-exact against
// the unregistered core under the same 2-edge input delay (fault vetoes still
// act on the same core edge as the publication they veto, so they reach the
// pins on the same edge). SU_RELEASE_REPLAY=1 makes the accepted release edge
// the caller's actual release_v&&release_r fire (latency-insensitive handshake).
module ot_hbm_integrated_su_cp_context #(parameter integer ENABLE=0,SU_ENABLE=0,SU_REGISTERED_OUTPUTS=0,
 SU_REGISTERED_STATUS=0,SU_REGISTERED_BOUNDARY=0,SU_BALANCED_OWNER_BOUNDARY=0,SU_FOUR_COMBINATIONAL_CUTS=0,SU_FAST_OWNER_FRONTIER=0,SU_PARALLEL_PHASE_VALIDATION=0,SU_CONTROL_TAIL_CUT=0,SU_OWNER_VETO_POLARITY=0,
 SU_PIN_MARGIN=0,SU_RELEASE_REPLAY=0) (
 input wire clk,por_n,input wire [1:0] launch_v,input wire [31:0] launch_pc,
 input wire [31:0] cp_job,input wire [3:0] cp_gen,
 input wire [16:0] launch_token,input wire [19:0] launch_pos,
 output wire [1:0] native_launch,
 output wire lease_v,input wire lease_granted,
 output wire release_v,input wire release_r,
 input wire exec_done,exec_fault,input wire [3:0] retired_original_ops,
 input wire shared_fault,
 output wire owned,pending,quiet,selected,done,fault,
 output wire [31:0] selected_pc,held_job,output wire [3:0] held_gen,
 output wire [16:0] held_token,output wire [19:0] held_pos,
 output wire exec_owned,new_request_permit,association_fault
);
 localparam integer IW=2+32+32+4+17+20+1+1+1+1+4+1; // 116 input bits
 localparam integer OW=2+1+1+1+1+1+1+1+1+32+32+4+17+20+1+1+1; // 118 output bits
 wire [IW-1:0] in_pin={launch_v,launch_pc,cp_job,cp_gen,launch_token,launch_pos,
  lease_granted,release_r,exec_done,exec_fault,retired_original_ops,shared_fault};
 wire [IW-1:0] in_core,in_next;
 wire [OW-1:0] out_core;
 // Core view of the inputs.
 wire [1:0] c_launch_v;wire [31:0] c_launch_pc,c_cp_job;wire [3:0] c_cp_gen;
 wire [16:0] c_launch_token;wire [19:0] c_launch_pos;
 wire c_lease_granted,c_release_r,c_exec_done,c_exec_fault,c_shared_fault;wire [3:0] c_retired;
 assign {c_launch_v,c_launch_pc,c_cp_job,c_cp_gen,c_launch_token,c_launch_pos,
  c_lease_granted,c_release_r,c_exec_done,c_exec_fault,c_retired,c_shared_fault}=in_core;
 // Live header one stage ahead (pin stage) for the registered owner compare.
 wire [1:0] n_launch_v;wire [31:0] n_launch_pc,n_cp_job;wire [3:0] n_cp_gen;
 wire [16:0] n_launch_token;wire [19:0] n_launch_pos;wire [8:0] n_rest;
 assign {n_launch_v,n_launch_pc,n_cp_job,n_cp_gen,n_launch_token,n_launch_pos,n_rest}=in_next;
 wire [191:0] owner_live_next={55'd0,n_launch_pos,n_launch_token,n_cp_gen,n_cp_job,32'd0,n_launch_pc};
 wire [1:0] c_native_launch;wire c_lease_v,c_release_v,c_owned,c_pending,c_quiet,c_selected,c_done,c_fault;
 wire [31:0] c_selected_pc,c_held_job;wire [3:0] c_held_gen;wire [16:0] c_held_token;wire [19:0] c_held_pos;
 wire c_exec_owned,c_new_request_permit,c_association_fault;
 assign out_core={c_native_launch,c_lease_v,c_release_v,c_owned,c_pending,c_quiet,c_selected,c_done,c_fault,
  c_selected_pc,c_held_job,c_held_gen,c_held_token,c_held_pos,c_exec_owned,c_new_request_permit,c_association_fault};
 wire [OW-1:0] out_pin;
 assign {native_launch,lease_v,release_v,owned,pending,quiet,selected,done,fault,
  selected_pc,held_job,held_gen,held_token,held_pos,exec_owned,new_request_permit,association_fault}=out_pin;
 generate if(SU_PIN_MARGIN)begin:pin_margin
  initial if(!(ENABLE&&SU_ENABLE))$fatal(1,"SU_PIN_MARGIN registers an enabled CP only");
  // Reset values equal the unregistered core's outputs in reset with idle inputs.
  localparam [OW-1:0] OUT_RESET={2'b0,1'b0,1'b0,1'b0,1'b0,1'b1,1'b0,1'b0,1'b0,32'd0,32'd0,4'd0,17'd0,20'd0,1'b0,1'b0,1'b0};
  reg [IW-1:0] in_q1,in_q2;reg [OW-1:0] out_q;
  always @(posedge clk or negedge por_n)begin
   if(!por_n)begin in_q1<=0;in_q2<=0;out_q<=OUT_RESET;end
   else begin in_q1<=in_pin;in_q2<=in_q1;out_q<=out_core;end
  end
  assign in_core=in_q2;assign in_next=in_q1;assign out_pin=out_q;
 end else begin:direct
  assign in_core=in_pin;assign in_next=in_pin;assign out_pin=out_core;
 end endgenerate
 wire [11:0] owned_frontier_terms;
 ot_hbm_integrated_su_cp_bind #(.ENABLE(ENABLE&&SU_ENABLE),
  .REGISTERED_OUTPUTS(SU_REGISTERED_OUTPUTS),.REGISTERED_STATUS(SU_REGISTERED_STATUS),
  .REGISTERED_BOUNDARY(SU_REGISTERED_BOUNDARY),.GROUPED_OWNER_BOUNDARY(0),
  .BALANCED_OWNER_BOUNDARY(SU_BALANCED_OWNER_BOUNDARY),.FOUR_COMBINATIONAL_CUTS(SU_FOUR_COMBINATIONAL_CUTS),.FAST_OWNER_FRONTIER(SU_FAST_OWNER_FRONTIER),.PARALLEL_PHASE_VALIDATION(SU_PARALLEL_PHASE_VALIDATION),.CONTROL_TAIL_CUT(SU_CONTROL_TAIL_CUT),.OWNER_VETO_POLARITY(SU_OWNER_VETO_POLARITY),
  .PIN_MARGIN(SU_PIN_MARGIN),.RELEASE_REPLAY(SU_RELEASE_REPLAY?3:0)) u_su_cp(
  .clk(clk),.por_n(por_n),.launch_v(c_launch_v),.launch_pc(c_launch_pc),
  .cp_job(c_cp_job),.cp_gen(c_cp_gen),.launch_token(c_launch_token),.launch_pos(c_launch_pos),
  .native_launch(c_native_launch),.lease_v(c_lease_v),.lease_granted(c_lease_granted),
  .release_v(c_release_v),.release_r(c_release_r),.exec_done(c_exec_done),.exec_fault(c_exec_fault),
  .retired_original_ops(c_retired),.shared_fault(c_shared_fault),
  .owned(c_owned),.owned_frontier_terms(owned_frontier_terms),.pending(c_pending),.quiet(c_quiet),.selected(c_selected),.done(c_done),.fault(c_fault),
  .selected_pc(c_selected_pc),.held_job(c_held_job),.held_gen(c_held_gen),.held_token(c_held_token),.held_pos(c_held_pos),
  .owner_live_next(owner_live_next));
 ot_hbm_integrated_su_cp_association #(.ENABLE(ENABLE&&SU_ENABLE&&SU_BALANCED_OWNER_BOUNDARY),.FAST_OWNER_FRONTIER(SU_FAST_OWNER_FRONTIER),.CONTROL_TAIL_CUT(SU_CONTROL_TAIL_CUT),.OWNER_VETO_POLARITY(SU_OWNER_VETO_POLARITY),
  .PIN_MARGIN(SU_PIN_MARGIN)) u_su_association(
  .clk(clk),.por_n(por_n),.raw_grant(c_lease_granted),.qualified_owned(c_owned),.qualified_owned_terms(owned_frontier_terms),
  .exec_owned(c_exec_owned),.new_request_permit(c_new_request_permit),.fault(c_association_fault));
endmodule
