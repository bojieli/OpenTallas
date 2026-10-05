`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Quartered threshold SELECT: Q x W-lane ot_hdc_tselect datapaths sharing one
// threshold, for the V4.1 index top-512 at Q x W elements per cycle without a
// Q x W-lane histogram or crossbar (the single 64-lane unit does not route on
// ASAP7: global routing congestion at 35/20/12 % utilisation).
//
// Semantics: tools/hdc_golden_v41.py `topk_lowest_index` in ascending-index
// order (k largest values, ties to the LOWER index, -0 == +0; NaN outside the
// contract), exactly as ot_hdc_tselect.
//
// Contract.  A segment is split into Q CONTIGUOUS position ranges ("quarters"):
// quarter q streams its range on its own port, W lanes per beat, indices
// ascending, closing with its own `in_last` (a quarter may be empty: one beat
// with in_lv = 0 and in_last).  Every index of quarter q is below every index of
// quarter q+1.  The runtime k is taken from quarter 0's in_last beat.  A
// quarter that has sent its last beat waits (in_ready low) until every quarter
// has, then the segment is processed.  Quarter q emits its part of the
// selection on its own output port, packed W lanes per beat, in position order,
// closed by its own `out_last` (every quarter emits at least one beat, the
// last possibly empty).  The concatenation of the Q outputs in quarter order is
// the selection in position order -- no merge.  Uses: the local level streams
// four position quarters of a die's scores; the cross-die level streams the G
// = Q dies' local selections, one die per quarter (each die owns a contiguous
// position range).  Each quarter has its own line memory (synchronous read,
// one-cycle latency, as ot_hdc_tselect).
//
// Algorithm: ot_hdc_tselect's, with one shared threshold.  Each quarter counts
// its hi (then lo) digits in its own 2^RB bins (a W-lane popcount per bin); the
// tree leaves are the registered sums of the Q quarters' bins, so the walks
// see the whole segment.  After walk 2 each quarter's tie quota is
//   rem_q = max(0, t - sum_{q' < q} eq_q'),   eq_q = quarter q's bin L count
// (its elements equal to T), because every tie in an earlier quarter precedes
// every tie in a later one.  Pass 3 runs in every quarter at once over its own
// lines with its own quota.
//
// Latency (edges from the edge that accepts the segment's final last beat,
// over all quarters, to the edge that registers the last quarter's out_last):
//   2 NL + LAT0 (+1 on a final-line overflow), NL = the longest quarter's
//   beats, LAT0 = ot_hdc_tselect's LAT0 + 2 (the registered leaf sums add one
//   edge to each walk's drain) = 2 x (12 + 16) + 5 + 2 ceil(log2(W) / 2).
// ---------------------------------------------------------------------------
module ot_hdc_tselect_q #(
    parameter integer Q  = 4,         // quarters (contiguous position ranges)
    parameter integer W  = 16,        // lanes per quarter per beat (power of two)
    parameter integer VW = 16,
    parameter integer IW = 16,
    parameter integer K  = 512,
    parameter integer AW = 10,        // line-address width per quarter
    parameter integer KW = $clog2(K + 1)
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire [Q-1:0]             in_valid,
    output wire [Q-1:0]             in_ready,
    input  wire [Q-1:0]             in_last,
    input  wire [Q*W-1:0]           in_lv,
    input  wire [Q*W*VW-1:0]        in_val,
    input  wire [Q*W*IW-1:0]        in_idx,
    input  wire [KW-1:0]            in_k,
    output wire [Q-1:0]             out_valid,
    output wire [Q-1:0]             out_last,
    output wire [Q*W-1:0]           out_lv,
    output wire [Q*W*VW-1:0]        out_val,
    output wire [Q*W*IW-1:0]        out_idx,
    output wire [Q*W-1:0]           out_ninf,
    output wire [Q-1:0]             mem_we,
    output wire [Q*AW-1:0]          mem_waddr,
    output wire [Q*W*(1+VW+IW)-1:0] mem_wdata,
    output wire [Q-1:0]             mem_re,
    output wire [Q*AW-1:0]          mem_raddr,
    input  wire [Q*W*(1+VW+IW)-1:0] mem_rdata,
    output wire                     busy
);
    localparam integer RB  = VW / 2;
    localparam integer HA  = RB / 2;
    localparam integer NH  = 1 << HA;
    localparam integer NL0 = 1 << (RB - HA);
    localparam integer NB  = 1 << RB;
    localparam integer LW  = $clog2(W);
    localparam integer QB  = (Q > 1) ? $clog2(Q) : 1;
    localparam integer CWQ = AW + LW + 1;          // one quarter's bin count width
    localparam integer CW  = CWQ + QB;             // leaf / tree count width
    localparam integer EW  = 1 + VW + IW;
    localparam integer PW  = 1 + VW + IW;
    localparam integer QW  = ((KW > CW ? KW : CW)) + 1;
    localparam integer DRAIN = 5 + RB - 1;         // histogram (4) + leaf sums (1) + tree levels below 1
    localparam integer PS  = (W >= 16) ? 8 : 1;
    localparam integer PW_ = $clog2(W / PS);
    localparam integer CE  = 1 + LW + PW;
    localparam integer RE  = 1 + PW;
    localparam integer KQI = K;
    localparam [QW-1:0] KQ = KQI[QW-1:0];
    localparam integer RBM1I = RB - 1;
    localparam [3:0]    RBM1 = RBM1I[3:0];
    localparam [4:0]    DR = DRAIN[4:0];
    localparam [2:0] S_ING = 3'd0, S_W1 = 3'd1, S_P2 = 3'd2, S_W2 = 3'd3, S_P3 = 3'd4;

    function automatic [VW-1:0] fkey(input [VW-1:0] v);
        fkey = (v[VW-2:0] == 0) ? {1'b1, {(VW-1){1'b0}}} : v[VW-1] ? ~v : {1'b1, v[VW-2:0]};
    endfunction

    // -- shared control ------------------------------------------------------------------
    reg  [2:0]    state;
    reg  [AW-1:0] rptr, nmax;
    reg  [QW-1:0] mq, trest;
    reg  [RB-1:0] bsel, lsel;
    reg  [4:0]    dc;
    reg  [RB-1:0] wp;
    reg  [3:0]    wstep;
    reg  [CW:0]   wacc;
    reg  [QW-1:0] wkq;
    reg           wph, w2d;
    reg  [2:0]    init;
    reg  [Q-1:0]  done;                             // quarter has delivered its last beat
    wire [Q-1:0]  acc_q = in_valid & in_ready;
    wire [Q-1:0]  lastq = acc_q & in_last;
    wire [Q-1:0]  done_n = done | lastq;
    wire          seg_in = (state == S_ING) && (lastq != 0) && (&done_n);
    assign in_ready = {Q{(state == S_ING) && (init == 0)}} & ~done;
    wire rd = (state == S_P2) || (state == S_P3);
    wire rd_end = rd && (rptr == nmax);
    wire hclr_c;
    // runtime k: from quarter 0's last beat
    reg  [KW-1:0] kq0;
    wire [KW-1:0] kq_s = lastq[0] ? in_k : kq0;
    always @(posedge clk) if (lastq[0]) kq0 <= in_k;
    wire [AW*Q-1:0] nlast_v;
    wire [Q*NB*CWQ-1:0] hbq;                        // every quarter's bins

    // -- leaf sums and tree ---------------------------------------------------------------
    reg [NB*CW-1:0] lf;                             // registered sums of the Q quarters' bins
    reg [NB*CW-1:0] tn;
    wire [2*NB*CW-1:0] tv = {lf, tn};
    integer n;
    wire [NB*CW-1:0] lf_d;
    genvar gs, gt;
    generate
        for (gs = 0; gs < NB; gs = gs + 1) begin : g_lsum
            wire [Q*CWQ-1:0] xs;
            for (gt = 0; gt < Q; gt = gt + 1) begin : g_t
                assign xs[CWQ*gt +: CWQ] = hbq[(gt*NB + gs)*CWQ +: CWQ];
            end
            ot_hdc_tsel_sum #(.N(Q), .IW(CWQ), .OW(CW)) u_ls (.x(xs), .y(lf_d[CW*gs +: CW]));
        end
    endgenerate
    always @(posedge clk) begin
        lf <= lf_d;
        for (n = 1; n < NB; n = n + 1)
            tn[CW*n +: CW] <= tv[CW*(2*n) +: CW] + tv[CW*(2*n+1) +: CW];
        tn[CW-1:0] <= {CW{1'b0}};
    end

    // -- tree walk (two edges a step, as ot_hdc_tselect) ----------------------------------
    wire [RB:0]   wright = {wp, 1'b1};
    wire [CW-1:0] wc     = tv[CW*wright +: CW];
    reg  [CW-1:0] wc_q;
    always @(posedge clk) wc_q <= wc;
    wire [CW:0]   wsum   = wacc + {1'b0, wc_q};
    wire          wgo    = ({{(QW){1'b0}}, wsum} >= {{(CW + 1){1'b0}}, wkq});
    wire [RB-1:0] wp_n   = {wp[RB-2:0], wgo};
    wire [CW:0]   wacc_n = wgo ? wacc : wsum;
    wire          wlast  = (dc == 0) && wph && (wstep == RBM1);
    wire [QW-1:0] wrest  = wkq - wacc_n[QW-1:0];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) init <= 3'd7;
        else if (init != 0) init <= init - 1'b1;
    end
    assign hclr_c = ((state == S_W1) && wlast) || ((state == S_P3) && rd_end) || (init != 0);

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_ING; rptr <= 0; dc <= 0; wstep <= 0; wph <= 1'b0; done <= 0; w2d <= 1'b0;
        end else begin
            wph <= (state == S_W1 || state == S_W2) && dc == 0 && !wph;
            w2d <= (state == S_W2) && wlast;
            case (state)
                S_ING: begin
                    if (seg_in) begin state <= S_W1; dc <= DR; wstep <= 0; done <= 0; end
                    else done <= done_n;
                end
                S_W1, S_W2: begin
                    if (dc != 0) dc <= dc - 1'b1;
                    else if (wph) begin
                        wstep <= wstep + 1'b1;
                        if (wlast) begin state <= (state == S_W1) ? S_P2 : S_P3; rptr <= 0; wstep <= 0; end
                    end
                end
                S_P2, S_P3: begin
                    rptr <= rptr + 1'b1;
                    if (rptr == nmax) begin state <= (state == S_P2) ? S_W2 : S_ING; dc <= DR; wstep <= 0; end
                end
                default: state <= S_ING;
            endcase
        end
    end
    // the longest quarter's last line, once every quarter has closed
    reg [AW-1:0] mx;
    always @(*) begin
        mx = {AW{1'b0}};
        for (i = 0; i < Q; i = i + 1)
            if (nlast_v[AW*i +: AW] > mx) mx = nlast_v[AW*i +: AW];
    end
    always @(posedge clk) begin
        if (state == S_W1 && dc == DR) nmax <= mx;  // quarters' nlast settle on the segment's last accept
        if (seg_in) begin
            wkq <= ({{(QW-KW){1'b0}}, kq_s} > KQ) ? KQ : {{(QW-KW){1'b0}}, kq_s};
            wp <= {{(RB-1){1'b0}}, 1'b1}; wacc <= 0;
        end else if ((state == S_P2) && rptr == nmax) begin
            wkq <= mq; wp <= {{(RB-1){1'b0}}, 1'b1}; wacc <= 0;
        end else if ((state == S_W1 || state == S_W2) && dc == 0 && wph) begin
            wp <= wp_n; wacc <= wacc_n;
            if (wlast && state == S_W1) begin bsel <= wp_n; mq <= wrest; end
            if (wlast && state == S_W2) begin lsel <= wp_n; trest <= wrest; end
        end
    end

    // tie quotas: rem_q = max(0, t - ties in earlier quarters), loaded the edge after walk 2
    reg  [Q*CW-1:0] eqpre;                          // ties (bin L) in quarters below q
    reg  [CW-1:0]   eacc;
    always @(*) begin
        eacc = {CW{1'b0}};
        for (i = 0; i < Q; i = i + 1) begin
            eqpre[CW*i +: CW] = eacc;
            eacc = eacc + {{QB{1'b0}}, hbq[(i*NB)*CWQ + CWQ*lsel +: CWQ]};
        end
    end
    genvar gq;

    reg [Q-1:0] ib;                                 // quarter still owes this segment's out_last
    wire [Q-1:0] ol;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ib <= 0;
        else ib <= (ib & ~(out_valid & out_last)) | {Q{seg_in}};
    end
    assign busy = (state != S_ING) || (ib != 0) || (done != 0);

    // -- per-quarter datapath ----------------------------------------------------------------
    generate
        for (gq = 0; gq < Q; gq = gq + 1) begin : g_q
            wire          acc_in = acc_q[gq];
            reg  [AW-1:0] wptr, nlast;
            assign nlast_v[AW*gq +: AW] = nlast;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) wptr <= 0;
                else if (acc_in) wptr <= in_last[gq] ? {AW{1'b0}} : wptr + 1'b1;
            end
            always @(posedge clk) if (acc_in && in_last[gq]) nlast <= wptr;
            wire [W-1:0]    ilv  = in_lv[W*gq +: W];
            wire [W*VW-1:0] ival = in_val[W*VW*gq +: W*VW];
            wire [W*IW-1:0] iidx = in_idx[W*IW*gq +: W*IW];
            wire [W*EW-1:0] rdat = mem_rdata[W*EW*gq +: W*EW];
            assign mem_we[gq] = acc_in;
            assign mem_waddr[AW*gq +: AW] = wptr;
            genvar gl;
            for (gl = 0; gl < W; gl = gl + 1) begin : g_wd
                assign mem_wdata[W*EW*gq + EW*gl +: EW] = {ilv[gl], ival[VW*gl +: VW], iidx[IW*gl +: IW]};
            end
            wire qrd = rd && (rptr <= nlast);
            assign mem_re[gq] = qrd;
            assign mem_raddr[AW*gq +: AW] = rptr;

            reg          s0_v;
            reg [W-1:0]  s0_lv;
            reg [W*VW-1:0] s0_val;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) s0_v <= 1'b0;
                else s0_v <= acc_in;
            end
            always @(posedge clk) if (acc_in) begin s0_lv <= ilv; s0_val <= ival; end
            reg rv, rph3, rlast;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin rv <= 1'b0; rph3 <= 1'b0; rlast <= 1'b0; end
                else begin rv <= qrd; rph3 <= (state == S_P3); rlast <= qrd && (rptr == nlast); end
            end

            // histogram of this quarter
            reg [W*NH-1:0]  h1_hi;
            reg [W*NL0-1:0] h1_lo;
            wire hs_ing = s0_v;
            wire hs_p2  = rv && !rph3;
            wire [W*NH-1:0]  h1_hi_d;
            wire [W*NL0-1:0] h1_lo_d;
            for (gl = 0; gl < W; gl = gl + 1) begin : g_hpre
                wire [VW-1:0] v  = hs_ing ? s0_val[VW*gl +: VW] : rdat[EW*gl + IW +: VW];
                wire [VW-1:0] k  = fkey(v);
                wire          e  = hs_ing ? s0_lv[gl] : (hs_p2 && rdat[EW*gl + EW - 1] && k[VW-1 -: RB] == bsel);
                wire [RB-1:0] dg = hs_ing ? k[VW-1 -: RB] : k[RB-1:0];
                assign h1_hi_d[NH*gl +: NH]   = e ? ({{(NH-1){1'b0}}, 1'b1} << dg[RB-1 -: HA]) : {NH{1'b0}};
                assign h1_lo_d[NL0*gl +: NL0] = {{(NL0-1){1'b0}}, 1'b1} << dg[RB-HA-1:0];
            end
            always @(posedge clk) begin h1_hi <= h1_hi_d; h1_lo <= h1_lo_d; end
            reg  [NB*(LW+1)-1:0] h2;
            wire [NB*(LW+1)-1:0] h2_d;
            genvar gb, gx;
            for (gb = 0; gb < NB; gb = gb + 1) begin : g_hcnt
                wire [W-1:0] x;
                for (gx = 0; gx < W; gx = gx + 1) begin : g_x
                    assign x[gx] = h1_hi[NH*gx + (gb >> (RB - HA))] && h1_lo[NL0*gx + (gb % NL0)];
                end
                wire [PS*(PW_+1)-1:0] part_d;
                reg  [PS*(PW_+1)-1:0] part;
                for (gx = 0; gx < PS; gx = gx + 1) begin : g_ps
                    ot_hdc_tsel_popc #(.N(W / PS), .OW(PW_ + 1)) u_pp (.x(x[(W / PS)*gx +: W / PS]),
                                                                       .y(part_d[(PW_+1)*gx +: PW_+1]));
                end
                always @(posedge clk) part <= part_d;
                ot_hdc_tsel_sum #(.N(PS), .IW(PW_ + 1), .OW(LW + 1)) u_ps (.x(part), .y(h2_d[(LW+1)*gb +: LW+1]));
            end
            always @(posedge clk) h2 <= h2_d;
            reg [NB*CWQ-1:0] hb;
            integer bb;
            always @(posedge clk) begin
                for (bb = 0; bb < NB; bb = bb + 1)
                    hb[CWQ*bb +: CWQ] <= hclr_c ? {CWQ{1'b0}} : hb[CWQ*bb +: CWQ] + {{(CWQ-LW-1){1'b0}}, h2[(LW+1)*bb +: LW+1]};
            end
            assign hbq[gq*NB*CWQ +: NB*CWQ] = hb;

            // pass 3
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
            for (gl = 0; gl < W; gl = gl + 1) begin : g_cmp
                wire [VW-1:0] v  = rdat[EW*gl + IW +: VW];
                wire          lv = rdat[EW*gl + EW - 1];
                wire [VW-1:0] k  = fkey(v);
                assign c1_gt_d[gl] = lv && (k > tkey);
                assign c1_eq_d[gl] = lv && (k == tkey);
                assign c1_p_d[PW*gl +: PW] = {v == {1'b1, 8'hFF, {(VW-9){1'b0}}}, v, rdat[EW*gl +: IW]};
            end
            always @(posedge clk) begin c1_gt <= c1_gt_d; c1_eq <= c1_eq_d; c1_p <= c1_p_d; end
            reg          c2_v, c2_l;
            reg [W-1:0]  c2_gt, c2_eq;
            reg [W*PW-1:0] c2_p;
            reg [(LW+1)*W-1:0] c2_pre;
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
            reg [QW-1:0] rem;
            wire [QW-1:0] epq = {{(QW-CW){1'b0}}, eqpre[CW*gq +: CW]};
            integer ll;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin c3_v <= 1'b0; c3_l <= 1'b0; end
                else begin c3_v <= c2_v; c3_l <= c2_l; end
            end
            always @(posedge clk) begin
                for (ll = 0; ll < W; ll = ll + 1)
                    c3_sel[ll] <= c2_gt[ll] || (c2_eq[ll] && ({{(QW-LW-1){1'b0}}, c2_pre[(LW+1)*ll +: LW+1]} < rem));
                c3_p <= c2_p;
                if (w2d) rem <= (trest > epq) ? trest - epq : {QW{1'b0}};
                else if (c2_v) rem <= (rem > {{(QW-LW-1){1'b0}}, c2_cnt}) ? rem - {{(QW-LW-1){1'b0}}, c2_cnt} : {QW{1'b0}};
            end

            // compaction
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
            always @(posedge clk) begin
                c4_cnt <= sel_inc[(LW+1)*(W-1) +: LW+1];
                c4_e   <= c4_e_d;
            end
            localparam integer NCR = (LW + 1) / 2;
            wire [NCR*W*CE-1:0]   crf;
            wire [NCR*(LW+1)-1:0] crc;
            reg  [NCR:0]          cr_v, cr_l;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin cr_v <= 0; cr_l <= 0; end
                else begin cr_v <= {cr_v[NCR-1:0], c4_v}; cr_l <= {cr_l[NCR-1:0], c4_l}; end
            end
            genvar gr;
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

            // rotate + accumulate
            wire [W*CE-1:0] cp = crf[W*CE*(NCR-1) +: W*CE];
            wire            cp_v = cr_v[NCR-1], cp_l = cr_l[NCR-1];
            wire [LW:0]     cp_cnt = crc[(LW+1)*(NCR-1) +: LW+1];
            reg  [LW-1:0]   frun;
            reg  [NCR:0]    ro_v, ro_l;
            wire [NCR*2*W*RE-1:0] rof;
            wire [NCR*LW-1:0]     rff;
            wire [NCR*(LW+1)-1:0] rcf;
            wire [2*W*RE-1:0] rin;
            for (gl = 0; gl < 2 * W; gl = gl + 1) begin : g_rin
                if (gl < W) begin : g_l
                    assign rin[RE*gl +: RE] = {cp[CE*gl + CE - 1], cp[CE*gl +: PW]};
                end else begin : g_h
                    assign rin[RE*gl +: RE] = {RE{1'b0}};
                end
            end
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin ro_v <= 0; ro_l <= 0; frun <= 0; end
                else begin
                    ro_v <= {ro_v[NCR-1:0], cp_v};
                    ro_l <= {ro_l[NCR-1:0], cp_l};
                    if (cp_v) frun <= cp_l ? {LW{1'b0}} : frun + cp_cnt[LW-1:0];
                end
            end
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
            wire [2*W*RE-1:0] rq = rof[2*W*RE*(NCR-1) +: 2*W*RE];
            wire              rq_v = ro_v[NCR-1], rq_l = ro_l[NCR-1];
            wire [LW:0]       rq_tot = {1'b0, rff[LW*(NCR-1) +: LW]} + rcf[(LW+1)*(NCR-1) +: LW+1];
            reg  [W*RE-1:0]   acc;
            wire [2*W*RE-1:0] win;
            for (gl = 0; gl < 2 * W; gl = gl + 1) begin : g_win
                if (gl < W) begin : g_l
                    assign win[RE*gl +: RE] = acc[RE*gl + RE - 1] ? acc[RE*gl +: RE] : rq[RE*gl +: RE];
                end else begin : g_h
                    assign win[RE*gl +: RE] = rq[RE*gl +: RE];
                end
            end
            reg          o_v, o_l, oflush;
            reg [W*RE-1:0] o_line;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    acc <= 0; oflush <= 1'b0; o_v <= 1'b0; o_l <= 1'b0; o_line <= 0;
                end else begin
                    o_v <= 1'b0; o_l <= 1'b0;
                    if (oflush) begin
                        o_v <= 1'b1; o_l <= 1'b1; o_line <= acc; acc <= 0; oflush <= 1'b0;
                    end else if (rq_v) begin
                        if (rq_tot[LW]) begin
                            o_v <= 1'b1; o_l <= rq_l && rq_tot[LW-1:0] == 0; o_line <= win[W*RE-1:0];
                            acc <= win[2*W*RE-1:W*RE];
                            oflush <= rq_l && rq_tot[LW-1:0] != 0;
                        end else if (rq_l) begin
                            o_v <= 1'b1; o_l <= 1'b1; o_line <= win[W*RE-1:0]; acc <= 0;
                        end else acc <= win[W*RE-1:0];
                    end
                end
            end
            assign out_valid[gq] = o_v;
            assign out_last[gq]  = o_l;
            for (gl = 0; gl < W; gl = gl + 1) begin : g_out
                assign out_lv[W*gq + gl]              = o_line[RE*gl + RE - 1];
                assign out_ninf[W*gq + gl]            = o_line[RE*gl + PW - 1];
                assign out_val[W*VW*gq + VW*gl +: VW] = o_line[RE*gl + IW +: VW];
                assign out_idx[W*IW*gq + IW*gl +: IW] = o_line[RE*gl +: IW];
            end
        end
    endgenerate
endmodule
