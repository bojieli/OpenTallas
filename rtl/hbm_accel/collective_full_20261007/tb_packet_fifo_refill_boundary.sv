`timescale 1ns/1ps
// Boundary bench of the II=1 refill: a write never hits the address being read, R/H never counted
// as quiet, full + push+pop rejected and latched (legacy contract), and the read latch R is never
// overwritten while it holds an untransferred word (fetch only when R is free or moving to H).
module tb_packet_fifo_refill_boundary;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,push=0,pop=0;reg [544:0]din=0;
 wire ready,valid,fault;wire[544:0]dout;wire[8:0]count;
 integer simultaneous=0;
 ot_hbm_collective_packet_fifo_refill #(.ENABLE(1),.DEPTH(64)) dut(.*);
 always @(posedge clk)if(rst_n)begin
  if(dut.put&&dut.fetch)begin
   simultaneous=simultaneous+1;
   if(dut.c_wp==dut.c_rp)$fatal(1,"same-address access escaped");
  end
  if(dut.fetch&&dut.c_pending&&!dut.xfer)$fatal(1,"read latch overwritten");
  if(dut.c_pending&&count==0)$fatal(1,"pending falsely quiet");
  if(dut.c_held&&count==0)$fatal(1,"held falsely quiet");
 end
 initial begin
  repeat(3)@(negedge clk);rst_n=1;pop=1;
  for(integer i=0;i<250;i=i+1)begin
   push=ready;din=i;pop=(i%5!=0);@(posedge clk);#1;if(fault)$fatal(1,"legal mixed traffic fault");@(negedge clk);
  end
  pop=0;
  while(ready)begin push=1;@(posedge clk);#1;@(negedge clk);end
  push=0;while(!valid)@(negedge clk);
  if(!valid||count!=64)$fatal(1,"full state wrong");
  if(simultaneous==0)$fatal(1,"simultaneous read/write not exercised");
  push=1;pop=1;
  if(ready)$fatal(1,"full simultaneous edge illegally ready");
  @(posedge clk);#1;
  if(!fault||ready||valid||count!=63)$fatal(1,"full simultaneous edge failed closed contract");
  $display("PASS_BOUNDARY simultaneous_distinct_address=%0d full_pop_push_rejected pending_held_not_quiet latch_never_overwritten",simultaneous);$finish;
 end
endmodule
