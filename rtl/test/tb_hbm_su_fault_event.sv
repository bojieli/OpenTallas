`timescale 1ns/1ps
// Minimum actual SU-side controller consumer. Arithmetic remains independently
// source-pinned; inject its aggregate fault-event interface, not result metadata.
module tb_hbm_su_fault_event;
 reg clk=0;always #5 clk=~clk;
 reg por_n=0;reg [1:0] launch_v=0;reg [31:0] launch_pc=32'h80000004;
 reg [31:0] cp_job=32'h1234;reg [3:0] cp_gen=3;
 reg [16:0] launch_token=4;reg [19:0] launch_pos=7;
 reg lease_granted=0,release_r=0,shared_fault=0,exec_done=0,raw_fault=0;
 reg [3:0] retired_original_ops=0;
 wire exec_fault;
`ifdef OT_NEG_SU_EVENT_BYPASS
 assign exec_fault=0;
`else
 assign exec_fault=raw_fault;
`endif
 wire lease_v,release_v,quiet,owned,pending,selected,done,fault;
 wire exec_owned,new_request_permit,association_fault;
 wire [31:0] selected_pc,held_job;wire [3:0] held_gen;
 wire [16:0] held_token;wire [19:0] held_pos;
 ot_hbm_su_cp_side #(.ENABLE(1),.OWN_IN(1),.OWN_OUT(1),.EXEC_IN(0),.EXEC_OUT(1),.OUT(1)) dut(.*);
 integer checks=0,cases=0;
 task tick;begin @(posedge clk);#1;end endtask
 task drive;begin @(negedge clk);end endtask
 task ck(input reg yes,input string why);begin checks=checks+1;if(!yes)$fatal(1,"FAULT_EVENT %s",why);end endtask
 task start;
 integer n;
 begin
  drive();por_n=0;launch_v=0;lease_granted=0;release_r=0;shared_fault=0;exec_done=0;raw_fault=0;retired_original_ops=0;
  repeat(3)tick();drive();por_n=1;repeat(3)tick();
  drive();launch_v=1;tick();drive();launch_v=0;
  n=0;while(!lease_v && n<32)begin tick();n=n+1;end
  ck(lease_v&&!fault,"valid launch must request actual lease");
  drive();lease_granted=1;n=0;
  while(!exec_owned && n<32)begin tick();n=n+1;end
  ck(exec_owned&&!fault,"actual selected executor owns lease");
  repeat(3)tick();ck(new_request_permit&&!fault,"selected executor may issue before fault");
 end endtask
 task pulse_case(input integer delay,input integer drain);
 begin
  start();repeat(delay)tick();
  drive();raw_fault=1;if(drain)begin exec_done=1;retired_original_ops=4;end
  tick();ck(!done,"fault edge never publishes done");
  drive();raw_fault=0;tick();
  ck(fault&&!new_request_permit&&!done,"event is sticky and blocks new requests within two edges");
  drive();exec_done=1;retired_original_ops=4;release_r=1;
  repeat(8)begin tick();ck(fault&&!done&&!new_request_permit,"transient fault cannot be erased by successful drain");end
  drive();lease_granted=0;exec_done=0;
  repeat(4)begin tick();ck(fault&&!done,"cleanup does not clear quarantine without reset");end
  cases=cases+1;
 end endtask
 initial begin
  pulse_case(0,0);pulse_case(32,0);pulse_case(64,1);
  start();ck(!fault&&new_request_permit,"reset permits new clean transaction");
  $display("PASS SU_FAULT_EVENT cases=%0d checks=%0d shape=1,1,0,1,1 bound=2",cases,checks);$finish;
 end
endmodule
