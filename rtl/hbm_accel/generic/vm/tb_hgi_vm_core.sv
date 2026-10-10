`timescale 1ps/1ps
// ot_hgi_vm_core bench (hgi-takeover): 3 clients, random word-masked writes / reads over a 4,096-sector window that
// exercises every bank and same-bank conflicts, random response back-pressure, a reference word array; then single-
// bit (CE) and double-bit (UE) injections.  PASS needs every read exact, ce == number of CE injections read back,
// ue only after a UE injection, no mask fault.  VM fast path: each client keeps up to 4 requests outstanding and the
// responses must come back in request order (tag / echo / data checked against a per-client queue); MUT 3 (writes answer
// early, out of order) must FAIL.
module tb_hgi_vm_core;
 parameter integer MUT = 0;
 parameter integer WP = 1, WDIRECT = 0;      // WP 32 + WDIRECT 1: random wide-lane writes (lane b, bank b) beside the clients
 localparam integer NC = 3;
 reg clk = 0; always #416 clk = ~clk; reg rst_n = 0;
 reg [NC-1:0] req_v = 0, rsp_r = 0; reg [NC*337-1:0] req = 0; wire [NC-1:0] req_r, rsp_v; wire [NC*273-1:0] rsp;
 wire [15:0] ce; wire ue, mask_fault;
 reg inj_v = 0; reg [4:0] inj_bank = 0; reg [2:0] inj_word = 0; reg [38:0] inj_mask = 0;
 reg [WP-1:0] wl_v; reg [WP*15-1:0] wl_sec = 0; reg [WP*256-1:0] wl_d = 0; reg [WP*8-1:0] wl_m = 0;   // wl_v: set in the initial block (an initializer gives the core's @* no event)
 wire [WP-1:0] wl_done; wire wl_conflict; integer nwl = 0, nwd = 0;
 always @(posedge clk) begin : cnt_wd integer p; for (p = 0; p < WP; p = p + 1) if (wl_done[p]) nwd = nwd + 1; end
 ot_hgi_vm_core #(.NC(NC), .WP(WP), .WDIRECT(WDIRECT), .MUT(MUT)) dut(.clk(clk), .rst_n(rst_n), .req_v(req_v), .req_r(req_r), .req(req), .rsp_v(rsp_v),
  .rsp_r(rsp_r), .rsp(rsp), .ce(ce), .ue(ue), .mask_fault(mask_fault), .inj_v(inj_v), .inj_bank(inj_bank), .inj_word(inj_word),
  .inj_mask(inj_mask), .wl_v(wl_v), .wl_sec(wl_sec), .wl_d(wl_d), .wl_m(wl_m), .wl_done(wl_done), .wl_conflict(wl_conflict));
 reg [31:0] ref_m [0:32767];               // window: sectors 0..4095 (32,768 words)
 integer pp;
 integer i, c, n, w, nrd = 0, nwr = 0, cycles = 0, seed = 7;
 reg [NC-1:0] acc_c = 0; reg [14:0] psec [0:NC-1]; reg pwe [0:NC-1]; reg [15:0] ptag [0:NC-1];
 reg [255:0] wd; reg [31:0] bm;
 // per-client queue of expected responses, in request order
 reg [15:0] qt [0:NC-1][0:7]; reg qw [0:NC-1][0:7]; reg [255:0] qd [0:NC-1][0:7]; reg [14:0] qs [0:NC-1][0:7];
 integer qh [0:NC-1]; integer qn [0:NC-1]; integer maxo = 0;
reg [255:0] last;
 task xact(input we, input [14:0] sec, input [255:0] data);
  begin
   issue(0, we, sec, data, 32'hffffffff, 16'h0a00);
   @(posedge clk); while (!(req_v[0] && req_r[0])) @(posedge clk);
   @(negedge clk); req_v[0] = 0;
   @(posedge clk); while (!rsp_v[0]) @(posedge clk);
   last = rsp[255:0]; @(negedge clk);
  end
 endtask
 task issue(input integer cc, input we, input [14:0] sec, input [255:0] data, input [31:0] mask, input [15:0] tag);
  begin req[cc*337 +: 337] = {we, {12'd0, sec, 5'd0}, data, mask, tag}; req_v[cc] = 1; psec[cc] = sec; pwe[cc] = we; ptag[cc] = tag; end
 endtask
 initial begin
  wl_v = 0;
  for (i = 0; i < 32768; i = i + 1) ref_m[i] = 0;
  repeat (4) @(posedge clk); rst_n = 1; repeat (2) @(posedge clk);
  for (c = 0; c < NC; c = c + 1) begin qh[c] = 0; qn[c] = 0; end
  while (nrd + nwr < 6000) begin
   @(posedge clk); cycles = cycles + 1; if (cycles > 200000) $fatal(1, "FATAL: liveness");
   for (c = 0; c < NC; c = c + 1) begin          // handshakes complete at this edge (pre-edge values)
    if (rsp_v[c] && rsp_r[c]) begin
     if (qn[c] == 0) $fatal(1, "FATAL: client %0d response with nothing outstanding", c);
     if (rsp[c*273 + 257 +: 16] !== qt[c][qh[c] % 8] || rsp[c*273 + 256] !== qw[c][qh[c] % 8])
      $fatal(1, "FATAL: client %0d response out of order / tag: got %h/%0d want %h/%0d", c, rsp[c*273 + 257 +: 16], rsp[c*273 + 256], qt[c][qh[c] % 8], qw[c][qh[c] % 8]);
     if (!qw[c][qh[c] % 8] && rsp[c*273 +: 256] !== qd[c][qh[c] % 8])
      $fatal(1, "FATAL: client %0d read sector %0d: %h != %h", c, qs[c][qh[c] % 8], rsp[c*273 +: 256], qd[c][qh[c] % 8]);
     qh[c] = qh[c] + 1; qn[c] = qn[c] - 1;
    end
   end
   // reads see the memory before this edge's writes (1R1W: same-edge read of a row being written returns old data)
   for (c = 0; c < NC; c = c + 1) if (req_v[c] && req_r[c] && !pwe[c]) begin
    acc_c[c] = 1; nrd = nrd + 1;
    for (w = 0; w < 8; w = w + 1) qd[c][(qh[c] + qn[c]) % 8][w*32 +: 32] = ref_m[psec[c]*8 + w];
   end
   for (c = 0; c < NC; c = c + 1) if (req_v[c] && req_r[c] && pwe[c]) begin
    acc_c[c] = 1; nwr = nwr + 1;
    for (w = 0; w < 8; w = w + 1) if (&req[c*337 + 16 + w*4 +: 4]) ref_m[psec[c]*8 + w] = req[c*337 + 48 + w*32 +: 32];
   end
   // wide lanes land at this edge too (lane b owns bank b: never the same sector as a client write this edge)
   for (pp = 0; pp < WP; pp = pp + 1) if (wl_v[pp]) begin
    nwl = nwl + 1;
    for (w = 0; w < 8; w = w + 1) if (wl_m[pp*8 + w]) ref_m[wl_sec[pp*15 +: 15]*8 + w] = wl_d[pp*256 + w*32 +: 32];
   end
   for (c = 0; c < NC; c = c + 1) if (acc_c[c]) begin
    qt[c][(qh[c] + qn[c]) % 8] = ptag[c]; qw[c][(qh[c] + qn[c]) % 8] = pwe[c]; qs[c][(qh[c] + qn[c]) % 8] = psec[c];
    qn[c] = qn[c] + 1; if (qn[c] > maxo) maxo = qn[c];
    if (qn[c] > 4) $fatal(1, "FATAL: client %0d has %0d outstanding (> 4 granted) ocnt=%0d busy=%b rfn=%0d", c, qn[c], dut.ocnt[c], dut.busy, dut.rf_n[c]);
   end
   @(negedge clk);
   wl_v = 0;
   if (WDIRECT != 0) for (pp = 0; pp < WP; pp = pp + 1) if (($random(seed) & 3) == 0) begin
    wl_v[pp] = 1; wl_sec[pp*15 +: 15] = 15'(pp + 32 * ($unsigned($random(seed)) % 128));
    for (w = 0; w < 8; w = w + 1) begin wl_d[pp*256 + w*32 +: 32] = $random(seed); wl_m[pp*8 + w] = $random(seed); end
   end
   for (c = 0; c < NC; c = c + 1) begin
    if (acc_c[c]) begin req_v[c] = 0; acc_c[c] = 0; end
    rsp_r[c] = ($random(seed) & 3) != 0;
    if (!req_v[c] && ($random(seed) & 7) != 0) begin
     n = $unsigned($random(seed)) % 4096;
     if (($random(seed) & 3) == 0 && qn[c] > 0) n = qs[c][(qh[c] + qn[c] - 1) % 8];   // re-touch the last sector (RAW / WAR)
     for (w = 0; w < 8; w = w + 1) begin wd[w*32 +: 32] = $random(seed); bm[w*4 +: 4] = ($random(seed) & 1) ? 4'hf : 4'h0; end
     issue(c, ($random(seed) & 1), n[14:0], wd, bm, 16'(c*4096 + (nrd + nwr + c) % 4096));
    end
   end
  end
  @(negedge clk); wl_v = 0;
  // drain
  while (qn[0] + qn[1] + qn[2] != 0 || req_v != 0) begin
   @(posedge clk);
   for (c = 0; c < NC; c = c + 1) if (rsp_v[c] && rsp_r[c]) begin qh[c] = qh[c] + 1; qn[c] = qn[c] - 1; end
   for (c = 0; c < NC; c = c + 1) if (req_v[c] && req_r[c]) begin acc_c[c] = 1; qt[c][(qh[c] + qn[c]) % 8] = ptag[c]; qn[c] = qn[c] + 1; end
   @(negedge clk); for (c = 0; c < NC; c = c + 1) begin rsp_r[c] = 1; if (acc_c[c]) begin req_v[c] = 0; acc_c[c] = 0; end end
  end
  if (maxo < 4) $fatal(1, "FATAL: the fast path never reached 4 outstanding (max %0d)", maxo);
  repeat (4) @(posedge clk);
  if (WDIRECT != 0 && (nwl == 0 || nwd != nwl || wl_conflict)) $fatal(1, "FATAL: wide lanes %0d writes %0d dones conflict %0d", nwl, nwd, wl_conflict);
  if (ce !== 0 || ue || mask_fault) $fatal(1, "FATAL: fault-free phase reported ce=%0d ue=%0d mask=%0d", ce, ue, mask_fault);
  // CE: a single-bit flip on a write of sector 5 word 3 (bank 5), read back corrected
  rsp_r = {NC{1'b1}};
  @(negedge clk); inj_v = 1; inj_bank = 5; inj_word = 3; inj_mask = 39'd1 << 17;
  xact(1, 15'd5, {8{32'h12345678}}); inj_v = 0;
  xact(0, 15'd5, 256'd0);
  if (last[3*32 +: 32] !== 32'h12345678 || ce != 1 || ue) $fatal(1, "FATAL: CE not corrected (data %h ce %0d ue %0d)", last[3*32 +: 32], ce, ue);
  // UE: a double-bit flip, read back -> ue
  @(negedge clk); inj_v = 1; inj_bank = 6; inj_word = 0; inj_mask = (39'd1 << 2) | (39'd1 << 30);
  xact(1, 15'd6, {8{32'h0f0f0f0f}}); inj_v = 0;
  xact(0, 15'd6, 256'd0);
  if (!ue) $fatal(1, "FATAL: UE not reported");
  // a misrouted wide lane (lane 3 carrying a bank-4 sector) is dropped and latches wl_conflict
  if (WDIRECT != 0) begin
   @(negedge clk); wl_v = 0; wl_v[3] = 1; wl_sec[3*15 +: 15] = 15'd4; wl_m[3*8 +: 8] = 8'hFF; wl_d[3*256 +: 256] = {8{32'hDEADBEEF}};
   @(negedge clk); wl_v = 0; repeat (3) @(negedge clk);
   xact(0, 15'd4, 256'd0);
   for (w = 0; w < 8; w = w + 1) if (last[w*32 +: 32] !== ref_m[4*8 + w]) $fatal(1, "FATAL: a misrouted wide lane wrote sector 4");
   if (!wl_conflict) $fatal(1, "FATAL: misrouted wide lane not flagged");
  end
  $display("PASS HGI-VM core clients=%0d wide_writes=%0d reads=%0d writes=%0d cycles=%0d max_outstanding=%0d in-order CE corrected UE flagged", NC, nwl, nrd, nwr, cycles, maxo);
  $finish;
 end
endmodule
