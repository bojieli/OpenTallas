`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen3-8B ROM TP8, track B (ONE die type: the KV die is merged into the ROM die), 2026-10-13: the merged-die KV
// sequencer (die master qkd_seq).
//
// On the two-die design the ROM end (ot_qkvd_rom_end: x3 / dc buffers, class split, ar / dh credit senders) and the KV
// sequencer (ot_qkvd_kv_seq) talked through two ot_qkvd_d2d adapters and the UCIe pair, and the ROM sequencer's dc / dh
// words were 528-b CTL / HCTL words that NO ROM-side RTL produced: the ROM sequencer (ot_qfd_seq_su_bi, slot cell
// qfd_seq_su) has only the raw stage-step pins.  On the merged die the D2D pair is a wire
// (tools/qwen_rom_fulldie_b3r2.py KV_DROP / KV_SHORT), so this block ends every ROM-side face itself: the existing
// sequencer + the ROM-end x3 buffer WITHOUT the adapters + the die's stage stepper (ot_qfd_dctl) on the raw pins.
//
// ROM-side faces (no same-cycle ready anywhere; a face with a bit against the flow has valid + credit):
//   x3    {v, tag 11, d 512} in, x3_cr out (su64).  tag[10:8] class: 001 Q (tag[5:0] beat), 010 KVN (tag[2:0]
//         {v, g, half}); any other class is a sticky fault.  ONE credit pool of XS = 40 words = one layer (8 KVN + 32 Q,
//         any order inside the layer): the words split on arrival into the Q FIFO (depth XS) and the KVN FIFO (depth
//         8), a credit returns per word the sequencer takes.  With layer-ordered traffic neither FIFO can overflow.
//   sd    56 b in, levels (qfd_seq_su dc[55:0], LSB first): seq_nval 32, seq_ntok 18, s_done, s_fault, core_fault,
//         coll_busy, kv_write_flush, rom_fault.
//   ds    187 b out (qfd_seq_su dh[186:0], LSB first): tp_pos 18, tp_token 18, stage_in 6, h_start, kv_write_drained,
//         {pw_data 64, pw_addr 10, pw_v}, {dw_data 64, dw_addr 3, dw_v}.  The stage stepper drives h_start / stage /
//         token / position (NS = 38 stages a step: E, L0..L35, H) and waits for s_done (armed) per stage, takes
//         seq_ntok / seq_nval at H, then waits for kv_write_drained (ot_qfd_dctl, unchanged; its fault code 3 is
//         rom_fault here).  kv_write_drained = no layer launched or waiting, every posted row's credit back from all
//         four landing write queues.
//   kvd   {kvd_v, kvd_kindk, kvd_pos 18, kvd_wbase 24} in (posted; qfd_seq_su kvd[200], [18], [17:0], [199:176]).  A
//         score descriptor (kindk = 1) LAUNCHES the layer's attention step: T = pos + 1, layer = wbase[11:6] (K of
//         layer l is block l of 64 words: rtl/qwen_sys/ot_qwen_sys_kv_svc.sv kvd_blk).  The weighted-sum descriptor
//         (kindk = 0) of the same position launches nothing (the near-HBM attention does both passes); one for another
//         position is a fault.  At most 2 launches wait (a third is a fault).
//   ar    {v, d 519} out, ar_cr in: RES words {g, beat, 16 FP32} to the VM.  The attention hub has no ready, so a
//         layer starts only with all 64 of its RES credits in hand (OCR_AR = 64 = the VM's promise): no RES buffer.
//   pw    {v, addr 10, data 64} out (posted): the host's program write to the ROM control tile (tt_ctlm pw_*); the
//         same write leaves on ds for the ROM sequencer's program copy.
// Host side (levels and posted pulses: the ot_qfd_pkgctl <-> ot_qfd_dctl contract, a step is named by its generation):
//   hc    182 b in, LSB first: d_pos 18, d_token 18, d_gen 2, d_start, {pw_data 64, pw_addr 10, pw_v},
//         {dw_data 64, dw_addr 3, dw_v}
//   tk    93 b out, LSB first: d_cycles 32, d_next_val 32, d_next_token 18, kv_write_flush, coll_busy, d_fault_code 4,
//         d_fault, d_drained, d_done_gen 2, d_done
// KV side: as ot_qkvd_kv_seq (attention start / T / layer / q beats, RES in, posted KV rows, stream commands), with
// FOUR registered copies of aq / kvn / kc (one per quadrant) and a CREDIT JOIN for the posted rows: each of the four
// landing write queues returns one credit per row; the sequencer's row credit returns when all four did.
// Gone on the merged die (no producer / consumer: contract v4 has no qkd_d2d / qfd_d2d_rom slot): the D2D faces c_* /
// u_* (slot rf / tf), d2d_fault / d2d_cause (slot d2df), the link-end fault word to the ROM sequencer (slot t_flt: the
// ROM sequencer has no such input), the CTL / HCTL word classes (dc / dh words, CSR responses) and the embedding
// classes EMBQ / EMBD (slot gq / gr): the SU's embedding face ends on the gateway (KV_SHORT emb / emb_a / emb_cr ->
// qkd_embgw t_eq / r_ea / t_ecr).
//
// Structure (the hardened leaves of the qkd_seq cluster, rtl/physical/ot_qwen_kv_centre_slots.sv, are these bodies):
//   ot_qkvd_seq_m_ctl    control: stage stepper, tag FIFOs, launcher, RES path, write relay, credit join
//   ot_qkvd_seq_m_store  x3 data storage (Q FIFO, KVN FIFO, the 8 KVN words), DW bits wide (cluster: 4 x 128)
//   ot_qkvd_seq_m_fan    one quadrant's pin registers (aq, kvn, kc out; credit and faults back)
// HEADS=1 is an opt-in TP8 receiver profile: 4 KVN tags 0,1,4,5, 32 native FP32 Q words (Q_FP32=1),
// 2 posted rows (vg=00/10), 32 FP32 RES words. The unchanged two-group attention
// leaves must be adapted separately; this profile alone is transport/control proof.
// No FP32-to-BF16 rounding is performed here.
// Latency against ot_qkvd_kv_seq: aq / kvn words + 4 cycles (control out, store in, store out, fan in, fan out),
// kc + 2, credits and faults back + 2.  Every hop is register -> wire -> register.
// MUT (bench only): 2 Q beats 0 / 1 swapped, 3 launcher layer + 1, 4 credit join = OR, 5 the ROM sequencer's copy of a
// program write lands one address up.
// ---------------------------------------------------------------------------------------------------------------------

// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_seq_m_ctl #(
    parameter integer Q_FP32 = 0,                 // explicit transport precision; no conversion
    parameter integer HEADS  = 2,                 // historical two-KV-head profile; TP8 candidate is one
    parameter integer XS     = 40,                // x3 credits = Q FIFO depth (one layer: 8 KVN + 32 Q)
    parameter integer KD     = 8,
    parameter integer KWC    = 4,                 // row credits of each landing write queue
    parameter integer OCR_AR = 64,                // RES credits of the VM (>= 64: one layer)
    parameter integer NS     = 38,                // stages of a decode step: E, L0..L35, H
    parameter integer VOCAB  = 151936,
    parameter integer WDOG   = 1 << 20,
    parameter integer KDESC  = 1,
    parameter integer KD_PMID = 0,
    parameter integer KD_PTOK = 0,
    parameter integer MUT    = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // ROM side
    input  wire          x3_v,
    input  wire [10:0]   x3_tag,
    output reg           x3_cr,
    input  wire [55:0]   sd,                      // {rom_fault, kv_write_flush, coll_busy, core_fault, s_fault, s_done, ntok 18, nval 32}
    input  wire [43:0]   kvd,                     // {v, kindk, pos 18, wbase 24}
    output reg           ar_v,
    output reg  [518:0]  ar_d,
    input  wire          ar_cr,
    output wire [186:0]  ds,                      // {dw 68, pw 75, kv_write_drained, h_start, stage 6, tp_token 18, tp_pos 18}
    output reg  [74:0]   pw,                      // {v, addr 10, data 64} -> the ROM control tile's program copy
    // store control
    output reg           s_qpop,
    output reg           s_kpop,
    output reg  [2:0]    s_kidx,
    output reg           s_kwgo,
    output reg  [1:0]    s_kwn,
    // fan control: two registered copies (0 = W quadrants, 1 = E quadrants)
    (* keep = "true", dont_touch = "true" *) output reg  [2*28-1:0] f_aqm,                 // {start, T 14, layer 6, q valid, beat 6}
    (* keep = "true", dont_touch = "true" *) output reg  [2*23-1:0] f_kwm,                 // {v, vg 2, t 14, layer 6}
    (* keep = "true", dont_touch = "true" *) output reg  [2*33-1:0] f_kc,                  // {v, d 32}
    input  wire [3:0]    f_cr,                    // row credit of quadrant k (through its fan)
    input  wire [3:0]    f_af,
    input  wire [3:0]    f_mf,
    // attention hub
    output reg           hs,                      // start, the cycle the fans' aq start leaves
    input  wire          a_out_valid,
    input  wire          a_out_g,
    input  wire [5:0]    a_out_beat,
    input  wire [511:0]  a_out_data,
    input  wire          a_hub_fault,
    // host
    input  wire [181:0]  hc,                      // {dw_v, dw_addr 3, dw_data 64, pw_v, pw_addr 10, pw_data 64, d_start, d_gen 2, d_token 18, d_pos 18}
    output wire [92:0]   tk,                      // {d_done, gen 2, drained, fault, code 4, coll_busy, kv_write_flush, next_token 18, next_val 32, cycles 32}
    output reg           fault,
    output reg  [8:0]    fault_cause
);
    localparam integer KWORDS = 4 * HEADS;
    localparam integer QWORDS = 16 * HEADS * (Q_FP32 ? 2 : 1); // 32 BF16 or 16 FP32 values/word
    localparam integer RWORDS = 32 * HEADS; // FP32, 16 values per word
    localparam integer KROWS = 2 * HEADS;
    wire [1:0] kw_vg = (HEADS == 1) ? {kw_n[0], 1'b0} : kw_n[1:0];
    reg [7:0] kv_seen;
    // ---- boundary capture ----
    reg           xv, kv, ov, og, ucq, hfq;
    reg  [10:0]   xt;
    reg  [42:0]   kr;
    reg  [5:0]    ob;
    reg  [511:0]  od;
    reg  [3:0]    crq, afq, mfq;
    always @(posedge clk) begin xt <= x3_tag; kr <= kvd[42:0]; ob <= a_out_beat; od <= a_out_data; og <= a_out_g; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin xv <= 1'b0; kv <= 1'b0; ov <= 1'b0; ucq <= 1'b0; hfq <= 1'b0; crq <= 4'd0; afq <= 4'd0; mfq <= 4'd0; end
        else begin xv <= x3_v; kv <= kvd[43]; ov <= a_out_valid; ucq <= ar_cr; hfq <= a_hub_fault; crq <= f_cr; afq <= f_af; mfq <= f_mf; end
    // ---- x3 tag FIFOs (the data words sit in the store, pushed and popped in step) ----
    wire          x_q  = (xt[10:8] == 3'b001), x_kv = (xt[10:8] == 3'b010);
    wire          q_empty, q_full, k_empty, k_full;
    wire [5:0]    q_tag;
    wire [2:0]    k_tag;
    reg           q_pop, k_pop;
    ot_qkvd_fifo #(.W(6), .D(XS)) u_qt (.clk(clk), .rst_n(rst_n), .push(xv && x_q), .din(xt[5:0]), .pop(q_pop),
        .dout(q_tag), .empty(q_empty), .full(q_full), .count());
    ot_qkvd_fifo #(.W(3), .D(KD)) u_kt (.clk(clk), .rst_n(rst_n), .push(xv && x_kv), .din(xt[2:0]), .pop(k_pop),
        .dout(k_tag), .empty(k_empty), .full(k_full), .count());
    // ---- the die's stage stepper (ot_qfd_dctl: d_start {token, pos, gen} -> NS stages of h_start / s_done -> d_done)
    //      and the program / descriptor write relay (capture at the host pins, launch at the ROM-side pins) ----
    localparam integer EW = 2 + 6 + 2 * 24;
    function [NS*EW-1:0] f_stab(input integer dummy);
        integer s_;
        reg [5:0] l_;
        begin
            f_stab = {(NS*EW){1'b0}};
            for (s_ = 0; s_ < NS; s_ = s_ + 1) begin
                l_ = (s_ >= 1 && s_ <= NS - 2) ? s_ - 1 : 63;
                f_stab[s_*EW +: EW] = {(s_ == 0) ? 2'd0 : (s_ == NS - 1) ? 2'd2 : 2'd1, l_, 48'd0};
            end
        end
    endfunction
    localparam [NS*EW-1:0] STAB = f_stab(0);
    reg          drn, cbq, kfq, f_step;
    wire         h_start, d_done, d_drained, d_fault;
    wire [17:0]  tp_token, tp_pos, d_ntok;
    wire [5:0]   stage;
    wire [1:0]   d_dgen;
    wire [3:0]   d_code;
    wire [31:0]  d_nval, d_cyc;
    ot_qfd_dctl #(.NW(18), .AW(24), .NS(NS), .VOCAB(VOCAB), .WDOG(WDOG), .STAB(STAB)) u_step (.clk(clk), .rst_n(rst_n),
        .d_start(hc[38]), .d_token(hc[35:18]), .d_pos(hc[17:0]), .d_gen(hc[37:36]), .d_done(d_done), .d_done_gen(d_dgen),
        .d_next_token(d_ntok), .d_next_val(d_nval), .d_drained(d_drained), .d_fault(d_fault), .d_fault_code(d_code),
        .d_cycles(d_cyc), .h_start(h_start), .tp_token(tp_token), .tp_pos(tp_pos), .stage(stage), .st_prog(), .st_layer(),
        .st_next_layer(), .st_crom(), .st_code(), .st_scale(), .s_done(sd[50]), .seq_ntok(sd[49:32]), .seq_nval(sd[31:0]),
        .s_fault(sd[51]), .core_fault(sd[52]), .coll_fault(sd[55]), .kv_write_drained(drn));
    reg  [74:0]  pwc, pws;
    reg  [67:0]  dwc, dwo;
    always @(posedge clk) begin
        pwc[73:0] <= hc[112:39]; dwc[66:0] <= hc[180:114];
        pw[73:0] <= pwc[73:0]; dwo[66:0] <= dwc[66:0];
        pws[73:0] <= (MUT == 5) ? {pwc[73:64] + 10'd1, pwc[63:0]} : pwc[73:0];
    end
    assign ds = {dwo, pws, drn, h_start, stage, tp_token, tp_pos};
    assign tk = {d_done, d_dgen, d_drained, d_fault, d_code, cbq, kfq, d_ntok, d_nval, d_cyc};
    // ---- launcher: score descriptors -> ATTN {T, layer} ----
    reg  [19:0]  lq0, lq1;                  // {T 14, layer 6}
    reg  [1:0]   ln;
    reg  [17:0]  lp;
    reg          lp_v, f_kq, f_kvd;
    wire         k_kind = kr[42];
    wire [17:0]  k_pos  = kr[41:24];
    wire [23:0]  k_wb   = kr[23:0];
    wire         l_push = kv && k_kind;
    wire [5:0]   l_lay  = (MUT == 3) ? k_wb[11:6] + 6'd1 : k_wb[11:6];
    wire [19:0]  l_w    = {k_pos[13:0] + 14'd1, l_lay};
    // ---- layer state ----
    localparam [2:0] S_IDLE = 3'd0, S_KV = 3'd1, S_ST = 3'd2, S_Q = 3'd3, S_RUN = 3'd4;
    reg [2:0]   st;
    reg [5:0]   layer;
    reg [13:0]  a_T;
    reg         a_start, a_q_valid;
    reg [5:0]   a_q_beat;
    reg [3:0]   kv_n;
    reg [5:0]   q_n;
    reg [6:0]   r_n;
    reg [2:0]   kw_n;
    reg [7:0]   kwc, uc0;
    reg         kw_go, kwq, kvw_v;
    reg [1:0]   kvw_vg;
    reg [13:0]  kvw_t;
    reg [5:0]   kvw_layer;
    reg         f_res, f_ord, f_row, f_pend, f_kw, f_x, f_xovr, f_join;
    wire        go = (st == S_IDLE) && (ln != 2'd0);
    always @* begin
        // (the previous layer's four rows are all posted before its KVN words are replaced: ot_qkvd_kv_seq dropped the
        //  unposted rows when the row credits were late)
        k_pop = (st == S_KV && kv_n < 4'(KWORDS) && !k_empty && kw_n == 3'(KROWS));
        q_pop = (st == S_Q && !q_empty);
    end
    wire [13:0] go_T  = lq0[19:6];
    wire [5:0]  go_L  = lq0[5:0];
    always @(posedge clk) begin
        if (q_pop) a_q_beat <= (MUT == 2 && q_tag < 6'd2) ? (q_tag ^ 6'd1) : q_tag;
        if (ov) ar_d <= {og, ob, od};
        if (kw_go) begin kvw_vg <= kw_vg; kvw_t <= a_T - 1'b1; kvw_layer <= layer; end
        s_kidx <= k_tag;
        s_kwn  <= kw_vg;
    end
    // ---- stream descriptors to the HBM controllers (as ot_qkvd_kv_seq KDESC) ----
    wire        kd_fault, kd_v;
    wire [31:0] kd_d;
    generate if (KDESC != 0) begin : g_kd
        ot_qkvd_kv_desc #(.NL(36)) u_kd (.clk(clk), .rst_n(rst_n), .p_mid_init(20'(KD_PMID)), .p_tok_init(20'(KD_PTOK)),
            .attn_v(go), .attn_layer(go_L), .attn_T(go_T),
            .done_v(st == S_RUN && ov && r_n == 7'(RWORDS - 1)), .k_v(kd_v), .k_d(kd_d), .k_ready(1'b1), .fault(kd_fault));
    end else begin : g_nkd
        assign kd_v = 1'b0; assign kd_d = 32'd0; assign kd_fault = 1'b0;
    end endgenerate
    always @(posedge clk) f_kc[31:0] <= kd_d;
    always @(posedge clk) f_kc[33 +: 32] <= kd_d;
    // ---- credit join of the four landing write queues ----
    reg  [2:0]  jc [0:3];
    wire [3:0]  jnz = {jc[3] != 0, jc[2] != 0, jc[1] != 0, jc[0] != 0};
    wire        jn  = (MUT == 4) ? |jnz : &jnz;
    // ---- outputs to the fans: the sequencer's own registers + one stage, then the pin copies ----
    reg  [27:0] aq1;
    reg  [22:0] kw1;
    reg  [2:0]  hsd;
    always @(posedge clk) begin
        aq1[26:7] <= {a_T, layer}; aq1[5:0] <= a_q_beat;
        f_aqm[26:7] <= aq1[26:7]; f_aqm[5:0] <= aq1[5:0];
        f_aqm[28+26 -: 20] <= aq1[26:7]; f_aqm[28 +: 6] <= aq1[5:0];
        kw1[21:0] <= {kvw_vg, kvw_t, kvw_layer};
        f_kwm[21:0] <= kw1[21:0]; f_kwm[23 +: 22] <= kw1[21:0];
    end
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            kv_seen <= 8'd0; st <= S_IDLE; layer <= 0; kv_n <= 0; q_n <= 0; r_n <= 0; a_start <= 1'b0; a_T <= 14'd0; a_q_valid <= 1'b0;
            x3_cr <= 1'b0; uc0 <= 8'(OCR_AR); ar_v <= 1'b0;
            kw_n <= 3'(KROWS); kwc <= 8'(KWC); kw_go <= 1'b0; kvw_v <= 1'b0; kwq <= 1'b0;
            s_qpop <= 1'b0; s_kpop <= 1'b0; s_kwgo <= 1'b0; hs <= 1'b0; hsd <= 3'd0;
            aq1[27] <= 1'b0; aq1[6] <= 1'b0; f_aqm[27] <= 1'b0; f_aqm[6] <= 1'b0; f_aqm[55] <= 1'b0; f_aqm[34] <= 1'b0;
            kw1[22] <= 1'b0; f_kwm[22] <= 1'b0; f_kwm[45] <= 1'b0; f_kc[32] <= 1'b0; f_kc[65] <= 1'b0;
            lq0 <= 20'd0; lq1 <= 20'd0; ln <= 2'd0; lp <= 18'd0; lp_v <= 1'b0; f_kq <= 1'b0; f_kvd <= 1'b0;
            for (i = 0; i < 4; i = i + 1) jc[i] <= 3'd0;
            f_res <= 1'b0; f_ord <= 1'b0; f_kw <= 1'b0; f_row <= 1'b0; f_pend <= 1'b0; f_x <= 1'b0;
            f_xovr <= 1'b0; f_join <= 1'b0; fault <= 1'b0; fault_cause <= 9'd0;
            drn <= 1'b0; cbq <= 1'b0; kfq <= 1'b0; f_step <= 1'b0;
            pwc[74] <= 1'b0; dwc[67] <= 1'b0; pw[74] <= 1'b0; pws[74] <= 1'b0; dwo[67] <= 1'b0;
        end else begin
            x3_cr <= q_pop | k_pop;
            s_qpop <= q_pop; s_kpop <= k_pop; s_kwgo <= kw_go;
            a_start <= 1'b0;
            a_q_valid <= q_pop;
            // host writes, status
            pwc[74] <= hc[113]; dwc[67] <= hc[181]; pw[74] <= pwc[74]; pws[74] <= pwc[74]; dwo[67] <= dwc[67];
            cbq <= sd[53]; kfq <= sd[54];
            // every posted row stored (all four queues returned its credit), nothing launched or waiting
            drn <= (st == S_IDLE) && (ln == 2'd0) && !kv && !xv && q_empty && k_empty && (kw_n == 3'(KROWS)) && !kw_go &&
                   (kwc == 8'(KWC)) && !kwq;
            // launcher queue
            if (l_push) begin
                lp <= k_pos; lp_v <= 1'b1;
                if (k_wb[23:12] != 12'd0 || k_pos[17:14] != 4'd0) f_kvd <= 1'b1;
                if (ln == 2'd2 && !go) f_kq <= 1'b1;
            end
            if (kv && !k_kind && (!lp_v || k_pos != lp)) f_kvd <= 1'b1;
            case ({l_push && !(ln == 2'd2 && !go), go})
                2'b10: begin if (ln == 2'd0) lq0 <= l_w; else lq1 <= l_w; ln <= ln + 2'd1; end
                2'b01: begin lq0 <= lq1; ln <= ln - 2'd1; end
                2'b11: begin if (ln == 2'd1) lq0 <= l_w; else begin lq0 <= lq1; lq1 <= l_w; end end
                default: ;
            endcase
            case (st)
                S_IDLE: if (go) begin
                    kv_seen <= 8'd0; a_T <= go_T; layer <= go_L; kv_n <= 0; q_n <= 0; r_n <= 0; st <= S_KV;
                end
                S_KV: begin
                    if (k_pop) begin
                        kv_n <= kv_n + 1'b1;
                        if (kv_seen[k_tag] || (HEADS == 1 && k_tag[1])) f_ord <= 1'b1;
                        kv_seen[k_tag] <= 1'b1;
                    end
                    // the hub has no ready: the layer starts with all of its 64 RES credits in hand
                    if (kv_n == 4'(KWORDS) && uc0 >= 8'(RWORDS)) begin st <= S_ST; a_start <= 1'b1; kw_n <= 3'd0; end
                end
                S_ST: st <= S_Q;           // start leads the first q beat by one cycle (the stack's contract)
                S_Q: begin
                    if (q_pop) begin
                        if (q_tag != q_n) f_ord <= 1'b1;
                        q_n <= q_n + 1'b1;
                        if (q_n == 6'(QWORDS - 1)) st <= S_RUN;
                    end
                end
                S_RUN: if (ov && r_n == 7'(RWORDS - 1)) st <= S_IDLE;
                default: st <= S_IDLE;
            endcase
            if (ov) begin
                r_n <= r_n + 1'b1;
                if (HEADS == 1 && (og || ob != r_n[5:0] || st != S_RUN)) f_ord <= 1'b1;
            end
            ar_v <= ov;
            if (ov && uc0 == 0) f_res <= 1'b1;
            uc0 <= uc0 - (ov ? 8'd1 : 8'd0) + (ucq ? 8'd1 : 8'd0);
            // KV write: post the four rows of the new position, one per (joined) credit
            kw_go <= (kw_n < 3'(KROWS)) && (kwc != 0) && !kw_go;
            if (kw_go) kw_n <= kw_n + 1'b1;
            kvw_v <= kw_go;
            kwc <= kwc - (kw_go ? 8'd1 : 8'd0) + (kwq ? 8'd1 : 8'd0);
            kwq <= jn;
            for (i = 0; i < 4; i = i + 1) begin
                jc[i] <= jc[i] + (crq[i] ? 3'd1 : 3'd0) - ((jn && jc[i] != 0) ? 3'd1 : 3'd0);
                if (crq[i] && jc[i] == 3'd7) f_join <= 1'b1;
            end
            // pin copies
            aq1[27] <= a_start; aq1[6] <= a_q_valid;
            f_aqm[27] <= aq1[27]; f_aqm[6] <= aq1[6]; f_aqm[55] <= aq1[27]; f_aqm[34] <= aq1[6];
            kw1[22] <= kvw_v; f_kwm[22] <= kw1[22]; f_kwm[45] <= kw1[22];
            f_kc[32] <= kd_v; f_kc[65] <= kd_v;
            hsd <= {hsd[1:0], a_start}; hs <= hsd[2];
            // faults
            if (xv && ((x_q && q_full && !q_pop) || (x_kv && k_full && !k_pop))) f_xovr <= 1'b1;
            if (xv && !x_q && !x_kv) f_x <= 1'b1;
            if (kwq && kwc == 8'(KWC)) f_kw <= 1'b1;
            f_row <= f_row | (|mfq); f_pend <= f_pend | hfq | (|afq);
            f_step <= f_step | d_fault;
            fault_cause <= {f_x | f_xovr, f_kq, f_kvd, f_join, kd_fault, f_kw | f_row | f_pend, f_ord, f_res, f_step};
            fault <= |{f_x, f_xovr, f_kq, f_kvd, f_join, f_kw, f_row, f_pend, f_ord, f_res, f_step, kd_fault};
        end
    end
`ifndef SYNTHESIS
    initial begin
        if (Q_FP32 != 0 && Q_FP32 != 1) $error("ot_qkvd_seq_m_ctl: Q_FP32 must be 0 or 1");
        if (HEADS != 1 && HEADS != 2) $error("ot_qkvd_seq_m_ctl: HEADS must be 1 or 2");
        if (OCR_AR < RWORDS) $error("ot_qkvd_seq_m_ctl: OCR_AR must cover one layer");
        if (XS < KWORDS + QWORDS || KD < KWORDS) $error("ot_qkvd_seq_m_ctl: input FIFO credits must cover one layer");
    end
