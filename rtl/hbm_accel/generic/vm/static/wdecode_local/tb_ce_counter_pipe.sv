`timescale 1ns/1ps
module tb_ce_counter_pipe;
 parameter integer MUT=0;
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0,event_v=0;reg[3:0] event_count=0;wire[15:0] count;
 ot_vms_ce_counter_pipe #(.MUT(MUT)) dut(.*);
 integer expected=0,previous=0,total=0,seed,step;reg [31:0] random_state=32'h789abcdf;
 task tick(input integer value,input integer valid);
 begin
  @(negedge clk);event_v=valid;event_count=4'(value);
  @(posedge clk);#0.1;
  if(count!==16'(expected))$fatal(1,"carry pipeline mismatch cycle%0d got%0d expected%0d",total,count,expected);
  if(valid)begin expected=expected+value;if(expected>65535)expected=65535;end
  total=total+1;
 end endtask
 initial begin
 repeat(2)@(negedge clk);rst_n=1;
 for(integer n=0;n<30000;n=n+1)begin
  random_state=random_state^(random_state<<13);random_state=random_state^(random_state>>17);random_state=random_state^(random_state<<5);
  tick(random_state%9,random_state[8]);
 end
 tick(0,0);tick(0,0);
 // All65536 count states x nine legal event populations; includes every saturation boundary.
 for(seed=0;seed<65536;seed=seed+1)for(step=0;step<=8;step=step+1)begin
  @(negedge clk);event_v=1;event_count=4'(step);
  dut.low=4'(seed);dut.low_aligned=4'(seed);dut.upper=12'(seed>>4);dut.carry_q=0;dut.saturated=0;
  @(posedge clk);#0.1;
  @(negedge clk);event_v=0;
  @(posedge clk);#0.1;
  expected=seed+step;if(expected>65535)expected=65535;
  if(count!==16'(expected))$fatal(1,"exhaustive mismatch seed%0d step%0d got%0d expected%0d",seed,step,count,expected);
 end
 $display("CE_COUNTER_PIPE PASS stream30000 exhaustive589824");$finish;
 end
endmodule
