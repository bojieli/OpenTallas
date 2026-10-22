`timescale 1ns/1ps
// HKV-PROMPT6 (10-19): ot_hkv_cnt_la (registered low-half carry lookahead) vs `if (en) q <= q + 1`, random enables and
// resets, at the production shape (64/32) and at small LO so the high half carries and wraps many times (64/4, 10/4,
// 8/2).  -DOT_HKV_CNT_LA_MUTANT (lookahead one count early) must FAIL.
module tb_hkv_cnt_la;
 reg clk=0, rst_n=0, en=0;
 always #1 clk = ~clk;
 wire [63:0] q0, q1; wire [9:0] q2; wire [7:0] q3;
 reg [63:0] r0=0, r1=0; reg [9:0] r2=0; reg [7:0] r3=0;
 ot_hkv_cnt_la #(.W(64),.LO(32)) d0(.clk(clk),.rst_n(rst_n),.en(en),.q(q0));
 ot_hkv_cnt_la #(.W(64),.LO(4))  d1(.clk(clk),.rst_n(rst_n),.en(en),.q(q1));
 ot_hkv_cnt_la #(.W(10),.LO(4))  d2(.clk(clk),.rst_n(rst_n),.en(en),.q(q2));
 ot_hkv_cnt_la #(.W(8),.LO(2))   d3(.clk(clk),.rst_n(rst_n),.en(en),.q(q3));
 always @(posedge clk or negedge rst_n)
  if (!rst_n) begin r0<=0; r1<=0; r2<=0; r3<=0; end
  else if (en) begin r0<=r0+1; r1<=r1+1; r2<=r2+1; r3<=r3+1; end
 integer i, mism=0, seed=7, wraps=0;
 initial begin
  repeat (3) @(negedge clk); rst_n = 1;
  for (i = 0; i < 200000; i = i + 1) begin
   @(negedge clk);
   en = ($random(seed) % 8) != 0;
   if (i == 100000) begin rst_n = 0; @(negedge clk); rst_n = 1; end
  end
  $display("HKV_CNT_LA cycles=%0d q1=%0d q2_wraps=%0d mismatches=%0d", i, q1, wraps, mism);
  if (mism == 0 && wraps > 50) $display("HKV_CNT_LA PASS"); else $display("HKV_CNT_LA FAIL");
  $finish;
 end
 always @(posedge clk) begin
  if (q2 == 10'h3ff && en) wraps <= wraps + 1;
  if (q0 !== r0 || q1 !== r1 || q2 !== r2 || q3 !== r3) begin
   mism <= mism + 1;
   if (mism < 5) $display("MISMATCH t=%0t %h/%h %h/%h %h/%h %h/%h", $time, q0, r0, q1, r1, q2, r2, q3, r3);
  end
 end
endmodule
