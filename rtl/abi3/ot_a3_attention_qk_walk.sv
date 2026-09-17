`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ATTENTION.SPARSE's QK reduction, for one (query row, head) over a source block.
//
// The reference's schedule is K-MAJOR and this follows it exactly, because the
// association is the contract:
//
//     "Step d forms every product of reduction index d and adds it in, so each
//      score still sees its own head_dim products in strictly ascending order."
//
// so the loops are d on the outside and lane on the inside. That ordering is
// also the only pipeline-friendly one: the LANES accumulators are independent,
// so consecutive issues never depend on each other and the MAC runs at one per
// cycle. The obvious lane-major nesting would make every issue depend on the
// previous one and cost the MAC's full latency per product.
//
// THE ACCUMULATOR HAZARD IS CLOSED BY LANES > DEPTH, not by interlocks. Lane L's
// accumulator is read at issue and written when the MAC retires, MAC_LAT + 1
// cycles later; the walk returns to lane L after LANES issues. With LANES at 64
// against a depth of 6 there is no window in which a stale accumulator can be
// read, and the elaboration-time check below makes that a property rather than
// an observation.
//
// ONE FUSED PRODUCT-ADD IS THE CONTRACT, not a multiply then an add. The
// reference's own repair path says so: where its two-ufunc schedule may differ it
// calls ``_single_rounded_add(accumulator, q, k)`` -- one rounding of
// ``acc + q*k``. ot_mac_bf16_fp32_pipe computes exactly that, and the product of
// two BF16 values is EXACT in binary32 (two 8-bit significands make at most 16
// significant bits against binary32's 24), so the fused form needs no repair
// path here at all: it is the contract directly, on every input.
//
// AN INVALID LANE READS AS ZERO, which is what the reference does -- it gathers
// row 0 for a padding lane and then overwrites that row with +0, so the lane's
// score is a sum of zero products. The softmax masks the lane afterwards, so the
// value is not observable; matching it anyway costs a mux and keeps the two
// implementations comparable at every intermediate.
// ---------------------------------------------------------------------------
module ot_a3_attention_qk_walk #(
    parameter integer LANES = 64,
    //: SIX, not five: this walk instantiates the product-add with its rounding
    //: stage split, which is what lifts the block off the MAC's own 1.716 ns
    //: final cone. Both depths are bit-identical to
    //: ot_fp32_rne_pkg::bf16_bf16_fp32_product_add_rne over 901,440 cases, so
    //: the choice is purely a timing one.
    parameter integer MAC_ROUND_STAGE = 1,
    parameter integer MAC_LAT = 6
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    //: Reduction depth: the head's width.
    input  wire [31:0] cfg_head_dim,
    input  wire [31:0] cfg_q_base,
    //: Elements between one KV row and the next.
    input  wire [31:0] cfg_kv_stride,
    input  wire [31:0] cfg_kv_base,
    //: The softmax scale, applied to every finished score.
    input  wire [31:0] cfg_scale_code,
    input  wire [LANES-1:0]    lane_valid,
    //: Each lane's selected KV row, from ot_a3_attention_kv_index.
    input  wire [LANES*32-1:0] lane_row,

    output reg         q_rd_en,
    output reg  [31:0] q_rd_addr,
    input  wire [31:0] q_rd_data,
    output reg         kv_rd_en,
    output reg  [31:0] kv_rd_addr,
    input  wire [31:0] kv_rd_data,

    output reg         busy,
    output reg         done,
    output reg  [LANES*32-1:0] scores,
    output reg  [7:0]  error_code,
    output reg  [31:0] mac_count
);
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE = ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_PRODUCT_RANGE = ot_a3_engine_pkg::ERR_PRODUCT_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    localparam [15:0] BF16_ONE = 16'h3F80;
    //: Read address to MAC issue is one edge, and the MAC retires MAC_LAT after
    //: that, so a lane's accumulator is busy for MAC_LAT + 2 issues.
    localparam integer PIPE_DEPTH = MAC_LAT + 2;

    integer i;

    localparam [2:0] S_BASE  = 3'd6;
    localparam [2:0] S_IDLE  = 3'd0;
    localparam [2:0] S_QHOLD = 3'd5;
    localparam [2:0] S_WALK  = 3'd1;
    localparam [2:0] S_DRAIN = 3'd2;
    localparam [2:0] S_SCALE = 3'd3;
    localparam [2:0] S_DONE  = 3'd4;
    reg [2:0] state;

    reg [31:0] depth;        //: the reduction index d
    reg [31:0] lane;         //: the lane cursor within this d
    reg [31:0] drain;
    reg [1:0]  qphase;
    reg [31:0] scale_lane;
    reg [31:0] acc [0:LANES-1];
    //: EVERY LANE'S ROW ADDRESS, COMPUTED ONCE.
    //:
    //: The inner loop's address is base + row[lane]*stride + depth, and `lane`
    //: advances every cycle, so writing it that way puts a 64-way mux, a 32x32
    //: multiply and two adds between the lane counter and the address register.
    //: Routed on ASAP7 that was this block's critical path as soon as the
    //: product-add stopped being it: lane[1] to kv_rd_addr[30] at -239 ps in a
    //: 1.2 ns period, for 694.9 MHz.
    //:
    //: Nothing in base + row[lane]*stride depends on the reduction index, so it
    //: is computed once per launch into one register per lane and the inner loop
    //: becomes a mux and an add. The setup costs LANES cycles against the
    //: LANES * head_dim issue cycles that follow -- 64 against 32,768 at the
    //: shipped head width.
    reg [31:0] row_addr [0:LANES-1];
    reg [31:0] base_lane;
    //: AND THE MULTIPLY IS PIPELINED THERE, because static timing does not care
    //: how often a path runs: hoisting it into its own state shortens no path by
    //: itself. Splitting it into two 16x32 halves with a register between is what
    //: shortens it, and the setup state has the cycles to spare.
    reg [31:0] mul_a, mul_b;
    reg [47:0] part_lo, part_hi;
    reg [1:0]  base_phase;
    reg [15:0] q_held;
    //: The lane and liveness that produced the address now on the kv bus.
    reg [31:0] kv_rd_lane;
    reg        kv_rd_live;
    reg        nonfinite;

    //: LANES must exceed the pipeline depth or a stale accumulator is read.
    //: Checked at elaboration rather than trusted to the default.
    initial begin
        if (LANES <= PIPE_DEPTH) begin
            $display("ot_a3_attention_qk_walk: LANES=%0d must exceed the pipeline depth %0d",
                     LANES, PIPE_DEPTH);
            $finish;
        end
    end

    // -- the operand pipeline: ONE stage, because the read is registered -----
    //: The address is on the bus during cycle C, the memory captures at edge
    //: C+1, so kv_rd_data is valid DURING C+1 -- which is the cycle this stage's
    //: valid marks and the cycle the MAC samples at its end. A second stage
    //: would pair each lane's accumulator with the NEXT lane's element, which is
    //: what this walk did first: every product right and every one misattributed.
    //: kv_rd_lane IS LATCHED WITH kv_rd_addr, BY THE SAME EDGE, so the element
    //: and the accumulator it lands in cannot drift apart. Sampling the live
    //: `lane` cursor here instead reads it one increment past the lane whose
    //: address is on the bus, and then every element is added to its
    //: neighbour's accumulator: the walk's second failure, and at the output
    //: indistinguishable from a latency error, which is why the retirement
    //: companion got blamed for it first and deepened wrongly.
    reg        b_valid;
    reg [31:0] b_lane;
    reg        b_live;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            b_valid <= 1'b0; b_lane <= 32'd0; b_live <= 1'b0;
        end else begin
            b_valid <= kv_rd_en;
            b_lane  <= kv_rd_lane;
            b_live  <= kv_rd_live;
        end
    end

    //: The KV element for a padding lane reads as +0, matching the reference's
    //: zeroed gather rather than leaving the lane's score undefined.
    wire [15:0] kv_element = b_live ? kv_rd_data[15:0] : 16'h0000;
    wire [31:0] acc_in = acc[b_lane[$clog2(LANES)-1:0]];
    wire [33:0] q_wide = ot_a3_format_pkg::decode_bf16(q_held);
    wire [33:0] kv_wide = ot_a3_format_pkg::decode_bf16(kv_element);

    wire        mac_vout;
    wire [31:0] mac_y;
    wire [1:0]  mac_err;
    ot_mac_bf16_fp32_pipe #(.ROUND_STAGE(MAC_ROUND_STAGE)) product_add (
        .clk(clk), .rst_n(rst_n), .valid_in(b_valid),
        .a(q_held), .b(kv_element), .c(acc_in),
        .y(mac_y), .err(mac_err), .valid_out(mac_vout)
    );

    //: The lane the retiring product belongs to, carried alongside it.
    //:
    //: MAC_LAT deep, counted from the cycle in which b_valid is high -- the
    //: issue cycle, whose ENDING edge the unit samples its operands on.
    localparam integer LANE_PIPE = MAC_LAT;
    reg [31:0] lat_lane [0:LANE_PIPE-1];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < LANE_PIPE; i = i + 1) lat_lane[i] <= 32'd0;
        end else begin
            lat_lane[0] <= b_lane;
            for (i = 0; i < LANE_PIPE-1; i = i + 1)
                lat_lane[i+1] <= lat_lane[i];
        end
    end
    wire [31:0] retire_lane = lat_lane[LANE_PIPE-1];

    //: The trailing scale multiply, one per lane once the walk has drained.
    reg         mul_valid_in;
    reg         mul_pending;
    wire [31:0] mul_y;
    wire [1:0]  mul_err;
    wire        mul_valid_out;
    ot_fp32_mul_rne_pipe scale_mul (
        .clk(clk), .rst_n(rst_n), .valid_in(mul_valid_in),
        .a(acc[scale_lane[$clog2(LANES)-1:0]]), .b(cfg_scale_code),
        .y(mul_y), .err(mul_err), .valid_out(mul_valid_out)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            depth <= 32'd0; lane <= 32'd0; drain <= 32'd0; scale_lane <= 32'd0;
            base_lane <= 32'd0; base_phase <= 2'd0;
            mul_a <= 32'd0; mul_b <= 32'd0;
            part_lo <= 48'd0; part_hi <= 48'd0;
            qphase <= 2'd0;
            q_rd_en <= 1'b0; q_rd_addr <= 32'd0;
            kv_rd_en <= 1'b0; kv_rd_addr <= 32'd0;
            kv_rd_lane <= 32'd0; kv_rd_live <= 1'b0;
            busy <= 1'b0; done <= 1'b0;
            scores <= {LANES{32'd0}};
            error_code <= ERR_NONE; mac_count <= 32'd0;
            q_held <= 16'd0; nonfinite <= 1'b0;
            mul_valid_in <= 1'b0; mul_pending <= 1'b0;
            for (i = 0; i < LANES; i = i + 1) acc[i] <= 32'd0;
        end else begin
            q_rd_en <= 1'b0;
            kv_rd_en <= 1'b0;
            mul_valid_in <= 1'b0;
            done <= 1'b0;

            //: Retire a product into its own lane's accumulator.
            if (mac_vout) begin
                acc[retire_lane[$clog2(LANES)-1:0]] <= mac_y;
                mac_count <= mac_count + 32'd1;
                if (mac_err != 2'd0) nonfinite <= 1'b1;
            end

            case (state)
                S_IDLE: begin
                    if (start) begin
                        depth <= 32'd0; lane <= 32'd0;
                        mac_count <= 32'd0; nonfinite <= 1'b0;
                        scale_lane <= 32'd0; mul_pending <= 1'b0;
                        for (i = 0; i < LANES; i = i + 1) acc[i] <= 32'd0;
                        if (cfg_head_dim == 32'd0) begin
                            error_code <= ERR_SHAPE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            error_code <= ERR_NONE;
                            busy <= 1'b1;
                            base_lane <= 32'd0;
                            base_phase <= 2'd0;
                            state <= S_BASE;
                        end
                    end
                end

                //: One lane's row address per pass through the two multiply
                //: halves. The row goes through the same validity gate the walk
                //: applies to the element, so an invalid lane addresses row zero
                //: rather than whatever -1 resolves to.
                S_BASE: begin
                    if (base_phase == 2'd0) begin
                        mul_a <= lane_valid[base_lane[$clog2(LANES)-1:0]]
                                 ? lane_row[base_lane[$clog2(LANES)-1:0]*32 +: 32]
                                 : 32'd0;
                        mul_b <= cfg_kv_stride;
                        base_phase <= 2'd1;
                    end else if (base_phase == 2'd1) begin
                        part_lo <= {16'd0, mul_a[15:0]} * {16'd0, mul_b};
                        part_hi <= {16'd0, mul_a[31:16]} * {16'd0, mul_b};
                        base_phase <= 2'd2;
                    end else begin
                        row_addr[base_lane[$clog2(LANES)-1:0]] <=
                            cfg_kv_base + part_lo[31:0] + {part_hi[15:0], 16'd0};
                        base_phase <= 2'd0;
                        if (base_lane + 32'd1 >= LANES[31:0]) begin
                            qphase <= 2'd0;
                            state <= S_QHOLD;
                        end else begin
                            base_lane <= base_lane + 32'd1;
                        end
                    end
                end

                //: THE QUERY ELEMENT IS HELD BEFORE THE LANE PASS, NOT DURING
                //: IT. Capturing it on the pass's first cycle takes whatever the
                //: bus held from the previous read, because the memory's own
                //: register updates on that same edge -- the first version of
                //: this walk did exactly that and every score was wrong.
                S_QHOLD: begin
                    if (qphase == 2'd0) begin
                        q_rd_en <= 1'b1;
                        q_rd_addr <= cfg_q_base + depth;
                        qphase <= 2'd1;
                    end else if (qphase == 2'd1) begin
                        qphase <= 2'd2;
                    end else begin
                        q_held <= q_rd_data[15:0];
                        lane <= 32'd0;
                        state <= S_WALK;
                    end
                end

                //: d on the OUTSIDE, lane on the inside -- the reference's order.
                S_WALK: begin
                    kv_rd_en <= 1'b1;
                    kv_rd_lane <= lane;
                    kv_rd_live <= lane_valid[lane[$clog2(LANES)-1:0]];
                    //: A mux and an add. The multiply is gone from this path.
                    kv_rd_addr <= row_addr[lane[$clog2(LANES)-1:0]] + depth;
                    if (lane + 32'd1 >= LANES[31:0]) begin
                        lane <= 32'd0;
                        if (depth + 32'd1 >= cfg_head_dim) begin
                            drain <= 32'd0;
                            state <= S_DRAIN;
                        end else begin
                            depth <= depth + 32'd1;
                            qphase <= 2'd0;
                            state <= S_QHOLD;
                        end
                    end else begin
                        lane <= lane + 32'd1;
                    end
                end

                S_DRAIN: begin
                    if (drain >= (PIPE_DEPTH[31:0] + 32'd2)) begin
                        if (nonfinite) begin
                            error_code <= ERR_OPERAND_NONFINITE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            scale_lane <= 32'd0;
                            state <= S_SCALE;
                        end
                    end else begin
                        drain <= drain + 32'd1;
                    end
                end

                //: score = RN(accumulator * scale), one binary32 rounding, which
                //: is what np.multiply(scores, scale) is.
                S_SCALE: begin
                    if (!mul_pending) begin
                        mul_valid_in <= 1'b1;
                        mul_pending <= 1'b1;
                    end else if (mul_valid_out) begin
                        mul_pending <= 1'b0;
                        if (mul_err != 2'd0) begin
                            error_code <= ERR_PRODUCT_RANGE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            scores[scale_lane*32 +: 32] <= mul_y;
                            if (scale_lane + 32'd1 >= LANES[31:0]) begin
                                busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                            end else begin
                                scale_lane <= scale_lane + 32'd1;
                            end
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

    wire _unused = &{1'b0, q_wide, kv_wide};
endmodule
