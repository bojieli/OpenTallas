// Additive observable-state forms; no pointer/reset/latency changes.
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
module ot_ha2_delay_quiet #(
    parameter integer W = 1,
    parameter integer D = 1
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v_in,
    input  wire [W-1:0] d_in,
    output wire quiet,
    output wire         v_out,
    output wire [W-1:0] d_out
);
    generate if (D == 0) begin : g_pass
        assign quiet = !v_in;
        assign v_out = v_in;
        assign d_out = d_in;
    end else begin : g_dly
        reg [W-1:0] mem [0:D-1];
        reg [D-1:0] vm;
        integer ptr;
        assign quiet = !(|vm);
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

`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_link_afifo: asynchronous FIFO for the die-to-die link layer (W15).
//
// Dual-clock FIFO with Gray-coded pointers and SYNC-flop synchronisers (the
// standard Cummings construction).  Pointers advance by at most one per
// cycle on each side, so the synchronised Gray pointer is always a value the
// other side actually held (single-bit change per step).
//
// Write side (wclk):  wr pushes wdata; wfull is conservative (from the
//                     synchronised read pointer).  A push while full is
//                     dropped and latched in ovf (fail closed: callers size
//                     the FIFO so that it cannot happen, and a test proves it).
//                     wfreed is the number of entries the read side released
//                     since the previous wclk cycle, as seen through the
//                     synchroniser -- the credit return of a hub-side counter.
// Read side  (rclk):  first-word fall-through head (rdata valid while
//                     !rempty); rd pops it.
//
// Latency of an entry: the write edge, SYNC read-clock edges for the Gray
// write pointer, then the head is visible -- between SYNC and SYNC + 1 read
// cycles after the write, depending on the phase of the two clocks.  That
// phase dependence is the non-determinism the release stage of ot_link_rx
// removes.
// ---------------------------------------------------------------------------
module ot_link_afifo_quiet #(
    parameter integer W    = 64,
    parameter integer AW   = 4,           // 2^AW entries
    parameter integer SYNC = 2
) (
    input  wire          wclk,
    input  wire          wrst_n,
    input  wire          wr,
    input  wire [W-1:0]  wdata,
    output wire wempty,
    output wire          wfull,
    output reg  [AW:0]   wfreed,
    output reg           ovf,
    input  wire          rclk,
    input  wire          rrst_n,
    input  wire          rd,
    output wire          rempty,
    output wire [W-1:0]  rdata,
    output wire [AW:0]   rcount           // entries visible to the read side
);
    localparam integer D = 1 << AW;
    reg [W-1:0] mem [0:D-1];

    function automatic [AW:0] g2b(input [AW:0] g);
        integer k;
        begin
            g2b[AW] = g[AW];
            for (k = AW - 1; k >= 0; k = k - 1) g2b[k] = g2b[k+1] ^ g[k];
        end
    endfunction

    // ---- write domain ----------------------------------------------------------------------------------
    reg  [AW:0] wbin, wgray, rbin_seen;
    reg  [AW:0] rgray_s [0:SYNC-1];
    wire [AW:0] rgray_w = rgray_s[SYNC-1];
    wire [AW:0] wbin_n = wbin + 1'b1;
    wire [AW:0] wgray_n = wbin_n ^ (wbin_n >> 1);
    assign wempty = wgray == rgray_w;
    assign wfull = (wgray == {~rgray_w[AW:AW-1], rgray_w[AW-2:0]});
    wire        push = wr && !wfull;
    wire [AW:0] rbin_w = g2b(rgray_w);
    integer i;
    always @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) begin
            wbin <= 0; wgray <= 0; ovf <= 1'b0; rbin_seen <= 0; wfreed <= 0;
            for (i = 0; i < SYNC; i = i + 1) rgray_s[i] <= 0;
        end else begin
            rgray_s[0] <= rgray;
            for (i = 1; i < SYNC; i = i + 1) rgray_s[i] <= rgray_s[i-1];
            wfreed <= rbin_w - rbin_seen;
            rbin_seen <= rbin_w;
            if (wr && wfull) ovf <= 1'b1;
            if (push) begin
                wbin <= wbin_n; wgray <= wgray_n;
            end
        end
    end
    always @(posedge wclk) if (push) mem[wbin[AW-1:0]] <= wdata;

    // ---- read domain -----------------------------------------------------------------------------------
    reg  [AW:0] rbin, rgray;
    reg  [AW:0] wgray_s [0:SYNC-1];
    wire [AW:0] wgray_r = wgray_s[SYNC-1];
    assign rempty = (rgray == wgray_r);
    assign rdata  = mem[rbin[AW-1:0]];
    assign rcount = g2b(wgray_r) - rbin;
    wire [AW:0] rbin_n = rbin + 1'b1;
    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin
            rbin <= 0; rgray <= 0;
            for (i = 0; i < SYNC; i = i + 1) wgray_s[i] <= 0;
        end else begin
            wgray_s[0] <= wgray;
            for (i = 1; i < SYNC; i = i + 1) wgray_s[i] <= wgray_s[i-1];
            if (rd && !rempty) begin
                rbin <= rbin_n; rgray <= rbin_n ^ (rbin_n >> 1);
            end
        end
    end
endmodule
