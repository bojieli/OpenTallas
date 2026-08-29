`timescale 1ns/1ps
// Bounded execution of the production DMA_HBM_INDEXED_TO_SRAM command used to
// select one Qwen RoPE coefficient row.  The 32-bit little-endian logical index
// is read from SRAM, range checked, and converted into an HBM row address.  All
// HBM bursts are buffered before the first SRAM write so an HBM response error
// cannot leave a partially replaced coefficient row.
//
// This is a source-profiled functional slice.  HBM PHY, retry/ECC policy,
// physical SRAM, banking, arbitration, and SRAM response-error signaling remain
// outside this boundary.
module ot_ta_dma_hbm_indexed_to_sram #(
    parameter [31:0] PROFILE_COMMAND_INDEX = 32'd3079,
    parameter [31:0] PROFILE_KERNEL_INDEX = 32'd7,
    parameter [31:0] PROFILE_ROW_BYTES = 32'd512,
    parameter [31:0] PROFILE_ROW_STRIDE = 32'd512,
    parameter [31:0] PROFILE_ROW_COUNT = 32'd8000,
    parameter [31:0] PROFILE_INDEX_BYTES = 32'd4
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

    output wire         hbm_request_valid,
    input  wire         hbm_request_ready,
    output wire [63:0]  hbm_request_address,
    output wire [15:0]  hbm_request_bytes,
    input  wire         hbm_response_valid,
    output wire         hbm_response_ready,
    input  wire [511:0] hbm_response_data,
    input  wire [1:0]   hbm_response_error,

    output wire         sram_write_valid,
    input  wire         sram_write_ready,
    output wire [63:0]  sram_write_address,
    output wire [127:0] sram_write_data,
    output wire [15:0]  sram_write_byte_enable,

    output reg          done_valid,
    input  wire         done_ready,
    output reg  [7:0]   done_error,
    output reg  [31:0]  done_command_index,
    output reg  [31:0]  done_logical_index,
    output reg  [63:0]  done_selected_hbm_address,
    output reg  [31:0]  done_sram_index_read_count,
    output reg  [31:0]  done_hbm_request_count,
    output reg  [31:0]  done_hbm_response_count,
    output reg  [31:0]  done_hbm_bytes_read,
    output reg  [31:0]  done_sram_write_count,
    output reg  [31:0]  done_sram_bytes_written
);
    localparam [7:0] OP_DMA_INDEXED = 8'h02;
    localparam [7:0] ERR_NONE = 8'd0;
    localparam [7:0] ERR_UNSUPPORTED_OPCODE = 8'd7;
    localparam [7:0] ERR_PROFILE = 8'd8;
    localparam [7:0] ERR_INDEX_RANGE = 8'd9;
    localparam [7:0] ERR_HBM_RESPONSE = 8'd11;
    localparam [31:0] HBM_BURST_BYTES = 32'd64;
    localparam [31:0] SRAM_WORD_BYTES = 32'd16;
    localparam integer PROFILE_BURSTS = PROFILE_ROW_BYTES / 64;

    localparam [3:0] STATE_IDLE = 4'd0;
    localparam [3:0] STATE_INDEX_LOW_REQ = 4'd1;
    localparam [3:0] STATE_INDEX_LOW_WAIT = 4'd2;
    localparam [3:0] STATE_INDEX_HIGH_REQ = 4'd3;
    localparam [3:0] STATE_INDEX_HIGH_WAIT = 4'd4;
    localparam [3:0] STATE_HBM_REQ = 4'd5;
    localparam [3:0] STATE_HBM_WAIT = 4'd6;
    localparam [3:0] STATE_WRITE = 4'd7;

    reg [3:0] state;
    reg [15:0] index_low;
    reg [63:0] table_base;
    reg [63:0] index_address;
    reg [63:0] destination_base;
    reg [63:0] selected_hbm_address;
    reg [4:0] write_word_index;
    reg [511:0] burst_buffer [0:PROFILE_BURSTS-1];

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

    wire static_profile_legal =
        (PROFILE_ROW_BYTES == 32'd512) &&
        (PROFILE_ROW_STRIDE == PROFILE_ROW_BYTES) &&
        (PROFILE_ROW_COUNT == 32'd8000) &&
        (PROFILE_INDEX_BYTES == 32'd4) &&
        ((PROFILE_ROW_BYTES & 32'd63) == 0);
    wire command_profile_legal =
        static_profile_legal &&
        (decoder_index == PROFILE_COMMAND_INDEX) &&
        (decoder_kernel_index == PROFILE_KERNEL_INDEX) &&
        (decoder_flags == 0) &&
        (decoder_auxiliary == 0) &&
        (decoder_size0 == PROFILE_ROW_BYTES) &&
        (decoder_size1 == PROFILE_ROW_STRIDE) &&
        (decoder_size2 == PROFILE_ROW_COUNT) &&
        (decoder_size3 == PROFILE_INDEX_BYTES) &&
        (decoder_source0[5:0] == 0) &&
        (decoder_source1[1:0] == 0) &&
        (decoder_destination[3:0] == 0) &&
        (decoder_source0 <=
         64'hffff_ffff_ffff_ffff -
         ({32'b0, PROFILE_ROW_STRIDE} * PROFILE_ROW_COUNT));

    wire read_request_fire = sram_read_valid && sram_read_ready;
    wire read_response_fire = sram_response_valid && sram_response_ready;
    wire hbm_request_fire = hbm_request_valid && hbm_request_ready;
    wire hbm_response_fire = hbm_response_valid && hbm_response_ready;
    wire write_fire = sram_write_valid && sram_write_ready;
    wire [31:0] assembled_index = {sram_response_data, index_low};
    wire assembled_index_legal = assembled_index < PROFILE_ROW_COUNT;
    wire [63:0] assembled_row_offset =
        {32'b0, assembled_index} * {32'b0, PROFILE_ROW_STRIDE};
    wire [2:0] write_burst_index = write_word_index[4:2];

    assign cmd_ready = decoder_in_ready && (state == STATE_IDLE) && !done_valid;
    assign sram_read_valid = (state == STATE_INDEX_LOW_REQ) ||
                             (state == STATE_INDEX_HIGH_REQ);
    assign sram_read_address = index_address +
                               (state == STATE_INDEX_HIGH_REQ ? 64'd2 : 64'd0);
    assign sram_response_ready = (state == STATE_INDEX_LOW_WAIT) ||
                                 (state == STATE_INDEX_HIGH_WAIT);
    assign hbm_request_valid = state == STATE_HBM_REQ;
    assign hbm_request_address = selected_hbm_address +
                                 ({32'b0, done_hbm_request_count} << 6);
    assign hbm_request_bytes = HBM_BURST_BYTES[15:0];
    assign hbm_response_ready = state == STATE_HBM_WAIT;
    assign sram_write_valid = state == STATE_WRITE;
    assign sram_write_address = destination_base +
                                {32'b0, done_sram_bytes_written};
    assign sram_write_byte_enable = 16'hffff;

    assign sram_write_data = burst_buffer[write_burst_index]
        [{write_word_index[1:0], 7'b0} +: 128];

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
            index_low <= 0;
            table_base <= 0;
            index_address <= 0;
            destination_base <= 0;
            selected_hbm_address <= 0;
            write_word_index <= 0;
            done_valid <= 1'b0;
            done_error <= ERR_NONE;
            done_command_index <= 0;
            done_logical_index <= 0;
            done_selected_hbm_address <= 0;
            done_sram_index_read_count <= 0;
            done_hbm_request_count <= 0;
            done_hbm_response_count <= 0;
            done_hbm_bytes_read <= 0;
            done_sram_write_count <= 0;
            done_sram_bytes_written <= 0;
        end else begin
            if (done_valid && done_ready)
                done_valid <= 1'b0;

            if (decoder_out_valid && decoder_out_ready) begin
                done_command_index <= decoder_index;
                done_logical_index <= 0;
                done_selected_hbm_address <= 0;
                done_sram_index_read_count <= 0;
                done_hbm_request_count <= 0;
                done_hbm_response_count <= 0;
                done_hbm_bytes_read <= 0;
                done_sram_write_count <= 0;
                done_sram_bytes_written <= 0;
                write_word_index <= 0;
                if (!decoder_out_legal) begin
                    done_valid <= 1'b1;
                    done_error <= {4'b0, decoder_out_error};
                end else if (decoder_opcode != OP_DMA_INDEXED) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_UNSUPPORTED_OPCODE;
                end else if (!command_profile_legal) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_PROFILE;
                end else begin
                    done_error <= ERR_NONE;
                    table_base <= decoder_source0;
                    index_address <= decoder_source1;
                    destination_base <= decoder_destination;
                    state <= STATE_INDEX_LOW_REQ;
                end
            end

            if (read_request_fire) begin
                if (state == STATE_INDEX_LOW_REQ)
                    state <= STATE_INDEX_LOW_WAIT;
                else
                    state <= STATE_INDEX_HIGH_WAIT;
            end

            if (read_response_fire) begin
                done_sram_index_read_count <=
                    done_sram_index_read_count + 1'b1;
                if (state == STATE_INDEX_LOW_WAIT) begin
                    index_low <= sram_response_data;
                    state <= STATE_INDEX_HIGH_REQ;
                end else if (!assembled_index_legal) begin
                    done_logical_index <= assembled_index;
                    done_valid <= 1'b1;
                    done_error <= ERR_INDEX_RANGE;
                    state <= STATE_IDLE;
                end else begin
                    done_logical_index <= assembled_index;
                    selected_hbm_address <= table_base + assembled_row_offset;
                    done_selected_hbm_address <=
                        table_base + assembled_row_offset;
                    state <= STATE_HBM_REQ;
                end
            end

            if (hbm_request_fire) begin
                done_hbm_request_count <= done_hbm_request_count + 1'b1;
                state <= STATE_HBM_WAIT;
            end

            if (hbm_response_fire) begin
                done_hbm_response_count <= done_hbm_response_count + 1'b1;
                if (hbm_response_error != 0) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_HBM_RESPONSE;
                    state <= STATE_IDLE;
                end else begin
                    burst_buffer[done_hbm_response_count[2:0]] <=
                        hbm_response_data;
                    done_hbm_bytes_read <= done_hbm_bytes_read +
                                           HBM_BURST_BYTES;
                    if (done_hbm_response_count + 1'b1 == PROFILE_BURSTS) begin
                        write_word_index <= 0;
                        state <= STATE_WRITE;
                    end else begin
                        state <= STATE_HBM_REQ;
                    end
                end
            end

            if (write_fire) begin
                done_sram_write_count <= done_sram_write_count + 1'b1;
                done_sram_bytes_written <= done_sram_bytes_written +
                                           SRAM_WORD_BYTES;
                if (done_sram_bytes_written + SRAM_WORD_BYTES ==
                    PROFILE_ROW_BYTES) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_NONE;
                    state <= STATE_IDLE;
                end else begin
                    write_word_index <= write_word_index + 1'b1;
                end
            end
        end
    end

    wire _unused_decoder = &{1'b0, decoder_unused_engine};
endmodule
