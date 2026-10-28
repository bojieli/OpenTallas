// MESO-COUNT-2 provable harness for ot_dp_clk_landing_ca (SymbiYosys multiclock, abc pdr; no SMT solver).
// Differences from MESO-COUNT-1 fv_ca.sv (PDR did not converge): no global time counter and no measured origin
// times; the lag is a STATIC function of the anyconst start offsets and phase, all harness counters are TW bits wide
// (= the DUT's count width, so every count relation is mod 2^TW) or small and saturating; data width 1 bit with one
// watched word (data independence: the ring never inspects data, every data bit takes the same path as bit 0).
// Global time = $global_clock steps, period P = 8 steps.  tclk rises when tick 7->0, rclk when tick (PH-1)->PH.
// The sender start is sampled high first by tclk edge #SR (edges counted from 0), the receiver start by rclk edge #RR.
//   tclk edge #i at step 8(i+1); rclk edge #i at step PH' + 8i, PH' = PH (1..7) or 8 (PH = 0)
//   lag of every word  L = t(rclk edge RR) + K P - t(tclk edge SR) = PH' + 8 (RR - SR + K - 1)   [steps]
// Metastability / STA abstraction (as MESO-COUNT-1): a slot read 0..3 steps (< P/2) after its write, or a guard sample
// at the write instant, returns an ARBITRARY value (fv_any, anyseq).
//   A_SAFE  (every PH, SR, RR in range, no window assumption): ready && !fault -> q == word (receiver count - 1 - K)
//   A_NOFLT (L in [LMIN, LMAX] steps): fault never rises
//   A_LIVE  (L in the window): ready once LIVEN receiver cycles passed since the receiver start
// MESO-RECONCILE-1: the wrapper's ready-timeout (TIMEOUT default = K + ARM + 2D + 8) is in the DUT; A_NOFLT now also
// proves it never fires in the window (helpers hb18..hb20 on dut.tmo_cnt); A_TMO (FV_TMO): a lag outside the window
// (L <= 3 or >= 8D - 3 steps) raises fault once TMO + 3 receiver cycles passed since the receiver start.
`ifndef FV_D
`define FV_D 4
`endif
`ifndef FV_K
`define FV_K 2
`endif
`ifndef FV_RRM
`define FV_RRM 12
`endif
`ifndef FV_SRM
`define FV_SRM 4
`endif
// MESO-STRAP-1 FV_STRAP: the DUT is ot_dp_clk_landing_cas (K = strap_k input, OWNER 12.15a).  The strap value KS is a free
// constant (anyconst) over ALL 2^TW values; the harness keeps the integer K it stands for as a free constant KI with
// KS = KI mod 2^TW, and a configuration fixes only the phase PH and E = (RR - SR) + KI (so the lag L = PH' + 8 (E - 1)).
// With SRM = RRM = 2^TW/2 + 1 the start offset RR - SR spans 2^TW + 1 values, so in every configuration KS takes every
// residue (each with its own start offset): the proof holds for all strap values, not one.
module fv_ca2 #(parameter integer D = `FV_D, parameter integer K = `FV_K, parameter integer SRM = `FV_SRM, parameter integer RRM = `FV_RRM,
                parameter integer LMIN = 5, parameter integer LMAX = 8 * D - 5,
`ifdef FV_STRAP
                parameter integer LIVEN = 3 * D + 16 + SRM) (
`else
                parameter integer LIVEN = 3 * D + 16) (
`endif
    input wire [0:0] d,
    input wire [4:0] fv_any
);
    localparam integer P = 8, AW = $clog2(D), TW = AW + 1 + 3;   // LAPX = 3 (wrapper default)
    localparam integer CW = $clog2(RRM + 2);
`ifdef FV_STRAP
    localparam integer NTK = 1 << TW;
    localparam integer ARMW = 2 * D + 4, TMO = NTK - 1 + ARMW + 2 * D + 8, TCW = $clog2(TMO + 2), RCW = 8;
    (* anyconst *) reg [TW-1:0] KS;        // the strap value seen by the DUT
    (* anyconst *) reg signed [9:0] KI;    // the integer K it stands for (harness only)
    always @* assume(KS == KI[TW-1:0]);
    wire signed [9:0] KIP = (KI > 0) ? KI : 10'sd0;
    wire signed [9:0] KL = KI;
    wire [TW-1:0] KT = KS;
`else
    localparam integer KP = (K > 0) ? K : 0, ARMW = 2 * D + 4, TMO = KP + ARMW + 2 * D + 8, TCW = $clog2(TMO + 2), RCW = 7;
    wire signed [9:0] KIP = KP;
    wire signed [9:0] KL = K;
    wire [TW-1:0] KT = K;
`endif
    (* anyconst *) reg [2:0] PH;
    (* anyconst *) reg [CW-1:0] SR, RR;
    (* anyconst *) reg [TW-1:0] N;        // watched sender word (mod 2^TW)
    always @* begin assume(SR >= 1 && SR <= SRM); assume(RR >= 1 && RR <= RRM); end
`ifdef FV_PH
    always @* assume(PH == `FV_PH);
