`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 event scoreboard and wait-set evaluation.
//
// Amendment A24.  Events are single assignment, and single assignment is a
// property of the *program text*: at most one instruction may name an event ID
// as its signal event, which verifier._verify_instructions proves at
// admission.  It is not a property of the execution.  A loop-compressed
// program -- the only kind ABI 3.0 admits, which is what amendments A4 and A13
// exist for -- re-executes its producer once per trip, so an event inside a
// loop body is signalled once per trip by the one instruction that owns it.
//
// An event is therefore a **level** that the producer raises and nothing
// lowers before the transaction ends.  Raising a level that is already raised
// is idempotent, not an error.  This block used to raise a sticky error bit on
// the second signal of an ID, which made every one of the shipped programs
// look defective: Qwen3-8B signals 691 times against 26 IDs on one prefill.
// runtime.sim.device.Device has always held ``signalled`` as a set, and the
// set is the reference; A24 writes the rule down and this block implements it.
// Two bits are kept per event:
//
//   signalled  the producing instruction retired, on this trip or an earlier
//              one; monotone within a transaction
//   published  its writes are ordered before the signal (SIGNAL_RELEASE, or a
//              wait-set ordering of RELEASE / ACQUIRE_RELEASE / SEQUENTIAL);
//              monotone for the same reason
//
// A wait set (EVENT_WAIT_SET_PAYLOAD) is evaluated one producer per cycle, in
// slot order, so the cost is bounded by the frozen twelve-producer maximum and
// the trap it raises names a definite producer.  A wait whose instruction
// carries WAIT_ACQUIRE, or whose descriptor declares ACQUIRE / ACQUIRE_RELEASE
// / SEQUENTIAL ordering, additionally requires the published bit: an acquire
// may not complete against a signal that has not been ordered against its
// producer's writes.  Waiting on an event that was never signalled is an
// internal-invariant trap (class 13), matching the golden model.
//
// ``signal_error`` therefore reports exactly one condition: a signal naming an
// event ID outside the implemented space.  Under amendment A23 that condition
// is refused at admission (verifier check ``event_id_bound``), so on any
// admitted program the bit is zero -- and the deployment co-simulation now
// asserts that rather than merely counting it.
// ---------------------------------------------------------------------------
module ot_a3_event_scoreboard
    // The package is referenced by scope rather than wildcard-imported: a
    // wildcard import is not accepted by every open synthesis front end this
    // program pins, and a block that only elaborates in a simulator is not an
    // implementable block.  [OI-43] docs/UNIFIED_EXECUTION_CHECKLIST.md
#(
    parameter integer EVENTS = ot_a3_pkg::A3_EVENT_COUNT
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         clear,

    // publication
    input  wire         signal_valid,
    input  wire [31:0]  signal_event_id,
    input  wire         signal_release,
    output reg          signal_error,      // sticky: event ID out of range

    // wait-set evaluation
    input  wire         wait_start,
    input  wire [511:0] wait_payload,      // EVENT_WAIT_SET payload, 64 bytes
    input  wire         wait_acquire,      // instruction WAIT_ACQUIRE flag
    output reg          wait_busy,
    output reg          wait_done,
    output reg          wait_ok,
    output reg  [15:0]  wait_trap_class,
    output reg  [31:0]  wait_fault_event,

    output reg  [31:0]  signal_count,
    output reg  [31:0]  wait_count
);
    // Derived from EVENTS, not written beside it.  A fixed width and a
    // parameterised bit vector look identical until someone raises EVENTS:
    // the range check ``slot_event < EVENTS`` would then admit event 300 and
    // the truncated index would alias it silently onto event 44.  A parameter
    // that looks parameterisable and is not is a trap, so the index width is
    // derived from the parameter it indexes.
    localparam integer EVENT_INDEX_W = (EVENTS <= 1) ? 1 : $clog2(EVENTS);

    reg [EVENTS-1:0] signalled;
    reg [EVENTS-1:0] published;

    wire [7:0] payload_ordering       = wait_payload[15:8];
    wire [7:0] payload_producer_count = wait_payload[31:24];
    reg  [7:0] producer_count;
    reg  [7:0] slot;
    reg        acquire_required;
    reg [511:0] payload_hold;

    wire [15:0] slot_bit = 16'd64 + ({8'd0, slot} << 5);
    wire [31:0] slot_event = payload_hold[slot_bit +: 32];
    wire        slot_in_range = (slot_event < EVENTS);
    wire [EVENT_INDEX_W-1:0] slot_index = slot_event[EVENT_INDEX_W-1:0];

    wire ordering_acquire = (payload_ordering == ot_a3_pkg::A3_ORDER_ACQUIRE) ||
                            (payload_ordering == ot_a3_pkg::A3_ORDER_ACQUIRE_RELEASE) ||
                            (payload_ordering == ot_a3_pkg::A3_ORDER_SEQUENTIAL);

    wire signal_in_range = (signal_event_id < EVENTS);
    wire [EVENT_INDEX_W-1:0] signal_index = signal_event_id[EVENT_INDEX_W-1:0];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            signalled <= {EVENTS{1'b0}};
            published <= {EVENTS{1'b0}};
            signal_error <= 1'b0;
            wait_busy <= 1'b0;
            wait_done <= 1'b0;
            wait_ok <= 1'b0;
            wait_trap_class <= ot_a3_pkg::A3_TRAP_NONE;
            wait_fault_event <= ot_a3_pkg::A3_NO_ID;
            producer_count <= 8'd0;
            slot <= 8'd0;
            acquire_required <= 1'b0;
            payload_hold <= 512'b0;
            signal_count <= 32'd0;
            wait_count <= 32'd0;
        end else begin
            wait_done <= 1'b0;
            if (clear) begin
                signalled <= {EVENTS{1'b0}};
                published <= {EVENTS{1'b0}};
                signal_error <= 1'b0;
                wait_busy <= 1'b0;
                signal_count <= 32'd0;
                wait_count <= 32'd0;
            end else begin
                if (signal_valid) begin
                    signal_count <= signal_count + 32'd1;
                    if (!signal_in_range) begin
                        // A23: an ID the scoreboard cannot address.  Admission
                        // refuses this, so reaching it is an implementation
                        // fault and the bit is sticky so it cannot be missed.
                        signal_error <= 1'b1;
                    end else begin
                        // A24: setting a level that is already set is this
                        // event's one producer running on a later loop trip.
                        signalled[signal_index] <= 1'b1;
                        if (signal_release)
                            published[signal_index] <= 1'b1;
                    end
                end

                if (wait_start) begin
                    wait_busy <= 1'b1;
                    wait_count <= wait_count + 32'd1;
                    payload_hold <= wait_payload;
                    producer_count <= payload_producer_count;
                    acquire_required <= wait_acquire || ordering_acquire;
                    slot <= 8'd0;
                    wait_ok <= 1'b1;
                    wait_trap_class <= ot_a3_pkg::A3_TRAP_NONE;
                    wait_fault_event <= ot_a3_pkg::A3_NO_ID;
                    if (payload_producer_count == 8'd0) begin
                        // A wait set with no producers is rejected at
                        // admission; treat it as an internal invariant here.
                        wait_busy <= 1'b0;
                        wait_done <= 1'b1;
                        wait_ok <= 1'b0;
                        wait_trap_class <= ot_a3_pkg::A3_TRAP_INTERNAL;
                    end
                end else if (wait_busy) begin
                    if (!slot_in_range ||
                        !signalled[slot_index] ||
                        (acquire_required && !published[slot_index])) begin
                        wait_busy <= 1'b0;
                        wait_done <= 1'b1;
                        wait_ok <= 1'b0;
                        wait_trap_class <= ot_a3_pkg::A3_TRAP_INTERNAL;
                        wait_fault_event <= slot_event;
                    end else if (slot + 8'd1 >= producer_count) begin
                        wait_busy <= 1'b0;
                        wait_done <= 1'b1;
                        wait_ok <= 1'b1;
                    end else begin
                        slot <= slot + 8'd1;
                    end
                end
            end
        end
    end
endmodule
