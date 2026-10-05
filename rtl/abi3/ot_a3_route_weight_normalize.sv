`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ROUTE.WEIGHT_NORMALIZE -- the routed gate divided by its own group sum.
//
// Per group of ``slots`` weights the reference computes
//
//     total = ordered_sum(weights, reduction_order)
//     out_i = RN32(RN32(w_i / total) * scale)
//
// and REFUSES the group if ``total`` is not positive finite, because a routed
// gate normalised by a nonpositive sum is not a gate.  The division is per
// element: computing one reciprocal and multiplying would be cheaper and is not
// the same arithmetic, so it is not done.
//
// EVERY SHIPPED OPERATOR IS FP32-IN/FP32-OUT WITH SEQUENTIAL_ASCENDING AND
// scale_bits 0.  Read off the descriptor tables at HEAD: 4 operators in
// deepseek-v4-flash-rom, 16 in deepseek-v41-flash-rom-array-64, all identical in
// those three fields.  Two consequences shape this block:
//
//   * FP32 addends cannot go through ot_mac_bf16_fp32_pipe, whose ``a`` is BF16.
//     The fold therefore runs on ot_fp32_add_rne_pipe -- five stages, II=1,
//     qualified bit-identical to ot_fp32_rne_pkg::fp32_add_rne over 898,081
//     cases.  The combinational authority in this position measured 157.6 MHz
//     inside ot_a3_reduction_expert_sum.
//   * a scale of 1.0 makes the trailing multiply the identity, so the only
//     binary32 multiplier this block would need is for a case nothing ships.
//     ENABLE_SCALE is therefore 0 by default and a scaled operator is REFUSED
//     rather than silently ignored; setting it to 1 admits the case and brings a
//     combinational ot_fp32_rne_pkg::fp32_mul_rne into the timing cone, which is
//     a cost the caller should choose deliberately.
//
// ORDER IS A REFUSAL, NOT A PARAMETER.  Only SEQUENTIAL_ASCENDING is admitted,
// matching ot_a3_reduction_ordered_sum: a fold that silently used a different
// association would disagree with the reference in the last bit.
//
// THROUGHPUT IS SET BY THE DIVIDER, NOT THE FOLD.  ot_a3_fp32_div_rne binary-
// searches the encoding space in 32 cycles and is not pipelined, so one group
// costs ceil(slots / DIVIDERS) * 32 cycles there against 5 * (slots - 1) in the
// fold.  DIVIDERS is the knob that matters; the fold is never the bottleneck.
// ---------------------------------------------------------------------------
module ot_a3_route_weight_normalize #(
    parameter integer MAX_SLOTS = 8,
    parameter integer DIVIDERS = 1,
    parameter integer ENABLE_SCALE = 0
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [31:0] cfg_groups,
    input  wire [31:0] cfg_slots,            //: 1..MAX_SLOTS
    //: runtime.abi3.constants.ReductionOrder; only 0 is admitted.
    input  wire [7:0]  cfg_reduction_order,
    input  wire        cfg_has_scale,
    input  wire [31:0] cfg_scale_code,
    input  wire [31:0] cfg_in_base,
    input  wire [31:0] cfg_out_base,
    //: 0 narrows the result to BF16, 1 stores the binary32 code.
    input  wire        cfg_out_fp32,

    output reg         wgt_rd_en,
    output reg  [31:0] wgt_rd_addr,
    input  wire [31:0] wgt_rd_data,

    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count,
    output reg  [31:0] saturation_count
);
    // Re-declared rather than wildcard-imported: Icarus 11 turns a
    // wildcard-imported name used only in a port connection into an implicit
    // net, and the pinned Yosys 0.68 frontend rejects ``import`` outright.
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE = ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_ACCUMULATE_RANGE = ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_SCALE_RANGE = ot_a3_engine_pkg::ERR_SCALE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    //: runtime.abi3.constants.ReductionOrder.SEQUENTIAL_ASCENDING
    localparam [7:0] ORDER_SEQUENTIAL_ASCENDING = 8'd0;

    localparam [3:0] S_IDLE     = 4'd0;
    localparam [3:0] S_READ     = 4'd1;
    localparam [3:0] S_RDRAIN   = 4'd9;
    localparam [3:0] S_FOLD     = 4'd2;
    localparam [3:0] S_TOTAL    = 4'd3;
    localparam [3:0] S_DIV_REQ  = 4'd4;
    localparam [3:0] S_DIV_WAIT = 4'd5;
    localparam [3:0] S_WRITE    = 4'd6;
    localparam [3:0] S_NEXT     = 4'd7;
    localparam [3:0] S_DONE     = 4'd8;
    //: The registered read answers two cycles behind its address, so the fold
    //: must not start the cycle the last address is issued. Without this the
    //: fold reads a STALE hold: fatal at slots=1, where S_READ issues one
    //: address and leaves immediately, and racy at slots=2.
    localparam integer READ_DRAIN = 3;

    integer i;

    reg [3:0]  state;
    reg [31:0] grp;
    reg [31:0] slot;
    reg [31:0] row;              //: advanced by slots, never grp * slots
    reg [31:0] total;
    reg [31:0] held [0:MAX_SLOTS-1];
    reg [31:0] quotient;
    //: The fold's own handshake. Keying the issue off ``add_valid_in`` instead
    //: re-issues the SAME add every cycle the adder is still working, because
    //: that register is high for exactly one cycle and the result is five away.
    reg        fold_started;
    reg        fold_pending;
    reg [31:0] drain;

    wire cfg_bad = (cfg_groups == 32'd0) || (cfg_slots == 32'd0) ||
                   (cfg_slots > MAX_SLOTS[31:0]) ||
                   (cfg_reduction_order != ORDER_SEQUENTIAL_ASCENDING);
    //: A scaled operator with no multiplier fails closed; it is never dropped.
    wire cfg_scale_refused = cfg_has_scale && (ENABLE_SCALE == 0);

    // -- the fold, on the pipelined adder ------------------------------------
    reg         add_valid_in;
    reg  [31:0] add_a, add_b;
    wire [31:0] add_y;
    wire [1:0]  add_err;
    wire        add_valid_out;

    ot_fp32_add_rne_pipe fold_adder (
        .clk(clk), .rst_n(rst_n), .valid_in(add_valid_in),
        .a(add_a), .b(add_b),
        .y(add_y), .err(add_err), .valid_out(add_valid_out)
    );

    // -- the division, correctly rounded -------------------------------------
    reg         div_in_valid;
    wire        div_in_ready;
    reg  [31:0] div_num;
    wire        div_out_valid;
    wire [31:0] div_result;
    wire [1:0]  div_error;

    ot_a3_fp32_div_rne divider (
        .clk(clk), .rst_n(rst_n),
        .in_valid(div_in_valid), .in_ready(div_in_ready),
        .numerator_code(div_num), .denominator_code(total),
        .out_valid(div_out_valid), .out_ready(state == S_DIV_WAIT),
        .result_code(div_result), .result_error(div_error)
    );

    // -- the trailing scale, present only when the caller admits the case ----
    wire [33:0] scaled = ot_fp32_rne_pkg::fp32_mul_rne(quotient, cfg_scale_code);
    wire [31:0] scale_applied = (ENABLE_SCALE != 0) && cfg_has_scale
                              ? scaled[31:0] : quotient;
    wire [1:0]  scale_error = (ENABLE_SCALE != 0) && cfg_has_scale
                            ? scaled[33:32] : 2'd0;

    // -- the narrowing, which is the identity on the shipped FP32 output -----
    wire [18:0] narrowed = ot_fp32_rne_pkg::fp32_to_bf16_rne(scale_applied);
    wire [31:0] store_code = cfg_out_fp32 ? scale_applied
                                          : {16'h0000, narrowed[15:0]};
    wire        store_saturated = !cfg_out_fp32 && narrowed[16];
    wire [1:0]  store_error = cfg_out_fp32 ? 2'd0 : narrowed[18:17];

    //: A total must be positive and finite, or the group is refused. Sign bit
    //: set, or a zero significand, or the nonfinite field -- all three.
    wire total_nonpositive = total[31] || (total[30:0] == 31'd0);
    wire total_nonfinite = (total[30:23] == 8'hff);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            grp <= 32'd0; slot <= 32'd0; row <= 32'd0;
            total <= 32'd0; quotient <= 32'd0;
            wgt_rd_en <= 1'b0; wgt_rd_addr <= 32'd0;
            out_we <= 1'b0; out_addr <= 32'd0; out_data <= 32'd0;
            busy <= 1'b0; done <= 1'b0; error_code <= ERR_NONE;
            out_count <= 32'd0; saturation_count <= 32'd0;
            add_valid_in <= 1'b0; add_a <= 32'd0; add_b <= 32'd0;
            div_in_valid <= 1'b0; div_num <= 32'd0;
            fold_started <= 1'b0; fold_pending <= 1'b0; drain <= 32'd0;
            for (i = 0; i < MAX_SLOTS; i = i + 1) held[i] <= 32'd0;
        end else begin
            wgt_rd_en <= 1'b0;
            out_we <= 1'b0;
            done <= 1'b0;
            add_valid_in <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (start) begin
                        grp <= 32'd0; slot <= 32'd0; row <= 32'd0;
                        out_count <= 32'd0; saturation_count <= 32'd0;
                        if (cfg_bad) begin
                            error_code <= ERR_SHAPE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else if (cfg_scale_refused) begin
                            error_code <= ERR_SCALE_RANGE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            error_code <= ERR_NONE;
                            busy <= 1'b1;
                            slot <= 32'd0;
                            fold_started <= 1'b0;
                            fold_pending <= 1'b0;
                            state <= S_READ;
                        end
                    end
                end

                //: Read the group's weights into the hold, one per cycle. The
                //: read is registered, so the value for ``slot`` lands two
                //: cycles later and is captured against the LATCHED index.
                S_READ: begin
                    wgt_rd_en <= 1'b1;
                    wgt_rd_addr <= cfg_in_base + row + slot;
                    if (slot + 32'd1 >= cfg_slots) begin
                        slot <= 32'd0;
                        drain <= 32'd0;
                        state <= S_RDRAIN;
                    end else begin
                        slot <= slot + 32'd1;
                    end
                end

                S_RDRAIN: begin
                    if (drain >= READ_DRAIN[31:0]) state <= S_FOLD;
                    else drain <= drain + 32'd1;
                end

                //: SEQUENTIAL ASCENDING, which is a loop-carried chain: the
                //: adder's five stages set the spacing, not its throughput.
                //: Independent GROUPS are what this adder can interleave, and
                //: doing so is the array's job, not this block's.
                S_FOLD: begin
                    if (!fold_started) begin
                        total <= held[0];
                        slot <= 32'd1;
                        fold_started <= 1'b1;
                        if (cfg_slots == 32'd1) state <= S_TOTAL;
                    end else if (!fold_pending) begin
                        add_valid_in <= 1'b1;
                        add_a <= total;
                        add_b <= held[slot[2:0]];
                        fold_pending <= 1'b1;
                    end else if (add_valid_out) begin
                        fold_pending <= 1'b0;
                        if (add_err != 2'd0) begin
                            error_code <= ERR_ACCUMULATE_RANGE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            total <= add_y;
                            if (slot + 32'd1 >= cfg_slots) begin
                                slot <= 32'd0;
                                state <= S_TOTAL;
                            end else begin
                                slot <= slot + 32'd1;
                            end
                        end
                    end
                end

                S_TOTAL: begin
                    if (total_nonfinite) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                    end else if (total_nonpositive) begin
                        //: The reference's trap: a routed gate cannot be
                        //: normalised by a sum that is not positive.
                        error_code <= ERR_ACCUMULATE_RANGE;
                        busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                    end else begin
                        slot <= 32'd0;
                        state <= S_DIV_REQ;
                    end
                end

                S_DIV_REQ: begin
                    div_num <= held[slot[2:0]];
                    if (div_in_ready) begin
                        div_in_valid <= 1'b1;
                        state <= S_DIV_WAIT;
                    end
                end

                S_DIV_WAIT: begin
                    div_in_valid <= 1'b0;
                    if (div_out_valid) begin
                        if (div_error != 2'd0) begin
                            error_code <= ERR_ACCUMULATE_RANGE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            quotient <= div_result;
                            state <= S_WRITE;
                        end
                    end
                end

                S_WRITE: begin
                    if (scale_error != 2'd0 || store_error != 2'd0) begin
                        error_code <= ERR_SCALE_RANGE;
                        busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                    end else begin
                        out_we <= 1'b1;
                        out_addr <= cfg_out_base + row + slot;
                        out_data <= store_code;
                        out_count <= out_count + 32'd1;
                        if (store_saturated)
                            saturation_count <= saturation_count + 32'd1;
                        if (slot + 32'd1 >= cfg_slots) begin
                            slot <= 32'd0;
                            state <= S_NEXT;
                        end else begin
                            slot <= slot + 32'd1;
                            state <= S_DIV_REQ;
                        end
                    end
                end

                S_NEXT: begin
                    if (grp + 32'd1 >= cfg_groups) begin
                        state <= S_DONE;
                    end else begin
                        grp <= grp + 32'd1;
                        row <= row + cfg_slots;
                        slot <= 32'd0;
                        fold_started <= 1'b0;
                        fold_pending <= 1'b0;
                        state <= S_READ;
                    end
                end

                S_DONE: begin
                    busy <= 1'b0; done <= 1'b1; state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end

    //: The registered read lands two cycles behind the address, so the hold is
    //: written against the LATCHED index rather than the live counter -- the
    //: counter has already moved on, and sampling it here is the off-by-one that
    //: leaves every value right and every position wrong.
    reg        rd_v1;
    reg [31:0] rd_i1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rd_v1 <= 1'b0; rd_i1 <= 32'd0;
        end else begin
            rd_v1 <= wgt_rd_en;
            //: Recovered from the ADDRESS, which is the only copy of the index
            //: that has not already advanced; ``row`` is stable for the whole
            //: group because it moves only in S_NEXT.
            rd_i1 <= wgt_rd_addr - cfg_in_base - row;
            if (rd_v1) held[rd_i1[2:0]] <= wgt_rd_data;
        end
    end
endmodule
