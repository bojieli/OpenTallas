`timescale 1ns/1ps
// Exact ABI 3.0 PC41 adapter for the Qwen3-8B attention output projection.
//
// Only the two shipped ROM/HBM encodings are admitted.  Instruction CRC and
// five complete descriptor-record CRCs are checked before semantic admission
// and before any operand read.  Placement-specific IDs differ, but both paths
// must name the same fixed shape, numeric contract, association, and request.
module ot_a3_qwen_output_projection_adapter (
    input  wire           clk,
    input  wire           rst_n,
    input  wire           start,

    input  wire [255:0]   instruction_record,
    input  wire [31:0]    instruction_index,
    input  wire [31:0]    instruction_count,
    input  wire [31:0]    operator_descriptor_id,
    input  wire [31:0]    view0_descriptor_id,
    input  wire [31:0]    view1_descriptor_id,
    input  wire [31:0]    output_descriptor_id,
    input  wire [31:0]    numeric_descriptor_id,
    input  wire [31:0]    expected_object0,
    input  wire [31:0]    expected_object1,
    input  wire [31:0]    expected_output_object,
    input  wire [1535:0]  operator_record,
    input  wire [1535:0]  view0_record,
    input  wire [1535:0]  view1_record,
    input  wire [1535:0]  output_record,
    input  wire [1535:0]  numeric_record,

    input  wire [31:0]    cfg_position_start,
    input  wire [31:0]    cfg_context_length,
    input  wire [31:0]    cfg_input_base,
    input  wire [31:0]    cfg_weight_base,
    input  wire [31:0]    cfg_output_base,

    output wire           mem_req_valid,
    input  wire           mem_req_ready,
    output wire [31:0]    mem_req_addr,
    input  wire           mem_rsp_valid,
    input  wire [31:0]    mem_rsp_data,
    output wire           out_valid,
    input  wire           out_ready,
    output wire [31:0]    out_addr,
    output wire [31:0]    out_data,

    output reg            busy,
    output reg            done,
    output reg            failed,
    output reg  [15:0]    trap_class,
    output reg  [7:0]     refusal_reason,
    output reg  [31:0]    records_checked,
    output wire [31:0]    memory_read_count,
    output wire [31:0]    input_read_count,
    output wire [31:0]    weight_read_count,
    output wire [31:0]    mac_count,
    output wire [31:0]    write_count,
    output wire [31:0]    saturation_count,
    output reg            projection_executed
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
    localparam [7:0] FAMILY_TENSOR = 8'h20;
    localparam [7:0] TENSOR_MATMUL = 8'h00;
    localparam [7:0] FMT_BF16 = 8'h10;
    localparam [7:0] FMT_FP32 = 8'h12;
    localparam [31:0] WIDTH = 32'd4096;
    localparam [255:0] CONTRACT_MATMUL_RAW =
        256'ha15a76a03cd9c4212365014f8ebb77b73f61872818463b77d5d93f776adc5075;

    localparam [2:0] S_IDLE = 3'd0;
    localparam [2:0] S_DECODE_START = 3'd1;
    localparam [2:0] S_DECODE_WAIT = 3'd2;
    localparam [2:0] S_RECORD_START = 3'd3;
    localparam [2:0] S_RECORD_WAIT = 3'd4;
    localparam [2:0] S_ADMIT = 3'd5;
    localparam [2:0] S_ENGINE_START = 3'd6;
    localparam [2:0] S_ENGINE_WAIT = 3'd7;
    localparam [3:0] S_FINISH = 4'd8;

    reg [3:0] state;
    reg [2:0] record_slot;
    reg [255:0] instruction_record_q;
    reg [31:0] instruction_index_q;
    reg [31:0] instruction_count_q;
    reg [31:0] operator_id_q;
    reg [31:0] view0_id_q;
    reg [31:0] view1_id_q;
    reg [31:0] output_id_q;
    reg [31:0] numeric_id_q;
    reg [31:0] object0_q;
    reg [31:0] object1_q;
    reg [31:0] output_object_q;
    reg [1535:0] operator_record_q;
    reg [1535:0] view0_record_q;
    reg [1535:0] view1_record_q;
    reg [1535:0] output_record_q;
    reg [1535:0] numeric_record_q;
    reg [31:0] position_q;
    reg [31:0] context_q;
    reg [31:0] input_base_q;
    reg [31:0] weight_base_q;
    reg [31:0] output_base_q;
    reg engine_invoked_q;

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
        .in_valid(state == S_DECODE_START), .in_ready(decoder_in_ready),
        .in_record(instruction_record_q), .in_index(instruction_index_q),
        .in_instruction_count(instruction_count_q),
        .out_valid(decoder_out_valid), .out_ready(state == S_DECODE_WAIT),
        .out_legal(decoder_out_legal), .out_error(decoder_out_error),
        .out_trap_class(decoder_out_trap), .out_index(),
        .out_major(decoder_out_major), .out_sub(decoder_out_sub),
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
            3'd3: selected_record = output_record_q;
            3'd4: begin
                selected_record = numeric_record_q;
                selected_type = DESC_NUMERIC;
                selected_total = 32'd128;
                selected_payload = 32'd64;
            end
            default: selected_record = 1536'd0;
        endcase
    end

    wire record_done;
    wire record_legal;
    wire [7:0] record_error;
    ot_a3_descriptor_record_validator descriptor_validator (
        .clk(clk), .rst_n(rst_n), .start(state == S_RECORD_START),
        .record(selected_record), .expected_type(selected_type),
        .expected_total_bytes(selected_total),
        .expected_payload_bytes(selected_payload), .busy(),
        .done(record_done), .legal(record_legal), .error_code(record_error)
    );

    function automatic view_header_ok;
        input [1535:0] data;
        input [31:0] object_id;
        input [31:0] permissions;
        begin
            view_header_ok =
                (data[127:96] == 32'd0) &&
                (data[159:128] == object_id) && (object_id != NO_ID) &&
                (data[191:160] == NO_ID) &&
                (data[223:192] == NO_ID) &&
                (data[255:224] == NO_ID) &&
                (data[287:256] == permissions) &&
                (data[319:288] == 32'd0) &&
                (data[519:512] == FMT_BF16) &&
                (data[527:520] == 8'd2) &&
                (data[535:528] == 8'd0) &&
                (data[543:536] == 8'd1) &&
                (data[575:544] == NO_ID) &&
                (data[607:576] == 32'd0) &&
                (data[639:608] == NO_ID);
        end
    endfunction

    function automatic matrix_view_ok;
        input [1535:0] data;
        input [31:0] object_id;
        input [31:0] permissions;
        input [31:0] rows;
        input [15:0] term_index;
        input [31:0] term_stride;
        begin
            matrix_view_ok = view_header_ok(data, object_id, permissions) &&
                (data[703:640] == 64'd0) &&
                (data[735:704] == rows) &&
                (data[767:736] == WIDTH) &&
                (data[895:768] == 128'd0) &&
                (data[927:896] == WIDTH) &&
                (data[959:928] == 32'd1) &&
                (data[1087:960] == 128'd0) &&
                (data[1103:1088] == 16'd0) &&
                (data[1119:1104] == term_index) &&
                (data[1151:1120] == term_stride) &&
                (data[1535:1152] == 384'd0);
        end
    endfunction

    wire rom_profile =
        (operator_id_q == 32'd134) && (view0_id_q == 32'd130) &&
        (view1_id_q == 32'd131) && (output_id_q == 32'd132) &&
        (numeric_id_q == 32'd57) && (object0_q == 32'd45) &&
        (object1_q == 32'd12) && (output_object_q == 32'd55) &&
        (instruction_wait_q == 32'd135);
    wire hbm_profile =
        (operator_id_q == 32'd137) && (view0_id_q == 32'd134) &&
        (view1_id_q == 32'd135) && (output_id_q == 32'd136) &&
        (numeric_id_q == 32'd70) && (object0_q == 32'd19) &&
        (object1_q == 32'd7) && (output_object_q == 32'd20) &&
        (instruction_wait_q == 32'd138);
    wire profile_ok = rom_profile || hbm_profile;
    wire [31:0] expected_schedule = rom_profile ? 32'd133 : 32'd71;
    wire [31:0] expected_counter = rom_profile ? 32'd40 : 32'd47;
    wire [15:0] activation_loop = rom_profile ? 16'd129 : 16'd133;
    wire [15:0] layer_loop = rom_profile ? 16'd19 : 16'd56;

    wire instruction_ok =
        (instruction_count_q == 32'd74) &&
        (instruction_index_q == 32'd41) &&
        (instruction_major_q == FAMILY_TENSOR) &&
        (instruction_sub_q == TENSOR_MATMUL) &&
        (instruction_flags_q == 16'd12) &&
        (instruction_predicate_q == NO_ID) &&
        (instruction_descriptor_q == operator_id_q) &&
        (instruction_signal_q == 32'd13) &&
        (instruction_control_q == NO_ID) &&
        (instruction_source_q == 32'd14);
    wire operator_ok =
        (operator_record_q[127:96] == 32'd0) &&
        (operator_record_q[159:128] == NO_ID) &&
        (operator_record_q[191:160] == NO_ID) &&
        (operator_record_q[223:192] == numeric_id_q) &&
        (operator_record_q[255:224] == expected_schedule) &&
        (operator_record_q[287:256] == 32'd5) &&
        (operator_record_q[319:288] == 32'd0) &&
        (operator_record_q[519:512] == FAMILY_TENSOR) &&
        (operator_record_q[527:520] == TENSOR_MATMUL) &&
        (operator_record_q[543:528] == 16'd0) &&
        (operator_record_q[575:544] == NO_ID) &&
        (operator_record_q[607:576] == 32'd14) &&
        (operator_record_q[639:608] == expected_counter) &&
        (operator_record_q[671:640] == numeric_id_q) &&
        (operator_record_q[703:672] == expected_schedule) &&
        (operator_record_q[735:704] == view0_id_q) &&
        (operator_record_q[767:736] == view1_id_q) &&
        (operator_record_q[831:768] == {2{NO_ID}}) &&
        (operator_record_q[863:832] == output_id_q) &&
        (operator_record_q[895:864] == NO_ID) &&
        (operator_record_q[1023:896] == {4{NO_ID}});
    wire views_ok =
        matrix_view_ok(
            view0_record_q, object0_q, 32'd1, 32'd512,
            activation_loop, 32'd2097152
        ) &&
        matrix_view_ok(
            view1_record_q, object1_q, 32'd1, WIDTH,
            layer_loop, 32'd16777216
        ) &&
        matrix_view_ok(
            output_record_q, output_object_q, 32'd3, 32'd512,
            activation_loop, 32'd2097152
        );
    wire numeric_ok =
        (numeric_record_q[127:96] == 32'd0) &&
        (numeric_record_q[159:128] == NO_ID) &&
        (numeric_record_q[191:160] == NO_ID) &&
        (numeric_record_q[223:192] == NO_ID) &&
        (numeric_record_q[255:224] == NO_ID) &&
        (numeric_record_q[287:256] == 32'd129) &&
        (numeric_record_q[319:288] == 32'd0) &&
        (numeric_record_q[519:512] == FMT_BF16) &&
        (numeric_record_q[527:520] == FMT_BF16) &&
        (numeric_record_q[535:528] == FMT_FP32) &&
        (numeric_record_q[543:536] == FMT_BF16) &&
        (numeric_record_q[551:544] == 8'd0) &&
        (numeric_record_q[559:552] == 8'd2) &&
        (numeric_record_q[575:560] == 16'd0) &&
        (numeric_record_q[607:576] == 32'd0) &&
        (numeric_record_q[767:608] == 160'd0) &&
        (numeric_record_q[1023:768] == CONTRACT_MATMUL_RAW);
    wire semantics_ok = profile_ok && instruction_ok && operator_ok &&
        views_ok && numeric_ok && (position_q == 32'd16) &&
        (context_q == 32'd17) && (context_q == position_q + 1'b1);

    wire engine_done;
    wire engine_failed;
    wire [7:0] engine_error;
    wire engine_mem_req_valid;
    wire [31:0] engine_mem_req_addr;
    wire engine_out_valid;
    wire [31:0] engine_out_addr;
    wire [31:0] engine_out_data;
    wire [31:0] engine_memory_reads;
    wire [31:0] engine_input_reads;
    wire [31:0] engine_weight_reads;
    wire [31:0] engine_macs;
    wire [31:0] engine_writes;
    wire [31:0] engine_saturations;
    ot_a3_qwen_output_projection engine (
        .clk(clk), .rst_n(rst_n), .start(state == S_ENGINE_START),
        .cfg_input_base(input_base_q), .cfg_weight_base(weight_base_q),
        .cfg_output_base(output_base_q),
        .mem_req_valid(engine_mem_req_valid), .mem_req_ready(mem_req_ready),
        .mem_req_addr(engine_mem_req_addr), .mem_rsp_valid(mem_rsp_valid),
        .mem_rsp_data(mem_rsp_data), .out_valid(engine_out_valid),
        .out_ready(out_ready), .out_addr(engine_out_addr),
        .out_data(engine_out_data), .busy(), .done(engine_done),
        .failed(engine_failed), .error_code(engine_error),
        .memory_read_count(engine_memory_reads),
        .input_read_count(engine_input_reads),
        .weight_read_count(engine_weight_reads), .mac_count(engine_macs),
        .output_write_count(engine_writes),
        .saturation_count(engine_saturations)
    );
    assign mem_req_valid = engine_invoked_q && engine_mem_req_valid;
    assign mem_req_addr = engine_mem_req_addr;
    assign out_valid = engine_invoked_q && engine_out_valid;
    assign out_addr = engine_out_addr;
    assign out_data = engine_out_data;
    assign memory_read_count = engine_invoked_q ? engine_memory_reads : 0;
    assign input_read_count = engine_invoked_q ? engine_input_reads : 0;
    assign weight_read_count = engine_invoked_q ? engine_weight_reads : 0;
    assign mac_count = engine_invoked_q ? engine_macs : 0;
    assign write_count = engine_invoked_q ? engine_writes : 0;
    assign saturation_count = engine_invoked_q ? engine_saturations : 0;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            record_slot <= 0;
            instruction_record_q <= 0;
            instruction_index_q <= 0;
            instruction_count_q <= 0;
            operator_id_q <= NO_ID;
            view0_id_q <= NO_ID;
            view1_id_q <= NO_ID;
            output_id_q <= NO_ID;
            numeric_id_q <= NO_ID;
            object0_q <= NO_ID;
            object1_q <= NO_ID;
            output_object_q <= NO_ID;
            operator_record_q <= 0;
            view0_record_q <= 0;
            view1_record_q <= 0;
            output_record_q <= 0;
            numeric_record_q <= 0;
            position_q <= 0;
            context_q <= 0;
            input_base_q <= 0;
            weight_base_q <= 0;
            output_base_q <= 0;
            engine_invoked_q <= 1'b0;
            instruction_major_q <= 0;
            instruction_sub_q <= 0;
            instruction_flags_q <= 0;
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
            records_checked <= 0;
            projection_executed <= 1'b0;
        end else begin
            done <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        instruction_record_q <= instruction_record;
                        instruction_index_q <= instruction_index;
                        instruction_count_q <= instruction_count;
                        operator_id_q <= operator_descriptor_id;
                        view0_id_q <= view0_descriptor_id;
                        view1_id_q <= view1_descriptor_id;
                        output_id_q <= output_descriptor_id;
                        numeric_id_q <= numeric_descriptor_id;
                        object0_q <= expected_object0;
                        object1_q <= expected_object1;
                        output_object_q <= expected_output_object;
                        operator_record_q <= operator_record;
                        view0_record_q <= view0_record;
                        view1_record_q <= view1_record;
                        output_record_q <= output_record;
                        numeric_record_q <= numeric_record;
                        position_q <= cfg_position_start;
                        context_q <= cfg_context_length;
                        input_base_q <= cfg_input_base;
                        weight_base_q <= cfg_weight_base;
                        output_base_q <= cfg_output_base;
                        engine_invoked_q <= 1'b0;
                        record_slot <= 0;
                        busy <= 1'b1;
                        failed <= 1'b0;
                        trap_class <= TRAP_NONE;
                        refusal_reason <= REFUSAL_NONE;
                        records_checked <= 0;
                        projection_executed <= 1'b0;
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
                            refusal_reason <= decoder_out_error == 4'd1
                                ? REFUSAL_INTEGRITY : REFUSAL_INSTRUCTION;
                            state <= S_FINISH;
                        end else if ((decoder_out_major != FAMILY_TENSOR) ||
                                     (decoder_out_sub != TENSOR_MATMUL)) begin
                            failed <= 1'b1;
                            trap_class <= TRAP_CAPABILITY;
                            refusal_reason <= REFUSAL_CAPABILITY;
                            state <= S_FINISH;
                        end else begin
                            state <= S_RECORD_START;
                        end
                    end
                end

                S_RECORD_START: state <= S_RECORD_WAIT;

                S_RECORD_WAIT: begin
                    if (record_done) begin
                        if (!record_legal) begin
                            failed <= 1'b1;
                            trap_class <= record_error == 8'd1
                                ? TRAP_INTEGRITY : TRAP_DESCRIPTOR;
                            refusal_reason <= record_error == 8'd1
                                ? REFUSAL_INTEGRITY : REFUSAL_DESCRIPTOR;
                            state <= S_FINISH;
                        end else begin
                            records_checked <= records_checked + 1'b1;
                            if (record_slot == 3'd4)
                                state <= S_ADMIT;
                            else begin
                                record_slot <= record_slot + 1'b1;
                                state <= S_RECORD_START;
                            end
                        end
                    end
                end

                S_ADMIT: begin
                    if (!semantics_ok) begin
                        failed <= 1'b1;
                        trap_class <= TRAP_DESCRIPTOR;
                        refusal_reason <= REFUSAL_DESCRIPTOR;
                        state <= S_FINISH;
                    end else begin
                        state <= S_ENGINE_START;
                    end
                end

                S_ENGINE_START: begin
                    engine_invoked_q <= 1'b1;
                    state <= S_ENGINE_WAIT;
                end

                S_ENGINE_WAIT: begin
                    if (engine_done) begin
                        if (engine_failed || engine_error != 0) begin
                            failed <= 1'b1;
                            trap_class <= TRAP_ENGINE;
                            refusal_reason <= REFUSAL_ENGINE;
                        end else begin
                            projection_executed <= 1'b1;
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
