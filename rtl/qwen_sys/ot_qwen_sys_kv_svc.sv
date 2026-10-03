`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_qwen_sys_kv_svc: the per-die KV service of the Qwen3 ROM system top
// (rtl/qwen_sys/ot_qwen_rom_sys_top.sv).  NEW, used only by the system top.
//
// The KV cache lives in the die's attached HBM.  The decode core
// (ot_hdc_core, KV_HBM = 1) reads KV through a fixed-latency, no-stall word
// port and writes it one FP32 element at a time; this service keeps that
// contract with the authoritative copy in HBM:
//
//   STAGING SRAM.  KVWORDS words of W x FP32 with a valid bit and a per-lane
//     dirty mask per word.  Every valid bit is CLEARED at the token start
//     (tok_start), so every KV word a token reads comes from HBM in that token:
//     the SRAM is a staging buffer, never a second home of the cache.
//   FILL.  The core announces a KV-sourced op (kvd_v) before it may issue it.
//     The service fills the op's block (2^LWB words: one layer's K or V rows
//     of this die's KV head) word by word with tagged 2-sector HBM reads,
//     merging HBM data only into lanes the core has not written this token,
//     and raises kv_ok when every word of the block is valid.  A core read of
//     a word that is not valid is a fault (the no-stall contract is checked,
//     not assumed).
//   WRITE-BACK.  Every word the core writes is queued once; at the queue head
//     a valid word is snapshotted (dirty lanes cleared, a later write re-queues
//     it) and written to HBM as two one-sector writes; a word that is not yet
//     valid is filled first (HBM3 has no write data mask).
//   EXACT COMPLETION (rom_bridge_gaps DA2 / A3).  Every HBM request takes an
//     entry of an outstanding table (OT); its tag is {generation, entry}.  A
//     response must name a live entry of the same generation, the same
//     direction (rsp_wr), a beat in range and not yet seen -- anything else is
//     a fault, never a silent misroute.  A write is complete only on its
//     tagged write-done (the HBM model's WR_ACK), never on acceptance.
//     `drained` = no queued word, no write-back in progress, no outstanding
//     request: the package controller reports a token to the host only when
//     every die is drained, so a completion implies the KV is durable in HBM.
//   BOOT CHECK.  boot_go writes a pattern to the last sector of the HBM range,
//     reads it back and compares; boot_done / boot_ok go to the reset
//     sequencer (the HBM-ready condition is produced by a real round trip).
//
// HBM port: ot_qwen_hbm_model_ack request/response convention (sector =
// SECW bits, reads of req_len sectors returned as tagged beats on NPC
// pseudo-channel ports, one-sector writes acknowledged with rsp_wr = 1).
// Word w of the die's cache is sectors 2 (kv_base + w) and 2 (kv_base + w) + 1.
// ---------------------------------------------------------------------------
module ot_qwen_sys_kv_svc #(
    parameter integer W       = 16,
    parameter integer G       = 4,
    parameter integer AW      = 24,
    parameter integer KVWORDS = 512,        // staging words (power of two)
    parameter integer LWB     = 6,          // log2 words per fill block (one layer's K or V)
    parameter integer HAW     = 24,         // HBM sector address bits
    parameter integer SECW    = 256,        // sector bits (W*32 = 2 sectors)
    parameter integer NPC     = 4,
    parameter integer LOT     = 6,          // log2 outstanding-table entries
    parameter integer LENW    = 5,
    parameter integer BEATW   = 4,
    parameter integer TAGW    = LOT + 1,    // {generation, entry}
    parameter [23:0]  BOOT_SECTOR = 24'hFFFFFF,  // the power-up check's sector (outside every user's KV)
    parameter integer SCRUB_SECTORS = 0,         // boot: zero sectors [0, SCRUB_SECTORS) first (the KV region)
    // RCLK_SEP = 1: the core read port (kv_re / kv_raddr / kv_q) is clocked by rclk -- the matrix engine's 1.2 GHz
    // clock (ME_CDC) -- a 1R1W staging SRAM with a fast read clock; everything else stays on clk.
    parameter integer RCLK_SEP = 0,
    // PREFETCH = 1: the token start is the sequencer's KV prefetch NOTICE: the service walks every block in the
    // program's layer order (K0, V0, K1, V1, ...) from the token start, ahead of each op's own announcement
    // (kvd_v, which still pre-empts the walk).  Words the core writes before their fill keep their lanes (the
    // dirty merge), so the order of notice, write and fill never changes a value.  0 (default): fill on kvd_v only.
    parameter integer PREFETCH = 0
) (
    input  wire                 clk,
    input  wire                 rclk,
    input  wire                 rst_n,
    // token boundary and the user's HBM word offset
    input  wire                 tok_start,
    input  wire [HAW-2:0]       kv_base,
    // core KV-streaming handshake
    input  wire                 kvd_v,
    input  wire [AW-1:0]        kvd_wbase,
    output reg                  kv_ok,
    // core KV read port: latency 1, no stall
    input  wire                 kv_re,
    input  wire [G*AW-1:0]      kv_raddr,
    output reg  [G*W*32-1:0]    kv_q,
    // core KV element writes
    input  wire                 kv_we,
    input  wire [AW-1:0]        kv_waddr,
    input  wire [31:0]          kv_wdata,
    output wire                 drained,
    // HBM requester
    output reg                  h_req_v,
    input  wire                 h_req_rdy,
    output reg                  h_req_we,
    output reg  [HAW-1:0]       h_req_addr,
    output reg  [LENW-1:0]      h_req_len,
    output reg  [TAGW-1:0]      h_req_tag,
    output reg  [SECW-1:0]      h_req_wdata,
    input  wire [NPC-1:0]       h_rsp_v,
    output wire [NPC-1:0]       h_rsp_rdy,
    input  wire [NPC*TAGW-1:0]  h_rsp_tag,
    input  wire [NPC*BEATW-1:0] h_rsp_beat,
    input  wire [NPC*SECW-1:0]  h_rsp_data,
    input  wire [NPC-1:0]       h_rsp_wr,
    // power-up check
    input  wire                 boot_go,
    output reg                  boot_done,
    output reg                  boot_ok,
    // faults and counters
    output wire                 fault,
    output wire [5:0]           fault_code,  // [0] tag/identity [1] duplicate beat [2] read of invalid word
                                             // [3] token start while not drained [4] boot mismatch [5] block range
    output reg  [31:0]          n_fill_words,
    output reg  [31:0]          n_wb_sectors,
    output reg  [31:0]          n_kvok_wait
);
    localparam integer NOT = 1 << LOT;
    reg       f_r;
    reg [5:0] fc_r;
    reg       rd_inv;             // a core read of a word that is not valid (read-clock domain)
    assign fault = f_r | rd_inv;
    assign fault_code = fc_r | {3'b000, rd_inv, 2'b00};
    localparam integer KB  = $clog2(KVWORDS);
    localparam integer NBLK = KVWORDS >> LWB;
    localparam integer HL  = W / 2;                 // lanes per sector
    assign h_rsp_rdy = {NPC{1'b1}};

    // -- staging SRAM and per-word state ----------------------------------------------------
    reg [W*32-1:0]   mem   [0:KVWORDS-1];
    reg [KVWORDS*W-1:0] dirty;          // per word, per lane
    reg [KVWORDS-1:0] valid, inflight, queued;

    // -- outstanding table -----------------------------------------------------------------
    reg [NOT-1:0]    ot_v;
    reg [NOT-1:0]    ot_gen;
    reg [NOT-1:0]    ot_we;
    reg [KB-1:0]     ot_word [0:NOT-1];
    reg [2*NOT-1:0]  ot_seen;            // beats received, per entry
    reg [LOT:0]      ot_n;
    reg [LOT-1:0]    free_idx;
    reg              free_any;
    integer i;
    always @(*) begin
        free_any = 1'b0; free_idx = 0;
        for (i = NOT - 1; i >= 0; i = i - 1) if (!ot_v[i]) begin free_any = 1'b1; free_idx = i[LOT-1:0]; end
    end

    // -- write-back queue (each word at most once) ------------------------------------------
    reg [KB-1:0] wq [0:KVWORDS-1];
    reg [KB-1:0] wq_r, wq_w;
    reg [KB:0]   wq_n;
    wire [KB-1:0] w_word = kv_waddr[KB+3:4];
    wire [3:0]    w_lane = kv_waddr[3:0];
    wire          w_push = kv_we && !queued[w_word];

    // -- write-back engine -----------------------------------------------------------------
    localparam [2:0] WB_IDLE = 0, WB_SNAP = 1, WB_LO = 2, WB_HI = 3, WB_FILL = 4;
    reg [2:0]       wb_st;
    reg [KB-1:0]    wb_word;
    reg [W*32-1:0]  wb_data;
    wire [KB-1:0]   wq_head = wq[wq_r];

    // -- block fill engine -----------------------------------------------------------------
    reg             bf_act;
    reg [KB-1:0]    bf_base;
    reg [LWB:0]     bf_k;
    reg [KB-LWB-1:0] cur_blk;
    reg             cur_v;
    wire [KB-1:0]   bf_word = bf_base + bf_k[LWB-1:0];
    reg             bf_pf, pf_on;
    reg [KB-LWB:0]  pf_i;
    // program order of the blocks: K of layer l is block l, V of layer l is block NBLK/2 + l
    wire [KB-LWB-1:0] pf_blk = pf_i[0] ? (NBLK / 2 + (pf_i >> 1)) : (pf_i >> 1);
    wire [KB-LWB-1:0] kvd_blk = kvd_wbase[KB-1:LWB];

    // -- boot check ------------------------------------------------------------------------
    localparam [2:0] BT_IDLE = 0, BT_WR = 1, BT_WWAIT = 2, BT_RD = 3, BT_RWAIT = 4, BT_DONE = 5,
                     BT_SCRUB = 6, BT_SWAIT = 7;
    reg [23:0]      sc_k;
    reg [2:0]       bt_st;
    reg [LOT-1:0]   boot_idx;
    localparam [SECW-1:0] PATTERN = {(SECW/32){32'hA5C3_0F96}} ^ {{(SECW-32){1'b0}}, 32'h0123_4567};

    // -- request arbitration: boot > write-back write > write-back fill > block fill ---------
    reg             rq_boot_wr, rq_boot_rd, rq_wb_w, rq_wb_f, rq_bf;
    wire            bf_need = bf_act && !bf_k[LWB] && !valid[bf_word] && !inflight[bf_word];
    wire            bf_skip = bf_act && !bf_k[LWB] && (valid[bf_word] || inflight[bf_word]);
    wire            can_issue = free_any && (!h_req_v || h_req_rdy);
    always @(*) begin
        rq_boot_wr = (bt_st == BT_WR) || (bt_st == BT_SCRUB);
        rq_boot_rd = (bt_st == BT_RD);
        rq_wb_w    = (wb_st == WB_LO) || (wb_st == WB_HI);
        rq_wb_f    = (wb_st == WB_FILL) && !valid[wb_word] && !inflight[wb_word];
        rq_bf      = bf_need;
    end
    wire            any_rq = rq_boot_wr || rq_boot_rd || rq_wb_w || rq_wb_f || rq_bf;
    wire            issue  = can_issue && any_rq;
    wire            g_boot = issue && (rq_boot_wr || rq_boot_rd);
    wire            g_wbw  = issue && !g_boot && rq_wb_w;
    wire            g_wbf  = issue && !g_boot && !rq_wb_w && rq_wb_f;
    wire            g_bf   = issue && !g_boot && !rq_wb_w && !rq_wb_f && rq_bf;
    wire [KB-1:0]   fill_word = g_wbf ? wb_word : bf_word;

    wire [HAW-1:0]  sec_base = {kv_base, 1'b0};

    assign drained = (wq_n == 0) && (wb_st == WB_IDLE) && (ot_n == 0);

    // -- response fields per port -------------------------------------------------------------
    reg [LOT-1:0]   r_idx  [0:NPC-1];
    reg             r_gen  [0:NPC-1];
    reg [BEATW-1:0] r_beat [0:NPC-1];
    integer p;
    always @(*) begin
        for (p = 0; p < NPC; p = p + 1) begin
            r_idx[p]  = h_rsp_tag[p*TAGW +: LOT];
            r_gen[p]  = h_rsp_tag[p*TAGW + LOT];
            r_beat[p] = h_rsp_beat[p*BEATW +: BEATW];
        end
    end

    // -- main sequential block --------------------------------------------------------------
    integer l, q, k;
    reg [KB-1:0]  rw;
    reg           rh;
    reg [LOT:0]   ot_n_nxt;
    reg [NOT-1:0] ot_v_nxt;
    reg [2*NOT-1:0] seen_nxt;
    reg [LOT-1:0] e;
    reg           live;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid <= 0; inflight <= 0; queued <= 0;
            ot_v <= 0; ot_gen <= 0; ot_we <= 0; ot_n <= 0;
            wq_r <= 0; wq_w <= 0; wq_n <= 0;
            bf_pf <= 1'b0; pf_on <= 1'b0; pf_i <= 0;
            wb_st <= WB_IDLE; bf_act <= 1'b0; bf_k <= 0; bf_base <= 0; cur_blk <= 0; cur_v <= 1'b0;
            kv_ok <= 1'b0; h_req_v <= 1'b0; h_req_we <= 1'b0; h_req_addr <= 0; h_req_len <= 0;
            h_req_tag <= 0; h_req_wdata <= 0;
            bt_st <= BT_IDLE; boot_done <= 1'b0; boot_ok <= 1'b0; sc_k <= 0;
            f_r <= 1'b0; fc_r <= 0;
            n_fill_words <= 0; n_wb_sectors <= 0; n_kvok_wait <= 0;
            dirty <= 0;
            ot_seen <= 0;
        end else begin
            ot_v_nxt = ot_v;
            ot_n_nxt = ot_n;
            if (h_req_v && h_req_rdy) h_req_v <= 1'b0;

            // ---- core writes: SRAM lane, dirty, queue
            if (kv_we) begin
                mem[w_word][32*w_lane +: 32] <= kv_wdata;
                dirty[w_word*W + w_lane] <= 1'b1;
                if (!queued[w_word]) queued[w_word] <= 1'b1;
            end


            // ---- responses: identity is checked beat by beat against the outstanding table
            seen_nxt = ot_seen;
            for (p = 0; p < NPC; p = p + 1) if (h_rsp_v[p]) begin
                e = r_idx[p];
                live = ot_v_nxt[e] && (ot_gen[e] == r_gen[p]);
                if (!live || (ot_we[e] != h_rsp_wr[p]) ||
                    (h_rsp_wr[p] ? (r_beat[p] != 0) : (r_beat[p] > 1))) begin
                    f_r <= 1'b1; fc_r[0] <= 1'b1;
                end else if (seen_nxt[2*e + r_beat[p][0]]) begin
                    f_r <= 1'b1; fc_r[1] <= 1'b1;
                end else if (h_rsp_wr[p]) begin
                    // tagged write-done: the sector is in the array
                    ot_v_nxt[e] = 1'b0; ot_n_nxt = ot_n_nxt - 1'b1;
                    seen_nxt[2*e +: 2] = 2'b00;
                    if (bt_st == BT_WWAIT && e == boot_idx) bt_st <= BT_RD;
                    if (bt_st == BT_SWAIT && ot_n_nxt == 0) bt_st <= BT_WR;
                end else if (bt_st == BT_RWAIT && e == boot_idx) begin
                    ot_v_nxt[e] = 1'b0; ot_n_nxt = ot_n_nxt - 1'b1;
                    seen_nxt[2*e +: 2] = 2'b00;
                    boot_done <= 1'b1;
                    boot_ok <= (h_rsp_data[p*SECW +: SECW] == PATTERN);
                    if (h_rsp_data[p*SECW +: SECW] != PATTERN) begin f_r <= 1'b1; fc_r[4] <= 1'b1; end
                    bt_st <= BT_DONE;
                end else begin
                    rw = ot_word[e];
                    rh = r_beat[p][0];
                    for (l = 0; l < HL; l = l + 1)
                        if (!dirty[rw*W + rh*HL + l] && !(kv_we && w_word == rw && w_lane == rh*HL + l))
                            mem[rw][32*(rh*HL + l) +: 32] <= h_rsp_data[p*SECW + 32*l +: 32];
                    seen_nxt[2*e + rh] = 1'b1;
                    if (seen_nxt[2*e +: 2] == 2'b11) begin
                        // both beats in: the word is valid, the entry retires
                        valid[rw] <= 1'b1; inflight[rw] <= 1'b0;
                        ot_v_nxt[e] = 1'b0; ot_n_nxt = ot_n_nxt - 1'b1;
                        seen_nxt[2*e +: 2] = 2'b00;
                        n_fill_words <= n_fill_words + 1;
                    end
                end
            end

            // ---- request issue (one per cycle)
            if (issue) begin
                ot_v_nxt[free_idx] = 1'b1; ot_n_nxt = ot_n_nxt + 1'b1;
                ot_gen[free_idx] <= ~ot_gen[free_idx];
                seen_nxt[2*free_idx +: 2] = 2'b00;
                h_req_v <= 1'b1;
                h_req_tag <= {~ot_gen[free_idx], free_idx};
                if (g_boot && bt_st == BT_SCRUB) begin
                    // power-up scrub: the user KV region starts as zeros, written and acknowledged
                    ot_we[free_idx] <= 1'b1; ot_word[free_idx] <= {KB{1'b1}};
                    h_req_we <= 1'b1; h_req_addr <= sc_k; h_req_len <= 1; h_req_wdata <= {SECW{1'b0}};
                    sc_k <= sc_k + 1'b1;
                    if (sc_k + 1 >= SCRUB_SECTORS) bt_st <= BT_SWAIT;
                end else if (g_boot) begin
                    ot_we[free_idx] <= rq_boot_wr; ot_word[free_idx] <= {KB{1'b1}};
                    h_req_we <= rq_boot_wr; h_req_addr <= BOOT_SECTOR; h_req_len <= 1;
                    h_req_wdata <= PATTERN;
                    bt_st <= rq_boot_wr ? BT_WWAIT : BT_RWAIT;
                end else if (g_wbw) begin
                    ot_we[free_idx] <= 1'b1; ot_word[free_idx] <= wb_word;
                    h_req_we <= 1'b1; h_req_len <= 1;
                    h_req_addr <= sec_base + {wb_word, (wb_st == WB_HI)};
                    h_req_wdata <= (wb_st == WB_HI) ? wb_data[W*32-1 -: SECW] : wb_data[SECW-1:0];
                    n_wb_sectors <= n_wb_sectors + 1;
                end else begin
                    ot_we[free_idx] <= 1'b0; ot_word[free_idx] <= fill_word;
                    h_req_we <= 1'b0; h_req_len <= 2;
                    h_req_addr <= sec_base + {fill_word, 1'b0};
                    inflight[fill_word] <= 1'b1;
                end
            end

            // ---- block fill walk
            if (kvd_v) begin
                bf_act <= 1'b1; bf_k <= 0; bf_base <= {kvd_blk, {LWB{1'b0}}}; bf_pf <= 1'b0;
                cur_blk <= kvd_blk; cur_v <= 1'b1; kv_ok <= 1'b0;
                if (kvd_wbase[AW-1:KB] != 0) begin f_r <= 1'b1; fc_r[5] <= 1'b1; end
            end else begin
                if (bf_act && (g_bf || bf_skip)) begin
                    bf_k <= bf_k + 1'b1;
                    if (bf_k == (1 << LWB) - 1) begin
                        bf_act <= 1'b0;
                        if (bf_pf) pf_i <= pf_i + 1'b1;
                    end
                end else if (PREFETCH != 0 && !bf_act && pf_on && pf_i < NBLK) begin
                    bf_act <= 1'b1; bf_k <= 0; bf_base <= {pf_blk, {LWB{1'b0}}}; bf_pf <= 1'b1;
                end
                kv_ok <= cur_v && (&valid[{cur_blk, {LWB{1'b0}}} +: (1 << LWB)]);
                if (cur_v && !(&valid[{cur_blk, {LWB{1'b0}}} +: (1 << LWB)])) n_kvok_wait <= n_kvok_wait + 1;
            end

            // ---- write-back engine
            case (wb_st)
                WB_IDLE: if (wq_n != 0) begin wb_word <= wq_head; wb_st <= WB_FILL; end
                WB_FILL: if (valid[wb_word] && !inflight[wb_word]) wb_st <= WB_SNAP;
                WB_SNAP: begin
                    wb_data <= mem[wb_word];
                    // dirty lanes are captured; a write this cycle keeps its lane dirty and re-queues
                    dirty[wb_word*W +: W] <= (kv_we && w_word == wb_word) ? ({{(W-1){1'b0}}, 1'b1} << w_lane) : {W{1'b0}};
                    wb_st <= WB_LO;
                end
                WB_LO: if (g_wbw) wb_st <= WB_HI;
                WB_HI: if (g_wbw) wb_st <= WB_IDLE;
                default: wb_st <= WB_IDLE;
            endcase

            // ---- queue push / pop
            begin : queue
                reg pop;
                pop = (wb_st == WB_IDLE) && (wq_n != 0);
                if (pop) begin
                    wq_r <= wq_r + 1'b1;
                    // the word may be queued again by a later write
                    if (!(kv_we && w_word == wq_head)) queued[wq_head] <= 1'b0;
                end
                if (w_push || (pop && kv_we && w_word == wq_head)) begin
                    wq[wq_w] <= w_word; wq_w <= wq_w + 1'b1;
                end
                wq_n <= wq_n + ((w_push || (pop && kv_we && w_word == wq_head)) ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
            end

            // ---- token start: the staging buffer is invalidated (every read comes from HBM)
            if (tok_start) begin
                // (a block walk still skipping valid words is cancelled; outstanding requests are not allowed)
                if (!drained) begin f_r <= 1'b1; fc_r[3] <= 1'b1; end
                valid <= 0; cur_v <= 1'b0; kv_ok <= 1'b0; bf_act <= 1'b0;
                pf_on <= (PREFETCH != 0); pf_i <= 0; bf_pf <= 1'b0;
            end

            // ---- boot
            if (boot_go && bt_st == BT_IDLE) begin
                bt_st <= (SCRUB_SECTORS > 0) ? BT_SCRUB : BT_WR; sc_k <= 0;
            end

            ot_v <= ot_v_nxt;
            ot_n <= ot_n_nxt;
            ot_seen <= seen_nxt;
        end
    end

    // ---- core reads (latency 1) and the read-of-invalid check, on the read clock
    wire rck = (RCLK_SEP != 0) ? rclk : clk;
    integer qq;
    always @(posedge rck or negedge rst_n) begin
        if (!rst_n) rd_inv <= 1'b0;
        else if (kv_re)
            for (qq = 0; qq < G; qq = qq + 1) begin
                kv_q[qq*W*32 +: W*32] <= mem[kv_raddr[qq*AW +: KB]];
                if (!valid[kv_raddr[qq*AW +: KB]]) rd_inv <= 1'b1;
            end
    end

    // the boot request's entry
    always @(posedge clk) if (issue && g_boot) boot_idx <= free_idx;
endmodule
