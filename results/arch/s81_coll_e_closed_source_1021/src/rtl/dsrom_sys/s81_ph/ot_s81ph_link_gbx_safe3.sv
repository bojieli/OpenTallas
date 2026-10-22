`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81ph_link_gbx_safe3 (S81-COLL bank64 safe source, LEAD-S81 decision 10-19): the FMT 1 beat format of
// ot_s81ph_link_gbx (fixed 3-slots-in-4-beats group format), cycle-for-cycle identical at every port, rebuilt to the
// owner safe-design checklist.  ot_s81ph_link_gbx is unchanged (legacy tiles keep it).
//   (1) storage: the 4 x 595-bit runtime-indexed slot FIFO sf[sh] (2,380 flop bits, sh[0] drove 2,382 loads) becomes
//       ot_sram_showahead_b64 (ten ot_sram_1r1w2c_32x64_m1 banks, rows 0..3 used; registered write port, show-ahead read
//       of the NEXT head with current / previous logical write forwarding, physical same-address read suppressed).
//   (2) fanout: every wide select is a REGISTERED ONE-HOT computed from the next control state at the edge the
//       original control state is written, and replicated per SL-bit slice as kept flops (TX: 6 payload selects per
//       slice of the beat, 2 rem selects per slice of rem; RX: 3 cut selects per slice of f_rx, 3 hold selects per
//       slice of hold).  Each select flop drives <= SL data gates; each central next-state net drives <= 25 copies.
//       No select is computed from a wide shared combinational enable.  Same edges: no added data or control cycle.
//   (3) reset: control flops reset from RN same-depth copies (rst_n[0]: TX control, [1]: RX control, [2..]: copies);
//       payload (beat bits 3.., rem, bg, hold, f_rx, r_rx) carries no reset, as the original.
// Proof of equivalence (induction): each select copy is reset to f(reset state) and loaded with f(next state) at
// every edge the state is loaded with its next state, so at every cycle select == f(state), i.e. the original
// combinational select; the data muxes are the original case statements written as AND-OR of those selects.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_link_gbx_safe3 #(
    parameter integer FFW = 595,
    parameter integer RFW = 53,
    parameter integer IDLE_P = 1024,
    parameter integer BW = 512,
    parameter integer G = BW - 3 - RFW,
    parameter integer S = FFW + 1,
    parameter integer SL = 24,                       // data bits per select copy
    parameter integer NSH = (FFW + 15) / 16,         // slot-store forwarding slices (ot_sram_showahead_b64 NS)
    parameter integer RL = 24,                       // max flops per reset leaf
    // reset leaves: [0] TX control, [1] RX control, then select copies (ps 6 / rs 2 / hs 3 / cs 3 flops each), then
    // slot-store flag slices (8 slices x 2 flags per leaf)
    parameter integer NPC = (G + SL - 1) / SL, NRC = (3 * (S - G) + SL - 1) / SL, NHC = (G + SL - 1) / SL,
    parameter integer NCC = (FFW + SL - 1) / SL,
    parameter integer KP = RL / 6, KR = RL / 2, KH = RL / 4, KC = RL / 3,
    parameter integer OP = 2, OR = OP + (NPC + KP - 1) / KP, OH = OR + (NRC + KR - 1) / KR, OC = OH + (NHC + KH - 1) / KH,
    parameter integer OS = OC + (NCC + KC - 1) / KC,
    parameter integer RN = OS + (NSH + 7) / 8,       // reset leaves the caller supplies (same release depth)
    parameter integer MUT = 0                        // bench mutants: 1 = TX rem select one cycle stale, 2 = RX hold select stale
) (
    input  wire            clk,
    input  wire [RN-1:0]   rst_n,
    input  wire            f_tx_v,
    input  wire [FFW-1:0]  f_tx,
    input  wire            r_tx_v,
    input  wire [RFW-1:0]  r_tx,
    output reg  [BW-1:0]   beat_tx,
    input  wire            beat_rx_v,
    input  wire [BW-1:0]   beat_rx,
    output reg             f_rx_v,
    output reg  [FFW-1:0]  f_rx,
    output reg             r_rx_v,
    output reg  [RFW-1:0]  r_rx,
    output reg             locked,
    output reg             fault
);
    localparam integer K1 = S - G;                   // 140 at S 596 / G 456
    localparam integer IB1 = $clog2(IDLE_P + 1);
`ifndef SYNTHESIS
    initial if (3 + RFW + G != BW || 3 * S > 4 * G || 3 * K1 > G || SL < 1 || RL < 6 || RN != OS + (NSH + 7) / 8)
        $fatal(1, "ot_s81ph_link_gbx_safe3: geometry");
