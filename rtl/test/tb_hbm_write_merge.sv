`timescale 1ns/1ps
module tb_hbm_write_merge;
 reg ck=0;always #0.416667 ck=~ck;
 reg rst_n=0;reg [2:0] v=0;reg [872:0] d=0;wire[2:0] r;
 wire sv;wire[290:0] sd;reg sr=0;reg[7:0] ack=0;wire[17:0] sa;wire fault;
 ot_hbm_write_merge #(.ENABLE(1)) dut(ck,rst_n,v,d,r,sv,sd,sr,ack,sa,fault);
 integer sourceq[0:8191];reg[290:0] dataq[0:8191];integer iw=0,ir=0;
 integer phyq[0:8191];integer pw=0,pr=0;
 integer cycles=0,accepted=0,retired=0,stalls=0,background=0,burst=0;
 integer last_bg=2;integer nextseq[0:2];integer i,j,n;reg[31:0] rng=32'h13579abc;
 reg[5:0] a[0:2];reg[17:0] expected_ack;reg hold=0;reg[290:0] held;
 initial begin
  nextseq[0]=0;nextseq[1]=0;nextseq[2]=0;
  repeat(5) @(negedge ck);rst_n=1;
  for(cycles=0;cycles<1800;cycles=cycles+1) begin
   rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
   // First exercise deterministic contention, then burst ACKs / stalls,
   // finally drain the finite campaign.
   v=cycles<60?3'b111:(cycles<1500?rng[2:0]:3'b000);
   sr=cycles<60?1'b1:rng[3];
   for(i=0;i<3;i=i+1)d[i*291+:291]={256'(nextseq[i]*3+i),30'(nextseq[i]),5'(i)};
   ack=0;n=pw-pr;
   if(cycles>=60 && n>0 && (rng[4] || cycles>=1500))begin
    ack=cycles>=1500?n:((rng[7:5]%n)+1);
    if(ack>1)burst=burst+1;
   end
   a[0]=0;a[1]=0;a[2]=0;
   for(j=0;j<ack;j=j+1) begin a[phyq[pr+j]]=a[phyq[pr+j]]+1;end
   expected_ack={a[2],a[1],a[0]};
   @(posedge ck);
   if(hold && (!sv || sd!==held))$fatal(1,"stalled service payload changed");
   hold=sv&&!sr;held=sd;if(hold)stalls=stalls+1;
   if(sv&&sr)begin
    if(ir==iw || sd!==dataq[ir])$fatal(1,"write mismatch at %0d",ir);
    phyq[pw]=sourceq[ir];pw=pw+1;ir=ir+1;
   end
   pr=pr+ack;retired=retired+ack;
   for(i=0;i<3;i=i+1)if(v[i]&&r[i])begin
    if(v[0]&&i!=0)$fatal(1,"WB priority violated");
    if(i!=0)begin
     if(v[1]&&v[2]&&i==last_bg)$fatal(1,"background alternation violated");
     last_bg=i;background=background+1;
    end
    dataq[iw]=d[i*291+:291];sourceq[iw]=i;iw=iw+1;
    nextseq[i]=nextseq[i]+1;accepted=accepted+1;
   end
   #0.1;
   if(sa!==expected_ack || fault)$fatal(1,"ACK ownership mismatch expected %h got %h",expected_ack,sa);
   @(negedge ck);
  end
  if(iw!=ir || pw!=pr || accepted!=retired || stalls==0 || background==0 || burst==0)
   $fatal(1,"campaign did not drain/exercise mechanism");
  // Completion beyond issued inventory must fault and acknowledge nothing.
  ack=1;v=0;@(posedge ck);#0.1;
  if(!fault || sa!=0)$fatal(1,"invalid completion accepted");
  $display("WRITE_MERGE PASS accepted=%0d retired=%0d stalls=%0d background=%0d bursts=%0d",accepted,retired,stalls,background,burst);
  $finish;
 end
endmodule
