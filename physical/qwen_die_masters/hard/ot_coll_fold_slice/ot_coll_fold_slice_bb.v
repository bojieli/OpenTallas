`timescale 1ns/1ps
// el1011-q-coll 2026-10-11: blackbox of the hardened all-reduce lane slice (routed qfd_io_collective_fs-b760fc991-tc-cl,
// TT +231.10 / FF +2.85, DRC 0); views: ot_coll_fold_slice.lef + _{tt,ss,ff}.lib (write_abstract_lef / write_timing_model
// from 6_final.odb + spef).  Parameters fixed at the hardened values N = 4, ADD_LAT = 7, SEAM = 1.
(* blackbox *)
module ot_coll_fold_slice (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         red_in,
    input  wire [511:0] src,
    output wire [127:0] sum,
    output wire         v_out,
    output wire         e_out
);
endmodule
