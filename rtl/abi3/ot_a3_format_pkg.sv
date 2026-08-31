`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 storage-format decode to binary32.
//
// One function per storage format this device's engine datapaths read.  Each
// returns ``{error[1:0], binary32_code}``, using the same error encoding as
// ot_fp32_rne_pkg: 0 none, 1 nonfinite/reserved encoding, 2 overflow.
//
// These are *decoders*, not approximations.  Every value of E4M3FN, E2M1 and
// E8M0 is exactly representable in binary32 -- E4M3FN spans 2**-9 .. 448, E2M1
// spans 0 .. 6 and E8M0 spans 2**-127 .. 2**127 -- so a decode is an exact
// re-encoding and never rounds.  The authority is runtime/reference/formats.py,
// whose exact Fraction decoders enumerate the lookup tables in
// runtime/sim/formats.py; tools/build_abi3_engine_vectors.py emits an
// exhaustive case over all 256 E4M3FN codes, all 16 E2M1 nibbles and all 256
// E8M0 codes so that a drift in either direction fails the campaign rather
// than being argued about here.
//
// Zero is canonical positive in every format, matching the tables: the exact
// decoder yields the rational 0 for both the +0 and -0 encodings and
// float(0) is +0.0, so E4M3FN 0x80 and E2M1 0x8 decode to +0.0 and not to
// -0.0.  A reserved encoding -- E4M3FN 0x7f/0xff, E8M0 0xff -- decodes to NaN
// in the tables, which an engine must treat as a poisoned block; here it is
// reported as error 1 rather than as a value.
// ---------------------------------------------------------------------------
package ot_a3_format_pkg;
    localparam [1:0] FMT_ERR_NONE      = 2'd0;
    localparam [1:0] FMT_ERR_NONFINITE = 2'd1;

    // Storage-format identifiers, transcribed from runtime/abi3/constants.DType.
    localparam [7:0] FMT_U8         = 8'h00;
    localparam [7:0] FMT_U32        = 8'h04;
    localparam [7:0] FMT_BF16       = 8'h10;
    localparam [7:0] FMT_FP32       = 8'h12;
    localparam [7:0] FMT_FP8_E4M3FN = 8'h20;
    localparam [7:0] FMT_MXFP4_E2M1 = 8'h30;
    localparam [7:0] FMT_E8M0_SCALE = 8'h31;

    // -- BF16 -> binary32.  Exact: the architectural pattern is the high half.
    function automatic [33:0] decode_bf16;
        input [15:0] code;
        reg [1:0] error;
        reg [31:0] value;
        begin
            error = FMT_ERR_NONE;
            value = {code, 16'b0};
            if (code[14:7] == 8'hff)
                error = FMT_ERR_NONFINITE;
            if (value[30:0] == 31'b0)
                value = 32'b0;
            decode_bf16 = {error, value};
        end
    endfunction

    // -- binary32 pass-through, with the same nonfinite gate.
    function automatic [33:0] decode_fp32;
        input [31:0] code;
        reg [1:0] error;
        begin
            error = (code[30:23] == 8'hff) ? FMT_ERR_NONFINITE : FMT_ERR_NONE;
            decode_fp32 = {error, code};
        end
    endfunction

    // -- OCP finite-only FP8 E4M3FN -> binary32.
    //    sign(1) exponent(4, bias 7) significand(3).  exponent 15 with
    //    significand 7 is the reserved encoding; exponent 0 is subnormal with
    //    value significand * 2**-9.
    function automatic [33:0] decode_e4m3fn;
        input [7:0] code;
        reg [1:0] error;
        reg [31:0] value;
        reg        sign;
        reg [3:0]  exponent;
        reg [2:0]  significand;
        begin
            error = FMT_ERR_NONE;
            value = 32'b0;
            sign = code[7];
            exponent = code[6:3];
            significand = code[2:0];
            if ((exponent == 4'hf) && (significand == 3'h7)) begin
                error = FMT_ERR_NONFINITE;
            end else if (exponent == 4'h0) begin
                if (significand == 3'h0) begin
                    value = 32'b0;            // canonical positive zero
                end else if (significand[2]) begin
                    // 4..7 -> (significand/4) * 2**-7
                    value = {sign, 8'd120, {significand[1:0], 21'b0}};
                end else if (significand[1]) begin
                    // 2..3 -> (significand/2) * 2**-8
                    value = {sign, 8'd119, {significand[0], 22'b0}};
                end else begin
                    // 1 -> 2**-9
                    value = {sign, 8'd118, 23'b0};
                end
            end else begin
                value = {sign, ({4'b0, exponent} + 8'd120),
                         {significand, 20'b0}};
            end
            decode_e4m3fn = {error, value};
        end
    endfunction

    // -- MXFP4 E2M1 nibble -> binary32.
    //    sign(1) exponent(2, bias 1) significand(1).  No reserved encoding:
    //    the sixteen nibbles decode to 0, +/-0.5, 1, 1.5, 2, 3, 4 and 6.
    function automatic [33:0] decode_e2m1;
        input [3:0] nibble;
        reg [31:0] value;
        reg        sign;
        reg [1:0]  exponent;
        reg        significand;
        begin
            sign = nibble[3];
            exponent = nibble[2:1];
            significand = nibble[0];
            if (exponent == 2'b0) begin
                if (significand == 1'b0)
                    value = 32'b0;            // canonical positive zero
                else
                    value = {sign, 8'd126, 23'b0};   // 0.5
            end else begin
                value = {sign, ({6'b0, exponent} + 8'd126),
                         {significand, 22'b0}};
            end
            decode_e2m1 = {FMT_ERR_NONE, value};
        end
    endfunction

    // -- unsigned E8M0 block scale -> binary32 power of two.
    //    code c is 2**(c-127); c = 0 is the binary32 subnormal 2**-127 and
    //    c = 255 is reserved.
    function automatic [33:0] decode_e8m0;
        input [7:0] code;
        reg [1:0] error;
        reg [31:0] value;
        begin
            error = FMT_ERR_NONE;
            if (code == 8'hff) begin
                error = FMT_ERR_NONFINITE;
                value = 32'b0;
            end else if (code == 8'h00) begin
                value = 32'h00400000;         // 2**-127, subnormal
            end else begin
                value = {1'b0, code, 23'b0};
            end
            decode_e8m0 = {error, value};
        end
    endfunction

    // -- one operand element of any supported storage format.
    //    ``word`` carries the element's storage code right-aligned in a 32-bit
    //    word, which is how tools/build_abi3_engine_vectors.py emits every
    //    operand image regardless of element width.
    function automatic [33:0] decode_element;
        input [7:0]  format_id;
        input [31:0] word;
        begin
            case (format_id)
                FMT_BF16:       decode_element = decode_bf16(word[15:0]);
                FMT_FP32:       decode_element = decode_fp32(word);
                FMT_FP8_E4M3FN: decode_element = decode_e4m3fn(word[7:0]);
                FMT_MXFP4_E2M1: decode_element = decode_e2m1(word[3:0]);
                FMT_E8M0_SCALE: decode_element = decode_e8m0(word[7:0]);
                default:        decode_element = {FMT_ERR_NONFINITE, 32'b0};
            endcase
        end
    endfunction
endpackage
