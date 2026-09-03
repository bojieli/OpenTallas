`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Verification top for the exact shipped ABI 3.0 decode-prefix witness.
//
// Program, descriptor and symbol images are the same source-bound images used
// by the full shipped-deployment control-plane campaign.  Only the compact
// operand banks are new.  The sequencer resolves the deployed views, the
// issue bridge validates the deployed OPERATOR/TENSOR_VIEW/NUMERIC records,
// and the existing engine array performs the real DMA copies before replying.
// ---------------------------------------------------------------------------
module ot_a3_shipped_prefix_top #(
    parameter integer PROGRAM_WORDS = 4096,
    parameter integer DESC_WORDS = 8192,
    parameter integer SYMBOL_WORDS = 2048,
    parameter integer INDEX_WORDS = 64,
    parameter integer SOURCE_WORDS = 65536,
    parameter integer RESULT_WORDS = 69632,
    parameter integer MATMUL_WEIGHT_BYTES = 33554432
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [31:0] cfg_program_base,
    input  wire [31:0] cfg_instruction_count,
    input  wire [31:0] cfg_entry_pc,
    input  wire [31:0] cfg_desc_base,
    input  wire [31:0] cfg_desc_count,
    input  wire [31:0] cfg_symbol_base,
    input  wire [31:0] cfg_symbol_mask,
    input  wire [63:0] cfg_max_retired_work,
    input  wire [31:0] cfg_state_count,
    input  wire [31:0] cfg_index_base,
    input  wire [31:0] cfg_source_base,
    input  wire [31:0] cfg_source_launch_stride,
    input  wire [31:0] cfg_embedding_source_base,
    input  wire [31:0] cfg_rms_input_base,
    input  wire [31:0] cfg_rms_weight_base,
    input  wire [31:0] cfg_transfer_index_base,
    input  wire [31:0] cfg_transfer_source_base,
    input  wire [31:0] cfg_matmul_input_base,
    input  wire [31:0] cfg_matmul_weight_base,
    input  wire [31:0] cfg_output_base,

    output wire        busy,
    output wire        done,
    output wire        complete,
    output wire        trapped,
    output wire [15:0] trap_class,
    output wire [31:0] first_fault_instruction,
    output wire [31:0] count_fetched,
    output wire [31:0] count_retired,
    output wire [31:0] count_predicated_off,
    output wire [31:0] count_issued,
    output wire [31:0] count_branches,
    output wire [31:0] count_loop_iterations,
    output wire [31:0] count_wait_events,
    output wire [31:0] count_signals,
    output wire [31:0] count_views_resolved,
    output wire [31:0] count_state_prepares,
    output wire [31:0] count_state_commits,
    output wire [31:0] count_state_discards,
    output wire [31:0] count_state_reads,
    output wire [31:0] count_state_generation_advances,
    output wire [31:0] count_state_commits_applied,
    output wire [31:0] count_state_rows_committed,
    output wire [63:0] count_state_bytes_written,
    output wire        event_signal_error,
    output wire        state_apply_overflow,

    output wire [31:0] real_launch_count,
    output wire [31:0] dma_gather_launch_count,
    output wire [31:0] embedding_launch_count,
    output wire [31:0] rms_norm_launch_count,
    output wire [31:0] dma_transfer_launch_count,
    output wire [31:0] matmul_launch_count,
    output wire [31:0] capability_fault_count,
    output wire [31:0] descriptor_fault_count,
    output wire [31:0] engine_fault_count,
    output wire [31:0] last_response_index,
    output wire [7:0]  last_response_family,
    output wire [7:0]  last_response_sub,
    output wire [31:0] last_response_descriptor_id,
    output wire        response_valid,
    output wire        response_fault,
    output wire [15:0] response_trap_class,
    output wire [7:0]  response_family,
    output wire [7:0]  response_sub,
    output wire [31:0] response_descriptor_id,
    output wire [31:0] response_index,
    output wire [7:0]  engine_error_code,
    output wire [31:0] engine_result_count,
    output wire [31:0] engine_work_count,
    output reg  [31:0] output_write_count,
    output reg  [31:0] writes_after_fault,
    output reg         operand_read_oob,
    output reg         result_write_oob,

    input  wire [31:0] result_read_addr,
    output wire [31:0] result_read_data
);
    reg [255:0]  program_mem [0:PROGRAM_WORDS-1];
    reg [1535:0] desc_mem [0:DESC_WORDS-1];
    reg [31:0]   symbol_mem [0:SYMBOL_WORDS-1];
    reg [31:0]   index_mem [0:INDEX_WORDS-1];
    reg [31:0]   source_mem [0:SOURCE_WORDS-1];
    reg [31:0]   result_mem [0:RESULT_WORDS-1];
    reg [7:0]    matmul_weight_mem [0:MATMUL_WEIGHT_BYTES-1];

    integer clear_word;
    integer weight_file;
    integer weight_bytes_read;
    initial begin
        $readmemh("a3_program.hex", program_mem);
        $readmemh("a3_descriptor.hex", desc_mem);
        $readmemh("a3_symbol.hex", symbol_mem);
        $readmemh("p3_index.hex", index_mem);
        $readmemh("p3_source.hex", source_mem);
        weight_file = $fopen("p3_matmul_weight.bin", "rb");
        if (weight_file == 0)
            $fatal(1, "cannot open p3_matmul_weight.bin");
        weight_bytes_read = $fread(matmul_weight_mem, weight_file);
        if (weight_bytes_read != MATMUL_WEIGHT_BYTES)
            $fatal(1, "p3_matmul_weight.bin has %0d bytes, expected %0d",
                   weight_bytes_read, MATMUL_WEIGHT_BYTES);
        $fclose(weight_file);
        for (clear_word = 0; clear_word < RESULT_WORDS;
             clear_word = clear_word + 1)
            result_mem[clear_word] = 32'hdead_beef;
    end

    // -- sequencer instruction and descriptor ports --------------------
    wire imem_req;
    wire [31:0] imem_index;
    reg imem_valid;
    reg [255:0] imem_data;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            imem_valid <= 1'b0;
            imem_data <= 256'd0;
        end else begin
            imem_valid <= imem_req;
            if (imem_req)
                imem_data <= program_mem[imem_index[19:0]];
        end
    end

    wire seq_desc_req;
    wire [31:0] seq_desc_id;
    reg seq_desc_valid;
    reg seq_desc_fault;
    reg [1535:0] seq_desc_data;
    wire [32:0] seq_desc_absolute =
        {1'b0, cfg_desc_base} + {1'b0, seq_desc_id};
    wire seq_desc_oob = (seq_desc_id >= cfg_desc_count) ||
                         (seq_desc_absolute >= DESC_WORDS);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            seq_desc_valid <= 1'b0;
            seq_desc_fault <= 1'b0;
            seq_desc_data <= 1536'd0;
        end else begin
            seq_desc_valid <= seq_desc_req;
            if (seq_desc_req) begin
                seq_desc_fault <= seq_desc_oob;
                seq_desc_data <= seq_desc_oob
                    ? 1536'd0 : desc_mem[seq_desc_absolute[19:0]];
            end
        end
    end

    // -- independent descriptor read port for the engine bridge --------
    wire bridge_desc_req;
    wire [31:0] bridge_desc_id;
    reg bridge_desc_valid;
    reg bridge_desc_fault;
    reg [1535:0] bridge_desc_data;
    wire [32:0] bridge_desc_absolute =
        {1'b0, cfg_desc_base} + {1'b0, bridge_desc_id};
    wire bridge_desc_oob = (bridge_desc_id >= cfg_desc_count) ||
                            (bridge_desc_absolute >= DESC_WORDS);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bridge_desc_valid <= 1'b0;
            bridge_desc_fault <= 1'b0;
            bridge_desc_data <= 1536'd0;
        end else begin
            bridge_desc_valid <= bridge_desc_req;
            if (bridge_desc_req) begin
                bridge_desc_fault <= bridge_desc_oob;
                bridge_desc_data <= bridge_desc_oob
                    ? 1536'd0 : desc_mem[bridge_desc_absolute[19:0]];
            end
        end
    end

    wire [3:0] sym_index;
    wire [31:0] sym_addr = cfg_symbol_base + {28'd0, sym_index};
    wire [31:0] sym_value = symbol_mem[sym_addr[19:0]];
    wire sym_bound = cfg_symbol_mask[sym_index];

    wire issue_valid;
    wire issue_ready;
    wire issue_fault;
    wire [15:0] issue_trap_class;
    wire [7:0] issue_family;
    wire [7:0] issue_sub;
    wire [31:0] issue_descriptor_id;
    wire [31:0] issue_index;
    wire view_valid;
    wire [31:0] view_descriptor_id;
    wire [2:0] view_slot;
    wire [31:0] view_extent;
    wire [7:0] view_extent_axis;
    wire [63:0] view_element_offset;
    wire [7:0] view_rank;

    assign response_valid = issue_valid && issue_ready;
    assign response_fault = issue_fault;
    assign response_trap_class = issue_trap_class;
    assign response_family = issue_family;
    assign response_sub = issue_sub;
    assign response_descriptor_id = issue_descriptor_id;
    assign response_index = issue_index;

    ot_a3_microsequencer #(.STATE_COMPAT(0)) sequencer (
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .cfg_program_base(cfg_program_base),
        .cfg_instruction_count(cfg_instruction_count),
        .cfg_entry_pc(cfg_entry_pc),
        .cfg_max_retired_work(cfg_max_retired_work),
        .cfg_state_count(cfg_state_count),
        .busy(busy),
        .done(done),
        .complete(complete),
        .trapped(trapped),
        .trap_class(trap_class),
        .first_fault_instruction(first_fault_instruction),
        .imem_req(imem_req),
        .imem_index(imem_index),
        .imem_valid(imem_valid),
        .imem_data(imem_data),
        .desc_req(seq_desc_req),
        .desc_id(seq_desc_id),
        .desc_valid(seq_desc_valid),
        .desc_fault(seq_desc_fault),
        .desc_data(seq_desc_data),
        .sym_index(sym_index),
        .sym_value(sym_value),
        .sym_bound(sym_bound),
        .predicate_read_req(),
        .predicate_read_object_id(),
        .predicate_read_element_index(),
        .predicate_read_valid(1'b0),
        .predicate_read_value(1'b0),
        .predicate_read_trap_class(16'd0),
        .issue_valid(issue_valid),
        .issue_ready(issue_ready),
        .issue_fault(issue_fault),
        .issue_trap_class(issue_trap_class),
        .issue_family(issue_family),
        .issue_sub(issue_sub),
        .issue_descriptor_id(issue_descriptor_id),
        .issue_index(issue_index),
        .view_valid(view_valid),
        .view_descriptor_id(view_descriptor_id),
        .view_slot(view_slot),
        .view_extent(view_extent),
        .view_extent_axis(view_extent_axis),
        .view_element_offset(view_element_offset),
        .view_rank(view_rank),
        .count_views_resolved(count_views_resolved),
        .count_fetched(count_fetched),
        .count_retired(count_retired),
        .count_predicated_off(count_predicated_off),
        .count_issued(count_issued),
        .count_branches(count_branches),
        .count_loop_iterations(count_loop_iterations),
        .count_wait_events(count_wait_events),
        .count_signals(count_signals),
        .count_state_prepares(count_state_prepares),
        .count_state_commits(count_state_commits),
        .count_state_discards(count_state_discards),
        .count_state_reads(count_state_reads),
        .count_state_generation_advances(count_state_generation_advances),
        .count_state_commits_applied(count_state_commits_applied),
        .count_state_rows_committed(count_state_rows_committed),
        .count_state_bytes_written(count_state_bytes_written),
        .loop_depth(),
        .event_signal_error(event_signal_error),
        .state_apply_overflow(state_apply_overflow),
        .dbg_decode_error(),
        .dbg_source_operation_id(),
        .dbg_wait_fault_event(),
        .dbg_loop_action()
    );

    // -- compact operand banks and result memory ------------------------
    wire m0_rd_en, m1_rd_en, m2_rd_en, m3_rd_en;
    wire [31:0] m0_rd_addr, m1_rd_addr, m2_rd_addr, m3_rd_addr;
    reg [31:0] m0_rd_data, m1_rd_data, m2_rd_data, m3_rd_data;
    wire out_we;
    wire [31:0] out_addr;
    wire [31:0] out_data;
    wire m0_reads_result;
    wire m1_reads_result;
    wire m1_reads_matmul_weight;
    reg fault_seen;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            m0_rd_data <= 32'd0;
            m1_rd_data <= 32'd0;
            m2_rd_data <= 32'd0;
            m3_rd_data <= 32'd0;
            output_write_count <= 32'd0;
            writes_after_fault <= 32'd0;
            operand_read_oob <= 1'b0;
            result_write_oob <= 1'b0;
            fault_seen <= 1'b0;
        end else begin
            if (start) begin
                output_write_count <= 32'd0;
                writes_after_fault <= 32'd0;
                operand_read_oob <= 1'b0;
                result_write_oob <= 1'b0;
                fault_seen <= 1'b0;
            end
            if (m0_rd_en) begin
                if (m0_reads_result && (m0_rd_addr < RESULT_WORDS))
                    m0_rd_data <= result_mem[m0_rd_addr];
                else if (!m0_reads_result && (m0_rd_addr < INDEX_WORDS))
                    m0_rd_data <= index_mem[m0_rd_addr];
                else begin
                    m0_rd_data <= 32'd0;
                    operand_read_oob <= 1'b1;
                end
            end
            if (m1_rd_en) begin
                if (m1_reads_matmul_weight) begin
                    if (m1_rd_addr < (MATMUL_WEIGHT_BYTES / 2))
                        m1_rd_data <= {16'd0,
                            matmul_weight_mem[(m1_rd_addr << 1) + 32'd1],
                            matmul_weight_mem[m1_rd_addr << 1]};
                    else begin
                        m1_rd_data <= 32'd0;
                        operand_read_oob <= 1'b1;
                    end
                end
                else if (m1_reads_result && (m1_rd_addr < RESULT_WORDS))
                    m1_rd_data <= result_mem[m1_rd_addr];
                else if (!m1_reads_result && (m1_rd_addr < SOURCE_WORDS))
                    m1_rd_data <= source_mem[m1_rd_addr];
                else begin
                    m1_rd_data <= 32'd0;
                    operand_read_oob <= 1'b1;
                end
            end
            if (m2_rd_en) begin
                m2_rd_data <= 32'd0;
                // ot_a3_mac_lane drives both scale ports for every reduction
                // step.  This exact Qwen descriptor declares both operands
                // unscaled, so zero is the architectural don't-care responder
                // and no scale-object access took place.
                if (!m1_reads_matmul_weight)
                    operand_read_oob <= 1'b1;
            end
            if (m3_rd_en) begin
                m3_rd_data <= 32'd0;
                if (!m1_reads_matmul_weight)
                    operand_read_oob <= 1'b1;
            end
            if (out_we) begin
                output_write_count <= output_write_count + 32'd1;
                if (fault_seen)
                    writes_after_fault <= writes_after_fault + 32'd1;
                if (out_addr < RESULT_WORDS)
                    result_mem[out_addr] <= out_data;
                else
                    result_write_oob <= 1'b1;
            end
            if (issue_valid && issue_ready && issue_fault)
                fault_seen <= 1'b1;
        end
    end

    assign result_read_data = (result_read_addr < RESULT_WORDS)
        ? result_mem[result_read_addr] : 32'd0;

    wire engine_busy;
    ot_a3_engine_issue_bridge bridge (
        .clk(clk),
        .rst_n(rst_n),
        .clear(start),
        .issue_valid(issue_valid),
        .issue_ready(issue_ready),
        .issue_fault(issue_fault),
        .issue_trap_class(issue_trap_class),
        .issue_family(issue_family),
        .issue_sub(issue_sub),
        .issue_descriptor_id(issue_descriptor_id),
        .issue_index(issue_index),
        .view_valid(view_valid),
        .view_descriptor_id(view_descriptor_id),
        .view_slot(view_slot),
        .view_extent(view_extent),
        .view_extent_axis(view_extent_axis),
        .view_element_offset(view_element_offset),
        .view_rank(view_rank),
        .desc_req(bridge_desc_req),
        .desc_id(bridge_desc_id),
        .desc_valid(bridge_desc_valid),
        .desc_fault(bridge_desc_fault),
        .desc_data(bridge_desc_data),
        .cfg_index_base(cfg_index_base),
        .cfg_source_base(cfg_source_base),
        .cfg_source_launch_stride(cfg_source_launch_stride),
        .cfg_embedding_source_base(cfg_embedding_source_base),
        .cfg_rms_input_base(cfg_rms_input_base),
        .cfg_rms_weight_base(cfg_rms_weight_base),
        .cfg_transfer_index_base(cfg_transfer_index_base),
        .cfg_transfer_source_base(cfg_transfer_source_base),
        .cfg_matmul_input_base(cfg_matmul_input_base),
        .cfg_matmul_weight_base(cfg_matmul_weight_base),
        .cfg_output_base(cfg_output_base),
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
        .m0_reads_result(m0_reads_result),
        .m1_reads_result(m1_reads_result),
        .m1_reads_matmul_weight(m1_reads_matmul_weight),
        .engine_busy(engine_busy),
        .engine_error_code(engine_error_code),
        .engine_result_count(engine_result_count),
        .engine_work_count(engine_work_count),
        .real_launch_count(real_launch_count),
        .dma_gather_launch_count(dma_gather_launch_count),
        .embedding_launch_count(embedding_launch_count),
        .rms_norm_launch_count(rms_norm_launch_count),
        .dma_transfer_launch_count(dma_transfer_launch_count),
        .matmul_launch_count(matmul_launch_count),
        .capability_fault_count(capability_fault_count),
        .descriptor_fault_count(descriptor_fault_count),
        .engine_fault_count(engine_fault_count),
        .last_response_index(last_response_index),
        .last_response_family(last_response_family),
        .last_response_sub(last_response_sub),
        .last_response_descriptor_id(last_response_descriptor_id)
    );
endmodule
