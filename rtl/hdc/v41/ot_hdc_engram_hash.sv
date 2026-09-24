`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Engram n-gram hash unit of the V4.1 decode core: every hash column of every
// Engram layer for one token position per cycle.  II 1, fixed LATENCY 12.
//
// FUNCTION (tools/hdc_golden_v41.EngramTables.hashes, bit for bit).  The unit
// keeps the last ENG_N compressed token ids (newest first; before a sequence's
// first token the history is the pad id).  For layer l and n-gram order s:
//
//     p[l][s]    = tok[s] * mult[l][s]                  (exact, < 2^64)
//     roll[l][s] = p[l][0] ^ p[l][1] ^ ... ^ p[l][s]
//     row[l][(s-1)*H + h] = roll[l][s] mod prime[l][s-1][h] + offset[l][(s-1)*H + h]
//
// for s = 1 .. N-1 and head h.  The row is the address of that column's row in
// layer l's concatenated embedding table (offsets are the cumulative primes).
//
// ARITHMETIC, and why it is exact.
// * The multiply by a constant is three table lookups, one per 4-bit digit of
//   the id (ENG_NIB[p][n] = n * mult, entries < 2^64 because each partial
//   product is at most the whole product), and two 64-bit adds.
// * The modulo by a constant prime q folds the 64-bit value in sixteen 4-bit
//   digits d_j: x = sum_j d_j 2^(4j), so x = sum_j (d_j 2^(4j) mod q)  (mod q).
//   Each term is a constant-table lookup (ENG_RES[c][j][d] = d*2^(4j) mod q),
//   their sum is below 16q, and four conditional subtractions of 8q, 4q, 2q
//   and q leave the residue in [0, q).  No divider, no reciprocal, no rounding:
//   every step is an integer identity, so the result equals Python's `%`.
// * Any 12-bit id is exact (the product stays below 2^64); ids beyond the
//   compressed vocabulary are not the model's, but the unit still hashes them
//   as the golden's integers would.
//
// Stages: 1 window, 2 digit products, 3-4 product adds, 5 XOR prefix,
// 6 residue lookups + pair adds, 7-9 residue adder tree, 10-11 conditional
// subtractions, 12 offset add (output register).
//
// One stream: in_first marks a sequence's first position and resets the
// history to the pad id in the same cycle.
// ---------------------------------------------------------------------------
import ot_hdc_engram_tables_pkg::*;

module ot_hdc_engram_hash (
    input  wire                                   clk,
    input  wire                                   rst_n,
    input  wire                                   in_valid,
    input  wire                                   in_first,
    input  wire [ENG_ID_W-1:0] in_cid,
    output wire                                   out_valid,
    //: column c of layer l at [ENG_ROW_W*(l*ENG_COLS + c) +: ENG_ROW_W]
    output wire [ENG_ROW_W*ENG_LAYERS*
                 ENG_COLS-1:0] out_row
);
    localparam integer LATENCY = 12;
    localparam integer NP = ENG_LAYERS * ENG_N;          // products
    localparam integer NC = ENG_LAYERS * ENG_COLS;       // columns
    localparam integer RW = ENG_RES_W;
    //: local copies: Yosys resolves a package constant under a variable
    //: part-select as an implicit wire, so the tables are indexed through these
    localparam [$bits(ENG_NIB)-1:0] NIB = ENG_NIB;
    localparam [$bits(ENG_RES)-1:0] RES = ENG_RES;

    reg [LATENCY:1] vl;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) vl <= {LATENCY{1'b0}};
        else vl <= {vl[LATENCY-1:1], in_valid};
    end
    assign out_valid = vl[LATENCY];

    // ---- 1: the n-gram window (w[0] newest) -------------------------------------
    reg [ENG_ID_W-1:0] hist [1:ENG_N-1];   // hist[k]: the id k positions back
    reg [ENG_ID_W-1:0] w    [0:ENG_N-1];
    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k = 1; k < ENG_N; k = k + 1) hist[k] <= ENG_PAD;
        end else if (in_valid) begin
            hist[1] <= in_cid;
            for (k = 2; k < ENG_N; k = k + 1) hist[k] <= in_first ? ENG_PAD : hist[k-1];
        end
    end
    always @(posedge clk) begin
        w[0] <= in_cid;
        for (k = 1; k < ENG_N; k = k + 1) w[k] <= in_first ? ENG_PAD : hist[k];
    end

    // ---- 2-4: tok * mult by digit tables --------------------------------------------
    wire [64*NP-1:0] prod_all;
    genvar p, c, j;
    generate
        for (p = 0; p < NP; p = p + 1) begin : g_prod
            wire [ENG_ID_W-1:0] t = w[p % ENG_N];
            localparam [64*16-1:0] TP = NIB[64*16*p +: 64*16];   // this product's 16 entries
            reg [63:0] pp0, pp1, pp2, pa, pb, prod;
            always @(posedge clk) begin
                pp0  <= TP[64*t[3:0]  +: 64];
                pp1  <= TP[64*t[7:4]  +: 64] << 4;
                pp2  <= TP[64*t[11:8] +: 64] << 8;
                pa   <= pp0 + pp1;
                pb   <= pp2;
                prod <= pa + pb;
            end
            assign prod_all[64*p +: 64] = prod;
        end
    endgenerate

    // ---- 5: rolling XOR, one value per (layer, s >= 1) --------------------------------
    //: roll_all[64*(l*N + s) +: 64] for s >= 1
    reg [64*NP-1:0] roll_all;
    integer l, s;
    reg [63:0] acc;
    always @(posedge clk) begin
        for (l = 0; l < ENG_LAYERS; l = l + 1) begin
            acc = prod_all[64*(l*ENG_N) +: 64];
            roll_all[64*(l*ENG_N) +: 64] <= 64'd0;
            for (s = 1; s < ENG_N; s = s + 1) begin
                acc = acc ^ prod_all[64*(l*ENG_N + s) +: 64];
                roll_all[64*(l*ENG_N + s) +: 64] <= acc;
            end
        end
    end

    // ---- 6-12: per column, x mod q + offset ------------------------------------------
    generate
        for (c = 0; c < NC; c = c + 1) begin : g_col
            localparam integer L_ = c / ENG_COLS;
            localparam integer S_ = (c % ENG_COLS) / ENG_HEADS + 1;
            localparam [RW-1:0] Q = ENG_PRIME[RW*c +: RW];
            localparam [ENG_ROW_W-1:0] OFF = ENG_OFFSET[ENG_ROW_W*c +: ENG_ROW_W];
            wire [63:0] x = roll_all[64*(L_*ENG_N + S_) +: 64];
            wire [RW-1:0] r [0:15];
            for (j = 0; j < 16; j = j + 1) begin : g_dig
                localparam [RW*16-1:0] TD = RES[RW*16*(c*16 + j) +: RW*16];   // this digit's 16 residues
                assign r[j] = TD[RW*x[4*j +: 4] +: RW];
            end
            reg [RW:0]   s1 [0:7];
            reg [RW+1:0] s2 [0:3];
            reg [RW+2:0] s3 [0:1];
            reg [RW+3:0] s4;
            reg [RW+2:0] m1;          // < 4q after the 8q and 4q steps
            reg [RW-1:0] m2;          // < q
            integer i;
            // conditional subtract: v - d if v >= d
            function automatic [RW+3:0] csub(input [RW+3:0] v, input [RW+3:0] d);
                reg [RW+4:0] t;
                begin
                    t = {1'b0, v} - {1'b0, d};
                    csub = t[RW+4] ? v : t[RW+3:0];
                end
            endfunction
            reg [RW+3:0] t8, t2;
            reg [ENG_ROW_W-1:0] row_q;
            assign out_row[ENG_ROW_W*c +: ENG_ROW_W] = row_q;
            always @(posedge clk) begin
                for (i = 0; i < 8; i = i + 1) s1[i] <= r[2*i] + r[2*i+1];
                for (i = 0; i < 4; i = i + 1) s2[i] <= s1[2*i] + s1[2*i+1];
                for (i = 0; i < 2; i = i + 1) s3[i] <= s2[2*i] + s2[2*i+1];
                s4 <= s3[0] + s3[1];
                t8 = csub(s4, {Q, 3'b000});
                m1 <= csub(t8, {1'b0, Q, 2'b00});
                t2 = csub({1'b0, m1}, {2'b0, Q, 1'b0});
                m2 <= csub(t2, {3'b0, Q});
                row_q <= {{(ENG_ROW_W-RW){1'b0}}, m2} + OFF;
            end
        end
    endgenerate
endmodule
