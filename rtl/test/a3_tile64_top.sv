`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Verification top for the T64 tile (results/rtl/abi3_tile64.json).
//
// Both checkers -- rtl/test/tb_a3_tile64.sv on Icarus and
// rtl/test/a3_tile64_harness.cpp on Verilator -- instantiate this module and
// read the same generated images, so the two simulators run identical RTL
// through independently written checkers.  It holds:
//
//   u_dut    rtl/abi3/ot_a3_tile64.sv (WEIGHT_SOURCE and STAGING_IN_TILE as
//            parameters of this top);
//   u_tree   one rtl/abi3/ot_a3_tree_endpoint_fp32.sv BESIDE the tile, never
//            inside it (the tree spans tiles); the checkers feed the tile's
//            captured partials through it column by column in the chained
//            shapes of the K-block tree;
//   the environment models the tile has no back-pressure against:
//     SDN     writes the weight stream into the tile's staging ring one
//             128-B word per cycle as the tile's credit allows (or ignoring
//             it, or stopping after a limit, when a case says so);
//     H-tree  broadcasts K-block b + 1's activation slice (and E8M0 slice)
//             into FIFO slice (b + 1) mod 2 while K-block b runs, and raises
//             act_ready_kblocks when the slice is complete;
//     ROM     serves the stream image on the sense port (WEIGHT_SOURCE = 1);
//     the external staging ring and activation arrays (STAGING_IN_TILE = 0),
//     with the same one-cycle latency the tile's own arrays have;
//   result memories, one region per tile lane, written from the partial
//   port at the lane-local address the tile emits.
//
// Images (tools/build_abi3_tile64_vectors.py):
//   t64_stream.hex   the weight stream, one 1024-bit word per tile lane-op
//                    as 32 lines of 32 bits (low word first)
//   t64_ws.hex       the weight scale table, one 512-bit word per index (16 lines)
//   t64_act.hex      the activation image (64-bit words, two lines each)
//   t64_act_scale.hex the activation E8M0 image (one code per line)
//   t64_case.hex     one record per case (layout in the checkers)
//   t64_expect.hex   partial expectations, then tree roots
//   t64_meta.hex     case count and the campaign totals
//
// Lockstep across the eight LQ8s is an invariant of the tile; this top
// checks it on every clock: whenever an LQ8 requests an activation word its
// address must equal the one the tile forwarded, its request enables must
// agree, and the stream address of every requesting LQ8 must equal the one
// the tile served.  lockstep_violations must read zero after every case.
// ---------------------------------------------------------------------------
module ot_a3_tile64_top #(
    parameter integer LQ8S            = 8,
    parameter integer LANES           = 8,
    parameter integer ADDER_STAGES    = 3,
    parameter integer ACC_SLOTS       = 8,
    parameter integer WEIGHT_SOURCE   = 0,
    parameter integer STAGING_IN_TILE = 1,
    parameter integer STAGING_BYTES   = 2048,
    parameter integer STAGING_BUFFERS = 2,
    parameter integer ACT_WORDS       = 2048,
    parameter integer ACT_SCALE_WORDS = 64,
    parameter integer STREAM_WORDS    = 262144,
    parameter integer WS_WORDS        = 16384,
    parameter integer ACT_IMG_WORDS   = 131072,
    parameter integer ACT_SCALE_IMG_WORDS = 8192,
    parameter integer REGION_WORDS    = 8192,
    parameter integer CASE_WORDS      = 16384,
    parameter integer EXPECT_WORDS    = 1048576,
    parameter integer META_WORDS      = 12
) (
    input  wire        clk,
    input  wire        rst_n,

    // -- the operation descriptor, driven by the checker ---------------------------
    input  wire        op_start,
    input  wire [15:0] op_rows,
    input  wire [15:0] op_cols,
    input  wire [15:0] op_depth,
    input  wire [15:0] op_kblock,
    input  wire [7:0]  op_dtype_a,
    input  wire [7:0]  op_dtype_b,
    input  wire [7:0]  op_group,
    input  wire        op_scale_a,
    input  wire [15:0] op_block_a,
    input  wire [15:0] op_block_rows_a,
    input  wire        op_scale_b,
    input  wire [15:0] op_block_b,
    input  wire [31:0] op_a_base,
    input  wire [15:0] op_a_block_stride,
    input  wire [31:0] op_scale_a_base,
    input  wire [15:0] op_scale_a_block_stride,
    input  wire [31:0] op_w_base,
    input  wire [31:0] op_w_words,
    input  wire [31:0] op_ws_base,
    input  wire [31:0] op_ws_block_stride,
    input  wire [31:0] op_out_base,
    input  wire [31:0] op_out_block_stride,
    input  wire        op_out_fp32,

    // -- environment control, driven by the checker --------------------------------
    input  wire        env_start,               // one pulse per case, after op_start
    input  wire [31:0] env_sdn_base,
    input  wire [31:0] env_sdn_words,           // words the SDN delivers
    input  wire        env_sdn_ignore_credit,
    input  wire [31:0] env_act_img_base,
    input  wire [15:0] env_act_slice_full,
    input  wire [15:0] env_act_slice_last,
    input  wire [15:0] env_act_stride,
    input  wire [31:0] env_act_region_base,
    input  wire [31:0] env_scale_img_base,
    input  wire [15:0] env_scale_slice_full,
    input  wire [15:0] env_scale_slice_last,
    input  wire [15:0] env_scale_stride,
    input  wire [31:0] env_scale_region_base,
    input  wire [15:0] env_blocks,
    output wire        env_busy,
    output reg  [31:0] sdn_written,

    // -- tile status ------------------------------------------------------------------
    output wire        dut_busy,
    output wire        dut_done,
    output wire        dut_kblock_active,
    output wire        dut_kblock_done,
    output wire [15:0] dut_kblock_index,
    output wire [7:0]  dut_error_code,
    output wire [7:0]  dut_error_detail,
    output wire [15:0] dut_error_kblock,
    output wire [7:0]  dut_error_lq8,
    output wire [7:0]  dut_error_lane,
    output wire [6:0]  dut_retire_count,
    output wire [31:0] dut_out_count,
    output wire [31:0] dut_saturation_count,
    output wire [31:0] dut_mac_count,
    output wire [31:0] dut_product_count,
    output wire [31:0] dut_staging_underruns,
    output wire [31:0] dut_staging_overruns,
    output wire [31:0] dut_stream_words_consumed,
    output reg  [31:0] lockstep_violations,
    // per-LQ8 and per-lane classes, selected
    input  wire [7:0]  lane_rd_sel,             // 0..63
    output wire [7:0]  lq8_rd_error_code,
    output wire [7:0]  lq8_rd_error_detail,
    output wire [7:0]  lane_rd_error_code,
    output wire [7:0]  lane_rd_error_detail,

    // -- the tree endpoint beside the tile, driven by the checker ----------------------
    input  wire        tree_in_valid,
    input  wire [3:0]  tree_in_count,
    input  wire [255:0] tree_in_leaf,
    input  wire [15:0] tree_in_tag,
    input  wire        tree_clear,
    output wire        tree_out_valid,
    output wire [31:0] tree_out_data,
    output wire [15:0] tree_out_tag,
    output wire [7:0]  tree_error_code,
    output wire [7:0]  tree_error_detail,
    output wire        tree_busy,

    // -- read-back for the checkers ------------------------------------------------------
    input  wire [31:0] case_rd_addr,
    output wire [31:0] case_rd_data,
    input  wire [31:0] expect_rd_addr,
    output wire [31:0] expect_rd_data,
    input  wire [31:0] meta_rd_addr,
    output wire [31:0] meta_rd_data,
    input  wire [31:0] res_rd_addr,             // lane * REGION_WORDS + lane-local address
    output wire [31:0] res_rd_data,
    output wire [31:0] acc_rd_data,
    output wire [31:0] adder_stages,
    output wire [31:0] lanes,
    output wire [31:0] region_words,
    output wire [31:0] weight_source,
    output wire [31:0] staging_in_tile
);
    localparam integer TILE_LANES  = LQ8S * LANES;
    localparam integer STREAM_BITS = 16 * TILE_LANES;
    localparam integer WS_BITS     = 8 * TILE_LANES;
    localparam integer RING_WORDS  = STAGING_BUFFERS * STAGING_BYTES / (STREAM_BITS / 8);
    localparam integer RING_AW     = $clog2(RING_WORDS);
    localparam integer ACT_AW      = $clog2(ACT_WORDS);
    localparam integer ACT_SAW     = $clog2(ACT_SCALE_WORDS);
    localparam integer RESULT_WORDS = TILE_LANES * REGION_WORDS;
    localparam [31:0]  UNWRITTEN   = 32'hdead_beef;

    // Images are held as 32-bit words (a wide-element memory costs Icarus
    // minutes at compile time) and the wide words are assembled on read.
    localparam integer STREAM_CHUNKS = STREAM_BITS / 32;
    localparam integer WS_CHUNKS     = WS_BITS / 32;
    reg [31:0]            stream_mem [0:STREAM_CHUNKS*STREAM_WORDS-1];
    reg [31:0]            ws_mem     [0:WS_CHUNKS*WS_WORDS-1];
    reg [31:0]            act_img    [0:2*ACT_IMG_WORDS-1];
    reg [31:0]            act_scale_img [0:ACT_SCALE_IMG_WORDS-1];
    reg [31:0]            case_mem   [0:CASE_WORDS-1];
    reg [31:0]            expect_mem [0:EXPECT_WORDS-1];
    reg [31:0]            meta_mem   [0:META_WORDS-1];
    reg [31:0]            res_mem    [0:RESULT_WORDS-1];
    reg [31:0]            acc_mem    [0:RESULT_WORDS-1];

    assign adder_stages = ADDER_STAGES;
    assign lanes = TILE_LANES;
    assign region_words = REGION_WORDS;
    assign weight_source = WEIGHT_SOURCE;
    assign staging_in_tile = STAGING_IN_TILE;

    integer clear_index;
    initial begin
        $readmemh("t64_stream.hex", stream_mem);
        $readmemh("t64_ws.hex", ws_mem);
        $readmemh("t64_act.hex", act_img);
        $readmemh("t64_act_scale.hex", act_scale_img);
        $readmemh("t64_case.hex", case_mem);
        $readmemh("t64_expect.hex", expect_mem);
        $readmemh("t64_meta.hex", meta_mem);
        for (clear_index = 0; clear_index < RESULT_WORDS; clear_index = clear_index + 1) begin
            res_mem[clear_index] = UNWRITTEN;
            acc_mem[clear_index] = UNWRITTEN;
        end
    end

    assign case_rd_data   = (case_rd_addr < CASE_WORDS) ? case_mem[case_rd_addr] : 32'b0;
    assign expect_rd_data = (expect_rd_addr < EXPECT_WORDS) ? expect_mem[expect_rd_addr] : 32'b0;
    assign meta_rd_data   = (meta_rd_addr < META_WORDS) ? meta_mem[meta_rd_addr] : 32'b0;
    assign res_rd_data    = (res_rd_addr < RESULT_WORDS) ? res_mem[res_rd_addr] : 32'b0;
    assign acc_rd_data    = (res_rd_addr < RESULT_WORDS) ? acc_mem[res_rd_addr] : 32'b0;

    // -- tile ports -----------------------------------------------------------------------------------
    reg                    stg_wr_en;
    reg  [31:0]            stg_wr_word;
    reg  [STREAM_BITS-1:0] stg_wr_data;
    wire [15:0]            stg_space;
    wire [31:0]            stg_fill_word;
    wire                   stg_rd_en;
    wire [RING_AW-1:0]     stg_rd_addr;
    reg  [STREAM_BITS-1:0] stg_rd_data;
    wire                   rom_rd_en;
    wire [31:0]            rom_rd_addr;
    reg  [STREAM_BITS-1:0] rom_rd_data;
    wire                   ws_rd_en;
    wire [31:0]            ws_rd_addr;
    reg  [WS_BITS-1:0]     ws_rd_data;
    reg                    act_wr_en;
    reg  [ACT_AW-1:0]      act_wr_addr;
    reg  [63:0]            act_wr_data;
    reg                    act_scale_wr_en;
    reg  [ACT_SAW-1:0]     act_scale_wr_addr;
    reg  [7:0]             act_scale_wr_data;
    reg  [15:0]            act_ready_kblocks;
    wire                   act_rd_en;
    wire [ACT_AW-1:0]      act_rd_addr;
    reg  [63:0]            act_rd_data;
    wire                   act_scale_rd_en;
    wire [ACT_SAW-1:0]     act_scale_rd_addr;
    reg  [7:0]             act_scale_rd_data;
    wire [TILE_LANES-1:0]    part_we;
    wire [32*TILE_LANES-1:0] part_addr, part_data, part_acc;
    wire [15:0]              part_kblock;
    wire [8*LQ8S-1:0]        lq8_error_code, lq8_error_detail;
    wire [8*TILE_LANES-1:0]  lane_error_code, lane_error_detail;
    wire [TILE_LANES-1:0]    op_retire;

    ot_a3_tile64 #(
        .LQ8S(LQ8S), .LANES(LANES), .ADDER_STAGES(ADDER_STAGES), .ACC_SLOTS(ACC_SLOTS),
        .STAGING_BYTES(STAGING_BYTES), .STAGING_BUFFERS(STAGING_BUFFERS),
        .STAGING_IN_TILE(STAGING_IN_TILE), .WEIGHT_SOURCE(WEIGHT_SOURCE),
        .ACT_WORDS(ACT_WORDS), .ACT_SCALE_WORDS(ACT_SCALE_WORDS), .LQ8_ABSTRACT(0)
    ) u_dut (
        .clk(clk), .rst_n(rst_n),
        .op_start(op_start), .op_rows(op_rows), .op_cols(op_cols), .op_depth(op_depth), .op_kblock(op_kblock),
        .op_dtype_a(op_dtype_a), .op_dtype_b(op_dtype_b), .op_group(op_group),
        .op_scale_a(op_scale_a), .op_block_a(op_block_a), .op_block_rows_a(op_block_rows_a),
        .op_scale_b(op_scale_b), .op_block_b(op_block_b),
        .op_a_base(op_a_base), .op_a_block_stride(op_a_block_stride),
        .op_scale_a_base(op_scale_a_base), .op_scale_a_block_stride(op_scale_a_block_stride),
        .op_w_base(op_w_base), .op_w_words(op_w_words),
        .op_ws_base(op_ws_base), .op_ws_block_stride(op_ws_block_stride),
        .op_out_base(op_out_base), .op_out_block_stride(op_out_block_stride), .op_out_fp32(op_out_fp32),
        .stg_wr_en(stg_wr_en), .stg_wr_word(stg_wr_word), .stg_wr_data(stg_wr_data),
        .stg_space(stg_space), .stg_fill_word(stg_fill_word),
        .stg_rd_en(stg_rd_en), .stg_rd_addr(stg_rd_addr), .stg_rd_data(stg_rd_data),
        .rom_rd_en(rom_rd_en), .rom_rd_addr(rom_rd_addr), .rom_rd_data(rom_rd_data),
        .ws_rd_en(ws_rd_en), .ws_rd_addr(ws_rd_addr), .ws_rd_data(ws_rd_data),
        .act_wr_en(act_wr_en), .act_wr_addr(act_wr_addr), .act_wr_data(act_wr_data),
        .act_scale_wr_en(act_scale_wr_en), .act_scale_wr_addr(act_scale_wr_addr),
        .act_scale_wr_data(act_scale_wr_data), .act_ready_kblocks(act_ready_kblocks),
        .act_rd_en(act_rd_en), .act_rd_addr(act_rd_addr), .act_rd_data(act_rd_data),
        .act_scale_rd_en(act_scale_rd_en), .act_scale_rd_addr(act_scale_rd_addr),
        .act_scale_rd_data(act_scale_rd_data),
        .part_we(part_we), .part_addr(part_addr), .part_data(part_data), .part_acc(part_acc),
        .part_kblock(part_kblock),
        .busy(dut_busy), .done(dut_done), .kblock_active(dut_kblock_active), .kblock_done(dut_kblock_done),
        .kblock_index(dut_kblock_index),
        .error_code(dut_error_code), .error_detail(dut_error_detail), .error_kblock(dut_error_kblock),
        .error_lq8(dut_error_lq8), .error_lane(dut_error_lane),
        .lq8_error_code(lq8_error_code), .lq8_error_detail(lq8_error_detail),
        .lane_error_code(lane_error_code), .lane_error_detail(lane_error_detail),
        .op_retire(op_retire), .retire_count(dut_retire_count),
        .out_count(dut_out_count), .saturation_count(dut_saturation_count),
        .mac_count(dut_mac_count), .product_count(dut_product_count),
        .staging_underruns(dut_staging_underruns), .staging_overruns(dut_staging_overruns),
        .stream_words_consumed(dut_stream_words_consumed)
    );

    /* verilator lint_off UNUSEDSIGNAL */
    wire [TILE_LANES-1:0] unused_op_retire = op_retire;
    wire [15:0]           unused_part_kblock = part_kblock;
    wire [31:0]           unused_fill = stg_fill_word;
    /* verilator lint_on UNUSEDSIGNAL */

    // -- the tree endpoint beside the tile ------------------------------------------------------------------
    /* verilator lint_off UNUSEDSIGNAL */
    wire        tree_out_last;
    wire [1:0]  tree_error_level;
    wire [15:0] tree_error_tag;
    wire [31:0] tree_adds_count, tree_combines_count;
    /* verilator lint_on UNUSEDSIGNAL */
    ot_a3_tree_endpoint_fp32 #(.LEAVES(8), .ADDER_STAGES(ADDER_STAGES), .TAG_W(16)) u_tree (
        .clk(clk), .rst_n(rst_n),
        .in_valid(tree_in_valid), .in_leaf_count(tree_in_count), .in_leaf(tree_in_leaf),
        .in_tag(tree_in_tag), .in_last(1'b0), .clear(tree_clear),
        .out_valid(tree_out_valid), .out_data(tree_out_data), .out_tag(tree_out_tag), .out_last(tree_out_last),
        .error_code(tree_error_code), .error_detail(tree_error_detail), .error_level(tree_error_level),
        .error_tag(tree_error_tag), .busy(tree_busy),
        .adds_count(tree_adds_count), .combines_count(tree_combines_count)
    );

    // -- wide words assembled from the 32-bit images ------------------------------------------------------
    function automatic [STREAM_BITS-1:0] stream_word;
        input [31:0] index;
        integer k;
        begin
            stream_word = {STREAM_BITS{1'b0}};
            if (index < STREAM_WORDS)
                for (k = 0; k < STREAM_CHUNKS; k = k + 1)
                    stream_word[32*k +: 32] = stream_mem[STREAM_CHUNKS * index + k];
        end
    endfunction
    function automatic [WS_BITS-1:0] ws_word;
        input [31:0] index;
        integer k;
        begin
            ws_word = {WS_BITS{1'b0}};
            if (index < WS_WORDS)
                for (k = 0; k < WS_CHUNKS; k = k + 1)
                    ws_word[32*k +: 32] = ws_mem[WS_CHUNKS * index + k];
        end
    endfunction
    function automatic [63:0] act_word;
        input [31:0] index;
        begin
            act_word = (index < ACT_IMG_WORDS) ? {act_img[2 * index + 1], act_img[2 * index]} : 64'b0;
        end
    endfunction

    // -- one cycle of latency on every external memory the tile reads -------------------------------------
    always @(posedge clk) begin
        if (rom_rd_en)       rom_rd_data <= stream_word(rom_rd_addr);
        if (ws_rd_en)        ws_rd_data  <= ws_word(ws_rd_addr);
    end

    // -- the external staging ring and activation arrays (STAGING_IN_TILE = 0) -----------------------------
    generate
        if (STAGING_IN_TILE == 0) begin : gen_arrays_in_top
            reg [STREAM_BITS-1:0] ring [0:RING_WORDS-1];
            reg [63:0]            act_mem [0:ACT_WORDS-1];
            reg [7:0]             act_scale_mem [0:ACT_SCALE_WORDS-1];
            integer ii;
            initial begin
                for (ii = 0; ii < RING_WORDS; ii = ii + 1) ring[ii] = {STREAM_BITS{1'b0}};
                for (ii = 0; ii < ACT_WORDS; ii = ii + 1) act_mem[ii] = 64'b0;
                for (ii = 0; ii < ACT_SCALE_WORDS; ii = ii + 1) act_scale_mem[ii] = 8'b0;
            end
            always @(posedge clk) begin
                if (stg_wr_en) ring[stg_wr_word[RING_AW-1:0]] <= stg_wr_data;
                if (stg_rd_en) stg_rd_data <= ring[stg_rd_addr];
                if (act_wr_en) act_mem[act_wr_addr] <= act_wr_data;
                if (act_scale_wr_en) act_scale_mem[act_scale_wr_addr] <= act_scale_wr_data;
                if (act_rd_en) act_rd_data <= act_mem[act_rd_addr];
                if (act_scale_rd_en) act_scale_rd_data <= act_scale_mem[act_scale_rd_addr];
            end
        end else begin : gen_arrays_in_tile
            initial begin
                stg_rd_data = {STREAM_BITS{1'b0}};
                act_rd_data = 64'b0;
                act_scale_rd_data = 8'b0;
            end
            /* verilator lint_off UNUSEDSIGNAL */
            wire unused_rd = stg_rd_en | act_rd_en | act_scale_rd_en;
            wire [RING_AW-1:0] unused_stg_addr = stg_rd_addr;
            wire [ACT_AW-1:0] unused_act_addr = act_rd_addr;
            wire [ACT_SAW-1:0] unused_scale_addr = act_scale_rd_addr;
            /* verilator lint_on UNUSEDSIGNAL */
        end
    endgenerate

    // -- the SDN model: one stream word per cycle as the credit allows ------------------------------------
    reg        sdn_active;
    reg [31:0] sdn_ptr;
    reg [31:0] sdn_remaining;
    reg        sdn_ignore;
    always @* begin
        stg_wr_en = sdn_active && (sdn_remaining != 32'b0) && (sdn_ignore || (stg_space != 16'b0));
        stg_wr_word = sdn_ptr;
        stg_wr_data = stream_word(sdn_ptr);
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sdn_active <= 1'b0;
            sdn_ptr <= 32'b0;
            sdn_remaining <= 32'b0;
            sdn_ignore <= 1'b0;
            sdn_written <= 32'b0;
        end else begin
            if (env_start) begin
                sdn_active <= (WEIGHT_SOURCE == 0);
                sdn_ptr <= env_sdn_base;
                sdn_remaining <= env_sdn_words;
                sdn_ignore <= env_sdn_ignore_credit;
                sdn_written <= 32'b0;
            end else if (stg_wr_en) begin
                sdn_ptr <= sdn_ptr + 32'd1;
                sdn_remaining <= sdn_remaining - 32'd1;
                sdn_written <= sdn_written + 32'd1;
                if (sdn_remaining == 32'd1)
                    sdn_active <= 1'b0;
            end
        end
    end

    // -- the H-tree model: slice b + 1 into FIFO slice (b + 1) mod 2 while K-block b runs ------------------
    localparam [1:0] H_IDLE = 2'd0, H_ACT = 2'd1, H_SCALE = 2'd2, H_WAIT = 2'd3;
    reg [1:0]  h_state;
    reg [15:0] h_slice;          // the slice being (or next to be) delivered
    reg [15:0] h_word;
    reg [15:0] h_words_this;     // words of the current slice
    reg [15:0] h_scale_this;
    wire       h_last_slice = (h_slice + 16'd1 == env_blocks);
    wire [15:0] act_words_of_slice   = h_last_slice ? env_act_slice_last : env_act_slice_full;
    wire [15:0] scale_words_of_slice = h_last_slice ? env_scale_slice_last : env_scale_slice_full;
    wire [31:0] act_dst   = env_act_region_base + (h_slice[0] ? {16'b0, env_act_stride} : 32'b0) + {16'b0, h_word};
    wire [31:0] act_src   = env_act_img_base + h_slice * env_act_stride + {16'b0, h_word};
    wire [31:0] scale_dst = env_scale_region_base + (h_slice[0] ? {16'b0, env_scale_stride} : 32'b0) + {16'b0, h_word};
    wire [31:0] scale_src = env_scale_img_base + h_slice * env_scale_stride + {16'b0, h_word};
    always @* begin
        act_wr_en = (h_state == H_ACT);
        act_wr_addr = act_dst[ACT_AW-1:0];
        act_wr_data = act_word(act_src);
        act_scale_wr_en = (h_state == H_SCALE);
        act_scale_wr_addr = scale_dst[ACT_SAW-1:0];
        act_scale_wr_data = (scale_src < ACT_SCALE_IMG_WORDS) ? act_scale_img[scale_src][7:0] : 8'b0;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            h_state <= H_IDLE;
            h_slice <= 16'b0;
            h_word <= 16'b0;
            h_words_this <= 16'b0;
            h_scale_this <= 16'b0;
            act_ready_kblocks <= 16'b0;
        end else begin
            if (env_start) begin
                h_slice <= 16'b0;
                h_word <= 16'b0;
                act_ready_kblocks <= 16'b0;
                h_state <= (env_blocks != 16'b0) ? H_ACT : H_IDLE;
                h_words_this <= env_act_slice_full;
                h_scale_this <= env_scale_slice_full;
                if (env_blocks == 16'd1) begin
                    h_words_this <= env_act_slice_last;
                    h_scale_this <= env_scale_slice_last;
                end
            end else begin
                case (h_state)
                    H_ACT: begin
                        // write word h_word of the activation slice; then the scales
                        if (h_word + 16'd1 >= h_words_this) begin
                            h_word <= 16'b0;
                            h_state <= (h_scale_this != 16'b0) ? H_SCALE : H_WAIT;
                            if (h_scale_this == 16'b0)
                                act_ready_kblocks <= h_slice + 16'd1;
                        end else begin
                            h_word <= h_word + 16'd1;
                        end
                    end
                    H_SCALE: begin
                        if (h_word + 16'd1 >= h_scale_this) begin
                            h_word <= 16'b0;
                            h_state <= H_WAIT;
                            act_ready_kblocks <= h_slice + 16'd1;
                        end else begin
                            h_word <= h_word + 16'd1;
                        end
                    end
                    H_WAIT: begin
                        // the next slice: slices 0 and 1 straight away, slice s >= 2 once
                        // K-block s - 1 is running (its predecessor's FIFO slice is free)
                        if (h_slice + 16'd1 < env_blocks) begin
                            if ((h_slice + 16'd1 < 16'd2) ||
                                (dut_kblock_active && (dut_kblock_index + 16'd1 >= h_slice + 16'd1))) begin
                                h_slice <= h_slice + 16'd1;
                                h_word <= 16'b0;
                                h_words_this <= (h_slice + 16'd2 == env_blocks) ? env_act_slice_last : env_act_slice_full;
                                h_scale_this <= (h_slice + 16'd2 == env_blocks) ? env_scale_slice_last : env_scale_slice_full;
                                h_state <= H_ACT;
                            end
                        end else begin
                            h_state <= H_IDLE;
                        end
                    end
                    default: h_state <= H_IDLE;
                endcase
            end
        end
    end
    assign env_busy = sdn_active || (h_state != H_IDLE);
    /* verilator lint_off UNUSEDSIGNAL */
    wire [15:0] unused_act_words_of_slice = act_words_of_slice;
    wire [15:0] unused_scale_words_of_slice = scale_words_of_slice;
    /* verilator lint_on UNUSEDSIGNAL */

    // -- result memories, one region per tile lane ----------------------------------------------------------
    integer wi;
    always @(posedge clk) begin
        for (wi = 0; wi < TILE_LANES; wi = wi + 1) begin
            if (part_we[wi] && (part_addr[32*wi +: 32] < REGION_WORDS)) begin
                res_mem[wi * REGION_WORDS + part_addr[32*wi +: 32]] <= part_data[32*wi +: 32];
                acc_mem[wi * REGION_WORDS + part_addr[32*wi +: 32]] <= part_acc[32*wi +: 32];
            end
        end
    end

    // -- selected per-LQ8 and per-lane classes ---------------------------------------------------------------------
    assign lq8_rd_error_code   = lq8_error_code[8*lane_rd_sel[5:3] +: 8];
    assign lq8_rd_error_detail = lq8_error_detail[8*lane_rd_sel[5:3] +: 8];
    assign lane_rd_error_code   = lane_error_code[8*lane_rd_sel[5:0] +: 8];
    assign lane_rd_error_detail = lane_error_detail[8*lane_rd_sel[5:0] +: 8];
    /* verilator lint_off UNUSEDSIGNAL */
    wire [1:0] unused_sel = lane_rd_sel[7:6];
    /* verilator lint_on UNUSEDSIGNAL */

    // -- the cross-LQ8 lockstep monitor (test-only visibility through the hierarchy) -------------------------------
    wire [LQ8S-1:0]    mon_a_en, mon_s_en, mon_w_en, mon_ws_en;
    wire [32*LQ8S-1:0] mon_a_addr, mon_w_addr;
    genvar gj;
    generate
        for (gj = 0; gj < LQ8S; gj = gj + 1) begin : gen_mon
            assign mon_a_en[gj]  = u_dut.gen_lq8[gj].gen_rtl.u_lq8.a_rd_en;
            assign mon_s_en[gj]  = u_dut.gen_lq8[gj].gen_rtl.u_lq8.s_rd_en;
            assign mon_w_en[gj]  = u_dut.gen_lq8[gj].gen_rtl.u_lq8.w_rd_en;
            assign mon_ws_en[gj] = u_dut.gen_lq8[gj].gen_rtl.u_lq8.ws_rd_en;
            assign mon_a_addr[32*gj +: 32] = u_dut.gen_lq8[gj].gen_rtl.u_lq8.a_rd_addr;
            assign mon_w_addr[32*gj +: 32] = u_dut.gen_lq8[gj].gen_rtl.u_lq8.w_rd_addr;
        end
    endgenerate

    reg violation_now;
    integer mi;
    always @* begin
        violation_now = 1'b0;
        for (mi = 0; mi < LQ8S; mi = mi + 1) begin
            if (mon_a_en[mi]) begin
                if (mon_a_addr[32*mi +: 32] != u_dut.sel_a_addr) violation_now = 1'b1;
                if (!u_dut.sel_a_valid) violation_now = 1'b1;
            end
            if (mon_w_en[mi]) begin
                if (mon_w_addr[32*mi +: 32] != u_dut.sel_w_addr) violation_now = 1'b1;
                if (!u_dut.sel_w_valid) violation_now = 1'b1;
            end
            // an LQ8 requests every port together (its lanes do); the scale ports follow cfg_scale_*
            if (mon_w_en[mi] != mon_a_en[mi]) violation_now = 1'b1;
            if (mon_s_en[mi] && !mon_a_en[mi]) violation_now = 1'b1;
            if (mon_ws_en[mi] && !mon_a_en[mi]) violation_now = 1'b1;
        end
        if (u_dut.sel_a_valid != (|mon_a_en)) violation_now = 1'b1;
        if (u_dut.sel_w_valid != (|mon_w_en)) violation_now = 1'b1;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            lockstep_violations <= 32'b0;
        else if (violation_now)
            lockstep_violations <= lockstep_violations + 32'd1;
    end
endmodule
