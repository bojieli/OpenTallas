`timescale 1ns/1ps
// Two-read/one-write scratch used by the balanced RMS reduction.  Keep the
// storage outside the resettable controller process so synthesis can preserve
// it as a memory instead of expanding 16,384 words into reset-process flops.
// Every successful transaction overwrites all words before the first read, so
// the scratch intentionally has no reset or initialization semantics.
module ot_a3_hc_reduction_store (
    input  wire        clk,
    input  wire        write_enable,
    input  wire [13:0] write_address,
    input  wire [31:0] write_data,
    input  wire [13:0] read_address_a,
    input  wire [13:0] read_address_b,
    output wire [31:0] read_data_a,
    output wire [31:0] read_data_b
);
    reg [31:0] memory [0:16383];

    always @(posedge clk) begin
        if (write_enable)
            memory[write_address] <= write_data;
    end

    assign read_data_a = memory[read_address_a];
    assign read_data_b = memory[read_address_b];
endmodule

// Atomic one-token DeepSeek HC_PRE normalization and projection datapath.
//
// The fixed production geometry is [4,4096] BF16 flattened to K=16384 and a
// [24,16384] FP32 projection.  RMS squares are reduced by the frozen balanced
// binary tree, followed by a separate power-of-two mean multiply, epsilon add,
// and the shared correctly rounded reciprocal square root.  Projection rows
// use eight physical field lanes and retain one accumulator per row across all
// increasing-K steps.  Each step is the exact BF16*FP32 fused product-add from
// ot_a3_hc_projection_pkg, with one binary32 RNE boundary.
//
// All diagnostic outputs are private/zero until the complete transaction has
// succeeded.  A nonfinite operand or finite overflow publishes only an error
// and all-zero results.  Controller cycles are verification metadata, not
// architectural token latency or TPOT.
module ot_a3_hc_projection_rms_rne (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         in_valid,
    output wire         in_ready,

    output reg          hidden_rd_en,
    output reg  [13:0]  hidden_rd_k,
    input  wire [15:0]  hidden_rd_data,
    output reg          weight_rd_en,
    output reg  [4:0]   weight_rd_field_base,
    output reg  [13:0]  weight_rd_k,
    input  wire [255:0] weight_rd_data,

    output reg          out_valid,
    input  wire         out_ready,
    output reg  [31:0]  mean_square_code,
    output reg  [31:0]  inverse_rms_code,
    output reg  [767:0] projection_codes,
    output reg  [767:0] normalized_projection_codes,
    output reg  [1:0]   result_error,
    output reg  [31:0]  square_count,
    output reg  [31:0]  reduction_add_count,
    output reg  [31:0]  fused_product_add_count
);
    localparam [1:0] FP_ERR_NONE = 2'd0;
    localparam [1:0] FP_ERR_ARGUMENT = 2'd1;
    localparam [1:0] FP_ERR_OVERFLOW = 2'd2;
    localparam integer WIDTH = 16384;
    localparam integer FIELDS = 24;
    localparam integer LANES = 8;
    localparam [31:0] MEAN_SCALE_CODE = 32'h3880_0000; // 2^-14 = 1/16384
    localparam [31:0] EPSILON_CODE = 32'h3586_37bd;

    localparam [3:0] S_IDLE          = 4'd0;
    localparam [3:0] S_RMS_ISSUE     = 4'd1;
    localparam [3:0] S_RMS_WAIT      = 4'd2;
    localparam [3:0] S_RMS_ACCEPT    = 4'd3;
    localparam [3:0] S_REDUCE        = 4'd4;
    localparam [3:0] S_MEAN          = 4'd5;
    localparam [3:0] S_EPSILON       = 4'd6;
    localparam [3:0] S_RSQRT_ISSUE   = 4'd7;
    localparam [3:0] S_RSQRT_WAIT    = 4'd8;
    localparam [3:0] S_PROJ_ISSUE    = 4'd9;
    localparam [3:0] S_PROJ_WAIT     = 4'd10;
    localparam [3:0] S_PROJ_ACCEPT   = 4'd11;
    localparam [3:0] S_PUBLISH       = 4'd12;
    localparam [3:0] S_OUT           = 4'd13;

    reg [3:0] state;
    reg [31:0] projection_accumulator [0:FIELDS-1];
    reg [31:0] projection_private [0:FIELDS-1];
    reg [31:0] normalized_private [0:FIELDS-1];
    reg [31:0] mean_private;
    reg [31:0] inverse_private;
    reg [13:0] k_index;
    reg [4:0] field_base;
    reg [13:0] reduction_pair_index;
    reg [14:0] reduction_count;
    integer item;

    wire [31:0] hidden_fp32 = {hidden_rd_data, 16'b0};
    wire [33:0] input_square = ot_fp32_rne_pkg::fp32_mul_rne(
        hidden_fp32, hidden_fp32
    );
    wire [14:0] reduction_left_index =
        {1'b0, reduction_pair_index} << 1;
    wire [14:0] reduction_right_index = reduction_left_index + 1'b1;
    wire [13:0] reduction_read_address_a = state == S_REDUCE
        ? reduction_left_index[13:0] : 14'b0;
    wire [13:0] reduction_read_address_b = state == S_REDUCE
        ? reduction_right_index[13:0] : 14'b0;
    wire [31:0] reduction_read_data_a;
    wire [31:0] reduction_read_data_b;
    wire [33:0] reduction_add = ot_fp32_rne_pkg::fp32_add_positive_rne(
        reduction_read_data_a,
        reduction_read_data_b
    );
    wire [33:0] mean_scale = ot_fp32_rne_pkg::fp32_mul_rne(
        reduction_read_data_a, MEAN_SCALE_CODE
    );
    wire [33:0] epsilon_add = ot_fp32_rne_pkg::fp32_add_positive_rne(
        mean_private, EPSILON_CODE
    );
    wire reduction_write_from_square =
        state == S_RMS_ACCEPT && hidden_rd_data[14:7] != 8'hff &&
        input_square[33:32] == FP_ERR_NONE;
    wire reduction_write_from_add =
        state == S_REDUCE && reduction_add[33:32] == FP_ERR_NONE;
    wire reduction_write_enable =
        reduction_write_from_square || reduction_write_from_add;
    wire [13:0] reduction_write_address = reduction_write_from_add
        ? reduction_pair_index : k_index;
    wire [31:0] reduction_write_data = reduction_write_from_add
        ? reduction_add[31:0] : input_square[31:0];

    ot_a3_hc_reduction_store reduction_store (
        .clk(clk),
        .write_enable(reduction_write_enable),
        .write_address(reduction_write_address),
        .write_data(reduction_write_data),
        .read_address_a(reduction_read_address_a),
        .read_address_b(reduction_read_address_b),
        .read_data_a(reduction_read_data_a),
        .read_data_b(reduction_read_data_b)
    );

    wire rsqrt_in_valid = state == S_RSQRT_ISSUE;
    wire rsqrt_in_ready;
    wire rsqrt_out_valid;
    wire [31:0] rsqrt_result_code;
    wire [1:0] rsqrt_result_error;

    ot_fp32_rsqrt_rne rsqrt (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(rsqrt_in_valid),
        .in_ready(rsqrt_in_ready),
        .argument_code(epsilon_add[31:0]),
        .out_valid(rsqrt_out_valid),
        .out_ready(state == S_RSQRT_WAIT),
        .result_code(rsqrt_result_code),
        .result_error(rsqrt_result_error)
    );

    wire [33:0] lane_fma [0:LANES-1];
    wire [33:0] lane_normalized [0:LANES-1];
    wire lane_fma_error;
    wire lane_normalized_error;
    genvar lane;
    generate
        for (lane = 0; lane < LANES; lane = lane + 1) begin : g_lane
            // Keep the exact, wide combinational function quiescent outside
            // the sole consume state.  This does not change its architectural
            // boundary and materially reduces event-driven verification cost.
            assign lane_fma[lane] = state == S_PROJ_ACCEPT
                ? ot_a3_hc_projection_pkg::bf16_fp32_fp32_product_add_rne(
                    projection_accumulator[field_base + lane],
                    hidden_rd_data,
                    weight_rd_data[32*lane +: 32]
                ) : 34'b0;
            assign lane_normalized[lane] =
                state == S_PROJ_ACCEPT && k_index == WIDTH-1
                ? ot_fp32_rne_pkg::fp32_mul_rne(
                    lane_fma[lane][31:0], inverse_private
                ) : 34'b0;
        end
    endgenerate
    assign lane_fma_error =
        (lane_fma[0][33:32] != FP_ERR_NONE) ||
        (lane_fma[1][33:32] != FP_ERR_NONE) ||
        (lane_fma[2][33:32] != FP_ERR_NONE) ||
        (lane_fma[3][33:32] != FP_ERR_NONE) ||
        (lane_fma[4][33:32] != FP_ERR_NONE) ||
        (lane_fma[5][33:32] != FP_ERR_NONE) ||
        (lane_fma[6][33:32] != FP_ERR_NONE) ||
        (lane_fma[7][33:32] != FP_ERR_NONE);
    assign lane_normalized_error =
        (lane_normalized[0][33:32] != FP_ERR_NONE) ||
        (lane_normalized[1][33:32] != FP_ERR_NONE) ||
        (lane_normalized[2][33:32] != FP_ERR_NONE) ||
        (lane_normalized[3][33:32] != FP_ERR_NONE) ||
        (lane_normalized[4][33:32] != FP_ERR_NONE) ||
        (lane_normalized[5][33:32] != FP_ERR_NONE) ||
        (lane_normalized[6][33:32] != FP_ERR_NONE) ||
        (lane_normalized[7][33:32] != FP_ERR_NONE);

    assign in_ready = state == S_IDLE && !out_valid;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            hidden_rd_en <= 1'b0;
            hidden_rd_k <= 0;
            weight_rd_en <= 1'b0;
            weight_rd_field_base <= 0;
            weight_rd_k <= 0;
            out_valid <= 1'b0;
            mean_square_code <= 0;
            inverse_rms_code <= 0;
            projection_codes <= 0;
            normalized_projection_codes <= 0;
            result_error <= FP_ERR_NONE;
            square_count <= 0;
            reduction_add_count <= 0;
            fused_product_add_count <= 0;
            mean_private <= 0;
            inverse_private <= 0;
            k_index <= 0;
            field_base <= 0;
            reduction_pair_index <= 0;
            reduction_count <= 0;
            for (item = 0; item < FIELDS; item = item + 1) begin
                projection_accumulator[item] <= 0;
                projection_private[item] <= 0;
                normalized_private[item] <= 0;
            end
        end else begin
            hidden_rd_en <= 1'b0;
            weight_rd_en <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (in_valid && in_ready) begin
                        out_valid <= 1'b0;
                        mean_square_code <= 0;
                        inverse_rms_code <= 0;
                        projection_codes <= 0;
                        normalized_projection_codes <= 0;
                        result_error <= FP_ERR_NONE;
                        square_count <= 0;
                        reduction_add_count <= 0;
                        fused_product_add_count <= 0;
                        mean_private <= 0;
                        inverse_private <= 0;
                        k_index <= 0;
                        field_base <= 0;
                        reduction_pair_index <= 0;
                        reduction_count <= WIDTH;
                        for (item = 0; item < FIELDS; item = item + 1) begin
                            projection_accumulator[item] <= 0;
                            projection_private[item] <= 0;
                            normalized_private[item] <= 0;
                        end
                        state <= S_RMS_ISSUE;
                    end
                end

                S_RMS_ISSUE: begin
                    hidden_rd_en <= 1'b1;
                    hidden_rd_k <= k_index;
                    state <= S_RMS_WAIT;
                end

                S_RMS_WAIT: state <= S_RMS_ACCEPT;

                S_RMS_ACCEPT: begin
                    if (hidden_rd_data[14:7] == 8'hff) begin
                        result_error <= FP_ERR_ARGUMENT;
                        out_valid <= 1'b1;
                        state <= S_OUT;
                    end else if (input_square[33:32] != FP_ERR_NONE) begin
                        result_error <= input_square[33:32];
                        out_valid <= 1'b1;
                        state <= S_OUT;
                    end else begin
                        square_count <= square_count + 1'b1;
                        if (k_index == WIDTH-1) begin
                            k_index <= 0;
                            reduction_pair_index <= 0;
                            reduction_count <= WIDTH;
                            state <= S_REDUCE;
                        end else begin
                            k_index <= k_index + 1'b1;
                            state <= S_RMS_ISSUE;
                        end
                    end
                end

                S_REDUCE: begin
                    if (reduction_add[33:32] != FP_ERR_NONE) begin
                        result_error <= reduction_add[33:32];
                        out_valid <= 1'b1;
                        state <= S_OUT;
                    end else begin
                        reduction_add_count <= reduction_add_count + 1'b1;
                        if ({1'b0, reduction_pair_index} + 1'b1 ==
                            (reduction_count >> 1)) begin
                            reduction_pair_index <= 0;
                            reduction_count <= reduction_count >> 1;
                            if ((reduction_count >> 1) == 1)
                                state <= S_MEAN;
                        end else begin
                            reduction_pair_index <=
                                reduction_pair_index + 1'b1;
                        end
                    end
                end

                S_MEAN: begin
                    if (mean_scale[33:32] != FP_ERR_NONE) begin
                        result_error <= mean_scale[33:32];
                        out_valid <= 1'b1;
                        state <= S_OUT;
                    end else begin
                        mean_private <= mean_scale[31:0];
                        state <= S_EPSILON;
                    end
                end

                S_EPSILON: begin
                    if ((epsilon_add[33:32] != FP_ERR_NONE) ||
                        (epsilon_add[30:0] == 0)) begin
                        result_error <= FP_ERR_OVERFLOW;
                        out_valid <= 1'b1;
                        state <= S_OUT;
                    end else begin
                        state <= S_RSQRT_ISSUE;
                    end
                end

                S_RSQRT_ISSUE: begin
                    if (rsqrt_in_ready)
                        state <= S_RSQRT_WAIT;
                end

                S_RSQRT_WAIT: begin
                    if (rsqrt_out_valid) begin
                        if (rsqrt_result_error != FP_ERR_NONE) begin
                            result_error <= rsqrt_result_error;
                            out_valid <= 1'b1;
                            state <= S_OUT;
                        end else begin
                            inverse_private <= rsqrt_result_code;
                            k_index <= 0;
                            field_base <= 0;
                            state <= S_PROJ_ISSUE;
                        end
                    end
                end

                S_PROJ_ISSUE: begin
                    hidden_rd_en <= 1'b1;
                    hidden_rd_k <= k_index;
                    weight_rd_en <= 1'b1;
                    weight_rd_field_base <= field_base;
                    weight_rd_k <= k_index;
                    state <= S_PROJ_WAIT;
                end

                S_PROJ_WAIT: state <= S_PROJ_ACCEPT;

                S_PROJ_ACCEPT: begin
                    if (lane_fma_error) begin
                        result_error <=
                            (lane_fma[0][33:32] == FP_ERR_OVERFLOW ||
                             lane_fma[1][33:32] == FP_ERR_OVERFLOW ||
                             lane_fma[2][33:32] == FP_ERR_OVERFLOW ||
                             lane_fma[3][33:32] == FP_ERR_OVERFLOW ||
                             lane_fma[4][33:32] == FP_ERR_OVERFLOW ||
                             lane_fma[5][33:32] == FP_ERR_OVERFLOW ||
                             lane_fma[6][33:32] == FP_ERR_OVERFLOW ||
                             lane_fma[7][33:32] == FP_ERR_OVERFLOW)
                            ? FP_ERR_OVERFLOW : FP_ERR_ARGUMENT;
                        out_valid <= 1'b1;
                        state <= S_OUT;
                    end else if ((k_index == WIDTH-1) &&
                                 lane_normalized_error) begin
                        result_error <= FP_ERR_OVERFLOW;
                        out_valid <= 1'b1;
                        state <= S_OUT;
                    end else begin
                        for (item = 0; item < LANES; item = item + 1)
                            projection_accumulator[field_base + item] <=
                                lane_fma[item][31:0];
                        fused_product_add_count <=
                            fused_product_add_count + LANES;
                        if (k_index == WIDTH-1) begin
                            for (item = 0; item < LANES; item = item + 1) begin
                                projection_private[field_base + item] <=
                                    lane_fma[item][31:0];
                                normalized_private[field_base + item] <=
                                    lane_normalized[item][31:0];
                            end
                            k_index <= 0;
                            if (field_base + LANES == FIELDS)
                                state <= S_PUBLISH;
                            else begin
                                field_base <= field_base + LANES;
                                state <= S_PROJ_ISSUE;
                            end
                        end else begin
                            k_index <= k_index + 1'b1;
                            state <= S_PROJ_ISSUE;
                        end
                    end
                end

                S_PUBLISH: begin
                    mean_square_code <= mean_private;
                    inverse_rms_code <= inverse_private;
                    for (item = 0; item < FIELDS; item = item + 1) begin
                        projection_codes[32*item +: 32] <=
                            projection_private[item];
                        normalized_projection_codes[32*item +: 32] <=
                            normalized_private[item];
                    end
                    result_error <= FP_ERR_NONE;
                    out_valid <= 1'b1;
                    state <= S_OUT;
                end

                S_OUT: begin
                    if (out_valid && out_ready) begin
                        out_valid <= 1'b0;
                        mean_square_code <= 0;
                        inverse_rms_code <= 0;
                        projection_codes <= 0;
                        normalized_projection_codes <= 0;
                        result_error <= FP_ERR_NONE;
                        state <= S_IDLE;
                    end
                end

                default: begin
                    mean_square_code <= 0;
                    inverse_rms_code <= 0;
                    projection_codes <= 0;
                    normalized_projection_codes <= 0;
                    result_error <= FP_ERR_ARGUMENT;
                    out_valid <= 1'b1;
                    state <= S_OUT;
                end
            endcase
        end
    end
endmodule
