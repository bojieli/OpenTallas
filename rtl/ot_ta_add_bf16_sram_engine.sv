`timescale 1ns/1ps
// Memory-bound control for the production ADD_BF16 stream executor.  This
// block converts each decoded operand address into two ordered 16-bit SRAM
// reads and retires each finite result only when its SRAM write is accepted.
// It permits one outstanding read, so no response tag is required.  SRAM
// arrays, ECC, banking, arbitration, and physical macros remain external.
module ot_ta_add_bf16_sram_engine (
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

    output wire         done_valid,
    input  wire         done_ready,
    output wire [7:0]   done_error,
    output wire [31:0]  done_command_index,
    output wire [31:0]  done_element_count,
    output wire [31:0]  done_saturation_count,
    output reg  [31:0]  done_sram_read_count,
    output reg  [31:0]  done_sram_write_count
);
    localparam [2:0] FETCH_LEFT  = 3'd0;
    localparam [2:0] WAIT_LEFT   = 3'd1;
    localparam [2:0] FETCH_RIGHT = 3'd2;
    localparam [2:0] WAIT_RIGHT  = 3'd3;
    localparam [2:0] PAIR_READY  = 3'd4;

    reg [2:0] fetch_state;
    reg [15:0] left_data;
    reg [15:0] right_data;

    wire executor_operand_valid = fetch_state == PAIR_READY;
    wire executor_operand_ready;
    wire [31:0] executor_operand_index;
    wire [63:0] executor_source0_address;
    wire [63:0] executor_source1_address;
    wire executor_result_valid;
    wire executor_result_ready;
    wire [15:0] executor_result_code;
    wire executor_result_saturated;
    wire [1:0] executor_result_error;
    wire [31:0] executor_result_index;
    wire [63:0] executor_destination_address;

    wire read_request_state = (fetch_state == FETCH_LEFT) ||
                              (fetch_state == FETCH_RIGHT);
    wire read_request_fire = sram_read_valid && sram_read_ready;
    wire read_response_fire = sram_response_valid && sram_response_ready;
    wire operand_fire = executor_operand_valid && executor_operand_ready;
    wire write_fire = sram_write_valid && sram_write_ready;
    wire command_fire = cmd_valid && cmd_ready;

    assign sram_read_valid = read_request_state && executor_operand_ready;
    assign sram_read_address = fetch_state == FETCH_RIGHT
                               ? executor_source1_address
                               : executor_source0_address;
    assign sram_response_ready = (fetch_state == WAIT_LEFT) ||
                                 (fetch_state == WAIT_RIGHT);

    // Faulting arithmetic results are retired without modifying SRAM.  Their
    // error is propagated by the underlying executor's completion record.
    assign sram_write_valid = executor_result_valid &&
                              (executor_result_error == 0);
    assign sram_write_address = executor_destination_address;
    assign sram_write_data = executor_result_code;
    assign sram_write_byte_enable = 2'b11;
    assign executor_result_ready = executor_result_valid &&
                                   (executor_result_error != 0
                                    ? 1'b1 : sram_write_ready);

    ot_ta_add_bf16_executor executor (
        .clk(clk),
        .rst_n(rst_n),
        .cmd_valid(cmd_valid),
        .cmd_ready(cmd_ready),
        .abi_major(abi_major),
        .abi_minor(abi_minor),
        .expected_command_index(expected_command_index),
        .command_record(command_record),
        .operand_valid(executor_operand_valid),
        .operand_ready(executor_operand_ready),
        .operand_left(left_data),
        .operand_right(right_data),
        .operand_index(executor_operand_index),
        .operand_source0_address(executor_source0_address),
        .operand_source1_address(executor_source1_address),
        .result_valid(executor_result_valid),
        .result_ready(executor_result_ready),
        .result_code(executor_result_code),
        .result_saturated(executor_result_saturated),
        .result_error(executor_result_error),
        .result_index(executor_result_index),
        .result_destination_address(executor_destination_address),
        .done_valid(done_valid),
        .done_ready(done_ready),
        .done_error(done_error),
        .done_command_index(done_command_index),
        .done_element_count(done_element_count),
        .done_saturation_count(done_saturation_count)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fetch_state <= FETCH_LEFT;
            left_data <= 0;
            right_data <= 0;
            done_sram_read_count <= 0;
            done_sram_write_count <= 0;
        end else begin
            if (command_fire) begin
                fetch_state <= FETCH_LEFT;
                done_sram_read_count <= 0;
                done_sram_write_count <= 0;
            end

            if (read_request_fire) begin
                if (fetch_state == FETCH_LEFT)
                    fetch_state <= WAIT_LEFT;
                else if (fetch_state == FETCH_RIGHT)
                    fetch_state <= WAIT_RIGHT;
            end

            if (read_response_fire) begin
                done_sram_read_count <= done_sram_read_count + 1'b1;
                if (fetch_state == WAIT_LEFT) begin
                    left_data <= sram_response_data;
                    fetch_state <= FETCH_RIGHT;
                end else if (fetch_state == WAIT_RIGHT) begin
                    right_data <= sram_response_data;
                    fetch_state <= PAIR_READY;
                end
            end

            if (operand_fire)
                fetch_state <= FETCH_LEFT;

            if (write_fire)
                done_sram_write_count <= done_sram_write_count + 1'b1;
        end
    end

    // These status signals are deliberately consumed inside the wrapped
    // executor.  Naming them here keeps lint from confusing the interface
    // contract with accidental truncation.
    wire _unused_status = &{1'b0, executor_operand_index,
                            executor_result_saturated, executor_result_index};
endmodule
