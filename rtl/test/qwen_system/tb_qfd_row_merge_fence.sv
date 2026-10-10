`timescale 1ns/1ps
// sys-takeover 2026-10-09: exact bench of ot_qfd_row_merge_fence against a reference composition:
//   32 in-order head-owner models (a head loads 3 edges after the previous one retires, retires when its ACK lanes cover
//   its V halves, an ACK for a PC without a head / for a half not needed / twice is an error), a random row-arb model
//   (up to 3 PCs a cycle, random halves of what is offered), LAYERS layers with a lay_start wavefront, one tail head per
//   layer in a random PC, and that PC's new-row write acks delayed 0..STALL edges (sometimes split in two halves).
// Checks: every half of every head granted exactly once and ACKed to the right PC (golden scoreboard), heads retire in
// queue order, a tail head is never offered before its PC's write ack for the layer covers its halves (KV4 fence),
// non-tail heads are never held by the fence, all layers drain, no fault.
// +STALL=<n> (default 400: the KV4 mut8-style long write stall).  Mutants: MUT=1 fence off, MUT=2 wrong source.
module tb_qfd_row_merge_fence;
 parameter integer MUT = 0;
 localparam integer N = 32, LAYERS = 24, MAXH = 6;
 reg clk = 0; always #0.416667 clk = ~clk;
 reg rst_n = 0, lay_start = 0;
 reg [N-1:0] head_v = 0, head_tail = 0; reg [2*N-1:0] head_need = 0;
 reg [2:0] wack_v = 0; reg [20:0] wack_data = 0; reg [2*N-1:0] h_grant = 0;
 wire [N-1:0] h_v; wire [2*N-1:0] h_need; wire [2:0] ack_v; wire [20:0] ack_data; wire fault;
 ot_qfd_row_merge_fence #(.ENABLE(1), .NPC(N), .MUT(MUT)) dut(.clk(clk), .rst_n(rst_n), .lay_start(lay_start),
  .head_v(head_v), .head_tail(head_tail), .head_need(head_need), .wack_v(wack_v), .wack_data(wack_data),
  .h_grant(h_grant), .h_v(h_v), .h_need(h_need), .ack_v(ack_v), .ack_data(ack_data), .fault(fault));
 // per-layer head lists
 integer nh [0:N-1]; reg [1:0] need [0:N-1][0:MAXH-1]; reg tail [0:N-1][0:MAXH-1];
 integer hi [0:N-1], wait_n [0:N-1]; reg [1:0] done [0:N-1];
 integer tpc, tidx, wdelay, wsplit, wsent, layer, cyc, retired, total, granted_halves, acked_halves, stall, held;
 reg [1:0] tneed, wcov, wcov_prev; reg [31:0] rng = 32'h2468ace1;
 function [31:0] rnd; begin rng = rng ^ (rng << 13); rng = rng ^ (rng >> 17); rng = rng ^ (rng << 5); rnd = rng; end endfunction
 integer p, k, j, g, pick;
 initial begin
  if (!$value$plusargs("STALL=%d", stall)) stall = 400;
  cyc = 0; granted_halves = 0; acked_halves = 0; held = 0;
  repeat (4) @(negedge clk); rst_n = 1; repeat (3) @(negedge clk);
  for (layer = 0; layer < LAYERS; layer = layer + 1) begin
   total = 0; retired = 0;
   tpc = rnd() % N;
   for (p = 0; p < N; p = p + 1) begin
    nh[p] = (p == tpc) ? 1 + rnd() % MAXH : rnd() % (MAXH + 1);
    for (k = 0; k < nh[p]; k = k + 1) begin need[p][k] = 1 + rnd() % 3; tail[p][k] = 0; end
    hi[p] = 0; wait_n[p] = 3 + rnd() % 3; done[p] = 0; total = total + nh[p];
   end
   tidx = rnd() % nh[tpc]; tail[tpc][tidx] = 1; tneed = need[tpc][tidx];
   wdelay = (layer % 3 == 0) ? stall : rnd() % 60; wsplit = rnd() % 2; wsent = 0; wcov = 0; wcov_prev = 0;
   lay_start = 1; @(negedge clk); lay_start = 0;
   while (retired < total) begin
    @(negedge clk); cyc = cyc + 1;
    if (cyc > 200000) $fatal(1, "watchdog: layer %0d did not drain (retired %0d/%0d)", layer, retired, total);
    if (fault) $fatal(1, "unexpected fault layer %0d", layer);
    // write acks of the new position's row (pc tpc), after wdelay edges, whole or split in two halves
    wack_v = 0; wack_data = 0;
    if (wdelay > 0) wdelay = wdelay - 1;
    else if (wsent < (wsplit ? 2 : 1)) begin
     wack_v[rnd() % 3] = 1'b1;
     for (j = 0; j < 3; j = j + 1) if (wack_v[j])
      wack_data[j*7 +: 7] = {5'(tpc), wsplit ? (wsent == 0 ? 2'b01 : 2'b10) : 2'b11};
     wsent = wsent + 1; wcov = wsplit ? (wsent == 1 ? 2'b01 : 2'b11) : 2'b11;
     wdelay = wsplit ? rnd() % 30 : 0;
    end
    // fence property on what the DUT offers this edge (its offer is 1 edge behind the inputs)
    for (p = 0; p < N; p = p + 1) if (h_v[p] && head_v[p] && head_tail[p] && (wcov_prev & head_need[2*p +: 2]) != head_need[2*p +: 2])
     $fatal(1, "KV4 fence violated: PC%0d tail head offered before its write ack (layer %0d)", p, layer);
    // arb model: up to 3 PCs from the offer
    h_grant = 0; g = 0;
    for (k = 0; k < N && g < 3; k = k + 1) begin
     p = (k + rnd()) % N;
     if (h_v[p] && h_grant[2*p +: 2] == 0 && rnd() % 2) begin
      pick = h_need[2*p +: 2] & (1 + rnd() % 3);
      if (pick == 0) pick = h_need[2*p +: 2];
      h_grant[2*p +: 2] = pick; g = g + 1;
      granted_halves = granted_halves + pick[0] + pick[1];
     end
    end
    // head-owner models consume the DUT's ACK lanes
    for (j = 0; j < 3; j = j + 1) if (ack_v[j]) begin
     p = ack_data[j*7+2 +: 5];
     if (!head_v[p] || (ack_data[j*7 +: 2] & ~need[p][hi[p]]) != 0 || (ack_data[j*7 +: 2] & done[p]) != 0)
      $fatal(1, "ACK to PC%0d mask %b does not match its head (wrong source / half / duplicate)", p, ack_data[j*7 +: 2]);
     done[p] = done[p] | ack_data[j*7 +: 2];
     acked_halves = acked_halves + ack_data[j*7] + ack_data[j*7+1];
    end
    for (p = 0; p < N; p = p + 1) begin
     if (head_v[p] && done[p] == need[p][hi[p]]) begin
      head_v[p] = 0; hi[p] = hi[p] + 1; done[p] = 0; retired = retired + 1; wait_n[p] = 3;
     end else if (!head_v[p] && hi[p] < nh[p]) begin
      if (wait_n[p] > 0) wait_n[p] = wait_n[p] - 1;
      else begin head_v[p] = 1; head_need[2*p +: 2] = need[p][hi[p]]; head_tail[p] = tail[p][hi[p]]; end
     end
     if (!head_v[p]) begin head_need[2*p +: 2] = 0; head_tail[p] = 0; end
    end
    if (head_v[tpc] && head_tail[tpc] && (wcov & tneed) != tneed) held = held + 1;
    wcov_prev = wcov;
   end
  end
  repeat (6) @(negedge clk);
  if (fault || acked_halves != granted_halves) $fatal(1, "scoreboard: granted %0d halves, acked %0d", granted_halves, acked_halves);
  if (held == 0) $fatal(1, "fence never exercised");
  $display("PASS_ROW_FENCE layers=%0d heads_last_layer=%0d halves=%0d fence_hold_edges=%0d cycles=%0d", LAYERS, total, acked_halves, held, cyc);
  $finish;
 end
endmodule
