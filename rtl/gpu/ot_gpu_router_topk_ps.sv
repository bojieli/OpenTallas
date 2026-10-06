`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Router top-K selector with a PIPELINED SELECTION (HBM accelerator MoE router, 1.2 GHz SS).
// Opt-in successor of ot_gpu_router_topk (rtl/gpu/ot_gpu_router_topk.sv): same ports, same
// parameters, same selections (the K largest of {okey(value), ~index}: value descending, the lower
// index first on ties, -0 == +0, NaN / Inf ordered by their key bits), emitted ascending by id.
//
// PIPESEL = 0 (default): the reference ot_gpu_router_topk, unchanged.
// PIPESEL = 1: pipelined selection at the full P scores a cycle (one vector per N / P beats).
// PIPESEL = 2: fallback, the same core at P / 2 a cycle behind a 2:1 serialiser; the producer
//              may present a beat at most every other cycle (+N / P cycles a vector).
//
// The reference keeps P per-lane sorted lists with a one-cycle compare-insert recurrence (the
// timing wall at 1.2 GHz).  Here no value-dependent state is updated every cycle, and every
// magnitude compare is split over two registered stages: 8-bit chunk (gt, eq) pairs, then the
// chunk combine (an explicit log-depth tree on plain gates: no relational operator on a key is
// left to synthesis, which maps one through $alu to a ripple chain).
//   S0  pin capture (in_valid, in_last, in_vals: flop-direct, no logic before the flop)
//   S1  order-preserving integer key per value: okey(f) = f == -0 ? 0x8000_0000 :
//       f[31] ? ~f : f | 1 << 31 (exactly the reference's key; no FP comparator anywhere)
//   S2  chunk compares of all P (P-1) / 2 lane pairs of the beat;  S3 their combine: lane j beats
//       lane m > j iff key_j >= key_m (equal keys go to the lower index, as in the reference)
//   S4  rank of every lane = how many lanes beat it (adder-tree popcount of P - 1 bits)
//   S5  local top-K of the beat, sorted: slot k = the lane whose rank is k (one-hot AND-OR mux)
//   S6..S8  NB = 4 running top-K banks take the beats round-robin, so a bank sees a beat at most
//       every 4th cycle and its merge with the running list is a 3-stage recurrence:
//       S6 chunk compares of the bank's K entries against the beat's K, S7 combine (the running
//       entry wins a tie: it has the lower index) + merge-path one-hot slot selects (entry i of
//       list A lands in slot i + |B ahead of it|; hold / fresh-vector folded into the selects),
//       S8 the bank register takes the AND-OR mux of {bank, beat}: no enable over the bank.
//   S9  all banks snapshotted 3 cycles after the vector's last beat left S5 (the one cycle in
//       which every bank holds its final list).
//   S10..S15  2-level merge tree of the 4 bank lists on the full key {okey, ~index} (the banks
//       interleave indices), 3 stages a level (chunk compare | combine + selects | mux).
//   S16..S18  ascending by id (compare | rank | select) -> out_ids / out_valid flops at the pins.
// Latency: in_valid of the last beat at the pins -> out_valid 19 cycles (the reference: 23,
// ot_gpu_router_topk_f: 24, by the bench's measure).  Throughput unchanged (PIPESEL = 1).
// Reset: rst_n asserts asynchronously into a 2-flop synchroniser only; all control flops take a
// registered synchronous reset; datapath flops have no reset and no enable.
// NEG (test only, default 0) plants a known error for the bench's negative controls:
//   1 bank merge gives ties to the arriving beat, 2 local sort gives ties to the higher lane,
//   3 -0 is not canonicalised, 4 the final merge ignores the index on ties.
// ---------------------------------------------------------------------------
// two descending K-lists of {key, idx} (EW bits; order on {key, ~idx}) -> their top K, descending.
// 3 registered stages; HA / HB: list present (an absent list loses every compare).
module ot_gpu_router_ps_merge #(
    parameter integer K   = 6,
    parameter integer IW  = 9,
    parameter integer NEG = 0
) (
    input  wire               clk,
    input  wire [K*(32+IW)-1:0] a,
    input  wire [K*(32+IW)-1:0] b,
    input  wire               ha,
    input  wire               hb,
    output reg  [K*(32+IW)-1:0] q,
    output reg                hq
);
    localparam integer EW = 32 + IW;
    // Compare helpers (inlined in each module of this file).  Every magnitude compare is
    // an explicit tree on plain gates: 8-bit chunk (gt, eq) pairs (registered by the caller), then a
    // log-depth chunk combine.  A relational operator on a key would be mapped through $alu to a ripple
    // carry chain (measured 750 ps WC pre-repair on the first route); none is used on a key.
    function automatic [1:0] cmp8(input [7:0] a, input [7:0] b);   // {a > b, a == b}
        reg [7:0] g, e;
        integer s, t;
        begin
            g = a & ~b; e = ~(a ^ b);
            for (s = 1; s < 8; s = s * 2)
                for (t = 0; t < 8; t = t + 2 * s) begin
                    g[t] = g[t+s] | (e[t+s] & g[t]);
                    e[t] = e[t+s] & e[t];
                end
            cmp8 = {g[0], e[0]};
        end
    endfunction
    // operands zero-extended to 64 bits: 8 chunks, chunk c at [2c+1:2c] = {gt, eq}
    function automatic [15:0] chunks(input [63:0] a, input [63:0] b);
        integer c;
        begin
            for (c = 0; c < 8; c = c + 1) chunks[2*c +: 2] = cmp8(a[8*c +: 8], b[8*c +: 8]);
        end
    endfunction
    function automatic [1:0] comb(input [15:0] v);                // {gt, eq} of the whole operand
        reg [7:0] g, e;
        integer s, t;
        begin
            for (t = 0; t < 8; t = t + 1) begin g[t] = v[2*t+1]; e[t] = v[2*t]; end
            for (s = 1; s < 8; s = s * 2)
                for (t = 0; t < 8; t = t + 2 * s) begin
                    g[t] = g[t+s] | (e[t+s] & g[t]);
                    e[t] = e[t+s] & e[t];
                end
            comb = {g[0], e[0]};
        end
    endfunction
    function automatic comb_gt(input [15:0] v);
        reg [1:0] r; begin r = comb(v); comb_gt = r[1]; end
    endfunction
    function automatic comb_ge(input [15:0] v);
        reg [1:0] r; begin r = comb(v); comb_ge = r[1] | r[0]; end
    endfunction
    function automatic gt_k(input [63:0] a, input [63:0] b);       // one-stage compare (short operands only)
        begin gt_k = comb_gt(chunks(a, b)); end
    endfunction
    // population count of 16 bits as a balanced adder tree (2-, 3-, 4-, 5-bit adds)
    function automatic [4:0] pop16(input [15:0] x);
        reg [1:0] pa [0:7]; reg [2:0] pb [0:3]; reg [3:0] pc [0:1];
        integer q;
        begin
            for (q = 0; q < 8; q = q + 1) pa[q] = {1'b0, x[2*q]} + {1'b0, x[2*q+1]};
            for (q = 0; q < 4; q = q + 1) pb[q] = {1'b0, pa[2*q]} + {1'b0, pa[2*q+1]};
            for (q = 0; q < 2; q = q + 1) pc[q] = {1'b0, pb[2*q]} + {1'b0, pb[2*q+1]};
            pop16 = {1'b0, pc[0]} + {1'b0, pc[1]};
        end
    endfunction
    integer i, j, k;
    reg [K*(32+IW)-1:0] a1, b1, a2, b2;
    reg [15:0] cc1 [0:K*K-1];
    reg ha1, hb1, h2;
    reg [2*K-1:0] sel2 [0:K-1];
    reg [K*K-1:0] c;
    reg [EW-1:0] acc;
    always @(posedge clk) begin
        for (i = 0; i < K; i = i + 1)
            for (j = 0; j < K; j = j + 1)
                cc1[i*K+j] <= (NEG == 4) ? chunks({a[i*EW+IW +: 32], {IW{1'b1}}}, {b[j*EW+IW +: 32], {IW{1'b0}}})
                                         : chunks({a[i*EW+IW +: 32], ~a[i*EW +: IW]}, {b[j*EW+IW +: 32], ~b[j*EW +: IW]});
        a1 <= a; b1 <= b; ha1 <= ha; hb1 <= hb;
        // stage 2: combine + selects
        for (i = 0; i < K; i = i + 1)
            for (j = 0; j < K; j = j + 1)
                c[i*K+j] = !hb1 ? 1'b1 : !ha1 ? 1'b0 : comb_gt(cc1[i*K+j]);
        for (k = 0; k < K; k = k + 1) begin
            sel2[k] <= {2*K{1'b0}};
            for (i = 0; i <= k; i = i + 1)
                sel2[k][i] <= ((k == i) ? 1'b1 : !c[i*K+((k>i)?(k-i-1):0)]) && c[i*K+k-i];
            for (j = 0; j <= k; j = j + 1)
                sel2[k][K+j] <= ((k == j) ? 1'b1 : c[((k>j)?(k-j-1):0)*K+j]) && !c[(k-j)*K+j];
        end
        a2 <= a1; b2 <= b1; h2 <= ha1 | hb1;
        // stage 3: mux
        for (k = 0; k < K; k = k + 1) begin
            acc = {EW{1'b0}};
            for (i = 0; i < K; i = i + 1) if (sel2[k][i]) acc = acc | a2[i*EW +: EW];
            for (j = 0; j < K; j = j + 1) if (sel2[k][K+j]) acc = acc | b2[j*EW +: EW];
            q[k*EW +: EW] <= acc;
        end
        hq <= h2;
    end
endmodule

module ot_gpu_router_topk_ps_core #(
    parameter integer N   = 384,
    parameter integer P   = 16,       // values a beat (power of two, K <= P <= 16)
    parameter integer K   = 6,
    parameter integer IW  = 9,
    parameter integer NEG = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              in_valid,
    input  wire [P*32-1:0]   in_vals,
    input  wire              in_last,
    output reg               out_valid,
    output reg  [K*IW-1:0]   out_ids
);
    localparam integer LP = (P > 1) ? $clog2(P) : 1;
    localparam integer EW = 32 + IW;                 // {key, idx}
    localparam integer KR = (K > 1) ? $clog2(K) : 1;  // id rank width
    localparam integer NB = 4;                       // running banks
    // Compare helpers (inlined in each module of this file).  Every magnitude compare is
    // an explicit tree on plain gates: 8-bit chunk (gt, eq) pairs (registered by the caller), then a
    // log-depth chunk combine.  A relational operator on a key would be mapped through $alu to a ripple
    // carry chain (measured 750 ps WC pre-repair on the first route); none is used on a key.
    function automatic [1:0] cmp8(input [7:0] a, input [7:0] b);   // {a > b, a == b}
        reg [7:0] g, e;
        integer s, t;
        begin
            g = a & ~b; e = ~(a ^ b);
            for (s = 1; s < 8; s = s * 2)
                for (t = 0; t < 8; t = t + 2 * s) begin
                    g[t] = g[t+s] | (e[t+s] & g[t]);
                    e[t] = e[t+s] & e[t];
                end
            cmp8 = {g[0], e[0]};
        end
    endfunction
    // operands zero-extended to 64 bits: 8 chunks, chunk c at [2c+1:2c] = {gt, eq}
    function automatic [15:0] chunks(input [63:0] a, input [63:0] b);
        integer c;
        begin
            for (c = 0; c < 8; c = c + 1) chunks[2*c +: 2] = cmp8(a[8*c +: 8], b[8*c +: 8]);
        end
    endfunction
    function automatic [1:0] comb(input [15:0] v);                // {gt, eq} of the whole operand
        reg [7:0] g, e;
        integer s, t;
        begin
            for (t = 0; t < 8; t = t + 1) begin g[t] = v[2*t+1]; e[t] = v[2*t]; end
            for (s = 1; s < 8; s = s * 2)
                for (t = 0; t < 8; t = t + 2 * s) begin
                    g[t] = g[t+s] | (e[t+s] & g[t]);
                    e[t] = e[t+s] & e[t];
                end
            comb = {g[0], e[0]};
        end
    endfunction
    function automatic comb_gt(input [15:0] v);
        reg [1:0] r; begin r = comb(v); comb_gt = r[1]; end
    endfunction
    function automatic comb_ge(input [15:0] v);
        reg [1:0] r; begin r = comb(v); comb_ge = r[1] | r[0]; end
    endfunction
    function automatic gt_k(input [63:0] a, input [63:0] b);       // one-stage compare (short operands only)
        begin gt_k = comb_gt(chunks(a, b)); end
    endfunction
    // population count of 16 bits as a balanced adder tree (2-, 3-, 4-, 5-bit adds)
    function automatic [4:0] pop16(input [15:0] x);
        reg [1:0] pa [0:7]; reg [2:0] pb [0:3]; reg [3:0] pc [0:1];
        integer q;
        begin
            for (q = 0; q < 8; q = q + 1) pa[q] = {1'b0, x[2*q]} + {1'b0, x[2*q+1]};
            for (q = 0; q < 4; q = q + 1) pb[q] = {1'b0, pa[2*q]} + {1'b0, pa[2*q+1]};
            for (q = 0; q < 2; q = q + 1) pc[q] = {1'b0, pb[2*q]} + {1'b0, pb[2*q+1]};
            pop16 = {1'b0, pc[0]} + {1'b0, pc[1]};
        end
    endfunction
    function automatic [31:0] okey(input [31:0] f);
        reg [31:0] c;
        begin
            c = (f == 32'h8000_0000 && NEG != 3) ? 32'h0 : f;
            okey = c[31] ? ~c : (c | 32'h8000_0000);
        end
    endfunction
    integer i, j, m, k, b;
    // ---- reset synchroniser + registered synchronous reset ----
    reg rs0, rs1;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rs0 <= 1'b0; rs1 <= 1'b0; end
        else begin rs0 <= 1'b1; rs1 <= rs0; end
    reg rst_c;
    always @(posedge clk) rst_c <= ~rs1;
    // ---- tag pipeline: per stage {valid, last, bank (2), fresh, has (NB)} ----
    localparam integer TW = 5 + NB;
    // ---- S0: pin capture ----
    reg v0, l0;
    reg [P*32-1:0] x0;
    always @(posedge clk) begin v0 <= in_valid; l0 <= in_last; x0 <= in_vals; end
    // ---- S1: keys + beat tags ----
    reg [IW-1:0] base_c;        // index of the next beat's lane 0
    reg [1:0]    par;           // bank of the next beat
    reg [NB-1:0] bfresh;        // bank's next beat is its first of the vector
    reg [NB-1:0] has;           // bank took a beat of the current vector
    reg          v1, l1, fresh1;
    reg [1:0]    bank1;
    reg [NB-1:0] hasf1;
    reg [IW-1:0] base1;
    reg [31:0]   key1 [0:P-1];
    always @(posedge clk) begin
        if (rst_c) begin
            base_c <= {IW{1'b0}}; par <= 2'd0; bfresh <= {NB{1'b1}}; has <= {NB{1'b0}}; v1 <= 1'b0;
        end else begin
            v1 <= v0;
            if (v0) begin
                par <= par + 2'd1;
                base_c <= l0 ? {IW{1'b0}} : base_c + P;
                if (l0) begin bfresh <= {NB{1'b1}}; has <= {NB{1'b0}}; end
                else begin bfresh[par] <= 1'b0; has[par] <= 1'b1; end
            end
        end
        l1 <= v0 & l0; bank1 <= par; fresh1 <= bfresh[par]; base1 <= base_c;
        hasf1 <= has | ({{NB-1{1'b0}}, 1'b1} << par);
        for (j = 0; j < P; j = j + 1) key1[j] <= okey(x0[32*j +: 32]);
    end
    // ---- S2: chunk compares of every lane pair ----
    reg [15:0]    cc2 [0:P*P-1];   // [j*P+m], j < m
    reg [31:0]    key2 [0:P-1];
    reg [IW-1:0]  base2;
    reg           v2, l2, fresh2;
    reg [1:0]     bank2;
    reg [NB-1:0]  hasf2;
    always @(posedge clk) begin
        for (j = 0; j < P; j = j + 1)
            for (m = j + 1; m < P; m = m + 1)
                cc2[j*P+m] <= chunks(key1[j], key1[m]);
        for (j = 0; j < P; j = j + 1) key2[j] <= key1[j];
        base2 <= base1; l2 <= l1; bank2 <= bank1; fresh2 <= fresh1; hasf2 <= hasf1;
        v2 <= rst_c ? 1'b0 : v1;
    end
    // ---- S3: combine -> lane j beats lane m ----
    reg [P*P-1:0] gt3;
    reg [31:0]    key3 [0:P-1];
    reg [IW-1:0]  base3;
    reg           v3, l3, fresh3;
    reg [1:0]     bank3;
    reg [NB-1:0]  hasf3;
    always @(posedge clk) begin
        gt3 <= {P*P{1'b0}};
        for (j = 0; j < P; j = j + 1)
            for (m = j + 1; m < P; m = m + 1)
                gt3[j*P+m] <= (NEG == 2) ? comb_gt(cc2[j*P+m]) : comb_ge(cc2[j*P+m]);
        for (j = 0; j < P; j = j + 1) key3[j] <= key2[j];
        base3 <= base2; l3 <= l2; bank3 <= bank2; fresh3 <= fresh2; hasf3 <= hasf2;
        v3 <= rst_c ? 1'b0 : v2;
    end
    // ---- S4: ranks ----
    reg [4:0]     rk4 [0:P-1];
    reg [31:0]    key4 [0:P-1];
    reg [IW-1:0]  base4;
    reg           v4, l4, fresh4;
    reg [1:0]     bank4;
    reg [NB-1:0]  hasf4;
    reg [15:0]    bv;
    always @(posedge clk) begin
        for (m = 0; m < P; m = m + 1) begin
            bv = 16'd0;
            for (j = 0; j < P; j = j + 1)
                if (j < m) bv[j] = gt3[j*P+m];
                else if (j > m) bv[j] = !gt3[m*P+j];
            rk4[m] <= pop16(bv);
            key4[m] <= key3[m];
        end
        base4 <= base3; l4 <= l3; bank4 <= bank3; fresh4 <= fresh3; hasf4 <= hasf3;
        v4 <= rst_c ? 1'b0 : v3;
    end
    // ---- S5: local top-K, descending ----
    reg [EW-1:0]  L5 [0:K-1];
    reg           v5, l5, fresh5;
    reg [1:0]     bank5;
    reg [NB-1:0]  hasf5;
    reg [EW-1:0]  acc;
    always @(posedge clk) begin
        for (k = 0; k < K; k = k + 1) begin
            acc = {EW{1'b0}};
            for (m = 0; m < P; m = m + 1)
                if (rk4[m] == k)
                    acc = acc | {key4[m], base4[IW-1:LP], m[LP-1:0]};
            L5[k] <= acc;
        end
        l5 <= l4; bank5 <= bank4; fresh5 <= fresh4; hasf5 <= hasf4;
        v5 <= rst_c ? 1'b0 : v4;
    end
    // ---- S6 / S7 / S8: NB running banks, 3-stage merge recurrence ----
    reg [EW-1:0]  R   [0:NB*K-1];          // bank b entry i at R[b*K+i]
    reg [15:0]    cc6 [0:NB*K*K-1];        // bank b: [b*K*K + i*K + j] = chunks(R_i, L_j)
    reg [EW-1:0]  Lc6 [0:K-1];
    reg [EW-1:0]  Lc7 [0:K-1];
    reg [NB-1:0]  mine6, fresh6;
    reg [2*K-1:0] sel7 [0:NB*K-1];         // bank b slot k: one-hot over {R_0..R_K-1, L_0..L_K-1}
    reg           l6, l7, l8;
    reg [NB-1:0]  hasf6, hasf7, hasf8;
    reg [K*K-1:0] c7;
    always @(posedge clk) begin
        // S6
        for (b = 0; b < NB; b = b + 1)
            for (i = 0; i < K; i = i + 1)
                for (j = 0; j < K; j = j + 1)
                    cc6[b*K*K+i*K+j] <= chunks(R[b*K+i][EW-1:IW], L5[j][EW-1:IW]);
        for (j = 0; j < K; j = j + 1) Lc6[j] <= L5[j];
        for (b = 0; b < NB; b = b + 1) begin
            mine6[b] <= !rst_c && v5 && (bank5 == b);
            fresh6[b] <= fresh5;
        end
        l6 <= rst_c ? 1'b0 : (v5 & l5); hasf6 <= hasf5;
        // S7
        for (b = 0; b < NB; b = b + 1) begin
            for (i = 0; i < K; i = i + 1)
                for (j = 0; j < K; j = j + 1)
                    c7[i*K+j] = (NEG == 1) ? comb_gt(cc6[b*K*K+i*K+j]) : comb_ge(cc6[b*K*K+i*K+j]);
            for (k = 0; k < K; k = k + 1) begin
                sel7[b*K+k] <= {2*K{1'b0}};
                if (!mine6[b]) sel7[b*K+k][k] <= 1'b1;                // hold
                else if (fresh6[b]) sel7[b*K+k][K+k] <= 1'b1;         // first beat of the vector
                else begin
                    for (i = 0; i <= k; i = i + 1)                    // R_i lands in slot k
                        sel7[b*K+k][i] <= ((k == i) ? 1'b1 : !c7[i*K+((k>i)?(k-i-1):0)]) && c7[i*K+k-i];
                    for (j = 0; j <= k; j = j + 1)                    // L_j lands in slot k
                        sel7[b*K+k][K+j] <= ((k == j) ? 1'b1 : c7[((k>j)?(k-j-1):0)*K+j]) && !c7[(k-j)*K+j];
                end
            end
        end
        for (j = 0; j < K; j = j + 1) Lc7[j] <= Lc6[j];
        l7 <= rst_c ? 1'b0 : l6; hasf7 <= hasf6;
        l8 <= rst_c ? 1'b0 : l7; hasf8 <= hasf7;
    end
    always @(posedge clk)                  // S8
        for (b = 0; b < NB; b = b + 1)
            for (k = 0; k < K; k = k + 1) begin
                acc = {EW{1'b0}};
                for (i = 0; i < K; i = i + 1) if (sel7[b*K+k][i]) acc = acc | R[b*K+i];
                for (j = 0; j < K; j = j + 1) if (sel7[b*K+k][K+j]) acc = acc | Lc7[j];
                R[b*K+k] <= acc;
            end
    // ---- S9: snapshot ----
    reg [NB*K*EW-1:0] F;
    reg               v9;
    reg [NB-1:0]      hasf9;
    always @(posedge clk) begin
        for (i = 0; i < NB*K; i = i + 1) F[i*EW +: EW] <= R[i];
        v9 <= rst_c ? 1'b0 : l8; hasf9 <= hasf8;
    end
    // ---- S10..S15: merge tree ----
    wire [K*EW-1:0] m01, m23, mt;
    wire h01, h23, ht;
    ot_gpu_router_ps_merge #(.K(K), .IW(IW), .NEG(NEG)) u_m01 (.clk(clk), .a(F[0*K*EW +: K*EW]), .b(F[1*K*EW +: K*EW]),
        .ha(hasf9[0]), .hb(hasf9[1]), .q(m01), .hq(h01));
    ot_gpu_router_ps_merge #(.K(K), .IW(IW), .NEG(NEG)) u_m23 (.clk(clk), .a(F[2*K*EW +: K*EW]), .b(F[3*K*EW +: K*EW]),
        .ha(hasf9[2]), .hb(hasf9[3]), .q(m23), .hq(h23));
    ot_gpu_router_ps_merge #(.K(K), .IW(IW), .NEG(NEG)) u_mt (.clk(clk), .a(m01), .b(m23),
        .ha(h01), .hb(h23), .q(mt), .hq(ht));
    reg [5:0] vt;                          // v9 -> S15
    always @(posedge clk) vt <= rst_c ? 6'd0 : {vt[4:0], v9};
    // ---- S16..S18: ascending by id ----
    reg [K*K-1:0] lt16;
    reg [IW-1:0]  id16 [0:K-1];
    reg [KR:0]    rk17 [0:K-1];
    reg [IW-1:0]  id17 [0:K-1];
    reg [15:0]    rv;
    reg [4:0]     rp;
    reg [IW-1:0]  ia;
    reg           v16, v17;
    always @(posedge clk) begin
        lt16 <= {K*K{1'b0}};
        for (j = 0; j < K; j = j + 1)
            for (m = j + 1; m < K; m = m + 1) lt16[j*K+m] <= gt_k(mt[m*EW +: IW], mt[j*EW +: IW]);
        for (j = 0; j < K; j = j + 1) id16[j] <= mt[j*EW +: IW];
        v16 <= rst_c ? 1'b0 : vt[5];
        for (m = 0; m < K; m = m + 1) begin
            rv = 16'd0;
            for (j = 0; j < K; j = j + 1)
                if (j < m) rv[j] = lt16[j*K+m];
                else if (j > m) rv[j] = !lt16[m*K+j];
            rp = pop16(rv);
            rk17[m] <= rp[KR:0];
            id17[m] <= id16[m];
        end
        v17 <= rst_c ? 1'b0 : v16;
        for (k = 0; k < K; k = k + 1) begin
            ia = {IW{1'b0}};
            for (m = 0; m < K; m = m + 1) if (rk17[m] == k) ia = ia | id17[m];
            out_ids[k*IW +: IW] <= ia;
        end
        out_valid <= rst_c ? 1'b0 : v17;
    end
endmodule

// PIPESEL = 2 front end: 2:1 serialiser (P -> P/2 lanes); a beat at most every other cycle.
module ot_gpu_router_topk_ps_half #(
    parameter integer P = 16
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              in_valid,
    input  wire [P*32-1:0]   in_vals,
    input  wire              in_last,
    output reg               h_valid,
    output reg [P*16-1:0]    h_vals,
    output reg               h_last
);
    reg rs0, rs1, rst_c;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rs0 <= 1'b0; rs1 <= 1'b0; end
        else begin rs0 <= 1'b1; rs1 <= rs0; end
    always @(posedge clk) rst_c <= ~rs1;
    reg va, la, lu; reg [P*32-1:0] xa; reg [P*16-1:0] xu;
    reg second;
    always @(posedge clk) begin
        va <= in_valid; la <= in_last; xa <= in_vals;
        if (rst_c) begin h_valid <= 1'b0; second <= 1'b0; end
        else begin h_valid <= va | second; second <= va; end
        if (va) begin xu <= xa[P*32-1:P*16]; lu <= la; end
        h_vals <= va ? xa[P*16-1:0] : xu;                // first half, then the held second half
        h_last <= va ? 1'b0 : lu;
    end
endmodule

module ot_gpu_router_topk_ps #(
    parameter integer N       = 384,
    parameter integer P       = 16,
    parameter integer K       = 6,
    parameter integer IW      = 9,
    parameter integer PIPESEL = 0,
    parameter integer NEG     = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              in_valid,
    input  wire [P*32-1:0]   in_vals,
    input  wire              in_last,
    output wire              out_valid,
    output wire [K*IW-1:0]   out_ids
);
    generate
        if (PIPESEL == 1) begin : g_ps
            ot_gpu_router_topk_ps_core #(.N(N), .P(P), .K(K), .IW(IW), .NEG(NEG)) u (.clk(clk), .rst_n(rst_n),
                .in_valid(in_valid), .in_vals(in_vals), .in_last(in_last), .out_valid(out_valid), .out_ids(out_ids));
        end else if (PIPESEL == 2) begin : g_half
            wire hv, hl; wire [P*16-1:0] hx;
            ot_gpu_router_topk_ps_half #(.P(P)) f (.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_vals(in_vals),
                .in_last(in_last), .h_valid(hv), .h_vals(hx), .h_last(hl));
            ot_gpu_router_topk_ps_core #(.N(N), .P(P/2), .K(K), .IW(IW), .NEG(NEG)) u (.clk(clk), .rst_n(rst_n),
                .in_valid(hv), .in_vals(hx), .in_last(hl), .out_valid(out_valid), .out_ids(out_ids));
        end else begin : g_ref
            ot_gpu_router_topk #(.N(N), .P(P), .K(K), .IW(IW)) u (.clk(clk), .rst_n(rst_n), .in_valid(in_valid),
                .in_vals(in_vals), .in_last(in_last), .out_valid(out_valid), .out_ids(out_ids));
        end
    endgenerate
endmodule
