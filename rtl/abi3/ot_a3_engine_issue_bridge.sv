`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Small ABI 3.0 sequencer-to-engine bridge.
//
// This is deliberately a bounded production profile, not a claim that every
// shipped operator has an RTL datapath.  It admits the exact dense one-index
// DMA.GATHER form at the head of all four shipped decode programs, launches
// the existing real engine array, and returns completion to the sequencer only
// after the datapath finishes.  Every other opcode returns a precise
// CAPABILITY trap.  Malformed operator/view/numeric metadata returns a
// DESCRIPTOR trap, and an engine failure returns an ENGINE trap.
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
    // supported gather uses each base.  Later gathers advance by the stated
    // source stride, one index word, and one output row respectively.
    input  wire [31:0]   cfg_index_base,
    input  wire [31:0]   cfg_source_base,
    input  wire [31:0]   cfg_source_launch_stride,
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

    // Non-control observation for the focused checker.
    output wire          engine_busy,
    output wire [7:0]    engine_error_code,
    output wire [31:0]   engine_result_count,
    output wire [31:0]   engine_work_count,
    output reg  [31:0]   real_launch_count,
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
    localparam [7:0] DMA_GATHER = 8'h02;
    localparam [7:0] FMT_U32 = 8'h04;
    localparam [7:0] FMT_I32 = 8'h05;
    localparam [7:0] FMT_FP32 = 8'h12;
    localparam [7:0] ERR_NONE = 8'd0;

    // The raw little-endian 256-bit value held in NUMERIC payload bytes
    // 32..63 for SHA-256("exact_index_select_v1").  Comparing the descriptor
    // bytes avoids silently accepting another contract with the same dtypes.
    localparam [255:0] CONTRACT_EXACT_INDEX_SELECT_RAW =
        256'heeda7776a6f13afec895e72e1caa26c9dbf71599e6a35ecc51380dc89741a212;

    localparam [3:0] S_IDLE        = 4'd0;
    localparam [3:0] S_OP_WAIT     = 4'd1;
    localparam [3:0] S_INDEX_WAIT  = 4'd2;
    localparam [3:0] S_SOURCE_WAIT = 4'd3;
    localparam [3:0] S_OUTPUT_WAIT = 4'd4;
    localparam [3:0] S_NUM_WAIT    = 4'd5;
    localparam [3:0] S_START       = 4'd6;
    localparam [3:0] S_ENGINE_WAIT = 4'd7;
    localparam [3:0] S_RESPONSE    = 4'd8;

    reg [3:0] state;
    reg       response_fault;
    reg [15:0] response_trap;
    reg       engine_start;

    reg [7:0]  issue_family_q;
    reg [7:0]  issue_sub_q;
    reg [31:0] issue_descriptor_q;
    reg [31:0] issue_index_q;

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
    reg [31:0] numeric_profile_dtypes;

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
            captured_valid <= 6'd0;
            op_input0 <= NO_ID;
            op_input1 <= NO_ID;
            op_output0 <= NO_ID;
            op_numeric <= NO_ID;
            index_raw_dim0 <= 32'd0;
            source_rows <= 32'd0;
            source_trailing <= 32'd0;
            source_dtype <= 8'd0;
            numeric_profile_dtypes <= 32'd0;
            real_launch_count <= 32'd0;
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
                real_launch_count <= 32'd0;
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
                            if ((issue_family != FAMILY_DMA) ||
                                (issue_sub != DMA_GATHER)) begin
                                // No speculative launch and no shape guess.
                                response_fault <= 1'b1;
                                response_trap <= TRAP_CAPABILITY;
                                state <= S_RESPONSE;
                            end else begin
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
                                (desc_data[519:512] != FAMILY_DMA) ||
                                (desc_data[527:520] != DMA_GATHER) ||
                                (desc_data[671:640] == NO_ID) ||
                                (desc_data[703:672] == NO_ID) ||
                                (desc_data[735:704] == NO_ID) ||
                                (desc_data[767:736] == NO_ID) ||
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
                                (captured_valid != 6'b010011) ||
                                (captured_id[0] != desc_data[735:704]) ||
                                (captured_id[1] != desc_data[767:736]) ||
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
                                state <= S_INDEX_WAIT;
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

                    S_SOURCE_WAIT: begin
                        if (desc_valid) begin
                            if (!descriptor_header_ok(
                                    desc_data, desc_fault, DESC_TENSOR_VIEW,
                                    32'd192, 32'd128
                                ) ||
                                (desc_view_dtype != FMT_FP32) ||
                                (desc_view_rank != 8'd2) ||
                                (desc_view_layout != 8'd0) ||
                                (desc_view_terms != 0) ||
                                (desc_view_scale_object != NO_ID) ||
                                (desc_view_scale_block != 0) ||
                                (desc_primary_object == NO_ID) ||
                                ((desc_permissions & 32'd1) == 0) ||
                                (desc_view_dim0 == 0) ||
                                (desc_view_dim1 == 0) ||
                                (desc_view_dim2 != 0) ||
                                (desc_view_dim3 != 0) ||
                                (desc_view_dim4 != 0) ||
                                (desc_view_dim5 != 0) ||
                                (desc_view_stride0 != desc_view_dim1) ||
                                (desc_view_stride1 != 1) ||
                                (desc_view_stride2 != 0) ||
                                (desc_view_stride3 != 0) ||
                                (desc_view_stride4 != 0) ||
                                (desc_view_stride5 != 0) ||
                                (captured_rank[1] != 2) ||
                                (captured_axis[1] != 0) ||
                                (captured_extent[1] != desc_view_dim0) ||
                                (captured_offset[1] != desc_view_offset)) begin
                                response_fault <= 1'b1;
                                response_trap <= TRAP_DESCRIPTOR;
                                state <= S_RESPONSE;
                            end else begin
                                source_rows <= desc_view_dim0;
                                source_trailing <= desc_view_dim1;
                                source_dtype <= desc_view_dtype;
                                desc_req <= 1'b1;
                                desc_id <= op_output0;
                                state <= S_OUTPUT_WAIT;
                            end
                        end
                    end

                    S_OUTPUT_WAIT: begin
                        if (desc_valid) begin
                            if (!descriptor_header_ok(
                                    desc_data, desc_fault, DESC_TENSOR_VIEW,
                                    32'd192, 32'd128
                                ) ||
                                (desc_view_dtype != source_dtype) ||
                                (desc_view_rank != 8'd2) ||
                                (desc_view_layout != 8'd0) ||
                                (desc_view_terms > 8'd4) ||
                                (desc_view_scale_object != NO_ID) ||
                                (desc_view_scale_block != 0) ||
                                (desc_primary_object == NO_ID) ||
                                ((desc_permissions & 32'd2) == 0) ||
                                (desc_view_dim0 != index_raw_dim0) ||
                                (desc_view_dim1 != source_trailing) ||
                                (desc_view_dim2 != 0) ||
                                (desc_view_dim3 != 0) ||
                                (desc_view_dim4 != 0) ||
                                (desc_view_dim5 != 0) ||
                                (desc_view_stride0 != source_trailing) ||
                                (desc_view_stride1 != 1) ||
                                (desc_view_stride2 != 0) ||
                                (desc_view_stride3 != 0) ||
                                (desc_view_stride4 != 0) ||
                                (desc_view_stride5 != 0) ||
                                (captured_rank[4] != 2) ||
                                (captured_axis[4] != 0) ||
                                (captured_extent[4] != captured_extent[0])) begin
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
                            if (!descriptor_header_ok(
                                    desc_data, desc_fault, DESC_NUMERIC,
                                    32'd128, 32'd64
                                ) ||
                                ((desc_data[519:512] != FMT_U32) &&
                                 (desc_data[519:512] != FMT_I32)) ||
                                (desc_data[527:520] != source_dtype) ||
                                (desc_data[535:528] != FMT_FP32) ||
                                (desc_data[543:536] != source_dtype) ||
                                (desc_data[551:544] != 0) ||
                                (desc_data[559:552] != 0) ||
                                (desc_data[567:560] != 0) ||
                                (desc_data[575:568] != 0) ||
                                (desc_data[607:576] != 0) ||
                                (desc_data[639:608] != 0) ||
                                (desc_data[671:640] != 0) ||
                                (desc_data[703:672] != 0) ||
                                (desc_data[767:704] != 0) ||
                                (desc_data[1023:768] !=
                                 CONTRACT_EXACT_INDEX_SELECT_RAW)) begin
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
                                (engine_result_count != source_trailing) ||
                                (engine_work_count != 1)) begin
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
                            if (!response_fault)
                                real_launch_count <= real_launch_count + 1;
                            else if (response_trap == TRAP_CAPABILITY)
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

    wire engine_done;
    wire [31:0] engine_saturation_count;
    wire [31:0] engine_token;
    wire [31:0] engine_tie_multiplicity;
    wire [31:0] launch_index_base =
        cfg_index_base + real_launch_count;
    wire [31:0] launch_source_base =
        cfg_source_base + real_launch_count * cfg_source_launch_stride;
    wire [31:0] launch_output_base =
        cfg_output_base + real_launch_count * source_trailing;

    ot_a3_engine_array engines (
        .clk(clk),
        .rst_n(rst_n),
        .start(engine_start),
        .cfg_family(issue_family_q),
        .cfg_sub(issue_sub_q),
        .cfg_rows(16'd0),
        .cfg_cols(source_trailing[15:0]),
        .cfg_depth(16'd0),
        .cfg_count(source_trailing),
        .cfg_dtype_a(FMT_U32),
        .cfg_dtype_b(source_dtype),
        .cfg_a_base(launch_index_base),
        .cfg_b_base(launch_source_base),
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
        .cfg_slots(32'd1),
        .cfg_trailing(source_trailing),
        .cfg_extent(source_rows),
        .cfg_input_valid(4'b0011),
        .cfg_output_valid(2'b01),
        .cfg_input_dtypes({16'd0, source_dtype, FMT_U32}),
        .cfg_output_dtypes({8'd0, source_dtype}),
        .cfg_view_ranks(24'h02_00_21),
        .cfg_view_scaled(6'd0),
        .cfg_profile_valid(1'b1),
        .cfg_profile_dtypes(numeric_profile_dtypes),
        .cfg_rounding_mode(8'd0),
        .cfg_reduction_order(8'd0),
        .cfg_profile_saturate(1'b0),
        .cfg_nan_policy(8'd0),
        .cfg_profile_scale_bits(32'd0),
        .cfg_epsilon_bits(32'd0),
        .cfg_profile_flags(32'd0),
        .cfg_input0_dims({96'd0, 32'd1}),
        .cfg_input1_dims({64'd0, source_trailing, source_rows}),
        .cfg_input2_dims(128'd0),
        .cfg_input3_dims(128'd0),
        .cfg_output0_dims({64'd0, source_trailing, 32'd1}),
        .cfg_output1_dims(128'd0),
        .cfg_contract_0(32'h12a24197),
        .cfg_contract_1(32'hc80d3851),
        .cfg_contract_2(32'hcc5ea3e6),
        .cfg_contract_3(32'h9915f7db),
        .cfg_contract_4(32'hc926aa1c),
        .cfg_contract_5(32'h2ee795c8),
        .cfg_contract_6(32'hfe3af1a6),
        .cfg_contract_7(32'h7677daee),
        .cfg_aux_valid(4'd0),
        .cfg_aux0(NO_ID),
        .cfg_aux1(NO_ID),
        .cfg_aux2(NO_ID),
        .cfg_aux3(NO_ID),
        .m0_rd_en(m0_rd_en),
        .m0_rd_addr(m0_rd_addr),
        .m0_rd_data(m0_rd_data),
        .m1_rd_en(m1_rd_en),
        .m1_rd_addr(m1_rd_addr),
        .m1_rd_data(m1_rd_data),
        .m2_rd_en(m2_rd_en),
        .m2_rd_addr(m2_rd_addr),
        .m2_rd_data(m2_rd_data),
        .m3_rd_en(m3_rd_en),
        .m3_rd_addr(m3_rd_addr),
        .m3_rd_data(m3_rd_data),
        .out_we(out_we),
        .out_addr(out_addr),
        .out_data(out_data),
        .busy(engine_busy),
        .done(engine_done),
        .error_code(engine_error_code),
        .result_count(engine_result_count),
        .saturation_count(engine_saturation_count),
        .work_count(engine_work_count),
        .token(engine_token),
        .tie_multiplicity(engine_tie_multiplicity)
    );
endmodule
