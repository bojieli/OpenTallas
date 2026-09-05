`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Exact one-token Qwen3-8B grouped-query attention datapath.
//
// This engine implements qwen3_gqa_fp32_softmax_bf16_v1 for the ABI 3.0
// decode geometry [1,32,128] x [C,8,128].  Query heads 4*h..4*h+3 select KV
// head h.
//
// C is a *runtime* length inside a compile-time bound, not a constant.  It
// was a constant 17, which expressed exactly one generated token: the
// governed workload's three decode positions run at contexts 17, 18 and 19,
// and the second and third were inexpressible.  ``MAX_CONTEXT`` now sizes the
// score, exponential and probability buffers, and ``cfg_context_length`` is
// checked against the closed interval [MIN_CONTEXT, MAX_CONTEXT] at start.
//
// The lower bound is not decoration.  The softmax denominator is the frozen
// eight-lane reduction, and ``binary32_lanes8_sum`` reduces a row shorter
// than eight *sequentially* -- a different association, and therefore
// potentially a different last bit.  This datapath implements the eight-lane
// branch only, so a context below eight is refused with ERR_CONFIG rather
// than reduced in an order the contract does not name.  Dot products and value reductions run in increasing logical index;
// every product/add rounds to binary32, the dot and scale round to BF16, and
// softmax uses the specified eight-lane reduction.  Exponential is delegated
// to the shared certifying transcendental engine and reciprocal to the shared
// correctly-rounded divider.
//
// Memory is one-outstanding-request ready/valid.  Every BF16 operand is checked
// before use.  No external output becomes visible until the complete 4,096-word
// result is buffered, so a late memory or numeric fault produces zero writes.
// Output valid/address/data remain stable under backpressure.
// ---------------------------------------------------------------------------
module ot_a3_qwen_gqa #(
    // The largest context this instance's buffers hold.  The reference caps a
    // Qwen KV cache at runtime.reference.tensor_accelerator_attention.
    // MAX_CONTEXT_TOKENS = 8192; a verification instance sizes itself to the
    // contexts its campaign actually issues.
    parameter integer MAX_CONTEXT = 32
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [31:0] cfg_context_length,
    input  wire [31:0] cfg_query_base,
    input  wire [31:0] cfg_key_base,
    input  wire [31:0] cfg_value_base,
    input  wire [31:0] cfg_output_base,

    output wire        mem_req_valid,
    input  wire        mem_req_ready,
    output wire [31:0] mem_req_addr,
    input  wire        mem_rsp_valid,
    input  wire [31:0] mem_rsp_data,

    output wire        out_valid,
    input  wire        out_ready,
    output wire [31:0] out_addr,
    output wire [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg         failed,
    output reg  [7:0]  error_code,
    output reg  [31:0] memory_read_count,
    output reg  [31:0] output_write_count,
    output reg  [31:0] score_multiply_count,
    output reg  [31:0] exponential_count,
    output reg  [31:0] value_multiply_count,
    output reg  [31:0] saturation_count
);
    localparam [7:0] ERR_NONE = 8'd0;
    localparam [7:0] ERR_CONFIG = 8'd1;
    localparam [7:0] ERR_INPUT = 8'd2;
    localparam [7:0] ERR_NUMERIC = 8'd3;

    // The eight-lane softmax reduction the contract names is defined for
    // rows of eight or more; below that the reference reduces sequentially.
    localparam integer MIN_CONTEXT = 8;
    localparam integer QUERY_HEADS = 32;
    localparam integer KV_HEADS = 8;
    localparam integer HEAD_WIDTH = 128;
    localparam integer KV_ROW_WORDS = KV_HEADS * HEAD_WIDTH;
    localparam integer OUTPUT_WORDS = QUERY_HEADS * HEAD_WIDTH;
    localparam [31:0] SCALE_CODE = 32'h3db5_0000;
    localparam [31:0] FP32_ONE = 32'h3f80_0000;

    localparam [5:0] S_IDLE = 6'd0;
    localparam [5:0] S_QUERY_REQ = 6'd1;
    localparam [5:0] S_QUERY_RSP = 6'd2;
    localparam [5:0] S_KEY_REQ = 6'd3;
    localparam [5:0] S_KEY_RSP = 6'd4;
    localparam [5:0] S_EXP_REQ = 6'd5;
    localparam [5:0] S_EXP_RSP = 6'd6;
    localparam [5:0] S_REDUCE_HALF = 6'd7;
    localparam [5:0] S_REDUCE_QUARTER = 6'd8;
    localparam [5:0] S_REDUCE_DENOM = 6'd9;
    localparam [5:0] S_DIV_REQ = 6'd10;
    localparam [5:0] S_DIV_RSP = 6'd11;
    localparam [5:0] S_PROBABILITY = 6'd12;
    localparam [5:0] S_VALUE_REQ = 6'd13;
    localparam [5:0] S_VALUE_RSP = 6'd14;
    localparam [5:0] S_PUBLISH = 6'd15;
    localparam [5:0] S_FINISH = 6'd16;

    reg [5:0] state;
    reg [31:0] query_base_q;
    reg [31:0] key_base_q;
    reg [31:0] value_base_q;
    reg [31:0] output_base_q;
    reg [5:0] query_head_q;
    reg [2:0] kv_head_q;
    reg [7:0] dimension_q;
    reg [15:0] context_index_q;
    reg [15:0] context_length_q;
    wire [15:0] context_last = context_length_q - 16'd1;
    reg [11:0] publish_index_q;

    reg [15:0] query_buffer [0:HEAD_WIDTH-1];
    reg [15:0] score_buffer [0:MAX_CONTEXT-1];
    reg [31:0] exponential_buffer [0:MAX_CONTEXT-1];
    reg [15:0] probability_buffer [0:MAX_CONTEXT-1];
    reg [15:0] output_buffer [0:OUTPUT_WORDS-1];
    reg [31:0] softmax_lanes [0:7];
    reg [31:0] softmax_half [0:3];
    reg [31:0] softmax_quarter [0:1];
    reg [31:0] maximum_code_q;
    reg [31:0] dot_accumulator_q;
    reg [31:0] value_accumulator_q;
    reg [31:0] inverse_denominator_q;

    wire request_is_query = state == S_QUERY_REQ;
    wire request_is_key = state == S_KEY_REQ;
    wire request_is_value = state == S_VALUE_REQ;
    assign mem_req_valid = request_is_query || request_is_key ||
        request_is_value;
    assign mem_req_addr = request_is_query
        ? query_base_q + query_head_q * HEAD_WIDTH + dimension_q
        : request_is_key
          ? key_base_q + context_index_q * KV_ROW_WORDS +
            kv_head_q * HEAD_WIDTH + dimension_q
          : value_base_q + context_index_q * KV_ROW_WORDS +
            kv_head_q * HEAD_WIDTH + dimension_q;

    assign out_valid = state == S_PUBLISH;
    assign out_addr = output_base_q + publish_index_q;
    assign out_data = {16'd0, output_buffer[publish_index_q]};

    wire response_nonfinite = mem_rsp_data[14:7] == 8'hff;
    wire [31:0] query_fp32 = {query_buffer[dimension_q], 16'd0};
    wire [31:0] response_fp32 = {mem_rsp_data[15:0], 16'd0};

    wire [33:0] score_product = ot_fp32_rne_pkg::fp32_mul_rne(
        query_fp32, response_fp32
    );
    wire [33:0] score_sum = ot_fp32_rne_pkg::fp32_add_rne(
        dot_accumulator_q, score_product[31:0]
    );
    wire [18:0] score_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(
        score_sum[31:0]
    );
    wire [33:0] scaled_score = ot_fp32_rne_pkg::fp32_mul_rne(
        {score_bf16[15:0], 16'd0}, SCALE_CODE
    );
    wire [18:0] scaled_score_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(
        scaled_score[31:0]
    );

    function automatic fp32_greater;
        input [31:0] left;
        input [31:0] right;
        begin
            if ((left[30:0] == 0) && (right[30:0] == 0))
                fp32_greater = 1'b0;
            else if (left[31] != right[31])
                fp32_greater = right[31];
            else if (!left[31])
                fp32_greater = left[30:0] > right[30:0];
            else
                fp32_greater = left[30:0] < right[30:0];
        end
    endfunction

    function automatic [31:0] negate_fp32;
        input [31:0] value;
        begin
            negate_fp32 = value[30:0] == 0 ? 32'd0 :
                {~value[31], value[30:0]};
        end
    endfunction

    wire [33:0] shifted_score = ot_fp32_rne_pkg::fp32_add_rne(
        {score_buffer[context_index_q], 16'd0}, negate_fp32(maximum_code_q)
    );

    wire exp_in_ready;
    wire exp_out_valid;
    wire [31:0] exp_result;
    wire [1:0] exp_error;
    ot_a3_fp32_transcendental_cr_rne exponential (
        .clk(clk), .rst_n(rst_n),
        .in_valid(state == S_EXP_REQ), .in_ready(exp_in_ready),
        .operation(1'b0), .argument_code(shifted_score[31:0]),
        .out_valid(exp_out_valid), .out_ready(state == S_EXP_RSP),
        .result_code(exp_result), .result_error(exp_error)
    );

    wire [33:0] lane_add = ot_fp32_rne_pkg::fp32_add_positive_rne(
        softmax_lanes[context_index_q[2:0]], exp_result
    );
    wire [33:0] half_add_0 = ot_fp32_rne_pkg::fp32_add_positive_rne(
        softmax_lanes[0], softmax_lanes[4]
    );
    wire [33:0] half_add_1 = ot_fp32_rne_pkg::fp32_add_positive_rne(
        softmax_lanes[1], softmax_lanes[5]
    );
    wire [33:0] half_add_2 = ot_fp32_rne_pkg::fp32_add_positive_rne(
        softmax_lanes[2], softmax_lanes[6]
    );
    wire [33:0] half_add_3 = ot_fp32_rne_pkg::fp32_add_positive_rne(
        softmax_lanes[3], softmax_lanes[7]
    );
    wire [33:0] quarter_add_0 = ot_fp32_rne_pkg::fp32_add_positive_rne(
        softmax_half[0], softmax_half[2]
    );
    wire [33:0] quarter_add_1 = ot_fp32_rne_pkg::fp32_add_positive_rne(
        softmax_half[1], softmax_half[3]
    );
    wire [33:0] denominator_add = ot_fp32_rne_pkg::fp32_add_positive_rne(
        softmax_quarter[0], softmax_quarter[1]
    );

    wire divider_in_ready;
    wire divider_out_valid;
    wire [31:0] divider_result;
    wire [1:0] divider_error;
    ot_a3_fp32_div_rne divider (
        .clk(clk), .rst_n(rst_n),
        .in_valid(state == S_DIV_REQ), .in_ready(divider_in_ready),
        .numerator_code(FP32_ONE),
        .denominator_code(denominator_add[31:0]),
        .out_valid(divider_out_valid), .out_ready(state == S_DIV_RSP),
        .result_code(divider_result), .result_error(divider_error)
    );

    wire [33:0] probability_product = ot_fp32_rne_pkg::fp32_mul_rne(
        exponential_buffer[context_index_q], inverse_denominator_q
    );
    wire [18:0] probability_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(
        probability_product[31:0]
    );
    wire [33:0] value_product = ot_fp32_rne_pkg::fp32_mul_rne(
        {probability_buffer[context_index_q], 16'd0}, response_fp32
    );
    wire [33:0] value_sum = ot_fp32_rne_pkg::fp32_add_rne(
        value_accumulator_q, value_product[31:0]
    );
    wire [18:0] output_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(
        value_sum[31:0]
    );

    task automatic fail_numeric;
        begin
            failed <= 1'b1;
            error_code <= ERR_NUMERIC;
            state <= S_FINISH;
        end
    endtask

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            query_base_q <= 0;
            key_base_q <= 0;
            value_base_q <= 0;
            output_base_q <= 0;
            query_head_q <= 0;
            kv_head_q <= 0;
            dimension_q <= 0;
            context_index_q <= 0;
            context_length_q <= 0;
            publish_index_q <= 0;
            maximum_code_q <= 0;
            dot_accumulator_q <= 0;
            value_accumulator_q <= 0;
            inverse_denominator_q <= 0;
            busy <= 1'b0;
            done <= 1'b0;
            failed <= 1'b0;
            error_code <= ERR_NONE;
            memory_read_count <= 0;
            output_write_count <= 0;
            score_multiply_count <= 0;
            exponential_count <= 0;
            value_multiply_count <= 0;
            saturation_count <= 0;
        end else begin
            done <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        query_base_q <= cfg_query_base;
                        key_base_q <= cfg_key_base;
                        value_base_q <= cfg_value_base;
                        output_base_q <= cfg_output_base;
                        query_head_q <= 0;
                        kv_head_q <= 0;
                        dimension_q <= 0;
                        context_index_q <= 0;
                        publish_index_q <= 0;
                        maximum_code_q <= 0;
                        dot_accumulator_q <= 0;
                        value_accumulator_q <= 0;
                        inverse_denominator_q <= 0;
                        busy <= 1'b1;
                        failed <= 1'b0;
                        error_code <= ERR_NONE;
                        memory_read_count <= 0;
                        output_write_count <= 0;
                        score_multiply_count <= 0;
                        exponential_count <= 0;
                        value_multiply_count <= 0;
                        saturation_count <= 0;
                        context_length_q <= cfg_context_length[15:0];
                        if ((cfg_context_length < MIN_CONTEXT) ||
                            (cfg_context_length > MAX_CONTEXT)) begin
                            failed <= 1'b1;
                            error_code <= ERR_CONFIG;
                            state <= S_FINISH;
                        end else begin
                            state <= S_QUERY_REQ;
                        end
                    end
                end

                S_QUERY_REQ: begin
                    if (mem_req_ready)
                        state <= S_QUERY_RSP;
                end

                S_QUERY_RSP: begin
                    if (mem_rsp_valid) begin
                        memory_read_count <= memory_read_count + 1'b1;
                        if (response_nonfinite) begin
                            failed <= 1'b1;
                            error_code <= ERR_INPUT;
                            state <= S_FINISH;
                        end else begin
                            query_buffer[dimension_q] <= mem_rsp_data[15:0];
                            if (dimension_q == HEAD_WIDTH-1) begin
                                dimension_q <= 0;
                                context_index_q <= 0;
                                dot_accumulator_q <= 0;
                                state <= S_KEY_REQ;
                            end else begin
                                dimension_q <= dimension_q + 1'b1;
                                state <= S_QUERY_REQ;
                            end
                        end
                    end
                end

                S_KEY_REQ: begin
                    if (mem_req_ready)
                        state <= S_KEY_RSP;
                end

                S_KEY_RSP: begin
                    if (mem_rsp_valid) begin
                        memory_read_count <= memory_read_count + 1'b1;
                        score_multiply_count <= score_multiply_count + 1'b1;
                        if (response_nonfinite ||
                            score_product[33:32] != 0 ||
                            score_sum[33:32] != 0) begin
                            failed <= 1'b1;
                            error_code <= response_nonfinite
                                ? ERR_INPUT : ERR_NUMERIC;
                            state <= S_FINISH;
                        end else if (dimension_q == HEAD_WIDTH-1) begin
                            if (score_bf16[18:17] != 0 ||
                                scaled_score[33:32] != 0 ||
                                scaled_score_bf16[18:17] != 0) begin
                                fail_numeric();
                            end else begin
                                score_buffer[context_index_q] <=
                                    scaled_score_bf16[15:0];
                                saturation_count <= saturation_count +
                                    score_bf16[16] + scaled_score_bf16[16];
                                if ((context_index_q == 0) ||
                                    fp32_greater(
                                        {scaled_score_bf16[15:0], 16'd0},
                                        maximum_code_q
                                    ))
                                    maximum_code_q <= {
                                        scaled_score_bf16[15:0], 16'd0
                                    };
                                dimension_q <= 0;
                                dot_accumulator_q <= 0;
                                if (context_index_q == context_last) begin
                                    context_index_q <= 0;
                                    state <= S_EXP_REQ;
                                end else begin
                                    context_index_q <=
                                        context_index_q + 1'b1;
                                    state <= S_KEY_REQ;
                                end
                            end
                        end else begin
                            dot_accumulator_q <= score_sum[31:0];
                            dimension_q <= dimension_q + 1'b1;
                            state <= S_KEY_REQ;
                        end
                    end
                end

                S_EXP_REQ: begin
                    if (shifted_score[33:32] != 0) begin
                        fail_numeric();
                    end else if (exp_in_ready) begin
                        state <= S_EXP_RSP;
                    end
                end

                S_EXP_RSP: begin
                    if (exp_out_valid) begin
                        if (exp_error != 0) begin
                            fail_numeric();
                        end else begin
                            exponential_count <= exponential_count + 1'b1;
                            exponential_buffer[context_index_q] <= exp_result;
                            if (context_index_q < 8) begin
                                softmax_lanes[context_index_q[2:0]] <=
                                    exp_result;
                            end else if (lane_add[33:32] != 0) begin
                                fail_numeric();
                            end else begin
                                softmax_lanes[context_index_q[2:0]] <=
                                    lane_add[31:0];
                            end
                            if (exp_error == 0 &&
                                (context_index_q < 8 ||
                                 lane_add[33:32] == 0)) begin
                                if (context_index_q == context_last) begin
                                    state <= S_REDUCE_HALF;
                                end else begin
                                    context_index_q <=
                                        context_index_q + 1'b1;
                                    state <= S_EXP_REQ;
                                end
                            end
                        end
                    end
                end

                S_REDUCE_HALF: begin
                    if ((half_add_0[33:32] != 0) ||
                        (half_add_1[33:32] != 0) ||
                        (half_add_2[33:32] != 0) ||
                        (half_add_3[33:32] != 0)) begin
                        fail_numeric();
                    end else begin
                        softmax_half[0] <= half_add_0[31:0];
                        softmax_half[1] <= half_add_1[31:0];
                        softmax_half[2] <= half_add_2[31:0];
                        softmax_half[3] <= half_add_3[31:0];
                        state <= S_REDUCE_QUARTER;
                    end
                end

                S_REDUCE_QUARTER: begin
                    if ((quarter_add_0[33:32] != 0) ||
                        (quarter_add_1[33:32] != 0)) begin
                        fail_numeric();
                    end else begin
                        softmax_quarter[0] <= quarter_add_0[31:0];
                        softmax_quarter[1] <= quarter_add_1[31:0];
                        state <= S_REDUCE_DENOM;
                    end
                end

                S_REDUCE_DENOM: begin
                    if (denominator_add[33:32] != 0 ||
                        denominator_add[30:0] == 0) begin
                        fail_numeric();
                    end else begin
                        state <= S_DIV_REQ;
                    end
                end

                S_DIV_REQ: begin
                    if (divider_in_ready)
                        state <= S_DIV_RSP;
                end

                S_DIV_RSP: begin
                    if (divider_out_valid) begin
                        if (divider_error != 0) begin
                            fail_numeric();
                        end else begin
                            inverse_denominator_q <= divider_result;
                            context_index_q <= 0;
                            state <= S_PROBABILITY;
                        end
                    end
                end

                S_PROBABILITY: begin
                    if (probability_product[33:32] != 0 ||
                        probability_bf16[18:17] != 0) begin
                        fail_numeric();
                    end else begin
                        probability_buffer[context_index_q] <=
                            probability_bf16[15:0];
                        saturation_count <= saturation_count +
                            probability_bf16[16];
                        if (context_index_q == context_last) begin
                            context_index_q <= 0;
                            dimension_q <= 0;
                            value_accumulator_q <= 0;
                            state <= S_VALUE_REQ;
                        end else begin
                            context_index_q <= context_index_q + 1'b1;
                        end
                    end
                end

                S_VALUE_REQ: begin
                    if (mem_req_ready)
                        state <= S_VALUE_RSP;
                end

                S_VALUE_RSP: begin
                    if (mem_rsp_valid) begin
                        memory_read_count <= memory_read_count + 1'b1;
                        value_multiply_count <= value_multiply_count + 1'b1;
                        if (response_nonfinite ||
                            value_product[33:32] != 0 ||
                            value_sum[33:32] != 0) begin
                            failed <= 1'b1;
                            error_code <= response_nonfinite
                                ? ERR_INPUT : ERR_NUMERIC;
                            state <= S_FINISH;
                        end else if (context_index_q == context_last) begin
                            if (output_bf16[18:17] != 0) begin
                                fail_numeric();
                            end else begin
                                output_buffer[
                                    query_head_q * HEAD_WIDTH + dimension_q
                                ] <= output_bf16[15:0];
                                saturation_count <= saturation_count +
                                    output_bf16[16];
                                context_index_q <= 0;
                                value_accumulator_q <= 0;
                                if (dimension_q == HEAD_WIDTH-1) begin
                                    dimension_q <= 0;
                                    if (query_head_q == QUERY_HEADS-1) begin
                                        publish_index_q <= 0;
                                        state <= S_PUBLISH;
                                    end else begin
                                        query_head_q <= query_head_q + 1'b1;
                                        kv_head_q <=
                                            (query_head_q + 1'b1) >> 2;
                                        state <= S_QUERY_REQ;
                                    end
                                end else begin
                                    dimension_q <= dimension_q + 1'b1;
                                    state <= S_VALUE_REQ;
                                end
                            end
                        end else begin
                            value_accumulator_q <= value_sum[31:0];
                            context_index_q <= context_index_q + 1'b1;
                            state <= S_VALUE_REQ;
                        end
                    end
                end

                S_PUBLISH: begin
                    if (out_ready) begin
                        output_write_count <= output_write_count + 1'b1;
                        if (publish_index_q == OUTPUT_WORDS-1)
                            state <= S_FINISH;
                        else
                            publish_index_q <= publish_index_q + 1'b1;
                    end
                end

                S_FINISH: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end

                default: begin
                    failed <= 1'b1;
                    error_code <= ERR_CONFIG;
                    state <= S_FINISH;
                end
            endcase
        end
    end
endmodule
