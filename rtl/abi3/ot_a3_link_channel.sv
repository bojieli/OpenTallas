`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 inter-chip link: one directed hop.
//
// This is the block the fairness audit says is missing.  The analytical model
// charges a collective `traversals x hop_latency`; nothing in this repository
// implemented the endpoint that a traversal actually crosses.  These modules
// do, at the level the ABI names: a bounded credit window
// (COMMUNICATION.credit_bound), CRC32C integrity (COMMUNICATION.integrity_mode
// = CRC32C), a monotone sequence, and bounded replay (COMMUNICATION.retry_bound
// and timeout_class).
//
// FLOW CONTROL AND ACKNOWLEDGEMENT ARE TWO MECHANISMS, NOT ONE.  This is the
// correction that matters and it was found by measurement, not by review: an
// earlier revision of this file returned one signal for both, on the reasoning
// that "a credit is the positive acknowledgement".  It passed every case at a
// one-cycle hop and produced WRONG ARITHMETIC at an eight-cycle hop under a
// single injected CRC error.  The cause is that a credit is returned when a
// flit DRAINS and an acknowledgement is owed when a flit is ACCEPTED, and those
// are different instants.  A go-back-N rewind to the oldest uncredited flit
// therefore replayed flits the receiver had already accepted, the receiver
// refused them as out of sequence, and the recovery re-ordered the payload.
// The three return signals below are separate for that reason:
//
//   ack    accepted into the receive buffer; frees one replay slot.
//   credit one receive-buffer slot is free again -- because the flit drained,
//          OR because it was rejected and never occupied a slot at all.
//   nak    a gap was detected; it CARRIES the sequence the receiver wants, so
//          the sender rewinds to the receiver's own position and never to a
//          stale local guess.
//
// WHAT THIS DOES NOT ESTABLISH.  `WIRE_CYCLES` is a parameter, not a
// measurement: it says how many cycles this model holds a flit on the wire, and
// it is set by whoever instantiates the block.  Nothing here establishes what a
// cycle is worth in seconds, how far one hop reaches in millimetres, or what a
// stitched or bonded reticle boundary costs.  Those stay in
// `configs/hardware/technology.json` `links.on_wafer`, derived and not measured.
// ---------------------------------------------------------------------------

module ot_a3_link_tx_channel #(
    parameter integer FLIT_W     = 64,
    parameter integer CREDITS    = 8,
    parameter integer RETRY_MAX  = 3,
    parameter integer ACK_TIMEOUT = 64
) (
    input  wire                  clk,
    input  wire                  rst_n,

    // service side
    input  wire                  in_valid,
    output wire                  in_ready,
    input  wire [FLIT_W-1:0]     in_flit,

    // wire side
    output reg                   w_valid,
    output reg  [FLIT_W-1:0]     w_flit,
    output reg  [7:0]            w_seq,
    output reg  [31:0]           w_crc,

    // return path
    input  wire                  r_ack,
    input  wire [7:0]            r_ack_seq,
    input  wire [1:0]            r_credit,
    input  wire                  r_nak,
    input  wire [7:0]            r_nak_seq,

    // Arms a single deliberate CRC corruption.  The pulse is latched and spent
    // on the NEXT flit this channel transmits, so a fault campaign injects
    // exactly one corruption per pulse whatever the traffic pattern is doing.
    input  wire                  inject_crc_error,

    // observation
    output reg  [31:0]           flits_accepted,
    output reg  [31:0]           flits_transmitted,
    output reg  [31:0]           replayed_flits,
    output reg  [31:0]           retry_events,
    output reg  [31:0]           credit_stall_cycles,
    output reg  [1:0]            retry_count,
    output reg                   timeout,
    output reg                   error,
    output reg                   ack_sequence_error,
    output reg                   credit_overflow_error
);
    localparam integer PTR_W = (CREDITS <= 1) ? 2 : ($clog2(CREDITS) + 1);
    localparam integer IDX_W = (CREDITS <= 1) ? 1 : $clog2(CREDITS);
    localparam integer SLOT_W = PTR_W + 1;
    localparam [PTR_W-1:0] CREDITS_P = CREDITS[PTR_W-1:0];
    localparam [SLOT_W-1:0] CREDITS_S = CREDITS[SLOT_W-1:0];

    reg [FLIT_W-1:0] replay [0:CREDITS-1];
    reg [PTR_W-1:0] wr_ptr;   // next free replay slot
    reg [PTR_W-1:0] sn_ptr;   // next slot to transmit
    reg [PTR_W-1:0] ak_ptr;   // oldest unacknowledged slot
    reg [SLOT_W-1:0] slots;   // receive-buffer slots this sender may still fill
    reg [31:0] ack_timer;
    reg        inject_armed;
    integer i;

    wire [PTR_W-1:0] occupancy = wr_ptr - ak_ptr;
    wire [PTR_W-1:0] pending   = wr_ptr - sn_ptr;
    wire window_full = (occupancy >= CREDITS_P);
    wire [IDX_W-1:0] wr_index = wr_ptr[IDX_W-1:0];
    wire [IDX_W-1:0] sn_index = sn_ptr[IDX_W-1:0];
    wire [31:0] send_crc =
        ot_crc_pkg::crc32c(FLIT_W, {{(4096-FLIT_W){1'b0}}, replay[sn_index]});

    assign in_ready = !window_full && !error;
    wire in_fire = in_valid && in_ready;
    wire send_fire = (pending != {PTR_W{1'b0}}) && (slots != {SLOT_W{1'b0}}) && !error;
    wire rewind = r_nak ||
                  (ACK_TIMEOUT != 0 && (occupancy != {PTR_W{1'b0}}) &&
                   (ack_timer >= ACK_TIMEOUT));

    reg [SLOT_W-1:0] slots_next;
    reg              credit_overflow;
    always @* begin
        credit_overflow = 1'b0;
        slots_next = slots + {{(SLOT_W-2){1'b0}}, r_credit};
        if (send_fire)
            slots_next = slots_next - 1'b1;
        if (slots_next > CREDITS_S) begin
            // Every transmitted flit returns exactly one credit -- on drain if
            // it was accepted, immediately if it was rejected -- so the count
            // cannot legally exceed the window.  The clamp keeps the counter
            // bounded; the flag beside it is what makes the clamp visible,
            // because a silent clamp is indistinguishable from a working link.
            slots_next = CREDITS_S;
            credit_overflow = 1'b1;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr <= 0;
            sn_ptr <= 0;
            ak_ptr <= 0;
            slots <= CREDITS_S;
            ack_timer <= 0;
            w_valid <= 1'b0;
            w_flit <= {FLIT_W{1'b0}};
            w_seq <= 8'd0;
            w_crc <= 32'd0;
            flits_accepted <= 32'd0;
            flits_transmitted <= 32'd0;
            replayed_flits <= 32'd0;
            retry_events <= 32'd0;
            credit_stall_cycles <= 32'd0;
            retry_count <= 2'd0;
            timeout <= 1'b0;
            error <= 1'b0;
            ack_sequence_error <= 1'b0;
            credit_overflow_error <= 1'b0;
            inject_armed <= 1'b0;
            for (i = 0; i < CREDITS; i = i + 1)
                replay[i] <= {FLIT_W{1'b0}};
        end else begin
            w_valid <= 1'b0;
            timeout <= 1'b0;
            slots <= slots_next;
            if (credit_overflow)
                credit_overflow_error <= 1'b1;
            if (inject_crc_error)
                inject_armed <= 1'b1;

            // A cycle in which this channel has something to send and cannot,
            // because the far end has no buffer slot, is what the cycle model
            // calls a credit stall.
            if ((pending != {PTR_W{1'b0}}) && (slots == {SLOT_W{1'b0}}) && !error)
                credit_stall_cycles <= credit_stall_cycles + 32'd1;

            if (in_fire) begin
                replay[wr_index] <= in_flit;
                wr_ptr <= wr_ptr + 1'b1;
                flits_accepted <= flits_accepted + 32'd1;
            end

            if (send_fire) begin
                w_valid <= 1'b1;
                w_flit <= replay[sn_index];
                w_seq <= {{(8-PTR_W){1'b0}}, sn_ptr};
                w_crc <= (inject_armed || inject_crc_error)
                         ? (send_crc ^ 32'h0000_0001) : send_crc;
                if (inject_armed)
                    inject_armed <= 1'b0;
                sn_ptr <= sn_ptr + 1'b1;
                flits_transmitted <= flits_transmitted + 32'd1;
            end

            // The acknowledgement frees a replay slot.  It is checked against
            // the sender's own position rather than trusted: the return path is
            // in order, so an acknowledgement that is not for the oldest
            // unacknowledged flit means the two ends disagree about the
            // sequence, which is a fault and not a recoverable event.
            if (r_ack) begin
                if (r_ack_seq[PTR_W-1:0] != ak_ptr)
                    ack_sequence_error <= 1'b1;
                ak_ptr <= r_ack_seq[PTR_W-1:0] + 1'b1;
                ack_timer <= 32'd0;
                retry_count <= 2'd0;
            end else if (occupancy != {PTR_W{1'b0}}) begin
                ack_timer <= ack_timer + 32'd1;
            end

            // Recovery.  The negative acknowledgement carries the receiver's
            // own expected sequence, so the sender resumes exactly where the
            // receiver stopped and can never replay an accepted flit.  The
            // timeout has no such information and falls back to the oldest
            // unacknowledged flit.
            if (rewind) begin
                if (!r_nak)
                    timeout <= 1'b1;
                ack_timer <= 32'd0;
                if (retry_count >= RETRY_MAX[1:0]) begin
                    error <= 1'b1;
                end else begin
                    retry_count <= retry_count + 2'd1;
                    retry_events <= retry_events + 32'd1;
                    if (r_nak) begin
                        replayed_flits <= replayed_flits +
                            {{(32-PTR_W){1'b0}}, (sn_ptr - r_nak_seq[PTR_W-1:0])};
                        sn_ptr <= r_nak_seq[PTR_W-1:0];
                        ak_ptr <= r_nak_seq[PTR_W-1:0];
                    end else begin
                        replayed_flits <= replayed_flits +
                            {{(32-PTR_W){1'b0}}, (sn_ptr - ak_ptr)};
                        sn_ptr <= ak_ptr;
                    end
                end
            end
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (CREDITS < 2 || CREDITS > 64)
            $error("ot_a3_link_tx_channel: credit_bound outside the modelled range");
        if (RETRY_MAX > 3)
            $error("ot_a3_link_tx_channel: retry_bound exceeds the 2-bit counter");
    end
`endif
endmodule


