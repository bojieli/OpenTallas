`timescale 1ns/1ps
module tb_owner_metadata;
 parameter integer MUT=0;
 reg clk=0;always #0.512 clk=~clk;
 reg rst_n=0,wv=0,rv=0;reg[4:0] wa=0,ra=0;reg[46:0] wd=0;
 wire[46:0] rd;wire rvalid,wdone;
 ot_hbm_owner_metadata_native #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),
  .write_v(wv),.write_addr(wa),.write_data(wd),.read_v(rv),.read_addr(ra),
  .read_data(rd),.read_valid(rvalid),.write_done(wdone));
 reg[46:0] refmem[0:31],wh[0:2];reg[4:0] wah[0:2],rah[0:2];
 reg[2:0] wvh=0,rvh=0;reg[46:0] half_ref=0,read_now=0;
 integer checks=0,phase,i,cycle;
 task automatic fail(input string s);begin $display("FAIL metadata %s phase=%0d cycle=%0d",s,phase,cycle);$fatal(1);end endtask
 task automatic tick;begin
  @(posedge clk);
  read_now=refmem[rah[1]];
  if(wvh[1])refmem[wah[1]]=wh[1];
  #0.01;
  if(rvalid!==rvh[2])fail("read valid age/reset");
  if(wdone!==wvh[1])fail("write commit age/reset");
  if(rvalid)begin if(rd!==half_ref)fail("generation/epoch/bank/ordinal/length identity");checks=checks+1;end
  half_ref=read_now;
  for(integer k=2;k>0;k=k-1)begin wh[k]=wh[k-1];wah[k]=wah[k-1];rah[k]=rah[k-1];end
  wh[0]=wd;wah[0]=wa;rah[0]=ra;wvh={wvh[1:0],wv};rvh={rvh[1:0],rv};
 end endtask
 initial begin
  for(phase=0;phase<8;phase=phase+1)begin
   @(negedge clk);rst_n=0;wv=0;rv=0;wvh=0;rvh=0;
   #0.02;if(rvalid!==0||wdone!==0)fail("occupied async reset");
   for(i=0;i<3;i=i+1)begin wh[i]=0;wah[i]=0;rah[i]=0;end
   repeat(3)@(posedge clk);@(negedge clk);rst_n=1;
   repeat(3)begin @(posedge clk);#0.01;if(rvalid||wdone)fail("release stale operation");end
   // Establish every real owner entry before any lookup.
   for(cycle=0;cycle<32;cycle=cycle+1)begin
    @(negedge clk);wv=1;wa=5'(cycle);wd={15'(phase+1),16'(cycle+123),16'(cycle*71+9)};tick();
   end
   for(cycle=32;cycle<4096;cycle=cycle+1)begin
    @(negedge clk);wv=(cycle%3==0);wa=5'(cycle*13+7);ra=(cycle%17==0)?wa:5'(cycle*19+11);rv=1;
    wd={15'(cycle^phase),16'(cycle*37),16'(cycle*23+phase)};tick();
   end
   @(negedge clk);#(0.02*phase);rst_n=0;#0.01;
   if(rvalid||wdone)fail("occupied asynchronous cancellation");
  end
  $display("PASS owner_metadata checks=%0d entries=32 width=47 read_edges=4 write_edges=3 reset_offsets=8 collision=read_first",checks);$finish;
 end
endmodule
