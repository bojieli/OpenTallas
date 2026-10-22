`timescale 1ns/1ps
module tb_tx_miter;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rn=0,reference_entry=0;
 // Reference has two reset stages, production n32 has the actual three-stage relay.
 // This explicit reference-only entry aligns the booked boot age; no production source or data edge changes.
 always @(posedge ck or negedge rn)if(!rn)reference_entry<=0;else reference_entry<=1;
 reg[275:0]vi=0,vo=0;
 wire[275:0]lo,ref_lo;wire[15:0]st,ref_st;
 dsdv_idx_tx_n32 #(.D(8192),.IB(64),.SRAM_MACRO(1),.MUT(MUT))dut(.ck(ck),.rst(rn),.vi(vi),.vo(vo),.lo(lo),.st(st));
 dsdv_idx_tx #(.D(8192),.IB(64),.SRAM_MACRO(1))reference_dut(.ck(ck),.rst(reference_entry),.vi(vi),.vo(vo),.lo(ref_lo),.st(ref_st));
 integer cycle=0,checks=0,beats=0,done_n=0,epochs=0;
 always @(posedge ck)begin
  #1;cycle=cycle+1;
  if(st!==ref_st||lo[0]!==ref_lo[0]||(ref_lo[0]&&lo!==ref_lo))begin
   $display("TX_MISMATCH cycle=%0d mut=%0d status=%b valid=%b payload=%b",cycle,MUT,st!==ref_st,lo[0]!==ref_lo[0],ref_lo[0]&&lo!==ref_lo);
   $fatal(1,"TX_MITER_FAIL");
  end
  checks=checks+17+(ref_lo[0]?275:0);
  if(ref_lo[0])beats=beats+1;
  if(ref_st[3])done_n=done_n+1;
 end
 task drive(input[275:0]v,input[275:0]o);begin @(negedge ck);vi=v;vo=o;end endtask
 task idle(input integer n);begin repeat(n)drive(0,0);end endtask
 task packet(input[511:0]w);reg[275:0]a;begin
  a=0;a[0]=1;a[3:1]=5;a[275:20]=w[255:0];drive(0,a);
  a[6]=1;a[275:20]=w[511:256];drive(0,a);idle(2);
 end endtask
 reg[275:0]a;reg[185:0]p;reg[511:0]w;
 initial begin
  for(integer epoch=0;epoch<2;epoch=epoch+1)begin
   @(negedge ck);rn=0;vi=0;vo=0;idle(8);
   @(negedge ck);rn=1;epochs=epochs+1;idle(16);
   // Write four lane ranges, two 16-score windows each, with distinct fields and a real lane-valid mask.
   for(integer lane=0;lane<4;lane=lane+1)begin
    a=0;a[0]=1;a[3:1]=4;a[5:4]=2'(lane);a[7]=1;a[19:16]=1;a[39:20]=20'(lane*32);drive(a,0);idle(3);
    for(integer win=0;win<2;win=win+1)begin
     a=0;a[0]=1;a[3:1]=4;a[5:4]=2'(lane);
     for(integer x=0;x<16;x=x+1)a[20+16*x+:16]=16'(epoch*8192+lane*1024+win*256+x*7+1);
     drive(a,0);a=0;a[0]=1;a[3:1]=4;a[5:4]=2'(lane);a[6]=1;a[35:20]=16'hffff;drive(a,0);idle(4);
    end
   end
   idle(16);
   p=0;p[7:0]=8'h5c;p[10:8]=2;p[20:16]=8;p[22:21]=0;p[30:23]=8'h77;p[40:31]=64;p[60:41]=0;p[68:61]=8'h45;p[84:69]=200;p[87:85]=4;p[99:88]=200;
   a=0;a[0]=1;a[3:1]=0;a[21+:186]=p;drive(0,a);idle(8);
   for(integer idxword=0;idxword<4;idxword=idxword+1)begin
    w=0;w[511:508]=3;w[507:500]=8'h45;w[335:320]=16'hffff;
    for(integer x=0;x<16;x=x+1)w[20*x+:20]=20'(idxword*16+x);
    packet(w);
   end
   w=0;w[511:508]=4;w[507:500]=8'h45;packet(w);idle(1100);
   if(!st[3]||st[0])$fatal(1,"TX_JOB_COVERAGE_FAIL epoch=%0d st=%h",epoch,st);
  end
  $display("TX_STATS cycles %0d checks %0d epochs %0d beats %0d done_edges %0d",cycle,checks,epochs,beats,done_n);
  if(beats<10||done_n<2)$fatal(1,"TX_TRAFFIC_COVERAGE_FAIL");
  $display("TX_MITER_PASS");$finish;
 end
endmodule
