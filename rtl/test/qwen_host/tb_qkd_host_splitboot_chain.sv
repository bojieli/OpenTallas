`timescale 1ns/1ps
module tb_qkd_host_splitboot_chain;
 parameter integer MUT=0,HOT=0;
 reg ck=0;always #5 ck=~ck;reg rst_n=0;
 reg[289:0]ing=0;wire ing_cr;wire[289:0]kv;wire kv_cr;wire[282:0]hb;reg hb_cr=0;reg[36863:0]land_es=0;wire[127:0]all_acks;wire prefix;wire[31:0]global_issued,global_landed;wire df;
 qkd_host_boot_dispatch #(.MUT(MUT))dispatch(.ck(ck),.ck_order(ck),.rst_n(rst_n),.boot_release(1'b0),.ing(ing),.ing_cr(ing_cr),.kv(kv),.kv_cr(kv_cr),.hb(hb),.hb_cr(hb_cr),.acks(all_acks),.prefix_v(prefix),.issued(global_issued),.landed(global_landed),.fault(df));wire[36863:0]ctrl_es,land_er_unused;wire[33407:0]land_er;
 reg[33407:0]ctrl_er=0;reg[127:0]cv=0;wire mv,mf;wire[65:0]marker;wire[31:0]issued,landed;wire[3:0]cf;
 qkd_host_ingest_chain_splitboot #(.MUT(0))dut(.ck_map(ck),.ck_sum(ck),.ck_order(ck),.ck_station({128{ck}}),.ck_static({128{ck}}),.rst_n(rst_n),
 .ing(kv),.ing_cr(kv_cr),.all_acks(all_acks),.land_es(land_es),.land_er(land_er),.ctrl_es(ctrl_es),.ctrl_er(ctrl_er),
 .completion_v(cv),.completion_we(cv),.marker_v(mv),.marker(marker),.marker_cr(1'b0),.issued(issued),.landed(landed),.map_fault(mf),.chain_fault(cf));
 // Scheduler model only: queue credit after three edges, ordered JEDEC-style
 // write retirement after seventeen edges. Real controller observer has a
 // separate exact JEDEC bench; this model does not qualify its throughput.
 reg[127:0]delay[0:16];reg[511:0]seen=0;integer x,sec,expected_id;integer retired=0;integer k,n=0,cyc=0,credit=8,sent=0,first=-1,last=-1;reg running=0,mark_sent=0;
 function[31:0]addr(input integer x);integer st,pc,sec;begin
 st=HOT?3:(x%4);pc=HOT?31:((x/4)%32);sec=(x/128)%64;addr=x%2 ? (32'h80000000|(x<<7)|(st<<5)|pc) : ((sec<<7)|(st<<5)|pc);end endfunction
 function[255:0]data(input integer x);data={{7{32'h9ac05e17}},x[31:0]};endfunction
 always @(posedge ck)begin
 cyc=cyc+1;ctrl_er<=0;land_es<=0;hb_cr<=hb[0];
 if(hb[0]&&!hb[1])begin
  integer bx,bst,bpc,bid,bp;
  bx=hb[27+:32];bst=hb[8:7];bpc=hb[6:2];bid=bst*32+bpc;bp=hb[26:2]>>7;
  if(bx%2!=1||hb[26:2]!=(addr(bx)&32'h7fffffff)||hb[282:27]!=data(bx))$fatal(1,"hb packing/data wrong");
  land_es[bid*288+:288]<={1'b1,1'b1,5'({bp[9:7],bp[1:0]}),5'(bp>>2),19'd24427,data(bx),1'b1};
 end
 if(hb[0]&&hb[1]&&(global_landed!=512||retired!=512||hb[90:27]!=64'h29a))$fatal(1,"BOOT_END passed incomplete physical prefix");cv<=delay[16];delay[0]<=0;
 for(k=1;k<17;k=k+1)delay[k]<=delay[k-1];
 for(k=0;k<128;k=k+1)begin
  if(delay[16][k])retired=retired+1;
  ctrl_er[k*261+259]<=delay[2][k];
  if(ctrl_es[k*288])begin
   x=ctrl_es[k*288+1+:32];sec=(x/128)%64;expected_id=HOT?127:((x%4)*32+(x/4)%32);
   if(x>=512||seen[x]||k!=expected_id||ctrl_es[k*288+:288]!==((x%2)?{1'b1,1'b1,5'({x[9:7],x[1:0]}),5'(x>>2),19'd24427,data(x),1'b1}:{1'b1,1'b1,5'(sec%4),5'(sec/4),19'd64,data(x),1'b1}))
    $fatal(1,"exact original native sector/order/ownership x=%0d pc=%0d expected=%0d",x,k,expected_id);
   seen[x]=1;
   delay[0][k]<=1;
   if(first<0)first=cyc;last=cyc;
   n=n+1;
  end
 end
 if(running&&ing_cr)credit=credit+1;
 if(global_landed>retired)$fatal(1,"ACK became visible before modeled physical retirement");
 if(df||mf||cf)$fatal(1,"chain fault map=%b stack=%b issued=%0d landed=%0d",mf,cf,issued,landed);
 if(mv)begin
  if(global_landed!=512||global_issued!=512||landed!=256||issued!=256||n!=512||retired!=512||seen!={512{1'b1}}||marker!=66'h29a)$fatal(1,"marker escaped real commits %0d/%0d launched%0d",issued,landed,n);
  $display("PASS HOST_SPLITBOOT_CHAIN HOT=%0d sectors=%0d launch_interval=%0d marker_cycle=%0d",HOT,n,last-first,cyc);$finish;
 end
 end
 always @(negedge ck)if(running)begin
 ing=0;
 if(credit>0&&sent<512)begin ing={data(sent),addr(sent),1'b1,1'b1};sent=sent+1;credit=credit-1;end
 else if(credit>0&&sent==512&&!mark_sent)begin ing={190'd0,66'h29a,32'hffffffff,1'b1,1'b1};mark_sent=1;credit=credit-1;end
 end
 initial begin for(k=0;k<17;k=k+1)delay[k]=0;repeat(8)@(negedge ck);rst_n=1;repeat(8)@(negedge ck);running=1;end
 initial begin #300000;$fatal(1,"timeout issued=%0d landed=%0d launched=%0d",issued,landed,n);end
endmodule
