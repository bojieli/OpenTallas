`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// RTL 3.0 shared registry package.
//
// Every constant here is transcribed from the frozen ABI 3.0 contracts and is
// normative for the blocks in this directory:
//
//   docs/TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md  sections 1, 2, 3, 4, 5, 8
//   runtime/abi3/constants.py                     opcode/flag/trap registries
//   runtime/abi3/records.py                       program header, instruction
//   runtime/abi3/descriptors.py                   descriptor header, payloads
//
// Nothing in this package is an implementation choice: a value that differs
// from the Python registry is a wire-format break, not a tuning knob.
// ---------------------------------------------------------------------------
package ot_a3_pkg;

    // -- section 1: common encoding -------------------------------------
    localparam [31:0] A3_NO_ID = 32'hffff_ffff;
    localparam integer A3_INSTRUCTION_BYTES = 32;
    localparam integer A3_HEADER_BYTES      = 256;
    localparam integer A3_DESCRIPTOR_HEADER_BYTES = 64;
    localparam integer A3_DESCRIPTOR_PAYLOAD_OFFSET = 64;
    localparam [31:0] A3_CRC32C_POLY = 32'h82f6_3b78;  // reflected Castagnoli

    // -- section 2: program header --------------------------------------
    // ASCII "OTTA3PG\0" read as one little-endian 64-bit word.
    localparam [63:0] A3_PROGRAM_MAGIC = 64'h0047_5033_4154_544f;
    localparam [7:0]  A3_ABI_MAJOR = 8'd3;
    localparam [7:0]  A3_ABI_MINOR = 8'd0;
    localparam integer A3_HEADER_WORDS = A3_HEADER_BYTES / 4;   // 64
    localparam integer A3_HEADER_CRC_WORD = A3_HEADER_WORDS - 1;

    // -- section 5: descriptor header -----------------------------------
    localparam [31:0] A3_DESCRIPTOR_MAGIC = 32'h4433_4154;      // ASCII "TA3D"
    localparam [7:0]  A3_TYPE_MAJOR = 8'd1;
    localparam [7:0]  A3_TYPE_MINOR = 8'd0;

    localparam [15:0] A3_DESC_MEMORY_OBJECT      = 16'h0001;
    localparam [15:0] A3_DESC_TENSOR_VIEW        = 16'h0002;
    localparam [15:0] A3_DESC_NUMERIC            = 16'h0003;
    localparam [15:0] A3_DESC_SCHEDULE           = 16'h0004;
    localparam [15:0] A3_DESC_TOPOLOGY           = 16'h0005;
    localparam [15:0] A3_DESC_COMMUNICATION      = 16'h0006;
    localparam [15:0] A3_DESC_STATE              = 16'h0007;
    localparam [15:0] A3_DESC_EVENT_WAIT_SET     = 16'h0008;
    localparam [15:0] A3_DESC_LOOP_CONTROL       = 16'h0009;
    localparam [15:0] A3_DESC_OPERATOR           = 16'h000a;
    localparam [15:0] A3_DESC_GENERATION_POLICY  = 16'h000b;
    localparam [15:0] A3_DESC_COUNTER_CLASS      = 16'h000c;
    localparam [15:0] A3_DESC_ENTRYPOINT_TABLE   = 16'h000d;
    localparam [15:0] A3_DESC_SIGNATURE_METADATA = 16'h000e;
    // Amendment TA-A3-ARCH-0-A3 (runtime/abi3/descriptors.py).
    localparam [15:0] A3_DESC_PREDICATE          = 16'h000f;
    localparam [15:0] A3_DESC_NONE               = 16'hffff;

    // -- section 3: instruction flags -----------------------------------
    localparam integer A3_FLAG_PREDICATED        = 0;
    localparam integer A3_FLAG_PREDICATE_INVERT  = 1;
    localparam integer A3_FLAG_WAIT_ACQUIRE      = 2;
    localparam integer A3_FLAG_SIGNAL_RELEASE    = 3;
    localparam integer A3_FLAG_TRANSACTION_SCOPED= 4;
    localparam integer A3_FLAG_GLOBAL_SCOPE      = 5;
    localparam integer A3_FLAG_TRACE_BOUNDARY    = 6;
    localparam integer A3_FLAG_OPTIONAL_FEATURE  = 7;
    localparam [15:0] A3_FLAG_MASK = 16'h00ff;   // bits 8..15 reserved zero

    // -- section 4: opcode registry -------------------------------------
    localparam [7:0] A3_MAJOR_CONTROL     = 8'h00;
    localparam [7:0] A3_MAJOR_DMA         = 8'h10;
    localparam [7:0] A3_MAJOR_TENSOR      = 8'h20;
    localparam [7:0] A3_MAJOR_VECTOR      = 8'h30;
    localparam [7:0] A3_MAJOR_ATTENTION   = 8'h40;
    localparam [7:0] A3_MAJOR_ROUTE       = 8'h50;
    localparam [7:0] A3_MAJOR_REDUCTION   = 8'h60;
    localparam [7:0] A3_MAJOR_SELECTION   = 8'h70;
    localparam [7:0] A3_MAJOR_STATE       = 8'h80;
    localparam [7:0] A3_MAJOR_LINK        = 8'h90;
    localparam [7:0] A3_MAJOR_OBSERVATION = 8'ha0;
    localparam [7:0] A3_MAJOR_RECOVERY    = 8'hb0;

    localparam [7:0] A3_CONTROL_NOP        = 8'h00;
    localparam [7:0] A3_CONTROL_BRANCH     = 8'h01;
    localparam [7:0] A3_CONTROL_LOOP_SETUP = 8'h02;
    localparam [7:0] A3_CONTROL_LOOP_NEXT  = 8'h03;
    localparam [7:0] A3_CONTROL_WAIT       = 8'h04;
    localparam [7:0] A3_CONTROL_FENCE      = 8'h05;
    localparam [7:0] A3_CONTROL_ASSERT     = 8'h06;
    localparam [7:0] A3_CONTROL_COMPLETE   = 8'h07;
    localparam [7:0] A3_CONTROL_TRAP       = 8'h08;

    localparam [7:0] A3_STATE_READ               = 8'h00;
    localparam [7:0] A3_STATE_PREPARE            = 8'h01;
    localparam [7:0] A3_STATE_COMMIT             = 8'h02;
    localparam [7:0] A3_STATE_DISCARD            = 8'h03;
    localparam [7:0] A3_STATE_GENERATION_ADVANCE = 8'h04;

    // Amendment A21 (wire format section 12.11): where a STATE.COMMIT takes
    // its row count from, declared at STATE payload byte 1.  REQUEST_SPAN is
    // SPAN_TOKENS rows at the cursor -- the rule and the value every pre-A21
    // deployment carried.  UNSTAGED is a resource no descriptor of the
    // deployment names as a destination: nothing can stage a row into it, so
    // its commit publishes none.
    localparam [7:0] A3_COMMIT_POLICY_REQUEST_SPAN = 8'h00;
    localparam [7:0] A3_COMMIT_POLICY_UNSTAGED     = 8'h01;

    localparam [7:0] A3_RECOVERY_POISON = 8'h00;
    localparam [7:0] A3_RECOVERY_ABORT  = 8'h01;
    localparam [7:0] A3_RECOVERY_DRAIN  = 8'h02;

    // -- section 8: trap classes ----------------------------------------
    localparam [15:0] A3_TRAP_NONE            = 16'd0;
    localparam [15:0] A3_TRAP_ADMISSION       = 16'd1;
    localparam [15:0] A3_TRAP_INTEGRITY       = 16'd2;
    localparam [15:0] A3_TRAP_DESCRIPTOR      = 16'd3;
    localparam [15:0] A3_TRAP_CAPABILITY      = 16'd4;
    localparam [15:0] A3_TRAP_ILLEGAL         = 16'd5;
    localparam [15:0] A3_TRAP_NUMERIC         = 16'd6;
    localparam [15:0] A3_TRAP_MEMORY          = 16'd7;
    localparam [15:0] A3_TRAP_ENGINE          = 16'd8;
    localparam [15:0] A3_TRAP_STATE           = 16'd9;
    localparam [15:0] A3_TRAP_WATCHDOG        = 16'd10;
    localparam [15:0] A3_TRAP_LINK            = 16'd11;
    localparam [15:0] A3_TRAP_POWER           = 16'd12;
    localparam [15:0] A3_TRAP_INTERNAL        = 16'd13;

    // -- amendment A5: runtime symbol registry --------------------------
    localparam integer A3_SYMBOL_COUNT           = 16;
    localparam [3:0] A3_SYMBOL_SPAN_TOKENS       = 4'd0;
    localparam [3:0] A3_SYMBOL_POSITION_START    = 4'd1;
    localparam [3:0] A3_SYMBOL_POSITION_END      = 4'd2;
    localparam [3:0] A3_SYMBOL_CONTEXT_LENGTH    = 4'd3;
    localparam [3:0] A3_SYMBOL_PHASE             = 4'd4;
    localparam [3:0] A3_SYMBOL_GENERATION_INDEX  = 4'd5;

    // -- predicate registry (runtime/abi3/descriptors.py) ---------------
    localparam [7:0] A3_PRED_ALWAYS         = 8'd0;
    localparam [7:0] A3_PRED_PHASE_IS       = 8'd1;
    localparam [7:0] A3_PRED_COMPARE_SYMBOL = 8'd2;
    localparam [7:0] A3_PRED_ENGINE_STATUS  = 8'd3;
    localparam [7:0] A3_PRED_ROUTE_VALID    = 8'd4;
    localparam [7:0] A3_PRED_EOS_MEMBER     = 8'd5;
    localparam [7:0] A3_PRED_LOOP_FIRST     = 8'd6;
    localparam [7:0] A3_PRED_LOOP_LAST      = 8'd7;
    localparam [7:0] A3_PRED_BOOLEAN_OBJECT = 8'd8;
    localparam [7:0] A3_PRED_COMPARE_LOOP   = 8'd9;

    localparam [7:0] A3_CMP_EQ = 8'd0;
    localparam [7:0] A3_CMP_NE = 8'd1;
    localparam [7:0] A3_CMP_LT = 8'd2;
    localparam [7:0] A3_CMP_LE = 8'd3;
    localparam [7:0] A3_CMP_GT = 8'd4;
    localparam [7:0] A3_CMP_GE = 8'd5;

    localparam [7:0] A3_SELECTOR_LOOP_INDUCTION = 8'd0;
    localparam [7:0] A3_SELECTOR_RUNTIME_SYMBOL = 8'd1;
    localparam [7:0] A3_SELECTOR_CONSTANT       = 8'd2;

    // -- ordering registry (section 8) ----------------------------------
    localparam [7:0] A3_ORDER_NONE            = 8'd0;
    localparam [7:0] A3_ORDER_ACQUIRE         = 8'd1;
    localparam [7:0] A3_ORDER_RELEASE         = 8'd2;
    localparam [7:0] A3_ORDER_ACQUIRE_RELEASE = 8'd3;
    localparam [7:0] A3_ORDER_SEQUENTIAL      = 8'd4;

    // -- implementation bounds (capability fields, not ABI) -------------
    localparam integer A3_LOOP_DEPTH   = 4;    // capability max_loop_depth
    localparam integer A3_STATE_SLOTS  = 8;
    localparam integer A3_EVENT_COUNT  = 256;  // capability max_events
    localparam integer A3_WAIT_PRODUCERS = 12; // MAX_WAIT_PRODUCERS

    // -- decoder error registry (block-local, mapped to trap classes) ---
    localparam [3:0] A3_ERR_NONE           = 4'd0;
    localparam [3:0] A3_ERR_CRC            = 4'd1;
    localparam [3:0] A3_ERR_MAJOR          = 4'd2;
    localparam [3:0] A3_ERR_SUB            = 4'd3;
    localparam [3:0] A3_ERR_FLAG_RESERVED  = 4'd4;
    localparam [3:0] A3_ERR_PREDICATE_FLAG = 4'd5;
    localparam [3:0] A3_ERR_PREDICATE_ID   = 4'd6;
    localparam [3:0] A3_ERR_BRANCH_TARGET  = 4'd7;
    localparam [3:0] A3_ERR_MAGIC          = 4'd8;
    localparam [3:0] A3_ERR_VERSION        = 4'd9;
    localparam [3:0] A3_ERR_SIZE           = 4'd10;
    localparam [3:0] A3_ERR_COUNT          = 4'd11;
    localparam [3:0] A3_ERR_RESERVED       = 4'd12;

    // Highest legal subopcode for each frozen major opcode.  Every family's
    // subopcodes are assigned contiguously from zero (wire format section 4),
    // so a bound is a complete legality statement, not an approximation.
    function automatic [8:0] a3_major_sub_bound;
        input [7:0] major;
        begin
            case (major)
                A3_MAJOR_CONTROL:     a3_major_sub_bound = {1'b1, 8'h08};
                A3_MAJOR_DMA:         a3_major_sub_bound = {1'b1, 8'h03};
                A3_MAJOR_TENSOR:      a3_major_sub_bound = {1'b1, 8'h03};
                A3_MAJOR_VECTOR:      a3_major_sub_bound = {1'b1, 8'h0c};
                A3_MAJOR_ATTENTION:   a3_major_sub_bound = {1'b1, 8'h02};
                A3_MAJOR_ROUTE:       a3_major_sub_bound = {1'b1, 8'h06};
                A3_MAJOR_REDUCTION:   a3_major_sub_bound = {1'b1, 8'h04};
                A3_MAJOR_SELECTION:   a3_major_sub_bound = {1'b1, 8'h02};
                A3_MAJOR_STATE:       a3_major_sub_bound = {1'b1, 8'h04};
                A3_MAJOR_LINK:        a3_major_sub_bound = {1'b1, 8'h07};
                A3_MAJOR_OBSERVATION: a3_major_sub_bound = {1'b1, 8'h01};
                A3_MAJOR_RECOVERY:    a3_major_sub_bound = {1'b1, 8'h02};
                default:              a3_major_sub_bound = {1'b0, 8'h00};
            endcase
        end
    endfunction

    function automatic a3_major_legal;
        input [7:0] major;
        reg [8:0] bound;
        begin
            bound = a3_major_sub_bound(major);
            a3_major_legal = bound[8];
        end
    endfunction

    function automatic a3_sub_legal;
        input [7:0] major;
        input [7:0] sub;
        reg [8:0] bound;
        begin
            bound = a3_major_sub_bound(major);
            a3_sub_legal = bound[8] && (sub <= bound[7:0]);
        end
    endfunction

    // Families that issue asynchronous engine work (ENGINE_FAMILIES plus the
    // observation and recovery families, which the golden model also routes
    // through its issue path).
    function automatic a3_is_engine_family;
        input [7:0] major;
        begin
            a3_is_engine_family = a3_major_legal(major) &&
                                  (major != A3_MAJOR_CONTROL);
        end
    endfunction

    // Descriptor type an instruction's descriptor ID must carry, per family.
    // Mirrors verifier._FAMILY_DESCRIPTOR; A3_DESC_NONE means "unconstrained".
    function automatic [15:0] a3_family_descriptor_type;
        input [7:0] major;
        begin
            case (major)
                A3_MAJOR_DMA,
                A3_MAJOR_TENSOR,
                A3_MAJOR_VECTOR,
                A3_MAJOR_ATTENTION,
                A3_MAJOR_ROUTE,
                A3_MAJOR_REDUCTION,
                A3_MAJOR_SELECTION:   a3_family_descriptor_type = A3_DESC_OPERATOR;
                A3_MAJOR_LINK:        a3_family_descriptor_type = A3_DESC_COMMUNICATION;
                A3_MAJOR_STATE:       a3_family_descriptor_type = A3_DESC_STATE;
                A3_MAJOR_OBSERVATION: a3_family_descriptor_type = A3_DESC_COUNTER_CLASS;
                default:              a3_family_descriptor_type = A3_DESC_NONE;
            endcase
        end
    endfunction

    // Reflected CRC32C over one little-endian 32-bit word.  The running
    // remainder is kept unfinalized; the final XOR is applied once, by the
    // consumer, so a CRC never depends on beat boundaries.
    function automatic [31:0] a3_crc32c_word;
        input [31:0] state;
        input [31:0] word;
        integer bit_index;
        reg [31:0] crc;
        reg feedback;
        begin
            crc = state;
            for (bit_index = 0; bit_index < 32; bit_index = bit_index + 1) begin
                feedback = crc[0] ^ word[bit_index];
                crc = crc >> 1;
                if (feedback)
                    crc = crc ^ A3_CRC32C_POLY;
            end
            a3_crc32c_word = crc;
        end
    endfunction

endpackage
