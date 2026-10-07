`timescale 1ns/1ps
// Exact lockstep for the SU-side CP block ot_hbm_su_cp_side (Claude:hbm-su-cpin
// 2026-10-06), adapted from tb_cp_pin_margin_exact. Reference: the canonical
// unregistered context driven with the stimulus delayed per port class
// (launch 2 edges, shared-owner inputs OWN_IN, executor inputs EXEC_IN); every
// block output must equal the reference output delayed by its class stage
// (status OUT, shared-owner seat OWN_OUT, executor EXEC_OUT). The cmdproc-side
// native steering (no CP edges) must equal the reference native_launch with
// only the 2 launch-delay edges. Same environment, perturbations and protected
// state upsets as the pin-margin bench.
module tb_su_cp_side_exact;
 parameter integer CYCLES=400000;
 parameter integer SEED=1;
 parameter integer OWN_IN=1,OWN_OUT=1,EXEC_IN=0,EXEC_OUT=1,OUT=1;
 reg clk=0;always #5 clk=~clk;
 reg por_n=0;
 // Stimulus s(t)
 reg [1:0] launch_v=0;reg [31:0] launch_pc=0,cp_job=0;reg [3:0] cp_gen=0;
 reg [16:0] launch_token=0;reg [19:0] launch_pos=0;
 reg lease_granted=0,release_r=0,exec_done=0,exec_fault=0,shared_fault=0;reg [3:0] retired=0;
 localparam integer IW=116,OW=118;
 wire [IW-1:0] s={launch_v,launch_pc,cp_job,cp_gen,launch_token,launch_pos,lease_granted,release_r,exec_done,exec_fault,retired,shared_fault};
 wire [1:0] o_launch_v;wire [31:0] o_launch_pc,o_cp_job;wire [3:0] o_cp_gen;wire [16:0] o_launch_token;wire [19:0] o_launch_pos;
 wire o_lg,o_rr,o_ed,o_ef,o_sf;wire [3:0] o_ret;
 ot_hbm_su_cp_side_stage #(.W(107),.N(2)) d_launch(.clk(clk),.por_n(por_n),.d({launch_v,launch_pc,cp_job,cp_gen,launch_token,launch_pos}),.r(107'd0),
  .q({o_launch_v,o_launch_pc,o_cp_job,o_cp_gen,o_launch_token,o_launch_pos}));
 ot_hbm_su_cp_side_stage #(.W(3),.N(OWN_IN)) d_own(.clk(clk),.por_n(por_n),.d({lease_granted,release_r,shared_fault}),.r(3'd0),.q({o_lg,o_rr,o_sf}));
 ot_hbm_su_cp_side_stage #(.W(6),.N(EXEC_IN)) d_exec(.clk(clk),.por_n(por_n),.d({exec_done,exec_fault,retired}),.r(6'd0),.q({o_ed,o_ef,o_ret}));
 wire [OW-1:0] out0,out1;
`define CP_PARAMS .ENABLE(1),.SU_ENABLE(1),.SU_REGISTERED_OUTPUTS(1),.SU_REGISTERED_STATUS(1),.SU_REGISTERED_BOUNDARY(1),.SU_BALANCED_OWNER_BOUNDARY(1),.SU_FOUR_COMBINATIONAL_CUTS(1),.SU_FAST_OWNER_FRONTIER(1),.SU_PARALLEL_PHASE_VALIDATION(1),.SU_CONTROL_TAIL_CUT(1),.SU_OWNER_VETO_POLARITY(1)
`define CP_OUTS(o) .native_launch(o[117:116]),.lease_v(o[115]),.release_v(o[114]),.owned(o[113]),.pending(o[112]),.quiet(o[111]),.selected(o[110]),.done(o[109]),.fault(o[108]),.selected_pc(o[107:76]),.held_job(o[75:44]),.held_gen(o[43:40]),.held_token(o[39:23]),.held_pos(o[22:3]),.exec_owned(o[2]),.new_request_permit(o[1]),.association_fault(o[0])
 ot_hbm_integrated_su_cp_context #(`CP_PARAMS) dut0(.clk(clk),.por_n(por_n),
  .launch_v(o_launch_v),.launch_pc(o_launch_pc),.cp_job(o_cp_job),.cp_gen(o_cp_gen),.launch_token(o_launch_token),.launch_pos(o_launch_pos),
  .lease_granted(o_lg),.release_r(o_rr),.exec_done(o_ed),.exec_fault(o_ef),.retired_original_ops(o_ret),.shared_fault(o_sf),`CP_OUTS(out0));
 // DUT: the SU-side block (RELEASE_REPLAY=0: lockstep feeds both cores the same inputs).
 wire [1:0] steer;
 ot_hbm_su_cp_side_native_steer u_steer(.launch_v(launch_v),.launch_pc(launch_pc),.native_launch(steer));
 ot_hbm_su_cp_side #(.ENABLE(1),.OWN_IN(OWN_IN),.OWN_OUT(OWN_OUT),.EXEC_IN(EXEC_IN),.EXEC_OUT(EXEC_OUT),.OUT(OUT),.RELEASE_REPLAY(0)) dut1(.clk(clk),.por_n(por_n),
  .launch_v(launch_v),.launch_pc(launch_pc),.cp_job(cp_job),.cp_gen(cp_gen),.launch_token(launch_token),.launch_pos(launch_pos),
  .owned(out1[113]),.pending(out1[112]),.selected(out1[110]),.done(out1[109]),.fault(out1[108]),
  .lease_v(out1[115]),.release_v(out1[114]),.quiet(out1[111]),.held_job(out1[75:44]),.held_gen(out1[43:40]),.held_token(out1[39:23]),.held_pos(out1[22:3]),
  .lease_granted(lease_granted),.release_r(release_r),.shared_fault(shared_fault),
  .exec_owned(out1[2]),.new_request_permit(out1[1]),.association_fault(out1[0]),.selected_pc(out1[107:76]),
  .exec_done(exec_done),.exec_fault(exec_fault),.retired_original_ops(retired));
 // native steering: compare against the reference with the 2 launch edges only
 wire [1:0] steer_d2;
 ot_hbm_su_cp_side_stage #(.W(2),.N(2)) d_steer(.clk(clk),.por_n(por_n),.d(steer),.r(2'd0),.q(steer_d2));
 assign out1[117:116]=steer_d2;
 // Original outputs seen by the environment (decoded)
 wire o_lease_v=out0[115],o_release_v=out0[114],o_owned=out0[113],o_done=out0[109],o_fault=out0[108],o_exec_owned=out0[2];
 // reference outputs delayed per class (reset values of the block's pin flops)
 wire [OW-1:0] out0_d;
 assign out0_d[117:116]=out0[117:116];
 ot_hbm_su_cp_side_stage #(.W(5),.N(OUT)) r_out(.clk(clk),.por_n(por_n),.d({out0[113],out0[112],out0[110],out0[109],out0[108]}),.r(5'd0),
  .q({out0_d[113],out0_d[112],out0_d[110],out0_d[109],out0_d[108]}));
 ot_hbm_su_cp_side_stage #(.W(76),.N(OWN_OUT)) r_own(.clk(clk),.por_n(por_n),.d({out0[115],out0[114],out0[111],out0[75:3]}),.r({3'b001,73'd0}),
  .q({out0_d[115],out0_d[114],out0_d[111],out0_d[75:3]}));
 ot_hbm_su_cp_side_stage #(.W(35),.N(EXEC_OUT)) r_exec(.clk(clk),.por_n(por_n),.d({out0[2],out0[1],out0[0],out0[107:76]}),.r(35'd0),
  .q({out0_d[2],out0_d[1],out0_d[0],out0_d[107:76]}));
 integer cyc=0,mism=0,checks=0,first_bad=-1;
 integer n_done=0,n_fault_cycles=0,n_upsets=0,n_owner_change=0,n_release_accept=0,n_revoke=0,n_sfault=0,n_efault=0,n_raw=0,n_launch=0,n_native=0,n_resets=0,n_lease=0;
 integer seed;
 // ---------------- environment ----------------
 integer st=0,wait_c=0,mode_raw=0,raw_left=0,since_reset=0;
 task automatic new_frame;begin
  cp_job=$random(seed);cp_gen=$random(seed);launch_token=$random(seed);launch_pos=$random(seed);
  launch_pc=($random(seed)&1)?32'h80000004:32'hc0000004;
 end endtask
 always @(negedge clk)if(por_n)begin
  cyc=cyc+1;since_reset=since_reset+1;
  // protocol-shaped environment reacting to the original (delayed) outputs
  if(raw_left>0)begin
   raw_left=raw_left-1;n_raw=n_raw+1;
   {launch_v,launch_pc,cp_job,cp_gen,launch_token,launch_pos}={$random(seed),$random(seed),$random(seed),$random(seed)};
   if($random(seed)&1)launch_pc=32'h80000004;
   {lease_granted,release_r,exec_done,exec_fault,shared_fault}=$random(seed);
   if(($random(seed)&7)!=0)begin exec_fault=0;shared_fault=0;end
   retired=($random(seed)&1)?4:$random(seed);
  end else begin
   release_r=($random(seed)%3)!=0;
   if(($random(seed)%4000)==0)begin raw_left=($random(seed)&31)+1;end
   case(st)
    0:begin // idle; sometimes a native launch, else an SU launch
     lease_granted=0;exec_done=0;exec_fault=0;shared_fault=0;retired=4;
     if(wait_c>0)wait_c=wait_c-1;
     else if(($random(seed)&3)==0)begin launch_v=($random(seed)&1)?2'b10:2'b01;launch_pc=32'h00001000+($random(seed)&255);n_native=n_native+1;wait_c=1;end
     else begin launch_v=0;new_frame;launch_v=($random(seed)%50==0)?2'b11:2'b01;st=1;wait_c=($random(seed)&3);n_launch=n_launch+1;end
    end
    1:begin // hold the launch; grant after lease_v
     if(($random(seed)%3)==0)launch_v=0; // CP holds after the entry edge
     if(o_lease_v&&wait_c==0)begin lease_granted=1;st=2;wait_c=($random(seed)&7);n_lease=n_lease+1;end
     else if(wait_c>0)wait_c=wait_c-1;
    end
    2:begin // executor runs
     if(wait_c>0)wait_c=wait_c-1;
     else begin exec_done=1;retired=(($random(seed)%40)==0)?3:4;st=3;end
    end
    3:begin // release handshake
     if(o_release_v&&release_r)begin st=4;n_release_accept=n_release_accept+1;wait_c=($random(seed)&3);end
    end
    4:begin // grant drops, executor clears
     if(wait_c>0)wait_c=wait_c-1;else begin lease_granted=0;exec_done=($random(seed)&1);st=5;end
    end
    5:begin exec_done=0;launch_v=0;if(o_done||($random(seed)%64)==0)begin st=0;wait_c=($random(seed)&7);end end
   endcase
   // rare perturbations
   if(st!=0&&($random(seed)%700)==0)begin cp_job[$random(seed)&31]=~cp_job[$random(seed)&31];n_owner_change=n_owner_change+1;end
   if(st!=0&&($random(seed)%900)==0)begin launch_pos[$random(seed)%20]=~launch_pos[0];n_owner_change=n_owner_change+1;end
   if(st>=2&&($random(seed)%1500)==0)begin lease_granted=0;n_revoke=n_revoke+1;end
   if(($random(seed)%3000)==0)begin shared_fault=1;n_sfault=n_sfault+1;end
   if(st>=2&&($random(seed)%3000)==0)begin exec_fault=1;n_efault=n_efault+1;end
  end
  if(o_fault)n_fault_cycles=n_fault_cycles+1;
  if(o_done)n_done=n_done+1;
  // recover from a stuck/failed transaction
  if((o_fault&&($random(seed)%40)==0)||since_reset>3000)begin
   por_n=0;st=0;wait_c=0;raw_left=0;since_reset=0;n_resets=n_resets+1;
   {launch_v,launch_pc,cp_job,cp_gen,launch_token,launch_pos,lease_granted,release_r,exec_done,exec_fault,retired,shared_fault}=0;
  end
 end else begin
  por_n=1;since_reset=0;
 end
 // ---------------- state upsets, same core edge in both ----------------
 always @(negedge clk)if(por_n&&cyc>8&&($random(seed)%500)==0)begin : upset
  integer w,b;
  w=$random(seed)%9;if(w<0)w=-w;b=$random(seed);if(b<0)b=-b;
  n_upsets=n_upsets+1;
  case(w)
   0:begin dut0.u_su_cp.on.phase_q[b%9]=~dut0.u_su_cp.on.phase_q[b%9];dut1.on.u_su_cp.on.phase_q[b%9]=~dut1.on.u_su_cp.on.phase_q[b%9];end
   1:begin dut0.u_su_cp.on.phase_n[b%9]=~dut0.u_su_cp.on.phase_n[b%9];dut1.on.u_su_cp.on.phase_n[b%9]=~dut1.on.u_su_cp.on.phase_n[b%9];end
   2:begin dut0.u_su_cp.on.registered_status.status_q[b%7]=~dut0.u_su_cp.on.registered_status.status_q[b%7];dut1.on.u_su_cp.on.registered_status.status_q[b%7]=~dut1.on.u_su_cp.on.registered_status.status_q[b%7];end
   3:begin dut0.u_su_cp.on.registered_status.status_n[b%7]=~dut0.u_su_cp.on.registered_status.status_n[b%7];dut1.on.u_su_cp.on.registered_status.status_n[b%7]=~dut1.on.u_su_cp.on.registered_status.status_n[b%7];end
   4:begin dut0.u_su_cp.on.registered_status.qualification_fault_n=~dut0.u_su_cp.on.registered_status.qualification_fault_n;dut1.on.u_su_cp.on.registered_status.qualification_fault_n=~dut1.on.u_su_cp.on.registered_status.qualification_fault_n;end
   5:begin dut0.u_su_association.on.associated_n=~dut0.u_su_association.on.associated_n;dut1.on.u_su_association.on.associated_n=~dut1.on.u_su_association.on.associated_n;end
   6:begin dut0.u_su_cp.on.frame_lo[b%72]=~dut0.u_su_cp.on.frame_lo[b%72];dut1.on.u_su_cp.on.frame_lo[b%72]=~dut1.on.u_su_cp.on.frame_lo[b%72];end
   7:begin dut0.u_su_cp.on.pc_code[b%72]=~dut0.u_su_cp.on.pc_code[b%72];dut1.on.u_su_cp.on.pc_code[b%72]=~dut1.on.u_su_cp.on.pc_code[b%72];end
   8:begin dut0.u_su_cp.on.checked_valid_q=~dut0.u_su_cp.on.checked_valid_q;dut1.on.u_su_cp.on.checked_valid_q=~dut1.on.u_su_cp.on.checked_valid_q;end
  endcase
 end
 // ---------------- compare ----------------
 integer settle=0;
 always @(posedge clk)begin
  if(!por_n)settle<=0;else settle<=settle+1;
  if(por_n&&settle>=3)begin
   checks<=checks+1;
   if(out1!==out0_d)begin
    mism<=mism+1;
    if(first_bad<0)begin first_bad<=cyc;$display("MISMATCH cyc=%0d new=%h orig_d=%h diff=%h",cyc,out1,out0_d,out1^out0_d);end
   end
  end
 end
 initial begin
  seed=SEED;
  repeat(4)@(posedge clk);por_n=1;
  wait(cyc>=CYCLES);
  @(posedge clk);
  $display("EXACT OWN_IN=%0d OWN_OUT=%0d EXEC_IN=%0d EXEC_OUT=%0d OUT=%0d checks=%0d mismatches=%0d first=%0d launches=%0d native=%0d leases=%0d release_accepts=%0d done=%0d fault_cycles=%0d upsets=%0d owner_changes=%0d revokes=%0d shared_faults=%0d exec_faults=%0d raw_cycles=%0d resets=%0d",
   OWN_IN,OWN_OUT,EXEC_IN,EXEC_OUT,OUT,checks,mism,first_bad,n_launch,n_native,n_lease,n_release_accept,n_done,n_fault_cycles,n_upsets,n_owner_change,n_revoke,n_sfault,n_efault,n_raw,n_resets);
  if(mism==0&&n_done>100&&n_upsets>100&&n_fault_cycles>100&&n_release_accept>100)$display("PASS");else $display("FAIL");
  $finish;
 end
endmodule
