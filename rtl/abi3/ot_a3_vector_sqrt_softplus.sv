// VECTOR.SQRT_SOFTPLUS: DeepSeek V4's router activation, sqrt(softplus(x)).
//
// runtime/reference/sqrt_softplus.py is the authority. The released source
// spells the boundary ``scores = F.softplus(scores).sqrt()`` and that module
// freezes what PyTorch does not promise:
//
//   * x > 20 STRICTLY: softplus is x, bit for bit (beta is exactly one, so the
//     threshold branch returns its input).
//   * x <= -105: softplus is zero. 0 < log(1+exp(x)) < exp(x) < 2**-150, which
//     is the binary32 zero midpoint, so every value there rounds to zero.
//   * otherwise: ONE binary32 rounding of the mathematical log(1+exp(x)).
//   * then sqrt correctly rounds the square root of that already-rounded
//     binary32 softplus, once.
//
// TWO ROUNDINGS IS A DIFFERENT FUNCTION, which is why this cannot be built from
// the correctly-rounded exponential this tree already has: taking a logarithm of
// a rounded exp rounds twice. ot_a3_fp32_transcendental_cr_rne now publishes its
// enclosing INTERVAL alongside its rounded result, and this operator carries
// that interval through its own logarithm before rounding at all.
//
// THE LOGARITHM IS atanh, not the log1p series. log(1+u) = u - u**2/2 + ...
// has ratio u, and u = exp(x) approaches 1 as x approaches 0, so it would need
// on the order of 2**FRAC_BITS terms there. The identity
//
//     log(1+u) = 2 * atanh(u / (2+u))
//
// maps u in (0,1] to z in (0,1/3], and atanh's series z + z**3/3 + z**5/5 + ...
// then has ratio z**2 <= 1/9: about 51 terms carry 160 fractional bits.
//
// Its terms are all POSITIVE, unlike the alternating series the exponential
// uses, so truncation gives a lower bound and the upper bound needs a tail
// estimate. For z <= 1/3 the tail past term K is below
// z**(2K+1)/(2K+1) * 1/(1-z**2) <= (9/8) * z**(2K+1)/(2K+1), and this adds
// twice that term instead -- a valid over-estimate that costs one bit of
// interval width and no reasoning about where 9/8 rounds.
//
// THE TAIL BOUND IS WHAT MAKES A SHORTFALL REFUSE INSTEAD OF LIE, and that is
// measured rather than argued. Running the suite at term counts too low to
// carry binary32:
//
//     terms   with the bound        without it
//       3     53 refusals, 0 wrong  103 wrong, 0 refusals
//       4     42 refusals, 0 wrong   81 wrong, 0 refusals
//       6     26 refusals, 0 wrong   51 wrong, 0 refusals
//       8     all 1202 correct       all 1202 correct
//
// Without the bound the upper endpoint is below the true value, so the pair is
// not an enclosure and the two ends can agree on a code that is wrong. With it,
// an interval too wide to decide is an interval that refuses.
//
// ATANH_TERMS IS 16, against a measured sufficiency of 8. The worst case is
// z -> 1/3, where x -> 0 and the result is log 2; the truncation after K terms
// is then (9/8) * 3**-(2K+1)/(2K+1) relative to 0.693, which at K = 8 is about
// 2**-30 against a half-ulp of 2**-24.5 -- six bits of margin, thin enough that
// a case outside this suite could cross it. At K = 16 it is 2**-56, which is
// thirty-two bits of margin, and it costs sixteen loop iterations rather than
// the fifty-six this was first written with.
//
// FRAC_BITS IS 224, AND THE REFERENCE'S ESCALATION TO 192 IS A REAL
// REQUIREMENT rather than an artifact of its doubling search. That is worth
// recording because the opposite conclusion is easy to reach and was reached
// here first.
//
// The tempting argument: a binary32 subnormal's ulp is 2**-149 wherever it
// sits, so 160 fractional bits resolve the smallest nonzero softplus -- just
// above 2**-150 -- with eleven bits to spare. That accounts for the
// REPRESENTATION and not for the INTERVAL. Every one of the fifty-odd series
// terms rounds its endpoints outward by an ulp of the fixed-point word, so the
// enclosure is about 56 * 2**-FRAC_BITS wide before the doubling, which at 160
// is 2**-153 -- roughly a eighteenth of a subnormal's ulp. Around one case in
// eighteen then straddles a rounding boundary and cannot be certified, which is
// exactly what happened: dozens of refusals between x = -99 and x = -89, every
// one of them a value the reference certifies.
//
// At 224 the enclosure is 2**-217 against the same 2**-149 ulp, which leaves
// 68 bits of margin. A single wide pass is taken rather than the reference's
// escalation because one width is far simpler in hardware than a refinement
// loop, and the width is chosen with margin rather than at the edge.
//
// It FAILS CLOSED. If the enclosing interval's two endpoints do not round to
// one binary32 code, this refuses rather than publishing a bit it cannot
// justify, exactly as the transcendental engine does.
module ot_a3_vector_sqrt_softplus #(
    parameter integer FRAC_BITS = 224,
    parameter integer ATANH_TERMS = 16
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    output wire        in_ready,
    input  wire [31:0] a,
    output reg  [31:0] y,
    //: 0 none, 1 the operand is nonfinite, 2 the interval did not certify.
    output reg  [1:0]  error_code,
    output reg         valid_out,
    output reg         busy,
    //: The branch the reference would have named, for a campaign to check that
    //: the device took the same one rather than only agreeing on the value.
    output reg  [1:0]  branch_taken,
    //: The rounded softplus, before the square root. Published so a failure
    //: localizes to one half or the other: the two halves round independently,
    //: and a wrong softplus and a wrong square root of a right one look
    //: identical at y.
    output wire [31:0] softplus_out
);
    localparam [1:0] ERR_NONE        = 2'd0;
    localparam [1:0] ERR_ARGUMENT    = 2'd1;
    localparam [1:0] ERR_UNCERTIFIED = 2'd2;

    localparam [1:0] BR_LINEAR       = 2'd0;
    localparam [1:0] BR_UNDERFLOW    = 2'd1;
    localparam [1:0] BR_TRANSCEND    = 2'd2;

    //: 20.0 and 105.0 as binary32 magnitudes, the reference's own thresholds.
    localparam [30:0] MAG_20  = 31'h41a0_0000;
    localparam [30:0] MAG_105 = 31'h42d2_0000;

    localparam [3:0] S_IDLE  = 4'd0;
    localparam [3:0] S_EXP   = 4'd1;
    localparam [3:0] S_ZFORM = 4'd2;
    localparam [3:0] S_ZSQ   = 4'd3;
    localparam [3:0] S_SUM   = 4'd4;
    localparam [3:0] S_TAIL  = 4'd5;
    localparam [3:0] S_ROUND = 4'd6;
    localparam [3:0] S_SQRT  = 4'd7;
    localparam [3:0] S_OUT   = 4'd8;

    localparam [FRAC_BITS+2:0] FIXED_ONE = {2'b0, 1'b1, {FRAC_BITS{1'b0}}};

    reg [3:0]  state;
    reg [31:0] arg_q;
    reg        arg_sign_q;
    reg [FRAC_BITS+2:0] u_lower, u_upper;
    reg [FRAC_BITS+2:0] z_lower, z_upper;
    reg [FRAC_BITS+2:0] zsq_lower, zsq_upper;
    reg [FRAC_BITS+2:0] t_lower, t_upper;
    reg [FRAC_BITS+2:0] s_lower, s_upper;
    reg [8:0]  term_index;
    reg [31:0] softplus_code;

    wire        arg_nonfinite = (a[30:23] == 8'hff);
    wire        arg_zero = (a[30:0] == 31'd0);
    wire        arg_gt_20 = !a[31] && (a[30:0] > MAG_20);
    wire        arg_le_neg105 = a[31] && (a[30:0] >= MAG_105);

    // -- the exponential's interval ------------------------------------------
    reg         exp_req;
    wire        exp_ready;
    wire        exp_valid;
    wire [31:0] exp_code;
    wire [1:0]  exp_error;
    wire        exp_interval_exact;
    wire [FRAC_BITS+2:0] exp_lower, exp_upper;
    //: Driven with -|x| so the engine's own nonpositive-exponential branch
    //: applies for either sign of the operand: softplus(x) for x > 0 is
    //: x + log(1+exp(-x)), and for x <= 0 it is log(1+exp(x)) -- both need
    //: exp(-|x|) and nothing else.
    wire [31:0] exp_argument = {1'b1, a[30:0]};
    ot_a3_fp32_transcendental_cr_rne #(
        .FRAC_BITS(FRAC_BITS)
    ) exponential (
        .clk(clk), .rst_n(rst_n),
        .in_valid(exp_req), .in_ready(exp_ready),
        .operation(1'b0), .argument_code(exp_argument),
        .out_valid(exp_valid), .out_ready(1'b1),
        .result_code(exp_code), .result_error(exp_error),
        .interval_exact(exp_interval_exact),
        .interval_lower_out(exp_lower), .interval_upper_out(exp_upper)
    );

    // -- the two exact dividers ----------------------------------------------
    //: Both are the restoring dividers ot_a3_fp32_transcendental_cr_rne uses,
    //: for the same reason it gives: a bounded restoring loop maps to a far
    //: smaller circuit than SystemVerilog's general-purpose wide ``/``, and it
    //: spares event-driven simulators building one per evaluation. They are
    //: repeated here rather than shared because they are sized by FRAC_BITS and
    //: a function cannot be passed a parameter across a module boundary.
    function automatic [FRAC_BITS+16:0] divide_by_small;
        input [FRAC_BITS+7:0] dividend;
        input [8:0] divisor;
        reg [FRAC_BITS+7:0] quotient;
        reg [8:0] remainder;
        reg [9:0] shifted;
        integer bit_index;
        begin
            quotient = 0;
            remainder = 0;
            shifted = 0;
            for (bit_index = FRAC_BITS + 7; bit_index >= 0;
                 bit_index = bit_index - 1) begin
                shifted = {remainder[8:0], dividend[bit_index]};
                if (shifted >= {1'b0, divisor}) begin
                    remainder = shifted[8:0] - divisor;
                    quotient[bit_index] = 1'b1;
                end else begin
                    remainder = shifted[8:0];
                end
            end
            divide_by_small = {quotient, remainder[8:0]};
        end
    endfunction

    function automatic [FRAC_BITS+3:0] divide_fixed_ratio;
        input [2*FRAC_BITS+7:0] numerator;
        input [FRAC_BITS+3:0] denominator;
        reg [FRAC_BITS+2:0] quotient;
        reg [FRAC_BITS+3:0] remainder;
        reg [FRAC_BITS+4:0] shifted;
        reg [FRAC_BITS+4:0] difference;
        integer bit_index;
        begin
            quotient = 0;
            remainder = 0;
            shifted = 0;
            difference = 0;
            for (bit_index = 2*FRAC_BITS + 7; bit_index >= 0;
                 bit_index = bit_index - 1) begin
                shifted = {remainder, numerator[bit_index]};
                if (shifted >= {1'b0, denominator}) begin
                    difference = shifted - {1'b0, denominator};
                    remainder = difference[FRAC_BITS+3:0];
                    if (bit_index <= FRAC_BITS + 2)
                        quotient[bit_index] = 1'b1;
                end else begin
                    remainder = shifted[FRAC_BITS+3:0];
                end
            end
            divide_fixed_ratio = {quotient, remainder != 0};
        end
    endfunction

    //: z = u / (2 + u), increasing in u, so the endpoints map straight across.
    reg [2*FRAC_BITS+7:0] z_num_lower, z_num_upper;
    reg [FRAC_BITS+3:0]   z_den_lower, z_den_upper;
    reg [FRAC_BITS+3:0]   z_div_lower, z_div_upper;
    reg [FRAC_BITS+2:0]   z_next_lower, z_next_upper;
    always @* begin
        z_num_lower = 0; z_num_upper = 0;
        z_den_lower = 1; z_den_upper = 1;
        z_div_lower = 0; z_div_upper = 0;
        z_next_lower = 0; z_next_upper = 0;
        if (state == S_ZFORM) begin
            z_num_lower = {5'b0, u_lower, {FRAC_BITS{1'b0}}};
            z_num_upper = {5'b0, u_upper, {FRAC_BITS{1'b0}}};
            z_den_lower = {FIXED_ONE, 1'b0} + {1'b0, u_lower};
            z_den_upper = {FIXED_ONE, 1'b0} + {1'b0, u_upper};
            z_div_lower = divide_fixed_ratio(z_num_lower, z_den_lower);
            z_div_upper = divide_fixed_ratio(z_num_upper, z_den_upper);
            z_next_lower = z_div_lower[FRAC_BITS+3:1];
            z_next_upper = z_div_upper[FRAC_BITS+3:1]
                         + {{(FRAC_BITS+2){1'b0}}, z_div_upper[0]};
        end
    end

    //: One interval multiply, used for z**2 and then for each term.
    reg [2*FRAC_BITS+5:0] prod_lower, prod_upper;
    reg [FRAC_BITS+2:0]   mul_lower, mul_upper;
    reg [FRAC_BITS+2:0]   mul_a_lower, mul_a_upper;
    reg [FRAC_BITS+2:0]   mul_b_lower, mul_b_upper;
    always @* begin
        //: Named rather than written as a conditional inside the multiply:
        //: Verilog widens the whole expression to the product's width, which
        //: widens the conditional's arms with it.
        mul_a_lower = (state == S_ZSQ) ? z_lower : t_lower;
        mul_a_upper = (state == S_ZSQ) ? z_upper : t_upper;
        mul_b_lower = (state == S_ZSQ) ? z_lower : zsq_lower;
        mul_b_upper = (state == S_ZSQ) ? z_upper : zsq_upper;
        prod_lower = mul_a_lower * mul_b_lower;
        prod_upper = mul_a_upper * mul_b_upper;
        mul_lower = prod_lower[2*FRAC_BITS+2:FRAC_BITS];
        mul_upper = prod_upper[2*FRAC_BITS+2:FRAC_BITS]
                  + {{(FRAC_BITS+2){1'b0}}, |prod_upper[FRAC_BITS-1:0]};
    end

    //: t / (2k+1): floor for the lower endpoint, ceil for the upper.
    wire [8:0] odd_divisor = {term_index[7:0], 1'b1};
    reg [FRAC_BITS+16:0] term_div_lower, term_div_upper;
    reg [FRAC_BITS+2:0]  term_share_lower, term_share_upper;
    always @* begin
        term_div_lower = divide_by_small({5'b0, t_lower}, odd_divisor);
        term_div_upper = divide_by_small({5'b0, t_upper}, odd_divisor);
        term_share_lower = term_div_lower[FRAC_BITS+11:9];
        term_share_upper = term_div_upper[FRAC_BITS+11:9]
                         + {{(FRAC_BITS+2){1'b0}}, |term_div_upper[8:0]};
    end

    // -- the final assembly, which is the one place extra integer width is
    //    needed: softplus(x) for x just under 20 is just under 20.694.
    localparam integer WIDE = FRAC_BITS + 7;
    //: A subnormal's ulp is 2**-149, so this is how far right of the
    //: fixed-point word's binary point its fraction's last bit sits.
    localparam integer SUB_SHIFT = FRAC_BITS - 149;
    reg [WIDE:0] wide_lower, wide_upper;
    //: THE WIDE FORMAT, not the interval's. The interval registers carry three
    //: bits above the binary point, which is all exp and sigmoid ever need
    //: because both are at most one. This operator's linear term is up to 20,
    //: which needs five -- and storing it in three silently dropped the top
    //: bits, so softplus(20) came out as 8.
    reg [WIDE:0] arg_fixed;
    wire [WIDE:0] doubled_lower = {{4{1'b0}}, s_lower, 1'b0};
    wire [WIDE:0] doubled_upper = {{4{1'b0}}, s_upper, 1'b0};

    function automatic [WIDE:0] magnitude_fixed;
        input [30:0] code;
        reg [7:0] exponent_field;
        reg [23:0] significand;
        reg [WIDE:0] wide_significand;
        integer shift_distance;
        begin
            exponent_field = code[30:23];
            significand = exponent_field == 0
                ? {1'b0, code[22:0]} : {1'b1, code[22:0]};
            wide_significand = {{(FRAC_BITS-16){1'b0}}, significand};
            magnitude_fixed = 0;
            //: value = significand * 2**(field - 150), in Q.FRAC_BITS.
            shift_distance = exponent_field == 0
                ? FRAC_BITS - 149
                : FRAC_BITS + {24'b0, exponent_field} - 150;
            if (shift_distance >= 0)
                magnitude_fixed = wide_significand << shift_distance;
            else
                magnitude_fixed = wide_significand >> -shift_distance;
        end
    endfunction

    function automatic [31:0] fixed_to_fp32_rne;
        input [WIDE:0] fixed_code;
        reg [23:0] main_mantissa;
        reg [24:0] rounded_mantissa;
        reg round_bit;
        reg sticky;
        reg [22:0] sub_frac;
        reg        sub_round;
        reg        sub_sticky;
        reg [23:0] sub_rounded;
        integer most_significant;
        integer floor_exponent;
        integer shift_distance;
        integer bit_index;
        begin
            main_mantissa = 0;
            rounded_mantissa = 0;
            round_bit = 0;
            sticky = 0;
            most_significant = -1;
            floor_exponent = 0;
            shift_distance = 0;
            fixed_to_fp32_rne = 0;
            for (bit_index = 0; bit_index <= WIDE; bit_index = bit_index + 1)
                if (fixed_code[bit_index]) most_significant = bit_index;
            if (most_significant >= 0) begin
                floor_exponent = most_significant - FRAC_BITS;
                shift_distance = most_significant - 23;
                for (bit_index = 0; bit_index < 24; bit_index = bit_index + 1)
                    if ((bit_index + shift_distance >= 0) &&
                        (bit_index + shift_distance <= WIDE))
                        main_mantissa[bit_index] =
                            fixed_code[bit_index + shift_distance];
                if (shift_distance > 0)
                    round_bit = fixed_code[shift_distance-1];
                for (bit_index = 0; bit_index <= WIDE; bit_index = bit_index + 1)
                    if (bit_index < shift_distance-1)
                        sticky = sticky | fixed_code[bit_index];
                rounded_mantissa = {1'b0, main_mantissa};
                if (round_bit && (sticky || main_mantissa[0]))
                    rounded_mantissa = rounded_mantissa + 1'b1;
                if (rounded_mantissa[24]) begin
                    rounded_mantissa = rounded_mantissa >> 1;
                    floor_exponent = floor_exponent + 1;
                end
                if (floor_exponent >= -126)
                    fixed_to_fp32_rne =
                        {1'b0, floor_exponent[7:0] + 8'd127,
                         rounded_mantissa[22:0]};
                else begin
                    //: A SUBNORMAL RESULT, which the deep tail of this operator
                    //: produces and the transcendental engine simply flushes:
                    //: softplus just above 2**-150 is the smallest subnormal.
                    //:
                    //: ROUNDED ONCE, FROM THE FIXED-POINT VALUE. A subnormal's
                    //: ulp is 2**-149 wherever it sits, so the fraction is
                    //: RNE(fixed_code / 2**(FRAC_BITS-149)) read straight out of
                    //: the fixed-point word -- eleven bits of shift at
                    //: FRAC_BITS = 160. Shifting the already-rounded 24-bit
                    //: significand instead rounds twice and truncates the
                    //: second one, which came out exactly one ulp low on every
                    //: subnormal case: 0 where the reference said 1, 1 where it
                    //: said 2, 9 where it said 10.
                    sub_frac = fixed_code[SUB_SHIFT+22:SUB_SHIFT];
                    sub_round = fixed_code[SUB_SHIFT-1];
                    sub_sticky = 1'b0;
                    for (bit_index = 0; bit_index < SUB_SHIFT-1;
                         bit_index = bit_index + 1)
                        sub_sticky = sub_sticky | fixed_code[bit_index];
                    sub_rounded = {1'b0, sub_frac};
                    if (sub_round && (sub_sticky || sub_frac[0]))
                        sub_rounded = sub_rounded + 1'b1;
                    //: Rounding up out of the fraction makes it the smallest
                    //: NORMAL, which is the one place a subnormal result can
                    //: leave its own exponent.
                    fixed_to_fp32_rne = sub_rounded[23]
                        ? {1'b0, 8'd1, 23'd0}
                        : {1'b0, 8'd0, sub_rounded[22:0]};
                end
            end
        end
    endfunction

    wire [31:0] rounded_lower = fixed_to_fp32_rne(wide_lower);
    wire [31:0] rounded_upper = fixed_to_fp32_rne(wide_upper);

    // -- the square root -----------------------------------------------------
    reg         sqrt_req;
    wire [31:0] sqrt_y;
    wire        sqrt_invalid, sqrt_valid, sqrt_busy;
    ot_a3_fp32_sqrt_rne square_root (
        .clk(clk), .rst_n(rst_n), .valid_in(sqrt_req),
        .a(softplus_code), .y(sqrt_y), .invalid(sqrt_invalid),
        .valid_out(sqrt_valid), .busy(sqrt_busy)
    );

    assign in_ready = (state == S_IDLE);
    assign softplus_out = softplus_code;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE; y <= 32'd0; error_code <= ERR_NONE;
            valid_out <= 1'b0; busy <= 1'b0; branch_taken <= BR_TRANSCEND;
            arg_q <= 32'd0; arg_sign_q <= 1'b0;
            u_lower <= 0; u_upper <= 0;
            z_lower <= 0; z_upper <= 0;
            zsq_lower <= 0; zsq_upper <= 0;
            t_lower <= 0; t_upper <= 0;
            s_lower <= 0; s_upper <= 0;
            wide_lower <= 0; wide_upper <= 0;
            arg_fixed <= 0;
            term_index <= 9'd0; softplus_code <= 32'd0;
            exp_req <= 1'b0; sqrt_req <= 1'b0;
        end else begin
            valid_out <= 1'b0;
            exp_req <= 1'b0;
            sqrt_req <= 1'b0;
            case (state)
                S_IDLE: if (valid_in) begin
                    arg_q <= a;
                    arg_sign_q <= a[31];
                    arg_fixed <= magnitude_fixed(a[30:0]);
                    error_code <= ERR_NONE;
                    if (arg_nonfinite) begin
                        //: The reference raises rather than returning a value.
                        error_code <= ERR_ARGUMENT;
                        softplus_code <= 32'd0;
                        y <= 32'd0;
                        valid_out <= 1'b1;
                    end else if (arg_gt_20) begin
                        //: softplus is the input, bit for bit, so only the
                        //: square root remains.
                        branch_taken <= BR_LINEAR;
                        softplus_code <= a;
                        busy <= 1'b1;
                        sqrt_req <= 1'b1;
                        state <= S_SQRT;
                    end else if (arg_le_neg105) begin
                        branch_taken <= BR_UNDERFLOW;
                        //: The intermediate is published, so it must be SET on
                        //: every branch. Left alone it reads whatever the
                        //: previous request put there, which is a stale value
                        //: on a port a campaign is checking.
                        softplus_code <= 32'd0;
                        y <= 32'd0;
                        valid_out <= 1'b1;
                    end else begin
                        branch_taken <= BR_TRANSCEND;
                        busy <= 1'b1;
                        if (arg_zero) begin
                            //: exp(0) is exactly one, and the engine answers a
                            //: zero argument from an early exit that publishes
                            //: no interval -- so the interval is set here
                            //: rather than asked for.
                            u_lower <= FIXED_ONE;
                            u_upper <= FIXED_ONE;
                            state <= S_ZFORM;
                        end else begin
                            exp_req <= 1'b1;
                            state <= S_EXP;
                        end
                    end
                end

                S_EXP: if (exp_valid) begin
                    if ((exp_error != 2'd0) || !exp_interval_exact) begin
                        error_code <= ERR_UNCERTIFIED;
                        y <= 32'd0;
                        busy <= 1'b0;
                        valid_out <= 1'b1;
                        state <= S_IDLE;
                    end else begin
                        u_lower <= exp_lower;
                        u_upper <= exp_upper;
                        state <= S_ZFORM;
                    end
                end

                S_ZFORM: begin
                    z_lower <= z_next_lower;
                    z_upper <= z_next_upper;
                    state <= S_ZSQ;
                end

                S_ZSQ: begin
                    zsq_lower <= mul_lower;
                    zsq_upper <= mul_upper;
                    //: The series opens at term zero, which is z itself over
                    //: one.
                    t_lower <= z_lower;
                    t_upper <= z_upper;
                    s_lower <= 0;
                    s_upper <= 0;
                    term_index <= 9'd0;
                    state <= S_SUM;
                end

                //: sum += t/(2k+1), then t *= z**2.
                S_SUM: begin
                    s_lower <= s_lower + term_share_lower;
                    s_upper <= s_upper + term_share_upper;
                    t_lower <= mul_lower;
                    t_upper <= mul_upper;
                    if (term_index + 9'd1 >= ATANH_TERMS[8:0]) begin
                        state <= S_TAIL;
                    end else begin
                        term_index <= term_index + 9'd1;
                    end
                end

                //: THE TAIL, which an all-positive series needs and the
                //: alternating exponential does not. Twice the next term over
                //: its own divisor bounds the whole remainder for z <= 1/3,
                //: where the true factor is 9/8.
                S_TAIL: begin
                    //: The series sum is DOUBLED (log(1+u) = 2*atanh(z)); the
                    //: linear term is NOT. Concatenating a trailing zero onto
                    //: both doubled the argument too, and softplus(x) = 2x +
                    //: log(1+exp(-x)) is a different function.
                    wide_lower <= doubled_lower
                                + (arg_sign_q ? {(WIDE+1){1'b0}} : arg_fixed);
                    wide_upper <= doubled_upper
                                + {{4{1'b0}}, term_share_upper, 1'b1}
                                + (arg_sign_q ? {(WIDE+1){1'b0}} : arg_fixed);
                    state <= S_ROUND;
                end

                S_ROUND: begin
                    if (rounded_lower != rounded_upper) begin
                        error_code <= ERR_UNCERTIFIED;
                        y <= 32'd0;
                        busy <= 1'b0;
                        valid_out <= 1'b1;
                        state <= S_IDLE;
                    end else begin
                        softplus_code <= rounded_lower;
                        sqrt_req <= 1'b1;
                        state <= S_SQRT;
                    end
                end

                S_SQRT: if (sqrt_valid) begin
                    if (sqrt_invalid) begin
                        error_code <= ERR_UNCERTIFIED;
                        y <= 32'd0;
                    end else begin
                        y <= sqrt_y;
                    end
                    busy <= 1'b0;
                    valid_out <= 1'b1;
                    state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
