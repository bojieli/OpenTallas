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
    ot_pdie_serdes #(.PMA_LAT(PMA_LAT)) u_link (
        .clk(ck), .rst(rst_n), .tx(coll_i0), .rx(rx), .st(st),
        .pma_tx(pma_tx), .pma_tck(pma_tck), .pma_rx(pma_rx), .pma_rck(pma_rck)
    );
`ifdef OT_S81HD_SERDES_MUT_STATUS
    assign coll_o0 = {st[0], st[1], rx};
`else
    assign coll_o0 = {st, rx};
`endif
endmodule
