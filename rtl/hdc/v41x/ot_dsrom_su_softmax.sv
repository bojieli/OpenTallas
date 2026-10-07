`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DS-ROM recovery lever su_softmax (2026-10-04): the attention softmax of one
// die's H heads as ONE fused 1.2 GHz pipeline (default-off, new file).  It
// replaces the five serial stream-unit ops of tools/dsrom_1m_su.chain_attend
// (scale + row max | exp(s - max) + row sum | exp(sink - max) + den |
// acc / den -> BF16 | inverse RoPE of the 64-element tail -> BF16) with the
// same binary32 operations in the same order (tools/hdc_golden_v41.attend):
//
//   s   = s_raw * scale                       (mul, RNE)
//   mb  = max_t s                             (ordered-key max: order free)
//   e   = exp(s + (-mb))                      (add, ot_hdc_v41x_exp)
//   es  = csum(e)                             (R-ARITH chunk-8: 7 sequential adds per chunk of 8 from the row's
//                                              start, then the pairwise tree over the chunk sums padded with +0)
//   den = es + exp(sink + (-mb))              (the sink exp runs as soon as mb is known, beside the row sum)
//   o0  = bf16(pv / den)                      (ot_hdc_v41x_fdiv, RNE; BF16 RNE)
//   o   = o0 with its last TAIL elements rotated as adjacent pairs (a, b), conjugate:
//         re = bf16(a*c + b*s),  im = bf16(b*c + -(a*s))
//
// No vector-memory round trip, no op issue: each stage feeds the next.
//
// LANES.  H heads x LPH lanes; vector v of head h holds elements v*LPH .. v*LPH + LPH-1 (LPH a power of two >= 8,
// so a chunk of 8 is 8 adjacent lanes of one vector and a vector's chunk sums are an aligned subtree of the row's
// chunk tree).  Scores arrive nv vectors a head (nv = T / LPH), PV rows NPV = 512 / LPH vectors a head.
//
// THE ROW SUM'S TREE.  In a vector: LPH/8 chunk sums, log2(LPH/8) levels.  Across vectors: a streaming binary
// counter, level t holds a left operand until its right sibling arrives; the row's last item combines with a held
// operand or passes (its sibling is the +0 padding: x + (+0) = x).  Every level step, pass or add, takes LA_T + 1
// cycles (the pass / add select is registered), so items stay in order.  The result is tapped at level lt = ceil(log2 nv) (an input).  This is exactly the
// golden's tree over 2^ceil(log2(T/8)) leaves (ot_hdc_v41x_vec_red's argument).
//
// WIRE.  DIN register stages on the score and PV inputs (hub traverse in), DOUT on the e and o outputs (out), RWU
// stages from the lanes to the reduction root and RWD from the root back to the lanes, for both reductions.
//
// Units: ot_hdc_qmul_lat / ot_hdc_qadd_lat (build with rtl/hdc/ot_hdc_fastfp_lat_f12.sv: the 1.2 GHz f12 mul LAT 5
// and add LAT 4), ot_hdc_v41x_exp (rtl/hdc/v41x/ot_hdc_v41x_sfu.sv), ot_dsrom_su_fdiv_f12 (the 1.2 GHz restaging of
// ot_hdc_v41x_fdiv, bit-identical).
//
// MARGIN = 1 (owner margin-first rule 2026-10-06: block SS setup >= +40 ps at 0.833 ns, every class within ~50 ps
// staged in one step; use with ADD6 2, LM 9, ELM 9, EXP6 1, EXPNS 2, DENK 1): the input-registered all-cut adder and
// the all-cut multiplier everywhere (ot_dsrom_su_softmax_m9.sv), the non-restoring divider (NR 1), the configuration
// inputs (nv, lt, scale, sink, cos, sin) registered at the pin, the per-lane running max as two interleaved
// accumulators (even / odd vectors) on a two-cycle compare | select recurrence merged after the row, every max-tree
// level compare | select, and lane-local registered copies of the RoPE pair index, the tail flag and the
// denominator load (x6u40 / x7u35 classes: u_ul -> c +0.6 ps, u_dndv -> denl +10.8, rmax recurrence +20..+42,
// u_urd -> ob +44).  Same arithmetic, same order, bit for bit; only register boundaries move.
// ---------------------------------------------------------------------------
module ot_dsrom_su_softmax #(
    parameter integer H     = 16,
    parameter integer LPH   = 16,
    parameter integer NVMAX = 40,        // score vectors a head, at most (T 640 / LPH)
    parameter integer LTMAX = 6,         // ceil(log2 NVMAX)
    parameter integer TAIL  = 64,        // rotated tail of each 512-element row
    parameter integer DIN   = 33,
    parameter integer DOUT  = 23,
    parameter integer RWU   = 9,
    parameter integer RWD   = 9,
    parameter integer LM    = 5,
    parameter integer LA    = 4,
    parameter integer ELM   = LM,        // the exp units' multiplier / add latencies (ot_hdc_v41x_exp)
    parameter integer ELA   = LA,
    parameter integer ADD6  = 0,         // 1: every add is the six-cut f12 adder (ot_dsrom_su_softmax_add6) at the
                                         // register-to-register sites; 0: the keep-prefix LAT-4/LAT-5 adder
    parameter integer EXP6  = 0,         // 1: the exp units' adds on the six-cut f12 adder too (ot_dsrom_su_softmax_exp6,
                                         // add latency 6; ELA unused)
    parameter integer EXPNS = 0,         // 1 (with EXP6): the exp's n = rint(t) over two stages (+1 cycle an exp)
    parameter integer DENK  = 0,         // 1: the per-lane den copies on reset flops, a cell type the output register den_d
                                         //    does not share, so synthesis cannot merge them into it (x6u30: den_d fanned
                                         //    out to every lane's divider, -55 ps at CTS)
    parameter integer DIVF12 = 1,        // 1: ot_dsrom_su_fdiv_f12 (DEPTH 33, 1.2 GHz); 0: ot_hdc_v41x_fdiv (19)
    parameter integer MARGIN = 0,        // 1: the margin build (header)
    parameter integer RECUT  = 0,        // 1: the exp units on the re-cut multiplier / adder (ELM must be 11): +2 cuts each
    parameter integer SAFE   = 0         // 3: exp units and dividers on half-rate clock-gated cores (2 * depth + 1 cycles); 1: exp units and dividers as tiles with registered inputs (+1 cycle each; needs EXP6 and DIVF12); 2: and the divider's steps in two stages (+29 cycles)
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [6:0]           nv,          // score vectors a head
    input  wire [2:0]           lt,          // ceil(log2 nv)
    input  wire [31:0]          scale,
    input  wire [H*32-1:0]      sink,
    input  wire [16*TAIL-1:0]   cosv,        // TAIL/2 pairs, binary32
    input  wire [16*TAIL-1:0]   sinv,
    input  wire                 s_v,
    input  wire [H*LPH*32-1:0]  s_d,
    output wire                 e_v,
    output wire [H*LPH*32-1:0]  e_d,
    output reg                  mx_v,        // row maxima at the root
    output reg  [H*32-1:0]      mx_d,
    output reg                  es_v,        // row sums at the root
    output reg  [H*32-1:0]      es_d,
    output reg                  den_v,       // denominators at the lanes (after RWD)
    output reg  [H*32-1:0]      den_d,
    input  wire                 pv_v,
    input  wire [H*LPH*32-1:0]  pv_d,
    output wire                 o_v,
    output wire [H*LPH*16-1:0]  o_d,
    output wire                 fault
);
    localparam integer LA_T = (ADD6 == 2) ? 9 : ADD6 ? 6 : LA;     // the add latency the pipeline is built around
    localparam integer NL = H * LPH;
    localparam integer CPV = LPH / 8;            // chunks a vector
    localparam integer LVI = $clog2(CPV);        // in-vector tree levels
    localparam integer NPV = 512 / LPH;
    localparam integer LH = $clog2(LPH);
    localparam integer ELA_T = EXP6 ? (RECUT ? 11 : ((ADD6 == 2) ? 9 : 6)) : ELA;    // the exp's add latency
    localparam integer D_EXP_CORE = 7 * ELM + 8 * ELA_T + 4 + (EXP6 ? EXPNS + ((EXPNS == 2) ? 1 : 0) : 0);
    localparam integer D_EXP = (SAFE == 3) ? 2 * D_EXP_CORE + 1 : D_EXP_CORE + ((SAFE != 0) ? 1 : 0);   // SAFE 3: half-rate cores
    localparam integer NRD = (SAFE == 2) ? 2 : MARGIN;     // SAFE 2: the divider's steps in two stages (62 deep)
    localparam integer D_DIV_CORE = (DIVF12 ? 33 + ((NRD != 0) ? 1 : 0) + ((NRD == 2) ? 28 : 0) : 19);
    localparam integer D_DIV = (SAFE == 3) ? 2 * D_DIV_CORE + 1 : D_DIV_CORE + ((SAFE != 0) ? 1 : 0);
    // configuration inputs: registered at the pin in the margin build
    wire [6:0]         nv_i;
    wire [2:0]         lt_i;
    wire [31:0]        scale_i;
    wire [H*32-1:0]    sink_i;
    wire [16*TAIL-1:0] cos_i, sin_i;
    generate if (MARGIN) begin : g_cin
        reg [6:0] nv_r; reg [2:0] lt_r; reg [31:0] scale_r; reg [H*32-1:0] sink_r; reg [16*TAIL-1:0] cos_r, sin_r;
        always @(posedge clk) begin
            nv_r <= nv; lt_r <= lt; scale_r <= scale; sink_r <= sink; cos_r <= cosv; sin_r <= sinv;
        end
        assign nv_i = nv_r; assign lt_i = lt_r; assign scale_i = scale_r; assign sink_i = sink_r;
        assign cos_i = cos_r; assign sin_i = sin_r;
    end else begin : g_cw
        assign nv_i = nv; assign lt_i = lt; assign scale_i = scale; assign sink_i = sink;
        assign cos_i = cosv; assign sin_i = sinv;
    end endgenerate

    function automatic [31:0] okey(input [31:0] x);
        okey = x[31] ? ~x : {1'b1, x[30:0]};
    endfunction
    function automatic [31:0] fmax(input [31:0] a, input [31:0] b);
        fmax = (okey(a) >= okey(b)) ? a : b;
    endfunction
    function automatic [15:0] bf16(input [31:0] x);
        bf16 = x[31:16] + {15'd0, x[15] & (x[16] | (|x[14:0]))};
    endfunction
    genvar l, h, k;
    integer i;

    // =================================================================================================
    // A. scores in (DIN) -> s = s_raw * scale -> buffer; per-lane running max; per-head tree; RWU -> root
    // =================================================================================================
    wire [DIN:0] siv;
    ot_hdc_vline #(.D(DIN)) u_siv (.clk(clk), .rst_n(rst_n), .v(s_v), .vd(siv));
    wire [NL*32-1:0] s_in;
    ot_hdc_delay #(.W(NL*32), .D(DIN)) u_sid (.clk(clk), .rst_n(rst_n), .d(s_d), .q(s_in));
    wire [LM:0] smv;
    ot_hdc_vline #(.D(LM)) u_smv (.clk(clk), .rst_n(rst_n), .v(siv[DIN]), .vd(smv));
    wire [NL*32-1:0] s_m;
    reg  [NL*32-1:0] sbuf [0:NVMAX-1];
    reg  [NL*32-1:0] rmax;
    reg  [6:0]       wcnt;
    reg              a_done;                     // the lanes' maxima are final this cycle
    generate for (l = 0; l < NL; l = l + 1) begin : g_sm
        wire fm;
        ot_dsrom_su_softmax_mul #(LM) u_m (clk, rst_n, siv[DIN], s_in[32*l +: 32], scale_i, s_m[32*l +: 32], fm);
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin wcnt <= 7'd0; a_done <= 1'b0; end
        else begin
            a_done <= s_mlast;
            if (smv[LM]) wcnt <= (wcnt + 7'd1 == nv_i) ? 7'd0 : wcnt + 7'd1;
        end
    end
    always @(posedge clk) if (smv[LM]) sbuf[wcnt] <= s_m;
    // running max per lane: s and the "first vector" / valid flags re-registered at the lane (kept copies: the
    // control fans out to one lane's flops only), then ONE keep-prefix ordered-key compare and a select (a
    // recurrence: one cycle)
    reg              s_mv;                       // valid of s_q (feeds a_done)
    reg              s_mlast;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s_mv <= 1'b0; s_mlast <= 1'b0; end
        else begin s_mv <= smv[LM]; s_mlast <= smv[LM] && (wcnt + 7'd1 == nv_i); end
    end
    wire [NL*32-1:0] mx0;                        // the lanes' row maxima (tree level 0)
    wire             mx0_v;
    generate if (MARGIN) begin : g_rmm
        // two interleaved accumulators a lane (even / odd vectors), each a two-cycle compare | select recurrence;
        // max on ordered keys is order free, so the merge after the row gives the same maximum
        reg [NL*32-1:0] rma, rmb, mga, mgb, mgo;
        reg nv1;                                 // a one-vector row: the odd accumulator holds nothing
        always @(posedge clk) nv1 <= (nv_i == 7'd1);
        for (l = 0; l < NL; l = l + 1) begin : g_rm
            (* keep *) reg fa_v, fa_f, fb_v, fb_f;   // stage 1: lane copies of the accumulator's valid / first
            (* keep *) reg ga_v, ga_f, gb_v, gb_f;   // stage 2
            reg  [31:0] s_q, s_q2;
            reg         gea, geb;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    fa_v <= 1'b0; fa_f <= 1'b0; fb_v <= 1'b0; fb_f <= 1'b0;
                    ga_v <= 1'b0; ga_f <= 1'b0; gb_v <= 1'b0; gb_f <= 1'b0;
                end else begin
                    fa_v <= smv[LM] && !wcnt[0]; fa_f <= (wcnt == 7'd0);
                    fb_v <= smv[LM] && wcnt[0];  fb_f <= (wcnt == 7'd1);
                    ga_v <= fa_v; ga_f <= fa_f; gb_v <= fb_v; gb_f <= fb_f;
                end
            end
            wire ca, cb;
            ot_hdc_kge #(.W(32), .K(1)) u_ga (.a(okey(rma[32*l +: 32])), .b(okey(s_q)), .ge(ca));
            ot_hdc_kge #(.W(32), .K(1)) u_gb (.a(okey(rmb[32*l +: 32])), .b(okey(s_q)), .ge(cb));
            always @(posedge clk) begin
                s_q <= s_m[32*l +: 32];
                s_q2 <= s_q;
                gea <= ca;
                geb <= cb;
            end
            always @(posedge clk) begin
                if (ga_v) rma[32*l +: 32] <= (ga_f || !gea) ? s_q2 : rma[32*l +: 32];
                if (gb_v) rmb[32*l +: 32] <= (gb_f || !geb) ? s_q2 : rmb[32*l +: 32];
            end
            // merge: compare | select
            wire cm;
            ot_hdc_kge #(.W(32), .K(1)) u_gm (.a(okey(rma[32*l +: 32])), .b(okey(rmb[32*l +: 32])), .ge(cm));
            reg gem;
            always @(posedge clk) begin
                mga[32*l +: 32] <= rma[32*l +: 32];
                mgb[32*l +: 32] <= rmb[32*l +: 32];
                gem <= cm;
                mgo[32*l +: 32] <= (nv1 || gem) ? mga[32*l +: 32] : mgb[32*l +: 32];
            end
        end
        // the last vector's s_q is visible with s_mlast: accumulators final 2 cycles later, merged 2 after that
        wire [4:0] adv;
        ot_hdc_vline #(.D(4)) u_adv (.clk(clk), .rst_n(rst_n), .v(s_mlast), .vd(adv));
        assign mx0 = mgo;
        assign mx0_v = adv[4];
    end else begin : g_rm1
        for (l = 0; l < NL; l = l + 1) begin : g_rm
            (* keep *) reg        fv, ff;            // lane copies: s_q valid, s_q is the row's first vector
            reg  [31:0] s_q;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin fv <= 1'b0; ff <= 1'b0; end
                else begin fv <= smv[LM]; ff <= (wcnt == 7'd0); end
            end
            always @(posedge clk) s_q <= s_m[32*l +: 32];
            wire ge;
            ot_hdc_kge #(.W(32), .K(1)) u_ge (.a(okey(rmax[32*l +: 32])), .b(okey(s_q)), .ge(ge));
            always @(posedge clk) if (fv) rmax[32*l +: 32] <= (ff || !ge) ? s_q : rmax[32*l +: 32];
        end
        assign mx0 = rmax;
        assign mx0_v = a_done;
    end endgenerate
    // per-head max tree: LH registered levels of pairwise max (order free: max on ordered keys); the margin build
    // splits each level into compare | select
    generate for (k = 0; k <= LH; k = k + 1) begin : g_mt
        wire [(NL >> k)*32-1:0] x;
        wire                    v;
        if (k == 0) begin : g_0
            assign x = mx0;
            assign v = mx0_v;
        end else begin : g_n
            reg [(NL >> k)*32-1:0] xr;
            reg                    vr;
            for (l = 0; l < (NL >> k); l = l + 1) begin : g_l
                wire [31:0] xa = g_mt[k-1].x[64*l +: 32], xb = g_mt[k-1].x[64*l + 32 +: 32];
                wire ge;
                ot_hdc_kge #(.W(32), .K(1)) u_ge (.a(okey(xa)), .b(okey(xb)), .ge(ge));
                if (MARGIN) begin : g_s
                    reg [31:0] ra, rb;
                    reg        rg;
                    always @(posedge clk) begin ra <= xa; rb <= xb; rg <= ge; end
                    always @(posedge clk) xr[32*l +: 32] <= rg ? ra : rb;
                end else begin : g_c
                    always @(posedge clk) xr[32*l +: 32] <= ge ? xa : xb;
                end
            end
            if (MARGIN) begin : g_sv
                reg vr0;
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) begin vr0 <= 1'b0; vr <= 1'b0; end else begin vr0 <= g_mt[k-1].v; vr <= vr0; end
            end else begin : g_cv
                always @(posedge clk or negedge rst_n) if (!rst_n) vr <= 1'b0; else vr <= g_mt[k-1].v;
            end
            assign x = xr;
            assign v = vr;
        end
    end endgenerate
    wire [H*32-1:0] mx_root = g_mt[LH].x;        // head h's max at the tree's root
    wire [H*32-1:0] mx_up;
    wire [RWU:0]    mxuv;
    ot_hdc_vline #(.D(RWU)) u_mxuv (.clk(clk), .rst_n(rst_n), .v(g_mt[LH].v), .vd(mxuv));
    ot_hdc_delay #(.W(H*32), .D(RWU)) u_mxu (.clk(clk), .rst_n(rst_n), .d(mx_root), .q(mx_up));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) mx_v <= 1'b0; else mx_v <= mxuv[RWU];
    end
    always @(posedge clk) if (mxuv[RWU]) mx_d <= mx_up;
    // the sink terms at the root: exp(sink + (-mb)), beside the row sum
    wire [LA_T+D_EXP:0] skv;
    ot_hdc_vline #(.D(LA_T + D_EXP)) u_skv (.clk(clk), .rst_n(rst_n), .v(mx_v), .vd(skv));
    wire [H*32-1:0] sk_d, sk_e;
    reg  [H*32-1:0] sk_hold;
    generate for (h = 0; h < H; h = h + 1) begin : g_sk
        wire fa, fe;
        ot_dsrom_su_softmax_add #(.ADD6(ADD6), .LA(LA)) u_a
            (clk, rst_n, mx_v, sink_i[32*h +: 32], {~mx_d[32*h + 31], mx_d[32*h +: 31]}, sk_d[32*h +: 32], fa);
        if (EXP6 && SAFE == 3) begin : g_xh
            ot_dsrom_su_softmax_exp_hr #(.LM(ELM), .LA(ELA_T), .NSPLIT(EXPNS)) u_e (.clk(clk), .rst_n(rst_n), .v(skv[LA_T]), .x(sk_d[32*h +: 32]),
                                                 .y(sk_e[32*h +: 32]), .vo(), .fault(fe));
        end else if (EXP6 && SAFE) begin : g_xt
            ot_dsrom_su_softmax_exp_tile #(.LM(ELM), .LA(ELA_T), .NSPLIT(EXPNS), .ADDX(RECUT == 2)) u_e (.clk(clk), .rst_n(rst_n), .v(skv[LA_T]), .x(sk_d[32*h +: 32]),
                                                 .y(sk_e[32*h +: 32]), .vo(), .fault(fe));
        end else if (EXP6) begin : g_x6
            ot_dsrom_su_softmax_exp6 #(.LM(ELM), .LA(ELA_T), .NSPLIT(EXPNS), .ADDX(RECUT == 2)) u_e (.clk(clk), .rst_n(rst_n), .v(skv[LA_T]), .x(sk_d[32*h +: 32]),
                                                 .y(sk_e[32*h +: 32]), .vo(), .fault(fe));
        end else begin : g_x
            ot_hdc_v41x_exp #(.LM(ELM), .LA(ELA)) u_e (.clk(clk), .rst_n(rst_n), .v(skv[LA_T]), .x(sk_d[32*h +: 32]),
                                                 .y(sk_e[32*h +: 32]), .vo(), .fault(fe));
        end
    end endgenerate
    always @(posedge clk) if (skv[LA_T + D_EXP]) sk_hold <= sk_e;
    // the maxima back to the lanes
    wire [H*32-1:0] mx_dn;
    wire [RWD:0]    mxdv;
    ot_hdc_vline #(.D(RWD)) u_mxdv (.clk(clk), .rst_n(rst_n), .v(mx_v), .vd(mxdv));
    ot_hdc_delay #(.W(H*32), .D(RWD)) u_mxd (.clk(clk), .rst_n(rst_n), .d(mx_d), .q(mx_dn));

    // =================================================================================================
    // B. re-read s, e = exp(s + (-mb)) -> out (DOUT) and to the row sum
    // =================================================================================================
    reg  [6:0]       rcnt;
    reg              rd_on, rv, rlast;
    reg  [NL*32-1:0] s_rd;
    (* keep *) reg [NL*32-1:0] mbn;              // -max of the lane's head, a leaf register per lane (kept: the
                                                 // copies must survive synthesis, each drives one lane's adder)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rd_on <= 1'b0; rcnt <= 7'd0; rv <= 1'b0; rlast <= 1'b0; end
        else begin
            rv <= rd_on;
            rlast <= rd_on && (rcnt + 7'd1 == nv_i);
            if (mxdv[RWD]) begin rd_on <= 1'b1; rcnt <= 7'd0; end
            else if (rd_on) begin
                rcnt <= rcnt + 7'd1;
                if (rcnt + 7'd1 == nv_i) rd_on <= 1'b0;
            end
        end
    end
    always @(posedge clk) begin
        if (rd_on) s_rd <= sbuf[rcnt];
    end
    wire [LA_T+D_EXP:0] bv, blast;
    ot_hdc_vline #(.D(LA_T + D_EXP)) u_bv (.clk(clk), .rst_n(rst_n), .v(rv), .vd(bv));
    ot_hdc_vline #(.D(LA_T + D_EXP)) u_bl (.clk(clk), .rst_n(rst_n), .v(rlast), .vd(blast));
    wire [NL*32-1:0] bd, be;
    generate for (l = 0; l < NL; l = l + 1) begin : g_b
        localparam integer HH = l / LPH;
        wire fa, fe;
        always @(posedge clk) if (mxdv[RWD]) mbn[32*l +: 32] <= {~mx_dn[32*HH + 31], mx_dn[32*HH +: 31]};
        ot_dsrom_su_softmax_add #(.ADD6(ADD6), .LA(LA)) u_a
            (clk, rst_n, rv, s_rd[32*l +: 32], mbn[32*l +: 32], bd[32*l +: 32], fa);
        if (EXP6 && SAFE == 3) begin : g_xh
            ot_dsrom_su_softmax_exp_hr #(.LM(ELM), .LA(ELA_T), .NSPLIT(EXPNS)) u_e (.clk(clk), .rst_n(rst_n), .v(bv[LA_T]), .x(bd[32*l +: 32]),
                                                 .y(be[32*l +: 32]), .vo(), .fault(fe));
        end else if (EXP6 && SAFE) begin : g_xt
            ot_dsrom_su_softmax_exp_tile #(.LM(ELM), .LA(ELA_T), .NSPLIT(EXPNS), .ADDX(RECUT == 2)) u_e (.clk(clk), .rst_n(rst_n), .v(bv[LA_T]), .x(bd[32*l +: 32]),
                                                 .y(be[32*l +: 32]), .vo(), .fault(fe));
        end else if (EXP6) begin : g_x6
            ot_dsrom_su_softmax_exp6 #(.LM(ELM), .LA(ELA_T), .NSPLIT(EXPNS), .ADDX(RECUT == 2)) u_e (.clk(clk), .rst_n(rst_n), .v(bv[LA_T]), .x(bd[32*l +: 32]),
                                                 .y(be[32*l +: 32]), .vo(), .fault(fe));
        end else begin : g_x
            ot_hdc_v41x_exp #(.LM(ELM), .LA(ELA)) u_e (.clk(clk), .rst_n(rst_n), .v(bv[LA_T]), .x(bd[32*l +: 32]),
                                                 .y(be[32*l +: 32]), .vo(), .fault(fe));
        end
    end endgenerate
    wire e_at = bv[LA_T + D_EXP];
    wire e_last = blast[LA_T + D_EXP];
    wire [DOUT:0] eov;
    ot_hdc_vline #(.D(DOUT)) u_eov (.clk(clk), .rst_n(rst_n), .v(e_at), .vd(eov));
    ot_hdc_delay #(.W(NL*32), .D(DOUT)) u_eod (.clk(clk), .rst_n(rst_n), .d(be), .q(e_d));
    assign e_v = eov[DOUT];

    // =================================================================================================
    // C. row sum: chunk chains (7 adds), in-vector tree, streaming time levels; RWU; den at the root; RWD
    // =================================================================================================
    // chunk chain: acc0 = x0 (-0 -> +0: the golden's +0 + x0), acc_j = acc_{j-1} + x_j
    wire [7*LA_T:0] cv, cl;
    ot_hdc_vline #(.D(7 * LA_T)) u_cv (.clk(clk), .rst_n(rst_n), .v(e_at), .vd(cv));
    ot_hdc_vline #(.D(7 * LA_T)) u_cl (.clk(clk), .rst_n(rst_n), .v(e_last), .vd(cl));
    wire [NL/8*32-1:0] csum_o;
    generate for (k = 0; k < NL / 8; k = k + 1) begin : g_ch
        wire [32*8-1:0] acc;
        wire [31:0] x0 = be[32*(8*k) +: 32];
        assign acc[31:0] = (x0 == 32'h80000000) ? 32'd0 : x0;
        genvar j;
        for (j = 1; j < 8; j = j + 1) begin : g_j
            wire [31:0] xj;
            wire fa;
            ot_hdc_delay #(.W(32), .D(LA_T * (j - 1))) u_xd (.clk(clk), .rst_n(rst_n), .d(be[32*(8*k+j) +: 32]), .q(xj));
            ot_dsrom_su_softmax_add #(.ADD6(ADD6), .LA(LA)) u_a
                (clk, rst_n, cv[LA_T*(j-1)], acc[32*(j-1) +: 32], xj, acc[32*j +: 32], fa);
        end
        assign csum_o[32*k +: 32] = acc[32*7 +: 32];
    end endgenerate
    // in-vector tree: LVI levels over each head's CPV chunk sums
    wire [LA_T*LVI:0] vtv, vtl;
    ot_hdc_vline #(.D(LA_T * LVI)) u_vtv (.clk(clk), .rst_n(rst_n), .v(cv[7*LA_T]), .vd(vtv));
    ot_hdc_vline #(.D(LA_T * LVI)) u_vtl (.clk(clk), .rst_n(rst_n), .v(cl[7*LA_T]), .vd(vtl));
    generate for (k = 0; k <= LVI; k = k + 1) begin : g_vt
        wire [((NL / 8) >> k)*32-1:0] x;
        if (k == 0) begin : g_0
            assign x = csum_o;
        end else begin : g_n
            for (l = 0; l < ((NL / 8) >> k); l = l + 1) begin : g_l
                wire fa;
                ot_dsrom_su_softmax_add #(.ADD6(ADD6), .LA(LA)) u_a
                    (clk, rst_n, vtv[LA_T*(k-1)], g_vt[k-1].x[64*l +: 32], g_vt[k-1].x[64*l + 32 +: 32],
                     x[32*l +: 32], fa);
            end
        end
    end endgenerate
    wire [H*32-1:0] vsum = g_vt[LVI].x;          // head h's vector sum
    wire            vs_v = vtv[LA_T*LVI];
    wire            vs_l = vtl[LA_T*LVI];
    // time levels: level t input (v, l, x); output after LA_T (add or pass)
    wire [(LTMAX+1)*H*32-1:0] tl_x;
    wire [LTMAX:0]            tl_v, tl_l;
    assign tl_x[H*32-1:0] = vsum;
    assign tl_v[0] = vs_v;
    assign tl_l[0] = vs_l;
    generate for (k = 0; k < LTMAX; k = k + 1) begin : g_tl
        wire [H*32-1:0] xi = tl_x[k*H*32 +: H*32];
        wire vi = tl_v[k], li = tl_l[k];
        reg  [H*32-1:0] held;
        reg             par;
        wire comb = vi && par;                   // odd item: combine with the held left operand
        wire pass = vi && !par && li;            // even and last: its sibling is +0 padding
        wire [LA_T:0] ov, ol, op;
        ot_hdc_vline #(.D(LA_T)) u_ov (.clk(clk), .rst_n(rst_n), .v(comb || pass), .vd(ov));
        ot_hdc_vline #(.D(LA_T)) u_ol (.clk(clk), .rst_n(rst_n), .v((comb || pass) && li), .vd(ol));
        ot_hdc_vline #(.D(LA_T)) u_op (.clk(clk), .rst_n(rst_n), .v(pass), .vd(op));
        wire [H*32-1:0] sum, pd;
        for (l = 0; l < H; l = l + 1) begin : g_h
            wire fa;
            ot_dsrom_su_softmax_add #(.ADD6(ADD6), .LA(LA)) u_a
                (clk, rst_n, comb, held[32*l +: 32], xi[32*l +: 32], sum[32*l +: 32], fa);
        end
        ot_hdc_delay #(.W(H*32), .D(LA_T)) u_pd (.clk(clk), .rst_n(rst_n), .d(xi), .q(pd));
        // the level's output is registered (pass / add select off the next level's adder input path): LA_T + 1
        reg  [H*32-1:0] xo;
        reg             vo_r, lo_r;
        always @(posedge clk) xo <= op[LA_T] ? pd : sum;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin vo_r <= 1'b0; lo_r <= 1'b0; end
            else begin vo_r <= ov[LA_T]; lo_r <= ol[LA_T]; end
        end
        assign tl_x[(k+1)*H*32 +: H*32] = xo;
        assign tl_v[k+1] = vo_r;
        assign tl_l[k+1] = lo_r;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) par <= 1'b0;
            else if (vi) par <= li ? 1'b0 : ~par;
        end
        always @(posedge clk) if (vi && !par) held <= xi;
    end endgenerate
    // tap at level lt: the item carrying the last flag
    reg  [H*32-1:0] rs_x;
    reg             rs_v;
    wire            tap = tl_v[lt_i] && tl_l[lt_i];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) rs_v <= 1'b0; else rs_v <= tap;
    end
    always @(posedge clk) if (tap) rs_x <= tl_x[lt_i*H*32 +: H*32];
    wire [H*32-1:0] es_up;
    wire [RWU:0]    esuv;
    ot_hdc_vline #(.D(RWU)) u_esuv (.clk(clk), .rst_n(rst_n), .v(rs_v), .vd(esuv));
    ot_hdc_delay #(.W(H*32), .D(RWU)) u_esu (.clk(clk), .rst_n(rst_n), .d(rs_x), .q(es_up));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) es_v <= 1'b0; else es_v <= esuv[RWU];
    end
    always @(posedge clk) if (esuv[RWU]) es_d <= es_up;
    // den = es + exp(sink - mb) at the root, then RWD to the lanes
    wire [LA_T:0]     dnv;
    wire [H*32-1:0] den_r;
    ot_hdc_vline #(.D(LA_T)) u_dnv (.clk(clk), .rst_n(rst_n), .v(es_v), .vd(dnv));
    generate for (h = 0; h < H; h = h + 1) begin : g_dn
        wire fa;
        ot_dsrom_su_softmax_add #(.ADD6(ADD6), .LA(LA)) u_a
            (clk, rst_n, es_v, es_d[32*h +: 32], sk_hold[32*h +: 32], den_r[32*h +: 32], fa);
    end endgenerate
    wire [H*32-1:0] den_dn;
    wire [RWD:0]    dndv;
    ot_hdc_vline #(.D(RWD)) u_dndv (.clk(clk), .rst_n(rst_n), .v(dnv[LA_T]), .vd(dndv));
    ot_hdc_delay #(.W(H*32), .D(RWD)) u_dnd (.clk(clk), .rst_n(rst_n), .d(den_r), .q(den_dn));
    // the margin build loads the lanes one cycle later (a lane-local registered enable and value), and reports den
    // one cycle later to match
    wire [H*32-1:0] den_rp;
    wire            den_vp;
    generate if (MARGIN) begin : g_dvm
        reg [H*32-1:0] dd; reg dv1;
        always @(posedge clk) dd <= den_dn;
        always @(posedge clk or negedge rst_n) if (!rst_n) dv1 <= 1'b0; else dv1 <= dndv[RWD];
        assign den_rp = dd; assign den_vp = dv1;
    end else begin : g_dv1
        assign den_rp = den_dn; assign den_vp = dndv[RWD];
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) den_v <= 1'b0; else den_v <= den_vp;
    end
    always @(posedge clk) if (den_vp) den_d <= den_rp;
    (* keep *) reg [NL*32-1:0] denl;             // den of the lane's head, a leaf register per lane (kept)
    generate for (l = 0; l < NL; l = l + 1) begin : g_dl
        if (MARGIN) begin : g_m
            (* keep *) reg        le;            // lane copies of the load enable and the head's den
            (* keep *) reg [31:0] lv;
            always @(posedge clk or negedge rst_n) if (!rst_n) le <= 1'b0; else le <= dndv[RWD];
            always @(posedge clk) lv <= den_dn[32*(l / LPH) +: 32];
            always @(posedge clk or negedge rst_n)
                if (!rst_n) denl[32*l +: 32] <= 32'd0;
                else if (le) denl[32*l +: 32] <= lv;
        end else if (DENK) begin : g_k
            always @(posedge clk or negedge rst_n)
                if (!rst_n) denl[32*l +: 32] <= 32'd0;
                else if (dndv[RWD]) denl[32*l +: 32] <= den_dn[32*(l / LPH) +: 32];
        end else begin : g_p
            always @(posedge clk) if (dndv[RWD]) denl[32*l +: 32] <= den_dn[32*(l / LPH) +: 32];
        end
    end endgenerate

    // =================================================================================================
    // D. pv in (DIN) -> pv / den -> BF16 -> inverse RoPE on the tail (BF16) -> out (DOUT)
    // =================================================================================================
    wire [DIN:0] piv;
    ot_hdc_vline #(.D(DIN)) u_piv (.clk(clk), .rst_n(rst_n), .v(pv_v), .vd(piv));
    wire [NL*32-1:0] pv_in;
    ot_hdc_delay #(.W(NL*32), .D(DIN)) u_pid (.clk(clk), .rst_n(rst_n), .d(pv_d), .q(pv_in));
    reg  [6:0] ucnt;                             // PV vector index at the divider input
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ucnt <= 7'd0;
        else if (piv[DIN]) ucnt <= (ucnt + 7'd1 == NPV) ? 7'd0 : ucnt + 7'd1;
    end
    localparam integer DR = D_DIV + 1 + LM + LA_T + 1;     // divide, BF16, mul, add, BF16
    wire [DR:0] dv;
    ot_hdc_vline #(.D(DR)) u_dv (.clk(clk), .rst_n(rst_n), .v(piv[DIN]), .vd(dv));
    wire [6:0] u_q, u_r;                         // vector index at the divide output / at its BF16 register
    ot_hdc_delay #(.W(7), .D(D_DIV)) u_ul (.clk(clk), .rst_n(rst_n), .d(ucnt), .q(u_q));
    ot_hdc_delay #(.W(7), .D(1)) u_ul1 (.clk(clk), .rst_n(rst_n), .d(u_q), .q(u_r));
    wire [NL*32-1:0] qd;
    reg  [NL*16-1:0] o0;                          // bf16(pv / den)
    generate for (l = 0; l < NL; l = l + 1) begin : g_dv
        localparam integer HH = l / LPH;
        wire fd;
        if (DIVF12 && SAFE == 3) begin : g_fh
            ot_dsrom_su_fdiv_hr #(.NR(NRD)) u_d (.clk(clk), .rst_n(rst_n), .v(piv[DIN]), .a(pv_in[32*l +: 32]),
                                      .b(denl[32*l +: 32]), .y(qd[32*l +: 32]), .vo(), .fault(fd));
        end else if (DIVF12 && SAFE) begin : g_ft
            ot_dsrom_su_fdiv_tile #(.NR(NRD)) u_d (.clk(clk), .rst_n(rst_n), .v(piv[DIN]), .a(pv_in[32*l +: 32]),
                                      .b(denl[32*l +: 32]), .y(qd[32*l +: 32]), .vo(), .fault(fd));
        end else if (DIVF12) begin : g_f12
            ot_dsrom_su_fdiv_f12 #(.NR(MARGIN)) u_d (.clk(clk), .rst_n(rst_n), .v(piv[DIN]), .a(pv_in[32*l +: 32]),
                                      .b(denl[32*l +: 32]), .y(qd[32*l +: 32]), .vo(), .fault(fd));
        end else begin : g_f19
            ot_hdc_v41x_fdiv u_d (.clk(clk), .rst_n(rst_n), .v(piv[DIN]), .a(pv_in[32*l +: 32]), .b(denl[32*l +: 32]),
                                  .y(qd[32*l +: 32]), .vo(), .fault(fd));
        end
        wire [15:0] qb;                          // BF16 RNE (keep-prefix increment)
        ot_hdc_kinc #(.W(16), .K(1)) u_bf (.a(qd[32*l + 16 +: 16]),
                                           .inc(qd[32*l + 15] & (qd[32*l + 16] | (|qd[32*l +: 15]))), .y(qb));
        always @(posedge clk) o0[16*l +: 16] <= qb;
    end endgenerate
    // RoPE: lane j of a tail vector, element p = u*LPH + j, pair i = (p - (512 - TAIL)) / 2
    wire [NL*16-1:0] o0_d;
    ot_hdc_delay #(.W(NL*16), .D(LM + LA_T)) u_o0d (.clk(clk), .rst_n(rst_n), .d(o0), .q(o0_d));
    wire [6:0] u_rd;
    ot_hdc_delay #(.W(7), .D(LM + LA_T)) u_urd (.clk(clk), .rst_n(rst_n), .d(u_r), .q(u_rd));
    // the margin build's lane copies start two cycles ahead: u_q2 = u_q two cycles early, u_rd2 = u_rd two early
    wire [6:0] u_q2, u_rd2;
    ot_hdc_delay #(.W(7), .D(D_DIV - 2)) u_uq2 (.clk(clk), .rst_n(rst_n), .d(ucnt), .q(u_q2));
    ot_hdc_delay #(.W(7), .D(LM + LA_T - 1)) u_urd2 (.clk(clk), .rst_n(rst_n), .d(u_q), .q(u_rd2));
    reg  [NL*16-1:0] ob;
    generate for (l = 0; l < NL; l = l + 1) begin : g_rp
        localparam integer J = l % LPH;
        localparam integer HB = (l / LPH) * LPH;
        wire [31:0] a = {o0[16*(HB + (J & ~1)) +: 16], 16'd0};
        wire [31:0] b = {o0[16*(HB + (J | 1)) +: 16], 16'd0};
        // the pair's cos / sin, selected a cycle ahead (from the divide-output index) into lane registers; the margin
        // build registers a lane copy of the index two cycles ahead and the pair index one cycle ahead
        reg  [31:0] c, s;
        wire        tail;
        if (MARGIN) begin : g_ix
            (* keep *) reg [6:0] ul, rl;
            reg [4:0] pr;
            reg       tr;
            wire [8:0] pidx = ({2'd0, ul} * LPH + J - (512 - TAIL)) >> 1;
            always @(posedge clk) begin
                ul <= u_q2;
                pr <= pidx[4:0];
                c <= cos_i[32*pr +: 32];
                s <= sin_i[32*pr +: 32];
                rl <= u_rd2;
                tr <= ({2'd0, rl} * LPH + J) >= (512 - TAIL);
            end
            assign tail = tr;
        end else begin : g_ix1
            wire [8:0]  pidx = ({2'd0, u_q} * LPH + J - (512 - TAIL)) >> 1;
            always @(posedge clk) begin
                c <= cos_i[32*pidx[4:0] +: 32];
                s <= sin_i[32*pidx[4:0] +: 32];
            end
            assign tail = ({2'd0, u_rd} * LPH + J) >= (512 - TAIL);
        end
        wire [31:0] m1, m2, ad;
        wire f1, f2, f3;
        // even lane: a*c + b*s; odd lane: b*c + -(a*s)
        ot_dsrom_su_softmax_mul #(LM) u_m1 (clk, rst_n, dv[D_DIV + 1], (J % 2 == 0) ? a : b, c, m1, f1);
        ot_dsrom_su_softmax_mul #(LM) u_m2 (clk, rst_n, dv[D_DIV + 1], (J % 2 == 0) ? b : a, s, m2, f2);
        wire [31:0] m2s = (J % 2 == 0) ? m2 : {~m2[31], m2[30:0]};
        ot_dsrom_su_softmax_add #(.ADD6(ADD6), .LA(LA)) u_a
            (clk, rst_n, dv[D_DIV + 1 + LM], m1, m2s, ad, f3);
        wire [15:0] adb;
        ot_hdc_kinc #(.W(16), .K(1)) u_bf (.a(ad[31:16]), .inc(ad[15] & (ad[16] | (|ad[14:0]))), .y(adb));
        always @(posedge clk) ob[16*l +: 16] <= tail ? adb : o0_d[16*l +: 16];
    end endgenerate
    wire [DOUT:0] oov;
    ot_hdc_vline #(.D(DOUT)) u_oov (.clk(clk), .rst_n(rst_n), .v(dv[DR]), .vd(oov));
    ot_hdc_delay #(.W(NL*16), .D(DOUT)) u_ood (.clk(clk), .rst_n(rst_n), .d(ob), .q(o_d));
    assign o_v = oov[DOUT];

    assign fault = 1'b0;   // operands are in range (finite scores, den > 0); fault bits kept for debug benches
endmodule
