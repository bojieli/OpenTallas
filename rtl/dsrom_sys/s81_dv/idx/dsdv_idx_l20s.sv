`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-RTLGAP/RG-L20 (10-21, MU.S81.L20.RTL): the L20 SPLIT die RTL for the 72-frame MU die (dv_plan --idxrd 4).
//
// What the 72-frame die (claude/s81-die72-g3-1021 4ee613834, IDX4 overlay) already carries for the index rank tree:
//   16 x dsfd_ctrl_rg3 rrq/rrd <-> 8 x dsdv_idx_rg3 rqo/rri (the old B1 svc splice is native in rg3/ctrl_rg3),
//   iq_src_l0/l1 s_3S iq -> iqf qs (the 513-b query frame on TWO PARALLEL 276-b lanes, 276 + 237: no serializer; owner
//   10-20 forbids 2-cycle edge serialization, so the old "513 -> 2 x 276 serializer" item is closed by the 2-lane split),
//   iqf ql / qc0 / qc1 (rank-tree parent / child query links: die ports), bk_sel = dsdv_bk_sel_vm (dsdv_idx_vmux in front
//   of dsdv_bk_sel: column rung + score-chain tail is_tail + child lanes ca / cb: die ports).
// What was MISSING for the split (a die that is a CHILD in the k = 3 / k = 6 rank tree cannot send its merged result):
//   the tree transmitter (score store + IDX -> BEAT re-encoder + slot-grid emitter, dsdv_idx_tx of S81-L20DIE) and its
//   output lane to the parent die.  This file adds it as part of the bk_sel die master (it taps the selector's vi_s /
//   vo_s, so it lives in the same block, same clock, no new die link inside the die):
//
//   dsdv_bk_sel_vmtx   die master = dsdv_bk_sel_vm ports + tl_o[275:0] (tree lane to the parent die: die port, the
//                      parent's ca / cb) + tx_st[15:0] (status: die status port).  u_vm / u_sel are unchanged
//                      (dsdv_idx_vmux, dsdv_bk_sel); u_tx = dsdv_idx_tx_n32.
//   dsdv_idx_tx_n32    safe-design successor of dsdv_idx_tx: SAME ports, SAME output stream at the SAME edges (the
//                      compiler's lower_bk job_rank_tree_rd schedule and its prices are unchanged: +0 edges), rebuilt
//                      for the safe-design checklist:
//                        * reset only on control / valid bits, 5 ot_rst_relay leaves (2-stage sync + 1 relay, <= 25
//                          loads each); datapath (hs, cur, e_lo, iw, score buffers, job fields, counters set at arm)
//                          unreset;
//                        * every wide write / load enable is a REGISTERED one-hot select in KEPT copies of <= 32 loads,
//                          computed one edge early from the pin inputs (hs field writes, c_hs lane mux, e_lo load, iw
//                          load, job-field loads on the CTL, score-store bank select);
//                        * the 4 x 276-b beat staging shift register (one comb pop select into 1,104 muxes + 275 output
//                          gates) is replaced by a 2-buffer window store (ping-pong; the closing window is never copied)
//                          + a 1-entry beat descriptor; the output beat is built from registered kept selects (the next
//                          cycle's grid slot and beat type are precomputed from the next state), so lo leaves a flop
//                          and no single select drives more than 32 data gates;
//                        * all storage > 2 kb in SRAM macros (score store 8 x ot_sram_1r1w_1024x256, IDX buffer 2);
//                          flops: two 256-b window buffers, 4 x 256-b part-0 holds, 8 x 36-b result FIFO (< 2 kb each).
//   dsdv_idx_txm_n32   the score store: dsdv_idx_txm with the bank select as kept one-hot copies (8 a bank, 32 bits a
//                      copy) instead of one 3-b register decoded into 8 x 256 AND gates.
//
// Static schedule: no credit / ready / back-pressure anywhere; every job is armed by a compiled CTL beat (uid 0x5C op 2)
// and every output beat leaves on the compiled slot grid (TX_SM 1600, R 1); violations are sticky faults (st).
// Clock: one clock ck (= the bk_sel block clock clk); the tree lane tl_o crosses dies through the die-to-die link
// (landed at the parent's ca / cb, fixed latency <= 729 edges: lower_bk LEG).
// ---------------------------------------------------------------------------------------------------------------------

// ===================================================================================================================
// dsdv_idx_txm_n32: score store (D windows x 256 b), 1 read + 1 masked write a cycle, read data 2 edges after re.
// ===================================================================================================================
module dsdv_idx_txm_n32 #(
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
        localparam integer NB = D / 1024;
        initial if (D % 1024 != 0 || D < 1024) $fatal(1, "dsdv_idx_txm_n32: D must be a multiple of 1024");
        wire [255:0] q [0:NB-1];
        genvar b, c;
        for (b = 0; b < NB; b = b + 1) begin : g_b
            ot_sram_1r1w_1024x256_m2_r2c2 u_mem (
                .clk(ck), .r_ce_in(re && (NB == 1 || ra[AW-1:10] == b)), .r_addr_in(ra[9:0]), .rd_out(q[b]),
                .w_ce_in(we && (NB == 1 || wa[AW-1:10] == b)), .w_addr_in(wa[9:0]), .wd_in(wd), .w_mask_in(wm),
                .rr_en(2'b0), .rr_addr(18'b0), .cr_en(2'b0), .cr_sel(16'b0));
        end
        // bank select of the read issued at edge t: valid in cycle t + 1 (the only cycle the consumer samples rd at
        // edge t + 2).  Loaded every edge from ra (no enable), 8 kept copies a bank, each gating 32 data bits.
        (* keep = "true" *) reg [NB*8-1:0] bsk;
        always @(posedge ck) begin : g_bs
            integer k_;
            for (k_ = 0; k_ < NB * 8; k_ = k_ + 1) bsk[k_] <= (NB == 1) ? 1'b1 : (ra[AW-1:10] == (k_ / 8));
        end
        reg [255:0] mx;
        integer k, g;
        always @* begin
            mx = 256'd0;
            for (k = 0; k < NB; k = k + 1)
                for (g = 0; g < 8; g = g + 1)
                    mx[32 * g +: 32] = mx[32 * g +: 32] | (q[k][32 * g +: 32] & {32{bsk[8 * k + g]}});
        end
        always @(posedge ck) rd <= mx;
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
// dsdv_idx_tx_n32: tree transmit (child die).  Function, job word and fault codes = dsdv_idx_tx (dsdv_idx_tree.sv):
// CAPTURE every ingress beat of kind IK on vi (per lane cursor, part-0 scores held, part 1 writes the 16 scores masked
// by lane-valid at window (cursor >> 4) mod D); JOB = CTL beat on vo (kind 0, p[7:0] == UID, p[10:8] == 2): [22:21] L,
// [30:23] PT, [40:31] K, [60:41] HB, [68:61] OT, [84:69] DLY, [87:85] R, [99:88] SM; IDX words of tag OT on vo -> IDX
// buffer, DONE ends the input; lookup one selected position a cycle; group into 16-aligned windows (REBASE when the
// window is not the lane cursor, BEAT part 0 scores, part 1 {2, PT, last, lv}); output HDR first, then the beats, one a
// grid slot (first slot = CTL vo edge + 1 + DLY, pitch R, SM slots).  st: {fault cause [15:8], 4'b0, done, armed, busy,
// fault}.  MUT (bench negative controls only): 1 score of the neighbouring lane field, 2 the final BEAT without last,
// 3 the grid one pitch late, 4 capture without the lane-valid mask.
// ===================================================================================================================
module dsdv_idx_tx_n32 #(
    parameter integer V = 276,
    parameter integer IK = 4,
    parameter integer EK = 5,
    parameter integer UID = 8'h5C,
    parameter integer D = 8192,
    parameter integer IB = 64,
    parameter bit SRAM_MACRO = 0,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst,       // active low (as dsdv_idx_tx / the bk_sel rst_n)
    input  wire [V-1:0]  vi,        // tap: u_sel.vi_s (the vmux output)
    input  wire [V-1:0]  vo,        // tap: u_sel.vo_s
    output reg  [V-1:0]  lo,        // tree link to the parent die
    output reg  [15:0]   st
);
    localparam integer AW = $clog2(D), IW = $clog2(IB);
    localparam integer IBD = (IB < 1024) ? 1024 : IB, IBA = $clog2(IBD);

    // ------------------------------------------------------------------ reset forest (control / valid bits only)
    // rl[0] pins + lookup control (24), rl[1] job / staging control (19), rl[2] CTL copies + faults (23),
    // rl[3] output selects + lo[0] (25), rl[4] status (16).
    wire [4:0] rl;
    ot_rst_relay #(.REGIONS(5), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(ck), .rst_n_in(rst), .rst_n(rl));

    // ------------------------------------------------------------------ pin registers
    reg [V-1:0] vi_r, vo_r;
    always @(posedge ck or negedge rl[0])
        if (!rl[0]) begin vi_r[0] <= 1'b0; vo_r[0] <= 1'b0; end
        else begin vi_r[0] <= vi[0]; vo_r[0] <= vo[0]; end
    always @(posedge ck) begin vi_r[V-1:1] <= vi[V-1:1]; vo_r[V-1:1] <= vo[V-1:1]; end

    // ------------------------------------------------------------------ one-edge-early selects from the pins (kept)
    wire       n_p0w  = vi[0] && vi[3:1] == 3'(IK) && !vi[6] && !vi[7];      // BEAT part 0 of kind IK
    wire       n_octl = vo[0] && vo[3:1] == 3'd0 && vo[28:21] == 8'(UID) && vo[31:29] == 3'd2;
    wire       n_ep0  = vo[0] && vo[3:1] == 3'(EK) && !vo[6];                 // egress part 0
    (* keep = "true" *) reg [31:0] hsw;      // [8 l + c]: hs[l][32 c +: 32] write enable
    (* keep = "true" *) reg [31:0] shs;      // [8 l + c]: lane l one-hot for m_wd[32 c +: 32]
    (* keep = "true" *) reg [3:0]  scl_m, scl_w;
    (* keep = "true" *) reg [7:0]  eph;      // e_lo[32 c +: 32] load
    (* keep = "true" *) reg [6:0]  okk;      // the CTL (o_ctl) copies, see the job block
    always @(posedge ck) begin : g_pre
        integer l_, c_;
        for (l_ = 0; l_ < 4; l_ = l_ + 1) begin
            for (c_ = 0; c_ < 8; c_ = c_ + 1) begin
                hsw[8 * l_ + c_] <= n_p0w && vi[5:4] == 2'(l_);
                shs[8 * l_ + c_] <= vi[5:4] == 2'(l_);
            end
            scl_m[l_] <= vi[5:4] == 2'(l_);
            scl_w[l_] <= vi[5:4] == 2'(l_);
        end
        eph <= {8{n_ep0}};
    end
    always @(posedge ck or negedge rl[2])
        if (!rl[2]) okk <= 7'd0; else okk <= {7{n_octl}};

    reg [7:0] fc_set, fc;

    // ------------------------------------------------------------------ capture
    wire        c_v  = vi_r[0] && vi_r[3:1] == 3'(IK);
    wire        c_p1 = vi_r[6], c_sg = vi_r[7];
    wire [3:0]  c_ty = vi_r[19:16];
    reg  [19:0] cur [0:3];
    reg  [255:0] hs [0:3];
    reg  [19:0] c_cur;
    integer li;
    always @* begin
        c_cur = 20'd0;
        for (li = 0; li < 4; li = li + 1) c_cur = c_cur | (cur[li] & {20{scl_m[li]}});
    end
    function automatic [255:0] lvmask(input [15:0] lv);
        integer i_; lvmask = 256'd0;
        for (i_ = 0; i_ < 16; i_ = i_ + 1) lvmask[16 * i_ +: 16] = {16{lv[i_]}};
    endfunction
    always @(posedge ck) begin : g_cap
        integer l_, c_;
        for (l_ = 0; l_ < 4; l_ = l_ + 1) begin
            if (scl_w[l_] && c_v && !c_p1 && c_sg && (c_ty == 4'd1 || c_ty == 4'd6)) cur[l_] <= vi_r[39:20];
            else if (scl_w[l_] && c_v && c_p1) cur[l_] <= c_cur + 20'd16;
            for (c_ = 0; c_ < 8; c_ = c_ + 1) if (hsw[8 * l_ + c_]) hs[l_][32 * c_ +: 32] <= vi_r[20 + 32 * c_ +: 32];
        end
    end
    // score-store write port: free-running data / address / mask (used only with m_we), m_we = a BEAT part 1
    reg         m_we; reg [AW-1:0] m_wa; reg [255:0] m_wd, m_wm;
    always @(posedge ck or negedge rl[0]) if (!rl[0]) m_we <= 1'b0; else m_we <= c_v && c_p1;
    always @(posedge ck) begin : g_mw
        integer l_, c_; reg [31:0] x_;
        m_wa <= AW'(c_cur[19:4]);
        m_wm <= (MUT == 4) ? {256{1'b1}} : lvmask(vi_r[35:20]);
        for (c_ = 0; c_ < 8; c_ = c_ + 1) begin
            x_ = 32'd0;
            for (l_ = 0; l_ < 4; l_ = l_ + 1) x_ = x_ | (hs[l_][32 * c_ +: 32] & {32{shs[8 * l_ + c_]}});
            m_wd[32 * c_ +: 32] <= x_;
        end
    end
    wire cap_unal = c_v && c_p1 && c_cur[3:0] != 4'd0;

    // ------------------------------------------------------------------ job fields (CTL on vo), kept-copy enables
    wire         o_v  = vo_r[0];
    wire [185:0] cp   = vo_r[21 +: 186];
    wire         o_eg = o_v && vo_r[3:1] == 3'(EK);
    reg  [1:0]  j_l; reg [7:0] j_pt, j_ot; reg [9:0] j_k; reg [19:0] j_hb; reg [15:0] j_dly; reg [2:0] j_r; reg [11:0] j_sm;
    always @(posedge ck) begin
        if (okk[0]) begin j_l <= cp[22:21]; j_pt <= cp[30:23]; j_k <= cp[40:31]; j_r <= cp[87:85]; end
        if (okk[1]) j_hb <= cp[60:41];
        if (okk[2]) begin j_ot <= cp[68:61]; j_sm <= cp[99:88]; end
        if (okk[3]) j_dly <= cp[84:69];
    end

    // ------------------------------------------------------------------ egress capture -> IDX buffer
    reg  [255:0] e_lo;
    always @(posedge ck) begin : g_elo
        integer c_;
        for (c_ = 0; c_ < 8; c_ = c_ + 1) if (eph[c_]) e_lo[32 * c_ +: 32] <= vo_r[20 + 32 * c_ +: 32];
    end
    reg          armed, busy, done, in_end, e_h;
    wire [511:0] e_w    = {vo_r[275:20], e_lo};
    wire         e_cpl  = o_eg && vo_r[6] && e_h;
    wire         e_mine = e_w[507:500] == j_ot;
    reg  [IW:0]  ib_w, ib_r;
    wire         ib_push = armed && e_cpl && e_mine && e_w[511:508] == 4'd3;
    wire         ib_re;
    wire [511:0] ib_q;
    dsdv_idx_txm #(.D(IBD), .SRAM_MACRO(SRAM_MACRO)) u_ib0 (.ck(ck), .re(ib_re), .ra(IBA'(ib_r[IW-1:0])),
        .rd(ib_q[255:0]), .we(ib_push), .wa(IBA'(ib_w[IW-1:0])), .wd(e_w[255:0]), .wm({256{1'b1}}));
    dsdv_idx_txm #(.D(IBD), .SRAM_MACRO(SRAM_MACRO)) u_ib1 (.ck(ck), .re(ib_re), .ra(IBA'(ib_r[IW-1:0])),
        .rd(ib_q[511:256]), .we(ib_push), .wa(IBA'(ib_w[IW-1:0])), .wd(e_w[511:256]), .wm({256{1'b1}}));

    // ------------------------------------------------------------------ lookup
    reg  [1:0]  fw;
    (* keep = "true" *) reg [9:0] fwk;        // fw[1] copies: iw[32 c +: 32] load
    reg         iw_v;
    assign      ib_re = !iw_v && fw == 2'b00 && ib_r != ib_w && armed;
    reg  [319:0] iw;                          // 16 x 20-b selected positions (bits [335:320] = lv go to lvl)
    reg  [15:0] lvl;
    reg  [3:0]  rq_n;
    wire        rq_room = rq_n < 4'd5;
    reg  [3:0]  ne; reg ne_v;
    integer bi_;
    always @* begin
        ne = 4'd0; ne_v = 1'b0;
        for (bi_ = 15; bi_ >= 0; bi_ = bi_ - 1) if (lvl[bi_]) begin ne = 4'(bi_); ne_v = 1'b1; end
    end
    reg  [19:0] ne_idx;
    always @* begin
        ne_idx = 20'd0;
        for (bi_ = 0; bi_ < 16; bi_ = bi_ + 1) ne_idx = ne_idx | (iw[20 * bi_ +: 20] & {20{ne == 4'(bi_)}});
    end
    wire        lk_go = iw_v && ne_v && rq_room;
    wire [255:0] m_rd;
    dsdv_idx_txm_n32 #(.D(D), .SRAM_MACRO(SRAM_MACRO)) u_sm (.ck(ck), .re(lk_go), .ra(AW'(ne_idx[19:4])), .rd(m_rd),
        .we(m_we), .wa(m_wa), .wd(m_wd), .wm(m_wm));
    reg  [1:0]  lp_v; reg [19:0] lp_i [0:1];
    reg  [35:0] rf [0:7];
    reg  [2:0]  rf_w, rf_r; reg [3:0] rf_n;
    wire [3:0]  sel_f = (MUT == 1) ? lp_i[1][3:0] + 4'd1 : lp_i[1][3:0];
    reg  [15:0] lk_s;
    always @* begin
        lk_s = 16'd0;
        for (bi_ = 0; bi_ < 16; bi_ = bi_ + 1) lk_s = lk_s | (m_rd[16 * bi_ +: 16] & {16{sel_f == 4'(bi_)}});
    end
    wire        rf_pop;
    wire        lk_idle = !iw_v && fw == 2'b00 && lp_v == 2'b00 && ib_r == ib_w;
    always @(posedge ck or negedge rl[0])
        if (!rl[0]) begin
            fw <= 2'b00; iw_v <= 1'b0; lp_v <= 2'b00; rf_w <= 3'd0; rf_r <= 3'd0; rf_n <= 4'd0; ib_r <= '0;
        end else begin
            fw <= {fw[0], ib_re};
            if (ib_re) ib_r <= ib_r + 1'b1;
            if (fw[1]) iw_v <= 1'b1;
            if (lk_go && (lvl & ~(16'd1 << ne)) == 16'd0) iw_v <= 1'b0;
            if (iw_v && !ne_v) iw_v <= 1'b0;
            lp_v <= {lp_v[0], lk_go};
            if (lp_v[1]) rf_w <= rf_w + 1'b1;
            if (rf_pop) rf_r <= rf_r + 1'b1;
            rf_n <= rf_n + (lp_v[1] ? 4'd1 : 4'd0) - (rf_pop ? 4'd1 : 4'd0);
        end
    always @(posedge ck) begin : g_lk
        integer c_;
        fwk <= {10{fw[0]}};
        for (c_ = 0; c_ < 10; c_ = c_ + 1) if (fwk[c_]) iw[32 * c_ +: 32] <= ib_q[32 * c_ +: 32];
        if (fw[1]) lvl <= ib_q[335:320];
        if (lk_go) lvl[ne] <= 1'b0;
        lp_i[0] <= ne_idx; lp_i[1] <= lp_i[0];
        if (lp_v[1]) rf[rf_w] <= {lp_i[1], lk_s};
    end
    always @* rq_n = rf_n + 4'(lp_v[0]) + 4'(lp_v[1]);

    // ------------------------------------------------------------------ window store (2 buffers) + beat descriptor
    reg         wv;                          // a window is open (in buffer act)
    reg         act;                         // buffer of the open window
    reg  [19:0] w0c;                         // the open window's base
    reg  [19:0] w0b [0:1]; reg [15:0] wlvb [0:1]; reg [255:0] wscb [0:1];
    reg  [19:0] lcur;                        // the parent lane's cursor
    reg  [2:0]  bq_n;                        // beats left in the descriptor
    reg  [1:0]  bix;                         // next beat index of the descriptor
    reg         d_h, d_buf, d_rb, d_em, d_last;   // descriptor: HDR / buffer / REBASE first / empty / last
    reg         hdr_q, fin;
    reg  [15:0] tc; reg [2:0] rc; reg [11:0] sn;
    reg         slot_q;                      // = the grid slot of this cycle (precomputed from the next state)
    wire [35:0] rh   = rf[rf_r];
    wire [19:0] r_i  = rh[35:16];
    wire        r_in = wv && r_i[19:4] == w0c[19:4];
    wire        pop  = slot_q && bq_n != 3'd0;
    wire        flush_ok = (bq_n == 3'd0 && !pop) || (bq_n == 3'd1 && pop);
    assign      rf_pop = rf_n != 4'd0 && armed && hdr_q && !fin && (!wv || r_in || flush_ok);
    wire        in_done = in_end && lk_idle && rf_n == 4'd0;
    wire        fl  = armed && hdr_q && !fin && flush_ok && ((rf_pop && wv && !r_in) || (in_done && rf_n == 4'd0));
    wire        o_ctl_c = okk[4];            // control copy
    wire        o_ctl_t = okk[5];            // tc / rc / sn copy
    wire        o_ctl_j = okk[6];            // next-state job-field copy
    wire        g_on = armed && tc >= j_dly + ((MUT == 3) ? 16'(j_r) : 16'd0);
    wire        lastf = in_done && rf_n == 4'd0 && (MUT != 2);
    wire        nb_t = wv ? ~act : act;      // buffer a new window opens in
    // next state (mirrors dsdv_idx_tx's update order exactly)
    reg         nx_armed, nx_busy, nx_done, nx_in_end, nx_wv, nx_act, nx_hdr_q, nx_fin, nx_slot;
    reg  [15:0] nx_tc; reg [2:0] nx_rc; reg [11:0] nx_sn; reg [2:0] nx_bq_n; reg [1:0] nx_bix;
    reg         nx_d_h, nx_d_buf, nx_d_rb, nx_d_em, nx_d_last; reg [19:0] nx_lcur, nx_w0c;
    reg  [15:0] nx_dly; reg [11:0] nx_sm; reg [2:0] nx_r;
    always @* begin
        nx_armed = armed; nx_busy = busy; nx_done = done; nx_in_end = in_end; nx_wv = wv; nx_act = act;
        nx_hdr_q = hdr_q; nx_fin = fin; nx_tc = tc; nx_rc = rc; nx_sn = sn; nx_bq_n = bq_n; nx_bix = bix;
        nx_d_h = d_h; nx_d_buf = d_buf; nx_d_rb = d_rb; nx_d_em = d_em; nx_d_last = d_last; nx_lcur = lcur; nx_w0c = w0c;
        if (armed && e_cpl && e_mine && e_w[511:508] == 4'd4) nx_in_end = 1'b1;
        if (o_ctl_c) begin
            nx_armed = 1'b1; nx_busy = 1'b1; nx_done = 1'b0; nx_in_end = 1'b0; nx_wv = 1'b0; nx_fin = 1'b0; nx_hdr_q = 1'b0;
        end
        if (o_ctl_t) begin nx_tc = 16'd0; nx_rc = 3'd0; nx_sn = 12'd0; end
        else if (armed) begin
            if (tc != 16'hFFFF) nx_tc = tc + 16'd1;
            if (g_on && !done) begin
                nx_rc = (rc == 3'd0) ? j_r - 3'd1 : rc - 3'd1;
                if (slot_q) nx_sn = sn + 12'd1;
            end
        end
        // staging: HDR first, else pop / flush
        if (armed && !hdr_q && !o_ctl_c) begin
            nx_d_h = 1'b1; nx_bq_n = 3'd1; nx_bix = 2'd0; nx_hdr_q = 1'b1; nx_lcur = j_hb;
        end else begin
            if (pop) begin nx_bq_n = bq_n - 3'd1; nx_bix = bix + 2'd1; end
            if (fl) begin
                nx_d_h = 1'b0; nx_d_buf = act; nx_d_em = !wv; nx_d_rb = wv && w0c != lcur; nx_d_last = lastf; nx_bix = 2'd0;
                nx_bq_n = (wv && w0c != lcur) ? 3'd3 : 3'd2;
                if (wv) nx_lcur = w0c + 20'd16;
                if (in_done && rf_n == 4'd0) nx_fin = 1'b1;
            end
        end
        // window open
        if (rf_pop && !r_in) begin nx_wv = 1'b1; nx_w0c = {r_i[19:4], 4'd0}; nx_act = nb_t; end
        if (fin && bq_n == 3'd0 && armed && !done) begin nx_done = 1'b1; nx_busy = 1'b0; end
        // the next cycle's grid slot
        nx_dly = o_ctl_j ? cp[84:69] : j_dly; nx_sm = o_ctl_j ? cp[99:88] : j_sm; nx_r = o_ctl_j ? cp[87:85] : j_r;
        nx_slot = nx_armed && nx_tc >= nx_dly + ((MUT == 3) ? 16'(nx_r) : 16'd0) && nx_rc == 3'd0 && nx_sn < nx_sm && !nx_done;
    end
    always @(posedge ck or negedge rl[1])
        if (!rl[1]) begin
            armed <= 1'b0; busy <= 1'b0; done <= 1'b0; in_end <= 1'b0; e_h <= 1'b0; ib_w <= '0; wv <= 1'b0;
            hdr_q <= 1'b0; fin <= 1'b0; bq_n <= 3'd0; slot_q <= 1'b0;
        end else begin
            armed <= nx_armed; busy <= nx_busy; done <= nx_done; in_end <= nx_in_end; wv <= nx_wv;
            hdr_q <= nx_hdr_q; fin <= nx_fin; bq_n <= nx_bq_n; slot_q <= nx_slot;
            if (o_eg && !vo_r[6]) e_h <= 1'b1;
            else if (o_eg && vo_r[6]) e_h <= 1'b0;
            if (ib_push) ib_w <= ib_w + 1'b1;
        end
    always @(posedge ck) begin
        act <= nx_act; w0c <= nx_w0c; tc <= nx_tc; rc <= nx_rc; sn <= nx_sn; bix <= nx_bix; lcur <= nx_lcur;
        d_h <= nx_d_h; d_buf <= nx_d_buf; d_rb <= nx_d_rb; d_em <= nx_d_em; d_last <= nx_d_last;
    end
    // window buffers: field f of buffer b written with the result score when the result lands in b
    wire        t_acc0  = rf_pop && r_in && !act,  t_acc1  = rf_pop && r_in && act;
    wire        t_open0 = rf_pop && !r_in && !nb_t, t_open1 = rf_pop && !r_in && nb_t;
    wire [15:0] r_oh = 16'd1 << r_i[3:0];
    always @(posedge ck) begin : g_win
        integer f_;
        for (f_ = 0; f_ < 16; f_ = f_ + 1) begin
            if ((t_acc0 || t_open0) && r_oh[f_]) wscb[0][16 * f_ +: 16] <= rh[15:0];
            if ((t_acc1 || t_open1) && r_oh[f_]) wscb[1][16 * f_ +: 16] <= rh[15:0];
        end
        if (t_open0) begin wlvb[0] <= r_oh; w0b[0] <= {r_i[19:4], 4'd0}; end else if (t_acc0) wlvb[0] <= wlvb[0] | r_oh;
        if (t_open1) begin wlvb[1] <= r_oh; w0b[1] <= {r_i[19:4], 4'd0}; end else if (t_acc1) wlvb[1] <= wlvb[1] | r_oh;
    end

    // ------------------------------------------------------------------ output: registered kept selects -> lo
    // beat type of descriptor (h, rb, ix): HDR | REBASE (rb, 0) | BEAT part 0 (rb ? 1 : 0) | BEAT part 1 (rb ? 2 : 1)
    wire        nx_pop = nx_slot && nx_bq_n != 3'd0;
    wire        nx_isr  = !nx_d_h && nx_d_rb && nx_bix == 2'd0;
    wire        nx_isb0 = !nx_d_h && (nx_d_rb ? nx_bix == 2'd1 : nx_bix == 2'd0);
    wire        nx_isb1 = !nx_d_h && (nx_d_rb ? nx_bix == 2'd2 : nx_bix == 2'd1);
    (* keep = "true" *) reg [15:0] sb0;      // [8 b + c]: BEAT part-0 scores of buffer b, bits [32 c +: 32]
    (* keep = "true" *) reg [1:0]  srb, sb1; // REBASE base / part-1 lane-valid of buffer b
    (* keep = "true" *) reg        s_b0, s_b1, s_h, s_p;   // any part 0 / any part 1 / HDR / any beat
    always @(posedge ck or negedge rl[3])
        if (!rl[3]) begin sb0 <= 16'd0; srb <= 2'd0; sb1 <= 2'd0; s_b0 <= 1'b0; s_b1 <= 1'b0; s_h <= 1'b0; s_p <= 1'b0; lo[0] <= 1'b0; end
        else begin : g_sel
            integer b_, c_;
            for (b_ = 0; b_ < 2; b_ = b_ + 1) begin
                for (c_ = 0; c_ < 8; c_ = c_ + 1) sb0[8 * b_ + c_] <= nx_pop && nx_isb0 && !nx_d_em && nx_d_buf == b_[0];
                srb[b_] <= nx_pop && nx_isr && nx_d_buf == b_[0];
                sb1[b_] <= nx_pop && nx_isb1 && !nx_d_em && nx_d_buf == b_[0];
            end
            s_b0 <= nx_pop && nx_isb0; s_b1 <= nx_pop && nx_isb1; s_h <= nx_pop && nx_d_h; s_p <= nx_pop;
            lo[0] <= s_p;
        end
    wire [255:0] wmk0 = wscb[0] & lvmask(wlvb[0]), wmk1 = wscb[1] & lvmask(wlvb[1]);   // stale fields masked
    always @(posedge ck) begin : g_lo
        integer c_;
        reg [255:0] dd; reg [11:0] tt;
        dd = {224'd0, {32{s_h}} & {j_l, j_k, j_hb}};                          // HDR {L, K, HB}
        dd[255:252] = dd[255:252] | ({4{s_b1}} & 4'd2);                       // part 1 {2, PT, 0, last, lv}
        dd[251:244] = dd[251:244] | ({8{s_b1}} & j_pt);
        dd[16]      = dd[16] | (s_b1 && d_last);
        dd[19:0]    = dd[19:0] | ({20{srb[0]}} & w0b[0]) | ({20{srb[1]}} & w0b[1]);   // REBASE {0, base}
        dd[15:0]    = dd[15:0] | ({16{sb1[0]}} & wlvb[0]) | ({16{sb1[1]}} & wlvb[1]);
        for (c_ = 0; c_ < 8; c_ = c_ + 1)                                      // part 0 scores
            dd[32 * c_ +: 32] = dd[32 * c_ +: 32] | ({32{sb0[c_]}} & wmk0[32 * c_ +: 32]) | ({32{sb0[8 + c_]}} & wmk1[32 * c_ +: 32]);
        tt = s_h ? {4'd1, j_pt} : (srb != 2'd0) ? {4'd6, j_pt} : s_b0 ? {4'd2, j_pt} : 12'd0;
        lo[V-1:1] <= {dd, tt, s_h || srb != 2'd0, s_b1, {2{s_p}} & j_l, {3{s_p}} & 3'(IK)};
    end

    // ------------------------------------------------------------------ faults / status
    always @(posedge ck or negedge rl[2])
        if (!rl[2]) begin fc_set <= 8'd0; fc <= 8'd0; end
        else begin
            fc_set <= 8'd0;
            if (o_eg && vo_r[6] && !e_h) fc_set[0] <= 1'b1;                           // part 1 without part 0
            if (ib_push && (ib_w - ib_r) == (IW + 1)'(IB)) fc_set[1] <= 1'b1;          // IDX buffer overflow
            if (o_ctl_c && busy) fc_set[2] <= 1'b1;                                     // a job while one is active
            if (o_ctl_c && (cp[87:85] == 3'd0 || cp[20:16] < 5'd8)) fc_set[3] <= 1'b1;
            if (rf_pop && !r_in && wv && r_i[19:4] < w0c[19:4]) fc_set[4] <= 1'b1;     // selection not ascending
            if (armed && !done && sn == j_sm && g_on) fc_set[5] <= 1'b1;               // grid exhausted, job not done
            if (cap_unal) fc_set[6] <= 1'b1;
            if (rf_n == 4'd8 && lp_v[1] && !rf_pop) fc_set[7] <= 1'b1;
            fc <= fc | fc_set;
        end
    always @(posedge ck or negedge rl[4])
        if (!rl[4]) st <= 16'd0;
        else st <= {fc, 4'b0, done, armed, busy, fc != 8'd0};
endmodule

// ===================================================================================================================
// dsdv_bk_sel_vmtx: the 72-frame die bk_sel master for the L20 split (= dsdv_bk_sel_vm + the tree transmitter).
// Ports = dsdv_bk_sel_vm + tl_o (tree lane to the parent die: die port <inst>_tl_o, the parent's ca / cb) + tx_st
// (die status port).  The TX ingress / egress kinds are the selector's straps of the die (ik 4, ek 5).
// ===================================================================================================================
module dsdv_bk_sel_vmtx #(
    parameter integer V      = 276,
    parameter integer MUT    = 0,
    parameter integer TX_MUT = 0,
    parameter bit     TX_SRAM = 1
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    tap_k,
    input  wire [7:0]    sink_k,
    input  wire [2:0]    ik,
    input  wire [2:0]    ek,
    input  wire [7:0]    uid,
    input  wire          eg_n,
    input  wire [V-1:0]  vi_s,
    output wire [V-1:0]  vo_n,
    input  wire [V-1:0]  vi_n,
    output wire [V-1:0]  vo_s,
    input  wire [V-1:0]  vi_idx,
    input  wire [V-1:0]  ca,
    input  wire [V-1:0]  cb,
    output wire          fault,
    output wire          vm_fault,
    output wire [V-1:0]  tl_o,
    output wire [15:0]   tx_st
);
    wire [V-1:0] vi_m;
    dsdv_idx_vmux #(.V(V)) u_vm (.ck(clk), .rst(rst_n), .i_r(vi_s), .i_s(vi_idx), .i_a(ca), .i_b(cb), .o(vi_m), .fault(vm_fault));
    dsdv_bk_sel #(.V(V), .MUT(MUT)) u_sel (.clk(clk), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k), .ik(ik), .ek(ek),
        .uid(uid), .eg_n(eg_n), .vi_s(vi_m), .vo_n(vo_n), .vi_n(vi_n), .vo_s(vo_s), .fault(fault));
    dsdv_idx_tx_n32 #(.V(V), .IK(4), .EK(5), .UID(8'h5C), .SRAM_MACRO(TX_SRAM), .MUT(TX_MUT)) u_tx (
        .ck(clk), .rst(rst_n), .vi(vi_m), .vo(vo_s), .lo(tl_o), .st(tx_st));
endmodule
