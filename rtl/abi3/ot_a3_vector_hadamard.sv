`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Bounded VECTOR.HADAMARD datapath.
//
// This is the qualified 128-point transform: seven ascending-stride binary32
// butterfly stages, multiplication by the exact binary32 encoding of
// 1/sqrt(128), and one BF16 RNE conversion.  At most four rows are accepted.
// Input and intermediate values remain in a private buffer until the complete
// operation succeeds, so every refusal leaves the destination untouched.
// ---------------------------------------------------------------------------
module ot_a3_vector_hadamard #(
    parameter [15:0] MAX_ROWS = 16'd4,
    parameter [15:0] WIDTH = 16'd128,
    parameter integer MAX_ELEMENTS = MAX_ROWS * WIDTH
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [15:0] cfg_rows,
    input  wire [15:0] cfg_cols,
    input  wire [31:0] cfg_count,
    input  wire [7:0]  cfg_dtype_a,
    input  wire [31:0] cfg_a_base,
    input  wire [31:0] cfg_out_base,

    output reg         a_rd_en,
    output reg  [31:0] a_rd_addr,
    input  wire [31:0] a_rd_data,
    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count
);
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE =
        ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_ACCUMULATE_RANGE =
        ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;
    localparam [7:0] FMT_BF16 = 8'h10;

    // Exact binary32 encoding frozen by runtime.reference.hadamard.
    localparam [31:0] HADAMARD_SCALE = 32'h3db5_04f3;

    localparam [3:0] S_IDLE       = 4'd0;
    localparam [3:0] S_LOAD_ISSUE = 4'd1;
    localparam [3:0] S_LOAD_WAIT  = 4'd2;
    localparam [3:0] S_LOAD       = 4'd3;
    localparam [3:0] S_CAPTURE    = 4'd4;
    localparam [3:0] S_BUTTERFLY  = 4'd5;
    localparam [3:0] S_NORMALIZE  = 4'd6;
    localparam [3:0] S_COMMIT     = 4'd7;
    localparam [3:0] S_DONE       = 4'd8;

    reg [3:0] state;
    reg [31:0] index;
    reg [15:0] row;
    reg [7:0] stride;
    reg [7:0] group_base;
    reg [7:0] offset;
    reg [31:0] lower_value;
    reg [31:0] upper_value;
    reg [31:0] values [0:MAX_ELEMENTS-1];

    wire [31:0] lower_index = ({16'b0, row} * WIDTH) +
                              {24'b0, group_base} + {24'b0, offset};
    wire [31:0] upper_index = lower_index + {24'b0, stride};
    wire [15:0] next_group = {8'b0, group_base} +
                             ({8'b0, stride} << 1);
    wire [33:0] decoded = ot_a3_format_pkg::decode_bf16(a_rd_data[15:0]);
    wire [33:0] summed =
        ot_fp32_rne_pkg::fp32_add_rne(lower_value, upper_value);
    wire [31:0] negated_upper = (upper_value[30:0] == 0)
                              ? 32'b0 : (upper_value ^ 32'h8000_0000);
    wire [33:0] differed =
        ot_fp32_rne_pkg::fp32_add_rne(lower_value, negated_upper);
    wire [33:0] scaled =
        ot_fp32_rne_pkg::fp32_mul_rne(values[index], HADAMARD_SCALE);
    wire [18:0] narrowed =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(scaled[31:0]);

    wire configuration_supported =
        (cfg_dtype_a == FMT_BF16) && (cfg_rows != 0) &&
        (cfg_rows <= MAX_ROWS) && (cfg_cols == WIDTH) &&
        (cfg_count == ({16'b0, cfg_rows} * WIDTH));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            index <= 0;
            row <= 0;
            stride <= 1;
            group_base <= 0;
            offset <= 0;
            lower_value <= 0;
            upper_value <= 0;
            a_rd_en <= 1'b0;
            a_rd_addr <= 0;
            out_we <= 1'b0;
            out_addr <= 0;
            out_data <= 0;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            out_count <= 0;
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
                        index <= 0;
                        row <= 0;
                        stride <= 1;
                        group_base <= 0;
                        offset <= 0;
                        if (!configuration_supported) begin
                            error_code <= ERR_SHAPE;
                            state <= S_DONE;
                        end else begin
                            state <= S_LOAD_ISSUE;
                        end
                    end
                end

                S_LOAD_ISSUE: begin
                    a_rd_en <= 1'b1;
                    a_rd_addr <= cfg_a_base + index;
                    state <= S_LOAD_WAIT;
                end

                S_LOAD_WAIT: state <= S_LOAD;

                S_LOAD: begin
                    if (decoded[33:32] != 0) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else begin
                        values[index] <= decoded[31:0];
                        if (index + 1 == cfg_count) begin
                            index <= 0;
                            state <= S_CAPTURE;
                        end else begin
                            index <= index + 1;
                            state <= S_LOAD_ISSUE;
                        end
                    end
                end

                S_CAPTURE: begin
                    lower_value <= values[lower_index];
                    upper_value <= values[upper_index];
                    state <= S_BUTTERFLY;
                end

                S_BUTTERFLY: begin
                    if ((summed[33:32] != 0) || (differed[33:32] != 0)) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        values[lower_index] <= summed[31:0];
                        values[upper_index] <= differed[31:0];
                        if (offset + 1 < stride) begin
                            offset <= offset + 1;
                            state <= S_CAPTURE;
                        end else if (next_group < WIDTH) begin
                            offset <= 0;
                            group_base <= next_group[7:0];
                            state <= S_CAPTURE;
                        end else if (row + 1 < cfg_rows) begin
                            offset <= 0;
                            group_base <= 0;
                            row <= row + 1;
                            state <= S_CAPTURE;
                        end else if (stride < 64) begin
                            offset <= 0;
                            group_base <= 0;
                            row <= 0;
                            stride <= stride << 1;
                            state <= S_CAPTURE;
                        end else begin
                            index <= 0;
                            state <= S_NORMALIZE;
                        end
                    end
                end

                S_NORMALIZE: begin
                    // Saturation is a refusal for the qualified transform,
                    // unlike generic BF16 storage conversion.
                    if ((scaled[33:32] != 0) ||
                        (narrowed[18:17] != 0) || narrowed[16]) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        values[index] <= {16'b0, narrowed[15:0]};
                        if (index + 1 == cfg_count) begin
                            index <= 0;
                            state <= S_COMMIT;
                        end else begin
                            index <= index + 1;
                        end
                    end
                end

                S_COMMIT: begin
                    out_we <= 1'b1;
                    out_addr <= cfg_out_base + index;
                    out_data <= values[index];
                    out_count <= out_count + 1;
                    if (index + 1 == cfg_count) begin
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
