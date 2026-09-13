`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The ABI 3.0 engine datapaths, behind one dispatch.
//
// W8.1 and W8.2 built the control plane -- the microsequencer, the queue, the
// event scoreboard and the state controller -- and W8.6 correlated it against
// the functional simulator over sixty-four generated programs.  That campaign
// deliberately stubbed every engine, so what it proved is that the *sequence*
// is right.  This block is the other half: given the operation the sequencer
// issued and the operand views it resolved, does the arithmetic produce the
// same bytes the functional simulator produced?
//
// Four families are implemented, chosen because each is a place where being
// wrong changes a published result rather than a cycle count:
//
//   TENSOR.MATMUL      every contraction in both models
//   DMA.GATHER/SCATTER every weight and every KV byte that moves
//   VECTOR.ADD         the residual, at every layer boundary
//   VECTOR.CONVERT     unscaled one-input/one-output storage conversion
//   VECTOR.SCALE       bounded constant and elementwise BF16 scaling
//   VECTOR.HADAMARD    the qualified 128-point BF16 rotation
//   VECTOR.INDEX_SCORE bounded four-head learned-index scoring at scale 1.0
//   VECTOR.COMPRESS    the bounded COMPRESS_PROJECT sub-case
//   VECTOR.MHC         the bounded HYPER_CONNECT_POST sub-case
//   SELECTION.ARGMAX   the token itself
//
// Dispatch is fail-closed: a (family, subopcode) pair this block does not
// implement raises ERR_SHAPE and executes nothing, rather than falling through
// to whichever datapath happened to be wired up.
// ---------------------------------------------------------------------------
module ot_a3_engine_array (
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

    // Correlated descriptor admission.  These fields are resolved from the
    // issuing OPERATOR, TENSOR_VIEW and NUMERIC descriptors before dispatch;
    // datapath convenience fields above are checked against them rather than
    // being trusted as a substitute for the descriptors.
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

    // operand image ports -- one element per 32-bit word, one cycle latency
    output wire        m0_rd_en,
    output wire [31:0] m0_rd_addr,
    input  wire [31:0] m0_rd_data,
    output wire        m1_rd_en,
    output wire [31:0] m1_rd_addr,
    input  wire [31:0] m1_rd_data,
    output wire        m2_rd_en,
    output wire [31:0] m2_rd_addr,
    input  wire [31:0] m2_rd_data,
    output wire        m3_rd_en,
    output wire [31:0] m3_rd_addr,
    input  wire [31:0] m3_rd_data,

    output wire        out_we,
    output wire [31:0] out_addr,
    output wire [31:0] out_data,

    output wire        busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] result_count,
    output reg  [31:0] saturation_count,
    output reg  [31:0] work_count,
    output reg  [31:0] token,
    output reg  [31:0] tie_multiplicity
);
    // Package constants are re-declared as local parameters and never pulled
    // in with a wildcard import.  Under Icarus 11, a wildcard-imported
    // identifier that appears only inside a module-instance port-connection
    // expression is not resolved against the import: Icarus creates an
    // implicit one-bit net of that name instead, and the net then shadows the
    // constant for the whole module.  ``DMA_SCATTER`` read as z, every scatter
    // dispatched as unimplemented, and ``DMA_GATHER`` -- which never appeared
    // in a port connection -- kept working, so three of twenty-nine cases
    // failed and the rest passed.  Verilator resolved the constant correctly;
    // the two-simulator rule is the only reason the disagreement was visible.
    // The pinned Yosys 0.68 frontend rejects ``import`` outright, so the same
    // change is what makes this block synthesisable at all.
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE = ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_PRODUCT_RANGE = ot_a3_engine_pkg::ERR_PRODUCT_RANGE;
    localparam [7:0] ERR_ACCUMULATE_RANGE = ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_INDEX_RANGE = ot_a3_engine_pkg::ERR_INDEX_RANGE;
    localparam [7:0] ERR_SELECT_NONFINITE = ot_a3_engine_pkg::ERR_SELECT_NONFINITE;
    localparam [7:0] ERR_SCALE_RANGE = ot_a3_engine_pkg::ERR_SCALE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;
    localparam [7:0] FAMILY_DMA = ot_a3_engine_pkg::FAMILY_DMA;
    localparam [7:0] FAMILY_TENSOR = ot_a3_engine_pkg::FAMILY_TENSOR;
    localparam [7:0] FAMILY_VECTOR = ot_a3_engine_pkg::FAMILY_VECTOR;
    localparam [7:0] FAMILY_SELECTION = ot_a3_engine_pkg::FAMILY_SELECTION;
    localparam [7:0] DMA_GATHER = ot_a3_engine_pkg::DMA_GATHER;
    localparam [7:0] DMA_SCATTER = ot_a3_engine_pkg::DMA_SCATTER;
    localparam [7:0] TENSOR_MATMUL = ot_a3_engine_pkg::TENSOR_MATMUL;
    localparam [7:0] VECTOR_ADD = ot_a3_engine_pkg::VECTOR_ADD;
    localparam [7:0] VECTOR_CONVERT = ot_a3_engine_pkg::VECTOR_CONVERT;
    localparam [7:0] VECTOR_SCALE = ot_a3_engine_pkg::VECTOR_SCALE;
    localparam [7:0] VECTOR_COMPRESS = ot_a3_engine_pkg::VECTOR_COMPRESS;
    localparam [7:0] VECTOR_MHC = ot_a3_engine_pkg::VECTOR_MHC;
    localparam [7:0] VECTOR_HADAMARD = ot_a3_engine_pkg::VECTOR_HADAMARD;
    localparam [7:0] VECTOR_INDEX_SCORE =
        ot_a3_engine_pkg::VECTOR_INDEX_SCORE;

    localparam [7:0] FMT_BF16 = 8'h10;
    localparam [7:0] FMT_FP32 = 8'h12;
    localparam [7:0] FMT_FP8_E4M3FN = 8'h20;
    localparam [7:0] ROUND_NEAREST_EVEN = 8'd0;
    localparam [7:0] REDUCTION_SEQUENTIAL_ASCENDING = 8'd0;
    localparam [31:0] NO_ID = 32'hffff_ffff;

    // SHA-256 bindings of the qualified contract names.  The descriptor
    // adapter transports all eight words; accepting a familiar dtype tuple
    // with an unrelated numeric contract would otherwise recreate the same
    // fail-open hole at a different boundary.
    localparam [255:0] CONTRACT_IDENTITY_STORAGE =
        256'hfcce0ffdec1b5dcaeba8810794676dda167456ed9ddf550db02a2dc195d14a94;
    localparam [255:0] CONTRACT_BF16_TO_FP32 =
        256'hcd40eba301e7a13bba0d52a947fec7564130f0d511730707bec1cce325323c75;
    localparam [255:0] CONTRACT_FP32_TO_BF16 =
        256'h158efe6079f1decd2fa6be3c4ec14b93a64eb8198313e6005adfe3d7661f1107;
    localparam [255:0] CONTRACT_FP8_TO_BF16 =
        256'hb2c7323162059eafc71474d1814b37e2bb5fb5063e75b7f7236e79a00d8116d8;
    localparam [255:0] CONTRACT_BF16_SCALE =
        256'h53e7793e7377e53bba6af04bfabc087891c2b420f4c7281d54ca239eaa665f51;
    localparam [255:0] CONTRACT_BF16_MUL =
        256'he330ed15a75c287342bba73aea069f79357229bdbd5af4422e8f7144dc190509;
    localparam [255:0] CONTRACT_HADAMARD =
        256'hb678c78bea1ea6afb9081ceb646020175c0fa7bdcf7c18f5ca6a7f0e4c7c8d8f;
    localparam [255:0] CONTRACT_INDEX_SCORE =
        256'haec57536aad948c4312f15f779dec61b441d713e33a3ffee9091719318369d27;
    localparam [255:0] CONTRACT_COMPRESS_PROJECT =
        256'h0dd119f04b6a544c42f760e974a87748cf0ce8f762adfa3b879c9680fa04c652;
    localparam [255:0] CONTRACT_MHC_POST =
        256'habb4df2b8a31bcd33aa62e69c58254be8de1bb7cac8463d4adec85f1dc50fc5e;

    wire [255:0] cfg_contract_digest = {
        cfg_contract_0, cfg_contract_1, cfg_contract_2, cfg_contract_3,
        cfg_contract_4, cfg_contract_5, cfg_contract_6, cfg_contract_7
    };
    wire [7:0] desc_in0_dtype = cfg_input_dtypes[7:0];
    wire [7:0] desc_in1_dtype = cfg_input_dtypes[15:8];
    wire [7:0] desc_in2_dtype = cfg_input_dtypes[23:16];
    wire [7:0] desc_in3_dtype = cfg_input_dtypes[31:24];
    wire [7:0] desc_out0_dtype = cfg_output_dtypes[7:0];
    wire [7:0] desc_out1_dtype = cfg_output_dtypes[15:8];
    wire [3:0] desc_in0_rank = cfg_view_ranks[3:0];
    wire [3:0] desc_in1_rank = cfg_view_ranks[7:4];
    wire [3:0] desc_in2_rank = cfg_view_ranks[11:8];
    wire [3:0] desc_in3_rank = cfg_view_ranks[15:12];
    wire [3:0] desc_out0_rank = cfg_view_ranks[19:16];
    wire [3:0] desc_out1_rank = cfg_view_ranks[23:20];
    wire [7:0] profile_input_dtype = cfg_profile_dtypes[7:0];
    wire [7:0] profile_second_dtype = cfg_profile_dtypes[15:8];
    wire [7:0] profile_output_dtype = cfg_profile_dtypes[23:16];
    wire [7:0] profile_accumulator_dtype = cfg_profile_dtypes[31:24];

    function automatic shape_well_formed;
        input [3:0] rank;
        input [127:0] dims;
        integer axis;
        begin
            shape_well_formed = (rank != 0) && (rank <= 4);
            for (axis = 0; axis < 4; axis = axis + 1) begin
                if ((axis < rank) && (dims[axis*32 +: 32] == 0))
                    shape_well_formed = 1'b0;
                if ((axis >= rank) && (dims[axis*32 +: 32] != 0))
                    shape_well_formed = 1'b0;
            end
        end
    endfunction

    function automatic [63:0] shape_elements;
        input [3:0] rank;
        input [127:0] dims;
        integer axis;
        reg [63:0] product;
        begin
            product = 64'd1;
            if (!shape_well_formed(rank, dims))
                product = 0;
            else
                for (axis = 0; axis < 4; axis = axis + 1)
                    if (axis < rank)
                        product = product * dims[axis*32 +: 32];
            shape_elements = product;
        end
    endfunction

    function automatic [31:0] shape_last;
        input [3:0] rank;
        input [127:0] dims;
        begin
            case (rank)
                1: shape_last = dims[31:0];
                2: shape_last = dims[63:32];
                3: shape_last = dims[95:64];
                4: shape_last = dims[127:96];
                default: shape_last = 0;
            endcase
        end
    endfunction
    localparam [7:0] SELECTION_ARGMAX = ot_a3_engine_pkg::SELECTION_ARGMAX;

    wire dma_is_scatter = (cfg_sub == DMA_SCATTER);

    wire select_mac = (cfg_family == FAMILY_TENSOR) && (cfg_sub == TENSOR_MATMUL);
    wire select_sel = (cfg_family == FAMILY_SELECTION) &&
                      (cfg_sub == SELECTION_ARGMAX);
    wire select_dma = (cfg_family == FAMILY_DMA) &&
                      ((cfg_sub == DMA_GATHER) || dma_is_scatter);
    wire select_add = (cfg_family == FAMILY_VECTOR) && (cfg_sub == VECTOR_ADD);
    wire select_convert = (cfg_family == FAMILY_VECTOR) &&
                          (cfg_sub == VECTOR_CONVERT);
    wire select_scale = (cfg_family == FAMILY_VECTOR) &&
                        (cfg_sub == VECTOR_SCALE);
    wire select_compress = (cfg_family == FAMILY_VECTOR) &&
                           (cfg_sub == VECTOR_COMPRESS);
    wire select_mhc = (cfg_family == FAMILY_VECTOR) &&
                      (cfg_sub == VECTOR_MHC);
    wire select_hadamard = (cfg_family == FAMILY_VECTOR) &&
                           (cfg_sub == VECTOR_HADAMARD);
    wire select_index = (cfg_family == FAMILY_VECTOR) &&
                        (cfg_sub == VECTOR_INDEX_SCORE);
    wire implemented = select_mac | select_sel | select_dma | select_add |
                       select_convert | select_scale | select_compress |
                       select_mhc | select_hadamard | select_index;

    wire profile_rne = cfg_rounding_mode == ROUND_NEAREST_EVEN;
    wire profile_sequential =
        cfg_reduction_order == REDUCTION_SEQUENTIAL_ASCENDING;
    wire bounded_profile_controls =
        (profile_accumulator_dtype == FMT_FP32) &&
        !cfg_profile_saturate && (cfg_nan_policy == 0) &&
        (cfg_epsilon_bits == 0) && (cfg_profile_flags == 0);
    wire all_views_unscaled = cfg_view_scaled == 6'b0;

    wire convert_contract_supported =
        ((desc_in0_dtype == desc_out0_dtype) &&
         (cfg_contract_digest == CONTRACT_IDENTITY_STORAGE)) ||
        ((desc_in0_dtype == FMT_BF16) &&
         (desc_out0_dtype == FMT_FP32) &&
         (cfg_contract_digest == CONTRACT_BF16_TO_FP32)) ||
        ((desc_in0_dtype == FMT_FP32) &&
         (desc_out0_dtype == FMT_BF16) &&
         (cfg_contract_digest == CONTRACT_FP32_TO_BF16)) ||
        ((desc_in0_dtype == FMT_FP8_E4M3FN) &&
         (desc_out0_dtype == FMT_BF16) &&
         (cfg_contract_digest == CONTRACT_FP8_TO_BF16));
    wire convert_descriptor_supported =
        (cfg_input_valid == 4'b0001) &&
        (cfg_output_valid == 2'b01) &&
        all_views_unscaled && (cfg_aux_valid == 0) &&
        shape_well_formed(desc_in0_rank, cfg_input0_dims) &&
        (desc_out0_rank == desc_in0_rank) &&
        (cfg_output0_dims == cfg_input0_dims) &&
        (shape_elements(desc_in0_rank, cfg_input0_dims) == cfg_count) &&
        (cfg_count != 0) &&
        (cfg_dtype_a == desc_in0_dtype) &&
        (cfg_block_a[7:0] == desc_out0_dtype) &&
        cfg_profile_valid &&
        (profile_input_dtype == desc_in0_dtype) &&
        (profile_second_dtype == desc_in0_dtype) &&
        (profile_output_dtype == desc_out0_dtype) &&
        profile_rne && profile_sequential && bounded_profile_controls &&
        (cfg_profile_scale_bits == 0) && convert_contract_supported;

    wire scale_elementwise = cfg_aux0 == 32'd1;
    wire scale_contract_supported =
        ((!scale_elementwise &&
          (cfg_contract_digest == CONTRACT_BF16_SCALE)) ||
         (scale_elementwise &&
          (cfg_contract_digest == CONTRACT_BF16_MUL)));
    wire scale_descriptor_supported =
        (cfg_output_valid == 2'b01) &&
        (cfg_input_valid == (scale_elementwise ? 4'b0011 : 4'b0001)) &&
        (cfg_aux_valid == 4'b0001) &&
        ((cfg_aux0 == 0) || scale_elementwise) &&
        (cfg_aux1 == NO_ID) && (cfg_aux2 == NO_ID) && (cfg_aux3 == NO_ID) &&
        all_views_unscaled &&
        (desc_in0_dtype == FMT_BF16) &&
        (!scale_elementwise || (desc_in1_dtype == FMT_BF16)) &&
        (desc_out0_dtype == FMT_BF16) &&
        shape_well_formed(desc_in0_rank, cfg_input0_dims) &&
        (desc_out0_rank == desc_in0_rank) &&
        (cfg_output0_dims == cfg_input0_dims) &&
        (!scale_elementwise ||
         ((desc_in1_rank == desc_in0_rank) &&
          (cfg_input1_dims == cfg_input0_dims))) &&
        (shape_elements(desc_in0_rank, cfg_input0_dims) == cfg_count) &&
        (cfg_count != 0) && (cfg_count <= 512) &&
        (cfg_dtype_a == desc_in0_dtype) &&
        (!scale_elementwise || (cfg_dtype_b == desc_in1_dtype)) &&
        (cfg_block_a == cfg_aux0[15:0]) &&
        cfg_profile_valid &&
        (profile_input_dtype == FMT_BF16) &&
        (profile_second_dtype == FMT_BF16) &&
        (profile_output_dtype == FMT_BF16) &&
        profile_rne && profile_sequential && bounded_profile_controls &&
        (cfg_c_base == cfg_profile_scale_bits) && scale_contract_supported;

    wire hadamard_descriptor_supported =
        (cfg_input_valid == 4'b0001) &&
        (cfg_output_valid == 2'b01) && (cfg_aux_valid == 0) &&
        all_views_unscaled &&
        (desc_in0_dtype == FMT_BF16) &&
        (desc_out0_dtype == FMT_BF16) &&
        shape_well_formed(desc_in0_rank, cfg_input0_dims) &&
        (desc_out0_rank == desc_in0_rank) &&
        (cfg_output0_dims == cfg_input0_dims) &&
        (shape_last(desc_in0_rank, cfg_input0_dims) == 128) &&
        (shape_elements(desc_in0_rank, cfg_input0_dims) == cfg_count) &&
        (cfg_count >= 128) && (cfg_count <= 512) &&
        (cfg_rows == (cfg_count >> 7)) && (cfg_cols == 128) &&
        (cfg_dtype_a == desc_in0_dtype) && cfg_profile_valid &&
        (profile_input_dtype == FMT_BF16) &&
        (profile_second_dtype == FMT_BF16) &&
        (profile_output_dtype == FMT_BF16) &&
        profile_rne && profile_sequential && bounded_profile_controls &&
        (cfg_profile_scale_bits == 0) &&
        (cfg_contract_digest == CONTRACT_HADAMARD);

    wire index_descriptor_supported =
        (cfg_input_valid == 4'b0111) &&
        (cfg_output_valid == 2'b01) && (cfg_aux_valid == 0) &&
        all_views_unscaled &&
        (desc_in0_dtype == FMT_BF16) &&
        (desc_in1_dtype == FMT_BF16) &&
        (desc_in2_dtype == FMT_BF16) &&
        (desc_out0_dtype == FMT_BF16) &&
        (desc_in0_rank == 4) && (desc_in1_rank == 3) &&
        (desc_in2_rank == 3) && (desc_out0_rank == 3) &&
        shape_well_formed(desc_in0_rank, cfg_input0_dims) &&
        shape_well_formed(desc_in1_rank, cfg_input1_dims) &&
        shape_well_formed(desc_in2_rank, cfg_input2_dims) &&
        shape_well_formed(desc_out0_rank, cfg_output0_dims) &&
        (cfg_input0_dims[31:0] == 1) &&
        (cfg_input0_dims[31:0] == cfg_input1_dims[31:0]) &&
        (cfg_input0_dims[31:0] == cfg_input2_dims[31:0]) &&
        (cfg_input0_dims[31:0] == cfg_output0_dims[31:0]) &&
        (cfg_input0_dims[63:32] == cfg_input2_dims[63:32]) &&
        (cfg_input0_dims[63:32] == cfg_output0_dims[63:32]) &&
        (cfg_input0_dims[95:64] == 4) &&
        (cfg_input0_dims[95:64] == cfg_input2_dims[95:64]) &&
        (cfg_input0_dims[127:96] == cfg_input1_dims[95:64]) &&
        (cfg_input1_dims[63:32] == cfg_output0_dims[95:64]) &&
        (cfg_rows == cfg_input0_dims[63:32]) &&
        (cfg_cols == cfg_input1_dims[63:32]) &&
        (cfg_depth == cfg_input0_dims[127:96]) &&
        (cfg_slots == cfg_input0_dims[95:64]) &&
        (cfg_count == shape_elements(desc_out0_rank, cfg_output0_dims)) &&
        (cfg_dtype_a == desc_in0_dtype) &&
        (cfg_dtype_b == desc_in1_dtype) && cfg_profile_valid &&
        (profile_input_dtype == FMT_BF16) &&
        (profile_second_dtype == FMT_BF16) &&
        (profile_output_dtype == FMT_BF16) &&
        profile_rne && profile_sequential && bounded_profile_controls &&
        (cfg_profile_scale_bits == 32'h3f80_0000) &&
        (cfg_c_base == cfg_profile_scale_bits) &&
        (cfg_contract_digest == CONTRACT_INDEX_SCORE);

    wire compress_descriptor_supported =
        (cfg_input_valid == 4'b0111) &&
        (cfg_output_valid == 2'b01) &&
        (cfg_aux_valid == 4'b0001) && (cfg_aux0 == 0) &&
        (cfg_aux1 == NO_ID) && (cfg_aux2 == NO_ID) && (cfg_aux3 == NO_ID) &&
        all_views_unscaled &&
        (desc_in0_dtype == FMT_BF16) &&
        (desc_in1_dtype == FMT_BF16) &&
        (desc_in2_dtype == FMT_BF16) &&
        (desc_out0_dtype == FMT_FP32) &&
        (desc_in0_rank == 3) && (desc_in1_rank == 2) &&
        (desc_in2_rank == 2) && (desc_out0_rank == 4) &&
        shape_well_formed(desc_in0_rank, cfg_input0_dims) &&
        shape_well_formed(desc_in1_rank, cfg_input1_dims) &&
        shape_well_formed(desc_in2_rank, cfg_input2_dims) &&
        shape_well_formed(desc_out0_rank, cfg_output0_dims) &&
        (cfg_input0_dims[95:64] == cfg_input1_dims[63:32]) &&
        (cfg_input0_dims[95:64] == cfg_input2_dims[63:32]) &&
        (cfg_input1_dims[31:0] == cfg_input2_dims[31:0]) &&
        (cfg_output0_dims[31:0] == cfg_input0_dims[31:0]) &&
        (cfg_output0_dims[63:32] == cfg_input0_dims[63:32]) &&
        (cfg_output0_dims[95:64] == 2) &&
        (cfg_output0_dims[127:96] == cfg_input1_dims[31:0]) &&
        (cfg_rows == (cfg_input0_dims[31:0] * cfg_input0_dims[63:32])) &&
        (cfg_cols == cfg_input1_dims[31:0]) &&
        (cfg_depth == cfg_input0_dims[95:64]) &&
        (cfg_count == shape_elements(desc_out0_rank, cfg_output0_dims)) &&
        (cfg_block_a == cfg_aux0[15:0]) &&
        (cfg_dtype_a == desc_in0_dtype) &&
        (cfg_dtype_b == desc_in1_dtype) && cfg_profile_valid &&
        (profile_input_dtype == FMT_BF16) &&
        (profile_second_dtype == FMT_BF16) &&
        (profile_output_dtype == FMT_FP32) &&
        profile_rne && profile_sequential && bounded_profile_controls &&
        (cfg_profile_scale_bits == 0) &&
        (cfg_contract_digest == CONTRACT_COMPRESS_PROJECT);

    wire mhc_descriptor_supported =
        (cfg_input_valid == 4'b1111) &&
        (cfg_output_valid == 2'b01) &&
        (cfg_aux_valid == 4'b0101) &&
        (cfg_aux0 == 1) && (cfg_aux1 == NO_ID) &&
        (cfg_aux2 == 4) && (cfg_aux3 == NO_ID) &&
        all_views_unscaled &&
        (desc_in0_dtype == FMT_BF16) &&
        (desc_in1_dtype == FMT_BF16) &&
        (desc_in2_dtype == FMT_FP32) &&
        (desc_in3_dtype == FMT_FP32) &&
        (desc_out0_dtype == FMT_BF16) &&
        (desc_in0_rank == 3) && (desc_in1_rank == 4) &&
        (desc_in2_rank == 3) && (desc_in3_rank == 4) &&
        (desc_out0_rank == 4) &&
        shape_well_formed(desc_in0_rank, cfg_input0_dims) &&
        shape_well_formed(desc_in1_rank, cfg_input1_dims) &&
        shape_well_formed(desc_in2_rank, cfg_input2_dims) &&
        shape_well_formed(desc_in3_rank, cfg_input3_dims) &&
        shape_well_formed(desc_out0_rank, cfg_output0_dims) &&
        (cfg_input1_dims == cfg_output0_dims) &&
        (cfg_input1_dims[31:0] == cfg_input0_dims[31:0]) &&
        (cfg_input1_dims[63:32] == cfg_input0_dims[63:32]) &&
        (cfg_input1_dims[127:96] == cfg_input0_dims[95:64]) &&
        (cfg_input1_dims[95:64] == 4) &&
        (cfg_input2_dims[31:0] == cfg_input0_dims[31:0]) &&
        (cfg_input2_dims[63:32] == cfg_input0_dims[63:32]) &&
        (cfg_input2_dims[95:64] == 4) &&
        (cfg_input3_dims[31:0] == cfg_input0_dims[31:0]) &&
        (cfg_input3_dims[63:32] == cfg_input0_dims[63:32]) &&
        (cfg_input3_dims[95:64] == 4) &&
        (cfg_input3_dims[127:96] == 4) &&
        (cfg_rows == (cfg_input0_dims[31:0] * cfg_input0_dims[63:32])) &&
        (cfg_cols == cfg_input0_dims[95:64]) && (cfg_slots == 4) &&
        (cfg_count == shape_elements(desc_out0_rank, cfg_output0_dims)) &&
        (cfg_block_a == cfg_aux0[15:0]) &&
        (cfg_block_b == cfg_aux2[15:0]) &&
        (cfg_dtype_a == desc_in0_dtype) &&
        (cfg_dtype_b == desc_in1_dtype) && !cfg_profile_valid &&
        (cfg_profile_dtypes == 0) &&
        (cfg_rounding_mode == 0) && (cfg_reduction_order == 0) &&
        !cfg_profile_saturate && (cfg_nan_policy == 0) &&
        (cfg_profile_scale_bits == 0) && (cfg_epsilon_bits == 0) &&
        (cfg_profile_flags == 0) &&
        (cfg_contract_digest == CONTRACT_MHC_POST);

    wire descriptor_admitted = select_convert ? convert_descriptor_supported
                             : select_scale ? scale_descriptor_supported
                             : select_hadamard ? hadamard_descriptor_supported
                             : select_index ? index_descriptor_supported
                             : select_compress ? compress_descriptor_supported
                             : select_mhc ? mhc_descriptor_supported
                             : 1'b1;

    // -- TENSOR.MATMUL ---------------------------------------------------
    wire        lmac_a_en, lmac_b_en, mac_s_en, mac_t_en, lmac_we, lmac_busy, lmac_done;
    wire [31:0] lmac_a_addr, lmac_b_addr, mac_s_addr, mac_t_addr;
    wire [31:0] lmac_addr, lmac_data, lmac_out_count, lmac_sat, lmac_macs;
    wire [7:0]  lmac_error;

    //: TWO TENSOR LANES, selected per descriptor.
    //:
    //: ot_a3_mac_lane_pipe retires one multiply-accumulate per cycle where
    //: ot_a3_mac_lane retires one every five, and is proven to produce identical
    //: write streams and error codes (rtl/test/tb_mac_lane_pipe_equiv.sv). It
    //: implements BF16 x BF16 with no block scaling; anything else -- another dtype
    //: pair, or a descriptor declaring a scale object -- goes to the legacy lane.
    //:
    //: Routing on the descriptor rather than replacing the lane outright means no
    //: descriptor changes behaviour: one that the pipelined lane does not claim is
    //: executed by exactly the gates that executed it before.
    wire use_pipe_mac = select_mac
                     && (cfg_dtype_a == FMT_BF16) && (cfg_dtype_b == FMT_BF16)
                     && !cfg_scale_a && !cfg_scale_b;

    wire        pmac_a_en, pmac_b_en, pmac_we, pmac_busy, pmac_done;
    wire [31:0] pmac_a_addr, pmac_b_addr, pmac_addr, pmac_data;
    wire [31:0] pmac_out_count, pmac_sat, pmac_macs;
    wire [7:0]  pmac_error;

    //: The array's consumers below read mac_* and do not know which lane answered.
    wire        mac_a_en     = use_pipe_mac ? pmac_a_en     : lmac_a_en;
    wire        mac_b_en     = use_pipe_mac ? pmac_b_en     : lmac_b_en;
    wire [31:0] mac_a_addr   = use_pipe_mac ? pmac_a_addr   : lmac_a_addr;
    wire [31:0] mac_b_addr   = use_pipe_mac ? pmac_b_addr   : lmac_b_addr;
    wire        mac_we       = use_pipe_mac ? pmac_we       : lmac_we;
    wire [31:0] mac_addr     = use_pipe_mac ? pmac_addr     : lmac_addr;
    wire [31:0] mac_data     = use_pipe_mac ? pmac_data     : lmac_data;
    //: busy and done are ORed rather than muxed: whichever lane was started must be
    //: able to finish even if the configuration inputs have since changed.
    wire        mac_busy     = pmac_busy | lmac_busy;
    wire        mac_done     = pmac_done | lmac_done;
    wire [7:0]  mac_error    = pmac_done ? pmac_error     : lmac_error;
    wire [31:0] mac_out_count = pmac_done ? pmac_out_count : lmac_out_count;
    wire [31:0] mac_sat      = pmac_done ? pmac_sat       : lmac_sat;
    wire [31:0] mac_macs     = pmac_done ? pmac_macs      : lmac_macs;

    ot_a3_mac_lane mac (
        .clk(clk), .rst_n(rst_n),
        .start(start & select_mac & ~use_pipe_mac),
        .cfg_rows(cfg_rows), .cfg_cols(cfg_cols), .cfg_depth(cfg_depth),
        .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b),
        .cfg_a_base(cfg_a_base), .cfg_b_base(cfg_b_base),
        .cfg_scale_a(cfg_scale_a), .cfg_scale_b(cfg_scale_b),
        .cfg_block_a(cfg_block_a), .cfg_block_b(cfg_block_b),
        .cfg_block_rows_a(cfg_block_rows_a), .cfg_block_rows_b(cfg_block_rows_b),
        .cfg_scale_a_base(cfg_scale_a_base), .cfg_scale_b_base(cfg_scale_b_base),
        .cfg_out_base(cfg_out_base),
        .a_rd_en(lmac_a_en), .a_rd_addr(lmac_a_addr), .a_rd_data(m0_rd_data),
        .b_rd_en(lmac_b_en), .b_rd_addr(lmac_b_addr), .b_rd_data(m1_rd_data),
        .s_rd_en(mac_s_en), .s_rd_addr(mac_s_addr), .s_rd_data(m2_rd_data),
        .t_rd_en(mac_t_en), .t_rd_addr(mac_t_addr), .t_rd_data(m3_rd_data),
        .out_we(lmac_we), .out_addr(lmac_addr), .out_data(lmac_data),
        .busy(lmac_busy), .done(lmac_done), .error_code(lmac_error),
        .out_count(lmac_out_count), .saturation_count(lmac_sat),
        .mac_count(lmac_macs)
    );

    ot_a3_mac_lane_pipe #(.LANES_IF(8)) fastmac (
        .clk(clk), .rst_n(rst_n),
        .start(start & use_pipe_mac),
        .cfg_rows(cfg_rows), .cfg_cols(cfg_cols), .cfg_depth(cfg_depth),
        .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b),
        .cfg_a_base(cfg_a_base), .cfg_b_base(cfg_b_base),
        .cfg_out_base(cfg_out_base),
        .a_rd_en(pmac_a_en), .a_rd_addr(pmac_a_addr), .a_rd_data(m0_rd_data),
        .b_rd_en(pmac_b_en), .b_rd_addr(pmac_b_addr), .b_rd_data(m1_rd_data),
        .out_we(pmac_we), .out_addr(pmac_addr), .out_data(pmac_data),
        .busy(pmac_busy), .done(pmac_done), .error_code(pmac_error),
        .out_count(pmac_out_count), .saturation_count(pmac_sat),
        .mac_count(pmac_macs)
    );

    // -- SELECTION.ARGMAX ------------------------------------------------
    wire        sel_a_en, sel_we, sel_busy, sel_done;
    wire [31:0] sel_a_addr, sel_addr, sel_data, sel_token, sel_ties, sel_read;
    wire [7:0]  sel_error;

    ot_a3_selection_argmax selection (
        .clk(clk), .rst_n(rst_n),
        .start(start & select_sel),
        .cfg_count(cfg_count), .cfg_dtype(cfg_dtype_a),
        .cfg_in_base(cfg_a_base), .cfg_out_base(cfg_out_base),
        .a_rd_en(sel_a_en), .a_rd_addr(sel_a_addr), .a_rd_data(m0_rd_data),
        .out_we(sel_we), .out_addr(sel_addr), .out_data(sel_data),
        .busy(sel_busy), .done(sel_done), .error_code(sel_error),
        .token(sel_token), .tie_multiplicity(sel_ties),
        .elements_read(sel_read)
    );

    // -- DMA.GATHER and DMA.SCATTER --------------------------------------
    wire        dma_idx_en, dma_src_en, dma_we, dma_busy, dma_done;
    wire [31:0] dma_idx_addr, dma_src_addr, dma_addr, dma_data;
    wire [31:0] dma_moved, dma_checked;
    wire [7:0]  dma_error;

    ot_a3_dma_index_mover mover (
        .clk(clk), .rst_n(rst_n),
        .start(start & select_dma),
        .cfg_scatter(dma_is_scatter),
        .cfg_slots(cfg_slots), .cfg_trailing(cfg_trailing),
        .cfg_rows(cfg_extent),
        .cfg_index_base(cfg_a_base), .cfg_source_base(cfg_b_base),
        .cfg_prior_base(cfg_c_base), .cfg_out_base(cfg_out_base),
        .idx_rd_en(dma_idx_en), .idx_rd_addr(dma_idx_addr),
        .idx_rd_data(m0_rd_data),
        .src_rd_en(dma_src_en), .src_rd_addr(dma_src_addr),
        .src_rd_data(m1_rd_data),
        .out_we(dma_we), .out_addr(dma_addr), .out_data(dma_data),
        .busy(dma_busy), .done(dma_done), .error_code(dma_error),
        .moved_elements(dma_moved), .indices_checked(dma_checked)
    );

    // -- VECTOR.ADD ------------------------------------------------------
    wire        add_a_en, add_b_en, add_we, add_busy, add_done;
    wire [31:0] add_a_addr, add_b_addr, add_addr, add_data;
    wire [31:0] add_out_count, add_sat;
    wire [7:0]  add_error;

    ot_a3_vector_add adder (
        .clk(clk), .rst_n(rst_n),
        .start(start & select_add),
        .cfg_count(cfg_count),
        .cfg_left_base(cfg_a_base), .cfg_right_base(cfg_b_base),
        .cfg_out_base(cfg_out_base),
        .a_rd_en(add_a_en), .a_rd_addr(add_a_addr), .a_rd_data(m0_rd_data),
        .b_rd_en(add_b_en), .b_rd_addr(add_b_addr), .b_rd_data(m1_rd_data),
        .out_we(add_we), .out_addr(add_addr), .out_data(add_data),
        .busy(add_busy), .done(add_done), .error_code(add_error),
        .out_count(add_out_count), .saturation_count(add_sat)
    );

    // -- VECTOR.CONVERT --------------------------------------------------
    // cfg_block_a carries the destination dtype for this bounded form.
    wire        convert_a_en, convert_we, convert_busy, convert_done;
    wire [31:0] convert_a_addr, convert_addr, convert_data;
    wire [31:0] convert_out_count, convert_sat;
    wire [7:0]  convert_error;

    ot_a3_vector_convert converter (
        .clk(clk), .rst_n(rst_n),
        .start(start & select_convert & descriptor_admitted),
        .cfg_count(cfg_count),
        .cfg_input_dtype(cfg_dtype_a),
        .cfg_output_dtype(cfg_block_a[7:0]),
        .cfg_input_base(cfg_a_base), .cfg_output_base(cfg_out_base),
        .a_rd_en(convert_a_en), .a_rd_addr(convert_a_addr),
        .a_rd_data(m0_rd_data),
        .out_we(convert_we), .out_addr(convert_addr), .out_data(convert_data),
        .busy(convert_busy), .done(convert_done), .error_code(convert_error),
        .out_count(convert_out_count), .saturation_count(convert_sat)
    );

    // -- VECTOR.SCALE ----------------------------------------------------
    // cfg_block_a is aux0 and cfg_c_base carries the profile's scale_bits.
    wire        scale_a_en, scale_b_en, scale_we, scale_busy, scale_done;
    wire [31:0] scale_a_addr, scale_b_addr, scale_addr, scale_data;
    wire [31:0] scale_out_count, scale_sat;
    wire [7:0]  scale_error;

    ot_a3_vector_scale scaler (
        .clk(clk), .rst_n(rst_n),
        .start(start & select_scale & descriptor_admitted),
        .cfg_count(cfg_count),
        .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b),
        .cfg_aux0(cfg_block_a), .cfg_scale_bits(cfg_c_base),
        .cfg_a_base(cfg_a_base), .cfg_b_base(cfg_b_base),
        .cfg_out_base(cfg_out_base),
        .a_rd_en(scale_a_en), .a_rd_addr(scale_a_addr), .a_rd_data(m0_rd_data),
        .b_rd_en(scale_b_en), .b_rd_addr(scale_b_addr), .b_rd_data(m1_rd_data),
        .out_we(scale_we), .out_addr(scale_addr), .out_data(scale_data),
        .busy(scale_busy), .done(scale_done), .error_code(scale_error),
        .out_count(scale_out_count), .saturation_count(scale_sat)
    );

    // -- VECTOR.HADAMARD -------------------------------------------------
    wire        had_a_en, had_we, had_busy, had_done;
    wire [31:0] had_a_addr, had_addr, had_data, had_out_count;
    wire [7:0]  had_error;

    ot_a3_vector_hadamard hadamard (
        .clk(clk), .rst_n(rst_n),
        .start(start & select_hadamard & descriptor_admitted),
        .cfg_rows(cfg_rows), .cfg_cols(cfg_cols), .cfg_count(cfg_count),
        .cfg_dtype_a(cfg_dtype_a),
        .cfg_a_base(cfg_a_base), .cfg_out_base(cfg_out_base),
        .a_rd_en(had_a_en), .a_rd_addr(had_a_addr), .a_rd_data(m0_rd_data),
        .out_we(had_we), .out_addr(had_addr), .out_data(had_data),
        .busy(had_busy), .done(had_done), .error_code(had_error),
        .out_count(had_out_count)
    );

    // -- VECTOR.INDEX_SCORE ---------------------------------------------
    // cfg_slots is the head count, cfg_c_base the profile scale_bits and
    // cfg_scale_a_base the third operand's image base.
    wire        index_q_en, index_k_en, index_w_en;
    wire        index_we, index_busy, index_done;
    wire [31:0] index_q_addr, index_k_addr, index_w_addr;
    wire [31:0] index_addr, index_data, index_out_count, index_work, index_sat;
    wire [7:0]  index_error;

    ot_a3_vector_index_score index_scorer (
        .clk(clk), .rst_n(rst_n),
        .start(start & select_index & descriptor_admitted),
        .cfg_rows(cfg_rows), .cfg_cols(cfg_cols), .cfg_depth(cfg_depth),
        .cfg_count(cfg_count), .cfg_heads(cfg_slots),
        .cfg_scale_bits(cfg_c_base),
        .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b),
        .cfg_query_base(cfg_a_base), .cfg_key_base(cfg_b_base),
        .cfg_weight_base(cfg_scale_a_base), .cfg_out_base(cfg_out_base),
        .q_rd_en(index_q_en), .q_rd_addr(index_q_addr), .q_rd_data(m0_rd_data),
        .k_rd_en(index_k_en), .k_rd_addr(index_k_addr), .k_rd_data(m1_rd_data),
        .w_rd_en(index_w_en), .w_rd_addr(index_w_addr), .w_rd_data(m2_rd_data),
        .out_we(index_we), .out_addr(index_addr), .out_data(index_data),
        .busy(index_busy), .done(index_done), .error_code(index_error),
        .out_count(index_out_count), .work_count(index_work),
        .saturation_count(index_sat)
    );

    // -- VECTOR.COMPRESS / COMPRESS_PROJECT -----------------------------
    // cfg_block_a is aux0 and cfg_scale_a_base is the gate-weight base.
    wire        compress_h_en, compress_kv_en, compress_gate_en;
    wire        compress_we, compress_busy, compress_done;
    wire [31:0] compress_h_addr, compress_kv_addr, compress_gate_addr;
    wire [31:0] compress_addr, compress_data, compress_out_count, compress_work;
    wire [7:0]  compress_error;

    ot_a3_vector_compress_project compressor (
        .clk(clk), .rst_n(rst_n),
        .start(start & select_compress & descriptor_admitted),
        .cfg_rows(cfg_rows), .cfg_cols(cfg_cols), .cfg_depth(cfg_depth),
        .cfg_count(cfg_count), .cfg_aux0(cfg_block_a),
        .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b),
        .cfg_hidden_base(cfg_a_base), .cfg_kv_base(cfg_b_base),
        .cfg_gate_base(cfg_scale_a_base), .cfg_out_base(cfg_out_base),
        .h_rd_en(compress_h_en), .h_rd_addr(compress_h_addr),
        .h_rd_data(m0_rd_data),
        .kv_rd_en(compress_kv_en), .kv_rd_addr(compress_kv_addr),
        .kv_rd_data(m1_rd_data),
        .gate_rd_en(compress_gate_en), .gate_rd_addr(compress_gate_addr),
        .gate_rd_data(m2_rd_data),
        .out_we(compress_we), .out_addr(compress_addr), .out_data(compress_data),
        .busy(compress_busy), .done(compress_done),
        .error_code(compress_error), .out_count(compress_out_count),
        .work_count(compress_work)
    );

    // -- VECTOR.MHC / HYPER_CONNECT_POST --------------------------------
    // cfg_block_a is aux0, cfg_block_b is aux2/hc_mult, cfg_slots repeats the
    // operand multiplier, and m2/m3 carry post/combination respectively.
    wire        mhc_branch_en, mhc_residual_en, mhc_post_en, mhc_comb_en;
    wire        mhc_we, mhc_busy, mhc_done;
    wire [31:0] mhc_branch_addr, mhc_residual_addr, mhc_post_addr, mhc_comb_addr;
    wire [31:0] mhc_addr, mhc_data, mhc_out_count, mhc_work, mhc_sat;
    wire [7:0]  mhc_error;

    ot_a3_vector_mhc_post mhc_post (
        .clk(clk), .rst_n(rst_n),
        .start(start & select_mhc & descriptor_admitted),
        .cfg_sites(cfg_rows), .cfg_hidden(cfg_cols), .cfg_count(cfg_count),
        .cfg_multiplier(cfg_slots), .cfg_aux0(cfg_block_a),
        .cfg_aux2(cfg_block_b),
        .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b),
        .cfg_branch_base(cfg_a_base), .cfg_residual_base(cfg_b_base),
        .cfg_post_base(cfg_scale_a_base), .cfg_comb_base(cfg_scale_b_base),
        .cfg_out_base(cfg_out_base),
        .branch_rd_en(mhc_branch_en), .branch_rd_addr(mhc_branch_addr),
        .branch_rd_data(m0_rd_data),
        .residual_rd_en(mhc_residual_en), .residual_rd_addr(mhc_residual_addr),
        .residual_rd_data(m1_rd_data),
        .post_rd_en(mhc_post_en), .post_rd_addr(mhc_post_addr),
        .post_rd_data(m2_rd_data),
        .comb_rd_en(mhc_comb_en), .comb_rd_addr(mhc_comb_addr),
        .comb_rd_data(m3_rd_data),
        .out_we(mhc_we), .out_addr(mhc_addr), .out_data(mhc_data),
        .busy(mhc_busy), .done(mhc_done), .error_code(mhc_error),
        .out_count(mhc_out_count), .work_count(mhc_work),
        .saturation_count(mhc_sat)
    );

    // -- operand and result port arbitration -----------------------------
    assign m0_rd_en = mac_a_en | sel_a_en | dma_idx_en | add_a_en |
                      convert_a_en | scale_a_en | had_a_en | index_q_en |
                      compress_h_en | mhc_branch_en;
    assign m0_rd_addr = select_mac ? mac_a_addr
                      : select_sel ? sel_a_addr
                      : select_dma ? dma_idx_addr
                      : select_add ? add_a_addr
                      : select_convert ? convert_a_addr
                      : select_scale ? scale_a_addr
                      : select_hadamard ? had_a_addr
                      : select_index ? index_q_addr
                      : select_compress ? compress_h_addr
                      : mhc_branch_addr;
    assign m1_rd_en = mac_b_en | dma_src_en | add_b_en | scale_b_en |
                      index_k_en | compress_kv_en | mhc_residual_en;
    assign m1_rd_addr = select_mac ? mac_b_addr
                      : select_dma ? dma_src_addr
                      : select_add ? add_b_addr
                      : select_scale ? scale_b_addr
                      : select_index ? index_k_addr
                      : select_compress ? compress_kv_addr
                      : mhc_residual_addr;
    assign m2_rd_en = mac_s_en | index_w_en | compress_gate_en | mhc_post_en;
    assign m2_rd_addr = select_mac ? mac_s_addr
                      : select_index ? index_w_addr
                      : select_compress ? compress_gate_addr
                      : mhc_post_addr;
    assign m3_rd_en = mac_t_en | mhc_comb_en;
    assign m3_rd_addr = select_mac ? mac_t_addr : mhc_comb_addr;

    assign out_we = mac_we | sel_we | dma_we | add_we | convert_we |
                    scale_we | had_we | index_we | compress_we | mhc_we;
    assign out_addr = select_mac ? mac_addr
                    : select_sel ? sel_addr
                    : select_dma ? dma_addr
                    : select_add ? add_addr
                    : select_convert ? convert_addr
                    : select_scale ? scale_addr
                    : select_hadamard ? had_addr
                    : select_index ? index_addr
                    : select_compress ? compress_addr
                    : mhc_addr;
    assign out_data = select_mac ? mac_data
                    : select_sel ? sel_data
                    : select_dma ? dma_data
                    : select_add ? add_data
                    : select_convert ? convert_data
                    : select_scale ? scale_data
                    : select_hadamard ? had_data
                    : select_index ? index_data
                    : select_compress ? compress_data
                    : mhc_data;
    assign busy = mac_busy | sel_busy | dma_busy | add_busy | convert_busy |
                  scale_busy | had_busy | index_busy | compress_busy | mhc_busy;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            done <= 1'b0;
            error_code <= ERR_NONE;
            result_count <= 32'b0;
            saturation_count <= 32'b0;
            work_count <= 32'b0;
            token <= 32'b0;
            tie_multiplicity <= 32'b0;
        end else begin
            done <= 1'b0;
            if (start && (!implemented || !descriptor_admitted)) begin
                // Fail closed on an unimplemented operation or on descriptor
                // metadata that does not prove the selected bounded profile.
                error_code <= ERR_SHAPE;
                result_count <= 32'b0;
                saturation_count <= 32'b0;
                work_count <= 32'b0;
                token <= 32'b0;
                tie_multiplicity <= 32'b0;
                done <= 1'b1;
            end else if (mac_done) begin
                error_code <= mac_error;
                result_count <= mac_out_count;
                saturation_count <= mac_sat;
                work_count <= mac_macs;
                token <= 32'b0;
                tie_multiplicity <= 32'b0;
                done <= 1'b1;
            end else if (sel_done) begin
                error_code <= sel_error;
                result_count <= (sel_error == ERR_NONE) ? 32'd1 : 32'd0;
                saturation_count <= 32'b0;
                work_count <= sel_read;
                token <= sel_token;
                tie_multiplicity <= sel_ties;
                done <= 1'b1;
            end else if (dma_done) begin
                error_code <= dma_error;
                result_count <= dma_moved;
                saturation_count <= 32'b0;
                work_count <= dma_checked;
                token <= 32'b0;
                tie_multiplicity <= 32'b0;
                done <= 1'b1;
            end else if (add_done) begin
                error_code <= add_error;
                result_count <= add_out_count;
                saturation_count <= add_sat;
                work_count <= add_out_count;
                token <= 32'b0;
                tie_multiplicity <= 32'b0;
                done <= 1'b1;
            end else if (convert_done) begin
                error_code <= convert_error;
                result_count <= convert_out_count;
                saturation_count <= convert_sat;
                work_count <= (convert_error == ERR_NONE)
                            ? convert_out_count : 32'b0;
                token <= 32'b0;
                tie_multiplicity <= 32'b0;
                done <= 1'b1;
            end else if (scale_done) begin
                error_code <= scale_error;
                result_count <= scale_out_count;
                saturation_count <= scale_sat;
                work_count <= (scale_error == ERR_NONE)
                            ? scale_out_count : 32'b0;
                token <= 32'b0;
                tie_multiplicity <= 32'b0;
                done <= 1'b1;
            end else if (had_done) begin
                error_code <= had_error;
                result_count <= had_out_count;
                saturation_count <= 32'b0;
                work_count <= (had_error == ERR_NONE)
                            ? had_out_count : 32'b0;
                token <= 32'b0;
                tie_multiplicity <= 32'b0;
                done <= 1'b1;
            end else if (index_done) begin
                error_code <= index_error;
                result_count <= index_out_count;
                saturation_count <= index_sat;
                work_count <= (index_error == ERR_NONE)
                            ? index_work : 32'b0;
                token <= 32'b0;
                tie_multiplicity <= 32'b0;
                done <= 1'b1;
            end else if (compress_done) begin
                error_code <= compress_error;
                result_count <= compress_out_count;
                saturation_count <= 32'b0;
                work_count <= (compress_error == ERR_NONE)
                            ? compress_work : 32'b0;
                token <= 32'b0;
                tie_multiplicity <= 32'b0;
                done <= 1'b1;
            end else if (mhc_done) begin
                error_code <= mhc_error;
                result_count <= mhc_out_count;
                saturation_count <= mhc_sat;
                work_count <= (mhc_error == ERR_NONE) ? mhc_work : 32'b0;
                token <= 32'b0;
                tie_multiplicity <= 32'b0;
                done <= 1'b1;
            end
        end
    end
endmodule
