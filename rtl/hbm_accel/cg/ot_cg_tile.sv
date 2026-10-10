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
    parameter integer MUT_LATE = 0
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
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wq <= 1'b1; cnt <= HOLD[CW-1:0]; wl <= {(MUT_LATE+1){1'b1}}; end
        else begin
            wq <= cgi;
            wl[0] <= wq;
            for (i = 1; i <= MUT_LATE; i = i + 1) wl[i] <= wl[i-1];
            cnt <= w_eff ? HOLD[CW-1:0] : ((cnt != 0) ? cnt - 1'b1 : cnt);
        end
    assign w_eff = (MUT_LATE == 0) ? wq : wl[MUT_LATE];
    wire en = w_eff | (cnt != 0) | !rst_n;
    assign cgo = wq;
    ot_hdc_cg u_cg (.clk(clk), .en(en), .gclk(gclk));
endmodule
