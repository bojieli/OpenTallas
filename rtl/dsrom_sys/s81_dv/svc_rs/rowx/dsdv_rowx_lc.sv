`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-ROWX3 (2026-10-26): LANDED CROSSING of the rank-order row transport (one per receiving link port of
// dsdv_rowx_xm).  The incoming beat lands in a pin flop, then in a D-deep landing FIFO; the consumer pops on ITS OWN
// static slot schedule (never on arrival), so the arrival may jitter by up to the landing depth without changing any
// downstream cycle.  No credit, no ready: a pop from an empty FIFO (the word missed its booked slot) and a push into a
// full one are sticky faults (checks only, they never reschedule) -- the compiler books the pop
// >= the worst-case arrival + 2 (pin flop + FIFO write).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_rowx_lc #(parameter integer W = 512, parameter integer D = 16) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          i_v,
    input  wire [W-1:0]  i_d,
    input  wire          pop,
    output wire [W-1:0]  o_d,          // FIFO head (valid when the pop is in its booked slot)
    output reg           f_late,       // sticky: pop with nothing landed
    output reg           f_ovf         // sticky: landing FIFO overflow
);
    localparam integer AW = $clog2(D);
    reg iv; reg [W-1:0] id;                                  // pin flops
    always @(posedge clk or negedge rst_n) if (!rst_n) iv <= 1'b0; else iv <= i_v;
    always @(posedge clk) id <= i_d;
    reg [W-1:0] m [0:D-1];
    reg [AW-1:0] wp, rp; reg [AW:0] n;
    wire emp = n == 0, ful = n == (AW+1)'(D);
    wire do_pop = pop && !emp, do_push = iv && (!ful || do_pop);
    assign o_d = emp ? {W{1'b0}} : m[rp];
    always @(posedge clk) if (do_push) m[wp] <= id;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wp <= 0; rp <= 0; n <= 0; f_late <= 1'b0; f_ovf <= 1'b0; end
        else begin
            if (do_push) wp <= (wp == AW'(D - 1)) ? '0 : wp + 1'b1;
            if (do_pop)  rp <= (rp == AW'(D - 1)) ? '0 : rp + 1'b1;
            n <= n + (AW+1)'(do_push) - (AW+1)'(do_pop);
            if (pop && emp) f_late <= 1'b1;
            if (iv && ful && !do_pop) f_ovf <= 1'b1;
        end
endmodule
