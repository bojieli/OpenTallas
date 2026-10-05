`timescale 1ns/1ps
module tb_su_cp_registered_status;
 reg clk=0;always #5 clk=~clk;
 reg por_n=0;reg[1:0] launch_v=0;reg[31:0] launch_pc=0,cp_job=0;
 reg[3:0] cp_gen=0;reg[16:0] launch_token=0;reg[19:0] launch_pos=0;
 reg lease_granted=0,release_r=0,exec_done=0,exec_fault=0,shared_fault=0;
 reg[3:0] retired_original_ops=0;
 wire[1:0] native_launch;wire lease_v,release_v,owned,pending,quiet,selected,done,fault;
 wire[31:0] selected_pc,held_job;wire[3:0] held_gen;
 wire[16:0] held_token;wire[19:0] held_pos;
 integer checks=0;
 integer inject_word=-1,inject_bit=0,cp_cpl_count=0,accepted_release_count=0;
 reg [6:0] saved_q,saved_n;
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
 ot_hbm_integrated_su_cp_bind #(.ENABLE(1),.REGISTERED_OUTPUTS(1),.REGISTERED_STATUS(1)) dut(.*);
 wire[1:0] off_native;wire off_done,off_fault;
 ot_hbm_integrated_su_cp_bind #(.ENABLE(0),.REGISTERED_OUTPUTS(1),.REGISTERED_STATUS(1)) baseline(
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
  tick();drive();launch_v=0;#1;
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
  ck(held_job==cp_job&&held_gen==cp_gen&&held_token==launch_token&&held_pos==launch_pos&&selected_pc==pc,"full immutable CP frame");
 end endtask
 task granted;
 begin drive();lease_granted=1;tick();ck(owned&&!pending&&!done&&!release_v,"accepted grant before execution");end
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
  $display("PASS su_cp_registered_status checks=%0d CPL=%0d",checks,cp_cpl_count);$finish;
 end
 initial begin #1000000;$fatal(1,"TIMEOUT su_cp_release");end
endmodule
