`timescale 1ns/1ps
// Head SerDes digital-link adapter. Exact reuse of the layer-die KP4/link
// implementation: coll_o0 is {live, fault, rx[511:0]}. PMA pads stay explicit;
// a physical head binding must publish them at its PHY boundary, never tie them.
// This adapter adds no register or latency cycle. Only the analog PMA remains
// behavioural inside ot_pdie_serdes, as in the existing released link bench.
module ot_s81hd_serdes_link #(
    parameter integer PMA_LAT = 4
) (
    input wire ck,
    input wire rst_n,
    input wire [511:0] coll_i0,
    output wire [513:0] coll_o0,
    output wire [543:0] pma_tx,
    output wire pma_tck,
    input wire [543:0] pma_rx,
    input wire pma_rck
);
    wire [511:0] rx;
    wire [1:0] st;
`ifdef OT_S81HD_SERDES_SC
    // DIE-HEAD-76-SERDESRF 11-06 opt-in SC form (ot_s81hd_serdes_sc.sv): hard children u_tx / u_dec.u_syn.u_bm0..2 /
    // u_dec.u_chn, RXQ receive side, pma_tx +2 ck edges.  Default (no define) is unchanged.
    ot_s81hd_pdie_sc #(.PMA_LAT(PMA_LAT)) u_link (
        .clk(ck), .rst(rst_n), .tx(coll_i0), .rx(rx), .st(st),
        .pma_tx(pma_tx), .pma_tck(pma_tck), .pma_rx(pma_rx), .pma_rck(pma_rck)
    );
`else
    ot_pdie_serdes #(.PMA_LAT(PMA_LAT)) u_link (
        .clk(ck), .rst(rst_n), .tx(coll_i0), .rx(rx), .st(st),
        .pma_tx(pma_tx), .pma_tck(pma_tck), .pma_rx(pma_rx), .pma_rck(pma_rck)
    );
`endif
`ifdef OT_S81HD_SERDES_MUT_STATUS
    assign coll_o0 = {st[0], st[1], rx};
`else
    assign coll_o0 = {st, rx};
`endif
endmodule
