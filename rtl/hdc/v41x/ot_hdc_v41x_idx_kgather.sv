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
// CONTROL (ot_hdc_v41x_idx_kgctl), every per-cycle decision reads registers:
//   list read (2 blocks) -> decode 1 (super-block, B0, code block) -> decode 2 (folds,
//   addresses, pseudo-channel one-hots) -> dispatch: both blocks of the pair enter the
//   per-pseudo-channel request FIFOs (one code FIFO and one scale FIFO a channel, two
//   write ports each) when every targeted FIFO has room for two and the reorder buffer
//   has two free slots; a pseudo-channel issues the older of its two FIFO heads.
//   Slot = sequence mod WB.  Per slot and channel a pending bit (code / scale) is set at
//   dispatch and cleared by the request's last beat (code beats counted: the HBM
//   scheduler reorders bursts); a slot is complete when it is dispatched and no bit is
//   pending (registered, so seen one cycle late, never early).  The drain takes the
//   head slot and the next one when complete: up to 2 blocks = 16 keys a cycle, in list
//   order (the select needs ascending positions).
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
    parameter integer DF   = 4          // request FIFO depth per channel and kind
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // candidate-list SRAM (two banks, even / odd entries), synchronous read: data of the
    // address presented with lr_re appears on lr_e / lr_o after the edge and holds
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
    input  wire                 dr_ready
);
    localparam integer SW = $clog2(WB);
    localparam integer QW = LMW + 1;
    localparam integer FW = $clog2(DF);

    function automatic [4:0] fold(input [HW-1:0] b);
        fold = b[4:0] ^ b[9:5];
    endfunction

    reg            run;
    reg [HW-1:0]   base;
    reg [6:0]      skip8;
    reg [QW-1:0]   n;
    reg [QW-1:0]   rd_seq;                  // next pair to read
    reg [QW-1:0]   a_seq;                   // next sequence to dispatch
    reg [QW-1:0]   d_seq;                   // drain head

    // -- pipeline: S1 list data, D1, D2 ------------------------------------------------------------
    reg            s1_v, d1_v, d2_v;
    reg [QW-1:0]   s1_seq, d1_seq, d2_seq;
    reg [1:0]      s1_m, d1_m, d2_m;        // lanes present (lane 0 = even sequence)
    wire [LBW-1:0] s1_blk [0:1];
    assign s1_blk[0] = lr_e;
    assign s1_blk[1] = lr_o;
    reg [LBW-1:0]  d1_blk [0:1];
    reg [6:0]      d1_j   [0:1];
    reg [HW-1:0]   d1_b0  [0:1];
    reg [HW-1:0]   d1_bc  [0:1];
    reg [LBW-1:0]  d2_blk [0:1];
    reg [6:0]      d2_j   [0:1];
    reg [4:0]      d2_fc  [0:1];
    reg [4:0]      d2_f0  [0:1];
    reg [HW-1:0]   d2_b0  [0:1];
    reg [HW-1:0]   d2_bc  [0:1];
    reg [NPC-1:0]  d2_cm  [0:1];            // code channels of the block
    reg [NPC-1:0]  d2_sm  [0:1];            // scale channel of the block

    // -- per-channel request FIFOs: kind 0 code, 1 scale -------------------------------------------
    reg [AW-1:0]   fq_addr [0:2*NPC*DF-1];
    reg [SW-1:0]   fq_slot [0:2*NPC*DF-1];
    reg [FW-1:0]   fq_rp   [0:2*NPC-1];
    reg [FW:0]     fq_n    [0:2*NPC-1];
    reg [2*NPC-1:0] room2;                  // registered: FIFO has >= 2 free entries

    // -- slot state -----------------------------------------------------------------------------------
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

    // -- dispatch decision -----------------------------------------------------------------------------
    wire [NPC-1:0] t_c = (d2_m[0] ? d2_cm[0] : {NPC{1'b0}}) | (d2_m[1] ? d2_cm[1] : {NPC{1'b0}});
    wire [NPC-1:0] t_s = (d2_m[0] ? d2_sm[0] : {NPC{1'b0}}) | (d2_m[1] ? d2_sm[1] : {NPC{1'b0}});
    wire           rob_ok = (QW'(d2_seq + 2 - d_seq) <= QW'(WB));
    wire           fifo_ok = ~|(t_c & ~room2[NPC-1:0]) && ~|(t_s & ~room2[2*NPC-1:NPC]);
    wire           disp = run && d2_v && rob_ok && fifo_ok;
    wire           d2_take = !d2_v || disp;
    wire           d1_take = !d1_v || d2_take;
    wire           s1_take = !s1_v || d1_take;
    assign lr_re = run && s1_take && !(cmd_v && !busy);
    assign lr_addr = rd_seq[LMW-1:1];

    // -- drain decision -----------------------------------------------------------------------------------
    wire [SW-1:0]  h0 = d_seq[SW-1:0];
    wire [SW-1:0]  h1 = h0 + 1'b1;
    wire           can0 = run && (d_seq < n) && cmp[h0] && dr_ready;
    wire           can1 = can0 && (QW'(d_seq + 1) < n) && cmp[h1];

    integer p, k, l, e, c, q;
    reg [SW-1:0]   rs;
    reg [FW:0]     cnt;
    reg [FW-1:0]   wp;
    reg [LBW+6:0]  lk8;

    // per channel: which FIFO head issues (the older slot relative to the drain head)
    reg [NPC-1:0]  use_s, iss;
    always @* begin
        for (q = 0; q < NPC; q = q + 1) begin
            use_s[q] = (fq_n[NPC + q] != 0) &&
                       ((fq_n[q] == 0) ||
                        (SW'(fq_slot[(NPC + q) * DF + fq_rp[NPC + q]] - h0) < SW'(fq_slot[q * DF + fq_rp[q]] - h0)));
            iss[q] = run && ((fq_n[q] != 0) || (fq_n[NPC + q] != 0)) && (!req_v[q] || req_rdy[q]);
        end
    end

    // registered responses
    reg [NPC-1:0]  rr_v;
    reg [SW-1:0]   rr_s [0:NPC-1];
    reg            rr_k [0:NPC-1];

    always @(posedge clk) begin
        if (!rst_n) begin
            run <= 1'b0; busy <= 1'b0; fault <= 1'b0; req_v <= 0; dr_v <= 0;
            s1_v <= 1'b0; d1_v <= 1'b0; d2_v <= 1'b0; adm <= 0; cmp <= 0; rr_v <= 0;
            room2 <= {2*NPC{1'b1}};
            for (p = 0; p < 2 * NPC; p = p + 1) begin fq_rp[p] <= 0; fq_n[p] <= 0; end
            for (p = 0; p < NPC * WB; p = p + 1) cntc[p] <= 2'd0;   // 4 beats wrap it back to 0
        end else begin
            dr_v <= 2'b00;
            // completion, one cycle late
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
            if (cmd_v && !busy) begin
                run <= 1'b1; busy <= 1'b1;
                base <= cmd_base; skip8 <= cmd_skip[9:3]; n <= cmd_n;
                fault <= (cmd_skip[2:0] != 3'd0);
                rd_seq <= 0; a_seq <= 0; d_seq <= 0;
                s1_v <= 1'b0; d1_v <= 1'b0; d2_v <= 1'b0;
            end else if (run) begin
                // list read -> S1
                if (s1_take) begin
                    s1_v <= (rd_seq < n);
                    s1_seq <= rd_seq;
                    s1_m <= {(QW'(rd_seq + 1) < n), 1'b1};
                    if (rd_seq < n) rd_seq <= rd_seq + 2;
                end
                // S1 -> D1: super-block, scale block, code block
                if (d1_take) begin
                    d1_v <= s1_v; d1_seq <= s1_seq; d1_m <= s1_m;
                    for (l = 0; l < 2; l = l + 1) begin
                        lk8 = {{LBW{1'b0}}, skip8} + {7'd0, s1_blk[l]};
                        d1_blk[l] <= s1_blk[l];
                        d1_j[l] <= lk8[6:0];
                        d1_b0[l] <= base + HW'(17 * (lk8 >> 7));
                        d1_bc[l] <= base + HW'(17 * (lk8 >> 7)) + 1 + HW'(lk8[6:3]);
                    end
                end
                // D1 -> D2: folds, one-hots
                if (d2_take) begin
                    d2_v <= d1_v; d2_seq <= d1_seq; d2_m <= d1_m;
                    for (l = 0; l < 2; l = l + 1) begin
                        d2_blk[l] <= d1_blk[l]; d2_j[l] <= d1_j[l];
                        d2_b0[l] <= d1_b0[l]; d2_bc[l] <= d1_bc[l];
                        d2_fc[l] <= fold(d1_bc[l]);
                        d2_f0[l] <= fold(d1_b0[l]);
                        d2_cm[l] <= 0; d2_sm[l] <= 0;
                        for (c = 0; c < 4; c = c + 1)
                            d2_cm[l][(5'({d1_j[l][2:0], 2'b00}) + 5'(c)) ^ fold(d1_bc[l])] <= 1'b1;
                        d2_sm[l][d1_j[l][6:2] ^ fold(d1_b0[l])] <= 1'b1;
                    end
                end
                // dispatch: both blocks of the pair into the channel FIFOs
                if (disp) begin
                    for (l = 0; l < 2; l = l + 1) if (d2_m[l]) begin
                        rs = SW'(d2_seq + l);
                        adm[rs] <= 1'b1;
                        pend_c[rs] <= d2_cm[l];
                        pend_s[rs] <= d2_sm[l];
                        m_j[rs] <= d2_j[l]; m_fc[rs] <= d2_fc[l]; m_f0[rs] <= d2_f0[l]; m_blk[rs] <= d2_blk[l];
                    end
                    a_seq <= d2_seq + 2;
                end
                // per-channel issue: the older of the code / scale heads
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
                // FIFO pushes / pops, counts, room
                for (p = 0; p < 2 * NPC; p = p + 1) begin
                    cnt = fq_n[p];
                    wp = FW'(fq_rp[p] + cnt[FW-1:0]);
                    if (disp) begin
                        for (l = 0; l < 2; l = l + 1)
                            if (d2_m[l] && (p < NPC ? d2_cm[l][p % NPC] : d2_sm[l][p % NPC])) begin
                                fq_slot[p * DF + wp] <= SW'(d2_seq + l);
                                // code: channel p serves column p ^ fold(Bc); scale: sector j of B0
                                fq_addr[p * DF + wp] <= (p < NPC) ? AW'({d2_bc[l], 5'(p % NPC) ^ d2_fc[l], 2'b00})
                                                                  : AW'({d2_b0[l], d2_j[l]});
                                wp = wp + 1'b1;
                                cnt = cnt + 1'b1;
                            end
                    end
                    if (p < NPC ? (iss[p % NPC] && !use_s[p % NPC]) : (iss[p % NPC] && use_s[p % NPC])) begin
                        fq_rp[p] <= fq_rp[p] + 1'b1;
                        cnt = cnt - 1'b1;
                    end
                    fq_n[p] <= cnt;
                    room2[p] <= (cnt + 2 <= DF);
                end
                // drain: head and next, in order
                if (can0) begin
                    dr_v <= {can1, 1'b1};
                    dr_slot <= h0;
                    dr_j <= {m_j[h1], m_j[h0]};
                    dr_fc <= {m_fc[h1], m_fc[h0]};
                    dr_f0 <= {m_f0[h1], m_f0[h0]};
                    dr_blk <= {m_blk[h1], m_blk[h0]};
                    adm[h0] <= 1'b0;
                    if (can1) adm[h1] <= 1'b0;
                    d_seq <= d_seq + (can1 ? 2 : 1);
                end
                if (d_seq >= n && !can0) run <= 1'b0;
            end else if (busy && dr_v == 2'b00) busy <= 1'b0;
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
    // output: register + one skid entry; the control may have a drain in flight
    reg            sk_v;
    reg [15:0]     sk_kv;
    reg [16*544-1:0] sk_key;
    reg [2*LBW-1:0] sk_blk;
    assign dr_ready = !sk_v && !(o_valid && !o_ready && dr_v != 2'b00);
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
        if (!rst_n) begin o_valid <= 1'b0; sk_v <= 1'b0; end
        else begin
            if (o_valid && o_ready) begin
                if (sk_v) begin
                    o_kv <= sk_kv; o_key <= sk_key; o_blk <= sk_blk; sk_v <= 1'b0;
                end else o_valid <= 1'b0;
            end
            if (dr_v != 2'b00) begin
                if (!o_valid || (o_ready && !sk_v)) begin
                    o_valid <= 1'b1; o_kv <= g_kv; o_key <= g_key; o_blk <= dr_blk;
                end else begin
                    sk_v <= 1'b1; sk_kv <= g_kv; sk_key <= g_key; sk_blk <= dr_blk;
                end
            end
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
    parameter integer DF   = 4
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
