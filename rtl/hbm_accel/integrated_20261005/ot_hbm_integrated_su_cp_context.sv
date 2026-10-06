`timescale 1ns/1ps
// Source-faithful CP child cut of g_die[d].u_su_cp/u_su_association.
// Shared grant/response owner and executor remain parent-facing boundaries.
// No added registers, independent authority, or delay of live-owner veto.
module ot_hbm_integrated_su_cp_context #(parameter integer ENABLE=0,SU_ENABLE=0,SU_REGISTERED_OUTPUTS=0,
 SU_REGISTERED_STATUS=0,SU_REGISTERED_BOUNDARY=0,SU_BALANCED_OWNER_BOUNDARY=0,SU_FOUR_COMBINATIONAL_CUTS=0,SU_FAST_OWNER_FRONTIER=0) (
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
 wire [11:0] owned_frontier_terms;
 ot_hbm_integrated_su_cp_bind #(.ENABLE(ENABLE&&SU_ENABLE),
  .REGISTERED_OUTPUTS(SU_REGISTERED_OUTPUTS),.REGISTERED_STATUS(SU_REGISTERED_STATUS),
  .REGISTERED_BOUNDARY(SU_REGISTERED_BOUNDARY),.GROUPED_OWNER_BOUNDARY(0),
  .BALANCED_OWNER_BOUNDARY(SU_BALANCED_OWNER_BOUNDARY),.FOUR_COMBINATIONAL_CUTS(SU_FOUR_COMBINATIONAL_CUTS),.FAST_OWNER_FRONTIER(SU_FAST_OWNER_FRONTIER)) u_su_cp(
  .clk(clk),.por_n(por_n),.launch_v(launch_v),.launch_pc(launch_pc),
  .cp_job(cp_job),.cp_gen(cp_gen),.launch_token(launch_token),.launch_pos(launch_pos),
  .native_launch(native_launch),.lease_v(lease_v),.lease_granted(lease_granted),
  .release_v(release_v),.release_r(release_r),.exec_done(exec_done),.exec_fault(exec_fault),
  .retired_original_ops(retired_original_ops),.shared_fault(shared_fault),
  .owned(owned),.owned_frontier_terms(owned_frontier_terms),.pending(pending),.quiet(quiet),.selected(selected),.done(done),.fault(fault),
  .selected_pc(selected_pc),.held_job(held_job),.held_gen(held_gen),.held_token(held_token),.held_pos(held_pos));
 ot_hbm_integrated_su_cp_association #(.ENABLE(ENABLE&&SU_ENABLE&&SU_BALANCED_OWNER_BOUNDARY),.FAST_OWNER_FRONTIER(SU_FAST_OWNER_FRONTIER)) u_su_association(
  .clk(clk),.por_n(por_n),.raw_grant(lease_granted),.qualified_owned(owned),.qualified_owned_terms(owned_frontier_terms),
  .exec_owned(exec_owned),.new_request_permit(new_request_permit),.fault(association_fault));
endmodule
