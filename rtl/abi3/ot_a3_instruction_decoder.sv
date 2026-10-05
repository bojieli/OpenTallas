`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 instruction admission.
//
// This is the ABI 3.0 analogue of ot_ta_command_decoder: a registered admission
// boundary that admits exactly one 32-byte device instruction (wire format
// section 3) at a time and fails closed on every structural error before the
// microsequencer is allowed to act on the record.
//
// CRC discipline.  The record CRC is reflected CRC32C/Castagnoli with initial
// state 0xffffffff and final XOR 0xffffffff, evaluated four bytes per cycle so
// that 224 recurrence steps never sit between an input pad and an output
// register.  Section 1 of the wire format says "a CRC field is treated as zero
// while its record CRC is calculated", and runtime/abi3/crc.record_crc
// implements exactly that: the checksum covers all 32 bytes with bytes 28..31
// replaced by zeros.  The section 3 table's "bytes 0 through 27" describes a
// different, incompatible checksum; this block implements the normative
// encoder, so word 7 is driven to zero instead of being skipped.
//
// SKIPPING THE RECURRENCE (``CRC_CACHE``).  ``CRC_CACHE = 0`` is the block as
// it has always been: the eight-beat recurrence runs on every record.  With
// ``CRC_CACHE = 1`` the caller may assert ``in_crc_validated``, which asserts
// that THIS EXACT RECORD's CRC has already been checked and passed by this
// block, and the recurrence is skipped -- the record is admitted in the cycle
// after it is accepted instead of eight cycles later.  Nothing else is
// skipped: the opcode, subopcode, reserved-flag, predicate-flag,
// predicate-ID and branch-target checks are combinational functions of the
// record and are re-evaluated on every fetch either way.  Only the 32-bit
// checksum is elided, and only for a record the caller has already validated.
//
// The skip is a control decision, not a datapath one.  ``in_crc_validated``
// steers the initial value of ``crc_word_index`` and one enable on the final
// compare; it adds no term to the recurrence and no term to the structural
// checker, so the block's combinational depth with ``CRC_CACHE = 1`` and a
// hit is the depth it already had, minus the recurrence that is not run.
//
// Legality is evaluated in a fixed priority order so that a record with more
// than one defect always reports the same trap class:
//   integrity (CRC)  >  opcode  >  subopcode  >  reserved flag bits  >
//   PREDICATE_INVERT without PREDICATED  >  predicate-ID agreement  >
//   branch target inside the authenticated body.
// ---------------------------------------------------------------------------
module ot_a3_instruction_decoder
    // The package is referenced by scope rather than wildcard-imported: a
    // wildcard import is not accepted by every open synthesis front end this
    // program pins, and a block that only elaborates in a simulator is not an
    // implementable block.  [OI-43] docs/UNIFIED_EXECUTION_CHECKLIST.md
#(
    // 0 rebuilds the block exactly as it was before the skip existed:
    // in_crc_validated is not read and every record takes eight beats.
    parameter integer CRC_CACHE = 0
)
(
    input  wire         clk,
    input  wire         rst_n,

    input  wire         in_valid,
    output wire         in_ready,
    input  wire [255:0] in_record,
    input  wire [31:0]  in_index,             // instruction index of the record
    input  wire [31:0]  in_instruction_count, // authenticated body length
    // Asserts that this exact record's CRC has already been checked and
    // passed by this block.  Ignored unless CRC_CACHE != 0.
    input  wire         in_crc_validated,

    output reg          out_valid,
    input  wire         out_ready,
    output reg          out_legal,
    output reg  [3:0]   out_error,
    output reg  [15:0]  out_trap_class,
    output reg  [31:0]  out_index,
    output reg  [7:0]   out_major,
    output reg  [7:0]   out_sub,
    output reg  [15:0]  out_flags,
    output reg  [31:0]  out_predicate_id,
    output reg  [31:0]  out_descriptor_id,
    output reg  [31:0]  out_wait_set_id,
    output reg  [31:0]  out_signal_event_id,
    output reg  [31:0]  out_control_id,
    output reg  [31:0]  out_source_operation_id
);
    localparam [2:0] CRC_LAST_WORD = 3'd7;

    reg          busy;
    reg          skip_q;          // this record was admitted on a validated hit
    reg  [2:0]   crc_word_index;
    reg  [31:0]  crc_state;
    reg  [255:0] record;
    reg  [31:0]  index_buffer;
    reg  [31:0]  count_buffer;

    wire [7:0]  major        = record[7:0];
    wire [7:0]  sub          = record[15:8];
    wire [15:0] flags        = record[31:16];
    wire [31:0] predicate_id = record[63:32];
    wire [31:0] descriptor_id= record[95:64];
    wire [31:0] wait_set_id  = record[127:96];
    wire [31:0] signal_id    = record[159:128];
    wire [31:0] control_id   = record[191:160];
    wire [31:0] source_id    = record[223:192];
    wire [31:0] supplied_crc = record[255:224];

    // Word 7 carries the CRC field itself and is checksummed as zero.
    wire [31:0] crc_word = (crc_word_index == CRC_LAST_WORD)
                         ? 32'h0000_0000
                         : record[{crc_word_index, 5'b00000} +: 32];
    wire [31:0] crc_next = ot_a3_pkg::a3_crc32c_word(crc_state, crc_word);
    wire [31:0] crc_final = crc_next ^ 32'hffff_ffff;

    // A hit is honoured only when the block is built with the skip.
    wire skip_now = (CRC_CACHE != 0) && in_crc_validated;

    wire predicated = flags[ot_a3_pkg::A3_FLAG_PREDICATED];
    wire invert     = flags[ot_a3_pkg::A3_FLAG_PREDICATE_INVERT];
    wire is_branch  = (major == ot_a3_pkg::A3_MAJOR_CONTROL) && (sub == ot_a3_pkg::A3_CONTROL_BRANCH);

    reg [3:0] error_comb;
    always @* begin
        if (!ot_a3_pkg::a3_major_legal(major))
            error_comb = ot_a3_pkg::A3_ERR_MAJOR;
        else if (!ot_a3_pkg::a3_sub_legal(major, sub))
            error_comb = ot_a3_pkg::A3_ERR_SUB;
        else if ((flags & ~ot_a3_pkg::A3_FLAG_MASK) != 16'h0000)
            error_comb = ot_a3_pkg::A3_ERR_FLAG_RESERVED;
        else if (invert && !predicated)
            error_comb = ot_a3_pkg::A3_ERR_PREDICATE_FLAG;
        else if (predicated && (predicate_id == ot_a3_pkg::A3_NO_ID))
            error_comb = ot_a3_pkg::A3_ERR_PREDICATE_ID;
        else if (!predicated && (predicate_id != ot_a3_pkg::A3_NO_ID))
            error_comb = ot_a3_pkg::A3_ERR_PREDICATE_ID;
        else if (is_branch && (control_id >= count_buffer))
            error_comb = ot_a3_pkg::A3_ERR_BRANCH_TARGET;
        else
            error_comb = ot_a3_pkg::A3_ERR_NONE;
    end

    // Every structural defect other than a failed integrity check is an
    // illegal instruction (trap class 5); a failed CRC is an integrity fault
    // (trap class 2).  The frozen ABI does not itself assign trap classes to
    // record-level defects: section 1 says nonzero reserved values "fail
    // before work is issued" (readable as class 1, admission) while section 3
    // calls a bad flag combination "illegal" (class 5).  Class 5 is used here
    // because the defect is in an instruction the sequencer is executing, not
    // in the deployment's admission; the golden model raises no trap class at
    // all for these, since it rejects the whole body at load time.
    function automatic [15:0] trap_of_error;
        input [3:0] error;
        begin
            if (error == ot_a3_pkg::A3_ERR_NONE)
                trap_of_error = ot_a3_pkg::A3_TRAP_NONE;
            else if (error == ot_a3_pkg::A3_ERR_CRC)
                trap_of_error = ot_a3_pkg::A3_TRAP_INTEGRITY;
            else
                trap_of_error = ot_a3_pkg::A3_TRAP_ILLEGAL;
        end
    endfunction

    assign in_ready = !busy && (!out_valid || out_ready);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0;
            skip_q <= 1'b0;
            crc_word_index <= 3'd0;
            crc_state <= 32'hffff_ffff;
            record <= 256'b0;
            index_buffer <= 32'b0;
            count_buffer <= 32'b0;
            out_valid <= 1'b0;
            out_legal <= 1'b0;
            out_error <= ot_a3_pkg::A3_ERR_NONE;
            out_trap_class <= ot_a3_pkg::A3_TRAP_NONE;
            out_index <= 32'b0;
            out_major <= 8'b0;
            out_sub <= 8'b0;
            out_flags <= 16'b0;
            out_predicate_id <= ot_a3_pkg::A3_NO_ID;
            out_descriptor_id <= ot_a3_pkg::A3_NO_ID;
            out_wait_set_id <= ot_a3_pkg::A3_NO_ID;
            out_signal_event_id <= ot_a3_pkg::A3_NO_ID;
            out_control_id <= ot_a3_pkg::A3_NO_ID;
            out_source_operation_id <= ot_a3_pkg::A3_NO_ID;
        end else begin
            if (out_valid && out_ready)
                out_valid <= 1'b0;

            if (in_valid && in_ready) begin
                busy <= 1'b1;
                skip_q <= skip_now;
                // On a hit the beat counter is started AT the terminal beat,
                // so the next cycle takes the same completion branch the
                // eighth beat would have taken.  The recurrence registers are
                // still initialised, and crc_state is never consumed on this
                // path, so the two builds differ in control only.
                crc_word_index <= skip_now ? CRC_LAST_WORD : 3'd0;
                crc_state <= 32'hffff_ffff;
                record <= in_record;
                index_buffer <= in_index;
                count_buffer <= in_instruction_count;
            end else if (busy) begin
                if (crc_word_index == CRC_LAST_WORD) begin
                    busy <= 1'b0;
                    out_valid <= 1'b1;
                    out_index <= index_buffer;
                    out_major <= major;
                    out_sub <= sub;
                    out_flags <= flags;
                    out_predicate_id <= predicate_id;
                    out_descriptor_id <= descriptor_id;
                    out_wait_set_id <= wait_set_id;
                    out_signal_event_id <= signal_id;
                    out_control_id <= control_id;
                    out_source_operation_id <= source_id;
                    // The integrity verdict is the recurrence's on a miss and
                    // the caller's standing "this record already passed" on a
                    // hit.  Priority is unchanged either way: a record whose
                    // CRC fails reports class 2 and never reaches the
                    // structural verdict below.
                    if (!skip_q && (crc_final != supplied_crc)) begin
                        out_legal <= 1'b0;
                        out_error <= ot_a3_pkg::A3_ERR_CRC;
                        out_trap_class <= ot_a3_pkg::A3_TRAP_INTEGRITY;
                    end else begin
                        out_legal <= (error_comb == ot_a3_pkg::A3_ERR_NONE);
                        out_error <= error_comb;
                        out_trap_class <= trap_of_error(error_comb);
                    end
                end else begin
                    crc_state <= crc_next;
                    crc_word_index <= crc_word_index + 3'd1;
                end
            end
        end
    end
endmodule
