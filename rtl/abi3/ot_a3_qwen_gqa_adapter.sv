`timescale 1ns/1ps
// Exact ABI 3.0 PC38 adapter for Qwen3-8B GQA.
//
// The previously qualified KV-scatter adapter remains the single validator for
// the real ROM/HBM instruction, OPERATOR, TENSOR_VIEW, NUMERIC, object, and
// request records.  Its precise PC38 CAPABILITY boundary is an internal
// admission handshake here; only that exact boundary starts arithmetic.  Any
// integrity/descriptor/instruction refusal is returned unchanged and performs
// no memory read or output write.
module ot_a3_qwen_gqa_adapter #(
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
    input  wire [31:0]    cfg_query_base,
    input  wire [31:0]    cfg_key_base,
    input  wire [31:0]    cfg_value_base,
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
    output wire [31:0]    write_count,
    output wire [31:0]    score_multiply_count,
    output wire [31:0]    exponential_count,
    output wire [31:0]    value_multiply_count,
    output wire [31:0]    saturation_count,
    output reg            gqa_executed
);
    localparam [15:0] TRAP_NONE = 16'd0;
    localparam [15:0] TRAP_CAPABILITY = 16'd4;
    localparam [15:0] TRAP_ENGINE = 16'd8;
    localparam [7:0] REFUSAL_NONE = 8'd0;
    localparam [7:0] REFUSAL_CAPABILITY = 8'd4;
    localparam [7:0] REFUSAL_ENGINE = 8'd5;

    localparam [2:0] S_IDLE = 3'd0;
    localparam [2:0] S_VALIDATE_START = 3'd1;
    localparam [2:0] S_VALIDATE_WAIT = 3'd2;
    localparam [2:0] S_ENGINE_START = 3'd3;
    localparam [2:0] S_ENGINE_WAIT = 3'd4;
    localparam [2:0] S_FINISH = 3'd5;

    reg [2:0] state;
    reg [31:0] context_q;
    reg [31:0] query_base_q;
    reg [31:0] key_base_q;
    reg [31:0] value_base_q;
    reg [31:0] output_base_q;
    reg engine_invoked_q;

    wire validator_done;
    wire validator_failed;
    wire [15:0] validator_trap;
    wire [7:0] validator_refusal;
    wire [31:0] validator_records;
    wire [31:0] validator_writes;
    wire validator_gqa_boundary;
    wire validator_idx_rd_en;
    wire [31:0] validator_idx_rd_addr;
    wire validator_src_rd_en;
    wire [31:0] validator_src_rd_addr;
    wire validator_out_we;
    wire [31:0] validator_out_addr;
    wire [31:0] validator_out_data;

    // At PC38 the validator reaches admission without issuing any of these
    // legacy DMA ports.  Tying responses low also makes an accidental opcode
    // transition unable to read application memory through this wrapper.
    ot_a3_qwen_kv_scatter_adapter #(
        .MIN_CONTEXT(MIN_CONTEXT),
        .MAX_CONTEXT(MAX_CONTEXT)
    ) metadata_validator (
        .clk(clk), .rst_n(rst_n), .start(state == S_VALIDATE_START),
        .instruction_record(instruction_record),
        .instruction_index(instruction_index),
        .instruction_count(instruction_count),
        .operator_descriptor_id(operator_descriptor_id),
        .view0_descriptor_id(view0_descriptor_id),
        .view1_descriptor_id(view1_descriptor_id),
        .view2_descriptor_id(view2_descriptor_id),
        .view3_descriptor_id(view3_descriptor_id),
        .output_descriptor_id(output_descriptor_id),
        .numeric_descriptor_id(numeric_descriptor_id),
        .expected_object0(expected_object0),
        .expected_object1(expected_object1),
        .expected_object2(expected_object2),
        .expected_object3(expected_object3),
        .expected_output_object(expected_output_object),
        .operator_record(operator_record), .view0_record(view0_record),
        .view1_record(view1_record), .view2_record(view2_record),
        .view3_record(view3_record), .output_record(output_record),
        .numeric_record(numeric_record),
        .cfg_position_start(cfg_position_start),
        .cfg_context_length(cfg_context_length),
        .cfg_index_base(32'd0), .cfg_source_base(32'd0),
        .cfg_prior_base(32'd0), .cfg_output_base(32'd0),
        .idx_rd_en(validator_idx_rd_en),
        .idx_rd_addr(validator_idx_rd_addr), .idx_rd_data(32'd0),
        .src_rd_en(validator_src_rd_en),
        .src_rd_addr(validator_src_rd_addr), .src_rd_data(32'd0),
        .out_we(validator_out_we), .out_addr(validator_out_addr),
        .out_data(validator_out_data), .busy(), .done(validator_done),
        .failed(validator_failed), .trap_class(validator_trap),
        .refusal_reason(validator_refusal),
        .records_checked(validator_records), .moved_elements(),
        .indices_checked(), .write_count(validator_writes),
        .gqa_boundary(validator_gqa_boundary)
    );

    wire engine_done;
    wire engine_failed;
    wire [7:0] engine_error;
    wire [31:0] engine_memory_reads;
    wire [31:0] engine_writes;
    wire [31:0] engine_score_multiplies;
    wire [31:0] engine_exponentials;
    wire [31:0] engine_value_multiplies;
    wire [31:0] engine_saturations;
    wire engine_mem_req_valid;
    wire [31:0] engine_mem_req_addr;
    wire engine_out_valid;
    wire [31:0] engine_out_addr;
    wire [31:0] engine_out_data;
    ot_a3_qwen_gqa #(
        .MAX_CONTEXT(MAX_CONTEXT)
    ) engine (
        .clk(clk), .rst_n(rst_n), .start(state == S_ENGINE_START),
        //: Decode: one query row, ending at the context.  Tied rather
        //: than left unconnected -- a floating input is 0 or x by tool,
        //: and MAX_QUERY_SPAN=1 folds both away regardless.
        .cfg_query_span(32'd1),
        .cfg_first_position(context_q - 32'd1),
        .cfg_context_length(context_q), .cfg_query_base(query_base_q),
        .cfg_key_base(key_base_q), .cfg_value_base(value_base_q),
        .cfg_output_base(output_base_q),
        .mem_req_valid(engine_mem_req_valid), .mem_req_ready(mem_req_ready),
        .mem_req_addr(engine_mem_req_addr), .mem_rsp_valid(mem_rsp_valid),
        .mem_rsp_data(mem_rsp_data), .out_valid(engine_out_valid),
        .out_ready(out_ready), .out_addr(engine_out_addr),
        .out_data(engine_out_data),
        .busy(), .done(engine_done), .failed(engine_failed),
        .error_code(engine_error), .memory_read_count(engine_memory_reads),
        .output_write_count(engine_writes),
        .score_multiply_count(engine_score_multiplies),
        .exponential_count(engine_exponentials),
        .value_multiply_count(engine_value_multiplies),
        .saturation_count(engine_saturations)
    );
    assign mem_req_valid = engine_invoked_q && engine_mem_req_valid;
    assign mem_req_addr = engine_mem_req_addr;
    assign out_valid = engine_invoked_q && engine_out_valid;
    assign out_addr = engine_out_addr;
    assign out_data = engine_out_data;
    assign memory_read_count = engine_invoked_q ? engine_memory_reads : 0;
    assign write_count = engine_invoked_q ? engine_writes : 0;
    assign score_multiply_count = engine_invoked_q
        ? engine_score_multiplies : 0;
    assign exponential_count = engine_invoked_q ? engine_exponentials : 0;
    assign value_multiply_count = engine_invoked_q
        ? engine_value_multiplies : 0;
    assign saturation_count = engine_invoked_q ? engine_saturations : 0;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            context_q <= 0;
            query_base_q <= 0;
            key_base_q <= 0;
            value_base_q <= 0;
            output_base_q <= 0;
            engine_invoked_q <= 1'b0;
            busy <= 1'b0;
            done <= 1'b0;
            failed <= 1'b0;
            trap_class <= TRAP_NONE;
            refusal_reason <= REFUSAL_NONE;
            records_checked <= 0;
            gqa_executed <= 1'b0;
        end else begin
            done <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        context_q <= cfg_context_length;
                        query_base_q <= cfg_query_base;
                        key_base_q <= cfg_key_base;
                        value_base_q <= cfg_value_base;
                        output_base_q <= cfg_output_base;
                        engine_invoked_q <= 1'b0;
                        busy <= 1'b1;
                        failed <= 1'b0;
                        trap_class <= TRAP_NONE;
                        refusal_reason <= REFUSAL_NONE;
                        records_checked <= 0;
                        gqa_executed <= 1'b0;
                        state <= S_VALIDATE_START;
                    end
                end

                S_VALIDATE_START: state <= S_VALIDATE_WAIT;

                S_VALIDATE_WAIT: begin
                    if (validator_done) begin
                        records_checked <= validator_records;
                        if (validator_failed &&
                            validator_trap == TRAP_CAPABILITY &&
                            validator_refusal == REFUSAL_CAPABILITY &&
                            validator_gqa_boundary &&
                            validator_records == 7 &&
                            validator_writes == 0 &&
                            !validator_idx_rd_en &&
                            !validator_src_rd_en &&
                            !validator_out_we) begin
                            state <= S_ENGINE_START;
                        end else begin
                            failed <= 1'b1;
                            trap_class <= validator_trap;
                            refusal_reason <= validator_refusal;
                            state <= S_FINISH;
                        end
                    end
                end

                S_ENGINE_START: begin
                    engine_invoked_q <= 1'b1;
                    state <= S_ENGINE_WAIT;
                end

                S_ENGINE_WAIT: begin
                    if (engine_done) begin
                        if (engine_failed) begin
                            failed <= 1'b1;
                            trap_class <= TRAP_ENGINE;
                            refusal_reason <= REFUSAL_ENGINE;
                        end else begin
                            gqa_executed <= 1'b1;
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
