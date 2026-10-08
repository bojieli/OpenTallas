`timescale 1ns/1ps
// Gate link_credit_rtt: two ot_qwen_die_hub_fr endpoints (one active lane each) joined by HOPS actual
// ot_qwen_die_link_fwd_full_tmr stations (forwarded clocks, independent clock phases), streaming N words each way
// as fast as the native credits allow.  Exact checks: every word delivered once, in order, bit-exact (payload
// {x[509:0],2'b00}); no native fault; drained invariants (link credits back to CR, ar credits back to ARC, all
// buffers empty).  Reports the measured credit round trip and the steady-state rate (words a cycle) between the
// first and last delivered word.  STALLS counts source cycles with a word but no link credit after the first
// credit return.  CR = 4 reproduces the predecessor's window (rate ~ 4/118).
// NEG (each must FAIL with the named native cause; the bench prints EXPECTED_FAULT then $fatal):
//   1 link credit UNDERFLOW: A's send forced whenever its skid holds a word (credits ignored) while B's consumer
//     back-pressures -> A's credit counter goes below zero (cause[3] at A) AND B's receive buffer overflows
//     (cause[1] at B); the bench requires both.
//   2 link credit OVERFLOW: corrupted Gray credit count into A (returned > outstanding) -> cause[3] at A.
//   3 ar credit overflow: A's consumer returns credits it was never given -> cause[4] at A.
//   4 x3 skid overflow: A's source ignores x3 credits -> cause[0] at A.
module tb_qwen_link_fullrate;
 parameter integer HOPS=54, N=4096, NEG=0, CR=128, OD=8, XS=8, ARC=4, BP=0;
 reg ca=0,cb=0,por=1,go=0;
 always #5 ca=~ca;
 initial begin #1.3;forever #5 cb=~cb;end
 wire [2111:0] alo,blo;
 wire [527:0] ab[0:HOPS],ba[0:HOPS];
 wire ac[0:HOPS],bc[0:HOPS];
 assign ab[0]=alo[527:0];assign ba[HOPS]=blo[527:0];
 assign ac[0]=ca;assign bc[HOPS]=cb;
 reg bad_gray=0;
 wire [527:0] into_a=bad_gray?{ba[0][527:5],4'b1000,ba[0][0]}:ba[0];
 genvar h;generate for(h=0;h<HOPS;h=h+1)begin:path
  ot_qwen_die_link_fwd_full_tmr #(.NL(1),.ENABLE(1)) r(
    .rst_n(por),.fclk_ab_i(ac[h]),.fclk_ab_o(ac[h+1]),
    .fclk_ba_i(bc[h+1]),.fclk_ba_o(bc[h]),
    .a_i(ab[h]),.b_o(ab[h+1]),.b_i(ba[h+1]),.a_o(ba[h]));
 end endgenerate
 reg av=0,bv=0,acr=0,bcr=0;
 reg [511:0] ad=0,bd=0;
 reg [10:0] atag=0,btag=0;
 wire axcr,bxcr,aov,bov,af,bf;
 wire [5:0] afc,bfc;
 wire [511:0] aod,bod;
 ot_qwen_die_hub_fr #(.CR(CR),.OD(OD),.XS(XS),.ARC(ARC)) A(.ck(ca),.rst_n(por),.fck({{3{cb}},bc[0]}),.l_i({1584'b0,into_a}),.l_o(alo),
  .x3_v(av),.x3_d(ad),.x3_tag(atag),.x3_cr(axcr),.ar_v(aov),.ar_d(aod),.ar_cr(acr),.fault(af),.fault_cause(afc));
 ot_qwen_die_hub_fr #(.CR(CR),.OD(OD),.XS(XS),.ARC(ARC)) B(.ck(cb),.rst_n(por),.fck({{3{ca}},ac[HOPS]}),.l_i({1584'b0,ab[HOPS]}),.l_o(blo),
  .x3_v(bv),.x3_d(bd),.x3_tag(btag),.x3_cr(bxcr),.ar_v(bov),.ar_d(bod),.ar_cr(bcr),.fault(bf),.fault_cause(bfc));
 function automatic [511:0] word(input integer side,epoch,index);
  reg[511:0] x;reg[31:0] v;integer j;
  begin v=32'hbc213a59^(side*32'h951bacd1)^(epoch<<20)^index;
   for(j=0;j<16;j=j+1)begin v=v^(v<<13);v=v^(v>>17);v=v^(v<<5);x[j*32+:32]=v;end
   x[511:510]=0;word=x;
  end
 endfunction
 function automatic [511:0] delivered(input integer side,epoch,index);
  reg[511:0] x;begin x=word(side,epoch,index);delivered={x[509:0],2'b00};end
 endfunction
 integer epoch=0,acred=XS,bcred=XS,asrc=0,bsrc=0,agot=0,bgot=0,aowe=0,bowe=0;
 integer aticks=0,bticks=0,asent=0,bsent=0;
 integer afirst=-1,areturn=-1,bfirst=-1,breturn=-1;
 integer astalls=0,bstalls=0,checks=0,arx0=-1,arx1=-1,brx0=-1,brx1=-1,amaxin=0,bmaxin=0;
 integer bpop=0,apop=0;
 always @(negedge ca) if(go)begin
  aticks=aticks+1;
  if(axcr)acred=acred+1;
  av=0;acr=0;
  if(alo[0])begin asent=asent+1;if(afirst<0)afirst=aticks;end
  if(B.g_rx[0].u_rx.i_cr)bpop=bpop+1;
  if(asent-bpop>amaxin)amaxin=asent-bpop;
  if(afirst>=0 && areturn<0 && A.lseen[0]!=0)areturn=aticks;
  if(aov)begin
   if(agot>=N || aod!==delivered(1,epoch,agot))$fatal(1,"DATA_MISMATCH sideA index=%0d",agot);
   if(agot==0)arx0=aticks; arx1=aticks;
   agot=agot+1;aowe=aowe+1;checks=checks+1;
  end
  if(NEG==3 && aticks==3)acr=1;
  else if(aowe>0 && !(BP==1 && aticks>=400 && aticks<900))begin acr=1;aowe=aowe-1;end
  if(asrc<N && (acred>0 || NEG==4))begin
   av=1;ad=word(0,epoch,asrc);atag=asrc;asrc=asrc+1;acred=acred-1;
  end
  if(A.sne && A.lc[0]==0 && areturn>=0)astalls=astalls+1;
  if(af || bf)begin
   if(NEG!=1 || bfc[1])begin
   $display("NATIVE_FAULT a=%0d causeA=%b b=%0d causeB=%b tick=%0d",af,afc,bf,bfc,aticks);
   if((NEG==1 && bfc[1] && afc[3]) || (NEG==2 && afc[3]) || (NEG==3 && afc[4]) || (NEG==4 && afc[0]))
    $display("EXPECTED_FAULT NEG=%0d",NEG);
   $fatal(1,"FAIL link_fullrate NEG=%0d",NEG);
   end
  end
 end
 always @(negedge cb) if(go)begin
  bticks=bticks+1;
  if(bxcr)bcred=bcred+1;
  bv=0;bcr=0;
  if(blo[0])begin bsent=bsent+1;if(bfirst<0)bfirst=bticks;end
  if(A.g_rx[0].u_rx.i_cr)apop=apop+1;
  if(bsent-apop>bmaxin)bmaxin=bsent-apop;
  if(bfirst>=0 && breturn<0 && B.lseen[0]!=0)breturn=bticks;
  if(bov)begin
   if(bgot>=N || bod!==delivered(0,epoch,bgot))$fatal(1,"DATA_MISMATCH sideB index=%0d",bgot);
   if(bgot==0)brx0=bticks; brx1=bticks;
   bgot=bgot+1;bowe=bowe+1;checks=checks+1;
  end
  if(bowe>0 && !((BP==1 || NEG==1 || NEG==4) && bticks>=400 && bticks<900))begin bcr=1;bowe=bowe-1;end
  if(bsrc<N && bcred>0)begin bv=1;bd=word(1,epoch,bsrc);btag=bsrc;bsrc=bsrc+1;bcred=bcred-1;end
  if(B.sne && B.lc[0]==0 && breturn>=0)bstalls=bstalls+1;
 end
 // NEG 1: A transmits without link credit
 initial if(NEG==1)begin #2000; force A.send=A.sne; end
 task automatic cold_start;
  begin
   go=0;av=0;bv=0;acr=0;bcr=0;por=0;
   repeat(8)@(negedge ca);por=1;
   repeat(HOPS+25)@(negedge ca);
   acred=XS;bcred=XS;asrc=0;bsrc=0;agot=0;bgot=0;aowe=0;bowe=0;aticks=0;bticks=0;
   asent=0;bsent=0;bpop=0;apop=0;afirst=-1;areturn=-1;bfirst=-1;breturn=-1;astalls=0;bstalls=0;
   arx0=-1;arx1=-1;brx0=-1;brx1=-1;amaxin=0;bmaxin=0;
   #0.3 go=1;
  end
 endtask
 task automatic wait_drained;
  integer watchdog;real ra,rb;
  begin watchdog=0;
   while(!(agot==N && bgot==N && aowe==0 && bowe==0 && acred==XS && bcred==XS && A.lc[0]==CR && B.lc[0]==CR && A.arc==ARC && B.arc==ARC))begin
    @(negedge ca);watchdog=watchdog+1;
    if(watchdog>N*200+20000)$fatal(1,"CONSERVATION_TIMEOUT sent=%0d/%0d received=%0d/%0d",asrc,bsrc,agot,bgot);
   end
   repeat(HOPS+8)@(negedge ca);
   if(!A.g_rx[0].u_rx.ib_empty || !B.g_rx[0].u_rx.ib_empty || A.g_rx[0].u_rx.u_af.wr_bin!=A.g_rx[0].u_rx.u_af.rd_bin || B.g_rx[0].u_rx.u_af.wr_bin!=B.g_rx[0].u_rx.u_af.rd_bin || A.sne || B.sne || A.xv_q || B.xv_q || aov || bov || A.lne!=0 || B.lne!=0)$fatal(1,"LIVE_STATE_AT_DRAIN");
   if(asent!=N || bsent!=N || bpop!=N || apop!=N)$fatal(1,"DRAIN_INVARIANT");
   ra=(N-1)*1.0/(arx1-arx0);rb=(N-1)*1.0/(brx1-brx0);
   $display("EPOCH %0d hops=%0d CR=%0d delivered=%0d/%0d credit_rtt=%0d/%0d rate_milli=%0d/%0d span=%0d/%0d stalls=%0d/%0d max_inflight=%0d/%0d cycles=%0d",
     epoch,HOPS,CR,agot,bgot,areturn-afirst,breturn-bfirst,$rtoi(ra*1000.0),$rtoi(rb*1000.0),arx1-arx0,brx1-brx0,astalls,bstalls,amaxin,bmaxin,aticks);
  end
 endtask
 initial begin
  #0.2;cold_start();
  if(NEG==2)begin repeat(5)@(negedge ca);bad_gray=1;end
  wait_drained();epoch=1;cold_start();wait_drained();
  if(NEG!=0)$fatal(1,"NEGATIVE_NOT_DETECTED NEG=%0d",NEG);
  $display("PASS link_fullrate HOPS=%0d CR=%0d checks=%0d epochs=2",HOPS,CR,checks);$finish;
 end
endmodule
