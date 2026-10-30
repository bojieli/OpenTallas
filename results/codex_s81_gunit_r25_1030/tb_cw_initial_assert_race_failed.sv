`timescale 1ps/1ps
module tb;
reg clk=0,rst_n=0;reg[265:0]d;wire[264:0]oq,nq,bq,pq;wire oe,ne,be,pe;
cw_old o(clk,rst_n,d,oq,oe);cw_candidate n(clk,rst_n,d,nq,ne);cw_badreset b(clk,rst_n,d,bq,be);cw_badpayload p(clk,rst_n,d,pq,pe);
reg[264:0]h0='x,h1='x,oldprevious;reg[1:0]eh=0;reg[31:0]rng=32'h54789910;
integer t,k,checks=0,errors=0,age_mut=0,reset_mut=0,payload_mut=0;
initial begin
for(t=0;t<12000;t=t+1)begin
 clk=0;rst_n=(t>=64 && !(t>=1017&&t<1081) && !(t>=6001&&t<6065));
 for(k=0;k<8;k=k+1)begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);d[k*32+:32]=rng;end
 d[264:256]=rng[8:0];d[265]=(t%7<4);if(t%53==0)d[105:99]='x;
 #1;if(!rst_n)begin checks=checks+1;if(ne!==1'b0)errors=errors+1;if(be!==1'b0)reset_mut=reset_mut+1;end
 #415;oldprevious=oq;clk=1;h1=h0;h0=d[264:0];if(!rst_n)eh=0;else eh={eh[0],d[265]};#1;
 checks=checks+4;
 if(oq!==h0)errors=errors+1;if(nq!==h1)errors=errors+1;if(ne!==eh[1])errors=errors+1;if(t>0&&nq!==oldprevious)errors=errors+1;
 if(t>2&&oq!==h1)age_mut=age_mut+1;if(t>2&&pq!==h1)payload_mut=payload_mut+1;if(be!==eh[1])reset_mut=reset_mut+1;
 #416;
end
$display("CW_NATIVE_R25 checks=%0d errors=%0d age_mutant=%0d payload_mutant=%0d reset_mutant=%0d period_ps=833 local1to2 lane72to73",checks,errors,age_mut,payload_mut,reset_mut);
if(errors||age_mut==0||payload_mut==0||reset_mut==0)$fatal(1,"FAIL");$finish;
end
endmodule
