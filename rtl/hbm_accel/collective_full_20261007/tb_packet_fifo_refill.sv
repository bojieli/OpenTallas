`timescale 1ns/1ps
// II=1 refill packet SRAM bench: tb_packet_fifo's order/stall/wrap/reset/ECC/seal/overflow checks
// plus a full-rate stream that must retire one flit an edge (PASS_II1), random push/pop, and
// count == pushed - popped on every edge.  -DII3_BASELINE runs the II=3 queue (the II1 check must fail).
module tb_packet_fifo_refill;
 parameter integer DEPTH=256, REFILL=1;  // -DII3_BASELINE: II=3 queue (negative control)
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,push=0,pop=0;reg[544:0]din=0;
 wire ready,valid,fault;wire[544:0]dout;wire[8:0]count;
`ifdef II3_BASELINE
 localparam integer REFILL_EFF=0;
 ot_hbm_collective_packet_fifo #(.ENABLE(1),.DEPTH(DEPTH)) dut(.*);
`else
 localparam integer REFILL_EFF=REFILL;
 ot_hbm_collective_packet_fifo_refill #(.ENABLE(1),.DEPTH(DEPTH)) dut(.*);
`endif
 reg[544:0] expected[0:40000];integer wr=0,rd=0,cyc=0;integer i,burst,maxburst;
 function automatic [544:0] payload(input integer x);
  reg[544:0]v;begin for(integer j=0;j<17;j=j+1)v[j*32+:32]=(32'hbf34981b*x)^(j*32'h7e529bd1);v[544]=x[1];payload=v;end
 endfunction
 task edge_step;begin
  @(posedge clk);
  if(fault)$fatal(1,"unexpected fault");
  if(pop&&valid)begin if(dout!==expected[rd])$fatal(1,"DATA order mismatch %0d",rd);rd=rd+1;burst=burst+1;if(burst>maxburst)maxburst=burst;end
  else burst=0;
  if(push&&ready)begin expected[wr]=din;wr=wr+1;end
  #1;if(count!==wr-rd)$fatal(1,"COUNT mismatch got%0d expected%0d",count,wr-rd);
  @(negedge clk);cyc=cyc+1;
 end endtask
 task cold;begin rst_n=0;repeat(2)@(negedge clk);rst_n=1;wr=0;rd=0;pop=0;push=0;burst=0;end endtask
 integer t_stream,n_stream;
 initial begin
  burst=0;maxburst=0;
  repeat(3)@(negedge clk);rst_n=1;
  for(i=0;i<DEPTH;i=i+1)begin push=1;din=payload(wr);edge_step();end
  push=0;if(ready)$fatal(1,"full accepted");repeat(9)edge_step();
  // Drain a full queue at one pop per edge: must retire DEPTH flits in DEPTH edges (+ 0 bubbles).
  pop=1;t_stream=cyc;n_stream=rd;
  while(rd<wr)edge_step();
  if((cyc-t_stream)!=DEPTH)$fatal(1,"II1 drain took %0d edges for %0d flits",cyc-t_stream,DEPTH);
  // Simultaneous push and pop at full rate through an empty queue (streaming pass-through).
  maxburst=0;burst=0;
  for(i=0;i<4*DEPTH;i=i+1)begin push=1;din=payload(wr);pop=1;edge_step();end
  push=0;while(rd<wr)edge_step();
  if(maxburst<4*DEPTH-4)$fatal(1,"CDC_II1 insufficient consecutive retirement %0d",maxburst);
  // Random traffic with stalls, wrap repeatedly.
  for(i=0;i<12000;i=i+1)begin pop=($urandom_range(0,3)!=0);push=ready&&($urandom_range(0,2)!=0);din=payload(wr);edge_step();end
  // Bursty consumer: long stalls then bursts, to exercise R held across stalls.
  for(i=0;i<6000;i=i+1)begin pop=((i/17)%3!=0);push=ready&&((i/5)%4!=0);din=payload(wr);edge_step();end
  push=0;pop=1;while(rd<wr)edge_step();
  if(wr<DEPTH*8)$fatal(1,"insufficient wrap");
  // Cold reset invalidates stale SRAM content.
  cold();
`ifdef II3_BASELINE
  push=1;din=payload(991);edge_step();push=0;while(!valid)edge_step();
  dut.g_on.captured[3]=~dut.g_on.captured[3];#1;
  if(fault||dout!==payload(991))$fatal(1,"single correction failed");
  dut.g_on.captured[4]=~dut.g_on.captured[4];#1;
  if(!fault||valid||ready)$fatal(1,"double error escaped");
`else
  // SRAM residency: a single upset in the stored code (word 0 at address 0: macro 0, row 0, column 2*bit)
  // is corrected on the way out; a double upset is detected (fault, never valid).
  push=1;din=payload(991);edge_step();push=0;
  dut.g_ram[0].storage.arr[0][2*5]=~dut.g_ram[0].storage.arr[0][2*5];
  while(!valid&&!fault)edge_step();
  if(fault||dout!==payload(991))$fatal(1,"single correction failed (SRAM upset)");
  // head register upset while held: detected one edge later, valid drops, never delivered
  dut.captured[17]=~dut.captured[17];
  @(posedge clk);#1;
  if(!fault||valid||ready)$fatal(1,"held-register upset escaped");
  cold();
  push=1;din=payload(992);edge_step();push=0;
  dut.g_ram[0].storage.arr[0][2*5]=~dut.g_ram[0].storage.arr[0][2*5];
  dut.g_ram[0].storage.arr[0][2*9]=~dut.g_ram[0].storage.arr[0][2*9];
  repeat(4)begin @(posedge clk);#1;if(valid)$fatal(1,"double error escaped (SRAM upset)");end
  if(!fault||ready)$fatal(1,"double error not flagged");
`endif
  cold();#1;
`ifdef II3_BASELINE
  dut.g_on.seal[0]=1;#1;
`else
  dut.seal[0]=1;#1;
`endif
  if(!fault||ready)$fatal(1,"control seal escaped");
  cold();
  for(i=0;i<DEPTH;i=i+1)begin push=1;din=payload(wr);edge_step();end
  @(posedge clk);#1;if(!fault||ready||valid)$fatal(1,"overflow escaped");
  $display("PASS_II1 longest_consecutive_retirement=%0d full_drain_edges=%0d",maxburst,DEPTH);
  $display("PASS depth=%0d cycles=%0d wrap/order/stall/reset/single/double/control/overflow",DEPTH,cyc);$finish;
 end
endmodule
