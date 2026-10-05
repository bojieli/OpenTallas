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
    parameter integer SYNC = 2              // synchronizer flops per crossing
) (
    // ---- CLK (core) domain ----
    input  wire             clk,
    input  wire             c_arst_n,
    output reg              l_v,
    output reg  [16:0]      l_sec,
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

    // local reset release, one synchronizer per domain
    (* async_reg = "true" *) reg [1:0] c_rs, h_rs;
    always @(posedge clk or negedge c_arst_n)  if (!c_arst_n) c_rs <= 2'b00; else c_rs <= {c_rs[0], 1'b1};
    always @(posedge hclk or negedge h_arst_n) if (!h_arst_n) h_rs <= 2'b00; else h_rs <= {h_rs[0], 1'b1};
    wire c_rst_n = c_rs[1], h_rst_n = h_rs[1];

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
    wire [LA:0] lw_bin_n = lw_bin + {{LA{1'b0}}, h_lv && !l_full};
    integer s;
    always @(posedge hclk or negedge h_rst_n) begin
        if (!h_rst_n) begin
            lw_bin <= 0; lw_gray <= 0; lr_seen <= 0; h_cred <= 0;
            for (s = 0; s < SYNC; s = s + 1) lr_s[s] <= 0;
        end else begin
            if (h_lv && !l_full) lmem[lw_bin[LA-1:0]] <= {h_lsec, h_lrow, h_ldata};
            lw_bin <= lw_bin_n; lw_gray <= (lw_bin_n >> 1) ^ lw_bin_n;
            lr_s[0] <= lr_gray; for (s = 1; s < SYNC; s = s + 1) lr_s[s] <= lr_s[s-1];
            h_cred <= 3'(lr_sb - lr_seen); lr_seen <= lr_sb;
        end
    end
    wire        l_empty = lr_gray == lw_s[SYNC-1];
    wire        l_ren   = !l_empty && (!l_v || l_pop);
    wire [LA:0] lr_bin_n = lr_bin + {{LA{1'b0}}, l_ren};
    always @(posedge clk or negedge c_rst_n) begin
        if (!c_rst_n) begin
            lr_bin <= 0; lr_gray <= 0; l_v <= 1'b0;
            for (s = 0; s < SYNC; s = s + 1) lw_s[s] <= 0;
        end else begin
            lw_s[0] <= lw_gray; for (s = 1; s < SYNC; s = s + 1) lw_s[s] <= lw_s[s-1];
            lr_bin <= lr_bin_n; lr_gray <= (lr_bin_n >> 1) ^ lr_bin_n;
            if (l_ren) l_v <= 1'b1; else if (l_pop) l_v <= 1'b0;
        end
    end
    always @(posedge clk) if (l_ren) {l_sec, l_row, l_data} <= lmem[lr_bin[LA-1:0]];

    // =========================== write queue: CLK -> HCLK ===========================
    reg [23:0]     wm_sec  [0:WB-1];
    reg [255:0]    wm_data [0:WB-1];
    reg [TAGW-1:0] wm_tag  [0:WB-1];
    reg [WA:0] ww_bin, ww_gray;                                   // CLK
    reg [WA:0] wh_bin, wc_bin, wc_gray;                           // HCLK: hand-off, completion
    (* async_reg = "true" *) reg [WA:0] ww_s [0:SYNC-1];          // ww_gray in HCLK
    (* async_reg = "true" *) reg [WA:0] wc_s [0:SYNC-1];          // wc_gray in CLK
    wire [WA:0] wc_sb = g2b_w(wc_s[SYNC-1]);
    wire        w_full = (ww_bin - wc_sb) == WB[WA:0];
    wire [WA:0] ww_bin_n = ww_bin + {{WA{1'b0}}, w_v && !w_full};
    always @(posedge clk or negedge c_rst_n) begin
        if (!c_rst_n) begin
            ww_bin <= 0; ww_gray <= 0; w_room <= 1'b0; c_fault <= 1'b0;
            for (s = 0; s < SYNC; s = s + 1) wc_s[s] <= 0;
        end else begin
            wc_s[0] <= wc_gray; for (s = 1; s < SYNC; s = s + 1) wc_s[s] <= wc_s[s-1];
            if (w_v && w_full) c_fault <= 1'b1;
            ww_bin <= ww_bin_n; ww_gray <= (ww_bin_n >> 1) ^ ww_bin_n;
            w_room <= (WB[WA:0] - (ww_bin_n - wc_sb)) >= 3;
        end
    end
    always @(posedge clk)
        if (w_v && !w_full) begin
            wm_sec[ww_bin[WA-1:0]] <= w_sec; wm_data[ww_bin[WA-1:0]] <= w_data; wm_tag[ww_bin[WA-1:0]] <= w_tag;
        end
    wire [WA:0] ww_sb = g2b_w(ww_s[SYNC-1]);
    wire [WA:0] wh_bin_n = wh_bin + {{WA{1'b0}}, h_hand};
    wire [WA:0] wc_bin_n = wc_bin + {{WA{1'b0}}, h_wcon};
    always @(posedge hclk or negedge h_rst_n) begin
        if (!h_rst_n) begin
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
        h_wsec <= wm_sec[wh_bin_n[WA-1:0]];
        if (h_wcon) begin
            h_csec <= wm_sec[wc_bin[WA-1:0]]; h_cdata <= wm_data[wc_bin[WA-1:0]]; h_ctag <= wm_tag[wc_bin[WA-1:0]];
        end
    end

    // =========================== write-done: HCLK -> CLK ===========================
    reg [TAGW-1:0] amem [0:AD-1];
    reg [AA:0] aw_bin, aw_gray;                                   // HCLK
    reg [AA:0] ar_bin, ar_gray;                                   // CLK
    (* async_reg = "true" *) reg [AA:0] aw_s [0:SYNC-1];
    (* async_reg = "true" *) reg [AA:0] ar_s [0:SYNC-1];
    wire        a_full = (aw_bin - g2b_a(ar_s[SYNC-1])) == AD[AA:0];
    wire [AA:0] aw_bin_n = aw_bin + {{AA{1'b0}}, h_av && !a_full};
    always @(posedge hclk or negedge h_rst_n) begin
        if (!h_rst_n) begin
            aw_bin <= 0; aw_gray <= 0; h_fault <= 1'b0;
            for (s = 0; s < SYNC; s = s + 1) ar_s[s] <= 0;
        end else begin
            ar_s[0] <= ar_gray; for (s = 1; s < SYNC; s = s + 1) ar_s[s] <= ar_s[s-1];
            if ((h_lv && l_full) || (h_av && a_full) || (h_wcon && wc_bin == ww_sb)) h_fault <= 1'b1;
            aw_bin <= aw_bin_n; aw_gray <= (aw_bin_n >> 1) ^ aw_bin_n;
        end
    end
    always @(posedge hclk) if (h_av && !a_full) amem[aw_bin[AA-1:0]] <= h_atag;
    wire        a_ren = ar_gray != aw_s[SYNC-1];                  // wd_v is always taken
    wire [AA:0] ar_bin_n = ar_bin + {{AA{1'b0}}, a_ren};
    always @(posedge clk or negedge c_rst_n) begin
        if (!c_rst_n) begin
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
