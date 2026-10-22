`timescale 1ns/1ps
module tb_pool_native;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,start=0;wire busy,done,fault,rv,wv;wire[9:0]ra,wa;wire[7:0]wm;wire[255:0]wd,y32;wire[15:0]age;
 reg[127:0] mem[0:1023];reg[511:0] exp_cp[0:31];reg[31:0] exp32[0:511];
 reg[3:0] qv=0;reg[255:0] qd[0:3];
 ot_s81sl_cmp_pool dut(clk,rst_n,start,10'd0,10'd256,10'd692,busy,done,fault,rv,ra,qv[3],qd[3],wv,wa,wm,wd,y32,age);
 integer cyc=0,nread=0,nwrite=0,ngroup=0,bad=0,t0;
 always @(posedge clk)begin
  qv<={qv[2:0],rv};qd[0]<={mem[ra+1],mem[ra]};
  for(integer k=1;k<4;k=k+1)qd[k]<=qd[k-1];
  if(rv)nread=nread+1;
  if(wv)begin nwrite=nwrite+1;for(integer k=0;k<8;k=k+1)if(wm[k])mem[wa+k/4][32*(k%4)+:32]<=wd[32*k+:32];end
 end
 always @(negedge clk)begin
  cyc=cyc+1;
  if(rst_n && dut.lo_v[0])begin
   for(integer k=0;k<8;k=k+1)if(y32[32*k+:32]!==exp32[8*ngroup+k])begin
    if(bad<6)$display("POOL_MISMATCH feature %0d actual %h expected %h",8*ngroup+k,y32[32*k+:32],exp32[8*ngroup+k]);bad=bad+1;
   end
   ngroup=ngroup+1;
  end
 end
 initial begin
  $readmemh("img_main.mem",mem);$readmemh("exp_cp.mem",exp_cp);$readmemh("exp_cp32.mem",exp32);
  if($test$plusargs("SWAP_KV"))for(integer k=0;k<128;k=k+1)begin reg[127:0] tmp;tmp=mem[k];mem[k]=mem[256+k];mem[256+k]=tmp;end
  repeat(64)@(negedge clk);rst_n=1;repeat(128)@(negedge clk);
  start=1;t0=cyc;@(negedge clk);start=0;wait(done);@(negedge clk);
  for(integer k=0;k<512;k=k+1)if(mem[692+k/4][32*(k%4)+:32]!==exp_cp[k/16][32*(k%16)+:32])bad=bad+1;
  $display("POOL_RESULT cycles %0d reads %0d writes %0d groups %0d bad %0d fault %0d",cyc-t0,nread,nwrite,ngroup,bad,fault);
  if(bad || fault || nread!=256 || nwrite!=64 || ngroup!=64)$fatal(1,"POOL_NATIVE_FAIL");
  $display("POOL_NATIVE_PASS");$finish;
 end
 initial begin repeat(1200)@(negedge clk);$fatal(1,"POOL_NATIVE_FAIL timeout");end
endmodule
