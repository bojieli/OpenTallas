`timescale 1ns/1ps
// HBM-NSFIX 10-18: ot_hbm_idx_xq_node_static node bench. Random lists every edge; checks y == {b,a} of 2 edges earlier,
// reset value 0 while held (random inputs during reset) and through release, on WI 297 (stack node) and 594 (root). MUT (bench-side faulty DUT wrapper):
// 0 none, 1 swapped halves {a,b}, 2 one extra output stage (3 edges), 3 bit WI/2 of y stuck at 0, 4 reset never asserted.
module tb_xq_node;
 parameter integer WI=297;
 parameter integer MUT=0;
 parameter integer N=4000;
 reg clk=0, rst_n=0;
 reg [WI-1:0] a=0, b=0;
 wire [2*WI-1:0] y_dut;
 reg  [2*WI-1:0] y_x;
 wire [2*WI-1:0] y;
 always #1 clk=~clk;
 wire rst_dut = (MUT==4) ? 1'b1 : rst_n;
 generate if (MUT==1) begin:m1
   ot_hbm_idx_xq_node_static #(.WI(WI)) u(.clk(clk),.rst_n(rst_dut),.a(b),.b(a),.y(y_dut));
 end else begin:m0
   ot_hbm_idx_xq_node_static #(.WI(WI)) u(.clk(clk),.rst_n(rst_dut),.a(a),.b(b),.y(y_dut));
 end endgenerate
 always @(posedge clk) y_x <= y_dut;
 assign y = (MUT==2) ? y_x : (MUT==3) ? (y_dut & ~({{(2*WI-1){1'b0}},1'b1} << (WI/2))) : y_dut;
 reg [2*WI-1:0] h1=0, h2=0;
 integer cyc=0, errors=0, checks=0, k;
 // 10-18 fix: fill a 32-bit-padded word then truncate; the old rnd[j +: 32] wrote past bit WI-1 of the function
 // return (WI 594: bits 576..607), which aborts Icarus 12 vvp (of_RET_VEC4 width assertion, rc 134) on the daemon hosts.
 localparam integer WP=((WI+31)/32)*32;
 function [WI-1:0] rnd; input integer dummy; integer j; reg [WP-1:0] w; begin
   w = {WP{1'b0}};
   for (j=0;j<WP;j=j+32) w[j +: 32] = $random;
   rnd = w[WI-1:0]; end endfunction
 initial begin
   repeat(8) @(posedge clk);
   #0.2 rst_n=1;
 end
 always @(posedge clk) begin
   cyc <= cyc+1;
   // expected: y after this edge = {b,a} sampled 2 edges ago (pipeline h1 -> h2)
   if (!rst_n || cyc < 21) begin
     if (y !== {2*WI{1'b0}} && cyc > 2) begin errors = errors+1; end
     if (cyc > 2) checks = checks+1;
   end else begin
     if (y !== h2) errors = errors+1;
     checks = checks+1;
   end
   h2 <= h1; h1 <= {b,a};
   if (cyc >= 20 || cyc < 7) begin a <= rnd(0); b <= rnd(1); end else begin a <= 0; b <= 0; end
   if (cyc == N) begin
     $display("IDX_XQ_NODE WI%0d MUT%0d checks%0d errors%0d %s", WI, MUT, checks, errors, (errors==0)?"PASS":"FAIL");
     $finish;
   end
 end
endmodule
