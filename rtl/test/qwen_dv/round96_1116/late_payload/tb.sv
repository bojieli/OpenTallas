`timescale 1ns/1ps
module tb;
reg ck=0;always #0.4165 ck=~ck;reg rst=0;
reg[63:0]din=0;wire[63:0]q14,q27,q55,qmut;reg[63:0]hist[0:1023];
qfd_dv_s8s_selected_delay #(.D(14)) d14(ck,rst,rst,din,q14);
qfd_dv_s8s_selected_delay #(.D(27)) d27(ck,rst,rst,din,q27);
qfd_dv_s8s_selected_delay #(.D(55),.ENABLE_DELAY55(1)) d55(ck,rst,rst,din,q55);
qfd_dv_s8s_selected_delay #(.D(55),.ENABLE_DELAY55(1),.MUT(1)) dm(ck,rst,rst,din,qmut);
reg cfg=0;reg[1:0]mode=1;reg[7:0]kc=1,nwords=8;
reg[63:0]sl=0,sh=0,nl=0,nh=0,nb=0;reg[3:0]sc=0,nc=0;reg[1:0]nbc=0;
wire av,bv,af,bf;wire[7:0]ai,bi;wire[63:0]ad,bd;wire al,bl;
`define PINS .ck(ck),.rst_n(rst),.cfg_v_p(cfg),.cfg_mode_p(mode),.cfg_wsrc_p(1'b0),.cfg_nwords_p(nwords),.cfg_sbase_p(9'd0),.cfg_kcm1_p(kc),.rs_s_lo_p(sl),.rs_s_hi_p(sh),.rs_n_lo_p(nl),.rs_n_hi_p(nh),.rs_s_c_p(sc),.rs_n_c_p(nc),.nb_d_p(nb),.nb_c_p(nbc),.bt_q_p(32'h3f803f80),.flt_bank_i(4'd0),.flt_vld_i(4'd0)
qfd_dv_s8_station_tail1_cb55 #(.SKEW(55),.ENABLE_DELAY55(1)) a(`PINS,.r_v(av),.r_idx(ai),.r_last(al),.r_d(ad),.fault(af));
qfd_dv_s8_station_tail1 #(.SKEW(14)) stale(`PINS,.r_v(bv),.r_idx(bi),.r_last(bl),.r_d(bd),.fault(bf));
function automatic[31:0]fp(input integer x);
 integer e,j;reg[31:0]m;
 begin e=0;for(j=0;j<24;j++)if(x>=(1<<j))e=j;m=x-(1<<e);fp=((127+e)<<23)|(m<<(23-e));end
endfunction
function automatic[63:0]pay(input integer k,input integer j,input integer half);
 integer a,b;begin a=k*32+j+1;b=k*64+j+3;
 if(half==0)pay={fp(a+1),fp(a)};else if(half==1)pay={fp(b+2),fp(b)};else if(half==2)pay={fp(a+9),fp(a+8)};else pay={fp(b+18),fp(b+16)};end
endfunction
integer CFG_EDGE=169;
integer cy=0,K=2,M=1,i,j,k,checks=0,mut=0,count=0,badcount=0,first=-1,last=-1,base,expect0,expect1;reg[63:0]gold;
initial begin
 if($value$plusargs("K=%d",K))begin end
 if($value$plusargs("MODE=%d",M))begin end
 if($value$plusargs("CFG_EDGE=%d",CFG_EDGE))begin end
 mode=M;kc=K-1;nwords=(M==0)?16:8;
 repeat(16)@(negedge ck);rst=1;
 for(cy=0;cy<850;cy++)begin
 @(negedge ck);din=64'h0102030405060708+64'(cy)*64'h100000003;hist[cy]=din;
 cfg=(cy==CFG_EDGE);sc=0;nc=0;sl=0;nl=0;sh=0;nh=0;nbc=0;nb=0;
 if(cy>=120&&cy<120+8*K)begin k=(cy-120)/8;j=(cy-120)%8;sl=pay(k,j,0);nl=pay(k,j,2);sc[1:0]=1;nc[1:0]=1;end
 if(cy>=175&&cy<175+8*K)begin k=(cy-175)/8;j=(cy-175)%8;sh=pay(k,j,1);nh=pay(k,j,3);sc[3:2]=1;nc[3:2]=1;end
 base=175+8*(K-1)+40;
 if(M==2&&cy>=base&&cy<base+8)begin j=cy-base;nbc=1;nb={fp(105+j),fp(100+j)};end
 @(posedge ck);
 if(cy>110)begin
  if(q14!==hist[cy-14])$fatal(1,"D14_PAYLOAD cy%0d",cy);
  if(q27!==hist[cy-27])$fatal(1,"D27_PAYLOAD cy%0d",cy);
  if(q55!==hist[cy-55])$fatal(1,"D55_PAYLOAD cy%0d",cy);
  if(qmut!==hist[cy-55])mut++;checks+=3;
 end
 if(av)begin
  if(first<0)first=cy;last=cy;
  if(ai!==8'(count))$fatal(1,"INDEX %0d %0d",count,ai);
  j=count%8;base=96*(K-1)+2*j+4;
  if(M==0)begin expect0=base+((count>=8)?24:0);expect1=expect0+3;end
  else begin expect0=2*base+24;expect1=expect0+6;if(M==2)begin expect0+=100+j;expect1+=105+j;end end
  gold={fp(expect1),fp(expect0)};
  if(ad!==gold)$fatal(1,"STN_PAYLOAD cy%0d idx%0d got%h exp%h",cy,count,ad,gold);
  count++;
 end
 if(bv)badcount++;
 end
 if(af||count!=nwords||mut==0||!bf)$fatal(1,"SUMMARY fault%b count%0d/%0d mutant%0d stale%b",af,count,nwords,mut,bf);
 $display("STN55_PASS K%0d MODE%0d words%0d first%0d last%0d delaychecks%0d delaymut%0d stale_fault%b stalewords%0d",K,M,count,first,last,checks,mut,bf,badcount);$finish;
end
endmodule
