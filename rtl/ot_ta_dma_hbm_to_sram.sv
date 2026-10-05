`timescale 1ns/1ps
// One-outstanding-burst execution of the production DMA_HBM_TO_SRAM command.
// The fixed 64-byte HBM response is drained as four 16-byte SRAM writes.  HBM
// PHY, retry/ECC policy, SRAM banks, arbitration, and physical macros remain
// outside this functional command boundary.
module ot_ta_dma_hbm_to_sram #(
    parameter [31:0] MAX_TRANSFER_BYTES = 32'd1048576
) (
    input  wire         clk,
    input  wire         rst_n,

    input  wire         cmd_valid,
    output wire         cmd_ready,
    input  wire [15:0]  abi_major,
    input  wire [15:0]  abi_minor,
    input  wire [31:0]  expected_command_index,
    input  wire [511:0] command_record,

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
    output reg  [127:0] sram_write_data,
    output wire [15:0]  sram_write_byte_enable,

    output reg          done_valid,
    input  wire         done_ready,
    output reg  [7:0]   done_error,
    output reg  [31:0]  done_command_index,
    output reg  [31:0]  done_hbm_request_count,
    output reg  [31:0]  done_hbm_response_count,
    output reg  [31:0]  done_hbm_bytes_read,
    output reg  [31:0]  done_sram_write_count,
    output reg  [31:0]  done_sram_bytes_written
);
    localparam [7:0] OP_DMA_DIRECT = 8'h01;
    localparam [7:0] ERR_NONE = 8'd0;
    localparam [7:0] ERR_UNSUPPORTED_OPCODE = 8'd7;
    localparam [7:0] ERR_SIZE_OR_ALIGNMENT = 8'd8;
    localparam [7:0] ERR_HBM_RESPONSE = 8'd11;
    localparam [31:0] HBM_BURST_BYTES = 32'd64;
    localparam [31:0] SRAM_WORD_BYTES = 32'd16;

    wire decoder_in_ready;
    wire decoder_out_valid;
    wire decoder_out_legal;
    wire [3:0] decoder_out_error;
    wire [7:0] decoder_opcode;
    wire [7:0] decoder_unused_engine;
    wire [15:0] decoder_unused_flags;
    wire [31:0] decoder_index;
    wire [31:0] decoder_unused_kernel_index;
    wire [63:0] decoder_source0;
    wire [63:0] decoder_unused_source1;
    wire [63:0] decoder_destination;
    wire [63:0] decoder_unused_auxiliary;
    wire [31:0] decoder_size0;
    wire [31:0] decoder_unused_size1;
    wire [31:0] decoder_unused_size2;
    wire [31:0] decoder_unused_size3;

    reg active;
    reg awaiting_response;
    reg burst_valid;
    reg [1:0] burst_word_index;
    reg [511:0] burst_data;
    reg [31:0] target_bytes;
    reg [31:0] requested_bytes;
    reg [63:0] hbm_base;
    reg [63:0] sram_base;

    wire decoder_out_ready = !active && !done_valid;
    wire request_fire = hbm_request_valid && hbm_request_ready;
    wire response_fire = hbm_response_valid && hbm_response_ready;
    wire write_fire = sram_write_valid && sram_write_ready;

    assign cmd_ready = decoder_in_ready && !active && !done_valid;
    assign hbm_request_valid = active && !awaiting_response && !burst_valid &&
                               (requested_bytes < target_bytes);
    assign hbm_request_address = hbm_base + {32'b0, requested_bytes};
    assign hbm_request_bytes = HBM_BURST_BYTES[15:0];
    assign hbm_response_ready = active && awaiting_response && !burst_valid;
    assign sram_write_valid = active && burst_valid;
    assign sram_write_address = sram_base + {32'b0, done_sram_bytes_written};
    assign sram_write_byte_enable = 16'hffff;

    always @* begin
        case (burst_word_index)
            2'd0: sram_write_data = burst_data[127:0];
            2'd1: sram_write_data = burst_data[255:128];
            2'd2: sram_write_data = burst_data[383:256];
            default: sram_write_data = burst_data[511:384];
        endcase
    end

    ot_ta_command_decoder decoder (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(cmd_valid && !active && !done_valid),
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
        .out_flags(decoder_unused_flags),
        .out_index(decoder_index),
        .out_kernel_index(decoder_unused_kernel_index),
        .out_source0(decoder_source0),
        .out_source1(decoder_unused_source1),
        .out_destination(decoder_destination),
        .out_auxiliary(decoder_unused_auxiliary),
        .out_size0(decoder_size0),
        .out_size1(decoder_unused_size1),
        .out_size2(decoder_unused_size2),
        .out_size3(decoder_unused_size3)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0;
            awaiting_response <= 1'b0;
            burst_valid <= 1'b0;
            burst_word_index <= 0;
            burst_data <= 0;
            target_bytes <= 0;
            requested_bytes <= 0;
            hbm_base <= 0;
            sram_base <= 0;
            done_valid <= 1'b0;
            done_error <= ERR_NONE;
            done_command_index <= 0;
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
                done_hbm_request_count <= 0;
                done_hbm_response_count <= 0;
                done_hbm_bytes_read <= 0;
                done_sram_write_count <= 0;
                done_sram_bytes_written <= 0;
                if (!decoder_out_legal) begin
                    done_valid <= 1'b1;
                    done_error <= {4'b0, decoder_out_error};
                end else if (decoder_opcode != OP_DMA_DIRECT) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_UNSUPPORTED_OPCODE;
                end else if ((decoder_size0 == 0) ||
                             (decoder_size0 > MAX_TRANSFER_BYTES) ||
                             (decoder_size0[5:0] != 0) ||
                             (decoder_source0[5:0] != 0) ||
                             (decoder_destination[3:0] != 0)) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_SIZE_OR_ALIGNMENT;
                end else begin
                    active <= 1'b1;
                    awaiting_response <= 1'b0;
                    burst_valid <= 1'b0;
                    burst_word_index <= 0;
                    target_bytes <= decoder_size0;
                    requested_bytes <= 0;
                    hbm_base <= decoder_source0;
                    sram_base <= decoder_destination;
                    done_error <= ERR_NONE;
                end
            end

            if (request_fire) begin
                awaiting_response <= 1'b1;
                requested_bytes <= requested_bytes + HBM_BURST_BYTES;
                done_hbm_request_count <= done_hbm_request_count + 1'b1;
            end

            if (response_fire) begin
                awaiting_response <= 1'b0;
                done_hbm_response_count <= done_hbm_response_count + 1'b1;
                if (hbm_response_error != 0) begin
                    active <= 1'b0;
                    burst_valid <= 1'b0;
                    done_valid <= 1'b1;
                    done_error <= ERR_HBM_RESPONSE;
                end else begin
                    burst_valid <= 1'b1;
                    burst_word_index <= 0;
                    burst_data <= hbm_response_data;
                    done_hbm_bytes_read <= done_hbm_bytes_read +
                                           HBM_BURST_BYTES;
                end
            end

            if (write_fire) begin
                done_sram_write_count <= done_sram_write_count + 1'b1;
                done_sram_bytes_written <= done_sram_bytes_written +
                                           SRAM_WORD_BYTES;
                if (burst_word_index == 2'd3) begin
                    burst_valid <= 1'b0;
                    burst_word_index <= 0;
                    if (done_sram_bytes_written + SRAM_WORD_BYTES ==
                        target_bytes) begin
                        active <= 1'b0;
                        done_valid <= 1'b1;
                        done_error <= ERR_NONE;
                    end
                end else begin
                    burst_word_index <= burst_word_index + 1'b1;
                end
            end
        end
    end

    wire _unused_decoder = &{1'b0, decoder_unused_engine,
                             decoder_unused_flags,
                             decoder_unused_kernel_index,
                             decoder_unused_source1,
                             decoder_unused_auxiliary,
                             decoder_unused_size1,
                             decoder_unused_size2,
                             decoder_unused_size3};
endmodule
