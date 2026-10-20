`timescale 1ns/1ps
module tb;
reg clk=0; always #0.4165 clk=~clk;
reg rst_n=0, v=0, fp4=0;
reg [255:0] xq=0,wq=0; reg signed [9:0] xe=0,we=0; reg [7:0] tag=0;
wire ov0,ov1,f0,f1; wire [31:0] y0,y1; wire [7:0] t0,t1;
old_bterm #(.TW(8),.P1S(1),.CSAM(10),.P2S(1),.NS(1)) a(.clk(clk),.rst_n(rst_n),.v(v),.fp4(fp4),.xq(xq),.xe(xe),.wq(wq),.we(we),.tag(tag),.ov(ov0),.y(y0),.f(f0),.otag(t0));
ot_v41_bterm4_w10 #(.TW(8),.P1S(1),.CSAM(10),.P2S(1),.NS(1)) b(.clk(clk),.rst_n(rst_n),.v(v),.fp4(fp4),.xq(xq),.xe(xe),.wq(wq),.we(we),.tag(tag),.ov(ov1),.y(y1),.f(f1),.otag(t1));
integer checked=0,subnormal=0; reg [31:0] rng=32'h17042026;
always @(negedge clk) if(rst_n) begin
 if(ov0!==ov1) $fatal(1,"BTERM_DIFF valid");
 if(ov0) begin
  checked=checked+1;
  if(y0[30:23]==0 && y0[22:0]!=0) subnormal=subnormal+1;
  if({y0,f0,t0} !== {y1,f1,t1}) $fatal(1,"BTERM_DIFF y=%h/%h tag=%h",y0,y1,t0);
 end
end
initial begin
 repeat(4) @(negedge clk); rst_n=1;
 for(integer i=0;i<4096;i=i+1) begin
  @(negedge clk); v=(i%7!=0); fp4=i[0]; tag=8'(i); xe=10'((i%321)-160);we=0;
  for(integer j=0;j<32;j=j+1) begin
   rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
   xq[8*j+:8]=(i<321 ? 8'h38 : (rng[7:0]&8'h77));
   wq[8*j+:8]=(i<321 ? 8'h38 : (rng[15:8]&8'h77));
  end
 end
 @(negedge clk);v=0; repeat(35) @(negedge clk);
 if(checked<3400 || subnormal<5) $fatal(1,"BTERM_COVERAGE checked=%0d subnormal=%0d",checked,subnormal);
 $display("BTERM_NATIVE32 PASS checked=%0d subnormal=%0d",checked,subnormal);$finish;
end
endmodule
