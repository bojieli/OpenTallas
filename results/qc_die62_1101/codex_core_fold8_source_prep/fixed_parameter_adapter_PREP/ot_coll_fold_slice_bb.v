`timescale 1ns/1ps
// UNQUALIFIED SOURCE PREP ONLY. One fixed N4/ADD_LAT7/SEAM1 hardmaster,
// reused eight times. This is metadata for existing native_bb guarded default
// serialization, not a SIGNED view or functional body. ABI stays512/128 for
// every parse; differing/unresolved overrides must fail before substitution.
(* blackbox *)
module ot_coll_fold_slice #(
    parameter integer N = 4,
    parameter integer ADD_LAT = 7,
    parameter integer SEAM = 1
) (
    input wire clk,
    input wire rst_n,
    input wire red_in,
    input wire [511:0] src,
    output wire [127:0] sum,
    output wire v_out,
    output wire e_out
);
endmodule
