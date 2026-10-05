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

    //: WIDENED to four bits. The three-bit encoding had all eight values in
    //: use, so the pipelined-adder wait states below could not be added without
    //: colliding with an existing one -- and a collision is silent: both
    //: elaborators accept two localparams with one value and a case takes the
    //: FIRST arm, which is how ot_a3_vector_mhc_post deadlocked every MHC_POST
    //: case earlier. tools/audit_rtl_state_code_collisions.py gates that now,
    //: and the new codes start at 8, one past the old maximum.
    localparam [3:0] S_IDLE      = 4'd0;
    localparam [3:0] S_SUM_A     = 4'd1;
    localparam [3:0] S_DIV_ISSUE = 4'd2;
    localparam [3:0] S_DIV_WAIT  = 4'd3;
    localparam [3:0] S_PACK      = 4'd4;
    localparam [3:0] S_OUT       = 4'd5;
    localparam [3:0] S_SUM_A_WAIT = 4'd8;
    localparam [3:0] S_SUM_B_WAIT = 4'd9;
    localparam [3:0] S_SUM_C_WAIT = 4'd10;

    reg [3:0] state;
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

    // Registered adder requests carry dependent sums without duplicate payload.
    reg [1:0]  sum_err_q;

    //: THE REDUCTION'S THREE ADDS, PIPELINED.
    //:
    //: Each was a single combinational ot_fp32_rne_pkg::fp32_add_positive_rne
    //: ALREADY alone between registers -- the pair adds read the matrix, the
    //: tree add reads pair_01_q and pair_23_q, the epsilon add reads
    //: pair_total_q -- so this block's clock WAS one such add plus the matrix
    //: read mux, and no rescheduling could reach past it. It routed at 276.9 MHz
    //: and, re-routed at a 1.8 ns target instead of 3.7 ns, returned 278.9 MHz:
    //: 0.7 percent for twice the effort. That made it the published ABI 3.0
    //: design limiter.
    //:
    //: ot_fp32_add_positive_rne_pipe is that same function in five stages,
    //: qualified bit-identical to the authority over 73,984 pairs at II=1
    //: including every refusal, both zero bypasses, subnormals, the full
    //: alignment range past the 28-bit jam saturation, carry out of the add and
    //: out of the round, and the overflow at 255. Standalone it closes at
    //: 1,075.0 MHz with positive slack.
    //:
    //: Two instances: the pair adds are independent and issue together, and the
    //: left one is reused for the tree add and the epsilon add, which are
    //: strictly sequential. The reduction costs three waits of LATENCY instead
    //: of three single cycles.
    localparam integer ADD_LATENCY = 5;
    reg         add_valid;
    reg  [31:0] add_l_a, add_l_b, add_r_a, add_r_b;
    wire [31:0] add_l_y, add_r_y;
    wire [1:0]  add_l_err, add_r_err;
    wire        add_l_done, add_r_done;
    ot_fp32_add_positive_rne_pipe adder_left (
        .clk(clk), .rst_n(rst_n), .valid_in(add_valid),
        .a(add_l_a), .b(add_l_b),
        .y(add_l_y), .err(add_l_err), .valid_out(add_l_done)
    );
    ot_fp32_add_positive_rne_pipe adder_right (
        .clk(clk), .rst_n(rst_n), .valid_in(add_valid),
        .a(add_r_a), .b(add_r_b),
        .y(add_r_y), .err(add_r_err), .valid_out(add_r_done)
    );

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


        input_invalid = 1'b0;
        for (load_index = 0; load_index < 16; load_index = load_index + 1)
            if (matrix_codes[32*load_index + 30 -: 8] == 8'hff ||
                matrix_codes[32*load_index + 31] ||
                matrix_codes[32*load_index +: 31] == 0)
                input_invalid = 1'b1;
    end

    // Prepare the following numerator while the divider owns the current one.
    // Only a successful response may hand off another division in this group.
    // Advance the lookahead on a handoff too: a zero numerator can
    // complete in one cycle, so waiting for the new index would be too late.
    wire [1:0] next_element = element_index + (div_handoff ? 2'd2 : 2'd1);
    wire [3:0] next_selected = row_phase ? {group_index,next_element} :
                                                        {next_element,group_index};
    reg [31:0] next_numerator;
    always @(posedge clk) next_numerator <= matrix[next_selected];
    wire div_handoff = state == S_DIV_WAIT && div_out_valid &&
                      div_result_error == ERR_NONE && element_index != 2'd3;
    wire div_in_valid = state == S_DIV_ISSUE || div_handoff;
    wire [31:0] div_numerator = state == S_DIV_ISSUE ? matrix[selected_index] : next_numerator;
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
                .numerator_code(div_numerator),
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
                .numerator_code(div_numerator),
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
            add_valid <= 1'b0;
            add_l_a <= 32'd0; add_l_b <= 32'd0;
            add_r_a <= 32'd0; add_r_b <= 32'd0;
            sum_err_q <= ERR_NONE;
            for (load_index = 0; load_index < 16;
                 load_index = load_index + 1)
                matrix[load_index] <= 0;
        end else begin
            //: one cycle wide: holding it would issue a second add
            add_valid <= 1'b0;
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

                // Stage A: the two independent pair adds, issued together.
                S_SUM_A: begin
                    add_l_a <= matrix[group_index_0];
                    add_l_b <= matrix[group_index_1];
                    add_r_a <= matrix[group_index_2];
                    add_r_b <= matrix[group_index_3];
                    add_valid <= 1'b1;
                    state <= S_SUM_A_WAIT;
                end

                //: both adders share one valid and have one latency, so they
                //: retire on the same cycle; waiting on the left one waits on
                //: both, and the right one's error is read here too
                S_SUM_A_WAIT: begin
                    if (add_l_done) begin
                        add_l_a <= add_l_y;
                        add_l_b <= add_r_y;
                        add_r_a <= 32'd0;
                        add_r_b <= 32'd0;
                        add_valid <= 1'b1;
                        sum_err_q <= add_l_err | add_r_err;
                        state <= S_SUM_B_WAIT;
                    end
                end

                // Feed each completed sum into the next registered request.
                // No extra payload copy or issue state between dependent adds.
                S_SUM_B_WAIT: begin
                    if (add_l_done) begin
                        add_l_a <= add_l_y;
                        add_l_b <= HC_EPSILON;
                        add_r_a <= 32'd0;
                        add_r_b <= 32'd0;
                        add_valid <= 1'b1;
                        sum_err_q <= sum_err_q | add_l_err;
                        state <= S_SUM_C_WAIT;
                    end
                end

                //: the same test the single-cycle original applied to the whole
                //: reduction, on the pipelined result
                S_SUM_C_WAIT: begin
                    if (add_l_done) begin
                    if ((sum_err_q | add_l_err) != ERR_NONE) begin
                        result_codes <= 0;
                        result_error <= sum_err_q | add_l_err;
                        out_valid <= 1'b1;
                        state <= S_OUT;
                    end else begin
                        denominator <= add_l_y;
                        element_index <= 0;
                        state <= S_DIV_ISSUE;
                    end
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
                                // Both divider variants permit replacement on
                                // the output handshake; retain fallback if busy.
                                state <= div_in_ready ? S_DIV_WAIT : S_DIV_ISSUE;
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
