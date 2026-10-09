`timescale 1ns/1ps
module tb_hbm_write_source_pc;
 reg ck=0;always #0.416667 ck=~ck;reg rst_n=0;
 reg[31:0] iv=0,dv=0;reg[1:0] source=0;wire[31:0] ready,busy;
 wire[17:0] ack;wire fault;
 ot_hbm_write_source_pc dut(.ck(ck),.rst_n(rst_n),.issue_v(iv),.issue_source(source),.issue_rdy(ready),.busy_pc(busy),.done_v(dv),.ack_n(ack),.fault(fault));
 integer q[0:31][0:4095];integer w[0:31],r[0:31];integer total=0,retired=0;
 reg[31:0] rng=32'hA9712365;reg[5:0] a[0:2];reg[17:0] expected;
 integer pc,i,c;
 task tick;
 begin
  a[0]=0;a[1]=0;a[2]=0;
  for(i=0;i<32;i=i+1)begin
   if(dv[i])begin a[q[i][r[i]]]=a[q[i][r[i]]]+1;r[i]=r[i]+1;retired=retired+1;end
   if(iv[i])begin q[i][w[i]]=source;w[i]=w[i]+1;total=total+1;end
  end
  expected={a[2],a[1],a[0]};@(posedge ck);#0.1;
  if(fault||ack!==expected)$fatal(1,"PCsource wrong expected %h got %h",expected,ack);
  @(negedge ck);
 end endtask
 initial begin
  for(i=0;i<32;i=i+1)begin w[i]=0;r[i]=0;end
  repeat(5)@(negedge ck);rst_n=1;
  // Fill all32 PCs to exact8-source-slot capacity with every source.
  for(c=0;c<8;c=c+1)begin iv=32'hffffffff;dv=0;source=c%3;tick();end
  if(busy!=32'hffffffff)$fatal(1,"livePC write inventory absent");
  if(ready!=0)$fatal(1,"capacity not enforced");
  // Retire in reversePC order; burst32 physical completions in onecycle too.
  iv=0;
  for(pc=31;pc>=0;pc=pc-1)begin dv=32'b1<<pc;tick();end
  for(c=0;c<7;c=c+1)begin dv=32'hffffffff;tick();end
  for(c=0;c<2000;c=c+1)begin
   rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
   source=rng[9:8]%3;iv=0;dv=0;
   for(pc=0;pc<32;pc=pc+1)begin
    if(w[pc]!=r[pc] && rng[(pc+1)%32])dv[pc]=1;
    if(ready[pc]&&rng[pc])iv[pc]=1;
   end
   tick();
  end
  iv=0;
  for(c=0;c<8;c=c+1)begin
   dv=0;for(pc=0;pc<32;pc=pc+1)if(w[pc]!=r[pc])dv[pc]=1;
   tick();
  end
  if(busy!=0)$fatal(1,"livePC inventory not drained");
  if(total!=retired)$fatal(1,"ledger failed drain %0d/%0d",retired,total);
  // Unexpectedcompletion must stickyfault without any sourceACK.
  iv=0;dv=1;@(posedge ck);#0.1;
  if(!fault||ack!=0||ready!=0)$fatal(1,"invalid completion not failclosed");
  $display("WRITE_SOURCE_PC PASS pcs=32 depth=8 issued=%0d retired=%0d",total,retired);$finish;
 end
endmodule
