`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 bounded loop stack.
//
// Implements CONTROL.LOOP_SETUP and CONTROL.LOOP_NEXT against the LOOP_CONTROL
// descriptor payload (runtime/abi3/descriptors.py LOOP_CONTROL_PAYLOAD) with
// the trip arithmetic of runtime/sim/device.Device._loop_trip:
//
//   constant-bounded:  span = upper_bound - lower_bound
//   symbol-bounded:    bound = ceil(symbol / max(bound_divisor, 1))
//                      span  = bound - lower_bound
//   trip = max(ceil(span / step), 0)
//
// and the three outcomes the golden model distinguishes:
//   * trip > max_iterations              -> trap class 4 (capability/resource)
//   * trip == 0                          -> skip to body_end + 1, no push
//   * otherwise                          -> push and enter the body
//
// The two ceiling divisions use one shared restoring divider rather than a
// synthesized "/" so the block has a bounded, data-independent cost and no
// combinational divider in the control path.  Depth is a capability field, not
// an ABI field: four matches the capability the frozen fixture declares.
//
// A LOOP_NEXT that names a loop other than the innermost open one is rejected
// here (trap class 5).  The golden model uses the innermost open loop and
// ignores the instruction's control ID, which is safe only because the
// verifier proves they agree; this block does not rely on that proof.
// ---------------------------------------------------------------------------
module ot_a3_loop_stack
    import ot_a3_pkg::*;
#(
    parameter integer DEPTH = A3_LOOP_DEPTH
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        clear,

    input  wire        setup_valid,
    input  wire        next_valid,
    input  wire [31:0] op_pc,
    input  wire [31:0] op_loop_id,

    // LOOP_CONTROL payload fields, presented with setup_valid
    input  wire [7:0]  setup_bound_kind,
    input  wire [31:0] setup_lower,
    input  wire [31:0] setup_upper,
    input  wire [31:0] setup_step,
    input  wire [31:0] setup_max_iterations,
    input  wire [31:0] setup_body_start,
    input  wire [31:0] setup_body_end,
    input  wire [31:0] setup_bound_divisor,
    input  wire [31:0] setup_symbol_value,
    input  wire        setup_symbol_bound,

    output reg         busy,
    output reg         done,
    output reg         trap_valid,
    output reg  [15:0] trap_class,
    output reg  [31:0] next_pc,
    output reg  [1:0]  action,          // 0 push, 1 skip, 2 iterate, 3 exit

    input  wire [31:0] query_id,
    output wire        query_active,
    output wire [31:0] query_value,
    output wire [31:0] query_trip,

    output reg  [31:0] iteration_count,
    output wire [3:0]  depth
);
    localparam [1:0] ACTION_PUSH    = 2'd0;
    localparam [1:0] ACTION_SKIP    = 2'd1;
    localparam [1:0] ACTION_ITERATE = 2'd2;
    localparam [1:0] ACTION_EXIT    = 2'd3;

    localparam [2:0] S_IDLE   = 3'd0;
    localparam [2:0] S_BOUND  = 3'd1;
    localparam [2:0] S_SPAN   = 3'd2;
    localparam [2:0] S_TRIP   = 3'd3;
    localparam [2:0] S_CHECK  = 3'd4;

    reg [31:0] loop_id     [0:DEPTH-1];
    reg [31:0] loop_trip   [0:DEPTH-1];
    reg [31:0] loop_value  [0:DEPTH-1];
    reg [31:0] loop_index  [0:DEPTH-1];
    reg [31:0] loop_step   [0:DEPTH-1];
    reg [31:0] loop_start  [0:DEPTH-1];
    reg [3:0]  stack_pointer;

    reg [2:0]  state;
    reg [31:0] hold_lower;
    reg [31:0] hold_upper;
    reg [31:0] hold_step;
    reg [31:0] hold_max;
    reg [31:0] hold_body_start;
    reg [31:0] hold_body_end;
    reg [31:0] hold_loop_id;
    reg [31:0] hold_pc;
    reg [7:0]  hold_kind;
    reg [31:0] hold_bound;
    reg [31:0] hold_trip;
    reg        hold_zero_span;

    // -- shared restoring divider: quotient = floor(numerator / divisor) ----
    reg         div_start;
    reg  [33:0] div_numerator;
    reg  [31:0] div_divisor;
    reg  [33:0] div_shift;
    reg  [33:0] div_remainder;
    reg  [33:0] div_quotient;
    reg  [5:0]  div_count;
    reg         div_busy;
    reg         div_done;
    wire [33:0] div_trial = {div_remainder[32:0], div_shift[33]};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            div_busy <= 1'b0;
            div_done <= 1'b0;
            div_shift <= 34'd0;
            div_remainder <= 34'd0;
            div_quotient <= 34'd0;
            div_count <= 6'd0;
        end else begin
            div_done <= 1'b0;
            if (div_start) begin
                div_busy <= 1'b1;
                div_shift <= div_numerator;
                div_remainder <= 34'd0;
                div_quotient <= 34'd0;
                div_count <= 6'd34;
            end else if (div_busy) begin
                if (div_trial >= {2'b00, div_divisor}) begin
                    div_remainder <= div_trial - {2'b00, div_divisor};
                    div_quotient <= {div_quotient[32:0], 1'b1};
                end else begin
                    div_remainder <= div_trial;
                    div_quotient <= {div_quotient[32:0], 1'b0};
                end
                div_shift <= {div_shift[32:0], 1'b0};
                div_count <= div_count - 6'd1;
                if (div_count == 6'd1) begin
                    div_busy <= 1'b0;
                    div_done <= 1'b1;
                end
            end
        end
    end

    // -- combinational queries ---------------------------------------------
    reg        query_hit;
    reg [31:0] query_hit_value;
    reg [31:0] query_hit_trip;
    integer    q;
    always @* begin
        query_hit = 1'b0;
        query_hit_value = 32'd0;
        query_hit_trip = 32'd0;
        for (q = 0; q < DEPTH; q = q + 1) begin
            if ((q < stack_pointer) && (loop_id[q] == query_id)) begin
                query_hit = 1'b1;
                query_hit_value = loop_value[q];
                query_hit_trip = loop_trip[q];
            end
        end
    end
    assign query_active = query_hit;
    assign query_value = query_hit_value;
    assign query_trip = query_hit_trip;
    assign depth = stack_pointer;

    wire signed [32:0] constant_span =
        $signed({1'b0, hold_upper}) - $signed({1'b0, hold_lower});
    wire signed [32:0] symbol_span =
        $signed({1'b0, hold_bound}) - $signed({1'b0, hold_lower});
    wire signed [32:0] span_value =
        (hold_kind == A3_SELECTOR_CONSTANT) ? constant_span : symbol_span;

    wire [3:0] top = (stack_pointer == 4'd0) ? 4'd0 : (stack_pointer - 4'd1);
    wire [31:0] top_next_index = loop_index[top] + 32'd1;

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            trap_valid <= 1'b0;
            trap_class <= A3_TRAP_NONE;
            next_pc <= 32'd0;
            action <= ACTION_PUSH;
            stack_pointer <= 4'd0;
            iteration_count <= 32'd0;
            div_start <= 1'b0;
            div_numerator <= 34'd0;
            div_divisor <= 32'd1;
            hold_lower <= 32'd0;
            hold_upper <= 32'd0;
            hold_step <= 32'd1;
            hold_max <= 32'd0;
            hold_body_start <= 32'd0;
            hold_body_end <= 32'd0;
            hold_loop_id <= A3_NO_ID;
            hold_pc <= 32'd0;
            hold_kind <= A3_SELECTOR_CONSTANT;
            hold_bound <= 32'd0;
            hold_trip <= 32'd0;
            hold_zero_span <= 1'b0;
            for (i = 0; i < DEPTH; i = i + 1) begin
                loop_id[i] <= A3_NO_ID;
                loop_trip[i] <= 32'd0;
                loop_value[i] <= 32'd0;
                loop_index[i] <= 32'd0;
                loop_step[i] <= 32'd1;
                loop_start[i] <= 32'd0;
            end
        end else begin
            done <= 1'b0;
            trap_valid <= 1'b0;
            div_start <= 1'b0;

            if (clear) begin
                state <= S_IDLE;
                busy <= 1'b0;
                stack_pointer <= 4'd0;
                iteration_count <= 32'd0;
            end else begin
                case (state)
                    S_IDLE: begin
                        if (setup_valid) begin
                            busy <= 1'b1;
                            hold_lower <= setup_lower;
                            hold_upper <= setup_upper;
                            hold_step <= setup_step;
                            hold_max <= setup_max_iterations;
                            hold_body_start <= setup_body_start;
                            hold_body_end <= setup_body_end;
                            hold_loop_id <= op_loop_id;
                            hold_pc <= op_pc;
                            hold_kind <= setup_bound_kind;
                            if (setup_bound_kind == A3_SELECTOR_CONSTANT) begin
                                state <= S_SPAN;
                            end else if (!setup_symbol_bound) begin
                                // Loop bound names a symbol this request did
                                // not bind: descriptor/address fault.
                                busy <= 1'b0;
                                done <= 1'b1;
                                trap_valid <= 1'b1;
                                trap_class <= A3_TRAP_DESCRIPTOR;
                            end else begin
                                div_start <= 1'b1;
                                div_divisor <= (setup_bound_divisor == 32'd0)
                                             ? 32'd1 : setup_bound_divisor;
                                div_numerator <= {2'b00, setup_symbol_value} +
                                                 {2'b00, (setup_bound_divisor == 32'd0)
                                                       ? 32'd1 : setup_bound_divisor} -
                                                 34'd1;
                                state <= S_BOUND;
                            end
                        end else if (next_valid) begin
                            iteration_count <= iteration_count + 32'd1;
                            busy <= 1'b0;
                            done <= 1'b1;
                            if (stack_pointer == 4'd0) begin
                                trap_valid <= 1'b1;
                                trap_class <= A3_TRAP_ILLEGAL;
                                iteration_count <= iteration_count;
                            end else if (loop_id[top] != op_loop_id) begin
                                trap_valid <= 1'b1;
                                trap_class <= A3_TRAP_ILLEGAL;
                                iteration_count <= iteration_count;
                            end else if (top_next_index < loop_trip[top]) begin
                                loop_index[top] <= top_next_index;
                                loop_value[top] <= loop_value[top] + loop_step[top];
                                next_pc <= loop_start[top];
                                action <= ACTION_ITERATE;
                            end else begin
                                stack_pointer <= stack_pointer - 4'd1;
                                next_pc <= op_pc + 32'd1;
                                action <= ACTION_EXIT;
                            end
                        end
                    end
                    S_BOUND: begin
                        if (div_done) begin
                            hold_bound <= div_quotient[31:0];
                            state <= S_SPAN;
                        end
                    end
                    S_SPAN: begin
                        if (span_value <= 33'sd0) begin
                            hold_trip <= 32'd0;
                            hold_zero_span <= 1'b1;
                            state <= S_CHECK;
                        end else if (hold_step == 32'd0) begin
                            // The verifier rejects a zero step; the golden
                            // model would divide by zero.  Fail closed.
                            busy <= 1'b0;
                            done <= 1'b1;
                            trap_valid <= 1'b1;
                            trap_class <= A3_TRAP_INTERNAL;
                            state <= S_IDLE;
                        end else begin
                            hold_zero_span <= 1'b0;
                            div_start <= 1'b1;
                            div_divisor <= hold_step;
                            div_numerator <= {1'b0, span_value} +
                                             {2'b00, hold_step} - 34'd1;
                            state <= S_TRIP;
                        end
                    end
                    S_TRIP: begin
                        if (div_done) begin
                            hold_trip <= div_quotient[31:0];
                            state <= S_CHECK;
                        end
                    end
                    S_CHECK: begin
                        busy <= 1'b0;
                        done <= 1'b1;
                        state <= S_IDLE;
                        if (hold_trip > hold_max) begin
                            trap_valid <= 1'b1;
                            trap_class <= A3_TRAP_CAPABILITY;
                        end else if (hold_trip == 32'd0) begin
                            next_pc <= hold_body_end + 32'd1;
                            action <= ACTION_SKIP;
                        end else if (stack_pointer >= DEPTH) begin
                            trap_valid <= 1'b1;
                            trap_class <= A3_TRAP_CAPABILITY;
                        end else begin
                            loop_id[stack_pointer] <= hold_loop_id;
                            loop_trip[stack_pointer] <= hold_trip;
                            loop_value[stack_pointer] <= hold_lower;
                            loop_index[stack_pointer] <= 32'd0;
                            loop_step[stack_pointer] <= hold_step;
                            loop_start[stack_pointer] <= hold_body_start;
                            stack_pointer <= stack_pointer + 4'd1;
                            next_pc <= hold_pc + 32'd1;
                            action <= ACTION_PUSH;
                        end
                    end
                    default: state <= S_IDLE;
                endcase
            end
        end
    end
endmodule
