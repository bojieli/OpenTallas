`timescale 1ns/1ps
module tb_su_cp_grouped_owner #(parameter integer BALANCED_OWNER_BOUNDARY_TEST=0,FOUR_COMBINATIONAL_CUTS_TEST=0,FAST_OWNER_FRONTIER_TEST=0,PARALLEL_PHASE_VALIDATION_TEST=0,CONTROL_TAIL_CUT_TEST=0);
 reg clk=0;always #5 clk=~clk;
 reg por_n=0;reg[1:0] launch_v=0;reg[31:0] launch_pc=0,cp_job=0;
 reg[3:0] cp_gen=0;reg[16:0] launch_token=0;reg[19:0] launch_pos=0;
 reg lease_granted=0,release_r=0,exec_done=0,exec_fault=0,shared_fault=0;
 reg[3:0] retired_original_ops=0;
 wire [11:0] owned_frontier_terms;
 wire[1:0] native_launch;wire lease_v,release_v,owned,pending,quiet,selected,done,fault;
 wire[31:0] selected_pc,held_job;wire[3:0] held_gen;
 wire[16:0] held_token;wire[19:0] held_pos;
 integer checks=0;
 reg [63:0] codec_probe_data=0;wire [71:0] codec_probe_code;
 reg [31:0] entry_probe_pc=0;wire entry_probe;
 integer codec_basis_checks=0,entry_basis_checks=0;
 ot_hbm_cp_four_encode codec_probe(.data(codec_probe_data),.code(codec_probe_code));
 if(FAST_OWNER_FRONTIER_TEST)begin:fast_entry_probe
  ot_hbm_cp_frontier_entry entry_probe_dut(.pc(entry_probe_pc),.entry(entry_probe));
 end else begin:prior_entry_probe
  ot_hbm_cp_four_entry entry_probe_dut(.pc(entry_probe_pc),.entry(entry_probe));
 end
 reg [17:0] phase_probe=0;wire phase_probe_valid;
 integer phase_truth_checks=0;
 ot_hbm_cp_parallel_phase phase_probe_dut(.q(phase_probe[8:0]),.n(phase_probe[17:9]),.valid(phase_probe_valid));
 reg [11:0] tail_probe=0;wire tail_probe_result;
 integer tail_truth_checks=0,tail_unknown_checks=0;
 ot_hbm_cp_frontier_and12 #(.FAST(1),.RETAINED_TAIL(1)) tail_probe_dut(
  .bits(tail_probe),.result(tail_probe_result));
 task check_four_cut_oracles;
 begin
  if(CONTROL_TAIL_CUT_TEST)begin
   for(integer bits=0;bits<4096;bits=bits+1)begin
    tail_probe=bits;#1;
    if(tail_probe_result!==(&tail_probe))$fatal(1,"exact complete12factor tail %h",tail_probe);
    tail_truth_checks=tail_truth_checks+1;
   end
   for(integer k=0;k<12;k=k+1)begin
    tail_probe=12'hfff;tail_probe[k]=1'bx;#1;
    if(tail_probe_result!==1'bx)$fatal(1,"unmasked unknown tail factor%0d",k);
    tail_probe=0;tail_probe[k]=1'bx;#1;
    if(tail_probe_result!==0)$fatal(1,"masked unknown tail factor%0d",k);
    tail_unknown_checks=tail_unknown_checks+2;
   end
   $display("PASS control_tail complete_words=%0d unknown_cases=%0d",tail_truth_checks,tail_unknown_checks);
  end
  if(PARALLEL_PHASE_VALIDATION_TEST&&!CONTROL_TAIL_CUT_TEST)begin
   for(integer bits=0;bits<262144;bits=bits+1)begin
    phase_probe=bits;#1;
    if(phase_probe_valid!==((phase_probe[17:9]==~phase_probe[8:0]) &&
       (phase_probe[8:0]!=0) && ((phase_probe[8:0]&(phase_probe[8:0]-9'd1))==0)))
     $fatal(1,"complete protected18bit phase oracle %h",phase_probe);
    phase_truth_checks=phase_truth_checks+1;
   end
   $display("PASS parallel_phase complete_words=%0d",phase_truth_checks);
  end
  if(FOUR_COMBINATIONAL_CUTS_TEST)begin
   // Zero+allones+64 basis vectors establish the unchanged linear72bit codec.
   for(integer k=0;k<66;k=k+1)begin
    codec_probe_data=(k==64)?64'd0:(k==65)?~64'd0:(64'd1<<k);#1;
    if(codec_probe_code!==ot_gpu_w6_secded_pkg::encode64(codec_probe_data))$fatal(1,"exact72bit SECDED encoder basis%0d",k);
    codec_basis_checks=codec_basis_checks+1;
   end
   for(integer mode=0;mode<2;mode=mode+1)begin
    for(integer k=0;k<33;k=k+1)begin
     entry_probe_pc=(mode?32'hc0000004:32'h80000004)^((k==32)?32'd0:(32'd1<<k));#1;
     if(entry_probe!==((entry_probe_pc==32'h80000004)||(entry_probe_pc==32'hc0000004)))$fatal(1,"exact entry PC mode%0d bit%0d",mode,k);
     entry_basis_checks=entry_basis_checks+1;
    end
   end
  end
 end endtask

 integer inject_word=-1,inject_bit=0,cp_cpl_count=0,accepted_release_count=0;
 reg [6:0] saved_q,saved_n;
 reg [8:0] saved_phase_q,saved_phase_n;
 reg [17:0] phase_mask;
 integer phase_cases=0,phase_mismatch=0,phase_zero=0,phase_multiple=0;
 time launch_capture_time;
 reg cp_reset_req=0,cp_cmd_we=0,cp_db_v=0,cp_cpl_ready=0;
 wire cp_reset_n,cp_reset_ack,cp_block_new,cp_reset_fault,cp_idle,cp_cpl_v;
 wire [31:0] cp_record_job;wire [3:0] cp_record_gen;wire [19:0] cp_record_pos;
 wire routes_drained=quiet&&!selected&&!lease_granted&&!exec_done&&!release_v;
 ot_hbm_integrated_cp_reset #(.ENABLE(1)) reset_hook(
 .clk(clk),.por_n(por_n),.reset_req(cp_reset_req),.cp_idle(cp_idle),
 .routes_drained(routes_drained),.cp_reset_n(cp_reset_n),.reset_ack(cp_reset_ack),
 .block_new(cp_block_new),.fault(cp_reset_fault));
 ot_ds_hbm_cmdproc20 #(.ENABLE(1)) cp(
 .clk(clk),.rst_n(cp_reset_n),.cmd_we(cp_cmd_we&&!cp_block_new),
 .cmd_addr(8'd0),.cmd_wdata(64'h2000000000000000),
 .db_v(cp_db_v&&cp_idle&&routes_drained&&!cp_block_new),.db_rdy(cp_idle),
 .db_token(launch_token),.db_pos(launch_pos),.db_job(cp_job),.db_generation(cp_gen),
 .cpl_position(cp_record_pos),.cpl_job(cp_record_job),.cpl_generation(cp_record_gen),
 .sm_done(2'b00),.sm_fault(2'b00),.res_v(2'b00),.res_data(64'd0),
 .cpl_v(cp_cpl_v),.cpl_rdy(cp_cpl_ready&&routes_drained));
 always @(posedge clk)begin
 if(!por_n)begin cp_cpl_count=0;accepted_release_count=0;end
 else if(release_v&&release_r)begin
 if(fault||cp_job!=held_job||cp_gen!=held_gen||launch_token!=held_token||launch_pos!=held_pos||launch_pc!=selected_pc||retired_original_ops!=4||!lease_granted||!exec_done)
 $fatal(1,"accepted release lacked live full owner or actual completion");
 accepted_release_count=accepted_release_count+1;
 end
 else if(cp_cpl_v&&cp_cpl_ready&&routes_drained)begin
 if(cp_record_job!=cp_job||cp_record_gen!=cp_gen||cp_record_pos!=launch_pos)
 $fatal(1,"accepted CPL changed original tuple");
 cp_cpl_count=cp_cpl_count+1;
 end
 end
 ot_hbm_integrated_su_cp_bind #(.ENABLE(1),.REGISTERED_OUTPUTS(1),.REGISTERED_STATUS(1),.REGISTERED_BOUNDARY(1),.GROUPED_OWNER_BOUNDARY(!BALANCED_OWNER_BOUNDARY_TEST),.BALANCED_OWNER_BOUNDARY(BALANCED_OWNER_BOUNDARY_TEST),.FOUR_COMBINATIONAL_CUTS(FOUR_COMBINATIONAL_CUTS_TEST),.FAST_OWNER_FRONTIER(FAST_OWNER_FRONTIER_TEST),.PARALLEL_PHASE_VALIDATION(PARALLEL_PHASE_VALIDATION_TEST),.CONTROL_TAIL_CUT(CONTROL_TAIL_CUT_TEST)) dut(.*);
 wire[1:0] off_native;wire off_done,off_fault;
 ot_hbm_integrated_su_cp_bind #(.ENABLE(0),.REGISTERED_OUTPUTS(1),.REGISTERED_STATUS(1),.REGISTERED_BOUNDARY(1),.GROUPED_OWNER_BOUNDARY(!BALANCED_OWNER_BOUNDARY_TEST),.BALANCED_OWNER_BOUNDARY(BALANCED_OWNER_BOUNDARY_TEST),.FOUR_COMBINATIONAL_CUTS(FOUR_COMBINATIONAL_CUTS_TEST),.FAST_OWNER_FRONTIER(FAST_OWNER_FRONTIER_TEST),.PARALLEL_PHASE_VALIDATION(PARALLEL_PHASE_VALIDATION_TEST),.CONTROL_TAIL_CUT(CONTROL_TAIL_CUT_TEST)) baseline(
 .clk(clk),.por_n(por_n),.launch_v(launch_v),.launch_pc(launch_pc),.cp_job(cp_job),.cp_gen(cp_gen),
 .launch_token(launch_token),.launch_pos(launch_pos),.lease_granted(lease_granted),
 .release_r(release_r),.exec_done(exec_done),.exec_fault(exec_fault),
 .retired_original_ops(retired_original_ops),.shared_fault(shared_fault),
 .native_launch(off_native),.done(off_done),.fault(off_fault));
 task tick;begin @(posedge clk);#1;end endtask
 task drive;begin @(negedge clk);end endtask
 task ck(input reg good,input string what);begin
  checks=checks+1;if(!good)$fatal(1,"CHECK %0d: %s",checks,what);
 end endtask
 task reset;
 begin
  drive();por_n=0;launch_v=0;lease_granted=0;release_r=0;
  exec_done=0;exec_fault=0;shared_fault=0;retired_original_ops=0;
  cp_reset_req=0;cp_cmd_we=0;cp_db_v=0;cp_cpl_ready=0;inject_word=-1;
  cp_job=32'h10203040;cp_gen=4'h3;launch_token=17'h12345;launch_pos=20'habcde;
  repeat(2)tick();drive();por_n=1;tick();ck(!fault&&!done&&!pending,"reset starts empty");
 end endtask
 task launch(input reg[31:0] pc);
 begin
  drive();launch_pc=pc;launch_v=1;#1;ck(native_launch==0,"selected native lane intercepted");
  ck(off_native==1&&!off_done&&!off_fault,"ENABLE0 native passthrough");
  tick();launch_capture_time=$time;drive();launch_v=0;#1;
  ck(!pending&&!lease_v&&!done,"E0 protected header cannot dispatch");
  case(inject_word)
   0:dut.on.pc_code=dut.on.pc_code^(72'b1<<inject_bit);
   1:dut.on.frame_lo=dut.on.frame_lo^(72'b1<<inject_bit);
   2:dut.on.frame_hi=dut.on.frame_hi^(72'b1<<inject_bit);
  endcase
  tick();ck(!pending&&!lease_v&&!done,"E1 syndrome capture cannot dispatch");
  tick();ck(!pending&&!lease_v&&!done,"E2 corrected header still requires validation");
  tick();ck(!pending&&!lease_v&&!done,"E3 owner checks cannot dispatch");
  tick();ck(!pending&&!lease_v&&!done,"E4 protected PENDING still requires registered permit");
  tick();
  ck(pending&&lease_v&&!done,"actual high-PC waits for shared lease");
  ck($time-launch_capture_time==50,"unchanged E0->E5 first lease, zero added boundary edges");
  ck(held_job==cp_job&&held_gen==cp_gen&&held_token==launch_token&&held_pos==launch_pos&&selected_pc==pc,"full immutable CP frame");
 end endtask
 task granted;
 begin drive();lease_granted=1;tick();ck(owned&&!pending&&!done&&!release_v,"accepted grant before execution");end
 endtask
 // Fault injection uses the same held-owner transaction, never a fabricated ACK.
 task phase_fault_case(input integer at_release,input integer bit_a,input integer bit_b);
 begin
  reset();launch(32'h80000004);granted();
  if(at_release)begin
   drive();retired_original_ops=4;exec_done=1;tick();
   ck(release_v&&!done,"real completion reaches held release boundary before injection");
  end
  drive();release_r=1;
  saved_phase_q=dut.on.phase_q;saved_phase_n=dut.on.phase_n;
  phase_mask=18'b1<<bit_a;
  if(bit_b>=0)phase_mask=phase_mask^(18'b1<<bit_b);
  dut.on.phase_q=saved_phase_q^phase_mask[8:0];
  dut.on.phase_n=saved_phase_n^phase_mask[17:9];
  #1;
  ck(dut.on.phase_bad,"every one/two-rail corruption fails protected one-hot validity");
  if(dut.on.phase_rails_bad)phase_mismatch=phase_mismatch+1;
  else if(dut.on.phase==0)phase_zero=phase_zero+1;
  else phase_multiple=phase_multiple+1;
  ck(fault&&!lease_v&&!release_v&&!owned&&!done&&!quiet&&selected,
   "phase error denies all positive permits, keeps held transaction selected");
  tick();ck(fault&&lease_granted&&accepted_release_count==0&&!done,
   "phase-corrupted ready edge never retires accepted owner debt");
  drive();dut.on.phase_q=saved_phase_q;dut.on.phase_n=saved_phase_n;
  tick();ck(fault&&!done&&!release_v&&!lease_v&&lease_granted&&accepted_release_count==0,
   "phase fault quarantine persists after restoring rails; only POR resets it");
  phase_cases=phase_cases+1;
 end
 endtask
 task good_case(input reg[31:0] pc);
 begin
  reset();launch(pc);
  repeat(4)begin tick();ck(pending&&!done&&lease_v,"grant stall preserves context");end
  granted();
  drive();retired_original_ops=3;tick();ck(!done&&!release_v,"three retired operations do not publish CP done");
  drive();retired_original_ops=4;exec_done=1;tick();ck(release_v&&!done,"executor done requests release but no CP done");
  repeat(5)begin tick();ck(release_v&&!done&&owned,"release backpressure retains lease and CP frame");end
  drive();release_r=1;tick();ck(!done,"release acceptance alone is not cleanup");
  drive();release_r=0;repeat(3)begin tick();ck(!done,"executor/grant must actually clean up");end
  drive();lease_granted=0;tick();ck(!done,"executor held done prevents premature cleanup");
  drive();exec_done=0;tick();ck(done&&!fault,"actual release plus cleanup publishes one CP done");
  tick();ck(!done&&!pending&&!fault&&!quiet&&selected,"one-edge done precedes status rearm");
  tick();ck(quiet&&!selected&&!done&&!pending&&!fault,"extra registered drain edge rearms source");
 end endtask
 initial begin
  check_four_cut_oracles();
  good_case(32'h80000004);good_case(32'hc0000004);
  reset();drive();launch_pc=12;launch_v=2;#1;
  ck(native_launch==2&&off_native==2,"ordinary CP launch retained");
  tick();ck(!pending&&!done&&!fault,"ordinary CP not treated as SU job");
  reset();launch(32'h80000004);drive();cp_gen=4;tick();
  ck(fault&&!done&&!lease_v,"foreign generation cannot acquire or complete");
  reset();launch(32'h80000004);granted();drive();retired_original_ops=3;exec_done=1;tick();
  ck(fault&&!done&&!release_v,"premature executor done is quarantined");
  reset();launch(32'h80000004);granted();drive();lease_granted=0;tick();
  ck(fault&&!done,"lost active grant cannot become done");
  reset();launch(32'h80000004);granted();drive();retired_original_ops=4;exec_done=1;tick();
  drive();shared_fault=1;release_r=1;tick();ck(fault&&!done&&!release_v,"fault suppresses release and done");
  reset();drive();launch_pc=32'h80000004;launch_v=3;tick();
  ck(fault&&!done,"multi-lane SU launch rejected");
  // All three W6 source words, every physical bit: one bit corrects before lease.
  for(integer w=0;w<3;w=w+1)for(integer b=0;b<72;b=b+1)begin
   reset();inject_word=w;inject_bit=b;launch(32'h80000004);
   ck(!fault&&pending&&lease_v,"single-bit checked header corrected before lease");
  end
  // PREDECODE is non-dispatching; a foreign live tuple must fail its registered validation.
  reset();drive();launch_pc=32'h80000004;launch_v=1;tick();drive();launch_v=0;cp_gen=4;
  repeat(3)begin tick();ck(!lease_v&&!done,"foreign predecode tuple cannot dispatch");end
  ck(fault,"registered validation rejects foreign predecode generation");
  // Double-bit corruption must quarantine before any grant/done.
  for(integer w=0;w<3;w=w+1)begin
   reset();drive();launch_pc=32'h80000004;launch_v=1;tick();drive();launch_v=0;
   case(w)
    0:dut.on.pc_code=dut.on.pc_code^72'd3;
    1:dut.on.frame_lo=dut.on.frame_lo^72'd3;
    2:dut.on.frame_hi=dut.on.frame_hi^72'd3;
   endcase
   repeat(4)begin tick();ck(!lease_v&&!done,"uncorrectable header never dispatches");end
   ck(fault,"uncorrectable header is sticky fault");
  end
  // Each foreign live owner field at an offered release must veto acceptance immediately.
  for(integer f=0;f<5;f=f+1)begin
   reset();launch(32'h80000004);granted();drive();retired_original_ops=4;exec_done=1;tick();
   ck(release_v&&!done,"real completion offers release before foreign owner test");
   drive();release_r=1;
   case(f)
    0:cp_job=cp_job^32'd1;
    1:cp_gen=cp_gen^4'd1;
    2:launch_token=launch_token^17'd1;
    3:launch_pos=launch_pos^20'd1;
    4:launch_pc=launch_pc^32'd1;
   endcase
   #1;ck(fault&&!release_v&&!done,"instant live-owner veto blocks ready release");
   tick();ck(fault&&accepted_release_count==0&&lease_granted,"foreign edge cannot retire held debt");
   drive();cp_job=32'h10203040;cp_gen=4'h3;launch_token=17'h12345;launch_pos=20'habcde;launch_pc=32'h80000004;
   tick();ck(fault&&!release_v&&!done&&accepted_release_count==0,"transient foreign owner remains quarantined");
  end
  // Single-bit faults on either rail cannot create a positive lease/release/done permit.
  for(integer rail=0;rail<2;rail=rail+1)for(integer b=0;b<7;b=b+1)begin
   reset();launch(32'h80000004);granted();drive();release_r=1;
   saved_q=dut.on.registered_status.status_q;saved_n=dut.on.registered_status.status_n;
   if(rail==0)dut.on.registered_status.status_q=saved_q^(7'b1<<b);
   else dut.on.registered_status.status_n=saved_n^(7'b1<<b);
   #1;ck(fault&&!lease_v&&!release_v&&!owned&&!done,"single status-rail error cannot make permit");
   tick();drive();dut.on.registered_status.status_q=saved_q;dut.on.registered_status.status_n=saved_n;
   tick();ck(fault&&!done&&!release_v&&accepted_release_count==0,"status-rail fault remains sticky after restore");
  end
  // Both ACTIVE held-owner and actual held RELEASE boundaries: all18 singles +153 pairs.
  for(integer boundary=0;boundary<2;boundary=boundary+1)begin
   for(integer a=0;a<18;a=a+1)phase_fault_case(boundary,a,-1);
   for(integer a=0;a<18;a=a+1)for(integer b=a+1;b<18;b=b+1)
    phase_fault_case(boundary,a,b);
  end
  ck(phase_cases==342,"exactly18 single plus153 pair faults at each of two boundaries");
  ck(phase_mismatch>0&&phase_zero==2&&phase_multiple>0,
   "fault cases cover rail mismatch, zero and multiple one-hot phase corruption");
  // Genuine completion and registered rearm permits the next high-PC launch without root reset.
  reset();launch(32'h80000004);granted();drive();retired_original_ops=4;exec_done=1;tick();
  drive();release_r=1;tick();drive();release_r=0;lease_granted=0;exec_done=0;tick();
  ck(done&&accepted_release_count==1,"first real release plus cleanup completes exactly once");
  tick();ck(!done&&!quiet,"first done drops before extra drain edge");
  tick();ck(quiet&&!selected,"first context fully rearms before next launch");
  launch(32'hc0000004);granted();drive();retired_original_ops=4;exec_done=1;tick();
  drive();release_r=1;tick();drive();release_r=0;lease_granted=0;exec_done=0;tick();
  ck(done&&accepted_release_count==2&&!fault,"back-to-back second context completes on its own release");
  tick();tick();ck(quiet&&!selected&&!done,"second context drains without reset");
  // Real END/CPL and actual deferred CP reset while the checked borrower holds debt.
  reset();drive();cp_cmd_we=1;tick();drive();cp_cmd_we=0;cp_db_v=1;tick();
  drive();cp_db_v=0;repeat(3)tick();ck(cp_cpl_v&&!cp_idle,"actual END posts held CPL");
  launch(32'h80000004);granted();drive();cp_reset_req=1;cp_cpl_ready=1;
  repeat(4)begin tick();ck(cp_reset_n&&!cp_reset_ack&&cp_block_new&&cp_cpl_count==0,
   "warm reset cannot bypass accepted borrower debt or held CPL");end
  drive();retired_original_ops=4;exec_done=1;tick();
  ck(release_v&&!done,"reset request does not manufacture release");
  drive();release_r=1;tick();drive();release_r=0;
  repeat(3)begin tick();ck(cp_reset_n&&!cp_reset_ack&&cp_cpl_count==0,
   "accepted release alone cannot reset or retire CPL");end
  drive();lease_granted=0;tick();drive();exec_done=0;tick();
  ck(done&&cp_reset_n&&cp_cpl_count==0,"done before real CPL acceptance, root reset intact");
  tick();ck(!done&&!quiet&&selected&&cp_reset_n,"done clears before registered status drain");
  tick();ck(quiet&&!selected&&cp_reset_n&&cp_cpl_count==0,"registered rearm precedes actual CPL");
  tick();ck(cp_cpl_count==1&&cp_idle&&cp_reset_n,"real CPL accepted before local reset");
  tick();ck(!cp_reset_n&&!cp_reset_ack&&por_n,"registered local reset after exact drain");
  tick();ck(cp_reset_n&&cp_reset_ack&&cp_block_new&&!cp_reset_fault&&por_n,
   "held reset ACK preserves root domain");
  repeat(3)begin tick();ck(cp_reset_ack&&cp_cpl_count==1,"reset request cannot repeat CPL");end
  drive();cp_reset_req=0;tick();ck(!cp_reset_ack&&!cp_block_new,"local reset rearms");
  $display("PASS_FOURCUT_ORACLES codec_basis=%0d entry_basis=%0d",codec_basis_checks,entry_basis_checks);
  $display("PASS su_cp_grouped_owner checks=%0d CPL=%0d phase_cases=%0d mismatch=%0d zero=%0d multiple=%0d prelease_edges=5 grant_edges=1 rearm_edges=1",checks,cp_cpl_count,phase_cases,phase_mismatch,phase_zero,phase_multiple);$finish;
 end
 initial begin #1000000;$fatal(1,"TIMEOUT su_cp_release");end
endmodule
