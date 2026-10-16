`timescale 1ns/1ps
`default_nettype none
// Half-cycle-read variant of ot_s81_static_lane_cross (S-ELEM CFIFO-HOLD 2026-10-16, closure-first).
// Same write side, epoch identity and Gray epoch check, same fixed calendar, same fault semantics.
// Why: in dsfd_cfifo_crs the read register o sat on root r_ck (cr_s) while the bank is on w_ck (xf) and the
// consumer on o_ck (cr). Each full-cycle hop between DIFFERENT roots carries the die-skew hold reserve (100 ps),
// and the zero-logic bank->o and o->x hops were the hold flood (gate 4_1_cts: 32k of 38.6k hold buffers;
// route EARLY_FAIL_HOLD at 21.7k). Here both cross-root hops are half-cycle by construction:
//   bank (posedge w_ck) -> h (negedge r_ck)         hold check half a period away
//   h    (negedge r_ck) -> o (posedge o_ck)         hold check half a period away
// The read select is one-hot, registered on negedge r_ck one full period before h uses it (predicted from
// rc_{j-1}+1 = rc_j), so the wide-fanout select is a full-cycle path. h at negedge j+1/2 holds exactly what the
// base module's o captured at posedge j+1; o (posedge o_ck, phase 0 with r_ck) at edge j+1 therefore equals the
// base o at edge j+1: zero added edges, zero calendar change. o has no reset: after an asynchronous reset
// assertion it reaches zero within two edges (warm is reset immediately, the select then clears); the compiler
// holds reset for the full trunk calendar, and every word after release is identical to the base module.
module ot_s81_static_lane_cross_hr #(
    parameter integer W=1101, DEPTH=8, OFFSET=4, EPOCH_SHIFT=0,
    parameter integer AW=$clog2(DEPTH)
)(
    input wire w_ck, w_rst_n,
    input wire [W-1:0] i,
    input wire r_ck, r_rst_n,
    input wire o_ck,
    output reg [W-1:0] o,
    output reg fault
);
    reg [W-1:0] bank [0:DEPTH-1];
    reg [AW:0] identity [0:DEPTH-1];
    reg [AW:0] wc, rc;
    reg [AW:0] warm;
    // r5b: the observed epoch is a dedicated Gray register (wgr == gray(wc) at every instant, same edges as the
    // base module's combinational wc^(wc>>1)). It keeps the cross-root wg1 capture off wc's bank-decode fanout
    // tree, whose long max path left no setup room for the hold buffers on wc->wg1 (gate r5 4_1_cts chunk 1:
    // RSZ stuck 9,000 iterations at -14.3 ps on u_x.u_cross.wg1[1]).
    reg [AW:0] wgr;
    wire [AW:0] wc_n = wc+1'b1;
    always @(posedge w_ck or negedge w_rst_n)
        if (!w_rst_n) wgr <= 0;
        else wgr <= wc_n^(wc_n>>1);
    wire [AW:0] wg=wgr;
    (* async_reg="true" *) reg [AW:0] wg1,wg2,wg3;
    wire [AW:0] epoch_expected=rc-2+EPOCH_SHIFT;
    wire [AW:0] epoch_gray=epoch_expected^(epoch_expected>>1);
    always @(posedge r_ck) begin wg1<=wg; wg2<=wg1; wg3<=wg2; end
    wire [AW:0] expected = rc-OFFSET+EPOCH_SHIFT;
    always @(posedge w_ck or negedge w_rst_n)
        if (!w_rst_n) wc <= 0;
        else begin
            bank[wc[AW-1:0]] <= i;
            identity[wc[AW-1:0]] <= wc;
            wc <= wc+1'b1;
        end
    always @(posedge r_ck or negedge r_rst_n)
        if (!r_rst_n) begin rc<=0; warm<=0; fault<=0; end
        else begin
            rc <= rc+1'b1;
            if (warm < OFFSET) warm<=warm+1'b1;
            else if (identity[expected[AW-1:0]] != expected || wg3 != epoch_gray) fault<=1;
        end
    // negedge j-1/2 sees rc_{j-1}, warm_{j-1}: the base o at edge j+1 reads slot rc_j-OFFSET+EPOCH_SHIFT
    // = rc_{j-1}+1-OFFSET+EPOCH_SHIFT and is non-zero iff warm_j >= OFFSET iff warm_{j-1} >= OFFSET-1.
`ifdef OT_S81_HR_MUT_SEL
    wire [AW:0] nxt = rc-OFFSET+EPOCH_SHIFT;
`else
    wire [AW:0] nxt = rc+1'b1-OFFSET+EPOCH_SHIFT;
`endif
    wire go = (warm >= OFFSET-1);
    reg [DEPTH-1:0] sel;
    integer k;
    always @(negedge r_ck) for (k=0;k<DEPTH;k=k+1) sel[k] <= go && (nxt[AW-1:0] == k);
    reg [W-1:0] rd_;
    always @* begin rd_ = {W{1'b0}}; for (k=0;k<DEPTH;k=k+1) rd_ = rd_ | (bank[k] & {W{sel[k]}}); end
    reg [W-1:0] h;
    always @(negedge r_ck) h <= rd_;
`ifdef OT_S81_HR_MUT_NOSTAGE
    always @* o = h;
`else
    always @(posedge o_ck) o <= h;
`endif
`ifndef SYNTHESIS
    initial if (W<1 || DEPTH<4 || (DEPTH & (DEPTH-1))!=0 || OFFSET<2 || OFFSET>DEPTH-2)
        $fatal(1,"static crossing requires power-of-two depth and 2 <= offset <= depth-2");
`endif
endmodule
`default_nettype wire
