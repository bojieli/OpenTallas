`timescale 1ns/1ps
// Closed loop: CP context <-> the real shared owner ot_hbm_integrated_sm0_borrow
// (SU = borrower 1, a W2-like competing borrower 2), a protected-request
// executor, a memory responder and a cmdproc-like front end. cdc_drained
// toggles, so release_r is not monotone (exercises the release handshake).
// FAULTS=0: every launch must end in exactly one CP done carrying its frame,
// with no CP, association or shared-owner fault, and bounded latency.
// FAULTS=1: sticky shared faults, executor faults and CP rail upsets are
// injected; each must produce a CP fault within FAULT_BOUND edges, and no CP
// done may follow a CP fault before the next reset.
module tb_cp_pin_margin_loop;
 parameter integer PIN=0,REPLAY=0,FAULTS=0,SEED=1,NTX=3000,FAULT_BOUND=3;
 reg clk=0;always #5 clk=~clk;
 reg por_n=0;
 integer seed;
 // front end
 reg [1:0] launch_v=0;reg [31:0] launch_pc=32'h80000004,cp_job=0;reg [3:0] cp_gen=0;
 reg [16:0] launch_token=0;reg [19:0] launch_pos=0;
 // CP pins
 wire [1:0] native_launch;wire lease_v,release_v,owned,pending,quiet,selected,done,fault;
 wire [31:0] selected_pc,held_job;wire [3:0] held_gen;wire [16:0] held_token;wire [19:0] held_pos;
 wire exec_owned,new_request_permit,association_fault;
 reg exec_done=0;reg [3:0] retired=4;
 reg inj_shared=0,inj_exec=0;wire exec_fault=inj_exec;
 wire arb_fault;
 wire shared_fault=arb_fault||inj_shared;
 wire [2:0] grants,releases;
 ot_hbm_integrated_su_cp_context #(.ENABLE(1),.SU_ENABLE(1),.SU_REGISTERED_OUTPUTS(1),.SU_REGISTERED_STATUS(1),.SU_REGISTERED_BOUNDARY(1),.SU_BALANCED_OWNER_BOUNDARY(1),.SU_FOUR_COMBINATIONAL_CUTS(1),.SU_FAST_OWNER_FRONTIER(1),.SU_PARALLEL_PHASE_VALIDATION(1),.SU_CONTROL_TAIL_CUT(1),.SU_OWNER_VETO_POLARITY(1),
  .SU_PIN_MARGIN(PIN),.SU_RELEASE_REPLAY(REPLAY)) cp(
  .clk(clk),.por_n(por_n),.launch_v(launch_v),.launch_pc(launch_pc),.cp_job(cp_job),.cp_gen(cp_gen),.launch_token(launch_token),.launch_pos(launch_pos),
  .native_launch(native_launch),.lease_v(lease_v),.lease_granted(grants[1]),.release_v(release_v),.release_r(releases[1]),
  .exec_done(exec_done),.exec_fault(exec_fault),.retired_original_ops(retired),.shared_fault(shared_fault),
  .owned(owned),.pending(pending),.quiet(quiet),.selected(selected),.done(done),.fault(fault),
  .selected_pc(selected_pc),.held_job(held_job),.held_gen(held_gen),.held_token(held_token),.held_pos(held_pos),
  .exec_owned(exec_owned),.new_request_permit(new_request_permit),.association_fault(association_fault));
 // W2-like borrower 2
 reg w2_lease=0,w2_owns=0,w2_rel=0;reg [31:0] w2_job=32'h5a5a0001;integer w2_hold=0;
 // executor (SU requests on route 2)
 reg ex_want=0;integer ex_left=0,ex_wait=0,ex_req=0,ex_rsp=0;reg ex_busy=0,ex_out=0;
 wire [3:0] req_rdy,rsp_v;wire [63:0] rsp_tag;wire [3:0] rsp_we;wire [1023:0] rsp_data;
 wire su_req_v=ex_want&&new_request_permit;
 // memory responder
 wire m_req_v,m_req_we;wire [31:0] m_req_addr,m_req_wstrb;wire [255:0] m_req_wdata;wire [15:0] m_req_tag;
 reg m_req_rdy=0,m_rsp_v=0,m_rsp_we=0;reg [15:0] m_rsp_tag=0;wire m_rsp_rdy;integer m_delay=0;reg m_pending=0;
 reg cdc_drained=1;
 wire idle,native_credit_empty;wire [3:0] response_authorized;
 ot_hbm_integrated_sm0_borrow #(.ENABLE(1)) arb(.clk(clk),.por_n(por_n),
  .native_clients_drained(1'b1),.cdc_drained(cdc_drained),
  .observe_req(4'b0),.observe_rsp(4'b0),.observe_req_we(4'b0),.observe_rsp_we(4'b0),.observe_req_tag(64'b0),.observe_rsp_tag(64'b0),
  .return_offer(4'b0),.response_authorized(response_authorized),
  .native_job(32'b0),.native_gen(4'b0),.native_token(17'b0),.native_pos(20'b0),.native_credit_empty(native_credit_empty),
  .lease_v({w2_lease,lease_v,1'b0}),.borrower_quiet({!w2_owns,quiet,1'b1}),
  .lease_job({w2_job,held_job,32'b0}),.lease_gen({4'd3,held_gen,4'b0}),.lease_token({17'd7,held_token,17'b0}),.lease_pos({20'd9,held_pos,20'b0}),
  .lease_granted(grants),
  .release_v({w2_rel,release_v,1'b0}),.release_r(releases),
  .release_job({w2_job,held_job,32'b0}),.release_gen({4'd3,held_gen,4'b0}),.release_token({17'd7,held_token,17'b0}),.release_pos({20'd9,held_pos,20'b0}),
  .req_v({1'b0,su_req_v,2'b0}),.req_rdy(req_rdy),.req_we({1'b0,1'b1,2'b0}),
  .req_addr({32'b0,32'h1000+ex_req,64'b0}),.req_wdata({256'b0,{8{32'hc0de0000+ex_req}},512'b0}),.req_wstrb({32'b0,32'hffffffff,64'b0}),.req_tag({16'b0,16'(ex_req),32'b0}),
  .rsp_v(rsp_v),.rsp_rdy({1'b0,1'b1,2'b0}),.rsp_we(rsp_we),.rsp_tag(rsp_tag),.rsp_data(rsp_data),
  .m_req_v(m_req_v),.m_req_rdy(m_req_rdy),.m_req_we(m_req_we),.m_req_addr(m_req_addr),.m_req_wdata(m_req_wdata),.m_req_wstrb(m_req_wstrb),.m_req_tag(m_req_tag),
  .m_rsp_v(m_rsp_v),.m_rsp_rdy(m_rsp_rdy),.m_rsp_we(m_rsp_we),.m_rsp_tag(m_rsp_tag),.m_rsp_data(256'b0),
  .idle(idle),.fault(arb_fault));
 // --- bookkeeping
 integer tx=0,n_done=0,n_bad_frame=0,n_cp_fault=0,n_arb_fault=0,n_assoc_fault=0,n_timeout=0,n_w2=0,n_req=0,n_rsp=0,n_inj=0,n_inj_detected=0,n_late=0,n_done_after_fault=0,n_rel_toggle=0;
 integer tx_start=0,cyc=0,phase=0,gap=0,inj_at=-1,fault_seen_at=-1,max_tx=0;
 reg [31:0] e_job;reg [3:0] e_gen;reg [16:0] e_tok;reg [19:0] e_pos;
 reg fault_latched=0;
 always @(posedge clk)cyc<=cyc+1;
 // memory responder: accept, then answer after a few edges with the same tag
 always @(posedge clk or negedge por_n)if(!por_n)begin m_req_rdy<=0;m_rsp_v<=0;m_pending<=0;end else begin
  m_req_rdy<=!m_pending&&($random(seed)%3!=0);
  if(m_req_v&&m_req_rdy&&!m_pending)begin m_pending<=1;m_delay<=($random(seed)&3);m_rsp_tag<=m_req_tag;m_rsp_we<=m_req_we;end
  else if(m_pending&&!m_rsp_v)begin if(m_delay==0)m_rsp_v<=1;else m_delay<=m_delay-1;end
  else if(m_rsp_v&&m_rsp_rdy)begin m_rsp_v<=0;m_pending<=0;end
 end
 // executor
 always @(posedge clk or negedge por_n)if(!por_n)begin ex_want<=0;ex_busy<=0;ex_out<=0;exec_done<=0;retired<=4;ex_left<=0;end else begin
  if(!ex_busy&&!exec_done&&exec_owned)begin ex_busy<=1;ex_left<=($random(seed)&3);ex_wait<=($random(seed)&3);end
  else if(ex_busy)begin
   if(ex_want&&su_req_v&&req_rdy[2])begin ex_want<=0;ex_out<=1;n_req<=n_req+1;ex_req<=ex_req+1;end
   else if(ex_out&&rsp_v[2])begin ex_out<=0;n_rsp<=n_rsp+1;ex_left<=ex_left-1;end
   else if(!ex_want&&!ex_out)begin
    if(ex_wait>0)ex_wait<=ex_wait-1;
    else if(ex_left>0)ex_want<=1;
    else begin ex_busy<=0;exec_done<=1;retired<=4;end
   end
  end else if(exec_done&&!exec_owned&&!grants[1])exec_done<=0;
 end
 // W2 borrower: lease, hold, release with its own tuple
 always @(posedge clk or negedge por_n)if(!por_n)begin w2_lease<=0;w2_owns<=0;w2_rel<=0;end else begin
  if(!w2_owns&&!w2_lease&&($random(seed)%200)==0)w2_lease<=1;
  if(w2_lease&&grants[2])begin w2_lease<=0;w2_owns<=1;w2_hold<=($random(seed)&15);n_w2<=n_w2+1;end
  if(w2_owns&&!w2_rel)begin if(w2_hold>0)w2_hold<=w2_hold-1;else w2_rel<=1;end
  if(w2_rel&&releases[2])begin w2_rel<=0;w2_owns<=0;end
 end
 // cdc drain toggles (release_r and grant safety are non-monotone)
 always @(posedge clk)cdc_drained<=($random(seed)%4)!=0;
 always @(posedge clk)if(release_v&&!releases[1]&&grants[1])n_rel_toggle<=n_rel_toggle+1;
 // front end: one launch pulse per transaction, frame held until done/fault
 always @(posedge clk)begin
  launch_v<=0;
  if(!por_n)begin phase<=0;gap<=3;end
  else case(phase)
   0:if(gap>0)gap<=gap-1;else if(tx<NTX)begin
      cp_job<=$random(seed);cp_gen<=$random(seed);launch_token<=$random(seed);launch_pos<=$random(seed);
      launch_pc<=($random(seed)&1)?32'h80000004:32'hc0000004;phase<=1;end
   1:begin launch_v<=2'b01;tx<=tx+1;tx_start<=cyc;phase<=2;e_job<=cp_job;e_gen<=cp_gen;e_tok<=launch_token;e_pos<=launch_pos;end
   2:begin
     if(done)begin
      if(fault_latched)n_done_after_fault<=n_done_after_fault+1;
      n_done<=n_done+1;
      if(held_job!==e_job||held_gen!==e_gen||held_token!==e_tok||held_pos!==e_pos)n_bad_frame<=n_bad_frame+1;
      if(cyc-tx_start>max_tx)max_tx<=cyc-tx_start;
      phase<=0;gap<=($random(seed)&7);
     end else if(cyc-tx_start>4000)begin n_timeout<=n_timeout+1;phase<=3;end
    end
   3:;
  endcase
 end
 // monitors
 always @(posedge clk)if(!por_n)fault_latched<=0;else begin
  if(fault&&!fault_latched)begin fault_latched<=1;n_cp_fault<=n_cp_fault+1;
   if(inj_at>=0)begin n_inj_detected<=n_inj_detected+1;if(cyc-inj_at>FAULT_BOUND)n_late<=n_late+1;end end
  if(arb_fault)n_arb_fault<=n_arb_fault+1;
  if(association_fault)n_assoc_fault<=n_assoc_fault+1;
 end
 // fault injection and recovery (FAULTS=1); non-fault runs reset only on a failure
 integer settle=0;
 always @(negedge clk)begin
  if(!por_n)begin settle=0;por_n=1;end
  else begin
   settle=settle+1;
   if(FAULTS&&inj_at<0&&settle>20&&phase==2&&($random(seed)%300)==0)begin : inj
    integer k;k=$random(seed)%4;if(k<0)k=-k;
    inj_at=cyc;n_inj=n_inj+1;
    case(k)
     0:inj_shared=1;
     1:if(grants[1])inj_exec=1;else inj_shared=1;
     2:cp.u_su_cp.on.phase_n[3]=~cp.u_su_cp.on.phase_n[3];
     3:cp.u_su_cp.on.registered_status.status_q[2]=~cp.u_su_cp.on.registered_status.status_q[2];
    endcase
   end
   if((fault_latched&&($random(seed)%32)==0)||(FAULTS&&phase==3)||(inj_at>=0&&cyc-inj_at>200))begin
    por_n=0;inj_shared=0;inj_exec=0;inj_at=-1;
   end
  end
 end
 initial begin
  seed=SEED;
  repeat(3)@(posedge clk);por_n=1;
  wait(tx>=NTX&&phase==0);
  repeat(20)@(posedge clk);
  $display("LOOP PIN=%0d REPLAY=%0d FAULTS=%0d tx=%0d done=%0d bad_frame=%0d cp_fault=%0d arb_fault_cycles=%0d assoc_fault_cycles=%0d timeouts=%0d w2_leases=%0d req=%0d rsp=%0d release_r_low_while_v=%0d max_tx_cycles=%0d injected=%0d detected=%0d late=%0d done_after_fault=%0d",
   PIN,REPLAY,FAULTS,tx,n_done,n_bad_frame,n_cp_fault,n_arb_fault,n_assoc_fault,n_timeout,n_w2,n_req,n_rsp,n_rel_toggle,max_tx,n_inj,n_inj_detected,n_late,n_done_after_fault);
  if(!FAULTS&&n_done==NTX&&n_bad_frame==0&&n_cp_fault==0&&n_arb_fault==0&&n_assoc_fault==0&&n_timeout==0&&n_req==n_rsp&&n_rel_toggle>0&&n_w2>0)$display("PASS");
  else if(FAULTS&&n_inj>50&&n_inj_detected==n_inj&&n_late==0&&n_done_after_fault==0&&n_bad_frame==0)$display("PASS");
  else $display("FAIL");
  $finish;
 end
 initial begin #(64'd50000000);$display("LOOP HANG tx=%0d done=%0d",tx,n_done);$display("FAIL");$finish;end
endmodule
