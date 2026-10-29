`timescale 1ns/1fs
module pipe #(parameter W=512,K=8)(input wire clk,rst_n,input wire[W-1:0]d,input wire e,output wire[W-1:0]q,output wire eq);
wire[W-1:0] p[0:K];wire[K:0]ep;assign p[0]=d;assign ep[0]=e;
genvar j;generate for(j=0;j<K;j=j+1)begin:g
ot_dp_st #(.W(W))st(.clk(clk),.rst_n(rst_n),.d(p[j]),.ea(ep[j]),.q(p[j+1]),.eq(ep[j+1]));
end endgenerate
assign q=p[K];assign eq=ep[K];
endmodule
module tb;
parameter MUT=0;
reg clk=0,rst_n=0;always #0.4165 clk=~clk;
reg[511:0] hi=0;reg[513:0]lo=0;reg e=0;integer n=0,k;reg[31:0]rng=32'h5e317c42;
wire[511:0]a,b,bc;wire[513:0]c,d;wire ae,be,ce,de;
pipe #(.W(512),.K(8))old_hi(clk,rst_n,hi,e,a,ae);
pipe #(.W(512),.K(MUT==2?13:14))new_hi(clk,rst_n,hi,e,b,be);
pipe #(.W(514),.K(8))old_lo(clk,rst_n,lo,e,c,ce);
pipe #(.W(514),.K(9))new_lo(clk,rst_n,lo,e,d,de);
assign bc=b ^ (MUT==1 ? (512'd1<<277) : 512'd0);
reg[512:0]hist[0:5];reg[514:0]low_hist;
integer cycles=0,checked=0;
integer z;
// Reset flushes epoch validity immediately; payload remains a free-running pipeline.
always@(negedge rst_n)begin
 for(z=0;z<6;z=z+1)hist[z][512]=0;
 low_hist[514]=0;
end
always@(posedge clk)begin
 cycles=cycles+1;#0.001;
 if(cycles>32)begin
  if({be,bc}!==hist[5])$fatal(1,"HIGH_LATENCY_DATA_MISMATCH cycle=%0d MUT=%0d",cycles,MUT);
  if({de,d}!==low_hist)$fatal(1,"LOW_LATENCY_DATA_MISMATCH cycle=%0d MUT=%0d",cycles,MUT);
  checked=checked+1;
 end
 for(k=5;k>0;k=k-1)hist[k]=hist[k-1];hist[0]={ae,a};low_hist={ce,c};
end
always@(negedge clk)begin
 n=n+1;rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
 for(k=0;k<16;k=k+1)hi[32*k+:32]=rng^(32'h9e3779b9*k)^n;
 lo={rng[1:0],hi};rst_n=(n>=5 && !(n>=120&&n<123));e=rst_n&&(n%7!=0);
 if(n==400)begin $display("PASS FT0_W512_8to14_plus6 FT1_W514_8to9_plus1 %0d checked edges MUT=%0d",checked,MUT);$finish;end
end
endmodule
