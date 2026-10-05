`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Plesiochronous crossing of a package-to-package link (gate K3, V4.1 rack).
//
// Every package runs its own PLL from a tray-local reference; a board or cable
// link between two packages is therefore plesiochronous: the receiver's clock
// differs from the transmitter's by up to +-100 ppm (IEEE 802.3 PHY tolerance;
// the bench also runs +-200 ppm).  A serial PHY transmits at a FIXED rate: the
// transmitter cannot see the receiver's buffer, so rate matching is open loop:
//
//   TX  (clk_tx)  offers one flit per cycle but leaves ONE IDLE slot every
//                 SKIP_EVERY cycles (the skip ordered set of PCIe/Ethernet PCS).
//                 A flit is written into the elastic buffer; an idle is not.
//   RX  (clk_rx)  reads a flit whenever the buffer holds one.
//
// The buffer is an asynchronous FIFO with Gray-coded pointers and SYNC-stage
// synchronisers.  With TX at most 1 - 1/SKIP_EVERY flits per TX cycle and RX
// reading one per RX cycle, the buffer cannot fill while
//      f_rx >= f_tx x (1 - 1/SKIP_EVERY),
// i.e. the idle rate must exceed the worst clock offset (200 ppm -> SKIP_EVERY
// <= 5000; the default 1024 leaves ~4.9x margin).  Overflow and underflow are
// still detected and latched (fail closed, never silent).
//
// Latency of a flit through the crossing: the write, SYNC RX cycles of pointer
// synchronisation, the read -- about SYNC + 2 RX cycles.  The 130 ns hop budgets
// 4 cycles of clock-domain crossing (configs/hardware/technology.json
// links.rom_board_serdes.latency_components_s.cdc).
// ---------------------------------------------------------------------------
module ot_rom_link_cdc #(
    parameter integer W          = 64,
    parameter integer AW         = 4,          // buffer of 2^AW flits
    parameter integer SYNC       = 2,
    parameter integer SKIP_EVERY = 1024
) (
    input  wire          clk_tx,
    input  wire          rst_tx_n,
    input  wire          tx_valid,            // a flit is offered this TX cycle
    input  wire [W-1:0]  tx_data,
    output wire          tx_slot,             // 1 = this cycle carries data if offered, 0 = forced idle
    output reg           ovf,                 // latched: a flit arrived to a full buffer (dropped)
    input  wire          clk_rx,
    input  wire          rst_rx_n,
    output reg           rx_valid,
    output reg  [W-1:0]  rx_data,
    output reg           unf                  // latched: never set by a correct design (read only when non-empty)
);
    localparam integer D = 1 << AW;
    reg [W-1:0] mem [0:D-1];

    // ---- TX domain -------------------------------------------------------------------------------------
    reg [31:0] slot_cnt;
    assign tx_slot = (slot_cnt != SKIP_EVERY - 1);
    always @(posedge clk_tx or negedge rst_tx_n)
        if (!rst_tx_n) slot_cnt <= 0;
        else slot_cnt <= (slot_cnt == SKIP_EVERY - 1) ? 0 : slot_cnt + 1;

    reg  [AW:0] wbin, wgray;
    reg  [AW:0] rgray_s [0:SYNC-1];
    wire [AW:0] rgray_tx = rgray_s[SYNC-1];
    wire [AW:0] wbin_n = wbin + 1'b1;
    wire [AW:0] wgray_n = wbin_n ^ (wbin_n >> 1);
    wire        full = (wgray_n == {~rgray_tx[AW:AW-1], rgray_tx[AW-2:0]});
    wire        wr = tx_valid && tx_slot;
    integer i;
    always @(posedge clk_tx or negedge rst_tx_n) begin
        if (!rst_tx_n) begin
            wbin <= 0; wgray <= 0; ovf <= 1'b0;
            for (i = 0; i < SYNC; i = i + 1) rgray_s[i] <= 0;
        end else begin
            rgray_s[0] <= rgray;
            for (i = 1; i < SYNC; i = i + 1) rgray_s[i] <= rgray_s[i-1];
            if (wr) begin
                if (full) ovf <= 1'b1;                   // open loop: a fixed-rate PHY cannot stall
                else begin
                    wbin <= wbin_n; wgray <= wgray_n;
                end
            end
        end
    end
    always @(posedge clk_tx) if (wr && !full) mem[wbin[AW-1:0]] <= tx_data;

    // ---- RX domain -------------------------------------------------------------------------------------
    reg  [AW:0] rbin, rgray;
    reg  [AW:0] wgray_s [0:SYNC-1];
    wire [AW:0] wgray_rx = wgray_s[SYNC-1];
    wire        empty = (rgray == wgray_rx);
    wire [AW:0] rbin_n = rbin + 1'b1;
    always @(posedge clk_rx or negedge rst_rx_n) begin
        if (!rst_rx_n) begin
            rbin <= 0; rgray <= 0; rx_valid <= 1'b0; unf <= 1'b0;
            for (i = 0; i < SYNC; i = i + 1) wgray_s[i] <= 0;
        end else begin
            wgray_s[0] <= wgray;
            for (i = 1; i < SYNC; i = i + 1) wgray_s[i] <= wgray_s[i-1];
            rx_valid <= !empty;
            if (!empty) begin
                rx_data <= mem[rbin[AW-1:0]];
                rbin <= rbin_n; rgray <= rbin_n ^ (rbin_n >> 1);
            end
        end
    end
endmodule
