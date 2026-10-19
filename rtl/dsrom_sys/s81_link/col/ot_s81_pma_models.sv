`timescale 1ns/1ps
// S81-SERDES 10-19: behavioural models of the two S81 SerDes analog PMA abstracts (owner rule: hard PHY analog may be
// behavioural; the kit binds the hard macros physical/asap7_memory_macros/ot_s81_pma_{txm,rxm} via their _bb.v).
// Same model as ot_pdie_serdes_edge3.sv / ot_pdie_serdes (ot_s81_pma_bm, LAT 4): TX one 544-b word a cycle -> pads LAT
// later, pad clock = the lane clock; RX pads -> recovered side LAT later on pma_rck.  Bench-only (never synthesised).
module ot_s81_pma_txm #(parameter integer LAT = 4) (
    input  wire          ck,
    input  wire          d_v,
    input  wire [543:0]  d,
    output wire [543:0]  pma_tx,
    output wire          pma_tck
);
    ot_s81_pma_bm #(.W(544), .LAT(LAT)) u_m (.clk(ck), .d_v(d_v), .d(d), .q(pma_tx));
    assign pma_tck = ck;
endmodule

module ot_s81_pma_rxm #(parameter integer LAT = 4) (
    input  wire          pma_rck,
    input  wire [543:0]  pma_rx,
    output wire [543:0]  q
);
    ot_s81_pma_bm #(.W(544), .LAT(LAT)) u_m (.clk(pma_rck), .d_v(1'b1), .d(pma_rx), .q(q));
endmodule
