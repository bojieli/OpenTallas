`timescale 1ns/1ps
`default_nettype none
// DATA head leaf of the record-overlap quant cluster (el1013-hbm-quant-split, 2026-10-13): the wide half of the former
// head ot_hgi_qw_ovh (17.4k clock sinks, over the 15k rule).  Holds: the four gather pin registers gpf (one a lane-group
// leaf), the OR4 register lx (decoder x), the decode launch / header RX registers, the result capture yc, the result
// FIFO (64 x 512 SRAM) with its pointers, the per-beat meta FIFO, and the WHOLE write side: write credits, write-head
// lookahead, w_fire, SRAM read issue, the write beat registers to the lane-group leaves and the write grant.
// The decoder tiles (ot_hgi_qw_dec3 / ot_hgi_qw_dec) are children of the wires-only parent: lx / launch / gh6 are this
// leaf's output registers, yc / yc_v / yc_f / yc_df its input registers (the same registers as in the one-head RTL).
// Seam with the control head ot_hgi_qw_ovc: see that file.  No datapath cycle is added.
module ot_hgi_qw_ovd #(
    parameter integer LQ = 16
) (
    input  wire          clk,
    input  wire          rst_n,
    // lane-group leaves
    input  wire [4*1024-1:0] l_gp,
    input  wire [31:0]       l_wcr,
    output wire [31:0]       l_wv,
    output wire [32*15-1:0]  l_wsec,
    output wire [32*4-1:0]   l_ws,
    output wire [511:0]      l_wy,
    // control head
    input  wire              c_gv,
    input  wire [17:0]       c_gh,
    input  wire              c_mw_v,
    input  wire [5:0]        c_mw_a,
    input  wire [14:0]       c_mw_sec,
    input  wire [2:0]        c_mw_n,
    input  wire              c_busy,
    output reg               d_wf,
    output reg               d_bad,
    // decoder tiles (parent level)
    output wire              dec_rst_n,
    output reg               x_v,
    output reg  [17:0]       x_hd,
    output reg  [1023:0]     x,
    input  wire              d_vo,
    input  wire              d_f,
    input  wire              d_df,
    input  wire [511:0]      d_y,
    output reg               wg_req,
    input  wire              wg_gnt
);
    localparam integer OD = 64, OW = 6;         // = SRAM words
    localparam integer CW = $clog2(LQ + 1);
    reg f_rst, f_wg; always @(posedge clk) begin f_rst <= rst_n; f_wg <= wg_gnt; end
    wire [2:0] rr_n;                            // 0 control, 1 counters / relays, 2 decoder tiles
    ot_rst_relay #(.REGIONS(3)) u_rst (.clk(clk), .rst_n_in(f_rst), .rst_n(rr_n));
    assign dec_rst_n = rr_n[2];
    function automatic [31:0] lanes(input [4:0] l0, input [2:0] nn);
        lanes = 0;
        for (integer j = 0; j < 4; j = j + 1) if (j < nn) lanes[5'(l0 + j)] = 1'b1;
    endfunction
    // ---------------------------------------------------------------- seam RX from the control head
    reg busy, mw_v; reg [OW-1:0] mw_a; reg [14:0] mw_sec; reg [2:0] mw_n;
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin busy <= 0; mw_v <= 0; x_v <= 0; end
        else begin busy <= c_busy; mw_v <= c_mw_v; x_v <= c_gv; end      // x_v = the one-head 'launch'
    always @(posedge clk) begin mw_a <= c_mw_a; mw_sec <= c_mw_sec; mw_n <= c_mw_n; x_hd <= c_gh; end   // x_hd = gh[6]
    // ---------------------------------------------------------------- gather tail: one pure pin register a leaf, then OR4
    reg [1023:0] gpf [0:3];
    always @(posedge clk) begin
        for (integer h = 0; h < 4; h = h + 1) gpf[h] <= l_gp[h*1024 +: 1024];
        x <= (gpf[0] | gpf[1]) | (gpf[2] | gpf[3]);
    end
    // ---------------------------------------------------------------- result capture, SRAM FIFO
    reg yc_v, yc_f, yc_df; reg [511:0] yc;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) begin yc_v <= 0; yc_f <= 0; yc_df <= 0; end
        else begin yc_v <= d_vo; yc_f <= d_vo && d_f; yc_df <= d_df; end
    always @(posedge clk) yc <= d_y;
    reg [14:0] mq_sec [0:OD-1]; reg [2:0] mq_n [0:OD-1];
    reg [OW-1:0] od_h, od_t; reg [OW:0] od_n;
    reg wg_ok;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) begin wg_ok <= 0; wg_req <= 0; end
        else begin wg_ok <= busy && f_wg; wg_req <= busy; end
    // write credits (take last cycle's hit vector)
    reg [31:0] ev_wcr, hit_w; reg [CW-1:0] wcr [0:31];
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) begin ev_wcr <= 0; for (integer b = 0; b < 32; b = b + 1) wcr[b] <= LQ[CW-1:0]; end
        else begin
            ev_wcr <= l_wcr;
            for (integer b = 0; b < 32; b = b + 1) wcr[b] <= wcr[b] + CW'(ev_wcr[b]) - CW'(hit_w[b]);
        end
    // write head lookahead: hd_* = meta of entry od_h, re-read every edge for the next od_h.  Exact: an entry counts in od_n
    // only after its gather/decode/capture pipeline (>= 5 edges after its meta write), so mq is settled when hd reads it.
    reg [14:0] hd_sec; reg [2:0] hd_n; reg [31:0] hd_ln;
    wire [14:0] w_sec0 = hd_sec; wire [2:0] w_n = hd_n;
    reg [31:0] w_ok_l;
    always @* for (integer b = 0; b < 32; b = b + 1) w_ok_l[b] = wcr[b] > CW'(hit_w[b]);
    wire w_cr_ok = &(~hd_ln | w_ok_l);
    wire w_fire = busy && !d_bad && wg_ok && od_n != 0 && w_cr_ok;
    wire [OW-1:0] od_hn = w_fire ? od_h + 1'b1 : od_h;
    always @(posedge clk) begin
        hd_sec <= mq_sec[od_hn]; hd_n <= mq_n[od_hn]; hd_ln <= lanes(mq_sec[od_hn][4:0], mq_n[od_hn]);
        if (mw_v) begin mq_sec[mw_a] <= mw_sec; mq_n[mw_a] <= mw_n; end
    end
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin od_h <= 0; od_t <= 0; od_n <= 0; hit_w <= 0; d_bad <= 0; d_wf <= 0; end
        else begin
            hit_w <= w_fire ? hd_ln : 32'd0; d_wf <= w_fire;
            if (yc_v) begin od_t <= od_t + 1'b1; if (yc_f) d_bad <= 1'b1; end
            if (yc_df) d_bad <= 1'b1;
            od_n <= od_n + (OW+1)'(yc_v) - (OW+1)'(w_fire);
            if (w_fire) od_h <= od_h + 1'b1;
        end
    // registered SRAM read issue (next to u_od): rf_* = w_fire / od_h / head meta one edge later
    reg rf_v; reg [OW-1:0] rf_a; reg [14:0] rf_sec; reg [2:0] rf_n;
    always @(posedge clk) begin rf_a <= od_h; rf_sec <= w_sec0; rf_n <= w_n; end
    wire [511:0] od_rd;
    ot_sram_1r1w_64x512_m1_r2c2 u_od (.clk(clk), .r_ce_in(rf_v), .r_addr_in(rf_a), .rd_out(od_rd),
        .w_ce_in(yc_v), .w_addr_in(od_t), .wd_in(yc), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    // write beat: capture the SRAM read, per-lane valid / slot / sector a cycle later, relay to the write quads
    reg [511:0] wc_y; reg wm_v; reg [14:0] wm_sec; reg [2:0] wm_n;
    reg [31:0] wv1; reg [3:0] ws1 [0:31]; reg [14:0] wsec1 [0:31];
    always @(posedge clk) begin
        wc_y <= od_rd;
        wm_sec <= rf_sec; wm_n <= rf_n;
        for (integer b = 0; b < 32; b = b + 1) begin
            ws1[b] <= 4'(1) << 2'(b - wm_sec[4:0]); wsec1[b] <= wm_sec + 15'(5'(b - wm_sec[4:0]));
        end
    end
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) begin rf_v <= 0; wm_v <= 0; wv1 <= 0; end
        else begin
            rf_v <= w_fire; wm_v <= rf_v;
            for (integer b = 0; b < 32; b = b + 1) wv1[b] <= wm_v && (5'(b - wm_sec[4:0]) < 5'(wm_n));
        end
    genvar gi;
    generate for (gi = 0; gi < 32; gi = gi + 1) begin : g_lo
        assign l_ws[gi*4 +: 4] = ws1[gi]; assign l_wsec[gi*15 +: 15] = wsec1[gi];
    end endgenerate
    assign l_wv = wv1; assign l_wy = wc_y;
    initial if ((LQ & (LQ - 1)) != 0) $fatal(1, "ot_hgi_qw_ovd: LQ");
endmodule
`default_nettype wire
