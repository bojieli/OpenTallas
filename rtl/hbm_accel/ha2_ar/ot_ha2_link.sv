`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_ha2_link: ONE direction of an HA2 direct die-to-die link, sender S ->
// receiver R, with its credit return R -> S.
//
//   S core clock   flit from the endpoint's port arbiter (sent only with a
//                  credit) -> WSTG wire stages (endpoint -> SerDes macro,
//                  floorplan-derived) -> TX CDC: ot_link_afifo (Gray, 2-flop)
//   S PHY clock    serializer pacing: BITS_X100 / 100 wire bits a PHY cycle
//                  (lanes x lane rate x FEC efficiency x PHY period); a flit
//                  of PWB bits leaves when its bits have accrued (no burst
//                  credit beyond one flit) -> PHY / FEC / flight / CDR /
//                  deskew / decode latency: dly PHY cycles (SIMULATION
//                  channel element; the constant is cited/ESTIMATE)
//   RX CDC         ot_link_afifo, recovered (= S PHY) clock -> R core clock
//   R core clock   WSTG wire stages (SerDes macro -> endpoint) -> out.  The
//                  endpoint's receive buffer (RXD flits) is the credit pool.
//   credit return  R pops a flit -> WSTG stages -> afifo (R core -> R PHY)
//                  -> reverse PHY latency (dly_r) -> afifo (R PHY -> S core)
//                  -> WSTG stages -> cr_ret pulse at the sender's counter.
//                  (In silicon the credit rides the reverse direction's
//                  frames; its LATENCY is that of the reverse link, which is
//                  what is charged here.)
// Faults: any afifo overflow (cannot happen when the credit pool <= the
// FIFO depths; latched so a test proves it).
// ---------------------------------------------------------------------------
module ot_ha2_link #(
    parameter integer W         = 551,     // flit bits carried
    parameter integer PWB       = 551,     // wire bits charged per flit (payload + header)
    parameter integer WSTG      = 14,      // endpoint <-> SerDes wire stages, each side
    parameter integer BITS_X100 = 21165,   // wire payload bits per PHY cycle x 100
    parameter integer DMAX      = 256,
    parameter integer AW        = 5
) (
    input  wire         s_clk, s_rst_n, s_pclk, s_prst_n,
    input  wire         r_clk, r_rst_n, r_pclk, r_prst_n,
    input  wire [15:0]  dly, dly_r,
    // sender core side
    input  wire         in_valid,
    input  wire [W-1:0] in_flit,
    output wire         cr_ret,
    // receiver core side
    output wire         out_valid,
    output wire [W-1:0] out_flit,
    input  wire         r_credit,
    output wire         fault,
    output reg  [31:0]  stat_flits
);
    // ---- forward ---------------------------------------------------------------------------------------
    wire         w1_v;
    wire [W-1:0] w1_d;
    ot_ha2_delay #(.W(W), .D(WSTG)) u_wtx (.clk(s_clk), .rst_n(s_rst_n), .v_in(in_valid), .d_in(in_flit),
        .v_out(w1_v), .d_out(w1_d));
    wire tx_empty, tx_ovf, tx_full;
    wire [W-1:0] tx_head;
    wire [AW:0] tx_freed, tx_cnt;
    reg  tx_pop;
    ot_link_afifo #(.W(W), .AW(AW)) u_txcdc (.wclk(s_clk), .wrst_n(s_rst_n), .wr(w1_v), .wdata(w1_d),
        .wfull(tx_full), .wfreed(tx_freed), .ovf(tx_ovf), .rclk(s_pclk), .rrst_n(s_prst_n), .rd(tx_pop),
        .rempty(tx_empty), .rdata(tx_head), .rcount(tx_cnt));
    // serializer pacing
    integer acc;
    always @* tx_pop = !tx_empty && (acc + BITS_X100 >= PWB * 100);
    always @(posedge s_pclk or negedge s_prst_n)
        if (!s_prst_n) acc <= 0;
        else begin : pace
            integer a;
            a = acc + BITS_X100;
            if (a > PWB * 100) a = PWB * 100;
            if (tx_pop) a = a - PWB * 100;
            acc <= a;
        end
    wire         ph_v;
    wire [W-1:0] ph_d;
    ot_ha2_vdelay #(.W(W), .DMAX(DMAX)) u_phy (.clk(s_pclk), .rst_n(s_prst_n), .dly(dly), .v_in(tx_pop),
        .d_in(tx_head), .v_out(ph_v), .d_out(ph_d));
    wire rx_empty, rx_ovf, rx_full;
    wire [W-1:0] rx_head;
    wire [AW:0] rx_freed, rx_cnt;
    ot_link_afifo #(.W(W), .AW(AW)) u_rxcdc (.wclk(s_pclk), .wrst_n(s_prst_n), .wr(ph_v), .wdata(ph_d),
        .wfull(rx_full), .wfreed(rx_freed), .ovf(rx_ovf), .rclk(r_clk), .rrst_n(r_rst_n), .rd(!rx_empty),
        .rempty(rx_empty), .rdata(rx_head), .rcount(rx_cnt));
    ot_ha2_delay #(.W(W), .D(WSTG)) u_wrx (.clk(r_clk), .rst_n(r_rst_n), .v_in(!rx_empty), .d_in(rx_head),
        .v_out(out_valid), .d_out(out_flit));
    always @(posedge r_clk or negedge r_rst_n)
        if (!r_rst_n) stat_flits <= 0; else if (out_valid) stat_flits <= stat_flits + 1;
    // ---- credit return ---------------------------------------------------------------------------------
    wire c1_v;
    wire [0:0] c1_d;
    ot_ha2_delay #(.W(1), .D(WSTG)) u_cw1 (.clk(r_clk), .rst_n(r_rst_n), .v_in(r_credit), .d_in(1'b1),
        .v_out(c1_v), .d_out(c1_d));
    wire ca_empty, ca_ovf, ca_full;
    wire [0:0] ca_head;
    wire [AW+1:0] ca_freed, ca_cnt;
    ot_link_afifo #(.W(1), .AW(AW+1)) u_cacdc (.wclk(r_clk), .wrst_n(r_rst_n), .wr(c1_v), .wdata(1'b1),
        .wfull(ca_full), .wfreed(ca_freed), .ovf(ca_ovf), .rclk(r_pclk), .rrst_n(r_prst_n), .rd(!ca_empty),
        .rempty(ca_empty), .rdata(ca_head), .rcount(ca_cnt));
    wire cp_v;
    wire [0:0] cp_d;
    ot_ha2_vdelay #(.W(1), .DMAX(DMAX)) u_cphy (.clk(r_pclk), .rst_n(r_prst_n), .dly(dly_r), .v_in(!ca_empty),
        .d_in(1'b1), .v_out(cp_v), .d_out(cp_d));
    wire cb_empty, cb_ovf, cb_full;
    wire [0:0] cb_head;
    wire [AW+1:0] cb_freed, cb_cnt;
    ot_link_afifo #(.W(1), .AW(AW+1)) u_cbcdc (.wclk(r_pclk), .wrst_n(r_prst_n), .wr(cp_v), .wdata(1'b1),
        .wfull(cb_full), .wfreed(cb_freed), .ovf(cb_ovf), .rclk(s_clk), .rrst_n(s_rst_n), .rd(!cb_empty),
        .rempty(cb_empty), .rdata(cb_head), .rcount(cb_cnt));
    wire c2_d;
    ot_ha2_delay #(.W(1), .D(WSTG)) u_cw2 (.clk(s_clk), .rst_n(s_rst_n), .v_in(!cb_empty), .d_in(1'b1),
        .v_out(cr_ret), .d_out(c2_d));
    assign fault = tx_ovf | rx_ovf | ca_ovf | cb_ovf;
endmodule
