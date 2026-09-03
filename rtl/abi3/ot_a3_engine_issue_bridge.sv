`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Small ABI 3.0 sequencer-to-engine bridge.
//
// This is deliberately a bounded production profile, not a claim that every
// shipped operator has an RTL datapath.  It admits the exact dense one-index
// DMA.GATHER, BF16 TENSOR.EMBED_LOOKUP, Qwen BF16 VECTOR.RMS_NORM and the
// descriptor-driven layer-zero query/key/value TENSOR.MATMUL family, and
// DeepSeek stride-zero DMA.TRANSFER forms at the head of the shipped decode
// programs.  EMBED_LOOKUP and TRANSFER are row movements and lower internally
// to the existing index mover; RMS_NORM uses the exact buffered arithmetic
// slice and MATMUL reuses the qualified ABI 3.0 MAC lane.  The sequencer
// continues to observe each original opcode and
// descriptor.  Completion is returned only after the datapath finishes.
// Every other opcode returns a precise CAPABILITY trap.  Malformed metadata
// returns a DESCRIPTOR trap, and a datapath failure returns an ENGINE trap.
//
// The descriptor port is independent of the sequencer's descriptor port.  A
// real descriptor store may arbitrate those reads; the verification top uses
// two registered read ports over one immutable image.  Operand addresses are
// compact verification-bank addresses.  Geometry, dtype, arity, permissions,
// resolved extents and the exact numeric-contract digest all come from the
// ABI descriptors and the sequencer's resolved-view stream.
// ---------------------------------------------------------------------------
module ot_a3_engine_issue_bridge (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          clear,

    // Sequencer completion interface.
    input  wire          issue_valid,
    output wire          issue_ready,
    output wire          issue_fault,
    output wire [15:0]   issue_trap_class,
    input  wire [7:0]    issue_family,
    input  wire [7:0]    issue_sub,
    input  wire [31:0]   issue_descriptor_id,
    input  wire [31:0]   issue_index,

    // Resolved operand observation, emitted before issue.
    input  wire          view_valid,
    input  wire [31:0]   view_descriptor_id,
    input  wire [2:0]    view_slot,
    input  wire [31:0]   view_extent,
    input  wire [7:0]    view_extent_axis,
    input  wire [63:0]   view_element_offset,
    input  wire [7:0]    view_rank,

    // Immutable descriptor-store read port, one-cycle response.
    output reg           desc_req,
    output reg  [31:0]   desc_id,
    input  wire          desc_valid,
    input  wire          desc_fault,
    input  wire [1535:0] desc_data,

    // Per-transaction compact verification-bank placement.  The first
    // supported operation uses one index word.  Gathers advance through the
    // generated-row source region by the stated stride; embeddings use the
    // separately packed checkpoint-row region.  Mixed-width results advance
    // through one contiguous output cursor.
    input  wire [31:0]   cfg_index_base,
    input  wire [31:0]   cfg_source_base,
    input  wire [31:0]   cfg_source_launch_stride,
    input  wire [31:0]   cfg_embedding_source_base,
    input  wire [31:0]   cfg_rms_input_base,
    input  wire [31:0]   cfg_rms_weight_base,
    input  wire [31:0]   cfg_transfer_index_base,
    input  wire [31:0]   cfg_transfer_source_base,
    input  wire [31:0]   cfg_matmul_input_base,
    input  wire [31:0]   cfg_matmul_weight_object_0,
    input  wire [31:0]   cfg_matmul_weight_base_0,
    input  wire [31:0]   cfg_matmul_weight_object_1,
    input  wire [31:0]   cfg_matmul_weight_base_1,
    input  wire [31:0]   cfg_matmul_weight_object_2,
    input  wire [31:0]   cfg_matmul_weight_base_2,
    input  wire [31:0]   cfg_output_base,

    // Operand/result ports of the integrated engine array.
    output wire          m0_rd_en,
    output wire [31:0]   m0_rd_addr,
    input  wire [31:0]   m0_rd_data,
    output wire          m1_rd_en,
    output wire [31:0]   m1_rd_addr,
    input  wire [31:0]   m1_rd_data,
    output wire          m2_rd_en,
    output wire [31:0]   m2_rd_addr,
    input  wire [31:0]   m2_rd_data,
    output wire          m3_rd_en,
    output wire [31:0]   m3_rd_addr,
    input  wire [31:0]   m3_rd_data,
    output wire          out_we,
    output wire [31:0]   out_addr,
    output wire [31:0]   out_data,
    output wire          m0_reads_result,
    output wire          m1_reads_result,
    output wire          m1_reads_matmul_weight,

    // Non-control observation for the focused checker.
    output wire          engine_busy,
    output wire [7:0]    engine_error_code,
    output wire [31:0]   engine_result_count,
    output wire [31:0]   engine_work_count,
    output reg  [31:0]   real_launch_count,
    output reg  [31:0]   dma_gather_launch_count,
    output reg  [31:0]   embedding_launch_count,
    output reg  [31:0]   rms_norm_launch_count,
    output reg  [31:0]   dma_transfer_launch_count,
    output reg  [31:0]   matmul_launch_count,
    output reg  [31:0]   capability_fault_count,
    output reg  [31:0]   descriptor_fault_count,
    output reg  [31:0]   engine_fault_count,
    output reg  [31:0]   last_response_index,
    output reg  [7:0]    last_response_family,
    output reg  [7:0]    last_response_sub,
    output reg  [31:0]   last_response_descriptor_id
);
    localparam [31:0] NO_ID = 32'hffff_ffff;
    localparam [31:0] DESC_MAGIC = 32'h4433_4154;
    localparam [7:0] TYPE_MAJOR = 8'd1;
    localparam [7:0] TYPE_MINOR = 8'd0;
    localparam [15:0] DESC_TENSOR_VIEW = 16'h0002;
    localparam [15:0] DESC_NUMERIC = 16'h0003;
    localparam [15:0] DESC_OPERATOR = 16'h000a;
    localparam [15:0] TRAP_NONE = 16'd0;
    localparam [15:0] TRAP_DESCRIPTOR = 16'd3;
    localparam [15:0] TRAP_CAPABILITY = 16'd4;
    localparam [15:0] TRAP_ENGINE = 16'd8;

    localparam [7:0] FAMILY_DMA = 8'h10;
    localparam [7:0] FAMILY_TENSOR = 8'h20;
    localparam [7:0] FAMILY_VECTOR = 8'h30;
    localparam [7:0] DMA_TRANSFER = 8'h00;
    localparam [7:0] DMA_GATHER = 8'h02;
    localparam [7:0] TENSOR_EMBED_LOOKUP = 8'h03;
    localparam [7:0] TENSOR_MATMUL = 8'h00;
    localparam [7:0] VECTOR_RMS_NORM = 8'h00;
    localparam [7:0] FMT_U32 = 8'h04;
    localparam [7:0] FMT_I32 = 8'h05;
    localparam [7:0] FMT_BF16 = 8'h10;
    localparam [7:0] FMT_FP32 = 8'h12;
    localparam [7:0] ERR_NONE = 8'd0;

    // The raw little-endian 256-bit value held in NUMERIC payload bytes
    // 32..63 for SHA-256("exact_index_select_v1").  Comparing the descriptor
    // bytes avoids silently accepting another contract with the same dtypes.
    localparam [255:0] CONTRACT_EXACT_INDEX_SELECT_RAW =
        256'heeda7776a6f13afec895e72e1caa26c9dbf71599e6a35ecc51380dc89741a212;
    localparam [255:0] CONTRACT_QWEN_EMBED_RAW =
        256'hccfb3965ab85c67667ddda70e90d7dafe030d6ce65f4179ee161b1e0182fead1;
    localparam [255:0] CONTRACT_DEEPSEEK_EMBED_RAW =
        256'hd380012f2a885dbd0aebdd47859b1407945d8d1f7f5a091fc23201aa20e762ca;
    localparam [255:0] CONTRACT_QWEN_RMS_NORM_RAW =
        256'hda3fc0b8b5271a03bfb1f0c1e6d2be46af1896d484db57fd6dc3d4c46bf89e99;
    localparam [255:0] CONTRACT_DEEPSEEK_TRANSFER_RAW =
        256'h94180f7a2a2d20609236e96941dde296643a19e8e71ff1ab239c3ac09ae5e14a;
    localparam [255:0] CONTRACT_QWEN_MATMUL_RAW =
        256'ha15a76a03cd9c4212365014f8ebb77b73f61872818463b77d5d93f776adc5075;
    localparam [31:0] QWEN_VOCABULARY = 32'd151936;
    localparam [31:0] DEEPSEEK_VOCABULARY = 32'd129280;
    localparam [31:0] EMBEDDING_WIDTH = 32'd4096;
    localparam [31:0] RMS_EPSILON = 32'h3586_37bd;
    localparam [31:0] TRANSFER_COPIES = 32'd4;

    localparam [3:0] S_IDLE        = 4'd0;
    localparam [3:0] S_OP_WAIT     = 4'd1;
    localparam [3:0] S_INDEX_WAIT  = 4'd2;
    localparam [3:0] S_SOURCE_WAIT = 4'd3;
    localparam [3:0] S_OUTPUT_WAIT = 4'd4;
    localparam [3:0] S_NUM_WAIT    = 4'd5;
    localparam [3:0] S_START       = 4'd6;
    localparam [3:0] S_ENGINE_WAIT = 4'd7;
    localparam [3:0] S_RESPONSE    = 4'd8;
    localparam [3:0] S_RMS_INPUT_WAIT = 4'd9;

    reg [3:0] state;
    reg       response_fault;
    reg [15:0] response_trap;
    reg       engine_start;

    reg [7:0]  issue_family_q;
    reg [7:0]  issue_sub_q;
    reg [31:0] issue_descriptor_q;
    reg [31:0] issue_index_q;
    reg        embedding_q;
    reg        rms_norm_q;
    reg        dma_transfer_q;
    reg        matmul_q;

    reg [5:0]  captured_valid;
    reg [31:0] captured_id [0:5];
    reg [31:0] captured_extent [0:5];
    reg [7:0]  captured_axis [0:5];
    reg [63:0] captured_offset [0:5];
    reg [7:0]  captured_rank [0:5];

    reg [31:0] op_input0;
    reg [31:0] op_input1;
    reg [31:0] op_output0;
    reg [31:0] op_numeric;
    reg [31:0] index_raw_dim0;
    reg [31:0] source_rows;
    reg [31:0] source_trailing;
    reg [7:0]  source_dtype;
    reg [31:0] matmul_weight_base_q;
    reg [31:0] numeric_profile_dtypes;
    reg [31:0] result_word_cursor;

    function automatic descriptor_header_ok;
        input [1535:0] data;
        input fault;
        input [15:0] expected_type;
        input [31:0] expected_total;
        input [31:0] expected_payload;
        begin
            descriptor_header_ok = !fault &&
                (data[31:0] == DESC_MAGIC) &&
                (data[47:32] == expected_type) &&
                (data[55:48] == TYPE_MAJOR) &&
                (data[63:56] == TYPE_MINOR) &&
                (data[95:64] == expected_total) &&
                (data[351:320] == 32'd64) &&
                (data[383:352] == expected_payload);
        end
    endfunction

    wire response_fire = (state == S_RESPONSE) && issue_valid;
    assign issue_ready = (state == S_RESPONSE);
    assign issue_fault = response_fault;
    assign issue_trap_class = response_trap;

    // Descriptor fields shared by the three view checks.
    wire [7:0] desc_view_dtype = desc_data[519:512];
    wire [7:0] desc_view_rank = desc_data[527:520];
    wire [7:0] desc_view_layout = desc_data[535:528];
    wire [7:0] desc_view_terms = desc_data[543:536];
    wire [31:0] desc_view_scale_object = desc_data[575:544];
    wire [31:0] desc_view_scale_block = desc_data[607:576];
    wire [63:0] desc_view_offset = desc_data[703:640];
    wire [31:0] desc_view_dim0 = desc_data[735:704];
    wire [31:0] desc_view_dim1 = desc_data[767:736];
    wire [31:0] desc_view_dim2 = desc_data[799:768];
    wire [31:0] desc_view_dim3 = desc_data[831:800];
    wire [31:0] desc_view_dim4 = desc_data[863:832];
    wire [31:0] desc_view_dim5 = desc_data[895:864];
    wire [31:0] desc_view_stride0 = desc_data[927:896];
    wire [31:0] desc_view_stride1 = desc_data[959:928];
    wire [31:0] desc_view_stride2 = desc_data[991:960];
    wire [31:0] desc_view_stride3 = desc_data[1023:992];
    wire [31:0] desc_view_stride4 = desc_data[1055:1024];
    wire [31:0] desc_view_stride5 = desc_data[1087:1056];
    wire [31:0] desc_permissions = desc_data[287:256];
    wire [31:0] desc_primary_object = desc_data[159:128];

    wire input_view_common_ok = descriptor_header_ok(
        desc_data, desc_fault, DESC_TENSOR_VIEW, 32'd192, 32'd128
    ) &&
        (desc_view_layout == 0) &&
        (desc_view_scale_object == NO_ID) &&
        (desc_view_scale_block == 0) &&
        (desc_primary_object != NO_ID) &&
        ((desc_permissions & 32'd1) != 0);
    wire dense_row_source_ok = !rms_norm_q && !dma_transfer_q && !matmul_q &&
        (desc_view_dtype == (embedding_q ? FMT_BF16 : FMT_FP32)) &&
        (desc_view_rank == 2) && (desc_view_terms == 0) &&
        (desc_view_dim0 != 0) && (desc_view_dim1 != 0) &&
        (desc_view_dim2 == 0) && (desc_view_dim3 == 0) &&
        (desc_view_dim4 == 0) && (desc_view_dim5 == 0) &&
        (desc_view_stride0 == desc_view_dim1) &&
        (desc_view_stride1 == 1) && (desc_view_stride2 == 0) &&
        (desc_view_stride3 == 0) && (desc_view_stride4 == 0) &&
        (desc_view_stride5 == 0) &&
        (captured_rank[1] == 2) && (captured_axis[1] == 0) &&
        (captured_extent[1] == desc_view_dim0) &&
        (captured_offset[1] == desc_view_offset) &&
        (!embedding_q || ((desc_view_dim1 == EMBEDDING_WIDTH) &&
         ((desc_view_dim0 == QWEN_VOCABULARY) ||
          (desc_view_dim0 == DEEPSEEK_VOCABULARY))));
    wire rms_weight_source_ok = rms_norm_q &&
        (desc_view_dtype == FMT_BF16) && (desc_view_rank == 1) &&
        (desc_view_terms <= 4) &&
        (desc_view_dim0 == EMBEDDING_WIDTH) &&
        (desc_view_dim1 == 0) && (desc_view_dim2 == 0) &&
        (desc_view_dim3 == 0) && (desc_view_dim4 == 0) &&
        (desc_view_dim5 == 0) && (desc_view_stride0 == 1) &&
        (desc_view_stride1 == 0) && (desc_view_stride2 == 0) &&
        (desc_view_stride3 == 0) && (desc_view_stride4 == 0) &&
        (desc_view_stride5 == 0) &&
        (captured_rank[1] == 1) && (captured_axis[1] == 0) &&
        (captured_extent[1] == EMBEDDING_WIDTH) &&
        (captured_offset[1] == desc_view_offset);
    wire matmul_weight_source_ok = matmul_q &&
        (desc_view_dtype == FMT_BF16) && (desc_view_rank == 2) &&
        (desc_view_terms <= 4) &&
        (desc_view_dim0 != 0) && (desc_view_dim0 <= EMBEDDING_WIDTH) &&
        (desc_view_dim1 == EMBEDDING_WIDTH) &&
        (desc_view_dim2 == 0) && (desc_view_dim3 == 0) &&
        (desc_view_dim4 == 0) && (desc_view_dim5 == 0) &&
        (desc_view_stride0 == EMBEDDING_WIDTH) &&
        (desc_view_stride1 == 1) && (desc_view_stride2 == 0) &&
        (desc_view_stride3 == 0) && (desc_view_stride4 == 0) &&
        (desc_view_stride5 == 0) &&
        (captured_rank[1] == 2) && (captured_axis[1] == 0) &&
        (captured_extent[1] == desc_view_dim0) &&
        (captured_offset[1] == desc_view_offset);
    wire matmul_weight_object_mapped =
        (desc_primary_object == cfg_matmul_weight_object_0) ||
        (desc_primary_object == cfg_matmul_weight_object_1) ||
        (desc_primary_object == cfg_matmul_weight_object_2);
    wire [31:0] mapped_matmul_weight_base =
        (desc_primary_object == cfg_matmul_weight_object_0)
        ? cfg_matmul_weight_base_0
        : (desc_primary_object == cfg_matmul_weight_object_1)
        ? cfg_matmul_weight_base_1
        : cfg_matmul_weight_base_2;
    wire transfer_source_ok = dma_transfer_q &&
        (desc_view_dtype == FMT_BF16) && (desc_view_rank == 3) &&
        (desc_view_terms <= 4) && (desc_view_dim0 != 0) &&
        (desc_view_dim1 == TRANSFER_COPIES) &&
        (desc_view_dim2 == EMBEDDING_WIDTH) &&
        (desc_view_dim3 == 0) && (desc_view_dim4 == 0) &&
        (desc_view_dim5 == 0) &&
        (desc_view_stride0 == EMBEDDING_WIDTH) &&
        (desc_view_stride1 == 0) && (desc_view_stride2 == 1) &&
        (desc_view_stride3 == 0) && (desc_view_stride4 == 0) &&
        (desc_view_stride5 == 0) &&
        (captured_rank[0] == 3) && (captured_axis[0] == 0) &&
        (captured_extent[0] == 1) &&
        (captured_offset[0] == desc_view_offset);

    wire output_view_common_ok = descriptor_header_ok(
        desc_data, desc_fault, DESC_TENSOR_VIEW, 32'd192, 32'd128
    ) &&
        (desc_view_dtype == source_dtype) &&
        (desc_view_layout == 0) && (desc_view_terms <= 4) &&
        (desc_view_scale_object == NO_ID) &&
        (desc_view_scale_block == 0) &&
        (desc_primary_object != NO_ID) &&
        ((desc_permissions & 32'd2) != 0);
    wire dense_row_output_ok = !dma_transfer_q && !matmul_q &&
        (desc_view_rank == 2) && (desc_view_dim0 == index_raw_dim0) &&
        (desc_view_dim1 == source_trailing) &&
        (desc_view_dim2 == 0) && (desc_view_dim3 == 0) &&
        (desc_view_dim4 == 0) && (desc_view_dim5 == 0) &&
        (desc_view_stride0 == source_trailing) &&
        (desc_view_stride1 == 1) && (desc_view_stride2 == 0) &&
        (desc_view_stride3 == 0) && (desc_view_stride4 == 0) &&
        (desc_view_stride5 == 0) &&
        (captured_rank[4] == 2) && (captured_axis[4] == 0) &&
        (captured_extent[4] == captured_extent[0]);
    wire matmul_output_ok = matmul_q &&
        (desc_view_rank == 2) && (desc_view_dim0 == index_raw_dim0) &&
        (desc_view_dim1 == source_rows) &&
        (desc_view_dim2 == 0) && (desc_view_dim3 == 0) &&
        (desc_view_dim4 == 0) && (desc_view_dim5 == 0) &&
        (desc_view_stride0 == source_rows) &&
        (desc_view_stride1 == 1) && (desc_view_stride2 == 0) &&
        (desc_view_stride3 == 0) && (desc_view_stride4 == 0) &&
        (desc_view_stride5 == 0) &&
        (captured_rank[4] == 2) && (captured_axis[4] == 0) &&
        (captured_extent[4] == captured_extent[0]);
    wire transfer_output_ok = dma_transfer_q &&
        (desc_view_rank == 3) && (desc_view_dim0 == index_raw_dim0) &&
        (desc_view_dim1 == TRANSFER_COPIES) &&
        (desc_view_dim2 == EMBEDDING_WIDTH) &&
        (desc_view_dim3 == 0) && (desc_view_dim4 == 0) &&
        (desc_view_dim5 == 0) &&
        (desc_view_stride0 == TRANSFER_COPIES * EMBEDDING_WIDTH) &&
        (desc_view_stride1 == EMBEDDING_WIDTH) &&
        (desc_view_stride2 == 1) && (desc_view_stride3 == 0) &&
        (desc_view_stride4 == 0) && (desc_view_stride5 == 0) &&
        (captured_rank[4] == 3) && (captured_axis[4] == 0) &&
        (captured_extent[4] == captured_extent[0]);

    wire numeric_common_ok = descriptor_header_ok(
        desc_data, desc_fault, DESC_NUMERIC, 32'd128, 32'd64
    ) &&
        (desc_data[535:528] == FMT_FP32) &&
        (desc_data[543:536] == source_dtype) &&
        (desc_data[551:544] == 0) &&
        (desc_data[567:560] == 0) &&
        (desc_data[575:568] == 0) &&
        (desc_data[639:608] == 0) &&
        (desc_data[671:640] == 0) &&
        (desc_data[703:672] == 0) &&
        (desc_data[767:704] == 0);
    wire gather_numeric_ok = !embedding_q && !rms_norm_q &&
        !dma_transfer_q &&
        ((desc_data[519:512] == FMT_U32) ||
         (desc_data[519:512] == FMT_I32)) &&
        (desc_data[527:520] == source_dtype) &&
        (desc_data[559:552] == 0) &&
        (desc_data[607:576] == 0) &&
        (desc_data[1023:768] == CONTRACT_EXACT_INDEX_SELECT_RAW);
    wire embedding_numeric_ok = embedding_q &&
        (desc_data[519:512] == FMT_U32) &&
        (desc_data[527:520] == source_dtype) &&
        (desc_data[559:552] == 0) &&
        (desc_data[607:576] == 0) &&
        (((source_rows == QWEN_VOCABULARY) &&
          (desc_data[1023:768] == CONTRACT_QWEN_EMBED_RAW)) ||
         ((source_rows == DEEPSEEK_VOCABULARY) &&
          (desc_data[1023:768] == CONTRACT_DEEPSEEK_EMBED_RAW)));
    wire rms_numeric_ok = rms_norm_q &&
        (desc_data[519:512] == FMT_BF16) &&
        (desc_data[527:520] == FMT_BF16) &&
        (desc_data[559:552] == 1) &&
        (desc_data[607:576] == RMS_EPSILON) &&
        (desc_data[1023:768] == CONTRACT_QWEN_RMS_NORM_RAW);
    wire transfer_numeric_ok = dma_transfer_q &&
        (desc_data[519:512] == FMT_BF16) &&
        (desc_data[527:520] == FMT_BF16) &&
        (desc_data[559:552] == 0) &&
        (desc_data[607:576] == 0) &&
        (desc_data[1023:768] == CONTRACT_DEEPSEEK_TRANSFER_RAW);
    wire matmul_numeric_ok = matmul_q &&
        (desc_data[519:512] == FMT_BF16) &&
        (desc_data[527:520] == FMT_BF16) &&
        (desc_data[559:552] == 2) &&
        (desc_data[607:576] == 0) &&
        (desc_data[1023:768] == CONTRACT_QWEN_MATMUL_RAW);

    integer slot;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            response_fault <= 1'b0;
            response_trap <= TRAP_NONE;
            engine_start <= 1'b0;
            desc_req <= 1'b0;
            desc_id <= NO_ID;
            issue_family_q <= 8'd0;
            issue_sub_q <= 8'd0;
            issue_descriptor_q <= NO_ID;
            issue_index_q <= NO_ID;
            embedding_q <= 1'b0;
            rms_norm_q <= 1'b0;
            dma_transfer_q <= 1'b0;
            matmul_q <= 1'b0;
            captured_valid <= 6'd0;
            op_input0 <= NO_ID;
            op_input1 <= NO_ID;
            op_output0 <= NO_ID;
            op_numeric <= NO_ID;
            index_raw_dim0 <= 32'd0;
            source_rows <= 32'd0;
            source_trailing <= 32'd0;
            source_dtype <= 8'd0;
            matmul_weight_base_q <= 32'd0;
            numeric_profile_dtypes <= 32'd0;
            result_word_cursor <= 32'd0;
            real_launch_count <= 32'd0;
            dma_gather_launch_count <= 32'd0;
            embedding_launch_count <= 32'd0;
            rms_norm_launch_count <= 32'd0;
            dma_transfer_launch_count <= 32'd0;
            matmul_launch_count <= 32'd0;
            capability_fault_count <= 32'd0;
            descriptor_fault_count <= 32'd0;
            engine_fault_count <= 32'd0;
            last_response_index <= NO_ID;
            last_response_family <= 8'd0;
            last_response_sub <= 8'd0;
            last_response_descriptor_id <= NO_ID;
            for (slot = 0; slot < 6; slot = slot + 1) begin
                captured_id[slot] <= NO_ID;
                captured_extent[slot] <= 32'd0;
                captured_axis[slot] <= 8'd0;
                captured_offset[slot] <= 64'd0;
                captured_rank[slot] <= 8'd0;
            end
        end else begin
            engine_start <= 1'b0;
            desc_req <= 1'b0;

            if (clear) begin
                state <= S_IDLE;
                response_fault <= 1'b0;
                response_trap <= TRAP_NONE;
                captured_valid <= 6'd0;
                embedding_q <= 1'b0;
                rms_norm_q <= 1'b0;
                dma_transfer_q <= 1'b0;
                matmul_q <= 1'b0;
                matmul_weight_base_q <= 32'd0;
                result_word_cursor <= 32'd0;
                real_launch_count <= 32'd0;
                dma_gather_launch_count <= 32'd0;
                embedding_launch_count <= 32'd0;
                rms_norm_launch_count <= 32'd0;
                dma_transfer_launch_count <= 32'd0;
                matmul_launch_count <= 32'd0;
                capability_fault_count <= 32'd0;
                descriptor_fault_count <= 32'd0;
                engine_fault_count <= 32'd0;
                last_response_index <= NO_ID;
                last_response_family <= 8'd0;
                last_response_sub <= 8'd0;
                last_response_descriptor_id <= NO_ID;
            end else begin
                if (view_valid && (view_slot < 6)) begin
                    captured_valid[view_slot] <= 1'b1;
                    captured_id[view_slot] <= view_descriptor_id;
                    captured_extent[view_slot] <= view_extent;
                    captured_axis[view_slot] <= view_extent_axis;
                    captured_offset[view_slot] <= view_element_offset;
                    captured_rank[view_slot] <= view_rank;
                end

                case (state)
                    S_IDLE: begin
                        if (issue_valid) begin
                            issue_family_q <= issue_family;
                            issue_sub_q <= issue_sub;
                            issue_descriptor_q <= issue_descriptor_id;
                            issue_index_q <= issue_index;
                            last_response_index <= issue_index;
                            last_response_family <= issue_family;
                            last_response_sub <= issue_sub;
                            last_response_descriptor_id <=
                                issue_descriptor_id;
                            if (!(((issue_family == FAMILY_DMA) &&
                                   (issue_sub == DMA_GATHER)) ||
                                  ((issue_family == FAMILY_TENSOR) &&
                                   (issue_sub == TENSOR_EMBED_LOOKUP)) ||
                                  ((issue_family == FAMILY_TENSOR) &&
                                   (issue_sub == TENSOR_MATMUL)) ||
                                  ((issue_family == FAMILY_VECTOR) &&
                                   (issue_sub == VECTOR_RMS_NORM)) ||
                                  ((issue_family == FAMILY_DMA) &&
                                   (issue_sub == DMA_TRANSFER)))) begin
                                // No speculative launch and no shape guess.
                                response_fault <= 1'b1;
                                response_trap <= TRAP_CAPABILITY;
                                state <= S_RESPONSE;
                            end else begin
                                embedding_q <=
                                    (issue_family == FAMILY_TENSOR) &&
                                    (issue_sub == TENSOR_EMBED_LOOKUP);
                                rms_norm_q <=
                                    (issue_family == FAMILY_VECTOR) &&
                                    (issue_sub == VECTOR_RMS_NORM);
                                dma_transfer_q <=
                                    (issue_family == FAMILY_DMA) &&
                                    (issue_sub == DMA_TRANSFER);
                                matmul_q <=
                                    (issue_family == FAMILY_TENSOR) &&
                                    (issue_sub == TENSOR_MATMUL);
                                desc_req <= 1'b1;
                                desc_id <= issue_descriptor_id;
                                state <= S_OP_WAIT;
                            end
                        end
                    end

                    S_OP_WAIT: begin
                        if (desc_valid) begin
                            if (!descriptor_header_ok(
                                    desc_data, desc_fault, DESC_OPERATOR,
                                    32'd128, 32'd64
                                ) ||
                                (desc_data[519:512] != issue_family_q) ||
                                (desc_data[527:520] != issue_sub_q) ||
                                (desc_data[543:528] != 0) ||
                                (desc_data[639:608] == NO_ID) ||
                                (desc_data[671:640] == NO_ID) ||
                                (desc_data[703:672] == NO_ID) ||
                                (desc_data[735:704] == NO_ID) ||
                                (!dma_transfer_q &&
                                 (desc_data[767:736] == NO_ID)) ||
                                (dma_transfer_q &&
                                 (desc_data[767:736] != NO_ID)) ||
                                (desc_data[799:768] != NO_ID) ||
                                (desc_data[831:800] != NO_ID) ||
                                (desc_data[863:832] == NO_ID) ||
                                (desc_data[895:864] != NO_ID) ||
                                (desc_data[927:896] != NO_ID) ||
                                (desc_data[959:928] != NO_ID) ||
                                (desc_data[991:960] != NO_ID) ||
                                (desc_data[1023:992] != NO_ID) ||
                                (desc_data[223:192] !=
                                 desc_data[671:640]) ||
                                (!dma_transfer_q &&
                                 (captured_valid != 6'b010011)) ||
                                (dma_transfer_q &&
                                 (captured_valid != 6'b010001)) ||
                                (captured_id[0] != desc_data[735:704]) ||
                                (!dma_transfer_q &&
                                 (captured_id[1] != desc_data[767:736])) ||
                                (captured_id[4] != desc_data[863:832])) begin
                                response_fault <= 1'b1;
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                op_numeric <= desc_data[671:640];
                                op_input0 <= desc_data[735:704];
                                op_input1 <= desc_data[767:736];
                                op_output0 <= desc_data[863:832];
                                desc_req <= 1'b1;
                                desc_id <= desc_data[735:704];
                                state <= (rms_norm_q || matmul_q)
                                      ? S_RMS_INPUT_WAIT
                                      : dma_transfer_q ? S_SOURCE_WAIT
                                      : S_INDEX_WAIT;
                            end
                        end
                    end

                    S_INDEX_WAIT: begin
                        if (desc_valid) begin
                            if (!descriptor_header_ok(
                                    desc_data, desc_fault, DESC_TENSOR_VIEW,
                                    32'd192, 32'd128
                                ) ||
                                (desc_view_dtype != FMT_U32) ||
                                (desc_view_rank != 8'd1) ||
                                (desc_view_layout != 8'd0) ||
                                (desc_view_terms > 8'd4) ||
                                (desc_view_scale_object != NO_ID) ||
                                (desc_view_scale_block != 32'd0) ||
                                (desc_primary_object == NO_ID) ||
                                ((desc_permissions & 32'd1) == 0) ||
                                (desc_view_dim0 == 0) ||
                                (desc_view_dim1 != 0) ||
                                (desc_view_dim2 != 0) ||
                                (desc_view_dim3 != 0) ||
                                (desc_view_dim4 != 0) ||
                                (desc_view_dim5 != 0) ||
                                (desc_view_stride0 != 1) ||
                                (desc_view_stride1 != 0) ||
                                (desc_view_stride2 != 0) ||
                                (desc_view_stride3 != 0) ||
                                (desc_view_stride4 != 0) ||
                                (desc_view_stride5 != 0) ||
                                (captured_rank[0] != 1) ||
                                (captured_axis[0] != 0) ||
                                (captured_extent[0] != 1)) begin
                                response_fault <= 1'b1;
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                index_raw_dim0 <= desc_view_dim0;
                                desc_req <= 1'b1;
                                desc_id <= op_input1;
                                state <= S_SOURCE_WAIT;
                            end
                        end
                    end

                    S_RMS_INPUT_WAIT: begin
                        if (desc_valid) begin
                            if (!descriptor_header_ok(
                                    desc_data, desc_fault, DESC_TENSOR_VIEW,
                                    32'd192, 32'd128
                                ) ||
                                (desc_view_dtype != FMT_BF16) ||
                                (desc_view_rank != 8'd2) ||
                                (desc_view_layout != 8'd0) ||
                                (desc_view_terms > 8'd4) ||
                                (desc_view_scale_object != NO_ID) ||
                                (desc_view_scale_block != 0) ||
                                (desc_primary_object == NO_ID) ||
                                ((desc_permissions & 32'd1) == 0) ||
                                (desc_view_dim0 == 0) ||
                                (desc_view_dim1 != EMBEDDING_WIDTH) ||
                                (desc_view_dim2 != 0) ||
                                (desc_view_dim3 != 0) ||
                                (desc_view_dim4 != 0) ||
                                (desc_view_dim5 != 0) ||
                                (desc_view_stride0 != EMBEDDING_WIDTH) ||
                                (desc_view_stride1 != 1) ||
                                (desc_view_stride2 != 0) ||
                                (desc_view_stride3 != 0) ||
                                (desc_view_stride4 != 0) ||
                                (desc_view_stride5 != 0) ||
                                (captured_rank[0] != 2) ||
                                (captured_axis[0] != 0) ||
                                (captured_extent[0] != 1) ||
                                (captured_offset[0] != desc_view_offset)) begin
                                response_fault <= 1'b1;
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                index_raw_dim0 <= desc_view_dim0;
                                source_rows <= matmul_q
                                    ? 32'd0 : 32'd1;
                                source_trailing <= EMBEDDING_WIDTH;
                                source_dtype <= FMT_BF16;
                                desc_req <= 1'b1;
                                desc_id <= op_input1;
                                state <= S_SOURCE_WAIT;
                            end
                        end
                    end

                    S_SOURCE_WAIT: begin
                        if (desc_valid) begin
                            if (!input_view_common_ok ||
                                !(dense_row_source_ok ||
                                  rms_weight_source_ok ||
                                  matmul_weight_source_ok ||
                                  transfer_source_ok) ||
                                (matmul_q &&
                                 !matmul_weight_object_mapped)) begin
                                response_fault <= 1'b1;
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                if (dma_transfer_q) begin
                                    index_raw_dim0 <= desc_view_dim0;
                                    source_rows <= 32'd1;
                                    source_trailing <= EMBEDDING_WIDTH;
                                    source_dtype <= FMT_BF16;
                                end else if (!rms_norm_q) begin
                                    source_rows <= desc_view_dim0;
                                    source_trailing <= desc_view_dim1;
                                    source_dtype <= desc_view_dtype;
                                    if (matmul_q)
                                        matmul_weight_base_q <=
                                            mapped_matmul_weight_base;
                                end
                                desc_req <= 1'b1;
                                desc_id <= op_output0;
                                state <= S_OUTPUT_WAIT;
                            end
                        end
                    end

                    S_OUTPUT_WAIT: begin
                        if (desc_valid) begin
                            if (!output_view_common_ok ||
                                !(dense_row_output_ok ||
                                  matmul_output_ok ||
                                  transfer_output_ok)) begin
                                response_fault <= 1'b1;
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                desc_req <= 1'b1;
                                desc_id <= op_numeric;
                                state <= S_NUM_WAIT;
                            end
                        end
                    end

                    S_NUM_WAIT: begin
                        if (desc_valid) begin
                            if (!numeric_common_ok ||
                                !(gather_numeric_ok ||
                                  embedding_numeric_ok ||
                                  rms_numeric_ok ||
                                  matmul_numeric_ok ||
                                  transfer_numeric_ok)) begin
                                response_fault <= 1'b1;
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                numeric_profile_dtypes <= {
                                    desc_data[535:528],
                                    desc_data[543:536],
                                    desc_data[527:520],
                                    desc_data[519:512]
                                };
                                state <= S_START;
                            end
                        end
                    end

                    S_START: begin
                        engine_start <= 1'b1;
                        state <= S_ENGINE_WAIT;
                    end

                    S_ENGINE_WAIT: begin
                        if (engine_done) begin
                            if ((engine_error_code != ERR_NONE) ||
                                (engine_result_count != expected_result_count) ||
                                (engine_work_count != expected_work_count)) begin
                                response_fault <= 1'b1;
                                response_trap <= TRAP_ENGINE;
                            end else begin
                                response_fault <= 1'b0;
                                response_trap <= TRAP_NONE;
                            end
                            state <= S_RESPONSE;
                        end
                    end

                    S_RESPONSE: begin
                        if (response_fire) begin
                            if (!response_fault) begin
                                real_launch_count <= real_launch_count + 1;
                                result_word_cursor <=
                                    result_word_cursor + expected_result_count;
                                if (rms_norm_q)
                                    rms_norm_launch_count <=
                                        rms_norm_launch_count + 1;
                                else if (matmul_q)
                                    matmul_launch_count <=
                                        matmul_launch_count + 1;
                                else if (dma_transfer_q)
                                    dma_transfer_launch_count <=
                                        dma_transfer_launch_count + 1;
                                else if (embedding_q)
                                    embedding_launch_count <=
                                        embedding_launch_count + 1;
                                else
                                    dma_gather_launch_count <=
                                        dma_gather_launch_count + 1;
                            end else if (response_trap == TRAP_CAPABILITY)
                                capability_fault_count <=
                                    capability_fault_count + 1;
                            else if (response_trap == TRAP_DESCRIPTOR)
                                descriptor_fault_count <=
                                    descriptor_fault_count + 1;
                            else
                                engine_fault_count <= engine_fault_count + 1;
                            captured_valid <= 6'd0;
                            state <= S_IDLE;
                        end
                    end

                    default: state <= S_IDLE;
                endcase
            end
        end
    end

    wire array_m0_rd_en;
    wire [31:0] array_m0_rd_addr;
    wire array_m1_rd_en;
    wire [31:0] array_m1_rd_addr;
    wire array_m2_rd_en;
    wire [31:0] array_m2_rd_addr;
    wire array_m3_rd_en;
    wire [31:0] array_m3_rd_addr;
    wire array_out_we;
    wire [31:0] array_out_addr;
    wire [31:0] array_out_data;
    wire array_busy;
    wire array_done;
    wire [7:0] array_error_code;
    wire [31:0] array_result_count;
    wire [31:0] array_saturation_count;
    wire [31:0] array_work_count;
    wire [31:0] array_token;
    wire [31:0] array_tie_multiplicity;

    wire rms_input_rd_en;
    wire [31:0] rms_input_rd_addr;
    wire rms_weight_rd_en;
    wire [31:0] rms_weight_rd_addr;
    wire rms_out_we;
    wire [31:0] rms_out_addr;
    wire [31:0] rms_out_data;
    wire rms_busy;
    wire rms_done;
    wire [7:0] rms_error_code;
    wire [31:0] rms_result_count;
    wire [31:0] rms_saturation_count;
    wire [31:0] rms_work_count;

    wire engine_done = rms_norm_q ? rms_done : array_done;
    assign engine_busy = rms_norm_q ? rms_busy : array_busy;
    assign engine_error_code = rms_norm_q
        ? rms_error_code : array_error_code;
    assign engine_result_count = rms_norm_q
        ? rms_result_count : array_result_count;
    assign engine_work_count = rms_norm_q
        ? rms_work_count : array_work_count;
    wire [31:0] expected_result_count = rms_norm_q
        ? EMBEDDING_WIDTH
        : matmul_q ? source_rows
        : dma_transfer_q ? (TRANSFER_COPIES * EMBEDDING_WIDTH)
        : source_trailing;
    wire [31:0] expected_work_count = rms_norm_q
        ? EMBEDDING_WIDTH
        : matmul_q ? (source_rows * source_trailing)
        : dma_transfer_q ? TRANSFER_COPIES : 32'd1;

    assign m0_rd_en = rms_norm_q ? rms_input_rd_en : array_m0_rd_en;
    assign m0_rd_addr = rms_norm_q ? rms_input_rd_addr : array_m0_rd_addr;
    assign m1_rd_en = rms_norm_q ? rms_weight_rd_en : array_m1_rd_en;
    assign m1_rd_addr = rms_norm_q ? rms_weight_rd_addr : array_m1_rd_addr;
    assign m2_rd_en = rms_norm_q ? 1'b0 : array_m2_rd_en;
    assign m2_rd_addr = rms_norm_q ? 32'd0 : array_m2_rd_addr;
    assign m3_rd_en = rms_norm_q ? 1'b0 : array_m3_rd_en;
    assign m3_rd_addr = rms_norm_q ? 32'd0 : array_m3_rd_addr;
    assign out_we = rms_norm_q ? rms_out_we : array_out_we;
    assign out_addr = rms_norm_q ? rms_out_addr : array_out_addr;
    assign out_data = rms_norm_q ? rms_out_data : array_out_data;
    assign m0_reads_result = rms_norm_q || matmul_q;
    assign m1_reads_result = dma_transfer_q;
    assign m1_reads_matmul_weight = matmul_q;

    wire [31:0] launch_index_base = dma_transfer_q
        ? cfg_transfer_index_base
        : (cfg_index_base + real_launch_count);
    wire [31:0] launch_source_base = dma_transfer_q
        ? cfg_transfer_source_base
        : embedding_q
            ? (cfg_embedding_source_base +
               embedding_launch_count * EMBEDDING_WIDTH)
            : (cfg_source_base +
               dma_gather_launch_count * cfg_source_launch_stride);
    wire [31:0] launch_output_base =
        cfg_output_base + result_word_cursor;

    ot_a3_vector_rms_norm rms_norm (
        .clk(clk),
        .rst_n(rst_n),
        .start(engine_start & rms_norm_q),
        .cfg_count(EMBEDDING_WIDTH),
        .cfg_epsilon_bits(RMS_EPSILON),
        .cfg_input_base(cfg_rms_input_base),
        .cfg_weight_base(cfg_rms_weight_base),
        .cfg_output_base(launch_output_base),
        .input_rd_en(rms_input_rd_en),
        .input_rd_addr(rms_input_rd_addr),
        .input_rd_data(m0_rd_data),
        .weight_rd_en(rms_weight_rd_en),
        .weight_rd_addr(rms_weight_rd_addr),
        .weight_rd_data(m1_rd_data),
        .out_we(rms_out_we),
        .out_addr(rms_out_addr),
        .out_data(rms_out_data),
        .busy(rms_busy),
        .done(rms_done),
        .error_code(rms_error_code),
        .result_count(rms_result_count),
        .saturation_count(rms_saturation_count),
        .work_count(rms_work_count)
    );

    ot_a3_engine_array engines (
        .clk(clk),
        .rst_n(rst_n),
        .start(engine_start & !rms_norm_q),
        .cfg_family(matmul_q ? FAMILY_TENSOR : FAMILY_DMA),
        .cfg_sub(matmul_q ? TENSOR_MATMUL : DMA_GATHER),
        .cfg_rows(matmul_q ? 16'd1 : 16'd0),
        .cfg_cols(matmul_q ? source_rows[15:0] : source_trailing[15:0]),
        .cfg_depth(matmul_q ? source_trailing[15:0] : 16'd0),
        .cfg_count(expected_result_count),
        .cfg_dtype_a(matmul_q ? FMT_BF16 : FMT_U32),
        .cfg_dtype_b(source_dtype),
        .cfg_a_base(matmul_q ? cfg_matmul_input_base : launch_index_base),
        .cfg_b_base(matmul_q ? matmul_weight_base_q : launch_source_base),
        .cfg_c_base(32'd0),
        .cfg_out_base(launch_output_base),
        .cfg_scale_a(1'b0),
        .cfg_scale_b(1'b0),
        .cfg_block_a(16'd0),
        .cfg_block_b(16'd0),
        .cfg_block_rows_a(16'd0),
        .cfg_block_rows_b(16'd0),
        .cfg_scale_a_base(32'd0),
        .cfg_scale_b_base(32'd0),
        .cfg_slots(dma_transfer_q ? TRANSFER_COPIES : 32'd1),
        .cfg_trailing(source_trailing),
        .cfg_extent(dma_transfer_q ? 32'd1 : source_rows),
        .cfg_input_valid(4'b0011),
        .cfg_output_valid(2'b01),
        .cfg_input_dtypes({16'd0, source_dtype,
            matmul_q ? FMT_BF16 : FMT_U32}),
        .cfg_output_dtypes({8'd0, source_dtype}),
        .cfg_view_ranks(matmul_q ? 24'h02_00_22 : 24'h02_00_21),
        .cfg_view_scaled(6'd0),
        .cfg_profile_valid(1'b1),
        .cfg_profile_dtypes(numeric_profile_dtypes),
        .cfg_rounding_mode(8'd0),
        .cfg_reduction_order(matmul_q ? 8'd2 : 8'd0),
        .cfg_profile_saturate(1'b0),
        .cfg_nan_policy(8'd0),
        .cfg_profile_scale_bits(32'd0),
        .cfg_epsilon_bits(32'd0),
        .cfg_profile_flags(32'd0),
        .cfg_input0_dims(matmul_q
            ? {64'd0, source_trailing, 32'd1}
            : {96'd0, dma_transfer_q ? TRANSFER_COPIES : 32'd1}),
        .cfg_input1_dims({64'd0, source_trailing,
            dma_transfer_q ? 32'd1 : source_rows}),
        .cfg_input2_dims(128'd0),
        .cfg_input3_dims(128'd0),
        .cfg_output0_dims(matmul_q
            ? {64'd0, source_rows, 32'd1}
            : {64'd0, source_trailing,
               dma_transfer_q ? TRANSFER_COPIES : 32'd1}),
        .cfg_output1_dims(128'd0),
        .cfg_contract_0(matmul_q ? 32'h7550dc6a : embedding_q
            ? ((source_rows == QWEN_VOCABULARY)
                ? 32'hd1ea2f18 : 32'hca62e720)
            : 32'h12a24197),
        .cfg_contract_1(matmul_q ? 32'h773fd9d5 : embedding_q
            ? ((source_rows == QWEN_VOCABULARY)
                ? 32'he0b161e1 : 32'haa0132c2)
            : 32'hc80d3851),
        .cfg_contract_2(matmul_q ? 32'h773b4618 : embedding_q
            ? ((source_rows == QWEN_VOCABULARY)
                ? 32'h9e17f465 : 32'h1f095a7f)
            : 32'hcc5ea3e6),
        .cfg_contract_3(matmul_q ? 32'h2887613f : embedding_q
            ? ((source_rows == QWEN_VOCABULARY)
                ? 32'hced630e0 : 32'h1f8d5d94)
            : 32'h9915f7db),
        .cfg_contract_4(matmul_q ? 32'hb777bb8e : embedding_q
            ? ((source_rows == QWEN_VOCABULARY)
                ? 32'haf7d0de9 : 32'h07149b85)
            : 32'hc926aa1c),
        .cfg_contract_5(matmul_q ? 32'h4f016523 : embedding_q
            ? ((source_rows == QWEN_VOCABULARY)
                ? 32'h70dadd67 : 32'h47ddeb0a)
            : 32'h2ee795c8),
        .cfg_contract_6(matmul_q ? 32'h21c4d93c : embedding_q
            ? ((source_rows == QWEN_VOCABULARY)
                ? 32'h76c685ab : 32'hbd5d882a)
            : 32'hfe3af1a6),
        .cfg_contract_7(matmul_q ? 32'ha0765aa1 : embedding_q
            ? ((source_rows == QWEN_VOCABULARY)
                ? 32'h6539fbcc : 32'h2f0180d3)
            : 32'h7677daee),
        .cfg_aux_valid(4'd0),
        .cfg_aux0(NO_ID),
        .cfg_aux1(NO_ID),
        .cfg_aux2(NO_ID),
        .cfg_aux3(NO_ID),
        .m0_rd_en(array_m0_rd_en),
        .m0_rd_addr(array_m0_rd_addr),
        .m0_rd_data(m0_rd_data),
        .m1_rd_en(array_m1_rd_en),
        .m1_rd_addr(array_m1_rd_addr),
        .m1_rd_data(m1_rd_data),
        .m2_rd_en(array_m2_rd_en),
        .m2_rd_addr(array_m2_rd_addr),
        .m2_rd_data(m2_rd_data),
        .m3_rd_en(array_m3_rd_en),
        .m3_rd_addr(array_m3_rd_addr),
        .m3_rd_data(m3_rd_data),
        .out_we(array_out_we),
        .out_addr(array_out_addr),
        .out_data(array_out_data),
        .busy(array_busy),
        .done(array_done),
        .error_code(array_error_code),
        .result_count(array_result_count),
        .saturation_count(array_saturation_count),
        .work_count(array_work_count),
        .token(array_token),
        .tie_multiplicity(array_tie_multiplicity)
    );
endmodule
