`timescale 1ps/1fs
module tb;
reg ck=0; always #416.6665 ck=~ck;
reg rst=0;
reg [2223:0] a0;
reg [2247:0] a1;
wire [2223:0] b0;
wire [2247:0] b1;
hfd_stn_v15_cc2224 u0(.ck(ck),.rst(rst),.a(a0),.b(b0));
hfd_stn_v15_cc2248 u1(.ck(ck),.rst(rst),.a(a1),.b(b1));
integer c,i;
initial begin
 a0=0;a1=0;
 for(c=0;c<128;c=c+1)begin
  @(negedge ck);rst=1;
  for(i=0;i<2224;i=i+1)a0[i]=((i*13+c*7)%(3+c%11))==0;
  for(i=0;i<2248;i=i+1)a1[i]=((i*17+c*11)%(5+c%13))==0;
  @(posedge ck);#1;
  if(b0!==a0 || b1!==a1)$fatal(1,"station mismatch cycle=%0d",c);
 end
 $display("V15_STATION PASS cycles=128 bits=4472 period_ps=833.333");$finish;
end
endmodule
