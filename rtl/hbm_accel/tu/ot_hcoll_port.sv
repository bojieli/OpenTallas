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
    parameter integer FB = 0,           // hardcore-1010 FALLBACK (needs PAYLOAD_ECC 0, FACE_CK 0): per-slice arbiter
    parameter integer FACE_CK = 0       // bit 0: the RX pin flops run on the face clock tap ckf; bit 1: the TX pin flops on ckt
) (
    input  wire           clk,
    input  wire           ckf,          // face clock tap (die leaf at the RX face, option-1 source latency); tie to clk when FACE_CK[0] = 0
    input  wire           ckt,          // face clock tap (die leaf at the TX face); tie to clk when FACE_CK[1] = 0
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
    wire ckr = (FACE_CK & 1) ? ckf : clk;
    // hgi-1010/d4 (route 3b90d75fa pd50: the TX pin flops ph_tx_flit / ph_tx_v hung off a late in-block leaf at the TX
    // face, 1,105 - 1,215 ps against the interior's ~810 ps TT -> FF hold -430 ps on u_txq -> ph_tx_flit, output setup
    // -20): with FACE_CK[1] they run on the TX face tap ckt (a die clock leaf at the TX face, option-1 source latency =
    // the interior insertion less the tap tree, measured per corner on the calibrate CTS: face_ck_latency.py).
    wire ckx = (FACE_CK & 2) ? ckt : clk;
    localparam integer TXF = (FACE_CK & 2) ? 1 : 0;
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
    localparam integer NS = (PWT + 63) / 64;
    wire [NS-1:0] pe, re, pp, rr;      // FB: per-slice empty / pop of the partial and result queues
    wire          tv_w;                // the TX wire stage's valid (FB: registered with tf)
    (* keep_hierarchy *) ot_hcoll_sfifo #(.PAYLOAD_ECC(PAYLOAD_ECC),.FB(FB),.W(PWT), .AW(QAW)) u_qp (.ecc_ce(ce[0]),.ecc_ue(ue[0]),.ecc_drop(drop[0]),.clk(clk), .rst_n(rst_n), .push(qp_push), .din(qp_din),
        .pop(qp_pop), .pop_v(pp), .empty_v(pe), .empty(qp_empty), .dout(qp_head), .ovf(qp_ovf), .count(c0));
    (* keep_hierarchy *) ot_hcoll_sfifo #(.PAYLOAD_ECC(PAYLOAD_ECC),.FB(FB),.W(PWT), .AW(QAW)) u_qr (.ecc_ce(ce[1]),.ecc_ue(ue[1]),.ecc_drop(drop[1]),.clk(clk), .rst_n(rst_n), .push(qr_push), .din(qr_din),
        .pop(qr_pop), .pop_v(rr), .empty_v(re), .empty(qr_empty), .dout(qr_head), .ovf(qr_ovf), .count(c1));
    generate if (FB != 0) begin : g_fb
`ifndef SYNTHESIS
        initial if (PAYLOAD_ECC != 0 || FACE_CK != 0) $fatal(1, "ot_hcoll_port: FB needs PAYLOAD_ECC 0 and FACE_CK 0");
`endif
        // hardcore-1010 FALLBACK: the arbiter is replicated per 64-bit slice.  Slice s decides from its own queue-head
        // empty flags (pe[s] / re[s]) and its own copy cok[s] of the credit test, registered from the value credit takes
        // (cok == credit > 0 every cycle); the selected slice word is registered (tfq) with its valid (tvq) before the
        // TX wire stage: +1 edge on the TX path, no control net wider than one slice.  All slices take the same decision
        // every cycle (lock-step queues), so the credit counter follows slice 0.
        reg [NS-1:0]  cok;
        reg           tvq;
        reg [PWT-1:0] tfq;
        for (genvar s = 0; s < NS; s = s + 1) begin : g_arb
            localparam integer LO = s*64;
            localparam integer WS = (PWT-LO < 64) ? PWT-LO : 64;
            assign pp[s] = cok[s] && !pe[s];
            assign rr[s] = cok[s] && pe[s] && !re[s];
            always @(posedge clk) tfq[LO+:WS] <= pp[s] ? qp_head[LO+:WS] : qr_head[LO+:WS];
        end
        always @* begin qp_pop = pp[0]; qr_pop = rr[0]; tv = pp[0] | rr[0]; tf = tfq; end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin cok <= {NS{SWCRED > 0}}; tvq <= 1'b0; end
            else begin
`ifdef OT_HCOLL_FB_MUT_CREDIT
                cok <= {NS{credit > 0}};    // mutant: stale credit test (one edge late) -> over-issue past the switch credit
`else
                cok <= {NS{(credit - (tv ? 1 : 0) + (cr_p ? 1 : 0) + (drop[2] ? 1 : 0)) > 0}};
