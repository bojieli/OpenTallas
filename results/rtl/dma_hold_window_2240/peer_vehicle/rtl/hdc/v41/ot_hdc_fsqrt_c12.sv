`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_fsqrt_c12: the 1.2 GHz (0.833 ns ASAP7 SS) successor of rtl/hdc/v41/ot_hdc_fsqrt.sv for the HBM SU
// (hbm-su closure, 2026-10-05).  Same ports, same DEPTH 31, the same {vo, y, fault} on every cycle, bit for bit
// (rtl/test/tb_hdc_fsqrt_c12_equiv.sv drives both from one stimulus).  New file; the original is unchanged.
// Timing-only rewrites (closure kit: kept prefix adders, precomputed carries), no register moved:
//   * digit stage: `shifted >= trial` and `shifted - trial` are ONE kept Kogge-Stone subtractor
//     (ot_hdc_ksadd_k: shifted + ~trial + 1; its carry out is the take bit), instead of a behavioural compare and
//     subtract that ABC ripples (routed -114 ps in the SU side pipe);
//   * finish 1 also registers both candidate biased exponents (no rounding carry / carry) and their
//     out-of-range flags, from the stage's own half exponent and top-bit select;
//   * finish 2 is only the kept 24-bit rounding increment (ot_hdc_inc_k) and a carry select (was -167 ps).
//     When the increment carries out, the rounded significand is 2^24, so the 23 stored fraction bits are the
//     increment's low 23 bits either way.
// Needs rtl/hdc/ot_hdc_prefix.sv (ot_hdc_ksadd_k, ot_hdc_inc_k) and ot_hdc_vline (rtl/hdc/ot_hdc_sfu.sv).
// ---------------------------------------------------------------------------
module ot_hdc_fsqrt_c12 (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer FRAC_SHIFT    = 15;
    localparam integer RADICAND_BITS = 25 + 2 * FRAC_SHIFT;
    localparam integer STAGES        = (RADICAND_BITS + 1) / 2;
    localparam integer RAD_W         = 2 * STAGES;
    localparam integer Q_W           = STAGES;
    localparam integer REM_W         = STAGES + 4;
    localparam integer EXP_W         = 12;
    localparam integer DEPTH         = STAGES + 3;
    localparam integer TOP           = FRAC_SHIFT + 12;

    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // ---- stage 0: unpack, normalise, force an even exponent (unchanged) ----------------
    wire [7:0]  in_biased   = a[30:23];
    wire [22:0] in_fraction = a[22:0];
    wire in_nonfinite = (in_biased == 8'hff);
    wire in_zero      = (a[30:0] == 31'b0);
    wire in_negative  = a[31] && !in_zero;
    wire in_subnormal = (in_biased == 8'b0);
    integer bit_index;
    reg [4:0] leading_shift;
    always @* begin
        leading_shift = 5'd23;
        for (bit_index = 0; bit_index < 23; bit_index = bit_index + 1)
            if (in_fraction[bit_index])
                leading_shift = 5'd22 - bit_index[4:0];
    end
    wire [23:0] significand = in_subnormal ? ({1'b0, in_fraction} << leading_shift) : {1'b1, in_fraction};
    wire signed [EXP_W-1:0] argument_exponent = in_subnormal
        ? (-12'sd149 - $signed({7'b0, leading_shift}))
        : ($signed({4'b0, in_biased}) - 12'sd150);
    wire exponent_odd = argument_exponent[0];
    wire [24:0] even_significand = exponent_odd ? {significand, 1'b0} : {1'b0, significand};
    wire signed [EXP_W-1:0] even_exponent = exponent_odd ? (argument_exponent - 12'sd1) : argument_exponent;
    wire signed [EXP_W-1:0] half_exponent = even_exponent >>> 1;

    reg [RAD_W-1:0]        s0_radicand;
    reg signed [EXP_W-1:0] s0_half;
    reg                    s0_zero, s0_err;
    always @(posedge clk) begin
        s0_radicand <= {{(RAD_W - RADICAND_BITS){1'b0}}, even_significand, {(2 * FRAC_SHIFT){1'b0}}};
        s0_half <= half_exponent;
        s0_zero <= in_zero;
        s0_err  <= in_nonfinite || in_negative;
    end

    // ---- stages 1..STAGES: one root digit per stage, one kept subtractor -------------------
    reg [RAD_W-1:0]        rad_stage  [1:STAGES];
    reg [REM_W-1:0]        rem_stage  [1:STAGES];
    reg [Q_W-1:0]          root_stage [1:STAGES];
    reg signed [EXP_W-1:0] half_stage [1:STAGES];
    reg                    zero_stage [1:STAGES];
    reg                    err_stage  [1:STAGES];
    genvar g;
    generate
        for (g = 1; g <= STAGES; g = g + 1) begin : g_dig
            wire [RAD_W-1:0] src_rad  = (g == 1) ? s0_radicand : rad_stage[g-1];
            wire [REM_W-1:0] src_rem  = (g == 1) ? {REM_W{1'b0}} : rem_stage[g-1];
            wire [Q_W-1:0]   src_root = (g == 1) ? {Q_W{1'b0}} : root_stage[g-1];
            wire [REM_W-1:0] shifted  = {src_rem[REM_W-3:0], src_rad[RAD_W-1:RAD_W-2]};
            wire [REM_W-1:0] trial    = ({{(REM_W-Q_W){1'b0}}, src_root} << 2) | {{(REM_W-1){1'b0}}, 1'b1};
            wire [REM_W-1:0] diff;
            wire             take;      // carry out of shifted + ~trial + 1  ==  (shifted >= trial)
            ot_hdc_ksadd_k #(.W(REM_W)) u_sub (.a(shifted), .b(~trial), .cin(1'b1), .s(diff), .cout(take));
            always @(posedge clk) begin
                rem_stage[g]  <= take ? diff : shifted;
                root_stage[g] <= {src_root[Q_W-2:0], take};
                rad_stage[g]  <= {src_rad[RAD_W-3:0], 2'b00};
                half_stage[g] <= (g == 1) ? s0_half : half_stage[g-1];
                zero_stage[g] <= (g == 1) ? s0_zero : zero_stage[g-1];
                err_stage[g]  <= (g == 1) ? s0_err  : err_stage[g-1];
            end
        end
    endgenerate

    // ---- finish 1: the root's top bit is TOP or TOP-1; both candidate exponents ------------
    wire [Q_W-1:0]   root = root_stage[STAGES];
    wire [REM_W-1:0] rem  = rem_stage[STAGES];
    wire hi = root[TOP];
    // biased = f_unb + 127 (+1 on a rounding carry); f_unb = half + (TOP - FRAC_SHIFT) (hi) or one less
    wire signed [EXP_W-1:0] h = half_stage[STAGES];
    wire signed [EXP_W-1:0] b_lo_hi = h + $signed(TOP - FRAC_SHIFT + 127);      // hi, no carry
    wire signed [EXP_W-1:0] b_lo_lo = h + $signed(TOP - 1 - FRAC_SHIFT + 127);  // lo, no carry
    wire signed [EXP_W-1:0] b_hi_hi = h + $signed(TOP - FRAC_SHIFT + 128);      // hi, carry
    wire [EXP_W-1:0] b0 = hi ? b_lo_hi : b_lo_lo;
    wire [EXP_W-1:0] b1 = hi ? b_hi_hi : b_lo_hi;                                 // lo + carry == hi, no carry
    reg [22:0] f_trunc_l;   // the truncated significand, low 23 bits
    reg        f_trunc23;
    reg        f_guard, f_sticky, f_zero, f_err;
    reg [7:0]  f_b0, f_b1;
    reg        f_oor0, f_oor1;
    always @(posedge clk) begin
        f_zero <= zero_stage[STAGES];
        f_err  <= err_stage[STAGES];
        f_b0 <= b0[7:0];
        f_b1 <= b1[7:0];
        f_oor0 <= ($signed(b0) < 12'sd1) || ($signed(b0) > 12'sd254);
        f_oor1 <= ($signed(b1) < 12'sd1) || ($signed(b1) > 12'sd254);
        if (hi) begin
            {f_trunc23, f_trunc_l} <= root[TOP -: 24];
            f_guard  <= root[TOP - 24];
            f_sticky <= (|root[TOP - 25:0]) || (|rem);
        end else begin
            {f_trunc23, f_trunc_l} <= root[TOP - 1 -: 24];
            f_guard  <= root[TOP - 25];
            f_sticky <= (|root[TOP - 26:0]) || (|rem);
        end
    end

    // ---- finish 2: kept rounding increment, carry select, encode --------------------------
    wire        round_up = f_guard && (f_sticky || f_trunc_l[0]);
    wire [23:0] rounded;
    wire        carried;
    ot_hdc_inc_k #(.W(24)) u_inc (.a({f_trunc23, f_trunc_l}), .inc(round_up), .y(rounded), .co(carried));
    wire [7:0] biased = carried ? f_b1 : f_b0;
    wire       out_of_range = carried ? f_oor1 : f_oor0;
    always @(posedge clk) begin
        if (f_err || (!f_zero && out_of_range)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f_zero) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {1'b0, biased, rounded[22:0]}; fault <= 1'b0; end
    end
endmodule
