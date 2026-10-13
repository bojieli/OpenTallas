`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hgi_smmv: SM.MATVEC record ENGINE, track B (el1011-hbm-smmv-b, 2026-10-12; spec results/rtl/sm_matvec_redesign_1012/
// SPEC.md).  Same record / x / publication / per-SM command contract as ot_hgi_sm_record (LEGACY 0), re-architected for
// throughput: records are no longer run one at a time.
//   * RECORD WINDOW: up to W records in flight; decode is a pipeline (one record an edge); x load, SM issue, publication
//     command and retire are four independent in-order pointers, so record N+1's decode, x load, descriptors and start
//     overlap record N's weight stream (the SM element queues NOUT ops and requests N+1's lines as soon as its
//     descriptor is taken).
//   * X SLOTS BY HARDWARE ALLOCATION: a ring over the XD x-store addresses; record i gets 8 op_g contiguous addresses
//     (op_xb = slot base) and releases them at its retire, so an x load never overwrites a slot that a record in flight
//     still reads (no compiler rule needed).  The loader (ot_hgi_sm_xload) adds the slot base x_xb in its write flop.
//   * X REUSE (header param[5] XR, track A 3a): an XR record whose A descriptor equals the LATEST load's takes that slot
//     with no load (verified hit; otherwise it loads); the slot stays pinned until it retires (the holder's release
//     moves to it; re-reserved if the holder already retired).  The compiler's xb is ignored (hardware allocation).
//   * B2 (HBM = 4 clusters x 8 SMs): one engine a cluster, NSM 8, strap sm_base = 8c; row blocks stay Q = ceil(M/32)
//     over the die, so station s owns global rows (sm_base + s) Q ... (two station edges: products, then clamps).
//   * SM STATIONS: per-SM fields (rows, d_base, d_lines) from {Q, LQ, ML, M, line0} with constant multiplies by the SM
//     index (one registered stage; on the die each station sits at its SM and the record crosses as ONE broadcast bus).
//   * EXACT DIVIDE: line0 = B.base / LB by the modular inverse (LB 136 = 8 x 17, 160 = 32 x 5), the multiple-of check
//     q <= (2^w - 1) / d (one pipelined multiply instead of the 20-edge iterative divide).
//   * RETIRE in order: every SM active in the record completed its op (per-SM completion counter, arrive toggles, vs
//     the record's per-SM target) AND the publication of the record is done (record-pipelined pub: one pub_done pulse
//     a record, in order; ot_hgi_smmv_pub).
// Refusals as ot_hgi_sm_record (+ 8 op_g > XD).  Any fault halts (sticky until rst_n), rec_fault pulses once.
// Mutants: MUT_SLOT (every record's x at slot 0, no allocation: a later load overwrites x under a running matvec),
//          MUT_EARLY (retire on issue, not on completion), MUT_XRS (an XR hit reads the previous load's slot: stale x).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_smmv #(
    parameter integer NSM = 8,            // SMs served by this engine (B2 default 8 = one cluster; legacy 32 = whole die)
    parameter integer W = 4,              // record window (power of two, <= 8; sequence numbers WI + 1 bits)
    parameter integer XD = 128,
    parameter integer XQ = 1,             // smmv-b BDW8: x loads in flight (1 or 2; the pipelined BW8 loader takes the next
                                          //   load while the previous one drains; x_done in order); 1 = one at a time
    parameter integer MUT_SLOT = 0,
    parameter integer MUT_EARLY = 0,
    parameter integer MUT_XRS = 0,        // bx mutant: an X REUSE hit takes the PREVIOUS load's slot (stale x)
    // el1013 redesign DE = 1 EARLY DESCRIPTORS: the descriptor pass (stations + per-SM descriptor / chunk handshakes) runs
    // on its own in-order pointer dp as soon as a record is decoded, NOT behind its x load; the start pass (ip) follows
    // when the x is in the store and sends only the start.  The SM fetches the record's weight lines (first HBM access
    // ~110 cycles) under the x load and under the previous records' streams; the kernel consumes them in descriptor
    // order when the op launches.  DE = 0: descriptor and start together after x (the 10-12 engine, unchanged).
    // MUT_DE (bench): the start pass does not wait for the x (e_xd): the op launches on a stale / half-written x.
    parameter integer DE = 0,
    parameter integer MUT_DE = 0,
    // smmv-cr (2026-10-12) ROW CREDITS (track A ot_hgi_sm_record CR, with its DEADLOCK RULE; CR = 0 default: one
    // descriptor of the whole slice, as before).  CR = 1: SM s is described in chunks of CHE rows, a chunk leaves while
    // cr[s] >= n (cr = AD - rows described and not yet consumed by the pub, +1 per sm_cr[s] pulse).  The SM issues
    // group-slot waves of SIL = 8 (row, group) items whose lines interleave and emits a row only when its wave is
    // complete, so a chunk is a MULTIPLE OF SIL ROWS (= G whole waves for any G): every row of a described chunk leaves
    // with no later line and credits never wait on a chunk that needs them (a chunk inside a wave + the last credits
    // = circular wait, track A r_ad4b).  AD < SIL is refused (a wave's rows leave back to back on a port with no
    // ready).  Credits persist across records (in-order descriptors; a record's last wave ends its op).
    parameter integer CR = 0,
    parameter integer AD = 32,
    parameter integer CH = 8,
    parameter integer SIL = 8,
    parameter integer MUT_CRDL = 0         // mutant: chunk min(CH, AD), not wave-aligned, AD < SIL allowed (deadlocks)
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire [4:0]         sm_base,       // static strap: global index of local SM 0 (B2 cluster c: 8c; legacy 0)
    input  wire               rec_v,
    output wire               rec_rdy,
    input  wire [127:0]       rec_hdr,
    input  wire [255:0]       rec_a, rec_b, rec_o,
    input  wire [20:0]        rec_n_a, rec_n_b,
    output reg                rec_done,
    output reg                rec_fault,
    output wire               halted,
    output reg                x_v,
    input  wire               x_rdy,
    output reg  [39:0]        x_base,
    output reg  [20:0]        x_n,
    output reg  [3:0]         x_p,
    output reg  [31:0]        x_stride,
    output reg  [1:0]         x_space,
    output reg  [1:0]         x_fmt,
    output reg  [6:0]         x_xb,          // the load's allocated slot base (ot_hgi_sm_xload adds it in its write pin flop)
    input  wire               x_done,
    input  wire               x_fault,
    output reg                pub_v,
    input  wire               pub_rdy,
    output reg  [39:0]        pub_base,
    output reg  [31:0]        pub_stride,
    output reg  [1:0]         pub_space,
    output reg  [19:0]        pub_m,
    output reg  [12:0]        pub_q,
    output reg  [3:0]         pub_p,
    output reg                pub_bf16,
    input  wire               pub_done,
    input  wire               pub_fault,
    output wire [NSM*106-1:0] sm_cmd,
    input  wire [NSM*4-1:0]   sm_ret,
    output reg                sm_cg_en,
    output wire [2:0]         dbg_iss_seq,     // sequence number of the record being issued (bench shadows)
    input  wire [NSM-1:0]     sm_cr            // smmv-cr: one pulse per arrival entry the pub consumed, per SM (CR = 1)
);
    localparam integer CW = 106;
    localparam [36:0] INV17 = 37'h10f0f0f0f1;   localparam [36:0] LIM17 = 37'd8084644321;
    localparam [34:0] INV5  = 35'h4cccccccd;    localparam [34:0] LIM5  = 35'd6871947673;
    localparam integer NSMT = 32;                // row blocks Q = ceil(M / 32) over the whole die's SMs (B2: 4 x 8)
    initial if (W > 8 || (W & (W - 1)) != 0 || (NSM != 8 && NSM != 16 && NSM != 32) || XD != 128)
        $fatal(1, "ot_hgi_smmv: W in {1,2,4,8}, NSM in {8,16,32}, XD 128");
    reg [4:0] smb_q; always @(posedge clk) smb_q <= sm_base;     // strap pin flop
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rst_i = rs[1];
    reg halt_q; assign halted = halt_q;
    reg [NSM*4-1:0] ret_q; always @(posedge clk) ret_q <= sm_ret;
    reg in_xd, in_xf, in_pd, in_pf;
    always @(posedge clk) begin in_xd <= x_done; in_xf <= x_fault; in_pd <= pub_done; in_pf <= pub_fault; end

    // ================= decode pipeline (D0 pin flops, D1 count fields + checks, D2 products, D3 checks -> window) ====
    reg         d0_v, d1_v, d2_v;
    reg [127:0] hdr0; reg [255:0] a0, b0, o0; reg [20:0] na0, nb0;
    wire [6:0]  opnd = hdr0[99:93];
    wire [1:0]  pf0 = hdr0[65:64];
    wire [3:0]  pp0 = {1'b0, hdr0[68:66]} + 4'd1;
    wire [2:0]  bfmt = b0[4:2];
    wire [2:0]  want = (pf0 == 2'd0) ? 3'd1 : (pf0 == 2'd1) ? 3'd2 : (pf0 == 2'd2) ? 3'd3 : 3'd4;
    wire [3:0]  lw8 = (pf0 == 2'd1) ? 4'd10 : (pf0 == 2'd2) ? 4'd11 : 4'd9;
    wire [20:0] km1 = nb0 - 21'd1;
    wire [20:0] g_full = (km1 >> lw8) + 21'd1;
    wire [19:0] mm0 = b0[87:68];
    wire [15:0] q_full = (mm0 + NSMT - 1) >> 5;
    wire bad0 = (hdr0[127:124] != 4'd1) || (hdr0[123:118] != 6'd0) || !opnd[0] || !opnd[1] || !opnd[4] ||
               (b0[1:0] != 2'd0) || (a0[1:0] != 2'd1 && a0[1:0] != 2'd2) || (o0[1:0] != 2'd1 && o0[1:0] != 2'd2) ||
               (bfmt != want) || b0[5] || (b0[135:120] > 16'd1) || (na0 != nb0) || (nb0 == 21'd0) ||
               (mm0 == 20'd0) || (g_full > 21'd16) || (q_full > 16'd4095) ||          // g <= 16: 8 g <= XD
               ((pf0 == 2'd1 || pf0 == 2'd2) && (|nb0[4:0])) ||
               (pp0 > 4'd1 && (a0[87:68] != {16'd0, pp0} || o0[87:68] != {16'd0, pp0}));
    // D1
    reg [255:0] a1, o1; reg [20:0] na1; reg [1:0] f1; reg [3:0] p1; reg [7:0] g1; reg [12:0] q1; reg [10:0] lpr1;
    reg lb160_1, bad1, xr1; reg [19:0] m1; reg [39:0] base1; reg [31:0] str1;
    // D2
    reg [255:0] a2, o2; reg [20:0] na2; reg [1:0] f2; reg [3:0] p2; reg [7:0] g2; reg [12:0] q2; reg [19:0] m2;
    reg [23:0] lq2; reg [30:0] ml2; reg [18:0] strp2; reg [31:0] str2; reg bad2; reg [36:0] qd2; reg lb160_2; reg lo_ok2; reg xr2;
    // r2: D2 products are multi-edge (held D1 operands; ONE record in decode at a time, rec_rdy low until D3 commits):
    // dw_v counts DLAT edges, then D2 captures.  Was one edge (base1 -> qd2 37 x 37 exact-divide multiply -141 ps,
    // lpr1 -> ml2 / lq2 -83 / -74 ps).
    localparam integer DLAT = 12;          // >= max LAT below (qd 7 + 4 = 11; ml 2 + 3; lq 2 + 2; strp 2 + 2)
    reg dw_v; reg [3:0] dcnt;
    wire dcap = dw_v && (dcnt == 4'(DLAT));
    wire [36:0] qx = lb160_1 ? {2'b00, base1[39:5]} : base1[39:3];
    wire [36:0] qk = lb160_1 ? {2'b00, INV5} : INV17;
    wire [36:0] qd_p; wire [23:0] lq_p; wire [30:0] ml_p; wire [18:0] strp_p;
    ot_hgi_smmv_pmul #(.WA(37), .WB(37), .WP(37), .R(6)) u_qd (.clk(clk), .a(qk), .b(qx), .p(qd_p));
    ot_hgi_smmv_pmul #(.WA(13), .WB(11), .WP(24), .R(6)) u_lq (.clk(clk), .a(q1), .b(lpr1), .p(lq_p));
    ot_hgi_smmv_pmul #(.WA(20), .WB(11), .WP(31), .R(6)) u_ml (.clk(clk), .a(m1), .b(lpr1), .p(ml_p));
    ot_hgi_smmv_pmul #(.WA(8), .WB(11), .WP(19), .R(6)) u_sp (.clk(clk), .a(lb160_1 ? 8'd160 : 8'd136), .b(lpr1), .p(strp_p));

    // ================= window (entries at seq mod W) =================
    localparam integer WI = (W > 1) ? $clog2(W) : 1;
    localparam integer SQ = WI + 1;      // sequence number bits (one more than the slot index: full / empty)
    localparam integer WA = 1 << WI;     // ring slots (W=1 keeps 2 slots so the 1-bit seq index stays in range; occupancy still <= W)
    reg [SQ-1:0] tail, xp, ip, rh, ppc, pdc;         // push / x / issue / retire / pub command / pub done (SQ-b seq)
    reg [255:0] e_a [0:WA-1]; reg [255:0] e_o [0:WA-1]; reg [20:0] e_na [0:WA-1];
    reg [1:0] e_f [0:WA-1]; reg [3:0] e_p [0:WA-1]; reg [7:0] e_g [0:WA-1]; reg [12:0] e_q [0:WA-1]; reg [19:0] e_m [0:WA-1];
    reg [23:0] e_lq [0:WA-1]; reg [30:0] e_ml [0:WA-1]; reg [31:0] e_l0 [0:WA-1];
    reg [6:0] e_xb [0:WA-1]; reg [7:0] e_rel [0:WA-1]; reg [WA-1:0] e_xd, e_xr;
    reg [NSM-1:0] e_act [0:WA-1]; reg [NSM*4-1:0] e_tgt [0:WA-1];
    reg [SQ-1:0] dp;                                 // DE: descriptor-pass pointer (tail >= dp >= ip)
    reg [NSM*13-1:0] e_rows [0:WA-1]; reg [WA-1:0] e_sd;   // DE: per-SM rows of the entry (start pass), stations done
    wire [SQ-1:0] nin = tail - rh;
    reg rdy_r;
    assign rec_rdy = rdy_r;
    function automatic [WI-1:0] ix(input [SQ-1:0] q); ix = q[WI-1:0]; endfunction

    // ================= x allocator / x stage =================
    reg [7:0] used; reg [6:0] ap; reg [6:0] xbc, xbp; reg [1:0] xn; reg [SQ-1:0] xfq [0:3]; reg [1:0] xfh, xft;   // XQ <= 3 (xp 10-13: a third load in flight)
    // r2 (route r1-6e530654e: xp -> used -89 ps = e_g[xp] mux -> ap + nf compare -> wrap -> used + ws + nf compare ->
    // used update in one edge): the allocation is precomputed over two registered edges.  al_age restarts at every
    // event that changes xp / ap / used-upward / the window tail (x alloc, x hit, D3 commit); an allocation fires only at
    // age 2.  A retire in between only LOWERS used, so a_ok computed on the older used stays safe (conservative).
    reg [1:0] al_age;
    reg [7:0] nf; reg fits_r; reg [6:0] a_st; reg [7:0] a_ws; reg a_okr;
    wire [7:0] nfw = {e_g[ix(xp)], 3'b000};
    always @(posedge clk) begin : alq
        // bx (10-12, deadlock at L1 xr cycle 94,847): an EMPTY ring (used 0: no live record holds a slot) restarts at
        // address 0 with no wrap waste.  Before, a record with 8 op_g > ap after a wrap point (here nf 128 at ap 64,
        // left there by a load before four X REUSE hits) needed waste 128 - ap + nf > 128 forever: ap only moves on
        // an allocation, so the x stage never allocated again and every SM went idle.  used is read 2 edges early,
        // but only an x event (which restarts al_age) raises it, so used 0 here is still 0 at the allocation.
        reg ft, em; em = (used == 8'd0); ft = em || ({1'b0, ap} + nfw) <= 8'd128;
        nf <= nfw; fits_r <= ft;
        a_st <= (MUT_SLOT != 0 || em) ? 7'd0 : (ft ? ap : 7'd0);
        a_ws <= (MUT_SLOT != 0 || ft) ? 8'd0 : (8'd128 - {1'b0, ap});
        a_okr <= (MUT_SLOT != 0) || ({1'b0, used} + a_ws + nf <= 9'd128);
    end
    wire       a_ok = a_okr && (al_age == 2'd2);

    // ================= issue stage + SM stations =================
    reg [NSM*CW-1:0] cmd_h;
    reg [NSM-1:0] st_pend, d_pend, rel, arr_prev; reg [NSM*4-1:0] iss_cnt, done_cnt;
    reg go, fld_v, fp_v, fq_v, fa_v;
    reg dgo, sq_v; reg [NSM*13-1:0] srows_s; reg [NSM-1:0] sact_s; reg [1:0] fmt_d; reg [7:0] g_d;   // DE
    // station strap index sg_s = sm_base + s: static, so one kept register per station (no adder in the product path)
    // and the products are split over two edges (gate 10-12: smb_q -> slq_p was ONE 5 x 24 multiply, 28 levels ~1015 ps)
    (* keep *) reg [4:0] sgq [0:NSM-1];
    always @(posedge clk) for (integer s_ = 0; s_ < NSM; s_ = s_ + 1) sgq[s_] <= smb_q + 5'(s_);
    reg [19:0] f_m; reg [12:0] f_q; reg [23:0] f_lq; reg [30:0] f_ml; reg [31:0] f_l0;
    // r2 (route r1-6e530654e: f_lq -> sla -89, sla -> slq_p -80, f_ml -> dl_s -134, f_l0 -> dbase_s -124, f_m -> rows_s
    // -20 ps, all ripple chains): per-station multi-edge arithmetic on the held f_* fields, <= 12 carry bits an edge.
    //   sq = sg Q (3 edges), slq = sg LQ (4), dmq = M - sq (2), gtq = dmq > Q (2), dm = ML - slq (3), gtl = dm > LQ (3),
    //   db = L0 + slq (3): longest chain slq -> dm -> gtl = 10 edges; capture after SLAT.
    localparam integer SLAT = 12;
    reg [3:0] scnt;
    wire [NSM-1:0] st_act; wire [NSM*13-1:0] st_rows; wire [NSM*24-1:0] st_dl; wire [NSM*32-1:0] st_db;
    genvar gs;
    for (gs = 0; gs < NSM; gs = gs + 1) begin : g_st
        wire [19:0] sq; wire [31:0] slq; wire [20:0] dmq, gq; wire [31:0] dm, db; wire [32:0] gl;
        ot_hgi_smmv_pmul #(.WA(13), .WB(5), .WP(20), .R(5)) u_sq (.clk(clk), .a(f_q), .b(sgq[gs]), .p(sq));
        ot_hgi_smmv_pmul #(.WA(24), .WB(5), .WP(32), .R(5)) u_slq (.clk(clk), .a(f_lq), .b(sgq[gs]), .p(slq));
        ot_hgi_smmv_padd #(.W(21), .SUB(1)) u_dmq (.clk(clk), .a({1'b0, f_m}), .b({1'b0, sq}), .s(dmq));
        ot_hgi_smmv_padd #(.W(21), .SUB(1)) u_gq (.clk(clk), .a({8'd0, f_q}), .b({1'b0, dmq[19:0]}), .s(gq));
        ot_hgi_smmv_padd #(.W(32), .SUB(1)) u_dm (.clk(clk), .a({1'b0, f_ml}), .b(slq), .s(dm));
        ot_hgi_smmv_padd #(.W(33), .SUB(1)) u_gl (.clk(clk), .a({9'd0, f_lq}), .b({1'b0, dm}), .s(gl));
        ot_hgi_smmv_padd #(.W(32), .SUB(0)) u_db (.clk(clk), .a(f_l0), .b(slq), .s(db));
        wire a_ = !dmq[20] && (|dmq[19:0]);                       // M > sg Q
        assign st_act[gs] = a_;
        assign st_rows[gs*13 +: 13] = !a_ ? 13'd0 : gq[20] ? f_q : dmq[12:0];
        assign st_dl[gs*24 +: 24] = !a_ ? 24'd0 : gl[32] ? f_lq : dm[23:0];
        assign st_db[gs*32 +: 32] = db;
    end
    reg [NSM*13-1:0] rows_s; reg [NSM*32-1:0] dbase_s; reg [NSM*24-1:0] dl_s; reg [NSM-1:0] act_s;
    // smmv-cr row-credit chunking (CR = 1): rows / lines still to describe, the next chunk's base, credits
    localparam integer CHM = (CH < AD) ? CH : AD;
    localparam integer CHE = (MUT_CRDL != 0 || CHM >= SIL) ? CHM : SIL;
    localparam integer LCH = $clog2(CHE), CRW = $clog2(AD + 1);
`ifndef SYNTHESIS
    initial if (CR != 0 && ((1 << LCH) != CHE || (MUT_CRDL == 0 && (AD < SIL || CHE % SIL != 0))))
        $fatal(1, "ot_hgi_smmv: row credits need AD >= SIL = %0d and a power-of-two chunk multiple of SIL rows (AD %0d, CH %0d)", SIL, AD, CH);
