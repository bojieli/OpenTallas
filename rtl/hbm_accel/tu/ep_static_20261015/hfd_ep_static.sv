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
// RX boundary: H-COLL ot_hgi_coll_offdie_rx_pingpong (two 64-frame blocks, real SRAM leaves).  A frame arriving while
// the armed block is not ready cannot wait (the SerDes never stalls): sticky fault (the compiler arms in time).
//
// Latencies: tx pin -> SerDes tx pin: 2 edges (pin reg, beat reg).  SerDes rx pin -> pingpong phy input: 2 edges
// (pin reg, slot-cut reg).  COLL control pins: +1 edge (pin reg) before the pingpong; block_ready / fault / phy_up
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
    reg idle;                           // master copies for control
    reg [612:0] prv;
    reg [612:0] cur;
    reg [509:0] g;
    integer s, j;
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
            ph <= 3'd0; gc <= {GB{1'b0}}; beat <= 512'd2; cal_fault <= 1'b0; idle <= 1'b0;
            oh <= {NSL{5'b00001}}; tk <= {NSL{1'b1}};
        end else begin
            ph <= ph_n; gc <= gc_n;
            idle <= idle_n;
            oh <= {NSL{(idle_n ? 5'b00000 : 5'b00001 << ph_n)}};
            tk <= {NSL{!idle_n && ph_n != 3'd4}};
            beat <= idle ? 512'd2 : {g, 1'b0, oh[0]};
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
    integer s, j;
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
        for (j = 0; j < 510; j = j + 1) if ((MUT == 2) ? 1'b1 : data_r[j / SL]) pg[j] <= gcur[j];
        f_d <= slot[612:1];
    end
endmodule

module hfd_ep_static #(parameter integer IDLE_K = 204, parameter integer MUT = 0) (
    input  wire         clk,            // link clock (= the SerDes macro ck), one root
    input  wire         rst_n,
    // COLL face (static calendars)
    input  wire         tx_v,
    input  wire [611:0] tx_frame,
    input  wire         rx_arm_v,
    input  wire         rx_arm_bank,
    input  wire [6:0]   rx_block_words,
    input  wire         rx_release_v,
    input  wire         rx_release_bank,
    input  wire         rx_slot_v,
    input  wire         rx_slot_bank,
    input  wire [5:0]   rx_slot_index,
    output wire         rx_pin_v,
    output wire [611:0] rx_pin_flit,
    output reg  [1:0]   rx_block_ready,
    output reg          phy_up,
    output reg          fault,
    output reg  [10:0]  fault_cause,
    // SerDes face (ot_pdie_serdes tx / rx / st)
    output wire [511:0] sd_tx,
    input  wire [511:0] sd_rx,
    input  wire [1:0]   sd_st
);
    // reset: 2-flop synchroniser, then one replicated copy per region
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    (* keep *) reg rn_tx, rn_rx, rn_bd, rn_o;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rn_tx <= 1'b0; rn_rx <= 1'b0; rn_bd <= 1'b0; rn_o <= 1'b0; end
        else begin rn_tx <= rs[1]; rn_rx <= rs[1]; rn_bd <= rs[1]; rn_o <= rs[1]; end
    // input pin registers (every input)
    reg p_tx_v; reg [611:0] p_tx_f;
    reg p_arm_v, p_arm_b, p_rel_v, p_rel_b, p_slot_v, p_slot_b;
    reg [6:0] p_words; reg [5:0] p_slot_i;
    reg [511:0] p_rx; reg [1:0] p_st; (* keep *) reg [7:0] p_rxd;
    always @(posedge clk) begin
        p_tx_v <= tx_v; p_tx_f <= tx_frame;
        p_arm_v <= rx_arm_v; p_arm_b <= rx_arm_bank; p_words <= rx_block_words;
        p_rel_v <= rx_release_v; p_rel_b <= rx_release_bank;
        p_slot_v <= rx_slot_v; p_slot_b <= rx_slot_bank; p_slot_i <= rx_slot_index;
        p_rx <= sd_rx; p_st <= sd_st; p_rxd <= {8{!sd_rx[1]}};
    end
    wire cal_fault;
    ot_hep_tx_gbx #(.IDLE_K(IDLE_K), .MUT(MUT == 1 ? 1 : 0)) u_tx (.clk(clk), .rst_n(rn_tx), .tx_v(p_tx_v),
        .tx_frame(p_tx_f), .beat(sd_tx), .cal_fault(cal_fault));
    wire f_v, locked, lock_lost; wire [611:0] f_d;
    ot_hep_rx_gbx #(.MUT((MUT == 2 || MUT == 3) ? MUT : 0)) u_rx (.clk(clk), .rst_n(rn_rx), .beat(p_rx), .data_r(p_rxd),
        .f_v(f_v), .f_d(f_d), .locked(locked), .lock_lost(lock_lost));
    wire phy_ready, bd_fault; wire [1:0] bready; wire [6:0] bd_cause;
    ot_hgi_coll_offdie_rx_pingpong #(.MUT(MUT == 4 ? 2 : 0)) u_rxb (.clk(clk), .rst_n(rn_bd),
        .arm_v(p_arm_v), .arm_bank(p_arm_b), .block_words(p_words),
        .phy_v(f_v), .phy_flit(f_d), .phy_ready(phy_ready), .block_ready(bready),
        .release_v(p_rel_v), .release_bank(p_rel_b),
        .slot_v(p_slot_v), .slot_bank(p_slot_b), .slot_index(p_slot_i),
        .pin_v(rx_pin_v), .pin_flit(rx_pin_flit), .fault(bd_fault), .fault_cause(bd_cause));
    // off-die boundary: an arriving frame cannot wait (the SerDes never stalls)
    reg early;
    always @(posedge clk or negedge rn_o)
        if (!rn_o) begin
            early <= 1'b0; rx_block_ready <= 2'b00; phy_up <= 1'b0; fault <= 1'b0; fault_cause <= 11'd0;
        end else begin
            if (f_v && !phy_ready) early <= 1'b1;
            rx_block_ready <= bready;
            phy_up <= p_st[1] && locked;
            fault_cause <= {p_st[0], cal_fault, early, lock_lost, bd_cause};
            fault <= p_st[0] | cal_fault | early | lock_lost | bd_fault;
        end
endmodule
`default_nettype wire
