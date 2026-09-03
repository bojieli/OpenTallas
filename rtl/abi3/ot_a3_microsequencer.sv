`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 deterministic microsequencer (feature bit 2).
//
// One transaction, in order, from an entrypoint's first instruction to
// CONTROL.COMPLETE or to the first trap.  The stages are the ones the golden
// model (runtime/sim/device.Device.run_transaction) executes per instruction,
// in exactly its order, because the two must agree instruction for instruction:
//
//   fetch      pc bound check, retired-work bound check, 32-byte record read
//   decode     ot_a3_instruction_decoder: CRC32C and structural legality
//   predicate  PREDICATE descriptor, optional inversion, skip without retire
//   wait       EVENT_WAIT_SET descriptor, every producer signalled
//   execute    control transfer, transactional state, or engine issue
//   retire     signal publication, counters, next pc
//
// Ordering that is load-bearing for correlation:
//   * a predicated-off instruction is fetched, never waits, never signals and
//     never retires;
//   * a control instruction never publishes its signal event -- only an
//     engine-family instruction does;
//   * the issued counter advances before the operation can fault, the retired
//     counter only after it cannot;
//   * an engine issue is emitted only once the family's own precondition has
//     passed, so a faulting STATE or RECOVERY.ABORT produces no issue event.
//
// Engine datapaths are out of scope: the issue port is a ready/valid interface
// carrying (family, subopcode, descriptor ID) and nothing else.  This block
// therefore models the control plane exactly and the data plane not at all.
// Data-dependent BOOLEAN_OBJECT and EOS_MEMBER predicates use a separate
// request/response port.  The memory/selection integration owns the read (and,
// for a cluster, the node-consensus check); the sequencer owns only the
// authenticated predicate descriptor and the resulting control decision.
//
// The one thing an engine cannot be handed as a raw descriptor ID is its
// operands' *extents*, because amendments A4 and A13 make those a function of
// the loop and symbol bindings live at the dispatch.  Before an OPERATOR-family
// instruction issues, each operand tensor view it names is therefore resolved
// by ot_a3_view_resolver against the open loops and the request's symbols, and
// the resolved extent and element offset are published on the view port in
// operand order (inputs 0..3 then outputs 0..1, skipping NO_ID).  Without A13 a
// final block iteration would present the block size where the request has
// fewer rows -- the failure the amendment exists to remove.
//
// Where this block is deliberately stricter than the golden model -- it may
// assume a verified program, but it does not have to trust one -- the check is
// marked STRICTER below.
// ---------------------------------------------------------------------------
module ot_a3_microsequencer
    import ot_a3_pkg::*;
#(
    // The four production-comparison deployments use ordinary live buffers
    // and contain no STATE descriptors or instructions.  Keeping the legacy
    // controller behind a parameter preserves ABI 3.0 compatibility tests
    // without forcing its slot file or apply path into the shipped profile.
    parameter integer STATE_COMPAT = 1
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
    // 192 bytes: the 64-byte header plus both 64-byte payload blocks, because
    // a TENSOR_VIEW's dynamic terms (payload offset 72) lie in the second.
    output reg           desc_req,
    output reg  [31:0]   desc_id,
    input  wire          desc_valid,
    input  wire          desc_fault,
    input  wire [1535:0] desc_data,

    // -- runtime symbol file (combinational read) ----------------------
    output wire [3:0]    sym_index,
    input  wire [31:0]   sym_value,
    input  wire          sym_bound,

    // -- data-dependent predicate result -------------------------------
    output reg           predicate_read_req,
    output reg  [31:0]   predicate_read_object_id,
    output reg  [31:0]   predicate_read_element_index,
    input  wire          predicate_read_valid,
    input  wire          predicate_read_value,
    input  wire [15:0]   predicate_read_trap_class,

    // -- engine issue --------------------------------------------------
    output reg           issue_valid,
    input  wire          issue_ready,
    output reg  [7:0]    issue_family,
    output reg  [7:0]    issue_sub,
    output reg  [31:0]   issue_descriptor_id,
    output reg  [31:0]   issue_index,

    // -- resolved tensor views (amendments A4, A13 and A18) ------------
    // One single-cycle pulse per operand view of the instruction about to
    // issue, in operand order.  Observation only: it carries no back-pressure
    // because it states what the issue already means.
    output reg           view_valid,
    output reg  [31:0]   view_descriptor_id,
    output reg  [2:0]    view_slot,
    output reg  [31:0]   view_extent,
    output reg  [7:0]    view_extent_axis,
    output reg  [63:0]   view_element_offset,
    output reg  [7:0]    view_rank,
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
    output wire [1:0]    dbg_loop_action
);
    // -- stage encoding -------------------------------------------------
    localparam [4:0] S_IDLE        = 5'd0;
    localparam [4:0] S_CHECK_PC    = 5'd1;
    localparam [4:0] S_FETCH_WAIT  = 5'd3;
    localparam [4:0] S_DECODE_PUSH = 5'd4;
    localparam [4:0] S_DECODE_WAIT = 5'd5;
    localparam [4:0] S_PRED_REQ    = 5'd6;
    localparam [4:0] S_PRED_WAIT   = 5'd7;
    localparam [4:0] S_PRED_SYM    = 5'd8;
    localparam [4:0] S_PRED_EVAL   = 5'd9;
    localparam [4:0] S_WAIT_REQ    = 5'd10;
    localparam [4:0] S_WAIT_WAIT   = 5'd11;
    localparam [4:0] S_WAIT_EVAL   = 5'd12;
    localparam [4:0] S_DISPATCH    = 5'd13;
    localparam [4:0] S_LOOP_WAIT   = 5'd14;
    localparam [4:0] S_LOOP_SYM    = 5'd15;
    localparam [4:0] S_LOOP_OP     = 5'd16;
    localparam [4:0] S_LOOP_DONE   = 5'd17;
    localparam [4:0] S_ENG_WAIT    = 5'd18;
    localparam [4:0] S_STATE_SYM   = 5'd19;
    localparam [4:0] S_STATE_DONE  = 5'd20;
    localparam [4:0] S_ISSUE       = 5'd21;
    localparam [4:0] S_RETIRE      = 5'd22;
    localparam [4:0] S_COMMIT      = 5'd23;
    localparam [4:0] S_DISCARD     = 5'd24;
    localparam [4:0] S_DONE        = 5'd25;
    localparam [4:0] S_VIEW_SCAN   = 5'd26;
    localparam [4:0] S_VIEW_WAIT   = 5'd27;
    localparam [4:0] S_VIEW_RES    = 5'd28;
    localparam [4:0] S_VIEW_EMIT   = 5'd29;
    localparam [4:0] S_PRED_OBJECT = 5'd30;

    reg [4:0]  state;
    reg [31:0] pc;
    reg [31:0] instruction_count;
    reg [31:0] program_base;
    reg [63:0] work_bound;
    reg [31:0] state_count;
    reg [255:0] record;
    reg        xact_clear;

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

    ot_a3_instruction_decoder decoder (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(dec_in_valid),
        .in_ready(dec_in_ready),
        .in_record(record),
        .in_index(pc),
        .in_instruction_count(instruction_count),
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

    // -- loop stack ------------------------------------------------------
    reg         loop_setup_valid;
    reg         loop_next_valid;
    wire        loop_done;
    wire        loop_trap_valid;
    wire [15:0] loop_trap_class;
    wire [31:0] loop_next_pc;
    wire [1:0]  loop_action;
    reg  [31:0] loop_query_id_q;
    wire [31:0] loop_query_id;
    wire        loop_query_active;
    wire [31:0] loop_query_value;
    wire [31:0] loop_query_trip;
    wire        loop_query_symbol_bounded;
    wire [31:0] loop_query_divisor;
    wire [31:0] loop_query_bound_value;
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

    ot_a3_loop_stack loops (
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
        .query_id(loop_query_id),
        .query_active(loop_query_active),
        .query_value(loop_query_value),
        .query_trip(loop_query_trip),
        .query_symbol_bounded(loop_query_symbol_bounded),
        .query_divisor(loop_query_divisor),
        .query_bound_value(loop_query_bound_value),
        .iteration_count(count_loop_iterations),
        .depth(loop_depth)
    );

    // -- event scoreboard -------------------------------------------------
    reg         evt_signal_valid;
    reg         evt_wait_start;
    reg [511:0] evt_wait_payload;
    reg         evt_wait_acquire;
    wire        evt_wait_done;
    wire        evt_wait_ok;
    wire [15:0] evt_wait_trap_class;
    wire [31:0] evt_wait_fault_event;

    ot_a3_event_scoreboard events (
        .clk(clk),
        .rst_n(rst_n),
        .clear(xact_clear),
        .signal_valid(evt_signal_valid),
        .signal_event_id(ins_signal_event_id),
        .signal_release(ins_flags[A3_FLAG_SIGNAL_RELEASE]),
        .signal_error(event_signal_error),
        .wait_start(evt_wait_start),
        .wait_payload(evt_wait_payload),
        .wait_acquire(evt_wait_acquire),
        .wait_busy(),
        .wait_done(evt_wait_done),
        .wait_ok(evt_wait_ok),
        .wait_trap_class(evt_wait_trap_class),
        .wait_fault_event(evt_wait_fault_event),
        .signal_count(count_signals),
        .wait_count(count_wait_events)
    );

    // -- state controller -------------------------------------------------
    reg         st_op_valid;
    reg         st_commit_all;
    reg         st_discard_all;
    wire        st_op_done;
    wire        st_op_ok;
    wire [15:0] st_op_trap_class;
    wire        st_apply_done;

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
                .op_rows(sym_value),
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
                .count_prepares(count_state_prepares),
                .count_commits(count_state_commits),
                .count_discards(count_state_discards),
                .count_reads(count_state_reads),
                .count_generation_advances(count_state_generation_advances),
                .count_commits_applied(count_state_commits_applied),
                .count_rows_committed(count_state_rows_committed),
                .count_bytes_written(count_state_bytes_written)
            );
        end else begin : g_no_state_compat
            assign st_op_done = 1'b1;
            assign st_op_ok = 1'b0;
            assign st_op_trap_class = A3_TRAP_CAPABILITY;
            assign st_apply_done = 1'b1;
            assign state_apply_overflow = 1'b0;
            assign count_state_prepares = 32'd0;
            assign count_state_commits = 32'd0;
            assign count_state_discards = 32'd0;
            assign count_state_reads = 32'd0;
            assign count_state_generation_advances = 32'd0;
            assign count_state_commits_applied = 32'd0;
            assign count_state_rows_committed = 32'd0;
            assign count_state_bytes_written = 64'd0;
        end
    endgenerate

    // -- tensor view resolution (A4 and A13) -------------------------------
    // OPERATOR payload (runtime/abi3/descriptors.OPERATOR_PAYLOAD):
    // input_view_{0..3} at byte 24, output_view_{0..1} at byte 40.
    reg  [511:0]  op_payload;
    reg  [1023:0] view_payload;
    reg  [2:0]    view_next_slot;
    reg           view_start;

    reg [31:0] view_slot_id;
    always @* begin
        case (view_next_slot)
            3'd0:    view_slot_id = op_payload[223:192];   // input_view_0
            3'd1:    view_slot_id = op_payload[255:224];   // input_view_1
            3'd2:    view_slot_id = op_payload[287:256];   // input_view_2
            3'd3:    view_slot_id = op_payload[319:288];   // input_view_3
            3'd4:    view_slot_id = op_payload[351:320];   // output_view_0
            3'd5:    view_slot_id = op_payload[383:352];   // output_view_1
            default: view_slot_id = A3_NO_ID;
        endcase
    end

    wire view_active = (state == S_VIEW_SCAN) || (state == S_VIEW_WAIT) ||
                       (state == S_VIEW_RES)  || (state == S_VIEW_EMIT);

    wire         res_done;
    wire         res_fault;
    wire [15:0]  res_trap_class;
    wire [63:0]  res_element_offset;
    wire [31:0]  res_extent;
    wire [7:0]   res_extent_axis;
    wire [7:0]   res_rank;
    wire [31:0]  res_loop_query_id;
    wire [3:0]   res_sym_index;

    // The resolver owns the loop query and the symbol select while it walks a
    // view's terms; the sequencer's own predicate, loop and state reads own
    // them otherwise.  Only one of the two is ever in flight.
    assign loop_query_id = view_active ? res_loop_query_id : loop_query_id_q;
    assign sym_index     = view_active ? res_sym_index     : sym_index_q;

    ot_a3_view_resolver view_resolver (
        .clk(clk),
        .rst_n(rst_n),
        .clear(xact_clear),
        .start(view_start),
        .payload(view_payload),
        .busy(),
        .done(res_done),
        .fault(res_fault),
        .trap_class(res_trap_class),
        .out_element_offset(res_element_offset),
        .out_extent(res_extent),
        .out_extent_axis(res_extent_axis),
        .out_rank(res_rank),
        .out_dtype(),
        .out_term_count(),
        .loop_query_id(res_loop_query_id),
        .loop_query_active(loop_query_active),
        .loop_query_value(loop_query_value),
        .loop_query_symbol_bounded(loop_query_symbol_bounded),
        .loop_query_divisor(loop_query_divisor),
        .loop_query_bound_value(loop_query_bound_value),
        .sym_index(res_sym_index),
        .sym_value(sym_value),
        .sym_bound(sym_bound)
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
    // A TENSOR_VIEW payload is 128 bytes; a 64-byte prefix stops short of the
    // dynamic terms, so view resolution reads both payload blocks.
    wire [1023:0] desc_payload_wide = desc_data[1535:512];
    wire         desc_header_ok = !desc_fault &&
                                  (desc_magic == A3_DESCRIPTOR_MAGIC) &&
                                  (desc_type_major == A3_TYPE_MAJOR) &&
                                  (desc_payload_offset == 32'd64);

    // -- predicate payload view -------------------------------------------
    wire [7:0]  pred_kind       = pred_payload[7:0];
    wire [7:0]  pred_comparison = pred_payload[15:8];
    wire [31:0] pred_selector   = pred_payload[63:32];
    wire [63:0] pred_immediate  = pred_payload[127:64];
    wire [31:0] pred_object_id  = pred_payload[159:128];
    wire [31:0] pred_element    = pred_payload[191:160];

    wire [63:0] pred_left = {32'd0, sym_value};
    reg  pred_compare_result;
    always @* begin
        case (pred_comparison)
            A3_CMP_EQ: pred_compare_result = (pred_left == pred_immediate);
            A3_CMP_NE: pred_compare_result = (pred_left != pred_immediate);
            A3_CMP_LT: pred_compare_result = (pred_left <  pred_immediate);
            A3_CMP_LE: pred_compare_result = (pred_left <= pred_immediate);
            A3_CMP_GT: pred_compare_result = (pred_left >  pred_immediate);
            default:   pred_compare_result = (pred_left >= pred_immediate);
        endcase
    end

    wire [63:0] loop_left = {32'd0, loop_query_value};
    reg  loop_compare_result;
    always @* begin
        case (pred_comparison)
            A3_CMP_EQ: loop_compare_result = (loop_left == pred_immediate);
            A3_CMP_NE: loop_compare_result = (loop_left != pred_immediate);
            A3_CMP_LT: loop_compare_result = (loop_left <  pred_immediate);
            A3_CMP_LE: loop_compare_result = (loop_left <= pred_immediate);
            A3_CMP_GT: loop_compare_result = (loop_left >  pred_immediate);
            default:   loop_compare_result = (loop_left >= pred_immediate);
        endcase
    end

    wire predicated = ins_flags[A3_FLAG_PREDICATED];
    wire invert     = ins_flags[A3_FLAG_PREDICATE_INVERT];
    wire is_control = (ins_major == A3_MAJOR_CONTROL);
    wire [15:0] expected_type = a3_family_descriptor_type(ins_major);
    wire work_exceeded = ({32'd0, count_retired} > work_bound);

    // Wire format section 3 gives *every* instruction a signal-event ID and
    // exempts no family from publishing it; section 4 does not exempt CONTROL
    // either.  runtime/sim/device.py publishes on the CONTROL path for exactly
    // that reason ("Nothing in the wire format exempts CONTROL from publishing
    // an event; the asymmetry was accidental"), and this block did not: it
    // raised evt_signal_valid only in S_ISSUE, which no CONTROL instruction
    // reaches.  A CONTROL.NOP that names an event is a real shape -- it is how
    // a program publishes "everything before this point has retired" without
    // dispatching work -- and the DeepSeek-V4-Flash wafer program uses it
    // twice inside one layer.  Called from every CONTROL retirement.
    task publish_signal;
        begin
            evt_signal_valid <= (ins_signal_event_id != A3_NO_ID);
        end
    endtask

    task raise_trap;
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
            busy <= 1'b0;
            done <= 1'b0;
            complete <= 1'b0;
            trapped <= 1'b0;
            trap_class <= A3_TRAP_NONE;
            first_fault_instruction <= A3_NO_ID;
            imem_req <= 1'b0;
            imem_index <= 32'd0;
            desc_req <= 1'b0;
            desc_id <= A3_NO_ID;
            sym_index_q <= 4'd0;
            predicate_read_req <= 1'b0;
            predicate_read_object_id <= A3_NO_ID;
            predicate_read_element_index <= 32'd0;
            issue_valid <= 1'b0;
            issue_family <= 8'd0;
            issue_sub <= 8'd0;
            issue_descriptor_id <= A3_NO_ID;
            issue_index <= A3_NO_ID;
            view_valid <= 1'b0;
            view_descriptor_id <= A3_NO_ID;
            view_slot <= 3'd0;
            view_extent <= 32'd0;
            view_extent_axis <= 8'd0;
            view_element_offset <= 64'd0;
            view_rank <= 8'd0;
            count_views_resolved <= 32'd0;
            op_payload <= 512'd0;
            view_payload <= 1024'd0;
            view_next_slot <= 3'd0;
            view_start <= 1'b0;
            dec_in_valid <= 1'b0;
            loop_setup_valid <= 1'b0;
            loop_next_valid <= 1'b0;
            loop_query_id_q <= A3_NO_ID;
            loop_payload <= 512'd0;
            evt_signal_valid <= 1'b0;
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
            ins_predicate_id <= A3_NO_ID;
            ins_descriptor_id <= A3_NO_ID;
            ins_wait_set_id <= A3_NO_ID;
            ins_signal_event_id <= A3_NO_ID;
            ins_control_id <= A3_NO_ID;
            count_fetched <= 32'd0;
            count_retired <= 32'd0;
            count_predicated_off <= 32'd0;
            count_issued <= 32'd0;
            count_branches <= 32'd0;
        end else begin
            done <= 1'b0;
            xact_clear <= 1'b0;
            imem_req <= 1'b0;
            desc_req <= 1'b0;
            view_valid <= 1'b0;
            view_start <= 1'b0;
            dec_in_valid <= 1'b0;
            loop_setup_valid <= 1'b0;
            loop_next_valid <= 1'b0;
            evt_signal_valid <= 1'b0;
            evt_wait_start <= 1'b0;
            st_op_valid <= 1'b0;
            st_commit_all <= 1'b0;
            st_discard_all <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        complete <= 1'b0;
                        trapped <= 1'b0;
                        trap_class <= A3_TRAP_NONE;
                        first_fault_instruction <= A3_NO_ID;
                        pc <= cfg_entry_pc;
                        program_base <= cfg_program_base;
                        instruction_count <= cfg_instruction_count;
                        work_bound <= cfg_max_retired_work;
                        state_count <= cfg_state_count;
                        count_fetched <= 32'd0;
                        count_retired <= 32'd0;
                        count_predicated_off <= 32'd0;
                        count_issued <= 32'd0;
                        count_branches <= 32'd0;
                        count_views_resolved <= 32'd0;
                        predicate_read_req <= 1'b0;
                        predicate_read_object_id <= A3_NO_ID;
                        predicate_read_element_index <= 32'd0;
                        xact_clear <= 1'b1;
                        if ((STATE_COMPAT == 0) &&
                            (cfg_state_count != 32'd0)) begin
                            trapped <= 1'b1;
                            trap_class <= A3_TRAP_CAPABILITY;
                            first_fault_instruction <= A3_NO_ID;
                            state <= S_DONE;
                        end else begin
                            state <= S_CHECK_PC;
                        end
                    end
                end

                // -- fetch ------------------------------------------------
                S_CHECK_PC: begin
                    if (pc >= instruction_count) begin
                        // Running off the authenticated body, or a control
                        // transfer that leaves it, is an illegal control flow.
                        raise_trap(A3_TRAP_ILLEGAL, pc);
                    end else begin
                        count_fetched <= count_fetched + 32'd1;
                        if (work_exceeded) begin
                            raise_trap(A3_TRAP_WATCHDOG, pc);
                        end else begin
                            imem_req <= 1'b1;
                            imem_index <= program_base + pc;
                            state <= S_FETCH_WAIT;
                        end
                    end
                end
                S_FETCH_WAIT: begin
                    if (imem_valid) begin
                        record <= imem_data;
                        state <= S_DECODE_PUSH;
                    end
                end
                S_DECODE_PUSH: begin
                    if (dec_in_ready) begin
                        dec_in_valid <= 1'b1;
                        state <= S_DECODE_WAIT;
                    end
                end
                S_DECODE_WAIT: begin
                    if (dec_out_valid) begin
                        ins_major <= dec_major;
                        ins_sub <= dec_sub;
                        ins_flags <= dec_flags;
                        ins_predicate_id <= dec_predicate_id;
                        ins_descriptor_id <= dec_descriptor_id;
                        ins_wait_set_id <= dec_wait_set_id;
                        ins_signal_event_id <= dec_signal_event_id;
                        ins_control_id <= dec_control_id;
                        if (!dec_out_legal)
                            raise_trap(dec_out_trap_class, dec_index);
                        else
                            state <= S_PRED_REQ;
                    end
                end

                // -- predicate --------------------------------------------
                S_PRED_REQ: begin
                    if (!predicated) begin
                        state <= S_WAIT_REQ;
                    end else begin
                        desc_req <= 1'b1;
                        desc_id <= ins_predicate_id;
                        state <= S_PRED_WAIT;
                    end
                end
                S_PRED_WAIT: begin
                    if (desc_valid) begin
                        if (!desc_header_ok || (desc_type != A3_DESC_PREDICATE)) begin
                            raise_trap(A3_TRAP_DESCRIPTOR, pc);
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
                    if (pred_kind == A3_PRED_PHASE_IS)
                        sym_index_q <= A3_SYMBOL_PHASE;
                    else
                        sym_index_q <= pred_selector[3:0];
                    loop_query_id_q <= pred_selector;
                    state <= S_PRED_EVAL;
                end
                S_PRED_EVAL: begin
                    case (pred_kind)
                        A3_PRED_ALWAYS: begin
                            if (invert) begin
                                count_predicated_off <= count_predicated_off + 32'd1;
                                pc <= pc + 32'd1;
                                state <= S_CHECK_PC;
                            end else begin
                                state <= S_WAIT_REQ;
                            end
                        end
                        A3_PRED_PHASE_IS, A3_PRED_COMPARE_SYMBOL: begin
                            if (!sym_bound ||
                                ((pred_kind == A3_PRED_COMPARE_SYMBOL) &&
                                 (pred_selector >= A3_SYMBOL_COUNT))) begin
                                raise_trap(A3_TRAP_DESCRIPTOR, pc);
                            end else if ((pred_kind == A3_PRED_PHASE_IS)
                                         ? ((pred_left == pred_immediate) ^ invert)
                                         : (pred_compare_result ^ invert)) begin
                                state <= S_WAIT_REQ;
                            end else begin
                                count_predicated_off <= count_predicated_off + 32'd1;
                                pc <= pc + 32'd1;
                                state <= S_CHECK_PC;
                            end
                        end
                        A3_PRED_COMPARE_LOOP: begin
                            if (!loop_query_active) begin
                                raise_trap(A3_TRAP_ILLEGAL, pc);
                            end else if (loop_compare_result ^ invert) begin
                                state <= S_WAIT_REQ;
                            end else begin
                                count_predicated_off <= count_predicated_off + 32'd1;
                                pc <= pc + 32'd1;
                                state <= S_CHECK_PC;
                            end
                        end
                        A3_PRED_LOOP_FIRST, A3_PRED_LOOP_LAST: begin
                            if ((loop_query_active &&
                                 ((pred_kind == A3_PRED_LOOP_FIRST)
                                  ? (loop_query_value == 32'd0)
                                  : (loop_query_value == (loop_query_trip - 32'd1))))
                                ^ invert) begin
                                state <= S_WAIT_REQ;
                            end else begin
                                count_predicated_off <= count_predicated_off + 32'd1;
                                pc <= pc + 32'd1;
                                state <= S_CHECK_PC;
                            end
                        end
                        A3_PRED_BOOLEAN_OBJECT, A3_PRED_EOS_MEMBER: begin
                            predicate_read_object_id <= pred_object_id;
                            predicate_read_element_index <= pred_element;
                            predicate_read_req <= 1'b1;
                            state <= S_PRED_OBJECT;
                        end
                        default: begin
                            // ENGINE_STATUS and ROUTE_VALID require an engine
                            // status interface this controller does not have.
                            // Fail closed on the capability, never guess.
                            raise_trap(A3_TRAP_CAPABILITY, pc);
                        end
                    endcase
                end
                S_PRED_OBJECT: begin
                    if (predicate_read_valid) begin
                        predicate_read_req <= 1'b0;
                        if (predicate_read_trap_class != A3_TRAP_NONE) begin
                            raise_trap(predicate_read_trap_class, pc);
                        end else if (predicate_read_value ^ invert) begin
                            state <= S_WAIT_REQ;
                        end else begin
                            count_predicated_off <= count_predicated_off + 32'd1;
                            pc <= pc + 32'd1;
                            state <= S_CHECK_PC;
                        end
                    end
                end

                // -- wait -------------------------------------------------
                S_WAIT_REQ: begin
                    if (ins_wait_set_id == A3_NO_ID) begin
                        state <= S_DISPATCH;
                    end else begin
                        desc_req <= 1'b1;
                        desc_id <= ins_wait_set_id;
                        state <= S_WAIT_WAIT;
                    end
                end
                S_WAIT_WAIT: begin
                    if (desc_valid) begin
                        if (!desc_header_ok ||
                            (desc_type != A3_DESC_EVENT_WAIT_SET)) begin
                            raise_trap(A3_TRAP_DESCRIPTOR, pc);
                        end else begin
                            evt_wait_start <= 1'b1;
                            evt_wait_payload <= desc_payload;
                            evt_wait_acquire <= ins_flags[A3_FLAG_WAIT_ACQUIRE];
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
                            A3_CONTROL_NOP,
                            A3_CONTROL_WAIT,
                            A3_CONTROL_FENCE,
                            A3_CONTROL_ASSERT: begin
                                count_retired <= count_retired + 32'd1;
                                publish_signal;
                                pc <= pc + 32'd1;
                                state <= S_CHECK_PC;
                            end
                            A3_CONTROL_BRANCH: begin
                                count_retired <= count_retired + 32'd1;
                                count_branches <= count_branches + 32'd1;
                                publish_signal;
                                pc <= ins_control_id;
                                state <= S_CHECK_PC;
                            end
                            A3_CONTROL_COMPLETE: begin
                                count_retired <= count_retired + 32'd1;
                                publish_signal;
                                complete <= 1'b1;
                                if (STATE_COMPAT != 0) begin
                                    st_commit_all <= 1'b1;
                                    state <= S_COMMIT;
                                end else begin
                                    // The program's final dependency fence
                                    // already orders direct live-buffer writes.
                                    state <= S_DONE;
                                end
                            end
                            A3_CONTROL_TRAP: begin
                                raise_trap(A3_TRAP_ILLEGAL, pc);
                            end
                            A3_CONTROL_LOOP_SETUP: begin
                                desc_req <= 1'b1;
                                desc_id <= ins_control_id;
                                state <= S_LOOP_WAIT;
                            end
                            default: begin   // A3_CONTROL_LOOP_NEXT
                                loop_next_valid <= 1'b1;
                                state <= S_LOOP_DONE;
                            end
                        endcase
                    end else begin
                        count_issued <= count_issued + 32'd1;
                        if ((ins_major == A3_MAJOR_RECOVERY) &&
                            (ins_sub == A3_RECOVERY_ABORT)) begin
                            raise_trap(A3_TRAP_INTERNAL, pc);
                        end else if (expected_type == A3_DESC_NONE) begin
                            state <= S_ISSUE;
                        end else begin
                            desc_req <= 1'b1;
                            desc_id <= ins_descriptor_id;
                            state <= S_ENG_WAIT;
                        end
                    end
                end

                // -- loops -------------------------------------------------
                S_LOOP_WAIT: begin
                    if (desc_valid) begin
                        if (!desc_header_ok ||
                            (desc_type != A3_DESC_LOOP_CONTROL)) begin
                            raise_trap(A3_TRAP_DESCRIPTOR, pc);
                        end else begin
                            loop_payload <= desc_payload;
                            state <= S_LOOP_SYM;
                        end
                    end
                end
                S_LOOP_SYM: begin
                    if (loop_symbol_id >= A3_SYMBOL_COUNT) begin
                        sym_index_q <= 4'd0;
                        if (loop_bound_kind != A3_SELECTOR_CONSTANT) begin
                            // Symbol-bounded loop naming a symbol outside the
                            // frozen registry.
                            raise_trap(A3_TRAP_DESCRIPTOR, pc);
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
                            count_retired <= count_retired + 32'd1;
                            publish_signal;
                            pc <= loop_next_pc;
                            state <= S_CHECK_PC;
                        end
                    end
                end

                // -- engine families ---------------------------------------
                S_ENG_WAIT: begin
                    if (desc_valid) begin
                        if (!desc_header_ok || (desc_type != expected_type)) begin
                            // STRICTER: the golden model type-checks only the
                            // STATE family here; every family is checked.
                            raise_trap(A3_TRAP_DESCRIPTOR, pc);
                        end else if (ins_major == A3_MAJOR_STATE) begin
                            if (STATE_COMPAT == 0) begin
                                raise_trap(A3_TRAP_CAPABILITY, pc);
                            end else begin
                                state_payload <= desc_payload;
                                sym_index_q <= A3_SYMBOL_SPAN_TOKENS;
                                state <= S_STATE_SYM;
                            end
                        end else if (expected_type == A3_DESC_OPERATOR) begin
                            // A4/A13: an engine is handed extents, not just a
                            // descriptor ID, so every operand view this
                            // operator names is resolved before the issue.
                            op_payload <= desc_payload;
                            view_next_slot <= 3'd0;
                            state <= S_VIEW_SCAN;
                        end else begin
                            state <= S_ISSUE;
                        end
                    end
                end

                // -- operand tensor views (A4 and A13) ---------------------
                S_VIEW_SCAN: begin
                    if (view_next_slot >= 3'd6) begin
                        state <= S_ISSUE;
                    end else if (view_slot_id == A3_NO_ID) begin
                        view_next_slot <= view_next_slot + 3'd1;
                    end else begin
                        desc_req <= 1'b1;
                        desc_id <= view_slot_id;
                        state <= S_VIEW_WAIT;
                    end
                end
                S_VIEW_WAIT: begin
                    if (desc_valid) begin
                        if (!desc_header_ok ||
                            (desc_type != A3_DESC_TENSOR_VIEW)) begin
                            raise_trap(A3_TRAP_DESCRIPTOR, pc);
                        end else begin
                            view_payload <= desc_payload_wide;
                            view_descriptor_id <= desc_id;
                            view_start <= 1'b1;
                            state <= S_VIEW_RES;
                        end
                    end
                end
                S_VIEW_RES: begin
                    if (res_done) begin
                        if (res_fault) begin
                            // The reference resolver raises rather than
                            // resolving; so does this.
                            raise_trap(res_trap_class, pc);
                        end else begin
                            view_valid <= 1'b1;
                            view_slot <= view_next_slot;
                            view_extent <= res_extent;
                            view_extent_axis <= res_extent_axis;
                            view_element_offset <= res_element_offset;
                            view_rank <= res_rank;
                            count_views_resolved <=
                                count_views_resolved + 32'd1;
                            state <= S_VIEW_EMIT;
                        end
                    end
                end
                S_VIEW_EMIT: begin
                    view_next_slot <= view_next_slot + 3'd1;
                    state <= S_VIEW_SCAN;
                end

                S_STATE_SYM: begin
                    st_op_valid <= 1'b1;
                    state <= S_STATE_DONE;
                end
                S_STATE_DONE: begin
                    if (st_op_done) begin
                        if (!st_op_ok)
                            raise_trap(st_op_trap_class, pc);
                        else
                            state <= S_ISSUE;
                    end
                end
                S_ISSUE: begin
                    issue_valid <= 1'b1;
                    issue_family <= ins_major;
                    issue_sub <= ins_sub;
                    issue_descriptor_id <= ins_descriptor_id;
                    issue_index <= pc;
                    if (issue_valid && issue_ready) begin
                        issue_valid <= 1'b0;
                        evt_signal_valid <= (ins_signal_event_id != A3_NO_ID);
                        state <= S_RETIRE;
                    end
                end
                S_RETIRE: begin
                    count_retired <= count_retired + 32'd1;
                    pc <= pc + 32'd1;
                    state <= S_CHECK_PC;
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
endmodule
