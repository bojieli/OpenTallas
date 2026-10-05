`timescale 1ns/1ps
// Data-bearing execution boundary for one production ADD_BF16 command.  The
// production decoder admits the command record; this block then exposes the
// exact SRAM byte addresses while accepting and retiring one operand/result
// element per ready/valid transfer.  Memory macros remain outside this module.
module ot_ta_add_bf16_executor #(
    parameter [31:0] MAX_ELEMENTS = 32'd1048576
) (
    input  wire         clk,
    input  wire         rst_n,

    input  wire         cmd_valid,
    output wire         cmd_ready,
    input  wire [15:0]  abi_major,
    input  wire [15:0]  abi_minor,
    input  wire [31:0]  expected_command_index,
    input  wire [511:0] command_record,

    input  wire         operand_valid,
    output wire         operand_ready,
    input  wire [15:0]  operand_left,
    input  wire [15:0]  operand_right,
    output wire [31:0]  operand_index,
    output wire [63:0]  operand_source0_address,
    output wire [63:0]  operand_source1_address,

    output reg          result_valid,
    input  wire         result_ready,
    output reg  [15:0]  result_code,
    output reg          result_saturated,
    output reg  [1:0]   result_error,
    output reg  [31:0]  result_index,
    output reg  [63:0]  result_destination_address,

    output reg          done_valid,
    input  wire         done_ready,
    output reg  [7:0]   done_error,
    output reg  [31:0]  done_command_index,
    output reg  [31:0]  done_element_count,
    output reg  [31:0]  done_saturation_count
);
    localparam [7:0] OP_ADD = 8'h22;
    localparam [7:0] ERR_NONE = 8'd0;
    localparam [7:0] ERR_UNSUPPORTED_OPCODE = 8'd7;
    localparam [7:0] ERR_SIZE = 8'd8;
    localparam [7:0] ERR_OPERAND_NONFINITE = 8'd9;
    localparam [7:0] ERR_ARITHMETIC_OVERFLOW = 8'd10;

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
    wire [63:0] decoder_source1;
    wire [63:0] decoder_destination;
    wire [63:0] decoder_unused_auxiliary;
    wire [31:0] decoder_size0;
    wire [31:0] decoder_size1;
    wire [31:0] decoder_unused_size2;
    wire [31:0] decoder_unused_size3;
    wire decoder_out_ready = !active && !done_valid;

    wire [63:0] decoded_element_count =
        {32'b0, decoder_size0} * {32'b0, decoder_size1};
    reg active;
    reg fault_pending;
    reg [31:0] target_elements;
    reg [31:0] accepted_elements;
    reg [31:0] retired_elements;
    reg [31:0] saturation_count;
    reg [63:0] source0_base;
    reg [63:0] source1_base;
    reg [63:0] destination_base;

    wire [15:0] add_result;
    wire add_saturated;
    wire [1:0] add_error;
    wire accept_operand = operand_valid && operand_ready;
    wire retire_result = result_valid && result_ready;

    assign cmd_ready = decoder_in_ready && !active && !done_valid;
    assign operand_ready = active && !fault_pending &&
                           (accepted_elements < target_elements) &&
                           (!result_valid || result_ready);
    assign operand_index = accepted_elements;
    assign operand_source0_address = source0_base +
                                     {31'b0, accepted_elements, 1'b0};
    assign operand_source1_address = source1_base +
                                     {31'b0, accepted_elements, 1'b0};

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
        .out_source1(decoder_source1),
        .out_destination(decoder_destination),
        .out_auxiliary(decoder_unused_auxiliary),
        .out_size0(decoder_size0),
        .out_size1(decoder_size1),
        .out_size2(decoder_unused_size2),
        .out_size3(decoder_unused_size3)
    );

    ot_bf16_add_rne add (
        .left_code(operand_left),
        .right_code(operand_right),
        .result_code(add_result),
        .result_saturated(add_saturated),
        .result_error(add_error)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0;
            fault_pending <= 1'b0;
            target_elements <= 0;
            accepted_elements <= 0;
            retired_elements <= 0;
            saturation_count <= 0;
            source0_base <= 0;
            source1_base <= 0;
            destination_base <= 0;
            result_valid <= 1'b0;
            result_code <= 0;
            result_saturated <= 1'b0;
            result_error <= 0;
            result_index <= 0;
            result_destination_address <= 0;
            done_valid <= 1'b0;
            done_error <= ERR_NONE;
            done_command_index <= 0;
            done_element_count <= 0;
            done_saturation_count <= 0;
        end else begin
            if (done_valid && done_ready)
                done_valid <= 1'b0;

            if (decoder_out_valid && decoder_out_ready) begin
                done_command_index <= decoder_index;
                done_element_count <= 0;
                done_saturation_count <= 0;
                if (!decoder_out_legal) begin
                    done_valid <= 1'b1;
                    done_error <= {4'b0, decoder_out_error};
                end else if (decoder_opcode != OP_ADD) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_UNSUPPORTED_OPCODE;
                end else if ((decoded_element_count == 0) ||
                             (decoded_element_count > {32'b0, MAX_ELEMENTS})) begin
                    done_valid <= 1'b1;
                    done_error <= ERR_SIZE;
                end else begin
                    active <= 1'b1;
                    fault_pending <= 1'b0;
                    target_elements <= decoded_element_count[31:0];
                    accepted_elements <= 0;
                    retired_elements <= 0;
                    saturation_count <= 0;
                    source0_base <= decoder_source0;
                    source1_base <= decoder_source1;
                    destination_base <= decoder_destination;
                    done_error <= ERR_NONE;
                end
            end

            if (!result_valid || result_ready) begin
                result_valid <= accept_operand;
                if (accept_operand) begin
                    result_code <= add_result;
                    result_saturated <= add_saturated;
                    result_error <= add_error;
                    result_index <= accepted_elements;
                    result_destination_address <= destination_base +
                                                  {31'b0, accepted_elements, 1'b0};
                    accepted_elements <= accepted_elements + 1'b1;
                    if (add_error != 0)
                        fault_pending <= 1'b1;
                end
            end

            if (retire_result) begin
                retired_elements <= retired_elements + 1'b1;
                if (result_saturated)
                    saturation_count <= saturation_count + 1'b1;
                if ((result_error != 0) ||
                    (retired_elements + 1'b1 == target_elements)) begin
                    active <= 1'b0;
                    fault_pending <= 1'b0;
                    done_valid <= 1'b1;
                    done_error <= result_error == 2'd1
                                  ? ERR_OPERAND_NONFINITE
                                  : result_error == 2'd2
                                    ? ERR_ARITHMETIC_OVERFLOW : ERR_NONE;
                    done_element_count <= retired_elements + 1'b1;
                    done_saturation_count <= saturation_count +
                                             (result_saturated ? 32'd1 : 32'd0);
                end
            end
        end
    end
endmodule
