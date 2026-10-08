// Candidate registered-head successor. Original module remains immutable.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81ph_link_gbx (CLAUDE S81-PH collective, 2026-10-06): the beat format of one S81 die link lane.
// The link macro (ot_pdie_serdes / ot_pdie_ucie: FEC, SerDes, clock recovery, rate matching = hard IP) moves one
// 512-b beat a die cycle each way.  One beat carries:
//     [0]            marker: a forward slot starts at gearbox bit 0 of this beat (alignment)
//     [1]            idle: no gearbox bits (the sender inserts one every IDLE_P beats so the PHY can absorb the
//                    clock offset of two dies by deleting it; the receiver skips it)
//     [2]            reverse frame valid
//     [3 +: RFW]     one reverse frame of ot_s81ph_link_ep (ACK / NAK / credit), carried whole in every beat
//     [3+RFW +: G]   G = 509 - RFW bits of the forward slot stream: slots {v, frame} of S = FFW + 1 bits back to
//                    back (v = 0: an empty slot), cut into G-bit chunks.
// The sender's ot_s81ph_link_ep is paced to the slot rate (PHY_NUM / PHY_DEN = FLIT_BYTES * G * (IDLE_P - 1) /
// (S * IDLE_P)), so the 4-entry slot FIFO never fills (overflow -> sticky fault).
// Receiver: hunts for two marker beats exactly MP = S / gcd(G, S) gearbox beats apart, then cuts slots; a marker
// where none is due (or a missing one) drops lock and re-hunts (frames cut while misaligned fail the link CRC).
// ---------------------------------------------------------------------------
module ot_s81ph_link_gbx_reset #(
    parameter integer TRIM_RX_RESET = 0,
    parameter integer PIPE_TX = 0,
    parameter integer HEAD_REG = PIPE_TX,
    parameter integer FFW = 595,
    parameter integer RFW = 53,
    parameter integer IDLE_P = 1024,
    parameter integer G = 509 - RFW,
    parameter integer S = FFW + 1,
    parameter integer MP = 149                 // S / gcd(G, S)
) (
    input  wire            clk,
    input  wire            rst_n,
    // sender (from the local ep)
    input  wire            f_tx_v,
    input  wire [FFW-1:0]  f_tx,
    input  wire            r_tx_v,
    input  wire [RFW-1:0]  r_tx,
    output reg  [511:0]    beat_tx,           // registered
    // receiver (to the local ep)
    input  wire            beat_rx_v,         // lane valid (meso r_v && peer live)
    input  wire [511:0]    beat_rx,
    output reg             f_rx_v,
    output reg  [FFW-1:0]  f_rx,
    output reg             r_rx_v,
    output reg  [RFW-1:0]  r_rx,
    output reg             locked,
    output reg             fault               // sticky: slot FIFO overflow
);
    localparam integer AB = G + S;             // accumulator bits
    localparam integer CB = $clog2(AB + 1);
    localparam integer PB = $clog2(S + 1);
    localparam integer IB = $clog2(IDLE_P + 1);
    localparam integer MB = $clog2(MP + 1);
