`timescale 1ps/1fs
module tb;
 reg clk=0;always #416.5 clk=~clk;
 reg phy_rst_n=0,ep_rst_n=0;
 reg[513:0]rx=0;reg[511:0]tx=0;
 wire[513:0]goodrx,badrx;wire[511:0]goodtx,badtx;
 reg[513:0]rh[0:3];reg[511:0]th[0:3];
 integer mut=0,n,checks=0,diffs=0,status_checks=0;
 initial if($value$plusargs("MUT=%d",mut))begin end
 wire[513:0]cin=(mut==1)?{rx[513:512],rx[255:0],rx[511:256]}:rx;
 SPB0_source good(clk,phy_rst_n,ep_rst_n,cin[511:0],tx,cin[513:512],goodrx[511:0],goodtx,goodrx[513:512]);
 SPB0_source_wrong_reset bad(clk,phy_rst_n,ep_rst_n,rx[511:0],tx,rx[513:512],badrx[511:0],badtx,badrx[513:512]);
 always@(posedge clk)begin
  rh[0][511:0]<=rx[511:0];rh[0][513:512]<=ep_rst_n?rx[513:512]:0;th[0]<=tx;
  for(integer j=1;j<4;j=j+1)begin rh[j][511:0]<=rh[j-1][511:0];rh[j][513:512]<=ep_rst_n?rh[j-1][513:512]:0;th[j]<=th[j-1];end
 end
 initial begin
  for(n=0;n<12000;n=n+1)begin
   @(negedge clk);
   phy_rst_n=n>5 && !(n>=4070&&n<4079) && !(n>=8090&&n<8095);
   ep_rst_n=n>12 && !(n>=4000&&n<4007) && !(n>=8000&&n<8004);
   for(integer k=0;k<16;k=k+1)begin rx[k*32+:32]=$urandom;tx[k*32+:32]=$urandom;end
   rx[513:512]=$urandom;
   @(posedge clk);#1;
   if(n>4)begin
    checks=checks+1;if(phy_rst_n!=ep_rst_n)status_checks=status_checks+1;
    if(((mut==3)?badrx:goodrx)!==rh[(mut==2)?2:3] || ((mut==3)?badtx:goodtx)!==th[3])diffs=diffs+1;
   end
  end
  if(mut==0&&diffs!=0)$fatal(1,"native reset mismatch %0d",diffs);
  if(mut!=0&&diffs==0)$fatal(1,"native reset mutant escaped %0d",mut);
  $display("SPB_RESET %s mut=%0d checks=%0d different_reset_edges=%0d diffs=%0d period833ps actualRTL+4/+4 model+2/+0",mut==0?"PASS":"CAUGHT",mut,checks,status_checks,diffs);$finish;
 end
endmodule
