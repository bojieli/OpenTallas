`timescale 1ns/1ps
// ot_sram_1r1w_64x16_m1_escape_p192: ASAP7 1R1W SRAM 64 x 16, mux 1, 1 bank(s), 0 spare row(s), 0 spare IO column(s); OpenTallas tools/mem_compiler/sram_gen.py v1.0
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_sram_1r1w_64x16_m1_escape_p192 (
    input wire clk,
    input wire r_ce_in,
    input wire [5:0] r_addr_in,
    output wire [15:0] rd_out,
    input wire w_ce_in,
    input wire [5:0] w_addr_in,
    input wire [15:0] wd_in,
    input wire [15:0] w_mask_in
);
endmodule
