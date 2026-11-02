`timescale 1ps/1fs
module chain #(parameter K=7)(input wire clk,rst_n,input wire[1661:0] d,output wire[1661:0]q,output wire e);
wire[1662:0]p[0:K];assign p[0]={rst_n,d};
for(genvar j=0;j<K;j=j+1)begin:st
ot_dp_st #(.W(1662)) u(clk,rst_n,p[j][1661:0],p[j][1662],p[j+1][1661:0],p[j+1][1662]);end
assign q=p[K][1661:0];assign e=p[K][1662];endmodule
module case_one #(parameter K=7)(input wire clk,rst_n,input wire[1661:0]d,output wire okay,output wire valid);
wire[1661:0]old,gold,newq;wire oe,ge,ne;
chain #(.K(K)) o(clk,rst_n,d,old,oe);
ot_dp_st #(.W(1662)) golden(clk,rst_n,old,oe,gold,ge);
`ifdef MUTANT_BYPASS_STAGE
chain #(.K(K)) n(clk,rst_n,d,newq,ne);
`else
chain #(.K(K+1)) n(clk,rst_n,d,newq,ne);
`endif
assign valid=ge;assign okay=(ne===ge)&&(!ge||(newq===gold));endmodule
module tb;
reg clk=0;always #416.5 clk=~clk;reg rst_n=0;reg[1661:0]d=0;wire a,b,va,vb;
case_one #(.K(5)) c5(clk,rst_n,d,a,va);case_one #(.K(7)) c7(clk,rst_n,d,b,vb);
integer i,j,checked5=0,checked7=0,caught5=0,caught7=0;reg[31:0]r=32'h7305;
initial begin
for(i=0;i<4200;i=i+1)begin
 @(negedge clk);rst_n=(i%79>=4);
 for(j=0;j<1662;j=j+1)begin r=(r<<1)^(r[31]?32'h04c11db7:0);d[j]=r[17];end
 @(posedge clk);#1;
 if(i>9)begin
  checked5=checked5+va;checked7=checked7+vb;
`ifdef MUTANT_BYPASS_STAGE
  caught5=caught5+(!a);caught7=caught7+(!b);
`else
  if(!a||!b)$fatal(1,"native downstream delay differs cycle%0d",i);
`endif
 end
end
`ifdef MUTANT_BYPASS_STAGE
if(caught5==0||caught7==0)$fatal(1,"stage mutant not caught");
$display("PASS MUTANT_STAGE_BYPASS_CAUGHT5=%0d CAUGHT7=%0d",caught5,caught7);
`else
if(checked5<3400||checked7<3400)$fatal(1,"too few comparisons");
$display("PASS NATIVE5_TO6_AND7_TO8 DATA_BITS=1662 EPOCH_BITS=1 CHECKED5=%0d CHECKED7=%0d RESETS=54 CLOCK_PS=833",checked5,checked7);
`endif
$finish;end
endmodule
