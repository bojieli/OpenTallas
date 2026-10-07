`timescale 1ns/1ps
// ot_s81ph_rfifo (CLAUDE S81-PH): small register FIFO, registered status (no combinational path from push/pop to
// the flags), first word fall-through from a register array.  room2 = at least 2 free entries (for producers that
// see the flag one cycle late).  Overflow (push when full) / underflow are sticky faults.
module ot_s81ph_rfifo #(
    parameter integer W = 8,
    parameter integer D = 4,
    parameter integer AW = (D > 1) ? $clog2(D) : 1,
    parameter integer R2RST = (D >= 2)    // room2 value during reset (0: a producer may not hand over words before release)
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         push,
    input  wire [W-1:0] wd,
    input  wire         pop,
    output wire         hv,
    output wire [W-1:0] hd,
    output reg          room,       // at least 1 free entry
    output reg          room2,      // at least 2 free entries
    output reg          fault
);
    reg [W-1:0] m [0:D-1];
    reg [AW-1:0] wp, rp;
    reg [AW:0] n;
    reg ne;
    wire do_pop = pop && ne;
    wire [AW:0] n_n = n + (push ? 1'b1 : 1'b0) - (do_pop ? 1'b1 : 1'b0);
    assign hv = ne;
    assign hd = m[rp];
    always @(posedge clk) if (push) m[wp] <= wd;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wp <= 0; rp <= 0; n <= 0; ne <= 1'b0; room <= 1'b1; room2 <= R2RST; fault <= 1'b0; end
        else begin
            if (push) wp <= (wp == D - 1) ? 0 : wp + 1'b1;
            if (do_pop) rp <= (rp == D - 1) ? 0 : rp + 1'b1;
            n <= n_n; ne <= n_n != 0; room <= n_n < D; room2 <= n_n + 2 <= D;
            if ((push && n == D && !do_pop) || (pop && !ne)) fault <= 1'b1;
        end
endmodule
