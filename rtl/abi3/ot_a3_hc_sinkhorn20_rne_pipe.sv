`timescale 1ns/1ps
// Pipelined twin of ot_a3_hc_sinkhorn20_rne: same arithmetic, shorter clock.
//
// WHY.  The routed ASAP7 coverage sweep put this block at **196.6 MHz**, below
// ot_a3_fp32_div_rne's 283.5 MHz, which makes it the ABI 3.0 datapath's clock
// limiter.  Its critical path is not fan-out (every stage on the reported path
// drives one to five loads); it is DEPTH.  ``S_SUM`` computes the whole
// four-element reduction in one cycle as a chain of three dependent binary32
// adds -- ``(x0+x1)`` and ``(x2+x3)`` in parallel, then their sum, then the
// contract's epsilon -- and each of those is a combinational significand
// alignment, add, normalise and round.  The reported path walks about ninety
// cells of adder carry and comparison logic between ``phase[0]`` and
// ``result_codes``.
//
// WHAT CHANGES.  Nothing arithmetic.  The same three adds happen on the same
// values in the same order; they are simply separated by registers, so the
// clock sees one add per cycle instead of three.  ``S_SUM`` becomes
// ``S_SUM_A`` (the two independent pair adds), ``S_SUM_B`` (their sum) and
// ``S_SUM_C`` (the epsilon add, which latches the denominator).  The error
// flags accumulate across the three stages and are tested where the original
// tested them, so a non-finite intermediate still returns a zero matrix with a
// nonzero error and the matrix stays private until every division retires.
//
// COST, MEASURED.  Two extra cycles per four-element reduction.  There are 39
// phases of four groups, so 156 reductions and 312 extra cycles against 624
// divisions that each take tens of cycles: the equivalence bench reports
// **1.01x** the reference's cycles over 35 matrices.
//
// AND WHY THE PIPELINED DIVIDER IS NOT THE DEFAULT.  ot_a3_fp32_div_rne_pipe is
// proven bit-exact against ot_a3_fp32_div_rne on 673 cases and closes at 431.4
// MHz against 283.5, so it looks like the obvious second step.  Instantiated
// here it costs **1.55x** the reference's cycles -- measured on the same 35
// matrices, with the sum pipeline alone at 1.01x, so the whole 54% is the
// divider.  Its own bench had recorded 1.06x of division TIME on its own
// stimulus; a Sinkhorn denominator is a four-element sum plus epsilon and its
// operands land differently in the seeded bracket, which is a reminder that a
// ratio measured on one stimulus is not a property of the module.  At 1.55x the
// cycles, the divider swap would need 1.55x the clock to break even, and 431.4
// over 283.5 is 1.52x.  So it is behind a parameter, defaulted off, with the
// number that decided it written down.
//
// This is a TWIN and not an edit: ot_a3_hc_sinkhorn20_rne is a certifying
// block whose bound vectors are hashed against its source, so the original is
// left byte-identical and rtl/test/tb_a3_hc_sinkhorn20_pipe_equiv.sv drives
// both from one stimulus and compares every output bit.
module ot_a3_hc_sinkhorn20_rne_pipe #(
    // 0 = ot_a3_fp32_div_rne, the divider the certifying block ships and the
    // cycle-correct choice (see the header).  1 = ot_a3_fp32_div_rne_pipe.
    parameter integer PIPELINED_DIVIDER = 0
) (
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
    localparam [2:0] S_SUM_A     = 3'd1;
    localparam [2:0] S_DIV_ISSUE = 3'd2;
    localparam [2:0] S_DIV_WAIT  = 3'd3;
    localparam [2:0] S_PACK      = 3'd4;
    localparam [2:0] S_OUT       = 3'd5;
    localparam [2:0] S_SUM_B     = 3'd6;
    localparam [2:0] S_SUM_C     = 3'd7;

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

    // One add per stage.  The staged values are the registers that break the
    // chain; the combinational results below feed only the next register.
    reg [31:0] pair_01_q;
    reg [31:0] pair_23_q;
    reg [31:0] pair_total_q;
    reg [1:0]  sum_err_q;

    reg [33:0] pair_01;
    reg [33:0] pair_23;
    reg [33:0] pair_total;
    reg [33:0] sum_with_epsilon;

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
            pair_01_q, pair_23_q
        );
        sum_with_epsilon = ot_fp32_rne_pkg::fp32_add_positive_rne(
            pair_total_q, HC_EPSILON
        );

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

    generate
        if (PIPELINED_DIVIDER) begin : g_pipelined_divider
            ot_a3_fp32_div_rne_pipe divider (
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
        end else begin : g_reference_divider
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
        end
    endgenerate

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
            pair_01_q <= 0;
            pair_23_q <= 0;
            pair_total_q <= 0;
            sum_err_q <= ERR_NONE;
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
                            state <= S_SUM_A;
                        end
                    end
                end

                // Stage A: the two independent pair adds.
                S_SUM_A: begin
                    pair_01_q <= pair_01[31:0];
                    pair_23_q <= pair_23[31:0];
                    sum_err_q <= pair_01[33:32] | pair_23[33:32];
                    state <= S_SUM_B;
                end

                // Stage B: their sum.
                S_SUM_B: begin
                    pair_total_q <= pair_total[31:0];
                    sum_err_q <= sum_err_q | pair_total[33:32];
                    state <= S_SUM_C;
                end

                // Stage C: the contract's epsilon, and the same test the
                // single-cycle original applied to the whole reduction.
                S_SUM_C: begin
                    if ((sum_err_q | sum_with_epsilon[33:32]) != ERR_NONE) begin
                        result_codes <= 0;
                        result_error <= sum_err_q | sum_with_epsilon[33:32];
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
                                state <= S_SUM_A;
                            end else if (phase != FINAL_PHASE) begin
                                phase <= phase + 1'b1;
                                group_index <= 0;
                                element_index <= 0;
                                state <= S_SUM_A;
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