`endif
    reg [NSM*13-1:0] rr_s; reg [NSM*24-1:0] lr_s; reg [NSM*32-1:0] nb_s; reg [NSM*CRW-1:0] cr_s; reg [NSM-1:0] rr_nz, cri;
    reg [23:0] chl;                                                  // lines a full chunk (LPR x CHE)
    always @(posedge clk) cri <= sm_cr;
    reg [1:0] fmt_i; reg [7:0] g_i; reg [6:0] xb_i;
    integer s;
    reg [NSM-1:0] st_n, d_n;
    always @* for (s = 0; s < NSM; s = s + 1) begin
        st_n[s] = st_pend[s] && !(cmd_h[s*CW] && sm_ret[s*4 + 0]);
        d_n[s]  = d_pend[s] && !(cmd_h[s*CW + 48] && sm_ret[s*4 + 1]);
    end
    always @(posedge clk)
        for (s = 0; s < NSM; s = s + 1)
            cmd_h[s*CW +: CW] <= {rel[s], dl_s[s*24 +: 24], dbase_s[s*32 +: 32], d_n[s] & ((DE != 0) ? dgo : go) & rst_i, xb_i,
                                  fmt_i, 1'b1, g_i, 16'd8, (DE != 0) ? srows_s[s*13 +: 13] : rows_s[s*13 +: 13], st_n[s] & go & rst_i};
    assign sm_cmd = cmd_h;
    assign dbg_iss_seq = 3'(ip);
    reg pend0_r; always @(posedge clk) pend0_r <= (st_n == 0) && (d_n == 0);
    reg pends_r, pendd_r; always @(posedge clk) begin pends_r <= (st_n == 0); pendd_r <= (d_n == 0); end   // DE: one a pass
    // retire condition of the head (registered reductions)
    reg hd_ok;
    always @(posedge clk) begin : hd
        reg ok; reg [3:0] df; integer k;
        ok = 1'b1;
        for (k = 0; k < NSM; k = k + 1) begin
            df = done_cnt[k*4 +: 4] - e_tgt[ix(rh)][k*4 +: 4];
            if (e_act[ix(rh)][k] && df[3]) ok = 1'b0;     // done - tgt < 0 (mod 16, window <= 8)
        end
        hd_ok <= ok;
    end
    reg any_fault;
    always @* begin
        any_fault = 1'b0;
        for (s = 0; s < NSM; s = s + 1) if (ret_q[s*4 + 3]) any_fault = 1'b1;
    end
    reg rh_wait;                                       // one edge after a retire (hd_ok recomputed for the new head)
    wire ret_go = (rh != ip) && !rh_wait && (MUT_EARLY != 0 || (hd_ok && pdc != rh)) && !halt_q;
    // x reuse: xo = the record currently holding the latest loaded slot's release; xo_live = it has not retired
    reg [SQ-1:0] xo; reg xo_v; reg [7:0] xo_nf;
    // the hit is VERIFIED: XR only says "x unchanged since"; the hardware reuses only the LATEST load's slot (the one a pin
    // can hold without breaking the ring's in-order release) and only if the A descriptor matches; otherwise it loads.
    function automatic [100:0] xkey(input [255:0] a, input [20:0] n, input [1:0] f, input [3:0] p);
        xkey = {a[47:8], a[119:88], a[1:0], n, f, p};
    endfunction
    reg [100:0] xk;
    wire x_hit = e_xr[ix(xp)] && xo_v && (xkey(e_a[ix(xp)], e_na[ix(xp)], e_f[ix(xp)], e_p[ix(xp)]) == xk);
    wire [SQ-1:0] xo_d = xo - rh, xp_d = xp - rh;
    wire xo_live = xo_d < xp_d;
    // bx (10-12): a hit no longer waits for the latest load to land (nor for its command to be taken): the hit record
    // only names the slot; issue is in order (ip) and waits on e_xd of the holder, so the hit's x is read after the
    // holder's load landed.  (Was !x_v && xn == 0: with XQ 2 a hit candidate always found a load in flight and loaded
    // again -> XR never engaged, w8_L1 xr = noxr = 10,704 cyc.)
    wire x_hit_go = xp != tail && !halt_q && x_hit;
    wire x_ld_go = !x_v && xn < 2'(XQ) && xp != tail && !halt_q && !x_hit_go && a_ok;
    wire x_ev = x_hit_go || x_ld_go;

    always @(posedge clk or negedge rst_i) begin
        if (!rst_i) begin
            d0_v <= 1'b0; d1_v <= 1'b0; d2_v <= 1'b0; dw_v <= 1'b0; dcnt <= 4'd0; al_age <= 2'd0; rdy_r <= 1'b0; halt_q <= 1'b0; rec_done <= 1'b0; rec_fault <= 1'b0;
            // control only (pointers, valids, counters); datapath / field registers carry no reset (gate: rst fanout)
            tail <= 0; xp <= 0; ip <= 0; rh <= 0; ppc <= 0; pdc <= 0; e_xd <= 0; used <= 0; ap <= 0;
            xn <= 2'd0; xfh <= 2'd0; xft <= 2'd0; x_v <= 1'b0; pub_v <= 1'b0; go <= 1'b0; fld_v <= 1'b0; fp_v <= 1'b0; fq_v <= 1'b0; fa_v <= 1'b0;
            xo <= 0; xo_v <= 1'b0; st_pend <= 0; d_pend <= 0; dp <= 0; dgo <= 1'b0; sq_v <= 1'b0; e_sd <= 0;
            rel <= 0; arr_prev <= 0; iss_cnt <= 0; done_cnt <= 0; sm_cg_en <= 1'b0; rh_wait <= 1'b0;
            rr_nz <= 0; for (s = 0; s < NSM; s = s + 1) cr_s[s*CRW +: CRW] <= CRW'(AD);
        end else begin : main
            reg [7:0] used_n;
            rec_done <= 1'b0; rec_fault <= 1'b0;
            sm_cg_en <= (tail != rh) || d0_v || d1_v || dw_v || d2_v;
            // ---- accept (window has room counting the decode pipe)
            // r2: one record in decode at a time (held operands): accept again once D3 has committed it
            rdy_r <= !halt_q && !(rec_v && rec_rdy) && !d0_v && !d1_v && !dw_v && ({1'b0, nin} + d2_v < W);
            d0_v <= rec_v && rec_rdy;
            if (rec_v && rec_rdy) begin hdr0 <= rec_hdr; a0 <= rec_a; b0 <= rec_b; o0 <= rec_o; na0 <= rec_n_a; nb0 <= rec_n_b; end
            // ---- D1
            d1_v <= d0_v;
            if (d0_v) begin
                a1 <= a0; o1 <= o0; na1 <= na0; f1 <= pf0; p1 <= pp0; g1 <= g_full[7:0]; q1 <= q_full[12:0];
                lpr1 <= (pf0 == 2'd3) ? {1'b0, g_full[7:0], 2'b00} : {g_full[7:0], 3'b000};
                lb160_1 <= (pf0 == 2'd3); bad1 <= bad0; xr1 <= hdr0[69]; m1 <= mm0; base1 <= b0[47:8]; str1 <= b0[119:88];
            end
            // ---- D2: products and the exact divide
            if (d1_v) begin dw_v <= 1'b1; dcnt <= 4'd0; end
            else if (dw_v) dcnt <= dcnt + 4'd1;
            if (dcap) dw_v <= 1'b0;
            d2_v <= dcap;
            if (dcap) begin
                a2 <= a1; o2 <= o1; na2 <= na1; f2 <= f1; p2 <= p1; g2 <= g1; q2 <= q1; m2 <= m1; bad2 <= bad1; xr2 <= xr1;
                lq2 <= lq_p; ml2 <= ml_p; str2 <= str1; strp2 <= strp_p; lb160_2 <= lb160_1;
                qd2 <= lb160_1 ? {2'b00, qd_p[34:0]} : qd_p;
                lo_ok2 <= lb160_1 ? (base1[4:0] == 5'd0) : (base1[2:0] == 3'd0);
            end
            // ---- D3: checks -> window entry
            if (d2_v) begin
                if (bad2 || (str2 != {13'd0, strp2}) || !lo_ok2 || (lb160_2 ? (qd2[34:0] > LIM5) : (qd2 > LIM17)) ||
                    (|qd2[36:32])) begin
                    rec_fault <= 1'b1; halt_q <= 1'b1;
                end else begin
                    e_a[ix(tail)] <= a2; e_o[ix(tail)] <= o2; e_na[ix(tail)] <= na2; e_f[ix(tail)] <= f2;
                    e_p[ix(tail)] <= p2; e_g[ix(tail)] <= g2; e_q[ix(tail)] <= q2; e_m[ix(tail)] <= m2;
                    e_lq[ix(tail)] <= lq2; e_ml[ix(tail)] <= ml2; e_l0[ix(tail)] <= qd2[31:0];
                    e_xd[ix(tail)] <= 1'b0; e_xr[ix(tail)] <= xr2; e_sd[ix(tail)] <= 1'b0;
                    tail <= tail + 1'b1;
                end
            end
            // ---- publication command (in order, as soon as decoded: the pub holds the descriptor before any row)
            if (pub_v && pub_rdy) pub_v <= 1'b0;
            if (!pub_v && !(pub_v && pub_rdy) && ppc != tail && !halt_q) begin
                pub_v <= 1'b1; pub_base <= e_o[ix(ppc)][47:8]; pub_stride <= e_o[ix(ppc)][119:88];
                pub_space <= e_o[ix(ppc)][1:0]; pub_bf16 <= (e_o[ix(ppc)][4:2] == 3'd1); pub_m <= e_m[ix(ppc)];
                pub_q <= e_q[ix(ppc)]; pub_p <= e_p[ix(ppc)]; ppc <= ppc + 1'b1;
            end
            if (in_pd) pdc <= pdc + 1'b1;
            // ---- x stage: allocate the slot, issue the load; one load in flight
            used_n = used;
            if (x_v && x_rdy) x_v <= 1'b0;
            if (x_hit_go) begin
                // X REUSE hit: the x of this record is the latest load's slot; no load.  The slot stays pinned until this
                // record retires: the latest holder's release moves to it, or (holder already retired) it is re-reserved
                // (it sits right behind the ring pointer, nothing was allocated since).
                e_xb[ix(xp)] <= (MUT_XRS != 0) ? xbp : xbc; e_xd[ix(xp)] <= 1'b1; xp <= xp + 1'b1; xo <= xp;
                if (MUT_SLOT != 0) e_rel[ix(xp)] <= 8'd0;
                else if (xo_live && !(ret_go && rh == xo)) begin e_rel[ix(xp)] <= e_rel[ix(xo)]; e_rel[ix(xo)] <= 8'd0; end
                else begin e_rel[ix(xp)] <= xo_nf; used_n = used_n + xo_nf; end
            end else if (x_ld_go) begin
                xo <= xp; xo_v <= 1'b1; xo_nf <= nf; xk <= xkey(e_a[ix(xp)], e_na[ix(xp)], e_f[ix(xp)], e_p[ix(xp)]);
                xp <= xp + 1'b1; xfq[xft] <= xp; xft <= xft + 2'd1; x_v <= 1'b1; x_base <= e_a[ix(xp)][47:8]; x_n <= e_na[ix(xp)]; x_p <= e_p[ix(xp)];
                x_stride <= e_a[ix(xp)][119:88]; x_space <= e_a[ix(xp)][1:0]; x_fmt <= e_f[ix(xp)]; x_xb <= a_st;
                e_xb[ix(xp)] <= a_st; e_rel[ix(xp)] <= (MUT_SLOT != 0) ? 8'd0 : a_ws + nf; xbc <= a_st; xbp <= xbc;
                if (MUT_SLOT == 0) begin used_n = used_n + a_ws + nf; ap <= a_st + nf[6:0]; end
            end
            if (xn != 2'd0 && in_xd) begin e_xd[ix(xfq[xfh])] <= 1'b1; xfh <= xfh + 2'd1; end
            xn <= xn + (x_ld_go ? 2'd1 : 2'd0) - ((xn != 2'd0 && in_xd) ? 2'd1 : 2'd0);
            // ---- issue stage: fields (stations) one edge, then the start / descriptor handshakes of every active SM
          if (DE == 0) begin : g_iss0
            if (!go && !fld_v && !fp_v && !fq_v && !fa_v && ip != xp && e_xd[ix(ip)] && ppc != ip && !halt_q) begin
                fq_v <= 1'b1; scnt <= 4'd0;                      // edge 1: select the issue entry's fields
                fmt_i <= e_f[ix(ip)]; g_i <= e_g[ix(ip)]; xb_i <= e_xb[ix(ip)];
                f_m <= e_m[ix(ip)]; f_q <= e_q[ix(ip)]; f_lq <= e_lq[ix(ip)]; f_ml <= e_ml[ix(ip)]; f_l0 <= e_l0[ix(ip)];
            end
            // r2 stations: operands f_* held while the multi-edge station arithmetic runs (SLAT edges), then one capture
            if (fq_v) begin
                if (scnt == 4'(SLAT)) begin
                    fq_v <= 1'b0; fld_v <= 1'b1;
                    for (s = 0; s < NSM; s = s + 1) begin
                        act_s[s] <= st_act[s];
                        rows_s[s*13 +: 13] <= st_rows[s*13 +: 13]; dl_s[s*24 +: 24] <= st_dl[s*24 +: 24];
                        dbase_s[s*32 +: 32] <= st_db[s*32 +: 32];
                    end
                end else scnt <= scnt + 4'd1;
            end
            if (fld_v) begin
                fld_v <= 1'b0; go <= 1'b1; st_pend <= act_s; d_pend <= (CR != 0) ? {NSM{1'b0}} : act_s; e_act[ix(ip)] <= act_s;
                rr_s <= rows_s; lr_s <= dl_s; nb_s <= dbase_s; rr_nz <= (CR != 0) ? act_s : {NSM{1'b0}};
                chl <= ((fmt_i == 2'd3) ? {14'd0, g_i, 2'b00} : {13'd0, g_i, 3'b000}) << LCH;   // LPR = 4 g (INT8) / 8 g
                for (s = 0; s < NSM; s = s + 1) e_tgt[ix(ip)][s*4 +: 4] <= iss_cnt[s*4 +: 4] + {3'd0, act_s[s]};
                for (s = 0; s < NSM; s = s + 1) iss_cnt[s*4 +: 4] <= iss_cnt[s*4 +: 4] + {3'd0, act_s[s]};
            end
            if (go) begin
                for (s = 0; s < NSM; s = s + 1) begin
                    if (st_pend[s] && cmd_h[s*CW] && sm_ret[s*4 + 0]) st_pend[s] <= 1'b0;
                    if (d_pend[s] && cmd_h[s*CW + 48] && sm_ret[s*4 + 1]) d_pend[s] <= 1'b0;
                end
                if (pend0_r && st_pend == 0 && d_pend == 0 && rr_nz == 0) begin go <= 1'b0; ip <= ip + 1'b1; end
            end
          end else begin : g_iss1
            // ---- DE descriptor pass (pointer dp): stations, then the descriptor / chunk handshakes; not behind the x
            if (!dgo && !fld_v && !fq_v && dp != tail && !(d2_v) && !halt_q) begin
                fq_v <= 1'b1; scnt <= 4'd0;
                fmt_d <= e_f[ix(dp)]; g_d <= e_g[ix(dp)];
                f_m <= e_m[ix(dp)]; f_q <= e_q[ix(dp)]; f_lq <= e_lq[ix(dp)]; f_ml <= e_ml[ix(dp)]; f_l0 <= e_l0[ix(dp)];
            end
            if (fq_v) begin
                if (scnt == 4'(SLAT)) begin
                    fq_v <= 1'b0; fld_v <= 1'b1;
                    for (s = 0; s < NSM; s = s + 1) begin
                        act_s[s] <= st_act[s];
                        rows_s[s*13 +: 13] <= st_rows[s*13 +: 13]; dl_s[s*24 +: 24] <= st_dl[s*24 +: 24];
                        dbase_s[s*32 +: 32] <= st_db[s*32 +: 32];
                    end
                end else scnt <= scnt + 4'd1;
            end
            if (fld_v) begin
                fld_v <= 1'b0; dgo <= 1'b1; d_pend <= (CR != 0) ? {NSM{1'b0}} : act_s;
                e_act[ix(dp)] <= act_s; e_rows[ix(dp)] <= rows_s; e_sd[ix(dp)] <= 1'b1;
                rr_s <= rows_s; lr_s <= dl_s; nb_s <= dbase_s; rr_nz <= (CR != 0) ? act_s : {NSM{1'b0}};
                chl <= ((fmt_d == 2'd3) ? {14'd0, g_d, 2'b00} : {13'd0, g_d, 3'b000}) << LCH;
            end
            if (dgo) begin
                for (s = 0; s < NSM; s = s + 1)
                    if (d_pend[s] && cmd_h[s*CW + 48] && sm_ret[s*4 + 1]) d_pend[s] <= 1'b0;
                if (pendd_r && d_pend == 0 && rr_nz == 0) begin dgo <= 1'b0; dp <= dp + 1'b1; end
            end
            // ---- DE start pass (pointer ip): the entry's stored per-SM rows, when its x is in the store
            if (!go && !sq_v && ip != tail && e_sd[ix(ip)] && ip != xp && (MUT_DE != 0 || e_xd[ix(ip)]) && ppc != ip && !halt_q) begin
                sq_v <= 1'b1; srows_s <= e_rows[ix(ip)]; sact_s <= e_act[ix(ip)];
                fmt_i <= e_f[ix(ip)]; g_i <= e_g[ix(ip)]; xb_i <= e_xb[ix(ip)];
            end
            if (sq_v) begin
                sq_v <= 1'b0; go <= 1'b1; st_pend <= sact_s;
                for (s = 0; s < NSM; s = s + 1) e_tgt[ix(ip)][s*4 +: 4] <= iss_cnt[s*4 +: 4] + {3'd0, sact_s[s]};
                for (s = 0; s < NSM; s = s + 1) iss_cnt[s*4 +: 4] <= iss_cnt[s*4 +: 4] + {3'd0, sact_s[s]};
            end
            if (go) begin
                for (s = 0; s < NSM; s = s + 1)
                    if (st_pend[s] && cmd_h[s*CW] && sm_ret[s*4 + 0]) st_pend[s] <= 1'b0;
                if (pends_r && st_pend == 0) begin go <= 1'b0; ip <= ip + 1'b1; end
            end
          end
            // smmv-cr chunk issue, per SM (CR = 1): the chunk's fields land in the command registers while d_pend is
            // low, then d_pend shows it; credits -n at the issue, +1 per landed sm_cr pulse (always counted)
            if (CR != 0) begin : g_chunk
                reg [12:0] n; reg [23:0] ln; reg [CRW-1:0] c; reg gk;
                for (s = 0; s < NSM; s = s + 1) begin
                    n  = (rr_s[s*13 +: 13] <= CHE) ? rr_s[s*13 +: 13] : 13'(CHE);
                    ln = (rr_s[s*13 +: 13] <= CHE) ? lr_s[s*24 +: 24] : chl;
                    c  = cr_s[s*CRW +: CRW];
                    gk = ((DE != 0) ? dgo : go) && !d_pend[s] && rr_nz[s] && ({{(32-CRW){1'b0}}, c} >= {19'd0, n});
                    if (gk) begin
                        dbase_s[s*32 +: 32] <= nb_s[s*32 +: 32]; dl_s[s*24 +: 24] <= ln; d_pend[s] <= 1'b1;
                        nb_s[s*32 +: 32] <= nb_s[s*32 +: 32] + {8'd0, ln}; lr_s[s*24 +: 24] <= lr_s[s*24 +: 24] - ln;
                        rr_s[s*13 +: 13] <= rr_s[s*13 +: 13] - n; rr_nz[s] <= (rr_s[s*13 +: 13] != n);
                    end
                    cr_s[s*CRW +: CRW] <= c + {{(CRW-1){1'b0}}, cri[s]} - (gk ? n[CRW-1:0] : {CRW{1'b0}});
                end
            end
            // ---- completions: one arrive toggle = one op of that SM done
            for (s = 0; s < NSM; s = s + 1) begin
                arr_prev[s] <= ret_q[s*4 + 2];
                if (ret_q[s*4 + 2] != arr_prev[s]) done_cnt[s*4 +: 4] <= done_cnt[s*4 +: 4] + 4'd1;
            end
            // ---- retire the head in order
            rh_wait <= 1'b0;
            if (ret_go) begin
                rec_done <= 1'b1; rh <= rh + 1'b1; rh_wait <= 1'b1;
                if (MUT_SLOT == 0) used_n = used_n - e_rel[ix(rh)];
                for (s = 0; s < NSM; s = s + 1) if (e_act[ix(rh)][s]) rel[s] <= ~rel[s];
            end
            used <= used_n;
            al_age <= (x_ev || d2_v) ? 2'd0 : (al_age == 2'd2) ? 2'd2 : al_age + 2'd1;
            if (!halt_q && (any_fault || in_xf || in_pf)) begin rec_fault <= 1'b1; halt_q <= 1'b1; end
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_hgi_smmv_pub: RECORD-PIPELINED publication (track B).  Transaction contract of ot_hgi_sm_pub_ff, except that it
// queues up to W commands (pub_rdy = queue not full) and pub_done pulses once per command, in order.  Every SM walks
// the command queue with its own pointer: its rows 0 .. R_s - 1 belong to its current command (R_s = clamp(M - s Q,
// 0, Q)), then the pointer moves on, so rows of record N+1 may arrive while record N's writes are still in flight.
// The VM word address of a row is formed per (SM, slot) from that SM's current command; the coalescing buffer flushes
// on a sector OR command change; every write / STREAM beat carries its command tag; command i is done when every SM
// has moved past it and no buffer, pending flush, FIFO entry or client write of tag i remains.  Overrun -> pub_fault.
// Flop form (functional reference of the hierarchical slice port; see SPEC.md section 2.6).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_smmv_pub #(
    parameter integer NSM = 8,
    parameter integer NC = 8,
    parameter integer NPC = 4,
    parameter integer W = 4,
    parameter integer MUT_ROW = 0
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire [4:0]         sm_base,       // static strap: global index of local SM 0 (B2 cluster c: 8c)
    input  wire               pub_v,
    output wire               pub_rdy,
    input  wire [39:0]        pub_base,
    input  wire [31:0]        pub_stride,
    input  wire [1:0]         pub_space,
    input  wire [19:0]        pub_m,
    input  wire [12:0]        pub_q,
    input  wire [3:0]         pub_p,
    input  wire               pub_bf16,
    output reg                pub_done,
    output reg                pub_fault,
    input  wire [NSM-1:0]     sm_rv,
    input  wire [NSM*12-1:0]  sm_rrow,
    input  wire [NSM*NC*32-1:0] sm_rdata,
    output reg  [NPC*338-1:0] vmq,
    input  wire [NPC*274-1:0] vmr,
    output reg                s0_v,
    output reg  [19:0]        s0_idx,
    output reg  [31:0]        s0_data
);
    localparam integer NB = NSM * NC, QD = 16;
    reg [4:0] smb_q; always @(posedge clk) smb_q <= sm_base;
    localparam integer WI = (W > 1) ? $clog2(W) : 1;
    localparam integer WA = 1 << WI;
    localparam integer SQ = WI + 1, SH = 53 + SQ;     // seq bits; STREAM shadow entry {tag, bf, idx 20, data 32}
    reg [SQ-1:0] ct, chd;                                     // command tail / done head (SQ-b seq)
    reg [17:0] c_ob [0:WA-1]; reg [17:0] c_ost [0:WA-1]; reg [19:0] c_mm [0:WA-1]; reg [12:0] c_qq [0:WA-1];
    reg [3:0] c_pp [0:WA-1]; reg [WA-1:0] c_sm, c_bf;
    // el1013: the occupancy is taken at SQ bits.  It was ((ct - chd) < W) with W a 32-b parameter: the subtraction ran at
    // 32 bits, so after ct wrapped (the 17th command) it read as 2^32 - n and pub_rdy stayed low until chd wrapped too,
    // i.e. until the queue was EMPTY -- the 17th record of every 16 waited for 7 retires (+176 cycles, L0 record 17).
    wire [SQ-1:0] c_occ = ct - chd;
    assign pub_rdy = rst_n && (c_occ < SQ'(W));
    function automatic [31:0] rb(input [31:0] x, input en);
        reg [31:0] r;
        begin
            if (!en) rb = x;
            else if (x[30:23] == 8'hFF && x[22:0] != 0) rb = {x[31:16] | 16'h0040, 16'd0};
            else begin r = x + 32'h7FFF + {31'd0, x[16]}; rb = {r[31:16], 16'd0}; end
        end
    endfunction
    function automatic [255:0] rb8(input [255:0] x, input en);
        integer q; for (q = 0; q < 8; q = q + 1) rb8[32*q +: 32] = rb(x[32*q +: 32], en);
    endfunction
    reg [NSM-1:0] rv_q; reg [11:0] rr_q [0:NSM-1]; reg [NC*32-1:0] rd_q [0:NSM-1];
    integer s, c;
    always @(posedge clk) for (s = 0; s < NSM; s = s + 1) begin rv_q[s] <= sm_rv[s]; rr_q[s] <= sm_rrow[s*12 +: 12];
                                                                rd_q[s] <= sm_rdata[s*NC*32 +: NC*32]; end
    // per-SM command pointer and rows of the current command
    reg [SQ-1:0] rp [0:NSM-1]; reg [12:0] recv [0:NSM-1];
    reg [12:0] need [0:NSM-1]; reg [NSM-1:0] has;           // has: the SM's pointer is at a queued command
    always @* for (s = 0; s < NSM; s = s + 1) begin : nd
        reg [19:0] r0; reg [WI-1:0] k;
        k = rp[s][WI-1:0]; r0 = (smb_q + s[4:0]) * c_qq[k];
        has[s] = (rp[s] != ct);
        need[s] = (c_mm[k] > r0) ? (((c_mm[k] - r0) > {7'd0, c_qq[k]}) ? c_qq[k] : (c_mm[k] - r0)) : 13'd0;
    end
    reg [NB-1:0] bval, fv, sv, ovr;
    wire [NB*15-1:0] fsec_v; wire [NB*256-1:0] fdat_v; wire [NB*8-1:0] fmsk_v; wire [NB*SH-1:0] shd_v;
    wire [NB*SQ-1:0] ftag_v; wire [NB-1:0] fbf_v;
    reg [3:0] qn, qh, qt;
    reg [14:0] qsec [0:QD-1]; reg [255:0] qdat [0:QD-1]; reg [7:0] qmsk [0:QD-1]; reg [SQ-1:0] qtag [0:QD-1]; reg [QD-1:0] qbf;
    wire [NB-1:0] req = fv | sv;
    reg gv; integer gk;
    always @* begin gv = 1'b0; gk = 0; for (c = NB - 1; c >= 0; c = c - 1) if (req[c]) begin gv = 1'b1; gk = c; end end
    wire g_str = sv[gk] && !fv[gk];                          // a pending flush first, else a STREAM beat
    wire take = gv && (g_str || qn < QD - 1);
    reg [NPC-1:0] cbusy; reg [SQ-1:0] ctag [0:NPC-1]; reg [273:0] vr [0:NPC-1];
    always @(posedge clk) for (c = 0; c < NPC; c = c + 1) vr[c] <= vmr[c*274 +: 274];
    // tag-of-head occupancy (registered reductions; done one edge later)
    wire [NB-1:0] hb_occ;
    genvar gs, gp;
    generate for (gs = 0; gs < NSM; gs = gs + 1) begin : g_s
        wire [WI-1:0] k = rp[gs][WI-1:0];
        wire sm_m = c_sm[k];
        for (gp = 0; gp < NC; gp = gp + 1) begin : g_p
            localparam integer K = gs * NC + gp;
            wire res = rv_q[gs] && has[gs] && (gp < c_pp[k]);
            wire [31:0] wd = {14'd0, c_ob[k]} + gp * {14'd0, c_ost[k]} + (MUT_ROW ? 32'd0 : {27'd0, smb_q + 5'(gs)} * {19'd0, c_qq[k]}) + {20'd0, rr_q[gs]};
            wire [19:0] gidx = gp * c_mm[k] + (MUT_ROW ? 20'd0 : {15'd0, smb_q + 5'(gs)} * {7'd0, c_qq[k]}) + {8'd0, rr_q[gs]};
            wire tk = take && gk == K;
            reg [14:0] bsec, fsec; reg [255:0] bdat, fdat; reg [7:0] bmsk, fmsk; reg [SQ-1:0] btag, ftag; reg bbf, fbf;
            reg [SH-1:0] sent [0:3]; reg [1:0] sw_, sr_; reg [2:0] scnt;
            assign fsec_v[K*15 +: 15] = fsec; assign fdat_v[K*256 +: 256] = fdat; assign fmsk_v[K*8 +: 8] = fmsk;
            assign ftag_v[K*SQ +: SQ] = ftag; assign fbf_v[K] = fbf; assign shd_v[K*SH +: SH] = sent[sr_];
            wire chg = res && !sm_m && bval[K] && (bsec != wd[17:3] || btag != rp[gs]);
            wire endf = bval[K] && !res && !fv[K] && btag != rp[gs];
            assign hb_occ[K] = (bval[K] && btag == chd) || (fv[K] && ftag == chd) || (scnt != 0 && sent[sr_][SH-1:53] == chd);
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin bval[K] <= 1'b0; fv[K] <= 1'b0; sv[K] <= 1'b0; ovr[K] <= 1'b0; sw_ <= 2'd0;
                                  sr_ <= 2'd0; scnt <= 3'd0; end
                else begin
                    ovr[K] <= 1'b0;
                    if (tk && !g_str) fv[K] <= 1'b0;
                    begin : sq
                        reg push, pop; reg [2:0] n;
                        push = res && sm_m; pop = tk && g_str; n = scnt;
                        if (push && n == 3'd4 && !pop) ovr[K] <= 1'b1;
                        else if (push) begin sent[sw_] <= {rp[gs], c_bf[k], gidx, rd_q[gs][32*gp +: 32]}; sw_ <= sw_ + 2'd1; end
                        if (pop) sr_ <= sr_ + 2'd1;
                        n = n + ((push && !(n == 3'd4 && !pop)) ? 3'd1 : 3'd0) - (pop ? 3'd1 : 3'd0);
                        scnt <= n; sv[K] <= (n != 3'd0);
                    end
                    if (chg || endf) begin
                        if (fv[K] && !(tk && !g_str)) ovr[K] <= 1'b1;
                        fv[K] <= 1'b1; fsec <= bsec; fdat <= bdat; fmsk <= bmsk; ftag <= btag; fbf <= bbf;
                        if (endf) bval[K] <= 1'b0;
                    end
                    if (res && !sm_m) begin
                        if (chg || !bval[K]) begin
                            bdat <= {224'd0, rd_q[gs][32*gp +: 32]} << {wd[2:0], 5'd0}; bmsk <= 8'd1 << wd[2:0];
                        end else begin
                            bdat <= bdat | ({224'd0, rd_q[gs][32*gp +: 32]} << {wd[2:0], 5'd0});
                            bmsk <= bmsk | (8'd1 << wd[2:0]);
                        end
                        bsec <= wd[17:3]; bval[K] <= 1'b1; btag <= rp[gs]; bbf <= c_bf[k];
                    end
                end
            end
        end
    end endgenerate
    reg head_busy_r, sm_past_r;
    always @(posedge clk) begin : hb
        reg o; integer j;
        o = |hb_occ;
        for (j = 0; j < QD; j = j + 1) if (((j - qh) & (QD - 1)) < qn && qtag[j] == chd) o = 1'b1;
        for (j = 0; j < NPC; j = j + 1) if (cbusy[j] && ctag[j] == chd) o = 1'b1;
        head_busy_r <= o;
        sm_past_r = 1'b1;
        for (j = 0; j < NSM; j = j + 1) if (rp[j] == chd) sm_past_r = 1'b0;
    end
    reg dwait;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ct <= 0; chd <= 0; pub_done <= 1'b0; pub_fault <= 1'b0; qh <= 0; qt <= 0; qn <= 0; cbusy <= 0; dwait <= 1'b0;
            vmq <= 0; s0_v <= 1'b0; s0_idx <= 20'd0; s0_data <= 32'd0; c_sm <= 0; c_bf <= 0;
            for (s = 0; s < NSM; s = s + 1) begin rp[s] <= '0; recv[s] <= 13'd0; end
        end else begin
            pub_done <= 1'b0; s0_v <= 1'b0; dwait <= 1'b0;
            for (c = 0; c < NPC; c = c + 1) vmq[c*338 + 337] <= 1'b0;
            if (|ovr) pub_fault <= 1'b1;
            if (pub_v && pub_rdy) begin
                if (!(pub_space == 2'd1 || pub_space == 2'd2) || pub_p == 4'd0 || pub_p > NC) pub_fault <= 1'b1;
                else begin
                    c_ob[ct[WI-1:0]] <= pub_base[17:0]; c_ost[ct[WI-1:0]] <= pub_stride[17:0]; c_mm[ct[WI-1:0]] <= pub_m;
                    c_qq[ct[WI-1:0]] <= pub_q; c_pp[ct[WI-1:0]] <= pub_p; c_sm[ct[WI-1:0]] <= (pub_space == 2'd2);
                    c_bf[ct[WI-1:0]] <= pub_bf16; ct <= ct + 1'b1;
                end
            end
            // per-SM pointer: a row of the current command; move on after its R_s rows (or at once if R_s = 0)
            for (s = 0; s < NSM; s = s + 1) begin
                if (rv_q[s] && (!has[s] || need[s] == 13'd0)) pub_fault <= 1'b1;            // a row with no command
                else if (rv_q[s]) begin
                    if (recv[s] + 13'd1 == need[s]) begin recv[s] <= 13'd0; rp[s] <= rp[s] + 1'b1; end
                    else recv[s] <= recv[s] + 13'd1;
                end else if (has[s] && need[s] == 13'd0) rp[s] <= rp[s] + 1'b1;
            end
            if (take) begin
                if (g_str) begin s0_v <= 1'b1; s0_idx <= shd_v[gk*SH + 32 +: 20]; s0_data <= rb(shd_v[gk*SH +: 32], shd_v[gk*SH + 52]); end
                else begin qsec[qt] <= fsec_v[gk*15 +: 15]; qdat[qt] <= fdat_v[gk*256 +: 256]; qmsk[qt] <= fmsk_v[gk*8 +: 8];
                           qtag[qt] <= ftag_v[gk*SQ +: SQ]; qbf[qt] <= fbf_v[gk]; end
            end
            begin : dr
                reg taken; taken = 1'b0;
                for (c = 0; c < NPC; c = c + 1)
                    if (!taken && !cbusy[c] && qn != 0) begin
                        vmq[c*338 +: 338] <= {1'b1, 1'b1, 12'd0, qsec[qh], 5'd0, rb8(qdat[qh], qbf[qh]),
                                              {{4{qmsk[qh][7]}}, {4{qmsk[qh][6]}}, {4{qmsk[qh][5]}}, {4{qmsk[qh][4]}},
                                               {4{qmsk[qh][3]}}, {4{qmsk[qh][2]}}, {4{qmsk[qh][1]}}, {4{qmsk[qh][0]}}}, 16'h5042};
                        cbusy[c] <= 1'b1; ctag[c] <= qtag[qh]; taken = 1'b1;
                    end
                qh <= qh + (taken ? 4'd1 : 4'd0);
                qt <= qt + ((take && !g_str) ? 4'd1 : 4'd0);
                qn <= qn + ((take && !g_str) ? 4'd1 : 4'd0) - (taken ? 4'd1 : 4'd0);
            end
            for (c = 0; c < NPC; c = c + 1) if (cbusy[c] && vr[c][273] && vr[c][256]) cbusy[c] <= 1'b0;
            // command chd done: every SM past it, nothing of tag chd anywhere (registered view + no take this edge)
            if (chd != ct && !dwait && sm_past_r && !head_busy_r) begin
                pub_done <= 1'b1; chd <= chd + 1'b1; dwait <= 1'b1;
            end
        end
    end
endmodule
// ---------------------------------------------------------------------------------------------------------------------
// smmv-b r2 (2026-10-12, route r1-6e530654e TT -141 ps: every failing class was a ripple carry chain -- ABC maps each
// adder / multiplier / compare to a MAJ chain, ~31 ps a bit -- 20 to 37 bits in one edge): HELD-INPUT MULTI-EDGE ARITHMETIC.
// Inputs must stay constant for LAT edges (the engine holds its decode / station operand registers while a counter runs);
// every edge carries at most SEG = 12 carry bits or R carry-save rows, so no stage depends on ABC's adder structure.
// ot_hgi_smmv_padd: s = a + b (SUB 0) or a - b (SUB 1) mod 2^W, carry-segmented, LAT = ceil(W / SEG).
module ot_hgi_smmv_padd #(parameter integer W = 32, parameter integer SUB = 0, parameter integer SEG = 12) (
    input  wire         clk,
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    output wire [W-1:0] s
);
    localparam integer NC = (W + SEG - 1) / SEG;
    wire [W-1:0] bb = (SUB != 0) ? ~b : b;
    reg  [W-1:0] sr;
    reg  [NC:0]  cy;                      // cy[j]: registered carry into segment j (cy[0] unused)
    genvar j;
    for (j = 0; j < NC; j = j + 1) begin : g_seg
        localparam integer LO = j * SEG;
        localparam integer WS = ((LO + SEG) <= W) ? SEG : (W - LO);
        wire ci = (j == 0) ? (SUB != 0) : cy[j];
        wire [WS:0] t = {1'b0, a[LO +: WS]} + {1'b0, bb[LO +: WS]} + {{WS{1'b0}}, ci};
        always @(posedge clk) begin sr[LO +: WS] <= t[WS-1:0]; cy[j+1] <= t[WS]; end
    end
    assign s = sr;
endmodule

// ot_hgi_smmv_pmul: p = a * b mod 2^WP; R multiplier bits a stage into a carry-save pair (R+2 -> 2 by a chain of R 3:2
// compressors, no carry propagation), then the carry-segmented final add.  LAT = ceil(WB / R) + ceil(WP / SEG).
module ot_hgi_smmv_pmul #(parameter integer WA = 8, parameter integer WB = 8, parameter integer WP = 16,
                          parameter integer R = 4, parameter integer SEG = 12) (
    input  wire          clk,
    input  wire [WA-1:0] a,
    input  wire [WB-1:0] b,
    output wire [WP-1:0] p
);
    localparam integer NS = (WB + R - 1) / R;
    reg  [WP*NS-1:0] ssr, ccr;
    wire [WP*(NS+1)-1:0] ssw = {ssr, {WP{1'b0}}};
    wire [WP*(NS+1)-1:0] ccw = {ccr, {WP{1'b0}}};
    wire [WP-1:0] ax;
    genvar k;
    for (k = 0; k < WP; k = k + 1) begin : g_ax
        assign ax[k] = (k < WA) ? a[(k < WA) ? k : 0] : 1'b0;
    end
    for (k = 0; k < NS; k = k + 1) begin : g_cs
        reg [WP-1:0] x0, x1, x2;
        integer j, bi;
        always @(posedge clk) begin
            x0 = ssw[k*WP +: WP]; x1 = ccw[k*WP +: WP];
            for (j = 0; j < R; j = j + 1) begin
                bi = k * R + j;
                x2 = (bi < WB && b[(bi < WB) ? bi : 0]) ? (ax << bi) : {WP{1'b0}};
                {x0, x1} = {x0 ^ x1 ^ x2, ((x0 & x1) | (x0 & x2) | (x1 & x2)) << 1};
            end
            ssr[k*WP +: WP] <= x0; ccr[k*WP +: WP] <= x1;
        end
    end
    ot_hgi_smmv_padd #(.W(WP), .SUB(0), .SEG(SEG)) u_cpa (.clk(clk), .a(ssr[(NS-1)*WP +: WP]), .b(ccr[(NS-1)*WP +: WP]), .s(p));
endmodule
`default_nettype wire