`endif
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Store FIFO: as ot_qkvd_fifo RH 0 (write registered, head read from the array) without flags (the control's tag FIFO
// carries them), with the READ POINTER replicated per 16 data bits (kept copies): one pointer bit selected every bit of
// the D:1 head mux (5,123 loads at 128 x 40, pre-route gate 10-13).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_seq_m_sfifo #(
    parameter integer W = 128,
    parameter integer D = 40,
    parameter integer GB = 16
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         push,
    input  wire [W-1:0] din,
    input  wire         pop,
    output wire [W-1:0] dout
);
    localparam integer AW = (D > 1) ? $clog2(D) : 1;
    localparam integer NG = (W + GB - 1) / GB;
    reg [W-1:0]  mem [0:D-1];
    reg [AW-1:0] wp;
    (* keep = "true", dont_touch = "true" *) reg [NG*AW-1:0] rp;
    always @(posedge clk) if (push) mem[wp] <= din;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) wp <= 0;
        else if (push) wp <= (wp == AW'(D - 1)) ? {AW{1'b0}} : wp + 1'b1;
    genvar g;
    generate for (g = 0; g < NG; g = g + 1) begin : g_rp
        localparam integer LO = g * GB;
        localparam integer GW = (LO + GB > W) ? W - LO : GB;
        wire [AW-1:0] r = rp[g*AW +: AW];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) rp[g*AW +: AW] <= {AW{1'b0}};
            else if (pop) rp[g*AW +: AW] <= (r == AW'(D - 1)) ? {AW{1'b0}} : r + 1'b1;
        wire [W-1:0] hw = mem[r];
        assign dout[LO +: GW] = hw[LO +: GW];
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// x3 data storage, DW bits of the 512-b word: Q FIFO (XS), KVN FIFO (KD) and the eight KVN words of the layer.  The
// control's tag FIFOs move in step: pushes are decoded here from the word's own valid / class (same pins, same edge),
// pops arrive registered from the control.  q and kw leave as two registered copies (W / E fans).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_seq_m_store #(
    parameter integer HEADS = 2,
    parameter integer DW = 512,
    parameter integer XS = 40,
    parameter integer KD = 8
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            x_v,
    input  wire [2:0]      x_cls,
    input  wire [DW-1:0]   x_d,
    input  wire            qpop,
    input  wire            kpop,
    input  wire [2:0]      kidx,
    input  wire            kwgo,
    input  wire [1:0]      kwn,
    (* keep = "true", dont_touch = "true" *) output reg  [2*DW-1:0] q,                  // copy c at [c*DW +: DW]
    (* keep = "true", dont_touch = "true" *) output reg  [4*DW-1:0] kw                  // copy c at [c*2*DW +: 2*DW] = {word {vg, 1}, word {vg, 0}}
);
    reg          xv, qp, kp, kg;
    reg [2:0]    xc, ki;
    reg [1:0]    kn;
    reg [DW-1:0] xd;
    always @(posedge clk) begin xc <= x_cls; xd <= x_d; ki <= kidx; kn <= kwn; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin xv <= 1'b0; qp <= 1'b0; kp <= 1'b0; kg <= 1'b0; end
        else begin xv <= x_v; qp <= qpop; kp <= kpop; kg <= kwgo; end
    wire [DW-1:0] qh, kh;
    ot_qkvd_seq_m_sfifo #(.W(DW), .D(XS)) u_q (.clk(clk), .rst_n(rst_n), .push(xv && xc == 3'b001), .din(xd), .pop(qp), .dout(qh));
    ot_qkvd_seq_m_sfifo #(.W(DW), .D(KD)) u_k (.clk(clk), .rst_n(rst_n), .push(xv && xc == 3'b010), .din(xd), .pop(kp), .dout(kh));
    reg [DW-1:0] kvn [0:7];
    always @(posedge clk) begin
        if (kp) kvn[(HEADS == 1) ? {ki[2],1'b0,ki[0]} : ki] <= kh;
        if (qp) q <= {2{qh}};
        if (kg) kw <= {2{kvn[{kn[1], (HEADS == 1 ? 1'b0 : kn[0]), 1'b1}], kvn[{kn[1], (HEADS == 1 ? 1'b0 : kn[0]), 1'b0}]}};
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// One quadrant's pin registers: aq / kvn / kc out (capture, then launch at the face), row credit and the two fault
// bits back (capture at the face, then launch toward the control).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_seq_m_fan #(
    parameter integer HD = 128
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire [27:0]        aqm,
    input  wire [511:0]       q,
    input  wire [22:0]        kwm,
    input  wire [HD*8-1:0]    kw,
    input  wire [32:0]        kc_i,
    output wire [539:0]       aq,              // {start, T 14, layer 6, q valid, beat 6, data 512}
    output wire [HD*8+22:0]   kvn,             // {v, vg 2, t 14, layer 6, row}
    output wire [32:0]        kc,              // {v, d 32}
    input  wire               kvn_cr,
    input  wire               af,
    input  wire               mf,
    output reg                cr_o,
    output reg                af_o,
    output reg                mf_o
);
    reg [27:0]      am, am2;
    reg [511:0]     qd, qd2;
    reg [22:0]      km, km2;
    reg [HD*8-1:0]  kd, kd2;
    reg [32:0]      kq, kq2;
    reg             c1, a1, m1;
    always @(posedge clk) begin
        am[26:7] <= aqm[26:7]; am[5:0] <= aqm[5:0]; am2[26:7] <= am[26:7]; am2[5:0] <= am[5:0];
        qd <= q; qd2 <= qd; km[21:0] <= kwm[21:0]; km2[21:0] <= km[21:0]; kd <= kw; kd2 <= kd;
        kq[31:0] <= kc_i[31:0]; kq2[31:0] <= kq[31:0];
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            am[27] <= 1'b0; am[6] <= 1'b0; am2[27] <= 1'b0; am2[6] <= 1'b0; km[22] <= 1'b0; km2[22] <= 1'b0;
            kq[32] <= 1'b0; kq2[32] <= 1'b0; c1 <= 1'b0; a1 <= 1'b0; m1 <= 1'b0; cr_o <= 1'b0; af_o <= 1'b0; mf_o <= 1'b0;
        end else begin
            am[27] <= aqm[27]; am[6] <= aqm[6]; am2[27] <= am[27]; am2[6] <= am[6]; km[22] <= kwm[22]; km2[22] <= km[22];
            kq[32] <= kc_i[32]; kq2[32] <= kq[32]; c1 <= kvn_cr; a1 <= af; m1 <= mf; cr_o <= c1; af_o <= a1; mf_o <= m1;
        end
    assign aq  = {am2[27:6], am2[5:0], qd2};
    assign kvn = {km2, kd2};
    assign kc  = kq2;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// The flat merged-die sequencer (reference of the cluster; the layer bench runs through it).  Quadrant k: 0 WS, 1 WN,
// 2 ES, 3 EN.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_kv_seq_merged #(
    parameter integer HD     = 128,
    parameter integer Q_FP32 = 0,                 // explicit transport precision; no conversion
    parameter integer HEADS  = 2,
    parameter integer XS     = 40,
    parameter integer KD     = 8,
    parameter integer KWC    = 4,
    parameter integer OCR_AR = 64,
    parameter integer NS     = 38,
    parameter integer VOCAB  = 151936,
    parameter integer WDOG   = 1 << 20,
    parameter integer KDESC  = 1,
    parameter integer KD_PMID = 0,
    parameter integer KD_PTOK = 0,
    parameter integer MUT    = 0
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               x3_v,
    input  wire [10:0]        x3_tag,
    input  wire [511:0]       x3_d,
    output wire               x3_cr,
    input  wire [55:0]        sd,
    input  wire [43:0]        kvd,
    output wire               ar_v,
    output wire [518:0]       ar_d,
    input  wire               ar_cr,
    output wire [186:0]       ds,
    output wire [74:0]        pw,
    output wire [4*540-1:0]   aq,
    output wire [4*(HD*8+23)-1:0] kvn,
    input  wire [3:0]         kvn_cr,
    output wire [4*33-1:0]    kc,
    input  wire [3:0]         af,
    input  wire [3:0]         mf,
    output wire               hs,
    input  wire               a_out_valid,
    input  wire               a_out_g,
    input  wire [5:0]         a_out_beat,
    input  wire [511:0]       a_out_data,
    input  wire               a_hub_fault,
    input  wire [181:0]       hc,
    output wire [92:0]        tk,
    output wire               fault,
    output wire [8:0]         fault_cause
);
    wire          s_qpop, s_kpop, s_kwgo;
    wire [2:0]    s_kidx;
    wire [1:0]    s_kwn;
    wire [2*28-1:0] f_aqm;
    wire [2*23-1:0] f_kwm;
    wire [2*33-1:0] f_kc;
    wire [3:0]    f_cr, f_af, f_mf;
    wire [2*512-1:0]  sq;
    wire [4*512-1:0]  skw;
    ot_qkvd_seq_m_ctl #(.Q_FP32(Q_FP32), .HEADS(HEADS), .XS(XS), .KD(KD), .KWC(KWC), .OCR_AR(OCR_AR), .NS(NS), .VOCAB(VOCAB), .WDOG(WDOG),
                        .KDESC(KDESC), .KD_PMID(KD_PMID), .KD_PTOK(KD_PTOK), .MUT(MUT)) u_ctl (
        .clk(clk), .rst_n(rst_n), .x3_v(x3_v), .x3_tag(x3_tag), .x3_cr(x3_cr), .sd(sd), .kvd(kvd), .ar_v(ar_v),
        .ar_d(ar_d), .ar_cr(ar_cr), .ds(ds), .pw(pw), .s_qpop(s_qpop), .s_kpop(s_kpop),
        .s_kidx(s_kidx), .s_kwgo(s_kwgo), .s_kwn(s_kwn), .f_aqm(f_aqm), .f_kwm(f_kwm), .f_kc(f_kc), .f_cr(f_cr),
        .f_af(f_af), .f_mf(f_mf), .hs(hs), .a_out_valid(a_out_valid), .a_out_g(a_out_g), .a_out_beat(a_out_beat),
        .a_out_data(a_out_data), .a_hub_fault(a_hub_fault), .hc(hc), .tk(tk), .fault(fault), .fault_cause(fault_cause));
    ot_qkvd_seq_m_store #(.HEADS(HEADS), .DW(512), .XS(XS), .KD(KD)) u_st (.clk(clk), .rst_n(rst_n), .x_v(x3_v), .x_cls(x3_tag[10:8]),
        .x_d(x3_d), .qpop(s_qpop), .kpop(s_kpop), .kidx(s_kidx), .kwgo(s_kwgo), .kwn(s_kwn), .q(sq), .kw(skw));
    genvar k;
    generate for (k = 0; k < 4; k = k + 1) begin : g_fan
        ot_qkvd_seq_m_fan #(.HD(HD)) u_f (.clk(clk), .rst_n(rst_n), .aqm(f_aqm[28*(k/2) +: 28]), .q(sq[512*(k/2) +: 512]),
            .kwm(f_kwm[23*(k/2) +: 23]), .kw(skw[1024*(k/2) +: 1024]), .kc_i(f_kc[33*(k/2) +: 33]),
            .aq(aq[540*k +: 540]), .kvn(kvn[(HD*8+23)*k +: HD*8+23]), .kc(kc[33*k +: 33]), .kvn_cr(kvn_cr[k]),
            .af(af[k]), .mf(mf[k]), .cr_o(f_cr[k]), .af_o(f_af[k]), .mf_o(f_mf[k]));
    end endgenerate
endmodule
