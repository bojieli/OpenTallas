`timescale 1ns/1ps
// ot_sram_1rw_64x128_m1: ASAP7 1RW SRAM 64 x 128, mux 1, 1 bank(s), 0 spare row(s), 0 spare IO column(s); OpenTallas tools/mem_compiler/sram_gen.py v1.0
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_sram_1rw_64x128_m1 (
    input wire clk,
    input wire ce_in,
    input wire we_in,
    input wire [5:0] addr_in,
    input wire [127:0] wd_in,
    input wire [127:0] w_mask_in,
    output wire [127:0] rd_out
);
endmodule
