`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Verification top for the RE8 pairwise-tree endpoint
// (results/rtl/abi3_re8.json).
//
// Both checkers -- rtl/test/tb_a3_re8.sv on Icarus and
// rtl/test/a3_re8_harness.cpp on Verilator -- instantiate this module and
// read the same generated images, so the two simulators run identical RTL
// through independently written checkers.  It holds one
// rtl/abi3/ot_a3_tree_endpoint_fp32.sv and the vector, case and meta images
// with read-back ports; the checkers drive the endpoint's input port
// directly and read its output port directly.
//
// Images (tools/build_abi3_re8_vectors.py):
//   re8_vec.hex    one leaf vector per VEC_STRIDE 32-bit words
//   re8_case.hex   one record per case (layout in the checkers)
//   re8_meta.hex   case count and the campaign totals
// ---------------------------------------------------------------------------
module ot_a3_re8_top #(
    parameter integer LEAVES       = 8,
    parameter integer ADDER_STAGES = 3,
    parameter integer TAG_W        = 16,
    parameter integer VEC_WORDS    = 262144,
    parameter integer CASE_WORDS   = 8192,
    parameter integer META_WORDS   = 8
) (
    input  wire                 clk,
    input  wire                 rst_n,

    input  wire                 in_valid,
    input  wire [3:0]           in_leaf_count,
    input  wire [32*LEAVES-1:0] in_leaf,
    input  wire [TAG_W-1:0]     in_tag,
    input  wire                 in_last,
    input  wire                 clear,

    output wire                 out_valid,
    output wire [31:0]          out_data,
    output wire [TAG_W-1:0]     out_tag,
    output wire                 out_last,
    output wire [7:0]           error_code,
    output wire [7:0]           error_detail,
    output wire [1:0]           error_level,
    output wire [TAG_W-1:0]     error_tag,
    output wire                 busy,
    output wire [31:0]          adds_count,
    output wire [31:0]          combines_count,

    input  wire [31:0]          vec_rd_addr,
    output wire [31:0]          vec_rd_data,
    input  wire [31:0]          case_rd_addr,
    output wire [31:0]          case_rd_data,
    input  wire [31:0]          meta_rd_addr,
    output wire [31:0]          meta_rd_data,
    output wire [31:0]          adder_stages,
    output wire [31:0]          leaves
);
    reg [31:0] vec_mem  [0:VEC_WORDS-1];
    reg [31:0] case_mem [0:CASE_WORDS-1];
    reg [31:0] meta_mem [0:META_WORDS-1];

    assign adder_stages = ADDER_STAGES;
    assign leaves = LEAVES;

    initial begin
        $readmemh("re8_vec.hex", vec_mem);
        $readmemh("re8_case.hex", case_mem);
        $readmemh("re8_meta.hex", meta_mem);
    end

    assign vec_rd_data  = (vec_rd_addr < VEC_WORDS) ? vec_mem[vec_rd_addr] : 32'b0;
    assign case_rd_data = (case_rd_addr < CASE_WORDS) ? case_mem[case_rd_addr] : 32'b0;
    assign meta_rd_data = (meta_rd_addr < META_WORDS) ? meta_mem[meta_rd_addr] : 32'b0;

    ot_a3_tree_endpoint_fp32 #(
        .LEAVES(LEAVES),
        .ADDER_STAGES(ADDER_STAGES),
        .TAG_W(TAG_W)
    ) u_dut (
        .clk(clk), .rst_n(rst_n),
        .in_valid(in_valid), .in_leaf_count(in_leaf_count), .in_leaf(in_leaf),
        .in_tag(in_tag), .in_last(in_last), .clear(clear),
        .out_valid(out_valid), .out_data(out_data), .out_tag(out_tag), .out_last(out_last),
        .error_code(error_code), .error_detail(error_detail), .error_level(error_level),
        .error_tag(error_tag), .busy(busy),
        .adds_count(adds_count), .combines_count(combines_count)
    );
endmodule
