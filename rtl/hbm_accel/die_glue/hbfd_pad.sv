`timescale 1ns/1ps
// TW5-BANKLATDIE 10-19: HBM d4g die LANE PAD -- N fixed register stages on a narrow die lane (VM bank request lanes,
// write-done return lanes, IDX hub/selector control lanes), inserted by tools/hbm_die_v16/d4g_layers/l12_banklat.py so a
// fixed-latency VM bank client's round trip equals its hardened latency budget on every bank (d4g_bank_latency.py LAT
// class).  Static, fixed latency: o = i delayed by N edges of ck; no valid/ready, no credit, no backpressure.
// Ports as the die relay family (hbfd_rly_<W>_<flow>): ck = the lane's regional clock, rs = asynchronous active-low
// clear (every stage flop resets to 0, as the relay classes: a request lane's valid bit is 0 after reset).
// Core = rtl/hdc/ot_hdc_delay.sv (RESET 1).  One SYNTH view per (W, N); placed by the die generator at the lane end.
`default_nettype none
module hbfd_pad #(
    parameter integer W = 17,
    parameter integer N = 1
) (
    input  wire         ck,
    input  wire         rs,
    input  wire [W-1:0] i,
    output wire [W-1:0] o
);
    ot_hdc_delay #(.W(W), .D(N), .RESET(1)) u_dly (.clk(ck), .rst_n(rs), .d(i), .q(o));
endmodule
`default_nettype wire
