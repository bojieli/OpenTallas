`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// TOK-QK/C 2026-10-24 (KV boot fix C2): the ONE clock-domain crossing of a SerDes FDI half, placed AT the PHY.
//
// The host SerDes PHY (ot_qfd_serdes_112g_x6_phy halves in sys_SW / sys_SE) runs on its own clock clk_phy (0.959 GHz);
// every on-die transport lane, the hub_Wi deskew join (ot_fdi_join2) and the host link adapter run on the core clock
// (1.2 GHz).  This module is the only crossing of either direction (no other synchroniser on the FDI path):
//   RX  PHY rx_v/rx_flit (clk_phy) -> pin capture -> ot_async_fifo (Gray pointers, 2-flop synchronisers, valid + data
//       written together as one entry) -> core-side output register -> core lanes.  The core side reads every cycle
//       the FIFO is non-empty (core faster than the PHY: the FIFO cannot fill; DEPTH covers sync latency + jitter).
//   TX  core lanes -> ot_async_fifo (written together) -> PHY-side output register -> PHY tx_v/tx_flit (clk_phy).
//       The writer must not exceed the PHY's flit rate: the host adapter's transmit slots are paced on the core clock
//       by ot_fdi_tx_pace (NUM/DEN of core cycles < clk_phy / clk_core), so the FIFO stays within a few entries;
//       DEPTH covers the pacing burst + sync latency.  There is no ready back to the adapter (static rate).
//   tx_up  PHY status level -> 2-flop synchroniser -> core (single-bit level: a bare 2-flop synchroniser is correct).
//   reset  link_rst_n (core-domain level from the HOST link reset lane) -> ot_reset_sync on clk_phy = p_rst_n (the PHY
//       reset; its async input is the only false path, as every reset synchroniser) ; both FIFOs are flushed by it.
// Rate mismatch / flow control is absorbed only here and in the adapter's own sequence/credit protocol (off-die
// boundary, owner rule): no on-die transport lane changes clock or carries backpressure.  A lost word (a FIFO written
// while full, which the pacing excludes) is a sequence gap the far adapter reports (f_seq): no extra fault port.
//
// SDC intent (die / partition STA): clk and clk_phy are asynchronous.  The only clk <-> clk_phy arcs are inside the two
// ot_async_fifo instances and the tx_up / reset synchronisers; constrain exactly those, as the repo's CDC FIFOs
// (physical/ref_tile/dsfd_vm_fcn_m5/clock.sdc proc ot_fh_cdc):
//   Gray pointer / online -> first synchroniser flop : max datapath delay 0.5 x T(faster clock) (bus skew), no hold
//   FIFO storage (write domain) -> read-domain register : max datapath delay 1.0 x T(read clock) - 60 ps, no hold
//   tx_up / reset async inputs -> first synchroniser flop : false path (single-bit level; reset synchroniser)
// (OpenSTA: set_max_delay -ignore_clock_latency + set_false_path -hold on those arcs; never set_clock_groups.)
// Latency (unit bench tools/qwen_layerbench/kv_dieslice/fdicdc): see that bench's report.
// ---------------------------------------------------------------------------------------------------------------------
module ot_fdi_phy_cdc #(
    parameter integer W = 522,
    parameter integer DEPTH = 8          // power of two >= 4 (ot_async_fifo)
) (
    // core side (partition clock)
    input  wire         clk,
    input  wire         link_rst_n,
    input  wire         c_tx_v,
    input  wire [W-1:0] c_tx_d,
    output reg          c_rx_v,
    output reg  [W-1:0] c_rx_d,
    output wire         c_tx_up,
    // PHY side (clk_phy)
    input  wire         clk_phy,
    output wire         p_rst_n,
    output reg          p_tx_v,
    output reg  [W-1:0] p_tx_d,
    input  wire         p_rx_v,
    input  wire [W-1:0] p_rx_d,
    input  wire         p_tx_up
);
    wire c_rst_n;
    ot_reset_sync u_crs (.clk(clk), .async_rst_n(link_rst_n), .sync_rst_n(c_rst_n));
    ot_reset_sync u_prs (.clk(clk_phy), .async_rst_n(link_rst_n), .sync_rst_n(p_rst_n));
    // ---- RX: PHY -> core ----
    reg          rq_v;
    reg  [W-1:0] rq_d;
    always @(posedge clk_phy) rq_d <= p_rx_d;                          // capture at the macro pins, no logic before it
    always @(posedge clk_phy or negedge p_rst_n) if (!p_rst_n) rq_v <= 1'b0; else rq_v <= p_rx_v;
    wire         rx_wr_rdy, rx_rd_v, rx_wovf, rx_rund;
    wire [W-1:0] rx_rd_d;
    ot_async_fifo #(.WIDTH(W), .DEPTH(DEPTH)) u_rx (
        .wr_clk(clk_phy), .wr_rst_n(link_rst_n), .wr_valid(rq_v), .wr_ready(rx_wr_rdy), .wr_data(rq_d), .wr_overflow(rx_wovf),
        .rd_clk(clk), .rd_rst_n(link_rst_n), .rd_valid(rx_rd_v), .rd_ready(1'b1), .rd_data(rx_rd_d), .rd_underflow(rx_rund));
    always @(posedge clk) c_rx_d <= rx_rd_d;
    always @(posedge clk or negedge c_rst_n) if (!c_rst_n) c_rx_v <= 1'b0; else c_rx_v <= rx_rd_v;
    // ---- TX: core -> PHY ----
    wire         tx_wr_rdy, tx_rd_v, tx_wovf, tx_rund;
    wire [W-1:0] tx_rd_d;
    ot_async_fifo #(.WIDTH(W), .DEPTH(DEPTH)) u_tx (
        .wr_clk(clk), .wr_rst_n(link_rst_n), .wr_valid(c_tx_v), .wr_ready(tx_wr_rdy), .wr_data(c_tx_d), .wr_overflow(tx_wovf),
        .rd_clk(clk_phy), .rd_rst_n(link_rst_n), .rd_valid(tx_rd_v), .rd_ready(1'b1), .rd_data(tx_rd_d), .rd_underflow(tx_rund));
    always @(posedge clk_phy) p_tx_d <= tx_rd_d;
    always @(posedge clk_phy or negedge p_rst_n) if (!p_rst_n) p_tx_v <= 1'b0; else p_tx_v <= tx_rd_v;
    // ---- tx_up: PHY status level -> core ----
    (* async_reg = "true" *) reg [1:0] up_s;
    always @(posedge clk or negedge c_rst_n) if (!c_rst_n) up_s <= 2'b00; else up_s <= {up_s[0], p_tx_up};
    assign c_tx_up = up_s[1];
`ifndef SYNTHESIS
    // a word offered while the FIFO cannot take it is lost (the far adapter then reports a sequence gap)
    integer n_rx_lost = 0, n_tx_lost = 0, n_rx = 0, n_tx = 0;
    always @(posedge clk_phy) if (p_rst_n && rq_v) begin
        n_rx = n_rx + 1;
        if (!rx_wr_rdy) begin n_rx_lost = n_rx_lost + 1; $error("ot_fdi_phy_cdc %m: RX word lost (FIFO full / offline)"); end
    end
    always @(posedge clk) if (c_rst_n && c_tx_v) begin
        n_tx = n_tx + 1;
        if (!tx_wr_rdy) begin n_tx_lost = n_tx_lost + 1; $error("ot_fdi_phy_cdc %m: TX word lost (FIFO full / offline)"); end
    end
`endif
endmodule
