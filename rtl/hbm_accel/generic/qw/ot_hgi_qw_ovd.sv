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
// ovd split (Claude hbm-group-B r2, 2026-10-14): the data head ot_hgi_qw_ovd held TWO independent flows -- the gather
// (4 x 1,024-b lane-group pin registers -> OR4 -> decoder x, W/N/S-west -> E) and the result side (yc -> 64 x 512 SRAM ->
// write beats to the four lane-group rows).  They share no signal (only clk / rst_n), but the SRAM sat between the gather
// pins and x: its M2-M4 block left two ~44-um channels for >= 1,600 b (cut 0.75 > 0.60, qw_ovd_ref-w2 GRT 17,243 markers,
// el1013-hbm-quant-split 06:46).  The leaf is therefore two leaves with NO seam between them: ot_hgi_qw_ovg (gather, no
// macro) and ot_hgi_qw_ovs (result SRAM + write side).  Each pin-flops rst_n into its own relay of the same depth, so both
// release on the same edge as the one-leaf RTL (x_v / the write side / dec_rst_n unchanged).  No cycle is added or removed;
// every register is the one of the one-leaf RTL.
module ot_hgi_qw_ovg (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [1023:0]     l_gp0, l_gp1, l_gp2, l_gp3,
    input  wire              c_gv,
    input  wire [17:0]       c_gh,
    output reg               x_v,
    output reg  [17:0]       x_hd,
    output reg  [1023:0]     x
);
    reg f_rst; always @(posedge clk) f_rst <= rst_n;
    wire [0:0] rr_n;
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(f_rst), .rst_n(rr_n));
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) x_v <= 0; else x_v <= c_gv;   // x_v = the one-head 'launch'
    always @(posedge clk) x_hd <= c_gh;                                                   // x_hd = gh[6]
    reg [1023:0] gpf [0:3];
    always @(posedge clk) begin
        gpf[0] <= l_gp0; gpf[1] <= l_gp1; gpf[2] <= l_gp2; gpf[3] <= l_gp3;
        x <= (gpf[0] | gpf[1]) | (gpf[2] | gpf[3]);
    end
endmodule

