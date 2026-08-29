`timescale 1ns/1ps
// Combinational finite-BF16 addition for the bf16_add_rne_v1 contract.
// Operands widen exactly, add through the binary32 boundary, and round once to
// BF16 with round-to-nearest, ties-to-even.  BF16 overflow saturates to the
// largest finite code and is reported; nonfinite input and binary32 arithmetic
// overflow fail closed.  Every zero result is canonical positive zero.
module ot_bf16_add_rne (
    input  wire [15:0] left_code,
    input  wire [15:0] right_code,
    output reg  [15:0] result_code,
    output reg         result_saturated,
    output reg  [1:0]  result_error
);
    localparam [1:0] ERR_NONE      = 2'd0;
    localparam [1:0] ERR_NONFINITE = 2'd1;
    localparam [1:0] ERR_OVERFLOW  = 2'd2;

    wire left_nonfinite = left_code[14:7] == 8'hff;
    wire right_nonfinite = right_code[14:7] == 8'hff;
    wire [7:0] left_mantissa = left_code[14:7] == 0
                               ? {1'b0, left_code[6:0]}
                               : {1'b1, left_code[6:0]};
    wire [7:0] right_mantissa = right_code[14:7] == 0
                                ? {1'b0, right_code[6:0]}
                                : {1'b1, right_code[6:0]};
    wire [7:0] left_exponent = left_code[14:7] == 0
                               ? 8'd1 : left_code[14:7];
    wire [7:0] right_exponent = right_code[14:7] == 0
                                ? 8'd1 : right_code[14:7];

    reg large_sign;
    reg small_sign;
    reg result_sign;
    reg [7:0] large_exponent;
    reg [7:0] small_exponent;
    reg [7:0] large_mantissa;
    reg [7:0] small_mantissa;
    reg [8:0] exponent_work;
    reg [8:0] rounded_mantissa;
    reg [11:0] large_extended;
    reg [11:0] small_extended;
    reg [11:0] arithmetic_extended;
    reg [11:0] normalized_extended;
    reg round_increment;
    integer normalization_step;

    function automatic [11:0] shift_right_jam;
        input [11:0] value;
        input [8:0] distance;
        integer bit_index;
        reg discarded;
        reg [11:0] shifted;
        begin
            discarded = 1'b0;
            shifted = 12'b0;
            if (distance == 0) begin
                shifted = value;
            end else if (distance >= 12) begin
                shifted = 12'b0;
                shifted[0] = |value;
            end else begin
                shifted = value >> distance;
                for (bit_index = 0; bit_index < 12; bit_index = bit_index + 1)
                    if (bit_index < distance)
                        discarded = discarded | value[bit_index];
                shifted[0] = shifted[0] | discarded;
            end
            shift_right_jam = shifted;
        end
    endfunction

    always @* begin
        result_code = 16'b0;
        result_saturated = 1'b0;
        result_error = ERR_NONE;
        large_sign = left_code[15];
        small_sign = right_code[15];
        large_exponent = left_exponent;
        small_exponent = right_exponent;
        large_mantissa = left_mantissa;
        small_mantissa = right_mantissa;
        result_sign = 1'b0;
        exponent_work = 9'b0;
        rounded_mantissa = 9'b0;
        large_extended = 12'b0;
        small_extended = 12'b0;
        arithmetic_extended = 12'b0;
        normalized_extended = 12'b0;
        round_increment = 1'b0;
        normalization_step = 0;

        if (left_nonfinite || right_nonfinite) begin
            result_error = ERR_NONFINITE;
        end else if ((left_mantissa == 0) && (right_mantissa == 0)) begin
            result_code = 16'b0;
        end else begin
            if ((right_exponent > left_exponent) ||
                ((right_exponent == left_exponent) &&
                 (right_mantissa > left_mantissa))) begin
                large_sign = right_code[15];
                small_sign = left_code[15];
                large_exponent = right_exponent;
                small_exponent = left_exponent;
                large_mantissa = right_mantissa;
                small_mantissa = left_mantissa;
            end
            result_sign = large_sign;
            exponent_work = {1'b0, large_exponent};
            large_extended = {1'b0, large_mantissa, 3'b000};
            small_extended = shift_right_jam(
                {1'b0, small_mantissa, 3'b000},
                {1'b0, large_exponent} - {1'b0, small_exponent}
            );
            if (large_sign == small_sign)
                arithmetic_extended = large_extended + small_extended;
            else
                arithmetic_extended = large_extended - small_extended;

            if (arithmetic_extended == 0) begin
                result_code = 16'b0;
            end else begin
                normalized_extended = arithmetic_extended;
                if (arithmetic_extended[11]) begin
                    normalized_extended = shift_right_jam(
                        arithmetic_extended, 9'd1
                    );
                    exponent_work = exponent_work + 1'b1;
                end else begin
                    for (normalization_step = 0;
                         normalization_step < 10;
                         normalization_step = normalization_step + 1) begin
                        if (!normalized_extended[10] && exponent_work > 1) begin
                            normalized_extended = normalized_extended << 1;
                            exponent_work = exponent_work - 1'b1;
                        end
                    end
                end

                if (exponent_work >= 9'd255) begin
                    // The exact BF16 sum has crossed the finite binary32 range.
                    result_error = ERR_OVERFLOW;
                    result_code = 16'b0;
                end else begin
                    rounded_mantissa = {1'b0, normalized_extended[10:3]};
                    round_increment = normalized_extended[2] &&
                                      ((|normalized_extended[1:0]) ||
                                       normalized_extended[3]);
                    if (round_increment)
                        rounded_mantissa = rounded_mantissa + 1'b1;
                    if (rounded_mantissa[8]) begin
                        rounded_mantissa = 9'd128;
                        exponent_work = exponent_work + 1'b1;
                    end

                    if (exponent_work >= 9'd255) begin
                        // Finite binary32 rounded beyond the finite BF16 range.
                        result_code = {result_sign, 8'hfe, 7'h7f};
                        result_saturated = 1'b1;
                    end else if ((exponent_work == 1) &&
                                 !rounded_mantissa[7]) begin
                        result_code = {
                            result_sign, 8'h00, rounded_mantissa[6:0]
                        };
                    end else begin
                        result_code = {
                            result_sign,
                            exponent_work[7:0],
                            rounded_mantissa[6:0]
                        };
                    end
                    if (result_code[14:0] == 0)
                        result_code = 16'b0;
                end
            end
        end
    end
endmodule
