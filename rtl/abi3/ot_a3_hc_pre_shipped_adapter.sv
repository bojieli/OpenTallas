`timescale 1ns/1ps
// Shipped ABI 3.0 adapter for the exact one-token DeepSeek HC_PRE boundary.
//
// The adapter consumes the issue metadata actually latched by
// ot_a3_microsequencer and all six observations actually emitted by its
// ot_a3_view_resolver.  It then rereads the immutable raw descriptor records
// through an independent descriptor-store port, validates each CRC/header and
// the production semantics not represented in the compact scheduler record,
// and constructs that record solely from those decoded sources.
//
// Base, scale, hidden and projection data all use one ready/valid request and
// response path.  The hidden/projection arithmetic itself is handshake-native;
// this is not a pulse adapter around a fixed-latency engine.  Successful
// arithmetic is held privately before 24 backpressured word commits.  No
// descriptor, view, read, or arithmetic failure can publish a partial result;
// once word publication begins there are no remaining fallible operations.
// Completion is returned to the sequencer only after the twenty-fourth write
// commits.  This block does not produce a model token or a TPOT measurement.
module ot_a3_hc_pre_shipped_adapter #(
    parameter integer CONFIG_WORDS = 128
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         clear,

    input  wire                         issue_valid,
    output wire                         issue_ready,
    output wire                         issue_fault,
    output wire [15:0]                  issue_trap_class,
    input  wire [7:0]                   issue_family,
    input  wire [7:0]                   issue_sub,
    input  wire [31:0]                  issue_descriptor_id,
    input  wire [31:0]                  issue_index,
    input  wire [15:0]                  issue_flags,
    input  wire [31:0]                  issue_wait_set_id,
    input  wire [31:0]                  issue_signal_event_id,
    input  wire [31:0]                  issue_control_id,
    input  wire [31:0]                  issue_source_operation_id,

    input  wire                         view_valid,
    input  wire [31:0]                  view_descriptor_id,
    input  wire [2:0]                   view_slot,
    input  wire [31:0]                  view_extent,
    input  wire [7:0]                   view_extent_axis,
    input  wire [63:0]                  view_element_offset,
    input  wire [7:0]                   view_rank,

    output wire                         desc_req,
    output wire [31:0]                  desc_id,
    input  wire                         desc_valid,
    input  wire                         desc_fault,
    input  wire [1535:0]                desc_data,

    output reg                          mem_read_valid,
    input  wire                         mem_read_ready,
    output reg  [31:0]                  mem_read_object_id,
    output reg  [63:0]                  mem_read_element_offset,
    output reg  [7:0]                   mem_read_dtype,
    output reg  [4:0]                   mem_read_element_count,
    output reg  [31:0]                  mem_read_element_stride,
    input  wire                         mem_response_valid,
    output reg                          mem_response_ready,
    input  wire [255:0]                 mem_response_data,
    input  wire                         mem_response_error,

    output wire                         mem_write_valid,
    input  wire                         mem_write_ready,
    output wire [31:0]                  mem_write_object_id,
    output wire [63:0]                  mem_write_element_offset,
    output wire [31:0]                  mem_write_data,

    output wire                         busy,
    output reg  [31:0]                  descriptor_records_checked,
    output reg  [31:0]                  resolved_views_captured,
    output reg  [31:0]                  memory_read_count,
    output reg  [31:0]                  memory_request_stall_cycles,
    output reg  [31:0]                  memory_response_stall_cycles,
    output reg  [31:0]                  output_write_count,
    output reg  [31:0]                  output_write_stall_cycles,
    output reg                          arithmetic_executed,
    output reg  [7:0]                   last_error_code,
    output wire [31:0]                  arithmetic_square_count,
    output wire [31:0]                  arithmetic_reduction_add_count,
    output wire [31:0]                  arithmetic_fma_count
);
    localparam [31:0] NO_ID = 32'hffff_ffff;
    localparam [15:0] DESC_TENSOR_VIEW = 16'h0002;
    localparam [15:0] DESC_NUMERIC = 16'h0003;
    localparam [15:0] DESC_SCHEDULE = 16'h0004;
    localparam [15:0] DESC_WAIT_SET = 16'h0008;
    localparam [15:0] DESC_OPERATOR = 16'h000a;
    localparam [15:0] DESC_COUNTER = 16'h000c;
    localparam [15:0] TRAP_NONE = 16'd0;
    localparam [15:0] TRAP_DESCRIPTOR = 16'd3;
    localparam [15:0] TRAP_CAPABILITY = 16'd4;
    localparam [15:0] TRAP_NUMERIC = 16'd6;
    localparam [15:0] TRAP_ENGINE = 16'd8;
    localparam [7:0] FAMILY_VECTOR = 8'h30;
    localparam [7:0] VECTOR_MHC = 8'h09;
    localparam [7:0] DTYPE_BF16 = 8'h10;
    localparam [7:0] DTYPE_FP32 = 8'h12;

    localparam [7:0] ERR_NONE = 8'd0;
    localparam [7:0] ERR_INSTRUCTION = 8'd1;
    localparam [7:0] ERR_VIEW_OBSERVATION = 8'd2;
    localparam [7:0] ERR_DESCRIPTOR_READ = 8'd3;
    localparam [7:0] ERR_DESCRIPTOR_INTEGRITY = 8'd4;
    localparam [7:0] ERR_DESCRIPTOR_SEMANTICS = 8'd5;
    localparam [7:0] ERR_MEMORY_READ = 8'd6;
    localparam [7:0] ERR_ARITHMETIC = 8'd7;

    localparam [3:0] S_IDLE = 4'd0;
    localparam [3:0] S_DESC_REQ = 4'd1;
    localparam [3:0] S_DESC_WAIT = 4'd2;
    localparam [3:0] S_VALIDATE_START = 4'd3;
    localparam [3:0] S_VALIDATE_WAIT = 4'd4;
    localparam [3:0] S_PRECHECK = 4'd5;
    localparam [3:0] S_BASE_REQ = 4'd6;
    localparam [3:0] S_BASE_RSP = 4'd7;
    localparam [3:0] S_SCALE_REQ = 4'd8;
    localparam [3:0] S_SCALE_RSP = 4'd9;
    localparam [3:0] S_ENGINE_START = 4'd10;
    localparam [3:0] S_ENGINE_WAIT = 4'd11;
    localparam [3:0] S_WRITE = 4'd12;
    localparam [3:0] S_RESPONSE = 4'd13;

    localparam [1:0] PROFILE_ROM = 2'd0;
    localparam [1:0] PROFILE_HBM = 2'd1;

    reg [3:0] state;
    reg [1:0] profile_q;
    reg response_fault_q;
    reg [15:0] response_trap_q;
    reg [3:0] descriptor_index;
    reg [1535:0] descriptor_record_q;
    reg [31:0] operator_counter_id;
    reg [31:0] operator_numeric_id;
    reg [31:0] operator_schedule_id;
    reg [31:0] operator_view_id [0:5];
    reg [CONFIG_WORDS*32-1:0] config_q;
    reg [767:0] base_codes_q;
    reg [95:0] scale_codes_q;
    reg [4:0] parameter_index;
    reg [255:0] result_weights_q;
    reg [511:0] result_combination_q;
    reg [4:0] write_index;

    reg [5:0] observed_valid;
    reg [31:0] observed_id [0:5];
    reg [31:0] observed_extent [0:5];
    reg [7:0] observed_axis [0:5];
    reg [63:0] observed_offset [0:5];
    reg [7:0] observed_rank [0:5];
    reg [5:0] issued_observed_valid;
    reg [31:0] issued_observed_id [0:5];
    reg [31:0] issued_observed_extent [0:5];
    reg [7:0] issued_observed_axis [0:5];
    reg [63:0] issued_observed_offset [0:5];
    reg [7:0] issued_observed_rank [0:5];

    reg engine_memory_pending;
    reg engine_memory_owner;
    integer item;
    integer semantic_item;
    integer view_item;

    function automatic [31:0] cfg;
        input [CONFIG_WORDS*32-1:0] words;
        input integer index;
        begin
            cfg = words[index*32 +: 32];
        end
    endfunction

    function automatic [31:0] view_cfg;
        input [CONFIG_WORDS*32-1:0] words;
        input integer slot;
        input integer field;
        begin
            view_cfg = cfg(words, 64 + slot*10 + field);
        end
    endfunction

    function automatic [31:0] expected_loop_id;
        input [1:0] profile;
        input integer slot;
        begin
            if (profile == PROFILE_ROM)
                expected_loop_id = (slot == 0 || slot >= 4)
                    ? 32'd369 : 32'd324;
            else
                expected_loop_id = (slot == 0 || slot >= 4)
                    ? 32'd536 : 32'd534;
        end
    endfunction

    function automatic [31:0] expected_dynamic_stride;
        input [1:0] profile;
        input integer slot;
        begin
            case (slot)
                0: expected_dynamic_stride = profile == PROFILE_ROM
                    ? 32'h8000_0000 : 32'd8388608;
                1: expected_dynamic_stride = 32'd393216;
                2: expected_dynamic_stride = 32'd24;
                3: expected_dynamic_stride = 32'd3;
                4: expected_dynamic_stride = profile == PROFILE_ROM
                    ? 32'd1048576 : 32'd4096;
                default: expected_dynamic_stride = profile == PROFILE_ROM
                    ? 32'd2097152 : 32'd8192;
            endcase
        end
    endfunction

    wire issue_is_rom =
        (issue_family == FAMILY_VECTOR) && (issue_sub == VECTOR_MHC) &&
        (issue_index == 32'd15) && (issue_descriptor_id == 32'd381);
    wire issue_is_hbm =
        (issue_family == FAMILY_VECTOR) && (issue_sub == VECTOR_MHC) &&
        (issue_index == 32'd14) && (issue_descriptor_id == 32'd545);

    reg [31:0] selected_descriptor_id;
    reg [15:0] selected_descriptor_type;
    reg [31:0] selected_total_bytes;
    reg [31:0] selected_payload_bytes;
    always @* begin
        selected_descriptor_id = issue_descriptor_id;
        selected_descriptor_type = DESC_OPERATOR;
        selected_total_bytes = 32'd128;
        selected_payload_bytes = 32'd64;
        case (descriptor_index)
            0: begin
                selected_descriptor_id = issue_descriptor_id;
                selected_descriptor_type = DESC_OPERATOR;
            end
            1: begin
                selected_descriptor_id = issue_wait_set_id;
                selected_descriptor_type = DESC_WAIT_SET;
            end
            2: begin
                selected_descriptor_id = operator_counter_id;
                selected_descriptor_type = DESC_COUNTER;
            end
            3: begin
                selected_descriptor_id = operator_numeric_id;
                selected_descriptor_type = DESC_NUMERIC;
            end
            4: begin
                selected_descriptor_id = operator_schedule_id;
                selected_descriptor_type = DESC_SCHEDULE;
            end
            5, 6, 7, 8, 9, 10: begin
                selected_descriptor_id = operator_view_id[descriptor_index-5];
                selected_descriptor_type = DESC_TENSOR_VIEW;
                selected_total_bytes = 32'd192;
                selected_payload_bytes = 32'd128;
            end
            default: begin
                selected_descriptor_id = NO_ID;
                selected_descriptor_type = 16'hffff;
                selected_total_bytes = 0;
                selected_payload_bytes = 0;
            end
        endcase
    end

    assign desc_req = state == S_DESC_REQ;
    assign desc_id = selected_descriptor_id;

    wire validator_busy;
    wire validator_done;
    wire validator_legal;
    wire [7:0] validator_error;
    ot_a3_descriptor_record_validator descriptor_validator (
        .clk(clk), .rst_n(rst_n), .start(state == S_VALIDATE_START),
        .record(descriptor_record_q),
        .expected_type(selected_descriptor_type),
        .expected_total_bytes(selected_total_bytes),
        .expected_payload_bytes(selected_payload_bytes),
        .busy(validator_busy), .done(validator_done),
        .legal(validator_legal), .error_code(validator_error)
    );

    // Semantic checks omitted by the common CRC/header validator.  The exact
    // numerical and geometry fields are also checked by the scheduler after
    // they have been reconstructed into config_q.
    reg current_record_semantic_ok;
    reg metadata_header_ok;
    reg view_header_ok;
    integer current_view_slot;
    always @* begin
        metadata_header_ok =
            (descriptor_record_q[127:96] == 0) &&
            (descriptor_record_q[159:128] == NO_ID) &&
            (descriptor_record_q[191:160] == NO_ID) &&
            (descriptor_record_q[223:192] == NO_ID) &&
            (descriptor_record_q[255:224] == NO_ID) &&
            (descriptor_record_q[287:256] == 32'd129) &&
            (descriptor_record_q[319:288] == 0);
        view_header_ok =
            (descriptor_record_q[127:96] == 0) &&
            (descriptor_record_q[191:160] == NO_ID) &&
            (descriptor_record_q[223:192] == NO_ID) &&
            (descriptor_record_q[255:224] == NO_ID) &&
            (descriptor_record_q[319:288] == 0);
        current_record_semantic_ok = 1'b1;
        current_view_slot = descriptor_index - 5;
        case (descriptor_index)
            0: begin
                current_record_semantic_ok =
                    (descriptor_record_q[127:96] == 0) &&
                    (descriptor_record_q[159:128] == NO_ID) &&
                    (descriptor_record_q[191:160] == NO_ID) &&
                    (descriptor_record_q[223:192] ==
                     descriptor_record_q[671:640]) &&
                    (descriptor_record_q[255:224] ==
                     descriptor_record_q[703:672]) &&
                    (descriptor_record_q[287:256] == 32'd5) &&
                    (descriptor_record_q[319:288] == 0);
            end
            1: begin
                current_record_semantic_ok = metadata_header_ok &&
                    (descriptor_record_q[519:512] == 0) &&
                    (descriptor_record_q[527:520] == 1) &&
                    (descriptor_record_q[535:528] == 0) &&
                    (descriptor_record_q[543:536] == 1) &&
                    (descriptor_record_q[575:544] == 1) &&
                    (descriptor_record_q[607:576] == 32'd3) &&
                    (descriptor_record_q[991:960] == 32'd1) &&
                    (descriptor_record_q[1023:992] == 0);
                for (semantic_item = 1; semantic_item < 12;
                     semantic_item = semantic_item + 1)
                    if (descriptor_record_q[576 + semantic_item*32 +: 32]
                        != NO_ID)
                        current_record_semantic_ok = 1'b0;
            end
            2: begin
                current_record_semantic_ok = metadata_header_ok &&
                    (descriptor_record_q[575:528] == 0) &&
                    (descriptor_record_q[1023:960] == 0);
                for (semantic_item = 3; semantic_item < 12;
                     semantic_item = semantic_item + 1)
                    if (descriptor_record_q[576 + semantic_item*32 +: 32]
                        != NO_ID)
                        current_record_semantic_ok = 1'b0;
            end
            3: begin
                current_record_semantic_ok = metadata_header_ok &&
                    (descriptor_record_q[703:672] == 0) &&
                    (descriptor_record_q[767:704] == 0);
            end
            4: begin
                current_record_semantic_ok = metadata_header_ok &&
                    (descriptor_record_q[1023:832] == 0);
            end
            5, 6, 7, 8, 9, 10: begin
                current_record_semantic_ok = view_header_ok &&
                    (descriptor_record_q[287:256] ==
                        (current_view_slot < 4 ? 32'd1 : 32'd3)) &&
                    (descriptor_record_q[535:528] == 0) &&
                    (descriptor_record_q[543:536] == 1) &&
                    (descriptor_record_q[575:544] == NO_ID) &&
                    (descriptor_record_q[607:576] == 0) &&
                    (descriptor_record_q[639:608] == NO_ID) &&
                    (descriptor_record_q[703:640] == 0) &&
                    (descriptor_record_q[895:800] == 0) &&
                    (descriptor_record_q[1087:992] == 0) &&
                    (descriptor_record_q[1103:1088] == 0) &&
                    ({16'd0, descriptor_record_q[1119:1104]} ==
                        expected_loop_id(profile_q, current_view_slot)) &&
                    (descriptor_record_q[1151:1120] ==
                        expected_dynamic_stride(profile_q, current_view_slot)) &&
                    (descriptor_record_q[1343:1152] == 0) &&
                    (descriptor_record_q[1535:1344] == 0);
            end
            default: current_record_semantic_ok = 1'b0;
        endcase
    end

    reg resolved_views_match;
    reg [31:0] expected_resolved_extent;
    always @* begin
        resolved_views_match = issued_observed_valid == 6'h3f;
        expected_resolved_extent = 0;
        for (view_item = 0; view_item < 6; view_item = view_item + 1) begin
            expected_resolved_extent =
                (view_item == 0 || view_item >= 4)
                ? 32'd1 : view_cfg(config_q, view_item, 4);
            if ((issued_observed_id[view_item] !=
                 operator_view_id[view_item]) ||
                (issued_observed_extent[view_item] !=
                 expected_resolved_extent) ||
                (issued_observed_axis[view_item] != 0) ||
                (issued_observed_offset[view_item] != 0) ||
                ({24'd0, issued_observed_rank[view_item]} !=
                 view_cfg(config_q, view_item, 3)))
                resolved_views_match = 1'b0;
        end
    end

    // Arithmetic-side request/response channels.
    wire engine_in_ready;
    wire engine_hidden_req_valid;
    wire engine_hidden_req_ready;
    wire [13:0] engine_hidden_req_k;
    wire engine_hidden_rsp_valid;
    wire engine_hidden_rsp_ready;
    wire [15:0] engine_hidden_rsp_data;
    wire engine_hidden_rsp_error;
    wire engine_weight_req_valid;
    wire engine_weight_req_ready;
    wire [4:0] engine_weight_req_field_base;
    wire [13:0] engine_weight_req_k;
    wire engine_weight_rsp_valid;
    wire engine_weight_rsp_ready;
    wire [255:0] engine_weight_rsp_data;
    wire engine_weight_rsp_error;
    wire engine_out_valid;
    wire engine_out_ready;
    wire [255:0] engine_result_weights;
    wire [511:0] engine_result_combination;
    wire [7:0] engine_result_error;
    wire [63:0] scheduler_projection_tiles;
    wire [63:0] scheduler_commit_tiles;
    wire [63:0] scheduler_logical_fmas;
    wire [63:0] scheduler_logical_outputs;

    ot_a3_hc_pre_t1_handshake_rne arithmetic (
        .clk(clk), .rst_n(rst_n),
        .in_valid(state == S_ENGINE_START), .in_ready(engine_in_ready),
        .config_words(config_q), .base_codes(base_codes_q),
        .scale_codes(scale_codes_q),
        .hidden_req_valid(engine_hidden_req_valid),
        .hidden_req_ready(engine_hidden_req_ready),
        .hidden_req_k(engine_hidden_req_k),
        .hidden_rsp_valid(engine_hidden_rsp_valid),
        .hidden_rsp_ready(engine_hidden_rsp_ready),
        .hidden_rsp_data(engine_hidden_rsp_data),
        .hidden_rsp_error(engine_hidden_rsp_error),
        .weight_req_valid(engine_weight_req_valid),
        .weight_req_ready(engine_weight_req_ready),
        .weight_req_field_base(engine_weight_req_field_base),
        .weight_req_k(engine_weight_req_k),
        .weight_rsp_valid(engine_weight_rsp_valid),
        .weight_rsp_ready(engine_weight_rsp_ready),
        .weight_rsp_data(engine_weight_rsp_data),
        .weight_rsp_error(engine_weight_rsp_error),
        .out_valid(engine_out_valid), .out_ready(engine_out_ready),
        .result_weight_codes(engine_result_weights),
        .result_combination_codes(engine_result_combination),
        .result_error(engine_result_error),
        .scheduler_projection_tiles(scheduler_projection_tiles),
        .scheduler_commit_tiles(scheduler_commit_tiles),
        .scheduler_logical_fmas(scheduler_logical_fmas),
        .scheduler_logical_outputs(scheduler_logical_outputs),
        .arithmetic_square_count(arithmetic_square_count),
        .arithmetic_reduction_add_count(
            arithmetic_reduction_add_count),
        .arithmetic_fma_count(arithmetic_fma_count)
    );

    wire choose_hidden_request =
        state == S_ENGINE_WAIT && !engine_memory_pending &&
        engine_hidden_req_valid;
    wire choose_weight_request =
        state == S_ENGINE_WAIT && !engine_memory_pending &&
        !engine_hidden_req_valid && engine_weight_req_valid;
    assign engine_hidden_req_ready = choose_hidden_request && mem_read_ready;
    assign engine_weight_req_ready = choose_weight_request && mem_read_ready;
    assign engine_hidden_rsp_valid = state == S_ENGINE_WAIT &&
        engine_memory_pending && !engine_memory_owner && mem_response_valid;
    assign engine_weight_rsp_valid = state == S_ENGINE_WAIT &&
        engine_memory_pending && engine_memory_owner && mem_response_valid;
    assign engine_hidden_rsp_data = mem_response_data[15:0];
    assign engine_weight_rsp_data = mem_response_data;
    assign engine_hidden_rsp_error = mem_response_error;
    assign engine_weight_rsp_error = mem_response_error;
    assign engine_out_ready = state == S_ENGINE_WAIT && engine_out_valid;

    always @* begin
        mem_read_valid = 1'b0;
        mem_read_object_id = NO_ID;
        mem_read_element_offset = 0;
        mem_read_dtype = 0;
        mem_read_element_count = 0;
        mem_read_element_stride = 0;
        mem_response_ready = 1'b0;
        if (state == S_BASE_REQ) begin
            mem_read_valid = 1'b1;
            mem_read_object_id = view_cfg(config_q, 2, 0);
            mem_read_element_offset = issued_observed_offset[2] +
                {59'd0, parameter_index};
            mem_read_dtype = DTYPE_FP32;
            mem_read_element_count = 1;
            mem_read_element_stride = 1;
        end else if (state == S_SCALE_REQ) begin
            mem_read_valid = 1'b1;
            mem_read_object_id = view_cfg(config_q, 3, 0);
            mem_read_element_offset = issued_observed_offset[3] +
                {59'd0, parameter_index};
            mem_read_dtype = DTYPE_FP32;
            mem_read_element_count = 1;
            mem_read_element_stride = 1;
        end else if (choose_hidden_request) begin
            mem_read_valid = 1'b1;
            mem_read_object_id = view_cfg(config_q, 0, 0);
            mem_read_element_offset = issued_observed_offset[0] +
                {50'd0, engine_hidden_req_k};
            mem_read_dtype = DTYPE_BF16;
            mem_read_element_count = 1;
            mem_read_element_stride = 1;
        end else if (choose_weight_request) begin
            mem_read_valid = 1'b1;
            mem_read_object_id = view_cfg(config_q, 1, 0);
            mem_read_element_offset = issued_observed_offset[1] +
                ({59'd0, engine_weight_req_field_base} *
                 {32'd0, view_cfg(config_q, 1, 7)}) +
                {50'd0, engine_weight_req_k};
            mem_read_dtype = DTYPE_FP32;
            mem_read_element_count = 5'd8;
            mem_read_element_stride = view_cfg(config_q, 1, 7);
        end

        if (state == S_BASE_RSP || state == S_SCALE_RSP)
            mem_response_ready = 1'b1;
        else if (state == S_ENGINE_WAIT && engine_memory_pending)
            mem_response_ready = engine_memory_owner
                ? engine_weight_rsp_ready : engine_hidden_rsp_ready;
    end

    assign mem_write_valid = state == S_WRITE;
    assign mem_write_object_id = write_index < 8
        ? view_cfg(config_q, 4, 0) : view_cfg(config_q, 5, 0);
    assign mem_write_element_offset = write_index < 8
        ? issued_observed_offset[4] + {59'd0, write_index}
        : issued_observed_offset[5] + {59'd0, write_index - 5'd8};
    assign mem_write_data = write_index < 8
        ? result_weights_q[write_index*32 +: 32]
        : result_combination_q[(write_index-8)*32 +: 32];

    assign issue_ready = state == S_RESPONSE;
    assign issue_fault = response_fault_q;
    assign issue_trap_class = response_trap_q;
    assign busy = state != S_IDLE;

    task automatic finish_fault;
        input [15:0] trap_value;
        input [7:0] error_value;
        begin
            response_fault_q <= 1'b1;
            response_trap_q <= trap_value;
            last_error_code <= error_value;
            state <= S_RESPONSE;
        end
    endtask

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            profile_q <= PROFILE_ROM;
            response_fault_q <= 1'b0;
            response_trap_q <= TRAP_NONE;
            descriptor_index <= 0;
            descriptor_record_q <= 0;
            operator_counter_id <= NO_ID;
            operator_numeric_id <= NO_ID;
            operator_schedule_id <= NO_ID;
            config_q <= 0;
            base_codes_q <= 0;
            scale_codes_q <= 0;
            parameter_index <= 0;
            result_weights_q <= 0;
            result_combination_q <= 0;
            write_index <= 0;
            observed_valid <= 0;
            issued_observed_valid <= 0;
            engine_memory_pending <= 1'b0;
            engine_memory_owner <= 1'b0;
            descriptor_records_checked <= 0;
            resolved_views_captured <= 0;
            memory_read_count <= 0;
            memory_request_stall_cycles <= 0;
            memory_response_stall_cycles <= 0;
            output_write_count <= 0;
            output_write_stall_cycles <= 0;
            arithmetic_executed <= 1'b0;
            last_error_code <= ERR_NONE;
            for (item = 0; item < 6; item = item + 1) begin
                operator_view_id[item] <= NO_ID;
                observed_id[item] <= NO_ID;
                observed_extent[item] <= 0;
                observed_axis[item] <= 0;
                observed_offset[item] <= 0;
                observed_rank[item] <= 0;
                issued_observed_id[item] <= NO_ID;
                issued_observed_extent[item] <= 0;
                issued_observed_axis[item] <= 0;
                issued_observed_offset[item] <= 0;
                issued_observed_rank[item] <= 0;
            end
        end else begin
            if (clear) begin
                state <= S_IDLE;
                response_fault_q <= 1'b0;
                response_trap_q <= TRAP_NONE;
                descriptor_index <= 0;
                descriptor_record_q <= 0;
                config_q <= 0;
                base_codes_q <= 0;
                scale_codes_q <= 0;
                result_weights_q <= 0;
                result_combination_q <= 0;
                observed_valid <= 0;
                issued_observed_valid <= 0;
                engine_memory_pending <= 1'b0;
                descriptor_records_checked <= 0;
                resolved_views_captured <= 0;
                memory_read_count <= 0;
                memory_request_stall_cycles <= 0;
                memory_response_stall_cycles <= 0;
                output_write_count <= 0;
                output_write_stall_cycles <= 0;
                arithmetic_executed <= 1'b0;
                last_error_code <= ERR_NONE;
            end else begin
                if (view_valid && view_slot < 6) begin
                    observed_valid[view_slot] <= 1'b1;
                    observed_id[view_slot] <= view_descriptor_id;
                    observed_extent[view_slot] <= view_extent;
                    observed_axis[view_slot] <= view_extent_axis;
                    observed_offset[view_slot] <= view_element_offset;
                    observed_rank[view_slot] <= view_rank;
                end
                if (mem_read_valid && !mem_read_ready)
                    memory_request_stall_cycles <=
                        memory_request_stall_cycles + 1'b1;
                if (mem_response_valid && !mem_response_ready)
                    memory_response_stall_cycles <=
                        memory_response_stall_cycles + 1'b1;
                if (mem_write_valid && !mem_write_ready)
                    output_write_stall_cycles <=
                        output_write_stall_cycles + 1'b1;

                case (state)
                    S_IDLE: begin
                        if (issue_valid) begin
                            response_fault_q <= 1'b0;
                            response_trap_q <= TRAP_NONE;
                            last_error_code <= ERR_NONE;
                            descriptor_index <= 0;
                            descriptor_records_checked <= 0;
                            resolved_views_captured <= 0;
                            memory_read_count <= 0;
                            memory_request_stall_cycles <= 0;
                            memory_response_stall_cycles <= 0;
                            output_write_count <= 0;
                            output_write_stall_cycles <= 0;
                            arithmetic_executed <= 1'b0;
                            config_q <= 0;
                            base_codes_q <= 0;
                            scale_codes_q <= 0;
                            result_weights_q <= 0;
                            result_combination_q <= 0;
                            issued_observed_valid <= observed_valid;
                            resolved_views_captured <=
                                observed_valid[0] + observed_valid[1] +
                                observed_valid[2] + observed_valid[3] +
                                observed_valid[4] + observed_valid[5];
                            for (item = 0; item < 6; item = item + 1) begin
                                issued_observed_id[item] <= observed_id[item];
                                issued_observed_extent[item] <=
                                    observed_extent[item];
                                issued_observed_axis[item] <= observed_axis[item];
                                issued_observed_offset[item] <=
                                    observed_offset[item];
                                issued_observed_rank[item] <= observed_rank[item];
                            end
                            if (issue_is_rom || issue_is_hbm) begin
                                profile_q <= issue_is_hbm
                                    ? PROFILE_HBM : PROFILE_ROM;
                                config_q[0 +: 32] <= issue_is_hbm
                                    ? 32'd1 : 32'd0;
                                config_q[32 +: 32] <= observed_extent[0];
                                config_q[64 +: 32] <= issue_index;
                                config_q[96 +: 32] <= {16'd0, issue_flags};
                                config_q[128 +: 32] <= issue_descriptor_id;
                                config_q[160 +: 32] <= issue_wait_set_id;
                                config_q[224 +: 32] <= issue_signal_event_id;
                                config_q[256 +: 32] <= issue_control_id;
                                config_q[288 +: 32] <=
                                    issue_source_operation_id;
                                state <= S_DESC_REQ;
                            end else begin
                                finish_fault(TRAP_CAPABILITY, ERR_INSTRUCTION);
                            end
                        end
                    end

                    S_DESC_REQ: state <= S_DESC_WAIT;

                    S_DESC_WAIT: begin
                        if (desc_valid) begin
                            if (desc_fault) begin
                                finish_fault(
                                    TRAP_DESCRIPTOR, ERR_DESCRIPTOR_READ);
                            end else begin
                                descriptor_record_q <= desc_data;
                                state <= S_VALIDATE_START;
                            end
                        end
                    end

                    S_VALIDATE_START: state <= S_VALIDATE_WAIT;

                    S_VALIDATE_WAIT: begin
                        if (validator_done) begin
                            if (!validator_legal) begin
                                finish_fault(
                                    TRAP_DESCRIPTOR,
                                    ERR_DESCRIPTOR_INTEGRITY);
                            end else if (!current_record_semantic_ok) begin
                                finish_fault(
                                    TRAP_DESCRIPTOR,
                                    ERR_DESCRIPTOR_SEMANTICS);
                            end else begin
                                descriptor_records_checked <=
                                    descriptor_records_checked + 1'b1;
                                case (descriptor_index)
                                    0: begin
                                        config_q[10*32 +: 32] <=
                                            {24'd0, descriptor_record_q[519:512]};
                                        config_q[11*32 +: 32] <=
                                            {24'd0, descriptor_record_q[527:520]};
                                        config_q[12*32 +: 32] <=
                                            {16'd0, descriptor_record_q[543:528]};
                                        for (item = 0; item < 15;
                                             item = item + 1)
                                            config_q[(13+item)*32 +: 32] <=
                                                descriptor_record_q[
                                                    544+item*32 +: 32];
                                        operator_counter_id <=
                                            descriptor_record_q[639:608];
                                        operator_numeric_id <=
                                            descriptor_record_q[671:640];
                                        operator_schedule_id <=
                                            descriptor_record_q[703:672];
                                        operator_view_id[0] <=
                                            descriptor_record_q[735:704];
                                        operator_view_id[1] <=
                                            descriptor_record_q[767:736];
                                        operator_view_id[2] <=
                                            descriptor_record_q[799:768];
                                        operator_view_id[3] <=
                                            descriptor_record_q[831:800];
                                        operator_view_id[4] <=
                                            descriptor_record_q[863:832];
                                        operator_view_id[5] <=
                                            descriptor_record_q[895:864];
                                    end
                                    1: config_q[6*32 +: 32] <=
                                        descriptor_record_q[607:576];
                                    2: begin
                                        config_q[28*32 +: 32] <=
                                            {24'd0, descriptor_record_q[519:512]};
                                        config_q[29*32 +: 32] <=
                                            {24'd0, descriptor_record_q[527:520]};
                                        config_q[30*32 +: 32] <=
                                            descriptor_record_q[607:576];
                                        config_q[31*32 +: 32] <=
                                            descriptor_record_q[639:608];
                                        config_q[32*32 +: 32] <=
                                            descriptor_record_q[671:640];
                                    end
                                    3: begin
                                        for (item = 0; item < 8;
                                             item = item + 1)
                                            config_q[(33+item)*32 +: 32] <=
                                                {24'd0,
                                                 descriptor_record_q[
                                                    512+item*8 +: 8]};
                                        config_q[41*32 +: 32] <=
                                            descriptor_record_q[607:576];
                                        config_q[42*32 +: 32] <=
                                            descriptor_record_q[639:608];
                                        config_q[43*32 +: 32] <=
                                            descriptor_record_q[671:640];
                                        for (item = 0; item < 8;
                                             item = item + 1)
                                            config_q[(44+item)*32 +: 32] <=
                                                descriptor_record_q[
                                                    768+item*32 +: 32];
                                    end
                                    4: begin
                                        config_q[52*32 +: 32] <=
                                            {24'd0, descriptor_record_q[519:512]};
                                        config_q[53*32 +: 32] <=
                                            {24'd0, descriptor_record_q[527:520]};
                                        config_q[54*32 +: 32] <=
                                            {16'd0, descriptor_record_q[543:528]};
                                        for (item = 0; item < 9;
                                             item = item + 1)
                                            config_q[(55+item)*32 +: 32] <=
                                                descriptor_record_q[
                                                    544+item*32 +: 32];
                                    end
                                    5, 6, 7, 8, 9, 10: begin
                                        config_q[(64+(descriptor_index-5)*10)*32
                                                 +: 32] <=
                                            descriptor_record_q[159:128];
                                        config_q[(65+(descriptor_index-5)*10)*32
                                                 +: 32] <=
                                            descriptor_record_q[287:256];
                                        config_q[(66+(descriptor_index-5)*10)*32
                                                 +: 32] <=
                                            {24'd0,
                                             descriptor_record_q[519:512]};
                                        config_q[(67+(descriptor_index-5)*10)*32
                                                 +: 32] <=
                                            {24'd0,
                                             descriptor_record_q[527:520]};
                                        for (item = 0; item < 3;
                                             item = item + 1)
                                            config_q[(68+(descriptor_index-5)*10
                                                      +item)*32 +: 32] <=
                                                descriptor_record_q[
                                                    704+item*32 +: 32];
                                        for (item = 0; item < 3;
                                             item = item + 1)
                                            config_q[(71+(descriptor_index-5)*10
                                                      +item)*32 +: 32] <=
                                                descriptor_record_q[
                                                    896+item*32 +: 32];
                                    end
                                endcase
                                if (descriptor_index == 10) begin
                                    state <= S_PRECHECK;
                                end else begin
                                    descriptor_index <= descriptor_index + 1'b1;
                                    state <= S_DESC_REQ;
                                end
                            end
                        end
                    end

                    S_PRECHECK: begin
                        if (!resolved_views_match) begin
                            finish_fault(
                                TRAP_DESCRIPTOR, ERR_VIEW_OBSERVATION);
                        end else begin
                            parameter_index <= 0;
                            state <= S_BASE_REQ;
                        end
                    end

                    S_BASE_REQ: begin
                        if (mem_read_valid && mem_read_ready) begin
                            memory_read_count <= memory_read_count + 1'b1;
                            state <= S_BASE_RSP;
                        end
                    end

                    S_BASE_RSP: begin
                        if (mem_response_valid && mem_response_ready) begin
                            if (mem_response_error) begin
                                finish_fault(TRAP_ENGINE, ERR_MEMORY_READ);
                            end else begin
                                base_codes_q[parameter_index*32 +: 32] <=
                                    mem_response_data[31:0];
                                if (parameter_index == 23) begin
                                    parameter_index <= 0;
                                    state <= S_SCALE_REQ;
                                end else begin
                                    parameter_index <= parameter_index + 1'b1;
                                    state <= S_BASE_REQ;
                                end
                            end
                        end
                    end

                    S_SCALE_REQ: begin
                        if (mem_read_valid && mem_read_ready) begin
                            memory_read_count <= memory_read_count + 1'b1;
                            state <= S_SCALE_RSP;
                        end
                    end

                    S_SCALE_RSP: begin
                        if (mem_response_valid && mem_response_ready) begin
                            if (mem_response_error) begin
                                finish_fault(TRAP_ENGINE, ERR_MEMORY_READ);
                            end else begin
                                scale_codes_q[parameter_index*32 +: 32] <=
                                    mem_response_data[31:0];
                                if (parameter_index == 2) begin
                                    parameter_index <= 0;
                                    state <= S_ENGINE_START;
                                end else begin
                                    parameter_index <= parameter_index + 1'b1;
                                    state <= S_SCALE_REQ;
                                end
                            end
                        end
                    end

                    S_ENGINE_START: begin
                        if (engine_in_ready) begin
                            arithmetic_executed <= 1'b1;
                            engine_memory_pending <= 1'b0;
                            state <= S_ENGINE_WAIT;
                        end
                    end

                    S_ENGINE_WAIT: begin
                        if (!engine_memory_pending && mem_read_valid &&
                            mem_read_ready) begin
                            engine_memory_pending <= 1'b1;
                            engine_memory_owner <= choose_weight_request;
                            memory_read_count <= memory_read_count + 1'b1;
                        end
                        if (engine_memory_pending && mem_response_valid &&
                            mem_response_ready)
                            engine_memory_pending <= 1'b0;
                        if (engine_out_valid && engine_out_ready) begin
                            if (engine_result_error != 0) begin
                                if (engine_result_error >= 16 &&
                                    engine_result_error <= 22)
                                    finish_fault(
                                        TRAP_DESCRIPTOR,
                                        ERR_DESCRIPTOR_SEMANTICS);
                                else if (engine_result_error == 34)
                                    finish_fault(TRAP_ENGINE, ERR_MEMORY_READ);
                                else
                                    finish_fault(TRAP_NUMERIC, ERR_ARITHMETIC);
                            end else begin
                                result_weights_q <= engine_result_weights;
                                result_combination_q <=
                                    engine_result_combination;
                                write_index <= 0;
                                state <= S_WRITE;
                            end
                        end
                    end

                    S_WRITE: begin
                        if (mem_write_valid && mem_write_ready) begin
                            output_write_count <= output_write_count + 1'b1;
                            if (write_index == 23) begin
                                response_fault_q <= 1'b0;
                                response_trap_q <= TRAP_NONE;
                                state <= S_RESPONSE;
                            end else begin
                                write_index <= write_index + 1'b1;
                            end
                        end
                    end

                    S_RESPONSE: begin
                        if (issue_valid && issue_ready) begin
                            observed_valid <= 0;
                            issued_observed_valid <= 0;
                            state <= S_IDLE;
                        end
                    end

                    default: finish_fault(TRAP_ENGINE, ERR_ARITHMETIC);
                endcase
            end
        end
    end
endmodule