`endif
                tvq <= tv;
            end
        assign tv_w = tvq;
    end else begin : g_arb0
        assign pp = '0; assign rr = '0;
        always @* begin
            qp_pop = 1'b0; qr_pop = 1'b0; tv = 1'b0; tf = '0;
            if (credit > 0) begin
                if (!qp_empty) begin qp_pop = 1'b1; tv = 1'b1; tf = qp_head; end
                else if (!qr_empty) begin qr_pop = 1'b1; tv = 1'b1; tf = qr_head; end
            end
        end
        assign tv_w = tv;
    end endgenerate
    // ---- TX wire stages -> 2-entry queue -> serializer pacing ----
    wire w1_v;
    wire [PWT-1:0] w1_d;
    (* keep_hierarchy *) ot_hcoll_sdelay #(.PAYLOAD_ECC(PAYLOAD_ECC),.W(PWT), .D(WSTG)) u_wtx (.ecc_ce(ce[2]),.ecc_ue(ue[2]),.ecc_drop(drop[2]),.clk(clk), .rst_n(rst_n), .v_in(tv_w), .d_in(tf),
        .v_out(w1_v), .d_out(w1_d));
    wire tx_empty, tx_ovf;
    wire [PWT-1:0] tx_head;
    wire [1:0] sc;
    integer acc;
    // hgi-1010/d4 (TXF: route 3b90d75fa pd50 TT -49 on acc -> 32-bit add / compare -> tx_pop -> u_txq rp / ph_tx_v): the
    // pacing test of the NEXT cycle is registered (acc_ok = acc' + BITS_X100 >= PWB * 100, computed from the value acc
    // takes), so tx_pop is one flop and the empty test.  Exact: acc_ok always equals the old combinational test.
    reg acc_ok;
    wire acc_go = (TXF || FB) ? acc_ok : (acc + BITS_X100 >= PWB * 100);
    wire tx_pop = !tx_empty && acc_go;
    (* keep_hierarchy *) ot_ha2_fifo #(.W(PWT), .AW(1)) u_txq (.clk(clk), .rst_n(rst_n), .push(w1_v), .din(w1_d), .pop(tx_pop),
        .empty(tx_empty), .dout(tx_head), .ovf(tx_ovf), .count(sc));
    // ---- RX wire stages -> receive buffer (exported head) ----
    wire w2_v;
    wire [PWT-1:0] w2_d;
    wire rb_ovf;
    (* keep_hierarchy *) ot_hcoll_sdelay #(.PAYLOAD_ECC(PAYLOAD_ECC),.W(PWT), .D(WSTG)) u_wrx (.ecc_ce(ce[3]),.ecc_ue(ue[3]),.ecc_drop(drop[3]),.clk(clk), .rst_n(rst_n), .v_in(rxv_p), .d_in(rxf_p),
        .v_out(w2_v), .d_out(w2_d));
    (* keep_hierarchy *) ot_hcoll_sfifo_x #(.PAYLOAD_ECC(PAYLOAD_ECC),.FB(FB),.W(PWT), .AW(RXAW), .K(K)) u_rb (.ecc_ce(ce[4]),.ecc_ue(ue[4]),.ecc_drop(drop[4]),.clk(clk), .rst_n(rst_n), .push(w2_v), .din(w2_d),
        .cr_in(rbcr_p), .out_v(rb_v), .out_d(rb_d), .ovf(rb_ovf));
    // ---- state, output flops ----
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            credit <= SWCRED; acc <= 0; acc_ok <= (BITS_X100 >= PWB * 100); stall <= 1'b0; fault <= 1'b0;
        end else begin : st
            integer a;
            credit <= credit - (tv ? 1 : 0) + (cr_p ? 1 : 0) + (drop[2] ? 1 : 0);
            a = acc + BITS_X100;
            if (a > PWB * 100) a = PWB * 100;
            if (tx_pop) a = a - PWB * 100;
            acc <= a;
            acc_ok <= (a + BITS_X100 >= PWB * 100);
            stall <= credit == 0 && !(qp_empty && qr_empty);
            fault <= fault | (|ue) | qp_ovf | qr_ovf | tx_ovf | rb_ovf;
        end
    // TX pin flops (on the TX face tap ckx with FACE_CK[1], else clk)
    always @(posedge ckx or negedge rst_n) if (!rst_n) ph_tx_v <= 1'b0; else ph_tx_v <= tx_pop;
    always @(posedge ckx) ph_tx_flit <= tx_head;
endmodule
