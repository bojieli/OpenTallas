`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Bounded VECTOR.HADAMARD datapath.
//
// This is the qualified 128-point transform: seven ascending-stride binary32
// butterfly stages, multiplication by the exact binary32 encoding of
// 1/sqrt(128), and one BF16 RNE conversion.  At most four rows are accepted.
// Input and intermediate values remain in a private buffer until the complete
// operation succeeds, so every refusal leaves the destination untouched.
//
// The butterflies ISSUE ONE PER CYCLE.  They used to take two cycles each with
// the binary32 add combinational, and that add is ~6.4 ns on ASAP7 by itself:
// routing ot_a3_engine_array at a 3.4 ns target put the worst path here, ending
// on this module's own buffer write, and clock-tree repair ground through 500
// iterations at -3.91 ns without moving it.
//
// Replacing the add with the pipelined one alone would have been a wash -- five
// stages of latency for a two-cycle butterfly is 3.5x the cycles to buy 3.3x the
// frequency.  What makes it a real gain is that WITHIN ONE STRIDE the butterflies
// are independent: offset, group_base and row together partition the buffer, so
// no two pairs at a fixed stride touch the same element.  So a pair is issued
// every cycle and only the seven stride boundaries drain, which cuts the cycle
// count as well as lifting the frequency.
//
// The buffer read is registered before the adders see it, so the 512-entry read
// mux and the adder's first stage are in different cycles.  Each pair's two
// indices ride a delay line the same depth as the adders, because the write has
// to land on the pair that produced it and not on whatever the generator has
// reached by then.
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
    //: S_CAPTURE and S_BUTTERFLY were the two-cycle butterfly.  S_SWEEP issues a
    //: pair every cycle instead and S_DRAIN waits for the adders to empty at a
    //: stride boundary, where the next stride reads what this one wrote.
    localparam [3:0] S_SWEEP      = 4'd4;
    localparam [3:0] S_DRAIN      = 4'd5;
    localparam [3:0] S_NORMALIZE  = 4'd6;
    localparam [3:0] S_COMMIT     = 4'd7;
    localparam [3:0] S_DONE       = 4'd8;
    //: The scale-and-narrow pass is pipelined the same way, for the same reason:
    //: it was reading the buffer, multiplying and narrowing in one cycle.
    localparam [3:0] S_NORM_DRAIN = 4'd9;

    //: Both proto pipes are five stages, so a result appears five cycles after
    //: the cycle its operands were presented.
    localparam integer PIPE_LATENCY = 5;

    reg [3:0] state;
    reg [31:0] index;
    reg [15:0] row;
    reg [7:0] stride;
    reg [7:0] group_base;
    reg [7:0] offset;
    reg [31:0] values [0:MAX_ELEMENTS-1];

    //: The read stage: the generator's indices and the two elements they name,
    //: registered so the buffer's read mux is not in the adders' first stage.
    reg [31:0] lower_value;
    reg [31:0] upper_value;
    reg [31:0] issue_lower;
    reg [31:0] issue_upper;
    reg        butterfly_issue;
    reg        normalize_issue;

    //: One in-flight count for both passes; they never overlap, because a stride
    //: boundary and the move to the scale pass both drain to zero first.
    reg [3:0] in_flight;

    //: Each pair's indices, delayed to meet its own result.  The generator is
    //: PIPE_LATENCY pairs further on by then.
    reg [31:0] lower_delay [1:PIPE_LATENCY];
    reg [31:0] upper_delay [1:PIPE_LATENCY];
    integer    delay_step;

    wire [31:0] lower_index = ({16'b0, row} * WIDTH) +
                              {24'b0, group_base} + {24'b0, offset};
    wire [31:0] upper_index = lower_index + {24'b0, stride};
    wire [15:0] next_group = {8'b0, group_base} +
                             ({8'b0, stride} << 1);
    wire [33:0] decoded = ot_a3_format_pkg::decode_bf16(a_rd_data[15:0]);

    //: The sign flip is a register-to-register XOR in front of the adder, and it
    //: keeps the module's own convention rather than IEEE's: negating a zero
    //: yields +0, which is what the combinational form did.
    wire [31:0] negated_upper = (upper_value[30:0] == 0)
                              ? 32'b0 : (upper_value ^ 32'h8000_0000);

    //: rtl/proto/ot_fp32_add_rne_pipe.sv and ot_fp32_mul_rne_pipe.sv are
    //: qualified bit-identical to the ot_fp32_rne_pkg functions they replace,
    //: including where that authority is deliberately not IEEE-754: every zero
    //: result is canonical +0.  So this is a latency change, not a numeric one.
    wire [31:0] sum_y, difference_y, scaled_y;
    wire [1:0]  sum_err, difference_err, scaled_err;
    wire        sum_done, difference_done, scaled_done;

    ot_fp32_add_rne_pipe adder_sum (
        .clk(clk), .rst_n(rst_n), .valid_in(butterfly_issue),
        .a(lower_value), .b(upper_value),
        .y(sum_y), .err(sum_err), .valid_out(sum_done)
    );
    ot_fp32_add_rne_pipe adder_difference (
        .clk(clk), .rst_n(rst_n), .valid_in(butterfly_issue),
        .a(lower_value), .b(negated_upper),
        .y(difference_y), .err(difference_err), .valid_out(difference_done)
    );
    ot_fp32_mul_rne_pipe scaler (
        .clk(clk), .rst_n(rst_n), .valid_in(normalize_issue),
        .a(lower_value), .b(HADAMARD_SCALE),
        .y(scaled_y), .err(scaled_err), .valid_out(scaled_done)
    );

    //: The narrowing reads the multiplier's registered output, so it has its own
    //: cycle rather than sharing the multiply's cone.
    wire [18:0] narrowed =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(scaled_y);

    //: A pair enters the read stage on every cycle either sweep is running.
    wire sweeping_butterfly = (state == S_SWEEP);
    wire sweeping_normalize = (state == S_NORMALIZE);

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
            issue_lower <= 0;
            issue_upper <= 0;
            butterfly_issue <= 1'b0;
            normalize_issue <= 1'b0;
            in_flight <= 0;
            for (delay_step = 1; delay_step <= PIPE_LATENCY;
                 delay_step = delay_step + 1) begin
                lower_delay[delay_step] <= 0;
                upper_delay[delay_step] <= 0;
            end
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
            //: An issue is one cycle wide; the sweep states re-assert it.
            butterfly_issue <= 1'b0;
            normalize_issue <= 1'b0;

            //: The index delay line advances every cycle, exactly as the pipes
            //: advance their own valid, so entry N always holds the indices of
            //: the pair whose result is N cycles from appearing.
            lower_delay[1] <= issue_lower;
            upper_delay[1] <= issue_upper;
            for (delay_step = 2; delay_step <= PIPE_LATENCY;
                 delay_step = delay_step + 1) begin
                lower_delay[delay_step] <= lower_delay[delay_step - 1];
                upper_delay[delay_step] <= upper_delay[delay_step - 1];
            end

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
                        in_flight <= 0;
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
                            state <= S_SWEEP;
                        end else begin
                            index <= index + 1;
                            state <= S_LOAD_ISSUE;
                        end
                        in_flight <= 0;
                    end
                end

                //: One pair per cycle: read the two elements the generator
                //: names into the issue registers, and advance the generator.
                //: The walk order is unchanged -- offset inside group_base
                //: inside row inside stride -- so pairs are issued in exactly
                //: the order the two-cycle form computed them, and a refusal
                //: still reports the first pair that overflows.
                S_SWEEP: begin
                    issue_lower <= lower_index;
                    issue_upper <= upper_index;
                    lower_value <= values[lower_index];
                    upper_value <= values[upper_index];
                    butterfly_issue <= 1'b1;

                    if (offset + 1 < stride) begin
                        offset <= offset + 1;
                    end else if (next_group < WIDTH) begin
                        offset <= 0;
                        group_base <= next_group[7:0];
                    end else if (row + 1 < cfg_rows) begin
                        offset <= 0;
                        group_base <= 0;
                        row <= row + 1;
                    end else begin
                        //: This stride is fully issued.  The next one reads what
                        //: this one writes, so it cannot start until the adders
                        //: have emptied.
                        offset <= 0;
                        group_base <= 0;
                        row <= 0;
                        state <= S_DRAIN;
                    end
                end

                S_DRAIN: begin
                    if (in_flight == 0) begin
                        if (stride < 64) begin
                            stride <= stride << 1;
                            state <= S_SWEEP;
                        end else begin
                            index <= 0;
                            state <= S_NORMALIZE;
                        end
                    end
                end

                //: The scale pass, one element per cycle.  It reads through the
                //: same issue register the butterflies use, because the two
                //: passes never overlap.
                S_NORMALIZE: begin
                    issue_lower <= index;
                    lower_value <= values[index];
                    normalize_issue <= 1'b1;
                    if (index + 1 == cfg_count) begin
                        state <= S_NORM_DRAIN;
                    end else begin
                        index <= index + 1;
                    end
                end

                S_NORM_DRAIN: begin
                    if (in_flight == 0) begin
                        index <= 0;
                        state <= S_COMMIT;
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
                    in_flight <= 0;
                    state <= S_IDLE;
                end

                default: begin
                    error_code <= ERR_SHAPE;
                    state <= S_DONE;
                end
            endcase

            //: RETIREMENT, after the case so that a refusal here overrides the
            //: transition the sweep just chose.  Results appear in issue order,
            //: so the pair reported is the first that overflows, as before; the
            //: pairs still in the pipes never write, exactly as the two-cycle
            //: form never computed the butterflies after a refusal.  The state
            //: guards also stop a result that appears after an abort from
            //: reaching the buffer.
            if ((state == S_SWEEP) || (state == S_DRAIN)) begin
                in_flight <= in_flight + (sweeping_butterfly ? 4'd1 : 4'd0)
                                       - (sum_done ? 4'd1 : 4'd0);
                if (sum_done) begin
                    if ((sum_err != 2'd0) || (difference_err != 2'd0)) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        values[lower_delay[PIPE_LATENCY]] <= sum_y;
                        values[upper_delay[PIPE_LATENCY]] <= difference_y;
                    end
                end
            end

            if ((state == S_NORMALIZE) || (state == S_NORM_DRAIN)) begin
                in_flight <= in_flight + (sweeping_normalize ? 4'd1 : 4'd0)
                                       - (scaled_done ? 4'd1 : 4'd0);
                if (scaled_done) begin
                    // Saturation is a refusal for the qualified transform,
                    // unlike generic BF16 storage conversion.
                    if ((scaled_err != 2'd0) ||
                        (narrowed[18:17] != 0) || narrowed[16]) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        values[lower_delay[PIPE_LATENCY]] <=
                            {16'b0, narrowed[15:0]};
                    end
                end
            end
        end
    end
endmodule
