`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Verification top for the ABI 3.0 RTL: a thin wrapper around the design's
// own control-plane top, rtl/abi3/ot_a3_device_top.sv, plus the memories it
// presents as abstract store boundaries.  Both the Icarus testbench
// (rtl/test/tb_a3_microsequencer.sv, rtl/test/tb_a3_deployment.sv) and the
// C++ harnesses under Verilator (rtl/test/a3_microsequencer_harness.cpp,
// rtl/test/a3_deployment_harness.cpp) instantiate this module and read the
// same generated vector files, so the two simulators exercise identical RTL
// through independently written checkers.  Its port list and parameters are
// the ones the checkers have always driven; what changed is that the
// admission block, the sequencer, the descriptor base/bound/fault logic and
// the symbol addressing now live in the design top, and this wrapper keeps
// only what a testbench legitimately owns: the arrays, their preload, the
// host-side header streaming, and the engine stub tie-offs.
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
//
// The store models below are the synchronous single-port macros of the
// vehicle memory plan: a read presents the row one cycle later and holds it,
// a write lands one 32-bit lane.  They are preloaded by $readmemh because the
// checkers own reset and start timing; the design's host load path is
// exercised by rtl/test/tb_a3_device_top_host_load.sv instead.
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

    // -- host-side header streaming --------------------------------------
    // The management processor's job: 64 beats from the header image into
    // the design's admission port, in_start with the first.
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

    // -- runtime symbol file (combinational read) ---------------------------
    wire [31:0] sym_addr;
    wire [31:0] sym_value = symbol_mem[sym_addr[19:0]];

    ot_a3_device_top #(
        .PROGRAM_WORDS(PROGRAM_WORDS),
        .DESC_WORDS(DESC_WORDS),
        .STATE_COMPAT(STATE_COMPAT)
    ) device (
        .clk(clk),
        .rst_n(rst_n),
        .hdr_in_valid(header_valid),
        .hdr_in_start(header_first),
        .hdr_in_word(header_data),
        .header_done(header_done),
        .header_legal(header_legal),
        .header_error(header_error),
        .header_trap_class(header_trap_class),
        .header_instruction_count(header_instruction_count),
        .header_entrypoint_count(header_entrypoint_count),
        .header_max_retired_work(header_max_retired_work),
        .header_entrypoint_descriptor(header_entrypoint_descriptor),
        // The stores are preloaded above; the host load path is idle here.
        .host_we(1'b0),
        .host_sel(1'b0),
        .host_row(32'd0),
        .host_lane(6'd0),
        .host_wdata(32'd0),
        .host_ready(),
        .host_write_refused(),
        .start(start),
        .cfg_program_base(cfg_program_base),
        .cfg_instruction_count(cfg_instruction_count),
        .cfg_entry_pc(cfg_entry_pc),
        .cfg_desc_base(cfg_desc_base),
        .cfg_desc_count(cfg_desc_count),
        .cfg_symbol_base(cfg_symbol_base),
        .cfg_symbol_mask(cfg_symbol_mask),
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
        .sym_addr(sym_addr),
        .sym_value(sym_value),
        .predicate_read_req(predicate_read_req),
        .predicate_read_object_id(predicate_read_object_id),
        .predicate_read_element_index(predicate_read_element_index),
        .predicate_read_valid(predicate_read_valid),
        .predicate_read_value(predicate_read_value),
        .predicate_read_trap_class(predicate_read_trap_class),
        .issue_valid(issue_valid),
        .issue_ready(issue_ready),
        // The standalone control-plane campaigns intentionally retain their
        // recording consumer: the checker drives issue_ready and every
        // dispatchable engine operation is a recording no-op.  The
        // shipped-prefix integration top supplies the real engine response
        // on these same ABI 3.0 sequencer ports.
        .issue_fault(1'b0),
        .issue_trap_class(16'd0),
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
