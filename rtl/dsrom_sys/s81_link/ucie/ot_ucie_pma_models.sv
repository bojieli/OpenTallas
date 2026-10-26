`timescale 1ns/1ps
// HBM-UCIE8 10-20: behavioural models of the two HBM host UCIe analog PMA abstracts (owner rule: hard PHY analog may be
// behavioural; the kit binds the hard macros physical/asap7_memory_macros/ot_ucie_pma_{txm,rxm} via their _bb.v, written by
// tools/mem_compiler/ucie_pma_gen.py).  Same model as ot_pdie_ucie (rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv: ot_s81_pma_bm,
// W 513, LAT 2): TX one 513-b word {valid, beat} a cycle -> pads LAT later, pad clock = the lane clock; RX pads -> the
// receive side LAT later on pma_rck.  Bench-only (never synthesised).
module ot_ucie_pma_txm #(parameter integer LAT = 2) (
    input  wire          ck,
    input  wire [512:0]  d,
    output wire [512:0]  pma_tx,
    output wire          pma_tck
);
    ot_s81_pma_bm #(.W(513), .LAT(LAT)) u_m (.clk(ck), .d_v(1'b1), .d(d), .q(pma_tx));
    assign pma_tck = ck;
endmodule

module ot_ucie_pma_rxm #(parameter integer LAT = 2) (
    input  wire          pma_rck,
    input  wire [512:0]  pma_rx,
    output wire [512:0]  q
);
    ot_s81_pma_bm #(.W(513), .LAT(LAT)) u_m (.clk(pma_rck), .d_v(1'b1), .d(pma_rx), .q(q));
endmodule