`endif
`ifdef FV_OFF
    always @* assume($signed({1'b0, RR}) - $signed({1'b0, SR}) == `FV_OFF);
`endif
`ifdef FV_E
    always @* assume($signed({1'b0, RR}) - $signed({1'b0, SR}) + KL == `FV_E);
`endif
    reg [2:0] tick = 0;
    wire tclk = (tick < 3'd4);
    wire [2:0] rt = tick - PH;
    wire rclk = (rt < 3'd4);
    wire tn = (tick == 3'd7);              // tclk rises at the next step
    wire [2:0] tick1 = tick + 3'd1;
    wire rn = (tick1 == PH);               // rclk rises at the next step
    reg [CW-1:0] te = 0, re = 0; reg t_rst_n = 0, rst_n = 0;
    reg [TW-1:0] sc = 0, rc = 0; reg [0:0] cap = 0; reg capv = 0;
    reg [RCW-1:0] rcs = 0;                 // receiver cycles since its start, saturating
    wire wr = tn && t_rst_n;               // a word is written at the next step, slot sc[AW-1:0]
    always @($global_clock) begin
        tick <= tick + 1'b1;
        if (tn) begin
            if (te != {CW{1'b1}}) te <= te + 1'b1;
            t_rst_n <= t_rst_n || (te + 1'b1 >= SR);
            if (t_rst_n) begin
                sc <= sc + 1'b1;
                if (sc == N) begin cap <= d; capv <= 1'b1; end
            end
        end
        if (rn) begin
            if (re != {CW{1'b1}}) re <= re + 1'b1;
            rst_n <= rst_n || (re + 1'b1 >= RR);
            if (rst_n) begin rc <= rc + 1'b1; if (rcs != {RCW{1'b1}}) rcs <= rcs + 1'b1; end
        end
    end
    wire [3:0] php = (PH == 3'd0) ? 4'd8 : {1'b0, PH};
    wire signed [12:0] L = $signed({9'b0, php}) + 13'sd8 * ($signed({1'b0, RR}) - $signed({1'b0, SR}) + KL - 1);
    wire inwin = L >= LMIN && L <= LMAX;
    reg [2:0] age [0:D-1];
    integer i;
    initial for (i = 0; i < D; i = i + 1) age[i] = 3'd7;
    wire [D-1:0] wnext, recent;
    genvar g;
    for (g = 0; g < D; g = g + 1) begin : gw
        assign wnext[g] = wr && (sc[AW-1:0] == g);
        always @($global_clock) age[g] <= wnext[g] ? 3'd0 : ((age[g] == 3'd7) ? 3'd7 : age[g] + 1'b1);
        assign recent[g] = wnext[g] || (age[g] <= 3'd2);
    end
    wire [0:0] q; wire ready, fault;
`ifdef FV_STRAP
    ot_dp_clk_landing_cas #(.W(1), .DEPTH(D), .GUARD_LO(0), .GUARD_HI(D)) dut (
        .fclk(tclk), .t_rst_n(t_rst_n), .clk(rclk), .rst_n(rst_n), .strap_k(KS), .d(d), .q(q), .ready(ready), .fault(fault),
`else
    ot_dp_clk_landing_ca #(.W(1), .DEPTH(D), .K(K), .GUARD_LO(0), .GUARD_HI(D)) dut (
        .fclk(tclk), .t_rst_n(t_rst_n), .clk(rclk), .rst_n(rst_n), .d(d), .q(q), .ready(ready), .fault(fault),
`endif
        .fv_recent(recent), .fv_now(wnext), .fv_any(fv_any));