module ot_hgi_qw_ovs #(
    parameter integer LQ = 16
) (
    input  wire          clk,
    input  wire          rst_n,
    // lane-group leaves
    // lane-group leaves, one port set a leaf row (each on the face toward its row; the write data has one kept copy a row)
    input  wire [7:0]        l_wcr0, l_wcr1, l_wcr2, l_wcr3,
    output wire [7:0]        l_wv0, l_wv1, l_wv2, l_wv3,
    output wire [8*15-1:0]   l_wsec0, l_wsec1, l_wsec2, l_wsec3,
    output wire [8*4-1:0]    l_ws0, l_ws1, l_ws2, l_ws3,
    output wire [511:0]      l_wy0, l_wy1, l_wy2, l_wy3,
    // control head
    input  wire              c_mw_v,
    input  wire [5:0]        c_mw_a,
    input  wire [14:0]       c_mw_sec,
    input  wire [2:0]        c_mw_n,
    input  wire              c_wg,        // control head: busy && write grant, registered
    output reg               d_wf,
    output reg               d_bad,
    // decoder tiles (parent level)
    output wire              dec_rst_n,
    input  wire              d_vo,
    input  wire              d_f,
    input  wire              d_df,
    input  wire [511:0]      d_y
);
    localparam integer OD = 64, OW = 6;         // = SRAM words
    localparam integer CW = $clog2(LQ + 1);
    reg f_rst; always @(posedge clk) f_rst <= rst_n;
    wire [2:0] rr_n;                            // 0 control, 1 counters / relays, 2 decoder tiles
    ot_rst_relay #(.REGIONS(3)) u_rst (.clk(clk), .rst_n_in(f_rst), .rst_n(rr_n));
    assign dec_rst_n = rr_n[2];
    function automatic [31:0] lanes(input [4:0] l0, input [2:0] nn);
        lanes = 0;
        for (integer j = 0; j < 4; j = j + 1) if (j < nn) lanes[5'(l0 + j)] = 1'b1;
    endfunction
    // ---------------------------------------------------------------- seam RX from the control head
    reg wg_ok, mw_v; reg [OW-1:0] mw_a; reg [14:0] mw_sec; reg [2:0] mw_n;
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin wg_ok <= 0; mw_v <= 0; end
        else begin wg_ok <= c_wg; mw_v <= c_mw_v; end
    always @(posedge clk) begin mw_a <= c_mw_a; mw_sec <= c_mw_sec; mw_n <= c_mw_n; end
    // ---------------------------------------------------------------- result capture, SRAM FIFO
    reg yc_v, yc_f, yc_df; reg [511:0] yc;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) begin yc_v <= 0; yc_f <= 0; yc_df <= 0; end
        else begin yc_v <= d_vo; yc_f <= d_vo && d_f; yc_df <= d_df; end
    always @(posedge clk) yc <= d_y;
    reg [14:0] mq_sec [0:OD-1]; reg [2:0] mq_n [0:OD-1];
    reg [OW-1:0] od_h, od_h1, od_t; reg [OW:0] od_n;           // od_h1 = od_h + 1 (registered)
    // write credits (take last cycle's hit vector)
    reg [31:0] ev_wcr, hit_w; reg [CW-1:0] wcr [0:31];
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) begin ev_wcr <= 0; for (integer b = 0; b < 32; b = b + 1) wcr[b] <= LQ[CW-1:0]; end
        else begin
            ev_wcr <= {l_wcr3, l_wcr2, l_wcr1, l_wcr0};
            for (integer b = 0; b < 32; b = b + 1) wcr[b] <= wcr[b] + CW'(ev_wcr[b]) - CW'(hit_w[b]);
        end
    // write head lookahead: hd_* = meta of entry od_h, re-read every edge for the next od_h.  Exact: an entry counts in od_n
    // only after its gather/decode/capture pipeline (>= 5 edges after its meta write), so mq is settled when hd reads it.
    reg [14:0] hd_sec; reg [2:0] hd_n; reg [31:0] hd_ln;
    wire [14:0] w_sec0 = hd_sec; wire [2:0] w_n = hd_n;
    reg [31:0] w_ok_l;
    always @* for (integer b = 0; b < 32; b = b + 1) w_ok_l[b] = wcr[b] > CW'(hit_w[b]);
    wire w_cr_ok = &(~hd_ln | w_ok_l);
    wire w_fire = !d_bad && wg_ok && od_n != 0 && w_cr_ok;   // wg_ok implies busy
    // B3 (ovs gate reg->reg -0.8 ps: od_n -> w_fire -> od_h + 1 -> 64:1 meta read -> lanes() -> hd_ln, 15 levels): both
    // candidate heads (od_h, od_h + 1) are read from REGISTERED pointers and decoded in parallel with the fire cone; the
    // fire only selects (one kept 2:1 per bit).  Same value every edge, no cycle.
    (* keep = 1 *) wire [14:0] c0_sec = mq_sec[od_h];  (* keep = 1 *) wire [2:0] c0_n = mq_n[od_h];
    (* keep = 1 *) wire [14:0] c1_sec = mq_sec[od_h1]; (* keep = 1 *) wire [2:0] c1_n = mq_n[od_h1];
    wire [31:0] c0_ln = lanes(c0_sec[4:0], c0_n), c1_ln = lanes(c1_sec[4:0], c1_n);
    always @(posedge clk) begin
        hd_sec <= w_fire ? c1_sec : c0_sec; hd_n <= w_fire ? c1_n : c0_n; hd_ln <= w_fire ? c1_ln : c0_ln;
        if (mw_v) begin mq_sec[mw_a] <= mw_sec; mq_n[mw_a] <= mw_n; end
    end
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin od_h <= 0; od_h1 <= 1; od_t <= 0; od_n <= 0; hit_w <= 0; d_bad <= 0; d_wf <= 0; end
        else begin
            hit_w <= w_fire ? hd_ln : 32'd0; d_wf <= w_fire;
            if (yc_v) begin od_t <= od_t + 1'b1; if (yc_f) d_bad <= 1'b1; end
            if (yc_df) d_bad <= 1'b1;
            od_n <= od_n + (OW+1)'(yc_v) - (OW+1)'(w_fire);
            if (w_fire) begin od_h <= od_h1; od_h1 <= od_h1 + 1'b1; end
        end
    // registered SRAM read issue (next to u_od): rf_* = w_fire / od_h / head meta one edge later
    reg rf_v; reg [OW-1:0] rf_a; reg [14:0] rf_sec; reg [2:0] rf_n;
    always @(posedge clk) begin rf_a <= od_h; rf_sec <= w_sec0; rf_n <= w_n; end
    wire [511:0] od_rd;
    ot_sram_1r1w_64x512_m1_r2c2 u_od (.clk(clk), .r_ce_in(rf_v), .r_addr_in(rf_a), .rd_out(od_rd),
        .w_ce_in(yc_v), .w_addr_in(od_t), .wd_in(yc), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    // write beat: capture the SRAM read, per-lane valid / slot / sector a cycle later, relay to the write quads
    (* keep *) reg [511:0] wc_y [0:3];           // one copy a leaf row (each ~400 um from this head: no shared 4-leaf net)
    reg wm_v; reg [14:0] wm_sec; reg [2:0] wm_n;
    reg [31:0] wv1; reg [3:0] ws1 [0:31]; reg [14:0] wsec1 [0:31];
    always @(posedge clk) begin
        for (integer r = 0; r < 4; r = r + 1) wc_y[r] <= od_rd;
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
    wire [32*4-1:0] ws_f; wire [32*15-1:0] wsec_f;
    genvar gi;
    generate for (gi = 0; gi < 32; gi = gi + 1) begin : g_lo
        assign ws_f[gi*4 +: 4] = ws1[gi]; assign wsec_f[gi*15 +: 15] = wsec1[gi];
    end endgenerate
    assign {l_wv3, l_wv2, l_wv1, l_wv0} = wv1;
    assign {l_ws3, l_ws2, l_ws1, l_ws0} = ws_f;
    assign {l_wsec3, l_wsec2, l_wsec1, l_wsec0} = wsec_f;
    assign l_wy0 = wc_y[0]; assign l_wy1 = wc_y[1]; assign l_wy2 = wc_y[2]; assign l_wy3 = wc_y[3];
    initial if ((LQ & (LQ - 1)) != 0) $fatal(1, "ot_hgi_qw_ovs: LQ");
endmodule
`default_nettype wire
