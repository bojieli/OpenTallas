`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// TENSOR.ROUTED_MATMUL -- each row contracted against the expert it was routed to.
//
// ``input 0`` is [rows, K] activations, ``input 1`` the stacked expert weight
// [E, N, K], ``input 2`` the [rows, topk] expert IDs and ``output 0`` is
// [rows, N].  ``aux_id_0``, when it is not NO_ID, is the GLOBAL expert count,
// which may exceed the local weight view's E on a node-sharded bank.
//
// EVERY SHIPPED INSTANCE IS topk = 1 AND CARRIES NO ROUTING WEIGHT, so this
// block implements that and refuses the rest.  Measured over all three
// deployments: input_view_2 is [rows, 1] in 72 of 72 instructions and
// input_view_3 is unbound in all 72.  DeepSeek resolves routing BEFORE the
// contraction -- ROUTE.EXPERT_DISPATCH has already made one row per (token,
// expert) pair -- so the graph carries one ID per row, the reference's slot loop
// runs once, and the routing weight is applied later by REDUCTION.EXPERT_SUM
// under amendment A10.  A topk > 1 operator is therefore REFUSED rather than
// given a combination order no deployment exercises.
//
// So the arithmetic is the ordinary contraction, and ot_a3_mac_lane_pipe is
// invoked once per row with the weight base that row's expert selects.  The lane
// interleaves LANES_IF output elements to hide its accumulate latency, and one
// row still presents N of them, so per-row invocation costs its start and drain
// against a row of N*K products -- 8.4 million at the shipped shapes.
//
// THE NODE-SHARD SKIP IS NOT OPTIONAL.  IDs are checked against the GLOBAL
// count, and a row whose expert belongs to another node's shard is left EXACT
// POSITIVE ZERO for the route-class-3 all-reduce to fill before EXPERT_REDUCE
// consumes it.  It is the one rule a "routed matmul is just a matmul" reading
// loses, and it is only exercised by the ARRAY topology:
//
//     deepseek-v4-flash-rom            local 256  global 256   never skips
//     deepseek-v41-flash-rom-wafer-2   local 384  global 384   never skips
//     deepseek-v4-flash-rom-array-32   local   8  global 256   skips 31 rows in 32
//
// A block tested only against the wafer deployments would pass and then silently
// contract rows its node does not own, on exactly one of the shipped cells.
//
// AND THE BOUND CHECK PRECEDES EVERY LAUNCH.  The reference reads the whole ID
// vector and raises before it contracts anything, so a refused operator leaves
// the output untouched rather than half-computed.
// ---------------------------------------------------------------------------
module ot_a3_tensor_routed_matmul #(
    parameter integer LANES_IF = 8
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [15:0] cfg_rows,           //: M
    input  wire [15:0] cfg_cols,           //: N
    input  wire [15:0] cfg_depth,          //: K
    input  wire [31:0] cfg_topk,           //: 1; anything else is refused
    input  wire [31:0] cfg_local_experts,  //: the weight view's E
    input  wire [31:0] cfg_global_experts, //: aux_id_0, or cfg_local_experts
    input  wire [31:0] cfg_expert_base,    //: node * local_experts
    input  wire [31:0] cfg_expert_stride,  //: N*K, the stride of one expert's matrix
    input  wire [7:0]  cfg_dtype_a,
    input  wire [7:0]  cfg_dtype_b,
    input  wire [31:0] cfg_a_base,
    input  wire [31:0] cfg_b_base,
    input  wire [31:0] cfg_id_base,
    input  wire [31:0] cfg_out_base,

    output reg         id_rd_en,
    output reg  [31:0] id_rd_addr,
    input  wire [31:0] id_rd_data,
    output wire        a_rd_en,
    output wire [31:0] a_rd_addr,
    input  wire [31:0] a_rd_data,
    output wire        b_rd_en,
    output wire [31:0] b_rd_addr,
    input  wire [31:0] b_rd_data,

    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count,
    output reg  [31:0] saturation_count,
    output reg  [31:0] mac_count,
    output reg  [31:0] rows_skipped,
    output reg  [31:0] rejected_ids
);
    // Re-declared rather than wildcard-imported: Icarus 11 turns a
    // wildcard-imported name used only in a port connection into an implicit
    // net, and the pinned Yosys 0.68 frontend rejects ``import`` outright.
    localparam [7:0] ERR_NONE        = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_INDEX_RANGE = ot_a3_engine_pkg::ERR_INDEX_RANGE;
    localparam [7:0] ERR_SHAPE       = ot_a3_engine_pkg::ERR_SHAPE;

    localparam [3:0] S_IDLE   = 4'd0;
    localparam [3:0] S_SCAN   = 4'd1;
    localparam [3:0] S_SCAND  = 4'd2;
    localparam [3:0] S_ROWID  = 4'd3;   //: this row's id is in flight
    localparam [3:0] S_DECIDE = 4'd4;
    localparam [3:0] S_LAUNCH = 4'd5;
    localparam [3:0] S_RUN    = 4'd6;
    localparam [3:0] S_ZERO   = 4'd7;   //: the node-shard skip's zero fill
    localparam [3:0] S_NEXT   = 4'd8;
    localparam [3:0] S_DONE   = 4'd9;

    reg [3:0]  state;
    reg [31:0] scan_index;
    reg [1:0]  tail;
    reg [31:0] row;
    reg [31:0] a_row_base;      //: advanced by K, never row*K
    reg [31:0] out_row_base;    //: advanced by N, never row*N
    reg [31:0] zero_col;
    reg [31:0] local_expert;
    reg [31:0] lane_b_base;
    reg        lane_start;
    reg        row_owned;

    //: ONE STAGE, NOT TWO.  ``id_rd_addr`` is registered, so it reaches the port
    //: the cycle after the scan drives it and the memory answers the cycle after
    //: that -- which is exactly when ``scan_v1``, taken from ``id_rd_en``, is
    //: high.  Checking a stage later reads the NEXT id against this index, so
    //: every id but the last is checked twice and the last not at all: the
    //: testbench saw an out-of-bound id accepted with rejected_ids at zero.
    //: Third time this exact off-by-one has appeared on a registered operand
    //: port in this session.
    reg scan_v1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) scan_v1 <= 1'b0;
        else scan_v1 <= id_rd_en;
    end

    wire cfg_bad = (cfg_rows == 16'd0) || (cfg_cols == 16'd0) ||
                   (cfg_depth == 16'd0) ||
                   (cfg_topk != 32'd1) ||
                   (cfg_local_experts == 32'd0) ||
                   (cfg_global_experts < cfg_local_experts) ||
                   (cfg_expert_stride == 32'd0);

    //: One contraction engine, restarted per row against a different expert.
    wire        lane_busy, lane_done;
    wire [7:0]  lane_error;
    wire        lane_out_we;
    wire [31:0] lane_out_addr, lane_out_data;
    wire [31:0] lane_out_count, lane_sat_count, lane_mac_count;

    ot_a3_mac_lane_pipe #(.LANES_IF(LANES_IF)) lane (
        .clk(clk),
        .rst_n(rst_n),
        .start(lane_start),
        .cfg_rows(16'd1),                 //: one row per invocation
        .cfg_cols(cfg_cols),
        .cfg_depth(cfg_depth),
        .cfg_dtype_a(cfg_dtype_a),
        .cfg_dtype_b(cfg_dtype_b),
        .cfg_a_base(cfg_a_base + a_row_base),
        .cfg_b_base(lane_b_base),
        .cfg_out_base(cfg_out_base + out_row_base),
        .a_rd_en(a_rd_en),
        .a_rd_addr(a_rd_addr),
        .a_rd_data(a_rd_data),
        .b_rd_en(b_rd_en),
        .b_rd_addr(b_rd_addr),
        .b_rd_data(b_rd_data),
        .out_we(lane_out_we),
        .out_addr(lane_out_addr),
        .out_data(lane_out_data),
        .busy(lane_busy),
        .done(lane_done),
        .error_code(lane_error),
        .out_count(lane_out_count),
        .saturation_count(lane_sat_count),
        .mac_count(lane_mac_count)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            scan_index <= 32'd0; tail <= 2'd0; row <= 32'd0;
            a_row_base <= 32'd0; out_row_base <= 32'd0; zero_col <= 32'd0;
            local_expert <= 32'd0; lane_b_base <= 32'd0;
            lane_start <= 1'b0; row_owned <= 1'b0;
            id_rd_en <= 1'b0; id_rd_addr <= 32'd0;
            out_we <= 1'b0; out_addr <= 32'd0; out_data <= 32'd0;
            busy <= 1'b0; done <= 1'b0; error_code <= ERR_NONE;
            out_count <= 32'd0; saturation_count <= 32'd0; mac_count <= 32'd0;
            rows_skipped <= 32'd0; rejected_ids <= 32'd0;
        end else begin
            id_rd_en <= 1'b0;
            lane_start <= 1'b0;
            done <= 1'b0;
            //: The lane's writes are this block's writes, except while the skip
            //: is filling zeros.
            out_we <= (state == S_ZERO) ? 1'b1 : lane_out_we;
            if (state != S_ZERO && lane_out_we) begin
                out_addr <= lane_out_addr;
                out_data <= lane_out_data;
                out_count <= out_count + 32'd1;
            end

            if (scan_v1 && (state == S_SCAN || state == S_SCAND)) begin
                if (id_rd_data >= cfg_global_experts)
                    rejected_ids <= rejected_ids + 32'd1;
            end

            case (state)
                S_IDLE: begin
                    if (start) begin
                        scan_index <= 32'd0; tail <= 2'd0; row <= 32'd0;
                        a_row_base <= 32'd0; out_row_base <= 32'd0;
                        out_count <= 32'd0; saturation_count <= 32'd0;
                        mac_count <= 32'd0; rows_skipped <= 32'd0;
                        rejected_ids <= 32'd0;
                        if (cfg_bad) begin
                            error_code <= ERR_SHAPE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            error_code <= ERR_NONE;
                            busy <= 1'b1; state <= S_SCAN;
                        end
                    end
                end
                //: Every ID checked before a single product is formed.
                S_SCAN: begin
                    id_rd_en <= 1'b1;
                    id_rd_addr <= cfg_id_base + scan_index;
                    if (scan_index + 32'd1 >= {16'd0, cfg_rows}) begin
                        tail <= 2'd0; state <= S_SCAND;
                    end else begin
                        scan_index <= scan_index + 32'd1;
                    end
                end
                S_SCAND: begin
                    if (tail >= 2'd2) begin
                        if (rejected_ids != 32'd0) begin
                            error_code <= ERR_INDEX_RANGE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            state <= S_ROWID;
                        end
                    end else begin
                        tail <= tail + 2'd1;
                    end
                end
                S_ROWID: begin
                    id_rd_en <= 1'b1;
                    id_rd_addr <= cfg_id_base + row;
                    tail <= 2'd0;
                    state <= S_DECIDE;
                end
                S_DECIDE: begin
                    if (tail >= 2'd2) begin
                        //: Ownership: this node holds experts
                        //: [expert_base, expert_base + local_experts).
                        row_owned <= (id_rd_data >= cfg_expert_base) &&
                                     (id_rd_data <
                                      cfg_expert_base + cfg_local_experts);
                        local_expert <= id_rd_data - cfg_expert_base;
                        state <= S_LAUNCH;
                    end else begin
                        tail <= tail + 2'd1;
                    end
                end
                S_LAUNCH: begin
                    if (row_owned) begin
                        //: One multiply per ROW, not per element, and registered
                        //: here so it never reaches the contraction's path.
                        lane_b_base <= cfg_b_base +
                                       local_expert * cfg_expert_stride;
                        lane_start <= 1'b1;
                        state <= S_RUN;
                    end else begin
                        rows_skipped <= rows_skipped + 32'd1;
                        zero_col <= 32'd0;
                        state <= S_ZERO;
                    end
                end
                S_RUN: begin
                    if (lane_done) begin
                        saturation_count <= saturation_count + lane_sat_count;
                        mac_count <= mac_count + lane_mac_count;
                        if (lane_error != ERR_NONE) begin
                            error_code <= lane_error;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            state <= S_NEXT;
                        end
                    end
                end
                //: EXACT POSITIVE ZERO across the row this node does not own.
                S_ZERO: begin
                    out_addr <= cfg_out_base + out_row_base + zero_col;
                    out_data <= 32'd0;
                    out_count <= out_count + 32'd1;
                    if (zero_col + 32'd1 >= {16'd0, cfg_cols})
                        state <= S_NEXT;
                    else
                        zero_col <= zero_col + 32'd1;
                end
                S_NEXT: begin
                    if (row + 32'd1 >= {16'd0, cfg_rows}) begin
                        state <= S_DONE;
                    end else begin
                        row <= row + 32'd1;
                        a_row_base <= a_row_base + {16'd0, cfg_depth};
                        out_row_base <= out_row_base + {16'd0, cfg_cols};
                        state <= S_ROWID;
                    end
                end
                S_DONE: begin
                    busy <= 1'b0; done <= 1'b1; state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
