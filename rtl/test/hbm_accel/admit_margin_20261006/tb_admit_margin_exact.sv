`timescale 1ns/1ps
// REPLAY=1 (default; the deployed margin CP is SU_PIN_MARGIN=1 +
// SU_RELEASE_REPLAY=1): the environment is closed around the margin CP's own
// pins (latency-insensitive release), so there is no cycle lockstep; the admit
// truth is the margin CP's CORE state (pending|selected|core grant), which
// reflects pin inputs 2 edges late, compared with the guard 2 edges earlier.
// REPLAY=0: the lockstep below is also checked (as in cp_pin_margin_20261006).
// Negative controls (must be unsafe): SHADOW=0 (CP outputs only: admit
// up to 3 edges too early) and SHADOW=2 (one edge too short).
// Exact lockstep (REPLAY=0): SU_PIN_MARGIN=1 CP context (pins registered: 2 input edges,
// 1 output edge) against the canonical unregistered context driven with the
// same stimulus delayed 2 edges. Both cores then hold the same state on every
// edge; every one of the 118 output bits must satisfy new(t) == orig(t-1).
// Fault injection flips protected state rails (phase, status, qualification,
// association, SECDED header/frame words) in both cores on the same edge.
// The environment is protocol-shaped (launch/lease/exec/release) and reacts to
// the original's outputs; it also injects live-owner changes, grant revocation,
// exec/shared faults and raw random input bursts.
module tb_admit_margin_exact;
 parameter integer CYCLES=400000,UPSETS=0,REPLAY=1;
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
 ot_hbm_integrated_su_cp_context #(`CP_PARAMS,.SU_PIN_MARGIN(1),.SU_RELEASE_REPLAY(REPLAY)) dut1(.clk(clk),.por_n(por_n),
  .launch_v(launch_v),.launch_pc(launch_pc),.cp_job(cp_job),.cp_gen(cp_gen),.launch_token(launch_token),.launch_pos(launch_pos),
  .lease_granted(lease_granted),.release_r(release_r),.exec_done(exec_done),.exec_fault(exec_fault),.retired_original_ops(retired),.shared_fault(shared_fault),`CP_OUTS(out1));
 // ---- admit re-qualification
 // Admit truth: the margin CP's core state (inputs 2 edges late) plus the core
// view of the raw grant (cluster su_owned is the raw peer grant). A FAULTED CP
// (sticky FAIL quarantine, reset only) re-asserts selected without any launch,
// possibly from a fault that reaches the pin in the same edge as the admit;
// that is not an SU ownership claim (counted separately as fault_sel).
wire ref_busy=dut1.c_pending|(dut1.c_selected&!dut1.c_fault)|dut1.c_lease_granted;
wire fault_sel=dut1.c_selected&dut1.c_fault;
 wire m_busy=out1[112]|out1[110]|lease_granted;
 wire g3_busy,g0_busy,g2_busy;reg [1:0] g3d=0,g0d=0,g2d=0;
 always @(posedge clk)begin g3d<={g3d[0],g3_busy};g0d<={g0d[0],g0_busy};g2d<={g2d[0],g2_busy};end
 ot_hbm_integrated_admit_guard #(.SHADOW(3)) g3(.clk(clk),.por_n(por_n),.launch_any(|launch_v),.cp_busy(m_busy),.busy(g3_busy));
 ot_hbm_integrated_admit_guard #(.SHADOW(2)) g2(.clk(clk),.por_n(por_n),.launch_any(|launch_v),.cp_busy(m_busy),.busy(g2_busy));
 ot_hbm_integrated_admit_guard #(.SHADOW(0)) g0(.clk(clk),.por_n(por_n),.launch_any(|launch_v),.cp_busy(m_busy),.busy(g0_busy));
 integer blk3=0,fsel3=0,unsafe3=0,unsafe0=0,unsafe2=0,adm3=0,adm0=0,adm_ref=0,uchk=0;
 always @(posedge clk)if(por_n&&since_reset>=6)begin
  uchk<=uchk+1;
  if(!ref_busy)adm_ref<=adm_ref+1;
  if(!g3d[1])begin adm3<=adm3+1;if(ref_busy)begin unsafe3<=unsafe3+1;if(unsafe3<6)$display("U cyc=%0d core p/s/g=%b%b%b st=%0d",cyc,dut1.c_pending,dut1.c_selected,dut1.c_lease_granted,st);end end
  if(g3d[1]&&!ref_busy&&!dut1.c_fault)blk3<=blk3+1;
  if(!g3d[1]&&fault_sel&&!ref_busy)fsel3<=fsel3+1;
  if(!g0d[1])begin adm0<=adm0+1;if(ref_busy)unsafe0<=unsafe0+1;end
  if(!g2d[1]&&ref_busy)unsafe2<=unsafe2+1;
 end
 integer trace_at=-1;
 initial if(!$value$plusargs("TRACE=%d",trace_at))trace_at=-1;
 always @(posedge clk)if(trace_at>=0&&cyc>=trace_at-10&&cyc<=trace_at+1)
  $display("T cyc=%0d por=%b lv=%b pc=%h out1 p/s=%b%b lg=%b g3=%b sr=%b g3d=%b core lv=%b p/s/g=%b%b%b q/d/f/o=%b%b%b%b ph=%b",cyc,por_n,launch_v,launch_pc,out1[112],out1[110],lease_granted,g3_busy,g3.on.sr,g3d,dut1.c_launch_v,dut1.c_pending,dut1.c_selected,dut1.c_lease_granted,dut1.c_quiet,dut1.c_done,dut1.c_fault,dut1.c_owned,dut1.u_su_cp.on.phase);
 // Original outputs seen by the environment (decoded)
 wire [OW-1:0] env=REPLAY?out1:out0;
 wire o_lease_v=env[115],o_release_v=env[114],o_owned=env[113],o_done=env[109],o_fault=env[108],o_exec_owned=env[2];
 reg [OW-1:0] out0_d=0;
 always @(posedge clk)out0_d<=out0;
 integer cyc=0,mism=0,checks=0,first_bad=-1;
 integer n_done=0,n_fault_cycles=0,n_upsets=0,n_owner_change=0,n_release_accept=0,n_revoke=0,n_sfault=0,n_efault=0,n_raw=0,n_launch=0,n_native=0,n_resets=0,n_lease=0;
 integer seed,sv,k,junk;
 // ---------------- environment ----------------
 integer st=0,wait_c=0,mode_raw=0,raw_left=0,since_reset=0;
 task automatic new_frame;begin
  cp_job=$signed($urandom);cp_gen=$signed($urandom);launch_token=$signed($urandom);launch_pos=$signed($urandom);
  launch_pc=($signed($urandom)&1)?32'h80000004:32'hc0000004;
 end endtask
 always @(negedge clk)if(por_n)begin
  cyc=cyc+1;since_reset=since_reset+1;
  // protocol-shaped environment reacting to the original (delayed) outputs
  if(raw_left>0)begin
   raw_left=raw_left-1;n_raw=n_raw+1;
   {launch_v,launch_pc,cp_job,cp_gen,launch_token,launch_pos}={$signed($urandom),$signed($urandom),$signed($urandom),$signed($urandom)};
   if($signed($urandom)&1)launch_pc=32'h80000004;
   {lease_granted,release_r,exec_done,exec_fault,shared_fault}=$signed($urandom);
   if(($signed($urandom)&7)!=0)begin exec_fault=0;shared_fault=0;end
   retired=($signed($urandom)&1)?4:$signed($urandom);
  end else begin
   release_r=($signed($urandom)%3)!=0;
   if(($signed($urandom)%4000)==0)begin raw_left=($signed($urandom)&31)+1;end
   case(st)
    0:begin // idle; sometimes a native launch, else an SU launch
     lease_granted=0;exec_done=0;exec_fault=0;shared_fault=0;retired=4;
     if(wait_c>0)wait_c=wait_c-1;
     else if(($signed($urandom)&3)==0)begin launch_v=($signed($urandom)&1)?2'b10:2'b01;launch_pc=32'h00001000+($signed($urandom)&255);n_native=n_native+1;wait_c=1;end
     else begin launch_v=0;new_frame;launch_v=($signed($urandom)%50==0)?2'b11:2'b01;st=1;wait_c=($signed($urandom)&3);n_launch=n_launch+1;end
    end
    1:begin // hold the launch; grant after lease_v
     if(($signed($urandom)%3)==0)launch_v=0; // CP holds after the entry edge
     if(o_lease_v&&wait_c==0)begin lease_granted=1;st=2;wait_c=($signed($urandom)&7);n_lease=n_lease+1;end
     else if(wait_c>0)wait_c=wait_c-1;
    end
    2:begin // executor runs
     if(wait_c>0)wait_c=wait_c-1;
     else begin exec_done=1;retired=(($signed($urandom)%40)==0)?3:4;st=3;end
    end
    3:begin // release handshake
     if(o_release_v&&release_r)begin st=4;n_release_accept=n_release_accept+1;wait_c=($signed($urandom)&3);end
    end
    4:begin // grant drops, executor clears
     if(wait_c>0)wait_c=wait_c-1;else begin lease_granted=0;exec_done=($signed($urandom)&1);st=5;end
    end
    5:begin exec_done=0;launch_v=0;if(o_done||($signed($urandom)%64)==0)begin st=0;wait_c=($signed($urandom)&7);end end
   endcase
   // rare perturbations
   if(st!=0&&($signed($urandom)%700)==0)begin cp_job[$signed($urandom)&31]=~cp_job[$signed($urandom)&31];n_owner_change=n_owner_change+1;end
   if(st!=0&&($signed($urandom)%900)==0)begin launch_pos[$signed($urandom)%20]=~launch_pos[0];n_owner_change=n_owner_change+1;end
   if(st>=2&&($signed($urandom)%1500)==0)begin lease_granted=0;n_revoke=n_revoke+1;end
   if(($signed($urandom)%3000)==0)begin shared_fault=1;n_sfault=n_sfault+1;end
   if(st>=2&&($signed($urandom)%3000)==0)begin exec_fault=1;n_efault=n_efault+1;end
  end
  if(o_fault)n_fault_cycles=n_fault_cycles+1;
  if(o_done)n_done=n_done+1;
  // recover from a stuck/failed transaction
  if((o_fault&&($signed($urandom)%40)==0)||since_reset>3000)begin
   por_n=0;st=0;wait_c=0;raw_left=0;since_reset=0;n_resets=n_resets+1;
   {launch_v,launch_pc,cp_job,cp_gen,launch_token,launch_pos,lease_granted,release_r,exec_done,exec_fault,retired,shared_fault}=0;
  end
 end else begin
  por_n=1;since_reset=0;
 end
 // ---------------- state upsets, same core edge in both ----------------
 always @(negedge clk)if(UPSETS&&por_n&&cyc>8&&($signed($urandom)%500)==0)begin : upset
  integer w,b;
  w=$signed($urandom)%9;if(w<0)w=-w;b=$signed($urandom);if(b<0)b=-b;
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
  if(!REPLAY&&por_n&&settle>=3)begin
   checks<=checks+1;
   if(out1!==out0_d)begin
    mism<=mism+1;
    if(first_bad<0)begin first_bad<=cyc;$display("MISMATCH cyc=%0d new=%h orig_d=%h diff=%h",cyc,out1,out0_d,out1^out0_d);end
   end
  end
 end
 initial begin
   if(!$value$plusargs("SEED=%d",sv))sv=SEED;
   // The simulator random(var) degenerates (the seed shifts to a constant);
   // stimulus uses the process RNG, seeded per run (+SEED=N advances it).
   for(k=0;k<sv*7919;k=k+1)junk=$urandom;
  repeat(4)@(posedge clk);por_n=1;
  wait(cyc>=CYCLES);
  @(posedge clk);
  $display("EXACT checks=%0d mismatches=%0d first=%0d launches=%0d native=%0d leases=%0d release_accepts=%0d done=%0d fault_cycles=%0d upsets=%0d owner_changes=%0d revokes=%0d shared_faults=%0d exec_faults=%0d raw_cycles=%0d resets=%0d",
   checks,mism,first_bad,n_launch,n_native,n_lease,n_release_accept,n_done,n_fault_cycles,n_upsets,n_owner_change,n_revoke,n_sfault,n_efault,n_raw,n_resets);
  $display("ADMIT REPLAY=%0d checks=%0d ref_idle=%0d shadow3_admit=%0d (extra_blocked_unfaulted=%0d) shadow3_unsafe=%0d | NEGCTL shadow0_admit=%0d shadow0_unsafe=%0d shadow2_unsafe=%0d | fault_quarantine_admits=%0d",REPLAY,uchk,adm_ref,adm3,blk3,unsafe3,adm0,unsafe0,unsafe2,fsel3);
  if(mism==0&&(REPLAY||checks>0)&&unsafe3==0&&n_done>100&&n_release_accept>100&&n_fault_cycles>100)$display("PASS");else $display("FAIL");
  if(unsafe0>0)$display("NEGCTL_SHADOW0 FAIL (expected: too-early admit caught)");else $display("NEGCTL_SHADOW0 PASS (unexpected)");
  if(unsafe2>0)$display("NEGCTL_SHADOW2 FAIL (expected)");else $display("NEGCTL_SHADOW2 PASS");
  $finish;
 end
endmodule
