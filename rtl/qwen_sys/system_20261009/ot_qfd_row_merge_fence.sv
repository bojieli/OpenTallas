`timescale 1ns/1ps
// sys-takeover 2026-10-09: qfd_row_merge_native_fence -- the binding between the 32 per-PC head owners
// (ot_qfd_pc_head_owner_n, 16-deep SRAM head queues), the row crossbar (ot_qfd_kv_row_arb: source = PC, V halves =
// h_need[2p +: 2], one merged-word credit per tile into the 8-deep ot_qfd_kv_merge_skid queues) and the KV4
// write-then-read fence of kv-die CONTRACT v1.1 (results/arch/qwen_kv_die_20261009/CONTRACT.md, ot_qkvd_kv_merge.sv),
// applied per PC:
//   * FENCE (KV4 semantics, per PC): a head whose row is the TAIL row (it holds t = T-1 of this layer) is held at the
//     head of its PC's in-order queue (the head owner queue; the heads behind it wait with it) until that PC's posted
//     write of the new position's row for THIS layer is acknowledged for every half the head needs (wack lanes
//     {pc[4:0], mask[1:0]}, the 7-bit ACK form of review AB5: no ID, no ordinal).  lay_start clears the per-layer
//     written state; it precedes the layer's first row request and its write (the KV4 lay_start wavefront).
//     No timing assumption: a write ack delayed by any amount is a stall, never a fault.
//   * Source IDs / V halves: the arb's 64 grant bits {pc, half} are packed into the head owners' three ACK lanes
//     {pc, mask} (one lane per granted PC, ascending PC, both halves in one lane when both were granted).
//   * A half granted once is never offered again for the same head.
// STRUCTURE (rev 3: every input is a bare pin flop; the group pre-encode and the write-ack decode run from the pin
// flops into their own registers: ACK +1 edge (grant -> ACK 2 edges, turnaround +3 edges total), fence release +2 edges.)
// (rev 2, rowfence_a/b e34e1c8cb TT -160/-203: 64-grant -> 3-lane packing and the wack decode -> fence were
// one edge, 26-29 levels): both are split at the pin flop, 0 added edges on the ACK path:
//   - grant packing: the pin stage pre-encodes each group of 8 PCs (first three granted PCs, count, >3 flag); the
//     second edge merges the four groups' lanes by prefix offsets into the ACK register.
//   - write acks: the pin stage decodes the three lanes into a 64-bit half mask (+ in-edge duplicate flag); the fence
//     uses that register: +1 edge on a fence release only (<= 1 cycle per layer, the tail head of a PC).
//   - offers / ACK lanes are gated by the registered fault; a violation is flagged on the next edge (sticky).
// Registered boundary: every output is a flop; offer +1 edge, ACK +1 edge (grant -> next head turnaround +2 edges).
// Sticky fault: a grant to a half not on offer, more than three granted PCs in one edge, a duplicate write ack for a
// half within a layer, an empty write-ack mask.  No ECC / parity / IDs / leases.
// MUT (bench only): 1 = fence off (tail heads offered before the write ack); 2 = ACK lane carries pc+1 (wrong source).
module ot_qfd_row_merge_fence #(parameter integer ENABLE=0, NPC=32, MUT=0) (
 input  wire              clk, rst_n,
 input  wire              lay_start,
 input  wire [NPC-1:0]    head_v, head_tail,
 input  wire [2*NPC-1:0]  head_need,
 input  wire [2:0]        wack_v,
 input  wire [20:0]       wack_data,
 input  wire [2*NPC-1:0]  h_grant,
 output reg  [NPC-1:0]    h_v,
 output reg  [2*NPC-1:0]  h_need,
 output reg  [2:0]        ack_v,
 output reg  [20:0]       ack_data,
 output reg               fault
);
 localparam integer NG = NPC/8;
 generate if (!ENABLE) begin : g_off
  always_comb begin h_v = 0; h_need = 0; ack_v = 0; ack_data = 0; fault = 0; end
 end else begin : g_on
  // ---------------- pin stage ----------------
  reg ls_p, ls_q; reg [NPC-1:0] hv_q, ht_q; reg [2*NPC-1:0] hn_q, g_q;
  reg [2:0] wv_p; reg [20:0] wd_p;   // write-ack pin flops (decode is one edge behind the pins; ls_p..ls_q aligns lay_start)
  // write-ack decode
  reg [2*NPC-1:0] wm_d, wm_q; reg wdup_d, wdup_q;
  // static decode: per PC, per lane, a 5-bit compare (no dynamic index)
  reg [2*NPC-1:0] lane_m [0:2];
  always_comb begin
   wdup_d = 0;
   for (integer j = 0; j < 3; j = j + 1) begin
    for (integer q = 0; q < NPC; q = q + 1)
     lane_m[j][2*q +: 2] = (wv_p[j] && wd_p[j*7+2 +: 5] == 5'(q)) ? wd_p[j*7 +: 2] : 2'b00;
    if (wv_p[j] && wd_p[j*7 +: 2] == 2'b00) wdup_d = 1;
   end
   wm_d = lane_m[0] | lane_m[1] | lane_m[2];
   if (|((lane_m[0] & lane_m[1]) | (lane_m[0] & lane_m[2]) | (lane_m[1] & lane_m[2]))) wdup_d = 1;
  end
  // grant pre-encode per group of 8 PCs: first three granted PCs by three masked priority finds (one-hot, then encode)
  reg gl_v_d [0:NG-1][0:2]; reg [2:0] gl_i_d [0:NG-1][0:2]; reg [1:0] gl_m_d [0:NG-1][0:2];
  reg [1:0] gc_d [0:NG-1]; reg go_d [0:NG-1];
  reg [2:0] gl_v_q [0:NG-1]; reg [2:0] gl_i_q [0:NG-1][0:2]; reg [1:0] gl_m_q [0:NG-1][0:2];
  reg [1:0] gc_q [0:NG-1]; reg go_q [0:NG-1];
  function automatic [7:0] first1(input [7:0] x); first1 = x & (~x + 8'd1); endfunction
  reg [7:0] gp, rest, oh;
  always_comb begin
   for (integer g = 0; g < NG; g = g + 1) begin
    for (integer k = 0; k < 8; k = k + 1) gp[k] = |g_q[2*(8*g+k) +: 2];
    rest = gp;
    for (integer l = 0; l < 3; l = l + 1) begin
     oh = first1(rest);
     rest = rest & ~oh;
     gl_v_d[g][l] = |oh;
     gl_i_d[g][l] = {|(oh & 8'hf0), |(oh & 8'hcc), |(oh & 8'haa)};
     gl_m_d[g][l] = 2'b00;
     for (integer k = 0; k < 8; k = k + 1) if (oh[k]) gl_m_d[g][l] = g_q[2*(8*g+k) +: 2];
    end
    go_d[g] = |rest;
    gc_d[g] = 2'(gl_v_d[g][0]) + 2'(gl_v_d[g][1]) + 2'(gl_v_d[g][2]);
   end
  end
  always @(posedge clk or negedge rst_n)
   if (!rst_n) begin
    ls_p <= 0; ls_q <= 0; wv_p <= 0; hv_q <= 0; g_q <= 0; wm_q <= 0; wdup_q <= 0;
    for (integer g = 0; g < NG; g = g + 1) begin gl_v_q[g] <= 0; gc_q[g] <= 0; go_q[g] <= 0; end
   end else begin
    ls_p <= lay_start; ls_q <= ls_p; wv_p <= wack_v; hv_q <= head_v; g_q <= h_grant; wm_q <= wm_d; wdup_q <= wdup_d;
    for (integer g = 0; g < NG; g = g + 1) begin
     gl_v_q[g] <= {gl_v_d[g][2], gl_v_d[g][1], gl_v_d[g][0]}; gc_q[g] <= gc_d[g]; go_q[g] <= go_d[g];
    end
   end
  always @(posedge clk) begin
   ht_q <= head_tail; hn_q <= head_need; wd_p <= wack_data;
   for (integer g = 0; g < NG; g = g + 1) for (integer k = 0; k < 3; k = k + 1) begin gl_i_q[g][k] <= gl_i_d[g][k]; gl_m_q[g][k] <= gl_m_d[g][k]; end
  end
  // ---------------- second stage ----------------
  reg [1:0] written [0:NPC-1];   // halves of this PC's new-position row acknowledged in this layer
  reg [1:0] gm      [0:NPC-1];   // halves of the current head already granted
  reg [2*NPC-1:0] off_q;
  // merge the groups' lanes by prefix offsets (ascending PC)
  reg [2:0] nav; reg [20:0] nad; reg [3:0] off, tot; reg gover; reg [4:0] pcn;
  always_comb begin
   nav = 0; nad = 0; off = 0; gover = 0; pcn = 0;
   for (integer g = 0; g < NG; g = g + 1) begin
    if (go_q[g]) gover = 1;
    for (integer k = 0; k < 3; k = k + 1) if (gl_v_q[g][k] && off + k < 3) begin
     pcn = 5'(8*g) + {2'b00, gl_i_q[g][k]};
     if (MUT == 2) pcn = pcn + 5'd1;
     nav[off + k] = 1'b1;
     nad[(off + k)*7 +: 7] = {pcn, gl_m_q[g][k]};
    end
    off = off + {2'b00, gc_q[g]};
   end
   tot = off;
  end
  wire gbad = gover || tot > 4'd3 || |(g_q & ~off_q);
  reg wbad_w;
  always_comb begin
   wbad_w = wdup_q;
   for (integer p = 0; p < NPC; p = p + 1) if (((ls_q ? 2'b00 : written[p]) & wm_q[2*p +: 2]) != 2'b00) wbad_w = 1;
  end
  // next offer
  reg [NPC-1:0] nv; reg [2*NPC-1:0] nn; reg [1:0] rem, wr;
  always_comb begin
   nv = 0; nn = 0; rem = 0; wr = 0;
   for (integer p = 0; p < NPC; p = p + 1) begin
    wr  = (ls_q ? 2'b00 : written[p]) | wm_q[2*p +: 2];
    rem = hn_q[2*p +: 2] & ~gm[p] & ~g_q[2*p +: 2] & ~h_grant[2*p +: 2];
    nv[p] = hv_q[p] && rem != 2'b00 && (!ht_q[p] || (wr & hn_q[2*p +: 2]) == hn_q[2*p +: 2] || MUT == 1);
    nn[2*p +: 2] = nv[p] ? rem : 2'b00;
   end
  end
  always @(posedge clk or negedge rst_n) begin
   if (!rst_n) begin
    h_v <= 0; h_need <= 0; off_q <= 0; ack_v <= 0; ack_data <= 0; fault <= 0;
    for (integer c = 0; c < NPC; c = c + 1) begin written[c] <= 2'b00; gm[c] <= 2'b00; end
   end else begin
    fault    <= fault || wbad_w || gbad;
    h_v      <= fault ? {NPC{1'b0}} : nv;
    h_need   <= fault ? {2*NPC{1'b0}} : nn;
    off_q    <= h_need;
    ack_v    <= fault ? 3'b000 : nav;
    ack_data <= nad;
    for (integer c = 0; c < NPC; c = c + 1) begin
     written[c] <= (ls_q ? 2'b00 : written[c]) | wm_q[2*c +: 2];
     gm[c]      <= !hv_q[c] ? 2'b00 : (gm[c] | g_q[2*c +: 2]);
    end
   end
  end
  initial if (NPC % 8 != 0) $fatal(1, "NPC must be a multiple of 8");
 end endgenerate
endmodule