module ot_a3_link_rx_channel #(
    parameter integer FLIT_W  = 64,
    parameter integer CREDITS = 8
) (
    input  wire                  clk,
    input  wire                  rst_n,

    // wire side
    input  wire                  w_valid,
    input  wire [FLIT_W-1:0]     w_flit,
    input  wire [7:0]            w_seq,
    input  wire [31:0]           w_crc,

    // return path
    output reg                   r_ack,
    output reg  [7:0]            r_ack_seq,
    output reg  [1:0]            r_credit,
    output reg                   r_nak,
    output reg  [7:0]            r_nak_seq,

    // service side
    output wire                  out_valid,
    output wire [FLIT_W-1:0]     out_flit,
    input  wire                  out_ready,

    // observation
    output reg  [31:0]           crc_errors,
    output reg  [31:0]           sequence_errors,
    output reg  [31:0]           flits_delivered,
    output reg                   overrun_error,
    output reg                   dropping
);
    localparam integer PTR_W = (CREDITS <= 1) ? 2 : ($clog2(CREDITS) + 1);
    localparam integer IDX_W = (CREDITS <= 1) ? 1 : $clog2(CREDITS);
    localparam [PTR_W-1:0] CREDITS_P = CREDITS[PTR_W-1:0];

    reg [FLIT_W-1:0] fifo [0:CREDITS-1];
    reg [PTR_W-1:0] head;
    reg [PTR_W-1:0] tail;
    reg [PTR_W-1:0] expected;
    integer i;

    wire [PTR_W-1:0] level = tail - head;
    wire [IDX_W-1:0] head_index = head[IDX_W-1:0];
    wire [IDX_W-1:0] tail_index = tail[IDX_W-1:0];
    wire [31:0] check_crc =
        ot_crc_pkg::crc32c(FLIT_W, {{(4096-FLIT_W){1'b0}}, w_flit});
    wire crc_bad = (check_crc != w_crc);
    wire seq_bad = (w_seq[PTR_W-1:0] != expected);
    wire reject = w_valid && (crc_bad || seq_bad);
    wire accept = w_valid && !crc_bad && !seq_bad;

    assign out_valid = (level != {PTR_W{1'b0}});
    assign out_flit = fifo[head_index];
    wire pop = out_valid && out_ready;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            head <= 0;
            tail <= 0;
            expected <= 0;
            r_ack <= 1'b0;
            r_ack_seq <= 8'd0;
            r_credit <= 2'd0;
            r_nak <= 1'b0;
            r_nak_seq <= 8'd0;
            crc_errors <= 32'd0;
            sequence_errors <= 32'd0;
            flits_delivered <= 32'd0;
            overrun_error <= 1'b0;
            dropping <= 1'b0;
            for (i = 0; i < CREDITS; i = i + 1)
                fifo[i] <= {FLIT_W{1'b0}};
        end else begin
            r_ack <= 1'b0;
            r_nak <= 1'b0;
            // A rejected flit occupied no slot, so its slot is handed straight
            // back; a drained flit hands back the slot it did occupy.  Both can
            // happen in one cycle, which is why the credit return is a count.
            r_credit <= {1'b0, reject} + {1'b0, pop};

            if (reject) begin
                if (crc_bad)
                    crc_errors <= crc_errors + 32'd1;
                else
                    sequence_errors <= sequence_errors + 32'd1;
                // One negative acknowledgement per gap.  Naking every flit of a
                // go-back-N burst would rewind the sender once per dropped flit
                // and could not converge.
                if (!dropping) begin
                    r_nak <= 1'b1;
                    r_nak_seq <= {{(8-PTR_W){1'b0}}, expected};
                    dropping <= 1'b1;
                end
            end

            if (accept) begin
                fifo[tail_index] <= w_flit;
                tail <= tail + 1'b1;
                expected <= expected + 1'b1;
                dropping <= 1'b0;
                r_ack <= 1'b1;
                r_ack_seq <= w_seq;
                if (level >= CREDITS_P)
                    overrun_error <= 1'b1;
            end

            if (pop) begin
                head <= head + 1'b1;
                flits_delivered <= flits_delivered + 32'd1;
            end
        end
    end
endmodule
