`timescale 1ns/1ps
`default_nettype none
// HGI-1 IDX.INDEX frame adapter, WIDE-LANE form (el1011-hbm-idxs 2026-10-11; ot_hgi_idx_unit IXW = 1).  Same frame
// semantics and the same selector ports as ot_hgi_idx_index (spec G18; see that file for the operand contract), but every
// VM transfer rides the die's 32-lane VM wide groups (the ot_hgi_vm_lanestation client format of the SU / SFU) instead of
// the one packet client.  Why (tput-hbm-1011, DS-V4.1 AR 1M L24: 9,291 cycles vs 1,080 priced): the packet adapter walks
// the 2,048-entry candidate table one entry a cycle with one read outstanding (~5.5k cycles), streams the 512 query
// sectors at ~0.5 sector a cycle (~1k) and compacts the top-k one lane a cycle (512) -- not the 64 keys/cycle scorers.
//
// Structure (physical spec: claude-takeover-20261007/el1011-hbm-idxs.log 10-11 20:55):
//   READ  one in-order read sequence B (head weights, a sector a chunk) -> C (keep_en: an id chunk, then the value chunk
//         of the same entries) -> A (512 query sectors).  A chunk = 1..4 sectors inside one 4-lane group (lane = sector
//         mod NL, group = sector[LB-1:2]; HBM B2: NL 8 = the slice-local lane group); every issued chunk is logged {kind, slot, count, sector} and the consumer
//         pops the logged chunks IN ORDER from per-lane landing FIFOs (DL deep, lane-local) through one 8:1 group gather
//         a cycle (no 32:1 crossbar).  Per-lane issue gate: the VM lane credit (LQ) and landing room (DL).  Nothing
//         upstream waits on a later log entry, so the sequence cannot deadlock.
//   KEEP  32 candidates a cycle pair (id chunk held, value chunk consumed): K1 fields + value test -> K2 q div 3
//         (x 43,691 >> 17, exact below 2^16) -> K3 rank / range match -> a 32-bit match buffer drained one match a cycle
//         into a registered (quarter, bit) keep set.  C.stride must be a multiple of 32 words (the compiler's 2,048) so
//         an id chunk and its value chunk share slots; otherwise the frame faults (fail-closed).
//         fs leaves at the frame start; kin beats leave when the walk is complete; the LAST query block is held until
//         every kin beat has left, so each scorer has its keep bitmap before its 32nd head (qloaded).
//   QUERY A sectors -> 8-sector ring -> one 32-word block a cycle on the selector's 4 qb credits (double-buffered).
//   OUT   top-k beats in two 8-lane halves (prefix-count compaction), candidate beats 2 lanes, into four sector packers
//         (O, R, D ids, D values; <= 1 sector a cycle each) and a 4-requester lane arbiter on the wide write group
//         (per-lane credits); done after the selector's done, the last beats, the packer flush and every write done.
// Every die-facing input lands in a flop, every output leaves a flop; wide datapath registers carry no reset.
module ot_hgi_idx_index_w #(
    parameter integer MUT = 0,      // bench mutants: 1 head weight of the next head, 2 R written from the wrong lane
    parameter integer DL  = 2,      // landing FIFO depth a read lane (power of 2; 64 sectors in flight >= 4 a cycle x RT 16)
    parameter integer LQ  = 8,      // VM lane queue credits a lane (read and write groups)
    parameter integer NL  = 8       // lanes of the wide groups (HBM B2 slice-local lane group: 8, lane b <-> bank b = sector[2:0])
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go_i,
    input  wire [11:0]   k_i,
    input  wire          cand_en_i, keep_en_i,
    input  wire [31:0]   n_i,
    input  wire [6:0]    rank_i,
    input  wire [19:0]   pos_i,
    input  wire [17:0]   a_base_i, b_base_i, c_base_i, o_base_i, r_base_i, d_base_i,
    input  wire [17:0]   d_stride_i,
    input  wire [17:0]   c_stride_i,
    input  wire [11:0]   c_n_i,
    input  wire          has_r_i,
    output reg           done,
    output reg           fault,
    // VM wide read group (NL lanes, lane b <-> bank b = sector mod NL)
    output reg  [NL*16-1:0]  wrq,
    input  wire [NL-1:0]     wrq_cr,
    input  wire [NL*257-1:0] wrr,
    output reg               rg_req,
    input  wire              rg_gnt,
    // VM wide write group
    output reg  [NL*280-1:0] wwq,
    input  wire [NL-1:0]     wwq_cr,
    input  wire [NL-1:0]     wwq_done,
    output reg               wg_req,
    input  wire              wg_gnt,
    // native selector
    output reg  [89:0]   fs,
    output reg  [1047:0] qb,
    input  wire          qbr,
    output reg  [344:0]  kin,
    input  wire [611:0]  to,
    output reg           toc,
    input  wire [71:0]   co,
    output reg           coc,
    input  wire [1:0]    ev
);
    localparam [1:0] K_B = 2'd0, K_CI = 2'd1, K_CV = 2'd2, K_A = 2'd3;
    localparam integer DLB = $clog2(DL), CB = $clog2(LQ) + 1, LB = $clog2(NL), NG = NL / 4, GB = (NG > 1) ? $clog2(NG) : 1;
    integer i, l, p;
    // local reset: rst_n lands in a 2-flop synchroniser (asserts at once, releases on the clock); every control register
    // resets from this flop, the wide datapath registers carry no reset
    reg rs1, rn;
    always @(posedge clk or negedge rst_n) if (!rst_n) {rn, rs1} <= 2'b00; else {rn, rs1} <= {rs1, 1'b1};
    // frame command pin registers (the record station holds them for the whole frame; go is a pulse)
    reg go; reg [11:0] k; reg cand_en, keep_en; reg [31:0] n; reg [6:0] rank; reg [19:0] pos;
    reg [17:0] a_base, b_base, c_base, o_base, r_base, d_base, d_stride, c_stride; reg [11:0] c_n; reg has_r;
    always @(posedge clk or negedge rn) if (!rn) go <= 1'b0; else go <= go_i;
    always @(posedge clk) begin
        k <= k_i; cand_en <= cand_en_i; keep_en <= keep_en_i; n <= n_i; rank <= rank_i; pos <= pos_i;
        a_base <= a_base_i; b_base <= b_base_i; c_base <= c_base_i; o_base <= o_base_i; r_base <= r_base_i;
        d_base <= d_base_i; d_stride <= d_stride_i; c_stride <= c_stride_i; c_n <= c_n_i; has_r <= has_r_i;
    end
    // ================================================================ pin registers (inputs)
    reg [NL-1:0] rcr_q, wcr_q, wdn_q, rr_v; reg [NL*256-1:0] rr_d; reg rgnt_q, wgnt_q, qbr_q; reg [1:0] ev_q;
    always @(posedge clk or negedge rn)
        if (!rn) begin rcr_q <= '0; wcr_q <= '0; wdn_q <= '0; rr_v <= '0; rgnt_q <= 1'b0; wgnt_q <= 1'b0; qbr_q <= 1'b0;
            ev_q <= 2'd0; end
        else begin
            rcr_q <= wrq_cr; wcr_q <= wwq_cr; wdn_q <= wwq_done; rgnt_q <= rg_gnt; wgnt_q <= wg_gnt; qbr_q <= qbr; ev_q <= ev;
            for (l = 0; l < NL; l = l + 1) rr_v[l] <= wrr[l*257 + 256];
        end
    always @(posedge clk) for (l = 0; l < NL; l = l + 1) rr_d[l*256 +: 256] <= wrr[l*257 +: 256];
    // selector output beats land in pin flops before the beat FIFOs
    reg to_v, co_v; reg [611:1] to_d; reg [71:1] co_d;
    always @(posedge clk or negedge rn) if (!rn) begin to_v <= 1'b0; co_v <= 1'b0; end else begin to_v <= to[0]; co_v <= co[0]; end
    always @(posedge clk) begin to_d <= to[611:1]; co_d <= co[71:1]; end
    // ================================================================ frame state
    localparam S_IDLE = 2'd0, S_RUN = 2'd1, S_FLUSH = 2'd2;
    reg [1:0] st;
    reg bad, sel_done, to_last, co_last;
    reg [15:0] wts [0:31];
    // ================================================================ read issue (static streams B -> C -> A)
    reg        is_on;
    reg [1:0]  is_kind;                     // K_B / K_CI (id chunk then its value chunk) / K_A
    reg        is_cv;                       // C: the value chunk of the current id chunk is next
    reg [14:0] is_sec, is_end;              // next sector / last sector of the current stream
    reg [14:0] c_s0, c_s1, a_s0, cs8;       // stream bounds, value offset in sectors (frame constants)
    reg [CB-1:0]  rcred [0:NL-1];           // VM read lane credits
    reg [DLB:0]   rres  [0:NL-1];            // landing slots reserved (issued, not yet popped)
    localparam integer LGW = 2 + 2 + 3 + 13;               // kind, slot, count, sector[14:2] (group = sector[LB-1:2])
    reg [LGW-1:0] lg [0:31]; reg [5:0] lg_n; reg [4:0] lg_h, lg_t;
    // Two-stage issuer (timing: the chunk walk -- room / count / stream bounds / value offset / lane mask -- is a
    // full cycle of 15-bit arithmetic; the issue cycle sees only the registered descriptor against lane credits).
    // Stage W computes the next chunk descriptor from the walker state into ch_* whenever the descriptor register
    // is empty or being issued this cycle, so a back-to-back walk still issues one chunk per cycle.
    reg [1:0]  nx_kind; reg [14:0] nx_sec; reg [2:0] nx_cnt; reg [NL-1:0] nx_mask; reg nx_last; reg [2:0] room;
    reg        pd_v;                        // ch_* holds a walked, not yet issued chunk
    reg [1:0]  ch_kind; reg [14:0] ch_sec; reg [2:0] ch_cnt; reg [NL-1:0] ch_mask; reg ch_ok, ch_v;
    always @* begin
        nx_kind = (is_kind == K_CI && is_cv) ? K_CV : is_kind;
        room = 3'd4 - {1'b0, is_sec[1:0]};
        if (is_kind == K_B) nx_cnt = 3'd1;
        else if ({12'd0, room} > is_end - is_sec) nx_cnt = 3'(is_end - is_sec + 15'd1);
        else nx_cnt = room;
        nx_sec = (nx_kind == K_CV) ? is_sec + cs8 : is_sec;
        nx_last = is_sec + {12'd0, nx_cnt} > is_end;
        nx_mask = '0;
        for (l = 0; l < 4; l = l + 1)
            if (l >= nx_sec[1:0] && l < nx_sec[1:0] + nx_cnt) nx_mask[(NG > 1 ? 4 * nx_sec[LB-1:2] : 0) + l] = 1'b1;
    end
    always @* begin
        ch_v = pd_v && st == S_RUN && !bad && lg_n != 6'd32 && rgnt_q;
        ch_ok = 1'b1;
        for (l = 0; l < NL; l = l + 1)
            if (ch_mask[l] && (rcred[l] == '0 || rres[l] == (DLB+1)'(DL))) ch_ok = 1'b0;
    end
    wire ch_go = ch_v && ch_ok;
    wire wk_go = st == S_RUN && is_on && !bad && (!pd_v || ch_go);
    // ================================================================ landing FIFOs (lane-local)
    reg [255:0] lm [0:NL*DL-1]; reg [DLB:0] lwp [0:NL-1], lrp [0:NL-1];   // lm: lane l entry e at l * DL + e
    reg [NL-1:0] lne, lpop;
    always @* for (l = 0; l < NL; l = l + 1) lne[l] = lwp[l] != lrp[l];
    always @(posedge clk) for (l = 0; l < NL; l = l + 1) if (rr_v[l]) lm[l*DL + lwp[l][DLB-1:0]] <= rr_d[l*256 +: 256];
    always @(posedge clk or negedge rn)
        if (!rn) for (l = 0; l < NL; l = l + 1) begin lwp[l] <= '0; lrp[l] <= '0; end
        else for (l = 0; l < NL; l = l + 1) begin
            if (rr_v[l]) lwp[l] <= lwp[l] + 1'b1;
            if (lpop[l]) lrp[l] <= lrp[l] + 1'b1;
        end
    // ================================================================ consumer stage G (one group a cycle, log order)
    wire [LGW-1:0] lgh = lg[lg_h];
    wire [1:0] h_kind = lgh[19:18]; wire [1:0] h_slot = lgh[17:16];
    wire [2:0] h_cnt = lgh[15:13]; wire [12:0] h_shi = lgh[12:0];
    wire [GB-1:0] h_grp = (NG > 1) ? h_shi[GB-1:0] : '0;
    reg [NL-1:0] h_mask; reg h_rdy;
    always @* begin
        h_mask = '0;
        for (l = 0; l < 4; l = l + 1) if (l >= h_slot && l < h_slot + h_cnt) h_mask[4 * h_grp + l] = 1'b1;
        h_rdy = lg_n != 6'd0 && ((lne & h_mask) == h_mask);
    end
    reg g_v; reg [1:0] g_kind; reg [1:0] g_slot; reg [2:0] g_cnt; reg [12:0] g_shi; reg [1023:0] g_d;
    wire g_take;
    wire g_load = h_rdy && (!g_v || g_take);
    always @* lpop = g_load ? h_mask : '0;
    always @(posedge clk or negedge rn) if (!rn) g_v <= 1'b0; else if (!g_v || g_take) g_v <= h_rdy;
    always @(posedge clk) if (g_load) begin
        g_kind <= h_kind; g_slot <= h_slot; g_cnt <= h_cnt; g_shi <= h_shi;
        for (l = 0; l < 4; l = l + 1) g_d[l*256 +: 256] <= lm[(4 * h_grp + l)*DL + lrp[4 * h_grp + l][DLB-1:0]];
    end
    wire [255:0] g_sec0 = g_d[g_slot*256 +: 256];
    // ================================================================ KEEP walk
    reg h0_v; reg [1023:0] h0_d; reg [1:0] h0_slot; reg [2:0] h0_cnt; reg [12:0] h0_shi;      // the held id chunk
    reg k1_v; reg [31:0] k1_ok; reg [14:0] k1_q [0:31]; reg [4:0] k1_lo [0:31];
    reg k2_v; reg [31:0] k2_ok; reg [13:0] k2_ord [0:31]; reg [14:0] k2_q [0:31]; reg [4:0] k2_lo [0:31];
    reg k3_v; reg [31:0] k3_m; reg [10:0] k3_ord [0:31];
    reg [31:0] mb; reg [10:0] mb_ord [0:31];
    reg [4:0] pk; reg pk_v;
    always @* begin
        pk_v = 1'b0; pk = 5'd0;
        for (l = 31; l >= 0; l = l - 1) if (mb[l]) begin pk_v = 1'b1; pk = 5'(l); end
    end
    wire [31:0] mb_left = mb & ~((pk_v ? 32'd1 : 32'd0) << pk);
    reg mb_z;                               // registered: the match buffer is empty
    wire k3_ld = k3_v && mb_z;
    wire k3_free = !k3_v || k3_ld;
    wire k2_free = !k2_v || k3_free;
    wire k1_free = !k1_v || k2_free;
    wire g_ci = g_v && g_kind == K_CI, g_cv = g_v && g_kind == K_CV;
    wire k1_ld = g_cv && k1_free;          // the value chunk meets its held id chunk
    reg ks_v; reg [1:0] ks_q; reg [8:0] ks_b; reg [10:0] ks_ord;
    reg [1367:0] keep;                      // bit ord = quarter ord div 342, bit ord mod 342
    reg [11:0] c_iss, c_done;               // C chunks (id + value) issued / consumed this frame
    reg [17:0] cw_w; reg [31:0] cv_w; reg [14:0] cq;
    always @(posedge clk or negedge rn) begin
        if (!rn) begin h0_v <= 1'b0; k1_v <= 1'b0; k2_v <= 1'b0; k3_v <= 1'b0; mb <= 32'd0; mb_z <= 1'b1; ks_v <= 1'b0; end
        else begin
            if (g_ci && !h0_v) h0_v <= 1'b1; else if (k1_ld) h0_v <= 1'b0;
            if (k1_free) k1_v <= k1_ld;
            if (k2_free) k2_v <= k1_v;
            if (k3_free) k3_v <= k2_v;
            mb <= k3_ld ? k3_m : mb_left;
            mb_z <= (k3_ld ? k3_m : mb_left) == 32'd0;
            ks_v <= pk_v;
        end
    end
    always @(posedge clk) begin
        if (g_ci && !h0_v) begin h0_d <= g_d; h0_slot <= g_slot; h0_cnt <= g_cnt; h0_shi <= g_shi; end
        if (k1_ld)
            for (p = 0; p < 32; p = p + 1) begin
                cw_w = {h0_shi, 2'(p / 8), 3'(p % 8)};
                cv_w = g_d[p*32 +: 32];
                k1_ok[p] <= (p / 8) >= h0_slot && (p / 8) < h0_slot + h0_cnt && cw_w >= c_base &&
                            (cw_w - c_base) < {6'd0, c_n} && h0_d[p*32 + 20 +: 12] == 12'd0 && cv_w != 32'hFF80_0000;
                k1_q[p] <= h0_d[p*32 + 5 +: 15];
                k1_lo[p] <= h0_d[p*32 +: 5];
            end
        if (k2_free && k1_v)
            for (p = 0; p < 32; p = p + 1) begin
                k2_ok[p] <= k1_ok[p];
                k2_ord[p] <= 14'(({17'd0, k1_q[p]} * 32'd43691) >> 17);
                k2_q[p] <= k1_q[p];
                k2_lo[p] <= k1_lo[p];
            end
        if (k3_free && k2_v)
            for (p = 0; p < 32; p = p + 1) begin
                k3_m[p] <= k2_ok[p] && {2'(k2_q[p] - 15'(k2_ord[p] + {k2_ord[p], 1'b0})), k2_lo[p]} == rank &&
                           k2_ord[p] < 14'd1368;
                k3_ord[p] <= k2_ord[p][10:0];
            end
        if (k3_ld) for (p = 0; p < 32; p = p + 1) mb_ord[p] <= k3_ord[p];
        if (pk_v) ks_ord <= mb_ord[pk];
    end
    wire k_busy = h0_v || k1_v || k2_v || k3_v || !mb_z || ks_v;
    wire walk_done = !keep_en || (is_kind == K_A || !is_on) && !(pd_v && ch_kind != K_A) && c_iss == c_done && !k_busy && !g_ci && !g_cv;
    // ================================================================ QUERY (A sectors -> 8-sector ring -> blocks)
    reg [255:0] ring [0:7]; reg [2:0] rg_wp, rg_rp; reg [3:0] rg_n;
    reg qfull; reg [1023:0] qdat; reg [7:0] qmade, qsent; reg [2:0] qcred;
    reg kin_sent; reg [1:0] kq; reg [2:0] kgap; reg fs_pend;
    wire q_send = st == S_RUN && qfull && qcred != 3'd0 && (qsent != 8'd127 || !keep_en || kin_sent);
    wire q_mk = rg_n >= 4'd4 && (!qfull || q_send) && qmade != 8'd128;
    wire a_take = g_v && g_kind == K_A && ({1'b0, rg_n} - (q_mk ? 5'd4 : 5'd0) + {2'd0, g_cnt}) <= 5'd8;
    assign g_take = g_v && (g_kind == K_B || (g_kind == K_CI && !h0_v) || k1_ld || a_take);
    // ================================================================ OUTPUT (to / co beats -> packers -> write lanes)
    reg [611:0] tf [0:7]; reg [2:0] tfh, tft; reg [3:0] tfn;
    reg [71:0]  cf [0:7]; reg [2:0] cfh, cft; reg [3:0] cfn;
    reg hb;
    reg t1_v; reg [7:0] t1_lv; reg [31:0] t1_o [0:7]; reg [31:0] t1_r [0:7]; reg [2:0] t1_pf [0:7]; reg [3:0] t1_n;
    reg t2_v; reg [3:0] t2_n; reg [255:0] t2_o, t2_r;
    reg d1_v; reg [3:0] d1_n; reg [255:0] d1_i, d1_x;
    wire [3:0] pk_rdy, pk_ev, pk_empty; wire [3*15-1+15:0] pk_sec; wire [4*256-1:0] pk_d; wire [4*8-1:0] pk_m;
    reg [3:0] e_take; reg flush;
    wire t2_go = t2_v && pk_rdy[0] && (pk_rdy[1] || !has_r);
    wire t2_free = !t2_v || t2_go;
    wire t1_free = !t1_v || t2_free;
    wire d1_go = d1_v && pk_rdy[2] && pk_rdy[3];
    wire d1_free = !d1_v || d1_go;
    wire [611:0] th = tf[tfh]; wire [71:0] ch = cf[cfh];
    wire t_ld = st == S_RUN && tfn != 4'd0 && t1_free;
    wire t_pop = t_ld && hb;
    wire c_pop = st == S_RUN && cfn != 4'd0 && d1_free;
    wire flush_go = flush && (&pk_rdy);
    ot_hgi_idx_wpack u_p0 (.clk(clk), .rst_n(rn), .ld(st == S_IDLE && go), .base(o_base), .in_v(t2_go), .in_n(t2_n),
        .in_w(t2_o), .flush(flush_go), .rdy(pk_rdy[0]), .e_v(pk_ev[0]), .e_sec(pk_sec[0 +: 15]), .e_d(pk_d[0 +: 256]),
        .e_m(pk_m[0 +: 8]), .e_take(e_take[0]), .empty(pk_empty[0]));
    ot_hgi_idx_wpack u_p1 (.clk(clk), .rst_n(rn), .ld(st == S_IDLE && go), .base(r_base), .in_v(t2_go && has_r),
        .in_n(t2_n), .in_w(t2_r), .flush(flush_go), .rdy(pk_rdy[1]), .e_v(pk_ev[1]), .e_sec(pk_sec[15 +: 15]),
        .e_d(pk_d[256 +: 256]), .e_m(pk_m[8 +: 8]), .e_take(e_take[1]), .empty(pk_empty[1]));
    ot_hgi_idx_wpack u_p2 (.clk(clk), .rst_n(rn), .ld(st == S_IDLE && go), .base(d_base), .in_v(d1_go), .in_n(d1_n),
        .in_w(d1_i), .flush(flush_go), .rdy(pk_rdy[2]), .e_v(pk_ev[2]), .e_sec(pk_sec[30 +: 15]), .e_d(pk_d[512 +: 256]),
        .e_m(pk_m[16 +: 8]), .e_take(e_take[2]), .empty(pk_empty[2]));
    ot_hgi_idx_wpack u_p3 (.clk(clk), .rst_n(rn), .ld(st == S_IDLE && go), .base(d_base + d_stride), .in_v(d1_go),
        .in_n(d1_n), .in_w(d1_x), .flush(flush_go), .rdy(pk_rdy[3]), .e_v(pk_ev[3]), .e_sec(pk_sec[45 +: 15]),
        .e_d(pk_d[768 +: 256]), .e_m(pk_m[24 +: 8]), .e_take(e_take[3]), .empty(pk_empty[3]));
    // write lane arbitration (fixed priority O, R, D ids, D values; one sector a lane a cycle; per-lane credits)
    reg [CB-1:0] wcred [0:NL-1];
    reg [11:0] w_out;
    reg [NL-1:0] w_used; reg [5:0] wdn_cnt; reg [LB-1:0] e_ln; reg [2:0] w_src [0:NL-1];
    always @* begin
        w_used = '0; e_take = 4'd0;
        for (l = 0; l < NL; l = l + 1) w_src[l] = 3'd4;
        for (i = 0; i < 4; i = i + 1) begin
            e_ln = pk_sec[i*15 +: LB];
            if (pk_ev[i] && wgnt_q && wg_req && !w_used[e_ln] && wcred[e_ln] != '0) begin
                e_take[i] = 1'b1; w_used[e_ln] = 1'b1; w_src[e_ln] = 3'(i);
            end
        end
        wdn_cnt = 6'd0;
        for (l = 0; l < NL; l = l + 1) wdn_cnt = wdn_cnt + {5'd0, wdn_q[l]};
    end
    // ================================================================ main sequential block
    reg [3:0] cntv; reg [3:0] pref; reg [255:0] o_acc, r_acc;
    always @(posedge clk) begin                 // synchronous reset from the local rn flop (datapath fields hold, no reset)
        if (!rn) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; bad <= 1'b0; is_on <= 1'b0; is_cv <= 1'b0; pd_v <= 1'b0;
            lg_n <= 6'd0; lg_h <= 5'd0; lg_t <= 5'd0; rg_req <= 1'b0; wg_req <= 1'b0;
            fs <= 90'd0; qb[0] <= 1'b0; kin[0] <= 1'b0; toc <= 1'b0; coc <= 1'b0; fs_pend <= 1'b0; qfull <= 1'b0;
            for (l = 0; l < NL; l = l + 1) begin wrq[l*16 + 15] <= 1'b0; wwq[l*280 + 279] <= 1'b0; end
            kin_sent <= 1'b0; kq <= 2'd0; kgap <= 3'd0; flush <= 1'b0;
            rg_n <= 4'd0; rg_wp <= 3'd0; rg_rp <= 3'd0; qmade <= 8'd0; qsent <= 8'd0; qcred <= 3'd4;
            tfn <= 4'd0; tfh <= 3'd0; tft <= 3'd0; cfn <= 4'd0; cfh <= 3'd0; cft <= 3'd0; hb <= 1'b0;
            t1_v <= 1'b0; t2_v <= 1'b0; d1_v <= 1'b0; w_out <= 12'd0; sel_done <= 1'b0; to_last <= 1'b0; co_last <= 1'b0;
            c_iss <= 12'd0; c_done <= 12'd0;
            for (l = 0; l < NL; l = l + 1) begin rcred[l] <= CB'(LQ); rres[l] <= '0; wcred[l] <= CB'(LQ); end
            keep <= '0;
        end else begin
            done <= 1'b0; fault <= 1'b0; fs[0] <= 1'b0; qb[0] <= 1'b0; kin[0] <= 1'b0; toc <= 1'b0; coc <= 1'b0;
            for (l = 0; l < NL; l = l + 1) begin wrq[l*16 + 15] <= 1'b0; wwq[l*280 + 279] <= 1'b0; end
            // ---- selector inputs (captured always: the selector sends only against credits)
            if (to_v) begin tf[tft] <= {to_d, 1'b1}; tft <= tft + 3'd1; end
            if (co_v) begin cf[cft] <= {co_d, 1'b1}; cft <= cft + 3'd1; end
            if (ev_q[0] && st != S_IDLE) sel_done <= 1'b1;
            if (ev_q[1] && st != S_IDLE) bad <= 1'b1;
            if (st != S_IDLE) begin
                tfn <= tfn + {3'd0, to_v} - {3'd0, t_pop};
                cfn <= cfn + {3'd0, co_v} - {3'd0, c_pop};
                if ((to_v && tfn == 4'd8 && !t_pop) || (co_v && cfn == 4'd8 && !c_pop)) bad <= 1'b1;
            end
            // ---- lane credits / landing reservations / writes outstanding
            for (l = 0; l < NL; l = l + 1) begin
                rcred[l] <= rcred[l] + CB'(rcr_q[l]) - CB'(ch_go && ch_mask[l]);
                rres[l] <= rres[l] + (DLB+1)'(ch_go && ch_mask[l]) - (DLB+1)'(lpop[l]);
                wcred[l] <= wcred[l] + CB'(wcr_q[l]) - CB'(w_used[l]);
            end
            w_out <= w_out + 12'(e_take[0]) + 12'(e_take[1]) + 12'(e_take[2]) + 12'(e_take[3]) - 12'(wdn_cnt);
            // per-lane output register: lane l takes the requester granted to it (constant-index lvalues)
            for (l = 0; l < NL; l = l + 1) if (w_used[l])
                wwq[l*280 +: 280] <= {1'b1, pk_sec[w_src[l][1:0]*15 +: 15], pk_d[w_src[l][1:0]*256 +: 256], pk_m[w_src[l][1:0]*8 +: 8]};
            // ---- read issue
            if (ch_go) begin
                for (l = 0; l < NL; l = l + 1)
                    if (ch_mask[l]) wrq[l*16 +: 16] <= {1'b1, ch_sec[14:2], 2'(l % 4)};
                lg[lg_t] <= {ch_kind, ch_sec[1:0], ch_cnt, ch_sec[14:2]};
                lg_t <= lg_t + 5'd1;
                if (ch_kind == K_CV) c_iss <= c_iss + 12'd1;
            end
            // ---- chunk walk (stage W)
            if (wk_go) begin
                ch_kind <= nx_kind; ch_sec <= nx_sec; ch_cnt <= nx_cnt; ch_mask <= nx_mask;
            end
            if (wk_go) pd_v <= 1'b1; else if (ch_go) pd_v <= 1'b0;
            if (wk_go) begin
                if (nx_kind == K_CI) is_cv <= 1'b1;
                else begin
                    is_cv <= 1'b0;
                    if (nx_last) begin                                     // stream exhausted -> next stream
                        if (is_kind == K_B && keep_en) begin is_kind <= K_CI; is_sec <= c_s0; is_end <= c_s1; end
                        else if (is_kind != K_A) begin is_kind <= K_A; is_sec <= a_s0; is_end <= a_s0 + 15'd511; end
                        else is_on <= 1'b0;
                    end else is_sec <= is_sec + {12'd0, nx_cnt};
                end
            end
            lg_n <= lg_n + 6'(ch_go) - 6'(g_load);
            if (g_load) lg_h <= lg_h + 5'd1;
            // ---- B chunk: head weights
            if (g_v && g_kind == K_B)
                for (i = 0; i < 32; i = i + 1)
                    if (((b_base + 18'(i)) >> 3) == {3'd0, g_shi, g_slot}) begin
                        if (g_sec0[((b_base + 18'(i)) & 18'd7) * 32 +: 16] != 16'd0) bad <= 1'b1;
                        wts[i] <= g_sec0[((b_base + 18'(i)) & 18'd7) * 32 + 16 +: 16];
                    end
            // ---- keep walk bookkeeping and keep bit set (match pick -> registered quarter / bit -> one bit)
            if (k1_ld) c_done <= c_done + 12'd1;
            for (l = 0; l < 1368; l = l + 1) if (ks_v && ks_ord == 11'(l)) keep[l] <= 1'b1;
            // ---- A sectors into the ring, blocks out
            if (a_take)
                for (i = 0; i < 4; i = i + 1)
                    if (i < g_cnt) ring[rg_wp + 3'(i)] <= g_d[(g_slot + 2'(i)) * 256 +: 256];
            if (a_take) rg_wp <= rg_wp + g_cnt;
            if (q_send) begin
                qb <= {wts[(MUT == 1) ? 5'(qsent / 4 + 1) : 5'(qsent / 4)], qdat, 2'(qsent % 4), 5'(qsent / 4), 1'b1};
                qsent <= qsent + 8'd1; qfull <= 1'b0;
            end
            if (q_mk) begin
                qdat <= {ring[rg_rp + 3'd3], ring[rg_rp + 3'd2], ring[rg_rp + 3'd1], ring[rg_rp]};
                qfull <= 1'b1; rg_rp <= rg_rp + 3'd4; qmade <= qmade + 8'd1;
            end
            rg_n <= rg_n + (a_take ? {1'b0, g_cnt} : 4'd0) - (q_mk ? 4'd4 : 4'd0);
            qcred <= qcred - 3'(q_send) + 3'(qbr_q);
            // ---- kin after the walk
            if (st == S_RUN && keep_en && !kin_sent && walk_done) begin
                if (kgap != 3'd0) kgap <= kgap - 3'd1;
                else begin
                    kin <= {keep[kq*342 +: 342], kq, 1'b1}; kgap <= 3'd3;
                    if (kq == 2'd3) kin_sent <= 1'b1; else kq <= kq + 2'd1;
                end
            end
            // ---- top-k half beats -> T1 -> T2 (compacted)
            if (t1_free) t1_v <= t_ld;
            if (t_ld) begin
                for (l = 0; l < 8; l = l + 1) begin
                    p = hb ? l + 8 : l;
                    t1_lv[l] <= th[4 + p];
                    t1_o[l] <= {12'd0, th[292 + 20*p +: 20]};
                    pref = (MUT == 2) ? 4'(p + 1) : 4'(p);
                    t1_r[l] <= th[20 + pref] ? 32'hFF80_0000 : {th[36 + 16*pref +: 16], 16'd0};
                end
                // prefix counts of the half beat's valid lanes (parallel popcounts, not a chained increment)
                for (l = 0; l < 8; l = l + 1) begin
                    cntv = 4'd0;
                    for (i = 0; i < 8; i = i + 1) if (i < l) cntv = cntv + 4'(th[4 + (hb ? i + 8 : i)]);
                    t1_pf[l] <= cntv[2:0];
                end
                cntv = 4'd0;
                for (i = 0; i < 8; i = i + 1) cntv = cntv + 4'(th[4 + (hb ? i + 8 : i)]);
                t1_n <= cntv;
                hb <= !hb;
                if (hb) begin tfh <= tfh + 3'd1; toc <= 1'b1; if (th[1]) to_last <= 1'b1; end
            end
            if (t2_free) t2_v <= t1_v;
            if (t2_free && t1_v) begin
                o_acc = 256'd0; r_acc = 256'd0;
                for (i = 0; i < 8; i = i + 1)              // output word i = the valid lane whose prefix count is i
                    for (l = 0; l < 8; l = l + 1)
                        if (t1_lv[l] && t1_pf[l] == 3'(i)) begin o_acc[i*32 +: 32] = o_acc[i*32 +: 32] | t1_o[l];
                                                                 r_acc[i*32 +: 32] = r_acc[i*32 +: 32] | t1_r[l]; end
                t2_n <= t1_n; t2_o <= o_acc; t2_r <= r_acc;
            end
            // ---- candidate beats -> D1 (2 lanes compacted)
            if (d1_free) d1_v <= c_pop;
            if (c_pop) begin
                cfh <= cfh + 3'd1; coc <= 1'b1; if (ch[1]) co_last <= 1'b1;
                d1_n <= 4'(ch[4]) + 4'(ch[5]);
                d1_i <= {192'd0, 32'(ch[55 +: 17]), ch[4] ? 32'(ch[38 +: 17]) : 32'(ch[55 +: 17])};
                d1_x <= {192'd0, {ch[22 +: 16], 16'd0}, ch[4] ? {ch[6 +: 16], 16'd0} : {ch[22 +: 16], 16'd0}};
            end
            if (flush_go) flush <= 1'b0;
            // ---- frame FSM
            case (st)
                S_IDLE: if (go) begin
                    if (k == 12'd0 || k > 12'd512 || n > 32'd10944 || rank >= 7'd96 || a_base[2:0] != 3'd0 ||
                        (keep_en && c_stride[4:0] != 5'd0)) fault <= 1'b1;
                    else begin
                        st <= S_RUN; bad <= 1'b0; sel_done <= 1'b0; to_last <= 1'b0; co_last <= !cand_en;
                        is_on <= 1'b1; is_cv <= 1'b0; pd_v <= 1'b0; is_kind <= K_B; is_sec <= b_base[17:3];
                        is_end <= 15'((b_base + 18'd31) >> 3);
                        c_s0 <= c_base[17:3]; c_s1 <= 15'((c_base + {6'd0, c_n} - 18'd1) >> 3); a_s0 <= a_base[17:3];
                        cs8 <= c_stride[17:3];
                        rg_req <= 1'b1; fs_pend <= 1'b1;
                        qmade <= 8'd0; qsent <= 8'd0; qfull <= 1'b0; qcred <= 3'd4; rg_n <= 4'd0; rg_wp <= 3'd0; rg_rp <= 3'd0;
                        kq <= 2'd0; kgap <= 3'd0; kin_sent <= 1'b0; c_iss <= 12'd0; c_done <= 12'd0;
                        keep <= '0;
                        tfn <= 4'd0; cfn <= 4'd0; tfh <= 3'd0; tft <= 3'd0; cfh <= 3'd0; cft <= 3'd0; hb <= 1'b0;
                    end
                end
                S_RUN: begin
                    if (fs_pend) begin
                        fs_pend <= 1'b0;
                        fs <= {keep_en, cand_en, k[9:0], n[13:0], rank, pos, 4'd0, 32'd0, 1'b1};
                    end
                    if (!is_on && !pd_v && lg_n == 6'd0 && !g_v) rg_req <= 1'b0;
                    if (t1_v || t2_v || d1_v || tfn != 4'd0 || cfn != 4'd0) wg_req <= 1'b1;
                    if (bad) begin st <= S_IDLE; fault <= 1'b1; rg_req <= 1'b0; wg_req <= 1'b0; end
                    else if (sel_done && to_last && co_last && tfn == 4'd0 && cfn == 4'd0 && !t1_v && !t2_v && !d1_v &&
                             qsent == 8'd128 && !is_on && !pd_v && lg_n == 6'd0 && !g_v) begin
                        st <= S_FLUSH; flush <= 1'b1; wg_req <= 1'b1;
                    end
                end
                S_FLUSH: if (!flush && (&pk_empty) && e_take == 4'd0 && w_out == 12'd0) begin
                    st <= S_IDLE; done <= 1'b1; wg_req <= 1'b0; rg_req <= 1'b0;
                end
                default: st <= S_IDLE;
            endcase
        end
    end
`ifndef SYNTHESIS
    always @(posedge clk) if (rn) begin
        for (l = 0; l < NL; l = l + 1) if (rr_v[l] && lwp[l] - lrp[l] == (DLB+1)'(DL))
            $fatal(1, "ot_hgi_idx_index_w: landing FIFO overflow lane %0d (%m)", l);
    end
`endif
endmodule

// One output sector packer: up to 8 words a cycle appended at the running word address; a sector leaves (registered
// e_v / e_sec / e_d / e_m, word mask for a partial first or last sector) when the run crosses its end or on flush.
module ot_hgi_idx_wpack (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         ld,            // frame start: take base, clear
    input  wire [17:0]  base,
    input  wire         in_v,          // caller holds in_v only while rdy
    input  wire [3:0]   in_n,          // 0..8 words
    input  wire [255:0] in_w,          // words 0..in_n-1
    input  wire         flush,         // caller holds flush only while rdy: emit the partial sector
    output wire         rdy,
    output reg          e_v,
    output reg  [14:0]  e_sec,
    output reg  [255:0] e_d,
    output reg  [7:0]   e_m,
    input  wire         e_take,
    output wire         empty
);
    reg [17:0] a; reg [255:0] b0; reg [7:0] m0;
    reg [511:0] b; reg [15:0] m; reg [2:0] off; integer x;
    assign rdy = !e_v || e_take;
    assign empty = !e_v && m0 == 8'd0;
    always @(posedge clk) begin
        if (!rst_n) begin e_v <= 1'b0; m0 <= 8'd0; end
        else begin
            if (e_take) e_v <= 1'b0;
            if (ld) begin a <= base; m0 <= 8'd0; end
            else if (in_v || flush) begin
                b = {256'd0, b0}; m = {8'd0, m0}; off = a[2:0];
                if (in_v)
                    for (x = 0; x < 8; x = x + 1)
                        if (x < in_n) begin b[({1'b0, off} + 4'(x)) * 32 +: 32] = in_w[x*32 +: 32]; m[{1'b0, off} + 4'(x)] = 1'b1; end
                if ((in_v && {1'b0, off} + in_n >= 4'd8) || (flush && m[7:0] != 8'd0)) begin
                    e_v <= 1'b1; e_sec <= a[17:3]; e_d <= b[255:0]; e_m <= m[7:0];
                    b0 <= b[511:256]; m0 <= m[15:8];
                end else begin
                    b0 <= b[255:0]; m0 <= m[7:0];
                end
                if (in_v) a <= a + {14'd0, in_n};
            end
        end
    end
endmodule
`default_nettype wire
