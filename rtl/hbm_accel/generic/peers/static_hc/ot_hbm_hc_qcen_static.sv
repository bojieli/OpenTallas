`timescale 1ns/1ps
`default_nettype none
// HC quarter-engine CENTRE (HBM-B-RTL2, plan (b) d4g, 2026-10-17): the control and reduction half of
// ot_hbm_hc_qeng_static that sits in the hole of the 3x3 bank ring, inside ot_hbm_hc_qhub_static beside hc_<q>.
//   rx       control-only x_wave beat receiver (v / beat / word: the data beats go from hc_<q> straight to the banks,
//            ot_hbm_hc_bankq_*): same pin flops, order check and wave_v edge as ot_hbm_hc_xw_rx_static.
//   ingest   the quarter's ingest sequencer, unchanged; it drives the bank write control {wv, xv, j, wa} (13 b) on four
//            kept per-face copies (W: bank 0; N: bank 2 + corner feeds 1, 3; E: bank 4; S: bank 6 + feeds 5, 7).
//   desc     the per-task descriptor relay (DRLY registers) to bank 0.
//   tree     the 6-level pairwise subtree over the 64 chunk sums arriving from bank 0's chain-exit relay (s_i), bit
//            for bit the aligned 64-leaf subtree of the 256-leaf csum tree (as ot_hbm_hc_qeng_static).
//   reset    ot_rst_relay, 9 regions: rst_b[k] -> bank k (each bank relays again), region 8 = this centre.
//   fault    sticky: rx order, ingest (unsolicited / missing / wrong word / bad event), any bank's residual check.
// MUT (bench): 3 = x landing one run off, 4 = tree level-1 pairs (0,2),(1,3).
// W (HBM-HC 2026-10-24, default 64 = unchanged, bit for bit): lanes of this hub's slice of every W = 256 run.  W 128 =
// the B2 8-SM die HALF hub (root ot_hbm_hc_root_static NQ 2, TPRE 7): 8 widened W 128 bank tiles, the 7-level aligned
// subtree over 128 chunk sums (= (q_2h + q_2h+1) of the 4-quarter form: the SAME pairs in the SAME order, no numerics
// change), 8-bit lane count d_nv, 6-bit half-local wave index i_w (< K/512 a row / position: run i_w / 4, slice
// i_w % 4), 2-bit write slice j (wc_* 14 b), 4,097-bit chain exit s_i.  Bench mutants: MUT 5 = level-1 pairs (i, i + W/2)
// (a reordered accumulation, e.g. a 128-lane run folded onto a 64-lane tree), MUT 6 = write slice j = i_w[0] only (wrong
// j), MUT 7 = top tree level dropped (the left subtree sum is output).
module ot_hbm_hc_qcen_static #(
    parameter integer K    = 20480,
    parameter integer DRLY = 1,
    parameter integer TLA  = 7,
    parameter integer CHX  = 0,     // HH-9 10-19: extra chain edges (bank chain pin registers, ot_hbm_hc_qeng_static CPR)
    parameter integer MUT  = 0,
    parameter integer W    = 64,    // 64 (quarter hub, as built) or 128 (B2 half hub)
    // derived (do not override)
    parameter integer NVW  = (W == 128) ? 8 : 7,
    parameter integer IWW  = (W == 128) ? 6 : 5,
    parameter integer JW   = (W == 128) ? 2 : 1
)(
    input  wire           clk, rst_n,
    input  wire           d_v, d_ss, input wire [NVW-1:0] d_nv, input wire [9:0] d_wa, d_xa,
    input  wire           i_v, i_kind, input wire [1:0] i_slot, input wire [4:0] i_lo, input wire [IWW-1:0] i_w,
    input  wire [11:0]    i_cnt, input wire [9:0] i_word,
    input  wire           x_v, input wire [1:0] x_beat, input wire [9:0] x_word,
    input  wire [W*32:0]  s_i,                       // {lane fault, W chunk sums} from bank 0's exit relay
    input  wire [7:0]     wfault_i,
    output wire [7:0]     rst_b,
    output wire           bd_v, bd_ss, output wire [NVW-1:0] bd_nv, output wire [9:0] bd_wa, bd_xa,
    output wire [11+JW:0] wc_w, wc_n, wc_e, wc_s,   // {wv, xv, j[JW-1:0], wa[9:0]}
    output reg            ps_v, output reg [31:0] ps, output reg ps_f,
    output reg            fault
);
    localparam integer AW = 10, R = K / 2048, WPRQ = K * W / 65536, NJ = W / 32;
    localparam integer LM = 8, LA = 7, SOR = 1, ML = 2, LT = (W == 128) ? 7 : 6;
    localparam integer SB = 1 + 7 * (LA + 1 + SOR) + 3 + 2 + (ML - 2) + LM + LA + SOR;
    initial if (K % 2048 != 0 || R > 16 || WPRQ > (1 << IWW)) $fatal(1, "K must be a multiple of 2,048, <= 32,768");
    initial if (!((W == 64 && NVW == 7 && IWW == 5 && JW == 1) || (W == 128 && NVW == 8 && IWW == 6 && JW == 2)))
        $fatal(1, "W must be 64 or 128 (NVW / IWW / JW are derived)");

    wire [8:0] rn;
    ot_rst_relay #(.REGIONS(9)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rn));
    wire rc = rn[8];
    assign rst_b = rn[7:0];

    // pin registers
    reg dv_q, dss_q; reg [NVW-1:0] dnv_q; reg [9:0] dwa_q, dxa_q;
    reg iv_q, ik_q; reg [1:0] is_q; reg [4:0] ilo_q; reg [IWW-1:0] iw_q; reg [11:0] ic_q; reg [9:0] iwd_q; reg [7:0] wf_q;
    always @(posedge clk or negedge rc)
        if (!rc) begin dv_q <= 1'b0; iv_q <= 1'b0; wf_q <= 8'd0; end
        else begin dv_q <= d_v; iv_q <= i_v; wf_q <= wfault_i; end
    always @(posedge clk) begin
        dss_q <= d_ss; dnv_q <= d_nv; dwa_q <= d_wa; dxa_q <= d_xa;
        ik_q <= i_kind; is_q <= i_slot; ilo_q <= i_lo; iw_q <= i_w; ic_q <= i_cnt; iwd_q <= i_word;
    end
    // rx, control only (ot_hbm_hc_xw_rx_static BEATS 4 without the data)
    reg v_q; reg [1:0] b_q; reg [9:0] w_q; reg [1:0] nxt; reg [9:0] hw; reg rx_fault;
    always @(posedge clk or negedge rc) if (!rc) v_q <= 1'b0; else v_q <= x_v;
    always @(posedge clk) begin b_q <= x_beat; w_q <= x_word; if (v_q && b_q != 2'd3) hw <= w_q; end
    always @(posedge clk or negedge rc)
        if (!rc) begin nxt <= 2'd0; rx_fault <= 1'b0; end
        else if (v_q) begin
            if (b_q != nxt || (b_q != 2'd0 && w_q != hw)) rx_fault <= 1'b1;
            nxt <= b_q + 2'd1;
        end else if (nxt != 2'd0) rx_fault <= 1'b1;
    wire xv_q = v_q && b_q == 2'd3;
    wire [9:0] xw_q = w_q;

    // ingest sequencer (as ot_hbm_hc_qeng_static; the residual low-half check moved into the banks)
    reg in_act, in_kind; reg [1:0] in_ph, in_slot; reg [4:0] in_lo; reg [IWW-1:0] in_w; reg [11:0] in_left; reg [9:0] in_word;
    wire due = in_act && in_ph == 2'd0;
    wire [3:0] drun = 4'(in_w / NJ);
    wire [JW-1:0] dj = (MUT == 6) ? JW'(in_w[0]) : in_w[JW-1:0];
    wire [9:0] dxaddr = 10'(in_lo * R + drun + ((MUT == 3) ? 1 : 0));
    wire [9:0] dwaddr = 10'(in_slot * 256 + in_lo * R + drun);
    reg ing_fault;
    (* keep = "true" *) reg [3:0] c_wv, c_xv; (* keep = "true" *) reg [JW-1:0] c_j [0:3]; (* keep = "true" *) reg [9:0] c_a [0:3];
    always @(posedge clk or negedge rc) begin
        if (!rc) begin in_act <= 0; in_ph <= 0; c_wv <= 0; c_xv <= 0; ing_fault <= 0; end
        else begin
            c_wv <= {4{due && in_kind}}; c_xv <= {4{due && !in_kind}};
            if (xv_q && !due) ing_fault <= 1'b1;
            if (due) begin
                if (!xv_q || xw_q != in_word) ing_fault <= 1'b1;
                in_word <= in_word + 1'b1;
                in_left <= in_left - 1'b1;
                if (in_left == 12'd1) in_act <= 1'b0;
                if (in_w == IWW'(WPRQ - 1)) begin
                    in_w <= {IWW{1'b0}};
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
    always @(posedge clk) begin
        for (integer f = 0; f < 4; f = f + 1) begin c_j[f] <= dj; c_a[f] <= in_kind ? dwaddr : dxaddr; end
    end
    assign wc_w = {c_wv[0], c_xv[0], c_j[0], c_a[0]};
    assign wc_n = {c_wv[1], c_xv[1], c_j[1], c_a[1]};
    assign wc_e = {c_wv[2], c_xv[2], c_j[2], c_a[2]};
    assign wc_s = {c_wv[3], c_xv[3], c_j[3], c_a[3]};

    // descriptor relay to bank 0
    localparam integer DW = 2 + NVW + 2 * AW;
    wire [DW-1:0] d_in = {dv_q, dss_q, dnv_q, dwa_q, dxa_q};
    reg [DW-1:0] dr [0:DRLY-1];
    always @(posedge clk) begin
        dr[0] <= d_in;
        for (integer i = 1; i < DRLY; i = i + 1) dr[i] <= dr[i-1];
    end
    assign {bd_v, bd_ss, bd_nv, bd_wa, bd_xa} = dr[DRLY-1];

    // LT-level subtree (6 at W 64, 7 at W 128) over the chunk sums of the task whose valid entered bank 0 SB + DRLY edges ago
    localparam integer VD = SB + DRLY + CHX;
    reg [VD-1:0] vl;
    always @(posedge clk or negedge rc) if (!rc) vl <= 0; else vl <= {vl[VD-2:0], bd_v};
    wire leaf_v = vl[VD-1];
    wire [W*32-1:0] lv0;
    for (genvar i = 0; i < W; i = i + 1) begin : g_perm
        localparam integer SRC = (MUT == 4) ? ((i & ~3) | ((i & 1) << 1) | ((i >> 1) & 1)) :
                                 (MUT == 5) ? ((i % 2) * (W / 2) + i / 2) : i;
        assign lv0[i*32 +: 32] = s_i[SRC*32 +: 32];
    end
    wire [(W-1)*32-1:0] nd; wire [W-2:0] nv, ne;
    for (genvar l = 1; l <= LT; l = l + 1) begin : g_lvl
        localparam integer N = W >> l, OFF = W - ((2*W) >> l), POFF = W - ((4*W) >> l);
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
    localparam integer RT = (MUT == 7) ? W - 4 : W - 2;   // MUT 7 (bench): top level dropped (left subtree out)
    reg [LT*TLA-1:0] lfd;
    always @(posedge clk or negedge rc) if (!rc) lfd <= 0; else lfd <= {lfd[LT*TLA-2:0], s_i[W*32] && leaf_v};
    always @(posedge clk or negedge rc) begin
        if (!rc) begin ps_v <= 1'b0; ps_f <= 1'b0; fault <= 1'b0; end
        else begin
            ps_v <= nv[RT];
            ps_f <= lfd[LT*TLA-1] || (|ne);
            if (ing_fault || rx_fault || (|wf_q)) fault <= 1'b1;
        end
    end
    always @(posedge clk) ps <= nd[RT*32 +: 32];
endmodule
`default_nettype wire
