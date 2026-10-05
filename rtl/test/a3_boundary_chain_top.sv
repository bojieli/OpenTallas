`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The two-tile dependent chain of section 13 item 13, and the top that
// measures its boundary.
//
// The chain, left to right, is FIVE design modules and nothing else:
//
//   u_prod  rtl/abi3/ot_a3_tile64.sv          the producing tile
//   u_coll  rtl/abi3/ot_a3_partial_collector.sv   its partials -> leaf vectors
//   u_tree  rtl/abi3/ot_a3_tree_endpoint_fp32.sv  the K-block tree
//   u_recv  rtl/abi3/ot_a3_operand_receiver.sv    the root -> an activation word
//   u_cons  rtl/abi3/ot_a3_tile64.sv          the consuming tile
//
// Every cycle of the measured span is spent inside one of those five.  The
// span is stamped from the producer tile's LAST partial write (the last cycle
// on which any bit of its part_we is high) to the consumer tile's FIRST
// lane-op (the first cycle its shared activation read is valid, which is the
// cycle a lane first consumes an operand), and is decomposed into six
// telescoping legs so that the residual is attributed rather than tuned.
//
// What is OUTSIDE the span, deliberately and by construction:
//   * the store-delivery network filling either tile's staging ring, and the
//     operand H-tree filling the PRODUCER's activation FIFO.  Both are bench
//     models here, both run to completion before the span opens, and neither
//     contributes a cycle to it: the consumer's ring is full and its weight
//     stream is present long before its operand arrives, so the only thing
//     gating the consumer is act_ready_kblocks, which is the receiver's.
//   * the control half of the boundary -- issue record store, event
//     scoreboard, queue admission -- which results/rtl/abi3_boundary_control.json
//     measures separately at 8 cycles.  The consumer's op_start is asserted
//     before the span opens, so this span is the DATAPATH half and the two are
//     additive rather than overlapping.
//   * the mesh traversal.  ot_a3_mesh_router's crossbar is combinational by
//     design and the traversal term is ot_a3_link_channel's, regressed in
//     results/rtl/a3_link_campaign.json.  The chain here is node-local.
//
// Geometry.  The producer is (rows 1, cols 64, K = 128 B) at BF16 g = 1 with
// op_kblock 128, so it emits one partial per lane per K-block -- the decode
// geometry -- and the collector's window is one element per lane.  The
// consumer is (rows 1, cols 64, K = 64) with op_kblock = K, so its single
// activation slice is exactly the producer's 64 output columns: layer l + 1's
// K equals layer l's N, which is what makes this a dependent chain and not two
// unrelated operations.
//
// Images (tools/build_abi3_boundary_chain_vectors.py):
//   ch_pstream.hex / ch_cstream.hex   the two weight streams
//   ch_pact.hex                       the producer's activation image
//   ch_case.hex                       one record per case
//   ch_expect.hex                     the roots, the delivered activation words
//                                     and the consumer's partials
//   ch_meta.hex                       case count and totals
// ---------------------------------------------------------------------------
module ot_a3_boundary_chain_top #(
    parameter integer LQ8S          = 8,
    parameter integer LANES         = 8,
    parameter integer ADDER_STAGES  = 3,
    parameter integer ACC_SLOTS     = 8,
    parameter integer LEAVES        = 8,
    parameter integer SLOT_ELEMS    = 2,
    parameter integer STAGING_BYTES = 2048,
    parameter integer STAGING_BUFFERS = 2,
    parameter integer ACT_WORDS     = 2048,
    parameter integer ACT_SCALE_WORDS = 64,
    parameter integer PSTREAM_WORDS = 4096,
    parameter integer CSTREAM_WORDS = 512,
    parameter integer PACT_WORDS    = 4096,
    parameter integer CASE_WORDS    = 1024,
    parameter integer EXPECT_WORDS  = 8192,
    parameter integer META_WORDS    = 8,
    parameter integer RESULT_WORDS  = 256,
    parameter integer CASE_STRIDE   = 32
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        run,
    input  wire [31:0] run_case,
    output reg         busy,
    output reg         done,

    // -- the measurement -------------------------------------------------------------
    output reg  [31:0] boundary_cycles,            // last partial write -> first lane-op
    output reg  [31:0] boundary_to_kblock_cycles,  // ... -> the consumer's K-block start
    output reg  [31:0] leg_collect,
    output reg  [31:0] leg_tree,
    output reg  [31:0] leg_receive,
    output reg  [31:0] leg_readiness,
    output reg  [31:0] leg_admit,
    output reg  [31:0] leg_lane_admission,
    output reg  [31:0] endpoint_first_root_cycles, // first leaf in -> first root out
    output reg  [31:0] leaf_span_cycles,
    output reg  [31:0] producer_cycles,            // op_start -> done, the producing pass
    output reg  [31:0] producer_kblock_cycles,     // the last K-block's own cycles

    // -- structural observables -------------------------------------------------------
    output reg  [31:0] obs_timeout,
    output wire [7:0]  obs_prod_error_code,
    output wire [7:0]  obs_prod_error_detail,
    output wire [7:0]  obs_cons_error_code,
    output wire [7:0]  obs_cons_error_detail,
    output wire [7:0]  obs_coll_error_code,
    output wire [7:0]  obs_coll_error_detail,
    output wire [7:0]  obs_tree_error_code,
    output wire [7:0]  obs_recv_error_code,
    output wire [7:0]  obs_recv_error_detail,
    output wire [31:0] obs_coll_vectors,
    output wire [31:0] obs_recv_words,
    output wire [15:0] obs_act_ready,
    output wire [31:0] obs_prod_out_count,
    output wire [31:0] obs_cons_out_count,
    output wire [31:0] obs_prod_underruns,
    output wire [31:0] obs_cons_underruns,
    output reg  [31:0] obs_roots,
    output reg  [31:0] obs_laneop_before_ready,   // a consumer lane-op before the operand landed

    // -- readback ----------------------------------------------------------------------
    input  wire [31:0] case_rd_addr,
    output wire [31:0] case_rd_data,
    input  wire [31:0] expect_rd_addr,
    output wire [31:0] expect_rd_data,
    input  wire [31:0] meta_rd_addr,
    output wire [31:0] meta_rd_data,
    input  wire [31:0] root_rd_addr,
    output wire [31:0] root_rd_data,
    input  wire [31:0] act_rd_addr,             // the words the receiver delivered
    output wire [31:0] act_rd_data,
    input  wire [31:0] res_rd_addr,             // the consumer's partials, per lane
    output wire [31:0] res_rd_data,
    output wire [31:0] adder_stages_param
);
    localparam integer TILE_LANES  = LQ8S * LANES;
    localparam integer STREAM_BITS = 16 * TILE_LANES;
    localparam integer STREAM_CHUNKS = STREAM_BITS / 32;
    localparam integer RING_WORDS  = STAGING_BUFFERS * STAGING_BYTES / (STREAM_BITS / 8);
    localparam integer RING_AW     = $clog2(RING_WORDS);
    localparam integer ACT_AW      = $clog2(ACT_WORDS);
    localparam integer ACT_SAW     = $clog2(ACT_SCALE_WORDS);
    localparam [31:0]  UNWRITTEN   = 32'hdeadbeef;

    reg [31:0] pstream_mem [0:STREAM_CHUNKS*PSTREAM_WORDS-1];
    reg [31:0] cstream_mem [0:STREAM_CHUNKS*CSTREAM_WORDS-1];
    reg [31:0] pact_mem    [0:2*PACT_WORDS-1];
    reg [31:0] case_mem    [0:CASE_WORDS-1];
    reg [31:0] expect_mem  [0:EXPECT_WORDS-1];
    reg [31:0] meta_mem    [0:META_WORDS-1];
    reg [31:0] root_mem    [0:TILE_LANES-1];
    reg [63:0] actlog_mem  [0:TILE_LANES-1];
    reg [31:0] res_mem     [0:RESULT_WORDS-1];

    integer init_i;
    initial begin
        $readmemh("ch_pstream.hex", pstream_mem);
        $readmemh("ch_cstream.hex", cstream_mem);
        $readmemh("ch_pact.hex", pact_mem);
        $readmemh("ch_case.hex", case_mem);
        $readmemh("ch_expect.hex", expect_mem);
        $readmemh("ch_meta.hex", meta_mem);
        for (init_i = 0; init_i < TILE_LANES; init_i = init_i + 1) begin
            root_mem[init_i] = UNWRITTEN;
            actlog_mem[init_i] = 64'hdeadbeefdeadbeef;
        end
        for (init_i = 0; init_i < RESULT_WORDS; init_i = init_i + 1) res_mem[init_i] = UNWRITTEN;
    end

    assign case_rd_data   = (case_rd_addr   < CASE_WORDS)   ? case_mem[case_rd_addr]     : 32'b0;
    assign expect_rd_data = (expect_rd_addr < EXPECT_WORDS) ? expect_mem[expect_rd_addr] : 32'b0;
    assign meta_rd_data   = (meta_rd_addr   < META_WORDS)   ? meta_mem[meta_rd_addr]     : 32'b0;
    assign root_rd_data   = (root_rd_addr   < TILE_LANES)   ? root_mem[root_rd_addr]     : 32'b0;
    assign act_rd_data    = ((act_rd_addr >> 1) < TILE_LANES)
                            ? (act_rd_addr[0] ? actlog_mem[act_rd_addr >> 1][63:32]
                                              : actlog_mem[act_rd_addr >> 1][31:0]) : 32'b0;
    assign res_rd_data    = (res_rd_addr < RESULT_WORDS) ? res_mem[res_rd_addr] : 32'b0;
    assign adder_stages_param = ADDER_STAGES;

    // -- the case, read combinationally out of the image -------------------------------
    reg [31:0] base;
    wire [31:0] f_p_depth   = case_mem[base + 2];
    wire [31:0] f_p_blocks  = case_mem[base + 4];
    wire [31:0] f_p_a_base  = case_mem[base + 5];
    wire [31:0] f_p_a_stride = case_mem[base + 6];
    wire [31:0] f_p_w_base  = case_mem[base + 7];
    wire [31:0] f_p_w_words = case_mem[base + 8];
    wire [31:0] f_p_out_base = case_mem[base + 9];
    wire [31:0] f_p_out_stride = case_mem[base + 10];
    wire [31:0] f_p_act_img = case_mem[base + 11];
    wire [31:0] f_p_act_slice = case_mem[base + 12];
    wire [31:0] f_c_depth   = case_mem[base + 15];
    wire [31:0] f_c_a_base  = case_mem[base + 18];
    wire [31:0] f_c_a_stride = case_mem[base + 19];
    wire [31:0] f_c_w_base  = case_mem[base + 20];
    wire [31:0] f_c_w_words = case_mem[base + 21];
    wire [31:0] f_c_out_base = case_mem[base + 22];
    wire [31:0] f_c_out_stride = case_mem[base + 23];

    localparam [7:0] FMT_BF16 = 8'h10;

    // -- descriptors ---------------------------------------------------------------------
    reg        p_start, c_start;
    reg [15:0] p_rows, p_cols, p_depth, p_kblock;
    reg [31:0] p_a_base, p_w_base, p_w_words, p_out_base, p_out_stride;
    reg [15:0] p_a_stride;
    reg [15:0] c_rows, c_cols, c_depth, c_kblock;
    reg [31:0] c_a_base, c_w_base, c_w_words, c_out_base, c_out_stride;
    reg [15:0] c_a_stride;

    // ================= the producing tile =====================================================
    reg                    p_stg_wr_en;
    reg  [31:0]            p_stg_wr_word;
    reg  [STREAM_BITS-1:0] p_stg_wr_data;
    wire [15:0]            p_stg_space;
    /* verilator lint_off UNUSEDSIGNAL */
    wire [31:0]            p_stg_fill_word, c_stg_fill_word;
    wire                   p_stg_rd_en, p_rom_rd_en, p_ws_rd_en, p_act_rd_en, p_act_scale_rd_en;
    wire [RING_AW-1:0]     p_stg_rd_addr;
    wire [31:0]            p_rom_rd_addr, p_ws_rd_addr;
    wire [ACT_AW-1:0]      p_act_rd_addr;
    wire [ACT_SAW-1:0]     p_act_scale_rd_addr;
    wire                   c_stg_rd_en, c_rom_rd_en, c_ws_rd_en, c_act_rd_en, c_act_scale_rd_en;
    wire [RING_AW-1:0]     c_stg_rd_addr;
    wire [31:0]            c_rom_rd_addr, c_ws_rd_addr;
    wire [ACT_AW-1:0]      c_act_rd_addr;
    wire [ACT_SAW-1:0]     c_act_scale_rd_addr;
    wire [8*LQ8S-1:0]      p_lq8_code, p_lq8_detail, c_lq8_code, c_lq8_detail;
    wire [8*TILE_LANES-1:0] p_lane_code, p_lane_detail, c_lane_code, c_lane_detail;
    wire [6:0]             p_retire, c_retire;
    wire [31:0]            p_sat, p_mac, p_prod_count, p_overruns, p_consumed;
    wire [31:0]            c_sat, c_mac, c_prod_count, c_overruns, c_consumed;
    wire [15:0]            p_error_kblock, c_error_kblock;
    wire [7:0]             p_error_lq8, p_error_lane, c_error_lq8, c_error_lane;
    wire [32*TILE_LANES-1:0] p_part_acc, c_part_acc;
    wire [15:0]            c_part_kblock;
    wire                   c_kblock_done, p_kblock_done;
    /* verilator lint_on UNUSEDSIGNAL */

    reg  [15:0]            p_act_ready;
    reg                    p_act_wr_en;
    reg  [ACT_AW-1:0]      p_act_wr_addr;
    reg  [63:0]            p_act_wr_data;
    wire [TILE_LANES-1:0]    p_part_we;
    wire [32*TILE_LANES-1:0] p_part_addr, p_part_data;
    wire [15:0]              p_part_kblock;
    wire                     p_busy, p_done, p_kblock_active;
    wire [15:0]              p_kblock_index;

    ot_a3_tile64 #(
        .LQ8S(LQ8S), .LANES(LANES), .ADDER_STAGES(ADDER_STAGES), .ACC_SLOTS(ACC_SLOTS),
        .STAGING_BYTES(STAGING_BYTES), .STAGING_BUFFERS(STAGING_BUFFERS),
        .STAGING_IN_TILE(1), .WEIGHT_SOURCE(0),
        .ACT_WORDS(ACT_WORDS), .ACT_SCALE_WORDS(ACT_SCALE_WORDS), .LQ8_ABSTRACT(0)
    ) u_prod (
        .clk(clk), .rst_n(rst_n),
        .op_start(p_start), .op_rows(p_rows), .op_cols(p_cols), .op_depth(p_depth),
        .op_kblock(p_kblock), .op_dtype_a(FMT_BF16), .op_dtype_b(FMT_BF16), .op_group(8'd1),
        .op_scale_a(1'b0), .op_block_a(16'd0), .op_block_rows_a(16'd0),
        .op_scale_b(1'b0), .op_block_b(16'd0),
        .op_a_base(p_a_base), .op_a_block_stride(p_a_stride),
        .op_scale_a_base(32'd0), .op_scale_a_block_stride(16'd0),
        .op_w_base(p_w_base), .op_w_words(p_w_words),
        .op_ws_base(32'd0), .op_ws_block_stride(32'd0),
        .op_out_base(p_out_base), .op_out_block_stride(p_out_stride), .op_out_fp32(1'b1),
        .stg_wr_en(p_stg_wr_en), .stg_wr_word(p_stg_wr_word), .stg_wr_data(p_stg_wr_data),
        .stg_space(p_stg_space), .stg_fill_word(p_stg_fill_word),
        .stg_rd_en(p_stg_rd_en), .stg_rd_addr(p_stg_rd_addr), .stg_rd_data({STREAM_BITS{1'b0}}),
        .rom_rd_en(p_rom_rd_en), .rom_rd_addr(p_rom_rd_addr), .rom_rd_data({STREAM_BITS{1'b0}}),
        .ws_rd_en(p_ws_rd_en), .ws_rd_addr(p_ws_rd_addr), .ws_rd_data({8*TILE_LANES{1'b0}}),
        .act_wr_en(p_act_wr_en), .act_wr_addr(p_act_wr_addr), .act_wr_data(p_act_wr_data),
        .act_scale_wr_en(1'b0), .act_scale_wr_addr({ACT_SAW{1'b0}}), .act_scale_wr_data(8'b0),
        .act_ready_kblocks(p_act_ready),
        .act_rd_en(p_act_rd_en), .act_rd_addr(p_act_rd_addr), .act_rd_data(64'b0),
        .act_scale_rd_en(p_act_scale_rd_en), .act_scale_rd_addr(p_act_scale_rd_addr),
        .act_scale_rd_data(8'b0),
        .part_we(p_part_we), .part_addr(p_part_addr), .part_data(p_part_data),
        .part_acc(p_part_acc), .part_kblock(p_part_kblock),
        .busy(p_busy), .done(p_done), .kblock_active(p_kblock_active),
        .kblock_done(p_kblock_done), .kblock_index(p_kblock_index),
        .error_code(obs_prod_error_code), .error_detail(obs_prod_error_detail),
        .error_kblock(p_error_kblock), .error_lq8(p_error_lq8), .error_lane(p_error_lane),
        .lq8_error_code(p_lq8_code), .lq8_error_detail(p_lq8_detail),
        .lane_error_code(p_lane_code), .lane_error_detail(p_lane_detail),
        .op_retire(), .retire_count(p_retire),
        .out_count(obs_prod_out_count), .saturation_count(p_sat), .mac_count(p_mac),
        .product_count(p_prod_count), .staging_underruns(obs_prod_underruns),
        .staging_overruns(p_overruns), .stream_words_consumed(p_consumed)
    );

    // ================= the collector ==============================================================
    reg         coll_start, chain_clear;
    reg [15:0]  coll_blocks;
    wire                 coll_valid;
    wire [3:0]           coll_count;
    wire [32*LEAVES-1:0] coll_leaf;
    wire [15:0]          coll_tag;
    wire                 coll_last;
    /* verilator lint_off UNUSEDSIGNAL */
    wire                 coll_busy, coll_done;
    wire [15:0]          coll_error_lane;
    wire [31:0]          coll_error_slot, coll_captured;
    /* verilator lint_on UNUSEDSIGNAL */

    ot_a3_partial_collector #(
        .TILE_LANES(TILE_LANES), .LEAVES(LEAVES), .SLOT_ELEMS(SLOT_ELEMS), .TAG_W(16)
    ) u_coll (
        .clk(clk), .rst_n(rst_n),
        .cfg_start(coll_start), .cfg_blocks(coll_blocks), .cfg_elems(16'd1),
        .cfg_out_base(p_out_base), .clear(chain_clear),
        .part_we(p_part_we), .part_addr(p_part_addr), .part_data(p_part_data),
        .part_kblock(p_part_kblock),
        .out_valid(coll_valid), .out_leaf_count(coll_count), .out_leaf(coll_leaf),
        .out_tag(coll_tag), .out_last(coll_last),
        .busy(coll_busy), .done(coll_done),
        .error_code(obs_coll_error_code), .error_detail(obs_coll_error_detail),
        .error_lane(coll_error_lane), .error_slot(coll_error_slot),
        .captured_count(coll_captured), .vectors_count(obs_coll_vectors)
    );

    // ================= the K-block tree ============================================================
    wire        tree_valid;
    wire [31:0] tree_data;
    wire [15:0] tree_tag;
    /* verilator lint_off UNUSEDSIGNAL */
    wire        tree_last, tree_busy;
    wire [7:0]  tree_error_detail;
    wire [1:0]  tree_error_level;
    wire [15:0] tree_error_tag;
    wire [31:0] tree_adds, tree_combines;
    /* verilator lint_on UNUSEDSIGNAL */

    ot_a3_tree_endpoint_fp32 #(.LEAVES(LEAVES), .ADDER_STAGES(ADDER_STAGES), .TAG_W(16)) u_tree (
        .clk(clk), .rst_n(rst_n),
        .in_valid(coll_valid), .in_leaf_count(coll_count), .in_leaf(coll_leaf),
        .in_tag(coll_tag), .in_last(coll_last), .clear(chain_clear),
        .out_valid(tree_valid), .out_data(tree_data), .out_tag(tree_tag),
        .out_last(tree_last),
        .error_code(obs_tree_error_code), .error_detail(tree_error_detail),
        .error_level(tree_error_level), .error_tag(tree_error_tag), .busy(tree_busy),
        .adds_count(tree_adds), .combines_count(tree_combines)
    );

    // ================= the operand receiver =========================================================
    reg         recv_start;
    reg [15:0]  recv_slice_words;
    wire                   c_act_wr_en;
    wire [ACT_AW-1:0]      c_act_wr_addr;
    wire [63:0]            c_act_wr_data;
    wire                   c_act_scale_wr_en;
    /* verilator lint_off UNUSEDSIGNAL */
    wire [ACT_SAW-1:0]     c_act_scale_wr_addr;
    wire [7:0]             c_act_scale_wr_data;
    wire                   recv_busy, recv_done;
    wire [15:0]            recv_error_tag, recv_slices;
    wire [31:0]            recv_roots, recv_sat;
    /* verilator lint_on UNUSEDSIGNAL */

    ot_a3_operand_receiver #(
        .ACT_WORDS(ACT_WORDS), .ACT_SCALE_WORDS(ACT_SCALE_WORDS), .TAG_W(16)
    ) u_recv (
        .clk(clk), .rst_n(rst_n),
        .cfg_start(recv_start), .cfg_blocks(16'd1), .cfg_slice_words(recv_slice_words),
        .cfg_group(8'd1), .cfg_dtype(FMT_BF16), .cfg_scaled(1'b0),
        .cfg_base(c_a_base), .cfg_stride(c_a_stride), .clear(chain_clear),
        .in_valid(tree_valid), .in_data(tree_data), .in_tag(tree_tag), .in_last(tree_last),
        .act_wr_en(c_act_wr_en), .act_wr_addr(c_act_wr_addr), .act_wr_data(c_act_wr_data),
        .act_scale_wr_en(c_act_scale_wr_en), .act_scale_wr_addr(c_act_scale_wr_addr),
        .act_scale_wr_data(c_act_scale_wr_data),
        .act_ready_kblocks(obs_act_ready),
        .busy(recv_busy), .done(recv_done),
        .error_code(obs_recv_error_code), .error_detail(obs_recv_error_detail),
        .error_tag(recv_error_tag), .roots_count(recv_roots),
        .words_written(obs_recv_words), .slices_ready(recv_slices),
        .saturation_count(recv_sat)
    );

    // ================= the consuming tile ============================================================
    reg                    c_stg_wr_en;
    reg  [31:0]            c_stg_wr_word;
    reg  [STREAM_BITS-1:0] c_stg_wr_data;
    wire [15:0]            c_stg_space;
    wire [TILE_LANES-1:0]    c_part_we;
    wire [32*TILE_LANES-1:0] c_part_addr, c_part_data;
    wire                     c_busy, c_done, c_kblock_active;
    wire [15:0]              c_kblock_index;

    ot_a3_tile64 #(
        .LQ8S(LQ8S), .LANES(LANES), .ADDER_STAGES(ADDER_STAGES), .ACC_SLOTS(ACC_SLOTS),
        .STAGING_BYTES(STAGING_BYTES), .STAGING_BUFFERS(STAGING_BUFFERS),
        .STAGING_IN_TILE(1), .WEIGHT_SOURCE(0),
        .ACT_WORDS(ACT_WORDS), .ACT_SCALE_WORDS(ACT_SCALE_WORDS), .LQ8_ABSTRACT(0)
    ) u_cons (
        .clk(clk), .rst_n(rst_n),
        .op_start(c_start), .op_rows(c_rows), .op_cols(c_cols), .op_depth(c_depth),
        .op_kblock(c_kblock), .op_dtype_a(FMT_BF16), .op_dtype_b(FMT_BF16), .op_group(8'd1),
        .op_scale_a(1'b0), .op_block_a(16'd0), .op_block_rows_a(16'd0),
        .op_scale_b(1'b0), .op_block_b(16'd0),
        .op_a_base(c_a_base), .op_a_block_stride(c_a_stride),
        .op_scale_a_base(32'd0), .op_scale_a_block_stride(16'd0),
        .op_w_base(c_w_base), .op_w_words(c_w_words),
        .op_ws_base(32'd0), .op_ws_block_stride(32'd0),
        .op_out_base(c_out_base), .op_out_block_stride(c_out_stride), .op_out_fp32(1'b1),
        .stg_wr_en(c_stg_wr_en), .stg_wr_word(c_stg_wr_word), .stg_wr_data(c_stg_wr_data),
        .stg_space(c_stg_space), .stg_fill_word(c_stg_fill_word),
        .stg_rd_en(c_stg_rd_en), .stg_rd_addr(c_stg_rd_addr), .stg_rd_data({STREAM_BITS{1'b0}}),
        .rom_rd_en(c_rom_rd_en), .rom_rd_addr(c_rom_rd_addr), .rom_rd_data({STREAM_BITS{1'b0}}),
        .ws_rd_en(c_ws_rd_en), .ws_rd_addr(c_ws_rd_addr), .ws_rd_data({8*TILE_LANES{1'b0}}),
        .act_wr_en(c_act_wr_en), .act_wr_addr(c_act_wr_addr), .act_wr_data(c_act_wr_data),
        .act_scale_wr_en(c_act_scale_wr_en), .act_scale_wr_addr(c_act_scale_wr_addr),
        .act_scale_wr_data(c_act_scale_wr_data),
        .act_ready_kblocks(obs_act_ready),
        .act_rd_en(c_act_rd_en), .act_rd_addr(c_act_rd_addr), .act_rd_data(64'b0),
        .act_scale_rd_en(c_act_scale_rd_en), .act_scale_rd_addr(c_act_scale_rd_addr),
        .act_scale_rd_data(8'b0),
        .part_we(c_part_we), .part_addr(c_part_addr), .part_data(c_part_data),
        .part_acc(c_part_acc), .part_kblock(c_part_kblock),
        .busy(c_busy), .done(c_done), .kblock_active(c_kblock_active),
        .kblock_done(c_kblock_done), .kblock_index(c_kblock_index),
        .error_code(obs_cons_error_code), .error_detail(obs_cons_error_detail),
        .error_kblock(c_error_kblock), .error_lq8(c_error_lq8), .error_lane(c_error_lane),
        .lq8_error_code(c_lq8_code), .lq8_error_detail(c_lq8_detail),
        .lane_error_code(c_lane_code), .lane_error_detail(c_lane_detail),
        .op_retire(), .retire_count(c_retire),
        .out_count(obs_cons_out_count), .saturation_count(c_sat), .mac_count(c_mac),
        .product_count(c_prod_count), .staging_underruns(obs_cons_underruns),
        .staging_overruns(c_overruns), .stream_words_consumed(c_consumed)
    );

    // ================= environment models, all of them OUTSIDE the measured span ======================
    function automatic [STREAM_BITS-1:0] pstream_word;
        input [31:0] index;
        integer k;
        begin
            pstream_word = {STREAM_BITS{1'b0}};
            if (index < PSTREAM_WORDS)
                for (k = 0; k < STREAM_CHUNKS; k = k + 1)
                    pstream_word[32*k +: 32] = pstream_mem[STREAM_CHUNKS * index + k];
        end
    endfunction
    function automatic [STREAM_BITS-1:0] cstream_word;
        input [31:0] index;
        integer k;
        begin
            cstream_word = {STREAM_BITS{1'b0}};
            if (index < CSTREAM_WORDS)
                for (k = 0; k < STREAM_CHUNKS; k = k + 1)
                    cstream_word[32*k +: 32] = cstream_mem[STREAM_CHUNKS * index + k];
        end
    endfunction
    function automatic [63:0] pact_word;
        input [31:0] index;
        begin
            pact_word = (index < PACT_WORDS) ? {pact_mem[2*index + 1], pact_mem[2*index]} : 64'b0;
        end
    endfunction

    // -- the two store-delivery networks: one word per cycle as the credit allows ---------
    reg        p_sdn_active, c_sdn_active;
    reg [31:0] p_sdn_ptr, p_sdn_left, c_sdn_ptr, c_sdn_left;
    always @* begin
        p_stg_wr_en   = p_sdn_active && (p_sdn_left != 32'b0) && (p_stg_space != 16'b0);
        p_stg_wr_word = p_sdn_ptr;
        p_stg_wr_data = pstream_word(p_sdn_ptr);
        c_stg_wr_en   = c_sdn_active && (c_sdn_left != 32'b0) && (c_stg_space != 16'b0);
        c_stg_wr_word = c_sdn_ptr;
        c_stg_wr_data = cstream_word(c_sdn_ptr);
    end

    // -- the producer's operand H-tree: slice b + 1 while K-block b runs -------------------
    localparam [1:0] H_IDLE = 2'd0, H_ACT = 2'd1, H_WAIT = 2'd2;
    reg [1:0]  h_state;
    reg [15:0] h_slice, h_word, h_words;
    reg [15:0] h_blocks;
    reg [31:0] h_img_base;
    always @* begin
        p_act_wr_en   = (h_state == H_ACT);
        p_act_wr_addr = (p_a_base + (h_slice[0] ? {16'b0, p_a_stride} : 32'b0) + {16'b0, h_word});
        p_act_wr_data = pact_word(h_img_base + {16'b0, h_slice} * {16'b0, p_a_stride} + {16'b0, h_word});
    end

    // ================= the measurement ================================================================
    reg [31:0] cycle;
    reg        armed;                       // the span is open
    reg [31:0] t_last_part, t_first_leaf, t_last_leaf, t_first_root, t_last_root;
    reg [31:0] t_first_actwr, t_last_actwr, t_ready, t_kblock_active, t_first_laneop;
    reg [31:0] t_prod_start, t_prod_done, t_last_kblock_start;
    reg        seen_leaf, seen_root, seen_actwr, seen_ready, seen_kblock, seen_laneop;
    reg        seen_pk;                    // the producer's last K-block has started
    wire       cons_laneop = u_cons.sel_a_valid;
    wire       prod_part_any = |p_part_we;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cycle <= 32'b0;
            t_last_part <= 32'b0; t_first_leaf <= 32'b0; t_last_leaf <= 32'b0;
            t_first_root <= 32'b0; t_last_root <= 32'b0;
            t_first_actwr <= 32'b0; t_last_actwr <= 32'b0; t_ready <= 32'b0;
            t_kblock_active <= 32'b0; t_first_laneop <= 32'b0;
            t_prod_start <= 32'b0; t_prod_done <= 32'b0; t_last_kblock_start <= 32'b0;
            seen_leaf <= 1'b0; seen_root <= 1'b0; seen_actwr <= 1'b0;
            seen_ready <= 1'b0; seen_kblock <= 1'b0; seen_laneop <= 1'b0;
            seen_pk <= 1'b0;
            obs_roots <= 32'b0;
            obs_laneop_before_ready <= 32'b0;
        end else begin
            cycle <= cycle + 32'd1;
            if (coll_start) begin
                seen_leaf <= 1'b0; seen_root <= 1'b0; seen_actwr <= 1'b0;
                seen_ready <= 1'b0; seen_kblock <= 1'b0; seen_laneop <= 1'b0;
                seen_pk <= 1'b0;
                obs_roots <= 32'b0;
                obs_laneop_before_ready <= 32'b0;
            end
            if (armed) begin
                if (p_start) t_prod_start <= cycle;
                if (p_done)  t_prod_done <= cycle;
                if (p_kblock_active && !seen_pk &&
                    (p_kblock_index + 16'd1 == coll_blocks)) begin
                    t_last_kblock_start <= cycle;
                    seen_pk <= 1'b1;
                end
                if (prod_part_any) t_last_part <= cycle;
                if (coll_valid) begin
                    t_last_leaf <= cycle;
                    if (!seen_leaf) begin t_first_leaf <= cycle; seen_leaf <= 1'b1; end
                end
                if (tree_valid) begin
                    t_last_root <= cycle;
                    obs_roots <= obs_roots + 32'd1;
                    root_mem[tree_tag[5:0]] <= tree_data;
                    if (!seen_root) begin t_first_root <= cycle; seen_root <= 1'b1; end
                end
                if (c_act_wr_en) begin
                    t_last_actwr <= cycle;
                    // indexed by the word's own place in the slice, not by the
                    // receiver's counter (which has already been incremented)
                    actlog_mem[c_act_wr_addr[5:0] - c_a_base[5:0]] <= c_act_wr_data;
                    if (!seen_actwr) begin t_first_actwr <= cycle; seen_actwr <= 1'b1; end
                end
                if ((obs_act_ready != 16'b0) && !seen_ready) begin
                    t_ready <= cycle; seen_ready <= 1'b1;
                end
                if (c_kblock_active && !seen_kblock) begin
                    t_kblock_active <= cycle; seen_kblock <= 1'b1;
                end
                if (cons_laneop && !seen_laneop) begin
                    t_first_laneop <= cycle; seen_laneop <= 1'b1;
                    if (!seen_ready) obs_laneop_before_ready <= obs_laneop_before_ready + 32'd1;
                end
            end
        end
    end

    // -- the consumer's results, one region per lane ----------------------------------------------
    integer wi;
    always @(posedge clk) begin
        for (wi = 0; wi < TILE_LANES; wi = wi + 1)
            if (c_part_we[wi] && (c_part_addr[32*wi +: 32] < 32'd4))
                res_mem[wi * 4 + c_part_addr[32*wi +: 32]] <= c_part_data[32*wi +: 32];
    end

    // ================= the case sequencer ==============================================================
    localparam [3:0] S_IDLE = 4'd0, S_CLEAR = 4'd1, S_ARM = 4'd2, S_CONS = 4'd3,
                     S_FILL = 4'd4, S_PROD = 4'd5, S_RUN = 4'd6, S_STAMP = 4'd7,
                     S_FINISH = 4'd8;
    reg [3:0]  sstate;
    reg [31:0] settle;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sstate <= S_IDLE;
            busy <= 1'b0; done <= 1'b0;
            p_start <= 1'b0; c_start <= 1'b0; coll_start <= 1'b0; recv_start <= 1'b0;
            chain_clear <= 1'b0;
            armed <= 1'b0;
            base <= 32'b0;
            p_rows <= 16'd1; p_cols <= 16'd64; p_depth <= 16'b0; p_kblock <= 16'd128;
            p_a_base <= 32'b0; p_a_stride <= 16'b0; p_w_base <= 32'b0; p_w_words <= 32'b0;
            p_out_base <= 32'b0; p_out_stride <= 32'd1;
            c_rows <= 16'd1; c_cols <= 16'd64; c_depth <= 16'b0; c_kblock <= 16'b0;
            c_a_base <= 32'b0; c_a_stride <= 16'b0; c_w_base <= 32'b0; c_w_words <= 32'b0;
            c_out_base <= 32'b0; c_out_stride <= 32'd1;
            coll_blocks <= 16'b0; recv_slice_words <= 16'b0;
            p_sdn_active <= 1'b0; p_sdn_ptr <= 32'b0; p_sdn_left <= 32'b0;
            c_sdn_active <= 1'b0; c_sdn_ptr <= 32'b0; c_sdn_left <= 32'b0;
            h_state <= H_IDLE; h_slice <= 16'b0; h_word <= 16'b0; h_words <= 16'b0;
            h_blocks <= 16'b0; h_img_base <= 32'b0;
            p_act_ready <= 16'b0;
            settle <= 32'b0;
            obs_timeout <= 32'b0;
            boundary_cycles <= 32'b0; boundary_to_kblock_cycles <= 32'b0;
            leg_collect <= 32'b0; leg_tree <= 32'b0; leg_receive <= 32'b0;
            leg_readiness <= 32'b0; leg_admit <= 32'b0; leg_lane_admission <= 32'b0;
            endpoint_first_root_cycles <= 32'b0; leaf_span_cycles <= 32'b0;
            producer_cycles <= 32'b0; producer_kblock_cycles <= 32'b0;
        end else begin
            done <= 1'b0;
            p_start <= 1'b0; c_start <= 1'b0; coll_start <= 1'b0; recv_start <= 1'b0;
            chain_clear <= 1'b0;

            // -- the store-delivery networks -----------------------------------------
            if (p_stg_wr_en) begin
                p_sdn_ptr <= p_sdn_ptr + 32'd1;
                p_sdn_left <= p_sdn_left - 32'd1;
                if (p_sdn_left == 32'd1) p_sdn_active <= 1'b0;
            end
            if (c_stg_wr_en) begin
                c_sdn_ptr <= c_sdn_ptr + 32'd1;
                c_sdn_left <= c_sdn_left - 32'd1;
                if (c_sdn_left == 32'd1) c_sdn_active <= 1'b0;
            end

            // -- the producer's H-tree ------------------------------------------------
            case (h_state)
                H_ACT: begin
                    if (h_word + 16'd1 >= h_words) begin
                        h_word <= 16'b0;
                        h_state <= H_WAIT;
                        p_act_ready <= h_slice + 16'd1;
                    end else begin
                        h_word <= h_word + 16'd1;
                    end
                end
                H_WAIT: begin
                    if (h_slice + 16'd1 < h_blocks) begin
                        if ((h_slice + 16'd1 < 16'd2) ||
                            (p_kblock_active && (p_kblock_index + 16'd1 >= h_slice + 16'd1))) begin
                            h_slice <= h_slice + 16'd1;
                            h_word <= 16'b0;
                            h_state <= H_ACT;
                        end
                    end else begin
                        h_state <= H_IDLE;
                    end
                end
                default: ;
            endcase

            case (sstate)
                S_IDLE: begin
                    if (run) begin
                        base <= run_case * CASE_STRIDE;
                        busy <= 1'b1;
                        chain_clear <= 1'b1;
                        obs_timeout <= 32'b0;
                        sstate <= S_CLEAR;
                    end
                end
                S_CLEAR: begin
                    // the descriptors, from the case image
                    p_depth <= f_p_depth[15:0];
                    p_a_base <= f_p_a_base;
                    p_a_stride <= f_p_a_stride[15:0];
                    p_w_base <= f_p_w_base;
                    p_w_words <= f_p_w_words;
                    p_out_base <= f_p_out_base;
                    p_out_stride <= f_p_out_stride;
                    c_depth <= f_c_depth[15:0];
                    c_kblock <= f_c_depth[15:0];
                    c_a_base <= f_c_a_base;
                    c_a_stride <= f_c_a_stride[15:0];
                    c_w_base <= f_c_w_base;
                    c_w_words <= f_c_w_words;
                    c_out_base <= f_c_out_base;
                    c_out_stride <= f_c_out_stride;
                    coll_blocks <= f_p_blocks[15:0];
                    recv_slice_words <= f_c_a_stride[15:0];
                    h_blocks <= f_p_blocks[15:0];
                    h_words <= f_p_act_slice[15:0];
                    h_img_base <= f_p_act_img;
                    armed <= 1'b0;
                    sstate <= S_ARM;
                end
                S_ARM: begin
                    // the collector and the receiver are configured before anything runs
                    coll_start <= 1'b1;
                    recv_start <= 1'b1;
                    sstate <= S_CONS;
                end
                S_CONS: begin
                    // the CONSUMER is issued first and parks in S_WAIT on its operand:
                    // its queue admission is complete before the span opens, so the span
                    // is the datapath half and does not double-count the control half
                    c_start <= 1'b1;
                    c_sdn_active <= 1'b1;
                    c_sdn_ptr <= c_w_base;
                    c_sdn_left <= c_w_words;
                    settle <= 32'b0;
                    sstate <= S_FILL;
                end
                S_FILL: begin
                    // let the consumer's staging ring fill, so that fill_ok is long true
                    // and act_ready_kblocks is the only thing gating it
                    settle <= settle + 32'd1;
                    if (settle > 32'd64) begin
                        settle <= 32'b0;
                        sstate <= S_PROD;
                    end
                end
                S_PROD: begin
                    p_start <= 1'b1;
                    p_sdn_active <= 1'b1;
                    p_sdn_ptr <= p_w_base;
                    p_sdn_left <= p_w_words;
                    p_act_ready <= 16'b0;
                    h_slice <= 16'b0;
                    h_word <= 16'b0;
                    h_state <= H_ACT;
                    armed <= 1'b1;
                    settle <= 32'b0;
                    sstate <= S_RUN;
                end
                S_RUN: begin
                    settle <= settle + 32'd1;
                    if ((!c_busy && !p_busy && seen_laneop) || (settle > 32'd200000)) begin
                        if (settle > 32'd200000) obs_timeout <= 32'd1;
                        armed <= 1'b0;
                        settle <= 32'b0;
                        sstate <= S_STAMP;
                    end
                end
                S_STAMP: begin
                    boundary_cycles           <= t_first_laneop - t_last_part;
                    boundary_to_kblock_cycles <= t_kblock_active - t_last_part;
                    leg_collect               <= t_first_leaf - t_last_part;
                    leg_tree                  <= t_last_root - t_first_leaf;
                    leg_receive               <= t_last_actwr - t_last_root;
                    leg_readiness             <= t_ready - t_last_actwr;
                    leg_admit                 <= t_kblock_active - t_ready;
                    leg_lane_admission        <= t_first_laneop - t_kblock_active;
                    endpoint_first_root_cycles <= t_first_root - t_first_leaf;
                    leaf_span_cycles          <= (t_last_leaf - t_first_leaf) + 32'd1;
                    producer_cycles           <= t_prod_done - t_prod_start;
                    producer_kblock_cycles    <= t_last_part - t_last_kblock_start;
                    sstate <= S_FINISH;
                end
                S_FINISH: begin
                    settle <= settle + 32'd1;
                    if (settle > 32'd8) begin
                        busy <= 1'b0;
                        done <= 1'b1;
                        settle <= 32'b0;
                        sstate <= S_IDLE;
                    end
                end
                default: sstate <= S_IDLE;
            endcase
        end
    end
endmodule
