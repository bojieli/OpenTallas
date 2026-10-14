`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_cg_tile (redesign-hbm 2026-10-09; coordinator: die power 613.5 W vs 474.56 W, coarse per-tile gating REQUIRED):
// the coarse clock gate of ONE hardened tile / unit (TPU / NVDLA practice: one ICG per unit, enabled by the unit's
// work schedule, never by its own data path).
//   * cgi  : the WAKE request (level).  It lands in an UNGATED pin flop (wq), the only state on the raw clock besides
//            the hold counter; cgo = wq forwards the request to the next unit downstream (one register a hop, so the
//            wake always runs AHEAD of the data, which crosses each hop through more registers than one).
//   * en   : wq OR (hold counter != 0) OR reset.  The counter reloads HOLD while wq is high and counts down after it
//            falls, so the unit keeps clocking HOLD edges after the wake drops (in-flight traffic drains first).
//   * gclk : ot_hdc_cg (the platform ICG cell); physical/common_flow/cg_pushdown.tcl clones it per sink cluster at
//            CTS, so every clone's clock pin sits at the leaf level of the tile's tree (balanced per-tile root, no
//            gated / ungated mixing on any data path: every data flop of the unit is on gclk).
// Exactness contract (the enable SOURCE's obligation, benched by lockstep against the ungated unit): cgi is high
// from no later than the first edge a job's input can reach the unit until its last output has left; HOLD covers
// the unit's in-flight traffic after that.  Reset: the unit is clocked while rst_n is low (ot_hdc_cg note).
// MUT_LATE (bench mutant only): the wake reaches en MUT_LATE edges late.
// ---------------------------------------------------------------------------
module ot_cg_tile #(
    parameter integer HOLD = 64,
    parameter integer MUT_LATE = 0,
    // RSTEN 0 (redesign-hbm 2026-10-10): no !rst_n term in the enable (the async reset already forces wq = 1); for gates whose
    // reset comes from far away (hub quarter: rst -> every group ICG ENA was a 1.3-3.6 ns gating-check path)
    parameter integer RSTEN = 1,
    // ENREG 1 ([cg-hc] 2026-10-10): the ICG enable is ONE register, en_r <= the next value of (wq | cnt != 0), so the
    // ICG's ENA is driven by a flop the placer puts beside the gate (hbm_hc_quarter rootcg-40ec7b434: wq / cnt sat 1 mm
    // from the group ICG, ENA wire 2.3 ns, TT -3,186 ps).  Same value every cycle (0 cycles); reset 1 like wq / cnt.
    // MUT_LATE > 0 (bench mutant) keeps the combinational enable.
    parameter integer ENREG = 0,
    // RAWRST 0 (el1013-smh-r11 2026-10-13, with RSTEN 0): the raw-clock registers (wq, cnt, en_r) carry NO reset, so the
    // rst_n port reaches nothing on the raw clock (SM tile cluster r10: port rst_n -> ICG ENA -2,360 ps and -> the nine raw
    // SETN/RESETN pins 858 ps across ~1,200 um; a port may serve one clock class, and the reset now enters the GATED class
    // through a pin flop).  The gate self-initialises from the wake: cgi = 1 loads wq = 1, cnt = HOLD and en_r = 1 on the
    // next raw edge whatever their power-up state.  CONTRACT (the wake source's obligation): cgi is high while the unit's
    // reset is asserted, from at least 2 raw edges before the first edge the gated logic needs.  rst_n is then unused.
    parameter integer RAWRST = 1
) (
    input  wire clk,
    input  wire rst_n,
    input  wire cgi,
    output wire cgo,
    output wire gclk
);
    localparam integer CW = (HOLD < 2) ? 1 : $clog2(HOLD + 1);
    (* keep *) reg wq;
    reg [CW-1:0] cnt;
    reg [MUT_LATE:0] wl;
    integer i;
    wire w_eff;
    wire en_c;
    reg  en_r;
    generate if (RAWRST != 0) begin : g_rr
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin wq <= 1'b1; cnt <= HOLD[CW-1:0]; wl <= {(MUT_LATE+1){1'b1}}; end
            else begin
                wq <= cgi;
                wl[0] <= wq;
                for (i = 1; i <= MUT_LATE; i = i + 1) wl[i] <= wl[i-1];
                cnt <= w_eff ? HOLD[CW-1:0] : ((cnt != 0) ? cnt - 1'b1 : cnt);
            end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) en_r <= 1'b1;
            else        en_r <= cgi | wq | (cnt > 1);   // = wq' | (cnt' != 0): cnt' = HOLD (wq) or cnt - 1 (cnt != 0)
    end else begin : g_nr
        always @(posedge clk) begin
            wq <= cgi;
            wl[0] <= wq;
            for (i = 1; i <= MUT_LATE; i = i + 1) wl[i] <= wl[i-1];
            cnt <= w_eff ? HOLD[CW-1:0] : ((cnt != 0) ? cnt - 1'b1 : cnt);
        end
        always @(posedge clk) en_r <= cgi | wq | (cnt > 1);
    end endgenerate
    assign w_eff = (MUT_LATE == 0) ? wq : wl[MUT_LATE];
    assign en_c = w_eff | (cnt != 0);
    wire en = (((ENREG != 0) && (MUT_LATE == 0) && (HOLD >= 2)) ? en_r : en_c) | ((RSTEN != 0) ? !rst_n : 1'b0);
    assign cgo = wq;
    ot_hdc_cg u_cg (.clk(clk), .en(en), .gclk(gclk));
`ifndef SYNTHESIS
    initial if (RAWRST == 0 && RSTEN != 0) $error("ot_cg_tile: RAWRST 0 needs RSTEN 0 (no reset path on the raw clock)");
`endif
endmodule
