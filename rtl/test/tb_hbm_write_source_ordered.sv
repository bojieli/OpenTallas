`timescale 1ns/1ps
module tb_hbm_write_source_ordered;
 parameter USE_COUNT_ACK=0,BAD=0;
 reg ck=0,rst_n=0;always #0.416667 ck=~ck;
 reg[31:0]iv=0,dv=0;reg[1:0]isrc=0;wire[31:0]ready,busy;wire[17:0]ack;wire fault;
 generate if(USE_COUNT_ACK)begin:mutant
  ot_hbm_write_source_pc dut(ck,rst_n,iv,isrc,ready,busy,dv,ack,fault);
 end else begin:normal
  ot_hbm_write_source_ordered #(.ENABLE(1)) dut(ck,rst_n,iv,isrc,ready,busy,dv,ack,fault);
 end endgenerate
 integer qs[0:31][0:31],qo[0:31][0:31],wp[0:31],rp[0:31];
 integer sent[0:2],retired[0:2];reg done[0:2][0:2047];
 integer p,s,k,j,n,total=0,accepted=0;
 task put(input integer pc,input integer src);
 begin
  @(negedge ck);dv=0;iv=0;isrc=src;#0.01;
  if(!ready[pc])$fatal(1,"admission unexpectedly blocked pc%0d",pc);
  iv[pc]=1;qs[pc][wp[pc]]=src;qo[pc][wp[pc]]=sent[src];wp[pc]=wp[pc]+1;
  done[src][sent[src]]=0;sent[src]=sent[src]+1;accepted=accepted+1;
 end endtask
 task finish_pc(input integer pc);
 begin
  if(rp[pc]>=wp[pc])$fatal(1,"test source FIFO empty");
  done[qs[pc][rp[pc]]][qo[pc][rp[pc]]]=1;rp[pc]=rp[pc]+1;dv[pc]=1;
 end endtask
 always @(posedge ck)begin
  #0.1;
  if(rst_n&&!BAD)begin
   if(fault)$fatal(1,"unexpected real source ACK fault");
   for(integer x=0;x<3;x=x+1)begin
    n=(ack>>(6*x))&63;
    for(integer y=0;y<n;y=y+1)begin
     if(retired[x]>=sent[x]||!done[x][retired[x]])$fatal(1,"EARLY_ORDINAL_ACK source%0d ordinal%0d",x,retired[x]);
     done[x][retired[x]]=0;retired[x]=retired[x]+1;total=total+1;
    end
   end
  end
 end
 initial begin
  for(p=0;p<32;p=p+1)begin wp[p]=0;rp[p]=0;end
  for(s=0;s<3;s=s+1)begin sent[s]=0;retired[s]=0;for(j=0;j<2048;j=j+1)done[s][j]=0;end
  repeat(4)@(negedge ck);rst_n=1;
  if(BAD)begin dv=1;repeat(2)@(negedge ck);if(!fault)$fatal(1,"orphancompletion escaped");$display("ORDERED_SOURCE ORPHAN_DETECTED");$finish;end
  // Full256-slot source1 window; later-PC visibility must not publish ordinal0.
  for(k=0;k<8;k=k+1)for(p=0;p<32;p=p+1)put(p,1);
  @(negedge ck);iv=0;
  for(k=0;k<8;k=k+1)for(p=31;p>=0;p=p-1)begin @(negedge ck);dv=0;finish_pc(p);end
  @(negedge ck);dv=0;repeat(300)@(negedge ck);
  if(total!=256||(|busy))$fatal(1,"firstprefix not drained");
  // Reuse all slots with mixed source ownership,32simultaneousPCcompletions.
  for(k=0;k<8;k=k+1)for(p=0;p<32;p=p+1)put(p,k%3);
  @(negedge ck);iv=0;
  for(k=0;k<8;k=k+1)begin @(negedge ck);dv=0;for(p=0;p<32;p=p+1)finish_pc(p);end
  @(negedge ck);dv=0;repeat(300)@(negedge ck);
  if(total!=512||total!=accepted||(|busy))$fatal(1,"sourcewindow/ACKnotdrained");
  for(s=0;s<3;s=s+1)if(retired[s]!=sent[s])$fatal(1,"wrongsourceACKcount");
  $display("ORDERED_SOURCE PASS accepted=%0d retired=%0d full32PCdepth8 reversedPCand32simultaneousWD",accepted,total);$finish;
 end
endmodule
