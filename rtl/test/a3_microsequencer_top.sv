`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Verification top for the ABI 3.0 RTL: a thin wrapper around the design's
// own control-plane top, rtl/abi3/ot_a3_device_top.sv, plus the memories it
// presents as abstract store boundaries.  Both the Icarus testbench
// (rtl/test/tb_a3_microsequencer.sv, rtl/test/tb_a3_deployment.sv) and the
// C++ harnesses under Verilator (rtl/test/a3_microsequencer_harness.cpp,
// rtl/test/a3_deployment_harness.cpp) instantiate this module and read the
// same generated vector files, so the two simulators exercise identical RTL
// through independently written checkers.
//
// This wrapper holds no image and runs no $readmemh
// (docs/CHIP_ARCHITECTURE_DESIGN.md section 13 item 12).  The program store,
// the descriptor store and the runtime symbol file are written through the
// design's own host load path (host_*), and the program header is streamed
// through the design's admission beat port (hdr_in_*), by the checker acting
// as the management processor (sections 2.7 and 9.2).  What the wrapper
// owns is exactly what a testbench legitimately owns: the arrays behind the
// three store boundaries, and nothing that decides.
//
// The store models are the synchronous single-port macros of the vehicle
// memory plan (section 11.2): a read presents the row one cycle later and
// holds it, a write lands one 32-bit lane.  The issue record store's payload
// is the third such macro: 32 entries x 8 lanes x 512 bits (the vehicle's
// 8 x 512 B is the sky130 column; the design's 32 entries are modelled here
// so every outstanding operation has its own record), written one lane at a
// time by the sequencer as it publishes an operation's resolved views and
// its counter snapshot, read back by the sequencer only to freeze the
// counters after an asynchronous engine fault.
//
// The engine port has two phases.  The checker accepts an issue
// (issue_valid && issue_ready) and later reports its completion
// (complete_valid with the slot the issue carried); every dispatchable
// operation is a recording no-op on the checker side, completed after a
// checker-chosen delay, in a checker-chosen order.
// ---------------------------------------------------------------------------
module ot_a3_microsequencer_top
    import ot_a3_pkg::*;
#(
    parameter integer PROGRAM_WORDS = 2048,
    parameter integer DESC_WORDS    = 4096,
    parameter integer STATE_COMPAT  = 1
) (
    input  wire        clk,
    input  wire        rst_n,

    // -- program header admission (host stream) --------------------------
    input  wire        hdr_in_valid,
    input  wire        hdr_in_start,
    input  wire [31:0] hdr_in_word,
    output wire        header_done,
    output wire        header_legal,
    output wire [3:0]  header_error,
    output wire [15:0] header_trap_class,
    output wire [31:0] header_instruction_count,
    output wire [31:0] header_entrypoint_count,
    output wire [63:0] header_max_retired_work,
    output wire [31:0] header_entrypoint_descriptor,

    // -- host load path: program store, descriptor store, symbol file -----
    input  wire        host_we,
    input  wire [1:0]  host_sel,
    input  wire [31:0] host_row,
    input  wire [5:0]  host_lane,
    input  wire [31:0] host_wdata,
    output wire        host_ready,
    output wire        host_write_refused,

    // -- transaction ----------------------------------------------------
    input  wire        start,
    input  wire [31:0] cfg_program_base,
    input  wire [31:0] cfg_instruction_count,
    input  wire [31:0] cfg_entry_pc,
    input  wire [31:0] cfg_desc_base,
    input  wire [31:0] cfg_desc_count,
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

    // -- engine issue: queue acceptance -------------------------------
    input  wire        issue_ready,
    output wire        issue_valid,
    output wire [7:0]  issue_family,
    output wire [7:0]  issue_sub,
    output wire [31:0] issue_descriptor_id,
    output wire [31:0] issue_index,
    output wire [31:0] issue_serial,
    output wire [4:0]  issue_slot,
    output wire [4:0]  issue_queue,

    // -- engine completion: any order, one per cycle -----------------
    input  wire        complete_valid,
    input  wire [4:0]  complete_slot,
    input  wire        complete_fault,
    input  wire [15:0] complete_trap_class,
    // The completion record's EOS reason byte.  This vehicle drives no
    // selection engine, so its checkers leave it at zero and the device's
    // session never retires; the port exists so the boundary is complete.
    input  wire [7:0]  complete_eos_reason,

    // -- resolved operand tensor views (A4 and A13) ---------------------
    output wire        view_valid,
    output wire [31:0] view_descriptor_id,
    output wire [2:0]  view_slot,
    output wire [31:0] view_extent,
    output wire [7:0]  view_extent_axis,
    output wire [63:0] view_element_offset,
    output wire [7:0]  view_rank,
    output wire [4:0]  view_irs_slot,
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
    output wire        state_apply_overflow,

    // -- run-ahead observation ------------------------------------------
    output wire [5:0]  dbg_outstanding,
    output wire [5:0]  dbg_max_outstanding,
    output wire [31:0] dbg_dep_stalls,
    output wire [31:0] dbg_wait_stalls,
    output wire        irs_protocol_error
);
    // The arrays behind the store boundaries.  Uninitialised: every row is
    // whatever the host wrote through host_*, and nothing else.
    reg [255:0]  program_mem [0:PROGRAM_WORDS-1];
    reg [1535:0] desc_mem    [0:DESC_WORDS-1];
    reg [511:0]  irs_payload_mem [0:A3_IRS_ENTRIES*8-1];

    // -- program store: one synchronous port, 8 x 32-bit lanes ------------
    wire         pstore_en;
    wire         pstore_we;
    wire [31:0]  pstore_addr;
    wire [2:0]   pstore_wlane;
    wire [31:0]  pstore_wdata;
    reg  [255:0] pstore_rdata;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pstore_rdata <= 256'd0;
        end else if (pstore_en) begin
            if (pstore_we)
                program_mem[pstore_addr[19:0]][pstore_wlane*32 +: 32]
                    <= pstore_wdata;
            else
                pstore_rdata <= program_mem[pstore_addr[19:0]];
        end
    end

    // -- descriptor store: one synchronous port, 48 x 32-bit lanes ---------
    wire          dstore_en;
    wire          dstore_we;
    wire [31:0]   dstore_addr;
    wire [5:0]    dstore_wlane;
    wire [31:0]   dstore_wdata;
    reg  [1535:0] dstore_rdata;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dstore_rdata <= 1536'd0;
        end else if (dstore_en) begin
            if (dstore_we)
                desc_mem[dstore_addr[19:0]][dstore_wlane*32 +: 32]
                    <= dstore_wdata;
            else
                dstore_rdata <= desc_mem[dstore_addr[19:0]];
        end
    end

    // -- issue record store payload: one synchronous port, 512-bit lanes ---
    wire         irs_we;
    wire [4:0]   irs_wslot;
    wire [2:0]   irs_wlane;
    wire [511:0] irs_wdata;
    wire         irs_re;
    wire [4:0]   irs_rslot;
    wire [2:0]   irs_rlane;
    reg  [511:0] irs_rdata;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            irs_rdata <= 512'd0;
        end else begin
            if (irs_we)
                irs_payload_mem[{irs_wslot, irs_wlane}] <= irs_wdata;
            if (irs_re)
                irs_rdata <= irs_payload_mem[{irs_rslot, irs_rlane}];
        end
    end

    ot_a3_device_top #(
        .PROGRAM_WORDS(PROGRAM_WORDS),
        .DESC_WORDS(DESC_WORDS),
        .STATE_COMPAT(STATE_COMPAT)
    ) device (
        .clk(clk),
        .rst_n(rst_n),
        .hdr_in_valid(hdr_in_valid),
        .hdr_in_start(hdr_in_start),
        .hdr_in_word(hdr_in_word),
        .header_done(header_done),
        .header_legal(header_legal),
        .header_error(header_error),
        .header_trap_class(header_trap_class),
        .header_instruction_count(header_instruction_count),
        .header_entrypoint_count(header_entrypoint_count),
        .header_max_retired_work(header_max_retired_work),
        .header_entrypoint_descriptor(header_entrypoint_descriptor),
        .host_we(host_we),
        .host_sel(host_sel),
        .host_row(host_row),
        .host_lane(host_lane),
        .host_wdata(host_wdata),
        .host_ready(host_ready),
        .host_write_refused(host_write_refused),
        .start(start),
        .cfg_program_base(cfg_program_base),
        .cfg_instruction_count(cfg_instruction_count),
        .cfg_entry_pc(cfg_entry_pc),
        .cfg_desc_base(cfg_desc_base),
        .cfg_desc_count(cfg_desc_count),
        .cfg_max_retired_work(cfg_max_retired_work),
        .cfg_state_count(cfg_state_count),
        .busy(busy),
        .done(done),
        .complete(complete),
        .trapped(trapped),
        .trap_class(trap_class),
        .first_fault_instruction(first_fault_instruction),
        .pstore_en(pstore_en),
        .pstore_we(pstore_we),
        .pstore_addr(pstore_addr),
        .pstore_wlane(pstore_wlane),
        .pstore_wdata(pstore_wdata),
        .pstore_rdata(pstore_rdata),
        .dstore_en(dstore_en),
        .dstore_we(dstore_we),
        .dstore_addr(dstore_addr),
        .dstore_wlane(dstore_wlane),
        .dstore_wdata(dstore_wdata),
        .dstore_rdata(dstore_rdata),
        .irs_we(irs_we),
        .irs_wslot(irs_wslot),
        .irs_wlane(irs_wlane),
        .irs_wdata(irs_wdata),
        .irs_re(irs_re),
        .irs_rslot(irs_rslot),
        .irs_rlane(irs_rlane),
        .irs_rdata(irs_rdata),
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
        .issue_serial(issue_serial),
        .issue_slot(issue_slot),
        .issue_queue(issue_queue),
        .complete_valid(complete_valid),
        .complete_slot(complete_slot),
        .complete_fault(complete_fault),
        .complete_trap_class(complete_trap_class),
        .complete_eos_reason(complete_eos_reason),
        .session_retired(),
        .session_eos_reason(),
        .count_transactions_refused_post_eos(),
        .view_valid(view_valid),
        .view_descriptor_id(view_descriptor_id),
        .view_slot(view_slot),
        .view_extent(view_extent),
        .view_extent_axis(view_extent_axis),
        .view_element_offset(view_element_offset),
        .view_rank(view_rank),
        .view_irs_slot(view_irs_slot),
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
        .dbg_loop_action(),
        .dbg_outstanding(dbg_outstanding),
        .dbg_max_outstanding(dbg_max_outstanding),
        .dbg_dep_stalls(dbg_dep_stalls),
        .dbg_wait_stalls(dbg_wait_stalls),
        .irs_protocol_error(irs_protocol_error)
    );
endmodule
