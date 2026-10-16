`timescale 1ns/1ps
// hardcore-1010/c (from hgi-1010/c's lockstep): ot_hgi_vm_unit (per-entry station FIFOs) vs the pre-change unit
// (tb/ot_hgi_vm_unit_ref.sv), NC 8 WP 32 WDIRECT 1 = the die instance (hfd_hgi_vm4); random clients (up to 5 in flight, so
// the overflow / proto_fault path is hit), random wide lanes incl. misrouted lanes; every output (cr, status, wq_done)
// compared every cycle at transaction level.  MUTS != 0 builds the DUT's core with that mutant (the reference stays clean):
// the lockstep must then FAIL.  Prints "PASS VM unit lockstep" or "FATAL".
module tb_hgi_vm_unit_lock;
 parameter integer NC = 8, WP = 32, MUTS = 0;
 reg clk = 0; always #1 clk = ~clk; reg rst_n = 0;
 reg [NC*338-1:0] cq = 0; reg [WP*280-1:0] wq = 0;
 wire [NC*274-1:0] cr_a, cr_b; wire [18:0] st_a, st_b; wire [WP-1:0] wd_a, wd_b;
 wire [15:0] rq0 = 16'd0; wire [279:0] w2q0 = 280'd0;
 ot_hgi_vm_unit #(.NC(NC), .WP(WP), .WDIRECT(1), .MUT(MUTS)) dut (.clk(clk), .rst_n(rst_n), .cq(cq), .cr(cr_a), .status(st_a),
   .wq(wq), .wq_done(wd_a), .rq(rq0), .rq_cr(), .rr(), .w2q(w2q0), .w2q_cr(), .w2q_done());
 ot_hgi_vm_unit_ref #(.NC(NC), .WP(WP), .WDIRECT(1)) ref_ (.clk(clk), .rst_n(rst_n), .cq(cq), .cr(cr_b), .status(st_b),
   .wq(wq), .wq_done(wd_b), .rq(rq0), .rq_cr(), .rr(), .w2q(w2q0), .w2q_cr(), .w2q_done());
 integer out [0:NC-1]; integer cyc = 0, nrsp = 0, nreq = 0, seed = 11, errs = 0, ovf = 0;
 initial begin if (!$value$plusargs("SEED=%d", seed)) seed = 11; $display("SEED=%0d", seed); end  // runtime seed (+SEED=<n> overrides): Verilator 5.050 drops a declaration initialiser read only by $random (tools/seed_init_lint.py)
 initial for (integer c = 0; c < NC; c = c + 1) out[c] = 0;
 always @(negedge clk) if (rst_n) begin
  cyc = cyc + 1;
  if (cr_a !== cr_b || st_a !== st_b || wd_a !== wd_b) begin
   errs = errs + 1; if (errs < 5) $display("MISMATCH cyc %0d st %h/%h", cyc, st_a, st_b);
  end
  for (integer c = 0; c < NC; c = c + 1) if (cr_b[c*274 + 273]) begin out[c] = out[c] - 1; nrsp = nrsp + 1; end
  cq = 0; wq = 0;
  for (integer c = 0; c < NC; c = c + 1) begin
   integer lim; lim = (cyc > 3000 && cyc < 3100 && c == 5) ? 6 : 4;          // a burst of overflows on client 5
   if (out[c] < lim && ($random(seed) & 1)) begin : rqb
    reg [336:0] q; reg [14:0] sec;
    sec = $unsigned($random(seed)) % 2048;
    q = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed),
         $random(seed), $random(seed), $random(seed)};
    q[335:304] = {12'd0, sec, 5'd0};
    q[47:16] = ($random(seed) & 1) ? 32'hFFFFFFFF : {$random(seed)} & 32'hF0F0FF0F;
    cq[c*338 +: 338] = {1'b1, q}; out[c] = out[c] + 1; nreq = nreq + 1;
    if (out[c] > 4) ovf = ovf + 1;
   end
  end
  for (integer p = 0; p < WP; p = p + 1) if (($random(seed) & 3) == 0) begin
   wq[p*280 +: 280] = {1'b1, 15'(p + 32 * ($unsigned($random(seed)) % 64)), {8{$random(seed)}}, 8'($random(seed))};
   if (cyc % 997 == 0 && p == 7) wq[p*280 + 264 +: 5] = 5'd9;                   // occasional misrouted lane
  end
 end
 initial begin
  repeat (3) @(negedge clk); rst_n = 1;
  repeat (6000) @(negedge clk);
  cq = 0; wq = 0; repeat (40) @(negedge clk);
  if (errs == 0 && nrsp > 1000 && st_a[18]) $display("PASS VM unit lockstep: %0d requests, %0d responses, %0d overflow pushes, status %h", nreq, nrsp, ovf, st_a);
  else $display("FATAL lockstep errs %0d nrsp %0d status %h", errs, nrsp, st_a);
  $finish;
 end
endmodule
