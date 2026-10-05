`timescale 1ns/1ps
// ot_sram_1r1w_1024x256_m2_r2c2: ASAP7 1R1W SRAM 1024 x 256, mux 2, 1 bank(s), 2 spare row(s), 2 spare IO column(s); OpenTallas tools/mem_compiler/sram_gen.py v1.0
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_sram_1r1w_1024x256_m2_r2c2 (
    input wire clk,
    input wire r_ce_in,
    input wire [9:0] r_addr_in,
    output wire [255:0] rd_out,
    input wire w_ce_in,
    input wire [9:0] w_addr_in,
    input wire [255:0] wd_in,
    input wire [255:0] w_mask_in,
    input wire [1:0] rr_en,
    input wire [17:0] rr_addr,
    input wire [1:0] cr_en,
    input wire [15:0] cr_sel
);
endmodule
