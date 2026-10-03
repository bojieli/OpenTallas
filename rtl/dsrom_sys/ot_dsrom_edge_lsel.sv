`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DeepSeek-V4.1 ROM EDGE INDEX SCORER: the per-HBM-stack local streamed top-K.
// (default-off successor block; nothing instantiates it unless the die selects
// the edge scorer -- see ot_dsrom_idx_edge.sv)
//
// Semantics.  tools/hdc_golden_v41.py `indexer` keeps
//     sorted(topk_lowest_index(s, min(512, n)))
// i.e. the K largest BF16 scores, ties to the LOWER position, +0 == -0, -inf
// ordered last; NaN is outside the contract.  This is a strict total order
//     a < b  <=>  key(a) > key(b)  or  (key(a) == key(b) and pos(a) < pos(b)).
// One HBM stack owns the positions p with (p >> 4) & 3 == s (16-key round
// robin); its scores arrive here in ascending position order.  This unit keeps
// the stack's exact local top-K and emits it in ascending position order; the
// hub (ot_dsrom_edge_hub) merges the four stacks' lists by position and takes
// the exact global top-K of the union -- the global top-K is contained in the
// union of the local top-Ks for any strict total order (class A).
//
// Streaming fold.  The unit never stores the stack's scan.  It keeps
//   S  the exact top-K of every score folded so far (<= K, position order,
//      at most K/W + 1 W-lane lines of flops), and
//   T  the key of the K-th element of S, valid once |S| == K.
// A score whose key is <= T is dropped at ingest: S holds K elements, every
// one with key >= T and an earlier position, and each of them is beaten only by
// elements that beat it in turn, so K elements beat the dropped one for the
// rest of the scan.  Survivors (key > T, or every score before T is valid) are
// compacted from LI-lane beats into dense W-lane lines and queued in a line
// FIFO (one 1R1W memory).  Whenever the selector is idle and the FIFO holds a
// line, a fold streams S followed by up to NC FIFO lines -- all in position
// order, S first -- into the qualified threshold selector ot_hdc_tselect
// (unchanged), whose exact top-K of that segment becomes the new S:
//     topK(A ++ B) = topK(topK(A) ++ B)   (A before B in position order).
// After the scan's last score, the last partial line is flushed, the final
// fold runs, and S leaves on the hub link as LO-lane beats, ascending position.
//
// Memory.  The selector's line memory is VIRTUAL: lines 0 .. nS-1 of a fold
// are the S flops, lines nS .. are the FIFO lines in place (the selector's
// own writes are redundant and only checked in simulation).  The FIFO read
// port is registered once more after the macro (2-cycle read), and the
// selector's 1-cycle read contract is kept by issuing every pass read one
// cycle early: ot_hdc_tselect reads its lines strictly in sequence 0, 1, ..,
// nlast in each pass, so the next address is (re ? raddr + 1 : 0).  The
// prediction is asserted in simulation.
//
// Throughput.  A fold of n lines occupies the selector ~3 (K/W + 1 + n) + 54
// cycles and absorbs n W-lane lines, so with W = 64 and NC = 32 the unit keeps
// up with 11.7 survivors/cycle even when EVERY score survives (ascending
// scores), above one HBM3E stack's 0.9 TB/s = 11.0 keys/cycle at 1.2 GHz.  The
// line FIFO (2^FA lines) back-pressures the score array when it fills.
// ---------------------------------------------------------------------------

// 1R1W line memory: behavioural (MACRO = 0) or tiles of the aligned ASAP7
// 128 x 256 SRAM macro (MACRO = 1, AW <= 7).  One-cycle synchronous read,
// read-before-write on an address collision (the macro's own behaviour).
module ot_dsrom_edge_ram #(
    parameter integer AW    = 7,
    parameter integer DW    = 2368,
    parameter integer MACRO = 0
) (
    input  wire          clk,
    input  wire          re,
    input  wire [AW-1:0] raddr,
    output wire [DW-1:0] rdata,
    input  wire          we,
    input  wire [AW-1:0] waddr,
    input  wire [DW-1:0] wdata
);
    generate
        if (MACRO != 0) begin : g_mac
            localparam integer MW = 256;
            localparam integer NT = (DW + MW - 1) / MW;
            wire [NT*MW-1:0] rd;
            wire [NT*MW-1:0] wd = {{(NT*MW-DW){1'b0}}, wdata};
            wire [6:0] ra = {{(7-AW){1'b0}}, raddr};
            wire [6:0] wa = {{(7-AW){1'b0}}, waddr};
            genvar t;
            for (t = 0; t < NT; t = t + 1) begin : g_t
                ot_sram_1r1w_128x256_m1_r2c2 u_m (
                    .clk(clk), .r_ce_in(re), .r_addr_in(ra), .rd_out(rd[MW*t +: MW]),
                    .w_ce_in(we), .w_addr_in(wa), .wd_in(wd[MW*t +: MW]), .w_mask_in({MW{1'b1}}),
                    .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
            end
            assign rdata = rd[DW-1:0];
        end else begin : g_beh
            reg [DW-1:0] m [0:(1 << AW) - 1];
            reg [DW-1:0] q;
            always @(posedge clk) begin
                if (re) q <= m[raddr];
                if (we) m[waddr] <= wdata;
            end
            assign rdata = q;
        end
    endgenerate
endmodule

module ot_dsrom_edge_lsel #(
    parameter integer LI    = 16,     // score lanes per input beat
    parameter integer W     = 64,     // selector lanes
    parameter integer VW    = 16,     // BF16 scores
    parameter integer IW    = 20,     // global position width
    parameter integer K     = 512,    // index top-k
    parameter integer NC    = 32,     // FIFO lines folded per selection, at most
    parameter integer FA    = 7,      // FIFO address bits: 2^FA lines
    parameter integer LO    = 16,     // hub link lanes
    parameter integer MACRO = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,          // a new scan; legal only when !busy
    input  wire              in_valid,
    output wire              in_ready,
    input  wire              in_last,        // last beat of the stack's scan (may be empty)
    input  wire [LI-1:0]     in_lv,
    input  wire [LI*VW-1:0]  in_val,
    input  wire [LI*IW-1:0]  in_idx,         // ascending across lanes and beats
    output reg               out_valid,
    input  wire              out_ready,
    output reg               out_last,
    output reg  [LO-1:0]     out_lv,
    output reg  [LO*VW-1:0]  out_val,
    output reg  [LO*IW-1:0]  out_idx,
    output wire              busy,
    output reg  [31:0]       st_folds,       // selector folds this scan
    output reg  [31:0]       st_pass,        // scores that survived the threshold
    output reg  [31:0]       st_lines,       // FIFO lines written
    output reg  [31:0]       st_stall        // in_valid && !in_ready cycles
);
    localparam integer EW  = 1 + VW + IW;            // {lv, value, position}
    localparam integer KL  = K / W;
    localparam integer SL  = KL + 1;                 // S lines: K/W full + a possibly empty last
    localparam integer TAW = $clog2(SL + NC);
    localparam integer KW  = $clog2(K + 1);
    localparam integer LW  = $clog2(W);
    localparam integer RW  = $clog2(LI + 1);         // rank / count width
    localparam integer LIX = (LI > 1) ? $clog2(LI) : 1;
    localparam integer PD  = 4;                      // compaction stages before the FIFO write
    localparam integer FD  = 1 << FA;
    localparam integer SW  = $clog2(SL + 1);
    localparam integer OPL = W / LO;                 // link beats per S line
    localparam integer OBW = $clog2(K / LO + 2);
    localparam [KW-1:0]  KK  = K;
    localparam [KW:0]    KK1 = K;
    localparam [FA:0]    NCF = NC;
    localparam [TAW:0]   NCT = NC;

    function automatic [VW-1:0] fkey(input [VW-1:0] v);
        fkey = (v[VW-2:0] == 0) ? {1'b1, {(VW-1){1'b0}}} : v[VW-1] ? ~v : {1'b1, v[VW-2:0]};
    endfunction

    integer ia, ib, ic, jc, p, im, jm, ipc, io;

    // -- control flags -------------------------------------------------------------------
    reg            scan;                             // between start and the accepted last beat
    reg            in_done;                          // the last beat has reached the FIFO
    reg  [FA:0]    fcnt;                             // FIFO lines held (including the fold's)
    reg  [FA-1:0]  fhead, ftail;
    reg            tv;                               // threshold valid (|S| == K)
    reg  [VW-1:0]  tk;                               // threshold key
    wire           take = in_valid && in_ready;
    assign in_ready = scan && ({1'b0, fcnt} + PD + 3 <= FD);

    // -- stage A: threshold prefilter -------------------------------------------------------
    reg            a_v, a_l;
    reg  [LI-1:0]  a_p;
    reg  [LI*EW-1:0] a_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin a_v <= 1'b0; a_l <= 1'b0; end
        else begin a_v <= take; a_l <= take && in_last; end
    end
    always @(posedge clk) if (take)
        for (ia = 0; ia < LI; ia = ia + 1) begin
            a_p[ia] <= in_lv[ia] && (!tv || fkey(in_val[VW*ia +: VW]) > tk);
            a_e[EW*ia +: EW] <= {1'b1, in_val[VW*ia +: VW], in_idx[IW*ia +: IW]};
        end

    // -- stage B: exclusive ranks of the survivors -------------------------------------------
    reg            b_v, b_l;
    reg  [LI-1:0]  b_p;
    reg  [LI*EW-1:0] b_e;
    reg  [LI*RW-1:0] b_r;
    reg  [RW-1:0]  b_m;
    reg  [RW-1:0]  rk;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin b_v <= 1'b0; b_l <= 1'b0; end
        else begin b_v <= a_v; b_l <= a_l; end
    end
    always @(posedge clk) begin
        rk = 0;
        for (ib = 0; ib < LI; ib = ib + 1) begin
            b_r[RW*ib +: RW] <= rk;
            rk = rk + {{(RW-1){1'b0}}, a_p[ib]};
        end
        b_m <= rk;
        b_p <= a_p;
        b_e <= a_e;
    end

    // -- stage C: dense block (survivor of rank r in lane r) ---------------------------------
    reg            c_v, c_l;
    reg  [LI*EW-1:0] c_d;
    reg  [RW-1:0]  c_m;
    reg  [EW-1:0]  sel;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin c_v <= 1'b0; c_l <= 1'b0; end
        else begin c_v <= b_v; c_l <= b_l; end
    end
    always @(posedge clk) begin
        for (jc = 0; jc < LI; jc = jc + 1) begin
            sel = {EW{1'b0}};
            for (ic = jc; ic < LI; ic = ic + 1)
                if (b_p[ic] && b_r[RW*ic +: RW] == jc[RW-1:0]) sel = sel | b_e[EW*ic +: EW];
            c_d[EW*jc +: EW] <= sel;
        end
        c_m <= b_m;
    end

    // -- stage D: place at the running fill, emit complete W-lane lines ------------------------
    reg  [LW-1:0]  fill;
    reg  [W*EW-1:0] acc;
    reg            flush;                            // the scan's partial line leaves next cycle
    reg            l_we;
    reg  [W*EW-1:0] l_wd;
    reg  [W*EW-1:0] pl_hi, pl_lo;                     // placed at/after the fill, wrapped below it
    reg  [LW-1:0]  jj;
    wire [LW:0]    tot = {1'b0, fill} + {{(LW+1-RW){1'b0}}, c_m};
    always @(*) begin
        pl_hi = {W*EW{1'b0}};
        pl_lo = {W*EW{1'b0}};
        for (p = 0; p < W; p = p + 1) begin
            jj = p[LW-1:0] - fill;
            if ({{(LW+1-RW){1'b0}}, c_m} > {1'b0, jj}) begin
                if (p >= fill) pl_hi[EW*p +: EW] = c_d[EW*jj[LIX-1:0] +: EW];
                else           pl_lo[EW*p +: EW] = c_d[EW*jj[LIX-1:0] +: EW];
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fill <= 0; acc <= 0; flush <= 1'b0; l_we <= 1'b0; in_done <= 1'b0;
        end else begin
            l_we <= 1'b0;
            if (start) begin
                fill <= 0; acc <= 0; flush <= 1'b0; in_done <= 1'b0;
            end else if (flush) begin
                l_we <= 1'b1; l_wd <= acc; acc <= 0; fill <= 0; flush <= 1'b0; in_done <= 1'b1;
            end else if (c_v) begin
                if (tot[LW]) begin
                    l_we <= 1'b1; l_wd <= acc | pl_hi; acc <= pl_lo;
                end else acc <= acc | pl_hi;
                fill <= tot[LW-1:0];
                if (c_l) begin
                    if (tot[LW-1:0] != 0) flush <= 1'b1;
                    else in_done <= 1'b1;
                end
            end
        end
    end

    // -- the line FIFO (virtual selector memory backing) ---------------------------------------
    wire              f_re;
    wire [FA-1:0]     f_ra;
    wire [W*EW-1:0]   f_rd;
    ot_dsrom_edge_ram #(.AW(FA), .DW(W*EW), .MACRO(MACRO)) u_fifo (
        .clk(clk), .re(f_re), .raddr(f_ra), .rdata(f_rd),
        .we(l_we), .waddr(ftail), .wdata(l_wd));

    // -- fold controller ---------------------------------------------------------------------
    localparam [2:0] F_IDLE = 3'd0, F_FEED = 3'd1, F_SEL = 3'd2, F_TUPD = 3'd3, F_OUT = 3'd4;
    reg  [2:0]     fs;
    reg  [SW-1:0]  sn;                               // S lines held (selector output beats with a lane)
    reg  [SW-1:0]  nsl;                              // S lines replayed in this fold
    reg  [FA:0]    nfl;                              // FIFO lines in this fold
    reg  [TAW:0]   fb;                               // feed beats issued
    reg  [TAW:0]   fbt;                              // feed beats in this fold
    reg  [KW:0]    scnt, ocnt;                       // |S|, selected count of the running fold
    reg  [SW-1:0]  oj;                               // output line being collected
    reg  [2:0]     tw;
    reg            emitted;                          // S has left on the link; wait for start
    reg  [SL*W*EW-1:0] sbuf;                         // S lines (flops)

    // selector
    wire           t_in_ready, t_out_valid, t_out_last, t_busy, t_mem_we, t_mem_re;
    wire [W-1:0]   t_out_lv, t_out_ninf;
    wire [W*VW-1:0] t_out_val;
    wire [W*IW-1:0] t_out_idx;
    wire [TAW-1:0] t_mem_waddr, t_mem_raddr;
    wire [W*EW-1:0] t_mem_wdata;

    // virtual read pipeline: request (rq) -> r1 (macro access / S index) -> r2 (registered line)
    wire           feed_req = (fs == F_FEED) && (fb != fbt);
    wire           pred_req = (fs == F_SEL);
    wire [TAW:0]   pred_a   = t_mem_re ? {1'b0, t_mem_raddr} + 1'b1 : {(TAW+1){1'b0}};
    wire           rq_v     = feed_req || pred_req;
    wire [TAW:0]   rq_a     = feed_req ? fb : pred_a;
    wire           rq_s     = rq_a < {{(TAW+1-SW){1'b0}}, nsl};
    wire [TAW:0]   rq_fo    = rq_a - {{(TAW+1-SW){1'b0}}, nsl};
    assign f_re = rq_v && !rq_s;
    assign f_ra = fhead + rq_fo[FA-1:0];
    reg            r1_v, r1_s, r1_feed, r1_last;
    reg  [SW-1:0]  r1_si;
    reg            r2_v, r2_feed, r2_last;
    reg  [W*EW-1:0] r2_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin r1_v <= 1'b0; r2_v <= 1'b0; r1_feed <= 1'b0; r2_feed <= 1'b0; end
        else begin
            r1_v <= rq_v; r1_feed <= feed_req; r1_last <= feed_req && (fb + 1'b1 == fbt);
            r2_v <= r1_v; r2_feed <= r1_v && r1_feed; r2_last <= r1_last;
        end
    end
    always @(posedge clk) begin
        r1_s  <= rq_s;
        r1_si <= rq_a[SW-1:0];
        if (r1_v) r2_d <= r1_s ? sbuf[W*EW*r1_si +: W*EW] : f_rd;
    end
    wire [W-1:0]    t_in_lv;
    wire [W*VW-1:0] t_in_val;
    wire [W*IW-1:0] t_in_idx;
    genvar gl;
    generate
        for (gl = 0; gl < W; gl = gl + 1) begin : g_unp
            assign t_in_lv[gl]             = r2_d[EW*gl + EW - 1];
            assign t_in_val[VW*gl +: VW]   = r2_d[EW*gl + IW +: VW];
            assign t_in_idx[IW*gl +: IW]   = r2_d[EW*gl +: IW];
        end
    endgenerate
    wire t_in_valid = r2_feed;

    ot_hdc_tselect #(.W(W), .VW(VW), .IW(IW), .K(K), .AW(TAW)) u_tsel (
        .clk(clk), .rst_n(rst_n), .in_valid(t_in_valid), .in_ready(t_in_ready), .in_last(r2_last),
        .in_lv(t_in_lv), .in_val(t_in_val), .in_idx(t_in_idx), .in_k(KK),
        .out_valid(t_out_valid), .out_last(t_out_last), .out_lv(t_out_lv), .out_val(t_out_val),
        .out_idx(t_out_idx), .out_ninf(t_out_ninf),
        .mem_we(t_mem_we), .mem_waddr(t_mem_waddr), .mem_wdata(t_mem_wdata), .mem_re(t_mem_re),
        .mem_raddr(t_mem_raddr), .mem_rdata(r2_d), .busy(t_busy));

    // running minimum key of the selector's output (two registered levels)
    localparam integer MG = (W >= 8) ? 8 : W;
    localparam integer MN = W / MG;
    reg  [MN*VW-1:0] m1;
    reg              m1_v, m2_v;
    reg  [VW-1:0]    m2, mrun, mk;
    reg  [KW:0]      pc;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin m1_v <= 1'b0; m2_v <= 1'b0; end
        else begin m1_v <= t_out_valid; m2_v <= m1_v; end
    end
    always @(posedge clk) begin
        for (im = 0; im < MN; im = im + 1) begin
            mk = {VW{1'b1}};
            for (jm = 0; jm < MG; jm = jm + 1)
                if (t_out_lv[MG*im + jm] && fkey(t_out_val[VW*(MG*im + jm) +: VW]) < mk)
                    mk = fkey(t_out_val[VW*(MG*im + jm) +: VW]);
            m1[VW*im +: VW] <= mk;
        end
        mk = {VW{1'b1}};
        for (im = 0; im < MN; im = im + 1) if (m1[VW*im +: VW] < mk) mk = m1[VW*im +: VW];
        m2 <= mk;
    end
    always @(*) begin
        pc = 0;
        for (ipc = 0; ipc < W; ipc = ipc + 1) pc = pc + {{KW{1'b0}}, t_out_lv[ipc]};
    end

    // -- output (hub link) ----------------------------------------------------------------------
    reg  [OBW-1:0] ob, obt;
    wire [SW-1:0]  o_line = ob / OPL;
    wire [OBW-1:0] o_part = ob % OPL;
    wire           o_adv  = !out_valid || out_ready;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fs <= F_IDLE; scan <= 1'b0; fcnt <= 0; fhead <= 0; ftail <= 0; tv <= 1'b0; tk <= 0;
            sn <= 0; nsl <= 0; nfl <= 0; fb <= 0; fbt <= 0; scnt <= 0; ocnt <= 0; oj <= 0; tw <= 0;
            mrun <= {VW{1'b1}}; ob <= 0; obt <= 0; emitted <= 1'b0;
            out_valid <= 1'b0; out_last <= 1'b0; out_lv <= 0; out_val <= 0; out_idx <= 0;
            st_folds <= 0; st_pass <= 0; st_lines <= 0; st_stall <= 0;
        end else begin
            if (start) begin
                scan <= 1'b1; tv <= 1'b0; sn <= 0; scnt <= 0; emitted <= 1'b0;
                st_folds <= 0; st_pass <= 0; st_lines <= 0; st_stall <= 0;
            end else if (take && in_last) scan <= 1'b0;
            if (in_valid && !in_ready && scan) st_stall <= st_stall + 1;
            if (b_v) st_pass <= st_pass + {{(32-RW){1'b0}}, b_m};
            if (l_we) begin ftail <= ftail + 1'b1; st_lines <= st_lines + 1; end
            // FIFO count: +1 per written line, -nfl when a fold retires
            fcnt <= fcnt + {{FA{1'b0}}, l_we} - ((fs == F_SEL && t_out_valid && t_out_last) ? nfl : {(FA+1){1'b0}});
            if (fs == F_SEL && t_out_valid && t_out_last) fhead <= fhead + nfl[FA-1:0];
            if (m2_v) mrun <= (m2 < mrun) ? m2 : mrun;
            if (o_adv) out_valid <= 1'b0;
            case (fs)
                F_IDLE: begin
                    if (!start && fcnt != 0 && !t_busy) begin
                        nsl  <= sn;
                        nfl  <= (fcnt > NCF) ? NCF : fcnt;
                        fbt  <= {{(TAW+1-SW){1'b0}}, sn} + ((fcnt > NCF) ? NCT : fcnt[TAW:0]);
                        fb   <= 0;
                        oj   <= 0; ocnt <= 0; mrun <= {VW{1'b1}};
                        st_folds <= st_folds + 1;
                        fs   <= F_FEED;
                    end else if (!start && in_done && fcnt == 0 && !l_we && !scan && !t_busy && !emitted) begin
                        ob  <= 0;
                        obt <= (scnt == 0) ? 1 : (scnt + LO - 1) / LO;
                        fs  <= F_OUT;
                    end
                end
                F_FEED: begin
                    fb <= fb + 1'b1;
                    if (fb + 1'b1 == fbt) fs <= F_SEL;
                end
                F_SEL: begin
                    if (t_out_valid) begin
                        sbuf[W*EW*oj +: W*EW] <= t_mem_line(t_out_lv, t_out_val, t_out_idx);
                        oj <= oj + 1'b1;
                        ocnt <= ocnt + pc;
                        if (t_out_last) begin
                            sn <= (t_out_lv != 0) ? oj + 1'b1 : oj;
                            scnt <= ocnt + pc;
                            tw <= 3'd3;
                            fs <= F_TUPD;
                        end
                    end
                end
                F_TUPD: begin                            // the minimum pipeline drains (2 levels + run)
                    if (tw != 0) tw <= tw - 1'b1;
                    else begin
                        tk <= mrun;
                        tv <= (scnt == KK1);
                        fs <= F_IDLE;
                    end
                end
                F_OUT: begin
                    if (o_adv) begin
                        out_valid <= 1'b1;
                        out_last  <= (ob + 1'b1 == obt);
                        for (io = 0; io < LO; io = io + 1) begin
                            out_lv[io]               <= (o_line < sn) && sbuf[W*EW*o_line + EW*(LO*o_part + io) + EW - 1];
                            out_val[VW*io +: VW]     <= sbuf[W*EW*o_line + EW*(LO*o_part + io) + IW +: VW];
                            out_idx[IW*io +: IW]     <= sbuf[W*EW*o_line + EW*(LO*o_part + io) +: IW];
                        end
                        ob <= ob + 1'b1;
                        if (ob + 1'b1 == obt) begin
                            fs <= F_IDLE; emitted <= 1'b1;     // S emitted: wait for the next start
                        end
                    end
                end
                default: fs <= F_IDLE;
            endcase
        end
    end

    function automatic [W*EW-1:0] t_mem_line(input [W-1:0] lv, input [W*VW-1:0] v, input [W*IW-1:0] x);
        integer e;
        begin
            for (e = 0; e < W; e = e + 1) t_mem_line[EW*e +: EW] = {lv[e], v[VW*e +: VW], x[IW*e +: IW]};
        end
    endfunction

    assign busy = scan || (in_done && !emitted) || fs != F_IDLE || fcnt != 0 || a_v || b_v || c_v || flush;

`ifndef SYNTHESIS
    // the virtual memory: the selector's own writes must equal what is already in place, and every
    // pass read must hit the predicted address
    reg [TAW-1:0] pa_q;
    reg           pa_v;
    always @(posedge clk) begin
        pa_v <= rst_n && pred_req;
        pa_q <= pred_a[TAW-1:0];
        if (rst_n && t_mem_re && !(pa_v && pa_q == t_mem_raddr))
            $fatal(1, "edge lsel: selector read %0d not predicted", t_mem_raddr);
        if (rst_n && t_mem_we && t_mem_wdata != r2_d)
            $fatal(1, "edge lsel: selector ingest line differs from the virtual memory");
        if (rst_n && t_in_valid && !t_in_ready)
            $fatal(1, "edge lsel: selector refused a fold beat");
        if (rst_n && l_we && fcnt >= FD)
            $fatal(1, "edge lsel: line FIFO overflow");
        if (rst_n && start && busy)
            $fatal(1, "edge lsel: start while busy");
        if (rst_n && fs == F_SEL && t_out_valid && oj >= SL)
            $fatal(1, "edge lsel: S overflow");
    end
`endif
endmodule
