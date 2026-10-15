`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hbm_accel_smh_pvacc: SM.ACC (attention p.v) leaf datapath, H-ELEM-A 2026-10-15 for H-SM-ATT (HBM attention on the
// SM engines, owner-adopted option B).  Standalone unit for one SM leaf; integration into ot_hbm_accel_smh_leaf after
// the H-SM-ATT contract answer (el1015-hbm-sm-attention.log REQUEST 10-15).
//
// Arithmetic = the golden att_pv (tools/hgi_sim/lib.py: csum8 over positions; IEEE binary32 RNE, zero results +0):
//   product   w = e4m3(code) * 2^e (exact in binary32: 3-bit significand), y = mul(p, w)       (p: BF16-valued FP32)
//   chunk     c = (((+0 + y_r0) + y_r1) + ... + y_r7)  over the 8 consecutive rows of the chunk (fewer: last chunk)
//   group     4 aligned chunks per group: ((c0 + c1) + (c2 + c3)) = the first two pairwise levels of the golden tree;
//             a short last group pads with +0 chunks exactly as the golden (c0 | c0+c1 | (c0+c1)+c2)
// The remaining pairwise levels over groups (T640: 20 groups padded to 32) run outside the SM (H-SM-ATT mapping).
//
// Datapath per element: one decode, one FP32 multiplier (ot_hdc_fp32_mul_lat, MLAT), one accumulate adder
// (ot_hdc_fp32_add_lat, ALAT = 4) with a same-cycle forward of the result of the same line position k, and one tree
// adder shared by the NK line positions.  Control is shared by the NE elements (same k / flags / timing).
// Input order contract: lines of a row come k = 0..NK-1 in order, at most one line an edge, so two lines of the same
// k are >= NK >= ALAT edges apart (checked: fault).  Tree operations are bounded per k (one chunk end every >= 8 rows)
// and issue by fixed priority (level 2 before level 1, lower k first) from per-k hold registers: deterministic,
// no input stall.  Fault = sticky: same-k hazard, non-finite FP result, tree hold overrun.
// Mutants (bench): MUT 1 group tree paired (c0 + c2) + (c1 + c3); MUT 2 chunk accumulator not restarted at +0.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_accel_smh_pvacc #(
    parameter integer NE   = 8,      // elements of a line this leaf owns
    parameter integer NK   = 4,      // lines per KV row (544 B KV8 row = 4 x 136 B)
    parameter integer ALAT = 4,
    parameter integer MLAT = 3,
    parameter integer MUT  = 0
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               in_v,
    input  wire [1:0]         in_k,         // line position within the row
    input  wire               in_cfirst,    // first row of a chunk
    input  wire               in_clast,     // last row of a chunk
    input  wire [1:0]         in_ci,        // chunk index within its group (0..3)
    input  wire               in_glast,     // this chunk ends the group (short last group allowed)
    input  wire [NE*8-1:0]    in_code,      // E4M3 codes
    input  wire signed [9:0]  in_e,         // block exponent of the line slice (actquant / SM fmt-1 layout)
    input  wire [31:0]        in_p,         // probability (BF16-valued binary32)
    output reg                out_v,
    output reg  [1:0]         out_k,
    output reg  [NE*32-1:0]   out_y,
    output reg                fault
);
    localparam integer KW = 2;
    initial if (NK > 4 || NK < 1 || ALAT > NK) $fatal(1, "ot_hbm_accel_smh_pvacc: NK <= 4, ALAT <= NK (same-k spacing)");
    // ---- S0 input registers
    reg s0v, s0f, s0l, s0g; reg [1:0] s0k, s0c; reg [NE*8-1:0] s0x; reg signed [9:0] s0e; reg [31:0] s0p;
    always @(posedge clk or negedge rst_n) if (!rst_n) s0v <= 1'b0; else s0v <= in_v;
    always @(posedge clk) begin s0f <= in_cfirst; s0l <= in_clast; s0g <= in_glast; s0k <= in_k; s0c <= in_ci;
                                s0x <= in_code; s0e <= in_e; s0p <= in_p; end
    // ---- S1 decode e4m3 * 2^e -> binary32 (exact; E4M3 NaN code S.1111.111 -> fault)
    function automatic [32:0] dec(input [7:0] c, input signed [9:0] e);
        reg s; reg [3:0] ex; reg [2:0] m; integer be; reg [2:0] mm; integer sh;
        begin
            s = c[7]; ex = c[6:3]; m = c[2:0];
            if (ex == 4'hf && m == 3'h7) dec = {1'b1, 32'h7fc00000};
            else if (ex == 0 && m == 0) dec = {1'b0, 32'h0};
            else begin
                if (ex != 0) begin be = ex - 7; mm = m; end
                else begin                                   // subnormal: 0.m * 2^-6, normalise
                    sh = m[2] ? 1 : m[1] ? 2 : 3; be = -6 - sh; mm = 3'(m << sh);
                end
                be = be + e + 127;
                if (be <= 0 || be >= 255) dec = {1'b1, 32'h7fc00000};   // outside binary32 normal range: fault
                else dec = {1'b0, s, 8'(be), mm, 20'd0};
            end
        end
    endfunction
    reg s1v, s1f, s1l, s1g, s1bad; reg [1:0] s1k, s1c; reg [NE*32-1:0] s1w; reg [31:0] s1p;
    always @(posedge clk or negedge rst_n) if (!rst_n) s1v <= 1'b0; else s1v <= s0v;
    always @(posedge clk) begin : g_dec
        reg [32:0] d; reg bad;
        bad = 1'b0;
        for (integer i = 0; i < NE; i = i + 1) begin d = dec(s0x[8*i +: 8], s0e); s1w[32*i +: 32] <= d[31:0]; bad = bad | d[32]; end
        s1bad <= s0v && bad; s1f <= s0f; s1l <= s0l; s1g <= s0g; s1k <= s0k; s1c <= s0c; s1p <= s0p;
    end
    // ---- multiplier (MLAT), control tags on a matching delay line
    wire [NE-1:0] mvo; wire [NE*32-1:0] my; wire [NE*2-1:0] merr;
    genvar gi;
    generate for (gi = 0; gi < NE; gi = gi + 1) begin : g_mul
        ot_hdc_fp32_mul_lat #(.LAT(MLAT)) u_m (.clk(clk), .rst_n(rst_n), .valid_in(s1v), .a(s1p), .b(s1w[32*gi +: 32]),
            .y(my[32*gi +: 32]), .err(merr[2*gi +: 2]), .valid_out(mvo[gi]));
    end endgenerate
    reg [6:0] mt [0:MLAT-1];                                  // {f, l, g, k2, c2}
    always @(posedge clk) begin
        mt[0] <= {s1f, s1l, s1g, s1k, s1c};
        for (integer d = 1; d < MLAT; d = d + 1) mt[d] <= mt[d-1];
    end
    wire mv = mvo[0];
    wire m_f = mt[MLAT-1][6], m_l = mt[MLAT-1][5], m_g = mt[MLAT-1][4];
    wire [1:0] m_k = mt[MLAT-1][3:2], m_c = mt[MLAT-1][1:0];
    // ---- accumulate adder: a = first ? +0 : acc[k] (forwarded when the same k's result returns this edge)
    reg [NE*32-1:0] acc [0:NK-1];
    wire [NE-1:0] avo; wire [NE*32-1:0] ay; wire [NE*2-1:0] aerr;
    reg [6:0] at [0:ALAT-1];                                  // {v, l, g, k2, c2}
    wire a_v = at[ALAT-1][6], a_l = at[ALAT-1][5], a_g = at[ALAT-1][4];
    wire [1:0] a_k = at[ALAT-1][3:2], a_c = at[ALAT-1][1:0];
    wire fwd = a_v && (a_k == m_k);
    wire [NE*32-1:0] acc_rd = fwd ? ay : acc[m_k];
    wire restart = (MUT == 2) ? 1'b0 : m_f;
    generate for (gi = 0; gi < NE; gi = gi + 1) begin : g_acc
        ot_hdc_fp32_add_lat #(.LAT(ALAT)) u_a (.clk(clk), .rst_n(rst_n), .valid_in(mv),
            .a(restart ? 32'd0 : acc_rd[32*gi +: 32]), .b(my[32*gi +: 32]),
            .y(ay[32*gi +: 32]), .err(aerr[2*gi +: 2]), .valid_out(avo[gi]));
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) for (integer d = 0; d < ALAT; d = d + 1) at[d] <= '0;
        else begin
            at[0] <= {mv, m_l, m_g, m_k, m_c};
            for (integer d = 1; d < ALAT; d = d + 1) at[d] <= at[d-1];
        end
    end
    always @(posedge clk) if (a_v) acc[a_k] <= ay;
    // same-k hazard: an issue of k while an earlier issue of k is still inside the adder (not yet at its last stage)
    reg haz;
    always @* begin
        haz = 1'b0;
        for (integer d = 0; d < ALAT - 1; d = d + 1) if (mv && at[d][6] && at[d][3:2] == m_k) haz = 1'b1;
    end
    // ---- group tree: per-k holds, one shared tree adder, fixed priority (L2 before L1, lower k first)
    reg [NE*32-1:0] s0h [0:NK-1];      // c0 / c2
    reg [NE*32-1:0] s01 [0:NK-1];      // c0 + c1
    reg [NE*32-1:0] bh  [0:NK-1];      // pending second operand
    reg [NK-1:0] p1, p2, p2fin;        // pending level 1 / level 2; level-1 result is final (short group)
    reg [NK-1:0] p1to2;                // level-1 result feeds a level 2 (chunk 3)
    reg [NE*32-1:0] x1  [0:NK-1];      // MUT 1 only (c1 held)
    wire [NE*32-1:0] c = ay;           // chunk value at a_v && a_l
    wire tvo; wire [NE-1:0] tvo_e; wire [NE*32-1:0] ty; wire [NE*2-1:0] terr;
    reg [3:0] tt [0:ALAT-1];           // {v, lvl2, k2}
    reg [3:0] tt1 [0:ALAT-1];          // {to2, fin, -, -}
    reg ti_v, ti_l2; reg [1:0] ti_k; reg [NE*32-1:0] ti_a, ti_b; reg ti_to2, ti_fin;
    always @* begin
        ti_v = 1'b0; ti_l2 = 1'b0; ti_k = 2'd0; ti_to2 = 1'b0; ti_fin = 1'b0;
        for (integer k = NK - 1; k >= 0; k = k - 1) if (p1[k]) begin ti_v = 1'b1; ti_k = 2'(k); end
        for (integer k = NK - 1; k >= 0; k = k - 1) if (p2[k]) begin ti_v = 1'b1; ti_l2 = 1'b1; ti_k = 2'(k); end
        ti_a = ti_l2 ? s01[ti_k] : s0h[ti_k];
        ti_b = bh[ti_k];
        ti_to2 = !ti_l2 && p1to2[ti_k]; ti_fin = ti_l2 || p2fin[ti_k];
    end
    generate for (gi = 0; gi < NE; gi = gi + 1) begin : g_tree
        ot_hdc_fp32_add_lat #(.LAT(ALAT)) u_t (.clk(clk), .rst_n(rst_n), .valid_in(ti_v),
            .a(ti_a[32*gi +: 32]), .b(ti_b[32*gi +: 32]), .y(ty[32*gi +: 32]), .err(terr[2*gi +: 2]), .valid_out(tvo_e[gi]));
    end endgenerate
    assign tvo = tvo_e[0];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) for (integer d = 0; d < ALAT; d = d + 1) begin tt[d] <= '0; tt1[d] <= '0; end
        else begin
            tt[0] <= {ti_v, ti_l2, ti_k}; tt1[0] <= {ti_to2, ti_fin, 2'd0};
            for (integer d = 1; d < ALAT; d = d + 1) begin tt[d] <= tt[d-1]; tt1[d] <= tt1[d-1]; end
        end
    end
    wire t_v = tt[ALAT-1][3], t_l2 = tt[ALAT-1][2]; wire [1:0] t_k = tt[ALAT-1][1:0];
    wire t_to2 = tt1[ALAT-1][3], t_fin = tt1[ALAT-1][2];
    reg ovr;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin p1 <= '0; p2 <= '0; p2fin <= '0; p1to2 <= '0; out_v <= 1'b0; fault <= 1'b0; end
        else begin
            out_v <= 1'b0; ovr = 1'b0;
            if (ti_v) begin if (ti_l2) p2[ti_k] <= 1'b0; else p1[ti_k] <= 1'b0; end
            // level-1 result: final (short group of 2) or operand of the level 2 (chunk 3; MUT 1 chains instead)
            if (t_v && !t_l2) begin
                if (t_fin) begin out_v <= 1'b1; out_k <= t_k; out_y <= ty; end
                else if (t_to2) begin
                    bh[t_k] <= ty; if (p2[t_k]) ovr = 1'b1; p2[t_k] <= 1'b1;
                end else s01[t_k] <= ty;
            end
            if (t_v && t_l2) begin out_v <= 1'b1; out_k <= t_k; out_y <= ty; end
            // chunk end (accumulate result of the chunk's last row)
            if (a_v && a_l) begin
                if (MUT == 1 && !a_g) begin                 // mutant pairing (c0 + c2) + (c1 + c3)
                    case (a_c)
                        2'd0: s0h[a_k] <= c;
                        2'd1: x1[a_k] <= c;
                        2'd2: begin bh[a_k] <= c; p1[a_k] <= 1'b1; p1to2[a_k] <= 1'b0; p2fin[a_k] <= 1'b0; end
                        2'd3: begin s0h[a_k] <= x1[a_k]; bh[a_k] <= c; p1[a_k] <= 1'b1; p1to2[a_k] <= 1'b1;
                                    p2fin[a_k] <= 1'b0; end
                    endcase
                end else case (a_c)
                    2'd0: if (a_g) begin if (t_v) ovr = 1'b1; out_v <= 1'b1; out_k <= a_k; out_y <= c; end
                          else s0h[a_k] <= c;
                    2'd1: begin bh[a_k] <= c; if (p1[a_k]) ovr = 1'b1; p1[a_k] <= 1'b1; p1to2[a_k] <= 1'b0;
                                p2fin[a_k] <= a_g; end
                    2'd2: begin if (p1[a_k]) ovr = 1'b1;
                          if (a_g) begin bh[a_k] <= c; if (p2[a_k]) ovr = 1'b1; p2[a_k] <= 1'b1; end
                          else s0h[a_k] <= c; end
                    2'd3: begin bh[a_k] <= c; if (p1[a_k]) ovr = 1'b1; p1[a_k] <= 1'b1; p1to2[a_k] <= 1'b1;
                                p2fin[a_k] <= 1'b0; end
                endcase
            end
            if (haz || ovr || s1bad || (avo[0] && |aerr) || (mvo[0] && |merr) || (tvo && |terr)) fault <= 1'b1;
        end
    end
endmodule
`default_nettype wire
