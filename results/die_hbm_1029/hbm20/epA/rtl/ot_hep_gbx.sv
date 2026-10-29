`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// hfd_ep_static (H-LKEP 2026-10-15): the v15 HBM die link endpoint master -- ONE master for all nine ep_N0..N3 /
// ep_S0..S4 windows (434.72 x 515.2 um, compact660_v5), successor of the retired v14 hfd_lk_ep (2600 x 830 um,
// credit/NAK retry with three replay SRAM pipelines, 13 failed flat routes; its COLL-side credits are an on-die
// flow-control edge that 0az forbids).
//
// Owner rules: on-die static (fixed calendars, no ready/credit toward COLL); flow control only at the off-die boundary,
// which this block IS (the SerDes macro's rate matcher inserts / deletes IDLE beats; the elastic RX blocks admit whole
// finite blocks before COLL drains them on fixed slots); every input and output registered at its pin.
// Reliability (sequence, CRC-32, 64-deep replay, epoch abort) stays in COLL's ot_hgi_coll_static_link_capture; this
// block owns the lane format and the off-die RX boundary only.
//
// Lane format (512-b SerDes beat, ot_pdie_serdes tx/rx):
//   [0] marker (group beat 0)   [1] IDLE (no gearbox bits; ot_pdie_serdes' rate matcher drops / inserts these)
//   [511:2] 510 gearbox bits.  A group = 5 data beats = 2,550 bits carrying 4 slots of S = 613 bits
//   {frame[611:0], v} back to back at FIXED positions (slot j = group bits [613j, 613j+613), bits [2452,2550) zero):
//   every beat bit is a phase-selected wire, no shifter.  TX inserts one IDLE beat after every IDLE_K groups.
//   Slot calendar (compiler obligation, static): counting data beats from the first beat after reset release, beat
//   phase p = 0..4 within the group; a TX frame presented at the tx pin is sampled one edge later and must land on a
//   beat with p < 4 (4 slots per 5 beats, 816 slots per 1,021 beats at IDLE_K = 204: 0.799 frame/beat vs 0.749 for
//   the retired NS3 endpoint); a frame on p = 4 or an IDLE beat is a calendar fault (sticky, never rescheduled).
//   RX: hunt two markers exactly 5 data beats apart -> locked; a marker out of place drops lock (sticky fault).
// RX boundary: ot_hep_rx_pingpong (ot_hep_rx_store.sv: H-COLL's off-die RX pingpong contract, two 64-frame blocks, real
// SRAM leaves, every wide select replicated per 64-b slice -- route-1 hold fix).  A frame arriving while
// the armed block is not ready cannot wait (the SerDes never stalls): sticky fault (the compiler arms in time).
//
// Latencies: tx pin -> SerDes tx pin: 2 edges (pin reg, beat reg).  SerDes rx pin -> pingpong phy input: 3 edges
// (pin reg, beat/data-copy reg, slot-cut reg; route 4: +1 so sd_rx[1] has one pin flop).  COLL control pins: +1 edge (pin reg) before the pingpong; block_ready / fault / phy_up
// leave through output registers (+1).  Pingpong: slot S -> rx_pin S+4 (its own contract) + 1 input pin edge.
// MUT (bench only): 1 TX slot-2 tail offset off by one bit, 2 RX does not skip IDLE beats, 3 RX swaps the prev/cur
// part of slot 1, 4 pingpong slot-bank mutant (H-COLL MUT 2).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hep_tx_gbx #(parameter integer IDLE_K = 204, parameter integer MUT = 0) (
    input  wire         clk,
    input  wire         rst_n,          // synchronised
    input  wire         tx_v,           // pin registers (driven from hfd_ep_static pin flops)
    input  wire [611:0] tx_frame,
    output reg  [511:0] beat,           // registered: the SerDes tx pins
    output reg          cal_fault
);
    // Physical structure (gate 1015 pre-route: reg->reg +34 ps through the phase/idle decode fanning out to 613 + 510
    // flops): the beat's phase one-hot and the slot-take bit are REGISTERS computed from the next state one edge early,
    // replicated per 64-b slice (keep), so no decode or compare sits in front of a data flop.  prv loads every edge
    // (it is only read at phases 1..4, which follow a take), so it has no enable.
    localparam integer GB = 13, SL = 64, NSL = (613 + SL - 1) / SL;
    reg [2:0]  ph;
    reg [GB-1:0] gc;                    // group counter within the IDLE period
    wire idle_n_now = (gc == IDLE_K[GB-1:0]);
    // next state (what the following edge sees)
    wire [2:0]  ph_n = idle_n_now ? ph : (ph == 3'd4 ? 3'd0 : ph + 3'd1);
    wire [GB-1:0] gc_n = idle_n_now ? {GB{1'b0}} : (ph == 3'd4 ? gc + 1'b1 : gc);
    wire idle_n = (gc_n == IDLE_K[GB-1:0]);
    (* keep *) reg [NSL*5-1:0] oh;      // per-slice phase one-hot of THIS edge's beat
    (* keep *) reg [NSL-1:0]   tk;      // per-slice: this edge's beat takes a slot (phase < 4, not IDLE)
    (* keep *) reg [7:0] idr;           // per-64-b-slice copies of idle (the beat register selects, <= 64 loads each)
    reg [612:0] prv;
    reg [612:0] cur;
    reg [509:0] g;
    integer s, j, k;
    wire [511:0] bnext = {g, 1'b0, oh[0]};
    always @(*) begin
        for (s = 0; s < NSL; s = s + 1)
            for (j = s * SL; j < (s + 1) * SL && j < 613; j = j + 1)
                cur[j] = tk[s] & (j == 0 ? tx_v : tx_frame[j - 1]);
        for (j = 0; j < 510; j = j + 1) begin
            // slice of the beat bit j (the bit's select copy)
            s = j / SL;
            g[j] = (oh[s*5+0] & cur[j])
                 | (oh[s*5+1] & (j < 103 ? prv[510 + j] : cur[j - 103]))
                 | (oh[s*5+2] & (j < 206 ? ((MUT == 1) ? prv[406 + j] : prv[407 + j]) : cur[j - 206]))
                 | (oh[s*5+3] & (j < 309 ? prv[304 + j] : cur[j - 309]))
                 | (oh[s*5+4] & (j < 412 ? prv[201 + j] : 1'b0));
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            ph <= 3'd0; gc <= {GB{1'b0}}; beat <= 512'd2; cal_fault <= 1'b0;
            oh <= {NSL{5'b00001}}; tk <= {NSL{1'b1}}; idr <= 8'd0;
        end else begin
            ph <= ph_n; gc <= gc_n;
            oh <= {NSL{(idle_n ? 5'b00000 : 5'b00001 << ph_n)}};
            tk <= {NSL{!idle_n && ph_n != 3'd4}};
            idr <= {8{idle_n}};
            for (k = 0; k < 512; k = k + 1) beat[k] <= idr[k / 64] ? (k == 1) : bnext[k];
            if (tx_v && !tk[0]) cal_fault <= 1'b1;
        end
    always @(posedge clk) prv <= cur;
endmodule

module ot_hep_rx_gbx #(parameter integer MUT = 0) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [511:0] beat,           // pin register (from hfd_ep_static)
    input  wire [7:0]   data_r,         // replicated pin-register copies of !beat[1] (one per 64-b slice of pg)
    output reg          f_v,            // registered
    output reg  [611:0] f_d,
    output reg          locked,
    output reg          lock_lost       // sticky: lock dropped after it was acquired
);
    // Physical structure: the slot select is a per-slice replicated one-hot phase register (keep); pg loads under a
    // replicated copy of the pin register's data bit; f_d loads every edge (f_v qualifies it), so no enable net.
    localparam integer SL = 64, NSL = (613 + SL - 1) / SL;
    wire data = (MUT == 2) ? 1'b1 : !beat[1];
    wire mk = beat[0];
    wire [509:0] gcur = beat[511:2];
    reg [509:0] pg;
    reg [2:0] ph, cnt;
    reg seen;
    (* keep *) reg [NSL*4-1:0] oh;      // per slice: phase 1..4 one-hot (phase 0 = all zero)
    reg [612:0] slot;
    reg [2:0] ph_n; reg lk_n;
    integer s, j, k;
    always @(*) begin
        for (j = 0; j < 613; j = j + 1) begin
            s = j / SL;
            slot[j] = (oh[s*4+0] & ((MUT == 3) ? (j < 103 ? pg[j] : gcur[j - 103]) : (j < 510 ? pg[j] : gcur[j - 510])))
                    | (oh[s*4+1] & (j < 407 ? pg[103 + j] : gcur[j - 407]))
                    | (oh[s*4+2] & (j < 304 ? pg[206 + j] : gcur[j - 304]))
                    | (oh[s*4+3] & (j < 201 ? pg[309 + j] : gcur[j - 201]));
        end
    end
    // next lock state / phase (control only)
    always @(*) begin
        ph_n = ph; lk_n = locked;
        if (data) begin
            if (!locked) begin
                if (mk && seen && cnt == 3'd4) begin lk_n = 1'b1; ph_n = 3'd1; end
            end else if ((ph == 3'd0) != mk) begin
                lk_n = 1'b0; ph_n = 3'd0;
            end else ph_n = (ph == 3'd4) ? 3'd0 : ph + 3'd1;
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            locked <= 1'b0; lock_lost <= 1'b0; ph <= 3'd0; cnt <= 3'd0; seen <= 1'b0; f_v <= 1'b0; oh <= {(NSL*4){1'b0}};
        end else begin
            f_v <= data && locked && ((ph == 3'd0) == mk) && ph != 3'd0 && slot[0];
            ph <= ph_n; locked <= lk_n;
            oh <= {NSL{(lk_n && ph_n != 3'd0) ? (4'b0001 << (ph_n - 3'd1)) : 4'b0000}};
            if (data) begin
                if (!locked) begin
                    if (mk) begin seen <= 1'b1; cnt <= 3'd0; end
                    else if (cnt != 3'd7) cnt <= cnt + 3'd1;
                end else if ((ph == 3'd0) != mk) begin
                    lock_lost <= 1'b1; seen <= mk; cnt <= 3'd0;
                end
            end
        end
    always @(posedge clk) begin
        for (k = 0; k < 510; k = k + 1) if ((MUT == 2) ? 1'b1 : data_r[k / SL]) pg[k] <= gcur[k];
        f_d <= slot[612:1];
    end
endmodule

`default_nettype wire
