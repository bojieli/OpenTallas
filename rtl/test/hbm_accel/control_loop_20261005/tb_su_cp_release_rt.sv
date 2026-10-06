`timescale 1ns/1ps
module tb_su_cp_release_rt;
 reg clk=0;always #5 clk=~clk;
 reg por_n=0;reg[1:0] launch_v=0;reg[31:0] launch_pc=0,cp_job=0;
 reg[3:0] cp_gen=0;reg[16:0] launch_token=0;reg[19:0] launch_pos=0;
 reg lease_granted=0,release_r=0,exec_done=0,exec_fault=0,shared_fault=0;
 reg[3:0] retired_original_ops=0;
 wire[1:0] native_launch;wire lease_v,release_v,owned,pending,quiet,selected,done,fault;
 wire[31:0] selected_pc,held_job;wire[3:0] held_gen;
 wire[16:0] held_token;wire[19:0] held_pos;
 integer checks=0;
 ot_hbm_su_cp_release_rt #(.ENABLE(1)) dut(.*);
 wire[1:0] off_native;wire off_done,off_fault;
 ot_hbm_su_cp_release_rt #(.ENABLE(0)) baseline(
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
  cp_job=32'h10203040;cp_gen=4'h3;launch_token=17'h12345;launch_pos=20'habcde;
  repeat(2)tick();drive();por_n=1;tick();ck(!fault&&!done&&!pending,"reset starts empty");
 end endtask
 task launch(input reg[31:0] pc);
 begin
  drive();launch_pc=pc;launch_v=1;#1;ck(native_launch==0,"selected native lane intercepted");
  ck(off_native==1&&!off_done&&!off_fault,"ENABLE0 native passthrough");
  tick();drive();launch_v=0;#1;
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
  tick();ck(!done&&!pending&&!fault,"CP done is one edge and state rearms");
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
  $display("PASS su_cp_release checks=%0d",checks);$finish;
 end
 initial begin #100000;$fatal(1,"TIMEOUT su_cp_release");end
endmodule
