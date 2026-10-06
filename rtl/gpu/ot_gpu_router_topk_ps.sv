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
// timing wall at 1.2 GHz).  Here no value-dependent state is updated every cycle:
//   S0  pin capture (in_valid, in_last, in_vals: flop-direct, no logic before the flop)
//   S1  order-preserving integer key per value: okey(f) = f == -0 ? 0x8000_0000 :
//       f[31] ? ~f : f | 1 << 31 (exactly the reference's key; no FP comparator anywhere)
//   S2  all P (P-1) / 2 pairwise compares of the beat (lane j beats lane m > j iff key_j >= key_m:
//       equal keys go to the lower index, as in the reference)
//   S3  rank of every lane = how many lanes beat it (popcount of P - 1 compare bits)
//   S4  local top-K of the beat, sorted: slot k = the lane whose rank is k (one-hot AND-OR mux)
//   S5  two running top-K banks take alternate beats (a bank sees a beat at most every other
//       cycle), so the merge with the running list is a 2-cycle recurrence split into two stages:
//       S5 compares the bank's K entries with the beat's K (K x K 32-bit compares; the running
//       entry wins a tie, it has the lower index) and registers the one-hot slot selects
//       (merge-path: entry i of list A lands in slot i + |B ahead of it|);
//   S6  the bank register takes the AND-OR mux of {bank, beat} (hold / fresh-vector are folded
//       into the selects, so no enable fans out over the bank).
//   S7  both banks are snapshotted two cycles after the vector's last beat left S4, the cycle in
//       which both hold their final lists (the next vector's first beats overwrite them only one
//       cycle later).
//   S8  merge of the two bank lists on the full key {okey, ~index} (the banks interleave
//       indices): K x K compares + the merge-path selects, registered;
//   S9  the K selected ids;  S10 pairwise id compares;  S11 id ranks;  S12 ids by rank ->
//       out_ids / out_valid flops at the output pins.
// Latency: in_valid of the last beat at the pins -> out_valid 13 cycles (the reference: 24,
// ot_gpu_router_topk_f: 25).  Throughput unchanged (PIPESEL = 1).
// Reset: rst_n asserts asynchronously into a 2-flop synchroniser only; all control flops take a
// registered synchronous reset; datapath flops have no reset and no enable.
// NEG (test only, default 0) plants a known error for the bench's negative controls:
//   1 bank merge gives ties to the arriving beat, 2 local sort gives ties to the higher lane,
//   3 -0 is not canonicalised, 4 the final merge ignores the index on ties.
// ---------------------------------------------------------------------------
module ot_gpu_router_topk_ps_core #(
    parameter integer N   = 384,
    parameter integer P   = 16,       // values a beat (power of two, >= K)
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
    function automatic [31:0] okey(input [31:0] f);
        reg [31:0] c;
        begin
            c = (f == 32'h8000_0000 && NEG != 3) ? 32'h0 : f;
            okey = c[31] ? ~c : (c | 32'h8000_0000);
        end
    endfunction
    // Magnitude compare as an explicit log-depth (gt, eq) prefix tree on plain gates: a `>=` operator is mapped
    // through $alu to a ripple carry chain (measured: 32-bit compare 750 ps WC pre-repair, MAJ chain), so no
    // relational operator on a key appears in this module.  Operands are zero-extended to 64 bits.
    function automatic [1:0] cmp_tree(input [63:0] a, input [63:0] b);   // {a > b, a == b}
        reg [63:0] g, e;
        integer s, t;
        begin
            g = a & ~b; e = ~(a ^ b);
            for (s = 1; s < 64; s = s * 2)
                for (t = 0; t < 64; t = t + 2 * s) begin
                    g[t] = g[t+s] | (e[t+s] & g[t]);
                    e[t] = e[t+s] & e[t];
                end
            cmp_tree = {g[0], e[0]};
        end
    endfunction
    function automatic ge_k(input [63:0] a, input [63:0] b);
        reg [1:0] r; begin r = cmp_tree(a, b); ge_k = r[1] | r[0]; end
    endfunction
    function automatic gt_k(input [63:0] a, input [63:0] b);
        reg [1:0] r; begin r = cmp_tree(a, b); gt_k = r[1]; end
    endfunction
    // population count of 16 bits as a balanced adder tree (2-, 3-, 4-, 5-bit adds)
    function automatic [4:0] pop16(input [15:0] x);
        reg [1:0] a [0:7]; reg [2:0] b [0:3]; reg [3:0] c [0:1];
        integer q;
        begin
            for (q = 0; q < 8; q = q + 1) a[q] = {1'b0, x[2*q]} + {1'b0, x[2*q+1]};
            for (q = 0; q < 4; q = q + 1) b[q] = {1'b0, a[2*q]} + {1'b0, a[2*q+1]};
            for (q = 0; q < 2; q = q + 1) c[q] = {1'b0, b[2*q]} + {1'b0, b[2*q+1]};
            pop16 = {1'b0, c[0]} + {1'b0, c[1]};
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
    // ---- S0: pin capture ----
    reg v0, l0;
    reg [P*32-1:0] x0;
    always @(posedge clk) begin v0 <= in_valid; l0 <= in_last; x0 <= in_vals; end
    // ---- S1: keys + beat tags ----
    reg [IW-1:0] base_c;        // index of the next beat's lane 0
    reg          par;           // bank of the next beat
    reg [1:0]    bfresh;        // bank's next beat is its first of the vector
    reg [1:0]    has;           // bank took a beat of the current vector
    reg          v1, l1, bank1, fresh1;
    reg [1:0]    hasf1;
    reg [IW-1:0] base1;
    reg [31:0]   key1 [0:P-1];
    always @(posedge clk) begin
        if (rst_c) begin
            base_c <= {IW{1'b0}}; par <= 1'b0; bfresh <= 2'b11; has <= 2'b00; v1 <= 1'b0;
        end else begin
            v1 <= v0;
            if (v0) begin
                par <= ~par;
                base_c <= l0 ? {IW{1'b0}} : base_c + P;
                if (l0) begin bfresh <= 2'b11; has <= 2'b00; end
                else begin bfresh[par] <= 1'b0; has[par] <= 1'b1; end
            end
        end
        l1 <= v0 & l0; bank1 <= par; fresh1 <= bfresh[par]; base1 <= base_c;
        hasf1 <= has | (par ? 2'b10 : 2'b01);
        for (j = 0; j < P; j = j + 1) key1[j] <= okey(x0[32*j +: 32]);
    end
    // ---- S2: pairwise compares ----
    reg [P*P-1:0] gt2;          // gt2[j*P+m] (j < m): lane j beats lane m
    reg [31:0]    key2 [0:P-1];
    reg [IW-1:0]  base2;
    reg           v2, l2, bank2, fresh2;
    reg [1:0]     hasf2;
    always @(posedge clk) begin
        gt2 <= {P*P{1'b0}};
        for (j = 0; j < P; j = j + 1)
            for (m = j + 1; m < P; m = m + 1)
                gt2[j*P+m] <= (NEG == 2) ? gt_k(key1[j], key1[m]) : ge_k(key1[j], key1[m]);
        for (j = 0; j < P; j = j + 1) key2[j] <= key1[j];
        base2 <= base1; l2 <= l1; bank2 <= bank1; fresh2 <= fresh1; hasf2 <= hasf1;
        v2 <= rst_c ? 1'b0 : v1;
    end
    // ---- S3: ranks ----
    reg [LP:0]    rk3 [0:P-1];
    reg [31:0]    key3 [0:P-1];
    reg [IW-1:0]  base3;
    reg           v3, l3, bank3, fresh3;
    reg [1:0]     hasf3;
    reg [15:0]    bv;
    always @(posedge clk) begin
        for (m = 0; m < P; m = m + 1) begin
            bv = 16'd0;
            for (j = 0; j < P; j = j + 1)
                if (j < m) bv[j] = gt2[j*P+m];
                else if (j > m) bv[j] = !gt2[m*P+j];
            rk3[m] <= pop16(bv);
            key3[m] <= key2[m];
        end
        base3 <= base2; l3 <= l2; bank3 <= bank2; fresh3 <= fresh2; hasf3 <= hasf2;
        v3 <= rst_c ? 1'b0 : v2;
    end
    // ---- S4: local top-K, descending ----
    reg [EW-1:0]  L4 [0:K-1];
    reg           v4, l4, bank4, fresh4;
    reg [1:0]     hasf4;
    reg [EW-1:0]  acc;
    always @(posedge clk) begin
        for (k = 0; k < K; k = k + 1) begin
            acc = {EW{1'b0}};
            for (m = 0; m < P; m = m + 1)
                if (rk3[m] == k)
                    acc = acc | {key3[m], base3[IW-1:LP], m[LP-1:0]};
            L4[k] <= acc;
        end
        l4 <= l3; bank4 <= bank3; fresh4 <= fresh3; hasf4 <= hasf3;
        v4 <= rst_c ? 1'b0 : v3;
    end
    // ---- S5 / S6: two running banks ----
    reg [EW-1:0]  R  [0:2*K-1];          // bank b entry i at R[b*K+i]
    reg [EW-1:0]  Lc5 [0:K-1];
    reg [2*K-1:0] sel5 [0:2*K-1];        // bank b slot k: one-hot over {R_0..R_K-1, L_0..L_K-1}
    reg           l5, l6;
    reg [1:0]     hasf5, hasf6;
    reg [K*K-1:0] c5;
    reg           mine;
    always @(posedge clk) begin
        for (b = 0; b < 2; b = b + 1) begin
            mine = v4 && (bank4 == b);
            for (i = 0; i < K; i = i + 1)
                for (j = 0; j < K; j = j + 1)
                    c5[i*K+j] = (NEG == 1) ? gt_k(R[b*K+i][EW-1:IW], L4[j][EW-1:IW])
                                           : ge_k(R[b*K+i][EW-1:IW], L4[j][EW-1:IW]);
            for (k = 0; k < K; k = k + 1) begin
                sel5[b*K+k] <= {2*K{1'b0}};
                if (!mine) sel5[b*K+k][k] <= 1'b1;               // hold
                else if (fresh4) sel5[b*K+k][K+k] <= 1'b1;       // first beat of the vector
                else begin
                    for (i = 0; i <= k; i = i + 1)               // R_i lands in slot k
                        sel5[b*K+k][i] <= ((k == i) ? 1'b1 : !c5[i*K+((k>i)?(k-i-1):0)]) && c5[i*K+k-i];
                    for (j = 0; j <= k; j = j + 1)               // L_j lands in slot k
                        sel5[b*K+k][K+j] <= ((k == j) ? 1'b1 : c5[((k>j)?(k-j-1):0)*K+j]) && !c5[(k-j)*K+j];
                end
            end
        end
        for (j = 0; j < K; j = j + 1) Lc5[j] <= L4[j];
        l5 <= rst_c ? 1'b0 : (v4 & l4); hasf5 <= hasf4;
        l6 <= rst_c ? 1'b0 : l5;        hasf6 <= hasf5;
    end
    always @(posedge clk)
        for (b = 0; b < 2; b = b + 1)
            for (k = 0; k < K; k = k + 1) begin
                acc = {EW{1'b0}};
                for (i = 0; i < K; i = i + 1) if (sel5[b*K+k][i]) acc = acc | R[b*K+i];
                for (j = 0; j < K; j = j + 1) if (sel5[b*K+k][K+j]) acc = acc | Lc5[j];
                R[b*K+k] <= acc;
            end
    // ---- S7: snapshot ----
    reg [EW-1:0]  F [0:2*K-1];
    reg           v7;
    reg [1:0]     hasf7;
    always @(posedge clk) begin
        for (i = 0; i < 2*K; i = i + 1) F[i] <= R[i];
        v7 <= rst_c ? 1'b0 : l6; hasf7 <= hasf6;
    end
    // ---- S8: final merge selects (full key, banks interleave indices) ----
    reg [K*K-1:0] c8;
    reg [2*K-1:0] sel8 [0:K-1];
    reg [IW-1:0]  Fi8 [0:2*K-1];
    reg           v8;
    always @(posedge clk) begin
        for (i = 0; i < K; i = i + 1)
            for (j = 0; j < K; j = j + 1)
                c8[i*K+j] = !hasf7[1] ? 1'b1 : !hasf7[0] ? 1'b0 :
                            (NEG == 4) ? ge_k(F[i][EW-1:IW], F[K+j][EW-1:IW])
                                       : gt_k({F[i][EW-1:IW], ~F[i][IW-1:0]}, {F[K+j][EW-1:IW], ~F[K+j][IW-1:0]});
        for (k = 0; k < K; k = k + 1) begin
            sel8[k] <= {2*K{1'b0}};
            for (i = 0; i <= k; i = i + 1)
                sel8[k][i] <= ((k == i) ? 1'b1 : !c8[i*K+((k>i)?(k-i-1):0)]) && c8[i*K+k-i];
            for (j = 0; j <= k; j = j + 1)
                sel8[k][K+j] <= ((k == j) ? 1'b1 : c8[((k>j)?(k-j-1):0)*K+j]) && !c8[(k-j)*K+j];
        end
        for (i = 0; i < 2*K; i = i + 1) Fi8[i] <= F[i][IW-1:0];
        v8 <= rst_c ? 1'b0 : v7;
    end
    // ---- S9: selected ids ----
    reg [IW-1:0]  id9 [0:K-1];
    reg [IW-1:0]  ia;
    reg           v9;
    always @(posedge clk) begin
        for (k = 0; k < K; k = k + 1) begin
            ia = {IW{1'b0}};
            for (i = 0; i < 2*K; i = i + 1) if (sel8[k][i]) ia = ia | Fi8[i];
            id9[k] <= ia;
        end
        v9 <= rst_c ? 1'b0 : v8;
    end
    // ---- S10..S12: ascending by id ----
    reg [K*K-1:0] lt10;
    reg [IW-1:0]  id10 [0:K-1];
    reg [KR:0]    rk11 [0:K-1];
    reg [IW-1:0]  id11 [0:K-1];
    reg [15:0]    rv;
    reg [4:0]     rp;
    reg           v10, v11;
    always @(posedge clk) begin
        lt10 <= {K*K{1'b0}};
        for (j = 0; j < K; j = j + 1)
            for (m = j + 1; m < K; m = m + 1) lt10[j*K+m] <= gt_k(id9[m], id9[j]);
        for (j = 0; j < K; j = j + 1) id10[j] <= id9[j];
        v10 <= rst_c ? 1'b0 : v9;
        for (m = 0; m < K; m = m + 1) begin
            rv = 16'd0;
            for (j = 0; j < K; j = j + 1)
                if (j < m) rv[j] = lt10[j*K+m];
                else if (j > m) rv[j] = !lt10[m*K+j];
            rp = pop16(rv);
            rk11[m] <= rp[KR:0];
            id11[m] <= id10[m];
        end
        v11 <= rst_c ? 1'b0 : v10;
        for (k = 0; k < K; k = k + 1) begin
            ia = {IW{1'b0}};
            for (m = 0; m < K; m = m + 1) if (rk11[m] == k) ia = ia | id11[m];
            out_ids[k*IW +: IW] <= ia;
        end
        out_valid <= rst_c ? 1'b0 : v11;
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
