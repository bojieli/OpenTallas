`timescale 1ns/1ps
// HBM-MU-QUAD-4 10-27 (COORD ruling 3): lock-step equivalence bench, OLD split tail unit (ot_hbm_hc_tail_unit_static_s:
// split Sinkhorn on the registered div-7 clock sclk) vs NEW (ot_hbm_hc_tail_unit_static_se: sk cores on clk + sk_en).
// Same stimulus into both.  Checks on every core edge t (sampled mid-cycle at negedge):
//  (1) tail-unit outputs identical: result_v_n(t) === result_v_o(t); result at result_v identical (768 b);
//      fault: MODE 0 both 0 throughout; MODE 1 (wide-range operands, reset before every launch, faults provoked)
//      fault_n(t) === fault_o(t) || (fault_n(t) === fault_o(t-1))  (a sink-detected fault reaches the tail flag
//      at most 1 core edge later) and per-launch sticky fault values identical;
//  (2) every sk-core output and control/state register: NEW(t) === OLD(t-1)  (the sk flops update on edge E+1 with the
//      values the old RTL sampled at the sclk rising edge E): y, fault, out_valid, in_ready, busy, b_q, bbad_q, abad_q,
//      pa, pb, ph, cnt, flt, the 16 st words and the 16 er words.  slow = number of old sclk rising edges covered.
// Plusargs +NL +SEED +MODE.  Params NSTA (stations on sk_en hop), MUT_EN (1 = enable one edge early: must FAIL).
module tb_sk_en_equiv;
 parameter integer NSTA = 0, MUT_EN = 0;
 localparam integer SDIV = 7;
 reg clk = 0; always #1 clk = ~clk;
 reg rst_n = 0, launch = 0; reg [767:0] mixes = 0, bases = 0; reg [95:0] scales = 0;
 wire rv_o, rv_n, f_o, f_n; wire [767:0] r_o, r_n;
 ot_hbm_hc_tail_unit_static_s old_ (.clk(clk), .rst_n(rst_n), .launch(launch), .mixes(mixes), .bases(bases), .scales(scales),
     .result_v(rv_o), .result(r_o), .fault(f_o));
 ot_hbm_hc_tail_unit_static_se #(.NSTA(NSTA), .MUT_EN(MUT_EN)) new_ (.clk(clk), .rst_n(rst_n), .launch(launch), .mixes(mixes),
     .bases(bases), .scales(scales), .result_v(rv_n), .result(r_n), .fault(f_n));
 // sk-core observation vector (outputs + every control/state register + the st / er matrices)
 function automatic [3*512+64:0] pack_o(input integer dummy); integer q; reg [511:0] stv, erv; begin
  for (q = 0; q < 16; q = q + 1) begin stv[q*32 +: 32] = old_.u_tail.sink.u_ss.st[q]; erv[q*32 +: 32] = old_.u_tail.sink.u_s0.er[q]; end
  pack_o = {old_.u_tail.sink.u_ss.y, old_.u_tail.sink.u_s0.b_q, stv, erv, old_.u_tail.sink.u_ss.fault, old_.u_tail.sink.u_ss.out_valid,
            old_.u_tail.sink.u_ss.in_ready, old_.u_tail.sink.u_ss.busy, old_.u_tail.sink.u_s0.bbad_q, old_.u_tail.sink.u_s0.abad_q,
            old_.u_tail.sink.u_ss.r_pa, old_.u_tail.sink.u_ss.r_pb, old_.u_tail.sink.u_ss.ph, old_.u_tail.sink.u_ss.cnt,
            old_.u_tail.sink.u_ss.flt, old_.u_tail.sink_fault, 41'd0}; end endfunction
 function automatic [3*512+64:0] pack_n(input integer dummy); integer q; reg [511:0] stv, erv; begin
  for (q = 0; q < 16; q = q + 1) begin stv[q*32 +: 32] = new_.u_tail.sink.u_ss.st[q]; erv[q*32 +: 32] = new_.u_tail.sink.u_s0.er[q]; end
  pack_n = {new_.u_tail.sink.u_ss.y, new_.u_tail.sink.u_s0.b_q, stv, erv, new_.u_tail.sink.u_ss.fault, new_.u_tail.sink.u_ss.out_valid,
            new_.u_tail.sink.u_ss.in_ready, new_.u_tail.sink.u_ss.busy, new_.u_tail.sink.u_s0.bbad_q, new_.u_tail.sink.u_s0.abad_q,
            new_.u_tail.sink.u_ss.r_pa, new_.u_tail.sink.u_ss.r_pb, new_.u_tail.sink.u_ss.ph, new_.u_tail.sink.u_ss.cnt,
            new_.u_tail.sink.u_ss.flt, new_.u_tail.sink_fault, 41'd0}; end endfunction
 reg [3*512+64:0] po_prev, po, pn; reg fo_prev = 0, sclk_prev = 0, first = 1;
 integer seed = 1, nl = 150, mode = 0, k, j, gap, t = 0;
 integer edges = 0, slow = 0, sk_err = 0, out_err = 0, results_o = 0, results_n = 0, faults_o = 0, faults_n = 0, sk_active = 0;
 reg [767:0] rq [0:15]; integer wr = 0, rd = 0;
 function automatic [31:0] f32(input integer e_lo, input integer e_span); begin
  f32 = {1'($random(seed)), 8'(e_lo + ($unsigned($random(seed)) % e_span)), 23'($random(seed))}; end endfunction
 always @(negedge clk) if (rst_n) begin
  t = t + 1; edges = edges + 1;
  po = pack_o(0); pn = pack_n(0);
  if (old_.sclk && !sclk_prev) slow = slow + 1;        // old sclk rose on the last edge
  if (old_.u_tail.sink.u_ss.busy) sk_active = sk_active + 1;
  if (!first && pn !== po_prev) begin sk_err = sk_err + 1;
   if (sk_err < 6) $display("SK_EN SK MISMATCH t=%0d new(t)!=old(t-1) diff=%h", t, pn ^ po_prev); end
  if (rv_n !== rv_o) begin out_err = out_err + 1; if (out_err < 6) $display("SK_EN RESULT_V MISMATCH t=%0d old=%b new=%b", t, rv_o, rv_n); end
  if (rv_o) begin rq[wr % 16] = r_o; wr = wr + 1; results_o = results_o + 1; end
  if (rv_n) begin results_n = results_n + 1;
   if (rd >= wr || r_n !== rq[rd % 16]) begin out_err = out_err + 1; if (out_err < 6) $display("SK_EN RESULT MISMATCH t=%0d", t); end
   rd = rd + 1; end
  if (mode == 0) begin if (f_o !== 1'b0 || f_n !== 1'b0) begin out_err = out_err + 1; if (out_err < 6) $display("SK_EN FAULT t=%0d old=%b new=%b", t, f_o, f_n); end end
  else if (!(f_n === f_o || f_n === fo_prev)) begin out_err = out_err + 1; if (out_err < 6) $display("SK_EN FAULT TIMING t=%0d old=%b old(t-1)=%b new=%b", t, f_o, fo_prev, f_n); end
  po_prev = po; fo_prev = f_o; sclk_prev = old_.sclk; first = 0;
 end
 initial begin
  if ($value$plusargs("SEED=%d", k)) seed = k;
  if ($value$plusargs("NL=%d", k)) nl = k;
  if ($value$plusargs("MODE=%d", k)) mode = k;
  repeat (5) @(negedge clk); rst_n = 1; repeat (3) @(negedge clk);
  for (k = 0; k < nl; k = k + 1) begin
   if (mode == 1) begin
    // per-launch sticky fault values must agree, then reset both (random divider phase restarts)
    if (f_o !== f_n) begin out_err = out_err + 1; $display("SK_EN STICKY FAULT MISMATCH launch=%0d old=%b new=%b", k, f_o, f_n); end
    faults_o = faults_o + f_o; faults_n = faults_n + f_n;
    @(posedge clk); #0.3 rst_n = 0; first = 1; @(negedge clk); @(negedge clk); rst_n = 1;
    repeat ($unsigned($random(seed)) % 7) @(negedge clk);
   end
   for (j = 0; j < 24; j = j + 1) begin
    mixes[j*32 +: 32] = (mode == 1) ? f32(100, 50) : f32(120, 10);
    bases[j*32 +: 32] = (mode == 1) ? f32(100, 50) : f32(118, 10); end
   for (j = 0; j < 3; j = j + 1) scales[j*32 +: 32] = (mode == 1) ? f32(110, 40) : {1'b0, 8'(125 + ($unsigned($random(seed)) % 4)), 23'($random(seed))};
   launch = 1; @(negedge clk); launch = 0;
   gap = 503 + 8 + ($unsigned($random(seed)) % 23);
   repeat (gap) @(negedge clk);
  end
  repeat (40) @(negedge clk);
  if (mode == 1) begin faults_o = faults_o + f_o; faults_n = faults_n + f_n; end
  if (sk_err == 0 && out_err == 0 && results_o == nl && results_n == nl && slow >= 10000)
   $display("SK_EN PASS mode=%0d NSTA=%0d MUT_EN=%0d launches=%0d results=%0d edges=%0d slow_edges=%0d sk_busy_edges=%0d sk_compares=%0d faults old=%0d new=%0d",
            mode, NSTA, MUT_EN, nl, results_n, edges, slow, sk_active, edges - 1, faults_o, faults_n);
  else $display("SK_EN FAIL mode=%0d NSTA=%0d MUT_EN=%0d sk_err=%0d out_err=%0d results old=%0d new=%0d/%0d edges=%0d slow_edges=%0d faults old=%0d new=%0d",
            mode, NSTA, MUT_EN, sk_err, out_err, results_o, results_n, nl, edges, slow, faults_o, faults_n);
  $finish;
 end
endmodule
