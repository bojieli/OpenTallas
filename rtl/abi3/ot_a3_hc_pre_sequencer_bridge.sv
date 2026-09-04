`timescale 1ns/1ps
// ABI 3.0 microsequencer integration for shipped DeepSeek HC_PRE.
//
// VECTOR.MHC issues are completed by ot_a3_hc_pre_shipped_adapter; all other
// issues are passed to the surrounding engine fabric unchanged.  Instruction,
// descriptor, symbol, predicate and tensor-memory services remain explicit
// ports, so this module does not hide a test-only fixed-latency memory model.
module ot_a3_hc_pre_sequencer_bridge (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          start,
    input  wire [31:0]   cfg_program_base,
    input  wire [31:0]   cfg_instruction_count,
    input  wire [31:0]   cfg_entry_pc,
    input  wire [63:0]   cfg_max_retired_work,
    input  wire [31:0]   cfg_state_count,

    output wire          imem_req,
    output wire [31:0]   imem_index,
    input  wire          imem_valid,
    input  wire [255:0]  imem_data,

    output wire          seq_desc_req,
    output wire [31:0]   seq_desc_id,
    input  wire          seq_desc_valid,
    input  wire          seq_desc_fault,
    input  wire [1535:0] seq_desc_data,

    output wire          hc_desc_req,
    output wire [31:0]   hc_desc_id,
    input  wire          hc_desc_valid,
    input  wire          hc_desc_fault,
    input  wire [1535:0] hc_desc_data,

    output wire [3:0]    sym_index,
    input  wire [31:0]   sym_value,
    input  wire          sym_bound,

    output wire          predicate_read_req,
    output wire [31:0]   predicate_read_object_id,
    output wire [31:0]   predicate_read_element_index,
    input  wire          predicate_read_valid,
    input  wire          predicate_read_value,
    input  wire [15:0]   predicate_read_trap_class,

    output wire          fallback_issue_valid,
    input  wire          fallback_issue_ready,
    input  wire          fallback_issue_fault,
    input  wire [15:0]   fallback_issue_trap_class,
    output wire [7:0]    fallback_issue_family,
    output wire [7:0]    fallback_issue_sub,
    output wire [31:0]   fallback_issue_descriptor_id,
    output wire [31:0]   fallback_issue_index,

    output wire          mem_read_valid,
    input  wire          mem_read_ready,
    output wire [31:0]   mem_read_object_id,
    output wire [63:0]   mem_read_element_offset,
    output wire [7:0]    mem_read_dtype,
    output wire [4:0]    mem_read_element_count,
    output wire [31:0]   mem_read_element_stride,
    input  wire          mem_response_valid,
    output wire          mem_response_ready,
    input  wire [255:0]  mem_response_data,
    input  wire          mem_response_error,

    output wire          mem_write_valid,
    input  wire          mem_write_ready,
    output wire [31:0]   mem_write_object_id,
    output wire [63:0]   mem_write_element_offset,
    output wire [31:0]   mem_write_data,

    output wire          busy,
    output wire          done,
    output wire          complete,
    output wire          trapped,
    output wire [15:0]   trap_class,
    output wire [31:0]   first_fault_instruction,
    output wire [31:0]   count_fetched,
    output wire [31:0]   count_retired,
    output wire [31:0]   count_predicated_off,
    output wire [31:0]   count_issued,
    output wire [31:0]   count_branches,
    output wire [31:0]   count_loop_iterations,
    output wire [31:0]   count_wait_events,
    output wire [31:0]   count_signals,
    output wire [31:0]   count_views_resolved,
    output wire          event_signal_error,
    output wire          state_apply_overflow,

    output wire          hc_issue_response,
    output wire          hc_issue_fault,
    output wire [15:0]   hc_issue_trap_class,
    output wire [31:0]   hc_descriptor_records_checked,
    output wire [31:0]   hc_resolved_views_captured,
    output wire [31:0]   hc_memory_read_count,
    output wire [31:0]   hc_memory_request_stall_cycles,
    output wire [31:0]   hc_memory_response_stall_cycles,
    output wire [31:0]   hc_output_write_count,
    output wire [31:0]   hc_output_write_stall_cycles,
    output wire          hc_arithmetic_executed,
    output wire [7:0]    hc_last_error_code,
    output wire [31:0]   hc_arithmetic_square_count,
    output wire [31:0]   hc_arithmetic_reduction_add_count,
    output wire [31:0]   hc_arithmetic_fma_count
);
    wire issue_valid;
    wire issue_ready;
    wire issue_fault;
    wire [15:0] issue_trap_class;
    wire [7:0] issue_family;
    wire [7:0] issue_sub;
    wire [31:0] issue_descriptor_id;
    wire [31:0] issue_index;
    wire [15:0] issue_flags;
    wire [31:0] issue_wait_set_id;
    wire [31:0] issue_signal_event_id;
    wire [31:0] issue_control_id;
    wire [31:0] issue_source_operation_id;
    wire view_valid;
    wire [31:0] view_descriptor_id;
    wire [2:0] view_slot;
    wire [31:0] view_extent;
    wire [7:0] view_extent_axis;
    wire [63:0] view_element_offset;
    wire [7:0] view_rank;
    wire [31:0] count_state_prepares;
    wire [31:0] count_state_commits;
    wire [31:0] count_state_discards;
    wire [31:0] count_state_reads;
    wire [31:0] count_state_generation_advances;
    wire [31:0] count_state_commits_applied;
    wire [31:0] count_state_rows_committed;
    wire [63:0] count_state_bytes_written;
    wire [3:0] loop_depth;

    wire route_hc = issue_valid &&
        (issue_family == 8'h30) && (issue_sub == 8'h09);
    wire hc_ready;
    wire hc_fault;
    wire [15:0] hc_trap;

    assign issue_ready = route_hc ? hc_ready : fallback_issue_ready;
    assign issue_fault = route_hc ? hc_fault : fallback_issue_fault;
    assign issue_trap_class = route_hc
        ? hc_trap : fallback_issue_trap_class;
    assign fallback_issue_valid = issue_valid && !route_hc;
    assign fallback_issue_family = issue_family;
    assign fallback_issue_sub = issue_sub;
    assign fallback_issue_descriptor_id = issue_descriptor_id;
    assign fallback_issue_index = issue_index;
    assign hc_issue_response = route_hc && hc_ready;
    assign hc_issue_fault = hc_fault;
    assign hc_issue_trap_class = hc_trap;

    ot_a3_microsequencer #(.STATE_COMPAT(0)) sequencer (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_program_base(cfg_program_base),
        .cfg_instruction_count(cfg_instruction_count),
        .cfg_entry_pc(cfg_entry_pc),
        .cfg_max_retired_work(cfg_max_retired_work),
        .cfg_state_count(cfg_state_count),
        .busy(busy), .done(done), .complete(complete), .trapped(trapped),
        .trap_class(trap_class),
        .first_fault_instruction(first_fault_instruction),
        .imem_req(imem_req), .imem_index(imem_index),
        .imem_valid(imem_valid), .imem_data(imem_data),
        .desc_req(seq_desc_req), .desc_id(seq_desc_id),
        .desc_valid(seq_desc_valid), .desc_fault(seq_desc_fault),
        .desc_data(seq_desc_data), .sym_index(sym_index),
        .sym_value(sym_value), .sym_bound(sym_bound),
        .predicate_read_req(predicate_read_req),
        .predicate_read_object_id(predicate_read_object_id),
        .predicate_read_element_index(predicate_read_element_index),
        .predicate_read_valid(predicate_read_valid),
        .predicate_read_value(predicate_read_value),
        .predicate_read_trap_class(predicate_read_trap_class),
        .issue_valid(issue_valid), .issue_ready(issue_ready),
        .issue_fault(issue_fault), .issue_trap_class(issue_trap_class),
        .issue_family(issue_family), .issue_sub(issue_sub),
        .issue_descriptor_id(issue_descriptor_id),
        .issue_index(issue_index), .issue_flags(issue_flags),
        .issue_wait_set_id(issue_wait_set_id),
        .issue_signal_event_id(issue_signal_event_id),
        .issue_control_id(issue_control_id),
        .issue_source_operation_id(issue_source_operation_id),
        .view_valid(view_valid), .view_descriptor_id(view_descriptor_id),
        .view_slot(view_slot), .view_extent(view_extent),
        .view_extent_axis(view_extent_axis),
        .view_element_offset(view_element_offset), .view_rank(view_rank),
        .count_views_resolved(count_views_resolved),
        .count_fetched(count_fetched), .count_retired(count_retired),
        .count_predicated_off(count_predicated_off),
        .count_issued(count_issued), .count_branches(count_branches),
        .count_loop_iterations(count_loop_iterations),
        .count_wait_events(count_wait_events), .count_signals(count_signals),
        .count_state_prepares(count_state_prepares),
        .count_state_commits(count_state_commits),
        .count_state_discards(count_state_discards),
        .count_state_reads(count_state_reads),
        .count_state_generation_advances(count_state_generation_advances),
        .count_state_commits_applied(count_state_commits_applied),
        .count_state_rows_committed(count_state_rows_committed),
        .count_state_bytes_written(count_state_bytes_written),
        .loop_depth(loop_depth), .event_signal_error(event_signal_error),
        .state_apply_overflow(state_apply_overflow),
        .dbg_decode_error(), .dbg_source_operation_id(),
        .dbg_wait_fault_event(), .dbg_loop_action()
    );

    ot_a3_hc_pre_shipped_adapter hc_adapter (
        .clk(clk), .rst_n(rst_n), .clear(start),
        .issue_valid(route_hc), .issue_ready(hc_ready),
        .issue_fault(hc_fault), .issue_trap_class(hc_trap),
        .issue_family(issue_family), .issue_sub(issue_sub),
        .issue_descriptor_id(issue_descriptor_id),
        .issue_index(issue_index), .issue_flags(issue_flags),
        .issue_wait_set_id(issue_wait_set_id),
        .issue_signal_event_id(issue_signal_event_id),
        .issue_control_id(issue_control_id),
        .issue_source_operation_id(issue_source_operation_id),
        .view_valid(view_valid), .view_descriptor_id(view_descriptor_id),
        .view_slot(view_slot), .view_extent(view_extent),
        .view_extent_axis(view_extent_axis),
        .view_element_offset(view_element_offset), .view_rank(view_rank),
        .desc_req(hc_desc_req), .desc_id(hc_desc_id),
        .desc_valid(hc_desc_valid), .desc_fault(hc_desc_fault),
        .desc_data(hc_desc_data), .mem_read_valid(mem_read_valid),
        .mem_read_ready(mem_read_ready),
        .mem_read_object_id(mem_read_object_id),
        .mem_read_element_offset(mem_read_element_offset),
        .mem_read_dtype(mem_read_dtype),
        .mem_read_element_count(mem_read_element_count),
        .mem_read_element_stride(mem_read_element_stride),
        .mem_response_valid(mem_response_valid),
        .mem_response_ready(mem_response_ready),
        .mem_response_data(mem_response_data),
        .mem_response_error(mem_response_error),
        .mem_write_valid(mem_write_valid),
        .mem_write_ready(mem_write_ready),
        .mem_write_object_id(mem_write_object_id),
        .mem_write_element_offset(mem_write_element_offset),
        .mem_write_data(mem_write_data), .busy(),
        .descriptor_records_checked(hc_descriptor_records_checked),
        .resolved_views_captured(hc_resolved_views_captured),
        .memory_read_count(hc_memory_read_count),
        .memory_request_stall_cycles(hc_memory_request_stall_cycles),
        .memory_response_stall_cycles(hc_memory_response_stall_cycles),
        .output_write_count(hc_output_write_count),
        .output_write_stall_cycles(hc_output_write_stall_cycles),
        .arithmetic_executed(hc_arithmetic_executed),
        .last_error_code(hc_last_error_code),
        .arithmetic_square_count(hc_arithmetic_square_count),
        .arithmetic_reduction_add_count(
            hc_arithmetic_reduction_add_count),
        .arithmetic_fma_count(hc_arithmetic_fma_count)
    );
endmodule
