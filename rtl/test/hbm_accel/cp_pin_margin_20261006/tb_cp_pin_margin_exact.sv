`timescale 1ns/1ps
// Exact lockstep: SU_PIN_MARGIN=1 CP context (pins registered: 2 input edges,
// 1 output edge) against the canonical unregistered context driven with the
// same stimulus delayed 2 edges. Both cores then hold the same state on every
// edge; every one of the 118 output bits must satisfy new(t) == orig(t-1).
// Fault injection flips protected state rails (phase, status, qualification,
// association, SECDED header/frame words) in both cores on the same edge.
// The environment is protocol-shaped (launch/lease/exec/release) and reacts to
// the original's outputs; it also injects live-owner changes, grant revocation,
// exec/shared faults and raw random input bursts.
module tb_cp_pin_margin_exact;
 parameter integer CYCLES=400000;
 parameter integer SEED=1;
 reg clk=0;always #5 clk=~clk;
 reg por_n=0;
 // Stimulus s(t)
 reg [1:0] launch_v=0;reg [31:0] launch_pc=0,cp_job=0;reg [3:0] cp_gen=0;
 reg [16:0] launch_token=0;reg [19:0] launch_pos=0;
 reg lease_granted=0,release_r=0,exec_done=0,exec_fault=0,shared_fault=0;reg [3:0] retired=0;
 localparam integer IW=116,OW=118;
 wire [IW-1:0] s={launch_v,launch_pc,cp_job,cp_gen,launch_token,launch_pos,lease_granted,release_r,exec_done,exec_fault,retired,shared_fault};
 reg [IW-1:0] s_d1=0,s_d2=0;
 always @(posedge clk or negedge por_n)if(!por_n)begin s_d1<=0;s_d2<=0;end else begin s_d1<=s;s_d2<=s_d1;end
 wire [1:0] o_launch_v;wire [31:0] o_launch_pc,o_cp_job;wire [3:0] o_cp_gen;wire [16:0] o_launch_token;wire [19:0] o_launch_pos;
 wire o_lg,o_rr,o_ed,o_ef,o_sf;wire [3:0] o_ret;
 assign {o_launch_v,o_launch_pc,o_cp_job,o_cp_gen,o_launch_token,o_launch_pos,o_lg,o_rr,o_ed,o_ef,o_ret,o_sf}=s_d2;
 wire [OW-1:0] out0,out1;
`define CP_PARAMS .ENABLE(1),.SU_ENABLE(1),.SU_REGISTERED_OUTPUTS(1),.SU_REGISTERED_STATUS(1),.SU_REGISTERED_BOUNDARY(1),.SU_BALANCED_OWNER_BOUNDARY(1),.SU_FOUR_COMBINATIONAL_CUTS(1),.SU_FAST_OWNER_FRONTIER(1),.SU_PARALLEL_PHASE_VALIDATION(1),.SU_CONTROL_TAIL_CUT(1),.SU_OWNER_VETO_POLARITY(1)
`define CP_OUTS(o) .native_launch(o[117:116]),.lease_v(o[115]),.release_v(o[114]),.owned(o[113]),.pending(o[112]),.quiet(o[111]),.selected(o[110]),.done(o[109]),.fault(o[108]),.selected_pc(o[107:76]),.held_job(o[75:44]),.held_gen(o[43:40]),.held_token(o[39:23]),.held_pos(o[22:3]),.exec_owned(o[2]),.new_request_permit(o[1]),.association_fault(o[0])
 ot_hbm_integrated_su_cp_context #(`CP_PARAMS) dut0(.clk(clk),.por_n(por_n),
  .launch_v(o_launch_v),.launch_pc(o_launch_pc),.cp_job(o_cp_job),.cp_gen(o_cp_gen),.launch_token(o_launch_token),.launch_pos(o_launch_pos),
  .lease_granted(o_lg),.release_r(o_rr),.exec_done(o_ed),.exec_fault(o_ef),.retired_original_ops(o_ret),.shared_fault(o_sf),`CP_OUTS(out0));
 ot_hbm_integrated_su_cp_context #(`CP_PARAMS,.SU_PIN_MARGIN(1),.SU_RELEASE_REPLAY(0)) dut1(.clk(clk),.por_n(por_n),
  .launch_v(launch_v),.launch_pc(launch_pc),.cp_job(cp_job),.cp_gen(cp_gen),.launch_token(launch_token),.launch_pos(launch_pos),
  .lease_granted(lease_granted),.release_r(release_r),.exec_done(exec_done),.exec_fault(exec_fault),.retired_original_ops(retired),.shared_fault(shared_fault),`CP_OUTS(out1));
 // Original outputs seen by the environment (decoded)
 wire o_lease_v=out0[115],o_release_v=out0[114],o_owned=out0[113],o_done=out0[109],o_fault=out0[108],o_exec_owned=out0[2];
 reg [OW-1:0] out0_d=0;
 always @(posedge clk)out0_d<=out0;
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
   0:begin dut0.u_su_cp.on.phase_q[b%9]=~dut0.u_su_cp.on.phase_q[b%9];dut1.u_su_cp.on.phase_q[b%9]=~dut1.u_su_cp.on.phase_q[b%9];end
   1:begin dut0.u_su_cp.on.phase_n[b%9]=~dut0.u_su_cp.on.phase_n[b%9];dut1.u_su_cp.on.phase_n[b%9]=~dut1.u_su_cp.on.phase_n[b%9];end
   2:begin dut0.u_su_cp.on.registered_status.status_q[b%7]=~dut0.u_su_cp.on.registered_status.status_q[b%7];dut1.u_su_cp.on.registered_status.status_q[b%7]=~dut1.u_su_cp.on.registered_status.status_q[b%7];end
   3:begin dut0.u_su_cp.on.registered_status.status_n[b%7]=~dut0.u_su_cp.on.registered_status.status_n[b%7];dut1.u_su_cp.on.registered_status.status_n[b%7]=~dut1.u_su_cp.on.registered_status.status_n[b%7];end
   4:begin dut0.u_su_cp.on.registered_status.qualification_fault_n=~dut0.u_su_cp.on.registered_status.qualification_fault_n;dut1.u_su_cp.on.registered_status.qualification_fault_n=~dut1.u_su_cp.on.registered_status.qualification_fault_n;end
   5:begin dut0.u_su_association.on.associated_n=~dut0.u_su_association.on.associated_n;dut1.u_su_association.on.associated_n=~dut1.u_su_association.on.associated_n;end
   6:begin dut0.u_su_cp.on.frame_lo[b%72]=~dut0.u_su_cp.on.frame_lo[b%72];dut1.u_su_cp.on.frame_lo[b%72]=~dut1.u_su_cp.on.frame_lo[b%72];end
   7:begin dut0.u_su_cp.on.pc_code[b%72]=~dut0.u_su_cp.on.pc_code[b%72];dut1.u_su_cp.on.pc_code[b%72]=~dut1.u_su_cp.on.pc_code[b%72];end
   8:begin dut0.u_su_cp.on.checked_valid_q=~dut0.u_su_cp.on.checked_valid_q;dut1.u_su_cp.on.checked_valid_q=~dut1.u_su_cp.on.checked_valid_q;end
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
  $display("EXACT checks=%0d mismatches=%0d first=%0d launches=%0d native=%0d leases=%0d release_accepts=%0d done=%0d fault_cycles=%0d upsets=%0d owner_changes=%0d revokes=%0d shared_faults=%0d exec_faults=%0d raw_cycles=%0d resets=%0d",
   checks,mism,first_bad,n_launch,n_native,n_lease,n_release_accept,n_done,n_fault_cycles,n_upsets,n_owner_change,n_revoke,n_sfault,n_efault,n_raw,n_resets);
  if(mism==0&&n_done>100&&n_upsets>100&&n_fault_cycles>100&&n_release_accept>100)$display("PASS");else $display("FAIL");
  $finish;
 end
endmodule