`ifndef SYNTHESIS
    initial if (G >= S || 3 + RFW + G != 512) $fatal(1, "ot_s81ph_link_gbx: geometry");
`endif
    // ------------------------------------------------------------------ sender
    reg  [FFW-1:0] sf [0:3];
    reg  [1:0]     sh, st;
    reg  [2:0]     sn;
    reg  [AB-1:0]  tacc;
    reg  [CB-1:0]  tcnt;
    reg  [PB-1:0]  tph;                         // stream bit position of this beat's gearbox bit 0, mod S
    reg  [IB-1:0]  ic;
    wire           idle_now = (ic == IDLE_P - 1);
    wire           need = !idle_now && (tcnt < G);
    wire           take = need && (sn != 0);
    // Mirror sf[sh] across queue updates. The bypass matches nonblocking
    // write/read semantics when the next head is written on this edge.
    // No queue capacity or beat latency is added. Payload needs no reset:
    // a valid head always derives from an actual enqueue before use.
    reg [FFW-1:0] head;
    wire [1:0] next_sh = sh + 2'd1;
    generate if (HEAD_REG != 0) begin : g_head
        always @(posedge clk) begin
            if (rst_n) begin
                if (take)
                    head <= (f_tx_v && st == next_sh) ? f_tx : sf[next_sh];
                else if (f_tx_v && st == sh)
                    head <= f_tx;
            end
        end
    end endgenerate
    wire [FFW-1:0] selected_frame = HEAD_REG != 0 ? head : sf[sh];
    wire [S-1:0]   slot = take ? {selected_frame, 1'b1} : {S{1'b0}};
    wire [AB-1:0]  tacc_a = need ? (tacc | ({{G{1'b0}}, slot} << tcnt)) : tacc;
    wire [CB-1:0]  tcnt_a = need ? tcnt + S : tcnt;
    wire [PB:0]    tph_n = {1'b0, tph} + G;
    reg [AB-1:0] ins_lo, ins_hi;
    reg [CB-5:0] ins_upper;
    reg [RFW+2:0] meta1, meta2; // {reverse data, reverse valid, idle, marker}
    reg valid1, valid2;
    wire [AB-1:0] merged = tacc | ins_hi;
    generate if (PIPE_TX != 0) begin : g_partition
        always @(posedge clk) begin
            ins_lo <= need ? ({{G{1'b0}}, slot} << tcnt[3:0]) : {AB{1'b0}};
            ins_upper <= tcnt[CB-1:4];
            ins_hi <= ins_lo << {ins_upper, 4'b0000};
            meta1 <= {r_tx, r_tx_v, idle_now, !idle_now && tph == 0};
            meta2 <= meta1;
        end
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid1 <= 0; valid2 <= 0;
            sh <= 0; st <= 0; sn <= 0; tacc <= 0; tcnt <= 0; tph <= 0; ic <= 0; beat_tx <= 0; fault <= 1'b0;
        end else begin
            if (f_tx_v) begin sf[st] <= f_tx; st <= st + 1'b1; end
            sn <= sn + (f_tx_v ? 3'd1 : 3'd0) - (take ? 3'd1 : 3'd0);
            if (take) sh <= sh + 1'b1;
            if (f_tx_v && sn == 4 && !take) fault <= 1'b1;
            ic <= idle_now ? 0 : ic + 1'b1;
            if (!idle_now) begin
                tcnt <= tcnt_a - G;
                tph <= (tph_n >= S) ? tph_n - S : tph_n[PB-1:0];
            end
            if (PIPE_TX == 0) begin
                if (idle_now) beat_tx <= {{G{1'b0}}, r_tx, r_tx_v, 1'b1, 1'b0};
                else begin
                    beat_tx <= {tacc_a[G-1:0], r_tx, r_tx_v, 1'b0, tph == 0};
                    tacc <= tacc_a >> G;
                end
            end else begin
                valid1 <= 1'b1; valid2 <= valid1;
                if (!valid2) beat_tx <= 0;
                else if (meta2[1]) beat_tx <= {{G{1'b0}}, meta2};
                else begin
                    beat_tx <= {merged[G-1:0], meta2};
                    tacc <= merged >> G;
                end
            end
        end
    end
    // ------------------------------------------------------------------ receiver
    // input beat registered at the pin (by the caller); here: one more register stage, then cut
    reg            bv, bm, bi;
    reg  [G-1:0]   bg;
    reg  [AB-1:0]  racc;
    reg  [CB-1:0]  rcnt;
    reg  [1:0]     hunt;                        // 0: no marker seen, 1: one marker seen (counting), 2: locked
    reg  [MB-1:0]  mc;                          // gearbox beats since the last marker
    wire           gb = bv && !bi;              // a beat that carries gearbox bits
    wire           due = (mc == MP - 1);
    wire [AB-1:0]  racc_a = racc | ({{S{1'b0}}, bg} << rcnt);
    wire [CB-1:0]  rcnt_a = rcnt + G;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bv <= 0; bm <= 0; bi <= 0; rcnt <= 0; hunt <= 0; mc <= 0; locked <= 0;
            f_rx_v <= 0; f_rx <= 0; r_rx_v <= 0; r_rx <= 0;
        end else begin
            bv <= beat_rx_v; bm <= beat_rx[0]; bi <= beat_rx[1];
            r_rx_v <= beat_rx_v && beat_rx[2]; r_rx <= beat_rx[3 +: RFW];
            f_rx_v <= 1'b0;
            if (gb) begin
                mc <= (bm || due) ? 0 : mc + 1'b1;
                if (hunt != 2) begin
                    locked <= 1'b0;
                    if (bm) begin
                        if (hunt == 1 && due) begin       // second marker exactly MP beats on: lock, cut from here
                            hunt <= 2; locked <= 1'b1;
                            rcnt <= G;
                        end else hunt <= 1;
                    end else if (hunt == 1 && due) hunt <= 0;
                end else if (bm != due) begin          // marker where none is due, or a missing one: re-hunt
                    hunt <= bm ? 1 : 0; locked <= 1'b0; racc <= 0; rcnt <= 0;
                end else begin
                    if (rcnt_a >= S) begin
                        f_rx_v <= racc_a[0];
                        f_rx <= racc_a[1 +: FFW];
                        rcnt <= rcnt_a - S;
                    end else begin
                        rcnt <= rcnt_a;
                    end
                end
            end
        end
    end
    // bg is consumed only after bv; racc is initialized on every lock acquisition.
    // Retain all control/visible-output resets and alignment-loss initialization.
    wire payload_rst_n = TRIM_RX_RESET != 0 ? 1'b1 : rst_n;
    always @(posedge clk or negedge payload_rst_n) begin
        if (!payload_rst_n) begin bg <= 0; racc <= 0; end
        else if (rst_n) begin
            bg <= beat_rx[511 -: G];
            if (gb) begin
                if (hunt != 2) begin
                    if (bm && hunt == 1 && due) racc <= {{S{1'b0}}, bg};
                end else if (bm != due) racc <= 0;
                else if (rcnt_a >= S) racc <= racc_a >> S;
                else racc <= racc_a;
            end
        end
    end
endmodule
