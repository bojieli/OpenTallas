`timescale 1ns/1ps
module tb_return256;
 reg ck=0;always #5 ck=~ck;
 reg rn=0;reg[1:0] rv;reg[3:0] rl,ev;reg[2047:0] ed;
 wire av,bv,af,bf;wire[1025:0]ad,bd;reg[1:0]fq;integer n,j,seed=1,checks=0;
 dsfd_vm_wfc_return #(.RESPONSE_PAD(2)) refold(.ck(ck),.rn(rn),.return_valid(rv),.return_lane(rl),.e_v(ev),.e_d(ed),.s_v(av),.s_d(ad),.r_bad(af));
 dsfd_vm_wfc_return_split256 dut(.ck({3{ck}}),.rn({3{rn}}),.return_valid(rv),.return_lane(rl),.e_v(ev),.e_d(ed),.s_v(bv),.s_d(bd),.r_bad(bf));
 always @(posedge ck)begin fq<={fq[0],af};end
 initial begin
  if($value$plusargs("seed=%d",seed))begin end
  fq=0;rv=0;rl=0;ev=0;ed=0;
  for(n=0;n<1600;n=n+1)begin
   if(n%200==0)begin release dut.lo.r_bad;release dut.hi.r_bad;end
   if(n%200==145)begin
    // Isolate each actual slice's diagnostic output in alternate reset epochs.
    // The other copy must still reach the actual native sticky join.
    if((n/200)%2==0)force dut.lo.r_bad=1'b0;
    else force dut.hi.r_bad=1'b0;
   end
   @(negedge ck);rn=(n%200>=4);rv=$random(seed);rl=$random(seed);
   ev=(rv[0]?(4'b1<<rl[1:0]):0)|(rv[1]?(4'b1<<rl[3:2]):0);
   // Include malformed actual replies after first clean reset epoch.
   if(n%200>150&&n%11==0)ev=$random(seed);
   for(j=0;j<64;j=j+1)ed[j*32+:32]=$random(seed);
   @(posedge ck);#1;
   if(n%200>12)begin
    if(av!==bv||ad!==bd)$fatal(1,"data mismatch edge%0d",n);
    if(bf!==fq[1])$fatal(1,"fault latency mismatch edge%0d old%0b new%0b",n,fq[1],bf);
    checks=checks+1;
   end
  end
  $display("RETURN256 PASS checks=%0d",checks);$finish;
 end
endmodule
