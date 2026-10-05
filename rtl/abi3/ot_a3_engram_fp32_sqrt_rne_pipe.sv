`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Correctly rounded finite binary32 SQUARE ROOT, FULLY PIPELINED.
//
// PIPELINE: STAGES+2 registered stages.  INITIATION INTERVAL: 1.  A new
// argument may be presented on every clock with no handshake and no stall; the
// result of the argument accepted in cycle t appears with out_valid in cycle
// t + LATENCY.  There is no combinational path from argument to result and none
// spanning two stages.
//
// WHY THIS EXISTS.  The repository already qualifies binary32 multiply, add,
// divide, reciprocal square root and the certifying exponential/sigmoid.  It
// does not have a square root, and engram_gate_fp32_v1 needs three of them per
// transaction: the two vector norms and the signed square root of the
// normalised dot.  sqrt is NOT obtainable from the qualified reciprocal square
// root: x * rsqrt(x) rounds twice and differs from the correctly rounded root
// in the last bit, which the campaign would report as a failure and which no
// numeric contract in this repository accepts.
//
// ALGORITHM, and why it pipelines where the bisecting blocks do not.
// ot_a3_fp32_div_rne and ot_fp32_rsqrt_rne bisect the binary32 code space:
// every iteration's candidate depends on the previous comparison, the state is
// one in-flight operand, and the block is therefore a multi-cycle FSM with an
// initiation interval of about 30.  A digit recurrence has the same dependence
// but it is a FIXED-LENGTH chain with a small carried state, so cutting it into
// one stage per digit turns it into a systolic pipeline.  Per stage:
//
//     rem' = (rem << 2) | next_two_radicand_bits
//     if (rem' >= 4*q + 1) { rem'' = rem' - (4*q + 1); q' = 2*q + 1; }
//     else                 { rem'' = rem';            q' = 2*q;     }
//
// which is one (STAGES+4)-bit compare-and-subtract per stage and no multiplier
// anywhere.  After STAGES digits, q = floor(sqrt(R)) and rem = R - q*q exactly,
// so the remainder IS the sticky bit and the rounding decision is exact.
//
// EXACTNESS.  The argument m * 2**e is normalised to a 24-bit significand, the
// exponent is forced even by one shift, and the radicand is m << (2*FRAC_SHIFT)
// so the integer root carries FRAC_SHIFT extra fractional bits.  With
// FRAC_SHIFT >= 14 the root has at least 26 significant bits, which is the 24
// binary32 keeps plus a round and a sticky bit, and the rounding is therefore
// correctly rounded round-to-nearest-ties-to-even.  A smaller FRAC_SHIFT is
// REFUSED at run time rather than silently rounded twice: result_error is
// ERR_RANGE.
//
// NO SUBNORMAL OR OVERFLOW PATH IS NEEDED, and that is a property of the
// operation, not an assumption about the model.  The square root of the
// smallest positive binary32 (2**-149) is 2**-74.5 and of the largest
// (about 2**128) is about 2**64, so every result of every finite nonnegative
// argument is a binary32 NORMAL.  The range checks are still written, derived
// from the exponent field width, so a parameter change cannot turn a wrapped
// exponent into a wrong answer.
//
// GEOMETRY.  Nothing here knows a vector width, a head count, a block size or
// a table extent.  FRAC_SHIFT is the only parameter and every internal width is
// derived from it.
// ---------------------------------------------------------------------------
module ot_a3_engram_fp32_sqrt_rne_pipe #(
    //: Fractional bits carried into the integer root.  14 is the minimum that
    //: makes the rounding correct; 15 is the default and leaves one bit of
    //: margin at the cost of one pipeline stage.
    parameter integer FRAC_SHIFT = 15
) (
    input  wire        clk,
    input  wire        rst_n,
    //: Accepted unconditionally.  There is no in_ready: the pipe never stalls.
    input  wire        in_valid,
    input  wire [31:0] argument_code,
    output wire        out_valid,
    output wire [31:0] result_code,
    output wire [1:0]  result_error
);
    localparam [1:0] ERR_NONE     = 2'd0;
    localparam [1:0] ERR_ARGUMENT = 2'd1;
    localparam [1:0] ERR_RANGE    = 2'd2;

    //: The radicand is the 25-bit even-exponent significand shifted up by two
    //: FRAC_SHIFTs.  STAGES digits of recurrence consume two radicand bits each.
    localparam integer RADICAND_BITS = 25 + 2 * FRAC_SHIFT;
    localparam integer STAGES        = (RADICAND_BITS + 1) / 2;
    localparam integer RAD_W         = 2 * STAGES;
    localparam integer Q_W           = STAGES;
    //: rem' = 4*rem + d is the widest intermediate; 4*rem < 2**(Q_W+2).
    localparam integer REM_W         = STAGES + 4;
    localparam integer EXP_W         = 12;
    localparam integer LATENCY       = STAGES + 2;

    // ---- stage 0: unpack, normalise, force an even exponent ---------------
    wire [7:0]  in_biased  = argument_code[30:23];
    wire [22:0] in_fraction = argument_code[22:0];
    wire in_nonfinite = (in_biased == 8'hff);
    wire in_zero      = (argument_code[30:0] == 31'b0);
    wire in_negative  = argument_code[31] && !in_zero;
    wire in_subnormal = (in_biased == 8'b0);

    //: Leading-zero normalisation of a subnormal fraction.  The loop is a
    //: priority encoder over 23 bits, one combinational stage, not a walk over
    //: a vector.
    integer bit_index;
    reg [4:0] leading_shift;
    always @* begin
        leading_shift = 5'd23;
        for (bit_index = 0; bit_index < 23; bit_index = bit_index + 1)
            if (in_fraction[bit_index])
                leading_shift = 5'd22 - bit_index[4:0];
    end

    wire [23:0] normal_significand = {1'b1, in_fraction};
    wire [23:0] subnormal_significand =
        {1'b0, in_fraction} << leading_shift;
    wire [23:0] significand =
        in_subnormal ? subnormal_significand : normal_significand;
    wire signed [EXP_W-1:0] argument_exponent = in_subnormal
        ? (-12'sd149 - $signed({7'b0, leading_shift}))
        : ($signed({4'b0, in_biased}) - 12'sd150);

    wire exponent_odd = argument_exponent[0];
    wire [24:0] even_significand = exponent_odd
        ? {significand, 1'b0} : {1'b0, significand};
    wire signed [EXP_W-1:0] even_exponent = exponent_odd
        ? (argument_exponent - 12'sd1) : argument_exponent;
    //: even_exponent is even, so the arithmetic shift is an exact halving.
    wire signed [EXP_W-1:0] half_exponent = even_exponent >>> 1;

    reg                     s0_valid;
    reg [RAD_W-1:0]         s0_radicand;
    reg signed [EXP_W-1:0]  s0_half_exponent;
    reg                     s0_zero;
    reg                     s0_argument_error;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s0_valid <= 1'b0;
            s0_radicand <= {RAD_W{1'b0}};
            s0_half_exponent <= {EXP_W{1'b0}};
            s0_zero <= 1'b0;
            s0_argument_error <= 1'b0;
        end else begin
            s0_valid <= in_valid;
            //: Zero-extended, never left-aligned: the recurrence roots the
            //: register's VALUE, so padding has to be on the high side.
            s0_radicand <= {{(RAD_W - RADICAND_BITS){1'b0}},
                            even_significand,
                            {(2 * FRAC_SHIFT){1'b0}}};
            s0_half_exponent <= half_exponent;
            s0_zero <= in_zero;
            s0_argument_error <= in_nonfinite || in_negative;
        end
    end

    // ---- stages 1..STAGES: one digit of the recurrence per stage ----------
    reg [RAD_W-1:0]        rad_stage   [1:STAGES];
    reg [REM_W-1:0]        rem_stage   [1:STAGES];
    reg [Q_W-1:0]          root_stage  [1:STAGES];
    reg                    valid_stage [1:STAGES];
    reg signed [EXP_W-1:0] half_stage  [1:STAGES];
    reg                    zero_stage  [1:STAGES];
    reg                    error_stage [1:STAGES];

    integer stage;
    reg [RAD_W-1:0] source_radicand;
    reg [REM_W-1:0] source_remainder;
    reg [Q_W-1:0]   source_root;
    reg [REM_W-1:0] shifted_remainder;
    reg [REM_W-1:0] trial;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (stage = 1; stage <= STAGES; stage = stage + 1) begin
                rad_stage[stage] <= {RAD_W{1'b0}};
                rem_stage[stage] <= {REM_W{1'b0}};
                root_stage[stage] <= {Q_W{1'b0}};
                valid_stage[stage] <= 1'b0;
                half_stage[stage] <= {EXP_W{1'b0}};
                zero_stage[stage] <= 1'b0;
                error_stage[stage] <= 1'b0;
            end
        end else begin
            for (stage = 1; stage <= STAGES; stage = stage + 1) begin
                if (stage == 1) begin
                    source_radicand = s0_radicand;
                    source_remainder = {REM_W{1'b0}};
                    source_root = {Q_W{1'b0}};
                    valid_stage[stage] <= s0_valid;
                    half_stage[stage] <= s0_half_exponent;
                    zero_stage[stage] <= s0_zero;
                    error_stage[stage] <= s0_argument_error;
                end else begin
                    source_radicand = rad_stage[stage-1];
                    source_remainder = rem_stage[stage-1];
                    source_root = root_stage[stage-1];
                    valid_stage[stage] <= valid_stage[stage-1];
                    half_stage[stage] <= half_stage[stage-1];
                    zero_stage[stage] <= zero_stage[stage-1];
                    error_stage[stage] <= error_stage[stage-1];
                end
                shifted_remainder =
                    {source_remainder[REM_W-3:0], source_radicand[RAD_W-1:RAD_W-2]};
                trial = ({{(REM_W-Q_W){1'b0}}, source_root} << 2) | {{(REM_W-1){1'b0}}, 1'b1};
                if (shifted_remainder >= trial) begin
                    rem_stage[stage] <= shifted_remainder - trial;
                    root_stage[stage] <= {source_root[Q_W-2:0], 1'b1};
                end else begin
                    rem_stage[stage] <= shifted_remainder;
                    root_stage[stage] <= {source_root[Q_W-2:0], 1'b0};
                end
                rad_stage[stage] <= {source_radicand[RAD_W-3:0], 2'b00};
            end
        end
    end

    // ---- final stage: normalise the integer root and round once -----------
    wire [Q_W-1:0]         final_root      = root_stage[STAGES];
    wire [REM_W-1:0]       final_remainder = rem_stage[STAGES];
    wire signed [EXP_W-1:0] final_half     = half_stage[STAGES];

    integer root_bit;
    reg [7:0] root_bits;
    always @* begin
        root_bits = 8'd0;
        for (root_bit = 0; root_bit < Q_W; root_bit = root_bit + 1)
            if (final_root[root_bit])
                root_bits = root_bit[7:0] + 8'd1;
    end

    wire [7:0] drop = root_bits - 8'd24;
    wire round_supported = (root_bits >= 8'd26);
    //: Narrowed explicitly: a bit index into a Q_W-wide value must be exactly
    //: $clog2(Q_W) bits wide, because a wider index is a truncation warning and a
    //: truncation warning on an index is how a -Wno-fatal build hides a wrong
    //: answer.  round_supported proves drop >= 2, so drop-1 does not underflow.
    localparam integer DROP_W = (Q_W <= 2) ? 1 : $clog2(Q_W);
    wire [DROP_W-1:0] guard_index = drop[DROP_W-1:0] - {{(DROP_W-1){1'b0}}, 1'b1};
    //: Bits discarded below the round bit, plus the recurrence remainder: the
    //: remainder is nonzero exactly when the root is inexact, so together they
    //: are the true sticky bit.
    wire [Q_W-1:0] low_mask =
        ({{(Q_W-1){1'b0}}, 1'b1} << guard_index) - {{(Q_W-1){1'b0}}, 1'b1};
    wire sticky = (|(final_root & low_mask)) || (|final_remainder);
    wire guard = final_root[guard_index];
    wire [Q_W-1:0] shifted_root = final_root >> drop;
    wire [24:0] truncated = {1'b0, shifted_root[23:0]};
    wire round_up = guard && (sticky || truncated[0]);
    wire [25:0] rounded = {1'b0, truncated} + {25'b0, round_up};
    wire carried = rounded[24];
    wire [23:0] significand_out = carried ? rounded[24:1] : rounded[23:0];
    wire signed [EXP_W-1:0] unbiased =
        $signed({4'b0, root_bits}) - 12'sd1 + final_half
        - $signed(FRAC_SHIFT[EXP_W-1:0]) + (carried ? 12'sd1 : 12'sd0);
    wire signed [EXP_W-1:0] biased = unbiased + 12'sd127;
    wire biased_out_of_range = (biased < 12'sd1) || (biased > 12'sd254);

    reg        out_valid_q;
    reg [31:0] out_code_q;
    reg [1:0]  out_error_q;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_valid_q <= 1'b0;
            out_code_q <= 32'b0;
            out_error_q <= ERR_NONE;
        end else begin
            out_valid_q <= valid_stage[STAGES];
            if (error_stage[STAGES]) begin
                out_code_q <= 32'b0;
                out_error_q <= ERR_ARGUMENT;
            end else if (zero_stage[STAGES]) begin
                out_code_q <= 32'b0;
                out_error_q <= ERR_NONE;
            end else if (!round_supported || biased_out_of_range) begin
                out_code_q <= 32'b0;
                out_error_q <= ERR_RANGE;
            end else begin
                out_code_q <=
                    {1'b0, biased[7:0], significand_out[22:0]};
                out_error_q <= ERR_NONE;
            end
        end
    end

    assign out_valid = out_valid_q;
    assign result_code = out_code_q;
    assign result_error = out_error_q;
endmodule
