`timescale 1ns/1ps
// Current-descriptor, one-token DeepSeek HC_PRE arithmetic integration.
//
// The ordinary ABI decoder/view resolver supplies the same 128-word semantic
// record consumed by ot_a3_vector_mhc_pre_tile_scheduler.  This adapter admits
// current ROM PC15/operator381 or HBM PC14/operator545 at active_tokens=1,
// starts the fixed [4,4096] projection/RMS engine from the first accepted
// projection tile, and feeds its private normalized projections into the
// atomic coefficient tail.  Scheduler completion and all arithmetic must both
// succeed before the 8 weight and 16 combination words become visible.
//
// This is a reusable decode-token HC_PRE boundary.  Multi-token buffering,
// subsequent model layers, logits, selection, append/EOS and architectural
// token-commit timing remain outside this module, so its cycles are not TPOT.
module ot_a3_hc_pre_t1_descriptor_rne #(
    parameter integer CONFIG_WORDS = 128
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         in_valid,
    output wire                         in_ready,
    input  wire [CONFIG_WORDS*32-1:0]   config_words,
    input  wire [767:0]                 base_codes,
    input  wire [95:0]                  scale_codes,

    output wire                         hidden_rd_en,
    output wire [13:0]                  hidden_rd_k,
    input  wire [15:0]                  hidden_rd_data,
    output wire                         weight_rd_en,
    output wire [4:0]                   weight_rd_field_base,
    output wire [13:0]                  weight_rd_k,
    input  wire [255:0]                 weight_rd_data,

    output wire                         out_valid,
    input  wire                         out_ready,
    output wire [255:0]                 result_weight_codes,
    output wire [511:0]                 result_combination_codes,
    output wire [7:0]                   result_error,
    output wire [63:0]                  scheduler_projection_tiles,
    output wire [63:0]                  scheduler_commit_tiles,
    output wire [63:0]                  scheduler_logical_fmas,
    output wire [63:0]                  scheduler_logical_outputs,
    output wire [31:0]                  arithmetic_square_count,
    output wire [31:0]                  arithmetic_reduction_add_count,
    output wire [31:0]                  arithmetic_fma_count
);
    localparam [7:0] ERR_ACTIVE_TOKENS = 8'd21;
    localparam [7:0] ERR_INTEGRATION = 8'd22;
    localparam [7:0] ERR_ARITHMETIC_ARGUMENT = 8'd32;
    localparam [7:0] ERR_ARITHMETIC_RANGE = 8'd33;

    localparam [2:0] S_IDLE = 3'd0;
    localparam [2:0] S_LAUNCH = 3'd1;
    localparam [2:0] S_WAIT_FIRST = 3'd2;
    localparam [2:0] S_RUN = 3'd3;
    localparam [2:0] S_ERROR_WAIT = 3'd4;
    localparam [2:0] S_ERROR_OUT = 3'd5;

    reg [2:0] state;
    reg [CONFIG_WORDS*32-1:0] config_q;
    reg [767:0] base_q;
    reg [95:0] scale_q;
    reg scheduler_finished;
    reg [7:0] error_q;

    wire scheduler_start = state == S_LAUNCH;
    wire scheduler_tile_valid;
    wire scheduler_tile_ready;
    wire [1:0] scheduler_tile_kind;
    wire [31:0] scheduler_tile_token_base;
    wire [31:0] scheduler_tile_field_base;
    wire [31:0] scheduler_tile_k_base;
    wire [31:0] scheduler_tile_active_tokens;
    wire [31:0] scheduler_tile_active_fields;
    wire [31:0] scheduler_tile_active_k;
    wire [63:0] scheduler_tile_logical_work;
    wire [63:0] scheduler_tile_output_base;
    wire [31:0] scheduler_tile_output_row_stride;
    wire scheduler_tile_last;
    wire scheduler_busy;
    wire scheduler_done;
    wire [7:0] scheduler_error;

    wire first_tile_expected =
        (scheduler_tile_kind == 0) &&
        (scheduler_tile_token_base == 0) &&
        (scheduler_tile_field_base == 0) &&
        (scheduler_tile_k_base == 0) &&
        (scheduler_tile_active_tokens == 1) &&
        (scheduler_tile_active_fields != 0) &&
        (scheduler_tile_active_k != 0);

    wire projection_in_ready;
    wire projection_in_valid =
        state == S_WAIT_FIRST && scheduler_tile_valid &&
        first_tile_expected;
    assign scheduler_tile_ready =
        state == S_WAIT_FIRST ? (first_tile_expected && projection_in_ready) :
        state == S_RUN || state == S_ERROR_WAIT;

    ot_a3_vector_mhc_pre_tile_scheduler scheduler (
        .clk(clk),
        .rst_n(rst_n),
        .start(scheduler_start),
        .config_words(config_q),
        .tile_valid(scheduler_tile_valid),
        .tile_ready(scheduler_tile_ready),
        .tile_kind(scheduler_tile_kind),
        .tile_token_base(scheduler_tile_token_base),
        .tile_field_base(scheduler_tile_field_base),
        .tile_k_base(scheduler_tile_k_base),
        .tile_active_tokens(scheduler_tile_active_tokens),
        .tile_active_fields(scheduler_tile_active_fields),
        .tile_active_k(scheduler_tile_active_k),
        .tile_logical_work(scheduler_tile_logical_work),
        .tile_output_base(scheduler_tile_output_base),
        .tile_output_row_stride(scheduler_tile_output_row_stride),
        .tile_last(scheduler_tile_last),
        .busy(scheduler_busy),
        .done(scheduler_done),
        .error_code(scheduler_error),
        .projection_tile_count(scheduler_projection_tiles),
        .commit_tile_count(scheduler_commit_tiles),
        .logical_fma_count(scheduler_logical_fmas),
        .logical_output_count(scheduler_logical_outputs)
    );

    wire projection_out_valid;
    wire projection_out_ready;
    wire [31:0] projection_mean;
    wire [31:0] projection_inverse;
    wire [767:0] projection_raw;
    wire [767:0] projection_normalized;
    wire [1:0] projection_error;

    ot_a3_hc_projection_rms_rne projection_rms (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(projection_in_valid),
        .in_ready(projection_in_ready),
        .hidden_rd_en(hidden_rd_en),
        .hidden_rd_k(hidden_rd_k),
        .hidden_rd_data(hidden_rd_data),
        .weight_rd_en(weight_rd_en),
        .weight_rd_field_base(weight_rd_field_base),
        .weight_rd_k(weight_rd_k),
        .weight_rd_data(weight_rd_data),
        .out_valid(projection_out_valid),
        .out_ready(projection_out_ready),
        .mean_square_code(projection_mean),
        .inverse_rms_code(projection_inverse),
        .projection_codes(projection_raw),
        .normalized_projection_codes(projection_normalized),
        .result_error(projection_error),
        .square_count(arithmetic_square_count),
        .reduction_add_count(arithmetic_reduction_add_count),
        .fused_product_add_count(arithmetic_fma_count)
    );

    wire coefficient_in_ready;
    wire coefficient_in_valid =
        state == S_RUN && projection_out_valid && projection_error == 0;
    wire coefficient_out_valid;
    wire coefficient_out_ready;
    wire [255:0] coefficient_weights;
    wire [511:0] coefficient_combination;
    wire [1:0] coefficient_error;
    wire [31:0] coefficient_affine_count;
    wire [31:0] coefficient_sigmoid_count;

    assign projection_out_ready =
        state == S_RUN &&
        ((projection_error != 0) || coefficient_in_ready);

    ot_a3_hc_coefficients_rne coefficients (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(coefficient_in_valid),
        .in_ready(coefficient_in_ready),
        .normalized_projection_codes(projection_normalized),
        .base_codes(base_q),
        .scale_codes(scale_q),
        .out_valid(coefficient_out_valid),
        .out_ready(coefficient_out_ready),
        .weight_codes(coefficient_weights),
        .combination_codes(coefficient_combination),
        .result_error(coefficient_error),
        .affine_count(coefficient_affine_count),
        .sigmoid_count(coefficient_sigmoid_count)
    );

    wire success_out_valid =
        state == S_RUN && scheduler_finished && coefficient_out_valid &&
        coefficient_error == 0;
    // A failed private coefficient transaction is consumed when its error is
    // captured below; it must never wait on, or appear on, the public success
    // handshake.  A successful transaction remains stable until the scheduler
    // has also finished and the public consumer accepts it.
    assign coefficient_out_ready =
        state == S_RUN && coefficient_out_valid &&
        ((coefficient_error != 0) ||
         (scheduler_finished && out_ready));
    assign out_valid = success_out_valid || state == S_ERROR_OUT;
    assign result_error = state == S_ERROR_OUT ? error_q : 0;
    assign result_weight_codes =
        success_out_valid && coefficient_error == 0 ? coefficient_weights : 0;
    assign result_combination_codes =
        success_out_valid && coefficient_error == 0
            ? coefficient_combination : 0;
    assign in_ready = state == S_IDLE;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            config_q <= 0;
            base_q <= 0;
            scale_q <= 0;
            scheduler_finished <= 1'b0;
            error_q <= 0;
        end else begin
            case (state)
                S_IDLE: begin
                    if (in_valid && in_ready) begin
                        config_q <= config_words;
                        base_q <= base_codes;
                        scale_q <= scale_codes;
                        scheduler_finished <= 1'b0;
                        error_q <= 0;
                        if (config_words[32 +: 32] != 1) begin
                            error_q <= ERR_ACTIVE_TOKENS;
                            state <= S_ERROR_OUT;
                        end else begin
                            state <= S_LAUNCH;
                        end
                    end
                end

                S_LAUNCH: state <= S_WAIT_FIRST;

                S_WAIT_FIRST: begin
                    if (scheduler_done) begin
                        error_q <= scheduler_error != 0
                            ? scheduler_error : ERR_INTEGRATION;
                        state <= S_ERROR_OUT;
                    end else if (scheduler_tile_valid &&
                                 !first_tile_expected) begin
                        error_q <= ERR_INTEGRATION;
                        state <= S_ERROR_WAIT;
                    end else if (scheduler_tile_valid &&
                                 scheduler_tile_ready) begin
                        state <= S_RUN;
                    end
                end

                S_RUN: begin
                    if (scheduler_done && scheduler_error != 0) begin
                        error_q <= scheduler_error;
                        scheduler_finished <= 1'b1;
                        state <= S_ERROR_OUT;
                    end else begin
                        if (scheduler_done)
                            scheduler_finished <= 1'b1;
                        if (projection_out_valid &&
                            projection_error != 0) begin
                            error_q <= projection_error == 1
                                ? ERR_ARITHMETIC_ARGUMENT
                                : ERR_ARITHMETIC_RANGE;
                            if (scheduler_finished || scheduler_done)
                                state <= S_ERROR_OUT;
                            else
                                state <= S_ERROR_WAIT;
                        end else if (coefficient_out_valid &&
                                     coefficient_error != 0) begin
                            error_q <= coefficient_error == 1
                                ? ERR_ARITHMETIC_ARGUMENT
                                : ERR_ARITHMETIC_RANGE;
                            if (scheduler_finished || scheduler_done)
                                state <= S_ERROR_OUT;
                            else
                                state <= S_ERROR_WAIT;
                        end else if (success_out_valid && out_ready) begin
                            state <= S_IDLE;
                        end
                    end
                end

                S_ERROR_WAIT: begin
                    if (scheduler_done) begin
                        scheduler_finished <= 1'b1;
                        state <= S_ERROR_OUT;
                    end
                end

                S_ERROR_OUT: begin
                    if (out_ready) begin
                        config_q <= 0;
                        base_q <= 0;
                        scale_q <= 0;
                        scheduler_finished <= 1'b0;
                        error_q <= 0;
                        state <= S_IDLE;
                    end
                end

                default: begin
                    error_q <= ERR_INTEGRATION;
                    state <= S_ERROR_OUT;
                end
            endcase
        end
    end
endmodule
