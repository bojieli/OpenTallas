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
module ot_s81ph_link_gbx #(
    // CLAUDE s81-blocks 2026-10-07 (coll lane SS -456..-734: ic/tcnt -> bit-granular 1052-b shifts): FMT 1 = fixed
    // group format: 3 slots in every 4 gearbox beats at FIXED bit positions (slot j of a group: beat j bits
    // [140j, 456) + beat j+1 bits [0, 140(j+1)); beat 3 bits [420, 456) zero), marker on group beat 0 (MP 4).  No
    // shifter: every beat bit is a phase-selected wire.  Slot rate 3/4 per gearbox beat vs G/S = 0.765 (-2.0 %);
    // the caller paces the ep at FB * 3 * (IDLE_P - 1) / (4 * IDLE_P).  Needs S <= 140 + G and 3 S <= 4 G.
    parameter integer FMT = 0,
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
`ifndef SYNTHESIS
    initial if (G >= S || 3 + RFW + G != 512 || (FMT != 0 && (S > G + (S - G) || 3 * S > 4 * G || 3 * (S - G) > G)))
        $fatal(1, "ot_s81ph_link_gbx: geometry");
`endif
    generate if (FMT == 0) begin : g_f0
    localparam integer AB = G + S;             // accumulator bits
    localparam integer CB = $clog2(AB + 1);
    localparam integer PB = $clog2(S + 1);
    localparam integer IB = $clog2(IDLE_P + 1);
    localparam integer MB = $clog2(MP + 1);
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
    wire [S-1:0]   slot = take ? {sf[sh], 1'b1} : {S{1'b0}};
    wire [AB-1:0]  tacc_a = need ? (tacc | ({{G{1'b0}}, slot} << tcnt)) : tacc;
    wire [CB-1:0]  tcnt_a = need ? tcnt + S : tcnt;
    wire [PB:0]    tph_n = {1'b0, tph} + G;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sh <= 0; st <= 0; sn <= 0; tacc <= 0; tcnt <= 0; tph <= 0; ic <= 0; beat_tx <= 0; fault <= 1'b0;
        end else begin
            if (f_tx_v) begin sf[st] <= f_tx; st <= st + 1'b1; end
            sn <= sn + (f_tx_v ? 3'd1 : 3'd0) - (take ? 3'd1 : 3'd0);
            if (take) sh <= sh + 1'b1;
            if (f_tx_v && sn == 4 && !take) fault <= 1'b1;
            ic <= idle_now ? 0 : ic + 1'b1;
            if (idle_now) begin
                beat_tx <= {{G{1'b0}}, r_tx, r_tx_v, 1'b1, 1'b0};
            end else begin
                beat_tx <= {tacc_a[G-1:0], r_tx, r_tx_v, 1'b0, tph == 0};
                tacc <= tacc_a >> G;
                tcnt <= tcnt_a - G;
                tph <= (tph_n >= S) ? tph_n - S : tph_n[PB-1:0];
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
            bv <= 0; bm <= 0; bi <= 0; bg <= 0; racc <= 0; rcnt <= 0; hunt <= 0; mc <= 0; locked <= 0;
            f_rx_v <= 0; f_rx <= 0; r_rx_v <= 0; r_rx <= 0;
        end else begin
            bv <= beat_rx_v; bm <= beat_rx[0]; bi <= beat_rx[1]; bg <= beat_rx[511 -: G];
            r_rx_v <= beat_rx_v && beat_rx[2]; r_rx <= beat_rx[3 +: RFW];
            f_rx_v <= 1'b0;
            if (gb) begin
                mc <= (bm || due) ? 0 : mc + 1'b1;
                if (hunt != 2) begin
                    locked <= 1'b0;
                    if (bm) begin
                        if (hunt == 1 && due) begin       // second marker exactly MP beats on: lock, cut from here
                            hunt <= 2; locked <= 1'b1;
                            racc <= {{S{1'b0}}, bg}; rcnt <= G;
                        end else hunt <= 1;
                    end else if (hunt == 1 && due) hunt <= 0;
                end else if (bm != due) begin          // marker where none is due, or a missing one: re-hunt
                    hunt <= bm ? 1 : 0; locked <= 1'b0; racc <= 0; rcnt <= 0;
                end else begin
                    if (rcnt_a >= S) begin
                        f_rx_v <= racc_a[0];
                        f_rx <= racc_a[1 +: FFW];
                        racc <= racc_a >> S;
                        rcnt <= rcnt_a - S;
                    end else begin
                        racc <= racc_a; rcnt <= rcnt_a;
                    end
                end
            end
        end
    end
    end else begin : g_f1
    // ================================================================== FMT 1: fixed 3-in-4 group format
    localparam integer IB1 = $clog2(IDLE_P + 1);
    localparam integer K1 = S - G;                 // slot j tail bits in beat j+1: K1*(j+1) (140 at S 596 / G 456)
    // sender
    reg  [FFW-1:0] sf [0:3];
    reg  [1:0]     sh, st, ph;                     // ph: group phase of the next gearbox beat
    reg  [2:0]     sn;
    reg  [S-1:0]   rem;                            // the slot taken at the previous gearbox beat
    reg  [IB1-1:0] ic;
    reg            idle_q;                         // the next beat is an idle beat (registered compare)
    wire           need = !idle_q && (ph != 2'd3);
    wire           take = need && (sn != 0);
    wire [S-1:0]   slot = take ? {sf[sh], 1'b1} : {S{1'b0}};
    reg  [G-1:0]   gpay;
    always @(*) begin
        case (ph)
            2'd0: gpay = slot[G-1:0];
            2'd1: gpay = {slot[G-K1-1:0], rem[S-1 -: K1]};
            2'd2: gpay = {slot[G-2*K1-1:0], rem[S-1 -: 2*K1]};
            default: gpay = {{(G-3*K1){1'b0}}, rem[S-1 -: 3*K1]};
        endcase
    end
    // control flops reset; the payload (beat bits 3 and up, the slot FIFO, rem) is data: no reset (lane SS
    // -40..-171 ps was the reset tree into these wide registers)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sh <= 0; st <= 0; sn <= 0; ph <= 0; ic <= 0; idle_q <= (IDLE_P == 1); beat_tx[2:0] <= 3'd0; fault <= 1'b0;
        end else begin
            if (f_tx_v) st <= st + 1'b1;
            sn <= sn + (f_tx_v ? 3'd1 : 3'd0) - (take ? 3'd1 : 3'd0);
            if (take) sh <= sh + 1'b1;
            if (f_tx_v && sn == 4 && !take) fault <= 1'b1;
            ic <= idle_q ? 0 : ic + 1'b1;
            idle_q <= !idle_q && (ic == IDLE_P - 2);
            beat_tx[2:0] <= idle_q ? {r_tx_v, 1'b1, 1'b0} : {r_tx_v, 1'b0, ph == 2'd0};
            if (!idle_q) ph <= ph + 1'b1;
        end
    end
    always @(posedge clk) begin
        if (f_tx_v) sf[st] <= f_tx;
        beat_tx[511:3] <= idle_q ? {{G{1'b0}}, r_tx} : {gpay, r_tx};
        if (!idle_q && need) rem <= slot;
    end
    // receiver
    reg            bv, bm, bi;
    reg  [G-1:0]   bg;
    reg  [1:0]     hunt;
    reg  [1:0]     mc;                             // gearbox beats since the last marker beat, minus one
    reg  [G-1:0]   hold;                           // the open slot's head bits
    wire           gb = bv && !bi;
    wire           due = (mc == 2'd3);
    wire [1:0]     rph = due ? 2'd0 : mc + 1'b1;   // group phase of this beat while locked
    reg  [S-1:0]   cut;
    always @(*) begin
        case (rph)
            2'd1: cut = {bg[K1-1:0], hold};
            2'd2: cut = {bg[2*K1-1:0], hold[G-K1-1:0]};
            default: cut = {bg[3*K1-1:0], hold[G-2*K1-1:0]};
        endcase
    end
    always @(posedge clk) begin
        bg <= beat_rx[511 -: G]; r_rx <= beat_rx[3 +: RFW]; f_rx <= cut[1 +: FFW];
        if (gb && hunt == 2 && bm == due) begin
            case (rph)
                2'd0: hold <= bg;
                2'd1: hold <= {{K1{1'b0}}, bg[G-1:K1]};
                2'd2: hold <= {{(2*K1){1'b0}}, bg[G-1:2*K1]};
                default: hold <= hold;
            endcase
        end else if (gb && hunt != 2 && bm && hunt == 1 && due) hold <= bg;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bv <= 0; bm <= 0; bi <= 0; hunt <= 0; mc <= 0; locked <= 0; f_rx_v <= 0; r_rx_v <= 0;
        end else begin
            bv <= beat_rx_v; bm <= beat_rx[0]; bi <= beat_rx[1];
            r_rx_v <= beat_rx_v && beat_rx[2];
            f_rx_v <= 1'b0;
            if (gb) begin
                mc <= (bm || due) ? 2'd0 : mc + 1'b1;
                if (hunt != 2) begin
                    locked <= 1'b0;
                    if (bm) begin
                        if (hunt == 1 && due) begin       // second marker exactly 4 beats on: lock, group starts here
                            hunt <= 2; locked <= 1'b1;
                        end else hunt <= 1;
                    end else if (hunt == 1 && due) hunt <= 0;
                end else if (bm != due) begin          // marker where none is due, or a missing one: re-hunt
                    hunt <= bm ? 1 : 0; locked <= 1'b0;
                end else begin
                    if (rph != 2'd0) f_rx_v <= cut[0];
                end
            end
        end
    end
    end endgenerate
endmodule
