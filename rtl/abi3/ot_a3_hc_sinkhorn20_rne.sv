`timescale 1ns/1ps
// Atomic exact Sinkhorn tail for DeepSeek-V4 HC_PRE.
//
// Input is the 4x4 source-major stable-softmax matrix *after* the contract's
// per-element epsilon addition.  This unit performs the remaining frozen
// sequence exactly: one column normalization, then nineteen row/column pairs.
// Each four-element reduction is (x0+x1)+(x2+x3), every add and divide rounds
// once to binary32 RNE, and epsilon 0x358637bd is added to every denominator.
//
// The matrix is private until all 624 divisions retire.  Any malformed input,
// arithmetic exception or divider exception returns a zero result with a
// nonzero error, so a consumer can never observe a partially normalized matrix.
module ot_a3_hc_sinkhorn20_rne (
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
    localparam [31:0] HC_EPSILON = 32'h3586_37bd;
    localparam [1:0] ERR_NONE = 2'd0;
    localparam [1:0] ERR_NONFINITE = 2'd1;
    localparam [5:0] FINAL_PHASE = 6'd38;

    localparam [2:0] S_IDLE      = 3'd0;
    localparam [2:0] S_SUM       = 3'd1;
    localparam [2:0] S_DIV_ISSUE = 3'd2;
    localparam [2:0] S_DIV_WAIT  = 3'd3;
    localparam [2:0] S_PACK      = 3'd4;
    localparam [2:0] S_OUT       = 3'd5;

    reg [2:0] state;
    reg [31:0] matrix [0:15];
    reg [31:0] denominator;
    reg [5:0] phase;
    reg [1:0] group_index;
    reg [1:0] element_index;

    integer load_index;
    reg [3:0] selected_index;
    reg [3:0] group_index_0;
    reg [3:0] group_index_1;
    reg [3:0] group_index_2;
    reg [3:0] group_index_3;
    reg input_invalid;

    reg [33:0] pair_01;
    reg [33:0] pair_23;
    reg [33:0] pair_total;
    reg [33:0] sum_with_epsilon;
    reg [1:0] sum_error;

    wire row_phase = phase[0];

    // Phase zero and every even phase normalize a column.  Odd phases
    // normalize a row.  The selected index is source-major [source][dest].
    always @* begin
        if (row_phase) begin
            group_index_0 = {group_index, 2'b00};
            group_index_1 = {group_index, 2'b00} + 4'd1;
            group_index_2 = {group_index, 2'b00} + 4'd2;
            group_index_3 = {group_index, 2'b00} + 4'd3;
            selected_index = {group_index, 2'b00} + {2'b0, element_index};
        end else begin
            group_index_0 = {2'b0, group_index};
            group_index_1 = {2'b0, group_index} + 4'd4;
            group_index_2 = {2'b0, group_index} + 4'd8;
            group_index_3 = {2'b0, group_index} + 4'd12;
            selected_index = {2'b0, group_index} + {element_index, 2'b00};
        end

        pair_01 = ot_fp32_rne_pkg::fp32_add_positive_rne(
            matrix[group_index_0], matrix[group_index_1]
        );
        pair_23 = ot_fp32_rne_pkg::fp32_add_positive_rne(
            matrix[group_index_2], matrix[group_index_3]
        );
        pair_total = ot_fp32_rne_pkg::fp32_add_positive_rne(
            pair_01[31:0], pair_23[31:0]
        );
        sum_with_epsilon = ot_fp32_rne_pkg::fp32_add_positive_rne(
            pair_total[31:0], HC_EPSILON
        );
        sum_error = pair_01[33:32] | pair_23[33:32] |
                    pair_total[33:32] | sum_with_epsilon[33:32];

        input_invalid = 1'b0;
        for (load_index = 0; load_index < 16; load_index = load_index + 1)
            if (matrix_codes[32*load_index + 30 -: 8] == 8'hff ||
                matrix_codes[32*load_index + 31] ||
                matrix_codes[32*load_index +: 31] == 0)
                input_invalid = 1'b1;
    end

    wire div_in_valid = state == S_DIV_ISSUE;
    wire div_in_ready;
    wire div_out_valid;
    wire [31:0] div_result_code;
    wire [1:0] div_result_error;

    ot_a3_fp32_div_rne divider (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(div_in_valid),
        .in_ready(div_in_ready),
        .numerator_code(matrix[selected_index]),
        .denominator_code(denominator),
        .out_valid(div_out_valid),
        .out_ready(state == S_DIV_WAIT),
        .result_code(div_result_code),
        .result_error(div_result_error)
    );

    assign in_ready = state == S_IDLE && !out_valid;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            denominator <= 0;
            phase <= 0;
            group_index <= 0;
            element_index <= 0;
            out_valid <= 1'b0;
            result_codes <= 0;
            result_error <= ERR_NONE;
            for (load_index = 0; load_index < 16;
                 load_index = load_index + 1)
                matrix[load_index] <= 0;
        end else begin
            case (state)
                S_IDLE: begin
                    if (in_valid && in_ready) begin
                        result_codes <= 0;
                        result_error <= ERR_NONE;
                        phase <= 0;
                        group_index <= 0;
                        element_index <= 0;
                        if (input_invalid) begin
                            result_error <= ERR_NONFINITE;
                            out_valid <= 1'b1;
                            state <= S_OUT;
                        end else begin
                            for (load_index = 0; load_index < 16;
                                 load_index = load_index + 1)
                                matrix[load_index] <=
                                    matrix_codes[32*load_index +: 32];
                            state <= S_SUM;
                        end
                    end
                end

                S_SUM: begin
                    if (sum_error != ERR_NONE) begin
                        result_codes <= 0;
                        result_error <= sum_error;
                        out_valid <= 1'b1;
                        state <= S_OUT;
                    end else begin
                        denominator <= sum_with_epsilon[31:0];
                        element_index <= 0;
                        state <= S_DIV_ISSUE;
                    end
                end

                S_DIV_ISSUE: begin
                    if (div_in_ready)
                        state <= S_DIV_WAIT;
                end

                S_DIV_WAIT: begin
                    if (div_out_valid) begin
                        if (div_result_error != ERR_NONE) begin
                            result_codes <= 0;
                            result_error <= div_result_error;
                            out_valid <= 1'b1;
                            state <= S_OUT;
                        end else begin
                            matrix[selected_index] <= div_result_code;
                            if (element_index != 3) begin
                                element_index <= element_index + 1'b1;
                                state <= S_DIV_ISSUE;
                            end else if (group_index != 3) begin
                                group_index <= group_index + 1'b1;
                                element_index <= 0;
                                state <= S_SUM;
                            end else if (phase != FINAL_PHASE) begin
                                phase <= phase + 1'b1;
                                group_index <= 0;
                                element_index <= 0;
                                state <= S_SUM;
                            end else begin
                                state <= S_PACK;
                            end
                        end
                    end
                end

                S_PACK: begin
                    for (load_index = 0; load_index < 16;
                         load_index = load_index + 1)
                        result_codes[32*load_index +: 32] <= matrix[load_index];
                    result_error <= ERR_NONE;
                    out_valid <= 1'b1;
                    state <= S_OUT;
                end

                S_OUT: begin
                    if (out_valid && out_ready) begin
                        out_valid <= 1'b0;
                        state <= S_IDLE;
                    end
                end

                default: begin
                    result_codes <= 0;
                    result_error <= ERR_NONFINITE;
                    out_valid <= 1'b1;
                    state <= S_OUT;
                end
            endcase
        end
    end
endmodule
