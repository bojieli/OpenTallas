`timescale 1ns/1ps
// Atomic source-major 4x4 stable-softmax front end for DeepSeek HC_PRE.
//
// For each source row this block computes the exact frozen sequence:
//   shifted[i] = RN32(logit[i] - max(logit))
//   exp[i]     = CR32_EXP_NONPOS(shifted[i])
//   denom      = RN32(RN32(exp[0]+exp[1]) + RN32(exp[2]+exp[3]))
//   result[i]  = RN32(RN32(exp[i] / denom) + 0x358637bd)
//
// The exponential and divider are reusable certifying/exact blocks.  Every
// input and intermediate must remain finite, and max subtraction must remain
// nonpositive.  All sixteen results remain private until the complete matrix
// succeeds; a malformed input or arithmetic refusal returns an all-zero result
// and a nonzero error, never a partially updated architectural matrix.
module ot_a3_hc_stable_softmax_rne (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         in_valid,
    output wire         in_ready,
    input  wire [511:0] matrix_codes,
    output reg          out_valid,
    input  wire         out_ready,
    output reg  [511:0] result_codes,
    output reg  [1:0]   result_error
);
    localparam [31:0] HC_EPSILON = 32'h3586_37bd;
    localparam [1:0] ERR_NONE = 2'd0;
    localparam [1:0] ERR_ARGUMENT = 2'd1;

    localparam [3:0] S_IDLE      = 4'd0;
    localparam [3:0] S_MAX       = 4'd1;
    localparam [3:0] S_SHIFT     = 4'd2;
    localparam [3:0] S_EXP_ISSUE = 4'd3;
    localparam [3:0] S_EXP_WAIT  = 4'd4;
    localparam [3:0] S_SUM       = 4'd5;
    localparam [3:0] S_DIV_ISSUE = 4'd6;
    localparam [3:0] S_DIV_WAIT  = 4'd7;
    localparam [3:0] S_EPSILON   = 4'd8;
    localparam [3:0] S_PACK      = 4'd9;
    localparam [3:0] S_OUT       = 4'd10;

    reg [3:0] state;
    reg [1:0] row_index;
    reg [1:0] element_index;
    reg [31:0] matrix [0:15];
    reg [31:0] exponentials [0:3];
    reg [31:0] output_matrix [0:15];
    reg [31:0] maximum_code;
    reg [31:0] shifted_code;
    reg [31:0] denominator_code;
    reg [31:0] quotient_code;

    integer load_index;
    integer sequential_index;
    integer max_index;
    reg input_invalid;
    reg [3:0] selected_index;
    reg [31:0] row_maximum;
    reg [31:0] negative_maximum;
    reg [33:0] shifted_add;
    reg [33:0] pair_01;
    reg [33:0] pair_23;
    reg [33:0] pair_total;
    reg [1:0] sum_error;
    reg [33:0] epsilon_add;

    function automatic [31:0] canonical_zero;
        input [31:0] code;
        begin
            canonical_zero = code[30:0] == 0 ? 32'b0 : code;
        end
    endfunction

    function automatic [31:0] order_key;
        input [31:0] code;
        reg [31:0] canonical;
        begin
            canonical = canonical_zero(code);
            order_key = canonical[31]
                ? ~canonical : (canonical | 32'h8000_0000);
        end
    endfunction

    function automatic [31:0] maximum;
        input [31:0] left;
        input [31:0] right;
        reg [31:0] left_canonical;
        reg [31:0] right_canonical;
        begin
            left_canonical = canonical_zero(left);
            right_canonical = canonical_zero(right);
            maximum = order_key(left_canonical) >= order_key(right_canonical)
                ? left_canonical : right_canonical;
        end
    endfunction

    always @* begin
        input_invalid = 1'b0;
        for (load_index = 0; load_index < 16;
             load_index = load_index + 1)
            if (matrix_codes[32*load_index + 30 -: 8] == 8'hff)
                input_invalid = 1'b1;

        selected_index = {row_index, 2'b00} + {2'b0, element_index};
        row_maximum = matrix[{row_index, 2'b00}];
        for (max_index = 1; max_index < 4; max_index = max_index + 1)
            row_maximum = maximum(
                row_maximum,
                matrix[{28'b0, row_index, 2'b00} + max_index]
            );

        negative_maximum = maximum_code[30:0] == 0
            ? 32'b0 : {~maximum_code[31], maximum_code[30:0]};
        shifted_add = ot_fp32_rne_pkg::fp32_add_rne(
            matrix[selected_index], negative_maximum
        );

        pair_01 = ot_fp32_rne_pkg::fp32_add_positive_rne(
            exponentials[0], exponentials[1]
        );
        pair_23 = ot_fp32_rne_pkg::fp32_add_positive_rne(
            exponentials[2], exponentials[3]
        );
        pair_total = ot_fp32_rne_pkg::fp32_add_positive_rne(
            pair_01[31:0], pair_23[31:0]
        );
        sum_error = pair_01[33:32] | pair_23[33:32] |
                    pair_total[33:32];

        epsilon_add = ot_fp32_rne_pkg::fp32_add_positive_rne(
            quotient_code, HC_EPSILON
        );
    end

    wire exp_in_valid = state == S_EXP_ISSUE;
    wire exp_in_ready;
    wire exp_out_valid;
    wire [31:0] exp_result_code;
    wire [1:0] exp_result_error;

    ot_a3_fp32_transcendental_cr_rne exponential (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(exp_in_valid),
        .in_ready(exp_in_ready),
        .operation(1'b0),
        .argument_code(shifted_code),
        .out_valid(exp_out_valid),
        .out_ready(state == S_EXP_WAIT),
        .result_code(exp_result_code),
        .result_error(exp_result_error)
    );

    wire div_in_valid = state == S_DIV_ISSUE;
    wire div_in_ready;
    wire div_out_valid;
    wire [31:0] div_result_code;
    wire [1:0] div_result_error;

    ot_a3_fp32_div_rne divider (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(div_in_valid),
        .in_ready(div_in_ready),
        .numerator_code(exponentials[element_index]),
        .denominator_code(denominator_code),
        .out_valid(div_out_valid),
        .out_ready(state == S_DIV_WAIT),
        .result_code(div_result_code),
        .result_error(div_result_error)
    );

    assign in_ready = state == S_IDLE && !out_valid;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            row_index <= 0;
            element_index <= 0;
            maximum_code <= 0;
            shifted_code <= 0;
            denominator_code <= 0;
            quotient_code <= 0;
            out_valid <= 1'b0;
            result_codes <= 0;
            result_error <= ERR_NONE;
            for (sequential_index = 0; sequential_index < 16;
                 sequential_index = sequential_index + 1) begin
                matrix[sequential_index] <= 0;
                output_matrix[sequential_index] <= 0;
            end
            for (sequential_index = 0; sequential_index < 4;
                 sequential_index = sequential_index + 1)
                exponentials[sequential_index] <= 0;
        end else begin
            case (state)
                S_IDLE: begin
                    if (in_valid && in_ready) begin
                        result_codes <= 0;
                        result_error <= ERR_NONE;
                        row_index <= 0;
                        element_index <= 0;
                        if (input_invalid) begin
                            result_error <= ERR_ARGUMENT;
                            out_valid <= 1'b1;
                            state <= S_OUT;
                        end else begin
                            for (sequential_index = 0; sequential_index < 16;
                                 sequential_index = sequential_index + 1) begin
                                matrix[sequential_index] <= canonical_zero(
                                    matrix_codes[32*sequential_index +: 32]
                                );
                                output_matrix[sequential_index] <= 0;
                            end
                            state <= S_MAX;
                        end
                    end
                end

                S_MAX: begin
                    maximum_code <= row_maximum;
                    element_index <= 0;
                    state <= S_SHIFT;
                end

                S_SHIFT: begin
                    if (shifted_add[33:32] != ERR_NONE ||
                        (!shifted_add[31] && shifted_add[30:0] != 0)) begin
                        result_codes <= 0;
                        result_error <= shifted_add[33:32] != ERR_NONE
                            ? shifted_add[33:32] : ERR_ARGUMENT;
                        out_valid <= 1'b1;
                        state <= S_OUT;
                    end else begin
                        shifted_code <= canonical_zero(shifted_add[31:0]);
                        state <= S_EXP_ISSUE;
                    end
                end

                S_EXP_ISSUE: begin
                    if (exp_in_ready)
                        state <= S_EXP_WAIT;
                end

                S_EXP_WAIT: begin
                    if (exp_out_valid) begin
                        if (exp_result_error != ERR_NONE ||
                            exp_result_code[31] ||
                            exp_result_code[30:23] == 8'hff) begin
                            result_codes <= 0;
                            result_error <= exp_result_error != ERR_NONE
                                ? exp_result_error : ERR_ARGUMENT;
                            out_valid <= 1'b1;
                            state <= S_OUT;
                        end else begin
                            exponentials[element_index] <= exp_result_code;
                            if (element_index != 3) begin
                                element_index <= element_index + 1'b1;
                                state <= S_SHIFT;
                            end else begin
                                state <= S_SUM;
                            end
                        end
                    end
                end

                S_SUM: begin
                    if (sum_error != ERR_NONE ||
                        pair_total[31] || pair_total[30:0] == 0) begin
                        result_codes <= 0;
                        result_error <= sum_error != ERR_NONE
                            ? sum_error : ERR_ARGUMENT;
                        out_valid <= 1'b1;
                        state <= S_OUT;
                    end else begin
                        denominator_code <= pair_total[31:0];
                        element_index <= 0;
                        state <= S_DIV_ISSUE;
                    end
                end

                S_DIV_ISSUE: begin
                    if (div_in_ready)
                        state <= S_DIV_WAIT;
                end

                S_DIV_WAIT: begin
                    if (div_out_valid) begin
                        if (div_result_error != ERR_NONE ||
                            div_result_code[31] ||
                            div_result_code[30:23] == 8'hff) begin
                            result_codes <= 0;
                            result_error <= div_result_error != ERR_NONE
                                ? div_result_error : ERR_ARGUMENT;
                            out_valid <= 1'b1;
                            state <= S_OUT;
                        end else begin
                            quotient_code <= div_result_code;
                            state <= S_EPSILON;
                        end
                    end
                end

                S_EPSILON: begin
                    if (epsilon_add[33:32] != ERR_NONE) begin
                        result_codes <= 0;
                        result_error <= epsilon_add[33:32];
                        out_valid <= 1'b1;
                        state <= S_OUT;
                    end else begin
                        output_matrix[selected_index] <= epsilon_add[31:0];
                        if (element_index != 3) begin
                            element_index <= element_index + 1'b1;
                            state <= S_DIV_ISSUE;
                        end else if (row_index != 3) begin
                            row_index <= row_index + 1'b1;
                            element_index <= 0;
                            state <= S_MAX;
                        end else begin
                            state <= S_PACK;
                        end
                    end
                end

                S_PACK: begin
                    for (sequential_index = 0; sequential_index < 16;
                         sequential_index = sequential_index + 1)
                        result_codes[32*sequential_index +: 32] <=
                            output_matrix[sequential_index];
                    result_error <= ERR_NONE;
                    out_valid <= 1'b1;
                    state <= S_OUT;
                end

                S_OUT: begin
                    if (out_valid && out_ready) begin
                        out_valid <= 1'b0;
                        state <= S_IDLE;
                    end
                end

                default: begin
                    result_codes <= 0;
                    result_error <= ERR_ARGUMENT;
                    out_valid <= 1'b1;
                    state <= S_OUT;
                end
            endcase
        end
    end
endmodule
