`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 device top: the synthesisable control plane of one node.
//
// This is the module docs/CHIP_ARCHITECTURE_DESIGN.md section 11.4 item 4
// names -- the design-side replacement for the verification tops
// rtl/test/a3_microsequencer_top.sv and rtl/test/a3_shipped_prefix_top.sv,
// which are thin wrappers around it.  The engines are still stubbed: the
// engine issue and completion ports, the predicate service port and the
// resolved-view port are top-level ports, so the checker (or the
// shipped-prefix engine bridge) that answers them answers them here.  The
// control plane behind those ports is the asynchronous front end of section
// 3.2: an engine instruction leaves at issue with a serial and an
// issue-record-store slot and completes through the completion port in any
// order, bounded by A3_QUEUE_DEPTH per queue and A3_OUTSTANDING per die,
// ordered by the dependence table and the three-bit event scoreboard
// (AM-C1), with six resolver lanes and one shared divider behind the
// resolve stage.
//
// What is design and what is not.  Everything in this module is synthesisable
// and owned by the design: the program-header admission block, the
// microsequencer with its decoder, loop stack, scoreboard, predicate unit,
// resolver bank, issue record store and dependence table, the descriptor
// base/bound/fault logic of section 3.4, the runtime symbol file (section
// 3.3: sixteen 64-bit entries with bound bits, written per request by the
// management processor), and the host load path through which the
// management processor writes the two control stores and the symbol file
// (section 3.4: "written only by the management processor"; section 9.2).
// The stores themselves are presented as abstract macro boundaries, the
// asap7 column of the vehicle memory plan (section 11.2): a 4 KiB program
// store (vehicle default 128 rows x 32 B), a 64 KiB descriptor store
// (vehicle default 256 rows of which the RTL reads the 192-byte record
// prefix) and the issue record store's 512-byte payload macro (32 entries x
// 8 lanes x 64 B: the six resolved views of the operation in operand order
// and its counter snapshot), each a single synchronous port -- a read
// returns the whole row one cycle later, a write lands one lane.  Their
// geometry stays parametric because the L1-CP vector image concatenates four
// deployments (2,763 program rows, 7,140 descriptor rows) and
// DeepSeek-V4-Flash alone needs 1,312 instructions and 3,841 records: the
// campaigns override to 4096 / 8192 exactly as the shared verification top
// always has.  No memory is loaded by this module: the management processor
// writes the stores and the symbol file through host_* (design) and the
// wrapper that owns the arrays backs the boundaries (verification).
//
// The host load path selects.  host_sel = A3_HOST_SEL_PROGRAM (0): one
// 32-bit lane (0..7) of one instruction row; A3_HOST_SEL_DESCRIPTOR (1): one
// lane (0..47) of the 192-byte record prefix of one row;
// A3_HOST_SEL_SYMBOL (2): symbol host_row[3:0], lane 0 = value[31:0], lane 1
// = value[63:32], lane 2 = the bound bit in host_wdata[0].  A write while a
// transaction runs, to an unknown select, past a store or past a row's
// lanes is dropped and host_write_refused stays set until reset.
//
// Session retirement is design, and it is the device's.  ABI 3.0 wire format
// section 12.5: the TOKEN_APPEND that commits the final allowed non-EOS token
// "returns completion EOS reason MAX_NEW_TOKENS=2, and the device refuses
// every later transaction for that session".  Operator conventions section 8
// says the same of an official EOS, and says why it cannot be left to the
// driver: "Both that reason and an official EOS retire the device session;
// host-only loop termination does not satisfy this operator contract".  This
// module holds that state.  The completion port carries the completion
// record's EOS reason byte; a completion reporting OFFICIAL_EOS or
// MAX_NEW_TOKENS latches `session_retired` until reset, and a `start` offered
// afterwards never reaches the sequencer -- nothing is fetched, decoded or
// issued, and the transaction ends as a trap of class A3_TRAP_STATE.
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
    parameter integer STATE_COMPAT  = 1,
    // Instruction-CRC re-validation policy; 0 keeps the recurrence on
    // every fetch, which is what this design has always done.
    parameter integer CRC_CACHE     = 0,
    parameter integer CRC_PERIOD    = 0,
    parameter integer CRC_CACHE_ENTRIES = 2048,
    // Front-end request scheduling; passed through to the microsequencer.
    // 0 rebuilds the pre-parameter front end exactly.
    parameter integer FAST_FRONT_END = 0,
    // The resolver's two optional walk shortcuts.  The microsequencer has
    // carried them since the resolver gained them, but this top did not pass
    // them down, so a harness that swept the matrix through the device top
    // could not elaborate at all -- the parameter it named did not exist here.
    // Both default to 0, which is the shipped build.
    parameter integer FAST_SCAN = 0,
    parameter integer FAST_WALK = 0
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

    // -- host: control-store and symbol-file load path -------------------
    // One 32-bit lane of one row per cycle (see the header).  Accepted only
    // while no transaction runs (host_ready); a write offered while busy or
    // outside the target is dropped and host_write_refused stays set until
    // reset, so a load that was not taken cannot pass for one that was.
    input  wire          host_we,
    input  wire [1:0]    host_sel,
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
    input  wire [63:0]   cfg_max_retired_work,
    input  wire [31:0]   cfg_state_count,

    output wire          busy,
    output wire          done,
    output wire          complete,
    output wire          trapped,
    output wire [15:0]   trap_class,
    output wire [31:0]   first_fault_instruction,

    // -- session retirement (observation) --------------------------------
    // Set once a completion reported OFFICIAL_EOS or MAX_NEW_TOKENS and held
    // until reset; every later transaction on this session is refused.
    output wire          session_retired,
    output wire [7:0]    session_eos_reason,
    output wire [31:0]   count_transactions_refused_post_eos,

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

    // -- issue record store payload boundary (one synchronous port) -----
    // 32 entries x 8 lanes x 512 bits.  irs_we: lane irs_wlane of entry
    // irs_wslot takes irs_wdata.  irs_re: irs_rdata presents lane irs_rlane
    // of entry irs_rslot in the next cycle.  Lanes 0..5 are the resolved
    // views in operand order, lane 6 the counter snapshot at issue.
    output wire          irs_we,
    output wire [4:0]    irs_wslot,
    output wire [2:0]    irs_wlane,
    output wire [511:0]  irs_wdata,
    output wire          irs_re,
    output wire [4:0]    irs_rslot,
    output wire [2:0]    irs_rlane,
    input  wire [511:0]  irs_rdata,

    // -- data-dependent predicate service ------------------------------
    output wire          predicate_read_req,
    output wire [31:0]   predicate_read_object_id,
    output wire [31:0]   predicate_read_element_index,
    input  wire          predicate_read_valid,
    input  wire          predicate_read_value,
    input  wire [15:0]   predicate_read_trap_class,

    // -- engine issue: ready is queue acceptance -------------------------
    // The operation is outstanding from the handshake until its completion
    // is reported on the completion port with the same slot.
    output wire          issue_valid,
    input  wire          issue_ready,
    output wire [7:0]    issue_family,
    output wire [7:0]    issue_sub,
    output wire [31:0]   issue_descriptor_id,
    output wire [31:0]   issue_index,
    output wire [31:0]   issue_serial,
    output wire [4:0]    issue_slot,
    output wire [4:0]    issue_queue,

    // -- engine completion: any order, one per cycle -------------------
    input  wire          complete_valid,
    input  wire [4:0]    complete_slot,
    input  wire          complete_fault,
    input  wire [15:0]   complete_trap_class,
    // The completion record's EOS reason byte (wire format section 7, byte
    // 108: NONE=0, OFFICIAL_EOS=1, MAX_NEW_TOKENS=2, ...).  SELECTION.
    // TOKEN_APPEND publishes it; the operator conventions (section 8) say
    // OFFICIAL_EOS and MAX_NEW_TOKENS "retire the device session", and that
    // "host-only loop termination does not satisfy this operator contract",
    // so the reason has to reach the control plane and not only the host.
    input  wire [7:0]    complete_eos_reason,

    // -- resolved operand tensor views (A4, A13, A18) -------------------
    // Published in operand order immediately before the operation's issue
    // handshake, tagged with its issue-record slot.
    output wire          view_valid,
    output wire [31:0]   view_descriptor_id,
    output wire [2:0]    view_slot,
    output wire [31:0]   view_extent,
    output wire [7:0]    view_extent_axis,
    output wire [63:0]   view_element_offset,
    output wire [7:0]    view_rank,
    output wire [4:0]    view_irs_slot,
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
    output wire [1:0]    dbg_loop_action,
    output wire [5:0]    dbg_outstanding,
    output wire [5:0]    dbg_max_outstanding,
    output wire [31:0]   dbg_dep_stalls,
    output wire [31:0]   dbg_wait_stalls,
    output wire          irs_protocol_error
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
    wire host_program_write = host_we && (host_sel == ot_a3_pkg::A3_HOST_SEL_PROGRAM);
    wire host_desc_write    = host_we && (host_sel == ot_a3_pkg::A3_HOST_SEL_DESCRIPTOR);
    wire host_symbol_write  = host_we && (host_sel == ot_a3_pkg::A3_HOST_SEL_SYMBOL);
    wire host_program_in_range = ({1'b0, host_row} < PROGRAM_ROWS) &&
                                 (host_lane < 6'd8);
    wire host_desc_in_range    = ({1'b0, host_row} < DESC_ROWS) &&
                                 (host_lane < 6'd48);
    wire host_symbol_in_range  = (host_row < ot_a3_pkg::A3_SYMBOL_COUNT) &&
                                 (host_lane < 6'd3);
    wire host_program_accept = host_program_write && host_ready &&
                               host_program_in_range;
    wire host_desc_accept    = host_desc_write && host_ready &&
                               host_desc_in_range;
    wire host_symbol_accept  = host_symbol_write && host_ready &&
                               host_symbol_in_range;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            host_write_refused <= 1'b0;
        else if (host_we &&
                 !(host_program_accept || host_desc_accept || host_symbol_accept))
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

    // -- session retirement, and the refusal the ABI requires --------------
    // ABI 3.0 wire format section 12.5: the TOKEN_APPEND that commits the
    // final allowed non-EOS token "returns completion EOS reason
    // MAX_NEW_TOKENS=2, and the device refuses every later transaction for
    // that session".  Operator conventions section 8 says the same of an
    // official EOS -- "Both that reason and an official EOS retire the
    // device session; host-only loop termination does not satisfy this
    // operator contract".  THE DEVICE, not the host: a refusal taken in the
    // driver satisfies neither sentence, and runtime/sim/device.py takes its
    // one (Device.run_transaction, Session.finished -> STATE_TRANSACTION)
    // inside the device model for exactly that reason.  This is the control
    // plane's half of it.
    //
    // Retirement is latched off the completion port -- the engine result
    // boundary -- because that is where the reason is published, and it is
    // held until reset because a session cannot be un-retired.  A start
    // offered afterwards never reaches the sequencer: nothing is fetched,
    // nothing is decoded, nothing is issued, and the transaction completes
    // as a trap of class A3_TRAP_STATE (9, "state transaction"), which is
    // the class runtime/abi3/constants.py names for it and the class the
    // reference model returns.
    //
    // runtime.abi3.records.EosReason, cited by value exactly as
    // rtl/abi3/ot_a3_selection_token_append.sv cites it.
    localparam [7:0] A3_EOS_OFFICIAL        = 8'd1;
    localparam [7:0] A3_EOS_MAX_NEW_TOKENS  = 8'd2;

    wire         seq_busy;
    wire         seq_done;
    wire         seq_complete;
    wire         seq_trapped;
    wire [15:0]  seq_trap_class;
    wire [31:0]  seq_first_fault_instruction;

    reg          session_retired_q;
    reg  [7:0]   session_eos_reason_q;
    reg          refused_q;
    reg          refuse_done_q;
    reg  [31:0]  refused_count_q;
    reg          start_q;

    wire completion_retires = complete_valid &&
        ((complete_eos_reason == A3_EOS_OFFICIAL) ||
         (complete_eos_reason == A3_EOS_MAX_NEW_TOKENS));
    // A start offered to a retired session, with the sequencer idle.  The
    // sequencer never sees it.  The refusal is taken on the RISING EDGE of
    // start, not on its level: the sequencer leaves S_IDLE on the first
    // cycle it sees start and so takes one transaction however long start is
    // held, and a refusal has to be the same one transaction -- one `done`
    // pulse and one count -- or a held start would refuse the same
    // transaction once per cycle.  ``seq_start`` stays the level the
    // sequencer always had, so an unretired session behaves bit for bit as
    // before.
    wire start_edge   = start && !start_q;
    wire refuse_start = start_edge && session_retired_q && !seq_busy;
    wire seq_start    = start && !session_retired_q;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            session_retired_q    <= 1'b0;
            session_eos_reason_q <= 8'd0;
            refused_q            <= 1'b0;
            refuse_done_q        <= 1'b0;
            refused_count_q      <= 32'd0;
            start_q              <= 1'b0;
        end else begin
            start_q       <= start;
            refuse_done_q <= 1'b0;
            if (completion_retires) begin
                session_retired_q    <= 1'b1;
                session_eos_reason_q <= complete_eos_reason;
            end
            if (refuse_start) begin
                refused_q       <= 1'b1;
                refuse_done_q   <= 1'b1;
                refused_count_q <= refused_count_q + 32'd1;
            end else if (seq_start) begin
                refused_q <= 1'b0;
            end
        end
    end

    assign session_retired    = session_retired_q;
    assign session_eos_reason = session_eos_reason_q;
    assign count_transactions_refused_post_eos = refused_count_q;

    // The transaction outputs are the sequencer's, except on a refused
    // transaction, where they are the refusal: never complete, always
    // trapped, class 9, and no faulting instruction because none was
    // fetched.  ``done`` is the sequencer's one-cycle pulse or the
    // refusal's, and they cannot coincide: the sequencer is idle whenever a
    // refusal is taken.
    assign busy      = seq_busy;
    assign done      = seq_done | refuse_done_q;
    assign complete  = refused_q ? 1'b0 : seq_complete;
    assign trapped   = refused_q ? 1'b1 : seq_trapped;
    assign trap_class = refused_q ? ot_a3_pkg::A3_TRAP_STATE : seq_trap_class;
    assign first_fault_instruction =
        refused_q ? ot_a3_pkg::A3_NO_ID : seq_first_fault_instruction;

    // -- the microsequencer ---------------------------------------------------
    ot_a3_microsequencer #(
        .STATE_COMPAT(STATE_COMPAT),
        .CRC_CACHE(CRC_CACHE),
        .CRC_PERIOD(CRC_PERIOD),
        .CRC_CACHE_ENTRIES(CRC_CACHE_ENTRIES),
        .FAST_FRONT_END(FAST_FRONT_END),
        .FAST_SCAN(FAST_SCAN),
        .FAST_WALK(FAST_WALK)
    ) sequencer (
        .clk(clk),
        .rst_n(rst_n),
        .start(seq_start),
        .cfg_program_base(cfg_program_base),
        .cfg_instruction_count(cfg_instruction_count),
        .cfg_entry_pc(cfg_entry_pc),
        .cfg_max_retired_work(cfg_max_retired_work),
        .cfg_state_count(cfg_state_count),
        .busy(seq_busy),
        .done(seq_done),
        .complete(seq_complete),
        .trapped(seq_trapped),
        .trap_class(seq_trap_class),
        .first_fault_instruction(seq_first_fault_instruction),
        .imem_req(imem_req),
        .imem_index(imem_index),
        .imem_valid(imem_valid),
        .imem_data(pstore_rdata),
        .desc_req(desc_req),
        .desc_id(desc_id),
        .desc_valid(desc_valid),
        .desc_fault(desc_fault),
        .desc_data(desc_data),
        .host_sym_we(host_symbol_accept),
        .host_sym_index(host_row[3:0]),
        .host_sym_lane(host_lane[1:0]),
        .host_sym_wdata(host_wdata),
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
        .irs_we(irs_we),
        .irs_wslot(irs_wslot),
        .irs_wlane(irs_wlane),
        .irs_wdata(irs_wdata),
        .irs_re(irs_re),
        .irs_rslot(irs_rslot),
        .irs_rlane(irs_rlane),
        .irs_rdata(irs_rdata),
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
        .dbg_decode_error(dbg_decode_error),
        .dbg_source_operation_id(dbg_source_operation_id),
        .dbg_wait_fault_event(dbg_wait_fault_event),
        .dbg_loop_action(dbg_loop_action),
        .dbg_outstanding(dbg_outstanding),
        .dbg_max_outstanding(dbg_max_outstanding),
        .dbg_dep_stalls(dbg_dep_stalls),
        .dbg_wait_stalls(dbg_wait_stalls),
        .irs_protocol_error(irs_protocol_error)
    );
endmodule
