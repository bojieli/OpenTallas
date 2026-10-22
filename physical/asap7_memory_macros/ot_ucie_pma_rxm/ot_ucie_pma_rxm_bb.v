`timescale 1ns/1ps
// ot_ucie_pma_rxm: HBM host UCIe analog PMA abstract, registered digital boundary (assumed); behavioural model: rtl/dsrom_sys/s81_link/ucie/ot_ucie_pma_models.sv
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_ucie_pma_rxm (
    input wire pma_rck,
    input wire [512:0] pma_rx,
    output wire [512:0] q
);
endmodule
