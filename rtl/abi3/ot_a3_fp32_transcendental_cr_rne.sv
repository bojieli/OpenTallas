`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Certifying finite-binary32 exponential / logistic-sigmoid engine.
//
// OP_EXP_NONPOS computes correctly rounded exp(x) for finite x <= 0.
// OP_SIGMOID computes correctly rounded 1/(1+exp(-x)) for any finite x.
//
// No input- or output-indexed result table is present.  The datapath converts
// |x|/256 exactly to Q0.FRAC_BITS, encloses exp(-|x|/256) with an alternating
// Taylor interval, and squares that interval eight times.  Sigmoid applies its
// monotone rational transform to the still-wide interval before either bound
// is rounded.  A result is published only when independently rounding both
// enclosing endpoints to binary32 RNE gives the same code.  An interval that
// is too wide fails closed instead of guessing a bit.
//
// FRAC_BITS >= 157 represents every finite binary32 fraction used by this
// range reduction exactly.  SERIES_TERMS must be positive and even; |x| < 150
// makes y=|x|/256 < 0.586, so the Taylor terms decrease from the start and the
// next omitted term encloses the alternating-series remainder.  All fixed-
// point multiplications retain a lower floor and upper ceil endpoint.
// ---------------------------------------------------------------------------
module ot_a3_fp32_transcendental_cr_rne #(
    parameter integer FRAC_BITS = 160,
    parameter integer SERIES_TERMS = 56
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        in_valid,
    output wire        in_ready,
    input  wire        operation,
    input  wire [31:0] argument_code,
    output reg         out_valid,
    input  wire        out_ready,
    output reg  [31:0] result_code,
    output reg  [1:0]  result_error
);
    localparam OP_EXP_NONPOS = 1'b0;
    localparam OP_SIGMOID = 1'b1;

    localparam [1:0] ERR_NONE = 2'd0;
    localparam [1:0] ERR_ARGUMENT = 2'd1;
    localparam [1:0] ERR_UNCERTIFIED = 2'd2;

    localparam [30:0] MAG_25 = 31'h41c8_0000;
    localparam [30:0] MAG_150 = 31'h4316_0000;
    localparam [31:0] FP32_HALF = 32'h3f00_0000;
    localparam [31:0] FP32_ONE = 32'h3f80_0000;

    localparam [2:0] S_IDLE = 3'd0;
    localparam [2:0] S_SERIES = 3'd1;
    localparam [2:0] S_SQUARE = 3'd2;
    localparam [2:0] S_TRANSFORM = 3'd3;
    localparam [2:0] S_CERTIFY = 3'd4;
    localparam [2:0] S_OUT = 3'd5;

    // One is exactly bit FRAC_BITS in every Q0.FRAC_BITS value.
    localparam [FRAC_BITS+2:0] FIXED_ONE =
        {{2{1'b0}}, 1'b1, {FRAC_BITS{1'b0}}};

    function automatic [FRAC_BITS:0] magnitude_div256_fixed;
        input [30:0] code;
        reg [7:0] exponent_field;
        reg [23:0] significand;
        reg [FRAC_BITS:0] wide_significand;
        integer shift_distance;
        begin
            exponent_field = code[30:23];
            significand = exponent_field == 0
                ? {1'b0, code[22:0]} : {1'b1, code[22:0]};
            wide_significand = {{(FRAC_BITS-23){1'b0}}, significand};
            magnitude_div256_fixed = 0;
            // Normal value = significand * 2**(field-150).  Dividing by
            // 256 and expressing in Q.FRAC_BITS gives this exact shift.
            shift_distance = exponent_field == 0
                ? FRAC_BITS - 157
                : FRAC_BITS + {24'b0, exponent_field} - 158;
            if (shift_distance >= 0)
                magnitude_div256_fixed =
                    wide_significand << shift_distance;
            else
                magnitude_div256_fixed = wide_significand >> -shift_distance;
        end
    endfunction

    function automatic [31:0] fixed_to_fp32_rne;
        input [FRAC_BITS+2:0] fixed_code;
        reg [23:0] main_mantissa;
        reg [24:0] rounded_mantissa;
        reg [7:0] encoded_exponent;
        reg round_bit;
        reg sticky;
        integer most_significant;
        integer floor_exponent;
        integer shift_distance;
        integer bit_index;
        begin
            main_mantissa = 0;
            rounded_mantissa = 0;
            encoded_exponent = 0;
            round_bit = 0;
            sticky = 0;
            most_significant = -1;
            floor_exponent = 0;
            shift_distance = 0;
            fixed_to_fp32_rne = 0;

            for (bit_index = 0; bit_index < FRAC_BITS + 3;
                 bit_index = bit_index + 1)
                if (fixed_code[bit_index])
                    most_significant = bit_index;

            if (most_significant >= 0) begin
                floor_exponent = most_significant - FRAC_BITS;
                if (floor_exponent >= -126) begin
                    shift_distance = most_significant - 23;
                    for (bit_index = 0; bit_index < 24;
                         bit_index = bit_index + 1)
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
                    encoded_exponent = floor_exponent[7:0] + 8'd127;
                    fixed_to_fp32_rne = {
                        1'b0, encoded_exponent, rounded_mantissa[22:0]
                    };
                end else begin
                    // Binary32 subnormal LSB is 2**-149.
                    shift_distance = FRAC_BITS - 149;
                    for (bit_index = 0; bit_index < 24;
                         bit_index = bit_index + 1)
                        if (bit_index + shift_distance < FRAC_BITS + 3)
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
                    if (rounded_mantissa >= 25'h0800000)
                        fixed_to_fp32_rne = 32'h0080_0000;
                    else
                        fixed_to_fp32_rne = {9'b0, rounded_mantissa[22:0]};
                end
            end
        end
    endfunction

    reg [2:0] state;
    reg operation_q;
    reg argument_sign;
    reg [7:0] term_index;
    reg [3:0] square_index;
    reg [FRAC_BITS:0] reduced_argument;
    reg [FRAC_BITS+2:0] term_lower;
    reg [FRAC_BITS+2:0] term_upper;
    reg [FRAC_BITS+2:0] sum_lower;
    reg [FRAC_BITS+2:0] sum_upper;
    reg [FRAC_BITS+2:0] interval_lower;
    reg [FRAC_BITS+2:0] interval_upper;

    wire [8:0] next_term_index = {1'b0, term_index} + 1'b1;

    // The Taylor recurrence only divides by the next term number (1..57 at
    // the default configuration).  Express that bounded small division as a
    // restoring divider rather than SystemVerilog's general-purpose wide
    // ``/`` and ``%`` operators.  Besides mapping to a much smaller circuit,
    // this avoids asking event-driven simulators to build and reevaluate two
    // arbitrary-width dividers for every Taylor term.  The low nine returned
    // bits are the exact remainder; the remaining bits are the quotient.
    function automatic [FRAC_BITS+16:0] divide_by_small;
        input [FRAC_BITS+7:0] dividend;
        input [8:0] divisor;
        reg [FRAC_BITS+7:0] quotient;
        reg [8:0] remainder;
        reg [9:0] shifted_remainder;
        integer divide_bit;
        begin
            quotient = 0;
            remainder = 0;
            shifted_remainder = 0;
            for (divide_bit = FRAC_BITS + 7; divide_bit >= 0;
                 divide_bit = divide_bit - 1) begin
                shifted_remainder = {
                    remainder[8:0], dividend[divide_bit]
                };
                if (shifted_remainder >= {1'b0, divisor}) begin
                    remainder =
                        shifted_remainder[8:0] - divisor;
                    quotient[divide_bit] = 1'b1;
                end else begin
                    remainder = shifted_remainder[8:0];
                end
            end
            divide_by_small = {quotient, remainder[8:0]};
        end
    endfunction

    reg [2*FRAC_BITS+7:0] lower_product;
    reg [2*FRAC_BITS+7:0] upper_product;
    reg [FRAC_BITS+7:0] lower_product_integer;
    reg [FRAC_BITS+7:0] upper_product_integer;
    reg [FRAC_BITS+16:0] lower_division;
    reg [FRAC_BITS+16:0] upper_division;
    reg [FRAC_BITS+2:0] next_term_lower;
    reg [FRAC_BITS+2:0] next_term_upper;
    reg upper_fraction_nonzero;
    reg upper_division_remainder;

    always @* begin
        lower_product =
            {{(FRAC_BITS+5){1'b0}}, term_lower} * reduced_argument;
        upper_product =
            {{(FRAC_BITS+5){1'b0}}, term_upper} * reduced_argument;
        lower_product_integer =
            lower_product[2*FRAC_BITS+7:FRAC_BITS];
        upper_product_integer =
            upper_product[2*FRAC_BITS+7:FRAC_BITS];
        upper_fraction_nonzero = |upper_product[FRAC_BITS-1:0];
        lower_division = divide_by_small(
            lower_product_integer, next_term_index
        );
        upper_division = divide_by_small(
            upper_product_integer, next_term_index
        );
        next_term_lower = lower_division[FRAC_BITS+11:9];
        next_term_upper = upper_division[FRAC_BITS+11:9];
        upper_division_remainder =
            (upper_division[8:0] != 0) ||
            upper_fraction_nonzero;
        if (upper_division_remainder)
            next_term_upper = next_term_upper + 1'b1;
    end

    reg [2*FRAC_BITS+7:0] square_lower_product;
    reg [2*FRAC_BITS+7:0] square_upper_product;
    reg [FRAC_BITS+2:0] square_lower;
    reg [FRAC_BITS+2:0] square_upper;
    reg square_upper_fraction;

    always @* begin
        square_lower_product = interval_lower * interval_lower;
        square_upper_product = interval_upper * interval_upper;
        square_lower =
            square_lower_product[2*FRAC_BITS+2:FRAC_BITS];
        square_upper =
            square_upper_product[2*FRAC_BITS+2:FRAC_BITS];
        square_upper_fraction = |square_upper_product[FRAC_BITS-1:0];
        if (square_upper_fraction)
            square_upper = square_upper + 1'b1;
    end

    reg [2*FRAC_BITS+7:0] transform_lower_numerator;
    reg [2*FRAC_BITS+7:0] transform_upper_numerator;
    reg [FRAC_BITS+3:0] transform_lower_denominator;
    reg [FRAC_BITS+3:0] transform_upper_denominator;
    reg [FRAC_BITS+2:0] transformed_lower;
    reg [FRAC_BITS+2:0] transformed_upper;
    reg [FRAC_BITS+3:0] transform_lower_division;
    reg [FRAC_BITS+3:0] transform_upper_division;

    // Exact restoring division for the sigmoid rational transform.  The
    // quotient is bounded by one in Q0.FRAC_BITS, so FRAC_BITS+3 quotient
    // bits cover the entire legal result.  The returned least-significant bit
    // says whether the exact division had a nonzero remainder and therefore
    // whether the enclosing upper endpoint must be rounded upward.
    function automatic [FRAC_BITS+3:0] divide_fixed_ratio;
        input [2*FRAC_BITS+7:0] numerator;
        input [FRAC_BITS+3:0] denominator;
        reg [FRAC_BITS+2:0] quotient;
        reg [FRAC_BITS+3:0] remainder;
        reg [FRAC_BITS+4:0] shifted_remainder;
        reg [FRAC_BITS+4:0] remainder_difference;
        integer divide_bit;
        begin
            quotient = 0;
            remainder = 0;
            shifted_remainder = 0;
            remainder_difference = 0;
            for (divide_bit = 2*FRAC_BITS + 7; divide_bit >= 0;
                 divide_bit = divide_bit - 1) begin
                shifted_remainder = {
                    remainder, numerator[divide_bit]
                };
                if (shifted_remainder >= {1'b0, denominator}) begin
                    remainder_difference =
                        shifted_remainder - {1'b0, denominator};
                    remainder = remainder_difference[FRAC_BITS+3:0];
                    if (divide_bit <= FRAC_BITS + 2)
                        quotient[divide_bit] = 1'b1;
                end else begin
                    remainder = shifted_remainder[FRAC_BITS+3:0];
                end
            end
            divide_fixed_ratio = {quotient, remainder != 0};
        end
    endfunction

    always @* begin
        transform_lower_numerator = 0;
        transform_upper_numerator = 0;
        transform_lower_denominator = 1;
        transform_upper_denominator = 1;
        transformed_lower = interval_lower;
        transformed_upper = interval_upper;
        transform_lower_division = 0;
        transform_upper_division = 0;
        // The two wide rational divisions are meaningful only once, after
        // range reconstruction has completed.  Qualifying them by state is
        // important both for clock-gated hardware and for RTL simulation:
        // without this guard they are reevaluated after every squaring step.
        if (state == S_TRANSFORM && operation_q == OP_SIGMOID) begin
            if (argument_sign) begin
                // e/(1+e), monotonically increasing.
                transform_lower_numerator = {
                    5'b0, interval_lower, {FRAC_BITS{1'b0}}
                };
                transform_upper_numerator = {
                    5'b0, interval_upper, {FRAC_BITS{1'b0}}
                };
                transform_lower_denominator = FIXED_ONE + interval_lower;
                transform_upper_denominator = FIXED_ONE + interval_upper;
            end else begin
                // 1/(1+e), monotonically decreasing.
                transform_lower_numerator[2*FRAC_BITS] = 1'b1;
                transform_upper_numerator[2*FRAC_BITS] = 1'b1;
                transform_lower_denominator = FIXED_ONE + interval_upper;
                transform_upper_denominator = FIXED_ONE + interval_lower;
            end
            transform_lower_division = divide_fixed_ratio(
                transform_lower_numerator, transform_lower_denominator
            );
            transform_upper_division = divide_fixed_ratio(
                transform_upper_numerator, transform_upper_denominator
            );
            transformed_lower =
                transform_lower_division[FRAC_BITS+3:1];
            transformed_upper =
                transform_upper_division[FRAC_BITS+3:1];
            if (transform_upper_division[0])
                transformed_upper = transformed_upper + 1'b1;
        end
    end

    wire [31:0] rounded_lower = fixed_to_fp32_rne(interval_lower);
    wire [31:0] rounded_upper = fixed_to_fp32_rne(interval_upper);
    wire argument_nonfinite = argument_code[30:23] == 8'hff;
    wire argument_zero = argument_code[30:0] == 0;

    assign in_ready = state == S_IDLE && (!out_valid || out_ready);

    initial begin
        if (FRAC_BITS < 157)
            $error("FRAC_BITS must be at least 157");
        if (SERIES_TERMS <= 0 || ((SERIES_TERMS & 1) != 0) ||
            SERIES_TERMS > 254)
            $error("SERIES_TERMS must be positive and even");
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            operation_q <= OP_EXP_NONPOS;
            argument_sign <= 1'b0;
            term_index <= 0;
            square_index <= 0;
            reduced_argument <= 0;
            term_lower <= 0;
            term_upper <= 0;
            sum_lower <= 0;
            sum_upper <= 0;
            interval_lower <= 0;
            interval_upper <= 0;
            out_valid <= 1'b0;
            result_code <= 0;
            result_error <= ERR_NONE;
        end else begin
            if (out_valid && out_ready)
                out_valid <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (in_valid && in_ready) begin
                        operation_q <= operation;
                        argument_sign <= argument_code[31];
                        result_code <= 0;
                        result_error <= ERR_NONE;
                        if (argument_nonfinite ||
                            (operation == OP_EXP_NONPOS &&
                             !argument_code[31] && !argument_zero)) begin
                            result_error <= ERR_ARGUMENT;
                            out_valid <= 1'b1;
                            state <= S_OUT;
                        end else if (argument_zero) begin
                            result_code <= operation == OP_EXP_NONPOS
                                ? FP32_ONE : FP32_HALF;
                            out_valid <= 1'b1;
                            state <= S_OUT;
                        end else if (operation == OP_EXP_NONPOS &&
                                     argument_code[30:0] >= MAG_150) begin
                            result_code <= 0;
                            out_valid <= 1'b1;
                            state <= S_OUT;
                        end else if (operation == OP_SIGMOID &&
                                     !argument_code[31] &&
                                     argument_code[30:0] >= MAG_25) begin
                            result_code <= FP32_ONE;
                            out_valid <= 1'b1;
                            state <= S_OUT;
                        end else if (operation == OP_SIGMOID &&
                                     argument_code[31] &&
                                     argument_code[30:0] >= MAG_150) begin
                            result_code <= 0;
                            out_valid <= 1'b1;
                            state <= S_OUT;
                        end else begin
                            reduced_argument <=
                                magnitude_div256_fixed(argument_code[30:0]);
                            term_index <= 0;
                            term_lower <= FIXED_ONE;
                            term_upper <= FIXED_ONE;
                            sum_lower <= FIXED_ONE;
                            sum_upper <= FIXED_ONE;
                            state <= S_SERIES;
                        end
                    end
                end

                S_SERIES: begin
                    if ({24'b0, term_index} < SERIES_TERMS) begin
                        term_lower <= next_term_lower;
                        term_upper <= next_term_upper;
                        term_index <= term_index + 1'b1;
                        if (!next_term_index[0]) begin
                            sum_lower <= sum_lower + next_term_lower;
                            sum_upper <= sum_upper + next_term_upper;
                        end else begin
                            sum_lower <= sum_lower - next_term_upper;
                            sum_upper <= sum_upper - next_term_lower;
                        end
                    end else begin
                        // SERIES_TERMS is even, so its partial sum is the
                        // upper alternating bound and the next odd term gives
                        // the lower bound.
                        interval_lower <= sum_lower - next_term_upper;
                        interval_upper <= sum_upper;
                        square_index <= 0;
                        state <= S_SQUARE;
                    end
                end

                S_SQUARE: begin
                    interval_lower <= square_lower;
                    interval_upper <= square_upper;
                    if (square_index == 7) begin
                        state <= operation_q == OP_SIGMOID
                            ? S_TRANSFORM : S_CERTIFY;
                    end else begin
                        square_index <= square_index + 1'b1;
                    end
                end

                S_TRANSFORM: begin
                    interval_lower <= transformed_lower;
                    interval_upper <= transformed_upper;
                    state <= S_CERTIFY;
                end

                S_CERTIFY: begin
                    if (rounded_lower == rounded_upper) begin
                        result_code <= rounded_lower;
                        result_error <= ERR_NONE;
                    end else begin
                        result_code <= 0;
                        result_error <= ERR_UNCERTIFIED;
                    end
                    out_valid <= 1'b1;
                    state <= S_OUT;
                end

                S_OUT: begin
                    if (out_valid && out_ready)
                        state <= S_IDLE;
                end

                default: begin
                    result_code <= 0;
                    result_error <= ERR_ARGUMENT;
                    out_valid <= 1'b1;
                    state <= S_OUT;
                end
            endcase
        end
    end
endmodule
