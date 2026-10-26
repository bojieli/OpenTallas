`timescale 1ns/1ps
// ot_sram_1r1w_32x512_m1: ASAP7 1R1W SRAM 32 x 512, mux 1, 1 bank(s), 0 spare row(s), 0 spare IO column(s); write enable per 32 bits; pin faces rw; OpenTallas tools/mem_compiler/sram_gen.py v1.0
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_sram_1r1w_32x512_m1 (
    input wire clk,
    input wire r_ce_in,
    input wire [4:0] r_addr_in,
    output wire [511:0] rd_out,
    input wire w_ce_in,
    input wire [4:0] w_addr_in,
    input wire [511:0] wd_in,
    input wire [15:0] w_mask_in
);
endmodule
