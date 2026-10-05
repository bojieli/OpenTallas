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
// is idempotent, not an error.  runtime.sim.device.Device has always held
// ``signalled`` as a set, and the set is the reference; A24 writes the rule
// down and this block implements it.  Three bits are kept per event
// (docs/CHIP_ARCHITECTURE_DESIGN.md section 3.6, [T2.1-17], AM-C1: 2,048
// events):
//
//   pending    an engine instruction naming the event has been issued and
//              has not completed; cleared when the last outstanding producer
//              of the event completes (the issue record store's CAM says
//              which completion is the last)
//   signalled  the producing instruction retired, on this trip or an earlier
//              one; monotone within a transaction
//   published  its writes are ordered before the signal (SIGNAL_RELEASE, or a
//              wait-set ordering of RELEASE / ACQUIRE_RELEASE / SEQUENTIAL);
//              monotone for the same reason
//
// A wait set (EVENT_WAIT_SET_PAYLOAD) is evaluated four producers per cycle
// over three cycles (twelve is the frozen maximum), and the decision is made
// only after every producer has been inspected (AM-C10):
//
//   * a producer that is neither pending nor signalled was never issued: trap
//     13 naming the lowest such slot -- the golden model's "wait on an event
//     that has not been signalled", preserved exactly, because in the golden
//     model an issued producer is already signalled and so "not signalled"
//     there is "neither" here;
//   * otherwise, while any producer is pending the wait stalls and rescans --
//     the one case the golden model cannot exhibit, and the only one that
//     becomes a stall; a producer signalled on an earlier loop trip and
//     re-issued now is pending, and stalls (the conservative reading);
//   * otherwise the wait passes, provided every producer is also published
//     when the instruction carries WAIT_ACQUIRE or the descriptor declares
//     ACQUIRE / ACQUIRE_RELEASE / SEQUENTIAL ordering (trap 13 if not).
//
// A CONTROL instruction that names an event publishes it directly at its
// retirement (it is never pending): the control_signal_* port.
//
// ``signal_error`` reports exactly one condition: a signal or an issue naming
// an event ID outside the implemented space.  Under amendment A23 that
// condition is refused at admission (verifier check ``event_id_bound``), so on
// any admitted program the bit is zero -- and the deployment co-simulation
// asserts that rather than merely counting it.
//
// The package is referenced by scope, never wildcard-imported [OI-43].
// ---------------------------------------------------------------------------
module ot_a3_event_scoreboard #(
    parameter integer EVENTS = ot_a3_pkg::A3_EVENT_COUNT
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         clear,

    // engine issue: the event goes pending
    input  wire         issue_valid,
    input  wire [31:0]  issue_event_id,

    // engine completion (from the issue record store's retirement)
    input  wire         complete_valid,
    input  wire [31:0]  complete_event_id,
    input  wire         complete_release,
    input  wire         complete_last,     // no other outstanding producer of this event

    // CONTROL retirement: signalled (and published under release) directly
    input  wire         control_signal_valid,
    input  wire [31:0]  control_signal_event_id,
    input  wire         control_signal_release,

    output reg          signal_error,      // sticky: event ID out of range

    // wait-set evaluation
    input  wire         wait_start,
    input  wire [511:0] wait_payload,      // EVENT_WAIT_SET payload, 64 bytes
    input  wire         wait_acquire,      // instruction WAIT_ACQUIRE flag
    output reg          wait_busy,
    output reg          wait_done,         // pulses on pass or trap only
    output reg          wait_ok,
    output reg  [15:0]  wait_trap_class,
    output reg  [31:0]  wait_fault_event,
    output reg          wait_stalled,      // level: rescanning behind a pending producer

    output reg  [31:0]  signal_count,
    output reg  [31:0]  wait_count
);
    // Derived from EVENTS, not written beside it: the range check below
    // must agree with the index width or an out-of-range ID would alias.
    localparam integer EVENT_INDEX_W = (EVENTS <= 1) ? 1 : $clog2(EVENTS);

    reg [EVENTS-1:0] pending;
    reg [EVENTS-1:0] signalled;
    reg [EVENTS-1:0] published;

    wire [7:0] payload_ordering       = wait_payload[15:8];
    wire [7:0] payload_producer_count = wait_payload[31:24];
    reg  [7:0] producer_count;
    reg  [1:0] chunk;                   // 0..2: producers 4c..4c+3
    reg        acquire_required;
    reg [511:0] payload_hold;
    reg        fault_seen;
    reg [31:0] fault_event;
    reg        pending_seen;

    wire ordering_acquire = (payload_ordering == ot_a3_pkg::A3_ORDER_ACQUIRE) ||
                            (payload_ordering == ot_a3_pkg::A3_ORDER_ACQUIRE_RELEASE) ||
                            (payload_ordering == ot_a3_pkg::A3_ORDER_SEQUENTIAL);

    // -- four read ports over the current chunk ----------------------------
    wire [31:0] port_event [0:3];
    wire        port_valid [0:3];
    wire        port_in_range [0:3];
    wire        port_pending [0:3];
    wire        port_signalled [0:3];
    wire        port_published [0:3];
    genvar gp;
    generate
        for (gp = 0; gp < 4; gp = gp + 1) begin : g_port
            wire [3:0]  slot = {chunk, 2'd0} + gp;
            wire [8:0]  bit_index = 9'd64 + ({5'd0, slot} << 5);
            assign port_event[gp] = payload_hold[bit_index +: 32];
            assign port_valid[gp] = ({4'd0, slot} < producer_count);
            assign port_in_range[gp] = (port_event[gp] < EVENTS);
            wire [EVENT_INDEX_W-1:0] idx = port_event[gp][EVENT_INDEX_W-1:0];
            assign port_pending[gp] = pending[idx];
            assign port_signalled[gp] = signalled[idx];
            assign port_published[gp] = published[idx];
        end
    endgenerate

    // Per-port verdicts, then the lowest faulting slot of the chunk.
    reg [3:0]  port_fault;
    reg [3:0]  port_pend;
    reg        chunk_fault;
    reg [31:0] chunk_fault_event;
    reg        chunk_pending;
    integer k;
    always @* begin
        for (k = 0; k < 4; k = k + 1) begin
            port_pend[k] = port_valid[k] && port_in_range[k] && port_pending[k];
            port_fault[k] = port_valid[k] &&
                            (!port_in_range[k] ||
                             (!port_pending[k] && !port_signalled[k]) ||
                             (!port_pending[k] && port_signalled[k] &&
                              acquire_required && !port_published[k]));
        end
        chunk_fault = 1'b0;
        chunk_fault_event = ot_a3_pkg::A3_NO_ID;
        chunk_pending = |port_pend;
        for (k = 3; k >= 0; k = k - 1) begin
            if (port_fault[k]) begin
                chunk_fault = 1'b1;
                chunk_fault_event = port_event[k];
            end
        end
    end

    wire issue_in_range    = (issue_event_id < EVENTS);
    wire complete_in_range = (complete_event_id < EVENTS);
    wire control_in_range  = (control_signal_event_id < EVENTS);
    wire [EVENT_INDEX_W-1:0] issue_index    = issue_event_id[EVENT_INDEX_W-1:0];
    wire [EVENT_INDEX_W-1:0] complete_index = complete_event_id[EVENT_INDEX_W-1:0];
    wire [EVENT_INDEX_W-1:0] control_index  = control_signal_event_id[EVENT_INDEX_W-1:0];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pending <= {EVENTS{1'b0}};
            signalled <= {EVENTS{1'b0}};
            published <= {EVENTS{1'b0}};
            signal_error <= 1'b0;
            wait_busy <= 1'b0;
            wait_done <= 1'b0;
            wait_ok <= 1'b0;
            wait_trap_class <= ot_a3_pkg::A3_TRAP_NONE;
            wait_fault_event <= ot_a3_pkg::A3_NO_ID;
            wait_stalled <= 1'b0;
            producer_count <= 8'd0;
            chunk <= 2'd0;
            acquire_required <= 1'b0;
            payload_hold <= 512'b0;
            fault_seen <= 1'b0;
            fault_event <= ot_a3_pkg::A3_NO_ID;
            pending_seen <= 1'b0;
            signal_count <= 32'd0;
            wait_count <= 32'd0;
        end else begin
            wait_done <= 1'b0;
            if (clear) begin
                pending <= {EVENTS{1'b0}};
                signalled <= {EVENTS{1'b0}};
                published <= {EVENTS{1'b0}};
                signal_error <= 1'b0;
                wait_busy <= 1'b0;
                wait_stalled <= 1'b0;
                signal_count <= 32'd0;
                wait_count <= 32'd0;
            end else begin
                // -- completion of an engine producer and CONTROL retirement
                signal_count <= signal_count +
                                (complete_valid ? 32'd1 : 32'd0) +
                                (control_signal_valid ? 32'd1 : 32'd0);
                if (complete_valid) begin
                    if (!complete_in_range) begin
                        signal_error <= 1'b1;
                    end else begin
                        signalled[complete_index] <= 1'b1;
                        if (complete_release)
                            published[complete_index] <= 1'b1;
                        if (complete_last)
                            pending[complete_index] <= 1'b0;
                    end
                end
                if (control_signal_valid) begin
                    if (!control_in_range) begin
                        signal_error <= 1'b1;
                    end else begin
                        signalled[control_index] <= 1'b1;
                        if (control_signal_release)
                            published[control_index] <= 1'b1;
                    end
                end
                // -- issue: the event goes pending (set wins over a
                // -- same-cycle clear of the same event) --------------------
                if (issue_valid) begin
                    if (!issue_in_range)
                        signal_error <= 1'b1;
                    else
                        pending[issue_index] <= 1'b1;
                end

                // -- wait-set evaluation -----------------------------------
                if (wait_start) begin
                    wait_busy <= 1'b1;
                    wait_stalled <= 1'b0;
                    wait_count <= wait_count + 32'd1;
                    payload_hold <= wait_payload;
                    producer_count <= payload_producer_count;
                    acquire_required <= wait_acquire || ordering_acquire;
                    chunk <= 2'd0;
                    fault_seen <= 1'b0;
                    fault_event <= ot_a3_pkg::A3_NO_ID;
                    pending_seen <= 1'b0;
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
                    if (chunk != 2'd2) begin
                        if (chunk_fault && !fault_seen) begin
                            fault_seen <= 1'b1;
                            fault_event <= chunk_fault_event;
                        end
                        pending_seen <= pending_seen | chunk_pending;
                        chunk <= chunk + 2'd1;
                    end else begin
                        // Last chunk: decide with everything inspected.
                        if (fault_seen || chunk_fault) begin
                            wait_busy <= 1'b0;
                            wait_stalled <= 1'b0;
                            wait_done <= 1'b1;
                            wait_ok <= 1'b0;
                            wait_trap_class <= ot_a3_pkg::A3_TRAP_INTERNAL;
                            wait_fault_event <= fault_seen ? fault_event
                                                           : chunk_fault_event;
                        end else if (pending_seen || chunk_pending) begin
                            // Stall: rescan from the first producer.
                            wait_stalled <= 1'b1;
                            chunk <= 2'd0;
                            pending_seen <= 1'b0;
                        end else begin
                            wait_busy <= 1'b0;
                            wait_stalled <= 1'b0;
                            wait_done <= 1'b1;
                            wait_ok <= 1'b1;
                        end
                    end
                end
            end
        end
    end
endmodule
