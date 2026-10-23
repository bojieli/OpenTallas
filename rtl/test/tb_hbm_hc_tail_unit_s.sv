`timescale 1ns/1ps
// HBM-P5-RTLB 10-23: lock-step bench of the hc_root over-cap split integration twin ot_hbm_hc_tail_unit_static_s
// (tail_s + split Sinkhorn ot_hdc_sinkhorn_s, sink_capture +1 sink edge) against the pinned ot_hbm_hc_tail_unit_static.
// One stimulus (random mixes / bases / scales, NL launches, random spacing >= L + 8, random divider phase at launch):
//   result_v_s(t) === result_v_p(t - SDIV)  on every edge (the documented +1 sink edge = +SDIV core edges: L 496 -> 503);
//   result_s at its result_v === result_p at its result_v (all 768 bits); fault_s === fault_p === 0 throughout.
// Plusargs: +NL=<launches> +SEED=<n>.  Mutant: -GSMUT=1 (CAP not moved: capture before the split out_valid) must FAIL.
module tb_hbm_hc_tail_unit_s;
 parameter integer SMUT = 0;
 localparam integer SDIV = 7;
 reg clk = 0; always #1 clk = ~clk;
 reg rst_n = 0, launch = 0; reg [767:0] mixes = 0, bases = 0; reg [95:0] scales = 0;
 wire rv_p, rv_s, f_p, f_s; wire [767:0] r_p, r_s;
 ot_hbm_hc_tail_unit_static ref0 (.clk(clk), .rst_n(rst_n), .launch(launch), .mixes(mixes), .bases(bases), .scales(scales),
     .result_v(rv_p), .result(r_p), .fault(f_p));
 ot_hbm_hc_tail_unit_static_s #(.SMUT(SMUT)) dut (.clk(clk), .rst_n(rst_n), .launch(launch), .mixes(mixes), .bases(bases),
     .scales(scales), .result_v(rv_s), .result(r_s), .fault(f_s));
 reg [SDIV:1] rvd = 0; reg [767:0] rq [0:15]; integer wr = 0, rd = 0;
 always @(posedge clk) rvd <= {rvd[SDIV-1:1], rv_p};
 integer seed = 1, nl = 40, checks = 0, errors = 0, results = 0, k, j, gap, t = 0, tl = 0, lat_p = -1, lat_s = -1;
 function automatic [31:0] f32(input integer e_lo, input integer e_span); begin
  f32 = {1'($random(seed)), 8'(e_lo + ($unsigned($random(seed)) % e_span)), 23'($random(seed))}; end endfunction
 always @(posedge clk) t <= t + 1;
 always @(posedge clk) if (rst_n) begin
  #0.1; checks = checks + 1;
  if (rv_p) begin rq[wr % 16] = r_p; wr = wr + 1; if (lat_p < 0) lat_p = t - tl; end
  if (rv_s !== rvd[SDIV]) begin errors = errors + 1; if (errors < 6) $display("TAIL_S RESULT_V MISMATCH t=%0d dut=%b ref(t-%0d)=%b", t, rv_s, SDIV, rvd[SDIV]); end
  if (rv_s) begin
   results = results + 1; if (lat_s < 0) lat_s = t - tl;
   if (rd >= wr || r_s !== rq[rd % 16]) begin errors = errors + 1; if (errors < 6) $display("TAIL_S RESULT MISMATCH t=%0d", t); end
   rd = rd + 1;
  end
  if (f_s !== 1'b0 || f_p !== 1'b0) begin errors = errors + 1; if (errors < 6) $display("TAIL_S FAULT t=%0d dut=%b ref=%b", t, f_s, f_p); end
 end
 initial begin
  if ($value$plusargs("SEED=%d", k)) seed = k;
  if ($value$plusargs("NL=%d", k)) nl = k;
  repeat (5) @(negedge clk); rst_n = 1; repeat (3) @(negedge clk);
  for (k = 0; k < nl; k = k + 1) begin
   for (j = 0; j < 24; j = j + 1) begin mixes[j*32 +: 32] = f32(120, 10); bases[j*32 +: 32] = f32(118, 10); end
   for (j = 0; j < 3; j = j + 1) scales[j*32 +: 32] = {1'b0, 8'(125 + ($unsigned($random(seed)) % 4)), 23'($random(seed))};
   launch = 1; tl = t + 1; @(negedge clk); launch = 0;
   gap = 503 + 8 + ($unsigned($random(seed)) % 23);                 // every divider phase at the next launch
   repeat (gap) @(negedge clk);
  end
  repeat (40) @(negedge clk);
  if (errors == 0 && results == nl && wr == nl && lat_s - lat_p == SDIV)
   $display("TAIL_UNIT_S PASS launches=%0d results=%0d checks=%0d latency pinned=%0d split=%0d (+%0d core edges = +1 sink edge) SMUT=%0d",
            nl, results, checks, lat_p, lat_s, lat_s - lat_p, SMUT);
  else $display("TAIL_UNIT_S FAIL errors=%0d results=%0d/%0d ref_results=%0d latency pinned=%0d split=%0d SMUT=%0d", errors, results, nl, wr, lat_p, lat_s, SMUT);
  $finish;
 end
endmodule
