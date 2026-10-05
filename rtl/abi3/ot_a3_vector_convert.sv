`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Bounded VECTOR.CONVERT datapath.
//
// This block implements the unscaled, one-input/one-output form of CONVERT.
// Equal formats are copied bit-for-bit.  Otherwise the source is widened by
// ot_a3_format_pkg and may be written as finite binary32 or narrowed once to
// BF16 with round-to-nearest-even.  The operand is deliberately scanned before
// the write pass: a reserved/nonfinite element anywhere in the view leaves the
// entire destination untouched, matching runtime.sim.engines.vector.
//
// The surrounding engine array supplies cfg_output_dtype from the generic
// block-A field.  Block-scaled dequantisation and two-output quantisation need
// more than this engine-array port exposes and remain fail-closed.
// ---------------------------------------------------------------------------
module ot_a3_vector_convert #(
    parameter integer MAX_ELEMENTS = 512
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [31:0] cfg_count,
    input  wire [7:0]  cfg_input_dtype,
    input  wire [7:0]  cfg_output_dtype,
    input  wire [31:0] cfg_input_base,
    input  wire [31:0] cfg_output_base,

    output reg         a_rd_en,
    output reg  [31:0] a_rd_addr,
    input  wire [31:0] a_rd_data,
    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count,
    output reg  [31:0] saturation_count
);
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE =
        ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_ACCUMULATE_RANGE =
        ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    localparam [7:0] FMT_U8 = 8'h00;
    localparam [7:0] FMT_U32 = 8'h04;
    localparam [7:0] FMT_BF16 = 8'h10;
    localparam [7:0] FMT_FP32 = 8'h12;
    localparam [7:0] FMT_FP8_E4M3FN = 8'h20;
    localparam [7:0] FMT_MXFP4_E2M1 = 8'h30;
    localparam [7:0] FMT_E8M0_SCALE = 8'h31;
    localparam [7:0] FMT_FP4_E2M1_S16_E4M3 = 8'h32;

    localparam [3:0] S_IDLE        = 4'd0;
    localparam [3:0] S_SCAN_ISSUE  = 4'd1;
    localparam [3:0] S_SCAN_WAIT   = 4'd2;
    localparam [3:0] S_SCAN_CHECK  = 4'd3;
    localparam [3:0] S_WRITE_ISSUE = 4'd4;
    localparam [3:0] S_WRITE_WAIT  = 4'd5;
    localparam [3:0] S_WRITE       = 4'd6;
    localparam [3:0] S_DONE        = 4'd7;

    reg [3:0] state;
    reg [31:0] index;

    wire identity = cfg_input_dtype == cfg_output_dtype;
    wire identity_supported = identity && (
        (cfg_input_dtype == FMT_U8) ||
        (cfg_input_dtype == FMT_U32) ||
        (cfg_input_dtype == FMT_BF16) ||
        (cfg_input_dtype == FMT_FP32) ||
        (cfg_input_dtype == FMT_FP8_E4M3FN) ||
        (cfg_input_dtype == FMT_MXFP4_E2M1) ||
        (cfg_input_dtype == FMT_FP4_E2M1_S16_E4M3) ||
        (cfg_input_dtype == FMT_E8M0_SCALE)
    );
    wire numeric_input =
        (cfg_input_dtype == FMT_BF16) ||
        (cfg_input_dtype == FMT_FP32) ||
        (cfg_input_dtype == FMT_FP8_E4M3FN) ||
        (cfg_input_dtype == FMT_MXFP4_E2M1) ||
        (cfg_input_dtype == FMT_FP4_E2M1_S16_E4M3) ||
        (cfg_input_dtype == FMT_E8M0_SCALE);
    wire conversion_supported = !identity && numeric_input &&
        ((cfg_output_dtype == FMT_BF16) ||
         (cfg_output_dtype == FMT_FP32));
    wire configuration_supported = identity_supported | conversion_supported;

    // BF16 -> FP32 preserves the architectural sign of zero.  The generic
    // decoder canonicalises zero for arithmetic users, which is correct for
    // ADD/MATMUL but not for an exact storage conversion.
    wire [33:0] decoded_generic =
        ot_a3_format_pkg::decode_element(cfg_input_dtype, a_rd_data);
    wire [33:0] decoded = (cfg_input_dtype == FMT_BF16)
        ? {((a_rd_data[14:7] == 8'hff) ? 2'd1 : 2'd0),
           a_rd_data[15:0], 16'b0}
        : decoded_generic;
    wire [18:0] narrowed =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(decoded[31:0]);

    reg [31:0] identity_word;
    always @* begin
        case (cfg_input_dtype)
            FMT_U8, FMT_FP8_E4M3FN, FMT_E8M0_SCALE:
                identity_word = {24'b0, a_rd_data[7:0]};
            FMT_MXFP4_E2M1, FMT_FP4_E2M1_S16_E4M3:
                identity_word = {28'b0, a_rd_data[3:0]};
            FMT_BF16:
                identity_word = {16'b0, a_rd_data[15:0]};
            default:
                identity_word = a_rd_data;
        endcase
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            index <= 0;
            a_rd_en <= 1'b0;
            a_rd_addr <= 0;
            out_we <= 1'b0;
            out_addr <= 0;
            out_data <= 0;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            out_count <= 0;
            saturation_count <= 0;
        end else begin
            done <= 1'b0;
            a_rd_en <= 1'b0;
            out_we <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        out_count <= 0;
                        saturation_count <= 0;
                        index <= 0;
                        if ((cfg_count == 0) ||
                            (cfg_count > MAX_ELEMENTS) ||
                            !configuration_supported) begin
                            error_code <= ERR_SHAPE;
                            state <= S_DONE;
                        end else if (identity) begin
                            // An identity conversion is a byte-preserving move,
                            // including NaN payloads and signed zero.
                            state <= S_WRITE_ISSUE;
                        end else begin
                            state <= S_SCAN_ISSUE;
                        end
                    end
                end

                S_SCAN_ISSUE: begin
                    a_rd_en <= 1'b1;
                    a_rd_addr <= cfg_input_base + index;
                    state <= S_SCAN_WAIT;
                end
                S_SCAN_WAIT: state <= S_SCAN_CHECK;
                S_SCAN_CHECK: begin
                    if (decoded[33:32] != 0) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else if ((cfg_output_dtype == FMT_BF16) &&
                                 (narrowed[18:17] != 0)) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else if (index + 1 == cfg_count) begin
                        index <= 0;
                        state <= S_WRITE_ISSUE;
                    end else begin
                        index <= index + 1;
                        state <= S_SCAN_ISSUE;
                    end
                end

                S_WRITE_ISSUE: begin
                    a_rd_en <= 1'b1;
                    a_rd_addr <= cfg_input_base + index;
                    state <= S_WRITE_WAIT;
                end
                S_WRITE_WAIT: state <= S_WRITE;
                S_WRITE: begin
                    out_we <= 1'b1;
                    out_addr <= cfg_output_base + index;
                    if (identity)
                        out_data <= identity_word;
                    else if (cfg_output_dtype == FMT_FP32)
                        out_data <= decoded[31:0];
                    else
                        out_data <= {16'b0, narrowed[15:0]};
                    out_count <= out_count + 1;
                    if (!identity && (cfg_output_dtype == FMT_BF16) &&
                        narrowed[16])
                        saturation_count <= saturation_count + 1;
                    if (index + 1 == cfg_count) begin
                        state <= S_DONE;
                    end else begin
                        index <= index + 1;
                        state <= S_WRITE_ISSUE;
                    end
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end
                default: begin
                    error_code <= ERR_SHAPE;
                    state <= S_DONE;
                end
            endcase
        end
    end
endmodule
