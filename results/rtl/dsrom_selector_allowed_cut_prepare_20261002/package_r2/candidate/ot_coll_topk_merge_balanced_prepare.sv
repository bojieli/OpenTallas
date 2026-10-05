`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_coll_topk_merge: the select half of COLL_TOPK_MERGE / ARGMAX_MERGE (W15b).
//
// Every die holds the same gathered candidates (the all-gather of each rank's
// n (score, local id) pairs, rank-major), so every die runs this identical,
// deterministic select and needs no second exchange.
//
//   global id  = rank * stride + local id
//   result     = the k global ids of the largest scores, ties to the LOWER
//                global id (tools/hdc_golden_v41.topk_lowest_index: scores
//                compared as values, so -0 == +0), emitted in ascending
//                global-id order, 16 ids a 512-bit word (the last word padded
//                with zeros).
//   order      = candidates are stored rank-major and each rank's local ids
//                ascending (the contract), so buffer order IS global-id order.
//
// Method: exact radix select, then one filter pass.
//   keys       binary32 -> an order-preserving u32 (-0 canonicalised to +0;
//              a NaN score latches fault).
//   HIST pass  d = 0..32/DIG-1: P candidates a cycle; those whose top d*DIG
//              key bits equal the prefix found so far are counted into
//              2^DIG bins by their next DIG bits.  The bin holding the r-th
//              largest extends the prefix and r becomes the rank inside it.
//              After the last pass the prefix is T, the k-th largest key, and
//              r is how many keys equal to T are taken.
//   FILTER     P candidates a cycle in buffer order: take key > T, or
//              key == T while fewer than r equal keys were taken (ties to the
//              lower id, since buffer order is id order).  Taken ids are
//              compacted (prefix counts, one-hot slot select) into a staging
//              buffer that emits OW = PF/LW full words at a time (aligned).
// Cycles (no stalls): (32/DIG) x (N*n/P + 7) + N*n/PF + 9.
// The candidate buffers are register files here (a synthesis stand-in for
// the die's SRAM); all timing-critical logic is pipelined for 1.2 GHz at SS.
// ---------------------------------------------------------------------------
module ot_coll_topk_merge_balanced_prepare #(
    parameter integer BALANCED = 0,
    parameter integer MUTANT = 0,
    parameter integer N     = 4,              // ranks
    parameter integer NMAX  = 512,            // candidates per rank (max); n % P == 0
    parameter integer LW    = 16,             // lanes (u32 elements) in one VM word
    parameter integer LDW   = 1,              // words a load beat: 1 (rank ld_rank) or N (word j is rank j)
    parameter integer P     = 64,             // HIST candidates a cycle (multiple of LW)
    parameter integer PF    = P,              // FILTER candidates a cycle (divides P, multiple of LW): the filter's
                                              // compactor is PF x PF, so a wide P keeps a narrow PF
    parameter integer DIG   = 4,              // radix bits per HIST pass (divides 32)
    parameter integer RB    = (N > 1) ? $clog2(N) : 1,
    parameter integer CAP   = N * NMAX,
    parameter integer CB    = $clog2(CAP + 1),
    parameter integer WB    = $clog2(CAP / LW),
    parameter integer OW    = PF / LW         // output words a cycle (max)
) (
    input  wire              clk,
    input  wire              rst_n,
    // gathered candidates: one 16-lane word of scores (ld_id 0) or local ids (ld_id 1) of rank ld_rank
    input  wire              ld_valid,
    input  wire              ld_id,
    input  wire [RB-1:0]     ld_rank,
    input  wire [WB-1:0]     ld_word,         // word index inside the rank (n / LW words); n stable while loading
    input  wire [32*LW*LDW-1:0] ld_data,
    // command
    input  wire              go,
    input  wire [CB-1:0]     n,               // candidates per rank
    input  wire [CB-1:0]     k,               // 1 <= k <= N * n
    input  wire [31:0]       stride,          // >= n (rank r owns [r*stride, (r+1)*stride))
    output reg               busy,
    output reg               done,            // one cycle, after the last output word
    output reg               fault,           // NaN score, or a bad command
    // result: out_nw words (LW ids each, word 0 in the low bits) a cycle, in order, in aligned groups of OW
    // words (only the last group may be short; the last word zero-padded)
    output reg               out_valid,
    output reg  [$clog2(OW+1)-1:0] out_nw,
    output reg  [32*LW*OW-1:0] out_data,
    output reg               out_last,
    output reg  [31:0]       stat_cycles      // go -> done
);
    generate if(BALANCED!=0) begin:g_balanced
        ot_coll_topk_merge_staged_impl_prepare #(.MUTANT(MUTANT),.N(N), .NMAX(NMAX), .LW(LW), .LDW(LDW), .P(P), .PF(PF), .DIG(DIG), .RB(RB), .CAP(CAP), .CB(CB), .WB(WB), .OW(OW)) u_core (.clk(clk), .rst_n(rst_n), .ld_valid(ld_valid), .ld_id(ld_id), .ld_rank(ld_rank), .ld_word(ld_word), .ld_data(ld_data), .go(go), .n(n), .k(k), .stride(stride), .busy(busy), .done(done), .fault(fault), .out_valid(out_valid), .out_nw(out_nw), .out_data(out_data), .out_last(out_last), .stat_cycles(stat_cycles));
    end else begin:g_original
        ot_coll_topk_merge #(.N(N), .NMAX(NMAX), .LW(LW), .LDW(LDW), .P(P), .PF(PF), .DIG(DIG), .RB(RB), .CAP(CAP), .CB(CB), .WB(WB), .OW(OW)) u_core (.clk(clk), .rst_n(rst_n), .ld_valid(ld_valid), .ld_id(ld_id), .ld_rank(ld_rank), .ld_word(ld_word), .ld_data(ld_data), .go(go), .n(n), .k(k), .stride(stride), .busy(busy), .done(done), .fault(fault), .out_valid(out_valid), .out_nw(out_nw), .out_data(out_data), .out_last(out_last), .stat_cycles(stat_cycles));
    end endgenerate
endmodule