`ifdef FV_HELP
    // Strengthening invariants (proved together with the properties, single output).  The h_* wires are driven by
    // `connect` in the sby script after flatten (yosys has no hierarchical references): h_tc = dut.u_ring.tc, ...
    localparam integer NS = 2 * D, LX = 3;
    wire [TW-1:0] h_tc, h_rp; wire [NS-1:0] h_oh; wire [D-1:0] h_di, h_sw, h_slap, h_sd; wire [D*LX-1:0] h_stag;
    reg [AW:0] nw = 0;                     // words written since the sender start, saturating at D
    reg sst = 0, rst = 0;                  // a sender / receiver edge sampled its start high
    always @($global_clock) begin
        if (tn && t_rst_n) begin sst <= 1'b1; if (nw != D) nw <= nw + 1'b1; end
        if (rn && rst_n) rst <= 1'b1;
    end
    wire [TW-1:0] teT = te, reT = re, srT = SR, rrT = RR;
    wire [TW-1:0] sR = sst ? sc : teT - srT;
    wire [TW-1:0] rR = rst ? rc : reT - rrT;
    wire [TW-1:0] one = 1, inc = (tick < php) ? 1 : 0;
    wire [TW-1:0] dsr = rrT - srT - one + inc;
    wire [TW-AW-1:0] sch = sc[TW-1:AW];
    reg [10:0] hb; wire h_ok = ~|hb && ~|hb2;
    integer j;
    always @* begin
        hb = 0;
        if (te != 0) begin
            if (h_tc != sc) hb[0] = 1;
            for (j = 0; j < D; j = j + 1) begin : hs
                if (h_sw[j] != (nw > j)) hb[1] = 1;
            end
        end
        if (te != 0) for (j = 0; j < D; j = j + 1) if (nw > j) begin
            // count of the last write into slot j: largest c < sc with c = j mod D
            if ({h_stag[j*LX +: LX], h_slap[j]} != ((sc[AW-1:0] > j) ? sch : sch - 1'b1)) hb[2] = 1;
            if ((((sc[AW-1:0] > j) ? sch : sch - 1'b1) == N[TW-1:AW]) && (N[AW-1:0] == j) && !(capv && h_sd[j] == cap)) hb[3] = 1;
        end
        if (re != 0) begin
            if (h_rp != rc - KT) hb[4] = 1;
            if (h_oh != (NS'(1) << h_rp[AW:0])) hb[5] = 1;
            if (h_di != (D'(1) << h_rp[AW-1:0])) hb[6] = 1;
        end
        // start-up counts: S - R == dsr at every step (S = sender count, virtual before its start; R likewise)
        if (sR - rR != dsr) hb[7] = 1;
        if (te != {CW{1'b1}} && re != {CW{1'b1}} && (te - re != ((tick < php) ? {CW{1'b0}} : {CW{1'b1}}))) hb[8] = 1;
        if (sst != (te > SR) || rst != (re > RR) || t_rst_n != (te >= SR) || rst_n != (re >= RR)) hb[9] = 1;
        for (j = 0; j < D; j = j + 1)
            if (age[j] != ((sst && ((sc - 1'b1) % D) == j) ? tick : 3'd7)) hb[10] = 1;
    end

    // in-window steady state of the wrapper / guard pipeline / RDREG (h2_* driven by `connect` like h_*)
    localparam integer ARMV = 2 * D + 4, CWA = $clog2(ARMV + 1);
    wire h2_seen, h2_fs, h2_rvq, h2_rlq, h2_yq, h2_dxq; wire [CWA-1:0] h2_arm; wire [3:0] h2_glo, h2_ghi;
    wire [TCW-1:0] h3_tmo;                 // dut.tmo_cnt (MESO-RECONCILE-1 ready-timeout counter)
    wire h3_armed = h2_seen && (h2_arm == ARMV);
    reg gN = 0;                            // the read at the last rclk edge was a clean read of word N
    wire [TW-1:0] rdw = rc - KT;           // word read at the coming rclk edge
    wire [TW-1:0] dN = sc - N;
    always @($global_clock) if (rn) gN <= rst_n && capv && (rdw == N) && (dN >= 1) && (dN <= D) && !recent[N[AW-1:0]];
    wire [TW-1:0] idx2 = rc - one - KT;
    wire [TW-1:0] dI = sc - idx2;
    reg [20:11] hb2;
    always @* begin
        hb2 = 0;
        if (inwin && re != 0) begin
            if (!h2_seen && (h2_arm != 0 || ready)) hb2[12] = 1;
            if (ready && !(h2_seen && h2_arm == ARMV)) hb2[12] = 1;
            if (h2_seen && !(h2_rvq && h2_rlq && h2_glo[0] && h2_ghi[0] && !h2_dxq)) hb2[13] = 1;
            if (h2_seen && h2_arm >= 1 && !(h2_glo[1] && h2_ghi[1])) hb2[14] = 1;
            if (h2_seen && h2_arm >= 2 && !(h2_glo[2] && h2_ghi[2])) hb2[14] = 1;
            if (h2_seen && h2_arm >= 3 && !(h2_glo[3] && h2_ghi[3])) hb2[14] = 1;
            if (h2_seen && !(dI >= 1 && dI <= D + 1)) hb2[15] = 1;
            if (h2_seen && idx2 == N && !gN) hb2[16] = 1;
        end
        if (gN && !h2_dxq && !(capv && h2_yq == cap)) hb2[17] = 1;
        // ready-timeout: counts receiver cycles since start while not armed; in the window armed long before TMO
        if (re != 0 && !h3_armed && h3_tmo != ((rcs >= TMO) ? TCW'(TMO) : TCW'(rcs))) hb2[18] = 1;
        if (inwin && re != 0 && $signed({2'b0, rcs}) >= KIP + 4 && !h2_seen) hb2[19] = 1;
        if (inwin && h2_seen && !h3_armed && $signed({2'b0, rcs}) > $signed({2'b0, h2_arm}) + KIP + 4) hb2[20] = 1;
    end
`else
    wire h_ok = 1'b1;
