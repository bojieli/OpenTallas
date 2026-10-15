`timescale 1ns/1ps
// Counterexample, not a production qualification: raw packed payload 2 looks
// like a legacy gearbox idle and is silently dropped while FIFO is not full.
module tb_legacy_idle_collision;
 reg wc=0,rc=0,rst_n=0,wv=0;
 always #5 wc=~wc;
 always #50 rc=~rc;
 reg [511:0] wd=0;
 wire [511:0] rd;
 wire fault;
 integer i,before_ptr;
 ot_s81_rate_match u(wc,rst_n,wv,wd,rc,rst_n,rd,fault);
 initial begin
  repeat(3)@(posedge rc);@(negedge wc);rst_n=1;
  for(i=0;i<6;i=i+1)begin
   @(negedge wc);wv=1;wd=(512'(i+1)<<2);
   @(posedge wc);#1;
  end
  @(negedge wc);wv=0;
  if(u.fill_w<6 || u.full)$fatal(1,"counterexample precondition fill=%0d full=%b",u.fill_w,u.full);
  before_ptr=u.wp;
  wd=512'd2;wv=1;
  #1;
  if(u.push!==1'b0)$fatal(1,"legacy classifier changed; re-evaluate boundary");
  @(posedge wc);#1;
  if(u.wp!==before_ptr || fault)$fatal(1,"unexpected pointer/fault");
  $display("COUNTEREXAMPLE_CONFIRMED packed payload=2 dropped with fill=%0d full=%b fault=%b",u.fill_w,u.full,fault);
  $finish;
 end
 initial begin #10000;$fatal(1,"timeout");end
endmodule
