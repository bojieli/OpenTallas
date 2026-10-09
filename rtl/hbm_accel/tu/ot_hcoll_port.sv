`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hcoll_port: ONE port slice of the switched-tier collective endpoint, hardened once and replicated 8x in the
// per-port split of hfd_coll (stream hbm-coll-rtl, 2026-10-08; ot_hbm_accel_tu_endpoint_ps).  pclk = clk (SYNCPHY).
// Holds what ot_hbm_accel_tu_endpoint_sr keeps per port: the partial / result transmit queues (SRAM), the arbiter
// (partial > result) with the switch-ingress credit counter, the TX wire stages (SRAM delay), the serializer pacing,
// the RX wire stages (SRAM delay) and the receive buffer (SRAM, 2^RXAW = the switch-egress credit pool).
// 18 ot_sram_1r1w_128x256 macros (qp 3, qr 3, wtx 3, wrx 3, rb 6).
// Every input lands in a flop with no logic before it and every output leaves a flop:
//   q*_push / q*_din -> the queues' write pin flops;  sw_cr_ret, ph_rx_*, rb_cr -> input flops (+1 edge each);
//   ph_tx_* / stall / fault -> output flops (+1 edge);  the receive-buffer head is EXPORTED with credit flow
//   (ot_hcoll_sfifo_x: rb_v / rb_d one beat per word, rb_cr one credit per consumer slot freed, K = 8 consumer slots).
// ---------------------------------------------------------------------------
module ot_hcoll_port #(
    parameter integer PWT = 545,
    parameter integer QAW = 7,
    parameter integer RXAW = 8,
    parameter integer WSTG = 14,
    parameter integer BITS_X100 = 72000,
    parameter integer PWB = 545,
    parameter integer SWCRED = 256,
    parameter integer K = 8,
    // struct-close 2026-10-09 (DRV6 re-judge: coll_port2_rows -403.8 at the IO reference; ph_rx_flit -> rxf_p I2R 181 ps
    // worse): RXPIN = 1 adds a PIN register stage on ph_rx_v / ph_rx_flit (keep_hierarchy, placed at the PHY pins) before
    // the input flops, so the 545-bit input wire is split across two stages.  +1 edge on the receive path; the RX credit
    // pool (2^RXAW = 256 switch-egress credits) absorbs it.  0 = unchanged.
    parameter integer RXPIN = `ifdef OT_HCOLL_RXPIN 1 `else 0 `endif
) (
    input  wire           clk,
    input  wire           rst_n,
    input  wire           qp_push,
    input  wire [PWT-1:0] qp_din,
    input  wire           qr_push,
    input  wire [PWT-1:0] qr_din,
    input  wire           sw_cr_ret,
    output reg            ph_tx_v,
    output reg  [PWT-1:0] ph_tx_flit,
    input  wire           ph_rx_v,
    input  wire [PWT-1:0] ph_rx_flit,
    output wire           rb_v,
    output wire [PWT-1:0] rb_d,
    input  wire           rb_cr,
    output reg            stall,
    output reg            fault
);
    // ---- RXPIN: pin stage on the receive inputs ----
    wire rxv_in; wire [PWT-1:0] rxf_in;
    generate if (RXPIN != 0) begin : g_rxpin
        (* keep_hierarchy *) ot_hcoll_rxpin #(.W(PWT)) u_rxpin (.clk(clk), .rst_n(rst_n), .v_i(ph_rx_v), .d_i(ph_rx_flit),
            .v_o(rxv_in), .d_o(rxf_in));
    end else begin : g_rxdir
        assign rxv_in = ph_rx_v; assign rxf_in = ph_rx_flit;
    end endgenerate
    // ---- input flops ----
    reg cr_p, rxv_p, rbcr_p;
    reg [PWT-1:0] rxf_p;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cr_p <= 1'b0; rxv_p <= 1'b0; rbcr_p <= 1'b0; end
        else begin cr_p <= sw_cr_ret; rxv_p <= rxv_in; rbcr_p <= rb_cr; end
    always @(posedge clk) rxf_p <= rxf_in;
    // ---- transmit queues + arbiter + switch-ingress credit ----
    wire qp_empty, qr_empty, qp_ovf, qr_ovf;
    wire [PWT-1:0] qp_head, qr_head;
    wire [QAW:0] c0, c1;
    reg qp_pop, qr_pop, tv;
    reg [PWT-1:0] tf;
    integer credit;
    (* keep_hierarchy *) ot_hcoll_sfifo #(.W(PWT), .AW(QAW)) u_qp (.clk(clk), .rst_n(rst_n), .push(qp_push), .din(qp_din),
        .pop(qp_pop), .empty(qp_empty), .dout(qp_head), .ovf(qp_ovf), .count(c0));
    (* keep_hierarchy *) ot_hcoll_sfifo #(.W(PWT), .AW(QAW)) u_qr (.clk(clk), .rst_n(rst_n), .push(qr_push), .din(qr_din),
        .pop(qr_pop), .empty(qr_empty), .dout(qr_head), .ovf(qr_ovf), .count(c1));
    always @* begin
        qp_pop = 1'b0; qr_pop = 1'b0; tv = 1'b0; tf = '0;
        if (credit > 0) begin
            if (!qp_empty) begin qp_pop = 1'b1; tv = 1'b1; tf = qp_head; end
            else if (!qr_empty) begin qr_pop = 1'b1; tv = 1'b1; tf = qr_head; end
        end
    end
    // ---- TX wire stages -> 2-entry queue -> serializer pacing ----
    wire w1_v;
    wire [PWT-1:0] w1_d;
    (* keep_hierarchy *) ot_hcoll_sdelay #(.W(PWT), .D(WSTG)) u_wtx (.clk(clk), .rst_n(rst_n), .v_in(tv), .d_in(tf),
        .v_out(w1_v), .d_out(w1_d));
    wire tx_empty, tx_ovf;
    wire [PWT-1:0] tx_head;
    wire [1:0] sc;
    integer acc;
    wire tx_pop = !tx_empty && (acc + BITS_X100 >= PWB * 100);
    (* keep_hierarchy *) ot_ha2_fifo #(.W(PWT), .AW(1)) u_txq (.clk(clk), .rst_n(rst_n), .push(w1_v), .din(w1_d), .pop(tx_pop),
        .empty(tx_empty), .dout(tx_head), .ovf(tx_ovf), .count(sc));
    // ---- RX wire stages -> receive buffer (exported head) ----
    wire w2_v;
    wire [PWT-1:0] w2_d;
    wire rb_ovf;
    (* keep_hierarchy *) ot_hcoll_sdelay #(.W(PWT), .D(WSTG)) u_wrx (.clk(clk), .rst_n(rst_n), .v_in(rxv_p), .d_in(rxf_p),
        .v_out(w2_v), .d_out(w2_d));
    (* keep_hierarchy *) ot_hcoll_sfifo_x #(.W(PWT), .AW(RXAW), .K(K)) u_rb (.clk(clk), .rst_n(rst_n), .push(w2_v), .din(w2_d),
        .cr_in(rbcr_p), .out_v(rb_v), .out_d(rb_d), .ovf(rb_ovf));
    // ---- state, output flops ----
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            credit <= SWCRED; acc <= 0; ph_tx_v <= 1'b0; stall <= 1'b0; fault <= 1'b0;
        end else begin : st
            integer a;
            credit <= credit - (tv ? 1 : 0) + (cr_p ? 1 : 0);
            a = acc + BITS_X100;
            if (a > PWB * 100) a = PWB * 100;
            if (tx_pop) a = a - PWB * 100;
            acc <= a;
            ph_tx_v <= tx_pop;
            stall <= credit == 0 && !(qp_empty && qr_empty);
            fault <= fault | qp_ovf | qr_ovf | tx_ovf | rb_ovf;
        end
    always @(posedge clk) ph_tx_flit <= tx_head;
endmodule

// RXPIN pin stage (struct-close 2026-10-09): one register on the receive valid / flit, no logic
module ot_hcoll_rxpin #(parameter integer W = 545) (input wire clk, input wire rst_n, input wire v_i, input wire [W-1:0] d_i,
                                                     output reg v_o, output reg [W-1:0] d_o);
    always @(posedge clk or negedge rst_n) if (!rst_n) v_o <= 1'b0; else v_o <= v_i;
`ifndef OT_HCOLL_MUT_RXPIN
    always @(posedge clk) d_o <= d_i;
`else
    reg [W-1:0] d_q;   // mutant: the flit is staged twice, the valid once (flit one beat late)
    always @(posedge clk) begin d_q <= d_i; d_o <= d_q; end
`endif
endmodule
