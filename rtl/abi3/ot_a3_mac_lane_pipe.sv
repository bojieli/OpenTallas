`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// TENSOR contraction lane, PIPELINED. A drop-in for ot_a3_mac_lane on the
// BF16 x BF16 unscaled path, under the same bf16_bf16_fp32_sequential_rne_v1
// contract and with the same memory-mapped ports.
//
// WHY. ot_a3_mac_lane retires one multiply-accumulate every FIVE cycles by
// construction -- ISSUE, WAIT, SCALE, MUL, ACC -- because it resolves a whole
// binary32 multiply and a whole binary32 add combinationally and gives each its
// own state. That is the tensor engine the real control plane drives, so it is
// the engine an end-to-end token currently flows through.
//
// This lane retires one per CYCLE, using the qualified ot_mac_bf16_fp32_pipe.
//
// HOW THE LOOP-CARRIED DEPENDENCE IS BROKEN, which is the whole design problem.
// The contract requires each output element's K products to accumulate in
// strictly ascending K. That is a serial dependence through a five-stage adder,
// so ONE output element can only advance every five cycles however deep the
// pipeline is -- which is exactly why the legacy lane is 1-in-5 and why simply
// pipelining the adder buys nothing.
//
// So the lane interleaves LANES_IF independent output elements. The inner loop
// runs over the interleave slot and the outer loop over K:
//
//     for k in 0..K-1:  for j in 0..LANES_IF-1:  issue (A[row,k], B[col+j,k])
//
// Consecutive cycles therefore touch DIFFERENT accumulators, and a given
// accumulator is revisited only every LANES_IF cycles. With LANES_IF >= the
// pipeline depth there is no hazard and the pipe stays full. Each element still
// sees its own products in ascending K, so the arithmetic is bit-identical --
// interleaving changes the ORDER OF ELEMENTS, never the order within an element.
//
// Output elements are written in ascending (row, col) exactly as before, because
// a group of LANES_IF columns finishes together and is drained in index order.
//
// SCOPE, and it is narrow on purpose. This lane implements BF16 x BF16 with no
// block scaling. Any other dtype pair, or a descriptor that declares a scale
// object, must go to ot_a3_mac_lane; ot_a3_engine_array routes on exactly that
// predicate, so nothing changes behaviour for descriptors this lane does not
// claim. The shipped Qwen3 program's MATMULs are all in scope.
// ---------------------------------------------------------------------------
module ot_a3_mac_lane_pipe #(
    //: Must be at least the pipeline depth of ot_mac_bf16_fp32_pipe, which is 5.
    //: Eight leaves margin and makes the slot counter a clean power of two.
    parameter integer LANES_IF = 8
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [15:0] cfg_rows,          // M
    input  wire [15:0] cfg_cols,          // N
    input  wire [15:0] cfg_depth,         // K
    input  wire [7:0]  cfg_dtype_a,
    input  wire [7:0]  cfg_dtype_b,
    input  wire [31:0] cfg_a_base,
    input  wire [31:0] cfg_b_base,
    input  wire [31:0] cfg_out_base,

    output reg         a_rd_en,
    output reg  [31:0] a_rd_addr,
    input  wire [31:0] a_rd_data,
    output reg         b_rd_en,
    output reg  [31:0] b_rd_addr,
    input  wire [31:0] b_rd_data,

    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count,
    output reg  [31:0] saturation_count,
    output reg  [31:0] mac_count
);
    localparam [7:0] ERR_NONE              = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE = ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_ACCUMULATE_RANGE  = ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_SHAPE             = ot_a3_engine_pkg::ERR_SHAPE;

    //: The accumulator array is LANES_IF deep, so an index into it must be
    //: exactly $clog2(LANES_IF) bits. A wider index is a truncation warning, and
    //: a truncation warning on an array index is the shape of defect that a
    //: -Wno-fatal build turns into a wrong answer.
    localparam integer SW = (LANES_IF <= 2) ? 1 : $clog2(LANES_IF);

    localparam [3:0] S_IDLE = 4'd0, S_WALK = 4'd1, S_DRAIN = 4'd2,
                     S_STORE = 4'd3, S_DONE = 4'd4;

    reg [3:0]  state;
    reg [15:0] row, col_base, k;
    reg [3:0]  slot;                      // interleave slot, 0..LANES_IF-1
    reg [3:0]  drain;
    reg [3:0]  store_j;
    reg [15:0] group_cols;                // columns live in this group

    //: One accumulator per interleave slot. Each is a separate output element's
    //: running binary32 sum, advanced in strictly ascending K.
    reg [31:0] acc [0:LANES_IF-1];

    // ---- operand fetch: one A word and one B word per cycle ----------------
    //: A[row,k] is re-read for every slot at the same k rather than cached. It
    //: costs a read port cycle that is available anyway -- the lane issues one A
    //: and one B read per cycle, which is what the legacy lane's ports provide --
    //: and it keeps the address arithmetic identical to the legacy lane's.
    wire [15:0] cur_col = col_base + {12'b0, slot};
    wire walking = (state == S_WALK);

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            a_rd_en <= 1'b0; b_rd_en <= 1'b0;
            a_rd_addr <= 32'b0; b_rd_addr <= 32'b0;
        end else begin
            a_rd_en   <= walking;
            b_rd_en   <= walking;
            a_rd_addr <= cfg_a_base + ({16'b0, row} * {16'b0, cfg_depth}) + {16'b0, k};
            b_rd_addr <= cfg_b_base + ({16'b0, cur_col} * {16'b0, cfg_depth}) + {16'b0, k};
        end

    //: TWO delays, not one. The address is REGISTERED on one edge, the memory
    //: answers on the NEXT, so the operand words are only valid on the second edge
    //: after the slot was current. Delaying the issue by one had the MAC sampling
    //: the previous slot's operands against this slot's accumulator -- the same
    //: off-by-one the compute unit's sequencer had, and for the same reason.
    reg        iss_v1, iss_v;
    reg [3:0]  iss_slot1, iss_slot;
    reg        iss_rng1, iss_in_range;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            iss_v1 <= 1'b0; iss_v <= 1'b0;
            iss_slot1 <= 4'b0; iss_slot <= 4'b0;
            iss_rng1 <= 1'b0; iss_in_range <= 1'b0;
        end else begin
            iss_v1       <= walking;
            iss_slot1    <= slot;
            iss_rng1     <= (cur_col < cfg_cols);
            iss_v        <= iss_v1;
            iss_slot     <= iss_slot1;
            iss_in_range <= iss_rng1;
        end

    wire [31:0] pipe_y;
    wire [1:0]  pipe_err;
    wire        pipe_ov;

    ot_mac_bf16_fp32_pipe mac (
        .clk(clk), .rst_n(rst_n),
        .valid_in(iss_v && iss_in_range),
        .a(a_rd_data[15:0]), .b(b_rd_data[15:0]),
        .c(acc[iss_slot[SW-1:0]]),
        .y(pipe_y), .err(pipe_err), .valid_out(pipe_ov)
    );

    //: The pipe's result returns DEPTH cycles later and must land in the slot it
    //: came from, so the slot index is delayed by the same depth. Five registers,
    //: matching ot_mac_bf16_fp32_pipe's five stages.
    reg [3:0] slot_d1, slot_d2, slot_d3, slot_d4, slot_d5;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            slot_d1 <= 4'b0; slot_d2 <= 4'b0; slot_d3 <= 4'b0;
            slot_d4 <= 4'b0; slot_d5 <= 4'b0;
        end else begin
            slot_d1 <= iss_slot; slot_d2 <= slot_d1; slot_d3 <= slot_d2;
            slot_d4 <= slot_d3;  slot_d5 <= slot_d4;
        end

    integer ai;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            for (ai = 0; ai < LANES_IF; ai = ai + 1) acc[ai] <= 32'b0;
        end else if (state == S_IDLE && start) begin
            for (ai = 0; ai < LANES_IF; ai = ai + 1) acc[ai] <= 32'b0;
        end else if (state == S_STORE && store_j == (LANES_IF[3:0] - 4'd1)) begin
            //: Cleared on the LAST drain cycle of a group, not the first. Clearing
            //: at store_j == 0 zeroed slots 1..LANES_IF-1 before they had been
            //: written, so every group after the first was wrong -- the failures
            //: started at write 8, the second column group. Because out_data is
            //: assigned non-blocking from acc[store_j] on this same edge, it still
            //: captures the pre-clear value, so the last slot is written correctly.
            for (ai = 0; ai < LANES_IF; ai = ai + 1) acc[ai] <= 32'b0;
        end else if (pipe_ov)
            acc[slot_d5[SW-1:0]] <= pipe_y;

    //: The narrowing of whichever accumulator S_STORE is draining this cycle.
    wire [18:0] narrowed = ot_fp32_rne_pkg::fp32_to_bf16_rne(acc[store_j[SW-1:0]]);

    // ---- error latching, fail closed as the legacy lane does ---------------
    always @(posedge clk or negedge rst_n)
        if (!rst_n) error_code <= ERR_NONE;
        else if (state == S_IDLE && start)
            error_code <= ((cfg_rows == 0) || (cfg_cols == 0) || (cfg_depth == 0))
                          ? ERR_SHAPE : ERR_NONE;
        else if (pipe_ov && (error_code == ERR_NONE)) begin
            if (pipe_err == 2'd1)      error_code <= ERR_OPERAND_NONFINITE;
            else if (pipe_err == 2'd2) error_code <= ERR_ACCUMULATE_RANGE;
        end

    // ---- sequencer ---------------------------------------------------------
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            state <= S_IDLE; busy <= 1'b0; done <= 1'b0;
            row <= 16'b0; col_base <= 16'b0; k <= 16'b0; slot <= 4'b0;
            drain <= 4'b0; store_j <= 4'b0; group_cols <= 16'b0;
            out_we <= 1'b0; out_addr <= 32'b0; out_data <= 32'b0;
            out_count <= 32'b0; saturation_count <= 32'b0; mac_count <= 32'b0;
        end else begin
            done <= 1'b0;
            out_we <= 1'b0;
            if (pipe_ov) mac_count <= mac_count + 32'd1;

            case (state)
                S_IDLE:
                    if (start) begin
                        busy <= 1'b1;
                        row <= 16'b0; col_base <= 16'b0; k <= 16'b0; slot <= 4'b0;
                        out_count <= 32'b0; saturation_count <= 32'b0;
                        mac_count <= 32'b0;
                        if ((cfg_rows == 0) || (cfg_cols == 0) || (cfg_depth == 0))
                            state <= S_DONE;
                        else
                            state <= S_WALK;
                    end

                S_WALK: begin
                    //: inner loop over the interleave slot, outer over K
                    if (slot == (LANES_IF[3:0] - 4'd1)) begin
                        slot <= 4'd0;
                        if (k == (cfg_depth - 16'd1)) begin
                            drain <= 4'd9;        // pipe depth plus margin
                            state <= S_DRAIN;
                        end else
                            k <= k + 16'd1;
                    end else
                        slot <= slot + 4'd1;
                end

                S_DRAIN:
                    if (drain == 4'd0) begin
                        store_j <= 4'd0;
                        state <= S_STORE;
                    end else
                        drain <= drain - 4'd1;

                S_STORE: begin
                    //: drain the group in ascending column order, skipping slots
                    //: past cfg_cols.
                    //:
                    //: THE OUTPUT IS BF16, not the raw binary32 accumulator. The
                    //: contract's last step is one RNE narrowing of the finished
                    //: accumulator, saturating to the largest finite BF16 code and
                    //: COUNTING that saturation. Writing the accumulator itself
                    //: made every output word wrong in a way the arithmetic
                    //: qualification could not see: ot_mac_bf16_fp32_pipe is
                    //: bit-exact and the lane around it still wrote 0xbbb2b33c
                    //: where the legacy lane writes 0x0000bbb3.
                    if ((col_base + {12'b0, store_j}) < cfg_cols) begin
                        if (narrowed[18:17] != 2'd0) begin
                            //: nonfinite accumulator: fail closed, write nothing,
                            //: exactly as the legacy lane does
                            if (error_code == ERR_NONE)
                                error_code <= ERR_OPERAND_NONFINITE;
                        end else begin
                            out_we   <= 1'b1;
                            out_addr <= cfg_out_base +
                                        ({16'b0, row} * {16'b0, cfg_cols}) +
                                        {16'b0, col_base} + {28'b0, store_j};
                            out_data <= {16'b0, narrowed[15:0]};
                            out_count <= out_count + 32'd1;
                            if (narrowed[16])
                                saturation_count <= saturation_count + 32'd1;
                        end
                    end
                    if (store_j == (LANES_IF[3:0] - 4'd1)) begin
                        store_j <= 4'd0;
                        if ((col_base + LANES_IF[15:0]) >= cfg_cols) begin
                            col_base <= 16'b0;
                            if (row == (cfg_rows - 16'd1))
                                state <= S_DONE;
                            else begin
                                row <= row + 16'd1;
                                k <= 16'b0; slot <= 4'b0;
                                state <= S_WALK;
                            end
                        end else begin
                            col_base <= col_base + LANES_IF[15:0];
                            k <= 16'b0; slot <= 4'b0;
                            state <= S_WALK;
                        end
                    end else
                        store_j <= store_j + 4'd1;
                end

                S_DONE: begin
                    busy <= 1'b0; done <= 1'b1; state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
endmodule
