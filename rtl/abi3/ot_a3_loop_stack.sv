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
// The two ceiling divisions go to the front end's one shared divider
// (ot_a3_shared_divider, requester 0; docs/CHIP_ARCHITECTURE_DESIGN.md
// section 3.5) rather than a synthesized "/" or a private unit, so the block
// has a bounded, data-independent cost and no combinational divider in the
// control path.  Depth is a capability field, not an ABI field: four matches
// the capability the frozen fixture declares.
//
// The bound symbol arrives as the 64-bit value of the symbol file (section
// 3.3).  The trip arithmetic is 32-bit, as the golden model's loop_trip_count
// is on every shipped binding: a symbol-bounded loop whose bound value does
// not fit 32 bits traps 4 at LOOP_SETUP (STRICTER: an implementation bound
// recorded here, never reached by an admitted program).
//
// Seven combinational query ports (QUERY_PORTS), flat: port 0 serves the
// predicate unit, ports 1..6 the six view-resolver lanes, so the lanes
// resolve one instruction's views concurrently without arbitration.
//
// A LOOP_NEXT that names a loop other than the innermost open one is rejected
// here (trap class 5).  The golden model uses the innermost open loop and
// ignores the instruction's control ID, which is safe only because the
// verifier proves they agree; this block does not rely on that proof.
//
// Amendment A13 (wire format section 12.4) needs three of the LOOP_CONTROL
// payload fields at *view resolution* time, not at setup time: the bound
// selector kind, the bound divisor and the value of the bound symbol.  They are
// cached per open loop here and published on the query port, so a view resolver
// never re-reads the loop descriptor and the two never disagree about which
// loop a partial extent belongs to.  A request symbol is bound for the whole
// transaction (runtime/sim/device.Device.run_transaction copies it once and
// never rewrites it), so the cached value is exact for every iteration.
// ---------------------------------------------------------------------------
module ot_a3_loop_stack
    // The package is referenced by scope rather than wildcard-imported: a
    // wildcard import is not accepted by every open synthesis front end this
    // program pins, and a block that only elaborates in a simulator is not an
    // implementable block.  [OI-43] docs/UNIFIED_EXECUTION_CHECKLIST.md
#(
    parameter integer DEPTH = ot_a3_pkg::A3_LOOP_DEPTH,
    parameter integer QUERY_PORTS = 7
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
    input  wire [63:0] setup_symbol_value,
    input  wire        setup_symbol_bound,

    output reg         busy,
    output reg         done,
    output reg         trap_valid,
    output reg  [15:0] trap_class,
    output reg  [31:0] next_pc,
    output reg  [1:0]  action,          // 0 push, 1 skip, 2 iterate, 3 exit

    // shared divider (requester 0 of ot_a3_shared_divider)
    output reg         div_req,
    output reg  [63:0] div_num,
    output reg  [31:0] div_den,
    input  wire        div_done,
    input  wire [63:0] div_quot,

    input  wire [QUERY_PORTS*32-1:0] query_id,
    output wire [QUERY_PORTS-1:0]    query_active,
    output wire [QUERY_PORTS*32-1:0] query_value,
    output wire [QUERY_PORTS*32-1:0] query_trip,
    // Amendment A13 operands, cached at LOOP_SETUP (see the header note).
    output wire [QUERY_PORTS-1:0]    query_symbol_bounded,
    output wire [QUERY_PORTS*32-1:0] query_divisor,
    output wire [QUERY_PORTS*32-1:0] query_bound_value,

    output reg  [31:0] iteration_count,
    output wire [3:0]  depth
);
    //: Set +OT_LOOP_TRACE=1 to report loop setup outcomes.
    reg trace_loops = 1'b0;
