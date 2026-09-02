`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Bounded VECTOR.INDEX_SCORE datapath.
//
// The integrated profile accepts batch one flattened into cfg_rows, four
// heads, up to eight candidates, a head dimension up to sixteen, and scale
// exactly 1.0.  Per head it performs an ascending-dimension BF16 dot product,
// rounds that score to BF16, applies ReLU, multiplies by the BF16 head weight
// and rounds again.  Four head contributions reduce as the frozen balanced
// tree (0+1)+(2+3), followed by the output BF16 conversion.
//
// Every operand is scanned before arithmetic and every output is buffered
// before commit.  A late poisoned key, weight, or intermediate therefore
// cannot expose a partial score tensor.
// ---------------------------------------------------------------------------
module ot_a3_vector_index_score #(
    parameter [15:0] MAX_ROWS = 16'd4,
    parameter integer HEADS = 4,
    parameter [15:0] MAX_CANDIDATES = 16'd8,
    parameter [15:0] MAX_DEPTH = 16'd16,
    parameter integer MAX_OUTPUTS = MAX_ROWS * MAX_CANDIDATES
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [15:0] cfg_rows,
    input  wire [15:0] cfg_cols,
    input  wire [15:0] cfg_depth,
    input  wire [31:0] cfg_count,
    input  wire [31:0] cfg_heads,
    input  wire [31:0] cfg_scale_bits,
    input  wire [7:0]  cfg_dtype_a,
    input  wire [7:0]  cfg_dtype_b,
    input  wire [31:0] cfg_query_base,
    input  wire [31:0] cfg_key_base,
    input  wire [31:0] cfg_weight_base,
    input  wire [31:0] cfg_out_base,

    output reg         q_rd_en,
    output reg  [31:0] q_rd_addr,
    input  wire [31:0] q_rd_data,
    output reg         k_rd_en,
    output reg  [31:0] k_rd_addr,
    input  wire [31:0] k_rd_data,
    output reg         w_rd_en,
    output reg  [31:0] w_rd_addr,
    input  wire [31:0] w_rd_data,
    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count,
    output reg  [31:0] work_count,
    output reg  [31:0] saturation_count
);
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE =
        ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_PRODUCT_RANGE = ot_a3_engine_pkg::ERR_PRODUCT_RANGE;
    localparam [7:0] ERR_ACCUMULATE_RANGE =
        ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;
    localparam [7:0] FMT_BF16 = 8'h10;
    localparam [1:0] LAST_HEAD = 2'd3;

    localparam [4:0] S_IDLE        = 5'd0;
    localparam [4:0] S_SCAN_ISSUE  = 5'd1;
    localparam [4:0] S_SCAN_WAIT   = 5'd2;
    localparam [4:0] S_SCAN_CHECK  = 5'd3;
    localparam [4:0] S_DOT_ISSUE   = 5'd4;
    localparam [4:0] S_DOT_WAIT    = 5'd5;
    localparam [4:0] S_DOT_STEP    = 5'd6;
    localparam [4:0] S_WEIGHT_ISSUE = 5'd7;
    localparam [4:0] S_WEIGHT_WAIT = 5'd8;
    localparam [4:0] S_WEIGHT      = 5'd9;
    localparam [4:0] S_REDUCE_1    = 5'd10;
    localparam [4:0] S_REDUCE_2    = 5'd11;
    localparam [4:0] S_COMMIT      = 5'd12;
    localparam [4:0] S_DONE        = 5'd13;

    reg [4:0] state;
    reg [1:0] scan_kind;
    reg [31:0] index;
    reg [15:0] row;
    reg [15:0] candidate;
    reg [1:0] head;
    reg [15:0] depth_index;
    reg [31:0] accumulator;
    reg [31:0] relu_value;
    reg [31:0] reduce_left;
    reg [31:0] reduce_right;
    reg [31:0] pending_saturation_count;
    reg [31:0] contributions [0:HEADS-1];
    reg [31:0] result_buffer [0:MAX_OUTPUTS-1];

    wire [31:0] query_elements =
        {16'b0, cfg_rows} * HEADS * {16'b0, cfg_depth};
    wire [31:0] key_elements =
        {16'b0, cfg_cols} * {16'b0, cfg_depth};
    wire [31:0] weight_elements = {16'b0, cfg_rows} * HEADS;
    wire [31:0] scan_limit = (scan_kind == 0) ? query_elements
                               : (scan_kind == 1) ? key_elements
                               : weight_elements;

    wire [33:0] decoded_q = ot_a3_format_pkg::decode_bf16(q_rd_data[15:0]);
    wire [33:0] decoded_k = ot_a3_format_pkg::decode_bf16(k_rd_data[15:0]);
    wire [33:0] decoded_w = ot_a3_format_pkg::decode_bf16(w_rd_data[15:0]);
    wire [33:0] dot_sum =
        ot_fp32_rne_pkg::bf16_bf16_fp32_product_add_rne(
            accumulator, q_rd_data[15:0], k_rd_data[15:0]
        );
    wire [18:0] dot_narrowed =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(dot_sum[31:0]);
    wire [33:0] weighted_product =
        ot_fp32_rne_pkg::fp32_mul_rne(relu_value, decoded_w[31:0]);
    wire [18:0] weighted_narrowed =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(weighted_product[31:0]);
    wire [33:0] pair_01 = ot_fp32_rne_pkg::fp32_add_rne(
        contributions[0], contributions[1]
    );
    wire [33:0] pair_23 = ot_fp32_rne_pkg::fp32_add_rne(
        contributions[2], contributions[3]
    );
    wire [33:0] head_total =
        ot_fp32_rne_pkg::fp32_add_rne(reduce_left, reduce_right);
    wire [18:0] output_narrowed =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(head_total[31:0]);

    wire [33:0] scan_decoded = (scan_kind == 0) ? decoded_q
                                 : (scan_kind == 1) ? decoded_k
                                 : decoded_w;
    wire configuration_supported =
        (cfg_dtype_a == FMT_BF16) && (cfg_dtype_b == FMT_BF16) &&
        (cfg_rows != 0) && (cfg_rows <= MAX_ROWS) &&
        (cfg_cols != 0) && (cfg_cols <= MAX_CANDIDATES) &&
        (cfg_depth != 0) && (cfg_depth <= MAX_DEPTH) &&
        (cfg_heads == HEADS) && (cfg_scale_bits == 32'h3f80_0000) &&
        (cfg_count == ({16'b0, cfg_rows} * {16'b0, cfg_cols}));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            scan_kind <= 0;
            index <= 0;
            row <= 0;
            candidate <= 0;
            head <= 0;
            depth_index <= 0;
            accumulator <= 0;
            relu_value <= 0;
            reduce_left <= 0;
            reduce_right <= 0;
            q_rd_en <= 1'b0;
            q_rd_addr <= 0;
            k_rd_en <= 1'b0;
            k_rd_addr <= 0;
            w_rd_en <= 1'b0;
            w_rd_addr <= 0;
            out_we <= 1'b0;
            out_addr <= 0;
            out_data <= 0;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            out_count <= 0;
            work_count <= 0;
            saturation_count <= 0;
            pending_saturation_count <= 0;
        end else begin
            done <= 1'b0;
            q_rd_en <= 1'b0;
            k_rd_en <= 1'b0;
            w_rd_en <= 1'b0;
            out_we <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        out_count <= 0;
                        work_count <= 0;
                        saturation_count <= 0;
                        pending_saturation_count <= 0;
                        scan_kind <= 0;
                        index <= 0;
                        row <= 0;
                        candidate <= 0;
                        head <= 0;
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
                        q_rd_en <= 1'b1;
                        q_rd_addr <= cfg_query_base + index;
                    end else if (scan_kind == 1) begin
                        k_rd_en <= 1'b1;
                        k_rd_addr <= cfg_key_base + index;
                    end else begin
                        w_rd_en <= 1'b1;
                        w_rd_addr <= cfg_weight_base + index;
                    end
                    state <= S_SCAN_WAIT;
                end

                S_SCAN_WAIT: state <= S_SCAN_CHECK;

                S_SCAN_CHECK: begin
                    if (scan_decoded[33:32] != 0) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else if (index + 1 == scan_limit) begin
                        index <= 0;
                        if (scan_kind == 2) begin
                            row <= 0;
                            candidate <= 0;
                            head <= 0;
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
                    q_rd_en <= 1'b1;
                    q_rd_addr <= cfg_query_base +
                        ({16'b0, row} * HEADS * {16'b0, cfg_depth}) +
                        (head * {16'b0, cfg_depth}) + {16'b0, depth_index};
                    k_rd_en <= 1'b1;
                    k_rd_addr <= cfg_key_base +
                        ({16'b0, candidate} * {16'b0, cfg_depth}) +
                        {16'b0, depth_index};
                    state <= S_DOT_WAIT;
                end

                S_DOT_WAIT: state <= S_DOT_STEP;

                S_DOT_STEP: begin
                    if ((decoded_q[33:32] != 0) ||
                        (decoded_k[33:32] != 0)) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else if (dot_sum[33:32] != 0) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        work_count <= work_count + 1;
                        if (depth_index + 1 == cfg_depth) begin
                            if (dot_narrowed[18:17] != 0) begin
                                error_code <= ERR_ACCUMULATE_RANGE;
                                state <= S_DONE;
                            end else begin
                                if (dot_narrowed[16])
                                    pending_saturation_count <=
                                        pending_saturation_count + 1;
                                // ReLU is applied after the architectural
                                // BF16 dot-product boundary.
                                relu_value <= dot_narrowed[15]
                                    ? 32'b0 : {dot_narrowed[15:0], 16'b0};
                                state <= S_WEIGHT_ISSUE;
                            end
                        end else begin
                            accumulator <= dot_sum[31:0];
                            depth_index <= depth_index + 1;
                            state <= S_DOT_ISSUE;
                        end
                    end
                end

                S_WEIGHT_ISSUE: begin
                    w_rd_en <= 1'b1;
                    w_rd_addr <= cfg_weight_base +
                        ({16'b0, row} * HEADS) + {30'b0, head};
                    state <= S_WEIGHT_WAIT;
                end

                S_WEIGHT_WAIT: state <= S_WEIGHT;

                S_WEIGHT: begin
                    if (decoded_w[33:32] != 0) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else if ((weighted_product[33:32] != 0) ||
                                 (weighted_narrowed[18:17] != 0)) begin
                        error_code <= ERR_PRODUCT_RANGE;
                        state <= S_DONE;
                    end else begin
                        if (weighted_narrowed[16])
                            pending_saturation_count <=
                                pending_saturation_count + 1;
                        contributions[head] <=
                            {weighted_narrowed[15:0], 16'b0};
                        accumulator <= 0;
                        depth_index <= 0;
                        if (head == LAST_HEAD) begin
                            state <= S_REDUCE_1;
                        end else begin
                            head <= head + 1;
                            state <= S_DOT_ISSUE;
                        end
                    end
                end

                S_REDUCE_1: begin
                    if ((pair_01[33:32] != 0) || (pair_23[33:32] != 0)) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        reduce_left <= pair_01[31:0];
                        reduce_right <= pair_23[31:0];
                        state <= S_REDUCE_2;
                    end
                end

                S_REDUCE_2: begin
                    if ((head_total[33:32] != 0) ||
                        (output_narrowed[18:17] != 0)) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        if (output_narrowed[16])
                            pending_saturation_count <=
                                pending_saturation_count + 1;
                        result_buffer[({16'b0, row} * {16'b0, cfg_cols}) +
                                      {16'b0, candidate}] <=
                            {16'b0, output_narrowed[15:0]};
                        head <= 0;
                        depth_index <= 0;
                        accumulator <= 0;
                        if (candidate + 1 < cfg_cols) begin
                            candidate <= candidate + 1;
                            state <= S_DOT_ISSUE;
                        end else if (row + 1 < cfg_rows) begin
                            candidate <= 0;
                            row <= row + 1;
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
