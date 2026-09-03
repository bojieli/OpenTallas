`timescale 1ns/1ps
// Reusable correctly-rounded finite IEEE-binary32 divider.
//
// The OpenTallas numeric contracts treat NaN, infinity, division by zero and
// a result that rounds beyond binary32 finite range as fail-closed errors.  All
// other finite inputs, including subnormals and signed zero, produce one
// round-to-nearest, ties-to-even result; zero is canonical positive zero.
//
// This bounded correctness implementation binary-searches the monotonically
// ordered positive finite encoding space.  Exact integer comparisons locate
// adjacent candidates around |numerator / denominator|.  A second exact
// comparison against their rational midpoint makes the RNE decision.  The
// virtual candidate immediately above 0x7f7fffff is 2**128, so the same
// midpoint rule detects the IEEE overflow-rounding boundary without ever
// representing infinity as an arithmetic operand.
module ot_a3_fp32_div_rne (
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
    localparam [1:0] ERR_NONE       = 2'd0;
    localparam [1:0] ERR_ARGUMENT   = 2'd1;
    localparam [1:0] ERR_OVERFLOW   = 2'd2;
    localparam [30:0] MAX_FINITE    = 31'h7f7f_ffff;

    reg busy;
    reg result_sign;
    reg [30:0] low_code;
    reg [30:0] high_code;
    reg [30:0] lower_code;
    reg [23:0] numerator_significand;
    reg [23:0] denominator_significand;
    integer numerator_power;
    integer denominator_power;

    wire [30:0] candidate_code =
        low_code + ((high_code - low_code) >> 1);
    reg [23:0] candidate_significand;
    integer candidate_power;
    integer candidate_comparison;

    reg [24:0] lower_significand;
    reg [24:0] upper_significand;
    integer lower_power;
    integer upper_power;
    integer common_power;
    reg [24:0] lower_aligned;
    reg [24:0] upper_aligned;
    reg [24:0] midpoint_significand;
    integer midpoint_power;
    integer midpoint_comparison;
    reg [30:0] rounded_magnitude;
    reg rounded_overflow;

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

    // Compare candidate * denominator with numerator exactly.  The return is
    // -1, 0 or +1.  Only when the top powers match do the integer magnitudes
    // need aligning; the required shift is then bounded by their significand
    // widths and the 97-bit work vectors retain every bit.
    function automatic integer compare_product_to_numerator;
        input [24:0] value_significand;
        input integer value_power;
        input [23:0] divisor_significand;
        input integer divisor_power;
        input [23:0] dividend_significand;
        input integer dividend_power;
        reg [48:0] product;
        reg [96:0] product_aligned;
        reg [96:0] dividend_aligned;
        integer product_lsb_power;
        integer product_msb;
        integer dividend_msb;
        integer product_top_power;
        integer dividend_top_power;
        integer align_distance;
        integer bit_index;
        begin
            product = 0;
            product_aligned = 0;
            dividend_aligned = 0;
            product_msb = -1;
            dividend_msb = -1;
            align_distance = 0;
            product_lsb_power = value_power + divisor_power;

            if (value_significand == 0 || divisor_significand == 0) begin
                compare_product_to_numerator =
                    dividend_significand == 0 ? 0 : -1;
            end else begin
                product = {{24{1'b0}}, value_significand} *
                          divisor_significand;
                for (bit_index = 0; bit_index < 49;
                     bit_index = bit_index + 1)
                    if (product[bit_index])
                        product_msb = bit_index;
                for (bit_index = 0; bit_index < 24;
                     bit_index = bit_index + 1)
                    if (dividend_significand[bit_index])
                        dividend_msb = bit_index;

                if (dividend_msb < 0) begin
                    compare_product_to_numerator = 1;
                end else begin
                    product_top_power = product_msb + product_lsb_power;
                    dividend_top_power = dividend_msb + dividend_power;
                    if (product_top_power < dividend_top_power) begin
                        compare_product_to_numerator = -1;
                    end else if (product_top_power > dividend_top_power) begin
                        compare_product_to_numerator = 1;
                    end else begin
                        product_aligned[48:0] = product;
                        dividend_aligned[23:0] = dividend_significand;
                        if (product_lsb_power < dividend_power) begin
                            align_distance = dividend_power - product_lsb_power;
                            dividend_aligned = dividend_aligned << align_distance;
                        end else if (dividend_power < product_lsb_power) begin
                            align_distance = product_lsb_power - dividend_power;
                            product_aligned = product_aligned << align_distance;
                        end
                        if (product_aligned < dividend_aligned)
                            compare_product_to_numerator = -1;
                        else if (product_aligned > dividend_aligned)
                            compare_product_to_numerator = 1;
                        else
                            compare_product_to_numerator = 0;
                    end
                end
            end
        end
    endfunction

    always @* begin
        decode_positive(candidate_code, candidate_significand,
                        candidate_power);
        candidate_comparison = compare_product_to_numerator(
            {1'b0, candidate_significand},
            candidate_power,
            denominator_significand,
            denominator_power,
            numerator_significand,
            numerator_power
        );

        decode_positive(lower_code, lower_significand[23:0], lower_power);
        lower_significand[24] = 1'b0;
        if (lower_code == MAX_FINITE) begin
            // The exact real candidate one ULP above max finite is 2**128.
            // Its midpoint with max finite is the RNE overflow boundary.
            upper_significand = 25'h1_000000;
            upper_power = 104;
        end else begin
            decode_positive(lower_code + 1'b1,
                            upper_significand[23:0], upper_power);
            upper_significand[24] = 1'b0;
        end
        common_power = lower_power < upper_power ? lower_power : upper_power;
        lower_aligned = lower_significand << (lower_power - common_power);
        upper_aligned = upper_significand << (upper_power - common_power);
        midpoint_significand = lower_aligned + upper_aligned;
        midpoint_power = common_power - 1;
        midpoint_comparison = compare_product_to_numerator(
            midpoint_significand,
            midpoint_power,
            denominator_significand,
            denominator_power,
            numerator_significand,
            numerator_power
        );

        rounded_magnitude = lower_code;
        rounded_overflow = 1'b0;
        if (midpoint_comparison < 0) begin
            if (lower_code == MAX_FINITE)
                rounded_overflow = 1'b1;
            else
                rounded_magnitude = lower_code + 1'b1;
        end else if (midpoint_comparison == 0 && lower_code[0]) begin
            if (lower_code == MAX_FINITE)
                rounded_overflow = 1'b1;
            else
                rounded_magnitude = lower_code + 1'b1;
        end
    end

    assign in_ready = !busy && (!out_valid || out_ready);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0;
            result_sign <= 1'b0;
            low_code <= 0;
            high_code <= 0;
            lower_code <= 0;
            numerator_significand <= 0;
            denominator_significand <= 0;
            numerator_power <= 0;
            denominator_power <= 0;
            out_valid <= 1'b0;
            result_code <= 0;
            result_error <= ERR_NONE;
        end else begin
            if (out_valid && out_ready)
                out_valid <= 1'b0;

            if (in_valid && in_ready) begin
                result_code <= 0;
                result_error <= ERR_NONE;
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
                    low_code <= 0;
                    high_code <= MAX_FINITE;
                    lower_code <= 0;
                    if (numerator_code[30:23] == 0) begin
                        numerator_significand <= {
                            1'b0, numerator_code[22:0]
                        };
                        numerator_power <= -149;
                    end else begin
                        numerator_significand <= {
                            1'b1, numerator_code[22:0]
                        };
                        numerator_power <=
                            {24'b0, numerator_code[30:23]} - 150;
                    end
                    if (denominator_code[30:23] == 0) begin
                        denominator_significand <= {
                            1'b0, denominator_code[22:0]
                        };
                        denominator_power <= -149;
                    end else begin
                        denominator_significand <= {
                            1'b1, denominator_code[22:0]
                        };
                        denominator_power <=
                            {24'b0, denominator_code[30:23]} - 150;
                    end
                end
            end else if (busy) begin
                if (low_code <= high_code) begin
                    if (candidate_comparison <= 0) begin
                        lower_code <= candidate_code;
                        if (candidate_code == MAX_FINITE)
                            low_code <= MAX_FINITE;
                        else
                            low_code <= candidate_code + 1'b1;
                        if (candidate_code == MAX_FINITE)
                            high_code <= MAX_FINITE - 1'b1;
                    end else begin
                        if (candidate_code == 0)
                            high_code <= 0;
                        else
                            high_code <= candidate_code - 1'b1;
                        if (candidate_code == 0)
                            low_code <= 1;
                    end
                end else begin
                    busy <= 1'b0;
                    out_valid <= 1'b1;
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
            end
        end
    end
endmodule
