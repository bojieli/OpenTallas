`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_pl_pad_ring (HBM-PGLG3 2026-10-20, opt-in lp.py "pad_ring_min"): an N-edge alignment delay with the EXACT behaviour of
// ot_pl_pad #(W, N) (plain register chain, no reset: q after edge t = d sampled at edge t-N+1) built as a RING BUFFER
// (owner SAFE-DESIGN checklist item 5: delay lines >= 3 deep become ring buffers, no long flop->flop hold chains).
//   S = N-1 slots + one output register; per edge: q <= slot[p]; slot[p] <= d; p advances (one-hot, period S).
//   slot[p] was written S edges earlier, so q after edge t = d(t-S) = d(t-N+1)  (== the chain).
// The word is cut into CHUNK-bit chunks, each with its OWN kept one-hot pointer (keep_hierarchy): a pointer bit drives
// 2 x CHUNK loads (slot enables + read AND) <= 32 at CHUNK 12 (native32 census), never a W-wide select.
// The pointer has no reset port (ot_pl_pad has none): a pointer that is not one-hot loads slot 0 on the next edge (power-up
// garbage or the 2-state simulator's zero), after which slots fill in S edges, i.e. the ring equals the chain once N edges
// have passed since power-up -- the same warm-up as the chain's own unreset flops.  N <= 2 falls back to the chain.
// ---------------------------------------------------------------------------------------------------------------------
module ot_pl_pad_ring #(
    parameter integer W = 1,
    parameter integer N = 3,
    parameter integer CHUNK = 12
) (
    input  wire         ck,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate if (N <= 2) begin : g_chain
        ot_pl_pad #(.W(W), .N(N)) u_chain (.ck(ck), .d(d), .q(q));
    end else begin : g_ring
        localparam integer C = (W + CHUNK - 1) / CHUNK;
        for (genvar c = 0; c < C; c = c + 1) begin : g_chunk
            localparam integer CW = (W - c * CHUNK < CHUNK) ? W - c * CHUNK : CHUNK;
            (* keep_hierarchy = "yes" *) ot_pl_pad_ring_local #(.W(CW), .S(N - 1), .ID(c)) u_local (
                .ck(ck), .d(d[c * CHUNK +: CW]), .q(q[c * CHUNK +: CW]));
        end
    end endgenerate
`ifndef SYNTHESIS
    initial if (CHUNK < 1 || CHUNK > 16) $fatal(1, "ot_pl_pad_ring: CHUNK must be 1..16 (pointer fanout)");
`endif
endmodule

module ot_pl_pad_ring_local #(
    parameter integer W = 12,
    parameter integer S = 2,
    parameter integer ID = 0
) (
    input  wire         ck,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    (* keep *) reg [S-1:0] p;
    reg [W-1:0] slot [0:S-1];
    reg ok;
    integer j;
    always @* begin            // p is one-hot
        ok = 1'b0;
        for (j = 0; j < S; j = j + 1) if (p == ({{(S-1){1'b0}}, 1'b1} << j)) ok = 1'b1;
    end
    always @(posedge ck)
        if (ok) p <= {p[S-2:0], p[S-1]};
        else    p <= {{(S-1){1'b0}}, 1'b1};
    reg [W-1:0] rd;
    always @* begin
        rd = {W{1'b0}};
        for (j = 0; j < S; j = j + 1) rd = rd | ({W{p[j]}} & slot[j]);
    end
    always @(posedge ck) q <= rd;
    genvar s;
    generate for (s = 0; s < S; s = s + 1) begin : g_slot
        always @(posedge ck) if (p[s]) slot[s] <= d;
    end endgenerate
endmodule
`default_nettype wire
