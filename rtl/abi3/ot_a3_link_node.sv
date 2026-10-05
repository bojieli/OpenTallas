`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 inter-chip endpoint: one mesh node.
//
// A node is the collective engine, the router that carries its flits, and the
// four credit/retry link channels that reach its neighbours.  Direction index
// is fixed everywhere in this fabric: 0 EAST (+x), 1 WEST (-x), 2 SOUTH (+y),
// 3 NORTH (-y).  The mesh wires node A's outgoing bundle to node B's incoming
// bundle; the return path (credit and NAK) runs the other way on the same link.
//
// The wire itself is outside this module: `ot_a3_link_wire` carries whatever
// number of cycles the instantiator declares a hop to occupy.  Nothing here,
// and nothing anywhere in this directory, establishes what that number is in
// seconds or in millimetres.
// ---------------------------------------------------------------------------
module ot_a3_link_node #(
    parameter integer FLIT_W      = 64,
    parameter integer MESH_X      = 4,
    parameter integer MESH_Y      = 4,
    parameter integer MY_X        = 0,
    parameter integer MY_Y        = 0,
    parameter integer VEC_LEN     = 16,
    parameter integer CREDITS     = 8,
    parameter integer RETRY_MAX   = 3,
    parameter integer ACK_TIMEOUT = 512
) (
    input  wire                  clk,
    input  wire                  rst_n,

    // -- engine command ------------------------------------------------------
    input  wire                  start,
    input  wire [7:0]            op,
    input  wire [1:0]            alg,
    input  wire [7:0]            reduction_order,
    input  wire [3:0]            root_x,
    input  wire [3:0]            root_y,
    output wire                  busy,
    output wire                  done,
    output wire                  trap,
    output wire [15:0]           trap_class,
    input  wire                  load_valid,
    input  wire [7:0]            load_index,
    input  wire [31:0]           load_data,
    input  wire [7:0]            read_index,
    output wire [31:0]           read_data,

    // -- outgoing wire bundles ----------------------------------------------
    output wire [3:0]            o_valid,
    output wire [4*FLIT_W-1:0]   o_flit,
    output wire [4*8-1:0]        o_seq,
    output wire [4*32-1:0]       o_crc,
    input  wire [3:0]            i_ack,
    input  wire [4*8-1:0]        i_ack_seq,
    input  wire [4*2-1:0]        i_credit,
    input  wire [3:0]            i_nak,
    input  wire [4*8-1:0]        i_nak_seq,

    // -- incoming wire bundles ----------------------------------------------
    input  wire [3:0]            i_valid,
    input  wire [4*FLIT_W-1:0]   i_flit,
    input  wire [4*8-1:0]        i_seq,
    input  wire [4*32-1:0]       i_crc,
    output wire [3:0]            o_ack,
    output wire [4*8-1:0]        o_ack_seq,
    output wire [4*2-1:0]        o_credit,
    output wire [3:0]            o_nak,
    output wire [4*8-1:0]        o_nak_seq,

    // -- fault injection, one bit per outgoing direction ---------------------
    input  wire [3:0]            inject_crc_error,

    // -- observation ---------------------------------------------------------
    output wire [31:0]           steps_taken,
    output wire [31:0]           engine_flits_sent,
    output wire [31:0]           engine_flits_received,
    output wire [31:0]           hop_distance_sent,
    output wire [31:0]           serial_traversals,
    output wire [31:0]           busy_cycles,
    output wire [31:0]           router_flits_forwarded,
    output wire [31:0]           router_flits_local,
    output reg  [31:0]           link_flits_transmitted,
    output reg  [31:0]           link_replayed_flits,
    output reg  [31:0]           link_retry_events,
    output reg  [31:0]           link_credit_stall_cycles,
    output reg  [31:0]           link_crc_errors,
    output reg  [31:0]           link_sequence_errors,
    output wire                  link_error,
    output wire                  router_misroute_error
);
    wire [4:0]          r_in_valid;
    wire [5*FLIT_W-1:0] r_in_flit;
    wire [4:0]          r_in_ready;
    wire [4:0]          r_out_valid;
    wire [5*FLIT_W-1:0] r_out_flit;
    wire [4:0]          r_out_ready;

    wire [31:0] tx_transmitted [0:3];
    wire [31:0] tx_replayed    [0:3];
    wire [31:0] tx_retries     [0:3];
    wire [31:0] tx_stalls      [0:3];
    wire [31:0] rx_crc_err     [0:3];
    wire [31:0] rx_seq_err     [0:3];
    wire [3:0]  tx_error;
    wire [3:0]  tx_ack_seq_error;
    wire [3:0]  tx_credit_overflow;
    wire [3:0]  rx_overrun;

    genvar d;
    generate
        for (d = 0; d < 4; d = d + 1) begin : GEN_DIR
            ot_a3_link_tx_channel #(
                .FLIT_W(FLIT_W), .CREDITS(CREDITS), .RETRY_MAX(RETRY_MAX),
                .ACK_TIMEOUT(ACK_TIMEOUT)
            ) u_tx (
                .clk(clk), .rst_n(rst_n),
                .in_valid(r_out_valid[d]),
                .in_ready(r_out_ready[d]),
                .in_flit(r_out_flit[d*FLIT_W +: FLIT_W]),
                .w_valid(o_valid[d]),
                .w_flit(o_flit[d*FLIT_W +: FLIT_W]),
                .w_seq(o_seq[d*8 +: 8]),
                .w_crc(o_crc[d*32 +: 32]),
                .r_ack(i_ack[d]),
                .r_ack_seq(i_ack_seq[d*8 +: 8]),
                .r_credit(i_credit[d*2 +: 2]),
                .r_nak(i_nak[d]),
                .r_nak_seq(i_nak_seq[d*8 +: 8]),
                .inject_crc_error(inject_crc_error[d]),
                .flits_accepted(),
                .flits_transmitted(tx_transmitted[d]),
                .replayed_flits(tx_replayed[d]),
                .retry_events(tx_retries[d]),
                .credit_stall_cycles(tx_stalls[d]),
                .retry_count(), .timeout(),
                .error(tx_error[d]),
                .ack_sequence_error(tx_ack_seq_error[d]),
                .credit_overflow_error(tx_credit_overflow[d])
            );

            ot_a3_link_rx_channel #(
                .FLIT_W(FLIT_W), .CREDITS(CREDITS)
            ) u_rx (
                .clk(clk), .rst_n(rst_n),
                .w_valid(i_valid[d]),
                .w_flit(i_flit[d*FLIT_W +: FLIT_W]),
                .w_seq(i_seq[d*8 +: 8]),
                .w_crc(i_crc[d*32 +: 32]),
                .r_ack(o_ack[d]),
                .r_ack_seq(o_ack_seq[d*8 +: 8]),
                .r_credit(o_credit[d*2 +: 2]),
                .r_nak(o_nak[d]),
                .r_nak_seq(o_nak_seq[d*8 +: 8]),
                .out_valid(r_in_valid[d]),
                .out_flit(r_in_flit[d*FLIT_W +: FLIT_W]),
                .out_ready(r_in_ready[d]),
                .crc_errors(rx_crc_err[d]),
                .sequence_errors(rx_seq_err[d]),
                .flits_delivered(),
                .overrun_error(rx_overrun[d]),
                .dropping()
            );
        end
    endgenerate

    // Any of these is an unrecoverable endpoint fault: replay exhausted, the
    // two ends disagreeing about the sequence, a receive buffer the credit
    // window failed to bound, or more credits returned than were issued.
    assign link_error = (|tx_error) | (|tx_ack_seq_error) |
                        (|tx_credit_overflow) | (|rx_overrun);

    integer c;
    always @* begin
        link_flits_transmitted = 32'd0;
        link_replayed_flits = 32'd0;
        link_retry_events = 32'd0;
        link_credit_stall_cycles = 32'd0;
        link_crc_errors = 32'd0;
        link_sequence_errors = 32'd0;
        for (c = 0; c < 4; c = c + 1) begin
            link_flits_transmitted = link_flits_transmitted + tx_transmitted[c];
            link_replayed_flits = link_replayed_flits + tx_replayed[c];
            link_retry_events = link_retry_events + tx_retries[c];
            link_credit_stall_cycles = link_credit_stall_cycles + tx_stalls[c];
            link_crc_errors = link_crc_errors + rx_crc_err[c];
            link_sequence_errors = link_sequence_errors + rx_seq_err[c];
        end
    end

    ot_a3_mesh_router #(
        .FLIT_W(FLIT_W), .MY_X(MY_X), .MY_Y(MY_Y)
    ) u_router (
        .clk(clk), .rst_n(rst_n),
        .in_valid(r_in_valid), .in_flit(r_in_flit), .in_ready(r_in_ready),
        .out_valid(r_out_valid), .out_flit(r_out_flit), .out_ready(r_out_ready),
        .flits_forwarded(router_flits_forwarded),
        .flits_delivered_local(router_flits_local),
        .misroute_error(router_misroute_error)
    );

    ot_a3_collective_engine #(
        .FLIT_W(FLIT_W), .MESH_X(MESH_X), .MESH_Y(MESH_Y),
        .MY_X(MY_X), .MY_Y(MY_Y), .VEC_LEN(VEC_LEN)
    ) u_engine (
        .clk(clk), .rst_n(rst_n),
        .start(start), .op(op), .alg(alg), .reduction_order(reduction_order),
        .root_x(root_x), .root_y(root_y),
        .busy(busy), .done(done), .trap(trap), .trap_class(trap_class),
        .load_valid(load_valid), .load_index(load_index), .load_data(load_data),
        .read_index(read_index), .read_data(read_data),
        .net_out_valid(r_in_valid[4]),
        .net_out_flit(r_in_flit[4*FLIT_W +: FLIT_W]),
        .net_out_ready(r_in_ready[4]),
        .net_in_valid(r_out_valid[4]),
        .net_in_flit(r_out_flit[4*FLIT_W +: FLIT_W]),
        .net_in_ready(r_out_ready[4]),
        .steps_taken(steps_taken),
        .flits_sent(engine_flits_sent),
        .flits_received(engine_flits_received),
        .hop_distance_sent(hop_distance_sent),
        .serial_traversals(serial_traversals),
        .busy_cycles(busy_cycles)
    );
endmodule


// The wire between two nodes.  `CYCLES` is the hop occupancy this model
// declares; it is a parameter, never a measurement.
module ot_a3_link_wire #(
    parameter integer FLIT_W = 64,
    parameter integer CYCLES = 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              in_valid,
    input  wire [FLIT_W-1:0] in_flit,
    input  wire [7:0]        in_seq,
    input  wire [31:0]       in_crc,
    output wire              out_valid,
    output wire [FLIT_W-1:0] out_flit,
    output wire [7:0]        out_seq,
    output wire [31:0]       out_crc
);
    generate
        if (CYCLES <= 0) begin : GEN_COMB
            assign out_valid = in_valid;
            assign out_flit = in_flit;
            assign out_seq = in_seq;
            assign out_crc = in_crc;
        end else begin : GEN_PIPE
            reg              v [0:CYCLES-1];
            reg [FLIT_W-1:0] f [0:CYCLES-1];
            reg [7:0]        s [0:CYCLES-1];
            reg [31:0]       c [0:CYCLES-1];
            integer i;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    for (i = 0; i < CYCLES; i = i + 1) begin
                        v[i] <= 1'b0;
                        f[i] <= {FLIT_W{1'b0}};
                        s[i] <= 8'd0;
                        c[i] <= 32'd0;
                    end
                end else begin
                    v[0] <= in_valid; f[0] <= in_flit; s[0] <= in_seq; c[0] <= in_crc;
                    for (i = 1; i < CYCLES; i = i + 1) begin
                        v[i] <= v[i-1]; f[i] <= f[i-1]; s[i] <= s[i-1]; c[i] <= c[i-1];
                    end
                end
            end
            assign out_valid = v[CYCLES-1];
            assign out_flit = f[CYCLES-1];
            assign out_seq = s[CYCLES-1];
            assign out_crc = c[CYCLES-1];
        end
    endgenerate
endmodule


// The return path of one link: credit and NAK, delayed by the same wire.
module ot_a3_link_return #(
    parameter integer CYCLES = 1
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       in_ack,
    input  wire [7:0] in_ack_seq,
    input  wire [1:0] in_credit,
    input  wire       in_nak,
    input  wire [7:0] in_nak_seq,
    output wire       out_ack,
    output wire [7:0] out_ack_seq,
    output wire [1:0] out_credit,
    output wire       out_nak,
    output wire [7:0] out_nak_seq
);
    generate
        if (CYCLES <= 0) begin : GEN_COMB
            assign out_ack = in_ack;
            assign out_ack_seq = in_ack_seq;
            assign out_credit = in_credit;
            assign out_nak = in_nak;
            assign out_nak_seq = in_nak_seq;
        end else begin : GEN_PIPE
            reg       ak [0:CYCLES-1];
            reg [7:0] as [0:CYCLES-1];
            reg [1:0] cr [0:CYCLES-1];
            reg       nk [0:CYCLES-1];
            reg [7:0] ns [0:CYCLES-1];
            integer i;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    for (i = 0; i < CYCLES; i = i + 1) begin
                        ak[i] <= 1'b0; as[i] <= 8'd0;
                        cr[i] <= 2'd0;
                        nk[i] <= 1'b0; ns[i] <= 8'd0;
                    end
                end else begin
                    ak[0] <= in_ack; as[0] <= in_ack_seq;
                    cr[0] <= in_credit;
                    nk[0] <= in_nak; ns[0] <= in_nak_seq;
                    for (i = 1; i < CYCLES; i = i + 1) begin
                        ak[i] <= ak[i-1]; as[i] <= as[i-1];
                        cr[i] <= cr[i-1];
                        nk[i] <= nk[i-1]; ns[i] <= ns[i-1];
                    end
                end
            end
            assign out_ack = ak[CYCLES-1];
            assign out_ack_seq = as[CYCLES-1];
            assign out_credit = cr[CYCLES-1];
            assign out_nak = nk[CYCLES-1];
            assign out_nak_seq = ns[CYCLES-1];
        end
    endgenerate
endmodule
