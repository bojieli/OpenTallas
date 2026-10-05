`timescale 1ns/1ps
// Exact arithmetic unique to DeepSeek HC_PRE projection.
//
// The projection contract widens a finite BF16 activation exactly, multiplies
// it by a finite binary32 coefficient, adds the exact product to a finite
// binary32 accumulator, and rounds the sum once to binary32 RNE.  This is not
// the same operation as a separately rounded multiply followed by an add.
package ot_a3_hc_projection_pkg;
    localparam [1:0] FP_ERR_NONE      = 2'd0;
    localparam [1:0] FP_ERR_NONFINITE = 2'd1;
    localparam [1:0] FP_ERR_OVERFLOW  = 2'd2;

    // Return {error[1:0], binary32_result[31:0]}.
    //
    // All finite inputs can be represented as integer multiples of 2**-282:
    // BF16's least unit is 2**-133 and binary32's is 2**-149.  A 540-bit
    // magnitude covers that common unit through the largest finite BF16*FP32
    // product (top bit 537), with guard capacity.  The exact signed addition
    // is performed before the one binary32 RNE boundary.
    function automatic [33:0] bf16_fp32_fp32_product_add_rne;
        input [31:0] accumulator_code;
        input [15:0] activation_code;
        input [31:0] weight_code;
        reg [1:0] error;
        reg [31:0] result;
        reg accumulator_sign;
        reg product_sign;
        reg result_sign;
        reg [7:0] accumulator_field;
        reg [7:0] activation_field;
        reg [7:0] weight_field;
        reg [23:0] accumulator_mantissa;
        reg [7:0] activation_mantissa;
        reg [23:0] weight_mantissa;
        reg [31:0] product_mantissa;
        reg [539:0] accumulator_magnitude;
        reg [539:0] product_magnitude;
        reg [539:0] exact_magnitude;
        reg [539:0] sticky_mask;
        reg [1023:0] magnitude_search;
        reg [23:0] main_mantissa;
        reg [24:0] rounded_mantissa;
        reg round_bit;
        reg sticky;
        integer accumulator_power;
        integer activation_power;
        integer weight_power;
        integer accumulator_shift;
        integer product_shift;
        integer sum_msb;
        integer floor_exponent;
        integer shift_distance;
        integer search_offset;
        integer bit_index;
        begin
            error = FP_ERR_NONE;
            result = 0;
            accumulator_sign = accumulator_code[31];
            product_sign = activation_code[15] ^ weight_code[31];
            result_sign = 0;
            accumulator_field = accumulator_code[30:23];
            activation_field = activation_code[14:7];
            weight_field = weight_code[30:23];
            accumulator_mantissa = accumulator_field == 0
                ? {1'b0, accumulator_code[22:0]}
                : {1'b1, accumulator_code[22:0]};
            activation_mantissa = activation_field == 0
                ? {1'b0, activation_code[6:0]}
                : {1'b1, activation_code[6:0]};
            weight_mantissa = weight_field == 0
                ? {1'b0, weight_code[22:0]}
                : {1'b1, weight_code[22:0]};
            product_mantissa = 0;
            accumulator_magnitude = 0;
            product_magnitude = 0;
            exact_magnitude = 0;
            sticky_mask = 0;
            magnitude_search = 0;
            main_mantissa = 0;
            rounded_mantissa = 0;
            round_bit = 0;
            sticky = 0;
            accumulator_power = 0;
            activation_power = 0;
            weight_power = 0;
            accumulator_shift = 0;
            product_shift = 0;
            sum_msb = -1;
            floor_exponent = 0;
            shift_distance = 0;
            search_offset = 0;

            if ((accumulator_field == 8'hff) ||
                (activation_field == 8'hff) ||
                (weight_field == 8'hff)) begin
                error = FP_ERR_NONFINITE;
            end else begin
                // value = signed integer significand * 2**power.
                accumulator_power = accumulator_field == 0
                    ? -149 : ({24'b0, accumulator_field} - 150);
                activation_power = activation_field == 0
                    ? -133 : ({24'b0, activation_field} - 134);
                weight_power = weight_field == 0
                    ? -149 : ({24'b0, weight_field} - 150);
                accumulator_shift = accumulator_power + 282;
                product_shift = activation_power + weight_power + 282;
                product_mantissa =
                    {{24{1'b0}}, activation_mantissa} * weight_mantissa;
                accumulator_magnitude =
                    {{516{1'b0}}, accumulator_mantissa} << accumulator_shift;
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

                // A ten-step leading-one search replaces a 540-iteration
                // scan.  The selected upper half is shifted into the low
                // half after each decision, while search_offset retains its
                // original bit position.  This is an ordinary priority
                // encoder, not a numeric approximation.
                if (exact_magnitude != 0) begin
                    magnitude_search = {{484{1'b0}}, exact_magnitude};
                    if (|magnitude_search[1023:512]) begin
                        magnitude_search = magnitude_search >> 512;
                        search_offset = search_offset + 512;
                    end
                    if (|magnitude_search[511:256]) begin
                        magnitude_search = magnitude_search >> 256;
                        search_offset = search_offset + 256;
                    end
                    if (|magnitude_search[255:128]) begin
                        magnitude_search = magnitude_search >> 128;
                        search_offset = search_offset + 128;
                    end
                    if (|magnitude_search[127:64]) begin
                        magnitude_search = magnitude_search >> 64;
                        search_offset = search_offset + 64;
                    end
                    if (|magnitude_search[63:32]) begin
                        magnitude_search = magnitude_search >> 32;
                        search_offset = search_offset + 32;
                    end
                    if (|magnitude_search[31:16]) begin
                        magnitude_search = magnitude_search >> 16;
                        search_offset = search_offset + 16;
                    end
                    if (|magnitude_search[15:8]) begin
                        magnitude_search = magnitude_search >> 8;
                        search_offset = search_offset + 8;
                    end
                    if (|magnitude_search[7:4]) begin
                        magnitude_search = magnitude_search >> 4;
                        search_offset = search_offset + 4;
                    end
                    if (|magnitude_search[3:2]) begin
                        magnitude_search = magnitude_search >> 2;
                        search_offset = search_offset + 2;
                    end
                    if (magnitude_search[1])
                        search_offset = search_offset + 1;
                    sum_msb = search_offset;
                end

                if (sum_msb < 0) begin
                    result = 0;
                end else begin
                    floor_exponent = sum_msb - 282;
                    if (floor_exponent >= -126) begin
                        shift_distance = sum_msb - 23;
                        for (bit_index = 0; bit_index < 24;
                             bit_index = bit_index + 1)
                            if ((bit_index + shift_distance >= 0) &&
                                (bit_index + shift_distance < 540))
                                main_mantissa[bit_index] =
                                    exact_magnitude[bit_index + shift_distance];
                        if (shift_distance > 0)
                            round_bit = exact_magnitude[shift_distance-1];
                        if (shift_distance > 1) begin
                            sticky_mask = {540{1'b1}} >>
                                (540 - (shift_distance - 1));
                            sticky = |(exact_magnitude & sticky_mask);
                        end
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
                        // Binary32's subnormal unit is 2**-149, 133 places
                        // above the common 2**-282 exact-product unit.
                        shift_distance = 133;
                        main_mantissa = exact_magnitude[156:133];
                        round_bit = exact_magnitude[shift_distance-1];
                        sticky = |exact_magnitude[131:0];
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
            bf16_fp32_fp32_product_add_rne = {error, result};
        end
    endfunction
endpackage
