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
    parameter integer RESULT_WORDS = 98304,
    parameter integer MATMUL_WEIGHT_BYTES = 50331648,
    parameter integer ENABLE_EXACT_MULTICAST = 0
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
    input  wire [31:0] cfg_matmul_weight_object_0,
    input  wire [31:0] cfg_matmul_weight_base_0,
    input  wire [31:0] cfg_matmul_weight_object_1,
    input  wire [31:0] cfg_matmul_weight_base_1,
    input  wire [31:0] cfg_matmul_weight_object_2,
    input  wire [31:0] cfg_matmul_weight_base_2,
    input  wire [31:0] cfg_head_input_object_0,
    input  wire [31:0] cfg_head_input_base_0,
    input  wire [31:0] cfg_head_input_object_1,
    input  wire [31:0] cfg_head_input_base_1,
    input  wire [31:0] cfg_head_weight_object_0,
    input  wire [31:0] cfg_head_weight_base_0,
    input  wire [31:0] cfg_head_weight_object_1,
    input  wire [31:0] cfg_head_weight_base_1,
    input  wire [31:0] cfg_rope_input_object_0,
    input  wire [31:0] cfg_rope_input_base_0,
    input  wire [31:0] cfg_rope_input_object_1,
    input  wire [31:0] cfg_rope_input_base_1,
    input  wire [31:0] cfg_rope_coefficient_object,
    input  wire [31:0] cfg_rope_coefficient_base,
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
    output wire [31:0] head_rms_norm_launch_count,
    output wire [31:0] rope_launch_count,
    output wire [31:0] dma_transfer_launch_count,
    output wire [31:0] matmul_launch_count,
    output wire [31:0] multicast_launch_count,
    output wire [31:0] multicast_fault_count,
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

    output wire        multicast_remote_write_valid,
    output wire        multicast_remote_write_ready,
    output wire [31:0] multicast_remote_write_object_id,
    output wire [15:0] multicast_remote_write_participant,
    output wire [63:0] multicast_remote_write_offset,
    output wire [31:0] multicast_remote_write_data,
    output wire [7:0]  multicast_tree_source,
    output wire [31:0] multicast_source_read_count,
    output wire [31:0] multicast_source_stall_cycles,
    output wire [31:0] multicast_destination_stall_cycles,
    output wire [31:0] multicast_remote_write_count,
    output wire [31:0] multicast_messages_sent,
    output wire [31:0] multicast_messages_received,
    output wire [63:0] multicast_bytes_sent,
    output wire [63:0] multicast_bytes_received,
    output wire [31:0] multicast_payload_flits,
    output wire [31:0] multicast_wire_flits,
    output wire [31:0] multicast_replayed_flits,
    output wire [31:0] multicast_retry_events,
    output wire [31:0] multicast_credit_stall_cycles,
    output wire [31:0] multicast_crc_errors,
    output wire [31:0] multicast_sequence_errors,
    output wire [31:0] multicast_writes_after_completion,
    output wire        multicast_protocol_error,

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

    // Complete exact records cannot all be reconstructed from the 192-byte
    // descriptor-prefix image: TOPOLOGY is 256 bytes.  These side images are
    // the first, admitted vector of the retained multicast qualification and
    // are hash-bound by the overlay manifest and campaign.
    reg [31:0] multicast_communication_mem [0:47];
    reg [31:0] multicast_topology_mem [0:63];
    reg [31:0] multicast_local_object_mem [0:31];
    reg [31:0] multicast_remote_object_mem [0:31];
    reg [31:0] multicast_counter_mem [0:31];
    reg [31:0] multicast_source_mem [0:16383];
    reg [1535:0] multicast_communication_record;
    reg [2047:0] multicast_topology_record;
    reg [1023:0] multicast_local_object_record;
    reg [1023:0] multicast_remote_object_record;
    reg [1023:0] multicast_counter_record;

    integer clear_word;
    integer multicast_record_word;
    integer weight_file;
    integer weight_bytes_read;
    initial begin
        $readmemh("a3_program.hex", program_mem);
        $readmemh("a3_descriptor.hex", desc_mem);
        $readmemh("a3_symbol.hex", symbol_mem);
        $readmemh("p3_index.hex", index_mem);
        $readmemh("p3_source.hex", source_mem);
        multicast_communication_record = 1536'd0;
        multicast_topology_record = 2048'd0;
        multicast_local_object_record = 1024'd0;
        multicast_remote_object_record = 1024'd0;
        multicast_counter_record = 1024'd0;
        if (ENABLE_EXACT_MULTICAST != 0) begin
            $readmemh("p3_multicast_communication.hex",
                      multicast_communication_mem);
            $readmemh("p3_multicast_topology.hex", multicast_topology_mem);
            $readmemh("p3_multicast_local_object.hex",
                      multicast_local_object_mem);
            $readmemh("p3_multicast_remote_object.hex",
                      multicast_remote_object_mem);
            $readmemh("p3_multicast_counter.hex", multicast_counter_mem);
            $readmemh("p3_multicast_source.hex", multicast_source_mem);
            for (multicast_record_word = 0; multicast_record_word < 48;
                 multicast_record_word = multicast_record_word + 1)
                multicast_communication_record[
                    multicast_record_word*32 +: 32] =
                    multicast_communication_mem[multicast_record_word];
            for (multicast_record_word = 0; multicast_record_word < 64;
                 multicast_record_word = multicast_record_word + 1)
                multicast_topology_record[
                    multicast_record_word*32 +: 32] =
                    multicast_topology_mem[multicast_record_word];
            for (multicast_record_word = 0; multicast_record_word < 32;
                 multicast_record_word = multicast_record_word + 1) begin
                multicast_local_object_record[
                    multicast_record_word*32 +: 32] =
                    multicast_local_object_mem[multicast_record_word];
                multicast_remote_object_record[
                    multicast_record_word*32 +: 32] =
                    multicast_remote_object_mem[multicast_record_word];
                multicast_counter_record[multicast_record_word*32 +: 32] =
                    multicast_counter_mem[multicast_record_word];
            end
        end
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

    wire bridge_issue_ready;
    wire bridge_issue_fault;
    wire [15:0] bridge_issue_trap_class;
    wire exact_multicast_issue = (ENABLE_EXACT_MULTICAST != 0) && issue_valid &&
        (issue_family == 8'h90) && (issue_sub == 8'd3);
    reg multicast_issue_active;
    reg multicast_start;
    reg multicast_inject_crc;
    reg [31:0] multicast_observed_views;
    reg [31:0] views_at_last_response;
    reg [31:0] multicast_launch_count_q;
    reg [31:0] multicast_fault_count_q;
    wire multicast_busy;
    wire multicast_done;
    wire multicast_failed;
    wire [15:0] multicast_trap_class;
    wire [7:0] multicast_refusal_reason;

    assign issue_ready = exact_multicast_issue
        ? (multicast_issue_active && (multicast_done || multicast_failed))
        : bridge_issue_ready;
    assign issue_fault = exact_multicast_issue
        ? multicast_failed : bridge_issue_fault;
    assign issue_trap_class = exact_multicast_issue
        ? multicast_trap_class : bridge_issue_trap_class;

    assign response_valid = issue_valid && issue_ready;
    assign response_fault = issue_fault;
    assign response_trap_class = issue_trap_class;
    assign response_family = issue_family;
    assign response_sub = issue_sub;
    assign response_descriptor_id = issue_descriptor_id;
    assign response_index = issue_index;

    assign multicast_launch_count = multicast_launch_count_q;
    assign multicast_fault_count = multicast_fault_count_q;

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

    // -- exact DeepSeek ROM wafer multicast ----------------------------
    // LINK owns no tensor views.  Record the number actually observed since
    // the preceding completion and make the adapter admit zero rather than
    // assuming it.  Every other LINK shape remains routed to the ordinary
    // bridge and receives its existing fail-closed CAPABILITY response.
    wire multicast_response_fire = exact_multicast_issue && issue_ready;
    reg multicast_started_this_transaction;
    reg [31:0] multicast_service_cycle;
    reg [31:0] multicast_source_read_count_q;
    reg [31:0] multicast_source_stall_cycles_q;
    reg [31:0] multicast_destination_stall_cycles_q;
    reg [31:0] multicast_writes_after_completion_q;
    reg multicast_protocol_error_q;
    reg multicast_completed_seen;
    reg multicast_source_ready_phase;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            multicast_issue_active <= 1'b0;
            multicast_start <= 1'b0;
            multicast_inject_crc <= 1'b0;
            multicast_observed_views <= 32'd0;
            views_at_last_response <= 32'd0;
            multicast_launch_count_q <= 32'd0;
            multicast_fault_count_q <= 32'd0;
            multicast_started_this_transaction <= 1'b0;
            multicast_service_cycle <= 32'd0;
            multicast_completed_seen <= 1'b0;
        end else begin
            multicast_start <= 1'b0;
            multicast_inject_crc <= 1'b0;
            if (start) begin
                multicast_issue_active <= 1'b0;
                multicast_observed_views <= 32'd0;
                views_at_last_response <= 32'd0;
                multicast_launch_count_q <= 32'd0;
                multicast_fault_count_q <= 32'd0;
                multicast_started_this_transaction <= 1'b0;
                multicast_service_cycle <= 32'd0;
                multicast_completed_seen <= 1'b0;
            end else begin
                if (multicast_issue_active)
                    multicast_service_cycle <= multicast_service_cycle + 32'd1;
                if (!multicast_issue_active && exact_multicast_issue) begin
                    multicast_issue_active <= 1'b1;
                    multicast_started_this_transaction <= 1'b1;
                    multicast_observed_views <=
                        count_views_resolved - views_at_last_response;
                    // The endpoint is idle when this pulse is sampled.  One
                    // packet is corrupted and recovered through NAK/replay.
                    multicast_inject_crc <= 1'b1;
                    multicast_start <= 1'b1;
                end
                if (multicast_done)
                    multicast_completed_seen <= 1'b1;
                if (response_valid)
                    views_at_last_response <= count_views_resolved;
                if (multicast_response_fire) begin
                    multicast_issue_active <= 1'b0;
                    if (multicast_failed)
                        multicast_fault_count_q <=
                            multicast_fault_count_q + 32'd1;
                    else
                        multicast_launch_count_q <=
                            multicast_launch_count_q + 32'd1;
                end
            end
        end
    end

    function automatic [31:0] multicast_expected_word;
        input [13:0] index;
        reg [31:0] widened;
        begin
            widened = {18'd0, index};
            multicast_expected_word = 32'h9e37_79b9 ^
                (widened * 32'h045d_9f3b) ^ {index, index, index[3:0]};
        end
    endfunction

    wire multicast_source_read_valid_int;
    wire multicast_source_read_ready_int = multicast_issue_active &&
        multicast_source_ready_phase;
    wire [31:0] multicast_source_read_object_id_int;
    wire [63:0] multicast_source_read_offset_int;
    reg multicast_source_response_valid;
    wire multicast_source_response_ready;
    reg [31:0] multicast_source_response_data;

    assign multicast_source_read_count = multicast_source_read_count_q;
    assign multicast_source_stall_cycles = multicast_source_stall_cycles_q;
    assign multicast_destination_stall_cycles =
        multicast_destination_stall_cycles_q;
    assign multicast_writes_after_completion =
        multicast_writes_after_completion_q;
    assign multicast_protocol_error = multicast_protocol_error_q;

    // One-outstanding-response scratch-memory service.  Its nonzero contents
    // represent live object 365; they are intentionally not aliased to the
    // preceding DMA result, which belongs to a different object.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            multicast_source_response_valid <= 1'b0;
            multicast_source_response_data <= 32'd0;
            multicast_source_read_count_q <= 32'd0;
            multicast_source_stall_cycles_q <= 32'd0;
            multicast_destination_stall_cycles_q <= 32'd0;
            multicast_writes_after_completion_q <= 32'd0;
            multicast_protocol_error_q <= 1'b0;
            multicast_source_ready_phase <= 1'b0;
        end else begin
            if (start) begin
                multicast_source_response_valid <= 1'b0;
                multicast_source_response_data <= 32'd0;
                multicast_source_read_count_q <= 32'd0;
                multicast_source_stall_cycles_q <= 32'd0;
                multicast_destination_stall_cycles_q <= 32'd0;
                multicast_writes_after_completion_q <= 32'd0;
                multicast_protocol_error_q <= 1'b0;
                multicast_source_ready_phase <= 1'b0;
            end else begin
                if (!multicast_source_read_valid_int)
                    multicast_source_ready_phase <= 1'b0;
                else if (!multicast_source_ready_phase)
                    multicast_source_ready_phase <= 1'b1;
                else if (multicast_source_read_ready_int)
                    multicast_source_ready_phase <= 1'b0;
                if (multicast_source_response_valid &&
                    multicast_source_response_ready)
                    multicast_source_response_valid <= 1'b0;
                if (multicast_source_read_valid_int &&
                    !multicast_source_read_ready_int)
                    multicast_source_stall_cycles_q <=
                        multicast_source_stall_cycles_q + 32'd1;
                if (multicast_source_read_valid_int &&
                    multicast_source_read_ready_int) begin
                    multicast_source_read_count_q <=
                        multicast_source_read_count_q + 32'd1;
                    if ((multicast_source_read_object_id_int != 32'd365) ||
                        (multicast_source_read_offset_int[1:0] != 2'd0) ||
                        (multicast_source_read_offset_int >= 64'd65536) ||
                        (multicast_source_read_offset_int[15:2] !=
                         multicast_source_read_count_q[13:0])) begin
                        multicast_source_response_data <= 32'd0;
                        multicast_protocol_error_q <= 1'b1;
                    end else begin
                        multicast_source_response_data <=
                            multicast_source_mem[
                                multicast_source_read_offset_int[15:2]];
                    end
                    multicast_source_response_valid <= 1'b1;
                end
                if (multicast_remote_write_valid &&
                    !multicast_remote_write_ready)
                    multicast_destination_stall_cycles_q <=
                        multicast_destination_stall_cycles_q + 32'd1;
                if (multicast_remote_write_valid &&
                    multicast_remote_write_ready) begin
                    if ((multicast_remote_write_object_id != 32'd366) ||
                        (multicast_remote_write_offset[1:0] != 2'd0) ||
                        (multicast_remote_write_offset >= 64'd16777216) ||
                        (multicast_remote_write_participant !=
                         {8'd0, multicast_remote_write_offset[23:16]}) ||
                        (multicast_remote_write_data !=
                         multicast_expected_word(
                             multicast_remote_write_offset[15:2])))
                        multicast_protocol_error_q <= 1'b1;
                    if (multicast_completed_seen)
                        multicast_writes_after_completion_q <=
                            multicast_writes_after_completion_q + 32'd1;
                end
            end
        end
    end

    // One-cycle deterministic ready gaps exercise integration-level source
    // and destination backpressure while remaining far below endpoint timeout.
    assign multicast_remote_write_ready = multicast_issue_active &&
        (multicast_service_cycle[1:0] != 2'b00);

    wire [31:0] multicast_messages_sent_int;
    wire [31:0] multicast_messages_received_int;
    wire [63:0] multicast_bytes_sent_int;
    wire [63:0] multicast_bytes_received_int;
    wire [31:0] multicast_remote_write_count_int;
    wire [31:0] multicast_payload_flits_int;
    wire [31:0] multicast_wire_flits_int;
    wire [31:0] multicast_replayed_flits_int;
    wire [31:0] multicast_retry_events_int;
    wire [31:0] multicast_credit_stall_cycles_int;
    wire [31:0] multicast_crc_errors_int;
    wire [31:0] multicast_sequence_errors_int;

    assign multicast_messages_sent = multicast_started_this_transaction
        ? multicast_messages_sent_int : 32'd0;
    assign multicast_messages_received = multicast_started_this_transaction
        ? multicast_messages_received_int : 32'd0;
    assign multicast_bytes_sent = multicast_started_this_transaction
        ? multicast_bytes_sent_int : 64'd0;
    assign multicast_bytes_received = multicast_started_this_transaction
        ? multicast_bytes_received_int : 64'd0;
    assign multicast_remote_write_count = multicast_started_this_transaction
        ? multicast_remote_write_count_int : 32'd0;
    assign multicast_payload_flits = multicast_started_this_transaction
        ? multicast_payload_flits_int : 32'd0;
    assign multicast_wire_flits = multicast_started_this_transaction
        ? multicast_wire_flits_int : 32'd0;
    assign multicast_replayed_flits = multicast_started_this_transaction
        ? multicast_replayed_flits_int : 32'd0;
    assign multicast_retry_events = multicast_started_this_transaction
        ? multicast_retry_events_int : 32'd0;
    assign multicast_credit_stall_cycles =
        multicast_started_this_transaction
        ? multicast_credit_stall_cycles_int : 32'd0;
    assign multicast_crc_errors = multicast_started_this_transaction
        ? multicast_crc_errors_int : 32'd0;
    assign multicast_sequence_errors = multicast_started_this_transaction
        ? multicast_sequence_errors_int : 32'd0;

    generate
        if (ENABLE_EXACT_MULTICAST != 0) begin : g_exact_multicast
            ot_a3_shipped_prefix_multicast_adapter_wrapper u_multicast (
                .clk(clk), .rst_n(rst_n), .start(multicast_start),
                .issue_pc(issue_index), .issue_major(issue_family),
                .issue_sub(issue_sub),
                .issue_descriptor_id(issue_descriptor_id),
                .observed_view_count(multicast_observed_views),
                .state_descriptor_count(cfg_state_count),
                .topology_descriptor_id(32'd0),
                .local_object_descriptor_id(32'd365),
                .remote_object_descriptor_id(32'd366),
                .counter_descriptor_id(32'd367),
                .communication_record(multicast_communication_record),
                .topology_record(multicast_topology_record),
                .local_object_record(multicast_local_object_record),
                .remote_object_record(multicast_remote_object_record),
                .counter_record(multicast_counter_record),
                .source_read_valid(multicast_source_read_valid_int),
                .source_read_ready(multicast_source_read_ready_int),
                .source_read_object_id(multicast_source_read_object_id_int),
                .source_read_offset(multicast_source_read_offset_int),
                .source_response_valid(multicast_source_response_valid),
                .source_response_ready(multicast_source_response_ready),
                .source_response_data(multicast_source_response_data),
                .source_response_error(1'b0),
                .remote_write_valid(multicast_remote_write_valid),
                .remote_write_ready(multicast_remote_write_ready),
                .remote_write_object_id(multicast_remote_write_object_id),
                .remote_write_participant(
                    multicast_remote_write_participant),
                .remote_write_offset(multicast_remote_write_offset),
                .remote_write_data(multicast_remote_write_data),
                .inject_crc_error(multicast_inject_crc),
                .busy(multicast_busy), .done(multicast_done),
                .failed(multicast_failed),
                .trap_class(multicast_trap_class),
                .refusal_reason(multicast_refusal_reason),
                .messages_sent(multicast_messages_sent_int),
                .messages_received(multicast_messages_received_int),
                .bytes_sent(multicast_bytes_sent_int),
                .bytes_received(multicast_bytes_received_int),
                .remote_write_count(multicast_remote_write_count_int),
                .payload_flits_delivered(multicast_payload_flits_int),
                .wire_flits_transmitted(multicast_wire_flits_int),
                .replayed_flits(multicast_replayed_flits_int),
                .retry_events(multicast_retry_events_int),
                .credit_stall_cycles(multicast_credit_stall_cycles_int),
                .crc_errors(multicast_crc_errors_int),
                .sequence_errors(multicast_sequence_errors_int),
                .tree_source(multicast_tree_source)
            );
        end else begin : g_no_exact_multicast
            assign multicast_source_read_valid_int = 1'b0;
            assign multicast_source_read_object_id_int = 32'd0;
            assign multicast_source_read_offset_int = 64'd0;
            assign multicast_source_response_ready = 1'b0;
            assign multicast_remote_write_valid = 1'b0;
            assign multicast_remote_write_object_id = 32'd0;
            assign multicast_remote_write_participant = 16'd0;
            assign multicast_remote_write_offset = 64'd0;
            assign multicast_remote_write_data = 32'd0;
            assign multicast_busy = 1'b0;
            assign multicast_done = 1'b0;
            assign multicast_failed = 1'b0;
            assign multicast_trap_class = 16'd0;
            assign multicast_refusal_reason = 8'd0;
            assign multicast_messages_sent_int = 32'd0;
            assign multicast_messages_received_int = 32'd0;
            assign multicast_bytes_sent_int = 64'd0;
            assign multicast_bytes_received_int = 64'd0;
            assign multicast_remote_write_count_int = 32'd0;
            assign multicast_payload_flits_int = 32'd0;
            assign multicast_wire_flits_int = 32'd0;
            assign multicast_replayed_flits_int = 32'd0;
            assign multicast_retry_events_int = 32'd0;
            assign multicast_credit_stall_cycles_int = 32'd0;
            assign multicast_crc_errors_int = 32'd0;
            assign multicast_sequence_errors_int = 32'd0;
            assign multicast_tree_source = 8'd0;
        end
    endgenerate

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
                if (out_addr < RESULT_WORDS)
                    result_mem[out_addr] <= out_data;
                else
                    result_write_oob <= 1'b1;
            end
            if (fault_seen &&
                (out_we || (multicast_remote_write_valid &&
                            multicast_remote_write_ready)))
                writes_after_fault <= writes_after_fault +
                    (out_we ? 32'd1 : 32'd0) +
                    ((multicast_remote_write_valid &&
                      multicast_remote_write_ready) ? 32'd1 : 32'd0);
            if (issue_valid && issue_ready && issue_fault)
                fault_seen <= 1'b1;
        end
    end

    assign result_read_data = (result_read_addr < RESULT_WORDS)
        ? result_mem[result_read_addr] : 32'd0;

    wire engine_busy;
    wire [31:0] bridge_real_launch_count;
    assign real_launch_count =
        bridge_real_launch_count + multicast_launch_count_q;
    ot_a3_engine_issue_bridge bridge (
        .clk(clk),
        .rst_n(rst_n),
        .clear(start),
        .issue_valid(issue_valid && !exact_multicast_issue),
        .issue_ready(bridge_issue_ready),
        .issue_fault(bridge_issue_fault),
        .issue_trap_class(bridge_issue_trap_class),
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
        .cfg_matmul_weight_object_0(cfg_matmul_weight_object_0),
        .cfg_matmul_weight_base_0(cfg_matmul_weight_base_0),
        .cfg_matmul_weight_object_1(cfg_matmul_weight_object_1),
        .cfg_matmul_weight_base_1(cfg_matmul_weight_base_1),
        .cfg_matmul_weight_object_2(cfg_matmul_weight_object_2),
        .cfg_matmul_weight_base_2(cfg_matmul_weight_base_2),
        .cfg_head_input_object_0(cfg_head_input_object_0),
        .cfg_head_input_base_0(cfg_head_input_base_0),
        .cfg_head_input_object_1(cfg_head_input_object_1),
        .cfg_head_input_base_1(cfg_head_input_base_1),
        .cfg_head_weight_object_0(cfg_head_weight_object_0),
        .cfg_head_weight_base_0(cfg_head_weight_base_0),
        .cfg_head_weight_object_1(cfg_head_weight_object_1),
        .cfg_head_weight_base_1(cfg_head_weight_base_1),
        .cfg_rope_input_object_0(cfg_rope_input_object_0),
        .cfg_rope_input_base_0(cfg_rope_input_base_0),
        .cfg_rope_input_object_1(cfg_rope_input_object_1),
        .cfg_rope_input_base_1(cfg_rope_input_base_1),
        .cfg_rope_coefficient_object(cfg_rope_coefficient_object),
        .cfg_rope_coefficient_base(cfg_rope_coefficient_base),
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
        .real_launch_count(bridge_real_launch_count),
        .dma_gather_launch_count(dma_gather_launch_count),
        .embedding_launch_count(embedding_launch_count),
        .rms_norm_launch_count(rms_norm_launch_count),
        .head_rms_norm_launch_count(head_rms_norm_launch_count),
        .rope_launch_count(rope_launch_count),
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