`endif
    wire [TW-1:0] idx = rc - 1'b1 - KT;
    wire up = (re != 0);                   // >= 1 rclk edge (a reset edge, RR >= 1): DUT state defined
    wire p_safe = !(up && ready && !fault && idx == N) || (capv && q == cap);
    wire p_noflt = !(up && inwin) || !fault;
    wire p_live = !(inwin && rcs >= LIVEN) || ready;
    wire p_closed = !((L <= 3 || L >= 8 * D - 3) && up && ready && !fault);   // fail closed outside the window
    localparam integer TMOW = TMO + 3;
    wire p_tmo = !((L <= 3 || L >= 8 * D - 3) && up && rcs >= TMOW) || fault;   // MESO-RECONCILE-1 ready-timeout
    always @* begin
`ifdef FV_TMOONE
        A_ALLT: assert (p_tmo && p_safe && p_closed && h_ok);   // MESO-RECONCILE-1, per out-of-window config
`elsif FV_ONE
`ifdef FV_NOLIVE
        A_ALL: assert (p_safe && p_noflt && p_closed && h_ok);   // liveness checked by BMC (bounded response)
`else
        A_ALL: assert (p_safe && p_noflt && p_live && h_ok);
`endif
`elsif FV_HELPONLY
        A_H0: assert (!hb[0]); A_H1: assert (!hb[1]); A_H2: assert (!hb[2]); A_H3: assert (!hb[3]);
        A_H4: assert (!hb[4]); A_H5: assert (!hb[5]); A_H6: assert (!hb[6]); A_H7: assert (!hb[7]);
        A_H8: assert (!hb[8]); A_H9: assert (!hb[9]); A_H10: assert (!hb[10]);
        A_H11: assert (!hb2[11]); A_H12: assert (!hb2[12]); A_H13: assert (!hb2[13]); A_H14: assert (!hb2[14]);
        A_H15: assert (!hb2[15]); A_H16: assert (!hb2[16]); A_H17: assert (!hb2[17]);
        A_H18: assert (!hb2[18]); A_H19: assert (!hb2[19]); A_H20: assert (!hb2[20]);
`elsif FV_SAFE_ONLY
        A_SAFE: assert (p_safe);
`else
        A_SAFE: assert (p_safe);
        A_NOFLT: assert (p_noflt);
        A_LIVE: assert (p_live);
`endif
    end
`ifdef FV_FLT
    // fail closed: a lag outside the window (and away from the two sampling-instant points L = 4, 8D - 4) raises fault
    // within LIVEN receiver cycles of the receiver start (bounded response, BMC)
    // fail closed: outside the window (away from the two sampling-instant points L = 4, 8D - 4) the crossing is never
    // ready-and-unfaulted (A_CLOSED); A_FLT (raised fault within LIVEN cycles) holds only where a valid word is ever
    // consumed -- for negative lags the reader never sees a written slot and stays !ready with no fault
    always @* A_CLOSED: assert (p_closed);
`ifdef FV_FLT_RAISE
    always @* if ((L <= 3 || L >= 8 * D - 3) && rcs >= LIVEN) A_FLT: assert (fault);
`endif
`endif
`ifdef FV_TMO
    // MESO-RECONCILE-1: a lag outside the window is no longer silent: fault within TMO + 3 receiver cycles
    always @* A_TMO: assert (p_tmo);
`endif
`ifdef FV_REACH
    always @* A_REACH: assert (!(up && ready && !fault && inwin && L == LMAX));
`endif
`ifdef FV_CHKL
    // cross-check of the static lag formula against measured origin times (BMC only)
    reg [9:0] t = 0, tw0 = 0, tr0 = 0; reg w0 = 0, r0 = 0;
    always @($global_clock) begin
        if (t != 10'h3ff) t <= t + 1'b1;
        if (tn && t_rst_n && !w0) begin w0 <= 1; tw0 <= t + 1'b1; end
        if (rn && rst_n && !r0) begin r0 <= 1; tr0 <= t + 1'b1; end
    end
    always @* if (w0 && r0) A_L: assert ($signed({3'b0, tr0}) + K * P - $signed({3'b0, tw0}) == L);
`endif
endmodule
