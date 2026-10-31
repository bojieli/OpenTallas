`timescale 1ns/1ps
// ot_s81_pma_txm: S81 SerDes analog PMA abstract, registered digital boundary (assumed); behavioural model: rtl/dsrom_sys/s81_link/col/ot_pdie_serdes_col.sv
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_s81_pma_txm (
    input wire ck,
    input wire d_v,
    input wire [543:0] d,
    output wire [543:0] pma_tx,
    output wire pma_tck
);
endmodule
