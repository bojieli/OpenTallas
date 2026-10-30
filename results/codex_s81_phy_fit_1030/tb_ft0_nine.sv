`timescale 1ps/1ps
module chain #(parameter N=8)(input clk,rst_n,input[512:0] d,output[512:0]q);
wire[512:0] s[0:N]; assign s[0]=d;assign q=s[N];
for(genvar g=0;g<N;g=g+1) begin
 ot_dp_st #(.W(512)) u(.clk(clk),.rst_n(rst_n),.d(s[g][511:0]),.ea(s[g][512]),.q(s[g+1][511:0]),.eq(s[g+1][512]));
end
endmodule
module tb;
reg clk=0,rst_n=0;reg[512:0]d;wire[512:0]oldq,newq;reg[511:0]hist[0:8];reg[8:0]ehist=0;
chain #(.N(8)) old8(clk,rst_n,d,oldq);chain #(.N(9)) candidate9(clk,rst_n,d,newq);
integer t,j,k,checks=0,errors=0,age_mut=0,payload_mut=0,epoch_mut=0;reg[511:0]prevold;reg[31:0]rng=32'h625981f3;
initial begin
 for(j=0;j<9;j=j+1)hist[j]='x;
 for(t=0;t<12000;t=t+1)begin
  clk=0;rst_n=(t>=64 && !(t>=1017 && t<1081) && !(t>=6001 && t<6065));
  for(k=0;k<16;k=k+1)begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);d[k*32+:32]=rng;end
  if(t%53==0)d[105:99]='x;
  d[512]=(t%7<4);
  #416;
  prevold=oldq[511:0];
  clk=1;
  for(j=8;j>0;j=j-1)hist[j]=hist[j-1];hist[0]=d[511:0];
  if(!rst_n)ehist=0;else ehist={ehist[7:0],d[512]};
  #1;
  checks=checks+4;
  if(oldq[511:0]!==hist[7])errors=errors+1;
  if(newq[511:0]!==hist[8])errors=errors+1;
  if(newq[512]!==ehist[8])errors=errors+1;
  if(t>0 && newq[511:0]!==prevold)errors=errors+1;
  if(t>9 && newq[511:0]!==oldq[511:0])age_mut=age_mut+1;
  if(t>9 && {newq[511:1],~newq[0]}!==hist[8])payload_mut=payload_mut+1;
  if(t>9 && newq[512]!==ehist[7])epoch_mut=epoch_mut+1;
  #416;
 end
 $display("FT0_NATIVE_NINE checks=%0d errors=%0d age_mutant_caught=%0d payload_mutant_caught=%0d epoch_mutant_caught=%0d period_ps=833 old_cycles=8 candidate_cycles=9",checks,errors,age_mut,payload_mut,epoch_mut);
 if(errors || age_mut==0 || payload_mut==0 || epoch_mut==0)$fatal(1,"FAIL");
 $finish;
end
endmodule
