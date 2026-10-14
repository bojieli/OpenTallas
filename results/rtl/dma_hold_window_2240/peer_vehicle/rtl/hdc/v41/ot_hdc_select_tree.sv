`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Parallel SELECT of the V4.1 hardwired decode core: the router top-k
// (k <= 8) of a whole score vector in a few beats, the successor of one
// ot_hdc_select unit walking the 384 router scores one per cycle.
//
// Semantics are exactly ot_hdc_select's (and tools/hdc_golden_v41.py
// `topk_lowest_index`): the k largest values, ties to the LOWER index, -0
// equals +0; NaN is outside the contract.  ORDER = 1 emits the selection in
// ascending index (the router's expert-id order), ORDER = 0 in rank order.
// Both units order entries by the same unsigned record
//     R = {valid, key(value), ~index}
// (key: order-preserving map of the IEEE value, -0 canonicalised to +0), a
// strict total order over the valid entries of a segment because indices are
// unique, so every compare-exchange network below that sorts by R returns
// the golden's selection and order.
//
// Interface.  A segment arrives as 1..NB beats of W lanes (in_lv marks the
// lanes that carry an element; an empty lane is the all-zero record, which
// loses to every element); in_last closes it.  There is no backpressure: the
// datapath is fully pipelined and segments may follow back to back.  The
// result leaves in ONE beat: out_v[j] / out_idx[j] / out_ninf[j], j < K, slot
// j valid iff j < min(K, elements).
//
// Microarchitecture (every compare-exchange is one registered stage: one
// (1+VW+IW)-bit compare and a 2:1 mux, as in ot_hdc_select's cells).
//   1. input register, then the key register (W records);
//   2. W/8 bitonic sorters of 8 (6 stages): each lane group sorted;
//   3. a binary tree of top-8 merges, log2(W/8) levels, 4 stages each: two
//      descending 8-lists A, B -> c[i] = max(A[i], B[7-i]) (the top 8 of the
//      union, bitonic), then a bitonic half-cleaner cascade of 8;
//      -> one sorted top-8 list per beat, one beat per cycle;
//   4. collector: the beat lists of a segment are held in NB slots and, on the
//      last beat, launched together (empty slots are all-zero lists);
//   5. a second merge tree over the NB lists, log2(NB) levels;
//   6. the first K entries; ORDER = 1 sorts them by {valid, ~index} with one
//      more bitonic sorter of 8 on (2+IW)-bit records.  The last stage's
//      register is the output register (no register-to-register copy: such a
//      wire-only path fails FF hold at 25 ps uncertainty).
// Latency (edges after the edge that accepts the last beat to the edge that
// registers the result): LAT = 1 + 6 + 4 log2(W/8) + 1 + 4 log2(NB)
// + (ORDER ? 6 : 0); for W 64, NB 8, ORDER 1: 38.
// ---------------------------------------------------------------------------

// one registered compare-exchange stage of a bitonic network over N records:
// pair (i, i^J) for i < i^J; larger record to i when (i & KB) == 0, else to i^J
module ot_hdc_seltree_cx #(
    parameter integer N  = 8,
    parameter integer EW = 43,     // record width; bit 0 is payload (not compared)
    parameter integer J  = 1,
    parameter integer KB = 8
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          iv,
    input  wire          il,
    input  wire [N*EW-1:0] d,
    output reg           ov,
    output reg           ol,
    output reg  [N*EW-1:0] q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ov <= 1'b0; ol <= 1'b0; end
        else begin ov <= iv; ol <= iv && il; end
    end
    genvar i;
    generate
        for (i = 0; i < N; i = i + 1) begin : g_p
            localparam integer L = i ^ J;
            if (L > i && L < N) begin : g_ce
                wire [EW-1:0] a = d[EW*i +: EW];
                wire [EW-1:0] b = d[EW*L +: EW];
                wire          gt = a[EW-1:1] > b[EW-1:1];
                wire          up = ((i & KB) == 0);
                wire [EW-1:0] hi = gt ? a : b;
                wire [EW-1:0] lo = gt ? b : a;
                always @(posedge clk) begin
                    q[EW*i +: EW] <= up ? hi : lo;
                    q[EW*L +: EW] <= up ? lo : hi;
                end
            end else if (L >= N) begin : g_pass
                always @(posedge clk) q[EW*i +: EW] <= d[EW*i +: EW];
            end
        end
    endgenerate
endmodule

// full bitonic sorter of 8 records, descending, 6 registered stages
module ot_hdc_seltree_sort8 #(
    parameter integer EW = 43
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          iv,
    input  wire          il,
    input  wire [8*EW-1:0] d,
    output wire          ov,
    output wire          ol,
    output wire [8*EW-1:0] q
);
    wire [8*EW-1:0] s [0:6];
    wire [6:0]      sv, sl;
    assign s[0] = d;
    assign sv[0] = iv;
    assign sl[0] = il;
    // (KB, J): (2,1) (4,2) (4,1) (8,4) (8,2) (8,1)
    ot_hdc_seltree_cx #(.N(8), .EW(EW), .J(1), .KB(2)) u0 (clk, rst_n, sv[0], sl[0], s[0], sv[1], sl[1], s[1]);
    ot_hdc_seltree_cx #(.N(8), .EW(EW), .J(2), .KB(4)) u1 (clk, rst_n, sv[1], sl[1], s[1], sv[2], sl[2], s[2]);
    ot_hdc_seltree_cx #(.N(8), .EW(EW), .J(1), .KB(4)) u2 (clk, rst_n, sv[2], sl[2], s[2], sv[3], sl[3], s[3]);
    ot_hdc_seltree_cx #(.N(8), .EW(EW), .J(4), .KB(8)) u3 (clk, rst_n, sv[3], sl[3], s[3], sv[4], sl[4], s[4]);
    ot_hdc_seltree_cx #(.N(8), .EW(EW), .J(2), .KB(8)) u4 (clk, rst_n, sv[4], sl[4], s[4], sv[5], sl[5], s[5]);
    ot_hdc_seltree_cx #(.N(8), .EW(EW), .J(1), .KB(8)) u5 (clk, rst_n, sv[5], sl[5], s[5], sv[6], sl[6], s[6]);
    assign q = s[6];
    assign ov = sv[6];
    assign ol = sl[6];
endmodule

// top 8 of two descending 8-lists, descending, 4 registered stages
module ot_hdc_seltree_merge8 #(
    parameter integer EW = 43
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          iv,
    input  wire          il,
    input  wire [8*EW-1:0] a,
    input  wire [8*EW-1:0] b,
    output wire          ov,
    output wire          ol,
    output wire [8*EW-1:0] q
);
    reg  [8*EW-1:0] c;
    reg             cv, cl;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin cv <= 1'b0; cl <= 1'b0; end
        else begin cv <= iv; cl <= iv && il; end
    end
    genvar i;
    generate
        for (i = 0; i < 8; i = i + 1) begin : g_f
            wire [EW-1:0] x = a[EW*i +: EW];
            wire [EW-1:0] y = b[EW*(7-i) +: EW];
            always @(posedge clk) c[EW*i +: EW] <= (x[EW-1:1] > y[EW-1:1]) ? x : y;
        end
    endgenerate
    wire [8*EW-1:0] s1, s2;
    wire            v1, v2, l1, l2;
    ot_hdc_seltree_cx #(.N(8), .EW(EW), .J(4), .KB(8)) u0 (clk, rst_n, cv, cl, c, v1, l1, s1);
    ot_hdc_seltree_cx #(.N(8), .EW(EW), .J(2), .KB(8)) u1 (clk, rst_n, v1, l1, s1, v2, l2, s2);
    ot_hdc_seltree_cx #(.N(8), .EW(EW), .J(1), .KB(8)) u2 (clk, rst_n, v2, l2, s2, ov, ol, q);
endmodule

// a binary tree of top-8 merges over NL descending 8-lists (NL a power of two)
module ot_hdc_seltree_tree #(
    parameter integer EW = 43,
    parameter integer NL = 8
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          iv,
    input  wire          il,
    input  wire [NL*8*EW-1:0] d,
    output wire          ov,
    output wire          ol,
    output wire [8*EW-1:0] q
);
    localparam integer LG = $clog2(NL);
    localparam integer LW = 8 * EW;
    wire [NL*LW-1:0] lv [0:LG];
    wire [LG:0]      vv, ll;
    assign lv[0] = d;
    assign vv[0] = iv;
    assign ll[0] = il;
    genvar t, n;
    generate
        for (t = 0; t < LG; t = t + 1) begin : g_lvl
            localparam integer NN = NL >> (t + 1);
            for (n = 0; n < NN; n = n + 1) begin : g_n
                wire nv, nl;
                ot_hdc_seltree_merge8 #(.EW(EW)) u (
                    .clk(clk), .rst_n(rst_n), .iv(vv[t]), .il(ll[t]),
                    .a(lv[t][LW*(2*n) +: LW]), .b(lv[t][LW*(2*n+1) +: LW]),
                    .ov(nv), .ol(nl), .q(lv[t+1][LW*n +: LW]));
                if (n == 0) begin : g_sb
                    assign vv[t+1] = nv;
                    assign ll[t+1] = nl;
                end
            end
            if (NN < NL) begin : g_pad
                assign lv[t+1][NL*LW-1 : NN*LW] = {((NL - NN) * LW){1'b0}};
            end
        end
    endgenerate
    assign q  = lv[LG][LW-1:0];
    assign ov = vv[LG];
    assign ol = ll[LG];
endmodule

module ot_hdc_select_tree #(
    parameter integer K     = 6,      // 1..8
    parameter integer VW    = 32,     // 16 = BF16 values, 32 = FP32 values
    parameter integer IW    = 9,      // index width
    parameter integer W     = 64,     // lanes per beat: a power of two >= 8
    parameter integer NB    = 8,      // beats per segment at most: a power of two
    parameter integer ORDER = 1       // 1 ascending index, 0 rank order
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              in_valid,
    input  wire              in_last,
    input  wire [W-1:0]      in_lv,
    input  wire [W*VW-1:0]   in_val,
    input  wire [W*IW-1:0]   in_idx,
    output wire              out_valid,
    output wire [K-1:0]      out_v,
    output wire [K*IW-1:0]   out_idx,
    output wire [K-1:0]      out_ninf
);
    localparam integer EW = 1 + VW + IW + 1;       // {valid, key, ~index, ninf}
    localparam integer LW = 8 * EW;
    localparam integer G  = W / 8;
    localparam integer CW = (NB > 1) ? $clog2(NB) : 1;

    // -- input register --------------------------------------------------------------
    reg              r0_v, r0_l;
    reg [W-1:0]      r0_lv;
    reg [W*VW-1:0]   r0_val;
    reg [W*IW-1:0]   r0_idx;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin r0_v <= 1'b0; r0_l <= 1'b0; end
        else begin r0_v <= in_valid; r0_l <= in_valid && in_last; end
    end
    always @(posedge clk) begin r0_lv <= in_lv; r0_val <= in_val; r0_idx <= in_idx; end

    // -- key register (ot_hdc_select's key map) -----------------------------------------
    reg              k_v, k_l;
    reg [W*EW-1:0]   k_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin k_v <= 1'b0; k_l <= 1'b0; end
        else begin k_v <= r0_v; k_l <= r0_l; end
    end
    genvar j;
    generate
        for (j = 0; j < W; j = j + 1) begin : g_key
            wire [VW-1:0] v    = r0_val[VW*j +: VW];
            wire          zero = (v[VW-2:0] == 0);
            wire [VW-1:0] key  = zero ? {1'b1, {(VW-1){1'b0}}} : v[VW-1] ? ~v : {1'b1, v[VW-2:0]};
            wire          ninf = (v == {1'b1, 8'hFF, {(VW - 9){1'b0}}});
            always @(posedge clk)
                k_d[EW*j +: EW] <= r0_lv[j] ? {1'b1, key, ~r0_idx[IW*j +: IW], ninf} : {EW{1'b0}};
        end
    endgenerate

    // -- lane-group sorters + per-beat merge tree ------------------------------------------
    wire [G*LW-1:0] srt;
    wire [G-1:0]    s_v, s_l;
    generate
        for (j = 0; j < G; j = j + 1) begin : g_leaf
            ot_hdc_seltree_sort8 #(.EW(EW)) u (.clk(clk), .rst_n(rst_n), .iv(k_v), .il(k_l),
                .d(k_d[LW*j +: LW]), .ov(s_v[j]), .ol(s_l[j]), .q(srt[LW*j +: LW]));
        end
    endgenerate
    wire [LW-1:0] bl;
    wire          b_v, b_l;
    generate
        if (G > 1) begin : g_t1
            ot_hdc_seltree_tree #(.EW(EW), .NL(G)) u (.clk(clk), .rst_n(rst_n), .iv(s_v[0]), .il(s_l[0]),
                .d(srt), .ov(b_v), .ol(b_l), .q(bl));
        end else begin : g_t1n
            assign bl = srt; assign b_v = s_v[0]; assign b_l = s_l[0];
        end
    endgenerate

    // -- collector: the segment's beat lists, launched on its last beat ----------------------
    reg  [NB*LW-1:0] slot;
    reg  [NB*LW-1:0] c_d;
    reg              c_v;
    reg  [CW-1:0]    cnt;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin c_v <= 1'b0; cnt <= {CW{1'b0}}; end
        else begin
            c_v <= b_v && b_l;
            if (b_v) cnt <= b_l ? {CW{1'b0}} : cnt + 1'b1;
        end
    end
    generate
        for (j = 0; j < NB; j = j + 1) begin : g_slot
            localparam [CW-1:0] JC = j;
            wire here = (NB == 1) || (cnt == JC);
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) slot[LW*j +: LW] <= {LW{1'b0}};
                else if (b_v) slot[LW*j +: LW] <= (b_l || !here) ? (b_l ? {LW{1'b0}} : slot[LW*j +: LW]) : bl;
            end
            always @(posedge clk) c_d[LW*j +: LW] <= here ? bl : slot[LW*j +: LW];
        end
    endgenerate

    // -- merge over the beat lists ------------------------------------------------------------
    wire [LW-1:0] fl;
    wire          f_v;
    generate
        if (NB > 1) begin : g_t2
            wire f_l;
            ot_hdc_seltree_tree #(.EW(EW), .NL(NB)) u (.clk(clk), .rst_n(rst_n), .iv(c_v), .il(c_v),
                .d(c_d), .ov(f_v), .ol(f_l), .q(fl));
        end else begin : g_t2n
            assign fl = c_d; assign f_v = c_v;
        end
    endgenerate

    // -- the first K, ordered -------------------------------------------------------------------
    generate
        if (ORDER != 0) begin : g_ord
            localparam integer XW = 1 + IW + 1;     // {valid, ~index, ninf}: descending = ascending index
            wire [8*XW-1:0] xd, xq;
            wire            x_v, x_l;
            for (j = 0; j < 8; j = j + 1) begin : g_x
                wire [EW-1:0] e = fl[EW*j +: EW];
                assign xd[XW*j +: XW] = (j < K && e[EW-1]) ? {1'b1, e[IW:1], e[0]} : {XW{1'b0}};
            end
            ot_hdc_seltree_sort8 #(.EW(XW)) u (.clk(clk), .rst_n(rst_n), .iv(f_v), .il(f_v),
                .d(xd), .ov(x_v), .ol(x_l), .q(xq));
            // the sorter's last stage is the output register (a register-to-register copy
            // with no logic between would only add a hold-critical path)
            assign out_valid = x_v;
            for (j = 0; j < K; j = j + 1) begin : g_o
                assign out_v[j]            = xq[XW*j + XW - 1];
                assign out_idx[IW*j +: IW] = ~xq[XW*j + 1 +: IW];
                assign out_ninf[j]         = xq[XW*j];
            end
        end else begin : g_rank
            assign out_valid = f_v;
            for (j = 0; j < K; j = j + 1) begin : g_o
                assign out_v[j]            = fl[EW*j + EW - 1];
                assign out_idx[IW*j +: IW] = ~fl[EW*j + 1 +: IW];
                assign out_ninf[j]         = fl[EW*j];
            end
        end
    endgenerate
endmodule
