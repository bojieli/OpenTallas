`timescale 1ns/1ps
module tb_packet_fifo;
 parameter integer DEPTH=256;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,push=0,pop=0;reg[544:0]din=0;
 wire ready,valid,fault;wire[544:0]dout;wire[8:0]count;
 ot_hbm_collective_packet_fifo #(.ENABLE(1),.DEPTH(DEPTH)) dut(.*);
 reg[544:0] expected[0:20000];integer wr=0,rd=0,cyc=0;integer i;
 function automatic [544:0] payload(input integer x);
  reg[544:0]v;begin for(integer j=0;j<17;j=j+1)v[j*32+:32]=(32'hbf34981b*x)^(j*32'h7e529bd1);v[544]=x[1];payload=v;end
 endfunction
 task edge_step;begin
  @(posedge clk);
  if(fault)$fatal(1,"unexpected fault");
  if(pop&&valid)begin if(dout!==expected[rd])$fatal(1,"DATA order mismatch %0d",rd);rd=rd+1;end
  if(push&&ready)begin expected[wr]=din;wr=wr+1;end
  #1;if(count!==wr-rd)$fatal(1,"COUNT mismatch got%0d expected%0d",count,wr-rd);
  @(negedge clk);cyc=cyc+1;
 end endtask
 initial begin
  repeat(3)@(negedge clk);rst_n=1;
  // Fill exactly, hold at capacity, drain and wrap repeatedly with random stalls.
  for(i=0;i<DEPTH;i=i+1)begin push=1;din=payload(wr);edge_step();end
  push=0;if(ready)$fatal(1,"full accepted");repeat(9)edge_step();
  for(i=0;i<6000;i=i+1)begin pop=($urandom_range(0,3)!=0);push=ready&&($urandom_range(0,2)!=0);din=payload(wr);edge_step();end
  push=0;pop=1;while(rd<wr)edge_step();
  if(wr<DEPTH*2)$fatal(1,"insufficient wrap");
  // Cold reset invalidates stale SRAM content.
  rst_n=0;repeat(2)@(negedge clk);rst_n=1;wr=0;rd=0;pop=0;
  push=1;din=payload(991);edge_step();push=0;while(!valid)edge_step();
  // A payload single bit is corrected, two bits fail closed; control corruption
  // likewise cannot authorize an access. Deliberate corruption of held register
  // tests shared ECC boundary, not SRAM physical upset coverage.
  dut.g_on.captured[3]=~dut.g_on.captured[3];#1;
  if(fault||dout!==payload(991))$fatal(1,"single correction failed");
  dut.g_on.captured[4]=~dut.g_on.captured[4];#1;
  if(!fault||valid||ready)$fatal(1,"double error escaped");
  rst_n=0;repeat(2)@(negedge clk);rst_n=1;#1;
  dut.g_on.seal[0]=1;#1;if(!fault||ready)$fatal(1,"control seal escaped");
  rst_n=0;repeat(2)@(negedge clk);rst_n=1;wr=0;rd=0;pop=0;
  for(i=0;i<DEPTH;i=i+1)begin push=1;din=payload(wr);edge_step();end
  // Overflow latches a sealed control fault; no silent entry loss.
  @(posedge clk);#1;if(!fault||ready||valid)$fatal(1,"overflow escaped");
  $display("PASS depth=%0d cycles=%0d wrap/order/stall/reset/single/double/control/overflow",DEPTH,cyc);$finish;
 end
endmodule
