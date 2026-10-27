`timescale 1ns/1ps
module tb_s81hd_static_issue;
 parameter integer MUT=0;
 reg ck=0;always #0.4165 ck=~ck;
 reg rn=0,start=0,run=1,ready=0,busy=0,retire=0,merge=0;reg[15:0]period=20,deadline=5;reg prohibit_issue=0;
 wire issue,job,due,fault;
 ot_s81hd_static_issue #(.MUT_MODE(MUT))dut(.ck(ck),.rn(rn),.start_i(start),.run_i(run),
 .issue_offset(16'd7),.issue_period(period),.merge_deadline(deadline),
 .loaded_ready(ready),.replay_busy(busy),.token_retire(retire),.merged_valid(merge),
 .issue_o(issue),.job_active_o(job),.due_o(due),.fault_o(fault));
 integer cycle=-1,S=-1,seen=0;reg expected;reg check_dates=1;
 always@(posedge ck)if(rn&&check_dates)begin
  cycle=cycle+1;if(start&&S<0)S=cycle;
  expected=S>=0&&(cycle-S==7||cycle-S==27||cycle-S==47);
  if(due!==expected)$fatal(1,"date miter mismatch at%0d",cycle-S);
  if(issue!==expected)$fatal(1,"issue miter readiness changed date at%0d",cycle-S);
  if(issue)seen=seen+1;
 end
 always@(posedge ck)if(rn&&prohibit_issue&&issue)$fatal(1,"invalid/aborted schedule issued GO");
 task tick;@(negedge ck);endtask
 integer i;
 initial begin
  repeat(3)tick;rn=1;repeat(3)tick;ready=1;repeat(2)tick;start=1;
  for(i=0;i<56;i=i+1)begin
   ready=!(i%20>=8 && i%20<=10);busy=!ready;
   merge=i==10||i==30||i==50;
   retire=i==14||i==34||i==54;
   tick;
   if((i==11||i==31||i==51)&&!job)$fatal(1,"merge incorrectly retired job");
  end
  run=0;retire=0;merge=0;
  if(seen!=3||fault)$fatal(1,"positive completion seen%0d fault%b",seen,fault);
  check_dates=0;rn=0;start=0;repeat(3)tick;rn=1;run=1;ready=0;start=1;
  repeat(10)tick;if(!fault||job)$fatal(1,"missing vector did not fault at its date");
  prohibit_issue=1;ready=1;repeat(20)tick;prohibit_issue=0;
  rn=0;start=0;repeat(3)tick;rn=1;ready=1;start=1;
  repeat(15)tick;if(!fault||!job)$fatal(1,"missing mesh deadline did not fault/retain job");
  rn=0;start=0;period=0;repeat(3)tick;rn=1;ready=1;start=1;prohibit_issue=1;
  repeat(10)tick;if(!fault||job)$fatal(1,"zero period admitted");
  rn=0;start=0;period=20;deadline=0;repeat(3)tick;rn=1;start=1;
  repeat(10)tick;if(!fault||job)$fatal(1,"zero merge deadline admitted");
  $display("PASS static_issue lockstep dates=3 job-retirement distinct missing-vector/deadline faults");$finish;
 end
 initial #1000 $fatal(1,"timeout");
endmodule
