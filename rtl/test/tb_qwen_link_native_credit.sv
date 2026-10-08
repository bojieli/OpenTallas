`timescale 1ns/1ps
// Actual full NL4 hubs; only physical lane0 active. Both hubs use their native
// IBUF4/AD8/OCRED1/Gray-count machinery. This is not a qfd_kvc implementation.
module tb_qwen_link_native_credit;
 parameter integer HOPS=54, N=96, NEG=0;
 reg ca=0,cb=0,por=1,kill_a=0,go=0;
 always #5 ca=~ca;
 initial begin #1.3;forever #5 cb=~cb;end
 wire ra=por&&!kill_a;
 wire [2111:0] alo,blo;
 wire [527:0] ab[0:HOPS],ba[0:HOPS];
 wire ac[0:HOPS],bc[0:HOPS];
 assign ab[0]=alo[527:0];assign ba[HOPS]=blo[527:0];
 assign ac[0]=ca;assign bc[HOPS]=cb;
 reg bad_gray=0;
 wire [527:0] into_a=bad_gray?{ba[0][527:5],4'b1111,ba[0][0]}:ba[0];
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
 wire [511:0] aod,bod;
 ot_qwen_die_hub A(.ck(ca),.rst_n(ra),.fck({{3{cb}},bc[0]}),.l_i({1584'b0,into_a}),.l_o(alo),
  .x3_v(av),.x3_d(ad),.x3_tag(atag),.x3_cr(axcr),.ar_v(aov),.ar_d(aod),.ar_cr(acr),.fault(af));
 ot_qwen_die_hub B(.ck(cb),.rst_n(por),.fck({{3{ca}},ac[HOPS]}),.l_i({1584'b0,ab[HOPS]}),.l_o(blo),
  .x3_v(bv),.x3_d(bd),.x3_tag(btag),.x3_cr(bxcr),.ar_v(bov),.ar_d(bod),.ar_cr(bcr),.fault(bf));
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
 integer epoch=0,acred=2,bcred=2,asrc=0,bsrc=0,agot=0,bgot=0,aowe=0,bowe=0;
 integer aticks=0,bticks=0,asent=0,bsent=0,bpop=0,apop=0;
 integer afirst=-1,areturn=-1,bfirst=-1,breturn=-1,a5=-1,b5=-1;
 integer astalls=0,bstalls=0,checks=0,awrap=0,bwrap=0;
 reg [3:0] aprev=0,bprev=0;
 always @(negedge ca) if(go)begin
  aticks=aticks+1;
  if(axcr)acred=acred+1;
  av=0;acr=0;
  if(alo[0])begin asent=asent+1;if(afirst<0)afirst=aticks;if(asent==5)a5=aticks;end
  if(B.g_rx[0].u_rx.i_cr)bpop=bpop+1;
  if(afirst>=0 && areturn<0 && A.lseen[0]!=0)areturn=aticks;
  if(A.g_rx[0].cb<aprev)awrap=awrap+1;aprev=A.g_rx[0].cb;
  if(asent-bpop>4)$fatal(1,"CREDIT_CONSERVATION sideA issued=%0d popped=%0d nativefault=%0d",asent,bpop,af);
  if(A.lc[0]>4)$fatal(1,"CREDIT_RANGE sideA lc=%0d nativefault=%0d",A.lc[0],af);
  if(aov)begin
   if(agot>=N || aod!==delivered(1,epoch,agot))$fatal(1,"DATA_MISMATCH sideA index=%0d",agot);
   agot=agot+1;aowe=aowe+1;checks=checks+1;
  end
  // Hold all four consumer credits during a deterministic interval.
  if(aowe>0 && !(aticks>=180 && aticks<650) && aticks%3!=0)begin acr=1;aowe=aowe-1;end
  if(asrc<N && (acred>0 || NEG==1))begin
   av=1;ad=word(0,epoch,asrc);atag=asrc;asrc=asrc+1;acred=acred-1;
  end else if(asrc<N)astalls=astalls+1;
  if(af || bf)$fatal(1,"NATIVE_FAULT a=%0d b=%0d",af,bf);
 end
 always @(negedge cb) if(go)begin
  bticks=bticks+1;
  if(bxcr)bcred=bcred+1;
  bv=0;bcr=0;
  if(blo[0])begin bsent=bsent+1;if(bfirst<0)bfirst=bticks;if(bsent==5)b5=bticks;end
  if(A.g_rx[0].u_rx.i_cr)apop=apop+1;
  if(bfirst>=0 && breturn<0 && B.lseen[0]!=0)breturn=bticks;
  if(B.g_rx[0].cb<bprev)bwrap=bwrap+1;bprev=B.g_rx[0].cb;
  if(bsent-apop>4)$fatal(1,"CREDIT_CONSERVATION sideB");
  if(B.lc[0]>4)$fatal(1,"CREDIT_RANGE sideB");
  if(bov)begin
   if(bgot>=N || bod!==delivered(0,epoch,bgot))$fatal(1,"DATA_MISMATCH sideB index=%0d",bgot);
   bgot=bgot+1;bowe=bowe+1;checks=checks+1;
  end
  if(bowe>0 && !(bticks>=180 && bticks<750) && bticks%4!=0)begin bcr=1;bowe=bowe-1;end
  if(bsrc<N && bcred>0)begin bv=1;bd=word(1,epoch,bsrc);btag=bsrc;bsrc=bsrc+1;bcred=bcred-1;end
  else if(bsrc<N)bstalls=bstalls+1;
  if(af || bf)$fatal(1,"NATIVE_FAULT a=%0d b=%0d",af,bf);
 end
 task automatic cold_start;
  begin
   go=0;av=0;bv=0;acr=0;bcr=0;por=0;
   repeat(8)@(negedge ca);por=1;
   repeat(HOPS+25)@(negedge ca);
   acred=2;bcred=2;asrc=0;bsrc=0;agot=0;bgot=0;aowe=0;bowe=0;aticks=0;bticks=0;
   asent=0;bsent=0;bpop=0;apop=0;afirst=-1;areturn=-1;bfirst=-1;breturn=-1;aprev=0;bprev=0;awrap=0;bwrap=0;a5=-1;b5=-1;
   #0.3 go=1;
  end
 endtask
 task automatic wait_drained;
  integer watchdog;
  begin watchdog=0;
   while(!(agot==N && bgot==N && aowe==0 && bowe==0 && acred==2 && bcred==2 && A.lc[0]==4 && B.lc[0]==4 && A.arc==4 && B.arc==4 && !A.held[0] && !B.held[0]))begin
    @(negedge ca);watchdog=watchdog+1;
    if(watchdog>30000)$fatal(1,"CONSERVATION_TIMEOUT sent=%0d/%0d received=%0d/%0d",asrc,bsrc,agot,bgot);
   end
   repeat(HOPS+8)@(negedge ca);
   if(!A.g_rx[0].u_rx.ib_empty || !B.g_rx[0].u_rx.ib_empty || A.g_rx[0].u_rx.g_af.u_af.wr_bin!=A.g_rx[0].u_rx.g_af.u_af.rd_bin || B.g_rx[0].u_rx.g_af.u_af.wr_bin!=B.g_rx[0].u_rx.g_af.u_af.rd_bin || A.sv!=0 || B.sv!=0 || A.xv_q || B.xv_q || aov || bov)$fatal(1,"LIVE_STATE_AT_DRAIN");
   if(asent!=N || bsent!=N || bpop!=N || apop!=N || awrap<5 || bwrap<5)$fatal(1,"DRAIN_OR_WRAP_INVARIANT");
   $display("EPOCH %0d hops=%0d delivered=%0d/%0d first_credit_rtt=%0d/%0d window_restart=%0d/%0d cycles=%0d stalls=%0d/%0d wraps=%0d/%0d",epoch,HOPS,agot,bgot,areturn-afirst,breturn-bfirst,a5-afirst,b5-bfirst,aticks,astalls,bstalls,awrap,bwrap);
  end
 endtask
 initial begin
  #0.2;cold_start();
  if(NEG==2)begin repeat(40)@(negedge ca);bad_gray=1;end
  if(NEG==3)begin repeat(40)@(negedge ca);kill_a=1;repeat(8)@(negedge ca);kill_a=0;end
  wait_drained();epoch=1;cold_start();wait_drained();
  $display("PASS native_credit HOPS=%0d checks=%0d epochs=2",HOPS,checks);$finish;
 end
endmodule
