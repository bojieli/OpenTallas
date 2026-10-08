`timescale 1ns/1ps
// Bench of the pin-registered II=1 packet queue (ot_hbm_collective_packet_fifo_ii1r, drive-0532 2026-10-08).
// Transaction-exact: every accepted flit is delivered once, in order, bit-exact (DATA order mismatch), into a
// consumer model with CB slots that returns one credit (pop pulse) per freed slot (CONSUMER_OVERFLOW if the
// queue sends beyond its credits).  count is checked on every edge against accepted-minus-delivered with the
// registered lag (COUNT mismatch).  Rate: a full queue drains DEPTH flits back-to-back (II1 drain), a
// push+pop stream runs one flit an edge with ready held high (STREAM).  ECC: an SRAM single upset is
// corrected, a double upset faults with the flit never delivered; a raw2 (post-syndrome) register upset is
// detected; control seal and overflow (push while not ready, -DPUSH_IGNORES_READY) fault.
module tb_packet_fifo_ii1r;
 parameter integer DEPTH=256, OCR=8, CB=8, WREG=0, IREL=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,push=0,pop=0;reg[544:0]din=0;
 wire ready,valid,fault;wire[544:0]dout;wire[8:0]count;
 ot_hbm_collective_packet_fifo_ii1r #(.DEPTH(DEPTH),.OCR(OCR),.WREG(WREG),.IREL(IREL)) dut(.*);
 reg[544:0] expected[0:40000];reg[544:0] cbuf[0:63];
 integer wr=0,rd=0,ndel=0,cyc=0,cb_n=0,cb_h=0,cb_t=0,i,burst=0,maxburst=0,wr_old;
 reg want_pop=0,want_push=0,chk_count=1,allow_fault=0;
 function automatic [544:0] payload(input integer x);
  reg[544:0]v;begin for(integer j=0;j<17;j=j+1)v[j*32+:32]=(32'hbf34981b*x)^(j*32'h7e529bd1);v[544]=x[1];payload=v;end
 endfunction
 // one edge: sample pushes with the pre-edge pins, then the registered outputs
 task edge_step;begin
  @(posedge clk);wr_old=wr;
`ifdef PUSH_IGNORES_READY
  if(push)begin expected[wr]=din;wr=wr+1;end
