`timescale 1ns/1ps
// ot_sram_1r1w_1024x39_m4_r0c0: ASAP7 1R1W SRAM 1024 x 39, mux 4, 1 bank(s), 0 spare row(s), 0 spare IO column(s); OpenTallas tools/mem_compiler/sram_gen.py v1.0+aligned-v2
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_sram_1r1w_1024x39_m4_r0c0 (
    input wire clk,
    input wire r_ce_in,
    input wire [9:0] r_addr_in,
    output wire [38:0] rd_out,
    input wire w_ce_in,
    input wire [9:0] w_addr_in,
    input wire [38:0] wd_in,
    input wire [38:0] w_mask_in
);
endmodule
