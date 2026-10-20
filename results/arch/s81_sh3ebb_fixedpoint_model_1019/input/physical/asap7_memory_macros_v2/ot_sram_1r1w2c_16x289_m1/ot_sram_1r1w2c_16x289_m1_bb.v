`timescale 1ns/1ps
// ot_sram_1r1w2c_16x289_m1: ASAP7 1R1W2C SRAM 16 x 289, mux 1, 1 bank(s), 0 spare row(s), 0 spare IO column(s); OpenTallas tools/mem_compiler/sram_gen.py v1.0
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_sram_1r1w2c_16x289_m1 (
    input wire wclk,
    input wire rclk,
    input wire r_ce_in,
    input wire [3:0] r_addr_in,
    output wire [288:0] rd_out,
    input wire w_ce_in,
    input wire [3:0] w_addr_in,
    input wire [288:0] wd_in,
    input wire [288:0] w_mask_in
);
endmodule
