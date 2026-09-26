`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Weight-engine TILE of the re-specified DeepSeek-V4.1-Flash decode die
// (block `wgt`, docs/ARCH_SPEC_V41.md 6 item 3).  KIND = 0: the quantised
// engine (FP8 E4M3 / FP4 E2M1 weights with a UE8M0 scale per row x 32-block,
// FP8 activation, tools/hdc_golden_v41.linear_q under R-ARITH chunk8, BF16
// out); KIND = 1: the BF16/FP32 engine (hdc_golden_v41.matvec_c / mv /
// linear_bf16 under chunk8: mul(w, bf16(x)) products, FP32 and BF16 out).
//
// GEOMETRY.  G chunk units of 8 lanes (L = 8G lanes).  A lane takes one ROM
// word per cycle: a 32-block (KIND 0: 32 MACs, one exact block dot) or one
// weight (KIND 1: one MAC), for M positions (MTP lane multiplier: one weight
// read feeds M MAC lanes).  A chunk unit is one R-ARITH chunk: 8 contiguous
// terms summed by a chain of 7 adders.  A row SEGMENT is P = 2^plg chunk
// units (8P lanes), the level-plg node of the chunk tree; G/P rows run side
// by side, each walking its ceil(nb / 8P) BEATS (aligned runs of 8P terms)
// over consecutive cycles; the beats' segment sums are combined by the
// padded pairwise tree in time (ot_hdc_v41x_wgt_comb).  Terms past the row
// (nb not a multiple of 8P) and rows past nrows are forced to +0 in the lane
// (z), which IS the padding of csum.  Result: bit-exact csum of each row for
// every legal plg -- the row's tree is geometry-independent.
//
// ROM READ NETWORK (the read port).  The tile holds one address per beat; the
// weight ROM is banked per lane: bank j (lane j = 8u + c) holds, at address
//     a = base + rg * nbeat + q        (row group rg, beat q),
// the word of row rg*(G/P) + (j >> (3+plg)), term q*8P + (j mod 8P).
// base = wbase + (ind ? eid * estride : 0): a routed expert's weights are
// found from its id (data-dependent address, the as-built QE's qe_ind).
// The tile presents 8 request buses, one per chain position c, each SKEWED by
// SK(c) = 3 * max(c - 1, 0) cycles -- the chain's add latency -- so skew
// costs one delayed address, not delayed data: rq_v[c], rq_a[c], rq_q[c]
// (beat index, for the activation broadcast), rq_plg[c], rq_tag[c].
// Every bank of chain position c answers exactly RL cycles after its request
// on rd_w[j] (KIND 0: 264 bits {we, codes}, see ot_hdc_v41x_wgt_bdot;
// KIND 1: 32 bits).  The ACTIVATION is quantised once per op (by
// ot_hdc_actquant, outside) and BROADCAST from a die-level activation buffer
// on the same request buses: rd_x[j] carries term q*8P + (j mod 8P) of op
// rq_tag for each of M positions (KIND 0: 264 bits {xe, E4M3 codes};
// KIND 1: 16 bits BF16), also RL cycles after the request.
//
// PROTOCOLS.  Descriptor: valid/ready (d_v, d_rdy), registered; a queue of
// one op behind the running one, so ops issue back to back (see LATENCY for the
// one gap rule).
// Output: credit-based -- the tile starts a row group only while it holds an
// output credit (OCRED at reset, +1 per o_cr pulse); o_v carries the row
// group's G >> plg results (o_mask: which are real rows), in issue order.
// Faults (o_f, per result and position) fail closed: a NaN code, a block
// value past binary32, or any adder fault (nonfinite operand, overflow).
//
// LATENCY (descriptor accept to a row group's result):
//   3 (descriptor A, B, C) + 1 (beat register) + RL + CL + 3*plg + 1 + 3*nlev + 1 + 1
//   CL = 30 (KIND 0: 9 block dot + 21 chain) or 25 (KIND 1: 4 multiply + 21 chain);
//   plg + nlev = ceil(log2(chunks per row)) for a well-chosen segment: one adder
//   latency per level of the row's own padded tree (ot_hdc_v41x_wgt_red).
// Throughput one beat (L lanes x M positions) per cycle, sustained across rows and
// across ops of equal depth; before an op SHALLOWER than its predecessor the tile
// idles 3 * max(0, plg1 - plg2, (plg1 + nlev1) - (plg2 + nlev2)) cycles (the only
// bubble), so results never collide and leave in issue order.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_wgt_tile #(
    parameter integer KIND = 0,
    parameter integer G = 1,              // chunk units (8 lanes each)
    parameter integer M = 1,              // MTP lane multiplier (positions per weight read)
    parameter integer LB = 5,             // combiner levels: up to 2^LB beats per row
    parameter integer PMIN_LG = 0,        // smallest segment (log2 chunk units)
    parameter integer AW = 20,            // ROM address
    parameter integer NBW = 14,           // terms per row (blocks or weights)
    parameter integer RWW = 16,           // rows / row groups
    parameter integer EIW = 9,            // expert id
    parameter integer TGW = 4,            // op tag
    parameter integer RL = 2,             // ROM / activation read latency
    parameter integer OCRED = 128         // output credits at reset
) (
    input  wire                  clk,
    input  wire                  rst_n,
    // descriptor
    input  wire                  d_v,
    output wire                  d_rdy,
    input  wire [3:0]            d_plg,
    input  wire [NBW-1:0]        d_nb,
    input  wire [RWW-1:0]        d_nrows,
    input  wire [AW-1:0]         d_wbase,
    input  wire                  d_ind,
    input  wire [EIW-1:0]        d_eid,
    input  wire [AW-1:0]         d_estride,
    input  wire                  d_fp4,
    input  wire [TGW-1:0]        d_tag,
    // read requests, one bus per chain position
    output wire [7:0]            rq_v,
    output wire [8*AW-1:0]       rq_a,
    output wire [8*NBW-1:0]      rq_q,
    output wire [8*4-1:0]        rq_plg,
    output wire [8*TGW-1:0]      rq_tag,
    // read data, RL cycles after the lane's request
    input  wire [8*G*(KIND ? 32 : 264)-1:0]       rd_w,
    input  wire [8*G*M*(KIND ? 16 : 264)-1:0]     rd_x,
    // results
    input  wire                  o_cr,
    output reg                   o_v,
    output reg  [RWW-1:0]        o_rg,
    output reg  [TGW-1:0]        o_tag,
    output reg  [(G>>PMIN_LG)-1:0]        o_mask,
    output reg  [(G>>PMIN_LG)*M*32-1:0]   o_y,
    output reg  [(G>>PMIN_LG)*M*16-1:0]   o_bf,
    output reg  [(G>>PMIN_LG)*M-1:0]      o_f,
    output wire                  idle
);
    function automatic integer clog2(input integer n);
        integer r;
        begin r = 0; while ((1 << r) < n) r = r + 1; clog2 = r; end
    endfunction
    localparam integer LG = clog2(G);
    localparam integer L = 8 * G;
    localparam integer NC = G >> PMIN_LG;
    localparam integer WW = KIND ? 32 : 264;
    localparam integer XW = KIND ? 16 : 264;
    localparam integer CL = KIND ? 25 : 30;
    localparam integer CW = 8;

    // -- descriptor stage A (registered boundary) ---------------------------------------------------
    reg              a_v;
    reg [3:0]        a_plg;
    reg [NBW-1:0]    a_nb;
    reg [RWW-1:0]    a_nrows;
    reg [AW-1:0]     a_wbase, a_estride;
    reg              a_ind, a_fp4;
    reg [EIW-1:0]    a_eid;
    reg [TGW-1:0]    a_tag;
    // stage B: expert offset, beats per row, row groups
    reg              b_v;
    reg [3:0]        b_plg;
    reg [NBW-1:0]    b_nb, b_nbeat;
    reg [RWW-1:0]    b_nrows, b_nrg;
    reg [AW-1:0]     b_wbase, b_off;
    reg              b_fp4;
    reg [TGW-1:0]    b_tag;
    // stage C: the running op
    reg              c_v;
    reg [3:0]        c_plg;
    reg [NBW-1:0]    c_nb, c_nbeat, c_q;
    reg [RWW-1:0]    c_nrows, c_nrg, c_rg;
    reg [AW-1:0]     c_a;
    reg              c_fp4;
    reg [TGW-1:0]    c_tag;
    reg [NBW-1:0]    c_nbm1;
    reg [RWW-1:0]    c_nrgm1;
    reg [2:0]        c_nlev;              // combiner levels: ceil(log2(beats per row))
    reg              c_first;             // the op's first beat is next
    reg [5:0]        g_r;                 // idle cycles owed before the op's first beat
    reg [5:0]        sl;                  // idle cycles since the last issued beat (saturating)
    reg [CW-1:0]     cred;
    reg              cr_r;

    function automatic [2:0] clog2v(input [NBW-1:0] x);
        integer i;
        begin
            clog2v = 3'd0;
            for (i = 0; i < 7; i = i + 1)
                if (({{NBW{1'b0}}, 1'b1} << i) < {1'b0, x}) clog2v = i + 1;
        end
    endfunction

    wire c_lastq = (c_q == c_nbm1);
    wire c_lastrg = (c_rg == c_nrgm1);
    //: a row group starts only with an output credit; an op's first beat also waits out the
    //: gap a shallower op owes its predecessor (ot_hdc_v41x_wgt_red: DEPTH IS PER OP)
    wire issue = c_v && ((c_q != {NBW{1'b0}}) ||
                         ((cred != {CW{1'b0}}) && (!c_first || (sl >= g_r))));
    wire c_done = issue && c_lastq && c_lastrg;
    wire c_free = !c_v || c_done;
    wire b_mv = b_v && c_free;
    wire b_free = !b_v || b_mv;
    wire a_mv = a_v && b_free;
    assign d_rdy = !a_v || a_mv;

    // (nb + 8P - 1) >> (3 + plg), (nrows + G/P - 1) >> (LG - plg)
    wire [NBW:0]   nb_up = {1'b0, a_nb} + ({{NBW{1'b0}}, 1'b1} << (3 + a_plg)) - 1'b1;
    wire [RWW:0]   nr_up = {1'b0, a_nrows} + ({{RWW{1'b0}}, 1'b1} << (LG - a_plg)) - 1'b1;

    wire [2:0] b_nlev = clog2v(b_nbeat);
    wire [4:0] dep_c = {1'b0, c_plg} + {2'b0, c_nlev};
    wire [4:0] dep_b = {1'b0, b_plg} + {2'b0, b_nlev};
    wire [4:0] gp = (c_plg > b_plg) ? {1'b0, c_plg - b_plg} : 5'd0;
    wire [4:0] gd = (dep_c > dep_b) ? dep_c - dep_b : 5'd0;
    wire [4:0] gm = (gp > gd) ? gp : gd;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_v <= 1'b0; b_v <= 1'b0; c_v <= 1'b0; cred <= OCRED; cr_r <= 1'b0;
            c_plg <= 4'd0; c_nlev <= 3'd0; c_first <= 1'b0; g_r <= 6'd0; sl <= 6'd0;
        end else begin
            cr_r <= o_cr;
            if (b_mv) begin
                c_plg <= b_plg; c_nlev <= b_nlev; c_first <= 1'b1;
                g_r <= {gm, 1'b0} + {1'b0, gm};          // 3 cycles per level
            end else if (issue) begin
                c_first <= 1'b0;
            end
            if (issue) sl <= 6'd0;
            else if (sl != 6'h3F) sl <= sl + 1'b1;
            if (d_v && d_rdy) a_v <= 1'b1;
            else if (a_mv) a_v <= 1'b0;
            if (a_mv) b_v <= 1'b1;
            else if (b_mv) b_v <= 1'b0;
            if (b_mv) c_v <= 1'b1;
            else if (c_done) c_v <= 1'b0;
            cred <= cred - {{(CW-1){1'b0}}, issue && (c_q == {NBW{1'b0}})} + {{(CW-1){1'b0}}, cr_r};
        end
    end
    always @(posedge clk) begin
        if (d_v && d_rdy) begin
            a_plg <= d_plg; a_nb <= d_nb; a_nrows <= d_nrows; a_wbase <= d_wbase; a_estride <= d_estride;
            a_ind <= d_ind; a_fp4 <= d_fp4; a_eid <= d_eid; a_tag <= d_tag;
        end
        if (a_mv) begin
            b_plg <= a_plg; b_nb <= a_nb; b_nrows <= a_nrows; b_wbase <= a_wbase; b_fp4 <= a_fp4; b_tag <= a_tag;
            b_off <= a_ind ? a_eid * a_estride : {AW{1'b0}};
            b_nbeat <= nb_up[NBW:0] >> (3 + a_plg);
            b_nrg <= nr_up[RWW:0] >> (LG - a_plg);
        end
        if (b_mv) begin
            c_nb <= b_nb; c_nbeat <= b_nbeat; c_nrows <= b_nrows; c_nrg <= b_nrg;
            c_nbm1 <= b_nbeat - 1'b1; c_nrgm1 <= b_nrg - 1'b1;
            c_a <= b_wbase + b_off; c_q <= {NBW{1'b0}}; c_rg <= {RWW{1'b0}}; c_fp4 <= b_fp4; c_tag <= b_tag;
        end else if (issue) begin
            c_a <= c_a + 1'b1;
            if (c_lastq) begin c_q <= {NBW{1'b0}}; c_rg <= c_rg + 1'b1; end
            else c_q <= c_q + 1'b1;
        end
    end
    assign idle = !a_v && !b_v && !c_v;

    // -- beat record and its skewed taps ---------------------------------------------------------
    localparam integer RW = 1 + AW + NBW + RWW + 1 + 4 + 3 + NBW + RWW + 1 + TGW;
    reg          r0v;
    reg [RW-2:0] r0d;
    wire [RW-1:0] r0 = {r0v, r0d};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) r0v <= 1'b0;
        else r0v <= issue;
    end
    always @(posedge clk)
        r0d <= {c_a, c_q, c_rg, c_lastq, c_plg, c_nlev, c_nb, c_nrows, c_fp4, c_tag};
    wire [19*RW-1:0] tapl;       // tapl[k] = r0 delayed k cycles
    assign tapl[RW-1:0] = r0;
    genvar k, c, u;
    generate
        for (k = 1; k <= 18; k = k + 1) begin : g_sk
            ot_hdc_delay #(.W(RW), .D(1)) u_d (.clk(clk), .rst_n(rst_n), .d(tapl[(k-1)*RW +: RW]), .q(tapl[k*RW +: RW]));
        end
    endgenerate
    // the skew line's valid bits carry a reset
    reg [18:1] tv;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) tv <= 18'd0;
        else tv <= {tv[17:1], r0[RW-1]};
    end

    wire [7:0]   lvall, lfall;
    wire [8*G-1:0] lzall;
    generate
        for (c = 0; c < 8; c = c + 1) begin : g_pos
            localparam integer SK = (c < 2) ? 0 : 3 * (c - 1);
            wire [RW-1:0] t = tapl[SK*RW +: RW];
            wire          tvv = (SK == 0) ? r0[RW-1] : tv[(SK == 0) ? 1 : SK];
            wire [AW-1:0]  t_a;
            wire [NBW-1:0] t_q, t_nb;
            wire [RWW-1:0] t_rg, t_nrows;
            wire           t_last, t_fp4;
            wire [3:0]     t_plg;
            wire [TGW-1:0] t_tag;
            wire [2:0]     t_nlev;
            assign {t_a, t_q, t_rg, t_last, t_plg, t_nlev, t_nb, t_nrows, t_fp4, t_tag} = t[RW-2:0];
            assign rq_v[c] = tvv;
            assign rq_a[c*AW +: AW] = t_a;
            assign rq_q[c*NBW +: NBW] = t_q;
            assign rq_plg[c*4 +: 4] = t_plg;
            assign rq_tag[c*TGW +: TGW] = t_tag;
            // lane controls, delayed RL cycles to meet the read data
            wire [G-1:0] zc;
            for (u = 0; u < G; u = u + 1) begin : g_u
                localparam integer J = 8 * u + c;
                wire [NBW+8:0]  blk = ({9'd0, t_q} << (3 + t_plg)) + (J & ((8 << t_plg) - 1));
                wire [RWW+8:0]  row = ({9'd0, t_rg} << (LG - t_plg)) + (J >> (3 + t_plg));
                assign zc[u] = (blk >= {9'd0, t_nb}) || (row >= {9'd0, t_nrows});
            end
            wire          lv, lfp4;
            wire [G-1:0]  lz;
            ot_hdc_delay #(.W(1), .D(RL), .RESET(1)) u_v (.clk(clk), .rst_n(rst_n), .d(tvv), .q(lv));
            ot_hdc_delay #(.W(G + 1), .D(RL)) u_z (.clk(clk), .rst_n(rst_n), .d({t_fp4, zc}), .q({lfp4, lz}));
            assign lvall[c] = lv;
            assign lfall[c] = lfp4;
            assign lzall[c*G +: G] = lz;
        end
    endgenerate

    // -- chunk units -----------------------------------------------------------------------------------
    wire [G-1:0]      cu_v;
    wire [G*M*32-1:0] cu_s;
    wire [G*M-1:0]    cu_f;
    generate
        for (u = 0; u < G; u = u + 1) begin : g_cu
            wire [7:0] lv8, lz8, lf8;
            for (c = 0; c < 8; c = c + 1) begin : g_c
                assign lv8[c] = lvall[c];
                assign lz8[c] = lzall[c*G + u];
                assign lf8[c] = lfall[c];
            end
            if (KIND == 0) begin : g_q
                ot_hdc_v41x_wgt_qchunk #(.M(M)) u_ch (
                    .clk(clk), .rst_n(rst_n), .v(lv8), .z(lz8), .fp4(lf8),
                    .w(rd_w[u*8*WW +: 8*WW]), .x(rd_x[u*8*M*XW +: 8*M*XW]),
                    .ov(cu_v[u]), .s(cu_s[u*M*32 +: M*32]), .sf(cu_f[u*M +: M]));
            end else begin : g_m
                ot_hdc_v41x_wgt_mchunk #(.M(M)) u_ch (
                    .clk(clk), .rst_n(rst_n), .v(lv8), .z(lz8),
                    .w(rd_w[u*8*WW +: 8*WW]), .x(rd_x[u*8*M*XW +: 8*M*XW]),
                    .ov(cu_v[u]), .s(cu_s[u*M*32 +: M*32]), .sf(cu_f[u*M +: M]));
            end
        end
    endgenerate

    // -- beat tag to the tree: {mask, rg, tag}, delayed RL + CL from the beat record ---------------------
    localparam integer TW = NC + RWW + TGW;
    wire [AW-1:0]  r_a;
    wire [NBW-1:0] r_q, r_nb;
    wire [RWW-1:0] r_rg, r_nrows;
    wire           r_last, r_fp4;
    wire [3:0]     r_plg;
    wire [TGW-1:0] r_tag;
    wire [2:0]     r_nlev;
    assign {r_a, r_q, r_rg, r_last, r_plg, r_nlev, r_nb, r_nrows, r_fp4, r_tag} = r0[RW-2:0];
    wire [NC-1:0] r_mask;
    genvar s;
    generate
        for (s = 0; s < NC; s = s + 1) begin : g_mask
            wire [RWW+8:0] row = ({9'd0, r_rg} << (LG - r_plg)) + s;
            assign r_mask[s] = ((s >> (LG - r_plg)) == 0) && (row < {9'd0, r_nrows});
        end
    endgenerate
    wire          tr_v, tr_last;
    wire [3:0]    tr_plg;
    wire [2:0]    tr_nlev;
    wire [TW-1:0] tr_t;
    ot_hdc_delay #(.W(1), .D(RL + CL), .RESET(1)) u_trv (.clk(clk), .rst_n(rst_n), .d(r0[RW-1]), .q(tr_v));
    ot_hdc_delay #(.W(8 + TW), .D(RL + CL)) u_tr (.clk(clk), .rst_n(rst_n),
                                                  .d({r_plg, r_nlev, r_last, r_mask, r_rg, r_tag}),
                                                  .q({tr_plg, tr_nlev, tr_last, tr_t}));

    wire              rv;
    wire [TW-1:0]     rt;
    wire [NC*M*32-1:0] ry;
    wire [NC*M-1:0]    rf;
    ot_hdc_v41x_wgt_red #(.G(G), .M(M), .LB(LB), .PMIN_LG(PMIN_LG), .TW(TW)) u_red (
        .clk(clk), .rst_n(rst_n), .v(tr_v), .plg(tr_plg), .nlev(tr_nlev), .last(tr_last), .t(tr_t), .s(cu_s), .sf(cu_f),
        .ov(rv), .ot(rt), .y(ry), .yf(rf));

    // -- registered output: FP32 and its BF16 rounding (RNE on the bits, as hdc_golden.to_bf16) ---------
    integer i;
    reg [32:0] rb;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) o_v <= 1'b0;
        else o_v <= rv;
    end
    always @(posedge clk) begin
        {o_mask, o_rg, o_tag} <= rt;
        o_y <= ry;
        o_f <= rf;
        for (i = 0; i < NC * M; i = i + 1) begin
            rb = {1'b0, ry[32*i +: 32]} + 33'h7FFF + {32'd0, ry[32*i + 16]};
            o_bf[16*i +: 16] <= rb[31:16];
        end
    end
endmodule
