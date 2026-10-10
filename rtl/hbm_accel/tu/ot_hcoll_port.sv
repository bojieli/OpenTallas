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
    parameter integer PAYLOAD_ECC = 0,
    parameter integer FACE_CK = 0       // 1: the RX pin flops run on the face clock tap ckf
) (
    input  wire           clk,
    input  wire           ckf,          // face clock tap (die leaf at the PHY face, option-1 source latency); tie to clk when FACE_CK = 0
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
    output reg            ecc_ce,
    output reg [1:0]      rx_ecc_drop,
    output reg            fault
);
    // ---- input flops ----
    reg cr_p, rxv_p, rbcr_p;
    reg [PWT-1:0] rxf_p;
    // hgi-takeover (route e21dc1395 TT -158 / FF -80: rxf_p at the PHY face hung off a late in-block leaf, ~500 ps behind
    // the RX wire stage): with FACE_CK the RX pin flops run on the face tap ckf, a die clock leaf at the PHY face whose
    // option-1 source latency (face_ck.sdc: the block's interior insertion) aligns them with the interior registers
    wire ckr = (FACE_CK != 0) ? ckf : clk;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cr_p <= 1'b0; rbcr_p <= 1'b0; end
        else begin cr_p <= sw_cr_ret; rbcr_p <= rb_cr; end
    always @(posedge ckr or negedge rst_n) if (!rst_n) rxv_p <= 1'b0; else rxv_p <= ph_rx_v;
    always @(posedge ckr) rxf_p <= ph_rx_flit;
    // ---- transmit queues + arbiter + switch-ingress credit ----
    wire [4:0] ce, ue, drop;
    // Two independent RX stores can retire corrupt words in the same cycle.
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin ecc_ce<=0;rx_ecc_drop<=0;end
        else begin ecc_ce<=|ce;rx_ecc_drop<={1'b0,drop[3]}+{1'b0,drop[4]};end
    wire qp_empty, qr_empty, qp_ovf, qr_ovf;
    wire [PWT-1:0] qp_head, qr_head;
    wire [QAW:0] c0, c1;
    reg qp_pop, qr_pop, tv;
    reg [PWT-1:0] tf;
    integer credit;
    (* keep_hierarchy *) ot_hcoll_sfifo #(.PAYLOAD_ECC(PAYLOAD_ECC),.W(PWT), .AW(QAW)) u_qp (.ecc_ce(ce[0]),.ecc_ue(ue[0]),.ecc_drop(drop[0]),.clk(clk), .rst_n(rst_n), .push(qp_push), .din(qp_din),
        .pop(qp_pop), .empty(qp_empty), .dout(qp_head), .ovf(qp_ovf), .count(c0));
    (* keep_hierarchy *) ot_hcoll_sfifo #(.PAYLOAD_ECC(PAYLOAD_ECC),.W(PWT), .AW(QAW)) u_qr (.ecc_ce(ce[1]),.ecc_ue(ue[1]),.ecc_drop(drop[1]),.clk(clk), .rst_n(rst_n), .push(qr_push), .din(qr_din),
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
    (* keep_hierarchy *) ot_hcoll_sdelay #(.PAYLOAD_ECC(PAYLOAD_ECC),.W(PWT), .D(WSTG)) u_wtx (.ecc_ce(ce[2]),.ecc_ue(ue[2]),.ecc_drop(drop[2]),.clk(clk), .rst_n(rst_n), .v_in(tv), .d_in(tf),
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
    (* keep_hierarchy *) ot_hcoll_sdelay #(.PAYLOAD_ECC(PAYLOAD_ECC),.W(PWT), .D(WSTG)) u_wrx (.ecc_ce(ce[3]),.ecc_ue(ue[3]),.ecc_drop(drop[3]),.clk(clk), .rst_n(rst_n), .v_in(rxv_p), .d_in(rxf_p),
        .v_out(w2_v), .d_out(w2_d));
    (* keep_hierarchy *) ot_hcoll_sfifo_x #(.PAYLOAD_ECC(PAYLOAD_ECC),.W(PWT), .AW(RXAW), .K(K)) u_rb (.ecc_ce(ce[4]),.ecc_ue(ue[4]),.ecc_drop(drop[4]),.clk(clk), .rst_n(rst_n), .push(w2_v), .din(w2_d),
        .cr_in(rbcr_p), .out_v(rb_v), .out_d(rb_d), .ovf(rb_ovf));
    // ---- state, output flops ----
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            credit <= SWCRED; acc <= 0; ph_tx_v <= 1'b0; stall <= 1'b0; fault <= 1'b0;
        end else begin : st
            integer a;
            credit <= credit - (tv ? 1 : 0) + (cr_p ? 1 : 0) + (drop[2] ? 1 : 0);
            a = acc + BITS_X100;
            if (a > PWB * 100) a = PWB * 100;
            if (tx_pop) a = a - PWB * 100;
            acc <= a;
            ph_tx_v <= tx_pop;
            stall <= credit == 0 && !(qp_empty && qr_empty);
            fault <= fault | (|ue) | qp_ovf | qr_ovf | tx_ovf | rb_ovf;
        end
    always @(posedge clk) ph_tx_flit <= tx_head;
endmodule
