`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Index-key reader for the ROW LAYOUT (ot_hdc_v41x_idx_rowmap.svh), one HBM3E stack (32 pseudo-channels):
//   * LIST mode (cmd_range = 0): the CANDIDATE-BLOCK GATHER of the re-index layers (L24, L28, L32, L36), the
//     row-layout successor of ot_hdc_v41x_idx_kgather (same list interface, same output beats);
//   * RANGE mode (cmd_range = 1): a full scan of a row-layout quarter, blocks 0 .. cmd_n - 1 (measured, see
//     results/rtl/dsrom_idxkey_layout_20261004: below 90% of peak under the controller's per-bank refresh,
//     so the scanned layers L2 / L8 / L14 / L20 keep the super-block layout and ot_hdc_v41x_idx_kstream_range).
// Opt-in: nothing instantiates it by default; the 4-KB super-block layout and its readers stay the default.
// The layout is a property of a layer's index-key region: the re-index layers' regions (gathered only) are
// written by ot_hdc_v41x_idx_ring_kwr_row and read here.
//
// LAYOUT.  An 8-key block = 17 sectors in columns 0..16 of ONE DRAM row (one pseudo-channel, one bank): a
// block read is 1 ACT + 17 column reads, against ~14 ACTs (0.8 per sector) in the super-block layout, where
// a block's 17 sectors land in 17 different banks.  Consecutive blocks rotate pseudo-channel, bank group,
// bank, so independent blocks (and a scan's consecutive blocks) overlap on all channels and bank groups.
// Ring: the stack's ring holds cmd_cblk blocks (ring slot t = position mod C, block t / 8; C a multiple of
// 8); the quarter starts at ring block cmd_x0 and its block j is ring block (cmd_x0 + j) mod cmd_cblk
// (the quarter may wrap the ring once).  Region base row cmd_row0.
//
// CONTROL (ot_hdc_v41x_idx_kgrctl), every decision on registers:
//   list read / range count (2 blocks a cycle) -> four never-stalling decode stages (ring block, wrap,
//   row, channel / address fields) -> an 8-pair FIFO with a registered head -> dispatch, decided when the
//   reorder window has room and each target channel has >= 2 free entries (registered), written a cycle
//   later: list-position metadata {channel, entry, block} and the channel ENTRY (address fields).
//   Each channel owns NE entries, allocated and freed in list order (a circular buffer: the drain is in
//   list order, so is every channel's share of it).  Per channel an issuer interleaves ALL its entries still
//   issuing, round robin, one sector request (len 1) a cycle, except that an entry waits while an older
//   entry of the same BANK is still issuing (its row would conflict): so every block the channel holds has
//   sectors queued at the controller -- its bank is visibly needed, which the controller's refresh-aware
//   per-bank refresh honours, and its row opens early -- column commands spread over the bank groups
//   (tCCD_S), and one bank never alternates rows.  A response (tag = {entry, sector}) is written to the
//   channel's data bank and counted; the 17th sets the entry's done bit.
//   The drain samples six list positions ahead (metadata, then done; two cycles stale, never early),
//   takes up to 2 blocks = 16 keys a cycle in list order (two only when on different channels), and frees
//   their entries.
// DATA (ot_hdc_v41x_idx_kgrdata): per channel NE x 17 sectors (behavioural; on silicon per channel 17
//   one-write register files of NE x 256 b, one per sector index: a response writes one, a drain reads
//   all 17 of one channel); the drain builds each key {scale[31:0], codes[511:0]} (the engine's format).
// OUTPUT: valid/ready beats of up to 16 keys (lanes 0-7 block o_blk0, 8-15 block o_blk1; o_kv marks the
//   present keys) -- key k of local block j is position quarter_base + 8 j + k.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_kgrctl #(
    parameter integer NPC  = 32,
    parameter integer WB   = 512,       // list positions in flight (metadata ring), power of two
    parameter integer AW   = 28,        // sector address bits
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer LBW  = 14,        // ring block bits
    parameter integer LMW  = 11,        // list entries = 2^LMW
    parameter integer NE   = 16         // entries (blocks) per channel, power of two
) (
    input  wire                 clk,
    input  wire                 rst_n,
    output wire                 lr_re,
    output wire [LMW-2:0]       lr_addr,
    input  wire [LBW-1:0]       lr_e,
    input  wire [LBW-1:0]       lr_o,
    input  wire                 cmd_v,
    input  wire                 cmd_range,
    input  wire [AW-16:0]       cmd_row0,
    input  wire [LBW-1:0]       cmd_x0,
    input  wire [LBW:0]         cmd_cblk,
    input  wire [LBW:0]         cmd_n,
    output reg                  busy,
    output reg                  fault,      // cmd_x0 >= cmd_cblk or cmd_n > cmd_cblk: not started
    output reg  [NPC-1:0]       req_v,
    input  wire [NPC-1:0]       req_rdy,
    output reg  [NPC*AW-1:0]    req_addr,
    output wire [NPC*LENW-1:0]  req_len,
    output reg  [NPC*TAGW-1:0]  req_tag,
    input  wire [NPC-1:0]       rsp_v,
    output wire [NPC-1:0]       rsp_rdy,
    input  wire [NPC*TAGW-1:0]  rsp_tag,
    output reg  [1:0]           dr_v,
    output reg  [9:0]           dr_pc,
    output reg  [2*$clog2(NE)-1:0] dr_e,
    output reg  [2*LBW-1:0]     dr_blk,
    input  wire                 dr_ready    // room for this drain and two in flight
);
    localparam integer SW = $clog2(WB);
    localparam integer EW = $clog2(NE);
    localparam integer QW = LBW + 2;
    localparam integer RWW = AW - 15;       // row bits
    localparam integer HIW = RWW + 3;       // {row, bank[4:2] ^ row[4:2]}
    localparam integer PD = 8;
    localparam integer PW = $clog2(PD);
    initial if (NPC != 32 || TAGW < EW + 5)
        $fatal(1, "ot_hdc_v41x_idx_kgrctl: NPC = 32, TAGW >= log2(NE) + 5");

    assign req_len = {NPC{LENW'(1)}};
    assign rsp_rdy = {NPC{1'b1}};           // every response has its entry

    reg            run, rng;
    reg [RWW-1:0]  row0;
    reg [LBW-1:0]  x0;
    reg [LBW:0]    cblk;
    reg [QW-1:0]   n, rd_seq, d_seq, d_left;
    reg [4:0]      occ;

    // ---- list read / range count, decode -------------------------------------------------------
    wire           rd_go = run && (rd_seq < n) && (occ < PD);
    assign lr_re = rd_go && !rng;
    assign lr_addr = rd_seq[LMW-1:1];
    reg            c0_v, c0_r; reg [QW-1:0] c0_seq; reg [1:0] c0_m;
    reg            e1_v, e2_v, e3_v, e4_v;
    reg [QW-1:0]   e1_seq, e2_seq, e3_seq, e4_seq;
    reg [1:0]      e1_m, e2_m, e3_m, e4_m;
    reg [LBW-1:0]  e1_blk[0:1], e2_blk[0:1], e3_blk[0:1], e4_blk[0:1];
    reg [LBW:0]    e1_xr[0:1];
    reg [LBW-1:0]  e2_x[0:1];
    reg [9:0]      e3_xl[0:1];
    reg [RWW-1:0]  e3_row[0:1];
    reg [4:0]      e4_pc[0:1], e4_pcf[0:1];
    reg [HIW-1:0]  e4_hi[0:1];
    reg [1:0]      e4_lo[0:1];
    reg [4:0]      e4_bk[0:1];

    // ---- pair FIFO, head ----------------------------------------------------------------------------
    reg [QW-1:0]   pf_seq[0:PD-1];
    reg [1:0]      pf_m  [0:PD-1];
    reg [LBW-1:0]  pf_blk[0:2*PD-1];
    reg [4:0]      pf_pc [0:2*PD-1], pf_pcf[0:2*PD-1];
    reg [HIW-1:0]  pf_hi [0:2*PD-1];
    reg [1:0]      pf_lo [0:2*PD-1];
    reg [4:0]      pf_bk [0:2*PD-1];
    reg [PW-1:0]   pf_wp, pf_rp;
    reg [PW:0]     pf_n;
    reg            hd_v; reg [QW-1:0] hd_seq; reg [1:0] hd_m;
    reg [LBW-1:0]  hd_blk[0:1]; reg [4:0] hd_pc[0:1], hd_pcf[0:1]; reg [HIW-1:0] hd_hi[0:1]; reg [1:0] hd_lo[0:1]; reg [4:0] hd_bk[0:1];

    // ---- dispatch -------------------------------------------------------------------------------------
    reg [NPC-1:0]  okf;                     // channel has >= 2 free entries (registered)
    reg            rob_ok;
    reg [QW-1:0]   inuse;
    reg [EW:0]     ap [0:NPC-1];            // allocated (decision time)
    reg [EW:0]     fp [0:NPC-1];            // freed (drain)
    reg [EW:0]     aw [0:NPC-1];            // written (issuable)
    wire           disp = run && hd_v && rob_ok && okf[hd_pc[0]] && (!hd_m[1] || okf[hd_pc[1]]);
    wire           hd_take = !hd_v || disp;
    wire [EW-1:0]  de0 = ap[hd_pc[0]][EW-1:0];
    wire [EW-1:0]  de1 = ap[hd_pc[1]][EW-1:0] + ((hd_pc[1] == hd_pc[0]) ? EW'(1) : EW'(0));
    reg            w_v; reg [1:0] w_m; reg [SW-1:0] w_s[0:1];
    reg [LBW-1:0]  w_blk[0:1]; reg [4:0] w_pc[0:1], w_pcf[0:1]; reg [HIW-1:0] w_hi[0:1]; reg [1:0] w_lo[0:1]; reg [4:0] w_bk[0:1];
    reg [EW-1:0]   w_e[0:1];

    // ---- list-position metadata, channel entries --------------------------------------------------
    reg [4:0]      m_pc [0:WB-1];
    reg [EW-1:0]   m_e  [0:WB-1];
    reg [LBW-1:0]  m_blk[0:WB-1];
    reg [WB-1:0]   adm;
    reg [HIW-1:0]  en_hi [0:NPC*NE-1];
    reg [4:0]      en_pcf[0:NPC*NE-1];
    reg [1:0]      en_lo [0:NPC*NE-1];
    reg [4:0]      en_ic [0:NPC*NE-1];      // sectors issued
    reg [4:0]      en_cnt[0:NPC*NE-1];      // sectors returned
    reg [NPC*NE-1:0] en_done;

    // ---- issue: entries still issuing, same-bank order, round robin ----------------------------------
    reg [NE-1:0]   isu  [0:NPC-1];          // entry allocated and not all 17 sectors requested
    reg [NE-1:0]   wv   [0:NPC-1];          // entry waits for an older entry of its bank
    reg [EW-1:0]   wpe  [0:NPC*NE-1];       // that entry
    reg [NE-1:0]   elig [0:NPC-1];          // may issue (registered)
    reg [EW-1:0]   lr   [0:NPC-1];          // last entry issued
    reg [EW-1:0]   lbe  [0:NPC*32-1];       // per bank: the youngest entry allocated to it
    reg [NPC-1:0]  rr_v;
    reg [EW-1:0]   rr_e [0:NPC-1];

    // ---- drain ------------------------------------------------------------------------------------------
    reg [5:0]      M_adm; reg [4:0] M_pc[0:5]; reg [EW-1:0] M_e[0:5];
    reg [5:0]      R;     reg [4:0] Rpc[0:5];
    reg [2:0]      advA, advB;
    wire [2:0]     ofs = advA + advB;
    wire           r0 = R[ofs], r1 = R[ofs + 3'd1];
    wire           samepc = (Rpc[ofs] == Rpc[ofs + 3'd1]);
    wire           can0 = run && (d_left != 0) && r0 && dr_ready;
    wire           can1 = can0 && (d_left > 1) && r1 && !samepc;
    reg            dq_v; reg [1:0] dq_m; reg [SW-1:0] dq_slot;

    integer p, l, k, e, i;
    reg [EW-1:0]   esel;
    reg            found, fin;
    reg [4:0]      j;
    reg [EW:0]     apn, fpn;
    reg [1:0]      na, nf;
    reg [QW-1:0]   nu;
    reg [SW-1:0]   s1;

    always @(posedge clk) begin
        if (!rst_n) begin
            run <= 1'b0; rng <= 1'b0; busy <= 1'b0; fault <= 1'b0; req_v <= 0; dr_v <= 0; dq_v <= 1'b0;
            c0_v <= 1'b0; e1_v <= 1'b0; e2_v <= 1'b0; e3_v <= 1'b0; e4_v <= 1'b0;
            hd_v <= 1'b0; w_v <= 1'b0; pf_n <= 0; pf_wp <= 0; pf_rp <= 0; occ <= 0;
            adm <= 0; en_done <= 0; rr_v <= 0; R <= 0; M_adm <= 0; advA <= 0; advB <= 0;
            okf <= {NPC{1'b1}}; rob_ok <= 1'b1; inuse <= 0;
            for (p = 0; p < NPC; p = p + 1) begin
                ap[p] <= 0; fp[p] <= 0; aw[p] <= 0; isu[p] <= 0; wv[p] <= 0; elig[p] <= 0; lr[p] <= 0;
            end
        end else begin
            // ---- responses: registered, then counted ----
            for (p = 0; p < NPC; p = p + 1) begin
                rr_v[p] <= rsp_v[p];
                rr_e[p] <= rsp_tag[p*TAGW + 5 +: EW];
                if (rr_v[p]) begin
                    en_cnt[p*NE + rr_e[p]] <= en_cnt[p*NE + rr_e[p]] + 5'd1;
                    if (en_cnt[p*NE + rr_e[p]] == 5'd16) en_done[p*NE + rr_e[p]] <= 1'b1;
                end
            end
            // ---- dispatch write stage: metadata and channel entries ----
            if (w_v) begin
                for (l = 0; l < 2; l = l + 1) if (w_m[l]) begin
                    adm[w_s[l]] <= 1'b1;
                    m_pc[w_s[l]] <= w_pc[l]; m_e[w_s[l]] <= w_e[l]; m_blk[w_s[l]] <= w_blk[l];
                    en_hi[w_pc[l]*NE + w_e[l]] <= w_hi[l];
                    en_pcf[w_pc[l]*NE + w_e[l]] <= w_pcf[l];
                    en_lo[w_pc[l]*NE + w_e[l]] <= w_lo[l];
                    en_ic[w_pc[l]*NE + w_e[l]] <= 5'd0;
                    en_cnt[w_pc[l]*NE + w_e[l]] <= 5'd0;
                    en_done[w_pc[l]*NE + w_e[l]] <= 1'b0;
                    isu[w_pc[l]][w_e[l]] <= 1'b1;
                    lbe[w_pc[l]*32 + w_bk[l]] <= w_e[l];
                    // an older entry of the same bank still issuing: wait for it (lane 1 may follow lane 0)
                    if (l == 1 && w_m[0] && w_pc[0] == w_pc[1] && w_bk[0] == w_bk[1]) begin
                        wv[w_pc[l]][w_e[l]] <= 1'b1; wpe[w_pc[l]*NE + w_e[l]] <= w_e[0];
                    end else begin
                        wv[w_pc[l]][w_e[l]] <= isu[w_pc[l]][lbe[w_pc[l]*32 + w_bk[l]]];
                        wpe[w_pc[l]*NE + w_e[l]] <= lbe[w_pc[l]*32 + w_bk[l]];
                    end
                end
                for (p = 0; p < NPC; p = p + 1)
                    aw[p] <= aw[p] + (w_m[0] && w_pc[0] == p ? 1 : 0) + (w_m[1] && w_pc[1] == p ? 1 : 0);
            end
            // ---- drain stage 2: entries out to the data path, freed ----
            dr_v <= 2'b00;
            if (dq_v) begin
                s1 = dq_slot + 1'b1;
                adm[dq_slot] <= 1'b0;
                if (dq_m[1]) adm[s1] <= 1'b0;
                dr_v <= dq_m;
                dr_pc <= {m_pc[s1], m_pc[dq_slot]};
                dr_e <= {m_e[s1], m_e[dq_slot]};
                dr_blk <= {m_blk[s1], m_blk[dq_slot]};
            end
            // ---- per-channel allocation / free counters, room flags ----
            for (p = 0; p < NPC; p = p + 1) begin
                na = (disp && hd_pc[0] == p ? 2'd1 : 2'd0) + (disp && hd_m[1] && hd_pc[1] == p ? 2'd1 : 2'd0);
                nf = (dq_v && m_pc[dq_slot] == p ? 2'd1 : 2'd0) +
                     (dq_v && dq_m[1] && m_pc[SW'(dq_slot + 1'b1)] == p ? 2'd1 : 2'd0);
                apn = ap[p] + na;
                fpn = fp[p] + nf;
                ap[p] <= apn;
                fp[p] <= fpn;
                okf[p] <= ((apn - fpn) <= (EW+1)'(NE - 2));
            end
            if (cmd_v && !busy) begin
                fault <= (cmd_x0 >= cmd_cblk) || (cmd_n > cmd_cblk);
                if (!((cmd_x0 >= cmd_cblk) || (cmd_n > cmd_cblk))) begin
                    run <= 1'b1; busy <= 1'b1;
                end
                rng <= cmd_range; row0 <= cmd_row0; x0 <= cmd_x0; cblk <= cmd_cblk; n <= QW'(cmd_n);
                rd_seq <= 0; d_seq <= 0; d_left <= QW'(cmd_n); occ <= 0; inuse <= 0; rob_ok <= 1'b1;
                c0_v <= 1'b0; e1_v <= 1'b0; e2_v <= 1'b0; e3_v <= 1'b0; e4_v <= 1'b0;
                hd_v <= 1'b0; w_v <= 1'b0; pf_n <= 0; pf_wp <= 0; pf_rp <= 0; dq_v <= 1'b0;
                R <= 0; M_adm <= 0; advA <= 0; advB <= 0;
            end else if (run) begin
                // list read (SRAM data next cycle) / range count
                c0_v <= rd_go; c0_r <= rng; c0_seq <= rd_seq; c0_m <= {(QW'(rd_seq + 1) < n), 1'b1};
                if (rd_go) rd_seq <= rd_seq + 2;
                occ <= occ + (rd_go ? 5'd1 : 5'd0) - (disp ? 5'd1 : 5'd0);
                // decode: block -> ring block -> wrap -> row -> channel / address fields
                e1_v <= c0_v; e1_seq <= c0_seq; e1_m <= c0_m;
                e2_v <= e1_v; e2_seq <= e1_seq; e2_m <= e1_m;
                e3_v <= e2_v; e3_seq <= e2_seq; e3_m <= e2_m;
                e4_v <= e3_v; e4_seq <= e3_seq; e4_m <= e3_m;
                for (l = 0; l < 2; l = l + 1) begin
                    e1_blk[l] <= c0_r ? LBW'(c0_seq + l) : (l ? lr_o : lr_e);
                    e1_xr[l] <= {1'b0, x0} + {1'b0, (c0_r ? LBW'(c0_seq + l) : (l ? lr_o : lr_e))};
                    e2_blk[l] <= e1_blk[l];
                    e2_x[l] <= (e1_xr[l] >= cblk) ? LBW'(e1_xr[l] - cblk) : LBW'(e1_xr[l]);
                    e3_blk[l] <= e2_blk[l];
                    e3_xl[l] <= e2_x[l][9:0];
                    e3_row[l] <= row0 + RWW'(e2_x[l] >> 10);
                    e4_blk[l] <= e3_blk[l];
                    e4_pc[l] <= e3_xl[l][4:0] ^ e3_row[l][4:0];
                    e4_hi[l] <= {e3_row[l], e3_xl[l][9:7] ^ e3_row[l][4:2]};
                    e4_pcf[l] <= e3_xl[l][4:0] ^ e3_row[l][4:0] ^ {e3_row[l][1:0], e3_xl[l][9:7] ^ e3_row[l][4:2]};
                    e4_lo[l] <= e3_xl[l][6:5] ^ e3_row[l][1:0];
                    e4_bk[l] <= e3_xl[l][9:5];
                end
                // pair FIFO
                if (e4_v) begin
                    pf_seq[pf_wp] <= e4_seq; pf_m[pf_wp] <= e4_m;
                    for (l = 0; l < 2; l = l + 1) begin
                        pf_blk[2*pf_wp+l] <= e4_blk[l]; pf_pc[2*pf_wp+l] <= e4_pc[l]; pf_pcf[2*pf_wp+l] <= e4_pcf[l];
                        pf_hi[2*pf_wp+l] <= e4_hi[l]; pf_lo[2*pf_wp+l] <= e4_lo[l]; pf_bk[2*pf_wp+l] <= e4_bk[l];
                    end
                    pf_wp <= pf_wp + 1'b1;
                end
                if (hd_take) begin
                    hd_v <= (pf_n != 0);
                    if (pf_n != 0) begin
                        hd_seq <= pf_seq[pf_rp]; hd_m <= pf_m[pf_rp];
                        for (l = 0; l < 2; l = l + 1) begin
                            hd_blk[l] <= pf_blk[2*pf_rp+l]; hd_pc[l] <= pf_pc[2*pf_rp+l]; hd_pcf[l] <= pf_pcf[2*pf_rp+l];
                            hd_hi[l] <= pf_hi[2*pf_rp+l]; hd_lo[l] <= pf_lo[2*pf_rp+l]; hd_bk[l] <= pf_bk[2*pf_rp+l];
                        end
                        pf_rp <= pf_rp + 1'b1;
                    end
                end
                pf_n <= pf_n + (e4_v ? 1'b1 : 1'b0) - ((hd_take && pf_n != 0) ? 1'b1 : 1'b0);
                // dispatch decision -> write stage
                w_v <= disp;
                if (disp) begin
                    w_m <= hd_m;
                    w_s[0] <= SW'(hd_seq); w_s[1] <= SW'(hd_seq + 1'b1);
                    w_e[0] <= de0; w_e[1] <= de1;
                    for (l = 0; l < 2; l = l + 1) begin
                        w_blk[l] <= hd_blk[l]; w_pc[l] <= hd_pc[l]; w_pcf[l] <= hd_pcf[l];
                        w_hi[l] <= hd_hi[l]; w_lo[l] <= hd_lo[l]; w_bk[l] <= hd_bk[l];
                    end
                end
                // drain sampling: metadata of the six positions ahead, then their done bits
                for (k = 0; k < 6; k = k + 1) begin
                    M_adm[k] <= adm[SW'(d_seq + k)];
                    M_pc[k] <= m_pc[SW'(d_seq + k)];
                    M_e[k] <= m_e[SW'(d_seq + k)];
                    R[k] <= M_adm[k] && en_done[M_pc[k]*NE + M_e[k]];
                    Rpc[k] <= M_pc[k];
                end
                advB <= advA;
                advA <= can1 ? 3'd2 : (can0 ? 3'd1 : 3'd0);
                dq_v <= can0;
                dq_m <= {can1, 1'b1};
                dq_slot <= SW'(d_seq);
                if (can0) begin
                    d_seq <= d_seq + (can1 ? 2 : 1);
                    d_left <= d_left - (can1 ? 2 : 1);
                end
                nu = inuse + (disp ? (hd_m[1] ? QW'(2) : QW'(1)) : QW'(0)) - (can1 ? QW'(2) : (can0 ? QW'(1) : QW'(0)));
                inuse <= nu;
                rob_ok <= (nu <= QW'(WB - 8));
                if (d_left == 0 && !dq_v) run <= 1'b0;
            end else if (busy && dr_v == 2'b00 && !dq_v) busy <= 1'b0;
            // ---- per-channel issue: round robin over the eligible entries (registered) ----
            for (p = 0; p < NPC; p = p + 1) begin
                if (req_v[p] && req_rdy[p]) req_v[p] <= 1'b0;
                found = 1'b0; esel = 0;
                for (i = 1; i <= NE; i = i + 1) begin
                    e = (lr[p] + i) % NE;
                    if (!found && elig[p][e]) begin found = 1'b1; esel = EW'(e); end
                end
                fin = 1'b0;
                if (found && (!req_v[p] || req_rdy[p])) begin
                    j = en_ic[p*NE + esel];
                    req_v[p] <= 1'b1;
                    req_addr[p*AW +: AW] <= {en_hi[p*NE + esel], j, en_pcf[p*NE + esel] ^ j, en_lo[p*NE + esel]};
                    req_tag[p*TAGW +: TAGW] <= TAGW'({esel, j});
                    en_ic[p*NE + esel] <= j + 5'd1;
                    lr[p] <= esel;
                    fin = (j == 5'd16);
                    if (fin) isu[p][esel] <= 1'b0;
                end
                for (e = 0; e < NE; e = e + 1) begin
                    if (wv[p][e] && !isu[p][wpe[p*NE + e]]) wv[p][e] <= 1'b0;   // the older entry is done
                    elig[p][e] <= isu[p][e] && !(wv[p][e] && isu[p][wpe[p*NE + e]]) && !(fin && esel == e);
                end
            end
        end
    end
endmodule

// Data banks and the drain gather (behavioural; per-channel register files on silicon).
module ot_hdc_v41x_idx_kgrdata #(
    parameter integer NPC  = 32,
    parameter integer TAGW = 16,
    parameter integer DW   = 256,
    parameter integer LBW  = 14,
    parameter integer NE   = 16
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [NPC-1:0]       rsp_v,
    input  wire [NPC*TAGW-1:0]  rsp_tag,
    input  wire [NPC*DW-1:0]    rsp_data,
    input  wire [1:0]           dr_v,
    input  wire [9:0]           dr_pc,
    input  wire [2*$clog2(NE)-1:0] dr_e,
    input  wire [2*LBW-1:0]     dr_blk,
    output wire                 dr_ready,
    output reg                  o_valid,
    input  wire                 o_ready,
    output reg  [15:0]          o_kv,
    output reg  [16*544-1:0]    o_key,
    output reg  [2*LBW-1:0]     o_blk
);
    localparam integer EW = $clog2(NE);
    reg [DW-1:0] mem [0:NPC*NE*17-1];
    integer p, b, k, base;
    always @(posedge clk)
        for (p = 0; p < NPC; p = p + 1)
            if (rsp_v[p])
                mem[(p * NE + rsp_tag[p*TAGW + 5 +: EW]) * 17 + rsp_tag[p*TAGW +: 5]] <= rsp_data[p*DW +: DW];
    reg [15:0]       f_kv  [0:3];
    reg [16*544-1:0] f_key [0:3];
    reg [2*LBW-1:0]  f_blk [0:3];
    reg [1:0]        f_wp, f_rp;
    reg [2:0]        f_n;
    assign dr_ready = (f_n <= 3'd1);
    always @* begin
        o_valid = (f_n != 0);
        o_kv = f_kv[f_rp]; o_key = f_key[f_rp]; o_blk = f_blk[f_rp];
    end
    reg [15:0]       g_kv;
    reg [16*544-1:0] g_key;
    always @* begin
        g_kv = 0; g_key = 0;
        for (b = 0; b < 2; b = b + 1) begin
            base = (dr_pc[5*b +: 5] * NE + dr_e[EW*b +: EW]) * 17;
            for (k = 0; k < 8; k = k + 1) begin
                g_kv[8*b + k] = dr_v[b];
                if (dr_v[b])
                    g_key[(8*b + k)*544 +: 544] = {mem[base][32*k +: 32], mem[base + 2 + 2*k], mem[base + 1 + 2*k]};
            end
        end
    end
    always @(posedge clk) begin
        if (!rst_n) begin f_wp <= 0; f_rp <= 0; f_n <= 0; end
        else begin
            if (dr_v != 2'b00) begin
                f_kv[f_wp] <= g_kv; f_key[f_wp] <= g_key; f_blk[f_wp] <= dr_blk; f_wp <= f_wp + 1'b1;
            end
            if (o_valid && o_ready) f_rp <= f_rp + 1'b1;
            f_n <= f_n + ((dr_v != 2'b00) ? 3'd1 : 3'd0) - ((o_valid && o_ready) ? 3'd1 : 3'd0);
        end
    end
endmodule

// One stack's row-layout reader: candidate list SRAM + control + data.
module ot_hdc_v41x_idx_kgrow #(
    parameter integer NPC  = 32,
    parameter integer WB   = 512,
    parameter integer AW   = 28,
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer DW   = 256,
    parameter integer LBW  = 14,
    parameter integer LMW  = 11,
    parameter integer NE   = 16
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 lw_v,
    input  wire [LMW-1:0]       lw_addr,
    input  wire [LBW-1:0]       lw_blk,
    input  wire                 cmd_v,
    input  wire                 cmd_range,
    input  wire [AW-16:0]       cmd_row0,
    input  wire [LBW-1:0]       cmd_x0,
    input  wire [LBW:0]         cmd_cblk,
    input  wire [LBW:0]         cmd_n,
    output wire                 busy,
    output wire                 fault,
    output wire [NPC-1:0]       req_v,
    input  wire [NPC-1:0]       req_rdy,
    output wire [NPC*AW-1:0]    req_addr,
    output wire [NPC*LENW-1:0]  req_len,
    output wire [NPC*TAGW-1:0]  req_tag,
    input  wire [NPC-1:0]       rsp_v,
    output wire [NPC-1:0]       rsp_rdy,
    input  wire [NPC*TAGW-1:0]  rsp_tag,
    input  wire [NPC*DW-1:0]    rsp_data,
    output wire                 o_valid,
    input  wire                 o_ready,
    output wire [15:0]          o_kv,
    output wire [16*544-1:0]    o_key,
    output wire [2*LBW-1:0]     o_blk,
    output reg  [47:0]          cnt_keys_streamed,
    output reg  [47:0]          cnt_hbm_beats
);
    localparam integer EW = $clog2(NE);
    wire [1:0] dr_v;
    wire [9:0] dr_pc;
    wire [2*EW-1:0] dr_e;
    wire [2*LBW-1:0] dr_blk;
    wire dr_ready, cbusy;
    assign busy = cbusy || o_valid;
    reg [LBW-1:0] lm_e [0:(1 << (LMW - 1)) - 1];
    reg [LBW-1:0] lm_o [0:(1 << (LMW - 1)) - 1];
    reg [LBW-1:0] lr_e, lr_o;
    wire          lr_re;
    wire [LMW-2:0] lr_addr;
    always @(posedge clk) begin
        if (lw_v) begin
            if (lw_addr[0]) lm_o[lw_addr[LMW-1:1]] <= lw_blk;
            else            lm_e[lw_addr[LMW-1:1]] <= lw_blk;
        end
        if (lr_re) begin lr_e <= lm_e[lr_addr]; lr_o <= lm_o[lr_addr]; end
    end
    integer ck;
    reg [4:0] nko;
    reg [5:0] nbt;
    always @* begin
        nko = 0; nbt = 0;
        for (ck = 0; ck < 16; ck = ck + 1) nko = nko + o_kv[ck];
        for (ck = 0; ck < NPC; ck = ck + 1) nbt = nbt + rsp_v[ck];
    end
    always @(posedge clk)
        if (!rst_n) begin cnt_keys_streamed <= 0; cnt_hbm_beats <= 0; end
        else begin
            if (o_valid && o_ready) cnt_keys_streamed <= cnt_keys_streamed + nko;
            cnt_hbm_beats <= cnt_hbm_beats + nbt;
        end
    ot_hdc_v41x_idx_kgrctl #(.NPC(NPC), .WB(WB), .AW(AW), .TAGW(TAGW), .LENW(LENW), .LBW(LBW), .LMW(LMW),
                             .NE(NE)) u_c (
        .clk(clk), .rst_n(rst_n), .lr_re(lr_re), .lr_addr(lr_addr), .lr_e(lr_e), .lr_o(lr_o),
        .cmd_v(cmd_v), .cmd_range(cmd_range), .cmd_row0(cmd_row0), .cmd_x0(cmd_x0), .cmd_cblk(cmd_cblk),
        .cmd_n(cmd_n), .busy(cbusy), .fault(fault),
        .req_v(req_v), .req_rdy(req_rdy), .req_addr(req_addr), .req_len(req_len), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(rsp_tag),
        .dr_v(dr_v), .dr_pc(dr_pc), .dr_e(dr_e), .dr_blk(dr_blk), .dr_ready(dr_ready));
    ot_hdc_v41x_idx_kgrdata #(.NPC(NPC), .TAGW(TAGW), .DW(DW), .LBW(LBW), .NE(NE)) u_d (
        .clk(clk), .rst_n(rst_n), .rsp_v(rsp_v), .rsp_tag(rsp_tag), .rsp_data(rsp_data),
        .dr_v(dr_v), .dr_pc(dr_pc), .dr_e(dr_e), .dr_blk(dr_blk), .dr_ready(dr_ready),
        .o_valid(o_valid), .o_ready(o_ready), .o_kv(o_kv), .o_key(o_key), .o_blk(o_blk));
endmodule
