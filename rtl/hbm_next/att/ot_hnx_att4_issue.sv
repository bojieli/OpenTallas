`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hnx_att4_issue: KV-LINE-STATIONARY MULTI-QUERY attention issue of one SM (HBM-NEXT-ATT4 2026-10-19, next-release
// HBM die at P = 4; fork of rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_issue.sv, DS head dim 512 only).
//
// One KV line stream (the UNION of the NL query lanes' rows, in the golden list order: window positions ascending, then
// compressed rows ascending -- results/arch/hbm_next_1019/att4/E1.md) feeds NL query lanes.  Every union row carries an
// NL-bit LANE MASK (mask store, loaded with the op: the window rule and the IDX top-k lists, compiled by CMTP); lane l
// applies a row only when its mask bit is set, and keeps its OWN row ordinal o_l:
//   QK  a lane computes the scores of its rows only; the score of row r leaves tagged with o_l(r) (its index in the
//       lane's own list), so the soft-max sees exactly the lane's score vector.
//   PV  chunk = 8 consecutive LANE ordinals (golden csum8 over the lane's own positions): first = o_l % 8 == 0,
//       last = o_l % 8 == 7 or the lane's last row, run_first / run_last per lane; x = p_l[o_l] from the lane's x store.
// A lane whose mask bit is clear gets NO beat (its ring slot circulates its sum: a bubble), never a +0 term, so chunk
// boundaries, the last chunk and the pairwise padding are the single-query ones (E1 negative control 'zins').
// All lanes share the beat timing (ring residue = the beat's slot, as the P = 1 issue): the op span is the union row
// count, not NL x the per-lane rows.  No credit / ready / stall: a lane's count that disagrees with its loaded length,
// an ordinal past the x store or a row past the mask store is a sticky FAULT.
//
// Loaders (before cfg_v, as the P = 1 x loader):  x: xw_en / xw_lane / xw_addr / xw_data -- QK words 0..7 = lane's q
// image, PV words 0..n_l-1 = p_l[o] (BF16, lane 0 of the word);  mask: mw_en / mw_addr / mw_data, 16 rows a word
// (row 16 a + i, lane l = bit NL i + l); the per-lane row counts accumulate on the writes (mclr zeroes them).
// P3 (owner 10-19 0le, lane HBM-NEXT-P3-UNITS): NL = the SM accumulator lane count P, production default 3 (generic
// 1..4).  The mask word keeps the FIXED 4-bit-per-row layout of the CMTP R10 plan words (row 16 a + i, lane l = bit
// 4 i + l, mw_data 64 b) at every NL, so the plan record is P-independent; bits of lanes >= NL are not stored.
// Tag to lane l's columns: [15] pv [14] run_first [13] run_last; QK [12:3] = o_l, [2:0] = ring slot; PV [2:0] = slot.
// Mutants (bench negative controls): MUT 1 = lane ordinals count every union row (zero insertion); MUT 2 = PV lanes
// ignore the mask (accumulate every union row); MUT 3 = PV x read at the union row, not the lane ordinal; MUT 4 = lane l
// reads lane l^1's mask bit.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hnx_att4_issue #(
    parameter integer NL    = 3,
    parameter integer MROWS = 256,
    parameter integer MUT   = 0
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 cfg_v,
    input  wire                 cfg_qk,
    input  wire [12:0]          cfg_rows,
    // x loader (per lane)
    input  wire                 xw_en,
    input  wire [1:0]           xw_lane,
    input  wire [6:0]           xw_addr,
    input  wire [1023:0]        xw_data,
    // mask loader
    input  wire                 mclr,
    input  wire                 mw_en,
    input  wire [3:0]           mw_addr,
    input  wire [63:0]          mw_data,
    // from the converter
    input  wire                 b_valid,
    output wire                 b_ready,
    input  wire [1023:0]        b_data,
    input  wire [2:0]           b_slot,
    input  wire [2:0]           b_step,
    input  wire                 b_wend,
    input  wire                 b_last,
    // to the lanes' columns
    output reg  [NL-1:0]        c_v,
    output reg  [NL-1:0]        c_first,
    output reg  [NL-1:0]        c_last,
    output reg  [16*NL-1:0]     c_tag,
    output reg  [1023:0]        c_w,
    output wire [NL*1024-1:0]   c_x,
    output wire [2:0]           c_ph,
    output reg                  op_issued,
    output reg                  fault
);
    initial if (NL < 1 || NL > 4 || MROWS != 256) $fatal(1, "ot_hnx_att4_issue: 1 <= NL <= 4, MROWS 256");
    reg qk; reg [12:0] rows; reg [9:0] wave;
    reg [2:0] ph;
    always @(posedge clk or negedge rst_n) if (!rst_n) ph <= 3'd0; else ph <= ph + 3'd1;
    assign c_ph = ph;
    wire [2:0] rslot = qk ? b_slot : b_step;
    assign b_ready = b_valid && (rslot == ph + 3'd2);
    wire acc = b_valid && b_ready;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin qk <= 1'b0; rows <= 13'd0; wave <= 10'd0; end
        else if (cfg_v) begin qk <= cfg_qk; rows <= cfg_rows; wave <= 10'd0; end
        else if (acc && b_wend) wave <= wave + 10'd1;
    end
    // ---------------- mask store + per-lane loaded row counts ----------------
    reg [NL-1:0] mrow [0:MROWS-1];
    reg [8:0]    cnt  [0:NL-1];
    reg [8:0]    clen [0:NL-1];
    integer i, l2;
    reg [8:0] pc;
    always @(posedge clk) if (mw_en) for (i = 0; i < 16; i = i + 1) mrow[{mw_addr, i[3:0]}] <= mw_data[4*i +: NL];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) for (l2 = 0; l2 < NL; l2 = l2 + 1) begin cnt[l2] <= 9'd0; clen[l2] <= 9'd0; end
        else begin
            for (l2 = 0; l2 < NL; l2 = l2 + 1) begin
                pc = 9'd0;
                for (i = 0; i < 16; i = i + 1) pc = pc + {8'd0, mw_data[4*i + l2]};
                if (mclr) cnt[l2] <= 9'd0;
                else if (mw_en) cnt[l2] <= cnt[l2] + pc;
                if (cfg_v) clen[l2] <= cnt[l2];
            end
        end
    end
    // ---------------- acceptance: row, lane masks, lane ordinals ----------------
    wire [12:0] rr = {wave, b_slot};                    // QK: the slot's row; PV: the token (row) of the beat
    wire [NL-1:0] mraw = mrow[rr[7:0]];
    wire [NL-1:0] m;
    genvar g;
    generate for (g = 0; g < NL; g = g + 1) begin : g_m
        if (MUT == 4 && NL > 1 && (g ^ 1) < NL) begin : g_swap
            assign m[g] = mraw[g ^ 1];
        end else begin : g_ok
            assign m[g] = mraw[g];
        end
    end endgenerate
    reg [8:0] qcnt [0:NL-1];                            // QK: next lane ordinal
    reg [8:0] qord [0:NL-1][0:7];                       // QK: ordinal of the row in ring slot s (latched at step 0)
    reg [8:0] pcnt [0:NL-1];                            // PV: lane ordinal of the current token
    reg       bad;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (l2 = 0; l2 < NL; l2 = l2 + 1) begin qcnt[l2] <= 9'd0; pcnt[l2] <= 9'd0; end
            fault <= 1'b0;
        end else begin
            bad = 1'b0;
            if (cfg_v) for (l2 = 0; l2 < NL; l2 = l2 + 1) begin qcnt[l2] <= 9'd0; pcnt[l2] <= 9'd0; end
            else if (acc) begin
                if (rr >= 13'(MROWS) || rr >= rows) bad = 1'b1;
                for (l2 = 0; l2 < NL; l2 = l2 + 1) begin
                    if (qk && b_step == 3'd0) begin
                        qord[l2][b_slot] <= qcnt[l2];
                        if (m[l2] || MUT == 1) qcnt[l2] <= qcnt[l2] + 9'd1;
                    end
                    if (!qk && b_step == 3'd7 && (m[l2] || MUT == 1)) pcnt[l2] <= pcnt[l2] + 9'd1;
                    if (!qk && m[l2] && pcnt[l2] >= 9'd128) bad = 1'b1;              // past the lane's x store
                    // op end: every lane consumed exactly its loaded rows
                    if (b_last) begin                       // QK: the op's last beat is step 7 (ordinals final)
                        if (qk && qcnt[l2] != clen[l2]) bad = 1'b1;
                        if (!qk && (pcnt[l2] + {8'd0, m[l2]}) != clen[l2]) bad = 1'b1;
                    end
                end
            end
            if (bad) fault <= 1'b1;
        end
    end
    // ---------------- x stores (one 1024-b word store per lane) ----------------
    wire [NL*1024-1:0] xr;
    generate for (g = 0; g < NL; g = g + 1) begin : g_lx
        wire [8:0] ck = pcnt[g];
        wire [6:0] xa = qk ? {4'd0, b_step} : ((MUT == 3) ? rr[6:0] : ck[6:0]);
        genvar k;
        for (k = 0; k < 4; k = k + 1) begin : g_x
            ot_sram_1r1w_128x256_m1_r2c2 u_x (.clk(clk), .r_ce_in(acc), .r_addr_in(xa), .rd_out(xr[1024*g + 256*k +: 256]),
                .w_ce_in(xw_en && xw_lane == g[1:0]), .w_addr_in(xw_addr), .wd_in(xw_data[256*k +: 256]),
                .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(16'd0));
        end
    end endgenerate
    // ---------------- stage 1 / 2 ----------------
    reg [NL-1:0] s1_v, s1_f, s1_l;
    reg [16*NL-1:0] s1_tag;
    reg s1_any, s1_qk, s1_last;
    reg [1023:0] s1_w;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= {NL{1'b0}}; c_v <= {NL{1'b0}}; s1_any <= 1'b0; op_issued <= 1'b0; end
        else begin
            for (l2 = 0; l2 < NL; l2 = l2 + 1) s1_v[l2] <= acc && (m[l2] || (MUT == 2 && !qk));
            s1_any <= acc;
            c_v <= s1_v;
            op_issued <= s1_any && s1_last;
        end
    end
    reg [8:0] ckl, lastc;
    always @(posedge clk) begin
        s1_w <= b_data; s1_qk <= qk; s1_last <= b_last;
        for (l2 = 0; l2 < NL; l2 = l2 + 1) begin
            if (qk) begin
                s1_f[l2] <= (b_step == 3'd0); s1_l[l2] <= (b_step == 3'd7);
                ckl = (b_step == 3'd0) ? qcnt[l2] : qord[l2][b_slot];
                s1_tag[16*l2 +: 16] <= {3'b000, 1'b0, ckl, b_slot};
            end else begin
                ckl = pcnt[l2];
                lastc = (clen[l2] - 9'd1) & ~9'd7;
                s1_f[l2] <= (ckl[2:0] == 3'd0);
                s1_l[l2] <= (ckl[2:0] == 3'd7) || (ckl + 9'd1 == clen[l2]);
                s1_tag[16*l2 +: 16] <= {1'b1, ckl < 9'd8, ckl >= lastc, 10'd0, rslot};
            end
        end
        c_w <= s1_w; c_first <= s1_f; c_last <= s1_l; c_tag <= s1_tag;
    end
    reg x_qk; always @(posedge clk) x_qk <= s1_qk;
    reg [NL*1024-1:0] xq;
    always @(posedge clk) xq <= xr;
    generate for (g = 0; g < NL; g = g + 1) begin : g_cx
        assign c_x[1024*g +: 1024] = x_qk ? xq[1024*g +: 1024] : {64{xq[1024*g +: 16]}};
    end endgenerate
endmodule
`default_nettype wire
