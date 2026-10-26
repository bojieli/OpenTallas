`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hbm_sm_attn_issue: attention issue stage of one SM (H-SM-ATT 2026-10-15) between the KV converter
// (ot_hbm_sm_kv_line) and the SM's BF16 columns (ot_hbm_sm_tcpv_col x 4 sub-rows).  It plays the role ot_hbm_accel_issue_pq
// plays for a BF16 matvec: the column's circulating FP32 ring holds 8 slot sums, slot s owns cycle residue s, so a beat for
// slot s leaves exactly when the free-running residue counter equals s (a slot with no beat circulates its sum: bubble).
//   QK: beat (slot s = row of wave, step t) -> first t == 0, last t == 7, x = q image word t (lane j = q[8j + t]).
//   PV: beat (row s of wave = token tk, beat b = slot b) -> chunk = 8 tokens: first tk % 8 == 0, last tk % 8 == 7 or the op's
//       last token; run_first = first chunk, run_last = last chunk; x = p[tk] broadcast to all 64 lanes.
// X STORE: 4 x ot_sram_1r1w_128x256 macros (the SM x-store macro type), written by the x loader port before the op:
//   QK words 0..7 = the q image (64 BF16 lanes each); PV words 0..rows-1 = p[tk] in lane 0 (BF16).
// Out: one beat per cycle at most, fixed 2-cycle latency from the accepting edge (x read + output register).
// HEAD DIM 128 (cfg_h128, Qwen GQA): QK ring slot s = rows 4s..4s+3 (one per SM sub-row); PV: the op's R tokens run as
//   4 interleaved TOKEN STREAMS of R/4 (aligned runs; the KV descriptor reads their rows round-robin: wave row s = stream
//   s % 4, stream token wave*2 + s/4), ring slot = 2 (s % 4) + beat; each stream's merge entry yields its own node.
// NCOL x columns (GQA: one q head each) share every beat; x store = NCOL x 4 macros, word = NCOL x 1024 bits.
// Tag to the columns: [15] pv  [14] run_first  [13] run_last  [12:0] row (QK: op row of the slot's first row; PV: slot).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_sm_attn_issue #(
    parameter integer NCOL = 1
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               cfg_v,
    input  wire               cfg_qk,
    input  wire               cfg_h128,
    input  wire [12:0]        cfg_rows,
    // x loader
    input  wire               xw_en,
    input  wire [6:0]         xw_addr,
    input  wire [NCOL*1024-1:0] xw_data,
    // from the converter
    input  wire               b_valid,
    output wire               b_ready,
    input  wire [1023:0]      b_data,
    input  wire [2:0]         b_slot,
    input  wire [2:0]         b_step,
    input  wire               b_wend,
    input  wire               b_last,
    // to the columns
    output reg                c_v,
    output reg                c_first,
    output reg                c_last,
    output reg  [15:0]        c_tag,
    output reg  [1023:0]      c_w,
    output wire [NCOL*1024-1:0] c_x,
    output wire [2:0]         c_ph,
    output reg                op_issued
);
    reg qk, h128; reg [12:0] rows; reg [9:0] wave;
    reg [2:0] ph;
    always @(posedge clk or negedge rst_n) if (!rst_n) ph <= 3'd0; else ph <= ph + 3'd1;
    assign c_ph = ph;
    // ring slot of the beat
    wire [2:0] rslot = qk ? b_slot : (h128 ? {b_slot[1:0], b_step[0]} : b_step);
    assign b_ready = b_valid && (rslot == ph + 3'd2);
    wire acc = b_valid && b_ready;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin qk <= 1'b0; h128 <= 1'b0; rows <= 13'd0; wave <= 10'd0; end
        else if (cfg_v) begin qk <= cfg_qk; h128 <= cfg_h128; rows <= cfg_rows; wave <= 10'd0; end
        else if (acc && b_wend) wave <= wave + 10'd1;
    end
    // row / token bookkeeping
    wire [12:0] qrow = h128 ? {wave[7:0], b_slot, 2'b00} : {wave, b_slot};        // QK: first row of the slot
    wire [12:0] r4   = rows >> 2;                                                  // PV h128: stream length
    wire [12:0] k4   = {1'b0, wave, b_slot[2]};                                    // PV h128: token within its stream
    wire [12:0] ptok = h128 ? (r4 * {11'd0, b_slot[1:0]} + k4) : {wave, b_slot};  // PV: token of the op
    wire [12:0] ck   = h128 ? k4 : ptok;                                           // position of the token in its run
    wire [12:0] clen = h128 ? r4 : rows;                                           // run length (tokens)
    wire [12:0] lastc = (clen - 13'd1) & ~13'd7;
    wire [6:0] xa = qk ? {4'd0, b_step} : ptok[6:0];
    wire [NCOL*1024-1:0] xr;
    genvar m;
    generate for (m = 0; m < 4 * NCOL; m = m + 1) begin : g_x
        ot_sram_1r1w_128x256_m1_r2c2 u_x (.clk(clk), .r_ce_in(acc), .r_addr_in(xa), .rd_out(xr[256*m +: 256]),
            .w_ce_in(xw_en), .w_addr_in(xw_addr), .wd_in(xw_data[256*m +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    reg s1_v, s1_f, s1_l, s1_qk, s1_last; reg [15:0] s1_tag; reg [1023:0] s1_w;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 1'b0; c_v <= 1'b0; op_issued <= 1'b0; end
        else begin s1_v <= acc; c_v <= s1_v; op_issued <= s1_v && s1_last; end
    end
    always @(posedge clk) begin
        s1_w <= b_data; s1_qk <= qk; s1_last <= b_last;
        if (qk) begin
            s1_f <= (b_step == 3'd0); s1_l <= (b_step == 3'd7);
            s1_tag <= {3'b000, qrow};
        end else begin
            s1_f <= (ck[2:0] == 3'd0);
            s1_l <= (ck[2:0] == 3'd7) || (ck + 13'd1 == clen);
            s1_tag <= {1'b1, ck < 13'd8, ck >= lastc, 10'd0, rslot};
        end
        c_w <= s1_w; c_first <= s1_f; c_last <= s1_l; c_tag <= s1_tag;
    end
    reg x_qk; always @(posedge clk) x_qk <= s1_qk;
    reg [NCOL*1024-1:0] xq;
    always @(posedge clk) xq <= xr;
    genvar c;
    generate for (c = 0; c < NCOL; c = c + 1) begin : g_cx
        assign c_x[1024*c +: 1024] = x_qk ? xq[1024*c +: 1024] : {64{xq[1024*c +: 16]}};
    end endgenerate
endmodule
`default_nettype wire
