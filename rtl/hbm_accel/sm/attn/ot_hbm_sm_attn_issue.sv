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
// Tag to the columns: [15] pv  [14] run_first  [13] run_last  [12:0] row (QK: op row = 8 wave + slot; PV: slot b).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_sm_attn_issue (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          cfg_v,
    input  wire          cfg_qk,
    input  wire [12:0]   cfg_rows,
    // x loader
    input  wire          xw_en,
    input  wire [6:0]    xw_addr,
    input  wire [1023:0] xw_data,
    // from the converter (slot = row of the wave, step = QK position / PV beat)
    input  wire          b_valid,
    output wire          b_ready,
    input  wire [1023:0] b_data,
    input  wire [2:0]    b_slot,
    input  wire [2:0]    b_step,
    input  wire [3:0]    b_wrows,
    input  wire          b_last,
    // to the 4 columns
    output reg           c_v,
    output reg           c_first,
    output reg           c_last,
    output reg  [15:0]   c_tag,
    output reg  [1023:0] c_w,
    output wire [1023:0] c_x,
    output wire [2:0]    c_ph,            // residue of this cycle (bench check: c_v only where c_ph == ring slot)
    output reg           op_issued        // pulse: the op's last beat reached the columns
);
    reg qk; reg [12:0] rows; reg [9:0] wave;
    reg [2:0] ph;
    always @(posedge clk or negedge rst_n) if (!rst_n) ph <= 3'd0; else ph <= ph + 3'd1;
    assign c_ph = ph;
    // ring slot of the beat: QK the wave row, PV the beat; it reaches the columns 2 edges after acceptance
    wire [2:0] rslot = qk ? b_slot : b_step;
    assign b_ready = b_valid && (rslot == ph + 3'd2);
    wire acc = b_valid && b_ready;
    wire [12:0] tk = {wave, 3'd0} + {10'd0, b_slot};              // QK: op row; PV: token
    wire wave_end = acc && (b_step == 3'd7) && ({1'b0, b_slot} == b_wrows - 4'd1);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin qk <= 1'b0; rows <= 13'd0; wave <= 10'd0; end
        else if (cfg_v) begin qk <= cfg_qk; rows <= cfg_rows; wave <= 10'd0; end
        else if (wave_end) wave <= wave + 10'd1;
    end
    // x store (QK: word t; PV: word tk)
    wire [6:0] xa = qk ? {4'd0, b_step} : tk[6:0];
    wire [1023:0] xr;
    genvar m;
    generate for (m = 0; m < 4; m = m + 1) begin : g_x
        ot_sram_1r1w_128x256_m1_r2c2 u_x (.clk(clk), .r_ce_in(acc), .r_addr_in(xa), .rd_out(xr[256*m +: 256]),
            .w_ce_in(xw_en), .w_addr_in(xw_addr), .wd_in(xw_data[256*m +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    // stage 1 (x macro read in flight), stage 2 = column inputs
    reg s1_v, s1_f, s1_l, s1_qk, s1_last; reg [15:0] s1_tag; reg [1023:0] s1_w;
    wire [12:0] lastc = (rows - 13'd1) & ~13'd7;                 // first token of the op's last chunk
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 1'b0; c_v <= 1'b0; op_issued <= 1'b0; end
        else begin s1_v <= acc; c_v <= s1_v; op_issued <= s1_v && s1_last; end
    end
    always @(posedge clk) begin
        s1_w <= b_data; s1_qk <= qk; s1_last <= b_last;
        if (qk) begin
            s1_f <= (b_step == 3'd0); s1_l <= (b_step == 3'd7);
            s1_tag <= {3'b000, tk};
        end else begin
            s1_f <= (tk[2:0] == 3'd0);
            s1_l <= (tk[2:0] == 3'd7) || (tk + 13'd1 == rows);
            s1_tag <= {1'b1, tk < 13'd8, tk >= lastc, 10'd0, b_step};
        end
        c_w <= s1_w; c_first <= s1_f; c_last <= s1_l; c_tag <= s1_tag;
    end
    reg x_qk; always @(posedge clk) x_qk <= s1_qk;
    reg [1023:0] xq;
    always @(posedge clk) xq <= xr;
    assign c_x = x_qk ? xq : {64{xq[15:0]}};
endmodule
`default_nettype wire
