`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// KV streaming engine of the hardwired decode core: the KV cache in HBM.
//
// The matrix engine (ot_hdc_matvec) reads the KV cache as if it were an
// on-core SRAM: every cycle of a KV-sourced op each lane group g presents a
// word address on kv_raddr[g] and takes the word one cycle later, with no
// valid and no stall.  This engine keeps that contract with the cache in HBM.
//
// WINDOW.  An op's KV words are consumed in a fixed order: round r, then k,
// then jh = j >> jsh (the 2^jsh slots that share a word -- the GQA heads of
// one KV head), and all G groups in parallel.  One (r, k, jh) is a LINE of G
// words, consumed over 2^jsh cycles.  Lines are numbered globally across ops,
// and line n lives in slot n mod WIN of a G-bank on-core window SRAM with a
// valid bit per (slot, group).
//
// FETCH.  When the sequencer reaches a KV op it announces the op's descriptor
// (kvd_*: the same fields the engine will run, after the DYN offsets).  The
// fetcher walks the op in line order in BLOCKS and issues large sequential
// HBM reads ahead of the engine, as far as the window has free slots:
//   * K-MODE (ks == 1, scores over positions tiled on lanes): per block of up
//     to BK k-steps, one request of BK consecutive words per (group, jh);
//     beat b fills line (k0 + b, jh).
//   * G-MODE (ts == 1, the weighted sum when a position row spans several
//     words): per block of up to BK k-steps, for each jh in turn, one request
//     per k-step of the valid groups' adjacent words; beat b fills group b.
//     Each KV head is fetched as one run of BK rows before the next, so the
//     heads' streams do not alternate row by row in the DRAM banks.
// Words that are not in HBM are never fetched:
//   * ZERO: tiles past the op's valid range (t*W >= nout) -- the engine masks
//     their lanes, so any finite value serves; zero is used;
//   * TAIL: for scores ops the open position tile (pos >> log2 W) and the one
//     before it live in an on-core double-buffered TAIL SRAM (below) and are
//     read from it at consumption time.
// The completion pointer walks lines in order and passes a line once every
// HBM-sourced word of it has arrived.
//
// NO STALL.  The engine cannot stall, so an op may only START when the window
// can feed it to the end.  kv_ok (the sequencer's issue condition for the op
// it is waiting on) is raised when the completion pointer has passed the op's
// whole line range, or T = (cfg_lead >> jsh) + 1 of its lines.  cfg_lead is
// the worst-case time, in cycles, from a line's fetch becoming possible to its
// arrival (HBM latency with a row conflict and an all-bank refresh, see
// tools/rtl_hdc_kv_stream_campaign.py).  With the HBM bandwidth provisioned at
// or above the op's consumption rate (G words per 2^jsh cycles), the lead
// covers the worst-case gap, so every word is in the window before its read;
// the window must hold T lines plus the in-flight fetch (WIN >= T + blocks).
// A read of a word that has not arrived is detected (fault, sticky): the
// guarantee is checked, not assumed.
//
// WRITES.  Stream-unit KV element writes (the new K and V rows of the token):
//   * K: the K layout packs W positions per word (lane = position mod W), so a
//     new position is one lane of HD words.  HBM3 has no write data mask, so
//     the open tile is held in the TAIL SRAM (2 banks: tile parity), updated
//     lane-wise (lane 0 starts a tile: the other lanes clear), and read from
//     there; when a tile closes (the token at pos with pos mod W == 0 starts
//     the next) its bank is FLUSHED to HBM in full words during the next W
//     tokens, in idle tail cycles, before it is ever read from HBM.
//   * V: a position's row is HD contiguous elements; they are combined into
//     full words and written as one burst each.
// Writes go ahead of fetch reads, and HBM serves each pseudo-channel in order,
// so a read of a row written earlier in the token sees the new data.
//
// All memories are ports (window banks, tail banks, HBM request/response):
// the testbench supplies behavioural ones, the physical top leaves them as
// macros / the HBM controller interface.
// ---------------------------------------------------------------------------
module ot_hdc_kv_stream #(
    parameter integer W      = 16,
    parameter integer G      = 4,
    parameter integer IL     = 8,
    parameter integer AW     = 24,
    parameter integer NW     = 16,
    parameter integer LWIN   = 8,        // window: 2^LWIN lines of G words
    parameter integer NPC    = 4,        // HBM response ports (pseudo-channels)
    parameter integer BK     = 16,       // K-mode request length, words (power of 2, >= G)
    parameter integer LOG_HD = 4,        // KV layout (tools/hdc_program.py k_elem): head_dim
    parameter integer LOG_TW = 2,        //   position tiles per KV head
    parameter integer LLG    = 3,        //   layers x KV heads
    parameter integer V0_WORD = 512      //   first V word (K words below)
) (
    input  wire              clk,
    input  wire              rst_n,
    // token start (flush trigger)
    input  wire              tok_start,
    input  wire [NW-1:0]     tok_pos,
    input  wire [NW-1:0]     cfg_lead,       // worst-case fetch lead, cycles
    // descriptor of the KV op the sequencer waits on, and its issue permission
    input  wire              kvd_v,
    input  wire [AW-1:0]     kvd_wbase, kvd_ts, kvd_ks, kvd_js,
    input  wire [2:0]        kvd_jsh,
    input  wire [NW-1:0]     kvd_tiles, kvd_k, kvd_nout,
    input  wire              kvd_kindk,
    input  wire [NW-1:0]     kvd_pos,
    output reg               kv_ok,
    // matrix-engine KV read port (fixed latency 1, no stall)
    input  wire              kv_re,
    input  wire [G*AW-1:0]   kv_raddr,
    output reg  [G*W*32-1:0] kv_q,
    // stream-unit KV element writes
    input  wire              kv_we,
    input  wire [AW-1:0]     kv_waddr,
    input  wire [31:0]       kv_wdata,
    // window SRAM: G banks of 2^LWIN words (W x BF16)
    output reg  [G-1:0]      win_we,
    output reg  [G*LWIN-1:0] win_waddr,
    output reg  [G*W*16-1:0] win_wdata,
    output wire              win_re,
    output wire [LWIN-1:0]   win_raddr,
    input  wire [G*W*16-1:0] win_q,
    // tail SRAM: 2 banks (tile parity) of 2^(LLG+LOG_HD) words, lane write mask
    output reg  [1:0]        tl_we,
    output reg  [2*(LLG+LOG_HD)-1:0] tl_waddr,
    output reg  [2*W-1:0]    tl_wmask,
    output reg  [2*W*16-1:0] tl_wdata,
    output reg  [1:0]        tl_re,
    output reg  [2*(LLG+LOG_HD)-1:0] tl_raddr,
    input  wire [2*W*16-1:0] tl_q,
    // HBM request (valid/ready): reads of hq_len words, or one-word writes
    output reg               hq_v,
    input  wire              hq_rdy,
    output reg               hq_we,
    output reg  [AW-1:0]     hq_addr,
    output reg  [$clog2(BK):0] hq_len,
    output reg  [1+LWIN+$clog2(G)+3-1:0] hq_tag,
    output reg  [W*16-1:0]   hq_wdata,
    // HBM read responses, one port per pseudo-channel (valid/ready)
    input  wire [NPC-1:0]    hr_v,
    output reg  [NPC-1:0]    hr_rdy,
    input  wire [NPC*(1+LWIN+$clog2(G)+3)-1:0] hr_tag,
    input  wire [NPC*$clog2(BK)-1:0] hr_beat,
    input  wire [NPC*W*16-1:0] hr_data,
    output reg               fault
);
    localparam integer LW   = $clog2(W);
    localparam integer LG   = $clog2(G);
    localparam integer LIL  = $clog2(IL);
    localparam integer LBK  = $clog2(BK);
    localparam integer WIN  = 1 << LWIN;
    localparam integer TAW  = LLG + LOG_HD;
    localparam integer TAGW = 1 + LWIN + LG + 3;
    localparam [1:0] SRC_WIN = 2'd0, SRC_ZERO = 2'd1, SRC_T0 = 2'd2, SRC_T1 = 2'd3;

    // ---- descriptors: 2 slots (the op being consumed, the op being announced) ----
    reg [1:0]    dv, fdone, cpdone;
    reg          wptr;
    reg [AW-1:0] d_wbase [0:1], d_ts [0:1], d_ks [0:1], d_js [0:1];
    reg [2:0]    d_jsh [0:1];
    reg [NW-1:0] d_tiles [0:1], d_k [0:1], d_ntile [0:1], d_to [0:1], d_T [0:1];
    reg          d_kindk [0:1], d_kmode [0:1], d_gmode [0:1], d_capped [0:1];
    // start threshold: lines covering cfg_lead cycles, at most the window less one fetch block
    wire [NW-1:0] t_lead = (cfg_lead >> kvd_jsh) + 1'b1;
    wire [NW-1:0] t_cap = WIN - (BK << (LIL - kvd_jsh));

    // Source of group g's word in round r of slot s.
    function automatic [1:0] src_of(input [NW-1:0] r, input integer g, input [NW-1:0] ntile,
                                    input kindk, input [NW-1:0] to);
        reg [NW-1:0] t;
        begin
            t = (r << LG) + g;
            if (t >= ntile) src_of = SRC_ZERO;
            else if (kindk && (t == to || (to != 0 && t + 1'b1 == to))) src_of = t[0] ? SRC_T1 : SRC_T0;
            else src_of = SRC_WIN;
        end
    endfunction

    // ---- line counters (global, wrap-safe) and valid bits --------------------------
    reg [31:0]      fetch_line, cp_line, cons_line;
    reg [WIN*G-1:0] vbits;

    // ---- fetcher ------------------------------------------------------------------------
    reg          f_idx, f_act, blk_open;
    reg [NW-1:0] f_r, f_k0, blen;
    reg [LG-1:0] f_g;
    reg [LIL-1:0] f_jh;
    reg [AW-1:0] f_rb, f_goff, f_jhoff, f_koff, f_kkoff;
    reg [NW-1:0] f_kk;
    reg [31:0]   line_base;
    wire [2:0]   f_jsh = d_jsh[f_idx];
    wire         f_km = d_kmode[f_idx];
    wire [LIL-1:0] f_jh_end = (1 << (LIL - f_jsh)) - 1;
    wire [NW-1:0] f_krem = d_k[f_idx] - f_k0;
    wire [NW-1:0] f_blen_c = (f_krem > BK) ? BK : f_krem;
    wire [31:0]  f_blines = {16'd0, f_blen_c} << (LIL - f_jsh);
    wire         f_space = (fetch_line + f_blines - cons_line) <= WIN;
    // valid groups of a round in G-mode (a prefix: no tail in weighted-sum ops)
    wire [NW-1:0] f_rt = f_r << LG;
    wire [NW-1:0] f_nval_raw = (d_ntile[f_idx] > f_rt) ? d_ntile[f_idx] - f_rt : 0;
    wire [LBK:0] f_nval = (f_nval_raw > G) ? G : f_nval_raw[LBK:0];
    wire [1:0]   f_src = src_of(f_r, f_g, d_ntile[f_idx], d_kindk[f_idx], d_to[f_idx]);
    wire         f_emit = f_km ? (f_src == SRC_WIN) : (f_nval != 0);
    wire [31:0]  f_tline = line_base + f_jh + (f_km ? 32'd0 : ({16'd0, f_kk} << (LIL - f_jsh)));
    wire         vf_empty;
    wire         f_req_v = f_act && blk_open && f_emit && vf_empty;
    wire [AW-1:0] f_req_addr = f_km ? (f_rb + f_goff + f_k0 + f_jhoff) : (f_rb + f_koff + f_kkoff + f_jhoff);
    wire [LBK:0] f_req_len = f_km ? blen[LBK:0] : f_nval;
    wire [TAGW-1:0] f_req_tag = {!f_km, f_tline[LWIN-1:0], f_km ? f_g : {LG{1'b0}}, f_jsh};
    wire         hq_free = !hq_v || hq_rdy;
    wire         f_take = hq_free && f_req_v;
    wire         f_adv = f_act && blk_open && (!f_emit || f_take);
    wire         f_kk_last = (f_kk + 1'b1 == blen);
    wire         f_blk_last_it = (f_jh == f_jh_end) && (f_km ? (f_g == G - 1) : f_kk_last);
    wire         f_blk_last_k = (f_k0 + blen == d_k[f_idx]);
    wire         f_blk_last_r = (f_r + 1'b1 == d_tiles[f_idx]);
    reg          f_unsup;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            f_idx <= 1'b0; f_act <= 1'b0; blk_open <= 1'b0; fetch_line <= 0; f_unsup <= 1'b0;
            fdone <= 2'b00;
        end else begin
            f_unsup <= 1'b0;
            if (kvd_v) fdone[wptr] <= 1'b0;
            if (!f_act) begin
                if (dv[f_idx] && !fdone[f_idx] && !(kvd_v && wptr == f_idx)) begin
                    f_act <= 1'b1; blk_open <= 1'b0;
                    f_r <= 0; f_k0 <= 0; f_g <= 0; f_jh <= 0;
                    f_rb <= d_wbase[f_idx]; f_goff <= 0; f_jhoff <= 0; f_koff <= 0;
                    f_unsup <= !d_kmode[f_idx] && !d_gmode[f_idx];
                end
            end else if (!blk_open) begin
                if (f_space) begin
                    blk_open <= 1'b1; blen <= f_blen_c; line_base <= fetch_line;
                    fetch_line <= fetch_line + f_blines;
                    f_g <= 0; f_jh <= 0; f_goff <= 0; f_jhoff <= 0; f_kk <= 0; f_kkoff <= 0;
                end
            end else if (f_adv) begin
                if (!f_blk_last_it) begin
                    if (!f_km) begin
                        // G-mode: k-steps inner, jh outer
                        if (!f_kk_last) begin
                            f_kk <= f_kk + 1'b1; f_kkoff <= f_kkoff + d_ks[f_idx];
                        end else begin
                            f_kk <= 0; f_kkoff <= 0; f_jh <= f_jh + 1'b1; f_jhoff <= f_jhoff + d_js[f_idx];
                        end
                    end else if (f_jh != f_jh_end) begin
                        f_jh <= f_jh + 1'b1; f_jhoff <= f_jhoff + d_js[f_idx];
                    end else begin
                        f_jh <= 0; f_jhoff <= 0; f_g <= f_g + 1'b1; f_goff <= f_goff + d_ts[f_idx];
                    end
                end else begin
                    blk_open <= 1'b0;
                    if (!f_blk_last_k) begin
                        //: G-mode: f_kkoff holds (blen - 1) * ks on the block's last request
                        f_k0 <= f_k0 + blen; f_koff <= f_koff + f_kkoff + d_ks[f_idx];
                    end else begin
                        f_k0 <= 0; f_koff <= 0;
                        if (!f_blk_last_r) begin
                            f_r <= f_r + 1'b1; f_rb <= f_rb + (d_ts[f_idx] << LG);
                        end else begin
                            f_act <= 1'b0; fdone[f_idx] <= 1'b1; f_idx <= !f_idx;
                        end
                    end
                end
            end
        end
    end

    // ---- completion pointer --------------------------------------------------------------
    reg          p_idx, p_act;
    reg [NW-1:0] p_cnt;
    wire [NW-1:0] p_r, p_k;
    wire [LIL-1:0] p_jh;
    wire         p_last;
    wire         p_load = !p_act && dv[p_idx] && !cpdone[p_idx] && !(kvd_v && wptr == p_idx);
    reg  [G-1:0] p_need;
    integer gg;
    always @(*) begin
        for (gg = 0; gg < G; gg = gg + 1)
            p_need[gg] = (src_of(p_r, gg, d_ntile[p_idx], d_kindk[p_idx], d_to[p_idx]) == SRC_WIN);
    end
    wire [G-1:0] p_have = vbits[cp_line[LWIN-1:0]*G +: G];
    wire         p_step = p_act && (cp_line != fetch_line) && ((p_have & p_need) == p_need);
    ot_hdc_kv_walk #(.NW(NW), .LIL(LIL)) u_pw (.clk(clk), .rst_n(rst_n), .load(p_load), .step(p_step),
        .tiles(d_tiles[p_idx]), .kk(d_k[p_idx]), .jsh(d_jsh[p_idx]), .r(p_r), .k(p_k), .jh(p_jh), .last(p_last));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            p_idx <= 1'b0; p_act <= 1'b0; p_cnt <= 0; cp_line <= 0; cpdone <= 2'b00;
        end else begin
            if (kvd_v) cpdone[wptr] <= 1'b0;
            if (p_load) begin
                p_act <= 1'b1; p_cnt <= 0;
            end else if (p_step) begin
                cp_line <= cp_line + 1'b1;
                if (p_cnt != {NW{1'b1}}) p_cnt <= p_cnt + 1'b1;
                if (p_last) begin
                    p_act <= 1'b0; cpdone[p_idx] <= 1'b1; p_idx <= !p_idx;
                end
            end
        end
    end

    // ---- issue permission for the announced op --------------------------------------------
    //: T is capped where the window cannot hold T lines beside a fetch block;
    //: an op started on a capped T (not fully in the window) is not covered by
    //: the lead, which is reported (uncovered) rather than assumed away.
    wire nidx = !wptr;                         // the newest descriptor
    wire ok_done = cpdone[nidx];
    wire ok_lead = p_act && p_idx == nidx && p_cnt >= d_T[nidx];
    reg  uncovered;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin kv_ok <= 1'b0; uncovered <= 1'b0; end
        else begin
            kv_ok <= !kvd_v && dv[nidx] && (ok_done || ok_lead);
            uncovered <= !kvd_v && dv[nidx] && !ok_done && ok_lead && d_capped[nidx] && !kv_ok;
        end
    end

    // ---- consumer: follows the engine's reads, one line per 2^jsh cycles -------------------
    reg          c_idx, c_act;
    reg [2:0]    c_e;
    wire [NW-1:0] c_r, c_k;
    wire [LIL-1:0] c_jh;
    wire         c_last;
    wire         c_load = !c_act && dv[c_idx] && !(kvd_v && wptr == c_idx);
    wire [LWIN-1:0] c_slot = cons_line[LWIN-1:0];
    wire [2:0]   c_jsh = d_jsh[c_idx];
    wire         c_line_end = (c_e == (3'd1 << c_jsh) - 1'b1);
    wire         c_step = kv_re && c_act && c_line_end;
    ot_hdc_kv_walk #(.NW(NW), .LIL(LIL)) u_cw (.clk(clk), .rst_n(rst_n), .load(c_load), .step(c_step),
        .tiles(d_tiles[c_idx]), .kk(d_k[c_idx]), .jsh(c_jsh), .r(c_r), .k(c_k), .jh(c_jh), .last(c_last));
    reg  [2*G-1:0] c_src;
    always @(*) begin
        for (gg = 0; gg < G; gg = gg + 1)
            c_src[2*gg +: 2] = src_of(c_r, gg, d_ntile[c_idx], d_kindk[c_idx], d_to[c_idx]);
    end
    assign win_re = kv_re;
    assign win_raddr = c_slot;
    // tail read address: the word address the engine presents, sliced to {layer x head, d}
    function automatic [TAW-1:0] tail_idx(input [AW-1:0] a);
        tail_idx = {a[LOG_HD + LOG_TW +: LLG], a[LOG_HD-1:0]};
    endfunction
    reg [1:0]    c_tl_use;
    reg [2*TAW-1:0] c_tl_addr;
    always @(*) begin
        c_tl_use = 2'b00; c_tl_addr = 0;
        for (gg = 0; gg < G; gg = gg + 1) begin
            if (c_src[2*gg +: 2] == SRC_T0) begin c_tl_use[0] = kv_re; c_tl_addr[0 +: TAW] = tail_idx(kv_raddr[gg*AW +: AW]); end
            if (c_src[2*gg +: 2] == SRC_T1) begin c_tl_use[1] = kv_re; c_tl_addr[TAW +: TAW] = tail_idx(kv_raddr[gg*AW +: AW]); end
        end
    end
    reg  [2*G-1:0] sel_r;
    reg            underflow;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            c_idx <= 1'b0; c_act <= 1'b0; c_e <= 0; cons_line <= 0; underflow <= 1'b0; sel_r <= 0;
        end else begin
            underflow <= 1'b0;
            if (c_load) begin
                c_act <= 1'b1; c_e <= 0;
            end
            if (kv_re) begin
                sel_r <= c_src;
                //: a word the engine reads now must already be in the window
                for (gg = 0; gg < G; gg = gg + 1)
                    if (c_src[2*gg +: 2] == SRC_WIN && !vbits[c_slot*G + gg]) underflow <= 1'b1;
                //: ...and its line passed by the completion pointer
                if (!c_act || $signed(cp_line - cons_line) <= 0) underflow <= 1'b1;
                if (c_act) begin
                    if (c_line_end) begin
                        c_e <= 0; cons_line <= cons_line + 1'b1;
                        if (c_last) begin c_act <= 1'b0; c_idx <= !c_idx; end
                    end else c_e <= c_e + 1'b1;
                end
            end
        end
    end
    integer lq;
    always @(*) begin
        for (gg = 0; gg < G; gg = gg + 1)
            for (lq = 0; lq < W; lq = lq + 1)
                case (sel_r[2*gg +: 2])
                    SRC_WIN:  kv_q[(gg*W + lq)*32 +: 32] = {win_q[(gg*W + lq)*16 +: 16], 16'h0000};
                    SRC_T0:   kv_q[(gg*W + lq)*32 +: 32] = {tl_q[lq*16 +: 16], 16'h0000};
                    SRC_T1:   kv_q[(gg*W + lq)*32 +: 32] = {tl_q[(W + lq)*16 +: 16], 16'h0000};
                    default:  kv_q[(gg*W + lq)*32 +: 32] = 32'd0;
                endcase
    end

    // ---- descriptor slots -------------------------------------------------------------------
    reg overrun;
    integer si;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dv <= 2'b00; wptr <= 1'b0; overrun <= 1'b0;
        end else begin
            overrun <= 1'b0;
            if (c_step && c_last) dv[c_idx] <= 1'b0;
            if (kvd_v) begin
                if (dv[wptr] && !(c_step && c_last && c_idx == wptr)) overrun <= 1'b1;
                dv[wptr] <= 1'b1; wptr <= !wptr;
            end
        end
    end
    always @(posedge clk) begin
        if (kvd_v) begin
            d_wbase[wptr] <= kvd_wbase; d_ts[wptr] <= kvd_ts; d_ks[wptr] <= kvd_ks; d_js[wptr] <= kvd_js;
            d_jsh[wptr] <= kvd_jsh; d_tiles[wptr] <= kvd_tiles; d_k[wptr] <= kvd_k;
            d_ntile[wptr] <= (kvd_nout + W - 1) >> LW; d_to[wptr] <= kvd_pos >> LW;
            d_T[wptr] <= (t_lead > t_cap) ? t_cap : t_lead;
            d_capped[wptr] <= (t_lead > t_cap);
            d_kindk[wptr] <= kvd_kindk; d_kmode[wptr] <= (kvd_ks == 1); d_gmode[wptr] <= (kvd_ts == 1);
        end
    end

    // ---- read responses -> window (one write per bank per cycle, rotating priority) --------
    reg [$clog2(NPC+1)-1:0] rr;
    reg [G-1:0]     st_we;
    reg [G*LWIN-1:0] st_slot;
    reg [G*W*16-1:0] st_data;
    reg [G-1:0]     bank_used;
    // each port's (line slot, group): tag = {gmode, line0, g0, jsh}, beat b
    wire [NPC*LWIN-1:0] rsp_line;
    wire [NPC*LG-1:0]   rsp_grp;
    genvar gp;
    generate
        for (gp = 0; gp < NPC; gp = gp + 1) begin : g_rsp
            wire [TAGW-1:0] t = hr_tag[gp*TAGW +: TAGW];
            wire [LWIN-1:0] b = hr_beat[gp*LBK +: LBK];
            assign rsp_line[gp*LWIN +: LWIN] = t[TAGW-2 -: LWIN] + (t[TAGW-1] ? {LWIN{1'b0}} : (b << (LIL - t[2:0])));
            assign rsp_grp[gp*LG +: LG] = t[TAGW-1] ? b[LG-1:0] : t[3 +: LG];
        end
    endgenerate
    integer pi, pp;
    always @(*) begin
        hr_rdy = 0; bank_used = 0;
        for (pi = 0; pi < NPC; pi = pi + 1) begin
            pp = (rr + pi) % NPC;
            if (hr_v[pp] && !bank_used[rsp_grp[pp*LG +: LG]]) begin
                hr_rdy[pp] = 1'b1; bank_used[rsp_grp[pp*LG +: LG]] = 1'b1;
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rr <= 0; st_we <= 0; win_we <= 0; end
        else begin
            rr <= (rr == NPC - 1) ? 0 : rr + 1'b1;
            st_we <= 0;
            for (pi = 0; pi < NPC; pi = pi + 1)
                if (hr_v[pi] && hr_rdy[pi]) st_we[rsp_grp[pi*LG +: LG]] <= 1'b1;
            win_we <= st_we;
        end
    end
    always @(posedge clk) begin
        for (pi = 0; pi < NPC; pi = pi + 1)
            if (hr_v[pi] && hr_rdy[pi]) begin
                st_slot[rsp_grp[pi*LG +: LG]*LWIN +: LWIN] <= rsp_line[pi*LWIN +: LWIN];
                st_data[rsp_grp[pi*LG +: LG]*W*16 +: W*16] <= hr_data[pi*W*16 +: W*16];
            end
    end
    always @(posedge clk) begin
        win_waddr <= st_slot; win_wdata <= st_data;
    end
    // valid bits: set as a word is written, cleared as its line is consumed
    integer vb;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) vbits <= 0;
        else begin
            if (c_step) vbits[c_slot*G +: G] <= {G{1'b0}};
            //: written the same edge the window SRAM takes the data (win_we = st_we delayed)
            for (vb = 0; vb < G; vb = vb + 1)
                if (win_we[vb]) vbits[win_waddr[vb*LWIN +: LWIN]*G + vb] <= 1'b1;
        end
    end

    // ---- K writes: the tail SRAM, lane-wise -------------------------------------------------
    wire [AW-1:0] w_word = kv_waddr >> LW;
    wire [LW-1:0] w_lane = kv_waddr[LW-1:0];
    wire          w_isk = (w_word < V0_WORD);
    wire          w_bank = w_word[LOG_HD];     // tile parity
    reg           fl_act, fl_rd;
    reg [TAW-1:0] fl_idx;
    reg [NW-1:0]  fl_T;
    wire          fl_bank = fl_T[0];
    reg  [2:0]    ff_res, ff_n;                // flush FIFO: reserved (incl. read in flight), filled
    wire          fl_go = fl_act && !c_tl_use[fl_bank] && (ff_res < 3'd4);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) tl_we <= 2'b00;
        else begin
            tl_we <= 2'b00;
            if (kv_we && w_isk) tl_we[w_bank] <= 1'b1;
        end
    end
    integer tb;
    always @(posedge clk) begin
        for (tb = 0; tb < 2; tb = tb + 1) begin
            tl_waddr[tb*TAW +: TAW] <= tail_idx(w_word);
            //: lane 0 opens a new tile: the other lanes (later positions) read zero
            tl_wmask[tb*W +: W] <= (w_lane == 0) ? {W{1'b1}} : ({{(W-1){1'b0}}, 1'b1} << w_lane);
            tl_wdata[tb*W*16 +: W*16] <= {{(W-1)*16{1'b0}}, kv_wdata[31:16]} << (16 * w_lane);
        end
    end
    // Reads: the engine's (same cycle as its kv_re, like the window) or, on a
    // cycle the engine leaves that bank idle, the flush.
    always @(*) begin
        tl_re = c_tl_use; tl_raddr = c_tl_addr;
        if (fl_go) begin
            tl_re[fl_bank] = 1'b1; tl_raddr[fl_bank*TAW +: TAW] = fl_idx;
        end
    end

    // ---- flush of a closed tile: during the next W tokens, in idle tail cycles --------------
    reg  [AW-1:0]   ff_addr [0:3];
    reg  [W*16-1:0] ff_data [0:3];
    reg  [1:0]      ff_wp, ff_rp;
    reg  [AW-1:0]   fl_rd_addr;
    reg             fl_rd_bank;
    reg             fl_late;
    wire            ff_pop;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fl_act <= 1'b0; fl_idx <= 0; fl_T <= 0; fl_rd <= 1'b0; fl_late <= 1'b0;
            ff_res <= 0; ff_n <= 0; ff_wp <= 0; ff_rp <= 0;
        end else begin
            fl_late <= 1'b0;
            //: the token at pos = W*m (m > 0) closes tile m-1; its bank is flushed
            //: before tile m+1 reuses it, W tokens later
            if (tok_start && tok_pos[LW-1:0] == 0 && (tok_pos >> LW) != 0) begin
                if (fl_act) fl_late <= 1'b1;
                fl_act <= 1'b1; fl_idx <= 0; fl_T <= (tok_pos >> LW) - 1'b1;
            end else if (fl_go) begin
                fl_idx <= fl_idx + 1'b1;
                if (fl_idx == {TAW{1'b1}}) fl_act <= 1'b0;
            end
            fl_rd <= fl_go;
            ff_res <= ff_res + (fl_go ? 3'd1 : 3'd0) - (ff_pop ? 3'd1 : 3'd0);
            ff_n <= ff_n + (fl_rd ? 3'd1 : 3'd0) - (ff_pop ? 3'd1 : 3'd0);
            if (fl_rd) ff_wp <= ff_wp + 1'b1;
            if (ff_pop) ff_rp <= ff_rp + 1'b1;
        end
    end
    always @(posedge clk) begin
        if (fl_go) begin
            fl_rd_addr <= {fl_idx[TAW-1 -: LLG], fl_T[LOG_TW-1:0], fl_idx[LOG_HD-1:0]};
            fl_rd_bank <= fl_bank;
        end
        if (fl_rd) begin
            ff_addr[ff_wp] <= fl_rd_addr;
            ff_data[ff_wp] <= tl_q[fl_rd_bank*W*16 +: W*16];
        end
    end

    // ---- V writes: combined into words --------------------------------------------------------
    reg  [W*16-1:0] vc_data;
    reg  [2:0]      vf_cnt;
    reg  [AW-1:0]   vf_addr [0:3];
    reg  [W*16-1:0] vf_data [0:3];
    reg  [1:0]      vf_wp, vf_rp;
    reg             vf_over;
    wire            vf_pop;
    assign vf_empty = (vf_cnt == 0);
    wire   vf_push = kv_we && !w_isk && (w_lane == W - 1);
    always @(posedge clk) if (kv_we && !w_isk) vc_data[w_lane*16 +: 16] <= kv_wdata[31:16];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin vf_cnt <= 0; vf_wp <= 0; vf_rp <= 0; vf_over <= 1'b0; end
        else begin
            vf_over <= vf_push && vf_cnt == 4 && !vf_pop;
            vf_cnt <= vf_cnt + (vf_push ? 3'd1 : 3'd0) - (vf_pop ? 3'd1 : 3'd0);
            if (vf_push) vf_wp <= vf_wp + 1'b1;
            if (vf_pop) vf_rp <= vf_rp + 1'b1;
        end
    end
    always @(posedge clk) if (vf_push) begin
        vf_addr[vf_wp] <= w_word;
        vf_data[vf_wp] <= {kv_wdata[31:16], vc_data[(W-1)*16-1:0]};
    end

    // ---- HBM request port: V writes, then fetch reads, then flush writes ------------------------
    assign vf_pop = hq_free && !vf_empty;
    assign ff_pop = hq_free && vf_empty && !f_req_v && ff_n != 0;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) hq_v <= 1'b0;
        else if (hq_free) hq_v <= !vf_empty || f_req_v || ff_n != 0;
    end
    always @(posedge clk) if (hq_free) begin
        if (!vf_empty) begin
            hq_we <= 1'b1; hq_addr <= vf_addr[vf_rp]; hq_len <= 1; hq_wdata <= vf_data[vf_rp]; hq_tag <= 0;
        end else if (f_req_v) begin
            hq_we <= 1'b0; hq_addr <= f_req_addr; hq_len <= f_req_len; hq_tag <= f_req_tag;
        end else if (ff_n != 0) begin
            hq_we <= 1'b1; hq_addr <= ff_addr[ff_rp]; hq_len <= 1; hq_wdata <= ff_data[ff_rp]; hq_tag <= 0;
        end
    end
    // ---- status ----------------------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault <= 1'b0;
        else if (underflow || overrun || vf_over || fl_late || f_unsup || uncovered) fault <= 1'b1;
    end
endmodule
