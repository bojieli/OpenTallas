`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// T64: the tensor tile -- eight LQ8 blocks, the tile stream sequencer, the
// staging ring, the activation FIFO and the partial port
// (docs/CHIP_ARCHITECTURE_DESIGN.md sections 4.3, 4.4 and 11.1; RTL module
// order 11.4 item 2).
//
// The tile is LQ8S = 8 instances of rtl/abi3/ot_a3_lq8.sv (LANES = 8 each,
// 64 lanes; the LQ8 and the lane are not modified here) under one 128 B/cycle
// weight port, one shared activation port, one weight-scale table port and a
// 64 x binary32 partial port, driven by a tile stream sequencer that runs one
// operation as a static sequence of K-block operations.
//
// Column rule.  Lane (j, i) = LQ8 j, lane i (tile lane 8 j + i) owns tile
// column 8 j + i of every 64-column group c: global column 64 c + 8 j + i.
// LQ8 j therefore computes cfg_cols = 8 x cols_per_lane block columns, its
// local column c * 8 + i being global column 64 c + 8 j + i (the LQ8's own
// rule "lane i owns block columns c * LANES + i", one level up).
//
// The static per-K-block schedule (the tile stream sequencer).  An operation
// is (rows, cols, K) with op_kblock = 128 (B = ceil(K / 128) K-blocks in
// ascending b, the tree's leaf order; a short final block only on unscaled
// formats) or op_kblock = K (the qualification schedule, B = 1).  For each b
// the sequencer starts all eight LQ8s on the same cycle with one identical,
// registered configuration held stable until every LQ8 is done:
//
//   cfg_depth      = min(128, K - 128 b)
//   cfg_a_base     = op_a_base + (b mod 2) x op_a_block_stride       (the FIFO's two slices)
//   cfg_scale_a_base = op_scale_a_base + (b mod 2) x op_scale_a_block_stride
//   cfg_w_base     = the next unread stream word (the stream is contiguous
//                    over K-blocks in the lanes' issue order, so no product
//                    is formed: the sequencer tracks the pointer)
//   cfg_ws_base    = op_ws_base + b x op_ws_block_stride               (accumulated)
//   cfg_out_base   = op_out_base + b x op_out_block_stride             (accumulated)
//   cfg_out_fp32   = 1: the tile emits binary32 partials always; the single
//                    rounding of section 4.3 item 4 lives in the output stage
//
// and waits for the AND of the eight done pulses before the next b.  A
// K-block starts only when the H-tree has delivered its activation slice
// (act_ready_kblocks > b) and, with the staging source, the SDN has filled
// at least half the ring beyond the stream pointer (or the whole remaining
// stream, op_w_words).  Nothing is computed per element: every per-K-block
// quantity is an adder over registered state.
//
// The per-pass quotients (decision, section 13 item 13).  Section 4.4 places
// the per-pass quotients (depth / block on both sides, block mod g, the
// remainder checks) in the tile stream sequencer, delivered to the lanes as
// registered strides.  For T64 v1 they STAY in the lane's multi-cycle
// admission unit as committed at 7a01ce5 (S_ADMIT: a 16-step restoring
// divider, one 17-bit subtract per cycle, never on the issue path), and the
// sequencer owns pass geometry only.  Why: the lane at 7a01ce5 is the only
// closed lane (asap7 6.0 ns) and D1 / groups / LQ8 are proven against it;
// moving the divider changes the lane's port list and invalidates all three
// campaigns and the LQ8 route, so it is a later lane change with its own
// re-run.  What the move would buy is the 16 admission cycles of the ~29
// cycles of per-K-block overhead; the rest (pipeline fill and drain, the
// start / done handshake) stays because the lane samples its configuration
// in S_IDLE and cannot accept the next operation before done.  The overhead
// that matters at N5 L = 1 with MXFP4 (32 issue cycles per K-block) needs
// back-to-back operation issue in the lane (a double-buffered configuration
// and start), not only the divider's relocation; the sequencer already holds
// every per-K-block quantity in registers, so when the lane grows a stride
// interface the sequencer computes cpr / bw once per operation with the same
// divider and S_ADMIT collapses to one cycle.  The T64 campaign MEASURES the
// cycles per K-block rather than quoting the ideal.
//
// Weight port.  WEIGHT_SOURCE = 0: a staging ring of STAGING_BUFFERS x
// STAGING_BYTES bytes (vehicle 2 x 2 KB = 32 words of 128 B; design 2 x
// 16 KB = one pass granule per buffer) written by the store-delivery
// network's write port (stg_wr_*, credit stg_space, in stream-word order)
// and read one word per lane-op cycle; a read of a word the SDN has not yet
// written is a staging underrun, counted and failed closed after the K-block
// (DETAIL_TILE_STAGING_UNDERRUN) because no LQ8 or lane has back-pressure; a
// write beyond the credit is a staging overrun (DETAIL_TILE_STAGING_OVERRUN).
// WEIGHT_SOURCE = 1: the ROM sense stream (rom_rd_*, two 64-B granules per
// cycle, one-cycle latency).  STAGING_IN_TILE = 1 keeps the ring and the
// activation FIFO as flop arrays inside the tile (the vehicle bench);
// STAGING_IN_TILE = 0 keeps them in the top behind stg_rd_* / act_rd_* /
// act_scale_rd_* (the physical build: the design's asap7 staging is a
// memory abstract, section 11.2, and the flop cost is reported separately).
//
// Stream layout (recorded, not chosen here): stream word n carries, for
// every lane, that lane's n-th lane-op in the lane's issue order (row ->
// lane-pass of L interleaved local columns -> k-group -> column within the
// pass), LQ8 j at bits [128 j +: 128], its lane i at [16 i +: 16], code j at
// [j * width +: width]; K-blocks follow each other.  Because a lane
// interleaves L local columns word by word, a 16-KiB pass granule is not a
// contiguous run of stream words when cols_per_lane > 1: the ROM plan's
// pass-granule rule (section 5.1) and the E8M0 scale interleave (section
// 4.4) are unwritten, so the weight scales stay on a table port
// (ws_rd_addr = the LQ8s' shared lane-local A15 index within the K-block's
// slice, byte 8 j + i for lane (j, i)) as in the LQ8.
//
// Activation FIFO.  Two slices of op_a_block_stride words (rows x 128 / g)
// plus two slices of E8M0 codes, written by the operand H-tree's broadcast
// port for K-block b + 1 while K-block b runs; the eight LQ8s' shared,
// lockstep a_rd / s_rd requests read it with one-cycle latency (the
// lowest-numbered requesting LQ8 speaks).  An address outside the FIFO is
// DETAIL_TILE_ACT_RANGE, failed closed after the K-block.
//
// Lockstep is an invariant, not a policed condition: identical
// configuration and one start pulse put the eight LQ8s on the same cycles;
// an LQ8 whose lanes all faulted drops out of the request OR and the
// selection falls through to the next requesting LQ8, exactly as the LQ8
// does per lane.  The verification top checks it on every cycle
// (rtl/test/a3_tile64_top.sv, lockstep_violations).
//
// Faults.  Tile-level refusals (class ERR_SHAPE, decided before K-block 0,
// zero counters): DETAIL_TILE_COLUMNS 18 (cols not a multiple of 64),
// DETAIL_TILE_KBLOCK 19 (op_kblock neither 128 nor K, K = 0, a short final
// block on a scaled format, or a scale block that does not divide 128 --
// i.e. is not a power of two at most 128), DETAIL_TILE_OUT_FORMAT 20
// (op_out_fp32 = 0: the tile emits partials only).  Run-time tile faults
// (class ERR_SHAPE, evaluated when the K-block completes, before any LQ8
// fault of the same block): DETAIL_TILE_STAGING_UNDERRUN 21,
// DETAIL_TILE_ACT_RANGE 22, DETAIL_TILE_STAGING_OVERRUN 23.  An LQ8 or lane
// fault: the running lanes of that K-block finish (the lane's own policy:
// nothing written after a faulting pass), the tile records the class,
// detail, K-block, LQ8 and lane of the lowest-numbered faulting LQ8 (and its
// lowest-numbered faulting lane), keeps every LQ8's and lane's class and
// detail beside them, and starts no later K-block.  The tree (RE8) sits
// outside the tile: the tile emits 64 partials per K-block on the partial
// port and the tree spans tiles.
//
// Package constants are referred to by scope, never by wildcard import (OI-43).
// ---------------------------------------------------------------------------
module ot_a3_tile64 #(
    parameter integer LQ8S            = 8,
    parameter integer LANES           = 8,       // per LQ8
    parameter integer ADDER_STAGES    = 3,
    parameter integer ACC_SLOTS       = 8,
    parameter integer STAGING_BYTES   = 2048,    // per buffer (design 16384)
    parameter integer STAGING_BUFFERS = 2,
    parameter integer STAGING_IN_TILE = 1,       // 1: ring + activation FIFO as flop arrays here; 0: in the top
    parameter integer WEIGHT_SOURCE   = 0,       // 0: staging ring (SDN write port); 1: ROM sense stream
    parameter integer ACT_WORDS       = 2048,    // activation FIFO, 64-bit words (two slices)
    parameter integer ACT_SCALE_WORDS = 64,      // activation E8M0 codes (two slices)
    parameter integer LQ8_ABSTRACT    = 0        // 1: instantiate ot_a3_lq8 without parameter overrides
                                                 //    (the hardened abstract of the BLOCKS flow; its own
                                                 //    defaults are LANES 8, ADDER_STAGES 3, ACC_SLOTS 8)
) (
    input  wire        clk,
    input  wire        rst_n,

    // -- operation descriptor, sampled on op_start ----------------------------------
    input  wire        op_start,
    input  wire [15:0] op_rows,
    input  wire [15:0] op_cols,                 // a multiple of 64
    input  wire [15:0] op_depth,                // K
    input  wire [15:0] op_kblock,               // 128, or K for the qualification schedule
    input  wire [7:0]  op_dtype_a,
    input  wire [7:0]  op_dtype_b,
    input  wire [7:0]  op_group,
    input  wire        op_scale_a,
    input  wire [15:0] op_block_a,
    input  wire [15:0] op_block_rows_a,
    input  wire        op_scale_b,
    input  wire [15:0] op_block_b,
    input  wire [31:0] op_a_base,               // activation FIFO word of slice 0
    input  wire [15:0] op_a_block_stride,       // words per slice = rows x 128 / g
    input  wire [31:0] op_scale_a_base,
    input  wire [15:0] op_scale_a_block_stride,
    input  wire [31:0] op_w_base,               // stream word of the first lane-op
    input  wire [31:0] op_w_words,              // stream words of the whole operation
    input  wire [31:0] op_ws_base,
    input  wire [31:0] op_ws_block_stride,      // scale-table words per K-block = cols_per_lane x 128 / block_b
    input  wire [31:0] op_out_base,
    input  wire [31:0] op_out_block_stride,     // partial words per K-block per lane = rows x cols_per_lane
    input  wire        op_out_fp32,             // must be 1

    // -- weight stream: SDN write port into the staging ring (WEIGHT_SOURCE = 0) ------
    input  wire            stg_wr_en,
    input  wire [31:0]     stg_wr_word,         // stream word index, written in order
    input  wire [16*LQ8S*LANES-1:0] stg_wr_data,
    output wire [15:0]     stg_space,           // free ring words (the SDN's credit)
    output wire [31:0]     stg_fill_word,       // words below this are present
    // external ring read (STAGING_IN_TILE = 0)
    output wire            stg_rd_en,
    output wire [$clog2(STAGING_BUFFERS*STAGING_BYTES/(2*LQ8S*LANES))-1:0] stg_rd_addr,
    input  wire [16*LQ8S*LANES-1:0] stg_rd_data,
    // ROM sense stream (WEIGHT_SOURCE = 1)
    output wire            rom_rd_en,
    output wire [31:0]     rom_rd_addr,
    input  wire [16*LQ8S*LANES-1:0] rom_rd_data,

    // -- weight scale table -----------------------------------------------------------
    output wire            ws_rd_en,
    output wire [31:0]     ws_rd_addr,
    input  wire [8*LQ8S*LANES-1:0] ws_rd_data,  // byte 8 j + i = lane (j, i)'s E8M0 code

    // -- activation broadcast (the H-tree's write port) and readiness ------------------
    input  wire            act_wr_en,
    input  wire [$clog2(ACT_WORDS)-1:0] act_wr_addr,
    input  wire [63:0]     act_wr_data,
    input  wire            act_scale_wr_en,
    input  wire [$clog2(ACT_SCALE_WORDS)-1:0] act_scale_wr_addr,
    input  wire [7:0]      act_scale_wr_data,
    input  wire [15:0]     act_ready_kblocks,   // slices of K-blocks below this are delivered
    // external activation arrays (STAGING_IN_TILE = 0)
    output wire            act_rd_en,
    output wire [$clog2(ACT_WORDS)-1:0] act_rd_addr,
    input  wire [63:0]     act_rd_data,
    output wire            act_scale_rd_en,
    output wire [$clog2(ACT_SCALE_WORDS)-1:0] act_scale_rd_addr,
    input  wire [7:0]      act_scale_rd_data,

    // -- partial port: 64 x binary32 per pass -------------------------------------------
    output wire [LQ8S*LANES-1:0]    part_we,
    output wire [32*LQ8S*LANES-1:0] part_addr,  // lane-local: op_out_base + b x stride + row x cols_per_lane + c
    output wire [32*LQ8S*LANES-1:0] part_data,
    output wire [32*LQ8S*LANES-1:0] part_acc,
    output reg  [15:0]              part_kblock,

    // -- status ------------------------------------------------------------------------
    output reg         busy,
    output reg         done,
    output reg         kblock_active,
    output reg         kblock_done,
    output reg  [15:0] kblock_index,
    output reg  [7:0]  error_code,
    output reg  [7:0]  error_detail,
    output reg  [15:0] error_kblock,
    output reg  [7:0]  error_lq8,
    output reg  [7:0]  error_lane,
    output wire [8*LQ8S-1:0]       lq8_error_code,
    output wire [8*LQ8S-1:0]       lq8_error_detail,
    output wire [8*LQ8S*LANES-1:0] lane_error_code,
    output wire [8*LQ8S*LANES-1:0] lane_error_detail,
    output wire [LQ8S*LANES-1:0]   op_retire,
    output reg  [$clog2(LQ8S*LANES+1)-1:0] retire_count,
    output reg  [31:0] out_count,
    output reg  [31:0] saturation_count,
    output reg  [31:0] mac_count,
    output reg  [31:0] product_count,
    output reg  [31:0] staging_underruns,
    output reg  [31:0] staging_overruns,
    output reg  [31:0] stream_words_consumed
);
    localparam integer TILE_LANES  = LQ8S * LANES;
    localparam integer STREAM_BITS = 16 * TILE_LANES;                  // 1,024: 128 B per stream word
    localparam integer RING_WORDS  = STAGING_BUFFERS * STAGING_BYTES / (STREAM_BITS / 8);
    localparam integer RING_AW     = $clog2(RING_WORDS);
    localparam integer ACT_AW      = $clog2(ACT_WORDS);
    localparam integer ACT_SAW     = $clog2(ACT_SCALE_WORDS);
    localparam integer LOG_LQ8S    = $clog2(LQ8S);
    localparam integer LOG_LANES   = $clog2(LANES);
    localparam integer RC_W        = $clog2(TILE_LANES + 1);

    localparam [7:0] ERR_NONE  = ot_a3_lane_pkg::ERR_NONE;
    localparam [7:0] ERR_SHAPE = ot_a3_lane_pkg::ERR_SHAPE;
    localparam [7:0] DETAIL_NONE = ot_a3_lane_pkg::DETAIL_NONE;
    // Tile-level details 18..23: 0..12 are the lane's, 16..17 the LQ8's, 24..26 the tree's.
    localparam [7:0] DETAIL_TILE_COLUMNS         = 8'd18;
    localparam [7:0] DETAIL_TILE_KBLOCK          = 8'd19;
    localparam [7:0] DETAIL_TILE_OUT_FORMAT      = 8'd20;
    localparam [7:0] DETAIL_TILE_STAGING_UNDERRUN = 8'd21;
    localparam [7:0] DETAIL_TILE_ACT_RANGE       = 8'd22;
    localparam [7:0] DETAIL_TILE_STAGING_OVERRUN = 8'd23;

    localparam [2:0] S_IDLE   = 3'd0;
    localparam [2:0] S_CHECK  = 3'd1;
    localparam [2:0] S_WAIT   = 3'd2;
    localparam [2:0] S_RUN    = 3'd3;
    localparam [2:0] S_FINISH = 3'd4;

    // Elaboration-time guards.
    generate
        if ((1 << LOG_LQ8S) != LQ8S) begin : gen_lq8s_not_power_of_two
            initial $error("ot_a3_tile64: LQ8S must be a power of two");
        end
        if ((1 << LOG_LANES) != LANES) begin : gen_lanes_not_power_of_two
            initial $error("ot_a3_tile64: LANES must be a power of two");
        end
        if ((1 << RING_AW) != RING_WORDS) begin : gen_ring_not_power_of_two
            initial $error("ot_a3_tile64: the staging ring must hold a power of two of stream words");
        end
        if ((LQ8_ABSTRACT != 0) && ((LANES != 8) || (ADDER_STAGES != 3) || (ACC_SLOTS != 8))) begin : gen_abstract_geometry
            initial $error("ot_a3_tile64: the hardened LQ8 abstract is LANES 8, ADDER_STAGES 3, ACC_SLOTS 8");
        end
    endgenerate

    // -- sampled descriptor ------------------------------------------------------------
    reg [15:0] d_rows, d_cols, d_depth, d_kblock, d_block_a, d_block_rows_a, d_block_b;
    reg [15:0] d_a_stride, d_sa_stride;
    reg [7:0]  d_dtype_a, d_dtype_b, d_group;
    reg        d_scale_a, d_scale_b, d_out_fp32;
    reg [31:0] d_a_base, d_sa_base, d_w_base, d_w_end, d_ws_base, d_ws_stride, d_out_base, d_out_stride;

    // -- the sequencer's registered K-block configuration -------------------------------
    reg [2:0]  state;
    reg [15:0] blocks, last_depth;
    reg [15:0] c_depth;
    reg [31:0] c_a_base, c_sa_base, c_w_base, c_ws_base, c_out_base;
    reg        region;                   // b mod 2: the activation FIFO slice
    reg        lq8_start;
    reg        lq8s_started;             // K-block 0 reached the LQ8s in this operation
    reg [LQ8S-1:0] lq8_finished;
    reg        pending;                  // a run-time tile fault waits for the K-block to complete
    reg [7:0]  pending_detail;

    // -- stream bookkeeping -----------------------------------------------------------------
    reg [31:0] fill_word;                // words below this were written by the SDN
    reg [31:0] stream_ptr;               // the next unread stream word

    // -- LQ8 configuration (identical for the eight, held from start to done) --------------
    wire [15:0] cfg_cols_lq8 = d_cols >> LOG_LQ8S;      // 8 x cols_per_lane

    // -- LQ8 request and result buses ------------------------------------------------------
    wire [LQ8S-1:0]          l_a_en, l_s_en, l_w_en, l_ws_en, l_busy, l_done;
    wire [32*LQ8S-1:0]       l_a_addr, l_s_addr, l_w_addr, l_ws_addr;
    wire [8*LQ8S-1:0]        l_error_code, l_error_detail, l_error_lane;
    wire [32*LQ8S-1:0]       l_out_count, l_sat_count, l_mac_count, l_product_count;
    wire [(LOG_LANES+1)*LQ8S-1:0] l_retire_count;
    wire [LANES*LQ8S-1:0]    l_lane_busy, l_lane_done;
    reg  [63:0]              a_data;             // broadcast activation word (one-cycle latency)
    reg  [31:0]              s_data;             // broadcast activation E8M0 code
    wire [STREAM_BITS-1:0]   w_data;             // the stream word (one-cycle latency)

    genvar gj;
    generate
        for (gj = 0; gj < LQ8S; gj = gj + 1) begin : gen_lq8
            if (LQ8_ABSTRACT != 0) begin : gen_abstract
                ot_a3_lq8 u_lq8 (
                    .clk(clk), .rst_n(rst_n),
                    .start(lq8_start),
                    .cfg_rows(d_rows), .cfg_cols(cfg_cols_lq8), .cfg_depth(c_depth),
                    .cfg_dtype_a(d_dtype_a), .cfg_dtype_b(d_dtype_b), .cfg_group(d_group),
                    .cfg_a_base(c_a_base), .cfg_scale_a(d_scale_a),
                    .cfg_block_a(d_block_a), .cfg_block_rows_a(d_block_rows_a),
                    .cfg_scale_a_base(c_sa_base),
                    .cfg_w_base(c_w_base), .cfg_scale_b(d_scale_b), .cfg_block_b(d_block_b),
                    .cfg_ws_base(c_ws_base), .cfg_out_base(c_out_base), .cfg_out_fp32(1'b1),
                    .a_rd_en(l_a_en[gj]), .a_rd_addr(l_a_addr[32*gj +: 32]), .a_rd_data(a_data),
                    .s_rd_en(l_s_en[gj]), .s_rd_addr(l_s_addr[32*gj +: 32]), .s_rd_data(s_data),
                    .w_rd_en(l_w_en[gj]), .w_rd_addr(l_w_addr[32*gj +: 32]),
                    .w_rd_data(w_data[16*LANES*gj +: 16*LANES]),
                    .ws_rd_en(l_ws_en[gj]), .ws_rd_addr(l_ws_addr[32*gj +: 32]),
                    .ws_rd_data(ws_rd_data[8*LANES*gj +: 8*LANES]),
                    .out_we(part_we[LANES*gj +: LANES]), .out_addr(part_addr[32*LANES*gj +: 32*LANES]),
                    .out_data(part_data[32*LANES*gj +: 32*LANES]), .out_acc(part_acc[32*LANES*gj +: 32*LANES]),
                    .busy(l_busy[gj]), .done(l_done[gj]),
                    .error_code(l_error_code[8*gj +: 8]), .error_detail(l_error_detail[8*gj +: 8]),
                    .error_lane(l_error_lane[8*gj +: 8]),
                    .lane_error_code(lane_error_code[8*LANES*gj +: 8*LANES]),
                    .lane_error_detail(lane_error_detail[8*LANES*gj +: 8*LANES]),
                    .lane_busy(l_lane_busy[LANES*gj +: LANES]), .lane_done(l_lane_done[LANES*gj +: LANES]),
                    .op_retire(op_retire[LANES*gj +: LANES]),
                    .retire_count(l_retire_count[(LOG_LANES+1)*gj +: LOG_LANES+1]),
                    .out_count(l_out_count[32*gj +: 32]), .saturation_count(l_sat_count[32*gj +: 32]),
                    .mac_count(l_mac_count[32*gj +: 32]), .product_count(l_product_count[32*gj +: 32])
                );
            end else begin : gen_rtl
                ot_a3_lq8 #(
                    .LANES(LANES),
                    .ADDER_STAGES(ADDER_STAGES),
                    .ACC_SLOTS(ACC_SLOTS)
                ) u_lq8 (
                    .clk(clk), .rst_n(rst_n),
                    .start(lq8_start),
                    .cfg_rows(d_rows), .cfg_cols(cfg_cols_lq8), .cfg_depth(c_depth),
                    .cfg_dtype_a(d_dtype_a), .cfg_dtype_b(d_dtype_b), .cfg_group(d_group),
                    .cfg_a_base(c_a_base), .cfg_scale_a(d_scale_a),
                    .cfg_block_a(d_block_a), .cfg_block_rows_a(d_block_rows_a),
                    .cfg_scale_a_base(c_sa_base),
                    .cfg_w_base(c_w_base), .cfg_scale_b(d_scale_b), .cfg_block_b(d_block_b),
                    .cfg_ws_base(c_ws_base), .cfg_out_base(c_out_base), .cfg_out_fp32(1'b1),
                    .a_rd_en(l_a_en[gj]), .a_rd_addr(l_a_addr[32*gj +: 32]), .a_rd_data(a_data),
                    .s_rd_en(l_s_en[gj]), .s_rd_addr(l_s_addr[32*gj +: 32]), .s_rd_data(s_data),
                    .w_rd_en(l_w_en[gj]), .w_rd_addr(l_w_addr[32*gj +: 32]),
                    .w_rd_data(w_data[16*LANES*gj +: 16*LANES]),
                    .ws_rd_en(l_ws_en[gj]), .ws_rd_addr(l_ws_addr[32*gj +: 32]),
                    .ws_rd_data(ws_rd_data[8*LANES*gj +: 8*LANES]),
                    .out_we(part_we[LANES*gj +: LANES]), .out_addr(part_addr[32*LANES*gj +: 32*LANES]),
                    .out_data(part_data[32*LANES*gj +: 32*LANES]), .out_acc(part_acc[32*LANES*gj +: 32*LANES]),
                    .busy(l_busy[gj]), .done(l_done[gj]),
                    .error_code(l_error_code[8*gj +: 8]), .error_detail(l_error_detail[8*gj +: 8]),
                    .error_lane(l_error_lane[8*gj +: 8]),
                    .lane_error_code(lane_error_code[8*LANES*gj +: 8*LANES]),
                    .lane_error_detail(lane_error_detail[8*LANES*gj +: 8*LANES]),
                    .lane_busy(l_lane_busy[LANES*gj +: LANES]), .lane_done(l_lane_done[LANES*gj +: LANES]),
                    .op_retire(op_retire[LANES*gj +: LANES]),
                    .retire_count(l_retire_count[(LOG_LANES+1)*gj +: LOG_LANES+1]),
                    .out_count(l_out_count[32*gj +: 32]), .saturation_count(l_sat_count[32*gj +: 32]),
                    .mac_count(l_mac_count[32*gj +: 32]), .product_count(l_product_count[32*gj +: 32])
                );
            end
        end
    endgenerate

    /* verilator lint_off UNUSEDSIGNAL */
    wire [LQ8S-1:0]       unused_l_busy = l_busy;
    wire [LANES*LQ8S-1:0] unused_lane_busy = l_lane_busy;
    wire [LANES*LQ8S-1:0] unused_lane_done = l_lane_done;
    /* verilator lint_on UNUSEDSIGNAL */

    // The LQ8s' own classes are gated by the tile's started flag: after a
    // tile-level refusal they still hold the previous operation's values.
    assign lq8_error_code   = lq8s_started ? l_error_code   : {8*LQ8S{1'b0}};
    assign lq8_error_detail = lq8s_started ? l_error_detail : {8*LQ8S{1'b0}};

    // -- shared requests: the lowest-numbered requesting LQ8 speaks -------------------------
    reg         sel_a_valid, sel_w_valid, sel_ws_valid, sel_s_valid;
    reg  [31:0] sel_a_addr, sel_s_addr, sel_w_addr, sel_ws_addr;
    integer     li;
    always @* begin
        sel_a_valid = 1'b0;
        sel_s_valid = 1'b0;
        sel_w_valid = 1'b0;
        sel_ws_valid = 1'b0;
        sel_a_addr = 32'b0;
        sel_s_addr = 32'b0;
        sel_w_addr = 32'b0;
        sel_ws_addr = 32'b0;
        for (li = LQ8S - 1; li >= 0; li = li - 1) begin
            if (l_a_en[li]) begin
                sel_a_valid = 1'b1;
                sel_a_addr = l_a_addr[32*li +: 32];
            end
            if (l_s_en[li]) begin
                sel_s_valid = 1'b1;
                sel_s_addr = l_s_addr[32*li +: 32];
            end
            if (l_w_en[li]) begin
                sel_w_valid = 1'b1;
                sel_w_addr = l_w_addr[32*li +: 32];
            end
            if (l_ws_en[li]) begin
                sel_ws_valid = 1'b1;
                sel_ws_addr = l_ws_addr[32*li +: 32];
            end
        end
    end

    assign ws_rd_en   = sel_ws_valid;
    assign ws_rd_addr = sel_ws_addr;

    // -- the weight stream ----------------------------------------------------------------------
    wire        w_underrun = sel_w_valid && (WEIGHT_SOURCE == 0) && (sel_w_addr >= fill_word);
    wire [31:0] occupancy  = (fill_word > stream_ptr) ? (fill_word - stream_ptr) : 32'b0;
    wire        wr_overrun = stg_wr_en && (WEIGHT_SOURCE == 0) &&
                             (stg_wr_word >= stream_ptr) && ((stg_wr_word - stream_ptr) >= RING_WORDS);
    wire [15:0] ring_words16 = RING_WORDS;
    assign stg_space     = (occupancy >= RING_WORDS) ? 16'd0 : (ring_words16 - occupancy[15:0]);
    assign stg_fill_word = fill_word;
    assign rom_rd_en     = (WEIGHT_SOURCE != 0) && sel_w_valid;
    assign rom_rd_addr   = sel_w_addr;
    assign stg_rd_en     = (WEIGHT_SOURCE == 0) && (STAGING_IN_TILE == 0) && sel_w_valid;
    assign stg_rd_addr   = sel_w_addr[RING_AW-1:0];
    assign act_rd_en        = (STAGING_IN_TILE == 0) && sel_a_valid;
    assign act_rd_addr      = sel_a_addr[ACT_AW-1:0];
    assign act_scale_rd_en  = (STAGING_IN_TILE == 0) && sel_s_valid;
    assign act_scale_rd_addr = sel_s_addr[ACT_SAW-1:0];

    wire act_range = (sel_a_valid && (sel_a_addr >= ACT_WORDS)) ||
                     (sel_s_valid && (sel_s_addr >= ACT_SCALE_WORDS));

    generate
        if (WEIGHT_SOURCE != 0) begin : gen_rom_source
            assign w_data = rom_rd_data;
            /* verilator lint_off UNUSEDSIGNAL */
            wire [STREAM_BITS-1:0] unused_stg_wr = stg_wr_data;
            wire [STREAM_BITS-1:0] unused_stg_rd = stg_rd_data;
            /* verilator lint_on UNUSEDSIGNAL */
        end else if (STAGING_IN_TILE != 0) begin : gen_ring_in_tile
            reg [STREAM_BITS-1:0] ring [0:RING_WORDS-1];
            reg [STREAM_BITS-1:0] ring_data;
            integer ri;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    for (ri = 0; ri < RING_WORDS; ri = ri + 1)
                        ring[ri] <= {STREAM_BITS{1'b0}};
                    ring_data <= {STREAM_BITS{1'b0}};
                end else begin
                    if (stg_wr_en)
                        ring[stg_wr_word[RING_AW-1:0]] <= stg_wr_data;
                    if (sel_w_valid)
                        ring_data <= ring[sel_w_addr[RING_AW-1:0]];
                end
            end
            assign w_data = ring_data;
            /* verilator lint_off UNUSEDSIGNAL */
            wire [STREAM_BITS-1:0] unused_stg_rd = stg_rd_data;
            wire [STREAM_BITS-1:0] unused_rom_rd = rom_rd_data;
            /* verilator lint_on UNUSEDSIGNAL */
        end else begin : gen_ring_in_top
            assign w_data = stg_rd_data;
            /* verilator lint_off UNUSEDSIGNAL */
            wire [STREAM_BITS-1:0] unused_stg_wr = stg_wr_data;
            wire [STREAM_BITS-1:0] unused_rom_rd = rom_rd_data;
            /* verilator lint_on UNUSEDSIGNAL */
        end
    endgenerate

    // -- the activation FIFO ----------------------------------------------------------------------
    generate
        if (STAGING_IN_TILE != 0) begin : gen_act_in_tile
            reg [63:0] act_mem [0:ACT_WORDS-1];
            reg [7:0]  act_scale_mem [0:ACT_SCALE_WORDS-1];
            integer ai;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    for (ai = 0; ai < ACT_WORDS; ai = ai + 1)
                        act_mem[ai] <= 64'b0;
                    for (ai = 0; ai < ACT_SCALE_WORDS; ai = ai + 1)
                        act_scale_mem[ai] <= 8'b0;
                    a_data <= 64'b0;
                    s_data <= 32'b0;
                end else begin
                    if (act_wr_en)
                        act_mem[act_wr_addr] <= act_wr_data;
                    if (act_scale_wr_en)
                        act_scale_mem[act_scale_wr_addr] <= act_scale_wr_data;
                    if (sel_a_valid)
                        a_data <= act_mem[sel_a_addr[ACT_AW-1:0]];
                    if (sel_s_valid)
                        s_data <= {24'b0, act_scale_mem[sel_s_addr[ACT_SAW-1:0]]};
                end
            end
            /* verilator lint_off UNUSEDSIGNAL */
            wire [63:0] unused_act_rd = act_rd_data;
            wire [7:0]  unused_act_scale_rd = act_scale_rd_data;
            /* verilator lint_on UNUSEDSIGNAL */
        end else begin : gen_act_in_top
            always @* begin
                a_data = act_rd_data;
                s_data = {24'b0, act_scale_rd_data};
            end
            /* verilator lint_off UNUSEDSIGNAL */
            wire        unused_act_wr_en = act_wr_en;
            wire [ACT_AW-1:0] unused_act_wr_addr = act_wr_addr;
            wire [63:0] unused_act_wr_data = act_wr_data;
            wire        unused_act_scale_wr_en = act_scale_wr_en;
            wire [ACT_SAW-1:0] unused_act_scale_wr_addr = act_scale_wr_addr;
            wire [7:0]  unused_act_scale_wr_data = act_scale_wr_data;
            /* verilator lint_on UNUSEDSIGNAL */
        end
    endgenerate

    // -- per-cycle retire count and the K-block's counters ------------------------------------------
    reg [31:0] blk_out, blk_sat, blk_mac, blk_product;
    integer ci;
    always @* begin
        retire_count = {RC_W{1'b0}};
        blk_out = 32'b0;
        blk_sat = 32'b0;
        blk_mac = 32'b0;
        blk_product = 32'b0;
        for (ci = 0; ci < LQ8S; ci = ci + 1) begin
            retire_count = retire_count + {{(RC_W-LOG_LANES-1){1'b0}}, l_retire_count[(LOG_LANES+1)*ci +: LOG_LANES+1]};
            blk_out = blk_out + l_out_count[32*ci +: 32];
            blk_sat = blk_sat + l_sat_count[32*ci +: 32];
            blk_mac = blk_mac + l_mac_count[32*ci +: 32];
            blk_product = blk_product + l_product_count[32*ci +: 32];
        end
    end

    // -- admission (S_CHECK), from the sampled descriptor ------------------------------------------
    function automatic divides_128;
        input [15:0] block;
        begin
            divides_128 = (block != 16'd0) && ((block & (block - 16'd1)) == 16'd0) && (block <= 16'd128);
        end
    endfunction
    wire        cols_ok   = (d_cols != 16'd0) && (d_cols[LOG_LQ8S+LOG_LANES-1:0] == {(LOG_LQ8S+LOG_LANES){1'b0}});
    wire        short_tail = (d_depth[6:0] != 7'd0);
    wire        kblock_128 = (d_kblock == 16'd128);
    wire        kblock_k   = (d_kblock == d_depth);
    wire        kblock_ok  = (d_depth != 16'd0) &&
                             (kblock_k ||
                              (kblock_128 && !(short_tail && (d_scale_a || d_scale_b)) &&
                               (!d_scale_a || divides_128(d_block_a)) &&
                               (!d_scale_b || divides_128(d_block_b))));
    wire [15:0] blocks_128 = (d_depth + 16'd127) >> 7;
    wire [15:0] tail_depth = short_tail ? {9'b0, d_depth[6:0]} : 16'd128;

    // -- readiness (S_WAIT) --------------------------------------------------------------------------
    wire [31:0] half_ahead   = stream_ptr + RING_WORDS / 2;
    wire [31:0] fill_target  = (half_ahead < d_w_end) ? half_ahead : d_w_end;
    wire        fill_ok      = (WEIGHT_SOURCE != 0) || (fill_word >= fill_target);
    wire        act_ok       = (act_ready_kblocks > kblock_index);
    wire        all_finished = &(lq8_finished | l_done);
    wire        last_block   = (kblock_index + 16'd1 == blocks);

    // -- the sequencer --------------------------------------------------------------------------------
    integer fi;
    reg     any_lq8_fault;
    always @* begin
        any_lq8_fault = 1'b0;
        for (fi = 0; fi < LQ8S; fi = fi + 1)
            if (l_error_code[8*fi +: 8] != ERR_NONE)
                any_lq8_fault = 1'b1;
    end
    integer fj;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            kblock_active <= 1'b0;
            kblock_done <= 1'b0;
            kblock_index <= 16'b0;
            part_kblock <= 16'b0;
            error_code <= ERR_NONE;
            error_detail <= DETAIL_NONE;
            error_kblock <= 16'b0;
            error_lq8 <= 8'b0;
            error_lane <= 8'b0;
            out_count <= 32'b0;
            saturation_count <= 32'b0;
            mac_count <= 32'b0;
            product_count <= 32'b0;
            staging_underruns <= 32'b0;
            staging_overruns <= 32'b0;
            stream_words_consumed <= 32'b0;
            d_rows <= 16'b0; d_cols <= 16'b0; d_depth <= 16'b0; d_kblock <= 16'b0;
            d_block_a <= 16'b0; d_block_rows_a <= 16'b0; d_block_b <= 16'b0;
            d_a_stride <= 16'b0; d_sa_stride <= 16'b0;
            d_dtype_a <= 8'b0; d_dtype_b <= 8'b0; d_group <= 8'b0;
            d_scale_a <= 1'b0; d_scale_b <= 1'b0; d_out_fp32 <= 1'b0;
            d_a_base <= 32'b0; d_sa_base <= 32'b0; d_w_base <= 32'b0; d_w_end <= 32'b0;
            d_ws_base <= 32'b0; d_ws_stride <= 32'b0; d_out_base <= 32'b0; d_out_stride <= 32'b0;
            blocks <= 16'b0;
            last_depth <= 16'b0;
            c_depth <= 16'b0;
            c_a_base <= 32'b0; c_sa_base <= 32'b0; c_w_base <= 32'b0; c_ws_base <= 32'b0; c_out_base <= 32'b0;
            region <= 1'b0;
            lq8_start <= 1'b0;
            lq8s_started <= 1'b0;
            lq8_finished <= {LQ8S{1'b0}};
            pending <= 1'b0;
            pending_detail <= DETAIL_NONE;
            fill_word <= 32'b0;
            stream_ptr <= 32'b0;
        end else begin
            done <= 1'b0;
            kblock_done <= 1'b0;
            lq8_start <= 1'b0;

            // -- stream bookkeeping, every cycle ------------------------------------------
            if (stg_wr_en && (WEIGHT_SOURCE == 0)) begin
                fill_word <= stg_wr_word + 32'd1;
                if (wr_overrun) begin
                    staging_overruns <= staging_overruns + 32'd1;
                    if (!pending) begin
                        pending <= 1'b1;
                        pending_detail <= DETAIL_TILE_STAGING_OVERRUN;
                    end
                end
            end
            if (sel_w_valid) begin
                stream_ptr <= sel_w_addr + 32'd1;
                stream_words_consumed <= stream_words_consumed + 32'd1;
                if (w_underrun) begin
                    staging_underruns <= staging_underruns + 32'd1;
                    if (!pending) begin
                        pending <= 1'b1;
                        pending_detail <= DETAIL_TILE_STAGING_UNDERRUN;
                    end
                end
            end
            if (act_range && !pending) begin
                pending <= 1'b1;
                pending_detail <= DETAIL_TILE_ACT_RANGE;
            end

            case (state)
                S_IDLE: begin
                    if (op_start) begin
                        d_rows <= op_rows; d_cols <= op_cols; d_depth <= op_depth; d_kblock <= op_kblock;
                        d_dtype_a <= op_dtype_a; d_dtype_b <= op_dtype_b; d_group <= op_group;
                        d_scale_a <= op_scale_a; d_block_a <= op_block_a; d_block_rows_a <= op_block_rows_a;
                        d_scale_b <= op_scale_b; d_block_b <= op_block_b;
                        d_a_base <= op_a_base; d_a_stride <= op_a_block_stride;
                        d_sa_base <= op_scale_a_base; d_sa_stride <= op_scale_a_block_stride;
                        d_w_base <= op_w_base; d_w_end <= op_w_base + op_w_words;
                        d_ws_base <= op_ws_base; d_ws_stride <= op_ws_block_stride;
                        d_out_base <= op_out_base; d_out_stride <= op_out_block_stride;
                        d_out_fp32 <= op_out_fp32;
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        error_detail <= DETAIL_NONE;
                        error_kblock <= 16'b0;
                        error_lq8 <= 8'b0;
                        error_lane <= 8'b0;
                        out_count <= 32'b0;
                        saturation_count <= 32'b0;
                        mac_count <= 32'b0;
                        product_count <= 32'b0;
                        staging_underruns <= 32'b0;
                        staging_overruns <= 32'b0;
                        stream_words_consumed <= 32'b0;
                        kblock_index <= 16'b0;
                        part_kblock <= 16'b0;
                        lq8s_started <= 1'b0;
                        pending <= 1'b0;
                        pending_detail <= DETAIL_NONE;
                        // The operation's stream begins at op_w_base; the SDN writes it
                        // after op_start, so nothing before counts as present.
                        fill_word <= op_w_base;
                        stream_ptr <= op_w_base;
                        state <= S_CHECK;
                    end
                end

                S_CHECK: begin
                    if (!cols_ok) begin
                        error_code <= ERR_SHAPE;
                        error_detail <= DETAIL_TILE_COLUMNS;
                        state <= S_FINISH;
                    end else if (!kblock_ok) begin
                        error_code <= ERR_SHAPE;
                        error_detail <= DETAIL_TILE_KBLOCK;
                        state <= S_FINISH;
                    end else if (!d_out_fp32) begin
                        error_code <= ERR_SHAPE;
                        error_detail <= DETAIL_TILE_OUT_FORMAT;
                        state <= S_FINISH;
                    end else begin
                        blocks <= kblock_k ? 16'd1 : blocks_128;
                        last_depth <= kblock_k ? d_depth : tail_depth;
                        c_depth <= kblock_k ? d_depth : ((blocks_128 == 16'd1) ? tail_depth : 16'd128);
                        c_a_base <= d_a_base;
                        c_sa_base <= d_sa_base;
                        c_w_base <= d_w_base;
                        c_ws_base <= d_ws_base;
                        c_out_base <= d_out_base;
                        region <= 1'b0;
                        state <= S_WAIT;
                    end
                end

                S_WAIT: begin
                    if (act_ok && fill_ok) begin
                        lq8_start <= 1'b1;
                        lq8s_started <= 1'b1;
                        lq8_finished <= {LQ8S{1'b0}};
                        kblock_active <= 1'b1;
                        state <= S_RUN;
                    end
                end

                S_RUN: begin
                    lq8_finished <= lq8_finished | l_done;
                    if (all_finished) begin
                        out_count <= out_count + blk_out;
                        saturation_count <= saturation_count + blk_sat;
                        mac_count <= mac_count + blk_mac;
                        product_count <= product_count + blk_product;
                        kblock_done <= 1'b1;
                        kblock_active <= 1'b0;
                        for (fj = LQ8S - 1; fj >= 0; fj = fj - 1) begin
                            if (l_error_code[8*fj +: 8] != ERR_NONE) begin
                                error_code <= l_error_code[8*fj +: 8];
                                error_detail <= l_error_detail[8*fj +: 8];
                                error_kblock <= kblock_index;
                                error_lq8 <= fj[7:0];
                                error_lane <= l_error_lane[8*fj +: 8];
                            end
                        end
                        if (pending) begin
                            // A tile-level fault of this K-block is the root cause and is
                            // reported before any LQ8 fault of the same K-block.
                            error_code <= ERR_SHAPE;
                            error_detail <= pending_detail;
                            error_kblock <= kblock_index;
                            error_lq8 <= 8'b0;
                            error_lane <= 8'b0;
                        end
                        if (pending || any_lq8_fault || last_block) begin
                            state <= S_FINISH;
                        end else begin
                            kblock_index <= kblock_index + 16'd1;
                            part_kblock <= kblock_index + 16'd1;
                            region <= ~region;
                            c_depth <= (kblock_index + 16'd2 == blocks) ? last_depth : 16'd128;
                            c_a_base <= region ? d_a_base : (d_a_base + {16'b0, d_a_stride});
                            c_sa_base <= region ? d_sa_base : (d_sa_base + {16'b0, d_sa_stride});
                            c_w_base <= stream_ptr;
                            c_ws_base <= c_ws_base + d_ws_stride;
                            c_out_base <= c_out_base + d_out_stride;
                            state <= S_WAIT;
                        end
                    end
                end

                S_FINISH: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
