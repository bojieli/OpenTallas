`timescale 1ns/1ps
// SU-side CP control block (Claude:hbm-su-cpin, 2026-10-06; default off).
//
// The canonical owner-veto SU CP binder (ot_hbm_integrated_su_cp_bind +
// ot_hbm_integrated_su_cp_association) placed inside the SU-side block, so its
// loops with the SU executor (exec_owned/new_request_permit out,
// exec_done/exec_fault/retired in) are plain in-block nets with no pin stage.
// Three port classes, each with its own stage count:
//  * cmdproc launch (die crossing): launch_v/pc, cp_job/gen, token, pos are
//    captured at the pin (stage 1) and once more (stage 2, the core view);
//    stage 1 feeds the registered 192-bit live-owner compare (bind PIN_MARGIN
//    core restructure, exact vs the canonical core under the same input delay).
//  * shared-owner seat (ot_hbm_integrated_sm0_borrow lives in the memory-control
//    gather owner, a different block): lease_granted/release_r/shared_fault get
//    OWN_IN pin stages; lease_v/release_v/quiet and the held frame leave from
//    OWN_OUT pin flops. With OWN_IN+OWN_OUT>0 the release acceptance replays the
//    caller's actual fire (RELEASE_REPLAY=OWN_IN+OWN_OUT).
//  * executor (in-block): EXEC_IN/EXEC_OUT stages, 0 in the adopted shape.
//  * die/cmdproc status (pending/selected/done/fault/owned): OUT pin flops.
// native_launch is NOT a block output: it is the stateless decode
// entry?0:launch_v (canonical), done next to the cmdproc by
// ot_hbm_su_cp_side_native_steer with zero added edges.
module ot_hbm_su_cp_side #(parameter integer ENABLE=0,OWN_IN=1,OWN_OUT=1,EXEC_IN=0,EXEC_OUT=0,OUT=1,
 RELEASE_REPLAY=-1)(
 input wire clk,por_n,
 // cmdproc launch (die crossing)
 input wire [1:0] launch_v,input wire [31:0] launch_pc,
 input wire [31:0] cp_job,input wire [3:0] cp_gen,
 input wire [16:0] launch_token,input wire [19:0] launch_pos,
 // die/cmdproc status
 output wire owned,pending,selected,done,fault,
 // shared-owner seat
 output wire lease_v,release_v,quiet,
 output wire [31:0] held_job,output wire [3:0] held_gen,
 output wire [16:0] held_token,output wire [19:0] held_pos,
 input wire lease_granted,release_r,shared_fault,
 // executor (in-block)
 output wire exec_owned,new_request_permit,association_fault,
 output wire [31:0] selected_pc,
 input wire exec_done,exec_fault,input wire [3:0] retired_original_ops
);
 localparam integer REPLAY=RELEASE_REPLAY>=0?RELEASE_REPLAY:OWN_IN+OWN_OUT;
 generate if(!ENABLE)begin:off
  assign {owned,pending,selected,done,fault,lease_v,release_v}=0;assign quiet=1;
  assign {held_job,held_gen,held_token,held_pos,exec_owned,new_request_permit,association_fault,selected_pc}=0;
 end else begin:on
  initial if(OWN_IN<0||OWN_IN>3||OWN_OUT<0||OWN_OUT>1||EXEC_IN<0||EXEC_IN>3||EXEC_OUT<0||EXEC_OUT>1||OUT<0||OUT>1)
   $fatal(1,"ot_hbm_su_cp_side: stage counts out of range");
  // ---- cmdproc launch: pin capture + core stage
  localparam integer LW=2+32+32+4+17+20;
  wire [LW-1:0] l_pin={launch_v,launch_pc,cp_job,cp_gen,launch_token,launch_pos};
  reg [LW-1:0] l_q1,l_q2;
  always @(posedge clk or negedge por_n)if(!por_n)begin l_q1<=0;l_q2<=0;end else begin l_q1<=l_pin;l_q2<=l_q1;end
  wire [1:0] c_launch_v;wire [31:0] c_launch_pc,c_cp_job;wire [3:0] c_cp_gen;wire [16:0] c_launch_token;wire [19:0] c_launch_pos;
  assign {c_launch_v,c_launch_pc,c_cp_job,c_cp_gen,c_launch_token,c_launch_pos}=l_q2;
  wire [1:0] n_launch_v;wire [31:0] n_launch_pc,n_cp_job;wire [3:0] n_cp_gen;wire [16:0] n_launch_token;wire [19:0] n_launch_pos;
  assign {n_launch_v,n_launch_pc,n_cp_job,n_cp_gen,n_launch_token,n_launch_pos}=l_q1;
  wire [191:0] owner_live_next={55'd0,n_launch_pos,n_launch_token,n_cp_gen,n_cp_job,32'd0,n_launch_pc};
  // ---- shared-owner and executor inputs
  wire c_lease_granted,c_release_r,c_shared_fault,c_exec_done,c_exec_fault;wire [3:0] c_retired;
  ot_hbm_su_cp_side_stage #(.W(3),.N(OWN_IN)) s_own_in(.clk(clk),.por_n(por_n),.d({lease_granted,release_r,shared_fault}),.r(3'b0),
   .q({c_lease_granted,c_release_r,c_shared_fault}));
  ot_hbm_su_cp_side_stage #(.W(6),.N(EXEC_IN)) s_exec_in(.clk(clk),.por_n(por_n),.d({exec_done,exec_fault,retired_original_ops}),.r(6'b0),
   .q({c_exec_done,c_exec_fault,c_retired}));
  // ---- canonical owner-veto core (PIN_MARGIN restructure, exact)
  wire [1:0] c_native_launch;
  wire c_lease_v,c_release_v,c_owned,c_pending,c_quiet,c_selected,c_done,c_fault;
  wire [31:0] c_selected_pc,c_held_job;wire [3:0] c_held_gen;wire [16:0] c_held_token;wire [19:0] c_held_pos;
  wire c_exec_owned,c_new_request_permit,c_association_fault;
  wire [11:0] owned_frontier_terms;
  ot_hbm_integrated_su_cp_bind #(.ENABLE(1),.REGISTERED_OUTPUTS(1),.REGISTERED_STATUS(1),.REGISTERED_BOUNDARY(1),.GROUPED_OWNER_BOUNDARY(0),
   .BALANCED_OWNER_BOUNDARY(1),.FOUR_COMBINATIONAL_CUTS(1),.FAST_OWNER_FRONTIER(1),.PARALLEL_PHASE_VALIDATION(1),.CONTROL_TAIL_CUT(1),.OWNER_VETO_POLARITY(1),
   .PIN_MARGIN(1),.RELEASE_REPLAY(REPLAY)) u_su_cp(
   .clk(clk),.por_n(por_n),.launch_v(c_launch_v),.launch_pc(c_launch_pc),
   .cp_job(c_cp_job),.cp_gen(c_cp_gen),.launch_token(c_launch_token),.launch_pos(c_launch_pos),
   .native_launch(c_native_launch),.lease_v(c_lease_v),.lease_granted(c_lease_granted),
   .release_v(c_release_v),.release_r(c_release_r),.exec_done(c_exec_done),.exec_fault(c_exec_fault),
   .retired_original_ops(c_retired),.shared_fault(c_shared_fault),
   .owned(c_owned),.owned_frontier_terms(owned_frontier_terms),.pending(c_pending),.quiet(c_quiet),.selected(c_selected),.done(c_done),.fault(c_fault),
   .selected_pc(c_selected_pc),.held_job(c_held_job),.held_gen(c_held_gen),.held_token(c_held_token),.held_pos(c_held_pos),
   .owner_live_next(owner_live_next));
  ot_hbm_integrated_su_cp_association #(.ENABLE(1),.FAST_OWNER_FRONTIER(1),.CONTROL_TAIL_CUT(1),.OWNER_VETO_POLARITY(1),.PIN_MARGIN(1)) u_su_association(
   .clk(clk),.por_n(por_n),.raw_grant(c_lease_granted),.qualified_owned(c_owned),.qualified_owned_terms(owned_frontier_terms),
   .exec_owned(c_exec_owned),.new_request_permit(c_new_request_permit),.fault(c_association_fault));
  // ---- outputs. Reset values = the canonical core in reset with idle inputs.
  ot_hbm_su_cp_side_stage #(.W(5),.N(OUT)) s_out(.clk(clk),.por_n(por_n),.d({c_owned,c_pending,c_selected,c_done,c_fault}),.r(5'b0),
   .q({owned,pending,selected,done,fault}));
  ot_hbm_su_cp_side_stage #(.W(3+73),.N(OWN_OUT)) s_own_out(.clk(clk),.por_n(por_n),
   .d({c_lease_v,c_release_v,c_quiet,c_held_job,c_held_gen,c_held_token,c_held_pos}),.r({3'b001,73'd0}),
   .q({lease_v,release_v,quiet,held_job,held_gen,held_token,held_pos}));
  ot_hbm_su_cp_side_stage #(.W(35),.N(EXEC_OUT)) s_exec_out(.clk(clk),.por_n(por_n),
   .d({c_exec_owned,c_new_request_permit,c_association_fault,c_selected_pc}),.r(35'd0),
   .q({exec_owned,new_request_permit,association_fault,selected_pc}));
 end endgenerate
endmodule

// N pin stages (N=0: wire). Async reset to r.
module ot_hbm_su_cp_side_stage #(parameter integer W=1,N=0)(
 input wire clk,por_n,input wire [W-1:0] d,input wire [W-1:0] r,output wire [W-1:0] q);
 generate if(N==0)begin:wire_through
  assign q=d;
 end else begin:regs
  reg [W-1:0] s[0:N-1];
  integer i;
  always @(posedge clk or negedge por_n)
   if(!por_n)for(i=0;i<N;i=i+1)s[i]<=r;
   else begin s[0]<=d;for(i=1;i<N;i=i+1)s[i]<=s[i-1];end
  assign q=s[N-1];
 end endgenerate
endmodule

// Canonical native steering (stateless): native_launch=entry?0:launch_v,
// placed beside the cmdproc so native launches take no CP pin edges.
module ot_hbm_su_cp_side_native_steer(input wire [1:0] launch_v,input wire [31:0] launch_pc,output wire [1:0] native_launch);
 wire entry;
 ot_hbm_cp_frontier_entry u_entry(.pc(launch_pc),.entry(entry));
 assign native_launch=entry?2'b0:launch_v;
endmodule
