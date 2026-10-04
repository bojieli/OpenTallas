`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// HA2 (direct die-to-die all-reduce, accelerator (ours)) small primitives.
//
// ot_ha2_delay   D free-running register stages (no stall inside: flow control
//                is by credits upstream).  Written as a circular buffer so a
//                96-die simulation does not copy every stage every cycle; the
//                cycle behaviour is exactly D flop stages (input at cycle t is
//                the output at cycle t + D).  Priced as D x W flops.
// ot_ha2_vdelay  the same with a run-time depth (1 .. DMAX): the PHY / FEC
//                latency of one link direction, drawn per link per run.
//                SIMULATION channel element (stands for hard IP), not RTL to
//                be synthesised.
// ot_ha2_fifo    synchronous FWFT FIFO (flops), overflow latched (fail closed).
// ---------------------------------------------------------------------------
module ot_ha2_delay #(
    parameter integer W = 1,
    parameter integer D = 1
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v_in,
    input  wire [W-1:0] d_in,
    output wire         v_out,
    output wire [W-1:0] d_out
);
    generate if (D == 0) begin : g_pass
        assign v_out = v_in;
        assign d_out = d_in;
    end else begin : g_dly
        reg [W-1:0] mem [0:D-1];
        reg [D-1:0] vm;
        integer ptr;
        assign v_out = vm[ptr];
        assign d_out = mem[ptr];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin vm <= '0; ptr <= 0; end
            else begin
                vm[ptr] <= v_in;
                ptr <= (ptr == D - 1) ? 0 : ptr + 1;
            end
        always @(posedge clk) if (v_in) mem[ptr] <= d_in;
    end endgenerate
endmodule

module ot_ha2_vdelay #(
    parameter integer W    = 1,
    parameter integer DMAX = 256
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [15:0]  dly,          // 1 .. DMAX, static for the run
    input  wire         v_in,
    input  wire [W-1:0] d_in,
    output wire         v_out,
    output wire [W-1:0] d_out
);
    reg [W-1:0] mem [0:DMAX-1];
    reg [DMAX-1:0] vm;
    integer wp, rp;
    always @* rp = (wp + DMAX - integer'(dly)) % DMAX;
    assign v_out = vm[rp];
    assign d_out = mem[rp];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin vm <= '0; wp <= 0; end
        else begin
            vm[wp] <= v_in;
            wp <= (wp == DMAX - 1) ? 0 : wp + 1;
        end
    always @(posedge clk) if (v_in) mem[wp] <= d_in;
endmodule

module ot_ha2_fifo #(
    parameter integer W  = 8,
    parameter integer AW = 4
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         push,
    input  wire [W-1:0] din,
    input  wire         pop,
    output wire         empty,
    output wire [W-1:0] dout,
    output reg          ovf,
    output wire [AW:0]  count
);
    localparam integer D = 1 << AW;
    reg [W-1:0] mem [0:D-1];
    reg [AW:0] wp, rp;
    assign empty = wp == rp;
    assign dout  = mem[rp[AW-1:0]];
    assign count = wp - rp;
    wire full = count == D;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wp <= 0; rp <= 0; ovf <= 1'b0; end
        else begin
            if (push && !full) wp <= wp + 1'b1;
            if (push && full) ovf <= 1'b1;
            if (pop && !empty) rp <= rp + 1'b1;
        end
    always @(posedge clk) if (push && !full) mem[wp[AW-1:0]] <= din;
endmodule
