`timescale 1ns/1ps
module tb_command_class_guard;
 reg clk=0;always #5 clk=~clk;
 reg app_reset_n=0;
 reg[191:0]assembled_command=0;
 reg descriptor_class_at_command=0,context_valid_at_command=0;
 wire fault,disabled_fault;
 integer mut=0,n=0;
 ot_hbm_svc_command_class_guard #(.ENABLE(1))dut(.*);
 ot_hbm_svc_command_class_guard #(.ENABLE(0))off_dut(.clk(clk),.app_reset_n(app_reset_n),
  .assembled_command(assembled_command),.descriptor_class_at_command(descriptor_class_at_command),
  .context_valid_at_command(context_valid_at_command),.fault(disabled_fault));
 task reset;begin
  @(negedge clk);app_reset_n=0;assembled_command=0;context_valid_at_command=0;
  repeat(2)@(negedge clk);app_reset_n=1;
 end endtask
 task offer;input[2:0]m;input c,v,want;begin
  @(negedge clk);assembled_command={8'ha2,m,181'd0};
  descriptor_class_at_command=c;context_valid_at_command=v;
  @(posedge clk);#1;
  if(fault!==want||disabled_fault!==0)$fatal(1,"CLASS_GUARD_FAIL mut=%0d mode=%0d class=%0d valid=%0d got=%0d expected=%0d",mut,m,c,v,fault,want);
  n=n+1;
 end endtask
 initial begin
  if($value$plusargs("MUT=%d",mut))begin end
  reset;
  // Every decoder-legal mode including5 (not produced by present compilers).
  offer(0,0,1,0);offer(1,0,1,0);offer(2,0,1,0);
  offer(4,mut==1?0:1,1,0);
  offer(mut==2?0:6,1,1,0);offer(7,1,1,0);offer(5,1,1,0);
  // Descriptor flips, missing metadata, illegal mode and reset recovery.
  offer(4,0,1,1);reset;offer(0,1,1,1);reset;
  offer(4,1,0,1);reset;offer(3,0,1,1);reset;
  // A post-mrel generic word rewritten from mode0 to mode4 is legal.
  offer(4,1,1,0);
  @(negedge clk);assembled_command=0;context_valid_at_command=0;
  @(posedge clk);#1;if(fault)$fatal(1,"CLASS_GUARD_FAIL idle");
  $display("CLASS_GUARD_PASS offers=%0d",n);$finish;
 end
endmodule
