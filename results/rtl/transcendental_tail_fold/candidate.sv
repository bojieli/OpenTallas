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
// EVERY WIDE MULTIPLY AND EVERY DIVISION HERE IS SEQUENTIAL, AND THAT IS WHY
// THIS BLOCK HAS AN ASAP7 RECORD AT ALL. It used to spell five wide products and
// four divisions as expressions in one cycle each, and the worst of them,
// ``divide_fixed_ratio``, unrolled a restoring loop over all 328 numerator bits
// with a 165-bit compare-and-subtract at every step -- some 54,000 levels of carry
// logic in a single cycle. That is not slow, it is unbuildable: a synthesis of
// this module ran EIGHT HOURS inside the pinned container and timed out in
// 1_2_yosys without producing a netlist, so the module had no ASAP7 number, and
// THIRTEEN of the design's twenty-seven uncovered modules sit behind it and its
// positive-argument sibling.
//
// The three primitives that replace them keep the arithmetic exactly:
// ot_wide_mul_seq (carry-save, so no cycle holds a wide carry chain),
// ot_wide_div_small_seq (the same restoring loop, ten bits per clock) and
// ot_wide_div_seq (one subtract per clock, because a 165-bit subtract is already
// 3.37 ns on ASAP7 and a second would halve the achievable clock). Each is
// checked against the expression it replaces over its own corpus in
// rtl/test/tb_wide_mul_seq_equiv.sv, tb_wide_div_small_seq_equiv.sv and
// tb_wide_div_seq_equiv.sv, so the enclosure, the certification and every refusal
// are the ones this module already published.
//
// FRAC_BITS >= 157 represents every finite binary32 fraction used by this
// range reduction exactly.  SERIES_TERMS must be positive and even; |x| < 150
// makes y=|x|/256 < 0.586, so the Taylor terms decrease from the start and the
// next omitted term encloses the alternating-series remainder.  All fixed-
// point multiplications retain a lower floor and upper ceil endpoint.
// ---------------------------------------------------------------------------
module ot_a3_fp32_transcendental_cr_rne #(
    parameter integer FRAC_BITS = 160,
    parameter integer SERIES_TERMS = 56,
    parameter bit ENABLE_SIGMOID = 1,
    // Restoring steps per clock: fewer steps shorten the series-divider path
    // at the cost of more clocks per term. Arithmetic and rounding are unchanged.
    parameter integer DIV_BITS_PER_STEP = 10
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
    output reg  [1:0]  result_error,
    //: THE ENCLOSING INTERVAL, for a caller that must not round twice.
    //:
    //: SQRT_SOFTPLUS needs log(1 + exp(x)) rounded ONCE, so it cannot take this
    //: engine's rounded exponential and take a logarithm of it -- that is two
    //: roundings and a different function. It takes the interval instead and
    //: carries it through its own series before rounding at all.
    //:
    //: Purely additive: nothing here changes what result_code or result_error
    //: carry, and the seven existing instances leave these unconnected. They
    //: are valid on the same cycle out_valid rises, and only for a request that
    //: actually ran the series -- an argument the engine answers from an early
    //: exit (zero, or a magnitude past the flush threshold) publishes
    //: interval_exact low, because there is no interval to publish.
    output reg               interval_exact,
    output reg [FRAC_BITS+2:0] interval_lower_out,
    output reg [FRAC_BITS+2:0] interval_upper_out
);
    //: THE SERIES DIVISOR IS AT MOST SERIES_TERMS + 1, WHICH IS 57 AT THE
    //: DEFAULT.  It was carried in nine bits, and ot_wide_div_small_seq's step
    //: chain is DIVISOR_BITS+1 wide compare-subtracts in series, so every
    //: subtract in the chain was ten bits for a value that never exceeds six.
    //: Routed, that chain -- series_div_upper.work[169] -> inexact -- is the
    //: binding path of BOTH this block and its exp_pos twin at 306 MHz, with the
    //: target genuinely binding (repair_timing fought 20 endpoints in it). Six
    //: bits drops each subtract from ten to seven, values untouched: every
    //: partial remainder is below the divisor, so the narrower walk holds every
    //: value the wider one held and the netlist is a strict narrowing of
    //: constant-zero bits. Zero cycles. Derive the width from SERIES_TERMS
    //: so larger supported series retain their full divisor as well.
    localparam integer SERIES_DIVISOR_BITS = $clog2(SERIES_TERMS + 2);
    localparam OP_EXP_NONPOS = 1'b0;
    localparam OP_SIGMOID = 1'b1;

    localparam [1:0] ERR_NONE = 2'd0;
    localparam [1:0] ERR_ARGUMENT = 2'd1;
    localparam [1:0] ERR_UNCERTIFIED = 2'd2;

    localparam [30:0] MAG_25 = 31'h41c8_0000;
    localparam [30:0] MAG_150 = 31'h4316_0000;
    localparam [31:0] FP32_HALF = 32'h3f00_0000;
    localparam [31:0] FP32_ONE = 32'h3f80_0000;

    //: One state per primitive the datapath waits on. The series step splits
    //: five ways and the squaring two, because a sequential primitive has to be
    //: started and then waited on, and because a 163-bit increment and a 163-bit
    //: add in the same cycle is 6 ns where each alone is under 3.4.
    localparam [3:0] S_IDLE      = 4'd0;
    localparam [3:0] S_SER_MUL   = 4'd1;
    localparam [3:0] S_SER_PROD  = 4'd2;
    localparam [3:0] S_SER_DIV   = 4'd3;
    localparam [3:0] S_SER_INC   = 4'd4;
    localparam [3:0] S_SER_ACC   = 4'd5;
    localparam [3:0] S_SQ_MUL    = 4'd6;
    localparam [3:0] S_SQ_ACC    = 4'd7;
    localparam [3:0] S_TR_DIV    = 4'd8;
    localparam [3:0] S_TR_ACC    = 4'd9;
    localparam [3:0] S_CERTIFY   = 4'd10;
    localparam [3:0] S_OUT       = 4'd11;

    //: Bits of each operand per clock, from the walk in
    //: results/physical_abi3/asap7/wide_datapath_knobs.json. Ten is the
    //: small-divisor divide's measured peak at 286.2 MHz; sixteen is not the
    //: multiply's -- four measures 303.5 MHz -- but four would take 81 cycles per
    //: product against sixteen's 21, so 3% of clock is not worth four times the
    //: latency of 57 terms and eight squarings. The wide-denominator divide takes
    //: one bit per clock because a 165-bit subtract is already 3.37 ns.
    localparam integer MUL_BITS_PER_STEP = 16;

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

    reg [3:0] state;
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

    //: THE SERIES PRODUCT AND THE SQUARING SHARE ONE PAIR OF MULTIPLIERS. They
    //: never run in the same state -- every squaring happens after the last term
    //: -- so two instances serve both, at the widths the squaring needs, with the
    //: reduced argument zero-extended for the series. That halves the multiplier
    //: area against four instances and costs two operand multiplexers.
    localparam integer ENDPOINT_W = FRAC_BITS + 3;        //: 163
    localparam integer SERIES_DIVIDEND_W = FRAC_BITS + 8; //: 168
    localparam integer PRODUCT_HIGH_W = 2 * ENDPOINT_W - FRAC_BITS;

    reg mul_start;
    wire mul_lower_busy, mul_upper_busy, mul_lower_done, mul_upper_done;
    wire [PRODUCT_HIGH_W-1:0] mul_lower_high, mul_upper_high;
    wire mul_lower_low_nonzero, mul_upper_low_nonzero;

    //: Held stable for the whole multiply because the state is: the multiplier
    //: reads ``a`` every cycle and latches ``b`` at the start, and the state does
    //: not leave S_SER_MUL or S_SQ_MUL until ``done``.
    wire series_phase = (state == S_SER_MUL);
    wire [ENDPOINT_W-1:0] mul_a_lower = series_phase ? term_lower : interval_lower;
    wire [ENDPOINT_W-1:0] mul_a_upper = series_phase ? term_upper : interval_upper;
    wire [ENDPOINT_W-1:0] mul_b_lower = series_phase
        ? {2'b00, reduced_argument} : interval_lower;
    wire [ENDPOINT_W-1:0] mul_b_upper = series_phase
        ? {2'b00, reduced_argument} : interval_upper;

    ot_wide_mul_seq #(
        .WA(ENDPOINT_W), .WB(ENDPOINT_W),
        .BITS_PER_STEP(MUL_BITS_PER_STEP), .LOW_BITS(FRAC_BITS)
    ) mul_lower (
        .clk(clk), .rst_n(rst_n), .start(mul_start),
        .a(mul_a_lower), .b(mul_b_lower),
        .busy(mul_lower_busy), .done(mul_lower_done),
        .product_high(mul_lower_high), .low_nonzero(mul_lower_low_nonzero)
    );
    ot_wide_mul_seq #(
        .WA(ENDPOINT_W), .WB(ENDPOINT_W),
        .BITS_PER_STEP(MUL_BITS_PER_STEP), .LOW_BITS(FRAC_BITS)
    ) mul_upper (
        .clk(clk), .rst_n(rst_n), .start(mul_start),
        .a(mul_a_upper), .b(mul_b_upper),
        .busy(mul_upper_busy), .done(mul_upper_done),
        .product_high(mul_upper_high), .low_nonzero(mul_upper_low_nonzero)
    );

    //: The series dividend is the product's integer part, bits
    //: [2*FRAC_BITS+7:FRAC_BITS]. An endpoint is below eight and the reduced
    //: argument below one, so the product cannot reach bit 2*FRAC_BITS+4 and the
    //: extension is zeros.
    wire [SERIES_DIVIDEND_W-1:0] series_dividend_lower =
        {{(SERIES_DIVIDEND_W-PRODUCT_HIGH_W){1'b0}}, mul_lower_high};
    wire [SERIES_DIVIDEND_W-1:0] series_dividend_upper =
        {{(SERIES_DIVIDEND_W-PRODUCT_HIGH_W){1'b0}}, mul_upper_high};

    reg [SERIES_DIVIDEND_W-1:0] series_dividend_lower_q, series_dividend_upper_q;
    reg [SERIES_DIVISOR_BITS-1:0] series_divisor_q;
    reg                         series_upper_fraction_q;

    reg  series_div_start;
    wire series_div_lower_busy, series_div_upper_busy;
    wire series_div_lower_done, series_div_upper_done;
    wire [SERIES_DIVIDEND_W-1:0] series_quotient_lower, series_quotient_upper;
    wire series_remainder_lower, series_remainder_upper;

    ot_wide_div_small_seq #(
        .WIDTH(SERIES_DIVIDEND_W), .DIVISOR_BITS(SERIES_DIVISOR_BITS),
        .BITS_PER_STEP(DIV_BITS_PER_STEP)
    ) series_div_lower (
        .clk(clk), .rst_n(rst_n), .start(series_div_start),
        .dividend(series_dividend_lower_q), .divisor(series_divisor_q),
        .busy(series_div_lower_busy), .done(series_div_lower_done),
        .quotient(series_quotient_lower), .inexact(series_remainder_lower)
    );
    ot_wide_div_small_seq #(
        .WIDTH(SERIES_DIVIDEND_W), .DIVISOR_BITS(SERIES_DIVISOR_BITS),
        .BITS_PER_STEP(DIV_BITS_PER_STEP)
    ) series_div_upper (
        .clk(clk), .rst_n(rst_n), .start(series_div_start),
        .dividend(series_dividend_upper_q), .divisor(series_divisor_q),
        .busy(series_div_upper_busy), .done(series_div_upper_done),
        .quotient(series_quotient_upper), .inexact(series_remainder_upper)
    );

    //: The upper endpoint takes one ulp when the product discarded a fraction OR
    //: the division left a remainder -- the same disjunction the expression form
    //: carried, and still the reason the enclosure encloses.
    reg [FRAC_BITS+2:0] next_term_lower;
    reg [FRAC_BITS+2:0] next_term_upper;

    // Once a positive reduced argument < 1 reaches term interval [0, 1]
    // (fixed-point integer codes), every subsequent term remains [0, 1].
    // Fold the remaining even additions and odd subtractions exactly, including
    // the final omitted odd term. This preserves BOTH published endpoints.
    wire [7:0] tail_remaining = SERIES_TERMS - term_index;
    wire [7:0] tail_lower_steps = {1'b0, tail_remaining[7:1]} + 8'd1;
    wire [7:0] tail_upper_steps = {1'b0, tail_remaining[7:1]} +
                                {7'd0, tail_remaining[0]};

    //: The squared endpoints. Same multipliers, different operands, and the upper
    //: one rounds up when the product discarded anything.
    reg [FRAC_BITS+2:0] square_lower_q, square_upper_q;

    //: The sigmoid's rational transform. Its numerator is 328 bits and its
    //: quotient is bounded by one in Q0.FRAC_BITS, so only the low FRAC_BITS+3
    //: quotient bits are kept -- which is what the expression form did by testing
    //: ``divide_bit <= FRAC_BITS+2``.
    localparam integer TRANSFORM_NUM_W = 2 * FRAC_BITS + 8;
    localparam integer TRANSFORM_DEN_W = FRAC_BITS + 4;

    reg [TRANSFORM_NUM_W-1:0] transform_numerator_lower;
    reg [TRANSFORM_NUM_W-1:0] transform_numerator_upper;
    reg [TRANSFORM_DEN_W-1:0] transform_denominator_lower;
    reg [TRANSFORM_DEN_W-1:0] transform_denominator_upper;

    //: Built in a combinational block because it is pure selection and shifting:
    //: an endpoint placed at bit FRAC_BITS, or a single bit at 2*FRAC_BITS.
    always @* begin
        transform_numerator_lower = {TRANSFORM_NUM_W{1'b0}};
        transform_numerator_upper = {TRANSFORM_NUM_W{1'b0}};
        transform_denominator_lower = {{(TRANSFORM_DEN_W-1){1'b0}}, 1'b1};
        transform_denominator_upper = {{(TRANSFORM_DEN_W-1){1'b0}}, 1'b1};
        if (argument_sign) begin
            //: e/(1+e), monotonically increasing.
            transform_numerator_lower = {5'b0, interval_lower, {FRAC_BITS{1'b0}}};
            transform_numerator_upper = {5'b0, interval_upper, {FRAC_BITS{1'b0}}};
            transform_denominator_lower = {1'b0, FIXED_ONE} + {1'b0, interval_lower};
            transform_denominator_upper = {1'b0, FIXED_ONE} + {1'b0, interval_upper};
        end else begin
            //: 1/(1+e), monotonically decreasing, so the endpoints swap.
            transform_numerator_lower[2*FRAC_BITS] = 1'b1;
            transform_numerator_upper[2*FRAC_BITS] = 1'b1;
            transform_denominator_lower = {1'b0, FIXED_ONE} + {1'b0, interval_upper};
            transform_denominator_upper = {1'b0, FIXED_ONE} + {1'b0, interval_lower};
        end
    end

    reg  transform_div_start;
    wire transform_lower_busy, transform_upper_busy;
    wire transform_lower_done, transform_upper_done;
    wire [FRAC_BITS+2:0] transform_quotient_lower, transform_quotient_upper;
    wire transform_remainder_lower, transform_remainder_upper;

    generate if (ENABLE_SIGMOID) begin : sigmoid_service
    ot_wide_div_seq #(
        .NUM_BITS(TRANSFORM_NUM_W), .DEN_BITS(TRANSFORM_DEN_W),
        .QUOT_BITS(FRAC_BITS+3), .BITS_PER_STEP(1)
    ) transform_div_lower (
        .clk(clk), .rst_n(rst_n), .start(transform_div_start),
        .numerator(transform_numerator_lower),
        .denominator(transform_denominator_lower),
        .busy(transform_lower_busy), .done(transform_lower_done),
        .quotient(transform_quotient_lower), .inexact(transform_remainder_lower)
    );
    ot_wide_div_seq #(
        .NUM_BITS(TRANSFORM_NUM_W), .DEN_BITS(TRANSFORM_DEN_W),
        .QUOT_BITS(FRAC_BITS+3), .BITS_PER_STEP(1)
    ) transform_div_upper (
        .clk(clk), .rst_n(rst_n), .start(transform_div_start),
        .numerator(transform_numerator_upper),
        .denominator(transform_denominator_upper),
        .busy(transform_upper_busy), .done(transform_upper_done),
        .quotient(transform_quotient_upper), .inexact(transform_remainder_upper)
    );

    end else begin : exponential_only
        assign transform_lower_busy = 0, transform_upper_busy = 0;
        assign transform_lower_done = 0, transform_upper_done = 0;
        assign transform_quotient_lower = 0, transform_quotient_upper = 0;
        assign transform_remainder_lower = 0, transform_remainder_upper = 0;
    end endgenerate

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
        if (SERIES_TERMS + 1 >= (1 << SERIES_DIVISOR_BITS))
            $error("SERIES_TERMS + 1 must fit SERIES_DIVISOR_BITS");
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
            interval_exact <= 1'b0;
            interval_lower_out <= 0;
            interval_upper_out <= 0;
            series_dividend_lower_q <= 0;
            series_dividend_upper_q <= 0;
            series_divisor_q <= {SERIES_DIVISOR_BITS{1'b0}};
            series_upper_fraction_q <= 1'b0;
            next_term_lower <= 0;
            next_term_upper <= 0;
            square_lower_q <= 0;
            square_upper_q <= 0;
            mul_start <= 1'b0;
            series_div_start <= 1'b0;
            transform_div_start <= 1'b0;
        end else begin
            //: Every ``start`` is a single cycle: the primitives latch on it and
            //: raise ``busy`` the cycle after, so holding it would restart them.
            mul_start <= 1'b0;
            series_div_start <= 1'b0;
            transform_div_start <= 1'b0;
            if (out_valid && out_ready)
                out_valid <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (in_valid && in_ready) begin
                        operation_q <= operation;
                        argument_sign <= argument_code[31];
                        result_code <= 0;
                        result_error <= ERR_NONE;
                        interval_exact <= 1'b0;
                        if ((!ENABLE_SIGMOID && operation == OP_SIGMOID) ||
                            argument_nonfinite ||
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
                            state <= S_SER_MUL;
                        end
                    end
                end

                //: term_{k+1} = term_k * y, high half kept, low half only as
                //: "was anything discarded".
                //: ``done`` IS TESTED BEFORE THE START CONDITION, here and in
                //: every other state that waits on a primitive: a primitive drops
                //: ``busy`` in the same cycle it raises ``done``, so testing "not
                //: busy and not started" first restarts it forever. The
                //: multiplier was caught doing exactly that -- looping at
                //: steps_left 21 with the state never leaving S_SER_MUL.
                S_SER_MUL: begin
                    if (mul_lower_done && mul_upper_done) begin
                        state <= S_SER_PROD;
                    end else if (!mul_lower_busy && !mul_start) begin
                        mul_start <= 1'b1;
                    end
                end

                S_SER_PROD: begin
                    series_dividend_lower_q <= series_dividend_lower;
                    series_dividend_upper_q <= series_dividend_upper;
                    series_divisor_q <= next_term_index[SERIES_DIVISOR_BITS-1:0];
                    series_upper_fraction_q <= mul_upper_low_nonzero;
                    state <= S_SER_DIV;
                end

                S_SER_DIV: begin
                    if (series_div_lower_done && series_div_upper_done) begin
                        state <= S_SER_INC;
                    end else if (!series_div_lower_busy && !series_div_start) begin
                        series_div_start <= 1'b1;
                    end
                end

                //: Its own cycle, because a 163-bit increment and the 163-bit add
                //: in S_SER_ACC are each under 3.4 ns and together are six.
                S_SER_INC: begin
                    next_term_lower <= series_quotient_lower[FRAC_BITS+2:0];
                    next_term_upper <= series_quotient_upper[FRAC_BITS+2:0] +
                        {{(FRAC_BITS+2){1'b0}},
                         (series_remainder_upper || series_upper_fraction_q)};
                    state <= S_SER_ACC;
                end

                S_SER_ACC: begin
                    if (next_term_lower == 0 && next_term_upper == 1 &&
                        {24'b0, term_index} < SERIES_TERMS) begin
                        interval_lower <= sum_lower - tail_lower_steps;
                        interval_upper <= sum_upper + tail_upper_steps;
                        square_index <= 0;
                        state <= S_SQ_MUL;
                    end else if ({24'b0, term_index} < SERIES_TERMS) begin
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
                        state <= S_SER_MUL;
                    end else begin
                        // SERIES_TERMS is even, so its partial sum is the
                        // upper alternating bound and the next odd term gives
                        // the lower bound.
                        interval_lower <= sum_lower - next_term_upper;
                        interval_upper <= sum_upper;
                        square_index <= 0;
                        state <= S_SQ_MUL;
                    end
                end

                //: Eight squarings reconstruct exp(x) from exp(|x|/256); the
                //: multipliers are the series ones, with the interval on both
                //: operand ports.
                S_SQ_MUL: begin
                    if (mul_lower_done && mul_upper_done) begin
                        square_lower_q <= mul_lower_high[FRAC_BITS+2:0];
                        square_upper_q <= mul_upper_high[FRAC_BITS+2:0] +
                            {{(FRAC_BITS+2){1'b0}}, mul_upper_low_nonzero};
                        state <= S_SQ_ACC;
                    end else if (!mul_lower_busy && !mul_start) begin
                        mul_start <= 1'b1;
                    end
                end

                S_SQ_ACC: begin
                    interval_lower <= square_lower_q;
                    interval_upper <= square_upper_q;
                    if (square_index == 7) begin
                        state <= ENABLE_SIGMOID && operation_q == OP_SIGMOID
                            ? S_TR_DIV : S_CERTIFY;
                    end else begin
                        square_index <= square_index + 1'b1;
                        state <= S_SQ_MUL;
                    end
                end

                //: The sigmoid transform: two exact wide divisions, one subtract
                //: per clock, on an interval that has not been rounded yet.
                S_TR_DIV: begin
                    if (transform_lower_done && transform_upper_done) begin
                        state <= S_TR_ACC;
                    end else if (!transform_lower_busy && !transform_div_start) begin
                        transform_div_start <= 1'b1;
                    end
                end

                S_TR_ACC: begin
                    interval_lower <= transform_quotient_lower;
                    interval_upper <= transform_quotient_upper +
                        {{(FRAC_BITS+2){1'b0}}, transform_remainder_upper};
                    state <= S_CERTIFY;
                end

                S_CERTIFY: begin
                    interval_exact <= 1'b1;
                    interval_lower_out <= interval_lower;
                    interval_upper_out <= interval_upper;
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
