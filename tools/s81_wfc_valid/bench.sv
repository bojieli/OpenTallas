`timescale 1ns/1ps
module tb_wfc_valid;
 reg ct=1,cs=1,rt=0,rs=0;always #6 ct=~ct;always #8 cs=~cs;
 reg[559:0] f=0;reg[3:0] ev=0;reg[2047:0] ed=0;reg vmf=0;
 wire[1028:0] tr,td;wire wr,wd;wire[13:0] ar,ad;wire[511:0] dr,dd;
 wire[3:0] vr,vd;wire[55:0] rr,rd;wire fr,fd;
 dsfd_vm_static_wfc_valid_ref #(.RLAT(15),.RESPONSE_PAD(2)) ref_(cs,ct,cs,ct,rs,rt,ct,rt,cs,ct,ct,cs,rs,rt,rt,rs,cs,ct,cs,ct,rs,rt,rs,rt,rs,rt,f,tr,wr,ar,dr,vr,rr,ev,ed,vmf,fr);
 dsfd_vm_static_wfc #(.RLAT(15),.RESPONSE_PAD(2)) dut(cs,ct,cs,ct,rs,rt,ct,rt,cs,ct,ct,cs,rs,rt,rt,rs,cs,ct,cs,ct,rs,rt,rs,rt,rs,rt,f,td,wd,ad,dd,vd,rd,ev,ed,vmf,fd);
 integer seed=731,mode,k,n,checks=0,writes=0,reads=0;reg check=0;
 always @(posedge ct)begin #1;if(check)begin
  if({wd,ad,dd,vd,rd,fd}!=={wr,ar,dr,vr,rr,fr})$fatal(1,"valid-equivalence core mode%0d edge%0d",mode,n);
  if(dut.x34f!==ref_.x34f)$fatal(1,"valid-equivalence x34 fault");
  checks=checks+1;writes=writes+wd;reads=reads+(|vd);
 end end
 always @(negedge cs)if(check && td!==tr)$fatal(1,"valid-equivalence serial mode%0d edge%0d",mode,n);
 initial begin
  for(mode=0;mode<10;mode=mode+1)begin
   check=0;rt=0;rs=0;f=0;ev=0;vmf=0;ed=0;
   #100;#(47-($time%48));rt=1;rs=1;repeat(20)@(negedge cs);check=1;
   for(n=0;n<240;n=n+1)begin
    @(negedge cs);#1;
    for(k=0;k<17;k=k+1)f[32*k+:32]=$random(seed);f[559:544]=$random(seed);
    // Idle carries arbitrary payload including invalid rows and lane collision.
    f[0]=(mode==2 || mode==3 || mode==4 || mode==5);
    f[528]=(mode==1 || mode==3 || mode==4 || mode==6 || mode==7);
    if(mode<5)begin f[527]=0;f[543]=0;f[559]=1;f[558]=0;f[545:544]=f[530:529]+2'd1;end
    if(mode==5)f[527:513]=15'h4001;
    if(mode==6)f[543:529]=15'h4002;
    if(mode==7)begin f[543]=0;f[559]=1;f[558]=0;f[545:544]=f[530:529];end
    if(mode==8)vmf=1;
    if(mode==9)ev=$random(seed);
    for(k=0;k<64;k=k+1)ed[32*k+:32]=$random(seed);
   end
   repeat(24)@(negedge cs);
   if(mode==0 && (fd || td[1028]))$fatal(1,"idle arbitrary payload caused diagnostic");
   if(mode>=5 && mode<=9 && (!fd || !td[1028]))$fatal(1,"fault witness absent mode%0d",mode);
   $display("WFC_VALID_CASE PASS mode%0d",mode);
  end
  if(checks<2000 || writes<100 || reads<100)$fatal(1,"vacuous operation comparison");
  $display("WFC_VALID_EQUIVALENCE PASS checks%0d writes%0d reads%0d",checks,writes,reads);$finish;
 end
endmodule
