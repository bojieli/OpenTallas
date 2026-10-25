module chain #(parameter W=513,K=4)(input clk,rst,input[W-1:0]d,input ea,output[W-1:0]q,output eq);
 wire[W-1:0]v[0:K];wire[K:0]e;assign v[0]=d;assign e[0]=ea;assign q=v[K];assign eq=e[K];
 for(genvar j=0;j<K;j++)ot_dp_st #(.W(W))u(.clk(clk),.rst_n(rst),.d(v[j]),.ea(e[j]),.q(v[j+1]),.eq(e[j+1]));
endmodule
module check_one #(parameter W=513,K=4,N=5,M=0)(input clk,rst,input integer tick);
 localparam E=N-K;reg[W-1:0]d;reg ea;wire[W-1:0]a,b;wire ae,be;reg[W-1:0]hist[0:4];reg[4:0]eh;integer warm=0;
 chain #(.W(W),.K(K))u0(clk,rst,d,ea,a,ae);chain #(.W(W),.K(N))u1(clk,rst,d,ea,b,be);
 always @(negedge clk)begin for(integer i=0;i<W/32;i++)d[32*i+:32]=$random;ea=$random;end
 always @(posedge clk)begin
  hist[0]<=a;eh[0]<=ae;for(integer i=1;i<5;i++)begin hist[i]<=hist[i-1];eh[i]<=eh[i-1];end
  if(!rst)warm=0;else warm=warm+1;
  #0.1;
  if(warm>20)begin
   if(E==0)begin if(a!==b||ae!==be)$fatal(1,"same-depth mismatch");end
   else if(b!==hist[E-1+(M!=0)]||be!==eh[E-1+(M!=0)])$fatal(1,"knee delayed lockstep mismatch tick%0d K%0d N%0d M%0d",tick,K,N,M);
  end
 end
endmodule
module tb;
 reg clk=0,rst=0;integer tick=0;always #0.4165 clk=~clk;
 check_one #(.W(512),.K(4),.N(5),.M(`MUT))a(clk,rst,tick);
 check_one #(.W(320),.K(3),.N(5))b(clk,rst,tick);
 check_one #(.W(512),.K(4),.N(4))c(clk,rst,tick);
 initial begin repeat(3000)begin @(negedge clk);tick++;rst=(tick>8 && tick%197>8);end $display("KNEE_EQ PASS 3000cycles +1/+2/0 staged data+epoch lockstep");$finish;end
endmodule
