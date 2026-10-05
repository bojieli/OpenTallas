`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// PC64: the partial collector -- the block between ot_a3_tile64's partial
// port and ot_a3_tree_endpoint_fp32's leaf port
// (docs/CHIP_ARCHITECTURE_DESIGN.md sections 3.6, 4.4 and 13 item 13).
//
// Why it exists.  results/rtl/abi3_boundary_chain.json established by
// elaboration -- not by reading source -- that nothing drives the endpoint's
// in_valid / in_leaf / in_leaf_count / in_tag from a tile's partial port:
// part_we is an internal net of the T64 vehicle and the endpoint's leaf port
// is a top-level input the checkers drive from captured partials.  The
// dependent chain of section 13 item 13 therefore had a missing term, and
// this is that term, designed rather than improvised for a measurement.
//
// What it does.  The K-block tree of the adopted association combines the
// block partials P_0 .. P_{B-1} of ONE output element by PAIRWISE_TREE over
// ascending block index (rtl/abi3/ot_a3_tree_endpoint_fp32.sv; item 2 of
// AM-E1).  The tile emits those partials the other way round: one K-block at
// a time, 64 lanes wide, over B passes.  The collector transposes the two --
// it captures every lane's partial into a per-lane leaf buffer indexed by
// K-block, and when the LAST K-block has written an element it presents that
// element's B leaves to the endpoint as one aligned leaf vector, in ascending
// block index, one vector per cycle.  That is the endpoint's own leaf order
// and its own rate (RE8 accepts one leaf vector per cycle,
// results/rtl/abi3_re8.json).
//
// The buffer is the endpoint's.  Section 4.4 allocates "two RE8 endpoints per
// eight-tile cluster, each with 4 KiB buffering"; TILE_LANES x SLOT_ELEMS x
// LEAVES x 4 B is that buffer, and the vehicle's 64 x 2 x 8 x 4 B = 4,096 B is
// exactly it.  A window wider than SLOT_ELEMS elements per lane does not fit
// and is REFUSED (DETAIL_COLLECT_WINDOW) rather than silently wrapped: the
// buffer is a sized resource of the design and the collector may not pretend
// otherwise.  B > LEAVES is likewise refused (DETAIL_COLLECT_BLOCKS): a
// deeper reduction is the chained upper tree of section 4.4, whose stages the
// engine controller composes out of further endpoints, and inventing a
// chaining rule here would be a design decision made inside a measurement.
//
// Addressing, from the tile's own rule.  The tile writes lane-local
//   part_addr = op_out_base + b x op_out_block_stride + row x cols_per_lane + c
// with op_out_block_stride = rows x cols_per_lane = the element window.  So
// with cfg_out_base = op_out_base and cfg_elems = the window, the element is
//   e = part_addr - (cfg_out_base + part_kblock x cfg_elems)
// and part_kblock -- a tile output register, one value for all 64 lanes -- is
// the leaf index.  One multiplier serves all 64 lanes because the K-block is
// shared; the per-lane work is a subtract and a range check.  Each lane owns a
// disjoint slice of the buffer (slot = lane x cfg_elems + e), so the buffer is
// 64 independent single-write-port arrays, not a 64-ported memory.
//
// Emission order and the tag.  Slots are emitted in ascending (lane, element)
// order and the tag is the emission index, so tags are dense and ascending and
// -- at the tile's decode geometry, cols = 64 and cols_per_lane = 1 -- the tag
// IS the output column, which is what the consumer's operand receiver needs.
// The endpoint returns the tag with the root (its in_tag is documented as a
// "column / pass identifier"), so the root arrives at the receiver already
// carrying the element it belongs to.  The K-block cannot be the tag of a
// vector that spans every K-block; what carries the K-block is the leaf INDEX,
// which is the tree's leaf order and is the thing the endpoint's association
// depends on.  For a chained upper stage the same rule applies one level up
// and the group index is the tag; that stage is not built here.
//
// Fail-closed, sticky, and in input order (the endpoint's policy, one level
// down).  Classes are ot_a3_lane_pkg's; details continue the family's
// numbering (0..12 lane, 16..17 LQ8, 18..23 tile, 24..26 tree):
//   27 DETAIL_COLLECT_BLOCKS      cfg_blocks 0 or above LEAVES
//   28 DETAIL_COLLECT_WINDOW      cfg_elems 0 or above SLOT_ELEMS
//   29 DETAIL_COLLECT_ADDR        a partial outside its K-block's window
//   30 DETAIL_COLLECT_KBLOCK      part_kblock at or above cfg_blocks
//   31 DETAIL_COLLECT_DUPLICATE   the same (element, K-block) leaf written twice
//   32 DETAIL_COLLECT_INCOMPLETE  a slot became ready without all B leaves
// A fault stops emission, holds error_* until clear, and ignores input; the
// lowest-numbered faulting lane is the one reported, as the tile reports the
// lowest-numbered faulting LQ8.
//
// Package constants are referred to by scope, never by wildcard import (OI-43).
// ---------------------------------------------------------------------------
module ot_a3_partial_collector #(
    parameter integer TILE_LANES = 64,   // the tile's lanes: LQ8S x LANES
    parameter integer LEAVES     = 8,    // the endpoint's leaf count; B <= LEAVES
    parameter integer SLOT_ELEMS = 2,    // leaf slots per lane; the 4 KiB buffer of section 4.4
    parameter integer TAG_W      = 16
) (
    input  wire        clk,
    input  wire        rst_n,

    // -- configuration, sampled on cfg_start (the tile's own operation descriptor) ----
    input  wire        cfg_start,
    input  wire [15:0] cfg_blocks,       // B: K-blocks of the producing operation
    input  wire [15:0] cfg_elems,        // op_out_block_stride = rows x cols_per_lane
    input  wire [31:0] cfg_out_base,     // op_out_base
    input  wire        clear,            // restart after a fault

    // -- the producer tile's partial port -----------------------------------------------
    input  wire [TILE_LANES-1:0]    part_we,
    input  wire [32*TILE_LANES-1:0] part_addr,
    input  wire [32*TILE_LANES-1:0] part_data,
    input  wire [15:0]              part_kblock,

    // -- the endpoint's leaf port ---------------------------------------------------------
    output reg                  out_valid,
    output reg  [3:0]           out_leaf_count,
    output reg  [32*LEAVES-1:0] out_leaf,
    output reg  [TAG_W-1:0]     out_tag,
    output reg                  out_last,

    // -- status ----------------------------------------------------------------------------
    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [7:0]  error_detail,
    output reg  [15:0] error_lane,
    output reg  [31:0] error_slot,
    output reg  [31:0] captured_count,   // partials captured
    output reg  [31:0] vectors_count     // leaf vectors emitted
);
    localparam integer LOG_LEAVES = (LEAVES > 1) ? $clog2(LEAVES) : 1;
    localparam integer LANE_AW    = (TILE_LANES > 1) ? $clog2(TILE_LANES) : 1;
    localparam integer ELEM_AW    = (SLOT_ELEMS > 1) ? $clog2(SLOT_ELEMS) : 1;
    localparam integer VEC_BITS   = 32 * LEAVES;

    localparam [7:0] ERR_NONE  = ot_a3_lane_pkg::ERR_NONE;
    localparam [7:0] ERR_SHAPE = ot_a3_lane_pkg::ERR_SHAPE;
    localparam [7:0] DETAIL_NONE = ot_a3_lane_pkg::DETAIL_NONE;
    localparam [7:0] DETAIL_COLLECT_BLOCKS     = 8'd27;
    localparam [7:0] DETAIL_COLLECT_WINDOW     = 8'd28;
    localparam [7:0] DETAIL_COLLECT_ADDR       = 8'd29;
    localparam [7:0] DETAIL_COLLECT_KBLOCK     = 8'd30;
    localparam [7:0] DETAIL_COLLECT_DUPLICATE  = 8'd31;
    localparam [7:0] DETAIL_COLLECT_INCOMPLETE = 8'd32;

    // Elaboration-time guards.
    generate
        if ((1 << LOG_LEAVES) != LEAVES) begin : gen_leaves_not_power_of_two
            initial $error("ot_a3_partial_collector: LEAVES must be a power of two");
        end
        if ((1 << LANE_AW) != TILE_LANES) begin : gen_lanes_not_power_of_two
            initial $error("ot_a3_partial_collector: TILE_LANES must be a power of two");
        end
        if (LEAVES > 15) begin : gen_leaf_count_width
            initial $error("ot_a3_partial_collector: the endpoint's in_leaf_count is four bits");
        end
    endgenerate

    // A LEAVES-bit prefix mask of ``count`` ones, with count = LEAVES safe.
    function automatic [LEAVES-1:0] prefix_mask;
        input [15:0] count;
        reg [LEAVES:0] one;
        begin
            one = {{LEAVES{1'b0}}, 1'b1};
            prefix_mask = (count >= LEAVES) ? {LEAVES{1'b1}}
                                            : ((one << count[LOG_LEAVES-1:0]) - one);
        end
    endfunction

    // -- sampled configuration -----------------------------------------------------------
    reg [15:0] d_blocks, d_elems;
    reg [31:0] d_out_base;
    reg [LEAVES-1:0] full_mask;          // (1 << B) - 1: the leaves a complete slot holds
    reg [15:0] last_block;               // B - 1

    reg  running;                        // capturing and emitting
    wire wipe = cfg_start;

    // -- one multiplier for the whole tile: the K-block is shared ------------------------
    wire [31:0] blk_base   = d_out_base + (part_kblock * {16'b0, d_elems});
    wire        kblock_bad = running && (part_kblock >= d_blocks);
    wire        is_last_block = (part_kblock == last_block);

    // -- per-lane capture decode ----------------------------------------------------------
    wire [TILE_LANES-1:0]     cap;         // this lane presents a partial
    wire [TILE_LANES-1:0]     addr_bad;
    wire [TILE_LANES-1:0]     dup;
    wire [32*TILE_LANES-1:0]  off;
    wire [TILE_LANES*SLOT_ELEMS-1:0] ready_flat;
    wire [VEC_BITS*TILE_LANES-1:0]   leaf_bus;
    wire [LEAVES*TILE_LANES-1:0]     have_bus;

    // -- the emission scanner --------------------------------------------------------------
    reg [LANE_AW-1:0] scan_lane;
    reg [15:0]        scan_e;
    reg [31:0]        emit_index;
    reg [31:0]        remaining;

    wire [31:0] scan_pos = ({{(32-LANE_AW){1'b0}}, scan_lane} * SLOT_ELEMS) + {16'b0, scan_e};
    wire        scan_ready = running && (remaining != 32'b0) && ready_flat[scan_pos];
    wire [31:0] leaf_off = {{(32-LANE_AW){1'b0}}, scan_lane} * VEC_BITS;
    wire [31:0] have_off = {{(32-LANE_AW){1'b0}}, scan_lane} * LEAVES;
    wire [VEC_BITS-1:0] sel_leaf = leaf_bus[leaf_off +: VEC_BITS];
    wire [LEAVES-1:0]   sel_have = have_bus[have_off +: LEAVES];
    wire                complete = (sel_have == full_mask);

    // -- fault arbitration: the lowest-numbered faulting lane -------------------------------
    reg         f_any;
    reg  [7:0]  f_detail;
    reg  [15:0] f_lane;
    reg  [31:0] f_slot;
    integer     fi;
    always @* begin
        f_any = 1'b0;
        f_detail = DETAIL_NONE;
        f_lane = 16'b0;
        f_slot = 32'b0;
        for (fi = TILE_LANES - 1; fi >= 0; fi = fi - 1) begin
            if (cap[fi]) begin
                if (kblock_bad) begin
                    f_any = 1'b1; f_detail = DETAIL_COLLECT_KBLOCK;
                    f_lane = fi[15:0]; f_slot = {16'b0, part_kblock};
                end else if (addr_bad[fi]) begin
                    f_any = 1'b1; f_detail = DETAIL_COLLECT_ADDR;
                    f_lane = fi[15:0]; f_slot = off[32*fi +: 32];
                end else if (dup[fi]) begin
                    f_any = 1'b1; f_detail = DETAIL_COLLECT_DUPLICATE;
                    f_lane = fi[15:0]; f_slot = off[32*fi +: 32];
                end
            end
        end
    end
    wire capture_fault = running && f_any;
    wire emit_fault    = scan_ready && !complete;
    wire emit_now      = scan_ready && complete && !capture_fault;

    // -- the emitting lane, decoded once for the per-lane ready clear -----------------------
    wire [LANE_AW-1:0] emit_lane = scan_lane;
    wire [15:0]        emit_e    = scan_e;

    // -- captured count ----------------------------------------------------------------------
    integer ci;
    reg [31:0] cap_this_cycle;
    always @* begin
        cap_this_cycle = 32'b0;
        for (ci = 0; ci < TILE_LANES; ci = ci + 1)
            if (cap[ci] && !kblock_bad && !addr_bad[ci] && !dup[ci])
                cap_this_cycle = cap_this_cycle + 32'd1;
    end

    // -- per-lane leaf buffer: one write port each, LEAVES read ports ------------------------
    genvar gl, gk, ge;
    generate
        for (gl = 0; gl < TILE_LANES; gl = gl + 1) begin : gen_lane
            reg [31:0]       leafmem [0:SLOT_ELEMS*LEAVES-1];
            reg [LEAVES-1:0] have    [0:SLOT_ELEMS-1];
            reg [SLOT_ELEMS-1:0] ready;
            integer wi;

            wire [31:0] lane_addr = part_addr[32*gl +: 32];
            wire [31:0] lane_off  = lane_addr - blk_base;
            assign off[32*gl +: 32] = lane_off;
            assign cap[gl] = running && part_we[gl];
            assign addr_bad[gl] = (lane_off >= {16'b0, d_elems});
            wire [ELEM_AW-1:0] e_index = lane_off[ELEM_AW-1:0];
            wire [LOG_LEAVES-1:0] b_index = part_kblock[LOG_LEAVES-1:0];
            assign dup[gl] = !addr_bad[gl] && !kblock_bad && have[e_index][b_index];
            wire accept = cap[gl] && !kblock_bad && !addr_bad[gl] && !dup[gl];

            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    for (wi = 0; wi < SLOT_ELEMS; wi = wi + 1) have[wi] <= {LEAVES{1'b0}};
                    ready <= {SLOT_ELEMS{1'b0}};
                end else if (wipe) begin
                    for (wi = 0; wi < SLOT_ELEMS; wi = wi + 1) have[wi] <= {LEAVES{1'b0}};
                    ready <= {SLOT_ELEMS{1'b0}};
                end else begin
                    if (emit_now && (emit_lane == gl[LANE_AW-1:0]))
                        ready[emit_e[ELEM_AW-1:0]] <= 1'b0;
                    if (accept) begin
                        leafmem[({{(32-ELEM_AW){1'b0}}, e_index} << LOG_LEAVES) + {{(32-LOG_LEAVES){1'b0}}, b_index}]
                            <= part_data[32*gl +: 32];
                        have[e_index] <= have[e_index] | ({{(LEAVES-1){1'b0}}, 1'b1} << b_index);
                        if (is_last_block)
                            ready[e_index] <= 1'b1;
                    end
                end
            end

            for (gk = 0; gk < LEAVES; gk = gk + 1) begin : gen_read
                assign leaf_bus[VEC_BITS*gl + 32*gk +: 32] =
                    leafmem[({{(32-ELEM_AW){1'b0}}, scan_e[ELEM_AW-1:0]} << LOG_LEAVES) + gk];
            end
            assign have_bus[LEAVES*gl +: LEAVES] = have[scan_e[ELEM_AW-1:0]];
            for (ge = 0; ge < SLOT_ELEMS; ge = ge + 1) begin : gen_ready
                assign ready_flat[SLOT_ELEMS*gl + ge] = ready[ge];
            end
        end
    endgenerate

    // -- admission and the sequencer ------------------------------------------------------------
    wire blocks_ok = (cfg_blocks != 16'd0) && (cfg_blocks <= LEAVES);
    wire elems_ok  = (cfg_elems  != 16'd0) && (cfg_elems  <= SLOT_ELEMS);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            running <= 1'b0;
            busy <= 1'b0;
            done <= 1'b0;
            out_valid <= 1'b0;
            out_last <= 1'b0;
            out_leaf <= {VEC_BITS{1'b0}};
            out_leaf_count <= 4'b0;
            out_tag <= {TAG_W{1'b0}};
            error_code <= ERR_NONE;
            error_detail <= DETAIL_NONE;
            error_lane <= 16'b0;
            error_slot <= 32'b0;
            captured_count <= 32'b0;
            vectors_count <= 32'b0;
            d_blocks <= 16'b0;
            d_elems <= 16'b0;
            d_out_base <= 32'b0;
            full_mask <= {LEAVES{1'b0}};
            last_block <= 16'b0;
            scan_lane <= {LANE_AW{1'b0}};
            scan_e <= 16'b0;
            emit_index <= 32'b0;
            remaining <= 32'b0;
        end else begin
            done <= 1'b0;
            out_valid <= 1'b0;
            out_last <= 1'b0;

            if (clear && !cfg_start) begin
                running <= 1'b0;
                busy <= 1'b0;
                error_code <= ERR_NONE;
                error_detail <= DETAIL_NONE;
                error_lane <= 16'b0;
                error_slot <= 32'b0;
            end

            if (cfg_start) begin
                d_blocks <= cfg_blocks;
                d_elems <= cfg_elems;
                d_out_base <= cfg_out_base;
                last_block <= cfg_blocks - 16'd1;
                full_mask <= prefix_mask(cfg_blocks);
                scan_lane <= {LANE_AW{1'b0}};
                scan_e <= 16'b0;
                emit_index <= 32'b0;
                captured_count <= 32'b0;
                vectors_count <= 32'b0;
                error_code <= ERR_NONE;
                error_detail <= DETAIL_NONE;
                error_lane <= 16'b0;
                error_slot <= 32'b0;
                if (!blocks_ok) begin
                    running <= 1'b0;
                    busy <= 1'b0;
                    remaining <= 32'b0;
                    error_code <= ERR_SHAPE;
                    error_detail <= DETAIL_COLLECT_BLOCKS;
                    done <= 1'b1;
                end else if (!elems_ok) begin
                    running <= 1'b0;
                    busy <= 1'b0;
                    remaining <= 32'b0;
                    error_code <= ERR_SHAPE;
                    error_detail <= DETAIL_COLLECT_WINDOW;
                    done <= 1'b1;
                end else begin
                    running <= 1'b1;
                    busy <= 1'b1;
                    remaining <= TILE_LANES * {16'b0, cfg_elems};
                end
            end else if (running) begin
                captured_count <= captured_count + cap_this_cycle;
                if (capture_fault) begin
                    running <= 1'b0;
                    busy <= 1'b0;
                    done <= 1'b1;
                    error_code <= ERR_SHAPE;
                    error_detail <= f_detail;
                    error_lane <= f_lane;
                    error_slot <= f_slot;
                end else if (emit_fault) begin
                    running <= 1'b0;
                    busy <= 1'b0;
                    done <= 1'b1;
                    error_code <= ERR_SHAPE;
                    error_detail <= DETAIL_COLLECT_INCOMPLETE;
                    error_lane <= {{(16-LANE_AW){1'b0}}, scan_lane};
                    error_slot <= emit_index;
                end else if (emit_now) begin
                    out_valid <= 1'b1;
                    out_leaf <= sel_leaf;
                    out_leaf_count <= d_blocks[3:0];
                    out_tag <= emit_index[TAG_W-1:0];
                    out_last <= (remaining == 32'd1);
                    emit_index <= emit_index + 32'd1;
                    vectors_count <= vectors_count + 32'd1;
                    remaining <= remaining - 32'd1;
                    if (scan_e + 16'd1 == d_elems) begin
                        scan_e <= 16'b0;
                        scan_lane <= scan_lane + {{(LANE_AW-1){1'b0}}, 1'b1};
                    end else begin
                        scan_e <= scan_e + 16'd1;
                    end
                    if (remaining == 32'd1) begin
                        running <= 1'b0;
                        busy <= 1'b0;
                        done <= 1'b1;
                    end
                end
            end
        end
    end
endmodule
