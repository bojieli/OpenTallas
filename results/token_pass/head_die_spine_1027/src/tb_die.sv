`timescale 1ns/1ps
// TOK-ALL-15: HEAD die spine/chain path on the GENERATED die top (tools/die_plan/gen.py rtl of main die_plan
// s81_head): all 264 hd_tile partitions = the native partition (ot_s81hd_tile_p -> ot_s81hd_tile_native + CV/ROM
// models, TOK-14 vehicle) with rank-0 released head.weight images; 6 spine nodes, 12 chains, 24 turn halves and every
// ft station partition as generated; die reset/START via the generated wavefront.  Off-path leaves stubbed.
module tb;
 reg ck = 0; always #0.4165 ck = ~ck;
 reg rst_n = 0, start = 0;
 s81_head_top dut (.clk(ck), .rst_n(rst_n), .start(start));
 integer maxc;
 initial begin
  if (!$value$plusargs("MAXC=%d", maxc)) maxc = 12000;
  repeat (8) @(negedge ck); rst_n = 1; repeat (4) @(negedge ck); start = 1;
  repeat (maxc) @(negedge ck);
  $finish;
 end
endmodule
