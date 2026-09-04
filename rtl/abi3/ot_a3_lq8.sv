`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// LQ8: LANES format-scaled contraction lanes under one weight stream port
// (docs/CHIP_ARCHITECTURE_DESIGN.md sections 4.2, 4.4 and 11.1; RTL module
// order 11.4 item 2).
//
// The block is LANES instances of rtl/abi3/ot_a3_lane_pipelined.sv, which is
// not modified here, plus the stream control that feeds them:
//
//   weight stream   one word of 2 B x LANES per lane-op cycle (16 B for the
//                   LQ8), read sequentially from cfg_w_base.  Word n carries,
//                   for every lane, the g storage codes of that lane's n-th
//                   lane-op in the lane's own issue order (row, pass of L
//                   interleaved columns, k-group, column within the pass), so
//                   the port's natural sequence is the lanes' consumption
//                   sequence -- the granule rule of section 4.4.  Lane i takes
//                   bits [16 i +: 16]; inside them the codes lie as the lane
//                   lays them out (code j at [j * width +: width]).
//   weight scales   a table of 1 B x LANES per E8M0 code index, read at
//                   cfg_ws_base + the lane's own amendment-A15 index for its
//                   lane-local column; lane i takes byte i.  (Section 4.4
//                   interleaves the scale bytes into the weight stream under a
//                   ROM-plan rule it marks as not yet written; the block keeps
//                   the scales on their own port until that rule exists.)
//   activation      one shared 64-bit operand port and one shared 32-bit
//                   scale port: every lane requests the same activation word
//                   at the same cycle, and the block forwards one request.
//
// Column assignment.  The block computes cfg_cols output columns, cfg_cols a
// multiple of LANES: lane i owns block columns c * LANES + i for its local
// columns c in [0, cfg_cols / LANES).  A pass of L interleaved local columns
// therefore covers L * LANES consecutive block columns, and each lane writes
// its results at lane-local addresses cfg_out_base + row * (cfg_cols / LANES)
// + c on its own output port -- the tile's partial port carries one binary32
// per lane, and the consumer knows which block column each lane holds.
//
// Lockstep.  Every lane receives the same configuration and the same start
// pulse, issues on the same cycles (the lane's only stall, slot_wait, depends
// on the configuration alone) and therefore asks for the same activation word
// and the same scale index in the same cycle.  A lane that faults stops
// issuing and drops out of the request OR; the lanes still running remain in
// lockstep with each other.  The stream pointer advances once per cycle in
// which any lane requests, so word n always meets lane-op n.  The invariant
// is not policed by cells here; the verification top checks it on every
// cycle of every case (rtl/test/a3_lq8_top.sv, lockstep_violations).
//
// Faults.  A lane that traps writes nothing after its faulting pass and
// reports the sequential lane's error class and its own distinct detail
// (gate D5); the other lanes complete their own columns.  The block reports
// the class and detail of the lowest-numbered faulting lane, that lane's
// index, and every lane's class and detail beside them.  A column count that
// is not a multiple of LANES, or a group whose weight codes do not fit the
// 2 B per lane the stream carries, is refused before any lane starts, with
// the block's own detail (DETAIL_BLOCK_COLUMNS, DETAIL_BLOCK_STREAM_WIDTH),
// so it is told apart from every lane-level refusal; a refused operation
// reports zero counters and no lane class (the lanes, never started, still
// hold the previous operation's values and are gated off).
//
// Package constants are referred to by scope, never by wildcard import (OI-43).
// ---------------------------------------------------------------------------
module ot_a3_lq8 #(
    parameter integer LANES        = 8,     // a power of two
    parameter integer ADDER_STAGES = 3,     // L, passed to every lane
    parameter integer ACC_SLOTS    = 8
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [15:0] cfg_rows,           // M
    input  wire [15:0] cfg_cols,           // N over the whole block, a multiple of LANES
    input  wire [15:0] cfg_depth,          // K
    input  wire [7:0]  cfg_dtype_a,
    input  wire [7:0]  cfg_dtype_b,
    input  wire [7:0]  cfg_group,          // g: 1, 2 or 4 products per lane-op
    input  wire [31:0] cfg_a_base,         // activation words (shared)
    input  wire        cfg_scale_a,
    input  wire [15:0] cfg_block_a,
    input  wire [15:0] cfg_block_rows_a,
    input  wire [31:0] cfg_scale_a_base,   // activation E8M0 codes (shared)
    input  wire [31:0] cfg_w_base,         // first weight stream word
    input  wire        cfg_scale_b,
    input  wire [15:0] cfg_block_b,        // weight scale block (elements)
    input  wire [31:0] cfg_ws_base,        // first weight scale table word
    input  wire [31:0] cfg_out_base,       // lane-local output base
    input  wire        cfg_out_fp32,

    // shared activation operand and scale ports (one cycle of read latency)
    output wire        a_rd_en,
    output wire [31:0] a_rd_addr,
    input  wire [63:0] a_rd_data,
    output wire        s_rd_en,
    output wire [31:0] s_rd_addr,
    input  wire [31:0] s_rd_data,

    // weight stream port: 2 B per lane per lane-op, sequential
    output wire        w_rd_en,
    output wire [31:0] w_rd_addr,
    input  wire [16*LANES-1:0] w_rd_data,

    // weight scale table port: 1 B per lane per E8M0 index
    output wire        ws_rd_en,
    output wire [31:0] ws_rd_addr,
    input  wire [8*LANES-1:0] ws_rd_data,

    // per-lane partial ports (lane-local addresses)
    output wire [LANES-1:0]    out_we,
    output wire [32*LANES-1:0] out_addr,
    output wire [32*LANES-1:0] out_data,
    output wire [32*LANES-1:0] out_acc,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,         // lowest faulting lane's class
    output reg  [7:0]  error_detail,       // and its detail
    output reg  [7:0]  error_lane,
    output wire [8*LANES-1:0] lane_error_code,
    output wire [8*LANES-1:0] lane_error_detail,
    output wire [LANES-1:0]   lane_busy,
    output wire [LANES-1:0]   lane_done,
    output wire [LANES-1:0]   op_retire,   // one pulse per lane per retired lane-op
    output reg  [$clog2(LANES+1)-1:0] retire_count,  // lanes retiring this cycle
    output reg  [31:0] out_count,          // sums over the lanes
    output reg  [31:0] saturation_count,
    output reg  [31:0] mac_count,
    output reg  [31:0] product_count
);
    localparam integer LOG_LANES = $clog2(LANES);

    localparam [7:0] ERR_NONE  = ot_a3_lane_pkg::ERR_NONE;
    localparam [7:0] ERR_SHAPE = ot_a3_lane_pkg::ERR_SHAPE;
    localparam [7:0] DETAIL_NONE = ot_a3_lane_pkg::DETAIL_NONE;
    // Block-level details start at 16; 0..12 are the lane's, 13..15 reserved.
    localparam [7:0] DETAIL_BLOCK_COLUMNS      = 8'd16;  // cfg_cols not a multiple of LANES
    localparam [7:0] DETAIL_BLOCK_STREAM_WIDTH = 8'd17;  // g weight codes exceed 2 B per lane-op

    localparam S_IDLE = 1'b0;
    localparam S_RUN  = 1'b1;

    // Elaboration-time guard: the column split is a shift.
    generate
        if ((1 << LOG_LANES) != LANES) begin : gen_lanes_not_power_of_two
            initial begin
                $error("ot_a3_lq8: LANES must be a power of two");
            end
        end
    endgenerate

    wire [15:0] cols_per_lane = cfg_cols >> LOG_LANES;
    wire        cols_ok = (cfg_cols[LOG_LANES-1:0] == {LOG_LANES{1'b0}});
    // The stream carries 2 B of weight per lane per lane-op in every format
    // (section 4.2): g is set by the weight format -- one BF16, two E4M3FN,
    // four E2M1 codes.  A group whose weight codes do not fit is refused here;
    // the lane itself would read zeros for the codes the word cannot hold.
    reg         stream_ok;
    always @* begin
        case (cfg_dtype_b)
            ot_a3_lane_pkg::FMT_MXFP4_E2M1: stream_ok = (cfg_group <= 8'd4);   // 4 x 4 bits
            ot_a3_lane_pkg::FMT_FP8_E4M3FN: stream_ok = (cfg_group <= 8'd2);   // 2 x 8 bits
            default:                        stream_ok = (cfg_group <= 8'd1);   // 1 x 16 bits
        endcase
    end

    // -- lane request buses ------------------------------------------------------
    wire [LANES-1:0]    l_a_en, l_b_en, l_s_en, l_t_en;
    wire [32*LANES-1:0] l_a_addr, l_b_addr, l_s_addr, l_t_addr;
    wire [32*LANES-1:0] l_out_count, l_saturation_count, l_mac_count, l_product_count;
    wire [8*LANES-1:0]  l_error_code, l_error_detail;
    reg                 lane_start;
    reg                 lanes_started;   // the last accepted start reached the lanes
    reg  [31:0]         w_ptr;
    reg  [LANES-1:0]    finished;
    reg                 state;

    genvar gi;
    generate
        for (gi = 0; gi < LANES; gi = gi + 1) begin : gen_lane
            ot_a3_lane_pipelined #(
                .ADDER_STAGES(ADDER_STAGES),
                .ACC_SLOTS(ACC_SLOTS)
            ) u_lane (
                .clk(clk), .rst_n(rst_n),
                .start(lane_start),
                .cfg_rows(cfg_rows), .cfg_cols(cols_per_lane), .cfg_depth(cfg_depth),
                .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b), .cfg_group(cfg_group),
                .cfg_a_base(cfg_a_base), .cfg_b_base(32'b0),
                .cfg_scale_a(cfg_scale_a), .cfg_scale_b(cfg_scale_b),
                .cfg_block_a(cfg_block_a), .cfg_block_b(cfg_block_b),
                .cfg_block_rows_a(cfg_block_rows_a), .cfg_block_rows_b(16'd0),
                .cfg_scale_a_base(cfg_scale_a_base), .cfg_scale_b_base(32'b0),
                .cfg_out_base(cfg_out_base), .cfg_out_fp32(cfg_out_fp32),
                .a_rd_en(l_a_en[gi]), .a_rd_addr(l_a_addr[32*gi +: 32]), .a_rd_data(a_rd_data),
                .b_rd_en(l_b_en[gi]), .b_rd_addr(l_b_addr[32*gi +: 32]),
                .b_rd_data({48'b0, w_rd_data[16*gi +: 16]}),
                .s_rd_en(l_s_en[gi]), .s_rd_addr(l_s_addr[32*gi +: 32]), .s_rd_data(s_rd_data),
                .t_rd_en(l_t_en[gi]), .t_rd_addr(l_t_addr[32*gi +: 32]),
                .t_rd_data({24'b0, ws_rd_data[8*gi +: 8]}),
                .out_we(out_we[gi]), .out_addr(out_addr[32*gi +: 32]),
                .out_data(out_data[32*gi +: 32]), .out_acc(out_acc[32*gi +: 32]),
                .busy(lane_busy[gi]), .done(lane_done[gi]),
                .error_code(l_error_code[8*gi +: 8]),
                .error_detail(l_error_detail[8*gi +: 8]),
                .out_count(l_out_count[32*gi +: 32]),
                .saturation_count(l_saturation_count[32*gi +: 32]),
                .mac_count(l_mac_count[32*gi +: 32]),
                .product_count(l_product_count[32*gi +: 32]),
                .op_retire(op_retire[gi])
            );
        end
    endgenerate

    // The lanes' own weight addresses are not used: the stream is sequential
    // and the scale table is addressed by the selected lane's index below.
    /* verilator lint_off UNUSEDSIGNAL */
    wire [32*LANES-1:0] unused_b_addr = l_b_addr;
    wire [LANES-1:0]    unused_b_en   = l_b_en;
    /* verilator lint_on UNUSEDSIGNAL */

    // -- shared request: the lowest-numbered requesting lane speaks for all ------
    reg         sel_valid;
    reg  [31:0] sel_a_addr, sel_s_addr, sel_t_addr;
    integer     li;
    always @* begin
        sel_valid = 1'b0;
        sel_a_addr = 32'b0;
        sel_s_addr = 32'b0;
        sel_t_addr = 32'b0;
        for (li = LANES - 1; li >= 0; li = li - 1) begin
            if (l_a_en[li]) begin
                sel_valid = 1'b1;
                sel_a_addr = l_a_addr[32*li +: 32];
                sel_s_addr = l_s_addr[32*li +: 32];
                sel_t_addr = l_t_addr[32*li +: 32];
            end
        end
    end

    assign a_rd_en    = sel_valid;
    assign a_rd_addr  = sel_a_addr;
    assign s_rd_en    = sel_valid && cfg_scale_a;
    assign s_rd_addr  = sel_s_addr;
    assign w_rd_en    = sel_valid;
    assign w_rd_addr  = w_ptr;
    assign ws_rd_en   = sel_valid && cfg_scale_b;
    assign ws_rd_addr = cfg_ws_base + sel_t_addr;

    // -- block counters: sums of the lanes' registered counters ------------------
    // The lanes clear their counters and classes only when they are started;
    // after a block-level refusal they still hold the previous operation's
    // values, so everything read from them is gated by lanes_started and a
    // refused operation reports zero counters and no lane class.
    always @* begin
        out_count = 32'b0;
        saturation_count = 32'b0;
        mac_count = 32'b0;
        product_count = 32'b0;
        retire_count = {$clog2(LANES+1){1'b0}};
        for (li = 0; li < LANES; li = li + 1) begin
            out_count = out_count + l_out_count[32*li +: 32];
            saturation_count = saturation_count + l_saturation_count[32*li +: 32];
            mac_count = mac_count + l_mac_count[32*li +: 32];
            product_count = product_count + l_product_count[32*li +: 32];
            retire_count = retire_count + {{($clog2(LANES+1)-1){1'b0}}, op_retire[li]};
        end
        if (!lanes_started) begin
            out_count = 32'b0;
            saturation_count = 32'b0;
            mac_count = 32'b0;
            product_count = 32'b0;
        end
    end
    assign lane_error_code   = lanes_started ? l_error_code   : {8*LANES{1'b0}};
    assign lane_error_detail = lanes_started ? l_error_detail : {8*LANES{1'b0}};

    // -- control ---------------------------------------------------------------------
    wire [LANES-1:0] finished_next = finished | lane_done;
    integer fi;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            lane_start <= 1'b0;
            lanes_started <= 1'b0;
            error_code <= ERR_NONE;
            error_detail <= DETAIL_NONE;
            error_lane <= 8'b0;
            w_ptr <= 32'b0;
            finished <= {LANES{1'b0}};
        end else begin
            done <= 1'b0;
            lane_start <= 1'b0;
            if (sel_valid)
                w_ptr <= w_ptr + 32'd1;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        error_code <= ERR_NONE;
                        error_detail <= DETAIL_NONE;
                        error_lane <= 8'b0;
                        finished <= {LANES{1'b0}};
                        if (!cols_ok) begin
                            error_code <= ERR_SHAPE;
                            error_detail <= DETAIL_BLOCK_COLUMNS;
                            lanes_started <= 1'b0;
                            done <= 1'b1;
                        end else if (!stream_ok) begin
                            error_code <= ERR_SHAPE;
                            error_detail <= DETAIL_BLOCK_STREAM_WIDTH;
                            lanes_started <= 1'b0;
                            done <= 1'b1;
                        end else begin
                            lane_start <= 1'b1;
                            lanes_started <= 1'b1;
                            w_ptr <= cfg_w_base;
                            busy <= 1'b1;
                            state <= S_RUN;
                        end
                    end
                end
                S_RUN: begin
                    finished <= finished_next;
                    if (&finished_next) begin
                        state <= S_IDLE;
                        busy <= 1'b0;
                        done <= 1'b1;
                        // The lanes hold their class and detail until the next
                        // start; report the lowest-numbered faulting lane.
                        for (fi = LANES - 1; fi >= 0; fi = fi - 1) begin
                            if (l_error_code[8*fi +: 8] != ERR_NONE) begin
                                error_code <= l_error_code[8*fi +: 8];
                                error_detail <= l_error_detail[8*fi +: 8];
                                error_lane <= fi[7:0];
                            end
                        end
                    end
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
