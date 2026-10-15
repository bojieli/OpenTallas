`timescale 1ns/1ps
module tb_calendar_static;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,program_we=0,start=0;reg[7:0]program_addr=0;reg[255:0]program_data=0;
 reg[11:0]length;wire issue_v,done,fault;wire[31:0]instruction;
 ot_hbm_idx_calendar_static dut(.clk(clk),.clk_mem(clk),.*);
 reg[255:0]mem[0:255];reg[31:0]gold[0:2047];integer checked=0,errors=0,n,rows,cycle=0,tstart,first=-1,last=-1;
 always @(posedge clk)cycle<=cycle+1;
 always @(negedge clk)if(issue_v)begin
  if(first<0)first=cycle;last=cycle;
  if(instruction!==gold[checked])errors++;
  if(done!==(checked==n-1))errors++;
  checked++;
 end
 initial begin
  if(!$value$plusargs("N=%d",n))$fatal(1,"needlength");length=12'(n);rows=(n+7)/8;
  $readmemh("calendar.hex",mem);$readmemh("calendar_instructions.hex",gold);
  repeat(4)@(negedge clk);rst_n=1;
  for(integer r=0;r<rows;r=r+1)begin
   program_we=1;program_addr=8'(r);program_data=mem[r];
   if(MUT==1&&r==10)program_data[0]=~program_data[0];
   @(negedge clk);
  end
  program_we=0;repeat(3)@(negedge clk);start=1;tstart=cycle;
  @(negedge clk);start=0;
  repeat(n+8)@(negedge clk);
  $display("IDX_CALENDAR_STATIC MUT%0d instructions%0d expected%0d errors%0d fault%0d start_to_first%0d span%0d",MUT,checked,n,errors,fault,first-tstart,last-first+1);
  if(errors||fault||checked!=n||last-first+1!=n)$fatal(1,"real SRAM compiler calendar mismatch");$finish;
 end
endmodule
