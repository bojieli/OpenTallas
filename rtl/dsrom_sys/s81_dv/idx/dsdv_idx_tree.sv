`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-L20DIE (10-19, MU.BAL.SX.3 / S81-L20SPLIT die RTL): the die-side units of the static index RANK TREE.
// A rank's L20 (and L2 / L8 / L14) keys sit on k dies (lower_bk SHARD_K); each die scans its own shard with its 16
// regional readers dsdv_idx_rg (score chain -> the die's selector dsdv_bk_sel, lane 0), and the rank's top-512 is merged
// up a static tree (lower_bk shard_tree): a parent selects over its OWN shard (lane 0) plus ONE LANE PER CHILD (lanes 2 /
// 3, the reader leaves them open: spec om) that carries the child's selected candidates WITH THEIR SCORES as
// HDR + (REBASE + sparse BEAT)* words.  The selector's IDX egress has no scores, so the child re-encodes at the SENDING
// end: dsdv_idx_tx keeps every score its selector ingested (direct-addressed by position window) and turns its own
// IDX egress back into BEAT words.  No credit / ready / back-pressure on any unit port: every job is armed by a compiled
// CTL beat, every output beat leaves on a compiled slot grid, every input lands at a compiled edge; a violation is a
// sticky fault (the static schedule is the compiler's, tools/s81_dv/layer_prog/lower_bk.py job_rank_tree_rd).
//
//   dsdv_idx_vmux  the bk_sel S-face ingress merge: column-4 rung (s_4S), score-chain tail, 2 landed child lanes ->
//                  u_bk_sel.vi_s.  OR of registered inputs, 2 edges pin -> pin; two valid beats in a cycle = fault.
//   dsdv_idx_tx    tree transmit (child die): score store + IDX -> BEAT re-encoder + slot-grid emitter onto the tree
//                  link to the parent (the parent's lane L, the parent's tag).
//   dsdv_idx_qf    query fan-out (every die): tree frame (type 10) from the parent link or the local source ->
//                  forwarded unchanged to both child links; this die's IDX_S job (type 4, ITS spec picked from the
//                  frame's spec table by the die uid) into the reader chain head.
// Pins: every input lands in a flop at the pin, every output leaves a flop.  One clock ck.  Reset rst: async assert,
// 2-flop synchronous release (reset_landing).
// ---------------------------------------------------------------------------------------------------------------------

// ===================================================================================================================
// dsdv_idx_vmux
// ===================================================================================================================
module dsdv_idx_vmux #(
    parameter integer V = 276
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [V-1:0]  i_r,      // column-4 rung from s_4S (unchanged traffic, compiled slots)
    input  wire [V-1:0]  i_s,      // score-chain tail (irg_15 so, after the is_tail relays)
    input  wire [V-1:0]  i_a,      // child lane A (landed tree link)
    input  wire [V-1:0]  i_b,      // child lane B (landed tree link)
    output reg  [V-1:0]  o,        // -> u_bk_sel.vi_s
    output reg           fault     // sticky: two valid beats met in one cycle (a compile error)
);
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
    reg [V-1:0] r_r, r_s, r_a, r_b;
    always @(posedge ck or negedge rn)
        if (!rn) begin r_r[0] <= 1'b0; r_s[0] <= 1'b0; r_a[0] <= 1'b0; r_b[0] <= 1'b0; o[0] <= 1'b0; fault <= 1'b0; end
        else begin
            r_r[0] <= i_r[0]; r_s[0] <= i_s[0]; r_a[0] <= i_a[0]; r_b[0] <= i_b[0];
            o[0] <= r_r[0] | r_s[0] | r_a[0] | r_b[0];
            if ((r_r[0] + r_s[0] + r_a[0] + r_b[0]) > 3'd1) fault <= 1'b1;
        end
    always @(posedge ck) begin
        r_r[V-1:1] <= i_r[V-1:1]; r_s[V-1:1] <= i_s[V-1:1]; r_a[V-1:1] <= i_a[V-1:1]; r_b[V-1:1] <= i_b[V-1:1];
        o[V-1:1] <= (r_r[0] ? r_r[V-1:1] : '0) | (r_s[0] ? r_s[V-1:1] : '0) | (r_a[0] ? r_a[V-1:1] : '0) | (r_b[0] ? r_b[V-1:1] : '0);
    end
endmodule

// ===================================================================================================================
// dsdv_idx_txm: D x 256-b 1R1W memory with a bit write mask, read latency 2 (address edge -> data valid 2 edges later:
// macro read register + bank-select register).  SRAM_MACRO 1: D / 256 x ot_sram_1r1w_256x256_m2_r2c2.
// ===================================================================================================================
module dsdv_idx_txm #(
    parameter integer D = 8192,
    parameter bit SRAM_MACRO = 0
) (
    input  wire                 ck,
    input  wire                 re,
    input  wire [$clog2(D)-1:0] ra,
    output reg  [255:0]         rd,
    input  wire                 we,
    input  wire [$clog2(D)-1:0] wa,
    input  wire [255:0]         wd,
    input  wire [255:0]         wm
);
    localparam integer AW = $clog2(D);
    generate if (SRAM_MACRO) begin : g_m
        localparam integer NB = D / 256;
        initial if (D % 256 != 0 || D < 256) $fatal(1, "dsdv_idx_txm: D must be a multiple of 256");
        wire [255:0] q [0:NB-1];
        reg  [AW-9:0] bs;
        genvar b;
        for (b = 0; b < NB; b = b + 1) begin : g_b
            ot_sram_1r1w_256x256_m2_r2c2 u_mem (
                .clk(ck), .r_ce_in(re && (NB == 1 || ra[AW-1:8] == b)), .r_addr_in(ra[7:0]), .rd_out(q[b]),
                .w_ce_in(we && (NB == 1 || wa[AW-1:8] == b)), .w_addr_in(wa[7:0]), .wd_in(wd), .w_mask_in(wm),
                .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
        end
        // bank select: one-hot AND-OR (no runtime-indexed part-select)
        reg [255:0] mx;
        integer k;
        always @* begin
            mx = 256'd0;
            for (k = 0; k < NB; k = k + 1) if (bs == k) mx = mx | q[k];
        end
        always @(posedge ck) begin
            if (re) bs <= (NB == 1) ? '0 : ra[AW-1:8];
            rd <= mx;
        end
    end else begin : g_b
        reg [255:0] mem [0:D-1];
        reg [255:0] q;
        always @(posedge ck) begin
            if (we) mem[wa] <= (mem[wa] & ~wm) | (wd & wm);
            if (re) q <= mem[ra];
            rd <= q;
        end
    end endgenerate
endmodule

// ===================================================================================================================
// dsdv_idx_tx
// ===================================================================================================================
// CAPTURE (always on; vi = the selector's vi_s, every ingress beat of kind IK): per lane the cursor (HDR / REBASE set
// it, a BEAT takes [cursor, cursor + 16) and advances it by 16) and the held part-0 scores; on a BEAT's part 1 the 16
// scores are written, masked by the word's lane-valid bits, at window address (cursor >> 4) mod D.  Every window the
// compiler gives a selector is 16-ALIGNED (reader lane 0: 16 j0 + 16 w; child lanes: aligned windows), so the positions
// of all lanes of one job share one address space without collision (masked writes; positions are disjoint); a BEAT
// on an unaligned cursor is a fault.  D windows = 16 D positions: the largest transmitting subtree (L20 k 6: dies 3-5,
// 131,073 keys = 8,192 windows; L2 / L14 k 3 leaves 87,382).
// JOB (CTL beat on vo, kind 0, payload p = beat[21 +: 186], p[7:0] == UID, p[10:8] == 2; p[20:16] must be >= 8 so the
// S-tier slices take no action, as the selector's drain CTL): [22:21] L parent lane, [30:23] PT parent tag, [40:31] K,
// [60:41] HB lane HDR base (16-aligned, <= the subtree's lowest position), [68:61] OT this die's selector tag, [84:69]
// DLY first slot = CTL vo edge + 1 + DLY, [87:85] R slot pitch (>= 1), [99:88] SM slots in the grid.
// IDX words of tag OT on vo (kind EK, part 0 + part 1) go to the IDX buffer (IB words); the DONE of tag OT ends the
// job's input.  Lookup: one selected position a cycle, ascending (quarters 0..3 in order = positions ascending, lanes
// hold ascending ranges), score = window word field (idx & 15).  Grouping: 16-aligned windows, REBASE when a window is
// not the lane cursor, BEAT (part 0 scores, part 1 {2, PT, last, lv}); the final BEAT carries last (an empty last BEAT
// when nothing was selected).  Output: HDR (single) first, then the words' beats in order, one beat per grid slot
// (slot s at first + R s, s < SM) when one is ready, else the slot stays empty.  Grid exhausted with beats left = fault.
// st: {fault cause 8 [15:8], 4'b0, done, armed, busy, fault}.
// MUT (bench negative controls only): 1 score of the neighbouring lane field, 2 the final BEAT without last,
// 3 the grid one pitch late, 4 capture without the lane-valid mask.
module dsdv_idx_tx #(
    parameter integer V = 276,
    parameter integer IK = 4,           // selector ingress kind (= the parent's: one die type)
    parameter integer EK = 5,           // selector egress kind
    parameter integer UID = 8'h5C,      // CTL address
    parameter integer D = 8192,         // score windows
    parameter integer IB = 64,          // IDX words buffered (<= 32 + 4 a job)
    parameter bit SRAM_MACRO = 0,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [V-1:0]  vi,      // tap: u_bk_sel.vi_s
    input  wire [V-1:0]  vo,      // tap: u_bk_sel.vo_s
    output reg  [V-1:0]  lo,      // tree link to the parent
    output reg  [15:0]   st
);
    localparam integer AW = $clog2(D), IW = $clog2(IB);
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];

    // ------------------------------------------------------------------ pin registers
    reg [V-1:0] vi_r, vo_r;
    always @(posedge ck or negedge rn)
        if (!rn) begin vi_r[0] <= 1'b0; vo_r[0] <= 1'b0; end
        else begin vi_r[0] <= vi[0]; vo_r[0] <= vo[0]; end
    always @(posedge ck) begin vi_r[V-1:1] <= vi[V-1:1]; vo_r[V-1:1] <= vo[V-1:1]; end

    reg [7:0] fc_set, fc;

    // ------------------------------------------------------------------ capture
    wire        c_v  = vi_r[0] && vi_r[3:1] == 3'(IK);
    wire [1:0]  c_l  = vi_r[5:4];
    wire        c_p1 = vi_r[6], c_sg = vi_r[7];
    wire [3:0]  c_ty = vi_r[19:16];
    reg  [19:0] cur [0:3];
    reg  [255:0] hs [0:3];
    reg         m_we; reg [AW-1:0] m_wa; reg [255:0] m_wd, m_wm;
    reg  [19:0] c_cur; reg [255:0] c_hs;
    integer li;
    always @* begin
        c_cur = 20'd0; c_hs = 256'd0;
        for (li = 0; li < 4; li = li + 1) if (c_l == 2'(li)) begin c_cur = cur[li]; c_hs = hs[li]; end
    end
    function automatic [255:0] lvmask(input [15:0] lv);
        integer i_; lvmask = 256'd0;
        for (i_ = 0; i_ < 16; i_ = i_ + 1) lvmask[16 * i_ +: 16] = {16{lv[i_]}};
    endfunction
    always @(posedge ck or negedge rn)
        if (!rn) begin
            m_we <= 1'b0;
            for (li = 0; li < 4; li = li + 1) cur[li] <= 20'd0;
        end else begin
            m_we <= 1'b0;
            if (c_v && !c_p1 && c_sg && (c_ty == 4'd1 || c_ty == 4'd6))
                cur[c_l] <= vi_r[39:20];                                   // HDR base / REBASE position
            if (c_v && c_p1) begin                                         // BEAT complete
                m_we <= 1'b1; m_wa <= AW'(c_cur[19:4]); m_wd <= c_hs;
                m_wm <= (MUT == 4) ? {256{1'b1}} : lvmask(vi_r[35:20]);
                cur[c_l] <= c_cur + 20'd16;
            end
        end
    always @(posedge ck) if (c_v && !c_p1 && !c_sg) hs[c_l] <= vi_r[275:20];
    wire cap_unal = c_v && c_p1 && c_cur[3:0] != 4'd0;

    // ------------------------------------------------------------------ job (CTL on vo) + IDX / DONE from vo
    wire        o_v   = vo_r[0];
    wire [185:0] cp   = vo_r[21 +: 186];
    wire        o_ctl = o_v && vo_r[3:1] == 3'd0 && cp[7:0] == 8'(UID) && cp[10:8] == 3'd2;
    wire        o_eg  = o_v && vo_r[3:1] == 3'(EK);
    reg         armed, busy, done, in_end;
    reg  [1:0]  j_l; reg [7:0] j_pt, j_ot; reg [9:0] j_k; reg [19:0] j_hb; reg [15:0] j_dly; reg [2:0] j_r; reg [11:0] j_sm;
    reg  [255:0] e_lo; reg e_h;                                        // egress part 0 held
    wire [511:0] e_w  = {vo_r[275:20], e_lo};
    wire        e_cpl = o_eg && vo_r[6] && e_h;                        // an egress word completes this cycle
    wire        e_mine = e_w[507:500] == j_ot;
    // IDX buffer (512-b words, 2 x dsdv_idx_txm halves when SRAM_MACRO, else flops of the behavioural model)
    reg  [IW:0] ib_w, ib_r;
    wire        ib_push = armed && e_cpl && e_mine && e_w[511:508] == 4'd3;
    wire        ib_re;
    wire [511:0] ib_q;
    dsdv_idx_txm #(.D(IB < 256 ? 256 : IB), .SRAM_MACRO(SRAM_MACRO)) u_ib0 (.ck(ck), .re(ib_re), .ra($clog2(IB < 256 ? 256 : IB)'(ib_r[IW-1:0])),
        .rd(ib_q[255:0]), .we(ib_push), .wa($clog2(IB < 256 ? 256 : IB)'(ib_w[IW-1:0])), .wd(e_w[255:0]), .wm({256{1'b1}}));
    dsdv_idx_txm #(.D(IB < 256 ? 256 : IB), .SRAM_MACRO(SRAM_MACRO)) u_ib1 (.ck(ck), .re(ib_re), .ra($clog2(IB < 256 ? 256 : IB)'(ib_r[IW-1:0])),
        .rd(ib_q[511:256]), .we(ib_push), .wa($clog2(IB < 256 ? 256 : IB)'(ib_w[IW-1:0])), .wd(e_w[511:256]), .wm({256{1'b1}}));

    // ------------------------------------------------------------------ lookup
    // word fetch: ib_re at f0 -> ib_q valid 2 edges later -> iw
    reg  [1:0]  fw;                       // fetch in flight (pipeline of 2)
    reg         iw_v;
    assign      ib_re = !iw_v && fw == 2'b00 && ib_r != ib_w && armed;
    reg  [511:0] iw;
    reg  [15:0] lvl;                      // remaining valid elements of iw
    reg  [3:0]  rq_n;                     // result FIFO occupancy + lookups in flight
    wire        rq_room = rq_n < 4'd5;    // result FIFO depth 8: <= 5 queued + 2 in flight + 1 issuing
    // next element: lowest set bit of lvl
    reg  [3:0]  ne; reg ne_v;
    integer bi;
    always @* begin
        ne = 4'd0; ne_v = 1'b0;
        for (bi = 15; bi >= 0; bi = bi - 1) if (lvl[bi]) begin ne = 4'(bi); ne_v = 1'b1; end
    end
    reg  [19:0] ne_idx;
    always @* begin
        ne_idx = 20'd0;
        for (bi = 0; bi < 16; bi = bi + 1) if (ne == 4'(bi)) ne_idx = iw[20 * bi +: 20];
    end
    wire        lk_go = iw_v && ne_v && rq_room;
    reg         m_re; reg [AW-1:0] m_ra;
    wire [255:0] m_rd;
    dsdv_idx_txm #(.D(D), .SRAM_MACRO(SRAM_MACRO)) u_sm (.ck(ck), .re(lk_go), .ra(AW'(ne_idx[19:4])), .rd(m_rd),
        .we(m_we), .wa(m_wa), .wd(m_wd), .wm(m_wm));
    reg  [1:0]  lp_v; reg [19:0] lp_i [0:1];
    // result FIFO (8 x {idx 20, score 16})
    reg  [35:0] rf [0:7];
    reg  [2:0]  rf_w, rf_r; reg [3:0] rf_n;
    wire [3:0]  sel_f = (MUT == 1) ? lp_i[1][3:0] + 4'd1 : lp_i[1][3:0];
    reg  [15:0] lk_s;
    always @* begin
        lk_s = 16'd0;
        for (bi = 0; bi < 16; bi = bi + 1) if (sel_f == 4'(bi)) lk_s = m_rd[16 * bi +: 16];
    end
    wire        rf_pop;
    wire        lk_idle = !iw_v && fw == 2'b00 && lp_v == 2'b00 && ib_r == ib_w;
    always @(posedge ck or negedge rn)
        if (!rn) begin
            fw <= 2'b00; iw_v <= 1'b0; lvl <= 16'd0; lp_v <= 2'b00; rf_w <= 0; rf_r <= 0; rf_n <= 0; ib_r <= 0;
        end else begin
            fw <= {fw[0], ib_re};
            if (ib_re) ib_r <= ib_r + 1'b1;
            if (fw[1]) begin iw_v <= 1'b1; iw <= ib_q; lvl <= ib_q[335:320]; end
            if (lk_go) begin
                lvl[ne] <= 1'b0;
                if ((lvl & ~(16'd1 << ne)) == 16'd0) iw_v <= 1'b0;
            end
            if (iw_v && !ne_v) iw_v <= 1'b0;                              // a word with no valid element
            lp_v <= {lp_v[0], lk_go};
            lp_i[0] <= ne_idx; lp_i[1] <= lp_i[0];
            if (lp_v[1]) begin rf[rf_w] <= {lp_i[1], lk_s}; rf_w <= rf_w + 1'b1; end
            if (rf_pop) rf_r <= rf_r + 1'b1;
            rf_n <= rf_n + (lp_v[1] ? 4'd1 : 4'd0) - (rf_pop ? 4'd1 : 4'd0);
        end
    always @* rq_n = rf_n + 4'(lp_v[0]) + 4'(lp_v[1]);

    // ------------------------------------------------------------------ grouping + beat staging (<= 3 beats)
    reg         wv;                         // window open
    reg  [19:0] w0;  reg [15:0] wlv; reg [255:0] wsc;
    reg  [19:0] lcur;                       // the parent lane's cursor
    reg  [V-1:0] bq [0:3]; reg [2:0] bq_n;  // staged beats (in order), popped at grid slots
    reg         hdr_q, fin;                 // HDR staged / final BEAT staged
    wire [35:0] rh = rf[rf_r];
    wire [19:0] r_i = rh[35:16];
    wire        r_in = wv && r_i[19:4] == w0[19:4];
    wire        bq_pop;
    wire        flush_ok = (bq_n == 3'd0 && !bq_pop) || (bq_n == 3'd1 && bq_pop);   // staging empty after this edge
    assign rf_pop = rf_n != 0 && armed && hdr_q && !fin && (!wv || r_in || flush_ok);
    wire        in_done = in_end && lk_idle && rf_n == 0;
    function automatic [V-1:0] bk(input [1:0] lane, input part, input single, input [11:0] tt, input [255:0] dd);
        bk = {dd, tt, single, part, lane, 3'(IK), 1'b1};
    endfunction
    function automatic [255:0] lane_put(input [255:0] s, input [3:0] f, input [15:0] v);
        integer i_; lane_put = s;
        for (i_ = 0; i_ < 16; i_ = i_ + 1) if (f == 4'(i_)) lane_put[16 * i_ +: 16] = v;
    endfunction

    // ------------------------------------------------------------------ slot grid
    reg  [15:0] tc;                          // cycles since the CTL
    reg  [2:0]  rc;                          // pitch down-counter
    reg  [11:0] sn;                          // slots used
    wire        g_on = armed && tc >= j_dly + ((MUT == 3) ? 16'(j_r) : 16'd0);
    wire        slot = g_on && rc == 3'd0 && sn < j_sm && !done;
    assign      bq_pop = slot && bq_n != 3'd0;
    integer qi_;
    always @(posedge ck or negedge rn)
        if (!rn) begin
            armed <= 1'b0; busy <= 1'b0; done <= 1'b0; in_end <= 1'b0; e_h <= 1'b0; ib_w <= 0; wv <= 1'b0; bq_n <= 3'd0;
            hdr_q <= 1'b0; fin <= 1'b0; tc <= 16'd0; rc <= 3'd0; sn <= 12'd0; lo[0] <= 1'b0; fc_set <= 8'd0; j_r <= 3'd1;
        end else begin
            fc_set <= 8'd0;
            // egress part 0 hold
            if (o_eg && !vo_r[6]) begin e_lo <= vo_r[275:20]; e_h <= 1'b1; end
            else if (o_eg && vo_r[6]) begin
                e_h <= 1'b0;
                if (!e_h) fc_set[0] <= 1'b1;                               // part 1 without part 0
            end
            if (ib_push) ib_w <= ib_w + 1'b1;
            if (ib_push && (ib_w - ib_r) == (IW + 1)'(IB)) fc_set[1] <= 1'b1;   // IDX buffer overflow
            if (armed && e_cpl && e_mine && e_w[511:508] == 4'd4) in_end <= 1'b1;
            // arm
            if (o_ctl) begin
                if (busy) fc_set[2] <= 1'b1;                               // a job while one is active
                if (cp[87:85] == 3'd0 || cp[20:16] < 5'd8) fc_set[3] <= 1'b1;
                armed <= 1'b1; busy <= 1'b1; done <= 1'b0; in_end <= 1'b0;
                j_l <= cp[22:21]; j_pt <= cp[30:23]; j_k <= cp[40:31]; j_hb <= cp[60:41]; j_ot <= cp[68:61];
                j_dly <= cp[84:69]; j_r <= cp[87:85]; j_sm <= cp[99:88];
                tc <= 16'd0; rc <= 3'd0; sn <= 12'd0; wv <= 1'b0; fin <= 1'b0; hdr_q <= 1'b0;
            end else if (armed) begin
                if (tc != 16'hFFFF) tc <= tc + 16'd1;
                if (g_on && !done) begin
                    rc <= (rc == 3'd0) ? j_r - 3'd1 : rc - 3'd1;
                    if (slot) sn <= sn + 12'd1;
                end
            end
            // staging: HDR first
            if (armed && !hdr_q && !o_ctl) begin
                bq[0] <= bk(j_l, 1'b0, 1'b1, {4'd1, j_pt}, {224'd0, j_l, j_k, j_hb});
                bq_n <= 3'd1; hdr_q <= 1'b1; lcur <= j_hb;
            end else begin : g_stage
                reg [2:0] n_; reg [V-1:0] nb [0:3]; integer k_;
                n_ = bq_n;
                for (k_ = 0; k_ < 4; k_ = k_ + 1) nb[k_] = bq[k_];
                if (bq_pop) begin
                    for (k_ = 0; k_ < 3; k_ = k_ + 1) nb[k_] = nb[k_ + 1];
                    n_ = n_ - 3'd1;
                end
                // flush the open window (a result outside it, or the end)
                if (armed && hdr_q && !fin && flush_ok && ((rf_pop && wv && !r_in) || (in_done && rf_n == 0))) begin
                    reg lastf; lastf = in_done && rf_n == 0 && (MUT != 2);
                    if (!wv) begin                                      // nothing selected: one empty last BEAT
                        nb[0] = bk(j_l, 1'b0, 1'b0, {4'd2, j_pt}, 256'd0);
                        nb[1] = bk(j_l, 1'b1, 1'b0, 12'd0, {4'd2, j_pt, 227'd0, lastf, 16'd0});
                        n_ = 3'd2;
                    end else if (w0 != lcur) begin
                        nb[0] = bk(j_l, 1'b0, 1'b1, {4'd6, j_pt}, {236'd0, w0});
                        nb[1] = bk(j_l, 1'b0, 1'b0, {4'd2, j_pt}, wsc);
                        nb[2] = bk(j_l, 1'b1, 1'b0, 12'd0, {4'd2, j_pt, 227'd0, lastf, wlv});
                        n_ = 3'd3;
                    end else begin
                        nb[0] = bk(j_l, 1'b0, 1'b0, {4'd2, j_pt}, wsc);
                        nb[1] = bk(j_l, 1'b1, 1'b0, 12'd0, {4'd2, j_pt, 227'd0, lastf, wlv});
                        n_ = 3'd2;
                    end
                    if (wv) lcur <= w0 + 20'd16;
                    if (in_done && rf_n == 0) fin <= 1'b1;
                end
                for (k_ = 0; k_ < 4; k_ = k_ + 1) bq[k_] <= nb[k_];
                bq_n <= n_;
            end
            // window accumulate / open
            if (rf_pop) begin
                if (r_in) begin wlv <= wlv | (16'd1 << r_i[3:0]); wsc <= lane_put(wsc, r_i[3:0], rh[15:0]); end
                else begin
                    wv <= 1'b1; w0 <= {r_i[19:4], 4'd0}; wlv <= 16'd1 << r_i[3:0];
                    wsc <= lane_put(256'd0, r_i[3:0], rh[15:0]);
                    if (wv && r_i[19:4] < w0[19:4]) fc_set[4] <= 1'b1;   // selection not ascending
                end
            end
            // output
            lo[0] <= bq_pop;
            if (fin && bq_n == 3'd0 && armed && !done) begin done <= 1'b1; busy <= 1'b0; end
            if (armed && !done && sn == j_sm && g_on) fc_set[5] <= 1'b1;   // grid exhausted, job not done
            if (cap_unal) fc_set[6] <= 1'b1;
            if (rf_n == 4'd8 && lp_v[1] && !rf_pop) fc_set[7] <= 1'b1;
        end
    always @(posedge ck) lo[V-1:1] <= bq_pop ? bq[0][V-1:1] : '0;
    always @(posedge ck or negedge rn)
        if (!rn) begin fc <= 8'd0; st <= 16'd0; end
        else begin fc <= fc | fc_set; st <= {fc, 4'd0, done, armed, busy, fc != 8'd0}; end
endmodule

// ===================================================================================================================
// dsdv_idx_qf
// ===================================================================================================================
// TREE FRAME (type 10, SVC FRAME PROTOCOL v1 header: [511:508] 10, [502:495] tag, [491:480] len = NS + 64, [458:449]
// user, [3:0] NS): NS spec words (4 entries a word, entry e = [128 e +: 128]: [127] valid, [126:119] die uid, [106:0]
// the dsdv_idx_rg IDX_S spec of that die: B, N, k, KB, T0, P, ik, om), then the 64 query words.  Every word goes to
// both child links unchanged (pin -> pin 3 edges).  The reader chain head gets, in the cycle of the last spec word,
// this die's job header (type 4, the frame's tag / user, len 64, spec = the entry with uid == this die's uid) and
// then the 64 query words (pin -> pin 3 edges, the same latency as the children: END reaches every die's reader 0 at a
// fixed offset from END at the parent).  No matching entry: nothing goes to the readers.  Frames of other types pass
// to the readers unchanged (and to the children).  qs (local source) and ql (parent link) both valid in a cycle = fault.
// MUT (bench only): 1 the entry of the next uid is taken.
module dsdv_idx_qf #(
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [7:0]    uid,        // die tree uid (die configuration input)
    input  wire [512:0]  qs,         // local frame source (s_3S)
    input  wire [512:0]  ql,         // parent tree link
    output reg  [512:0]  qr,         // -> irg_00 qi
    output reg  [512:0]  qc0,        // -> child link 0
    output reg  [512:0]  qc1,        // -> child link 1
    output reg  [3:0]    st          // {no-entry seen, bad frame, collision, fault}
);
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
    reg [512:0] qs_r, ql_r, s1;
    reg [7:0]   me;
    always @(posedge ck or negedge rn)
        if (!rn) begin qs_r[0] <= 1'b0; ql_r[0] <= 1'b0; s1[0] <= 1'b0; qc0[0] <= 1'b0; qc1[0] <= 1'b0; me <= 8'd0; end
        else begin
            qs_r[0] <= qs[0]; ql_r[0] <= ql[0]; s1[0] <= qs_r[0] | ql_r[0];
            qc0[0] <= s1[0]; qc1[0] <= s1[0]; me <= uid;
        end
    always @(posedge ck) begin
        qs_r[512:1] <= qs[512:1]; ql_r[512:1] <= ql[512:1];
        s1[512:1] <= (qs_r[0] ? qs_r[512:1] : 512'd0) | (ql_r[0] ? ql_r[512:1] : 512'd0);
        qc0[512:1] <= s1[512:1]; qc1[512:1] <= s1[512:1];
    end
    wire        v  = s1[0];
    wire [511:0] d = s1[512:1];
    // framing
    reg         infr, tree, hit;
    reg  [11:0] left;
    reg  [3:0]  nsl;                    // spec words left
    reg  [511:0] hdr;
    reg  [106:0] spec;
    wire [7:0]  want = (MUT == 1) ? me + 8'd1 : me;
    reg  [106:0] w_spec; reg w_hit;
    integer e;
    always @* begin
        w_spec = 107'd0; w_hit = 1'b0;
        for (e = 0; e < 4; e = e + 1)
            if (d[128 * e + 127] && d[128 * e + 119 +: 8] == want) begin w_spec = d[128 * e +: 107]; w_hit = 1'b1; end
    end
    reg [3:0] fl;
    always @(posedge ck or negedge rn)
        if (!rn) begin infr <= 1'b0; tree <= 1'b0; hit <= 1'b0; left <= 0; nsl <= 0; qr[0] <= 1'b0; fl <= 4'd0; st <= 4'd0; end
        else begin
            qr[0] <= 1'b0;
            if (qs_r[0] && ql_r[0]) fl[1] <= 1'b1;
            if (v) begin
                if (!infr) begin                                          // header
                    infr <= d[491:480] != 12'd0; left <= d[491:480];
                    tree <= d[511:508] == 4'd10; hit <= 1'b0;
                    if (d[511:508] == 4'd10) begin
                        hdr <= d; nsl <= d[3:0];
                        if (d[3:0] == 4'd0 || d[491:480] != 12'(64) + 12'(d[3:0])) fl[2] <= 1'b1;
                    end else qr[0] <= 1'b1;                               // other frames pass
                end else begin
                    left <= left - 12'd1;
                    if (left == 12'd1) infr <= 1'b0;
                    if (tree && nsl != 4'd0) begin                       // spec word
                        nsl <= nsl - 4'd1;
                        if (w_hit) begin spec <= w_spec; hit <= 1'b1; end
                        if (nsl == 4'd1) begin
                            if (w_hit || hit) qr[0] <= 1'b1;             // this die's header goes out now
                            else fl[3] <= 1'b1;
                        end
                    end else if (!tree || hit) qr[0] <= 1'b1;            // query words (or another frame's payload)
                end
            end
            st <= {fl[3], fl[2], fl[1], fl[1] | fl[2]};
        end
    // data path of qr (header rewrite in the cycle of the last spec word)
    wire [106:0] my_spec = w_hit ? w_spec : spec;
    always @(posedge ck) begin
        if (v && infr && tree && nsl == 4'd1) begin
            qr[512:1] <= 512'd0;
            qr[512:509] <= 4'd4; qr[503:496] <= hdr[502:495]; qr[492:481] <= 12'd64; qr[459:450] <= hdr[458:449];
            qr[107:1] <= my_spec;
        end else qr[512:1] <= d;
    end
endmodule
