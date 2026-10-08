`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// STREAM4 memory clock interface, ONE pseudo-channel (hardened element, replicated NPC = 128 a die).
// Synthesizable.  The near-HBM stream controller runs on the external periodic HCLK (1,024 ps,
// results/rtl/qwen_rom_stream4_clock_plan_20261005 selected_P0_clock_boundary_r5.json); the KV
// service runs on the core clock CLK (833.333 ps).  The three per-PC crossings of that plan:
//   landing    HCLK -> CLK  gray-pointer async FIFO, depth LD (64 > CRED 32), payload 281 b
//                           {sec17, row8, data256}; CLK side presents through a registered output
//                           stage (l_v / l_sec / l_row / l_data are flops); the controller's
//                           credits are the synchronized read pointer's advance per HCLK edge.
//   write      CLK -> HCLK  gray-pointer async FIFO, depth WB (16), payload 289 b {sec24, data256,
//                           tag}; TWO HCLK read pointers: hand-off h (the access-queue entry, head
//                           sector registered as h_wv / h_wsec) and completion c (the WR column
//                           command; its entry is captured into h_c* registers).  w_room (>= 3
//                           free) is computed against the synchronized completion pointer.
//   write-done HCLK -> CLK  gray-pointer async FIFO, depth AD (64), payload TAGW; wd_v / wd_tag
//                           registered, every presented head is taken (the service's contract).
// Every crossing is a binary-reflected Gray pointer through SYNC (>= 2) flops; storage is not
// reset (validity is carried by the pointers); the storage read mux is in the reading domain and
// is a constrained datapath arc (slot stable for >= SYNC destination edges after the pointer moves).
// Resets: c_arst_n / h_arst_n are the raw common reset epoch (asynchronous assertion); each domain
// releases it through its own local two-flop synchronizer inside the element, so every recovery
// path starts at a local flop (route r1: the port-driven reset tree missed recovery by 12.9 ps).
// No traffic before the descriptor, so no rendezvous is needed.
// ---------------------------------------------------------------------------
module ot_qwen_stream4_cdc_pc #(
    parameter integer TAGW = 9,
    parameter integer LD   = 64,            // landing depth, power of two
    parameter integer WB   = 16,            // write-queue depth, power of two
    parameter integer AD   = 64,            // write-done depth, power of two
    parameter integer SYNC = 2,             // synchronizer flops per crossing
    // r8 (default 0 = r6/r7 structure): RSEL 1 = every landing read column group owns a one-hot select
    // register in its own kept hierarchy (ot_hdc_v41x_kreg), loaded with decode(next read index): the
    // r7 routes showed yosys merging the r3 (* keep *) index copies back into lr_bin (one driver, a
    // 9/14/30/31 buffer tree into the 64:1 mux, SS -1.1..-49.9 ps).  RNG = column groups when RSEL = 1.
    parameter integer RSEL = 0,
    parameter integer RNG  = 10,
    // MARGIN 1 (owner margin rule 2026-10-06; default 0 = the structure above, unchanged): every data input is
    // registered at its pin (w_* in CLK, h_l* / h_a* in HCLK: one cycle of latency, flow control unchanged: w_room
    // keeps one more slot in flight), and the landing is CREDIT-based: l_pop is a registered credit return (one per
    // word the receiver consumed), l_v is a one-cycle push of the word on l_* (the receiver queues it), at most LCRED
    // words outstanding.  No input reaches a register enable or a mux select inside the element.
    parameter integer MARGIN = 0,
    parameter integer LCRED = 6
) (
    // ---- CLK (core) domain ----
    input  wire             clk,
    input  wire             c_arst_n,
    output reg              l_v,
    output reg  [16:0]      l_sec,           // driven by the group registers l_q
    output reg  [7:0]       l_row,
    output reg  [255:0]     l_data,
    input  wire             l_pop,
    input  wire             w_v,
    input  wire [23:0]      w_sec,
    input  wire [255:0]     w_data,
    input  wire [TAGW-1:0]  w_tag,
    output reg              w_room,
    output reg              wd_v,
    output reg  [TAGW-1:0]  wd_tag,
    output reg              c_fault,        // write pushed into a full queue
    // ---- HCLK (controller) domain ----
    input  wire             hclk,
    input  wire             h_arst_n,
    input  wire             h_lv,           // landing push (a returned RD beat)
    input  wire [16:0]      h_lsec,
    input  wire [7:0]       h_lrow,
    input  wire [255:0]     h_ldata,
    output reg  [2:0]       h_cred,         // landing slots freed since the previous HCLK edge
    output reg              h_wv,           // write-queue head (hand-off pointer) valid
    output reg  [23:0]      h_wsec,         // its sector
    input  wire             h_hand,         // head handed to the access queue (h_wv && wr_r)
    input  wire             h_wcon,         // WR column command consumes the completion entry
    output reg              h_cv,           // captured completion entry (one edge after h_wcon)
    output reg  [23:0]      h_csec,
    output reg  [255:0]     h_cdata,
    output reg  [TAGW-1:0]  h_ctag,
    input  wire             h_av,           // write-done push
    input  wire [TAGW-1:0]  h_atag,
    output reg              h_fault         // landing / write-done push into a full FIFO, or WR with empty queue
);
    localparam integer LA = $clog2(LD), WA = $clog2(WB), AA = $clog2(AD);
    // ---- MARGIN: pin registers ----
    wire             w_v_i, h_lv_i, h_av_i, l_pop_i;
    wire [23:0]      w_sec_i; wire [255:0] w_data_i; wire [TAGW-1:0] w_tag_i;
    wire [16:0]      h_lsec_i; wire [7:0] h_lrow_i; wire [255:0] h_ldata_i; wire [TAGW-1:0] h_atag_i;
    generate if (MARGIN != 0) begin : g_pin
        reg wv_q, lp_q, hlv_q, hav_q; reg [23:0] ws_q; reg [255:0] wd_q; reg [TAGW-1:0] wt_q;
        reg [16:0] hls_q; reg [7:0] hlr_q; reg [255:0] hld_q; reg [TAGW-1:0] hat_q;
        always @(posedge clk or negedge c_arst_n) if (!c_arst_n) begin wv_q <= 1'b0; lp_q <= 1'b0; end
                                                  else begin wv_q <= w_v; lp_q <= l_pop; end
        always @(posedge clk) begin ws_q <= w_sec; wd_q <= w_data; wt_q <= w_tag; end
        always @(posedge hclk or negedge h_arst_n) if (!h_arst_n) begin hlv_q <= 1'b0; hav_q <= 1'b0; end
                                                   else begin hlv_q <= h_lv; hav_q <= h_av; end
        always @(posedge hclk) begin hls_q <= h_lsec; hlr_q <= h_lrow; hld_q <= h_ldata; hat_q <= h_atag; end
        assign {w_v_i, w_sec_i, w_data_i, w_tag_i, l_pop_i} = {wv_q, ws_q, wd_q, wt_q, lp_q};
        assign {h_lv_i, h_lsec_i, h_lrow_i, h_ldata_i, h_av_i, h_atag_i} = {hlv_q, hls_q, hlr_q, hld_q, hav_q, hat_q};
    end else begin : g_nopin
        assign {w_v_i, w_sec_i, w_data_i, w_tag_i, l_pop_i} = {w_v, w_sec, w_data, w_tag, l_pop};
        assign {h_lv_i, h_lsec_i, h_lrow_i, h_ldata_i, h_av_i, h_atag_i} = {h_lv, h_lsec, h_lrow, h_ldata, h_av, h_atag};
    end endgenerate

    // local reset release, one synchronizer per domain
    // The release stage is three KEPT copies per domain, one per crossing (landing / write queue /
    // write-done), so each reset tree is local (route r2: one shared release flop missed recovery by 18 ps
    // through a 4-level placement-buffer chain across the element).
    (* async_reg = "true" *) reg c_rs0, h_rs0;
    (* keep *) reg c_rl, c_rw, c_ra, h_rl, h_rw, h_ra;
    // MARGIN >= 2 (qwen-blocks 2026-10-07): each kept release copy takes its own kept pre-stage, so the copy can sit
    // beside its tree (routes: c_ra -> ar_bin / ww_bin recovery -3.8..-24.3 ps through a 4-buffer chain from the shared
    // c_rs0 corner); every domain releases one edge later, all three trees of a domain still together.
    wire c_sl, c_sw, c_sa, h_sl, h_sw, h_sa;
    generate if (MARGIN >= 2) begin : g_rpre
        (* keep *) reg c_pl, c_pw, c_pa, h_pl, h_pw, h_pa;
        always @(posedge clk or negedge c_arst_n)
            if (!c_arst_n) {c_pl, c_pw, c_pa} <= 3'b0; else begin c_pl <= c_rs0; c_pw <= c_rs0; c_pa <= c_rs0; end
        always @(posedge hclk or negedge h_arst_n)
            if (!h_arst_n) {h_pl, h_pw, h_pa} <= 3'b0; else begin h_pl <= h_rs0; h_pw <= h_rs0; h_pa <= h_rs0; end
        assign {c_sl, c_sw, c_sa, h_sl, h_sw, h_sa} = {c_pl, c_pw, c_pa, h_pl, h_pw, h_pa};
    end else begin : g_rnopre
        assign {c_sl, c_sw, c_sa, h_sl, h_sw, h_sa} = {6{1'b0}} | {c_rs0, c_rs0, c_rs0, h_rs0, h_rs0, h_rs0};
    end endgenerate
    always @(posedge clk or negedge c_arst_n)
        if (!c_arst_n) {c_rs0, c_rl, c_rw, c_ra} <= 4'b0; else begin c_rs0 <= 1'b1; c_rl <= c_sl; c_rw <= c_sw; c_ra <= c_sa; end
    always @(posedge hclk or negedge h_arst_n)
        if (!h_arst_n) {h_rs0, h_rl, h_rw, h_ra} <= 4'b0; else begin h_rs0 <= 1'b1; h_rl <= h_sl; h_rw <= h_sw; h_ra <= h_sa; end

    function automatic [LA:0] g2b_l(input [LA:0] g);
        integer i; begin g2b_l[LA] = g[LA]; for (i = LA - 1; i >= 0; i = i - 1) g2b_l[i] = g2b_l[i+1] ^ g[i]; end
    endfunction
    function automatic [WA:0] g2b_w(input [WA:0] g);
        integer i; begin g2b_w[WA] = g[WA]; for (i = WA - 1; i >= 0; i = i - 1) g2b_w[i] = g2b_w[i+1] ^ g[i]; end
    endfunction
    function automatic [AA:0] g2b_a(input [AA:0] g);
        integer i; begin g2b_a[AA] = g[AA]; for (i = AA - 1; i >= 0; i = i - 1) g2b_a[i] = g2b_a[i+1] ^ g[i]; end
    endfunction

    // =========================== landing: HCLK -> CLK ===========================
    reg [280:0] lmem [0:LD-1];
    reg [LA:0] lw_bin, lw_gray;                                   // HCLK
    reg [LA:0] lr_bin, lr_gray;                                   // CLK
    (* async_reg = "true" *) reg [LA:0] lw_s [0:SYNC-1];          // lw_gray in CLK
    (* async_reg = "true" *) reg [LA:0] lr_s [0:SYNC-1];          // lr_gray in HCLK
    reg [LA:0] lr_seen;                                           // HCLK: synchronized read pointer, previous edge
    wire [LA:0] lr_sb = g2b_l(lr_s[SYNC-1]);
    wire        l_full = (lw_bin - lr_sb) == LD[LA:0];
    wire [LA:0] lw_bin_n = lw_bin + {{LA{1'b0}}, h_lv_i && !l_full};
    integer s;
    always @(posedge hclk or negedge h_rl) begin
        if (!h_rl) begin
            lw_bin <= 0; lw_gray <= 0; lr_seen <= 0; h_cred <= 0;
            for (s = 0; s < SYNC; s = s + 1) lr_s[s] <= 0;
        end else begin
            lw_bin <= lw_bin_n; lw_gray <= (lw_bin_n >> 1) ^ lw_bin_n;
            lr_s[0] <= lr_gray; for (s = 1; s < SYNC; s = s + 1) lr_s[s] <= lr_s[s-1];
            h_cred <= 3'(lr_sb - lr_seen); lr_seen <= lr_sb;
        end
    end
    // Storage write: NG column groups, each with a KEPT copy of the write index, and NOT gated by the
    // synchronized-pointer full flag (route r1: lr_s -> l_full -> 18k write enables missed by 3 ps).
    // The controller reserves a credit before every RD, so a push into a full FIFO is a protocol fault:
    // h_fault rises and the pointer does not advance (the overwritten slot is never presented as valid
    // data before the sticky fault).
    localparam integer LNG = 5, LGW = (281 + LNG - 1) / LNG;
    wire [LNG*LGW-1:0] l_in = {{(LNG*LGW-281){1'b0}}, h_lsec_i, h_lrow_i, h_ldata_i};
    for (genvar gw = 0; gw < LNG; gw = gw + 1) begin : lwg
        localparam integer LO = gw * LGW, HI = (LO + LGW > 281) ? 281 : LO + LGW;
        (* keep *) reg [LA-1:0] wi;
        always @(posedge hclk or negedge h_rl) if (!h_rl) wi <= 0; else wi <= lw_bin_n[LA-1:0];
        always @(posedge hclk) if (h_lv_i) lmem[wi][HI-1:LO] <= l_in[HI-1:LO];
    end
    wire        l_empty = lr_gray == lw_s[SYNC-1];
    // MARGIN: credit counter (LCRED receiver slots); a push needs a credit, l_pop_i returns one
    localparam integer CW = $clog2(LCRED + 1);
    reg  [CW-1:0] l_cred;
    wire        l_push  = !l_empty && (l_cred != 0);
    wire        l_ren   = (MARGIN != 0) ? l_push : (!l_empty && (!l_v || l_pop));
    always @(posedge clk or negedge c_rl)
        if (!c_rl) l_cred <= CW'(LCRED);
        else if (MARGIN != 0) l_cred <= l_cred - CW'(l_push) + CW'(l_pop_i);
    wire [LA:0] lr_bin_n = lr_bin + {{LA{1'b0}}, l_ren};
    always @(posedge clk or negedge c_rl) begin
        if (!c_rl) begin
            lr_bin <= 0; lr_gray <= 0; l_v <= 1'b0;
            for (s = 0; s < SYNC; s = s + 1) lw_s[s] <= 0;
        end else begin
            lw_s[0] <= lw_gray; for (s = 1; s < SYNC; s = s + 1) lw_s[s] <= lw_s[s-1];
            lr_bin <= lr_bin_n; lr_gray <= (lr_bin_n >> 1) ^ lr_bin_n;
            if (MARGIN != 0) l_v <= l_push;
            else if (l_ren) l_v <= 1'b1; else if (l_pop) l_v <= 1'b0;
        end
    end
    // The 281-bit read mux is split into NG column groups, each with its own KEPT copy of the read index
    // and of l_v (route r1/r2: the shared lr_bin -> 64:1 mux -> l_data path missed by 10 ps on fanout).
    // A group's output register loads whenever the presented word is free (!l_v || l_pop): when the FIFO
    // is empty it loads the unwritten slot at the read index, which l_v (= 0) marks invalid.  Identical
    // l_v / l_* sequence on every valid cycle; zero added cycles.
    localparam integer NG = (RSEL != 0) ? RNG : 5, GW = (281 + NG - 1) / NG;
    wire [NG*GW-1:0] l_word;
    reg  [NG*GW-1:0] l_q;
    wire [LD-1:0] lr_hot_n = {{(LD-1){1'b0}}, 1'b1} << lr_bin_n[LA-1:0];
    for (genvar gi = 0; gi < NG; gi = gi + 1) begin : lgrp
        localparam integer LO = gi * GW, HI = (LO + GW > 281) ? 281 : LO + GW;
        if (RSEL != 0) begin : g_hot
            // one-hot select of this group, a separate physical register (kept hierarchy); reset = slot 0
            wire [LD-1:0] hot;
            ot_hdc_v41x_kreg #(.W(LD), .R(0)) u_sel (.clk(clk), .rst_n(1'b1),
                .d(c_rl ? lr_hot_n : {{(LD-1){1'b0}}, 1'b1}), .q(hot));
            // AND-OR mux as continuous assigns (an always @(*) loop over the storage array is not re-evaluated
            // on storage writes by every simulator: r8 bench CHAIN ph137000 timed out with it)
            wire [HI-LO-1:0] acc [0:LD];
            assign acc[0] = {(HI-LO){1'b0}};
            for (genvar e = 0; e < LD; e = e + 1) begin : g_or
                assign acc[e+1] = acc[e] | ({(HI-LO){hot[e]}} & lmem[e][HI-1:LO]);
            end
            // the group loads only when the presented word is free (!l_v || l_pop), as r5: an unconditional
            // load (r6) re-reads the slot AFTER the presented one while l_v is held, and the writer may refill
            // the presented slot once the read pointer passed it.  The enable uses this group's own kept copy
            // of l_v, so each enable cone drives one group (~29 flops), not the whole 281-bit word.
            wire vg;
            ot_hdc_v41x_kreg #(.W(1), .R(1)) u_vg (.clk(clk), .rst_n(c_rl),
                .d((MARGIN != 0) ? 1'b0 : (l_ren ? 1'b1 : (l_pop ? 1'b0 : vg))), .q(vg));
            // MARGIN: the group loads exactly on a push (an internal enable)
            always @(posedge clk) if ((MARGIN != 0) ? l_push : (!vg || l_pop)) l_q[HI-1:LO] <= acc[LD];
        end else begin : g_ix
            // RSEL = 0: the r5 structure (main), unchanged (r6's unconditional load is withdrawn: it presented the
            // slot after the held word)
            (* keep *) reg [LA-1:0] ix;
            (* keep *) reg          vg;
            always @(posedge clk or negedge c_rl)
                if (!c_rl) begin ix <= 0; vg <= 1'b0; end
                else begin ix <= lr_bin_n[LA-1:0]; if (l_ren) vg <= 1'b1; else if (l_pop) vg <= 1'b0; end
            wire [280:0] row = lmem[ix];
            always @(posedge clk) if ((MARGIN != 0) ? l_push : (!vg || l_pop)) l_q[HI-1:LO] <= row[HI-1:LO];
        end
    end
    always @(*) {l_sec, l_row, l_data} = l_q[280:0];

    // =========================== write queue: CLK -> HCLK ===========================
    reg [WA:0] ww_bin, ww_gray;                                   // CLK
    reg [WA:0] wh_bin, wc_bin, wc_gray;                           // HCLK: hand-off, completion
    (* async_reg = "true" *) reg [WA:0] ww_s [0:SYNC-1];          // ww_gray in HCLK
    (* async_reg = "true" *) reg [WA:0] wc_s [0:SYNC-1];          // wc_gray in CLK
    wire [WA:0] wc_sb = g2b_w(wc_s[SYNC-1]);
    wire        w_full = (ww_bin - wc_sb) == WB[WA:0];
    wire [WA:0] ww_bin_n = ww_bin + {{WA{1'b0}}, w_v_i && !w_full};
    always @(posedge clk or negedge c_rw) begin
        if (!c_rw) begin
            ww_bin <= 0; ww_gray <= 0; w_room <= 1'b0; c_fault <= 1'b0;
            for (s = 0; s < SYNC; s = s + 1) wc_s[s] <= 0;
        end else begin
            wc_s[0] <= wc_gray; for (s = 1; s < SYNC; s = s + 1) wc_s[s] <= wc_s[s-1];
            if (w_v_i && w_full) c_fault <= 1'b1;
            ww_bin <= ww_bin_n; ww_gray <= (ww_bin_n >> 1) ^ ww_bin_n;
            w_room <= (WB[WA:0] - (ww_bin_n - wc_sb)) >= ((MARGIN != 0) ? 4 : 3);
        end
    end
    // storage write: kept index copies per column group, not gated by the synchronized full flag (a push
    // into a full queue raises the sticky c_fault; the service checks w_room first)
    localparam integer WNG = 5, WW = 24 + 256 + TAGW, WGW = (WW + WNG - 1) / WNG;
    reg  [WW-1:0] wmem [0:WB-1];
    wire [WNG*WGW-1:0] w_in = {{(WNG*WGW-WW){1'b0}}, w_sec_i, w_data_i, w_tag_i};
    for (genvar gw = 0; gw < WNG; gw = gw + 1) begin : wwg
        localparam integer LO = gw * WGW, HI = (LO + WGW > WW) ? WW : LO + WGW;
        (* keep *) reg [WA-1:0] wi;
        always @(posedge clk or negedge c_rw) if (!c_rw) wi <= 0; else wi <= ww_bin_n[WA-1:0];
        always @(posedge clk) if (w_v_i) wmem[wi][HI-1:LO] <= w_in[HI-1:LO];
    end
    wire [WA:0] ww_sb = g2b_w(ww_s[SYNC-1]);
    wire [WA:0] wh_bin_n = wh_bin + {{WA{1'b0}}, h_hand};
    wire [WA:0] wc_bin_n = wc_bin + {{WA{1'b0}}, h_wcon};
    always @(posedge hclk or negedge h_rw) begin
        if (!h_rw) begin
            wh_bin <= 0; wc_bin <= 0; wc_gray <= 0; h_wv <= 1'b0; h_cv <= 1'b0;
            for (s = 0; s < SYNC; s = s + 1) ww_s[s] <= 0;
        end else begin
            ww_s[0] <= ww_gray; for (s = 1; s < SYNC; s = s + 1) ww_s[s] <= ww_s[s-1];
            wh_bin <= wh_bin_n; wc_bin <= wc_bin_n; wc_gray <= (wc_bin_n >> 1) ^ wc_bin_n;
            h_wv <= wh_bin_n != ww_sb;
            h_cv <= h_wcon;
        end
    end
    always @(posedge hclk) begin
        h_wsec <= wmem[wh_bin_n[WA-1:0]][WW-1 -: 24];
        if (h_wcon) begin
            h_csec <= wmem[wc_bin[WA-1:0]][WW-1 -: 24]; h_cdata <= wmem[wc_bin[WA-1:0]][TAGW +: 256]; h_ctag <= wmem[wc_bin[WA-1:0]][TAGW-1:0];
        end
    end

    // =========================== write-done: HCLK -> CLK ===========================
    reg [TAGW-1:0] amem [0:AD-1];
    reg [AA:0] aw_bin, aw_gray;                                   // HCLK
    reg [AA:0] ar_bin, ar_gray;                                   // CLK
    (* async_reg = "true" *) reg [AA:0] aw_s [0:SYNC-1];
    (* async_reg = "true" *) reg [AA:0] ar_s [0:SYNC-1];
    wire        a_full = (aw_bin - g2b_a(ar_s[SYNC-1])) == AD[AA:0];
    wire [AA:0] aw_bin_n = aw_bin + {{AA{1'b0}}, h_av_i && !a_full};
    always @(posedge hclk or negedge h_ra) begin
        if (!h_ra) begin
            aw_bin <= 0; aw_gray <= 0; h_fault <= 1'b0;
            for (s = 0; s < SYNC; s = s + 1) ar_s[s] <= 0;
        end else begin
            ar_s[0] <= ar_gray; for (s = 1; s < SYNC; s = s + 1) ar_s[s] <= ar_s[s-1];
            if ((h_lv_i && l_full) || (h_av_i && a_full) || (h_wcon && wc_bin == ww_sb)) h_fault <= 1'b1;
            aw_bin <= aw_bin_n; aw_gray <= (aw_bin_n >> 1) ^ aw_bin_n;
        end
    end
    always @(posedge hclk) if (h_av_i && !a_full) amem[aw_bin[AA-1:0]] <= h_atag_i;
    wire        a_ren = ar_gray != aw_s[SYNC-1];                  // wd_v is always taken
    wire [AA:0] ar_bin_n = ar_bin + {{AA{1'b0}}, a_ren};
    always @(posedge clk or negedge c_ra) begin
        if (!c_ra) begin
            ar_bin <= 0; ar_gray <= 0; wd_v <= 1'b0;
            for (s = 0; s < SYNC; s = s + 1) aw_s[s] <= 0;
        end else begin
            aw_s[0] <= aw_gray; for (s = 1; s < SYNC; s = s + 1) aw_s[s] <= aw_s[s-1];
            ar_bin <= ar_bin_n; ar_gray <= (ar_bin_n >> 1) ^ ar_bin_n;
            wd_v <= a_ren;
        end
    end
    always @(posedge clk) if (a_ren) wd_tag <= amem[ar_bin[AA-1:0]];
endmodule
