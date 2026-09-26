`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// V4.1x index SELECT: a STREAMING EXACT FILTER in front of a threshold select, with an
// in-place garbage collector, for the DeepSeek-V4.1-Flash indexer top-k (k <= K = 512)
// at Q x W = 4 x 16 = 64 scores per cycle, and for the cross-die final select over the
// Q dies' local selections.  Block `sel` of docs/ARCH_SPEC_V41.md section 6 item 6.
//
// Semantics: tools/hdc_golden_v41.py `topk_lowest_index` emitted in ascending position
// order (the indexer's `sorted(...)`): the k largest BF16 values, ties to the LOWER
// index, -0 == +0; -inf is the smallest value, so masked (-inf) keys are selected only
// when fewer than k keys are finite; NaN is outside the contract.
//
// Contract (per segment = one query's scores on one die):
//   * The positions are split into Q CONTIGUOUS ranges ("quarters", any sizes, empty
//     allowed); quarter q streams its range on port q, W lanes per beat under
//     valid/ready, indices ASCENDING in stream order (lane 0 first), any lane mask
//     (`in_lv`), closing with its own `in_last` (an empty quarter sends one beat with
//     in_lv = 0 and in_last).  Every index of quarter q is below every index of q+1.
//     in_ready stays high for the whole ingest (64 scores/cycle, never throttled) until
//     the quarter's last beat.  The runtime k (`in_k`, clamped to K) must be the same
//     on every beat of the segment; it is taken from the first accepted beat.
//   * Output: port q emits quarter q's part of the selection, packed W lanes per beat
//     (every beat full except the last), in position order, closed by `out_last`
//     (a quarter with nothing selected emits one beat with out_lv = 0); valid/ready.
//     The concatenation of the Q outputs in quarter order is the selection.
//     `out_ninf` marks selected -inf values.
//   * Line memory: one 1R1W memory per quarter, 2^AW lines of W lanes x (1+16+IW) bits,
//     synchronous read (mem_rdata holds the line addressed on the edge where mem_re was
//     high, from the next edge on); all memory ports are registered here.
//   * Overflow fallback: when a quarter's survivors exceed its memory, the unit raises
//     `ovf` and, after the ingest, pulses `rep_req` twice; after each pulse the source
//     must re-stream the whole segment (same beats, all quarters).  The result is still
//     exact; the tail grows by two full scans (the two-pass select's latency).
//   * The next segment is accepted once every quarter has emitted its out_last.
//
// Algorithm.  Keys are the order-preserving 16-bit keys of the BF16 values (hi digit =
// top 8 bits, lo digit = bottom 8).  T is a running LOWER BOUND on the k-th largest key:
// at every moment, at least k elements already seen have key >= T.  An arriving element
// with key < T has k elements strictly above it and can never be selected; it is dropped
// (the FILTER).  Survivors (key >= T) are counted in a coarse (hi-digit) histogram and,
// when their hi digit is the tracked bucket Bt, in a fine (lo-digit) histogram; T is
// raised from these counts every cycle by two pipelined radix-16 searches (the control):
//   coarse: the highest bucket b with count(>= b) >= k            -> T >= {b, 0}
//   fine:   the highest l with count(> Bt) + fine(>= l) >= k        -> T >= {Bt, l}
// (a result is used only when its comparison actually verified >= k; counts only grow, so
// counts sampled at different edges keep the bound valid).  The slices keep the
// survivors in their line memories and continuously re-filter them against the current
// T (in-place GC sweeps), so the memories hold little more than the elements >= T.
// After the last score: the coarse search on the final counts gives the boundary bucket
// B and quota m = k - count(> B) (exact); pass 2 sweeps the survivors (dropping < {B,0})
// and histograms bucket B's lo digits; the fine search gives L, T* = {B, L} and the tie
// quota t = m - count(B, > L); quarter q takes t_q = max(0, t - ties in quarters < q) ties;
// pass 3 keeps key > T* and the first t_q ties (in stream order) and writes the
// selection back; EMIT streams it out.  Exactness: every element of the golden top-k is
// >= every bound ever used, so it survives the filter, the GC and pass 2; histogram
// counts of dropped elements only sit in buckets <= B below T*, so B, m, L and t are
// exact; pass 3 is ot_hdc_tselect's pass 3 per quarter with ot_hdc_tselect_q's quota.
//
// Tail (edges from the final last accept to the last out_last, out_ready high):
//   about 60 + NL2 + NL3 + NLo, with NL2/NL3 the lines the busiest quarter holds at
//   pass 2 / pass 3 (after the GC: ~ the elements >= T, not the survivors) and NLo its
//   output lines; the campaign measures it (spec: <= 181 at 1M per die, <= 155 at 200K).
//
// Hierarchy: Q ot_hdc_v41x_sel_slice (one quarter each: filter, histograms, packers,
// sweep engine, output FIFO; routed on their own) + ot_hdc_v41x_sel_ctl (the two
// searches, the bound and the sequencing).  Every signal between them is registered
// on both sides.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_sel #(
    parameter integer Q  = 4,         // quarters (contiguous position ranges), <= 4
    parameter integer W  = 16,        // lanes per quarter
    parameter integer IW = 20,        // index width
    parameter integer K  = 512,       // largest runtime k
    parameter integer AW = 8,         // line-memory address width per quarter
    parameter integer DG = 4,         // GC write-back queue per quarter
    parameter integer OD = 4,         // output FIFO per quarter
    parameter integer KW = $clog2(K + 1)
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire [Q-1:0]             in_valid,
    output wire [Q-1:0]             in_ready,
    input  wire [Q-1:0]             in_last,
    input  wire [Q*W-1:0]           in_lv,
    input  wire [Q*W*16-1:0]        in_val,
    input  wire [Q*W*IW-1:0]        in_idx,
    input  wire [KW-1:0]            in_k,
    output wire [Q-1:0]             out_valid,
    input  wire [Q-1:0]             out_ready,
    output wire [Q-1:0]             out_last,
    output wire [Q*W-1:0]           out_lv,
    output wire [Q*W*16-1:0]        out_val,
    output wire [Q*W*IW-1:0]        out_idx,
    output wire [Q*W-1:0]           out_ninf,
    output wire [Q-1:0]             mem_we,
    output wire [Q*AW-1:0]          mem_waddr,
    output wire [Q*W*(17+IW)-1:0]   mem_wdata,
    output wire [Q-1:0]             mem_re,
    output wire [Q*AW-1:0]          mem_raddr,
    input  wire [Q*W*(17+IW)-1:0]   mem_rdata,
    output wire                     rep_req,
    output wire                     ovf,
    output wire                     busy,
    output wire [Q*3*(AW+1)-1:0]    stats      // per quarter {lines read by P3, by P2, written by ingest}
);
    localparam integer CB = KW + 1;
    localparam integer GW = CB + 4;
    localparam integer EW = 17 + IW;

    wire [15:0]        c_T, c_st;
    wire [7:0]         c_Bt;
    wire [3:0]         c_cg, c_fg;
    wire               c_fclr, c_ing, c_stop, c_p2, c_p3, c_rep, c_hclr;
    wire [Q*(KW+1)-1:0] c_rem;
    wire [Q*16*GW-1:0] s_gc, s_gf;
    wire [Q*16*CB-1:0] s_bc, s_bf;
    wire [Q-1:0]       s_last, s_hfin, s_stopped, s_done2, s_emitted, s_ovf;

    reg  [KW-1:0] k_r;
    reg           kld_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) kld_r <= 1'b0;
        else kld_r <= |(in_valid & in_ready);
    end
    always @(posedge clk) if (|(in_valid & in_ready)) k_r <= in_k;

    genvar gq;
    generate
        for (gq = 0; gq < Q; gq = gq + 1) begin : g_s
            ot_hdc_v41x_sel_slice #(.W(W), .IW(IW), .K(K), .AW(AW), .DG(DG), .OD(OD), .KW(KW), .CB(CB)) u_s (
                .clk(clk), .rst_n(rst_n),
                .in_valid(in_valid[gq]), .in_ready(in_ready[gq]), .in_last(in_last[gq]),
                .in_lv(in_lv[W*gq +: W]), .in_val(in_val[W*16*gq +: W*16]), .in_idx(in_idx[W*IW*gq +: W*IW]),
                .c_T(c_T), .c_Bt(c_Bt), .c_fclr(c_fclr), .c_cg(c_cg), .c_fg(c_fg), .c_ing(c_ing), .c_stop(c_stop),
                .c_p2(c_p2), .c_p3(c_p3), .c_rep(c_rep), .c_st(c_st), .c_rem(c_rem[(KW+1)*gq +: KW+1]),
                .c_hclr(c_hclr),
                .s_gc(s_gc[16*GW*gq +: 16*GW]), .s_gf(s_gf[16*GW*gq +: 16*GW]),
                .s_bc(s_bc[16*CB*gq +: 16*CB]), .s_bf(s_bf[16*CB*gq +: 16*CB]),
                .s_last(s_last[gq]), .s_hfin(s_hfin[gq]), .s_stopped(s_stopped[gq]), .s_done2(s_done2[gq]),
                .s_emitted(s_emitted[gq]), .s_ovf(s_ovf[gq]),
                .s_nhead(stats[3*(AW+1)*gq +: AW+1]), .s_n2(stats[3*(AW+1)*gq + AW+1 +: AW+1]),
                .s_n3(stats[3*(AW+1)*gq + 2*(AW+1) +: AW+1]),
                .mem_we(mem_we[gq]), .mem_waddr(mem_waddr[AW*gq +: AW]), .mem_wdata(mem_wdata[W*EW*gq +: W*EW]),
                .mem_re(mem_re[gq]), .mem_raddr(mem_raddr[AW*gq +: AW]), .mem_rdata(mem_rdata[W*EW*gq +: W*EW]),
                .out_valid(out_valid[gq]), .out_ready(out_ready[gq]), .out_last(out_last[gq]),
                .out_lv(out_lv[W*gq +: W]), .out_val(out_val[W*16*gq +: W*16]), .out_idx(out_idx[W*IW*gq +: W*IW]),
                .out_ninf(out_ninf[W*gq +: W]));
        end
    endgenerate

    ot_hdc_v41x_sel_ctl #(.Q(Q), .K(K), .KW(KW), .CB(CB)) u_ctl (
        .clk(clk), .rst_n(rst_n), .k_in(k_r), .k_ld(kld_r),
        .s_gc(s_gc), .s_gf(s_gf), .s_bc(s_bc), .s_bf(s_bf),
        .s_last(s_last), .s_hfin(s_hfin), .s_stopped(s_stopped), .s_done2(s_done2), .s_emitted(s_emitted),
        .s_ovf(s_ovf),
        .c_T(c_T), .c_Bt(c_Bt), .c_fclr(c_fclr), .c_cg(c_cg), .c_fg(c_fg), .c_ing(c_ing), .c_stop(c_stop),
        .c_p2(c_p2), .c_p3(c_p3), .c_rep(c_rep), .c_st(c_st), .c_rem(c_rem), .c_hclr(c_hclr),
        .rep_req(rep_req), .ovf(ovf), .busy(busy));
endmodule

// ---------------------------------------------------------------------------
// Control: the running bound (two pipelined radix-16 searches over the slices'
// histograms) and the segment sequencing.  All outputs are registers.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_sel_ctl #(
    parameter integer Q  = 4,
    parameter integer K  = 512,
    parameter integer KW = $clog2(K + 1),
    parameter integer CB = KW + 1
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire [KW-1:0]           k_in,
    input  wire                    k_ld,
    input  wire [Q*16*(CB+4)-1:0]  s_gc,
    input  wire [Q*16*(CB+4)-1:0]  s_gf,
    input  wire [Q*16*CB-1:0]      s_bc,
    input  wire [Q*16*CB-1:0]      s_bf,
    input  wire [Q-1:0]            s_last,
    input  wire [Q-1:0]            s_hfin,
    input  wire [Q-1:0]            s_stopped,
    input  wire [Q-1:0]            s_done2,
    input  wire [Q-1:0]            s_emitted,
    input  wire [Q-1:0]            s_ovf,
    output reg  [15:0]             c_T,
    output reg  [7:0]              c_Bt,
    output reg                     c_fclr,
    output wire [3:0]              c_cg,
    output wire [3:0]              c_fg,
    output reg                     c_ing,
    output reg                     c_stop,
    output reg                     c_p2,
    output reg                     c_p3,
    output reg                     c_rep,
    output reg  [15:0]             c_st,
    output reg  [Q*(KW+1)-1:0]     c_rem,
    output reg                     c_hclr,
    output reg                     rep_req,
    output reg                     ovf,
    output wire                    busy
);
    localparam integer XW   = CB + 10;              // search sums
    localparam integer QC   = KW + 1;               // coarse quota width
    localparam integer WAIT = 13;                   // search latency after the counts settle (12) + 1
    localparam integer HOLD = 24;                   // fine results ignored after a bucket change
    localparam integer KI   = K;
    localparam [QC-1:0] KQ  = KI[QC-1:0];
    localparam [XW-1:0] QINV = {XW{1'b1}};          // a quota no count reaches
    localparam [2:0] C_ING = 3'd0, C_FL = 3'd1, C_P2 = 3'd2, C_W2 = 3'd3, C_R = 3'd4, C_P3 = 3'd5, C_CLR = 3'd6;

    // status inputs, registered
    reg [Q-1:0] st_last, st_hfin, st_stopped, st_done2, st_emitted, st_ovf;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin st_last <= 0; st_hfin <= 0; st_stopped <= 0; st_done2 <= 0; st_emitted <= 0; st_ovf <= 0; end
        else begin
            st_last <= s_last; st_hfin <= s_hfin; st_stopped <= s_stopped; st_done2 <= s_done2;
            st_emitted <= s_emitted; st_ovf <= s_ovf;
        end
    end

    // the two searches
    reg  [QC-1:0] kq;
    reg  [XW-1:0] qf;
    wire [7:0]    cres_b, fres_b;
    wire [XW-1:0] cres_above, fres_above;
    wire          cres_ok, fres_ok;
    wire [Q*CB-1:0] cres_eq, fres_eq;
    ot_hdc_v41x_sel_su #(.Q(Q), .CB(CB), .QW(QC)) u_cs (
        .clk(clk), .gs(s_gc), .bs(s_bc), .q(kq), .g_out(c_cg),
        .res_b(cres_b), .res_above(cres_above), .res_ok(cres_ok), .res_eq(cres_eq));
    ot_hdc_v41x_sel_su #(.Q(Q), .CB(CB), .QW(XW)) u_fs (
        .clk(clk), .gs(s_gf), .bs(s_bf), .q(qf), .g_out(c_fg),
        .res_b(fres_b), .res_above(fres_above), .res_ok(fres_ok), .res_eq(fres_eq));

    reg  [2:0]    st;
    reg  [5:0]    wcnt, hold_c, hold_f;
    reg           kseen, hf_seen, bs_done;
    reg  [7:0]    bs, ls;
    reg  [QC-1:0] m, t;
    reg  [Q*CB-1:0] eq;
    wire [15:0]   tc = {cres_b, 8'h00};
    wire [15:0]   tf = {c_Bt, fres_b};
    wire          use_c = (st == C_ING) && kseen && (hold_c == 0) && cres_ok;
    wire          use_f = (st == C_ING) && kseen && (hold_c == 0) && (hold_f == 0) && fres_ok;
    wire [QC-1:0] kin_c = ({1'b0, k_in} > KQ) ? KQ : {1'b0, k_in};
    wire [XW-1:0] cab = cres_above;

    // tie quotas: t_q = max(0, t - ties in quarters below q)
    reg  [Q*QC-1:0] rem_d;
    reg  [CB+2:0]   pre;
    integer i;
    always @(*) begin
        pre = 0;
        for (i = 0; i < Q; i = i + 1) begin
            rem_d[QC*i +: QC] = ({{(CB+3-QC){1'b0}}, t} > pre) ? t - pre[QC-1:0] : {QC{1'b0}};
            pre = pre + {3'b000, eq[CB*i +: CB]};
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= C_CLR; wcnt <= 6'd20; c_T <= 0; c_Bt <= 0; c_fclr <= 1'b0; c_ing <= 1'b0; c_stop <= 1'b0;
            c_p2 <= 1'b0; c_p3 <= 1'b0; c_rep <= 1'b0; c_st <= 0; c_rem <= 0; c_hclr <= 1'b0; rep_req <= 1'b0;
            ovf <= 1'b0; kq <= 0; qf <= QINV; hold_c <= 0; hold_f <= 0; kseen <= 1'b0; hf_seen <= 1'b0;
            bs_done <= 1'b0; bs <= 0; ls <= 0; m <= 0; t <= 0; eq <= 0;
        end else begin
            c_fclr <= 1'b0; c_p2 <= 1'b0; c_p3 <= 1'b0; c_hclr <= 1'b0; rep_req <= 1'b0;
            if (hold_c != 0) hold_c <= hold_c - 1'b1;
            if (hold_f != 0) hold_f <= hold_f - 1'b1;
            if (wcnt != 0) wcnt <= wcnt - 1'b1;
            case (st)
                C_ING: begin
                    if (k_ld && !kseen) begin
                        kseen <= 1'b1; kq <= kin_c; hold_c <= 6'd16; hold_f <= 6'd32;
                    end
                    // the running bound
                    if (use_c) begin
                        if (cres_b > c_Bt) begin
                            c_Bt <= cres_b; c_fclr <= 1'b1; hold_f <= HOLD; qf <= QINV;
                        end else if (cres_b == c_Bt)
                            qf <= {{(XW-QC){1'b0}}, kq} - cab;
                    end
                    if (use_c && use_f)          c_T <= (tc > c_T) ? ((tc > tf) ? tc : tf) : ((tf > c_T) ? tf : c_T);
                    else if (use_c && tc > c_T)  c_T <= tc;
                    else if (use_f && tf > c_T)  c_T <= tf;
                    if (&st_last) begin st <= C_FL; c_ing <= 1'b0; c_stop <= 1'b1; hf_seen <= 1'b0; bs_done <= 1'b0; end
                end
                C_FL: begin
                    if ((&st_hfin) && !hf_seen) begin hf_seen <= 1'b1; wcnt <= WAIT; end
                    if (hf_seen && wcnt == 0 && !bs_done) begin
                        bs_done <= 1'b1; bs <= cres_b; m <= kq - cab[QC-1:0];
                    end
                    if (bs_done && (&st_stopped)) begin
                        st <= C_P2; c_rep <= |st_ovf; ovf <= |st_ovf; rep_req <= |st_ovf;
                        c_st <= {bs, 8'h00}; c_p2 <= 1'b1; qf <= {{(XW-QC){1'b0}}, m};
                    end
                end
                C_P2: begin
                    if (&st_done2) begin st <= C_W2; wcnt <= WAIT; end
                end
                C_W2: begin
                    if (wcnt == 0) begin
                        st <= C_R; ls <= fres_b; t <= m - fres_above[QC-1:0]; eq <= fres_eq;
                    end
                end
                C_R: begin
                    st <= C_P3; c_rem <= rem_d; c_st <= {bs, ls}; c_p3 <= 1'b1; rep_req <= c_rep;
                end
                C_P3: begin
                    if (&st_emitted) begin st <= C_CLR; c_hclr <= 1'b1; wcnt <= 6'd20; end
                end
                default: begin                     // C_CLR: the slices clear; stale search results drain
                    c_T <= 0; c_Bt <= 0; qf <= QINV; kseen <= 1'b0; c_rep <= 1'b0; c_stop <= 1'b0;
                    if (wcnt == 0) begin st <= C_ING; c_ing <= 1'b1; end
                end
            endcase
        end
    end
    assign busy = (st != C_ING) || kseen;
endmodule
