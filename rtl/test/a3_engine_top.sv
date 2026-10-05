`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Verification top for the ABI 3.0 engine datapaths.
//
// Both checkers -- the Icarus testbench (rtl/test/tb_a3_engine.sv) and the C++
// harness for Verilator (rtl/test/a3_engine_harness.cpp) -- instantiate this
// module and read the same generated images, so the two simulators exercise
// identical RTL through independently written checkers.  The comparison itself
// lives in each checker, not here: this module holds memory and the design
// under test and nothing else, so neither checker can pass by agreeing with
// the other.
//
// Images are produced by tools/build_abi3_engine_vectors.py from real ABI 3.0
// deployments built with runtime.abi3.builder.DeploymentBuilder, admitted by
// runtime.abi3.verifier and executed by runtime.sim.device.Device with its
// real engine implementations -- no stubs.  The operand images are the bytes
// the resolved operand views actually held at the issue, read back out of
// device memory, and the expected image is the bytes the engine wrote:
//
//   e3_m0.hex      operand stream 0: activations, logits, gather indices, left
//   e3_m1.hex      operand stream 1: weights, source rows, values, right
//   e3_m2.hex      operand-0 E8M0 block scales
//   e3_m3.hex      operand-1 E8M0 block scales
//   e3_expect.hex  the elements the functional engine wrote
//   e3_case.hex    one descriptor-correlated record per case
//   e3_meta.hex    case count and the campaign totals
//
// Every image carries one element per 32-bit word whatever the storage format
// is, so the width of a BF16 code, an FP8 code, an MXFP4 nibble and a U32
// index is a decode question inside the datapath rather than an addressing
// question here.
// ---------------------------------------------------------------------------
module ot_a3_engine_top #(
    parameter integer M0_WORDS     = 40960,
    parameter integer M1_WORDS     = 40960,
    parameter integer M2_WORDS     = 4096,
    parameter integer M3_WORDS     = 4096,
    parameter integer RESULT_WORDS = 40960,
    parameter integer CASE_WORDS   = 16384,
    parameter integer META_WORDS   = 8
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [7:0]  cfg_family,
    input  wire [7:0]  cfg_sub,
    input  wire [15:0] cfg_rows,
    input  wire [15:0] cfg_cols,
    input  wire [15:0] cfg_depth,
    input  wire [31:0] cfg_count,
    input  wire [7:0]  cfg_dtype_a,
    input  wire [7:0]  cfg_dtype_b,
    input  wire [31:0] cfg_a_base,
    input  wire [31:0] cfg_b_base,
    input  wire [31:0] cfg_c_base,
    input  wire [31:0] cfg_out_base,
    input  wire        cfg_scale_a,
    input  wire        cfg_scale_b,
    input  wire [15:0] cfg_block_a,
    input  wire [15:0] cfg_block_b,
    input  wire [15:0] cfg_block_rows_a,
    input  wire [15:0] cfg_block_rows_b,
    input  wire [31:0] cfg_scale_a_base,
    input  wire [31:0] cfg_scale_b_base,
    input  wire [31:0] cfg_slots,
    input  wire [31:0] cfg_trailing,
    input  wire [31:0] cfg_extent,
    input  wire [3:0]  cfg_input_valid,
    input  wire [1:0]  cfg_output_valid,
    input  wire [31:0] cfg_input_dtypes,
    input  wire [15:0] cfg_output_dtypes,
    input  wire [23:0] cfg_view_ranks,
    input  wire [5:0]  cfg_view_scaled,
    input  wire        cfg_profile_valid,
    input  wire [31:0] cfg_profile_dtypes,
    input  wire [7:0]  cfg_rounding_mode,
    input  wire [7:0]  cfg_reduction_order,
    input  wire        cfg_profile_saturate,
    input  wire [7:0]  cfg_nan_policy,
    input  wire [31:0] cfg_profile_scale_bits,
    input  wire [31:0] cfg_epsilon_bits,
    input  wire [31:0] cfg_profile_flags,
    input  wire [127:0] cfg_input0_dims,
    input  wire [127:0] cfg_input1_dims,
    input  wire [127:0] cfg_input2_dims,
    input  wire [127:0] cfg_input3_dims,
    input  wire [127:0] cfg_output0_dims,
    input  wire [127:0] cfg_output1_dims,
    input  wire [31:0] cfg_contract_0,
    input  wire [31:0] cfg_contract_1,
    input  wire [31:0] cfg_contract_2,
    input  wire [31:0] cfg_contract_3,
    input  wire [31:0] cfg_contract_4,
    input  wire [31:0] cfg_contract_5,
    input  wire [31:0] cfg_contract_6,
    input  wire [31:0] cfg_contract_7,
    input  wire [3:0]  cfg_aux_valid,
    input  wire [31:0] cfg_aux0,
    input  wire [31:0] cfg_aux1,
    input  wire [31:0] cfg_aux2,
    input  wire [31:0] cfg_aux3,

    output wire        busy,
    output wire        done,
    output wire [7:0]  error_code,
    output wire [31:0] result_count,
    output wire [31:0] saturation_count,
    output wire [31:0] work_count,
    output wire [31:0] token,
    output wire [31:0] tie_multiplicity,

    // read-back ports for the checkers
    input  wire [31:0] case_rd_addr,
    output wire [31:0] case_rd_data,
    input  wire [31:0] res_rd_addr,
    output wire [31:0] res_rd_data,
    input  wire [31:0] meta_rd_addr,
    output wire [31:0] meta_rd_data,

    // Combinational storage-format decode probe.  Both checkers walk the
    // complete code space of every format the datapaths read -- 256 E4M3FN
    // codes, 16 E2M1 nibbles, 256 E8M0 codes and all 65,536 BF16 patterns --
    // against e3_decode.hex, which tools/build_abi3_engine_vectors.py
    // enumerates from runtime.sim.formats.  Those tables are themselves
    // enumerated from the exact Fraction decoders in
    // runtime/reference/formats.py, so a drift on either side fails here.
    input  wire [7:0]  probe_format,
    input  wire [31:0] probe_word,
    output wire [33:0] probe_result,

    // Combinational binary32 arithmetic probe.  The engine cases exercise the
    // adder and the multiplier on the value distribution real operands
    // produce; this port exercises them on the distribution that breaks
    // them -- signed zeros, subnormals, exact cancellations, ties, the
    // overflow boundary -- against runtime.reference.formats, whose
    // fractions.Fraction arithmetic rounds once and involves no host floating
    // point at all.
    input  wire [31:0] arith_a,
    input  wire [31:0] arith_b,
    input  wire [31:0] arith_accumulator,
    input  wire [15:0] arith_left_bf16,
    input  wire [15:0] arith_right_bf16,
    output wire [33:0] arith_add,
    output wire [33:0] arith_mul,
    output wire [33:0] arith_product_add,
    output wire [18:0] arith_bf16
);
    reg [31:0] m0_mem   [0:M0_WORDS-1];
    reg [31:0] m1_mem   [0:M1_WORDS-1];
    reg [31:0] m2_mem   [0:M2_WORDS-1];
    reg [31:0] m3_mem   [0:M3_WORDS-1];
    reg [31:0] res_mem  [0:RESULT_WORDS-1];
    reg [31:0] case_mem [0:CASE_WORDS-1];
    reg [31:0] meta_mem [0:META_WORDS-1];

    assign probe_result = ot_a3_format_pkg::decode_element(probe_format, probe_word);
    assign arith_add  = ot_fp32_rne_pkg::fp32_add_rne(arith_a, arith_b);
    assign arith_mul  = ot_fp32_rne_pkg::fp32_mul_rne(arith_a, arith_b);
    assign arith_product_add =
        ot_fp32_rne_pkg::bf16_bf16_fp32_product_add_rne(
            arith_accumulator, arith_left_bf16, arith_right_bf16
        );
    assign arith_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(arith_a);

    integer clear_index;

    initial begin
        $readmemh("e3_m0.hex", m0_mem);
        $readmemh("e3_m1.hex", m1_mem);
        $readmemh("e3_m2.hex", m2_mem);
        $readmemh("e3_m3.hex", m3_mem);
        $readmemh("e3_case.hex", case_mem);
        $readmemh("e3_meta.hex", meta_mem);
        // The result memory starts at a value no engine writes, so an element
        // the design never produced is distinguishable from one it produced as
        // zero.  A checker that only compared the elements written would not
        // notice a datapath that wrote too few.
        for (clear_index = 0; clear_index < RESULT_WORDS; clear_index = clear_index + 1)
            res_mem[clear_index] = 32'hdead_beef;
    end

    wire        m0_rd_en, m1_rd_en, m2_rd_en, m3_rd_en;
    wire [31:0] m0_rd_addr, m1_rd_addr, m2_rd_addr, m3_rd_addr;
    reg  [31:0] m0_rd_data, m1_rd_data, m2_rd_data, m3_rd_data;

    always @(posedge clk) begin
        if (m0_rd_en && (m0_rd_addr < M0_WORDS)) m0_rd_data <= m0_mem[m0_rd_addr];
        if (m1_rd_en && (m1_rd_addr < M1_WORDS)) m1_rd_data <= m1_mem[m1_rd_addr];
        if (m2_rd_en && (m2_rd_addr < M2_WORDS)) m2_rd_data <= m2_mem[m2_rd_addr];
        if (m3_rd_en && (m3_rd_addr < M3_WORDS)) m3_rd_data <= m3_mem[m3_rd_addr];
    end

    wire        out_we;
    wire [31:0] out_addr;
    wire [31:0] out_data;

    always @(posedge clk) begin
        if (out_we && (out_addr < RESULT_WORDS))
            res_mem[out_addr] <= out_data;
    end

    assign case_rd_data = (case_rd_addr < CASE_WORDS)
                          ? case_mem[case_rd_addr] : 32'b0;
    assign res_rd_data  = (res_rd_addr < RESULT_WORDS)
                          ? res_mem[res_rd_addr] : 32'b0;
    assign meta_rd_data = (meta_rd_addr < META_WORDS)
                          ? meta_mem[meta_rd_addr] : 32'b0;

    ot_a3_engine_array engines (
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .cfg_family(cfg_family),
        .cfg_sub(cfg_sub),
        .cfg_rows(cfg_rows),
        .cfg_cols(cfg_cols),
        .cfg_depth(cfg_depth),
        .cfg_count(cfg_count),
        .cfg_dtype_a(cfg_dtype_a),
        .cfg_dtype_b(cfg_dtype_b),
        .cfg_a_base(cfg_a_base),
        .cfg_b_base(cfg_b_base),
        .cfg_c_base(cfg_c_base),
        .cfg_out_base(cfg_out_base),
        .cfg_scale_a(cfg_scale_a),
        .cfg_scale_b(cfg_scale_b),
        .cfg_block_a(cfg_block_a),
        .cfg_block_b(cfg_block_b),
        .cfg_block_rows_a(cfg_block_rows_a),
        .cfg_block_rows_b(cfg_block_rows_b),
        .cfg_scale_a_base(cfg_scale_a_base),
        .cfg_scale_b_base(cfg_scale_b_base),
        .cfg_slots(cfg_slots),
        .cfg_trailing(cfg_trailing),
        .cfg_extent(cfg_extent),
        .cfg_input_valid(cfg_input_valid),
        .cfg_output_valid(cfg_output_valid),
        .cfg_input_dtypes(cfg_input_dtypes),
        .cfg_output_dtypes(cfg_output_dtypes),
        .cfg_view_ranks(cfg_view_ranks),
        .cfg_view_scaled(cfg_view_scaled),
        .cfg_profile_valid(cfg_profile_valid),
        .cfg_profile_dtypes(cfg_profile_dtypes),
        .cfg_rounding_mode(cfg_rounding_mode),
        .cfg_reduction_order(cfg_reduction_order),
        .cfg_profile_saturate(cfg_profile_saturate),
        .cfg_nan_policy(cfg_nan_policy),
        .cfg_profile_scale_bits(cfg_profile_scale_bits),
        .cfg_epsilon_bits(cfg_epsilon_bits),
        .cfg_profile_flags(cfg_profile_flags),
        .cfg_input0_dims(cfg_input0_dims),
        .cfg_input1_dims(cfg_input1_dims),
        .cfg_input2_dims(cfg_input2_dims),
        .cfg_input3_dims(cfg_input3_dims),
        .cfg_output0_dims(cfg_output0_dims),
        .cfg_output1_dims(cfg_output1_dims),
        .cfg_contract_0(cfg_contract_0),
        .cfg_contract_1(cfg_contract_1),
        .cfg_contract_2(cfg_contract_2),
        .cfg_contract_3(cfg_contract_3),
        .cfg_contract_4(cfg_contract_4),
        .cfg_contract_5(cfg_contract_5),
        .cfg_contract_6(cfg_contract_6),
        .cfg_contract_7(cfg_contract_7),
        .cfg_aux_valid(cfg_aux_valid),
        .cfg_aux0(cfg_aux0), .cfg_aux1(cfg_aux1),
        .cfg_aux2(cfg_aux2), .cfg_aux3(cfg_aux3),
        .m0_rd_en(m0_rd_en), .m0_rd_addr(m0_rd_addr), .m0_rd_data(m0_rd_data),
        .m1_rd_en(m1_rd_en), .m1_rd_addr(m1_rd_addr), .m1_rd_data(m1_rd_data),
        .m2_rd_en(m2_rd_en), .m2_rd_addr(m2_rd_addr), .m2_rd_data(m2_rd_data),
        .m3_rd_en(m3_rd_en), .m3_rd_addr(m3_rd_addr), .m3_rd_data(m3_rd_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy),
        .done(done),
        .error_code(error_code),
        .result_count(result_count),
        .saturation_count(saturation_count),
        .work_count(work_count),
        .token(token),
        .tie_multiplicity(tie_multiplicity)
    );
endmodule
