`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Bounded VECTOR.SCALE datapath.
//
// The covered forms are amendment-A8 aux0 0 (one binary32 constant from the
// numeric profile) and aux0 1 (a same-shape BF16 factor).  Both are BF16 to
// BF16: operands widen exactly, one binary32 RNE multiply is performed, and
// the result crosses one BF16 RNE boundary.  Aux0 2 is the correctly-rounded
// logistic sigmoid and deliberately remains fail-closed.
//
// Results are buffered until every element has been decoded and computed.
// Consequently a nonfinite value or arithmetic refusal at the end of the
// operand leaves the whole architectural destination untouched.
// ---------------------------------------------------------------------------
module ot_a3_vector_scale #(
    parameter integer MAX_ELEMENTS = 512
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [31:0] cfg_count,
    input  wire [7:0]  cfg_dtype_a,
    input  wire [7:0]  cfg_dtype_b,
    input  wire [15:0] cfg_aux0,
    input  wire [31:0] cfg_scale_bits,
    input  wire [31:0] cfg_a_base,
    input  wire [31:0] cfg_b_base,
    input  wire [31:0] cfg_out_base,

    output reg         a_rd_en,
    output reg  [31:0] a_rd_addr,
    input  wire [31:0] a_rd_data,
    output reg         b_rd_en,
    output reg  [31:0] b_rd_addr,
    input  wire [31:0] b_rd_data,
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
    localparam [7:0] ERR_PRODUCT_RANGE = ot_a3_engine_pkg::ERR_PRODUCT_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    localparam [7:0] FMT_BF16 = 8'h10;
    localparam [15:0] SCALE_CONSTANT = 16'd0;
    localparam [15:0] SCALE_ELEMENTWISE = 16'd1;

    localparam [2:0] S_IDLE    = 3'd0;
    localparam [2:0] S_ISSUE   = 3'd1;
    localparam [2:0] S_WAIT    = 3'd2;
    localparam [2:0] S_COMPUTE = 3'd3;
    localparam [2:0] S_COMMIT  = 3'd4;
    localparam [2:0] S_DONE    = 3'd5;

    reg [2:0] state;
    reg [31:0] index;
    reg [31:0] pending_saturation_count;
    reg [31:0] result_buffer [0:MAX_ELEMENTS-1];

    wire [33:0] decoded_a = ot_a3_format_pkg::decode_bf16(a_rd_data[15:0]);
    wire [33:0] decoded_b = ot_a3_format_pkg::decode_bf16(b_rd_data[15:0]);
    wire [31:0] right_value = (cfg_aux0 == SCALE_CONSTANT)
                            ? cfg_scale_bits : decoded_b[31:0];
    wire [33:0] product =
        ot_fp32_rne_pkg::fp32_mul_rne(decoded_a[31:0], right_value);
    wire [18:0] narrowed =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(product[31:0]);

    wire scale_is_finite = cfg_scale_bits[30:23] != 8'hff;
    wire supported =
        (cfg_count != 0) && (cfg_count <= MAX_ELEMENTS) &&
        (cfg_dtype_a == FMT_BF16) &&
        ((cfg_aux0 == SCALE_CONSTANT) ||
         ((cfg_aux0 == SCALE_ELEMENTWISE) && (cfg_dtype_b == FMT_BF16)));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            index <= 0;
            pending_saturation_count <= 0;
            a_rd_en <= 1'b0;
            a_rd_addr <= 0;
            b_rd_en <= 1'b0;
            b_rd_addr <= 0;
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
            b_rd_en <= 1'b0;
            out_we <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        out_count <= 0;
                        saturation_count <= 0;
                        pending_saturation_count <= 0;
                        index <= 0;
                        if (!supported) begin
                            error_code <= ERR_SHAPE;
                            state <= S_DONE;
                        end else if ((cfg_aux0 == SCALE_CONSTANT) &&
                                     !scale_is_finite) begin
                            error_code <= ERR_OPERAND_NONFINITE;
                            state <= S_DONE;
                        end else begin
                            state <= S_ISSUE;
                        end
                    end
                end

                S_ISSUE: begin
                    a_rd_en <= 1'b1;
                    a_rd_addr <= cfg_a_base + index;
                    if (cfg_aux0 == SCALE_ELEMENTWISE) begin
                        b_rd_en <= 1'b1;
                        b_rd_addr <= cfg_b_base + index;
                    end
                    state <= S_WAIT;
                end

                S_WAIT: state <= S_COMPUTE;

                S_COMPUTE: begin
                    if ((decoded_a[33:32] != 0) ||
                        ((cfg_aux0 == SCALE_ELEMENTWISE) &&
                         (decoded_b[33:32] != 0))) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else if ((product[33:32] != 0) ||
                                 (narrowed[18:17] != 0)) begin
                        error_code <= ERR_PRODUCT_RANGE;
                        state <= S_DONE;
                    end else begin
                        result_buffer[index] <= {16'b0, narrowed[15:0]};
                        if (narrowed[16])
                            pending_saturation_count <=
                                pending_saturation_count + 1;
                        if (index + 1 == cfg_count) begin
                            index <= 0;
                            state <= S_COMMIT;
                        end else begin
                            index <= index + 1;
                            state <= S_ISSUE;
                        end
                    end
                end

                S_COMMIT: begin
                    out_we <= 1'b1;
                    out_addr <= cfg_out_base + index;
                    out_data <= result_buffer[index];
                    out_count <= out_count + 1;
                    if (index + 1 == cfg_count) begin
                        saturation_count <= pending_saturation_count;
                        state <= S_DONE;
                    end else begin
                        index <= index + 1;
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
