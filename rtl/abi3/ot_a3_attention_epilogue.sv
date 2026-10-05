`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ATTENTION.SPARSE's closing stage: the sink term, the normalise, the narrow.
//
// After every source block has been folded, the reference closes a (query row,
// head) with four lines:
//
//     sink_exp    = exp_cr32(sink_values - maxima)
//     denominator = sums + sink_exp
//     context     = accumulator / denominator
//     codes       = _narrow(context)
//
// and this is those four, on the units that already exist: the certifying
// exponential, ot_fp32_add_rne_pipe, ot_a3_fp32_div_rne and
// ot_fp32_rne_pkg::fp32_to_bf16_rne -- which was CHECKED against the reference's
// own ``_narrow``, not assumed to match it: identical code and identical
// saturation flag over 119,570 finite binary32 inputs, the saturating and
// zero-canonicalising edges included.
//
// TWO PLACES THIS REFUSES WHERE THE REFERENCE REPAIRS, and both are recorded
// because neither is a property of the arithmetic:
//
//   1. A SINK LOGIT ABOVE THE ROW MAXIMUM -- NO LONGER REFUSED. Nothing bounds
//      the sink from above: ``maxima`` is the maximum over SCORES and the sink
//      never joins the running maximum, and read out of the checkpoints 2,680 of
//      V4-Flash's 2,944 sink logits are POSITIVE (91.0%), as are 71.3% of
//      V4.1's. So the offset is positive on ordinary rows, not corner ones, and
//      an earlier version of this block refused every one of them.
//      ot_a3_fp32_transcendental_cr_rne's OP_EXP_NONPOS takes finite x <= 0 and
//      ot_a3_fp32_exp_pos_cr_rne takes x > 0, each correctly rounded and each
//      qualified against the reference's own exp_cr32, so the offset's SIGN
//      selects between them and neither is asked for a value outside its
//      domain. 1/exp(-x) and sigmoid(x)/(1-sigmoid(x)) would both have rounded
//      twice and neither is used.
//   2. A DENOMINATOR THAT IS NOT POSITIVE FINITE. The reference does not refuse
//      this: it FLAGS the query row and re-runs it through an exact oracle
//      (``_repair_rows``). This block has no oracle, so it refuses. A datapath
//      that must match the reference on such a row needs that repair path, and
//      it does not exist in RTL.
//
// One divide per output channel, and ot_a3_fp32_div_rne binary-searches the
// encoding space in 32 cycles without pipelining, so a head of WIDTH channels
// costs WIDTH * 32 cycles here. That is the dominant cost of the closing stage
// and the reason DIVIDERS would be the knob if it needed one.
// ---------------------------------------------------------------------------
module ot_a3_attention_epilogue (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    //: Output channels in this head, the accumulator's own width.
    input  wire [31:0] cfg_width,
    input  wire [31:0] cfg_acc_base,
    input  wire [31:0] cfg_out_base,
    //: The (row, head)'s final running maximum and denominator partial.
    input  wire [31:0] cfg_final_max,
    input  wire [31:0] cfg_final_sums,
    //: The head's attention-sink logit, binary32.
    input  wire [31:0] cfg_sink_code,

    output reg         acc_rd_en,
    output reg  [31:0] acc_rd_addr,
    input  wire [31:0] acc_rd_data,

    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    //: Both recorded by the reference alongside the output row.
    output reg  [31:0] sink_exp,
    output reg  [31:0] final_denominator,
    output reg  [31:0] out_count,
    output reg  [31:0] saturation_count
);
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE = ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_ACCUMULATE_RANGE = ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_SCALE_RANGE = ot_a3_engine_pkg::ERR_SCALE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    localparam OP_EXP_NONPOS = 1'b0;

    localparam [3:0] S_IDLE    = 4'd0;
    localparam [3:0] S_OFFSET  = 4'd1;
    localparam [3:0] S_SINK    = 4'd2;
    localparam [3:0] S_DENOM   = 4'd3;
    localparam [3:0] S_CHECK   = 4'd4;
    localparam [3:0] S_READ    = 4'd5;
    localparam [3:0] S_DIV     = 4'd6;
    localparam [3:0] S_WRITE   = 4'd7;
    localparam [3:0] S_DONE    = 4'd8;
    reg [3:0] state;

    reg [31:0] channel;
    reg [31:0] offset_q;
    reg [31:0] numerator_q;
    reg        sub_pending;
    reg        div_pending;
    //: THE REGISTERED READ ANSWERS TWO EDGES AFTER THE ADDRESS, NOT ONE. The
    //: address is latched at edge N and is on the bus during cycle N; the memory
    //: captures at edge N+1, so the datum is valid DURING cycle N+1 and readable
    //: at edge N+2. Capturing at N+1 takes the PREVIOUS channel's value, which
    //: is the off-by-one this loop was first written with -- every channel right
    //: and every one attached to its neighbour.
    reg [1:0]  rd_phase;

    // -- one subtractor, and one adder, both the same qualified unit ---------
    reg         add_valid_in;
    reg  [31:0] add_a, add_b;
    reg         add_negate_b;
    wire [31:0] add_y;
    wire [1:0]  add_err;
    wire        add_valid_out;
    ot_fp32_add_rne_pipe addsub (
        .clk(clk), .rst_n(rst_n), .valid_in(add_valid_in),
        .a(add_a),
        .b(add_negate_b ? {~add_b[31], add_b[30:0]} : add_b),
        .y(add_y), .err(add_err), .valid_out(add_valid_out)
    );

    //: TWO EXPONENTIALS, SELECTED BY THE OFFSET'S SIGN. Each is correctly
    //: rounded on its own domain and each is qualified against exp_cr32; asking
    //: either for a value outside its domain is what the select prevents.
    reg         exp_in_valid;
    reg  [31:0] exp_argument;

    wire        neg_in_ready, neg_out_valid;
    wire [31:0] neg_result;
    wire [1:0]  neg_error;
    ot_a3_fp32_transcendental_cr_rne exponential_nonpos (
        .clk(clk), .rst_n(rst_n),
        .in_valid(exp_in_valid & ~offset_positive), .in_ready(neg_in_ready),
        .operation(OP_EXP_NONPOS), .argument_code(exp_argument),
        .out_valid(neg_out_valid), .out_ready(state == S_SINK),
        .result_code(neg_result), .result_error(neg_error)
    );

    wire        pos_in_ready, pos_out_valid;
    wire [31:0] pos_result;
    wire [1:0]  pos_error;
    ot_a3_fp32_exp_pos_cr_rne exponential_pos (
        .clk(clk), .rst_n(rst_n),
        .in_valid(exp_in_valid & offset_positive), .in_ready(pos_in_ready),
        .argument_code(exp_argument),
        .out_valid(pos_out_valid), .out_ready(state == S_SINK),
        .result_code(pos_result), .result_error(pos_error)
    );

    wire        exp_in_ready  = offset_positive ? pos_in_ready  : neg_in_ready;
    wire        exp_out_valid = offset_positive ? pos_out_valid : neg_out_valid;
    wire [31:0] exp_result    = offset_positive ? pos_result    : neg_result;
    wire [1:0]  exp_error     = offset_positive ? pos_error     : neg_error;

    reg         div_in_valid;
    wire        div_in_ready;
    wire        div_out_valid;
    wire [31:0] div_result;
    wire [1:0]  div_error;
    ot_a3_fp32_div_rne divider (
        .clk(clk), .rst_n(rst_n),
        .in_valid(div_in_valid), .in_ready(div_in_ready),
        .numerator_code(numerator_q), .denominator_code(final_denominator),
        .out_valid(div_out_valid), .out_ready(state == S_DIV),
        .result_code(div_result), .result_error(div_error)
    );

    //: The narrowing, verified identical to the reference's own _narrow.
    wire [18:0] narrowed = ot_fp32_rne_pkg::fp32_to_bf16_rne(div_result);

    //: A sink ABOVE the maximum gives a positive offset, which OP_EXP_NONPOS
    //: refuses. Detected on the offset rather than on the operands so the
    //: refusal names the real condition.
    wire offset_positive = !offset_q[31] && (offset_q[30:0] != 31'd0);
    wire denom_bad = final_denominator[31] || (final_denominator[30:0] == 31'd0) ||
                     (final_denominator[30:23] == 8'hff);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            channel <= 32'd0; offset_q <= 32'd0; numerator_q <= 32'd0;
            sub_pending <= 1'b0; div_pending <= 1'b0; rd_phase <= 2'd0;
            acc_rd_en <= 1'b0; acc_rd_addr <= 32'd0;
            out_we <= 1'b0; out_addr <= 32'd0; out_data <= 32'd0;
            busy <= 1'b0; done <= 1'b0; error_code <= ERR_NONE;
            sink_exp <= 32'd0; final_denominator <= 32'd0;
            out_count <= 32'd0; saturation_count <= 32'd0;
            add_valid_in <= 1'b0; add_a <= 32'd0; add_b <= 32'd0;
            add_negate_b <= 1'b0;
            exp_in_valid <= 1'b0; exp_argument <= 32'd0;
            div_in_valid <= 1'b0;
        end else begin
            add_valid_in <= 1'b0;
            exp_in_valid <= 1'b0;
            div_in_valid <= 1'b0;
            acc_rd_en <= 1'b0;
            out_we <= 1'b0;
            done <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (start) begin
                        channel <= 32'd0;
                        out_count <= 32'd0; saturation_count <= 32'd0;
                        sub_pending <= 1'b0; div_pending <= 1'b0;
                        rd_phase <= 2'd0;
                        error_code <= ERR_NONE;
                        if (cfg_width == 32'd0) begin
                            error_code <= ERR_SHAPE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else if ((cfg_final_max[30:23] == 8'hff) ||
                                     (cfg_final_sums[30:23] == 8'hff) ||
                                     (cfg_sink_code[30:23] == 8'hff)) begin
                            error_code <= ERR_OPERAND_NONFINITE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            busy <= 1'b1;
                            state <= S_OFFSET;
                        end
                    end
                end

                //: offset = sink - maxima
                S_OFFSET: begin
                    if (!sub_pending) begin
                        add_valid_in <= 1'b1;
                        add_a <= cfg_sink_code;
                        add_b <= cfg_final_max;
                        add_negate_b <= 1'b1;
                        sub_pending <= 1'b1;
                    end else if (add_valid_out) begin
                        sub_pending <= 1'b0;
                        if (add_err != 2'd0) begin
                            error_code <= ERR_OPERAND_NONFINITE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            offset_q <= add_y;
                            state <= S_SINK;
                        end
                    end
                end

                S_SINK: begin
                    if (exp_out_valid) begin
                        if (exp_error != 2'd0) begin
                            error_code <= ERR_SCALE_RANGE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            sink_exp <= exp_result;
                            state <= S_DENOM;
                        end
                    end else if (exp_in_ready && !exp_in_valid) begin
                        exp_in_valid <= 1'b1;
                        exp_argument <= offset_q;
                    end
                end

                //: final_denominator = sums + sink_exp
                S_DENOM: begin
                    if (!sub_pending) begin
                        add_valid_in <= 1'b1;
                        add_a <= cfg_final_sums;
                        add_b <= sink_exp;
                        add_negate_b <= 1'b0;
                        sub_pending <= 1'b1;
                    end else if (add_valid_out) begin
                        sub_pending <= 1'b0;
                        if (add_err != 2'd0) begin
                            error_code <= ERR_ACCUMULATE_RANGE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            final_denominator <= add_y;
                            state <= S_CHECK;
                        end
                    end
                end

                S_CHECK: begin
                    if (denom_bad) begin
                        //: The reference FLAGS the row and repairs it through an
                        //: exact oracle. There is no oracle here, so it refuses.
                        error_code <= ERR_ACCUMULATE_RANGE;
                        busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                    end else begin
                        state <= S_READ;
                    end
                end

                S_READ: begin
                    if (channel >= cfg_width) begin
                        busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                    end else if (rd_phase == 2'd0) begin
                        acc_rd_en <= 1'b1;
                        acc_rd_addr <= cfg_acc_base + channel;
                        rd_phase <= 2'd1;
                    end else if (rd_phase == 2'd1) begin
                        //: One edge for the memory to capture the address.
                        rd_phase <= 2'd2;
                    end else begin
                        numerator_q <= acc_rd_data;
                        rd_phase <= 2'd0;
                        state <= S_DIV;
                    end
                end

                S_DIV: begin
                    if (!div_pending) begin
                        if (div_in_ready) begin
                            div_in_valid <= 1'b1;
                            div_pending <= 1'b1;
                        end
                    end else if (div_out_valid) begin
                        div_pending <= 1'b0;
                        if (div_error != 2'd0) begin
                            error_code <= ERR_ACCUMULATE_RANGE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else if (narrowed[18:17] != 2'd0) begin
                            error_code <= ERR_OPERAND_NONFINITE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            out_we <= 1'b1;
                            out_addr <= cfg_out_base + channel;
                            out_data <= {16'h0000, narrowed[15:0]};
                            out_count <= out_count + 32'd1;
                            if (narrowed[16])
                                saturation_count <= saturation_count + 32'd1;
                            channel <= channel + 32'd1;
                            state <= S_READ;
                        end
                    end
                end

                S_DONE: begin
                    busy <= 1'b0; state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
