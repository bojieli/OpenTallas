`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Exact descriptor-sized Qwen BF16 RMSNorm datapath.
//
// This is the ABI 3.0 bank-port form of the already correlated production
// RMSNorm arithmetic: BF16 inputs widen exactly, every square and balanced
// binary32 reduction node rounds once, reciprocal square root is correctly
// rounded, normalization rounds to BF16 before the BF16 gain multiply, and
// the final result rounds to BF16.  The complete result is buffered before
// the first write, so a numeric refusal cannot expose a partial destination.
// The admitted geometries are any power-of-two row width up to 4,096 -- one
// model row of that width, or up to 32 independent rows no wider than the
// 128-element head profile.  Power-of-two is the exact condition under which
// the engine's reciprocal multiply reproduces the golden's division by the
// width bit for bit, so it is the widest set that stays inside the
// characterised arithmetic; the shipped Qwen pair (one 4,096-element model row,
// up to 32 128-element head rows) and the reduced regression pair (128 and 16)
// are both inside it.  One BF16 code occupies the low half of each 32-bit
// verification-bank word.
// ---------------------------------------------------------------------------
module ot_a3_vector_rms_norm #(
    //: THE OPERATING PROFILE, as parameters rather than localparams.
    //:
    //: These four were fixed constants, and the index registers below were sized
    //: to match them by hand.  A 16-token prefill normalises 16 x heads rows at
    //: once, which is 128 rows against a 32-row ceiling -- and because
    //: ``row_index`` was hand-sized to 6 bits for that ceiling, raising the
    //: ceiling alone would have made the row terminator never match and the
    //: engine HANG rather than refuse.  Deriving the register widths from the
    //: parameters is what makes the ceiling safe to raise.
    parameter [31:0] PROFILE_MAX_COUNT   = 32'd4096,
    parameter [31:0] PROFILE_MAX_ROWS    = 32'd32,
    parameter [31:0] PROFILE_MODEL_WIDTH = 32'd4096,
    parameter [31:0] PROFILE_HEAD_WIDTH  = 32'd128
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [31:0] cfg_count,
    input  wire [31:0] cfg_rows,
    input  wire [31:0] cfg_cols,
    input  wire [31:0] cfg_epsilon_bits,
    input  wire [31:0] cfg_input_base,
    input  wire [31:0] cfg_weight_base,
    input  wire [31:0] cfg_output_base,

    output reg         input_rd_en,
    output reg  [31:0] input_rd_addr,
    input  wire [31:0] input_rd_data,
    output reg         weight_rd_en,
    output reg  [31:0] weight_rd_addr,
    input  wire [31:0] weight_rd_data,
    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] result_count,
    output reg  [31:0] saturation_count,
    output reg  [31:0] work_count
);
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE =
        ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_ACCUMULATE_RANGE =
        ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;
    localparam [1:0] FP_ERR_NONE = 2'd0;

    localparam [31:0] PROFILE_EPSILON = 32'h3586_37bd;
    // The two widths the shipped Qwen deployment issues, kept as named
    // constants because the shape check and the census both cite them.
    localparam [31:0] MODEL_MEAN_SCALE_CODE = 32'h3980_0000;  // 1/4096 = 2**-12
    localparam [31:0] HEAD_MEAN_SCALE_CODE = 32'h3c00_0000;   // 1/128  = 2**-7

    // ...but the reciprocal is DERIVED, not selected from those two.
    //
    // The golden model is width-generic and does not use a reciprocal at all:
    // ``runtime/reference/tensor_accelerator_rmsnorm.py`` reads
    // ``width = len(inputs[0])`` and takes the mean as
    // ``binary32_divide(total, encode_binary32_rne(width))``.  For a
    // power-of-two width, dividing by 2**k and multiplying by the exact
    // reciprocal 2**-k are both pure exponent adjustments with no rounding, so
    // the two are BIT-IDENTICAL.  The engine's former restriction to exactly
    // 4096 and 128 was therefore an artefact of hardcoding two constants, not
    // a limit of the characterised arithmetic.
    //
    // Deriving it admits the reduced regression configuration (a 128-wide
    // model row and 16-wide attention-head rows), which rung G1f measured this
    // engine refusing with ERR_SHAPE.  Non-powers-of-two are still refused,
    // because for those the reciprocal is inexact and would NOT reproduce the
    // golden's division.
    function automatic [31:0] exact_reciprocal_code(input [31:0] width);
        integer k;
        begin
            exact_reciprocal_code = 32'd0;
            for (k = 0; k < 31; k = k + 1) begin
                if (width == (32'd1 << k)) begin
                    exact_reciprocal_code = {1'b0, (8'd127 - k[7:0]), 23'd0};
                end
            end
        end
    endfunction

    function automatic is_power_of_two(input [31:0] width);
        begin
            is_power_of_two = (width != 32'd0) && ((width & (width - 32'd1)) == 32'd0);
        end
    endfunction
    //: One element per admitted count, so the buffer follows the ceiling.
    localparam integer BUFFER_ELEMENTS = PROFILE_MAX_COUNT;
    //: Enough to index 0 .. BUFFER_ELEMENTS, and 0 .. PROFILE_MAX_ROWS-1.  The
    //: +1 on the element width is the one the old [12:0] carried for 4,096.
    localparam integer EIW = $clog2(BUFFER_ELEMENTS) + 1;
    localparam integer CIW = $clog2(PROFILE_MODEL_WIDTH);
    localparam integer RIW = $clog2(PROFILE_MAX_ROWS);
    //: The buffer address width.  Every comparison below is done at 32 bits
    //: against the cfg_* inputs instead of against a hand-sized literal, so no
    //: width in this module has to be kept in step with the profile by hand.
    localparam integer BIW = $clog2(BUFFER_ELEMENTS);

    localparam [3:0] S_IDLE         = 4'd0;
    localparam [3:0] S_INPUT_ISSUE  = 4'd1;
    localparam [3:0] S_MEMORY_WAIT  = 4'd2;
    localparam [3:0] S_INPUT        = 4'd3;
    localparam [3:0] S_REDUCE       = 4'd4;
    localparam [3:0] S_MEAN         = 4'd5;
    localparam [3:0] S_EPSILON      = 4'd6;
    localparam [3:0] S_RSQRT_ISSUE  = 4'd7;
    localparam [3:0] S_RSQRT_WAIT   = 4'd8;
    localparam [3:0] S_WEIGHT_ISSUE = 4'd9;
    localparam [3:0] S_WEIGHT       = 4'd10;
    localparam [3:0] S_WRITE        = 4'd11;
    localparam [3:0] S_DONE         = 4'd12;

    reg [3:0] state;
    reg [3:0] wait_next;
    reg [15:0] input_buffer [0:BUFFER_ELEMENTS-1];
    reg [15:0] output_buffer [0:BUFFER_ELEMENTS-1];
    reg [31:0] reduction_buffer [0:BUFFER_ELEMENTS-1];
    reg [EIW-1:0] element_index;
    reg [CIW-1:0] column_index;
    reg [EIW-1:0] row_base_index;
    reg [RIW-1:0] row_index;
    reg [CIW-1:0] reduction_pair_index;
    reg [EIW-1:0] reduction_count;
    reg [31:0] mean_square_code;
    reg [31:0] inverse_rms_code;

    wire [15:0] input_code = input_rd_data[15:0];
    wire [15:0] weight_code = weight_rd_data[15:0];
    wire input_nonfinite = input_code[14:7] == 8'hff;
    wire weight_nonfinite = weight_code[14:7] == 8'hff;
    wire [31:0] input_fp32_code = {input_code, 16'b0};
    wire [31:0] buffered_input_fp32_code = {
        input_buffer[element_index[BIW-1:0]], 16'b0
    };
    wire [31:0] weight_fp32_code = {weight_code, 16'b0};

    wire [33:0] input_square = ot_fp32_rne_pkg::fp32_mul_rne(
        input_fp32_code, input_fp32_code
    );
    wire [CIW-1:0] reduction_left_index = reduction_pair_index << 1;
    wire [CIW-1:0] reduction_right_index = reduction_left_index + 1'b1;
    wire [33:0] reduction_add =
        ot_fp32_rne_pkg::fp32_add_positive_rne(
            reduction_buffer[reduction_left_index],
            reduction_buffer[reduction_right_index]
        );
    wire [31:0] mean_scale_code = exact_reciprocal_code(cfg_cols);
    wire [33:0] mean_scale = ot_fp32_rne_pkg::fp32_mul_rne(
        reduction_buffer[0],
        mean_scale_code
    );
    wire [33:0] epsilon_add =
        ot_fp32_rne_pkg::fp32_add_positive_rne(
            mean_square_code, cfg_epsilon_bits
        );
    wire [33:0] normalized_product = ot_fp32_rne_pkg::fp32_mul_rne(
        buffered_input_fp32_code, inverse_rms_code
    );
    wire [18:0] normalized_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(
        normalized_product[31:0]
    );
    wire [31:0] normalized_fp32_code = {
        normalized_bf16[15:0], 16'b0
    };
    wire [33:0] weighted_product = ot_fp32_rne_pkg::fp32_mul_rne(
        normalized_fp32_code, weight_fp32_code
    );
    wire [18:0] output_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(
        weighted_product[31:0]
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

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            wait_next <= S_IDLE;
            element_index <= 0;
            column_index <= 0;
            row_base_index <= 0;
            row_index <= 0;
            reduction_pair_index <= 0;
            reduction_count <= 0;
            mean_square_code <= 0;
            inverse_rms_code <= 0;
            input_rd_en <= 1'b0;
            input_rd_addr <= 0;
            weight_rd_en <= 1'b0;
            weight_rd_addr <= 0;
            out_we <= 1'b0;
            out_addr <= 0;
            out_data <= 0;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            result_count <= 0;
            saturation_count <= 0;
            work_count <= 0;
        end else begin
            input_rd_en <= 1'b0;
            weight_rd_en <= 1'b0;
            out_we <= 1'b0;
            done <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        result_count <= 0;
                        saturation_count <= 0;
                        work_count <= 0;
                        element_index <= 0;
                        column_index <= 0;
                        row_base_index <= 0;
                        row_index <= 0;
                        reduction_pair_index <= 0;
                        reduction_count <= cfg_cols[EIW-1:0];
                        mean_square_code <= 0;
                        inverse_rms_code <= 0;
                        if ((cfg_count == 0) ||
                            (cfg_count > PROFILE_MAX_COUNT) ||
                            (cfg_rows == 0) ||
                            (cfg_rows > PROFILE_MAX_ROWS) ||
                            !is_power_of_two(cfg_cols) ||
                            (cfg_cols > PROFILE_MODEL_WIDTH) ||
                            ((cfg_rows > 1) &&
                             (cfg_cols > PROFILE_HEAD_WIDTH)) ||
                            ((cfg_rows * cfg_cols) != cfg_count) ||
                            (cfg_epsilon_bits != PROFILE_EPSILON)) begin
                            error_code <= ERR_SHAPE;
                            state <= S_DONE;
                        end else begin
                            state <= S_INPUT_ISSUE;
                        end
                    end
                end

                S_INPUT_ISSUE: begin
                    input_rd_en <= 1'b1;
                    input_rd_addr <= cfg_input_base + {19'b0, element_index};
                    wait_next <= S_INPUT;
                    state <= S_MEMORY_WAIT;
                end

                S_MEMORY_WAIT: state <= wait_next;

                S_INPUT: begin
                    if (input_nonfinite) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else if (input_square[33:32] != FP_ERR_NONE) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        input_buffer[element_index[BIW-1:0]] <= input_code;
                        reduction_buffer[column_index] <= input_square[31:0];
                        if (({{(32-CIW){1'b0}}, column_index} + 32'd1) ==
                            cfg_cols) begin
                            reduction_pair_index <= 0;
                            reduction_count <= cfg_cols[EIW-1:0];
                            state <= S_REDUCE;
                        end else begin
                            element_index <= element_index + 1'b1;
                            column_index <= column_index + 1'b1;
                            state <= S_INPUT_ISSUE;
                        end
                    end
                end

                S_REDUCE: begin
                    if (reduction_add[33:32] != FP_ERR_NONE) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        reduction_buffer[reduction_pair_index] <=
                            reduction_add[31:0];
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
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        mean_square_code <= mean_scale[31:0];
                        state <= S_EPSILON;
                    end
                end

                S_EPSILON: begin
                    if ((epsilon_add[33:32] != FP_ERR_NONE) ||
                        (epsilon_add[30:0] == 0)) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
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
                            error_code <= ERR_ACCUMULATE_RANGE;
                            state <= S_DONE;
                        end else begin
                            inverse_rms_code <= rsqrt_result_code;
                            element_index <= row_base_index;
                            column_index <= 0;
                            state <= S_WEIGHT_ISSUE;
                        end
                    end
                end

                S_WEIGHT_ISSUE: begin
                    weight_rd_en <= 1'b1;
                    weight_rd_addr <= cfg_weight_base + {20'b0, column_index};
                    wait_next <= S_WEIGHT;
                    state <= S_MEMORY_WAIT;
                end

                S_WEIGHT: begin
                    if (weight_nonfinite) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else if ((normalized_product[33:32] != FP_ERR_NONE) ||
                                 (normalized_bf16[18:17] != FP_ERR_NONE) ||
                                 (weighted_product[33:32] != FP_ERR_NONE) ||
                                 (output_bf16[18:17] != FP_ERR_NONE)) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        output_buffer[element_index[BIW-1:0]] <= output_bf16[15:0];
                        saturation_count <= saturation_count +
                            normalized_bf16[16] + output_bf16[16];
                        if (({{(32-CIW){1'b0}}, column_index} + 32'd1) ==
                            cfg_cols) begin
                            if (({{(32-RIW){1'b0}}, row_index} + 32'd1) ==
                                cfg_rows) begin
                                result_count <= cfg_count;
                                work_count <= cfg_count;
                                element_index <= 0;
                                state <= S_WRITE;
                            end else begin
                                row_index <= row_index + 1'b1;
                                row_base_index <= row_base_index +
                                    cfg_cols[EIW-1:0];
                                element_index <= row_base_index +
                                    cfg_cols[EIW-1:0];
                                column_index <= 0;
                                reduction_pair_index <= 0;
                                reduction_count <= cfg_cols[EIW-1:0];
                                state <= S_INPUT_ISSUE;
                            end
                        end else begin
                            element_index <= element_index + 1'b1;
                            column_index <= column_index + 1'b1;
                            state <= S_WEIGHT_ISSUE;
                        end
                    end
                end

                S_WRITE: begin
                    out_we <= 1'b1;
                    out_addr <= cfg_output_base + {19'b0, element_index};
                    out_data <= {16'b0, output_buffer[element_index[BIW-1:0]]};
                    if (({{(32-EIW){1'b0}}, element_index} + 32'd1) ==
                        cfg_count) begin
                        element_index <= 0;
                        state <= S_DONE;
                    end else begin
                        element_index <= element_index + 1'b1;
                    end
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end

                default: begin
                    busy <= 1'b0;
                    error_code <= ERR_SHAPE;
                    state <= S_DONE;
                end
            endcase
        end
    end
endmodule
