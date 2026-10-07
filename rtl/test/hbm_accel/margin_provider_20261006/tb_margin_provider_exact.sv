`timescale 1ns/1ps
// SU_PIN_MARGIN + SU_PROVIDER_ADAPTER exact bench (2026-10-06).
// DUT = the cluster's margin+provider composition: SU_PIN_MARGIN=1 CP context
// (2 input + 1 output pin edges) + ot_hbm_integrated_su_provider_margin
// (LIVE_GRANT_GUARD=1), with the executor's done/fault/retired reaching the CP
// pins through the provider hookup exactly as wired in the cluster.
// REF = the unregistered path delayed by the CP pin latency: the canonical
// unregistered CP context (SU_PIN_MARGIN=0, bind + association) driven with the
// CP stimulus delayed 2 edges, its outputs taken 1 edge later (3 total), and
// the cluster's legacy provider equations (g_su_legacy_provider) on the live
// provider datapath, plus the live-grant AND on NEW requests.
// REPLAY=0: every one of the 118 CP output bits and every provider-boundary bit
// (request valid/ready/337-bit payload, response valid/ready/273-bit payload,
// 73-bit owner frame, selected pc, caller done/fault/retired, exec_owned,
// permit, fault) must match REF on every edge. REPLAY=1 (deployed
// SU_RELEASE_REPLAY): no CP lockstep (latency-insensitive release); the
// provider boundary is checked against the same equations on the DUT pins.
// Unsafe admit: a NEW provider request handshake (req_v&&req_r) on an edge
// where the live raw grant is 0. Must be 0 for the DUT.
// Negative controls (must FAIL): NG = same composition with LIVE_GRANT_GUARD=0
// (unsafe>0); LAT2 = the provider boundary compared against REF taken at 2
// edges of CP latency instead of 3 (mismatches>0).
module tb_margin_provider_exact;
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
 // ---- provider datapath stimulus (live)
 reg exec_req_v=0,provider_req_r=0,provider_rsp_v=0,exec_rsp_r=0;
 reg [336:0] exec_req=0;reg [272:0] provider_rsp=0;
 // ---- DUT provider hookup (cluster wiring) on the margin CP pins
 wire p_req_v,p_exec_req_r,p_rsp_r,p_exec_rsp_v,p_eo,p_pm,p_fa,p_cd,p_cf;
 wire [336:0] p_req;wire [272:0] p_exec_rsp;wire [72:0] p_frame;wire [31:0] p_pc;wire [3:0] p_cr;

`define CP_PARAMS .ENABLE(1),.SU_ENABLE(1),.SU_REGISTERED_OUTPUTS(1),.SU_REGISTERED_STATUS(1),.SU_REGISTERED_BOUNDARY(1),.SU_BALANCED_OWNER_BOUNDARY(1),.SU_FOUR_COMBINATIONAL_CUTS(1),.SU_FAST_OWNER_FRONTIER(1),.SU_PARALLEL_PHASE_VALIDATION(1),.SU_CONTROL_TAIL_CUT(1),.SU_OWNER_VETO_POLARITY(1)
`define CP_OUTS(o) .native_launch(o[117:116]),.lease_v(o[115]),.release_v(o[114]),.owned(o[113]),.pending(o[112]),.quiet(o[111]),.selected(o[110]),.done(o[109]),.fault(o[108]),.selected_pc(o[107:76]),.held_job(o[75:44]),.held_gen(o[43:40]),.held_token(o[39:23]),.held_pos(o[22:3]),.exec_owned(o[2]),.new_request_permit(o[1]),.association_fault(o[0])
 ot_hbm_integrated_su_cp_context #(`CP_PARAMS) dut0(.clk(clk),.por_n(por_n),
  .launch_v(o_launch_v),.launch_pc(o_launch_pc),.cp_job(o_cp_job),.cp_gen(o_cp_gen),.launch_token(o_launch_token),.launch_pos(o_launch_pos),
  .lease_granted(o_lg),.release_r(o_rr),.exec_done(o_ed),.exec_fault(o_ef),.retired_original_ops(o_ret),.shared_fault(o_sf),`CP_OUTS(out0));
 ot_hbm_integrated_su_cp_context #(`CP_PARAMS,.SU_PIN_MARGIN(1),.SU_RELEASE_REPLAY(REPLAY)) dut1(.clk(clk),.por_n(por_n),
  .launch_v(launch_v),.launch_pc(launch_pc),.cp_job(cp_job),.cp_gen(cp_gen),.launch_token(launch_token),.launch_pos(launch_pos),
  .lease_granted(lease_granted),.release_r(release_r),.exec_done(p_cd),.exec_fault(p_cf),.retired_original_ops(p_cr),.shared_fault(shared_fault),`CP_OUTS(out1));
 integer trace_at=-1;
 initial if(!$value$plusargs("TRACE=%d",trace_at))trace_at=-1;
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
 ot_hbm_integrated_su_provider_margin #(.ENABLE(1),.LIVE_GRANT_GUARD(1)) prov(
  .raw_grant(lease_granted),.ext_exec_owned(out1[2]),.ext_new_request_permit(out1[1]),.ext_fault(out1[0]),
  .exec_owned(p_eo),.new_request_permit(p_pm),.fault(p_fa),
  .exec_req_v(exec_req_v),.exec_req_r(p_exec_req_r),.exec_req(exec_req),
  .provider_req_v(p_req_v),.provider_req_r(provider_req_r),.provider_req(p_req),
  .provider_rsp_v(provider_rsp_v),.provider_rsp_r(p_rsp_r),.provider_rsp(provider_rsp),
  .exec_rsp_v(p_exec_rsp_v),.exec_rsp_r(exec_rsp_r),.exec_rsp(p_exec_rsp),
  .held_job(out1[75:44]),.held_gen(out1[43:40]),.held_token(out1[39:23]),.held_pos(out1[22:3]),.owner_frame(p_frame),
  .held_selected_pc(out1[107:76]),.selected_pc(p_pc),
  .exec_done(exec_done),.exec_fault(exec_fault),.retired_original_ops(retired),
  .caller_exec_done(p_cd),.caller_exec_fault(p_cf),.caller_retired_original_ops(p_cr));
 // Negative control NG: no live-grant guard.
 wire n_req_v,n_req_r;
 ot_hbm_integrated_su_provider_margin #(.ENABLE(1),.LIVE_GRANT_GUARD(0)) prov_ng(
  .raw_grant(lease_granted),.ext_exec_owned(out1[2]),.ext_new_request_permit(out1[1]),.ext_fault(out1[0]),
  .exec_owned(),.new_request_permit(),.fault(),
  .exec_req_v(exec_req_v),.exec_req_r(n_req_r),.exec_req(exec_req),
  .provider_req_v(n_req_v),.provider_req_r(provider_req_r),.provider_req(),
  .provider_rsp_v(provider_rsp_v),.provider_rsp_r(),.provider_rsp(provider_rsp),
  .exec_rsp_v(),.exec_rsp_r(exec_rsp_r),.exec_rsp(),
  .held_job(32'd0),.held_gen(4'd0),.held_token(17'd0),.held_pos(20'd0),.owner_frame(),
  .held_selected_pc(32'd0),.selected_pc(),
  .exec_done(1'b0),.exec_fault(1'b0),.retired_original_ops(4'd0),
  .caller_exec_done(),.caller_exec_fault(),.caller_retired_original_ops());
 // REF provider boundary: legacy equations on CP outputs `c` (REF delayed by
 // the pin latency in REPLAY=0; the DUT pins in REPLAY=1) and the live datapath.
 function automatic [1+1+337+1+1+273+73+32+1+1+4+1+1+1-1:0] ref_prov(input [117:0] c,input lg);
  reg pm;begin
   pm=c[1]&&lg;
   ref_prov={exec_req_v&&pm,provider_req_r&&pm,exec_req,provider_rsp_v,exec_rsp_r,provider_rsp,
    {c[22:3],c[39:23],c[43:40],c[75:44]},c[107:76],exec_done,exec_fault,retired,c[2],pm,c[0]};
  end
 endfunction
 localparam integer PW_=1+1+337+1+1+273+73+32+1+1+4+1+1+1;
 wire [PW_-1:0] dut_prov={p_req_v,p_exec_req_r,p_req,p_exec_rsp_v,p_rsp_r,p_exec_rsp,p_frame,p_pc,p_cd,p_cf,p_cr,p_eo,p_pm,p_fa};
 wire [117:0] cref=REPLAY?out1:out0_d;
 wire [PW_-1:0] ref_prov_w=ref_prov(cref,lease_granted);
 wire [PW_-1:0] lat2_prov_w=ref_prov(out0,lease_granted);
 integer pchecks=0,pmism=0,pfirst=-1,lat2_mism=0,unsafe=0,unsafe_ng=0,fires=0,fires_ng=0,rsp_fires=0,guard_blocks=0,req_cycles=0,core_stale=0;
 always @(posedge clk)if(por_n&&since_reset>=6)begin
  pchecks<=pchecks+1;
  if(dut_prov!==ref_prov_w)begin pmism<=pmism+1;if(pfirst<0)begin pfirst<=cyc;$display("PMISMATCH cyc=%0d diff=%h",cyc,dut_prov^ref_prov_w);end end
  if(!REPLAY&&dut_prov!==lat2_prov_w)lat2_mism<=lat2_mism+1;
  if(exec_req_v)req_cycles<=req_cycles+1;
  if(p_req_v&&provider_req_r)begin fires<=fires+1;if(!lease_granted)unsafe<=unsafe+1;if(!dut1.c_new_request_permit)core_stale<=core_stale+1;end
  if(n_req_v&&provider_req_r)begin fires_ng<=fires_ng+1;if(!lease_granted)unsafe_ng<=unsafe_ng+1;end
  if(n_req_v&&!p_req_v)guard_blocks<=guard_blocks+1;
  if(provider_rsp_v&&p_rsp_r)rsp_fires<=rsp_fires+1;
 end
 // provider datapath stimulus: the executor issues while its owned input (the
 // CP exec_owned pin it sees) is high, plus rare stray requests.
 integer kk;
 always @(negedge clk)if(por_n)begin
  exec_req_v=(o_exec_owned&&($signed($urandom)%3)!=0)||(($signed($urandom)%200)==0);
  for(kk=0;kk<11;kk=kk+1)exec_req[kk*32+:32]=$urandom;
  provider_req_r=($signed($urandom)%4)!=0;
  provider_rsp_v=($signed($urandom)%3)==0;exec_rsp_r=($signed($urandom)%4)!=0;
  for(kk=0;kk<9;kk=kk+1)provider_rsp[kk*32+:32]=$urandom;
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
  $display("PROVIDER REPLAY=%0d checks=%0d mismatches=%0d first=%0d req_cycles=%0d fires=%0d rsp_fires=%0d unsafe=%0d guard_blocks=%0d core_stale=%0d | NEGCTL NG fires=%0d unsafe=%0d | NEGCTL LAT2 mismatches=%0d",
   REPLAY,pchecks,pmism,pfirst,req_cycles,fires,rsp_fires,unsafe,guard_blocks,core_stale,fires_ng,unsafe_ng,lat2_mism);
  if(mism==0&&pmism==0&&unsafe==0&&(REPLAY||checks>0)&&pchecks>0&&fires>1000&&rsp_fires>1000&&n_done>100&&n_release_accept>100&&n_fault_cycles>100)$display("PASS");else $display("FAIL");
  if(unsafe_ng>0)$display("NEGCTL_NG FAIL (expected: request without live grant)");else $display("NEGCTL_NG PASS (unexpected)");
  if(!REPLAY)begin if(lat2_mism>0)$display("NEGCTL_LAT2 FAIL (expected: wrong pin latency caught)");else $display("NEGCTL_LAT2 PASS (unexpected)");end
  $finish;
 end
endmodule
