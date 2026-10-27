`timescale 1ns/1ps
// HEAD-CORE-R11: ot_v41_fadd SPLIT9 CY_COPY=0 (no kept round-carry copies) == CY_COPY=1 (four kept copies), same cycle,
// every output every cycle: random + corner operands (zeros, subnormals, carry-out on round, overflow, nonfinite) and,
// one add in two, the chain-head case a = +0.  CY_COPY=0 is a structure change only (cyk = the registered round carry
// rnd9[24], the value every copy holds), so the lockstep must be exact for ANY operands.  Negative control: build with
// the CY_COPY=0 branch mutated (tools/s81_head bench recipe) -> must FAIL.
module tb_fadd_cycopy #(parameter [8:0] CUT = 9'h1ff);
 reg clk=0, rst_n=0; always #0.5 clk=~clk;
 reg v=0; reg [31:0] a=0, b=0;
 wire [31:0] y0, y1; wire [1:0] e0, e1; wire v0, v1;
 ot_v41_fadd #(.CUT(CUT), .SPLIT9(1), .CY_COPY(1)) r(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(y0),.err(e0),.valid_out(v0));
 ot_v41_fadd #(.CUT(CUT), .SPLIT9(1), .CY_COPY(0)) d(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(y1),.err(e1),.valid_out(v1));
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
 integer i, n=0, nz=0, ncy=0;
 initial begin
  repeat(3) @(negedge clk); rst_n=1;
  for (i=0;i<400000;i=i+1) begin
   @(negedge clk);
   if ({v1,e1,y1}!=={v0,e0,y0}) $fatal(1,"cy_copy lockstep %0d: %h/%h/%h vs %h/%h/%h", i, v1,e1,y1, v0,e0,y0);
   if (v1) n=n+1;
   if (r.g_cy_copy.cyq[0]) ncy=ncy+1;
   v=$urandom%4!=0;
   if ($urandom%2) begin a=32'd0; b=pick(i); nz=nz+1; end
   else begin a=pick(i); b=($urandom%3==0)? {~a[31],a[30:0]} ^ 32'($urandom%4) : pick(i); end
  end
  if (ncy == 0) $fatal(1, "round carry never 1: bench does not exercise the copies");
  $display("PASS fadd CY_COPY 0 == 1 adds=%0d a0=%0d carry1=%0d", n, nz, ncy); $finish;
 end
endmodule
