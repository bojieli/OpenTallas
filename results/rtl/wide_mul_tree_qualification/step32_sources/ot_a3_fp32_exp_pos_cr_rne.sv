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
// THE WIDE ARITHMETIC IS SEQUENTIAL, AND THAT IS WHY THIS BLOCK IS NOT 17.5 MHz.
// Every product and every division here used to be one cycle: two 163-by-161
// multiplier trees and a 161-by-162 one, each ending in a 324-bit carry-propagate
// adder, and two restoring divides UNROLLED over every bit of the dividend. The
// routed evidence was a worst path of 2,135 cell delays from reduced[40] to
// interval_upper[162] -- 57.2 ns against a 4 ns target, 373,426 cells, and a
// seven-hour route. Measured alone at synthesis and pre-layout timing, the
// unrolled divide is 20.5 MHz; every OTHER wide operation in this module already
// clears 296 MHz, including the 163-bit adds, the 170-bit subtract, the
// comparators and the 163-bit priority encode inside the rounding. So exactly two
// things were the wall, and both are now sequential primitives:
// ot_wide_mul_seq (carry-save, no wide carry chain anywhere) and
// ot_wide_div_small_seq (the same restoring loop, ten bits per clock).
//
// NOTHING ABOUT THE ARITHMETIC CHANGED. Both primitives are bit-identical to the
// expressions they replace -- the divider runs the same restoring steps in the
// same order and the multiplier is checked against ``*`` itself -- so the
// enclosure, the certification and every refusal are the ones this module already
// published. rtl/test/tb_wide_div_small_seq_equiv.sv and
// rtl/test/tb_wide_mul_seq_equiv.sv carry that check, and tb_a3_exp_pos.sv still
// grades the whole module against exp_cr32.
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
    parameter integer INT_BITS = 9,
    // Fewer restoring steps shorten the series-divider path, adding cycles.
    parameter integer DIV_BITS_PER_STEP = 10
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

    //: One state per sequential primitive it waits on. S_SERIES became four --
    //: multiply, latch the product, divide, latch the term -- because an
    //: increment and an add in the same cycle is 6 ns where each alone is under
    //: 3.4, which is the one place the split is about timing rather than about
    //: waiting for a primitive.
    localparam [3:0] S_IDLE      = 4'd0;
    localparam [3:0] S_REDUCE_MUL = 4'd1;
    localparam [3:0] S_REDUCE    = 4'd2;
    localparam [3:0] S_FIXUP     = 4'd3;
    localparam [3:0] S_TERM_MUL  = 4'd4;
    localparam [3:0] S_TERM_PROD = 4'd5;
    localparam [3:0] S_TERM_DIV  = 4'd6;
    localparam [3:0] S_TERM_INC  = 4'd7;
    localparam [3:0] S_TERM_ACC  = 4'd8;
    localparam [3:0] S_CERTIFY   = 4'd9;
    localparam [3:0] S_OUT       = 4'd10;
    reg [3:0] state;

    //: Bits of each operand consumed per clock, from the walk in
    //: results/physical_abi3/asap7/wide_datapath_knobs.json -- measurement rather
    //: than preference, and NOT simply the two peaks.
    //:
    //: Ten IS the divide's peak, 286.2 MHz pre-layout against 20.5 MHz unrolled.
    //: Sixteen is NOT the multiply's: four bits per clock measures 303.5 MHz and
    //: sixteen 294.7. Four would take 81 cycles to emit the 324-bit product where
    //: sixteen takes 21, so it buys 3% of clock for four times the latency of
    //: every one of the 57 terms. Sixteen is the trade, stated because the record
    //: shows the faster point and a reader should see why it was not taken.
    //:
    //: Neither is the block's ceiling. fixed_to_fp32_scaled with a variable power
    //: measures 279.6 MHz, and that is what the enclosure's rounding costs: no
    //: amount of sequencing the products and divides lifts it, because it is what
    //: the arithmetic IS rather than how it is scheduled.
    localparam integer MUL_BITS_PER_STEP = 32;

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

    //: term_{k+1} = term_k * r / (k+1), both endpoints kept enclosing. The
    //: product and the division are each a sequential primitive now, so the
    //: recurrence is four states rather than one expression; the VALUES are the
    //: ones the expressions produced.
    wire [8:0] next_index = term_index + 9'd1;

    localparam integer TERM_W = FRAC_BITS + 3;   //: an enclosure endpoint
    localparam integer RED_W  = FRAC_BITS + 1;   //: the reduced argument
    localparam integer TERM_PRODUCT_HIGH = TERM_W + RED_W - FRAC_BITS;

    reg  mul_start, div_start;
    wire mul_lower_busy, mul_upper_busy, mul_lower_done, mul_upper_done;
    wire [TERM_PRODUCT_HIGH-1:0] mul_lower_high, mul_upper_high;
    wire mul_lower_low_nonzero, mul_upper_low_nonzero;

    //: ``term * reduced`` keeps bits [2*FRAC_BITS+2:FRAC_BITS] and needs the low
    //: FRAC_BITS only as "was anything discarded", which is what LOW_BITS means
    //: here: those bits are OR-reduced as they leave and never stored.
    ot_wide_mul_seq #(
        .WA(TERM_W), .WB(RED_W),
        .BITS_PER_STEP(MUL_BITS_PER_STEP), .LOW_BITS(FRAC_BITS)
    ) mul_lower (
        .clk(clk), .rst_n(rst_n), .start(mul_start),
        .a(term_lower), .b(reduced),
        .busy(mul_lower_busy), .done(mul_lower_done),
        .product_high(mul_lower_high), .low_nonzero(mul_lower_low_nonzero)
    );
    ot_wide_mul_seq #(
        .WA(TERM_W), .WB(RED_W),
        .BITS_PER_STEP(MUL_BITS_PER_STEP), .LOW_BITS(FRAC_BITS)
    ) mul_upper (
        .clk(clk), .rst_n(rst_n), .start(mul_start),
        .a(term_upper), .b(reduced),
        .busy(mul_upper_busy), .done(mul_upper_done),
        .product_high(mul_upper_high), .low_nonzero(mul_upper_low_nonzero)
    );

    //: The product is Q0.(2*FRAC_BITS); take the high half as the lower endpoint
    //: and add one ulp when anything was discarded. The increment is registered
    //: away from the divide because a 163-bit increment and one divider step in
    //: the same cycle is 6 ns where each alone is under 3.5.
    reg [FRAC_BITS+2:0] prod_lower_q, prod_upper_q;
    reg [SERIES_DIVISOR_BITS-1:0] divisor_q;

    wire div_lower_busy, div_upper_busy, div_lower_done, div_upper_done;
    wire [FRAC_BITS+2:0] div_lower_quotient, div_upper_quotient;
    wire div_lower_inexact, div_upper_inexact;

    ot_wide_div_small_seq #(
        .WIDTH(TERM_W), .DIVISOR_BITS(SERIES_DIVISOR_BITS), .BITS_PER_STEP(DIV_BITS_PER_STEP)
    ) div_lower (
        .clk(clk), .rst_n(rst_n), .start(div_start),
        .dividend(prod_lower_q), .divisor(divisor_q),
        .busy(div_lower_busy), .done(div_lower_done),
        .quotient(div_lower_quotient), .inexact(div_lower_inexact)
    );
    ot_wide_div_small_seq #(
        .WIDTH(TERM_W), .DIVISOR_BITS(SERIES_DIVISOR_BITS), .BITS_PER_STEP(DIV_BITS_PER_STEP)
    ) div_upper (
        .clk(clk), .rst_n(rst_n), .start(div_start),
        .dividend(prod_upper_q), .divisor(divisor_q),
        .busy(div_upper_busy), .done(div_upper_done),
        .quotient(div_upper_quotient), .inexact(div_upper_inexact)
    );

    //: The rounded-away bit of the division rounds the UPPER endpoint away from
    //: zero, so the enclosure still encloses.
    reg [FRAC_BITS+2:0] next_term_lower, next_term_upper;

    //: The geometric tail: remainder < term_{N+1} * 4 for r < 0.75.
    wire [FRAC_BITS+2:0] tail_bound = next_term_upper << 2;

    //: n * ln2, and the reduced argument.
    //: n * ln2 in Q(INT_BITS).FRAC_BITS. n is below 185 and ln2 below one, so
    //: the product stays under 128 and the integer field fits INT_BITS. A
    //: 161-by-16 constant product measures 534 MHz, so this one stays an
    //: expression.
    wire [FRAC_BITS+17:0] n_times_ln2 =
        {{17{1'b0}}, LN2} * {{(FRAC_BITS+2){1'b0}}, n_power[15:0]};
    wire [WIDE:0] n_ln2_fixed = n_times_ln2[WIDE:0];

    //: x * log2(e), for the floor that starts the range reduction. Sequential for
    //: the same reason as the term products, and the CONSTANT is the multiplicand
    //: so the per-step shifts and selects fold away at synthesis. Only nine bits
    //: at 2*FRAC_BITS are read, so everything below is OR-reduced and dropped.
    localparam integer LOG2E_W = FRAC_BITS + 2;
    localparam integer REDUCE_LOW = 2 * FRAC_BITS;
    localparam integer REDUCE_HIGH_W = LOG2E_W + WIDE + 1 - REDUCE_LOW;
    reg  reduce_mul_start;
    wire reduce_mul_busy, reduce_mul_done, reduce_low_nonzero;
    wire [REDUCE_HIGH_W-1:0] reduce_high;
    ot_wide_mul_seq #(
        .WA(LOG2E_W), .WB(WIDE + 1),
        .BITS_PER_STEP(MUL_BITS_PER_STEP), .LOW_BITS(REDUCE_LOW)
    ) mul_reduce (
        .clk(clk), .rst_n(rst_n), .start(reduce_mul_start),
        .a(LOG2E), .b(x_fixed),
        .busy(reduce_mul_busy), .done(reduce_mul_done),
        .product_high(reduce_high), .low_nonzero(reduce_low_nonzero)
    );
    //: Bits [2*FRAC_BITS+8 : 2*FRAC_BITS] of the product, which is the integer
    //: part of x*log2(e) and so the floor the reduction wants.
    reg [8:0] n_estimate;
    //: Named so the discarded-bit reasoning stays checkable: the reduction reads
    //: only the integer part, and the fraction below it is deliberately dropped.
    wire _unused_reduce_low = reduce_low_nonzero;

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
            prod_lower_q <= {(FRAC_BITS+3){1'b0}};
            prod_upper_q <= {(FRAC_BITS+3){1'b0}};
            next_term_lower <= {(FRAC_BITS+3){1'b0}};
            next_term_upper <= {(FRAC_BITS+3){1'b0}};
            divisor_q <= {SERIES_DIVISOR_BITS{1'b0}};
            n_estimate <= 9'd0;
            mul_start <= 1'b0;
            div_start <= 1'b0;
            reduce_mul_start <= 1'b0;
        end else begin
            //: Every ``start`` is a single cycle: the primitives latch on it and
            //: raise ``busy`` the cycle after, so holding it would restart them.
            mul_start <= 1'b0;
            div_start <= 1'b0;
            reduce_mul_start <= 1'b0;
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
                            state <= S_REDUCE_MUL;
                        end
                    end
                end

                //: x_fixed was registered the cycle before, so the multiply
                //: starts here rather than in S_IDLE.
                //:
                //: ``done`` IS TESTED BEFORE THE START CONDITION, in this state
                //: and in every other one that waits on a primitive. A primitive
                //: drops ``busy`` in the same cycle it raises ``done``, so testing
                //: "not busy and not started" first restarts it forever: the
                //: multiplier was caught looping at steps_left 21 with the state
                //: never leaving S_TERM_MUL.
                S_REDUCE_MUL: begin
                    if (reduce_mul_done) begin
                        n_estimate <= reduce_high[8:0];
                        state <= S_REDUCE;
                    end else if (!reduce_mul_busy && !reduce_mul_start) begin
                        reduce_mul_start <= 1'b1;
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
                        state <= S_TERM_MUL;
                    end
                end

                //: term_{k+1} = term_k * r, high half kept, low half only as
                //: "was anything discarded".
                S_TERM_MUL: begin
                    if (mul_lower_done && mul_upper_done) begin
                        state <= S_TERM_PROD;
                    end else if (!mul_lower_busy && !mul_start) begin
                        mul_start <= 1'b1;
                    end
                end

                //: The upper endpoint takes one ulp for whatever the product
                //: discarded, so the enclosure still encloses. Registered here
                //: rather than fed straight into the divide: a 163-bit increment
                //: plus one divider step is 6 ns, and each alone is under 3.5.
                S_TERM_PROD: begin
                    prod_lower_q <= mul_lower_high[FRAC_BITS+2:0];
                    prod_upper_q <= mul_upper_high[FRAC_BITS+2:0] +
                                    {{(FRAC_BITS+2){1'b0}}, mul_upper_low_nonzero};
                    divisor_q <= next_index[SERIES_DIVISOR_BITS-1:0];
                    state <= S_TERM_DIV;
                end

                S_TERM_DIV: begin
                    if (div_lower_done && div_upper_done) begin
                        state <= S_TERM_INC;
                    end else if (!div_lower_busy && !div_start) begin
                        div_start <= 1'b1;
                    end
                end

                //: The division's rounded-away bit rounds the upper endpoint away
                //: from zero. Its own cycle, for the same 163-bit-increment
                //: reason as S_TERM_PROD.
                S_TERM_INC: begin
                    next_term_lower <= div_lower_quotient;
                    next_term_upper <= div_upper_quotient +
                                       {{(FRAC_BITS+2){1'b0}}, div_upper_inexact};
                    state <= S_TERM_ACC;
                end

                S_TERM_ACC: begin
                    if ({23'd0, term_index} < SERIES_TERMS) begin
                        term_lower <= next_term_lower;
                        term_upper <= next_term_upper;
                        term_index <= next_index;
                        //: ALL TERMS ARE POSITIVE, so both endpoints accumulate
                        //: additively -- no alternation.
                        sum_lower <= sum_lower + next_term_lower;
                        sum_upper <= sum_upper + next_term_upper;
                        state <= S_TERM_MUL;
                    end else begin
                        //: The truncated sum is the lower bound; the geometric
                        //: tail bounds what is left. term_index reached
                        //: SERIES_TERMS, so this pass computed term_{N+1} without
                        //: adding it -- which is what the tail bound needs.
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
