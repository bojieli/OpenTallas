`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81-P6 (10-23, COORD S81 RTL item): plan-width SEAM crossing between two abutted die-plan partitions (frame bands).
// Drop-in, cycle-exact replacement of an ot_pl_land_vector_reset_w / ot_pl_land_vector_reset_r pair whose two halves sit
// in different partitions.  Under the die plan every partition has its own clock taps with neighbour flops <= 80 ps
// (TOPDOWN-PLAN R4), so the 4-deep landing ring (which ships D*W bits across the seam) is not functionally needed: the
// seam carries W bits, flop-first in the source partition (face flop) and flop-last in the destination partition.
//
// Exactness (same rsi age on both halves, as the landing requires): the landing pair gives
//     o(t+1) = warm(t) ? i(t-K) : 0,   warm(t) = rq was 1 for the last K cycles (rc reached K)
// and the seam gives o(t+1) = warm(t) ? p_K(t) : 0 with p_1 = (rq ? i : 0) in the source half and p_2..p_K in the
// destination half, i.e. p_K(t) = i(t-K) whenever warm(t) = 1.  Latency E + 1 = K + 1 edges, unchanged.
// Ports keep the landing's rsi vector (one leaf per CHUNK_BITS chunk, same reset forest leaves); bank/epo/vld -> q/d.
// ---------------------------------------------------------------------------------------------------------------------
module ot_pl_seam_w #(
    parameter integer W = 1073, CHUNK_BITS = 24,
    parameter integer CHUNKS = (W + CHUNK_BITS - 1) / CHUNK_BITS
) (
    input  wire              ck,
    input  wire [CHUNKS-1:0] rsi,
    input  wire [W-1:0]      i,
    output wire [W-1:0]      q                          // face flop -> seam (W bits)
);
    genvar c;
    generate for (c = 0; c < CHUNKS; c = c + 1) begin : g_chunk
        localparam integer CW = (W - c*CHUNK_BITS < CHUNK_BITS) ? W - c*CHUNK_BITS : CHUNK_BITS;
        reg rq;
        reg [CW-1:0] p;
        always @(posedge ck) rq <= rsi[c];
        always @(posedge ck) p <= rq ? i[c*CHUNK_BITS +: CW] : {CW{1'b0}};
        assign q[c*CHUNK_BITS +: CW] = p;
    end endgenerate
endmodule

module ot_pl_seam_r #(
    parameter integer W = 1073, K = 2, CHUNK_BITS = 24,
    parameter integer CHUNKS = (W + CHUNK_BITS - 1) / CHUNK_BITS
) (
    input  wire              ck,
    input  wire [CHUNKS-1:0] rsi,
    input  wire [W-1:0]      d,                         // seam (W bits) from ot_pl_seam_w.q
    output wire [W-1:0]      o                          // flop-last -> destination register
);
    localparam integer CK = (K < 2) ? 2 : K;
    genvar c;
    generate for (c = 0; c < CHUNKS; c = c + 1) begin : g_chunk
        localparam integer CW = (W - c*CHUNK_BITS < CHUNK_BITS) ? W - c*CHUNK_BITS : CHUNK_BITS;
        reg rq;
        reg [$clog2(CK + 1)-1:0] rc;                    // saturating age since reset release
        reg [CW-1:0] pad [0:CK-2];                      // p_2 .. p_K
        reg [CW-1:0] oq;
        wire warm = (rc == CK[$clog2(CK + 1)-1:0]);
        always @(posedge ck) rq <= rsi[c];
        always @(posedge ck)
            if (!rq) rc <= '0;
            else if (!warm) rc <= rc + 1'b1;
        always @(posedge ck) pad[0] <= d[c*CHUNK_BITS +: CW];
        for (genvar s = 1; s < CK - 1; s = s + 1) begin : g_pad
            always @(posedge ck) pad[s] <= pad[s-1];
        end
        always @(posedge ck) oq <= warm ? pad[CK-2] : {CW{1'b0}};
        assign o[c*CHUNK_BITS +: CW] = oq;
    end endgenerate
`ifndef SYNTHESIS
    initial if (K < 2) $fatal(1, "ot_pl_seam_r: K must be >= 2 (one flop each side of the seam)");
`endif
endmodule
`default_nettype wire
