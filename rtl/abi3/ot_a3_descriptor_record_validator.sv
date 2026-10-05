`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 fixed-descriptor integrity admission.
//
// The deployment loader authenticates the complete descriptor table before a
// program starts.  Focused engine adapters still need a local, synthesizable
// way to reject a corrupt record before it can cause a write.  This block
// checks one fixed descriptor record a word per cycle.  The record CRC follows
// the same rule as runtime/abi3/crc.py: bytes 48..51 are treated as zero while
// the reflected CRC32C is evaluated over the declared (and expected) record
// length.
//
// The input is the 192-byte descriptor-store beat used by the ABI 3.0 RTL.
// Shorter fixed records occupy its low bits and must have zero high padding.
// Typed payload semantics remain the responsibility of the consuming adapter;
// this boundary proves integrity and the common 64-byte header only.
// ---------------------------------------------------------------------------
module ot_a3_descriptor_record_validator (
    input  wire           clk,
    input  wire           rst_n,
    input  wire           start,
    input  wire [1535:0]  record,
    input  wire [15:0]    expected_type,
    input  wire [31:0]    expected_total_bytes,
    input  wire [31:0]    expected_payload_bytes,

    output reg            busy,
    output reg            done,
    output reg            legal,
    output reg  [7:0]     error_code
);
    localparam [31:0] DESC_MAGIC = 32'h4433_4154;
    localparam [7:0] TYPE_MAJOR = 8'd1;
    localparam [7:0] TYPE_MINOR = 8'd0;
    localparam [7:0] ERR_NONE = 8'd0;
    localparam [7:0] ERR_CRC = 8'd1;
    localparam [7:0] ERR_HEADER = 8'd2;
    localparam [5:0] CRC_WORD_INDEX = 6'd12;

    reg [1535:0] record_q;
    reg [15:0] expected_type_q;
    reg [31:0] expected_total_q;
    reg [31:0] expected_payload_q;
    reg [5:0] word_index;
    reg [31:0] crc_state;

    wire [31:0] selected_word =
        (word_index == CRC_WORD_INDEX)
        ? 32'd0 : record_q[word_index * 32 +: 32];
    wire [31:0] crc_next =
        ot_a3_pkg::a3_crc32c_word(crc_state, selected_word);
    wire [31:0] crc_final = crc_next ^ 32'hffff_ffff;
    wire [31:0] supplied_crc = record_q[415:384];
    wire [5:0] last_word = expected_total_q[7:2] - 6'd1;

    wire common_header_ok =
        (record_q[31:0] == DESC_MAGIC) &&
        (record_q[47:32] == expected_type_q) &&
        (record_q[55:48] == TYPE_MAJOR) &&
        (record_q[63:56] == TYPE_MINOR) &&
        (record_q[95:64] == expected_total_q) &&
        (record_q[351:320] == 32'd64) &&
        (record_q[383:352] == expected_payload_q) &&
        (record_q[511:416] == 96'd0) &&
        ((expected_total_q != 32'd128) ||
         (record_q[1535:1024] == 512'd0));
    wire expected_geometry_ok =
        ((expected_total_q == 32'd128) ||
         (expected_total_q == 32'd192)) &&
        (expected_payload_q + 32'd64 == expected_total_q);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            record_q <= 1536'd0;
            expected_type_q <= 16'd0;
            expected_total_q <= 32'd0;
            expected_payload_q <= 32'd0;
            word_index <= 6'd0;
            crc_state <= 32'hffff_ffff;
            busy <= 1'b0;
            done <= 1'b0;
            legal <= 1'b0;
            error_code <= ERR_NONE;
        end else begin
            done <= 1'b0;
            if (start && !busy) begin
                record_q <= record;
                expected_type_q <= expected_type;
                expected_total_q <= expected_total_bytes;
                expected_payload_q <= expected_payload_bytes;
                word_index <= 6'd0;
                crc_state <= 32'hffff_ffff;
                busy <= 1'b1;
                legal <= 1'b0;
                error_code <= ERR_NONE;
            end else if (busy) begin
                if (word_index == last_word) begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    if (crc_final != supplied_crc) begin
                        legal <= 1'b0;
                        error_code <= ERR_CRC;
                    end else if (!expected_geometry_ok || !common_header_ok) begin
                        legal <= 1'b0;
                        error_code <= ERR_HEADER;
                    end else begin
                        legal <= 1'b1;
                        error_code <= ERR_NONE;
                    end
                end else begin
                    crc_state <= crc_next;
                    word_index <= word_index + 6'd1;
                end
            end
        end
    end
endmodule
