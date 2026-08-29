`timescale 1ns/1ps
// Exact four-command boundary for two adjacent Qwen per-head RMSNorm kernels:
// DMA/RMSNorm for Q followed by DMA/RMSNorm for K.  Only one command executes
// at a time; kernel indices, contiguous ordering, alternating opcodes, and the
// unique terminal command are checked before dispatch.
module ot_ta_dma_head_rmsnorm_sequencer #(
    parameter [31:0] MAX_TRANSFER_BYTES = 32'd1048576,
    parameter [31:0] FIRST_COMMAND_INDEX = 32'd3075,
    parameter [31:0] LAST_COMMAND_INDEX = 32'd3078,
    parameter [31:0] KERNEL0_INDEX = 32'd5,
    parameter [31:0] KERNEL0_LAST_COMMAND_INDEX = 32'd3076,
    parameter [31:0] KERNEL0_ROWS = 32'd32,
    parameter [31:0] KERNEL1_INDEX = 32'd6,
    parameter [31:0] KERNEL1_LAST_COMMAND_INDEX = 32'd3078,
    parameter [31:0] KERNEL1_ROWS = 32'd8
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cmd_valid,
    output wire         cmd_ready,
    input  wire         cmd_last,
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
    output wire         sram_read_valid,
    input  wire         sram_read_ready,
    output wire [63:0]  sram_read_address,
    input  wire         sram_response_valid,
    output wire         sram_response_ready,
    input  wire [15:0]  sram_response_data,
    output wire         sram_write_valid,
    input  wire         sram_write_ready,
    output wire [63:0]  sram_write_address,
    output wire [127:0] sram_write_data,
    output wire [15:0]  sram_write_byte_enable,
    output wire         program_active,
    output reg          program_done_valid,
    input  wire         program_done_ready,
    output reg  [7:0]   program_done_error,
    output reg  [31:0]  program_done_failing_command_index,
    output reg  [31:0]  program_done_last_command_index,
    output reg  [31:0]  program_done_commands_accepted,
    output reg  [31:0]  program_done_commands_completed,
    output reg  [31:0]  program_done_hbm_request_count,
    output reg  [31:0]  program_done_hbm_response_count,
    output reg  [31:0]  program_done_hbm_bytes_read,
    output reg  [31:0]  program_done_sram_read_count,
    output reg  [31:0]  program_done_sram_bytes_read,
    output reg  [31:0]  program_done_sram_write_count,
    output reg  [31:0]  program_done_sram_bytes_written,
    output reg  [31:0]  program_done_row_count,
    output reg  [31:0]  program_done_element_count,
    output reg  [31:0]  program_done_normalized_saturation_count,
    output reg  [31:0]  program_done_output_saturation_count,
    output reg  [31:0]  program_done_mean_square_code,
    output reg  [31:0]  program_done_inverse_rms_code
);
    localparam [7:0] OP_DMA_DIRECT = 8'h01;
    localparam [7:0] OP_RMSNORM = 8'h20;
    localparam [7:0] ERR_NONE = 8'd0;
    localparam [7:0] ERR_UNSUPPORTED_OPCODE = 8'd7;
    localparam [7:0] ERR_PROGRAM_ORDER = 8'd12;
    localparam [31:0] NO_FAILING_INDEX = 32'hffff_ffff;
    localparam [2:0] STATE_ACCEPT = 3'd0;
    localparam [2:0] STATE_DISPATCH_DMA = 3'd1;
    localparam [2:0] STATE_WAIT_DMA = 3'd2;
    localparam [2:0] STATE_DISPATCH_RMS = 3'd3;
    localparam [2:0] STATE_WAIT_RMS = 3'd4;
    localparam [2:0] STATE_DONE = 3'd5;

    reg [2:0] state;
    reg active_program;
    reg [31:0] last_accepted_index;
    reg [511:0] buffered_record;
    reg [31:0] buffered_expected_index;
    reg [15:0] buffered_abi_major;
    reg [15:0] buffered_abi_minor;
    reg buffered_last;

    wire first_command = !active_program;
    wire command_fire = cmd_valid && cmd_ready;
    wire command_in_order = first_command
        ? expected_command_index == FIRST_COMMAND_INDEX
        : expected_command_index == last_accepted_index + 1'b1;
    wire [31:0] expected_kernel_index =
        expected_command_index <= KERNEL0_LAST_COMMAND_INDEX
        ? KERNEL0_INDEX : KERNEL1_INDEX;
    wire static_profile_legal =
        (LAST_COMMAND_INDEX == FIRST_COMMAND_INDEX + 3) &&
        (KERNEL0_LAST_COMMAND_INDEX == FIRST_COMMAND_INDEX + 1) &&
        (KERNEL1_LAST_COMMAND_INDEX == LAST_COMMAND_INDEX);
    wire command_profile_legal =
        static_profile_legal &&
        (expected_command_index >= FIRST_COMMAND_INDEX) &&
        (expected_command_index <= LAST_COMMAND_INDEX) &&
        (command_record[95:64] == expected_kernel_index) &&
        (expected_command_index[0]
         ? command_record[7:0] == OP_DMA_DIRECT
         : command_record[7:0] == OP_RMSNORM) &&
        (cmd_last == (expected_command_index == LAST_COMMAND_INDEX));
    assign cmd_ready = (state == STATE_ACCEPT) && !program_done_valid;
    assign program_active = active_program;

    wire dma_cmd_valid = state == STATE_DISPATCH_DMA;
    wire dma_cmd_ready;
    wire dma_done_valid;
    wire dma_done_ready = state == STATE_WAIT_DMA;
    wire [7:0] dma_done_error;
    wire [31:0] dma_done_command_index;
    wire [31:0] dma_done_hbm_request_count;
    wire [31:0] dma_done_hbm_response_count;
    wire [31:0] dma_done_hbm_bytes_read;
    wire [31:0] dma_done_sram_write_count;
    wire [31:0] dma_done_sram_bytes_written;
    wire dma_sram_write_valid;
    wire dma_sram_write_ready;
    wire [63:0] dma_sram_write_address;
    wire [127:0] dma_sram_write_data;
    wire [15:0] dma_sram_write_byte_enable;

    wire rms_cmd_valid = state == STATE_DISPATCH_RMS;
    wire rms_cmd_ready;
    wire rms_done_valid;
    wire rms_done_ready = state == STATE_WAIT_RMS;
    wire [7:0] rms_done_error;
    wire [31:0] rms_done_command_index;
    wire [31:0] rms_done_row_count;
    wire [31:0] rms_done_element_count;
    wire [31:0] rms_done_normalized_saturation_count;
    wire [31:0] rms_done_output_saturation_count;
    wire [31:0] rms_done_sram_input_read_count;
    wire [31:0] rms_done_sram_weight_read_count;
    wire [31:0] rms_done_sram_write_count;
    wire [31:0] rms_done_mean_square_code;
    wire [31:0] rms_done_inverse_rms_code;
    wire rms_sram_read_valid;
    wire rms_sram_read_ready;
    wire [63:0] rms_sram_read_address;
    wire rms_sram_response_ready;
    wire rms_sram_write_valid;
    wire rms_sram_write_ready;
    wire [63:0] rms_sram_write_address;
    wire [15:0] rms_sram_write_data;
    wire [1:0] rms_sram_write_byte_enable;

    assign dma_sram_write_ready = (state == STATE_WAIT_DMA) && sram_write_ready;
    assign rms_sram_write_ready = (state == STATE_WAIT_RMS) && sram_write_ready;
    assign sram_write_valid = state == STATE_WAIT_DMA
        ? dma_sram_write_valid
        : state == STATE_WAIT_RMS ? rms_sram_write_valid : 1'b0;
    assign sram_write_address = state == STATE_WAIT_DMA
        ? dma_sram_write_address : rms_sram_write_address;
    assign sram_write_data = state == STATE_WAIT_DMA
        ? dma_sram_write_data : {112'b0, rms_sram_write_data};
    assign sram_write_byte_enable = state == STATE_WAIT_DMA
        ? dma_sram_write_byte_enable : {14'b0, rms_sram_write_byte_enable};
    assign sram_read_valid = (state == STATE_WAIT_RMS) && rms_sram_read_valid;
    assign rms_sram_read_ready = (state == STATE_WAIT_RMS) && sram_read_ready;
    assign sram_read_address = rms_sram_read_address;
    assign sram_response_ready =
        (state == STATE_WAIT_RMS) && rms_sram_response_ready;

    ot_ta_dma_hbm_to_sram #(.MAX_TRANSFER_BYTES(MAX_TRANSFER_BYTES)) dma_engine (
        .clk(clk), .rst_n(rst_n), .cmd_valid(dma_cmd_valid),
        .cmd_ready(dma_cmd_ready), .abi_major(buffered_abi_major),
        .abi_minor(buffered_abi_minor),
        .expected_command_index(buffered_expected_index),
        .command_record(buffered_record),
        .hbm_request_valid(hbm_request_valid),
        .hbm_request_ready(hbm_request_ready),
        .hbm_request_address(hbm_request_address),
        .hbm_request_bytes(hbm_request_bytes),
        .hbm_response_valid(hbm_response_valid),
        .hbm_response_ready(hbm_response_ready),
        .hbm_response_data(hbm_response_data),
        .hbm_response_error(hbm_response_error),
        .sram_write_valid(dma_sram_write_valid),
        .sram_write_ready(dma_sram_write_ready),
        .sram_write_address(dma_sram_write_address),
        .sram_write_data(dma_sram_write_data),
        .sram_write_byte_enable(dma_sram_write_byte_enable),
        .done_valid(dma_done_valid), .done_ready(dma_done_ready),
        .done_error(dma_done_error),
        .done_command_index(dma_done_command_index),
        .done_hbm_request_count(dma_done_hbm_request_count),
        .done_hbm_response_count(dma_done_hbm_response_count),
        .done_hbm_bytes_read(dma_done_hbm_bytes_read),
        .done_sram_write_count(dma_done_sram_write_count),
        .done_sram_bytes_written(dma_done_sram_bytes_written)
    );

    ot_ta_head_rmsnorm_bf16_sram_engine #(
        .PROFILE_COMMAND0_INDEX(KERNEL0_LAST_COMMAND_INDEX),
        .PROFILE_KERNEL0_INDEX(KERNEL0_INDEX), .PROFILE_ROWS0(KERNEL0_ROWS),
        .PROFILE_COMMAND1_INDEX(KERNEL1_LAST_COMMAND_INDEX),
        .PROFILE_KERNEL1_INDEX(KERNEL1_INDEX), .PROFILE_ROWS1(KERNEL1_ROWS)
    ) rmsnorm_engine (
        .clk(clk), .rst_n(rst_n), .cmd_valid(rms_cmd_valid),
        .cmd_ready(rms_cmd_ready), .abi_major(buffered_abi_major),
        .abi_minor(buffered_abi_minor),
        .expected_command_index(buffered_expected_index),
        .command_record(buffered_record),
        .sram_read_valid(rms_sram_read_valid),
        .sram_read_ready(rms_sram_read_ready),
        .sram_read_address(rms_sram_read_address),
        .sram_response_valid(sram_response_valid),
        .sram_response_ready(rms_sram_response_ready),
        .sram_response_data(sram_response_data),
        .sram_write_valid(rms_sram_write_valid),
        .sram_write_ready(rms_sram_write_ready),
        .sram_write_address(rms_sram_write_address),
        .sram_write_data(rms_sram_write_data),
        .sram_write_byte_enable(rms_sram_write_byte_enable),
        .done_valid(rms_done_valid), .done_ready(rms_done_ready),
        .done_error(rms_done_error),
        .done_command_index(rms_done_command_index),
        .done_row_count(rms_done_row_count),
        .done_element_count(rms_done_element_count),
        .done_normalized_saturation_count(rms_done_normalized_saturation_count),
        .done_output_saturation_count(rms_done_output_saturation_count),
        .done_sram_input_read_count(rms_done_sram_input_read_count),
        .done_sram_weight_read_count(rms_done_sram_weight_read_count),
        .done_sram_write_count(rms_done_sram_write_count),
        .done_mean_square_code(rms_done_mean_square_code),
        .done_inverse_rms_code(rms_done_inverse_rms_code)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= STATE_ACCEPT;
            active_program <= 1'b0;
            last_accepted_index <= 0;
            buffered_record <= 0;
            buffered_expected_index <= 0;
            buffered_abi_major <= 0;
            buffered_abi_minor <= 0;
            buffered_last <= 1'b0;
            program_done_valid <= 1'b0;
            program_done_error <= ERR_NONE;
            program_done_failing_command_index <= NO_FAILING_INDEX;
            program_done_last_command_index <= 0;
            program_done_commands_accepted <= 0;
            program_done_commands_completed <= 0;
            program_done_hbm_request_count <= 0;
            program_done_hbm_response_count <= 0;
            program_done_hbm_bytes_read <= 0;
            program_done_sram_read_count <= 0;
            program_done_sram_bytes_read <= 0;
            program_done_sram_write_count <= 0;
            program_done_sram_bytes_written <= 0;
            program_done_row_count <= 0;
            program_done_element_count <= 0;
            program_done_normalized_saturation_count <= 0;
            program_done_output_saturation_count <= 0;
            program_done_mean_square_code <= 0;
            program_done_inverse_rms_code <= 0;
        end else begin
            if (program_done_valid && program_done_ready) begin
                program_done_valid <= 1'b0;
                active_program <= 1'b0;
                state <= STATE_ACCEPT;
            end

            if (command_fire) begin
                if (first_command) begin
                    active_program <= 1'b1;
                    program_done_error <= ERR_NONE;
                    program_done_failing_command_index <= NO_FAILING_INDEX;
                    program_done_last_command_index <= 0;
                    program_done_commands_accepted <= 1;
                    program_done_commands_completed <= 0;
                    program_done_hbm_request_count <= 0;
                    program_done_hbm_response_count <= 0;
                    program_done_hbm_bytes_read <= 0;
                    program_done_sram_read_count <= 0;
                    program_done_sram_bytes_read <= 0;
                    program_done_sram_write_count <= 0;
                    program_done_sram_bytes_written <= 0;
                    program_done_row_count <= 0;
                    program_done_element_count <= 0;
                    program_done_normalized_saturation_count <= 0;
                    program_done_output_saturation_count <= 0;
                    program_done_mean_square_code <= 0;
                    program_done_inverse_rms_code <= 0;
                end else begin
                    program_done_commands_accepted <=
                        program_done_commands_accepted + 1'b1;
                end
                if (!command_in_order || !command_profile_legal) begin
                    program_done_valid <= 1'b1;
                    program_done_error <= ERR_PROGRAM_ORDER;
                    program_done_failing_command_index <= expected_command_index;
                    program_done_last_command_index <= expected_command_index;
                    state <= STATE_DONE;
                end else begin
                    last_accepted_index <= expected_command_index;
                    buffered_record <= command_record;
                    buffered_expected_index <= expected_command_index;
                    buffered_abi_major <= abi_major;
                    buffered_abi_minor <= abi_minor;
                    buffered_last <= cmd_last;
                    if (command_record[7:0] == OP_DMA_DIRECT)
                        state <= STATE_DISPATCH_DMA;
                    else if (command_record[7:0] == OP_RMSNORM)
                        state <= STATE_DISPATCH_RMS;
                    else begin
                        program_done_valid <= 1'b1;
                        program_done_error <= ERR_UNSUPPORTED_OPCODE;
                        program_done_failing_command_index <=
                            expected_command_index;
                        program_done_last_command_index <= expected_command_index;
                        state <= STATE_DONE;
                    end
                end
            end

            if (state == STATE_DISPATCH_DMA && dma_cmd_ready)
                state <= STATE_WAIT_DMA;
            if (state == STATE_DISPATCH_RMS && rms_cmd_ready)
                state <= STATE_WAIT_RMS;

            if (state == STATE_WAIT_DMA && dma_done_valid) begin
                program_done_last_command_index <= dma_done_command_index;
                program_done_hbm_request_count <=
                    program_done_hbm_request_count + dma_done_hbm_request_count;
                program_done_hbm_response_count <=
                    program_done_hbm_response_count + dma_done_hbm_response_count;
                program_done_hbm_bytes_read <=
                    program_done_hbm_bytes_read + dma_done_hbm_bytes_read;
                program_done_sram_write_count <=
                    program_done_sram_write_count + dma_done_sram_write_count;
                program_done_sram_bytes_written <=
                    program_done_sram_bytes_written + dma_done_sram_bytes_written;
                if (dma_done_error != ERR_NONE) begin
                    program_done_valid <= 1'b1;
                    program_done_error <= dma_done_error;
                    program_done_failing_command_index <= dma_done_command_index;
                    state <= STATE_DONE;
                end else begin
                    program_done_commands_completed <=
                        program_done_commands_completed + 1'b1;
                    if (buffered_last) begin
                        program_done_valid <= 1'b1;
                        program_done_failing_command_index <= NO_FAILING_INDEX;
                        state <= STATE_DONE;
                    end else begin
                        state <= STATE_ACCEPT;
                    end
                end
            end

            if (state == STATE_WAIT_RMS && rms_done_valid) begin
                program_done_last_command_index <= rms_done_command_index;
                program_done_sram_read_count <= program_done_sram_read_count +
                    rms_done_sram_input_read_count +
                    rms_done_sram_weight_read_count;
                program_done_sram_bytes_read <= program_done_sram_bytes_read +
                    ((rms_done_sram_input_read_count +
                      rms_done_sram_weight_read_count) << 1);
                program_done_sram_write_count <= program_done_sram_write_count +
                    rms_done_sram_write_count;
                program_done_sram_bytes_written <=
                    program_done_sram_bytes_written +
                    (rms_done_sram_write_count << 1);
                program_done_row_count <=
                    program_done_row_count + rms_done_row_count;
                program_done_element_count <=
                    program_done_element_count + rms_done_element_count;
                program_done_normalized_saturation_count <=
                    program_done_normalized_saturation_count +
                    rms_done_normalized_saturation_count;
                program_done_output_saturation_count <=
                    program_done_output_saturation_count +
                    rms_done_output_saturation_count;
                program_done_mean_square_code <= rms_done_mean_square_code;
                program_done_inverse_rms_code <= rms_done_inverse_rms_code;
                if (rms_done_error != ERR_NONE) begin
                    program_done_valid <= 1'b1;
                    program_done_error <= rms_done_error;
                    program_done_failing_command_index <= rms_done_command_index;
                    state <= STATE_DONE;
                end else begin
                    program_done_commands_completed <=
                        program_done_commands_completed + 1'b1;
                    if (buffered_last) begin
                        program_done_valid <= 1'b1;
                        program_done_error <= ERR_NONE;
                        program_done_failing_command_index <= NO_FAILING_INDEX;
                        state <= STATE_DONE;
                    end else begin
                        state <= STATE_ACCEPT;
                    end
                end
            end
        end
    end
endmodule
