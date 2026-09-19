`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 deterministic microsequencer (feature bit 2), asynchronous front end.
//
// One transaction, in order, from an entrypoint's first instruction to
// CONTROL.COMPLETE or to the first trap.  The stages are the ones the golden
// model (runtime/sim/device.Device.run_transaction) executes per instruction,
// in exactly its order, because the two must agree instruction for
// instruction (docs/CHIP_ARCHITECTURE_DESIGN.md section 3.2, the cycle-level
// contract; section 3.3's rows F D P L W R H I):
//
//   fetch      pc bound check, watchdog (issue serial vs max_retired_work),
//              32-byte record read
//   decode     ot_a3_instruction_decoder: CRC32C and structural legality
//   predicate  PREDICATE descriptor, optional inversion, skip without retire;
//              a BOOLEAN_OBJECT / EOS_MEMBER read is checked RAW against the
//              dependence table before it is requested
//   wait       EVENT_WAIT_SET descriptor: every producer signalled (and
//              published under acquire); stall while any is pending (AM-C10)
//   execute    control transfer, transactional state, or an engine issue:
//              descriptor fetch, SCHEDULE fetch for the queue, six views
//              resolved concurrently by ot_a3_resolver_bank, the dependence
//              check (two ranges per cycle), publication of the resolved
//              views in slot order, then the issue handshake
//   retire     CONTROL retires in the front end; an engine instruction
//              retires when its completion is reported, in any order
//
// Ordering that is load-bearing for correlation:
//   * a predicated-off instruction is fetched, never waits, never signals and
//     never retires;
//   * the issued counter advances at dispatch, before the operation can
//     fault; the retired counter advances only at a completion that carries
//     no fault (section 3.2 item 3: instructions.retired counts at
//     completion; retired_work is retirements at COMPLETE);
//   * an engine issue is emitted only once the family's own precondition has
//     passed, so a faulting STATE or RECOVERY.ABORT produces no issue event;
//   * the resolved views of an instruction are published together, after
//     the dependence check has passed and immediately before its issue
//     handshake, tagged with its issue-record slot -- so no view of an
//     instruction the golden model never reached is ever published, and the
//     view and issue streams stay in program order at every run-ahead depth.
//
// The engine port has two phases (section 3.2 item 2).  Issue: issue_valid /
// issue_ready is *queue acceptance*, with the serial, the IRS slot and the
// queue beside the family, subopcode, descriptor and pc; at most one per
// cycle; it stalls while A3_QUEUE_DEPTH operations are outstanding on the
// queue or A3_OUTSTANDING on the die.  Completion: complete_valid names the
// slot, in any order, one per cycle, with a fault bit and class.  Retirement
// then signals the event (pending -> signalled -> published), releases the
// dependence entry and counts.
//
// Faults (section 3.2 item 5).  A precise front-end trap (decode, predicate,
// wait, loop, resolver, watchdog, TRAP, running off the body) is held until
// nothing is outstanding: if an engine fault arrives first it wins, because
// its serial is lower.  An asynchronous engine fault stops issue in the cycle
// it is reported; the front end abandons the instruction in flight (cancels a
// predicate read, clears the resolver bank), waits for every outstanding
// operation to complete or fault, then restores the transaction counters
// from the snapshot the faulting instruction wrote at its issue -- fetched,
// issued, predicated off, views resolved, loop iterations, branches, wait
// events, signals, retired -- so a FAILED transaction's counters equal the
// golden model's, which stops at the faulting pc.  The snapshot lives in the
// issue record store's payload (lane 6 of the entry), beside the resolved
// views (lanes 0..5); the payload is a memory macro outside this block.
// first_fault_instruction is the lowest issue serial among faulting
// instructions.  Predicate reads already made for later instructions are a
// real run-ahead side effect (reads only) and are not undone.
//
// Drains (AM-C2).  FENCE drains at ENGINE scope -- every shipped wait set
// carries scope 0, and a FENCE without a wait set is ENGINE scope by the
// amendment -- which on one node is "nothing outstanding"; COMPLETE,
// OBSERVATION.COUNTER_SNAPSHOT and RECOVERY.DRAIN/POISON drain the same way.
// The single-node top has no CLUSTER / SYSTEM traversal to add.
//
// Not in this block, recorded here so the report and the design agree: the
// front end is not pipelined across instructions (section 3.3's four-cycle
// occupancy is not claimed; only issue -> completion is asynchronous); the
// instruction CRC is still checked at fetch (8 beats, section 3.4 moves it to
// LOAD; kept because the host-load bench's empty-store case depends on it);
// no predicate value cache; no node-band predication (AM-R4); frontier
// streaming is frontier 0 (section 3.6, non-architectural).
//
// RE-VALIDATION OF A RE-FETCHED RECORD (``CRC_CACHE`` / ``CRC_PERIOD``).
// The front end re-runs the eight-beat instruction CRC on every fetch,
// including every re-fetch of a loop body.  The Qwen decode token fetches
// 2,104 records out of a 74-instruction body, so 2,030 of those 2,104
// recurrences re-check bits this block has already checked in this same
// transaction.  Nothing in the frozen ABI asks for that: wire format section
// 1 says invalid CRCs "fail before work is issued" and section 2 says "every
// instruction CRC must pass" -- both are validate-before-act obligations on a
// record, not per-fetch obligations.  docs/CHIP_ARCHITECTURE_DESIGN.md
// section 3.4 is more explicit still: the program store is "written only by
// the management processor after the body SHA-256 and every instruction CRC
// have passed", and post-load corruption of the store is caught by the
// store's SECDED, which "traps 2" -- not by re-running the checksum.
//
// ``CRC_CACHE = 0`` keeps the recurrence on every fetch and is the build this
// block has always been.  ``CRC_CACHE = 1`` keeps one bit per instruction
// index saying "this index's CRC has been run and passed since this
// transaction started", and a hit admits the record without the recurrence.
// The bit vector is cleared at every ``start``, so it never spans a program
// load and never outlives one transaction.  ``CRC_PERIOD`` bounds the
// exposure further: 0 validates an index once per transaction, K >= 2
// re-validates it on every Kth fetch.
//
// What is skipped is exactly the 32-bit checksum.  The opcode, subopcode,
// reserved-flag, predicate-flag, predicate-ID and branch-target checks are
// combinational in the record and are re-evaluated on every fetch in both
// builds.  What is given up with CRC_CACHE = 1 is stated once, plainly: a bit
// that flips IN the program store after an index's validating fetch and
// before its last fetch of the same transaction is no longer caught by this
// block, because the record is no longer re-checksummed -- that is the case
// section 3.4 assigns to the store's SECDED, which this RTL does not yet
// implement.
//
// The package is referenced by scope, never wildcard-imported [OI-43].
// ---------------------------------------------------------------------------
module ot_a3_microsequencer
#(
    // The four production-comparison deployments use ordinary live buffers
    // and contain no STATE descriptors or instructions.  Keeping the legacy
    // controller behind a parameter preserves ABI 3.0 compatibility tests
    // without forcing its slot file or apply path into the shipped profile.
    parameter integer STATE_COMPAT = 1,
    // 0 re-runs the instruction CRC on every fetch, exactly as before.
    parameter integer CRC_CACHE = 0,
    // 0 = validate an index once per transaction; K >= 2 = every Kth fetch of
    // that index; 1 = never skip (equivalent to CRC_CACHE = 0).
    parameter integer CRC_PERIOD = 0,
    // Instruction indexes covered by the vector.  A pc at or above this always
    // takes the full recurrence, so a short vector loses cycles, never checks.
    parameter integer CRC_CACHE_ENTRIES = 2048,
    // Completion-level board depth, forwarded to ot_a3_event_scoreboard.
    //
    // ABI 3.0 events are SINGLE-ASSIGNMENT levels -- section 12.14 lets at most
    // one instruction name a given event ID in its signal field, and nothing
    // lowers a level before the transaction ends -- so the board bounds the
    // number of distinct completion levels a program's TEXT may name, not the
    // number it holds at once.  An allocator cannot recycle an ID: that was
    // built and refused by the verifier, ``event 0 is signalled more than
    // once``.
    //
    // The shipped DeepSeek-V4.1-Flash release needs 2,442 levels at eight
    // nodes, and the legal reduction -- merging producers that every wait set
    // names together -- reaches only 2,165.  Both are over the default 2,048,
    // so the board is the thing that has to be wider, and it is a parameter
    // rather than a new default so that no bound vector and no shipped
    // capability record moves: the default elaboration is byte-identical to
    // the one every committed campaign was run against.  The cost is three
    // flip-flops a level, 6,144 for a board of 4,096.
    parameter integer EVENTS = ot_a3_pkg::A3_EVENT_COUNT,
    // Front-end request scheduling.  ``FAST_FRONT_END = 0`` rebuilds the
    // front end exactly as it was before this parameter: one state per
    // decision, each request registered by the state that decided to make
    // it, so the store sees it a cycle after the decision and the wait state
    // costs two cycles.  ``FAST_FRONT_END = 1`` launches each request from
    // the state that already held the operand a cycle earlier and deletes
    // the pure-decision states (S_DECODE_PUSH, S_PRED_REQ, S_WAIT_REQ,
    // S_LOOP_SYM), which removes four cycles per instruction and one per
    // LOOP_SETUP.  It moves no logic onto a memory address or enable path:
    // every request signal stays a register output, ``imem_index`` is
    // maintained as program_base + pc by a single adder, and the only new
    // combinational logic is one 32-bit equality (the wait-set ID against
    // A3_NO_ID) between two registers.  Both builds are driven from one
    // stimulus by rtl/test/tb_a3_front_end_equiv.sv.
    parameter integer FAST_FRONT_END = 0,
    // View-resolution scheduling, forwarded to ot_a3_resolver_bank.  Two
    // separate optimisations behind two separate knobs, both 0 by default so
    // the unconfigured build is the control plane exactly as it shipped:
    //   FAST_SCAN elides the bank's per-slot scan state.
    //   FAST_WALK folds ot_a3_view_resolver's S_SELECT into the states that
    //   already advance the term, and pairs the bounding walk's accumulate
    //   with the next axis's operand presentation.
    // The 0 build is held to cycle-exact identity with a verbatim copy of the
    // shipped blocks by rtl/test/tb_a3_resolver_bank_inert.sv.
    parameter integer FAST_SCAN = 0,
    parameter integer FAST_WALK = 0
)
(
    input  wire          clk,
    input  wire          rst_n,

    // -- transaction control ------------------------------------------
    input  wire          start,
    input  wire [31:0]   cfg_program_base,
    input  wire [31:0]   cfg_instruction_count,
    input  wire [31:0]   cfg_entry_pc,
    input  wire [63:0]   cfg_max_retired_work,
    input  wire [31:0]   cfg_state_count,

    output reg           busy,
    output reg           done,
    output reg           complete,
    output reg           trapped,
    output reg  [15:0]   trap_class,
    output reg  [31:0]   first_fault_instruction,

    // -- instruction memory (registered read, one cycle) ---------------
    output reg           imem_req,
    output reg  [31:0]   imem_index,
    input  wire          imem_valid,
    input  wire [255:0]  imem_data,

    // -- descriptor store (registered read, one cycle) -----------------
    output wire          desc_req,
    output wire [31:0]   desc_id,
    input  wire          desc_valid,
    input  wire          desc_fault,
    input  wire [1535:0] desc_data,

    // -- runtime symbol file: host write port (section 3.3) ------------
    input  wire          host_sym_we,
    input  wire [3:0]    host_sym_index,
    input  wire [1:0]    host_sym_lane,
    input  wire [31:0]   host_sym_wdata,

    // -- data-dependent predicate result -------------------------------
    output reg           predicate_read_req,
    output reg  [31:0]   predicate_read_object_id,
    output reg  [31:0]   predicate_read_element_index,
    input  wire          predicate_read_valid,
    input  wire          predicate_read_value,
    input  wire [15:0]   predicate_read_trap_class,

    // -- engine issue: queue acceptance --------------------------------
    // issue_valid is withdrawn in the cycle an engine fault is reported
    // (section 3.2 item 5: an asynchronous fault stops issue in the cycle it
    // is reported), so no operation after the faulting one is ever accepted.
    output wire          issue_valid,
    input  wire          issue_ready,
    output reg  [7:0]    issue_family,
    output reg  [7:0]    issue_sub,
    output reg  [31:0]   issue_descriptor_id,
    output reg  [31:0]   issue_index,
    output reg  [31:0]   issue_serial,
    output reg  [4:0]    issue_slot,
    output reg  [4:0]    issue_queue,

    // -- engine completion: any order, one per cycle -------------------
    input  wire          complete_valid,
    input  wire [4:0]    complete_slot,
    input  wire          complete_fault,
    input  wire [15:0]   complete_trap_class,

    // -- issue record store payload (memory macro outside this block) --
    // 32 entries x 8 lanes x 512 bits; lanes 0..5 hold the resolved views
    // in slot order, lane 6 the counter snapshot at issue.  A read returns
    // the lane one cycle later.
    output reg           irs_we,
    output reg  [4:0]    irs_wslot,
    output reg  [2:0]    irs_wlane,
    output reg  [511:0]  irs_wdata,
    output reg           irs_re,
    output reg  [4:0]    irs_rslot,
    output reg  [2:0]    irs_rlane,
    input  wire [511:0]  irs_rdata,

    // -- resolved tensor views (amendments A4, A13 and A18) ------------
    // One single-cycle pulse per operand view of the instruction about to
    // issue, in operand order, tagged with the issue-record slot it belongs
    // to.  Observation only: it carries no back-pressure because it states
    // what the issue already means.
    output reg           view_valid,
    output reg  [31:0]   view_descriptor_id,
    output reg  [2:0]    view_slot,
    output reg  [31:0]   view_extent,
    output reg  [7:0]    view_extent_axis,
    output reg  [63:0]   view_element_offset,
    output reg  [7:0]    view_rank,
    output reg  [4:0]    view_irs_slot,
    output reg  [31:0]   count_views_resolved,

    // -- accounting ----------------------------------------------------
    output reg  [31:0]   count_fetched,
    output reg  [31:0]   count_retired,
    output reg  [31:0]   count_predicated_off,
    output reg  [31:0]   count_issued,
    output reg  [31:0]   count_branches,
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

    // -- observation (retained by the testbench, not control) ----------
    output wire [3:0]    dbg_decode_error,
    output wire [31:0]   dbg_source_operation_id,
    output wire [31:0]   dbg_wait_fault_event,
    output wire [1:0]    dbg_loop_action,
    output wire [5:0]    dbg_outstanding,
    output wire [5:0]    dbg_max_outstanding,
    output reg  [31:0]   dbg_dep_stalls,
    output reg  [31:0]   dbg_wait_stalls,
    output wire          irs_protocol_error
);
    // -- stage encoding -------------------------------------------------
    localparam [5:0] S_IDLE          = 6'd0;
    localparam [5:0] S_CHECK_PC      = 6'd1;
    localparam [5:0] S_FETCH_WAIT    = 6'd2;
    localparam [5:0] S_DECODE_PUSH   = 6'd3;
    localparam [5:0] S_DECODE_WAIT   = 6'd4;
    localparam [5:0] S_PRED_REQ      = 6'd5;
    localparam [5:0] S_PRED_WAIT     = 6'd6;
    localparam [5:0] S_PRED_SYM      = 6'd7;
    localparam [5:0] S_PRED_EVAL     = 6'd8;
    localparam [5:0] S_PRED_HAZARD   = 6'd9;
    localparam [5:0] S_PRED_OBJECT   = 6'd10;
    localparam [5:0] S_WAIT_REQ      = 6'd11;
    localparam [5:0] S_WAIT_WAIT     = 6'd12;
    localparam [5:0] S_WAIT_EVAL     = 6'd13;
    localparam [5:0] S_DISPATCH      = 6'd14;
    localparam [5:0] S_LOOP_WAIT     = 6'd15;
    localparam [5:0] S_LOOP_SYM      = 6'd16;
    localparam [5:0] S_LOOP_OP       = 6'd17;
    localparam [5:0] S_LOOP_DONE     = 6'd18;
    localparam [5:0] S_ENG_WAIT      = 6'd19;
    localparam [5:0] S_SCHED_WAIT    = 6'd20;
    localparam [5:0] S_RESOLVE       = 6'd21;
    localparam [5:0] S_HAZARD        = 6'd22;
    localparam [5:0] S_HAZARD_STALL  = 6'd23;
    localparam [5:0] S_VIEW_PUB      = 6'd24;
    localparam [5:0] S_ISSUE         = 6'd25;
    localparam [5:0] S_STATE_SYM     = 6'd26;
    localparam [5:0] S_STATE_DONE    = 6'd27;
    localparam [5:0] S_DRAIN         = 6'd28;
    localparam [5:0] S_TRAP_WAIT     = 6'd29;
    localparam [5:0] S_FAULT_DRAIN   = 6'd30;
    localparam [5:0] S_FAULT_READ    = 6'd31;
    localparam [5:0] S_FAULT_WAIT    = 6'd32;
    localparam [5:0] S_FAULT_APPLY   = 6'd33;
    localparam [5:0] S_COMMIT        = 6'd34;
    localparam [5:0] S_DISCARD       = 6'd35;
    localparam [5:0] S_DONE          = 6'd36;

    // what a drain leads to
    localparam [1:0] DRAIN_RETIRE   = 2'd0;   // FENCE: retire and publish
    localparam [1:0] DRAIN_COMPLETE = 2'd1;   // COMPLETE
    localparam [1:0] DRAIN_ISSUE    = 2'd2;   // OBSERVATION / RECOVERY: then issue

    reg [5:0]  state;
    reg [31:0] pc;
    reg [31:0] instruction_count;
    reg [31:0] program_base;
    reg [63:0] work_bound;
    reg [31:0] state_count;
    reg [255:0] record;
    reg        xact_clear;
    reg [31:0] serial;            // program-order issue serial (section 3.2 item 2)
    reg [1:0]  drain_next;

    // decoded instruction
    reg [7:0]  ins_major;
    reg [7:0]  ins_sub;
    reg [15:0] ins_flags;
    reg [31:0] ins_predicate_id;
    reg [31:0] ins_descriptor_id;
    reg [31:0] ins_wait_set_id;
    reg [31:0] ins_signal_event_id;
    reg [31:0] ins_control_id;

    reg [511:0] pred_payload;
    reg [511:0] state_payload;
    reg [3:0]   sym_index_q;

    // -- runtime symbol file ---------------------------------------------
    wire [ot_a3_pkg::A3_SYMBOL_COUNT*64-1:0] sym_values;
    wire [ot_a3_pkg::A3_SYMBOL_COUNT-1:0]    sym_bounds;
    ot_a3_symbol_file symbols (
        .clk(clk),
        .rst_n(rst_n),
        .host_we(host_sym_we),
        .host_index(host_sym_index),
        .host_lane(host_sym_lane),
        .host_wdata(host_sym_wdata),
        .file_values(sym_values),
        .file_bound(sym_bounds)
    );
    wire [63:0] sym_value = sym_values[sym_index_q*64 +: 64];
    wire        sym_bound = sym_bounds[sym_index_q];

    // -- validated-record vector (CRC_CACHE) -----------------------------
    // One bit per instruction index: "the CRC of the record at this index has
    // been run by the decoder and passed, since this transaction started".
    // Cleared on reset and on every start pulse, so a hit can never refer to
    // a program the host loaded after the bit was set.
    localparam integer CRC_IDX_W  = (CRC_CACHE_ENTRIES < 2) ? 1 : $clog2(CRC_CACHE_ENTRIES);
    localparam integer CRC_PHASE_W = (CRC_PERIOD < 2) ? 1 : $clog2(CRC_PERIOD);

    // Both are packed vectors rather than unpacked arrays so the clear at
    // start is one assignment, not a loop: a delayed assignment to an array
    // inside a for loop is not accepted by every simulator this program
    // pins, and the vector form is also what synthesis wants here.
    reg  [CRC_CACHE_ENTRIES-1:0]              crc_valid_vec;
    reg  [CRC_CACHE_ENTRIES*CRC_PHASE_W-1:0]  crc_phase_vec;

    // pc is the index; a pc outside the vector is never cached.
    wire                  crc_in_range = (CRC_CACHE != 0) &&
                                         (pc < CRC_CACHE_ENTRIES[31:0]);
    wire [CRC_IDX_W-1:0]  crc_idx      = pc[CRC_IDX_W-1:0];
    // Registered one fetch state ahead of use: the vector read is resolved
    // during S_CHECK_PC and consumed at S_DECODE_PUSH, two states later, so
    // the read multiplexer is never in the same cycle as the decoder handshake.
    reg                   crc_hit_q;
    reg                   crc_cached_q;   // this fetch's index is in the vector
    reg  [CRC_IDX_W-1:0]  crc_idx_q;

    // Counted, not asserted: both checkers read these out of the design.
    reg  [31:0]           dbg_crc_full;
    reg  [31:0]           dbg_crc_skipped;

    // -- instruction decoder --------------------------------------------
    reg         dec_in_valid;
    wire        dec_in_ready;
    wire        dec_out_valid;
    wire        dec_out_legal;
    wire [3:0]  dec_out_error;
    wire [15:0] dec_out_trap_class;
    wire [7:0]  dec_major;
    wire [7:0]  dec_sub;
    wire [15:0] dec_flags;
    wire [31:0] dec_predicate_id;
    wire [31:0] dec_descriptor_id;
    wire [31:0] dec_wait_set_id;
    wire [31:0] dec_signal_event_id;
    wire [31:0] dec_control_id;
    wire [31:0] dec_source_operation_id;
    wire [31:0] dec_index;

    ot_a3_instruction_decoder #(.CRC_CACHE(CRC_CACHE)) decoder (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(dec_in_valid),
        .in_ready(dec_in_ready),
        .in_record(record),
        .in_index(pc),
        .in_instruction_count(instruction_count),
        .in_crc_validated(crc_hit_q),
        .out_valid(dec_out_valid),
        .out_ready(1'b1),
        .out_legal(dec_out_legal),
        .out_error(dec_out_error),
        .out_trap_class(dec_out_trap_class),
        .out_index(dec_index),
        .out_major(dec_major),
        .out_sub(dec_sub),
        .out_flags(dec_flags),
        .out_predicate_id(dec_predicate_id),
        .out_descriptor_id(dec_descriptor_id),
        .out_wait_set_id(dec_wait_set_id),
        .out_signal_event_id(dec_signal_event_id),
        .out_control_id(dec_control_id),
        .out_source_operation_id(dec_source_operation_id)
    );

    // -- shared divider ---------------------------------------------------
    wire        loop_div_req;
    wire [63:0] loop_div_num;
    wire [31:0] loop_div_den;
    wire [5:0]  bank_div_req;
    wire [6*64-1:0] bank_div_num;
    wire [6*32-1:0] bank_div_den;
    wire [6:0]  div_done;
    wire [63:0] div_quot;
    wire [63:0] div_rem;

    ot_a3_shared_divider #(.REQUESTERS(7)) divider (
        .clk(clk),
        .rst_n(rst_n),
        .clear(xact_clear),
        .req({bank_div_req, loop_div_req}),
        .num({bank_div_num, loop_div_num}),
        .den({bank_div_den, loop_div_den}),
        .grant(),
        .busy(),
        .done(div_done),
        .quot(div_quot),
        .rem(div_rem)
    );

    // -- loop stack ------------------------------------------------------
    reg         loop_setup_valid;
    reg         loop_next_valid;
    wire        loop_done;
    wire        loop_trap_valid;
    wire [15:0] loop_trap_class;
    wire [31:0] loop_next_pc;
    wire [1:0]  loop_action;
    wire [31:0] loop_iteration_count;
    reg  [31:0] loop_query_id_q;
    wire [6*32-1:0] bank_loop_query_id;
    wire [6:0]      loop_query_active;
    wire [7*32-1:0] loop_query_value;
    wire [7*32-1:0] loop_query_trip;
    wire [6:0]      loop_query_symbol_bounded;
    wire [7*32-1:0] loop_query_divisor;
    wire [7*32-1:0] loop_query_bound_value;
    reg  [511:0] loop_payload;

    wire [7:0]  loop_bound_kind = loop_payload[15:8];
    wire [31:0] loop_lower      = loop_payload[63:32];
    wire [31:0] loop_upper      = loop_payload[95:64];
    wire [31:0] loop_step       = loop_payload[127:96];
    wire [31:0] loop_max_iter   = loop_payload[159:128];
    wire [31:0] loop_symbol_id  = loop_payload[223:192];
    wire [31:0] loop_body_start = loop_payload[255:224];
    wire [31:0] loop_body_end   = loop_payload[287:256];
    wire [31:0] loop_divisor    = loop_payload[351:320];
    // The same two fields taken straight off the descriptor word, one cycle
    // before loop_payload is readable, so S_LOOP_SYM's work can happen in
    // S_LOOP_WAIT (FAST_FRONT_END).  Slices of a store output, no logic.
    wire [7:0]  desc_loop_kind   = desc_payload[15:8];
    wire [31:0] desc_loop_symbol = desc_payload[223:192];

    ot_a3_loop_stack #(.QUERY_PORTS(7)) loops (
        .clk(clk),
        .rst_n(rst_n),
        .clear(xact_clear),
        .setup_valid(loop_setup_valid),
        .next_valid(loop_next_valid),
        .op_pc(pc),
        .op_loop_id(ins_control_id),
        .setup_bound_kind(loop_bound_kind),
        .setup_lower(loop_lower),
        .setup_upper(loop_upper),
        .setup_step(loop_step),
        .setup_max_iterations(loop_max_iter),
        .setup_body_start(loop_body_start),
        .setup_body_end(loop_body_end),
        .setup_bound_divisor(loop_divisor),
        .setup_symbol_value(sym_value),
        .setup_symbol_bound(sym_bound),
        .busy(),
        .done(loop_done),
        .trap_valid(loop_trap_valid),
        .trap_class(loop_trap_class),
        .next_pc(loop_next_pc),
        .action(loop_action),
        .div_req(loop_div_req),
        .div_num(loop_div_num),
        .div_den(loop_div_den),
        .div_done(div_done[0]),
        .div_quot(div_quot),
        .query_id({bank_loop_query_id, loop_query_id_q}),
        .query_active(loop_query_active),
        .query_value(loop_query_value),
        .query_trip(loop_query_trip),
        .query_symbol_bounded(loop_query_symbol_bounded),
        .query_divisor(loop_query_divisor),
        .query_bound_value(loop_query_bound_value),
        .iteration_count(loop_iteration_count),
        .depth(loop_depth)
    );
    wire        pq_active = loop_query_active[0];
    wire [31:0] pq_value  = loop_query_value[31:0];
    wire [31:0] pq_trip   = loop_query_trip[31:0];

    // -- issue record store ---------------------------------------------------
    reg         irs_alloc_valid;
    wire        irs_alloc_ready;
    wire [4:0]  irs_free_slot;
    reg  [4:0]  issue_slot_q;
    reg  [4:0]  issue_queue_q;
    wire        irs_retire_valid;
    wire [4:0]  irs_retire_slot;
    wire [31:0] irs_retire_serial;
    wire [31:0] irs_retire_event_id;
    wire        irs_retire_release;
    wire        irs_retire_event_last;
    wire        irs_retire_fault;
    wire        irs_fault_valid;
    wire [4:0]  irs_fault_slot;
    wire [31:0] irs_fault_serial;
    wire [31:0] irs_fault_pc;
    wire [15:0] irs_fault_trap_class;
    wire [5:0]  irs_outstanding;
    wire [5:0]  irs_outstanding_with_event;
    wire        irs_any_outstanding;

    ot_a3_issue_record_store irs (
        .clk(clk),
        .rst_n(rst_n),
        .clear(xact_clear),
        .alloc_queue(issue_queue_q),
        .alloc_ready(irs_alloc_ready),
        .free_slot(irs_free_slot),
        .alloc_valid(irs_alloc_valid),
        .alloc_slot(issue_slot_q),
        .alloc_serial(serial),
        .alloc_pc(pc),
        .alloc_event_id(ins_signal_event_id),
        .alloc_release(ins_flags[ot_a3_pkg::A3_FLAG_SIGNAL_RELEASE]),
        .complete_valid(complete_valid),
        .complete_slot(complete_slot),
        .complete_fault(complete_fault),
        .complete_trap_class(complete_trap_class),
        .retire_valid(irs_retire_valid),
        .retire_slot(irs_retire_slot),
        .retire_serial(irs_retire_serial),
        .retire_event_id(irs_retire_event_id),
        .retire_release(irs_retire_release),
        .retire_event_last(irs_retire_event_last),
        .retire_fault(irs_retire_fault),
        .fault_valid(irs_fault_valid),
        .fault_slot(irs_fault_slot),
        .fault_serial(irs_fault_serial),
        .fault_pc(irs_fault_pc),
        .fault_trap_class(irs_fault_trap_class),
        .outstanding(irs_outstanding),
        .outstanding_with_event(irs_outstanding_with_event),
        .any_outstanding(irs_any_outstanding),
        .max_outstanding(dbg_max_outstanding),
        .irs_protocol_error(irs_protocol_error)
    );
    assign dbg_outstanding = irs_outstanding;

    // The issue handshake is withdrawn the moment a fault is reported: the
    // registered first-fault record, and the completion carrying the fault in
    // the cycle before that record exists.
    reg issue_valid_q;
    assign issue_valid = issue_valid_q && !irs_fault_valid &&
                         !(complete_valid && complete_fault);

    // a retirement that counts: no fault on it, and no fault recorded before it
    wire retire_counts = irs_retire_valid && !irs_retire_fault && !irs_fault_valid;
    wire retire_signals = irs_retire_valid && !irs_retire_fault &&
                          (irs_retire_event_id != ot_a3_pkg::A3_NO_ID);

    // -- event scoreboard -------------------------------------------------
    reg         evt_issue_valid;
    reg         evt_control_valid;
    reg         evt_wait_start;
    reg [511:0] evt_wait_payload;
    reg         evt_wait_acquire;
    wire        evt_wait_done;
    wire        evt_wait_ok;
    wire [15:0] evt_wait_trap_class;
    wire [31:0] evt_wait_fault_event;
    wire        evt_wait_stalled;
    wire [31:0] sb_signal_count;
    wire [31:0] sb_wait_count;

    ot_a3_event_scoreboard #(.EVENTS(EVENTS)) events (
        .clk(clk),
        .rst_n(rst_n),
        .clear(xact_clear),
        .issue_valid(evt_issue_valid),
        .issue_event_id(ins_signal_event_id),
        .complete_valid(irs_retire_valid && !irs_retire_fault &&
                        (irs_retire_event_id != ot_a3_pkg::A3_NO_ID)),
        .complete_event_id(irs_retire_event_id),
        .complete_release(irs_retire_release),
        .complete_last(irs_retire_event_last),
        .control_signal_valid(evt_control_valid),
        .control_signal_event_id(ins_signal_event_id),
        .control_signal_release(ins_flags[ot_a3_pkg::A3_FLAG_SIGNAL_RELEASE]),
        .signal_error(event_signal_error),
        .wait_start(evt_wait_start),
        .wait_payload(evt_wait_payload),
        .wait_acquire(evt_wait_acquire),
        .wait_busy(),
        .wait_done(evt_wait_done),
        .wait_ok(evt_wait_ok),
        .wait_trap_class(evt_wait_trap_class),
        .wait_fault_event(evt_wait_fault_event),
        .wait_stalled(evt_wait_stalled),
        .signal_count(sb_signal_count),
        .wait_count(sb_wait_count)
    );

    // -- state controller -------------------------------------------------
    reg         st_op_valid;
    reg         st_commit_all;
    reg         st_discard_all;
    wire        st_op_done;
    wire        st_op_ok;
    wire [15:0] st_op_trap_class;
    wire        st_apply_done;
    wire [31:0] st_count_prepares;
    wire [31:0] st_count_commits;
    wire [31:0] st_count_discards;
    wire [31:0] st_count_reads;
    wire [31:0] st_count_generation_advances;

    generate
        if (STATE_COMPAT != 0) begin : g_state_compat
            ot_a3_state_controller states (
                .clk(clk),
                .rst_n(rst_n),
                .clear(xact_clear),
                .op_valid(st_op_valid),
                .op_sub(ins_sub),
                .op_descriptor_id(ins_descriptor_id),
                .op_payload(state_payload),
                .op_rows(sym_value[31:0]),
                .op_rows_bound(sym_bound),
                .op_done(st_op_done),
                .op_ok(st_op_ok),
                .op_trap_class(st_op_trap_class),
                .commit_all(st_commit_all),
                .discard_all(st_discard_all),
                .session_state_count(state_count),
                .apply_busy(),
                .apply_done(st_apply_done),
                .apply_overflow(state_apply_overflow),
                .count_prepares(st_count_prepares),
                .count_commits(st_count_commits),
                .count_discards(st_count_discards),
                .count_reads(st_count_reads),
                .count_generation_advances(st_count_generation_advances),
                .count_commits_applied(count_state_commits_applied),
                .count_rows_committed(count_state_rows_committed),
                .count_bytes_written(count_state_bytes_written)
            );
        end else begin : g_no_state_compat
            assign st_op_done = 1'b1;
            assign st_op_ok = 1'b0;
            assign st_op_trap_class = ot_a3_pkg::A3_TRAP_CAPABILITY;
            assign st_apply_done = 1'b1;
            assign state_apply_overflow = 1'b0;
            assign st_count_prepares = 32'd0;
            assign st_count_commits = 32'd0;
            assign st_count_discards = 32'd0;
            assign st_count_reads = 32'd0;
            assign st_count_generation_advances = 32'd0;
            assign count_state_commits_applied = 32'd0;
            assign count_state_rows_committed = 32'd0;
            assign count_state_bytes_written = 64'd0;
        end
    endgenerate

    // -- resolver bank -----------------------------------------------------
    reg           bank_start;
    reg           bank_abort;
    wire          bank_desc_req;
    wire [31:0]   bank_desc_id;
    wire          bank_done;
    wire          bank_fault;
    wire [15:0]   bank_trap_class;
    wire [5:0]    bank_slot_valid;
    wire [6*32-1:0] bank_slot_descriptor_id;
    wire [6*32-1:0] bank_slot_extent;
    wire [6*8-1:0]  bank_slot_axis;
    wire [6*64-1:0] bank_slot_offset;
    wire [6*8-1:0]  bank_slot_rank;
    wire [6*16-1:0] bank_slot_object;
    wire [6*40-1:0] bank_slot_lo;
    wire [6*40-1:0] bank_slot_hi;
    wire [5:0]      bank_slot_write;
    wire [6*32-1:0] bank_slot_scale_object;
    wire [5:0]      bank_slot_scale_valid;
    reg  [511:0]    op_payload;

    ot_a3_resolver_bank #(
        .FAST_SCAN(FAST_SCAN),
        .FAST_WALK(FAST_WALK)
    ) bank (
        .clk(clk),
        .rst_n(rst_n),
        .clear(xact_clear | bank_abort),
        .start(bank_start),
        .op_payload(op_payload),
        .desc_req(bank_desc_req),
        .desc_id(bank_desc_id),
        .desc_valid(desc_valid),
        .desc_fault(desc_fault),
        .desc_data(desc_data),
        .loop_query_id(bank_loop_query_id),
        .loop_query_active(loop_query_active[6:1]),
        .loop_query_value(loop_query_value[7*32-1:32]),
        .loop_query_symbol_bounded(loop_query_symbol_bounded[6:1]),
        .loop_query_divisor(loop_query_divisor[7*32-1:32]),
        .loop_query_bound_value(loop_query_bound_value[7*32-1:32]),
        .sym_values(sym_values),
        .sym_bound(sym_bounds),
        .div_req(bank_div_req),
        .div_num(bank_div_num),
        .div_den(bank_div_den),
        .div_done(div_done[6:1]),
        .div_quot(div_quot),
        .div_rem(div_rem),
        .busy(),
        .done(bank_done),
        .fault(bank_fault),
        .trap_class(bank_trap_class),
        .slot_valid(bank_slot_valid),
        .slot_descriptor_id(bank_slot_descriptor_id),
        .slot_extent(bank_slot_extent),
        .slot_axis(bank_slot_axis),
        .slot_offset(bank_slot_offset),
        .slot_rank(bank_slot_rank),
        .slot_object(bank_slot_object),
        .slot_lo(bank_slot_lo),
        .slot_hi(bank_slot_hi),
        .slot_write(bank_slot_write),
        .slot_scale_object(bank_slot_scale_object),
        .slot_scale_valid(bank_slot_scale_valid)
    );

    // The bank owns the descriptor port while it resolves; the sequencer's
    // own reads own it otherwise.  Only one of the two is ever in flight.
    reg         seq_desc_req;
    reg  [31:0] seq_desc_id;
    wire        bank_owns_desc = (state == S_RESOLVE);
    assign desc_req = bank_owns_desc ? bank_desc_req : seq_desc_req;
    assign desc_id  = bank_owns_desc ? bank_desc_id  : seq_desc_id;

    // -- dependence table ---------------------------------------------------
    reg         dep_insert_valid;
    reg  [15:0] dep_insert_object;
    reg  [39:0] dep_insert_lo;
    reg  [39:0] dep_insert_hi;
    reg         dep_insert_write;
    reg         dep_check0_valid;
    reg  [15:0] dep_check0_object;
    reg  [39:0] dep_check0_lo;
    reg  [39:0] dep_check0_hi;
    reg         dep_check0_write;
    wire        dep_check0_conflict;
    reg         dep_check1_valid;
    reg  [15:0] dep_check1_object;
    reg  [39:0] dep_check1_lo;
    reg  [39:0] dep_check1_hi;
    reg         dep_check1_write;
    wire        dep_check1_conflict;

    ot_a3_dependence_table deps (
        .clk(clk),
        .rst_n(rst_n),
        .clear(xact_clear),
        .insert_valid(dep_insert_valid),
        .insert_slot(issue_slot_q),
        .insert_object(dep_insert_object),
        .insert_lo(dep_insert_lo),
        .insert_hi(dep_insert_hi),
        .insert_write(dep_insert_write),
        .check0_valid(dep_check0_valid),
        .check0_object(dep_check0_object),
        .check0_lo(dep_check0_lo),
        .check0_hi(dep_check0_hi),
        .check0_write(dep_check0_write),
        .check0_conflict(dep_check0_conflict),
        .check1_valid(dep_check1_valid),
        .check1_object(dep_check1_object),
        .check1_lo(dep_check1_lo),
        .check1_hi(dep_check1_hi),
        .check1_write(dep_check1_write),
        .check1_conflict(dep_check1_conflict),
        .release_valid(irs_retire_valid),
        .release_slot(irs_retire_slot),
        .dbg_ranges_used()
    );

    assign dbg_decode_error = dec_out_error;
    assign dbg_source_operation_id = dec_source_operation_id;
    assign dbg_wait_fault_event = evt_wait_fault_event;
    assign dbg_loop_action = loop_action;

    // -- descriptor header view -------------------------------------------
    wire [31:0]  desc_magic         = desc_data[31:0];
    wire [15:0]  desc_type          = desc_data[47:32];
    wire [7:0]   desc_type_major    = desc_data[55:48];
    wire [31:0]  desc_payload_offset= desc_data[351:320];   // byte 40
    wire [511:0] desc_payload       = desc_data[1023:512];
    wire         desc_header_ok = !desc_fault &&
                                  (desc_magic == ot_a3_pkg::A3_DESCRIPTOR_MAGIC) &&
                                  (desc_type_major == ot_a3_pkg::A3_TYPE_MAJOR) &&
                                  (desc_payload_offset == 32'd64);

    // -- predicate payload view -------------------------------------------
    wire [7:0]  pred_kind       = pred_payload[7:0];
    wire [7:0]  pred_comparison = pred_payload[15:8];
    wire [31:0] pred_selector   = pred_payload[63:32];
    wire [63:0] pred_immediate  = pred_payload[127:64];
    wire [31:0] pred_object_id  = pred_payload[159:128];
    wire [31:0] pred_element    = pred_payload[191:160];

    wire [63:0] pred_left = sym_value;
    reg  pred_compare_result;
    always @* begin
        case (pred_comparison)
            ot_a3_pkg::A3_CMP_EQ: pred_compare_result = (pred_left == pred_immediate);
            ot_a3_pkg::A3_CMP_NE: pred_compare_result = (pred_left != pred_immediate);
            ot_a3_pkg::A3_CMP_LT: pred_compare_result = (pred_left <  pred_immediate);
            ot_a3_pkg::A3_CMP_LE: pred_compare_result = (pred_left <= pred_immediate);
            ot_a3_pkg::A3_CMP_GT: pred_compare_result = (pred_left >  pred_immediate);
            default:   pred_compare_result = (pred_left >= pred_immediate);
        endcase
    end

    wire [63:0] loop_left = {32'd0, pq_value};
    reg  loop_compare_result;
    always @* begin
        case (pred_comparison)
            ot_a3_pkg::A3_CMP_EQ: loop_compare_result = (loop_left == pred_immediate);
            ot_a3_pkg::A3_CMP_NE: loop_compare_result = (loop_left != pred_immediate);
            ot_a3_pkg::A3_CMP_LT: loop_compare_result = (loop_left <  pred_immediate);
            ot_a3_pkg::A3_CMP_LE: loop_compare_result = (loop_left <= pred_immediate);
            ot_a3_pkg::A3_CMP_GT: loop_compare_result = (loop_left >  pred_immediate);
            default:   loop_compare_result = (loop_left >= pred_immediate);
        endcase
    end

    wire predicated = ins_flags[ot_a3_pkg::A3_FLAG_PREDICATED];
    wire invert     = ins_flags[ot_a3_pkg::A3_FLAG_PREDICATE_INVERT];
    wire is_control = (ins_major == ot_a3_pkg::A3_MAJOR_CONTROL);
    wire [15:0] expected_type = ot_a3_pkg::a3_family_descriptor_type(ins_major);
    // Watchdog: the issue serial against max_retired_work (section 3.2 item
    // 6) -- the golden model's ``retired`` at every fetch is exactly the
    // count of instructions it has retired in program order so far.
    wire work_exceeded = ({32'd0, serial} > work_bound);

    // -- the instruction's dependence ranges -------------------------------
    // Index 2s is view slot s (from the bank), 2s + 1 its scale object as a
    // whole-object read, 12 and 13 the family ranges: the COMMUNICATION local
    // range for LINK, the committed and prepared objects for STATE.
    reg          use_bank;
    reg  [1:0]   aux_valid;
    reg  [15:0]  aux_object [0:1];
    reg  [39:0]  aux_lo     [0:1];
    reg  [39:0]  aux_hi     [0:1];
    reg  [1:0]   aux_write;

    reg  [13:0]  rng_valid;
    reg  [15:0]  rng_object [0:13];
    reg  [39:0]  rng_lo     [0:13];
    reg  [39:0]  rng_hi     [0:13];
    reg  [13:0]  rng_write;
    integer rs;
    always @* begin
        for (rs = 0; rs < 6; rs = rs + 1) begin
            rng_valid[2*rs]   = use_bank && bank_slot_valid[rs];
            rng_object[2*rs]  = bank_slot_object[rs*16 +: 16];
            rng_lo[2*rs]      = bank_slot_lo[rs*40 +: 40];
            rng_hi[2*rs]      = bank_slot_hi[rs*40 +: 40];
            rng_write[2*rs]   = bank_slot_write[rs];
            rng_valid[2*rs+1] = use_bank && bank_slot_valid[rs] &&
                                bank_slot_scale_valid[rs];
            rng_object[2*rs+1] = bank_slot_scale_object[rs*32 +: 16];
            rng_lo[2*rs+1]    = 40'd0;
            rng_hi[2*rs+1]    = {40{1'b1}};
            rng_write[2*rs+1] = 1'b0;
        end
        rng_valid[12]  = aux_valid[0];
        rng_object[12] = aux_object[0];
        rng_lo[12]     = aux_lo[0];
        rng_hi[12]     = aux_hi[0];
        rng_write[12]  = aux_write[0];
        rng_valid[13]  = aux_valid[1];
        rng_object[13] = aux_object[1];
        rng_lo[13]     = aux_lo[1];
        rng_hi[13]     = aux_hi[1];
        rng_write[13]  = aux_write[1];
    end

    function automatic [3:0] lowest_bit;
        input [13:0] mask;
        integer b;
        begin
            lowest_bit = 4'd15;
            for (b = 13; b >= 0; b = b - 1)
                if (mask[b]) lowest_bit = b[3:0];
        end
    endfunction

    reg  [13:0] hz_work;
    reg         hz_acc;
    reg         hz_retire_seen;     // a retirement landed since the scan began
    wire [3:0]  hz_first  = lowest_bit(hz_work);
    wire [13:0] hz_rest   = hz_work & ~(14'd1 << hz_first);
    wire [3:0]  hz_second = lowest_bit(hz_rest);
    wire        hz_conflict_now = hz_acc | dep_check0_conflict | dep_check1_conflict;

    reg  [13:0] pub_work;
    wire [3:0]  pub_first = lowest_bit(pub_work);

    // COMMUNICATION payload (runtime/abi3/descriptors.COMMUNICATION_PAYLOAD)
    wire [7:0]  comm_vc          = desc_payload[31:24];
    wire [31:0] comm_local_obj   = desc_payload[159:128];
    wire [63:0] comm_local_off   = desc_payload[255:192];
    wire [63:0] comm_byte_extent = desc_payload[383:320];
    wire [64:0] comm_local_end   = {1'b0, comm_local_off} + {1'b0, comm_byte_extent};
    wire        comm_range_fits  = (comm_local_off[63:40] == 24'd0) &&
                                   (comm_local_end[64:40] == 25'd0);
    // SCHEDULE payload: queue_index at byte 1
    wire [7:0]  sched_queue_index = desc_payload[15:8];
    // STATE payload: committed (byte 8) and prepared (byte 12) objects
    wire [31:0] state_committed_obj = state_payload[95:64];
    wire [31:0] state_prepared_obj  = state_payload[127:96];
    // OPERATOR payload: schedule_id at byte 20
    wire [31:0] op_schedule_id = desc_payload[191:160];

    // -- frozen counters after an asynchronous fault ----------------------
    reg         frozen;
    reg  [31:0] frozen_loop_iterations;
    reg  [31:0] frozen_wait_events;
    reg  [31:0] frozen_signals;
    reg  [31:0] frozen_state_prepares;
    reg  [31:0] frozen_state_commits;
    reg  [31:0] frozen_state_discards;
    reg  [31:0] frozen_state_reads;
    reg  [31:0] frozen_state_advances;
    assign count_loop_iterations = frozen ? frozen_loop_iterations : loop_iteration_count;
    assign count_wait_events     = frozen ? frozen_wait_events : sb_wait_count;
    assign count_signals         = frozen ? frozen_signals : sb_signal_count;
    assign count_state_prepares  = frozen ? frozen_state_prepares : st_count_prepares;
    assign count_state_commits   = frozen ? frozen_state_commits : st_count_commits;
    assign count_state_discards  = frozen ? frozen_state_discards : st_count_discards;
    assign count_state_reads     = frozen ? frozen_state_reads : st_count_reads;
    assign count_state_generation_advances =
        frozen ? frozen_state_advances : st_count_generation_advances;

    // The counter snapshot an issue writes (payload lane 6).  The retired
    // count it carries is the issue serial itself: every operation issued
    // before this one has a lower serial and, if this one is the first to
    // fault, will complete without fault, so at that fault the golden
    // model's ``retired`` -- the instructions it retired in program order
    // before stopping -- is exactly the serial.  Signals likewise carry the
    // older outstanding producers that will still complete.
    wire [31:0] snap_retired = serial;
    wire [31:0] snap_signals = sb_signal_count + {26'd0, irs_outstanding_with_event} +
                               (retire_signals ? 32'd1 : 32'd0) +
                               (evt_control_valid ? 32'd1 : 32'd0);
    wire [511:0] snapshot_word = {
        pc,                                     // [511:480]
        serial,                                 // [479:448]
        st_count_generation_advances,           // [447:416]
        st_count_reads,                         // [415:384]
        st_count_discards,                      // [383:352]
        st_count_commits,                       // [351:320]
        st_count_prepares,                      // [319:288]
        snap_retired,                           // [287:256]
        snap_signals,                           // [255:224]
        sb_wait_count,                          // [223:192]
        count_branches,                         // [191:160]
        loop_iteration_count,                   // [159:128]
        count_views_resolved,                   // [127:96]
        count_predicated_off,                   // [95:64]
        count_issued,                           // [63:32]
        count_fetched                           // [31:0]
    };

    // Issue handshake: the allocation, the pending mark and the snapshot
    // write all land in the handshake cycle, so a completion reported in
    // the very next cycle finds its entry.
    wire issue_fire = (state == S_ISSUE) && issue_valid && issue_ready;
    always @* begin
        irs_alloc_valid = issue_fire;
        evt_issue_valid = issue_fire && (ins_signal_event_id != ot_a3_pkg::A3_NO_ID);
    end

    // A CONTROL retirement, counted one cycle later through the same adder
    // as engine completions (see the retirement block below).
    reg ctl_retire_q;

    // A pending precise trap, held until nothing is outstanding.
    reg [15:0] pending_trap_class;
    reg [31:0] pending_trap_index;

    // -- tasks --------------------------------------------------------------
    // CONTROL retirement: counts, publishes the signal event, advances the
    // serial.  Called from every CONTROL retirement.
    task retire_control;
        begin
            ctl_retire_q <= 1'b1;
            serial <= serial + 32'd1;
            evt_control_valid <= (ins_signal_event_id != ot_a3_pkg::A3_NO_ID);
        end
    endtask

    // Start the fetch of the instruction at ``next_index`` (already
    // program_base + pc) and enter the bound/watchdog check.  Under
    // FAST_FRONT_END the request is registered here, one state before
    // S_CHECK_PC, so it is on the wire *during* the check and the store's
    // one-cycle answer lands in the first S_FETCH_WAIT cycle instead of the
    // second.  The checks themselves do not move and neither does the cycle
    // they trap in; what changes is that a fetch the checks then reject has
    // already been presented to the store, which for a read-only port is one
    // ignored read on the one instruction that traps.  The address is one
    // 32-bit add or increment away from a register in every caller, never an
    // add chain, so nothing lengthens.
    task launch_fetch;
        input [31:0] next_index;
        begin
            if (FAST_FRONT_END != 0) begin
                imem_req   <= 1'b1;
                imem_index <= next_index;
            end
            state <= S_CHECK_PC;
        end
    endtask

    // Enter the wait stage.  S_WAIT_REQ exists only to read a register the
    // caller already holds, so under FAST_FRONT_END the caller makes the
    // decision and launches the descriptor read itself.
    task enter_wait_stage;
        begin
            if (FAST_FRONT_END == 0) begin
                state <= S_WAIT_REQ;
            end else if (ins_wait_set_id != ot_a3_pkg::A3_NO_ID) begin
                seq_desc_req <= 1'b1;
                seq_desc_id <= ins_wait_set_id;
                state <= S_WAIT_WAIT;
            end else begin
                state <= S_DISPATCH;
            end
        end
    endtask

    // A precise front-end trap.  Applied at once when nothing is outstanding;
    // otherwise held, because an outstanding operation that faults has the
    // lower serial and wins (section 3.2 item 5).
    task raise_trap;
        input [15:0] class_value;
        input [31:0] fault_index;
        begin
            pending_trap_class <= class_value;
            pending_trap_index <= fault_index;
            predicate_read_req <= 1'b0;
            state <= S_TRAP_WAIT;
        end
    endtask

    task apply_trap;
        input [15:0] class_value;
        input [31:0] fault_index;
        begin
            trap_class <= class_value;
            first_fault_instruction <= fault_index;
            trapped <= 1'b1;
            predicate_read_req <= 1'b0;
            if (STATE_COMPAT != 0) begin
                st_discard_all <= 1'b1;
                state <= S_DISCARD;
            end else begin
                // Live-buffer execution is fail-stop.  There is no staged
                // image to discard and partial buffers are never reused.
                state <= S_DONE;
            end
        end
    endtask

    // Abandon the instruction in flight for an asynchronous engine fault.
    task abort_for_fault;
        begin
            predicate_read_req <= 1'b0;
            bank_abort <= 1'b1;
            issue_valid_q <= 1'b0;
            state <= S_FAULT_DRAIN;
        end
    endtask

    // Publish one resolved view: the port pulse and the payload write.
    task publish_view;
        input [2:0] s;
        begin
            view_valid <= 1'b1;
            view_descriptor_id <= bank_slot_descriptor_id[s*32 +: 32];
            view_slot <= s;
            view_extent <= bank_slot_extent[s*32 +: 32];
            view_extent_axis <= bank_slot_axis[s*8 +: 8];
            view_element_offset <= bank_slot_offset[s*64 +: 64];
            view_rank <= bank_slot_rank[s*8 +: 8];
            view_irs_slot <= issue_slot_q;
            count_views_resolved <= count_views_resolved + 32'd1;
            irs_we <= 1'b1;
            irs_wslot <= issue_slot_q;
            irs_wlane <= s;
            irs_wdata <= {
                238'd0,
                bank_slot_scale_valid[s],                 // [273]
                bank_slot_scale_object[s*32 +: 32],       // [272:241]
                bank_slot_write[s],                       // [240]
                bank_slot_hi[s*40 +: 40],                 // [239:200]
                bank_slot_lo[s*40 +: 40],                 // [199:160]
                bank_slot_object[s*16 +: 16],             // [159:144]
                bank_slot_rank[s*8 +: 8],                 // [143:136]
                bank_slot_offset[s*64 +: 64],             // [135:72]
                bank_slot_axis[s*8 +: 8],                 // [71:64]
                bank_slot_extent[s*32 +: 32],             // [63:32]
                bank_slot_descriptor_id[s*32 +: 32]       // [31:0]
            };
        end
    endtask

    // Whether the front end is in a state an asynchronous fault may abort.
    wire abortable = (state != S_IDLE) && (state != S_DONE) &&
                     (state != S_COMMIT) && (state != S_DISCARD) &&
                     (state != S_TRAP_WAIT) &&
                     (state != S_FAULT_DRAIN) && (state != S_FAULT_READ) &&
                     (state != S_FAULT_WAIT) && (state != S_FAULT_APPLY);

    integer j;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            pc <= 32'd0;
            instruction_count <= 32'd0;
            program_base <= 32'd0;
            work_bound <= 64'd0;
            state_count <= 32'd0;
            record <= 256'd0;
            xact_clear <= 1'b0;
            serial <= 32'd0;
            drain_next <= DRAIN_RETIRE;
            busy <= 1'b0;
            done <= 1'b0;
            complete <= 1'b0;
            trapped <= 1'b0;
            trap_class <= ot_a3_pkg::A3_TRAP_NONE;
            first_fault_instruction <= ot_a3_pkg::A3_NO_ID;
            imem_req <= 1'b0;
            imem_index <= 32'd0;
            seq_desc_req <= 1'b0;
            seq_desc_id <= ot_a3_pkg::A3_NO_ID;
            sym_index_q <= 4'd0;
            predicate_read_req <= 1'b0;
            predicate_read_object_id <= ot_a3_pkg::A3_NO_ID;
            predicate_read_element_index <= 32'd0;
            issue_valid_q <= 1'b0;
            issue_family <= 8'd0;
            issue_sub <= 8'd0;
            issue_descriptor_id <= ot_a3_pkg::A3_NO_ID;
            issue_index <= ot_a3_pkg::A3_NO_ID;
            issue_serial <= 32'd0;
            issue_slot <= 5'd0;
            issue_queue <= 5'd0;
            issue_slot_q <= 5'd0;
            issue_queue_q <= 5'd0;
            irs_we <= 1'b0;
            irs_wslot <= 5'd0;
            irs_wlane <= 3'd0;
            irs_wdata <= 512'd0;
            irs_re <= 1'b0;
            irs_rslot <= 5'd0;
            irs_rlane <= 3'd0;
            view_valid <= 1'b0;
            view_descriptor_id <= ot_a3_pkg::A3_NO_ID;
            view_slot <= 3'd0;
            view_extent <= 32'd0;
            view_extent_axis <= 8'd0;
            view_element_offset <= 64'd0;
            view_rank <= 8'd0;
            view_irs_slot <= 5'd0;
            count_views_resolved <= 32'd0;
            op_payload <= 512'd0;
            bank_start <= 1'b0;
            bank_abort <= 1'b0;
            use_bank <= 1'b0;
            aux_valid <= 2'b00;
            aux_write <= 2'b00;
            for (j = 0; j < 2; j = j + 1) begin
                aux_object[j] <= 16'd0;
                aux_lo[j] <= 40'd0;
                aux_hi[j] <= 40'd0;
            end
            hz_work <= 14'd0;
            hz_acc <= 1'b0;
            hz_retire_seen <= 1'b0;
            pub_work <= 14'd0;
            dep_insert_valid <= 1'b0;
            dep_insert_object <= 16'd0;
            dep_insert_lo <= 40'd0;
            dep_insert_hi <= 40'd0;
            dep_insert_write <= 1'b0;
            dep_check0_valid <= 1'b0;
            dep_check0_object <= 16'd0;
            dep_check0_lo <= 40'd0;
            dep_check0_hi <= 40'd0;
            dep_check0_write <= 1'b0;
            dep_check1_valid <= 1'b0;
            dep_check1_object <= 16'd0;
            dep_check1_lo <= 40'd0;
            dep_check1_hi <= 40'd0;
            dep_check1_write <= 1'b0;
            dec_in_valid <= 1'b0;
            crc_valid_vec <= {CRC_CACHE_ENTRIES{1'b0}};
            crc_phase_vec <= {(CRC_CACHE_ENTRIES*CRC_PHASE_W){1'b0}};
            crc_hit_q <= 1'b0;
            crc_cached_q <= 1'b0;
            crc_idx_q <= {CRC_IDX_W{1'b0}};
            dbg_crc_full <= 32'd0;
            dbg_crc_skipped <= 32'd0;
            loop_setup_valid <= 1'b0;
            loop_next_valid <= 1'b0;
            loop_query_id_q <= ot_a3_pkg::A3_NO_ID;
            loop_payload <= 512'd0;
            evt_control_valid <= 1'b0;
            evt_wait_start <= 1'b0;
            evt_wait_payload <= 512'd0;
            evt_wait_acquire <= 1'b0;
            st_op_valid <= 1'b0;
            st_commit_all <= 1'b0;
            st_discard_all <= 1'b0;
            pred_payload <= 512'd0;
            state_payload <= 512'd0;
            ins_major <= 8'd0;
            ins_sub <= 8'd0;
            ins_flags <= 16'd0;
            ins_predicate_id <= ot_a3_pkg::A3_NO_ID;
            ins_descriptor_id <= ot_a3_pkg::A3_NO_ID;
            ins_wait_set_id <= ot_a3_pkg::A3_NO_ID;
            ins_signal_event_id <= ot_a3_pkg::A3_NO_ID;
            ins_control_id <= ot_a3_pkg::A3_NO_ID;
            count_fetched <= 32'd0;
            count_retired <= 32'd0;
            count_predicated_off <= 32'd0;
            count_issued <= 32'd0;
            count_branches <= 32'd0;
            pending_trap_class <= ot_a3_pkg::A3_TRAP_NONE;
            pending_trap_index <= ot_a3_pkg::A3_NO_ID;
            ctl_retire_q <= 1'b0;
            frozen <= 1'b0;
            frozen_loop_iterations <= 32'd0;
            frozen_wait_events <= 32'd0;
            frozen_signals <= 32'd0;
            frozen_state_prepares <= 32'd0;
            frozen_state_commits <= 32'd0;
            frozen_state_discards <= 32'd0;
            frozen_state_reads <= 32'd0;
            frozen_state_advances <= 32'd0;
            dbg_dep_stalls <= 32'd0;
            dbg_wait_stalls <= 32'd0;
        end else begin
            done <= 1'b0;
            xact_clear <= 1'b0;
            imem_req <= 1'b0;
            seq_desc_req <= 1'b0;
            view_valid <= 1'b0;
            irs_we <= 1'b0;
            irs_re <= 1'b0;
            bank_start <= 1'b0;
            bank_abort <= 1'b0;
            dep_insert_valid <= 1'b0;
            dep_check0_valid <= 1'b0;
            dep_check1_valid <= 1'b0;
            dec_in_valid <= 1'b0;
            loop_setup_valid <= 1'b0;
            loop_next_valid <= 1'b0;
            evt_control_valid <= 1'b0;
            evt_wait_start <= 1'b0;
            st_op_valid <= 1'b0;
            st_commit_all <= 1'b0;
            st_discard_all <= 1'b0;
            ctl_retire_q <= 1'b0;

            // -- retirements land independently of the front end ----------
            // One adder for both sources of a retirement: a completion that
            // counts and a CONTROL instruction retired by the front end in
            // the previous cycle (the ctl_retire_q pulse), so neither can
            // hide the other.
            count_retired <= count_retired + (retire_counts ? 32'd1 : 32'd0) +
                             (ctl_retire_q ? 32'd1 : 32'd0);
            if (irs_retire_valid)
                hz_retire_seen <= 1'b1;
            if (evt_wait_stalled)
                dbg_wait_stalls <= dbg_wait_stalls + 32'd1;

            // An asynchronous engine fault stops issue in the cycle it is
            // reported (section 3.2 item 5).  The record is sticky until the
            // transaction clear, which lands one cycle after start: a fault
            // left by the previous transaction is not this one's.
            if (irs_fault_valid && abortable && !xact_clear) begin
                abort_for_fault;
            end else begin
            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        complete <= 1'b0;
                        trapped <= 1'b0;
                        trap_class <= ot_a3_pkg::A3_TRAP_NONE;
                        first_fault_instruction <= ot_a3_pkg::A3_NO_ID;
                        pc <= cfg_entry_pc;
                        program_base <= cfg_program_base;
                        instruction_count <= cfg_instruction_count;
                        // A validated bit never spans a transaction, so it can
                        // never refer to a program image the host replaced
                        // between transactions.
                        crc_valid_vec <= {CRC_CACHE_ENTRIES{1'b0}};
                        crc_phase_vec <= {(CRC_CACHE_ENTRIES*CRC_PHASE_W){1'b0}};
                        crc_hit_q <= 1'b0;
                        crc_cached_q <= 1'b0;
                        dbg_crc_full <= 32'd0;
                        dbg_crc_skipped <= 32'd0;
                        work_bound <= cfg_max_retired_work;
                        state_count <= cfg_state_count;
                        serial <= 32'd0;
                        count_fetched <= 32'd0;
                        count_retired <= 32'd0;
                        count_predicated_off <= 32'd0;
                        count_issued <= 32'd0;
                        count_branches <= 32'd0;
                        count_views_resolved <= 32'd0;
                        frozen <= 1'b0;
                        dbg_dep_stalls <= 32'd0;
                        dbg_wait_stalls <= 32'd0;
                        predicate_read_req <= 1'b0;
                        predicate_read_object_id <= ot_a3_pkg::A3_NO_ID;
                        predicate_read_element_index <= 32'd0;
                        issue_valid_q <= 1'b0;
                        use_bank <= 1'b0;
                        aux_valid <= 2'b00;
                        xact_clear <= 1'b1;
                        if ((STATE_COMPAT == 0) &&
                            (cfg_state_count != 32'd0)) begin
                            trapped <= 1'b1;
                            trap_class <= ot_a3_pkg::A3_TRAP_CAPABILITY;
                            first_fault_instruction <= ot_a3_pkg::A3_NO_ID;
                            state <= S_DONE;
                        end else begin
                            launch_fetch(cfg_program_base + cfg_entry_pc);
                        end
                    end
                end

                // -- fetch ------------------------------------------------
                S_CHECK_PC: begin
                    use_bank <= 1'b0;
                    aux_valid <= 2'b00;
                    if (pc >= instruction_count) begin
                        // Running off the authenticated body, or a control
                        // transfer that leaves it, is an illegal control flow.
                        raise_trap(ot_a3_pkg::A3_TRAP_ILLEGAL, pc);
                    end else begin
                        count_fetched <= count_fetched + 32'd1;
                        if (work_exceeded) begin
                            raise_trap(ot_a3_pkg::A3_TRAP_WATCHDOG, pc);
                        end else begin
                            // Resolve the validated bit here, two states before
                            // the decoder handshake consumes it.
                            crc_cached_q <= crc_in_range;
                            crc_idx_q <= crc_idx;
                            crc_hit_q <= crc_in_range && crc_valid_vec[crc_idx] &&
                                         ((CRC_PERIOD == 0) ||
                                          ((CRC_PERIOD >= 2) &&
                                           (crc_phase_vec[crc_idx*CRC_PHASE_W +: CRC_PHASE_W]
                                            != {CRC_PHASE_W{1'b0}})));
                            // Under FAST_FRONT_END the request was registered
                            // by the state that set this pc and is on the wire
                            // now; there is nothing left to drive here.
                            if (FAST_FRONT_END == 0) begin
                                imem_req <= 1'b1;
                                imem_index <= program_base + pc;
                            end
                            state <= S_FETCH_WAIT;
                        end
                    end
                end
                S_FETCH_WAIT: begin
                    if (imem_valid) begin
                        record <= imem_data;
                        if (FAST_FRONT_END != 0) begin
                            // S_DECODE_PUSH only ever offered the record the
                            // cycle after it arrived; ``record`` is written on
                            // this same edge, so the offer can ride with it.
                            dec_in_valid <= 1'b1;
                            state <= S_DECODE_WAIT;
                        end else begin
                            state <= S_DECODE_PUSH;
                        end
                    end
                end
                S_DECODE_PUSH: begin
                    if (dec_in_ready) begin
                        dec_in_valid <= 1'b1;
                        state <= S_DECODE_WAIT;
                    end
                end
                S_DECODE_WAIT: begin
                    // The admission offer is held until the decoder takes it.
                    // S_DECODE_PUSH sampled dec_in_ready a cycle before it
                    // raised dec_in_valid; holding is strictly safer and, with
                    // out_ready tied high and one instruction in flight, never
                    // fires.
                    if (FAST_FRONT_END != 0)
                        if (dec_in_valid && !dec_in_ready)
                            dec_in_valid <= 1'b1;
                    if (dec_out_valid) begin
                        // Record what the recurrence learned about this index.
                        // A bit is set only by a fetch that actually ran the
                        // recurrence and saw it pass; a failed CRC leaves the
                        // index unvalidated (and traps below anyway).
                        if (crc_cached_q && !crc_hit_q) begin
                            if (dec_out_error != ot_a3_pkg::A3_ERR_CRC)
                                crc_valid_vec[crc_idx_q] <= 1'b1;
                            crc_phase_vec[crc_idx_q*CRC_PHASE_W +: CRC_PHASE_W] <=
                                (CRC_PERIOD >= 2) ? {{(CRC_PHASE_W-1){1'b0}}, 1'b1}
                                                  : {CRC_PHASE_W{1'b0}};
                        end else if (crc_cached_q && crc_hit_q) begin
                            crc_phase_vec[crc_idx_q*CRC_PHASE_W +: CRC_PHASE_W] <=
                                (crc_phase_vec[crc_idx_q*CRC_PHASE_W +: CRC_PHASE_W] ==
                                 (CRC_PERIOD[CRC_PHASE_W-1:0] - 1'b1))
                                    ? {CRC_PHASE_W{1'b0}}
                                    : (crc_phase_vec[crc_idx_q*CRC_PHASE_W +: CRC_PHASE_W] + 1'b1);
                        end
                        if (crc_hit_q)
                            dbg_crc_skipped <= dbg_crc_skipped + 32'd1;
                        else
                            dbg_crc_full <= dbg_crc_full + 32'd1;
                        ins_major <= dec_major;
                        ins_sub <= dec_sub;
                        ins_flags <= dec_flags;
                        ins_predicate_id <= dec_predicate_id;
                        ins_descriptor_id <= dec_descriptor_id;
                        ins_wait_set_id <= dec_wait_set_id;
                        ins_signal_event_id <= dec_signal_event_id;
                        ins_control_id <= dec_control_id;
                        if (!dec_out_legal) begin
                            raise_trap(dec_out_trap_class, dec_index);
                        end else if (FAST_FRONT_END == 0) begin
                            state <= S_PRED_REQ;
                        end else if (dec_flags[ot_a3_pkg::A3_FLAG_PREDICATED]) begin
                            // S_PRED_REQ and S_WAIT_REQ read nothing this
                            // cycle has not already produced, so both reads
                            // are launched from here.
                            seq_desc_req <= 1'b1;
                            seq_desc_id <= dec_predicate_id;
                            state <= S_PRED_WAIT;
                        end else if (dec_wait_set_id != ot_a3_pkg::A3_NO_ID) begin
                            seq_desc_req <= 1'b1;
                            seq_desc_id <= dec_wait_set_id;
                            state <= S_WAIT_WAIT;
                        end else begin
                            state <= S_DISPATCH;
                        end
                    end
                end

                // -- predicate --------------------------------------------
                S_PRED_REQ: begin
                    if (!predicated) begin
                        state <= S_WAIT_REQ;
                    end else begin
                        seq_desc_req <= 1'b1;
                        seq_desc_id <= ins_predicate_id;
                        state <= S_PRED_WAIT;
                    end
                end
                S_PRED_WAIT: begin
                    if (desc_valid) begin
                        if (!desc_header_ok || (desc_type != ot_a3_pkg::A3_DESC_PREDICATE)) begin
                            raise_trap(ot_a3_pkg::A3_TRAP_DESCRIPTOR, pc);
                        end else begin
                            pred_payload <= desc_payload;
                            state <= S_PRED_SYM;
                        end
                    end
                end
                S_PRED_SYM: begin
                    // Present the symbol or loop selector one cycle before it
                    // is read so the register file read is not in the compare
                    // path.
                    if (pred_kind == ot_a3_pkg::A3_PRED_PHASE_IS)
                        sym_index_q <= ot_a3_pkg::A3_SYMBOL_PHASE;
                    else
                        sym_index_q <= pred_selector[3:0];
                    loop_query_id_q <= pred_selector;
                    state <= S_PRED_EVAL;
                end
                S_PRED_EVAL: begin
                    case (pred_kind)
                        ot_a3_pkg::A3_PRED_ALWAYS: begin
                            if (invert) begin
                                count_predicated_off <= count_predicated_off + 32'd1;
                                pc <= pc + 32'd1;
                                launch_fetch(imem_index + 32'd1);
                            end else begin
                                enter_wait_stage;
                            end
                        end
                        ot_a3_pkg::A3_PRED_PHASE_IS, ot_a3_pkg::A3_PRED_COMPARE_SYMBOL: begin
                            if (!sym_bound ||
                                ((pred_kind == ot_a3_pkg::A3_PRED_COMPARE_SYMBOL) &&
                                 (pred_selector >= ot_a3_pkg::A3_SYMBOL_COUNT))) begin
                                raise_trap(ot_a3_pkg::A3_TRAP_DESCRIPTOR, pc);
                            end else if ((pred_kind == ot_a3_pkg::A3_PRED_PHASE_IS)
                                         ? ((pred_left == pred_immediate) ^ invert)
                                         : (pred_compare_result ^ invert)) begin
                                enter_wait_stage;
                            end else begin
                                count_predicated_off <= count_predicated_off + 32'd1;
                                pc <= pc + 32'd1;
                                launch_fetch(imem_index + 32'd1);
                            end
                        end
                        ot_a3_pkg::A3_PRED_COMPARE_LOOP: begin
                            if (!pq_active) begin
                                raise_trap(ot_a3_pkg::A3_TRAP_ILLEGAL, pc);
                            end else if (loop_compare_result ^ invert) begin
                                enter_wait_stage;
                            end else begin
                                count_predicated_off <= count_predicated_off + 32'd1;
                                pc <= pc + 32'd1;
                                launch_fetch(imem_index + 32'd1);
                            end
                        end
                        ot_a3_pkg::A3_PRED_LOOP_FIRST, ot_a3_pkg::A3_PRED_LOOP_LAST: begin
                            if ((pq_active &&
                                 ((pred_kind == ot_a3_pkg::A3_PRED_LOOP_FIRST)
                                  ? (pq_value == 32'd0)
                                  : (pq_value == (pq_trip - 32'd1))))
                                ^ invert) begin
                                enter_wait_stage;
                            end else begin
                                count_predicated_off <= count_predicated_off + 32'd1;
                                pc <= pc + 32'd1;
                                launch_fetch(imem_index + 32'd1);
                            end
                        end
                        ot_a3_pkg::A3_PRED_BOOLEAN_OBJECT, ot_a3_pkg::A3_PRED_EOS_MEMBER: begin
                            // The flag word goes through the dependence
                            // table first (section 3.7): a read against an
                            // outstanding write of the word waits for it.
                            dep_check0_valid <= 1'b1;
                            dep_check0_object <= pred_object_id[15:0];
                            dep_check0_lo <= {6'd0, pred_element, 2'b00};
                            dep_check0_hi <= {6'd0, pred_element, 2'b00} + 40'd4;
                            dep_check0_write <= 1'b0;
                            state <= S_PRED_HAZARD;
                        end
                        default: begin
                            // ENGINE_STATUS and ROUTE_VALID require an engine
                            // status interface this controller does not have.
                            // Fail closed on the capability, never guess.
                            raise_trap(ot_a3_pkg::A3_TRAP_CAPABILITY, pc);
                        end
                    endcase
                end
                S_PRED_HAZARD: begin
                    // The check issued last cycle answers now.
                    if (dep_check0_conflict) begin
                        dep_check0_valid <= 1'b1;
                        dbg_dep_stalls <= dbg_dep_stalls + 32'd1;
                    end else begin
                        predicate_read_object_id <= pred_object_id;
                        predicate_read_element_index <= pred_element;
                        predicate_read_req <= 1'b1;
                        state <= S_PRED_OBJECT;
                    end
                end
                S_PRED_OBJECT: begin
                    if (predicate_read_valid) begin
                        predicate_read_req <= 1'b0;
                        if (predicate_read_trap_class != ot_a3_pkg::A3_TRAP_NONE) begin
                            raise_trap(predicate_read_trap_class, pc);
                        end else if (predicate_read_value ^ invert) begin
                            enter_wait_stage;
                        end else begin
                            count_predicated_off <= count_predicated_off + 32'd1;
                            pc <= pc + 32'd1;
                            launch_fetch(imem_index + 32'd1);
                        end
                    end
                end

                // -- wait -------------------------------------------------
                S_WAIT_REQ: begin
                    if (ins_wait_set_id == ot_a3_pkg::A3_NO_ID) begin
                        state <= S_DISPATCH;
                    end else begin
                        seq_desc_req <= 1'b1;
                        seq_desc_id <= ins_wait_set_id;
                        state <= S_WAIT_WAIT;
                    end
                end
                S_WAIT_WAIT: begin
                    if (desc_valid) begin
                        if (!desc_header_ok ||
                            (desc_type != ot_a3_pkg::A3_DESC_EVENT_WAIT_SET)) begin
                            raise_trap(ot_a3_pkg::A3_TRAP_DESCRIPTOR, pc);
                        end else begin
                            evt_wait_start <= 1'b1;
                            evt_wait_payload <= desc_payload;
                            evt_wait_acquire <= ins_flags[ot_a3_pkg::A3_FLAG_WAIT_ACQUIRE];
                            state <= S_WAIT_EVAL;
                        end
                    end
                end
                S_WAIT_EVAL: begin
                    if (evt_wait_done) begin
                        if (!evt_wait_ok)
                            raise_trap(evt_wait_trap_class, pc);
                        else
                            state <= S_DISPATCH;
                    end
                end

                // -- execute ----------------------------------------------
                S_DISPATCH: begin
                    if (is_control) begin
                        case (ins_sub)
                            ot_a3_pkg::A3_CONTROL_NOP,
                            ot_a3_pkg::A3_CONTROL_WAIT,
                            ot_a3_pkg::A3_CONTROL_ASSERT: begin
                                retire_control;
                                pc <= pc + 32'd1;
                                launch_fetch(imem_index + 32'd1);
                            end
                            ot_a3_pkg::A3_CONTROL_FENCE: begin
                                // AM-C2: an ENGINE-scope drain -- the scope
                                // byte of every shipped wait set, and the
                                // amendment's default without one.
                                drain_next <= DRAIN_RETIRE;
                                state <= S_DRAIN;
                            end
                            ot_a3_pkg::A3_CONTROL_BRANCH: begin
                                retire_control;
                                count_branches <= count_branches + 32'd1;
                                pc <= ins_control_id;
                                launch_fetch(program_base + ins_control_id);
                            end
                            ot_a3_pkg::A3_CONTROL_COMPLETE: begin
                                // Implicit SYSTEM drain (AM-C2), then the
                                // completion record.
                                drain_next <= DRAIN_COMPLETE;
                                state <= S_DRAIN;
                            end
                            ot_a3_pkg::A3_CONTROL_TRAP: begin
                                raise_trap(ot_a3_pkg::A3_TRAP_ILLEGAL, pc);
                            end
                            ot_a3_pkg::A3_CONTROL_LOOP_SETUP: begin
                                seq_desc_req <= 1'b1;
                                seq_desc_id <= ins_control_id;
                                state <= S_LOOP_WAIT;
                            end
                            default: begin   // A3_CONTROL_LOOP_NEXT
                                loop_next_valid <= 1'b1;
                                state <= S_LOOP_DONE;
                            end
                        endcase
                    end else begin
                        count_issued <= count_issued + 32'd1;
                        issue_queue_q <= ot_a3_pkg::a3_queue_base(ins_major);
                        if ((ins_major == ot_a3_pkg::A3_MAJOR_RECOVERY) &&
                            (ins_sub == ot_a3_pkg::A3_RECOVERY_ABORT)) begin
                            raise_trap(ot_a3_pkg::A3_TRAP_INTERNAL, pc);
                        end else if (expected_type == ot_a3_pkg::A3_DESC_NONE) begin
                            // RECOVERY: POISON and DRAIN drain (AM-C2), then
                            // issue as a recorded operation.
                            drain_next <= DRAIN_ISSUE;
                            state <= S_DRAIN;
                        end else begin
                            seq_desc_req <= 1'b1;
                            seq_desc_id <= ins_descriptor_id;
                            state <= S_ENG_WAIT;
                        end
                    end
                end

                // -- loops -------------------------------------------------
                S_LOOP_WAIT: begin
                    if (desc_valid) begin
                        if (!desc_header_ok ||
                            (desc_type != ot_a3_pkg::A3_DESC_LOOP_CONTROL)) begin
                            raise_trap(ot_a3_pkg::A3_TRAP_DESCRIPTOR, pc);
                        end else if (FAST_FRONT_END == 0) begin
                            loop_payload <= desc_payload;
                            state <= S_LOOP_SYM;
                        end else begin
                            // S_LOOP_SYM only selected the symbol from a
                            // payload this cycle already has on its input.
                            loop_payload <= desc_payload;
                            if (desc_loop_symbol >= ot_a3_pkg::A3_SYMBOL_COUNT) begin
                                sym_index_q <= 4'd0;
                                if (desc_loop_kind != ot_a3_pkg::A3_SELECTOR_CONSTANT) begin
                                    raise_trap(ot_a3_pkg::A3_TRAP_DESCRIPTOR, pc);
                                end else begin
                                    loop_setup_valid <= 1'b1;
                                    state <= S_LOOP_DONE;
                                end
                            end else begin
                                sym_index_q <= desc_loop_symbol[3:0];
                                state <= S_LOOP_OP;
                            end
                        end
                    end
                end
                S_LOOP_SYM: begin
                    if (loop_symbol_id >= ot_a3_pkg::A3_SYMBOL_COUNT) begin
                        sym_index_q <= 4'd0;
                        if (loop_bound_kind != ot_a3_pkg::A3_SELECTOR_CONSTANT) begin
                            // Symbol-bounded loop naming a symbol outside the
                            // frozen registry.
                            raise_trap(ot_a3_pkg::A3_TRAP_DESCRIPTOR, pc);
                        end else begin
                            loop_setup_valid <= 1'b1;
                            state <= S_LOOP_DONE;
                        end
                    end else begin
                        sym_index_q <= loop_symbol_id[3:0];
                        state <= S_LOOP_OP;
                    end
                end
                S_LOOP_OP: begin
                    loop_setup_valid <= 1'b1;
                    state <= S_LOOP_DONE;
                end
                S_LOOP_DONE: begin
                    if (loop_done) begin
                        if (loop_trap_valid) begin
                            raise_trap(loop_trap_class, pc);
                        end else begin
                            retire_control;
                            pc <= loop_next_pc;
                            launch_fetch(program_base + loop_next_pc);
                        end
                    end
                end

                // -- engine families ---------------------------------------
                S_ENG_WAIT: begin
                    if (desc_valid) begin
                        if (!desc_header_ok || (desc_type != expected_type)) begin
                            // STRICTER: the golden model type-checks only the
                            // STATE family here; every family is checked.
                            raise_trap(ot_a3_pkg::A3_TRAP_DESCRIPTOR, pc);
                        end else if (ins_major == ot_a3_pkg::A3_MAJOR_STATE) begin
                            if (STATE_COMPAT == 0) begin
                                raise_trap(ot_a3_pkg::A3_TRAP_CAPABILITY, pc);
                            end else begin
                                state_payload <= desc_payload;
                                sym_index_q <= ot_a3_pkg::A3_SYMBOL_SPAN_TOKENS;
                                state <= S_STATE_SYM;
                            end
                        end else if (expected_type == ot_a3_pkg::A3_DESC_OPERATOR) begin
                            // A4/A13: an engine is handed extents, not just a
                            // descriptor ID, so every operand view this
                            // operator names is resolved before the issue.
                            op_payload <= desc_payload;
                            use_bank <= 1'b1;
                            if (op_schedule_id == ot_a3_pkg::A3_NO_ID) begin
                                bank_start <= 1'b1;
                                state <= S_RESOLVE;
                            end else begin
                                // Section 3.8: SCHEDULE.queue_index selects
                                // the queue.
                                seq_desc_req <= 1'b1;
                                seq_desc_id <= op_schedule_id;
                                state <= S_SCHED_WAIT;
                            end
                        end else if (expected_type == ot_a3_pkg::A3_DESC_COMMUNICATION) begin
                            // LINK: the queue is the virtual channel; the
                            // dependence range is the local object's range,
                            // written conservatively for every LINK shape.
                            issue_queue_q <= ot_a3_pkg::a3_queue_base(ins_major) +
                                             ({3'd0, comm_vc[1:0]} &
                                              ot_a3_pkg::a3_queue_index_mask(ins_major));
                            aux_valid[0] <= 1'b1;
                            aux_object[0] <= comm_local_obj[15:0];
                            aux_lo[0] <= comm_range_fits ? comm_local_off[39:0] : 40'd0;
                            aux_hi[0] <= comm_range_fits ? comm_local_end[39:0] : {40{1'b1}};
                            aux_write[0] <= 1'b1;
                            hz_work <= 14'd1 << 12;
                            hz_acc <= 1'b0;
                            hz_retire_seen <= 1'b0;
                            state <= S_HAZARD;
                        end else if ((ins_major == ot_a3_pkg::A3_MAJOR_OBSERVATION) &&
                                     (ins_sub == 8'h00)) begin
                            // OBSERVATION.COUNTER_SNAPSHOT is an ENGINE drain
                            // (AM-C2).
                            drain_next <= DRAIN_ISSUE;
                            state <= S_DRAIN;
                        end else begin
                            hz_work <= 14'd0;
                            hz_acc <= 1'b0;
                            hz_retire_seen <= 1'b0;
                            state <= S_HAZARD;
                        end
                    end
                end
                S_SCHED_WAIT: begin
                    if (desc_valid) begin
                        if (!desc_header_ok || (desc_type != ot_a3_pkg::A3_DESC_SCHEDULE)) begin
                            // STRICTER: the verifier proves the OPERATOR's
                            // schedule_id names a SCHEDULE.
                            raise_trap(ot_a3_pkg::A3_TRAP_DESCRIPTOR, pc);
                        end else begin
                            issue_queue_q <= ot_a3_pkg::a3_queue_base(ins_major) +
                                             ({3'd0, sched_queue_index[1:0]} &
                                              ot_a3_pkg::a3_queue_index_mask(ins_major));
                            bank_start <= 1'b1;
                            state <= S_RESOLVE;
                        end
                    end
                end
                S_RESOLVE: begin
                    if (bank_done) begin
                        if (bank_fault) begin
                            // The reference resolver raises rather than
                            // resolving; so does this.
                            raise_trap(bank_trap_class, pc);
                        end else begin
                            hz_work <= rng_valid;
                            hz_acc <= 1'b0;
                            hz_retire_seen <= 1'b0;
                            state <= S_HAZARD;
                        end
                    end
                end

                // -- dependence check (section 3.6): two ranges per cycle --
                S_HAZARD: begin
                    if (hz_work != 14'd0) begin
                        dep_check0_valid <= 1'b1;
                        dep_check0_object <= rng_object[hz_first];
                        dep_check0_lo <= rng_lo[hz_first];
                        dep_check0_hi <= rng_hi[hz_first];
                        dep_check0_write <= rng_write[hz_first];
                        if (hz_rest != 14'd0) begin
                            dep_check1_valid <= 1'b1;
                            dep_check1_object <= rng_object[hz_second];
                            dep_check1_lo <= rng_lo[hz_second];
                            dep_check1_hi <= rng_hi[hz_second];
                            dep_check1_write <= rng_write[hz_second];
                            hz_work <= hz_rest & ~(14'd1 << hz_second);
                        end else begin
                            hz_work <= 14'd0;
                        end
                        hz_acc <= hz_acc | dep_check0_conflict | dep_check1_conflict;
                    end else if (hz_conflict_now) begin
                        dbg_dep_stalls <= dbg_dep_stalls + 32'd1;
                        state <= S_HAZARD_STALL;
                    end else if (irs_alloc_ready) begin
                        // Reserve the entry: no other allocator exists, so
                        // the lowest free entry stays free until the issue.
                        issue_slot_q <= irs_free_slot;
                        pub_work <= rng_valid;
                        state <= S_VIEW_PUB;
                    end
                end
                S_HAZARD_STALL: begin
                    // A retirement released an entry -- now, or while the
                    // scan that found the conflict was still running -- so
                    // scan again.  Nothing outstanding means nothing to
                    // conflict with, and the scan proves it.
                    if (irs_retire_valid || hz_retire_seen || !irs_any_outstanding) begin
                        hz_work <= rng_valid;
                        hz_acc <= 1'b0;
                        hz_retire_seen <= 1'b0;
                        state <= S_HAZARD;
                    end
                end

                // -- publish the resolved views and enter the ranges --------
                S_VIEW_PUB: begin
                    if (pub_work != 14'd0) begin
                        dep_insert_valid <= 1'b1;
                        dep_insert_object <= rng_object[pub_first];
                        dep_insert_lo <= rng_lo[pub_first];
                        dep_insert_hi <= rng_hi[pub_first];
                        dep_insert_write <= rng_write[pub_first];
                        if ((pub_first < 4'd12) && !pub_first[0])
                            publish_view(pub_first[3:1]);
                        pub_work <= pub_work & ~(14'd1 << pub_first);
                    end else begin
                        issue_valid_q <= 1'b1;
                        issue_family <= ins_major;
                        issue_sub <= ins_sub;
                        issue_descriptor_id <= ins_descriptor_id;
                        issue_index <= pc;
                        issue_serial <= serial;
                        issue_slot <= issue_slot_q;
                        issue_queue <= issue_queue_q;
                        state <= S_ISSUE;
                    end
                end

                S_STATE_SYM: begin
                    st_op_valid <= 1'b1;
                    state <= S_STATE_DONE;
                end
                S_STATE_DONE: begin
                    if (st_op_done) begin
                        if (!st_op_ok) begin
                            raise_trap(st_op_trap_class, pc);
                        end else begin
                            // Whole committed and prepared objects.
                            aux_valid <= 2'b11;
                            aux_object[0] <= state_committed_obj[15:0];
                            aux_lo[0] <= 40'd0;
                            aux_hi[0] <= {40{1'b1}};
                            aux_write[0] <= 1'b1;
                            aux_object[1] <= state_prepared_obj[15:0];
                            aux_lo[1] <= 40'd0;
                            aux_hi[1] <= {40{1'b1}};
                            aux_write[1] <= 1'b1;
                            hz_work <= 14'd3 << 12;
                            hz_acc <= 1'b0;
                            hz_retire_seen <= 1'b0;
                            state <= S_HAZARD;
                        end
                    end
                end

                // -- issue handshake: queue acceptance ---------------------
                S_ISSUE: begin
                    if (issue_valid && issue_ready) begin
                        issue_valid_q <= 1'b0;
                        // The counter snapshot of this issue (payload lane 6).
                        irs_we <= 1'b1;
                        irs_wslot <= issue_slot_q;
                        irs_wlane <= 3'd6;
                        irs_wdata <= snapshot_word;
                        serial <= serial + 32'd1;
                        pc <= pc + 32'd1;
                        launch_fetch(imem_index + 32'd1);
                    end
                end

                // -- drains (AM-C2) ------------------------------------------
                S_DRAIN: begin
                    if (!irs_any_outstanding) begin
                        case (drain_next)
                            DRAIN_RETIRE: begin
                                retire_control;
                                pc <= pc + 32'd1;
                                launch_fetch(imem_index + 32'd1);
                            end
                            DRAIN_COMPLETE: begin
                                retire_control;
                                complete <= 1'b1;
                                if (STATE_COMPAT != 0) begin
                                    st_commit_all <= 1'b1;
                                    state <= S_COMMIT;
                                end else begin
                                    state <= S_DONE;
                                end
                            end
                            default: begin
                                hz_work <= 14'd0;
                                hz_acc <= 1'b0;
                                hz_retire_seen <= 1'b0;
                                state <= S_HAZARD;
                            end
                        endcase
                    end
                end

                // -- a precise trap, held behind outstanding work ------------
                S_TRAP_WAIT: begin
                    if (irs_fault_valid) begin
                        // The outstanding operation's fault has the lower
                        // serial and wins.
                        abort_for_fault;
                    end else if (!irs_any_outstanding) begin
                        apply_trap(pending_trap_class, pending_trap_index);
                    end
                end

                // -- an asynchronous engine fault ----------------------------
                S_FAULT_DRAIN: begin
                    if (!irs_any_outstanding) begin
                        irs_re <= 1'b1;
                        irs_rslot <= irs_fault_slot;
                        irs_rlane <= 3'd6;
                        state <= S_FAULT_READ;
                    end
                end
                S_FAULT_READ: begin
                    state <= S_FAULT_WAIT;
                end
                S_FAULT_WAIT: begin
                    // irs_rdata presents the snapshot this cycle.
                    count_fetched <= irs_rdata[31:0];
                    count_issued <= irs_rdata[63:32];
                    count_predicated_off <= irs_rdata[95:64];
                    count_views_resolved <= irs_rdata[127:96];
                    frozen_loop_iterations <= irs_rdata[159:128];
                    count_branches <= irs_rdata[191:160];
                    frozen_wait_events <= irs_rdata[223:192];
                    frozen_signals <= irs_rdata[255:224];
                    count_retired <= irs_rdata[287:256];
                    frozen_state_prepares <= irs_rdata[319:288];
                    frozen_state_commits <= irs_rdata[351:320];
                    frozen_state_discards <= irs_rdata[383:352];
                    frozen_state_reads <= irs_rdata[415:384];
                    frozen_state_advances <= irs_rdata[447:416];
                    frozen <= 1'b1;
                    state <= S_FAULT_APPLY;
                end
                S_FAULT_APPLY: begin
                    apply_trap(
                        (irs_fault_trap_class == ot_a3_pkg::A3_TRAP_NONE)
                            ? ot_a3_pkg::A3_TRAP_ENGINE : irs_fault_trap_class,
                        irs_fault_pc
                    );
                end

                // -- termination -------------------------------------------
                S_COMMIT: begin
                    if (st_apply_done)
                        state <= S_DONE;
                end
                S_DISCARD: begin
                    if (st_apply_done)
                        state <= S_DONE;
                end
                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
            end
        end
    end
endmodule
