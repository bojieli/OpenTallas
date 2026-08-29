`timescale 1ns/1ps
// Registered admission boundary for the production tensor-accelerator command
// ABI.  The 64-byte record layout, reflected IEEE CRC32, opcode/minor mapping,
// engine mapping, and field legality mirror production_command.py.  This block
// intentionally decodes one record at a time; stream-level header/body CRC and
// terminal-COMPLETE ordering remain command-processor responsibilities.
module ot_ta_command_decoder (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         in_valid,
    output wire         in_ready,
    input  wire [15:0]  abi_major,
    input  wire [15:0]  abi_minor,
    input  wire [31:0]  expected_index,
    input  wire [511:0] command_record,
    output reg          out_valid,
    input  wire         out_ready,
    output reg          out_legal,
    output reg  [3:0]   out_error,
    output reg  [7:0]   out_opcode,
    output reg  [7:0]   out_engine,
    output reg  [15:0]  out_flags,
    output reg  [31:0]  out_index,
    output reg  [31:0]  out_kernel_index,
    output reg  [63:0]  out_source0,
    output reg  [63:0]  out_source1,
    output reg  [63:0]  out_destination,
    output reg  [63:0]  out_auxiliary,
    output reg  [31:0]  out_size0,
    output reg  [31:0]  out_size1,
    output reg  [31:0]  out_size2,
    output reg  [31:0]  out_size3
);
    localparam [3:0] ERR_NONE   = 4'd0;
    localparam [3:0] ERR_CRC    = 4'd1;
    localparam [3:0] ERR_OPCODE = 4'd2;
    localparam [3:0] ERR_ENGINE = 4'd3;
    localparam [3:0] ERR_ABI    = 4'd4;
    localparam [3:0] ERR_FIELD  = 4'd5;
    localparam [3:0] ERR_INDEX  = 4'd6;

    localparam [7:0] OP_DMA_DIRECT  = 8'h01;
    localparam [7:0] OP_DMA_INDEXED = 8'h02;
    localparam [7:0] OP_SRAM_INDEX  = 8'h03;
    localparam [7:0] OP_MATMUL       = 8'h10;
    localparam [7:0] OP_RMSNORM      = 8'h20;
    localparam [7:0] OP_ROPE         = 8'h21;
    localparam [7:0] OP_ADD          = 8'h22;
    localparam [7:0] OP_SILU_MUL     = 8'h23;
    localparam [7:0] OP_KV_PREPARE   = 8'h30;
    localparam [7:0] OP_ATTENTION    = 8'h31;
    localparam [7:0] OP_STATE_COMMIT = 8'h32;
    localparam [7:0] OP_COMPLETE     = 8'hff;

    localparam [7:0] ENGINE_CONTROL = 8'd0;
    localparam [7:0] ENGINE_DMA     = 8'd1;
    localparam [7:0] ENGINE_TENSOR  = 8'd2;
    localparam [7:0] ENGINE_VECTOR  = 8'd3;
    localparam [7:0] ENGINE_STATE   = 8'd4;
    localparam [31:0] NO_KERNEL = 32'hffff_ffff;

    wire [7:0]  opcode      = command_record[7:0];
    wire [7:0]  engine      = command_record[15:8];
    wire [15:0] flags       = command_record[31:16];
    wire [31:0] index       = command_record[63:32];
    wire [31:0] kernel      = command_record[95:64];
    wire [63:0] source0     = command_record[159:96];
    wire [63:0] source1     = command_record[223:160];
    wire [63:0] destination = command_record[287:224];
    wire [63:0] auxiliary   = command_record[351:288];
    wire [31:0] size0       = command_record[383:352];
    wire [31:0] size1       = command_record[415:384];
    wire [31:0] size2       = command_record[447:416];
    wire [31:0] size3       = command_record[479:448];
    wire [31:0] supplied_crc = command_record[511:480];

    reg [7:0] expected_engine;
    reg [15:0] minimum_minor;
    reg opcode_known;
    reg fields_legal;
    reg [3:0] error_comb;

    function automatic [31:0] crc32_ieee;
        input [479:0] payload;
        integer byte_index;
        integer bit_index;
        reg [31:0] crc;
        reg feedback;
        begin
            crc = 32'hffff_ffff;
            for (byte_index = 0; byte_index < 60; byte_index = byte_index + 1) begin
                for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1) begin
                    feedback = crc[0] ^ payload[byte_index*8 + bit_index];
                    crc = crc >> 1;
                    if (feedback)
                        crc = crc ^ 32'hedb8_8320;
                end
            end
            crc32_ieee = ~crc;
        end
    endfunction

    always @* begin
        opcode_known = 1'b1;
        expected_engine = ENGINE_CONTROL;
        minimum_minor = 16'd0;
        case (opcode)
            OP_DMA_DIRECT: begin
                expected_engine = ENGINE_DMA;
                minimum_minor = 16'd0;
            end
            OP_DMA_INDEXED: begin
                expected_engine = ENGINE_DMA;
                minimum_minor = 16'd1;
            end
            OP_SRAM_INDEX: begin
                expected_engine = ENGINE_DMA;
                minimum_minor = 16'd5;
            end
            OP_MATMUL: begin
                expected_engine = ENGINE_TENSOR;
                minimum_minor = 16'd0;
            end
            OP_RMSNORM: begin
                expected_engine = ENGINE_VECTOR;
                minimum_minor = 16'd1;
            end
            OP_ROPE: begin
                expected_engine = ENGINE_VECTOR;
                minimum_minor = 16'd2;
            end
            OP_ADD, OP_SILU_MUL: begin
                expected_engine = ENGINE_VECTOR;
                minimum_minor = 16'd4;
            end
            OP_KV_PREPARE, OP_STATE_COMMIT: begin
                expected_engine = ENGINE_STATE;
                minimum_minor = 16'd3;
            end
            OP_ATTENTION: begin
                expected_engine = ENGINE_VECTOR;
                minimum_minor = 16'd3;
            end
            OP_COMPLETE: begin
                expected_engine = ENGINE_CONTROL;
                minimum_minor = 16'd0;
            end
            default: begin
                opcode_known = 1'b0;
                expected_engine = ENGINE_CONTROL;
                minimum_minor = 16'hffff;
            end
        endcase
    end

    always @* begin
        fields_legal = 1'b0;
        case (opcode)
            OP_DMA_DIRECT:
                fields_legal = (flags == 0) && (kernel != NO_KERNEL) &&
                               (size0 != 0) && (source1 == 0) &&
                               (auxiliary == 0) && (size1 == 0) &&
                               (size2 == 0) && (size3 == 0);
            OP_DMA_INDEXED, OP_SRAM_INDEX:
                fields_legal = (flags == 0) && (kernel != NO_KERNEL) &&
                               (size0 != 0) && (size1 != 0) &&
                               (size2 != 0) && (size3 == 4);
            OP_MATMUL:
                fields_legal = ((flags & 16'hfffc) == 0) &&
                               (kernel != NO_KERNEL) && (size0 != 0) &&
                               (size1 != 0) && (size2 != 0) && (size3 == 0);
            OP_RMSNORM:
                fields_legal = (flags == 0) && (kernel != NO_KERNEL) &&
                               (size0 != 0) && (size1 != 0) &&
                               (size2 != 0) && (size3 == 0) && (auxiliary == 0);
            OP_ROPE:
                fields_legal = (flags == 0) && (kernel != NO_KERNEL) &&
                               (size0 != 0) && (size1 != 0) &&
                               (size2 != 0) && (size3 != 0);
            OP_ADD, OP_SILU_MUL:
                fields_legal = (flags == 0) && (kernel != NO_KERNEL) &&
                               (auxiliary == 0) && (size0 != 0) &&
                               (size1 != 0) && (size2 == 0) && (size3 == 0);
            OP_KV_PREPARE, OP_ATTENTION:
                fields_legal = (flags == 0) && (kernel != NO_KERNEL) &&
                               (source0 != 0) && (source1 != 0) &&
                               (destination != 0) && (auxiliary != 0) &&
                               (size0 != 0) && (size1 != 0) && (size2 != 0);
            OP_STATE_COMMIT:
                fields_legal = (flags == 0) && (kernel == NO_KERNEL) &&
                               (source0 != 0) && (source1 != 0) &&
                               (destination == 0) && (auxiliary == 0) &&
                               (size0 != 0) && (size1 != 0) &&
                               (size2 == 0) && (size3 == 0);
            OP_COMPLETE:
                fields_legal = (flags == 0) && (kernel == NO_KERNEL) &&
                               (source0 == 0) && (source1 == 0) &&
                               (destination == 0) && (auxiliary == 0) &&
                               (size0 == 0) && (size1 == 0) &&
                               (size2 == 0) && (size3 == 0);
            default: fields_legal = 1'b0;
        endcase
    end

    always @* begin
        if (crc32_ieee(command_record[479:0]) != supplied_crc)
            error_comb = ERR_CRC;
        else if (!opcode_known)
            error_comb = ERR_OPCODE;
        else if (engine != expected_engine)
            error_comb = ERR_ENGINE;
        else if ((abi_major != 16'd2) || (abi_minor > 16'd5) ||
                 (abi_minor < minimum_minor))
            error_comb = ERR_ABI;
        else if (!fields_legal)
            error_comb = ERR_FIELD;
        else if (index != expected_index)
            error_comb = ERR_INDEX;
        else
            error_comb = ERR_NONE;
    end

    assign in_ready = !out_valid || out_ready;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_valid <= 1'b0;
            out_legal <= 1'b0;
            out_error <= ERR_NONE;
            out_opcode <= 0;
            out_engine <= 0;
            out_flags <= 0;
            out_index <= 0;
            out_kernel_index <= 0;
            out_source0 <= 0;
            out_source1 <= 0;
            out_destination <= 0;
            out_auxiliary <= 0;
            out_size0 <= 0;
            out_size1 <= 0;
            out_size2 <= 0;
            out_size3 <= 0;
        end else if (in_ready) begin
            out_valid <= in_valid;
            if (in_valid) begin
                out_legal <= (error_comb == ERR_NONE);
                out_error <= error_comb;
                out_opcode <= opcode;
                out_engine <= engine;
                out_flags <= flags;
                out_index <= index;
                out_kernel_index <= kernel;
                out_source0 <= source0;
                out_source1 <= source1;
                out_destination <= destination;
                out_auxiliary <= auxiliary;
                out_size0 <= size0;
                out_size1 <= size1;
                out_size2 <= size2;
                out_size3 <= size3;
            end
        end
    end
endmodule