`ifndef YOSYS
    // Yosys 0.68 has no $test$plusargs and refuses the whole file on it, so
    // the simulation-only plusarg probe is hidden from synthesis; trace_loops
    // keeps its 1'b0 initialiser there and every trace branch folds away.
    initial if ($test$plusargs("OT_LOOP_TRACE")) trace_loops = 1'b1;
`endif

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
    reg        loop_symbolic [0:DEPTH-1];  // A13: bound kind is RUNTIME_SYMBOL
    reg [31:0] loop_divisor  [0:DEPTH-1];  // A13: max(bound_divisor, 1)
    reg [31:0] loop_bound    [0:DEPTH-1];  // A13: the bound symbol's value
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
    reg        hold_symbolic;
    reg [31:0] hold_divisor;
    reg [31:0] hold_symbol_value;

    // -- combinational queries ---------------------------------------------
    genvar gq;
    generate
        for (gq = 0; gq < QUERY_PORTS; gq = gq + 1) begin : g_query
            reg        hit;
            reg [31:0] hit_value;
            reg [31:0] hit_trip;
            reg        hit_symbolic;
            reg [31:0] hit_divisor;
            reg [31:0] hit_bound;
            integer    q;
            always @* begin
                hit = 1'b0;
                hit_value = 32'd0;
                hit_trip = 32'd0;
                hit_symbolic = 1'b0;
                hit_divisor = 32'd1;
                hit_bound = 32'd0;
                for (q = 0; q < DEPTH; q = q + 1) begin
                    if ((q < stack_pointer) &&
                        (loop_id[q] == query_id[gq*32 +: 32])) begin
                        hit = 1'b1;
                        hit_value = loop_value[q];
                        hit_trip = loop_trip[q];
                        hit_symbolic = loop_symbolic[q];
                        hit_divisor = loop_divisor[q];
                        hit_bound = loop_bound[q];
                    end
                end
            end
            assign query_active[gq] = hit;
            assign query_value[gq*32 +: 32] = hit_value;
            assign query_trip[gq*32 +: 32] = hit_trip;
            assign query_symbol_bounded[gq] = hit_symbolic;
            assign query_divisor[gq*32 +: 32] = hit_divisor;
            assign query_bound_value[gq*32 +: 32] = hit_bound;
        end
    endgenerate
    assign depth = stack_pointer;

    wire signed [32:0] constant_span =
        $signed({1'b0, hold_upper}) - $signed({1'b0, hold_lower});
    wire signed [32:0] symbol_span =
        $signed({1'b0, hold_bound}) - $signed({1'b0, hold_lower});
    wire signed [32:0] span_value =
        (hold_kind == ot_a3_pkg::A3_SELECTOR_CONSTANT) ? constant_span : symbol_span;

    wire [3:0] top = (stack_pointer == 4'd0) ? 4'd0 : (stack_pointer - 4'd1);
    wire [31:0] top_next_index = loop_index[top] + 32'd1;

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            trap_valid <= 1'b0;
            trap_class <= ot_a3_pkg::A3_TRAP_NONE;
            next_pc <= 32'd0;
            action <= ACTION_PUSH;
            stack_pointer <= 4'd0;
            iteration_count <= 32'd0;
            div_req <= 1'b0;
            div_num <= 64'd0;
            div_den <= 32'd1;
            hold_lower <= 32'd0;
            hold_upper <= 32'd0;
            hold_step <= 32'd1;
            hold_max <= 32'd0;
            hold_body_start <= 32'd0;
            hold_body_end <= 32'd0;
            hold_loop_id <= ot_a3_pkg::A3_NO_ID;
            hold_pc <= 32'd0;
            hold_kind <= ot_a3_pkg::A3_SELECTOR_CONSTANT;
            hold_bound <= 32'd0;
            hold_trip <= 32'd0;
            hold_symbolic <= 1'b0;
            hold_divisor <= 32'd1;
            hold_symbol_value <= 32'd0;
            for (i = 0; i < DEPTH; i = i + 1) begin
                loop_id[i] <= ot_a3_pkg::A3_NO_ID;
                loop_trip[i] <= 32'd0;
                loop_value[i] <= 32'd0;
                loop_index[i] <= 32'd0;
                loop_step[i] <= 32'd1;
                loop_start[i] <= 32'd0;
                loop_symbolic[i] <= 1'b0;
                loop_divisor[i] <= 32'd1;
                loop_bound[i] <= 32'd0;
            end
        end else begin
            done <= 1'b0;
            trap_valid <= 1'b0;

            if (clear) begin
                state <= S_IDLE;
                busy <= 1'b0;
                div_req <= 1'b0;
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
                            // A13 operands.  ``_remaining_rows`` bounds only a
                            // loop whose bound selector is a runtime symbol
                            // that this request actually bound, and reads the
                            // divisor as max(bound_divisor, 1).
                            hold_symbolic <= (setup_bound_kind ==
                                              ot_a3_pkg::A3_SELECTOR_RUNTIME_SYMBOL) &&
                                             setup_symbol_bound;
                            hold_divisor <= (setup_bound_divisor == 32'd0)
                                          ? 32'd1 : setup_bound_divisor;
                            hold_symbol_value <= setup_symbol_value[31:0];
                            if (setup_bound_kind == ot_a3_pkg::A3_SELECTOR_CONSTANT) begin
                                state <= S_SPAN;
                            end else if (!setup_symbol_bound) begin
                                // Loop bound names a symbol this request did
                                // not bind: descriptor/address fault.
                                busy <= 1'b0;
                                done <= 1'b1;
                                trap_valid <= 1'b1;
                                trap_class <= ot_a3_pkg::A3_TRAP_DESCRIPTOR;
                            end else if (setup_symbol_value[63:32] != 32'd0) begin
                                // STRICTER (implementation bound): a 64-bit
                                // bound above 2^32 is outside the 32-bit trip
                                // arithmetic of loop_trip_count.
                                busy <= 1'b0;
                                done <= 1'b1;
                                trap_valid <= 1'b1;
                                trap_class <= ot_a3_pkg::A3_TRAP_CAPABILITY;
                            end else begin
                                div_req <= 1'b1;
                                div_den <= (setup_bound_divisor == 32'd0)
                                         ? 32'd1 : setup_bound_divisor;
                                div_num <= {32'd0, setup_symbol_value[31:0]} +
                                           {32'd0, (setup_bound_divisor == 32'd0)
                                                 ? 32'd1 : setup_bound_divisor} -
                                           64'd1;
                                state <= S_BOUND;
                            end
                        end else if (next_valid) begin
                            iteration_count <= iteration_count + 32'd1;
                            busy <= 1'b0;
                            done <= 1'b1;
                            if (stack_pointer == 4'd0) begin
                                trap_valid <= 1'b1;
                                trap_class <= ot_a3_pkg::A3_TRAP_ILLEGAL;
                                iteration_count <= iteration_count;
                            end else if (loop_id[top] != op_loop_id) begin
                                trap_valid <= 1'b1;
                                trap_class <= ot_a3_pkg::A3_TRAP_ILLEGAL;
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
                            div_req <= 1'b0;
                            hold_bound <= div_quot[31:0];
                            state <= S_SPAN;
                        end
                    end
                    S_SPAN: begin
                        if (span_value <= 33'sd0) begin
                            hold_trip <= 32'd0;
                            state <= S_CHECK;
                        end else if (hold_step == 32'd0) begin
                            // The verifier rejects a zero step; the golden
                            // model would divide by zero.  Fail closed.
                            busy <= 1'b0;
                            done <= 1'b1;
                            trap_valid <= 1'b1;
                            trap_class <= ot_a3_pkg::A3_TRAP_INTERNAL;
                            state <= S_IDLE;
                        end else begin
                            div_req <= 1'b1;
                            div_den <= hold_step;
                            div_num <= {31'd0, span_value} +
                                       {32'd0, hold_step} - 64'd1;
                            state <= S_TRIP;
                        end
                    end
                    S_TRIP: begin
                        if (div_done) begin
                            div_req <= 1'b0;
                            hold_trip <= div_quot[31:0];
                            state <= S_CHECK;
                        end
                    end
                    S_CHECK: begin
                        busy <= 1'b0;
                        done <= 1'b1;
                        state <= S_IDLE;
                        //: Set +OT_LOOP_TRACE=1 to report each setup's outcome.
`ifndef YOSYS   // simulation-only trace; Yosys carries the $display
                //: text into the mapped netlist, where OpenSTA cannot parse it
                        if (trace_loops)
                            $display("OT_LOOP_SETUP id=%0d trip=%0d max=%0d sp=%0d kind=%0d sym=%0d div=%0d bs=%0d be=%0d",
                                     hold_loop_id, hold_trip, hold_max, stack_pointer,
                                     hold_kind, hold_symbolic, hold_divisor,
                                     hold_body_start, hold_body_end);
`endif
                        if (hold_trip > hold_max) begin
                            trap_valid <= 1'b1;
                            trap_class <= ot_a3_pkg::A3_TRAP_CAPABILITY;
                        end else if (hold_trip == 32'd0) begin
                            next_pc <= hold_body_end + 32'd1;
                            action <= ACTION_SKIP;
                        end else if (stack_pointer >= DEPTH) begin
                            trap_valid <= 1'b1;
                            trap_class <= ot_a3_pkg::A3_TRAP_CAPABILITY;
                        end else begin
                            loop_id[stack_pointer] <= hold_loop_id;
                            loop_trip[stack_pointer] <= hold_trip;
                            loop_value[stack_pointer] <= hold_lower;
                            loop_index[stack_pointer] <= 32'd0;
                            loop_step[stack_pointer] <= hold_step;
                            loop_start[stack_pointer] <= hold_body_start;
                            loop_symbolic[stack_pointer] <= hold_symbolic;
                            loop_divisor[stack_pointer] <= hold_divisor;
                            loop_bound[stack_pointer] <= hold_symbol_value;
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
