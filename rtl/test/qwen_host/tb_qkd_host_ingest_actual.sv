`timescale 1ns/1ps
module tb_qkd_host_ingest_actual;
 parameter integer MUT=0,HOT=0;
 integer hot_mode,event_mut;initial begin if(!$value$plusargs("HOT=%d",hot_mode))hot_mode=HOT;if(!$value$plusargs("EVENT_MUT=%d",event_mut))event_mut=0;end
 reg hclk=0;always #0.512 hclk=~hclk;
 reg ck=0;always #0.416667 ck=~ck;reg rst_n=0;
 reg[289:0]ing=0;wire ing_cr;wire[36863:0]ctrl_es,land_er_unused;wire[33407:0]land_er;
 wire[33407:0]ctrl_er;wire[127:0]cv,cw;wire mv,mf;wire[65:0]marker;wire[31:0]issued,landed;wire[3:0]cf;
 qkd_host_ingest_chain #(.MUT(MUT))dut(.ck_map(ck),.ck_sum(ck),.ck_order(ck),.ck_station({128{ck}}),.ck_static({128{ck}}),.rst_n(rst_n),
 .ing(ing),.ing_cr(ing_cr),.land_es(36864'd0),.land_er(land_er),.ctrl_es(ctrl_es),.ctrl_er(ctrl_er),
 .completion_v(cv),.completion_we(cw^({128{event_mut!=0}}&(128'd1<<127))),.marker_v(mv),.marker(marker),.marker_cr(1'b0),.issued(issued),.landed(landed),.map_fault(mf),.chain_fault(cf));
 integer retired=0,physical=0;reg[511:0]seen=0;integer x,sec,expected_id;integer k,n=0,cyc=0,credit=8,sent=0,first=-1,last=-1;reg running=0,mark_sent=0;
 function[31:0]addr(input integer x);integer st,pc,sec;begin
 st=hot_mode?3:(x%4);pc=hot_mode?31:((x/4)%32);sec=(x/128)%64;addr=(sec<<7)|(st<<5)|pc;end endfunction
 function[255:0]data(input integer x);data={{7{32'h9ac05e17}},x[31:0]};endfunction
 always @(posedge ck)begin
 cyc=cyc+1;
 for(k=0;k<128;k=k+1)begin
  if(cv[k])begin if(!cw[k])$fatal(1,"unexpected read retirement");retired=retired+1;end
  if(ctrl_es[k*288])begin
   x=ctrl_es[k*288+1+:32];sec=(x/128)%64;expected_id=hot_mode?127:((x%4)*32+(x/4)%32);
   if(x>=512||seen[x]||k!=expected_id||ctrl_es[k*288+:288]!=={1'b1,1'b1,5'(sec%4),5'(sec/4),19'd64,data(x),1'b1})
    $fatal(1,"exact original native sector/order/ownership x=%0d pc=%0d expected=%0d",x,k,expected_id);
   seen[x]=1;

   if(first<0)first=cyc;last=cyc;
   n=n+1;
  end
 end
 if(running&&ing_cr)credit=credit+1;
 if(landed>retired)$fatal(1,"ACK became visible before actual physical retirement");
 if(mf||cf)$fatal(1,"chain fault map=%b stack=%b issued=%0d landed=%0d",mf,cf,issued,landed);
 if(mv)begin
  if(landed!=512||issued!=512||n!=512||retired!=512||physical!=512||seen!={512{1'b1}}||marker!=66'h29a)$fatal(1,"marker escaped real commits %0d/%0d launched%0d",issued,landed,n);
  $display("PASS HOST_INGEST_ACTUAL HOT=%0d sectors=%0d launch_interval=%0d marker_cycle=%0d",hot_mode,n,last-first,cyc);$finish;
 end
 end
 always @(negedge ck)if(running)begin
 ing=0;
 if(credit>0&&sent<512)begin ing={data(sent),addr(sent),1'b1,1'b1};sent=sent+1;credit=credit-1;end
 else if(credit>0&&sent==512&&!mark_sent)begin ing={190'd0,66'h29a,32'hffffffff,1'b1,1'b1};mark_sent=1;credit=credit-1;end
 end
    function automatic [71:0] enc64(input [63:0] data);
        reg [71:0] c; integer p, k, j;
        begin
            c = '0; j = 0;
            for (p = 1; p <= 71; p = p + 1) if ((p & (p - 1)) != 0) begin c[p-1] = data[j]; j = j + 1; end
            for (k = 0; k < 7; k = k + 1)
                for (p = 1; p <= 71; p = p + 1)
                    if ((p & (1 << k)) != 0 && p != (1 << k)) c[(1<<k)-1] = c[(1<<k)-1] ^ c[p-1];
            c[71] = ^c[70:0]; enc64 = c;
        end
    endfunction
    function automatic [287:0] enc256(input [255:0] d);
        enc256 = {enc64(d[255:192]), enc64(d[191:128]), enc64(d[127:64]), enc64(d[63:0])};
    endfunction

 for(genvar id=0;id<128;id++)begin:g_pc
  wire[327:0]po;wire[293:0]co;wire[32:0]ko;wire ff,ef;
  qkd_ctrl_pc_host u_ctrl(.pll_hbm(hclk),.hrst(rst_n),.ck(ck),.rsi(rst_n),.pc(5'(id%32)),.ci(319'd0),.co(co),
   .es(ctrl_es[id*288+:288]),.er(ctrl_er[id*261+:261]),.po(po),.pi(289'd0),.ki(33'd0),.ko(ko),.fi(1'b0),.fo(ff),
   .completion_v(cv[id]),.completion_we(cw[id]),.completion_fault(ef));
  reg[286:0]posts[0:511];integer wp=0,rp=0;reg[286:0]meta;
  reg[4:0]dv=0;reg[255:0]dd[0:4];reg[18:0]open_row[0:31];reg[31:0]open_bank=0;
  always @(posedge ck)if(running&&ctrl_es[id*288])begin posts[wp]=ctrl_es[id*288+1+:287];wp++;end
  always @(posedge hclk)begin
   if(rst_n&&(ff||ef))$fatal(1,"actual controller fault PC=%0d",id);
   dv<={dv[3:0],po[28]&&po[29]};for(integer j=1;j<5;j++)dd[j]<=dd[j-1];
   if(po[0])begin if(po[3:1]==1)begin open_bank[po[8:4]]=1;open_row[po[8:4]]=po[27:9];end else if(po[3:1]==0)open_bank[po[8:4]]=0;end
   if(po[28])begin
    if(!po[29]||rp>=wp)$fatal(1,"unexpected static physical column PC=%0d",id);
    meta=posts[rp];rp++;
    if(!open_bank[po[34:30]]||{po[34:30],po[39:35],open_row[po[34:30]]}!==meta[284:256])$fatal(1,"actual HBM bank/column/row ownership PC=%0d",id);
    dd[0]<=meta[255:0];
   end
   if(dv[4])begin
    if(po[327:40]!==enc256(dd[4]))$fatal(1,"actual ECC PHY256 write payload PC=%0d",id);
    physical=physical+1;
   end
  end
 end
 initial begin repeat(20)@(negedge ck);rst_n=1;repeat(300)@(negedge ck);running=1;end
 initial begin #100000;$fatal(1,"timeout issued=%0d landed=%0d launched=%0d",issued,landed,n);end
endmodule
