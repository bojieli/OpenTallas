`timescale 1ns/1ps
module tb_wfc_pipeline;
 parameter RLAT=17, PAD=0;
 reg ct=0,cs=0,rt=0,rs=0;
 always #6 ct=~ct; always #8 cs=~cs;
 reg[559:0] f=0; reg[3:0] ev=0,evd=0;reg[2047:0] ed=0,edd=0;
 wire[1028:0] tr,td;wire wr,wd;wire[13:0] ar,ad;wire[511:0] dr,dd;wire[3:0] vr,vd;wire[55:0] rr,rd;wire fr,fd;
 dsfd_vm_static_wfc_r5_ref #(.RLAT(RLAT),.RESPONSE_PAD(PAD)) ref_(cs,ct,cs,ct,cs,ct,rs,rt,rs,rt,rs,rt,f,tr,wr,ar,dr,vr,rr,ev,ed,1'b0,fr);
 dsfd_vm_static_wfc #(.RLAT(RLAT),.RESPONSE_PAD(PAD)) dut(cs,ct,cs,ct,rs,rt,cs,ct,cs,ct,rs,rt,rs,rt,rs,rt,f,td,wd,ad,dd,vd,rd,evd,edd,1'b0,fd);
 reg[526:0] whist=0;reg[59:0] ahist=0;
 reg[1025:0] shist[0:3];reg[1025:0] thist[0:2];reg[3:0] vhist=0;
 integer n=0,k,seed=1,seed0,reads=0,writes=0;
 initial begin
  if($value$plusargs("seed=%d",seed))begin end seed0=seed;
  for(k=0;k<4;k=k+1)shist[k]=0;
  for(k=0;k<3;k=k+1)thist[k]=0;
  #190.5;rt=1;rs=1;
  repeat(2500)begin
   @(negedge ct);
   ev=(ref_.u_ctl.e0 ? (4'd1<<ref_.u_ctl.l0):4'd0)|(ref_.u_ctl.e1 ? (4'd1<<ref_.u_ctl.l1):4'd0);
   for(k=0;k<64;k=k+1)ed[32*k+:32]=$random(seed);
   @(posedge ct);
   evd<=ev;edd<=ed;
   #1;
   if(n>40)begin
    if({wd,ad,dd}!==whist)$fatal(1,"request +1 write mismatch %0d",n);
    if({vd,rd}!==ahist)$fatal(1,"request +1 read mismatch %0d",n);
    if(dut.sd!==shist[3] || dut.sv!==vhist[3])$fatal(1,"return +4 mismatch %0d",n);
   end
   whist={wr,ar,dr};ahist={vr,rr};
   for(k=3;k>0;k=k-1)shist[k]=shist[k-1];shist[0]=ref_.sd;vhist={vhist[2:0],ref_.sv};
   reads=reads+(|vr);writes=writes+wr;n=n+1;
  end
  if(reads<100||writes<100)$fatal(1,"vacuous data traffic");
  // The legacy error ABI includes return-slot mismatch/core faults, even with healthy x43.
  force dut.u_ctl.r_bad=1'b1;
  repeat(12)@(posedge cs);#1;
  if(td[1028]!==1'b1 || fd!==1'b1)$fatal(1,"core diagnostic not reported to BOTH domains");
  release dut.u_ctl.r_bad;
  // Reset and isolate the opposite diagnostic direction.
  rt=0;rs=0;repeat(8)@(posedge ct);#1;rt=1;rs=1;
  repeat(12)@(posedge ct);force dut.x43f=1'b1;
  repeat(12)@(posedge ct);#1;
  if(fd!==1'b1 || td[1028]!==1'b1)$fatal(1,"serial diagnostic not reported to BOTH domains");
  release dut.x43f;
  $display("WFC_PIPELINE PASS seed%0d edges%0d reads%0d writes%0d request_delta1 core_return_delta4 serial_return_delta3 fault_both_directions",seed0,n,reads,writes);$finish;
 end
 always @(negedge cs)if(rs)begin
  if(n>40 && n<2450 && td[1027:2]!==thist[2])$fatal(1,"serial +3 mismatch %0d",n);
  for(integer j=2;j>0;j=j-1)thist[j]=thist[j-1];thist[0]=tr[1027:2];
  f=0;
  if($random(seed)%3==0)begin f[0]=1;f[527:513]=$unsigned($random(seed))%16384;for(integer j=0;j<16;j=j+1)f[1+32*j+:32]=$random(seed);end
  if($random(seed)%3==0)begin f[528]=1;f[543:529]=$unsigned($random(seed))%16384;f[558:544]=$unsigned($random(seed))%16384;f[559]=$random(seed);if(f[545:544]==f[530:529])f[545:544]=f[530:529]+2'd1;end
 end
endmodule
