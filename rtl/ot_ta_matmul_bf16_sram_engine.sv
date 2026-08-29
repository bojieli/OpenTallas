`timescale 1ns/1ps
// Bounded data-bearing execution of the first production Qwen q_proj output
// block.  Each MATMUL_BF16_TILE consumes [1,256] @ [64,256]^T.  Command 4
// initializes 64 raw binary32 accumulators, commands 6 through 32 reload and
// extend those accumulators, and command 34 reloads, extends, and finalizes the
// result to 64 BF16 auxiliary values.
//
// BF16 operands widen exactly.  Every product and every strictly increasing-K
// accumulation rounds once to binary32 RNE, and exact zero is canonicalized
// positive by the arithmetic package.  A non-init command reloads each FP32
// lane through two ordered 16-bit SRAM reads, low halfword first.  Complete
// arithmetic and, for MATMUL_FINAL, all BF16 conversions remain buffered until
// every numeric event succeeds.  A failing command therefore exposes neither
// a partial accumulator rewrite nor a partial auxiliary write.  A successful
// final command writes the complete FP32 accumulator tile before the BF16 tile,
// matching the production simulator's visible ordering.
//
// SRAM macros, ECC, arbitration, and response-error signaling remain external.
module ot_ta_matmul_bf16_sram_engine #(
    parameter [31:0] PROFILE_INPUT_ROWS = 32'd1,
    parameter [31:0] PROFILE_OUTPUTS = 32'd64,
    parameter [31:0] PROFILE_REDUCTION = 32'd256
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
    output wire [31:0]  sram_write_data,
    output wire [3:0]   sram_write_byte_enable,

    output reg          done_valid,
    input  wire         done_ready,
    output reg  [7:0]   done_error,
    output reg  [31:0]  done_command_index,
    output reg  [31:0]  done_accumulator_read_count,
    output reg  [31:0]  done_input_read_count,
    output reg  [31:0]  done_weight_read_count,
    output reg  [31:0]  done_multiply_count,
    output reg  [31:0]  done_add_count,
    output reg  [31:0]  done_output_count,
    output reg  [31:0]  done_accumulator_write_count,
    output reg  [31:0]  done_auxiliary_write_count,
    output reg  [31:0]  done_output_saturation_count
);
    localparam [7:0] OP_MATMUL = 8'h10;
    localparam [15:0] FLAG_MATMUL_INIT = 16'h0001;
    localparam [15:0] FLAG_MATMUL_FINAL = 16'h0002;
    localparam [7:0] ERR_NONE = 8'd0;
    localparam [7:0] ERR_UNSUPPORTED_OPCODE = 8'd7;
    localparam [7:0] ERR_PROFILE = 8'd8;
    localparam [7:0] ERR_OPERAND_NONFINITE = 8'd9;
    localparam [7:0] ERR_ARITHMETIC_OVERFLOW = 8'd10;
    localparam [1:0] FP_ERR_NONE = 2'd0;

    localparam [3:0] STATE_IDLE        = 4'd0;
    localparam [3:0] STATE_ACC_REQ     = 4'd1;
    localparam [3:0] STATE_ACC_WAIT    = 4'd2;
    localparam [3:0] STATE_INPUT_REQ   = 4'd3;
    localparam [3:0] STATE_INPUT_WAIT  = 4'd4;
    localparam [3:0] STATE_WEIGHT_REQ  = 4'd5;
    localparam [3:0] STATE_WEIGHT_WAIT = 4'd6;
    localparam [3:0] STATE_FINALIZE    = 4'd7;
    localparam [3:0] STATE_WRITE_ACC   = 4'd8;
    localparam [3:0] STATE_WRITE_AUX   = 4'd9;
    localparam [3:0] STATE_DONE        = 4'd10;

    localparam integer INPUT_ELEMENTS = 256;
    localparam integer OUTPUT_ELEMENTS = 64;
    localparam [63:0] MAX_INPUT_BASE = 64'hffff_ffff_ffff_fe00;
    localparam [63:0] MAX_WEIGHT_BASE = 64'hffff_ffff_ffff_8000;
    localparam [63:0] MAX_DESTINATION_BASE = 64'hffff_ffff_ffff_ff00;
    localparam [63:0] MAX_AUXILIARY_BASE = 64'hffff_ffff_ffff_ff80;
    localparam [7:0] LAST_INPUT = 8'hff;
    localparam [5:0] LAST_OUTPUT = 6'h3f;
    localparam [7:0] LAST_REDUCTION = 8'hff;

    reg [3:0] state;
    reg [15:0] input_buffer [0:INPUT_ELEMENTS-1];
    reg [31:0] accumulator_buffer [0:OUTPUT_ELEMENTS-1];
    reg [15:0] auxiliary_buffer [0:OUTPUT_ELEMENTS-1];
    reg [7:0] input_index;
    reg [5:0] output_index;
    reg [7:0] reduction_index;
    reg accumulator_half;
    reg command_is_init;
    reg command_is_final;
    reg [63:0] input_base;
    reg [63:0] weight_base;
    reg [63:0] destination_base;
    reg [63:0] auxiliary_base;

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

    wire command_index_legal =
        (decoder_index >= 32'd4) &&
        (decoder_index <= 32'd34) &&
        !decoder_index[0];
    wire command_flags_legal =
        ((decoder_index == 32'd4) &&
         (decoder_flags == FLAG_MATMUL_INIT)) ||
        ((decoder_index > 32'd4) && (decoder_index < 32'd34) &&
         !decoder_index[0] && (decoder_flags == 16'b0)) ||
        ((decoder_index == 32'd34) &&
         (decoder_flags == FLAG_MATMUL_FINAL));
    wire command_profile_legal =
        (PROFILE_INPUT_ROWS == 32'd1) &&
        (PROFILE_OUTPUTS == 32'd64) &&
        (PROFILE_REDUCTION == 32'd256) &&
        command_index_legal &&
        command_flags_legal &&
        (decoder_kernel_index == 32'd2) &&
        (decoder_size0 == PROFILE_INPUT_ROWS) &&
        (decoder_size1 == PROFILE_OUTPUTS) &&
        (decoder_size2 == PROFILE_REDUCTION) &&
        (decoder_size3 == 0) &&
        (decoder_source0[0] == 1'b0) &&
        (decoder_source1[0] == 1'b0) &&
        (decoder_destination[1:0] == 2'b00) &&
        (decoder_auxiliary[0] == 1'b0) &&
        (decoder_auxiliary != 0) &&
        (decoder_source0 <= MAX_INPUT_BASE) &&
        (decoder_source1 <= MAX_WEIGHT_BASE) &&
        (decoder_destination <= MAX_DESTINATION_BASE) &&
        (decoder_auxiliary <= MAX_AUXILIARY_BASE);

    wire read_request_state =
        (state == STATE_ACC_REQ) ||
        (state == STATE_INPUT_REQ) ||
        (state == STATE_WEIGHT_REQ);
    wire read_request_fire = sram_read_valid && sram_read_ready;
    wire read_response_fire = sram_response_valid && sram_response_ready;
    wire write_fire = sram_write_valid && sram_write_ready;
    wire [63:0] input_byte_offset = {55'b0, input_index, 1'b0};
    wire [63:0] weight_byte_offset = {
        49'b0, output_index, reduction_index, 1'b0
    };
    wire [63:0] accumulator_byte_offset = {56'b0, output_index, 2'b00};
    wire [63:0] accumulator_half_offset = {
        62'b0, accumulator_half, 1'b0
    };
    wire [63:0] auxiliary_byte_offset = {57'b0, output_index, 1'b0};

    assign cmd_ready = decoder_in_ready && (state == STATE_IDLE) &&
                       !done_valid;
    assign sram_read_valid = read_request_state;
    assign sram_read_address = state == STATE_ACC_REQ
                               ? destination_base + accumulator_byte_offset +
                                 accumulator_half_offset
                               : state == STATE_WEIGHT_REQ
                                 ? weight_base + weight_byte_offset
                                 : input_base + input_byte_offset;
    assign sram_response_ready =
        (state == STATE_ACC_WAIT) ||
        (state == STATE_INPUT_WAIT) ||
        (state == STATE_WEIGHT_WAIT);
    assign sram_write_valid =
        (state == STATE_WRITE_ACC) || (state == STATE_WRITE_AUX);
    assign sram_write_address = state == STATE_WRITE_AUX
                                ? auxiliary_base + auxiliary_byte_offset
                                : destination_base + accumulator_byte_offset;
    assign sram_write_data = state == STATE_WRITE_AUX
                             ? {16'b0, auxiliary_buffer[output_index]}
                             : accumulator_buffer[output_index];
    assign sram_write_byte_enable = state == STATE_WRITE_AUX ? 4'h3 : 4'hf;

    wire response_bf16_nonfinite =
        sram_response_data[14:7] == 8'hff;
    wire [31:0] reload_accumulator_code = {
        sram_response_data, accumulator_buffer[output_index][15:0]
    };
    wire reload_accumulator_nonfinite =
        reload_accumulator_code[30:23] == 8'hff;
    wire [31:0] compute_input_code = {
        input_buffer[reduction_index], 16'b0
    };
    wire [31:0] compute_weight_code = {
        sram_response_data, 16'b0
    };
    wire [31:0] compute_accumulator_code =
        command_is_init && (reduction_index == 0)
        ? 32'b0 : accumulator_buffer[output_index];
    wire [33:0] compute_product = ot_fp32_rne_pkg::fp32_mul_rne(
        compute_input_code, compute_weight_code
    );
    wire [33:0] compute_sum = ot_fp32_rne_pkg::fp32_add_rne(
        compute_accumulator_code, compute_product[31:0]
    );
    wire [18:0] finalize_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(
        accumulator_buffer[output_index]
    );

    ot_ta_command_decoder decoder (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(cmd_valid && (state == STATE_IDLE) && !done_valid),
        .in_ready(decoder_in_ready),
        .abi_major(abi_major),
        .abi_minor(abi_minor),
        .expected_index(expected_command_index),
        .command_record(command_record),
        .out_valid(decoder_out_valid),
        .out_ready(decoder_out_ready),
        .out_legal(decoder_out_legal),
        .out_error(decoder_out_error),
        .out_opcode(decoder_opcode),
        .out_engine(decoder_unused_engine),
        .out_flags(decoder_flags),
        .out_index(decoder_index),
        .out_kernel_index(decoder_kernel_index),
        .out_source0(decoder_source0),
        .out_source1(decoder_source1),
        .out_destination(decoder_destination),
        .out_auxiliary(decoder_auxiliary),
        .out_size0(decoder_size0),
        .out_size1(decoder_size1),
        .out_size2(decoder_size2),
        .out_size3(decoder_size3)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= STATE_IDLE;
            input_index <= 0;
            output_index <= 0;
            reduction_index <= 0;
            accumulator_half <= 0;
            command_is_init <= 0;
            command_is_final <= 0;
            input_base <= 0;
            weight_base <= 0;
            destination_base <= 0;
            auxiliary_base <= 0;
            done_valid <= 1'b0;
            done_error <= ERR_NONE;
            done_command_index <= 0;
            done_accumulator_read_count <= 0;
            done_input_read_count <= 0;
            done_weight_read_count <= 0;
            done_multiply_count <= 0;
            done_add_count <= 0;
            done_output_count <= 0;
            done_accumulator_write_count <= 0;
            done_auxiliary_write_count <= 0;
            done_output_saturation_count <= 0;
        end else begin
            if (done_valid && done_ready) begin
                done_valid <= 1'b0;
                state <= STATE_IDLE;
            end

            if (decoder_out_valid && decoder_out_ready) begin
                done_command_index <= decoder_index;
                done_accumulator_read_count <= 0;
                done_input_read_count <= 0;
                done_weight_read_count <= 0;
                done_multiply_count <= 0;
                done_add_count <= 0;
                done_output_count <= 0;
                done_accumulator_write_count <= 0;
                done_auxiliary_write_count <= 0;
                done_output_saturation_count <= 0;
                if (!decoder_out_legal) begin
                    done_valid <= 1'b1;
                    done_error <= {4'b0, decoder_out_error};
                    state <= STATE_DONE;
                end else if (decoder_opcode != OP_MATMUL) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_UNSUPPORTED_OPCODE;
                    state <= STATE_DONE;
                end else if (!command_profile_legal) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_PROFILE;
                    state <= STATE_DONE;
                end else begin
                    done_error <= ERR_NONE;
                    input_index <= 0;
                    output_index <= 0;
                    reduction_index <= 0;
                    accumulator_half <= 0;
                    command_is_init <=
                        decoder_flags == FLAG_MATMUL_INIT;
                    command_is_final <=
                        decoder_flags == FLAG_MATMUL_FINAL;
                    input_base <= decoder_source0;
                    weight_base <= decoder_source1;
                    destination_base <= decoder_destination;
                    auxiliary_base <= decoder_auxiliary;
                    state <= decoder_flags == FLAG_MATMUL_INIT
                             ? STATE_INPUT_REQ : STATE_ACC_REQ;
                end
            end

            if (read_request_fire) begin
                if (state == STATE_ACC_REQ)
                    state <= STATE_ACC_WAIT;
                else if (state == STATE_INPUT_REQ)
                    state <= STATE_INPUT_WAIT;
                else
                    state <= STATE_WEIGHT_WAIT;
            end

            if (read_response_fire && state == STATE_ACC_WAIT) begin
                done_accumulator_read_count <=
                    done_accumulator_read_count + 1'b1;
                if (!accumulator_half) begin
                    accumulator_buffer[output_index][15:0] <=
                        sram_response_data;
                    accumulator_half <= 1'b1;
                    state <= STATE_ACC_REQ;
                end else if (reload_accumulator_nonfinite) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_OPERAND_NONFINITE;
                    state <= STATE_DONE;
                end else begin
                    accumulator_buffer[output_index] <=
                        reload_accumulator_code;
                    accumulator_half <= 1'b0;
                    if (output_index == LAST_OUTPUT) begin
                        output_index <= 0;
                        input_index <= 0;
                        state <= STATE_INPUT_REQ;
                    end else begin
                        output_index <= output_index + 1'b1;
                        state <= STATE_ACC_REQ;
                    end
                end
            end

            if (read_response_fire && state == STATE_INPUT_WAIT) begin
                done_input_read_count <= done_input_read_count + 1'b1;
                if (response_bf16_nonfinite) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_OPERAND_NONFINITE;
                    state <= STATE_DONE;
                end else begin
                    input_buffer[input_index] <= sram_response_data;
                    if (input_index == LAST_INPUT) begin
                        output_index <= 0;
                        reduction_index <= 0;
                        state <= STATE_WEIGHT_REQ;
                    end else begin
                        input_index <= input_index + 1'b1;
                        state <= STATE_INPUT_REQ;
                    end
                end
            end

            if (read_response_fire && state == STATE_WEIGHT_WAIT) begin
                done_weight_read_count <= done_weight_read_count + 1'b1;
                if (response_bf16_nonfinite) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_OPERAND_NONFINITE;
                    state <= STATE_DONE;
                end else if (compute_product[33:32] != FP_ERR_NONE ||
                             compute_sum[33:32] != FP_ERR_NONE) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_ARITHMETIC_OVERFLOW;
                    state <= STATE_DONE;
                end else begin
                    accumulator_buffer[output_index] <= compute_sum[31:0];
                    done_multiply_count <= done_multiply_count + 1'b1;
                    done_add_count <= done_add_count + 1'b1;
                    if (reduction_index == LAST_REDUCTION) begin
                        reduction_index <= 0;
                        if (output_index == LAST_OUTPUT) begin
                            output_index <= 0;
                            state <= command_is_final
                                     ? STATE_FINALIZE : STATE_WRITE_ACC;
                        end else begin
                            output_index <= output_index + 1'b1;
                            state <= STATE_WEIGHT_REQ;
                        end
                    end else begin
                        reduction_index <= reduction_index + 1'b1;
                        state <= STATE_WEIGHT_REQ;
                    end
                end
            end

            if (state == STATE_FINALIZE) begin
                if (finalize_bf16[18:17] != FP_ERR_NONE) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_OPERAND_NONFINITE;
                    state <= STATE_DONE;
                end else begin
                    auxiliary_buffer[output_index] <= finalize_bf16[15:0];
                    if (finalize_bf16[16])
                        done_output_saturation_count <=
                            done_output_saturation_count + 1'b1;
                    if (output_index == LAST_OUTPUT) begin
                        output_index <= 0;
                        state <= STATE_WRITE_ACC;
                    end else begin
                        output_index <= output_index + 1'b1;
                    end
                end
            end

            if (write_fire && state == STATE_WRITE_ACC) begin
                done_output_count <= done_output_count + 1'b1;
                done_accumulator_write_count <=
                    done_accumulator_write_count + 1'b1;
                if (output_index == LAST_OUTPUT) begin
                    output_index <= 0;
                    if (command_is_final) begin
                        state <= STATE_WRITE_AUX;
                    end else begin
                        done_valid <= 1'b1;
                        done_error <= ERR_NONE;
                        state <= STATE_DONE;
                    end
                end else begin
                    output_index <= output_index + 1'b1;
                end
            end

            if (write_fire && state == STATE_WRITE_AUX) begin
                done_auxiliary_write_count <=
                    done_auxiliary_write_count + 1'b1;
                if (output_index == LAST_OUTPUT) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_NONE;
                    state <= STATE_DONE;
                end else begin
                    output_index <= output_index + 1'b1;
                end
            end
        end
    end

    wire _unused_decoder = &{1'b0, decoder_unused_engine};
endmodule
