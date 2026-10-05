`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// OR64: the operand receiver -- the block between a tree root arriving off the
// link and a consumer tile's activation FIFO
// (docs/CHIP_ARCHITECTURE_DESIGN.md sections 3.6, 4.4 and 13 item 13).
//
// Why it exists.  results/rtl/abi3_boundary_chain.json established by
// elaboration that ot_a3_tile64's act_wr_en is an internal net of the T64
// vehicle: nothing in the design writes a reduction root into a consumer
// tile's activation FIFO, and the tile's own record says so in its own words
// ("the T64 bench models the H-tree and its record already declares that a
// does_not_establish").  This is that term, designed rather than improvised
// for a measurement.
//
// What it does.  It accepts one binary32 root per cycle with the tag the
// collector gave it (the output element), performs the output stage's SINGLE
// rounding to the consumer's activation storage format, packs the consumer's
// activation word, writes it on the tile's activation broadcast port, and --
// one cycle after the last word of a K-block slice has landed in the array --
// advances act_ready_kblocks, which is the tile's own operand-readiness gate
// (ot_a3_tile64 S_WAIT: act_ok = act_ready_kblocks > kblock_index).
//
// Why it rounds.  Section 4.4: "Output conversion occurs once after the
// complete reduction."  The consumer settles the format, not this block: the
// lane reads its activation as a 16/8/4-bit storage code out of a packed
// 64-bit word (ot_a3_lane_pipelined.sv element_code / ot_a3_lane_pkg
// element_width) and has no binary32 activation path at all, so a root cannot
// be delivered unrounded.  The rounding is ot_fp32_rne_pkg::fp32_to_bf16_rne,
// the same function the lane's own output stage and ot_a3_vector_add use --
// not a second implementation of it.
//
// Word packing, from the tile's own rule.  A slice of K-block b is
// rows x ceil(depth_b / g) 64-bit words at op_a_base + (b mod 2) x
// op_a_block_stride, and word w holds the g elements of one k-group at
// element_width(dtype) bits each.  So element index t goes to word t / g at
// bit (t mod g) x width.  Roots arrive in ascending tag order (the collector
// emits ascending slots), so the receiver accumulates g elements and writes
// the word once; a tag out of order is REFUSED rather than reordered
// (DETAIL_RECV_TAG_ORDER), because a reordering buffer here would be an
// invented structure inside a measurement.
//
// What it refuses, and why the refusal is the honest answer.
//   * a slice that never fills stalls the consumer rather than being flushed
//     short: a partially filled final word is a packing rule section 4.4 does
//     not state, so act_ready_kblocks simply does not advance.
//   * a scaled activation (cfg_scaled) is refused: the E8M0 activation
//     interleave is recorded as unwritten in ot_a3_tile64's own header, and
//     the scale a quantising output stage would emit is not a tree root.
//   * a format other than BF16 is refused: fp32 -> FP8/MXFP4 is a two-output
//     quantisation, which ot_a3_vector_convert also refuses.
// Details continue the family's numbering (0..12 lane, 16..17 LQ8, 18..23
// tile, 24..26 tree, 27..32 collector):
//   33 DETAIL_RECV_FORMAT        dtype / group / scaled unsupported
//   34 DETAIL_RECV_WINDOW        slice geometry inadmissible
//   35 DETAIL_RECV_TAG_ORDER     a root out of ascending tag order
//   36 DETAIL_RECV_ACT_RANGE     a word outside the activation FIFO
//   37 DETAIL_RECV_SLICE_OVERRUN more slices offered than cfg_blocks
//   38 DETAIL_RECV_ROOT_NONFINITE a root that is NaN or infinity
// A fault stops delivery, holds error_* until clear, ignores input, and never
// advances act_ready_kblocks: the consumer stalls rather than running on an
// operand the receiver could not deliver.
//
// Package constants are referred to by scope, never by wildcard import (OI-43).
// ---------------------------------------------------------------------------
module ot_a3_operand_receiver #(
    parameter integer ACT_WORDS       = 2048,   // the consumer tile's activation FIFO
    parameter integer ACT_SCALE_WORDS = 64,
    parameter integer TAG_W           = 16
) (
    input  wire        clk,
    input  wire        rst_n,

    // -- configuration, sampled on cfg_start (the consumer's own descriptor) ----------
    input  wire        cfg_start,
    input  wire [15:0] cfg_blocks,          // K-block slices to deliver
    input  wire [15:0] cfg_slice_words,     // 64-bit words per slice = rows x ceil(depth_b / g)
    input  wire [7:0]  cfg_group,           // g: elements per activation word (1, 2, 4)
    input  wire [7:0]  cfg_dtype,           // the consumer's activation format
    input  wire        cfg_scaled,          // the consumer reads block scales (refused)
    input  wire [31:0] cfg_base,            // op_a_base: FIFO word of slice 0
    input  wire [15:0] cfg_stride,          // op_a_block_stride
    input  wire        clear,

    // -- the root, off the link -----------------------------------------------------------
    input  wire             in_valid,
    input  wire [31:0]      in_data,
    input  wire [TAG_W-1:0] in_tag,
    input  wire             in_last,

    // -- the consumer tile's activation broadcast port --------------------------------------
    output reg                          act_wr_en,
    output reg  [$clog2(ACT_WORDS)-1:0] act_wr_addr,
    output reg  [63:0]                  act_wr_data,
    output wire                         act_scale_wr_en,
    output wire [$clog2(ACT_SCALE_WORDS)-1:0] act_scale_wr_addr,
    output wire [7:0]                   act_scale_wr_data,
    output reg  [15:0]                  act_ready_kblocks,

    // -- status -------------------------------------------------------------------------------
    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [7:0]  error_detail,
    output reg  [TAG_W-1:0] error_tag,
    output reg  [31:0] roots_count,
    output reg  [31:0] words_written,
    output reg  [15:0] slices_ready,
    output reg  [31:0] saturation_count
);
    localparam integer ACT_AW  = $clog2(ACT_WORDS);
    localparam integer ACT_SAW = $clog2(ACT_SCALE_WORDS);

    localparam [7:0] ERR_NONE  = ot_a3_lane_pkg::ERR_NONE;
    localparam [7:0] ERR_SHAPE = ot_a3_lane_pkg::ERR_SHAPE;
    localparam [7:0] ERR_OPERAND_NONFINITE = ot_a3_lane_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] DETAIL_NONE = ot_a3_lane_pkg::DETAIL_NONE;
    localparam [7:0] DETAIL_RECV_FORMAT         = 8'd33;
    localparam [7:0] DETAIL_RECV_WINDOW         = 8'd34;
    localparam [7:0] DETAIL_RECV_TAG_ORDER      = 8'd35;
    localparam [7:0] DETAIL_RECV_ACT_RANGE      = 8'd36;
    localparam [7:0] DETAIL_RECV_SLICE_OVERRUN  = 8'd37;
    localparam [7:0] DETAIL_RECV_ROOT_NONFINITE = 8'd38;

    localparam [7:0] FMT_BF16 = ot_a3_lane_pkg::FMT_BF16;

    // -- sampled configuration -----------------------------------------------------------------
    reg [15:0] d_blocks, d_slice_words, d_stride;
    reg [7:0]  d_group;
    reg [31:0] d_base;
    reg [5:0]  d_width;               // element width in bits

    reg        running;
    reg [15:0] slice_ctr;             // the slice being filled
    reg [15:0] word_index;            // word within the slice
    reg [7:0]  elem_ctr;              // element within the word
    reg [63:0] word_acc;
    reg [TAG_W-1:0] expect_tag;
    reg        slice_done_d;          // the slice's last word was written last cycle

    // The activation scale port exists so the receiver presents the tile's whole
    // broadcast port; a scaled activation is refused at admission, so it never drives.
    assign act_scale_wr_en   = 1'b0;
    assign act_scale_wr_addr = {ACT_SAW{1'b0}};
    assign act_scale_wr_data = 8'b0;

    // -- admission -------------------------------------------------------------------------------
    wire group_ok  = (cfg_group == 8'd1) || (cfg_group == 8'd2) || (cfg_group == 8'd4);
    wire format_ok = (cfg_dtype == FMT_BF16) && group_ok && !cfg_scaled;
    wire [31:0] slice_span = {16'b0, cfg_slice_words};
    wire [31:0] slice_top0 = cfg_base + slice_span;
    // Admission checks the slice-0 window only.  The odd slice's destination
    // depends on cfg_stride, which the descriptor supplies per operation, and
    // an out-of-range odd slice is a RUN-TIME refusal (DETAIL_RECV_ACT_RANGE)
    // so that the two failures stay distinct instead of collapsing into one.
    wire window_ok = (cfg_slice_words != 16'd0) && (cfg_blocks != 16'd0) &&
                     (slice_top0 <= ACT_WORDS);

    // -- the arriving root -------------------------------------------------------------------------
    wire [18:0] narrowed = ot_fp32_rne_pkg::fp32_to_bf16_rne(in_data);
    wire        root_nonfinite = (narrowed[18:17] != 2'd0);
    wire        accept = running && in_valid;
    wire        tag_bad = accept && (in_tag != expect_tag);
    wire        slice_overrun = accept && (slice_ctr >= d_blocks);
    wire [63:0] acc_next = word_acc |
        ({48'b0, narrowed[15:0]} << ({6'b0, elem_ctr[3:0]} * {4'b0, d_width}));
    wire        word_last = (elem_ctr + 8'd1 >= d_group);
    wire [31:0] dst_word = d_base + (slice_ctr[0] ? {16'b0, d_stride} : 32'b0) + {16'b0, word_index};
    wire        act_range = accept && word_last && (dst_word >= ACT_WORDS);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            running <= 1'b0;
            busy <= 1'b0;
            done <= 1'b0;
            act_wr_en <= 1'b0;
            act_wr_addr <= {ACT_AW{1'b0}};
            act_wr_data <= 64'b0;
            act_ready_kblocks <= 16'b0;
            error_code <= ERR_NONE;
            error_detail <= DETAIL_NONE;
            error_tag <= {TAG_W{1'b0}};
            roots_count <= 32'b0;
            words_written <= 32'b0;
            slices_ready <= 16'b0;
            saturation_count <= 32'b0;
            d_blocks <= 16'b0; d_slice_words <= 16'b0; d_stride <= 16'b0;
            d_group <= 8'b0; d_base <= 32'b0; d_width <= 4'b0;
            slice_ctr <= 16'b0;
            word_index <= 16'b0;
            elem_ctr <= 8'b0;
            word_acc <= 64'b0;
            expect_tag <= {TAG_W{1'b0}};
            slice_done_d <= 1'b0;
        end else begin
            done <= 1'b0;
            act_wr_en <= 1'b0;

            if (clear && !cfg_start) begin
                running <= 1'b0;
                busy <= 1'b0;
                slice_done_d <= 1'b0;
                error_code <= ERR_NONE;
                error_detail <= DETAIL_NONE;
                error_tag <= {TAG_W{1'b0}};
            end

            if (cfg_start) begin
                d_blocks <= cfg_blocks;
                d_slice_words <= cfg_slice_words;
                d_group <= cfg_group;
                d_stride <= cfg_stride;
                d_base <= cfg_base;
                d_width <= ot_a3_lane_pkg::element_width(cfg_dtype);
                slice_ctr <= 16'b0;
                word_index <= 16'b0;
                elem_ctr <= 8'b0;
                word_acc <= 64'b0;
                expect_tag <= {TAG_W{1'b0}};
                slice_done_d <= 1'b0;
                act_ready_kblocks <= 16'b0;
                roots_count <= 32'b0;
                words_written <= 32'b0;
                slices_ready <= 16'b0;
                saturation_count <= 32'b0;
                error_code <= ERR_NONE;
                error_detail <= DETAIL_NONE;
                error_tag <= {TAG_W{1'b0}};
                if (!format_ok) begin
                    running <= 1'b0; busy <= 1'b0; done <= 1'b1;
                    error_code <= ERR_SHAPE; error_detail <= DETAIL_RECV_FORMAT;
                end else if (!window_ok) begin
                    running <= 1'b0; busy <= 1'b0; done <= 1'b1;
                    error_code <= ERR_SHAPE; error_detail <= DETAIL_RECV_WINDOW;
                end else begin
                    running <= 1'b1; busy <= 1'b1;
                end
            end else begin
                // one cycle after the slice's last word landed in the array
                if (slice_done_d) begin
                    slice_done_d <= 1'b0;
                    act_ready_kblocks <= slice_ctr;
                    slices_ready <= slice_ctr;
                    if (slice_ctr >= d_blocks) begin
                        running <= 1'b0;
                        busy <= 1'b0;
                        done <= 1'b1;
                    end
                end
                if (accept) begin
                    roots_count <= roots_count + 32'd1;
                    if (tag_bad) begin
                        running <= 1'b0; busy <= 1'b0; done <= 1'b1;
                        error_code <= ERR_SHAPE; error_detail <= DETAIL_RECV_TAG_ORDER;
                        error_tag <= in_tag;
                    end else if (slice_overrun) begin
                        running <= 1'b0; busy <= 1'b0; done <= 1'b1;
                        error_code <= ERR_SHAPE; error_detail <= DETAIL_RECV_SLICE_OVERRUN;
                        error_tag <= in_tag;
                    end else if (root_nonfinite) begin
                        running <= 1'b0; busy <= 1'b0; done <= 1'b1;
                        error_code <= ERR_OPERAND_NONFINITE;
                        error_detail <= DETAIL_RECV_ROOT_NONFINITE;
                        error_tag <= in_tag;
                    end else if (act_range) begin
                        running <= 1'b0; busy <= 1'b0; done <= 1'b1;
                        error_code <= ERR_SHAPE; error_detail <= DETAIL_RECV_ACT_RANGE;
                        error_tag <= in_tag;
                    end else begin
                        expect_tag <= in_tag + {{(TAG_W-1){1'b0}}, 1'b1};
                        if (narrowed[16])
                            saturation_count <= saturation_count + 32'd1;
                        if (word_last) begin
                            act_wr_en <= 1'b1;
                            act_wr_addr <= dst_word[ACT_AW-1:0];
                            act_wr_data <= acc_next;
                            words_written <= words_written + 32'd1;
                            word_acc <= 64'b0;
                            elem_ctr <= 8'b0;
                            if (word_index + 16'd1 >= d_slice_words) begin
                                word_index <= 16'b0;
                                slice_ctr <= slice_ctr + 16'd1;
                                slice_done_d <= 1'b1;
                            end else begin
                                word_index <= word_index + 16'd1;
                            end
                        end else begin
                            word_acc <= acc_next;
                            elem_ctr <= elem_ctr + 8'd1;
                        end
                    end
                end
            end
        end
    end

    /* verilator lint_off UNUSEDSIGNAL */
    wire unused_in_last = in_last;
    /* verilator lint_on UNUSEDSIGNAL */
endmodule
