`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Package-to-package link for the layer-per-package ROM pipeline.
//
// docs/ANALYTICAL_REPORT.md prices a hop between ROM packages at ~100 ns and
// 1.8 TB/s per direction (links.rom_board_serdes), with no software on the
// path.  This block is the digital part of that hop: a cut-through, credit
// flow-controlled pipe that forwards a message flit by flit as it arrives,
// never waiting for the whole message.  Its latency in cycles is
//
//     TX_STAGES + CHANNEL_CYCLES + RX_STAGES + 1 + (flits - 1)
//
// for a message of `flits` flits, with CHANNEL_CYCLES standing in for the
// SerDes, FEC and flight time an analog PHY adds.  The testbench measures the
// first-flit and last-flit latencies and checks ordering and back-pressure.
//
// NOT A PHY.  Serialisation, equalisation, FEC and lane deskew are the
// CHANNEL_CYCLES delay line; only the digital framing, credits and cut-through
// forwarding are real logic here.
// ---------------------------------------------------------------------------
module ot_rom_pkg_link #(
    parameter integer FLIT_BYTES     = 1800,   // 1.8 TB/s at 1 GHz
    parameter integer TX_STAGES      = 2,
    parameter integer CHANNEL_CYCLES = 60,     // PHY + FEC + flight stand-in
    parameter integer RX_STAGES      = 2,
    parameter integer CREDITS        = 128     // receiver buffer, in flits
) (
    input  wire                     clk,
    input  wire                     rst_n,
    // sender side
    input  wire                     in_valid,
    output wire                     in_ready,
    input  wire [FLIT_BYTES*8-1:0]  in_data,
    input  wire                     in_last,
    // receiver side
    output wire                     out_valid,
    input  wire                     out_ready,
    output wire [FLIT_BYTES*8-1:0]  out_data,
    output wire                     out_last,
    output reg  [31:0]              credit_stalls
);
    localparam integer W = FLIT_BYTES * 8;
    localparam integer DEPTH = TX_STAGES + CHANNEL_CYCLES + RX_STAGES;
    localparam integer CW = $clog2(CREDITS + 1);

    // Credits the sender holds; one is returned when the receiver buffer
    // drains a flit.  The return path is modelled as immediate, which is the
    // optimistic end: a real return crosses the channel too, so CREDITS must
    // cover the round trip for full rate (checked by the campaign).
    reg [CW-1:0] credits;
    wire send = in_valid && in_ready;
    assign in_ready = (credits != 0);

    // The pipe: TX framing, channel, RX deframing as one fixed delay.
    reg [W-1:0] pipe_data  [0:DEPTH-1];
    reg         pipe_valid [0:DEPTH-1];
    reg         pipe_last  [0:DEPTH-1];

    // Receiver buffer (FIFO) sized by CREDITS, read through a registered
    // output stage.  Routing at ASAP7 showed the FIFO's read mux driving the
    // output port as the critical path (919 MHz); registering the output is
    // the standard boundary rule and costs one cycle of latency.
    reg [W-1:0] fifo_data [0:CREDITS-1];
    reg         fifo_last [0:CREDITS-1];
    reg [CW-1:0] head, tail, fill;
    reg          out_valid_r, out_last_r;
    reg [W-1:0]  out_data_r;
    assign out_valid = out_valid_r;
    assign out_data  = out_data_r;
    assign out_last  = out_last_r;
    // Pop the FIFO into the output register whenever it is empty or draining.
    wire drain = (fill != 0) && (!out_valid_r || out_ready);
    wire arrive = pipe_valid[DEPTH-1];

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            credits <= CREDITS; head <= 0; tail <= 0; fill <= 0; credit_stalls <= 0;
            out_valid_r <= 1'b0; out_last_r <= 1'b0; out_data_r <= 0;
            for (i = 0; i < DEPTH; i = i + 1) pipe_valid[i] <= 1'b0;
        end else begin
            pipe_valid[0] <= send;
            pipe_data[0]  <= in_data;
            pipe_last[0]  <= in_last;
            for (i = 1; i < DEPTH; i = i + 1) begin
                pipe_valid[i] <= pipe_valid[i-1];
                pipe_data[i]  <= pipe_data[i-1];
                pipe_last[i]  <= pipe_last[i-1];
            end
            if (arrive) begin
                fifo_data[tail] <= pipe_data[DEPTH-1];
                fifo_last[tail] <= pipe_last[DEPTH-1];
                tail <= (tail + 1 == CREDITS) ? 0 : tail + 1;
            end
            if (drain) begin
                head <= (head + 1 == CREDITS) ? 0 : head + 1;
                out_data_r  <= fifo_data[head];
                out_last_r  <= fifo_last[head];
                out_valid_r <= 1'b1;
            end else if (out_valid_r && out_ready) begin
                out_valid_r <= 1'b0;
            end
            fill <= fill + (arrive ? 1 : 0) - (drain ? 1 : 0);
            credits <= credits - (send ? 1 : 0) + (drain ? 1 : 0);
            if (in_valid && !in_ready) credit_stalls <= credit_stalls + 1;
        end
    end
endmodule
