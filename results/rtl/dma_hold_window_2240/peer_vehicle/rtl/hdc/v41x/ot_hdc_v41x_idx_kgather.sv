`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Index-key CANDIDATE-BLOCK GATHER from HBM, one HBM3E stack (NPC pseudo-channels).
// DeepSeek-V4.1 re-index layers (L24, L28, L32, L36): the golden scores ALL keys and
// then masks every position outside the candidate blocks of the candidate-source layer
// (tools/hdc_golden_v41.py Model.indexer: s = where(cand, s, -inf)).  A masked key can
// never be selected while at least k keys are candidates (always: see
// ot_hdc_v41x_sel_mdrop), and a key's score depends on that key alone, so reading and
// scoring ONLY the candidate blocks gives the same scores at the same positions and the
// same selection.  This unit replaces the full-range ot_hdc_v41x_idx_kstream_range scan
// for those layers (opt-in: the full scan stays the default path).
//
// KEY LAYOUT: ot_hdc_v41x_idx_kstream_range's (68 B a key; 1,024-key super-blocks of 17
// 4-KB blocks: block 0 the scales, 4 B a key; blocks 1..16 the codes, 64 B a key; column c
// of block B on pseudo-channel c ^ fold(B), fold(B) = (B ^ B >> 5) mod 32).  A candidate
// block is 8 positions, 8-aligned; with the stack's ring head (cmd_skip) a multiple of 8
// its 8 keys are 8 consecutive keys of one super-block, so it is exactly
//   * 4 full code columns (4 x 128 B = 8 keys x 64 B) of one code block, on 4 distinct
//     pseudo-channels:  column 4 (j mod 8) + i of block B0 + 1 + j / 8, i = 0..3;
//   * 1 scale sector (8 keys x 4 B = 32 B): sector j of block B0;
// where j = local 8-key group within the super-block, B0 = base + 17 * super-block.
// 17 sectors a block, every one needed: no over-fetch.
//
// LIST: the stack's candidate blocks (local block indices, ascending), written ahead
// through lw_* (the candidate list is produced >= 4 layers earlier by the candidate
// select, ot_hdc_v41x_sel_cand, whose output port q is already quarter q's ascending
// list); two banks (even / odd entries) so two blocks are read a cycle.
//
// CONTROL (ot_hdc_v41x_idx_kgctl), pipelined for 1.2 GHz (every decision reads registers):
//   list read (2 blocks a cycle, while fewer than 8 pairs are undispatched) -> five
//   never-stalling decode stages (local key, 17 x super-block, offsets, block addresses,
//   folds / channel one-hots) -> an 8-pair FIFO with a registered head -> dispatch, decided
//   when the reorder buffer has the pair's two slots and every targeted request FIFO has
//   >= 4 free entries (2 in flight), and written one cycle later: slots, metadata, pending
//   bits and the per-channel request FIFOs (one code FIFO and one scale FIFO a channel, two
//   write ports each).  A channel issues its scale head first, else its code head.
//   Slot = sequence mod WB.  Per slot and channel a pending bit (code / scale) is set at
//   dispatch and cleared by the request's last beat (code beats counted: the HBM scheduler
//   reorders bursts); a slot is complete when dispatched and nothing is pending (registered).
//   The drain samples the completion of the head and the next three slots, decides on the
//   sample a cycle later (stale, never early), takes up to 2 blocks = 16 keys a cycle in
//   list order (the select needs ascending positions), and reads the slots' metadata in a
//   second stage.
// DATA (ot_hdc_v41x_idx_kgdata): per pseudo-channel bank WB x 4 code beats + WB scale
// sectors (behavioural here; one 1W1R SRAM bank per channel on silicon, the
// kstream_range ROB plus a WB x 256 b scale bank); the drain gathers each key's
// {scale[31:0], codes[511:0]} (the engine's key format).
// OUTPUT: valid/ready beats of up to 16 keys (lanes 0-7 block o_blk0, 8-15 block
// o_blk1; o_kv marks present keys) -- key j of block b is position quarter_base + 8 b + j.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_kgctl #(
    parameter integer NPC  = 32,
    parameter integer WB   = 128,       // reorder slots (blocks), power of two
    parameter integer AW   = 28,        // sector address bits
    parameter integer HW   = 20,        // 4-KB block address bits
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4,
    parameter integer LBW  = 14,        // local block index bits
    parameter integer LMW  = 11,        // list entries = 2^LMW
    parameter integer DF   = 8          // request FIFO depth per channel and kind
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // candidate-list SRAM (two banks, even / odd entries), synchronous read: data of the
    // address presented with lr_re appears on lr_e / lr_o after the edge
    output wire                 lr_re,
    output wire [LMW-2:0]       lr_addr,
    input  wire [LBW-1:0]       lr_e,
    input  wire [LBW-1:0]       lr_o,
    input  wire                 cmd_v,
    input  wire [HW-1:0]        cmd_base,
    input  wire [9:0]           cmd_skip,   // ring head, keys (multiple of 8)
    input  wire [LMW:0]         cmd_n,      // candidate blocks of this stack
    output reg                  busy,
    output reg                  fault,      // cmd_skip not a multiple of 8
    output reg  [NPC-1:0]       req_v,
    input  wire [NPC-1:0]       req_rdy,
    output reg  [NPC*AW-1:0]    req_addr,
    output reg  [NPC*LENW-1:0]  req_len,
    output reg  [NPC*TAGW-1:0]  req_tag,
    input  wire [NPC-1:0]       rsp_v,
    output wire [NPC-1:0]       rsp_rdy,
    input  wire [NPC*TAGW-1:0]  rsp_tag,
    input  wire [NPC*BEATW-1:0] rsp_beat,
    output reg  [1:0]           dr_v,
    output reg  [$clog2(WB)-1:0] dr_slot,   // block 0's slot (block 1: dr_slot + 1)
    output reg  [2*7-1:0]       dr_j,
    output reg  [2*5-1:0]       dr_fc,
    output reg  [2*5-1:0]       dr_f0,
    output reg  [2*LBW-1:0]     dr_blk,
    input  wire                 dr_ready    // room for this drain and two in flight
);
    localparam integer SW = $clog2(WB);
    localparam integer QW = LMW + 1;
    localparam integer FW = $clog2(DF);
    localparam integer ND = 5;              // decode stages (fixed latency, never stall)
    localparam integer PD = 8;              // decoded-pair FIFO depth
    localparam integer PW = $clog2(PD);

    function automatic [4:0] fold(input [HW-1:0] b);
        fold = b[4:0] ^ b[9:5];
    endfunction

    reg            run;
    reg [HW-1:0]   base;
    reg [6:0]      skip8;
    reg [QW-1:0]   n;
    reg [QW-1:0]   rd_seq;                  // next pair to read
    reg [QW-1:0]   d_seq;                   // drain head
    reg [QW-1:0]   d_left;                  // n - d_seq
    reg [4:0]      occ;                     // pairs read and not yet dispatched

    // -- list read and the decode pipe -----------------------------------------------------------
    wire           rd_go = run && (rd_seq < n) && (occ < PD);
    assign lr_re = rd_go;
    assign lr_addr = rd_seq[LMW-1:1];
    reg            c0_v;   reg [QW-1:0] c0_seq; reg [1:0] c0_m;
    reg            e1_v;   reg [QW-1:0] e1_seq; reg [1:0] e1_m;
    reg            e2_v;   reg [QW-1:0] e2_seq; reg [1:0] e2_m;
    reg            e3_v;   reg [QW-1:0] e3_seq; reg [1:0] e3_m;
    reg            e4_v;   reg [QW-1:0] e4_seq; reg [1:0] e4_m;
    reg            e5_v;   reg [QW-1:0] e5_seq; reg [1:0] e5_m;
    reg [LBW+6:0]  e1_lk [0:1];             // local key / 8
    reg [LBW-1:0]  e1_blk[0:1], e2_blk[0:1], e3_blk[0:1], e4_blk[0:1], e5_blk[0:1];
    reg [LBW+4:0]  e2_m17[0:1];             // 17 x super-block
    reg [6:0]      e2_j [0:1], e3_j [0:1], e4_j [0:1], e5_j [0:1];
    reg [HW-1:0]   e3_o0[0:1], e3_oc[0:1];  // offsets of the scale / code block
    reg [HW-1:0]   e4_b0[0:1], e4_bc[0:1], e5_b0[0:1], e5_bc[0:1];
    reg [4:0]      e5_f0[0:1], e5_fc[0:1];
    reg [NPC-1:0]  e5_cm[0:1], e5_sm[0:1];

    // -- decoded-pair FIFO, registered head ----------------------------------------------------------
    reg [QW-1:0]   pf_seq [0:PD-1];
    reg [1:0]      pf_m   [0:PD-1];
    reg [LBW-1:0]  pf_blk [0:2*PD-1];
    reg [6:0]      pf_j   [0:2*PD-1];
    reg [4:0]      pf_f0  [0:2*PD-1], pf_fc [0:2*PD-1];
    reg [HW-1:0]   pf_b0  [0:2*PD-1], pf_bc [0:2*PD-1];
    reg [NPC-1:0]  pf_cm  [0:2*PD-1], pf_sm [0:2*PD-1];
    reg [PW-1:0]   pf_wp, pf_rp;
    reg [PW:0]     pf_n;
    reg            hd_v;   reg [QW-1:0] hd_seq; reg [1:0] hd_m; reg [SW-1:0] hd_s1;
    reg [LBW-1:0]  hd_blk[0:1]; reg [6:0] hd_j[0:1]; reg [4:0] hd_f0[0:1], hd_fc[0:1];
    reg [HW-1:0]   hd_b0[0:1], hd_bc[0:1];
    reg [NPC-1:0]  hd_cm[0:1], hd_sm[0:1];

    // -- dispatch: decided on registers, written one cycle later -----------------------------------
    // both conditions registered: every request FIFO has >= 4 free entries (2 in flight + 2),
    // and the slots in use (dispatched pairs x 2 - drained) leave room for this pair and one
    // in flight (conservative: a FIFO filling anywhere pauses dispatch for a cycle)
    reg            room_all, rob_ok;
    reg [QW-1:0]   inuse;
    wire           disp = run && hd_v && rob_ok && room_all;
    wire           hd_take = !hd_v || disp;
    reg            w_v;    reg [QW-1:0] w_seq; reg [1:0] w_m; reg [SW-1:0] w_rs[0:1];
    reg [LBW-1:0]  w_blk[0:1]; reg [6:0] w_j[0:1]; reg [4:0] w_f0[0:1], w_fc[0:1];
    reg [HW-1:0]   w_b0[0:1], w_bc[0:1];
    reg [NPC-1:0]  w_cm[0:1], w_sm[0:1];

    // -- per-channel request FIFOs: [0, NPC) code, [NPC, 2 NPC) scale ------------------------------
    reg [AW-1:0]   fq_addr [0:2*NPC*DF-1];
    reg [SW-1:0]   fq_slot [0:2*NPC*DF-1];
    reg [FW-1:0]   fq_rp   [0:2*NPC-1];
    reg [FW-1:0]   fq_wp   [0:2*NPC-1];
    reg [FW:0]     fq_n    [0:2*NPC-1];

    // -- slot state ------------------------------------------------------------------------------------
    reg [NPC-1:0]  pend_c [0:WB-1];
    reg [NPC-1:0]  pend_s [0:WB-1];
    reg [1:0]      cntc   [0:NPC*WB-1];
    reg [WB-1:0]   adm;
    reg [WB-1:0]   cmp;                     // registered completion
    reg [6:0]      m_j   [0:WB-1];
    reg [4:0]      m_fc  [0:WB-1];
    reg [4:0]      m_f0  [0:WB-1];
    reg [LBW-1:0]  m_blk [0:WB-1];

    assign rsp_rdy = {NPC{1'b1}};           // every beat has its slot (allocated at dispatch)

    // -- drain: completion of head .. head+3 sampled a cycle earlier; adv_r = the step taken then ----
    reg [3:0]      rq;
    reg [1:0]      adv_r;
    wire [SW-1:0]  h0 = d_seq[SW-1:0];
    wire           rq0 = (adv_r == 2'd0) ? rq[0] : (adv_r == 2'd1) ? rq[1] : rq[2];
    wire           rq1 = (adv_r == 2'd0) ? rq[1] : (adv_r == 2'd1) ? rq[2] : rq[3];
    wire           can0 = run && (d_left != 0) && rq0 && dr_ready;
    wire           can1 = can0 && (d_left > 1) && rq1;
    reg            dq_v; reg [1:0] dq_m; reg [SW-1:0] dq_slot;    // drain decided: read metadata next

    // per channel issue: the scale head first, else the code head
    reg [NPC-1:0]  iss, use_s;
    integer q;
    always @* begin
        for (q = 0; q < NPC; q = q + 1) begin
            use_s[q] = (fq_n[NPC + q] != 0);
            iss[q] = run && ((fq_n[q] != 0) || use_s[q]) && (!req_v[q] || req_rdy[q]);
        end
    end

    integer p, l, e, c, k;
    reg [SW-1:0]   rs;
    reg [FW:0]     cnt;
    reg [FW-1:0]   wp;
    reg [NPC-1:0]  t;
    reg [2*NPC-1:0] rm;
    reg [QW-1:0]   nu;

    // registered responses
    reg [NPC-1:0]  rr_v;
    reg [SW-1:0]   rr_s [0:NPC-1];
    reg            rr_k [0:NPC-1];

    always @(posedge clk) begin
        if (!rst_n) begin
            run <= 1'b0; busy <= 1'b0; fault <= 1'b0; req_v <= 0; dr_v <= 0; dq_v <= 1'b0;
            c0_v <= 1'b0; e1_v <= 1'b0; e2_v <= 1'b0; e3_v <= 1'b0; e4_v <= 1'b0; e5_v <= 1'b0;
            hd_v <= 1'b0; w_v <= 1'b0; pf_n <= 0; pf_wp <= 0; pf_rp <= 0; occ <= 0;
            adm <= 0; cmp <= 0; rr_v <= 0; rq <= 0; adv_r <= 0;
            room_all <= 1'b1; rob_ok <= 1'b1; inuse <= 0;
            for (p = 0; p < 2 * NPC; p = p + 1) begin fq_rp[p] <= 0; fq_wp[p] <= 0; fq_n[p] <= 0; end
            for (p = 0; p < NPC * WB; p = p + 1) cntc[p] <= 2'd0;   // 4 beats wrap it back to 0
        end else begin
            // completion, one cycle late; head look-ahead, one more
            for (e = 0; e < WB; e = e + 1) cmp[e] <= adm[e] && ~|pend_c[e] && ~|pend_s[e];
            // responses: registered, then counted
            for (p = 0; p < NPC; p = p + 1) begin
                rr_v[p] <= rsp_v[p];
                rr_s[p] <= rsp_tag[p*TAGW +: SW];
                rr_k[p] <= rsp_tag[p*TAGW + SW];
                if (rr_v[p]) begin
                    if (rr_k[p]) pend_s[rr_s[p]][p] <= 1'b0;
                    else begin
                        cntc[p * WB + rr_s[p]] <= cntc[p * WB + rr_s[p]] + 2'd1;
                        if (cntc[p * WB + rr_s[p]] == 2'd3) pend_c[rr_s[p]][p] <= 1'b0;
                    end
                end
            end
            // dispatch write stage (decided last cycle): slots, metadata, pending bits
            if (w_v) begin
                for (l = 0; l < 2; l = l + 1) if (w_m[l]) begin
                    rs = w_rs[l];
                    adm[rs] <= 1'b1;
                    pend_c[rs] <= w_cm[l];
                    pend_s[rs] <= w_sm[l];
                    m_j[rs] <= w_j[l]; m_fc[rs] <= w_fc[l]; m_f0[rs] <= w_f0[l]; m_blk[rs] <= w_blk[l];
                end
            end
            // drain stage 2: retire the slots, read their metadata for the data path
            dr_v <= 2'b00;
            if (dq_v) begin
                adm[dq_slot] <= 1'b0;
                if (dq_m[1]) adm[SW'(dq_slot + 1)] <= 1'b0;
                dr_v <= dq_m;
                dr_slot <= dq_slot;
                dr_j <= {m_j[SW'(dq_slot + 1)], m_j[dq_slot]};
                dr_fc <= {m_fc[SW'(dq_slot + 1)], m_fc[dq_slot]};
                dr_f0 <= {m_f0[SW'(dq_slot + 1)], m_f0[dq_slot]};
                dr_blk <= {m_blk[SW'(dq_slot + 1)], m_blk[dq_slot]};
            end
            if (cmd_v && !busy) begin
                run <= 1'b1; busy <= 1'b1;
                base <= cmd_base; skip8 <= cmd_skip[9:3]; n <= cmd_n;
                fault <= (cmd_skip[2:0] != 3'd0);
                rd_seq <= 0; d_seq <= 0; d_left <= cmd_n; occ <= 0; inuse <= 0; rob_ok <= 1'b1;
                c0_v <= 1'b0; e1_v <= 1'b0; e2_v <= 1'b0; e3_v <= 1'b0; e4_v <= 1'b0; e5_v <= 1'b0;
                hd_v <= 1'b0; w_v <= 1'b0; pf_n <= 0; pf_wp <= 0; pf_rp <= 0; rq <= 0; adv_r <= 0; dq_v <= 1'b0;
            end else if (run) begin
                // list read (SRAM output valid next cycle)
                c0_v <= rd_go; c0_seq <= rd_seq; c0_m <= {(QW'(rd_seq + 1) < n), 1'b1};
                if (rd_go) rd_seq <= rd_seq + 2;
                occ <= occ + (rd_go ? 5'd1 : 5'd0) - (disp ? 5'd1 : 5'd0);
                // decode pipe
                e1_v <= c0_v; e1_seq <= c0_seq; e1_m <= c0_m;
                e2_v <= e1_v; e2_seq <= e1_seq; e2_m <= e1_m;
                e3_v <= e2_v; e3_seq <= e2_seq; e3_m <= e2_m;
                e4_v <= e3_v; e4_seq <= e3_seq; e4_m <= e3_m;
                e5_v <= e4_v; e5_seq <= e4_seq; e5_m <= e4_m;
                for (l = 0; l < 2; l = l + 1) begin
                    e1_blk[l] <= l ? lr_o : lr_e;
                    e1_lk[l] <= {{LBW{1'b0}}, skip8} + {7'd0, l ? lr_o : lr_e};
                    e2_blk[l] <= e1_blk[l]; e2_j[l] <= e1_lk[l][6:0];
                    e2_m17[l] <= {e1_lk[l][LBW+6:7], 4'd0} + {4'd0, e1_lk[l][LBW+6:7]};
                    e3_blk[l] <= e2_blk[l]; e3_j[l] <= e2_j[l];
                    e3_o0[l] <= HW'(e2_m17[l]);
                    e3_oc[l] <= HW'(e2_m17[l]) + HW'(1) + HW'(e2_j[l][6:3]);
                    e4_blk[l] <= e3_blk[l]; e4_j[l] <= e3_j[l];
                    e4_b0[l] <= base + e3_o0[l];
                    e4_bc[l] <= base + e3_oc[l];
                    e5_blk[l] <= e4_blk[l]; e5_j[l] <= e4_j[l]; e5_b0[l] <= e4_b0[l]; e5_bc[l] <= e4_bc[l];
                    e5_f0[l] <= fold(e4_b0[l]); e5_fc[l] <= fold(e4_bc[l]);
                    t = 0;
                    for (c = 0; c < 4; c = c + 1) t[(5'({e4_j[l][2:0], 2'b00}) + 5'(c)) ^ fold(e4_bc[l])] = 1'b1;
                    e5_cm[l] <= t;
                    t = 0;
                    t[e4_j[l][6:2] ^ fold(e4_b0[l])] = 1'b1;
                    e5_sm[l] <= t;
                end
                // pair FIFO: push from the pipe, pop into the head register
                if (e5_v) begin
                    pf_seq[pf_wp] <= e5_seq; pf_m[pf_wp] <= e5_m;
                    for (l = 0; l < 2; l = l + 1) begin
                        pf_blk[2*pf_wp+l] <= e5_blk[l]; pf_j[2*pf_wp+l] <= e5_j[l];
                        pf_f0[2*pf_wp+l] <= e5_f0[l]; pf_fc[2*pf_wp+l] <= e5_fc[l];
                        pf_b0[2*pf_wp+l] <= e5_b0[l]; pf_bc[2*pf_wp+l] <= e5_bc[l];
                        pf_cm[2*pf_wp+l] <= e5_m[l] ? e5_cm[l] : {NPC{1'b0}};
                        pf_sm[2*pf_wp+l] <= e5_m[l] ? e5_sm[l] : {NPC{1'b0}};
                    end
                    pf_wp <= pf_wp + 1'b1;
                end
                if (hd_take) begin
                    hd_v <= (pf_n != 0);
                    if (pf_n != 0) begin
                        hd_seq <= pf_seq[pf_rp]; hd_m <= pf_m[pf_rp]; hd_s1 <= SW'(pf_seq[pf_rp]) + 1'b1;
                        for (l = 0; l < 2; l = l + 1) begin
                            hd_blk[l] <= pf_blk[2*pf_rp+l]; hd_j[l] <= pf_j[2*pf_rp+l];
                            hd_f0[l] <= pf_f0[2*pf_rp+l]; hd_fc[l] <= pf_fc[2*pf_rp+l];
                            hd_b0[l] <= pf_b0[2*pf_rp+l]; hd_bc[l] <= pf_bc[2*pf_rp+l];
                            hd_cm[l] <= pf_cm[2*pf_rp+l]; hd_sm[l] <= pf_sm[2*pf_rp+l];
                        end
                        pf_rp <= pf_rp + 1'b1;
                    end
                end
                pf_n <= pf_n + (e5_v ? 1'b1 : 1'b0) - ((hd_take && pf_n != 0) ? 1'b1 : 1'b0);
                // dispatch decision -> write stage
                w_v <= disp;
                if (disp) begin
                    w_seq <= hd_seq; w_m <= hd_m;
                    w_rs[0] <= hd_seq[SW-1:0]; w_rs[1] <= hd_s1;
                    for (l = 0; l < 2; l = l + 1) begin
                        w_blk[l] <= hd_blk[l]; w_j[l] <= hd_j[l]; w_f0[l] <= hd_f0[l]; w_fc[l] <= hd_fc[l];
                        w_b0[l] <= hd_b0[l]; w_bc[l] <= hd_bc[l]; w_cm[l] <= hd_cm[l]; w_sm[l] <= hd_sm[l];
                    end
                end
                // per-channel issue
                for (p = 0; p < NPC; p = p + 1) begin
                    if (req_v[p] && req_rdy[p]) req_v[p] <= 1'b0;
                    if (iss[p]) begin
                        req_v[p] <= 1'b1;
                        if (use_s[p]) begin
                            req_addr[p*AW +: AW] <= fq_addr[(NPC + p) * DF + fq_rp[NPC + p]];
                            req_len[p*LENW +: LENW] <= LENW'(1);
                            req_tag[p*TAGW +: TAGW] <= TAGW'({1'b1, fq_slot[(NPC + p) * DF + fq_rp[NPC + p]]});
                        end else begin
                            req_addr[p*AW +: AW] <= fq_addr[p * DF + fq_rp[p]];
                            req_len[p*LENW +: LENW] <= LENW'(4);
                            req_tag[p*TAGW +: TAGW] <= TAGW'({1'b0, fq_slot[p * DF + fq_rp[p]]});
                        end
                    end
                end
                // FIFO pushes (from the write stage) / pops, counts, room
                for (p = 0; p < 2 * NPC; p = p + 1) begin
                    cnt = fq_n[p];
                    wp = fq_wp[p];
                    if (w_v) begin
                        for (l = 0; l < 2; l = l + 1)
                            if (p < NPC ? w_cm[l][p % NPC] : w_sm[l][p % NPC]) begin
                                fq_slot[p * DF + wp] <= w_rs[l];
                                // code: channel p serves column p ^ fold(Bc); scale: sector j of B0
                                fq_addr[p * DF + wp] <= (p < NPC) ? AW'({w_bc[l], 5'(p % NPC) ^ w_fc[l], 2'b00})
                                                                  : AW'({w_b0[l], w_j[l]});
                                wp = wp + 1'b1;
                                cnt = cnt + 1'b1;
                            end
                    end
                    fq_wp[p] <= wp;
                    if (p < NPC ? (iss[p % NPC] && !use_s[p % NPC]) : (iss[p % NPC] && use_s[p % NPC])) begin
                        fq_rp[p] <= fq_rp[p] + 1'b1;
                        cnt = cnt - 1'b1;
                    end
                    fq_n[p] <= cnt;
                    rm[p] = (cnt + 4 <= DF);
                end
                room_all <= &rm;
                // drain stage 1: head and next, in order
                for (k = 0; k < 4; k = k + 1) rq[k] <= cmp[SW'(h0 + k)];
                adv_r <= can1 ? 2'd2 : (can0 ? 2'd1 : 2'd0);
                dq_v <= can0;
                dq_m <= {can1, 1'b1};
                dq_slot <= h0;
                if (can0) begin
                    d_seq <= d_seq + (can1 ? 2 : 1);
                    d_left <= d_left - (can1 ? 2 : 1);
                end
                nu = inuse + (disp ? QW'(2) : QW'(0)) - (can1 ? QW'(2) : (can0 ? QW'(1) : QW'(0)));
                inuse <= nu;
                rob_ok <= (nu <= QW'(WB - 4));
                if (d_left == 0 && !dq_v) run <= 1'b0;
            end else if (busy && dr_v == 2'b00 && !dq_v) busy <= 1'b0;
        end
    end
endmodule

// Reorder storage and the drain gather (behavioural banks; SRAM on silicon).
module ot_hdc_v41x_idx_kgdata #(
    parameter integer NPC  = 32,
    parameter integer WB   = 128,
    parameter integer TAGW = 16,
    parameter integer BEATW = 4,
    parameter integer DW   = 256,
    parameter integer LBW  = 14
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [NPC-1:0]       rsp_v,
    input  wire [NPC*TAGW-1:0]  rsp_tag,
    input  wire [NPC*BEATW-1:0] rsp_beat,
    input  wire [NPC*DW-1:0]    rsp_data,
    input  wire [1:0]           dr_v,
    input  wire [$clog2(WB)-1:0] dr_slot,
    input  wire [2*7-1:0]       dr_j,
    input  wire [2*5-1:0]       dr_fc,
    input  wire [2*5-1:0]       dr_f0,
    input  wire [2*LBW-1:0]     dr_blk,
    output wire                 dr_ready,
    output reg                  o_valid,
    input  wire                 o_ready,
    output reg  [15:0]          o_kv,
    output reg  [16*544-1:0]    o_key,
    output reg  [2*LBW-1:0]     o_blk
);
    localparam integer SW = $clog2(WB);
    reg [DW-1:0] code_mem  [0:NPC*WB*4-1];
    reg [DW-1:0] scale_mem [0:NPC*WB-1];
    integer p, b, k;
    always @(posedge clk)
        for (p = 0; p < NPC; p = p + 1)
            if (rsp_v[p]) begin
                if (rsp_tag[p*TAGW + SW])
                    scale_mem[p * WB + rsp_tag[p*TAGW +: SW]] <= rsp_data[p*DW +: DW];
                else
                    code_mem[(p * WB + rsp_tag[p*TAGW +: SW]) * 4 + rsp_beat[p*BEATW +: 2]] <= rsp_data[p*DW +: DW];
            end
    // output: a 4-entry FIFO; the control decides a drain two cycles before it lands here, so it
    // drains only while at most one entry is held (this one + two in flight fit)
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
    reg [15:0]     g_kv;
    reg [16*544-1:0] g_key;
    reg [4:0]      col, bank, sb;
    reg [SW-1:0]   slot;
    always @* begin
        g_kv = 0; g_key = 0;
        for (b = 0; b < 2; b = b + 1) begin
            slot = dr_slot + SW'(b);
            sb = dr_j[7*b+2 +: 5] ^ dr_f0[5*b +: 5];
            for (k = 0; k < 8; k = k + 1) begin
                col = {dr_j[7*b +: 3], 2'b00} + 5'(k / 2);
                bank = col ^ dr_fc[5*b +: 5];
                g_kv[8*b + k] = dr_v[b];
                if (dr_v[b])
                    g_key[(8*b + k)*544 +: 544] = {scale_mem[sb * WB + slot][32*k +: 32],
                                                   code_mem[(bank * WB + slot) * 4 + 2 * (k % 2) + 1],
                                                   code_mem[(bank * WB + slot) * 4 + 2 * (k % 2)]};
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

// One stack's candidate-block gather: control + data.
module ot_hdc_v41x_idx_kgather #(
    parameter integer NPC  = 32,
    parameter integer WB   = 128,
    parameter integer AW   = 28,
    parameter integer HW   = 20,
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4,
    parameter integer DW   = 256,
    parameter integer LBW  = 14,
    parameter integer LMW  = 11,
    parameter integer DF   = 8
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 lw_v,
    input  wire [LMW-1:0]       lw_addr,
    input  wire [LBW-1:0]       lw_blk,
    input  wire                 cmd_v,
    input  wire [HW-1:0]        cmd_base,
    input  wire [9:0]           cmd_skip,
    input  wire [LMW:0]         cmd_n,
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
    input  wire [NPC*BEATW-1:0] rsp_beat,
    input  wire [NPC*DW-1:0]    rsp_data,
    output wire                 o_valid,
    input  wire                 o_ready,
    output wire [15:0]          o_kv,
    output wire [16*544-1:0]    o_key,
    output wire [2*LBW-1:0]     o_blk,
    output reg  [47:0]          cnt_keys_streamed,
    output reg  [47:0]          cnt_hbm_beats
);
    wire [1:0] dr_v;
    wire [$clog2(WB)-1:0] dr_slot;
    wire [13:0] dr_j;
    wire [9:0] dr_fc, dr_f0;
    wire [2*LBW-1:0] dr_blk;
    wire dr_ready, cbusy;
    assign busy = cbusy || o_valid;
    // candidate-list SRAM: two banks (even / odd entries), 1W1R, synchronous read
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
    ot_hdc_v41x_idx_kgctl #(.NPC(NPC), .WB(WB), .AW(AW), .HW(HW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW),
                            .LBW(LBW), .LMW(LMW), .DF(DF)) u_c (
        .clk(clk), .rst_n(rst_n), .lr_re(lr_re), .lr_addr(lr_addr), .lr_e(lr_e), .lr_o(lr_o),
        .cmd_v(cmd_v), .cmd_base(cmd_base), .cmd_skip(cmd_skip), .cmd_n(cmd_n), .busy(cbusy), .fault(fault),
        .req_v(req_v), .req_rdy(req_rdy), .req_addr(req_addr), .req_len(req_len), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat),
        .dr_v(dr_v), .dr_slot(dr_slot), .dr_j(dr_j), .dr_fc(dr_fc), .dr_f0(dr_f0), .dr_blk(dr_blk),
        .dr_ready(dr_ready));
    ot_hdc_v41x_idx_kgdata #(.NPC(NPC), .WB(WB), .TAGW(TAGW), .BEATW(BEATW), .DW(DW), .LBW(LBW)) u_d (
        .clk(clk), .rst_n(rst_n), .rsp_v(rsp_v), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat), .rsp_data(rsp_data),
        .dr_v(dr_v), .dr_slot(dr_slot), .dr_j(dr_j), .dr_fc(dr_fc), .dr_f0(dr_f0), .dr_blk(dr_blk),
        .dr_ready(dr_ready), .o_valid(o_valid), .o_ready(o_ready), .o_kv(o_kv), .o_key(o_key), .o_blk(o_blk));
endmodule
