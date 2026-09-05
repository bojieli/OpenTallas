`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 device top: the synthesisable control plane of one node.
//
// This is the module docs/CHIP_ARCHITECTURE_DESIGN.md section 11.4 item 4
// names -- the design-side replacement for the verification tops
// rtl/test/a3_microsequencer_top.sv and rtl/test/a3_shipped_prefix_top.sv,
// which from this commit on are thin wrappers around it.  In this first form
// the engines are still stubbed: the engine issue port, the predicate service
// port and the resolved-view port are top-level ports, so the checker (or the
// shipped-prefix engine bridge) that answered them before answers them now,
// and the control plane crosses from testbench to design with zero change in
// observation (section 11.6, gate L1-CP).  The asynchronous front end (issue
// record store, dependence table, widened scoreboard, resolver bank, shared
// divider) is the second half and is not here.
//
// What is design and what is not.  Everything in this module is synthesisable
// and owned by the design: the program-header admission block, the
// microsequencer with its decoder, loop stack, scoreboard, predicate unit and
// one view-resolver lane, the descriptor base/bound/fault logic of section
// 3.4, the symbol-file addressing, and the host load path through which the
// management processor writes the two control stores (section 3.4: "written
// only by the management processor").  The stores themselves are presented as
// abstract macro boundaries, the asap7 column of the vehicle memory plan
// (section 11.2): a 4 KiB program store (vehicle default 128 rows x 32 B) and
// a 64 KiB descriptor store (vehicle default 256 rows of which the RTL reads
// the 192-byte record prefix), each a single synchronous port ganged from
// 32-bit macros -- a read returns the whole row one cycle later, a write lands
// one 32-bit lane.  Their geometry stays parametric because the L1-CP vector
// image concatenates four deployments (2,763 program rows, 7,140 descriptor
// rows) and DeepSeek-V4-Flash alone needs 1,312 instructions and 3,841
// records: the campaigns override to 4096 / 8192 exactly as the shared
// verification top always has.  No memory is loaded by this module: the
// wrapper that owns the arrays preloads them (verification) or the management
// processor writes them through host_* (design).
//
// The package is referenced by scope, never wildcard-imported [OI-43].
// ---------------------------------------------------------------------------
module ot_a3_device_top #(
    // Vehicle store geometry (docs/CHIP_ARCHITECTURE_DESIGN.md section 11.2):
    // program store 4 KiB = 128 instruction rows; descriptor store 64 KiB =
    // 256 rows at the 256-byte port width.  Only the descriptor bound check
    // and the host-path bound checks read these; the arrays live outside.
    parameter integer PROGRAM_WORDS = 128,
    parameter integer DESC_WORDS    = 256,
    // 1 elaborates the compatibility STATE controller (the sibling
    // microsequencer campaign); 0 is the production profile every shipped
    // deployment campaign runs.
    parameter integer STATE_COMPAT  = 1
) (
    input  wire          clk,
    input  wire          rst_n,

    // -- host: program-header admission --------------------------------
    // The management processor streams the 256-byte header as 64 x 32-bit
    // beats, in_start with the first; header_done pulses once after the last.
    input  wire          hdr_in_valid,
    input  wire          hdr_in_start,
    input  wire [31:0]   hdr_in_word,
    output wire          header_done,
    output wire          header_legal,
    output wire [3:0]    header_error,
    output wire [15:0]   header_trap_class,
    output wire [31:0]   header_instruction_count,
    output wire [31:0]   header_entrypoint_count,
    output wire [63:0]   header_max_retired_work,
    output wire [31:0]   header_entrypoint_descriptor,

    // -- host: control-store load path ---------------------------------
    // One 32-bit lane of one row per cycle into the program store
    // (host_sel = 0, lanes 0..7) or the descriptor store (host_sel = 1,
    // lanes 0..47).  Accepted only while no transaction runs (host_ready);
    // a write offered while busy or outside the store is dropped and
    // host_write_refused stays set until reset, so a load that was not
    // taken cannot pass for one that was.
    input  wire          host_we,
    input  wire          host_sel,
    input  wire [31:0]   host_row,
    input  wire [5:0]    host_lane,
    input  wire [31:0]   host_wdata,
    output wire          host_ready,
    output reg           host_write_refused,

    // -- transaction ----------------------------------------------------
    input  wire          start,
    input  wire [31:0]   cfg_program_base,
    input  wire [31:0]   cfg_instruction_count,
    input  wire [31:0]   cfg_entry_pc,
    input  wire [31:0]   cfg_desc_base,
    input  wire [31:0]   cfg_desc_count,
    input  wire [31:0]   cfg_symbol_base,
    input  wire [31:0]   cfg_symbol_mask,
    input  wire [63:0]   cfg_max_retired_work,
    input  wire [31:0]   cfg_state_count,

    output wire          busy,
    output wire          done,
    output wire          complete,
    output wire          trapped,
    output wire [15:0]   trap_class,
    output wire [31:0]   first_fault_instruction,

    // -- program store boundary (one synchronous port) ------------------
    // pstore_en && !pstore_we: pstore_rdata presents row pstore_addr in the
    // next cycle and holds it until the next read.  pstore_en && pstore_we:
    // lane pstore_wlane of row pstore_addr takes pstore_wdata.
    output wire          pstore_en,
    output wire          pstore_we,
    output wire [31:0]   pstore_addr,
    output wire [2:0]    pstore_wlane,
    output wire [31:0]   pstore_wdata,
    input  wire [255:0]  pstore_rdata,

    // -- descriptor store boundary (one synchronous port) ---------------
    // Same contract; the row is the 192-byte record prefix (64-byte header
    // plus both 64-byte payload blocks) the sequencer reads.
    output wire          dstore_en,
    output wire          dstore_we,
    output wire [31:0]   dstore_addr,
    output wire [5:0]    dstore_wlane,
    output wire [31:0]   dstore_wdata,
    input  wire [1535:0] dstore_rdata,

    // -- runtime symbol file boundary (combinational read) -------------
    // sym_addr = cfg_symbol_base + symbol index; the bound bit is
    // cfg_symbol_mask[index] and never leaves this module.
    output wire [31:0]   sym_addr,
    input  wire [31:0]   sym_value,

    // -- data-dependent predicate service ------------------------------
    output wire          predicate_read_req,
    output wire [31:0]   predicate_read_object_id,
    output wire [31:0]   predicate_read_element_index,
    input  wire          predicate_read_valid,
    input  wire          predicate_read_value,
    input  wire [15:0]   predicate_read_trap_class,

    // -- engine issue: ready is completion, not queue acceptance --------
    output wire          issue_valid,
    input  wire          issue_ready,
    input  wire          issue_fault,
    input  wire [15:0]   issue_trap_class,
    output wire [7:0]    issue_family,
    output wire [7:0]    issue_sub,
    output wire [31:0]   issue_descriptor_id,
    output wire [31:0]   issue_index,

    // -- resolved operand tensor views (A4, A13, A18) -------------------
    output wire          view_valid,
    output wire [31:0]   view_descriptor_id,
    output wire [2:0]    view_slot,
    output wire [31:0]   view_extent,
    output wire [7:0]    view_extent_axis,
    output wire [63:0]   view_element_offset,
    output wire [7:0]    view_rank,
    output wire [31:0]   count_views_resolved,

    // -- accounting -----------------------------------------------------
    output wire [31:0]   count_fetched,
    output wire [31:0]   count_retired,
    output wire [31:0]   count_predicated_off,
    output wire [31:0]   count_issued,
    output wire [31:0]   count_branches,
    output wire [31:0]   count_loop_iterations,
    output wire [31:0]   count_wait_events,
    output wire [31:0]   count_signals,
    output wire [31:0]   count_state_prepares,
    output wire [31:0]   count_state_commits,
    output wire [31:0]   count_state_discards,
    output wire [31:0]   count_state_reads,
    output wire [31:0]   count_state_generation_advances,
    output wire [31:0]   count_state_commits_applied,
    output wire [31:0]   count_state_rows_committed,
    output wire [63:0]   count_state_bytes_written,
    output wire [3:0]    loop_depth,
    output wire          event_signal_error,
    output wire          state_apply_overflow,

    // -- observation (trace; not control) -------------------------------
    output wire [3:0]    dbg_decode_error,
    output wire [31:0]   dbg_source_operation_id,
    output wire [31:0]   dbg_wait_fault_event,
    output wire [1:0]    dbg_loop_action
);
    // -- program-header admission ----------------------------------------
    ot_a3_program_header header (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(hdr_in_valid),
        .in_start(hdr_in_start),
        .in_word(hdr_in_word),
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

    // -- store geometry as 33-bit row counts -----------------------------
    // Sized so that a 32-bit row or a 33-bit base-plus-ID compares against
    // the row count without truncation.
    localparam [32:0] PROGRAM_ROWS = {1'b0, PROGRAM_WORDS};
    localparam [32:0] DESC_ROWS    = {1'b0, DESC_WORDS};

    // -- host load path ----------------------------------------------------
    // The sequencer's store reads occur only inside a transaction, so a
    // write accepted while !busy can never contend with one; the port muxes
    // below still let a read win should that invariant ever be broken.
    assign host_ready = !busy;
    wire host_program_write = host_we && !host_sel;
    wire host_desc_write    = host_we &&  host_sel;
    wire host_program_in_range = ({1'b0, host_row} < PROGRAM_ROWS) &&
                                 (host_lane < 6'd8);
    wire host_desc_in_range    = ({1'b0, host_row} < DESC_ROWS) &&
                                 (host_lane < 6'd48);
    wire host_program_accept = host_program_write && host_ready &&
                               host_program_in_range;
    wire host_desc_accept    = host_desc_write && host_ready &&
                               host_desc_in_range;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            host_write_refused <= 1'b0;
        else if (host_we && !(host_program_accept || host_desc_accept))
            host_write_refused <= 1'b1;
    end

    // -- program store port ------------------------------------------------
    wire         imem_req;
    wire [31:0]  imem_index;
    reg          imem_valid;

    assign pstore_en    = imem_req | host_program_accept;
    assign pstore_we    = !imem_req && host_program_accept;
    assign pstore_addr  = imem_req ? imem_index : host_row;
    assign pstore_wlane = host_lane[2:0];
    assign pstore_wdata = host_wdata;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            imem_valid <= 1'b0;
        else
            imem_valid <= imem_req;
    end

    // -- descriptor store port (section 3.4 base, bound and fault) ---------
    // A descriptor ID is relative to the transaction's descriptor base; an
    // ID at or beyond the declared count, or a row beyond the store, is a
    // fault the sequencer turns into the descriptor trap, and the store is
    // not read for it.  The fault flag is registered beside the read so the
    // sequencer sees exactly the registered one-cycle port it always has.
    wire         desc_req;
    wire [31:0]  desc_id;
    reg          desc_valid;
    reg          desc_fault;
    wire [32:0]  desc_absolute = {1'b0, cfg_desc_base} + {1'b0, desc_id};
    wire         desc_out_of_range = (desc_id >= cfg_desc_count) ||
                                     (desc_absolute >= DESC_ROWS);
    wire         desc_read = desc_req && !desc_out_of_range;

    assign dstore_en    = desc_read | host_desc_accept;
    assign dstore_we    = !desc_req && host_desc_accept;
    assign dstore_addr  = desc_req ? desc_absolute[31:0] : host_row;
    assign dstore_wlane = host_lane;
    assign dstore_wdata = host_wdata;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            desc_valid <= 1'b0;
            desc_fault <= 1'b0;
        end else begin
            desc_valid <= desc_req;
            if (desc_req)
                desc_fault <= desc_out_of_range;
        end
    end

    wire [1535:0] desc_data = desc_fault ? 1536'd0 : dstore_rdata;

    // -- runtime symbol file -------------------------------------------------
    wire [3:0]  sym_index;
    assign sym_addr = cfg_symbol_base + {28'd0, sym_index};
    wire        sym_bound = cfg_symbol_mask[{1'b0, sym_index}];

    // -- the microsequencer ---------------------------------------------------
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
        .imem_data(pstore_rdata),
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
        .loop_depth(loop_depth),
        .event_signal_error(event_signal_error),
        .state_apply_overflow(state_apply_overflow),
        .dbg_decode_error(dbg_decode_error),
        .dbg_source_operation_id(dbg_source_operation_id),
        .dbg_wait_fault_event(dbg_wait_fault_event),
        .dbg_loop_action(dbg_loop_action)
    );
endmodule
