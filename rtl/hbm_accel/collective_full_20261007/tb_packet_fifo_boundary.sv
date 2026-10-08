`timescale 1ns/1ps
module tb_packet_fifo_boundary;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,push=0,pop=0;reg [544:0]din=0;
 wire ready,valid,fault;wire[544:0]dout;wire[8:0]count;
 integer simultaneous=0,transactions=0;
 ot_hbm_collective_packet_fifo #(.ENABLE(1),.DEPTH(64)) dut(.*);
 always @(posedge clk)if(rst_n)begin
  if(dut.g_on.put&&dut.g_on.fetch)begin
   simultaneous=simultaneous+1;
   if(dut.g_on.c.wp==dut.g_on.c.rp)$fatal(1,"same-address access escaped");
  end
  if(dut.g_on.c.pending&&count==0)$fatal(1,"pending falsely quiet");
  if(dut.g_on.c.held&&count==0)$fatal(1,"held falsely quiet");
 end
 initial begin
  repeat(3)@(negedge clk);rst_n=1;pop=1;
  for(integer i=0;i<250;i=i+1)begin
   push=ready;din=i;@(posedge clk);#1;if(fault)$fatal(1,"legal mixed traffic fault");@(negedge clk);
  end
  // Stop retirement and fill all outstanding capacity, including held head.
  pop=0;
  while(ready)begin push=1;@(posedge clk);#1;@(negedge clk);end
  push=0;while(!valid)@(negedge clk);
  if(!valid||count!=64)$fatal(1,"full state wrong");
  if(simultaneous==0)$fatal(1,"simultaneous read/write not exercised");
  // Matches legacy FIFO: being full forbids enqueue even when pop occurs.
  // The invalid push must be rejected and latch fault, never overwrite unread.
  push=1;pop=1;
  if(ready)$fatal(1,"full simultaneous edge illegally ready");
  @(posedge clk);#1;
  if(!fault||ready||valid||count!=63)$fatal(1,"full simultaneous edge failed closed contract");
  $display("PASS_BOUNDARY simultaneous_distinct_address=%0d full_pop_push_rejected pending_held_not_quiet",simultaneous);$finish;
 end
endmodule
