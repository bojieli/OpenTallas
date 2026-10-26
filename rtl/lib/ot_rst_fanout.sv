`timescale 1ns/1ps
`default_nettype none
// HBM-SVGREL8 2026-10-20: second-level reset leaves under an ot_rst_relay leaf (same clock).  rst_n_in is ALREADY
// synchronous to clk (an ot_rst_relay / ot_rst_fanout output), so one KEPT flop stage per leaf is a clean synchronous
// release (assert stays asynchronous and immediate); release = +1 clk edge.  Each leaf drives <= 32 reset pins.  The
// copies are logically identical: (* keep *) + the ORFS ot_keep_regs.tcl hook keep them as separate flop cells.
module ot_rst_fanout #(parameter integer N=4)(
 input wire clk,rst_n_in,output wire[N-1:0]rst_n
);
 (* keep="true",dont_touch="true" *) reg[N-1:0]q;
 always @(posedge clk or negedge rst_n_in)if(!rst_n_in)q<={N{1'b0}};else q<={N{1'b1}};
 assign rst_n=q;
endmodule
`default_nettype wire
