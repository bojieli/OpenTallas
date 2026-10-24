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

// ---------------------------------------------------------------------------------------------------------------------
// S81-P7 (10-23): PLAN forms of the seam, for die-plan partition contents (tools/s81_dv/frame_band_plan.py).  The
// partition wrapper (tools/die_plan gen_rtl) registers every bus at both pins (ot_dp_st, data without reset): that out
// flop is the seam's p_1 and that in flop is its p_2.  So the content keeps only the reset gating and the remaining
// stages: ot_pl_seam_w_pl drives (rq ? i : 0) combinationally into the out boundary flop; ot_pl_seam_r_pl holds
// p_3 .. p_K and the warm-gated flop-last.  wrapper flops + plan forms == ot_pl_seam_w + ot_pl_seam_r, edge for edge.
// ---------------------------------------------------------------------------------------------------------------------
module ot_pl_seam_w_pl #(
    parameter integer W = 1073, CHUNK_BITS = 24,
    parameter integer CHUNKS = (W + CHUNK_BITS - 1) / CHUNK_BITS
) (
    input  wire              ck,
    input  wire [CHUNKS-1:0] rsi,
    input  wire [W-1:0]      i,
    output wire [W-1:0]      q                          // -> the partition's out boundary flop (p_1)
);
    genvar c;
    generate for (c = 0; c < CHUNKS; c = c + 1) begin : g_chunk
        localparam integer CW = (W - c*CHUNK_BITS < CHUNK_BITS) ? W - c*CHUNK_BITS : CHUNK_BITS;
        reg rq;
        always @(posedge ck) rq <= rsi[c];
        assign q[c*CHUNK_BITS +: CW] = rq ? i[c*CHUNK_BITS +: CW] : {CW{1'b0}};
    end endgenerate
endmodule

module ot_pl_seam_r_pl #(
    parameter integer W = 1073, K = 2, CHUNK_BITS = 24,
    parameter integer CHUNKS = (W + CHUNK_BITS - 1) / CHUNK_BITS
) (
    input  wire              ck,
    input  wire [CHUNKS-1:0] rsi,
    input  wire [W-1:0]      d,                         // <- the partition's in boundary flop (p_2)
    output wire [W-1:0]      o
);
    localparam integer CK = (K < 2) ? 2 : K;
    genvar c;
    generate for (c = 0; c < CHUNKS; c = c + 1) begin : g_chunk
        localparam integer CW = (W - c*CHUNK_BITS < CHUNK_BITS) ? W - c*CHUNK_BITS : CHUNK_BITS;
        reg rq;
        reg [$clog2(CK + 1)-1:0] rc;
        reg [CW-1:0] oq;
        wire [CW-1:0] pk;                               // p_K
        wire warm = (rc == CK[$clog2(CK + 1)-1:0]);
        always @(posedge ck) rq <= rsi[c];
        always @(posedge ck)
            if (!rq) rc <= '0;
            else if (!warm) rc <= rc + 1'b1;
        if (CK == 2) begin : g_k2
            assign pk = d[c*CHUNK_BITS +: CW];
        end else begin : g_kn
            reg [CW-1:0] pad [0:CK-3];                  // p_3 .. p_K
            always @(posedge ck) pad[0] <= d[c*CHUNK_BITS +: CW];
            for (genvar s = 1; s < CK - 2; s = s + 1) begin : g_pad
                always @(posedge ck) pad[s] <= pad[s-1];
            end
            assign pk = pad[CK-3];
        end
        always @(posedge ck) oq <= warm ? pk : {CW{1'b0}};
        assign o[c*CHUNK_BITS +: CW] = oq;
    end endgenerate
`ifndef SYNTHESIS
    initial if (K < 2) $fatal(1, "ot_pl_seam_r_pl: K must be >= 2");
`endif
endmodule
// ---------------------------------------------------------------------------------------------------------------------
// S81-P9-RTL (10-23, COORD R3-INTERNAL: reg-reg > 750 um inside a partition): RELAY-PLACEABLE plan forms of the seam.
// tools/die_plan/relay_mid.tcl places a soft station (flops named <path>.u_y_<name>.*) FIRM on the line between its fixed
// D sources and fixed Q sinks, but it traces only through buffers/inverters: the seam's reset gating (rq ? i : 0 in the
// writer, warm ? p_K : 0 in the reader) is an AND in front of / behind the seam flop, so relay_mid saw soft endpoints and
// GPL put the flop next to one end (S81-P8 r3_internal_v45: face -> reader flop-last 760-1318 um, writer source -> out
// boundary flop 844-1237 um).  These forms move the gating onto the flop's ASYNCHRONOUS clear (relay_mid ignores
// non-D pins; the ot_s81_rly RSREG pattern), so the data flops' D comes straight from the fixed source and Q goes
// straight to the fixed sink.  Control flops (rq / rc / wq) stay outside the u_y_* group.  Latency unchanged (K + 1).
//
// ot_pl_seam_r_plq == ot_pl_seam_r_pl edge for edge after reset release: wq is a REGISTERED copy of warm (same next-state
// function as rc), so wq(t) == warm(t) on every cycle, and an async clear held low over edge t+1 gives oq(t+1) = 0 exactly
// when warm(t) = 0.  Only at reset ASSERTION (rsi falling while warm) does oq clear one cycle earlier than the original
// (initialization only; no data edge) -- the same contract as ot_s81_rly RSREG.
// ---------------------------------------------------------------------------------------------------------------------
module ot_pl_seam_r_plq #(
    parameter integer W = 1073, K = 2, CHUNK_BITS = 24,
    parameter integer CHUNKS = (W + CHUNK_BITS - 1) / CHUNK_BITS
) (
    input  wire              ck,
    input  wire [CHUNKS-1:0] rsi,
    input  wire [W-1:0]      d,                         // <- the partition's in boundary flop (p_2)
    output wire [W-1:0]      o
);
    localparam integer CK = (K < 2) ? 2 : K;
    localparam integer CB = $clog2(CK + 1);
    wire [CHUNKS-1:0] wq;
    wire [W-1:0] pk;                                    // p_K
    genvar c;
    generate for (c = 0; c < CHUNKS; c = c + 1) begin : g_chunk
        localparam integer CW = (W - c*CHUNK_BITS < CHUNK_BITS) ? W - c*CHUNK_BITS : CHUNK_BITS;
        reg rq, wr;
        reg [CB-1:0] rc;
        wire warm = (rc == CK[CB-1:0]);
        always @(posedge ck) rq <= rsi[c];
        always @(posedge ck)
            if (!rq) rc <= '0;
            else if (!warm) rc <= rc + 1'b1;
        // wr(t+1) = warm(t+1): the next-state of (rc == CK)
        always @(posedge ck) wr <= rq && (warm || (rc + 1'b1 == CK[CB-1:0]));
        assign wq[c] = wr;
        if (CK == 2) begin : g_k2
            assign pk[c*CHUNK_BITS +: CW] = d[c*CHUNK_BITS +: CW];
        end else begin : g_kn
            reg [CW-1:0] pad [0:CK-3];                  // p_3 .. p_K
            always @(posedge ck) pad[0] <= d[c*CHUNK_BITS +: CW];
            for (genvar s = 1; s < CK - 2; s = s + 1) begin : g_pad
                always @(posedge ck) pad[s] <= pad[s-1];
            end
            assign pk[c*CHUNK_BITS +: CW] = pad[CK-3];
        end
    end endgenerate
    // the flop-last: one relay-placeable station for the whole seam (relay_mid group <path>.u_y_q)
    ot_pl_seam_cq #(.W(W), .CHUNK_BITS(CHUNK_BITS)) u_y_q (.ck(ck), .clr_n(wq), .d(pk), .q(o));
`ifndef SYNTHESIS
    initial if (K < 2) $fatal(1, "ot_pl_seam_r_plq: K must be >= 2");
`endif
endmodule

// ot_pl_seam_w_plr: the plan writer REGISTERED at the source.  For a seam whose writer input i is exactly one relay's
// output (dsfd_rly_* = ot_s81_rly #(RSREG), rs = leaf rse) the relay and the writer gate become ONE flop fed by the
// relay's INPUT ir.  Original: q(t) = rsi(t-1) ? r(t) : 0 with the relay r(t) = e(t-1) ? ir(t-1) : 0, e = the relay's
// reset pin register (RSREG 1: e(t) = rse(t-1), released one edge after rse) or rse itself (RSREG 0).  Here the station
// flops are async-cleared by rsi & e (both registered, monotone at release: no glitch), so q(t) = (rsi(t-1) & e(t-1)) ?
// ir(t-1) : 0 -- the same function edge for edge, latency unchanged, no leaf-age assumption.  The data flops are one
// relay-placeable station <path>.u_y_w: D from the relay's fixed source, Q to the out boundary flop (FIRM face flops), so
// relay_mid puts it on that line.  (e <= rse, not <= 1'b1: cycle-identical, no TIEHI on its D.)
module ot_pl_seam_w_plr #(
    parameter integer W = 1073, CHUNK_BITS = 24,
    parameter integer RSREG = 1,                        // the replaced relay's ot_s81_rly RSREG
    parameter integer CHUNKS = (W + CHUNK_BITS - 1) / CHUNK_BITS
) (
    input  wire              ck,
    input  wire [CHUNKS-1:0] rsi,                       // the writer's reset leaves (one per chunk)
    input  wire              rse,                       // the replaced relay's reset leaf (its rs)
    input  wire [W-1:0]      ir,                        // the replaced relay's input
    output wire [W-1:0]      q                          // -> the partition's out boundary flop (p_1)
);
    wire e;
    generate if (RSREG != 0) begin : g_rsreg
        reg rq;
        always @(posedge ck or negedge rse)
            if (!rse) rq <= 1'b0;
            else rq <= rse;
        assign e = rq;
    end else begin : g_rs
        assign e = rse;
    end endgenerate
    ot_pl_seam_cq #(.W(W), .CHUNK_BITS(CHUNK_BITS)) u_y_w (.ck(ck), .clr_n(rsi & {CHUNKS{e}}), .d(ir), .q(q));
endmodule

// one seam station: W data flops, chunk c asynchronously cleared by clr_n[c] (a registered control flop)
module ot_pl_seam_cq #(
    parameter integer W = 1073, CHUNK_BITS = 24,
    parameter integer CHUNKS = (W + CHUNK_BITS - 1) / CHUNK_BITS
) (
    input  wire              ck,
    input  wire [CHUNKS-1:0] clr_n,
    input  wire [W-1:0]      d,
    output wire [W-1:0]      q
);
    genvar c;
    generate for (c = 0; c < CHUNKS; c = c + 1) begin : g_chunk
        localparam integer CW = (W - c*CHUNK_BITS < CHUNK_BITS) ? W - c*CHUNK_BITS : CHUNK_BITS;
        reg [CW-1:0] r;
        always @(posedge ck or negedge clr_n[c])
            if (!clr_n[c]) r <= {CW{1'b0}};
            else r <= d[c*CHUNK_BITS +: CW];
        assign q[c*CHUNK_BITS +: CW] = r;
    end endgenerate
endmodule
`default_nettype wire
