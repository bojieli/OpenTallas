// SPDX-License-Identifier: Apache-2.0
//
// ot_a3_fp32_div_rne_pipe -- the correctly-rounded binary32 divider, with its
// bisection step split across two cycles.
//
// WHY.  ``ot_a3_fp32_div_rne`` closes on ASAP7 at 3.6 ns, 283.5 MHz
// (results/physical_abi3/asap7/fp32_div_rne/pnr_3p6ns_closed.json).  Seven
// parents instantiate it -- ot_a3_attention_epilogue, ot_a3_hc_sinkhorn20_rne,
// ot_a3_hc_stable_softmax_rne, ot_a3_qwen_gqa, ot_a3_route_weight_normalize,
// ot_a3_vector_engram_gate, ot_a3_vector_silu_mul -- all on the token path, and
// it sits inside ot_a3_engine_issue_bridge, so it bounds the engine complex.
//
// Its routed critical path is ONE bisection step, entire, in one cycle:
// ``lower_code`` -> midpoint -> decode -> 24x24 multiply -> 97-bit align ->
// compare -> update bounds.  Three changes shorten it without changing what it
// computes:
//
//   1. THE MULTIPLY IS REGISTERED.  The step becomes two cycles: one that forms
//      the 49-bit product of the candidate significand and the divisor, and one
//      that aligns it against the numerator and moves the bracket.  A division
//      takes about twice the cycles at well under half the period, which is the
//      trade a shared clock wants -- every other block on that clock gets the
//      shorter period too.
//
//   2. THE ROUNDING COMPARISON LEAVES THE LOOP.  The reference evaluates a
//      SECOND full comparison every cycle, for the round-to-nearest-even
//      midpoint between ``lower_code`` and its successor.  That value is only
//      read once, after the bracket has closed.  Here it is computed then, in
//      its own two cycles, so the per-cycle logic carries one comparator
//      instead of two.
//
//   3. THE BRACKET IS SEEDED FROM THE EXPONENTS.  The reference bisects the whole
//      31-bit code space, ~31 steps, when the quotient's exponent is arithmetic:
//      for normal operands with significands in [1,2) the ratio lies strictly in
//      (2**(ed-1), 2**(ed+1)) where ed = e_n - e_d, so the result's biased
//      exponent is ed+126 or ed+127 and the answer's code lies in
//      [(ed+126)<<23, ((ed+128)<<23)-1].  Seeding that two-exponent window costs
//      ~24 steps instead of ~31.  A subnormal operand breaks the argument, so
//      those fall back to the full range -- falling back is always correct and
//      only slower.
//
// WHAT IS NOT CHANGED.  The ports, the algorithm and every result.  The bracket
// update, the MAX_FINITE clamps, the overflow boundary (the real candidate one
// ULP above max finite is 2**128, so its midpoint with max finite is the RNE
// overflow boundary) and the tie-to-even rule are transcribed from the
// reference.  ``rtl/test/tb_a3_fp32_div_pipe_equiv.sv`` drives both modules from
// one stimulus and asserts ``result_code`` and ``result_error`` are bit-equal.
//
// The handshake is why no parent changes: ``in_valid``/``in_ready`` and
// ``out_valid``/``out_ready`` are unchanged, so a caller sees only more latency.
`default_nettype none

module ot_a3_fp32_div_rne_pipe (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        in_valid,
    output wire        in_ready,
    input  wire [31:0] numerator_code,
    input  wire [31:0] denominator_code,
    output reg         out_valid,
    input  wire        out_ready,
    output reg  [31:0] result_code,
    output reg  [1:0]  result_error
);
    localparam [1:0] ERR_NONE     = 2'd0;
    localparam [1:0] ERR_ARGUMENT = 2'd1;
    localparam [1:0] ERR_OVERFLOW = 2'd2;
    localparam [30:0] MAX_FINITE  = 31'h7f7f_ffff;

    // Phases.  STEP_* are the bisection; ROUND_* run once, after it closes.
    localparam [1:0] STEP_MUL  = 2'd0;
    localparam [1:0] STEP_CMP  = 2'd1;
    localparam [1:0] ROUND_MUL = 2'd2;
    localparam [1:0] ROUND_CMP = 2'd3;

    reg        busy;
    reg [1:0]  phase;
    reg        result_sign;
    reg [30:0] low_code;
    reg [30:0] high_code;
    reg [30:0] lower_code;
    reg [23:0] numerator_significand;
    reg [23:0] denominator_significand;
    integer    numerator_power;
    integer    denominator_power;

    // Stage-1 registers: what the multiply cycle hands the compare cycle.
    reg [48:0] product_q;
    integer    product_lsb_power_q;
    reg        degenerate_q;      // a zero significand on either side
    reg [30:0] candidate_code_q;

    // ---- decode, shared by both cycles -----------------------------------
    task automatic decode_positive;
        input [30:0] code;
        output [23:0] significand;
        output integer value_power;
        begin
            if (code[30:23] == 0) begin
                significand = {1'b0, code[22:0]};
                value_power = -149;
            end else begin
                significand = {1'b1, code[22:0]};
                value_power = {24'b0, code[30:23]} - 150;
            end
        end
    endtask

    // ---- cycle one: the product ------------------------------------------
    wire [30:0] candidate_code = low_code + ((high_code - low_code) >> 1);
    reg  [23:0] candidate_significand;
    integer     candidate_power;

    // The RNE midpoint of [lower_code, lower_code + 1], formed once the bracket
    // has closed.  Transcribed from the reference, including the 2**128 upper
    // bound that makes the max-finite midpoint the overflow boundary.
    reg [24:0] lower_significand;
    reg [24:0] upper_significand;
    integer    lower_power;
    integer    upper_power;
    integer    common_power;
    reg [24:0] lower_aligned;
    reg [24:0] upper_aligned;
    reg [24:0] midpoint_significand;
    integer    midpoint_power;

    always @* begin
        decode_positive(candidate_code, candidate_significand, candidate_power);

        decode_positive(lower_code, lower_significand[23:0], lower_power);
        lower_significand[24] = 1'b0;
        if (lower_code == MAX_FINITE) begin
            upper_significand = 25'h1_000000;
            upper_power = 104;
        end else begin
            decode_positive(lower_code + 1'b1, upper_significand[23:0],
                            upper_power);
            upper_significand[24] = 1'b0;
        end
        common_power = lower_power < upper_power ? lower_power : upper_power;
        lower_aligned = lower_significand << (lower_power - common_power);
        upper_aligned = upper_significand << (upper_power - common_power);
        midpoint_significand = lower_aligned + upper_aligned;
        midpoint_power = common_power - 1;
    end

    // ---- cycle two: align the registered product and compare -------------
    // The reference's ``compare_product_to_numerator`` from the multiply
    // onward.  Splitting there is what shortens the path: the 25x24 multiply
    // and the 97-bit alignment no longer share a cycle.
    // Balanced leading-zero normalization: six bounded shifts, with the
    // exponent adjustment accumulated alongside the normalized significand.
    function automatic [54:0] normalize49(input [48:0] value);
        reg [48:0] work_value;
        reg [5:0] shift;
        begin
            work_value=value;shift=0;
            if(work_value[48:17]==0)begin work_value=work_value<<32;shift=shift+32;end
            if(work_value[48:33]==0)begin work_value=work_value<<16;shift=shift+16;end
            if(work_value[48:41]==0)begin work_value=work_value<<8;shift=shift+8;end
            if(work_value[48:45]==0)begin work_value=work_value<<4;shift=shift+4;end
            if(work_value[48:47]==0)begin work_value=work_value<<2;shift=shift+2;end
            if(work_value[48]==0)begin work_value=work_value<<1;shift=shift+1;end
            normalize49={shift,work_value};
        end
    endfunction

    function automatic integer compare_registered_product;
        input [48:0] product;
        input integer product_lsb_power;
        input         degenerate;
        input [23:0]  dividend_significand;
        input integer dividend_power;
        reg [48:0] product_aligned;
        reg [48:0] dividend_aligned;
        integer product_msb;
        integer dividend_msb;
        integer product_top_power;
        integer dividend_top_power;
        reg [54:0] product_normalized,dividend_normalized;
        begin
            product_normalized=normalize49(product);
            dividend_normalized=normalize49({25'b0,dividend_significand});
            product_aligned = 0;
            dividend_aligned = 0;
            product_msb = -1;
            dividend_msb = -1;
            if (degenerate) begin
                compare_registered_product =
                    dividend_significand == 0 ? 0 : -1;
            end else begin
                product_msb=48-integer'({1'b0,product_normalized[54:49]});
                dividend_msb=dividend_significand==0?-1:48-integer'({1'b0,dividend_normalized[54:49]});
                if (dividend_msb < 0) begin
                    compare_registered_product = 1;
                end else begin
                    product_top_power = product_msb + product_lsb_power;
                    dividend_top_power = dividend_msb + dividend_power;
                    if (product_top_power < dividend_top_power) begin
                        compare_registered_product = -1;
                    end else if (product_top_power > dividend_top_power) begin
                        compare_registered_product = 1;
                    end else begin
                        // Equal top powers: align both leading ones to bit
                        // 48. Neither operand loses bits (product <=49 bits,
                        // dividend <=24 bits). This compares exact fractions
                        // without exponent-difference-controlled 97-bit shifts.
                        product_aligned = product_normalized[48:0];
                        dividend_aligned = dividend_normalized[48:0];
                        if (product_aligned < dividend_aligned)
                            compare_registered_product = -1;
                        else if (product_aligned > dividend_aligned)
                            compare_registered_product = 1;
                        else
                            compare_registered_product = 0;
                    end
                end
            end
        end
    endfunction

    integer comparison;
    reg [30:0] rounded_magnitude;
    reg        rounded_overflow;

    always @* begin
        comparison = compare_registered_product(
            product_q, product_lsb_power_q, degenerate_q,
            numerator_significand, numerator_power
        );
        // The rounding decision, from that same comparison when the phase is
        // ROUND_CMP.  Identical rule to the reference: round up when the
        // midpoint is below the quotient, and on an exact tie when the low
        // code is odd.
        rounded_magnitude = lower_code;
        rounded_overflow = 1'b0;
        if (comparison < 0) begin
            if (lower_code == MAX_FINITE)
                rounded_overflow = 1'b1;
            else
                rounded_magnitude = lower_code + 1'b1;
        end else if (comparison == 0 && lower_code[0]) begin
            if (lower_code == MAX_FINITE)
                rounded_overflow = 1'b1;
            else
                rounded_magnitude = lower_code + 1'b1;
        end
    end

    // ---- the seeded bracket ------------------------------------------------
    // Both operands normal: the quotient's biased exponent is ed+126 or ed+127,
    // so the answer's code lies in [(ed+126)<<23, ((ed+128)<<23)-1], clamped to
    // the code space.  Either operand subnormal: the [1,2) significand argument
    // does not hold, so the full range is used.
    wire        numerator_subnormal   = (numerator_code[30:23] == 8'd0);
    wire        denominator_subnormal = (denominator_code[30:23] == 8'd0);
    wire signed [10:0] exponent_difference =
        $signed({3'b0, numerator_code[30:23]}) -
        $signed({3'b0, denominator_code[30:23]});
    wire signed [10:0] low_exponent  = exponent_difference + 11'sd126;
    wire signed [10:0] high_exponent = exponent_difference + 11'sd128;
    wire [30:0] seed_low =
        (numerator_subnormal || denominator_subnormal) ? 31'd0 :
        (low_exponent <= 11'sd0) ? 31'd0 :
        (low_exponent >= 11'sd255) ? MAX_FINITE :
        {low_exponent[7:0], 23'd0};
    wire [30:0] seed_high =
        (numerator_subnormal || denominator_subnormal) ? MAX_FINITE :
        (high_exponent >= 11'sd255) ? MAX_FINITE :
        (high_exponent <= 11'sd0) ? MAX_FINITE :
        (({high_exponent[7:0], 23'd0} - 31'd1) > MAX_FINITE
            ? MAX_FINITE : ({high_exponent[7:0], 23'd0} - 31'd1));

    assign in_ready = !busy && (!out_valid || out_ready);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0;
            phase <= STEP_MUL;
            result_sign <= 1'b0;
            low_code <= 0;
            high_code <= 0;
            lower_code <= 0;
            numerator_significand <= 0;
            denominator_significand <= 0;
            numerator_power <= 0;
            denominator_power <= 0;
            product_q <= 0;
            product_lsb_power_q <= 0;
            degenerate_q <= 1'b0;
            candidate_code_q <= 0;
            out_valid <= 1'b0;
            result_code <= 0;
            result_error <= ERR_NONE;
        end else begin
            if (out_valid && out_ready)
                out_valid <= 1'b0;

            if (in_valid && in_ready) begin
                result_code <= 0;
                result_error <= ERR_NONE;
                phase <= STEP_MUL;
                if (numerator_code[30:23] == 8'hff ||
                    denominator_code[30:23] == 8'hff ||
                    denominator_code[30:0] == 0) begin
                    busy <= 1'b0;
                    out_valid <= 1'b1;
                    result_error <= ERR_ARGUMENT;
                end else if (numerator_code[30:0] == 0) begin
                    busy <= 1'b0;
                    out_valid <= 1'b1;
                    result_code <= 0;
                end else begin
                    busy <= 1'b1;
                    result_sign <= numerator_code[31] ^ denominator_code[31];
                    // The seeded bracket.  ``lower_code`` still starts at 0 and
                    // that is safe: the window's low end is the code of
                    // 2**(ed-1), which is strictly BELOW the ratio, so the search
                    // always moves ``lower_code`` to at least that code and never
                    // reports the initial value.
                    low_code <= seed_low;
                    high_code <= seed_high;
                    lower_code <= 0;
                    if (numerator_code[30:23] == 0) begin
                        numerator_significand <= {1'b0, numerator_code[22:0]};
                        numerator_power <= -149;
                    end else begin
                        numerator_significand <= {1'b1, numerator_code[22:0]};
                        numerator_power <= {24'b0, numerator_code[30:23]} - 150;
                    end
                    if (denominator_code[30:23] == 0) begin
                        denominator_significand <= {1'b0, denominator_code[22:0]};
                        denominator_power <= -149;
                    end else begin
                        denominator_significand <= {1'b1, denominator_code[22:0]};
                        denominator_power <=
                            {24'b0, denominator_code[30:23]} - 150;
                    end
                end
            end else if (busy) begin
                case (phase)
                    STEP_MUL: begin
                        if (low_code <= high_code) begin
                            candidate_code_q <= candidate_code;
                            degenerate_q <= (candidate_significand == 0) ||
                                            (denominator_significand == 0);
                            product_q <= {25'b0, candidate_significand} *
                                         {25'b0, denominator_significand};
                            product_lsb_power_q <=
                                candidate_power + denominator_power;
                            phase <= STEP_CMP;
                        end else begin
                            // The bracket has closed.  Form the midpoint
                            // product once, here, rather than every cycle.
                            degenerate_q <= (midpoint_significand == 0) ||
                                            (denominator_significand == 0);
                            product_q <= midpoint_significand *
                                         {25'b0, denominator_significand};
                            product_lsb_power_q <=
                                midpoint_power + denominator_power;
                            phase <= ROUND_CMP;
                        end
                    end
                    STEP_CMP: begin
                        if (comparison <= 0) begin
                            lower_code <= candidate_code_q;
                            if (candidate_code_q == MAX_FINITE) begin
                                low_code <= MAX_FINITE;
                                high_code <= MAX_FINITE - 1'b1;
                            end else begin
                                low_code <= candidate_code_q + 1'b1;
                            end
                        end else begin
                            if (candidate_code_q == 0) begin
                                high_code <= 0;
                                low_code <= 1;
                            end else begin
                                high_code <= candidate_code_q - 1'b1;
                            end
                        end
                        phase <= STEP_MUL;
                    end
                    ROUND_CMP: begin
                        busy <= 1'b0;
                        out_valid <= 1'b1;
                        phase <= STEP_MUL;
                        if (rounded_overflow) begin
                            result_code <= 0;
                            result_error <= ERR_OVERFLOW;
                        end else if (rounded_magnitude == 0) begin
                            result_code <= 0;
                            result_error <= ERR_NONE;
                        end else begin
                            result_code <= {result_sign, rounded_magnitude};
                            result_error <= ERR_NONE;
                        end
                    end
                    default: phase <= STEP_MUL;
                endcase
            end
        end
    end
endmodule

`default_nettype wire
