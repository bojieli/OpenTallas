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
// CONTROL (ot_hdc_v41x_idx_kgctl_kc7), pipelined for 1.2 GHz (every decision reads registers):
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
//   Routed at 1.2 GHz (results/rtl/dsrom_reindex_close_20261004, 2026-10-04) the first cut failed SS by
//   89 ps on broadcast fan-out across its ~40k flops; the control now (a) loads the dispatch write stage
//   into 8 kept copies (each feeding 16 slots or 4 channels' request FIFOs), (b) writes slots through a
//   one-hot slot register, (c) registers each response's slot one-hot, (d) reads the drain's metadata
//   AND-OR through a one-hot head (16-slot partials registered with the drain decision, OR'd in the
//   second stage), (e) forms completion in two registered levels (8-channel partials, then their AND
//   with adm delayed alongside: one more cycle from last beat to completion, never early), (f) adds the
//   ring head to the list word in the stage after the SRAM register, and (g) counts request-FIFO room
//   without the cycle's pop (conservative; keeps req_rdy out of the 64-FIFO room AND).
// DATA (ot_hdc_v41x_idx_kgdata_kc7): per pseudo-channel bank WB x 4 code beats + WB scale
// sectors (behavioural here; one 1W1R SRAM bank per channel on silicon, the
// kstream_range ROB plus a WB x 256 b scale bank); the drain gathers each key's
// {scale[31:0], codes[511:0]} (the engine's key format).
// OUTPUT: valid/ready beats of up to 16 keys (lanes 0-7 block o_blk0, 8-15 block
// o_blk1; o_kv marks present keys) -- key j of block b is position quarter_base + 8 b + j.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_kgctl_kc7 #(
    parameter integer OPT_KC6 = 1,
    parameter integer OPT_KC7 = 0,
    parameter integer OPT_KC8 = 0,   // grouped registered room, replicated slot write enables
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
    localparam integer GS = 8;              // copies of the dispatch write stage
    localparam integer SG = WB / GS;        // slots fed by one slot-side copy
    localparam integer CG = NPC / GS;       // channels fed by one channel-side copy

    function automatic [4:0] fold(input [HW-1:0] b);
        fold = b[4:0] ^ b[9:5];
    endfunction
    function automatic [WB-1:0] onehot(input [SW-1:0] s);
        onehot = {{(WB-1){1'b0}}, 1'b1} << s;
    endfunction
    function automatic [WB-1:0] rotl(input [WB-1:0] v, input integer k);
        rotl = (v << k) | (v >> (WB - k));
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
    reg [LBW+6:0]  lk    [0:1];             // local key / 8 (e2 stage, combinational)
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
    // OPT_KC8: the 64-FIFO room AND is retimed: each channel group (4 code + 4 scale FIFOs, beside its
    // channel copy) registers the AND of its own 8 room bits, and the dispatch ANDs the 8 group flags.
    // room_g(t+1)[g] = &rm_g(t), so &room_g == room_all every cycle: identical dispatch, zero latency.
    reg  [7:0]     room_g;
    wire           room_ok = (OPT_KC8 != 0) ? &room_g : room_all;
    wire           disp = run && hd_v && rob_ok && room_ok;
    wire           hd_take = !hd_v || disp;
    reg            w_v;
    reg [WB-1:0]   w_oh0, w_oh1;            // the write stage's slots, one-hot (zero when nothing is written)
    // OPT_KC8: three kept copies of each one-hot (metadata / code-pending / scale-pending writes): a slot's
    // enable drove 95 mux selects (kc7: 512 post-route slew violations on those nets).  Same D as w_oh*.
    wire [WB-1:0]  w_oh0_d, w_oh1_d;
    wire [3*WB-1:0] w_oh0_c, w_oh1_c;
    // The write stage's operands, in GS kept copies (ot_hdc_v41x_kg_kreg_kc7) loaded from the head every cycle
    // (used only on w_v / a one-hot slot): slot copy g feeds slots [g SG, (g+1) SG), channel copy g the request
    // FIFOs of channels [g CG, (g+1) CG); the channel copies' masks are gated by the dispatch (zero otherwise).
    localparam integer SLW = LBW + 7 + 5 + 5 + 2 * NPC;            // blk, j, f0, fc, cm, sm
    localparam integer CHW = 2 * HW + 5 + 7 + SW + 2 * CG;         // b0, bc, fc, j, rs, cm / sm of the group
    wire [GS*2*SLW-1:0] sl_q;               // copy g, lane l at [(2 g + l) SLW +: SLW]
    wire [GS*2*CHW-1:0] ch_q;

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
    reg [WB-1:0]   adm_q;                   // adm, a cycle later (aligned with cpart)
    reg [7:0]      cpart [0:WB-1];          // nothing pending in each 8-channel group (code 0-3, scale 4-7)
    reg [WB-1:0]   cmp;                     // registered completion: adm_q && &cpart
    reg [6:0]      m_j   [0:WB-1];
    reg [4:0]      m_fc  [0:WB-1];
    reg [4:0]      m_f0  [0:WB-1];
    reg [LBW-1:0]  m_blk [0:WB-1];

    assign rsp_rdy = {NPC{1'b1}};           // every beat has its slot (allocated at dispatch)

    // -- drain: completion of head .. head+3 sampled a cycle earlier; adv_r = the step taken then ----
    reg [3:0]      rq;
    reg [1:0]      adv_r;
    reg [WB-1:0]   hoh;                     // the drain head's slot, one-hot (= d_seq mod WB)
    wire [SW-1:0]  h0 = d_seq[SW-1:0];
    wire           rq0 = (adv_r == 2'd0) ? rq[0] : (adv_r == 2'd1) ? rq[1] : rq[2];
    wire           rq1 = (adv_r == 2'd0) ? rq[1] : (adv_r == 2'd1) ? rq[2] : rq[3];
    wire           can0 = run && (d_left != 0) && rq0 && dr_ready;
    wire           can1 = can0 && (d_left > 1) && rq1;
    wire drain_eligible = run && (d_left != 0) && rq0;
    wire drain_two = (d_left > 1) && rq1;
    wire [WB-1:0] next_hoh;
    wire [WB-1:0] rotated_one = rotl(hoh, 1);
    wire [WB-1:0] rotated_two = rotl(hoh, 2);
    generate for (genvar hs=0; hs<GS; hs=hs+1) begin : g_head_local
        ot_dsrom_kc7_ready_last #(.W(SG)) u_select (
            .eligible(drain_eligible), .two(drain_two), .ready(dr_ready),
            .old_head(hoh[hs*SG +: SG]), .one_head(rotated_one[hs*SG +: SG]),
            .two_head(rotated_two[hs*SG +: SG]), .next_head(next_hoh[hs*SG +: SG]));
    end endgenerate
    // All arithmetic and rob comparisons are independent of actual ready.
    wire [QW-1:0] seq_one = d_seq + QW'(1), seq_two = d_seq + QW'(2);
    wire [QW-1:0] left_one = d_left - QW'(1), left_two = d_left - QW'(2);
    wire [QW-1:0] use_base = inuse + (disp ? QW'(2) : QW'(0));
    wire [QW-1:0] use_one = use_base - QW'(1), use_two = use_base - QW'(2);
    wire [QW-1:0] next_seq, next_left, next_use;
    wire next_rob_ok;
    generate for (genvar ds=0; ds<QW; ds=ds+4) begin : g_drain_ready_last
        localparam integer W = (QW-ds < 4) ? QW-ds : 4;
        ot_dsrom_kc7_ready_last #(.W(W)) u_seq (
            .eligible(drain_eligible), .two(drain_two), .ready(dr_ready),
            .old_head(d_seq[ds+:W]), .one_head(seq_one[ds+:W]),
            .two_head(seq_two[ds+:W]), .next_head(next_seq[ds+:W]));
        ot_dsrom_kc7_ready_last #(.W(W)) u_left (
            .eligible(drain_eligible), .two(drain_two), .ready(dr_ready),
            .old_head(d_left[ds+:W]), .one_head(left_one[ds+:W]),
            .two_head(left_two[ds+:W]), .next_head(next_left[ds+:W]));
        ot_dsrom_kc7_ready_last #(.W(W)) u_use (
            .eligible(drain_eligible), .two(drain_two), .ready(dr_ready),
            .old_head(use_base[ds+:W]), .one_head(use_one[ds+:W]),
            .two_head(use_two[ds+:W]), .next_head(next_use[ds+:W]));
    end endgenerate
    ot_dsrom_kc7_ready_last #(.W(1)) u_rob (
        .eligible(drain_eligible), .two(drain_two), .ready(dr_ready),
        .old_head(use_base <= QW'(WB-4)), .one_head(use_one <= QW'(WB-4)),
        .two_head(use_two <= QW'(WB-4)), .next_head(next_rob_ok));
    reg            dq_v; reg [1:0] dq_m; reg [SW-1:0] dq_slot;    // drain decided: read metadata next
    reg [WB-1:0]   dq_oh;

    assign w_oh0_d = (rst_n && !(cmd_v && !busy) && run && disp && hd_m[0]) ? onehot(hd_seq[SW-1:0]) : {WB{1'b0}};
    assign w_oh1_d = (rst_n && !(cmd_v && !busy) && run && disp && hd_m[1]) ? onehot(hd_s1) : {WB{1'b0}};
    generate for (genvar wc = 0; wc < 3; wc = wc + 1) begin : g_woh
        if (OPT_KC8 != 0) begin : g_on
            ot_hdc_v41x_kg_kreg_kc7 #(.W(WB)) u_w0 (.clk(clk), .d(w_oh0_d), .q(w_oh0_c[wc*WB +: WB]));
            ot_hdc_v41x_kg_kreg_kc7 #(.W(WB)) u_w1 (.clk(clk), .d(w_oh1_d), .q(w_oh1_c[wc*WB +: WB]));
        end else begin : g_off
            assign w_oh0_c[wc*WB +: WB] = w_oh0;
            assign w_oh1_c[wc*WB +: WB] = w_oh1;
        end
    end endgenerate

    // per channel issue: the scale head first, else the code head
    reg [NPC-1:0]  iss, use_s;
    integer q;
    always @* begin
        for (q = 0; q < NPC; q = q + 1) begin
            use_s[q] = (fq_n[NPC + q] != 0);
            iss[q] = run && ((fq_n[q] != 0) || use_s[q]) && (!req_v[q] || req_rdy[q]);
        end
    end

    // -- the write-stage copies ------------------------------------------------------------------------
    genvar gg, gl;
    generate for (gg = 0; gg < GS; gg = gg + 1) begin : g_cp
        for (gl = 0; gl < 2; gl = gl + 1) begin : g_l
            wire [SW-1:0] rs = gl ? hd_s1 : hd_seq[SW-1:0];
            wire [CG-1:0] cmg = disp ? hd_cm[gl][gg*CG +: CG] : {CG{1'b0}};
            wire [CG-1:0] smg = disp ? hd_sm[gl][gg*CG +: CG] : {CG{1'b0}};
            ot_hdc_v41x_kg_kreg_kc7 #(.W(SLW)) u_s (.clk(clk), .d({hd_blk[gl], hd_j[gl], hd_f0[gl], hd_fc[gl],
                                                               hd_cm[gl], hd_sm[gl]}), .q(sl_q[(2*gg+gl)*SLW +: SLW]));
            ot_hdc_v41x_kg_kreg_kc7 #(.W(CHW)) u_c (.clk(clk), .d({hd_b0[gl], hd_bc[gl], hd_fc[gl], hd_j[gl], rs,
                                                               cmg, smg}), .q(ch_q[(2*gg+gl)*CHW +: CHW]));
        end
    end endgenerate

    integer p, l, e, c, k, g;
    reg [FW:0]     cnt;
    reg [FW-1:0]   wp;
    reg [NPC-1:0]  t;
    reg [2*NPC-1:0] rm;
    wire [FW:0] fq_nm1 [0:2*NPC-1];
    wire [FW:0] fq_np1 [0:2*NPC-1];
    wire [FW:0] fq_np2 [0:2*NPC-1];
    generate for (genvar fp = 0; fp < 2*NPC; fp = fp+1) begin : g_count_alternatives
        // Fixed-width modular arithmetic, before the ready-dependent pop.
        assign fq_nm1[fp] = fq_n[fp] - 1'b1;
        assign fq_np1[fp] = fq_n[fp] + 1'b1;
        assign fq_np2[fp] = fq_n[fp] + 2'd2;
    end endgenerate
    reg push_a, push_b, pop_now;
    reg [QW-1:0]   nu;
    reg            b0, b1;
    reg [HW-1:0]   cb0, cbc;
    reg [4:0]      cfc;
    reg [6:0]      cj;
    reg [SW-1:0]   crs;
    reg [SW-1:0]   x_rs [0:1];
    reg [AW-1:0]   x_ad [0:1];

    // registered responses: one-hot slot (zero when no beat), kind
    reg [WB-1:0]   rr_oh [0:NPC-1];
    reg [NPC-1:0]  rr_k;

    // ---- control (synchronously reset) ----------------------------------------------------------------
    always @(posedge clk) begin
        if (!rst_n) begin
            run <= 1'b0; busy <= 1'b0; fault <= 1'b0; req_v <= 0; dr_v <= 0; dq_v <= 1'b0;
            c0_v <= 1'b0; e1_v <= 1'b0; e2_v <= 1'b0; e3_v <= 1'b0; e4_v <= 1'b0; e5_v <= 1'b0;
            hd_v <= 1'b0; w_v <= 1'b0; w_oh0 <= 0; w_oh1 <= 0; pf_n <= 0; pf_wp <= 0; pf_rp <= 0; occ <= 0;
            adm <= 0; adm_q <= 0; cmp <= 0; rq <= 0; adv_r <= 0; hoh <= {{(WB-1){1'b0}}, 1'b1};
            room_all <= 1'b1; room_g <= 8'hff; rob_ok <= 1'b1; inuse <= 0;
            for (p = 0; p < NPC; p = p + 1) rr_oh[p] <= 0;
            for (p = 0; p < 2 * NPC; p = p + 1) begin fq_rp[p] <= 0; fq_wp[p] <= 0; fq_n[p] <= 0; end
            for (p = 0; p < NPC * WB; p = p + 1) cntc[p] <= 2'd0;   // 4 beats wrap it back to 0
        end else begin
            // completion, two cycles late: per-group partials, then their AND (never early: adm_q is
            // registered alongside the partials)
            adm_q <= adm;
            for (e = 0; e < WB; e = e + 1) begin
                if (!OPT_KC6)
                    for (k = 0; k < 4; k = k + 1) begin
                        cpart[e][k]     <= ~|pend_c[e][8*k +: 8];
                        cpart[e][4 + k] <= ~|pend_s[e][8*k +: 8];
                    end
                cmp[e] <= adm_q[e] && &cpart[e];
            end
            // responses: registered (one-hot slot), then counted
            for (p = 0; p < NPC; p = p + 1) begin
                rr_oh[p] <= rsp_v[p] ? onehot(rsp_tag[p*TAGW +: SW]) : {WB{1'b0}};
                rr_k[p] <= rsp_tag[p*TAGW + SW];
                if (!rr_k[p])
                    for (e = 0; e < WB; e = e + 1)
                        if (rr_oh[p][e]) cntc[p * WB + e] <= cntc[p * WB + e] + 2'd1;
            end
            // dispatch write stage (decided last cycle): admitted slots
            adm <= adm | w_oh0 | w_oh1;
            // drain stage 2: retire the slots (after the dispatch write, as before)
            dr_v <= 2'b00;
            if (dq_v) begin
                adm <= (adm | w_oh0 | w_oh1) & ~(dq_oh | (dq_m[1] ? rotl(dq_oh, 1) : {WB{1'b0}}));
                dr_v <= dq_m;
                dr_slot <= dq_slot;
            end
            w_oh0 <= 0; w_oh1 <= 0;
            if (cmd_v && !busy) begin
                run <= 1'b1; busy <= 1'b1;
                base <= cmd_base; skip8 <= cmd_skip[9:3]; n <= cmd_n;
                fault <= (cmd_skip[2:0] != 3'd0);
                rd_seq <= 0; d_seq <= 0; d_left <= cmd_n; occ <= 0; inuse <= 0; rob_ok <= 1'b1;
                hoh <= {{(WB-1){1'b0}}, 1'b1};
                c0_v <= 1'b0; e1_v <= 1'b0; e2_v <= 1'b0; e3_v <= 1'b0; e4_v <= 1'b0; e5_v <= 1'b0;
                hd_v <= 1'b0; w_v <= 1'b0; pf_n <= 0; pf_wp <= 0; pf_rp <= 0; rq <= 0; adv_r <= 0; dq_v <= 1'b0;
            end else if (run) begin
                // list read (SRAM output valid next cycle)
                c0_v <= rd_go; c0_m <= {(QW'(rd_seq + 1) < n), 1'b1};
                if (rd_go) rd_seq <= rd_seq + 2;
                occ <= occ + (rd_go ? 5'd1 : 5'd0) - (disp ? 5'd1 : 5'd0);
                e1_v <= c0_v; e2_v <= e1_v; e3_v <= e2_v; e4_v <= e3_v; e5_v <= e4_v;
                if (e5_v) pf_wp <= pf_wp + 1'b1;
                if (hd_take) begin
                    hd_v <= (pf_n != 0);
                    if (pf_n != 0) pf_rp <= pf_rp + 1'b1;
                end
                pf_n <= pf_n + (e5_v ? 1'b1 : 1'b0) - ((hd_take && pf_n != 0) ? 1'b1 : 1'b0);
                // dispatch decision -> write stage
                w_v <= disp;
                w_oh0 <= (disp && hd_m[0]) ? onehot(hd_seq[SW-1:0]) : {WB{1'b0}};
                w_oh1 <= (disp && hd_m[1]) ? onehot(hd_s1) : {WB{1'b0}};
                // per-channel issue
                for (p = 0; p < NPC; p = p + 1) begin
                    if (req_v[p] && req_rdy[p]) req_v[p] <= 1'b0;
                    if (iss[p]) req_v[p] <= 1'b1;
                end
                // FIFO pushes (from the write stage; masks zero unless written) / pops, counts, room
                for (p = 0; p < 2 * NPC; p = p + 1) begin
                    g = (p % NPC) / CG;
                    c = (p % NPC) % CG;
                    cnt = fq_n[p];
                    wp = fq_wp[p];
                    for (l = 0; l < 2; l = l + 1)
                        if (ch_q[(2*g+l)*CHW + (p < NPC ? CG : 0) + c]) begin
                            wp = wp + 1'b1;
                            cnt = cnt + 1'b1;
                        end
                    fq_wp[p] <= wp;
                    // room counts the pushes but not this cycle's pop (conservative: keeps the request
                    // port's req_rdy out of the 64-FIFO room AND)
                    rm[p] = (cnt + 4 <= DF);
                    if (p < NPC ? (iss[p % NPC] && !use_s[p % NPC]) : (iss[p % NPC] && use_s[p % NPC])) begin
                        fq_rp[p] <= fq_rp[p] + 1'b1;
                        cnt = cnt - 1'b1;
                    end
                    if (OPT_KC6) begin
                        push_a = ch_q[(2*g+0)*CHW + (p < NPC ? CG : 0) + c];
                        push_b = ch_q[(2*g+1)*CHW + (p < NPC ? CG : 0) + c];
                        pop_now = p < NPC ? (iss[p % NPC] && !use_s[p % NPC])
                                          : (iss[p % NPC] && use_s[p % NPC]);
                        // Late pop selects precomputed counts; rm above still
                        // sees pushed count BEFORE pop, exactly as the donor.
                        case ({push_a, push_b})
                            2'b00: fq_n[p] <= pop_now ? fq_nm1[p] : fq_n[p];
                            2'b11: fq_n[p] <= pop_now ? fq_np1[p] : fq_np2[p];
                            default: fq_n[p] <= pop_now ? fq_n[p] : fq_np1[p];
                        endcase
                    end else fq_n[p] <= cnt;
                end
                room_all <= &rm;
                for (g = 0; g < GS; g = g + 1)
                    room_g[g] <= &{rm[NPC + g*CG +: CG], rm[g*CG +: CG]};
                // drain stage 1: head and next, in order
                for (k = 0; k < 4; k = k + 1) rq[k] <= |(cmp & rotl(hoh, k));
                adv_r <= can1 ? 2'd2 : (can0 ? 2'd1 : 2'd0);
                dq_v <= can0;
                dq_m <= {can1, 1'b1};
                dq_slot <= h0;
                dq_oh <= hoh;
                if (OPT_KC7) begin
                    d_seq <= next_seq;
                    d_left <= next_left;
                end else if (can0) begin
                    d_seq <= d_seq + (can1 ? 2 : 1);
                    d_left <= d_left - (can1 ? 2 : 1);
                end
                if (can0 && !OPT_KC6) hoh <= can1 ? rotl(hoh, 2) : rotl(hoh, 1);
                if (OPT_KC6) hoh <= next_hoh;
                nu = inuse + (disp ? QW'(2) : QW'(0)) - (can1 ? QW'(2) : (can0 ? QW'(1) : QW'(0)));
                inuse <= OPT_KC7 ? next_use : nu;
                rob_ok <= OPT_KC7 ? next_rob_ok : (nu <= QW'(WB - 4));
                if (d_left == 0 && !dq_v) run <= 1'b0;
            end else if (busy && dr_v == 2'b00 && !dq_v) busy <= 1'b0;
        end
    end

    localparam integer RQPW = AW + LENW + TAGW;
    wire [NPC*RQPW-1:0] next_payload;
    generate for (genvar pp=0; pp<NPC; pp=pp+1) begin : g_payload_ready_last
        wire [RQPW-1:0] code_payload = {fq_addr[pp*DF+fq_rp[pp]],
            LENW'(4), TAGW'({1'b0, fq_slot[pp*DF+fq_rp[pp]]})};
        wire [RQPW-1:0] scale_payload = {fq_addr[(NPC+pp)*DF+fq_rp[NPC+pp]],
            LENW'(1), TAGW'({1'b1, fq_slot[(NPC+pp)*DF+fq_rp[NPC+pp]]})};
        wire [RQPW-1:0] old_payload = {req_addr[pp*AW+:AW],
            req_len[pp*LENW+:LENW], req_tag[pp*TAGW+:TAGW]};
        for (genvar ps=0; ps<RQPW; ps=ps+8) begin : g_slice
            localparam integer W = (RQPW-ps < 8) ? RQPW-ps : 8;
            ot_dsrom_kc7_payload_last #(.W(W)) u_select (
                .eligible(run && ((fq_n[pp] != 0) || use_s[pp])),
                .scale(use_s[pp]), .valid(req_v[pp]), .ready(req_rdy[pp]),
                .old_data(old_payload[ps+:W]), .code_data(code_payload[ps+:W]),
                .scale_data(scale_payload[ps+:W]), .next_data(next_payload[pp*RQPW+ps+:W]));
        end
    end endgenerate
    // ---- data (no reset: every word is written before it is read) ---------------------------------------
    integer p2, l2, e2, c2, g2;
    reg [6:0]      aj [0:1];
    reg [4:0]      afc [0:1], af0 [0:1];
    reg [LBW-1:0]  ablk [0:1];
    localparam integer MDW = 7 + 5 + 5 + LBW;
    reg [MDW-1:0]  mp;
    reg [MDW-1:0]  dpart [0:2*GS-1];
    always @(posedge clk) begin
        // Derived partials have no reset value; adm_q/cmp still reset-clear.
        // NBA reads the same pre-edge pending state as the donor.
        if (OPT_KC6)
            for (e2 = 0; e2 < WB; e2 = e2 + 1)
                for (c2 = 0; c2 < 4; c2 = c2 + 1) begin
                    cpart[e2][c2] <= ~|pend_c[e2][8*c2 +: 8];
                    cpart[e2][4+c2] <= ~|pend_s[e2][8*c2 +: 8];
                end
        // decode pipe
        c0_seq <= rd_seq;
        e1_seq <= c0_seq; e2_seq <= e1_seq; e3_seq <= e2_seq; e4_seq <= e3_seq; e5_seq <= e4_seq;
        e1_m <= c0_m; e2_m <= e1_m; e3_m <= e2_m; e4_m <= e3_m; e5_m <= e4_m;
        for (l2 = 0; l2 < 2; l2 = l2 + 1) begin
            e1_blk[l2] <= l2 ? lr_o : lr_e;
            lk[l2] = {{LBW{1'b0}}, skip8} + {7'd0, e1_blk[l2]};
            e2_blk[l2] <= e1_blk[l2]; e2_j[l2] <= lk[l2][6:0];
            e2_m17[l2] <= {lk[l2][LBW+6:7], 4'd0} + {4'd0, lk[l2][LBW+6:7]};
            e3_blk[l2] <= e2_blk[l2]; e3_j[l2] <= e2_j[l2];
            e3_o0[l2] <= HW'(e2_m17[l2]);
            e3_oc[l2] <= HW'(e2_m17[l2]) + HW'(1) + HW'(e2_j[l2][6:3]);
            e4_blk[l2] <= e3_blk[l2]; e4_j[l2] <= e3_j[l2];
            e4_b0[l2] <= base + e3_o0[l2];
            e4_bc[l2] <= base + e3_oc[l2];
            e5_blk[l2] <= e4_blk[l2]; e5_j[l2] <= e4_j[l2]; e5_b0[l2] <= e4_b0[l2]; e5_bc[l2] <= e4_bc[l2];
            e5_f0[l2] <= fold(e4_b0[l2]); e5_fc[l2] <= fold(e4_bc[l2]);
            t = 0;
            for (c2 = 0; c2 < 4; c2 = c2 + 1) t[(5'({e4_j[l2][2:0], 2'b00}) + 5'(c2)) ^ fold(e4_bc[l2])] = 1'b1;
            e5_cm[l2] <= t;
            t = 0;
            t[e4_j[l2][6:2] ^ fold(e4_b0[l2])] = 1'b1;
            e5_sm[l2] <= t;
        end
        // pair FIFO: push from the pipe, pop into the head register
        if (run && e5_v) begin
            pf_seq[pf_wp] <= e5_seq; pf_m[pf_wp] <= e5_m;
            for (l2 = 0; l2 < 2; l2 = l2 + 1) begin
                pf_blk[2*pf_wp+l2] <= e5_blk[l2]; pf_j[2*pf_wp+l2] <= e5_j[l2];
                pf_f0[2*pf_wp+l2] <= e5_f0[l2]; pf_fc[2*pf_wp+l2] <= e5_fc[l2];
                pf_b0[2*pf_wp+l2] <= e5_b0[l2]; pf_bc[2*pf_wp+l2] <= e5_bc[l2];
                pf_cm[2*pf_wp+l2] <= e5_m[l2] ? e5_cm[l2] : {NPC{1'b0}};
                pf_sm[2*pf_wp+l2] <= e5_m[l2] ? e5_sm[l2] : {NPC{1'b0}};
            end
        end
        if (run && hd_take && pf_n != 0) begin
            hd_seq <= pf_seq[pf_rp]; hd_m <= pf_m[pf_rp]; hd_s1 <= SW'(pf_seq[pf_rp]) + 1'b1;
            for (l2 = 0; l2 < 2; l2 = l2 + 1) begin
                hd_blk[l2] <= pf_blk[2*pf_rp+l2]; hd_j[l2] <= pf_j[2*pf_rp+l2];
                hd_f0[l2] <= pf_f0[2*pf_rp+l2]; hd_fc[l2] <= pf_fc[2*pf_rp+l2];
                hd_b0[l2] <= pf_b0[2*pf_rp+l2]; hd_bc[l2] <= pf_bc[2*pf_rp+l2];
                hd_cm[l2] <= pf_cm[2*pf_rp+l2]; hd_sm[l2] <= pf_sm[2*pf_rp+l2];
            end
        end
        // responses clear pending bits; the dispatch write (one-hot slots, slot copies) then sets them
        for (p2 = 0; p2 < NPC; p2 = p2 + 1)
            for (e2 = 0; e2 < WB; e2 = e2 + 1)
                if (rr_oh[p2][e2]) begin
                    if (rr_k[p2]) pend_s[e2][p2] <= 1'b0;
                    else if (cntc[p2 * WB + e2] == 2'd3) pend_c[e2][p2] <= 1'b0;
                end
        for (e2 = 0; e2 < WB; e2 = e2 + 1)
            for (l2 = 0; l2 < 2; l2 = l2 + 1)
                begin
                    if (l2 ? w_oh1_c[e2] : w_oh0_c[e2])
                        {m_blk[e2], m_j[e2], m_f0[e2], m_fc[e2]} <= sl_q[(2*(e2/SG)+l2)*SLW + 2*NPC +: SLW - 2*NPC];
                    if (l2 ? w_oh1_c[WB + e2] : w_oh0_c[WB + e2])
                        pend_c[e2] <= sl_q[(2*(e2/SG)+l2)*SLW + NPC +: NPC];
                    if (l2 ? w_oh1_c[2*WB + e2] : w_oh0_c[2*WB + e2])
                        pend_s[e2] <= sl_q[(2*(e2/SG)+l2)*SLW +: NPC];
                end
        // request FIFO entries (lane 0 at the write pointer, lane 1 after it)
        for (p2 = 0; p2 < 2 * NPC; p2 = p2 + 1) begin
            g2 = (p2 % NPC) / CG;
            c2 = (p2 % NPC) % CG;
            b0 = ch_q[(2*g2+0)*CHW + (p2 < NPC ? CG : 0) + c2];
            b1 = ch_q[(2*g2+1)*CHW + (p2 < NPC ? CG : 0) + c2];
            for (l2 = 0; l2 < 2; l2 = l2 + 1) begin
                {cb0, cbc, cfc, cj, crs} = ch_q[(2*g2+l2)*CHW + 2*CG +: CHW - 2*CG];
                x_rs[l2] = crs;
                // code: channel p serves column p ^ fold(Bc); scale: sector j of B0
                x_ad[l2] = (p2 < NPC) ? AW'({cbc, 5'(p2 % NPC) ^ cfc, 2'b00}) : AW'({cb0, cj});
            end
            if (b0) begin fq_slot[p2 * DF + fq_wp[p2]] <= x_rs[0]; fq_addr[p2 * DF + fq_wp[p2]] <= x_ad[0]; end
            if (b1) begin
                fq_slot[p2 * DF + FW'(fq_wp[p2] + (b0 ? 1 : 0))] <= x_rs[1];
                fq_addr[p2 * DF + FW'(fq_wp[p2] + (b0 ? 1 : 0))] <= x_ad[1];
            end
        end
        // per-channel issue data
        for (p2 = 0; p2 < NPC; p2 = p2 + 1)
            if (OPT_KC7) begin
                {req_addr[p2*AW+:AW], req_len[p2*LENW+:LENW], req_tag[p2*TAGW+:TAGW]}
                    <= next_payload[p2*RQPW+:RQPW];
            end else if (iss[p2]) begin
                if (use_s[p2]) begin
                    req_addr[p2*AW +: AW] <= fq_addr[(NPC + p2) * DF + fq_rp[NPC + p2]];
                    req_len[p2*LENW +: LENW] <= LENW'(1);
                    req_tag[p2*TAGW +: TAGW] <= TAGW'({1'b1, fq_slot[(NPC + p2) * DF + fq_rp[NPC + p2]]});
                end else begin
                    req_addr[p2*AW +: AW] <= fq_addr[p2 * DF + fq_rp[p2]];
                    req_len[p2*LENW +: LENW] <= LENW'(4);
                    req_tag[p2*TAGW +: TAGW] <= TAGW'({1'b0, fq_slot[p2 * DF + fq_rp[p2]]});
                end
            end
        // drain metadata: stage 1 registers per-16-slot partial AND-OR reads of the head and next slot
        // (both admitted and complete when taken, so their metadata cannot change before stage 2);
        // stage 2 ORs the GS partials
        for (g2 = 0; g2 < GS; g2 = g2 + 1)
            for (l2 = 0; l2 < 2; l2 = l2 + 1) begin
                mp = 0;
                for (e2 = g2 * SG; e2 < (g2 + 1) * SG; e2 = e2 + 1)
                    mp = mp | ({m_j[e2], m_fc[e2], m_f0[e2], m_blk[e2]} & {MDW{hoh[(e2 + WB - l2) % WB]}});
                dpart[2*g2+l2] <= mp;
            end
        for (l2 = 0; l2 < 2; l2 = l2 + 1) begin
            mp = 0;
            for (g2 = 0; g2 < GS; g2 = g2 + 1) mp = mp | dpart[2*g2+l2];
            {aj[l2], afc[l2], af0[l2], ablk[l2]} = mp;
        end
        if (dq_v) begin
            dr_j <= {aj[1], aj[0]}; dr_fc <= {afc[1], afc[0]}; dr_f0 <= {af0[1], af0[0]};
            dr_blk <= {ablk[1], ablk[0]};
        end
    end
endmodule

// A W-bit register that synthesis keeps as its own instance: Yosys opt_merge merges flip-flops with identical
// inputs even under (* keep *), which would fold the write-stage copies back into one high-fanout register
// (same reasoning as rtl/v41rom/ot_v41_kreg.sv).
(* keep_hierarchy *)
module ot_hdc_v41x_kg_kreg_kc7 #(parameter integer W = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    always @(posedge clk) q <= d;
endmodule

// Reorder storage and the drain gather (behavioural banks; SRAM on silicon).
module ot_hdc_v41x_idx_kgdata_kc7 #(
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
module ot_hdc_v41x_idx_kgather_kc7 #(
    parameter integer OPT_KC6 = 1,
    parameter integer OPT_KC7 = 0,
    parameter integer OPT_KC8 = 0,   // grouped registered room, replicated slot write enables
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
    ot_hdc_v41x_idx_kgctl_kc7 #(.OPT_KC6(OPT_KC6), .OPT_KC7(OPT_KC7), .OPT_KC8(OPT_KC8), .NPC(NPC), .WB(WB), .AW(AW), .HW(HW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW),
                            .LBW(LBW), .LMW(LMW), .DF(DF)) u_c (
        .clk(clk), .rst_n(rst_n), .lr_re(lr_re), .lr_addr(lr_addr), .lr_e(lr_e), .lr_o(lr_o),
        .cmd_v(cmd_v), .cmd_base(cmd_base), .cmd_skip(cmd_skip), .cmd_n(cmd_n), .busy(cbusy), .fault(fault),
        .req_v(req_v), .req_rdy(req_rdy), .req_addr(req_addr), .req_len(req_len), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat),
        .dr_v(dr_v), .dr_slot(dr_slot), .dr_j(dr_j), .dr_fc(dr_fc), .dr_f0(dr_f0), .dr_blk(dr_blk),
        .dr_ready(dr_ready));
    ot_hdc_v41x_idx_kgdata_kc7 #(.NPC(NPC), .WB(WB), .TAGW(TAGW), .BEATW(BEATW), .DW(DW), .LBW(LBW)) u_d (
        .clk(clk), .rst_n(rst_n), .rsp_v(rsp_v), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat), .rsp_data(rsp_data),
        .dr_v(dr_v), .dr_slot(dr_slot), .dr_j(dr_j), .dr_fc(dr_fc), .dr_f0(dr_f0), .dr_blk(dr_blk),
        .dr_ready(dr_ready), .o_valid(o_valid), .o_ready(o_ready), .o_kv(o_kv), .o_key(o_key), .o_blk(o_blk));
endmodule

// Preserve local combinational selection boundaries, not duplicated state.
// Keep the actual ready as the last mux input; no sampled-ready substitution.
(* keep_hierarchy = "yes" *)
module ot_dsrom_kc7_ready_last #(parameter integer W=16) (
    input wire eligible, two, ready,
    input wire [W-1:0] old_head, one_head, two_head,
    output wire [W-1:0] next_head
);
    (* keep = 1 *) wire [W-1:0] eligible_head = eligible ? (two ? two_head : one_head) : old_head;
    assign next_head = ready ? eligible_head : old_head;
endmodule

// Combinational partition only: no ready sample, state, or protocol edge.
(* keep_hierarchy = "yes" *)
module ot_dsrom_kc7_payload_last #(parameter integer W=8) (
    input wire eligible, scale, valid, ready,
    input wire [W-1:0] old_data, code_data, scale_data,
    output wire [W-1:0] next_data
);
    (* keep = 1 *) wire [W-1:0] selected = scale ? scale_data : code_data;
    (* keep = 1 *) wire [W-1:0] available = eligible ? selected : old_data;
    assign next_data = (ready || !valid) ? available : old_data;
endmodule
