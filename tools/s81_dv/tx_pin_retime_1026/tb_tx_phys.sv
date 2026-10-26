`timescale 1ns/1ps
module tb_tx_miter;
 parameter integer MUT=0;
 parameter integer RDL=0,WDL=0;  // STW-S81c-COLLA 10-22: score-store read capture / write landing
 parameter integer WDC=0,SCS=0;  // STW-S81c-COLLA2-TX 10-22: write-port column copy / slot-count carry-select
 parameter integer RIL=0,RHP=0;  // STW-S81c-COLLA2 10-22: read-issue landing / FIFO head prefetch
 parameter integer REF_LPX=0,SPLIT=0;   // STW-S81c-TOK4 10-22: reference lookup pipe extension (the booked RIL edge)
 reg ck=0;always #5 ck=~ck;
 reg rn=0,reference_entry=0;
 // Reference has two reset stages, production n32 has the actual three-stage relay.
 // This explicit reference-only entry aligns the booked boot age; no production source or data edge changes.
 always @(posedge ck or negedge rn)if(!rn)reference_entry<=0;else reference_entry<=1;
 reg[275:0]vi=0,vo=0;
 wire[275:0]lo,ref_lo;wire[15:0]st,ref_st;

 wire[267:0]pv;wire[260:0]po;wire[272:0]pl,ml;wire[11:0]ps,ms;
 wire[275:0]mut_lo;wire[15:0]mut_st;
 genvar g;
 generate
  for(g=0;g<268;g=g+1)assign pv[g]=vi[g<8?g:g+8];
  for(g=0;g<261;g=g+1)assign po[g]=vo[g<4?g:(g==4?6:g+15)];
  for(g=0;g<276;g=g+1)begin
   if(g==1||g==2||g==19)begin assign lo[g]=0;assign mut_lo[g]=0;end
   else begin assign lo[g]=pl[g==0?0:(g<19?g-2:g-3)];assign mut_lo[g]=ml[g==0?0:(g<19?g-2:g-3)];end
  end
  for(g=0;g<16;g=g+1)begin
   if(g>=4&&g<=7)begin assign st[g]=0;assign mut_st[g]=0;end
   else begin assign st[g]=ps[g<4?g:g-4];assign mut_st[g]=ms[g<4?g:g-4];end
  end
 endgenerate
 dsdv_idx_tx_n32_phys #(.SRAM_MACRO(1))dut(.ck(ck),.rst(rn),.vi(pv),.vo(po),.lo(pl),.st(ps));
 dsdv_idx_tx_n32_phys #(.SRAM_MACRO(1),.PHYS_MUT(1))mut(.ck(ck),.rst(rn),.vi(pv),.vo(po),.lo(ml),.st(ms));
 integer mutant_edges=0;
 always @(posedge ck)begin #1;if(mut_lo!==ref_lo||mut_st!==ref_st)mutant_edges=mutant_edges+1;end

 dsdv_idx_tx_n32__reference #(.D(8192),.IB(64),.SRAM_MACRO(1))reference_dut(.ck(ck),.rst(rn),.vi(vi),.vo(vo),.lo(ref_lo),.st(ref_st));
 integer cycle=0,checks=0,beats=0,done_n=0,epochs=0;
 always @(posedge ck)begin
  #1;cycle=cycle+1;
  if(st!==ref_st||lo!==ref_lo)begin
   $display("TX_MISMATCH cycle=%0d mut=%0d status=%b valid=%b payload=%b st=%h ref_st=%h lo0=%b",cycle,MUT,st!==ref_st,lo[0]!==ref_lo[0],ref_lo[0]&&lo!==ref_lo,st,ref_st,lo[0]);
   $fatal(1,"TX_MITER_FAIL");
  end
  checks=checks+17+(ref_lo[0]?275:0);
  if(ref_lo[0])beats=beats+1;
  if(ref_st[3])done_n=done_n+1;
 end
 task drive(input[275:0]v,input[275:0]o);begin @(negedge ck);vi=v;vo=o;vi[15:8]=$urandom;vo[19:7]=$urandom;vo[5:4]=$urandom;end endtask
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
   // Write all eight physical score banks, two widely separated 16-score windows per lane, with distinct fields and a real lane-valid mask.
   for(integer lane=0;lane<4;lane=lane+1)begin
    for(integer win=0;win<2;win=win+1)begin
     a=0;a[0]=1;a[3:1]=4;a[5:4]=2'(lane);a[7]=1;a[19:16]=win==0?1:6;a[39:20]=20'(lane*32768+win*16384);drive(a,0);idle(3);
     a=0;a[0]=1;a[3:1]=4;a[5:4]=2'(lane);
     for(integer x=0;x<16;x=x+1)a[20+16*x+:16]=16'(epoch*8192+lane*1024+win*256+x*7+1);
     drive(a,0);a=0;a[0]=1;a[3:1]=4;a[5:4]=2'(lane);a[6]=1;a[35:20]=16'hffff;drive(a,0);idle(4);
    end
   end
   // STW-S81c-TOK4 10-22: partial-mask rewrite of lane 0 window 0 (the window the lookups read): new scores under lane
   // mask 16'h5a5a, so lookups of masked-OUT positions must still return the first write (catches a write-mask mutant).
   a=0;a[0]=1;a[3:1]=4;a[5:4]=2'd0;a[7]=1;a[19:16]=1;a[39:20]=20'd0;drive(a,0);idle(3);
   a=0;a[0]=1;a[3:1]=4;a[5:4]=2'd0;
   for(integer x=0;x<16;x=x+1)a[20+16*x+:16]=16'(16'h4000+epoch*8192+x*13+5);
   drive(a,0);a=0;a[0]=1;a[3:1]=4;a[5:4]=2'd0;a[6]=1;a[35:20]=16'h5a5a;drive(a,0);idle(4);
   idle(16);
   p=0;p[7:0]=8'h5c;p[10:8]=2;p[20:16]=8;p[22:21]=0;p[30:23]=8'h77;p[40:31]=64;p[60:41]=0;p[68:61]=8'h45;p[84:69]=200;p[87:85]=4;p[99:88]=200;
   a=0;a[0]=1;a[3:1]=0;a[21+:186]=p;drive(0,a);idle(8);
   for(integer idxword=0;idxword<4;idxword=idxword+1)begin
    w=0;w[511:508]=3;w[507:500]=8'h45;w[335:320]=16'hffff;
    for(integer x=0;x<16;x=x+1)w[20*x+:20]=20'(((idxword*16+x)/8)*16384+2*((idxword*16+x)%8)+(epoch%2));
    packet(w);
   end
   w=0;w[511:508]=4;w[507:500]=8'h45;packet(w);idle(1100);
   if(!st[3]||st[0])$fatal(1,"TX_JOB_COVERAGE_FAIL epoch=%0d st=%h",epoch,st);
  end
  $display("TX_STATS cycles %0d checks %0d epochs %0d beats %0d done_edges %0d",cycle,checks,epochs,beats,done_n);
  if(beats<40||done_n<2)$fatal(1,"TX_TRAFFIC_COVERAGE_FAIL");
  $display("TX_PHYS_MUTANT_EDGES %0d",mutant_edges);if(mutant_edges==0)$fatal(1,"MUTANT_NOT_CAUGHT");$display("TX_MITER_PASS");$finish;
 end
endmodule
