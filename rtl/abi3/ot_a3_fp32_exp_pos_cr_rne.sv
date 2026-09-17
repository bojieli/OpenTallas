`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Certifying correctly-rounded binary32 exponential for POSITIVE arguments.
//
// ot_a3_fp32_transcendental_cr_rne's OP_EXP_NONPOS covers finite x <= 0 and
// REFUSES a positive one, because its enclosure is Q0.FRAC_BITS with three
// integer bits -- sized for exp(-|x|), which lives in (0, 1]. ATTENTION.SPARSE
// needs the other side: its sink term is exp(sink - maxima), the sink never
// joins the running maximum, and 2,680 of the 2,944 shipped V4-Flash sink logits
// are POSITIVE (1,961 of 2,752 for V4.1), so a positive offset is the common
// case rather than a corner. VECTOR.SQRT_SOFTPLUS needs it too:
// softplus(x) = log(1 + exp(x)) has the same argument range.
//
// RANGE REDUCTION BY ln2 IS WHAT MAKES THIS FIT. Write x = n*ln2 + r with r in
// [0, ln2); then exp(x) = 2**n * exp(r) and exp(r) lies in [1, 2) -- ONE integer
// bit. The power of two becomes the binary32 EXPONENT rather than a wide shift,
// which is the representation the rounding already builds, so nothing needs a
// wider datapath. Reducing by 256 as the other unit does would leave the result
// needing up to 127 integer bits; this needs one.
//
// THE SERIES IS ALL-POSITIVE HERE, so the remainder bound is NOT "the next
// omitted term" -- that rule belongs to the alternating series the other unit
// sums. For r < 1 the terms decrease and the tail is geometric:
//
//     sum_{k>N} r^k/k!  <=  term_{N+1} / (1 - r)  <  term_{N+1} * 4
//
// since r < ln2 < 0.75 gives 1/(1-r) < 3.26 < 4. The upper endpoint therefore
// adds the next term shifted left by two, which is exact and never
// under-estimates. At SERIES_TERMS = 56 that bound is ~7e-86, far past the
// FRAC_BITS the format carries.
//
// THREE THINGS HERE ARE DEFENSIVE AND UNREACHABLE AT THESE CONSTANT WIDTHS, and
// that is recorded rather than presented as covered, because mutants that remove
// each of them pass every one of the 2,201 qualification arguments:
//
//   * BOTH FLOOR FIXUPS. ln2 and log2(e) are floored to FRAC_BITS fractional
//     bits, so the estimated n can be low by at most x*(log2e - LOG2E/2**160) <
//     88.7 * 2**-160 = 6.1e-47. Measured over 40,508 arguments -- every multiple
//     of ln2 in range, both neighbours of each, and 40,000 random -- the closest
//     x*log2(e) ever came to an integer was 2.7e-09, which is 125 binary orders
//     above that bound, and neither fixup ever fired. They stay because the
//     bound is an argument about these widths and the fixup is a property of the
//     code: narrow FRAC_BITS and the fixup is what keeps it correct.
//   * THE GEOMETRIC TAIL. At SERIES_TERMS = 56 the remainder is ~7e-86, which is
//     some sixty binary orders below the 24-bit rounding boundary, so both
//     endpoints round alike whether or not the tail is added. It stays because
//     the ENCLOSURE is the claim: an interval that does not contain the result is
//     wrong even when it rounds right, and a smaller SERIES_TERMS would expose it.
//
// FAILS CLOSED, LIKE ITS SIBLING. A nonpositive or nonfinite argument is
// ERR_ARGUMENT; an interval whose two endpoints do not round to the same
// binary32 is ERR_UNCERTIFIED and publishes no result; a result beyond the
// finite range is ERR_OVERFLOW rather than an infinity.
// ---------------------------------------------------------------------------
module ot_a3_fp32_exp_pos_cr_rne #(
    parameter integer FRAC_BITS = 160,
    parameter integer SERIES_TERMS = 56,
    //: Integer bits the reduction needs: the argument is bounded below 150, and
    //: n*ln2 tracks it, so eight covers both with room.
    parameter integer INT_BITS = 9
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        in_valid,
    output wire        in_ready,
    input  wire [31:0] argument_code,
    output reg         out_valid,
    input  wire        out_ready,
    output reg  [31:0] result_code,
    output reg  [1:0]  result_error
);
    localparam [1:0] ERR_NONE = 2'd0;
    localparam [1:0] ERR_ARGUMENT = 2'd1;
    localparam [1:0] ERR_UNCERTIFIED = 2'd2;
    localparam [1:0] ERR_OVERFLOW = 2'd3;

    //: exp(x) exceeds the largest finite binary32 above ~88.73, so an argument
    //: at or beyond 128 cannot produce one and is refused before any work.
    localparam [30:0] MAG_128 = 31'h4300_0000;

    localparam integer WIDE = FRAC_BITS + INT_BITS;

    //: ln 2 and log2 e to FRAC_BITS fractional bits, floored. Both are exact
    //: constants of the format, computed once and checked against the reference
    //: in tools/build_a3_exp_pos_vectors.py rather than trusted.
    localparam [FRAC_BITS:0] LN2 =
        161'h0b17217f7d1cf79abc9e3b39803f2f6af40f34326;
    localparam [FRAC_BITS+1:0] LOG2E =
        162'h171547652b82fe1777d0ffda0d23a7d11d6aef551;

    localparam [2:0] S_IDLE   = 3'd0;
    localparam [2:0] S_REDUCE = 3'd1;
    localparam [2:0] S_FIXUP  = 3'd2;
    localparam [2:0] S_SERIES = 3'd3;
    localparam [2:0] S_CERTIFY = 3'd4;
    localparam [2:0] S_OUT    = 3'd5;
    reg [2:0] state;

    integer i;

    reg [WIDE:0]      x_fixed;        //: the argument, Q(INT_BITS).FRAC_BITS
    reg signed [15:0] n_power;        //: the extracted power of two
    reg [FRAC_BITS:0] reduced;        //: r, in [0, ln2)
    reg [8:0]         term_index;
    reg [FRAC_BITS+2:0] term_lower, term_upper;
    reg [FRAC_BITS+2:0] sum_lower, sum_upper;
    reg [FRAC_BITS+2:0] interval_lower, interval_upper;

    assign in_ready = (state == S_IDLE) && (!out_valid || out_ready);

    wire        arg_nonfinite = (argument_code[30:23] == 8'hff);
    wire        arg_nonpositive = argument_code[31] ||
                                  (argument_code[30:0] == 31'd0);
    wire        arg_too_large = (argument_code[30:0] >= MAG_128);

    //: The argument as Q(INT_BITS).FRAC_BITS. Finite binary32 below 128 needs
    //: seven integer bits, so nothing is lost.
    function automatic [WIDE:0] to_fixed;
        input [30:0] code;
        reg [7:0] field;
        reg [23:0] significand;
        reg [WIDE:0] wide;
        integer shift;
        begin
            field = code[30:23];
            significand = (field == 8'd0) ? {1'b0, code[22:0]}
                                          : {1'b1, code[22:0]};
            wide = {{(WIDE-23){1'b0}}, significand};
            //: value = significand * 2**(field-127-23)
            //: value = significand * 2**(field - 150), so the Q.FRAC_BITS
            //: position is FRAC_BITS - 150 + field. Widened to the integer the
            //: expression is evaluated in.
            shift = (field == 8'd0) ? (FRAC_BITS - 149)
                                    : (FRAC_BITS - 150 + {24'd0, field});
            if (shift >= 0) to_fixed = wide << shift;
            else            to_fixed = wide >> (-shift);
        end
    endfunction

    //: Round a Q0.FRAC_BITS enclosure endpoint to binary32, scaled by 2**power.
    //: This is ot_a3_fp32_transcendental_cr_rne's fixed_to_fp32_rne with the
    //: exponent offset the range reduction produces, and the overflow check that
    //: offset makes reachable.
    function automatic [32:0] fixed_to_fp32_scaled;
        input [FRAC_BITS+2:0] fixed_code;
        //: ``integer`` is already signed; Icarus 11 rejects the redundant keyword.
        input integer         power;
        reg [23:0] main_mantissa;
        reg [24:0] rounded_mantissa;
        reg round_bit, sticky;
        integer most_significant, bit_index, shift_distance;
        integer floor_exponent;
        begin
            main_mantissa = 0; rounded_mantissa = 0;
            round_bit = 0; sticky = 0;
            most_significant = -1; shift_distance = 0;
            fixed_to_fp32_scaled = 33'd0;
            for (bit_index = 0; bit_index < FRAC_BITS + 3;
                 bit_index = bit_index + 1)
                if (fixed_code[bit_index]) most_significant = bit_index;
            if (most_significant >= 0) begin
                floor_exponent = most_significant - FRAC_BITS + power;
                shift_distance = most_significant - 23;
                for (bit_index = 0; bit_index < 24; bit_index = bit_index + 1)
                    if ((bit_index + shift_distance >= 0) &&
                        (bit_index + shift_distance < FRAC_BITS + 3))
                        main_mantissa[bit_index] =
                            fixed_code[bit_index + shift_distance];
                if (shift_distance > 0)
                    round_bit = fixed_code[shift_distance-1];
                for (bit_index = 0; bit_index < FRAC_BITS + 3;
                     bit_index = bit_index + 1)
                    if (bit_index < shift_distance-1)
                        sticky = sticky | fixed_code[bit_index];
                rounded_mantissa = {1'b0, main_mantissa};
                if (round_bit && (sticky || main_mantissa[0]))
                    rounded_mantissa = rounded_mantissa + 1'b1;
                if (rounded_mantissa[24]) begin
                    rounded_mantissa = rounded_mantissa >> 1;
                    floor_exponent = floor_exponent + 1;
                end
                //: A positive exponential cannot be subnormal, so the only
                //: encoding hazard here is overflow. Bit 32 flags it.
                if (floor_exponent > 127)
                    fixed_to_fp32_scaled = {1'b1, 32'd0};
                else
                    fixed_to_fp32_scaled = {1'b0, 1'b0,
                        floor_exponent[7:0] + 8'd127, rounded_mantissa[22:0]};
            end
        end
    endfunction

    //: The Taylor recurrence divides only by the next term number, so a bounded
    //: restoring divide -- the same shape ot_a3_fp32_transcendental_cr_rne uses,
    //: and for the same reason: a general wide `/` builds an enormous circuit and
    //: makes event-driven simulation crawl. The low bit returns whether the
    //: division was inexact, so the upper endpoint can round away from zero.
    function automatic [FRAC_BITS+3:0] divide_small;
        input [FRAC_BITS+2:0] dividend;
        input [8:0] divisor;
        reg [FRAC_BITS+2:0] quotient;
        reg [9:0] remainder;
        integer bit_index;
        begin
            quotient = 0;
            remainder = 0;
            for (bit_index = FRAC_BITS + 2; bit_index >= 0;
                 bit_index = bit_index - 1) begin
                remainder = {remainder[8:0], dividend[bit_index]};
                if (remainder >= {1'b0, divisor}) begin
                    remainder = remainder - {1'b0, divisor};
                    quotient[bit_index] = 1'b1;
                end
            end
            divide_small = {quotient, |remainder};
        end
    endfunction

    //: term_{k+1} = term_k * r / (k+1), both endpoints kept enclosing.
    wire [8:0] next_index = term_index + 9'd1;
    wire [2*FRAC_BITS+3:0] scaled_lower = term_lower * {2'b0, reduced};
    wire [2*FRAC_BITS+3:0] scaled_upper = term_upper * {2'b0, reduced};
    //: The product is Q0.(2*FRAC_BITS); take the high half as the lower endpoint
    //: and add one ulp when anything was discarded.
    wire [FRAC_BITS+2:0] prod_lower = scaled_lower[2*FRAC_BITS+2:FRAC_BITS];
    wire                 prod_lower_inexact = |scaled_lower[FRAC_BITS-1:0];
    wire [FRAC_BITS+2:0] prod_upper = scaled_upper[2*FRAC_BITS+2:FRAC_BITS] +
                                      {{(FRAC_BITS+2){1'b0}},
                                       (|scaled_upper[FRAC_BITS-1:0])};
    wire [FRAC_BITS+3:0] div_lower = divide_small(prod_lower, next_index);
    wire [FRAC_BITS+3:0] div_upper = divide_small(prod_upper, next_index);
    wire [FRAC_BITS+2:0] next_term_lower = div_lower[FRAC_BITS+3:1];
    wire [FRAC_BITS+2:0] next_term_upper = div_upper[FRAC_BITS+3:1] +
                                           {{(FRAC_BITS+2){1'b0}}, div_upper[0]};
    //: Unused, but named so the discarded-bit reasoning above is checkable.
    wire _unused_inexact = prod_lower_inexact;

    //: The geometric tail: remainder < term_{N+1} * 4 for r < 0.75.
    wire [FRAC_BITS+2:0] tail_bound = next_term_upper << 2;

    //: n * ln2, and the reduced argument.
    //: n * ln2 in Q(INT_BITS).FRAC_BITS. n is below 185 and ln2 below one, so
    //: the product stays under 128 and the integer field fits INT_BITS.
    wire [FRAC_BITS+17:0] n_times_ln2 =
        {{17{1'b0}}, LN2} * {{(FRAC_BITS+2){1'b0}}, n_power[15:0]};
    wire [WIDE:0] n_ln2_fixed = n_times_ln2[WIDE:0];

    //: Named, because indexing an EXPRESSION is rejected by both elaborators --
    //: the same shape as indexing a part-select, which has cost this session
    //: five compile failures.
    //: x_fixed is Q(INT_BITS).FRAC_BITS and LOG2E is Q1.FRAC_BITS, so the
    //: product is Q(INT_BITS+1).(2*FRAC_BITS) and needs every one of these bits.
    //: Sizing it at 2*FRAC_BITS+3 put the integer field past the end of the wire.
    wire [2*FRAC_BITS+INT_BITS+2:0] x_times_log2e = x_fixed * LOG2E;
    wire [8:0] n_estimate = x_times_log2e[2*FRAC_BITS+8 : 2*FRAC_BITS];
    wire [WIDE:0] x_minus_nln2 = x_fixed - n_ln2_fixed;
    wire [FRAC_BITS:0] reduced_next = x_minus_nln2[FRAC_BITS:0];

    reg [32:0] rounded_lower, rounded_upper;
    always @* begin
        rounded_lower = fixed_to_fp32_scaled(interval_lower, {{16{n_power[15]}}, n_power});
        rounded_upper = fixed_to_fp32_scaled(interval_upper, {{16{n_power[15]}}, n_power});
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            out_valid <= 1'b0; result_code <= 32'd0; result_error <= ERR_NONE;
            x_fixed <= {(WIDE+1){1'b0}}; n_power <= 16'sd0;
            reduced <= {(FRAC_BITS+1){1'b0}};
            term_index <= 9'd0;
            term_lower <= {(FRAC_BITS+3){1'b0}};
            term_upper <= {(FRAC_BITS+3){1'b0}};
            sum_lower <= {(FRAC_BITS+3){1'b0}};
            sum_upper <= {(FRAC_BITS+3){1'b0}};
            interval_lower <= {(FRAC_BITS+3){1'b0}};
            interval_upper <= {(FRAC_BITS+3){1'b0}};
        end else begin
            if (out_valid && out_ready) out_valid <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (in_valid && in_ready) begin
                        if (arg_nonfinite || arg_nonpositive) begin
                            result_code <= 32'd0;
                            result_error <= ERR_ARGUMENT;
                            out_valid <= 1'b1;
                            state <= S_OUT;
                        end else if (arg_too_large) begin
                            result_code <= 32'd0;
                            result_error <= ERR_OVERFLOW;
                            out_valid <= 1'b1;
                            state <= S_OUT;
                        end else begin
                            x_fixed <= to_fixed(argument_code[30:0]);
                            state <= S_REDUCE;
                        end
                    end
                end

                //: n = floor(x * log2 e), taken from the high bits of the
                //: product. It can be one low, never one high, and S_FIXUP
                //: corrects that against an EXACT r rather than trusting it.
                S_REDUCE: begin
                    n_power <= {7'd0, n_estimate};
                    state <= S_FIXUP;
                end

                S_FIXUP: begin
                    //: r = x - n*ln2, computed exactly in the wide format. If it
                    //: reached or passed ln2 the floor was one low, so take one
                    //: more power of two; the loop runs at most twice in
                    //: practice and the guard makes that a property, not a hope.
                    if (x_fixed < n_ln2_fixed) begin
                        n_power <= n_power - 16'sd1;
                    end else if (x_minus_nln2 >=
                                 {{(INT_BITS){1'b0}}, LN2}) begin
                        n_power <= n_power + 16'sd1;
                    end else begin
                        reduced <= reduced_next;
                        //: term_0 = 1, and the running sum starts there.
                        term_lower <= {2'b0, 1'b1, {FRAC_BITS{1'b0}}};
                        term_upper <= {2'b0, 1'b1, {FRAC_BITS{1'b0}}};
                        sum_lower <= {2'b0, 1'b1, {FRAC_BITS{1'b0}}};
                        sum_upper <= {2'b0, 1'b1, {FRAC_BITS{1'b0}}};
                        term_index <= 9'd0;
                        state <= S_SERIES;
                    end
                end

                S_SERIES: begin
                    if ({23'd0, term_index} < SERIES_TERMS) begin
                        term_lower <= next_term_lower;
                        term_upper <= next_term_upper;
                        term_index <= next_index;
                        //: ALL TERMS ARE POSITIVE, so both endpoints accumulate
                        //: additively -- no alternation.
                        sum_lower <= sum_lower + next_term_lower;
                        sum_upper <= sum_upper + next_term_upper;
                    end else begin
                        //: The truncated sum is the lower bound; the geometric
                        //: tail bounds what is left.
                        interval_lower <= sum_lower;
                        interval_upper <= sum_upper + tail_bound;
                        state <= S_CERTIFY;
                    end
                end

                S_CERTIFY: begin
                    if (rounded_lower[32] || rounded_upper[32]) begin
                        result_code <= 32'd0;
                        result_error <= ERR_OVERFLOW;
                    end else if (rounded_lower[31:0] == rounded_upper[31:0]) begin
                        result_code <= rounded_lower[31:0];
                        result_error <= ERR_NONE;
                    end else begin
                        result_code <= 32'd0;
                        result_error <= ERR_UNCERTIFIED;
                    end
                    out_valid <= 1'b1;
                    state <= S_OUT;
                end

                S_OUT: begin
                    if (out_valid && out_ready) state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
