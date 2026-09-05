`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 issue record store: the control half of the IRS
// (docs/CHIP_ARCHITECTURE_DESIGN.md sections 3.2 items 2-3 and 5, 3.6, 3.8;
// [T2.1-15]).
//
// One entry per outstanding engine operation, A3_IRS_ENTRIES of them: an
// operation is allocated an entry at issue and frees it when its completion
// is reported, in any order.  Issue stalls (alloc_ready low) while every entry
// is taken, while A3_OUTSTANDING operations are outstanding, or while the
// operation's queue already holds A3_QUEUE_DEPTH -- bounded queue occupancy as
// a hardware property (ADR-003 section 9).  The entry's 512-byte payload --
// the six resolved views and the counter snapshot -- is a memory macro at the
// vehicle (section 11.2) and lives outside this block behind the sequencer's
// irs_* payload port; only what the control plane must search or compare is
// held here in flops: serial, pc, signal event and release bit, queue.
//
// Retirement.  A completion for slot s is registered and re-emitted one cycle
// later as retire_*: the event scoreboard sets signalled/published from it,
// the dependence table releases the entry, the sequencer counts it.  Beside
// the event ID the retirement says whether this was the *last* outstanding
// producer of that event (a CAM over the live entries), which is what lets
// the scoreboard clear ``pending`` without a per-event counter.
//
// Faults.  A completion carrying a fault records {serial, pc, class, slot};
// a later faulting completion replaces the record only if its serial is
// lower, so first_fault_instruction is the lowest issue serial among faulting
// instructions (section 3.2 item 5).  The sequencer, once nothing is
// outstanding, reads that slot's counter snapshot from the payload and
// freezes the transaction's counters at the faulting serial.  fault_valid is
// sticky until clear.
//
// A completion naming a slot that holds no operation is a protocol error of
// the engine side; irs_protocol_error is sticky and the checkers assert it
// zero.
//
// The package is referenced by scope, never wildcard-imported [OI-43].
// ---------------------------------------------------------------------------
module ot_a3_issue_record_store #(
    parameter integer ENTRIES = ot_a3_pkg::A3_IRS_ENTRIES,
    parameter integer QUEUES  = ot_a3_pkg::A3_QUEUE_COUNT
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          clear,

    // -- allocation --------------------------------------------------------
    // free_slot is the lowest free entry; alloc_ready says an allocation of
    // alloc_queue could be accepted now.  The sequencer reserves free_slot
    // ahead of the issue handshake and presents it back as alloc_slot: no
    // other allocator exists, so the reservation holds.
    input  wire [4:0]    alloc_queue,
    output wire          alloc_ready,
    output wire [4:0]    free_slot,
    input  wire          alloc_valid,
    input  wire [4:0]    alloc_slot,
    input  wire [31:0]   alloc_serial,
    input  wire [31:0]   alloc_pc,
    input  wire [31:0]   alloc_event_id,
    input  wire          alloc_release,

    // -- completion (engine side, any order, one per cycle) ---------------
    input  wire          complete_valid,
    input  wire [4:0]    complete_slot,
    input  wire          complete_fault,
    input  wire [15:0]   complete_trap_class,

    // -- retirement (one cycle after completion) --------------------------
    output reg           retire_valid,
    output reg  [4:0]    retire_slot,
    output reg  [31:0]   retire_serial,
    output reg  [31:0]   retire_event_id,
    output reg           retire_release,
    output reg           retire_event_last,
    output reg           retire_fault,

    // -- first fault -------------------------------------------------------
    output reg           fault_valid,
    output reg  [4:0]    fault_slot,
    output reg  [31:0]   fault_serial,
    output reg  [31:0]   fault_pc,
    output reg  [15:0]   fault_trap_class,

    // -- occupancy ---------------------------------------------------------
    output reg  [5:0]    outstanding,
    output reg  [5:0]    outstanding_with_event,
    output wire          any_outstanding,
    output reg  [5:0]    max_outstanding,
    output reg           irs_protocol_error
);
    reg [ENTRIES-1:0] valid;
    reg [31:0] serial   [0:ENTRIES-1];
    reg [31:0] pc       [0:ENTRIES-1];
    reg [31:0] event_id [0:ENTRIES-1];
    reg        release_bit  [0:ENTRIES-1];
    reg [4:0]  queue    [0:ENTRIES-1];
    reg [4:0]  queue_count [0:QUEUES-1];

    // lowest free entry (one loop variable per process: a variable shared
    // between a combinational and a sequential process is two drivers to
    // the synthesis front end)
    reg [4:0] lowest_free;
    reg       any_free;
    integer j;
    always @* begin
        lowest_free = 5'd0;
        any_free = 1'b0;
        for (j = ENTRIES - 1; j >= 0; j = j - 1) begin
            if (!valid[j]) begin
                lowest_free = j[4:0];
                any_free = 1'b1;
            end
        end
    end
    assign free_slot = lowest_free;
    assign alloc_ready = any_free &&
                         (outstanding < ot_a3_pkg::A3_OUTSTANDING) &&
                         (queue_count[alloc_queue] < ot_a3_pkg::A3_QUEUE_DEPTH);
    assign any_outstanding = |valid;

    // completion CAM: is any *other* live entry a producer of the same event?
    // An allocation landing in this very cycle counts: it is a producer of
    // its event from the handshake on, so it must keep the event pending.
    wire        complete_hit = complete_valid && valid[complete_slot];
    wire [31:0] complete_event = event_id[complete_slot];
    reg         other_producer;
    integer     k;
    always @* begin
        other_producer = alloc_valid && (alloc_slot != complete_slot) &&
                         (alloc_event_id == complete_event);
        for (k = 0; k < ENTRIES; k = k + 1) begin
            if (valid[k] && (k[4:0] != complete_slot) &&
                (event_id[k] == complete_event))
                other_producer = 1'b1;
        end
    end

    wire alloc_fire = alloc_valid;
    wire retire_fire = complete_hit;
    wire alloc_has_event = (alloc_event_id != ot_a3_pkg::A3_NO_ID);
    wire retire_has_event = (complete_event != ot_a3_pkg::A3_NO_ID);
    wire [5:0] outstanding_next = outstanding + (alloc_fire ? 6'd1 : 6'd0) -
                                  (retire_fire ? 6'd1 : 6'd0);

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid <= {ENTRIES{1'b0}};
            for (i = 0; i < ENTRIES; i = i + 1) begin
                serial[i] <= 32'd0;
                pc[i] <= 32'd0;
                event_id[i] <= ot_a3_pkg::A3_NO_ID;
                release_bit[i] <= 1'b0;
                queue[i] <= 5'd0;
            end
            for (i = 0; i < QUEUES; i = i + 1)
                queue_count[i] <= 5'd0;
            retire_valid <= 1'b0;
            retire_slot <= 5'd0;
            retire_serial <= 32'd0;
            retire_event_id <= ot_a3_pkg::A3_NO_ID;
            retire_release <= 1'b0;
            retire_event_last <= 1'b0;
            retire_fault <= 1'b0;
            fault_valid <= 1'b0;
            fault_slot <= 5'd0;
            fault_serial <= 32'd0;
            fault_pc <= 32'd0;
            fault_trap_class <= ot_a3_pkg::A3_TRAP_NONE;
            outstanding <= 6'd0;
            outstanding_with_event <= 6'd0;
            max_outstanding <= 6'd0;
            irs_protocol_error <= 1'b0;
        end else begin
            retire_valid <= 1'b0;
            if (clear) begin
                valid <= {ENTRIES{1'b0}};
                for (i = 0; i < QUEUES; i = i + 1)
                    queue_count[i] <= 5'd0;
                fault_valid <= 1'b0;
                outstanding <= 6'd0;
                outstanding_with_event <= 6'd0;
                max_outstanding <= 6'd0;
                irs_protocol_error <= 1'b0;
            end else begin
                if (complete_valid && !valid[complete_slot])
                    irs_protocol_error <= 1'b1;
                if (alloc_fire) begin
                    valid[alloc_slot] <= 1'b1;
                    serial[alloc_slot] <= alloc_serial;
                    pc[alloc_slot] <= alloc_pc;
                    event_id[alloc_slot] <= alloc_event_id;
                    release_bit[alloc_slot] <= alloc_release;
                    queue[alloc_slot] <= alloc_queue;
                end
                if (retire_fire) begin
                    valid[complete_slot] <= 1'b0;
                    retire_valid <= 1'b1;
                    retire_slot <= complete_slot;
                    retire_serial <= serial[complete_slot];
                    retire_event_id <= complete_event;
                    retire_release <= release_bit[complete_slot];
                    retire_event_last <= !other_producer;
                    retire_fault <= complete_fault;
                    if (complete_fault &&
                        (!fault_valid || (serial[complete_slot] < fault_serial))) begin
                        fault_valid <= 1'b1;
                        fault_slot <= complete_slot;
                        fault_serial <= serial[complete_slot];
                        fault_pc <= pc[complete_slot];
                        fault_trap_class <= complete_trap_class;
                    end
                end
                // queue occupancy: an allocation and a retirement of the same
                // queue in one cycle leave it unchanged
                if (alloc_fire && retire_fire &&
                    (alloc_queue == queue[complete_slot])) begin
                    queue_count[alloc_queue] <= queue_count[alloc_queue];
                end else begin
                    if (alloc_fire)
                        queue_count[alloc_queue] <= queue_count[alloc_queue] + 5'd1;
                    if (retire_fire)
                        queue_count[queue[complete_slot]] <=
                            queue_count[queue[complete_slot]] - 5'd1;
                end
                outstanding <= outstanding_next;
                if (outstanding_next > max_outstanding)
                    max_outstanding <= outstanding_next;
                outstanding_with_event <= outstanding_with_event +
                    ((alloc_fire && alloc_has_event) ? 6'd1 : 6'd0) -
                    ((retire_fire && retire_has_event) ? 6'd1 : 6'd0);
            end
        end
    end
endmodule
