`timescale 1ns/1ps
module tb;
reg ck=0;always #0.4165 ck=~ck;reg rst=0;reg va=0,vb=0,fa=0,fb=0;reg[255:0]wa=0,wb=0;wire[63:0]qa,qb;wire[7:0]lfa,lfb;wire tfa,tfb;
ot_qwen_w12_lane_slice #(.G(4),.NPL(2),.IL(8),.MUL_LAT(5),.ACC_LAT(5),.TREE_LAT(3)) a(ck,rst,va,fa,4'd8,wa,{4{32'h3f800000}},qa,lfa,tfa);
ot_qwen_w12_lane_slice #(.G(4),.NPL(2),.IL(8),.MUL_LAT(5),.ACC_LAT(5),.TREE_LAT(3)) b(ck,rst,vb,fb,4'd8,wb,{4{32'h3f800000}},qb,lfb,tfb);
function automatic[31:0]fp(input integer x);integer e,j;reg[31:0]m;begin e=0;for(j=0;j<24;j++)if(x>=(1<<j))e=j;m=x-(1<<e);fp=((127+e)<<23)|(m<<(23-e));end endfunction
integer cy,K=2,na=0,nb=0,ia,ib,kr,r,slot,checks=0;reg[63:0]hist[0:255];
initial begin
 if($value$plusargs("K=%d",K))begin end
 repeat(20)@(negedge ck);rst=1;
 for(cy=0;cy<600;cy++)begin
 @(negedge ck);va=0;vb=0;fa=0;fb=0;
 ia=cy-20;ib=(cy-20)%96;r=(cy-20)/96;
 if(ia>=0&&ia<24*K)begin va=1;fa=(ia%(8*K)<8);end
 if(cy>=20&&r<3&&ib<8*K)begin vb=1;fb=(ib<8);end
 for(integer g=0;g<4;g++)for(integer p=0;p<2;p++)begin wa[32*(g*2+p)+:32]=fp(g+1+p);wb[32*(g*2+p)+:32]=fp(g+1+p);end
 @(posedge ck);
 if(a.vline[18])begin
  kr=(na/8)%K;
  if(qa!=={fp(14*(kr+1)),fp(10*(kr+1))})$fatal(1,"GOLD_A n%0d got%h",na,qa);
  hist[na]=qa;na++;checks++;
 end
 if(b.vline[18])begin
  kr=(nb/8)%K;
  if(qb!=={fp(14*(kr+1)),fp(10*(kr+1))})$fatal(1,"GOLD_B n%0d got%h",nb,qb);
  if(nb<na&&qb!==hist[nb])$fatal(1,"PAUSE_ARITH");nb++;checks++;
 end
 end
 if(na!=24*K||nb!=24*K||(|lfa)||(|lfb)||tfa||tfb)$fatal(1,"COUNT_OR_FAULT %0d %0d",na,nb);
 $display("ROUND96_LANE_PASS K%0d words%0d checks%0d actualG4NPL2 goldenintegerFP32",K,nb,checks);$finish;
end
endmodule
