`timescale 1ns/1ps
// Bounded data-bearing execution of the production 128-wide per-head
// RMSNORM_BF16 profile used by Qwen Q and K normalization.  Every row has an
// independent balanced binary32 reduction, correctly rounded reciprocal square
// root, BF16-normalized boundary, and BF16-weighted result.  The complete
// multi-row output is buffered before the first SRAM write, so a fault in any
// row cannot leave a partial destination update.
//
// This is a source-profiled functional slice.  SRAM macros, ECC, banking,
// arbitration, and response-error signaling remain external.
module ot_ta_head_rmsnorm_bf16_sram_engine #(
    parameter [31:0] PROFILE_WIDTH = 32'd128,
    parameter [31:0] PROFILE_MAX_ROWS = 32'd32,
    parameter [31:0] PROFILE_COMMAND0_INDEX = 32'd3076,
    parameter [31:0] PROFILE_KERNEL0_INDEX = 32'd5,
    parameter [31:0] PROFILE_ROWS0 = 32'd32,
    parameter [31:0] PROFILE_COMMAND1_INDEX = 32'd3078,
    parameter [31:0] PROFILE_KERNEL1_INDEX = 32'd6,
    parameter [31:0] PROFILE_ROWS1 = 32'd8
) (
    input  wire         clk,
    input  wire         rst_n,

    input  wire         cmd_valid,
    output wire         cmd_ready,
    input  wire [15:0]  abi_major,
    input  wire [15:0]  abi_minor,
    input  wire [31:0]  expected_command_index,
    input  wire [511:0] command_record,

    output wire         sram_read_valid,
    input  wire         sram_read_ready,
    output wire [63:0]  sram_read_address,
    input  wire         sram_response_valid,
    output wire         sram_response_ready,
    input  wire [15:0]  sram_response_data,

    output wire         sram_write_valid,
    input  wire         sram_write_ready,
    output wire [63:0]  sram_write_address,
    output wire [15:0]  sram_write_data,
    output wire [1:0]   sram_write_byte_enable,

    output reg          done_valid,
    input  wire         done_ready,
    output reg  [7:0]   done_error,
    output reg  [31:0]  done_command_index,
    output reg  [31:0]  done_row_count,
    output reg  [31:0]  done_element_count,
    output reg  [31:0]  done_normalized_saturation_count,
    output reg  [31:0]  done_output_saturation_count,
    output reg  [31:0]  done_sram_input_read_count,
    output reg  [31:0]  done_sram_weight_read_count,
    output reg  [31:0]  done_sram_write_count,
    output reg  [31:0]  done_mean_square_code,
    output reg  [31:0]  done_inverse_rms_code
);
    localparam [7:0] OP_RMSNORM = 8'h20;
    localparam [7:0] ERR_NONE = 8'd0;
    localparam [7:0] ERR_UNSUPPORTED_OPCODE = 8'd7;
    localparam [7:0] ERR_PROFILE = 8'd8;
    localparam [7:0] ERR_OPERAND_NONFINITE = 8'd9;
    localparam [7:0] ERR_ARITHMETIC_OVERFLOW = 8'd10;
    localparam [1:0] FP_ERR_NONE = 2'd0;

    localparam [3:0] STATE_IDLE         = 4'd0;
    localparam [3:0] STATE_INPUT_REQ    = 4'd1;
    localparam [3:0] STATE_INPUT_WAIT   = 4'd2;
    localparam [3:0] STATE_REDUCE       = 4'd3;
    localparam [3:0] STATE_MEAN         = 4'd4;
    localparam [3:0] STATE_EPSILON      = 4'd5;
    localparam [3:0] STATE_RSQRT_REQ    = 4'd6;
    localparam [3:0] STATE_RSQRT_WAIT   = 4'd7;
    localparam [3:0] STATE_WEIGHT_REQ   = 4'd8;
    localparam [3:0] STATE_WEIGHT_WAIT  = 4'd9;
    localparam [3:0] STATE_WRITE        = 4'd10;
    localparam [3:0] STATE_DONE         = 4'd11;

    localparam integer BUFFER_ELEMENTS = 4096;
    localparam integer REDUCTION_ELEMENTS = 128;
    localparam [31:0] MEAN_SCALE_CODE = 32'h3c00_0000;
    localparam [63:0] MAX_VECTOR_BASE = 64'hffff_ffff_ffff_e000;
    localparam [63:0] MAX_WEIGHT_BASE = 64'hffff_ffff_ffff_ff00;
    localparam [6:0] LAST_COLUMN = 7'd127;

    reg [3:0] state;
    reg [15:0] input_buffer [0:BUFFER_ELEMENTS-1];
    reg [15:0] output_buffer [0:BUFFER_ELEMENTS-1];
    reg [31:0] reduction_buffer [0:REDUCTION_ELEMENTS-1];
    reg [11:0] element_index;
    reg [6:0] column_index;
    reg [6:0] reduction_pair_index;
    reg [7:0] reduction_count;
    reg [4:0] row_index;
    reg [5:0] row_count;
    reg [63:0] input_base;
    reg [63:0] weight_base;
    reg [63:0] destination_base;
    reg [31:0] epsilon_code;
    reg [31:0] mean_square_code;
    reg [31:0] inverse_rms_code;

    wire decoder_in_ready;
    wire decoder_out_valid;
    wire decoder_out_legal;
    wire [3:0] decoder_out_error;
    wire [7:0] decoder_opcode;
    wire [7:0] decoder_unused_engine;
    wire [15:0] decoder_flags;
    wire [31:0] decoder_index;
    wire [31:0] decoder_kernel_index;
    wire [63:0] decoder_source0;
    wire [63:0] decoder_source1;
    wire [63:0] decoder_destination;
    wire [63:0] decoder_auxiliary;
    wire [31:0] decoder_size0;
    wire [31:0] decoder_size1;
    wire [31:0] decoder_size2;
    wire [31:0] decoder_size3;
    wire decoder_out_ready = (state == STATE_IDLE) && !done_valid;

    wire profile_command0 = decoder_index == PROFILE_COMMAND0_INDEX;
    wire profile_command1 = decoder_index == PROFILE_COMMAND1_INDEX;
    wire [31:0] profile_kernel_index = profile_command0
        ? PROFILE_KERNEL0_INDEX : PROFILE_KERNEL1_INDEX;
    wire [31:0] profile_rows = profile_command0
        ? PROFILE_ROWS0 : PROFILE_ROWS1;
    wire static_profile_legal =
        (PROFILE_WIDTH == 32'd128) &&
        (PROFILE_MAX_ROWS == 32'd32) &&
        (PROFILE_ROWS0 > 0) &&
        (PROFILE_ROWS0 <= PROFILE_MAX_ROWS) &&
        (PROFILE_ROWS1 > 0) &&
        (PROFILE_ROWS1 <= PROFILE_MAX_ROWS) &&
        (PROFILE_COMMAND1_INDEX > PROFILE_COMMAND0_INDEX);
    wire command_profile_legal =
        static_profile_legal &&
        (profile_command0 || profile_command1) &&
        (decoder_kernel_index == profile_kernel_index) &&
        (decoder_flags == 0) &&
        (decoder_auxiliary == 0) &&
        (decoder_size0 == profile_rows) &&
        (decoder_size1 == PROFILE_WIDTH) &&
        (decoder_size2[31] == 1'b0) &&
        (decoder_size2[30:23] != 8'hff) &&
        (decoder_size2[30:0] != 0) &&
        (decoder_size3 == 0) &&
        (decoder_source0[0] == 1'b0) &&
        (decoder_source1[0] == 1'b0) &&
        (decoder_destination[0] == 1'b0) &&
        (decoder_source0 <= MAX_VECTOR_BASE) &&
        (decoder_source1 <= MAX_WEIGHT_BASE) &&
        (decoder_destination <= MAX_VECTOR_BASE);

    wire read_request_state = (state == STATE_INPUT_REQ) ||
                              (state == STATE_WEIGHT_REQ);
    wire read_request_fire = sram_read_valid && sram_read_ready;
    wire read_response_fire = sram_response_valid && sram_response_ready;
    wire write_fire = sram_write_valid && sram_write_ready;
    wire [63:0] element_byte_offset = {51'b0, element_index, 1'b0};
    wire [63:0] weight_byte_offset = {56'b0, column_index, 1'b0};
    wire [12:0] total_elements = {row_count, 7'b0};
    wire [11:0] last_element_index = total_elements[11:0] - 1'b1;

    assign cmd_ready = decoder_in_ready && (state == STATE_IDLE) && !done_valid;
    assign sram_read_valid = read_request_state;
    assign sram_read_address = state == STATE_WEIGHT_REQ
        ? weight_base + weight_byte_offset
        : input_base + element_byte_offset;
    assign sram_response_ready = (state == STATE_INPUT_WAIT) ||
                                 (state == STATE_WEIGHT_WAIT);
    assign sram_write_valid = state == STATE_WRITE;
    assign sram_write_address = destination_base + element_byte_offset;
    assign sram_write_data = output_buffer[element_index];
    assign sram_write_byte_enable = 2'b11;

    wire response_bf16_nonfinite = sram_response_data[14:7] == 8'hff;
    wire [31:0] input_fp32_code = {input_buffer[element_index], 16'b0};
    wire [31:0] response_fp32_code = {sram_response_data, 16'b0};
    wire [33:0] input_square = ot_fp32_rne_pkg::fp32_mul_rne(
        response_fp32_code, response_fp32_code
    );
    wire [6:0] reduction_left_index = reduction_pair_index << 1;
    wire [6:0] reduction_right_index = reduction_left_index + 1'b1;
    wire [33:0] reduction_add = ot_fp32_rne_pkg::fp32_add_positive_rne(
        reduction_buffer[reduction_left_index],
        reduction_buffer[reduction_right_index]
    );
    wire [33:0] mean_scale = ot_fp32_rne_pkg::fp32_mul_rne(
        reduction_buffer[0], MEAN_SCALE_CODE
    );
    wire [33:0] epsilon_add = ot_fp32_rne_pkg::fp32_add_positive_rne(
        mean_square_code, epsilon_code
    );
    wire [33:0] normalized_product = ot_fp32_rne_pkg::fp32_mul_rne(
        input_fp32_code, inverse_rms_code
    );
    wire [18:0] normalized_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(
        normalized_product[31:0]
    );
    wire [31:0] normalized_fp32_code = {normalized_bf16[15:0], 16'b0};
    wire [33:0] weighted_product = ot_fp32_rne_pkg::fp32_mul_rne(
        normalized_fp32_code, response_fp32_code
    );
    wire [18:0] output_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(
        weighted_product[31:0]
    );

    wire rsqrt_in_valid = state == STATE_RSQRT_REQ;
    wire rsqrt_in_ready;
    wire rsqrt_out_valid;
    wire rsqrt_out_ready = state == STATE_RSQRT_WAIT;
    wire [31:0] rsqrt_result_code;
    wire [1:0] rsqrt_result_error;

    ot_ta_command_decoder decoder (
        .clk(clk), .rst_n(rst_n),
        .in_valid(cmd_valid && (state == STATE_IDLE) && !done_valid),
        .in_ready(decoder_in_ready),
        .abi_major(abi_major), .abi_minor(abi_minor),
        .expected_index(expected_command_index),
        .command_record(command_record),
        .out_valid(decoder_out_valid), .out_ready(decoder_out_ready),
        .out_legal(decoder_out_legal), .out_error(decoder_out_error),
        .out_opcode(decoder_opcode), .out_engine(decoder_unused_engine),
        .out_flags(decoder_flags), .out_index(decoder_index),
        .out_kernel_index(decoder_kernel_index), .out_source0(decoder_source0),
        .out_source1(decoder_source1), .out_destination(decoder_destination),
        .out_auxiliary(decoder_auxiliary), .out_size0(decoder_size0),
        .out_size1(decoder_size1), .out_size2(decoder_size2),
        .out_size3(decoder_size3)
    );

    ot_fp32_rsqrt_rne rsqrt (
        .clk(clk), .rst_n(rst_n), .in_valid(rsqrt_in_valid),
        .in_ready(rsqrt_in_ready), .argument_code(epsilon_add[31:0]),
        .out_valid(rsqrt_out_valid), .out_ready(rsqrt_out_ready),
        .result_code(rsqrt_result_code), .result_error(rsqrt_result_error)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= STATE_IDLE;
            element_index <= 0;
            column_index <= 0;
            reduction_pair_index <= 0;
            reduction_count <= 0;
            row_index <= 0;
            row_count <= 0;
            input_base <= 0;
            weight_base <= 0;
            destination_base <= 0;
            epsilon_code <= 0;
            mean_square_code <= 0;
            inverse_rms_code <= 0;
            done_valid <= 1'b0;
            done_error <= ERR_NONE;
            done_command_index <= 0;
            done_row_count <= 0;
            done_element_count <= 0;
            done_normalized_saturation_count <= 0;
            done_output_saturation_count <= 0;
            done_sram_input_read_count <= 0;
            done_sram_weight_read_count <= 0;
            done_sram_write_count <= 0;
            done_mean_square_code <= 0;
            done_inverse_rms_code <= 0;
        end else begin
            if (done_valid && done_ready) begin
                done_valid <= 1'b0;
                state <= STATE_IDLE;
            end

            if (decoder_out_valid && decoder_out_ready) begin
                done_command_index <= decoder_index;
                done_row_count <= 0;
                done_element_count <= 0;
                done_normalized_saturation_count <= 0;
                done_output_saturation_count <= 0;
                done_sram_input_read_count <= 0;
                done_sram_weight_read_count <= 0;
                done_sram_write_count <= 0;
                done_mean_square_code <= 0;
                done_inverse_rms_code <= 0;
                mean_square_code <= 0;
                inverse_rms_code <= 0;
                if (!decoder_out_legal) begin
                    done_valid <= 1'b1;
                    done_error <= {4'b0, decoder_out_error};
                    state <= STATE_DONE;
                end else if (decoder_opcode != OP_RMSNORM) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_UNSUPPORTED_OPCODE;
                    state <= STATE_DONE;
                end else if (!command_profile_legal) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_PROFILE;
                    state <= STATE_DONE;
                end else begin
                    done_error <= ERR_NONE;
                    element_index <= 0;
                    column_index <= 0;
                    reduction_pair_index <= 0;
                    reduction_count <= PROFILE_WIDTH[7:0];
                    row_index <= 0;
                    row_count <= profile_rows[5:0];
                    input_base <= decoder_source0;
                    weight_base <= decoder_source1;
                    destination_base <= decoder_destination;
                    epsilon_code <= decoder_size2;
                    state <= STATE_INPUT_REQ;
                end
            end

            if (read_request_fire) begin
                if (state == STATE_INPUT_REQ)
                    state <= STATE_INPUT_WAIT;
                else if (state == STATE_WEIGHT_REQ)
                    state <= STATE_WEIGHT_WAIT;
            end

            if (read_response_fire && state == STATE_INPUT_WAIT) begin
                done_sram_input_read_count <=
                    done_sram_input_read_count + 1'b1;
                done_element_count <= done_element_count + 1'b1;
                if (response_bf16_nonfinite) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_OPERAND_NONFINITE;
                    state <= STATE_DONE;
                end else if (input_square[33:32] != FP_ERR_NONE) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_ARITHMETIC_OVERFLOW;
                    state <= STATE_DONE;
                end else begin
                    input_buffer[element_index] <= sram_response_data;
                    reduction_buffer[column_index] <= input_square[31:0];
                    if (column_index == LAST_COLUMN) begin
                        reduction_pair_index <= 0;
                        reduction_count <= PROFILE_WIDTH[7:0];
                        state <= STATE_REDUCE;
                    end else begin
                        element_index <= element_index + 1'b1;
                        column_index <= column_index + 1'b1;
                        state <= STATE_INPUT_REQ;
                    end
                end
            end

            if (state == STATE_REDUCE) begin
                if (reduction_add[33:32] != FP_ERR_NONE) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_ARITHMETIC_OVERFLOW;
                    state <= STATE_DONE;
                end else begin
                    reduction_buffer[reduction_pair_index] <=
                        reduction_add[31:0];
                    if ({1'b0, reduction_pair_index} + 1'b1 ==
                        (reduction_count >> 1)) begin
                        reduction_pair_index <= 0;
                        reduction_count <= reduction_count >> 1;
                        if ((reduction_count >> 1) == 1)
                            state <= STATE_MEAN;
                    end else begin
                        reduction_pair_index <= reduction_pair_index + 1'b1;
                    end
                end
            end

            if (state == STATE_MEAN) begin
                if (mean_scale[33:32] != FP_ERR_NONE) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_ARITHMETIC_OVERFLOW;
                    state <= STATE_DONE;
                end else begin
                    mean_square_code <= mean_scale[31:0];
                    done_mean_square_code <= mean_scale[31:0];
                    state <= STATE_EPSILON;
                end
            end

            if (state == STATE_EPSILON) begin
                if (epsilon_add[33:32] != FP_ERR_NONE ||
                    epsilon_add[30:0] == 0) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_ARITHMETIC_OVERFLOW;
                    state <= STATE_DONE;
                end else begin
                    state <= STATE_RSQRT_REQ;
                end
            end

            if (state == STATE_RSQRT_REQ && rsqrt_in_ready)
                state <= STATE_RSQRT_WAIT;

            if (state == STATE_RSQRT_WAIT && rsqrt_out_valid) begin
                if (rsqrt_result_error != FP_ERR_NONE) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_ARITHMETIC_OVERFLOW;
                    state <= STATE_DONE;
                end else begin
                    inverse_rms_code <= rsqrt_result_code;
                    done_inverse_rms_code <= rsqrt_result_code;
                    element_index <= {row_index, 7'b0};
                    column_index <= 0;
                    state <= STATE_WEIGHT_REQ;
                end
            end

            if (read_response_fire && state == STATE_WEIGHT_WAIT) begin
                done_sram_weight_read_count <=
                    done_sram_weight_read_count + 1'b1;
                if (response_bf16_nonfinite) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_OPERAND_NONFINITE;
                    state <= STATE_DONE;
                end else if (normalized_product[33:32] != FP_ERR_NONE ||
                             normalized_bf16[18:17] != FP_ERR_NONE ||
                             weighted_product[33:32] != FP_ERR_NONE ||
                             output_bf16[18:17] != FP_ERR_NONE) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_ARITHMETIC_OVERFLOW;
                    state <= STATE_DONE;
                end else begin
                    output_buffer[element_index] <= output_bf16[15:0];
                    if (normalized_bf16[16])
                        done_normalized_saturation_count <=
                            done_normalized_saturation_count + 1'b1;
                    if (output_bf16[16])
                        done_output_saturation_count <=
                            done_output_saturation_count + 1'b1;
                    if (column_index == LAST_COLUMN) begin
                        if ({1'b0, row_index} + 1'b1 == row_count) begin
                            done_row_count <= {26'b0, row_count};
                            element_index <= 0;
                            state <= STATE_WRITE;
                        end else begin
                            row_index <= row_index + 1'b1;
                            element_index <= element_index + 1'b1;
                            column_index <= 0;
                            reduction_pair_index <= 0;
                            reduction_count <= PROFILE_WIDTH[7:0];
                            state <= STATE_INPUT_REQ;
                        end
                    end else begin
                        element_index <= element_index + 1'b1;
                        column_index <= column_index + 1'b1;
                        state <= STATE_WEIGHT_REQ;
                    end
                end
            end

            if (write_fire) begin
                done_sram_write_count <= done_sram_write_count + 1'b1;
                if (element_index == last_element_index) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_NONE;
                    done_element_count <= {19'b0, total_elements};
                    state <= STATE_DONE;
                end else begin
                    element_index <= element_index + 1'b1;
                end
            end
        end
    end

    wire _unused_decoder = &{1'b0, decoder_unused_engine};
endmodule
