`timescale 1ns/1ps
// Synthesizable finite IEEE-binary32 helpers for target-visible Qwen numeric
// contracts.  Results use round-to-nearest, ties-to-even and canonical positive
// zero.  The packed return convention is {error[1:0], value}; error 1 denotes
// an illegal/nonfinite operand and error 2 denotes finite binary32 overflow.
package ot_fp32_rne_pkg;
    localparam [1:0] FP_ERR_NONE      = 2'd0;
    localparam [1:0] FP_ERR_NONFINITE = 2'd1;
    localparam [1:0] FP_ERR_OVERFLOW  = 2'd2;

    function automatic [27:0] shift_right_jam_28;
        input [27:0] value;
        input integer distance;
        integer bit_index;
        reg discarded;
        reg [27:0] shifted;
        begin
            discarded = 1'b0;
            shifted = 28'b0;
            if (distance <= 0) begin
                shifted = value;
            end else if (distance >= 28) begin
                shifted[0] = |value;
            end else begin
                shifted = value >> distance;
                for (bit_index = 0; bit_index < 28; bit_index = bit_index + 1)
                    if (bit_index < distance)
                        discarded = discarded | value[bit_index];
                shifted[0] = shifted[0] | discarded;
            end
            shift_right_jam_28 = shifted;
        end
    endfunction

    function automatic [23:0] shift_right_48_to_24;
        input [47:0] value;
        input integer distance;
        integer bit_index;
        begin
            shift_right_48_to_24 = 0;
            for (bit_index = 0; bit_index < 24; bit_index = bit_index + 1)
                if ((bit_index + distance >= 0) &&
                    (bit_index + distance < 48))
                    shift_right_48_to_24[bit_index] =
                        value[bit_index + distance];
        end
    endfunction

    // Positive-only addition is sufficient for RMS-square reductions and the
    // positive epsilon addition.  Rejecting negative inputs keeps accidental
    // use outside that contract fail closed.
    function automatic [33:0] fp32_add_positive_rne;
        input [31:0] left_code;
        input [31:0] right_code;
        reg [1:0] error;
        reg [31:0] result;
        reg [7:0] left_field;
        reg [7:0] right_field;
        reg [7:0] left_exponent;
        reg [7:0] right_exponent;
        reg [7:0] large_exponent;
        reg [7:0] small_exponent;
        reg [23:0] left_mantissa;
        reg [23:0] right_mantissa;
        reg [23:0] large_mantissa;
        reg [23:0] small_mantissa;
        reg [27:0] large_extended;
        reg [27:0] small_extended;
        reg [27:0] sum_extended;
        reg [26:0] normalized;
        reg [24:0] rounded_mantissa;
        reg round_increment;
        integer distance;
        begin
            error = FP_ERR_NONE;
            result = 32'b0;
            left_field = left_code[30:23];
            right_field = right_code[30:23];
            left_exponent = left_field == 0 ? 8'd1 : left_field;
            right_exponent = right_field == 0 ? 8'd1 : right_field;
            left_mantissa = left_field == 0
                            ? {1'b0, left_code[22:0]}
                            : {1'b1, left_code[22:0]};
            right_mantissa = right_field == 0
                             ? {1'b0, right_code[22:0]}
                             : {1'b1, right_code[22:0]};
            large_exponent = left_exponent;
            small_exponent = right_exponent;
            large_mantissa = left_mantissa;
            small_mantissa = right_mantissa;
            large_extended = 0;
            small_extended = 0;
            sum_extended = 0;
            normalized = 0;
            rounded_mantissa = 0;
            round_increment = 0;
            distance = 0;

            if (left_code[31] || right_code[31] ||
                left_field == 8'hff || right_field == 8'hff) begin
                error = FP_ERR_NONFINITE;
            end else if (left_mantissa == 0) begin
                result = right_mantissa == 0 ? 32'b0 : right_code;
            end else if (right_mantissa == 0) begin
                result = left_code;
            end else begin
                if ((right_exponent > left_exponent) ||
                    ((right_exponent == left_exponent) &&
                     (right_mantissa > left_mantissa))) begin
                    large_exponent = right_exponent;
                    small_exponent = left_exponent;
                    large_mantissa = right_mantissa;
                    small_mantissa = left_mantissa;
                end
                distance = {24'b0, large_exponent};
                distance = distance - {24'b0, small_exponent};
                large_extended = {1'b0, large_mantissa, 3'b000};
                small_extended = shift_right_jam_28(
                    {1'b0, small_mantissa, 3'b000}, distance
                );
                sum_extended = large_extended + small_extended;
                normalized = sum_extended[26:0];
                if (sum_extended[27]) begin
                    normalized = sum_extended[27:1];
                    normalized[0] = normalized[0] | sum_extended[0];
                    large_exponent = large_exponent + 1'b1;
                end
                if (large_exponent >= 8'hff) begin
                    error = FP_ERR_OVERFLOW;
                end else begin
                    rounded_mantissa = {1'b0, normalized[26:3]};
                    round_increment = normalized[2] &&
                                      ((|normalized[1:0]) || normalized[3]);
                    if (round_increment)
                        rounded_mantissa = rounded_mantissa + 1'b1;
                    if (rounded_mantissa[24]) begin
                        rounded_mantissa = rounded_mantissa >> 1;
                        large_exponent = large_exponent + 1'b1;
                    end
                    if (large_exponent >= 8'hff) begin
                        error = FP_ERR_OVERFLOW;
                        result = 0;
                    end else if ((large_exponent == 1) &&
                                 !rounded_mantissa[23]) begin
                        result = {9'b0, rounded_mantissa[22:0]};
                    end else begin
                        result = {
                            1'b0, large_exponent, rounded_mantissa[22:0]
                        };
                    end
                    if (result[30:0] == 0)
                        result = 0;
                end
            end
            fp32_add_positive_rne = {error, result};
        end
    endfunction

    // General finite binary32 addition for signed MATMUL accumulators.  The
    // larger-magnitude operand supplies the result sign for subtraction;
    // exact cancellation and every signed-zero combination canonicalize to
    // positive zero.  Three explicit rounding bits plus a jammed sticky bit
    // retain the information required by round-to-nearest, ties-to-even.
    function automatic [33:0] fp32_add_rne;
        input [31:0] left_code;
        input [31:0] right_code;
        reg [1:0] error;
        reg [31:0] result;
        reg left_sign;
        reg right_sign;
        reg result_sign;
        reg [7:0] left_field;
        reg [7:0] right_field;
        reg [7:0] left_exponent;
        reg [7:0] right_exponent;
        reg [7:0] large_exponent;
        reg [7:0] small_exponent;
        reg [23:0] left_mantissa;
        reg [23:0] right_mantissa;
        reg [23:0] large_mantissa;
        reg [23:0] small_mantissa;
        reg [27:0] large_extended;
        reg [27:0] small_extended;
        reg [27:0] arithmetic_extended;
        reg [26:0] normalized;
        reg [24:0] rounded_mantissa;
        reg round_increment;
        integer distance;
        integer shift_count;
        begin
            error = FP_ERR_NONE;
            result = 0;
            left_sign = left_code[31];
            right_sign = right_code[31];
            result_sign = left_sign;
            left_field = left_code[30:23];
            right_field = right_code[30:23];
            left_exponent = left_field == 0 ? 8'd1 : left_field;
            right_exponent = right_field == 0 ? 8'd1 : right_field;
            left_mantissa = left_field == 0
                            ? {1'b0, left_code[22:0]}
                            : {1'b1, left_code[22:0]};
            right_mantissa = right_field == 0
                             ? {1'b0, right_code[22:0]}
                             : {1'b1, right_code[22:0]};
            large_exponent = left_exponent;
            small_exponent = right_exponent;
            large_mantissa = left_mantissa;
            small_mantissa = right_mantissa;
            large_extended = 0;
            small_extended = 0;
            arithmetic_extended = 0;
            normalized = 0;
            rounded_mantissa = 0;
            round_increment = 0;
            distance = 0;
            shift_count = 0;

            if (left_field == 8'hff || right_field == 8'hff) begin
                error = FP_ERR_NONFINITE;
            end else if (left_mantissa == 0) begin
                result = right_mantissa == 0 ? 32'b0 : right_code;
            end else if (right_mantissa == 0) begin
                result = left_code;
            end else begin
                if ((right_exponent > left_exponent) ||
                    ((right_exponent == left_exponent) &&
                     (right_mantissa > left_mantissa))) begin
                    large_exponent = right_exponent;
                    small_exponent = left_exponent;
                    large_mantissa = right_mantissa;
                    small_mantissa = left_mantissa;
                    result_sign = right_sign;
                end
                distance = {24'b0, large_exponent};
                distance = distance - {24'b0, small_exponent};
                large_extended = {1'b0, large_mantissa, 3'b000};
                small_extended = shift_right_jam_28(
                    {1'b0, small_mantissa, 3'b000}, distance
                );

                if (left_sign == right_sign) begin
                    arithmetic_extended = large_extended + small_extended;
                    normalized = arithmetic_extended[26:0];
                    if (arithmetic_extended[27]) begin
                        normalized = arithmetic_extended[27:1];
                        normalized[0] = normalized[0] |
                                        arithmetic_extended[0];
                        large_exponent = large_exponent + 1'b1;
                    end
                end else begin
                    arithmetic_extended = large_extended - small_extended;
                    if (arithmetic_extended == 0) begin
                        result = 0;
                    end else begin
                        // Equal-exponent cancellation is exact before this
                        // normalization; exponent-separated subtraction uses
                        // the jam bit to preserve the final rounding decision.
                        for (shift_count = 0; shift_count < 27;
                             shift_count = shift_count + 1) begin
                            if (!arithmetic_extended[26] &&
                                (large_exponent > 1)) begin
                                arithmetic_extended =
                                    arithmetic_extended << 1;
                                large_exponent = large_exponent - 1'b1;
                            end
                        end
                        normalized = arithmetic_extended[26:0];
                    end
                end

                if (arithmetic_extended != 0) begin
                    if (large_exponent >= 8'hff) begin
                        error = FP_ERR_OVERFLOW;
                    end else begin
                        rounded_mantissa = {1'b0, normalized[26:3]};
                        round_increment = normalized[2] &&
                                          ((|normalized[1:0]) ||
                                           normalized[3]);
                        if (round_increment)
                            rounded_mantissa = rounded_mantissa + 1'b1;
                        if (rounded_mantissa[24]) begin
                            rounded_mantissa = rounded_mantissa >> 1;
                            large_exponent = large_exponent + 1'b1;
                        end
                        if (large_exponent >= 8'hff) begin
                            error = FP_ERR_OVERFLOW;
                            result = 0;
                        end else if ((large_exponent == 1) &&
                                     !rounded_mantissa[23]) begin
                            result = {
                                result_sign, 8'b0,
                                rounded_mantissa[22:0]
                            };
                        end else begin
                            result = {
                                result_sign, large_exponent,
                                rounded_mantissa[22:0]
                            };
                        end
                        if (result[30:0] == 0)
                            result = 0;
                    end
                end
            end
            fp32_add_rne = {error, result};
        end
    endfunction

    function automatic [33:0] fp32_mul_rne;
        input [31:0] left_code;
        input [31:0] right_code;
        reg [1:0] error;
        reg [31:0] result;
        reg result_sign;
        reg [7:0] left_field;
        reg [7:0] right_field;
        reg [23:0] left_mantissa;
        reg [23:0] right_mantissa;
        reg [47:0] product;
        reg [23:0] main_mantissa;
        reg [24:0] rounded_mantissa;
        reg [7:0] encoded_exponent;
        reg round_bit;
        reg sticky;
        integer left_power;
        integer right_power;
        integer product_msb;
        integer floor_exponent;
        integer shift_distance;
        integer bit_index;
        begin
            error = FP_ERR_NONE;
            result = 0;
            result_sign = left_code[31] ^ right_code[31];
            left_field = left_code[30:23];
            right_field = right_code[30:23];
            left_mantissa = left_field == 0
                            ? {1'b0, left_code[22:0]}
                            : {1'b1, left_code[22:0]};
            right_mantissa = right_field == 0
                             ? {1'b0, right_code[22:0]}
                             : {1'b1, right_code[22:0]};
            left_power = {24'b0, left_field};
            right_power = {24'b0, right_field};
            if (left_field == 0)
                left_power = -149;
            else
                left_power = left_power - 150;
            if (right_field == 0)
                right_power = -149;
            else
                right_power = right_power - 150;
            product = 0;
            main_mantissa = 0;
            rounded_mantissa = 0;
            encoded_exponent = 0;
            round_bit = 0;
            sticky = 0;
            product_msb = -1;
            floor_exponent = 0;
            shift_distance = 0;

            if (left_field == 8'hff || right_field == 8'hff) begin
                error = FP_ERR_NONFINITE;
            end else if (left_mantissa == 0 || right_mantissa == 0) begin
                result = 0;
            end else begin
                // Normalize binary32 subnormals into the same 24-bit form as
                // normal operands while retaining the exact power of two.
                for (bit_index = 0; bit_index < 23; bit_index = bit_index + 1) begin
                    if (!left_mantissa[23]) begin
                        left_mantissa = left_mantissa << 1;
                        left_power = left_power - 1;
                    end
                    if (!right_mantissa[23]) begin
                        right_mantissa = right_mantissa << 1;
                        right_power = right_power - 1;
                    end
                end
                // Size the first operand to the complete result width.  Plain
                // Verilog multiplication otherwise inherits tool-dependent
                // expression sizing before the assignment to ``product``.
                product = {24'b0, left_mantissa} * right_mantissa;
                for (bit_index = 0; bit_index < 48; bit_index = bit_index + 1)
                    if (product[bit_index])
                        product_msb = bit_index;
                floor_exponent = product_msb + left_power + right_power;

                if (floor_exponent >= -126) begin
                    shift_distance = product_msb - 23;
                    main_mantissa = shift_right_48_to_24(
                        product, shift_distance
                    );
                    round_bit = shift_distance > 0
                                ? product[shift_distance-1] : 1'b0;
                    sticky = 1'b0;
                    for (bit_index = 0; bit_index < 48; bit_index = bit_index + 1)
                        if (bit_index < shift_distance-1)
                            sticky = sticky | product[bit_index];
                    rounded_mantissa = {1'b0, main_mantissa};
                    if (round_bit && (sticky || main_mantissa[0]))
                        rounded_mantissa = rounded_mantissa + 1'b1;
                    if (rounded_mantissa[24]) begin
                        rounded_mantissa = rounded_mantissa >> 1;
                        floor_exponent = floor_exponent + 1;
                    end
                    if (floor_exponent > 127) begin
                        error = FP_ERR_OVERFLOW;
                        result = 0;
                    end else begin
                        encoded_exponent = floor_exponent[7:0] + 8'd127;
                        result = {
                            result_sign,
                            encoded_exponent,
                            rounded_mantissa[22:0]
                        };
                    end
                end else begin
                    // Round directly in units of the binary32 subnormal LSB.
                    shift_distance = -(left_power + right_power + 149);
                    if (shift_distance >= 48)
                        main_mantissa = 0;
                    else begin
                        main_mantissa = shift_right_48_to_24(
                            product, shift_distance
                        );
                    end
                    round_bit = (shift_distance > 0 && shift_distance <= 48)
                                ? product[shift_distance-1] : 1'b0;
                    sticky = 1'b0;
                    for (bit_index = 0; bit_index < 48; bit_index = bit_index + 1)
                        if (bit_index < shift_distance-1)
                            sticky = sticky | product[bit_index];
                    rounded_mantissa = {1'b0, main_mantissa};
                    if (round_bit && (sticky || main_mantissa[0]))
                        rounded_mantissa = rounded_mantissa + 1'b1;
                    if (rounded_mantissa >= 25'h0800000)
                        result = {result_sign, 8'h01, 23'b0};
                    else
                        result = {result_sign, 8'h00,
                                  rounded_mantissa[22:0]};
                end
                if (result[30:0] == 0)
                    result = 0;
            end
            fp32_mul_rne = {error, result};
        end
    endfunction

    // One NUM-4.1 ordered-dot step.  The BF16 product is kept exact and is
    // added to the exact value of the binary32 accumulator before the single
    // binary32 round-to-nearest-even boundary.  In particular, this is not
    // equivalent to composing fp32_mul_rne with fp32_add_rne: a BF16 product
    // can carry fourteen fraction bits, seven more than either operand, and
    // those low bits can decide the final accumulator rounding.
    //
    // Every finite BF16 product and binary32 accumulator is an integer
    // multiple of 2**-266.  The 524-bit magnitudes below cover bit 0 at that
    // common exponent through the largest finite BF16 product at bit 521,
    // plus the carry needed by same-sign addition.  The packed return remains
    // {error[1:0], value}; a nonfinite input is error 1 and a finite exact sum
    // outside binary32 is error 2.
    function automatic [33:0] bf16_bf16_fp32_product_add_rne;
        input [31:0] accumulator_code;
        input [15:0] left_code;
        input [15:0] right_code;
        reg [1:0] error;
        reg [31:0] result;
        reg accumulator_sign;
        reg product_sign;
        reg result_sign;
        reg [7:0] accumulator_field;
        reg [7:0] left_field;
        reg [7:0] right_field;
        reg [23:0] accumulator_mantissa;
        reg [7:0] left_mantissa;
        reg [7:0] right_mantissa;
        reg [15:0] product_mantissa;
        reg [523:0] accumulator_magnitude;
        reg [523:0] product_magnitude;
        reg [523:0] exact_magnitude;
        reg [23:0] main_mantissa;
        reg [24:0] rounded_mantissa;
        reg round_bit;
        reg sticky;
        integer accumulator_power;
        integer left_power;
        integer right_power;
        integer accumulator_shift;
        integer product_shift;
        integer sum_msb;
        integer floor_exponent;
        integer shift_distance;
        integer bit_index;
        begin
            error = FP_ERR_NONE;
            result = 0;
            accumulator_sign = accumulator_code[31];
            product_sign = left_code[15] ^ right_code[15];
            result_sign = 0;
            accumulator_field = accumulator_code[30:23];
            left_field = left_code[14:7];
            right_field = right_code[14:7];
            accumulator_mantissa = accumulator_field == 0
                ? {1'b0, accumulator_code[22:0]}
                : {1'b1, accumulator_code[22:0]};
            left_mantissa = left_field == 0
                ? {1'b0, left_code[6:0]}
                : {1'b1, left_code[6:0]};
            right_mantissa = right_field == 0
                ? {1'b0, right_code[6:0]}
                : {1'b1, right_code[6:0]};
            product_mantissa = 0;
            accumulator_magnitude = 0;
            product_magnitude = 0;
            exact_magnitude = 0;
            main_mantissa = 0;
            rounded_mantissa = 0;
            round_bit = 0;
            sticky = 0;
            accumulator_power = 0;
            left_power = 0;
            right_power = 0;
            accumulator_shift = 0;
            product_shift = 0;
            sum_msb = -1;
            floor_exponent = 0;
            shift_distance = 0;

            if ((accumulator_field == 8'hff) ||
                (left_field == 8'hff) || (right_field == 8'hff)) begin
                error = FP_ERR_NONFINITE;
            end else begin
                // value = integer significand * 2**power.
                accumulator_power = accumulator_field == 0
                    ? -149 : ({24'b0, accumulator_field} - 150);
                left_power = left_field == 0
                    ? -133 : ({24'b0, left_field} - 134);
                right_power = right_field == 0
                    ? -133 : ({24'b0, right_field} - 134);
                accumulator_shift = accumulator_power + 266;
                product_shift = left_power + right_power + 266;
                product_mantissa = left_mantissa * right_mantissa;
                accumulator_magnitude =
                    {{500{1'b0}}, accumulator_mantissa} << accumulator_shift;
                product_magnitude =
                    {{508{1'b0}}, product_mantissa} << product_shift;

                if (accumulator_mantissa == 0) begin
                    exact_magnitude = product_magnitude;
                    result_sign = product_sign;
                end else if (product_mantissa == 0) begin
                    exact_magnitude = accumulator_magnitude;
                    result_sign = accumulator_sign;
                end else if (accumulator_sign == product_sign) begin
                    exact_magnitude = accumulator_magnitude + product_magnitude;
                    result_sign = accumulator_sign;
                end else if (accumulator_magnitude >= product_magnitude) begin
                    exact_magnitude = accumulator_magnitude - product_magnitude;
                    result_sign = accumulator_sign;
                end else begin
                    exact_magnitude = product_magnitude - accumulator_magnitude;
                    result_sign = product_sign;
                end

                for (bit_index = 0; bit_index < 524;
                     bit_index = bit_index + 1)
                    if (exact_magnitude[bit_index])
                        sum_msb = bit_index;

                if (sum_msb < 0) begin
                    result = 0;
                end else begin
                    floor_exponent = sum_msb - 266;
                    if (floor_exponent >= -126) begin
                        shift_distance = sum_msb - 23;
                        for (bit_index = 0; bit_index < 24;
                             bit_index = bit_index + 1)
                            if ((bit_index + shift_distance >= 0) &&
                                (bit_index + shift_distance < 524))
                                main_mantissa[bit_index] =
                                    exact_magnitude[bit_index + shift_distance];
                        if (shift_distance > 0)
                            round_bit = exact_magnitude[shift_distance-1];
                        for (bit_index = 0; bit_index < 524;
                             bit_index = bit_index + 1)
                            if (bit_index < shift_distance-1)
                                sticky = sticky | exact_magnitude[bit_index];
                        rounded_mantissa = {1'b0, main_mantissa};
                        if (round_bit && (sticky || main_mantissa[0]))
                            rounded_mantissa = rounded_mantissa + 1'b1;
                        if (rounded_mantissa[24]) begin
                            rounded_mantissa = rounded_mantissa >> 1;
                            floor_exponent = floor_exponent + 1;
                        end
                        if (floor_exponent > 127) begin
                            error = FP_ERR_OVERFLOW;
                            result = 0;
                        end else begin
                            result = {result_sign, 8'b0,
                                      rounded_mantissa[22:0]};
                            result[30:23] = floor_exponent + 127;
                        end
                    end else begin
                        // The shared unit is 2**-266 and the binary32
                        // subnormal unit is 2**-149, hence this fixed shift.
                        shift_distance = 117;
                        for (bit_index = 0; bit_index < 24;
                             bit_index = bit_index + 1)
                            main_mantissa[bit_index] =
                                exact_magnitude[bit_index + shift_distance];
                        round_bit = exact_magnitude[shift_distance-1];
                        // Constant loop bound with a guarded body, matching the
                        // sibling branch above.  A variable bound is not
                        // synthesizable -- Yosys rejects it outright, which
                        // stopped ot_a3_vector_compress_project and
                        // ot_a3_vector_index_score from elaborating at all.
                        // 524 is the width of exact_magnitude; the guard keeps
                        // the OR over exactly bits 0..shift_distance-2 as
                        // before.
                        for (bit_index = 0; bit_index < 524;
                             bit_index = bit_index + 1)
                            if (bit_index < shift_distance-1)
                                sticky = sticky | exact_magnitude[bit_index];
                        rounded_mantissa = {1'b0, main_mantissa};
                        if (round_bit && (sticky || main_mantissa[0]))
                            rounded_mantissa = rounded_mantissa + 1'b1;
                        if (rounded_mantissa >= 25'h0800000)
                            result = {result_sign, 8'h01, 23'b0};
                        else
                            result = {
                                result_sign, 8'h00,
                                rounded_mantissa[22:0]
                            };
                    end
                    if (result[30:0] == 0)
                        result = 0;
                end
            end
            bf16_bf16_fp32_product_add_rne = {error, result};
        end
    endfunction

    // Return {error[1:0], saturated, bf16_code}.  Finite binary32 values that
    // round beyond the BF16 finite range saturate as required by the target
    // contract; nonfinite binary32 input remains an error.
    function automatic [18:0] fp32_to_bf16_rne;
        input [31:0] code;
        reg [1:0] error;
        reg saturated;
        reg [15:0] rounded;
        reg [15:0] result;
        reg increment;
        begin
            error = FP_ERR_NONE;
            saturated = 1'b0;
            rounded = 0;
            result = 0;
            increment = 1'b0;
            if (code[30:23] == 8'hff) begin
                error = FP_ERR_NONFINITE;
            end else begin
                increment = (code[15:0] > 16'h8000) ||
                            ((code[15:0] == 16'h8000) && code[16]);
                rounded = code[31:16] + {15'b0, increment};
                result = rounded;
                if (result[14:7] == 8'hff) begin
                    result = {code[31], 8'hfe, 7'h7f};
                    saturated = 1'b1;
                end
                if (result[14:0] == 0)
                    result = 0;
            end
            fp32_to_bf16_rne = {error, saturated, result};
        end
    endfunction
endpackage
