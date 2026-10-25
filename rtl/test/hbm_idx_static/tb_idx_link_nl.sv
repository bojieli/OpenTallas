`timescale 1ns/1ps
`default_nettype none
// HBM-BIND B2 (lane hbm-bind-idx 2026-10-24): ot_hbm_idx_topk_link_static NL (selector lists on selected_line) bench.
// REF = the UNCHANGED as-built r18h5 master (source d34578d6f, renamed ot_hbm_idx_topk_link_static_ref, 4 lists).
// DUT = ot_hbm_idx_topk_link_static #(.NL(NL), .MUT(LMUT)); DUT list j = REF list j+OFF, the other REF lists 0 (as the
// as-built selector's empty lists deliver). Checked EVERY edge: tx_v, tx, fault, selected_count identical.
// Stimulus: NFRAME legal frames (clear; ingest edges whose random lane valids add up to exactly 512 records, random gaps;
// flush; 16 emit beats at 8-edge intervals, random rank >= gbase), then 3,000 edges of random control (fault paths).
module tb_idx_link_nl #(parameter integer NL = 1, parameter integer OFF = 0, parameter integer LMUT = 0,
    parameter integer NFRAME = 6, parameter integer SEED = 5);
 reg clk = 0, rst_n = 0; always #1 clk = ~clk;
 reg clear = 0, ingest_v = 0, flush = 0, emit_v = 0; reg [3:0] emit_group = 0; reg [7:0] rank = 0, gbase = 0;
 reg [NL*592-1:0] sl = 0; wire [2367:0] sl_r;
 genvar g;
 for (g = 0; g < 4; g = g + 1) begin : g_map
  if (g >= OFF && g < OFF + NL) begin : g_on assign sl_r[g*592 +: 592] = sl[(g-OFF)*592 +: 592]; end
  else begin : g_off assign sl_r[g*592 +: 592] = 592'd0; end
 end
 wire [3:0] rtv, ntv; wire [2179:0] rtx, ntx; wire rf, nf; wire [9:0] rc, nc;
 ot_hbm_idx_topk_link_static_ref ref_u(.clk(clk), .clk_mem({8{clk}}), .rst_n(rst_n), .clear(clear), .ingest_v(ingest_v),
  .selected_line(sl_r), .flush(flush), .emit_v(emit_v), .emit_group(emit_group), .rank(rank), .gbase(gbase),
  .tx_v(rtv), .tx(rtx), .fault(rf), .selected_count(rc));
 ot_hbm_idx_topk_link_static #(.MUT(LMUT), .NL(NL)) dut(.clk(clk), .clk_mem({8{clk}}), .rst_n(rst_n), .clear(clear),
  .ingest_v(ingest_v), .selected_line(sl), .flush(flush), .emit_v(emit_v), .emit_group(emit_group), .rank(rank),
  .gbase(gbase), .tx_v(ntv), .tx(ntx), .fault(nf), .selected_count(nc));
 integer chk = 0, mism = 0, ntx_beats = 0, nflt = 0, seed = SEED, frames_ok = 0;
 always @(posedge clk) if (rst_n) begin
  chk = chk + 1;
  if (rtv !== ntv || rtx !== ntx || rf !== nf || rc !== nc) begin
   mism = mism + 1; if (mism < 5) $display("MISMATCH t=%0t tx_v %h/%h tx_eq %b fault %b/%b count %0d/%0d", $time, rtv, ntv, rtx === ntx, rf, nf, rc, nc);
  end
  if (|rtv) ntx_beats = ntx_beats + 1;
  if (rf) nflt = nflt + 1;
 end
 task automatic idle(input integer n); for (integer i = 0; i < n; i = i + 1) begin
  clear <= 0; ingest_v <= 0; flush <= 0; emit_v <= 0; @(posedge clk); end endtask
 task automatic frame; integer remaining, c; reg [NL*592-1:0] v; begin
  clear <= 1; @(posedge clk); clear <= 0;
  remaining = 512;
  while (remaining > 0) begin
   v = 0; c = 0;
   for (integer q = 0; q < NL; q = q + 1) for (integer l = 0; l < 16; l = l + 1) begin
    v[q*592 + l*37 +: 37] = {20'($random(seed)), 16'($random(seed)), 1'b0};
    if (c < remaining && $unsigned($random(seed)) % 3 != 0) begin v[q*592 + l*37] = 1'b1; c = c + 1; end
   end
   remaining = remaining - c;
   sl <= v; ingest_v <= 1; @(posedge clk); ingest_v <= 0;
   if ($unsigned($random(seed)) % 4 == 0) idle(1 + $unsigned($random(seed)) % 3);
  end
  idle(2); flush <= 1; @(posedge clk); flush <= 0; idle(3);
  for (integer e = 0; e < 16; e = e + 1) begin
   gbase <= 8'($unsigned($random(seed)) % 128); rank <= 8'(128 + $unsigned($random(seed)) % 128);
   emit_group <= 4'(e); emit_v <= 1; @(posedge clk); emit_v <= 0; idle(7);
  end
  idle(6); if (rf === 1'b0) frames_ok = frames_ok + 1;
 end endtask
 initial begin
  idle(4); rst_n = 1; idle(4);
  for (integer f = 0; f < NFRAME; f = f + 1) frame;
  for (integer i = 0; i < 3000; i = i + 1) begin
   for (integer w = 0; w < NL*592; w = w + 32) sl[w +: 32] <= $random(seed);
   clear <= ($unsigned($random(seed)) % 50 == 0); ingest_v <= ($unsigned($random(seed)) % 3 == 0);
   flush <= ($unsigned($random(seed)) % 40 == 0); emit_v <= ($unsigned($random(seed)) % 10 == 0);
   emit_group <= $random(seed); rank <= $random(seed); gbase <= $random(seed); @(posedge clk);
  end
  idle(8);
  $display("IDX_LINK_NL NL=%0d OFF=%0d LMUT=%0d checks=%0d tx_beats=%0d clean_frames=%0d/%0d ref_fault_edges=%0d mismatches=%0d",
   NL, OFF, LMUT, chk, ntx_beats, frames_ok, NFRAME, nflt, mism);
  $display("IDX_LINK_NL %s checks=%0d errors=%0d", (mism == 0 && ntx_beats > 0 && frames_ok == NFRAME) ? "PASS" : "FAIL", chk, mism);
  $finish;
 end
endmodule
`default_nettype wire
