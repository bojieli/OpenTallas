`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Threshold SELECT of the V4.1 indexer: W-lane radix select + position-order
// compaction.  The latency replacement for ot_hdc_select on the index top-512.
//
// Semantics are tools/hdc_golden_v41.py `topk_lowest_index` emitted in
// ascending-index order (the indexer's `sorted(...)`): the k largest values,
// ties to the LOWER index, -0 equal to +0; NaN is outside the contract.  The
// selected (value, index) pairs leave in the order they arrived, which is
// ascending index, W lanes per beat, packed.
//
// Contract.  A segment arrives as beats of W lanes (`in_lv` marks the lanes
// that hold an element; any mask, an all-empty beat is legal) under
// valid/ready; `in_last` closes it and carries the runtime k (`in_k`, clamped
// to K; 0 selects nothing).  Indices must ASCEND in stream order (lane 0
// first, beat by beat).  Both uses satisfy it: the local level streams a die's
// index scores in position order, and the cross-die level streams the G local
// selections in die order when each die owns a contiguous position range --
// so the output of either level is already in position order and the
// ascending-index pass of ot_hdc_select disappears.  At most 2^AW beats per
// segment.  The segment is kept in a line memory outside the unit (one W-lane
// line per beat, synchronous read, one-cycle latency: mem_rdata holds the line
// addressed on the edge where mem_re was high, from the next edge on).
//
// Algorithm (value keys are the order-preserving unsigned VW-bit key of
// ot_hdc_select; hi = its top RB = VW/2 bits, lo = the rest):
//   ingest   every beat is written to the memory and its hi digits counted in
//            a 2^RB-bin histogram (W lanes per cycle);
//   walk 1   a registered segment tree over the bins; RB steps from the root,
//            each "does the right (higher) subtree still hold k?", give the
//            boundary bucket B, the count S strictly above it and the quota
//            m = k - S to take from bucket B;
//   pass 2   re-read the lines; lo digits of the elements in bucket B are
//            histogrammed; walk 2 with quota m gives the threshold key
//            T = {B, L} and the tie quota t (elements equal to T to take);
//   pass 3   re-read the lines: an element is selected when key > T, or key
//            == T and fewer than t equal keys precede it in stream order (a
//            prefix count across lanes plus a running remainder -- ties go to
//            the lower index); the selected lanes are compacted (log2 W
//            stages, each element moves left by the number of unselected
//            lanes before it, LSB first, collision free) and packed into W-lane
//            output beats through a rotate-and-accumulate stage.
// Exactness: the selected set is {key > T} U {the first t of key == T}, which
// is exactly the golden's lexicographic (value desc, index asc) top-k.
//
// Latency, in clock edges from the edge that accepts the last beat of a
// segment of NL beats to the edge that registers its `out_last` beat:
//   LAT = 2 NL + LAT0 (+1 when the final pass-3 beat overflows the partial
//   output line and the remainder takes one more beat),
//   LAT0 = 2 x (DRAIN 10 + 2 x RB 8 walk steps) + 5 + 2 ceil(log2(W) / 2)
//        = 63 at W = 64 (a walk step is two edges: mux register, then add/compare) (read, compare, tie prefix, select, shift counts,
//          3 compaction + 3 rotate register stages, output register).
// The next segment is accepted once pass 3 has issued its last read: in_ready
// is low for 2 NL + 52 edges after the last accept.  Area is linear in W
// (2^RB bins x W-lane popcounts, W log W compaction/rotate muxes) and
// independent of K and of the segment length (the lines are in the memory).
// Every segment emits at least one beat; the one with `out_last` may be empty.
// ---------------------------------------------------------------------------
module ot_hdc_tselect #(
    parameter integer W  = 64,        // lanes per beat (power of two)
    parameter integer VW = 16,        // value width (BF16; RB = VW/2 radix bits per pass)
    parameter integer IW = 16,        // index width
    parameter integer K  = 512,       // largest runtime k
    parameter integer AW = 10,        // line-address width: at most 2^AW beats per segment
    parameter integer KW = $clog2(K + 1)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              in_valid,
    output wire              in_ready,
    input  wire              in_last,
    input  wire [W-1:0]      in_lv,
    input  wire [W*VW-1:0]   in_val,
    input  wire [W*IW-1:0]   in_idx,
    input  wire [KW-1:0]     in_k,
    output reg               out_valid,
    output reg               out_last,
    output reg  [W-1:0]      out_lv,
    output reg  [W*VW-1:0]   out_val,
    output reg  [W*IW-1:0]   out_idx,
    output reg  [W-1:0]      out_ninf,
    // line memory (outside the unit)
    output wire              mem_we,
    output wire [AW-1:0]     mem_waddr,
    output wire [W*(1+VW+IW)-1:0] mem_wdata,
    output wire              mem_re,
    output wire [AW-1:0]     mem_raddr,
    input  wire [W*(1+VW+IW)-1:0] mem_rdata,
    output wire              busy
);
    localparam integer RB  = VW / 2;               // radix bits per pass
    localparam integer HA  = RB / 2;               // predecode split
    localparam integer NH  = 1 << HA;
    localparam integer NL0 = 1 << (RB - HA);
    localparam integer NB  = 1 << RB;              // histogram bins
    localparam integer LW  = $clog2(W);
    localparam integer CW  = AW + LW + 1;          // bin / tree count width
    localparam integer EW  = 1 + VW + IW;          // stored lane {lv, value, index}
    localparam integer PW  = 1 + VW + IW;          // payload {ninf, value, index}
    localparam integer QW  = (KW > LW + 1 ? KW : LW + 1) + 1;
    localparam integer DRAIN = 3 + RB - 1;         // histogram (3) + tree levels below level 1
    localparam integer CE  = 1 + LW + PW;          // compaction lane {v, z, payload}
    localparam integer RE  = 1 + PW;               // rotate lane {v, payload}
    localparam integer KQI = K;
    localparam [QW-1:0] KQ = KQI[QW-1:0];
    localparam integer RBM1I = RB - 1;
    localparam [3:0]    RBM1 = RBM1I[3:0];
    localparam [4:0]    DR = DRAIN[4:0];

    localparam [2:0] S_ING = 3'd0, S_W1 = 3'd1, S_P2 = 3'd2, S_W2 = 3'd3, S_P3 = 3'd4;

    function automatic [VW-1:0] fkey(input [VW-1:0] v);
        fkey = (v[VW-2:0] == 0) ? {1'b1, {(VW-1){1'b0}}} : v[VW-1] ? ~v : {1'b1, v[VW-2:0]};
    endfunction

    // -- control ---------------------------------------------------------------------
    reg  [2:0]    state;
    reg  [AW-1:0] wptr, nlast, rptr;
    reg  [QW-1:0] kq;                               // clamped runtime k (walk 1 quota)
    reg  [QW-1:0] mq;                               // bucket-B quota (walk 2 quota)
    reg  [QW-1:0] rem;                              // pass-3 tie quota still open
    reg  [RB-1:0] bsel, lsel;
    reg  [4:0]    dc;
    reg  [RB-1:0] wp;                               // walk node (heap index, top bit implied)
    reg  [3:0]    wstep;
    reg  [CW:0]   wacc;
    reg  [QW-1:0] wkq;
    reg           oflush;
    reg           pipe_busy;

    reg  [2:0]    init;                             // clear the bins for a few edges after reset
    assign in_ready = (state == S_ING) && (init == 0);
    wire acc_in = in_valid && in_ready;
    assign mem_we    = acc_in;
    assign mem_waddr = wptr;
    genvar gl;
    generate
        for (gl = 0; gl < W; gl = gl + 1) begin : g_wd
            assign mem_wdata[EW*gl +: EW] = {in_lv[gl], in_val[VW*gl +: VW], in_idx[IW*gl +: IW]};
        end
    endgenerate
    assign mem_re    = (state == S_P2) || (state == S_P3);
    assign mem_raddr = rptr;

    // -- ingest register -------------------------------------------------------------
    reg          s0_v;
    reg [W-1:0]  s0_lv;
    reg [W*VW-1:0] s0_val;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s0_v <= 1'b0;
        else s0_v <= acc_in;
    end
    always @(posedge clk) if (acc_in) begin s0_lv <= in_lv; s0_val <= in_val; end

    // read tags: the line in mem_rdata belongs to pass 2 / pass 3 and may be the last
    reg rv, rph3, rlast;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rv <= 1'b0; rph3 <= 1'b0; rlast <= 1'b0; end
        else begin rv <= mem_re; rph3 <= (state == S_P3); rlast <= mem_re && (rptr == nlast); end
    end

    // -- histogram: predecode, per-bin popcount, bins ----------------------------------
    reg [W*NH-1:0]  h1_hi;
    reg [W*NL0-1:0] h1_lo;
    wire hs_ing = s0_v;
    wire hs_p2  = rv && !rph3;
    wire [W*NH-1:0]  h1_hi_d;
    wire [W*NL0-1:0] h1_lo_d;
    generate
        for (gl = 0; gl < W; gl = gl + 1) begin : g_hpre
            wire [VW-1:0] v  = hs_ing ? s0_val[VW*gl +: VW] : mem_rdata[EW*gl + IW +: VW];
            wire [VW-1:0] k  = fkey(v);
            wire          e  = hs_ing ? s0_lv[gl] : (hs_p2 && mem_rdata[EW*gl + EW - 1] && k[VW-1 -: RB] == bsel);
            wire [RB-1:0] dg = hs_ing ? k[VW-1 -: RB] : k[RB-1:0];
            assign h1_hi_d[NH*gl +: NH]   = e ? ({{(NH-1){1'b0}}, 1'b1} << dg[RB-1 -: HA]) : {NH{1'b0}};
            assign h1_lo_d[NL0*gl +: NL0] = {{(NL0-1){1'b0}}, 1'b1} << dg[RB-HA-1:0];
        end
    endgenerate
    always @(posedge clk) begin h1_hi <= h1_hi_d; h1_lo <= h1_lo_d; end
    reg  [NB*(LW+1)-1:0] h2;
    wire [NB*(LW+1)-1:0] h2_d;
    genvar gb, gq;
    generate
        for (gb = 0; gb < NB; gb = gb + 1) begin : g_hcnt
            wire [W-1:0] x;
            for (gq = 0; gq < W; gq = gq + 1) begin : g_x
                assign x[gq] = h1_hi[NH*gq + (gb >> (RB - HA))] && h1_lo[NL0*gq + (gb % NL0)];
            end
            ot_hdc_tsel_popc #(.N(W), .OW(LW + 1)) u_pc (.x(x), .y(h2_d[(LW+1)*gb +: LW+1]));
        end
    endgenerate
    always @(posedge clk) h2 <= h2_d;
    integer l, b;
    wire hclr;
    reg [NB*CW-1:0] hb;                             // bins = tree leaves
    reg [NB*CW-1:0] tn;                             // internal nodes 1..NB-1
    wire [2*NB*CW-1:0] tv = {hb, tn};               // heap: node n at tv[CW*n +: CW]
    integer n;
    always @(posedge clk) begin
        for (b = 0; b < NB; b = b + 1)
            hb[CW*b +: CW] <= hclr ? {CW{1'b0}} : hb[CW*b +: CW] + {{(CW-LW-1){1'b0}}, h2[(LW+1)*b +: LW+1]};
        for (n = 1; n < NB; n = n + 1)
            tn[CW*n +: CW] <= tv[CW*(2*n) +: CW] + tv[CW*(2*n+1) +: CW];
        tn[CW-1:0] <= {CW{1'b0}};
    end

    // -- tree walk ---------------------------------------------------------------------
    wire [RB:0]   wright = {wp, 1'b1};              // right child of the current node
    wire [CW-1:0] wc     = tv[CW*wright +: CW];
    // a walk step takes two edges: the first registers the child count (a 2^RB-way mux), the second
    // adds, compares and descends -- the one-edge step was the unit's critical path (wp -> mux -> add ->
    // compare -> subtract -> rem, -0.72 ns at a 0.9 ns target in the routed ot_hdc_tselect_cand)
    reg  [CW-1:0] wc_q;
    reg           wph;
    always @(posedge clk) wc_q <= wc;
    wire [CW:0]   wsum   = wacc + {1'b0, wc_q};
    wire          wgo    = ({{(QW){1'b0}}, wsum} >= {{(CW + 1){1'b0}}, wkq});
    wire [RB-1:0] wp_n   = {wp[RB-2:0], wgo};
    wire [CW:0]   wacc_n = wgo ? wacc : wsum;
    wire          wlast  = (dc == 0) && wph && (wstep == RBM1);
    wire [QW-1:0] wrest  = wkq - wacc_n[QW-1:0];    // quota left for the boundary bucket (<= wkq)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) init <= 3'd7;
        else if (init != 0) init <= init - 1'b1;
    end
    assign hclr = ((state == S_W1) && wlast) || ((state == S_P3) && rptr == nlast) || (init != 0);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_ING; wptr <= 0; rptr <= 0; dc <= 0; wstep <= 0; wph <= 1'b0;
        end else begin
            wph <= (state == S_W1 || state == S_W2) && dc == 0 && !wph;
            case (state)
                S_ING: if (acc_in) begin
                    wptr <= in_last ? {AW{1'b0}} : wptr + 1'b1;
                    if (in_last) begin state <= S_W1; nlast <= wptr; dc <= DR; wstep <= 0; end
                end
                S_W1, S_W2: begin
                    if (dc != 0) dc <= dc - 1'b1;
                    else if (wph) begin
                        wstep <= wstep + 1'b1;
                        if (wlast) begin
                            state <= (state == S_W1) ? S_P2 : S_P3; rptr <= 0; wstep <= 0;
                        end
                    end
                end
                S_P2, S_P3: begin
                    rptr <= rptr + 1'b1;
                    if (rptr == nlast) begin
                        state <= (state == S_P2) ? S_W2 : S_ING; dc <= DR; wstep <= 0;
                    end
                end
                default: state <= S_ING;
            endcase
        end
    end
    // walk datapath (no reset: always initialised before use)
    always @(posedge clk) begin
        if (state == S_ING && acc_in && in_last) begin
            kq  <= ({{(QW-KW){1'b0}}, in_k} > KQ) ? KQ : {{(QW-KW){1'b0}}, in_k};
            wkq <= ({{(QW-KW){1'b0}}, in_k} > KQ) ? KQ : {{(QW-KW){1'b0}}, in_k};
            wp <= {{(RB-1){1'b0}}, 1'b1}; wacc <= 0;
        end else if ((state == S_P2) && rptr == nlast) begin
            wkq <= mq; wp <= {{(RB-1){1'b0}}, 1'b1}; wacc <= 0;
        end else if ((state == S_W1 || state == S_W2) && dc == 0 && wph) begin
            wp <= wp_n; wacc <= wacc_n;
            if (wlast && state == S_W1) begin bsel <= wp_n; mq <= wrest; end
            if (wlast && state == S_W2) begin lsel <= wp_n; end
        end
    end

    // -- pass 3: compare, tie ranks, selection ------------------------------------------
    wire [VW-1:0] tkey = {bsel, lsel};
    reg          c1_v, c1_l;
    reg [W-1:0]  c1_gt, c1_eq;
    reg [W*PW-1:0] c1_p;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin c1_v <= 1'b0; c1_l <= 1'b0; end
        else begin c1_v <= rv && rph3; c1_l <= rv && rph3 && rlast; end
    end
    wire [W-1:0]   c1_gt_d, c1_eq_d;
    wire [W*PW-1:0] c1_p_d;
    generate
        for (gl = 0; gl < W; gl = gl + 1) begin : g_cmp
            wire [VW-1:0] v  = mem_rdata[EW*gl + IW +: VW];
            wire          lv = mem_rdata[EW*gl + EW - 1];
            wire [VW-1:0] k  = fkey(v);
            assign c1_gt_d[gl] = lv && (k > tkey);
            assign c1_eq_d[gl] = lv && (k == tkey);
            assign c1_p_d[PW*gl +: PW] = {v == {1'b1, 8'hFF, {(VW-9){1'b0}}}, v, mem_rdata[EW*gl +: IW]};
        end
    endgenerate
    always @(posedge clk) begin c1_gt <= c1_gt_d; c1_eq <= c1_eq_d; c1_p <= c1_p_d; end
    reg          c2_v, c2_l;
    reg [W-1:0]  c2_gt, c2_eq;
    reg [W*PW-1:0] c2_p;
    reg [(LW+1)*W-1:0] c2_pre;                      // equal keys in lanes below (exclusive)
    reg [LW:0]   c2_cnt;
    wire [(LW+1)*W-1:0] eq_inc;
    ot_hdc_tsel_prefix #(.N(W), .OW(LW + 1)) u_eqpre (.x(c1_eq), .y(eq_inc));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin c2_v <= 1'b0; c2_l <= 1'b0; end
        else begin c2_v <= c1_v; c2_l <= c1_l; end
    end
    always @(posedge clk) begin
        c2_gt <= c1_gt; c2_eq <= c1_eq; c2_p <= c1_p;
        c2_pre <= {eq_inc[(LW+1)*(W-1)-1:0], {(LW+1){1'b0}}};
        c2_cnt <= eq_inc[(LW+1)*(W-1) +: LW+1];
    end
    reg          c3_v, c3_l;
    reg [W-1:0]  c3_sel;
    reg [W*PW-1:0] c3_p;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin c3_v <= 1'b0; c3_l <= 1'b0; end
        else begin c3_v <= c2_v; c3_l <= c2_l; end
    end
    always @(posedge clk) begin
        for (l = 0; l < W; l = l + 1)
            c3_sel[l] <= c2_gt[l] || (c2_eq[l] && ({{(QW-LW-1){1'b0}}, c2_pre[(LW+1)*l +: LW+1]} < rem));
        c3_p <= c2_p;
        if ((state == S_W2) && wlast) rem <= wrest;
        else if (c2_v) rem <= (rem > {{(QW-LW-1){1'b0}}, c2_cnt}) ? rem - {{(QW-LW-1){1'b0}}, c2_cnt} : {QW{1'b0}};
    end

    // -- compaction: z = unselected lanes below; LSB-first shifts, registered every 2 stages
    wire [(LW+1)*W-1:0] sel_inc;
    ot_hdc_tsel_prefix #(.N(W), .OW(LW + 1)) u_selpre (.x(c3_sel), .y(sel_inc));
    reg          c4_v, c4_l;
    reg [LW:0]   c4_cnt;
    reg [W*CE-1:0] c4_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin c4_v <= 1'b0; c4_l <= 1'b0; end
        else begin c4_v <= c3_v; c4_l <= c3_l; end
    end
    wire [W*CE-1:0] c4_e_d;
    generate
        for (gl = 0; gl < W; gl = gl + 1) begin : g_zl
            localparam integer LANEI = gl;
            localparam [LW:0]  LANE = LANEI[LW:0];
            wire [LW:0] below;
            if (gl == 0) begin : g_first
                assign below = {(LW+1){1'b0}};
            end else begin : g_rest
                assign below = sel_inc[(LW+1)*(gl-1) +: LW+1];
            end
            assign c4_e_d[CE*gl +: CE] = {c3_sel[gl], LANE[LW-1:0] - below[LW-1:0], c3_p[PW*gl +: PW]};
        end
    endgenerate
    always @(posedge clk) begin
        c4_cnt <= sel_inc[(LW+1)*(W-1) +: LW+1];
        c4_e   <= c4_e_d;
    end
    localparam integer NCR = (LW + 1) / 2;          // compaction register stages
    wire [NCR*W*CE-1:0]   crf;
    wire [NCR*(LW+1)-1:0] crc;
    reg  [NCR:0]          cr_v, cr_l;               // bit r: stage r holds a beat
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin cr_v <= 0; cr_l <= 0; end
        else begin
            cr_v <= {cr_v[NCR-1:0], c4_v};
            cr_l <= {cr_l[NCR-1:0], c4_l};
        end
    end
    genvar gr;
    generate
        for (gr = 0; gr < NCR; gr = gr + 1) begin : g_cst
            wire [W*CE-1:0] a0 = (gr == 0) ? c4_e : crf[W*CE*(gr == 0 ? 0 : gr - 1) +: W*CE];
            wire [W*CE-1:0] a1, a2;
            ot_hdc_tsel_cstage #(.W(W), .CE(CE), .ZB(PW + 2 * gr), .S(2 * gr)) u_c0 (.a(a0), .y(a1));
            if (2 * gr + 1 < LW) begin : g_c1
                ot_hdc_tsel_cstage #(.W(W), .CE(CE), .ZB(PW + 2 * gr + 1), .S(2 * gr + 1)) u_c1 (.a(a1), .y(a2));
            end else begin : g_c1n
                assign a2 = a1;
            end
            reg  [W*CE-1:0] q;
            reg  [LW:0]     qc;
            always @(posedge clk) begin
                q  <= a2;
                qc <= (gr == 0) ? c4_cnt : crc[(LW+1)*(gr == 0 ? 0 : gr - 1) +: LW+1];
            end
            assign crf[W*CE*gr +: W*CE] = q;
            assign crc[(LW+1)*gr +: LW+1] = qc;
        end
    endgenerate

    // -- rotate by the running fill, then accumulate into W-lane output beats ------------
    wire [W*CE-1:0] cp = crf[W*CE*(NCR-1) +: W*CE];
    wire            cp_v = cr_v[NCR-1], cp_l = cr_l[NCR-1];
    wire [LW:0]     cp_cnt = crc[(LW+1)*(NCR-1) +: LW+1];
    reg  [LW-1:0]   frun;
    reg  [NCR:0]    ro_v, ro_l;
    wire [NCR*2*W*RE-1:0] rof;
    wire [NCR*LW-1:0]     rff;
    wire [NCR*(LW+1)-1:0] rcf;
    reg  [2*W*RE-1:0] rin;
    always @(*) begin
        rin = 0;
        for (l = 0; l < W; l = l + 1) rin[RE*l +: RE] = {cp[CE*l + CE - 1], cp[CE*l +: PW]};
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ro_v <= 0; ro_l <= 0; frun <= 0; end
        else begin
            ro_v <= {ro_v[NCR-1:0], cp_v};
            ro_l <= {ro_l[NCR-1:0], cp_l};
            if (cp_v) frun <= cp_l ? {LW{1'b0}} : frun + cp_cnt[LW-1:0];
        end
    end
    generate
        for (gr = 0; gr < NCR; gr = gr + 1) begin : g_rst
            wire [2*W*RE-1:0] a0 = (gr == 0) ? rin : rof[2*W*RE*(gr == 0 ? 0 : gr - 1) +: 2*W*RE];
            wire [LW-1:0]     f  = (gr == 0) ? frun : rff[LW*(gr == 0 ? 0 : gr - 1) +: LW];
            wire [2*W*RE-1:0] a1, a2;
            ot_hdc_tsel_rstage #(.N(2 * W), .RE(RE), .S(2 * gr)) u_r0 (.a(a0), .sh(f[2 * gr]), .y(a1));
            if (2 * gr + 1 < LW) begin : g_r1
                ot_hdc_tsel_rstage #(.N(2 * W), .RE(RE), .S(2 * gr + 1)) u_r1 (.a(a1), .sh(f[2 * gr + 1]), .y(a2));
            end else begin : g_r1n
                assign a2 = a1;
            end
            reg  [2*W*RE-1:0] q;
            reg  [LW-1:0]     qf;
            reg  [LW:0]       qc;
            always @(posedge clk) begin
                q  <= a2;
                qf <= f;
                qc <= (gr == 0) ? cp_cnt : rcf[(LW+1)*(gr == 0 ? 0 : gr - 1) +: LW+1];
            end
            assign rof[2*W*RE*gr +: 2*W*RE] = q;
            assign rff[LW*gr +: LW] = qf;
            assign rcf[(LW+1)*gr +: LW+1] = qc;
        end
    endgenerate
    wire [2*W*RE-1:0] rq = rof[2*W*RE*(NCR-1) +: 2*W*RE];
    wire              rq_v = ro_v[NCR-1], rq_l = ro_l[NCR-1];
    wire [LW:0]       rq_tot = {1'b0, rff[LW*(NCR-1) +: LW]} + rcf[(LW+1)*(NCR-1) +: LW+1];
    reg  [W*RE-1:0]   acc;                          // the partial output line
    reg  [2*W*RE-1:0] win;
    always @(*) begin
        win = rq;
        for (l = 0; l < W; l = l + 1)
            if (acc[RE*l + RE - 1]) win[RE*l +: RE] = acc[RE*l +: RE];
    end
    task automatic emit(input [W*RE-1:0] line, input last);
        integer e;
        begin
            out_valid <= 1'b1;
            out_last  <= last;
            for (e = 0; e < W; e = e + 1) begin
                out_lv[e]              <= line[RE*e + RE - 1];
                out_ninf[e]            <= line[RE*e + PW - 1];
                out_val[VW*e +: VW]    <= line[RE*e + IW +: VW];
                out_idx[IW*e +: IW]    <= line[RE*e +: IW];
            end
        end
    endtask
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            acc <= 0; oflush <= 1'b0; out_valid <= 1'b0; out_last <= 1'b0;
            out_lv <= 0; out_ninf <= 0; out_val <= 0; out_idx <= 0;
        end else begin
            out_valid <= 1'b0; out_last <= 1'b0;
            if (oflush) begin
                emit(acc, 1'b1); acc <= 0; oflush <= 1'b0;
            end else if (rq_v) begin
                if (rq_tot[LW]) begin                  // a full line leaves
                    emit(win[W*RE-1:0], rq_l && rq_tot[LW-1:0] == 0);
                    acc <= win[2*W*RE-1:W*RE];
                    oflush <= rq_l && rq_tot[LW-1:0] != 0;
                end else if (rq_l) begin
                    emit(win[W*RE-1:0], 1'b1); acc <= 0;
                end else acc <= win[W*RE-1:0];
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) pipe_busy <= 1'b0;
        else if (acc_in && in_last) pipe_busy <= 1'b1;
        else if (out_valid && out_last) pipe_busy <= 1'b0;
    end
    assign busy = pipe_busy || state != S_ING;
endmodule


// -- structural helpers (generate-level, so synthesis does not inline loops) -------------

// balanced popcount of N bits (pairwise tree)
module ot_hdc_tsel_popc #(
    parameter integer N  = 64,
    parameter integer OW = 7
) (
    input  wire [N-1:0]  x,
    output wire [OW-1:0] y
);
    localparam integer NP = 1 << $clog2(N);
    // heap: node n (1 .. 2NP-1) at t[OW*n +: OW]; leaves NP .. 2NP-1
    /* verilator lint_off UNOPTFLAT */
    wire [2*NP*OW-1:0] t;
    /* verilator lint_on UNOPTFLAT */
    genvar n;
    generate
        for (n = 0; n < NP; n = n + 1) begin : g_leaf
            if (n < N) begin : g_x
                assign t[OW*(NP+n) +: OW] = {{(OW-1){1'b0}}, x[n]};
            end else begin : g_0
                assign t[OW*(NP+n) +: OW] = {OW{1'b0}};
            end
        end
        for (n = 1; n < NP; n = n + 1) begin : g_node
            assign t[OW*n +: OW] = t[OW*(2*n) +: OW] + t[OW*(2*n+1) +: OW];
        end
    endgenerate
    assign y = t[OW +: OW];
    assign t[OW-1:0] = {OW{1'b0}};
endmodule

// inclusive prefix counts of N bits (Kogge-Stone): y[OW*l +: OW] = popcount(x[l:0])
module ot_hdc_tsel_prefix #(
    parameter integer N  = 64,
    parameter integer OW = 7
) (
    input  wire [N-1:0]    x,
    output wire [N*OW-1:0] y
);
    localparam integer LV = $clog2(N);
    /* verilator lint_off UNOPTFLAT */
    wire [(LV+1)*N*OW-1:0] s;                      // level d at s[N*OW*d +: N*OW]
    /* verilator lint_on UNOPTFLAT */
    genvar d, l;
    generate
        for (l = 0; l < N; l = l + 1) begin : g_in
            assign s[OW*l +: OW] = {{(OW-1){1'b0}}, x[l]};
        end
        for (d = 0; d < LV; d = d + 1) begin : g_lv
            for (l = 0; l < N; l = l + 1) begin : g_l
                if (l >= (1 << d)) begin : g_add
                    assign s[N*OW*(d+1) + OW*l +: OW] = s[N*OW*d + OW*l +: OW] + s[N*OW*d + OW*(l - (1 << d)) +: OW];
                end else begin : g_pass
                    assign s[N*OW*(d+1) + OW*l +: OW] = s[N*OW*d + OW*l +: OW];
                end
            end
        end
    endgenerate
    assign y = s[N*OW*LV +: N*OW];
endmodule

// one compaction stage: lane j takes lane j + 2^S when that lane is valid (bit CE-1) and its shift
// count has bit S set (bit ZB), else keeps its own lane when that is valid and does not move
module ot_hdc_tsel_cstage #(
    parameter integer W  = 64,
    parameter integer CE = 40,
    parameter integer ZB = 33,
    parameter integer S  = 0
) (
    input  wire [W*CE-1:0] a,
    output wire [W*CE-1:0] y
);
    genvar j;
    generate
        for (j = 0; j < W; j = j + 1) begin : g_lane
            wire [CE-1:0] me = a[CE*j +: CE];
            wire [CE-1:0] up;
            if (j + (1 << S) < W) begin : g_up
                assign up = a[CE*(j + (1 << S)) +: CE];
            end else begin : g_none
                assign up = {CE{1'b0}};
            end
            wire take = up[CE-1] && up[ZB];
            wire keep = me[CE-1] && !me[ZB];
            assign y[CE*j +: CE] = take ? up : keep ? me : {CE{1'b0}};
        end
    endgenerate
endmodule

// one rotate stage over N lanes: every lane moves 2^S up when `sh` is set
module ot_hdc_tsel_rstage #(
    parameter integer N  = 128,
    parameter integer RE = 34,
    parameter integer S  = 0
) (
    input  wire [N*RE-1:0] a,
    input  wire            sh,
    output wire [N*RE-1:0] y
);
    genvar j;
    generate
        for (j = 0; j < N; j = j + 1) begin : g_lane
            if (j >= (1 << S)) begin : g_mv
                assign y[RE*j +: RE] = sh ? a[RE*(j - (1 << S)) +: RE] : a[RE*j +: RE];
            end else begin : g_lo
                assign y[RE*j +: RE] = sh ? {RE{1'b0}} : a[RE*j +: RE];
            end
        end
    endgenerate
endmodule
