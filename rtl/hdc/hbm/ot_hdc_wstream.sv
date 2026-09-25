`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Weight streaming engine of the hardwired decode core: the weights in HBM.
//
// The matrix engine (ot_hdc_matvec) reads its weights as if from a ROM: every
// cycle of a weight-sourced op it presents a word address on wrom_addr and
// takes the word one cycle later, with no valid and no stall.  This engine
// keeps that contract with the weights in HBM (ot_hdc_core W_HBM = 1).
//
// LAYOUT.  The program is static, so every weight word the engine will read,
// and the order it reads them in, is known when the program is generated.
// tools/hdc_program.py (hbm_weight_image) stores the token's weights in HBM as
// one STREAM in consumption order -- op by op, each op's words in the order its
// element loop reads them -- followed by the embedding table.  A word is WS
// consecutive 32-byte sectors (HBM3 bursts); the controller's address map
// interleaves pseudo-channels every 128 B and bank groups every sector, so the
// sequential stream is spread over every channel and bank group.
//
// FETCH.  Word n of the stream (n counts across tokens: the stream repeats every
// cfg_ntot words) lives in slot n mod WIN of the window SRAM, with a valid bit
// per (slot, sector).  The window is BF sets of WS banks (one per sector), each
// bank 2^LWIN / BF deep: slot s uses set s mod BF, and sector j of it sits in
// bank (j + s / BF) mod WS of the set.  Consecutive words come from different
// pseudo-channels at about the same time; the sets and the rotation spread
// their same-numbered sectors over different banks, so the responses of NPC
// channels rarely contend for a bank's single write port.  The fetcher needs no
// descriptor: it requests the stream in order, RQW words per request, whenever
// the window has room (fetched - consumed <= WIN), from the first token start
// on -- through stream-unit phases, KV ops and across the token boundary (the
// next token's first weights are prefetched while this token's argmax drains).
// The completion pointer walks the stream in order and passes a word once all
// its sectors have arrived.
//
// NO STALL.  When the sequencer reaches a weight op it announces the op's shape
// (wd_*: word base, rounds, k); the op's n = tiles * k * IL words are the next n
// of the stream.  It may start only when the window can feed it to the end:
// w_ok rises once the completion pointer is T words into the op, with
//     T = min(n, lead + n - floor(n * rate / 256))
// where cfg_lead covers the worst-case fetch latency (a refresh behind a row
// conflict) and cfg_rate is the guaranteed sustained arrival rate in words per
// cycle x 256.  With rate >= 1 word a cycle (supply at or above the engine's
// demand) T = min(n, lead); below it the op waits until the words it will
// consume faster than they arrive are already in the window, so a bandwidth-
// limited HBM slows the token without the engine ever stalling.  T must fit the
// window: tools/hdc_program.py --wchunk issues large ops as round chunks of at
// most WIN/2 words.  Every word the engine reads is checked (fail closed, sticky
// fault): it must have arrived, and its ROM address must be the announced op's
// next (the stream is what the program says it is).
//
// EMBEDDING.  The stream unit's read of the token's embedding row (wrom_su) is
// token-dependent: at each token start its EMBW words are fetched (ahead of the
// stream) into a small buffer, and emb_ok gates the stream-unit op.
//
// All memories are ports (window banks, HBM request/response); the testbench
// supplies behavioural ones, the physical top leaves them as macros / the HBM
// controller interface.
// ---------------------------------------------------------------------------
module ot_hdc_wstream #(
    parameter integer WB     = 1024,     // weight word bits (G * W * 16)
    parameter integer SB     = 256,      // sector (HBM burst) bits
    parameter integer AW     = 24,       // ROM word address bits
    parameter integer HAW    = 24,       // HBM sector address bits
    parameter integer NW     = 16,
    parameter integer IL     = 8,
    parameter integer LWIN   = 11,       // window: 2^LWIN words
    parameter integer NPC    = 4,        // HBM response ports (pseudo-channels)
    parameter integer RQW    = 4,        // words per stream request (RQW * WS sectors <= 2^(LENW-1))
    parameter integer LENW   = 5,
    parameter integer BEATW  = 4,
    parameter integer EMBW   = 2,        // embedding row, words
    parameter integer PCS    = 1,        // per-pseudo-channel sub-streams (needs WB = 1024: one 128 B unit)
    parameter integer BF     = 2         // window bank sets
) (
    input  wire              clk,
    input  wire              rst_n,
    // configuration (static per deployment)
    input  wire [HAW-1:0]    cfg_base,       // HBM sector of stream word 0
    input  wire [31:0]       cfg_ntot,       // words in one token's stream
    input  wire [HAW-1:0]    cfg_emb_base,   // HBM sector of the embedding table
    input  wire [AW-1:0]     cfg_emb_rom,    // ROM word address of the embedding table (as the core reads it)
    input  wire [NW-1:0]     cfg_lead,       // worst-case fetch lead, cycles
    input  wire [15:0]       cfg_rate,       // guaranteed arrival rate, words per cycle x 256
    // token start
    input  wire              tok_start,
    input  wire [NW-1:0]     token,
    // shape of the weight op the sequencer waits on, and its issue permission
    input  wire              wd_v,
    input  wire [AW-1:0]     wd_wbase,
    input  wire [NW-1:0]     wd_tiles, wd_k,
    output reg               w_ok,
    output reg               emb_ok,
    // the core's weight-ROM read port (fixed latency 1, no stall)
    input  wire              wrom_re,
    input  wire [AW-1:0]     wrom_addr,
    input  wire              wrom_su,
    output reg  [WB-1:0]     wrom_q,
    // window SRAM: BF * WS banks of 2^LWIN / BF sectors (addressed by slot / BF)
    output reg  [BF*WB/SB-1:0]  win_we,
    output reg  [BF*(WB/SB)*LWIN-1:0] win_waddr,   // slot of each bank's write
    output reg  [BF*WB-1:0]     win_wdata,
    output wire [BF*WB/SB-1:0]  win_re,
    output wire [LWIN-1:0]   win_raddr,             // slot of the read
    input  wire [BF*WB-1:0]  win_q,
    // HBM read requests (valid/ready)
    output reg               hq_v,
    input  wire              hq_rdy,
    output reg  [HAW-1:0]    hq_addr,
    output reg  [LENW-1:0]   hq_len,
    output reg  [LWIN:0]     hq_tag,         // {embedding, first word slot}
    input  wire [NPC-1:0]    hq_room,        // pseudo-channels with queue room (PCS)
    // HBM read responses, one port per pseudo-channel (valid/ready)
    input  wire [NPC-1:0]    hr_v,
    output reg  [NPC-1:0]    hr_rdy,
    input  wire [NPC*(LWIN+1)-1:0] hr_tag,
    input  wire [NPC*BEATW-1:0] hr_beat,
    input  wire [NPC*SB-1:0] hr_data,
    // status
    output reg               fault,
    output reg  [3:0]        fault_why,      // {uncoverable, overrun, address, underflow}
    output wire [31:0]       st_fetched,     // stream words requested (PCS: sub-stream words)
    output wire [31:0]       st_consumed     // stream words read by the engine
);
    localparam integer WS   = WB / SB;
    localparam integer WIN  = 1 << LWIN;
    localparam integer TAGW = LWIN + 1;
    localparam integer LWS  = (WS > 1) ? $clog2(WS) : 1;
    localparam integer NB   = BF * WS;
    localparam integer LBF  = (BF > 1) ? $clog2(BF) : 0;
    localparam integer LNB  = (NB > 1) ? $clog2(NB) : 1;
    localparam integer EMBS = EMBW * WS;         // embedding row, sectors
    localparam integer LEMB = (EMBW > 1) ? $clog2(EMBW) : 1;

    // ---- pointers (global word counts, wrap-safe) -------------------------------------------
    reg  [31:0] fp, cp, cons;          // fetched (requested), complete, consumed
    reg  [31:0] fpos;                  // fp's word within the token stream (HBM address)
    reg         run;                   // streaming since the first token start
    reg  [WIN*WS-1:0] vbits;

    // ---- embedding row -----------------------------------------------------------------------
    reg         emb_req;               // the row's request is pending
    reg  [HAW-1:0] emb_addr;
    reg  [AW-1:0]  emb_row;            // ROM word address of the row
    reg  [$clog2(EMBS+1)-1:0] emb_cnt; // sectors arrived
    reg  [WB-1:0] emb_buf [0:EMBW-1];

    // ---- request port: the embedding row first, then the stream ---------------------------------
    // PCS = 0: in order, RQW words per request.
    // PCS = 1: one sub-stream per pseudo-channel.  A word is one 128-byte
    // interleave unit, so it lives in one pseudo-channel; with the stream
    // aligned to NPC words (cfg_base, cfg_ntot), every aligned group of NPC
    // words covers each pseudo-channel once, and the controller's XOR map puts
    // word r of group gc on pseudo-channel r ^ ((gc ^ gc >> LPC) mod NPC).
    // Sub-stream p walks its words in stream order; each cycle the next word
    // of one sub-stream whose pseudo-channel has room (hq_room, from the
    // controller) and whose slot is free is requested, rotating over the sub-
    // streams -- so a pseudo-channel held by a refresh delays only its own
    // words, not the whole stream.
    localparam integer LPC = (NPC > 1) ? $clog2(NPC) : 0;
    wire        hq_free = !hq_v || hq_rdy;
    wire [31:0] occ = fp - cons;
    wire [31:0] left = cfg_ntot - fpos;
    wire [31:0] nreq = (left < RQW) ? left : RQW;
    wire        s_req0 = run && !emb_req && (occ + nreq <= WIN);
    reg  [31:0] sg [0:NPC-1];          // sub-stream: groups requested (global)
    reg  [31:0] sgp [0:NPC-1];         // ... and its group within the token stream
    wire [31:0] ngrp = cfg_ntot >> LPC;
    wire [HAW-1:0] base_gc = cfg_base >> (2 + LPC);
    reg  [NPC-1:0] s_elig;
    reg  [31:0]    c_n [0:NPC-1];      // each sub-stream's next word, computed from its counters ...
    reg  [HAW-1:0] c_addr [0:NPC-1];
    reg  [31:0]    s_n [0:NPC-1];      // ... and registered (nx_v): the pick reads registers only
    reg  [HAW-1:0] s_addr [0:NPC-1];
    reg  [NPC-1:0] nx_v;
    reg  [HAW-1:0] s_gc;
    reg  [LPC:0]   s_r;
    reg  [LWIN+1:0] s_d;
    integer sp;
    always @(*) begin
        for (sp = 0; sp < NPC; sp = sp + 1) begin
            s_gc = base_gc + sgp[sp][HAW-1:0];
            s_r = (sp ^ (s_gc ^ (s_gc >> LPC))) & (NPC - 1);
            c_n[sp] = (sg[sp] << LPC) + s_r;
            c_addr[sp] = ((s_gc << LPC) + s_r) << 2;
            //: the next word is at most WIN + NPC ahead of the consumer: LWIN + 2 bits hold the distance
            s_d = s_n[sp][LWIN+1:0] - cons[LWIN+1:0];
            s_elig[sp] = run && !emb_req && nx_v[sp] && hq_room[sp] && (s_d < WIN);
        end
    end
    reg  [LPC:0] s_rr;                 // rotating priority
    reg  [LPC:0] s_pick;
    reg          s_any;
    integer sq, sk;
    always @(*) begin
        s_any = 1'b0; s_pick = 0;
        for (sq = NPC - 1; sq >= 0; sq = sq - 1) begin
            sk = (s_rr + sq) % NPC;
            if (s_elig[sk]) begin s_any = 1'b1; s_pick = sk; end
        end
    end
    wire s_req = (PCS != 0) ? s_any : s_req0;
    integer si;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            hq_v <= 1'b0; fp <= 0; fpos <= 0; run <= 1'b0; emb_req <= 1'b0; s_rr <= 0;
            for (si = 0; si < NPC; si = si + 1) begin sg[si] <= 0; sgp[si] <= 0; end
            nx_v <= 0;
        end else begin
            //: a sub-stream's next word is registered the cycle after its counters move
            for (si = 0; si < NPC; si = si + 1)
                if (!nx_v[si]) begin s_n[si] <= c_n[si]; s_addr[si] <= c_addr[si]; nx_v[si] <= 1'b1; end
            if (tok_start) begin
                run <= 1'b1; emb_req <= 1'b1;
                emb_addr <= cfg_emb_base + token * EMBS;
                emb_row <= cfg_emb_rom + token * EMBW;
            end
            if (hq_free) begin
                hq_v <= 1'b0;
                if (emb_req && !tok_start) begin
                    hq_v <= 1'b1; hq_addr <= emb_addr; hq_len <= EMBS; hq_tag <= {1'b1, {LWIN{1'b0}}};
                    emb_req <= 1'b0;
                end else if (s_req && !tok_start && PCS != 0) begin
                    hq_v <= 1'b1; hq_addr <= s_addr[s_pick]; hq_len <= WS;
                    hq_tag <= {1'b0, s_n[s_pick][LWIN-1:0]};
                    fp <= fp + 1'b1;
                    sg[s_pick] <= sg[s_pick] + 1'b1;
                    nx_v[s_pick] <= 1'b0;
                    sgp[s_pick] <= (sgp[s_pick] + 1'b1 == ngrp) ? 0 : sgp[s_pick] + 1'b1;
                    s_rr <= (s_pick + 1'b1) % NPC;
                end else if (s_req && !tok_start) begin
                    hq_v <= 1'b1; hq_addr <= cfg_base + fpos * WS; hq_len <= nreq * WS;
                    hq_tag <= {1'b0, fp[LWIN-1:0]};
                    fp <= fp + nreq;
                    fpos <= (fpos + nreq == cfg_ntot) ? 0 : fpos + nreq;
                end
            end
        end
    end

    // ---- responses -> window banks (one write per bank per cycle, rotating priority) ------------
    reg  [$clog2(NPC+1)-1:0] rr;
    wire [NPC*LWIN-1:0] rsp_slot;
    wire [NPC*LWS-1:0]  rsp_sec;
    wire [NPC*LNB-1:0]  rsp_bank;
    wire [NPC-1:0]      rsp_emb;
    wire [NPC*LEMB-1:0] rsp_ew;
    genvar gp;
    generate
        for (gp = 0; gp < NPC; gp = gp + 1) begin : g_rsp
            wire [TAGW-1:0]  t = hr_tag[gp*TAGW +: TAGW];
            wire [BEATW-1:0] b = hr_beat[gp*BEATW +: BEATW];
            assign rsp_emb[gp] = t[LWIN];
            assign rsp_slot[gp*LWIN +: LWIN] = t[LWIN-1:0] + b / WS;
            assign rsp_sec[gp*LWS +: LWS] = b % WS;
            //: sector j of the word in slot s sits in bank (j + s) mod WS: consecutive
            //: words come from different pseudo-channels in lockstep, and the
            //: rotation keeps their same-numbered sectors off one bank
            assign rsp_bank[gp*LNB +: LNB] = (rsp_slot[gp*LWIN +: LWIN] % BF) * WS +
                                             ((b % WS) + ((rsp_slot[gp*LWIN +: LWIN] >> LBF) % WS)) % WS;
            assign rsp_ew[gp*LEMB +: LEMB] = b / WS;
        end
    endgenerate
    reg  [NB-1:0] bank_used;
    integer pi, pp;
    always @(*) begin
        hr_rdy = 0; bank_used = 0;
        for (pi = 0; pi < NPC; pi = pi + 1) begin
            pp = (rr + pi) % NPC;
            if (hr_v[pp] && (rsp_emb[pp] || !bank_used[rsp_bank[pp*LNB +: LNB]])) begin
                hr_rdy[pp] = 1'b1;
                if (!rsp_emb[pp]) bank_used[rsp_bank[pp*LNB +: LNB]] = 1'b1;
            end
        end
    end
    // stage 1: registered per bank; stage 2: the window write (and its valid bit)
    reg  [NB-1:0]      st_we;
    reg  [NB*LWIN-1:0] st_slot;
    reg  [NB*SB-1:0]   st_data;
    integer eb;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rr <= 0; st_we <= 0; win_we <= 0; end
        else begin
            rr <= (rr == NPC - 1) ? 0 : rr + 1'b1;
            st_we <= 0;
            for (pi = 0; pi < NPC; pi = pi + 1)
                if (hr_v[pi] && hr_rdy[pi] && !rsp_emb[pi]) st_we[rsp_bank[pi*LNB +: LNB]] <= 1'b1;
            win_we <= st_we;
        end
    end
    always @(posedge clk) begin
        for (pi = 0; pi < NPC; pi = pi + 1)
            if (hr_v[pi] && hr_rdy[pi]) begin
                if (!rsp_emb[pi]) begin
                    st_slot[rsp_bank[pi*LNB +: LNB]*LWIN +: LWIN] <= rsp_slot[pi*LWIN +: LWIN];
                    st_data[rsp_bank[pi*LNB +: LNB]*SB +: SB] <= hr_data[pi*SB +: SB];
                end else
                    emb_buf[rsp_ew[pi*LEMB +: LEMB]][rsp_sec[pi*LWS +: LWS]*SB +: SB] <= hr_data[pi*SB +: SB];
            end
        win_waddr <= st_slot; win_wdata <= st_data;
    end
    // embedding sectors arrived (several ports may deliver in one cycle)
    integer ne;
    reg [$clog2(NPC+1)-1:0] n_emb;
    always @(*) begin
        n_emb = 0;
        for (ne = 0; ne < NPC; ne = ne + 1) if (hr_v[ne] && hr_rdy[ne] && rsp_emb[ne]) n_emb = n_emb + 1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin emb_cnt <= 0; emb_ok <= 1'b0; end
        else begin
            if (tok_start) emb_cnt <= 0;
            else emb_cnt <= emb_cnt + n_emb;
            emb_ok <= !tok_start && !emb_req && (emb_cnt == EMBS);
        end
    end

    // ---- completion pointer and consumer ---------------------------------------------------------
    wire [LWIN-1:0] cp_slot = cp[LWIN-1:0];
    wire [LWIN-1:0] c_slot = cons[LWIN-1:0];
    //: a slot's valid bits belong to word cp once the slot's previous word
    //: (cp - WIN) is consumed: its bits clear then, and only word cp's
    //: responses set them again
    wire [31:0] cp_ahead = cp - cons;
    wire        cp_step = (cp_ahead < WIN) && (&vbits[cp_slot*WS +: WS]);
    wire        c_rd = wrom_re && !wrom_su;
    integer vb;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin vbits <= 0; cp <= 0; cons <= 0; end
        else begin
            if (cp_step) cp <= cp + 1'b1;
            if (c_rd) begin
                cons <= cons + 1'b1;
                vbits[c_slot*WS +: WS] <= {WS{1'b0}};
            end
            //: set the same edge the window SRAM takes the data
            for (vb = 0; vb < NB; vb = vb + 1)
                if (win_we[vb]) vbits[win_waddr[vb*LWIN +: LWIN]*WS + (vb % WS)] <= 1'b1;
        end
    end
    genvar gr;
    generate
        for (gr = 0; gr < NB; gr = gr + 1) begin : g_rd
            assign win_re[gr] = c_rd && ((gr / WS) == (c_slot % BF));
        end
    endgenerate
    assign win_raddr = c_slot;
    reg        q_su;
    reg [LEMB-1:0] q_ew;
    reg [LWS-1:0]  q_rot;
    reg [LBF:0]    q_set;
    always @(posedge clk) begin
        q_su <= wrom_su;
        q_ew <= wrom_addr - emb_row;
        q_rot <= (c_slot >> LBF) % WS;
        q_set <= c_slot % BF;
    end
    //: undo the bank rotation: sector j of the word is bank (j + rot) mod WS
    reg [WB-1:0] w_rot;
    integer rj;
    always @(*) begin
        for (rj = 0; rj < WS; rj = rj + 1) w_rot[rj*SB +: SB] = win_q[(q_set*WS + (rj + q_rot) % WS)*SB +: SB];
        wrom_q = q_su ? emb_buf[q_ew] : w_rot;
    end

    // ---- announced ops: shape -> threshold, issue permission, consumption check ------------------
    //: two slots: the op being consumed and the op being announced
    reg  [1:0]    dv;
    reg           wptr, cidx;
    reg  [AW-1:0] d_wbase [0:1];
    reg  [31:0]   d_n [0:1];
    reg  [31:0]   ann_end;             // stream words of every announced op
    reg  [31:0]   op_start;            // stream position of the newest op
    // threshold pipeline: n = tiles * k * IL, then n * rate, then T
    reg  [2:0]    tp;                  // stages in flight
    reg  [NW-1:0] a_tiles, a_k;
    reg  [31:0]   a_n, a_nr, a_T;
    reg           t_rdy, uncoverable;
    wire [31:0]   a_fast = a_nr >> 8;
    wire [31:0]   a_short = (a_fast >= a_n) ? 32'd0 : a_n - a_fast;
    wire [31:0]   a_Tl = cfg_lead + a_short;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tp <= 0; t_rdy <= 1'b0; w_ok <= 1'b0; uncoverable <= 1'b0; ann_end <= 0; op_start <= 0;
        end else begin
            uncoverable <= 1'b0;
            tp <= {tp[1:0], wd_v};
            if (wd_v) begin a_tiles <= wd_tiles; a_k <= wd_k; t_rdy <= 1'b0; end
            if (tp[0]) begin
                a_n <= a_tiles * a_k * IL;
            end
            if (tp[1]) begin
                a_nr <= a_n * cfg_rate;
                op_start <= ann_end; ann_end <= ann_end + a_n;
            end
            if (tp[2]) begin
                a_T <= (a_Tl < a_n) ? a_Tl : a_n;
                uncoverable <= ((a_Tl < a_n) ? a_Tl : a_n) > WIN;
                t_rdy <= 1'b1;
            end
            w_ok <= t_rdy && !wd_v && (tp == 0) && (cp - op_start >= a_T);
        end
    end
    // slots
    reg  [31:0] c_i;
    reg         overrun, addr_bad, underflow;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dv <= 2'b00; wptr <= 1'b0; cidx <= 1'b0; c_i <= 0; overrun <= 1'b0; addr_bad <= 1'b0; underflow <= 1'b0;
        end else begin
            overrun <= 1'b0; addr_bad <= 1'b0; underflow <= 1'b0;
            if (tp[1]) begin
                if (dv[wptr]) overrun <= 1'b1;
                dv[wptr] <= 1'b1; d_n[wptr] <= a_n; wptr <= !wptr;
            end
            if (c_rd) begin
                //: the word the engine reads now must have arrived ...
                if ($signed(cp - cons) <= 0) underflow <= 1'b1;
                //: ... and be the announced op's next word
                if (!dv[cidx] || wrom_addr != d_wbase[cidx] + c_i[AW-1:0]) addr_bad <= 1'b1;
                if (c_i + 1 == d_n[cidx]) begin
                    c_i <= 0; dv[cidx] <= 1'b0; cidx <= !cidx;
                end else c_i <= c_i + 1'b1;
            end
        end
    end
    always @(posedge clk) if (wd_v) d_wbase[wptr] <= wd_wbase;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fault <= 1'b0; fault_why <= 0; end
        else if (underflow || addr_bad || overrun || uncoverable) begin
            fault <= 1'b1;
            fault_why <= fault_why | {uncoverable, overrun, addr_bad, underflow};
        end
    end
    assign st_fetched = fp;
    assign st_consumed = cons;
endmodule
