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
module ot_link_afifo #(
    parameter integer W    = 64,
    parameter integer AW   = 4,           // 2^AW entries
    parameter integer SYNC = 2,
    // RCOPY > 0 (S-ELEM-PQ 2026-10-15, host_c route: u_hx rbin[1] drove 8,230 read-mux loads): the head read selects
    // each ceil(W/RCOPY)-bit slice with its own kept copy of the read address, loaded with rbin on the same edge.
    parameter integer RCOPY = 0
) (
    input  wire          wclk,
    input  wire          wrst_n,
    input  wire          wr,
    input  wire [W-1:0]  wdata,
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

`ifdef OT_S81_HOST_PHASESAFE
    // Low-source lockups defer every pointer transition until the source's
    // falling edge. Related 1:1 and 3:4 positive edges cannot race this seam.
    reg [AW:0] wgray_seam, rgray_seam;
    always @* if (!wrst_n) wgray_seam='0; else if (!wclk) wgray_seam=wgray;
    always @* if (!rrst_n) rgray_seam='0; else if (!rclk) rgray_seam=rgray;
`else
    wire [AW:0] wgray_seam=wgray, rgray_seam=rgray;
`endif
    // ---- write domain ----------------------------------------------------------------------------------
    reg  [AW:0] wbin, wgray, rbin_seen;
    reg  [AW:0] rgray_s [0:SYNC-1];
    wire [AW:0] rgray_w = rgray_s[SYNC-1];
    wire [AW:0] wbin_n = wbin + 1'b1;
    wire [AW:0] wgray_n = wbin_n ^ (wbin_n >> 1);
    assign wfull = (wgray == {~rgray_w[AW:AW-1], rgray_w[AW-2:0]});
    wire        push = wr && !wfull;
    wire [AW:0] rbin_w = g2b(rgray_w);
    integer i;
    always @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) begin
            wbin <= 0; wgray <= 0; ovf <= 1'b0; rbin_seen <= 0; wfreed <= 0;
            for (i = 0; i < SYNC; i = i + 1) rgray_s[i] <= 0;
        end else begin
            rgray_s[0] <= rgray_seam;
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
    wire [AW:0] rbin_n = rbin + 1'b1;
    reg  [AW:0] wgray_s [0:SYNC-1];
    wire [AW:0] wgray_r = wgray_s[SYNC-1];
    assign rempty = (rgray == wgray_r);
    wire [W-1:0] raw_rdata;
    localparam integer RS = (RCOPY > 0) ? (W + RCOPY - 1) / RCOPY : W;
    if (RCOPY > 0) begin : g_rcopy
        (* keep *) reg [RCOPY*AW-1:0] rbin_c;
        always @(posedge rclk or negedge rrst_n)
            if (!rrst_n) rbin_c <= '0;
            else if (rd && !rempty) for (int k = 0; k < RCOPY; k++)
`ifdef OT_LINK_AFIFO_MUT_RCOPY
                if (k != 0) rbin_c[AW*k +: AW] <= rbin_n[AW-1:0];      // negative control: slice 0 copy stalls
`else
                rbin_c[AW*k +: AW] <= rbin_n[AW-1:0];
`endif
        genvar gs;
        for (gs = 0; gs < RCOPY; gs = gs + 1) begin : g_s
            localparam integer LO = gs * RS, HI = ((gs + 1) * RS > W) ? W : (gs + 1) * RS;
            if (LO < W) begin : g_on
                wire [W-1:0] row = mem[rbin_c[AW*gs +: AW]];
                assign raw_rdata[HI-1:LO] = row[HI-1:LO];
            end
        end
    end else begin : g_r1
        assign raw_rdata  = mem[rbin[AW-1:0]];
    end
`ifdef OT_S81_HOST_PHASESAFE
    reg [W-1:0] head_seam;
    always @* if (rclk) head_seam=raw_rdata;
    assign rdata=head_seam;
`else
    assign rdata=raw_rdata;
`endif
    assign rcount = g2b(wgray_r) - rbin;
    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin
            rbin <= 0; rgray <= 0;
            for (i = 0; i < SYNC; i = i + 1) wgray_s[i] <= 0;
        end else begin
            wgray_s[0] <= wgray_seam;
            for (i = 1; i < SYNC; i = i + 1) wgray_s[i] <= wgray_s[i-1];
            if (rd && !rempty) begin
                rbin <= rbin_n; rgray <= rbin_n ^ (rbin_n >> 1);
            end
        end
    end
endmodule
