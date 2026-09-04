`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 bank-port adapter for the qualified Qwen BF16 RoPE datapath.
//
// The released ABI presents query and key rotation as two independent
// VECTOR.ROPE operations, while ot_ta_rope_bf16_sram_engine implements the
// earlier qualified fused 32-query-head plus 8-key-head command.  This adapter
// executes one declared ABI operand at a time through that unchanged datapath.
// The inactive side receives internal positive-zero data and its writes are
// discarded; no undeclared external operand is read or destination written.
//
// ABI 3.0 coefficient rows are FP32.  They are narrowed to BF16 RNE at the
// adapter boundary, exactly as qwen3_rope_fp32_bf16_v1 requires, before the
// qualified core performs its two BF16-rounded products and BF16-rounded sum.
// One BF16 code occupies the low half of each 32-bit verification-bank word.
// ---------------------------------------------------------------------------
module ot_a3_vector_rope (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [31:0] cfg_count,
    input  wire [31:0] cfg_rows,
    input  wire [31:0] cfg_cols,
    input  wire [31:0] cfg_input_base,
    input  wire [31:0] cfg_coefficient_base,
    input  wire [31:0] cfg_output_base,

    output wire        input_rd_en,
    output wire [31:0] input_rd_addr,
    input  wire [31:0] input_rd_data,
    output wire        coefficient_rd_en,
    output wire [31:0] coefficient_rd_addr,
    input  wire [31:0] coefficient_rd_data,
    output wire        out_we,
    output wire [31:0] out_addr,
    output wire [31:0] out_data,

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

    localparam [31:0] QUERY_HEADS = 32'd32;
    localparam [31:0] KEY_HEADS = 32'd8;
    localparam [31:0] HEAD_WIDTH = 32'd128;
    localparam [31:0] COEFFICIENT_COUNT = 32'd256;

    // The internal byte-address spaces are deliberately disjoint.  They are
    // decoded here and never escape onto an ABI-visible memory port.
    localparam [63:0] CORE_QUERY_BASE = 64'h0000_0000_0001_0000;
    localparam [63:0] CORE_KEY_BASE = 64'h0000_0000_0002_0000;
    localparam [63:0] CORE_QUERY_OUTPUT_BASE = 64'h0000_0000_0003_0000;
    localparam [63:0] CORE_KEY_OUTPUT_BASE = 64'h0000_0000_0004_0000;
    localparam [63:0] CORE_COEFFICIENT_BASE = 64'h0000_0000_0005_0000;
    localparam [63:0] CORE_QUERY_BYTES = 64'd8192;
    localparam [63:0] CORE_KEY_BYTES = 64'd2048;
    localparam [63:0] CORE_COEFFICIENT_BYTES = 64'd512;

    // ABI 2.2 is private to this adapter.  The record contains ROPE_BF16,
    // vector engine 3, index/kernel 0, the five internal bases above,
    // 32/8/128 geometry, and reflected IEEE CRC32 0xdb8405f0.
    localparam [511:0] CORE_COMMAND =
        512'hdb8405f0000500000000008000000008000000200000000000040000000000000003000000000000000200000000000000010000000000000000000000000321;

    localparam [1:0] S_IDLE = 2'd0;
    localparam [1:0] S_DISPATCH = 2'd1;
    localparam [1:0] S_RUN = 2'd2;
    localparam [1:0] S_DONE = 2'd3;
    localparam [1:0] READ_DUMMY = 2'd0;
    localparam [1:0] READ_INPUT = 2'd1;
    localparam [1:0] READ_COEFFICIENT = 2'd2;
    localparam [1:0] READ_INVALID = 2'd3;

    reg [1:0] state;
    reg active_query;
    reg [31:0] input_base_q;
    reg [31:0] coefficient_base_q;
    reg [31:0] output_base_q;
    reg [31:0] count_q;
    reg read_pending;
    reg [1:0] read_kind;
    reg address_fault;
    reg [31:0] selected_write_count;

    wire core_cmd_valid = state == S_DISPATCH;
    wire core_cmd_ready;
    wire core_read_valid;
    wire core_read_ready;
    wire [63:0] core_read_address;
    wire core_response_valid;
    wire core_response_ready;
    wire [15:0] core_response_data;
    wire core_write_valid;
    wire core_write_ready;
    wire [63:0] core_write_address;
    wire [15:0] core_write_data;
    wire [1:0] core_write_byte_enable;
    wire core_done_valid;
    wire core_done_ready = state == S_RUN;
    wire [7:0] core_done_error;
    wire [31:0] core_done_command_index;
    wire [31:0] core_done_coefficient_reads;
    wire [31:0] core_done_query_reads;
    wire [31:0] core_done_key_reads;
    wire [31:0] core_done_writes;
    wire [31:0] core_done_elements;
    wire [31:0] core_done_multiplications;
    wire [31:0] core_done_additions;
    wire [31:0] core_done_multiplication_saturations;
    wire [31:0] core_done_addition_saturations;

    wire read_is_query =
        (core_read_address >= CORE_QUERY_BASE) &&
        (core_read_address < CORE_QUERY_BASE + CORE_QUERY_BYTES);
    wire read_is_key =
        (core_read_address >= CORE_KEY_BASE) &&
        (core_read_address < CORE_KEY_BASE + CORE_KEY_BYTES);
    wire read_is_coefficient =
        (core_read_address >= CORE_COEFFICIENT_BASE) &&
        (core_read_address <
         CORE_COEFFICIENT_BASE + CORE_COEFFICIENT_BYTES);
    wire read_is_selected_input =
        (active_query && read_is_query) || (!active_query && read_is_key);
    wire read_is_dummy_input =
        (active_query && read_is_key) || (!active_query && read_is_query);
    wire [63:0] selected_input_offset = active_query
        ? core_read_address - CORE_QUERY_BASE
        : core_read_address - CORE_KEY_BASE;
    wire [63:0] coefficient_offset =
        core_read_address - CORE_COEFFICIENT_BASE;

    assign core_read_ready = (state == S_RUN) && !read_pending;
    assign input_rd_en = core_read_valid && core_read_ready &&
                         read_is_selected_input;
    assign input_rd_addr = input_base_q + selected_input_offset[32:1];
    assign coefficient_rd_en = core_read_valid && core_read_ready &&
                               read_is_coefficient;
    assign coefficient_rd_addr =
        coefficient_base_q + coefficient_offset[32:1];

    wire [18:0] narrowed_coefficient =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(coefficient_rd_data);
    wire coefficient_conversion_error =
        narrowed_coefficient[18:17] != 2'd0;
    assign core_response_valid = read_pending;
    assign core_response_data = read_kind == READ_INPUT
        ? input_rd_data[15:0]
        : read_kind == READ_COEFFICIENT
        ? (coefficient_conversion_error
           ? 16'h7f80 : narrowed_coefficient[15:0])
        : read_kind == READ_DUMMY ? 16'd0 : 16'h7f80;

    wire write_is_query =
        (core_write_address >= CORE_QUERY_OUTPUT_BASE) &&
        (core_write_address < CORE_QUERY_OUTPUT_BASE + CORE_QUERY_BYTES);
    wire write_is_key =
        (core_write_address >= CORE_KEY_OUTPUT_BASE) &&
        (core_write_address < CORE_KEY_OUTPUT_BASE + CORE_KEY_BYTES);
    wire write_is_selected =
        (active_query && write_is_query) || (!active_query && write_is_key);
    wire write_is_dummy =
        (active_query && write_is_key) || (!active_query && write_is_query);
    wire [63:0] selected_output_offset = active_query
        ? core_write_address - CORE_QUERY_OUTPUT_BASE
        : core_write_address - CORE_KEY_OUTPUT_BASE;
    assign core_write_ready = state == S_RUN;
    assign out_we = core_write_valid && core_write_ready && write_is_selected;
    assign out_addr = output_base_q + selected_output_offset[32:1];
    assign out_data = {16'd0, core_write_data};

    ot_ta_rope_bf16_sram_engine #(
        .PROFILE_COMMAND_INDEX(32'd0),
        .PROFILE_KERNEL_INDEX(32'd0)
    ) qualified_rope (
        .clk(clk),
        .rst_n(rst_n),
        .cmd_valid(core_cmd_valid),
        .cmd_ready(core_cmd_ready),
        .abi_major(16'd2),
        .abi_minor(16'd2),
        .expected_command_index(32'd0),
        .command_record(CORE_COMMAND),
        .sram_read_valid(core_read_valid),
        .sram_read_ready(core_read_ready),
        .sram_read_address(core_read_address),
        .sram_response_valid(core_response_valid),
        .sram_response_ready(core_response_ready),
        .sram_response_data(core_response_data),
        .sram_write_valid(core_write_valid),
        .sram_write_ready(core_write_ready),
        .sram_write_address(core_write_address),
        .sram_write_data(core_write_data),
        .sram_write_byte_enable(core_write_byte_enable),
        .done_valid(core_done_valid),
        .done_ready(core_done_ready),
        .done_error(core_done_error),
        .done_command_index(core_done_command_index),
        .done_coefficient_read_count(core_done_coefficient_reads),
        .done_query_read_count(core_done_query_reads),
        .done_key_read_count(core_done_key_reads),
        .done_output_write_count(core_done_writes),
        .done_element_count(core_done_elements),
        .done_multiplication_count(core_done_multiplications),
        .done_addition_count(core_done_additions),
        .done_multiplication_saturation_count(
            core_done_multiplication_saturations
        ),
        .done_addition_saturation_count(core_done_addition_saturations)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            active_query <= 1'b0;
            input_base_q <= 0;
            coefficient_base_q <= 0;
            output_base_q <= 0;
            count_q <= 0;
            read_pending <= 1'b0;
            read_kind <= READ_DUMMY;
            address_fault <= 1'b0;
            selected_write_count <= 0;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            result_count <= 0;
            saturation_count <= 0;
            work_count <= 0;
        end else begin
            done <= 1'b0;

            if (core_read_valid && core_read_ready) begin
                read_pending <= 1'b1;
                if (read_is_selected_input)
                    read_kind <= READ_INPUT;
                else if (read_is_coefficient)
                    read_kind <= READ_COEFFICIENT;
                else if (read_is_dummy_input)
                    read_kind <= READ_DUMMY;
                else begin
                    read_kind <= READ_INVALID;
                    address_fault <= 1'b1;
                end
            end else if (core_response_valid && core_response_ready) begin
                read_pending <= 1'b0;
                if ((read_kind == READ_COEFFICIENT) &&
                    narrowed_coefficient[16])
                    saturation_count <= saturation_count + 1'b1;
            end

            if (core_write_valid && core_write_ready) begin
                if (write_is_selected)
                    selected_write_count <= selected_write_count + 1'b1;
                else if (!write_is_dummy)
                    address_fault <= 1'b1;
            end

            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        result_count <= 0;
                        saturation_count <= 0;
                        work_count <= 0;
                        read_pending <= 1'b0;
                        read_kind <= READ_DUMMY;
                        address_fault <= 1'b0;
                        selected_write_count <= 0;
                        input_base_q <= cfg_input_base;
                        coefficient_base_q <= cfg_coefficient_base;
                        output_base_q <= cfg_output_base;
                        count_q <= cfg_count;
                        active_query <= cfg_rows == QUERY_HEADS;
                        if ((cfg_cols != HEAD_WIDTH) ||
                            !((cfg_rows == QUERY_HEADS) ||
                              (cfg_rows == KEY_HEADS)) ||
                            (cfg_count != cfg_rows * cfg_cols)) begin
                            error_code <= ERR_SHAPE;
                            state <= S_DONE;
                        end else begin
                            state <= S_DISPATCH;
                        end
                    end
                end

                S_DISPATCH: begin
                    if (core_cmd_valid && core_cmd_ready)
                        state <= S_RUN;
                end

                S_RUN: begin
                    if (core_done_valid) begin
                        if (core_done_error == 8'd9)
                            error_code <= ERR_OPERAND_NONFINITE;
                        else if (core_done_error == 8'd10)
                            error_code <= ERR_ACCUMULATE_RANGE;
                        else if ((core_done_error != 0) || address_fault ||
                                 (core_done_command_index != 0) ||
                                 (core_done_coefficient_reads !=
                                  COEFFICIENT_COUNT) ||
                                 (core_done_query_reads != 32'd4096) ||
                                 (core_done_key_reads != 32'd1024) ||
                                 (core_done_writes != 32'd5120) ||
                                 (core_done_elements != 32'd5120) ||
                                 (core_done_multiplications != 32'd10240) ||
                                 (core_done_additions != 32'd5120) ||
                                 (selected_write_count != count_q))
                            error_code <= ERR_SHAPE;
                        else begin
                            error_code <= ERR_NONE;
                            result_count <= count_q;
                            work_count <= count_q;
                        end
                        state <= S_DONE;
                    end
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end

                default: begin
                    error_code <= ERR_SHAPE;
                    state <= S_DONE;
                end
            endcase
        end
    end

    wire _unused_core = &{1'b0, core_write_byte_enable,
        core_done_multiplication_saturations,
        core_done_addition_saturations};
endmodule
