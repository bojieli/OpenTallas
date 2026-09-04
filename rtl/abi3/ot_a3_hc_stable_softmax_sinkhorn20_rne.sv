`timescale 1ns/1ps
// Atomic 4x4 combination-coefficient arithmetic for DeepSeek HC_PRE.
//
// Input is one source-major matrix of finite FP32 affine logits.  The first
// qualified block performs stable softmax with the frozen max/subtract/exp/
// balanced-sum/divide/epsilon order.  Its complete private result feeds the
// separately qualified Sinkhorn-20 tail: one column normalization followed by
// nineteen row/column pairs.  No intermediate matrix is externally visible.
//
// Any upstream or downstream arithmetic refusal publishes an all-zero matrix
// and the nonzero error code.  Thus reset, malformed input, or a failed child
// cannot expose a partially normalized architectural coefficient transaction.
module ot_a3_hc_stable_softmax_sinkhorn20_rne (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         in_valid,
    output wire         in_ready,
    input  wire [511:0] matrix_codes,
    output reg          out_valid,
    input  wire         out_ready,
    output reg  [511:0] result_codes,
    output reg  [1:0]   result_error
);
    localparam [1:0] ERR_NONE = 2'd0;
    localparam [1:0] ERR_ARGUMENT = 2'd1;

    localparam [2:0] S_IDLE           = 3'd0;
    localparam [2:0] S_SOFTMAX_WAIT   = 3'd1;
    localparam [2:0] S_SINKHORN_ISSUE = 3'd2;
    localparam [2:0] S_SINKHORN_WAIT  = 3'd3;
    localparam [2:0] S_OUT            = 3'd4;

    reg [2:0] state;
    reg [511:0] softmax_matrix;

    wire softmax_in_valid = state == S_IDLE && in_valid;
    wire softmax_in_ready;
    wire softmax_out_valid;
    wire [511:0] softmax_result_codes;
    wire [1:0] softmax_result_error;

    ot_a3_hc_stable_softmax_rne stable_softmax (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(softmax_in_valid),
        .in_ready(softmax_in_ready),
        .matrix_codes(matrix_codes),
        .out_valid(softmax_out_valid),
        .out_ready(state == S_SOFTMAX_WAIT),
        .result_codes(softmax_result_codes),
        .result_error(softmax_result_error)
    );

    wire sinkhorn_in_valid = state == S_SINKHORN_ISSUE;
    wire sinkhorn_in_ready;
    wire sinkhorn_out_valid;
    wire [511:0] sinkhorn_result_codes;
    wire [1:0] sinkhorn_result_error;

    ot_a3_hc_sinkhorn20_rne sinkhorn20 (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(sinkhorn_in_valid),
        .in_ready(sinkhorn_in_ready),
        .matrix_codes(softmax_matrix),
        .out_valid(sinkhorn_out_valid),
        .out_ready(state == S_SINKHORN_WAIT),
        .result_codes(sinkhorn_result_codes),
        .result_error(sinkhorn_result_error)
    );

    assign in_ready = state == S_IDLE && !out_valid && softmax_in_ready;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            softmax_matrix <= 0;
            out_valid <= 1'b0;
            result_codes <= 0;
            result_error <= ERR_NONE;
        end else begin
            case (state)
                S_IDLE: begin
                    if (in_valid && in_ready) begin
                        softmax_matrix <= 0;
                        result_codes <= 0;
                        result_error <= ERR_NONE;
                        state <= S_SOFTMAX_WAIT;
                    end
                end

                S_SOFTMAX_WAIT: begin
                    if (softmax_out_valid) begin
                        if (softmax_result_error != ERR_NONE) begin
                            softmax_matrix <= 0;
                            result_codes <= 0;
                            result_error <= softmax_result_error;
                            out_valid <= 1'b1;
                            state <= S_OUT;
                        end else begin
                            softmax_matrix <= softmax_result_codes;
                            state <= S_SINKHORN_ISSUE;
                        end
                    end
                end

                S_SINKHORN_ISSUE: begin
                    if (sinkhorn_in_ready)
                        state <= S_SINKHORN_WAIT;
                end

                S_SINKHORN_WAIT: begin
                    if (sinkhorn_out_valid) begin
                        softmax_matrix <= 0;
                        if (sinkhorn_result_error != ERR_NONE) begin
                            result_codes <= 0;
                            result_error <= sinkhorn_result_error;
                        end else begin
                            result_codes <= sinkhorn_result_codes;
                            result_error <= ERR_NONE;
                        end
                        out_valid <= 1'b1;
                        state <= S_OUT;
                    end
                end

                S_OUT: begin
                    if (out_valid && out_ready) begin
                        out_valid <= 1'b0;
                        result_codes <= 0;
                        result_error <= ERR_NONE;
                        state <= S_IDLE;
                    end
                end

                default: begin
                    softmax_matrix <= 0;
                    result_codes <= 0;
                    result_error <= ERR_ARGUMENT;
                    out_valid <= 1'b1;
                    state <= S_OUT;
                end
            endcase
        end
    end
endmodule
