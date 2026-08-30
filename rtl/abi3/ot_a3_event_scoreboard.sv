`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 event scoreboard and wait-set evaluation.
//
// Events are single assignment: a program may signal an event ID at most once
// (verifier._verify_instructions proves this at admission, and this block
// enforces it again at run time rather than trusting the proof).  Two bits are
// kept per event:
//
//   signalled  the producing instruction retired
//   published  its writes are ordered before the signal (SIGNAL_RELEASE, or a
//              wait-set ordering of RELEASE / ACQUIRE_RELEASE / SEQUENTIAL)
//
// A wait set (EVENT_WAIT_SET_PAYLOAD) is evaluated one producer per cycle, in
// slot order, so the cost is bounded by the frozen twelve-producer maximum and
// the trap it raises names a definite producer.  A wait whose instruction
// carries WAIT_ACQUIRE, or whose descriptor declares ACQUIRE / ACQUIRE_RELEASE
// / SEQUENTIAL ordering, additionally requires the published bit: an acquire
// may not complete against a signal that has not been ordered against its
// producer's writes.  Waiting on an event that was never signalled is an
// internal-invariant trap (class 13), matching the golden model.
// ---------------------------------------------------------------------------
module ot_a3_event_scoreboard
    import ot_a3_pkg::*;
#(
    parameter integer EVENTS = A3_EVENT_COUNT
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         clear,

    // publication
    input  wire         signal_valid,
    input  wire [31:0]  signal_event_id,
    input  wire         signal_release,
    output reg          signal_error,      // sticky: repeat assignment seen

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

    wire ordering_acquire = (payload_ordering == A3_ORDER_ACQUIRE) ||
                            (payload_ordering == A3_ORDER_ACQUIRE_RELEASE) ||
                            (payload_ordering == A3_ORDER_SEQUENTIAL);

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
            wait_trap_class <= A3_TRAP_NONE;
            wait_fault_event <= A3_NO_ID;
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
                        signal_error <= 1'b1;
                    end else begin
                        if (signalled[signal_index])
                            signal_error <= 1'b1;
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
                    wait_trap_class <= A3_TRAP_NONE;
                    wait_fault_event <= A3_NO_ID;
                    if (payload_producer_count == 8'd0) begin
                        // A wait set with no producers is rejected at
                        // admission; treat it as an internal invariant here.
                        wait_busy <= 1'b0;
                        wait_done <= 1'b1;
                        wait_ok <= 1'b0;
                        wait_trap_class <= A3_TRAP_INTERNAL;
                    end
                end else if (wait_busy) begin
                    if (!slot_in_range ||
                        !signalled[slot_index] ||
                        (acquire_required && !published[slot_index])) begin
                        wait_busy <= 1'b0;
                        wait_done <= 1'b1;
                        wait_ok <= 1'b0;
                        wait_trap_class <= A3_TRAP_INTERNAL;
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
