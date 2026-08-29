`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 device-program header admission (wire format section 2).
//
// The 256-byte header is admitted as sixty-four little-endian 32-bit beats,
// four checksummed bytes per cycle, matching the instruction decoder's CRC
// discipline.  Word 63 carries the header CRC field and is checksummed as zero
// because runtime/abi3/crc.record_crc zeroes a record's own CRC field rather
// than excluding it from the span.
//
// Check order mirrors the normative decoder in runtime/abi3/records.py, which
// validates the layout (magic, reserved-zero spans) before the CRC and the
// version/size/count rules after it.  A header with several defects therefore
// reports the same trap class in RTL and in the reference implementation:
//   magic or reserved bytes -> class 1 (admission or version)
//   header CRC              -> class 2 (authentication or integrity)
//   version, sizes, counts  -> class 1 (admission or version)
//
// Not checked here: the deployment, descriptor-table, topology and body
// SHA-256 digests.  A 256-bit digest engine is a separate admission block; a
// program whose body digest is wrong but whose per-instruction CRCs pass is
// still rejected instruction by instruction, never issued as work.
// ---------------------------------------------------------------------------
module ot_a3_program_header
    import ot_a3_pkg::*;
(
    input  wire        clk,
    input  wire        rst_n,

    input  wire        in_valid,
    input  wire        in_start,          // asserted with the first of 64 beats
    input  wire [31:0] in_word,

    output reg         out_valid,         // one-cycle pulse after the last beat
    output reg         out_legal,
    output reg  [3:0]  out_error,
    output reg  [15:0] out_trap_class,
    output reg  [7:0]  out_abi_major,
    output reg  [7:0]  out_abi_minor,
    output reg  [15:0] out_flags,
    output reg  [31:0] out_instruction_count,
    output reg  [31:0] out_entrypoint_count,
    output reg  [63:0] out_max_retired_work,
    output reg  [31:0] out_watchdog_class,
    output reg  [31:0] out_entrypoint_table_descriptor,
    output reg  [31:0] out_signature_descriptor
);
    localparam [5:0] WORD_MAGIC_LO   = 6'd0;
    localparam [5:0] WORD_MAGIC_HI   = 6'd1;
    localparam [5:0] WORD_VERSION    = 6'd2;
    localparam [5:0] WORD_SIZES      = 6'd3;
    localparam [5:0] WORD_INSTR_CNT  = 6'd4;
    localparam [5:0] WORD_ENTRY_CNT  = 6'd5;
    localparam [5:0] WORD_WORK_LO    = 6'd46;
    localparam [5:0] WORD_WORK_HI    = 6'd47;
    localparam [5:0] WORD_WATCHDOG   = 6'd48;
    localparam [5:0] WORD_ENTRY_DESC = 6'd49;
    localparam [5:0] WORD_SIG_DESC   = 6'd50;
    localparam [5:0] WORD_RESERVED_0 = 6'd51;
    localparam [5:0] WORD_RESERVED_N = 6'd62;
    localparam [5:0] WORD_CRC        = 6'd63;

    reg [5:0]  word_index;
    reg [31:0] crc_state;
    reg        magic_bad;
    reg        reserved_bad;
    reg [7:0]  abi_major;
    reg [7:0]  abi_minor;
    reg [15:0] header_bytes;
    reg [15:0] instruction_bytes;
    reg [15:0] header_flags;
    reg [31:0] instruction_count;
    reg [31:0] entrypoint_count;
    reg [31:0] work_lo;
    reg [31:0] work_hi;
    reg [31:0] watchdog_class;
    reg [31:0] entry_descriptor;
    reg [31:0] signature_descriptor;

    wire [5:0]  active_index = in_start ? 6'd0 : word_index;
    wire [31:0] active_state = in_start ? 32'hffff_ffff : crc_state;
    // The CRC field is treated as zero while the record CRC is calculated.
    wire [31:0] checksum_word =
        (active_index == WORD_CRC) ? 32'h0000_0000 : in_word;
    wire [31:0] crc_next = a3_crc32c_word(active_state, checksum_word);
    wire [31:0] crc_final = crc_next ^ 32'hffff_ffff;

    wire magic_lo_bad = (active_index == WORD_MAGIC_LO) &&
                        (in_word != A3_PROGRAM_MAGIC[31:0]);
    wire magic_hi_bad = (active_index == WORD_MAGIC_HI) &&
                        (in_word != A3_PROGRAM_MAGIC[63:32]);
    wire reserved_now = (active_index >= WORD_RESERVED_0) &&
                        (active_index <= WORD_RESERVED_N) &&
                        (in_word != 32'h0000_0000);

    reg [3:0] error_comb;
    always @* begin
        if (magic_bad)
            error_comb = A3_ERR_MAGIC;
        else if (reserved_bad)
            error_comb = A3_ERR_RESERVED;
        else if (crc_final != in_word)
            error_comb = A3_ERR_CRC;
        else if ((abi_major != A3_ABI_MAJOR) || (abi_minor > A3_ABI_MINOR))
            error_comb = A3_ERR_VERSION;
        else if ((header_bytes != 16'd256) || (instruction_bytes != 16'd32))
            error_comb = A3_ERR_SIZE;
        else if (header_flags != 16'h0000)
            error_comb = A3_ERR_VERSION;
        else if ((instruction_count == 32'd0) || (entrypoint_count == 32'd0))
            error_comb = A3_ERR_COUNT;
        else
            error_comb = A3_ERR_NONE;
    end

    function automatic [15:0] trap_of_error;
        input [3:0] error;
        begin
            if (error == A3_ERR_NONE)
                trap_of_error = A3_TRAP_NONE;
            else if (error == A3_ERR_CRC)
                trap_of_error = A3_TRAP_INTEGRITY;
            else
                trap_of_error = A3_TRAP_ADMISSION;
        end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            word_index <= 6'd0;
            crc_state <= 32'hffff_ffff;
            magic_bad <= 1'b0;
            reserved_bad <= 1'b0;
            abi_major <= 8'd0;
            abi_minor <= 8'd0;
            header_bytes <= 16'd0;
            instruction_bytes <= 16'd0;
            header_flags <= 16'd0;
            instruction_count <= 32'd0;
            entrypoint_count <= 32'd0;
            work_lo <= 32'd0;
            work_hi <= 32'd0;
            watchdog_class <= 32'd0;
            entry_descriptor <= A3_NO_ID;
            signature_descriptor <= A3_NO_ID;
            out_valid <= 1'b0;
            out_legal <= 1'b0;
            out_error <= A3_ERR_NONE;
            out_trap_class <= A3_TRAP_NONE;
            out_abi_major <= 8'd0;
            out_abi_minor <= 8'd0;
            out_flags <= 16'd0;
            out_instruction_count <= 32'd0;
            out_entrypoint_count <= 32'd0;
            out_max_retired_work <= 64'd0;
            out_watchdog_class <= 32'd0;
            out_entrypoint_table_descriptor <= A3_NO_ID;
            out_signature_descriptor <= A3_NO_ID;
        end else begin
            out_valid <= 1'b0;
            if (in_valid) begin
                if (in_start) begin
                    magic_bad <= magic_lo_bad;
                    reserved_bad <= 1'b0;
                end else begin
                    magic_bad <= magic_bad | magic_lo_bad | magic_hi_bad;
                    reserved_bad <= reserved_bad | reserved_now;
                end
                case (active_index)
                    WORD_VERSION: begin
                        abi_major <= in_word[7:0];
                        abi_minor <= in_word[15:8];
                        header_bytes <= in_word[31:16];
                    end
                    WORD_SIZES: begin
                        instruction_bytes <= in_word[15:0];
                        header_flags <= in_word[31:16];
                    end
                    WORD_INSTR_CNT:  instruction_count <= in_word;
                    WORD_ENTRY_CNT:  entrypoint_count <= in_word;
                    WORD_WORK_LO:    work_lo <= in_word;
                    WORD_WORK_HI:    work_hi <= in_word;
                    WORD_WATCHDOG:   watchdog_class <= in_word;
                    WORD_ENTRY_DESC: entry_descriptor <= in_word;
                    WORD_SIG_DESC:   signature_descriptor <= in_word;
                    default: ;
                endcase
                if (active_index == WORD_CRC) begin
                    word_index <= 6'd0;
                    crc_state <= 32'hffff_ffff;
                    out_valid <= 1'b1;
                    out_legal <= (error_comb == A3_ERR_NONE);
                    out_error <= error_comb;
                    out_trap_class <= trap_of_error(error_comb);
                    out_abi_major <= abi_major;
                    out_abi_minor <= abi_minor;
                    out_flags <= header_flags;
                    out_instruction_count <= instruction_count;
                    out_entrypoint_count <= entrypoint_count;
                    out_max_retired_work <= {work_hi, work_lo};
                    out_watchdog_class <= watchdog_class;
                    out_entrypoint_table_descriptor <= entry_descriptor;
                    out_signature_descriptor <= signature_descriptor;
                end else begin
                    crc_state <= crc_next;
                    word_index <= active_index + 6'd1;
                end
            end
        end
    end
endmodule
