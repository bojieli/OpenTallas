`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Bounded VECTOR.INDEX_SCORE datapath.
//
// The integrated profile accepts batch one flattened into cfg_rows, four
// heads, up to eight candidates, a head dimension up to sixteen, and scale
// exactly 1.0.  Per head it performs an ascending-dimension BF16 dot product,
// rounds that score to BF16, applies ReLU, multiplies by the BF16 head weight
// and rounds again.  Four head contributions reduce as the frozen balanced
// tree (0+1)+(2+3), followed by the output BF16 conversion.
//
// Every operand is scanned before arithmetic and every output is buffered
// before commit.  A late poisoned key, weight, or intermediate therefore
// cannot expose a partial score tensor.
// ---------------------------------------------------------------------------
module ot_a3_vector_index_score #(
    parameter [15:0] MAX_ROWS = 16'd4,
    parameter integer HEADS = 4,
    parameter [15:0] MAX_CANDIDATES = 16'd8,
    parameter [15:0] MAX_DEPTH = 16'd16,
    parameter integer MAX_OUTPUTS = MAX_ROWS * MAX_CANDIDATES
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [15:0] cfg_rows,
    input  wire [15:0] cfg_cols,
    input  wire [15:0] cfg_depth,
    input  wire [31:0] cfg_count,
    input  wire [31:0] cfg_heads,
    input  wire [31:0] cfg_scale_bits,
    input  wire [7:0]  cfg_dtype_a,
    input  wire [7:0]  cfg_dtype_b,
    input  wire [31:0] cfg_query_base,
    input  wire [31:0] cfg_key_base,
    input  wire [31:0] cfg_weight_base,
    input  wire [31:0] cfg_out_base,

    output reg         q_rd_en,
    output reg  [31:0] q_rd_addr,
    input  wire [31:0] q_rd_data,
    output reg         k_rd_en,
    output reg  [31:0] k_rd_addr,
    input  wire [31:0] k_rd_data,
    output reg         w_rd_en,
    output reg  [31:0] w_rd_addr,
    input  wire [31:0] w_rd_data,
    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count,
    output reg  [31:0] work_count,
    output reg  [31:0] saturation_count
);
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE =
        ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_PRODUCT_RANGE = ot_a3_engine_pkg::ERR_PRODUCT_RANGE;
    localparam [7:0] ERR_ACCUMULATE_RANGE =
        ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;
    localparam [7:0] FMT_BF16 = 8'h10;
    localparam [1:0] LAST_HEAD = 2'd3;

    localparam [4:0] S_IDLE        = 5'd0;
    localparam [4:0] S_SCAN_ISSUE  = 5'd1;
    localparam [4:0] S_SCAN_WAIT   = 5'd2;
    localparam [4:0] S_SCAN_CHECK  = 5'd3;
    localparam [4:0] S_DOT_ISSUE   = 5'd4;
    localparam [4:0] S_DOT_WAIT    = 5'd5;
    localparam [4:0] S_DOT_STEP    = 5'd6;
    localparam [4:0] S_WEIGHT_ISSUE = 5'd7;
    localparam [4:0] S_WEIGHT_WAIT = 5'd8;
    localparam [4:0] S_WEIGHT      = 5'd9;
    localparam [4:0] S_REDUCE_1    = 5'd10;
    localparam [4:0] S_REDUCE_2    = 5'd11;
    localparam [4:0] S_COMMIT      = 5'd12;
    localparam [4:0] S_DONE        = 5'd13;
    //: the pipelined reduction adds answer LATENCY cycles after valid_in
    localparam [4:0] S_REDUCE_1W   = 5'd14;
    localparam [4:0] S_REDUCE_2W   = 5'd15;
    //: the dot product's narrowing and ReLU, moved off the product-add's cycle
    localparam [4:0] S_DOT_FINAL   = 5'd16;
    //: the interleaved dot loop: one six-cycle step per depth index, four MAC
    //: issues and two cycles of slack, and a drain for the pipe's tail
    localparam [4:0] S_DOT_RUN     = 5'd17;
    localparam [4:0] S_DOT_DRAIN   = 5'd18;
    //: the weight product's narrowing and its saturation count, off the multiply's cycle
    localparam [4:0] S_WEIGHT_FINAL = 5'd19;

    reg [4:0] state;
    reg [1:0] scan_kind;
    reg [31:0] index;
    reg [15:0] row;
    reg [15:0] candidate;
    reg [1:0] head;
    reg [15:0] depth_index;
    reg [31:0] accumulator;
    //: ONE ACCUMULATOR PER HEAD, because the four heads are what makes a pipelined
    //: MAC usable here.  The dot accumulation is loop-carried -- acc(d+1) needs
    //: acc(d) -- so a five-stage MAC serialised on one head costs five cycles per
    //: depth step where the combinational one cost three, which is a throughput loss
    //: against the clock gain.  The heads are INDEPENDENT: each keeps its own sum and
    //: they meet only in the balanced tree above, so four chains interleaved through
    //: one MAC keep it busy while every head still accumulates d = 0 .. D-1 in order.
    reg [31:0] head_acc [0:HEADS-1];
    reg [2:0]  dot_phase;
    reg [31:0] weight_product_q;
    reg [31:0] relu_value;
    reg [31:0] reduce_left;
    reg [31:0] reduce_right;
    reg [31:0] pending_saturation_count;
    reg [31:0] contributions [0:HEADS-1];
    reg [31:0] result_buffer [0:MAX_OUTPUTS-1];

    wire [31:0] query_elements =
        {16'b0, cfg_rows} * HEADS * {16'b0, cfg_depth};
    wire [31:0] key_elements =
        {16'b0, cfg_cols} * {16'b0, cfg_depth};
    wire [31:0] weight_elements = {16'b0, cfg_rows} * HEADS;
    wire [31:0] scan_limit = (scan_kind == 0) ? query_elements
                               : (scan_kind == 1) ? key_elements
                               : weight_elements;

    wire [33:0] decoded_q = ot_a3_format_pkg::decode_bf16(q_rd_data[15:0]);
    wire [33:0] decoded_k = ot_a3_format_pkg::decode_bf16(k_rd_data[15:0]);
    wire [33:0] decoded_w = ot_a3_format_pkg::decode_bf16(w_rd_data[15:0]);
    wire [33:0] dot_sum =
        ot_fp32_rne_pkg::bf16_bf16_fp32_product_add_rne(
            accumulator, q_rd_data[15:0], k_rd_data[15:0]
        );
    wire [18:0] dot_narrowed =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(dot_sum[31:0]);
    //: THE NARROWING OFF THE PRODUCT-ADD'S CYCLE.  With the head reduction pipelined,
    //: the critical path became k_rd_data[10] to relu_value[24] -- 117 cell arcs
    //: holding the operand decode, the FUSED bf16 product-add, this narrowing and the
    //: ReLU, all between two registers, and the block sat at 235.7 MHz.  The narrowing
    //: reads the ACCUMULATOR instead, which is a register, so the cone ends at the
    //: product-add and the narrowing starts a cycle of its own.
    //:
    //: It costs ONE cycle per head per candidate, taken once at the end of a
    //: cfg_depth-long accumulation (128 for the shipped indexer), and it changes no
    //: value: the same fp32_to_bf16_rne of the same binary32 sum, one cycle later.
    wire [18:0] acc_narrowed =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(accumulator);

    //: THE MAC, PIPELINED.  ot_mac_bf16_fp32_pipe is RN(a*b + c) at one result per
    //: cycle with a BF16 a and b and an FP32 c, qualified against the same
    //: bf16_bf16_fp32_product_add_rne this block used combinationally, so the value
    //: of every step is unchanged and only its timing moves.
    //:
    //: THE SIX-CYCLE STEP.  Phase 0 drives head 0's query address and the key
    //: address; phases 1..4 issue head 0..3 with the data that arrived; phase 5 is
    //: slack.  A result lands five cycles after its issue, so head h's issue in the
    //: next step is exactly one cycle after that head's previous result is written --
    //: which is why the step is six cycles and not five.  Four MACs per six cycles
    //: against the combinational form's one per three: 2x the rate before the clock.
    reg         mac_valid_in;
    reg  [1:0]  mac_head;
    wire [31:0] mac_y;
    wire [1:0]  mac_err;
    wire        mac_valid_out;
    reg  [1:0]  mac_head_d1, mac_head_d2, mac_head_d3, mac_head_d4, mac_head_d5;

    ot_mac_bf16_fp32_pipe dot_mac (
        .clk(clk), .rst_n(rst_n),
        .valid_in(mac_valid_in),
        .a(q_rd_data[15:0]), .b(k_rd_data[15:0]),
        .c(head_acc[mac_head]),
        .y(mac_y), .err(mac_err), .valid_out(mac_valid_out)
    );

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            mac_head_d1 <= 2'd0; mac_head_d2 <= 2'd0; mac_head_d3 <= 2'd0;
            mac_head_d4 <= 2'd0; mac_head_d5 <= 2'd0;
        end else begin
            mac_head_d1 <= mac_head;    mac_head_d2 <= mac_head_d1;
            mac_head_d3 <= mac_head_d2; mac_head_d4 <= mac_head_d3;
            mac_head_d5 <= mac_head_d4;
        end

    //: the result lands in the slot it came from, five cycles later
    integer ha;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            for (ha = 0; ha < HEADS; ha = ha + 1) head_acc[ha] <= 32'b0;
        end else if ((state == S_IDLE) && start) begin
            for (ha = 0; ha < HEADS; ha = ha + 1) head_acc[ha] <= 32'b0;
        end else if ((state == S_REDUCE_1) || (state == S_DOT_ISSUE)) begin
            for (ha = 0; ha < HEADS; ha = ha + 1) head_acc[ha] <= 32'b0;
        end else if (mac_valid_out) begin
            head_acc[mac_head_d5] <= mac_y;
        end

    wire [18:0] head_narrowed =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(head_acc[head]);
    wire [33:0] weighted_product =
        ot_fp32_rne_pkg::fp32_mul_rne(relu_value, decoded_w[31:0]);
    wire [18:0] weighted_narrowed =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(weighted_product[31:0]);
    //: THE WEIGHT STAGE'S NARROWING, OFF THE MULTIPLY'S CYCLE.  With the dot loop
    //: interleaved the critical path moved here: w_rd_data[7] to
    //: pending_saturation_count[24], 134 cell arcs with 60 HAxp5, holding the weight
    //: decode, fp32_mul_rne, this narrowing AND a 32-bit counter increment in one
    //: cycle.  Reading the REGISTERED product instead ends the multiply's cone at a
    //: flop, and costs one cycle per head per candidate.  Same value: the same
    //: fp32_to_bf16_rne of the same binary32 product, one cycle later.
    wire [18:0] weight_q_narrowed =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(weight_product_q);
    //: THE BALANCED REDUCTION, PIPELINED.  The four head contributions reduce as a
    //: tree -- two pair adds, then one -- and each was a combinational
    //: ot_fp32_rne_pkg::fp32_add_rne between registers.  Routed, the final one was the
    //: critical path: reduce_right[29] to result_buffer[17][1], 253 cell arcs with 60
    //: HAxp5 half adders, and the block came back at 151.0 MHz not met.  The pair adds
    //: are the same expression on the same operand width, so replacing only the last
    //: one would hand the wall to them -- which is why all three go at once.
    //:
    //: rtl/proto/ot_fp32_add_rne_pipe.sv is that arithmetic in five stages, qualified
    //: bit-identical to the authority including where the authority is deliberately
    //: not IEEE-754, so the REDUCTION ORDER and every rounding are unchanged: pair 0+1
    //: and pair 2+3 first, then their sum, which is what "the frozen balanced tree"
    //: means and what this block's vectors are bound to.
    //:
    //: The two pair adds share one valid_in because they are issued together and
    //: retire together, which keeps S_REDUCE_1 a single decision point.
    reg         add_pair_valid;
    reg         add_total_valid;
    wire [31:0] pair_01_y, pair_23_y, head_total_y;
    wire [1:0]  pair_01_err, pair_23_err, head_total_err;
    wire        pair_01_ov, pair_23_ov, head_total_ov;

    ot_fp32_add_rne_pipe pair_01_add (
        .clk(clk), .rst_n(rst_n), .valid_in(add_pair_valid),
        .a(contributions[0]), .b(contributions[1]),
        .y(pair_01_y), .err(pair_01_err), .valid_out(pair_01_ov)
    );
    ot_fp32_add_rne_pipe pair_23_add (
        .clk(clk), .rst_n(rst_n), .valid_in(add_pair_valid),
        .a(contributions[2]), .b(contributions[3]),
        .y(pair_23_y), .err(pair_23_err), .valid_out(pair_23_ov)
    );
    ot_fp32_add_rne_pipe head_total_add (
        .clk(clk), .rst_n(rst_n), .valid_in(add_total_valid),
        .a(reduce_left), .b(reduce_right),
        .y(head_total_y), .err(head_total_err), .valid_out(head_total_ov)
    );

    wire [18:0] output_narrowed =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(head_total_y);

    wire [33:0] scan_decoded = (scan_kind == 0) ? decoded_q
                                 : (scan_kind == 1) ? decoded_k
                                 : decoded_w;
    wire configuration_supported =
        (cfg_dtype_a == FMT_BF16) && (cfg_dtype_b == FMT_BF16) &&
        (cfg_rows != 0) && (cfg_rows <= MAX_ROWS) &&
        (cfg_cols != 0) && (cfg_cols <= MAX_CANDIDATES) &&
        (cfg_depth != 0) && (cfg_depth <= MAX_DEPTH) &&
        (cfg_heads == HEADS) && (cfg_scale_bits == 32'h3f80_0000) &&
        (cfg_count == ({16'b0, cfg_rows} * {16'b0, cfg_cols}));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            scan_kind <= 0;
            index <= 0;
            row <= 0;
            candidate <= 0;
            head <= 0;
            depth_index <= 0;
            accumulator <= 0;
            relu_value <= 0;
            reduce_left <= 0;
            reduce_right <= 0;
            add_pair_valid <= 1'b0;
            add_total_valid <= 1'b0;
            weight_product_q <= 32'b0;
            dot_phase <= 3'd0;
            mac_valid_in <= 1'b0;
            mac_head <= 2'd0;
            q_rd_en <= 1'b0;
            q_rd_addr <= 0;
            k_rd_en <= 1'b0;
            k_rd_addr <= 0;
            w_rd_en <= 1'b0;
            w_rd_addr <= 0;
            out_we <= 1'b0;
            out_addr <= 0;
            out_data <= 0;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            out_count <= 0;
            work_count <= 0;
            saturation_count <= 0;
            pending_saturation_count <= 0;
        end else begin
            done <= 1'b0;
            q_rd_en <= 1'b0;
            k_rd_en <= 1'b0;
            w_rd_en <= 1'b0;
            out_we <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        out_count <= 0;
                        work_count <= 0;
                        saturation_count <= 0;
                        pending_saturation_count <= 0;
                        scan_kind <= 0;
                        index <= 0;
                        row <= 0;
                        candidate <= 0;
                        head <= 0;
                        depth_index <= 0;
                        accumulator <= 0;
                        if (!configuration_supported) begin
                            error_code <= ERR_SHAPE;
                            state <= S_DONE;
                        end else begin
                            state <= S_SCAN_ISSUE;
                        end
                    end
                end

                S_SCAN_ISSUE: begin
                    if (scan_kind == 0) begin
                        q_rd_en <= 1'b1;
                        q_rd_addr <= cfg_query_base + index;
                    end else if (scan_kind == 1) begin
                        k_rd_en <= 1'b1;
                        k_rd_addr <= cfg_key_base + index;
                    end else begin
                        w_rd_en <= 1'b1;
                        w_rd_addr <= cfg_weight_base + index;
                    end
                    state <= S_SCAN_WAIT;
                end

                S_SCAN_WAIT: state <= S_SCAN_CHECK;

                S_SCAN_CHECK: begin
                    if (scan_decoded[33:32] != 0) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else if (index + 1 == scan_limit) begin
                        index <= 0;
                        if (scan_kind == 2) begin
                            row <= 0;
                            candidate <= 0;
                            head <= 0;
                            depth_index <= 0;
                            accumulator <= 0;
                            state <= S_DOT_ISSUE;
                        end else begin
                            scan_kind <= scan_kind + 1;
                            state <= S_SCAN_ISSUE;
                        end
                    end else begin
                        index <= index + 1;
                        state <= S_SCAN_ISSUE;
                    end
                end

                //: ENTRY.  Clears the four head accumulators (the always block above
                //: watches for this state) and starts the interleaved loop.
                S_DOT_ISSUE: begin
                    depth_index <= 0;
                    dot_phase <= 3'd0;
                    state <= S_DOT_RUN;
                end

                //: ONE DEPTH INDEX PER EIGHT CYCLES, four MAC issues inside it.
                //:
                //: phases 0..3 drive head 0..3's query address, and the KEY address
                //: every cycle -- the key is the same element for all four heads, so
                //: re-driving it keeps k_rd_data stable and no holding register is
                //: needed.  A memory answers two cycles after its address, so phases
                //: 2..5 carry head 0..3's query word and are the issue cycles;
                //: mac_valid_in is a register, so it is raised in phases 1..4.
                //:
                //: A result lands five cycles after its issue -- phases 7, 8, 9, 10 --
                //: and the next step issues head h at its own phase 2+h, which is
                //: absolute 10+h.  Head 0's result at 7 against its next issue at 10;
                //: head 3's at 10 against 13.  Three cycles of margin on every head,
                //: which is what buys the accumulator chain its safety without a
                //: forwarding path in the issue cone.
                S_DOT_RUN: begin
                    if (dot_phase <= 3'd3) begin
                        q_rd_en <= 1'b1;
                        q_rd_addr <= cfg_query_base +
                            ({16'b0, row} * HEADS * {16'b0, cfg_depth}) +
                            ({30'b0, dot_phase[1:0]} * {16'b0, cfg_depth}) +
                            {16'b0, depth_index};
                        k_rd_en <= 1'b1;
                        k_rd_addr <= cfg_key_base +
                            ({16'b0, candidate} * {16'b0, cfg_depth}) +
                            {16'b0, depth_index};
                    end
                    if ((dot_phase >= 3'd1) && (dot_phase <= 3'd4)) begin
                        mac_valid_in <= 1'b1;
                        mac_head <= dot_phase[1:0] - 2'd1;
                    end else
                        mac_valid_in <= 1'b0;

                    //: the operands of the issue happening THIS cycle
                    if ((dot_phase >= 3'd2) && (dot_phase <= 3'd5)) begin
                        if ((decoded_q[33:32] != 0) || (decoded_k[33:32] != 0)) begin
                            error_code <= ERR_OPERAND_NONFINITE;
                            mac_valid_in <= 1'b0;
                            state <= S_DONE;
                        end else
                            work_count <= work_count + 1;
                    end

                    if (dot_phase == 3'd7) begin
                        if (depth_index + 1 == cfg_depth) begin
                            dot_phase <= 3'd0;
                            state <= S_DOT_DRAIN;
                        end else begin
                            depth_index <= depth_index + 1;
                            dot_phase <= 3'd0;
                        end
                    end else
                        dot_phase <= dot_phase + 3'd1;
                end

                //: the pipe's tail: the last issue was five cycles back at most, so
                //: eight cycles of drain is more than enough and costs once per
                //: candidate rather than once per depth index.
                S_DOT_DRAIN: begin
                    mac_valid_in <= 1'b0;
                    if (mac_valid_out && (mac_err != 2'd0)) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end
                    if (dot_phase == 3'd7) begin
                        head <= 0;
                        state <= S_DOT_FINAL;
                    end else
                        dot_phase <= dot_phase + 3'd1;
                end

                //: per head, once all four accumulations are complete
                S_DOT_FINAL: begin
                    if (head_narrowed[18:17] != 0) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        if (head_narrowed[16])
                            pending_saturation_count <=
                                pending_saturation_count + 1;
                        // ReLU is applied after the architectural
                        // BF16 dot-product boundary.
                        relu_value <= head_narrowed[15]
                            ? 32'b0 : {head_narrowed[15:0], 16'b0};
                        state <= S_WEIGHT_ISSUE;
                    end
                end

                S_WEIGHT_ISSUE: begin
                    w_rd_en <= 1'b1;
                    w_rd_addr <= cfg_weight_base +
                        ({16'b0, row} * HEADS) + {30'b0, head};
                    state <= S_WEIGHT_WAIT;
                end

                S_WEIGHT_WAIT: state <= S_WEIGHT;

                S_WEIGHT: begin
                    if (decoded_w[33:32] != 0) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else if (weighted_product[33:32] != 0) begin
                        error_code <= ERR_PRODUCT_RANGE;
                        state <= S_DONE;
                    end else begin
                        //: the product is latched; its narrowing, its range check and
                        //: the saturation count read it from the register next cycle
                        weight_product_q <= weighted_product[31:0];
                        state <= S_WEIGHT_FINAL;
                    end
                end

                S_WEIGHT_FINAL: begin
                    if (weight_q_narrowed[18:17] != 0) begin
                        error_code <= ERR_PRODUCT_RANGE;
                        state <= S_DONE;
                    end else begin
                        if (weight_q_narrowed[16])
                            pending_saturation_count <=
                                pending_saturation_count + 1;
                        contributions[head] <=
                            {weight_q_narrowed[15:0], 16'b0};
                        accumulator <= 0;
                        depth_index <= 0;
                        if (head == LAST_HEAD) begin
                            state <= S_REDUCE_1;
                        end else begin
                            //: the accumulations are all done; the next head only
                            //: needs its narrowing, ReLU and weight
                            head <= head + 1;
                            state <= S_DOT_FINAL;
                        end
                    end
                end

                S_REDUCE_1: begin
                    add_pair_valid <= 1'b1;
                    state <= S_REDUCE_1W;
                end

                S_REDUCE_1W: begin
                    add_pair_valid <= 1'b0;
                    if (pair_01_ov && pair_23_ov) begin
                        if ((pair_01_err != 2'd0) || (pair_23_err != 2'd0)) begin
                            error_code <= ERR_ACCUMULATE_RANGE;
                            state <= S_DONE;
                        end else begin
                            reduce_left <= pair_01_y;
                            reduce_right <= pair_23_y;
                            state <= S_REDUCE_2;
                        end
                    end
                end

                S_REDUCE_2: begin
                    add_total_valid <= 1'b1;
                    state <= S_REDUCE_2W;
                end

                S_REDUCE_2W: begin
                    add_total_valid <= 1'b0;
                    if (!head_total_ov) begin
                        //: wait for the pipe
                    end else if ((head_total_err != 2'd0) ||
                        (output_narrowed[18:17] != 0)) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        if (output_narrowed[16])
                            pending_saturation_count <=
                                pending_saturation_count + 1;
                        result_buffer[({16'b0, row} * {16'b0, cfg_cols}) +
                                      {16'b0, candidate}] <=
                            {16'b0, output_narrowed[15:0]};
                        head <= 0;
                        depth_index <= 0;
                        accumulator <= 0;
                        if (candidate + 1 < cfg_cols) begin
                            candidate <= candidate + 1;
                            state <= S_DOT_ISSUE;
                        end else if (row + 1 < cfg_rows) begin
                            candidate <= 0;
                            row <= row + 1;
                            state <= S_DOT_ISSUE;
                        end else begin
                            index <= 0;
                            state <= S_COMMIT;
                        end
                    end
                end

                S_COMMIT: begin
                    out_we <= 1'b1;
                    out_addr <= cfg_out_base + index;
                    out_data <= result_buffer[index];
                    out_count <= out_count + 1;
                    if (index + 1 == cfg_count) begin
                        saturation_count <= pending_saturation_count;
                        state <= S_DONE;
                    end else begin
                        index <= index + 1;
                    end
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end

                default: begin
                    error_code <= ERR_SHAPE;
                    state <= S_DONE;
                end
            endcase
        end
    end
endmodule
