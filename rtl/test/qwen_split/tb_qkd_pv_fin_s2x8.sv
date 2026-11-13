`timescale 1ns/1ps
// KV-PVFIN-1 2026-11-13: lock-step equivalence bench of the lane-sliced pair qkd_pv_fin_s2x8 (2 x qkd_pv_fin_s8, 8 lanes
// each) against the unsliced qkd_pv_fin_s on the SAME pins, every edge (declared latency change: 0 cycles).
// Gold = qkd_pv_fin_s (MUT 0), whose own proof against the reference finalize is tb_qkd_pv_fin_s.sv.
// Stimulus per command (random, +SEED): calendar P0 / P1 (|P0 - P1| <= SKEW) and R in the three STRETCH regimes
// (R <= max(P0, P1); max < R <= max + 8; R = max + 9 .. max + 1108), random fp32 operands (normal range, zeros, exact
// cancellations, signs) and reciprocals, the static beat streams; and one injected class per faulty command:
//   1 wrong beat index   2 wrong epoch          3 missing beat          4 valid off its slot (idle extra beat)
//   5 start while active 6 unmeetable calendar  7 non-finite operand in ONE slice's lanes (lo or hi only)
//   8 multiplier overflow in one slice's lanes  9 warm reset mid-command  10 reciprocal epoch wrong
// After a fault both designs are dead until reset: the bench resets (warm) and goes on.
// Checks (every posedge, after it settles, DUT at edge t vs gold at edge t - 1: the declared +1 cycle): out_valid and
// fault equal; out_beat and out_epoch equal while no fault was seen since the last reset, out_data equal while no fault
// was seen since the last product beat (out_data has no reset in either design), and all three on every out_valid beat.
// +SHIFT=0 / +SHIFT=2 (a wrongly declared 0 / +2 cycles) must FAIL; MUT 1..3 (in the slices) and
// -DOT_PVFIN_S2X8_MUTANT_LANESWAP must FAIL.
module tb_qkd_pv_fin_s2x8;
 parameter integer MUT=0;
 parameter integer SKEW=1;
 parameter integer IN_STAGE=1;
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg start=0;reg [15:0] epoch=0;reg [47:0] cal=0;
 reg p0v=0,p1v=0,rv=0;reg [4:0] p0b=0,p1b=0;reg [15:0] p0e=0,p1e=0,rep=0;reg [511:0] p0d=0,p1d=0;reg [127:0] rz=0;
 wire gv,gf,dv,df;wire [4:0] gb,db;wire [15:0] ge,de;wire [511:0] gd,dd;
 qkd_pv_fin_s #(.SKEW(SKEW),.MUT(0)) u_gold(.ck(ck),.rst_n(rst_n),.start(start),.epoch(epoch),.cal(cal),
  .p0_valid(p0v),.p0_beat(p0b),.p0_epoch(p0e),.p0_data(p0d),.p1_valid(p1v),.p1_beat(p1b),.p1_epoch(p1e),.p1_data(p1d),
  .rz_valid(rv),.rz_epoch(rep),.rz(rz),.out_valid(gv),.out_beat(gb),.out_epoch(ge),.out_data(gd),.fault(gf));
 qkd_pv_fin_s2x8 #(.SKEW(SKEW),.MUT(MUT),.IN_STAGE(IN_STAGE)) u_dut(.ck(ck),.rst_n(rst_n),.start(start),.epoch(epoch),.cal(cal),
  .p0_valid(p0v),.p0_beat(p0b),.p0_epoch(p0e),.p0_data(p0d),.p1_valid(p1v),.p1_beat(p1b),.p1_epoch(p1e),.p1_data(p1d),
  .rz_valid(rv),.rz_epoch(rep),.rz(rz),.out_valid(dv),.out_beat(db),.out_epoch(de),.out_data(dd),.fault(df));
 // ---------------- checker ----------------
 // The DUT is declared +IN_STAGE cycles (stage-i input flops): at edge t it must equal gold at edge t - SHIFT, SHIFT =
 // IN_STAGE by default.
 // rst_n is asynchronous in both designs: while rst_n is low the expectation is the reset value (valid / fault / beat /
 // epoch 0), whatever gold showed SHIFT edges earlier.  +SHIFT=0 and +SHIFT=2 (a wrongly declared latency) must FAIL.
 integer SHIFT=IN_STAGE,errs=0,edges=0,vbeats=0,pay_edges=0,seenf=0,dstale=0,hn=0,k_;
 reg h_v[0:2],h_f[0:2];reg [4:0] h_b[0:2];reg [15:0] h_e[0:2];reg [511:0] h_d[0:2];
 always @(posedge ck)begin
  #0.5;
  edges=edges+1;
  for(k_=2;k_>0;k_=k_-1)begin h_v[k_]=h_v[k_-1];h_f[k_]=h_f[k_-1];h_b[k_]=h_b[k_-1];h_e[k_]=h_e[k_-1];h_d[k_]=h_d[k_-1];end
  h_v[0]=gv;h_f[0]=gf;h_b[0]=gb;h_e[0]=ge;h_d[0]=gd;
  if(hn<2)hn=hn+1;
  if(hn>=SHIFT)begin : chk
   reg xv,xf;reg [4:0] xb;reg [15:0] xe;reg [511:0] xd;
   xv=h_v[SHIFT];xf=h_f[SHIFT];xb=h_b[SHIFT];xe=h_e[SHIFT];xd=h_d[SHIFT];
   if(!rst_n)begin xv=0;xf=0;xb=0;xe=0;dstale=1;end   // reset: out_data stale from this edge on (see below)
   if(dv!==xv||df!==xf)begin errs=errs+1;if(errs<8)$display("MISMATCH edge %0d valid %b/%b fault %b/%b",edges,xv,dv,xf,df);end
   if((seenf==0&&!xf||xv)&&(db!==xb||de!==xe||(dstale==0||xv)&&dd!==xd))begin   // the fault edge itself: payload not qualified
    errs=errs+1;if(errs<8)$display("MISMATCH edge %0d payload beat %0d/%0d epoch %h/%h data %0s",edges,xb,db,xe,de,dd===xd?"eq":"DIFF");
   end
   if(seenf==0)pay_edges=pay_edges+1;
   if(xv)vbeats=vbeats+1;
   if(xf||df)begin seenf=1;dstale=1;end
   if(!rst_n)begin seenf=0;dstale=1;end  // out_valid / out_beat / out_epoch / fault are reset; out_data (no reset, as
   // qkd_pv_fin_s) is stale across a reset: a reset may cancel the last product write that gold made SHIFT edges earlier
   if(xv&&!xf)dstale=0;      // keeps a post-fault value until the next product beat rewrites it
  end
 end
 // ---------------- stimulus ----------------
 integer seed=1,NCMD=400,cmd,okc=0,STRETCH=1;
 initial begin : stall_guard #8000000; $display("PVFIN_S2X8 FAIL stalled"); $finish; end
 integer kinds[0:10];
 function [31:0] rnd_fp(input integer kind);
  reg [31:0] r;
  begin
   r=$random(seed);
   case(kind%8)
    0:rnd_fp=32'd0;
    1:rnd_fp={r[31],8'd127+{4'd0,r[3:0]}-8'd8,r[22:0]};
    default:rnd_fp={r[31],8'd100+{2'd0,r[29:24]},r[22:0]};
   endcase
  end
 endfunction
 task idle_inputs;begin p0v=0;p1v=0;rv=0;start=0;end endtask
 task warm_reset;begin @(negedge ck);idle_inputs;rst_n=0;repeat(1+($random(seed)&3))@(negedge ck);rst_n=1;repeat(2)@(negedge ck);end endtask
 task one(input integer c);
  integer a0,a1,ar,last,kend,k,b,l,e,inj,at,lane0,sl;
  reg [511:0] w0,w1;
  begin
   inj=(($random(seed)&15)<9)?0:1+(($random(seed)&255)%10);
   a0=1+($random(seed)&31);a1=a0+(($random(seed)&7)%(2*SKEW+1))-SKEW;if(a1<1)a1=1;
   last=(a0>a1)?a0:a1;ar=1+(($random(seed)&255)%last);
   if(STRETCH!=0&&c%3==1)ar=last+1+(($random(seed)&255)%8);
   if(STRETCH!=0&&c%3==2)ar=last+9+(($random(seed)&16'hffff)%1100);
   kend=((ar>last)?ar:last)+7+2+6+32+4;
   e=$random(seed)&16'hffff;
   if(inj==6)begin case($random(seed)&3) 0:a0=0; 1:a1=a0+SKEW+1; 2:ar=0; default:ar=16'hfff0; endcase end
   at=1+(($random(seed)&255)%(kend>2?kend-1:1));
   sl=$random(seed)&1;lane0=8*sl+(($random(seed)&255)%8);   // the slice (lo / hi) a lane-only fault hits
   for(k=0;k<4;k=k+1)rz[32*k+:32]={1'b0,8'd120+{5'd0,k[2:0]},23'($random(seed))};
   if(inj==8)rz={4{32'h5f800000}};                            // 2^64 reciprocals: only the 2^127 sums (one slice) overflow
   @(negedge ck);start=1;epoch=e;cal={16'(ar),16'(a1),16'(a0)};
   @(negedge ck);start=0;
   for(k=1;k<=kend;k=k+1)begin
    for(b=0;b<16;b=b+1)begin
     w0[32*b+:32]=rnd_fp($random(seed)&255);
     w1[32*b+:32]=(($random(seed)&7)==0)?{~w0[32*b+31],w0[32*b+:31]}:rnd_fp($random(seed)&255);
    end
    if(inj==8)for(b=0;b<16;b=b+1)if(b/8==sl)begin w0[32*b+:32]=32'h7e800000;w1[32*b+:32]=32'h7e800000;end
    p0v=(k>=a0&&k<a0+32);p0b=5'(k-a0);p0e=e;p0d=w0;
    p1v=(k>=a1&&k<a1+32);p1b=5'(k-a1);p1e=e;p1d=w1;
    rv=(k==ar);rep=e;
    if(inj==1&&k==a0+(at%32))p0b=p0b+5'd3;
    if(inj==2&&k==a1+(at%32))p1e=e^16'h40;
    if(inj==3&&k==a0+(at%32))p0v=0;
    if(inj==4&&k==a1+32+(at%3))p1v=1;
    if(inj==5&&k==at)start=1;
    if(inj==7&&k==a0+(at%32))p0d[32*lane0+:32]=32'h7f800000|{9'd0,23'($random(seed)&1)};   // inf / NaN in one lane
    if(inj==10&&k==ar)rep=e^16'h1;
    if(inj==9&&k==at)begin warm_reset;k=kend+1;end
    else begin @(negedge ck);start=0;end
   end
   idle_inputs;
   repeat(($random(seed)&7))@(negedge ck);
   kinds[inj]=kinds[inj]+1;
   if(gf||df)warm_reset;else if(inj==0)okc=okc+1;
  end
 endtask
 integer i;
 initial begin
  for(i=0;i<=10;i=i+1)kinds[i]=0;
  if($value$plusargs("SEED=%d",seed));if($value$plusargs("N=%d",NCMD));if($value$plusargs("SHIFT=%d",SHIFT));
  if($value$plusargs("STRETCH=%d",STRETCH));
  repeat(3)@(negedge ck);rst_n=1;repeat(2)@(negedge ck);
  for(cmd=0;cmd<NCMD;cmd=cmd+1)one(cmd);
  repeat(20)@(negedge ck);
  $display("COVER healthy %0d inj1..10 %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d edges %0d valid_beats %0d payload_edges %0d",
   okc,kinds[1],kinds[2],kinds[3],kinds[4],kinds[5],kinds[6],kinds[7],kinds[8],kinds[9],kinds[10],edges,vbeats,pay_edges);
  if(errs==0&&okc>=NCMD/3&&vbeats>=32*okc)$display("PVFIN_S2X8 PASS mut=%0d skew=%0d in_stage=%0d seed=%0d shift=%0d",MUT,SKEW,IN_STAGE,seed,SHIFT);
  else $display("PVFIN_S2X8 FAIL mut=%0d skew=%0d in_stage=%0d seed=%0d shift=%0d errs=%0d",MUT,SKEW,IN_STAGE,seed,SHIFT,errs);
  $finish;
 end
endmodule
