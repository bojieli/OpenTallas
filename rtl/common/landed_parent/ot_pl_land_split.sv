`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// QW-S5-LP (2026-10-21): wide chunked landing for tools/landed_parent/lp.py specs with "regional_reset_copies": true and
// a landing wider than 32 chunks (W > 32 * CHUNK_BITS).  Identical to ot_pl_land_chunk_w / ot_pl_land_chunk_r (same
// ot_pl_land_local_w / ot_pl_land_local_r per chunk, same slots / epochs / K / reset age) except that the reset input is
// a vector: chunk c is reset by rsi[c / RG], so each regional reset copy drives <= RG (32) chunk rq flops (mapped
// native32 census safe).  lp.py drives every rsi bit from a copy of the SAME last regional stage (same reset age).
// ---------------------------------------------------------------------------------------------------------------------
module ot_pl_land_split_w #(
    parameter integer W = 1088, D = 4, CHUNK_BITS = 24, RG = 32,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D),
    parameter integer NC = (W + CHUNK_BITS - 1) / CHUNK_BITS
) (
    input wire ck,
    input wire [(NC + RG - 1) / RG - 1:0] rsi,
    input wire [W-1:0] i,
    output wire [D*W-1:0] bank,
    output wire [D*(AW+1)-1:0] epo,
    output wire [D*NC-1:0] vld
);
    genvar c, s;
    generate for (c = 0; c < NC; c = c + 1) begin : g_chunk
        localparam integer CW = (W - c*CHUNK_BITS < CHUNK_BITS) ? W - c*CHUNK_BITS : CHUNK_BITS;
        wire [D*CW-1:0] cb;
        wire [D*(AW+1)-1:0] ce;
        wire [D-1:0] cv;
        (* keep_hierarchy = "yes" *) ot_pl_land_local_w #(.W(CW), .D(D)) u_local (
            .ck(ck), .rsi(rsi[c / RG]), .i(i[c*CHUNK_BITS +: CW]), .bank(cb), .epo(ce), .vld(cv));
        for (s = 0; s < D; s = s + 1) begin : g_slot
            assign bank[s*W + c*CHUNK_BITS +: CW] = cb[s*CW +: CW];
        end
        assign vld[c*D +: D] = cv;
        if (c == 0) begin : g_tags
            assign epo = ce;
        end
    end endgenerate
`ifndef SYNTHESIS
    initial if (CHUNK_BITS < 1 || CHUNK_BITS > 24 || RG < 1 || RG > 32)
        $fatal(1, "ot_pl_land_split_w: CHUNK_BITS must be 1..24, RG 1..32");
`endif
endmodule

module ot_pl_land_split_r #(
    parameter integer W = 1088, D = 4, K = 2, CHUNK_BITS = 24, RG = 32,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D),
    parameter integer NC = (W + CHUNK_BITS - 1) / CHUNK_BITS
) (
    input wire ck,
    input wire [(NC + RG - 1) / RG - 1:0] rsi,
    input wire [D*W-1:0] bank,
    input wire [D*(AW+1)-1:0] epo,
    input wire [D*NC-1:0] vld,
    output wire [W-1:0] o
);
    genvar c, s;
    generate for (c = 0; c < NC; c = c + 1) begin : g_chunk
        localparam integer CW = (W - c*CHUNK_BITS < CHUNK_BITS) ? W - c*CHUNK_BITS : CHUNK_BITS;
        wire [D*CW-1:0] cb;
        for (s = 0; s < D; s = s + 1) begin : g_slot
            assign cb[s*CW +: CW] = bank[s*W + c*CHUNK_BITS +: CW];
        end
        (* keep_hierarchy = "yes" *) ot_pl_land_local_r #(.W(CW), .D(D), .K(K)) u_local (
            .ck(ck), .rsi(rsi[c / RG]), .bank(cb), .epo(epo), .vld(vld[c*D +: D]), .o(o[c*CHUNK_BITS +: CW]));
    end endgenerate
`ifndef SYNTHESIS
    initial if (CHUNK_BITS < 1 || CHUNK_BITS > 24 || RG < 1 || RG > 32)
        $fatal(1, "ot_pl_land_split_r: CHUNK_BITS must be 1..24, RG 1..32");
`endif
endmodule
