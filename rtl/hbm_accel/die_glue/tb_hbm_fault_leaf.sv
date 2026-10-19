`timescale 1ns/1ps
`default_nettype none
// SVC-SMALL 2026-10-18: unit bench of ot_hbm_fault_leaf at one die parameter set (N, SYNC_MASK) and one MUT.
// Cycle model: p1 <= in, p2 <= p1, f <= OR(p1 & ~mask | p2 & mask); fault = f.  So after edge e the expected fault is
//   OR over plain bits i of in_i sampled at edge e-1, OR over SYNC bits of in_i sampled at edge e-2
// (fixed latency: bit -> fault 2 edges, SYNC bit -> fault 3 edges, counted from the edge that samples the bit).
// Phases: (1) reset value; (2) every bit alone: a one-edge pulse must give exactly one fault pulse at its latency, never
// earlier or later; (3) every bit held as a level; (4) 20,000 edges of random multi-bit traffic (sparse and dense);
// (5) async reset mid-traffic clears every flop.  Each edge compares fault against the model.
// Exit: "PASS tb_hbm_fault_leaf ... checks=<n>" or "FAIL tb_hbm_fault_leaf ..." ($fatal, non-zero).
module tb_hbm_fault_leaf;
 parameter integer N = 4;
 parameter [63:0] SYNC_MASK = 64'h8;
 parameter integer MUT = 0;
 parameter integer WRAP = 0;   // 1: the per-variant wrapper block ot_hbm_fault_leaf_n<N>_s<mask> (ot_hbm_fault_leaf_variants.sv)
 reg clk = 1'b0, rst_n = 1'b0;
 always #1 clk = ~clk;
 reg [N-1:0] in = {N{1'b0}};
 wire fault;
 generate if (WRAP == 0) begin : g_base
 ot_hbm_fault_leaf #(.N(N), .SYNC_MASK(SYNC_MASK), .MUT(MUT)) dut(.clk(clk), .rst_n(rst_n), .in(in), .fault(fault));
 end else if (N == 8 && SYNC_MASK == 64'h0) begin : g_n8_s0
  ot_hbm_fault_leaf_n8_s0 #(.MUT(MUT)) dut(.clk(clk), .rst_n(rst_n), .in(in), .fault(fault));
 end else if (N == 8 && SYNC_MASK == 64'h40) begin : g_n8_s40
  ot_hbm_fault_leaf_n8_s40 #(.MUT(MUT)) dut(.clk(clk), .rst_n(rst_n), .in(in), .fault(fault));
 end else if (N == 9 && SYNC_MASK == 64'h40) begin : g_n9_s40
  ot_hbm_fault_leaf_n9_s40 #(.MUT(MUT)) dut(.clk(clk), .rst_n(rst_n), .in(in), .fault(fault));
 end else if (N == 11 && SYNC_MASK == 64'h100) begin : g_n11_s100
  ot_hbm_fault_leaf_n11_s100 #(.MUT(MUT)) dut(.clk(clk), .rst_n(rst_n), .in(in), .fault(fault));
 end else begin : g_none
  initial $fatal(1, "FAIL tb_hbm_fault_leaf: no wrapper for N=%0d SYNC_MASK=%h", N, SYNC_MASK);
 end endgenerate
 wire [N-1:0] sm = SYNC_MASK[N-1:0];
 // model: h1 = in sampled at the last edge, h2 = at the one before; m = model fault register
 reg [N-1:0] h1 = 0, h2 = 0; reg m = 0;
 always @(posedge clk or negedge rst_n)
  if (!rst_n) begin h1 <= 0; h2 <= 0; m <= 0; end
  else begin m <= |((h1 & ~sm) | (h2 & sm)); h2 <= h1; h1 <= in; end
 integer errors = 0, checks = 0, pulses = 0, e, i, k;
 always @(negedge clk) begin
  checks = checks + 1;
  if (fault !== m) begin
   errors = errors + 1;
   if (errors < 8) $display("FAULT_LEAF_MISMATCH t=%0t in=%b fault=%b exp=%b", $time, in, fault, m);
  end
 end
 task edge_set(input [N-1:0] v); begin @(posedge clk); #0.2 in = v; end endtask
 initial begin
  #0.2;
  repeat (3) @(posedge clk);
  #0.2 if (fault !== 1'b0) begin errors = errors + 1; $display("FAULT_LEAF_RESET fault=%b", fault); end
  rst_n = 1'b1;
  repeat (4) @(posedge clk);
  // (2) single-bit pulses: the fault must rise exactly at the bit's latency, for one edge
  for (i = 0; i < N; i = i + 1) begin
   edge_set({{(N-1){1'b0}}, 1'b1} << i);
   edge_set({N{1'b0}});
   k = 0;
   for (e = 0; e < 6; e = e + 1) begin @(negedge clk); if (fault) k = k + 1; end
   if (k != 1) begin errors = errors + 1; $display("FAULT_LEAF_PULSE bit %0d fault edges %0d (exp 1)", i, k); end
   pulses = pulses + 1;
  end
  // (3) levels
  for (i = 0; i < N; i = i + 1) begin
   edge_set({{(N-1){1'b0}}, 1'b1} << i);
   repeat (5) @(posedge clk);
   #0.2 if (!fault) begin errors = errors + 1; $display("FAULT_LEAF_LEVEL bit %0d not seen", i); end
   edge_set({N{1'b0}}); repeat (4) @(posedge clk);
  end
  // (4) random traffic
  for (e = 0; e < 20000; e = e + 1) begin
   @(posedge clk); #0.2;
   for (i = 0; i < N; i = i + 1) in[i] = (e % 1000 < 500) ? ($urandom % 16 == 0) : ($urandom % 2 == 0);
  end
  // (5) async reset mid-traffic
  @(posedge clk); #0.2 in = {N{1'b1}}; repeat (3) @(posedge clk);
  #0.5 rst_n = 1'b0; #0.2 if (fault !== 1'b0) begin errors = errors + 1; $display("FAULT_LEAF_ASYNC_RESET fault=%b", fault); end
  in = {N{1'b0}}; repeat (2) @(posedge clk); #0.2 rst_n = 1'b1;
  repeat (6) @(posedge clk); #0.2;
  if (errors == 0)
   $display("PASS tb_hbm_fault_leaf N=%0d SYNC_MASK=%h MUT=%0d pulses=%0d checks=%0d", N, SYNC_MASK, MUT, pulses, checks);
  else $fatal(1, "FAIL tb_hbm_fault_leaf N=%0d SYNC_MASK=%h MUT=%0d errors=%0d checks=%0d", N, SYNC_MASK, MUT, errors, checks);
  $finish;
 end
endmodule
`default_nettype wire
