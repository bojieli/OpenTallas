`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// hfd_ep_static_vc2 / hfd_ep_host_vc (HBM-BIND 2026-10-24, OWNER ruling 10-24 "host in-band"): the B2 die drops its
// dedicated host UCIe (host_N, ot_pdie_ucie_col).  Host control-plane frames ride the N0 die link as a second virtual
// channel (VC 1) beside the COLL frames (VC 0):
//
//     hb_coll_NW --tx/rx (VC0)--> ep_N0 = hfd_ep_static_vc2 <--sd 512 b--> lk_N0 (ot_pdie_serdes, unchanged)
//     host_cp_rxs <--COLL face--> host_ep = hfd_ep_host_vc <--frame face (VC1, 612 b each way)--> ep_N0
//
// hfd_ep_static (CLOSED, 494f8abf) is untouched; this file holds a successor endpoint with the same lane rules.
//
// Lane format change (both ends of a VC link run this master): slot S = 614 b = {vc, frame[611:0], v} (hfd_ep_static:
// 613 b {frame, v}).  4 slots per 5-beat group still fit (4 x 614 = 2,456 <= 2,550 gearbox bits), so the slot calendar
// (phase 0..3 take, phase 4 / IDLE never) and the lane rate (816 slots / 1,021 beats) are unchanged.  The gearboxes
// below are the hfd_ep_static ones with the slot offsets written as d_k = k (S - 510) (S = 613 gives the as-built
// constants 103 / 206 / 309 / 412 and 510 / 407 / 304 / 201).
//
// Static schedule / flow control (owner rules 10-14): VC 0 (COLL) keeps the compiler calendar -- a COLL frame must land
// on a take slot exactly as before (+1 TX edge, below), never waits, and has priority.  VC 1 (host) is the off-die host
// boundary (configuration path, no token schedule; the host sends <= 1 request / 16 edges and the die answers <= 1 /
// TXGAP = 12 edges, ot_hbm_host_cp_rxs): host TX frames enter a HQ-deep elastic queue in ep_N0 and leave on the first
// take slot COLL does not use, at least HMIN = 10 edges after the previous host frame (the queue never bunches frames:
// the far host_cp_rxs drains a one-frame pingpong that recycles in 8 receiver edges; +2 for a rate-matcher IDLE slip).
// Compiler obligation on a host-carrying link: the COLL calendar leaves free take slots at >= the host frame rate
// (host rule: <= 1 frame / 16 edges each way), e.g. one free take slot in every 16 beats (7.8% of the take slots) or host
// windows between COLL phases; bursts are absorbed while the queue holds HQ frames; a queue overflow is a sticky
// fault (fault_cause[9], the calendar-fault position, and h_cause[1]), never a stall.  RX: the slot's vc bit steers the
// frame to the COLL pingpong (vc 0) or to the host face (vc 1); each side's pingpong admits only its own frames, so the
// host's arming never interacts with the COLL calendar.
//
// Latencies vs hfd_ep_static: COLL tx pin -> SerDes tx pin 3 edges (+1: q pin flop, then the VC merge register = the
// gearbox's input register); RX unchanged (3 edges to the pingpong).  Host: h_tx pin -> merge >= 2 edges (+ queue wait),
// RX vc 1 frame -> h_rx pins 1 edge after the gearbox, + host_ep pin flop (1) -> host pingpong.
// MUT (bench only): 1..4 as hfd_ep_static; 5 TX drops the vc bit; 6 VC merge ignores the take lookahead; 7 RX ignores
// the vc bit (every frame to COLL); 8 host queue never advances its read pointer; 9 host lane spacing HMIN ignored.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hep_tx_gbx_vc #(parameter integer IDLE_K = 204, parameter integer S = 614, parameter integer MUT = 0) (
    input  wire         clk,
    input  wire         rst_n,          // synchronised
    input  wire         tx_v,           // the merge registers (hfd_ep_static_vc2)
    input  wire [611:0] tx_frame,
    input  wire         tx_vc,
    output reg  [511:0] beat,           // registered: the SerDes tx pins
    output wire         take_next,      // the beat after the next edge takes a slot (merge lookahead)
    output reg          cal_fault
);
    localparam integer GB = 13, SL = 64, NSL = (S + SL - 1) / SL;
    localparam integer D1 = S - 510, D2 = 2 * (S - 510), D3 = 3 * (S - 510), D4 = 4 * (S - 510);
    initial if (S < 613 || S > 614 || D4 > 510) $fatal(1, "ot_hep_tx_gbx_vc: slot width must be 613 or 614");
    reg [2:0]  ph;
    reg [GB-1:0] gc;
    wire idle_n_now = (gc == IDLE_K[GB-1:0]);
    wire [2:0]  ph_n = idle_n_now ? ph : (ph == 3'd4 ? 3'd0 : ph + 3'd1);
    wire [GB-1:0] gc_n = idle_n_now ? {GB{1'b0}} : (ph == 3'd4 ? gc + 1'b1 : gc);
    wire idle_n = (gc_n == IDLE_K[GB-1:0]);
    assign take_next = !idle_n && ph_n != 3'd4;
    (* keep *) reg [NSL*5-1:0] oh;
    (* keep *) reg [NSL-1:0]   tk;
    (* keep *) reg [7:0] idr;
    reg [S-1:0] prv;
    reg [S-1:0] cur;
    reg [509:0] g;
    integer s, j, k;
    wire [511:0] bnext = {g, 1'b0, oh[0]};
    always @(*) begin
        for (s = 0; s < NSL; s = s + 1)
            for (j = s * SL; j < (s + 1) * SL && j < S; j = j + 1)
                cur[j] = tk[s] & (j == 0 ? tx_v : (j <= 612 ? tx_frame[j - 1] : ((MUT == 5) ? 1'b0 : tx_vc)));
        for (j = 0; j < 510; j = j + 1) begin
            s = j / SL;
            g[j] = (oh[s*5+0] & cur[j])
                 | (oh[s*5+1] & (j < D1 ? prv[S - D1 + j] : cur[j - D1]))
                 | (oh[s*5+2] & (j < D2 ? ((MUT == 1) ? prv[S - D2 - 1 + j] : prv[S - D2 + j]) : cur[j - D2]))
                 | (oh[s*5+3] & (j < D3 ? prv[S - D3 + j] : cur[j - D3]))
                 | (oh[s*5+4] & (j < D4 ? prv[S - D4 + j] : 1'b0));
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

module ot_hep_rx_gbx_vc #(parameter integer S = 614, parameter integer MUT = 0) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [511:0] beat,
    input  wire [7:0]   data_r,
    output reg          f_v0,           // registered: a vc 0 frame
    output reg          f_v1,           // registered: a vc 1 frame
    output reg  [611:0] f_d,
    output reg          locked,
    output reg          lock_lost
);
    localparam integer SL = 64, NSL = (S + SL - 1) / SL;
    localparam integer D1 = S - 510, D2 = 2 * (S - 510), D3 = 3 * (S - 510);
    initial if (S < 613 || S > 614) $fatal(1, "ot_hep_rx_gbx_vc: slot width must be 613 or 614");
    wire data = (MUT == 2) ? 1'b1 : !beat[1];
    wire mk = beat[0];
    wire [509:0] gcur = beat[511:2];
    reg [509:0] pg;
    reg [2:0] ph, cnt;
    reg seen;
    (* keep *) reg [NSL*4-1:0] oh;
    reg [S-1:0] slot;
    reg [2:0] ph_n; reg lk_n;
    integer s, j;
    always @(*) begin
        for (j = 0; j < S; j = j + 1) begin
            s = j / SL;
            slot[j] = (oh[s*4+0] & ((MUT == 3) ? (j < D1 ? pg[j] : gcur[j - D1]) : (j < 510 ? pg[j] : gcur[j - 510])))
                    | (oh[s*4+1] & (j < 510 - D1 ? pg[D1 + j] : gcur[j - (510 - D1)]))
                    | (oh[s*4+2] & (j < 510 - D2 ? pg[D2 + j] : gcur[j - (510 - D2)]))
                    | (oh[s*4+3] & (j < 510 - D3 ? pg[D3 + j] : gcur[j - (510 - D3)]));
        end
    end
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
    wire fv = data && locked && ((ph == 3'd0) == mk) && ph != 3'd0 && slot[0];
    wire vc = (S > 613 && MUT != 7) ? slot[S-1] : 1'b0;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            locked <= 1'b0; lock_lost <= 1'b0; ph <= 3'd0; cnt <= 3'd0; seen <= 1'b0; f_v0 <= 1'b0; f_v1 <= 1'b0;
            oh <= {(NSL*4){1'b0}};
        end else begin
            f_v0 <= fv && !vc;
            f_v1 <= fv && vc;
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

// ep_N0 of the B2 die: hfd_ep_static + host VC (queue, merge, demux).
module hfd_ep_static_vc2 #(parameter integer IDLE_K = 204, parameter integer HQ = 4, parameter integer HMIN = 10,
                          parameter integer MUT = 0) (
    input  wire         clk,
    input  wire         rst_n,
    // COLL face (VC 0, static calendars) -- as hfd_ep_static
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
    // host face (VC 1, frames; hfd_ep_host_vc)
    input  wire         h_tx_v,
    input  wire [611:0] h_tx_frame,
    output reg          h_rx_v,
    output reg  [611:0] h_rx_frame,
    output reg          h_up,
    output reg  [2:0]   h_cause,        // {SerDes st fault, calendar / host-queue fault, RX lock lost}
    // SerDes face
    output wire [511:0] sd_tx,
    input  wire [511:0] sd_rx,
    input  wire [1:0]   sd_st
);
    localparam integer S = 614, HW = (HQ <= 2) ? 1 : $clog2(HQ);
    initial if (HQ < 2 || (1 << HW) != HQ || HMIN < 1 || HMIN > 32) $fatal(1, "hfd_ep_static_vc2: HQ power of two >= 2, HMIN 1..32");
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    (* keep *) reg rn_tx, rn_rx, rn_bd, rn_o, rn_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rn_tx <= 1'b0; rn_rx <= 1'b0; rn_bd <= 1'b0; rn_o <= 1'b0; rn_q <= 1'b0; end
        else begin rn_tx <= rs[1]; rn_rx <= rs[1]; rn_bd <= rs[1]; rn_o <= rs[1]; rn_q <= rs[1]; end
    // input pin registers (every input)
    reg q_tx_v; reg [611:0] q_tx_f;
    reg q_h_v; reg [611:0] q_h_f;
    reg p_arm_v, p_arm_b, p_rel_v, p_rel_b, p_slot_v, p_slot_b;
    reg [6:0] p_words; reg [5:0] p_slot_i;
    reg [511:0] p_rx; reg [1:0] p_st;
    reg [511:0] q_rx; (* keep *) reg [7:0] p_rxd;
    always @(posedge clk) begin
        q_tx_v <= tx_v; q_tx_f <= tx_frame;
        q_h_v <= h_tx_v; q_h_f <= h_tx_frame;
        p_arm_v <= rx_arm_v; p_arm_b <= rx_arm_bank; p_words <= rx_block_words;
        p_rel_v <= rx_release_v; p_rel_b <= rx_release_bank;
        p_slot_v <= rx_slot_v; p_slot_b <= rx_slot_bank; p_slot_i <= rx_slot_index;
        p_rx <= sd_rx; p_st <= sd_st;
        q_rx <= p_rx; p_rxd <= {8{!p_rx[1]}};
    end
    // ---- host TX queue (off-die host boundary: elastic, HQ frames, overflow = sticky fault)
    reg [611:0] hq [0:HQ-1];
    reg [HW-1:0] hwp, hrp; reg [HW:0] hcnt; reg hq_ovf;
    wire take_next;
    wire hq_ne = hcnt != 0;
    reg [4:0] hsp;                      // lane spacing of host frames (>= HMIN edges: the far host_cp_rxs one-frame
                                        // pingpong recycles in 8 receiver edges; the queue must not bunch frames)
    wire hsel = !q_tx_v && hq_ne && (hsp == 5'd0 || MUT == 9) && ((MUT == 6) ? 1'b1 : take_next);
    wire hpush = q_h_v && hcnt != HQ[HW:0];
    always @(posedge clk or negedge rn_q)
        if (!rn_q) begin hwp <= 0; hrp <= 0; hcnt <= 0; hq_ovf <= 1'b0; hsp <= 5'd0; end
        else begin
            hsp <= hsel ? 5'(HMIN - 1) : (hsp != 5'd0 ? hsp - 5'd1 : 5'd0);
            if (hpush) hwp <= hwp + 1'b1;
            if (hsel && MUT != 8) hrp <= hrp + 1'b1;
            hcnt <= hcnt + (hpush ? 1'b1 : 1'b0) - (hsel ? 1'b1 : 1'b0);
            if (q_h_v && hcnt == HQ[HW:0]) hq_ovf <= 1'b1;
        end
    always @(posedge clk) if (hpush) hq[hwp] <= q_h_f;
    // ---- VC merge register = the gearbox input register (COLL priority; host only on a take slot COLL leaves free)
    reg p_tx_v, p_vc; reg [611:0] p_tx_f;
    wire [611:0] hhead = hq[hrp];
    integer k;
    always @(posedge clk) begin
        p_tx_v <= q_tx_v || hsel;
        p_vc <= hsel;
        for (k = 0; k < 612; k = k + 1) p_tx_f[k] <= q_tx_v ? q_tx_f[k] : hhead[k];
    end
    wire cal_fault;
    ot_hep_tx_gbx_vc #(.IDLE_K(IDLE_K), .S(S), .MUT((MUT == 1 || MUT == 5) ? MUT : 0)) u_tx (.clk(clk), .rst_n(rn_tx),
        .tx_v(p_tx_v), .tx_frame(p_tx_f), .tx_vc(p_vc), .beat(sd_tx), .take_next(take_next), .cal_fault(cal_fault));
    wire f_v0, f_v1, locked, lock_lost; wire [611:0] f_d;
    ot_hep_rx_gbx_vc #(.S(S), .MUT((MUT == 2 || MUT == 3 || MUT == 7) ? MUT : 0)) u_rx (.clk(clk), .rst_n(rn_rx),
        .beat(q_rx), .data_r(p_rxd), .f_v0(f_v0), .f_v1(f_v1), .f_d(f_d), .locked(locked), .lock_lost(lock_lost));
    wire phy_ready, bd_fault; wire [1:0] bready; wire [6:0] bd_cause;
    ot_hep_rx_pingpong #(.MUT(MUT == 4 ? 2 : 0)) u_rxb (.clk(clk), .rst_n(rn_bd),
        .arm_v(p_arm_v), .arm_bank(p_arm_b), .block_words(p_words),
        .phy_v(f_v0), .phy_flit(f_d), .phy_ready(phy_ready), .block_ready(bready),
        .release_v(p_rel_v), .release_bank(p_rel_b),
        .slot_v(p_slot_v), .slot_bank(p_slot_b), .slot_index(p_slot_i),
        .pin_v(rx_pin_v), .pin_flit(rx_pin_flit), .fault(bd_fault), .fault_cause(bd_cause));
    // host RX face: registered vc 1 frames (h_rx_frame loads every edge, h_rx_v qualifies)
    always @(posedge clk) h_rx_frame <= f_d;
    reg early;
    always @(posedge clk or negedge rn_o)
        if (!rn_o) begin
            early <= 1'b0; rx_block_ready <= 2'b00; phy_up <= 1'b0; fault <= 1'b0; fault_cause <= 11'd0;
            h_rx_v <= 1'b0; h_up <= 1'b0; h_cause <= 3'd0;
        end else begin
            if (f_v0 && !phy_ready) early <= 1'b1;
            rx_block_ready <= bready;
            phy_up <= p_st[1] && locked;
            h_up <= p_st[1] && locked;
            h_rx_v <= f_v1;
            fault_cause <= {p_st[0], cal_fault | hq_ovf, early, lock_lost, bd_cause};
            fault <= p_st[0] | cal_fault | hq_ovf | early | lock_lost | bd_fault;
            h_cause <= {p_st[0], cal_fault | hq_ovf, lock_lost};
        end
endmodule

// host_ep of the B2 die: the host's COLL-style face (ot_hbm_host_cp_rxs unchanged) on the ep_N0 host VC.
module hfd_ep_host_vc #(parameter integer MUT = 0) (
    input  wire         clk,
    input  wire         rst_n,
    // COLL face (as hfd_ep_static; driven by ot_hbm_host_cp_rxs)
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
    // VC face (hfd_ep_static_vc2 host face)
    output reg          vc_tx_v,
    output reg  [611:0] vc_tx_frame,
    input  wire         vc_rx_v,
    input  wire [611:0] vc_rx_frame,
    input  wire         vc_up,
    input  wire [2:0]   vc_cause
);
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    (* keep *) reg rn_bd, rn_o;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rn_bd <= 1'b0; rn_o <= 1'b0; end else begin rn_bd <= rs[1]; rn_o <= rs[1]; end
    reg p_arm_v, p_arm_b, p_rel_v, p_rel_b, p_slot_v, p_slot_b;
    reg [6:0] p_words; reg [5:0] p_slot_i;
    reg p_rx_v; reg [611:0] p_rx_f; reg p_up; reg [2:0] p_cause;
    always @(posedge clk) begin
        vc_tx_v <= tx_v; vc_tx_frame <= tx_frame;       // pin flop = output register (ep_N0 pin-flops it again)
        p_arm_v <= rx_arm_v; p_arm_b <= rx_arm_bank; p_words <= rx_block_words;
        p_rel_v <= rx_release_v; p_rel_b <= rx_release_bank;
        p_slot_v <= rx_slot_v; p_slot_b <= rx_slot_bank; p_slot_i <= rx_slot_index;
        p_rx_v <= vc_rx_v; p_rx_f <= vc_rx_frame; p_up <= vc_up; p_cause <= vc_cause;
    end
    wire phy_ready, bd_fault; wire [1:0] bready; wire [6:0] bd_cause;
    ot_hep_rx_pingpong #(.MUT(MUT == 4 ? 2 : 0)) u_rxb (.clk(clk), .rst_n(rn_bd),
        .arm_v(p_arm_v), .arm_bank(p_arm_b), .block_words(p_words),
        .phy_v(p_rx_v), .phy_flit(p_rx_f), .phy_ready(phy_ready), .block_ready(bready),
        .release_v(p_rel_v), .release_bank(p_rel_b),
        .slot_v(p_slot_v), .slot_bank(p_slot_b), .slot_index(p_slot_i),
        .pin_v(rx_pin_v), .pin_flit(rx_pin_flit), .fault(bd_fault), .fault_cause(bd_cause));
    reg early;
    always @(posedge clk or negedge rn_o)
        if (!rn_o) begin
            early <= 1'b0; rx_block_ready <= 2'b00; phy_up <= 1'b0; fault <= 1'b0; fault_cause <= 11'd0;
        end else begin
            if (p_rx_v && !phy_ready) early <= 1'b1;
            rx_block_ready <= bready;
            phy_up <= p_up;
            fault_cause <= {p_cause[2], p_cause[1], early, p_cause[0], bd_cause};
            fault <= (|p_cause) | early | bd_fault;
        end
endmodule
`default_nettype wire
