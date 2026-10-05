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
    // The package is referenced by scope rather than wildcard-imported: a
    // wildcard import is not accepted by every open synthesis front end this
    // program pins, and a block that only elaborates in a simulator is not an
    // implementable block.  [OI-43] docs/UNIFIED_EXECUTION_CHECKLIST.md
#(
    parameter integer SLOTS = ot_a3_pkg::A3_STATE_SLOTS
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
    wire [SLOTS-1:0] slot_match;
    generate for(genvar n=0;n<SLOTS;n=n+1)begin: match_slot
        assign slot_match[n]=slot_used[n] && slot_descriptor[n]==op_descriptor_id;
    end endgenerate
    reg [31:0] matched_cursor, matched_capacity;
    reg [7:0] matched_policy;
    reg matched_open;
    // Descriptor allocation occurs only on a lookup miss, so used entries
    // have unique descriptor identities. Select payload with that one-hot
    // match directly; the encoded index is needed only for table writes.
    always @* begin
        matched_cursor=0;matched_capacity=0;matched_policy=0;matched_open=0;
        for(integer n=0;n<SLOTS;n=n+1)begin
            matched_cursor=matched_cursor | (slot_cursor[n] & {32{slot_match[n]}});
            matched_capacity=matched_capacity | (slot_capacity[n] & {32{slot_match[n]}});
            matched_policy=matched_policy | (slot_policy[n] & {8{slot_match[n]}});
            matched_open=matched_open | (slot_open[n] & slot_match[n]);
        end
    end
    always @* begin
        hit_slot = {SLOT_W{1'b0}};
        hit_found = 1'b0;
        free_slot = {SLOT_W{1'b0}};
        free_found = 1'b0;
        for (s = 0; s < SLOTS; s = s + 1) begin
            if (!hit_found && slot_match[s[SLOT_W-1:0]]) begin
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
    wire [31:0] target_cursor = hit_found ? matched_cursor : payload_initial_cur;
    wire [31:0] target_capacity = hit_found ? matched_capacity : payload_capacity;
    wire        target_open = matched_open;
    wire [7:0]  target_policy = hit_found ? matched_policy : payload_policy;
    wire        target_unstaged = (target_policy == ot_a3_pkg::A3_COMMIT_POLICY_UNSTAGED);
    wire        target_saturating = (target_policy == ot_a3_pkg::A3_COMMIT_POLICY_SATURATING);
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
    // Only non-saturating policies use this bound. Keep the saturating
    // capacity/min selection out of its add-and-compare path.
    wire [32:0] commit_end = {1'b0, target_cursor} +
        {1'b0, (target_unstaged ? 32'd0 : commit_span)};

    wire [SLOT_W-1:0] apply_slot = pending_slot[apply_index];
    wire [31:0] apply_rows = pending_rows[apply_index];
    wire [31:0] apply_span = pending_span[apply_index];
    wire        apply_saturating =
        (slot_policy[apply_slot] == ot_a3_pkg::A3_COMMIT_POLICY_SATURATING);
    wire [32:0] apply_end = {1'b0, slot_cursor[apply_slot]} + {1'b0, apply_rows};
    // A25: the ring head, which is the slot the next absolute position writes.
    wire [32:0] apply_sum = {1'b0, slot_cursor[apply_slot]} + {1'b0, apply_span};
    wire [32:0] apply_capacity = {1'b0, slot_capacity[apply_slot]};
    // Ring commits are infrequent transaction-drain work. Keep a general
    // 33-by-32 remainder off the common control clock: one restoring step
    // per cycle, with exact mask bypass for power-of-two capacities.
    reg [1:0] modulo_state;
    reg [32:0] modulo_shift;
    reg [31:0] modulo_rem, modulo_den;
    reg [5:0] modulo_left;
    wire [32:0] modulo_trial = {modulo_rem, modulo_shift[32]};
    wire [31:0] modulo_sub = modulo_trial[31:0] - modulo_den;
    wire [31:0] modulo_next = modulo_trial >= {1'b0, modulo_den}
        ? modulo_sub : modulo_trial[31:0];
    wire [31:0] capacity_mask = apply_capacity[31:0] - 32'd1;
    wire capacity_pow2 = (apply_capacity[31:0] & capacity_mask) == 0;
    wire needs_modulo = apply_saturating && apply_capacity != 0 && !capacity_pow2;
    wire [31:0] apply_wrapped = apply_capacity == 0 ? apply_end[31:0]
        : capacity_pow2 ? (apply_sum[31:0] & capacity_mask) : modulo_rem;

    // Payload is not architectural until pending_count advances. Capture the
    // free entry without fanning admission's complete verdict into every bit.
    // A rejected commit cannot expose it; the next attempt overwrites it.
    // The capacity guard protects existing entries when the queue is full.
    always @(posedge clk) begin
        if (rst_n && !clear && !discard_all && !commit_all && !apply_busy &&
            op_valid && op_sub == ot_a3_pkg::A3_STATE_COMMIT &&
            pending_count < SLOTS[SLOT_W:0]) begin
            pending_slot[pending_count[SLOT_W-1:0]] <= target;
            pending_rows[pending_count[SLOT_W-1:0]] <= commit_rows;
            pending_span[pending_count[SLOT_W-1:0]] <= commit_span;
        end
    end

    // Experimental apply pipeline: select operands, multiply, then retire.
    // Payload flops need no reset; phase controls validity and cancellation.
    reg [1:0] apply_phase;
    reg [31:0] apply_rows_q, apply_row_bytes_q;
    reg [63:0] apply_bytes_q;
    always @(posedge clk) begin
        if (apply_busy && apply_phase == 0) begin
            apply_rows_q <= apply_rows;
            apply_row_bytes_q <= slot_row_bytes[apply_slot];
        end
        if (apply_busy && apply_phase == 1)
            apply_bytes_q <= {32'd0, apply_rows_q} * {32'd0, apply_row_bytes_q};
    end

    // Parallel increment carry predicates depend only on the old counter.
    // Keep admission's late enable out of a serial increment carry chain.
    wire [31:0] commit_increment;
    assign commit_increment[0] = ~count_commits[0];
    genvar cb;
    generate for (cb = 1; cb < 32; cb = cb + 1) begin : commit_carry
        assign commit_increment[cb] = count_commits[cb] ^ (&count_commits[cb-1:0]);
    end endgenerate

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < SLOTS; i = i + 1) begin
                slot_descriptor[i] <= ot_a3_pkg::A3_NO_ID;
                slot_cursor[i] <= 32'd0;
                slot_capacity[i] <= 32'd0;
                slot_row_bytes[i] <= 32'd0;
                slot_generation[i] <= 32'd0;
                slot_policy[i] <= ot_a3_pkg::A3_COMMIT_POLICY_REQUEST_SPAN;
            end
            slot_used <= {SLOTS{1'b0}};
            slot_open <= {SLOTS{1'b0}};
            pending_count <= {(SLOT_W+1){1'b0}};
            apply_index <= {SLOT_W{1'b0}};
            modulo_state <= 0;
                apply_phase <= 0; modulo_shift <= 0; modulo_rem <= 0;
            modulo_den <= 0; modulo_left <= 0;
            op_done <= 1'b0;
            op_ok <= 1'b0;
            op_trap_class <= ot_a3_pkg::A3_TRAP_NONE;
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
                modulo_state <= 0;
                apply_phase <= 0;
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
                modulo_state <= 0;
                apply_phase <= 0;
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
                modulo_state <= 0;
                apply_phase <= 0;
                if (pending_count == {(SLOT_W+1){1'b0}}) begin
                    apply_done <= 1'b1;
                end else begin
                    apply_busy <= 1'b1;
                    apply_index <= {SLOT_W{1'b0}};
                end
            end else if (apply_busy) begin
                if (apply_phase == 0) begin
                    apply_phase <= 1;
                end else if (apply_phase == 1) begin
                    apply_phase <= 2;
                end
                // Byte accounting and ring remainder are independent. Start
                // both together and retire only after both results are valid.
                if (modulo_state == 1) begin
                    modulo_rem <= modulo_next;
                    modulo_shift <= {modulo_shift[31:0], 1'b0};
                    modulo_left <= modulo_left - 1'b1;
                    if (modulo_left == 1) modulo_state <= 2;
                end else if (needs_modulo && modulo_state == 0) begin
                    modulo_shift <= apply_sum;
                    modulo_rem <= 0;
                    modulo_den <= apply_capacity[31:0];
                    modulo_left <= 33;
                    modulo_state <= 1;
                end else if (apply_phase == 2) begin
                modulo_state <= 0;
                apply_phase <= 0;
                slot_cursor[apply_slot] <=
                    apply_saturating ? apply_wrapped : apply_end[31:0];
                slot_generation[apply_slot] <= slot_generation[apply_slot] + 32'd1;
                slot_open[apply_slot] <= 1'b0;
                count_commits_applied <= count_commits_applied + 32'd1;
                count_rows_committed <= count_rows_committed + apply_rows;
                count_bytes_written <= count_bytes_written +
                    apply_bytes_q;
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
                end
            end else if (op_valid) begin
                op_done <= 1'b1;
                op_ok <= 1'b1;
                op_trap_class <= ot_a3_pkg::A3_TRAP_NONE;
                if (!hit_found && !free_found) begin
                    op_ok <= 1'b0;
                    op_trap_class <= ot_a3_pkg::A3_TRAP_CAPABILITY;
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
                        ot_a3_pkg::A3_STATE_PREPARE: begin
                            if (target_open) begin
                                op_ok <= 1'b0;
                                op_trap_class <= ot_a3_pkg::A3_TRAP_STATE;
                            end else begin
                                slot_open[target] <= 1'b1;
                                count_prepares <= count_prepares + 32'd1;
                            end
                        end
                        ot_a3_pkg::A3_STATE_READ: count_reads <= count_reads + 32'd1;
                        ot_a3_pkg::A3_STATE_COMMIT: begin
                            if (!target_open) begin
                                op_ok <= 1'b0;
                                op_trap_class <= ot_a3_pkg::A3_TRAP_STATE;
                            end else if (!target_unstaged &&
                                         (commit_span == 32'd0)) begin
                                // A21: zero rows is a malformed request only
                                // where the request is what supplies them.
                                op_ok <= 1'b0;
                                op_trap_class <= ot_a3_pkg::A3_TRAP_STATE;
                            end else if (!target_saturating &&
                                         (commit_end >
                                          {1'b0, target_capacity})) begin
                                // A25: a saturating commit was clamped to the
                                // ring, so this comparison can only refuse a
                                // commit the ring already satisfies.
                                op_ok <= 1'b0;
                                op_trap_class <= ot_a3_pkg::A3_TRAP_CAPABILITY;
                            end else if (pending_count >= SLOTS[SLOT_W:0]) begin
                                op_ok <= 1'b0;
                                op_trap_class <= ot_a3_pkg::A3_TRAP_CAPABILITY;
                            end else begin
                                pending_count <= pending_count + 1'b1;
                                count_commits <= commit_increment;
                            end
                        end
                        ot_a3_pkg::A3_STATE_DISCARD: begin
                            slot_open[target] <= 1'b0;
                            count_discards <= count_discards + 32'd1;
                        end
                        ot_a3_pkg::A3_STATE_GENERATION_ADVANCE:
                            count_generation_advances <=
                                count_generation_advances + 32'd1;
                        default: begin
                            op_ok <= 1'b0;
                            op_trap_class <= ot_a3_pkg::A3_TRAP_STATE;
                        end
                    endcase
                end
            end
        end
    end
endmodule
