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

// Temporal padded-tree combiner over LB levels.  Input: one partial per cycle at most,
// `last` on a row's final partial.  Level k pairs its inputs in arrival order; a row's odd
// final element at a level is added to +0 (the tree's padding: exact, canonical), so every
// element travels one adder per level and order is preserved.  A row with at most 2^LB
// partials leaves at level LB exactly 3*LB cycles after its last partial.
module ot_hdc_v41x_wgt_comb #(
    parameter integer M = 1,
    parameter integer LB = 5,
    parameter integer TW = 1
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v,
    input  wire            last,
    input  wire [M*32-1:0] d,
    input  wire [M-1:0]    df,
    input  wire [TW-1:0]   t,
    output wire            ov,
    output wire [M*32-1:0] y,
    output wire [M-1:0]    yf,
    output wire [TW-1:0]   ot
);
    localparam integer EW = 1 + 1 + M*32 + M + TW;   // {v, last, d, f, t}
    wire [(LB+1)*EW-1:0] E;
    assign E[EW-1:0] = {v, last, d, df, t};
    genvar k;
    generate
        for (k = 0; k < LB; k = k + 1) begin : g_lvl
            wire            ev = E[k*EW + EW-1];
            wire            el = E[k*EW + EW-2];
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
            wire [TW:0]     nt;
            ot_hdc_v41x_wgt_add #(.M(M), .TW(TW + 1)) u_a (
                .clk(clk), .rst_n(rst_n), .v(issue),
                .a(pv ? pd : ed), .af(pv ? pf : ef),
                .b(pv ? ed : {(M*32){1'b0}}), .bf(pv ? ef : {M{1'b0}}),
                .t({el, et}), .ov(nv), .y(nd), .yf(nf), .ot(nt));
            assign E[(k+1)*EW +: EW] = {nv, nt[TW], nd, nf, nt[TW-1:0]};
        end
    endgenerate
    assign ov = E[LB*EW + EW-1] && E[LB*EW + EW-2];
    assign y = E[LB*EW + M + TW +: M*32];
    assign yf = E[LB*EW + TW +: M];
    assign ot = E[LB*EW +: TW];
endmodule

// Tree + combiners.  Inputs: G chunk sums of one beat (valid together) and the beat's tag
// {plg, last, rest}.  Level l (1..LG) adds node pairs; segment s of a beat with segment size
// 2^plg is node s of level plg, delayed through the remaining levels (so every plg leaves at
// the same time), then combiner s.  NC = G >> PMIN_LG combiners.  LATENCY 3*LG + 3*LB.
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
    input  wire              last,
    input  wire [TW-1:0]     t,
    input  wire [G*M*32-1:0] s,
    input  wire [G*M-1:0]    sf,
    output wire              ov,
    output wire [TW-1:0]     ot,
    output wire [(G>>PMIN_LG)*M*32-1:0] y,
    output wire [(G>>PMIN_LG)*M-1:0]    yf
);
    function automatic integer clog2(input integer n);
        integer r;
        begin r = 0; while ((1 << r) < n) r = r + 1; clog2 = r; end
    endfunction
    localparam integer LG = clog2(G);
    localparam integer NC = G >> PMIN_LG;
    localparam integer TT = 4 + 1 + TW;     // plg, last, rest
    localparam integer VW = G*M*32;
    localparam integer FW = G*M;
    localparam integer DW = NC*M*32;
    localparam integer DFW = NC*M;

    // level l: VA holds G >> l nodes (upper slots zero), VTA/VVA its beat tag and valid
    wire [(LG+1)*VW-1:0]  VA;
    wire [(LG+1)*FW-1:0]  VFA;
    wire [(LG+1)*TT-1:0]  VTA;
    wire [LG:0]           VVA;
    wire [(LG+1)*DW-1:0]  DA;
    wire [(LG+1)*DFW-1:0] DFA;
    assign VA[VW-1:0] = s; assign VFA[FW-1:0] = sf; assign VTA[TT-1:0] = {plg, last, t}; assign VVA[0] = v;
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
        // D[l]: plg == l takes the level's node, plg < l the previous D delayed 3 cycles
        for (l = 0; l <= LG; l = l + 1) begin : g_eq
            wire [3:0] pl = VTA[l*TT + TT-1 -: 4];
            if (l < PMIN_LG) begin : g_none
                assign DA[l*DW +: DW] = {DW{1'b0}};
                assign DFA[l*DFW +: DFW] = {DFW{1'b0}};
            end else if (l == PMIN_LG) begin : g_base
                assign DA[l*DW +: DW] = VA[l*VW +: DW];
                assign DFA[l*DFW +: DFW] = VFA[l*FW +: DFW];
            end else begin : g_mix
                wire [DW-1:0]  dd;
                wire [DFW-1:0] ddf;
                ot_hdc_delay #(.W(DW + DFW), .D(3)) u_d (.clk(clk), .rst_n(rst_n),
                    .d({DFA[(l-1)*DFW +: DFW], DA[(l-1)*DW +: DW]}), .q({ddf, dd}));
                for (n = 0; n < NC; n = n + 1) begin : g_s
                    if (n < (G >> l)) begin : g_node
                        assign DA[l*DW + n*M*32 +: M*32] = (pl == l) ? VA[l*VW + n*M*32 +: M*32] : dd[n*M*32 +: M*32];
                        assign DFA[l*DFW + n*M +: M] = (pl == l) ? VFA[l*FW + n*M +: M] : ddf[n*M +: M];
                    end else begin : g_dly
                        assign DA[l*DW + n*M*32 +: M*32] = dd[n*M*32 +: M*32];
                        assign DFA[l*DFW + n*M +: M] = ddf[n*M +: M];
                    end
                end
            end
        end
        wire [NC-1:0]    cv;
        wire [NC*TW-1:0] ct;
        for (n = 0; n < NC; n = n + 1) begin : g_cmb
            ot_hdc_v41x_wgt_comb #(.M(M), .LB(LB), .TW(TW)) u_c (
                .clk(clk), .rst_n(rst_n), .v(VVA[LG]), .last(VTA[LG*TT + TW]),
                .d(DA[LG*DW + n*M*32 +: M*32]), .df(DFA[LG*DFW + n*M +: M]), .t(VTA[LG*TT +: TW]),
                .ov(cv[n]), .y(y[n*M*32 +: M*32]), .yf(yf[n*M +: M]), .ot(ct[n*TW +: TW]));
        end
        assign ov = cv[0];
        assign ot = ct[TW-1:0];
    endgenerate
endmodule
