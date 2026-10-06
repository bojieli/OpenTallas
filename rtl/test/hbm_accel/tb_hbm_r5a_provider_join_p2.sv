`timescale 1ps/1fs
// Changed seam only: real Gibbs NP32 coded READ export -> real R5a checker.
// No controller, array, original1024 gate or ordinary88 replay.
module tb_hbm_r5a_provider_join_p2;
 reg clk=0,por_n=0;always #512 clk=~clk;
 reg bind_v=0,frame_valid=0;reg[72:0] frame=0;
 reg[31:0] issue=0,ret=0;reg[95:0] freed=0;
 wire[31:0] ip,rp,empty;wire[511:0] nextord,retord;wire[2335:0] retframe;
 wire drained,provider_fault;
 reg[511:0] callerord=0;reg[8191:0] payload=0;
 reg wrong_frame=0,wrong_issue=0;
 wire[31:0] checked_issue,checked_return;wire[511:0] checked_ord;
 wire[8191:0] checked_data;wire fault;
 integer p,b,accepted=0,delivered=0;
 ot_hbm_pcwb_p2_return_bind #(.ENABLE(1)) provider(
  .clk(clk),.por_n(por_n),.bind_v(bind_v),.bind_frame(frame),
  .issue_v(issue),.return_v(ret),.freed(freed),.issue_permit(ip),.return_permit(rp),
  .next_ordinal(nextord),.return_ordinal(retord),.return_frame(retframe),
  .empty(empty),.drained(drained),.fault(provider_fault));
 ot_hbm_accel_expert_provider_join_p2 #(.ENABLE(1)) dut(
  .service_clk(clk),.por_n(por_n),.held_frame_valid(frame_valid),.held_frame(frame),
  .provider_fault(provider_fault),.provider_issue_v(issue),.provider_return_v(ret),
  .provider_next_ordinal(nextord^(wrong_issue?512'b1:512'b0)),.caller_next_ordinal(callerord),
  .provider_return_ordinal(retord),.provider_return_frame(retframe^(wrong_frame?(2336'b1<<72):2336'b0)),
  .provider_return_data(payload),.issue_v(checked_issue),.rsp_v(checked_return),
  .rsp_ordinal(checked_ord),.rsp_data(checked_data),.fault(fault));
 wire[31:0] off_issue,off_return;wire off_fault;
 ot_hbm_accel_expert_provider_join_p2 disabled(
  .service_clk(clk),.por_n(por_n),.held_frame_valid(frame_valid),.held_frame(frame),
  .provider_fault(provider_fault),.provider_issue_v(issue),.provider_return_v(ret),
  .provider_next_ordinal(nextord),.caller_next_ordinal(callerord),.provider_return_ordinal(retord),
  .provider_return_frame(retframe),.provider_return_data(payload),
  .issue_v(off_issue),.rsp_v(off_return),.rsp_ordinal(),.rsp_data(),.fault(off_fault));
 task tick;begin @(posedge clk);#1;end endtask
 task step;begin @(negedge clk);#1;end endtask
 task cold;
  begin step();por_n=0;bind_v=0;frame_valid=0;issue=0;ret=0;freed=0;
   wrong_frame=0;wrong_issue=0;callerord=0;
   repeat(2)tick();step();por_n=1;tick();end
 endtask
 task enroll(input[72:0] f);
  begin step();frame=f;frame_valid=1;bind_v=1;tick();step();bind_v=0;tick();end
 endtask
 task read_once;
  begin
   step();issue=ip;#1;
   if(checked_issue!=='1||fault)$fatal(1,"JOIN_REAL_READ_ACCEPT");
   tick();step();issue=0;
   for(p=0;p<32;p=p+1)callerord[p*16+:16]=callerord[p*16+:16]+1'b1;
   tick();step();ret=rp;#1;
   if(checked_return!=='1||checked_data!==payload||fault)$fatal(1,"JOIN_REAL_PAYLOAD_FRAME");
   for(p=0;p<32;p=p+1)if(checked_ord[p*16+:16]!==callerord[p*16+:16]-16'd1)$fatal(1,"JOIN_RETURN_ORDINAL");
   accepted=accepted+32;delivered=delivered+32;
   tick();step();ret=0;tick();step();
   // Reclaim only after this vehicle consumed/compared the returned payload.
   for(p=0;p<32;p=p+1)freed[p*3+:3]=1;
   tick();step();freed=0;tick();
  end
 endtask
 initial begin
  for(p=0;p<32;p=p+1)for(b=0;b<8;b=b+1)payload[p*256+b*32+:32]=32'h10203040^(p<<16)^b;
  cold();enroll((73'b1<<72)|(73'b1<<52)|73'h12345678);
  read_once();
  if(!drained||provider_fault||off_issue||off_return||off_fault)$fatal(1,"JOIN_DRAIN_DEFAULT_OFF");
  // Real drained rebind keeps ordinals continuous; no warm reset of either side.
  enroll((73'b1<<71)|(73'b1<<51)|73'h87654321);read_once();
  // Wrong high full73 bit must suppress every publication before capture.
  step();issue=ip;tick();step();issue=0;
  for(p=0;p<32;p=p+1)callerord[p*16+:16]=callerord[p*16+:16]+1'b1;
  tick();step();wrong_frame=1;ret=rp;#1;
  if(!fault||checked_return!=0)$fatal(1,"JOIN_FULL73_HIGHBIT_ACCEPTED");
  tick();step();wrong_frame=0;ret=0;tick();
  if(!fault)$fatal(1,"JOIN_FAILURE_NOT_HELD");
  cold();enroll(73'hdef);step();wrong_issue=1;issue=ip;#1;
  if(!fault||checked_issue!=0||checked_return!=0)$fatal(1,"JOIN_ISSUE_ORDINAL_ACCEPTED");
  cold();enroll(73'habc);step();frame_valid=0;issue=ip;#1;
  if(!fault||checked_issue!=0)$fatal(1,"JOIN_UNENROLLED_ACCEPTED");
  cold();enroll(73'h123);step();dut.on.poison_n=0;#1;
  if(!fault||checked_issue||checked_return)$fatal(1,"JOIN_FAULT_RAIL_ACCEPTED");
  $display("R5A_PROVIDER_JOIN_PASS PCs32 realREAD64 exact256payload64 full73highbit issueordinal unenrolled stickyrail defaultOFF drainedrebind");$finish;
 end
endmodule
