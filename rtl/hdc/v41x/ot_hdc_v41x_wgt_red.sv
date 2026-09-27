`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// R-ARITH reduction of the V4.1x weight engines (block `wgt`).
//
// The arithmetic contract (docs/ARCH_SPEC_V41.md 4, tools/hdc_golden_v41.csum):
// the terms of a row -- FP8/FP4 block values (quantised engine) or FP32 products
// (BF16/FP32 engine) -- are cut into contiguous chunks of 8, each chunk summed
// sequentially from +0, and the chunk sums combined by a pairwise tree padded
// with +0 to a power of two.  Three modules implement it:
//
//   ot_hdc_v41x_wgt_chain   the chunk: 8 skewed terms -> 7 chained adds
//                           (s1 = t0 + t1, s_j = s_{j-1} + t_j).  t0 + t1 equals
//                           (+0 + t0) + t1 bit for bit (the adder's zero bypass
//                           returns the other operand; (+-0) + (+-0) = +0).
//   ot_hdc_v41x_wgt_red     the tree: G chunk sums of a beat -> a pairwise tree;
//                           a row segment of P = 2^plg chunks is the level-plg
//                           node (an ALIGNED subtree of the row's tree), then
//                           NC temporal combiners (one per segment) finish the
//                           row's tree over its beats.
//   ot_hdc_v41x_wgt_comb    the temporal combiner: the padded pairwise tree
//                           over a stream of partials, one adder per level.
//
// DEPTH IS PER OP.  A beat leaves the tree at its own level plg and a row leaves
// the combiner at its own level nlev = ceil(log2(beats per row)), so the tree +
// combiner cost 3 * (plg + nlev) = 3 * ceil(log2(chunks)) cycles -- one adder
// latency per level of the row's own tree, as the spec's depth formula counts.
// Two ops of different depth must not collide: the issuing sequencer leaves
// 3 * max(0, plg1 - plg2, (plg1 + nlev1) - (plg2 + nlev2)) idle cycles between
// an op and a SHALLOWER successor (ot_hdc_v41x_wgt_tile), so at most one level
// hands a value to the combiner and at most one combiner level retires a row
// in any cycle, in issue order.
//
// Every adder is ot_hdc_qadd (3 cycles, IEEE binary32 RNE, gradual underflow,
// canonical +0, fail-closed fault on a nonfinite operand or overflow).
// ---------------------------------------------------------------------------

// M-position qadd with a fault operand path and a tag, LATENCY 3.
module ot_hdc_v41x_wgt_add #(
    parameter integer M = 1,
    parameter integer TW = 1
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v,
    input  wire [M*32-1:0] a,
    input  wire [M-1:0]    af,
    input  wire [M*32-1:0] b,
    input  wire [M-1:0]    bf,
    input  wire [TW-1:0]   t,
    output wire            ov,
    output wire [M*32-1:0] y,
    output wire [M-1:0]    yf,
    output wire [TW-1:0]   ot
);
    wire [M-1:0] qf;
    wire [M-1:0] df;
    genvar p;
    generate
        for (p = 0; p < M; p = p + 1) begin : g_p
            ot_hdc_qadd u_add (.clk(clk), .rst_n(rst_n), .v(v), .a(a[32*p +: 32]), .b(b[32*p +: 32]),
                               .y(y[32*p +: 32]), .fault(qf[p]));
        end
    endgenerate
    ot_hdc_delay #(.W(M + TW), .D(3)) u_t (.clk(clk), .rst_n(rst_n), .d({af | bf, t}), .q({df, ot}));
    ot_hdc_delay #(.W(1), .D(3), .RESET(1)) u_v (.clk(clk), .rst_n(rst_n), .d(v), .q(ov));
    assign yf = (df | qf) & {M{ov}};
endmodule

// The chunk chain: term j (j = 0..7) presented at cycle t + SK(j), SK = 0,0,3,6,..,18;
// the chunk sum leaves at t + 21.  v[j] is term j's valid (the lanes of a beat are valid
// together, skewed); adder j runs on v[j].
module ot_hdc_v41x_wgt_chain #(
    parameter integer M = 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        v,
    input  wire [8*M*32-1:0] t,
    input  wire [8*M-1:0]    tf,
    output wire              ov,
    output wire [M*32-1:0]   s,
    output wire [M-1:0]      sf
);
    wire [8*M*32-1:0] c;
    wire [8*M-1:0]    cf;
    wire [7:0]        cv;
    assign c[M*32-1:0] = t[M*32-1:0];
    assign cf[M-1:0] = tf[M-1:0];
    assign cv[0] = v[0];
    genvar j;
    generate
        for (j = 1; j < 8; j = j + 1) begin : g_add
            wire unused_t;
            ot_hdc_v41x_wgt_add #(.M(M), .TW(1)) u_a (
                .clk(clk), .rst_n(rst_n), .v(v[j]),
                .a(c[(j-1)*M*32 +: M*32]), .af(cf[(j-1)*M +: M]), .b(t[j*M*32 +: M*32]), .bf(tf[j*M +: M]),
                .t(1'b0), .ov(cv[j]), .y(c[j*M*32 +: M*32]), .yf(cf[j*M +: M]), .ot(unused_t));
        end
    endgenerate
    assign ov = cv[7];
    assign s = c[7*M*32 +: M*32];
    assign sf = cf[7*M +: M];
endmodule

// Temporal padded-tree combiner, up to LB levels.  Input: one partial per cycle at most,
// `last` on a row's final partial, `nlev` the row's level count (ceil(log2(partials))).
// Level k pairs its inputs in arrival order; a row's odd final element at a level is added
// to +0 (the tree's padding: exact, canonical), so every element travels one adder per
// level and order is preserved.  The row leaves when it reaches level nlev: 3*nlev cycles
// after its last partial (nlev = 0: the partial itself, the same cycle).
module ot_hdc_v41x_wgt_comb #(
    parameter integer M = 1,
    parameter integer LB = 5,
    parameter integer TW = 1
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v,
    input  wire            last,
    input  wire [2:0]      nlev,
    input  wire [M*32-1:0] din,
    input  wire [M-1:0]    dinf,
    input  wire [TW-1:0]   t,
    output wire            ov,
    output wire [M*32-1:0] y,
    output wire [M-1:0]    yf,
    output wire [TW-1:0]   ot
);
    localparam integer EW = 1 + 1 + 3 + M*32 + M + TW;   // {v, last, nlev, d, f, t}
    wire [(LB+1)*EW-1:0] E;
    wire [LB:0]          hit;
    assign E[EW-1:0] = {v, last, nlev, din, dinf, t};
    genvar k;
    generate
        for (k = 0; k <= LB; k = k + 1) begin : g_hit
            assign hit[k] = E[k*EW + EW-1] && (E[k*EW + EW-3 -: 3] == k);
        end
        for (k = 0; k < LB; k = k + 1) begin : g_lvl
            wire            ev = E[k*EW + EW-1] && !hit[k];
            wire            el = E[k*EW + EW-2];
            wire [2:0]      en = E[k*EW + EW-3 -: 3];
            wire [M*32-1:0] ed = E[k*EW + M + TW +: M*32];
            wire [M-1:0]    ef = E[k*EW + TW +: M];
            wire [TW-1:0]   et = E[k*EW +: TW];
            reg            pv;
            reg [M*32-1:0] pd;
            reg [M-1:0]    pf;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) pv <= 1'b0;
                else if (ev) pv <= !pv && !el;
            end
            always @(posedge clk) if (ev && !pv) begin pd <= ed; pf <= ef; end
            wire issue = ev && (pv || el);
            wire            nv;
            wire [M*32-1:0] nd;
            wire [M-1:0]    nf;
            wire [TW+3:0]   nt;
            ot_hdc_v41x_wgt_add #(.M(M), .TW(TW + 4)) u_a (
                .clk(clk), .rst_n(rst_n), .v(issue),
                .a(pv ? pd : ed), .af(pv ? pf : ef),
                .b(pv ? ed : {(M*32){1'b0}}), .bf(pv ? ef : {M{1'b0}}),
                .t({el, en, et}), .ov(nv), .y(nd), .yf(nf), .ot(nt));
            assign E[(k+1)*EW +: EW] = {nv, nt[TW+3], nt[TW+2:TW], nd, nf, nt[TW-1:0]};
        end
    endgenerate
    // the retiring level (at most one per cycle): an AND-OR select
    reg [M*32-1:0] sy;
    reg [M-1:0]    sf;
    reg [TW-1:0]   st;
    integer i;
    always @(*) begin
        sy = {(M*32){1'b0}}; sf = {M{1'b0}}; st = {TW{1'b0}};
        for (i = 0; i <= LB; i = i + 1) begin
            sy = sy | (E[i*EW + M + TW +: M*32] & {(M*32){hit[i]}});
            sf = sf | (E[i*EW + TW +: M] & {M{hit[i]}});
            st = st | (E[i*EW +: TW] & {TW{hit[i]}});
        end
    end
    assign ov = |hit;
    assign y = sy;
    assign yf = sf;
    assign ot = st;
endmodule

// Tree + combiners.  Inputs: G chunk sums of one beat (valid together) and the beat's tag
// {plg, nlev, last, rest}.  Level l (1..LG) adds node pairs; segment s of a beat with segment
// size 2^plg is node s of level plg, handed to combiner s (NC = G >> PMIN_LG combiners)
// through a register.  The combiners' output is registered.
// LATENCY 3*plg + 1 + 3*nlev + 1.
module ot_hdc_v41x_wgt_red #(
    parameter integer G = 8,
    parameter integer M = 1,
    parameter integer LB = 5,
    parameter integer PMIN_LG = 0,
    parameter integer TW = 1                // `rest` of the tag, carried to the output
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              v,
    input  wire [3:0]        plg,
    input  wire [2:0]        nlev,
    input  wire              last,
    input  wire [TW-1:0]     t,
    input  wire [G*M*32-1:0] s,
    input  wire [G*M-1:0]    sf,
    output reg               ov,
    output reg  [TW-1:0]     ot,
    output reg  [(G>>PMIN_LG)*M*32-1:0] y,
    output reg  [(G>>PMIN_LG)*M-1:0]    yf
);
    function automatic integer clog2(input integer n);
        integer r;
        begin r = 0; while ((1 << r) < n) r = r + 1; clog2 = r; end
    endfunction
    localparam integer LG = clog2(G);
    localparam integer NC = G >> PMIN_LG;
    localparam integer TT = 4 + 3 + 1 + TW;     // plg, nlev, last, rest
    localparam integer VW = G*M*32;
    localparam integer FW = G*M;
    localparam integer DW = NC*M*32;
    localparam integer DFW = NC*M;

    // level l: VA holds G >> l nodes (upper slots zero), VTA/VVA its beat tag and valid
    wire [(LG+1)*VW-1:0]  VA;
    wire [(LG+1)*FW-1:0]  VFA;
    wire [(LG+1)*TT-1:0]  VTA;
    wire [LG:0]           VVA;
    assign VA[VW-1:0] = s; assign VFA[FW-1:0] = sf; assign VTA[TT-1:0] = {plg, nlev, last, t}; assign VVA[0] = v;
    genvar l, n;
    generate
        for (l = 1; l <= LG; l = l + 1) begin : g_lvl
            localparam integer NN = G >> l;
            wire [VW-1:0] pv = VA[(l-1)*VW +: VW];
            wire [FW-1:0] pf = VFA[(l-1)*FW +: FW];
            wire [NN*M*32-1:0] nv;
            wire [NN*M-1:0]    nf;
            wire [NN-1:0]      av;
            wire [NN*TT-1:0]   at;
            for (n = 0; n < NN; n = n + 1) begin : g_n
                ot_hdc_v41x_wgt_add #(.M(M), .TW(TT)) u_a (
                    .clk(clk), .rst_n(rst_n), .v(VVA[l-1]),
                    .a(pv[(2*n)*M*32 +: M*32]), .af(pf[(2*n)*M +: M]),
                    .b(pv[(2*n+1)*M*32 +: M*32]), .bf(pf[(2*n+1)*M +: M]),
                    .t(VTA[(l-1)*TT +: TT]), .ov(av[n]), .y(nv[n*M*32 +: M*32]), .yf(nf[n*M +: M]),
                    .ot(at[n*TT +: TT]));
            end
            assign VVA[l] = av[0];
            assign VTA[l*TT +: TT] = at[TT-1:0];
            if (NN < G) begin : g_pad
                assign VA[l*VW +: VW] = {{((G-NN)*M*32){1'b0}}, nv};
                assign VFA[l*FW +: FW] = {{((G-NN)*M){1'b0}}, nf};
            end else begin : g_full
                assign VA[l*VW +: VW] = nv;
                assign VFA[l*FW +: FW] = nf;
            end
        end
    endgenerate

    // the tap: the level whose beat has plg == level (at most one per cycle), registered
    wire [LG:0] tap;
    generate
        for (l = 0; l <= LG; l = l + 1) begin : g_tap
            if (l < PMIN_LG) begin : g_no
                assign tap[l] = 1'b0;
            end else begin : g_yes
                assign tap[l] = VVA[l] && (VTA[l*TT + TT-1 -: 4] == l);
            end
        end
    endgenerate
    reg [DW-1:0]  cd;
    reg [DFW-1:0] cf;
    reg [TT-1:0]  ctg;
    reg           cv;
    reg [DW-1:0]  md;
    reg [DFW-1:0] mf;
    reg [TT-1:0]  mt;
    integer i, j;
    always @(*) begin
        md = {DW{1'b0}}; mf = {DFW{1'b0}}; mt = {TT{1'b0}};
        for (i = PMIN_LG; i <= LG; i = i + 1) begin
            mt = mt | (VTA[i*TT +: TT] & {TT{tap[i]}});
            for (j = 0; j < NC; j = j + 1)
                if (j < (G >> i)) begin
                    md[j*M*32 +: M*32] = md[j*M*32 +: M*32] | (VA[i*VW + j*M*32 +: M*32] & {(M*32){tap[i]}});
                    mf[j*M +: M] = mf[j*M +: M] | (VFA[i*FW + j*M +: M] & {M{tap[i]}});
                end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) cv <= 1'b0;
        else cv <= |tap;
    end
    always @(posedge clk) begin
        cd <= md; cf <= mf; ctg <= mt;
    end

    wire [NC-1:0]      rv;
    wire [NC*TW-1:0]   rt;
    wire [DW-1:0]      ry;
    wire [DFW-1:0]     rf;
    generate
        for (n = 0; n < NC; n = n + 1) begin : g_cmb
            ot_hdc_v41x_wgt_comb #(.M(M), .LB(LB), .TW(TW)) u_c (
                .clk(clk), .rst_n(rst_n), .v(cv), .last(ctg[TW]), .nlev(ctg[TW+3:TW+1]),
                .din(cd[n*M*32 +: M*32]), .dinf(cf[n*M +: M]), .t(ctg[TW-1:0]),
                .ov(rv[n]), .y(ry[n*M*32 +: M*32]), .yf(rf[n*M +: M]), .ot(rt[n*TW +: TW]));
        end
    endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ov <= 1'b0;
        else ov <= rv[0];
    end
    always @(posedge clk) begin
        ot <= rt[TW-1:0];
        y <= ry;
        yf <= rf;
    end
endmodule
