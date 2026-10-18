`timescale 1ns/1ps
`default_nettype none
// Static HC QUARTER engine (HBM-B-RTL2, plan (b) d4g, 2026-10-17): one per quadrant (hc_eng_<q>, one master, x4),
// beside the quadrant's hc_<q> LG client.  It is the projection datapath of ot_hbm_hc_eng_static cut by the hidden
// dimension: quarter q owns lanes 64q .. 64q+63 of every W = 256 run, i.e. chunks r*256 + 64q + i (i = 0..63,
// r = 0..R-1) of the K = 20,480 vector (K/4 = 5,120 terms per quarter).  The root ot_hbm_hc_root_static keeps the
// programme, the HCP issue/scalar core, the mix store, the table and the tails.
//   BANKS   8 x ot_hbm_hc_bank_static #(W = 64) (term k of every 8-term chunk; 8 hard lane leaves, 8 weight + 4 x
//           macros each), chained 0 -> 7 exactly as in the full engine (csum chunk order ((0+t0)+t1)..+t7 kept).
//           Physically a SQUARE RING of the 8 bank tiles (3 x 3, centre = ingress + tree): bank 0 and bank 7 both sit
//           beside the centre, so the descriptor entry and the chunk-sum exit are short.
//   TREE    the first 6 levels of the csum pairwise chunk tree over the quarter's 64 chunk sums (ot_hdc_fp32_add_lat,
//           TLA stages a level, bit for bit the core's ot_hdc_fp32_add_fast): the result is the aligned 64-chunk
//           subtree sum, one binary32 a task, that the root's core (TPRE = 6) combines with the other 3 quarters'
//           ((q0 + q1) + (q2 + q3)) -- the same pairs as the 256-leaf tree, so every run sum is bit-identical.
//   INGRESS one x_wave port (this quadrant's hc_<q> reader, XW_BEATS = 4 beats of 2,048 b, ot_hbm_hc_xw_rx_static).
//           A quarter wave lw (lw = 0 .. K/1024 - 1 per row / position) carries quarter chunks 32 lw .. 32 lw + 31 =
//           run lw/2, lanes 32 (lw%2) .. +31 (global chunk r*256 + 64q + 32(lw%2) + m).  The 4 quarters land waves
//           in parallel (no cross-quadrant phase stagger any more: each quarter has its own bank write port).
// The ingest event (from the root programme, pin flops here) and the per-task descriptor (from the root core's tap 0,
// pin flops here) are the only inputs from the root; the 32-b subtree sum (+ valid + lane/tree fault) the only output.
// STATIC: no ready, credit or backpressure.  fault (sticky): a wave missing on its due edge, an unsolicited wave, a
// wrong word index, a residual word with nonzero low half, an overlapping ingest event, a bad event field, a beat
// error.  Pin registers: every input lands in a pin flop, every output is a flop.  rst_n: ot_rst_relay (sync release,
// one region per bank tile + centre); each bank tile relays it again at its own boundary (RST_RELAY 1).
// MUT (bench): 1 = bank 3 weight slice rotated, 3 = x landing one run off, 4 = tree level-1 pairs (0,2),(1,3)
// instead of (0,1),(2,3) (reduction order changed).
module ot_hbm_hc_qeng_static #(
    parameter integer K    = 20480,
    parameter integer DRLY = 1,                  // relay registers centre <-> bank 0 / bank 7
    parameter integer TLA  = 7,                  // tree adder stages (1.2 GHz pipelined binary32 add)
    parameter integer XW_BEATS = 4,
    parameter integer MUT  = 0
)(
    input  wire           clk, rst_n,
    // per-task descriptor from the root core (quarter lane count already clamped by the root)
    input  wire           d_v, d_ss,
    input  wire [6:0]     d_nv,
    input  wire [9:0]     d_wa, d_xa,
    // ingest event from the root programme
    input  wire           i_v, i_kind,
    input  wire [1:0]     i_slot,
    input  wire [4:0]     i_lo,
    input  wire [4:0]     i_w,
    input  wire [11:0]    i_cnt,
    input  wire [9:0]     i_word,
    // this quadrant's x_wave link (hc_<q>)
    input  wire           x_wave_v,
    input  wire [1:0]     x_wave_beat,
    input  wire [9:0]     x_wave_word,
    input  wire [8192/XW_BEATS-1:0] x_wave,
    // subtree sum to the root
    output reg            ps_v,
    output reg  [31:0]    ps,
    output reg            ps_f,
    output reg            fault
);
    localparam integer W = 64, AW = 10, R = K / 2048, WPRQ = K / 1024, NJ = W / 32;
    localparam integer LM = 8, LA = 7, SOR = 1, ML = 2, NVW = 7, LT = 6;
    // bank 0 input -> bank 7 sum_out (the full engine's SYS_LAT - 2 DRLY)
    localparam integer SB = 1 + 7 * (LA + 1 + SOR) + 3 + 2 + (ML - 2) + LM + LA + SOR;
    initial if (K % 2048 != 0 || R > 16 || WPRQ > 32) $fatal(1, "K must be a multiple of 2,048, <= 32,768");

    // ------------------------------------------------------------------ synced reset (9 regions: 8 banks + centre)
    wire [8:0] rn;
    ot_rst_relay #(.REGIONS(9)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rn));
    wire rc = rn[8];

    // ------------------------------------------------------------------ pin registers
    reg dv_q, dss_q; reg [6:0] dnv_q; reg [9:0] dwa_q, dxa_q;
    reg iv_q, ik_q; reg [1:0] is_q; reg [4:0] ilo_q, iw_q; reg [11:0] ic_q; reg [9:0] iwd_q;
    always @(posedge clk or negedge rc)
        if (!rc) begin dv_q <= 1'b0; iv_q <= 1'b0; end else begin dv_q <= d_v; iv_q <= i_v; end
    always @(posedge clk) begin
        dss_q <= d_ss; dnv_q <= d_nv; dwa_q <= d_wa; dxa_q <= d_xa;
        ik_q <= i_kind; is_q <= i_slot; ilo_q <= i_lo; iw_q <= i_w; ic_q <= i_cnt; iwd_q <= i_word;
    end
    wire xv_q; wire [9:0] xw_q; wire [8191:0] xd_q; wire rx_fault;
    ot_hbm_hc_xw_rx_static #(.BEATS(XW_BEATS)) u_rx (.clk(clk), .rst_n(rc), .x_v(x_wave_v), .x_beat(x_wave_beat),
        .x_word(x_wave_word), .x_data(x_wave), .wave_v(xv_q), .wave_word(xw_q), .wave(xd_q), .fault(rx_fault));

    // ------------------------------------------------------------------ ingest sequencer (this quadrant)
    reg in_act, in_kind; reg [1:0] in_ph, in_slot; reg [4:0] in_lo, in_w; reg [11:0] in_left; reg [9:0] in_word;
    wire due = in_act && in_ph == 2'd0;
    wire [3:0] drun = 4'(in_w / NJ);
    wire dj = in_w[0];
    wire [9:0] dxaddr = 10'(in_lo * R + drun + ((MUT == 3) ? 1 : 0));
    wire [9:0] dwaddr = 10'(in_slot * 256 + in_lo * R + drun);
    reg lowbad;
    always @* begin
        lowbad = 1'b0;
        for (integer m = 0; m < 256; m = m + 1) lowbad = lowbad | (|xd_q[m*32 +: 16]);
    end
    reg b_wv, b_xv, b_j; reg [9:0] b_a; reg [8191:0] b_d; reg ing_fault;
    always @(posedge clk or negedge rc) begin
        if (!rc) begin in_act <= 0; in_ph <= 0; b_wv <= 0; b_xv <= 0; ing_fault <= 0; end
        else begin
            b_wv <= due && in_kind; b_xv <= due && !in_kind;
            if (xv_q && !due) ing_fault <= 1'b1;                                    // unsolicited wave
            if (due) begin
                if (!xv_q || xw_q != in_word) ing_fault <= 1'b1;
                if (!in_kind && lowbad) ing_fault <= 1'b1;                          // residual must be BF16-valued
                in_word <= in_word + 1'b1;
                in_left <= in_left - 1'b1;
                if (in_left == 12'd1) in_act <= 1'b0;
                if (in_w == 5'(WPRQ - 1)) begin
                    in_w <= 5'd0;
                    if (in_kind && in_lo == 5'd23) begin in_lo <= 5'd0; in_slot <= in_slot + 1'b1; end
                    else in_lo <= in_lo + 1'b1;
                end else in_w <= in_w + 1'b1;
            end
            if (in_act) in_ph <= in_ph + 1'b1;
            if (iv_q) begin
                if (in_act || ic_q == 0 || iw_q >= WPRQ || ilo_q >= (ik_q ? 24 : 8)) ing_fault <= 1'b1;
                in_act <= 1'b1; in_kind <= ik_q; in_ph <= 2'd0; in_slot <= is_q; in_lo <= ilo_q; in_w <= iw_q;
                in_left <= ic_q; in_word <= iwd_q;
            end
        end
    end
    always @(posedge clk) begin b_j <= dj; b_a <= in_kind ? dwaddr : dxaddr; b_d <= xd_q; end

    // ------------------------------------------------------------------ bank ring (chain 0 -> 7)
    localparam integer DW = 2 + NVW + 2 * AW;
    wire [DW-1:0] d_in = {dv_q, dss_q, dnv_q, dwa_q, dxa_q};
    wire [DW-1:0] d_rel; wire [W*32:0] s_src, s_rel;
    if (DRLY == 0) begin : g_nor
        assign d_rel = d_in; assign s_rel = s_src;
    end else begin : g_rel
        reg [DW-1:0] dr [0:DRLY-1]; reg [W*32:0] sr [0:DRLY-1];
        always @(posedge clk) begin
            dr[0] <= d_in; sr[0] <= s_src;
            for (integer i = 1; i < DRLY; i = i + 1) begin dr[i] <= dr[i-1]; sr[i] <= sr[i-1]; end
        end
        assign d_rel = dr[DRLY-1]; assign s_rel = sr[DRLY-1];
    end
    wire [8:0] cv, css, cf; wire [9*NVW-1:0] cnv; wire [9*AW-1:0] cwa, cxa; wire [9*W*32-1:0] csum;
    assign {cv[0], css[0], cnv[0 +: NVW], cwa[0 +: AW], cxa[0 +: AW]} = d_rel;
    assign csum[0 +: W*32] = {(W*32){1'b0}}; assign cf[0] = 1'b0;
    assign s_src = {cf[8], csum[8*W*32 +: W*32]};
    genvar gk;
    for (gk = 0; gk < 8; gk = gk + 1) begin : g_bank
        ot_hbm_hc_bank_static #(.W(W), .AW(AW), .LM(LM), .LA(LA), .MUT((MUT == 1 && gk == 3) ? 1 : 0), .RST_RELAY(1)) u_b (
            .clk(clk), .rst_n(rn[gk]), .first(gk == 0),
            .d_v(cv[gk]), .d_ss(css[gk]), .d_nv(cnv[gk*NVW +: NVW]), .d_wa(cwa[gk*AW +: AW]), .d_xa(cxa[gk*AW +: AW]),
            .o_v(cv[gk+1]), .o_ss(css[gk+1]), .o_nv(cnv[(gk+1)*NVW +: NVW]), .o_wa(cwa[(gk+1)*AW +: AW]),
            .o_xa(cxa[(gk+1)*AW +: AW]), .sum_in(csum[gk*W*32 +: W*32]), .sum_out(csum[(gk+1)*W*32 +: W*32]),
            .f_in(cf[gk]), .f_out(cf[gk+1]),
            .wv(b_wv), .xv(b_xv), .j(b_j), .wa(b_a), .wd(bank_slice(b_d, gk)));
    end
    function automatic [1023:0] bank_slice(input [8191:0] d, input integer k);
        for (integer m = 0; m < 32; m = m + 1) bank_slice[m*32 +: 32] = d[m*256 + k*32 +: 32];
    endfunction

    // ------------------------------------------------------------------ 6-level subtree of the csum chunk tree
    // valid of the task whose chunk sums are on s_rel now (bank 0 input + SB + DRLY)
    localparam integer VD = SB + DRLY;
    reg [VD-1:0] vl;
    always @(posedge clk or negedge rc) if (!rc) vl <= 0; else vl <= {vl[VD-2:0], cv[0]};
    wire leaf_v = vl[VD-1];
    wire [64*32-1:0] lv0;
    // MUT 4: level-1 pairs (0,2),(1,3) within each group of 4 (association changed)
    for (genvar i = 0; i < 64; i = i + 1) begin : g_perm
        localparam integer SRC = (MUT == 4) ? ((i & ~3) | ((i & 1) << 1) | ((i >> 1) & 1)) : i;
        assign lv0[i*32 +: 32] = s_rel[SRC*32 +: 32];
    end
    // nodes: level l (1..6) holds 64 >> l nodes at flat index OFF(l) + i, OFF(l) = 64 - (128 >> l); root = node 62
    wire [63*32-1:0] nd; wire [62:0] nv, ne;
    for (genvar l = 1; l <= LT; l = l + 1) begin : g_lvl
        localparam integer N = 64 >> l, OFF = 64 - (128 >> l), POFF = 64 - (256 >> l);
        for (genvar i = 0; i < N; i = i + 1) begin : g_n
            wire [31:0] a, b; wire va; wire [1:0] e;
            if (l == 1) begin : g_leaf
                assign a = lv0[(2*i)*32 +: 32]; assign b = lv0[(2*i+1)*32 +: 32]; assign va = leaf_v;
            end else begin : g_up
                assign a = nd[(POFF + 2*i)*32 +: 32]; assign b = nd[(POFF + 2*i + 1)*32 +: 32]; assign va = nv[POFF + 2*i];
            end
            ot_hdc_fp32_add_lat #(.LAT(TLA), .DRST(0)) u_a (.clk(clk), .rst_n(rc), .valid_in(va), .a(a), .b(b),
                .y(nd[(OFF + i)*32 +: 32]), .err(e), .valid_out(nv[OFF + i]));
            assign ne[OFF + i] = nv[OFF + i] && (|e);
        end
    end
    localparam integer RT = 62;
    // lane fault of the task, delayed to the tree output
    reg [LT*TLA-1:0] lfd;
    always @(posedge clk or negedge rc) if (!rc) lfd <= 0; else lfd <= {lfd[LT*TLA-2:0], s_rel[W*32] && leaf_v};

    // ------------------------------------------------------------------ output pin flops + status
    always @(posedge clk or negedge rc) begin
        if (!rc) begin ps_v <= 1'b0; ps_f <= 1'b0; fault <= 1'b0; end
        else begin
            ps_v <= nv[RT];
            ps_f <= lfd[LT*TLA-1] || (|ne);
            if (ing_fault || rx_fault) fault <= 1'b1;
        end
    end
    always @(posedge clk) ps <= nd[RT*32 +: 32];
endmodule
`default_nettype wire
