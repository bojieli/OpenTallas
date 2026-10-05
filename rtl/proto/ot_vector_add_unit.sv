`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Vector add unit: LANES pipelined BF16 adders under one issue port.
//
// This is the vector pipe of a compute unit, built the way a GPU builds one. The
// engine it replaces, ot_ta_add_bf16_sram_engine, retires ONE element per cycle
// through a combinational adder and place-and-routes at 239 MHz. Two things are
// wrong with that, and they are independent:
//
//   * one element per cycle is not a vector unit. A GPU's FP pipe is W lanes
//     wide and retires W results per cycle.
//   * a combinational adder sets the cycle time to a whole float add. The adder
//     here is ot_bf16_add_pipe, five stages, one result per lane per cycle.
//
// FLOW CONTROL, and why it is credit-based. The obvious way to handle
// backpressure on a pipelined unit is to put an enable on every pipeline
// register and freeze the whole thing when the consumer stalls. That works and
// it is wrong here: it puts a mux in front of every register in the datapath,
// on the exact path the pipelining existed to shorten, so it gives back some of
// what the pipelining bought.
//
// Instead nothing in the datapath can ever stall. An operand is issued only when
// a landing slot is already reserved for its result, so the result always has
// somewhere to go. `credits` counts free slots in the output FIFO, is decremented
// at issue and incremented at drain, and the unit refuses to accept when it hits
// zero. The FIFO is deeper than the pipeline, which is what makes the guarantee
// hold: every operand in flight has a slot waiting even if the consumer never
// takes another result.
//
// The arithmetic is ot_bf16_add_pipe's, which is bit-identical to
// ot_bf16_add_rne -- proven over all 2**32 input pairs by SAT miter
// (tools/prove_bf16_add_equivalence.sh). So this unit does not change what a
// vector add computes. It changes how many of them happen per cycle and how
// short the cycle can be.
//
// Per-lane error and saturation reporting is preserved: the engine's contract
// reports a saturating element and a nonfinite input, and losing that at the
// vector boundary would be a silent narrowing of the ABI.
// ---------------------------------------------------------------------------
module ot_vector_add_unit #(
    parameter integer LANES     = 8,
    parameter integer FIFO_LOG2 = 4       // 16 slots, > the 5-stage depth
) (
    input  wire                   clk,
    input  wire                   rst_n,

    // ---- issue port: one vector of LANES operand pairs per cycle ----
    input  wire                   in_valid,
    output wire                   in_ready,
    input  wire [16*LANES-1:0]    in_left,
    input  wire [16*LANES-1:0]    in_right,

    // ---- drain port ----
    output wire                   out_valid,
    input  wire                   out_ready,
    output wire [16*LANES-1:0]    out_result,
    output wire [LANES-1:0]       out_saturated,
    output wire [2*LANES-1:0]     out_error
);
    localparam integer DEPTH = 1 << FIFO_LOG2;

    // ---- LANES pipelined adders, all in lockstep --------------------------
    wire [16*LANES-1:0] lane_result;
    wire [LANES-1:0]    lane_saturated;
    wire [2*LANES-1:0]  lane_error;
    wire [LANES-1:0]    lane_valid;

    wire accept = in_valid && in_ready;

    genvar i;
    generate
        for (i = 0; i < LANES; i = i + 1) begin : lane
            ot_bf16_add_pipe u_add (
                .clk(clk), .rst_n(rst_n),
                .in_valid(accept),
                .left_code (in_left [16*i +: 16]),
                .right_code(in_right[16*i +: 16]),
                .out_valid(lane_valid[i]),
                .result_code(lane_result[16*i +: 16]),
                .result_saturated(lane_saturated[i]),
                .result_error(lane_error[2*i +: 2])
            );
        end
    endgenerate

    //: Every lane sees the same in_valid and has the same depth, so lane 0's
    //: out_valid is the whole vector's. The others are left unread on purpose --
    //: reducing them would build an AND tree across the vector width for a
    //: signal that cannot differ.
    wire vec_valid = lane_valid[0];

    // ---- output FIFO: the landing slots the credit counter reserves --------
    reg [16*LANES-1:0] fifo_result [0:DEPTH-1];
    reg [LANES-1:0]    fifo_sat    [0:DEPTH-1];
    reg [2*LANES-1:0]  fifo_err    [0:DEPTH-1];
    reg [FIFO_LOG2:0]  wptr, rptr;

    wire fifo_empty = (wptr == rptr);
    wire drain      = out_valid && out_ready;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) wptr <= {(FIFO_LOG2+1){1'b0}};
        else if (vec_valid) begin
            fifo_result[wptr[FIFO_LOG2-1:0]] <= lane_result;
            fifo_sat   [wptr[FIFO_LOG2-1:0]] <= lane_saturated;
            fifo_err   [wptr[FIFO_LOG2-1:0]] <= lane_error;
            wptr <= wptr + 1'b1;
        end

    always @(posedge clk or negedge rst_n)
        if (!rst_n) rptr <= {(FIFO_LOG2+1){1'b0}};
        else if (drain) rptr <= rptr + 1'b1;

    assign out_valid     = !fifo_empty;
    assign out_result    = fifo_result[rptr[FIFO_LOG2-1:0]];
    assign out_saturated = fifo_sat   [rptr[FIFO_LOG2-1:0]];
    assign out_error     = fifo_err   [rptr[FIFO_LOG2-1:0]];

    // ---- credits: a slot is reserved BEFORE the operand is issued ---------
    //: This is the whole reason the datapath needs no enables. credits is the
    //: number of FIFO slots not already promised to an operand in flight or to
    //: a result already sitting in the FIFO. Issue takes one; drain returns one.
    //: At zero the unit stops accepting, so a result can never arrive with
    //: nowhere to land and no pipeline register ever has to hold its value.
    reg [FIFO_LOG2:0] credits;

    always @(posedge clk or negedge rst_n)
        if (!rst_n)            credits <= DEPTH[FIFO_LOG2:0];
        else if (accept && !drain) credits <= credits - 1'b1;
        else if (drain && !accept) credits <= credits + 1'b1;

    assign in_ready = (credits != {(FIFO_LOG2+1){1'b0}});
endmodule