`endif
    // ============================================================== TX central control (the original FMT 1 control)
    reg  [1:0]     sh, st, ph;
    reg  [2:0]     sn;
    reg  [IB1-1:0] ic;
    reg            idle_q;
    wire           need = !idle_q && (ph != 2'd3);
    wire           take = need && (sn != 0);
    // next control state
    wire           idle_n = !idle_q && (ic == IDLE_P - 2);
    wire [1:0]     ph_n   = idle_q ? ph : ph + 1'b1;
    wire [2:0]     sn_n   = sn + (f_tx_v ? 3'd1 : 3'd0) - (take ? 3'd1 : 3'd0);
    wire [1:0]     sh_n   = take ? sh + 1'b1 : sh;
    wire           need_n = !idle_n && (ph_n != 2'd3);
    wire           take_n = need_n && (sn_n != 0);
    // registered one-hot payload selects for the next beat: {t0, t1, t2, r1, r2, r3}
    //   t_k: slot (shifted k*K1) is taken in group phase k; r_k: rem's top k*K1 bits fill the low bits in phase k
    wire [5:0]     psel_n = {take_n && ph_n == 2'd0, take_n && ph_n == 2'd1, take_n && ph_n == 2'd2,
                             !idle_n && ph_n == 2'd1, !idle_n && ph_n == 2'd2, !idle_n && ph_n == 2'd3};
    wire [1:0]     rsel_n = {take_n, !need_n};             // {load slot, keep}: rem <= slot when need (0 when not taken)
    always @(posedge clk or negedge rst_n[0]) begin
        if (!rst_n[0]) begin
            sh <= 0; st <= 0; sn <= 0; ph <= 0; ic <= 0; idle_q <= (IDLE_P == 1); beat_tx[2:0] <= 3'd0; fault <= 1'b0;
        end else begin
            if (f_tx_v) st <= st + 1'b1;
            sn <= sn_n;
            sh <= sh_n;
            if (f_tx_v && sn == 4 && !take) fault <= 1'b1;
            ic <= idle_q ? 0 : ic + 1'b1;
            idle_q <= idle_n;
            beat_tx[2:0] <= idle_q ? {r_tx_v, 1'b1, 1'b0} : {r_tx_v, 1'b0, ph == 2'd0};
            ph <= ph_n;
        end
    end
    // slot store: q = sf[sh] (show-ahead of the head; the caller-side read address is the NEXT head)
    wire [FFW-1:0] q;
    wire [NSH-1:0] sh_rst_n;
    genvar c, i;
    generate for (c = 0; c < NSH; c = c + 1) begin : g_shr
        assign sh_rst_n[c] = rst_n[OS + c / 8];
    end endgenerate
    ot_sram_showahead_b64 #(.W(FFW), .AW(2), .WREG(1), .NS(NSH), .LOCAL_HIT(1)) u_sf (
        .clk(clk), .rst_n(sh_rst_n), .we(f_tx_v), .wa(st), .wd(f_tx), .ra(sh_n), .q(q));
    wire [S-1:0]   slotv = {q, 1'b1};                // slot when taken (bit 0 = slot valid)
    // TX payload: beat bits [BW-1:3] = {gpay, r_tx}; gpay[i] per the original case (ph) with slot = take ? {sf, 1} : 0
    localparam integer RLO = S - 3 * K1;              // lowest rem bit any phase reads (176)
    localparam integer RW  = 3 * K1;                  // rem bits kept (420)
    reg  [RW-1:0]  rem;                               // = original rem[S-1:RLO] (lower bits never read)
    wire [G-1:0]   gpay;
    generate for (c = 0; c < NPC; c = c + 1) begin : g_pc
        localparam integer LO = c * SL, HI = ((c + 1) * SL > G) ? G : (c + 1) * SL;
        (* keep = "true" *) reg [5:0] ps;            // {t0, t1, t2, r1, r2, r3} copy
        always @(posedge clk or negedge rst_n[OP + c / KP])
            if (!rst_n[OP + c / KP]) ps <= 6'd0;   // reset state: take 0, ph 0
            else ps <= psel_n;
        for (i = LO; i < HI; i = i + 1) begin : g_b
            wire a0 = ps[5] & slotv[i];
            wire a1 = (i >= K1)     ? (ps[4] & slotv[(i >= K1) ? i - K1 : 0])         : (ps[2] & rem[(i < K1) ? i + 2 * K1 : 0]);
            wire a2 = (i >= 2 * K1) ? (ps[3] & slotv[(i >= 2 * K1) ? i - 2 * K1 : 0]) :
                                      (ps[1] & rem[(i < 2 * K1) ? i + K1 : 0]);
            wire a3 = (i < 3 * K1)  ? (ps[0] & rem[(i < 3 * K1) ? i : 0]) : 1'b0;
            assign gpay[i] = a0 | a1 | a2 | a3;
        end
    end endgenerate
    // rem (original: if (!idle_q && need) rem <= slot): original bit j = RLO + k
    generate for (c = 0; c < NRC; c = c + 1) begin : g_rc
        localparam integer LO = c * SL, HI = ((c + 1) * SL > RW) ? RW : (c + 1) * SL;
        (* keep = "true" *) reg [1:0] rs;            // {load, keep} copy (neither: clear); one AND-OR term per bit each
        always @(posedge clk or negedge rst_n[OR + c / KR])
            if (!rst_n[OR + c / KR]) rs <= 2'b00;   // reset state: need 1, take 0 -> clear
            else rs <= (MUT == 1) ? {take, !need} : rsel_n;
        always @(posedge clk)
            rem[HI-1:LO] <= ({(HI-LO){rs[1]}} & slotv[RLO + LO +: (HI - LO)]) | ({(HI-LO){rs[0]}} & rem[HI-1:LO]);
    end endgenerate
    always @(posedge clk) beat_tx[BW-1:3] <= {gpay, r_tx};
    // ============================================================== RX
    reg            bv, bm, bi;
    reg  [G-1:0]   bg;
    reg  [1:0]     hunt;
    reg  [1:0]     mc;
    reg  [G-1:0]   hold;
    wire           gb  = bv && !bi;
    wire           due = (mc == 2'd3);
    wire [1:0]     rph = due ? 2'd0 : mc + 1'b1;
    // next control state (the original reset process)
    wire           bv_n = beat_rx_v, bm_n = beat_rx[0], bi_n = beat_rx[1];
    reg  [1:0]     hunt_n, mc_n;
    reg            locked_n, fv_n;
    always @(*) begin
        hunt_n = hunt; mc_n = mc; locked_n = locked; fv_n = 1'b0;
        if (gb) begin
            mc_n = (bm || due) ? 2'd0 : mc + 1'b1;
            if (hunt != 2) begin
                locked_n = 1'b0;
                if (bm) begin
                    if (hunt == 1 && due) begin hunt_n = 2; locked_n = 1'b1; end
                    else hunt_n = 1;
                end else if (hunt == 1 && due) hunt_n = 0;
            end else if (bm != due) begin
                hunt_n = bm ? 2'd1 : 2'd0; locked_n = 1'b0;
            end else begin
                if (rph != 2'd0) fv_n = hold[0];    // original: f_rx_v <= cut[0]; cut[0] = hold[0] in every phase
            end
        end
    end
    wire           gb_n  = bv_n && !bi_n;
    wire           due_n = (mc_n == 2'd3);
    wire [1:0]     rph_n = due_n ? 2'd0 : mc_n + 1'b1;
    wire           lk_n  = gb_n && hunt_n == 2'd2 && (bm_n == due_n);
    // hold selects {h0, h1, h2}: hold <= bg (phase 0, or the locking second marker), bg >> K1 (phase 1), bg >> 2K1 (phase 2)
    wire [2:0]     hsel_n = {(lk_n && rph_n == 2'd0) || (gb_n && hunt_n == 2'd1 && bm_n && due_n),
                             lk_n && rph_n == 2'd1, lk_n && rph_n == 2'd2};
    // cut selects {c1, c2, c0}
    wire [2:0]     csel_n = {rph_n == 2'd1, rph_n == 2'd2, rph_n == 2'd0 || rph_n == 2'd3};
    always @(posedge clk or negedge rst_n[1]) begin
        if (!rst_n[1]) begin
            bv <= 0; bm <= 0; bi <= 0; hunt <= 0; mc <= 0; locked <= 0; f_rx_v <= 0; r_rx_v <= 0;
        end else begin
            bv <= bv_n; bm <= bm_n; bi <= bi_n;
            r_rx_v <= beat_rx_v && beat_rx[2];
            hunt <= hunt_n; mc <= mc_n; locked <= locked_n; f_rx_v <= fv_n;
        end
    end
    always @(posedge clk) begin bg <= beat_rx[BW-1 -: G]; r_rx <= beat_rx[3 +: RFW]; end
    // hold slices
    generate for (c = 0; c < NHC; c = c + 1) begin : g_hc
        localparam integer LO = c * SL, HI = ((c + 1) * SL > G) ? G : (c + 1) * SL;
        (* keep = "true" *) reg [3:0] hs;          // {h0, h1, h2, none}: one-hot, each drives one AND-OR term per bit
        always @(posedge clk or negedge rst_n[OH + c / KH])
            if (!rst_n[OH + c / KH]) hs <= 4'b0001;   // reset state: bv 0 -> hold
            else hs <= (MUT == 2) ? hs : {hsel_n, hsel_n == 3'd0};
        for (i = LO; i < HI; i = i + 1) begin : g_b
            wire s1 = (i + K1 < G)     ? bg[(i + K1 < G) ? i + K1 : 0]         : 1'b0;
            wire s2 = (i + 2 * K1 < G) ? bg[(i + 2 * K1 < G) ? i + 2 * K1 : 0] : 1'b0;
            always @(posedge clk)
                hold[i] <= (hs[3] & bg[i]) | (hs[2] & s1) | (hs[1] & s2) | (hs[0] & hold[i]);
        end
    end endgenerate
    // f_rx slices: f_rx <= cut[1 +: FFW]; cut[j] = phase 1: j < G ? hold[j] : bg[j - G];
    //   phase 2: j < G - K1 ? hold[j] : bg[j - G + K1]; phase 0/3: j < G - 2K1 ? hold[j] : bg[j - G + 2K1]
    generate for (c = 0; c < NCC; c = c + 1) begin : g_cc
        localparam integer LO = c * SL, HI = ((c + 1) * SL > FFW) ? FFW : (c + 1) * SL;
        (* keep = "true" *) reg [2:0] cs;
        always @(posedge clk or negedge rst_n[OC + c / KC])
            if (!rst_n[OC + c / KC]) cs <= 3'b100;   // reset state: mc 0 -> rph 1
            else cs <= csel_n;
        for (i = LO; i < HI; i = i + 1) begin : g_b
            localparam integer J = i + 1;
            wire v1 = (J < G)          ? hold[(J < G) ? J : 0]                   : bg[(J >= G) ? J - G : 0];
            wire v2 = (J < G - K1)     ? hold[(J < G - K1) ? J : 0]              : bg[(J >= G - K1) ? J - G + K1 : 0];
            wire v0 = (J < G - 2 * K1) ? hold[(J < G - 2 * K1) ? J : 0]          : bg[(J >= G - 2 * K1) ? J - G + 2 * K1 : 0];
            always @(posedge clk) f_rx[i] <= (cs[2] & v1) | (cs[1] & v2) | (cs[0] & v0);
        end
    end endgenerate
endmodule
