`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Exact Qwen3-8B ABI 3.0 KV-append continuation.
//
// This adapter is deliberately narrower than the shared four-target issue
// bridge.  It consumes the real instruction and descriptor records at Qwen
// decode PCs 32/35, validates their CRCs and complete required semantics, and
// executes the one-row key/value append through ot_a3_dma_index_mover.  It also
// admits the exact metadata at PC 38 and returns CAPABILITY before any write:
// grouped-query attention arithmetic is the next honest RTL boundary.
//
// The compact prior/output memories are logical K or V planes.  The adapter
// validates the physical ABI view's 2,048-element interleaved row stride and
// 0/1,024 plane offset before mapping one selected plane into that compact
// verification bank.  No token, logit, or attention result enters this block.
//
// The active context is a runtime length inside a compile-time bound, not the
// constant 17 it began as.  A constant 17 admits exactly the first generated
// token: the governed workload's three decode positions run at contexts 17,
// 18 and 19, and the second and third were refused with a DESCRIPTOR trap.
// The invariant that actually matters is preserved and still checked -- the
// context is the index view's own resolved position plus one -- and the
// bound is now the parameter pair below, with the same lower limit of eight
// the attention datapath's eight-lane softmax reduction requires.
// ---------------------------------------------------------------------------
module ot_a3_qwen_kv_scatter_adapter #(
    parameter integer MIN_CONTEXT = 8,
    parameter integer MAX_CONTEXT = 32
) (
    input  wire           clk,
    input  wire           rst_n,
    input  wire           start,

    input  wire [255:0]   instruction_record,
    input  wire [31:0]    instruction_index,
    input  wire [31:0]    instruction_count,
    input  wire [31:0]    operator_descriptor_id,
    input  wire [31:0]    view0_descriptor_id,
    input  wire [31:0]    view1_descriptor_id,
    input  wire [31:0]    view2_descriptor_id,
    input  wire [31:0]    view3_descriptor_id,
    input  wire [31:0]    output_descriptor_id,
    input  wire [31:0]    numeric_descriptor_id,
    input  wire [31:0]    expected_object0,
    input  wire [31:0]    expected_object1,
    input  wire [31:0]    expected_object2,
    input  wire [31:0]    expected_object3,
    input  wire [31:0]    expected_output_object,

    input  wire [1535:0]  operator_record,
    input  wire [1535:0]  view0_record,
    input  wire [1535:0]  view1_record,
    input  wire [1535:0]  view2_record,
    input  wire [1535:0]  view3_record,
    input  wire [1535:0]  output_record,
    input  wire [1535:0]  numeric_record,

    input  wire [31:0]    cfg_position_start,
    input  wire [31:0]    cfg_context_length,
    input  wire [31:0]    cfg_index_base,
    input  wire [31:0]    cfg_source_base,
    input  wire [31:0]    cfg_prior_base,
    input  wire [31:0]    cfg_output_base,

    output wire           idx_rd_en,
    output wire [31:0]    idx_rd_addr,
    input  wire [31:0]    idx_rd_data,
    output wire           src_rd_en,
    output wire [31:0]    src_rd_addr,
    input  wire [31:0]    src_rd_data,
    output wire           out_we,
    output wire [31:0]    out_addr,
    output wire [31:0]    out_data,

    output reg            busy,
    output reg            done,
    output reg            failed,
    output reg  [15:0]    trap_class,
    output reg  [7:0]     refusal_reason,
    output reg  [31:0]    records_checked,
    output reg  [31:0]    moved_elements,
    output reg  [31:0]    indices_checked,
    output reg  [31:0]    write_count,
    output reg            gqa_boundary
);
    localparam [31:0] NO_ID = 32'hffff_ffff;
    localparam [15:0] DESC_TENSOR_VIEW = 16'h0002;
    localparam [15:0] DESC_NUMERIC = 16'h0003;
    localparam [15:0] DESC_OPERATOR = 16'h000a;
    localparam [15:0] TRAP_NONE = 16'd0;
    localparam [15:0] TRAP_INTEGRITY = 16'd2;
    localparam [15:0] TRAP_DESCRIPTOR = 16'd3;
    localparam [15:0] TRAP_CAPABILITY = 16'd4;
    localparam [15:0] TRAP_ENGINE = 16'd8;
    localparam [7:0] REFUSAL_NONE = 8'd0;
    localparam [7:0] REFUSAL_INSTRUCTION = 8'd1;
    localparam [7:0] REFUSAL_INTEGRITY = 8'd2;
    localparam [7:0] REFUSAL_DESCRIPTOR = 8'd3;
    localparam [7:0] REFUSAL_CAPABILITY = 8'd4;
    localparam [7:0] REFUSAL_ENGINE = 8'd5;
    localparam [7:0] FAMILY_DMA = 8'h10;
    localparam [7:0] DMA_SCATTER = 8'h03;
    localparam [7:0] FAMILY_ATTENTION = 8'h40;
    localparam [7:0] ATTENTION_GQA = 8'h01;
    localparam [7:0] FMT_U32 = 8'h04;
    localparam [7:0] FMT_BF16 = 8'h10;
    localparam [7:0] FMT_FP32 = 8'h12;
    localparam [7:0] ERR_NONE = 8'd0;

    localparam [31:0] KV_HEADS = 32'd8;
    localparam [31:0] QUERY_HEADS = 32'd32;
    localparam [31:0] HEAD_WIDTH = 32'd128;
    localparam [31:0] KV_PLANE_WORDS = 32'd1024;
    localparam [31:0] CACHE_ROWS = 32'd8256;
    localparam [31:0] TOKEN_BLOCK = 32'd512;
    localparam [31:0] KV_ROW_STRIDE = 32'd2048;
    localparam [31:0] GQA_SCALE_BITS = 32'h3db5_0000;
    localparam [255:0] CONTRACT_KV_SCATTER_RAW =
        256'h6fe100be19c00c87797983af8409335999bfd793cdcf3862af5ba6bdcc9bf355;
    localparam [255:0] CONTRACT_GQA_RAW =
        256'h81e12c87d89ead473983a0898c3fbfe08d7b0a3864b55fb1f0171a4698f53a62;

    localparam [3:0] S_IDLE = 4'd0;
    localparam [3:0] S_DECODE_START = 4'd1;
    localparam [3:0] S_DECODE_WAIT = 4'd2;
    localparam [3:0] S_RECORD_START = 4'd3;
    localparam [3:0] S_RECORD_WAIT = 4'd4;
    localparam [3:0] S_ADMIT = 4'd5;
    localparam [3:0] S_INDEX_ISSUE = 4'd6;
    localparam [3:0] S_INDEX_WAIT = 4'd7;
    localparam [3:0] S_MOVER_START = 4'd8;
    localparam [3:0] S_MOVER_WAIT = 4'd9;
    localparam [3:0] S_FINISH = 4'd10;

    reg [3:0] state;
    reg scatter_q;
    reg gqa_q;
    reg [2:0] record_slot;
    reg [2:0] record_count;

    reg [255:0] instruction_record_q;
    reg [31:0] instruction_index_q;
    reg [31:0] instruction_count_q;
    reg [31:0] operator_id_q;
    reg [31:0] view0_id_q;
    reg [31:0] view1_id_q;
    reg [31:0] view2_id_q;
    reg [31:0] view3_id_q;
    reg [31:0] output_id_q;
    reg [31:0] numeric_id_q;
    reg [31:0] object0_q;
    reg [31:0] object1_q;
    reg [31:0] object2_q;
    reg [31:0] object3_q;
    reg [31:0] output_object_q;
    reg [1535:0] operator_record_q;
    reg [1535:0] view0_record_q;
    reg [1535:0] view1_record_q;
    reg [1535:0] view2_record_q;
    reg [1535:0] view3_record_q;
    reg [1535:0] output_record_q;
    reg [1535:0] numeric_record_q;
    reg [31:0] position_q;
    reg [31:0] context_q;
    reg [31:0] index_base_q;
    reg [31:0] source_base_q;
    reg [31:0] prior_base_q;
    reg [31:0] output_base_q;

    reg [7:0] instruction_major_q;
    reg [7:0] instruction_sub_q;
    reg [15:0] instruction_flags_q;
    reg [31:0] instruction_predicate_q;
    reg [31:0] instruction_descriptor_q;
    reg [31:0] instruction_wait_q;
    reg [31:0] instruction_signal_q;
    reg [31:0] instruction_control_q;
    reg [31:0] instruction_source_q;

    wire decoder_in_ready;
    wire decoder_out_valid;
    wire decoder_out_legal;
    wire [3:0] decoder_out_error;
    wire [15:0] decoder_out_trap;
    wire [31:0] decoder_out_index;
    wire [7:0] decoder_out_major;
    wire [7:0] decoder_out_sub;
    wire [15:0] decoder_out_flags;
    wire [31:0] decoder_out_predicate;
    wire [31:0] decoder_out_descriptor;
    wire [31:0] decoder_out_wait;
    wire [31:0] decoder_out_signal;
    wire [31:0] decoder_out_control;
    wire [31:0] decoder_out_source;

    ot_a3_instruction_decoder instruction_decoder (
        .clk(clk), .rst_n(rst_n),
        .in_valid(state == S_DECODE_START),
        .in_ready(decoder_in_ready),
        .in_record(instruction_record_q),
        .in_index(instruction_index_q),
        .in_instruction_count(instruction_count_q),
        .out_valid(decoder_out_valid),
        .out_ready(state == S_DECODE_WAIT),
        .out_legal(decoder_out_legal),
        .out_error(decoder_out_error),
        .out_trap_class(decoder_out_trap),
        .out_index(decoder_out_index),
        .out_major(decoder_out_major),
        .out_sub(decoder_out_sub),
        .out_flags(decoder_out_flags),
        .out_predicate_id(decoder_out_predicate),
        .out_descriptor_id(decoder_out_descriptor),
        .out_wait_set_id(decoder_out_wait),
        .out_signal_event_id(decoder_out_signal),
        .out_control_id(decoder_out_control),
        .out_source_operation_id(decoder_out_source)
    );

    reg [1535:0] selected_record;
    reg [15:0] selected_type;
    reg [31:0] selected_total;
    reg [31:0] selected_payload;
    always @* begin
        selected_record = 1536'd0;
        selected_type = DESC_TENSOR_VIEW;
        selected_total = 32'd192;
        selected_payload = 32'd128;
        case (record_slot)
            3'd0: begin
                selected_record = operator_record_q;
                selected_type = DESC_OPERATOR;
                selected_total = 32'd128;
                selected_payload = 32'd64;
            end
            3'd1: selected_record = view0_record_q;
            3'd2: selected_record = view1_record_q;
            3'd3: selected_record = gqa_q
                ? view2_record_q : output_record_q;
            3'd4: begin
                selected_record = gqa_q ? view3_record_q : numeric_record_q;
                if (!gqa_q) begin
                    selected_type = DESC_NUMERIC;
                    selected_total = 32'd128;
                    selected_payload = 32'd64;
                end
            end
            3'd5: selected_record = output_record_q;
            3'd6: begin
                selected_record = numeric_record_q;
                selected_type = DESC_NUMERIC;
                selected_total = 32'd128;
                selected_payload = 32'd64;
            end
            default: selected_record = 1536'd0;
        endcase
    end

    wire record_busy;
    wire record_done;
    wire record_legal;
    wire [7:0] record_error;
    ot_a3_descriptor_record_validator descriptor_validator (
        .clk(clk), .rst_n(rst_n),
        .start(state == S_RECORD_START),
        .record(selected_record),
        .expected_type(selected_type),
        .expected_total_bytes(selected_total),
        .expected_payload_bytes(selected_payload),
        .busy(record_busy), .done(record_done), .legal(record_legal),
        .error_code(record_error)
    );

    function automatic view_header_ok;
        input [1535:0] data;
        input [31:0] object_id;
        input [31:0] permissions;
        input [7:0] dtype;
        input [7:0] rank;
        input [7:0] terms;
        begin
            view_header_ok =
                (data[127:96] == 32'd0) &&
                (data[159:128] == object_id) && (object_id != NO_ID) &&
                (data[191:160] == NO_ID) &&
                (data[223:192] == NO_ID) &&
                (data[255:224] == NO_ID) &&
                (data[287:256] == permissions) &&
                (data[319:288] == 32'd0) &&
                (data[519:512] == dtype) &&
                (data[527:520] == rank) &&
                (data[535:528] == 8'd0) &&
                (data[543:536] == terms) &&
                (data[575:544] == NO_ID) &&
                (data[607:576] == 32'd0) &&
                (data[639:608] == NO_ID);
        end
    endfunction

    function automatic index_view_ok;
        input [1535:0] data;
        input [31:0] object_id;
        begin
            index_view_ok = view_header_ok(
                data, object_id, 32'd1, FMT_U32, 8'd1, 8'd2
            ) &&
                (data[703:640] == 64'd0) &&
                (data[735:704] == TOKEN_BLOCK) &&
                (data[895:736] == 160'd0) &&
                (data[927:896] == 32'd1) &&
                (data[1087:928] == 160'd0) &&
                (data[1103:1088] == 16'd1) &&
                (data[1119:1104] == 16'd1) &&
                (data[1151:1120] == 32'd1) &&
                (data[1167:1152] == 16'd0) &&
                (data[1183:1168] != 16'hffff) &&
                (data[1215:1184] == TOKEN_BLOCK) &&
                (data[1535:1216] == 320'd0);
        end
    endfunction

    function automatic kv_source_view_ok;
        input [1535:0] data;
        input [31:0] object_id;
        input [15:0] loop_id;
        begin
            kv_source_view_ok = view_header_ok(
                data, object_id, 32'd1, FMT_BF16, 8'd3, 8'd1
            ) &&
                (data[703:640] == 64'd0) &&
                (data[735:704] == TOKEN_BLOCK) &&
                (data[767:736] == KV_HEADS) &&
                (data[799:768] == HEAD_WIDTH) &&
                (data[895:800] == 96'd0) &&
                (data[927:896] == KV_PLANE_WORDS) &&
                (data[959:928] == HEAD_WIDTH) &&
                (data[991:960] == 32'd1) &&
                (data[1087:992] == 96'd0) &&
                (data[1103:1088] == 16'd0) &&
                (data[1119:1104] == loop_id) &&
                (data[1151:1120] == 32'd524288) &&
                (data[1535:1152] == 384'd0);
        end
    endfunction

    function automatic kv_cache_view_ok;
        input [1535:0] data;
        input [31:0] object_id;
        input [31:0] permissions;
        input [63:0] plane_offset;
        begin
            kv_cache_view_ok = view_header_ok(
                data, object_id, permissions, FMT_BF16, 8'd3, 8'd1
            ) &&
                (data[703:640] == plane_offset) &&
                (data[735:704] == CACHE_ROWS) &&
                (data[767:736] == KV_HEADS) &&
                (data[799:768] == HEAD_WIDTH) &&
                (data[895:800] == 96'd0) &&
                (data[927:896] == KV_ROW_STRIDE) &&
                (data[959:928] == HEAD_WIDTH) &&
                (data[991:960] == 32'd1) &&
                (data[1087:992] == 96'd0) &&
                (data[1103:1088] == 16'd0) &&
                (data[1119:1104] != 16'hffff) &&
                (data[1151:1120] == 32'd16908288) &&
                (data[1535:1152] == 384'd0);
        end
    endfunction

    function automatic query_view_ok;
        input [1535:0] data;
        input [31:0] object_id;
        input [31:0] permissions;
        begin
            query_view_ok = view_header_ok(
                data, object_id, permissions, FMT_BF16, 8'd3, 8'd1
            ) &&
                (data[703:640] == 64'd0) &&
                (data[735:704] == TOKEN_BLOCK) &&
                (data[767:736] == QUERY_HEADS) &&
                (data[799:768] == HEAD_WIDTH) &&
                (data[895:800] == 96'd0) &&
                (data[927:896] == 32'd4096) &&
                (data[959:928] == HEAD_WIDTH) &&
                (data[991:960] == 32'd1) &&
                (data[1087:992] == 96'd0) &&
                (data[1103:1088] == 16'd0) &&
                (data[1119:1104] != 16'hffff) &&
                (data[1151:1120] == 32'd2097152) &&
                (data[1535:1152] == 384'd0);
        end
    endfunction

    function automatic numeric_header_ok;
        input [1535:0] data;
        begin
            numeric_header_ok =
                (data[127:96] == 32'd0) &&
                (data[159:128] == NO_ID) &&
                (data[191:160] == NO_ID) &&
                (data[223:192] == NO_ID) &&
                (data[255:224] == NO_ID) &&
                (data[287:256] == 32'd129) &&
                (data[319:288] == 32'd0);
        end
    endfunction

    wire numeric_controls_zero =
        (numeric_record_q[559:544] == 16'd0) &&
        (numeric_record_q[575:560] == 16'd0) &&
        (numeric_record_q[607:576] == 32'd0) &&
        (numeric_record_q[671:640] == 32'd0) &&
        (numeric_record_q[767:672] == 96'd0);
    wire scatter_dtype_order_ok =
        ((numeric_record_q[519:512] == FMT_BF16) &&
         (numeric_record_q[527:520] == FMT_U32)) ||
        ((numeric_record_q[519:512] == FMT_U32) &&
         (numeric_record_q[527:520] == FMT_BF16));
    wire scatter_numeric_ok = numeric_header_ok(numeric_record_q) &&
        scatter_dtype_order_ok &&
        (numeric_record_q[535:528] == FMT_FP32) &&
        (numeric_record_q[543:536] == FMT_BF16) &&
        numeric_controls_zero &&
        (numeric_record_q[639:608] == 32'd0) &&
        (numeric_record_q[1023:768] == CONTRACT_KV_SCATTER_RAW);
    wire gqa_numeric_ok = numeric_header_ok(numeric_record_q) &&
        (numeric_record_q[519:512] == FMT_BF16) &&
        (numeric_record_q[527:520] == FMT_BF16) &&
        (numeric_record_q[535:528] == FMT_FP32) &&
        (numeric_record_q[543:536] == FMT_BF16) &&
        (numeric_record_q[559:544] == 16'd0) &&
        (numeric_record_q[575:560] == 16'd0) &&
        (numeric_record_q[607:576] == 32'd0) &&
        (numeric_record_q[639:608] == GQA_SCALE_BITS) &&
        (numeric_record_q[767:640] == 128'd0) &&
        (numeric_record_q[1023:768] == CONTRACT_GQA_RAW);

    wire operator_header_ok =
        (operator_record_q[127:96] == 32'd0) &&
        (operator_record_q[159:128] == NO_ID) &&
        (operator_record_q[191:160] == NO_ID) &&
        (operator_record_q[223:192] == numeric_id_q) &&
        (operator_record_q[255:224] == operator_record_q[703:672]) &&
        (operator_record_q[703:672] != NO_ID) &&
        (operator_record_q[287:256] == 32'd5) &&
        (operator_record_q[319:288] == 32'd0);
    wire operator_identity_ok =
        (instruction_descriptor_q == operator_id_q) &&
        (operator_record_q[519:512] == instruction_major_q) &&
        (operator_record_q[527:520] == instruction_sub_q) &&
        (operator_record_q[543:528] == 16'd0) &&
        (operator_record_q[575:544] == NO_ID) &&
        (operator_record_q[607:576] == instruction_source_q) &&
        (operator_record_q[639:608] != NO_ID) &&
        (operator_record_q[671:640] == numeric_id_q);

    // The context the request declares must be an expressible length and
    // must be the index view's own position plus one.  Neither alone.
    wire context_bound_ok =
        (context_q >= MIN_CONTEXT) && (context_q <= MAX_CONTEXT) &&
        (context_q <= CACHE_ROWS);

    wire scatter_pc_ok =
        (((instruction_index_q == 32'd32) &&
          (instruction_source_q == 32'd11) &&
          (instruction_signal_q == 32'd10) &&
          (output_record_q[703:640] == 64'd0)) ||
         ((instruction_index_q == 32'd35) &&
          (instruction_source_q == 32'd12) &&
          (instruction_signal_q == 32'd11) &&
          (output_record_q[703:640] == 64'd1024)));
    wire instruction_common_ok =
        (instruction_count_q == 32'd74) &&
        (instruction_flags_q == 16'd12) &&
        (instruction_predicate_q == NO_ID) &&
        (instruction_wait_q != NO_ID) &&
        (instruction_control_q == NO_ID);
    wire scatter_operator_ok = operator_header_ok && operator_identity_ok &&
        (operator_record_q[735:704] == view0_id_q) &&
        (operator_record_q[767:736] == view1_id_q) &&
        (operator_record_q[831:768] == {2{NO_ID}}) &&
        (operator_record_q[863:832] == output_id_q) &&
        (operator_record_q[895:864] == NO_ID) &&
        (operator_record_q[1023:896] == {4{NO_ID}});
    wire scatter_views_ok = index_view_ok(view0_record_q, object0_q) &&
        kv_source_view_ok(
            view1_record_q, object1_q, view0_record_q[1183:1168]
        ) &&
        kv_cache_view_ok(
            output_record_q, output_object_q, 32'd3,
            (instruction_index_q == 32'd32) ? 64'd0 : 64'd1024
        );
    wire scatter_semantics_ok = instruction_common_ok && scatter_pc_ok &&
        (instruction_major_q == FAMILY_DMA) &&
        (instruction_sub_q == DMA_SCATTER) &&
        scatter_operator_ok && scatter_views_ok && scatter_numeric_ok &&
        context_bound_ok && (context_q == position_q + 32'd1) &&
        (view2_id_q == NO_ID) && (view3_id_q == NO_ID) &&
        (object2_q == NO_ID) && (object3_q == NO_ID);

    wire gqa_instruction_ok = instruction_common_ok &&
        (instruction_index_q == 32'd38) &&
        (instruction_major_q == FAMILY_ATTENTION) &&
        (instruction_sub_q == ATTENTION_GQA) &&
        (instruction_source_q == 32'd13) &&
        (instruction_signal_q == 32'd12);
    wire gqa_operator_ok = operator_header_ok && operator_identity_ok &&
        (operator_record_q[735:704] == view0_id_q) &&
        (operator_record_q[767:736] == view1_id_q) &&
        (operator_record_q[799:768] == view2_id_q) &&
        (operator_record_q[831:800] == view3_id_q) &&
        (operator_record_q[863:832] == output_id_q) &&
        (operator_record_q[895:864] == NO_ID) &&
        (operator_record_q[927:896] == 32'd4) &&
        (operator_record_q[959:928] == 32'd0) &&
        (operator_record_q[991:960] == 32'd3) &&
        (operator_record_q[1023:992] == 32'd1);
    wire gqa_k_permissions_ok =
        (view1_record_q[287:256] == 32'd1) ||
        (view1_record_q[287:256] == 32'd3);
    wire gqa_v_permissions_ok =
        (view2_record_q[287:256] == 32'd1) ||
        (view2_record_q[287:256] == 32'd3);
    wire gqa_views_ok =
        query_view_ok(view0_record_q, object0_q, 32'd1) &&
        gqa_k_permissions_ok &&
        kv_cache_view_ok(
            view1_record_q, object1_q, view1_record_q[287:256], 64'd0
        ) &&
        gqa_v_permissions_ok &&
        kv_cache_view_ok(
            view2_record_q, object2_q, view2_record_q[287:256], 64'd1024
        ) &&
        index_view_ok(view3_record_q, object3_q) &&
        query_view_ok(output_record_q, output_object_q, 32'd3) &&
        (view0_record_q[1119:1104] == output_record_q[1119:1104]) &&
        (view1_record_q[1119:1104] == view2_record_q[1119:1104]) &&
        (object1_q == object2_q);
    wire gqa_semantics_ok = gqa_instruction_ok && gqa_operator_ok &&
        gqa_views_ok && gqa_numeric_ok &&
        context_bound_ok && (context_q == position_q + 32'd1);

    wire mover_idx_rd_en;
    wire [31:0] mover_idx_rd_addr;
    wire mover_src_rd_en;
    wire [31:0] mover_src_rd_addr;
    wire mover_out_we;
    wire [31:0] mover_out_addr;
    wire [31:0] mover_out_data;
    wire mover_busy;
    wire mover_done;
    wire [7:0] mover_error;
    wire [31:0] mover_moved;
    wire [31:0] mover_checked;

    assign idx_rd_en = (state == S_INDEX_ISSUE) || mover_idx_rd_en;
    assign idx_rd_addr = (state == S_INDEX_ISSUE)
        ? index_base_q : mover_idx_rd_addr;
    assign src_rd_en = mover_src_rd_en;
    assign src_rd_addr = mover_src_rd_addr;
    assign out_we = mover_out_we;
    assign out_addr = mover_out_addr;
    assign out_data = mover_out_data;

    ot_a3_dma_index_mover mover (
        .clk(clk), .rst_n(rst_n),
        .start(state == S_MOVER_START),
        .cfg_scatter(1'b1),
        .cfg_slots(32'd1),
        .cfg_trailing(KV_PLANE_WORDS),
        .cfg_rows(context_q),
        .cfg_index_base(index_base_q),
        .cfg_source_base(source_base_q),
        .cfg_prior_base(prior_base_q),
        .cfg_out_base(output_base_q),
        .idx_rd_en(mover_idx_rd_en),
        .idx_rd_addr(mover_idx_rd_addr),
        .idx_rd_data(idx_rd_data),
        .src_rd_en(mover_src_rd_en),
        .src_rd_addr(mover_src_rd_addr),
        .src_rd_data(src_rd_data),
        .out_we(mover_out_we),
        .out_addr(mover_out_addr),
        .out_data(mover_out_data),
        .busy(mover_busy), .done(mover_done),
        .error_code(mover_error),
        .moved_elements(mover_moved),
        .indices_checked(mover_checked)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            scatter_q <= 1'b0;
            gqa_q <= 1'b0;
            record_slot <= 3'd0;
            record_count <= 3'd0;
            instruction_record_q <= 256'd0;
            instruction_index_q <= 32'd0;
            instruction_count_q <= 32'd0;
            operator_id_q <= NO_ID;
            view0_id_q <= NO_ID;
            view1_id_q <= NO_ID;
            view2_id_q <= NO_ID;
            view3_id_q <= NO_ID;
            output_id_q <= NO_ID;
            numeric_id_q <= NO_ID;
            object0_q <= NO_ID;
            object1_q <= NO_ID;
            object2_q <= NO_ID;
            object3_q <= NO_ID;
            output_object_q <= NO_ID;
            operator_record_q <= 1536'd0;
            view0_record_q <= 1536'd0;
            view1_record_q <= 1536'd0;
            view2_record_q <= 1536'd0;
            view3_record_q <= 1536'd0;
            output_record_q <= 1536'd0;
            numeric_record_q <= 1536'd0;
            position_q <= 32'd0;
            context_q <= 32'd0;
            index_base_q <= 32'd0;
            source_base_q <= 32'd0;
            prior_base_q <= 32'd0;
            output_base_q <= 32'd0;
            instruction_major_q <= 8'd0;
            instruction_sub_q <= 8'd0;
            instruction_flags_q <= 16'd0;
            instruction_predicate_q <= NO_ID;
            instruction_descriptor_q <= NO_ID;
            instruction_wait_q <= NO_ID;
            instruction_signal_q <= NO_ID;
            instruction_control_q <= NO_ID;
            instruction_source_q <= NO_ID;
            busy <= 1'b0;
            done <= 1'b0;
            failed <= 1'b0;
            trap_class <= TRAP_NONE;
            refusal_reason <= REFUSAL_NONE;
            records_checked <= 32'd0;
            moved_elements <= 32'd0;
            indices_checked <= 32'd0;
            write_count <= 32'd0;
            gqa_boundary <= 1'b0;
        end else begin
            done <= 1'b0;
            if (mover_out_we)
                write_count <= write_count + 32'd1;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        instruction_record_q <= instruction_record;
                        instruction_index_q <= instruction_index;
                        instruction_count_q <= instruction_count;
                        operator_id_q <= operator_descriptor_id;
                        view0_id_q <= view0_descriptor_id;
                        view1_id_q <= view1_descriptor_id;
                        view2_id_q <= view2_descriptor_id;
                        view3_id_q <= view3_descriptor_id;
                        output_id_q <= output_descriptor_id;
                        numeric_id_q <= numeric_descriptor_id;
                        object0_q <= expected_object0;
                        object1_q <= expected_object1;
                        object2_q <= expected_object2;
                        object3_q <= expected_object3;
                        output_object_q <= expected_output_object;
                        operator_record_q <= operator_record;
                        view0_record_q <= view0_record;
                        view1_record_q <= view1_record;
                        view2_record_q <= view2_record;
                        view3_record_q <= view3_record;
                        output_record_q <= output_record;
                        numeric_record_q <= numeric_record;
                        position_q <= cfg_position_start;
                        context_q <= cfg_context_length;
                        index_base_q <= cfg_index_base;
                        source_base_q <= cfg_source_base;
                        prior_base_q <= cfg_prior_base;
                        output_base_q <= cfg_output_base;
                        scatter_q <= 1'b0;
                        gqa_q <= 1'b0;
                        record_slot <= 3'd0;
                        record_count <= 3'd0;
                        busy <= 1'b1;
                        failed <= 1'b0;
                        trap_class <= TRAP_NONE;
                        refusal_reason <= REFUSAL_NONE;
                        records_checked <= 32'd0;
                        moved_elements <= 32'd0;
                        indices_checked <= 32'd0;
                        write_count <= 32'd0;
                        gqa_boundary <= 1'b0;
                        state <= S_DECODE_START;
                    end
                end

                S_DECODE_START: begin
                    if (decoder_in_ready)
                        state <= S_DECODE_WAIT;
                end

                S_DECODE_WAIT: begin
                    if (decoder_out_valid) begin
                        instruction_major_q <= decoder_out_major;
                        instruction_sub_q <= decoder_out_sub;
                        instruction_flags_q <= decoder_out_flags;
                        instruction_predicate_q <= decoder_out_predicate;
                        instruction_descriptor_q <= decoder_out_descriptor;
                        instruction_wait_q <= decoder_out_wait;
                        instruction_signal_q <= decoder_out_signal;
                        instruction_control_q <= decoder_out_control;
                        instruction_source_q <= decoder_out_source;
                        if (!decoder_out_legal) begin
                            failed <= 1'b1;
                            trap_class <= decoder_out_trap;
                            refusal_reason <=
                                (decoder_out_error == 4'd1)
                                ? REFUSAL_INTEGRITY : REFUSAL_INSTRUCTION;
                            state <= S_FINISH;
                        end else if ((decoder_out_major == FAMILY_DMA) &&
                                     (decoder_out_sub == DMA_SCATTER)) begin
                            scatter_q <= 1'b1;
                            gqa_q <= 1'b0;
                            record_count <= 3'd5;
                            record_slot <= 3'd0;
                            state <= S_RECORD_START;
                        end else if ((decoder_out_major == FAMILY_ATTENTION) &&
                                     (decoder_out_sub == ATTENTION_GQA)) begin
                            scatter_q <= 1'b0;
                            gqa_q <= 1'b1;
                            record_count <= 3'd7;
                            record_slot <= 3'd0;
                            state <= S_RECORD_START;
                        end else begin
                            failed <= 1'b1;
                            trap_class <= TRAP_CAPABILITY;
                            refusal_reason <= REFUSAL_CAPABILITY;
                            state <= S_FINISH;
                        end
                    end
                end

                S_RECORD_START: state <= S_RECORD_WAIT;

                S_RECORD_WAIT: begin
                    if (record_done) begin
                        if (!record_legal) begin
                            failed <= 1'b1;
                            trap_class <= (record_error == 8'd1)
                                ? TRAP_INTEGRITY : TRAP_DESCRIPTOR;
                            refusal_reason <= (record_error == 8'd1)
                                ? REFUSAL_INTEGRITY : REFUSAL_DESCRIPTOR;
                            state <= S_FINISH;
                        end else begin
                            records_checked <= records_checked + 32'd1;
                            if (record_slot + 3'd1 == record_count)
                                state <= S_ADMIT;
                            else begin
                                record_slot <= record_slot + 3'd1;
                                state <= S_RECORD_START;
                            end
                        end
                    end
                end

                S_ADMIT: begin
                    if ((scatter_q && !scatter_semantics_ok) ||
                        (gqa_q && !gqa_semantics_ok)) begin
                        failed <= 1'b1;
                        trap_class <= TRAP_DESCRIPTOR;
                        refusal_reason <= REFUSAL_DESCRIPTOR;
                        state <= S_FINISH;
                    end else if (gqa_q) begin
                        failed <= 1'b1;
                        trap_class <= TRAP_CAPABILITY;
                        refusal_reason <= REFUSAL_CAPABILITY;
                        gqa_boundary <= 1'b1;
                        state <= S_FINISH;
                    end else begin
                        state <= S_INDEX_ISSUE;
                    end
                end

                S_INDEX_ISSUE: state <= S_INDEX_WAIT;

                S_INDEX_WAIT: begin
                    indices_checked <= 32'd1;
                    if ((idx_rd_data != position_q) ||
                        (idx_rd_data >= context_q)) begin
                        failed <= 1'b1;
                        trap_class <= TRAP_ENGINE;
                        refusal_reason <= REFUSAL_ENGINE;
                        state <= S_FINISH;
                    end else begin
                        state <= S_MOVER_START;
                    end
                end

                S_MOVER_START: state <= S_MOVER_WAIT;

                S_MOVER_WAIT: begin
                    if (mover_done) begin
                        moved_elements <= mover_moved;
                        indices_checked <= mover_checked;
                        if ((mover_error != ERR_NONE) ||
                            (mover_moved != KV_PLANE_WORDS) ||
                            (mover_checked != 32'd1)) begin
                            failed <= 1'b1;
                            trap_class <= TRAP_ENGINE;
                            refusal_reason <= REFUSAL_ENGINE;
                        end
                        state <= S_FINISH;
                    end
                end

                S_FINISH: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end

                default: begin
                    failed <= 1'b1;
                    trap_class <= TRAP_ENGINE;
                    refusal_reason <= REFUSAL_ENGINE;
                    state <= S_FINISH;
                end
            endcase
        end
    end
endmodule
