`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Verification top for the pipelined contraction lane (gates D1, D2, D5).
//
// Both checkers -- the Icarus testbench rtl/test/tb_a3_lane_pipelined.sv and
// the Verilator harness rtl/test/a3_lane_pipelined_harness.cpp -- instantiate
// this module and read the same generated images, so the two simulators run
// identical RTL through independently written checkers.  This module holds
// memory, the design under test and the untouched sequential reference lane
// (rtl/abi3/ot_a3_mac_lane.sv) side by side on the same operand images, and
// nothing else: the comparison lives in each checker.
//
// Images are produced by tools/build_abi3_lane_vectors.py:
//
//   lane_m0.hex     operand stream A (activations), one 64-bit word per
//                   k-group of g packed storage codes; g = 1 puts one code in
//                   the low bits, which is the sequential lane's own layout
//   lane_m1.hex     operand stream B (weights), the same layout
//   lane_m2.hex     operand-A E8M0 block scales, one code per 32-bit word
//   lane_m3.hex     operand-B E8M0 block scales
//   lane_expect.hex two words per output element: the expected output word
//                   and the expected binary32 accumulator
//   lane_case.hex   one record per case (see the checkers for the layout)
//   lane_meta.hex   case count and the campaign totals
//
// The sequential lane reads 32-bit words; it is given the low half of the
// same 64-bit operand word, so for g = 1 both lanes read exactly the same
// element from exactly the same address.  Its binary32 accumulator is not an
// output of that module; it is captured here from the S_STORE state, the
// cycle in which the reference narrows it, so that gate D1 can compare the
// two lanes at full accumulator precision and not only after the BF16
// rounding that hides most binary32 differences.
// ---------------------------------------------------------------------------
module ot_a3_lane_pipelined_top #(
    parameter integer ADDER_STAGES  = 3,
    parameter integer ACC_SLOTS     = 8,
    parameter integer OPERAND_WORDS = 524288,
    parameter integer SCALE_WORDS   = 65536,
    parameter integer RESULT_WORDS  = 65536,
    parameter integer CASE_WORDS    = 32768,
    parameter integer EXPECT_WORDS  = 131072,
    parameter integer META_WORDS    = 8
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start_dut,
    input  wire        start_ref,
    input  wire [15:0] cfg_rows,
    input  wire [15:0] cfg_cols,
    input  wire [15:0] cfg_depth,
    input  wire [7:0]  cfg_dtype_a,
    input  wire [7:0]  cfg_dtype_b,
    input  wire [7:0]  cfg_group,
    input  wire [31:0] cfg_a_base,
    input  wire [31:0] cfg_b_base,
    input  wire        cfg_scale_a,
    input  wire        cfg_scale_b,
    input  wire [15:0] cfg_block_a,
    input  wire [15:0] cfg_block_b,
    input  wire [15:0] cfg_block_rows_a,
    input  wire [15:0] cfg_block_rows_b,
    input  wire [31:0] cfg_scale_a_base,
    input  wire [31:0] cfg_scale_b_base,
    input  wire [31:0] cfg_out_base,
    input  wire        cfg_out_fp32,

    // design under test
    output wire        dut_busy,
    output wire        dut_done,
    output wire [7:0]  dut_error_code,
    output wire [7:0]  dut_error_detail,
    output wire [31:0] dut_out_count,
    output wire [31:0] dut_saturation_count,
    output wire [31:0] dut_mac_count,
    output wire [31:0] dut_product_count,
    output wire        dut_op_retire,
    output wire        dut_out_we,

    // sequential reference
    output wire        ref_busy,
    output wire        ref_done,
    output wire [7:0]  ref_error_code,
    output wire [31:0] ref_out_count,
    output wire [31:0] ref_saturation_count,
    output wire [31:0] ref_mac_count,

    // read-back ports for the checkers
    input  wire [31:0] case_rd_addr,
    output wire [31:0] case_rd_data,
    input  wire [31:0] expect_rd_addr,
    output wire [31:0] expect_rd_data,
    input  wire [31:0] meta_rd_addr,
    output wire [31:0] meta_rd_data,
    input  wire [31:0] res_rd_addr,
    output wire [31:0] dut_res_rd_data,
    output wire [31:0] dut_acc_rd_data,
    output wire [31:0] ref_res_rd_data,
    output wire [31:0] ref_acc_rd_data,
    output wire [31:0] adder_stages
);
    localparam [31:0] UNWRITTEN = 32'hdead_beef;

    reg [63:0] m0_mem     [0:OPERAND_WORDS-1];
    reg [63:0] m1_mem     [0:OPERAND_WORDS-1];
    reg [31:0] m2_mem     [0:SCALE_WORDS-1];
    reg [31:0] m3_mem     [0:SCALE_WORDS-1];
    reg [31:0] dut_res_mem [0:RESULT_WORDS-1];
    reg [31:0] dut_acc_mem [0:RESULT_WORDS-1];
    reg [31:0] ref_res_mem [0:RESULT_WORDS-1];
    reg [31:0] ref_acc_mem [0:RESULT_WORDS-1];
    reg [31:0] case_mem   [0:CASE_WORDS-1];
    reg [31:0] expect_mem [0:EXPECT_WORDS-1];
    reg [31:0] meta_mem   [0:META_WORDS-1];

    assign adder_stages = ADDER_STAGES;

    integer clear_index;
    initial begin
        $readmemh("lane_m0.hex", m0_mem);
        $readmemh("lane_m1.hex", m1_mem);
        $readmemh("lane_m2.hex", m2_mem);
        $readmemh("lane_m3.hex", m3_mem);
        $readmemh("lane_case.hex", case_mem);
        $readmemh("lane_expect.hex", expect_mem);
        $readmemh("lane_meta.hex", meta_mem);
        // Result memories start at a value no lane writes, so an element a
        // lane never produced is distinguishable from one produced as zero.
        for (clear_index = 0; clear_index < RESULT_WORDS; clear_index = clear_index + 1) begin
            dut_res_mem[clear_index] = UNWRITTEN;
            dut_acc_mem[clear_index] = UNWRITTEN;
            ref_res_mem[clear_index] = UNWRITTEN;
            ref_acc_mem[clear_index] = UNWRITTEN;
        end
    end

    // -- operand memories: one cycle of read latency, four read ports per lane --
    wire        d_a_en, d_b_en, d_s_en, d_t_en;
    wire [31:0] d_a_addr, d_b_addr, d_s_addr, d_t_addr;
    reg  [63:0] d_a_data, d_b_data;
    reg  [31:0] d_s_data, d_t_data;
    wire        r_a_en, r_b_en, r_s_en, r_t_en;
    wire [31:0] r_a_addr, r_b_addr, r_s_addr, r_t_addr;
    reg  [63:0] r_a_word, r_b_word;
    reg  [31:0] r_s_data, r_t_data;

    always @(posedge clk) begin
        if (d_a_en && (d_a_addr < OPERAND_WORDS)) d_a_data <= m0_mem[d_a_addr];
        if (d_b_en && (d_b_addr < OPERAND_WORDS)) d_b_data <= m1_mem[d_b_addr];
        if (d_s_en && (d_s_addr < SCALE_WORDS))   d_s_data <= m2_mem[d_s_addr];
        if (d_t_en && (d_t_addr < SCALE_WORDS))   d_t_data <= m3_mem[d_t_addr];
        if (r_a_en && (r_a_addr < OPERAND_WORDS)) r_a_word <= m0_mem[r_a_addr];
        if (r_b_en && (r_b_addr < OPERAND_WORDS)) r_b_word <= m1_mem[r_b_addr];
        if (r_s_en && (r_s_addr < SCALE_WORDS))   r_s_data <= m2_mem[r_s_addr];
        if (r_t_en && (r_t_addr < SCALE_WORDS))   r_t_data <= m3_mem[r_t_addr];
    end

    // -- result memories ---------------------------------------------------------
    wire        d_out_we, r_out_we;
    wire [31:0] d_out_addr, d_out_data, d_out_acc;
    wire [31:0] r_out_addr, r_out_data;
    reg  [31:0] ref_acc_capture;

    always @(posedge clk) begin
        if (d_out_we && (d_out_addr < RESULT_WORDS)) begin
            dut_res_mem[d_out_addr] <= d_out_data;
            dut_acc_mem[d_out_addr] <= d_out_acc;
        end
        if (r_out_we && (r_out_addr < RESULT_WORDS)) begin
            ref_res_mem[r_out_addr] <= r_out_data;
            ref_acc_mem[r_out_addr] <= ref_acc_capture;
        end
        // The sequential lane narrows its accumulator in S_STORE (state 5)
        // and clears it at the same edge that raises out_we; capture it there.
        if (u_ref.state == 4'd5)
            ref_acc_capture <= u_ref.acc;
    end

    assign case_rd_data   = (case_rd_addr < CASE_WORDS) ? case_mem[case_rd_addr] : 32'b0;
    assign expect_rd_data = (expect_rd_addr < EXPECT_WORDS) ? expect_mem[expect_rd_addr] : 32'b0;
    assign meta_rd_data   = (meta_rd_addr < META_WORDS) ? meta_mem[meta_rd_addr] : 32'b0;
    assign dut_res_rd_data = (res_rd_addr < RESULT_WORDS) ? dut_res_mem[res_rd_addr] : 32'b0;
    assign dut_acc_rd_data = (res_rd_addr < RESULT_WORDS) ? dut_acc_mem[res_rd_addr] : 32'b0;
    assign ref_res_rd_data = (res_rd_addr < RESULT_WORDS) ? ref_res_mem[res_rd_addr] : 32'b0;
    assign ref_acc_rd_data = (res_rd_addr < RESULT_WORDS) ? ref_acc_mem[res_rd_addr] : 32'b0;

    assign dut_out_we = d_out_we;

    ot_a3_lane_pipelined #(
        .ADDER_STAGES(ADDER_STAGES),
        .ACC_SLOTS(ACC_SLOTS)
    ) u_dut (
        .clk(clk), .rst_n(rst_n),
        .start(start_dut),
        .cfg_rows(cfg_rows), .cfg_cols(cfg_cols), .cfg_depth(cfg_depth),
        .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b), .cfg_group(cfg_group),
        .cfg_a_base(cfg_a_base), .cfg_b_base(cfg_b_base),
        .cfg_scale_a(cfg_scale_a), .cfg_scale_b(cfg_scale_b),
        .cfg_block_a(cfg_block_a), .cfg_block_b(cfg_block_b),
        .cfg_block_rows_a(cfg_block_rows_a), .cfg_block_rows_b(cfg_block_rows_b),
        .cfg_scale_a_base(cfg_scale_a_base), .cfg_scale_b_base(cfg_scale_b_base),
        .cfg_out_base(cfg_out_base), .cfg_out_fp32(cfg_out_fp32),
        .a_rd_en(d_a_en), .a_rd_addr(d_a_addr), .a_rd_data(d_a_data),
        .b_rd_en(d_b_en), .b_rd_addr(d_b_addr), .b_rd_data(d_b_data),
        .s_rd_en(d_s_en), .s_rd_addr(d_s_addr), .s_rd_data(d_s_data),
        .t_rd_en(d_t_en), .t_rd_addr(d_t_addr), .t_rd_data(d_t_data),
        .out_we(d_out_we), .out_addr(d_out_addr), .out_data(d_out_data), .out_acc(d_out_acc),
        .busy(dut_busy), .done(dut_done),
        .error_code(dut_error_code), .error_detail(dut_error_detail),
        .out_count(dut_out_count), .saturation_count(dut_saturation_count),
        .mac_count(dut_mac_count), .product_count(dut_product_count),
        .op_retire(dut_op_retire)
    );

    ot_a3_mac_lane u_ref (
        .clk(clk), .rst_n(rst_n),
        .start(start_ref),
        .cfg_rows(cfg_rows), .cfg_cols(cfg_cols), .cfg_depth(cfg_depth),
        .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b),
        .cfg_a_base(cfg_a_base), .cfg_b_base(cfg_b_base),
        .cfg_scale_a(cfg_scale_a), .cfg_scale_b(cfg_scale_b),
        .cfg_block_a(cfg_block_a), .cfg_block_b(cfg_block_b),
        .cfg_block_rows_a(cfg_block_rows_a), .cfg_block_rows_b(cfg_block_rows_b),
        .cfg_scale_a_base(cfg_scale_a_base), .cfg_scale_b_base(cfg_scale_b_base),
        .cfg_out_base(cfg_out_base),
        .a_rd_en(r_a_en), .a_rd_addr(r_a_addr), .a_rd_data(r_a_word[31:0]),
        .b_rd_en(r_b_en), .b_rd_addr(r_b_addr), .b_rd_data(r_b_word[31:0]),
        .s_rd_en(r_s_en), .s_rd_addr(r_s_addr), .s_rd_data(r_s_data),
        .t_rd_en(r_t_en), .t_rd_addr(r_t_addr), .t_rd_data(r_t_data),
        .out_we(r_out_we), .out_addr(r_out_addr), .out_data(r_out_data),
        .busy(ref_busy), .done(ref_done), .error_code(ref_error_code),
        .out_count(ref_out_count), .saturation_count(ref_saturation_count),
        .mac_count(ref_mac_count)
    );
endmodule