`else
  if(push&&ready)begin expected[wr]=din;wr=wr+1;end
`endif
  #1;
  if(fault&&!allow_fault)$fatal(1,"unexpected fault at cycle %0d",cyc);
  if(valid)begin
   if(cb_n==CB)$fatal(1,"CONSUMER_OVERFLOW: flit sent beyond the %0d credits",CB);
   cbuf[cb_t]=dout;cb_t=(cb_t+1)%64;cb_n=cb_n+1;ndel=ndel+1;burst=burst+1;if(burst>maxburst)maxburst=burst;
  end else burst=0;
  if(chk_count&&count!==wr_old-ndel)$fatal(1,"COUNT mismatch got %0d expected %0d",count,wr_old-ndel);
  @(negedge clk);cyc=cyc+1;
  // consumer: free one slot (credit return) when asked
  pop=0;
  if(want_pop&&cb_n>0)begin
   if(cbuf[cb_h]!==expected[rd])$fatal(1,"DATA order mismatch %0d",rd);
   cb_h=(cb_h+1)%64;cb_n=cb_n-1;rd=rd+1;pop=1;
  end
  push=want_push&&ready;din=payload(wr);
 end endtask
 task cold;begin
  rst_n=0;push=0;pop=0;want_push=0;want_pop=0;repeat(2)@(negedge clk);rst_n=1;
  wr=0;rd=0;ndel=0;cb_n=0;cb_h=0;cb_t=0;burst=0;@(negedge clk);
 end endtask
 task drain;begin want_push=0;want_pop=1;while(rd<wr)edge_step();repeat(10)edge_step();
  if(count!==0||cb_n!=0)$fatal(1,"COUNT mismatch at drain count=%0d cb=%0d",count,cb_n);end endtask
 integer t0,t1,k;
 initial begin
  repeat(3)@(negedge clk);rst_n=1;@(negedge clk);
  // fill with no consumer progress: the queue takes DEPTH resident + CB delivered flits, then ready drops
  want_push=1;want_pop=0;
  for(i=0;i<DEPTH+CB+40;i=i+1)edge_step();
  if(ready)$fatal(1,"full accepted (ready high at %0d accepted)",wr);
  if(wr!=DEPTH+CB)$fatal(1,"CAPACITY accepted %0d, expected %0d",wr,DEPTH+CB);
  want_push=0;
  // II1 drain: consumer frees a slot every edge; the queue must deliver its DEPTH residents back-to-back
  maxburst=0;want_pop=1;t0=cyc;
  while(rd<wr)edge_step();
  if(maxburst<DEPTH)$fatal(1,"II1 drain: longest back-to-back delivery %0d < %0d",maxburst,DEPTH);
  repeat(10)edge_step();
  // streaming: push and pop every edge, ready must stay high and delivery must be one flit an edge
  maxburst=0;want_push=1;want_pop=1;t0=wr;
  for(i=0;i<4*DEPTH;i=i+1)begin edge_step();if(i>4&&!ready)$fatal(1,"STREAM ready dropped at %0d",i);end
  if(wr-t0<4*DEPTH-2)$fatal(1,"STREAM accepted %0d of %0d",wr-t0,4*DEPTH);
  drain();
  if(maxburst<4*DEPTH-8)$fatal(1,"STREAM insufficient consecutive delivery %0d",maxburst);
  // random traffic with stalls and wrap
  for(i=0;i<12000;i=i+1)begin want_pop=($urandom_range(0,3)!=0);want_push=($urandom_range(0,2)!=0);edge_step();end
  for(i=0;i<6000;i=i+1)begin want_pop=((i/17)%3!=0);want_push=((i/5)%4!=0);edge_step();end
  drain();
  if(wr<DEPTH*8)$fatal(1,"insufficient wrap");
  // SRAM single upset corrected: exhaust the credits (CB flits sit in the consumer), then the next flit stays
  // resident at address CB (macro 0, row CB/2, column 2*bit) while it is upset
  cold();
  want_push=1;for(i=0;i<CB;i=i+1)edge_step();want_push=0;repeat(12)edge_step();
  if(cb_n!=CB)$fatal(1,"setup: consumer holds %0d",cb_n);
  push=1;din=payload(wr);edge_step();push=0;repeat(3+IREL)edge_step();
  expected[wr-1]=payload(wr-1);
  dut.g_ram[0].storage.arr[CB/2][2*5]=~dut.g_ram[0].storage.arr[CB/2][2*5];
  drain();
  // double upset: fault, never delivered
  cold();
  want_push=1;for(i=0;i<CB;i=i+1)edge_step();want_push=0;repeat(12)edge_step();
  push=1;din=payload(wr);edge_step();push=0;repeat(3)edge_step();
  dut.g_ram[0].storage.arr[CB/2][2*5]=~dut.g_ram[0].storage.arr[CB/2][2*5];
  dut.g_ram[0].storage.arr[CB/2][2*9]=~dut.g_ram[0].storage.arr[CB/2][2*9];
  allow_fault=1;chk_count=0;want_pop=1;
  for(i=0;i<CB;i=i+1)edge_step();   // the CB good flits leave the consumer; the upset word is fetched
  for(i=0;i<8;i=i+1)begin edge_step();if(valid)$fatal(1,"double error escaped (SRAM upset)");end
  if(!fault||ready)$fatal(1,"double error not flagged");
  allow_fault=0;chk_count=1;
  // raw2 register upset (after the syndrome stage): detected, never delivered
  cold();
  push=1;din=payload(wr);edge_step();push=0;
  allow_fault=1;chk_count=0;
  k=0;while(!dut.v2&&k<8)begin @(posedge clk);#1;k=k+1;end   // flit sits in raw_q; next edge moves it to raw2_q
  @(posedge clk);#1;dut.raw2_q[17]=~dut.raw2_q[17];
  for(i=0;i<6;i=i+1)begin @(posedge clk);#1;if(valid)$fatal(1,"raw2 upset escaped");end
  if(!fault||ready)$fatal(1,"raw2 upset not flagged");
  allow_fault=0;chk_count=1;
  // control seal
  cold();allow_fault=1;chk_count=0;dut.seal[0]=~dut.seal[0];
  repeat(3)begin @(posedge clk);#1;end
  if(!fault||ready)$fatal(1,"control seal escaped");
  allow_fault=0;chk_count=1;
  // overflow: push while ready is low
  cold();
  want_push=1;for(i=0;i<DEPTH+CB+40;i=i+1)edge_step();want_push=0;
  allow_fault=1;chk_count=0;push=1;din=0;
  repeat(3+IREL)begin @(posedge clk);#1;end
  push=0;
  if(!fault||ready||valid)$fatal(1,"overflow escaped");
  $display("PASS_II1R depth=%0d ocr=%0d wreg=%0d irel=%0d cycles=%0d order/count/credit/II1-drain/stream/wrap/reset/single/double/raw2/control/overflow",
   DEPTH,OCR,WREG,IREL,cyc);
  $finish;
 end
endmodule
