`timescale 1ns/1ps
// ot_sram_1r1w_128x128_m1_r0c0_g128: ASAP7 1R1W SRAM 128 x 128, mux 1, 1 bank(s), 0 spare row(s), 0 spare IO column(s); write enable per 128 bits; pin faces rw; OpenTallas tools/mem_compiler/sram_gen.py v1.0+aligned-v2
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_sram_1r1w_128x128_m1_r0c0_g128 (
    input wire clk,
    input wire r_ce_in,
    input wire [6:0] r_addr_in,
    output wire [127:0] rd_out,
    input wire w_ce_in,
    input wire [6:0] w_addr_in,
    input wire [127:0] wd_in,
    input wire w_mask_in
);
endmodule
