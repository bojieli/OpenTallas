`timescale 1ns/1ps
// ot_v41_fadd SPLIT9=1 == SPLIT9=0 (same CUT) one cycle later: random + corner operands (zeros, subnormals, carry-out,
// overflow, nonfinite), 200,000 adds. MUT=1: compare without the +1 offset (must FAIL).
module tb_fadd_split9 #(parameter [8:0] CUT = 9'h1ff, parameter integer MUT = 0);
 reg clk=0, rst_n=0; always #0.5 clk=~clk;
 reg v=0; reg [31:0] a=0, b=0;
 wire [31:0] y0, y1; wire [1:0] e0, e1; wire v0, v1;
 ot_v41_fadd #(.CUT(CUT), .SPLIT9(0)) r(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(y0),.err(e0),.valid_out(v0));
 ot_v41_fadd #(.CUT(CUT), .SPLIT9(1)) d(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(y1),.err(e1),.valid_out(v1));
 reg [34:0] q; always @(posedge clk) q <= {v0,e0,y0};
 function [31:0] pick(input integer k);
  case ($urandom%10)
   0: pick = {1'($urandom), 8'd0, 23'($urandom)};              // subnormal
   1: pick = {1'($urandom), 8'hfe, 23'($urandom)};             // near overflow
   2: pick = {1'($urandom), 8'hff, 23'($urandom%2 ? $urandom : 0)}; // inf / nan
   3: pick = {1'($urandom), 31'd0};                             // zero
   4: pick = {1'($urandom), 8'd127, 23'h7fffff};                // carry-out on round
   default: pick = $urandom;
  endcase
 endfunction
 integer i, n=0;
 initial begin
  repeat(3) @(negedge clk); rst_n=1;
  for (i=0;i<200000;i=i+1) begin
   @(negedge clk);
   if (i>20 && (MUT ? {v1,e1,y1}!=={v0,e0,y0} : {v1,e1,y1}!==q)) $fatal(1,"split9 lockstep %0d", i);
   if (v1) n=n+1;
   v=$urandom%4!=0; a=pick(i); b=($urandom%3==0)? {~a[31],a[30:0]} ^ 32'($urandom%4) : pick(i);
  end
  $display("PASS fadd SPLIT9 == CUT reference +1 adds=%0d", n); $finish;
 end
endmodule
