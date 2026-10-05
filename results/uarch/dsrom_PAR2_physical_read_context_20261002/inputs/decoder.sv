`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// SECDED (extended Hamming) decoder for ROM codewords, combinational.
//
// Identical to tools/mem_compiler/ecc.py:
//   cw = { overall_parity, check[R-1:0], data[K-1:0] }
//   data bit j carries the j-th positive integer that is not a power of two
//   (3, 5, 6, 7, 9, ...) as its Hamming position; check bit i is the parity of
//   the data bits whose position has bit i set; the overall parity makes the
//   whole codeword even.
// Outputs the corrected data, `corrected` for a single-bit error anywhere in
// the codeword (data, check or parity bit), and `uncorrectable` for an even
// number of errors (double error) or a syndrome naming no bit.
// ---------------------------------------------------------------------------
module ot_rom_secded_dec #(
    parameter integer K = 64,
    // closed form of the smallest r with 2^r >= K + r + 1; a constant function here was
    // evaluated once and reused for every K by Verilator 4.038
    parameter integer R = (K <= 1) ? 2 : (K <= 4) ? 3 : (K <= 11) ? 4 : (K <= 26) ? 5 : (K <= 57) ? 6 : (K <= 120) ? 7 :
                          (K <= 247) ? 8 : (K <= 502) ? 9 : (K <= 1013) ? 10 : 11,
    parameter integer N = K + R + 1
) (
    input  wire [N-1:0] cw,
    output wire [K-1:0] data,
    output wire         corrected,
    output wire         uncorrectable
);

    // Hamming position of data bit j
    function automatic integer pos_of(input integer j);
        integer p, n;
        begin
            p = 3; n = 0; pos_of = 3;
            while (n <= j) begin
                if ((p & (p - 1)) != 0) begin
                    if (n == j) pos_of = p;
                    n = n + 1;
                end
                p = p + 1;
            end
        end
    endfunction

    wire [R-1:0] syn;
    wire [K-1:0] fix;
    genvar gi;
    generate
        // The covered-bit selection is built per (check bit, data bit) from pos_of,
        // which does not depend on K: a K-dependent constant function (chk_mask)
        // was miscompiled by Verilator 4.038 when two K were elaborated in one
        // design (it reused one instance's masks for the other).
        for (gi = 0; gi < R; gi = gi + 1) begin : g_chk
            wire [K-1:0] t;
            genvar gj;
            for (gj = 0; gj < K; gj = gj + 1) begin : g_bit
                localparam integer PJ = pos_of(gj);
                assign t[gj] = (((PJ >> gi) & 1) != 0) ? cw[gj] : 1'b0;
            end
            assign syn[gi] = cw[K + gi] ^ (^t);
        end
        for (gi = 0; gi < K; gi = gi + 1) begin : g_fix
            localparam integer P = pos_of(gi);
            assign fix[gi] = (syn == P[R-1:0]);
        end
    endgenerate
    wire overall = ^cw;
    wire syn_zero = (syn == {R{1'b0}});
    wire syn_pow2 = ((syn & (syn - 1'b1)) == {R{1'b0}});   // includes zero
    wire hit_data = |fix;
    assign data = cw[K-1:0] ^ (overall ? fix : {K{1'b0}});
    assign corrected = overall & (syn_pow2 | hit_data);
    assign uncorrectable = (~overall & ~syn_zero) | (overall & ~syn_pow2 & ~hit_data);
endmodule
