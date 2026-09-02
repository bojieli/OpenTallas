`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Bounded VECTOR.COMPRESS / COMPRESS_PROJECT datapath (aux0 == 0).
//
// BF16 hidden rows are projected by independent BF16 KV and gate matrices.
// Each dot product walks the reduction dimension in ascending order and keeps
// a binary32 accumulator.  The FP32 output is packed in the frozen
// [row, plane, column] order: the complete KV plane precedes the gate plane
// for each row.  Other COMPRESS sub-cases remain fail-closed.
//
// A complete input preflight and a private output buffer make the operation
// atomic with respect to every detected operand or arithmetic fault.
// ---------------------------------------------------------------------------
module ot_a3_vector_compress_project #(
    parameter [15:0] MAX_ROWS = 16'd8,
    parameter [15:0] MAX_COLS = 16'd16,
    parameter [15:0] MAX_DEPTH = 16'd64,
    parameter integer MAX_OUTPUTS = MAX_ROWS * MAX_COLS * 2
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [15:0] cfg_rows,
    input  wire [15:0] cfg_cols,
    input  wire [15:0] cfg_depth,
    input  wire [31:0] cfg_count,
    input  wire [15:0] cfg_aux0,
    input  wire [7:0]  cfg_dtype_a,
    input  wire [7:0]  cfg_dtype_b,
    input  wire [31:0] cfg_hidden_base,
    input  wire [31:0] cfg_kv_base,
    input  wire [31:0] cfg_gate_base,
    input  wire [31:0] cfg_out_base,

    output reg         h_rd_en,
    output reg  [31:0] h_rd_addr,
    input  wire [31:0] h_rd_data,
    output reg         kv_rd_en,
    output reg  [31:0] kv_rd_addr,
    input  wire [31:0] kv_rd_data,
    output reg         gate_rd_en,
    output reg  [31:0] gate_rd_addr,
    input  wire [31:0] gate_rd_data,
    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count,
    output reg  [31:0] work_count
);
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE =
        ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_PRODUCT_RANGE = ot_a3_engine_pkg::ERR_PRODUCT_RANGE;
    localparam [7:0] ERR_ACCUMULATE_RANGE =
        ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;
    localparam [7:0] FMT_BF16 = 8'h10;
    localparam [15:0] COMPRESS_PROJECT = 16'd0;

    localparam [3:0] S_IDLE       = 4'd0;
    localparam [3:0] S_SCAN_ISSUE = 4'd1;
    localparam [3:0] S_SCAN_WAIT  = 4'd2;
    localparam [3:0] S_SCAN_CHECK = 4'd3;
    localparam [3:0] S_DOT_ISSUE  = 4'd4;
    localparam [3:0] S_DOT_WAIT   = 4'd5;
    localparam [3:0] S_DOT_STEP   = 4'd6;
    localparam [3:0] S_COMMIT     = 4'd7;
    localparam [3:0] S_DONE       = 4'd8;

    reg [3:0] state;
    reg [1:0] scan_kind;
    reg [31:0] index;
    reg [15:0] row;
    reg        plane;
    reg [15:0] col;
    reg [15:0] depth_index;
    reg [31:0] accumulator;
    reg [31:0] result_buffer [0:MAX_OUTPUTS-1];

    wire [31:0] hidden_elements =
        {16'b0, cfg_rows} * {16'b0, cfg_depth};
    wire [31:0] matrix_elements =
        {16'b0, cfg_cols} * {16'b0, cfg_depth};
    wire [31:0] scan_limit = (scan_kind == 0)
                           ? hidden_elements : matrix_elements;

    wire [33:0] decoded_hidden =
        ot_a3_format_pkg::decode_bf16(h_rd_data[15:0]);
    wire [33:0] decoded_kv =
        ot_a3_format_pkg::decode_bf16(kv_rd_data[15:0]);
    wire [33:0] decoded_gate =
        ot_a3_format_pkg::decode_bf16(gate_rd_data[15:0]);
    wire [33:0] decoded_weight = plane ? decoded_gate : decoded_kv;
    wire [15:0] weight_code = plane
        ? gate_rd_data[15:0] : kv_rd_data[15:0];
    wire [33:0] accumulated =
        ot_fp32_rne_pkg::bf16_bf16_fp32_product_add_rne(
            accumulator, h_rd_data[15:0], weight_code
        );

    wire configuration_supported =
        (cfg_aux0 == COMPRESS_PROJECT) &&
        (cfg_dtype_a == FMT_BF16) && (cfg_dtype_b == FMT_BF16) &&
        (cfg_rows != 0) && (cfg_rows <= MAX_ROWS) &&
        (cfg_cols != 0) && (cfg_cols <= MAX_COLS) &&
        (cfg_depth != 0) && (cfg_depth <= MAX_DEPTH) &&
        (cfg_count == ({16'b0, cfg_rows} * {16'b0, cfg_cols} * 2));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            scan_kind <= 0;
            index <= 0;
            row <= 0;
            plane <= 0;
            col <= 0;
            depth_index <= 0;
            accumulator <= 0;
            h_rd_en <= 1'b0;
            h_rd_addr <= 0;
            kv_rd_en <= 1'b0;
            kv_rd_addr <= 0;
            gate_rd_en <= 1'b0;
            gate_rd_addr <= 0;
            out_we <= 1'b0;
            out_addr <= 0;
            out_data <= 0;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            out_count <= 0;
            work_count <= 0;
        end else begin
            done <= 1'b0;
            h_rd_en <= 1'b0;
            kv_rd_en <= 1'b0;
            gate_rd_en <= 1'b0;
            out_we <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        out_count <= 0;
                        work_count <= 0;
                        scan_kind <= 0;
                        index <= 0;
                        row <= 0;
                        plane <= 0;
                        col <= 0;
                        depth_index <= 0;
                        accumulator <= 0;
                        if (!configuration_supported) begin
                            error_code <= ERR_SHAPE;
                            state <= S_DONE;
                        end else begin
                            state <= S_SCAN_ISSUE;
                        end
                    end
                end

                S_SCAN_ISSUE: begin
                    if (scan_kind == 0) begin
                        h_rd_en <= 1'b1;
                        h_rd_addr <= cfg_hidden_base + index;
                    end else if (scan_kind == 1) begin
                        kv_rd_en <= 1'b1;
                        kv_rd_addr <= cfg_kv_base + index;
                    end else begin
                        gate_rd_en <= 1'b1;
                        gate_rd_addr <= cfg_gate_base + index;
                    end
                    state <= S_SCAN_WAIT;
                end

                S_SCAN_WAIT: state <= S_SCAN_CHECK;

                S_SCAN_CHECK: begin
                    if (((scan_kind == 0) &&
                         (decoded_hidden[33:32] != 0)) ||
                        ((scan_kind == 1) && (decoded_kv[33:32] != 0)) ||
                        ((scan_kind == 2) && (decoded_gate[33:32] != 0))) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else if (index + 1 == scan_limit) begin
                        index <= 0;
                        if (scan_kind == 2) begin
                            row <= 0;
                            plane <= 0;
                            col <= 0;
                            depth_index <= 0;
                            accumulator <= 0;
                            state <= S_DOT_ISSUE;
                        end else begin
                            scan_kind <= scan_kind + 1;
                            state <= S_SCAN_ISSUE;
                        end
                    end else begin
                        index <= index + 1;
                        state <= S_SCAN_ISSUE;
                    end
                end

                S_DOT_ISSUE: begin
                    h_rd_en <= 1'b1;
                    h_rd_addr <= cfg_hidden_base +
                        ({16'b0, row} * {16'b0, cfg_depth}) +
                        {16'b0, depth_index};
                    if (!plane) begin
                        kv_rd_en <= 1'b1;
                        kv_rd_addr <= cfg_kv_base +
                            ({16'b0, col} * {16'b0, cfg_depth}) +
                            {16'b0, depth_index};
                    end else begin
                        gate_rd_en <= 1'b1;
                        gate_rd_addr <= cfg_gate_base +
                            ({16'b0, col} * {16'b0, cfg_depth}) +
                            {16'b0, depth_index};
                    end
                    state <= S_DOT_WAIT;
                end

                S_DOT_WAIT: state <= S_DOT_STEP;

                S_DOT_STEP: begin
                    if ((decoded_hidden[33:32] != 0) ||
                        (decoded_weight[33:32] != 0)) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else if (accumulated[33:32] != 0) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else if (depth_index + 1 < cfg_depth) begin
                        accumulator <= accumulated[31:0];
                        depth_index <= depth_index + 1;
                        state <= S_DOT_ISSUE;
                    end else begin
                        // Frozen projection_order: kv_then_gate.
                        result_buffer[
                            ({16'b0, row} * {16'b0, cfg_cols} * 2) +
                            (plane ? {16'b0, cfg_cols} : 0) + {16'b0, col}
                        ] <= accumulated[31:0];
                        accumulator <= 0;
                        depth_index <= 0;
                        if (col + 1 < cfg_cols) begin
                            col <= col + 1;
                            state <= S_DOT_ISSUE;
                        end else if (!plane) begin
                            col <= 0;
                            plane <= 1'b1;
                            state <= S_DOT_ISSUE;
                        end else if (row + 1 < cfg_rows) begin
                            row <= row + 1;
                            plane <= 1'b0;
                            col <= 0;
                            state <= S_DOT_ISSUE;
                        end else begin
                            index <= 0;
                            state <= S_COMMIT;
                        end
                    end
                end

                S_COMMIT: begin
                    out_we <= 1'b1;
                    out_addr <= cfg_out_base + index;
                    out_data <= result_buffer[index];
                    out_count <= out_count + 1;
                    work_count <= work_count + 1;
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
