`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Correctly rounded binary32 SQUARE ROOT for the V4.1 decode core: II 1, fixed
// DEPTH 31.  A stage-rebalanced copy of the qualified
// rtl/abi3/ot_a3_engram_fp32_sqrt_rne_pipe.sv (FRAC_SHIFT 15), with the decode
// core's port convention (v/a -> y/vo/fault).
//
// WHAT CHANGED, AND WHY.  The qualified pipe routes at 766 MHz on ASAP7: its
// critical path is the single finishing stage, which finds the root's leading
// bit by a priority encoder over all 28 root bits, shifts by a variable amount,
// rounds and encodes in one cycle.  But the leading bit is not variable: the
// radicand is a 24- or 25-bit significand times 2^(2*FRAC_SHIFT), so the root
// lies in [2^(11.5+F), 2^(12.5+F)) and its top bit is bit F+12 or bit F+11.
// Here the finish is a 2-way select on root[F+12] (stage 1: truncated
// significand, guard, sticky, exponent) and a separate round-and-encode
// (stage 2).  The digit recurrence and the decode stage are transcribed
// unchanged.  rtl/test/tb_hdc_fsqrt_equiv.sv drives both modules from one
// stimulus and requires the same code and the same refusal for every operand,
// one cycle later.
//
// FUNCTION.  y = RN_even(sqrt(a)); sqrt(+-0) = +0; subnormal arguments are
// normalised; a negative or nonfinite argument FAILS CLOSED (fault, y = +0).
// ---------------------------------------------------------------------------
module ot_hdc_fsqrt (
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
    localparam integer TOP           = FRAC_SHIFT + 12;   // the root's possible top bit

    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // ---- stage 0: unpack, normalise, force an even exponent (as qualified) ------
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

    // ---- stages 1..STAGES: one root digit per stage (as qualified) --------------
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
            wire take = (shifted >= trial);
            always @(posedge clk) begin
                rem_stage[g]  <= take ? (shifted - trial) : shifted;
                root_stage[g] <= {src_root[Q_W-2:0], take};
                rad_stage[g]  <= {src_rad[RAD_W-3:0], 2'b00};
                half_stage[g] <= (g == 1) ? s0_half : half_stage[g-1];
                zero_stage[g] <= (g == 1) ? s0_zero : zero_stage[g-1];
                err_stage[g]  <= (g == 1) ? s0_err  : err_stage[g-1];
            end
        end
    endgenerate

    // ---- finish 1: the root's top bit is TOP or TOP-1 -------------------------------
    wire [Q_W-1:0]   root = root_stage[STAGES];
    wire [REM_W-1:0] rem  = rem_stage[STAGES];
    wire hi = root[TOP];
    reg [23:0] f_trunc;
    reg        f_guard, f_sticky, f_zero, f_err;
    reg signed [EXP_W-1:0] f_unb;       // unbiased exponent before the rounding carry
    always @(posedge clk) begin
        f_zero <= zero_stage[STAGES];
        f_err  <= err_stage[STAGES];
        if (hi) begin
            f_trunc  <= root[TOP -: 24];
            f_guard  <= root[TOP - 24];
            f_sticky <= (|root[TOP - 25:0]) || (|rem);
            f_unb    <= $signed(TOP) + half_stage[STAGES] - $signed(FRAC_SHIFT);
        end else begin
            f_trunc  <= root[TOP - 1 -: 24];
            f_guard  <= root[TOP - 25];
            f_sticky <= (|root[TOP - 26:0]) || (|rem);
            f_unb    <= $signed(TOP - 1) + half_stage[STAGES] - $signed(FRAC_SHIFT);
        end
    end

    // ---- finish 2: round to nearest even, encode --------------------------------------
    wire        round_up = f_guard && (f_sticky || f_trunc[0]);
    wire [24:0] rounded  = {1'b0, f_trunc} + {24'd0, round_up};
    wire        carried  = rounded[24];
    wire [23:0] sig_out  = carried ? rounded[24:1] : rounded[23:0];
    wire signed [EXP_W-1:0] biased = f_unb + (carried ? 12'sd1 : 12'sd0) + 12'sd127;
    wire out_of_range = (biased < 12'sd1) || (biased > 12'sd254);
    always @(posedge clk) begin
        if (f_err || (!f_zero && out_of_range)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f_zero) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {1'b0, biased[7:0], sig_out[22:0]}; fault <= 1'b0; end
    end
endmodule
