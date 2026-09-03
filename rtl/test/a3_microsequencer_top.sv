`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Verification top for the ABI 3.0 RTL: memories plus the two admission and
// execution blocks under test.  Both the Icarus testbench
// (rtl/test/tb_a3_microsequencer.sv) and the Verilator C++ harness
// (rtl/test/a3_microsequencer_harness.cpp) instantiate this module and read the
// same generated vector files, so the two simulators exercise identical RTL
// through independently written checkers.
//
// Memory images are produced by tools/build_abi3_rtl_vectors.py directly from
// real ABI 3.0 deployments built with runtime.abi3.builder.DeploymentBuilder:
//
//   a3_program.hex     256-bit words: every program body, instruction records
//   a3_header.hex       32-bit words: 64 per case, the 256-byte program header
//   a3_descriptor.hex 1536-bit words: descriptor header + both payload blocks
//   a3_symbol.hex       32-bit words: 16 runtime symbols per case
//
// The descriptor image keeps the first 192 bytes of each record: the 64-byte
// header plus both 64-byte payload blocks.  A 128-byte prefix was enough while
// the sequencer only read control descriptors, but a TENSOR_VIEW payload is 128
// bytes and its amendment-A4 dynamic terms start at payload offset 72, so view
// resolution needs the second block.  Descriptor record CRC is still not
// re-checked here; it belongs to a descriptor-admission block that owns whole
// records.
// ---------------------------------------------------------------------------
module ot_a3_microsequencer_top
    import ot_a3_pkg::*;
#(
    parameter integer PROGRAM_WORDS = 2048,
    parameter integer HEADER_WORDS  = 8192,
    parameter integer DESC_WORDS    = 4096,
    parameter integer SYMBOL_WORDS  = 2048,
    parameter integer STATE_COMPAT  = 1
) (
    input  wire        clk,
    input  wire        rst_n,

    // -- program header admission --------------------------------------
    input  wire        header_start,
    input  wire [31:0] cfg_header_base,
    output wire        header_done,
    output wire        header_legal,
    output wire [3:0]  header_error,
    output wire [15:0] header_trap_class,
    output wire [31:0] header_instruction_count,
    output wire [31:0] header_entrypoint_count,
    output wire [63:0] header_max_retired_work,
    output wire [31:0] header_entrypoint_descriptor,

    // -- transaction ----------------------------------------------------
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

    output wire        busy,
    output wire        done,
    output wire        complete,
    output wire        trapped,
    output wire [15:0] trap_class,
    output wire [31:0] first_fault_instruction,

    // -- data-dependent predicate result ------------------------------
    output wire        predicate_read_req,
    output wire [31:0] predicate_read_object_id,
    output wire [31:0] predicate_read_element_index,
    input  wire        predicate_read_valid,
    input  wire        predicate_read_value,
    input  wire [15:0] predicate_read_trap_class,

    // -- engine issue ---------------------------------------------------
    input  wire        issue_ready,
    output wire        issue_valid,
    output wire [7:0]  issue_family,
    output wire [7:0]  issue_sub,
    output wire [31:0] issue_descriptor_id,
    output wire [31:0] issue_index,

    // -- resolved operand tensor views (A4 and A13) ---------------------
    output wire        view_valid,
    output wire [31:0] view_descriptor_id,
    output wire [2:0]  view_slot,
    output wire [31:0] view_extent,
    output wire [7:0]  view_extent_axis,
    output wire [63:0] view_element_offset,
    output wire [7:0]  view_rank,
    output wire [31:0] count_views_resolved,

    // -- accounting -----------------------------------------------------
    output wire [31:0] count_fetched,
    output wire [31:0] count_retired,
    output wire [31:0] count_predicated_off,
    output wire [31:0] count_issued,
    output wire [31:0] count_branches,
    output wire [31:0] count_loop_iterations,
    output wire [31:0] count_wait_events,
    output wire [31:0] count_signals,
    output wire [31:0] count_state_prepares,
    output wire [31:0] count_state_commits,
    output wire [31:0] count_state_discards,
    output wire [31:0] count_state_reads,
    output wire [31:0] count_state_generation_advances,
    output wire [31:0] count_state_commits_applied,
    output wire [31:0] count_state_rows_committed,
    output wire [63:0] count_state_bytes_written,
    output wire [3:0]  loop_depth,
    output wire        event_signal_error,
    output wire        state_apply_overflow
);
    reg [255:0]  program_mem [0:PROGRAM_WORDS-1];
    reg [31:0]   header_mem  [0:HEADER_WORDS-1];
    reg [1535:0] desc_mem    [0:DESC_WORDS-1];
    reg [31:0]   symbol_mem  [0:SYMBOL_WORDS-1];

    initial begin
        $readmemh("a3_program.hex", program_mem);
        $readmemh("a3_header.hex", header_mem);
        $readmemh("a3_descriptor.hex", desc_mem);
        $readmemh("a3_symbol.hex", symbol_mem);
    end

    // -- header streaming -----------------------------------------------
    reg        header_active;
    reg [6:0]  header_word;
    reg [31:0] header_base;
    reg        header_valid;
    reg        header_first;
    reg [31:0] header_data;
    wire [31:0] header_next_addr = header_base + {25'd0, header_word} + 32'd1;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            header_active <= 1'b0;
            header_word <= 7'd0;
            header_base <= 32'd0;
            header_valid <= 1'b0;
            header_first <= 1'b0;
            header_data <= 32'd0;
        end else begin
            header_valid <= 1'b0;
            header_first <= 1'b0;
            if (header_start && !header_active) begin
                header_active <= 1'b1;
                header_word <= 7'd0;
                header_base <= cfg_header_base;
                header_valid <= 1'b1;
                header_first <= 1'b1;
                header_data <= header_mem[cfg_header_base[19:0]];
            end else if (header_active) begin
                header_valid <= 1'b1;
                header_word <= header_word + 7'd1;
                header_data <= header_mem[header_next_addr[19:0]];
                if (header_word == 7'd62)
                    header_active <= 1'b0;
            end
        end
    end

    ot_a3_program_header header (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(header_valid),
        .in_start(header_first),
        .in_word(header_data),
        .out_valid(header_done),
        .out_legal(header_legal),
        .out_error(header_error),
        .out_trap_class(header_trap_class),
        .out_abi_major(),
        .out_abi_minor(),
        .out_flags(),
        .out_instruction_count(header_instruction_count),
        .out_entrypoint_count(header_entrypoint_count),
        .out_max_retired_work(header_max_retired_work),
        .out_watchdog_class(),
        .out_entrypoint_table_descriptor(header_entrypoint_descriptor),
        .out_signature_descriptor()
    );

    // -- instruction memory port -----------------------------------------
    wire         imem_req;
    wire [31:0]  imem_index;
    reg          imem_valid;
    reg  [255:0] imem_data;

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

    // -- descriptor store port --------------------------------------------
    wire         desc_req;
    wire [31:0]  desc_id;
    reg          desc_valid;
    reg          desc_fault;
    reg  [1535:0] desc_data;
    wire [32:0]  desc_absolute = {1'b0, cfg_desc_base} + {1'b0, desc_id};
    wire         desc_out_of_range = (desc_id >= cfg_desc_count) ||
                                     (desc_absolute >= DESC_WORDS);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            desc_valid <= 1'b0;
            desc_fault <= 1'b0;
            desc_data <= 1536'd0;
        end else begin
            desc_valid <= desc_req;
            if (desc_req) begin
                desc_fault <= desc_out_of_range;
                desc_data <= desc_out_of_range
                           ? 1536'd0
                           : desc_mem[desc_absolute[19:0]];
            end
        end
    end

    // -- runtime symbol file -----------------------------------------------
    wire [3:0]  sym_index;
    wire [31:0] sym_addr = cfg_symbol_base + {28'd0, sym_index};
    wire [31:0] sym_value = symbol_mem[sym_addr[19:0]];
    wire        sym_bound = cfg_symbol_mask[sym_index];

    ot_a3_microsequencer #(
        .STATE_COMPAT(STATE_COMPAT)
    ) sequencer (
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
        .desc_req(desc_req),
        .desc_id(desc_id),
        .desc_valid(desc_valid),
        .desc_fault(desc_fault),
        .desc_data(desc_data),
        .sym_index(sym_index),
        .sym_value(sym_value),
        .sym_bound(sym_bound),
        .predicate_read_req(predicate_read_req),
        .predicate_read_object_id(predicate_read_object_id),
        .predicate_read_element_index(predicate_read_element_index),
        .predicate_read_valid(predicate_read_valid),
        .predicate_read_value(predicate_read_value),
        .predicate_read_trap_class(predicate_read_trap_class),
        .issue_valid(issue_valid),
        .issue_ready(issue_ready),
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
        .loop_depth(loop_depth),
        .event_signal_error(event_signal_error),
        .state_apply_overflow(state_apply_overflow),
        .dbg_decode_error(),
        .dbg_source_operation_id(),
        .dbg_wait_fault_event(),
        .dbg_loop_action()
    );
endmodule
