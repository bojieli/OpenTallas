`timescale 1ns/1ps
// Atomic one-token DeepSeek HC_PRE coefficient tail.
//
// Twenty-four normalized projection values undergo the frozen, separately
// rounded affine multiply/add.  Fields 0..3 become sigmoid(x)+epsilon, fields
// 4..7 become 2*sigmoid(x), and source-major fields 8..23 feed the qualified
// stable-softmax/Sinkhorn-20 composition.  No affine or nonlinear intermediate
// is externally visible, and any child refusal publishes all-zero outputs.
module ot_a3_hc_coefficients_rne (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         in_valid,
    output wire         in_ready,
    input  wire [767:0] normalized_projection_codes,
    input  wire [767:0] base_codes,
    input  wire [95:0]  scale_codes,
    output reg          out_valid,
    input  wire         out_ready,
    output reg  [255:0] weight_codes,
    output reg  [511:0] combination_codes,
    output reg  [1:0]   result_error,
    output reg  [31:0]  affine_count,
    output reg  [31:0]  sigmoid_count
);
    localparam [1:0] FP_ERR_NONE = 2'd0;
    localparam [1:0] FP_ERR_ARGUMENT = 2'd1;
    localparam [31:0] EPSILON_CODE = 32'h3586_37bd;
    localparam [31:0] TWO_CODE = 32'h4000_0000;

    localparam [3:0] S_IDLE          = 4'd0;
    localparam [3:0] S_AFFINE        = 4'd1;
    localparam [3:0] S_SIG_ISSUE     = 4'd2;
    localparam [3:0] S_SIG_WAIT      = 4'd3;
    localparam [3:0] S_COMB_ISSUE    = 4'd4;
    localparam [3:0] S_COMB_WAIT     = 4'd5;
    localparam [3:0] S_PUBLISH       = 4'd6;
    localparam [3:0] S_OUT           = 4'd7;

    reg [3:0] state;
    reg [4:0] field_index;
    reg [767:0] normalized_q;
    reg [767:0] base_q;
    reg [95:0] scale_q;
    reg [31:0] affine_q;
    reg [31:0] pre_private [0:3];
    reg [31:0] post_private [0:3];
    reg [31:0] combination_input_private [0:15];
    reg [511:0] combination_private;
    integer item;

    wire [31:0] current_normalized =
        normalized_q[32*field_index +: 32];
    wire [31:0] current_base = base_q[32*field_index +: 32];
    wire [1:0] scale_index = field_index < 4 ? 0 :
                             field_index < 8 ? 1 : 2;
    wire [31:0] current_scale = scale_q[32*scale_index +: 32];
    wire [33:0] affine_product = ot_fp32_rne_pkg::fp32_mul_rne(
        current_normalized, current_scale
    );
    wire [33:0] affine_sum = ot_fp32_rne_pkg::fp32_add_rne(
        affine_product[31:0], current_base
    );

    wire sigmoid_in_valid = state == S_SIG_ISSUE;
    wire sigmoid_in_ready;
    wire sigmoid_out_valid;
    wire [31:0] sigmoid_result_code;
    wire [1:0] sigmoid_result_error;
    ot_a3_fp32_transcendental_cr_rne sigmoid (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(sigmoid_in_valid),
        .in_ready(sigmoid_in_ready),
        .operation(1'b1),
        .argument_code(affine_q),
        .out_valid(sigmoid_out_valid),
        .out_ready(state == S_SIG_WAIT),
        .result_code(sigmoid_result_code),
        .result_error(sigmoid_result_error)
    );

    wire [33:0] pre_epsilon = ot_fp32_rne_pkg::fp32_add_positive_rne(
        sigmoid_result_code, EPSILON_CODE
    );
    wire [33:0] post_factor = ot_fp32_rne_pkg::fp32_mul_rne(
        TWO_CODE, sigmoid_result_code
    );

    reg [511:0] combination_input;
    always @* begin
        combination_input = 0;
        for (item = 0; item < 16; item = item + 1)
            combination_input[32*item +: 32] =
                combination_input_private[item];
    end

    wire combination_in_valid = state == S_COMB_ISSUE;
    wire combination_in_ready;
    wire combination_out_valid;
    wire [511:0] combination_result_codes;
    wire [1:0] combination_result_error;
    ot_a3_hc_stable_softmax_sinkhorn20_rne combination (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(combination_in_valid),
        .in_ready(combination_in_ready),
        .matrix_codes(combination_input),
        .out_valid(combination_out_valid),
        .out_ready(state == S_COMB_WAIT),
        .result_codes(combination_result_codes),
        .result_error(combination_result_error)
    );

    assign in_ready = state == S_IDLE && !out_valid;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            field_index <= 0;
            normalized_q <= 0;
            base_q <= 0;
            scale_q <= 0;
            affine_q <= 0;
            combination_private <= 0;
            out_valid <= 1'b0;
            weight_codes <= 0;
            combination_codes <= 0;
            result_error <= FP_ERR_NONE;
            affine_count <= 0;
            sigmoid_count <= 0;
            for (item = 0; item < 4; item = item + 1) begin
                pre_private[item] <= 0;
                post_private[item] <= 0;
            end
            for (item = 0; item < 16; item = item + 1)
                combination_input_private[item] <= 0;
        end else begin
            case (state)
                S_IDLE: begin
                    if (in_valid && in_ready) begin
                        normalized_q <= normalized_projection_codes;
                        base_q <= base_codes;
                        scale_q <= scale_codes;
                        field_index <= 0;
                        affine_q <= 0;
                        combination_private <= 0;
                        out_valid <= 1'b0;
                        weight_codes <= 0;
                        combination_codes <= 0;
                        result_error <= FP_ERR_NONE;
                        affine_count <= 0;
                        sigmoid_count <= 0;
                        for (item = 0; item < 4; item = item + 1) begin
                            pre_private[item] <= 0;
                            post_private[item] <= 0;
                        end
                        for (item = 0; item < 16; item = item + 1)
                            combination_input_private[item] <= 0;
                        state <= S_AFFINE;
                    end
                end

                S_AFFINE: begin
                    if (affine_product[33:32] != FP_ERR_NONE) begin
                        result_error <= affine_product[33:32];
                        out_valid <= 1'b1;
                        state <= S_OUT;
                    end else if (affine_sum[33:32] != FP_ERR_NONE) begin
                        result_error <= affine_sum[33:32];
                        out_valid <= 1'b1;
                        state <= S_OUT;
                    end else begin
                        affine_count <= affine_count + 1'b1;
                        if (field_index < 8) begin
                            affine_q <= affine_sum[31:0];
                            state <= S_SIG_ISSUE;
                        end else begin
                            combination_input_private[field_index - 8] <=
                                affine_sum[31:0];
                            if (field_index == 23)
                                state <= S_COMB_ISSUE;
                            else begin
                                field_index <= field_index + 1'b1;
                                state <= S_AFFINE;
                            end
                        end
                    end
                end

                S_SIG_ISSUE: begin
                    if (sigmoid_in_ready)
                        state <= S_SIG_WAIT;
                end

                S_SIG_WAIT: begin
                    if (sigmoid_out_valid) begin
                        if (sigmoid_result_error != FP_ERR_NONE) begin
                            result_error <= sigmoid_result_error;
                            out_valid <= 1'b1;
                            state <= S_OUT;
                        end else if (field_index < 4 &&
                                     pre_epsilon[33:32] != FP_ERR_NONE) begin
                            result_error <= pre_epsilon[33:32];
                            out_valid <= 1'b1;
                            state <= S_OUT;
                        end else if (field_index >= 4 &&
                                     post_factor[33:32] != FP_ERR_NONE) begin
                            result_error <= post_factor[33:32];
                            out_valid <= 1'b1;
                            state <= S_OUT;
                        end else begin
                            sigmoid_count <= sigmoid_count + 1'b1;
                            if (field_index < 4)
                                pre_private[field_index] <=
                                    pre_epsilon[31:0];
                            else
                                post_private[field_index - 4] <=
                                    post_factor[31:0];
                            field_index <= field_index + 1'b1;
                            state <= S_AFFINE;
                        end
                    end
                end

                S_COMB_ISSUE: begin
                    if (combination_in_ready)
                        state <= S_COMB_WAIT;
                end

                S_COMB_WAIT: begin
                    if (combination_out_valid) begin
                        if (combination_result_error != FP_ERR_NONE) begin
                            result_error <= combination_result_error;
                            out_valid <= 1'b1;
                            state <= S_OUT;
                        end else begin
                            combination_private <= combination_result_codes;
                            state <= S_PUBLISH;
                        end
                    end
                end

                S_PUBLISH: begin
                    for (item = 0; item < 4; item = item + 1) begin
                        weight_codes[32*item +: 32] <= pre_private[item];
                        weight_codes[32*(item+4) +: 32] <= post_private[item];
                    end
                    combination_codes <= combination_private;
                    result_error <= FP_ERR_NONE;
                    out_valid <= 1'b1;
                    state <= S_OUT;
                end

                S_OUT: begin
                    if (out_valid && out_ready) begin
                        out_valid <= 1'b0;
                        weight_codes <= 0;
                        combination_codes <= 0;
                        result_error <= FP_ERR_NONE;
                        state <= S_IDLE;
                    end
                end

                default: begin
                    weight_codes <= 0;
                    combination_codes <= 0;
                    result_error <= FP_ERR_ARGUMENT;
                    out_valid <= 1'b1;
                    state <= S_OUT;
                end
            endcase
        end
    end
endmodule
