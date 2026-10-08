`timescale 1ns/1ps
// ot_s81ph_coll_rstc (CLAUDE S81-PH, 2026-10-06): die reset controller of the S81 collective slab.
//   por_n (async, active low, die pin) and PLL lock gate everything: while por_n is low or lock is low every reset
//   output is asserted ASYNCHRONOUSLY (the outputs are flops cleared by !(por_n & lock)).  The sequencer runs on
//   refclk (the only clock that is clean before lock): por_n release and lock are 2-flop synchronised to refclk;
//   after lock has been seen continuously for LOCK_HOLD refclk cycles the domain resets are released in order
//   stream, serial, hbm, GAP refclk cycles apart.  Release (deassertion) is synchronised in each receiving domain
//   by its consumer (every S81 glue block / slab has its own 2-flop reset synchroniser), as is the collective's own
//   stream logic (rst_s below).  A lock loss re-asserts everything and restarts the sequence.
//   pd (PLL power-down / reset) = !por_n.
module ot_s81ph_coll_rstc #(
    parameter integer LOCK_HOLD = 64,
    parameter integer GAP = 8
) (
    input  wire refclk,
    input  wire por_n,
    input  wire lock,
    output wire pll_pd,
    output reg  rst_stream_n,
    output reg  rst_serial_n,
    output reg  rst_hbm_n,
    output wire [2:0] seq_state
);
    localparam integer CB = $clog2(LOCK_HOLD + 3 * GAP + 2);
`ifdef OT_S81PH_MUT_SYNCLOCK
    wire arst_n = por_n;                                   // negative control: lock loss only seen synchronously
`else
    wire arst_n = por_n & lock;
`endif
    reg  [1:0] ps, ls;
    reg  [CB-1:0] c;
    assign pll_pd = !por_n;
    always @(posedge refclk or negedge por_n)
        if (!por_n) ps <= 2'b00; else ps <= {ps[0], 1'b1};
    always @(posedge refclk or negedge arst_n)
        if (!arst_n) ls <= 2'b00; else ls <= {ls[0], 1'b1};
    wire up = ps[1] & ls[1];
    always @(posedge refclk or negedge arst_n) begin
        if (!arst_n) begin
            c <= 0; rst_stream_n <= 1'b0; rst_serial_n <= 1'b0; rst_hbm_n <= 1'b0;
        end else if (!up) begin
            c <= 0; rst_stream_n <= 1'b0; rst_serial_n <= 1'b0; rst_hbm_n <= 1'b0;
        end else begin
            if (c != LOCK_HOLD + 2 * GAP + 1) c <= c + 1'b1;
            if (c == LOCK_HOLD)           rst_stream_n <= 1'b1;
`ifdef OT_S81PH_MUT_ORDER
            if (c == LOCK_HOLD - GAP)     rst_serial_n <= 1'b1;   // negative control: serial before stream
`else
            if (c == LOCK_HOLD + GAP)     rst_serial_n <= 1'b1;
`endif
            if (c == LOCK_HOLD + 2 * GAP) rst_hbm_n <= 1'b1;
        end
    end
    assign seq_state = {rst_hbm_n, rst_serial_n, rst_stream_n};
endmodule
