`timescale 1ns/1ps
// Correctly rounded finite-positive binary32 reciprocal square root.  A binary
// search over positive finite encodings uses exact integer comparison of
// candidate^2 * argument against one, followed by the exact midpoint/ties-even
// decision.  This is a bounded correctness implementation, not a throughput-
// optimized arithmetic macro.
module ot_fp32_rsqrt_rne (
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

    reg busy;
    reg [31:0] low_code;
    reg [31:0] high_code;
    reg [31:0] lower_code;
    reg [23:0] argument_significand;
    integer argument_power;

    wire [31:0] candidate_code =
        low_code + ((high_code - low_code) >> 1);
    reg [24:0] candidate_significand;
    integer candidate_power;
    integer candidate_comparison;

    reg [31:0] upper_code;
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

    function automatic integer compare_square_product_to_one;
        input [24:0] significand;
        input integer value_power;
        input [23:0] arg_significand;
        input integer arg_power;
        reg [49:0] square;
        reg [73:0] product;
        integer product_msb;
        integer combined_power;
        integer bit_index;
        reg lower_bits;
        begin
            // Explicitly widen one operand at each multiply.  This preserves
            // every exact product bit under both IEEE expression-sizing
            // interpretations used by the supported simulators/synthesizers.
            square = {{25{1'b0}}, significand} * significand;
            product = {{24{1'b0}}, square} * arg_significand;
            product_msb = -1;
            lower_bits = 1'b0;
            for (bit_index = 0; bit_index < 74; bit_index = bit_index + 1)
                if (product[bit_index])
                    product_msb = bit_index;
            if (product_msb < 0) begin
                compare_square_product_to_one = -1;
            end else begin
                combined_power = product_msb +
                                 2 * value_power + arg_power;
                if (combined_power < 0) begin
                    compare_square_product_to_one = -1;
                end else if (combined_power > 0) begin
                    compare_square_product_to_one = 1;
                end else begin
                    for (bit_index = 0; bit_index < 74;
                         bit_index = bit_index + 1)
                        if (bit_index < product_msb)
                            lower_bits = lower_bits | product[bit_index];
                    compare_square_product_to_one = lower_bits ? 1 : 0;
                end
            end
        end
    endfunction

    task automatic decode_positive;
        input [30:0] code;
        output [24:0] significand;
        output integer value_power;
        begin
            if (code[30:23] == 0) begin
                significand = {2'b0, code[22:0]};
                value_power = -149;
            end else begin
                significand = {1'b0, 1'b1, code[22:0]};
                value_power = {24'b0, code[30:23]};
                value_power = value_power - 150;
            end
        end
    endtask

    always @* begin
        decode_positive(candidate_code[30:0], candidate_significand,
                        candidate_power);
        candidate_comparison = compare_square_product_to_one(
            candidate_significand,
            candidate_power,
            argument_significand,
            argument_power
        );

        upper_code = lower_code + 1'b1;
        decode_positive(lower_code[30:0], lower_significand, lower_power);
        decode_positive(upper_code[30:0], upper_significand, upper_power);
        common_power = lower_power < upper_power ? lower_power : upper_power;
        lower_aligned = lower_significand << (lower_power - common_power);
        upper_aligned = upper_significand << (upper_power - common_power);
        midpoint_significand = lower_aligned + upper_aligned;
        midpoint_power = common_power - 1;
        midpoint_comparison = compare_square_product_to_one(
            midpoint_significand,
            midpoint_power,
            argument_significand,
            argument_power
        );
    end

    assign in_ready = !busy && (!out_valid || out_ready);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0;
            low_code <= 0;
            high_code <= 0;
            lower_code <= 0;
            argument_significand <= 0;
            argument_power <= 0;
            out_valid <= 1'b0;
            result_code <= 0;
            result_error <= ERR_NONE;
        end else begin
            if (out_valid && out_ready)
                out_valid <= 1'b0;

            if (in_valid && in_ready) begin
                if (argument_code[31] || argument_code[30:23] == 8'hff ||
                    argument_code[30:0] == 0) begin
                    out_valid <= 1'b1;
                    result_code <= 0;
                    result_error <= ERR_ARGUMENT;
                end else begin
                    busy <= 1'b1;
                    low_code <= 0;
                    high_code <= 32'h7f7f_ffff;
                    lower_code <= 0;
                    if (argument_code[30:23] == 0) begin
                        argument_significand <= {1'b0, argument_code[22:0]};
                        argument_power <= -149;
                    end else begin
                        argument_significand <= {
                            1'b1, argument_code[22:0]
                        };
                        argument_power <=
                            {24'b0, argument_code[30:23]} - 32'd150;
                    end
                    result_error <= ERR_NONE;
                end
            end else if (busy) begin
                if (low_code <= high_code) begin
                    if (candidate_comparison <= 0) begin
                        lower_code <= candidate_code;
                        low_code <= candidate_code + 1'b1;
                    end else begin
                        high_code <= candidate_code - 1'b1;
                    end
                end else begin
                    busy <= 1'b0;
                    out_valid <= 1'b1;
                    result_error <= ERR_NONE;
                    if (lower_code == 32'h7f7f_ffff)
                        result_code <= lower_code;
                    else if (midpoint_comparison < 0)
                        result_code <= upper_code;
                    else if (midpoint_comparison > 0)
                        result_code <= lower_code;
                    else
                        result_code <= lower_code[0]
                                       ? upper_code : lower_code;
                end
            end
        end
    end
endmodule
