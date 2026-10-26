`timescale 1ns/1ps
// ot_ucie_pma_txm: HBM host UCIe analog PMA abstract, registered digital boundary (assumed); behavioural model: rtl/dsrom_sys/s81_link/ucie/ot_ucie_pma_models.sv
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_ucie_pma_txm (
    input wire ck,
    input wire [512:0] d,
    output wire [512:0] pma_tx,
    output wire pma_tck
);
endmodule
