`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Verification top for ROUTE.BLOCK_MAX (rtl/abi3/ot_a3_route_block_max.sv),
// record results/rtl/a3_v41_block_max_campaign.json.
//
// Both checkers -- rtl/test/tb_a3_route_block_max.sv on Icarus Verilog and
// rtl/test/a3_route_block_max_harness.cpp on the pinned Verilator 5.050 --
// instantiate THIS module and read the SAME generated images, so the two
// simulators run identical RTL through two independently written checkers.
// The checkers drive the block's input port and read its output port directly;
// no sequencing lives here, because sequencing shared between the checkers
// would be sequencing neither of them checks.
//
// The score port is presented as LANES_MAX fixed 32-bit words rather than as
// SCORE_W*BLOCK bits so that one C++ checker drives every parameter shape the
// campaign elaborates: lane k is word k, taken from its low SCORE_W bits.
// LANES_MAX is a harness convenience and is unrelated to the block's geometry;
// only BLOCK of the words are wired.
//
// The images (tools/build_a3_v41_block_max_vectors.py) are NOT held here: each
// checker loads bm_meta.hex, bm_case.hex, bm_vec.hex and bm_expect.hex with its
// own reader, the Icarus checker through $readmemh and the C++ checker through
// its own hex parser, so neither inherits the other's view of them.  What this
// module does carry is the ELABORATED parameter values, reported on param_*
// ports, which is how each checker confirms it is driving the shape the images
// were built for.
// ---------------------------------------------------------------------------
//: the harness ports are fixed 32-bit words so one C++ checker serves every
//: parameter shape; the bits above the block's own widths are deliberately
//: unwired.
/* verilator lint_off UNUSEDSIGNAL */
module ot_a3_route_block_max_top #(
    parameter integer BLOCK       = 8,
    parameter integer SCORE_W     = 32,
    parameter integer EXP_W       = 8,
    parameter integer MANT_W      = 23,
    parameter integer MAX_BLOCKS  = 2048,
    parameter integer BLOCK_ID_W  = 16,
    parameter integer TAG_W       = 16,
    parameter integer COUNT_W     = 8,
    parameter integer CMP_STAGES  = 1,
    parameter integer COUNTER_W   = 32,
    parameter integer LANES_MAX   = 16
) (
    input  wire                       clk,
    input  wire                       rst_n,

    input  wire                       in_valid,
    input  wire [31:0]                in_valid_count_w,
    input  wire [32*LANES_MAX-1:0]    in_score_words,
    input  wire                       in_row_last,
    input  wire [31:0]                in_tag_w,
    input  wire                       clear,

    output wire                       out_valid,
    output wire [31:0]                out_score_w,
    output wire [31:0]                out_block_id_w,
    output wire                       out_row_last,
    output wire [31:0]                out_tag_w,
    output wire [7:0]                 error_code,
    output wire [7:0]                 error_detail,
    output wire [31:0]                error_block_id_w,
    output wire [31:0]                error_tag_w,
    output wire                       busy,
    output wire [31:0]                pipeline_depth,
    output wire [31:0]                blocks_count_w,
    output wire [31:0]                positions_count_w,
    output wire [31:0]                rows_count_w,

    output wire [31:0]                param_block,
    output wire [31:0]                param_score_w,
    output wire [31:0]                param_exp_w,
    output wire [31:0]                param_mant_w,
    output wire [31:0]                param_max_blocks,
    output wire [31:0]                param_cmp_stages,
    output wire [31:0]                param_lanes_max
);
    assign param_block      = BLOCK;
    assign param_score_w    = SCORE_W;
    assign param_exp_w      = EXP_W;
    assign param_mant_w     = MANT_W;
    assign param_max_blocks = MAX_BLOCKS;
    assign param_cmp_stages = CMP_STAGES;
    assign param_lanes_max  = LANES_MAX;

    //: lane k of the block takes the low SCORE_W bits of harness word k.
    wire [SCORE_W*BLOCK-1:0] dut_in_score;
    genvar gk;
    generate
        for (gk = 0; gk < BLOCK; gk = gk + 1) begin : g_lane
            assign dut_in_score[SCORE_W*gk +: SCORE_W] = in_score_words[32*gk +: SCORE_W];
        end
    endgenerate

    wire [SCORE_W-1:0]    dut_out_score;
    wire [BLOCK_ID_W-1:0] dut_out_block_id;
    wire [TAG_W-1:0]      dut_out_tag;
    wire [BLOCK_ID_W-1:0] dut_error_block_id;
    wire [TAG_W-1:0]      dut_error_tag;
    wire [COUNTER_W-1:0]  dut_blocks_count;
    wire [COUNTER_W-1:0]  dut_positions_count;
    wire [COUNTER_W-1:0]  dut_rows_count;

    assign out_score_w      = {{(32-SCORE_W){1'b0}},    dut_out_score};
    assign out_block_id_w   = {{(32-BLOCK_ID_W){1'b0}}, dut_out_block_id};
    assign out_tag_w        = {{(32-TAG_W){1'b0}},      dut_out_tag};
    assign error_block_id_w = {{(32-BLOCK_ID_W){1'b0}}, dut_error_block_id};
    assign error_tag_w      = {{(32-TAG_W){1'b0}},      dut_error_tag};
    assign blocks_count_w    = dut_blocks_count;
    assign positions_count_w = dut_positions_count;
    assign rows_count_w      = dut_rows_count;

    ot_a3_route_block_max #(
        .BLOCK(BLOCK), .SCORE_W(SCORE_W), .EXP_W(EXP_W), .MANT_W(MANT_W),
        .MAX_BLOCKS(MAX_BLOCKS), .BLOCK_ID_W(BLOCK_ID_W), .TAG_W(TAG_W),
        .COUNT_W(COUNT_W), .CMP_STAGES(CMP_STAGES), .COUNTER_W(COUNTER_W)
    ) u_dut (
        .clk(clk), .rst_n(rst_n),
        .in_valid(in_valid),
        .in_valid_count(in_valid_count_w[COUNT_W-1:0]),
        .in_score(dut_in_score),
        .in_row_last(in_row_last),
        .in_tag(in_tag_w[TAG_W-1:0]),
        .clear(clear),
        .out_valid(out_valid), .out_score(dut_out_score), .out_block_id(dut_out_block_id),
        .out_row_last(out_row_last), .out_tag(dut_out_tag),
        .error_code(error_code), .error_detail(error_detail),
        .error_block_id(dut_error_block_id), .error_tag(dut_error_tag),
        .busy(busy), .pipeline_depth(pipeline_depth),
        .blocks_count(dut_blocks_count), .positions_count(dut_positions_count),
        .rows_count(dut_rows_count)
    );
endmodule
/* verilator lint_on UNUSEDSIGNAL */
