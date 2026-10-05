`timescale 1ns/1ps
// Bounded data-bearing execution of the Qwen ROPE_BF16 profile.  One selected
// coefficient row is consumed as cos[128] followed by sin[128].  Each direct
// and rotated binary32 product rounds independently to BF16, their decoded BF16
// values add in binary32, and the sum rounds once more to BF16.  The half-vector
// transform is concat(-second_half, first_half), with signed zero canonicalized.
//
// All 5,120 Q/K results are validated and buffered before the first destination
// write, so any operand or arithmetic fault preserves both output regions.
// Physical SRAM, ECC, banking, arbitration, and response-error signaling remain
// external to this functional command boundary.
module ot_ta_rope_bf16_sram_engine #(
    parameter [31:0] PROFILE_COMMAND_INDEX = 32'd3080,
    parameter [31:0] PROFILE_KERNEL_INDEX = 32'd7,
    parameter [31:0] PROFILE_QUERY_HEADS = 32'd32,
    parameter [31:0] PROFILE_KEY_HEADS = 32'd8,
    parameter [31:0] PROFILE_HEAD_WIDTH = 32'd128
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
    output reg  [31:0]  done_coefficient_read_count,
    output reg  [31:0]  done_query_read_count,
    output reg  [31:0]  done_key_read_count,
    output reg  [31:0]  done_output_write_count,
    output reg  [31:0]  done_element_count,
    output reg  [31:0]  done_multiplication_count,
    output reg  [31:0]  done_addition_count,
    output reg  [31:0]  done_multiplication_saturation_count,
    output reg  [31:0]  done_addition_saturation_count
);
    localparam [7:0] OP_ROPE = 8'h21;
    localparam [7:0] ERR_NONE = 8'd0;
    localparam [7:0] ERR_UNSUPPORTED_OPCODE = 8'd7;
    localparam [7:0] ERR_PROFILE = 8'd8;
    localparam [7:0] ERR_OPERAND_NONFINITE = 8'd9;
    localparam [7:0] ERR_ARITHMETIC_OVERFLOW = 8'd10;
    localparam [1:0] FP_ERR_NONE = 2'd0;

    //: GEOMETRY.  These nine were Qwen3-8B constants -- 256, 128, 4096, 1024,
    //: 5120 and their last indices -- which is why the profile check below had
    //: to pin the parameters that were supposed to set them.  Every one is an
    //: identity over (query heads, key heads, head width), so state the
    //: identities and let the parameters mean something.  At the default
    //: 32/8/128 each expression reproduces the constant it replaced.
    localparam integer HEAD_ELEMENTS = PROFILE_HEAD_WIDTH;
    localparam integer HALF_HEAD = HEAD_ELEMENTS / 2;
    localparam integer COEFFICIENT_ELEMENTS = 2 * HEAD_ELEMENTS;
    localparam integer QUERY_ELEMENTS = PROFILE_QUERY_HEADS * HEAD_ELEMENTS;
    localparam integer KEY_ELEMENTS = PROFILE_KEY_HEADS * HEAD_ELEMENTS;
    localparam integer OUTPUT_ELEMENTS = QUERY_ELEMENTS + KEY_ELEMENTS;
    localparam integer TOTAL_HEADS = PROFILE_QUERY_HEADS + PROFILE_KEY_HEADS;

    //: Index widths, sized to the geometry rather than written down.  At
    //: 32/8/128 these are 8, 7, 6 and 13 -- the widths the registers had.
    localparam integer CIW = $clog2(COEFFICIENT_ELEMENTS);
    localparam integer CLW = $clog2(HEAD_ELEMENTS);
    localparam integer HIW = $clog2(TOTAL_HEADS);
    localparam integer OIW = $clog2(OUTPUT_ELEMENTS);

    localparam [CIW-1:0] LAST_COEFFICIENT_INDEX = COEFFICIENT_ELEMENTS - 1;
    localparam [CLW-1:0] LAST_COLUMN_INDEX = HEAD_ELEMENTS - 1;
    localparam [CLW-1:0] HALF_HEAD_INDEX = HALF_HEAD;
    localparam [HIW-1:0] LAST_HEAD_INDEX = TOTAL_HEADS - 1;
    localparam [OIW-1:0] FIRST_KEY_OUTPUT_INDEX = QUERY_ELEMENTS;
    localparam [OIW-1:0] LAST_OUTPUT_INDEX = OUTPUT_ELEMENTS - 1;

    localparam [3:0] STATE_IDLE = 4'd0;
    localparam [3:0] STATE_COEFFICIENT_REQ = 4'd1;
    localparam [3:0] STATE_COEFFICIENT_WAIT = 4'd2;
    localparam [3:0] STATE_INPUT_REQ = 4'd3;
    localparam [3:0] STATE_INPUT_WAIT = 4'd4;
    localparam [3:0] STATE_COMPUTE = 4'd5;
    localparam [3:0] STATE_WRITE = 4'd6;

    reg [3:0] state;
    reg [15:0] coefficient_buffer [0:COEFFICIENT_ELEMENTS-1];
    reg [15:0] head_buffer [0:HEAD_ELEMENTS-1];
    reg [15:0] output_buffer [0:OUTPUT_ELEMENTS-1];
    reg [CIW-1:0] coefficient_index;
    reg [HIW-1:0] head_index;
    reg [CLW-1:0] column_index;
    reg [OIW-1:0] write_index;
    reg [63:0] query_base;
    reg [63:0] key_base;
    reg [63:0] query_destination_base;
    reg [63:0] key_destination_base;
    reg [63:0] coefficient_base;

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

    //: What the datapath actually requires, in place of the model it used to
    //: name: RoPE rotates each column against its partner half a head away,
    //: so the head width must be even and non-zero, and there must be at
    //: least one head of each kind to rotate.
    wire static_profile_legal =
        (PROFILE_HEAD_WIDTH >= 32'd2) &&
        ((PROFILE_HEAD_WIDTH & 32'd1) == 32'd0) &&
        (PROFILE_QUERY_HEADS != 32'd0) &&
        (PROFILE_KEY_HEADS != 32'd0);
    wire command_profile_legal =
        static_profile_legal &&
        (decoder_index == PROFILE_COMMAND_INDEX) &&
        (decoder_kernel_index == PROFILE_KERNEL_INDEX) &&
        (decoder_flags == 0) &&
        (decoder_size0 == PROFILE_QUERY_HEADS) &&
        (decoder_size1 == PROFILE_KEY_HEADS) &&
        (decoder_size2 == PROFILE_HEAD_WIDTH) &&
        (decoder_source0[0] == 0) &&
        (decoder_source1[0] == 0) &&
        (decoder_destination[0] == 0) &&
        (decoder_auxiliary[0] == 0) &&
        (decoder_size3[0] == 0) &&
        (decoder_source0 <= 64'hffff_ffff_ffff_dfff) &&
        (decoder_source1 <= 64'hffff_ffff_ffff_f7ff) &&
        (decoder_destination <= 64'hffff_ffff_ffff_dfff) &&
        (decoder_auxiliary <= 64'hffff_ffff_ffff_f7ff) &&
        ({32'b0, decoder_size3} <= 64'hffff_ffff_ffff_fdff);

    wire read_request_fire = sram_read_valid && sram_read_ready;
    wire read_response_fire = sram_response_valid && sram_response_ready;
    wire write_fire = sram_write_valid && sram_write_ready;
    wire reading_coefficients = (state == STATE_COEFFICIENT_REQ) ||
                                (state == STATE_COEFFICIENT_WAIT);
    wire reading_query = head_index < PROFILE_QUERY_HEADS[HIW-1:0];
    wire [HIW-1:0] source_head_index = reading_query
        ? head_index : head_index - PROFILE_QUERY_HEADS[HIW-1:0];
    //: These were shifts by seven, which is only a multiply by the head width
    //: when that width is 128.
    wire [OIW-1:0] source_element_index =
        (source_head_index * HEAD_ELEMENTS) + column_index;
    wire [OIW-1:0] output_element_index =
        (head_index * HEAD_ELEMENTS) + column_index;
    //: Two bytes per BF16 element.
    wire [63:0] source_element_offset = 64'd2 * {{(64-OIW){1'b0}}, source_element_index};
    wire [63:0] coefficient_offset = 64'd2 * {{(64-CIW){1'b0}}, coefficient_index};

    //: The partner column is half a head away.  Testing bit 6 and adding 64
    //: said the same thing only at a head width of 128.
    wire column_upper = column_index >= HALF_HEAD_INDEX;
    wire [CLW-1:0] rotated_column = column_upper
        ? column_index - HALF_HEAD_INDEX : column_index + HALF_HEAD_INDEX;
    wire [15:0] input_code = head_buffer[column_index];
    wire [15:0] rotated_raw_code = head_buffer[rotated_column];
    wire rotated_nonzero = rotated_raw_code[14:0] != 0;
    wire [15:0] rotated_code = !column_upper
        ? (rotated_nonzero ? rotated_raw_code ^ 16'h8000 : 16'h0000)
        : rotated_raw_code;
    //: Cosines occupy the first head width of the table, sines the second.
    wire [15:0] cosine_code = coefficient_buffer[{1'b0, column_index}];
    wire [15:0] sine_code =
        coefficient_buffer[HEAD_ELEMENTS[CIW-1:0] + {1'b0, column_index}];
    wire [33:0] direct_product = ot_fp32_rne_pkg::fp32_mul_rne(
        {input_code, 16'b0}, {cosine_code, 16'b0}
    );
    wire [33:0] rotated_product = ot_fp32_rne_pkg::fp32_mul_rne(
        {rotated_code, 16'b0}, {sine_code, 16'b0}
    );
    wire [18:0] direct_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(
        direct_product[31:0]
    );
    wire [18:0] rotated_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(
        rotated_product[31:0]
    );
    wire [33:0] summed = ot_fp32_rne_pkg::fp32_add_rne(
        {direct_bf16[15:0], 16'b0}, {rotated_bf16[15:0], 16'b0}
    );
    wire [18:0] output_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(
        summed[31:0]
    );
    wire arithmetic_error =
        (direct_product[33:32] != FP_ERR_NONE) ||
        (rotated_product[33:32] != FP_ERR_NONE) ||
        (direct_bf16[18:17] != FP_ERR_NONE) ||
        (rotated_bf16[18:17] != FP_ERR_NONE) ||
        (summed[33:32] != FP_ERR_NONE) ||
        (output_bf16[18:17] != FP_ERR_NONE);
    wire [1:0] multiplication_saturation_increment =
        {1'b0, direct_bf16[16]} + {1'b0, rotated_bf16[16]};
    wire [OIW-1:0] key_write_index = write_index - FIRST_KEY_OUTPUT_INDEX;
    wire [63:0] query_write_offset = 64'd2 * {{(64-OIW){1'b0}}, write_index};
    wire [63:0] key_write_offset = 64'd2 * {{(64-OIW){1'b0}}, key_write_index};

    assign cmd_ready = decoder_in_ready && (state == STATE_IDLE) && !done_valid;
    assign sram_read_valid = (state == STATE_COEFFICIENT_REQ) ||
                             (state == STATE_INPUT_REQ);
    assign sram_read_address = reading_coefficients
        ? coefficient_base + coefficient_offset
        : (reading_query ? query_base : key_base) + source_element_offset;
    assign sram_response_ready = (state == STATE_COEFFICIENT_WAIT) ||
                                 (state == STATE_INPUT_WAIT);
    assign sram_write_valid = state == STATE_WRITE;
    assign sram_write_address = write_index < FIRST_KEY_OUTPUT_INDEX
        ? query_destination_base + query_write_offset
        : key_destination_base + key_write_offset;
    assign sram_write_data = output_buffer[write_index];
    assign sram_write_byte_enable = 2'b11;

    ot_ta_command_decoder decoder (
        .clk(clk), .rst_n(rst_n),
        .in_valid(cmd_valid && (state == STATE_IDLE) && !done_valid),
        .in_ready(decoder_in_ready), .abi_major(abi_major),
        .abi_minor(abi_minor), .expected_index(expected_command_index),
        .command_record(command_record), .out_valid(decoder_out_valid),
        .out_ready(decoder_out_ready), .out_legal(decoder_out_legal),
        .out_error(decoder_out_error), .out_opcode(decoder_opcode),
        .out_engine(decoder_unused_engine), .out_flags(decoder_flags),
        .out_index(decoder_index), .out_kernel_index(decoder_kernel_index),
        .out_source0(decoder_source0), .out_source1(decoder_source1),
        .out_destination(decoder_destination),
        .out_auxiliary(decoder_auxiliary), .out_size0(decoder_size0),
        .out_size1(decoder_size1), .out_size2(decoder_size2),
        .out_size3(decoder_size3)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= STATE_IDLE;
            coefficient_index <= 0;
            head_index <= 0;
            column_index <= 0;
            write_index <= 0;
            query_base <= 0;
            key_base <= 0;
            query_destination_base <= 0;
            key_destination_base <= 0;
            coefficient_base <= 0;
            done_valid <= 1'b0;
            done_error <= ERR_NONE;
            done_command_index <= 0;
            done_coefficient_read_count <= 0;
            done_query_read_count <= 0;
            done_key_read_count <= 0;
            done_output_write_count <= 0;
            done_element_count <= 0;
            done_multiplication_count <= 0;
            done_addition_count <= 0;
            done_multiplication_saturation_count <= 0;
            done_addition_saturation_count <= 0;
        end else begin
            if (done_valid && done_ready)
                done_valid <= 1'b0;

            if (decoder_out_valid && decoder_out_ready) begin
                done_command_index <= decoder_index;
                done_coefficient_read_count <= 0;
                done_query_read_count <= 0;
                done_key_read_count <= 0;
                done_output_write_count <= 0;
                done_element_count <= 0;
                done_multiplication_count <= 0;
                done_addition_count <= 0;
                done_multiplication_saturation_count <= 0;
                done_addition_saturation_count <= 0;
                coefficient_index <= 0;
                head_index <= 0;
                column_index <= 0;
                write_index <= 0;
                if (!decoder_out_legal) begin
                    done_valid <= 1'b1;
                    done_error <= {4'b0, decoder_out_error};
                end else if (decoder_opcode != OP_ROPE) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_UNSUPPORTED_OPCODE;
                end else if (!command_profile_legal) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_PROFILE;
                end else begin
                    done_error <= ERR_NONE;
                    query_base <= decoder_source0;
                    key_base <= decoder_source1;
                    query_destination_base <= decoder_destination;
                    key_destination_base <= decoder_auxiliary;
                    coefficient_base <= {32'b0, decoder_size3};
                    state <= STATE_COEFFICIENT_REQ;
                end
            end

            if (read_request_fire) begin
                if (state == STATE_COEFFICIENT_REQ)
                    state <= STATE_COEFFICIENT_WAIT;
                else
                    state <= STATE_INPUT_WAIT;
            end

            if (read_response_fire && state == STATE_COEFFICIENT_WAIT) begin
                done_coefficient_read_count <=
                    done_coefficient_read_count + 1'b1;
                if (sram_response_data[14:7] == 8'hff) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_OPERAND_NONFINITE;
                    state <= STATE_IDLE;
                end else begin
                    coefficient_buffer[coefficient_index] <= sram_response_data;
                    if (coefficient_index == LAST_COEFFICIENT_INDEX) begin
                        coefficient_index <= 0;
                        head_index <= 0;
                        column_index <= 0;
                        state <= STATE_INPUT_REQ;
                    end else begin
                        coefficient_index <= coefficient_index + 1'b1;
                        state <= STATE_COEFFICIENT_REQ;
                    end
                end
            end

            if (read_response_fire && state == STATE_INPUT_WAIT) begin
                if (reading_query)
                    done_query_read_count <= done_query_read_count + 1'b1;
                else
                    done_key_read_count <= done_key_read_count + 1'b1;
                if (sram_response_data[14:7] == 8'hff) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_OPERAND_NONFINITE;
                    state <= STATE_IDLE;
                end else begin
                    head_buffer[column_index] <= sram_response_data;
                    if (column_index == LAST_COLUMN_INDEX) begin
                        column_index <= 0;
                        state <= STATE_COMPUTE;
                    end else begin
                        column_index <= column_index + 1'b1;
                        state <= STATE_INPUT_REQ;
                    end
                end
            end

            if (state == STATE_COMPUTE) begin
                if (arithmetic_error) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_ARITHMETIC_OVERFLOW;
                    state <= STATE_IDLE;
                end else begin
                    output_buffer[output_element_index] <= output_bf16[15:0];
                    done_element_count <= done_element_count + 1'b1;
                    done_multiplication_count <=
                        done_multiplication_count + 2;
                    done_addition_count <= done_addition_count + 1'b1;
                    done_multiplication_saturation_count <=
                        done_multiplication_saturation_count +
                        {30'b0, multiplication_saturation_increment};
                    if (output_bf16[16])
                        done_addition_saturation_count <=
                            done_addition_saturation_count + 1'b1;
                    if (column_index == LAST_COLUMN_INDEX) begin
                        column_index <= 0;
                        if (head_index ==
                            LAST_HEAD_INDEX) begin
                            write_index <= 0;
                            state <= STATE_WRITE;
                        end else begin
                            head_index <= head_index + 1'b1;
                            state <= STATE_INPUT_REQ;
                        end
                    end else begin
                        column_index <= column_index + 1'b1;
                    end
                end
            end

            if (write_fire) begin
                done_output_write_count <= done_output_write_count + 1'b1;
                if (write_index == LAST_OUTPUT_INDEX) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_NONE;
                    state <= STATE_IDLE;
                end else begin
                    write_index <= write_index + 1'b1;
                end
            end
        end
    end

    wire _unused_decoder = &{1'b0, decoder_unused_engine};
endmodule
