// ot_s81hd_elemA_cv / ot_s81hd_elemB_cv black boxes (S81-HEAD 10-24): synthesis view of the CLOSED head element macros
// (LEF / liberty physical/die_plan/s81_head/cores/views/ot_s81hd_elem{A,B}_cv).  Simulation: ot_s81hd_elem_cv.sv.
(* blackbox *)
module ot_s81hd_elemA_cv (
    input clk, input rst_n, input go, input [16:0] row0, input [255:0] x, input b_v, input [31:0] b_d,
    output o_v, output [31:0] o_d, output l_v, output [31:0] l_d, output done, output [16:0] best_row,
    output [31:0] best_bits, output [31:0] best_key, output fault);
endmodule
(* blackbox *)
module ot_s81hd_elemB_cv (
    input clk, input rst_n, input go, input [16:0] row0, input [255:0] x, input b_v, input [31:0] b_d,
    output o_v, output [31:0] o_d, output l_v, output [31:0] l_d, output done, output [16:0] best_row,
    output [31:0] best_bits, output [31:0] best_key, output fault);
endmodule
