`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// SELECT unit of the V4.1 hardwired decode core: a streaming top-k.
//
// Semantics are tools/hdc_golden_v41.py `topk_lowest_index`: the k largest
// values, ties to the LOWER index; -0 equals +0 (the golden compares float64
// values).  NaN inputs are outside the contract (the golden never produces
// one).  One instance serves the index top-k (BF16 scores, k = index_topk),
// the candidate-block select (BF16 block maxima with +inf / -inf pins,
// k = candidate_topk_blocks) and the router top-6 (FP32 biased scores).
//
// Interface.  One (value, index) per cycle under valid/ready; `in_last` closes
// a segment and carries that segment's runtime k (`in_k`, clamped to K; 0
// selects nothing).  Indices are unique within a segment and may arrive in any
// order; bubbles are free.  The selected indices leave on consecutive cycles:
//   ORDER = 1: ascending index (position order: the indexer's `sorted(...)`,
//              the router's expert-id order, the candidate-block keep mask);
//   ORDER = 0: rank order (value descending, ties to the lower index), the
//              order `topk_lowest_index` itself returns.
// `out_ninf` flags a selected value equal to -inf (candidate_blocks keeps a
// block only when its score is above -inf).  min(k, n) indices are emitted.
//
// Microarchitecture.
// 1. Key stage.  value -> order-preserving unsigned key (sign flips the
//    magnitude, -0 canonicalised to +0), then R = {valid, key, ~index}: one
//    unsigned compare of R is the golden's lexicographic (value desc, index
//    asc) order and an empty slot (valid = 0) loses to everything.
// 2. Systolic insertion array of K cells.  Every cell holds one entry and
//    compares it with the entry handed down by its left neighbour: it keeps
//    the larger R and passes the smaller one on, registered.  Cell j therefore
//    holds the rank-j entry of everything that has reached it, and a cell's
//    logic is one (1+VW+IW)-bit compare and a 2:1 mux whatever K is -- no
//    broadcast of the incoming element, so the clock does not fall with K.
//    A one-bit wave travels behind the segment's last element: when it
//    reaches cell j that cell's content is final; it is copied into the
//    emission bank and the cell restarts empty for the next segment, so
//    segments stream back to back with no bubble.
// 3. Emission bank of K (valid, index, ninf) cells, loaded along the wave.
//    ORDER = 1 sorts it by index with K phases of odd-even transposition
//    (one (IW+1)-bit compare per neighbour pair, alternating parity; K phases
//    sort K entries); then it shifts out through cell 0, one index per cycle.
//
// Latency (clock edges after the edge that accepts the last element to the
// edge that registers the first output): LAT = K + 2 + (ORDER ? K : 0).
// The bank is busy for LAT + K - 1 edges after that accept; a following
// segment's LAST element waits (in_ready low) until the bank is free, every
// other element is accepted, so segments of at least ~(2 or 3)K elements
// stream at one element per cycle.  Everything is registered: an insertion
// cell, a sort pair and the output are each one compare deep.
//
// Area ~ K x (2 (1+VW+IW+1) + 1 insertion flops + (IW + 2) bank flops + one
// threshold flop, a (1+VW+IW)-bit and an (IW+1)-bit comparator): linear in K.
// A bitonic network is O(K log^2 K) compare-exchanges per input width; it
// only pays for W elements per cycle, which no producer here delivers (the
// reduce/stream unit emits one score per cycle).
// ---------------------------------------------------------------------------
module ot_hdc_select #(
    parameter integer K     = 6,
    parameter integer VW    = 32,     // 16 = BF16 values, 32 = FP32 values
    parameter integer IW    = 16,     // index width
    parameter integer ORDER = 1,      // 1 ascending index, 0 rank order
    parameter integer KW    = $clog2(K + 1)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          in_valid,
    output wire          in_ready,
    input  wire          in_last,
    input  wire [VW-1:0] in_val,
    input  wire [IW-1:0] in_idx,
    input  wire [KW-1:0] in_k,
    output reg           out_valid,
    output reg           out_last,
    output reg  [IW-1:0] out_idx,
    output reg           out_ninf,
    output wire          busy
);
    localparam integer RW = 1 + VW + IW;           // {valid, key, ~index}
    localparam integer PW = RW + 1;                // + ninf

    // -- stage 0: input register ------------------------------------------------
    reg          bsy;
    assign busy     = bsy;
    assign in_ready = !(in_last && bsy);
    wire acc = in_valid && in_ready;
    reg          r0_v, r0_last;
    reg [VW-1:0] r0_val;
    reg [IW-1:0] r0_idx;
    reg [KW-1:0] r0_k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin r0_v <= 1'b0; r0_last <= 1'b0; end
        else begin r0_v <= acc; r0_last <= acc && in_last; end
    end
    always @(posedge clk) begin r0_val <= in_val; r0_idx <= in_idx; r0_k <= in_k; end

    // -- stage 1: key ---------------------------------------------------------------
    wire          zero = (r0_val[VW-2:0] == 0);
    wire [VW-1:0] key  = zero ? {1'b1, {(VW-1){1'b0}}} :
                         r0_val[VW-1] ? ~r0_val : {1'b1, r0_val[VW-2:0]};
    wire          ninf = (r0_val == {1'b1, 8'hFF, {(VW - 9){1'b0}}});   // -inf, BF16 or FP32

    // Flat per-cell vectors: xv = cell j's incoming entry (xv[0] is the stage-1
    // register), sv = its stored entry, mv = what it keeps (final when xw[j]).
    // Only the valid bits and the wave carry a reset.
    wire [PW*K-1:0] xv, sv, mv, lv;
    reg  [K-1:0]    xw;
    reg  [K-1:0]    thr;                           // cell j < this segment's k
    reg             x0_v;
    reg  [PW-2:0]   x0_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin x0_v <= 1'b0; xw[0] <= 1'b0; end
        else begin x0_v <= r0_v; xw[0] <= r0_last; end
    end
    always @(posedge clk) x0_d <= {key, ~r0_idx, ninf};
    assign xv[PW-1:0] = {x0_v, x0_d};
    genvar j;
    generate
        for (j = 0; j < K; j = j + 1) begin : g_thr
            always @(posedge clk) if (r0_last) thr[j] <= (r0_k > j);
        end
    endgenerate

    // -- insertion array ------------------------------------------------------------
    generate
        for (j = 0; j < K; j = j + 1) begin : g_cell
            wire [PW-1:0] xj = xv[PW*j +: PW];
            wire [PW-1:0] sj = sv[PW*j +: PW];
            // R = {valid, key, ~index}; the valid terms are written out so an
            // empty cell's undefined payload never reaches the decision
            wire          gt = xj[PW-1] && (!sj[PW-1] || xj[PW-2:1] > sj[PW-2:1]);
            assign mv[PW*j +: PW] = gt ? xj : sj;
            assign lv[PW*j +: PW] = gt ? sj : xj;
            reg           s_v;
            reg [PW-2:0]  s_d;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) s_v <= 1'b0;
                else s_v <= mv[PW*j + PW - 1] && !xw[j];         // restart empty behind the wave
            end
            always @(posedge clk) s_d <= mv[PW*j +: PW-1];
            assign sv[PW*j +: PW] = {s_v, s_d};
            if (j + 1 < K) begin : g_pass
                reg          x_v;
                reg [PW-2:0] x_d;
                always @(posedge clk or negedge rst_n) begin
                    if (!rst_n) begin x_v <= 1'b0; xw[j+1] <= 1'b0; end
                    else begin x_v <= lv[PW*j + PW - 1]; xw[j+1] <= xw[j]; end
                end
                always @(posedge clk) x_d <= lv[PW*j +: PW-1];
                assign xv[PW*(j+1) +: PW] = {x_v, x_d};
            end
        end
    endgenerate

    // -- emission bank ------------------------------------------------------------------
    localparam integer SK = (ORDER != 0) ? K : 0;
    localparam integer B1 = (K > 1) ? 1 : 0;
    localparam integer KM1I = K - 1;
    localparam [KW:0]  KM1 = KM1I[KW:0];
    reg          sorting, emitting;
    reg [KW:0]   pc;
    reg          par;
    reg [K-1:0]  bv, bn;
    reg [IW*K-1:0] bi;
    // swap[j]: the pair (j, j+1) exchanges in this sort phase; the sort key is
    // {empty, index}, so empty cells collect at the end
    wire [K-1:0] swap;
    generate
        for (j = 0; j < K; j = j + 1) begin : g_bank
            localparam integer JL = (j > 0) ? j - 1 : 0;
            localparam integer JR = (j + 1 < K) ? j + 1 : j;
            localparam [0:0]   JP = ((j % 2) == 1);
            if (j + 1 < K) begin : g_cmp
                assign swap[j] = sorting && (par == JP) && bv[JR] &&
                                 (!bv[j] || bi[IW*j +: IW] > bi[IW*JR +: IW]);
            end else begin : g_end
                assign swap[j] = 1'b0;
            end
            wire from_left  = (j > 0) && swap[JL];
            wire from_right = (j + 1 < K) && (swap[j] || emitting);
            always @(posedge clk) begin
                if (xw[j]) begin
                    bv[j] <= mv[PW*j + PW - 1] && thr[j];
                    bi[IW*j +: IW] <= ~mv[PW*j + 1 +: IW];
                    bn[j] <= mv[PW*j];
                end else if (from_left) begin
                    bv[j] <= bv[JL]; bi[IW*j +: IW] <= bi[IW*JL +: IW]; bn[j] <= bn[JL];
                end else if (from_right) begin
                    bv[j] <= bv[JR]; bi[IW*j +: IW] <= bi[IW*JR +: IW]; bn[j] <= bn[JR];
                end else if (emitting) begin
                    bv[j] <= 1'b0;                  // the last cell empties as the bank shifts
                end
            end
        end
    endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bsy <= 1'b0; sorting <= 1'b0; emitting <= 1'b0; pc <= 0; par <= 1'b0;
            out_valid <= 1'b0; out_last <= 1'b0;
        end else begin
            if (acc && in_last) bsy <= 1'b1;
            out_valid <= emitting && bv[0];
            out_last  <= emitting && bv[0] && (pc == KM1 || !bv[B1]);
            if (xw[K-1]) begin                      // the bank's last cell loads on this edge
                pc <= 0; par <= 1'b0;
                if (SK != 0) sorting <= 1'b1; else emitting <= 1'b1;
            end else if (sorting) begin
                pc <= pc + 1'b1; par <= !par;
                if (pc == KM1) begin sorting <= 1'b0; emitting <= 1'b1; pc <= 0; end
            end else if (emitting) begin
                pc <= pc + 1'b1;
                if (pc == KM1) begin emitting <= 1'b0; bsy <= 1'b0; end
            end
        end
    end
    always @(posedge clk) begin out_idx <= bi[IW-1:0]; out_ninf <= bn[0]; end
endmodule
