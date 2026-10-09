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
//     {pc, mask} (one lane per granted PC, both halves in one lane when both were granted).
//   * A half granted once is never offered again for the same head (the offer is withdrawn the edge after the grant
//     and stays withdrawn until the head owner drops head_v).
// Registered boundary: every input is captured in a pin flop (h_grant also withdraws the next offer: 2 gates to the
// offer flop), every output is a flop: +1 edge on the offer, +1 edge on the ACK, so a PC's grant -> ACK -> next-head
// turnaround grows by 2 edges.  Sticky fault (0 cycles): a grant to a half not on offer, more than three granted PCs in
// one edge, a duplicate write ack for a half within a layer, an empty write-ack mask.  No ECC / parity / IDs / leases.
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
 generate if (!ENABLE) begin : g_off
  always @* begin h_v = 0; h_need = 0; ack_v = 0; ack_data = 0; fault = 0; end
 end else begin : g_on
  // pin flops
  reg ls_q; reg [NPC-1:0] hv_q, ht_q; reg [2*NPC-1:0] hn_q, g_q; reg [2:0] wv_q; reg [20:0] wd_q;
  always @(posedge clk or negedge rst_n)
   if (!rst_n) begin ls_q <= 0; hv_q <= 0; wv_q <= 0; g_q <= 0; end
   else begin ls_q <= lay_start; hv_q <= head_v; wv_q <= wack_v; g_q <= h_grant; end
  always @(posedge clk) begin ht_q <= head_tail; hn_q <= head_need; wd_q <= wack_data; end
  reg [1:0] written [0:NPC-1];   // halves of this PC's new-position row acknowledged in this layer
  reg [1:0] gm      [0:NPC-1];   // halves of the current head already granted
  reg [2*NPC-1:0] wmask, off_q;
  reg wbad, gbad;
  reg [NPC-1:0] gpc;
  integer p, j, ng;
  always @* begin
   wmask = 0; wbad = 0;
   for (j = 0; j < 3; j = j + 1) if (wv_q[j]) begin
    if (wd_q[j*7 +: 2] == 2'b00 || (wmask[2*wd_q[j*7+2 +: 5] +: 2] & wd_q[j*7 +: 2]) != 2'b00) wbad = 1;
    wmask[2*wd_q[j*7+2 +: 5] +: 2] = wmask[2*wd_q[j*7+2 +: 5] +: 2] | wd_q[j*7 +: 2];
   end
   for (p = 0; p < NPC; p = p + 1)
    if ((ls_q ? 2'b00 : written[p]) & wmask[2*p +: 2]) wbad = 1;
  end
  // grant check against the offer the arb saw on the grant edge
  always @* begin
   gbad = 0; gpc = 0; ng = 0;
   for (p = 0; p < NPC; p = p + 1) begin
    gpc[p] = |g_q[2*p +: 2];
    ng = ng + gpc[p];
    if ((g_q[2*p +: 2] & ~off_q[2*p +: 2]) != 2'b00) gbad = 1;
   end
   if (ng > 3) gbad = 1;
  end
  // ACK lanes: one per granted PC, ascending PC order
  reg [2:0] nav; reg [20:0] nad; integer n;
  always @* begin
   nav = 0; nad = 0; n = 0;
   for (p = 0; p < NPC; p = p + 1) if (gpc[p] && n < 3) begin
    nav[n] = 1'b1;
    nad[n*7 +: 7] = {5'((MUT == 2) ? (p + 1) % NPC : p), g_q[2*p +: 2]};
    n = n + 1;
   end
  end
  // next offer
  reg [NPC-1:0] nv; reg [2*NPC-1:0] nn; reg [1:0] rem, wr;
  always @* begin
   nv = 0; nn = 0; rem = 0; wr = 0;
   for (p = 0; p < NPC; p = p + 1) begin
    wr  = (ls_q ? 2'b00 : written[p]) | wmask[2*p +: 2];
    rem = hn_q[2*p +: 2] & ~gm[p] & ~g_q[2*p +: 2] & ~h_grant[2*p +: 2];
    nv[p] = hv_q[p] && rem != 2'b00 && (!ht_q[p] || (wr & hn_q[2*p +: 2]) == hn_q[2*p +: 2] || MUT == 1);
    nn[2*p +: 2] = nv[p] ? rem : 2'b00;
   end
  end
  integer c;
  wire bad = fault || wbad || gbad;
  always @(posedge clk or negedge rst_n) begin
   if (!rst_n) begin
    h_v <= 0; h_need <= 0; off_q <= 0; ack_v <= 0; ack_data <= 0; fault <= 0;
    for (c = 0; c < NPC; c = c + 1) begin written[c] <= 2'b00; gm[c] <= 2'b00; end
   end else begin
    fault    <= bad;
    h_v      <= bad ? {NPC{1'b0}} : nv;
    h_need   <= bad ? {2*NPC{1'b0}} : nn;
    off_q    <= h_need;
    ack_v    <= (fault || gbad) ? 3'b000 : nav;
    ack_data <= nad;
    for (c = 0; c < NPC; c = c + 1) begin
     written[c] <= (ls_q ? 2'b00 : written[c]) | wmask[2*c +: 2];
     gm[c]      <= !hv_q[c] ? 2'b00 : (gm[c] | g_q[2*c +: 2]);
    end
   end
  end
 end endgenerate
endmodule
