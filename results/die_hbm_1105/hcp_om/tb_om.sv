`timescale 1ns/1ps
module tb;
 reg clk=0, rst_n=0, v=0; reg [31:0] a=0,b=0; wire [31:0] y3,y5; wire [1:0] e3,e5; wire v3,v5;
 ot_hdc_fp32_mul_fast f(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(y3),.err(e3),.valid_out(v3));
 ot_hdc_fp32_mul_lat #(.LAT(5)) l(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(y5),.err(e5),.valid_out(v5));
 reg [31:0] yd[0:1]; reg [1:0] ed[0:1]; reg vd[0:1]; integer n=0,bad=0,c=0;
 function automatic [31:0] pick(input integer k); integer r; begin r=$urandom_range(0,9);
  case(r) 0: pick=32'h0; 1: pick=32'h7f800000; 2: pick=$urandom&32'h807fffff; 3: pick=32'h7fc00001; 4:pick=($urandom&32'h007fffff)|32'h00800000; default: pick=$urandom; endcase end endfunction
 always #1 clk=~clk;
 always @(posedge clk) begin yd[0]<=y3; yd[1]<=yd[0]; ed[0]<=e3; ed[1]<=ed[0]; vd[0]<=v3; vd[1]<=vd[0];
  if(rst_n && c>8) begin if(vd[1]!==v5) bad<=bad+1; if(v5) begin n<=n+1; if(y5!==yd[1]||e5!==ed[1]) bad<=bad+1; end end end
 always @(negedge clk) begin c<=c+1; rst_n<=(c>3); v<=(c>4)&&($urandom_range(0,7)!=0); a<=pick(0); b<=pick(1);
  if(c==400000) begin $display("OM_EQ %s results %0d bad %0d", bad==0?"PASS":"FAIL",n,bad); $finish; end end
endmodule
