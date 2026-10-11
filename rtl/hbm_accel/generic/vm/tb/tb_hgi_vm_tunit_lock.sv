`timescale 1ns/1ps
// el1011-hbm-hcvm/vm: lockstep of the tiled VM (ot_hgi_vm_tunit) against the pre-change unit (tb/ot_hgi_vm_unit_ref.sv),
// NC 8 WP 32 WDIRECT 1 (die instance hfd_hgi_vm4).  The tiled hub sees cq 2 and wq 3 cycles late, so the reference is fed
// cq delayed 2 / wq delayed 3; then every DUT output is the reference's shifted: cr +7 (valid bit always, payload when
// valid), status +8 (all 19 bits), wq_done +4.  Random clients (the outstanding count follows the DUT's responses; up to 6
// in flight on client 5 in a window, so overflow / proto_fault is hit), random wide lanes incl. misrouted lanes.
// (No out-of-range packet addresses: the reference predates the range check.)  MUTS != 0 builds the DUT with that mutant: the lockstep must FAIL.
module tb_hgi_vm_tunit_lock;
 parameter integer NC = 8, WP = 32, MUTS = 0, NCYC = 6000;
 localparam integer KQ = 2, KW = 3, ER = 7, ES = 8, EW = 4, H = 16;
 reg clk = 0; always #1 clk = ~clk; reg rst_n = 0;
 reg [NC*338-1:0] cq = 0; reg [WP*280-1:0] wq = 0;
 reg [NC*338-1:0] cqd [1:KQ]; reg [WP*280-1:0] wqd [1:KW];
 wire [NC*274-1:0] cr_a, cr_b; wire [18:0] st_a, st_b; wire [WP-1:0] wd_a, wd_b;
 wire [15:0] rq0 = 16'd0; wire [279:0] w2q0 = 280'd0;
 ot_hgi_vm_tunit #(.NC(NC), .WP(WP), .WDIRECT(1), .MUT(MUTS)) dut (.clk(clk), .rst_n(rst_n), .cq(cq), .cr(cr_a), .status(st_a),
   .wq(wq), .wq_done(wd_a), .wq_rdy(), .ap_q(), .ap_cr(8'd0), .ap_done(8'd0), .rq(rq0), .rq_cr(), .rr(), .w2q(w2q0), .w2q_cr(), .w2q_done());
 ot_hgi_vm_unit_ref #(.NC(NC), .WP(WP), .WDIRECT(1)) ref_ (.clk(clk), .rst_n(rst_n), .cq(cqd[KQ]), .cr(cr_b), .status(st_b),
   .wq(wqd[KW]), .wq_done(wd_b), .rq(rq0), .rq_cr(), .rr(), .w2q(w2q0), .w2q_cr(), .w2q_done());
 reg [NC*274-1:0] hcr [0:H-1]; reg [18:0] hst [0:H-1]; reg [WP-1:0] hwd [0:H-1];
 integer out [0:NC-1]; integer cyc = 0, nrsp = 0, nreq = 0, seed = 11, errs = 0, ovf = 0, nwr = 0, nrd = 0, nwq = 0;
 initial begin if (!$value$plusargs("SEED=%d", seed)) seed = 11; $display("SEED=%0d", seed); end
 initial begin for (integer c = 0; c < NC; c = c + 1) out[c] = 0; for (integer k = 1; k <= KQ; k = k + 1) cqd[k] = 0;
   for (integer k = 1; k <= KW; k = k + 1) wqd[k] = 0; end
 always @(negedge clk) if (rst_n) begin
  cyc = cyc + 1;
  for (integer k = H - 1; k > 0; k = k - 1) begin hcr[k] = hcr[k-1]; hst[k] = hst[k-1]; hwd[k] = hwd[k-1]; end
  hcr[0] = cr_b; hst[0] = st_b; hwd[0] = wd_b;
  if (cyc > H) begin
   for (integer c = 0; c < NC; c = c + 1) begin : cmp
    reg [273:0] a, b; a = cr_a[c*274 +: 274]; b = hcr[ER][c*274 +: 274];
    if (a[273] !== b[273] || (b[273] && a[272:0] !== b[272:0])) begin
     errs = errs + 1; if (errs < 6) $display("MISMATCH cr cyc %0d client %0d dut %h ref %h", cyc, c, a[273:256], b[273:256]); end
   end
   if (st_a !== hst[ES]) begin errs = errs + 1; if (errs < 6) $display("MISMATCH status cyc %0d %h / %h", cyc, st_a, hst[ES]); end
   if (wd_a !== hwd[EW]) begin errs = errs + 1; if (errs < 6) $display("MISMATCH wq_done cyc %0d %h / %h", cyc, wd_a, hwd[EW]); end
  end
  for (integer c = 0; c < NC; c = c + 1) if (cr_a[c*274 + 273]) begin out[c] = out[c] - 1; nrsp = nrsp + 1; end
  for (integer k = KQ; k > 1; k = k - 1) cqd[k] = cqd[k-1]; cqd[1] = cq;
  for (integer k = KW; k > 1; k = k - 1) wqd[k] = wqd[k-1]; wqd[1] = wq;
  cq = 0; wq = 0;
  if (cyc > 12 && cyc < NCYC) begin
   for (integer c = 0; c < NC; c = c + 1) begin
    integer lim; lim = (cyc > 3000 && cyc < 3100 && c == 5) ? 6 : 4;
    if (out[c] < lim && ($random(seed) & 1)) begin : rqb
     reg [336:0] q; reg [14:0] sec;
     sec = $unsigned($random(seed)) % 2048;
     q = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed),
          $random(seed), $random(seed), $random(seed)};
     q[335:304] = {12'd0, sec, 5'd0};
     q[47:16] = ($random(seed) & 1) ? 32'hFFFFFFFF : {$random(seed)} & 32'hF0F0FF0F;
     if (q[336]) nwr = nwr + 1; else nrd = nrd + 1;
     cq[c*338 +: 338] = {1'b1, q}; out[c] = out[c] + 1; nreq = nreq + 1;
     if (out[c] > 4) ovf = ovf + 1;
    end
   end
   for (integer p = 0; p < WP; p = p + 1) if (($random(seed) & 3) == 0) begin
    wq[p*280 +: 280] = {1'b1, 15'(p + 32 * ($unsigned($random(seed)) % 64)), {8{$random(seed)}}, 8'($random(seed))};
    if (cyc % 997 == 0 && p == 7) wq[p*280 + 264 +: 5] = 5'd9;
    nwq = nwq + 1;
   end
  end
 end
 initial begin
  repeat (3) @(negedge clk); rst_n = 1;
  repeat (NCYC + 60) @(negedge clk);
  if (errs == 0 && nrsp > 1000 && st_a[18] && st_a[17]) $display("PASS VM tunit lockstep: %0d requests (%0d rd %0d wr), %0d responses, %0d wide, %0d overflow pushes, status %h", nreq, nrd, nwr, nrsp, nwq, ovf, st_a);
  else $display("FATAL lockstep errs %0d nrsp %0d status %h", errs, nrsp, st_a);
  $finish;
 end
endmodule
