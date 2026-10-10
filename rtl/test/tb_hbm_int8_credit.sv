`timescale 1ns/1ps
module tb_hbm_int8_credit;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,launch=0,take=0,int8_mode=0;
 reg [12:0] op_rows=0;
 reg [7:0] op_g=0;
 reg [15:0] op_c=0;
 wire intake_credit;
 ot_hbm_accel_int8_credit #(.RW(12)) dut(.*);
 integer cases=0,accepted=0,j;
 task run(input integer rows,groups,columns,mode);
 integer n,i;
 begin
  @(negedge clk);op_rows=rows;op_g=groups;op_c=columns;int8_mode=mode;launch=1;take=0;
  @(negedge clk);launch=0;n=rows*groups*columns/(mode?2:1);
  for(i=0;i<n;i=i+1) begin
   if(!intake_credit) $fatal(1,"early credit exhaustion %0d/%0d",i,n);
   take=1;@(negedge clk);accepted=accepted+1;
   if(i%13==4) begin take=0;repeat(2) @(negedge clk);end
  end
  take=0;
  if(intake_credit) $fatal(1,"extra cross-operation intake credit");
  cases=cases+1;
 end endtask
 initial begin
  repeat(3) @(negedge clk);rst_n=1;
  run(32,8,8,1);run(8,8,8,1);run(8,8,8,1);run(128,2,8,1);
  run(96,8,8,1);run(96,8,8,1);run(128,6,8,1);run(1187,8,8,1);
  // Even total with odd inner dimensions crosses a nested boundary mid-line.
  run(2,3,3,1);run(3,2,3,1);run(3,3,3,0);run(2,1,7,0);
  run(0,1,8,1);
  @(negedge clk);launch=1;op_rows=12;op_g=8;op_c=8;
  @(negedge clk);launch=0;take=1;
  repeat(4) @(negedge clk);rst_n=0;take=0;
  @(negedge clk);rst_n=1;
  if(intake_credit) $fatal(1,"reset ghost credit");
  $display("PASS finite nested intake credit: full Qwen shapes, odd dimensions, legacy/reset; cases=%0d lines=%0d",cases,accepted);$finish;
 end
 initial begin #20000000;$fatal(1,"deadlock watchdog");end
endmodule
