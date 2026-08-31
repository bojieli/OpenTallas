`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 transactional state controller (STATE family, wire format section 4;
// STATE descriptor payload, runtime/abi3/descriptors.py).
//
// The atomicity rule this block exists to enforce is the one in
// runtime/sim/device.Device.run_transaction: a COMMIT does not move a state
// resource.  It stages the commit, and the whole staged set is applied only
// when the transaction reaches CONTROL.COMPLETE.  Any trap, at any point,
// drops the entire staged set and clears the open prepares, so no fault can
// expose a partially advanced cursor or generation.
//
//   PREPARE             already open              -> trap class 9
//   COMMIT              no open prepare           -> trap class 9
//                       span not positive         -> trap class 9  (staged only)
//                       cursor + rows > capacity  -> trap class 4  (REQUEST_SPAN)
//   DISCARD             always clears the prepare
//   READ / GENERATION_ADVANCE  accounted, no state change
//
// Amendment A21 (wire format section 12.11).  The commit's row count is the
// resource's to declare, in ``commit_policy`` at STATE payload byte 1, and not
// the request's to assume: SPAN_TOKENS is a token count and is a row count
// only where the resource's row axis is the token axis.  Under REQUEST_SPAN --
// the value every pre-A21 deployment carried, so this block's behaviour on
// them is unchanged -- the sequencer's bound SPAN_TOKENS is the count and a
// zero count is still trap class 9.  Under UNSTAGED no descriptor of the
// deployment names the resource's prepared image as a destination, nothing can
// stage a row into it, and the commit stages zero rows: it publishes nothing,
// leaves the cursor where it was, satisfies the capacity bound by
// construction, and still closes the prepare and advances the generation,
// because ADR-003 8.6 makes the whole declared state set one transition.
//
// Amendment A25 (wire format section 12.16).  SATURATING is the third value:
// the resource's row axis is a ring of capacity_rows slots that the token axis
// maps onto by ``position mod capacity_rows``, so a span longer than the ring
// does not overflow it -- it wraps onto it.  A saturating commit publishes
// min(span, capacity) rows, its capacity comparison is skipped because the
// clamp already satisfies it, and its cursor advances to
// (cursor + span) mod capacity rather than to cursor + rows.  The span is
// carried into the staged record beside the row count because the cursor must
// advance by the positions the request presented and the counters by the rows
// the ring published, and above the window those are different numbers.  Below
// the window they are the same number and this block behaves exactly as it did
// before the amendment.
//
// Capacity is checked against the committed cursor, exactly as the golden
// model does.  That check is per commit, not per staged set: two staged
// commits can each pass and still exceed capacity when both apply.  This block
// reproduces the reference behaviour rather than silently diverging from it,
// and reports the condition on apply_overflow so the divergence is visible.
//
// Row counts, capacities and cursors are carried as the low 32 bits of the
// descriptor's 64-bit fields; a state resource larger than 4G rows is outside
// the capability this RTL is built for.
// ---------------------------------------------------------------------------
module ot_a3_state_controller
    import ot_a3_pkg::*;
#(
    parameter integer SLOTS = A3_STATE_SLOTS
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         clear,

    input  wire         op_valid,
    input  wire [7:0]   op_sub,
    input  wire [31:0]  op_descriptor_id,
    input  wire [511:0] op_payload,
    input  wire [31:0]  op_rows,
    input  wire         op_rows_bound,
    output reg          op_done,
    output reg          op_ok,
    output reg  [15:0]  op_trap_class,

    input  wire         commit_all,      // CONTROL.COMPLETE reached
    input  wire         discard_all,     // transaction trapped
    // The number of STATE descriptors this session declares.  An abort
    // discards the whole prepared state set, not only the slots this
    // transaction happened to touch (ADR-003 8.6; runtime/sim/device.py
    // counts ``len(session.states)`` on the failing path), so the discard
    // accounting needs the session's declared state count, which is a
    // deployment property this block cannot observe from its own traffic.
    input  wire [31:0]  session_state_count,
    output reg          apply_busy,
    output reg          apply_done,
    output reg          apply_overflow,

    output reg  [31:0]  count_prepares,
    output reg  [31:0]  count_commits,       // staged
    output reg  [31:0]  count_discards,
    output reg  [31:0]  count_reads,
    output reg  [31:0]  count_generation_advances,
    output reg  [31:0]  count_commits_applied,
    output reg  [31:0]  count_rows_committed,
    output reg  [63:0]  count_bytes_written
);
    localparam integer SLOT_W = $clog2(SLOTS);

    reg [31:0] slot_descriptor [0:SLOTS-1];
    reg [31:0] slot_cursor     [0:SLOTS-1];
    reg [31:0] slot_capacity   [0:SLOTS-1];
    reg [31:0] slot_row_bytes  [0:SLOTS-1];
    reg [31:0] slot_generation [0:SLOTS-1];
    reg [7:0]  slot_policy     [0:SLOTS-1];
    reg [SLOTS-1:0] slot_used;
    reg [SLOTS-1:0] slot_open;

    reg [SLOT_W-1:0] pending_slot [0:SLOTS-1];
    reg [31:0] pending_rows [0:SLOTS-1];
    reg [31:0] pending_span [0:SLOTS-1];
    reg [SLOT_W:0] pending_count;
    reg [SLOT_W-1:0] apply_index;

    // STATE payload fields (byte offsets 1, 16, 24, 32 inside the payload).
    wire [7:0]  payload_policy      = op_payload[8   +: 8];
    wire [31:0] payload_row_bytes   = op_payload[128 +: 32];
    wire [31:0] payload_capacity    = op_payload[192 +: 32];
    wire [31:0] payload_initial_cur = op_payload[256 +: 32];

    reg [SLOT_W:0]   s;
    reg [SLOT_W-1:0] hit_slot;
    reg              hit_found;
    reg [SLOT_W-1:0] free_slot;
    reg              free_found;
    always @* begin
        hit_slot = {SLOT_W{1'b0}};
        hit_found = 1'b0;
        free_slot = {SLOT_W{1'b0}};
        free_found = 1'b0;
        for (s = 0; s < SLOTS; s = s + 1) begin
            if (!hit_found && slot_used[s[SLOT_W-1:0]] &&
                (slot_descriptor[s[SLOT_W-1:0]] == op_descriptor_id)) begin
                hit_slot = s[SLOT_W-1:0];
                hit_found = 1'b1;
            end
            if (!free_found && !slot_used[s[SLOT_W-1:0]]) begin
                free_slot = s[SLOT_W-1:0];
                free_found = 1'b1;
            end
        end
    end

    wire [SLOT_W-1:0] target = hit_found ? hit_slot : free_slot;
    wire [31:0] target_cursor = hit_found ? slot_cursor[target] : payload_initial_cur;
    wire [31:0] target_capacity = hit_found ? slot_capacity[target] : payload_capacity;
    wire        target_open = hit_found ? slot_open[target] : 1'b0;
    wire [7:0]  target_policy = hit_found ? slot_policy[target] : payload_policy;
    wire        target_unstaged = (target_policy == A3_COMMIT_POLICY_UNSTAGED);
    wire        target_saturating = (target_policy == A3_COMMIT_POLICY_SATURATING);
    // The positions the request presented.  A21's zero-count trap is stated on
    // this and not on the published row count, because zero rows is a
    // malformed *request* and a saturating commit's row count is the ring's.
    wire [31:0] commit_span = op_rows_bound ? op_rows : 32'd0;
    // A21: an unstaged resource stages no row, whatever the request's span is.
    // A25: a saturating one stages its ring, and no more.
    wire [31:0] commit_rows =
        target_unstaged ? 32'd0
      : target_saturating ? ((commit_span < target_capacity) ? commit_span
                                                             : target_capacity)
      : commit_span;
    wire [32:0] commit_end = {1'b0, target_cursor} + {1'b0, commit_rows};

    wire [SLOT_W-1:0] apply_slot = pending_slot[apply_index];
    wire [31:0] apply_rows = pending_rows[apply_index];
    wire [31:0] apply_span = pending_span[apply_index];
    wire        apply_saturating =
        (slot_policy[apply_slot] == A3_COMMIT_POLICY_SATURATING);
    wire [32:0] apply_end = {1'b0, slot_cursor[apply_slot]} + {1'b0, apply_rows};
    // A25: the ring head, which is the slot the next absolute position writes.
    wire [32:0] apply_sum = {1'b0, slot_cursor[apply_slot]} + {1'b0, apply_span};
    wire [32:0] apply_capacity = {1'b0, slot_capacity[apply_slot]};
    // A remainder modulo a 32-bit capacity is a 32-bit value; the extra bit
    // the 33-bit divide carries is provably zero and is not read.
    /* verilator lint_off UNUSED */
    wire [32:0] apply_remainder = apply_sum % apply_capacity;
    /* verilator lint_on UNUSED */
    wire [31:0] apply_wrapped =
        (apply_saturating && (apply_capacity != 33'd0))
            ? apply_remainder[31:0] : apply_end[31:0];

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < SLOTS; i = i + 1) begin
                slot_descriptor[i] <= A3_NO_ID;
                slot_cursor[i] <= 32'd0;
                slot_capacity[i] <= 32'd0;
                slot_row_bytes[i] <= 32'd0;
                slot_generation[i] <= 32'd0;
                slot_policy[i] <= A3_COMMIT_POLICY_REQUEST_SPAN;
                pending_slot[i] <= {SLOT_W{1'b0}};
                pending_rows[i] <= 32'd0;
                pending_span[i] <= 32'd0;
            end
            slot_used <= {SLOTS{1'b0}};
            slot_open <= {SLOTS{1'b0}};
            pending_count <= {(SLOT_W+1){1'b0}};
            apply_index <= {SLOT_W{1'b0}};
            op_done <= 1'b0;
            op_ok <= 1'b0;
            op_trap_class <= A3_TRAP_NONE;
            apply_busy <= 1'b0;
            apply_done <= 1'b0;
            apply_overflow <= 1'b0;
            count_prepares <= 32'd0;
            count_commits <= 32'd0;
            count_discards <= 32'd0;
            count_reads <= 32'd0;
            count_generation_advances <= 32'd0;
            count_commits_applied <= 32'd0;
            count_rows_committed <= 32'd0;
            count_bytes_written <= 64'd0;
        end else begin
            op_done <= 1'b0;
            apply_done <= 1'b0;

            if (clear) begin
                slot_used <= {SLOTS{1'b0}};
                slot_open <= {SLOTS{1'b0}};
                pending_count <= {(SLOT_W+1){1'b0}};
                apply_busy <= 1'b0;
                apply_overflow <= 1'b0;
                count_prepares <= 32'd0;
                count_commits <= 32'd0;
                count_discards <= 32'd0;
                count_reads <= 32'd0;
                count_generation_advances <= 32'd0;
                count_commits_applied <= 32'd0;
                count_rows_committed <= 32'd0;
                count_bytes_written <= 64'd0;
            end else if (discard_all) begin
                // A trap poisons the whole transaction: nothing staged is
                // applied and every open prepare is released.  Releasing the
                // whole declared set -- not only the slots that reached a
                // staged commit -- is what keeps a resource that was prepared
                // and then faulted from refusing a legitimate retry as a
                // double prepare.
                pending_count <= {(SLOT_W+1){1'b0}};
                slot_open <= {SLOTS{1'b0}};
                apply_busy <= 1'b0;
                apply_done <= 1'b1;
                count_discards <= count_discards + session_state_count;
            end else if (commit_all) begin
                if (pending_count == {(SLOT_W+1){1'b0}}) begin
                    apply_done <= 1'b1;
                end else begin
                    apply_busy <= 1'b1;
                    apply_index <= {SLOT_W{1'b0}};
                end
            end else if (apply_busy) begin
                slot_cursor[apply_slot] <=
                    apply_saturating ? apply_wrapped : apply_end[31:0];
                slot_generation[apply_slot] <= slot_generation[apply_slot] + 32'd1;
                slot_open[apply_slot] <= 1'b0;
                count_commits_applied <= count_commits_applied + 32'd1;
                count_rows_committed <= count_rows_committed + apply_rows;
                count_bytes_written <= count_bytes_written +
                    ({32'd0, apply_rows} * {32'd0, slot_row_bytes[apply_slot]});
                // A25: a ring cannot be overflowed by a span, so the
                // divergence flag is a REQUEST_SPAN condition only.
                if (!apply_saturating &&
                    (apply_end > {1'b0, slot_capacity[apply_slot]}))
                    apply_overflow <= 1'b1;
                if (({1'b0, apply_index} + 1'b1) >= pending_count) begin
                    apply_busy <= 1'b0;
                    apply_done <= 1'b1;
                    pending_count <= {(SLOT_W+1){1'b0}};
                end else begin
                    apply_index <= apply_index + 1'b1;
                end
            end else if (op_valid) begin
                op_done <= 1'b1;
                op_ok <= 1'b1;
                op_trap_class <= A3_TRAP_NONE;
                if (!hit_found && !free_found) begin
                    op_ok <= 1'b0;
                    op_trap_class <= A3_TRAP_CAPABILITY;
                end else begin
                    if (!hit_found) begin
                        slot_used[target] <= 1'b1;
                        slot_descriptor[target] <= op_descriptor_id;
                        slot_cursor[target] <= payload_initial_cur;
                        slot_capacity[target] <= payload_capacity;
                        slot_row_bytes[target] <= payload_row_bytes;
                        slot_policy[target] <= payload_policy;
                        slot_generation[target] <= 32'd0;
                    end
                    case (op_sub)
                        A3_STATE_PREPARE: begin
                            if (target_open) begin
                                op_ok <= 1'b0;
                                op_trap_class <= A3_TRAP_STATE;
                            end else begin
                                slot_open[target] <= 1'b1;
                                count_prepares <= count_prepares + 32'd1;
                            end
                        end
                        A3_STATE_READ: count_reads <= count_reads + 32'd1;
                        A3_STATE_COMMIT: begin
                            if (!target_open) begin
                                op_ok <= 1'b0;
                                op_trap_class <= A3_TRAP_STATE;
                            end else if (!target_unstaged &&
                                         (commit_span == 32'd0)) begin
                                // A21: zero rows is a malformed request only
                                // where the request is what supplies them.
                                op_ok <= 1'b0;
                                op_trap_class <= A3_TRAP_STATE;
                            end else if (!target_saturating &&
                                         (commit_end >
                                          {1'b0, target_capacity})) begin
                                // A25: a saturating commit was clamped to the
                                // ring, so this comparison can only refuse a
                                // commit the ring already satisfies.
                                op_ok <= 1'b0;
                                op_trap_class <= A3_TRAP_CAPABILITY;
                            end else if (pending_count >= SLOTS[SLOT_W:0]) begin
                                op_ok <= 1'b0;
                                op_trap_class <= A3_TRAP_CAPABILITY;
                            end else begin
                                pending_slot[pending_count[SLOT_W-1:0]] <= target;
                                pending_rows[pending_count[SLOT_W-1:0]] <= commit_rows;
                                pending_span[pending_count[SLOT_W-1:0]] <= commit_span;
                                pending_count <= pending_count + 1'b1;
                                count_commits <= count_commits + 32'd1;
                            end
                        end
                        A3_STATE_DISCARD: begin
                            slot_open[target] <= 1'b0;
                            count_discards <= count_discards + 32'd1;
                        end
                        A3_STATE_GENERATION_ADVANCE:
                            count_generation_advances <=
                                count_generation_advances + 32'd1;
                        default: begin
                            op_ok <= 1'b0;
                            op_trap_class <= A3_TRAP_STATE;
                        end
                    endcase
                end
            end
        end
    end
endmodule
