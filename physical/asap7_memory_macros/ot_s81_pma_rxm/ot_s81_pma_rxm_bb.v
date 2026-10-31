`timescale 1ns/1ps
// ot_s81_pma_rxm: S81 SerDes analog PMA abstract, registered digital boundary (assumed); behavioural model: rtl/dsrom_sys/s81_link/col/ot_pdie_serdes_col.sv
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_s81_pma_rxm (
    input wire pma_rck,
    input wire [543:0] pma_rx,
    output wire [543:0] q
);
endmodule
